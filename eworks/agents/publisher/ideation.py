"""Ideation agent — Claude-powered content idea generation."""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from eworks.agents.publisher.base_publisher import BasePublisher

logger = logging.getLogger(__name__)


class IdeationAgent(BasePublisher):
    """Generates content ideas using Claude AI for the content pipeline."""

    SYSTEM_PROMPT = """You are an expert content strategist specializing in AI automation for B2B audiences.
Your target audience is CTOs, founders, and decision-makers at mid-to-large companies.
You create compelling, data-driven content ideas that position AI automation as a competitive advantage.

Your ideas should:
- Address real pain points (manual processes, scaling bottlenecks, cost reduction)
- Use technical authority without being overly academic
- Include a strong hook that stops the scroll
- Have a clear value proposition in the angle
- Be optimized for viral potential on YouTube and Instagram Reels"""

    async def generate_ideas(
        self,
        n: int = 5,
        language: str = "en",
        niche: str = "AI automation for businesses",
    ) -> list[dict[str, Any]]:
        """Generate n content ideas using Claude and save them to the database.

        Args:
            n: Number of ideas to generate
            language: Target language ('en' or 'pt')
            niche: Content niche/topic area

        Returns:
            List of saved idea dicts with database IDs
        """
        client = anthropic.Anthropic(api_key=self.anthropic_api_key)

        lang_instruction = ""
        if language == "pt":
            lang_instruction = "Generate all content in Brazilian Portuguese (PT-BR). "

        user_prompt = f"""{lang_instruction}Generate exactly {n} unique content ideas about {niche}.

Return a JSON array with exactly {n} objects. Each object must have:
- "title": Compelling video title (max 60 chars)
- "hook": Opening line that grabs attention in first 3 seconds (1-2 sentences)
- "angle": Unique perspective or argument that differentiates this content (1-2 sentences)
- "keywords": Array of 5-8 SEO keywords (strings)
- "format": One of "long-form", "reel", or "both"

Return ONLY the JSON array, no markdown, no explanation."""

        logger.info("Generating %d content ideas with Claude (language=%s)", n, language)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        ideas_data = json.loads(raw)
        if not isinstance(ideas_data, list):
            raise ValueError(f"Expected JSON array from Claude, got: {type(ideas_data)}")

        saved_ideas = []
        conn = self._get_conn()

        for idea in ideas_data[:n]:
            keywords_json = json.dumps(idea.get("keywords", []))
            cur = conn.execute(
                """INSERT INTO content_ideas (title, hook, angle, keywords, format, language, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'draft')""",
                (
                    idea.get("title", "Untitled"),
                    idea.get("hook", ""),
                    idea.get("angle", ""),
                    keywords_json,
                    idea.get("format", "both"),
                    language,
                ),
            )
            conn.commit()
            idea_id = cur.lastrowid
            saved = self.db.get_content_idea(idea_id)
            saved["keywords"] = json.loads(saved["keywords"]) if saved.get("keywords") else []
            saved_ideas.append(saved)
            logger.info("Saved idea #%d: %s", idea_id, idea.get("title"))

        logger.info("Generated and saved %d ideas", len(saved_ideas))
        return saved_ideas

    async def run(self, campaign_id: int) -> dict:
        """Run ideation for a campaign (generates 5 ideas)."""
        ideas = await self.generate_ideas(n=5)
        return {"status": "completed", "ideas_generated": len(ideas), "campaign_id": campaign_id}
