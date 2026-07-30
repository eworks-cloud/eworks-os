"""Claude AI message generator for LinkedIn outreach.

Uses the Anthropic API to generate personalised connection request messages
that are within LinkedIn's 300-character limit.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from eworks.core.phoenix_instrumentation import trace_llm_call, trace_workflow_step

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Cesar Schneider, founder of Eworks Labs AI agency. "
    "Write a personalized LinkedIn connection request message. "
    "Max 300 characters (LinkedIn limit). "
    "Be direct, reference something specific about their work, make a clear offer. "
    "No generic lines. No emojis in professional mode. "
    "Return ONLY the message text — no quotes, no explanation."
)

FORBIDDEN_PATTERNS = [
    r"hope\s+this\s+(message\s+)?finds\s+you",
    r"i\s+came\s+across\s+your\s+profile",
    r"i\s+would\s+love\s+to\s+connect",
    r"let'?s\s+connect\s+and\s+explore",
]


class MessageGenerator:
    """Generates personalised LinkedIn messages using Claude."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-5"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazily initialise the Anthropic client."""
        if self._client is None:
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError as exc:
                raise RuntimeError(
                    "anthropic package is not installed. Run: pip install anthropic"
                ) from exc
        return self._client

    def _build_prompt(
        self,
        prospect: dict[str, Any],
        persona: dict[str, Any],
        campaign: dict[str, Any],
    ) -> str:
        """Build the user-facing prompt for Claude."""
        name = prospect.get("full_name", "there")
        headline = prospect.get("headline", "")
        company = prospect.get("company", "")
        mutual = prospect.get("mutual_connections", 0) or 0
        offer = persona.get("offer_summary", "AI-powered growth solutions")
        tone = persona.get("tone", "professional")

        mutual_note = (
            f"You have {mutual} mutual connection(s) with them." if mutual > 0 else ""
        )

        return (
            f"Write a LinkedIn connection request message to {name}.\n"
            f"Their headline: {headline}\n"
            f"Their company: {company}\n"
            f"{mutual_note}\n"
            f"Tone: {tone}\n"
            f"Your offer: {offer}\n\n"
            "Remember: max 300 characters, no generic openers, no emojis (unless tone is casual)."
        )

    def validate_message(self, text: str) -> bool:
        """Return True if the message is valid for LinkedIn sending."""
        if not text or len(text) > 300:
            return False
        text_lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text_lower):
                logger.debug("Message rejected — forbidden pattern: %s", pattern)
                return False
        return True

    @trace_llm_call("anthropic/claude", "generate_message")
    async def generate(
        self,
        prospect: dict[str, Any],
        persona: dict[str, Any],
        campaign: dict[str, Any],
    ) -> str:
        """Generate a single personalised message. Returns the message body."""
        client = self._get_client()
        prompt = self._build_prompt(prospect, persona, campaign)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=self.model,
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ),
        )

        text = response.content[0].text.strip()

        # If over limit, truncate at last word boundary
        if len(text) > 300:
            text = text[:297].rsplit(" ", 1)[0] + "…"

        logger.debug(
            "Generated message for %s (%d chars): %s",
            prospect.get("full_name", "?"),
            len(text),
            text[:80],
        )
        return text

    @trace_workflow_step("generate_batch")
    async def generate_batch(
        self,
        prospects: list[dict[str, Any]],
        persona: dict[str, Any],
        campaign: dict[str, Any],
        max: int = 20,
        db=None,
    ) -> list[dict[str, Any]]:
        """Generate messages for multiple prospects.

        Returns list of dicts with: prospect_id, message, valid, generation_prompt.
        """
        results = []
        count = 0

        for prospect in prospects[:max]:
            if count >= max:
                break

            prompt = self._build_prompt(prospect, persona, campaign)
            try:
                message = await self.generate(prospect, persona, campaign)
                valid = self.validate_message(message)
                result = {
                    "prospect_id": prospect.get("id"),
                    "prospect_url": prospect.get("linkedin_url"),
                    "full_name": prospect.get("full_name"),
                    "message": message,
                    "valid": valid,
                    "generation_prompt": prompt,
                    "generation_model": self.model,
                }
                results.append(result)

                # Persist to messages table
                if db and prospect.get("id"):
                    try:
                        db.get_connection().execute(
                            """
                            INSERT INTO messages
                                (prospect_id, campaign_id, body, status, generation_model, generation_prompt)
                            VALUES (?, ?, ?, 'draft', ?, ?)
                            """,
                            (
                                prospect["id"],
                                campaign.get("id"),
                                message,
                                self.model,
                                prompt,
                            ),
                        )
                        db.get_connection().commit()
                    except Exception as exc:
                        logger.error("Failed to save message to DB: %s", exc)

                count += 1
            except Exception as exc:
                logger.error(
                    "Failed to generate message for %s: %s",
                    prospect.get("full_name"),
                    exc,
                )
                results.append(
                    {
                        "prospect_id": prospect.get("id"),
                        "prospect_url": prospect.get("linkedin_url"),
                        "full_name": prospect.get("full_name"),
                        "message": None,
                        "valid": False,
                        "error": str(exc),
                    }
                )

            # Human-like delay between API calls
            if count < min(max, len(prospects)):
                await asyncio.sleep(1.0 + (count % 2))

        logger.info("Batch generation complete: %d messages", len(results))
        return results
