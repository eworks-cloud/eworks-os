# STORY-7.5 — Instagram Full Publisher (Image + Carousel + Analytics)
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want Instagram posting to support single images and carousels (not just reels) so that I can publish all content types to Instagram.

## Acceptance Criteria
- [x] AC1. post_image() uploads image to CDN and posts via Graph API
- [x] AC2. upload_file_to_cdn() handles both images and videos
- [x] AC3. post_carousel() creates album with up to 10 images
- [x] AC4. get_post_analytics() fetches impressions/reach/likes/comments
- [x] AC5. upload_video_to_cdn() alias created for backward compatibility
- [x] AC6. Returns needs_auth when credentials missing

## Tasks
- [x] Task 1: Add post_image() to InstagramPoster
- [x] Task 2: Add upload_file_to_cdn() (general CDN upload)
- [x] Task 3: Add post_carousel() with item container creation
- [x] Task 4: Add get_post_analytics() via Graph API insights
- [x] Task 5: Keep upload_to_cdn() as backward compat alias
- [x] Task 6: Git commit

## Dev Notes
Instagram image posts require public URL — uses file.io CDN.
Carousel: create individual containers first, then carousel container, then publish.
Max 10 images enforced.

## File List
- eworks/agents/publisher/social_poster.py (modified)
