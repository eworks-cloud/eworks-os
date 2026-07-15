# STORY-12.5 — Incremental Sync Scheduler Job + Provenance/Citation Mapping

**Epic:** 12 — Knowledge Management Agent
**Status:** Ready
**Points:** 5

## Summary
Schedulable incremental sync from SQLite into gbrain, reusing the existing APScheduler, with a shared provenance module and reliance on gbrain's self-wiring knowledge graph.

## Acceptance Criteria
- [ ] `eworks/core/brain_sync.py` implements an incremental sync that pushes new/updated durable knowledge from SQLite into gbrain without re-embedding unchanged content (FR-1210)
- [ ] SQLite writes happen first for every source table; `brain_sync.py` is never the primary write target for transactional state (FR-1210, CON-1201)
- [ ] The sync job is registered on the existing APScheduler instance (`eworks/core/scheduler.py`) — no new scheduling infrastructure introduced (FR-1210; DEP-1206)
- [ ] `eworks/core/brain_provenance.py` provides the single shared provenance/citation mapping module used by all three adapters (nurturer/closer/connector), linking each knowledge item to its source (agent, table, row id) (FR-1209, NFR-1206)
- [ ] Sync relies on gbrain's self-wiring knowledge graph to extract entity relationships (e.g. contact `works_at` company, conversation `relates_to` deal) without additional LLM calls — no custom relationship-extraction code is added (FR-1208)
- [ ] Test confirms removing/disabling gbrain leaves all synced SQLite tables (nurturer/closer/connector) fully intact and unmodified (NFR-1202, CON-1201)

## Dependencies
- Stories 12.2, 12.3, 12.4; DEP-1206

## Validation
- **Score:** 9/10
- **Verdict:** GO
- **Rationale:** Strong integration story with precise AC for incremental sync, shared provenance module, APScheduler reuse (no new infra), and an explicit additive-safety test proving SQLite integrity when gbrain is removed.
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
