# STORY-12.9 — Graceful Fallback, Non-Blocking Capture & Additive-Safety Tests

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 5

## Summary
Closing story — ensure the brain degrades gracefully when unavailable, capture never blocks agents, and additive-safety is proven by tests.

## Acceptance Criteria
- [ ] `eworks/core/brain.py` wraps all gbrain calls (init, capture, sync, search, think) with error handling that, on gbrain unavailability (not initialized, engine error), lets agents continue operating normally against SQLite (FR-1216, CON-1206)
- [ ] Knowledge capture across all three adapters (nurturer/closer/connector, Stories 12.2-12.4) is confirmed best-effort and non-blocking — a forced `brain_adapter.py` write failure in tests does not fail or delay the corresponding agent's SQLite transaction or run (NFR-1205, FR-1216)
- [ ] Queries (search/think/`/client`) degrade to an explicit "brain unavailable" state rather than raising an unhandled error when gbrain is down (FR-1216)
- [ ] `tests/test_brain.py` asserts: SQLite schema is unchanged by the brain integration; removing/disabling gbrain leaves all agent state (nurturer/closer/connector tables) fully intact (NFR-1202, CON-1201)
- [ ] `tests/test_brain.py` asserts gbrain is never used as an agent-orchestration framework — no LangChain/CrewAI/AutoGen-style orchestration dependency is introduced alongside it (CON-1203)
- [ ] Privacy check: captured PII in gbrain inherits single-operator/local access controls; the brain store is not exposed to unauthenticated network access by default (NFR-1208)
- [ ] Auditability check: a sample synthesized think/`/client` answer is manually traced end-to-end to its source SQLite row(s) via the Story 12.5 provenance module, confirming no unsupported facts appear (NFR-1206, FR-1209)

## Dependencies
- Stories 12.1 through 12.8 (all capture/sync/query paths must exist to verify fallback and additive-safety end-to-end)
