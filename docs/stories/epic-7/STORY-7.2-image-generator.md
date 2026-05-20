# STORY-7.2 — Database Tables for Social Posts + Analytics
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want social_posts and social_analytics tables in the DB so that all posts and their metrics are tracked persistently.

## Acceptance Criteria
- [x] AC1. social_posts table created with all required columns
- [x] AC2. social_analytics table created with impressions/likes/comments/shares
- [x] AC3. add_social_publisher_tables() method added to DatabaseManager
- [x] AC4. All status CHECK constraints enforced

## Tasks
- [x] Task 1: Add SOCIAL_PUBLISHER_SCHEMA_SQL constant to database.py
- [x] Task 2: Implement add_social_publisher_tables() method
- [x] Task 3: Git commit

## Dev Notes
Tables use CHECK constraints for platform, content_type, and status columns.
carousel_paths stored as JSON array TEXT.
References content_scripts(id) and content_ideas(id) from publisher tables.

## File List
- eworks/core/database.py (modified)
