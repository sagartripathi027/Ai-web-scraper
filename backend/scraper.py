"""
scraper.py — Job scraping logic using requests + BeautifulSoup
Extracts job listings from the given URL.
Supports official APIs for Jobicy and RemoteOK, with HTML fallback for other sites.
"""

import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# ------------------ OFFICIAL API HANDLERS ------------------

def fetch_jobicy_api(url: str) -> Dict | None:
    if "jobicy.com" not in url:
        return None
    try:
        api_url = "https://jobicy.com/api/v2/remote-jobs?count=20"
        response = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for j in data.get("jobs", []):
            salary_min = j.get("annualSalaryMin")
            salary_max = j.get("annualSalaryMax")
            salary = f"${salary_min}–${salary_max}" if salary_min and salary_max else "N/A"
            jobs.append({
                "title": str(j.get("jobTitle", "N/A"))[:200],
                "company": str(j.get("companyName", "N/A"))[:200],
                "location": str(j.get("jobGeo", "Remote"))[:200],
                "salary": salary[:200],
                "url": str(j.get("url", url))[:2000],
            })
        return {
            "jobs": jobs,
            "page_summary": {
                "title": "Jobicy Remote Jobs",
                "description": f"Fetched via Jobicy public API v2. {len(jobs)} jobs retrieved.",
                "h1": "Remote Jobs", "h2": "", "body_preview": "",
            },
        }
    except Exception:
        return None


def fetch_remoteok_api(url: str) -> Dict | None:
    if "remoteok" not in url:
        return None
    try:
        api_headers = {**HEADERS, "User-Agent": "Mozilla/5.0"}
        response = requests.get("https://remoteok.com/api", headers=api_headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for j in data:
            if not isinstance(j, dict) or "position" not in j:
                continue
            jobs.append({
                "title": str(j.get("position", "N/A"))[:200],
                "company": str(j.get("company", "N/A"))[:200],
                "location": str(j.get("location", "Remote"))[:200],
                "salary": str(j.get("salary", "N/A"))[:200] if j.get("salary") else "N/A",
                "url": str(j.get("url", url))[:2000],
            })
        return {
            "jobs": jobs[:30],
            "page_summary": {
                "title": "RemoteOK Jobs",
                "description": f"Fetched via RemoteOK public API. {len(jobs[:30])} jobs retrieved.",
                "h1": "Remote Jobs", "h2": "", "body_preview": "",
            },
        }
    except Exception:
        return None


# ------------------ HTML FALLBACK ------------------

def fetch_page(url: str) -> str:
    session = requests.Session()
    headers = {
        **HEADERS,
        "Referer": "https://www.google.com/",
        "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        response = session.get(url, headers=headers, timeout=TIMEOUT, verify=True)
        response.raise_for_status()
        return response.text
    except requests.exceptions.SSLError:
        response = session.get(url, headers=headers, timeout=TIMEOUT, verify=False)
        response.raise_for_status()
        return response.text


def extract_jobs(html: str, base_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen: set = set()

    selectors = [
        "div.job_seen_beacon",
        "li.jobs-search-results__list-item",
        "article.jobDescription",
        "div.job-card-container",
        "div[class*='job-listing']",
        "div[class*='job-card']",
        "div[class*='jobCard']",
        "li[class*='job']",
        "div[class*='vacancy']",
        "div[class*='position']",
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    if not cards:
        for tag in soup.find_all("a", href=True):
            href = str(tag["href"]).strip()
            text = tag.get_text(strip=True)
            if not text or len(text) < 5:
                continue
            if any(kw in href.lower() for kw in ["job", "career", "vacancy", "position", "opening"]):
                absolute_url = urljoin(base_url, href)
                if absolute_url in seen:
                    continue
                seen.add(absolute_url)
                jobs.append({
                    "title": text[:200],
                    "company": "N/A",
                    "location": "N/A",
                    "salary": "N/A",
                    "url": absolute_url[:2000],
                })
        return jobs

    for card in cards:
        title_tag = (
            card.find("h2") or card.find("h3") or
            card.find(class_=lambda c: c and "title" in c.lower()) or
            card.find("a")
        )
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        company_tag = card.find(class_=lambda c: c and any(k in c.lower() for k in ["company", "employer", "org"]))
        company = company_tag.get_text(strip=True) if company_tag else "N/A"
        location_tag = card.find(class_=lambda c: c and "location" in c.lower())
        location = location_tag.get_text(strip=True) if location_tag else "N/A"
        salary_tag = card.find(class_=lambda c: c and any(k in c.lower() for k in ["salary", "pay", "compensation"]))
        salary = salary_tag.get_text(strip=True) if salary_tag else "N/A"
        link_tag = card.find("a", href=True)
        job_url = urljoin(base_url, str(link_tag["href"])) if link_tag else base_url

        if job_url in seen or title == "N/A":
            continue
        seen.add(job_url)
        jobs.append({
            "title": title[:200],
            "company": company[:200],
            "location": location[:200],
            "salary": salary[:200],
            "url": job_url[:2000],
        })

    return jobs


def get_page_summary(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "No title"
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = str(meta_desc["content"])[:500]
    h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")][:5]
    h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")][:8]
    body_text = ""
    body = soup.find("body")
    if body:
        body_text = body.get_text(separator=" ", strip=True)[:600]
    return {
        "title": title,
        "description": description,
        "h1": ", ".join(h1_tags) if h1_tags else "None",
        "h2": ", ".join(h2_tags) if h2_tags else "None",
        "body_preview": body_text,
    }


# ------------------ MAIN ENTRY ------------------

def scrape(url: str) -> Dict:
    api_result = fetch_jobicy_api(url) or fetch_remoteok_api(url)
    if api_result:
        return api_result

    try:
        html = fetch_page(url)
    except requests.exceptions.Timeout:
        raise ValueError(f"Request timed out after {TIMEOUT}s. Try a different URL.")
    except requests.exceptions.ConnectionError:
        raise ValueError("Could not connect. Check the URL and your internet connection.")
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        if code == 403:
            raise ValueError("HTTP 403: This site blocks scrapers. Try RemoteOK, Jobicy, or Himalayas.")
        raise ValueError(f"HTTP Error {code}: {e.response.reason}")
    except Exception as e:
        raise ValueError(f"Failed to fetch page: {str(e)}")

    jobs = extract_jobs(html, base_url=url)
    page_summary = get_page_summary(html)
    return {"jobs": jobs, "page_summary": page_summary}