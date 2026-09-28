---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 07
subsystem: engine-measurement
tags: [gate-run, stacked-arms, throughput, move-quality, stop-rule, calibration, attribution]

requires:
  - phase: 225-03
    provides: "accept-rule.md (A0 = 1b5313b96), d02-allowance.md (W = 0.09)"
  - phase: 225-04
    provides: "A2 = a9d5113ef (item 2, round underfill)"
  - phase: 225-05
    provides: "A21 = 27beff12f (item 1, root comparability guard)"
  - phase: 225-06
    provides: "FINAL = fd8d9200f (item 3, findability fallback)"
provides:
  - "reports/data/engine-search-fixes-225/{a0,a2,a21,final}/: every judged TSV slot in the accept-rule layout, plus a2/mq-off-rerun"
  - "reports/data/engine-search-fixes-225/calibration/: verdict-a21-vs-july.json (primary) and the decision-branch set (a0/a2 cells JSON, a0-vs-july, a2-vs-july, a2-vs-a0, a21-vs-a2)"
  - "reports/data/sweep-225-{a21,a0,a2}-{human1100,light1300,light1900,deep1500,deep2300}/: 15 calibration ledgers (TSVs only)"
  - "scripts/engine_search_fixes_verdict.py: reruns subcommand bug fix (reads the rerun dir like gates does)"
affects: [225-08]

actuals:
  tasks: 3
  commits: 6
  plan_head_before: 7acb340d615cd47faaf654cd20dc7e1d288129eb

tech-stack:
  added: []
  patterns:
    - "Wall-clock arms run alone under one sequential setsid driver with the local remote eval worker SIGSTOPped (user-approved), resumed before the node-deterministic runs"
    - "Arm output copied back into the phase worktree and committed before any arm worktree was removed; removal gated on git ls-files for every arm-side file"

key-files:
  created:
    - reports/data/engine-search-fixes-225/calibration/verdict-a21-vs-july.json
  modified:
    - scripts/engine_search_fixes_verdict.py
    - tests/scripts/test_engine_search_fixes_verdict.py

key-decisions:
  - "Task 1 (lock the pre-registration): lock-and-run. Chosen by the orchestrator because the user asked to defer all questions until after implementation and delegated every gray area in CONTEXT.md; no gate data existed and the verdict/allowance tests were green at lock time."
  - "reruns bug fixed after gate data existed: required_reruns() passed None as the rerun rows, so a confirmed flip stayed listed forever. Fixed to read the optional rerun dir exactly like gates; no constant, threshold or gate decision logic changed (commit d12c4b899, mutation-checked)."

requirements-completed: []

duration: ~17h wall (mostly calibration sweeps)
completed: 2026-09-28
---

# Phase 225 Plan 07: Gate run Summary

**The pre-registered gate ran end to end. Throughput, stop rule and MQ-1 pass; MQ-2 fails on one fixture row (confirmed by a fresh-process rerun); calibration fails for A21 and the decision branch shows the unchanged baseline A0 fails against the July curves too. Verdict: item 2 hold, item 1 hold, item 3 independent.**

## Arms (resolved by the accept-rule lookups, content assertions all passed)

| Arm | SHA |
|---|---|
| A0 | 1b5313b9648d9be1116bb519a1d51e8627f3ec15 |
| A2 | a9d5113efed9270d02692c9b97e87508ecc414b2 |
| A21 | 27beff12fb22d009b1f30c2b5552ba9cba4aad0e |
| FINAL | fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d |

Content assertions: tooling diff (scripts, bin, frontend/package*.json) empty between every arm pair; A0 engine identical to the merge-base; A0->A2, A2->A21, A21->FINAL engine diffs limited to the files the rule lists. All four arms passed the harness self-test after `npm ci`.

## Task 1: lock

lock-and-run (see key-decisions). Verified before the first gate TSV: no a0/a2/a21/final/calibration dir, 33/33 verdict+allowance tests green, accept-rule.md and the twin clean in git.

## Task 2: wall-clock and move-quality arms

- Wall-clock driver (stop a0/a2/a21, throughput a0-50, a2-50, a0-400, a2-400) ran 10:38-12:16 on 2026-09-27 on an idle box (95% idle at launch; the local remote_eval_worker was SIGSTOPped with the user's approval and resumed right after). One short ledger-schema check (a few seconds) ran during a2-400.
- Move quality a0 off, a2 off, a2 on, a21 on, final off ran 12:16-12:25 (node-deterministic, overlapping the A21 calibration as the rule allows).
- `reruns` listed `a2 off`; the fresh-process rerun into a2/mq-off-rerun reproduced the flip (row cBFTV: A0 picks e4c6, es 0.975 pass; A2 picks e2g4, es 0.405 regression; the other 11 rows identical).

| Criterion | Result |
|---|---|
| T-50 | PASS (A2/A0 ladder wall ratio 0.9450) |
| T-400 | PASS (0.9529) |
| MQ-2 | FAIL (A2 stop-off 5 regressions vs A0 4, flip confirmed) |
| S1 | PASS (A21 max wall 8,343 ms) |
| S2 | PASS (A21 early stops 10 vs A2 10) |
| MQ-1 | PASS (A21 stop-on 4 vs A2 4) |

## Task 3: calibration

A21 five cells ran 12:16-18:55 under bin/preset-supervisor.sh with the pinned anchors (no crashes). Primary verdict **fails**: Maia pooled -97.9 (se 41, threshold 85), SF pooled -40.0 (within 50), null controls within threshold, shape guard on 1500/0.5 (Maia -262). `branch` said **decision**, so A0 and A2 ran concurrently 18:56-03:54 (ten cells, no crashes).

| Verdict | Result | Maia pooled | SF pooled | Shape guard |
|---|---|---|---|---|
| a21-vs-july | fails | -97.9 (se 41) | -40.0 (se 33) | 1500/0.5 |
| a0-vs-july | fails | -71.9 (se 40) | -81.4 (se 32) | 1500/0.5 |
| a2-vs-july | void | -73.5 (se 42) | +29.2 (se 32) | 1500/0.5 |
| a2-vs-a0 | fails | +4.0 (se 38) | +117.2 (se 36) | none |
| a21-vs-a2 | fails | -30.5 (se 38) | -67.5 (se 36) | none |

The unchanged baseline (A0) already fails against the July-21 curves with the same deep1500 shape-guard cell, so the verdict script reports `baseline_drift: true`.

## Final gate status

`scripts/engine_search_fixes_verdict.py gates` exits 0, status complete: ITEM2 hold, ITEM1 hold, ITEM3 independent. No refit and no recalibration was started (D-14).

## Deviations

1. **reruns bug fix (tooling, after data).** See key-decisions. Committed as `fix(225-07)` with a regression test; reverting the fix makes the new test fail.
2. **Calibration ledgers force-added.** `reports/data/sweep-*/` is gitignored; the Phase 199 ledgers are force-added, so the Phase 225 ledgers follow that precedent (`git add -f`, TSVs only, no logs).
3. **Phase worktree.** The whole phase ran in `../flawchess-225` (branch gsd/phase-225-...) instead of the main checkout because another session held uncommitted work there; arm worktrees were `../flawchess-225-{a0,a2,a21,final}` and are removed.

## Self-Check: PASSED
