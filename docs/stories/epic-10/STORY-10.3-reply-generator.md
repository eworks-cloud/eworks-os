# STORY-10.3 — Reply Generator (Claude AI)

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 5

## Summary
Claude AI reply generator with lead detection, sentiment analysis, language detection, and confidence scoring.

## Acceptance Criteria
- [ ] eworks/agents/connector/reply_generator.py created
- [ ] detect_lead_signal() checks for meeting/pricing keywords in EN+PT
- [ ] detect_language() returns 'en' or 'pt'
- [ ] analyze_sentiment() returns positive/neutral/negative
- [ ] generate_reply() calls Claude, returns structured dict
- [ ] generate_lead_opener() generates Cesar's personal opener
- [ ] All errors handled gracefully (returns dict with should_escalate=True)
