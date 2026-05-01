import sqlite3
import hashlib
import secrets
import time
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path("jobmind.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            name        TEXT    NOT NULL DEFAULT '',
            plan        TEXT    NOT NULL DEFAULT 'free',
            created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            searches_today INTEGER NOT NULL DEFAULT 0,
            last_search_date TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token       TEXT    PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            expires_at  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS searches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
            url         TEXT    NOT NULL,
            job_count   INTEGER NOT NULL DEFAULT 0,
            ai_summary  TEXT    DEFAULT '',
            created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS saved_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            company     TEXT    NOT NULL,
            location    TEXT    NOT NULL,
            salary      TEXT    NOT NULL,
            url         TEXT    NOT NULL,
            source_url  TEXT    NOT NULL DEFAULT '',
            saved_at    INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            status      TEXT    NOT NULL DEFAULT 'saved',
            notes       TEXT    DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_token   ON sessions(token);
        CREATE INDEX IF NOT EXISTS idx_searches_user    ON searches(user_id);
        CREATE INDEX IF NOT EXISTS idx_saved_jobs_user  ON saved_jobs(user_id);
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# AUTH
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":", 1)
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
    except Exception:
        return False


def create_user(email: str, password: str, name: str) -> Optional[Dict]:
    conn = get_db()
    try:
        hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email.lower().strip(), hashed, name.strip())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        if row and verify_password(password, row["password"]):
            return dict(row)
        return None
    finally:
        conn.close()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + 7 * 24 * 3600  # 7 days
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires)
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> Optional[Dict]:
    conn = get_db()
    try:
        now = int(time.time())
        row = conn.execute("""
            SELECT u.* FROM users u
            JOIN sessions s ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# SEARCHES
def log_search(user_id: Optional[int], url: str, job_count: int, ai_summary: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO searches (user_id, url, job_count, ai_summary) VALUES (?, ?, ?, ?)",
        (user_id, url, job_count, ai_summary or "")
    )
    conn.commit()
    search_id = cur.lastrowid

    if user_id:
        today = time.strftime("%Y-%m-%d")
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user:
            if user["last_search_date"] != today:
                conn.execute("UPDATE users SET searches_today = 1, last_search_date = ? WHERE id = ?", (today, user_id))
            else:
                conn.execute("UPDATE users SET searches_today = searches_today + 1 WHERE id = ?", (user_id,))
        conn.commit()

    conn.close()
    return search_id


def get_search_history(user_id: int, limit: int = 20) -> List[Dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM searches WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
    
# SAVED JOBS
def save_job(user_id: int, job: Dict, source_url: str) -> Optional[int]:
    conn = get_db()
    try:
        cur = conn.execute("""
            INSERT INTO saved_jobs (user_id, title, company, location, salary, url, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, job["title"], job["company"], job["location"],
              job["salary"], job["url"], source_url))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_saved_jobs(user_id: int) -> List[Dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM saved_jobs WHERE user_id = ? ORDER BY saved_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(job_id: int, user_id: int, status: str, notes: str = ""):
    conn = get_db()
    conn.execute(
        "UPDATE saved_jobs SET status = ?, notes = ? WHERE id = ? AND user_id = ?",
        (status, notes, job_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_saved_job(job_id: int, user_id: int):
    conn = get_db()
    conn.execute("DELETE FROM saved_jobs WHERE id = ? AND user_id = ?", (job_id, user_id))
    conn.commit()
    conn.close()


def get_user_stats(user_id: int) -> Dict:
    conn = get_db()
    searches = conn.execute("SELECT COUNT(*) as c FROM searches WHERE user_id = ?", (user_id,)).fetchone()["c"]
    saved = conn.execute("SELECT COUNT(*) as c FROM saved_jobs WHERE user_id = ?", (user_id,)).fetchone()["c"]
    applied = conn.execute(
        "SELECT COUNT(*) as c FROM saved_jobs WHERE user_id = ? AND status = 'applied'", (user_id,)
    ).fetchone()["c"]
    conn.close()
    return {"total_searches": searches, "saved_jobs": saved, "applied": applied}
