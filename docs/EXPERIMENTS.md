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
