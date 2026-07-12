# STORY-12.6 — Brain CLI Commands: sync/search/think/status

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 3

## Summary
Typer CLI commands for manual capture, query, and health inspection of the brain.

## Acceptance Criteria
- [ ] `eworks/cli/main.py` gains a `brain` command group: `eos brain sync`, `eos brain search`, `eos brain think`, `eos brain status`, consistent with the platform's existing Typer CLI (FR-1214)
- [ ] `eos brain search "<query>"` calls gbrain `search` (fast hybrid retrieval, no LLM cost) and prints raw results (FR-1211)
- [ ] `eos brain think "<question>"` calls gbrain `think` and prints a synthesized, cited answer with gap analysis (FR-1212, NFR-1204)
- [ ] `eos brain status` reports engine (pglite), active embedding provider (from Story 12.1's status accessor), item count, and last sync time (FR-1204, FR-1214)
- [ ] `eos brain sync` manually triggers the Story 12.5 incremental sync job outside the scheduler (FR-1210, FR-1214)

## Dependencies
- Story 12.1, Story 12.5
