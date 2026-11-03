# Project state

Branch: `upgrade/replayable-investigations`
Draft PR: https://github.com/nafeytauheed-cyber/RiskRadar/pull/1
Original base: `4456e04df6e571e310f159bac8c9318804e66d7b`
Latest implementation published: `f66e7bedc9d2fbab71ca34f852eba089ecd122cd` (bounded replay and retained feature runtimes).

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
Independent chronological/industrial validation is blocked by the supplied data. Validated fault hypotheses are not available; the model may report unknown. Production scale/secret-management/RLS/general schema migration work is explicitly deferred in ROADMAP. The full original acceptance list is not represented as complete.

## Exact next action
Replay follow-up implementation `f66e7bedc9d2fbab71ca34f852eba089ecd122cd` passed [CI 41387576979](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41387576979): 50 backend tests (25 real PostgreSQL), three browser tests, frontend build, offline evaluation and four database experiments. Local verification: 25 unit tests passed; 25 PostgreSQL tests skipped without a local server.

Migration 004 adds immutable pinned replay inputs, durable page progress/leases, cancellation/resume and paginated results. Registry retains causal-v1/v2 and dispatches historical replay by artifact version; golden fixtures preserve historical features. The 500-event replay completed 20 pages of 25 in 2.9164 s with 1,022,493 peak traced Python bytes; cancellation/resume and no live incident/outbox effects were verified. This is a bounded experiment, not capacity certification.

Next engineering work: measure larger input pinning snapshots and sustained contention, or implement the audited dead-letter review workflow. Scientific priority remains a suitably licensed independent lifecycle/outcome dataset. Follow RESUME_WORK; preserve historical modules and never weaken fingerprint checks. The branch remains a draft, not merged or deployed.
