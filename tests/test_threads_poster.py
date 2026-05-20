"""
Tests for ThreadsPoster (Epic 11: Threads / Substack publisher).
All tests run offline — no real HTTP calls.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from eworks.agents.publisher.threads_poster import ThreadsPoster


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def sqlite_conn():
    """In-memory SQLite connection to stand in for the DB layer."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture()
def mock_db(sqlite_conn):
    """
    Mock DatabaseManager that returns a real SQLite connection
    so _get_conn() / _ensure_table() work without the full ORM.
    """
    db = MagicMock()

    @contextmanager
    def _get_connection():
        yield sqlite_conn

    db.get_connection.side_effect = _get_connection
    return db


@pytest.fixture()
def poster(mock_db):
    """ThreadsPoster with both env-var credentials set."""
    with (
        patch.dict(
            os.environ,
            {"THREADS_ACCESS_TOKEN": "test_token", "THREADS_USER_ID": "123456"},
        )
    ):
        p = ThreadsPoster(db=mock_db, config={})
    return p


@pytest.fixture()
def poster_no_creds(mock_db):
    """ThreadsPoster created without any Threads env vars."""
    env = os.environ.copy()
    env.pop("THREADS_ACCESS_TOKEN", None)
    env.pop("THREADS_USER_ID", None)
    with patch.dict(os.environ, env, clear=True):
        p = ThreadsPoster(db=mock_db, config={})
    return p


# ─── Initialisation ───────────────────────────────────────────────────────────


class TestThreadsPosterInit:
    def test_credentials_loaded_from_env(self, poster):
        """Access token and user ID are pulled from environment variables."""
        assert poster.access_token == "test_token"
        assert poster.user_id == "123456"

    def test_is_configured_true_when_both_set(self, poster):
        """_is_configured() returns True when both env vars present."""
        assert poster._is_configured() is True

    def test_is_configured_false_when_missing(self, poster_no_creds):
        """_is_configured() returns False when env vars are absent."""
        assert poster_no_creds._is_configured() is False

    def test_default_params_contains_token(self, poster):
        """_default_params() always includes the access_token key."""
        params = poster._default_params()
        assert params["access_token"] == "test_token"


# ─── _create_container ────────────────────────────────────────────────────────


class TestCreateContainer:
    def test_returns_container_id_on_success(self, poster):
        """_create_container() returns the 'id' from the API JSON."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "container_abc"}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp):
            result = poster._create_container("TEXT", text="Hello world")

        assert result == "container_abc"

    def test_raises_when_no_id_returned(self, poster):
        """_create_container() raises RuntimeError if API returns no id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "something"}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="No container ID"):
                poster._create_container("TEXT", text="Hello")

    def test_url_uses_user_id(self, poster):
        """_create_container() calls the /{user_id}/threads endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "cid_1"}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp) as mock_post:
            poster._create_container("TEXT", text="Hi")

        called_url = mock_post.call_args[0][0]
        assert "123456" in called_url
        assert "threads" in called_url


# ─── _publish_container ───────────────────────────────────────────────────────


class TestPublishContainer:
    def test_returns_post_id_on_success(self, poster):
        """_publish_container() returns the post ID from the API."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "post_xyz"}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp):
            result = poster._publish_container("container_abc")

        assert result == "post_xyz"

    def test_raises_when_no_post_id(self, poster):
        """_publish_container() raises RuntimeError if API returns no id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="No post ID"):
                poster._publish_container("container_abc")

    def test_calls_threads_publish_endpoint(self, poster):
        """_publish_container() targets the threads_publish endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "post_123"}
        mock_resp.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_resp) as mock_post:
            poster._publish_container("cid_99")

        called_url = mock_post.call_args[0][0]
        assert "threads_publish" in called_url


# ─── post_text ────────────────────────────────────────────────────────────────


class TestPostText:
    def test_returns_needs_auth_when_not_configured(self, poster_no_creds):
        """post_text() returns needs_auth when credentials are missing."""
        result = poster_no_creds.post_text("Hello threads!")
        assert result["status"] == "needs_auth"

    def test_successful_post_returns_posted_status(self, poster):
        """post_text() returns status=posted with URL on success."""
        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"id": "container_1"}
        create_resp.raise_for_status.return_value = None

        publish_resp = MagicMock()
        publish_resp.status_code = 200
        publish_resp.json.return_value = {"id": "post_111"}
        publish_resp.raise_for_status.return_value = None

        with patch("requests.post", side_effect=[create_resp, publish_resp]):
            result = poster.post_text("Hello threads!")

        assert result["status"] == "posted"
        assert result["threads_post_id"] == "post_111"
        assert "threads.net" in result["threads_url"]

    def test_truncates_long_text(self, poster):
        """post_text() truncates text to MAX_TEXT_LENGTH characters."""
        long_text = "x" * 600

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"id": "c1"}
        create_resp.raise_for_status.return_value = None

        publish_resp = MagicMock()
        publish_resp.status_code = 200
        publish_resp.json.return_value = {"id": "p1"}
        publish_resp.raise_for_status.return_value = None

        with patch("requests.post", side_effect=[create_resp, publish_resp]) as mock_post:
            poster.post_text(long_text)

        # The text param sent to _create_container must be ≤500 chars
        params_sent = mock_post.call_args_list[0][1]["params"]
        assert len(params_sent["text"]) == 500

    def test_returns_error_on_api_failure(self, poster):
        """post_text() returns status=error when the API raises RuntimeError."""
        with patch.object(poster, "_create_container", side_effect=RuntimeError("API down")):
            result = poster.post_text("Hello!")

        assert result["status"] == "error"
        assert "API down" in result["message"]


# ─── post_carousel ────────────────────────────────────────────────────────────


class TestPostCarousel:
    def test_returns_needs_auth_when_not_configured(self, poster_no_creds):
        """post_carousel() returns needs_auth when credentials missing."""
        result = poster_no_creds.post_carousel("Caption", ["https://example.com/a.jpg"])
        assert result["status"] == "needs_auth"

    def test_returns_error_for_empty_media_list(self, poster):
        """post_carousel() returns error when media_urls is empty."""
        result = poster.post_carousel("Caption", [])
        assert result["status"] == "error"
        assert "No media URLs" in result["message"]

    def test_successful_carousel_returns_item_count(self, poster):
        """post_carousel() reports the correct number of carousel items."""
        item_resp = MagicMock(status_code=200)
        item_resp.json.return_value = {"id": "item_1"}
        item_resp.raise_for_status.return_value = None

        item_resp2 = MagicMock(status_code=200)
        item_resp2.json.return_value = {"id": "item_2"}
        item_resp2.raise_for_status.return_value = None

        carousel_resp = MagicMock(status_code=200)
        carousel_resp.json.return_value = {"id": "carousel_c"}
        carousel_resp.raise_for_status.return_value = None

        publish_resp = MagicMock(status_code=200)
        publish_resp.json.return_value = {"id": "post_carousel_1"}
        publish_resp.raise_for_status.return_value = None

        with (
            patch("requests.post", side_effect=[item_resp, item_resp2, carousel_resp, publish_resp]),
            patch("time.sleep"),
        ):
            result = poster.post_carousel(
                "My carousel",
                ["https://example.com/a.jpg", "https://example.com/b.jpg"],
            )

        assert result["status"] == "posted"
        assert result["item_count"] == 2
        assert result["threads_post_id"] == "post_carousel_1"

    def test_carousel_caps_at_max_items(self, poster):
        """post_carousel() uses at most MAX_CAROUSEL_ITEMS URLs."""
        from eworks.agents.publisher.threads_poster import MAX_CAROUSEL_ITEMS

        urls = [f"https://example.com/{i}.jpg" for i in range(MAX_CAROUSEL_ITEMS + 5)]

        # One response per item + carousel container + publish
        total_calls = MAX_CAROUSEL_ITEMS + 2
        responses = []
        for i in range(MAX_CAROUSEL_ITEMS):
            r = MagicMock(status_code=200)
            r.json.return_value = {"id": f"item_{i}"}
            r.raise_for_status.return_value = None
            responses.append(r)
        carousel_r = MagicMock(status_code=200)
        carousel_r.json.return_value = {"id": "carousel_x"}
        carousel_r.raise_for_status.return_value = None
        responses.append(carousel_r)
        pub_r = MagicMock(status_code=200)
        pub_r.json.return_value = {"id": "post_capped"}
        pub_r.raise_for_status.return_value = None
        responses.append(pub_r)

        with (
            patch("requests.post", side_effect=responses),
            patch("time.sleep"),
        ):
            result = poster.post_carousel("Caption", urls)

        assert result["item_count"] == MAX_CAROUSEL_ITEMS


# ─── get_post_analytics ───────────────────────────────────────────────────────


class TestGetPostAnalytics:
    def test_returns_needs_auth_when_not_configured(self, poster_no_creds):
        """get_post_analytics() returns needs_auth when credentials missing."""
        result = poster_no_creds.get_post_analytics("post_123")
        assert result["status"] == "needs_auth"

    def test_returns_metrics_on_success(self, poster):
        """get_post_analytics() parses the insights data array correctly."""
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "data": [
                {"name": "views", "values": [{"value": 1500}]},
                {"name": "likes", "values": [{"value": 42}]},
                {"name": "replies", "values": [{"value": 7}]},
                {"name": "reposts", "values": [{"value": 3}]},
                {"name": "quotes", "values": [{"value": 1}]},
            ]
        }
        mock_resp.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_resp):
            result = poster.get_post_analytics("post_123")

        assert result["status"] == "ok"
        assert result["views"] == 1500
        assert result["likes"] == 42
        assert result["replies_count"] == 7
        assert result["reposts"] == 3
        assert result["quotes"] == 1

    def test_returns_error_on_api_failure(self, poster):
        """get_post_analytics() returns error status when the API call fails."""
        with patch.object(poster, "_get", side_effect=RuntimeError("timeout")):
            result = poster.get_post_analytics("post_123")

        assert result["status"] == "error"
        assert result["post_id"] == "post_123"


# ─── Retry logic ──────────────────────────────────────────────────────────────


class TestRetryLogic:
    def test_retries_on_429_then_succeeds(self, poster):
        """_post() retries after a 429 rate-limit and returns on success."""
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.raise_for_status.return_value = None

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"id": "post_ok"}
        success.raise_for_status.return_value = None

        url = "https://graph.facebook.com/v1.0/test"
        with (
            patch("requests.post", side_effect=[rate_limited, success]),
            patch("time.sleep"),
        ):
            result = poster._post(url, params={"access_token": "tok"})

        assert result == {"id": "post_ok"}

    def test_raises_after_max_retries_on_rate_limit(self, poster):
        """_post() raises RuntimeError after MAX_RETRIES consecutive 429s."""
        from eworks.agents.publisher.threads_poster import MAX_RETRIES

        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.raise_for_status.return_value = None

        url = "https://graph.facebook.com/v1.0/test"
        with (
            patch("requests.post", return_value=rate_limited),
            patch("time.sleep"),
        ):
            with pytest.raises(RuntimeError, match="rate limited"):
                poster._post(url, params={})
