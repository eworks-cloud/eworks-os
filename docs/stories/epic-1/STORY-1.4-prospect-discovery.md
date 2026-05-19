# STORY-1.4 — Prospect Discovery + ICP Scorer

**Status:** ✅ Done
**Epic:** Epic 1 — LinkedIn Prospector Agent
**Agent:** @dev (Dex)

## Description
Scrape LinkedIn connections and profiles, then score each prospect against the Ideal Customer Profile.

## Acceptance Criteria
- [x] `ProspectDiscovery.scrape_connections()` — paginates LinkedIn connections page
- [x] `ProspectDiscovery.scrape_profile()` — extracts full profile data
- [x] `ProspectDiscovery.discover_prospects()` — orchestrates scrape → score → DB save
- [x] `ICPScorer.score()` — weighted 0–100 scoring:
  - title_match: 30 pts (CEO/CTO/Founder/Director/VP)
  - company_size_signal: 20 pts (startup signals)
  - location_match: 15 pts (Brazil/LATAM/USA/Europe)
  - industry_match: 20 pts (Tech/SaaS/Fintech/AI)
  - engagement_signal: 15 pts (mutual connections)

## Commit
`feat(discovery): prospect scraper + weighted ICP scorer (30/20/20/15/15)`
