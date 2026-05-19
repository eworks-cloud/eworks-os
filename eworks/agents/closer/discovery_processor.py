"""Discovery call processor — extracts requirements from raw notes using Claude AI."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class DiscoveryProcessor(BaseAgent):
    """Processes raw discovery call notes to extract structured requirements via Claude."""

    async def run(self, campaign_id: int) -> dict:
        """BaseAgent interface — not used directly for closer agent."""
        return {"status": "ok"}

    async def create_call(self, client_id: int, notes: str) -> int:
        """Create a discovery_calls record and return its ID."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO discovery_calls (client_id, raw_notes, call_date, status)
            VALUES (?, ?, ?, 'notes_taken')
            """,
            (client_id, notes, datetime.utcnow().isoformat()),
        )
        conn.commit()
        call_id = cur.lastrowid
        logger.info("Created discovery call %d for client %d", call_id, client_id)
        return call_id

    async def process_notes(self, call_id: int) -> dict[str, Any]:
        """Extract structured requirements from raw notes using Claude AI."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT * FROM discovery_calls WHERE id=?", (call_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Discovery call {call_id} not found")
        call = dict(row)
        raw_notes = call["raw_notes"]

        extraction = await self._extract_with_claude(raw_notes)

        # Save extracted data back to DB
        conn.execute(
            """
            UPDATE discovery_calls SET
                extracted_requirements=?,
                pain_points=?,
                budget_range=?,
                timeline=?,
                decision_makers=?,
                tech_stack=?,
                status='processed'
            WHERE id=?
            """,
            (
                json.dumps(extraction.get("technical_requirements", [])),
                json.dumps(extraction.get("pain_points", [])),
                extraction.get("budget_range", ""),
                extraction.get("timeline_expectations", ""),
                json.dumps(extraction.get("decision_makers", [])),
                extraction.get("existing_tech_stack", ""),
                call_id,
            ),
        )
        conn.commit()
        logger.info("Processed discovery call %d", call_id)
        return extraction

    async def _extract_with_claude(self, raw_notes: str) -> dict[str, Any]:
        """Call Claude API to extract structured requirements from raw notes."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            prompt = f"""Extract structured information from these discovery call notes.

NOTES:
{raw_notes}

Return a JSON object with exactly these keys:
- pain_points: list of strings (main problems the client has)
- technical_requirements: list of strings (specific technical needs)
- budget_range: string (any budget or investment range mentioned)
- timeline_expectations: string (when they need it done)
- decision_makers: list of strings (names/roles of people involved in decision)
- existing_tech_stack: string (current tools/technologies they use)
- success_criteria: list of strings (how they'll measure success)

Return ONLY valid JSON, no markdown, no explanation."""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            # Clean up markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as exc:
            logger.error("Claude extraction failed: %s", exc)
            # Return minimal structure on failure
            return {
                "pain_points": [],
                "technical_requirements": [],
                "budget_range": "",
                "timeline_expectations": "",
                "decision_makers": [],
                "existing_tech_stack": "",
                "success_criteria": [],
                "error": str(exc),
            }
