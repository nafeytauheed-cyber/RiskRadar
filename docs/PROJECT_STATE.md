# Project state

Branch: `upgrade/replayable-investigations`; base: `4456e04df6e571e310f159bac8c9318804e66d7b`.

Implemented: v2 causal/offline science pipeline, JSON logistic artifact, PostgreSQL schema/API/worker/outbox, isolated replay, incident transitions, investigation UI, Compose and CI. Baseline and offline evaluation executed. Local tests and CI are being verified; do not yet claim database correctness.

Blocked locally: PostgreSQL installation requires unsupported user switching. Pending requirements are enumerated in ROADMAP; the whole requested platform is not yet complete.

Exact next action: run local unit suite/frontend build, push checkpoint, inspect PostgreSQL CI and repair any failures before finalizing evidence.

Second milestone in progress: first remote CI at 879878e passed 28 tests and a 200-event duplicate experiment; evidence is committed in benchmarks/postgres-initial.json. Added causal-v2 idle-gap behavior, immutable database records, explicit maintenance boundary API, clock-order validation, process-death/outage/outbox tests, and restart/restore drill. Local latest unit result: 23 passed / 12 PostgreSQL skipped. Next action: push this milestone and verify its own CI (first checkpoint success does not cover new changes).
