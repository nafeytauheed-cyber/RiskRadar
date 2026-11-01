# ADR 001: PostgreSQL queue and bounded JSON model artifacts

Accepted 2026-11-01. Use one database transaction for each set of durable effects and equipment-level fencing across inference. Avoid a broker until measurements justify another service. Tradeoff: tenant admission locks limit ingestion throughput, and no claim of unbounded scale is made.

Serve a logistic model using JSON rather than executing pickle/joblib contents. Tradeoff: complex offline challengers cannot be promoted without a separately validated serializer/runtime. Training, selection, calibration and final evaluation are explicit offline steps. Never train on API startup.
