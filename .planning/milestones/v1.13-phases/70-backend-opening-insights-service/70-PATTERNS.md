# Phase 70: Backend opening insights service - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 9 (3 new schemas/services/tests, 1 router edit, 1 repo extend, 1 model edit, 1 alembic migration, 3 test files)
**Analogs found:** 9 / 9

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `app/schemas/opening_insights.py` (NEW) | schema | request-response | `app/schemas/openings.py` (request shape) + `app/schemas/stats.py::OpeningWDL` (str hash) + `app/schemas/insights.py` (Literal idiom) | exact (composite) |
| `app/services/opening_insights_service.py` (NEW) | service | request-response | `app/services/insights_service.py::compute_findings` | exact (single public entry point + Sentry context) |
| `app/repositories/openings_repository.py` (EXTEND, +2 funcs) | repository | CRUD aggregate | `app/repositories/openings_repository.py::query_next_moves` (line 359) + `app/repositories/stats_repository.py::query_top_openings_sql_wdl` (line 209) | exact (same module, same `apply_game_filters` style) |
| `app/routers/insights.py` (EXTEND, +1 route) | router | request-response | `app/routers/insights.py::get_endgame_insights` (line 78) | exact (same router file, mirror route shape) |
| `app/models/game_position.py` (EDIT `__table_args__`) | model | schema | existing `Index("ix_gp_user_endgame_game", ..., postgresql_include=...)` (line 29) | exact (same partial-INCLUDE pattern) |
| `alembic/versions/{rev}_add_gp_user_game_ply_index.py` (NEW) | migration | DDL | `20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` | role-match (same INCLUDE+partial idiom; differs only in CONCURRENTLY which is novel) |
| `tests/test_opening_insights_repository.py` (NEW) | test | DB integration | `tests/test_openings_repository.py` (uses `db_session`, `_seed_game`) | exact |
| `tests/services/test_opening_insights_service.py` (NEW) | test | unit (no DB) | `tests/services/test_insights_service.py` (synthetic Pydantic, AsyncMock) | exact |
| `tests/services/test_opening_insights_arrow_consistency.py` (NEW) | test | static / regex | (no analog — first-of-kind; Phase 63 spec'd `test_endgame_zones_consistency.py` but the file is not present in the tree) | no analog (build per RESEARCH.md spec) |

---

## Pattern Assignments

### `app/schemas/opening_insights.py` (NEW — schema, request-response)

**Analog:** `app/schemas/openings.py` (request shape) + `app/schemas/stats.py::OpeningWDL` (str hash convention).

**Imports pattern** — copy the openings idiom verbatim (`app/schemas/openings.py` lines 1-9):

```python
from typing import Literal
from pydantic import BaseModel, Field
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD
```

**Request model pattern** — mirror `OpeningsRequest` (lines 11-48). Note: `recency` Literal MUST match what `recency_cutoff()` accepts (`"all" | "week" | "month" | "3months" | "6months" | "year" | "3years" | "5years"` — see `openings_service.py:78-86`). Do **NOT** use the endgame `"all_time"` spelling.

```python
class OpeningInsightsRequest(BaseModel):
    recency: Literal[
        "week", "month", "3months", "6months", "year", "3years", "5years", "all"
    ] | None = None
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD
    color: Literal["all", "white", "black"] = "all"
```

**Hash str-form convention** — copy from `app/schemas/stats.py::OpeningWDL` (line 50):

```python
full_hash: str  # String form of 64-bit Zobrist full hash, for synthetic bookmark construction
```

Use this for `entry_full_hash: str` and `resulting_full_hash: str` on `OpeningInsightFinding`.

**Response shape pattern** — `Field(default_factory=list)` (matches `EndgameInsightsReport.recommendations` style):

```python
class OpeningInsightsResponse(BaseModel):
    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
```

**Divergence from analog:** Do **NOT** import or re-use `app/schemas/insights.py::FilterContext` (D-11 explicit). The new file is fully decoupled.

---

### `app/services/opening_insights_service.py` (NEW — service, request-response)

**Analog:** `app/services/insights_service.py::compute_findings` (line 122-199).

**Imports pattern** (copy structure from `insights_service.py` lines 37-77):

```python
import datetime
from typing import Literal

import chess
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opening import Opening
from app.repositories.openings_repository import (
    query_opening_transitions,        # NEW (this phase)
    query_openings_by_hashes,         # NEW (this phase)
)
from app.schemas.opening_insights import (
    OpeningInsightFinding,
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.services.openings_service import recency_cutoff
```

**Module-level constants pattern** (copy idiom from `insights_service.py` lines 82-114, frontend `arrowColor.ts` lines 17-19):

```python
# CONTEXT.md D-28. Mirror frontend arrowColor.ts so opening insights and
# board arrow colors stay in lock-step (CI-enforced via
# tests/services/test_opening_insights_arrow_consistency.py).
MIN_ENTRY_PLY: int = 3
MAX_ENTRY_PLY: int = 16
MIN_GAMES_PER_CANDIDATE: int = 20
LIGHT_THRESHOLD: float = 0.55          # arrowColor.ts LIGHT_COLOR_THRESHOLD/100
DARK_THRESHOLD: float = 0.60           # arrowColor.ts DARK_COLOR_THRESHOLD/100
WEAKNESS_CAP_PER_COLOR: int = 5
STRENGTH_CAP_PER_COLOR: int = 3
```

**Single public entry-point pattern** — copy the shape of `compute_findings` (`insights_service.py` lines 122-141). Sequential `await` on the same session, never `asyncio.gather`:

```python
async def compute_insights(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
) -> OpeningInsightsResponse:
    cutoff = recency_cutoff(request.recency)
    colors_to_query: list[Literal["white", "black"]] = (
        ["white", "black"] if request.color == "all" else [request.color]
    )
    try:
        rows_by_color: dict[str, list[...]] = {}
        for color in colors_to_query:
            rows_by_color[color] = await query_opening_transitions(
                session, user_id, color, ...
            )
    except Exception as exc:
        sentry_sdk.set_context(
            "opening_insights",
            {"user_id": user_id, "request": request.model_dump()},
        )
        sentry_sdk.capture_exception(exc)
        raise
    # ... classify / attribute / dedupe / rank / cap ...
```

**Sentry context capture pattern** — verbatim from `insights_service.py` lines 162-169 (CLAUDE.md §Sentry: never embed variables in error messages):

```python
except Exception as exc:
    sentry_sdk.set_context(
        "opening_insights", {"user_id": user_id, "request": request.model_dump()}
    )
    sentry_sdk.capture_exception(exc)
    raise
```

**FEN replay pattern** — copy from `app/services/openings_service.py` (imports `chess`, `chess.pgn` at lines 9-10). For `Opening.pgn` (space-separated SAN, NOT full PGN — see RESEARCH.md Pitfall 8):

```python
def _reconstruct_entry_fen(opening_pgn: str) -> str:
    board = chess.Board()
    for san in opening_pgn.split():
        board.push_san(san)
    return board.fen()
```

**Display-name "vs. " prefix pattern** — copy from `stats_repository.py` lines 250-260 (apply at the service layer here, not in SQL):

```python
# Apply when attribution's ply parity disagrees with the finding's color.
# Whites end on odd ply (white's last move), blacks on even ply.
user_parity = 1 if finding_color == "white" else 0
if opening.ply_count % 2 != user_parity:
    display_name = f"vs. {opening.name}"
else:
    display_name = opening.name
```

**Divergence from analog:** Unlike `insights_service.py`, this service does **NOT** use `EndgameTabFindings`/`findings_hash`/`as_of` (no caching this phase per D-29). No `_compute_hash`, no two-window orchestration — it issues 1-2 SQL queries (one per active color) and returns immediately.

---

### `app/repositories/openings_repository.py` (EXTEND — repository, CRUD aggregate)

**Analog:** `query_next_moves` in the same file (line 359-434) for the join-and-aggregate skeleton; `query_top_openings_sql_wdl` in `stats_repository.py` (lines 240-289) for the win/loss/draw conditions.

**File-existing import pattern** — already at top of `openings_repository.py` (lines 1-14), reuse:

```python
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD, apply_game_filters
```

For the new function, add `from sqlalchemy import cast, Float` (HAVING float ratio per RESEARCH.md Pitfall 5).

**Win/Loss/Draw conditions pattern** — copy verbatim from `stats_repository.py:240-248`:

```python
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
draw_cond = Game.result == "1/2-1/2"
loss_cond = or_(
    and_(Game.result == "0-1", Game.user_color == "white"),
    and_(Game.result == "1-0", Game.user_color == "black"),
)
```

**Function signature pattern** — copy from `query_next_moves` (lines 359-371). Use `Sequence[str]` not `list[str]` for filter params (CLAUDE.md §ty compliance):

```python
async def query_opening_transitions(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> list[Row[Any]]:
```

**LAG transition CTE pattern** — RESEARCH.md Pattern 2 (no direct analog in repo for `func.lag`; this is the new bit):

```python
transitions_cte = (
    select(
        GamePosition.game_id,
        GamePosition.ply,
        GamePosition.move_san,
        func.lag(GamePosition.full_hash).over(
            partition_by=GamePosition.game_id,
            order_by=GamePosition.ply,
        ).label("entry_hash"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.ply.between(1, MAX_ENTRY_PLY + 1),  # 1..17
    )
    .cte("transitions")
)
```

**`apply_game_filters` chaining pattern** — copy from `query_next_moves` lines 428-431:

```python
stmt = apply_game_filters(
    stmt, time_control, platform, rated, opponent_type, recency_cutoff,
    opponent_strength=opponent_strength, elo_threshold=elo_threshold,
)
```

**Note:** Pass `color=None` to `apply_game_filters` (or omit, since it defaults to None). The per-color filter is applied explicitly at the JOIN (`Game.user_color == color`) for self-documenting SQL — see RESEARCH.md anti-pattern note.

**Float HAVING ratio pattern** — RESEARCH.md Pitfall 5 (no analog in repo; cast explicitly):

```python
from sqlalchemy import Float, cast
# In .having(...):
or_(
    cast(wins, Float) / cast(n_games, Float) > LIGHT_THRESHOLD,
    cast(losses, Float) / cast(n_games, Float) > LIGHT_THRESHOLD,
)
```

**Second new function `query_openings_by_hashes`** — copy idiom from `query_transposition_counts` (lines 437-458):

```python
async def query_openings_by_hashes(
    session: AsyncSession,
    full_hashes: list[int],
) -> dict[int, Opening]:
    if not full_hashes:
        return {}
    stmt = select(Opening).where(
        Opening.full_hash.is_not(None),     # RESEARCH.md Pitfall 6
        Opening.full_hash.in_(full_hashes),
    )
    rows = await session.execute(stmt)
    by_hash: dict[int, Opening] = {}
    for opening in rows.scalars():
        existing = by_hash.get(opening.full_hash)
        if existing is None or opening.ply_count > existing.ply_count:
            by_hash[opening.full_hash] = opening
    return by_hash
```

**Divergence from analog:** `query_next_moves` uses a self-join (`gp1 + gp2`) that requires a known `target_hash`. Phase 70's transition CTE uses `LAG()` instead because we want **all** transitions across **all** entries in one pass (~60 entries vs 60 round-trips).

---

### `app/routers/insights.py` (EXTEND — router, request-response)

**Analog:** existing `@router.post("/endgame")` in the same file (lines 78-139).

**Existing module pattern** — `router = APIRouter(prefix="/insights", tags=["insights"])` already declared at line 38. Add the new route as `@router.post("/openings", ...)` — relative path, NOT `/insights/openings` (CLAUDE.md §Router Convention).

**POST + JSON body pattern** (D-13 chose POST for URL-length safety on `time_control[]`/`platform[]`). The endgame route uses query params; for openings, accept a JSON body via `OpeningInsightsRequest`. Pattern:

```python
from app.schemas.opening_insights import (
    OpeningInsightsRequest, OpeningInsightsResponse,
)
from app.services.opening_insights_service import compute_insights

@router.post("/openings", response_model=OpeningInsightsResponse)
async def get_opening_insights(
    request: OpeningInsightsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OpeningInsightsResponse:
    return await compute_insights(session=session, user_id=user.id, request=request)
```

**Divergence from analog (D-14 explicit):** Do **NOT** call `_validate_full_history_filters` — that gate is endgame-LLM-specific. Phase 70's contract is "every filter reshapes findings" (INSIGHT-CORE-01). No 400 gate.

**Divergence from analog (no exception → HTTP mapping):** The endgame route maps `InsightsRateLimitExceeded` / `InsightsValidationFailure` / `InsightsProviderError` to 429/502. Phase 70 has no LLM, so let exceptions propagate to the global Sentry handler — no `except` block in the router.

---

### `app/models/game_position.py` (EDIT `__table_args__` — model, schema)

**Analog:** `ix_gp_user_endgame_game` already in the same `__table_args__` tuple (lines 29-34) — exact same `postgresql_where` + `postgresql_include` pattern.

**Insert into existing tuple** (line 11-35):

```python
__table_args__ = (
    Index("ix_gp_user_full_hash", "user_id", "full_hash"),
    Index("ix_gp_user_white_hash", "user_id", "white_hash"),
    Index("ix_gp_user_black_hash", "user_id", "black_hash"),
    Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),
    Index(
        "ix_gp_user_endgame_class",
        "user_id", "endgame_class",
        postgresql_where=text("endgame_class IS NOT NULL"),
    ),
    Index(
        "ix_gp_user_endgame_game",
        "user_id", "game_id", "endgame_class", "ply",
        postgresql_where=text("endgame_class IS NOT NULL"),
        postgresql_include=["material_imbalance"],
    ),
    # NEW (Phase 70):
    Index(
        "ix_gp_user_game_ply",
        "user_id", "game_id", "ply",
        postgresql_where=text("ply BETWEEN 1 AND 17"),
        postgresql_include=["full_hash", "move_san"],
        # COLUMN ORDER IS LOAD-BEARING. The opening_insights_service transition
        # CTE uses LAG(full_hash) OVER (PARTITION BY game_id ORDER BY ply); this
        # ordering matches so PostgreSQL streams rows from the index without
        # a re-sort. Do NOT reorder for symmetry with ix_gp_user_full_hash etc.
        # See alembic migration <rev>_add_gp_user_game_ply_index.py for the
        # full rationale and verified perf numbers.
    ),
)
```

**Note:** `text` is already imported at line 3. No new imports.

---

### Alembic migration `{rev}_add_gp_user_game_ply_index.py` (NEW — migration, DDL)

**Analog:** `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` (same INCLUDE + partial idiom).

**Header / revision boilerplate pattern** (copy from latest migration `20260426_drop_eval_depth_eval_source_version_from_games.py`):

```python
"""add ix_gp_user_game_ply partial composite index for opening insights

Revision ID: <generated>
Revises: 6809b7c79eb3
Create Date: 2026-04-27 ...

Phase 70 (v1.13). [...rationale block with perf numbers from CONTEXT.md D-31...]
"""

from alembic import op
import sqlalchemy as sa

revision: str = "<generated>"
down_revision: str | None = "6809b7c79eb3"
branch_labels: str | None = None
depends_on: str | None = None
```

**Index DDL pattern** — analog `befacc0fce23` lines 27-34, BUT add `postgresql_concurrently=True` and wrap in `op.get_context().autocommit_block()`:

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_gp_user_game_ply",
            "game_positions",
            ["user_id", "game_id", "ply"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
            postgresql_include=["full_hash", "move_san"],
        )

def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_gp_user_game_ply",
            table_name="game_positions",
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
        )
```

**Divergence from analog (FIRST IN PROJECT):** No prior migration uses `postgresql_concurrently=True` or `autocommit_block()`. The base analog `befacc0fce23` runs inside the default migration transaction; CONCURRENTLY cannot. Source: Alembic cookbook (cited in RESEARCH.md). Risk noted in RESEARCH.md §Risks: deploy-time index build for Hikaru-class user is ~30-60s — verify against `flawchess-prod-db` via SSH tunnel before commit.

---

### `tests/test_opening_insights_repository.py` (NEW — test, DB integration)

**Analog:** `tests/test_openings_repository.py` (uses real PostgreSQL via `db_session` fixture, rolled-back transactions).

**Imports / fixtures pattern** (copy from `test_openings_repository.py` lines 20-42):

```python
import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.openings_repository import query_opening_transitions

@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    from tests.conftest import ensure_test_user
    for uid in [1, 2]:
        await ensure_test_user(db_session, uid)
```

**Seed-helper pattern** — copy `_seed_game()` (lines 56-103). Extend for multi-position seeding (Phase 70 needs ply boundary fixtures).

**Boundary test cases required** (RESEARCH.md §Critical Sample Dimensions):
- `test_entry_ply_boundaries` — ply 2 (excluded), 3 (included), 16 (included), 17 (excluded)
- `test_lag_across_game_boundary` — first ply of each game has `entry_hash IS NULL`
- `test_min_games_floor` — n=19 (excluded), n=20 (included), n=21 (included)
- `test_classification_strict_gt` — exactly 0.55 → excluded; 0.551 → included
- `test_severity_boundary` — exactly 0.60 → major; 0.599 → minor

---

### `tests/services/test_opening_insights_service.py` (NEW — test, unit no-DB)

**Analog:** `tests/services/test_insights_service.py` (lines 1-80). Synthetic Pydantic instances, AsyncMock for repo calls, zero DB.

**Imports + helper-factory pattern** — copy from `test_insights_service.py` lines 24-78:

```python
from __future__ import annotations
import math
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.opening_insights import (
    OpeningInsightFinding, OpeningInsightsRequest, OpeningInsightsResponse,
)
from app.services.opening_insights_service import (
    LIGHT_THRESHOLD, DARK_THRESHOLD,
    MIN_GAMES_PER_CANDIDATE,
    WEAKNESS_CAP_PER_COLOR, STRENGTH_CAP_PER_COLOR,
    compute_insights,
)
```

**Test classes required** (RESEARCH.md §Critical Sample Dimensions):
- `TestClassificationBoundaries` — 0.549 / 0.550 / 0.551 / 0.599 / 0.600 / 0.650 (both win & loss directions)
- `TestSeverityTier` — minor vs major mapping
- `TestRankingAndCaps` — sort `(severity desc, n_games desc)`, cap 5 weak / 3 strong per section
- `TestDedupeWithinSection` — same `resulting_full_hash` → keep deeper-entry-by-ply_count
- `TestCrossColorPreservation` — same hash in white & black sections → both kept
- `TestAttributionDeepest` — `MAX(ply_count)` wins among multiple `openings.full_hash` matches
- `TestAttributionLineageWalk` — fallback to parent hash when entry has no direct match
- `TestUnnamedLineFallback` — `opening_name == "<unnamed line>"`, `opening_eco == ""`
- `TestColorOptimization` — D-12: when `request.color="white"`, only ONE SQL call made
- `TestDisplayNameVsPrefix` — black-section finding with white-defined opening → `display_name = "vs. London System"`

**Mock pattern** — copy AsyncMock idiom from `test_insights_service.py` line 29:

```python
with patch(
    "app.services.opening_insights_service.query_opening_transitions",
    new_callable=AsyncMock,
) as mock_query:
    mock_query.return_value = [...]
    response = await compute_insights(session=AsyncMock(), user_id=1, request=req)
```

---

### `tests/services/test_opening_insights_arrow_consistency.py` (NEW — test, regex / static)

**Analog:** None in tree (the spec'd `test_endgame_zones_consistency.py` referenced in CONTEXT.md is not present — only the `__pycache__` trace remains). Build from RESEARCH.md spec.

**Pattern (build from scratch):**

```python
"""CI-enforced consistency: opening_insights service constants must match
frontend/src/lib/arrowColor.ts. A future arrow-color tweak that doesn't update
the Python service will fail this test."""
import re
from pathlib import Path

from app.services.opening_insights_service import (
    LIGHT_THRESHOLD, DARK_THRESHOLD,
)

_ARROW_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/arrowColor.ts"

def _extract(name: str) -> int:
    text = _ARROW_TS.read_text()
    m = re.search(rf"{name}\s*=\s*(\d+)", text)
    assert m, f"could not find {name} in arrowColor.ts"
    return int(m.group(1))

def test_light_threshold_matches_frontend() -> None:
    assert _extract("LIGHT_COLOR_THRESHOLD") == int(LIGHT_THRESHOLD * 100)

def test_dark_threshold_matches_frontend() -> None:
    assert _extract("DARK_COLOR_THRESHOLD") == int(DARK_THRESHOLD * 100)
```

**Note (RESEARCH.md):** `MIN_GAMES_FOR_COLOR = 10` in arrowColor.ts is intentionally NOT mirrored — Phase 70 uses `MIN_GAMES_PER_CANDIDATE = 20` for the insights floor (D-33 tightened it). Only the threshold pair is locked together.

---

## Shared Patterns

### Authentication
**Source:** `app/users.py:257` (`current_active_user = fastapi_users.current_user(active=True)`).
**Apply to:** new router endpoint.
```python
from app.users import current_active_user
from app.models.user import User
# in endpoint signature:
user: Annotated[User, Depends(current_active_user)]
# Then pass user.id to compute_insights — never accept user_id from request body.
```

### Async session injection
**Source:** `app/core/database.py::get_async_session` (used everywhere, e.g. `app/routers/insights.py:80`).
**Apply to:** new router endpoint.
```python
from app.core.database import get_async_session
session: Annotated[AsyncSession, Depends(get_async_session)]
```

### Sequential awaits on same session
**Source:** CLAUDE.md §Critical Constraints + `insights_service.py:142-161`.
**Apply to:** `compute_insights` when running both color queries.
```python
# Two color queries — sequential, NEVER asyncio.gather.
rows_white = await query_opening_transitions(session, user_id, "white", ...)
rows_black = await query_opening_transitions(session, user_id, "black", ...)
```

### Sentry context capture
**Source:** `app/services/insights_service.py:162-169`.
**Apply to:** every non-trivial `except` block in the new service.
```python
except Exception as exc:
    sentry_sdk.set_context(
        "opening_insights",
        {"user_id": user_id, "request": request.model_dump()},
    )
    sentry_sdk.capture_exception(exc)
    raise
```

### Pydantic v2 + Literal for fixed enums
**Source:** `app/schemas/insights.py:133-147` (FilterContext) + `app/schemas/openings.py:33-43`.
**Apply to:** every state field on `OpeningInsightsRequest` and `OpeningInsightFinding` (`color`, `classification`, `severity`, `recency`, `opponent_type`, `opponent_strength`).

### Win/Loss/Draw conditions
**Source:** `app/repositories/stats_repository.py:240-248`.
**Apply to:** the new `query_opening_transitions` SQL.

### apply_game_filters chaining
**Source:** `app/repositories/openings_repository.py:428-431`.
**Apply to:** the new `query_opening_transitions` SQL — embed AFTER joining `Game`.

### `recency_cutoff` reuse
**Source:** `app/services/openings_service.py:78-86`.
**Apply to:** `compute_insights` — convert `request.recency` to `datetime.datetime | None` before passing to repo.

### Hash str-form at API boundary
**Source:** `app/schemas/stats.py::OpeningWDL.full_hash:str` (line 50).
**Apply to:** `OpeningInsightFinding.entry_full_hash:str` and `resulting_full_hash:str`. Operate as `int` in Python/SQL; stringify on the way out only.

### Display-name "vs. " prefix
**Source:** `app/repositories/stats_repository.py:250-260`.
**Apply to:** the service's attribution step — when `(opening.ply_count % 2 == 1) != (finding.color == "white")`.

### Module-level constants block
**Source:** Frontend `arrowColor.ts:17-19` + backend `insights_service.py:84-114`.
**Apply to:** top of `opening_insights_service.py` — D-28 mandates the seven-constant block.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/services/test_opening_insights_arrow_consistency.py` | test | regex / static | Phase 63's `test_endgame_zones_consistency.py` referenced in CONTEXT.md no longer exists in the tree (only `__pycache__` trace). Build from RESEARCH.md spec — pattern shown above. |
| Alembic CONCURRENTLY DDL | migration | DDL | First-of-its-kind in this project: no prior migration uses `postgresql_concurrently=True` or `autocommit_block()`. Cited from Alembic cookbook in RESEARCH.md. |
| `LAG()` window function in SQL | repository | aggregate | No existing repo function uses `func.lag().over(partition_by=...)`. The transition CTE is the genuinely new SQL pattern. RESEARCH.md Pattern 2 has the SQLAlchemy 2.x recipe. |

---

## Metadata

**Analog search scope:**
- `app/schemas/` (openings.py, stats.py, insights.py, endgames.py)
- `app/services/` (insights_service.py, openings_service.py)
- `app/repositories/` (openings_repository.py, stats_repository.py, query_utils.py)
- `app/routers/insights.py`
- `app/models/` (game_position.py, opening.py)
- `alembic/versions/` (latest 11 migrations + befacc0fce23 index analog)
- `tests/` (test_openings_repository.py, services/test_insights_service.py, test_insights_router.py)
- `frontend/src/lib/arrowColor.ts`

**Files scanned:** 17

**Pattern extraction date:** 2026-04-26
