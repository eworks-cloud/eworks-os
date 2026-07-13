# Epic 14 — Documentation Backfill (Closer, Conductor, Treasurer, Nurturer)
**Type:** Retroactive / as-built documentation (documentation-only; zero code change)
**Status:** Draft
**Goal:** Write hindsight documentation for four shipped-but-undocumented agents and reconcile the two stale E1–E6 roadmap tables. Every FR traces to real code (Article IV — No Invention).
**Full PRD:** [`../../prd/epic-14-documentation-backfill.md`](../../prd/epic-14-documentation-backfill.md)

> One epic, four FR groups (agents share a single "documentation backfill" purpose, Dependencies, Risks, and Out-of-Scope). "SHALL document…" never means a code change — the four agents' source is read-only here (CON-1401).

## FR Groups Overview

| Group | Agent | Dir | FR band | Roadmap origin |
|-------|-------|-----|---------|----------------|
| A | closer | `eworks/agents/closer/` | FR-1401–FR-1408 | E3 — Proposal Generation |
| B | conductor | `eworks/agents/conductor/` | FR-1411–FR-1419 | E4 — Project Management |
| C | treasurer | `eworks/agents/treasurer/` | FR-1421–FR-1430 | E5 — Invoice & Billing |
| D | nurturer | `eworks/agents/nurturer/` | FR-1431–FR-1438 | E6 — Customer Success |

## Functional Requirements

### A. Closer (E3) — `orchestrator.py`, `discovery_processor.py`, `proposal_generator.py`, `exporter.py`, `delivery.py`
- FR-1401: Document `run_from_notes` end-to-end pipeline (notes→client→discovery→proposal→export→deliver→summary).
- FR-1402: Document `_find_or_create_client` dedupe + `clients` status transitions (discovery→won/lost).
- FR-1403: Document `DiscoveryProcessor` Claude extraction (`claude-3-5-sonnet-20241022`) → `discovery_calls`; minimal fallback.
- FR-1404: Document `ProposalGenerator` Claude 10-section Markdown proposal + template fallback → `proposals`.
- FR-1405: Document heuristic pricing/timeline ($150 default, `40+8*(i%3)`h, `max(4,ceil(n*1.5))`w, 30-day validity) — NOT E3's discount tiers.
- FR-1406: Document `ProposalExporter` Markdown + weasyprint PDF (`.txt` fallback) → `data/proposals/`.
- FR-1407: Document `deliver_via_telegram` (summary + file attachment via `TelegramReporter`) → status `sent`.
- FR-1408: Document `mark_accepted`/`mark_rejected`/`get_pipeline_summary` status + pipeline value tracking.

### B. Conductor (E4) — `orchestrator.py`, `tracker.py`, `sprint_manager.py`, `status_reporter.py`
- FR-1411: Document project CRUD (`projects` table, planning default, health 100).
- FR-1412: Document rule-based health score (base 100; −10/overdue task, −20 budget overrun, −15 no 7-day activity).
- FR-1413: Document `get_project_summary` (task counts, budget remaining, days remaining).
- FR-1414: Document manual `log_hours` (NOT Toggl integration).
- FR-1415: Document sprint/task CRUD + 6-state task lifecycle (`sprints`/`project_tasks`).
- FR-1416: Document kanban board (5 cols), velocity (Σ done story points), `complete_sprint`.
- FR-1417: Document Claude weekly report (`claude-opus-4-5`) + template fallback → `project_updates`.
- FR-1418: Document `send_update_to_client` (Telegram), `check_blockers` (>2 days), `alert_if_at_risk` (<60).
- FR-1419: Document `run_daily_check` + `run_weekly_reports` orchestration.

### C. Treasurer (E5) — `orchestrator.py`, `invoice_generator.py`, `payment_tracker.py`, `reminder_system.py`
- FR-1421: Document `EW-YYYY-NNN` sequential numbering.
- FR-1422: Document `create_invoice` (line items, subtotal/tax/total, Net-N, auto-markdown) → `invoices`/`invoice_items`.
- FR-1423: Document branded "EWORKS LABS" Markdown invoice.
- FR-1424: Document PDF export (weasyprint, `.txt` fallback) → `data/invoices/`.
- FR-1425: Document manual `record_payment` (mark paid when amount≥total; partial handling) — NOT Stripe.
- FR-1426: Document `get_overdue_invoices` + `mark_overdue_invoices`.
- FR-1427: Document `get_revenue_summary` (month/quarter/year, collection rate) — NOT MRR/P&L.
- FR-1428: Document 6 reminder templates + `send_reminder` → `payment_reminders`; NOTE `due_today`/`final_notice` are never dispatched.
- FR-1429: Document `run_daily_reminders` escalation (upcoming/3d/7d/14d) + same-day dedupe.
- FR-1430: Document `run_daily` orchestration + Telegram finance report.

### D. Nurturer (E6) — `orchestrator.py`, `health_scorer.py`, `onboarding.py`, `checkin_system.py`, `upsell_detector.py`
- FR-1431: Document 4-component (25 pts each) health scoring → `client_health_scores`.
- FR-1432: Document component thresholds (payment 25/15/5; engagement 30d/60d/older; project scaled; satisfaction NPS≥8/6-7/<6).
- FR-1433: Document `get_health_trend` + `get_at_risk_clients` (<60; NOTE E6 metric said <40).
- FR-1434: Document 7-step onboarding checklist (`onboarding_checklists`) — a shipped ADDITION beyond E6.
- FR-1435: Document AI check-ins (`claude-opus-4-5`) + generic fallback → `client_checkins`.
- FR-1436: Document `record_response` (keyword sentiment, NPS) + `run_scheduled_checkins` (>30 days).
- FR-1437: Document Claude upsell detection (1–3 opps) → `upsell_opportunities` + `get_pipeline_value`.
- FR-1438: Document `run_daily` orchestration (score→alert→checkins).

## Non-Functional Requirements
- NFR-1401: Traceability — every FR names a real module/function (Article IV).
- NFR-1402: Zero code/behavior change to the four agents (hard).
- NFR-1403: Correct 15-table ownership map per agent from `eworks/core/database.py`.
- NFR-1404: Delivery-channel fidelity — Telegram-only (`prospector/reporter.py::TelegramReporter`); no email.
- NFR-1405: AI-usage fidelity — direct `import anthropic`, graceful fallbacks, inconsistent model IDs (sonnet vs opus) cross-ref Epic 13 A-1301.
- NFR-1406: Divergence honesty — thinner-than-vision code stated plainly, not aspirationally.
- NFR-1407: Roadmap consistency after reconciliation without deleting/renumbering E1–E6 rows.
- NFR-1408: Format parity with epic-13 (PRD) and epic-10 (short-form).

## Constraints
- CON-1401: Documentation only; zero code change (hard). Unused templates + model-ID inconsistency are documented, never fixed.
- CON-1402: No invention; document only read source; divergences are §12 findings.
- CON-1403: No STORY-14.x files here (that is @sm's job).
- CON-1404: Roadmap reconciliation by annotation only; preserve/keep E1–E6 rows.
- CON-1405: Divergences are findings, not a work list; no remediation.
- CON-1406: `14xx` ID band, consistent between PRD and this doc.

## Roadmap Divergence Findings (summary — full tables in PRD §12)
- **E3/closer:** no web/company research, no package matcher, no case-study library, flat pricing (no tiers), Telegram-only (no email), no follow-up.
- **E4/conductor:** internal SQLite (no Linear/Notion/ClickUp), manual hours (no Toggl), no milestones/review-queue/retro/capacity, blocker >2d (vision >1d), Telegram not email.
- **E5/treasurer:** manual payments (no Stripe), Telegram not email, no expense/P&L/tax/retainer/MRR, `due_today`+`final_notice` templates dead.
- **E6/nurturer:** 4×25 model + at-risk <60 (vision <40), keyword sentiment + manual NPS (no Typeform), no renewals/KB/testimonials/referrals/anniversary/LTV; 7-step onboarding is an addition.
- **Cross-cutting:** roadmap promised PostgreSQL + email + Docker-per-agent; code is SQLite + Telegram + no per-agent containers.

## Deliverables
1. `docs/prd/epic-14-documentation-backfill.md` (full PRD).
2. `docs/stories/epic-14/EPIC-14-documentation-backfill.md` (this doc).
3. `docs/prd/product-roadmap.md` — both stale E1–E6 tables reconciled with real-epic/status annotation (CON-1404).

## Data Model Ownership (from `eworks/core/database.py`)
| Agent | Tables |
|-------|--------|
| closer | `clients` (shared), `discovery_calls`, `proposals` |
| conductor | `projects`, `sprints`, `project_tasks`, `project_updates` |
| treasurer | `invoices`, `invoice_items`, `payments`, `payment_reminders` |
| nurturer | `onboarding_checklists`, `client_health_scores`, `upsell_opportunities`, `client_checkins` |

## Out of Scope
Any code change to the four agents; closing E3–E6 vision gaps; STORY-14.x creation; migrating `import anthropic` call sites (Epic 13); documenting prospector/publisher/connector (already done); renumbering/deleting E1–E6 rows; PostgreSQL/Docker architecture-doc changes.
