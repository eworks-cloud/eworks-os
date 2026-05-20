# STORY-10.6 — Connector Orchestrator

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 5

## Summary
Main orchestrator that wires together all listeners, reply generator, Slack notifier, and conversation tracker.

## Acceptance Criteria
- [ ] eworks/agents/connector/orchestrator.py created
- [ ] ConnectorOrchestrator extends BaseAgent
- [ ] _process_interaction() handles full pipeline per interaction
- [ ] run_platform() scans single platform
- [ ] run_all() scans all platforms concurrently
- [ ] Leads routed to notify_lead(), others to notify_interaction()
- [ ] Auto-reply when confidence >= 70% and not escalating
- [ ] _log_run() records stats to connector_runs table
