# STORY-12.4 — Connector Knowledge Capture Adapter

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 3

## Summary
Capture the connector's cross-platform conversation history into gbrain, associated with the contact and, where linked, the client entity.

## Acceptance Criteria
- [ ] `eworks/agents/connector/brain_adapter.py` captures interactions and their content/sentiment/lead signals (`social_interactions`) and thread context summaries (`conversation_threads`), associated with the author/contact and, where linked, the client entity (FR-1207)
- [ ] Each captured item carries provenance back to its source SQLite row (agent=connector, table, row id) (FR-1209)
- [ ] Adapter writes are best-effort/non-blocking relative to the connector's primary SQLite work (NFR-1205)
- [ ] `brain_adapter.py` is isolated to `eworks/agents/connector/` so a connector schema change affects only this adapter (NFR-1207)

## Dependencies
- Story 12.1; DEP-1205
