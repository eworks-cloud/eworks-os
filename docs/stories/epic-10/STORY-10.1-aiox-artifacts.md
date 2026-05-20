# STORY-10.1 — AIOX Story Files + DB Tables

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 3

## Summary
Create all AIOX story files for Epic 10, add connector DB tables to database.py, add slack-sdk dependency.

## Acceptance Criteria
- [ ] docs/stories/epic-10/ exists with EPIC-10-connector.md and STORY-10.1 through STORY-10.11
- [ ] database.py has add_connector_tables() method with social_interactions, conversation_threads, connector_runs
- [ ] requirements.txt includes slack-sdk>=3.27.0
- [ ] .env.example has all Slack env vars
