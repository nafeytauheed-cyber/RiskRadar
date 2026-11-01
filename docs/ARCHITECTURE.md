# Architecture

The v2 API entry point is `backend/app/main.py`. It does not import the legacy pipeline or train. `ml/causal.py` is shared by offline training and durable inference. `ml/artifact.py` accepts only bounded JSON coefficients and explicit scaler/calibrator parameters. PostgreSQL owns durable events and jobs; the worker acquires a short equipment-row lock, increments a fencing token, and releases the transaction before inference. Commit locks the equipment again and checks the current unexpired token before atomically storing snapshots, predictions, evidence, incident changes, outbox and job completion.

The API serializes admissions per tenant to enforce its queue bound, and per equipment to define receipt order. This prioritizes correctness over throughput. Worker execution is at least once. A process dying after commit cannot duplicate effects; expired workers cannot commit after a successor takes its token. Failed jobs retry at most five times, then remain dead for investigation. An earlier pending retry blocks subsequent equipment jobs. No broker is required.

Replay pins a repeatable-read input manifest, then computes without database locks. It writes in a distinct content-addressed scope. There is no incident or outbox dependency in its compute path. Same manifest is idempotent. Arrival replay reconstructs per-observation decisions, not the exact timing of worker crashes/operator changes; original live predictions remain authoritative for those historical actions.

Model registry entries are content-addressed. Promotion is explicit and audited; rollback promotes a prior ID. In-flight jobs retain the model loaded during preparation. Registry validation checks content hash again before scoring. The initial serving artifact is logistic only; gradient boosting/IsolationForest are offline comparators, not falsely advertised as deployable artifacts.

Legacy `backend/app/pipeline/` and React display components remain for reference/migration, but are not connected to v2 serving. Their historical claims are not v2 outputs. No LLM or custom ForceModel dependency is introduced.
