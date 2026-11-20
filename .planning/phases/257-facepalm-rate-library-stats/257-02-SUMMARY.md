---
phase: 257-facepalm-rate-library-stats
plan: 02
subsystem: api
tags: [facepalm, sqlalchemy, pydantic, library-games, flaw-markers]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats
    provides: facepalm_type_expr / facepalm_type_from_sql / FacepalmType, typed seeds (plan 01)
provides:
  - FacepalmChipValue(score, facepalm_type) from fetch_page_facepalm_scores (owner side only)
  - FlawMarker.facepalm_type on GET /api/library/games and /games/{game_id}, blunder-gated like the score
  - TS FlawMarker.facepalm_type mirror
affects: [257-03]

actuals:
  tokens: 6000
  tasks: 1
  commits: 2
plan_head_before: 2ddc9d45d40b95c57d3264ecc8b0c8ae1fb5f73e
plan_head_after: 0bb7f924904517bd678e640f1c018c10c2f0ed1d
commits: 2

tech-stack:
  added: []
  patterns:
    - "NamedTuple marker value (score + type) selected in one statement instead of two parallel maps"

key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - frontend/src/types/library.ts
    - tests/test_library_repository.py
    - tests/services/test_eval_chart_service.py
    - tests/test_library_router.py

key-decisions:
  - "Field is named facepalm_type (not type) on FacepalmChipValue to avoid shadowing the builtin"
  - "A row whose SQL type narrows to None is skipped in the reader (cannot happen with a non-NULL score), so a marker never carries a score without a type"

patterns-established:
  - "Marker facepalm score and type share one blunder gate in _build_eval_series (one bound `facepalm` value)"

requirements-completed: [D-06, D-08]

duration: 12 min
completed: 2026-11-20
---

# Phase 257 Plan 02: Facepalm type on flaw markers Summary

**Flaw markers of the games payloads now carry facepalm_type next to facepalm_score, from the same owner-side statement and the same blunder gate; opponent and non-blunder markers carry neither.**

## Accomplishments

- `FacepalmChipValue(NamedTuple)` in `app/repositories/library_repository.py`; `fetch_page_facepalm_scores` selects `facepalm_type_expr()` next to the library-lambda score with the unchanged WHERE (user scope, `player_only_gate`, score IS NOT NULL) and returns `dict[int, dict[int, FacepalmChipValue]]`.
- `_build_eval_series` / `_build_card` take `dict[int, FacepalmChipValue]`; a single `facepalm` value gated on `severity == "blunder"` feeds both marker fields.
- `FlawMarker.facepalm_type: FacepalmType | None = None` (schema) and `facepalm_type?: FacepalmType | null` (TS) added after `facepalm_score`.

## Task Commits

1. **RED:** `60adc1027` (test) - failing reader and marker tests.
2. **GREEN:** `0bb7f9249` (feat) - implementation on both stacks.

## TDD Gate Compliance

- RED commit `60adc1027`: `TestFetchPageFacepalmScores` failed with `AttributeError: 'float' object has no attribute 'score'` (all three value-reading tests, including the new `test_marker_value_carries_missed_win_type`); `test_eval_chart_service.py` failed at collection (`FacepalmChipValue` missing). The implementation had been drafted in the working tree first; it was moved aside by copying the four files to a scratch dir and `git checkout -- <file>` on those files only, the RED run was taken against the reverted code, then the files were restored for the GREEN commit.
- GREEN commit `0bb7f9249`: all four target test files pass (317 passed with the neighbouring library repository, router and maia scoring tests).
- No REFACTOR commit.

## Deviations from Plan

None. The plan's step 7 asserts on `GET /api/library/games` (the existing test); the single-game card builds markers through the same `_build_eval_series`, so no separate test was added.

## Known Stubs

None.

## Threat Flags

None. The type column joins the existing owner-side statement (T-257-03); the owner gate and IDOR tests are unchanged and green (T-257-04). No drill or filter reader touched.

## Verification Run

- `uv run pytest` on test_library_repository (both files), test_eval_chart_service, test_library_router, test_maia_flaw_scoring: 317 passed.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check .`, `ruff format`, `check_function_size.py --fail-over-depth 4`: clean.
- Frontend: `npm run lint`, `npm run build`, `npm run knip` exit 0.

## Self-Check: PASSED

- FOUND: app/repositories/library_repository.py (`class FacepalmChipValue`), app/schemas/library.py, app/services/library_service.py, frontend/src/types/library.ts
- FOUND commits: 60adc1027, 0bb7f9249
