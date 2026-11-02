# Resume instructions

1. Checkout `upgrade/replayable-investigations` from GitHub. Read PROJECT_STATE, CHALLENGES, EXPERIMENTS and ROADMAP; inspect PR #1 and its current head/checks before editing. Preserve unrelated changes.
2. Install `python -m pip install -r requirements-dev.txt`; run `OPENBLAS_NUM_THREADS=1 python -m pytest -q`. No DATABASE_URL means PostgreSQL tests skip, not pass.
3. For real PostgreSQL tests use a fresh disposable PostgreSQL 16 database; set DATABASE_URL, RISKRADAR_TEST_DATABASE=1 and PYTHONPATH=.:backend. `python -m pytest -q tests/test_postgres.py` truncates test tables, so never point it at real data.
4. Reproduce experiments with `python -m benchmarks.load --events 200 --output benchmarks/postgres-load.json` and `python -m benchmarks.concurrency`. The recovery drill additionally requires the disposable Docker service container ID; follow .github/workflows/verify.yml.
5. Reproduce science with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m ml.evaluate --output experiments/reproduction`, `python -m ml.stress`, and `python -m ml.plot_reliability`. Do not retune using the reported final test.
6. Run `npm ci --prefix frontend` and `npm run build --prefix frontend`. Browser tests require the API/DB fixture; follow the workflow's `benchmarks.ui_fixture` and Playwright steps.
7. First resolve any failing current-head CI without weakening assertions. Then address scientific blockers using suitable independent data, or pick a specific deferred engineering acceptance criterion from ROADMAP.
8. Record actual commands/results, update continuity docs, and push another coherent checkpoint to the same draft PR. No merge, public deployment or paid resources are authorized.

The local scratch git history may contain equivalent connector-created commits with different SHAs. Compare trees and use a fresh checkout of the remote branch if necessary; never force-push to reconcile those local aliases.
