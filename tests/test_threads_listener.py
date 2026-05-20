"""
Tests for ThreadsListener (Epic 11: Connector — Threads listener).
All tests run offline — no real HTTP calls; aiohttp is fully mocked.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eworks.agents.connector.threads_listener import ThreadsListener


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _recent_ts() -> str:
    """ISO-8601 timestamp two minutes ago (well within any scan window)."""
    return (datetime.now(tz=timezone.utc) - timedelta(minutes=2)).isoformat()


def _old_ts() -> str:
    """ISO-8601 timestamp 60 minutes ago (outside default 15-min window)."""
    return (datetime.now(tz=timezone.utc) - timedelta(minutes=60)).isoformat()


def run(coro):
    """Synchronous helper to execute an async coroutine in tests."""
    return asyncio.run(coro)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def listener():
    """ThreadsListener with both env vars set."""
    with patch.dict(
        os.environ,
        {"THREADS_ACCESS_TOKEN": "tok123", "THREADS_USER_ID": "uid999"},
    ):
        return ThreadsListener()


@pytest.fixture()
def listener_no_creds():
    """ThreadsListener without any Threads env vars."""
    env = os.environ.copy()
    env.pop("THREADS_ACCESS_TOKEN", None)
    env.pop("THREADS_USER_ID", None)
    with patch.dict(os.environ, env, clear=True):
        return ThreadsListener()


# ─── Initialisation ───────────────────────────────────────────────────────────


class TestThreadsListenerInit:
    def test_access_token_loaded(self, listener):
        """THREADS_ACCESS_TOKEN is read from the environment."""
        assert listener.access_token == "tok123"

    def test_user_id_loaded(self, listener):
        """THREADS_USER_ID is read from the environment."""
        assert listener.user_id == "uid999"

    def test_empty_creds_when_env_absent(self, listener_no_creds):
        """access_token and user_id default to empty strings."""
        assert listener_no_creds.access_token == ""
        assert listener_no_creds.user_id == ""


# ─── get_recent_posts ─────────────────────────────────────────────────────────


class TestGetRecentPosts:
    def test_returns_posts_from_api(self, listener):
        """get_recent_posts() returns the data array from the API response."""
        posts = [
            {"id": "post_1", "text": "Hello", "timestamp": _recent_ts(), "username": "alice"},
            {"id": "post_2", "text": "World", "timestamp": _recent_ts(), "username": "alice"},
        ]
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch.object(
            listener,
            "_get",
            new=AsyncMock(return_value={"data": posts}),
        ):
            result = run(listener.get_recent_posts(mock_session, limit=5))

        assert len(result) == 2
        assert result[0]["id"] == "post_1"

    def test_returns_empty_list_on_empty_response(self, listener):
        """get_recent_posts() returns [] when the API returns no data."""
        mock_session = MagicMock()

        with patch.object(listener, "_get", new=AsyncMock(return_value={})):
            result = run(listener.get_recent_posts(mock_session))

        assert result == []


# ─── get_replies ──────────────────────────────────────────────────────────────


class TestGetReplies:
    def test_returns_replies_from_api(self, listener):
        """get_replies() returns the reply data array for a post."""
        replies = [
            {"id": "reply_1", "text": "Nice!", "timestamp": _recent_ts(), "username": "bob"},
        ]
        mock_session = MagicMock()

        with patch.object(
            listener,
            "_get",
            new=AsyncMock(return_value={"data": replies}),
        ):
            result = run(listener.get_replies(mock_session, "post_1"))

        assert len(result) == 1
        assert result[0]["id"] == "reply_1"

    def test_returns_empty_list_when_no_replies(self, listener):
        """get_replies() returns [] when the post has no replies."""
        mock_session = MagicMock()

        with patch.object(listener, "_get", new=AsyncMock(return_value={})):
            result = run(listener.get_replies(mock_session, "post_99"))

        assert result == []


# ─── fetch_interactions ───────────────────────────────────────────────────────


class TestFetchInteractions:
    def test_returns_correct_dict_structure(self, listener):
        """fetch_interactions() result items have the expected interaction keys."""
        interaction = {
            "platform": "threads",
            "interaction_type": "reply",
            "external_id": "reply_abc",
            "parent_id": "post_1",
            "author_id": "bob",
            "author_username": "bob",
            "author_name": "bob",
            "content": "Great post!",
            "url": "https://www.threads.net/@alice/post/post_1",
            "created_at": _recent_ts(),
            "raw": {},
        }
        with patch.object(listener, "scan", new=AsyncMock(return_value=[interaction])):
            result = run(listener.fetch_interactions(since_minutes=15))

        assert len(result) == 1
        item = result[0]
        for key in ("platform", "external_id", "author_id", "content", "url", "created_at"):
            assert key in item, f"Key '{key}' missing from interaction dict"
        assert item["platform"] == "threads"

    def test_returns_empty_when_no_new_interactions(self, listener):
        """fetch_interactions() returns [] when scan finds nothing."""
        with patch.object(listener, "scan", new=AsyncMock(return_value=[])):
            result = run(listener.fetch_interactions())

        assert result == []


# ─── Deduplication ────────────────────────────────────────────────────────────


class TestDeduplication:
    def test_same_interaction_not_returned_twice_with_db(self, listener):
        """fetch_interactions() skips already-seen interactions via DB."""
        interaction = {
            "platform": "threads",
            "interaction_type": "reply",
            "external_id": "dup_id_42",
            "parent_id": "p1",
            "author_id": "u1",
            "author_username": "u1",
            "author_name": "u1",
            "content": "Hello",
            "url": "https://threads.net/t/dup_id_42",
            "created_at": _recent_ts(),
            "raw": {},
        }

        mock_db = MagicMock()

        with (
            patch.object(listener, "scan", new=AsyncMock(return_value=[interaction])),
            patch.object(ThreadsListener, "_is_seen", return_value=True),
            patch.object(ThreadsListener, "_mark_seen"),
        ):
            result = run(listener.fetch_interactions(db=mock_db))

        # Already seen — should be filtered out
        assert result == []

    def test_new_interaction_marked_and_returned(self, listener):
        """fetch_interactions() marks new interactions seen and returns them."""
        interaction = {
            "platform": "threads",
            "interaction_type": "reply",
            "external_id": "new_id_99",
            "parent_id": "p2",
            "author_id": "u2",
            "author_username": "u2",
            "author_name": "u2",
            "content": "Fresh!",
            "url": "https://threads.net/t/new_id_99",
            "created_at": _recent_ts(),
            "raw": {},
        }

        mock_db = MagicMock()

        with (
            patch.object(listener, "scan", new=AsyncMock(return_value=[interaction])),
            patch.object(ThreadsListener, "_is_seen", return_value=False),
            patch.object(ThreadsListener, "_mark_seen") as mock_mark,
        ):
            result = run(listener.fetch_interactions(db=mock_db))

        assert len(result) == 1
        mock_mark.assert_called_once_with(mock_db, "threads", "new_id_99")


# ─── No-op when unconfigured ──────────────────────────────────────────────────


class TestNoOpWhenUnconfigured:
    def test_scan_returns_empty_list_when_no_token(self, listener_no_creds):
        """scan() returns [] without making any API calls when unconfigured."""
        result = run(listener_no_creds.scan())
        assert result == []

    def test_fetch_interactions_returns_empty_when_no_token(self, listener_no_creds):
        """fetch_interactions() returns [] when THREADS_ACCESS_TOKEN is absent."""
        result = run(listener_no_creds.fetch_interactions())
        assert result == []


# ─── Helper method tests ──────────────────────────────────────────────────────


class TestHelperMethods:
    def test_parse_ts_valid_iso(self, listener):
        """_parse_ts() parses a valid ISO-8601 string."""
        ts = "2024-01-15T10:30:00+00:00"
        result = ThreadsListener._parse_ts(ts)
        assert result is not None
        assert result.year == 2024

    def test_parse_ts_empty_returns_none(self, listener):
        """_parse_ts() returns None for an empty string."""
        assert ThreadsListener._parse_ts("") is None

    def test_is_recent_returns_true_for_recent(self, listener):
        """_is_recent() returns True when timestamp is after the cutoff."""
        ts = _recent_ts()
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=15)
        assert ThreadsListener._is_recent(ts, cutoff) is True

    def test_is_recent_returns_false_for_old(self, listener):
        """_is_recent() returns False when timestamp is before the cutoff."""
        ts = _old_ts()
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=15)
        assert ThreadsListener._is_recent(ts, cutoff) is False

    def test_post_url_with_username(self, listener):
        """_post_url() builds the @username style URL."""
        url = ThreadsListener._post_url("alice", "post_123")
        assert "@alice" in url
        assert "post_123" in url

    def test_post_url_without_username(self, listener):
        """_post_url() falls back to /t/ style when username is absent."""
        url = ThreadsListener._post_url("", "post_456")
        assert "post_456" in url
        assert "/t/" in url
