# STORY-11.8 — Org / Pipeline View (Conductor)

**Epic:** 11 — Operator Console
**Status:** Ready
**Points:** 5

## Summary
Project delivery state — active projects, sprints, task board, and blockers.

## Acceptance Criteria
- [ ] `web/app/projects/page.tsx` shows active projects with health score, sprint status, and task-board counts by status, sourced from `projects`, `sprints`, `project_tasks` (FR-1112)
- [ ] Recent `project_updates` (including blockers) are listed on the projects view (FR-1112)
- [ ] `web/app/projects/[id]/page.tsx` drill-down opens a project with its sprints and tasks (FR-1117)

## Dependencies
- Story 11.2, Story 11.3; DEP-1106

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Projects/org ACs cover health/sprint/task-board counts, recent updates/blockers, and project drill-down — traced to FR-1112/1117; deps and points present. Compact (3 ACs) with per-story risks absent, but each AC is testable and PRD-aligned — proceed.
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
