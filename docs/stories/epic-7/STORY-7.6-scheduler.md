# STORY-7.6 — Analytics Collector
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want an AnalyticsCollector that fetches post metrics from LinkedIn and Instagram and saves them to the DB so that I can track content performance over time.

## Acceptance Criteria
- [x] AC1. collect_linkedin() fetches metrics and inserts into social_analytics
- [x] AC2. collect_instagram() async fetches metrics and inserts into social_analytics
- [x] AC3. get_summary() returns platform-grouped aggregate metrics
- [x] AC4. Uses LinkedInPoster and InstagramPoster for API calls

## Tasks
- [x] Task 1: Create eworks/agents/publisher/analytics.py
- [x] Task 2: Implement AnalyticsCollector class
- [x] Task 3: Implement collect_linkedin() with DB write
- [x] Task 4: Implement collect_instagram() async with DB write
- [x] Task 5: Implement get_summary() with GROUP BY query
- [x] Task 6: Git commit

## Dev Notes
Analytics stored in social_analytics table.
LinkedIn analytics via socialActions API endpoint.
Instagram analytics via insights API (impressions, reach, likes, comments, shares, saved).

## File List
- eworks/agents/publisher/analytics.py (new)
