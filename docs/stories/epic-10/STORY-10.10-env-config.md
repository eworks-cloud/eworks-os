# STORY-10.10 — Env Config + Dependencies

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 1

## Summary
Add all required Slack env vars to .env.example and slack-sdk to requirements.txt.

## Acceptance Criteria
- [ ] .env.example has SLACK_BOT_TOKEN + 5 channel IDs
- [ ] requirements.txt has slack-sdk>=3.27.0
- [ ] pip install succeeds
