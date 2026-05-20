"""Nurturer Orchestrator — daily customer success pipeline runner."""
from __future__ import annotations

import logging
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.agents.nurturer.health_scorer import HealthScorer
from eworks.agents.nurturer.checkin_system import CheckinSystem
from eworks.agents.prospector.reporter import TelegramReporter

logger = logging.getLogger(__name__)


class NurturerOrchestrator(BaseAgent):
    """Orchestrates the daily customer success run."""

    async def run(self, campaign_id: int = 0) -> dict:
        """Alias for run_daily — campaign_id unused."""
        return await self.run_daily()

    async def run_daily(self) -> dict[str, Any]:
        """
        Daily customer success pipeline:
          1. Record health scores for all active clients
          2. Alert on at-risk clients via Telegram
          3. Run scheduled check-ins
        Returns {clients_scored, at_risk, checkins_sent}.
        """
        conn = self.db.get_connection()

        # 1. Get all active clients
        try:
            client_rows = conn.execute(
                "SELECT id, name FROM clients WHERE status NOT IN ('lost', 'churned')"
            ).fetchall()
        except Exception as exc:
            self.logger.error("Failed to fetch clients: %s", exc)
            return {"clients_scored": 0, "at_risk": 0, "checkins_sent": 0}

        scorer = HealthScorer(db=self.db, config=self.config)
        clients_scored = 0
        for row in client_rows:
            try:
                scorer.record_health_score(row["id"])
                clients_scored += 1
            except Exception as exc:
                self.logger.error("Health score failed for client %d: %s", row["id"], exc)

        # 2. Alert at-risk clients
        at_risk = scorer.get_at_risk_clients()
        if at_risk:
            await self._alert_at_risk(at_risk)

        # 3. Run scheduled check-ins
        checkin_system = CheckinSystem(db=self.db, config=self.config)
        checkin_result = await checkin_system.run_scheduled_checkins()

        result = {
            "clients_scored": clients_scored,
            "at_risk": len(at_risk),
            "checkins_sent": checkin_result.get("checkins_sent", 0),
            "clients_checked": checkin_result.get("clients_checked", 0),
        }
        self.logger.info("Nurturer daily run complete: %s", result)
        return result

    async def _alert_at_risk(self, at_risk_clients: list[dict]) -> None:
        """Send a Telegram alert listing at-risk clients."""
        lines = ["🚨 <b>At-Risk Clients Alert</b>\n"]
        for c in at_risk_clients:
            name = c.get("client_name", f"Client #{c['client_id']}")
            company = c.get("company", "")
            score = c.get("score", "?")
            lines.append(
                f"• <b>{name}</b>"
                + (f" ({company})" if company else "")
                + f" — Health: <b>{score}/100</b>"
            )
        lines.append("\nPlease reach out to these clients promptly.")

        reporter = TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", ""),
            chat_id=getattr(self.config, "telegram_chat_id", ""),
        )
        await reporter.send("\n".join(lines))
