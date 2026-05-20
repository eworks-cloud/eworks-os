# STORY-9.6: Extended CLI Commands

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 3

## Summary
Add extended YouTube and Instagram CLI commands to `eworks/cli/main.py`.

## New Commands
### YouTube
- `eos youtube shorts --video --title`
- `eos youtube thumbnail --video-id --topic`
- `eos youtube captions --video-id --script`
- `eos youtube playlist --video-id --playlist`
- `eos youtube schedule --video-id --publish-at`
- `eos youtube analytics --video-id`

### Instagram
- `eos instagram story --image`
- `eos instagram story-video --video`
- `eos instagram hashtags --topic`
- `eos instagram auto-reply --post-id --topic`
- `eos instagram reel-with-cover --video --caption`

## Files
- `eworks/cli/main.py` (extended)

## Commit
`feat(epic-9): extended CLI — YouTube Shorts/thumbnails/captions + Instagram Stories/hashtags/auto-reply`
