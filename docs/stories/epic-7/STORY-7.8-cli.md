# STORY-7.8 — CLI Commands
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want CLI commands for social posting so that I can trigger LinkedIn/Instagram posts from the terminal with simple commands.

## Acceptance Criteria
- [x] AC1. `eworks social post` — unified post command with all options
- [x] AC2. `eworks social text` — text-only post
- [x] AC3. `eworks social image` — AI image post
- [x] AC4. `eworks social video` — HeyGen video post
- [x] AC5. `eworks social carousel` — multi-image carousel
- [x] AC6. `eworks social analytics` — fetch post metrics
- [x] AC7. `eworks social list` — list all posts
- [x] AC8. `eworks social schedule` — schedule recurring posts
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
