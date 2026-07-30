# Epic: OBSERVABILITY — AI Observability Platform

**Epic ID:** OBSERVABILITY  
**Status:** Batch 1 — Planning & Governance  
**Date:** May 22, 2026  
**Product Manager:** AIOX @pm Agent  
**Project:** Eworks OS AI Observability Integration  

---

## Executive Summary

The Eworks OS AI Observability Platform enables real-time distributed tracing of all seven agents (Prospector, Publisher, Closer, Conductor, Treasurer, Nurturer, Connector) using Arize Phoenix. This PRD defines comprehensive functional and non-functional requirements, constraints, user stories, and acceptance criteria to deliver production-ready observability across the system.

**Strategic Vision:** Transform agents from black boxes into glass boxes — every decision, every API call, every failure visible in real-time.

**Success Definition:** 100% agent instrumentation, < 10ms span latency, 99.9% span delivery, < $500/month cost, CI/CD validation, and production dashboard.

---

## Part 1: Functional Requirements (FR-OBS-001 through FR-OBS-030)

### 1.1 Agent Execution Tracing (FR-OBS-001 through FR-OBS-008)

#### FR-OBS-001: Trace All Prospector Agent Methods
- **Description:** Instrument all methods in Prospector (`orchestrator.py`, `executor.py`, `generator.py`) with @trace_agent_execution decorator
- **Scope:** run_campaign, run, generate, send_connection, track_response, _process_response
- **Expected Outcome:** Every Prospector method execution creates a Phoenix span with agent="prospector", method=<method_name>, and timing attributes
- **Acceptance:** Verified by grep for @trace_agent_execution + unit tests

#### FR-OBS-002: Trace All Publisher Agent Methods
- **Description:** Instrument all methods in Publisher (`orchestrator.py`, `social_orchestrator.py`) with @trace_agent_execution decorator
- **Scope:** run, generate_ideas, create_post, schedule, _validate_content, _publish_to_platforms
- **Expected Outcome:** Every Publisher method execution creates a Phoenix span with agent="publisher", method=<method_name>, timing, and token attributes
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-003: Trace All Closer Agent Methods
- **Description:** Instrument all methods in Closer (`orchestrator.py`, `discovery_processor.py`, `proposal_generator.py`)
- **Scope:** run, discover_opportunities, generate_proposal, send_proposal, _find_or_create_client, _evaluate_fit
- **Expected Outcome:** All Closer methods traced with agent="closer", relevant business attributes (opportunity_id, proposal_status)
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-004: Trace All Conductor Agent Methods
- **Description:** Instrument all methods in Conductor (`orchestrator.py`, `tracker.py`, `status_reporter.py`)
- **Scope:** run, run_daily_check, generate_report, _track_workflow, _delegate_task
- **Expected Outcome:** All Conductor methods traced with agent="conductor", workflow tracking attributes
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-005: Trace All Treasurer Agent Methods
- **Description:** Instrument all methods in Treasurer (`orchestrator.py`, financial modules)
- **Scope:** process_transaction, generate_report, check_budget, _calculate_totals, _alert_on_threshold
- **Expected Outcome:** All Treasurer methods traced with agent="treasurer", financial data attributes
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-006: Trace All Nurturer Agent Methods
- **Description:** Instrument all methods in Nurturer (`orchestrator.py`, engagement modules)
- **Scope:** send_followup, evaluate_sentiment, update_score, _select_next_action, _compose_message
- **Expected Outcome:** All Nurturer methods traced with agent="nurturer", engagement attributes
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-007: Trace All Connector Agent Methods
- **Description:** Instrument all methods in Connector (`orchestrator.py`, `listener.py`, `reply_generator.py`)
- **Scope:** listen, process_message, route_message, _detect_reply, _generate_response, _route_to_agent
- **Expected Outcome:** All Connector methods traced with agent="connector", platform/message routing attributes
- **Acceptance:** Verified by grep + unit tests

#### FR-OBS-008: Support Async/Sync Method Tracing
- **Description:** Decorator must auto-detect and properly trace both `async def` and `def` methods without breaking execution
- **Scope:** All agent methods (some async, some sync)
- **Expected Outcome:** Decorator works seamlessly for both async and sync methods; no execution errors
- **Acceptance:** Unit tests for both async and sync variants pass

---

### 1.2 LLM & Tool Call Tracing (FR-OBS-009 through FR-OBS-015)

#### FR-OBS-009: Trace All LLM API Calls
- **Description:** Wrap all `client.messages.create()` calls with @trace_llm_call decorator
- **Scope:** All agents calling Claude/GPT/other LLMs
- **Expected Outcome:** Every LLM call creates a span with model, prompt_tokens, completion_tokens, latency, operation attributes
- **Acceptance:** 100% of LLM calls in codebase wrapped; spans include token counts and model name

#### FR-OBS-010: Capture LLM Token Consumption
- **Description:** Decorator captures input/output token counts from LLM responses
- **Scope:** All LLM calls (Claude, GPT-4, Sonnet models)
- **Expected Outcome:** Span attributes include `tokens_used`, `input_tokens`, `output_tokens`, `cost_estimate`
- **Acceptance:** Token counts present in 95%+ of LLM spans (account for API responses that don't include token data)

#### FR-OBS-011: Trace Database Queries
- **Description:** Instrument all database operations (SELECT, INSERT, UPDATE, DELETE) with @trace_tool_call decorator
- **Scope:** All agent database interactions
- **Expected Outcome:** Each query creates a span with query_type, table, row_count, latency attributes
- **Acceptance:** Database operations traceable in Phoenix dashboard

#### FR-OBS-012: Trace External API Calls
- **Description:** Instrument all external API calls (LinkedIn, Twitter, email, etc.) with @trace_tool_call decorator
- **Scope:** Prospector (LinkedIn), Publisher (Twitter/Facebook), Connector (multi-platform), others as needed
- **Expected Outcome:** API calls traced with endpoint, http_status, latency, response_size attributes
- **Acceptance:** External API failures visible in Phoenix with status codes and error messages

#### FR-OBS-013: Trace File Operations
- **Description:** Instrument file read/write operations with @trace_tool_call decorator
- **Scope:** Any agent reading/writing files (reports, exports, configs)
- **Expected Outcome:** File operations traced with filename, operation (read/write), file_size, latency attributes
- **Acceptance:** File operations visible in performance dashboards

#### FR-OBS-014: Capture Error Context
- **Description:** When exceptions occur in traced methods, capture stack trace, error message, and error type as span attributes
- **Scope:** All traced methods (agent, LLM, tool calls)
- **Expected Outcome:** Span attributes include error=<message>, error_type=<exception_type>, stack_trace=<truncated>
- **Acceptance:** Errors traceable and root-causable from Phoenix dashboard

#### FR-OBS-015: Trace Workflow Steps
- **Description:** For multi-step workflows (e.g., Conductor orchestration), create separate spans per workflow step
- **Scope:** Conductor agent's workflow execution
- **Expected Outcome:** Workflow execution shows step-by-step breakdown with step names, status (running/completed/failed), latency per step
- **Acceptance:** Conductor workflows show complete step-by-step breakdown in dashboard

---

### 1.3 Observability Infrastructure (FR-OBS-016 through FR-OBS-022)

#### FR-OBS-016: Phoenix Integration Setup
- **Description:** Initialize Phoenix client on Eworks OS startup; validate API key; handle connection failures gracefully
- **Scope:** `eworks/cli/main.py`, environment configuration
- **Expected Outcome:** Phoenix client initialized at startup; warnings logged if key invalid; tracing degrades gracefully (doesn't crash agents)
- **Acceptance:** Startup logs confirm Phoenix connected; agents work even if Phoenix unreachable

#### FR-OBS-017: Span Schema Consistency
- **Description:** Define and enforce a consistent span schema (required attributes: agent, method, timestamp; optional: inputs, outputs, tokens, latency)
- **Scope:** All spans across all agents
- **Expected Outcome:** All spans follow schema defined in architecture doc; schema validation in tests
- **Acceptance:** Architecture doc defines schema; schema validation passes for 100% of test spans

#### FR-OBS-018: Real-Time Dashboard
- **Description:** Create Phoenix dashboard with 4+ tabs (Overview, Performance, Cost, Errors) accessible to users
- **Scope:** All agent metrics, real-time data, customizable queries
- **Expected Outcome:** Dashboard deployed to Phoenix UI; shows agent status, latency graphs, cost breakdown, error heatmaps
- **Acceptance:** Dashboard accessible via Phoenix link; queries return data within 10s; metrics accurate

#### FR-OBS-019: Alerting & Notification System
- **Description:** Configure automated alerts for critical conditions (agent failure, high error rate, high latency, cost overrun, span delivery failure)
- **Scope:** At least 5 alert rules, Slack/Telegram notification channels
- **Expected Outcome:** Alerts fire when thresholds crossed; notifications delivered to ops/founders
- **Acceptance:** 5+ alert rules configured; test alert fires correctly; logs confirm delivery

#### FR-OBS-020: Evaluation Metrics Definition
- **Description:** Define per-agent metrics (counters, gauges, histograms) per observability-brief.md
- **Scope:** Prospector, Publisher, Closer, Conductor, Treasurer, Nurturer, Connector + system-level metrics
- **Expected Outcome:** Metrics document defines ~40-50 metrics with SLO targets; dashboards can compute metrics from spans
- **Acceptance:** Metrics doc complete; dashboards display all metrics; manual validation of 3+ key metrics

#### FR-OBS-021: CI/CD Span Validation
- **Description:** Add GitHub Actions workflow to validate spans in test suite on every PR
- **Scope:** `.github/workflows/validate-spans.yml`
- **Expected Outcome:** PR tests include span collection; workflow validates span quality and schema; fails if critical attributes missing
- **Acceptance:** Workflow exists and runs on every PR; enforces span quality gate

#### FR-OBS-022: Cost Tracking & Budgeting
- **Description:** Track estimated Phoenix costs (span ingestion + storage); alert if monthly cost exceeds $500
- **Scope:** Daily cost calculation, cost per agent breakdown
- **Expected Outcome:** Dashboard shows estimated daily/monthly costs; alerts fire if cost > $500/month
- **Acceptance:** Cost metrics visible in dashboard; validation against actual Phoenix billing

---

### 1.4 Documentation & Operations (FR-OBS-023 through FR-OBS-030)

#### FR-OBS-023: Instrumentation Framework Documentation
- **Description:** Document decorator usage, pitfalls, and best practices in `docs/instrumentation-guide.md`
- **Scope:** How to use @trace_agent_execution, @trace_llm_call, @trace_tool_call; decorator ordering with Click; async/sync handling
- **Expected Outcome:** Developers can instrument new agents/methods without assistance
- **Acceptance:** Guide complete; examples for all decorator types; pitfalls documented

#### FR-OBS-024: Dashboard User Guide
- **Description:** Create user guide explaining dashboard tabs, queries, filters, and how to use for debugging
- **Scope:** Personas: Cesar (executive), QA (debugging), Ops (optimization)
- **Expected Outcome:** Guide walks through each dashboard tab; example queries for common use cases
- **Acceptance:** Guide complete; new user can navigate dashboard independently

#### FR-OBS-025: Runbook: Debug High Latency
- **Description:** Document step-by-step procedure to investigate and resolve high agent latency
- **Scope:** Queries to identify slow methods, bottleneck detection, optimization strategies
- **Expected Outcome:** Ops can reduce agent latency by 50%+ using runbook
- **Acceptance:** Runbook tested with 2+ latency investigations; documented results

#### FR-OBS-026: Runbook: Investigate Failed Span Delivery
- **Description:** Document step-by-step procedure to debug when spans aren't reaching Phoenix
- **Scope:** Network troubleshooting, API key validation, Phoenix connectivity checks
- **Expected Outcome:** Ops can restore span delivery within 15 minutes of detection
- **Acceptance:** Runbook tested; successfully restores span delivery in test scenario

#### FR-OBS-027: Runbook: Reduce LLM Costs
- **Description:** Document cost optimization strategies (model selection, prompt efficiency, batch processing)
- **Scope:** Identify high-cost operations; recommend cost-effective alternatives
- **Expected Outcome:** Ops can identify > $100/month savings opportunities
- **Acceptance:** Runbook identifies actual cost savings in pilot runs

#### FR-OBS-028: SLO Definition & Tracking
- **Description:** Define per-agent SLOs (e.g., "Prospector campaign latency p95 < 30s") and dashboard to track compliance
- **Scope:** All agents; latency, error rate, cost SLOs
- **Expected Outcome:** Dashboard shows SLO compliance status; alerts when SLO violated
- **Acceptance:** 10+ SLOs defined; dashboard tracks compliance; 95%+ compliance achieved

#### FR-OBS-029: Span Sampling Configuration
- **Description:** Implement sampling strategy (100% for errors/exceptions, 10% for normal operations) to manage costs
- **Scope:** Configurable sampling rates via environment variables
- **Expected Outcome:** Normal operations sampled at 10%; errors/exceptions always sampled; cost reduced by ~50%
- **Acceptance:** Sampling rates configurable; cost validation shows 50%+ reduction

#### FR-OBS-030: Observability Runbooks Repository
- **Description:** Create `docs/observability/runbooks/` directory with 5+ runbooks for common scenarios
- **Scope:** High latency, failed spans, cost overrun, error investigation, dashboard troubleshooting
- **Expected Outcome:** Complete runbook library enables self-service debugging
- **Acceptance:** 5+ runbooks created; tested in real scenarios

---

## Part 2: Non-Functional Requirements (NFR-OBS-001 through NFR-OBS-015)

#### NFR-OBS-001: Span Latency Overhead
- **Requirement:** Decorator overhead must be < 10ms per method call
- **Rationale:** Agent performance must not degrade; observability is invisible to end-users
- **Measurement:** Profile all decorators in isolated test; p99 overhead < 10ms
- **Acceptance Criteria:** Latency profile in architecture doc; test confirms < 10ms overhead

#### NFR-OBS-002: Span Delivery Reliability
- **Requirement:** 99.9% of created spans must be successfully delivered to Phoenix within 5 seconds
- **Rationale:** Observability gaps lead to blind spots; metrics must be trustworthy
- **Measurement:** Dashboard metric `span_delivery_rate`; monthly compliance tracking
- **Acceptance Criteria:** 99.9% delivery rate measured over 1 week of production traffic

#### NFR-OBS-003: Span Processing Latency
- **Requirement:** Span processing (creation + transmission) must complete within 500ms (non-blocking)
- **Rationale:** Spans are asynchronous; must not block agent execution
- **Measurement:** Span creation and transmission happens in background thread/async task
- **Acceptance Criteria:** Agent latency unchanged (< 5% variance) with tracing enabled vs. disabled

#### NFR-OBS-004: Dashboard Query Performance
- **Requirement:** Dashboard queries must return results within 10 seconds
- **Rationale:** Real-time debugging requires fast feedback
- **Measurement:** Query execution time logged; p95 latency tracked
- **Acceptance Criteria:** 95% of queries complete within 10s; slowest queries analyzed and optimized

#### NFR-OBS-005: Monthly Cost Target
- **Requirement:** Total observability cost (Phoenix + infrastructure) must be < $500/month
- **Rationale:** Cost-effective observability for early-stage startup
- **Measurement:** Daily cost tracking; monthly invoice validation
- **Acceptance Criteria:** Monthly bill < $500; sampling strategy validates savings

#### NFR-OBS-006: Dashboard Uptime
- **Requirement:** Dashboard must be available 99.5% of the time (aligned with Phoenix SLA)
- **Rationale:** Observability system is critical for ops; needs high availability
- **Measurement:** Dashboard uptime monitoring; alerting on failures
- **Acceptance Criteria:** 99.5% uptime over 30 days; <4 hours downtime

#### NFR-OBS-007: Span Storage & Retention
- **Requirement:** Spans retained for 30 days in Phoenix; older spans archived
- **Rationale:** Balance historical analysis with cost; 30 days sufficient for issue investigation
- **Measurement:** Phoenix retention policy configured
- **Acceptance Criteria:** 30-day policy verified; cost savings confirmed

#### NFR-OBS-008: Security & Access Control
- **Requirement:** Dashboard access controlled via role-based access control; only authorized users (Cesar, QA, Ops) can view sensitive metrics (cost)
- **Rationale:** Financial data is sensitive; must protect from unauthorized access
- **Measurement:** Phoenix IAM configuration; audit logs of dashboard access
- **Acceptance Criteria:** RBAC configured; audit logs show proper access control

#### NFR-OBS-009: Backward Compatibility
- **Requirement:** All instrumentation changes must be backward compatible; no breaking changes to agent interfaces
- **Rationale:** Existing agent code must work unchanged
- **Measurement:** All existing agent tests pass with tracing enabled
- **Acceptance Criteria:** 100% of existing tests pass; no signature changes to agent methods

#### NFR-OBS-010: Scalability — Multi-Agent Tracing
- **Requirement:** Tracing infrastructure must support 7+ concurrent agents; no performance degradation with scale
- **Rationale:** All agents run concurrently; tracing must not become bottleneck
- **Measurement:** Load test with all 7 agents running; span delivery rate, latency metrics tracked
- **Acceptance Criteria:** Span delivery remains 99.9% with all 7 agents active

#### NFR-OBS-011: Error Handling & Resilience
- **Requirement:** If Phoenix is unavailable, agents must continue working (graceful degradation); errors logged but not surfaced to users
- **Rationale:** Observability is supplementary; agents must be resilient
- **Measurement:** Test with Phoenix API key invalid; agent execution continues
- **Acceptance Criteria:** Agent works with Phoenix disabled; errors logged to stdout; no crashes

#### NFR-OBS-012: Data Privacy & Sensitivity
- **Requirement:** Spans must not capture personally identifiable information (PII) unless explicitly configured; sensitive data redacted
- **Rationale:** GDPR/privacy compliance; protect user data
- **Measurement:** Span audits; redaction validation
- **Acceptance Criteria:** No PII in spans by default; documentation on redaction strategy

#### NFR-OBS-013: Monitoring & Observability of Observability
- **Requirement:** Tracing infrastructure itself must be observable (e.g., span count, delivery rate metrics)
- **Rationale:** Meta-observability; need to know if observability system is working
- **Measurement:** System-level metrics (span_delivery_rate, span_count, cost) in dashboard
- **Acceptance Criteria:** System-level metrics visible and tracked in dashboard

#### NFR-OBS-014: Test Coverage
- **Requirement:** All instrumentation code must have 100% unit test coverage
- **Rationale:** Decorators are critical; must be bulletproof
- **Measurement:** pytest --cov=eworks.core.phoenix_instrumentation
- **Acceptance Criteria:** Coverage reports show 100% line coverage for instrumentation module

#### NFR-OBS-015: Documentation Completeness
- **Requirement:** All features must be documented; no code without accompanying docs
- **Rationale:** Enables self-service adoption by developers
- **Measurement:** Doc completeness checklist
- **Acceptance Criteria:** All FRs/NFRs have corresponding doc sections; no "TBD" placeholders

---

## Part 3: Constraints (CON-OBS-001 through CON-OBS-005)

#### CON-OBS-001: Python Version Requirement
- **Constraint:** Python 3.12+ required for async decorator compatibility and latest stdlib features
- **Rationale:** Async decorator frameworks require Python 3.12+
- **Impact:** All Eworks OS agents must run on Python 3.12+; legacy Python versions not supported
- **Validation:** CI/CD enforces Python 3.12+ check

#### CON-OBS-002: Phoenix Version Requirement
- **Constraint:** Arize Phoenix v16.0+ required for API features used in instrumentation
- **Rationale:** Earlier versions lack span batch API, context propagation, and sampling features
- **Impact:** Production Phoenix instance must be v16.0+
- **Validation:** Startup code validates Phoenix version

#### CON-OBS-003: No Breaking Changes to Agent Interfaces
- **Constraint:** All instrumentation must not change agent method signatures, return types, or side effects
- **Rationale:** Existing code depends on agent interfaces; cannot break compatibility
- **Impact:** Decorators must be transparent; no signature changes
- **Validation:** All existing agent tests pass; integration tests verify output equivalence

#### CON-OBS-004: LinkedIn API Rate Limits
- **Constraint:** Prospector agent must respect LinkedIn API rate limits; observability cannot exceed rate limit quota
- **Scope:** Prospector's external API calls
- **Impact:** Instrumentation of LinkedIn calls must not generate additional requests; tracing is synchronous
- **Validation:** Network calls logged; rate limit compliance verified

#### CON-OBS-005: Budget Limitations
- **Constraint:** LLM token consumption must remain within budget; observability cost cannot exceed $500/month
- **Rationale:** Startup cost constraints
- **Impact:** Sampling strategy enforced; cost tracking non-negotiable
- **Validation:** Monthly cost tracking; alerts if budget exceeded

---

## Part 4: User Stories & Acceptance Criteria

### 4.1 User Story: STORY-OBS-1.1
**Title:** Trace Prospector Agent Execution  
**Epic:** OBSERVABILITY  
**Persona:** QA Engineer (DevOps)  

**User Story:**
> As a QA engineer, I want to trace every Prospector campaign execution from start to finish so that I can debug failures and validate the instrumentation is working.

**Requirements Mapping:**
- FR-OBS-001 (Trace Prospector methods)
- FR-OBS-009 (Trace LLM calls)
- FR-OBS-014 (Capture errors)

**Acceptance Criteria:**
- [ ] All methods in `prospector/orchestrator.py`, `executor.py`, `generator.py` have @trace_agent_execution decorator
- [ ] @trace_llm_call decorator wraps all `client.messages.create()` calls
- [ ] Each span includes agent="prospector", method=<name>, campaign_id, prospect_count, tokens_used, latency_ms
- [ ] Error spans include error message and stack trace (first 500 chars)
- [ ] 5+ unit tests verify decorators fire and span attributes are correct
- [ ] All existing Prospector tests pass with tracing enabled
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged to main branch
- [ ] Tests passing (100% coverage for instrumentation)
- [ ] Spans visible in Phoenix test environment
- [ ] PR reviewed and approved

---

### 4.2 User Story: STORY-OBS-1.2
**Title:** Trace Publisher Agent Execution  
**Epic:** OBSERVABILITY  
**Persona:** QA Engineer (DevOps)  

**User Story:**
> As a QA engineer, I want to trace Publisher's content generation pipeline so that I can measure latency, token usage, and identify bottlenecks.

**Requirements Mapping:**
- FR-OBS-002 (Trace Publisher methods)
- FR-OBS-009 (Trace LLM calls)
- FR-OBS-010 (Capture tokens)
- FR-OBS-015 (Trace workflow steps)

**Acceptance Criteria:**
- [ ] All methods in `publisher/orchestrator.py`, `social_orchestrator.py` have @trace_agent_execution decorator
- [ ] Workflow spans show step-by-step breakdown (generate_ideas, create_post, schedule, publish)
- [ ] Each span includes agent="publisher", method, content_id, idea_count, tokens_used, latency_ms
- [ ] LLM spans capture input/output tokens for each generation call
- [ ] 5+ unit tests verify decorator firing and span quality
- [ ] All existing Publisher tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Spans visible in Phoenix with proper attributes
- [ ] Latency breakdown visible in dashboard

---

### 4.3 User Story: STORY-OBS-1.3
**Title:** Trace Closer Agent & Deal Opportunities  
**Epic:** OBSERVABILITY  
**Persona:** Operations / Cesar (Founder)  

**User Story:**
> As a founder, I want to see every proposal generated by the Closer agent, its latency, and success rate so that I can understand deal flow and optimize the Closer's performance.

**Requirements Mapping:**
- FR-OBS-003 (Trace Closer methods)
- FR-OBS-012 (Trace external API calls)
- FR-OBS-020 (Evaluation metrics)

**Acceptance Criteria:**
- [ ] All Closer methods instrumented (discover_opportunities, generate_proposal, send_proposal, _evaluate_fit)
- [ ] Each proposal generation span includes opportunity_id, prospect_id, proposal_status, tokens_used, latency
- [ ] Dashboard shows proposals_generated (counter), acceptance_rate (gauge %), discovery_latency_p95
- [ ] 5+ unit tests + integration test for full proposal flow
- [ ] All existing tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Metrics visible in dashboard
- [ ] Cesar can see proposal KPIs in real-time

---

### 4.4 User Story: STORY-OBS-1.4
**Title:** Trace Conductor Workflow Orchestration  
**Epic:** OBSERVABILITY  
**Persona:** QA Engineer / Operations  

**User Story:**
> As an operations engineer, I want to see Conductor's workflow execution step-by-step so that I can identify which agent is causing delays in the overall pipeline.

**Requirements Mapping:**
- FR-OBS-004 (Trace Conductor methods)
- FR-OBS-015 (Trace workflow steps)

**Acceptance Criteria:**
- [ ] Conductor's run() method instrumented with workflow tracking
- [ ] Each workflow step (delegate to Prospector, Publisher, Closer) creates separate span
- [ ] Span attributes: workflow_id, step_count, step_name, step_status, step_latency
- [ ] Dashboard shows workflow success rate, end-to-end latency, per-step latency breakdown
- [ ] 5+ unit tests verify workflow span structure
- [ ] All existing tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Workflow traces visible with step-by-step breakdown
- [ ] Dashboard shows complete workflow timing

---

### 4.5 User Story: STORY-OBS-1.5
**Title:** Trace Treasurer Financial Operations  
**Epic:** OBSERVABILITY  
**Persona:** Operations / CFO  

**User Story:**
> As an operations person, I want to track all financial transactions processed by Treasurer so that I can validate financial accuracy and monitor cost of LLM inference.

**Requirements Mapping:**
- FR-OBS-005 (Trace Treasurer methods)
- FR-OBS-020 (Evaluation metrics)

**Acceptance Criteria:**
- [ ] All Treasurer methods instrumented (process_transaction, generate_report, check_budget)
- [ ] Each transaction span includes transaction_id, amount, report_type, tokens_used, latency
- [ ] Dashboard shows transactions_processed (counter), reports_generated (counter), budget alerts
- [ ] Cost-per-report metric calculated and displayed
- [ ] 5+ unit tests
- [ ] All existing tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Financial metrics visible in dashboard
- [ ] Budget alerts configured

---

### 4.6 User Story: STORY-OBS-1.6
**Title:** Trace Nurturer Prospect Engagement  
**Epic:** OBSERVABILITY  
**Persona:** Operations / Cesar  

**User Story:**
> As a founder, I want to track prospect engagement improvements over time so that I can measure the Nurturer agent's effectiveness and validate ROI.

**Requirements Mapping:**
- FR-OBS-006 (Trace Nurturer methods)
- FR-OBS-020 (Evaluation metrics)

**Acceptance Criteria:**
- [ ] All Nurturer methods instrumented (send_followup, evaluate_sentiment, update_score)
- [ ] Span attributes: prospect_id, message_type, sentiment_score, engagement_delta, tokens_used
- [ ] Dashboard shows follow_ups_sent (counter), engagement_improvement_rate (gauge %), sentiment trends
- [ ] Historical engagement score tracking enabled
- [ ] 5+ unit tests
- [ ] All existing tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Engagement metrics visible in dashboard
- [ ] Trend analysis available (week-over-week improvement)

---

### 4.7 User Story: STORY-OBS-1.7
**Title:** Trace Connector Multi-Platform Message Routing  
**Epic:** OBSERVABILITY  
**Persona:** QA Engineer / Operations  

**User Story:**
> As a QA engineer, I want to trace Connector's message listening and routing logic so that I can ensure messages are routed to the correct agent and identify platform integration failures.

**Requirements Mapping:**
- FR-OBS-007 (Trace Connector methods)
- FR-OBS-012 (Trace external API calls)

**Acceptance Criteria:**
- [ ] All Connector methods instrumented (listen, process_message, route_message)
- [ ] Span attributes: platform, message_id, source_platform, target_agent, route_accuracy, latency
- [ ] Platform integration health visible in dashboard (integration_uptime gauge)
- [ ] Failed routing attempts captured with error details
- [ ] 5+ unit tests covering happy path and error scenarios
- [ ] All existing tests pass
- [ ] CodeRabbit approval obtained

**Definition of Done:**
- [ ] Code merged; tests passing
- [ ] Message routing metrics visible in dashboard
- [ ] Platform failure alerts configured

---

### 4.8 User Story: STORY-OBS-2.1
**Title:** Create Real-Time Observability Dashboard  
**Epic:** OBSERVABILITY  
**Persona:** Cesar (Founder), Operations, QA Engineer  

**User Story:**
> As a founder and operations team, I want a real-time dashboard showing all agent activity, costs, and errors so that I can monitor business operations and quickly identify problems.

**Requirements Mapping:**
- FR-OBS-018 (Real-time dashboard)
- FR-OBS-020 (Evaluation metrics)
- FR-OBS-028 (SLO tracking)

**Acceptance Criteria:**
- [ ] Dashboard has 4+ tabs: Overview, Performance, Cost, Errors
- [ ] Overview tab shows: Agent status (green/yellow/red), daily metrics (campaigns sent, proposals, etc.), system health
- [ ] Performance tab shows: p50/p95/p99 latency per agent, method breakdown, bottleneck identification
- [ ] Cost tab shows: Cost per agent, cost per method, daily/monthly trend, budget remaining
- [ ] Errors tab shows: Error rate per agent, top error types, stack trace traces
- [ ] Dashboard queries execute within 10 seconds
- [ ] Data refreshes every 30 seconds (near real-time)
- [ ] SLO compliance widget shows on Overview tab

**Definition of Done:**
- [ ] Dashboard deployed to Phoenix
- [ ] All queries tested and validated
- [ ] User testing with Cesar/Ops confirms usability
- [ ] Link to dashboard shared

---

### 4.9 User Story: STORY-OBS-2.2
**Title:** Configure Alerting & Notifications  
**Epic:** OBSERVABILITY  
**Persona:** Operations / Cesar  

**User Story:**
> As an operations team, I want to receive alerts when critical issues occur so that I can respond quickly and minimize downtime.

**Requirements Mapping:**
- FR-OBS-019 (Alerting system)
- FR-OBS-028 (SLO tracking)

**Acceptance Criteria:**
- [ ] 5+ alert rules configured:
  - Agent execution error rate > 5%
  - Agent latency p95 > 30 seconds
  - Span delivery rate < 99%
  - Estimated daily cost > $50
  - LLM token consumption > 1M tokens
- [ ] Slack/Telegram notifications configured and tested
- [ ] Alert firing test scenarios verified
- [ ] Alert thresholds documented
- [ ] Alert logs show delivery confirmation

**Definition of Done:**
- [ ] All alerts firing correctly
- [ ] Notifications received on test channels
- [ ] Alert thresholds reviewed with Cesar/Ops

---

### 4.10 User Story: STORY-OBS-2.3
**Title:** Implement CI/CD Span Validation  
**Epic:** OBSERVABILITY  
**Persona:** QA Engineer / DevOps  

**User Story:**
> As a QA engineer, I want automated validation of spans in the test suite so that I can catch instrumentation regressions before they reach production.

**Requirements Mapping:**
- FR-OBS-021 (CI/CD span validation)
- FR-OBS-017 (Span schema consistency)

**Acceptance Criteria:**
- [ ] GitHub Actions workflow created (`.github/workflows/validate-spans.yml`)
- [ ] Workflow runs on every PR and push
- [ ] Test suite collects spans using in-memory Phoenix mock
- [ ] Schema validation: all spans have required attributes (agent, method, timestamp)
- [ ] Span quality checks:
  - No missing critical attributes (latency_ms, tokens_used for LLM calls)
  - Latency overhead < 10ms per call
  - Error spans include error message
- [ ] Workflow fails if schema validation fails
- [ ] PR blocks merge if validation fails
- [ ] Documentation on running validation locally

**Definition of Done:**
- [ ] Workflow deployed to GitHub
- [ ] Test run validates correctly
- [ ] PR created to verify workflow integration
- [ ] Developers can run validation locally

---

### 4.11 User Story: STORY-OBS-2.4
**Title:** Document Instrumentation Framework & Best Practices  
**Epic:** OBSERVABILITY  
**Persona:** Developers (all roles)  

**User Story:**
> As a developer, I want clear documentation on how to instrument new agents/methods so that I can add observability to new features without assistance.

**Requirements Mapping:**
- FR-OBS-023 (Instrumentation documentation)
- FR-OBS-024 (Dashboard guide)

**Acceptance Criteria:**
- [ ] `docs/instrumentation-guide.md` created with:
  - Overview of @trace_agent_execution, @trace_llm_call, @trace_tool_call decorators
  - Code examples for each decorator type
  - Async/sync handling explained
  - Decorator ordering with Click commands (pitfall: place custom decorators after Click decorators)
  - Error handling and span attribute best practices
- [ ] Dashboard user guide created with:
  - Tab-by-tab walkthrough
  - Common queries (latency analysis, cost breakdown, error investigation)
  - Filter and drill-down instructions
- [ ] Troubleshooting guide for common issues (Phoenix key invalid, no spans appearing, high latency)

**Definition of Done:**
- [ ] Docs complete and reviewed
- [ ] Examples tested and working
- [ ] New developer can instrument a method using guide alone

---

### 4.12 User Story: STORY-OBS-3.1
**Title:** Define & Track Service Level Objectives (SLOs)  
**Epic:** OBSERVABILITY  
**Persona:** Operations / Cesar  

**User Story:**
> As an operations team, I want defined SLOs for each agent so that I can measure and maintain performance standards.

**Requirements Mapping:**
- FR-OBS-028 (SLO definition)
- FR-OBS-020 (Evaluation metrics)

**Acceptance Criteria:**
- [ ] SLO document created: `docs/observability/slos.md`
- [ ] 10+ SLOs defined:
  - Prospector: campaign_latency_p95 < 30s, response_rate > 5%, error_rate < 2%
  - Publisher: content_pipeline_latency_p95 < 120s, quality_score > 70
  - Closer: discovery_latency_p95 < 30s, acceptance_rate > 10%
  - Conductor: workflow_latency_p95 < 60s, success_rate > 95%
  - (and others per agent)
- [ ] Dashboard widget shows SLO compliance status per agent
- [ ] SLO compliance tracked over 30-day rolling window
- [ ] Alerts fire when SLO at risk (< 80% compliance)
- [ ] Weekly SLO report generated

**Definition of Done:**
- [ ] SLO doc complete
- [ ] Dashboard SLO widget deployed
- [ ] First week of SLO tracking begins

---

### 4.13 User Story: STORY-OBS-3.2
**Title:** Create Observability Runbooks  
**Epic:** OBSERVABILITY  
**Persona:** Operations  

**User Story:**
> As an operations engineer, I want runbooks for common debugging scenarios so that I can troubleshoot issues quickly and independently.

**Requirements Mapping:**
- FR-OBS-025 (Debug latency runbook)
- FR-OBS-026 (Failed spans runbook)
- FR-OBS-027 (Cost optimization runbook)
- FR-OBS-030 (Runbooks repository)

**Acceptance Criteria:**
- [ ] Runbook 1: "Debug High Agent Latency"
  - Query 1: Identify slowest methods per agent
  - Query 2: Drill down into slow method calls
  - Analysis: LLM latency vs. API latency vs. other overhead
  - Action items: Model downgrade, API caching, parallelization
- [ ] Runbook 2: "Investigate Failed Span Delivery"
  - Check 1: Phoenix API key validity
  - Check 2: Network connectivity (curl test)
  - Check 3: Span queue status (in-memory buffer)
  - Recovery: Restart agent, verify spans resume
- [ ] Runbook 3: "Reduce LLM Costs"
  - Analysis: Cost per agent, cost per method
  - Identification: High-token-count operations
  - Actions: Model downgrade, prompt optimization, batch processing
  - Target: 20%+ cost reduction
- [ ] Runbook 4: "Validate Instrumentation Health"
  - Checks: Span count, delivery rate, schema compliance
  - Recovery: Restart tracing, validate decorators
- [ ] Runbook 5: "Dashboard Troubleshooting"
  - Slow queries: Identify and optimize
  - Missing data: Validate data flow
  - Access issues: Permission troubleshooting

**Definition of Done:**
- [ ] All 5 runbooks created and reviewed
- [ ] Each runbook tested in real scenario (not just documented)
- [ ] Runbook repository linked in dashboard
- [ ] Team trained on runbook usage

---

## Part 5: Release & Success Criteria

### 5.1 Release Criteria

**Phase 1: Governance (Batch 1)**
- [ ] This PRD complete and signed off
- [ ] Architecture document complete (span schema, dashboard design, evaluation framework)
- [ ] Brainstorming brief approved

**Phase 2: Development (Batch 2-4)**
- [ ] All 7 agents instrumented (FRs-001-007)
- [ ] All LLM/tool calls traced (FRs-009-015)
- [ ] 100% unit test coverage for instrumentation
- [ ] Dashboard deployed and verified
- [ ] CI/CD validation integrated

**Phase 3: Operations (Batch 5)**
- [ ] Dashboard live in production
- [ ] Alerting functional (5+ alert rules firing)
- [ ] SLOs defined and tracked
- [ ] Runbooks created and tested
- [ ] Team trained

### 5.2 Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Instrumentation Coverage | 100% of agent methods | Grep for @trace_agent_execution |
| Unit Test Coverage | 100% of decorators | pytest --cov=eworks.core.phoenix |
| Span Latency Overhead | < 10ms per call | Profile report |
| Span Delivery Rate | 99.9% | Dashboard metric `span_delivery_rate` |
| Dashboard Query Performance | p95 < 10s | Query logs |
| Monthly Cost | < $500 | Phoenix billing invoice |
| Uptime | 99.5% | Uptime monitoring |
| SLO Compliance | 95%+ | Weekly report |
| Test Pass Rate | 100% | CI/CD dashboard |

### 5.3 Go/No-Go Decision

**Go if:**
- ✅ All FRs and NFRs met or on track
- ✅ Test coverage > 95%
- ✅ Dashboard deployed and validated
- ✅ Alerting functional
- ✅ Cost < $500/month

**No-Go if:**
- ❌ Critical instrumentation missing (> 20% agents)
- ❌ Test coverage < 80%
- ❌ Span delivery rate < 95% (unreliable)
- ❌ Cost exceeds $500/month

---

## Part 6: Approval & Sign-Off

**Document Status:** Ready for Review

- [ ] **AIOX @pm (Product Manager):** Reviewed and approved PRD
- [ ] **AIOX @architect (Architecture Lead):** Confirmed architecture feasibility
- [ ] **Cesar Schneider (Founder/CEO):** Approved business requirements and success criteria
- [ ] **QA Lead:** Confirmed test strategy
- [ ] **Engineering Lead:** Confirmed technical feasibility

---

## Document Metadata

**Epic ID:** OBSERVABILITY  
**PRD Version:** 1.0  
**Date Created:** May 22, 2026  
**Last Updated:** May 22, 2026  
**Product Manager:** AIOX @pm Agent  
**Architecture Lead:** AIOX @architect Agent  
**Status:** Batch 1 — Complete (Pending Review)  

**Next Steps:**
1. Circulate PRD to stakeholders for review
2. Incorporate feedback
3. Obtain sign-offs from Cesar, engineering, QA
4. Proceed to Batch 2: Story drafting and parallel implementation

---

**End of PRD: epic-OBSERVABILITY-platform.md**
