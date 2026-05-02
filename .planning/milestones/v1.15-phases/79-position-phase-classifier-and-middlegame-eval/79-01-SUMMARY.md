---
phase: 79-position-phase-classifier-and-middlegame-eval
plan: "01"
subsystem: position-classifier
tags:
  - position-classifier
  - phase-classification
  - divider
  - alembic
  - schema

dependency_graph:
  requires:
    - "app/repositories/endgame_repository.py (ENDGAME_PIECE_COUNT_THRESHOLD=6)"
    - "app/models/game_position.py (existing SmallInteger columns)"
  provides:
    - "app/services/position_classifier.py: is_endgame(), is_middlegame(), PositionClassification.phase"
    - "app/models/game_position.py: phase: Mapped[Optional[int]] column"
    - "alembic migration 1efcc66a7695: adds nullable phase SmallInteger to game_positions"
    - "tests/test_position_classifier.py: TestPhaseClassification (11 Divider-sourced assertions)"
  affects:
    - "79-02: import-path integration (reads phase from classify_position, writes to DB)"
    - "79-03: backfill script extension (phase column UPDATE pass + middlegame eval pass)"

tech_stack:
  added:
    - "Literal[0, 1, 2] type annotation on PositionClassification.phase (Pydantic/dataclass)"
  patterns:
    - "frozen dataclass extension with new field"
    - "cross-module constant import (ENDGAME_PIECE_COUNT_THRESHOLD from endgame_repository)"
    - "pure predicate functions operating on already-derived inputs (no second board scan)"
    - "nullable SmallInteger column with transient-nullability comment pattern"
    - "Alembic revision with no embedded backfill (op.add_column only)"

key_files:
  created:
    - "alembic/versions/20260502_203948_1efcc66a7695_add_phase_column_to_game_positions.py"
  modified:
    - "app/services/position_classifier.py"
    - "app/models/game_position.py"
    - "tests/test_position_classifier.py"

decisions:
  - "ENDGAME_PIECE_COUNT_THRESHOLD imported from endgame_repository (single source of truth, not redefined)"
  - "is_endgame checked before is_middlegame in classify_position so PHASE-INV-01 holds by construction (D-79-06)"
  - "phase: Literal[0, 1, 2] used on dataclass field for type safety; bare int in PlyData TypedDict (Plan 79-02)"
  - "Migration body is op.add_column only -- no embedded backfill per D-79-11"
  - "FEN for piece_count=11 test: rn1qk1nr/pppppppp/8/8/8/8/PPPPPPPP/RN1QKBNR (white Q+R+R+B+N+N=6, black Q+R+R+N+N=5)"
  - "FEN for endgame-precedence test: 4k3/1q1n4/8/4r3/3R4/8/1Q1N4/4K3 (piece_count=6, mixedness=159)"

metrics:
  duration: "8 minutes"
  completed: "2026-05-02"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
---

# Phase 79 Plan 01: Foundation (Divider predicates + phase column) Summary

Port lichess Divider.scala `isEndGame` / `isMidGame` predicates into `position_classifier.py`, extend `PositionClassification` with a `phase: Literal[0, 1, 2]` field, add the `phase` SmallInteger column to `game_positions` via Alembic, and lock the parity test fixture.

## What Was Built

### Task 1: Divider predicates and phase field

`app/services/position_classifier.py` extended with:

- `from typing import Literal` + `from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD`
- Two new module-level constants: `MIDGAME_MAJORS_AND_MINORS_THRESHOLD = 10` and `MIDGAME_MIXEDNESS_THRESHOLD = 10`
- `is_endgame(piece_count: int) -> bool` predicate (Divider `isEndGame`)
- `is_middlegame(piece_count: int, backrank_sparse: bool, mixedness: int) -> bool` predicate (Divider `isMidGame`)
- `PositionClassification` dataclass gains `phase: Literal[0, 1, 2]` field
- `classify_position()` refactored to hoist helpers to locals, then derive `phase` inline with `is_endgame` checked first (D-79-06)

**Threshold constants (all match lichess Divider.scala defaults):**

| Constant | Value | Source |
|----------|-------|--------|
| `ENDGAME_PIECE_COUNT_THRESHOLD` | 6 | `endgame_repository.py` (imported, not redefined) |
| `MIDGAME_MAJORS_AND_MINORS_THRESHOLD` | 10 | new in `position_classifier.py` |
| `MIDGAME_MIXEDNESS_THRESHOLD` | 10 | new in `position_classifier.py` |

### Task 2: TestPhaseClassification (11 Divider-sourced tests)

`tests/test_position_classifier.py` gains `TestPhaseClassification` class with 11 tests. All expected phase values sourced from Divider.scala algorithm, not from the Python implementation under test.

**FEN choices (all verified empirically):**

| Test | FEN | Metrics | Expected phase |
|------|-----|---------|----------------|
| starting position | standard start | piece_count=14, bs=False, mix=0 | 0 |
| KQR vs KQR | `3qk2r/.../R2QK3` | piece_count=4 | 2 |
| KR vs KR | `4k2r/.../R3K3` | piece_count=2 | 2 |
| KQ+8P vs KQ+8P | `3qk3/pppp.../3QK3` | piece_count=2 | 2 |
| piece_count=11, full backranks | `rn1qk1nr/.../RN1QKBNR` | pc=11, bs=False, mix=0 | 0 |
| piece_count=10 | `r1bqk1nr/.../R1BQK1NR` | pc=10, bs=False | 1 |
| castled both sides | `r4rk1/.../R4RK1` | pc=8, bs=True, mix=80 | 1 |
| open center | `rnbqkbnr/pp3ppp/...` | pc=14, bs=False, mix=114 | 1 |
| mixedness=9 boundary | pure predicate call | is_middlegame(11,False,9) | False |
| mixedness=10 boundary | pure predicate call | is_middlegame(11,False,10) | True |
| endgame precedence | `4k3/1q1n4/...` | pc=6, mix=159 | 2 |

Key deviation from plan FEN suggestions: the plan's `piece_count=11` FEN (`rn1qkbnr/.../RNBQKB1R`) gave `piece_count=13, mixedness=20` -- the plan noted "executor MUST verify and adjust". Used `rn1qk1nr/.../RN1QKBNR` instead (verified: pc=11, bs=False, mix=0). The plan's `endgame-precedence` FEN (`4k3/p1p1p1p1/1P1P1P1P/8/8/8/8/3RK2R`) gave pc=2, not pc=6. Used `4k3/1q1n4/8/4r3/3R4/8/1Q1N4/4K3` (pc=6, mix=159). Both FEN adjustments are within the scope the plan explicitly anticipated.

### Task 3: Model column + Alembic migration

- `app/models/game_position.py`: `phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` added after `mixedness`
- Alembic revision `1efcc66a7695` (`down_revision: "c92af8282d1a"`): `op.add_column` only -- no embedded backfill (D-79-11)
- Up/down/up cycle verified on dev DB; `phase | smallint | YES` confirmed in `information_schema.columns`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Adjustment] FEN corrections for two test cases**

- **Found during:** Task 2 FEN verification
- **Issue:** Plan's suggested FEN for `test_piece_count_eleven_mid_development_phase_opening` produced pc=13 (not 11); plan's suggested FEN for `test_endgame_takes_precedence_over_middlegame` produced pc=2 (not 6). The plan explicitly noted the executor MUST verify and adjust FENs.
- **Fix:** Replaced both FENs with empirically verified alternatives that produce the documented metrics. No change to test expectations or phase logic.
- **Files modified:** `tests/test_position_classifier.py`

**2. [Rule 3 - Cleanup] Inadvertent edits to main repo files**

- **Found during:** Task 1 implementation
- **Issue:** Edits were initially made to the main project repo (`/home/aimfeld/Projects/Python/flawchess/`) instead of the git worktree. Reverted with `git checkout --` on the main repo.
- **Fix:** Wrote changes to the correct worktree path. No functional impact.

**3. [Rule 3 - Cleanup] Extraneous alembic autogenerate changes stripped**

- **Found during:** Task 3 migration generation
- **Issue:** `alembic revision --autogenerate` detected pre-existing schema drift (Float type changes on `clock_seconds`, `white_accuracy`, `black_accuracy`; llm_logs index changes). These are unrelated to this plan.
- **Fix:** Stripped all non-phase changes from the generated migration, leaving only `op.add_column("game_positions", sa.Column("phase", ...))` in upgrade and `op.drop_column("game_positions", "phase")` in downgrade. Scope boundary respected.

## Known Stubs

None. All implementations are complete and non-placeholder.

## Threat Flags

None. This plan adds a classification column computed from existing data. No new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `app/services/position_classifier.py` -- FOUND and modified (Task 1)
- `app/models/game_position.py` -- FOUND and modified (Task 3)
- `tests/test_position_classifier.py` -- FOUND and modified (Task 2)
- `alembic/versions/20260502_203948_1efcc66a7695_add_phase_column_to_game_positions.py` -- FOUND (Task 3)
- Commits exist: `7c4e1d6` (Task 1), `c102eb5` (Task 2), `1a011a7` (Task 3)
- All 48 tests in `test_position_classifier.py` pass
- `uv run ty check` and `uv run ruff check` pass on all modified files
- Alembic up/down/up cycle verified on dev DB
