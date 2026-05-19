"""Tests for ICPScorer — weighted ideal customer profile scoring."""
from __future__ import annotations

import pytest

from eworks.agents.prospector.discovery import ICPScorer


@pytest.fixture
def scorer():
    return ICPScorer()


def test_ceo_scores_high(scorer):
    """A CEO at a tech company in Brazil should score well above 70."""
    prospect = {
        "full_name": "Ana Silva",
        "headline": "CEO at TechStartup Brasil",
        "company": "TechStartup",
        "location": "São Paulo, Brazil",
        "about": "We are a SaaS startup building AI tools",
        "mutual_connections": 3,
    }
    result = scorer.score(prospect)
    assert result["score"] > 70, f"Expected > 70, got {result['score']}"
    assert result["breakdown"]["title_match"] == 30.0


def test_unknown_title_scores_low(scorer):
    """A generic/unknown job title with no signals should score < 30."""
    prospect = {
        "full_name": "Bob Generic",
        "headline": "Professional at Generic Corp",
        "company": "Generic Corp",
        "location": "Unknown City",
        "about": "",
        "mutual_connections": 0,
    }
    result = scorer.score(prospect)
    assert result["score"] < 30, f"Expected < 30, got {result['score']}"


def test_location_boost(scorer):
    """Brazil location should earn 15 location points."""
    prospect_brazil = {
        "headline": "Staff Engineer",
        "location": "Curitiba, Brazil",
        "mutual_connections": 0,
    }
    prospect_other = {
        "headline": "Staff Engineer",
        "location": "Nairobi, Kenya",
        "mutual_connections": 0,
    }
    score_brazil = scorer.score(prospect_brazil)["breakdown"]["location_match"]
    score_other = scorer.score(prospect_other)["breakdown"]["location_match"]

    assert score_brazil == 15.0, f"Brazil should get 15, got {score_brazil}"
    assert score_other < 15.0, f"Other should get < 15, got {score_other}"


def test_mutual_connections_boost(scorer):
    """Having any mutual connections should add exactly 15 engagement points."""
    prospect_with = {
        "headline": "Software Engineer",
        "location": "Remote",
        "mutual_connections": 2,
    }
    prospect_without = {
        "headline": "Software Engineer",
        "location": "Remote",
        "mutual_connections": 0,
    }
    score_with = scorer.score(prospect_with)["breakdown"]["engagement_signal"]
    score_without = scorer.score(prospect_without)["breakdown"]["engagement_signal"]

    assert score_with == 15.0
    assert score_without == 0.0
