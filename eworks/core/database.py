"""SQLite database manager for Eworks OS."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT CHECK(status IN ('draft','active','paused','completed')) DEFAULT 'draft',
    daily_limit INTEGER DEFAULT 20,
    total_sent INTEGER DEFAULT 0,
    total_replies INTEGER DEFAULT 0,
    icp_config TEXT,
    message_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linkedin_url TEXT UNIQUE NOT NULL,
    full_name TEXT,
    headline TEXT,
    company TEXT,
    location TEXT,
    connections_count INTEGER,
    mutual_connections INTEGER DEFAULT 0,
    icp_score REAL DEFAULT 0.0,
    icp_breakdown TEXT,
    status TEXT CHECK(status IN ('discovered','scored','queued','contacted','replied','meeting_booked','not_interested','dnc')) DEFAULT 'discovered',
    campaign_id INTEGER REFERENCES campaigns(id),
    notes TEXT,
    raw_data TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contacted_at TIMESTAMP,
    replied_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    campaign_id INTEGER REFERENCES campaigns(id),
    message_type TEXT CHECK(message_type IN ('connection_request','inmail','follow_up')) DEFAULT 'connection_request',
    subject TEXT,
    body TEXT NOT NULL,
    status TEXT CHECK(status IN ('draft','sent','delivered','read','replied','failed')) DEFAULT 'draft',
    sent_at TIMESTAMP,
    replied_at TIMESTAMP,
    reply_text TEXT,
    generation_model TEXT,
    generation_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    payload TEXT,
    status TEXT CHECK(status IN ('pending','running','done','failed')) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    campaign_id INTEGER REFERENCES campaigns(id),
    status TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    prospects_scanned INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    linkedin_url TEXT,
    tone TEXT DEFAULT 'professional',
    language TEXT DEFAULT 'en',
    signature TEXT,
    offer_summary TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS linkedin_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    session_file TEXT,
    status TEXT CHECK(status IN ('active','restricted','banned','needs_reauth')) DEFAULT 'active',
    daily_connection_requests_sent INTEGER DEFAULT 0,
    daily_messages_sent INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings_store (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_campaign ON prospects(campaign_id);
CREATE INDEX IF NOT EXISTS idx_prospects_icp_score ON prospects(icp_score);
CREATE INDEX IF NOT EXISTS idx_messages_prospect ON messages(prospect_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status, priority);
CREATE INDEX IF NOT EXISTS idx_agent_runs_campaign ON agent_runs(campaign_id);
"""

CLOSER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    linkedin_url TEXT,
    phone TEXT,
    prospect_id INTEGER REFERENCES prospects(id),
    status TEXT CHECK(status IN ('lead','discovery','proposal_sent','negotiating','won','lost','churned')) DEFAULT 'lead',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discovery_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    call_date TIMESTAMP,
    raw_notes TEXT NOT NULL,
    extracted_requirements TEXT,
    pain_points TEXT,
    budget_range TEXT,
    timeline TEXT,
    decision_makers TEXT,
    tech_stack TEXT,
    status TEXT CHECK(status IN ('notes_taken','processed','proposal_generated')) DEFAULT 'notes_taken',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    discovery_call_id INTEGER REFERENCES discovery_calls(id),
    title TEXT NOT NULL,
    executive_summary TEXT,
    scope_of_work TEXT,
    timeline_weeks INTEGER,
    total_price REAL,
    pricing_breakdown TEXT,
    markdown_content TEXT,
    pdf_path TEXT,
    status TEXT CHECK(status IN ('draft','sent','viewed','accepted','rejected','expired')) DEFAULT 'draft',
    valid_until TIMESTAMP,
    sent_at TIMESTAMP,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_proposals_client ON proposals(client_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_discovery_calls_client ON discovery_calls(client_id);
"""


class DatabaseManager:
    """Manages the SQLite database connection and schema for Eworks OS."""

    def __init__(self, db_path: str = "data/eworks.db"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def get_connection(self) -> sqlite3.Connection:
        """Return (or create) the database connection."""
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            logger.debug("Connected to database: %s", self.db_path)
        return self._conn

    def init_schema(self) -> None:
        """Create all tables and indexes if they don't exist."""
        conn = self.get_connection()
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logger.info("Database schema initialized at %s", self.db_path)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed")

    # ─── Prospect helpers ─────────────────────────────────────────────────────

    def get_prospect_by_linkedin_url(self, url: str) -> dict[str, Any] | None:
        """Return a prospect row as a dict, or None if not found."""
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM prospects WHERE linkedin_url = ?", (url,)
        ).fetchone()
        return dict(row) if row else None

    def upsert_prospect(self, data: dict[str, Any]) -> int:
        """Insert or update a prospect. Returns the prospect ID."""
        conn = self.get_connection()
        existing = self.get_prospect_by_linkedin_url(data["linkedin_url"])
        if existing:
            fields = {k: v for k, v in data.items() if k != "linkedin_url"}
            if fields:
                set_clause = ", ".join(f"{k}=?" for k in fields)
                values = list(fields.values()) + [data["linkedin_url"]]
                conn.execute(
                    f"UPDATE prospects SET {set_clause} WHERE linkedin_url=?",
                    values,
                )
                conn.commit()
            return existing["id"]
        else:
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            cur = conn.execute(
                f"INSERT INTO prospects ({columns}) VALUES ({placeholders})",
                list(data.values()),
            )
            conn.commit()
            return cur.lastrowid

    # ─── Task queue helpers ───────────────────────────────────────────────────

    def get_pending_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return pending tasks ordered by priority then creation time."""
        conn = self.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM task_queue
            WHERE status = 'pending' AND attempts < max_attempts
            ORDER BY priority ASC, created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_task_status(
        self,
        task_id: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update task status and optionally record an error."""
        conn = self.get_connection()
        now = datetime.utcnow().isoformat()
        if status in ("done", "failed"):
            conn.execute(
                "UPDATE task_queue SET status=?, completed_at=?, error_message=? WHERE id=?",
                (status, now, error_message, task_id),
            )
        elif status == "running":
            conn.execute(
                "UPDATE task_queue SET status=?, started_at=?, attempts=attempts+1 WHERE id=?",
                (status, now, task_id),
            )
        else:
            conn.execute(
                "UPDATE task_queue SET status=? WHERE id=?",
                (status, task_id),
            )
        conn.commit()

    # ─── Agent run helpers ────────────────────────────────────────────────────

    def log_agent_run(self, data: dict[str, Any]) -> int:
        """Insert an agent run record and return its ID."""
        conn = self.get_connection()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        cur = conn.execute(
            f"INSERT INTO agent_runs ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid

    def update_agent_run(self, run_id: int, data: dict[str, Any]) -> None:
        """Update an existing agent run record."""
        conn = self.get_connection()
        set_clause = ", ".join(f"{k}=?" for k in data)
        conn.execute(
            f"UPDATE agent_runs SET {set_clause} WHERE id=?",
            list(data.values()) + [run_id],
        )
        conn.commit()

    # ─── Campaign helpers ─────────────────────────────────────────────────────

    def get_campaign(self, campaign_id: int) -> dict[str, Any] | None:
        """Return a campaign by ID."""
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM campaigns WHERE id=?", (campaign_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_campaigns(self) -> list[dict[str, Any]]:
        """Return all campaigns."""
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def create_campaign(self, data: dict[str, Any]) -> int:
        """Create a new campaign and return its ID."""
        conn = self.get_connection()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        cur = conn.execute(
            f"INSERT INTO campaigns ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid

    def update_campaign(self, campaign_id: int, data: dict[str, Any]) -> None:
        """Update a campaign."""
        data["updated_at"] = datetime.utcnow().isoformat()
        conn = self.get_connection()
        set_clause = ", ".join(f"{k}=?" for k in data)
        conn.execute(
            f"UPDATE campaigns SET {set_clause} WHERE id=?",
            list(data.values()) + [campaign_id],
        )
        conn.commit()

    # ─── Settings helpers ─────────────────────────────────────────────────────

    def add_closer_tables(self) -> None:
        """Create closer/proposal pipeline tables if they don't exist."""
        conn = self.get_connection()
        conn.executescript(CLOSER_SCHEMA_SQL)
        conn.commit()
        logger.info("Closer tables initialized")

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Return a settings value by key."""
        conn = self.get_connection()
        row = conn.execute(
            "SELECT value FROM settings_store WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Upsert a settings value."""
        conn = self.get_connection()
        conn.execute(
            """
            INSERT INTO settings_store (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, value, datetime.utcnow().isoformat()),
        )
        conn.commit()

    # ─── Publisher / Content Pipeline helpers ────────────────────────────────

    def add_publisher_tables(self) -> None:
        """Create content pipeline tables if they don't exist."""
        conn = self.get_connection()
        conn.executescript("""
CREATE TABLE IF NOT EXISTS content_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    hook TEXT,
    angle TEXT,
    keywords TEXT,
    format TEXT CHECK(format IN ('long-form','reel','both')) DEFAULT 'both',
    language TEXT DEFAULT 'en',
    status TEXT CHECK(status IN ('draft','approved','scripted','produced','published','rejected')) DEFAULT 'draft',
    campaign_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER NOT NULL REFERENCES content_ideas(id),
    youtube_script TEXT,
    reel_script TEXT,
    youtube_title TEXT,
    youtube_description TEXT,
    instagram_caption TEXT,
    tags TEXT,
    language TEXT DEFAULT 'en',
    status TEXT CHECK(status IN ('draft','approved','rejected')) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL REFERENCES content_scripts(id),
    platform TEXT CHECK(platform IN ('youtube','instagram','both')),
    heygen_video_id TEXT,
    heygen_video_url TEXT,
    local_video_path TEXT,
    youtube_video_id TEXT,
    youtube_url TEXT,
    instagram_post_id TEXT,
    instagram_url TEXT,
    audio_path TEXT,
    status TEXT CHECK(status IN ('pending','generating','ready','approved','posting','posted','failed')) DEFAULT 'pending',
    approval_message_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_ideas_status ON content_ideas(status);
CREATE INDEX IF NOT EXISTS idx_content_scripts_idea ON content_scripts(idea_id);
CREATE INDEX IF NOT EXISTS idx_content_posts_script ON content_posts(script_id);
CREATE INDEX IF NOT EXISTS idx_content_posts_status ON content_posts(status);
        """)
        conn.commit()
        logger.info("Publisher tables initialized")

    def get_content_idea(self, idea_id: int) -> dict[str, Any] | None:
        """Return a content idea by ID."""
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM content_ideas WHERE id=?", (idea_id,)).fetchone()
        return dict(row) if row else None

    def list_content_ideas(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Return content ideas, optionally filtered by status."""
        conn = self.get_connection()
        if status:
            rows = conn.execute(
                "SELECT * FROM content_ideas WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM content_ideas ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_content_script(self, script_id: int) -> dict[str, Any] | None:
        """Return a content script by ID."""
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM content_scripts WHERE id=?", (script_id,)).fetchone()
        return dict(row) if row else None

    def get_script_by_idea(self, idea_id: int) -> dict[str, Any] | None:
        """Return the latest script for a given idea."""
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM content_scripts WHERE idea_id=? ORDER BY created_at DESC LIMIT 1",
            (idea_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_content_post(self, post_id: int) -> dict[str, Any] | None:
        """Return a content post by ID."""
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM content_posts WHERE id=?", (post_id,)).fetchone()
        return dict(row) if row else None

    def list_content_posts(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Return content posts, optionally filtered by status."""
        conn = self.get_connection()
        if status:
            rows = conn.execute(
                "SELECT * FROM content_posts WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM content_posts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def update_content_post(self, post_id: int, data: dict[str, Any]) -> None:
        """Update a content post record."""
        conn = self.get_connection()
        set_clause = ", ".join(f"{k}=?" for k in data)
        conn.execute(
            f"UPDATE content_posts SET {set_clause} WHERE id=?",
            list(data.values()) + [post_id],
        )
        conn.commit()
