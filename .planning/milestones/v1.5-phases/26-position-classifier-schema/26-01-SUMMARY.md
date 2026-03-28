---
phase: 26-position-classifier-schema
plan: "01"
subsystem: backend
tags: [classifier, chess, endgame, python-chess, tdd]
dependency_graph:
  requires: []
  provides:
    - classify_position pure function (Board -> PositionClassification)
    - PositionClassification dataclass (7 fields)
  affects:
    - Phase 27 import wiring (will call classify_position per position)
tech_stack:
  added: []
  patterns:
    - TDD with pytest (RED -> GREEN -> refactor)
    - Frozen dataclass for immutable return type
    - Named constants for all thresholds (no magic numbers)
    - Private helpers prefixed with _ (mirrors zobrist.py style)
key_files:
  created:
    - app/services/position_classifier.py
    - tests/test_position_classifier.py
  modified: []
decisions:
  - "Bare kings (K vs K) classified as 'pawnless', not 'pawn' — pawn class requires at least one pawn on board"
  - "Used python-chess BB_DARK_SQUARES bitboard for opposite-color bishop detection"
  - "Frozen dataclass chosen over TypedDict for type safety and immutability"
metrics:
  duration: "5 minutes"
  completed: "2026-03-23"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
---

# Phase 26 Plan 01: Position Classifier Summary

**One-liner:** Pure `classify_position(board)` function returning game phase, canonical material signature, signed centipawn imbalance, endgame class, and three tactical indicators via frozen dataclass.

## What Was Built

`app/services/position_classifier.py` — a pure, synchronous, zero-I/O classification module. Mirrors the style of `zobrist.py`: module docstring, private helpers prefixed with `_`, documented public function. No DB access, no async, no side effects.

`tests/test_position_classifier.py` — 41 unit tests organized in 5 test classes covering all classification logic.

### Implementation Details

**Named constants (CLAUDE.md compliance):**
- `_PHASE_WEIGHT = {QUEEN: 9, ROOK: 5, BISHOP: 3, KNIGHT: 3}`
- `_OPENING_THRESHOLD = 50`, `_ENDGAME_THRESHOLD = 25`
- `_MATERIAL_VALUE_CP = {PAWN: 100, KNIGHT: 300, BISHOP: 300, ROOK: 500, QUEEN: 900}`

**Game phase logic:** Sum non-pawn/non-king weights for both sides combined. Starting position = 62. Thresholds: >= 50 opening, >= 25 middlegame, < 25 endgame.

**Material signature:** Canonical form with stronger side first (by centipawn total), lexicographic tie-break for equal material. Starting position = `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP` (33 chars, fits in String(40) column).

**Endgame class priority chain:** pawn (only kings+pawns) → pawnless (no pawns) → rook (rooks+pawns only) → minor_piece (bishops/knights+pawns, no rooks/queens) → queen (queens+pawns, no rooks/minors) → mixed (catch-all). Only assigned when `game_phase == 'endgame'`.

**Opposite-color bishops:** Uses `chess.BB_DARK_SQUARES & chess.BB_SQUARES[sq]` to determine square color. Both sides must have exactly one bishop on different colored squares.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 5a4d6bb | test | Add failing tests for position classifier (RED) |
| eafa879 | feat | Implement position classifier with all tests passing (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bare kings (K vs K) incorrectly returned 'pawn' endgame class**
- **Found during:** GREEN implementation — test `test_endgame_class_assigned_in_endgame` failed
- **Issue:** Priority 1 (pawn) fired when `not has_any_piece` — but bare kings have no pieces AND no pawns; "pawn" class should require at least one pawn present
- **Fix:** Changed priority 1 condition to `not has_any_piece and has_any_pawn`; bare kings now correctly classified as "pawnless"
- **Files modified:** `app/services/position_classifier.py`
- **Commit:** eafa879

**2. [Rule 1 - Bug] Test used incorrect square color assumptions for opposite-color bishops**
- **Found during:** GREEN implementation — `test_opposite_color_bishops_true` failed
- **Issue:** Test placed bishops on C1 and D8 assuming they were opposite colors, but both are dark squares in python-chess's BB_DARK_SQUARES convention
- **Fix:** Updated test to use C1 (dark) + C8 (light) for opposite-color, and C1 (dark) + D8 (dark) for same-color; added inline comments documenting square colors
- **Files modified:** `tests/test_position_classifier.py`
- **Commit:** eafa879

**3. [Rule 3 - Blocking] Test DB had migration revision from parallel plan-02 agent**
- **Found during:** First test run
- **Issue:** The parallel agent running plan 02 (Alembic migration) had already executed migrations against the shared test DB, leaving revision `38239eef59a8` which doesn't exist in plan-01's branch. Conftest.py session fixture runs `alembic upgrade head` which failed.
- **Fix:** Updated `alembic_version` table in test DB directly back to `b5b8170c0f72` (last known revision in plan-01 branch). Test DB then ran `upgrade head` successfully (no-op since plan-01 adds no migration).
- **Files modified:** None (DB admin fix)
- **Commit:** N/A (not a code change)

## Known Stubs

None — all fields are computed from the live `chess.Board` state. No placeholder values.

## Self-Check: PASSED

Files exist:
- FOUND: app/services/position_classifier.py
- FOUND: tests/test_position_classifier.py

Commits exist:
- FOUND: 5a4d6bb (test RED)
- FOUND: eafa879 (feat GREEN)

Tests: 41/41 passed
