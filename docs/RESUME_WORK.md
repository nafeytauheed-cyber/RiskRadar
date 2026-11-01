# Resume instructions

1. Checkout `upgrade/replayable-investigations`; inspect `git status`, PR and current CI before edits.
2. Read PROJECT_STATE, CHALLENGES, EXPERIMENTS and ROADMAP. Do not repeat old accuracy claims.
3. Install requirements-dev.txt; run `OPENBLAS_NUM_THREADS=1 python -m pytest -q`.
4. Use a disposable PostgreSQL 16 database; set DATABASE_URL, RISKRADAR_TEST_DATABASE=1 and PYTHONPATH=.:backend, then run tests and `python -m benchmarks.load --events 200 --output benchmarks/postgres-load.json`.
5. Resolve failing tests without weakening their assertions. Persist exact commands/environment/results.
6. Complete pending roadmap items as tested vertical slices, especially lifecycle/intervention API, chronological/held-out evaluation, and restart/outage drills.
7. Update state/docs and push a coherent checkpoint to the same draft PR. Never merge/deploy implicitly.
