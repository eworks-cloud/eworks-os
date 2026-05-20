# STORY-8.6: X CLI Commands

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As a developer/operator, I need `eos x` CLI commands to trigger X.com posting, analytics, and scheduling from the command line.

---

## Acceptance Criteria

- [x] `eos x tweet --topic ...` posts a single tweet
- [x] `eos x thread --topic ... --length 5` posts a thread
- [x] `eos x image --topic ...` posts an image tweet
- [x] `eos x video --topic ...` posts a video tweet
- [x] `eos x cross-post --linkedin-text ...` adapts and posts LinkedIn content
- [x] `eos x analytics --post-id N` shows tweet metrics
- [x] `eos x list --status posted` lists X posts
- [x] `eos x schedule` shows scheduling config
- [x] All commands support --dry-run and/or --auto-approve where appropriate

---

## Tasks

- [x] Add `x` group to eworks/cli/main.py
- [x] Implement all 8 subcommands
- [x] Use asyncio.run() for async orchestrator calls

---

## Files

- eworks/cli/main.py (modified — x group added)
