# STORY-12.1 — gbrain PGLite Init + Embedding Provider Detection

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 5

## Summary
Initialize gbrain's embedded PGLite engine and wire local-first embedding-provider detection with a reportable status.

## Acceptance Criteria
- [ ] `eworks/core/brain.py` wraps `gbrain init --pglite`, initializing the brain store on the same host as the agents with no new server, database service, or Docker container (FR-1201, NFR-1201, CON-1202)
- [ ] `eworks/core/brain_config.py` defaults the embedding provider to local (Ollama/llama.cpp), incurring zero cloud cost out of the box (FR-1202, NFR-1203, CON-1204)
- [ ] `eworks/core/brain_config.py` supports switching to a cloud embedding provider (OpenAI/Voyage/ZeroEntropy) as an explicit opt-in via environment/config using gbrain's env-key auto-detection; switching providers is a config change only, never a code change (FR-1203, CON-1204)
- [ ] `config/settings.yaml` gains a `brain:` section documenting the PGLite path and embedding-provider config keys (FR-1201)
- [ ] `eworks/core/brain.py` exposes a provider-status accessor reporting the active embedding provider (local vs. which cloud provider), for later use by the status CLI command (Story 12.6) (FR-1204)
- [ ] SQLite schema in `eworks/core/database.py` is verified unchanged by this story — gbrain integration touches no existing table (NFR-1202, CON-1201)

## Dependencies
- DEP-1201, DEP-1202
