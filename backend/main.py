"""
main.py — FastAPI backend for AI Web Scraper
Run with:  uvicorn main:app --reload
API Docs:  http://127.0.0.1:8000/docs
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import google.generativeai as genai

from scraper import scrape

# ── App setup ───────────────────────────────────────────────
genai.configure(api_key="AIzaSyB6wH3HFD6esxLXGD4YFXDGYMykmPkow50")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request & Response schemas ──────────────────────────────
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


# ── AI Analysis helper ──────────────────────────────────────
def generate_ai_analysis(url: str, page_summary: dict, links: list) -> str:
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

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


# ── Routes ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "AI Web Scraper API is running.",
        "docs": "http://127.0.0.1:8000/docs",
        "endpoints": ["/scrape"],
    }


@app.post("/scrape", response_model=ScrapeResponse)
def scrape_url(body: ScrapeRequest):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        result = scrape(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    links = result["links"]
    page_summary = result["page_summary"]

    ai_analysis = generate_ai_analysis(url, page_summary, links)

    return ScrapeResponse(
        url=url,
        link_count=len(links),
        links=[LinkItem(**l) for l in links],
        ai_analysis=ai_analysis,
    )


# ── Dev entry point ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)