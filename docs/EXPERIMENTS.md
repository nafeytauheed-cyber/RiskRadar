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
