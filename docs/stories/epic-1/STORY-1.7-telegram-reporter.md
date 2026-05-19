# STORY-1.7 — Telegram Reporter

**Status:** ✅ Done
**Epic:** Epic 1 — LinkedIn Prospector Agent
**Agent:** @dev (Dex)

## Description
Send structured daily reports, error alerts and real-time notifications to a Telegram chat.

## Acceptance Criteria
- [x] `TelegramReporter.__init__(bot_token, chat_id)` — from env or explicit params
- [x] `send()` — plain text with HTML parse mode
- [x] `send_daily_report()` — formatted report with scan count, messages sent, replies, meetings, reply rate
- [x] `send_error_alert()` — error + context notification
- [x] `send_prospect_reply()` — reply notification with prospect name
- [x] `send_start_notification()` — campaign start alert

## Commit
`feat(reporter): Telegram daily reports + alerts + reply notifications`
