---
phase: 27-import-wiring-backfill
verified: 2026-03-24T18:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 27: Import Wiring & Backfill — Verification Report

**Phase Goal:** All newly imported games populate the seven metadata columns at import time, and all previously imported games have those columns filled without requiring users to re-import
**Verified:** 2026-03-24
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A newly imported game has non-null game_phase, material_signature, material_imbalance, has_bishop_pair_white, has_bishop_pair_black, has_opposite_color_bishops on every game_positions row | VERIFIED | `test_position_rows_include_game_phase`, `test_position_rows_include_material_signature` pass; classify_position called per-ply in `_flush_batch()` lines 426-444 |
| 2 | classify_position is called with the board state BEFORE each move is pushed (pre-move, matching ply semantics) | VERIFIED | Code at line 428: `classification = classify_position(classify_board)` precedes `classify_board.push(classify_nodes[i].move)` at line 444; `test_starting_position_classified_as_opening` asserts ply 0 = 'opening' |
| 3 | If PGN parsing fails for classification, the game still imports with NULL metadata columns (graceful degradation) | VERIFIED | try/except at lines 427-441 catches any classify_position exception and logs a warning; `test_classification_failure_degrades_gracefully` passes |
| 4 | Running the backfill script against a database with NULL game_phase rows results in zero NULL game_phase rows afterward | VERIFIED | `test_backfill_updates_null_game_phase_to_nonnull` and `test_backfill_sets_all_7_metadata_columns` pass with real PostgreSQL |
| 5 | The backfill script resumes correctly if interrupted — re-running picks up only unprocessed games | VERIFIED | `get_unprocessed_game_ids()` queries for NULL `game_phase`; `test_backfill_is_idempotent` confirms processed game_id absent from second query |
| 6 | The script commits every 10 games to stay within the OOM-safe batch size | VERIFIED | `_BATCH_SIZE = 10` at line 29; `await session.commit()` at line 168 after each batch |
| 7 | A VACUUM ANALYZE runs automatically after all games are processed | VERIFIED | `run_vacuum()` called in `main()` line 173; uses `engine.connect()` with `AUTOCOMMIT` isolation level; `text("VACUUM ANALYZE game_positions")` at line 112 |
| 8 | Games with corrupt or unparseable PGN are skipped with Sentry error capture and the script continues | VERIFIED | `sentry_sdk.capture_exception(e)` at lines 153 and 177; `skipped_ids.add(game_id)` prevents infinite loop; `test_corrupt_pgn_skips_gracefully` passes |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/import_service.py` | classify_position wired into per-ply position_rows assembly | VERIFIED | Imports `classify_position` at line 26; calls it at line 428 inside `_flush_batch()` per-ply loop; all 7 metadata keys added to row dict |
| `tests/test_import_service.py` | Tests verifying metadata columns are populated on import | VERIFIED | 4 new tests in `TestRunImport`: `test_position_rows_include_game_phase`, `test_position_rows_include_material_signature`, `test_starting_position_classified_as_opening`, `test_classification_failure_degrades_gracefully` — all pass |
| `scripts/backfill_positions.py` | Standalone async backfill script | VERIFIED | 189 lines, substantive implementation with `get_unprocessed_game_ids()`, `backfill_game()`, `run_vacuum()`, `main()`; valid Python syntax confirmed |
| `tests/test_backfill.py` | Tests for backfill correctness and error handling | VERIFIED | 8 tests in 2 classes: `TestBackfillGame` (5 tests) and `TestGetUnprocessedGameIds` (3 tests) — all pass |
| `scripts/__init__.py` | Package marker for test imports | VERIFIED | File exists, enables `from scripts.backfill_positions import ...` in tests |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/import_service.py` | `app/services/position_classifier.py` | `from app.services.position_classifier import classify_position` | WIRED | Import at line 26 confirmed; `classify_position(classify_board)` called at line 428 inside per-ply loop |
| `app/services/import_service.py` | `app/repositories/game_repository.py` | position_rows dicts with 7 metadata keys passed to bulk_insert_positions | WIRED | `row.update({game_phase, material_signature, ...})` at lines 429-437; `bulk_insert_positions(session, position_rows)` at line 464 |
| `scripts/backfill_positions.py` | `app/services/position_classifier.py` | `from app.services.position_classifier import classify_position` | WIRED | Import at line 27; called at lines 66, 84 inside `backfill_game()` |
| `scripts/backfill_positions.py` | `app/core/database.py` | `from app.core.database import async_session_maker, engine` | WIRED | Import at line 24; `async_session_maker()` used in `main()` loop; `engine.connect()` used in `run_vacuum()` |
| `scripts/backfill_positions.py` | `app/models/game_position.py` | UPDATE game_positions via `GamePosition` model | WIRED | Import at line 26; `sa_update(GamePosition).where(...).values(...)` used in `backfill_game()` at lines 67-79 and 85-97 |

### Data-Flow Trace (Level 4)

Not applicable — both artifacts are backend service modules, not UI components that render dynamic data. The data flow is verified via test assertions on actual DB state.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All import service + backfill tests pass | `uv run pytest tests/test_import_service.py tests/test_backfill.py -x` | 33 passed in 0.54s | PASS |
| No lint errors in modified/created files | `uv run ruff check app/services/import_service.py scripts/backfill_positions.py` | All checks passed | PASS |
| Valid Python syntax in backfill script | `python3 -c "import ast; ast.parse(...)"` | syntax OK | PASS |
| classify_position import in import_service.py | `grep -c "from app.services.position_classifier import classify_position" app/services/import_service.py` | 1 | PASS |
| _BATCH_SIZE = 10 in backfill script | `grep -c "_BATCH_SIZE = 10" scripts/backfill_positions.py` | 1 | PASS |
| VACUUM ANALYZE present in backfill script | `grep "VACUUM ANALYZE game_positions" scripts/backfill_positions.py` | line 112 (functional call) | PASS |
| AUTOCOMMIT isolation for VACUUM | `grep -c "isolation_level.*AUTOCOMMIT" scripts/backfill_positions.py` | 1 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PMETA-05 | 27-01, 27-02 | System backfills position metadata for all previously imported games without requiring user re-import | SATISFIED | import_service.py wires classifier at import time (27-01); backfill_positions.py updates existing NULL rows (27-02); both fully tested and passing |

No orphaned requirements — PMETA-05 is the only requirement mapped to Phase 27 in REQUIREMENTS.md traceability table, and both plans claim it.

### Anti-Patterns Found

No anti-patterns detected:

- No TODO/FIXME/placeholder comments in implementation files
- No empty implementations (`return null`, `return {}`, `return []`)
- No hardcoded empty data structures flowing to output
- All 7 metadata fields populated with real values from `classify_position()` results
- Graceful degradation pattern is correctly implemented (try/except per-ply, not a permanent stub)

### Human Verification Required

**1. Production Backfill Execution**

**Test:** SSH into production server and run `uv run python scripts/backfill_positions.py`
**Expected:** Script runs to completion, prints progress every 50 games, ends with "Backfill complete" summary showing zero errors or acceptable error count, VACUUM ANALYZE completes
**Why human:** Cannot verify against production database from this environment; runtime OOM safety during large production import is observable only by running the script

**2. New Import End-to-End**

**Test:** After deploying, import a small set of games from chess.com or lichess for a test user, then query `SELECT game_phase, material_signature FROM game_positions WHERE user_id = <test_user_id> LIMIT 10`
**Expected:** All returned rows show non-null game_phase values ('opening', 'middlegame', or 'endgame') and non-null material_signature values
**Why human:** Requires a live deployment with actual platform API access and a real user account

### Gaps Summary

No gaps. All automated checks passed and all 8 must-have truths are verified.

---

_Verified: 2026-03-24_
_Verifier: Claude (gsd-verifier)_
