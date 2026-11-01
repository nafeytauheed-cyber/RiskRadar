# Operations

Liveness `/api/health` does not require the database. Readiness `/api/ready` requires connection and migration version. `/api/metrics` requires a query credential and exposes tenant queue/outbox counts. Worker emits JSON event messages, excludes payloads/secrets, handles TERM/INT between jobs; leases recover interrupted jobs. It is one sequential worker by default. More consumers may be started, but equipment serialization remains enforced.

Secrets are environment variables, never committed. API keys are hashed in the database, role-scoped, and device keys are bound to equipment. Hashing high-entropy keys is not a substitute for hashing user passwords; passwords are not supported. Rotate a key by inserting its hash and then deleting the old hash. Production TLS, external secret manager, per-key rate limits and RLS remain deployment hardening work; don't expose this draft publicly.

Migration: `PYTHONPATH=.:backend python -m app.platform.admin migrate`. Explicit migration advisory lock; API never mutates schema at startup. Register model JSON, validate its content hash, then promote with the admin CLI. Rollback is promotion of the previous model ID in audit_events. Historical predictions remain attached to their original artifact.

Backup: `docker compose exec -T db pg_dump -U riskradar -d riskradar -Fc > riskradar.dump`. Store encrypted backups outside the host. Restore into a fresh database with `pg_restore --no-owner --exit-on-error -U riskradar -d RESTORE_DB riskradar.dump`. Never overwrite the live database to test restore. Compare events, prediction/model hashes, migration version and pending jobs after restoration, run readiness and replay, and only then switch services. A restore drill has not yet been executed in this environment.

Outbox: set a trusted NOTIFICATION_URL and run `python -m app.platform.outbox` explicitly. Receiver must honor tenant-qualified Idempotency-Key. A timeout after remote success is ambiguous; duplicates are possible, at most five send attempts per row under normal configuration. Dead jobs/outbox remain queryable. Manual retries need an audited administrative workflow (pending); do not silently delete them.
