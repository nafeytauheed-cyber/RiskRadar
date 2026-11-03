# Audit and baseline

Audited main `4456e04df6e571e310f159bac8c9318804e66d7b` (unchanged from prior review), 2026-11-01.

| Finding | Evidence in original source | Status |
|---|---|---|
| Future leakage | preprocessing.clean interpolate/bfill; engineer_features bfill | Confirmed |
| Batch-dependent score | anomaly.score_anomalies percentiles of scoring batch | Confirmed |
| Fleet-dependent baseline | runner.run baseline_stats(current), current rolling quantiles | Confirmed |
| Unevaluated probabilities | prediction.fit_model trains all histories, no independent partitions/calibrator | Confirmed |
| Invalid labels | build_training_set treats missing failure as negative and post-failure as positive; no lifecycle/censoring | Confirmed |
| Arbitrary composite | risk_score 0.55 probability + 0.30 anomaly + 0.15 hypothesis confidence | Confirmed |
| Unsupported corroboration | root_cause adds 0.2 on similarity agreement | Confirmed |
| Causal/explanation overstatement | root_cause known causal signature, runner Likely Root Cause; explain global importance as contribution_pct | Confirmed |
| Mutable startup models | main lifespan PIPELINE.run; unauthenticated refresh retrains | Confirmed |
| Security | unrestricted CORS; no authentication/tenant ownership | Confirmed |
| Missing verification | recursive repository tree has no tests, CI, benchmarks | Confirmed |

Original source is preserved in git. Baseline executable: `PYTHONPATH=backend python -c 'from app.pipeline import RiskRadarPipeline; RiskRadarPipeline().run()'`. Baseline measurements in benchmarks/baseline.json when successful. Existing data is synthetic, all historical lifecycles start at the same timestamp, and fault rules mirror its generator. It cannot establish independent industrial validity or chronological generalization. No repository license was found; do not relabel third-party data as licensed.
