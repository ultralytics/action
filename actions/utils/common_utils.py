# Ultralytics Actions 🚀, AGPL-3.0 license https://ultralytics.com/license

import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib import parse


def remove_html_comments(body: str) -> str:
    """Removes HTML comments from a string using regex pattern matching."""
    return re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()


def clean_url(url):
    """Remove extra characters from URL strings."""
    for _ in range(3):
        url = str(url).strip('"').strip("'").rstrip(".,:;!?`\\").replace(".git@main", "").replace("git+", "")
    return url


def is_url(url, check=True, max_attempts=3, timeout=2):
    """Check if string is URL and check if URL exists."""
    allow_list = (
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
        "kaggle.com",  # blocks automated header requests
        "reddit.com",  # blocks automated header requests
        "linkedin.com",
        "twitter.com",
        "x.com",
        "storage.googleapis.com",  # private GCS buckets
    )
    try:
        # Check allow list
        if any(x in url for x in allow_list):
            return True

        # Check structure
        result = parse.urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False

        # Check response
        if check:
            for attempt in range(max_attempts):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                        "Accept": "*",
                        "Accept-Language": "*",
                        "Accept-Encoding": "*",
                    }
                    return requests.head(url, headers=headers, timeout=timeout, allow_redirects=True).status_code < 400
                except Exception:
                    if attempt == max_attempts - 1:  # last attempt
                        return False
                    time.sleep(2**attempt)  # exponential backoff
            return False
        return True
    except Exception:
        return False


def check_links_in_string(text, verbose=True, return_bad=False):
    """Process a given text, find unique URLs within it, and check for any 404 errors."""
    pattern = (
        r"\[([^\]]+)\]\(([^)]+)\)"  # Matches Markdown links [text](url)
        r"|"
        r"("  # Start capturing group for plaintext URLs
        r"(?:https?://)?"  # Optional http:// or https://
        r"(?:www\.)?"  # Optional www.
        r"[\w.-]+"  # Domain name and subdomains
        r"\.[a-zA-Z]{2,}"  # TLD
        r"(?:/[^\s\"')\]]*)?"  # Optional path
        r")"
    )
    # all_urls.extend([url for url in match if url and parse.urlparse(url).scheme])
    all_urls = []
    for md_text, md_url, plain_url in re.findall(pattern, text):
        url = md_url or plain_url
        if url and parse.urlparse(url).scheme:
            all_urls.append(url)

    urls = set(map(clean_url, all_urls))  # remove extra characters and make unique
    # bad_urls = [x for x in urls if not is_url(x, check=True)]  # single-thread
    with ThreadPoolExecutor(max_workers=16) as executor:  # multi-thread
        bad_urls = [url for url, valid in zip(urls, executor.map(lambda x: not is_url(x, check=True), urls)) if valid]

    passing = not bad_urls
    if verbose and not passing:
        print(f"WARNING ⚠️ errors found in URLs {bad_urls}")

    return (passing, bad_urls) if return_bad else passing
