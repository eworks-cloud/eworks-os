# STORY-7.9 — Tests
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want a comprehensive test suite for the social publisher so that I can verify all components work correctly without calling real APIs.

## Acceptance Criteria
- [x] AC1. ImageGenerator init and API key validation tested
- [x] AC2. Platform size mapping logic tested
- [x] AC3. LinkedInPoster no-auth fallback tested
- [x] AC4. LinkedIn payload structure validated
- [x] AC5. Carousel max image limits tested for both platforms
- [x] AC6. InstagramPoster no-auth fallback tested
- [x] AC7. social_posts and social_analytics table creation tested
- [x] AC8. All tests pass without calling external APIs

## Tasks
- [x] Task 1: Create tests/test_social_publisher.py
- [x] Task 2: Write all test functions
- [x] Task 3: Run pytest and verify all pass
- [x] Task 4: Git commit

## Dev Notes
Tests use unittest.mock for all external API calls.
DB tests use tempfile for isolated SQLite databases.
asyncio.run() used for async Instagram tests.

## File List
- tests/test_social_publisher.py (new)
