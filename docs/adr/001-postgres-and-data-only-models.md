# ADR 001: PostgreSQL queue and bounded JSON model artifacts

Accepted 2026-11-01. Use one database transaction for each set of durable effects and equipment-level fencing across inference. Avoid a broker until measurements justify another service. Tradeoff: tenant admission locks limit ingestion throughput, and no claim of unbounded scale is made.

Serve a logistic model using JSON rather than executing pickle/joblib contents. Tradeoff: complex offline challengers cannot be promoted without a separately validated serializer/runtime. Training, selection, calibration and final evaluation are explicit offline steps. Never train on API startup.

Evaluation outcome: the gradient-boosting comparator outperformed the predeclared logistic serving baseline on the held-out synthetic test (see results.json). We do not select or tune a new model using that final test. Logistic remains the first serving format for inspectability and low loading risk; a gradient-boosting serving adapter requires a new selection/calibration protocol and another untouched test cohort. This is a limitation, not a claim that logistic is the most accurate model.

Admission uses `FOR NO KEY UPDATE` on the tenant row, allowing foreign-key key-share locks during concurrent worker commits. Using `FOR UPDATE` there would unnecessarily conflict with inserts referencing the tenant and could create an admission/equipment lock cycle. Per-equipment raw reads are bounded to the affected twenty-cycle neighborhood; target snapshots still use their own ten-cycle/age cutoffs.
