"""
main.py — Production-ready FastAPI backend for JobMindAI
Auth + DB + Scraping + AI Analysis
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator
from typing import Optional, List

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
except ImportError:
    GEMINI_AVAILABLE = False
    GEMINI_API_KEY = ""

from backend.scraper import scrape
from backend.database import (
    init_db, create_user, authenticate_user, create_session,
    get_user_by_token, delete_session, log_search, get_search_history,
    save_job, get_saved_jobs, update_job_status, delete_saved_job,
    get_user_stats
)

# ---------- INIT ----------
init_db()
app = FastAPI(title="JobMindAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- MODELS ----------

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class ScrapeRequest(BaseModel):
    url: str

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v):
        v = str(v).strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

class SaveJobRequest(BaseModel):
    job: dict
    source_url: str

class UpdateJobRequest(BaseModel):
    status: str
    notes: str = ""

class JobItem(BaseModel):
    title: str
    company: str
    location: str
    salary: str
    url: str

class ScrapeResponse(BaseModel):
    success: bool
    url: str
    job_count: int
    jobs: List[JobItem]
    ai_analysis: Optional[str]
    message: str


# ---------- AUTH DEPENDENCY ----------

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ", 1)[1]
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return user

def get_optional_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    return get_user_by_token(token)


# ---------- AI ANALYSIS ----------

def generate_ai_analysis(url: str, page_summary: dict, jobs: list) -> str:
    if not GEMINI_AVAILABLE:
        return "⚠️ Add GOOGLE_API_KEY to .env to enable AI analysis."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        sample_jobs = "\n".join(
            f'- {j["title"]} @ {j["company"]} ({j["location"]})'
            for j in jobs[:10]
        ) or "No specific jobs extracted."

        prompt = f"""You are a career analyst. Analyze these job listings.

Source: {url}
Page: {page_summary.get("title", "N/A")}
Total Jobs: {len(jobs)}

Listings:
{sample_jobs}

Give a concise analysis (under 180 words):
1. 🔥 Trending roles
2. 🏢 Notable companies/sectors
3. 📍 Location patterns
4. 🛠️ In-demand skills
5. ✅ Verdict for job seekers

Be specific and actionable."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


# ---------- ERROR HANDLING ----------

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "success": False,
        "message": str(exc.errors()[0].get("msg", "bad input")),
    })


# ---------- ROUTES ----------

@app.get("/")
def root():
    return {"success": True, "message": "JobMindAI API v2 🚀", "gemini": GEMINI_AVAILABLE}

@app.get("/health")
def health():
    return {"status": "ok", "gemini": GEMINI_AVAILABLE}


# -- AUTH --

@app.post("/auth/register")
def register(body: RegisterRequest):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if "@" not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    user = create_user(body.email, body.password, body.name or body.email.split("@")[0])
    if not user:
        raise HTTPException(status_code=409, detail="Email already registered")
    token = create_session(user["id"])
    return {
        "success": True,
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"]}
    }

@app.post("/auth/login")
def login(body: LoginRequest):
    user = authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_session(user["id"])
    return {
        "success": True,
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"]}
    }

@app.post("/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        delete_session(authorization.split(" ", 1)[1])
    return {"success": True}

@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    stats = get_user_stats(user["id"])
    return {
        "success": True,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"]},
        "stats": stats
    }


# -- SCRAPING --

@app.post("/scrape", response_model=ScrapeResponse)
def scrape_url(body: ScrapeRequest, user=Depends(get_optional_user)):
    url = body.url
    try:
        result = scrape(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

    jobs = result.get("jobs", [])
    page_summary = result.get("page_summary", {})
    ai_analysis = generate_ai_analysis(url, page_summary, jobs)

    # Log to DB
    log_search(user["id"] if user else None, url, len(jobs), ai_analysis or "")

    return ScrapeResponse(
        success=True,
        url=url,
        job_count=len(jobs),
        jobs=[JobItem(**j) for j in jobs],
        ai_analysis=ai_analysis,
        message=f"Found {len(jobs)} job(s)" if jobs else "No jobs found — site may block bots or use JS rendering."
    )


# -- HISTORY --

@app.get("/history")
def history(user=Depends(get_current_user)):
    return {"success": True, "history": get_search_history(user["id"])}


# -- SAVED JOBS --

@app.get("/saved")
def get_saved(user=Depends(get_current_user)):
    return {"success": True, "jobs": get_saved_jobs(user["id"])}

@app.post("/saved")
def save(body: SaveJobRequest, user=Depends(get_current_user)):
    job_id = save_job(user["id"], body.job, body.source_url)
    return {"success": True, "id": job_id}

@app.put("/saved/{job_id}")
def update_saved(job_id: int, body: UpdateJobRequest, user=Depends(get_current_user)):
    update_job_status(job_id, user["id"], body.status, body.notes)
    return {"success": True}

@app.delete("/saved/{job_id}")
def delete_saved(job_id: int, user=Depends(get_current_user)):
    delete_saved_job(job_id, user["id"])
    return {"success": True}


# ---------- RUN ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)