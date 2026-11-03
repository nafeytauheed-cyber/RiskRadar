# Changelog

## 2.0 investigation-platform draft
- Replace startup training/cache API with authenticated durable processing API.
- Add causal feature snapshots, censoring-aware labels, separated calibration/test evaluation and bounded JSON logistic artifacts.
- Add transactional event/job ingestion, fenced leases, append-only predictions/revisions, incidents, outbox and isolated replay.
- Add investigation UI, PostgreSQL schema, local Compose and verification workflow.
- Preserve original demonstration code as disconnected legacy reference; industrial validity and production readiness are not claimed.

- Verify separate durable feature/inference phases, maintenance boundaries, original-model late revisions, snapshot integrity, and reopening hysteresis.
- Record 42 passing backend tests, 2 passing browser tests, multi-equipment duplicate/delay workload, and real database restart/restore evidence at implementation checkpoint 1d63d2c.

- Added immutable replay membership, bounded scoring/results pages, durable progress, fenced cancel/resume, optional replay consumer and UI controls.
- Retained historical feature runtimes with golden parity fixtures; pinned replay fingerprints and blocked historical-only model promotion.
