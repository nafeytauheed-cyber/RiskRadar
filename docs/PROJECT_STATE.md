# Project state

Branch: `upgrade/replayable-investigations`
Draft PR: https://github.com/nafeytauheed-cyber/RiskRadar/pull/1
Original base: `4456e04df6e571e310f159bac8c9318804e66d7b`
Latest implementation published: `1d63d2cb429e041fc369329be3451014972c72ed` (incident reopening + browser selector fix).

## Implemented
Causal/offline evaluation and data-only logistic artifacts; authenticated tenant/device API; PostgreSQL migrations and immutable histories; atomic ingestion/jobs; separate fenced feature/inference workers; bounded retries and outbox; quality/idle/session handling; late revisions pinned to original models; incidents, notes and maintenance lifecycle outcomes; isolated arrival/corrected replay; React investigation UI; Compose, CI, load/concurrency/recovery experiments and continuation documentation.

## Verified evidence
- Latest implementation `1d63d2cb429e041fc369329be3451014972c72ed` passed [CI run 41381105831](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41381105831): **42 backend tests (19 real PostgreSQL tests), 2 Chromium browser tests, frontend production build, offline evaluation, and three database experiments**.
- Local check: 23 unit tests passed; the 19 database tests skip locally because no PostgreSQL server is available. CI supplies the real server.
- Sequential workload: 200 unique + 200 duplicates => exactly 200 predictions, 20.5683 s total.
- Concurrent workload: 4 equipment / 4 producers / 2 consumers, 200 unique + 200 duplicates => 200 original predictions + 211 late revisions, 0 dead jobs, maximum inference attempts 1, 10.4689 s.
- PostgreSQL stop/restart rejected ingestion during outage and recovered pending work; backup restoration matched table counts and model hashes.
- Final measured reports: benchmarks/postgres-final.json, concurrency-final.json and recovery-final.json. Tests and timings are bounded experiments, not production-capacity claims.
- Baseline leakage/batch defects and synthetic-only scientific results are documented in AUDIT and EXPERIMENTS. The browser selector regression and incident-reopening edge case are fixed and verified.

## Blocked/deferred
Independent chronological/industrial validation is blocked by the supplied data. Validated fault hypotheses are not available; the model may report unknown. Production scale/secret-management/RLS/feature-runtime migration work is explicitly deferred in ROADMAP. The full original acceptance list is not represented as complete.

## Exact next action
The implemented checkpoint is verified and ready for review in the draft PR; it is not merged or deployed. To continue development, select a deferred acceptance criterion from ROADMAP. Highest scientific priority: obtain a suitably licensed independent lifecycle/outcome dataset and evaluate a later cohort without tuning on the current final test. Highest engineering priority: retained feature-version runtimes and bounded/paginated replay. Reproduce the existing checks using RESUME_WORK before new changes.

## Follow-up in progress
Migration 004 adds immutable pinned replay inputs, durable progress/leases, cancellation/resume and paginated results. Runtime registry retains causal-v1/v2 and dispatches historical replay by artifact version. New PostgreSQL parity/fencing/isolation tests and golden historical feature tests are being verified. Do not claim this follow-up verified until its CI completes.
