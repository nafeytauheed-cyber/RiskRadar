# Learning guide

1. Read `benchmarks/baseline.json` beside `docs/AUDIT.md`: changing a future row or the scoring fleet must not change an earlier saved decision.
2. `ml/causal.py:snapshot`: observation cutoff says what the sensor had observed; arrival cutoff says what the service knew. Walk through `tests/test_science.py:test_late_observation_revises_not_original`.
3. `ml/causal.py:label`: follow-up and interventions decide whether a negative is actually observable. Missing outcomes do not mean healthy.
4. `ml/evaluate.py`: each equipment belongs to one partition. Selection tunes C; calibration learns a probability map; only final testing measures held-out outcomes. Inspect reliability bins as well as PR-AUC.
5. `platform/service.py:ingest`: the event and its job either both commit or neither does. A digest distinguishes a retry from conflicting content.
6. `claim`, `prepare`, `finish`: a lease does not prove ownership forever. The fencing token prevents a slow/crashed old worker from writing after replacement.
7. `update_incident` and `outbox.py`: database effects are atomic; external delivery cannot be made exactly once by a local transaction. The recipient must deduplicate.
8. `platform/replay.py`: same pinned inputs can score different artifacts while leaving live incidents alone. Compare hashes in the UI.
9. `tests/test_postgres.py`: actual PostgreSQL proves behavior mocks cannot prove. A skipped test is not a passed guarantee.
