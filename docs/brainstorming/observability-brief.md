# Observability Brainstorming Brief

**Project:** Eworks OS AI Observability Platform  
**Date:** May 22, 2026  
**Author:** AIOX @analyst Agent  
**Status:** Batch 1 — Planning & Governance  

---

## Vision

Eworks OS observability provides real-time insight into agent execution, LLM interactions, and business outcomes. By instrumenting all seven agents (Prospector, Publisher, Closer, Conductor, Treasurer, Nurturer, Connector) with distributed tracing via Phoenix, Eworks OS transforms raw telemetry into actionable intelligence for founders, operators, and engineers.

**Core Insight:** Without observability, agents are black boxes. With it, we see **every decision, every API call, every failure — in real-time.**

---

## Strategic Goals

### 1. Real-Time Agent Health Monitoring
- **What:** Detect agent failures, performance degradation, and anomalies in < 1 second
- **Why:** Cesar needs to know "Is my agent working?" without waiting for daily reports
- **Metric:** Alert latency < 100ms; detection accuracy > 95%

### 2. Cost Tracking & Optimization
- **What:** Track LLM token consumption, API call volumes, and cost per agent
- **Why:** LLM costs are the primary expense; need visibility to optimize prompts and batch sizes
- **Metric:** Cost attribution per agent; identify > 10% waste opportunities within 24 hours

### 3. Error Detection & Root Cause Analysis
- **What:** Capture stack traces, error rates, and failure patterns across all agents
- **Why:** Debug issues faster; reduce MTTR (mean time to recovery) by 50%
- **Metric:** Root cause identifiable within 5 minutes of error detection

### 4. Performance Optimization
- **What:** Measure latency, throughput, and bottlenecks per agent and per method
- **Why:** Identify slow steps (e.g., LLM inference, API calls) and optimize (parallelization, caching, model selection)
- **Metric:** p95 latency < 30s for all agent methods; identify optimization targets

### 5. Business Outcome Tracking
- **What:** Correlate agent activity with business metrics (campaigns sent, proposals generated, deals closed)
- **Why:** Understand ROI of each agent; validate product-market fit
- **Metric:** End-to-end latency from user request to business outcome; conversion rate per agent

---

## User Personas

### Persona 1: Cesar (Founder/CEO)
**Goal:** "Is my agent working? How many leads did Prospector send today? Are we on track?"

**Pain Points:**
- No visibility into agent behavior between daily reports
- Can't debug why agents sometimes fail
- Doesn't know which agents are ROI-positive

**Observability Needs:**
- Dashboard: Agent status (healthy/degraded/failed), daily metrics (campaigns sent, proposals, deals)
- Alerting: Notify when agent fails or response rate < 5%
- Reports: Weekly cost breakdown, ROI per agent

---

### Persona 2: QA Engineer / DevOps
**Goal:** "Did the instrumentation break? Are spans being collected? Is the trace quality acceptable?"

**Pain Points:**
- Can't validate that decorators are still working post-deployment
- No automated tests for instrumentation layer
- Manual dashboard checks are tedious and error-prone

**Observability Needs:**
- CI/CD: GitHub Actions to validate spans in test suite on every PR
- Dashboards: Instrumentation health (span count per agent, delivery rate, latency)
- Alerting: Alert if span count drops > 50% (possible decorator failure)

---

### Persona 3: Ops / Performance Engineer
**Goal:** "Which agent consumes the most tokens? Where's the latency bottleneck? Can we optimize?"

**Pain Points:**
- No breakdown of LLM token usage by model, agent, method
- Can't identify slow API calls or inefficient prompts
- Can't correlate agent latency with external factors (API availability, network)

**Observability Needs:**
- Dashboards: Token consumption heatmap, latency percentiles per method, API call breakdown
- Queries: "Which agents use GPT-4? What's the cost delta vs. Sonnet?"
- Trends: Week-over-week cost/latency graphs, anomaly detection

---

## Metrics per Agent

### **Prospector Agent**
**Role:** Finds leads, sends connection requests, tracks responses

**Metrics:**
- `campaigns_sent` (counter) — Total campaigns launched
- `prospects_added` (counter) — Total LinkedIn prospects added to workspace
- `connection_requests_sent` (counter) — Total connection requests sent
- `connection_response_rate` (gauge %) — % of requests that received responses
- `avg_message_tokens` (histogram) — Average tokens per outreach message
- `campaign_latency_p95` (histogram, seconds) — 95th percentile time to complete a campaign
- `error_rate` (gauge %) — % of campaigns that failed
- `cost_per_campaign` (gauge $) — Estimated LLM cost per campaign

**Span Attributes:**
- `agent: "prospector"`
- `method: "run_campaign" | "send_connection" | "track_response"`
- `campaign_id, prospect_count, error (if failed)`
- `tokens_used, latency_ms`

---

### **Publisher Agent**
**Role:** Generates content ideas, creates posts, schedules publication

**Metrics:**
- `content_ideas_generated` (counter) — Total ideas created
- `posts_created` (counter) — Total posts finalized
- `posts_scheduled` (counter) — Total posts scheduled to social platforms
- `content_pipeline_latency_p95` (histogram, seconds) — 95th percentile time from idea to published
- `avg_idea_tokens` (histogram) — Average tokens per generated idea
- `generation_quality_score` (gauge 0-100) — Estimated quality of ideas (via LLM evaluation)
- `error_rate` (gauge %) — % of content creation failures
- `cost_per_idea` (gauge $) — Estimated LLM cost per idea

**Span Attributes:**
- `agent: "publisher"`
- `method: "generate_ideas" | "create_post" | "schedule"`
- `content_id, platform, idea_count`
- `tokens_used, latency_ms`

---

### **Closer Agent**
**Role:** Identifies deal opportunities, generates proposals, tracks engagement

**Metrics:**
- `opportunities_identified` (counter) — Total deal opportunities flagged
- `proposals_generated` (counter) — Total proposals created
- `proposals_sent` (counter) — Total proposals delivered to prospects
- `proposal_acceptance_rate` (gauge %) — % of sent proposals that received positive response
- `avg_proposal_tokens` (histogram) — Average tokens per proposal
- `discovery_latency_p95` (histogram, seconds) — 95th percentile time to complete discovery
- `error_rate` (gauge %) — % of proposal generation failures
- `cost_per_proposal` (gauge $) — Estimated LLM cost per proposal

**Span Attributes:**
- `agent: "closer"`
- `method: "discover_opportunities" | "generate_proposal" | "send_proposal"`
- `opportunity_id, prospect_id, proposal_status`
- `tokens_used, latency_ms`

---

### **Conductor Agent**
**Role:** Orchestrates multi-agent workflows, tracks overall progress, generates reports

**Metrics:**
- `workflows_started` (counter) — Total workflows initiated
- `workflows_completed` (counter) — Total workflows that finished successfully
- `workflow_success_rate` (gauge %) — % of workflows completed without error
- `workflow_latency_p95` (histogram, seconds) — 95th percentile end-to-end workflow time
- `daily_check_count` (counter) — Total daily status checks performed
- `status_report_tokens` (histogram) — Average tokens per status report
- `error_rate` (gauge %) — % of workflow failures
- `cost_per_workflow` (gauge $) — Estimated LLM cost per workflow

**Span Attributes:**
- `agent: "conductor"`
- `method: "run" | "run_daily_check" | "generate_report"`
- `workflow_id, step_count, status`
- `tokens_used, latency_ms`

---

### **Treasurer Agent**
**Role:** Tracks spending, generates financial reports, alerts on budget thresholds

**Metrics:**
- `transactions_processed` (counter) — Total financial transactions tracked
- `reports_generated` (counter) — Total financial reports created
- `budget_alerts_sent` (counter) — Total alerts for budget overages
- `report_latency_p95` (histogram, seconds) — 95th percentile time to generate financial report
- `avg_report_tokens` (histogram) — Average tokens per report
- `error_rate` (gauge %) — % of transaction processing failures
- `cost_per_report` (gauge $) — Estimated LLM cost per report

**Span Attributes:**
- `agent: "treasurer"`
- `method: "process_transaction" | "generate_report" | "check_budget"`
- `transaction_id, report_type, amount`
- `tokens_used, latency_ms`

---

### **Nurturer Agent**
**Role:** Maintains relationships with prospects, sends follow-ups, tracks engagement sentiment

**Metrics:**
- `follow_ups_sent` (counter) — Total follow-up messages sent
- `engagement_score_updates` (counter) — Total prospect engagement scores updated
- `sentiment_evaluations` (counter) — Total sentiment analyses performed
- `nurture_latency_p95` (histogram, seconds) — 95th percentile time to complete nurture cycle
- `avg_followup_tokens` (histogram) — Average tokens per follow-up message
- `engagement_improvement_rate` (gauge %) — % of prospects with improved engagement scores
- `error_rate` (gauge %) — % of follow-up delivery failures
- `cost_per_followup` (gauge $) — Estimated LLM cost per follow-up

**Span Attributes:**
- `agent: "nurturer"`
- `method: "send_followup" | "evaluate_sentiment" | "update_score"`
- `prospect_id, message_type, sentiment_score`
- `tokens_used, latency_ms`

---

### **Connector Agent**
**Role:** Manages multi-platform integrations, listens for inbound messages, routes responses

**Metrics:**
- `messages_received` (counter) — Total inbound messages processed
- `message_routes_processed` (counter) — Total routing decisions made
- `platform_integrations_active` (gauge) — Number of active platform connections
- `message_processing_latency_p95` (histogram, seconds) — 95th percentile time to process & route message
- `route_accuracy` (gauge %) — % of messages routed to correct agent
- `integration_uptime` (gauge %) — % of time all platform integrations were healthy
- `error_rate` (gauge %) — % of message processing failures
- `cost_per_message` (gauge $) — Estimated cost per routed message (if LLM used)

**Span Attributes:**
- `agent: "connector"`
- `method: "listen" | "process_message" | "route_message"`
- `platform, message_id, source_platform, target_agent`
- `latency_ms, error (if failed)`

---

## Cross-Agent Metrics

### System-Level Metrics
- `total_daily_spans` (counter) — Total spans collected daily
- `span_delivery_rate` (gauge %) — % of spans successfully delivered to Phoenix
- `span_processing_latency_p99` (histogram, ms) — 99th percentile time to log a span
- `total_daily_tokens` (counter) — Total LLM tokens consumed across all agents
- `total_daily_cost` (gauge $) — Estimated total LLM cost
- `instrumentation_coverage` (gauge %) — % of agent methods traced
- `test_pass_rate` (gauge %) — % of automated tests passing

---

## Success Criteria

### Coverage Criteria
- ✅ **100% of agent methods traced** — All 7 agents, all orchestrator + executor methods have @trace_agent_execution or @trace_llm_call decorators
- ✅ **100% of LLM calls traced** — All client.messages.create() calls wrapped with @trace_llm_call
- ✅ **100% of tool calls traced** — All external API/DB/file operations have @trace_tool_call decorators
- ✅ **100% test coverage for instrumentation** — All decorators have unit tests verifying they fire correctly

### Quality Criteria
- ✅ **Span latency < 10ms** — No decorator adds > 10ms overhead per call
- ✅ **Span delivery rate > 99.9%** — Of all spans created, > 99.9% reach Phoenix within 5 seconds
- ✅ **Span schema consistency** — All spans have required attributes (agent, method, timestamp); optional attributes present > 95% of the time
- ✅ **Dashboard accuracy** — Dashboard queries return data within 10 seconds; metric calculations match source traces

### Cost Criteria
- ✅ **Instrumentation cost < $500/month** — Phoenix span ingestion + storage cost < $500/month (assuming 1M+ spans/day)
- ✅ **No overhead to agent execution** — Agent output latency unchanged (< 5% variance)

### Operational Criteria
- ✅ **CI/CD validation** — GitHub Actions validates spans on every PR; fails if span quality degraded
- ✅ **Dashboard deployed & accessible** — Phoenix dashboard accessible to Cesar, QA, Ops with proper access controls
- ✅ **Alerting functional** — At least 5 alerts configured (agent failure, high error rate, high latency, cost overrun, span delivery failure)
- ✅ **Runbooks documented** — At least 3 runbooks: "Debug high latency", "Investigate failed span delivery", "Reduce LLM costs"

---

## Scope & Constraints

### In Scope
- ✅ Distributed tracing for all 7 agents (Prospector, Publisher, Closer, Conductor, Treasurer, Nurturer, Connector)
- ✅ Phoenix integration (span collection + storage)
- ✅ Real-time dashboard with 4+ tabs (Overview, Performance, Cost, Errors)
- ✅ Automated alerting (Slack/Telegram notifications)
- ✅ Evaluation framework (metrics definition, SLOs, quality rules)
- ✅ CI/CD integration (span validation on every PR)
- ✅ Test coverage for instrumentation layer

### Out of Scope
- ❌ Tracing for utility functions (helpers, validators) — only agent-level and LLM-level tracing
- ❌ Custom APM solution — use Phoenix as primary observability backend
- ❌ Real-time alerting for non-critical events (logs via stdout OK; alerts only for failures/anomalies)
- ❌ Historical analysis (trend analysis starts from deployment date; no backfill of old logs)
- ❌ Cost optimization recommendations — dashboard shows costs; optimization is manual decision

### Constraints
- **Python version:** Python 3.12+ required (for async decorator compatibility)
- **Phoenix version:** Phoenix v16.0+ required (for latest API features)
- **No breaking changes:** All instrumentation must not change agent method signatures or outputs
- **Backward compatibility:** Must work with existing agent codebases without refactoring

---

## Dependencies & Risks

### Dependencies
- ✅ **Phoenix API key** — PHOENIX_API_KEY env var must be set in production
- ✅ **Network connectivity** — Agents must have outbound HTTPS access to Phoenix servers
- ✅ **Async support** — Decorators must handle both `async def` and `def` methods

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Span overhead exceeds 10ms | Medium | Agent latency increases 10-50% | Profile decorators in isolated test; optimize hotpaths |
| Phoenix API key invalid at startup | Low | Tracing silently fails | Validate key during CLI init; log warnings to stderr |
| Decorator placement conflicts with @click decorators | Medium | Instrumentation doesn't work | Place custom decorators **after** Click decorators (documented in pitfalls) |
| Span delivery fails (network issue) | Low | Metrics become unavailable | Implement retry logic + local fallback logging |
| Test coverage for decorators is incomplete | Medium | Instrumentation drifts post-deployment | Add tests in Batch 2; CI/CD validates spans on every PR |

---

## Next Steps (Batch 2-5)

### Phase 1: Planning (Batch 1 — Now)
- ✅ **This document:** Observability brainstorming brief (defines goals, metrics, personas, success criteria)
- **Next:** @pm creates PRD, @architect creates architecture doc

### Phase 2: Story Drafting (Batch 2)
- @sm drafts STORY-2.1, STORY-2.2, STORY-2.3 for Prospector, Publisher, Closer instrumentation
- Parallel implementation by Sonnet-A, Sonnet-B, Sonnet-C

### Phase 3: Agent Instrumentation A (Batch 2 — Days 1-2)
- Instrument Prospector, Publisher, Closer in parallel
- Expected: ~2 days, 100% coverage

### Phase 4: Agent Instrumentation B + Dashboard (Batch 3 — Days 3-4)
- Instrument Conductor, Treasurer, Nurturer in parallel
- Architect designs dashboard layout in parallel
- Expected: ~2 days

### Phase 5: Connector + Evaluation (Batch 4 — Days 5-6)
- Instrument Connector (complex async listeners)
- Create evaluation framework (metrics, SLOs, alert rules)
- Expected: ~2 days

### Phase 6: QA & CI/CD (Batch 5 — Day 7)
- QA validates all spans against schema
- DevOps deploys dashboards + GitHub Actions
- Expected: ~1 day

### Phase 7: Launch & Monitor (Post-Batch 5)
- Deploy to production
- Monitor span delivery, dashboard health, alerting
- Iterate on metrics based on feedback

---

## Estimated Timeline

| Batch | Activity | Duration | Parallelism | Status |
|-------|----------|----------|-------------|--------|
| **1** | Planning + Governance | 1 day | Sequential (@analyst, @pm, @architect) | **IN PROGRESS** |
| **2** | Agent Instrumentation A (3 agents) | 2 days | 3-way parallel (Sonnet-A/B/C) | Pending Batch 1 |
| **3** | Agent Instrumentation B + Dashboard | 2 days | 3-way parallel (Sonnet-D/E + Architect) | Pending Batch 2 |
| **4** | Connector + Evaluation Framework | 2 days | 2-way parallel (Sonnet-F + Architect) | Pending Batch 3 |
| **5** | QA + CI/CD + Deploy | 1 day | Sequential (@qa, @devops) | Pending Batch 4 |
| **TOTAL** | Full Integration | **~8 days** | High | Ready for start |

---

## Glossary

- **Span:** A unit of work in distributed tracing (e.g., "run_campaign for campaign_id=123")
- **Trace:** A collection of spans representing a single user request end-to-end
- **Phoenix:** AI observability platform (AI4's observability backend; primary system for this project)
- **Decorator:** Python function wrapper (@trace_agent_execution, @trace_llm_call) that automatically logs spans
- **Attribute:** Metadata attached to a span (e.g., agent="prospector", method="run_campaign")
- **SLO:** Service Level Objective (e.g., "p95 latency < 30s")
- **MTTR:** Mean Time To Recovery (how long it takes to detect and fix an issue)
- **LLM:** Large Language Model (Claude, GPT-4, etc.)

---

## Approval & Sign-Off

- [ ] @analyst: Approved brainstorming brief
- [ ] @pm: Ready to create PRD based on goals + personas
- [ ] @architect: Ready to create architecture doc based on metrics + success criteria
- [ ] Cesar (CEO): Confirmed observability goals align with business objectives

---

**Document Version:** 1.0  
**Last Updated:** May 22, 2026  
**Next Review:** Upon PRD completion (Batch 1 Stage 2)
