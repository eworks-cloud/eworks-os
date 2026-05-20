# STORY-8.6: X CLI Commands

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As a developer/operator, I need `eworks x` CLI commands to trigger X.com posting, analytics, and scheduling from the command line.

---

## Acceptance Criteria

- [x] `eworks x tweet --topic ...` posts a single tweet
- [x] `eworks x thread --topic ... --length 5` posts a thread
- [x] `eworks x image --topic ...` posts an image tweet
- [x] `eworks x video --topic ...` posts a video tweet
- [x] `eworks x cross-post --linkedin-text ...` adapts and posts LinkedIn content
- [x] `eworks x analytics --post-id N` shows tweet metrics
- [x] `eworks x list --status posted` lists X posts
- [x] `eworks x schedule` shows scheduling config
- [x] All commands support --dry-run and/or --auto-approve where appropriate

---

## Tasks

- [x] Add `x` group to eworks/cli/main.py
- [x] Implement all 8 subcommands
- [x] Use asyncio.run() for async orchestrator calls

---

## Files

- eworks/cli/main.py (modified — x group added)
