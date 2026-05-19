"""Configuration loader for Eworks OS.

Loads settings from:
1. config/settings.yaml (defaults)
2. .env file (overrides via environment variables)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """Application configuration — single source of truth."""

    _defaults: dict[str, Any] = {
        "database": {"path": "data/eworks.db"},
        "session": {"dir": "session/"},
        "agent": {
            "daily_connection_limit": 20,
            "icp_score_threshold": 60.0,
            "run_windows": [
                {"start": "09:00", "end": "11:30"},
                {"start": "14:00", "end": "16:30"},
            ],
            "delays": {
                "between_actions_min": 30,
                "between_actions_max": 90,
                "page_load_min": 1.5,
                "page_load_max": 4.0,
            },
        },
        "claude": {
            "model": "claude-opus-4-5",
            "max_tokens": 500,
            "message_max_chars": 300,
        },
        "linkedin": {
            "base_url": "https://www.linkedin.com",
            "connections_url": "https://www.linkedin.com/mynetwork/invite-connect/connections/",
            "viewport": {"width": 1366, "height": 768},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        "telegram": {"parse_mode": "HTML"},
        "scheduler": {"default_cron": "0 9 * * 1-5"},
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }

    def __init__(self, config_path: str = "config/settings.yaml", env_path: str = ".env"):
        # Load .env
        env_file = Path(env_path)
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug("Loaded .env from %s", env_file)
        else:
            load_dotenv()  # try default locations

        # Load yaml
        self._data = self._defaults.copy()
        yaml_file = Path(config_path)
        if yaml_file.exists():
            with yaml_file.open() as f:
                file_config = yaml.safe_load(f) or {}
            self._data = _deep_merge(self._defaults, file_config)
            logger.debug("Loaded settings from %s", yaml_file)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value using dot-path keys."""
        node = self._data
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
            if node is default:
                return default
        return node

    # ─── Typed property shortcuts ─────────────────────────────────────────────

    @property
    def database_path(self) -> str:
        return os.environ.get("DATABASE_PATH", self.get("database", "path", default="data/eworks.db"))

    @property
    def session_dir(self) -> str:
        return os.environ.get("SESSION_DIR", self.get("session", "dir", default="session/"))

    @property
    def anthropic_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def linkedin_email(self) -> str:
        return os.environ.get("LINKEDIN_EMAIL", "")

    @property
    def linkedin_password(self) -> str:
        return os.environ.get("LINKEDIN_PASSWORD", "")

    @property
    def telegram_bot_token(self) -> str:
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        return os.environ.get("TELEGRAM_CHAT_ID", "")

    @property
    def claude_model(self) -> str:
        return os.environ.get("CLAUDE_MODEL", self.get("claude", "model", default="claude-opus-4-5"))

    @property
    def daily_connection_limit(self) -> int:
        env_val = os.environ.get("DAILY_CONNECTION_LIMIT")
        if env_val:
            return int(env_val)
        return self.get("agent", "daily_connection_limit", default=20)

    @property
    def icp_score_threshold(self) -> float:
        env_val = os.environ.get("ICP_SCORE_THRESHOLD")
        if env_val:
            return float(env_val)
        return self.get("agent", "icp_score_threshold", default=60.0)

    @property
    def user_agent(self) -> str:
        return self.get("linkedin", "user_agent", default="")

    @property
    def viewport(self) -> dict:
        return self.get("linkedin", "viewport", default={"width": 1366, "height": 768})

    def __repr__(self) -> str:
        return f"Config(db={self.database_path!r})"


# Module-level singleton
_config: Config | None = None


def get_config(**kwargs) -> Config:
    """Return the global Config singleton, creating it if necessary."""
    global _config
    if _config is None:
        _config = Config(**kwargs)
    return _config
