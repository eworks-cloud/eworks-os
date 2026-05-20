# STORY-9.5: Instagram Auto-Reply + Location Tagging

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 3

## Summary
Create `IGEngagementManager` for auto-replying to Instagram comments with Claude-generated responses and posting images with location tags.

## Acceptance Criteria
- [x] `get_comments()` fetches recent comments for a post
- [x] `reply_to_comment()` sends reply via Graph API
- [x] `generate_reply()` uses Claude Haiku for contextual <150 char replies
- [x] `auto_reply_to_recent()` rate-limits to 3s between replies
- [x] `post_with_location()` posts image with Facebook Place ID

## Files
- `eworks/agents/publisher/ig_engagement.py` (new)

## Commit
`feat(epic-9): Instagram auto-reply engine + location tagging`
