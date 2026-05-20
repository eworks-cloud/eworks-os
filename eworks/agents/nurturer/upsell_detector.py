"""Upsell Detector — Claude AI-powered opportunity identification."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class UpsellDetector(BaseAgent):
    """Detects upsell opportunities for clients using Claude AI."""

    async def run(self, campaign_id: int) -> dict:
        """Not used directly."""
        return {"status": "upsell_detector"}

    # ── Opportunity detection ────────────────────────────────────────────────

    async def detect_opportunities(self, client_id: int) -> list[dict[str, Any]]:
        """
        Use Claude to identify 1-3 upsell opportunities for a client.
        Saves results to upsell_opportunities table and returns list.
        """
        conn = self.db.get_connection()

        # Gather client profile data
        client_row = conn.execute(
            "SELECT * FROM clients WHERE id=?", (client_id,)
        ).fetchone()
        if not client_row:
            self.logger.warning("Client %d not found", client_id)
            return []
        client = dict(client_row)

        # Invoice history (if table exists)
        invoice_summary = self._get_invoice_summary(conn, client_id)

        # Project completion info
        project_summary = self._get_project_summary(conn, client_id)

        # Check-in notes / engagement
        checkin_summary = self._get_checkin_summary(conn, client_id)

        # Latest health score
        health_row = conn.execute(
            "SELECT score FROM client_health_scores WHERE client_id=? ORDER BY recorded_at DESC LIMIT 1",
            (client_id,),
        ).fetchone()
        health_score = health_row["score"] if health_row else "unknown"

        profile = {
            "client_name": client.get("name", ""),
            "company": client.get("company", ""),
            "status": client.get("status", ""),
            "health_score": health_score,
            "invoice_summary": invoice_summary,
            "project_summary": project_summary,
            "checkin_summary": checkin_summary,
        }

        prompt = (
            "Based on this client profile for an AI agency, identify 1-3 upsell opportunities. "
            "Consider: adding new AI agents to their OS, expanding project scope, converting to a "
            "retainer model, referral program, or training/support packages.\n\n"
            f"Client Profile:\n{json.dumps(profile, indent=2, default=str)}\n\n"
            "Return ONLY a valid JSON array of objects with these exact keys:\n"
            '  opportunity_type (string), description (string), estimated_value (number in USD), '
            'confidence ("low"|"medium"|"high")\n\n'
            "Example: [{\"opportunity_type\": \"retainer_upgrade\", \"description\": \"...\", "
            "\"estimated_value\": 2500, \"confidence\": \"high\"}]"
        )

        opportunities = await self._call_claude(prompt)

        # Save to DB
        saved = []
        now = datetime.now(timezone.utc).isoformat()
        for opp in opportunities:
            if not isinstance(opp, dict):
                continue
            cur = conn.execute(
                """
                INSERT INTO upsell_opportunities
                    (client_id, opportunity_type, description, estimated_value, confidence, identified_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    opp.get("opportunity_type", "unknown"),
                    opp.get("description", ""),
                    opp.get("estimated_value"),
                    opp.get("confidence", "medium"),
                    now,
                ),
            )
            opp["id"] = cur.lastrowid
            opp["client_id"] = client_id
            saved.append(opp)
        conn.commit()

        self.logger.info("Detected %d upsell opportunities for client %d", len(saved), client_id)
        return saved

    async def _call_claude(self, prompt: str) -> list[dict]:
        """Call the Anthropic Claude API and parse the JSON response."""
        try:
            import anthropic

            api_key = getattr(self.config, "anthropic_api_key", None) or ""
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON array
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception as exc:
            self.logger.error("Claude API error in upsell detection: %s", exc)
            # Return a sensible default if AI fails
            return [
                {
                    "opportunity_type": "retainer_model",
                    "description": "Convert client to a monthly retainer for ongoing AI agent support.",
                    "estimated_value": 2000.0,
                    "confidence": "medium",
                }
            ]

    # ── Helper data gatherers ────────────────────────────────────────────────

    def _get_invoice_summary(self, conn, client_id: int) -> dict:
        try:
            rows = conn.execute(
                "SELECT status, amount FROM invoices WHERE client_id=?", (client_id,)
            ).fetchall()
            total = sum(r["amount"] or 0 for r in rows)
            paid = sum(r["amount"] or 0 for r in rows if r["status"] == "paid")
            overdue = sum(1 for r in rows if r["status"] in ("overdue", "unpaid"))
            return {"total_invoiced": total, "total_paid": paid, "overdue_count": overdue}
        except Exception:
            return {}

    def _get_project_summary(self, conn, client_id: int) -> list[dict]:
        try:
            rows = conn.execute(
                "SELECT name, status, health_score FROM projects WHERE client_id=?", (client_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _get_checkin_summary(self, conn, client_id: int) -> dict:
        try:
            rows = conn.execute(
                """
                SELECT checkin_type, sentiment, nps_score, response_received, sent_at
                  FROM client_checkins WHERE client_id=? ORDER BY sent_at DESC LIMIT 5
                """,
                (client_id,),
            ).fetchall()
            return {"recent_checkins": [dict(r) for r in rows]}
        except Exception:
            return {}

    # ── Pipeline analytics ───────────────────────────────────────────────────

    def get_pipeline_value(self) -> dict[str, Any]:
        """Summarise the full upsell pipeline by confidence level."""
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT confidence, COUNT(*) as count, SUM(estimated_value) as total_value
              FROM upsell_opportunities
             WHERE status NOT IN ('won', 'lost')
             GROUP BY confidence
            """
        ).fetchall()

        by_confidence: dict[str, dict] = {
            "high": {"count": 0, "value": 0.0},
            "medium": {"count": 0, "value": 0.0},
            "low": {"count": 0, "value": 0.0},
        }
        total_count = 0
        total_value = 0.0

        for row in rows:
            conf = row["confidence"]
            cnt = row["count"]
            val = row["total_value"] or 0.0
            if conf in by_confidence:
                by_confidence[conf] = {"count": cnt, "value": val}
            total_count += cnt
            total_value += val

        return {
            "total_opportunities": total_count,
            "total_estimated_value": total_value,
            "by_confidence": by_confidence,
        }
