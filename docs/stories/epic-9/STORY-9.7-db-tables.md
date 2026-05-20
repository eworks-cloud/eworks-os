# STORY-9.7: Extended DB Tables

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 2

## Summary
Add `add_extended_media_tables()` to `DatabaseManager` creating `youtube_videos`, `ig_stories`, and `ig_comments` tables.

## Tables
- `youtube_videos` — tracks uploaded videos with analytics, scheduling, captions
- `ig_stories` — tracks Stories with expiry, media type
- `ig_comments` — tracks comments and auto-reply state

## Files
- `eworks/core/database.py` (add_extended_media_tables method)

## Commit
`feat(epic-9): DB tables — youtube_videos, ig_stories, ig_comments`
