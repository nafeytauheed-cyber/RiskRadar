# Experiments

## Baseline
`benchmarks/baseline.json`: original commit 4456e04, 14 equipment, 15.015 seconds pipeline run. Same observation anomaly score: 22.7045 in batch, 0 alone. Earliest temperature rolling mean: 64.8267 with full history, 0 with one-row prefix. These demonstrate leakage and batch dependence, not predictive accuracy.

## Offline evaluation
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m ml.evaluate --output benchmarks/scientific`
Full observed outputs, seeds, split manifests, CSV hashes, environment and runtime are in `benchmarks/scientific/results.json`. Exported `model.json` is synthetic-research-only. Equipment-disjoint train/selection/calibration/test partitions; final comparisons share test rows. No external validation or chronological-generalization claim.

## Contract tests
`OPENBLAS_NUM_THREADS=1 python -m pytest -q`. PostgreSQL tests require DATABASE_URL and RISKRADAR_TEST_DATABASE=1. Skips are not verification. CI executes on PostgreSQL 16 and publishes evidence.

## Load/failure experiment
`PYTHONPATH=.:backend python -m benchmarks.load --events 200 --output benchmarks/postgres-load.json` against an explicitly disposable database. Sequential producer, one equipment, duplicate every event, repeat finish after commit to model acknowledgment loss. Measures both ingestion and processing wall time, p50/p95 ingestion-pair latency and Python process RSS. This is not a capacity or network-partition test. Results must be present before citing numbers.

## First remote verification (879878e)
[CI run 41324963549](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41324963549): 28 passed, including seven real PostgreSQL integration tests; frontend build passed. PostgreSQL 16.15, Python 3.12.15, Ubuntu runner with 4 CPUs. `benchmarks/postgres-initial.json` contains the exact extracted load output and source commit: 200 events + 200 duplicates => 200 predictions; 12.7207 seconds total; ingestion-pair p95 26.4549 ms; peak Python process RSS 74,776 KiB. This result applies to that checkpoint, not automatically to later code.

## Additional evaluation
`python -m ml.stress` writes seeded held-out-mechanism stress measurements to benchmarks/stress.json. This uses later synthetic timestamps and a distinct generator; it is NOT independent real-world chronological validation. The final model now uses causal-v2, with a maximum history age as well as maximum fill age. Re-evaluation records its changed hash. Exported runtime probabilities are checked against sklearn probabilities at 1e-12 tolerance. Results also include selective-error/coverage and incident grouping reduction/delay under a no-operator-resolution assumption.

## Second remote verification (6e19d5d)
[CI run 41325496137](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41325496137): 35 passed including 12 PostgreSQL integration tests, frontend build passed, load and restart/restore drills passed. `benchmarks/postgres-second.json` and `benchmarks/recovery-second.json` preserve exact outputs. The stop/restart drill rejected ingestion during outage and recovered the pending job; backup restore matched event/job/prediction/model/outbox/audit table counts and model hashes. It does not establish multi-node failover safety.

## Reliability diagram
`python -m ml.plot_reliability` (requires matplotlib) renders `benchmarks/scientific/reliability.svg` from observed bins, shown with sample counts. Calibration is fitted independently but reliability remains uneven, especially in sparsely populated high-probability bins. Do not describe the probabilities as industrially validated.

## Third remote verification (75767a4)
[CI run 41325921043](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41325921043): 38 backend tests passed (including real PostgreSQL stages), 2 Chromium browser tests passed, frontend build and database recovery drill passed. The two-stage load experiment completed in 21.1493 seconds for 200 unique + 200 duplicate submissions. Later bounded-query/locking improvements require their own run. Browser tests exercise login, quality/provenance and arrival/corrected replay navigation with real API/database fixtures.

## Fourth remote verification (d94dda8)
[CI run 41380709807](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41380709807): 41 backend tests passed; frontend build passed. All three database experiments passed. One browser test failed because a broad selector matched the new investigation-notes panel rather than provenance; the follow-up commit scopes that selector and retains both provenance assertions.

- `benchmarks/postgres-fourth.json`: 200 unique + 200 duplicate submissions, exactly 200 original predictions, 20.5354 s total, ingestion-pair p95 23.5297 ms. Runner: 4 vCPUs, AMD EPYC 7763, about 16 GiB reported host memory; Python process peak RSS 73,524 KiB. These are runner measurements, not an 8 GB laptop certification.
- `benchmarks/concurrency-fourth.json`: four equipment, four producer threads, two consumers, seeded shuffled five-cycle blocks, 200 unique + 200 duplicate submissions; 200 originals and 211 append-only late revisions, zero dead jobs, maximum inference attempts 1, 10.3371 s elapsed. Revision count depends on actual arrival/interleaving; input seed and contract assertions are reproducible, wall-clock scheduling is not deterministic.
- `benchmarks/recovery-fourth.json`: database stop rejected ingestion, restart recovered its pending job, repeat ingestion remained a duplicate, and backup restoration preserved table counts/model hashes. Single-node drill only.

## Final implemented checkpoint (1d63d2c)
[CI run 41381105831](https://github.com/nafeytauheed-cyber/RiskRadar/actions/runs/41381105831): **42 backend tests passed in 7.74 s; 2 Chromium browser tests passed in 3.8 s; production frontend build and all database experiments passed.** This includes the incident-reopening fix and corrected provenance-panel selector.

Exact machine-readable evidence:
- `postgres-final.json`: 200 unique + 200 duplicate submissions => 200 predictions; 20.5683 s total; ingestion-pair p95 22.1772 ms; process RSS 73,692 KiB.
- `concurrency-final.json`: four equipment/four producers/two consumers, seeded shuffled arrivals; 200 originals plus 211 appended late revisions; zero dead jobs, maximum inference attempts 1; 10.4689 s.
- `recovery-final.json`: unavailable database rejected ingestion, restart recovered a pending job, duplicates remained idempotent, and restored database counts/model hashes matched.

Hardware/configuration is recorded with the sequential report: 4 visible vCPUs, AMD EPYC 7763 host model, ~16 GiB reported host memory, PostgreSQL 16, Python 3.12.15. These short experiments do not certify an 8 GB laptop, sustained capacity, replicas or partition tolerance. Revisions reflect actual asynchronous arrival interleavings; determinism is asserted for replay of a pinned persisted manifest, not thread scheduling.
