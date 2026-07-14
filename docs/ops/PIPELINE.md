# Autonomous SDC Pipeline — Runbook & Memory

**This is the source of truth for the hourly autonomous Story Development Cycle pipeline.** Every Routine firing session MUST read this file before acting. If anything in the Routine prompt conflicts with this file, this file wins. Sessions resuming pipeline work manually (Claude Code interactive sessions) should also start here.

Last updated: 2026-07-14 (UTC).

## Mission

Walk every story in Epics 11–17 through the full AIOX Story Development Cycle — Validate (@po) → Implement (@dev, YOLO) → QA Gate (@qa) → Push/PR/auto-merge (@devops) — unattended, one stage-transition per hourly firing, merging each story to `main` behind CI before the next story starts.

## Environment facts (verified, do not re-derive)

| Fact | Value |
|---|---|
| Repo | `eworks-cloud/eworks-os` |
| Work branch | `claude/autonomous-ai-company-jbkya7` (GitHub auto-deletes it after each PR merge — recreate from `origin/main` and `push -u` when missing) |
| Default branch | `main` — branch protection ON, requires PR + green CI |
| CI | `.github/workflows/ci.yml`: `python-tests` (pytest, 229 passing as of 2026-07-14) + `web-tests` (no-ops until `web/` exists) |
| Repo setting | "Allow auto-merge" enabled |
| Auth in firing sessions | Env vars `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITHUB_TOKEN` (fine-grained PAT: Contents R/W, Pull requests R/W, Workflows R/W, Checks RO). Raw `git` over HTTPS works. **Never print or commit token values. `.env` is gitignored — never stage it.** |
| Firing-session gaps | GitHub MCP tools and `gh` CLI are usually ABSENT; `aiox-*` custom agent types usually NOT registered. Use the fallbacks below. |
| AIOX framework | `.aiox-core/` v5.3.0 installed via official installer. L1/L2 boundary: never hand-edit `.aiox-core/`. Known upstream bug: the `aiox` CLI crashes on `quality/metrics-collector` — do NOT use the CLI; the SDC skills and task files work fine. |
| Python env | 3.12; `pip install -e ".[dev]"` then `pytest tests/` |

## Hard rules (non-negotiable)

1. **PUSH AFTER EVERY COMMIT.** Firing sessions are ephemeral containers — unpushed commits are permanently lost (this happened on 2026-07-14: a completed @po validation was lost). After any commit run `git push origin claude/autonomous-ai-company-jbkya7`; retry 4× with 2s/4s/8s/16s backoff on network errors; if the remote moved, `git pull --rebase` then push. Never end a firing with unpushed work.
2. **Scope guard:** only `docs/stories/epic-11/` … `epic-17/`, their PRDs in `docs/prd/`, and the code/tests those stories specify. Never touch Epics 1–10 content, never invent epics beyond 17, never force-push, never change branch protection, never hand-edit `.aiox-core/`.
3. **One stage-transition per firing.** Small blast radius, auditable. On rate-limit or API errors, stop silently — the next hourly firing is the retry.
4. **Kill switch:** if `docs/ops/PAUSE` exists, do nothing and stop. HALT conditions (below) are implemented by *creating* that file.
5. **Log every firing:** append one row to the table in `docs/ops/pipeline-state.md` (`UTC time | story | stage | outcome | PR# or —`), committed and pushed with the stage's changes.

## Epic order and current state

Process epics in this order (user-chosen sequencing): **11 → 12 → 13 → 14 → 17 → 15 → 16.** Within an epic, numeric story order.

| Epic | Theme | State (2026-07-14) |
|---|---|---|
| 11 | Operator Console (Next.js dashboard over `eworks.db`, read-only, in `web/`) | PRD + 11 stories (11.1–11.11) drafted. 11.1 validated GO 7.5/10 once but the commit was lost — re-validate. |
| 12 | Knowledge Management (gbrain PGLite, capture adapters, `/client` command) | PRD + 9 stories drafted |
| 13 | AI Provider Resilience (`eworks/core/ai.py`, Anthropic primary, Bedrock/DeepInfra/Fireworks/Together fallbacks, circuit breaker) | PRD + 8 stories drafted |
| 14 | Documentation Backfill (closer/conductor/treasurer/nurturer docs) | PRD `docs/prd/epic-14-documentation-backfill.md` + epic doc exist; **no stories yet → @sm must draft them** |
| 17 | DevOps/QA Tooling (gstack-inspired: /canary, /codex ideas) | **Not scoped → @pm must create PRD + epic doc first** |
| 15 | AI Client Migration (migrate 12 files with direct `import anthropic` onto Epic 13's AIClient) | **Not scoped → @pm** |
| 16 | Knowledge Capture Expansion & Brain UI Wiring (more agents into gbrain; wire Epic 11's Brain placeholder) | **Not scoped → @pm** |

**@pm scoping sources (Article IV — No Invention):** `docs/prd/product-roadmap.md`, `docs/architecture/autonomous-company-platform-analysis.md`, the existing Epic 11–14 PRDs (gap sections), and the codebase itself. Follow the format of `docs/prd/epic-13-ai-provider-resilience.md` (FR-/NFR-/CON- numbering) and `docs/stories/epic-13/` story format (`# STORY-{e}.{n} — Title`, `**Status:** Draft`, `**Points:**`, AC checklists citing FR IDs).

## State machine (first match wins)

Find the first story (epic order above, numeric story order) not yet Done-and-merged, then:

| Condition | Stage | Action |
|---|---|---|
| `docs/ops/PAUSE` exists | — | Stop immediately, no commits |
| Epic reached, PRD/epic doc missing | @pm | Scope the epic (PRD + `EPIC-*.md`), commit, push |
| Epic PRD exists, no STORY files | @sm | Draft all stories for the epic, commit, push |
| Story `**Status:** Draft` | @po | Run `validate-next-story` (10-point checklist). GO (≥7) → `Ready`. NO-GO → write required fixes into the story, keep `Draft` (next firing re-runs @po after fixes are applied by @sm) |
| `Ready` | @dev | YOLO mode `dev-develop-story`: implement ACs, add tests, run `pytest tests/` (MUST pass), update File List + checkboxes, → `InReview` |
| `InReview` | @qa | `qa-gate` (7 checks). PASS or CONCERNS-waived → `Done`. FAIL → findings into story, → `InProgress`; **2nd consecutive FAIL on the same story → HALT** |
| `Done`, no open PR | @devops | Push branch, open PR → `main`, enable auto-merge (CI-gated). Record PR # in log |
| `Done`, PR open | @devops | Check PR: merged → log `advance` (next firing starts next story, recreating the branch); checks failed → **HALT**; pending → log `waiting`, stop |
| Everything in Epics 11–17 Done + merged | — | Write `docs/ops/PAUSE` containing `PIPELINE COMPLETE`, push, stop |

**HALT procedure:** write `docs/ops/PAUSE` with a one-line reason (`HALT: <story> — <reason>`), commit, push, and state the reason prominently in the session's final message (it becomes the push notification). Humans resume by fixing the issue and deleting the file.

## Execution fallbacks (in order of preference)

**Agent stages** — use the first available path:
1. Agent tool with custom types `aiox-po` / `aiox-dev` / `aiox-qa` / `aiox-devops` / `aiox-pm` / `aiox-sm` (rarely registered in fresh firing sessions).
2. SDC skills shipped in the repo: `validate-story-draft`, `develop-story`, `review-story`, `close-story`, `aiox-commit`.
3. `general-purpose` agent (or inline execution) reading `.claude/agents/aiox-{role}.md` **plus the AIOX task file it references** (`.aiox-core/development/tasks/…`), following both faithfully. Always respect `.claude/rules/agent-authority.md` (e.g. only the @devops stage pushes PRs).

**GitHub operations without MCP/`gh`** — use the REST API with `curl`, header `Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN` (fall back to `$GITHUB_TOKEN`), `Accept: application/vnd.github+json`:
- Create PR: `POST https://api.github.com/repos/eworks-cloud/eworks-os/pulls` body `{"title","head":"claude/autonomous-ai-company-jbkya7","base":"main","body"}`
- List open PRs for the branch: `GET …/pulls?head=eworks-cloud:claude/autonomous-ai-company-jbkya7&state=open` (and `state=closed` + `merged_at` to detect merges)
- CI status: `GET …/commits/{head_sha}/check-runs`
- Enable auto-merge: GraphQL `enablePullRequestAutoMerge` (`POST https://api.github.com/graphql`). If that fails AND all check-runs have completed successfully, merge directly: `PUT …/pulls/{number}/merge` body `{"merge_method":"squash"}`. **Never merge with failing or pending checks.**
- Never echo commands that would print the token; pass it via the header from the env var.

## Commit conventions

Conventional commits referencing the story: `feat: implement data access layer [STORY-11.2]`, `docs(qa): gate PASS [STORY-11.2]`. Stage-transition commits should include the story file change and any code in one commit where practical.

## Key user decisions (do not re-litigate)

- Merge policy: PR + GitHub auto-merge gated on CI (never direct-to-main).
- Cadence: hourly Routine, fresh session per firing; the hourly cadence IS the rate-limit backoff.
- Scope: Epics 11–17 only, fixed.
- Epic sequencing after 13: 14 → 17 → 15 → 16.
- Epic 13 design: standalone opt-in `AIClient` module for resilience/fallback (not cost routing); zero-config Anthropic parity; migration of existing call sites deferred to Epic 15.
- YOLO mode throughout; no human interaction expected between HALTs.
