"""Status Reporter — Claude-powered weekly reports + Telegram alerts."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.core.phoenix_instrumentation import trace_workflow_step, trace_llm_call

logger = logging.getLogger(__name__)


class StatusReporter(BaseAgent):
    """Generates client-facing reports and sends alerts for at-risk projects."""

    async def run(self, campaign_id: int = 0) -> dict:  # type: ignore[override]
        return {"status": "StatusReporter ready"}

    # ──────────────────────────────────────────────────────────────────────────
    # Weekly Report
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("generate_weekly_report")
    async def generate_weekly_report(self, project_id: int) -> str:
        """
        Use Claude to generate a professional client-facing weekly update.
        Saves to project_updates and returns the report text.
        """
        conn = self.db.get_connection()

        # Gather project context
        project = conn.execute(
            "SELECT * FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if not project:
            return ""
        project = dict(project)

        one_week_ago = (date.today() - timedelta(days=7)).isoformat()

        # Tasks completed this week
        completed = conn.execute(
            """
            SELECT title, story_points FROM project_tasks
            WHERE project_id=? AND status='done'
              AND completed_at >= ?
            ORDER BY completed_at DESC
            """,
            (project_id, one_week_ago),
        ).fetchall()
        completed_list = [dict(r) for r in completed]

        # In-progress tasks
        in_progress = conn.execute(
            """
            SELECT title, assignee, due_date FROM project_tasks
            WHERE project_id=? AND status='in_progress'
            ORDER BY due_date ASC
            """,
            (project_id,),
        ).fetchall()
        in_progress_list = [dict(r) for r in in_progress]

        # Blockers
        blockers = await self.check_blockers(project_id)

        # Health score
        health_score = project.get("health_score", 100)

        # Build context for Claude
        context = f"""
Project: {project['name']}
Status: {project['status']}
Health Score: {health_score}/100
Budget: ${project.get('budget', 0):,.2f}
Hours Logged: {project.get('hours_logged', 0):.1f}h

Completed this week ({len(completed_list)} tasks):
{chr(10).join(f"  - {t['title']}" for t in completed_list) or "  None"}

Currently in progress ({len(in_progress_list)} tasks):
{chr(10).join(f"  - {t['title']} (due: {t.get('due_date','TBD')})" for t in in_progress_list) or "  None"}

Blockers / Overdue:
{chr(10).join(f"  - {b}" for b in blockers) or "  None"}
        """.strip()

        report_text = await self._call_claude(context, project["name"])

        # Save to project_updates
        today_str = date.today().isoformat()
        conn.execute(
            """
            INSERT INTO project_updates (project_id, update_type, title, content, sent_to_client)
            VALUES (?, 'weekly_report', ?, ?, 0)
            """,
            (project_id, f"Weekly Report — {today_str}", report_text),
        )
        conn.commit()

        return report_text

    @trace_llm_call("anthropic/claude", "generate_weekly_report_llm")
    async def _call_claude(self, context: str, project_name: str) -> str:
        """Call Claude API to generate the report. Falls back to template on error."""
        try:
            import anthropic  # type: ignore

            client = anthropic.AsyncAnthropic()
            message = await client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"You are a professional project manager writing a weekly status update "
                            f"for client project: {project_name}.\n\n"
                            f"Project data:\n{context}\n\n"
                            "Write a concise, professional client-facing weekly status update. "
                            "Include: ✅ Completed this week, 🔄 In Progress, 📅 Next Week Plan, "
                            "⚠️ Risks/Blockers, 💚 Overall Health. "
                            "Keep it under 300 words. Use bullet points."
                        ),
                    }
                ],
            )
            return message.content[0].text
        except Exception as exc:
            logger.warning("Claude API call failed (%s), using template report", exc)
            return self._template_report(context, project_name)

    def _template_report(self, context: str, project_name: str) -> str:
        """Fallback template report when Claude is unavailable."""
        return (
            f"📋 Weekly Status Report — {project_name}\n"
            f"{'='*50}\n\n"
            f"{context}\n\n"
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Send Update
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("send_client_update")
    async def send_update_to_client(self, update_id: int) -> bool:
        """Send a project_update via Telegram and mark it sent."""
        from eworks.agents.prospector.reporter import TelegramReporter

        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT * FROM project_updates WHERE id=?", (update_id,)
        ).fetchone()
        if not row:
            logger.error("Update %d not found", update_id)
            return False

        update = dict(row)
        reporter = TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", None),
            chat_id=getattr(self.config, "telegram_chat_id", None),
        )

        message = f"📋 *{update['title']}*\n\n{update['content']}"
        sent = await reporter.send(message)

        if sent:
            conn.execute(
                "UPDATE project_updates SET sent_to_client=1 WHERE id=?",
                (update_id,),
            )
            conn.commit()
            logger.info("Update %d sent to client", update_id)

        return sent

    # ──────────────────────────────────────────────────────────────────────────
    # Blockers
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("check_blockers")
    async def check_blockers(self, project_id: int) -> list[str]:
        """
        Return titles of tasks that are in_progress and overdue by >2 days.
        """
        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT title FROM project_tasks
            WHERE project_id=?
              AND status = 'in_progress'
              AND due_date IS NOT NULL
              AND due_date < ?
            ORDER BY due_date ASC
            """,
            (project_id, two_days_ago),
        ).fetchall()
        return [row["title"] for row in rows]

    # ──────────────────────────────────────────────────────────────────────────
    # At-Risk Alert
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("alert_if_at_risk")
    async def alert_if_at_risk(self, project_id: int) -> bool:
        """Send a Telegram alert if health_score < 60. Returns True if alert sent."""
        from eworks.agents.prospector.reporter import TelegramReporter

        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT name, health_score FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if not row:
            return False

        project = dict(row)
        if project["health_score"] >= 60:
            return False

        reporter = TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", None),
            chat_id=getattr(self.config, "telegram_chat_id", None),
        )

        msg = (
            f"🚨 *Project At Risk*\n\n"
            f"Project: *{project['name']}*\n"
            f"Health Score: {project['health_score']}/100\n\n"
            f"Immediate attention required. Check tasks and timeline."
        )
        sent = await reporter.send(msg)
        if sent:
            logger.warning(
                "At-risk alert sent for project %d (score=%d)",
                project_id, project["health_score"],
            )
        return sent
