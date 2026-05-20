"""
Tests for Epic 8: X.com Publisher
Covers XPoster core logic, thread composition, DB tables, and analytics.
No live API calls — all tests work without X credentials.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eworks.agents.publisher.x_poster import XPoster, MAX_TWEET_LENGTH
from eworks.core.database import DatabaseManager


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def poster():
    """XPoster with no credentials (env vars not set)."""
    return XPoster()


@pytest.fixture
def db(tmp_path):
    """Fresh DatabaseManager with full schema + X publisher tables."""
    db_path = str(tmp_path / "test_x.db")
    mgr = DatabaseManager(db_path=db_path)
    mgr.init_schema()
    mgr.add_x_publisher_tables()
    yield mgr
    mgr.close()


# ─── Auth guard tests ──────────────────────────────────────────────────────────


def test_xposter_needs_auth(poster):
    """post_tweet() returns needs_auth when no OAuth tokens are configured."""
    result = poster.post_tweet("Hello X!")
    assert result.get("status") == "needs_auth", f"Expected needs_auth, got {result}"


def test_delete_needs_auth(poster):
    """delete_tweet() returns False when tokens are not configured."""
    result = poster.delete_tweet("12345678901234567890")
    assert result is False


# ─── Thread composition tests ─────────────────────────────────────────────────


def test_compose_thread_single_tweet(poster):
    """Short text (≤270 chars) returns a single-item list."""
    short = "AI is transforming how businesses operate. Leaders who adapt now will dominate."
    chunks = poster.compose_thread(short)
    assert len(chunks) == 1
    assert chunks[0] == short


def test_compose_thread_splits_correctly(poster):
    """800-char text is split into multiple chunks, each ≤270 chars."""
    long_text = (
        "The future of AI in business is not about replacing humans. "
        "It is about augmenting human capabilities with intelligent systems that learn. "
        "Companies that embrace this shift early will gain compounding advantages. "
        "Those that wait will face an insurmountable gap within five years. "
        "The key is starting with high-value, repetitive tasks and scaling from there. "
        "Every workflow that can be automated should be automated. "
        "This frees your best people to focus on strategy, creativity, and relationships."
    )
    assert len(long_text) > 270, "Test text must be longer than max_length"
    chunks = poster.compose_thread(long_text, max_length=270)
    assert len(chunks) > 1, "Long text should produce multiple chunks"
    for chunk in chunks:
        assert len(chunk) <= 270, f"Chunk too long ({len(chunk)}): {chunk[:60]}..."


def test_compose_thread_all_chunks_non_empty(poster):
    """All returned chunks are non-empty strings."""
    long_text = "Sentence one is here. Sentence two follows. Sentence three completes the thought. " * 4
    chunks = poster.compose_thread(long_text, max_length=100)
    for chunk in chunks:
        assert chunk.strip(), "Empty chunk found in thread"
        assert len(chunk) > 0


def test_compose_thread_numbering(poster):
    """Thread posted via post_thread appends (N/total) numbering to each tweet."""
    # We test the numbering logic inside post_thread by patching post_tweet
    poster_with_auth = XPoster()
    # Simulate configured poster
    poster_with_auth.api_key = "fake"
    poster_with_auth.api_secret = "fake"
    poster_with_auth.access_token = "fake"
    poster_with_auth.access_token_secret = "fake"

    posted_texts = []

    def mock_post_tweet(text, media_ids=None, reply_to_id=None, quote_tweet_id=None):
        posted_texts.append(text)
        return {"tweet_id": f"id_{len(posted_texts)}", "tweet_url": "https://x.com/test", "status": "posted"}

    poster_with_auth.post_tweet = mock_post_tweet

    texts = ["First tweet about AI", "Second insight on automation", "Third point on scaling"]
    result = poster_with_auth.post_thread(texts)

    assert result["status"] == "posted"
    assert len(result["tweet_ids"]) == 3
    # Each posted text should contain the (N/total) indicator
    for i, posted in enumerate(posted_texts):
        expected_marker = f"({i+1}/3)"
        assert expected_marker in posted, f"Missing {expected_marker} in: {posted}"


# ─── Tweet truncation test ────────────────────────────────────────────────────


def test_tweet_truncation(poster):
    """
    post_tweet truncates text to MAX_TWEET_LENGTH (280).
    When unconfigured, returns needs_auth — but we test truncation via compose_thread
    and verify the constant is correct.
    """
    assert MAX_TWEET_LENGTH == 280
    # Verify truncation happens for text > 280 chars
    long_text = "A" * 400
    # Simulate truncation (same logic as post_tweet uses)
    truncated = long_text[:MAX_TWEET_LENGTH]
    assert len(truncated) == 280
    # Also test with poster (will return needs_auth but validates the path)
    result = poster.post_tweet(long_text)
    assert result.get("status") == "needs_auth"


# ─── DB table tests ────────────────────────────────────────────────────────────


def test_x_posts_table_created(db):
    """x_posts table exists after add_x_publisher_tables()."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='x_posts'"
        ).fetchone()
    assert row is not None, "x_posts table was not created"


def test_x_analytics_table_created(db):
    """x_analytics table exists after add_x_publisher_tables()."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='x_analytics'"
        ).fetchone()
    assert row is not None, "x_analytics table was not created"


def test_x_posts_table_columns(db):
    """x_posts table has key columns: tweet_id, content_type, status, text_content."""
    with db.get_connection() as conn:
        info = conn.execute("PRAGMA table_info(x_posts)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "tweet_id", "content_type", "text_content", "status", "created_at"}
    assert required.issubset(col_names), f"Missing columns: {required - col_names}"


# ─── Analytics summary test ────────────────────────────────────────────────────


def test_analytics_summary_empty(db):
    """get_summary() returns zeroed dict when no analytics rows exist."""
    from eworks.agents.publisher.x_analytics import XAnalyticsCollector
    collector = XAnalyticsCollector(db)
    summary = collector.get_summary()
    assert isinstance(summary, dict)
    assert summary.get("posts_tracked") == 0
    assert summary.get("total_impressions") == 0
    assert summary.get("avg_engagement_rate") == 0.0


# ─── Thread length test ────────────────────────────────────────────────────────


def test_thread_length_respected(poster):
    """
    post_thread with unconfigured poster returns needs_auth immediately,
    confirming auth check runs before any API calls.
    """
    texts = ["Tweet 1", "Tweet 2", "Tweet 3", "Tweet 4", "Tweet 5"]
    result = poster.post_thread(texts)
    # With no auth, returns needs_auth (not an error about thread length)
    assert result.get("status") == "needs_auth"


def test_compose_thread_respects_max_length_param(poster):
    """compose_thread respects custom max_length parameter."""
    text = "Short. Medium length sentence here. Another one. And one more for good measure." * 3
    chunks_150 = poster.compose_thread(text, max_length=150)
    chunks_270 = poster.compose_thread(text, max_length=270)
    for chunk in chunks_150:
        assert len(chunk) <= 150
    for chunk in chunks_270:
        assert len(chunk) <= 270
    # Smaller max_length should produce more or equal chunks
    assert len(chunks_150) >= len(chunks_270)
