# Phase 167: Backend Store-on-Finish - Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 9 (new/modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/routers/bots.py` (NEW) | router | request-response | `app/routers/feedback.py` | exact |
| `app/services/store_bot_game_service.py` (NEW) | service | CRUD (orchestrator) | `app/services/import_service.py` (`_flush_batch` caller pattern) + `app/routers/feedback.py` (service-call shape) | role-match |
| `app/services/normalization.py` (MODIFY: add `normalize_flawchess_game`) | transform/utility | transform | `normalize_chesscom_game` / `normalize_lichess_game` in same file | exact (structure), partial (data source — PGN-only, no JSON payload) |
| `app/schemas/normalization.py` (MODIFY: `Platform` Literal + new request schema) | schema | request-response | `NormalizedGame` + `Platform` Literal (same file); `app/schemas/feedback.py::FeedbackCreate` for the new request schema shape | exact |
| `app/models/bot_game_settings.py` (NEW) + migration | model / migration | CRUD | `app/models/feedback.py` + `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py` | role-match (FK+CASCADE precedent); CHECK constraint has NO precedent in codebase (see Shared Patterns) |
| `app/repositories/query_utils.py` (MODIFY: `apply_game_filters` platform default-exclude) | utility (shared filter) | CRUD (WHERE-clause builder) | same file, existing `opponent_type`/`platform` branches | exact |
| `app/services/library_service.py` (MODIFY: `get_library_games` opt-in + `_build_card` rating guard) | service | CRUD | same file, existing `get_library_games` / `_build_card` | exact |
| `app/repositories/bot_game_settings_repository.py` (NEW, optional per discretion) | repository | CRUD | `app/repositories/user_rating_anchors_repository.py` (dataclass-return, `user_id`-scoped pattern) | role-match |
| `tests/routers/test_bots.py` / `tests/services/test_store_bot_game_service.py` (NEW) | test | request-response / CRUD | `tests/services/test_import_service.py::TestStage5c...` (proves `_flush_batch` callable with a real `db_session`, no `JobState`) | exact for the `_flush_batch` call shape |

## Pattern Assignments

### `app/routers/bots.py` (router, request-response)

**Analog:** `app/routers/feedback.py` (full file, 43 lines — copy the whole shape)

**Imports pattern:**
```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.bots import StoreBotGameRequest, StoreBotGameResponse
from app.services import store_bot_game_service
from app.users import current_active_user

router = APIRouter(prefix="/bots", tags=["bots"])
```

**Core request-response pattern** (mirrors `feedback.py` lines 23-42):
```python
@router.post("/games", response_model=StoreBotGameResponse, status_code=200)
async def store_game(
    data: StoreBotGameRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> StoreBotGameResponse:
    """Persist a finished bot game as a platform='flawchess' Library game.

    user_id is derived from the authenticated JWT — never from the request
    body (V4). Covers guests too (D-13) — same dependency, no special-casing.
    """
    result = await store_bot_game_service.store_bot_game(session, user.id, data)
    if result is None:
        raise HTTPException(status_code=422, detail="Invalid PGN or missing [%clk] annotations")
    return result
```

**Error handling pattern:** feedback.py raises `HTTPException(429, ...)` inline in the router for a business-rule rejection (rate limit) — same shape applies here for the 422 `[%clk]`/unparseable-PGN gate (D-15): the *service* returns `None`/raises a typed sentinel, the *router* maps it to the HTTP status code. Do not let PGN parse exceptions escape uncaught — `process_game_pgn`/`chess.pgn.read_game` convention (see normalization pattern below) is to catch and return `None`, never raise past the service boundary.

---

### `app/services/store_bot_game_service.py` (service, CRUD orchestrator) — NEW, no direct analog

**Analog (compose from two sources):** `app/services/import_service.py` lines 726-857 (`_flush_batch` call contract) + `app/repositories/user_rating_anchors_repository.py` lines 33-71 (`RatingAnchorRow` + `fetch_anchors_for_user` return shape).

**`_flush_batch` call contract to copy exactly** (`app/services/import_service.py:726-748`):
```python
async def _flush_batch(
    session: Any,
    batch: list[NormalizedGame],
    user_id: int,
) -> int:
    """...
    WR-05: this function does NOT commit. The caller owns the transaction
    boundary ...
    Returns:
        Number of newly inserted games (duplicates excluded).
    """
```
D-10 requires the store service to open/commit its own transaction around this call — mirror `_flush_batch_with_progress`'s commit-after-flush pattern (not copied here since that path also touches `JobState`, which D-10 explicitly excludes).

**Verified test-proof of the direct-call contract** (`tests/services/test_import_service.py:296-381`, read verbatim — copy this call shape into the new service):
```python
await _flush_batch(db_session, cast(list[NormalizedGame], batch), user_id=test_user_id)
await db_session.flush()
# proves: no JobState, no import_job row, no progress counter required
```

**Rating-anchor lookup pattern** (`app/repositories/user_rating_anchors_repository.py:33-71`):
```python
@dataclass(frozen=True)
class RatingAnchorRow:
    anchor_rating: int
    n_chesscom_games: int
    n_lichess_games: int
    chesscom_median_native: int | None
    lichess_median_native: int | None

anchors: dict[TimeControlBucket, RatingAnchorRow] = await fetch_anchors_for_user(session, user_id=user_id)
row = anchors.get(bot_game_tc_bucket)  # None if user has no anchor for this TC (D-06)
```
Derive `rating_source` per D-07 from `row.n_lichess_games`/`row.n_chesscom_games` (both>0 → "blended", lichess-only → "lichess", chesscom-only → "chesscom", `row is None` → `None`).

**Idempotency / missing-id landmine (Pitfall 2, RESEARCH):** `_flush_batch` returns only an `int` count, never a game id, on EITHER the newly-inserted (`1`) or duplicate (`0`) path. No existing `game_repository` helper does "SELECT id WHERE (user_id, platform, platform_game_id)" — add one (small addition, mirror the lightweight `select(Game.id, Game.platform_game_id).where(Game.id.in_(...))` pattern already used inside `_collect_position_rows`, `app/services/import_service.py:934-936`):
```python
result = await session.execute(
    select(Game.id).where(
        Game.user_id == user_id,
        Game.platform == "flawchess",
        Game.platform_game_id == platform_game_id,
    )
)
game_id = result.scalar_one()
```

**Transaction/commit pattern (D-10):**
```python
inserted_count = await _flush_batch(session, [normalized], user_id)
game_id = await <lookup above>
if inserted_count == 1:
    session.add(BotGameSettings(game_id=game_id, nominal_elo=..., play_style_blend=..., tc_preset=..., rating_source=...))
created = inserted_count == 1
await session.commit()  # D-10 — endpoint/service owns the transaction, mirrors feedback_repository.create_feedback + router commit-free pattern (session commit is implicit via get_async_session's context manager in most routers — verify at implementation time which layer calls commit() in this codebase's convention)
```

---

### `app/services/normalization.py` — add `normalize_flawchess_game` (transform, PGN-only)

**Analog:** `normalize_chesscom_game` (lines 221-331) and `normalize_lichess_game` (lines 334-485) in the same file — copy the **function signature + NormalizedGame(...) return shape**, but the body differs structurally (no platform JSON, single PGN parse via `chess.pgn.read_game`, not JSON dict access).

**Signature + imports pattern** (top of file, lines 1-18 — reuse the module's existing imports, add `chess`/`chess.pgn`/`io`):
```python
from app.schemas.normalization import (
    Color,
    GameResult,
    NormalizedGame,
    Termination,
    TimeControlBucket,
)
from app.services.opening_lookup import find_opening
```

**Time-control parsing to reuse verbatim (do not reimplement):**
```python
tc_bucket, tc_seconds = parse_time_control(tc_str)          # lines 55-101
base_time_seconds, increment_seconds = parse_base_and_increment(tc_str)  # lines 104-139
```

**Return-shape pattern** (mirror `normalize_chesscom_game`'s final `return NormalizedGame(...)`, lines 305-331) — set `platform="flawchess"`, `platform_game_id=game_uuid`, `platform_url=None`, `rated=False` (D-04), `is_computer_game=True` (D-04), `white_username`/`black_username` per D-08 (`"FlawChess Bot"` for the bot side), `white_rating`/`black_rating` per D-08 placement (player-color = converted anchor rating, opponent-color = `bot_elo`).

**Skip-game / `None` return convention** (mirrors `_normalize_chesscom_result`'s explicit "return None on unrecognized combination" pattern, lines 189-218 — comment explaining the None-signals-invalid convention): unparseable PGN, no moves, missing `[%clk]` either color, or unrecognized `Result` header → return `None`, no exception, no fabricated draw. The router maps `None` → 422 (mirrors PRUNE-03's "skip the game" convention, not silently defaulting).

**`[%clk]` gate — verified via headless parse this session** (RESEARCH `Code Examples`):
```python
import chess.pgn, io
game = chess.pgn.read_game(io.StringIO(pgn_text))
for node in game.mainline():
    node.clock()  # None when no [%clk] present (verified)
```

---

### `app/schemas/normalization.py` — extend `Platform` Literal (D-17)

**Analog:** same file, line 12.

**Current:**
```python
Platform = Literal["chess.com", "lichess"]
```
**Change to:**
```python
Platform = Literal["chess.com", "lichess", "flawchess"]
```
**Audit both real `cast(Platform, ...)` sites** (per Pitfall 4 — do NOT touch the unrelated inline `Literal["chess.com", "lichess"]` filter types in `insights.py`/`imports.py`/`opening_insights.py`/`openings.py`/`endgames.py`): `app/services/library_service.py:534` and `:544` (both inside `_build_card`, see below).

**New request schema — analog `app/schemas/feedback.py::FeedbackCreate`** (Pydantic v2 boundary model, same file conventions as `NormalizedGame`):
```python
class StoreBotGameRequest(BaseModel):
    game_uuid: str          # client-minted UUIDv4 (D-14) — validate as UUID
    pgn: str                # consider a max_length bound (RESEARCH Security: DoS via oversized PGN)
    user_color: Color       # reuse existing Color Literal ("white"/"black")
    bot_elo: int
    play_style_blend: float # b ∈ [0,1] — Phase 166 D-01 blend, clamp/validate range
    tc_preset: str

class StoreBotGameResponse(BaseModel):
    game_id: int
    created: bool
```

---

### `app/models/bot_game_settings.py` (NEW model) + Alembic migration

**Analog:** `app/models/feedback.py` (FK+CASCADE structure) — but note Pitfall/RESEARCH Pattern 3: **no existing `CheckConstraint` precedent** in `app/models/*.py` (grep returned zero hits). This is genuinely new ground — use SQLAlchemy's `CheckConstraint` directly, not a copy-paste of an existing check.

**Model pattern** (mirrors `Feedback`'s FK+mapped_column style, `app/models/feedback.py:1-25`):
```python
import datetime
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class BotGameSettings(Base):
    __tablename__ = "bot_game_settings"
    __table_args__ = (
        CheckConstraint(
            "rating_source IN ('lichess', 'chesscom', 'blended')",
            name="ck_bot_game_settings_rating_source",
        ),
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    nominal_elo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    play_style_blend: Mapped[float] = mapped_column(REAL, nullable=False)
    tc_preset: Mapped[str] = mapped_column(Text, nullable=False)
    rating_source: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Migration analog** (`alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py`, full file, 53 lines — copy the `op.create_table` + `ForeignKeyConstraint(ondelete="CASCADE")` + `PrimaryKeyConstraint` shape, add a `CheckConstraint`):
```python
def upgrade() -> None:
    op.create_table(
        "bot_game_settings",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("nominal_elo", sa.SmallInteger(), nullable=False),
        sa.Column("play_style_blend", postgresql.REAL(), nullable=False),
        sa.Column("tc_preset", sa.Text(), nullable=False),
        sa.Column("rating_source", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id"),
        sa.CheckConstraint(
            "rating_source IN ('lichess', 'chesscom', 'blended')",
            name="ck_bot_game_settings_rating_source",
        ),
    )

def downgrade() -> None:
    op.drop_table("bot_game_settings")
```
Set `down_revision = "12d3df9c5373"` (verified current alembic head via `uv run alembic heads`; re-verify at plan/implementation time in case another phase lands first).

---

### `app/repositories/query_utils.py` — `apply_game_filters` platform default-exclude (D-02)

**Analog:** same file — the existing `platform`/`opponent_type` branches, `apply_game_filters` lines 180-189.

**Current relevant branch (verbatim, lines 180-189):**
```python
if time_control is not None:
    stmt = stmt.where(Game.time_control_bucket.in_(time_control))
if platform is not None:
    stmt = stmt.where(Game.platform.in_(platform))
if rated is not None:
    stmt = stmt.where(Game.rated == rated)  # noqa: E712
if opponent_type == "human":
    stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
elif opponent_type == "bot":
    stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
```
**D-02 change (module constant + None-case predicate):**
```python
# Module-level constant, near the top of the file (mirrors _PLY_EVEN_MOVER_WHITE's
# "single source" convention at line 20).
DEFAULT_EXCLUDED_PLATFORMS = ("flawchess",)

# ... inside apply_game_filters, replacing the `if platform is not None:` branch:
if platform is not None:
    stmt = stmt.where(Game.platform.in_(platform))
else:
    stmt = stmt.where(Game.platform.notin_(DEFAULT_EXCLUDED_PLATFORMS))
```
No signature change needed — `platform` param stays `Sequence[str] | None`.

---

### `app/services/library_service.py` — two changes (D-03 opt-in + Pitfall 3 rating guard)

**Analog:** same file — `get_library_games` (lines 645-724) and `_build_card` (lines 364-580, specifically 526-550).

**D-03 opt-in at `get_library_games`'s call into `query_filtered_games`** (line ~682): the `platform` param currently flows through unchanged from the router's `platform: list[str] | None` query param. To include flawchess by default on the Library Games tab without changing the router's own default (Pitfall 5 — router's `opponent_type` ALSO defaults to `"human"`, which independently hides bot games; that wiring is explicitly Phase 171's job per D-03/Pitfall 5, not this phase's), the exact minimal seam is: when the caller's `platform` argument is `None`, `get_library_games` should build an explicit list that includes `"flawchess"` alongside the existing platforms before calling `query_filtered_games`/`apply_game_filters` — i.e. `platform=platform if platform is not None else ["chess.com", "lichess", "flawchess"]`. Flag exact call site to the planner for the `query_filtered_games` call at line 678.

**Pitfall 3 rating-conversion guard** (`_build_card`, lines 526-550 — verbatim, both call sites):
```python
white_rating_lichess_blitz = (
    normalize_to_lichess_blitz(
        game.white_rating,
        cast(Platform, game.platform),
        cast(TimeControlBucket, game.time_control_bucket),
        is_correspondence=is_correspondence,
    )
    if game.white_rating is not None and game.time_control_bucket is not None
    else None
)
black_rating_lichess_blitz = (
    normalize_to_lichess_blitz(
        game.black_rating,
        cast(Platform, game.platform),
        cast(TimeControlBucket, game.time_control_bucket),
        is_correspondence=is_correspondence,
    )
    if game.black_rating is not None and game.time_control_bucket is not None
    else None
)
```
`normalize_to_lichess_blitz` (`app/services/chesscom_to_lichess.py:300-420`) has only `if platform == "chess.com": ... else: # lichess` — **no** third branch. Once `Platform` includes `"flawchess"` (D-17), both calls above silently misroute a flawchess game's already-lichess-equivalent rating through the lichess Table-2 inversion for non-blitz buckets. **Fix:** guard both call sites with an explicit `platform == "flawchess"` branch that passes the rating through unchanged (the STORE-03 rating IS already lichess-blitz-equivalent by construction of `anchor_rating`):
```python
white_rating_lichess_blitz = (
    game.white_rating
    if game.platform == "flawchess"
    else (
        normalize_to_lichess_blitz(...)
        if game.white_rating is not None and game.time_control_bucket is not None
        else None
    )
)
# same pattern for black_rating_lichess_blitz
```

---

## Shared Patterns

### Auth (guests included, no special-casing)
**Source:** `app/routers/feedback.py:18,27` — `current_active_user` dependency; `app/services/guest_service.py` (`create_guest_user`) confirms guests are ordinary `User` rows with `is_guest=True`.
**Apply to:** `app/routers/bots.py` — the one new router file.
```python
from app.users import current_active_user
user: Annotated[User, Depends(current_active_user)]
```

### Thin router / service split
**Source:** `app/routers/feedback.py` (whole file) — router validates + calls one service function + shapes response; zero business logic in the router.
**Apply to:** `app/routers/bots.py` → `app/services/store_bot_game_service.py`.

### No-commit contract for reused batch-insert helpers (WR-05)
**Source:** `app/services/import_service.py:737-739,856` (`_flush_batch` docstring + trailing comment) — "this function does NOT commit. The caller owns the transaction boundary."
**Apply to:** `store_bot_game_service.store_bot_game` — must issue its own `session.commit()` after `_flush_batch` + the side-table insert (D-10), since `_flush_batch` never commits.

### Pydantic v2 at the boundary, no client-trusted derived fields
**Source:** `app/schemas/normalization.py` (`NormalizedGame`) + `app/schemas/feedback.py` (`FeedbackCreate`) — both are plain `BaseModel`s with `Literal` types for fixed-value fields, no computed fields trusted from the client.
**Apply to:** `StoreBotGameRequest` (new schema) — the four raw fields only (`game_uuid`, `pgn`, `user_color`, `bot_elo`, `play_style_blend`, `tc_preset`); result/termination/clocks/rating are always server-derived, never accepted as request fields (D-05/D-14, ASVS V4 mitigation already documented in `user_rating_anchors_repository.py`'s own docstring).

### Sentry on non-trivial exceptions, no interpolated variables
**Source:** `app/services/normalization.py:270-274` (`normalize_chesscom_game`'s `sentry_sdk.set_context("chesscom_result", {...}); sentry_sdk.capture_message(...)` — variables via context, not string interpolation) and `app/services/import_service.py:949-951` (`sentry_sdk.set_context("import", {"game_id": game_id}); sentry_sdk.capture_exception()` inside a `try/except Exception` around a PGN parse).
**Apply to:** `normalize_flawchess_game`'s PGN-parse failure path and `store_bot_game_service`'s `_flush_batch`/side-table-insert exception paths — never embed `game_uuid`/`user_id` in the message string, always `set_context`.

## No Analog Found

None — every file in scope has at least a role-match analog in the codebase (see table above). The one genuinely precedent-free element is the `CheckConstraint` on `bot_game_settings.rating_source` (Pitfall/Pattern 3 in RESEARCH.md) — grep confirmed zero existing `CheckConstraint` usages in `app/models/*.py`, so this is the first real application of the CLAUDE.md TEXT+CHECK DB rule; follow the rule directly (SQLAlchemy `CheckConstraint` in `__table_args__` + `sa.CheckConstraint(...)` in the migration's `op.create_table`), not a copy-paste of an existing check.

## Metadata

**Analog search scope:** `app/routers/`, `app/services/`, `app/schemas/`, `app/models/`, `app/repositories/`, `alembic/versions/`, `tests/services/`
**Files scanned:** `app/routers/feedback.py`, `app/routers/library.py`, `app/services/normalization.py`, `app/services/import_service.py`, `app/services/library_service.py`, `app/repositories/query_utils.py`, `app/repositories/user_rating_anchors_repository.py`, `app/repositories/game_repository.py`, `app/models/feedback.py`, `app/schemas/normalization.py`, `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py`, `tests/services/test_import_service.py`
**Pattern extraction date:** 2026-07-11
