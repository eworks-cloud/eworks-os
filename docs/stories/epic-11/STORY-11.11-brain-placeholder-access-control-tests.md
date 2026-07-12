# STORY-11.11 — Brain Placeholder, Access Control & Read-Only Verification

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Closing story — Brain placeholder route, single-user access control, Telegram cross-link enforcement, and the test suite proving the console is strictly read-only and additive.

## Acceptance Criteria
- [ ] `web/app/brain/page.tsx` is added to the nav (FR-1116) and renders an explicit "not configured — arriving in Epic 12" state with no fabricated knowledge-graph/query data (FR-1115)
- [ ] `web/middleware.ts` enforces local single-user access control — requests without the configured `OPERATOR_CONSOLE_ACCESS_TOKEN` (or non-localhost binding) are rejected; no prospect/client PII is exposed to unauthenticated requests (FR-1118, NFR-1107)
- [ ] Every view that surfaces an actionable item links to its corresponding Telegram command instead of performing the action; a repo-wide check confirms no in-console action-taking code path exists (FR-1119, CON-1101, CON-1102)
- [ ] `web/tests/read-only.test.ts` asserts no console code path issues `INSERT`/`UPDATE`/`DELETE` against `eworks.db` (static scan of `web/lib/db/` + a live-connection test) (FR-1102, NFR-1101, CON-1101)
- [ ] Integration test starts the console against a live `eworks.db` while an agent process runs concurrently, confirming zero effect on the agent, and zero effect on any running agent when the console is brought down (CON-1107, NFR-1101)
- [ ] Every implemented view (Home, Roster, Funnel, Comms, Social, Projects, Finances, Customer Success, Brain) renders within 2 seconds against a realistic-size database, verified in this story's test pass (NFR-1102)
- [ ] Zero seed/placeholder data exists anywhere in `web/` — an acceptance test explicitly checks for absence of any hardcoded demo rows (CON-1105, FR-1103)

## Dependencies
- Stories 11.1 through 11.10 (all views must exist to verify read-only + performance across the full console)
