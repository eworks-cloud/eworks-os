# STORY-1.8 — Scheduler + CLI

**Status:** ✅ Done
**Epic:** Epic 1 — LinkedIn Prospector Agent
**Agent:** @dev (Dex)

## Description
Build the APScheduler-backed background scheduler and full Click CLI with 14 commands.

## Acceptance Criteria
- [x] `SchedulerManager` with `add_campaign_job()`, `remove_job()`, `list_jobs()`, `start()`, `stop()`
- [x] APScheduler BackgroundScheduler with cron triggers
- [x] 14 CLI commands via Click:
  - `eworks auth login / status`
  - `eworks campaign create / list / start / pause`
  - `eworks prospect list / score`
  - `eworks agent run / status`
  - `eworks report daily`
  - `eworks config set / show`
  - `eworks daemon start / stop / status`
- [x] `--json` flag on all commands for JSON output
- [x] CLI entrypoint in `pyproject.toml`: `eworks = "eworks.cli.main:cli"`

## Commit
`feat(cli): full Click CLI + APScheduler — 14 commands with JSON output`
