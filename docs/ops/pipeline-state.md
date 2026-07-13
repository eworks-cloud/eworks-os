# Autonomous SDC Pipeline — Run Log

Append-only log written by the hourly SDC pipeline Routine (Epics 11-17 only). One line per firing. This log is for forensics and stall-detection — the source of truth for pipeline state is always each story file's `**Status:**` field plus live GitHub PR state, not this file.

To pause the pipeline, create an empty file at `docs/ops/PAUSE` — the Routine checks for it first on every firing and no-ops if present. Delete the file to resume.

| Timestamp (UTC) | Story | Stage | Outcome | PR |
|---|---|---|---|---|
