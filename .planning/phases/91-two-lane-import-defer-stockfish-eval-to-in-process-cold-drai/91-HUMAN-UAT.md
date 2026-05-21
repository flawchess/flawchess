---
status: partial
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
source:
  - 91-VERIFICATION.md
  - 91-08-SUMMARY.md (deferred Task 8.2 stress-test execution)
started: 2026-05-21T00:00:00Z
updated: 2026-05-21T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. EvalCoverageHeader renders during a live import
expected: After triggering an import on the dev DB, navigate to Endgames Stats tab, Openings Stats subtab, Openings Explorer subtab, or Openings Insights subtab. An amber-tinted progress banner ("Stockfish analysis in progress: X% complete (N games still pending)") with an animated Cpu icon and a progress bar appears at the top of the content. It disappears at 100% coverage. (Operator already surfaced this gap once during local testing — the polish commit `fix(91): make eval-coverage banner visible…` should resolve it. Re-verify.)
result: [pending]

### 2. Per-metric pending caveat appears with warning icon + sample size
expected: While imports are in progress, hovering or tapping any Stockfish-dependent metric popover (Score Gap in EndgameMetricCard, Conversion in EndgameTypeCard, Eval Confidence in opening findings, etc.) shows an amber-tinted caveat with an AlertTriangle icon, reading "Based on N currently-evaluated games. Stockfish is still analysing K more across your library — this metric may shift as analysis completes." The caveat is absent after drain completes.
result: [pending]

### 3. Backend RSS stays flat during imports
expected: Run an import while watching backend memory (`/proc/<pid>/status` or `docker stats` if containerised) and Postgres anon+shmem. RSS plateaus rather than climbing in step with progress. No Postgres OOM-kill occurs. The absence of eval work in the hot lane is the key behavioural signal — the `TestHotLaneNoEvalCalls` CI guard backs this structurally.
result: [pending]

### 4. Cold drain liveness
expected: After an import finishes, the drain coroutine processes pending evals over minutes. `GET /api/imports/eval-coverage` returns increasing `pct_complete` and decreasing `pending_count` over time. The EvalCoverageHeader updates every ~10s and eventually disappears at 100%. No Sentry events with `source=eval_drain` during normal operation.
result: [pending]

### 5. Plan 91-08 Task 8.2: dual-20k stress harness execution (deferred, opportunistic)
expected: `scripts/measure_dual_import_rss.py` runs against a dev backend, triggers two concurrent 20k-game imports, polls Postgres + RSS + swap + coverage every 30s, and exits with the acceptance summary. Operator decision (2026-05-21): the planned procedure required resetting the dev DB and will not be executed as written. The harness ships as a deliverable; if formal acceptance verification is ever wanted, it can be run against the existing dev DB by importing to a fresh test user. Does NOT block phase completion.
result: [skipped — operator decision]

## Summary

total: 5
passed: 0
issues: 0
pending: 4
skipped: 1
blocked: 0

## Gaps
