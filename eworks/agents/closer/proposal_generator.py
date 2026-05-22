"""Proposal generator — full Claude-powered professional proposal creation."""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.core.phoenix_instrumentation import trace_workflow_step, trace_llm_call

logger = logging.getLogger(__name__)

HOURLY_RATE = 150  # USD, configurable via settings

# Estimated hours per deliverable by complexity bucket
HOURS_PER_DELIVERABLE = 40  # default 1 week per deliverable at 40h/week


class ProposalGenerator(BaseAgent):
    """Generates professional proposals from discovery call data using Claude AI."""

    async def run(self, campaign_id: int) -> dict:
        """BaseAgent interface — not used directly for closer agent."""
        return {"status": "ok"}

    def _get_hourly_rate(self) -> float:
        """Return hourly rate from settings or default."""
        try:
            rate = self.db.get_setting("hourly_rate")
            return float(rate) if rate else HOURLY_RATE
        except Exception:
            return HOURLY_RATE

    def format_pricing_table(self, deliverables: list[str]) -> dict[str, Any]:
        """
        Build a pricing breakdown from a list of deliverable names.
        Returns {items: [{name, hours, price}], total: float, currency: 'USD'}
        """
        rate = self._get_hourly_rate()
        items = []
        for i, deliverable in enumerate(deliverables):
            # Vary hours slightly based on position (later deliverables may be more complex)
            hours = HOURS_PER_DELIVERABLE + (i % 3) * 8  # 40, 48, 56, 40, 48...
            price = hours * rate
            items.append({"name": deliverable, "hours": hours, "price": price})
        total = sum(item["price"] for item in items)
        return {"items": items, "total": total, "currency": "USD"}

    @trace_workflow_step("generate_full_proposal")
    async def generate(self, discovery_call_id: int) -> int:
        """Generate a full proposal from a processed discovery call. Returns proposal_id."""
        conn = self.db.get_connection()

        # Load discovery call
        row = conn.execute(
            "SELECT * FROM discovery_calls WHERE id=?", (discovery_call_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Discovery call {discovery_call_id} not found")
        call = dict(row)

        # Load client
        client_row = conn.execute(
            "SELECT * FROM clients WHERE id=?", (call["client_id"],)
        ).fetchone()
        client = dict(client_row) if client_row else {}

        # Parse extracted data
        requirements = []
        pain_points = []
        try:
            requirements = json.loads(call.get("extracted_requirements") or "[]")
        except Exception:
            pass
        try:
            pain_points = json.loads(call.get("pain_points") or "[]")
        except Exception:
            pass

        budget_range = call.get("budget_range", "")
        timeline = call.get("timeline", "")
        tech_stack = call.get("tech_stack", "")

        # Generate proposal markdown via Claude
        markdown_content = await self._generate_with_claude(
            client=client,
            requirements=requirements,
            pain_points=pain_points,
            budget_range=budget_range,
            timeline=timeline,
            tech_stack=tech_stack,
            raw_notes=call.get("raw_notes", ""),
        )

        # Extract deliverables from markdown (look for numbered list in Scope section)
        deliverables = self._extract_deliverables(markdown_content, requirements)

        # Calculate pricing
        pricing = self.format_pricing_table(deliverables)
        total_price = pricing["total"]

        # Estimate timeline in weeks
        num_deliverables = len(deliverables) if deliverables else 3
        timeline_weeks = max(4, math.ceil(num_deliverables * 1.5))

        # Build title
        company = client.get("company") or client.get("name", "Client")
        title = f"Eworks Labs AI Project Proposal — {company}"

        # Build executive summary (first paragraph of markdown or generate one)
        exec_summary = self._extract_exec_summary(markdown_content)

        # Valid for 30 days
        valid_until = (datetime.utcnow() + timedelta(days=30)).isoformat()

        # Save proposal
        cur = conn.execute(
            """
            INSERT INTO proposals (
                client_id, discovery_call_id, title, executive_summary,
                scope_of_work, timeline_weeks, total_price, pricing_breakdown,
                markdown_content, status, valid_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
            """,
            (
                call["client_id"],
                discovery_call_id,
                title,
                exec_summary,
                json.dumps(deliverables),
                timeline_weeks,
                total_price,
                json.dumps(pricing),
                markdown_content,
                valid_until,
            ),
        )
        conn.commit()
        proposal_id = cur.lastrowid

        # Update discovery call status
        conn.execute(
            "UPDATE discovery_calls SET status='proposal_generated' WHERE id=?",
            (discovery_call_id,),
        )
        conn.commit()

        logger.info("Generated proposal %d for call %d (total: $%.0f)", proposal_id, discovery_call_id, total_price)
        return proposal_id

    def _extract_deliverables(self, markdown: str, requirements: list[str]) -> list[str]:
        """Extract deliverable names from the proposal markdown."""
        deliverables = []
        in_scope = False
        for line in markdown.splitlines():
            line_stripped = line.strip()
            lower = line_stripped.lower()
            if "scope of work" in lower or "deliverable" in lower:
                in_scope = True
            elif in_scope and line_stripped.startswith("#"):
                # New section, stop
                in_scope = False
            elif in_scope and line_stripped and (
                line_stripped[0].isdigit() or line_stripped.startswith("-") or line_stripped.startswith("*")
            ):
                # Clean up bullet/number prefix
                text = line_stripped.lstrip("0123456789.-* ").strip()
                if text and len(text) > 5:
                    deliverables.append(text[:100])  # cap length
        if not deliverables:
            # Fallback: use requirements as deliverables
            deliverables = requirements[:8] if requirements else [
                "Project Discovery & Architecture", "Core Development", "Testing & QA", "Deployment & Launch"
            ]
        return deliverables[:10]  # cap at 10

    def _extract_exec_summary(self, markdown: str) -> str:
        """Extract the executive summary section from the proposal markdown."""
        lines = markdown.splitlines()
        in_exec = False
        summary_lines = []
        for line in lines:
            lower = line.lower().strip()
            if "executive summary" in lower:
                in_exec = True
                continue
            elif in_exec and line.strip().startswith("#"):
                break
            elif in_exec and line.strip():
                summary_lines.append(line.strip())
        return " ".join(summary_lines[:5]) if summary_lines else ""

    @trace_llm_call("anthropic/claude", "generate_proposal_markdown")
    async def _generate_with_claude(
        self,
        client: dict,
        requirements: list[str],
        pain_points: list[str],
        budget_range: str,
        timeline: str,
        tech_stack: str,
        raw_notes: str,
    ) -> str:
        """Generate the full proposal markdown using Claude."""
        try:
            import anthropic

            api_client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

            client_name = client.get("name", "Valued Client")
            company = client.get("company", "")
            rate = self._get_hourly_rate()

            system_prompt = (
                "You are Cesar Schneider, founder of Eworks Labs AI Agency. "
                "Generate professional project proposals that are technical, confident, and value-focused. "
                "Your proposals win deals because they show deep understanding of the client's problem "
                "and present a clear, credible path to solving it."
            )

            user_prompt = f"""Generate a professional project proposal for {client_name}{' at ' + company if company else ''}.

DISCOVERY NOTES:
{raw_notes}

EXTRACTED INFORMATION:
- Pain Points: {', '.join(pain_points) if pain_points else 'See notes'}
- Technical Requirements: {', '.join(requirements) if requirements else 'See notes'}
- Budget Range: {budget_range or 'To be discussed'}
- Timeline: {timeline or 'To be discussed'}
- Current Tech Stack: {tech_stack or 'Not specified'}
- Our Hourly Rate: ${rate}/hour

Generate a complete, professional proposal in Markdown format with these exact sections:
1. # Executive Summary
2. # Problem Understanding
3. # Proposed Solution
4. # Scope of Work (numbered deliverables list)
5. # Technical Approach
6. # Timeline (week-by-week breakdown)
7. # Investment (pricing summary)
8. # Why Eworks Labs
9. # Next Steps
10. # Terms & Conditions

Tone: confident, technical, value-focused. Be specific to the client's situation.
Length: comprehensive (800-1200 words). Include specific technologies and methodologies."""

            response = api_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text.strip()

        except Exception as exc:
            logger.error("Claude proposal generation failed: %s", exc)
            # Return a minimal fallback proposal
            client_name = client.get("name", "Client")
            company = client.get("company", "")
            rate = self._get_hourly_rate()
            return f"""# Executive Summary

Thank you for the opportunity to present this proposal to {client_name}{' at ' + company if company else ''}.
Eworks Labs will deliver a comprehensive AI solution tailored to your specific needs.

# Problem Understanding

Based on our discovery call, we understand your key challenges include:
{chr(10).join('- ' + p for p in pain_points) if pain_points else '- Operational inefficiencies requiring AI automation'}

# Proposed Solution

We propose a custom AI solution leveraging modern LLM technology and robust engineering practices.

# Scope of Work

1. Discovery & Architecture Design
2. Core AI Pipeline Development
3. Integration & API Development
4. Testing & Quality Assurance
5. Deployment & Launch
6. Training & Documentation

# Technical Approach

We will utilize state-of-the-art AI models and cloud infrastructure to deliver a scalable solution.

# Timeline

- Week 1-2: Discovery & Architecture
- Week 3-6: Core Development
- Week 7-8: Testing & Integration
- Week 9-10: Deployment & Launch

# Investment

| Service | Hours | Investment |
|---------|-------|------------|
| Architecture & Planning | 40h | ${40 * rate:,.0f} |
| Development | 120h | ${120 * rate:,.0f} |
| Testing & QA | 40h | ${40 * rate:,.0f} |
| Deployment | 20h | ${20 * rate:,.0f} |
| **Total** | **220h** | **${220 * rate:,.0f}** |

Rate: ${rate}/hour

# Why Eworks Labs

Eworks Labs combines deep AI expertise with pragmatic engineering to deliver real business results.

# Next Steps

1. Review this proposal
2. Schedule a follow-up call
3. Sign engagement letter
4. Kick off in Week 1

# Terms & Conditions

- 50% deposit upon signing
- 25% at midpoint milestone
- 25% upon delivery
- 30-day validity on this proposal
- All IP transferred to client upon final payment
"""
