"""Tests for the Content Pipeline (Publisher) agent — Epic 2."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eworks.core.database import DatabaseManager
from eworks.agents.publisher.base_publisher import BasePublisher
from eworks.agents.publisher.ideation import IdeationAgent
from eworks.agents.publisher.scripting import ScriptingAgent
from eworks.agents.publisher.video_generator import HeyGenAgent, AVATAR_ID


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a fresh in-memory-like database for each test."""
    db_path = str(tmp_path / "test.db")
    db = DatabaseManager(db_path=db_path)
    db.init_schema()
    db.add_publisher_tables()
    return db


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.anthropic_api_key = "test-key"
    cfg.heygen_api_key = "test-heygen-key"
    cfg.elevenlabs_api_key = "test-el-key"
    cfg.telegram_bot_token = "test-tg-token"
    cfg.telegram_chat_id = "123456"
    cfg.instagram_access_token = "test-ig-token"
    cfg.instagram_account_id = "test-ig-id"
    return cfg


@pytest.fixture
def ideation_agent(tmp_db, mock_config):
    return IdeationAgent(db=tmp_db, config=mock_config)


@pytest.fixture
def scripting_agent(tmp_db, mock_config):
    return ScriptingAgent(db=tmp_db, config=mock_config)


@pytest.fixture
def heygen_agent(tmp_db, mock_config):
    return HeyGenAgent(db=tmp_db, config=mock_config)


@pytest.fixture
def base_publisher(tmp_db, mock_config):
    class ConcretePublisher(BasePublisher):
        async def run(self, campaign_id: int) -> dict:
            return {}
    return ConcretePublisher(db=tmp_db, config=mock_config)


# ─── test_ideation_saves_to_db ────────────────────────────────────────────────


def test_ideation_saves_to_db(ideation_agent, tmp_db):
    """Mock Claude response; verify ideas are saved to content_ideas table."""
    mock_ideas = [
        {
            "title": "How AI Cuts Your Support Costs by 60%",
            "hook": "Your support team is burning money — here's the fix.",
            "angle": "Data-driven analysis of AI support ROI for mid-market SaaS",
            "keywords": ["AI automation", "customer support", "cost reduction", "SaaS", "ROI"],
            "format": "both",
        },
        {
            "title": "The CTO's Guide to AI Automation in 2025",
            "hook": "Most CTOs are making this automation mistake.",
            "angle": "Strategic framework for phased AI adoption without disruption",
            "keywords": ["CTO", "AI strategy", "automation", "digital transformation"],
            "format": "long-form",
        },
    ]

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_ideas))]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("eworks.agents.publisher.ideation.anthropic.Anthropic", return_value=mock_client):
        ideas = asyncio.run(ideation_agent.generate_ideas(n=2, language="en"))

    # Verify returned list
    assert len(ideas) == 2
    assert ideas[0]["title"] == "How AI Cuts Your Support Costs by 60%"
    assert ideas[1]["format"] == "long-form"

    # Verify DB persistence
    conn = tmp_db.get_connection()
    rows = conn.execute("SELECT * FROM content_ideas ORDER BY id").fetchall()
    assert len(rows) == 2
    first = dict(rows[0])
    assert first["title"] == "How AI Cuts Your Support Costs by 60%"
    assert first["status"] == "draft"
    assert first["language"] == "en"

    # Keywords stored as JSON string
    keywords = json.loads(first["keywords"])
    assert isinstance(keywords, list)
    assert "AI automation" in keywords


# ─── test_icp_script_length ───────────────────────────────────────────────────


def test_icp_script_length(scripting_agent, tmp_db):
    """Verify reel_script <= 150 words and youtube_script >= 300 words."""
    # Insert a test idea
    conn = tmp_db.get_connection()
    conn.execute(
        "INSERT INTO content_ideas (title, hook, angle, keywords, format, language) VALUES (?,?,?,?,?,?)",
        ("Test Idea", "Test hook", "Test angle", '["ai","automation"]', "both", "en"),
    )
    conn.commit()
    idea_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    reel_words = "short " * 120  # 120 words — within 150
    yt_words = "long content word " * 350  # 350 words — above 300

    mock_script_data = {
        "youtube_script": yt_words.strip(),
        "reel_script": reel_words.strip(),
        "youtube_title": "AI Automation Guide for CTOs",
        "youtube_description": "A comprehensive guide to AI automation for enterprise teams.",
        "instagram_caption": "AI is changing everything. Here's how to stay ahead. #AI #automation #CTO",
        "tags": ["AI", "automation", "CTO", "SaaS"],
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_script_data))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("eworks.agents.publisher.scripting.anthropic.Anthropic", return_value=mock_client):
        script = asyncio.run(scripting_agent.generate_script(idea_id, language="en"))

    reel_word_count = len(script["reel_script"].split())
    yt_word_count = len(script["youtube_script"].split())

    assert reel_word_count <= 150, f"Reel script too long: {reel_word_count} words"
    assert yt_word_count >= 300, f"YouTube script too short: {yt_word_count} words"


# ─── test_message_validation ──────────────────────────────────────────────────


def test_message_validation(base_publisher):
    """Test BasePublisher.validate_message() with various inputs."""
    # Valid messages
    assert base_publisher.validate_message("Hello world") is True
    assert base_publisher.validate_message("A " * 100, max_words=200) is True

    # Empty / whitespace
    assert base_publisher.validate_message("") is False
    assert base_publisher.validate_message("   ") is False
    assert base_publisher.validate_message(None) is False

    # Exceeds word limit
    long_text = " ".join(["word"] * 200)
    assert base_publisher.validate_message(long_text, max_words=150) is False
    assert base_publisher.validate_message(long_text, max_words=200) is True


# ─── test_instagram_caption_hashtags ─────────────────────────────────────────


def test_instagram_caption_hashtags(scripting_agent, tmp_db):
    """Verify generated instagram_caption has <= 30 hashtags."""
    # Insert idea
    conn = tmp_db.get_connection()
    conn.execute(
        "INSERT INTO content_ideas (title, hook, angle, keywords, format, language) VALUES (?,?,?,?,?,?)",
        ("Hashtag Test", "hook", "angle", '["ai"]', "reel", "en"),
    )
    conn.commit()
    idea_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Caption with exactly 28 hashtags (within limit)
    hashtags_28 = " ".join(f"#tag{i}" for i in range(28))
    caption_28 = f"Great content about AI automation! {hashtags_28}"

    mock_script_data = {
        "youtube_script": "word " * 400,
        "reel_script": "word " * 100,
        "youtube_title": "Test Title",
        "youtube_description": "Test description for YouTube.",
        "instagram_caption": caption_28,
        "tags": ["AI", "automation"],
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_script_data))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("eworks.agents.publisher.scripting.anthropic.Anthropic", return_value=mock_client):
        script = asyncio.run(scripting_agent.generate_script(idea_id, language="en"))

    caption = script["instagram_caption"]
    hashtag_count = caption.count("#")
    assert hashtag_count <= 30, f"Too many hashtags: {hashtag_count} (max 30)"


# ─── test_heygen_format_dimensions ───────────────────────────────────────────


def test_heygen_format_dimensions(heygen_agent):
    """Verify HeyGen agent returns correct dimensions per format."""
    reel_w, reel_h = heygen_agent._get_dimensions("reel")
    assert reel_w == 1080, f"Reel width should be 1080, got {reel_w}"
    assert reel_h == 1920, f"Reel height should be 1920, got {reel_h}"

    yt_w, yt_h = heygen_agent._get_dimensions("youtube")
    assert yt_w == 1920, f"YouTube width should be 1920, got {yt_w}"
    assert yt_h == 1080, f"YouTube height should be 1080, got {yt_h}"

    # Verify AVATAR_ID constant
    assert heygen_agent.AVATAR_ID == "494ce8a1dbe64573a4cb1684ad0e0e14"
    assert heygen_agent.AVATAR_ID == AVATAR_ID
