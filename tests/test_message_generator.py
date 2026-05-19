"""Tests for MessageGenerator — validation and mocked generation."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eworks.agents.prospector.generator import MessageGenerator


@pytest.fixture
def generator():
    return MessageGenerator(api_key="test-key", model="claude-opus-4-5")


# ─── Validation tests (no network needed) ────────────────────────────────────


def test_message_length_validation_fails(generator):
    """A message over 300 characters must fail validation."""
    long_message = "a" * 301
    assert generator.validate_message(long_message) is False


def test_message_length_validation_at_limit(generator):
    """A message of exactly 300 characters must pass validation."""
    message = "a" * 300
    assert generator.validate_message(message) is True


def test_message_under_limit(generator):
    """A short, realistic message must pass validation."""
    message = "Hi Ana, your work on AI-driven growth at TechCo caught my eye. Would love to connect and share how we can accelerate results."
    assert len(message) <= 300
    assert generator.validate_message(message) is True


def test_empty_message_fails(generator):
    """Empty string must fail validation."""
    assert generator.validate_message("") is False


def test_forbidden_pattern_fails(generator):
    """Messages with generic openers must fail validation."""
    generic = "Hope this message finds you well! Would love to connect."
    assert generator.validate_message(generic) is False


# ─── Generation tests (mocked Claude API) ────────────────────────────────────


def test_generate_uses_prospect_name(generator):
    """The generated message (mocked) should contain the prospect's name."""
    prospect = {
        "full_name": "Carlos Mendes",
        "headline": "CTO at Fintech Brasil",
        "company": "Fintech Brasil",
        "mutual_connections": 1,
    }
    persona = {"offer_summary": "AI automation for financial ops", "tone": "professional"}
    campaign = {"id": 1, "name": "Test Campaign"}

    # Mock Anthropic client response
    mock_content = MagicMock()
    mock_content.text = "Carlos, your work at Fintech Brasil is impressive. Let's connect — I help fintechs automate ops with AI."
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    generator._client = mock_client

    result = asyncio.run(generator.generate(prospect, persona, campaign))

    assert "Carlos" in result
    assert len(result) <= 300
    mock_client.messages.create.assert_called_once()


def test_generate_truncates_long_response(generator):
    """If Claude returns more than 300 chars, the generator must truncate it."""
    long_text = "This is a very long message that exceeds the LinkedIn character limit. " * 6
    assert len(long_text) > 300

    mock_content = MagicMock()
    mock_content.text = long_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    generator._client = mock_client

    prospect = {"full_name": "Test User", "headline": "CEO", "company": "Co", "mutual_connections": 0}
    persona = {"offer_summary": "AI tools", "tone": "professional"}
    campaign = {"id": 1}

    result = asyncio.run(generator.generate(prospect, persona, campaign))
    assert len(result) <= 300
