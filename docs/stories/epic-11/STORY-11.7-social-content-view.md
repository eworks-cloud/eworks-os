# STORY-11.7 — Social / Content View (Publisher)

**Epic:** 11 — Operator Console
**Status:** Ready
**Points:** 5

## Summary
Content pipeline and post performance from publisher tables and analytics.

## Acceptance Criteria
- [ ] `web/app/content/page.tsx` shows `content_ideas`, `content_scripts`, `content_posts`, `social_posts`, and `x_posts` grouped by status (FR-1111)
- [ ] Engagement metrics (impressions, likes, comments, shares, engagement rate) from `social_analytics` and `x_analytics` are displayed for posted content (FR-1111)
- [ ] Content with no analytics yet shows an explicit "no metrics yet" state rather than zeros presented as real performance (FR-1103, FR-1111)

## Dependencies
- Story 11.2, Story 11.3; DEP-1105

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Content-pipeline ACs (status grouping, engagement metrics, explicit "no metrics yet" honesty) are testable and traced to FR-1111/1103; deps and points present. Thinner than sibling views (no drill-down AC, per PRD US-11.5 which does not require one) and per-story risks absent, but scope is coherent and aligned — proceed.
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
