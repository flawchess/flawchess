---
phase: 78
plan: "04"
subsystem: import
tags: [import, span-entry, eval, sentry, timing, tdd]
dependency_graph:
  requires: [app.services.engine]
  provides: [import-time-eval, IMP-01, IMP-02]
  affects: [app.services.import_service, tests.services.test_import_service_eval]
tech_stack:
  added: []
  patterns: [post-insert eval pass, _board_at_ply PGN replay, defaultdict span-entry grouping, perf_counter timing]
key_files:
  created:
    - tests/services/test_import_service_eval.py
  modified:
    - app/services/import_service.py
decisions:
  - "_board_at_ply defined locally in import_service.py (not shared with backfill script) — Option A from RESEARCH.md keeps Wave 2 plans independent"
  - "game_eval_data list collects (game_id, pgn, plies) alongside position_rows to avoid a second full PGN parse loop"
  - "PlyData TypedDict used for game_eval_data type annotation to satisfy ty type checker"
  - "eval_pass placed between step 5 (bulk_insert_positions) and step 6 (move_count UPDATE) so all writes land in same session.commit()"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-02"
  tasks: 2
  files_touched: 2
---

# Phase 78 Plan 04: Import Path Integration Summary

Import-time Stockfish eval for chess.com games: span-entry rows get eval_cp/eval_mate populated automatically during import, no backfill needed for new data.

## What Was Built

`app/services/import_service.py` additions:

- `_board_at_ply(pgn_text, target_ply)` helper (lines 40-62): replays PGN mainline to reconstruct the board at a span-entry ply without retaining chess.Board objects in memory during the main walk. Mirrors RESEARCH.md Option A.
- `game_eval_data` list (line 477): per-game `(game_id, pgn, plies_list)` tuples collected alongside position_rows for the post-insert pass.
- **Eval pass at line 529** (Step 5a, `_flush_batch`): runs after `bulk_insert_positions` (line 527) and before the `move_count` UPDATE (Step 6), within the same transaction.
  - Groups plies by `endgame_class` via `defaultdict`
  - For groups with `count >= ENDGAME_PLY_THRESHOLD`: finds `MIN(ply)` span entry
  - Skips if `eval_cp is not None or eval_mate is not None` (lichess preservation, T-78-17)
  - Calls `await engine_service.evaluate(board)` for each qualifying span entry
  - On `(None, None)` return: sets Sentry context with `game_id, ply, endgame_class` only (T-78-18), no PGN/fen/user_id
  - On success: issues `UPDATE game_positions SET eval_cp=..., eval_mate=... WHERE game_id=... AND ply=... AND endgame_class=...`
- Timing instrumentation: `eval_pass_ms` logged via `logger.info("import_eval_pass", extra={...})` (IMP-02 budget observation)

**Insertion point:** `_flush_batch`, line 529, immediately after `await game_repository.bulk_insert_positions(session, position_rows)`.

`tests/services/test_import_service_eval.py` (715 lines):

- 6 tests across 5 classes (plan required >= 5 classes)
- `TestImportEvalChessCom`: chess.com game with 8 endgame plies → `engine_service.evaluate` called >= 1, UPDATE issued with eval_cp=150
- `TestImportEvalLichessPreservation`: lichess game with `eval_cp=15` already set → engine call_count == 0 (T-78-17)
- `TestImportEvalEngineError`: engine returns `(None, None)` → Sentry `set_context("eval", {game_id, ply, endgame_class})`, no pgn/user_id/fen, no UPDATE issued (T-78-18, D-11)
- `TestImportEvalNoEndgame` (2 tests): game with no endgame plies OR below threshold → engine call_count == 0
- `TestImportEvalMultiClass`: game with 2 endgame classes (8 plies each) → exactly 2 engine calls

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED  | 738c70f | `test(78-04): add failing IMP-01 Wave 0 integration tests (RED)` |
| GREEN | 09ffe55 | `feat(78-04): hook engine eval into _flush_batch import pipeline (IMP-01 GREEN)` |

RED confirmed by: `AttributeError: module 'app.services.import_service' has no attribute 'engine_service'`

## Observed eval_pass_ms

Tests are mocked (no Stockfish). Production budget from RESEARCH.md: 1-3 evaluations at ~70ms each + <1ms PGN replay = ~70-210ms per game at p50. `eval_pass_ms` is logged per batch — operator monitors after deploy. No hard gate; logged for IMP-02 observation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PGN validity required for _board_at_ply at ply=0**

- **Found during:** Task 1 RED → Task 2 GREEN cross-verification
- **Issue:** Test PGN `1. Rh1 Rh8...` was invalid (Rh1 illegal from initial position). `chess.pgn.read_game` silently produced 0 mainline nodes, so `_board_at_ply(pgn, 0)` returned `None`, skipping the engine call. Tests showed `call_count == 0` even after GREEN implementation.
- **Fix:** Changed test PGNs to a valid legal game (`1. e4 e5 2. Nf3 Nc6 3. Bc4 Be7...`). `process_game_pgn` is mocked so the PGN only needs to be valid for `_board_at_ply` replay, not represent the actual endgame.
- **Files modified:** `tests/services/test_import_service_eval.py`
- **Commit:** 09ffe55

**2. [Rule 2 - Missing functionality] PlyData TypedDict type annotation**

- **Found during:** Task 2 ty check
- **Issue:** `game_eval_data: list[tuple[int, str, list[dict[str, Any]]]]` caused ty error `Expected tuple[int, str, list[dict[str, Any]]], found tuple[Any, str, list[PlyData]]`
- **Fix:** Changed to `list[tuple[int, str, list[PlyData]]]` and imported `PlyData` from `app.services.zobrist`; changed `pd.get("endgame_class")` to `pd["endgame_class"]` (TypedDict key access); changed inner type annotation to `dict[int, list[PlyData]]`.
- **Files modified:** `app/services/import_service.py`
- **Commit:** 09ffe55

## Threat Coverage

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-78-17 (Tampering: lichess eval overwritten) | `if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None: continue` | Implemented + tested |
| T-78-18 (Info disclosure: Sentry PGN/fen) | `set_context("eval", {game_id, ply, endgame_class})` only | Implemented + tested |
| T-78-19 (DoS: engine error wedges import) | `(None, None)` → skip, log, continue (D-11) | Implemented + tested |
| T-78-20 (Tampering: commit failure) | Eval UPDATEs within same session.commit() as bulk insert | Implemented by design |
| T-78-21 (DoS: IMP-02 budget) | `eval_pass_ms` logged for operator monitoring | Implemented |

## Known Stubs

None. All eval values are populated by the real engine wrapper (mocked in tests). No hardcoded empty values in any data flow path.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/services/import_service.py | FOUND |
| tests/services/test_import_service_eval.py | FOUND |
| commit 738c70f (RED) | FOUND |
| commit 09ffe55 (GREEN) | FOUND |
| `engine_service.evaluate` in import_service | FOUND (line 561) |
| `ENDGAME_PLY_THRESHOLD` imported | FOUND (line 32) |
| `_board_at_ply` definition | FOUND (line 40) |
| `eval_pass_ms` timing instrumentation | FOUND (lines 533, 590, 597) |
| No pgn/fen in Sentry context | VERIFIED (grep confirms only comment) |
| No asyncio.gather introduced | VERIFIED (grep count = 1, only comment) |
| ty check clean | PASSED |
| ruff check clean | PASSED |
| 1179 tests pass | PASSED |
