# Phase 91: Two-lane import — Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 18 new/modified files
**Analogs found:** 18 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/<rev>_add_evals_completed_at.py` | migration | batch | `alembic/versions/20260427_074044_d7f960830d54_expand_ix_gp_user_game_ply_predicate_to_.py` | exact |
| `app/models/game.py` (modify) | model | — | `app/models/game.py` lines 122-126 (`imported_at`) | exact |
| `app/services/eval_drain.py` | service | event-driven, batch | `app/services/import_service.py` (`run_periodic_reaper` + `_board_at_ply` + `_RETRIABLE_DB_OUTAGE_ERRORS`) | exact |
| `app/services/import_service.py` (modify) | service | batch | self — strip stages 3a/4/5-eval, add 5c | exact |
| `app/main.py` (modify) | config | event-driven | `app/main.py` lines 64-81 (existing `reaper_task` wiring) | exact |
| `app/schemas/imports.py` (modify) | model/schema | request-response | `app/schemas/imports.py` (`DeleteGamesResponse`) | exact |
| `app/repositories/game_repository.py` (modify) | repository | CRUD | `app/repositories/game_repository.py` (`count_games_for_user`) | exact |
| `app/routers/imports.py` (modify) | router | request-response | `app/routers/imports.py` (`get_active_imports` endpoint) | exact |
| `frontend/src/types/api.ts` (modify) | types | — | `frontend/src/types/api.ts` lines 162-188 (Imports section) | exact |
| `frontend/src/hooks/useEvalCoverage.ts` | hook | request-response | `frontend/src/hooks/useImport.ts` (`useImportPolling` with `refetchInterval`) | exact |
| `frontend/src/components/EvalCoverageHeader.tsx` | component | request-response | `frontend/src/pages/Import.tsx` (`ImportProgressBar` inline component) | role-match |
| `frontend/src/pages/Endgames.tsx` (modify) | page | — | self — mount `<EvalCoverageHeader />` | exact |
| `frontend/src/pages/openings/StatsTab.tsx` (modify) | page | — | self — mount `<EvalCoverageHeader />` | exact |
| `frontend/src/components/insights/EvalConfidenceTooltip.tsx` (modify) | component | — | self — add `isPending` conditional `<p>` | exact |
| `frontend/src/components/popovers/MetricStatTooltip.tsx` (modify) | component | — | self — add `isPending` conditional `<p>` after methodology footer | exact |
| `frontend/src/components/insights/BulletConfidencePopover.tsx` (modify) | component | — | self — thread `isPending`/`pendingCount` to `EvalConfidenceTooltip` | exact |
| `frontend/src/components/charts/PositionResultsPanel.tsx` (modify) | component | — | self — call `useEvalCoverage()`, pass to `BulletConfidencePopover` | exact |
| `frontend/src/components/charts/EndgameOverallEntryCard.tsx` (and other EndgameXxx/OpeningXxx components — modify) | component | — | `frontend/src/components/charts/EndgameOverallEntryCard.tsx` — existing `MetricStatPopover` callsite pattern | exact |

---

## Pattern Assignments

### `alembic/versions/<rev>_add_evals_completed_at.py` (migration)

**Analog:** `alembic/versions/20260427_074044_d7f960830d54_expand_ix_gp_user_game_ply_predicate_to_.py`

**Module header + revision metadata** (lines 1-24):
```python
"""add evals_completed_at to games

Phase 91: tracks per-game Stockfish eval completion so the cold-drain
coroutine (run_eval_drain) can pick up uncompleted games without
re-evaluating already-processed rows. A partial index on (id) WHERE
evals_completed_at IS NULL enables fast LIFO drain picks and cheap
per-user COUNT queries for GET /imports/eval-coverage.

Revision ID: <hash>
Revises: e925558020b9
Create Date: YYYY-MM-DD HH:MM:SS.000000+00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "<hash>"
down_revision: Union[str, None] = "e925558020b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Upgrade operations** — add column, create partial index, backfill:
```python
def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("evals_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index: drain pick query (ORDER BY id DESC LIMIT 10) and
    # eval-coverage COUNT both predicate on evals_completed_at IS NULL.
    # String form (not sa.text) — matches project convention in 20260427_*.py
    # and 20260504_*.py (most recent partial index migrations).
    op.create_index(
        "ix_games_evals_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where="evals_completed_at IS NULL",
    )
    # Backfill: all pre-Phase-91 games have been through the import-time eval
    # pass. Mark them completed so the cold drain skips them.
    # NOTE: games table has `imported_at`, NOT `updated_at` or `created_at`.
    op.execute(
        "UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW()) "
        "WHERE evals_completed_at IS NULL"
    )

def downgrade() -> None:
    op.drop_index(
        "ix_games_evals_pending",
        table_name="games",
        postgresql_where="evals_completed_at IS NULL",
    )
    op.drop_column("games", "evals_completed_at")
```

---

### `app/models/game.py` — add `evals_completed_at` column (model modification)

**Analog:** `app/models/game.py` lines 122-126 (the existing `imported_at` column — same `DateTime(timezone=True)` + `mapped_column` pattern)

**Existing timestamp pattern to copy** (lines 122-126):
```python
imported_at: Mapped[datetime.datetime] = mapped_column(
    nullable=False,
    server_default=func.now(),
)
```

**New column to add** (after `imported_at`):
```python
evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
```
Note: use `sa.DateTime` (explicit import from `sqlalchemy`) consistent with the Alembic migration. The existing timestamp columns use SQLAlchemy's implicit DateTime via `Mapped[datetime.datetime]`; adding an explicit `DateTime(timezone=True)` ensures timezone-awareness is enforced at the ORM level, matching the TIMESTAMPTZ column added by the migration.

---

### `app/services/eval_drain.py` (new service — cold-lane coroutine)

**Analog:** `app/services/import_service.py` — `run_periodic_reaper` (lines 314-335) + `_RETRIABLE_DB_OUTAGE_ERRORS` (lines 51-62) + `_board_at_ply` (lines 65-85)

**Imports pattern** — copy from `import_service.py` lines 1-41, trimmed to what `eval_drain.py` needs:
```python
import asyncio
import io
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

import chess
import chess.pgn
import sentry_sdk
import asyncpg
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.services import engine as engine_service
```

**`_RETRIABLE_DB_OUTAGE_ERRORS` constant** (copy verbatim from `import_service.py` lines 51-62):
```python
_RETRIABLE_DB_OUTAGE_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    DBAPIError,
    asyncpg.exceptions.CannotConnectNowError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.InterfaceError,
    asyncpg.exceptions.PostgresConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    OSError,
)

_DRAIN_IDLE_SLEEP_SECONDS = 5   # D-13: poll interval when queue empty
_DRAIN_BATCH_SIZE = 10          # D-11: games per drain tick
```

**`run_periodic_reaper` shape** (lines 314-335) — the structural template for `run_eval_drain`:
```python
async def run_periodic_reaper() -> None:
    while True:
        await asyncio.sleep(_REAPER_INTERVAL_SECONDS)
        try:
            await cleanup_orphaned_jobs(...)
        except Exception:
            logger.exception("Periodic orphan-job reaper failed")
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.capture_exception()
```

**`run_eval_drain` must differ from `run_periodic_reaper` in three ways:**
1. Sleep is AFTER processing when the batch is empty (`continue` path), not always-first — LIFO drain should start immediately on startup.
2. Three-tier exception handling: `asyncio.CancelledError` propagates (no except), `_RETRIABLE_DB_OUTAGE_ERRORS` logs + sleeps + continues, `Exception` logs + sleeps + continues.
3. Session discipline: two short read sessions (pick IDs, load PGNs), then `asyncio.gather` with NO open session, then one short write session.

**`_board_at_ply` function** (lines 65-85) — lifted verbatim into `eval_drain.py`:
```python
def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i == target_ply:
            return board
        board.push(node.move)
    return None
```

**`_mark_evals_completed` helper** — uses `Game.__table__` + `bindparam` discipline from `import_service.py` Stage 5 (the existing executemany UPDATE pattern):
```python
async def _mark_evals_completed(session: AsyncSession, game_ids: Sequence[int]) -> None:
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)
        .where(games_table.c.id == bindparam("b_id"))
        .values(evals_completed_at=now_ts)
    )
    await session.execute(stmt, [{"b_id": gid} for gid in game_ids])
```

---

### `app/services/import_service.py` (modification — strip eval stages, add 5c gate)

**Cut-points from RESEARCH.md:** Remove lines 738-765 (Stages 3a + 4 + eval-UPDATE block from `_flush_batch`). Add Stage 5c (covered-game gate) after the existing `fen_params` executemany.

**Stage 5c covered-game gate pattern** — copies the existing Stage 5 `bindparam`/`executemany` discipline already in `_flush_batch` (see `import_service.py` around line 720-737 where `update(games_table).where(...).values(...) + executemany` pattern lives):
```python
# Stage 5c: mark games whose entry plies are already fully covered (D-08 hot-lane gate)
covered_ids = _collect_covered_game_ids(rows_result.game_eval_data)
if covered_ids:
    now_ts = datetime.now(timezone.utc)
    covered_stmt = (
        update(games_table)
        .where(games_table.c.id == bindparam("b_id"))
        .values(evals_completed_at=now_ts)
    )
    await session.execute(covered_stmt, [{"b_id": gid} for gid in covered_ids])
```

`_collect_covered_game_ids` is a pure function (no session, no engine). A game is covered if both `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` return empty for its in-memory `game_eval_data` entry.

---

### `app/main.py` — add `drain_task` (modification)

**Analog:** `app/main.py` lines 64-81 (existing `reaper_task` wiring)

**Existing pattern** (lines 64-81):
```python
reaper_task = asyncio.create_task(run_periodic_reaper(), name="periodic-orphan-reaper")
try:
    yield
finally:
    reaper_task.cancel()
    try:
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass  # expected on shutdown
        except Exception:
            logger.exception("Periodic reaper task raised on shutdown")
    finally:
        await stop_engine()
```

**Modified pattern** — add `drain_task` alongside; both are cancelled+awaited in `finally` before `stop_engine()`:
```python
from app.services.eval_drain import run_eval_drain

# In lifespan, after existing reaper_task line:
drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")
try:
    yield
finally:
    reaper_task.cancel()
    drain_task.cancel()
    try:
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Periodic reaper task raised on shutdown")
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Eval drain task raised on shutdown")
    finally:
        await stop_engine()
```

---

### `app/schemas/imports.py` — add `EvalCoverageResponse` (modification)

**Analog:** `app/schemas/imports.py` lines 41-43 (`DeleteGamesResponse` — simplest schema in the file)

**Existing pattern** (lines 41-43):
```python
class DeleteGamesResponse(BaseModel):
    """Response for DELETE /imports/games."""
    deleted_count: int
```

**New schema to add:**
```python
class EvalCoverageResponse(BaseModel):
    """Response for GET /imports/eval-coverage."""
    pending_count: int
    total_count: int
    pct_complete: int  # 0–100, rounded
```

No additional imports needed — `BaseModel` is already imported at line 5.

---

### `app/repositories/game_repository.py` — add `count_pending_evals` (modification)

**Analog:** `app/repositories/game_repository.py` lines 38-43 (`count_games_for_user`)

**Existing pattern** (lines 38-43):
```python
async def count_games_for_user(session: AsyncSession, user_id: int) -> int:
    """Return total number of games imported by the given user."""
    result = await session.execute(
        select(func.count()).select_from(Game).where(Game.user_id == user_id)
    )
    return result.scalar_one()
```

**New function to add immediately after:**
```python
async def count_pending_evals(session: AsyncSession, user_id: int) -> int:
    """Return count of games not yet Stockfish-evaluated for the given user."""
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.evals_completed_at.is_(None))
    )
    return result.scalar_one()
```

`.is_(None)` (not `== None`) generates `IS NULL` SQL — SQLAlchemy convention enforced by ruff/ty.

---

### `app/routers/imports.py` — add `GET /imports/eval-coverage` (modification)

**Analog:** `app/routers/imports.py` lines 73-123 (`get_active_imports` endpoint — authenticated GET with `session` + `user` deps)

**Existing endpoint signature pattern** (lines 73-78):
```python
@router.get("/active", response_model=list[ImportStatusResponse])
async def get_active_imports(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ImportStatusResponse]:
```

**New endpoint to add** — append after `get_active_imports`, before `get_import_status`:
```python
@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
    """Return Stockfish eval coverage for the authenticated user.

    Returns pending_count, total_count, and pct_complete (0–100).
    Returns pct_complete=100 when the user has no games.
    """
    total = await game_repository.count_games_for_user(session, user.id)
    if total == 0:
        return EvalCoverageResponse(pending_count=0, total_count=0, pct_complete=100)
    pending = await game_repository.count_pending_evals(session, user.id)
    pct = round(100 * (total - pending) / total)
    return EvalCoverageResponse(pending_count=pending, total_count=total, pct_complete=pct)
```

Add `EvalCoverageResponse` to the import from `app.schemas.imports` at line 17-22.

---

### `frontend/src/types/api.ts` — add `EvalCoverageResponse` (modification)

**Analog:** `frontend/src/types/api.ts` lines 162-188 (Imports section — existing interface block)

**Existing section structure** (lines 162-188):
```typescript
// ─── Imports ─────────────────────────────────────────────────────────────────

export type Platform = 'chess.com' | 'lichess';

export interface ImportRequest { ... }
export interface ImportStartedResponse { ... }
export type ImportJobStatus = ...
export interface ImportStatusResponse { ... }
```

**New interface to append at end of Imports section:**
```typescript
export interface EvalCoverageResponse {
  pending_count: number;
  total_count: number;
  pct_complete: number;  // 0–100, rounded
}
```

---

### `frontend/src/hooks/useEvalCoverage.ts` (new hook)

**Analog:** `frontend/src/hooks/useImport.ts` — `useImportPolling` (lines 34-48) — same `refetchInterval` conditional stop pattern

**`useImportPolling` pattern** (lines 34-48):
```typescript
export function useImportPolling(jobId: string | null) {
  return useQuery<ImportStatusResponse, Error>({
    queryKey: ['import', jobId],
    queryFn: async () => {
      const response = await apiClient.get<ImportStatusResponse>(`/imports/${jobId}`);
      return response.data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });
}
```

**`useEvalCoverage` to create** — same refetchInterval-conditional pattern, stops at pct_complete === 100:
```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

const EVAL_COVERAGE_POLL_INTERVAL_MS = 10_000;
const EVAL_COVERAGE_STALE_TIME_MS = 10_000;

export function useEvalCoverage() {
  const query = useQuery<EvalCoverageResponse>({
    queryKey: ['imports', 'eval-coverage'],
    queryFn: async () => {
      const response = await apiClient.get<EvalCoverageResponse>('/imports/eval-coverage');
      return response.data;
    },
    staleTime: EVAL_COVERAGE_STALE_TIME_MS,
    refetchInterval: (query) =>
      query.state.data?.pct_complete === 100 ? false : EVAL_COVERAGE_POLL_INTERVAL_MS,
  });

  const data = query.data;
  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending: (data?.pct_complete ?? 100) < 100,
    isLoading: query.isLoading,
  };
}
```

Key decisions:
- Default `pct: 100` / `isPending: false` while loading — prevents flashing the caveat before first fetch resolves.
- `queryKey: ['imports', 'eval-coverage']` — shares the `imports` namespace with `useActiveJobs` (`['imports', 'active']`) and `useImportPolling` (`['import', jobId]`).
- No `enabled` gate needed: Endgames/Stats pages are behind auth; unauthenticated users are redirected before reaching them.
- No local `Sentry.captureException` — global `QueryCache.onError` in `lib/queryClient.ts` handles it (CLAUDE.md rule).

---

### `frontend/src/components/EvalCoverageHeader.tsx` (new component)

**Analog:** `frontend/src/pages/Import.tsx` — `ImportProgressBar` inline component (lines 54-119) — same status-bar shape (icon + text + conditional render)

**`ImportProgressBar` structural pattern** (lines 83-118):
```typescript
return (
  <div className="space-y-1.5">
    <div className="flex items-center justify-between gap-2">
      <div className={`flex items-center gap-1.5 text-sm ${...}`}>
        <PlatformIcon ... />
        <span>{progressText}</span>
      </div>
      ...
    </div>
    <div className="h-2 w-full ...">...</div>
  </div>
);
```

**`EvalCoverageHeader` to create** — simpler (no progress bar, no dismiss button):
```typescript
import { Cpu } from 'lucide-react';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

export function EvalCoverageHeader() {
  const { pendingCount, pct, isPending } = useEvalCoverage();

  if (!isPending) return null;

  const gamesLabel = pendingCount === 1 ? 'game' : 'games';
  return (
    <div
      role="status"
      data-testid="eval-coverage-header"
      className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3"
    >
      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
      Stockfish analysis: {pct}% complete ({pendingCount.toLocaleString()} {gamesLabel} pending)
    </div>
  );
}
```

Key design points:
- `role="status"` — ARIA live region; screen readers announce % updates.
- `data-testid="eval-coverage-header"` — CLAUDE.md browser automation rule.
- `text-sm` — primary UI copy, CLAUDE.md minimum font-size rule.
- `Cpu className="h-3.5 w-3.5"` — exact sizing from `PositionResultsPanel.tsx:198` + `OpeningFindingCard.tsx:139`.
- `pendingCount.toLocaleString()` — comma-separated thousands (e.g. "1,432").
- Returns `null` when not pending — no layout gap when coverage is complete.

---

### `frontend/src/pages/Endgames.tsx` + `frontend/src/pages/openings/StatsTab.tsx` (modification)

**Mount site pattern** — add `<EvalCoverageHeader />` import and render at top of page return:

```typescript
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';

// In Endgames.tsx: insert after page-level heading area, before <Tabs>
// In StatsTab.tsx: insert at top of StatsTab return, before section headings
<EvalCoverageHeader />
```

No props needed — the component calls `useEvalCoverage()` internally.

---

### `frontend/src/components/insights/EvalConfidenceTooltip.tsx` — add pending caveat (modification)

**Analog:** `EvalConfidenceTooltip.tsx` lines 97-105 — existing `<p className="opacity-70 italic">` footer

**Existing footer pattern** (lines 97-105):
```typescript
<p className="opacity-70 italic">
  {showBaselineTick && (
    <>
      Dashed tick: typical eval for {color} ({fmtSigned(baselinePawns)} pawns).<br />
    </>
  )}
  Test: two-sided Wald z vs 0 pawns.<br />
  Confidence interval: Wald 95% (whiskers).
</p>
```

**Modifications:**
1. Add `isPending?: boolean` and `pendingCount?: number` to `EvalConfidenceTooltipProps` interface (lines 38-54).
2. Add conditional `<p>` as the last element inside `<div className="text-left space-y-1">`, after the existing methodology `<p>`:

```typescript
{isPending === true && (pendingCount ?? 0) > 0 && (
  <p className="opacity-70">
    Based on currently-evaluated games. {(pendingCount ?? 0).toLocaleString()} more being
    analysed — refresh in a few minutes for updated values.
  </p>
)}
```

`text-xs` is acceptable here — CLAUDE.md popover body exception applies.

---

### `frontend/src/components/popovers/MetricStatTooltip.tsx` — add pending caveat (modification)

**Analog:** `MetricStatTooltip.tsx` lines 215-218 — existing `<p className="opacity-70 italic">{methodology}</p>` footer

**Existing footer pattern** (line 218):
```typescript
<p className="opacity-70 italic">{methodology}</p>
```

**Modifications:**
1. Add `isPending?: boolean` and `pendingCount?: number` to `MetricStatTooltipProps` interface (lines 53-92).
2. Add conditional `<p>` after the methodology line (last element in `<div className="text-left space-y-1">`):

```typescript
{isPending === true && (pendingCount ?? 0) > 0 && (
  <p className="opacity-70">
    Based on currently-evaluated games. {(pendingCount ?? 0).toLocaleString()} more being
    analysed — refresh in a few minutes for updated values.
  </p>
)}
```

Also add `isPending` and `pendingCount` to `MetricStatPopoverProps` in `MetricStatPopover.tsx` (line 30-35), forwarding them through `{...tooltipProps}` to `<MetricStatTooltip>` (already handled by spread at line 89).

---

### `frontend/src/components/insights/BulletConfidencePopover.tsx` + other `<Cpu />`-bearing components (modification)

**Analog:** `BulletConfidencePopover.tsx` lines 9-26 (interface + prop forwarding to `EvalConfidenceTooltip`)

**Existing prop-threading pattern** (lines 9-26 + 89-97):
```typescript
interface BulletConfidencePopoverProps {
  // ... existing props ...
  showBaselineTick?: boolean;
  evalContext?: 'opening-end' | 'endgame-entry';
}
// ...
<EvalConfidenceTooltip
  // ... forwarded props ...
  showBaselineTick={showBaselineTick}
  evalContext={evalContext}
/>
```

**Pattern to replicate** — add `isPending` and `pendingCount` to each component's interface, call `useEvalCoverage()` at the component level, thread to the child popover:

```typescript
// In each Cpu-bearing component:
import { useEvalCoverage } from '@/hooks/useEvalCoverage';

// Inside component function:
const { isPending, pendingCount } = useEvalCoverage();

// Pass to popover:
<BulletConfidencePopover
  // ... existing props ...
  isPending={isPending}
  pendingCount={pendingCount}
/>
// or for MetricStatPopover call sites:
<MetricStatPopover
  // ... existing props ...
  isPending={isPending}
  pendingCount={pendingCount}
/>
```

**Touch sites that need this treatment** (from D-07):
- `BulletConfidencePopover.tsx` — thread to `EvalConfidenceTooltip`
- `PositionResultsPanel.tsx` — call `useEvalCoverage()`, pass to `BulletConfidencePopover`
- `OpeningFindingCard.tsx` — call `useEvalCoverage()`, pass to eval metric display
- `EndgameOverallEntryCard.tsx` — call `useEvalCoverage()`, pass to both `MetricStatPopover` instances
- `EndgameOverallPerformanceSection.tsx` — call `useEvalCoverage()`, pass to both `MetricStatPopover` instances
- `EndgameMetricCard.tsx` — call `useEvalCoverage()`, pass to `MetricStatPopover`
- `EndgameTypeCard.tsx` — call `useEvalCoverage()`, pass to `MetricStatPopover`
- `OpeningStatsCard.tsx` — call `useEvalCoverage()`, pass to eval display

**Exclude:** `EndgameTimePressureCard.tsx` — Clock Gap is clock-diff, not Stockfish-dependent (confirmed: imports `Swords`, not `Cpu`; see OQ-1 in RESEARCH.md).

**TanStack Query deduplication:** All these components calling `useEvalCoverage()` with the same `queryKey: ['imports', 'eval-coverage']` share one in-flight request and one cached result. No extra HTTP calls per additional popover on the page.

---

## Shared Patterns

### Lifespan-spawned background coroutine
**Source:** `app/main.py` lines 64-81 + `app/services/import_service.py` lines 314-335
**Apply to:** `app/services/eval_drain.py` (`run_eval_drain`) + `app/main.py` (wiring)

```python
# Shape of a lifespan-managed background coroutine:
async def run_background_task() -> None:
    while True:
        await asyncio.sleep(INTERVAL)  # or after processing when queue empty
        try:
            await do_work()
        except Exception:
            logger.exception("task failed")
            sentry_sdk.set_tag("source", "task_name")
            sentry_sdk.capture_exception()

# In lifespan:
task = asyncio.create_task(run_background_task(), name="task-name")
try:
    yield
finally:
    task.cancel()
    try:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Task raised on shutdown")
    finally:
        await stop_engine()
```

### Authenticated GET endpoint with session
**Source:** `app/routers/imports.py` lines 73-78
**Apply to:** `GET /imports/eval-coverage`

```python
@router.get("/resource", response_model=ResponseSchema)
async def get_resource(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ResponseSchema:
```

### `bindparam` + executemany UPDATE discipline
**Source:** `app/services/import_service.py` Stage 5 UPDATE (around lines 720-740)
**Apply to:** `_mark_evals_completed` in `eval_drain.py` + Stage 5c in `import_service.py`

```python
games_table = Game.__table__
stmt = (
    update(games_table)
    .where(games_table.c.id == bindparam("b_id"))
    .values(column=value)
)
await session.execute(stmt, [{"b_id": gid} for gid in id_list])
```

### `refetchInterval` conditional stop
**Source:** `frontend/src/hooks/useImport.ts` lines 42-46
**Apply to:** `frontend/src/hooks/useEvalCoverage.ts`

```typescript
refetchInterval: (query) => {
  const status = query.state.data?.status;
  if (status === 'completed' || status === 'failed') return false;
  return 2000;
},
```

### Popover body pending caveat `<p>`
**Source:** `frontend/src/components/insights/EvalConfidenceTooltip.tsx` lines 97-105 (footer pattern)
**Apply to:** `EvalConfidenceTooltip`, `MetricStatTooltip` (last `<p>` in body)

```typescript
{isPending === true && (pendingCount ?? 0) > 0 && (
  <p className="opacity-70">
    Based on currently-evaluated games. {(pendingCount ?? 0).toLocaleString()} more being
    analysed — refresh in a few minutes for updated values.
  </p>
)}
```

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `alembic/versions/`, `app/models/`, `app/services/`, `app/repositories/`, `app/routers/`, `app/schemas/`, `frontend/src/hooks/`, `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/types/`
**Files scanned:** ~25 source files read directly; ~15 additional inspected via grep
**Pattern extraction date:** 2026-05-21
