"""Scripting agent — YouTube + Reel script generator."""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from eworks.agents.publisher.base_publisher import BasePublisher

logger = logging.getLogger(__name__)


class ScriptingAgent(BasePublisher):
    """Generates full YouTube scripts and Instagram Reel scripts from content ideas."""

    SYSTEM_PROMPT = """You are writing scripts for Cesar Schneider — a CTO and AI automation expert.

Voice style: Direct, technical but accessible. Speaks with authority like a seasoned CTO.
No fluff, no filler words. Gets to the point immediately.
Uses concrete examples, real numbers, and actionable insights.
Never says "In today's video" or "Don't forget to like and subscribe".
Opens with the insight or hook directly.

Target audience: CTOs, VPs of Engineering, founders, and technical decision-makers."""

    async def generate_script(self, idea_id: int, language: str = "en") -> dict[str, Any]:
        """Generate YouTube + Reel scripts for a content idea.

        Args:
            idea_id: ID of the content idea in the database
            language: Target language ('en' or 'pt')

        Returns:
            Dict with all script fields and the database ID
        """
        idea = self.db.get_content_idea(idea_id)
        if not idea:
            raise ValueError(f"Content idea #{idea_id} not found")

        keywords = idea.get("keywords", "[]")
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = []
        keywords_str = ", ".join(keywords) if keywords else idea.get("title", "")

        client = anthropic.Anthropic(api_key=self.anthropic_api_key)

        lang_instruction = "Write everything in Brazilian Portuguese (PT-BR)." if language == "pt" else "Write in English."

        user_prompt = f"""{lang_instruction}

Create complete scripts for this content idea:

Title: {idea['title']}
Hook: {idea.get('hook', '')}
Angle: {idea.get('angle', '')}
Keywords: {keywords_str}

Generate a JSON object with these exact keys:

"youtube_script": Full YouTube video script (600-1200 words, 3-8 minutes when spoken).
  - Open directly with the hook — no intro fluff
  - Structure: Hook → Problem → Solution → Examples → Call to action
  - Include natural pauses and emphasis markers in [brackets]
  - End with a specific next step (not "like and subscribe")

"reel_script": Short-form Instagram Reel script (100-150 words, 30-60 seconds).
  - First line is the scroll-stopper hook (same as or adapted from the hook)
  - Ultra-concise, punchy, every word earns its place
  - Ends with a strong CTA

"youtube_title": SEO-optimized title (max 60 chars, includes primary keyword)

"youtube_description": YouTube video description (200-300 words).
  - First 2 sentences are keyword-rich (shown in search)
  - Includes timestamps placeholder: [00:00 Hook, 01:30 Problem, ...]
  - 3-5 relevant hashtags at the end

"instagram_caption": Instagram Reel caption (150-220 chars + hashtags).
  - Conversational opening line
  - Maximum 30 hashtags, mix of niche and broad

"tags": JSON array of 10-15 YouTube tags (strings)

Return ONLY the JSON object, no markdown code fences."""

        logger.info("Generating scripts for idea #%d: %s", idea_id, idea["title"])
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        script_data = json.loads(raw)

        tags_json = json.dumps(script_data.get("tags", []))
        conn = self._get_conn()
        cur = conn.execute(
            """INSERT INTO content_scripts
               (idea_id, youtube_script, reel_script, youtube_title,
                youtube_description, instagram_caption, tags, language, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
            (
                idea_id,
                script_data.get("youtube_script", ""),
                script_data.get("reel_script", ""),
                script_data.get("youtube_title", idea["title"]),
                script_data.get("youtube_description", ""),
                script_data.get("instagram_caption", ""),
                tags_json,
                language,
            ),
        )
        conn.commit()
        script_id = cur.lastrowid

        # Update idea status to 'scripted'
        conn.execute("UPDATE content_ideas SET status='scripted' WHERE id=?", (idea_id,))
        conn.commit()

        result = self.db.get_content_script(script_id)
        result["tags"] = json.loads(result["tags"]) if result.get("tags") else []
        logger.info("Saved script #%d for idea #%d", script_id, idea_id)
        return result

    async def run(self, campaign_id: int) -> dict:
        """Run scripting for all 'approved' ideas in the system."""
        ideas = self.db.list_content_ideas(status="approved")
        scripts_generated = 0
        for idea in ideas:
            try:
                await self.generate_script(idea["id"])
                scripts_generated += 1
            except Exception as exc:
                logger.error("Failed to script idea #%d: %s", idea["id"], exc)
        return {
            "status": "completed",
            "scripts_generated": scripts_generated,
            "campaign_id": campaign_id,
        }
