---
phase: 241-codebase-cleanup
plan: 67
subsystem: backend-naming
tags: [rename, naming, cross-layer, d-16-sweep]
requires: ["241-66"]
provides:
  - "MIN_TACTIC_CHIP_CONFIDENCE single definition (library_repository)"
  - "on_attempt_cap_reached callback and its two implementations"
  - "compute_score_difference_test(a_*, b_*) generic cohort parameters"
affects: [app/repositories, app/services, app/routers, tests, scripts/tactic_tagger_report.py]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-67.tsv
    - .planning/phases/241-codebase-cleanup/allow/241-67.tsv
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - app/services/tactic_detector.py
    - scripts/tactic_tagger_report.py
    - .claude/skills/tactic-tagger-report/SKILL.md
    - app/services/eval_apply.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - app/services/score_confidence.py
    - tests/test_library_repository.py
    - tests/services/test_eval_apply.py
    - tests/services/test_score_confidence.py
key-decisions:
  - "No alias kept for the old chip-confidence name (D-17); library_service re-exports the repository name through its import so scripts/benchmarks/chapter5.py and two tests still resolve"
requirements-completed: [D-06, D-07, D-09, D-17]
status: complete
commits: 3
plan_head_before: 56254a38fe99c9a0af9db9b65286e335f2465566
plan_head_after: 32a4381a1e9cb9ff7b44be2470e84b828cb3610f
actuals:
  tokens: 25000
  tasks: 3
---

# Phase 241 Plan 67: X4/X6/X7 cross-layer renames Summary

Three single-commit renames with no behavior change: the chip confidence floor gets one name, the path-C callbacks are named for the attempt cap, and the two-cohort score test names its cohorts A and B.

## Renames

| Ref | Old | New | Commit | Files |
|-----|-----|-----|--------|-------|
| X4 | `_TACTIC_CHIP_CONFIDENCE_MIN` (+ service alias) | `MIN_TACTIC_CHIP_CONFIDENCE` | 28ce6ffe2 | library_repository.py, library_service.py, schemas/library.py, tactic_detector.py, tactic_tagger_report.py (name only), tactic-tagger-report SKILL.md (name only), 6 test files |
| X6 | `on_path_c_capacity_reached` / `_log_path_c_capacity_reached` / `_report_path_c_capacity_reached` | `on_attempt_cap_reached` / `_log_path_c_attempt_cap_reached` / `_report_path_c_attempt_cap_reached` | b915ebffc | eval_apply.py, eval_drain.py, eval_remote.py, test_eval_apply.py |
| X7 | `eg_{w,d,l,n}`, `ne_{w,d,l,n}`, `score_eg/ne`, `var_eg/ne` | `a_*`, `b_*`, `score_a/b`, `var_a/b` | 32a4381a1 | score_confidence.py, test_score_confidence.py |

## Allow-listed change

X4 deleted the alias assignment `MIN_TACTIC_CHIP_CONFIDENCE: int = _TACTIC_CHIP_CONFIDENCE_MIN` in library_service.py (and its explanatory comment). The name now arrives through the repository import. Recorded in allow/241-67.tsv.

## Verification

- ruff check/format, ty (app/ tests/ scripts/): clean after each commit.
- Tests: X4 371 passed / 7 skipped; X6 236 passed; X7 229 passed.
- `cleanup.py absent` clean for all 16 map rows; `cleanup.py diff` passes with only the X4 alias deletion allow-listed.
- scripts/benchmarks/chapter5.py and reports/ untouched; value 70 unchanged.

## Deviations from Plan

- Docstring wording in X7: added a short sentence to the `compute_score_difference_test` docstring stating cohorts A and B are generic. No code change.
- Line numbers in the plan's read_first lists were slightly off; symbols were re-located by grep. No effect on outcome.
- X6: no docstring contained the word "capacity", so no wording change beyond the identifiers was needed.
- X7: every `eg_*`/`ne_*` in tests/services/test_score_confidence.py belonged to this function's tests, so the whole file was renamed with word-boundary substitution.

## Known Stubs

None.

## Self-Check: PASSED

Commits 28ce6ffe2, b915ebffc, 32a4381a1 exist on the worktree branch; rename-maps/241-67.tsv and allow/241-67.tsv present.
