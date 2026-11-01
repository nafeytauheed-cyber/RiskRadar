# Roadmap / acceptance

1. Audit + baseline: reproduced original leakage/batch defects; retain measurements.
2. Science slice: causal features, censoring labels, equipment-disjoint selection/calibration/test, safe logistic artifact and baseline comparisons. Pending independent chronological cohorts, realistic intervention validation, abstention-error curves and held-out mechanisms.
3. Durability slice: atomic ingest/jobs, leases/fences, idempotent effects, retries/dead jobs/outbox. Acceptance requires green real PostgreSQL tests, not mocks.
4. Ordering/quality/incidents: bounded causal fill, session warmup, idle freshness, append revisions, optimistic incident transitions. Pending cross-event clock anomaly quarantine, maintenance lifecycle management and inspection outcome API.
5. Replay/provenance: arrival and corrected modes, manifests/model hashes/isolated scopes, UI comparison. Pending scalable paginated replay and persisted run progress/cancellation.
6. Operations: auth/ownership/CORS, Compose, CI, load experiment, promotion/rollback. Pending process-kill and outage/soak experiments, dead-letter operator workflow, production secret rotation/RLS and restore drill.
7. Product/docs: new investigation surface preserves legacy components, code-linked guide, draft PR. Pending browser-driven interaction/accessibility tests and independent operator study.

No item marked pending may be represented as verified or production-ready.
