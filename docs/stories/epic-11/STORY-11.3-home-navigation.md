# STORY-11.3 — Home / Overview + Navigation Shell

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Home view summarizing all seven agents at a glance, plus the persistent navigation shell with deep-linkable routes for every view.

## Acceptance Criteria
- [ ] `web/app/page.tsx` renders a status tile for each of the seven agents (prospector, publisher, connector, closer, conductor, treasurer, nurturer) with last-run info sourced from the Story 11.2 data layer (FR-1106)
- [ ] `web/app/page.tsx` renders a cross-agent "needs attention" list aggregating escalated interactions, overdue invoices, and red-zone client health scores (FR-1106)
- [ ] Empty/uncaptured agents render an explicit "no data yet" tile, never a fabricated status (FR-1103, NFR-1104)
- [ ] `web/components/nav/Sidebar.tsx` lists all views (Home, Roster, Funnel, Comms, Social, Projects, Finances, Customer Success, Brain), each directly addressable by its own URL for bookmarking/deep-linking (FR-1116)
- [ ] `web/lib/hooks/useAutoRefresh.ts` polls the Story 11.2 data layer on a configurable interval (default 30s) and/or manual refresh; last-refreshed timestamp is visible on Home (FR-1104)
- [ ] Home view renders within 2 seconds against a realistic-size database (NFR-1102)

## Dependencies
- Story 11.1, Story 11.2
