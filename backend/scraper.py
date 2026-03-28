"""
scraper.py — Web scraping logic using requests + BeautifulSoup
Extracts all links from the given URL.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = 12  # seconds


def fetch_page(url: str) -> str:
    """Download page HTML. Raises on HTTP error or timeout."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def extract_links(html: str, base_url: str) -> List[Dict[str, str]]:
    """
    Parse all <a href="..."> tags and return a list of dicts:
      { "text": "Link text", "url": "Absolute URL" }
    Filters out empty, mailto:, tel:, and javascript: links.
    Deduplicates by URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen_urls = set()
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # Skip useless schemes
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        if not href:
            continue

        # Resolve relative URLs to absolute
        absolute_url = urljoin(base_url, href)

        # Validate it's a proper http/https URL
        parsed = urlparse(absolute_url)
        if parsed.scheme not in ("http", "https"):
            continue

        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)

        link_text = tag.get_text(separator=" ", strip=True)

        links.append({
            "text": link_text[:200],      # cap text length
            "url": absolute_url[:2000],   # cap URL length
        })

    return links


def get_page_summary(html: str) -> Dict[str, str]:
    """
    Extract lightweight page metadata to pass to the AI:
    title, meta description, h1 headings.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else "No title"

    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"][:500]

    h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")][:5]
    h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")][:8]

    # First ~600 chars of visible body text
    body_text = ""
    body = soup.find("body")
    if body:
        raw = body.get_text(separator=" ", strip=True)
        body_text = raw[:600]

    return {
        "title": title,
        "description": description,
        "h1": ", ".join(h1_tags) if h1_tags else "None",
        "h2": ", ".join(h2_tags) if h2_tags else "None",
        "body_preview": body_text,
    }


def scrape(url: str) -> Dict:
    """
    Full scrape pipeline:
    1. Fetch page HTML
    2. Extract all links
    3. Extract page metadata for AI prompt
    Returns dict with 'links' and 'page_summary'.
    Raises ValueError on failure.
    """
    try:
        html = fetch_page(url)
    except requests.exceptions.Timeout:
        raise ValueError(f"Request timed out after {TIMEOUT}s. The site may be slow or unreachable.")
    except requests.exceptions.ConnectionError:
        raise ValueError("Could not connect to the URL. Check the address and your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"HTTP Error: {e.response.status_code} — {e.response.reason}")
    except Exception as e:
        raise ValueError(f"Failed to fetch page: {str(e)}")

    links = extract_links(html, base_url=url)
    page_summary = get_page_summary(html)

    return {
        "links": links,
        "page_summary": page_summary,
    }