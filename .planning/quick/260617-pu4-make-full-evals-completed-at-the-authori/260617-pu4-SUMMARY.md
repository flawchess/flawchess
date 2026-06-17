---
phase: quick-260617-pu4
plan: "01"
subsystem: library-repository
tags: [perf, correctness, analyzed-gate, eval-drain]
status: complete
completed: "2026-06-17"
duration: "~25 min"

depends_on: []
provides:
  - "games.full_evals_completed_at as the authoritative analyzed gate for Library/Games flaw stats"
affects:
  - "app/repositories/library_repository.py"
  - "app/services/library_service.py (consumers unchanged)"
  - "tests/test_library_repository.py"
  - "tests/services/test_library_service.py"
  - "tests/services/test_flaw_comparison.py"
  - "tests/test_library_router.py"

tech-stack:
  patterns:
    - "Indexed games lookup via Game.full_evals_completed_at.isnot(None) replaces GROUP BY / HAVING partition scan"

key-files:
  modified:
    - path: "app/repositories/library_repository.py"
      role: "_analyzed_game_ids_subquery rewritten; dead imports removed; Pitfall 6 comment updated"
    - path: "tests/test_library_repository.py"
      role: "TestAnalyzedDenominator and TestStatsAggregatesPlayerOnly updated to column-authoritative semantics"
    - path: "tests/services/test_library_service.py"
      role: "_seed_db_game sets full_evals_completed_at when analyzed=True"
    - path: "tests/services/test_flaw_comparison.py"
      role: "_seed_analyzed sets full_evals_completed_at instead of seeding per-ply positions"
    - path: "tests/test_library_router.py"
      role: "_seed_game_committed gains full_evals_completed_at; eval_series and game_by_id fixtures updated"
    - path: "CHANGELOG.md"
      role: "User-facing bullet under [Unreleased] ### Changed"

decisions:
  - "D-1: Dead imports Float, and_, EVAL_COVERAGE_MIN removed; case/or_/GamePosition retained (still used elsewhere)"
  - "D-2: Tests updated (not deleted) to column-authoritative semantics per plan requirement"
  - "D-3: fetch_flaw_trend_rows left untouched — already uses oracle-present gate by design"
---

# Phase quick-260617-pu4 Plan 01: Make full_evals_completed_at the Authoritative Analyzed Gate Summary

**One-liner:** Replaced game_positions GROUP BY / HAVING coverage recompute with indexed games.full_evals_completed_at lookup in _analyzed_game_ids_subquery, eliminating 135s avg / 49-min max tail latency under eval drain.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Swap _analyzed_game_ids_subquery to games-based gate + clean dead imports | 0821b538 | app/repositories/library_repository.py |
| 2 | Update tests to column-authoritative semantics, CHANGELOG, full backend gate | 7c651438 | tests/test_library_repository.py, tests/services/test_library_service.py, tests/services/test_flaw_comparison.py, tests/test_library_router.py, CHANGELOG.md |

## What Changed

### Task 1: Repository change

`_analyzed_game_ids_subquery(user_id)` was rewritten from:

```python
# OLD — full partition scan on game_positions per call
select(GamePosition.game_id.label("game_id"))
    .where(GamePosition.user_id == user_id)
    .group_by(GamePosition.game_id)
    .having(and_(func.count() > 1, coverage >= EVAL_COVERAGE_MIN))
    .subquery("analyzed")
```

to:

```python
# NEW — cheap indexed games lookup
select(Game.id.label("game_id"))
    .where(Game.user_id == user_id, Game.full_evals_completed_at.isnot(None))
    .subquery("analyzed")
```

Dead imports removed: `Float`, `and_`, `EVAL_COVERAGE_MIN`. The comment at `fetch_stats_aggregates` (~line 554) documenting Pitfall 6 / D-03 was updated to explain the reversal and the prod finding.

### Task 2: Tests updated

- `tests/test_library_repository.py` — `_seed_game` now accepts `full_evals_completed_at`. `TestAnalyzedDenominator` tests updated: games that were previously marked "analyzed" via dense per-ply `eval_cp` seeding now use `full_evals_completed_at=datetime.now(utc)` instead. `test_short_fully_analyzed_game_is_analyzed` repurposed to assert the same game that the old (COUNT-1) fix rescued is now rescued by the column gate. `TestStatsAggregatesPlayerOnly._seed_analyzed_game_with_positions` simplified.
- `tests/services/test_library_service.py` — `_seed_db_game` sets `full_evals_completed_at=now` when `analyzed=True` (default). The trend test comment updated.
- `tests/services/test_flaw_comparison.py` — `_seed_analyzed` now sets `full_evals_completed_at` and drops the per-ply position seeding loop (positions no longer needed for the analyzed gate).
- `tests/test_library_router.py` — `_seed_game_committed` gains `full_evals_completed_at` param; `eval_series_test_state` and `game_by_id_test_state` fixtures updated to set it on analyzed games.

## Verification

- `_analyzed_game_ids_subquery` no longer references `GamePosition`, `Float`, `and_`, or `EVAL_COVERAGE_MIN`
- All call sites unchanged, consuming `.c.game_id`
- `fetch_flaw_trend_rows` untouched
- No Alembic migration (no schema change)
- `ruff format --check`: clean
- `ruff check`: all checks passed
- `ty check`: zero errors
- `pytest -n auto`: **2713 passed, 10 skipped** (pre-existing benchmark-excluded tests)

## Deviations from Plan

**1. [Rule 1 - Additional tests] `tests/test_library_router.py` required updates**

The plan identified `tests/repositories/test_library_repository.py` and implied `test_library_service.py` / `test_flaw_comparison.py` as the affected test files. Two additional router-level integration tests also failed:
- `TestEvalSeriesPayload::test_eval_series_analyzed_game_has_non_null_fields`
- `TestLibraryGameById::test_library_game_by_id_own_game_200`

Both assert `analysis_state == "analyzed"` which is derived from `fetch_page_analyzed_set` (which calls `_analyzed_game_ids_subquery`). The `_seed_game_committed` helper in `test_library_router.py` and the fixtures `eval_series_test_state` / `game_by_id_test_state` were updated to set `full_evals_completed_at` on analyzed games. No test was deleted; all were migrated to the column-authoritative gate.

## Self-Check

### Files exist

- `app/repositories/library_repository.py` — modified (FOUND)
- `CHANGELOG.md` — modified (FOUND)
- `tests/test_library_repository.py` — modified (FOUND)
- `tests/services/test_library_service.py` — modified (FOUND)
- `tests/services/test_flaw_comparison.py` — modified (FOUND)
- `tests/test_library_router.py` — modified (FOUND)

### Commits exist

- `0821b538` — perf(260617-pu4): replace per-ply coverage scan with full_evals_completed_at gate (FOUND)
- `7c651438` — test(260617-pu4): migrate analyzed-gate tests to full_evals_completed_at; add CHANGELOG (FOUND)

## Self-Check: PASSED
