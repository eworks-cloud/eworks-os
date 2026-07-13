# PRD — Epic 14: Documentation Backfill (Closer, Conductor, Treasurer, Nurturer)

**Product:** Eworks OS — Multi-Agent Company Operating System
**Epic:** Epic 14 — Documentation Backfill for four shipped, undocumented agents
**Version:** 1.0.0
**Status:** Draft
**Author:** Morgan (PM)
**Owner:** Cesar Schneider, Eworks Labs
**Last Updated:** 2026-07-12

---

> **Source of truth — this is retroactive, as-built documentation.** Four agents — **closer**, **conductor**, **treasurer**, and **nurturer** — are real, committed, shipped Python code under `eworks/agents/` with **zero** PRD/story documentation, unlike prospector (`docs/prd/epic-1-linkedin-agent.md` + `docs/stories/epic-1/`) and publisher/connector (`docs/stories/epic-7/`…`epic-10/`). This epic writes hindsight documentation for **what already exists in code** — it does **not** propose new requirements or new capabilities. Every Functional Requirement below traces to a specific module/function that was read directly from source (Constitution Article IV — No Invention). Where the shipped code **diverges from or falls short of** the original E3–E6 roadmap vision, that divergence is documented explicitly as a finding, not hidden. This epic's own Article-IV compliance fix — reconciling the two stale E1–E6 roadmap tables in `docs/prd/product-roadmap.md` — is in scope here (see §7 / §9).

> **Framing note.** Because this is as-built documentation of shipped code (not a forward-looking feature epic), two sections are relabeled from the standard PRD template: **§2 "Business Objective" → "As-Built Capability Summary"** (what the code does today, not a future goal), and the usual **"Success Metrics" → §-embedded "Observed / Expected Behavior"** (what the shipped code actually does when run, not aspirational KPIs — there is nothing new to launch).

---

## Table of Contents
1. [Epic Overview](#1-epic-overview)
2. [As-Built Capability Summary](#2-as-built-capability-summary)
3. [Stakeholders](#3-stakeholders)
4. [Assumptions & Background](#4-assumptions--background)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Constraints](#7-constraints)
8. [User Stories & Acceptance Criteria](#8-user-stories--acceptance-criteria)
9. [Out of Scope](#9-out-of-scope)
10. [Dependencies](#10-dependencies)
11. [Risks](#11-risks)
12. [Roadmap Divergence Findings (E3–E6 Vision vs. As-Built)](#12-roadmap-divergence-findings)
13. [Glossary](#13-glossary)

---

## 1. Epic Overview

Eworks OS has shipped seven agents. Three of them are documented: **prospector** (Epic 1) and **publisher/connector** (Epics 7–10). Four of them are **not**: the **closer** (proposal generation), **conductor** (project management), **treasurer** (invoice & billing), and **nurturer** (customer success). All four are real, committed, tested Python under `eworks/agents/`, wired into the CLI (`eworks/cli/main.py`) and the shared SQLite database (`eworks/core/database.py`), yet carry **no PRD and no story documentation**. A reader of `docs/` today would not know these agents exist, what they do, what tables they own, or how they diverge from the plan.

This epic closes that documentation gap. It produces **as-built documentation** describing exactly what these four agents do today — their modules, their public methods, their database tables, their AI usage, their delivery channel, and their observed behavior — and it reconciles the two stale roadmap tables that still show these capabilities as "📋 Planned" under the original E3–E6 letter numbering.

Critically, this is a **documentation-only** epic. It changes **zero** lines of the four agents' code, alters **zero** behavior, and invents **zero** features. Where the code is thinner than the E3–E6 roadmap originally promised (and it is, materially — see §12), this epic records the gap as a finding for future prioritization; it does **not** "fix" the code to match the old vision. The one file this epic *edits* is `docs/prd/product-roadmap.md`, and only to annotate the two tables so a reader is no longer misled.

The four agents, at a glance (all read directly from source):

| Agent | Directory | Roadmap origin | What it actually is today |
|-------|-----------|----------------|---------------------------|
| **closer** | `eworks/agents/closer/` | E3 — Proposal Generation | Discovery-notes → Claude requirement extraction → Claude proposal (Markdown, 10 sections) → PDF/txt export → Telegram delivery → status tracking |
| **conductor** | `eworks/agents/conductor/` | E4 — Project Management | Internal SQLite projects/sprints/tasks (kanban + velocity) → rule-based health scoring → Claude weekly reports → Telegram alerts + hour logging |
| **treasurer** | `eworks/agents/treasurer/` | E5 — Invoice & Billing | Invoice generation (`EW-YYYY-NNN`, Markdown + PDF/txt) → manual payment recording → overdue detection → escalating Telegram reminders → daily finance report |
| **nurturer** | `eworks/agents/nurturer/` | E6 — Customer Success | 4-component (25 pts each) client health scoring → 7-step onboarding checklist → Claude AI check-ins + keyword sentiment/NPS → Claude upsell detection → at-risk Telegram alerts |

---

## 2. As-Built Capability Summary

> This section replaces the standard "Business Objective." Because nothing new is being built, there is no problem/solution/KPI to state — only a summary of the capability that **already exists** and why documenting it matters.

| Item | Detail |
|------|--------|
| **Situation** | Four production agents (closer, conductor, treasurer, nurturer) — ~18 distinct capabilities across 17 Python modules and 15 database tables — are fully shipped and CLI-wired but carry no PRD/story docs. Their behavior, data model, AI usage, and (significant) divergence from the E3–E6 roadmap vision are undocumented and invisible in `docs/`. |
| **What this epic delivers** | Retroactive, as-built documentation: this PRD (FR-14xx grouped per agent, each tracing to named code), a companion short-form epic doc (`docs/stories/epic-14/EPIC-14-documentation-backfill.md`), and a reconciliation of the two stale E1–E6 roadmap tables so shipped work is no longer shown as "📋 Planned." |
| **Why it matters** | Documentation parity across all seven agents; a single source of truth for what closer/conductor/treasurer/nurturer actually do; an honest, written record of where the code falls short of E3–E6 (input for future scoping); and Article-IV/roadmap hygiene (shipped ≠ planned). |
| **Explicit non-goal** | Building, extending, refactoring, or "completing" any of the four agents. Divergences from E3–E6 are **findings**, not a work list for this epic. |
| **Strategic value** | Removes a discoverability and onboarding blind spot: any future @sm/@dev/@architect touching these agents now has authoritative as-built docs, and any future planning of E3–E6 "gap-closing" epics starts from a written baseline instead of code archaeology. |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Cesar Schneider | Confirms the as-built documentation matches intent; owns future prioritization of the E3–E6 gaps surfaced in §12 |
| PM | Morgan | This PRD; as-built accuracy; roadmap-table reconciliation; divergence findings |
| Architect | Aria | Reviews that documented data model / module boundaries match the real code |
| SM | River | Creates STORY-14.x files from this PRD (separate task; not part of this epic) |
| Dev | Dex | Consumer of the docs when future work touches these agents; makes **no** code change under this epic |
| Analyst | Alex | May use §12 divergence findings to shape future gap-closing research |

---

## 4. Assumptions & Background

- **A-1401** — All four agents exist and are committed. Verified by reading source and `git log`: closer (`823cc71` invoice… actually `df63e85`+ for treasurer, `26a78da`/`0efaa85` conductor/nurturer commits, etc.), with feature-named commits such as `feat(nurturer): health scorer — 4-component 100pt scoring system`, `feat(treasurer): invoice generator — numbering + markdown + PDF export`, `feat(conductor): sprint manager — kanban board + velocity tracking`, `feat(nurturer): check-in system — AI personalized messages + NPS tracking`.
- **A-1402** — None of the four has PRD or story docs. Verified: `docs/stories/` contains `epic-1`, `epic-7`…`epic-13` but **no** epic covering closer/conductor/treasurer/nurturer; `docs/prd/` has no proposal/PM/billing/customer-success PRD.
- **A-1403** — All four share the single SQLite database defined in `eworks/core/database.py`. Their tables are created lazily via `db.add_closer_tables()` / `add_conductor_tables()` / `add_treasurer_tables()` / `add_nurturer_tables()` (called from the CLI). SQLite is the system of record — **not** the PostgreSQL described in the roadmap's "Platform Architecture Principles."
- **A-1404** — All four deliver exclusively via **Telegram**, reusing `eworks/agents/prospector/reporter.py::TelegramReporter`. None sends email, despite the E3–E6 vision repeatedly describing email delivery.
- **A-1405** — All AI calls use the Anthropic SDK **directly** (`import anthropic`), matching Epic 13's confirmed 12-call-site pattern (A-1301 lists `closer/discovery_processor.py`, `closer/proposal_generator.py`, `nurturer/upsell_detector.py`, `nurturer/checkin_system.py`). Model IDs are **inconsistent across agents**: closer uses `claude-3-5-sonnet-20241022`; conductor's status reporter, nurturer's check-in system, and nurturer's upsell detector use `claude-opus-4-5`. This epic documents the inconsistency; Epic 13 is the vehicle that would later unify it.
- **A-1406** — Every Claude-dependent method has a **deterministic non-AI fallback** (template proposal, template weekly report, generic check-in message, default upsell) so the pipeline degrades gracefully when the API is unavailable.
- **A-1407** — PDF export (closer + treasurer) uses `weasyprint` + `markdown2` and **falls back to a styled `.txt`** when those libraries are absent. Exports land in `data/proposals/` and `data/invoices/`.
- **A-1408** — The roadmap's original E3–E6 sections describe **intended** features. The shipped code is materially thinner (no web research, no external PM tool, no Stripe, no renewals, etc.). Documenting these gaps is a deliverable (§12), not a defect to remediate here.
- **A-1409** — `docs/prd/product-roadmap.md` contains **two** tables still using the E1–E6 letter numbering that were never reconciled with the real `docs/stories/epic-N/` folders: the top **"Roadmap Summary"** (lines ~23–30) and the bottom **"Cumulative Story Estimates"** under "Platform Roadmap Summary" (lines ~422–430). Both still show E3–E6 as "📋 Planned."

---

## 5. Functional Requirements

> Each FR documents a capability **that already exists in code**. FR IDs are grouped per agent: **FR-1401–FR-1408 closer**, **FR-1411–FR-1419 conductor**, **FR-1421–FR-1430 treasurer**, **FR-1431–FR-1438 nurturer**. "SHALL be documented as…" here means "the documentation SHALL accurately describe the shipped behavior of…"; no FR mandates a code change.

### 5.1 Closer Agent — Proposal Generation (`eworks/agents/closer/`)

**FR-1401 — End-to-End Proposal Pipeline (`orchestrator.py::CloserOrchestrator.run_from_notes`)**
The documentation SHALL describe the closer's single-entry pipeline `run_from_notes(client_name, company, notes, deliver=True)` that chains: find/create client → create discovery call → extract requirements → generate proposal → export Markdown + PDF → (optionally) deliver via Telegram → return a summary dict (`proposal_id`, `client_id`, `total_price`, `timeline_weeks`, `md_path`, `pdf_path`, `delivered`, `status`, `extraction`).

**FR-1402 — Client Resolution & Persistence (`orchestrator.py::_find_or_create_client`)**
The documentation SHALL describe deduplicated client resolution (match on `name` + `company`, else insert with `status='discovery'`) against the shared `clients` table (`eworks/core/database.py`), and the client status transitions the closer drives (`discovery` → `won`/`lost`).

**FR-1403 — Discovery Note Extraction via Claude (`discovery_processor.py::DiscoveryProcessor`)**
The documentation SHALL describe `create_call()` (inserts a `discovery_calls` row, status `notes_taken`) and `process_notes()` → `_extract_with_claude()`, which prompts Claude (`claude-3-5-sonnet-20241022`, max 2000 tokens) to return structured JSON — `pain_points`, `technical_requirements`, `budget_range`, `timeline_expectations`, `decision_makers`, `existing_tech_stack`, `success_criteria` — persisted back to `discovery_calls` (status → `processed`), with a minimal-structure fallback on any exception.

**FR-1404 — Claude Proposal Drafting with Template Fallback (`proposal_generator.py::ProposalGenerator.generate` / `_generate_with_claude`)**
The documentation SHALL describe generation of a full Markdown proposal via Claude (`claude-3-5-sonnet-20241022`, max 4000 tokens, "Cesar Schneider / Eworks Labs" system persona) across ten fixed sections (Executive Summary, Problem Understanding, Proposed Solution, Scope of Work, Technical Approach, Timeline, Investment, Why Eworks Labs, Next Steps, Terms & Conditions), and the deterministic fallback template proposal used when the API fails. Persists to `proposals` (status `draft`) and advances `discovery_calls.status` to `proposal_generated`.

**FR-1405 — Heuristic Pricing & Timeline Engine (`proposal_generator.py::format_pricing_table` / `_get_hourly_rate`)**
The documentation SHALL describe the as-built pricing heuristic: hourly rate from `settings_store` (`hourly_rate`) defaulting to **$150**, `HOURS_PER_DELIVERABLE=40` with a `+8*(i%3)` per-position variance, `total = Σ(hours × rate)`, `timeline_weeks = max(4, ceil(num_deliverables × 1.5))`, and 30-day proposal validity. It SHALL note this is a flat heuristic, **not** the configurable discount-tier pricing engine E3 envisioned.

**FR-1406 — Proposal Export to Markdown & PDF (`exporter.py::ProposalExporter`)**
The documentation SHALL describe `export_markdown()` and `export_pdf()` writing to `data/proposals/` (`{id}-{slug}.{md|pdf|txt}`), PDF via `weasyprint` + `markdown2` with a branded HTML/CSS template, and the styled `.txt` fallback when PDF libraries are unavailable. `proposals.pdf_path` is updated in the DB.

**FR-1407 — Telegram Proposal Delivery (`delivery.py::ProposalDelivery.deliver_via_telegram`)**
The documentation SHALL describe delivery of a formatted HTML summary (client, title, investment, timeline, status, exec-summary excerpt) plus the exported file as a Telegram document attachment, reusing prospector's `TelegramReporter`, and the `proposals.status` → `sent` (+ `sent_at`) transition on success.

**FR-1408 — Proposal Status Tracking & Pipeline Summary (`delivery.py::mark_accepted` / `mark_rejected` / `get_pipeline_summary`)**
The documentation SHALL describe `mark_accepted()` (proposal → `accepted`, client → `won`), `mark_rejected(reason)` (proposal → `rejected`, client → `lost`, reason appended to client notes), and `get_pipeline_summary()` (counts per status + `total_value_pipeline` for sent/viewed/accepted + `total_value_won`).

### 5.2 Conductor Agent — Project Management (`eworks/agents/conductor/`)

**FR-1411 — Project CRUD (`tracker.py::ProjectTracker.create_project` / `get_project` / `get_all_active_projects`)**
The documentation SHALL describe project creation into the `projects` table (status default `planning`, `hourly_rate` default 150, `health_score` default 100) and active-project retrieval used by the daily/weekly runs.

**FR-1412 — Rule-Based Project Health Scoring (`tracker.py::calculate_health_score`)**
The documentation SHALL describe the deterministic 0–100 score: base **100**, **−10 per overdue task** (`due_date < today` and not `done`/`cancelled`), **−20 if budget overrun** (`hours_logged × hourly_rate > budget`), **−15 if no task activity in 7 days** (only when the project has tasks and is ≥7 days old), clamped to 0–100 and persisted to `projects.health_score`.

**FR-1413 — Project Summary (`tracker.py::get_project_summary`)**
The documentation SHALL describe the rich summary (task totals by status, `hours_logged`, `budget_remaining = budget − hours_logged×rate`, `days_remaining` to `end_date`, live health score).

**FR-1414 — Hour Logging (`tracker.py::log_hours`)**
The documentation SHALL describe manual hour logging that increments `projects.hours_logged` and optionally `project_tasks.hours_logged`. It SHALL note this is manual entry, **not** the Toggl/automatic time-tracking integration E4 envisioned.

**FR-1415 — Sprint & Task Lifecycle (`sprint_manager.py::create_sprint` / `add_task` / `update_task_status`)**
The documentation SHALL describe sprint creation (`sprints` table), task creation into `project_tasks` (default status `backlog`, priority `medium`, `story_points` default 1, `assignee` default "AI Agent"), and the validated 6-state task lifecycle (`backlog`/`todo`/`in_progress`/`review`/`done`/`cancelled`) with `completed_at` set on `done`.

**FR-1416 — Kanban Board & Velocity (`sprint_manager.py::get_sprint_board` / `get_sprint_velocity` / `complete_sprint`)**
The documentation SHALL describe the 5-column Kanban view (backlog/todo/in_progress/review/done), velocity as `Σ story_points` of `done` tasks, and `complete_sprint()` (marks sprint `completed`, persists velocity, returns completed + incomplete task lists).

**FR-1417 — Claude Weekly Report with Template Fallback (`status_reporter.py::generate_weekly_report` / `_call_claude`)**
The documentation SHALL describe weekly-report generation: gather completed-this-week / in-progress / blocker / health context, prompt Claude (`AsyncAnthropic`, `claude-opus-4-5`, max 1024 tokens) for a <300-word client-facing update (✅/🔄/📅/⚠️/💚 structure), fall back to a plain template on error, and persist to `project_updates` (`update_type='weekly_report'`, `sent_to_client=0`).

**FR-1418 — Client Delivery, Blocker Detection & At-Risk Alerts (`status_reporter.py::send_update_to_client` / `check_blockers` / `alert_if_at_risk`)**
The documentation SHALL describe Telegram delivery of a saved update (marks `sent_to_client=1`), blocker detection (`in_progress` tasks overdue by **>2 days**), and at-risk alerting when `health_score < 60`. It SHALL note blockers use a >2-day rule (E4 vision said >1 day) and delivery is Telegram, not email.

**FR-1419 — Conductor Orchestration (`orchestrator.py::run_daily_check` / `run_weekly_reports`)**
The documentation SHALL describe the daily loop (recompute health, check blockers, alert if `health < 60`; returns `projects_checked`/`alerts_sent`/`at_risk_count`) and the weekly loop (generate + send a report per active project; returns `projects_reported`/`updates_sent`).

### 5.3 Treasurer Agent — Invoice & Billing (`eworks/agents/treasurer/`)

**FR-1421 — Sequential Invoice Numbering (`invoice_generator.py::generate_invoice_number`)**
The documentation SHALL describe `EW-YYYY-NNN` numbering (year + 3-digit sequence derived from a `COUNT(*)` of the year's invoices).

**FR-1422 — Invoice Creation with Line Items (`invoice_generator.py::create_invoice`)**
The documentation SHALL describe creation into `invoices` (+ `invoice_items`) computing `subtotal = Σ(qty × unit_price)`, `tax_amount = subtotal × tax_rate/100`, `total`, `payment_terms = "Net {due_days}"` (default 30), status `draft`, and auto-generation of Markdown on create.

**FR-1423 — Branded Markdown Invoice (`invoice_generator.py::generate_markdown`)**
The documentation SHALL describe the "EWORKS LABS" branded Markdown invoice (header, Bill-To, Services table, Summary with subtotal/tax/total, payment instructions, notes) saved to `invoices.markdown_content`.

**FR-1424 — Invoice PDF Export (`invoice_generator.py::export_pdf`)**
The documentation SHALL describe PDF export to `data/invoices/` via `weasyprint` + `markdown2` (branded CSS), the styled `.txt` fallback, and the `invoices.pdf_path` update.

**FR-1425 — Payment Recording (`payment_tracker.py::record_payment`)**
The documentation SHALL describe recording into `payments`, marking the invoice `paid` (+ `paid_at`, `paid_amount`) when `amount ≥ total`, and logging partial payments otherwise. It SHALL note payments are recorded **manually**, **not** via a Stripe/processor integration (E5 vision).

**FR-1426 — Overdue Detection (`payment_tracker.py::get_overdue_invoices` / `mark_overdue_invoices`)**
The documentation SHALL describe listing sent/viewed/overdue invoices past `due_date` (joined to client) and the status transition `sent`/`viewed` → `overdue` for past-due invoices.

**FR-1427 — Revenue Summary (`payment_tracker.py::get_revenue_summary`)**
The documentation SHALL describe period summaries (`month`/`quarter`/`year`) returning `total_invoiced`, `total_paid`, `total_overdue`, `outstanding_count`, `paid_count`, `overdue_count`, and `collection_rate_pct`. It SHALL note this is collection/AR reporting, **not** the MRR/profitability/P&L reporting E5 envisioned.

**FR-1428 — Escalating Reminder Templates & Send (`reminder_system.py::REMINDER_TEMPLATES` / `send_reminder`)**
The documentation SHALL describe the six HTML reminder templates (`upcoming`, `due_today`, `overdue_3d`, `overdue_7d`, `overdue_14d`, `final_notice`), Telegram send, and logging every attempt to `payment_reminders` (`sent_via='telegram'`). It SHALL note that `due_today` and `final_notice` templates exist but are **never dispatched** by the daily scheduler (FR-1429) — a documented dead-template gap.

**FR-1429 — Daily Reminder Scheduler (`reminder_system.py::run_daily_reminders`)**
The documentation SHALL describe the daily escalation logic over sent/viewed/overdue invoices: `upcoming` (due in 0–3 days), `overdue_3d` (≥3 days overdue), `overdue_7d` (≥7), `overdue_14d` (≥14), with a same-day dedupe guard per `(invoice, reminder_type)`. Returns `reminders_sent`/`invoices_checked`.

**FR-1430 — Treasurer Daily Orchestration (`orchestrator.py::run_daily`)**
The documentation SHALL describe the daily run: mark overdue → run reminders → compile monthly revenue → send a formatted Telegram finance report (invoiced/paid/overdue/collection-rate + counts + reminders sent).

### 5.4 Nurturer Agent — Customer Success (`eworks/agents/nurturer/`)

**FR-1431 — 4-Component Health Scoring (`health_scorer.py::calculate_health` / `record_health_score`)**
The documentation SHALL describe the 0–100 client health score as the sum of four 25-point components — `payment_score`, `engagement_score`, `project_health_score`, `satisfaction_score` — clamped 0–100 and persisted to `client_health_scores` (with per-component columns).

**FR-1432 — Component Scoring Rules (`health_scorer.py::_calc_payment_score` / `_calc_engagement_score` / `_calc_project_health_score` / `_calc_satisfaction_score`)**
The documentation SHALL describe the exact thresholds: payment (25 = 0 overdue, 15 = 1, 5 = 2+); engagement (25 = responded ≤30d, 15 = ≤60d, 5 = older/none); project (avg active-project `health_score` scaled to 25, neutral 15 if none); satisfaction (25 = NPS ≥8, 15 = 6–7 or none, 5 = <6). Each gathers data defensively (tables may not yet exist).

**FR-1433 — Health Trend & At-Risk Detection (`health_scorer.py::get_health_trend` / `get_at_risk_clients`)**
The documentation SHALL describe the last-N score history and at-risk detection (each client's most-recent score `< 60`). It SHALL note the as-built threshold is **<60** (E6 success metric referenced <40).

**FR-1434 — 7-Step Onboarding Checklist (`onboarding.py::OnboardingManager`)**
The documentation SHALL describe the `DEFAULT_STEPS` (kickoff, credentials, project setup, comms channels, first deliverable, feedback session, workflow established) created into `onboarding_checklists`, `complete_step()`, `get_onboarding_progress()` (completion %, next step), and `send_onboarding_reminder()` (Telegram, when <100% and stale >3 days). It SHALL note onboarding was **not** in the E6 vision — it is a shipped addition.

**FR-1435 — AI-Personalized Check-ins (`checkin_system.py::send_checkin` / `_generate_checkin_message`)**
The documentation SHALL describe context gathering (client, recent projects, last check-in, recent deliverables), Claude message generation (`claude-opus-4-5`, max 512 tokens, warm 3–5 sentence tone), Telegram send, recording into `client_checkins`, and the generic fallback message on API failure.

**FR-1436 — Response Recording & Scheduled Check-ins (`checkin_system.py::record_response` / `run_scheduled_checkins` / `_classify_sentiment`)**
The documentation SHALL describe response capture with **keyword-based** sentiment classification (positive/neutral/negative word sets) and optional NPS, and the scheduled batch that sends monthly check-ins to clients whose last check-in was >30 days ago. It SHALL note sentiment is keyword-based (not AI) and NPS is captured manually (not via Typeform, per E6 vision).

**FR-1437 — Claude Upsell Detection (`upsell_detector.py::detect_opportunities` / `get_pipeline_value`)**
The documentation SHALL describe profile assembly (invoice/project/check-in summaries + latest health score), Claude identification of 1–3 opportunities (`claude-opus-4-5`, max 1024 tokens) returning `opportunity_type`/`description`/`estimated_value`/`confidence`, persistence to `upsell_opportunities`, a default opportunity fallback on failure, and `get_pipeline_value()` (open pipeline grouped by confidence).

**FR-1438 — Nurturer Daily Orchestration (`orchestrator.py::run_daily`)**
The documentation SHALL describe the daily run: record health scores for all non-lost/churned clients → alert at-risk clients via Telegram → run scheduled check-ins; returns `clients_scored`/`at_risk`/`checkins_sent`/`clients_checked`.

---

## 6. Non-Functional Requirements

**NFR-1401 — Traceability (Article IV — No Invention)**
Every FR SHALL name the specific module and function/class it documents, and SHALL contain no capability that is not present in the read source. The documentation SHALL be verifiable by opening the cited file.

**NFR-1402 — Zero Code / Behavior Change**
Producing this documentation SHALL change **no** line of any file under `eworks/agents/closer|conductor|treasurer|nurturer/`, `eworks/core/database.py`, or `eworks/cli/main.py`, and SHALL alter no runtime behavior (hard requirement; see CON-1401).

**NFR-1403 — Accurate Data-Model Documentation**
The documentation SHALL correctly attribute each of the 15 tables to its owning agent as defined in `eworks/core/database.py`: closer (`clients` shared, `discovery_calls`, `proposals`); conductor (`projects`, `sprints`, `project_tasks`, `project_updates`); treasurer (`invoices`, `invoice_items`, `payments`, `payment_reminders`); nurturer (`onboarding_checklists`, `client_health_scores`, `upsell_opportunities`, `client_checkins`).

**NFR-1404 — Delivery-Channel Fidelity**
The documentation SHALL correctly record that all four agents deliver via Telegram (`prospector/reporter.py::TelegramReporter`) and none via email, matching the code.

**NFR-1405 — AI-Usage Fidelity**
The documentation SHALL correctly record direct `import anthropic` usage, the graceful non-AI fallbacks, and the **inconsistent model IDs** across agents (`claude-3-5-sonnet-20241022` in closer; `claude-opus-4-5` in conductor/nurturer), cross-referencing Epic 13 (A-1301).

**NFR-1406 — Divergence Honesty**
Wherever the code is thinner than the E3–E6 vision, the documentation SHALL state so plainly (§12) rather than describing the aspirational feature as if it shipped.

**NFR-1407 — Roadmap Consistency After Reconciliation**
After the §7/§9 edits, both roadmap tables SHALL make it unambiguous that E3–E6 have shipped code (documented via this epic) and are no longer "📋 Planned," **without** deleting or renumbering the historical E1–E6 rows.

**NFR-1408 — Format Parity with Existing Epics**
This PRD SHALL follow the structure/depth of `epic-13-ai-provider-resilience.md`, and the companion doc SHALL follow the short-form style of `docs/stories/epic-10/EPIC-10-connector.md`, so the four agents read consistently alongside their documented siblings.

---

## 7. Constraints

**CON-1401 — Documentation Only; Zero Code Change (hard)**
This epic MUST NOT modify, refactor, extend, or "fix" any of the four agents' source, their tables, their tests, or the CLI. Its only file edits are the two new docs and the annotation of `docs/prd/product-roadmap.md`.

**CON-1402 — No Invention; Document Only What Exists**
Every documented capability MUST trace to read source. No E3–E6 vision feature that is absent from the code may be described as present. Divergences MUST be recorded as findings (§12), not silently "documented into existence."

**CON-1403 — No Story Files in This Epic**
This epic MUST NOT create `STORY-14.x` files. Story creation is @sm's separate responsibility (Delegation Matrix). This PRD defines the acceptance surface only.

**CON-1404 — Roadmap Reconciliation by Annotation Only**
The two E1–E6 roadmap tables MUST be reconciled by **adding** a status/real-epic annotation (extra column or inline note). Existing E1–E6 rows and their data MUST NOT be deleted or renumbered — they are historical vision-doc references.

**CON-1405 — Divergences Are Findings, Not a Work List**
The E3–E6 gaps in §12 MUST be framed as documentation findings for future prioritization. This epic MUST NOT schedule, promise, or begin any remediation of them.

**CON-1406 — Preserve Existing Numbering Convention**
FR/NFR/CON IDs MUST use the `14xx` band and remain consistent between this PRD and the companion doc, mirroring the convention of epics 10–13.

---

## 8. User Stories & Acceptance Criteria

> Story files (STORY-14.x) are created separately by @sm (CON-1403). The stories below define the acceptance surface for that work.

### US-14.1 — Closer As-Built PRD Section
**As** a future contributor, **I want** accurate documentation of the closer agent, **so that** I understand its notes→proposal→delivery pipeline without reading all five modules.
**Acceptance Criteria:**
- [ ] FR-1401–FR-1408 each name a real closer module/function and match its behavior.
- [ ] Pricing heuristic and its divergence from E3's discount-tier engine are documented (FR-1405).
- [ ] `discovery_calls`/`proposals` tables and the `draft→sent→accepted/rejected` + client `won/lost` transitions are documented.
- [ ] Claude model (`claude-3-5-sonnet-20241022`) and template fallbacks are recorded.

### US-14.2 — Conductor As-Built PRD Section
**As** a future contributor, **I want** the conductor's project/sprint/health/report model documented, **so that** I know it is internal SQLite, not an external PM tool.
**Acceptance Criteria:**
- [ ] FR-1411–FR-1419 trace to real conductor code.
- [ ] Health-score formula (100 base; −10/overdue, −20 budget, −15 stale) is documented exactly.
- [ ] Divergences (no Linear/Notion/ClickUp, no Toggl, >2-day blocker rule, Telegram not email) are recorded.
- [ ] `projects`/`sprints`/`project_tasks`/`project_updates` ownership is correct.

### US-14.3 — Treasurer As-Built PRD Section
**As** a future contributor, **I want** the billing agent documented, **so that** I know invoicing is manual + Telegram, not Stripe + email.
**Acceptance Criteria:**
- [ ] FR-1421–FR-1430 trace to real treasurer code.
- [ ] `EW-YYYY-NNN` numbering, tax math, and reminder escalation (3/7/14-day) are documented.
- [ ] The unused `due_today`/`final_notice` template gap is documented (FR-1428).
- [ ] Divergences (no Stripe, no email, no expense/P&L/tax export/retainer/MRR) are recorded.

### US-14.4 — Nurturer As-Built PRD Section
**As** a future contributor, **I want** the customer-success agent documented, **so that** I know its 4×25 health model, onboarding, check-ins, and upsell detection.
**Acceptance Criteria:**
- [ ] FR-1431–FR-1438 trace to real nurturer code.
- [ ] The four 25-pt components and their thresholds are documented (FR-1432).
- [ ] Additions vs. E6 (7-step onboarding) and divergences (no renewals/KB/referrals/anniversary/LTV, keyword sentiment, <60 threshold) are recorded.
- [ ] `onboarding_checklists`/`client_health_scores`/`upsell_opportunities`/`client_checkins` ownership is correct.

### US-14.5 — Companion Short-Form Epic Doc
**As** the SM, **I want** a short-form epic doc mirroring the FR/NFR/CON IDs, **so that** I can draft stories from a concise index.
**Acceptance Criteria:**
- [ ] `docs/stories/epic-14/EPIC-14-documentation-backfill.md` exists with the same FR/NFR/CON IDs, grouped per agent.
- [ ] It follows the short-form style of `docs/stories/epic-10/EPIC-10-connector.md`.

### US-14.6 — Roadmap Table Reconciliation (Article-IV fix)
**As** a roadmap reader, **I want** the two stale E1–E6 tables annotated with real status, **so that** I'm not misled into thinking E3–E6 are unbuilt.
**Acceptance Criteria:**
- [ ] Both the top "Roadmap Summary" and bottom "Cumulative Story Estimates" tables carry a real-epic/status annotation for E1–E6.
- [ ] E1→epic-1 (documented, in development); E2→shipped as **publisher**, documented across epic-7/8/9 (not epic-2); E3→**closer** (shipped, documented via Epic 14); E4→**conductor** (shipped, Epic 14); E5→**treasurer** (shipped, Epic 14); E6→**nurturer** (shipped, Epic 14).
- [ ] No E1–E6 row is deleted or renumbered; existing data preserved (CON-1404).

---

## 9. Out of Scope (Epic 14)

- **Any code change to the four agents** — behavior, refactors, bug fixes, model unification, new features (CON-1401). The unused `due_today`/`final_notice` treasurer templates and the inconsistent model IDs are **documented**, not fixed.
- **Closing the E3–E6 vision gaps** — web/company research, service-package matcher, case-study library, external PM tools, Toggl, Stripe, email delivery, expense/P&L/tax export, retainers/MRR, renewals, client knowledge base/`/client` query, testimonials, referrals, anniversary alerts, LTV dashboard, Typeform NPS, AI intervention talking points. All are **findings** (§12), not work here (CON-1405).
- **Story files (STORY-14.x)** — @sm's separate task (CON-1403).
- **Migrating the four agents' `import anthropic` call sites** — that is Epic 13's future scope, not this epic.
- **Documenting prospector, publisher, or connector** — already documented (epic-1, epic-7…epic-10).
- **Renumbering or deleting the historical E1–E6 roadmap rows** — annotation only (CON-1404).
- **PostgreSQL / Docker-per-agent reconciliation** — the roadmap's "Platform Architecture Principles" describe Postgres + Docker containers; the code uses SQLite and no per-agent containers. This epic may *note* the discrepancy in §12 but MUST NOT alter architecture docs beyond the two required tables.

---

## 10. Dependencies

| ID | Dependency | Type | Owner | Required By |
|----|-----------|------|-------|-------------|
| DEP-1401 | Source under `eworks/agents/closer|conductor|treasurer|nurturer/` (read-only) | Internal | Engineering | Every FR |
| DEP-1402 | `eworks/core/database.py` schema (15 tables) | Internal | Engineering | NFR-1403 data-model docs |
| DEP-1403 | `eworks/cli/main.py` command wiring | Internal | Engineering | As-built trigger narrative |
| DEP-1404 | `docs/prd/epic-13-ai-provider-resilience.md` (format + A-1301 cross-ref) | Internal | Morgan | Format parity, AI-usage docs |
| DEP-1405 | `docs/stories/epic-10/EPIC-10-connector.md` (short-form template) | Internal | Morgan | Companion doc |
| DEP-1406 | `docs/prd/product-roadmap.md` E3–E6 sections + two stale tables | Internal | Morgan | §12 divergence + reconciliation |
| DEP-1407 | `git log` for the four agent dirs (chronology / feature names) | Internal | Engineering | As-built narrative (A-1401) |
| DEP-1408 | @sm availability to later draft STORY-14.x | Internal | River | Post-epic story creation |

---

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R-1401 | Documentation drifts from code if agents change after write | Medium | Medium | FRs cite exact modules/functions (NFR-1401); re-verify on any future agent change |
| R-1402 | Reader mistakes documented E3–E6 gaps as a committed backlog | Medium | Medium | CON-1405 + §12 framing: findings, not a work list |
| R-1403 | Roadmap edit accidentally deletes/renumbers historical rows | Low | Medium | CON-1404: annotation only; preserve existing data |
| R-1404 | An FR describes an aspirational feature not in code (invention) | Low | High | CON-1402 + NFR-1401; every FR traced to read source |
| R-1405 | The two Claude model IDs are "corrected" during doc work (scope creep into code) | Low | High | CON-1401: document the inconsistency, never change it |
| R-1406 | Table-ownership errors (wrong agent credited) | Low | Medium | NFR-1403 explicit ownership map from `database.py` |
| R-1407 | Divergence list read as criticism of shipped work rather than a neutral gap record | Low | Low | §2/§12 frame divergence as a valuable baseline finding |

---

## 12. Roadmap Divergence Findings

> Neutral, as-built findings: **intended** (E3–E6 roadmap) vs. **shipped** (real code). These are documentation outputs for future prioritization, not defects or a work list (CON-1405). A recurring, cross-cutting divergence: the roadmap's "Platform Architecture Principles" promise **PostgreSQL**, **email**, and **Docker-per-agent**; the shipped code uses **SQLite** (`eworks/core/database.py`), **Telegram-only** delivery, and no per-agent containers.

### E3 → Closer
| E3 intended | As-built in `closer/` |
|-------------|-----------------------|
| Pull prospect/company context from E1 DB; enrich via web search (Perplexity/Serper/Tavily) | **None.** Starts from raw discovery-call **notes** passed to `run_from_notes`; no web/company research. |
| Service-package matcher; case-study library auto-select | **Absent.** No package matcher, no case-study library. |
| Pricing engine with discount tiers | Flat heuristic: `$150/h` default, `40 + 8*(i%3)` hours, `Σ`. No tiers/discounts (FR-1405). |
| Branded PDF **and** email to prospect; follow-up via E1 | PDF/txt to `data/proposals/`; **Telegram-only** delivery; no email; no follow-up scheduling. |
| ~25 stories / ~100 pts of capability | 5 modules: discovery extract, proposal draft, export, deliver, status tracking. |

### E4 → Conductor
| E4 intended | As-built in `conductor/` |
|-------------|--------------------------|
| Integrate external PM tool (Linear/Notion/ClickUp) + task templates | **Internal SQLite** `projects`/`sprints`/`project_tasks` with a 5-column kanban; no external tool, no template library. |
| Toggl (or similar) time tracking | Manual `log_hours` only (FR-1414). |
| Milestone tracking; deliverable review queue; retrospectives + KB; capacity planning | **None** shipped. |
| Blocker = overdue >1 day; client status via email | Blocker = `in_progress` overdue **>2 days**; Telegram delivery (FR-1418). |
| Weekly client update email (Claude-drafted, Cesar-approved) | Claude weekly report saved to `project_updates`, sent via Telegram; no approval gate. |

### E5 → Treasurer
| E5 intended | As-built in `treasurer/` |
|-------------|--------------------------|
| Stripe/recurring + processor integration | **None.** `record_payment` is manual entry (FR-1425). |
| Email invoices with Claude cover note | Markdown/PDF to `data/invoices/`; **Telegram-only**; no email; no Claude cover note. |
| Expense tracking; profitability/P&L; tax export (BR); retainer mgmt; MRR | **All absent.** Revenue summary is invoiced/paid/overdue + collection rate (FR-1427). |
| Reminder cadence: 3d-before / day-of / 3d / 7d overdue | Shipped: `upcoming` (0–3d), `overdue_3d/7d/14d`. `due_today` + `final_notice` templates exist but are **never dispatched** (FR-1428/1429). |

### E6 → Nurturer
| E6 intended | As-built in `nurturer/` |
|-------------|-------------------------|
| Health from 5 signals; alert below threshold (<40 metric) | **4×25** components (payment/engagement/project/satisfaction); at-risk **<60** (FR-1431/1433). |
| NPS via Typeform; AI sentiment | NPS captured **manually** via `record_response`; **keyword** sentiment (FR-1436). |
| Renewal mgmt; client KB + `/client` query; testimonials; referrals; anniversary; LTV dashboard; AI intervention talking points | **None** shipped (client KB/query is Epic 12/gbrain territory). At-risk alert is a generic Telegram message. |
| (Not in E6 vision) | **7-step onboarding checklist** (`onboarding.py`) is a shipped **addition** beyond E6 (FR-1434). |

---

## 13. Glossary

| Term | Definition |
|------|-----------|
| **As-built documentation** | Documentation written after the fact to describe what code actually does, vs. forward-looking requirements |
| **closer** | The proposal-generation agent (`eworks/agents/closer/`); roadmap origin E3 |
| **conductor** | The project-management agent (`eworks/agents/conductor/`); roadmap origin E4 |
| **treasurer** | The invoice & billing agent (`eworks/agents/treasurer/`); roadmap origin E5 |
| **nurturer** | The customer-success agent (`eworks/agents/nurturer/`); roadmap origin E6 |
| **Divergence finding** | A documented gap between E3–E6 intended features and shipped code (§12); a finding, not a defect or task |
| **TelegramReporter** | Shared delivery client (`prospector/reporter.py`) reused by all four agents; the sole delivery channel |
| **Health score (conductor)** | 0–100 project score: base 100, −10/overdue task, −20 budget overrun, −15 no 7-day activity |
| **Health score (nurturer)** | 0–100 client score = sum of four 25-pt components (payment, engagement, project, satisfaction) |
| **`EW-YYYY-NNN`** | Treasurer's sequential invoice-number format |
| **Graceful fallback** | Deterministic non-AI path (template proposal/report/message, default upsell, `.txt` export) used when Claude/PDF libs are unavailable |
| **Roadmap reconciliation** | Annotating the two stale E1–E6 tables in `product-roadmap.md` so shipped agents are not shown as "📋 Planned" (this epic's Article-IV fix) |
| **Eworks OS** | The multi-agent company operating system these four agents are part of |
