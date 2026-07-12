# STORY-12.3 — Closer Knowledge Capture Adapter

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 3

## Summary
Capture the closer's discovery-call and proposal knowledge into gbrain, associated with client/deal entities.

## Acceptance Criteria
- [ ] `eworks/agents/closer/brain_adapter.py` captures discovery-call notes and extracted requirements/pain-points/budget/timeline (`discovery_calls`) and proposal content/summaries (`proposals`), associated with the client and deal entities (FR-1206)
- [ ] Each captured item carries provenance back to its source SQLite row (agent=closer, table, row id) (FR-1209)
- [ ] Adapter writes are best-effort/non-blocking relative to the closer's primary SQLite work (NFR-1205)
- [ ] `brain_adapter.py` is isolated to `eworks/agents/closer/` so a closer schema change affects only this adapter (NFR-1207)

## Dependencies
- Story 12.1; DEP-1204
