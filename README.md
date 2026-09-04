# RiskRadar — AI Safety Investigator (PS 04)

RiskRadar analyzes industrial equipment telemetry, maintenance logs, and
historical failure records to answer four questions an investigator would
ask after an incident — before it happens:

> **What is going wrong, why is it happening, how serious is the risk, and
> what should we do?**

It does this through explicit **failure-chain reasoning**:

```
Weak Signals  →  Emerging Pattern  →  Likely Root Cause  →  Predicted Failure
   →  Safety Risk Score  →  Explainable Evidence  →  Recommended Intervention
```

No IoT, no hardware. All data is simulated and shipped with the repo, so the
whole system runs end-to-end on a laptop with no external services.

---

## What it does

- **Data pipeline**: cleans and engineers rolling-window features (mean, std,
  trend slope) from raw multi-sensor equipment telemetry.
- **Anomaly detection**: an Isolation Forest trained on healthy historical
  telemetry flags multivariate deviations; per-sensor z-scores give
  human-readable evidence.
- **Failure-risk prediction**: a Gradient Boosting classifier trained on a
  historical run-to-failure fleet (labeled by remaining-useful-life) predicts
  the probability that a currently-monitored unit fails within 30 cycles.
- **Historical failure similarity**: a nearest-neighbor search over failure
  "signatures" surfaces the most similar past incidents and how they were
  resolved.
- **Root-cause reasoning engine**: rule-based logic combines sensor
  deviation direction + magnitude + trend + similarity-search agreement into
  ranked root-cause hypotheses (bearing wear, lubrication breakdown, seal
  leak, blockage, electrical overload, misalignment) — each with the actual
  evidence chain behind it.
- **Composite risk score**: blends failure probability, anomaly severity,
  root-cause confidence, and equipment criticality into a 0–100 score with a
  Low/Medium/High/Critical severity band.
- **Recommended actions**: a knowledge base maps root cause + severity to
  prioritized immediate / short-term / monitoring actions.
- **Automated report generation**: a narrative "investigation report" per
  equipment unit, downloadable as PDF straight from the browser.

## Architecture

```
RiskRadar/
├── backend/                 FastAPI + ML pipeline (Python)
│   └── app/
│       ├── data_gen.py      synthetic dataset generator
│       ├── pipeline/        preprocessing, anomaly, prediction, similarity,
│       │                    root-cause engine, risk scoring, explainability,
│       │                    recommendations, timeline, report generation
│       ├── data/            generated CSVs (created on first run)
│       └── main.py          REST API
└── frontend/                React + Vite + Tailwind dashboard
    └── src/
        ├── components/      Dashboard, EquipmentDetail, ReportView, ...
        └── api.js           talks to the backend REST API
```

The pipeline trains at API startup (well under a second on this dataset size)
and results are cached in memory — no database needed.

## Prerequisites

- Python 3.10+
- Node.js 18+

## One-click launch (Windows)

Double-click **`start.bat`** in the project root. It will (on first run) create
the backend virtual environment, install both backend and frontend
dependencies, then open two windows — one running the API, one running the
dashboard — and launch your browser to `http://localhost:5173` automatically.
Close those two windows to stop RiskRadar. Subsequent runs skip the install
steps and start in a few seconds.

## Setup & Run (Windows / PowerShell)

**1. Backend**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.data_gen        # generates the sample dataset (first time only)
uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://127.0.0.1:8000` (docs at `/docs`). Dataset
generation also runs automatically on first API startup if the CSVs are
missing, so `python -m app.data_gen` is optional.

**2. Frontend** (in a second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api/*` to the backend
on port 8000, so no CORS configuration is needed.

## Setup & Run (macOS / Linux / Git Bash)

```bash
cd backend
python -m venv venv
source venv/bin/activate      # or: source venv/Scripts/activate on Git Bash/Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## Using the dashboard

- **Fleet Overview** (`/`): overall system risk, KPI counts, and every piece
  of equipment ranked by risk with a severity filter.
- **Equipment Investigation** (`/equipment/:id`): individual risk score,
  the failure-chain visualization, sensor trend chart, explainable evidence,
  event timeline, similar historical incidents, and recommended actions.
- **Generate Investigation Report**: from an equipment page, produces a
  formatted narrative report — click "Download / Print PDF" to save it.

## Regenerating / resetting the sample data

```bash
cd backend
python -m app.data_gen
```

This overwrites the CSVs in `backend/app/data/` with a fresh random (but
seeded/reproducible) fleet. Restart the backend afterward (or call
`POST /api/refresh`) to retrain the pipeline on the new data.

## Notes on the ML design

- The **historical fleet** (`sensor_readings_history.csv` +
  `failure_history.csv`) contains completed run-to-failure lifecycles with
  known outcomes — used purely for training the anomaly/failure models and
  building the similarity library.
- The **current fleet** (`sensor_readings.csv` + `equipment_master.csv`) is
  what the app actually investigates: ongoing, mid-lifecycle units, most of
  which are silently developing (but have not reached) one of the fault
  patterns. The app has no access to ground-truth labels for this fleet — it
  has to (re)discover risk from raw telemetry, the same way it would with
  real plant data.
