# STORY-7.8 — CLI Commands
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want CLI commands for social posting so that I can trigger LinkedIn/Instagram posts from the terminal with simple commands.

## Acceptance Criteria
- [x] AC1. `eos social post` — unified post command with all options
- [x] AC2. `eos social text` — text-only post
- [x] AC3. `eos social image` — AI image post
- [x] AC4. `eos social video` — HeyGen video post
- [x] AC5. `eos social carousel` — multi-image carousel
- [x] AC6. `eos social analytics` — fetch post metrics
- [x] AC7. `eos social list` — list all posts
- [x] AC8. `eos social schedule` — schedule recurring posts
- [x] AC9. LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN added to .env.example

## Tasks
- [x] Task 1: Add `social` group to eworks/cli/main.py
- [x] Task 2: Implement all 8 social commands
- [x] Task 3: Update .env.example with LinkedIn vars
- [x] Task 4: Git commit

## Dev Notes
Commands use asyncio.run() to call SocialOrchestrator.
platform="both" resolves to ["linkedin", "instagram"].
All commands support --json flag for programmatic output.

## File List
- eworks/cli/main.py (modified)
- .env.example (modified)
