---
phase: 124-schema-tactic-detector
plan: "04"
subsystem: flaws_service / tactic_detector integration
tags: [tactic-detection, flaws-service, integration, both-color]
dependency_graph:
  requires: ["124-01", "124-02", "124-03"]
  provides: ["TACDET-04", "tactic-field-population-in-classify-path"]
  affects: ["app/services/flaws_service.py", "tests/services/test_flaws_service.py"]
tech_stack:
  added: []
  patterns: ["_detect_tactic_for_flaw helper extraction", "ply-parity side-to-move from piece-placement FEN"]
key_files:
  modified:
    - app/services/flaws_service.py
    - tests/services/test_flaws_service.py
decisions:
  - "Extracted _detect_tactic_for_flaw helper so _build_flaw_record stays within nesting/LOC limits"
  - "Set board_before.turn from ply parity (n%2) after chess.Board(piece_placement_fen) because board_fen() strips side-to-move metadata and chess.Board() defaults to white to move"
metrics:
  duration: "~30 minutes (continued from previous session)"
  completed: "2026-06-18"
  tasks_completed: 2
  files_modified: 2
status: complete
---

# Phase 124 Plan 04: Tactic Detector Integration Summary

Wire `detect_tactic_motif` into `_build_flaw_record` so that `classify_game_flaws` and `backfill_flaws.py` populate tactic fields for both colors with no new engine call (TACDET-04).

## One-liner

`detect_tactic_motif` wired into `_build_flaw_record` via `_detect_tactic_for_flaw` helper; both-color tactic fields populated from stored PV with ply-parity side-to-move fix and None/malformed guards.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Call detect_tactic_motif inside _build_flaw_record | `aae1e33e` | app/services/flaws_service.py |
| 2 | Both-color + None-PV integration tests | `9bb3c558` | app/services/flaws_service.py, tests/services/test_flaws_service.py |

## What Was Built

### Task 1: `_detect_tactic_for_flaw` helper + `_build_flaw_record` wiring

Added `_detect_tactic_for_flaw(n, fen_map, positions)` helper before `_build_flaw_record` in `app/services/flaws_service.py`:
- Reads `pv = positions[n+1].pv` guarded by `n+1 < len(positions)` (Pitfall 1)
- Reads `move_san_of_flaw = positions[n].move_san` and `fen_before_flaw = fen_map.get(n, "")`
- Early-returns `(None, None, None)` when any of the three is falsy
- Sets `board_before.turn` from ply parity after `chess.Board(piece_placement_fen)` (see Deviations)
- Wraps `parse_san` in `try/except (ValueError, chess.IllegalMoveError)` for malformed input (Pitfall 6)
- Calls `detect_tactic_motif(board_after_flaw, pv)` and returns the tuple

`_build_flaw_record` calls `_detect_tactic_for_flaw` and passes the three returned values into `FlawRecord(tactic_motif_int=..., tactic_piece=..., tactic_confidence=...)`.

### Task 2: `TestTacticIntegration` test class

Added `_make_pos_with_pv` helper and `TestTacticIntegration` class to `tests/services/test_flaws_service.py` with three tests:

1. **`test_both_color_detection`**: PGN `"1. e4 e5 2. Bc4 d5 3. f3 Bg4 *"` with white blunder at ply 4 (f3??, PV=d5c4) and black blunder at ply 5 (Bg4??, PV=f3g4). Both FlawRecords carry non-None `tactic_motif_int` (hanging-piece detector fires for both). Proves Phase 113 both-color pass flows through tactic detection.

2. **`test_none_pv_leaves_tactic_fields_none`**: Removes PV from positions[5] (lichess-eval-only case). White's flaw at ply 4 has `tactic_motif_int=None` and no exception raised (T-124-07 guard verified).

3. **`test_malformed_move_san_leaves_tactic_fields_none`**: Sets `positions[4].move_san = "INVALID!!!"`. The try/except branch catches `IllegalMoveError` and all three tactic fields remain None without raising.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] chess.Board(piece_placement_fen) defaults to white to move**
- **Found during:** Task 2 test run (black FlawRecords had tactic_motif_int=None)
- **Issue:** `fen_map` stores `board.board_fen()` (piece-placement only, per CLAUDE.md). `chess.Board(piece_placement_fen)` defaults to `chess.WHITE` to move. For odd plies (black mover), `board_before.parse_san(black_san)` raised `chess.IllegalMoveError` because white's legal moves don't include black's moves. The except block silently returned `(None, None, None)`, so all black flaws had no tactic motif.
- **Fix:** Added `board_before.turn = chess.WHITE if n % 2 == 0 else chess.BLACK` after `chess.Board(fen_before_flaw)` in `_detect_tactic_for_flaw`.
- **Files modified:** app/services/flaws_service.py
- **Commit:** `9bb3c558`

## Known Stubs

None. Tactic fields are fully populated from stored PV — no placeholder values.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. The integration reads only already-stored `game_positions.pv` (internal data) with no new compute surface.

## Self-Check: PASSED
