# STORY-11.5 — Funnel View (Prospector → Closer)

**Epic:** 11 — Operator Console
**Status:** Ready
**Points:** 5

## Summary
Acquisition-to-conversion funnel joining prospector and closer data, with drill-down into individual prospects/clients.

## Acceptance Criteria
- [ ] `web/app/funnel/page.tsx` groups prospects by real `status` (discovered → scored → queued → contacted → replied → meeting_booked / not_interested / dnc) and clients by real `status` (lead → discovery → proposal_sent → negotiating → won / lost / churned), with `proposals` status shown where present (FR-1109)
- [ ] Funnel-stage conversion counts shown match a direct DB query (verified in QA) (FR-1109)
- [ ] `web/app/funnel/prospects/[id]/page.tsx` and `web/app/funnel/clients/[id]/page.tsx` provide drill-down into an individual prospect/client, including related proposals (FR-1117)
- [ ] Stages/clients with zero real rows render "no data yet," not zero-filled fabricated funnel stages (FR-1103, CON-1105)

## Dependencies
- Story 11.2, Story 11.3; DEP-1102, DEP-1103

## Validation
- **Score:** 9/10
- **Verdict:** GO
- **Rationale:** Funnel ACs enumerate real status values, require counts to match a direct DB query (QA-verifiable), include drill-down routes, and honesty states — traced to FR-1109/1117/1103 and CON-1105; deps and points present; only per-story risk notes absent (epic §11).
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
