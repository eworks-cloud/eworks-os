# Epic 7 — Full Social Publisher Agent
**Status:** In Progress
**Agent:** Publisher (extended)
**Goal:** Support LinkedIn + Instagram with text, image, video, carousel posts and analytics

## Functional Requirements
- FR-701: LinkedIn text post via ugcPosts API
- FR-702: LinkedIn image post (FAL.ai generated image + upload)
- FR-703: LinkedIn video post (HeyGen video + native upload)
- FR-704: LinkedIn carousel post (multi-image)
- FR-705: Instagram image post (FAL.ai generated)
- FR-706: Instagram carousel post (multi-image Reel/Feed)
- FR-707: Analytics fetch for LinkedIn posts
- FR-708: Analytics fetch for Instagram posts
- FR-709: Smart scheduler (optimal times: Tue-Thu 8-10 AM)
- FR-710: Telegram approval before posting
- FR-711: All posts saved to DB with status tracking
- FR-712: CLI commands for all content types

## Non-Functional Requirements
- NFR-701: Max 3 LinkedIn posts/day (safety limit, API allows 150)
- NFR-702: Max 5 Instagram posts/day
- NFR-703: Image generation timeout: 60s
- NFR-704: Video upload timeout: 30min
- NFR-705: All tokens stored securely in .env

## Constraints
- CON-701: LinkedIn API requires OAuth2 access token with w_member_social scope
- CON-702: Instagram image posts require public URL (not local file)
- CON-703: LinkedIn video must be uploaded as binary (not URL)
- CON-704: Carousel max 9 images on LinkedIn, 10 on Instagram
