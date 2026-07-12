# STORY-11.10 — Customer Success View (Nurturer)

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Client health, check-ins, upsell opportunities, and onboarding progress, with red-zone highlighting.

## Acceptance Criteria
- [ ] `web/app/customer-success/page.tsx` shows each client's current health score with component breakdown from `client_health_scores` (FR-1114)
- [ ] Recent check-ins with NPS/sentiment (`client_checkins`) and open `upsell_opportunities` are listed per client (FR-1114)
- [ ] Onboarding progress from `onboarding_checklists` is shown (FR-1114)
- [ ] Red-zone (low health-score) clients are visually highlighted (FR-1114)
- [ ] `web/app/customer-success/[clientId]/page.tsx` drill-down shows the client's full health/check-in/upsell history (FR-1117)

## Dependencies
- Story 11.2, Story 11.3; DEP-1108
