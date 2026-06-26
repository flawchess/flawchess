# Phase 124: Schema + Tactic Detector - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/tactic_detector.py` | service | transform (pure CPU) | `app/services/flaws_service.py` (module shape) + `app/services/endgame_service.py:108` (IntEnum encoding) | role-match |
| `app/models/game_flaw.py` | model | — | existing nullable SmallInteger columns in same file (lines 44-50) | exact |
| `app/repositories/game_flaws_repository.py` | repository | CRUD | same file — `flaw_record_to_row` pattern (lines 42-116) | exact |
| `app/services/flaws_service.py` | service | transform | same file — `FlawRecord` TypedDict + `_build_flaw_record` (lines 119-377) | exact |
| `alembic/versions/<ts>_phase_124_tactic_motifs.py` | migration | — | `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py` | exact |
| `tests/services/test_tactic_detector.py` | test | — | `tests/services/test_flaws_service.py` (`_make_pos` pattern + class layout) | role-match |

---

## Pattern Assignments

### `app/services/tactic_detector.py` (new service module, pure CPU transform)

**Analogs:**
- `app/services/endgame_service.py` lines 108-129 — IntEnum + bidirectional dicts pattern
- `app/schemas/endgames.py` line 16 — Literal type alias pattern
- `app/services/flaws_service.py` lines 1-15, 34-50 — module docstring + named-constants block

**Module docstring pattern** (`flaws_service.py` lines 1-15):
```python
"""Tactic-motif detector for Phase 124 (TACDET-01/02/03/04).

Pure Python/CPU transform over a stored Stockfish refutation PV.
No I/O, no DB, no Stockfish calls. Input: board_after_flaw (chess.Board)
+ pv_str (space-joined UCI from game_positions.pv). Output: (motif, piece, confidence).
"""
```

**Named-constants block** (`flaws_service.py` lines 34-50 pattern):
```python
# --- Named constants (CLAUDE.md: no magic numbers) ---

# Piece values (cook.py convention): used by fork, skewer, hanging-piece, capturing-defender.
_PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 99,
}

# Core detectors fire with this confidence (cook is boolean — no gradations).
TACTIC_CONFIDENCE_HIGH: int = 100

# Severity gate (D-05): only mistakes and blunders get motif detection.
# Tunable constant — do not hardcode.
TACTIC_MIN_SEVERITY: frozenset[str] = frozenset({"mistake", "blunder"})
```

**IntEnum + bidirectional dicts pattern** (`endgame_service.py` lines 108-129):
```python
class EndgameClassInt(IntEnum):
    """Integer encoding for endgame_class column (SmallInteger, 2 bytes per row).
    Maps 1:1 to EndgameClass Literal strings. Per D-06."""
    ROOK = 1
    MINOR_PIECE = 2
    ...

_INT_TO_CLASS: dict[int, EndgameClass] = {
    1: "rook",
    2: "minor_piece",
    ...
}

_CLASS_TO_INT: dict[EndgameClass, int] = {v: k for k, v in _INT_TO_CLASS.items()}
```

**Apply this pattern as** (copy structure, rename):
```python
class TacticMotifInt(IntEnum):
    """Integer encoding for tactic_motif column (SmallInteger). Maps 1:1 to TacticMotif
    Literal strings. Values must never be reordered — existing DB rows encode these ints."""
    FORK = 1
    HANGING_PIECE = 2
    PIN = 3
    SKEWER = 4
    DOUBLE_CHECK = 5
    DISCOVERED_ATTACK = 6
    BACK_RANK_MATE = 7
    MATE = 8
    DEFLECTION = 9
    ATTRACTION = 10
    INTERMEZZO = 11
    X_RAY = 12
    INTERFERENCE = 13
    SELF_INTERFERENCE = 14
    CLEARANCE = 15
    CAPTURING_DEFENDER = 16
    SACRIFICE = 17
    SMOTHERED_MATE = 18
    ANASTASIA_MATE = 19
    HOOK_MATE = 20
    ARABIAN_MATE = 21
    BODEN_MATE = 22
    DOUBLE_BISHOP_MATE = 23
    DOVETAIL_MATE = 24

TacticMotif = Literal[
    "fork", "hanging-piece", "pin", "skewer", "double-check", "discovered-attack",
    "back-rank-mate", "mate",
    "deflection", "attraction", "intermezzo", "x-ray", "interference",
    "self-interference", "clearance", "capturing-defender", "sacrifice",
    "smothered-mate", "anastasia-mate", "hook-mate", "arabian-mate",
    "boden-mate", "double-bishop-mate", "dovetail-mate",
]

_INT_TO_MOTIF: dict[int, TacticMotif] = {
    1: "fork", 2: "hanging-piece", 3: "pin", 4: "skewer", 5: "double-check",
    6: "discovered-attack", 7: "back-rank-mate", 8: "mate",
    9: "deflection", 10: "attraction", 11: "intermezzo", 12: "x-ray",
    13: "interference", 14: "self-interference", 15: "clearance",
    16: "capturing-defender", 17: "sacrifice",
    18: "smothered-mate", 19: "anastasia-mate", 20: "hook-mate",
    21: "arabian-mate", 22: "boden-mate", 23: "double-bishop-mate",
    24: "dovetail-mate",
}

_MOTIF_TO_INT: dict[TacticMotif, int] = {v: k for k, v in _INT_TO_MOTIF.items()}
```

**Public API function signature** (RESEARCH.md §Integration Point):
```python
def detect_tactic_motif(
    board_after_flaw: chess.Board,
    pv_str: str,
) -> tuple[int | None, int | None, int | None]:
    """Detect the highest-priority tactic motif from the refutation PV.

    Args:
        board_after_flaw: Position immediately after the flawed move was played.
                          board_after_flaw.turn is the refuting side (pov).
        pv_str: Space-joined UCI refutation line from game_positions.pv.

    Returns:
        (tactic_motif_int, tactic_piece, tactic_confidence) where:
        - tactic_motif_int: TacticMotifInt value or None if no detector fired.
        - tactic_piece: chess.PieceType int (1-6) or None (per-motif semantic D-12).
        - tactic_confidence: 0-100 or None when tactic_motif_int is None.
    """
```

---

### `app/models/game_flaw.py` (add 3 nullable SmallInteger columns)

**Analog:** same file, lines 44-50 (`tempo` column — the exact nullable SmallInteger pattern):
```python
# From game_flaw.py lines 44-50:
# Tempo family: 0=low-clock, 1=hasty, 2=unrushed; NULL when no clock data.
tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

# Phase family: 0=opening, 1=middlegame, 2=endgame (denormalized from game_positions.phase).
phase: Mapped[int] = mapped_column(SmallInteger, nullable=False)
```

**Apply this pattern as** (add after `fen` column at line 66):
```python
# Tactic family (Phase 124 — D-01): all nullable SmallInteger.
# tactic_motif: TacticMotifInt enum (1-24); NULL = no detector fired.
# tactic_piece: python-chess PieceType (1=PAWN,2=KNIGHT,3=BISHOP,4=ROOK,5=QUEEN,6=KING)
#               per-motif semantic per D-12; NULL for ambiguous cases.
# tactic_confidence: winner-confidence 0-100; NULL when tactic_motif is NULL.
tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

**Import already present:** `from typing import Optional` and `from sqlalchemy import SmallInteger` are both already in `game_flaw.py` line 14. No new imports needed.

---

### `app/repositories/game_flaws_repository.py` (extend `flaw_record_to_row`)

**Analog:** same file, lines 27-116 — the full existing mapping pattern.

**Encoding maps pattern** (lines 27-36):
```python
# From game_flaws_repository.py lines 27-36:
_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}
_TEMPO_INT: dict[str, int] = {"low-clock": 0, "hasty": 1, "unrushed": 2}
_PHASE_INT: dict[str, int] = {"opening": 0, "middlegame": 1, "endgame": 2}
```

**Return dict extension** (lines 100-116):
```python
# Current return dict in flaw_record_to_row (lines 100-116):
return {
    "user_id": user_id,
    "game_id": game_id,
    "ply": flaw["ply"],
    "severity": _SEVERITY_INT[severity],
    "tempo": tempo_int,
    "phase": phase_int,
    "is_miss": "miss" in tags,
    "is_lucky": "lucky" in tags,
    "is_reversed": "reversed" in tags,
    "is_squandered": "squandered" in tags,
    "fen": flaw["fen"],
}
```

**Extend return dict** by appending three fields following the same `flaw[key]` pattern:
```python
    "tactic_motif": flaw.get("tactic_motif_int"),       # int (TacticMotifInt) or None
    "tactic_piece": flaw.get("tactic_piece"),            # int (chess.PieceType) or None
    "tactic_confidence": flaw.get("tactic_confidence"),  # int 0-100 or None
```

**Note:** Use `.get()` not direct key access because these are new optional TypedDict fields — `.get()` returns None for keys absent from old FlawRecord construction paths.

---

### `app/services/flaws_service.py` (extend `FlawRecord` + `_build_flaw_record`)

**Analog:** same file — `FlawRecord` TypedDict (lines 119-130), `_build_flaw_record` (lines 351-377).

**FlawRecord TypedDict** (lines 119-130 — the pattern to extend):
```python
class FlawRecord(TypedDict):
    ply: int
    fen: str
    side: Literal["white", "black"]
    severity: FlawSeverity
    tags: list[FlawTag]
    es_before: float
    es_after: float
    move_san: str | None
```

**Add three optional fields** (TypedDict supports optional via `total=False` or `NotRequired` — use the same untyped approach the existing tags use; all three default to None):
```python
    tactic_motif_int: int | None   # TacticMotifInt value; None = no detector fired
    tactic_piece: int | None       # chess.PieceType (1-6) or None per D-12
    tactic_confidence: int | None  # 0-100 or None when tactic_motif_int is None
```

**`_build_flaw_record` current return** (lines 368-377):
```python
return FlawRecord(
    ply=n,
    fen=fen_map.get(n, ""),
    side=mover,
    severity=severity,
    tags=[],
    es_before=es_before,
    es_after=es_after,
    move_san=positions[n].move_san,
)
```

**Extend with detector call** (insert before the `return`, following RESEARCH.md §Integration Point pattern):
```python
# Tactic detection (Phase 124, D-04): read pv from positions[n+1], detect motif.
# Guard: pv is None for lichess-eval-only games (no full_evals_completed_at).
tactic_motif_int: int | None = None
tactic_piece_val: int | None = None
tactic_confidence: int | None = None

fen_before_flaw = fen_map.get(n, "")
pv: str | None = positions[n + 1].pv if n + 1 < len(positions) else None
move_san_of_flaw = positions[n].move_san

if fen_before_flaw and pv and move_san_of_flaw:
    board_before = chess.Board(fen_before_flaw)
    try:
        flaw_move = board_before.parse_san(move_san_of_flaw)
        board_after_flaw = board_before.copy()
        board_after_flaw.push(flaw_move)
        tactic_motif_int, tactic_piece_val, tactic_confidence = detect_tactic_motif(
            board_after_flaw, pv
        )
    except (ValueError, chess.IllegalMoveError):
        pass  # malformed move_san or FEN — leave all three as None (Pitfall 6)
```

**Import to add** at top of `flaws_service.py`:
```python
from app.services.tactic_detector import TacticMotif, detect_tactic_motif
```

(`chess` is already imported at line 21.)

---

### `alembic/versions/<ts>_phase_124_tactic_motifs.py` (new migration)

**Analog:** `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py` — simplest recent nullable-column-addition migration.

**Full structure to copy** (phase_123 lines 1-57):
```python
"""Phase 124: Add tactic_motif, tactic_piece, tactic_confidence to game_flaws.

Three nullable SmallInteger columns. Adding nullable columns to PostgreSQL 18
is a pure catalog update — no table rewrite, no extended lock on the game_flaws
table. Safe to run inline at deploy time via deploy/entrypoint.sh.

Revision ID: <autogenerate>
Revises: 20260616_120000
Create Date: 2026-06-17 ...
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "<autogenerate>"
down_revision: Union[str, None] = "20260616_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tactic_motif, tactic_piece, tactic_confidence to game_flaws (no backfill)."""
    op.add_column("game_flaws", sa.Column("tactic_motif", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_piece", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_confidence", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("game_flaws", "tactic_confidence")
    op.drop_column("game_flaws", "tactic_piece")
    op.drop_column("game_flaws", "tactic_motif")
```

**Critical rule** (from RESEARCH.md §Migration note): migrations must NOT import live app constants. Use literal `sa.SmallInteger()`, not `from app.models.game_flaw import GameFlaw`.

---

### `tests/services/test_tactic_detector.py` (new test file)

**Analog:** `tests/services/test_flaws_service.py` — the `_make_pos` pattern (lines 51-83) + class-per-feature layout.

**Test module header** (copy from `test_flaws_service.py` lines 1-11 pattern):
```python
"""Unit tests for app.services.tactic_detector.

Covers TACDET-01/02/03: motif fixture tests, priority-order tiebreak, precision harness.
No DB required — all tests use chess.Board in-memory.
"""
import chess
import pytest

from app.services.tactic_detector import (
    TacticMotifInt,
    detect_tactic_motif,
    _INT_TO_MOTIF,
    _MOTIF_TO_INT,
)
```

**`_make_pos` extension pattern** (lines 51-83 — instantiate ORM objects without DB):
```python
# From test_flaws_service.py lines 51-83:
def _make_pos(ply: int, eval_cp: int | None = None, ...) -> GamePosition:
    pos = GamePosition()
    pos.ply = ply
    pos.eval_cp = eval_cp
    ...  # set every column the service reads
    return pos
```

**Extend for tactic_detector tests**:
```python
def _make_pos_with_pv(ply: int, pv: str | None = None, move_san: str | None = None) -> GamePosition:
    """Build a GamePosition with pv and move_san fields for tactic_detector tests."""
    pos = GamePosition()
    pos.ply = ply
    pos.pv = pv
    pos.move_san = move_san
    pos.eval_cp = None
    pos.eval_mate = None
    pos.clock_seconds = None
    pos.phase = 1
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KP_KP"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos
```

**Fixture format** (per RESEARCH.md §Fixture format):
```python
# Each fixture: (fen_before_flaw, move_san_of_flaw, pv_str, expected_motif)
# Test reconstructs board_after_flaw by pushing move_san onto fen_before_flaw.
_FORK_FIXTURES: list[tuple[str, str, str, str]] = [
    ("fen1...", "Nf5", "d7d5 f5e7", "fork"),
    ...  # 10-15 positives from prod flaws (game 975197, user 44 is a verified example)
]
```

**Precision harness** (from RESEARCH.md §Precision measurement harness):
```python
def _compute_precision(results: list[tuple[str | None, str | None]]) -> float:
    """(predicted, expected) pairs. Returns TP / (TP + FP)."""
    tp = sum(1 for pred, exp in results if pred == exp and exp is not None)
    fp = sum(1 for pred, exp in results if pred is not None and pred != exp)
    return tp / (tp + fp) if (tp + fp) > 0 else 1.0
```

**Test class layout** (from `test_flaws_service.py` class-per-concern pattern):
```python
class TestTacticMotifInt:
    """Verify enum values and bidirectional dict roundtrip."""

class TestForkDetector:
    """Fixture-based precision tests for fork (Core 8, ≥90% bar)."""

class TestHangingPieceDetector:
    """..."""

# ... one class per motif family ...

class TestPriorityOrder:
    """D-07: mate > geometric > tier-3 > hanging-piece tiebreak."""

class TestPrecisionBars:
    """D-10: aggregate precision harness per tier."""
```

---

## Shared Patterns

### Python-chess Board Instantiation (no DB)
**Source:** `tests/services/test_flaws_service.py` lines 51-83 (`_make_pos`)
**Apply to:** `test_tactic_detector.py` — SQLAlchemy ORM objects can be instantiated without a session for attribute access.

### Literal type + IntEnum split (service layer vs schema layer)
**Source:** `app/schemas/endgames.py` line 16 (`EndgameClass = Literal[...]`) + `app/services/endgame_service.py` lines 108-129 (`EndgameClassInt`, `_INT_TO_CLASS`, `_CLASS_TO_INT`)
**Apply to:** `tactic_detector.py` — define `TacticMotif = Literal[...]` and `TacticMotifInt(IntEnum)` together in the service module for Phase 124 (Phase 126 can move the Literal to `app/schemas/tactics.py` when the API needs it).

### Named constants block
**Source:** `app/services/flaws_service.py` lines 34-93
**Apply to:** `tactic_detector.py` — all thresholds and fixed values (piece values, confidence constants, severity gate) extracted as named constants before function definitions.

### Nullable SmallInteger ORM column
**Source:** `app/models/game_flaw.py` line 47 (`tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)`)
**Apply to:** Three new columns in same file. `Optional` from `typing` and `SmallInteger` from `sqlalchemy` are already imported.

### Migration: no-backfill nullable ADD COLUMN
**Source:** `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py` lines 39-57
**Apply to:** Phase 124 migration — identical pattern, three columns instead of two, targeting `game_flaws` table.

---

## No Analog Found

None — all files have close analogs in the codebase.

---

## Metadata

**Analog search scope:** `app/services/`, `app/models/`, `app/repositories/`, `alembic/versions/`, `tests/services/`
**Files scanned:** 8 source files read directly
**Pattern extraction date:** 2026-06-17
