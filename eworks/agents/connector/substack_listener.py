"""
Substack comment listener for the Connector agent.

⚠️  WARNING: This module uses Substack's *unofficial* internal REST API
    (the same endpoints their web app calls). Substack may change or
    remove these endpoints at any time without notice. Monitor for
    HTTP 4xx / 5xx responses.

Polling strategy
----------------
Substack has no webhook / push API, so we poll on a schedule:
  1. Fetch the most recent posts (last 30 days) via
     GET /api/v1/posts?limit=20
  2. For each post, fetch its comment thread via
     GET /api/v1/posts/{post_id}/comments
  3. De-duplicate against the local ``social_interactions`` table
     (checked via the optional *db* handle passed to scan()).

Environment variables
---------------------
SUBSTACK_EMAIL            – account email address
SUBSTACK_PASSWORD         – account password
SUBSTACK_PUBLICATION_URL  – publication host, e.g. "cesarschneider.substack.com"
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

# ── Constants ─────────────────────────────────────────────────────────────────

_LOGIN_URL = "https://substack.com/api/v1/login"
_SESSION_COOKIE = "substack.sid"
_POST_WINDOW_DAYS = 30  # Only inspect posts published within this window
_REQUEST_TIMEOUT = 30   # seconds


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string; return None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ── Listener class ─────────────────────────────────────────────────────────────

class SubstackListener:
    """
    Polls a Substack publication for new reader comments and surfaces them
    as normalised interaction dicts compatible with the Connector orchestrator.

    Session / auth
    ~~~~~~~~~~~~~~
    The first API call triggers an email+password login that stores the
    ``substack.sid`` cookie inside a ``requests.Session``.  Subsequent calls
    reuse the same session without re-authenticating.

    De-duplication
    ~~~~~~~~~~~~~~
    If a *db* handle (the project's ``Database`` object) is supplied to
    :meth:`scan`, each comment is checked against ``social_interactions``
    (platform + external_id) before being included in the result set so that
    only *new* comments are returned.
    """

    def __init__(self) -> None:
        self.email = os.environ.get("SUBSTACK_EMAIL", "")
        self.password = os.environ.get("SUBSTACK_PASSWORD", "")
        self.publication_url = (
            os.environ.get("SUBSTACK_PUBLICATION_URL", "").strip().rstrip("/")
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self._session: Optional[requests.Session] = None

    # ── Configuration ──────────────────────────────────────────────────────────

    def _is_configured(self) -> bool:
        return bool(self.email and self.password and self.publication_url)

    def _api_base(self) -> str:
        return f"https://{self.publication_url}/api/v1"

    # ── Session / auth ─────────────────────────────────────────────────────────

    def _get_session(self) -> Optional[requests.Session]:
        """Return a cached authenticated session, logging in if necessary."""
        if self._session is not None:
            return self._session

        if not self._is_configured():
            self.logger.warning(
                "Substack not configured — set SUBSTACK_EMAIL, SUBSTACK_PASSWORD, "
                "SUBSTACK_PUBLICATION_URL"
            )
            return None

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; EworksOS/1.0)",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        try:
            resp = session.post(
                _LOGIN_URL,
                json={
                    "email": self.email,
                    "password": self.password,
                    "captcha_response": None,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            self.logger.info("Substack login successful for %s", self.email)
        except requests.HTTPError as exc:
            self.logger.error(
                "Substack login failed: %s — %s",
                exc,
                getattr(exc.response, "text", "")[:200],
            )
            return None
        except requests.RequestException as exc:
            self.logger.error("Substack login network error: %s", exc)
            return None

        self._session = session
        return self._session

    def logout(self) -> None:
        """Discard the cached session (forces re-login on the next call)."""
        self._session = None
        self.logger.debug("Substack session cleared")

    # ── API helpers ────────────────────────────────────────────────────────────

    def get_recent_posts(self, limit: int = 20) -> list[dict]:
        """
        Return recent posts published within the last *_POST_WINDOW_DAYS* days.

        Each item contains: id, title, slug, post_date, canonical_url.
        """
        session = self._get_session()
        if session is None:
            return []

        try:
            resp = session.get(
                f"{self._api_base()}/posts",
                params={"limit": limit},
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error("Substack posts fetch failed: %s", exc)
            return []

        raw = resp.json()
        # Endpoint returns either a list or {"posts": [...]}
        items: list = raw if isinstance(raw, list) else raw.get("posts", [])

        cutoff = _utcnow() - timedelta(days=_POST_WINDOW_DAYS)
        posts: list[dict] = []
        for item in items:
            published = _parse_iso(item.get("post_date", ""))
            if published is None:
                continue
            # Ensure tz-aware comparison
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue  # Too old — stop (posts are returned newest-first)
            posts.append(
                {
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "slug": item.get("slug", ""),
                    "post_date": item.get("post_date", ""),
                    "canonical_url": item.get("canonical_url", ""),
                }
            )
        return posts

    def get_comments(self, post_id: str) -> list[dict]:
        """
        Return all comments (including nested replies) for a single post.

        Each raw comment dict preserves the full Substack payload plus a
        synthesised ``_post_id`` key so callers can correlate back to the post.
        """
        session = self._get_session()
        if session is None:
            return []

        try:
            resp = session.get(
                f"{self._api_base()}/posts/{post_id}/comments",
                params={"all_comments": "true", "limit": 100},
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error(
                "Substack comments fetch failed for post %s: %s", post_id, exc
            )
            return []

        data = resp.json()

        # The API may wrap comments under a "comments" key or return a list
        if isinstance(data, list):
            raw_comments = data
        elif isinstance(data, dict):
            raw_comments = data.get("comments", [])
        else:
            raw_comments = []

        # Flatten top-level comments and their children into one list
        flat: list[dict] = []
        for comment in raw_comments:
            comment["_post_id"] = post_id
            flat.append(comment)
            for child in comment.get("children", []):
                child["_post_id"] = post_id
                flat.append(child)

        return flat

    def reply_to_comment(self, post_id: str, comment_id: str, text: str) -> dict:
        """
        Post a reply to a Substack comment.

        Parameters
        ----------
        post_id    : Substack post ID (integer-as-string).
        comment_id : ID of the comment to reply to.
        text       : Reply body (plain text; max ~5 000 chars advised).

        Returns
        -------
        dict with keys ``reply_id`` and ``status``.
        """
        session = self._get_session()
        if session is None:
            return {"status": "needs_auth"}

        try:
            resp = session.post(
                f"{self._api_base()}/posts/{post_id}/comments",
                json={
                    "body": text[:5000],
                    "parent_comment_id": int(comment_id),
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            reply_id = str(data.get("id", ""))
            self.logger.info(
                "Replied to Substack comment %s on post %s → reply_id=%s",
                comment_id,
                post_id,
                reply_id,
            )
            return {"reply_id": reply_id, "status": "replied"}
        except requests.RequestException as exc:
            self.logger.error("Substack reply failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    # ── De-duplication helper ──────────────────────────────────────────────────

    def _is_seen(self, db, external_id: str) -> bool:
        """
        Return True if this comment has already been recorded in
        ``social_interactions`` (connector_seen dedup).
        """
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM social_interactions "
                    "WHERE platform='substack' AND external_id=?",
                    (external_id,),
                ).fetchone()
            return row is not None
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Dedup check failed for %s: %s", external_id, exc)
            return False  # Safer to process than to silently skip

    # ── Main scan ──────────────────────────────────────────────────────────────

    def scan(self, db=None) -> list[dict]:
        """
        Full poll: fetch comments on all posts published in the last 30 days.

        Parameters
        ----------
        db : optional Database instance (eworks.core.database.Database).
             When supplied, already-seen comments are filtered out via the
             ``social_interactions`` table (connector_seen dedup).

        Returns
        -------
        List of normalised interaction dicts ready for the Connector
        orchestrator.  Each dict contains:

        platform, interaction_type, external_id, author_id, author_username,
        author_name, content, parent_id, url, created_at, raw.
        """
        if not self._is_configured():
            self.logger.warning(
                "Substack listener not configured — skipping scan"
            )
            return []

        posts = self.get_recent_posts(limit=20)
        if not posts:
            self.logger.info("No recent Substack posts found")
            return []

        interactions: list[dict] = []

        for post in posts:
            post_id = post["id"]
            post_slug = post.get("slug", post_id)
            canonical_url = post.get("canonical_url", "")
            # Fall back to constructing the URL if the API didn't supply it
            if not canonical_url:
                canonical_url = f"https://{self.publication_url}/p/{post_slug}"

            try:
                comments = self.get_comments(post_id)
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Failed to fetch comments for post %s: %s", post_id, exc
                )
                continue

            for comment in comments:
                comment_id = str(comment.get("id", ""))
                if not comment_id:
                    continue

                # ── De-duplicate against connector_seen (social_interactions) ──
                if db is not None and self._is_seen(db, comment_id):
                    continue

                # ── Extract author info ────────────────────────────────────────
                user = comment.get("user") or {}
                author_id = str(comment.get("user_id") or user.get("id", ""))
                author_name = (
                    comment.get("user_name")
                    or user.get("name")
                    or user.get("username")
                    or ""
                )

                # ── Extract body ───────────────────────────────────────────────
                body = comment.get("body") or comment.get("body_json_string") or ""
                if not body:
                    continue  # Skip empty comments

                # ── Parent: top-level → post, nested → parent comment ──────────
                raw_parent = comment.get("parent_comment_id")
                parent_id = str(raw_parent) if raw_parent else post_id

                # ── Timestamps ────────────────────────────────────────────────
                created_at = comment.get("created_at", "")
                if not created_at:
                    created_at = _utcnow().isoformat()

                # ── Build URL with fragment anchor ─────────────────────────────
                url = f"{canonical_url}#{comment_id}"

                interactions.append(
                    {
                        "platform": "substack",
                        "interaction_type": "comment",
                        "external_id": comment_id,
                        "author_id": author_id,
                        "author_username": author_name,
                        "author_name": author_name,
                        "content": body,
                        "parent_id": parent_id,
                        "url": url,
                        "created_at": created_at,
                        "raw": comment,
                    }
                )

            # Be polite to the Substack API between posts
            time.sleep(0.5)

        self.logger.info(
            "Substack scan complete — %d new interaction(s) across %d post(s)",
            len(interactions),
            len(posts),
        )
        return interactions
