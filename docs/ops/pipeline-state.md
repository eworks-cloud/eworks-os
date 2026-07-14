# Autonomous SDC Pipeline — Run Log

Append-only log written by the hourly SDC pipeline Routine (Epics 11-17 only). One line per firing. This log is for forensics and stall-detection — the source of truth for pipeline state is always each story file's `**Status:**` field plus live GitHub PR state, not this file.

To pause the pipeline, create an empty file at `docs/ops/PAUSE` — the Routine checks for it first on every firing and no-ops if present. Delete the file to resume.

## Operating rules for Routine firing sessions — READ BEFORE ACTING

These rules OVERRIDE anything in the Routine prompt that conflicts with them. They exist because firing sessions are ephemeral containers: anything not pushed before the session ends is permanently lost.

1. **PUSH AFTER EVERY COMMIT — MANDATORY.** Immediately after any commit (story status change, implementation code, QA verdict, this log file), run `git push origin claude/autonomous-ai-company-jbkya7`. Never end a firing with unpushed commits. If push fails on a network error, retry up to 4 times with exponential backoff (2s/4s/8s/16s). If the remote has moved, `git pull --rebase origin claude/autonomous-ai-company-jbkya7` and push again. The 2026-07-14 firing lost a completed @po validation by committing without pushing — do not repeat this.
2. **If `aiox-po`/`aiox-dev`/`aiox-qa`/`aiox-devops` agent types are not registered** in your session, use this fallback chain, in order: (a) the SDC skills — `validate-story-draft`, `develop-story`, `review-story`, `close-story`; (b) a `general-purpose` agent instructed to read and follow `.claude/agents/aiox-{role}.md` plus the task file it references; (c) inline execution reading the same files. All three paths must respect `.claude/rules/agent-authority.md`.
3. **If GitHub MCP tools and `gh` CLI are unavailable**, use the GitHub REST API directly with `curl` and the token in `$GITHUB_PERSONAL_ACCESS_TOKEN` (or `$GITHUB_TOKEN`). Never print the token value. The @devops stage needs:
   - Create PR: `POST https://api.github.com/repos/eworks-cloud/eworks-os/pulls` with `{"title": ..., "head": "claude/autonomous-ai-company-jbkya7", "base": "main", "body": ...}` and header `Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN`.
   - Check CI on the PR head: `GET .../commits/{sha}/check-runs`.
   - Enable auto-merge (GraphQL `enablePullRequestAutoMerge`), or if auto-merge enablement fails and all checks have completed successfully, merge via `PUT .../pulls/{number}/merge` with `{"merge_method": "squash"}`. Never merge with failing or still-pending checks.
4. **Log discipline:** append exactly one row to the table below per firing (UTC timestamp, story, stage, outcome, PR number or `—`), commit it together with the stage's other changes, and push (rule 1).

| Timestamp (UTC) | Story | Stage | Outcome | PR |
|---|---|---|---|---|
