# STORY-12.8 — gbrain MCP Server Registration — Setup Doc & Script for @devops

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 2

## Summary
Deliver the setup documentation/script @devops will run to register gbrain as an MCP server. This story's deliverable is the doc/script only — actual `claude mcp add` execution is @devops-exclusive per `.claude/rules/mcp-usage.md` and CON-1207.

## Acceptance Criteria
- [ ] `docs/ops/gbrain-mcp-setup.md` documents the exact registration command (`claude mcp add gbrain -- gbrain serve`) and prerequisites (gbrain installed, PGLite store initialized per Story 12.1), for @devops to execute (FR-1215, CON-1207)
- [ ] `scripts/setup-gbrain-mcp.sh` packages the prerequisite checks (gbrain binary present, brain store initialized) as a script @devops can run before registration; the script does not itself call `claude mcp add` (FR-1215, CON-1207)
- [ ] `docs/ops/gbrain-mcp-setup.md` includes a verification step (a sample "what do we know about client X?" query) @devops can run post-registration to confirm a Claude Code session can query the brain (FR-1215)
- [ ] The story file explicitly notes: this story does NOT execute `claude mcp add` — that step is @devops-exclusive per `agent-authority.md` and `mcp-usage.md`; this story delivers documentation and a prerequisite script only (CON-1207)

## Dependencies
- Story 12.1; DEP-1208
