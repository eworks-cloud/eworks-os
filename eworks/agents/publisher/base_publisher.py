"""Base publisher class for content pipeline agents."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from eworks.agents.base import BaseAgent


class BasePublisher(BaseAgent):
    """Base class for all publisher agents.
    
    Extends BaseAgent with publisher-specific helpers and config.
    """

    def __init__(self, db, config):
        super().__init__(db, config)
        self.data_dir = Path("data")
        self.videos_dir = self.data_dir / "videos"
        self.audio_dir = self.data_dir / "audio"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # API keys from environment
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.heygen_api_key = os.environ.get("HEYGEN_API_KEY", "")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self.instagram_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self.instagram_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")

    async def run(self, campaign_id: int) -> dict:
        """Default run — override in subclasses."""
        raise NotImplementedError("Subclasses must implement run()")

    def _get_conn(self):
        """Convenience: return the database connection."""
        return self.db.get_connection()

    def validate_message(self, text: str, max_words: int | None = None) -> bool:
        """Basic validation: non-empty, optionally within word limit."""
        if not text or not text.strip():
            return False
        if max_words:
            word_count = len(text.split())
            if word_count > max_words:
                return False
        return True
