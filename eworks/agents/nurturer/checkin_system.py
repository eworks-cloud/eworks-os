"""Check-in System — AI-personalized client check-ins with NPS tracking."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.agents.prospector.reporter import TelegramReporter

logger = logging.getLogger(__name__)

POSITIVE_KEYWORDS = {
    "great", "excellent", "amazing", "fantastic", "love", "perfect", "wonderful",
    "happy", "satisfied", "impressed", "awesome", "brilliant", "outstanding",
    "good", "well", "pleased", "thank", "thanks", "helpful", "smooth",
}
NEGATIVE_KEYWORDS = {
    "bad", "terrible", "awful", "horrible", "disappointed", "unhappy", "frustrated",
    "problem", "issue", "fail", "failed", "broken", "wrong", "late", "delay",
    "poor", "worst", "complaint", "bug", "error", "stuck", "confused",
}


def _classify_sentiment(text: str) -> str:
    """Simple keyword-based sentiment: positive / neutral / negative."""
    if not text:
        return "neutral"
    words = set(re.sub(r"[^\w\s]", " ", text.lower()).split())
    pos = len(words & POSITIVE_KEYWORDS)
    neg = len(words & NEGATIVE_KEYWORDS)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    else:
        return "neutral"


class CheckinSystem(BaseAgent):
    """Sends AI-personalised check-in messages to clients and tracks responses."""

    async def run(self, campaign_id: int) -> dict:
        """Not used directly."""
        return {"status": "checkin_system"}

    # ── Send check-in ────────────────────────────────────────────────────────

    async def send_checkin(self, client_id: int, checkin_type: str = "monthly") -> int:
        """
        Generate a personalised check-in message with Claude, send it via Telegram,
        record it in the DB, and return the checkin_id.
        """
        conn = self.db.get_connection()

        # Gather context
        client_row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        if not client_row:
            raise ValueError(f"Client {client_id} not found")
        client = dict(client_row)

        project_rows = self._get_projects(conn, client_id)
        last_checkin = self._get_last_checkin(conn, client_id)
        recent_deliverables = self._get_recent_deliverables(conn, client_id)

        # Build Claude prompt
        context = {
            "client_name": client.get("name", ""),
            "company": client.get("company", ""),
            "client_status": client.get("status", ""),
            "projects": project_rows,
            "last_checkin": last_checkin,
            "recent_deliverables": recent_deliverables,
            "checkin_type": checkin_type,
        }

        message = await self._generate_checkin_message(context)

        # Send via Telegram
        reporter = TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", ""),
            chat_id=getattr(self.config, "telegram_chat_id", ""),
        )
        await reporter.send(message)

        # Record in DB
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO client_checkins (client_id, checkin_type, message_sent, sent_at)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, checkin_type, message, now),
        )
        conn.commit()
        checkin_id = cur.lastrowid
        self.logger.info("Sent %s check-in to client %d (id=%d)", checkin_type, client_id, checkin_id)
        return checkin_id

    async def _generate_checkin_message(self, context: dict) -> str:
        """Call Claude to write a personalised check-in message."""
        try:
            import anthropic

            api_key = getattr(self.config, "anthropic_api_key", None) or ""
            client = anthropic.Anthropic(api_key=api_key)

            prompt = (
                "Write a warm, professional check-in message to a client of an AI agency. "
                "Keep it concise (3-5 sentences), personal, and reference their specific context.\n\n"
                f"Context:\n{json.dumps(context, indent=2, default=str)}\n\n"
                "The message should:\n"
                "- Greet the client by first name\n"
                "- Reference their project(s) or recent work\n"
                "- Ask an open-ended question about their experience or needs\n"
                "- Be warm and genuine, not salesy\n\n"
                "Return only the message text, no subject line or metadata."
            )

            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            self.logger.error("Claude API error generating check-in: %s", exc)
            client_name = context.get("client_name", "there")
            first_name = client_name.split()[0] if client_name else "there"
            return (
                f"Hi {first_name}, hope you're doing well! 👋\n\n"
                "I wanted to check in on how things are going with our work together. "
                "Is there anything you'd like to discuss or any feedback you'd like to share?\n\n"
                "Looking forward to hearing from you!"
            )

    # ── Response recording ───────────────────────────────────────────────────

    def record_response(
        self, checkin_id: int, response_text: str, nps_score: int | None = None
    ) -> bool:
        """Save a client's response, calculate sentiment, and update the check-in record."""
        conn = self.db.get_connection()
        sentiment = _classify_sentiment(response_text)
        now = datetime.now(timezone.utc).isoformat()

        cur = conn.execute(
            """
            UPDATE client_checkins
               SET response_received=?, nps_score=?, sentiment=?, responded_at=?
             WHERE id=?
            """,
            (response_text, nps_score, sentiment, now, checkin_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            self.logger.warning("No check-in found with id %d", checkin_id)
            return False
        self.logger.info("Recorded response for check-in %d (sentiment=%s)", checkin_id, sentiment)
        return True

    # ── Scheduled batch check-ins ────────────────────────────────────────────

    async def run_scheduled_checkins(self) -> dict[str, int]:
        """
        Send monthly check-ins to all clients whose last check-in was >30 days ago.
        Returns {checkins_sent, clients_checked}.
        """
        conn = self.db.get_connection()

        # Get all active clients
        try:
            client_rows = conn.execute(
                "SELECT id FROM clients WHERE status NOT IN ('lost', 'churned')"
            ).fetchall()
        except Exception:
            return {"checkins_sent": 0, "clients_checked": 0}

        clients_checked = 0
        checkins_sent = 0

        for row in client_rows:
            client_id = row["id"]
            clients_checked += 1

            # Check last check-in date
            last = conn.execute(
                """
                SELECT sent_at FROM client_checkins
                 WHERE client_id=? ORDER BY sent_at DESC LIMIT 1
                """,
                (client_id,),
            ).fetchone()

            needs_checkin = True
            if last and last["sent_at"]:
                try:
                    last_dt = datetime.fromisoformat(last["sent_at"])
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    days_ago = (datetime.now(timezone.utc) - last_dt).days
                    needs_checkin = days_ago > 30
                except (ValueError, TypeError):
                    pass

            if needs_checkin:
                try:
                    await self.send_checkin(client_id, checkin_type="monthly")
                    checkins_sent += 1
                except Exception as exc:
                    self.logger.error("Failed to send check-in for client %d: %s", client_id, exc)

        self.logger.info(
            "Scheduled check-ins complete: %d/%d clients received check-ins",
            checkins_sent, clients_checked,
        )
        return {"checkins_sent": checkins_sent, "clients_checked": clients_checked}

    # ── Data helpers ─────────────────────────────────────────────────────────

    def _get_projects(self, conn, client_id: int) -> list[dict]:
        try:
            rows = conn.execute(
                "SELECT name, status, health_score FROM projects WHERE client_id=? ORDER BY created_at DESC LIMIT 3",
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _get_last_checkin(self, conn, client_id: int) -> dict | None:
        try:
            row = conn.execute(
                """
                SELECT checkin_type, sentiment, nps_score, sent_at, responded_at
                  FROM client_checkins WHERE client_id=? ORDER BY sent_at DESC LIMIT 1
                """,
                (client_id,),
            ).fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def _get_recent_deliverables(self, conn, client_id: int) -> list[str]:
        """Extract recent deliverable info from project notes or tasks (best effort)."""
        try:
            rows = conn.execute(
                """
                SELECT name FROM projects
                 WHERE client_id=? AND status IN ('active', 'completed')
                 ORDER BY created_at DESC LIMIT 3
                """,
                (client_id,),
            ).fetchall()
            return [r["name"] for r in rows]
        except Exception:
            return []
