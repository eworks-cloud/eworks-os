# STORY-11.2 — Read-Only Data Access Layer

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Implement the single, centralized read-only data-access module over `eworks.db` that every view consumes — no new agent tables, no writes, one place for schema knowledge.

## Acceptance Criteria
- [ ] `web/lib/db/client.ts` opens a read-only SQLite connection (`query_only` PRAGMA or read-only open mode) against the DB path resolved in Story 11.1 (FR-1101, FR-1102, CON-1106)
- [ ] Read-only enforcement verified: no `INSERT`/`UPDATE`/`DELETE` statement exists anywhere under `web/lib/db/` (FR-1102, NFR-1101, CON-1101)
- [ ] `web/lib/db/queries/` exposes one query module per agent domain — `prospector-closer.ts`, `connector.ts`, `publisher.ts`, `conductor.ts`, `treasurer.ts`, `nurturer.ts` — as the single place schema knowledge lives; no agent business logic reimplemented (NFR-1105, CON-1106)
- [ ] Each query function returns an explicit `isEmpty` / `notConfigured` flag alongside data so callers render honest "no data yet" states rather than fabricating rows (FR-1103, NFR-1104, CON-1105)
- [ ] `web/lib/db/health.ts` exposes a connection-health check (`connected` / `db-not-found` / `read-error`) and structured logging of read requests/errors (NFR-1106)
- [ ] Queries use existing indexes (e.g. `idx_prospects_status`, `idx_invoices_status`) and are paginated/capped to meet the <2s render budget (NFR-1102)
- [ ] Concurrent-write test: an agent write script runs against `eworks.db` while the read layer queries it (WAL mode) with no lock/corruption (NFR-1101)

## Dependencies
- DEP-1101 through DEP-1108 (all seven agents' schemas); Story 11.1
