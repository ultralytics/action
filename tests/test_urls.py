# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license

# Continuous Integration (CI) GitHub Actions tests


import aiohttp
import pytest

from actions.utils.common_utils import check_links_in_string_async, is_url_async

URLS = [
    "https://docs.ultralytics.com/help/contributing",
    "https://ultralytics.com",
    "https://ultralytics.com/images/bus.jpg",
    "https://github.com/ultralytics/ultralytics",
    "https://azure.microsoft.com/",
    "https://www.tableau.com/",
    "https://openai.com/research/gpt-4",
    "https://azure.microsoft.com/en-us/services/machine-learning/",
    "https://azure.microsoft.com/en-us/products/storage/blobs",
    "https://www.reuters.com/article/idUSKCN1MK08G/",
    "https://www.kdnuggets.com/",
    "https://www.datacamp.com/tutorial/understanding-logistic-regression-python",
    "https://www.statisticshowto.com/probability-and-statistics/find-outliers/",
    "https://www.reddit.com/r/Ultralytics/comments/1fw3605/release_megathread/",
    "https://www.kaggle.com/models/ultralytics/yolo11",
    "https://apps.apple.com/xk/app/ultralytics/id1583935240",
]


@pytest.fixture
def verbose():
    """Fixture that provides a verbose logging utility for detailed output during testing and debugging."""
    return False  # Set False to suppress print statements during tests


@pytest.mark.asyncio
async def test_is_url():
    """Test each URL using is_url_async function."""
    async with aiohttp.ClientSession() as session:
        for url in URLS:
            assert await is_url_async(url, session), f"URL check failed: {url}"


@pytest.mark.asyncio
async def test_html_links(verbose):
    """Tests the validity of URLs within HTML anchor tags and returns any invalid URLs found."""
    text = "Visit <a href='https://err.com'>our site</a> or <a href=\"http://test.org\">test site</a>"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.com", "http://test.org"}


@pytest.mark.asyncio
async def test_markdown_links(verbose):
    """Validates URLs in Markdown links within a given text using check_links_in_string_async."""
    text = "Check [Example](https://err.com) or [Test](http://test.org)"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.com", "http://test.org"}


@pytest.mark.asyncio
async def test_mixed_formats(verbose):
    """Tests URL detection in mixed text formats (HTML, Markdown, plain text) using check_links_in_string_async."""
    text = "A <a href='https://1.com'>link</a> and [markdown](https://2.org/) and https://3.net"
    result, urls = await check_links_in_string_async(text, return_bad=True)
    assert result is False
    assert set(urls) == {"https://1.com", "https://3.net"}


@pytest.mark.asyncio
async def test_duplicate_urls(verbose):
    """Tests detection of duplicate URLs in various text formats using the check_links_in_string_async function."""
    text = "Same URL: https://err.com and <a href='https://err.com'>link</a>"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.com"}


@pytest.mark.asyncio
async def test_no_urls(verbose):
    """Tests that a string with no URLs returns True when checked using the check_links_in_string_async function."""
    text = "This text contains no URLs."
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is True
    assert not set(urls)


@pytest.mark.asyncio
async def test_invalid_urls(verbose):
    """Test invalid URLs."""
    text = "Invalid URL: http://.com"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"http://.com"}


@pytest.mark.asyncio
async def test_urls_with_paths_and_queries(verbose):
    """Test URLs with paths and query parameters to ensure they are correctly identified and validated."""
    text = "Complex URL: https://err.com/path?query=value#fragment"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.com/path?query=value#fragment"}


@pytest.mark.asyncio
async def test_urls_with_different_tlds(verbose):
    """Test URLs with various top-level domains (TLDs) to ensure correct identification and handling."""
    text = "Different TLDs: https://err.ml https://err.org https://err.net https://err.io https://err.ai"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.ml", "https://err.io", "https://err.ai"}


@pytest.mark.asyncio
async def test_case_sensitivity(verbose):
    """Tests URL case sensitivity by verifying that URLs with different cases are correctly identified and handled."""
    text = "Case test: HTTPS://err.com and https://err.com"
    result, urls = await check_links_in_string_async(text, verbose, return_bad=True)
    assert result is False
    assert set(urls) == {"https://err.com"}
