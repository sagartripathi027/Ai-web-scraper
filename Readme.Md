# ⚡ JobMind AI — Intelligent Job Discovery Platform

An AI-powered job scraper with authentication, persistent storage, and Gemini AI analysis.

---

## 🏗️ Architecture

```
ai-job-scraper/
├── backend/
│   ├── __init__.py
│   ├── main.py        ← FastAPI app (auth + routes)
│   ├── scraper.py     ← Web scraping engine
│   └── database.py    ← SQLite ORM (users, sessions, jobs, history)
├── frontend/
│   └── index.html     ← Full SPA (auth, search, saved, history, profile)
├── deploy/
│   └── nginx.conf     ← Nginx reverse proxy config
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (Local Dev)

### 1. Clone & install

```bash
cd "ai-job-scraper"
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
# Get a free key at: https://aistudio.google.com
```

### 3. Start the backend

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Open the frontend

Just open `frontend/index.html` in your browser — no build step needed!

Or serve it with Python:
```bash
cd frontend
python -m http.server 3000
# Then open http://localhost:3000
```

---

## 🐳 Docker Deployment (Recommended)

```bash
# Copy and fill in your API key
cp .env.example .env

# Build and run everything
docker-compose up -d

# Frontend: http://localhost:3000
# API:      http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## ☁️ Deploy to Railway / Render / Fly.io

### Railway (easiest)
1. Push repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add env var: `GOOGLE_API_KEY=your_key`
4. Done — Railway auto-detects the Dockerfile

### Render
1. New Web Service → Connect GitHub repo
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add env vars

### Fly.io
```bash
fly launch
fly secrets set GOOGLE_API_KEY=your_key
fly deploy
```

---

## 🔌 API Reference

All endpoints at `http://localhost:8000`. Interactive docs at `/docs`.

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Sign in → returns token |
| POST | `/auth/logout` | Invalidate token |
| GET  | `/auth/me` | Current user + stats |

### Scraping
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scrape` | Scrape URL (+ AI analysis) |
| GET  | `/history` | Search history (auth required) |

### Saved Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/saved` | List saved jobs |
| POST | `/saved` | Save a job |
| PUT  | `/saved/{id}` | Update status/notes |
| DELETE | `/saved/{id}` | Remove job |

---

## 🔑 Auth Flow

Uses simple token-based auth stored in localStorage:
1. Register/Login → server returns a 7-day session token
2. Token stored in `localStorage` as `jm_token`
3. Sent as `Authorization: Bearer <token>` header on all requests
4. Passwords hashed with SHA-256 + random salt

---

## 🗄️ Database Schema

SQLite (`jobmind.db`) with 4 tables:

- **users** — email, hashed password, name, plan
- **sessions** — bearer tokens with expiry
- **searches** — search history per user
- **saved_jobs** — saved listings with status tracking (saved → applied → interview → offer/rejected)

---

## 🌐 Supported Job Boards

| Site | Method | Quality |
|------|--------|---------|
| jobicy.com | Official API | ⭐⭐⭐ |
| remoteok.com | Official API | ⭐⭐⭐ |
| himalayas.app | HTML scraping | ⭐⭐ |
| weworkremotely.com | HTML scraping | ⭐⭐ |
| Any job board | HTML fallback | ⭐ |

> **Note**: Sites like LinkedIn and Indeed actively block scrapers. Use the supported sites above for best results.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLite, BeautifulSoup4, Gemini AI
- **Frontend**: Vanilla HTML/CSS/JS (no framework, no build step)
- **Auth**: Token-based sessions, SHA-256 password hashing
- **Deployment**: Docker + Nginx