# STORY-9.8: Test Suite

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 2

## Summary
Create comprehensive test suite for all Epic 9 features.

## Tests
- `test_caption_generator_srt_format` — SRT format validation
- `test_caption_generator_timing` — monotonically increasing timestamps
- `test_caption_generator_chunks_correctly` — chunking 100-word text
- `test_thumbnail_generator_init` — ThumbnailGenerator init
- `test_hashtag_set_length` — ≤30 hashtags returned
- `test_hashtag_format` — all tags start with #
- `test_hashtag_includes_branded` — #eworkslabs present
- `test_youtube_short_adds_hashtag` — #Shorts in title/description
- `test_youtube_videos_table_created` — DB table exists
- `test_ig_stories_table_created` — DB table exists
- `test_ig_comments_table_created` — DB table exists

## Files
- `tests/test_extended_publisher.py` (new)

## Commit
`test(epic-9): YouTube + Instagram extended features test suite`
