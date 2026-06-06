# Phase 108: Flaws Subtab — Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 18 new/modified files
**Analogs found:** 17 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/models/game_flaw.py` | model | CRUD | `app/models/game_position.py` | exact |
| `alembic/versions/…_add_game_flaws_table.py` | migration | batch | `alembic/versions/20260603_153628_f4d88c3659c6_gp_natural_composite_pk_seed_035.py` | exact |
| `app/repositories/game_flaws_repository.py` | repository | CRUD | `app/repositories/game_repository.py` (bulk_insert_games) | exact |
| `app/repositories/library_repository.py` (modified) | repository | request-response | `app/repositories/library_repository.py` (flaw_exists_subquery) | self |
| `app/repositories/query_utils.py` (modified) | utility | request-response | `app/repositories/query_utils.py` (apply_game_filters) | self |
| `app/services/eval_drain.py` (modified) | service | event-driven | `app/services/eval_drain.py` lines 543-551 | self |
| `app/services/library_service.py` (modified) | service | CRUD | `app/services/library_service.py` existing | self |
| `app/schemas/library.py` (modified) | schema | request-response | `app/schemas/library.py` (GameFlawCard/LibraryGamesResponse) | exact |
| `app/routers/library.py` (modified) | router | request-response | `app/routers/library.py` (get_library_games) | exact |
| `scripts/backfill_flaws.py` | utility | batch | `scripts/backfill_eval.py` | exact |
| `frontend/src/hooks/useFlawFilterStore.ts` | hook | event-driven | `frontend/src/hooks/useFilterStore.ts` | exact |
| `frontend/src/hooks/useLibrary.ts` (modified) | hook | request-response | `frontend/src/hooks/useLibrary.ts` existing | self |
| `frontend/src/api/client.ts` (modified) | utility | request-response | `frontend/src/api/client.ts` (libraryApi.getGames) | role-match |
| `frontend/src/types/library.ts` (modified) | type | — | `frontend/src/types/library.ts` existing | self |
| `frontend/src/components/filters/FlawFilterControl.tsx` | component | event-driven | `frontend/src/components/library/TagChip.tsx` (family colors/icons pattern) | role-match |
| `frontend/src/components/filters/LibraryFilterPanel.tsx` (modified) | component | event-driven | `frontend/src/components/filters/LibraryFilterPanel.tsx` existing | self |
| `frontend/src/components/results/LibraryGameCard.tsx` (modified) | component | request-response | `frontend/src/components/library/TagChip.tsx` | role-match |
| `frontend/src/pages/library/FlawsTab.tsx` | component | request-response | `frontend/src/pages/library/GamesTab.tsx` | exact |
| `frontend/src/pages/library/LibraryPage.tsx` (modified) | component | request-response | `frontend/src/pages/library/LibraryPage.tsx` existing | self |

---

## Pattern Assignments

### `app/models/game_flaw.py` (model, CRUD)

**Analog:** `app/models/game_position.py`

**Imports pattern** (lines 1-7):
```python
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
```

**Core model pattern** (lines 25-134 of analog — composite PK with FKs + ondelete CASCADE):
```python
class GameFlaw(Base):
    __tablename__ = "game_flaws"
    __table_args__ = (
        Index("ix_game_flaws_user_severity", "user_id", "severity"),
    )

    # Natural composite PK: (user_id, game_id, ply) — mirrors game_positions PK (SEED-035)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True, index=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)

    # Severity: 1=mistake, 2=blunder (SmallInteger, ordered — see _SEVERITY_INT in flaws_service)
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Tempo family: 0=low-clock, 1=impatient, 2=considered; NULL when no clock data
    tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    # Phase family: 0=opening, 1=middlegame, 2=endgame (denormalized from game_positions.phase)
    phase: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Opportunity family (boolean typed columns)
    is_miss: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_lucky_escape: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Impact family
    is_while_ahead: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_result_changing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Display payload (SEED-038: stored at classify time to avoid PGN replay per request)
    es_before: Mapped[float] = mapped_column(Float, nullable=False)
    es_after: Mapped[float] = mapped_column(Float, nullable=False)
    move_san: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fen: Mapped[str] = mapped_column(String, nullable=False)  # board_fen() at this ply
```

**Rule:** Every FK uses explicit `ondelete="CASCADE"` (CLAUDE.md DB design rule). Use `SmallInteger` not `Integer` for ordered enumerations (severity, tempo, phase). Store `fen` as a column — RESEARCH §4/Pitfall 4 confirms this avoids per-request PGN replay.

---

### `alembic/versions/…_add_game_flaws_table.py` (migration, batch)

**Analog:** `alembic/versions/20260603_153628_f4d88c3659c6_gp_natural_composite_pk_seed_035.py`

**Header pattern** (lines 68-76 of analog):
```python
import sqlalchemy as sa
from alembic import op

revision: str = "<hash>"
down_revision: str | None = "<prev_hash>"
branch_labels: str | None = None
depends_on: str | None = None
```

**Core migration pattern** (`op.create_table` + CONCURRENTLY index via autocommit_block):
```python
def upgrade() -> None:
    op.create_table(
        "game_flaws",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("ply", sa.SmallInteger(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("tempo", sa.SmallInteger(), nullable=True),
        sa.Column("phase", sa.SmallInteger(), nullable=False),
        sa.Column("is_miss", sa.Boolean(), nullable=False),
        sa.Column("is_lucky_escape", sa.Boolean(), nullable=False),
        sa.Column("is_while_ahead", sa.Boolean(), nullable=False),
        sa.Column("is_result_changing", sa.Boolean(), nullable=False),
        sa.Column("es_before", sa.Float(), nullable=False),
        sa.Column("es_after", sa.Float(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=True),
        sa.Column("fen", sa.String(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "game_id", "ply"),
    )
    # CONCURRENTLY cannot run inside a transaction — use autocommit_block
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_game_flaws_user_severity",
            "game_flaws",
            ["user_id", "severity"],
            postgresql_concurrently=True,
        )

def downgrade() -> None:
    op.drop_table("game_flaws")
```

**Rules from analog:** Never import live app constants in migrations (version-pinned snapshots). All column sizes and types are literal values. `CONCURRENTLY` requires `autocommit_block()`. Always provide `downgrade()`.

---

### `app/repositories/game_flaws_repository.py` (repository, CRUD)

**Analog:** `app/repositories/game_repository.py` lines 48-72 (`bulk_insert_games`)

**Imports pattern** (lines 1-10 of analog):
```python
from collections.abc import Sequence
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.game_flaw import GameFlaw
```

**Bulk insert with ON CONFLICT DO NOTHING** (analog lines 48-72):
```python
async def bulk_insert_game_flaws(
    session: AsyncSession,
    rows: list[dict],
) -> None:
    """Insert game_flaws rows, skipping conflicts (idempotent for import hook).

    Uses ON CONFLICT DO NOTHING on the PK (user_id, game_id, ply).
    Per RESEARCH §11: small per-game row count (~1-5), pg_insert is appropriate.
    """
    if not rows:
        return
    stmt = pg_insert(GameFlaw).values(rows).on_conflict_do_nothing()
    await session.execute(stmt)

async def delete_flaws_for_game(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> None:
    """Delete all game_flaws rows for one game (used by backfill recompute)."""
    await session.execute(
        delete(GameFlaw).where(
            GameFlaw.game_id == game_id,
            GameFlaw.user_id == user_id,
        )
    )
```

---

### `app/repositories/library_repository.py` (modified — add `build_flaw_filter_clauses` + `flaw_exists_from_table`)

**Analog:** self — existing `flaw_exists_subquery` (lines 164-193)

**Pattern to copy for the new predicate builder** (replaces the window-scan EXISTS):
```python
# Existing flaw_exists_subquery structure (lines 179-193) — copy this shape:
def flaw_exists_subquery(user_id: int, severities: Sequence[FlawSeverity]) -> ColumnElement[bool]:
    if not severities:
        return false()
    threshold = min(_drop_threshold(s) for s in severities)
    inner = _per_ply_drop_subquery(user_id)
    return exists(
        select(inner.c.ply).where(
            inner.c.game_id == Game.id,
            _drop_filter(inner),
            _user_ply_filter(inner),
            inner.c.drop >= threshold,
        )
    )
```

**New functions to add** (RESEARCH §5-6, share one predicate builder):
```python
# Severity int encoding — mirrors flaws_service._SEVERITY_INT
_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}
_TEMPO_INT: dict[str, int] = {"low-clock": 0, "impatient": 1, "considered": 2}

def build_flaw_filter_clauses(
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> list[ColumnElement[bool]]:
    """Return WHERE clauses for game_flaws rows. OR within family, AND across (SEED-038)."""
    clauses: list[ColumnElement[bool]] = []
    if severity:
        threshold = min(_SEVERITY_INT[s] for s in severity)
        clauses.append(GameFlaw.severity >= threshold)
    # Tempo family
    tempo_tags = [t for t in tags if t in {"low-clock", "impatient", "considered"}]
    if tempo_tags:
        clauses.append(GameFlaw.tempo.in_([_TEMPO_INT[t] for t in tempo_tags]))
    # Opportunity family
    opp_tags = [t for t in tags if t in {"miss", "lucky-escape"}]
    if opp_tags:
        opp_clauses = []
        if "miss" in opp_tags: opp_clauses.append(GameFlaw.is_miss == True)  # noqa: E712
        if "lucky-escape" in opp_tags: opp_clauses.append(GameFlaw.is_lucky_escape == True)  # noqa: E712
        clauses.append(or_(*opp_clauses))
    # Impact family
    imp_tags = [t for t in tags if t in {"while-ahead", "result-changing"}]
    if imp_tags:
        imp_clauses = []
        if "while-ahead" in imp_tags: imp_clauses.append(GameFlaw.is_while_ahead == True)  # noqa: E712
        if "result-changing" in imp_tags: imp_clauses.append(GameFlaw.is_result_changing == True)  # noqa: E712
        clauses.append(or_(*imp_clauses))
    return clauses  # caller ANDs all clauses

def flaw_exists_from_table(
    user_id: int,
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> ColumnElement[bool]:
    """game_flaws-backed EXISTS (replaces the window-scan after D-02 migration)."""
    clauses = build_flaw_filter_clauses(severity, tags)
    if not clauses:
        return true()
    return exists(
        select(GameFlaw.ply).where(
            GameFlaw.game_id == Game.id,
            GameFlaw.user_id == user_id,
            *clauses,
        )
    )
```

**Note:** Phase tags (`opening`, `middlegame`, `endgame`) are NOT handled in `build_flaw_filter_clauses` — per UI-SPEC §"Tag-family sections" and Pitfall 5 in RESEARCH.

---

### `app/repositories/query_utils.py` (modified — update `flaw_severity` EXISTS path)

**Analog:** self — lines 103-114

**Current pattern to update** (lines 103-114):
```python
if flaw_severity:
    if user_id is None:
        raise ValueError("flaw_severity filter requires user_id for EXISTS scoping")
    from app.repositories.library_repository import flaw_exists_subquery  # lazy import
    from app.services.flaws_service import FlawSeverity
    severities = cast(Sequence[FlawSeverity], flaw_severity)
    stmt = stmt.where(flaw_exists_subquery(user_id=user_id, severities=severities))
```

After D-02 migration, replace `flaw_exists_subquery` import+call with the new `flaw_exists_from_table`. Signature for the new parameter (also add `flaw_tags`):
```python
def apply_game_filters(
    stmt: Any,
    ...
    *,
    flaw_severity: Sequence[str] | None = None,
    flaw_tags: Sequence[str] | None = None,   # NEW — FlawTag values
    user_id: int | None = None,
) -> Any:
```

The `Sequence[str]` parameter type convention is already established (`flaw_severity: Sequence[str]`) — use the same for `flaw_tags` (CLAUDE.md: use `Sequence` not `list` for covariance).

---

### `app/services/eval_drain.py` (modified — add import hook)

**Analog:** self — lines 543-551

**Hook insertion pattern** (insert between `_apply_eval_results` and `_mark_evals_completed`):
```python
# Current write session (lines 543-551):
async with async_session_maker() as session:
    if eval_targets:
        await _apply_eval_results(session, eval_targets, list(eval_results))
    # NEW: classify + bulk-insert game_flaws for all just-evaluated games
    await _classify_and_insert_flaws(session, game_ids)
    await _mark_evals_completed(session, game_ids)
    await session.commit()
```

**New helper skeleton** (sequential — CLAUDE.md: never `asyncio.gather` on same AsyncSession):
```python
async def _classify_and_insert_flaws(
    session: AsyncSession,
    game_ids: list[int],
) -> None:
    """Classify game_flaws for a batch of just-evaluated games and bulk-insert.

    Runs sequentially — AsyncSession is not safe for concurrent coroutines (CLAUDE.md).
    Batch size is _DRAIN_BATCH_SIZE (10 games), ~1-5 flaws each = ~50 rows max.
    Skips GameNotAnalyzed silently.
    """
    games = (await session.execute(
        select(Game).where(Game.id.in_(game_ids))
    )).scalars().all()
    for game in games:
        positions = (await session.execute(
            select(GamePosition)
            .where(GamePosition.game_id == game.id, GamePosition.user_id == game.user_id)
            .order_by(GamePosition.ply)
        )).scalars().all()
        result = classify_game_flaws(game, list(positions))
        if isinstance(result, GameNotAnalyzed):
            continue
        rows = [_flaw_record_to_dict(game, flaw) for flaw in result]
        await bulk_insert_game_flaws(session, rows)
```

**Pattern note:** The `_classify_and_insert_flaws` name follows `_apply_eval_results` / `_mark_evals_completed` naming convention (underscore prefix = private module helper).

---

### `app/schemas/library.py` (modified — add `FlawListItem`, `LibraryFlawsResponse`)

**Analog:** `app/schemas/library.py` lines 21-63 (`GameFlawCard`, `LibraryGamesResponse`)

**Imports pattern** (lines 1-18 of file):
```python
import datetime
from typing import Literal
from pydantic import BaseModel
from app.services.flaws_service import FlawSeverity, FlawTag, SeverityCounts, TempoTag
```

**Core schema pattern to copy** (lines 21-63):
```python
class FlawListItem(BaseModel):
    """One row in the Flaws subtab — one flawed position."""
    game_id: int
    ply: int
    fen: str
    move_san: str | None
    severity: FlawSeverity           # "mistake" | "blunder"
    tags: list[FlawTag]              # reconstructed from typed columns
    es_before: float
    es_after: float
    # Game metadata (row header)
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    user_color: str

class LibraryFlawsResponse(BaseModel):
    """Response for GET /api/library/flaws — paginated per-flaw list."""
    flaws: list[FlawListItem]
    matched_count: int
    offset: int
    limit: int
```

**Rule:** Mirror `LibraryGamesResponse` pagination shape (matched_count / offset / limit). Never expose `*_hash` fields (CLAUDE.md V5 rule). Use `Literal["win", "draw", "loss"]` not bare `str` (CLAUDE.md type-safety rule).

---

### `app/routers/library.py` (modified — add `GET /flaws`)

**Analog:** self — lines 31-74 (`get_library_games`)

**New route pattern** (copy the `get_library_games` shape exactly):
```python
@router.get("/flaws", response_model=LibraryFlawsResponse)
async def get_library_flaws(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    tag: list[FlawTagFilter] | None = Query(default=None),   # FlawTagFilter = Literal[...all 7 non-phase tags]
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    color: str | None = Query(default=None),
) -> LibraryFlawsResponse:
    """Return a paginated list of individual flawed positions (GET /library/flaws).

    D-07: ORDER BY g.played_at DESC, f.ply. D-08: page size 20.
    Severity filter is M+B-only (game_flaws stores M+B only, D-03).
    """
    return await library_service.get_library_flaws(
        session,
        user_id=user.id,
        severity=list(severity) if severity else ["mistake", "blunder"],
        tags=list(tag) if tag else [],
        ...
    )
```

**Router convention:** `APIRouter(prefix="/library")` already declared (line 23). Paths are relative (no `/library` prefix in `@router.get("/flaws")`). Thin HTTP layer only — push logic to `library_service`.

---

### `scripts/backfill_flaws.py` (utility, batch)

**Analog:** `scripts/backfill_eval.py` lines 1-116

**Header + CLI pattern** (lines 1-116 of analog):
```python
"""Backfill game_flaws materialization for all users (or --user-id).

Usage:
    uv run python scripts/backfill_flaws.py --db dev --user-id 28 --dry-run
    uv run python scripts/backfill_flaws.py --db dev --user-id 28
    uv run python scripts/backfill_flaws.py --db benchmark
    uv run python scripts/backfill_flaws.py --db prod
"""
from __future__ import annotations
import argparse, asyncio, sys
from pathlib import Path
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target   # noqa: E402
from app.models.game import Game                # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.models.game_flaw import GameFlaw       # noqa: E402
from app.services.flaws_service import classify_game_flaws, GameNotAnalyzed  # noqa: E402
from app.repositories.game_flaws_repository import bulk_insert_game_flaws    # noqa: E402

# No magic numbers (CLAUDE.md rule)
BACKFILL_GAMES_PER_BATCH = 100   # games per commit chunk

def _log(msg: str = "") -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill game_flaws table")
    parser.add_argument("--db", choices=["dev", "benchmark", "prod"], required=True)
    parser.add_argument("--user-id", type=int, default=None, dest="user_id")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()
```

**Session-maker pattern** (analog line 127 `db_url_for_target`, and async_sessionmaker usage):
```python
async def run_backfill(*, db: str, user_id: int | None, dry_run: bool, limit: int | None) -> None:
    url = db_url_for_target(db)
    engine = create_async_engine(url, pool_pre_ping=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    # batch loop: load game_ids → delete existing → reclassify → insert → commit
    ...

if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run_backfill(db=args.db, user_id=args.user_id, dry_run=args.dry_run, limit=args.limit))
```

**Key differences from backfill_eval.py:** No `--workers` arg (classification is pure Python). No EnginePool. Idempotency via DELETE-then-INSERT (full recompute), not ON CONFLICT DO NOTHING. Sentry: call `sentry_sdk.capture_exception()` on errors (CLAUDE.md backend rule).

---

### `frontend/src/hooks/useFlawFilterStore.ts` (hook, event-driven)

**Analog:** `frontend/src/hooks/useFilterStore.ts` — copy exactly (37 lines)

**Full pattern to mirror** (lines 1-37 of analog):
```typescript
import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';

export interface FlawFilterState {
  severity: ('blunder' | 'mistake')[];  // default: both
  tags: FlawTag[];                      // default: []
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: ['blunder', 'mistake'],
  tags: [],
};

// Module-level shared state — survives page navigations within the SPA
let currentFlawFilter: FlawFilterState = { ...DEFAULT_FLAW_FILTER };
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

function getSnapshot(): FlawFilterState {
  return currentFlawFilter;
}

type FlawFilterUpdater = FlawFilterState | ((prev: FlawFilterState) => FlawFilterState);

function setFlawFilter(next: FlawFilterUpdater): void {
  currentFlawFilter = typeof next === 'function' ? next(currentFlawFilter) : next;
  for (const listener of listeners) { listener(); }
}

export function useFlawFilterStore(): readonly [FlawFilterState, (next: FlawFilterUpdater) => void] {
  const state = useSyncExternalStore(subscribe, getSnapshot);
  const update = useCallback((next: FlawFilterUpdater) => setFlawFilter(next), []);
  return [state, update] as const;
}
```

**No Zustand.** No new packages. Zero dependencies beyond `useSyncExternalStore` (already in React 18+).

---

### `frontend/src/hooks/useLibrary.ts` (modified — add `useLibraryFlaws`, extend `buildLibraryParams`)

**Analog:** self — lines 1-75

**Pattern to add** (`useLibraryFlaws` copies `useLibraryGames` shape exactly):
```typescript
// Extend buildLibraryParams to accept flaw filter state
function buildLibraryParams(
  filters: FilterState,
  severity: ('blunder' | 'mistake')[],
  tags: FlawTag[],   // NEW
) {
  const dateParams = dateRangeToWireParams(resolveDateRange(filters));
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    ...dateParams,
    rated: filters.rated,
    opponent_type: filters.opponentType,
    opponent_strength: filters.opponentStrength,
    severity: severity.length > 0 ? severity : undefined,
    tag: tags.length > 0 ? tags : undefined,   // multi-value: tag=low-clock&tag=result-changing
    color: filters.playedAs === 'either' ? undefined : filters.playedAs,
  };
}

export function useLibraryFlaws(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaws', params, offset, limit],
    queryFn: () => libraryApi.getFlaws({ ...params, offset, limit }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

**TanStack Query key convention** (lines 49-54 of analog): include all filter state in the key so any change triggers a refetch.

---

### `frontend/src/components/filters/FlawFilterControl.tsx` (component, event-driven)

**Analog:** `frontend/src/components/library/TagChip.tsx` for family colors/icons; `frontend/src/pages/library/GamesTab.tsx` lines 57-99 for toggle button pattern.

**Family color imports** (TagChip.tsx lines 1-16):
```typescript
import { Clock, Zap, Brain, Target, Clover, TrendingDown, Swords } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  FAM_TEMPO, FAM_TEMPO_BG,
  FAM_OPPORTUNITY, FAM_OPPORTUNITY_BG,
  FAM_IMPACT, FAM_IMPACT_BG,
} from '@/lib/theme';
import type { FlawTag } from '@/types/library';
import { TAG_DEFINITIONS, TAG_LABELS } from '@/lib/tagDefinitions';
```

**Severity toggle button pattern** (UI-SPEC §Severity section):
```tsx
<button
  type="button"
  data-testid="filter-flaw-severity-blunder"
  aria-pressed={severity.includes('blunder')}
  className={cn(
    "h-11 sm:h-7 rounded-md px-3 text-sm font-bold border transition-colors",
    severity.includes('blunder')
      ? "border-toggle-active bg-toggle-active text-toggle-active-foreground"
      : "border-border bg-inactive-bg text-muted-foreground"
  )}
  onClick={() => handleSeverityToggle('blunder')}
>
  Blunders
</button>
```

**Tag family button pattern** (selected = family color, unselected = inactive; mirrors TagChip visual):
```tsx
<button
  type="button"
  data-testid="filter-flaw-tag-low-clock"
  aria-pressed={tags.includes('low-clock')}
  aria-label="Filter flaws by tag: low-clock"
  className={cn(
    "h-11 sm:h-7 rounded-full px-3 py-0.5 text-sm font-bold border transition-colors",
    tags.includes('low-clock')
      ? ""  // inline style for family color (use style prop with FAM_TEMPO/FAM_TEMPO_BG)
      : "border-border bg-inactive-bg text-muted-foreground"
  )}
  style={tags.includes('low-clock') ? {
    color: FAM_TEMPO,
    borderColor: FAM_TEMPO,
    backgroundColor: FAM_TEMPO_BG,
  } : undefined}
  onClick={() => handleTagToggle('low-clock')}
>
  <Clock className="mr-1 h-3 w-3" />
  {TAG_LABELS['low-clock']}
</button>
```

**Family group ARIA pattern** (UI-SPEC §ARIA):
```tsx
<div role="group" aria-label="Timing tag filters" data-testid="filter-flaw-family-tempo">
  {/* tag buttons */}
</div>
```

**Clear affordance pattern** (UI-SPEC §Clear affordance):
```tsx
{isNonDefault && (
  <button
    type="button"
    data-testid="btn-clear-flaw-filter"
    aria-label="Clear all flaw filter selections"
    className="text-sm text-muted-foreground underline cursor-pointer"
    onClick={onClear}
  >
    Clear flaw filter
  </button>
)}
```

**At-least-one-severity guard** (RESEARCH Pitfall 8):
```typescript
function handleSeverityToggle(sev: 'blunder' | 'mistake'): void {
  const next = severity.includes(sev)
    ? severity.filter(s => s !== sev)
    : [...severity, sev];
  if (next.length === 0) return;  // prevent deselecting last active button
  onSeverityChange(next);
}
```

**Props shape:**
```typescript
interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  onSeverityChange: (next: ('blunder' | 'mistake')[]) => void;
  onTagChange: (next: FlawTag[]) => void;
  onClear: () => void;
}
```

---

### `frontend/src/pages/library/FlawsTab.tsx` (component, request-response)

**Analog:** `frontend/src/pages/library/GamesTab.tsx` — copy the full structure

**Imports to adapt** (GamesTab.tsx lines 1-17):
```typescript
import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';   // NEW: URL sync
import { SlidersHorizontal, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { LibraryFilterPanel } from '@/components/filters/LibraryFilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import { useLibraryFlaws } from '@/hooks/useLibrary';
import { Pagination } from '@/components/results/Pagination';
```

**URL sync on mount pattern** (RESEARCH §12 / UI-SPEC §URL sync):
```typescript
const [searchParams, setSearchParams] = useSearchParams();
const [flawFilter, setFlawFilter] = useFlawFilterStore();

// Mount: read URL params → initialize store (only when URL has params, per OQ §3)
useEffect(() => {
  const urlTags = searchParams.getAll('tag') as FlawTag[];
  const urlSeverity = searchParams.getAll('severity') as ('blunder' | 'mistake')[];
  if (urlTags.length > 0 || urlSeverity.length > 0) {
    setFlawFilter({
      tags: urlTags,
      severity: urlSeverity.length > 0 ? urlSeverity : ['blunder', 'mistake'],
    });
  }
}, []); // eslint-disable-line react-hooks/exhaustive-deps — intentional mount-only

// Store change → update URL (replace, not push — avoids polluting history)
useEffect(() => {
  const params = new URLSearchParams();
  flawFilter.tags.forEach(t => params.append('tag', t));
  if (flawFilter.severity.length < 2) {
    flawFilter.severity.forEach(s => params.append('severity', s));
  }
  setSearchParams(params, { replace: true });
}, [flawFilter, setSearchParams]);
```

**isError branch pattern** (CLAUDE.md frontend rule — always handle isError):
```typescript
const { data, isLoading, isError } = useLibraryFlaws(appliedFilters, flawFilter, offset, PAGE_SIZE);

if (isError) {
  return <p>Failed to load flaws. Something went wrong. Please try again in a moment.</p>;
}
```

**Matched count + empty states** (UI-SPEC §Copywriting):
```typescript
// Matched count
<p>{data.matched_count} flaw{data.matched_count === 1 ? '' : 's'} matched</p>

// Empty: no flaws matched filter
<p>No flaws matched</p>
<p>Try adjusting the flaw filter or game filters.</p>

// Empty: no analyzed games
<p>No analyzed games</p>
<p>Only Lichess games with engine analysis have flaws. Import Lichess games to see your flaws.</p>
```

**Pagination wiring** (reuse `Pagination` component from Phase 107):
```typescript
<Pagination
  currentPage={Math.floor(offset / PAGE_SIZE) + 1}
  totalPages={Math.ceil((data?.matched_count ?? 0) / PAGE_SIZE)}
  onPageChange={(page) => {
    setOffset((page - 1) * PAGE_SIZE);
    window.scrollTo({ top: 0 });
  }}
/>
```

---

### `frontend/src/pages/library/LibraryPage.tsx` (modified — add Flaws tab)

**Analog:** self — lines 55-83 (desktop Tabs) and 87-143 (mobile Tabs)

**activeTab detection** (lines 38-42 of analog — add `flaws` branch):
```typescript
const activeTab = location.pathname.includes('/import')
  ? 'import'
  : location.pathname.includes('/games')
    ? 'games'
    : location.pathname.includes('/flaws')   // NEW
      ? 'flaws'
      : 'stats';
```

**New TabsTrigger** (copy the `games` trigger pattern; insert between games and stats):
```tsx
<TabsTrigger value="flaws" data-testid="tab-flaws" className="flex-1">
  <AlertTriangle className="mr-1.5 h-4 w-4" />
  Flaws
</TabsTrigger>
```

**New TabsContent** (insert between games and stats in both desktop and mobile blocks):
```tsx
<TabsContent value="flaws" className="mt-4">
  <FlawsTab />
</TabsContent>
```

**Both desktop and mobile blocks must be updated** (CLAUDE.md: always apply changes to mobile too). Mobile trigger uses `data-testid="tab-flaws-mobile"`.

---

### `frontend/src/components/results/LibraryGameCard.tsx` (modified — chip deep-link)

**Analog:** `frontend/src/components/library/TagChip.tsx` lines 107-144 (current popover trigger)

**Current pattern to REPLACE** (popover trigger — RESEARCH §14):
```tsx
// BEFORE: display-only popover
<PopoverPrimitive.Root>
  <PopoverPrimitive.Trigger asChild>
    <span role="button" aria-label={`Tag: ${tag} — ${TAG_DEFINITIONS[tag]}`}>
```

**New pattern** (navigation button — D-05: `/library/flaws?tag={TAG}`, no `game_id`):
```tsx
// AFTER: navigation trigger
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
// ...
<button
  type="button"
  aria-label={`Filter flaws by tag: ${tag}`}
  data-testid={`chip-${tag}-${gameId}`}   // data-testid unchanged
  className="cursor-pointer ..."
  onClick={() => navigate(`/library/flaws?tag=${tag}`)}
>
```

**Confirmed only consumer:** `LibraryGameCard.tsx` (RESEARCH §14 verified). Safe to change the API.

---

## Shared Patterns

### Authentication (all routes)
**Source:** `app/routers/library.py` lines 32-34
```python
user: Annotated[User, Depends(current_active_user)]
```
Apply to the new `GET /library/flaws` route. No new auth mechanism needed.

### Ownership guard in all `game_flaws` queries
**Source:** `app/repositories/library_repository.py` lines 133, 186
```python
# All queries MUST scope to the authenticated user's data
.where(GameFlaw.user_id == user_id)
```
Apply to `query_flaws`, `flaw_exists_from_table`, and `build_flaw_filter_clauses` callers. Mirrors the `GamePosition.user_id == user_id` guard already established.

### Error handling (backend services)
**Source:** CLAUDE.md backend rules
```python
try:
    ...
except Exception as exc:
    sentry_sdk.set_context("game_flaws", {"game_id": game_id, "user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise  # or continue in backfill loop
```
Apply to `_classify_and_insert_flaws`, `backfill_flaws.py` game-level loops.

### TanStack Query `isError` branch (all frontend queries)
**Source:** CLAUDE.md frontend rules
Every `useQuery` result rendered in a list/loading/data ternary must include an `isError` branch showing "Failed to load [X]. Something went wrong. Please try again in a moment." Apply to `useLibraryFlaws`, `useLibraryGames` (already has it — verify), `useLibraryFlawStats`.

### `data-testid` on all interactive elements
**Source:** CLAUDE.md browser automation rules + UI-SPEC §Browser Automation
All new buttons, inputs, containers must have `data-testid` per the UI-SPEC table. Family groups use `filter-flaw-family-{tempo|opportunity|impact}`. Container uses `data-testid="flaw-list"`.

### `Sequence[str]` for multi-value params (ty compliance)
**Source:** CLAUDE.md ty compliance rule; established in `apply_game_filters` signature
```python
flaw_severity: Sequence[str] | None = None  # list invariance — use Sequence
flaw_tags: Sequence[str] | None = None
```
Apply to any new function accepting a list of `Literal` values.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/components/filters/FlawFilterControl.tsx` (full component) | component | event-driven | No existing multi-family tag toggle filter in codebase; assembled from TagChip colors + GamesTab button patterns |

---

## Metadata

**Analog search scope:** `app/models/`, `app/repositories/`, `app/routers/`, `app/schemas/`, `app/services/eval_drain.py`, `scripts/backfill_eval.py`, `frontend/src/hooks/`, `frontend/src/pages/library/`, `frontend/src/components/`
**Files scanned:** 19 source files read directly
**Pattern extraction date:** 2026-06-06
