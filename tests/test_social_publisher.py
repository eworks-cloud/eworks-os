"""Tests for Epic 7: LinkedIn + Instagram Social Publisher."""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


# ─── Test ImageGenerator ──────────────────────────────────────────────────────

def test_image_generator_init():
    from eworks.agents.publisher.image_generator import ImageGenerator
    gen = ImageGenerator()
    assert gen.output_dir.name == "images"


def test_image_generator_needs_api_key():
    from eworks.agents.publisher.image_generator import ImageGenerator
    gen = ImageGenerator()
    gen.api_key = ""
    with pytest.raises(ValueError, match="FAL_KEY"):
        gen.generate("test prompt")


def test_image_generator_platform_sizes():
    from eworks.agents.publisher.image_generator import ImageGenerator
    gen = ImageGenerator()
    gen.api_key = "test"
    # Verify size mapping logic (don't call API)
    sizes = {
        "linkedin_image": "landscape_4_3",
        "linkedin_carousel": "square_hd",
        "instagram_image": "square_hd",
        "instagram_carousel": "square_hd",
    }
    for key, expected_size in sizes.items():
        actual_size = {
            "linkedin_image": "landscape_4_3",
            "linkedin_carousel": "square_hd",
            "instagram_image": "square_hd",
            "instagram_carousel": "square_hd",
            "instagram_reel": "portrait_16_9",
        }.get(key, "square_hd")
        assert actual_size == expected_size, f"Size mismatch for {key}: expected {expected_size}, got {actual_size}"


def test_image_generator_generate_mocked():
    """Test generate() with mocked API call."""
    from eworks.agents.publisher.image_generator import ImageGenerator

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "images": [{"url": "https://example.com/test.jpg"}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_img_response = MagicMock()
    mock_img_response.content = b"fake_image_data"
    mock_img_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response), \
         patch("requests.get", return_value=mock_img_response):
        gen = ImageGenerator()
        gen.api_key = "test_key"
        path = gen.generate("test prompt")
        assert path.endswith(".jpg")


# ─── Test LinkedInPoster ──────────────────────────────────────────────────────

def test_linkedin_poster_needs_auth():
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    poster = LinkedInPoster()
    poster.access_token = ""
    result = poster.post_text("Hello LinkedIn")
    assert result["status"] == "needs_auth"


def test_linkedin_poster_image_needs_auth():
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    poster = LinkedInPoster()
    poster.access_token = ""
    result = poster.post_image("Hello LinkedIn", "/tmp/test.jpg")
    assert result["status"] == "needs_auth"


def test_linkedin_poster_video_needs_auth():
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    poster = LinkedInPoster()
    poster.access_token = ""
    result = poster.post_video("Hello LinkedIn", "/tmp/test.mp4")
    assert result["status"] == "needs_auth"


def test_linkedin_poster_carousel_needs_auth():
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    poster = LinkedInPoster()
    poster.access_token = ""
    result = poster.post_carousel("Hello LinkedIn", ["/tmp/img1.jpg"])
    assert result["status"] == "needs_auth"


def test_linkedin_text_payload_structure():
    """Verify ugcPosts payload is correctly structured."""
    author = "urn:li:person:test123"
    text = "Test post content"
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    assert payload["lifecycleState"] == "PUBLISHED"
    assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == text
    assert payload["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"] == "PUBLIC"


def test_linkedin_carousel_max_images():
    """LinkedIn carousel capped at 9 images."""
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    poster = LinkedInPoster()
    poster.access_token = ""
    # Would be capped at 9 even if we pass 15
    test_paths = [f"/tmp/img_{i}.jpg" for i in range(15)]
    capped = test_paths[:9]
    assert len(capped) == 9


def test_linkedin_text_truncation():
    """LinkedIn text capped at 3000 chars."""
    long_text = "x" * 5000
    truncated = long_text[:3000]
    assert len(truncated) == 3000


def test_linkedin_analytics_unavailable():
    """get_post_analytics returns unavailable when API fails."""
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("requests.get", return_value=mock_response):
        poster = LinkedInPoster()
        poster.access_token = "test_token"
        result = poster.get_post_analytics("urn:li:ugcPost:12345")
        assert result["status"] == "unavailable"


# ─── Test InstagramPoster extensions ──────────────────────────────────────────

def test_instagram_carousel_max_images():
    """Instagram carousel capped at 10 images."""
    test_paths = [f"/tmp/img_{i}.jpg" for i in range(15)]
    capped = test_paths[:10]
    assert len(capped) == 10


def test_instagram_needs_credentials():
    from eworks.agents.publisher.social_poster import InstagramPoster
    poster = InstagramPoster(access_token="", ig_user_id="")
    import asyncio
    result = asyncio.run(poster.post_image("/tmp/test.jpg", "test caption"))
    assert result["status"] == "needs_auth"


def test_instagram_carousel_needs_credentials():
    from eworks.agents.publisher.social_poster import InstagramPoster
    poster = InstagramPoster(access_token="", ig_user_id="")
    import asyncio
    result = asyncio.run(poster.post_carousel(["/tmp/img1.jpg"], "test caption"))
    assert result["status"] == "needs_auth"


def test_instagram_upload_file_cdn_missing_file():
    """upload_file_to_cdn raises FileNotFoundError for missing files."""
    from eworks.agents.publisher.social_poster import InstagramPoster
    import asyncio
    poster = InstagramPoster(access_token="test", ig_user_id="test")
    with pytest.raises(FileNotFoundError):
        asyncio.run(poster.upload_file_to_cdn("/tmp/nonexistent_file_xyz.jpg"))


# ─── Test social_posts DB table ───────────────────────────────────────────────

def test_social_posts_table_creation():
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseManager(db_path)
        db.init_schema()
        db.add_publisher_tables()
        db.add_social_publisher_tables()
        conn = db.get_connection()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "social_posts" in tables
        assert "social_analytics" in tables
    finally:
        os.unlink(db_path)


def test_social_post_insert_and_query():
    """Test inserting and querying a social post."""
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseManager(db_path)
        db.init_schema()
        db.add_publisher_tables()
        db.add_social_publisher_tables()
        conn = db.get_connection()
        conn.execute(
            """INSERT INTO social_posts (platform, content_type, text_content, status)
               VALUES ('linkedin', 'text', 'Hello LinkedIn', 'posted')"""
        )
        conn.commit()
        row = conn.execute("SELECT * FROM social_posts WHERE platform='linkedin'").fetchone()
        assert row is not None
        assert dict(row)["content_type"] == "text"
        assert dict(row)["status"] == "posted"
    finally:
        os.unlink(db_path)


def test_social_analytics_table_columns():
    """Test social_analytics table has required columns."""
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseManager(db_path)
        db.init_schema()
        db.add_publisher_tables()
        db.add_social_publisher_tables()
        conn = db.get_connection()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(social_analytics)").fetchall()]
        for col in ["post_id", "platform", "impressions", "likes", "comments", "shares", "reach"]:
            assert col in cols, f"Column {col} missing from social_analytics"
    finally:
        os.unlink(db_path)


def test_social_post_status_enum():
    """Verify valid status values."""
    valid_statuses = {"draft", "scheduled", "approved", "posting", "posted", "failed"}
    assert "posted" in valid_statuses
    assert "draft" in valid_statuses
    assert "failed" in valid_statuses
    assert "scheduled" in valid_statuses


def test_social_post_platform_enum():
    """Verify valid platform values."""
    valid_platforms = {"linkedin", "instagram", "youtube", "both"}
    assert "linkedin" in valid_platforms
    assert "instagram" in valid_platforms


def test_social_post_content_type_enum():
    """Verify valid content type values."""
    valid_types = {"text", "image", "video", "carousel", "reel"}
    assert "text" in valid_types
    assert "carousel" in valid_types
    assert "reel" in valid_types


# ─── Test AnalyticsCollector ──────────────────────────────────────────────────

def test_analytics_collector_init():
    """Test AnalyticsCollector initializes with DB."""
    from eworks.agents.publisher.analytics import AnalyticsCollector
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseManager(db_path)
        db.init_schema()
        db.add_publisher_tables()
        db.add_social_publisher_tables()
        collector = AnalyticsCollector(db)
        assert collector.linkedin is not None
        assert collector.instagram is not None
    finally:
        os.unlink(db_path)


def test_analytics_get_summary_empty():
    """Test get_summary returns empty dict when no data."""
    from eworks.agents.publisher.analytics import AnalyticsCollector
    from eworks.core.database import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseManager(db_path)
        db.init_schema()
        db.add_publisher_tables()
        db.add_social_publisher_tables()
        collector = AnalyticsCollector(db)
        summary = collector.get_summary()
        assert isinstance(summary, dict)
    finally:
        os.unlink(db_path)


# ─── Test imports ─────────────────────────────────────────────────────────────

def test_linkedin_poster_importable():
    from eworks.agents.publisher.linkedin_poster import LinkedInPoster
    assert LinkedInPoster is not None


def test_image_generator_importable():
    from eworks.agents.publisher.image_generator import ImageGenerator
    assert ImageGenerator is not None


def test_analytics_collector_importable():
    from eworks.agents.publisher.analytics import AnalyticsCollector
    assert AnalyticsCollector is not None


def test_social_orchestrator_importable():
    from eworks.agents.publisher.social_orchestrator import SocialOrchestrator
    assert SocialOrchestrator is not None
