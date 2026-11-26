---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
plan: 02
subsystem: scripts/blunder-check-calibration
tags: [calibration, pure-functions, hazard-model, findability, SEED-261108-dk0]
requires: []
provides:
  - "scripts/blunder_check/metrics.py: pure calibration math (miss classification, Good/band judgement, findability, hazard window fit, herring windows, supply cap, AUC, quartiles, flaw control)"
affects: [248-04, 248-05]
tech-stack:
  added: []
  patterns: ["private import of flaw-pipeline internals (INACCURACY_DROP, _MoveEntry, _SEVERITY_INT) so thresholds are never redefined"]
key-files:
  created:
    - scripts/blunder_check/__init__.py
    - scripts/blunder_check/metrics.py
    - tests/scripts/test_blunder_check_metrics.py
  modified: []
decisions:
  - "ES values are read from the classifier's own _run_all_moves_pass output; es_ref = 1 - all_moves[p-1][2], es_played = all_moves[p][3], pre-move ES = all_moves[p][2]"
  - "P(L >= k) in the hazard model is the share of WINDOW_LENGTHS that are >= k (uniform over lengths), which reproduces the D-16 numbers"
  - "flaw_control total is the union of plies carrying a mistake/blunder on either side; inaccuracies ignored on the recomputed side"
metrics:
  duration: "~15 min"
  completed: "2026-11-09"
status: complete
commits: 2
plan_head_before: 974fb91803fdf91dfca2042aa8ae5481a76ca632
plan_head_after: 8eb68152d
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
---

# Phase 248 Plan 02: Blunder-check calibration metrics Summary

Pure, tested module for the D-13..D-16 and D-23 calibration rules: miss classification with an inclusive `INACCURACY_DROP` boundary, Good/in-band judgement, Maia findability on (prob, rank) pairs, hazard-weighted window fit, disjoint herring windows, the miss-share supply cap, per-user supply estimate, AUC and quartiles, and a stored-vs-recomputed flaw control.

Note on `commits`: the `rev-list` count from `plan_head_before` to HEAD also contains plan 248-01's commit (same worktree, concurrent executor); this plan's own commits are `1ebbaa883` (Task 1) and `8eb68152d` (Task 2).

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Tracer: miss case and window fit from real per-ply evals through `_run_all_moves_pass` | 1ebbaa883 |
| 2 | Findability grid, buckets, herring windows, supply cap, estimates, AUC, flaw control | 8eb68152d |

## Verification

- `uv run pytest tests/scripts/test_blunder_check_metrics.py`: 31 passed (acceptance asked for >= 14).
- `uv run ruff check` / `ruff format --check` on own files: clean. `uv run ty check app/ tests/ scripts/`: All checks passed. `check_function_size.py scripts/blunder_check --fail-over-depth 4`: no breaches.
- Tracer runs the real `_run_all_moves_pass` on a synthetic game (white user holds +100 cp, black blunders to +500 at ply 7, user gives it back at ply 8): ply 8 classifies `pure_miss` and fits window position 4 but not 5.
- D-16 hazard numbers reproduced within 1e-3: raw 0.265 / 0.1948 / 0.1432 / 0.0701 / 0.0258, herring share 0.301, normalized 0.379 / 0.279 / 0.205 / 0.100 / 0.037.

### Mutation proofs (each applied, test failed, then reverted; suite back to 31 passed)

| Mutation | Failing test |
| -------- | ------------ |
| (a) `miss_case` comparison made strict (`>`) | `TestMissCase::test_boundary_is_inclusive` |
| (b) dropped `rank == RANK_BASE` branch in `_pair_passes` | `TestFindable::test_top_rank_passes_regardless_of_prob` |
| (c) overlapping instead of disjoint herring windows | `TestHerringWindows::test_disjoint_windows_per_run` |

## Deviations from Plan

None. The plan executed as written. One test-authoring fix: the inaccuracy test initially used -30 cp (drop 0.028, below `INACCURACY_DROP`); changed to -80 cp (drop ~0.073). A pure test-data correction, not a code change.

## Known Stubs

None.

## Threat Flags

None. Pure functions, no I/O, DB or network.

## Self-Check: PASSED

- scripts/blunder_check/__init__.py, scripts/blunder_check/metrics.py, tests/scripts/test_blunder_check_metrics.py exist.
- Commits 1ebbaa883 and 8eb68152d are on the phase branch.
