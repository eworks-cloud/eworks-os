# STORY-7.3 — FAL.ai Image Generator
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want an ImageGenerator that calls FAL.ai Flux Schnell to create images for social posts so that posts have professional AI-generated visuals.

## Acceptance Criteria
- [x] AC1. ImageGenerator class created in image_generator.py
- [x] AC2. generate() produces single image from prompt
- [x] AC3. generate_batch() produces multiple images for carousels
- [x] AC4. generate_for_post() uses platform-optimized sizes
- [x] AC5. FAL_KEY not set raises ValueError
- [x] AC6. data/images/ directory created

## Tasks
- [x] Task 1: Create eworks/agents/publisher/image_generator.py
- [x] Task 2: Implement generate() with FAL.ai API
- [x] Task 3: Implement generate_batch() for carousels
- [x] Task 4: Implement generate_for_post() with size mapping
- [x] Task 5: Create data/images/.gitkeep
- [x] Task 6: Git commit

## Dev Notes
Uses FAL.ai Flux Schnell (fal-ai/flux/schnell) for fast generation.
Platform sizes: LinkedIn image=landscape_4_3, carousel=square_hd; Instagram feed=square_hd, reel=portrait_16_9.

## File List
- eworks/agents/publisher/image_generator.py (new)
- data/images/.gitkeep (new)
