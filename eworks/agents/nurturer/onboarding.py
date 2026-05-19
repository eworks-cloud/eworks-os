"""Onboarding Manager — 7-step client onboarding checklist tracker."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.agents.prospector.reporter import TelegramReporter

logger = logging.getLogger(__name__)

DEFAULT_STEPS: list[tuple[str, str]] = [
    ("kickoff_meeting", "Schedule and conduct kickoff meeting with client"),
    ("access_credentials", "Collect all necessary access credentials and accounts"),
    ("project_setup", "Set up project in Eworks OS, create initial sprint"),
    ("communication_channels", "Set up Telegram/Slack/email communication channels"),
    ("first_deliverable", "Deliver first milestone or prototype"),
    ("feedback_session", "Collect first feedback from client"),
    ("workflow_established", "Confirm regular update cadence established"),
]


class OnboardingManager(BaseAgent):
    """Manages client onboarding via a 7-step checklist."""

    async def run(self, campaign_id: int) -> dict:
        """Not used directly; individual methods drive onboarding."""
        return {"status": "onboarding_manager"}

    # ── Checklist creation ──────────────────────────────────────────────────

    def create_onboarding(self, client_id: int, project_id: int | None = None) -> int:
        """Insert all DEFAULT_STEPS for a client. Returns count of steps created."""
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for step_name, step_description in DEFAULT_STEPS:
            conn.execute(
                """
                INSERT INTO onboarding_checklists
                    (client_id, project_id, step_name, step_description, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (client_id, project_id, step_name, step_description, now),
            )
            count += 1
        conn.commit()
        self.logger.info("Created %d onboarding steps for client %d", count, client_id)
        return count

    # ── Step management ──────────────────────────────────────────────────────

    def complete_step(self, checklist_id: int, notes: str | None = None) -> bool:
        """Mark a checklist step as completed. Returns True on success."""
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            UPDATE onboarding_checklists
               SET status='completed', completed_at=?, notes=?
             WHERE id=?
            """,
            (now, notes, checklist_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            self.logger.warning("No checklist step found with id %d", checklist_id)
            return False
        self.logger.info("Completed onboarding step %d", checklist_id)
        return True

    # ── Progress tracking ────────────────────────────────────────────────────

    def get_onboarding_progress(self, client_id: int) -> dict[str, Any]:
        """Return progress summary for a client's onboarding."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM onboarding_checklists WHERE client_id=? ORDER BY created_at ASC",
            (client_id,),
        ).fetchall()

        total = len(rows)
        completed = sum(1 for r in rows if r["status"] == "completed")
        in_progress = sum(1 for r in rows if r["status"] == "in_progress")
        pending = sum(1 for r in rows if r["status"] == "pending")
        skipped = sum(1 for r in rows if r["status"] == "skipped")

        completion_pct = round((completed / total * 100), 1) if total else 0.0

        # Next step = first non-completed, non-skipped step
        next_step = None
        for r in rows:
            if r["status"] in ("pending", "in_progress"):
                next_step = {
                    "id": r["id"],
                    "step_name": r["step_name"],
                    "step_description": r["step_description"],
                    "status": r["status"],
                }
                break

        return {
            "client_id": client_id,
            "total_steps": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "skipped": skipped,
            "completion_pct": completion_pct,
            "next_step": next_step,
        }

    # ── Reminders ────────────────────────────────────────────────────────────

    async def send_onboarding_reminder(self, client_id: int) -> bool:
        """Send Telegram reminder if onboarding < 100% and stale > 3 days."""
        progress = self.get_onboarding_progress(client_id)
        if progress["completion_pct"] >= 100.0:
            self.logger.info("Client %d onboarding complete — no reminder needed", client_id)
            return False

        # Check staleness: find the most recent updated checklist item
        conn = self.db.get_connection()
        row = conn.execute(
            """
            SELECT MAX(COALESCE(completed_at, created_at)) as last_update
              FROM onboarding_checklists
             WHERE client_id=?
            """,
            (client_id,),
        ).fetchone()

        if row and row["last_update"]:
            try:
                last_update = datetime.fromisoformat(row["last_update"])
                # Make timezone-aware if naive
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_stale = (now - last_update).days
                if days_stale < 3:
                    self.logger.info(
                        "Client %d onboarding updated %d days ago — no reminder", client_id, days_stale
                    )
                    return False
            except (ValueError, TypeError):
                pass  # If parse fails, send the reminder anyway

        # Fetch client name
        client_row = conn.execute("SELECT name, company FROM clients WHERE id=?", (client_id,)).fetchone()
        client_name = client_row["name"] if client_row else f"Client #{client_id}"
        company = client_row["company"] if client_row else ""

        next_step = progress["next_step"]
        next_step_text = next_step["step_name"] if next_step else "N/A"

        message = (
            f"🔔 <b>Onboarding Reminder</b>\n\n"
            f"Client: <b>{client_name}</b>"
            + (f" ({company})" if company else "")
            + f"\nProgress: <b>{progress['completion_pct']}%</b> "
            f"({progress['completed']}/{progress['total_steps']} steps)\n"
            f"Next step: <b>{next_step_text}</b>\n\n"
            "Please follow up to keep the onboarding moving!"
        )

        reporter = TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", ""),
            chat_id=getattr(self.config, "telegram_chat_id", ""),
        )
        sent = await reporter.send(message)
        if sent:
            self.logger.info("Sent onboarding reminder for client %d", client_id)
        return sent
