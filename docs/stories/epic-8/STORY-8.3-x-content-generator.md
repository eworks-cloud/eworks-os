# STORY-8.3: X Content Generator

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As Eworks OS, I need Claude-powered content generation for X — single tweets, threads, image prompts, and LinkedIn cross-post adaptation.

---

## Acceptance Criteria

- [x] generate_tweet() returns ≤280 chars
- [x] generate_tweet() supports styles: insight, tip, question, stat, announcement
- [x] generate_thread() returns JSON list of tweet strings
- [x] generate_image_prompt() returns FAL.ai-compatible prompt for 16:9 landscape
- [x] adapt_from_linkedin() strips corporate tone, returns 4-5 tweet list
- [x] Both EN and PT (Brazilian Portuguese) language support

---

## Tasks

- [x] Create eworks/agents/publisher/x_content_generator.py
- [x] Wire claude-opus-4-5 for tweet/thread generation
- [x] Wire claude-haiku-4-5 for image prompts (cost optimization)
- [x] JSON parsing with fallback to line-split

---

## Dev Notes

System prompt personas as Cesar Schneider — builds authority, not cringe.
No hashtags in tweet body, no emojis unless meaningful.
Model: claude-opus-4-5 for quality tweets; claude-haiku-4-5 for image prompts.

---

## Files

- eworks/agents/publisher/x_content_generator.py (created)
