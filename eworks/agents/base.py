"""Base agent class for all Eworks OS agents."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Abstract base for all Eworks OS agents."""

    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self, campaign_id: int) -> dict:
        """Run the agent for the given campaign. Returns a summary dict."""

    async def report_status(self, message: str) -> None:
        """Log a status message (override in subclasses to also send to Telegram)."""
        self.logger.info(message)
