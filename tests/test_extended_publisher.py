"""
Epic 9: YouTube + Instagram Extended Features — Test Suite
Tests for CaptionGenerator, ThumbnailGenerator, HashtagResearcher, YouTubePoster, and DB tables.
"""
from __future__ import annotations
import os
import re
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ─── CaptionGenerator ─────────────────────────────────────────────────────────

from eworks.agents.publisher.caption_generator import CaptionGenerator


class TestCaptionGenerator:
    def setup_method(self):
        self.gen = CaptionGenerator()
        self.sample_text = "Hello world this is a test of the caption generator system."

    def test_caption_generator_srt_format(self):
        """SRT has correct format: number, timecode arrow, text, blank line."""
        srt = self.gen.generate_srt(self.sample_text)
        lines = srt.strip().split('\n')
        # First block: index line, timecode line, text line
        assert lines[0].strip().isdigit(), f"First line should be index number, got: {lines[0]!r}"
        assert '-->' in lines[1], f"Second line should be timecode with '-->', got: {lines[1]!r}"
        assert len(lines[2]) > 0, "Third line should be caption text"

    def test_caption_generator_timing(self):
        """Timestamps increase monotonically."""
        # 40 words to get multiple blocks
        text = " ".join(["word"] * 40)
        srt = self.gen.generate_srt(text)
        timecodes = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', srt)
        assert len(timecodes) > 1, "Should produce multiple timecoded blocks"

        def parse_time(ts: str) -> float:
            h, m, rest = ts.split(':')
            s, ms = rest.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        starts = [parse_time(tc[0]) for tc in timecodes]
        ends = [parse_time(tc[1]) for tc in timecodes]
        # Each start should be greater than the previous end (gap between blocks)
        for i in range(1, len(starts)):
            assert starts[i] > starts[i - 1], f"Start {i} ({starts[i]}) not > start {i-1} ({starts[i-1]})"
        # Each end should be greater than its start
        for i, (start, end) in enumerate(zip(starts, ends)):
            assert end > start, f"Block {i}: end ({end}) not > start ({start})"

    def test_caption_generator_chunks_correctly(self):
        """100-word text creates multiple blocks (chunk_size=8 → ~13 blocks)."""
        words = " ".join([f"word{i}" for i in range(100)])
        srt = self.gen.generate_srt(words)
        # Count index numbers (1, 2, 3, ...)
        indices = re.findall(r'^(\d+)$', srt, re.MULTILINE)
        assert len(indices) >= 12, f"Expected ~12+ blocks for 100 words, got {len(indices)}"

    def test_format_time_correct(self):
        """_format_time produces HH:MM:SS,mmm format."""
        result = self.gen._format_time(3661.5)
        assert result == "01:01:01,500"

    def test_format_time_zero(self):
        """_format_time handles 0 seconds."""
        result = self.gen._format_time(0)
        assert result == "00:00:00,000"


# ─── ThumbnailGenerator ───────────────────────────────────────────────────────

class TestThumbnailGenerator:
    def test_thumbnail_generator_init(self):
        """ThumbnailGenerator initializes without errors."""
        from eworks.agents.publisher.thumbnail_generator import ThumbnailGenerator
        gen = ThumbnailGenerator()
        assert gen.image_gen is not None
        assert gen.logger is not None

    def test_thumbnail_generator_has_methods(self):
        """ThumbnailGenerator has required methods."""
        from eworks.agents.publisher.thumbnail_generator import ThumbnailGenerator
        gen = ThumbnailGenerator()
        assert callable(gen.generate_youtube_thumbnail)
        assert callable(gen.generate_reel_cover)


# ─── HashtagResearcher ────────────────────────────────────────────────────────

class TestHashtagResearcher:
    def setup_method(self):
        # Patch Claude to avoid real API calls
        self.claude_patcher = patch('eworks.agents.publisher.hashtag_researcher.anthropic.Anthropic')
        self.mock_anthropic = self.claude_patcher.start()
        # Mock response
        mock_msg = MagicMock()
        mock_content = MagicMock()
        mock_content.text = (
            "#ai, #technology, #innovation, #startup, #machinelearning, "
            "#artificialintelligence, #tech, #business, #automation, #deeplearning, "
            "#datascience, #programming, #python, #softwareengineering, #cloudcomputing, "
            "#devops, #coding, #developer, #eworkslabs, #aitools, "
            "#techstartup, #futureofwork, #digitaltransformation, #productivity, "
            "#entrepreneurship, #saas, #agentic, #llm"
        )
        mock_msg.content = [mock_content]
        self.mock_anthropic.return_value.messages.create.return_value = mock_msg

    def teardown_method(self):
        self.claude_patcher.stop()

    def test_hashtag_set_length(self):
        """generate_hashtag_set returns ≤30 hashtags."""
        from eworks.agents.publisher.hashtag_researcher import HashtagResearcher
        researcher = HashtagResearcher()
        tags = researcher.generate_hashtag_set("artificial intelligence tools")
        assert len(tags) <= 30, f"Expected ≤30 tags, got {len(tags)}"
        assert len(tags) > 0, "Should return at least some tags"

    def test_hashtag_format(self):
        """All generated hashtags start with #."""
        from eworks.agents.publisher.hashtag_researcher import HashtagResearcher
        researcher = HashtagResearcher()
        tags = researcher.generate_hashtag_set("AI automation")
        for tag in tags:
            assert tag.startswith('#'), f"Tag {tag!r} should start with #"

    def test_hashtag_includes_branded(self):
        """#eworkslabs branded hashtag is included."""
        from eworks.agents.publisher.hashtag_researcher import HashtagResearcher
        researcher = HashtagResearcher()
        tags = researcher.generate_hashtag_set("business automation")
        assert '#eworkslabs' in tags, f"#eworkslabs not in tags: {tags}"

    def test_format_for_caption(self):
        """format_for_caption appends hashtags with double newline."""
        from eworks.agents.publisher.hashtag_researcher import HashtagResearcher
        researcher = HashtagResearcher()
        tags = ['#ai', '#tech', '#eworkslabs']
        result = researcher.format_for_caption(tags, "My caption")
        assert result.startswith("My caption\n\n")
        assert '#ai' in result
        assert '#eworkslabs' in result


# ─── YouTubePoster Extended ───────────────────────────────────────────────────

class TestYouTubePosterExtended:
    def test_youtube_short_adds_hashtag_to_title(self):
        """make_youtube_short adds #Shorts to title."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        # Patch upload_video to avoid real upload
        with patch.object(poster, 'upload_video', return_value={'status': 'needs_auth'}) as mock_upload:
            poster.make_youtube_short("/fake/video.mp4", "My Video", "Description")
            call_args = mock_upload.call_args
            title_arg = call_args[0][1]  # second positional arg is title
            assert '#Shorts' in title_arg, f"'#Shorts' not in title: {title_arg!r}"

    def test_youtube_short_adds_hashtag_to_description(self):
        """make_youtube_short adds #Shorts to description."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        with patch.object(poster, 'upload_video', return_value={'status': 'needs_auth'}) as mock_upload:
            poster.make_youtube_short("/fake/video.mp4", "My Video", "Original description")
            call_args = mock_upload.call_args
            desc_arg = call_args[0][2]  # third positional arg is description
            assert '#Shorts' in desc_arg, f"'#Shorts' not in description: {desc_arg!r}"

    def test_youtube_short_includes_shorts_tags(self):
        """make_youtube_short includes Shorts and YouTubeShorts tags."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        with patch.object(poster, 'upload_video', return_value={'status': 'needs_auth'}) as mock_upload:
            poster.make_youtube_short("/fake/video.mp4", "My Video", "Desc", tags=["python"])
            call_kwargs = mock_upload.call_args[1]
            tags = call_kwargs.get('tags', [])
            assert 'Shorts' in tags
            assert 'YouTubeShorts' in tags

    def test_set_thumbnail_returns_false_no_token(self):
        """set_thumbnail returns False when token file missing."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        result = poster.set_thumbnail("abc123", "/fake/thumb.jpg")
        assert result is False

    def test_add_to_playlist_returns_needs_auth_no_token(self):
        """add_to_playlist returns needs_auth when token missing."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        result = poster.add_to_playlist("abc123")
        assert result.get('status') == 'needs_auth'

    def test_set_scheduled_publish_returns_false_no_token(self):
        """set_scheduled_publish returns False when token missing."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        result = poster.set_scheduled_publish("abc123", "2026-06-01T09:00:00Z")
        assert result is False

    def test_upload_captions_returns_needs_auth_no_token(self):
        """upload_captions returns needs_auth when token missing."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        result = poster.upload_captions("abc123", "1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        assert result.get('status') == 'needs_auth'

    def test_get_video_analytics_returns_needs_auth_no_token(self):
        """get_video_analytics returns needs_auth when token missing."""
        from eworks.agents.publisher.social_poster import YouTubePoster
        poster = YouTubePoster(token_path="/nonexistent/token.json")
        result = poster.get_video_analytics("abc123")
        assert result.get('status') == 'needs_auth'


# ─── DB Tables ────────────────────────────────────────────────────────────────

class TestExtendedDBTables:
    def setup_method(self):
        """Create in-memory DB for each test."""
        from eworks.core.database import DatabaseManager
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db = DatabaseManager(db_path=self.tmp.name)
        self.db.init_schema()
        self.db.add_extended_media_tables()

    def teardown_method(self):
        self.db.close()
        os.unlink(self.tmp.name)

    def _table_exists(self, table_name: str) -> bool:
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return row is not None

    def test_youtube_videos_table_created(self):
        """youtube_videos table is created by add_extended_media_tables."""
        assert self._table_exists('youtube_videos'), "youtube_videos table not found"

    def test_ig_stories_table_created(self):
        """ig_stories table is created by add_extended_media_tables."""
        assert self._table_exists('ig_stories'), "ig_stories table not found"

    def test_ig_comments_table_created(self):
        """ig_comments table is created by add_extended_media_tables."""
        assert self._table_exists('ig_comments'), "ig_comments table not found"

    def test_youtube_videos_columns(self):
        """youtube_videos has expected columns."""
        conn = self.db.get_connection()
        cols = conn.execute("PRAGMA table_info(youtube_videos)").fetchall()
        col_names = {c['name'] for c in cols}
        expected = {'video_id', 'title', 'views', 'likes', 'is_short', 'playlist_id', 'thumbnail_path'}
        missing = expected - col_names
        assert not missing, f"Missing columns in youtube_videos: {missing}"

    def test_ig_stories_columns(self):
        """ig_stories has expected columns."""
        conn = self.db.get_connection()
        cols = conn.execute("PRAGMA table_info(ig_stories)").fetchall()
        col_names = {c['name'] for c in cols}
        expected = {'story_id', 'media_type', 'media_path', 'expires_at', 'status'}
        missing = expected - col_names
        assert not missing, f"Missing columns in ig_stories: {missing}"

    def test_ig_comments_columns(self):
        """ig_comments has expected columns."""
        conn = self.db.get_connection()
        cols = conn.execute("PRAGMA table_info(ig_comments)").fetchall()
        col_names = {c['name'] for c in cols}
        expected = {'post_id', 'comment_id', 'username', 'comment_text', 'replied', 'reply_text'}
        missing = expected - col_names
        assert not missing, f"Missing columns in ig_comments: {missing}"

    def test_add_extended_media_tables_idempotent(self):
        """Calling add_extended_media_tables twice doesn't raise errors."""
        # Call a second time — should be idempotent
        self.db.add_extended_media_tables()
        assert self._table_exists('youtube_videos')


# ─── Instagram Stories (no-auth path) ─────────────────────────────────────────

class TestInstagramStoriesNoAuth:
    def test_post_story_image_returns_needs_auth(self):
        """post_story_image returns needs_auth when no credentials."""
        import asyncio
        from eworks.agents.publisher.social_poster import InstagramPoster
        poster = InstagramPoster(access_token="", ig_user_id="")
        result = asyncio.run(poster.post_story_image("/fake/image.jpg"))
        assert result.get('status') == 'needs_auth'

    def test_post_story_video_returns_needs_auth(self):
        """post_story_video returns needs_auth when no credentials."""
        import asyncio
        from eworks.agents.publisher.social_poster import InstagramPoster
        poster = InstagramPoster(access_token="", ig_user_id="")
        result = asyncio.run(poster.post_story_video("/fake/video.mp4"))
        assert result.get('status') == 'needs_auth'

    def test_post_reel_with_cover_returns_needs_auth(self):
        """post_reel_with_cover returns needs_auth when no credentials."""
        import asyncio
        from eworks.agents.publisher.social_poster import InstagramPoster
        poster = InstagramPoster(access_token="", ig_user_id="")
        result = asyncio.run(poster.post_reel_with_cover("https://example.com/v.mp4", "Caption"))
        assert result.get('status') == 'needs_auth'
