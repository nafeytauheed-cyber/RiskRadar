# Roadmap / acceptance

## Implemented vertical slices
- Audit and executable original baseline; causal sensor/window features with explicit quality and idle behavior.
- Offline equipment-disjoint train/selection/calibration/test; threshold/logistic/gradient-boosting/IsolationForest comparisons; calibration bins/diagram, lead time, false-alert exposure, Brier/log-loss, lifecycle bootstrap, selective error/coverage, grouping delay/reduction; safe logistic artifact and export parity.
- Seeded healthy/degradation/abrupt/bias/stuck/missing/duplicates/delays/restart/maintenance/simultaneous/unknown scenarios, separate hidden outcomes, held-out seeds/severity/mechanism stress report.
- PostgreSQL migrations, tenant ownership, admission bounds, idempotent ingestion, fenced retries/dead jobs, separate durable feature and inference workers, immutable histories, pinned late revisions.
- Explicit incident state machine, optimistic transitions, investigation notes, inspection/maintenance outcomes, maintenance lifecycle reset, notification outbox and ambiguous-delivery retry contract.
- Pinned arrival/corrected replay, isolated result scopes, comparison UI, model promotion/rollback, audit trail.
- Auth/roles/device scope, body limit/CORS, readiness/liveness, structured logs/queue metrics, Compose, CI, process-death/outage/restart/restore drills, browser walkthrough tests.

Verification is commit-specific; see PROJECT_STATE and EXPERIMENTS for which revisions ran successfully.

## Blocked scientific acceptance
1. Independently collected chronological/lifecycle validation: current historical CSVs start together and are synthetic. Later seeded simulator stress is implemented but does not substitute for an independent later cohort. Need a suitably licensed dataset with observable failure, operating-cycle, maintenance and censoring labels.
2. Validated diagnostic hypothesis support: no causal/diagnostic certainty can be inferred from the supplied generator and matching rules. Current output explicitly permits unknown faults. Any future fault classifier requires independent mechanisms/outcomes.
3. Threshold/business validation: 0.5/two-high policy is transparent and evaluated, but not optimized against real operational costs. Need domain costs and operator feedback before promotion beyond a demo.

## Deferred engineering acceptance (not claimed complete)
- Broad sustained multi-equipment/high-contention load, network partitions and replica failover; existing experiments are small single-instance workloads.
- Measure larger replay workloads and pinning-transaction duration; scoring and query pages are now bounded, but pinning scans all identities in one snapshot.
- Operational dead-letter retry/review UI, audited equipment/key provisioning workflow, external secret manager, RLS and production TLS/rate limits.
- General incompatible sensor-schema migrations. Retained causal-v1/v2 runtimes and replay fingerprints now exist; new versions still require explicit reviewed code and golden fixtures.
- Larger accessibility/operator study; browser walkthrough covers the core connect/evidence/replay path, not all usability cases.
- LLM summaries and ForceModel/LossLearning remain deliberately optional and unimplemented.
