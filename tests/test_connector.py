"""
Tests for the Connector agent (Epic 10).
All tests run offline — no API calls.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile
import pytest

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def db():
    """Create a fresh in-memory DatabaseManager with connector tables."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    mgr = DatabaseManager(db_path=db_path)
    mgr.init_schema()
    mgr.add_connector_tables()
    yield mgr
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture()
def tracker(db):
    from eworks.agents.connector.conversation_tracker import ConversationTracker
    return ConversationTracker(db)


@pytest.fixture()
def generator():
    from eworks.agents.connector.reply_generator import ReplyGenerator
    return ReplyGenerator()


# ─── DB Table Tests ────────────────────────────────────────────────────────────


def test_connector_tables_created(db):
    """social_interactions, conversation_threads, connector_runs must exist."""
    with db.get_connection() as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert 'social_interactions' in tables
    assert 'conversation_threads' in tables
    assert 'connector_runs' in tables


# ─── Lead Signal Detection ─────────────────────────────────────────────────────


def test_lead_signal_detection_meeting(generator):
    """'meeting' should trigger lead detection."""
    is_lead, signal = generator.detect_lead_signal(
        'Can we schedule a meeting to discuss this?'
    )
    assert is_lead is True
    assert 'meeting' in signal


def test_lead_signal_detection_price(generator):
    """'price' should trigger lead detection."""
    is_lead, signal = generator.detect_lead_signal(
        'What is the price for your services?'
    )
    assert is_lead is True
    assert 'price' in signal


def test_lead_signal_no_signal(generator):
    """A neutral comment should not trigger lead detection."""
    is_lead, signal = generator.detect_lead_signal(
        'This is a really interesting post, thanks for sharing!'
    )
    assert is_lead is False
    assert signal == ''


def test_lead_signal_portuguese(generator):
    """'reunião' (Portuguese for meeting) should trigger lead detection."""
    is_lead, signal = generator.detect_lead_signal(
        'Podemos marcar uma reunião para falar sobre isso?'
    )
    assert is_lead is True
    assert 'reunião' in signal


# ─── Sentiment Analysis ────────────────────────────────────────────────────────


def test_sentiment_positive(generator):
    """Positive keywords should return 'positive' sentiment."""
    sentiment = generator.analyze_sentiment('This is amazing work, thanks so much!')
    assert sentiment == 'positive'


def test_sentiment_negative(generator):
    """Negative keywords should return 'negative' sentiment."""
    sentiment = generator.analyze_sentiment('This is terrible and awful content, stop posting.')
    assert sentiment == 'negative'


def test_sentiment_neutral(generator):
    """Neutral text should return 'neutral' sentiment."""
    sentiment = generator.analyze_sentiment('I watched the video yesterday.')
    assert sentiment == 'neutral'


# ─── Language Detection ────────────────────────────────────────────────────────


def test_language_detection_en(generator):
    """Clear English text should be detected as 'en'."""
    lang = generator.detect_language('This is a great post about artificial intelligence.')
    assert lang == 'en'


def test_language_detection_pt(generator):
    """Portuguese text with multiple PT indicators should be detected as 'pt'."""
    lang = generator.detect_language('Você não sabe como isso funciona para mim muito bem.')
    assert lang == 'pt'


# ─── Conversation Tracker Tests ────────────────────────────────────────────────


def test_cooldown_check_empty_db(tracker):
    """No cooldown should be enforced on an empty DB."""
    result = tracker.is_in_cooldown('instagram', 'user_123')
    assert result is False


def test_save_interaction(tracker):
    """Saving an interaction should persist it and return a valid ID."""
    interaction = {
        'platform': 'instagram',
        'interaction_type': 'comment',
        'external_id': 'ig_comment_001',
        'parent_id': 'post_abc',
        'author_username': 'test_user',
        'author_id': 'test_user',
        'author_name': 'Test User',
        'content': 'This is a test comment.',
        'url': 'https://instagram.com/p/abc',
    }
    analysis = {
        'language': 'en',
        'sentiment': 'positive',
        'is_lead': False,
        'lead_signal': '',
        'confidence': 0.85,
    }
    interaction_id = tracker.save_interaction(interaction, analysis)
    assert interaction_id > 0

    # Verify it was saved
    pending = tracker.get_pending(platform='instagram')
    assert len(pending) == 1
    assert pending[0]['external_id'] == 'ig_comment_001'
    assert pending[0]['sentiment'] == 'positive'
    assert pending[0]['confidence'] == pytest.approx(0.85)


def test_already_seen(tracker):
    """Duplicate interactions should be detected correctly."""
    interaction = {
        'platform': 'x',
        'interaction_type': 'mention',
        'external_id': 'tweet_xyz_999',
        'parent_id': 'thread_001',
        'author_username': 'someone',
        'author_id': 'someone',
        'author_name': 'Someone',
        'content': 'Hey, what do you think about this?',
        'url': 'https://x.com/i/web/status/tweet_xyz_999',
    }
    analysis = {'language': 'en', 'sentiment': 'neutral', 'is_lead': False, 'lead_signal': '', 'confidence': 0.7}

    # First save — not seen
    assert tracker.is_already_seen('x', 'tweet_xyz_999') is False
    tracker.save_interaction(interaction, analysis)

    # Second check — should be seen now
    assert tracker.is_already_seen('x', 'tweet_xyz_999') is True


# ─── Slack Notifier Tests ──────────────────────────────────────────────────────


def test_slack_notifier_skips_when_unconfigured():
    """SlackNotifier should return {'status': 'skipped'} when no token is configured."""
    # Ensure token is not set
    os.environ.pop('SLACK_BOT_TOKEN', None)
    from eworks.agents.connector.slack_notifier import SlackNotifier
    notifier = SlackNotifier()
    result = notifier.notify_interaction(
        platform='instagram',
        interaction={
            'id': 1,
            'author_username': 'testuser',
            'content': 'Hello there!',
            'url': '',
            'sentiment': 'neutral',
        },
        confidence=0.5,
        reason='Test',
    )
    assert result.get('status') == 'skipped'


# ─── Exchange Count Tests ──────────────────────────────────────────────────────


def test_exchange_count_zero(tracker):
    """A new thread with no prior replies should have exchange count = 0."""
    count = tracker.get_exchange_count('linkedin', 'post_brand_new', 'author_abc')
    assert count == 0
