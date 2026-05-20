---
phase: 90
plan: "01"
subsystem: import-pipeline
tags:
  - sqlalchemy
  - executemany
  - bulk-update
  - memory-leak
  - bug-fix
dependency_graph:
  requires: []
  provides:
    - "_flush_batch Stage 5 invariant-SQL executemany rewrite"
    - "TestFlushBatchStage5 Wave 0 unit tests"
  affects:
    - "app/services/import_service.py::_flush_batch"
    - "tests/test_import_service.py"
tech_stack:
  added: []
  patterns:
    - "SQLAlchemy 2.x executemany with bindparam — update().where(col == bindparam()).values(col=bindparam())"
key_files:
  created: []
  modified:
    - path: app/services/import_service.py
      lines: "27, 544-585"
      description: "Replace case()+IN Stage 5 UPDATE with two bindparam executemany groups"
    - path: tests/test_import_service.py
      lines: "1-22, 1318-1720"
      description: "Add TestFlushBatchStage5 class (5 tests); add cast/NormalizedGame imports"
decisions:
  - "Two executemany groups (not COALESCE): result_fen is only written for games where the parsed value is not None, preserving prior values for None-fen games (Pitfall 1 / SQLAlchemy issue #9075 fragility)"
  - "b_ param prefix on bindparam names (b_id, b_mc, b_rf) to avoid collision with Game column names"
  - "xfail markers on Tests 2 and 5 removed after Task 2 flip — all 5 now pass cleanly"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-20"
  tasks_completed: 2
  files_modified: 2
---

# Phase 90 Plan 01: Stage 5 Executemany Rewrite Summary

One-liner: Replace `_flush_batch` Stage 5's CASE()+IN bulk UPDATE with two bound-parameter `executemany` groups that emit invariant SQL text, fixing the production OOM memory leak (FLAWCHESS-56 / FLAWCHESS-3Q).

## What Was Built

### Task 1 (TDD RED): TestFlushBatchStage5 unit tests

Added `class TestFlushBatchStage5` to `tests/test_import_service.py` (line ~1318):

| Test | Name | Status against current code |
|------|------|-----------------------------|
| 1 | `test_move_count_lands_for_all_games` | PASS |
| 2 | `test_result_fen_none_preserved` | XFAIL (strict=False) — current emits 1 combined UPDATE |
| 3 | `test_result_fen_all_none_skips_fen_update` | PASS |
| 4 | `test_empty_move_counts_short_circuits` | PASS |
| 5 | `test_stage5_sql_text_invariant_across_batches` | XFAIL (strict=True) — CASE SQL varies per batch |

### Task 2 (TDD GREEN): Stage 5 rewrite

`app/services/import_service.py` lines 544–585:
- Replaced `case()+IN` single UPDATE with two `executemany` groups
- Group (a): `move_count` for ALL games — `update(Game).where(Game.id == bindparam("b_id")).values(move_count=bindparam("b_mc"))`
- Group (b): `result_fen` ONLY for games where `result_fen is not None` — `update(Game).where(Game.id == bindparam("b_id")).values(result_fen=bindparam("b_rf"))`
- Removed `case` from SQLAlchemy import; added `bindparam`
- Added bug-fix comment block per CLAUDE.md

After Task 2:
- Tests 2 and 5 xfail markers removed — all 5 tests pass
- 37 total tests in `tests/test_import_service.py` pass
- ruff clean, ty clean

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `app/services/import_service.py` | 27 | `from sqlalchemy import bindparam, select, update` (removed `case`, added `bindparam`) |
| `app/services/import_service.py` | 544–585 | Stage 5 rewrite: two `executemany` groups |
| `tests/test_import_service.py` | 1–22 | Added `cast`, `NormalizedGame` imports |
| `tests/test_import_service.py` | 1318–1720 | Added `TestFlushBatchStage5` class (5 tests) |

## Test Summary

```
uv run pytest tests/test_import_service.py::TestFlushBatchStage5 -v
5 passed in 0.11s

uv run pytest tests/test_import_service.py -x -q
37 passed in 0.18s
```

## Import Confirmation

- `case` import removed: confirmed — `grep -n '^from sqlalchemy import' app/services/import_service.py` shows `bindparam, select, update`
- `bindparam` added: confirmed — 4 occurrences of `bindparam("b_` in the file (2 per statement × 2 statements)

## Deviations from Plan

None — plan executed exactly as written.

The xfail approach for Tests 2 and 5 was clarified during implementation:
- Test 2 (xfail strict=False): The mock-based assertion checks that Stage 5 emits exactly 2 UPDATE execute calls (not 1 combined), which fails correctly on current code
- Test 5 (xfail strict=True): Calls `_flush_batch` twice with different game-id sets and compares compiled SQL text, which fails correctly on current code (different CASE clause counts)

Both markers were removed (not just flipped) after Task 2 since the tests now pass unconditionally.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access, or schema changes. The `bindparam` executemany approach is net-neutral vs the `case()` map on SQL injection surface (both parameterized).

## Self-Check: PASSED

- [x] `app/services/import_service.py` exists and contains `bindparam("b_id")`
- [x] `tests/test_import_service.py` exists and contains `class TestFlushBatchStage5`
- [x] Commit `8053e125` (Task 1 TDD RED) exists
- [x] Commit `c125d53a` (Task 2 TDD GREEN) exists
- [x] All 37 tests pass, ruff clean, ty clean
