# STORY-9.2: YouTube Extended Features

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 5

## Summary
Extend `YouTubePoster` with Shorts upload, thumbnail setting, playlist management, scheduled publishing, caption upload, analytics fetch. Create `CaptionGenerator` and `ThumbnailGenerator` modules.

## Acceptance Criteria
- [x] `make_youtube_short()` uploads with #Shorts tag
- [x] `set_thumbnail()` sets custom thumbnail via thumbnails API
- [x] `add_to_playlist()` creates playlist if missing, returns {playlist_id, playlist_title, status}
- [x] `set_scheduled_publish()` sets privacyStatus=private + publishAt
- [x] `upload_captions()` uploads SRT to YouTube captions API
- [x] `get_video_analytics()` fetches views/likes/comments/watch_time with graceful fallback
- [x] `CaptionGenerator` creates SRT from script text (2.3 wps pace)
- [x] `ThumbnailGenerator` generates 16:9 thumbnail + 9:16 reel cover via FAL.ai

## Files
- `eworks/agents/publisher/social_poster.py` (YouTubePoster extended)
- `eworks/agents/publisher/caption_generator.py` (new)
- `eworks/agents/publisher/thumbnail_generator.py` (new)

## Commit
`feat(epic-9): YouTube extended — Shorts, thumbnails, captions, playlists, scheduling, analytics`
