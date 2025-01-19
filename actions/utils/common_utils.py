# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license

import asyncio
import re
from urllib import parse

import aiohttp

REQUESTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8,zh-CN;q=0.7,zh;q=0.6",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua": '"Chromium";v="132", "Google Chrome";v="132", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Referer": "https://www.google.com/",
    "Origin": "https://www.google.com/",
}

URL_IGNORE_LIST = frozenset(
    {
        "localhost",
        "127.0.0",
        ":5000",
        ":3000",
        ":8000",
        ":8080",
        ":6006",
        "MODEL_ID",
        "API_KEY",
        "url",
        "example",
        "mailto:",
        "github.com",  # ignore GitHub links that may be private repos
        "linkedin.com",
        "twitter.com",
        "x.com",
        "storage.googleapis.com",  # private GCS buckets
    }
)

URL_PATTERN = re.compile(
    r"\[([^]]+)]\(([^)]+)\)"  # Matches Markdown links [text](url)
    r"|"
    r"("  # Start capturing group for plaintext URLs
    r"(?:https?://)?"  # Optional http:// or https://
    r"(?:www\.)?"  # Optional www.
    r"(?:[\w.-]+)?"  # Optional domain name and subdomains
    r"\.[a-zA-Z]{2,}"  # TLD
    r"(?:/[^\s\"')\]]*)?"  # Optional path
    r")"
)


def remove_html_comments(body: str) -> str:
    """Removes HTML comments from a string using regex pattern matching."""
    return re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()


def clean_url(url):
    """Remove extra characters from URL strings."""
    for _ in range(3):
        url = str(url).strip('"').strip("'").rstrip(".,:;!?`\\").replace(".git@main", "").replace("git+", "")
    return url


async def is_url_async(url, session, check=True, max_attempts=3, timeout=2):
    """Asynchronously check if string is URL and optionally verify it exists."""
    try:
        # Check allow list
        if any(x in url for x in URL_IGNORE_LIST):
            return True

        # Check structure
        result = parse.urlparse(url)
        partition = result.netloc.partition(".")  # i.e. netloc = "github.com" -> ("github", ".", "com")
        if not result.scheme or not partition[0] or not partition[2]:
            return False

        if check:
            bad_codes = {404, 410, 500, 502, 503, 504}
            kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout)}

            for attempt in range(max_attempts):
                try:
                    # Try HEAD first, then GET if needed
                    for method in (session.head, session.get):
                        async with method(url, **kwargs) as response:
                            if response.status not in bad_codes:
                                return True
                    return False
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    if attempt == max_attempts - 1:  # last attempt
                        return False
                    await asyncio.sleep(2**attempt)  # exponential backoff
            return False
        return True
    except Exception:
        return False


async def check_links_in_string_async(text, verbose=True, return_bad=False):
    """Asynchronously process a given text, find unique URLs within it, and check for any 404 errors."""
    all_urls = []
    for md_text, md_url, plain_url in URL_PATTERN.findall(text):
        url = md_url or plain_url
        if url and parse.urlparse(url).scheme:
            all_urls.append(url)

    urls = set(map(clean_url, all_urls))  # remove extra characters and make unique

    async with aiohttp.ClientSession(headers=REQUESTS_HEADERS) as session:
        tasks = [is_url_async(url, session) for url in urls]
        results = await asyncio.gather(*tasks)
        bad_urls = [url for url, valid in zip(urls, results) if not valid]

    passing = not bad_urls
    if verbose and not passing:
        print(f"WARNING ⚠️ errors found in URLs {bad_urls}")

    return (passing, bad_urls) if return_bad else passing


async def main():
    # Example usage
    passing, bad_urls = await check_links_in_string_async(
        "Check out https://ultralytics.com/images/bus.jpg and this non-existent link https://ultralytics.com/invalid"
    )
    print(f"Passing: {passing}")
    if not passing:
        print(f"Bad URLs: {bad_urls}")

    # Test is_url_async directly
    async with aiohttp.ClientSession() as session:
        result = await is_url_async("https://ultralytics.com/images/bus.jpg", session)
        print(f"Is valid URL: {result}")


if __name__ == "__main__":
    asyncio.run(main())
