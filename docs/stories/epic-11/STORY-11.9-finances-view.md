# STORY-11.9 — Finances View (Treasurer)

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Invoices, payments, and overdue totals with drill-down reconciliation.

## Acceptance Criteria
- [ ] `web/app/finances/page.tsx` groups invoices by status (draft/sent/viewed/paid/overdue/cancelled) and computes outstanding and overdue totals from real rows in `invoices`/`invoice_items` (FR-1113)
- [ ] Overdue invoices are highlighted in a "needs attention" treatment, matching the Home view's aggregated "needs attention" list (FR-1113, FR-1106)
- [ ] Reminder activity from `payment_reminders` is shown alongside the relevant invoice (FR-1113)
- [ ] `web/app/finances/invoices/[id]/page.tsx` drill-down reconciles payments received against the invoice (FR-1117)

## Dependencies
- Story 11.2, Story 11.3; DEP-1107
