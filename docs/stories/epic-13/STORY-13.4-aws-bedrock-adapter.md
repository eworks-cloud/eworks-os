# STORY-13.4 — AWS Bedrock Adapter

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Draft
**Points:** 3

## Summary
First concrete fallback provider adapter: AWS Bedrock, using its `invoke_model` API shape (not OpenAI-compatible), plugged into the `Provider` protocol and fallback chain from Story 13.2.

## Acceptance Criteria
- [ ] `eworks/core/ai_providers/bedrock.py` implements a `BedrockProvider` class conforming to the `Provider` protocol (Story 13.2), configured via AWS credentials/IAM role plus region and model ID (FR-1308, FR-1309)
- [ ] `BedrockProvider` uses Bedrock's `invoke_model` API shape (not an OpenAI-compatible chat-completions call) to translate the common `generate(...)` request into Bedrock's request/response format, supporting basic system/user/assistant roles only (FR-1309, CON-1305)
- [ ] `BedrockProvider`'s default model ID is `meta.llama3-1-70b-instruct-v1:0`, overridable via an environment variable (FR-1309)
- [ ] `BedrockProvider` reads AWS credentials/region/model config through a config block in `eworks/core/config.py` following existing patterns; no AWS secret is committed or logged (FR-1309, NFR-1306, CON-1306)
- [ ] `BedrockProvider` requires no new standing infrastructure — only outbound HTTPS calls via `boto3`/AWS SDK to the Bedrock `invoke_model` endpoint (NFR-1302, CON-1303, DEP-1305)
- [ ] `BedrockProvider` is fully isolated behind the `Provider` protocol; adding it requires no change to `AIClient` core or callers (NFR-1307)

## Dependencies
- STORY-13.2
- DEP-1305
