# Challenges

## Real PostgreSQL runtime
- Evidence: no PostgreSQL or Docker installed; apt installation failed on setgroups/setuid in this restricted container.
- Impact: local locking/transaction tests skip; local claims must exclude them.
- Options: real service in GitHub CI, developer Docker Compose, or provisioned disposable DB.
- Decision: add PostgreSQL 16 GitHub service and strict integration tests; inspect results before claiming verification. No paid resource requested.
- Uncertainty: remote workflow execution availability.

## Scientific evidence scope
- Evidence: repository is synthetic; historical units share their initial date and faults mirror diagnostic rules; no license supplied.
- Impact: this cannot establish chronological generalization or real industrial accuracy.
- Decision: separate equipment partitions, selection/calibration/final test, cluster bootstrap, no causal fault-label claims; defer industrial validation until a suitable outcome dataset exists.
- Input eventually needed: permission and provenance/license for an independently collected lifecycle/outcome dataset, plus operational false-alert costs.

## Scope and continuity
- Decisions: serve logistic JSON first; keep complex models offline; no LLM/ForceModel dependency; preserve original components as disconnected legacy reference. Feature/inference phases share one worker process with a pure feature boundary, not two separately queued worker services yet.
- Remaining: roadmap explicitly tracks unfinished requirements; do not infer completeness from the number of files or tables.
