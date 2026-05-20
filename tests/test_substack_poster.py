"""
Tests for SubstackPoster (Epic 11: Threads / Substack publisher).
All tests run offline — no real HTTP calls.
"""
from __future__ import annotations

import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from eworks.agents.publisher.substack_poster import SubstackPoster


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_conn():
    """In-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture()
def poster(db_conn):
    """SubstackPoster with valid env vars and an in-memory DB."""
    env = {
        "SUBSTACK_EMAIL": "test@example.com",
        "SUBSTACK_PASSWORD": "secret",
        "SUBSTACK_PUBLICATION_URL": "testpub.substack.com",
    }
    with patch.dict(os.environ, env):
        p = SubstackPoster(db_conn=db_conn)
    return p


@pytest.fixture()
def poster_no_creds():
    """SubstackPoster created without any Substack env vars."""
    env = os.environ.copy()
    for key in ("SUBSTACK_EMAIL", "SUBSTACK_PASSWORD", "SUBSTACK_PUBLICATION_URL"):
        env.pop(key, None)
    with patch.dict(os.environ, env, clear=True):
        p = SubstackPoster(db_conn=None)
    return p


# ─── Initialisation ───────────────────────────────────────────────────────────


class TestSubstackPosterInit:
    def test_credentials_loaded_from_env(self, poster):
        """Email, password, and publication URL are read from env vars."""
        assert poster.email == "test@example.com"
        assert poster.password == "secret"
        assert "testpub.substack.com" in poster.publication_url

    def test_is_configured_true(self, poster):
        """_is_configured() returns True when all three vars are present."""
        assert poster._is_configured() is True

    def test_is_configured_false_when_email_missing(self, poster_no_creds):
        """_is_configured() returns False when credentials are absent."""
        assert poster_no_creds._is_configured() is False

    def test_api_base_includes_publication_url(self, poster):
        """_api_base() builds the correct base URL."""
        base = poster._api_base()
        assert "testpub.substack.com" in base
        assert base.startswith("https://")


# ─── _get_session (login flow) ────────────────────────────────────────────────


class TestGetSession:
    def test_returns_session_on_successful_login(self, poster):
        """_get_session() returns a requests.Session after a 200 login."""
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        with patch.object(requests.Session, "post", return_value=mock_resp):
            session = poster._get_session()

        assert session is not None

    def test_caches_session_on_second_call(self, poster):
        """_get_session() does not re-authenticate when a session is cached."""
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        with patch.object(requests.Session, "post", return_value=mock_resp) as mock_post:
            poster._get_session()
            poster._get_session()

        # Login should only be called once
        assert mock_post.call_count == 1

    def test_raises_on_login_failure(self, poster):
        """_get_session() propagates an HTTPError when login returns 401."""
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        http_err = requests.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err

        with patch.object(requests.Session, "post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                poster._get_session()

    def test_logout_clears_cached_session(self, poster):
        """logout() forces re-authentication on the next call."""
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        with patch.object(requests.Session, "post", return_value=mock_resp):
            poster._get_session()
            poster.logout()
            poster._get_session()

        assert mock_resp.raise_for_status.call_count == 2


# ─── create_draft ─────────────────────────────────────────────────────────────


class TestCreateDraft:
    def test_raises_when_not_configured(self, poster_no_creds):
        """create_draft() raises RuntimeError when credentials are missing."""
        with pytest.raises(RuntimeError, match="not configured"):
            poster_no_creds.create_draft("Title", "<p>Body</p>")

    def test_returns_draft_id_on_success(self, poster):
        """create_draft() returns the draft post ID string."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"id": 42, "canonical_url": "https://testpub.substack.com/p/test"}
        mock_session.post.return_value = mock_resp

        with patch.object(poster, "_get_session", return_value=mock_session):
            draft_id = poster.create_draft("My Title", "<p>Hello world</p>")

        assert draft_id == "42"

    def test_saves_post_to_db(self, poster, db_conn):
        """create_draft() inserts a row into substack_posts with status=draft."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"id": 99, "canonical_url": "https://testpub.substack.com/p/test"}
        mock_session.post.return_value = mock_resp

        with patch.object(poster, "_get_session", return_value=mock_session):
            poster.create_draft("Saved Title", "<p>Content</p>")

        row = db_conn.execute(
            "SELECT * FROM substack_posts WHERE substack_post_id='99'"
        ).fetchone()
        assert row is not None
        assert row["status"] == "draft"
        assert row["title"] == "Saved Title"


# ─── publish_post ─────────────────────────────────────────────────────────────


class TestPublishPost:
    def test_raises_when_not_configured(self, poster_no_creds):
        """publish_post() raises RuntimeError when credentials are missing."""
        with pytest.raises(RuntimeError, match="not configured"):
            poster_no_creds.publish_post("draft_1")

    def test_returns_canonical_url(self, poster):
        """publish_post() returns the canonical URL of the published post."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "canonical_url": "https://testpub.substack.com/p/my-post"
        }
        mock_session.post.return_value = mock_resp

        with patch.object(poster, "_get_session", return_value=mock_session):
            url = poster.publish_post("draft_42")

        assert url == "https://testpub.substack.com/p/my-post"

    def test_updates_db_status_to_published(self, poster, db_conn):
        """publish_post() updates the local DB row to status=published."""
        # First, insert a draft row we can update
        db_conn.execute(
            "INSERT INTO substack_posts (substack_post_id, title, status) VALUES ('77', 'Test', 'draft')"
        )
        db_conn.commit()

        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"canonical_url": "https://testpub.substack.com/p/t"}
        mock_session.post.return_value = mock_resp

        with patch.object(poster, "_get_session", return_value=mock_session):
            poster.publish_post("77")

        row = db_conn.execute(
            "SELECT status FROM substack_posts WHERE substack_post_id='77'"
        ).fetchone()
        assert row["status"] == "published"


# ─── create_and_publish ───────────────────────────────────────────────────────


class TestCreateAndPublish:
    def test_calls_create_then_publish(self, poster):
        """create_and_publish() invokes create_draft then publish_post."""
        with (
            patch.object(poster, "create_draft", return_value="draft_55") as mock_create,
            patch.object(
                poster, "publish_post", return_value="https://testpub.substack.com/p/x"
            ) as mock_publish,
        ):
            url = poster.create_and_publish("Title", "<p>Body</p>")

        mock_create.assert_called_once()
        mock_publish.assert_called_once_with(
            draft_id="draft_55", send_email=True, audience="everyone"
        )
        assert url == "https://testpub.substack.com/p/x"

    def test_passes_subtitle_to_create_draft(self, poster):
        """create_and_publish() forwards optional subtitle to create_draft."""
        with (
            patch.object(poster, "create_draft", return_value="d1") as mock_create,
            patch.object(poster, "publish_post", return_value="https://x.com/p/p"),
        ):
            poster.create_and_publish("Title", "<p>Body</p>", subtitle="A deck line")

        _, kwargs = mock_create.call_args
        assert kwargs.get("subtitle") == "A deck line"


# ─── get_post_stats ───────────────────────────────────────────────────────────


class TestGetPostStats:
    def test_returns_needs_auth_when_not_configured(self, poster_no_creds):
        """get_post_stats() returns needs_auth when credentials missing."""
        result = poster_no_creds.get_post_stats("post_1")
        assert result["status"] == "needs_auth"

    def test_returns_stats_on_success(self):
        """get_post_stats() parses views, likes, and comments from the API."""
        # Use db_conn=None so no DB upsert is attempted (avoids NOT NULL constraints
        # on synthetic rows that lack a title column).
        env = {
            "SUBSTACK_EMAIL": "test@example.com",
            "SUBSTACK_PASSWORD": "secret",
            "SUBSTACK_PUBLICATION_URL": "testpub.substack.com",
        }
        with patch.dict(os.environ, env):
            p = SubstackPoster(db_conn=None)

        detail_resp = MagicMock()
        detail_resp.status_code = 200
        detail_resp.json.return_value = {
            "canonical_url": "https://testpub.substack.com/p/x",
            "reads": 300,
            "reaction_count": 15,
            "email_opens": 50,
        }

        comments_resp = MagicMock()
        comments_resp.status_code = 200
        comments_resp.json.return_value = {"total": 8}

        mock_session = MagicMock()
        mock_session.get.side_effect = [detail_resp, comments_resp]

        with patch.object(p, "_get_session", return_value=mock_session):
            stats = p.get_post_stats("post_1")

        assert stats["status"] == "ok"
        assert stats["views"] == 300
        assert stats["email_opens"] == 50

    def test_returns_unavailable_on_non_200(self, poster):
        """get_post_stats() returns unavailable when post returns 404."""
        detail_resp = MagicMock()
        detail_resp.status_code = 404

        mock_session = MagicMock()
        mock_session.get.return_value = detail_resp

        with patch.object(poster, "_get_session", return_value=mock_session):
            stats = poster.get_post_stats("missing_post")

        assert stats["status"] == "unavailable"
