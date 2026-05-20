# STORY-9.4: Instagram Hashtag Research

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 3

## Summary
Create `HashtagResearcher` that uses Claude to generate optimized 28-tag Instagram hashtag sets with mix of broad, medium, and niche tags.

## Acceptance Criteria
- [x] `generate_hashtag_set()` returns ≤30 tags using Claude Haiku
- [x] All tags start with `#`
- [x] `#eworkslabs` branded tag always included
- [x] `format_for_caption()` appends tags with proper Instagram spacing
- [x] `get_optimal_hashtags()` async wrapper for CLI use

## Files
- `eworks/agents/publisher/hashtag_researcher.py` (new)

## Commit
`feat(epic-9): Instagram hashtag researcher — Claude-curated 30-tag optimization`
