# STORY-7.4 — LinkedIn Poster (All Content Types)
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want a LinkedInPoster that supports text, image, video, and carousel posts via the official LinkedIn API so that I can publish all content types to LinkedIn.

## Acceptance Criteria
- [x] AC1. post_text() posts text-only via ugcPosts API
- [x] AC2. post_image() uploads image binary and creates media post
- [x] AC3. post_video() registers upload and posts native video
- [x] AC4. post_carousel() uploads multiple images and posts carousel
- [x] AC5. get_post_analytics() fetches post engagement metrics
- [x] AC6. All methods return needs_auth if no token set

## Tasks
- [x] Task 1: Create eworks/agents/publisher/linkedin_poster.py
- [x] Task 2: Implement _headers(), get_person_urn()
- [x] Task 3: Implement post_text()
- [x] Task 4: Implement _register_image_upload() + _upload_image_binary()
- [x] Task 5: Implement post_image()
- [x] Task 6: Implement post_video()
- [x] Task 7: Implement post_carousel()
- [x] Task 8: Implement get_post_analytics()
- [x] Task 9: Git commit

## Dev Notes
Uses LinkedIn ugcPosts API for all post types.
Image/video upload uses registerUpload + binary PUT pattern.
Carousel max 9 images enforced.
Analytics via /socialActions/{urn} endpoint.

## File List
- eworks/agents/publisher/linkedin_poster.py (new)
