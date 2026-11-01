# RiskRadar — replayable failure investigations (v2 draft)

Authenticated telemetry ingestion, causal feature snapshots, durable prediction processing, append-only revisions, incident investigation and isolated model replay. **Research platform in development, not a validated industrial safety system.** The committed model is evaluated only on this repository's synthetic histories. See [current state](docs/PROJECT_STATE.md), [audit](docs/AUDIT.md), [experiments](docs/EXPERIMENTS.md) and [unfinished work](docs/ROADMAP.md).

## Local setup

Python 3.12, Node 20 and Docker Compose. No cloud resources needed. The DB/API/worker memory limits total 2 GiB; frontend runs separately. These are configured limits, not a measured 8 GB laptop benchmark.

```bash
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_hex(24))')"
export RISKRADAR_API_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up -d db
docker compose run --rm admin migrate
docker compose run --rm admin bootstrap --tenant demo --equipment degradation --lifecycle original
docker compose run --rm admin register benchmarks/scientific/model.json
# Copy the returned content hash into MODEL_ID:
export MODEL_ID=73b6bac514fb3290239c21b452e926c4dce6ce70077dfaac96e62763af09f0fb
docker compose run --rm admin promote --tenant demo --model "$MODEL_ID"
docker compose up -d api worker
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open localhost:5173 and enter the API key (held only in page memory). Provision devices separately through the database/admin extension; never embed admin secrets in frontend bundles. CORS permits only the configured local origin. API and database ports bind loopback. Notification delivery is intentionally not started by Compose.

## Train, test and replay

```bash
python -m pip install -r requirements-dev.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m ml.evaluate --output experiments/local
python -m pytest -q
# For real PostgreSQL tests use an EMPTY, DISPOSABLE database:
export DATABASE_URL='postgresql://USER:PASSWORD@localhost:5432/riskradar_test'
export RISKRADAR_TEST_DATABASE=1
PYTHONPATH=.:backend python -m pytest -q tests/test_postgres.py
# Against your demo database (unset RISKRADAR_TEST_DATABASE afterwards):
PYTHONPATH=.:backend python -m app.platform.replay --tenant demo --models "$MODEL_ID" --mode arrival
PYTHONPATH=.:backend python -m app.platform.replay --tenant demo --models "$MODEL_ID" --mode corrected
python -m simulator.generate --seed 42 --output experiments/scenario
```

Telemetry contract and ordering rules: [DATA_CONTRACTS](docs/DATA_CONTRACTS.md). Hidden simulator outcomes are written separately and never consumed by inference. Simulator output uses epoch seconds and includes a simulated arrival timestamp; the HTTP API requires ISO observed_at and rejects caller-supplied received_at. Use the demo feeder below for HTTP ingestion.

## Demo walkthrough

Run `PYTHONPATH=.:backend python -m simulator.feed --url http://localhost:8000` with RISKRADAR_API_KEY set. It sends 20 recent degradation observations to the provisioned demo equipment, then an identical duplicate. Refresh the UI, inspect quality/warmup, probability, evidence IDs, input cutoffs and model hash. Use the two replay commands above and compare results in the UI. No real failure prediction is established by this demo.

## Operations and continuity

See [operations](docs/OPERATIONS.md), [architecture](docs/ARCHITECTURE.md), [learning guide](docs/LEARNING_GUIDE.md), and [resume instructions](docs/RESUME_WORK.md). Legacy pipeline/components remain disconnected for reference; do not run the old pipeline as a validated service. No paid resource, public deployment or merge is part of this draft.
