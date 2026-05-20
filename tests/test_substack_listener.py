"""
Tests for SubstackListener (Epic 11: Connector — Substack listener).
All tests run offline — no real HTTP calls; requests is fully mocked.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from eworks.agents.connector.substack_listener import SubstackListener, _utcnow, _parse_iso


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _recent_date() -> str:
    """ISO date from 5 days ago — within the 30-day post window."""
    return (datetime.now(tz=timezone.utc) - timedelta(days=5)).isoformat()


def _old_date() -> str:
    """ISO date from 45 days ago — outside the 30-day post window."""
    return (datetime.now(tz=timezone.utc) - timedelta(days=45)).isoformat()


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def listener():
    """SubstackListener with valid env vars."""
    env = {
        "SUBSTACK_EMAIL": "user@example.com",
        "SUBSTACK_PASSWORD": "password123",
        "SUBSTACK_PUBLICATION_URL": "mypub.substack.com",
    }
    with patch.dict(os.environ, env):
        return SubstackListener()


@pytest.fixture()
def listener_no_creds():
    """SubstackListener without any Substack env vars."""
    env = os.environ.copy()
    for key in ("SUBSTACK_EMAIL", "SUBSTACK_PASSWORD", "SUBSTACK_PUBLICATION_URL"):
        env.pop(key, None)
    with patch.dict(os.environ, env, clear=True):
        return SubstackListener()


@pytest.fixture()
def mock_session():
    """A mock requests.Session with default successful responses."""
    sess = MagicMock()
    login_resp = MagicMock()
    login_resp.raise_for_status.return_value = None
    sess.post.return_value = login_resp
    return sess


# ─── Initialisation ───────────────────────────────────────────────────────────


class TestSubstackListenerInit:
    def test_credentials_loaded(self, listener):
        """Email, password, and publication URL are read from env vars."""
        assert listener.email == "user@example.com"
        assert listener.password == "password123"
        assert "mypub.substack.com" in listener.publication_url

    def test_is_configured_true(self, listener):
        """_is_configured() returns True when all credentials present."""
        assert listener._is_configured() is True

    def test_is_configured_false_when_env_missing(self, listener_no_creds):
        """_is_configured() returns False when credentials absent."""
        assert listener_no_creds._is_configured() is False

    def test_session_starts_as_none(self, listener):
        """_session is None on fresh initialisation (lazy login)."""
        assert listener._session is None

    def test_api_base_correct(self, listener):
        """_api_base() produces the correct URL for the publication."""
        assert listener._api_base() == "https://mypub.substack.com/api/v1"


# ─── _get_session ─────────────────────────────────────────────────────────────


class TestGetSession:
    def test_returns_none_when_not_configured(self, listener_no_creds):
        """_get_session() returns None when credentials are missing."""
        result = listener_no_creds._get_session()
        assert result is None

    def test_successful_login_returns_session(self, listener, mock_session):
        """_get_session() returns a session after a successful login."""
        import requests

        with patch("requests.Session", return_value=mock_session):
            sess = listener._get_session()

        assert sess is not None

    def test_session_is_cached_after_first_call(self, listener, mock_session):
        """_get_session() does not re-authenticate on repeated calls."""
        import requests

        with patch("requests.Session", return_value=mock_session):
            listener._get_session()
            listener._get_session()

        # post (login) should only be called once
        assert mock_session.post.call_count == 1

    def test_returns_none_on_http_error(self, listener):
        """_get_session() returns None if login raises HTTPError."""
        import requests

        mock_sess = MagicMock()
        error_resp = MagicMock()
        error_resp.text = "Unauthorized"
        http_err = requests.HTTPError(response=error_resp)
        error_resp.raise_for_status.side_effect = http_err
        mock_sess.post.return_value = error_resp

        with patch("requests.Session", return_value=mock_sess):
            result = listener._get_session()

        assert result is None

    def test_logout_clears_session(self, listener, mock_session):
        """logout() forces re-login on the next _get_session() call."""
        import requests

        with patch("requests.Session", return_value=mock_session):
            listener._get_session()
            listener.logout()
            assert listener._session is None


# ─── get_recent_posts ─────────────────────────────────────────────────────────


class TestGetRecentPosts:
    def test_returns_posts_within_window(self, listener):
        """get_recent_posts() includes posts published within 30 days."""
        posts_payload = [
            {
                "id": 1,
                "title": "Recent Post",
                "slug": "recent-post",
                "post_date": _recent_date(),
                "canonical_url": "https://mypub.substack.com/p/recent-post",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = posts_payload

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            posts = listener.get_recent_posts()

        assert len(posts) == 1
        assert posts[0]["id"] == "1"
        assert posts[0]["title"] == "Recent Post"

    def test_filters_out_old_posts(self, listener):
        """get_recent_posts() excludes posts older than 30 days."""
        posts_payload = [
            {
                "id": 2,
                "title": "Old Post",
                "slug": "old-post",
                "post_date": _old_date(),
                "canonical_url": "https://mypub.substack.com/p/old-post",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = posts_payload

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            posts = listener.get_recent_posts()

        assert posts == []

    def test_returns_empty_when_session_none(self, listener):
        """get_recent_posts() returns [] when _get_session() returns None."""
        with patch.object(listener, "_get_session", return_value=None):
            posts = listener.get_recent_posts()

        assert posts == []

    def test_accepts_posts_dict_wrapper(self, listener):
        """get_recent_posts() handles API responses that wrap posts under 'posts' key."""
        wrapped = {
            "posts": [
                {
                    "id": 5,
                    "title": "Wrapped",
                    "slug": "wrapped",
                    "post_date": _recent_date(),
                    "canonical_url": "https://mypub.substack.com/p/wrapped",
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = wrapped

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            posts = listener.get_recent_posts()

        assert len(posts) == 1


# ─── get_comments ─────────────────────────────────────────────────────────────


class TestGetComments:
    def test_returns_top_level_comments(self, listener):
        """get_comments() returns comments from the API response."""
        comments_data = {
            "comments": [
                {"id": 101, "body": "Great post!", "user": {"name": "Alice"}, "children": []},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = comments_data

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            comments = listener.get_comments("post_1")

        assert len(comments) == 1
        assert comments[0]["id"] == 101

    def test_flattens_nested_children(self, listener):
        """get_comments() flattens child replies into the returned list."""
        comments_data = {
            "comments": [
                {
                    "id": 200,
                    "body": "Parent comment",
                    "user": {"name": "Bob"},
                    "children": [
                        {"id": 201, "body": "Child reply", "user": {"name": "Carol"}},
                    ],
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = comments_data

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            comments = listener.get_comments("post_2")

        # Both parent and child should be in the flat list
        assert len(comments) == 2
        ids = {c["id"] for c in comments}
        assert 200 in ids
        assert 201 in ids

    def test_adds_post_id_to_each_comment(self, listener):
        """get_comments() injects _post_id onto every comment for correlation."""
        comments_data = {"comments": [{"id": 300, "body": "Hello", "children": []}]}
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = comments_data

        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch.object(listener, "_get_session", return_value=mock_sess):
            comments = listener.get_comments("post_xyz")

        assert all(c["_post_id"] == "post_xyz" for c in comments)

    def test_returns_empty_when_session_none(self, listener):
        """get_comments() returns [] when _get_session() returns None."""
        with patch.object(listener, "_get_session", return_value=None):
            comments = listener.get_comments("any_post")

        assert comments == []


# ─── scan — interaction dict structure ────────────────────────────────────────


class TestScanInteractionStructure:
    def test_scan_returns_correct_keys(self, listener):
        """scan() items contain all required interaction dict keys."""
        mock_post = {
            "id": "42",
            "title": "My Post",
            "slug": "my-post",
            "post_date": _recent_date(),
            "canonical_url": "https://mypub.substack.com/p/my-post",
        }
        mock_comment = {
            "id": 500,
            "_post_id": "42",
            "body": "Fascinating article!",
            "user": {"name": "Dave", "id": "dave_1"},
            "user_id": "dave_1",
            "created_at": _recent_date(),
            "children": [],
        }

        with (
            patch.object(listener, "get_recent_posts", return_value=[mock_post]),
            patch.object(listener, "get_comments", return_value=[mock_comment]),
            patch("time.sleep"),
        ):
            result = listener.scan()

        assert len(result) == 1
        item = result[0]
        required_keys = {
            "platform",
            "interaction_type",
            "external_id",
            "author_id",
            "author_username",
            "author_name",
            "content",
            "parent_id",
            "url",
            "created_at",
            "raw",
        }
        missing = required_keys - set(item.keys())
        assert not missing, f"Missing keys: {missing}"
        assert item["platform"] == "substack"
        assert item["interaction_type"] == "comment"

    def test_scan_skips_empty_body(self, listener):
        """scan() skips comments with no body."""
        mock_post = {
            "id": "99",
            "title": "Empty Test",
            "slug": "empty",
            "post_date": _recent_date(),
            "canonical_url": "https://mypub.substack.com/p/empty",
        }
        mock_comment = {
            "id": 600,
            "_post_id": "99",
            "body": "",           # empty body — should be skipped
            "user": {"name": "Eve"},
            "user_id": "eve_1",
            "created_at": _recent_date(),
            "children": [],
        }

        with (
            patch.object(listener, "get_recent_posts", return_value=[mock_post]),
            patch.object(listener, "get_comments", return_value=[mock_comment]),
            patch("time.sleep"),
        ):
            result = listener.scan()

        assert result == []


# ─── scan — deduplication ─────────────────────────────────────────────────────


class TestScanDeduplication:
    def test_scan_skips_already_seen_comments_with_db(self, listener):
        """scan() with a db handle skips comments already in social_interactions."""
        mock_post = {
            "id": "10",
            "title": "Test",
            "slug": "test",
            "post_date": _recent_date(),
            "canonical_url": "https://mypub.substack.com/p/test",
        }
        mock_comment = {
            "id": 700,
            "_post_id": "10",
            "body": "Already seen this comment",
            "user": {"name": "Frank"},
            "user_id": "f1",
            "created_at": _recent_date(),
            "children": [],
        }
        mock_db = MagicMock()

        with (
            patch.object(listener, "get_recent_posts", return_value=[mock_post]),
            patch.object(listener, "get_comments", return_value=[mock_comment]),
            patch.object(listener, "_is_seen", return_value=True),
            patch("time.sleep"),
        ):
            result = listener.scan(db=mock_db)

        assert result == []

    def test_scan_includes_new_comments_with_db(self, listener):
        """scan() with a db handle includes comments not yet seen."""
        mock_post = {
            "id": "11",
            "title": "New",
            "slug": "new",
            "post_date": _recent_date(),
            "canonical_url": "https://mypub.substack.com/p/new",
        }
        mock_comment = {
            "id": 800,
            "_post_id": "11",
            "body": "Brand new comment",
            "user": {"name": "Grace"},
            "user_id": "g1",
            "created_at": _recent_date(),
            "children": [],
        }
        mock_db = MagicMock()

        with (
            patch.object(listener, "get_recent_posts", return_value=[mock_post]),
            patch.object(listener, "get_comments", return_value=[mock_comment]),
            patch.object(listener, "_is_seen", return_value=False),
            patch("time.sleep"),
        ):
            result = listener.scan(db=mock_db)

        assert len(result) == 1
        assert result[0]["external_id"] == "800"


# ─── No-op when unconfigured ──────────────────────────────────────────────────


class TestNoOpWhenUnconfigured:
    def test_scan_returns_empty_list(self, listener_no_creds):
        """scan() returns [] immediately when credentials are absent."""
        result = listener_no_creds.scan()
        assert result == []

    def test_get_recent_posts_returns_empty(self, listener_no_creds):
        """get_recent_posts() returns [] when credentials are absent."""
        result = listener_no_creds.get_recent_posts()
        assert result == []

    def test_get_comments_returns_empty(self, listener_no_creds):
        """get_comments() returns [] when credentials are absent."""
        result = listener_no_creds.get_comments("post_1")
        assert result == []


# ─── Helper function tests ────────────────────────────────────────────────────


class TestHelperFunctions:
    def test_parse_iso_valid_utc(self):
        """_parse_iso() parses a valid UTC ISO-8601 string."""
        result = _parse_iso("2024-03-15T08:00:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3

    def test_parse_iso_empty_returns_none(self):
        """_parse_iso() returns None for an empty string."""
        assert _parse_iso("") is None

    def test_parse_iso_invalid_returns_none(self):
        """_parse_iso() returns None for a non-date string."""
        assert _parse_iso("not-a-date") is None

    def test_utcnow_is_aware(self):
        """_utcnow() returns a timezone-aware datetime."""
        now = _utcnow()
        assert now.tzinfo is not None
