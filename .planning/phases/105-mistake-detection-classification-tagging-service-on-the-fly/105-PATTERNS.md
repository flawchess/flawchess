# Phase 105: Mistake-Detection + Classification + Tagging Service — Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 4 new files
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/mistakes_service.py` | service | transform (per-ply iteration) | `app/services/eval_utils.py` | role-match (module-level constants + Literal types); `endgame_service.py` for ES derivation pattern |
| `app/repositories/mistakes_repository.py` | repository | CRUD (single SELECT + order) | `app/repositories/endgame_repository.py` | role-match (AsyncSession, select/where/order_by, `list(result.scalars().all())`) |
| `tests/services/test_mistakes_service.py` | test | unit (pure, no DB) | `tests/services/test_eval_utils.py` | exact (class-per-behavior, pytest.approx, no fixtures) |
| `tests/test_mistakes_repository.py` | test | integration (DB-backed) | `tests/test_endgame_repository.py` | exact (_seed_game + _seed_game_position helpers, `db_session`, `pytest.mark.asyncio`) |

---

## Pattern Assignments

### `app/services/mistakes_service.py` (service, transform)

**Primary analog:** `app/services/eval_utils.py`
**Secondary analog:** `app/services/endgame_service.py` (ES derivation structure)

#### Module docstring pattern (eval_utils.py lines 1–33)

```python
"""<One-line summary of what the module exposes.>

Used by Phase 105 / SEED-036. Derives per-ply mistake severity and
attribution tags from stored Stockfish evals. No I/O, no DB.
The module is unit-testable in isolation; see
tests/services/test_mistakes_service.py.

Two output types:
  list[FlawRecord]   analyzed game — one entry per user flaw
  GameNotAnalyzed    chess.com / unanalyzed lichess game
"""
```

#### Imports pattern (eval_utils.py lines 35–41 + endgame_service.py lines 15–97)

```python
from __future__ import annotations

import io
import math
from typing import Literal, TypedDict

import chess
import chess.pgn

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.eval_utils import eval_cp_to_expected_score
```

#### Module-level named constants (eval_utils.py lines 38–41 style — no magic numbers)

```python
# Lichess-aligned severity thresholds on the [0,1] ES scale.
# Lichess uses [−1, +1] winningChances with cutoffs 0.10/0.20/0.30; our scale
# is (winningChances + 1) / 2, so thresholds halve. See CONTEXT.md §Severity.
INACCURACY_DROP: float = 0.05
MISTAKE_DROP: float = 0.10
BLUNDER_DROP: float = 0.15

# Mate Option B: map mate eval to ±1000 cp before the sigmoid (CONTEXT.md §Mate).
# Do NOT use eval_mate_to_expected_score (hard 1.0/0.0) for drop math.
MATE_CP_EQUIVALENT: int = 1000

# Eval coverage gate: fraction of plies with non-null eval required for "analyzed".
EVAL_COVERAGE_MIN: float = 0.90

# Attribution tag thresholds
FROM_WINNING_ES: float = 0.85       # tag: from-winning
RESULT_WIN_THRESHOLD: float = 0.70  # tag: result-changing (winning zone)
RESULT_DRAW_THRESHOLD: float = 0.40 # tag: result-changing (drawing zone)

# Tempo thresholds — relative to base_time_seconds (see RESEARCH §Pattern 6).
# [ASSUMED] initial values; tunable once real data is available.
TIME_PRESSURE_CLOCK_FRACTION: float = 0.05  # < 5% of base = low clock
HASTY_MOVE_FRACTION: float = 0.01           # < 1% of base = fast move on comfortable clock
TIME_PRESSURE_CLOCK_ABS_SECONDS: float = 30.0   # fallback when base_time unknown
HASTY_MOVE_ABS_SECONDS: float = 5.0             # fallback

# Oracle closeness tolerance for sanity test against Lichess game-level columns.
# [ASSUMED] — allows ≤2 off per color per severity (mate-handling divergence).
SANITY_TOLERANCE: int = 2
```

#### Literal type aliases (eval_utils.py + CLAUDE.md ty rules)

```python
# Use Literal[...] for all fields with a fixed value set (CLAUDE.md §Type safety).
FlawSeverity = Literal["inaccuracy", "mistake", "blunder"]
FlawTag = Literal[
    "miss", "unpunished", "from-winning", "result-changing",
    "time-pressure", "hasty", "knowledge-gap",
    "phase-opening", "phase-middlegame", "phase-endgame",
]
TempoTag = Literal["time-pressure", "hasty", "knowledge-gap"]
```

#### TypedDict output contract pattern (zobrist.py PlyData style)

```python
class FlawRecord(TypedDict):
    ply: int                          # half-move number (0-indexed)
    fen: str                          # board_fen() at this ply (piece placement only)
    side: Literal["white", "black"]   # mover who made the flawed move
    severity: FlawSeverity
    tags: list[FlawTag]               # ordered, additive, orthogonal
    es_before: float                  # mover-POV ES before the flaw
    es_after: float                   # mover-POV ES after the flaw
    move_san: str | None              # SAN from positions[N].move_san


class GameNotAnalyzed(TypedDict):
    reason: Literal["no_engine_analysis"]
    eval_coverage: float              # fraction 0.0–1.0


GameMistakesResult = list[FlawRecord] | GameNotAnalyzed
```

#### Public function signature (explicit return type, per CLAUDE.md §ty compliance)

```python
def classify_game_mistakes(
    game: Game,
    positions: list[GamePosition],
) -> GameMistakesResult:
    """Derive all user flaws from stored per-ply evals.

    Args:
        game: Game row with result, user_color, base_time_seconds, increment_seconds, pgn.
        positions: All GamePosition rows for this game, ordered by ply ASC.
            Load via mistakes_repository.fetch_game_positions_ordered.

    Returns:
        list[FlawRecord] for analyzed games, GameNotAnalyzed otherwise.
    """
```

#### Private helpers — signature pattern (explicit types, docstrings, from eval_utils.py lines 44–66)

```python
def _ply_to_es(
    pos: GamePosition,
    mover_color: Literal["white", "black"],
) -> float | None:
    """Return mover-POV ES for this ply, or None if eval unavailable.

    Option B mate: maps mate to ±MATE_CP_EQUIVALENT cp before sigmoid.
    Do NOT call eval_mate_to_expected_score here — that returns hard 1.0/0.0.
    """

def _classify_severity(drop: float) -> FlawSeverity | None:
    """Map a mover-POV ES drop to a severity label, or None if below threshold."""

def _classify_tempo(
    move_time: float | None,
    clock_after: float | None,
    base_time: int | None,
) -> TempoTag:
    """Every flaw carries exactly one tempo tag. Defaults to knowledge-gap on missing data."""

def _compute_eval_coverage(positions: list[GamePosition]) -> float:
    """Fraction of positions with non-null eval_cp or eval_mate (0.0–1.0)."""

def _recompute_fen_map(pgn: str) -> dict[int, str]:
    """Return {ply: board_fen()} for every ply by replaying the PGN with python-chess."""
```

---

### `app/repositories/mistakes_repository.py` (repository, CRUD)

**Analog:** `app/repositories/endgame_repository.py`

#### Module docstring pattern (endgame_repository.py lines 1–11)

```python
"""Mistakes repository: DB queries for mistake-detection service.

Functions:
- fetch_game_positions_ordered: all GamePosition rows for one game, ordered by ply ASC
"""
```

#### Imports pattern (endgame_repository.py lines 13–26)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_position import GamePosition
```

#### Core SELECT pattern (endgame_repository.py body — select/where/order_by/scalars)

```python
async def fetch_game_positions_ordered(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> list[GamePosition]:
    """Load all GamePosition rows for one game, ordered by ply ASC.

    user_id is included in the WHERE clause as an ownership guard — the
    composite PK is (game_id, user_id, ply), so this filter is index-backed.
    """
    stmt = (
        select(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.user_id == user_id)
        .order_by(GamePosition.ply)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

Key points to copy:
- `async def` + `AsyncSession` parameter (never synchronous, per project ORM pattern)
- `select(Model).where(...).order_by(...)` — SQLAlchemy 2.x `select()` API, not legacy 1.x
- `list(result.scalars().all())` — standard project pattern for returning typed list of ORM rows
- No SQL in the service layer; service receives `list[GamePosition]` already loaded

---

### `tests/services/test_mistakes_service.py` (test, unit — pure, no DB)

**Analog:** `tests/services/test_eval_utils.py`

#### Module docstring + imports pattern (test_eval_utils.py lines 1–25)

```python
"""Unit tests for app.services.mistakes_service.

Covers Phase 105 LIBG-02/06/07: severity classification, 8 attribution tags,
TypedDict output contract, eval coverage gate, mate Option B, FEN recomputation.
No DB required — all tests construct GamePosition objects in memory.

Sign convention: eval_cp / eval_mate are white-perspective (Stockfish / python-chess).
"""

import pytest

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.mistakes_service import (
    BLUNDER_DROP,
    EVAL_COVERAGE_MIN,
    FROM_WINNING_ES,
    INACCURACY_DROP,
    MATE_CP_EQUIVALENT,
    MISTAKE_DROP,
    SANITY_TOLERANCE,
    FlawRecord,
    GameMistakesResult,
    GameNotAnalyzed,
    classify_game_mistakes,
    _classify_severity,
    _classify_tempo,
    _compute_eval_coverage,
    _ply_to_es,
)
```

#### In-memory GamePosition factory (test_endgame_repository.py lines 99–137 adapted for no-DB use)

```python
def _make_pos(
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Build a GamePosition with eval/clock fields for pure unit testing (no DB flush)."""
    pos = GamePosition.__new__(GamePosition)
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = move_san
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

#### Test class structure (test_eval_utils.py class-per-behavior pattern)

```python
class TestSeverityClassification:
    def test_below_inaccuracy_threshold_returns_none(self) -> None: ...
    def test_inaccuracy_threshold_boundary(self) -> None: ...
    def test_mistake_threshold_boundary(self) -> None: ...
    def test_blunder_threshold_boundary(self) -> None: ...
    def test_highest_band_wins(self) -> None: ...

class TestMateOptionB:
    def test_mate_maps_to_cp_equivalent_not_hard_one(self) -> None: ...
    def test_negative_mate_maps_to_negative_cp_equivalent(self) -> None: ...
    def test_mate_to_non_mate_transition_not_always_blunder(self) -> None: ...

class TestEvalCoverageGate:
    def test_zero_coverage_returns_not_analyzed(self) -> None: ...
    def test_full_coverage_minus_final_ply_is_analyzed(self) -> None: ...
    def test_below_threshold_returns_not_analyzed(self) -> None: ...

class TestAttributionTags:
    def test_miss_tag_when_preceding_opponent_blunder(self) -> None: ...
    def test_unpunished_tag_on_blunder_not_recovered(self) -> None: ...
    def test_from_winning_tag_when_es_before_above_threshold(self) -> None: ...
    def test_exactly_one_tempo_tag_per_flaw(self) -> None: ...
    def test_phase_tag_maps_phase_column(self) -> None: ...

class TestFlawRecordShape:
    def test_all_required_fields_present(self) -> None: ...
    def test_fen_uses_board_fen_not_full_fen(self) -> None: ...

class TestOracleCloseness:
    def test_derived_counts_close_to_lichess_columns(self) -> None: ...
```

#### Assertion pattern (test_eval_utils.py lines 37–45)

```python
# Use pytest.approx for float comparisons
assert _ply_to_es(pos, "white") == pytest.approx(0.591, abs=1e-3)

# Use exact equality for Literal values
assert flaw["severity"] == "blunder"

# Use set containment for tags (order-independent)
assert "from-winning" in flaw["tags"]
assert sum(t in flaw["tags"] for t in ("time-pressure", "hasty", "knowledge-gap")) == 1
```

---

### `tests/test_mistakes_repository.py` (test, integration — DB-backed)

**Analog:** `tests/test_endgame_repository.py`

#### Module pattern (test_endgame_repository.py lines 1–96)

```python
"""Integration tests for app.repositories.mistakes_repository.

Uses a real PostgreSQL database through the db_session fixture (rolled-back
transaction per test). Covers:
- fetch_game_positions_ordered: returns rows sorted by ply ASC
- fetch_game_positions_ordered: user_id ownership guard (different user returns empty)
- fetch_game_positions_ordered: empty result for unknown game_id
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.mistakes_repository import fetch_game_positions_ordered
```

#### DB seed helpers (test_endgame_repository.py lines 50–137 — copy these helper shapes exactly)

Use `_seed_game` (insert Game, `await session.flush()`) and `_seed_game_position` (insert GamePosition with `eval_cp`, `eval_mate`, `clock_seconds`, `phase`, `move_san`). Key difference from endgame repo tests: the mistakes repo test seeds `clock_seconds`, `phase`, and `move_san` explicitly; eval fields are central.

```python
@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    from tests.conftest import ensure_test_user
    for uid in [99999]:
        await ensure_test_user(db_session, uid)


async def _seed_game(session: AsyncSession, *, user_id: int = 99999) -> Game:
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=move_san,
        clock_seconds=clock_seconds,
        phase=phase,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        piece_count=2,
        material_count=1000,
        material_signature="KP_KP",
        material_imbalance=0,
        endgame_class=None,
    )
    session.add(pos)
    await session.flush()
    return pos
```

#### Test structure (test_endgame_repository.py lines 145–180 pattern)

```python
class TestFetchGamePositionsOrdered:
    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_game(self, db_session: AsyncSession) -> None: ...

    @pytest.mark.asyncio
    async def test_positions_sorted_by_ply_asc(self, db_session: AsyncSession) -> None: ...

    @pytest.mark.asyncio
    async def test_ownership_guard_different_user_returns_empty(
        self, db_session: AsyncSession
    ) -> None: ...
```

---

## Shared Patterns

### Literal types for fixed-value fields
**Source:** `app/services/eval_utils.py` (function signatures) + CLAUDE.md §Type safety
**Apply to:** All function signatures in `mistakes_service.py` and `mistakes_repository.py`

```python
# Never use bare str for "white"/"black", "inaccuracy"/"mistake"/"blunder".
# Use Literal[...] or the defined type alias.
user_color: Literal["white", "black"]
severity: FlawSeverity  # = Literal["inaccuracy", "mistake", "blunder"]
```

### No magic numbers — module-level named constants
**Source:** `app/services/eval_utils.py` lines 38–41; `app/repositories/endgame_repository.py` lines 28–39
**Apply to:** All threshold values in `mistakes_service.py`

Every numeric threshold must be a named module-level constant with a comment explaining what it means and where it comes from. See the constants block in the Pattern Assignment above.

### Explicit return type annotations
**Source:** CLAUDE.md §ty compliance; `eval_utils.py` lines 44–66
**Apply to:** All functions in both new files

```python
# Every function must have an explicit return type — ty will fail the build without it.
async def fetch_game_positions_ordered(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> list[GamePosition]: ...
```

### SQLAlchemy 2.x async SELECT (never legacy 1.x)
**Source:** `app/repositories/endgame_repository.py` body
**Apply to:** `mistakes_repository.py`

```python
# Always: select(Model).where(...).order_by(...)
# Never: session.query(Model)...
stmt = select(GamePosition).where(...).order_by(GamePosition.ply)
result = await session.execute(stmt)
return list(result.scalars().all())
```

### `board.board_fen()` — not `board.fen()`
**Source:** CLAUDE.md §Chess logic; confirmed at `app/services/zobrist.py` line 270
**Apply to:** `_recompute_fen_map` in `mistakes_service.py`

```python
# board_fen() = piece placement only (castling/en passant excluded).
# board.fen() is wrong here — produces position-variant strings.
fens[ply] = board.board_fen()
```

### `eval_cp_to_expected_score` reuse (never re-implement the sigmoid)
**Source:** `app/services/eval_utils.py` lines 44–66
**Apply to:** `_ply_to_es` in `mistakes_service.py`

Import and call the existing function. Do NOT call `eval_mate_to_expected_score` from drop math — only the cp-based sigmoid is correct for per-ply drops (see CONTEXT.md §Mate and RESEARCH §Pitfall 3).

### TypedDict for structured outputs (not dataclass)
**Source:** `app/services/zobrist.py` `PlyData`; `app/services/normalization.py` `NormalizedGame`
**Apply to:** `FlawRecord`, `GameNotAnalyzed` in `mistakes_service.py`

Use `TypedDict` (not `@dataclass`) for the serializable output contract consumed by downstream services and endpoints. TypedDict is lighter and aligns with existing per-item structured outputs in the project.

---

## No Analog Found

All four new files have analogs. No gaps.

---

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/models/`, `tests/services/`, `tests/`
**Files read:** `app/services/eval_utils.py`, `app/models/game_position.py`, `app/models/game.py`, `app/repositories/endgame_repository.py`, `tests/services/test_eval_utils.py`, `tests/test_endgame_repository.py`, `tests/services/test_endgame_service.py` (partial)
**Pattern extraction date:** 2026-06-05
