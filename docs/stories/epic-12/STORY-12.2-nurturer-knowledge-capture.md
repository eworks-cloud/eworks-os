# STORY-12.2 — Nurturer Knowledge Capture Adapter

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 3

## Summary
Capture the nurturer's client-health knowledge into gbrain, associated with the client entity, with provenance and non-blocking writes.

## Acceptance Criteria
- [ ] `eworks/agents/nurturer/brain_adapter.py` captures client health notes and score context (`client_health_scores`), check-in summaries and NPS/sentiment (`client_checkins`), upsell opportunities (`upsell_opportunities`), and onboarding notes (`onboarding_checklists`), associated with the client entity (FR-1205)
- [ ] Each captured item written via `brain_adapter.py` carries provenance back to its source SQLite row (agent=nurturer, table, row id) (FR-1209)
- [ ] Adapter writes are best-effort/asynchronous relative to the nurturer's primary SQLite work — a gbrain write failure never fails or delays a nurturer SQLite transaction or run (NFR-1205)
- [ ] `brain_adapter.py` is isolated to `eworks/agents/nurturer/` so a nurturer schema change affects only this adapter; no nurturer core logic is entangled with gbrain internals (NFR-1207)
- [ ] The SQLite write for each nurturer table happens first; the `brain_adapter.py` call happens after, never blocking or replacing the SQLite write (CON-1201, FR-1210 ordering)

## Dependencies
- Story 12.1; DEP-1203
