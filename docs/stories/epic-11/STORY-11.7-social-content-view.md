# STORY-11.7 — Social / Content View (Publisher)

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Content pipeline and post performance from publisher tables and analytics.

## Acceptance Criteria
- [ ] `web/app/content/page.tsx` shows `content_ideas`, `content_scripts`, `content_posts`, `social_posts`, and `x_posts` grouped by status (FR-1111)
- [ ] Engagement metrics (impressions, likes, comments, shares, engagement rate) from `social_analytics` and `x_analytics` are displayed for posted content (FR-1111)
- [ ] Content with no analytics yet shows an explicit "no metrics yet" state rather than zeros presented as real performance (FR-1103, FR-1111)

## Dependencies
- Story 11.2, Story 11.3; DEP-1105
