"""
main.py — FastAPI backend for AI Web Scraper
Run with:  uvicorn main:app --reload
API Docs:  http://127.0.0.1:8000/docs
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import anthropic

from scraper import scrape


# ── App setup ─────────────────────────────────────────────
app = FastAPI(
    title="AI Web Scraper API",
    description="Scrapes a URL for links and generates AI analysis using Claude.",
    version="1.0.0",
)

# Allow requests from the frontend (any localhost port during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Anthropic client ───────────────────────────────────────
# Set your API key as an environment variable:
#   Windows:  set ANTHROPIC_API_KEY=sk-ant-...
#   Linux/Mac: export ANTHROPIC_API_KEY=sk-ant-...
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ── Request & Response schemas ─────────────────────────────
class ScrapeRequest(BaseModel):
    url: str


class LinkItem(BaseModel):
    text: str
    url: str


class ScrapeResponse(BaseModel):
    url: str
    link_count: int
    links: list[LinkItem]
    ai_analysis: str


# ── AI Analysis helper ─────────────────────────────────────
def generate_ai_analysis(url: str, page_summary: dict, links: list) -> str:
    """
    Send page metadata + link count to Claude and get a structured analysis.
    """
    total = len(links)
    internal = sum(1 for l in links if url.split("/")[2] in l["url"])
    external = total - internal

    prompt = f"""You are an expert web analyst. Analyze this web page and provide a concise intelligence report.

**Page Data:**
- URL: {url}
- Title: {page_summary.get("title", "N/A")}
- Meta Description: {page_summary.get("description", "None")}
- H1 Headings: {page_summary.get("h1", "None")}
- H2 Headings: {page_summary.get("h2", "None")}
- Body Preview: {page_summary.get("body_preview", "None")}

**Link Statistics:**
- Total links found: {total}
- Internal links: {internal}
- External links: {external}

**Sample Links (first 10):**
{chr(10).join(f'- [{l["text"] or "No text"}]({l["url"]})' for l in links[:10])}

Write a clear, structured analysis covering:
1. **Purpose** — What is this page/site about?
2. **Content Summary** — Key topics and themes.
3. **Link Structure** — What do the links reveal about the site's structure?
4. **Notable External References** — Any interesting external domains linked.
5. **Quick Verdict** — One sentence summary of the site's nature.

Use **bold** for section labels. Keep it professional, insightful, and under 300 words.
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ── Routes ─────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "AI Web Scraper API is running.",
        "docs": "http://127.0.0.1:8000/docs",
        "endpoints": ["/scrape"],
    }


@app.post("/scrape", response_model=ScrapeResponse)
def scrape_url(body: ScrapeRequest):
    """
    POST /scrape
    Body: { "url": "https://example.com" }
    Returns extracted links and AI analysis.
    """
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    # Normalize URL
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # 1. Scrape the page
    try:
        result = scrape(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    links = result["links"]
    page_summary = result["page_summary"]

    # 2. Generate AI analysis
    try:
        ai_analysis = generate_ai_analysis(url, page_summary, links)
    except Exception as e:
        # Don't fail the whole request if AI fails
        ai_analysis = f"AI analysis unavailable: {str(e)}"

    return ScrapeResponse(
        url=url,
        link_count=len(links),
        links=[LinkItem(**l) for l in links],
        ai_analysis=ai_analysis,
    )


# ── Dev entry point ────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)