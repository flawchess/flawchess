---
phase: quick-260626-dxs
plan: "01"
subsystem: library
tags: [bug-fix, clock-suppression, daily-games, correspondence]
status: complete
dependency_graph:
  requires: []
  provides: [is_correspondence_time_control predicate, clock/move-time suppression at EvalPoint and FlawListItem build sites]
  affects: [app/services/normalization.py, app/services/library_service.py, app/repositories/library_repository.py]
tech_stack:
  added: []
  patterns: [is_correspondence_time_control predicate, display-layer suppression with storage untouched]
key_files:
  created:
    - tests/services/test_normalization.py
  modified:
    - app/services/normalization.py
    - app/services/library_service.py
    - app/repositories/library_repository.py
    - tests/services/test_eval_chart_service.py
    - tests/repositories/test_library_repository.py
decisions:
  - "Suppressed at display layer only — game_positions.clock_seconds storage untouched (feeds time-management stats)"
  - "Separator-based predicate rather than platform-specific check — both chess.com and lichess normalize to 1/{seconds} format"
  - "Compute is_correspondence once per game before the loop in _build_eval_series (not per-EvalPoint)"
metrics:
  duration: "~15 min"
  completed: "2026-06-26"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 5
  files_created: 1
---

# Phase quick-260626-dxs Plan 01: Suppress Clock/Move-Time Display for Daily/Correspondence Games Summary

## One-liner

Backend display-layer suppression of meaningless %clk values for chess.com daily and lichess correspondence games via a reusable `is_correspondence_time_control` predicate — clock_seconds and move_seconds forced to None at both the EvalPoint and FlawListItem build sites, with storage untouched.

## What Was Built

### Task 1: Add predicate and suppress clock/move-time at both build sites (commit 61102f3c)

**`app/services/normalization.py`** — Added `CORRESPONDENCE_TC_SEPARATOR = "/"` named constant and `is_correspondence_time_control(time_control_str: str | None) -> bool` predicate. The function returns True when the string is non-empty, not "-", and contains "/" (the per-move separator shared by chess.com "1/86400" daily format and lichess correspondence normalization "1/{daysPerTurn*86400}"). Placed next to the existing time-control helpers.

**`app/services/library_service.py`** — In `_build_eval_series`, imported `is_correspondence_time_control`, computed the flag once per game before the position loop, and forced `clock = None` when `is_correspondence`. The existing `if clock is not None:` guard then naturally makes `move_seconds = None` as well. Added bug-fix comment citing the witnessed nonsensical jump (game 687474 user 28: 0.7s → 21.3s → 1008s → 90s).

**`app/repositories/library_repository.py`** — In `_build_flaw_item`, added `is_correspondence_time_control` to the `normalization` import, computed the flag from `game.time_control_str`, and used it to force both `clock_seconds=None` and `move_seconds=None` (skipping `_compute_move_seconds`) in the `FlawListItem` constructor. Same bug-fix comment.

**Tests** — New `tests/services/test_normalization.py` (9 predicate unit tests). Expanded `test_eval_chart_service.py` with `_make_game` `time_control_str` param and new `TestCorrespondenceClockSuppression` class (3 tests: daily suppression, 3-day correspondence suppression, classical regression). Expanded `test_library_repository.py` with in-memory helper functions and new `TestBuildFlawItemClockSuppression` class (2 tests: daily suppression and classical regression for `_build_flaw_item`).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
uv run ruff format app/ tests/        # 2 files reformatted (test files only)
uv run ruff check app/ tests/ --fix   # All checks passed
uv run ty check app/ tests/           # All checks passed (0 errors)
uv run pytest -n auto tests/services/test_normalization.py \
  tests/services/test_eval_chart_service.py \
  tests/repositories/test_library_repository.py -x
# 60 passed in 10.41s
```

## Self-Check: PASSED

- [x] `app/services/normalization.py` — `is_correspondence_time_control` added
- [x] `app/services/library_service.py` — clock suppression in `_build_eval_series`
- [x] `app/repositories/library_repository.py` — clock suppression in `_build_flaw_item`
- [x] `tests/services/test_normalization.py` — created
- [x] `tests/services/test_eval_chart_service.py` — extended
- [x] `tests/repositories/test_library_repository.py` — extended
- [x] Commit 61102f3c exists in git log
- [x] 60/60 tests pass
- [x] No frontend changes, no migrations, no import-pipeline edits, no new TC bucket/enum/filter
