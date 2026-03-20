---
phase: 12-backend-next-moves-endpoint
verified: 2026-03-16T21:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 12: Backend Next-Moves Endpoint Verification Report

**Phase Goal:** A single endpoint aggregates next moves for any position hash with correct W/D/L counts, respecting all existing filters and handling transpositions without double-counting.
**Verified:** 2026-03-16T21:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All must-haves are drawn from the PLAN frontmatter of plans 01 and 02.

#### Plan 01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `query_next_moves` returns per-move game_count, wins, draws, losses grouped by move_san with COUNT(DISTINCT game_id) | VERIFIED | `func.count(Game.id.distinct()).label("game_count")` + CASE expressions at lines 301-330 of analysis_repository.py |
| 2 | A game reaching the same position at multiple plies and playing the same move is counted once (transposition dedup) | VERIFIED | Self-join on `(gp2.game_id == gp1.game_id) & (gp2.ply == gp1.ply + 1)` + COUNT(DISTINCT) confirmed by TestNextMovesTranspositions::test_transposition_counted_once PASSING |
| 3 | `query_transposition_counts` returns total distinct games reaching each result_hash under the same filters | VERIFIED | `func.count(GamePosition.game_id.distinct())` + `.in_(result_hash_list)` at lines 370-386; TestTranspositionCounts PASSING |
| 4 | `NextMovesRequest` schema accepts target_hash as string (BigInt coercion) and all filter fields minus match_side and pagination | VERIFIED | Lines 141-168 of analysis.py: `target_hash: int` with `@field_validator("target_hash", mode="before")` coercing strings; no `match_side`, `offset`, or `limit` fields |

#### Plan 02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | POST /analysis/next-moves returns NextMovesResponse with position_stats and moves list | VERIFIED | `@router.post("/analysis/next-moves", response_model=NextMovesResponse)` at line 52 of analysis.py router; calls `analysis_service.get_next_moves` |
| 6 | Each move entry includes result_fen (board_fen via python-chess replay) and result_hash (as string) | VERIFIED | `_fetch_result_fens` uses `board.board_fen()` (line 306 of analysis_service.py); `result_hash=str(row.result_hash)` (line 418); TestGetNextMoves::test_result_fen_uses_board_fen PASSING |
| 7 | sort_by=frequency orders by game_count desc; sort_by=win_rate orders by win_pct desc | VERIFIED | Lines 425-428 of analysis_service.py; TestNextMovesSorting::test_sort_by_frequency and test_sort_by_win_rate both PASSING |
| 8 | transposition_count is >= game_count for every move entry | VERIFIED | TestGetNextMoves::test_transposition_count_gte_game_count PASSING |
| 9 | All existing filters reduce the move list correctly | VERIFIED | `_apply_game_filters` shared helper (lines 242-271 of analysis_repository.py) applied consistently to both `query_next_moves` and `query_transposition_counts`; TestNextMovesFilters tests PASSING |
| 10 | position_stats uses full_hash exclusively (no match_side) | VERIFIED | `hash_column=GamePosition.full_hash` at line 333 of analysis_service.py; NextMovesRequest has no match_side field |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/analysis.py` | NextMovesRequest, NextMoveEntry, NextMovesResponse schemas | VERIFIED | All three classes present at lines 141-191; target_hash required (not Optional); sort_by field present; no match_side/pagination |
| `app/repositories/analysis_repository.py` | query_next_moves, query_transposition_counts, _apply_game_filters | VERIFIED | All three functions present (lines 242, 274, 347); substantive implementations with self-join and CASE expressions |
| `tests/test_analysis_repository.py` | TestNextMoves, TestNextMovesTranspositions, TestNextMovesFilters, TestTranspositionCounts, TestNextMovesNullMoveExcluded | VERIFIED | All 5 test classes present at lines 665, 754, 816, 905, 988; 7 tests all PASS |
| `app/services/analysis_service.py` | get_next_moves, _fetch_result_fens | VERIFIED | Both functions present (lines 249, 311); PGN replay via `board.board_fen()` confirmed at line 306 |
| `app/routers/analysis.py` | POST /analysis/next-moves endpoint | VERIFIED | `@router.post("/analysis/next-moves", response_model=NextMovesResponse)` at line 52; dependency injection correct |
| `tests/test_analysis_service.py` | TestGetNextMoves, TestNextMovesSorting, _seed_game_with_positions | VERIFIED | All three present (lines 283, 345, 457); 6 tests all PASS |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/repositories/analysis_repository.py` | `app/models/game_position.py` | `GamePosition.move_san`, self-join gp1/gp2 on game_id+ply | VERIFIED | `gp1.move_san`, `gp2.full_hash`, `gp2.ply == gp1.ply + 1` confirmed at lines 296-338 |
| `app/repositories/analysis_repository.py` | `app/models/game.py` | `Game.result`, `Game.user_color` for CASE WHEN W/D/L | VERIFIED | win_case/draw_case/loss_case use `Game.result` and `Game.user_color` conditions at lines 301-320 |
| `app/services/analysis_service.py` | `app/repositories/analysis_repository.py` | imports query_next_moves, query_transposition_counts, query_all_results | VERIFIED | Lines 14-21: all three imported and called in get_next_moves |
| `app/routers/analysis.py` | `app/services/analysis_service.py` | calls analysis_service.get_next_moves | VERIFIED | Line 63: `return await analysis_service.get_next_moves(session, user.id, request)` |
| `app/services/analysis_service.py` | python-chess | `chess.Board()` + `board.push()` + `board.board_fen()` | VERIFIED | `import chess; import chess.pgn` at lines 7-8; `board.board_fen()` at line 306 (not `board.fen()`) |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MEXP-04 | 12-01, 12-02 | Backend endpoint returns next moves for a given position hash with game count and W/D/L stats per move, respecting all existing filters | SATISFIED | POST /analysis/next-moves returns NextMovesResponse with per-move game_count + W/D/L; _apply_game_filters applied consistently |
| MEXP-05 | 12-01, 12-02 | Transpositions are handled correctly — each game counted only once per move even if position reached via different move orders | SATISFIED | COUNT(DISTINCT game_id) with self-join gp1/gp2; TestNextMovesTranspositions::test_transposition_counted_once PASSING |
| MEXP-10 | 12-01, 12-02 | Next-moves endpoint returns transposition count (total games reaching the resulting position via any move order) alongside direct game count | SATISFIED | `transposition_count` field on NextMoveEntry; query_transposition_counts batch lookup; TestGetNextMoves::test_transposition_count_gte_game_count PASSING |

No orphaned requirements: all three IDs appear in both plan frontmatters and are fully satisfied.

---

### Anti-Patterns Found

None. Scanned all 4 modified/created source files for TODO/FIXME/placeholder markers and stub return patterns. The three `return {}` instances in analysis_repository.py and analysis_service.py are all guarded early returns for empty-input conditions (`if not result_hash_list` / `if not result_hashes` / `if not sample_rows`) — not stubs.

---

### Human Verification Required

None required for this phase. The endpoint is backend-only and fully covered by integration tests against a real PostgreSQL database. All observable behaviors are verifiable programmatically:

- W/D/L aggregation: verified via integration tests with seeded data
- Transposition dedup: verified via TestNextMovesTranspositions
- Filter application: verified via TestNextMovesFilters
- result_fen format (board_fen not full FEN): verified via test_result_fen_uses_board_fen asserting no spaces in FEN
- Sort order: verified via TestNextMovesSorting
- Endpoint registration: verified by presence in router and full test suite (278 passed)

---

### Test Suite

- Repository tests (`-k "NextMoves or TranspositionCount or NullMove"`): **7 passed**
- Service tests (`-k "NextMoves or NextMovesSorting"`): **6 passed**
- Full test suite: **278 passed, 0 failed**
- Lint (`ruff check`): **All checks passed**

---

### Summary

Phase 12 goal is fully achieved. The single POST /analysis/next-moves endpoint aggregates next moves for any position hash with correct per-move W/D/L counts (via COUNT(DISTINCT CASE WHEN) self-join), respects all existing filters through the shared _apply_game_filters helper, and handles transpositions without double-counting. The result_fen is computed correctly via python-chess PGN replay using board.board_fen() (piece-placement-only). All 13 new integration tests pass and the full suite of 278 tests is green.

---

_Verified: 2026-03-16T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
