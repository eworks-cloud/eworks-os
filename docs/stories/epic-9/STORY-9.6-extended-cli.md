# STORY-9.6: Extended CLI Commands

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 3

## Summary
Add extended YouTube and Instagram CLI commands to `eworks/cli/main.py`.

## New Commands
### YouTube
- `eworks youtube shorts --video --title`
- `eworks youtube thumbnail --video-id --topic`
- `eworks youtube captions --video-id --script`
- `eworks youtube playlist --video-id --playlist`
- `eworks youtube schedule --video-id --publish-at`
- `eworks youtube analytics --video-id`

### Instagram
- `eworks instagram story --image`
- `eworks instagram story-video --video`
- `eworks instagram hashtags --topic`
- `eworks instagram auto-reply --post-id --topic`
- `eworks instagram reel-with-cover --video --caption`

## Files
- `eworks/cli/main.py` (extended)

## Commit
`feat(epic-9): extended CLI — YouTube Shorts/thumbnails/captions + Instagram Stories/hashtags/auto-reply`
