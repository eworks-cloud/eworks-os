"""
Meta Threads reply and mention listener.

Polls for new replies on recent posts and @mention threads every 15 minutes.
Env vars required:
  THREADS_ACCESS_TOKEN  — long-lived user access token
  THREADS_USER_ID       — numeric Threads user ID

Deduplication is done against the connector_seen table
(columns: platform, external_id, seen_at).  When a DB handle is supplied
to fetch_interactions() the method records each returned interaction as
seen and skips any that were already recorded.  Without a DB handle it
falls back to time-window filtering (since_minutes), the same approach
used by InstagramListener.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List

import aiohttp

THREADS_API = "https://graph.threads.net/v1.0"

# Fields fetched for every thread object
_POST_FIELDS = "id,text,timestamp,username,media_type,permalink"
_REPLY_FIELDS = "id,text,timestamp,username"


class ThreadsListener:
    """Listener for Meta Threads replies and mentions."""

    def __init__(self) -> None:
        self.access_token: str = os.environ.get("THREADS_ACCESS_TOKEN", "")
        self.user_id: str = os.environ.get("THREADS_USER_ID", "")
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Low-level API helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        session: aiohttp.ClientSession,
        path: str,
        params: dict | None = None,
    ) -> dict:
        """Execute a GET against the Threads Graph API and return parsed JSON."""
        base_params = {"access_token": self.access_token}
        if params:
            base_params.update(params)
        url = f"{THREADS_API}/{path}"
        async with session.get(url, params=base_params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                text = await resp.text()
                self.logger.warning("Threads API %s → %s: %s", url, resp.status, text[:200])
                return {}
            return await resp.json()

    async def get_recent_posts(
        self,
        session: aiohttp.ClientSession,
        limit: int = 10,
    ) -> list[dict]:
        """Return the most recent Threads posts for the authenticated user."""
        data = await self._get(
            session,
            f"{self.user_id}/threads",
            params={"fields": _POST_FIELDS, "limit": limit},
        )
        return data.get("data", [])

    async def get_replies(
        self,
        session: aiohttp.ClientSession,
        thread_id: str,
    ) -> list[dict]:
        """Return all direct replies to a given thread post."""
        data = await self._get(
            session,
            f"{thread_id}/replies",
            params={"fields": _REPLY_FIELDS},
        )
        return data.get("data", [])

    async def get_mentions(
        self,
        session: aiohttp.ClientSession,
        limit: int = 25,
    ) -> list[dict]:
        """Return recent threads in which the account is @mentioned."""
        # The Threads API surfaces @mentions as reply-type posts where the
        # owner wasn't the original author.  We query the user's own thread
        # list with the reply_to_id expansion to surface mention contexts.
        data = await self._get(
            session,
            f"{self.user_id}/threads",
            params={
                "fields": "id,text,timestamp,username,replied_to",
                "limit": limit,
            },
        )
        posts = data.get("data", [])
        # Keep only posts that are replies *to someone else* — these are
        # mentions or conversations started by other users.
        mentions = [p for p in posts if p.get("replied_to")]
        return mentions

    # ------------------------------------------------------------------
    # Cutoff helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ts(ts_str: str) -> datetime | None:
        """Parse an ISO-8601 timestamp returned by the Threads API."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _is_recent(ts_str: str, cutoff: datetime) -> bool:
        """Return True if the timestamp is at or after the cutoff."""
        ts = ThreadsListener._parse_ts(ts_str)
        if ts is None:
            return True  # be inclusive when timestamp is unparseable
        # Make cutoff tz-aware if the parsed ts carries tz info
        if ts.tzinfo is not None and cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        return ts >= cutoff

    # ------------------------------------------------------------------
    # Interaction builders
    # ------------------------------------------------------------------

    @staticmethod
    def _post_url(username: str, post_id: str) -> str:
        """Canonical Threads URL for a post."""
        if username:
            return f"https://www.threads.net/@{username}/post/{post_id}"
        return f"https://www.threads.net/t/{post_id}"

    def _build_reply_interaction(
        self,
        reply: dict,
        parent_post: dict,
    ) -> dict:
        """Map a raw Threads reply object to the standard interaction schema."""
        username = reply.get("username", "")
        return {
            "platform": "threads",
            "interaction_type": "reply",
            "external_id": reply["id"],
            "parent_id": parent_post["id"],
            "author_id": username,
            "author_username": username,
            "author_name": username,
            "content": reply.get("text", ""),
            "url": self._post_url(
                parent_post.get("username", ""), parent_post["id"]
            ),
            "created_at": reply.get("timestamp", ""),
            "raw": reply,
        }

    def _build_mention_interaction(self, mention: dict) -> dict:
        """Map a raw Threads mention/reply object to the standard interaction schema."""
        username = mention.get("username", "")
        replied_to = mention.get("replied_to", {})
        parent_id = replied_to.get("id", mention["id"]) if isinstance(replied_to, dict) else mention["id"]
        return {
            "platform": "threads",
            "interaction_type": "mention",
            "external_id": mention["id"],
            "parent_id": parent_id,
            "author_id": username,
            "author_username": username,
            "author_name": username,
            "content": mention.get("text", ""),
            "url": self._post_url(username, mention["id"]),
            "created_at": mention.get("timestamp", ""),
            "raw": mention,
        }

    # ------------------------------------------------------------------
    # Deduplication against connector_seen (optional DB helper)
    # ------------------------------------------------------------------

    @staticmethod
    def _mark_seen(db, platform: str, external_id: str) -> None:
        """Record an interaction in connector_seen so it won't be re-fetched."""
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO connector_seen (platform, external_id, seen_at)
                    VALUES (?, ?, ?)""",
                    (platform, external_id, datetime.utcnow().isoformat()),
                )
        except Exception as exc:  # pragma: no cover
            logging.getLogger("ThreadsListener").warning(
                "connector_seen write failed: %s", exc
            )

    @staticmethod
    def _is_seen(db, platform: str, external_id: str) -> bool:
        """Return True if this external_id is already in connector_seen."""
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM connector_seen WHERE platform=? AND external_id=?",
                    (platform, external_id),
                ).fetchone()
            return row is not None
        except Exception as exc:  # pragma: no cover
            logging.getLogger("ThreadsListener").warning(
                "connector_seen read failed: %s", exc
            )
            return False

    # ------------------------------------------------------------------
    # Core scan
    # ------------------------------------------------------------------

    async def scan(self, since_minutes: int = 15) -> list[dict]:
        """
        Fetch new replies and @mentions from the last ``since_minutes`` minutes.

        Returns a list of interaction dicts ready for ConnectorOrchestrator.
        Deduplicates by external_id within the returned batch only; pass the
        result through ``fetch_interactions()`` with a DB handle for persistent
        deduplication against connector_seen.
        """
        if not self.access_token or not self.user_id:
            self.logger.warning(
                "Threads not configured — set THREADS_ACCESS_TOKEN and THREADS_USER_ID"
            )
            return []

        cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
        interactions: list[dict] = []
        seen_ids: set[str] = set()

        async with aiohttp.ClientSession() as session:
            # ── 1. Replies on our own recent posts ──────────────────────────
            try:
                posts = await self.get_recent_posts(session, limit=10)
            except Exception as exc:
                self.logger.error("Failed to fetch recent Threads posts: %s", exc)
                posts = []

            for post in posts:
                post_id = post.get("id", "")
                if not post_id:
                    continue
                # Skip posts that are themselves too old to have new replies
                # (keep the window broad — replies may be recent even if the
                # post is older, so only skip posts older than 7 days)
                post_ts = self._parse_ts(post.get("timestamp", ""))
                if post_ts is not None:
                    age_limit = datetime.now(tz=post_ts.tzinfo) - timedelta(days=7)
                    if post_ts < age_limit:
                        continue

                try:
                    replies = await self.get_replies(session, post_id)
                except Exception as exc:
                    self.logger.error(
                        "Failed to fetch replies for post %s: %s", post_id, exc
                    )
                    continue

                for reply in replies:
                    reply_id = reply.get("id", "")
                    if not reply_id or reply_id in seen_ids:
                        continue
                    if not self._is_recent(reply.get("timestamp", ""), cutoff):
                        continue
                    seen_ids.add(reply_id)
                    interactions.append(self._build_reply_interaction(reply, post))

                await asyncio.sleep(0.3)  # gentle rate limiting

            # ── 2. @Mentions / tagged threads ───────────────────────────────
            try:
                mentions = await self.get_mentions(session, limit=25)
            except Exception as exc:
                self.logger.error("Failed to fetch Threads mentions: %s", exc)
                mentions = []

            for mention in mentions:
                mention_id = mention.get("id", "")
                if not mention_id or mention_id in seen_ids:
                    continue
                if not self._is_recent(mention.get("timestamp", ""), cutoff):
                    continue
                seen_ids.add(mention_id)
                interactions.append(self._build_mention_interaction(mention))

        self.logger.info(
            "Threads scan complete: %d new interaction(s) in last %d min",
            len(interactions),
            since_minutes,
        )
        return interactions

    # ------------------------------------------------------------------
    # fetch_interactions — public API with optional connector_seen dedup
    # ------------------------------------------------------------------

    async def fetch_interactions(
        self,
        since_minutes: int = 15,
        db=None,
    ) -> List[dict]:
        """
        Fetch new Threads interactions, optionally deduplicating against
        the ``connector_seen`` DB table.

        Args:
            since_minutes: Look-back window in minutes (default: 15).
            db: Optional DB handle exposing ``get_connection()``.  When
                supplied, interactions already present in connector_seen
                are skipped and new ones are recorded before returning.

        Returns:
            List of interaction dicts with keys:
                platform, external_id, author_id, author_name, content,
                parent_id, url, created_at  (plus interaction_type, raw).
        """
        raw = await self.scan(since_minutes=since_minutes)

        if db is None:
            return raw

        # Filter out already-seen, then mark new ones
        new_interactions: list[dict] = []
        for interaction in raw:
            ext_id = interaction["external_id"]
            if self._is_seen(db, "threads", ext_id):
                continue
            self._mark_seen(db, "threads", ext_id)
            new_interactions.append(interaction)

        self.logger.info(
            "Threads fetch_interactions: %d new (of %d raw) after connector_seen dedup",
            len(new_interactions),
            len(raw),
        )
        return new_interactions

    # ------------------------------------------------------------------
    # Reply helper (used by ConnectorOrchestrator._post_reply)
    # ------------------------------------------------------------------

    async def reply_to_thread(self, thread_id: str, text: str) -> dict:
        """
        Post a reply to a Threads post.

        Uses the two-step Threads Publishing API:
          1. Create a media container with ``reply_to_id``.
          2. Publish the container.
        """
        if not self.access_token or not self.user_id:
            return {"status": "needs_auth"}

        async with aiohttp.ClientSession() as session:
            # Step 1 — create container
            try:
                create_data = await self._post(
                    session,
                    f"{self.user_id}/threads",
                    data={
                        "media_type": "TEXT",
                        "text": text[:500],
                        "reply_to_id": thread_id,
                    },
                )
            except Exception as exc:
                self.logger.error("Threads create container failed: %s", exc)
                return {"status": "error", "error": str(exc)}

            container_id = create_data.get("id", "")
            if not container_id:
                return {"status": "error", "error": "no container id returned"}

            # Step 2 — publish
            try:
                publish_data = await self._post(
                    session,
                    f"{self.user_id}/threads_publish",
                    data={"creation_id": container_id},
                )
            except Exception as exc:
                self.logger.error("Threads publish failed: %s", exc)
                return {"status": "error", "error": str(exc)}

            reply_id = publish_data.get("id", "")
            if reply_id:
                return {
                    "reply_id": reply_id,
                    "status": "replied",
                    "url": f"https://www.threads.net/t/{reply_id}",
                }
            return {"status": "error", "error": publish_data}

    async def _post(
        self,
        session: aiohttp.ClientSession,
        path: str,
        data: dict | None = None,
    ) -> dict:
        """Execute a POST against the Threads Graph API."""
        params = {"access_token": self.access_token}
        url = f"{THREADS_API}/{path}"
        async with session.post(
            url,
            params=params,
            json=data or {},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                self.logger.warning("Threads POST %s → %s: %s", url, resp.status, text[:200])
                return {}
            return await resp.json()
