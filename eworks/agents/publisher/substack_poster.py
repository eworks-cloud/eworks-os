"""
Substack publisher via undocumented internal API + SMTP email fallback.

⚠️  WARNING: This module uses Substack's *unofficial* internal REST API
    (the same endpoints their web app calls).  Substack may change or
    remove these endpoints at any time without notice, which would break
    this integration.  Use with caution in production and monitor for
    HTTP 4xx / 5xx responses.

Supported operations
---------------------
- Email/password session login (cookie-based auth)
- Create a draft post
- Update an existing draft
- Publish a draft (optionally send email to subscribers)
- Fetch post stats (views, likes, comments, email opens)
- List recent posts
- SMTP fallback: send post as an email draft when the API is unavailable

Environment variables
---------------------
SUBSTACK_EMAIL               – account email
SUBSTACK_PASSWORD            – account password
SUBSTACK_PUBLICATION_URL     – e.g. "cesarschneider.substack.com"
SMTP_HOST                    – fallback SMTP server (default: smtp.gmail.com)
SMTP_PORT                    – fallback SMTP port   (default: 587)
SMTP_USER                    – fallback SMTP username
SMTP_PASSWORD                – fallback SMTP password
SMTP_FROM                    – fallback sender address
"""
from __future__ import annotations

import logging
import os
import smtplib
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

# ── Constants ──────────────────────────────────────────────────────────────────

_LOGIN_URL = "https://substack.com/api/v1/login"
_SESSION_COOKIE = "substack.sid"
_BODY_PREVIEW_LEN = 500


# ── Table DDL ──────────────────────────────────────────────────────────────────

SUBSTACK_POSTS_DDL = """
CREATE TABLE IF NOT EXISTS substack_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    substack_post_id TEXT UNIQUE,
    title TEXT NOT NULL,
    subtitle TEXT,
    body_preview TEXT,
    post_url TEXT,
    status TEXT CHECK(status IN ('draft','published','failed')) DEFAULT 'draft',
    audience TEXT DEFAULT 'everyone',
    send_email INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    email_opens INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_substack_posts_status ON substack_posts(status);
CREATE INDEX IF NOT EXISTS idx_substack_posts_post_id ON substack_posts(substack_post_id);
"""


class SubstackPoster:
    """
    Posts long-form content to Substack via its internal (undocumented) API.

    Maintains a requests Session so that the session cookie (substack.sid)
    is reused across calls without re-authenticating on every request.

    Falls back to SMTP if the API is unavailable or credentials are missing.
    """

    def __init__(self, db_conn: Optional[sqlite3.Connection] = None):
        self.email = os.environ.get("SUBSTACK_EMAIL", "")
        self.password = os.environ.get("SUBSTACK_PASSWORD", "")
        self.publication_url = os.environ.get("SUBSTACK_PUBLICATION_URL", "").strip().rstrip("/")
        # SMTP fallback
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.smtp_from = os.environ.get("SMTP_FROM", self.smtp_user)

        self.logger = logging.getLogger(self.__class__.__name__)
        self._session: Optional[requests.Session] = None
        self._db = db_conn

        if self._db is not None:
            self._ensure_table()

    # ── DB helpers ─────────────────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        """Create substack_posts table if it doesn't exist."""
        self._db.executescript(SUBSTACK_POSTS_DDL)
        self._db.commit()

    def _save_post(self, data: dict) -> int:
        """Insert a new substack_posts row and return its local id."""
        if self._db is None:
            return -1
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        cur = self._db.execute(
            f"INSERT INTO substack_posts ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self._db.commit()
        return cur.lastrowid

    def _update_post(self, local_id: int, data: dict) -> None:
        """Update an existing substack_posts row."""
        if self._db is None or not data:
            return
        set_clause = ", ".join(f"{k}=?" for k in data)
        self._db.execute(
            f"UPDATE substack_posts SET {set_clause} WHERE id=?",
            list(data.values()) + [local_id],
        )
        self._db.commit()

    def _upsert_post_by_substack_id(self, substack_post_id: str, data: dict) -> None:
        """Upsert a row by substack_post_id (used when syncing stats)."""
        if self._db is None:
            return
        row = self._db.execute(
            "SELECT id FROM substack_posts WHERE substack_post_id=?",
            (substack_post_id,),
        ).fetchone()
        if row:
            set_clause = ", ".join(f"{k}=?" for k in data)
            self._db.execute(
                f"UPDATE substack_posts SET {set_clause} WHERE substack_post_id=?",
                list(data.values()) + [substack_post_id],
            )
        else:
            data["substack_post_id"] = substack_post_id
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            self._db.execute(
                f"INSERT INTO substack_posts ({columns}) VALUES ({placeholders})",
                list(data.values()),
            )
        self._db.commit()

    # ── Configuration helpers ──────────────────────────────────────────────────

    def _is_configured(self) -> bool:
        return bool(self.email and self.password and self.publication_url)

    def _api_base(self) -> str:
        return f"https://{self.publication_url}/api/v1"

    # ── Session / auth ─────────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """Return an authenticated requests Session, logging in if needed."""
        if self._session is not None:
            return self._session
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; EworksOS/1.0)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        # Attempt login to obtain the session cookie
        try:
            resp = session.post(
                _LOGIN_URL,
                json={"email": self.email, "password": self.password, "captcha_response": None},
                timeout=30,
            )
            resp.raise_for_status()
            self.logger.info("Substack login successful for %s", self.email)
        except requests.HTTPError as exc:
            self.logger.error("Substack login failed: %s — %s", exc, exc.response.text[:200])
            raise
        self._session = session
        return self._session

    def logout(self) -> None:
        """Discard the cached session (forces re-login on next call)."""
        self._session = None
        self.logger.debug("Substack session cleared")

    # ── Core API methods ───────────────────────────────────────────────────────

    def create_draft(
        self,
        title: str,
        body_html: str,
        subtitle: Optional[str] = None,
        cover_image_url: Optional[str] = None,
    ) -> str:
        """
        Create a new draft post on Substack.

        Parameters
        ----------
        title           : Post headline.
        body_html       : Full body as HTML.  Supports headers, bold, images, etc.
        subtitle        : Optional deck / preview text shown in email clients.
        cover_image_url : Optional URL to the cover/header image.

        Returns
        -------
        str – The Substack post ID (integer as string).
        """
        if not self._is_configured():
            raise RuntimeError(
                "Substack not configured. Set SUBSTACK_EMAIL, SUBSTACK_PASSWORD, "
                "SUBSTACK_PUBLICATION_URL."
            )
        session = self._get_session()
        payload: dict = {
            "draft_title": title,
            "draft_body": body_html,
            "draft_section_id": None,
            "audience": "everyone",
            "type": "newsletter",
        }
        if subtitle:
            payload["draft_subtitle"] = subtitle
        if cover_image_url:
            payload["cover_image"] = cover_image_url

        resp = session.post(
            f"{self._api_base()}/posts",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        draft_id = str(data.get("id", ""))
        self.logger.info("Substack draft created: id=%s title=%r", draft_id, title)

        # Persist to local DB
        body_preview = _strip_html(body_html)[:_BODY_PREVIEW_LEN]
        self._save_post({
            "substack_post_id": draft_id,
            "title": title,
            "subtitle": subtitle or "",
            "body_preview": body_preview,
            "post_url": data.get("canonical_url", ""),
            "status": "draft",
            "audience": "everyone",
            "send_email": 1,
            "created_at": datetime.utcnow().isoformat(),
        })
        return draft_id

    def update_draft(
        self,
        draft_id: str,
        title: Optional[str] = None,
        body_html: Optional[str] = None,
        subtitle: Optional[str] = None,
        cover_image_url: Optional[str] = None,
    ) -> dict:
        """
        Update an existing draft post.

        Only the fields you pass (non-None) are sent to the API.
        Returns the updated post data dict from Substack.
        """
        if not self._is_configured():
            raise RuntimeError("Substack not configured.")
        session = self._get_session()
        payload: dict = {}
        if title is not None:
            payload["draft_title"] = title
        if body_html is not None:
            payload["draft_body"] = body_html
        if subtitle is not None:
            payload["draft_subtitle"] = subtitle
        if cover_image_url is not None:
            payload["cover_image"] = cover_image_url

        resp = session.put(
            f"{self._api_base()}/posts/{draft_id}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.logger.info("Substack draft updated: id=%s", draft_id)
        return data

    def publish_post(
        self,
        draft_id: str,
        send_email: bool = True,
        audience: str = "everyone",
    ) -> str:
        """
        Publish an existing draft post.

        Parameters
        ----------
        draft_id   : Substack post ID returned by create_draft().
        send_email : Whether to send the post as an email to subscribers.
        audience   : "everyone" (public), "only_paid", or "founding_member".

        Returns
        -------
        str – The canonical URL of the published post.
        """
        if not self._is_configured():
            raise RuntimeError("Substack not configured.")
        session = self._get_session()
        payload = {
            "send_email": send_email,
            "audience": audience,
        }
        resp = session.post(
            f"{self._api_base()}/posts/{draft_id}/publish",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        post_url = data.get("canonical_url", "")
        self.logger.info("Substack post published: %s", post_url)

        # Update local DB record
        if self._db is not None:
            self._db.execute(
                """
                UPDATE substack_posts
                SET status='published', audience=?, send_email=?,
                    post_url=?, published_at=?
                WHERE substack_post_id=?
                """,
                (audience, int(send_email), post_url,
                 datetime.utcnow().isoformat(), draft_id),
            )
            self._db.commit()
        return post_url

    def create_and_publish(
        self,
        title: str,
        body_html: str,
        subtitle: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        send_email: bool = True,
        audience: str = "everyone",
    ) -> str:
        """
        Convenience: create a draft and immediately publish it.

        Returns
        -------
        str – The canonical URL of the published post.
        """
        draft_id = self.create_draft(
            title=title,
            body_html=body_html,
            subtitle=subtitle,
            cover_image_url=cover_image_url,
        )
        post_url = self.publish_post(
            draft_id=draft_id,
            send_email=send_email,
            audience=audience,
        )
        return post_url

    # ── Stats & listing ────────────────────────────────────────────────────────

    def get_post_stats(self, post_id: str) -> dict:
        """
        Fetch engagement stats for a published post.

        Returns a dict with keys: views, likes, comments, email_opens,
        post_id, post_url, status.

        Note: email_opens are only available to publication owners via
        the internal stats endpoint — standard free accounts may receive 0.
        """
        if not self._is_configured():
            return {"status": "needs_auth", "post_id": post_id}
        session = self._get_session()

        # Post detail
        resp = session.get(
            f"{self._api_base()}/posts/{post_id}",
            timeout=30,
        )
        if resp.status_code != 200:
            return {"status": "unavailable", "post_id": post_id}
        detail = resp.json()

        # Comments count
        comments_count = 0
        try:
            c_resp = session.get(
                f"{self._api_base()}/posts/{post_id}/comments",
                params={"all_comments": "true", "limit": 1},
                timeout=30,
            )
            if c_resp.status_code == 200:
                comments_count = c_resp.json().get("total", 0)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Could not fetch comments for post %s: %s", post_id, exc)

        stats = {
            "post_id": post_id,
            "post_url": detail.get("canonical_url", ""),
            "views": detail.get("reads", 0),
            "likes": detail.get("reactions", {}).get("❤", 0) if isinstance(detail.get("reactions"), dict) else detail.get("reaction_count", 0),
            "comments": comments_count,
            "email_opens": detail.get("email_opens", 0),
            "status": "ok",
        }

        # Sync stats back to local DB
        if self._db is not None:
            self._upsert_post_by_substack_id(post_id, {
                "views": stats["views"],
                "likes": stats["likes"],
                "comments_count": stats["comments"],
                "email_opens": stats["email_opens"],
                "post_url": stats["post_url"],
            })
        return stats

    def list_posts(self, limit: int = 10) -> list[dict]:
        """
        Return a list of recent posts from the publication.

        Each item contains: id, title, subtitle, post_url, status,
        published_at, reads, reaction_count.
        """
        if not self._is_configured():
            return []
        session = self._get_session()
        resp = session.get(
            f"{self._api_base()}/posts",
            params={"limit": limit},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        # The endpoint returns either a list or {"posts": [...]}
        items = raw if isinstance(raw, list) else raw.get("posts", [])
        result = []
        for item in items:
            result.append({
                "id": str(item.get("id", "")),
                "title": item.get("title", ""),
                "subtitle": item.get("subtitle", ""),
                "post_url": item.get("canonical_url", ""),
                "status": item.get("draft_status", "published"),
                "published_at": item.get("post_date", ""),
                "reads": item.get("reads", 0),
                "reaction_count": item.get("reaction_count", 0),
            })
        return result

    # ── SMTP email fallback ────────────────────────────────────────────────────

    def send_email_draft(
        self,
        title: str,
        body_html: str,
        recipient: Optional[str] = None,
        subtitle: Optional[str] = None,
    ) -> dict:
        """
        Fallback: send the post as an HTML email via SMTP.

        Useful when the Substack API is unavailable or for sending drafts
        to a preview address before publishing.

        Parameters
        ----------
        title     : Email subject / post title.
        body_html : Full HTML body.
        recipient : Destination address (defaults to SMTP_USER / SUBSTACK_EMAIL).
        subtitle  : Optional subtitle prepended to the body.
        """
        to_addr = recipient or self.smtp_user or self.email
        if not to_addr:
            return {"status": "error", "message": "No recipient address configured"}
        if not self.smtp_user or not self.smtp_password:
            return {"status": "error", "message": "SMTP credentials not configured"}

        subject = f"[Draft] {title}"
        if subtitle:
            body_html = f"<p><em>{subtitle}</em></p>\n<hr/>\n{body_html}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_from or self.smtp_user
        msg["To"] = to_addr
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(msg["From"], [to_addr], msg.as_string())
            self.logger.info("Email draft sent to %s: %r", to_addr, title)
            return {"status": "sent", "recipient": to_addr, "subject": subject}
        except smtplib.SMTPException as exc:
            self.logger.error("SMTP send failed: %s", exc)
            return {"status": "error", "message": str(exc)}


# ── Utilities ──────────────────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Very lightweight HTML tag stripper for body_preview generation."""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
