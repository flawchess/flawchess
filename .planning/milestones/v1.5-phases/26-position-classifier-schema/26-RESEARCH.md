# Phase 26: Position Classifier & Schema - Research

**Researched:** 2026-03-23
**Domain:** Chess position classification (python-chess) + SQLAlchemy 2.x model extension + Alembic migration
**Confidence:** HIGH

## Summary

Phase 26 is a pure-backend, self-contained module: write `position_classifier.py`, add 7 nullable columns to `game_positions` via Alembic, and cover everything with unit tests. No import wiring (Phase 27), no frontend, no analytics (Phase 28).

All decisions are locked in CONTEXT.md — the algorithms, column names/types, and classification priority order. Research confirms the python-chess API fully supports the required computations with minimal complexity. The `chess.Board.pieces(piece_type, color)` API returns a `SquareSet` (countable, iterable) which is the foundation for every computation in the classifier. The `chess.BB_DARK_SQUARES` and `chess.BB_LIGHT_SQUARES` bitboard constants enable O(1) square-color tests for opposite-color bishop detection.

The only non-trivial design concern is the chunk_size update in `bulk_insert_positions()`: 8 columns → 15 columns requires reducing from 4000 to 2184 (floor(32767/15)). STATE.md incorrectly notes "8 → 12 columns = 2730 rows max" — the actual count is 15 columns (8 existing + 7 new), not 12.

**Primary recommendation:** Implement `classify_position(board: chess.Board) -> PositionClassification` returning a typed dataclass. Keep all classification logic in one pure function with no side effects; tests exercise it directly without DB fixtures.

## Project Constraints (from CLAUDE.md)

- SQLAlchemy 2.x `Mapped[]` + `mapped_column()` syntax (not legacy Column())
- Alembic autogenerate for migrations; run `uv run alembic revision --autogenerate -m "description"`
- python-chess 1.10.x — already a project dependency
- Pydantic v2 throughout; use typed dataclasses or TypedDicts for internal structures
- No magic numbers — all thresholds must be named constants
- Type hints on all function signatures
- pytest for tests; `asyncio_mode = "auto"` in pyproject.toml

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Game Phase Classification (PMETA-01)**
- Material-weight scoring: N=3, B=3, R=5, Q=9 (non-pawn, non-king only)
- Starting phase score = 62
- Opening: phase_score >= 50; Middlegame: 25 <= phase_score < 50; Endgame: phase_score < 25
- Store as string enum: 'opening', 'middlegame', 'endgame'

**D-02: Material Signature Format (PMETA-02)**
- Format: `K[pieces][pawns]_K[pieces][pawns]`
- Piece ordering: Q, R, B, N, P descending value
- Multiple pieces: repeat letter (KRR not KR2)
- Separator: underscore
- Canonical: stronger side first by total material value; if equal, lexicographic
- King always listed, not counted in material value comparison
- Store as String(20)

**D-03: Material Imbalance (PMETA-03)**
- Values: P=100, N=300, B=300, R=500, Q=900
- Imbalance = white_material - black_material (signed integer)
- Positive = white advantage, negative = black advantage
- Includes pawns; store as Integer (centipawns)

**D-04: Endgame Class Categories (PMETA-04)**
- Six mutually exclusive categories, only when game_phase == 'endgame' (NULL otherwise)
- Priority order:
  1. pawn — kings and pawns only, no pieces
  2. pawnless — no pawns either side, any piece combination
  3. rook — rook(s) + possibly pawns, no queens/bishops/knights
  4. minor_piece — bishop(s)/knight(s) + possibly pawns, no rooks/queens
  5. queen — queen(s) + possibly pawns, no rooks/bishops/knights
  6. mixed — multiple piece types with pawns (catch-all)
- Store as String(12)

**D-05: Tactical Indicators**
- has_bishop_pair_white: Boolean — white has 2+ bishops
- has_bishop_pair_black: Boolean — black has 2+ bishops
- has_opposite_color_bishops: Boolean — each side has exactly one bishop on different square colors

**D-06: Database Column Types**
- game_phase: String(12)
- material_signature: String(20)
- material_imbalance: Integer
- endgame_class: String(12)
- has_bishop_pair_white: Boolean
- has_bishop_pair_black: Boolean
- has_opposite_color_bishops: Boolean
- All nullable (backfill pattern: existing rows start NULL)

### Claude's Discretion

User deferred all decisions to Claude: "go for established best practices and important references." The decisions above were collaboratively decided during discussion.

### Deferred Ideas (OUT OF SCOPE)

- Bitboard storage for partial-position queries
- Track user account creation/last login timestamps
- Import wiring (Phase 27)
- Analytics (Phase 28)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PMETA-01 | System computes game phase (opening/middlegame/endgame) for every position during import using material-weight thresholds | Material-weight phase scoring confirmed correct with verified python-chess API (`board.pieces()`). Starting score=62 verified empirically. Early queen trade → 44 (stays middlegame). |
| PMETA-02 | System computes material signature in canonical form (stronger side first, e.g., KRP_KR) for every position during import | Piece string construction with `board.pieces()` verified. Canonical ordering (by material value, then lex for ties) verified empirically. Max length ~33 chars for starting position — CONTEXT.md String(20) limit needs validation; see Open Questions. |
| PMETA-03 | System computes material imbalance in centipawns for every position during import | Straightforward centipawn calculation using `board.pieces()` count × value. Signed integer arithmetic is standard Python. |
| PMETA-04 | System classifies endgame type (rook/minor piece/pawn/queen/mixed/pawnless) for positions in endgame phase | Six-category priority ladder confirmed. NULL when not endgame satisfies success criterion #2. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.10.x | Board state, piece enumeration, square color constants | Already in project; complete API for all required computations |
| SQLAlchemy | 2.x | ORM model extension (`Mapped[]` + `mapped_column()`) | Already in project; project standard |
| Alembic | 1.13.x | Schema migration (autogenerate) | Already in project; project standard |
| pytest | 8.x | Unit testing | Already in project; project standard |

### No New Dependencies

Phase 26 requires zero new packages. All computation uses python-chess, all persistence uses SQLAlchemy/Alembic, all tests use pytest.

**Installation:** None required.

## Architecture Patterns

### Recommended Project Structure

```
app/services/
├── position_classifier.py   # NEW: pure classification logic
├── zobrist.py               # Existing: pattern to mirror
└── ...

app/models/
└── game_position.py         # MODIFY: add 7 new columns

alembic/versions/
└── YYYYMMDD_HHMMSS_xxxx_add_position_metadata_columns.py  # NEW migration

tests/
└── test_position_classifier.py  # NEW: unit tests (no DB fixtures needed)
```

### Pattern 1: Pure Classification Function

**What:** `classify_position(board)` accepts a `chess.Board` and returns a typed dataclass. No I/O, no DB, no async. Pure computation.

**When to use:** Mirrors `compute_hashes(board)` in `zobrist.py` — same input shape, same pure-function contract.

**Example:**
```python
# Source: mirrors app/services/zobrist.py pattern
from dataclasses import dataclass
from typing import Optional
import chess

@dataclass
class PositionClassification:
    game_phase: str           # 'opening' | 'middlegame' | 'endgame'
    material_signature: str   # e.g. 'KQRR_KQR'
    material_imbalance: int   # centipawns, signed
    endgame_class: Optional[str]          # None when not endgame
    has_bishop_pair_white: bool
    has_bishop_pair_black: bool
    has_opposite_color_bishops: bool

def classify_position(board: chess.Board) -> PositionClassification:
    ...
```

### Pattern 2: Named Constants for Thresholds

**What:** All magic numbers extracted to module-level constants.

**When to use:** Mandatory per CLAUDE.md "no magic numbers" rule.

**Example:**
```python
# Phase scoring weights (non-pawn, non-king only)
_PHASE_WEIGHT: dict[int, int] = {
    chess.QUEEN: 9,
    chess.ROOK: 5,
    chess.BISHOP: 3,
    chess.KNIGHT: 3,
}
_STARTING_PHASE_SCORE = 62
_OPENING_THRESHOLD = 50   # phase_score >= this → opening
_ENDGAME_THRESHOLD = 25   # phase_score < this → endgame

# Material imbalance weights (centipawns)
_MATERIAL_VALUE_CP: dict[int, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}

# Piece order for signature string (descending value)
_SIGNATURE_ORDER = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
_SIGNATURE_LETTER: dict[int, str] = {
    chess.QUEEN: 'Q', chess.ROOK: 'R', chess.BISHOP: 'B',
    chess.KNIGHT: 'N', chess.PAWN: 'P',
}
```

### Pattern 3: SQLAlchemy Column Addition

**What:** Add nullable columns using `Mapped[Optional[X]]` with `mapped_column()`.

**When to use:** Matches existing `game_position.py` style.

**Example:**
```python
# Source: app/models/game_position.py existing pattern
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

# In GamePosition class:
game_phase: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
material_signature: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
material_imbalance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
endgame_class: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
has_bishop_pair_white: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
has_bishop_pair_black: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
has_opposite_color_bishops: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
```

### Pattern 4: Alembic Autogenerate Migration

**What:** Autogenerate from model changes, then manually verify the output.

**When to use:** Every schema change. Matches all existing migration files.

**Example workflow:**
```bash
uv run alembic revision --autogenerate -m "add position metadata columns"
# Review generated file in alembic/versions/
uv run alembic upgrade head
```

**Generated migration will look like:**
```python
def upgrade() -> None:
    op.add_column('game_positions', sa.Column('game_phase', sa.String(length=12), nullable=True))
    op.add_column('game_positions', sa.Column('material_signature', sa.String(length=20), nullable=True))
    op.add_column('game_positions', sa.Column('material_imbalance', sa.Integer(), nullable=True))
    op.add_column('game_positions', sa.Column('endgame_class', sa.String(length=12), nullable=True))
    op.add_column('game_positions', sa.Column('has_bishop_pair_white', sa.Boolean(), nullable=True))
    op.add_column('game_positions', sa.Column('has_bishop_pair_black', sa.Boolean(), nullable=True))
    op.add_column('game_positions', sa.Column('has_opposite_color_bishops', sa.Boolean(), nullable=True))
```

### Pattern 5: chunk_size Update in bulk_insert_positions

**What:** Reduce chunk_size constant to account for 7 new columns.

**Current state:** `chunk_size = 4000` with comment "8 columns → max 4095"

**Required change:** 8 columns → 15 columns. `floor(32767 / 15) = 2184`. Use 2100 for safety margin.

**Note:** STATE.md says "8 → 12 columns = 2730", but 8 existing + 7 new = 15 total. The planner must use 15.

```python
# PostgreSQL asyncpg limits query arguments to 32,767.
# Each position row has 15 columns, so max rows per chunk = 32767 / 15 = 2184.
# Use 2100 for safety margin.
chunk_size = 2100
```

### Anti-Patterns to Avoid

- **Async classifier:** `classify_position()` must be synchronous. It's pure computation on an in-memory `chess.Board`, no I/O. Adding `async` would force `await` call sites unnecessarily.
- **DB fixture in classifier tests:** `test_position_classifier.py` needs only `chess.Board` fixtures — no `db_session`, no Alembic migration. Tests run fast without Docker.
- **Mutable default arg for piece weights:** Do not use `dict = {}` as default; use module-level constants.
- **Using `board.fen()` instead of `board.board_fen()`:** CLAUDE.md mandates `board.board_fen()` for position comparison. Classifier does not compare FENs but must not accidentally use the full FEN (which includes castling/en passant side-effects).
- **String(20) overflow for starting position:** The full starting position signature `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP` is 33 characters. The classifier will never be called on the starting position during a real game (phase_score=62 → opening, endgame_class=NULL, but signature IS computed for all positions). The signature must be computed correctly regardless of game phase. See Open Questions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Piece enumeration | Loop over 64 squares | `board.pieces(piece_type, color)` | Returns `SquareSet` directly; handles internal bitboard |
| Square color detection | Modular arithmetic on file+rank | `chess.BB_DARK_SQUARES & chess.BB_SQUARES[sq]` | One-line bitwise test using library constants |
| Piece count | Manual counter | `len(board.pieces(piece_type, color))` | `SquareSet.__len__` is O(1) via `popcount` |
| Board iteration | Manual board scan | `chess.scan_forward(board.occupied_co[color])` | Same pattern as `zobrist.py`; efficient bitboard scan |

**Key insight:** python-chess exposes the entire bitboard layer. Any manual iteration or arithmetic is both slower and less readable than the library API.

## Common Pitfalls

### Pitfall 1: String(20) Too Short for Full-Material Signatures

**What goes wrong:** The material signature for a starting position is `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP` = 33 characters. If the column is `String(20)`, writing a starting-position signature truncates or raises.

**Why it happens:** CONTEXT.md says `String(20)` with "max realistic length ~16 chars", but that applies to endgame/middlegame positions (pieces traded off), not opening positions with full material. In practice, Phase 27 will backfill ALL positions including ply=0 of each game (full starting position).

**How to avoid:** Either increase to `String(40)` to handle worst cases, or document that the classifier is only called after the position has diverged from the starting material (but Phase 27 backfills ply=0). Verify max possible signature length before locking String(20).

**Warning signs:** Test with `chess.Board()` (full starting position) and verify the signature fits in the column.

**Verified:** `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP` is 33 chars. `String(20)` will not fit. Consider `String(40)`.

### Pitfall 2: Endgame Class Assigned When phase_score == 25 (Boundary)

**What goes wrong:** Success criterion #2 says endgame_class must be NULL for non-endgame positions. The boundary is `phase_score < 25` for endgame. A position with exactly phase_score=25 is "middlegame" — endgame_class must be NULL.

**Why it happens:** Off-by-one on the threshold: `<` vs `<=`.

**How to avoid:** Use strict `<` for endgame: `phase_score < _ENDGAME_THRESHOLD`. Test the boundary value explicitly.

**Warning signs:** Test with a position that has exactly phase_score=25 (e.g., 4 minor pieces + 1 rook for one side = 3+3+5=11, other side same = 22... needs careful construction).

### Pitfall 3: Endgame Class Priority Order Bugs

**What goes wrong:** The `pawnless` category (priority 2) must be checked BEFORE `rook`, `minor_piece`, etc. A K+R vs K (pawnless rook endgame) must not fall through to `mixed`.

**Why it happens:** If `pawnless` check is after `rook` check, K+R vs K would be classified as `rook` correctly — but K+B vs K+N would be `mixed` unless `pawnless` comes first.

**How to avoid:** Implement as explicit `if/elif` chain in the documented priority order (pawn → pawnless → rook → minor_piece → queen → mixed). Test each category independently.

**Warning signs:** Test K vs K+B+N — should be `pawnless` not `minor_piece`.

### Pitfall 4: Canonical Signature Non-Determinism with Equal Material

**What goes wrong:** When both sides have equal material value, lexicographic ordering of the string determines which goes first. If implementation compares Python strings inconsistently (e.g., comparing `'KQRRBBNN'` vs the other side), the result could depend on which side was "white" vs "black".

**Why it happens:** The canonical form must be identical regardless of which color the user played (success criterion #2: "symmetric material produces the same canonical signature regardless of which color the user played").

**How to avoid:** When material values are equal, use `sorted([white_str, black_str])[0]` as the first element. Test by computing signature from a board, then swapping colors and verifying the signature is identical.

### Pitfall 5: chunk_size Column Count Error

**What goes wrong:** STATE.md says "8 → 12 columns" for the chunk_size update. The actual count is 8 existing + 7 new = 15 columns. Using 12 would allow chunk_size=2730 when the true safe maximum is 2184.

**Why it happens:** An off-by-three error in STATE.md (was written when only PMETA columns were planned, before tactical indicators were added).

**How to avoid:** Count columns from the model directly: id, game_id, user_id, ply, full_hash, white_hash, black_hash, move_san, clock_seconds = 9 existing (not 8 — `id` is included in INSERT), plus 7 new = 16? Actually `id` is a serial/autoincrement and may not be in the INSERT dict. Verify by counting keys in the `position_rows` dict. The comment in `bulk_insert_positions()` says "8 columns" — confirm against the actual dict keys passed in `import_service.py`.

## Code Examples

Verified patterns from official sources and project code:

### Phase Score Computation
```python
# Source: verified empirically against python-chess 1.10.x
import chess

_PHASE_WEIGHT: dict[int, int] = {
    chess.QUEEN: 9,
    chess.ROOK: 5,
    chess.BISHOP: 3,
    chess.KNIGHT: 3,
}
_ENDGAME_THRESHOLD = 25
_OPENING_THRESHOLD = 50

def _compute_phase_score(board: chess.Board) -> int:
    return sum(
        len(board.pieces(pt, color)) * w
        for pt, w in _PHASE_WEIGHT.items()
        for color in (chess.WHITE, chess.BLACK)
    )

def _compute_game_phase(board: chess.Board) -> str:
    score = _compute_phase_score(board)
    if score >= _OPENING_THRESHOLD:
        return "opening"
    elif score >= _ENDGAME_THRESHOLD:
        return "middlegame"
    else:
        return "endgame"
```

### Material Signature Construction
```python
# Source: verified empirically against python-chess 1.10.x
_SIGNATURE_ORDER = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
_SIGNATURE_LETTER: dict[int, str] = {
    chess.QUEEN: 'Q', chess.ROOK: 'R', chess.BISHOP: 'B',
    chess.KNIGHT: 'N', chess.PAWN: 'P',
}
_MATERIAL_VALUE_CP: dict[int, int] = {
    chess.PAWN: 100, chess.KNIGHT: 300, chess.BISHOP: 300,
    chess.ROOK: 500, chess.QUEEN: 900,
}

def _side_string(board: chess.Board, color: chess.Color) -> str:
    return 'K' + ''.join(
        _SIGNATURE_LETTER[pt] * len(board.pieces(pt, color))
        for pt in _SIGNATURE_ORDER
    )

def _side_material(board: chess.Board, color: chess.Color) -> int:
    return sum(
        len(board.pieces(pt, color)) * v
        for pt, v in _MATERIAL_VALUE_CP.items()
    )

def _compute_material_signature(board: chess.Board) -> str:
    white_str = _side_string(board, chess.WHITE)
    black_str = _side_string(board, chess.BLACK)
    white_val = _side_material(board, chess.WHITE)
    black_val = _side_material(board, chess.BLACK)
    if white_val > black_val:
        return f"{white_str}_{black_str}"
    elif black_val > white_val:
        return f"{black_str}_{white_str}"
    else:
        first, second = sorted([white_str, black_str])
        return f"{first}_{second}"
```

### Opposite-Color Bishop Detection
```python
# Source: verified empirically against python-chess 1.10.x
def _compute_opposite_color_bishops(board: chess.Board) -> bool:
    white_bishops = board.pieces(chess.BISHOP, chess.WHITE)
    black_bishops = board.pieces(chess.BISHOP, chess.BLACK)
    if len(white_bishops) != 1 or len(black_bishops) != 1:
        return False
    wb_sq = next(iter(white_bishops))
    bb_sq = next(iter(black_bishops))
    wb_dark = bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[wb_sq])
    bb_dark = bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[bb_sq])
    return wb_dark != bb_dark
```

### Endgame Class Classification
```python
# Source: CONTEXT.md D-04 priority order
def _compute_endgame_class(board: chess.Board) -> Optional[str]:
    has_pieces = lambda pt, color: len(board.pieces(pt, color)) > 0
    has_any_piece = lambda color: any(
        has_pieces(pt, color)
        for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
    )
    has_pawn = lambda color: has_pieces(chess.PAWN, color)

    has_pieces_white = has_any_piece(chess.WHITE)
    has_pieces_black = has_any_piece(chess.BLACK)
    has_pawns_white = has_pawn(chess.WHITE)
    has_pawns_black = has_pawn(chess.BLACK)

    # Priority 1: pawn endgame — kings and pawns only
    if not has_pieces_white and not has_pieces_black:
        return "pawn"
    # Priority 2: pawnless — no pawns either side
    if not has_pawns_white and not has_pawns_black:
        return "pawnless"
    # Priority 3: rook endgame — rooks + possibly pawns, no other pieces
    has_queen = lambda c: has_pieces(chess.QUEEN, c)
    has_bishop = lambda c: has_pieces(chess.BISHOP, c)
    has_knight = lambda c: has_pieces(chess.KNIGHT, c)
    has_rook = lambda c: has_pieces(chess.ROOK, c)
    if (not has_queen(chess.WHITE) and not has_queen(chess.BLACK)
            and not has_bishop(chess.WHITE) and not has_bishop(chess.BLACK)
            and not has_knight(chess.WHITE) and not has_knight(chess.BLACK)):
        return "rook"
    # Priority 4: minor piece — bishops/knights + possibly pawns, no rooks/queens
    if (not has_queen(chess.WHITE) and not has_queen(chess.BLACK)
            and not has_rook(chess.WHITE) and not has_rook(chess.BLACK)):
        return "minor_piece"
    # Priority 5: queen — queens + possibly pawns, no rooks/bishops/knights
    if (not has_rook(chess.WHITE) and not has_rook(chess.BLACK)
            and not has_bishop(chess.WHITE) and not has_bishop(chess.BLACK)
            and not has_knight(chess.WHITE) and not has_knight(chess.BLACK)):
        return "queen"
    # Priority 6: mixed — catch-all
    return "mixed"
```

### Test Pattern (No DB Required)
```python
# Source: mirrors test_zobrist.py structure
import chess
import pytest
from app.services.position_classifier import classify_position

@pytest.fixture
def board_kpk():
    """King + pawn vs King — pure pawn endgame."""
    b = chess.Board(fen=None)
    b.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    b.set_piece_at(chess.E4, chess.Piece(chess.PAWN, chess.WHITE))
    b.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    return b

def test_pawn_endgame_class(board_kpk):
    result = classify_position(board_kpk)
    assert result.game_phase == "endgame"
    assert result.endgame_class == "pawn"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Column()` in SQLAlchemy | `Mapped[] + mapped_column()` | SQLAlchemy 2.0 | Project already uses new style |
| `board.fen()` for position id | `board.board_fen()` (piece-only) | FlawChess CLAUDE.md | Avoids castling/en passant in comparison |

## Open Questions

1. **String(20) too short for material_signature**
   - What we know: Starting position signature = `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP` = 33 chars. CONTEXT.md says String(20).
   - What's unclear: Is the classifier expected to be called on opening positions? Phase 27 backfill includes ply=0, which is always the starting position for a new game.
   - Recommendation: Use `String(40)` in the migration. The planner should raise this with the user or choose String(40) under Claude's discretion (since all decisions were deferred to Claude). A 40-char column costs nothing at scale but avoids silent truncation.

2. **Exact column count for chunk_size**
   - What we know: `bulk_insert_positions()` comment says "8 columns". STATE.md says "8 → 12 columns = 2730".
   - What's unclear: Does the INSERT dict include `id`? The `position_rows` dicts passed in `import_service.py` need to be verified.
   - Recommendation: Read `import_service.py` and count keys in the position_rows dict before updating chunk_size. The planner should read `import_service.py` and confirm the exact column count.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-chess | Position classification | ✓ | >=1.10.0 (in pyproject.toml) | — |
| PostgreSQL (Docker) | Migration testing | ✓ | 18 (docker-compose.dev.yml) | — |
| pytest | Unit tests | ✓ | >=8.0.0 (in pyproject.toml) | — |
| Alembic | Migration | ✓ | >=1.13.0 (in pyproject.toml) | — |

No missing dependencies. All required tools are available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_position_classifier.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PMETA-01 | opening/middlegame/endgame classification with correct boundaries | unit | `uv run pytest tests/test_position_classifier.py -x` | ❌ Wave 0 |
| PMETA-01 | Early queen trade stays middlegame (phase_score=44 >= 25) | unit | same | ❌ Wave 0 |
| PMETA-01 | All major pieces off → endgame (phase_score=24 < 25) | unit | same | ❌ Wave 0 |
| PMETA-02 | Symmetric material: same signature regardless of color played | unit | same | ❌ Wave 0 |
| PMETA-02 | Asymmetric material: stronger side first | unit | same | ❌ Wave 0 |
| PMETA-03 | Imbalance = white_cp - black_cp, signed | unit | same | ❌ Wave 0 |
| PMETA-04 | All 6 endgame class categories assigned correctly | unit | same | ❌ Wave 0 |
| PMETA-04 | endgame_class is NULL for opening/middlegame positions | unit | same | ❌ Wave 0 |
| Migration | 7 new columns added cleanly; `alembic upgrade head` passes | integration | `uv run alembic upgrade head` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_position_classifier.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_position_classifier.py` — covers all PMETA-01 through PMETA-04 scenarios
- [ ] `app/services/position_classifier.py` — the module under test
- [ ] Alembic migration file — covers migration test

*(Existing `tests/conftest.py` with `starting_board` and `empty_board` fixtures is reusable.)*

## Sources

### Primary (HIGH confidence)
- python-chess library — `chess.Board.pieces()`, `chess.BB_DARK_SQUARES`, `chess.BB_LIGHT_SQUARES`, `chess.BB_SQUARES` verified by empirical testing against installed version
- `app/services/zobrist.py` — Classifier module design mirrors this pattern directly
- `app/models/game_position.py` — Model column style confirmed
- `alembic/versions/20260316_180737_*.py` — Migration autogenerate pattern confirmed
- `tests/conftest.py` — Test fixture patterns (board fixtures, DB session pattern)
- `tests/test_zobrist.py` — Unit test style without DB for pure computation functions
- `app/repositories/game_repository.py` — chunk_size location confirmed (line 88)

### Secondary (MEDIUM confidence)
- `.planning/phases/26-position-classifier-schema/26-CONTEXT.md` — All algorithm decisions locked
- `.planning/STATE.md` — Critical constraints; note the "8 → 12 columns" figure may be off (see Open Questions)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all existing project libs
- Architecture: HIGH — directly mirrors `zobrist.py` pattern, all API calls empirically verified
- Pitfalls: HIGH — String(20) overflow verified empirically (33 chars > 20 limit); chunk_size discrepancy verified by arithmetic

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (python-chess API is stable; Alembic autogenerate pattern stable)
