# Challenges and decisions

## Local PostgreSQL unavailable — verification moved to CI
- Evidence: this container has neither PostgreSQL nor Docker; package installation failed because server user switching is unsupported.
- Impact: local PostgreSQL tests skip. They are not counted as local passes.
- Decision: execute the integration suite, load workloads, process-death tests and database stop/restart/restore drill against PostgreSQL 16 in GitHub Actions.
- Status: remote verification at 1d63d2c passed all 42 backend tests, both browser tests and all three database experiments. No paid infrastructure or public deployment was created.

## Scientific validity remains bounded by data
- Evidence: supplied CSVs are synthetic, historical units begin together, and old diagnostic rules mirror the original generator. No independent licensed outcome dataset is supplied.
- Impact: no claim of real industrial accuracy, causality or independent chronological generalization.
- Decision: causal-v2 features, equipment-disjoint training/selection/calibration/test, explicit censoring/intervention labels, uncertainty and calibration diagnostics. A different seeded simulator supplies held-out mechanisms, severities and later timestamps as stress evidence only.
- Unresolved: independent later lifecycle cohorts and operational false-alert costs. Input needed before industrial validation: a suitably licensed dataset with operating cycles, failures, maintenance interventions and observable follow-up.

## Model comparison and safe serving
- Evidence: held-out synthetic PR-AUC is 0.709 for logistic and 0.828 for gradient boosting; calibration bins remain uneven.
- Decision: keep the predeclared inspectable JSON logistic serving baseline; do not tune/promote a challenger using the already-inspected final test. Complex models remain offline comparators until a safe runtime and fresh selection/test protocol exist.
- Tradeoff: simpler serving, lower observed test performance than the boosting comparator. This is documented rather than hidden.

## Durable stages and locking
- Feature and inference workers have separate durable phases (migration 003), with the earliest equipment job blocking overtaking.
- Tenant admission uses a no-key-update lock to serialize queue admission without conflicting with foreign-key key-share locks during worker commits.
- Late revisions retain the original target model even after promotion; original observations use the current promoted model.
- Resolution resets hysteresis so reopening requires two new high observations. All these contracts have dedicated real-PostgreSQL tests.

## Browser regression
- d94dda8 passed 41 backend tests and all three database experiments, but one browser test selected the newly added notes panel instead of the provenance panel.
- The selector is now scoped to the provenance details element; the assertion itself remains unchanged. CI run 41381105831 confirms the fix; both browser tests pass.

## Remaining scope
See ROADMAP for explicit scientific blockers and deferred scale/operations work. Current results do not establish sustained-load capacity, replica failover, network-partition safety or production readiness. Replay currently loads its pinned input set in memory. Future incompatible feature schemas require retained executable runtimes; do not promote them into an existing installation without migration support.

## Historical runtimes and bounded replay
Problem/evidence: the prior runner loaded all events/results and committed only at the end; feature-version metadata alone could not execute older semantics. Impact: memory growth, lost progress on crash and historically incorrect feature dispatch. Decision: immutable input membership, fenced page commits and explicit retained runtime modules. Options rejected: adding a broker without measured need, or importing arbitrary model-provided code. Uncertainty: long pinning snapshots, sustained workload behavior and dependency-level reproducibility remain unmeasured. No user input is required for this engineering slice.

Local retraining reproduced numeric parameters within 1e-12, but not byte-for-byte: coefficient/calibration differences were at floating-point rounding scale. Artifact hashes intentionally remain exact; reproducible predictions use the saved immutable artifact, rather than treating numerically close retraining as identical provenance.
