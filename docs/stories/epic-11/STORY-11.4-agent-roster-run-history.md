# STORY-11.4 — Agent Roster + Run History View

**Epic:** 11 — Operator Console
**Status:** Ready
**Points:** 3

## Summary
Roster listing all seven agents with health/status, plus a run-history timeline sourced from `agent_runs`/`connector_runs`.

## Acceptance Criteria
- [ ] `web/app/roster/page.tsx` lists all seven agents, each showing name/theme, last run time and outcome, and a lightweight activity indicator sourced from `agent_runs`, `connector_runs`, and each agent's own tables (FR-1107)
- [ ] Agents with no recorded runs show an honest "no runs yet" state, not a fabricated run (FR-1107, FR-1103)
- [ ] `web/app/roster/history/page.tsx` shows a run-history timeline with agent name, start/complete time, counts (e.g. prospects scanned, messages sent, errors), and status, drawn from `agent_runs` and `connector_runs` (FR-1108)
- [ ] Roster and history views reuse the Story 11.2 query modules only — no direct SQL in the page components (NFR-1105)

## Dependencies
- Story 11.2, Story 11.3

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Roster + run-history ACs are testable and traced to FR-1107/1108/1103 and NFR-1105 (reuse query modules, no direct SQL); deps and points present; per-story risk notes absent and business value only implicit via epic US-11.2, but scope is clear enough to proceed.
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
