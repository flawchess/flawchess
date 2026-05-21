# Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain - Research

**Researched:** 2026-05-20
**Domain:** Python/FastAPI async import pipeline, SQLAlchemy 2.x, Alembic, React/TanStack Query
**Confidence:** HIGH — architecture is fully locked by SEED-023 + CONTEXT.md D-01–D-13; research validates implementation details against live code.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01** — New dedicated endpoint `GET /imports/eval-coverage` returning `{pending_count: int, total_count: int, pct_complete: int}`. NOT extending `GET /imports/active`.

**D-02** — Page-level header bar on **Endgames page** and **Openings → Stats subtab** only. Hidden when `pending_count == 0`. Not in global topbar, not on Import page.

**D-03** — Polling: 10 s `staleTime` + 10 s `refetchInterval` while `pending_count > 0`. `refetchInterval: pct === 100 ? false : 10_000`. Same single TanStack Query key shared by header bar and per-metric hook.

**D-04** — Copy: `<Cpu /> Stockfish analysis: 87% complete (1,432 games pending)`. Plural-aware. `Cpu` icon at `h-3.5 w-3.5` (matches `PositionResultsPanel.tsx:198` and `OpeningFindingCard.tsx:139`).

**D-05** — Centralized hook `useEvalCoverage()` in `frontend/src/hooks/` returning `{pendingCount, totalCount, pct, isPending: pct < 100}`. All Stockfish-dependent components import it. One HTTP call per page.

**D-06** — Per-metric caveat is a one-line addendum in existing popover bodies. When `isPending` is true: `"Based on currently-evaluated games. {pendingCount} more being analysed — refresh in a few minutes for updated values."` When false: omit entirely. NO new popover component family.

**D-07** — Touch sites: `EvalConfidenceTooltip.tsx`, `BulletConfidencePopover.tsx` (opens EvalConfidenceTooltip), `PositionResultsPanel.tsx` (Row 3 Eval block), `OpeningFindingCard.tsx`, `EndgameOverallEntryCard.tsx`, `EndgameTimePressureCard.tsx`, `EndgameOverallPerformanceSection.tsx`, `OpeningStatsCard.tsx`, `EndgameMetricCard.tsx`, `EndgameTypeCard.tsx`. Caveat is per-user, never per-metric.

**D-08** — Migration backfill: `evals_completed_at = COALESCE(updated_at, created_at, NOW())` for all existing rows. Pre-Phase-91 games are fully evaluated.

**D-09** — Retroactive re-eval of historical engine-failure rows: manual via `scripts/backfill_eval.py`. Out of scope.

**D-10** — Backfill runs at deploy time in the Alembic migration. Acceptable at ~150k rows.

**D-11** — LIFO ordering: `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 10`.

**D-12** — No per-user fairness ordering. LIFO on `id` is sufficient at current scale.

**D-13** — Cold-drain idle interval constant: `_DRAIN_IDLE_SLEEP_SECONDS = 5`.

### Claude's Discretion

- Exact filename conventions (`useEvalCoverage.ts` — match project convention of flat file, no index.ts subdir).
- Exact wording of header-bar copy and per-metric caveat (match project voice: no jargon, terse, functional).
- Test structure (unit vs integration mix) — match Phase 90 pattern: real-DB integration for DB-exercising paths, mock-session for service-logic paths.

### Deferred Ideas (OUT OF SCOPE)

- Concurrent-import admission control (SEED-022 option F)
- Scheduled backend restart cadence (SEED-022 option G)
- Idempotent `on_game_fetched` for lichess stream-retry (SEED-022 option A')
- Per-user fairness in cold-lane pick order
- Per-ply (not per-game) eval pending state
- Retroactive re-eval of historical engine-failure rows (automated)
</user_constraints>

---

## Overview

Phase 91 surgically removes the Stockfish evaluation pass from `_flush_batch` in `import_service.py` (currently Stages 3a, 4, and the eval UPDATEs in 5) and moves that work into a new `run_eval_drain()` coroutine that runs continuously in `app/main.py`'s lifespan loop alongside the existing `run_periodic_reaper`. The critical discipline is "gather outside the session": the cold drain picks 10 game IDs in one short transaction, collects eval targets from stored PGNs (no session, CPU only), fans out `asyncio.gather` across the existing module-level `EnginePool`, then opens a fresh session only as a short write window for the combined UPDATEs. Hot-lane transactions shrink from 20-40 seconds per batch to under one second (parse + insert only), eliminating the WAL/page-cache pressure that OOM-killed Postgres during the 2026-05-20 stress test. A new `games.evals_completed_at TIMESTAMPTZ NULL` column with a `WHERE evals_completed_at IS NULL` partial index on `(id)` tracks drain progress. A new `GET /imports/eval-coverage` endpoint exposes pending/total counts, consumed by a `useEvalCoverage()` TanStack Query hook that drives both a page-level header bar (Endgames page + Openings Stats subtab) and per-metric "being analysed" caveats injected into existing popover bodies.

---

## Architecture Summary

See SEED-023 (`seeds/SEED-023-two-lane-import-defer-stockfish.md`) for the canonical locked design. This document does not re-derive it; it validates implementation details.

**Key invariant from SEED-023:** the Stockfish `asyncio.gather` must NEVER run inside an open `AsyncSession` scope (CLAUDE.md hard rule: AsyncSession is not safe for concurrent use, and holding a session open for 20-40 s during multi-position analysis is the structural OOM driver). The session opens only after all `engine.evaluate()` calls complete — a write window of <100 ms.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hot-lane game insert + progress bump | API / Backend (import_service.py) | Database | No change to fetch/insert ownership; eval stage removed |
| Cold-lane Stockfish evaluation | API / Backend (eval_drain.py) | Database | In-process coroutine owns eval gather + UPDATEs |
| `evals_completed_at` tracking | Database | API / Backend | Column + partial index owned by DB; set by drain and conditionally by hot lane |
| `GET /imports/eval-coverage` | API / Backend (routers/imports.py) | Database | New router endpoint; COUNT queries on `games` table |
| Eval coverage header bar | Frontend (new EvalCoverageHeader) | — | Page-level UI; mounts in Endgames.tsx + StatsTab |
| Per-metric caveat | Frontend (existing popover bodies) | — | Conditional `<p>` injected into EvalConfidenceTooltip + MetricStatTooltip bodies |
| `useEvalCoverage()` hook | Frontend (hooks/useEvalCoverage.ts) | — | TanStack Query; single HTTP call per page shared by header + popovers |

---

## File-by-File Change Inventory

### Backend

| File | Current State | Target State |
|------|--------------|-------------|
| `app/services/import_service.py` | `_flush_batch` contains Stages 3a + 4 + eval UPDATEs in `_apply_eval_results`. `_collect_midgame_eval_targets`, `_collect_endgame_span_eval_targets`, `_split_into_contiguous_islands`, `_island_eval_targets`, `_apply_eval_results`, `_board_at_ply`, `_EvalTarget` all defined here. | Remove Stages 3a/4/eval-UPDATE from `_flush_batch`. Add "lichess-already-covered" gate that sets `evals_completed_at` in the Stage 5 bulk UPDATE for qualifying games. Extract all eval helpers to `eval_drain.py`. Add `_DRAIN_IDLE_SLEEP_SECONDS = 5` and `_DRAIN_BATCH_SIZE = 10` constants. |
| `app/services/eval_drain.py` | Does not exist | New module: `_EvalTarget` dataclass, `_board_at_ply`, `_collect_midgame_eval_targets`, `_collect_endgame_span_eval_targets`, `_split_into_contiguous_islands`, `_island_eval_targets`, `_apply_eval_results` (lifted verbatim from import_service.py), `_pick_pending_game_ids()`, `_collect_eval_targets_for_game()`, `run_eval_drain()` coroutine. |
| `app/main.py` | Spawns `reaper_task = asyncio.create_task(run_periodic_reaper(), ...)`. Cancel+await in `finally`. | Add `drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")`. Cancel+await alongside `reaper_task` in `finally`. Import `run_eval_drain` from `app.services.eval_drain`. |
| `app/routers/imports.py` | Has `GET /imports/active`, `GET /imports/{job_id}`, `POST /imports`, `DELETE /imports/games`. | Add `GET /imports/eval-coverage` endpoint. Returns new `EvalCoverageResponse` Pydantic schema. Uses `current_active_user` + `get_async_session`. |
| `app/schemas/imports.py` | `ImportRequest`, `ImportStartedResponse`, `ImportStatusResponse`, `DeleteGamesResponse` | Add `EvalCoverageResponse(pending_count: int, total_count: int, pct_complete: int)` |
| `app/repositories/game_repository.py` | Has `count_games_for_user()` (total count). | Add `count_pending_evals(session, user_id)` — COUNT WHERE `evals_completed_at IS NULL AND user_id = :uid`. |
| `app/models/game.py` | `Game` model has no `evals_completed_at` column. | Add `evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` |
| Alembic migration (new file) | — | New revision: `ADD COLUMN games.evals_completed_at TIMESTAMPTZ NULL` + partial index + backfill UPDATE. |

### Frontend

| File | Current State | Target State |
|------|--------------|-------------|
| `frontend/src/hooks/useEvalCoverage.ts` | Does not exist | New hook. `useQuery` against `GET /api/imports/eval-coverage`. `staleTime: 10_000`, `refetchInterval: (query) => query.state.data?.pct_complete === 100 ? false : 10_000`. Returns `{pendingCount, totalCount, pct, isPending}`. |
| `frontend/src/components/EvalCoverageHeader.tsx` | Does not exist | New component. Renders `<Cpu /> Stockfish analysis: {pct}% complete ({pendingCount} games pending)`. Hidden when `pendingCount === 0`. `data-testid="eval-coverage-header"`, `role="status"`. |
| `frontend/src/pages/Endgames.tsx` | No coverage header. | Mount `<EvalCoverageHeader />` below the page title, above the tab bar. |
| `frontend/src/pages/openings/StatsTab.tsx` | No coverage header. | Mount `<EvalCoverageHeader />` at top of StatsTab render. |
| `frontend/src/components/insights/EvalConfidenceTooltip.tsx` | Body text: value + headline + p-value + methodology footer. | Add `isPending?: boolean` + `pendingCount?: number` props. Append conditional `<p>` when `isPending`. |
| `frontend/src/components/popovers/MetricStatTooltip.tsx` | Body text: name + explanation + value + verdict + methodology. | Add `isPending?: boolean` + `pendingCount?: number` props. Append conditional `<p>`. |
| `frontend/src/components/insights/BulletConfidencePopover.tsx` | Passes props to `EvalConfidenceTooltip`. | Thread `isPending` + `pendingCount` from `useEvalCoverage()` through to `EvalConfidenceTooltip`. |
| `frontend/src/components/charts/PositionResultsPanel.tsx` | BulletConfidencePopover without isPending. | Call `useEvalCoverage()`, pass `isPending` + `pendingCount` to `BulletConfidencePopover`. |
| `frontend/src/components/insights/OpeningFindingCard.tsx` | `<Cpu />` icon row without pending caveat. | Call `useEvalCoverage()`, pass `isPending` + `pendingCount` to eval metric display. |
| `frontend/src/components/charts/EndgameOverallEntryCard.tsx` | Two `MetricStatPopover` instances (Entry Eval, Achievable Score). | Call `useEvalCoverage()`, thread to both `MetricStatPopover`s. |
| `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` | Two `MetricStatPopover` instances (Achievable Score Gap, Endgame Score Gap). | Call `useEvalCoverage()`, thread to both. |
| `frontend/src/components/charts/EndgameMetricCard.tsx` | `MetricStatPopover` for per-bucket Score Gap. | Call `useEvalCoverage()`, thread to `MetricStatPopover`. |
| `frontend/src/components/charts/EndgameTypeCard.tsx` | `MetricStatPopover` for Score Gap, `Cpu` icon. | Call `useEvalCoverage()`, thread to `MetricStatPopover`. |
| `frontend/src/components/charts/EndgameTimePressureCard.tsx` | `MetricStatPopover` for Clock Gap. | Verify whether Clock Gap is eval-dependent; if yes, thread `useEvalCoverage()`. (Clock Gap is clock-diff, not Stockfish-dependent — likely NO caveat needed. See Open Questions.) |
| `frontend/src/components/stats/OpeningStatsCard.tsx` | `<Cpu />` icon + eval bullet. | Call `useEvalCoverage()`, thread to eval display. |
| `frontend/src/types/api.ts` (or new `types/imports.ts`) | No `EvalCoverageResponse` type | Add `EvalCoverageResponse { pending_count: number; total_count: number; pct_complete: number }` |

---

## Hot-Lane Refactor Cut-Points

All changes are within `_flush_batch` in `app/services/import_service.py`.

**Remove entirely (lines 738-765):**

```
lines 738-756: eval_pass_start + eval_targets list + eval_targets.extend(_collect_midgame_eval_targets...) + eval_targets.extend(_collect_endgame_span_eval_targets...)
lines 748-754: if eval_targets: ... asyncio.gather + _apply_eval_results + logging block
lines 756-765: eval_pass_ms + logger.info("import_eval_pass", ...)
```

These are Stage 3a (target collection) and Stage 4 (gather + apply). The `_PositionRowsResult.game_eval_data` field is still populated by `_collect_position_rows` — the cold drain reads PGNs from the DB, not from memory, so `game_eval_data` in `_PositionRowsResult` becomes unnecessary after this phase. However, removing the `game_eval_data` field from the dataclass is a separate cleanup; the planner may choose to leave it as dead code in Phase 91 and remove it in a follow-up, to minimize diff risk.

**Add (in Stage 5, within the `if rows_result.move_counts:` block after the fen_params executemany):**

New logic to set `evals_completed_at` on the batch. For each game in `rows_result.new_game_ids`, check whether it has any entry plies needing Stockfish:
- If `game_eval_data` has no entry plies (phase=1 or endgame spans all have lichess `%eval`), set `evals_completed_at = NOW()` immediately.
- Otherwise leave NULL (cold drain will handle it).

Implementation uses a third executemany group using the same `bindparam`/`Table.__table__` discipline:

```python
# Stage 5c: mark games whose entry plies are already fully covered (D-08 hot-lane gate)
# A game is "covered" if: it has no midgame entries needing eval AND no endgame span
# entries needing eval. Both conditions: entry ply already has lichess %eval, or no
# entry ply exists at all. This is equivalent to checking whether _collect_midgame_eval_targets
# and _collect_endgame_span_eval_targets would return empty for this game.
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

`_collect_covered_game_ids` is a pure function (no session, no engine) that checks the in-memory `game_eval_data` tuples. A game is covered if both `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` return empty for its data.

**Functions to extract to `eval_drain.py` (verbatim lift):**

- `_EvalTarget` dataclass (lines 113-127)
- `_board_at_ply` (lines 65-85)
- `_collect_midgame_eval_targets` (lines 919-950)
- `_collect_endgame_span_eval_targets` (lines 953-977)
- `_split_into_contiguous_islands` (lines 980-997)
- `_island_eval_targets` (lines 1000-1030)
- `_apply_eval_results` (lines 1033-1074)

After extraction, `import_service.py` imports these from `eval_drain` only for `_collect_covered_game_ids`. Once the hot-lane no longer calls them directly, the import can be dropped entirely and `import_service.py` imports only `_collect_covered_game_ids` (or inlines it).

---

## Cold-Lane Drain Coroutine Design

### Constants (in `eval_drain.py`)

```python
_DRAIN_IDLE_SLEEP_SECONDS = 5   # D-13: poll interval when queue empty
_DRAIN_BATCH_SIZE = 10           # D-11: games per drain tick
```

### Pseudocode

```python
async def run_eval_drain() -> None:
    """Continuously evaluate entry plies for games with evals_completed_at IS NULL.

    Picks _DRAIN_BATCH_SIZE game IDs (LIFO by id DESC), loads PGNs from DB,
    derives entry-ply targets, fans out asyncio.gather OUTSIDE any session scope
    (CLAUDE.md: AsyncSession not safe for concurrent use), then opens a short
    write-window session for the combined UPDATEs.

    Crash-safe: if the process dies before commit, all picked games remain
    evals_completed_at IS NULL and are re-picked on the next tick. At most a
    few seconds of eval CPU is repeated (idempotent).

    Wired in app/main.py lifespan alongside run_periodic_reaper.
    """
    while True:
        try:
            # Step 1: pick batch (short read tx, then close session).
            game_ids = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)
            if not game_ids:
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
                continue

            # Step 2: load PGNs + derive targets (no session, CPU only).
            game_pgn_rows = await _load_pgns_for_games(game_ids)
            eval_targets = _collect_eval_targets_for_games(game_pgn_rows)

            # Step 3: fan out engine evaluations (OUTSIDE any session scope).
            if eval_targets:
                eval_results = await asyncio.gather(
                    *(engine_service.evaluate(t.board) for t in eval_targets)
                )
            else:
                eval_results = []

            # Step 4: open session LATE, write all UPDATEs in one short tx.
            async with async_session_maker() as session:
                if eval_targets:
                    await _apply_eval_results(session, eval_targets, eval_results)
                # Mark all 10 games done regardless of eval success/failure.
                # engine.evaluate() returning (None, None) is treated as
                # "evaluated — engine failed for this position, leave row NULL"
                # (same contract as today's import-time pass, D-11).
                await _mark_evals_completed(session, game_ids)
                await session.commit()

        except asyncio.CancelledError:
            # Lifespan shutdown — propagate without retry (cancellation contract
            # mirrors WR-07 in import_service.py: CancelledError is BaseException,
            # neither except clause below catches it).
            raise
        except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
            # Postgres restart mid-tick: log + short sleep, then re-poll.
            # Games remain evals_completed_at IS NULL and will be re-picked.
            logger.warning("eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS)
            sentry_sdk.set_tag("source", "eval_drain")
            sentry_sdk.capture_exception(exc)
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        except Exception:
            logger.exception("eval_drain: unexpected error — continuing")
            sentry_sdk.set_tag("source", "eval_drain")
            sentry_sdk.capture_exception()
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
```

### Session Discipline

- `_pick_pending_game_ids`: opens `async_session_maker()` context, executes `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 10`, extracts scalar list, closes session. Session lifetime: milliseconds.
- `_load_pgns_for_games`: opens separate session, executes `SELECT id, pgn FROM games WHERE id = ANY(:ids)`, extracts list of `(id, pgn)` tuples, closes session.
- `asyncio.gather` for `engine.evaluate` calls: runs with NO open session.
- Write session: opens only after gather completes, holds for the duration of `_apply_eval_results` UPDATEs + `_mark_evals_completed` UPDATE + commit. Expected hold time <100 ms (40 UPDATEs on GamePosition + 10 UPDATE on games).

### `_mark_evals_completed` Helper

```python
async def _mark_evals_completed(session: AsyncSession, game_ids: Sequence[int]) -> None:
    """Mark all picked games as eval-complete in one executemany UPDATE."""
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)
        .where(games_table.c.id == bindparam("b_id"))
        .values(evals_completed_at=now_ts)
    )
    await session.execute(stmt, [{"b_id": gid} for gid in game_ids])
```

Uses the same `Game.__table__` / `bindparam` discipline as Stage 5 in `_flush_batch` to emit invariant SQL (no unique-SQL cache growth).

### Error Handling on (None, None)

When `engine.evaluate()` returns `(None, None)` for a target, `_apply_eval_results` skips the UPDATE for that row and logs to Sentry (same D-11 contract as today). `_mark_evals_completed` then marks the game `evals_completed_at = NOW()` anyway — the entry ply stays NULL permanently, which is the correct behaviour (engine failure at this position; re-running would hit the same failure). This mirrors the existing import-time pass contract.

### `app/main.py` Wiring

```python
# Add alongside existing reaper_task:
from app.services.eval_drain import run_eval_drain

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
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Eval drain task raised on shutdown")
    finally:
        await stop_engine()
```

The `try/except asyncio.CancelledError: pass` pattern is already established for `reaper_task`. The drain task follows the same shape.

---

## Schema Migration Design

### Revision Shape

```
filename: YYYYMMDD_HHMMSS_<hash>_add_evals_completed_at_to_games.py
down_revision: e925558020b9   (current head as of 2026-05-20)
```

### Upgrade Operations

```python
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    # Step 1: add nullable column.
    op.add_column(
        "games",
        sa.Column("evals_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Step 2: partial index — enables instant index scan for drain SELECT
    # and for GET /imports/eval-coverage COUNT query.
    # postgresql_where string form (not sa.text) — consistent with
    # alembic/versions/20260427_074044_d7f960830d54_*.py project convention.
    op.create_index(
        "ix_games_evals_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where="evals_completed_at IS NULL",
    )

    # Step 3: backfill — mark all existing rows as evaluated (D-08).
    # COALESCE(updated_at, created_at, NOW()) is safe: every pre-Phase-91
    # game has been through the import-time eval pass. Any (None, None)
    # result from the engine is already stored as a NULL eval_cp/eval_mate
    # row — the cold drain should NOT re-attempt these rows.
    # Single UPDATE over ~150k rows — runs in seconds on prod (seq scan +
    # heap-only tuple update; no join, no subquery).
    op.execute(
        "UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW()) "
        "WHERE evals_completed_at IS NULL"
    )
    # NOTE: updated_at does not exist on the games table (see game.py model —
    # games has imported_at but no updated_at). Use imported_at as the
    # COALESCE fallback instead. CONTEXT.md D-08 says COALESCE(updated_at,
    # created_at, NOW()) but the actual column is imported_at. Use
    # imported_at (the correct column) here.
```

**Important discrepancy found:** `app/models/game.py` defines `imported_at` (not `updated_at`). The CONTEXT.md D-08 text mentions `COALESCE(updated_at, created_at, NOW())` but neither `updated_at` nor `created_at` exist on the `games` table. The correct backfill expression is `COALESCE(imported_at, NOW())`. The planner must use this corrected expression.

### Downgrade Operations

```python
def downgrade() -> None:
    op.drop_index(
        "ix_games_evals_pending",
        table_name="games",
        postgresql_where="evals_completed_at IS NULL",
    )
    op.drop_column("games", "evals_completed_at")
```

### Partial Index — Why It Works

`WHERE evals_completed_at IS NULL` is a standard PostgreSQL partial index predicate. The drain's pick query `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 10` and the coverage endpoint's `COUNT(*) WHERE user_id = :uid AND evals_completed_at IS NULL` both match the partial index predicate. Once the drain catches up and all rows have `evals_completed_at IS NOT NULL`, the partial index is empty and has zero storage cost.

For a LIFO (DESC) scan, PostgreSQL's B-tree index supports backward scans with no penalty — the same B-tree index supports both `ORDER BY id ASC` and `ORDER BY id DESC`.

### Alembic `postgresql_where` String vs `sa.text()`

Both forms work. The project uses both: `postgresql_where=sa.text('endgame_class IS NOT NULL')` (in 20260326_*.py) and `postgresql_where="phase = 1"` (in 20260504_*.py). Either is acceptable; string form is shorter and used in the most recent partial index migration.

### Backfill Performance at 150k Rows

A single `UPDATE games SET evals_completed_at = ... WHERE evals_completed_at IS NULL` against 150k rows is a sequential scan + write. On the prod server (4 vCPUs, 75 GB NVMe, PostgreSQL 18), this type of full-table UPDATE with a cheap expression completes in under 2 seconds for table sizes in the low hundreds of thousands. The Alembic migration runs in a single transaction during `deploy/entrypoint.sh` before Uvicorn starts accepting requests — no service impact. [ASSUMED: timing estimate based on typical PostgreSQL UPDATE throughput; exact timing depends on I/O load at deploy time.]

---

## `GET /imports/eval-coverage` Endpoint Design

### Route

```python
# In app/routers/imports.py, using existing router = APIRouter(prefix="/imports", tags=["imports"])
@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
    """Return Stockfish eval coverage for the authenticated user.

    Returns pending_count, total_count, and pct_complete (0–100).
    Returns zeros when the user has no games.
    """
    total = await game_repository.count_games_for_user(session, user.id)
    if total == 0:
        return EvalCoverageResponse(pending_count=0, total_count=0, pct_complete=100)
    pending = await game_repository.count_pending_evals(session, user.id)
    pct = round(100 * (total - pending) / total)
    return EvalCoverageResponse(
        pending_count=pending,
        total_count=total,
        pct_complete=pct,
    )
```

### Schema

```python
# In app/schemas/imports.py
class EvalCoverageResponse(BaseModel):
    pending_count: int
    total_count: int
    pct_complete: int  # 0–100, rounded
```

### Repository Query

```python
# In app/repositories/game_repository.py
async def count_pending_evals(session: AsyncSession, user_id: int) -> int:
    """Return count of games not yet Stockfish-evaluated for the given user."""
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.evals_completed_at.is_(None))
    )
    return result.scalar_one()
```

### Query Plan

The `count_pending_evals` query `WHERE user_id = :uid AND evals_completed_at IS NULL`:
- The partial index `ix_games_evals_pending` on `(id) WHERE evals_completed_at IS NULL` does NOT include `user_id`, so a per-user COUNT will not use it for index-only scan.
- PostgreSQL will likely use the existing `ix_games_user_id` index (or similar) to find the user's rows, then filter by `evals_completed_at IS NULL`.
- Alternatively, the planner may bitmap-AND the partial index with the user_id index.
- At current scale (~150k rows total, typically <50k per user), either plan is fast. The existing `count_games_for_user` function already does a similar per-user COUNT with no index concern noted.
- If per-user COUNT proves slow at scale, a composite index `(user_id) WHERE evals_completed_at IS NULL` would solve it. Leave as a follow-up.

---

## Frontend Integration Design

### `useEvalCoverage.ts` Hook

```typescript
// frontend/src/hooks/useEvalCoverage.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/imports';

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

Notes:
- Constants extracted per CLAUDE.md no-magic-numbers rule.
- Default to `pct: 100` / `isPending: false` while loading — prevents "flashing" the caveat on page load before the first fetch resolves.
- `queryKey: ['imports', 'eval-coverage']` matches the existing `imports` namespace used by `useActiveJobs` and `useImportPolling` in `useImport.ts`.
- No `enabled` gate: the endpoint is authenticated; unauthenticated users are redirected before reaching these pages. If a guest scenario arises, add `enabled: !!user` as a follow-up.
- TanStack Query's `QueryCache.onError` in `lib/queryClient.ts` handles Sentry capture (CLAUDE.md rule: do NOT add local capture in hooks backed by `useQuery`).

### `EvalCoverageHeader` Component

```typescript
// frontend/src/components/EvalCoverageHeader.tsx
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

- `role="status"` makes it a live region for screen readers.
- `data-testid="eval-coverage-header"` per CLAUDE.md browser automation rules.
- `text-sm` is the minimum per CLAUDE.md (primary UI copy, not a popover body).
- Uses `pendingCount.toLocaleString()` for comma-separated thousands (e.g. "1,432").
- Returns `null` when not pending — avoids a layout gap when coverage is complete.

### Per-Metric Caveat Pattern

Each Stockfish-dependent popover body gets an optional `<p>` conditional:

```typescript
// Pattern for EvalConfidenceTooltip.tsx and MetricStatTooltip bodies:
{isPending && pendingCount > 0 && (
  <p className="opacity-70">
    Based on currently-evaluated games. {pendingCount.toLocaleString()} more being analysed —
    refresh in a few minutes for updated values.
  </p>
)}
```

- `text-xs` is acceptable here — popover bodies are the CLAUDE.md exception.
- `opacity-70` matches the italic footer styling already used in `EvalConfidenceTooltip.tsx:97`.
- The caveat is the LAST element in the popover body, after the methodology footer.

### Mount Points

**Endgames page (`Endgames.tsx`):** Insert `<EvalCoverageHeader />` inside the `EndgamesPage` return, after the page-level heading area and before the tab bar (`<Tabs ...>`). The component imports `useEvalCoverage` internally, so no props needed at the mount site.

**Openings Stats subtab (`StatsTab.tsx`):** Insert `<EvalCoverageHeader />` at the top of the StatsTab return, before the section headings.

### One HTTP Call Per Page — Verification

TanStack Query deduplicates requests by `queryKey`. Both the header bar (`EvalCoverageHeader` calls `useEvalCoverage()`) and each per-metric popover component that calls `useEvalCoverage()` share `queryKey: ['imports', 'eval-coverage']`. TanStack Query serves all callers from the single in-flight request and cached result — no matter how many `MetricStatPopover` instances appear on a page, exactly one HTTP call fires per polling interval. [VERIFIED: TanStack Query docs — `useQuery` with the same `queryKey` in the same `QueryClient` shares the request.]

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), Vitest 4.x + RTL 16.x (frontend) |
| Config file | `pytest.ini` or `pyproject.toml` (existing), `vite.config.ts` (frontend) |
| Backend quick run | `uv run pytest tests/services/test_eval_drain.py tests/services/test_import_service_hot_lane.py -x` |
| Backend full suite | `uv run pytest` |
| Frontend quick run | `npm test -- --run src/hooks/__tests__/useEvalCoverage.test.tsx src/components/__tests__/EvalCoverageHeader.test.tsx` |
| Frontend full suite | `npm test` |

### Phase Requirements to Test Map

| Claim | Test Type | Automated Command | File Exists? |
|-------|-----------|-------------------|-------------|
| Hot-lane `_flush_batch` no longer calls `engine.evaluate` | unit / mock | `uv run pytest tests/services/test_import_service_hot_lane.py::TestHotLaneNoEvalCalls -x` | Wave 0 |
| Hot-lane correctly marks lichess-covered games `evals_completed_at = NOW()` | unit / mock | `uv run pytest tests/services/test_import_service_hot_lane.py::TestHotLaneCoveredGateRealDb -x` | Wave 0 |
| Cold-drain picks 10 LIFO game IDs and marks them done on success | integration / real DB | `uv run pytest tests/services/test_eval_drain.py::TestDrainBatchPick -x` | Wave 0 |
| Cold-drain idempotency: crash before commit leaves rows `IS NULL` and re-picks next tick | integration / real DB | `uv run pytest tests/services/test_eval_drain.py::TestDrainCrashIdempotency -x` | Wave 0 |
| Cold-drain marks game done even when engine returns `(None, None)` | unit / mock | `uv run pytest tests/services/test_eval_drain.py::TestDrainEngineNoneMarksComplete -x` | Wave 0 |
| Schema migration `upgrade` adds column + partial index | Alembic / `uv run alembic upgrade head` | Manual + CI | N/A |
| Schema migration `downgrade` removes column + index cleanly | Alembic / `uv run alembic downgrade -1` | Manual | N/A |
| `GET /imports/eval-coverage` returns correct pending/total counts | integration / real DB | `uv run pytest tests/routers/test_eval_coverage.py -x` | Wave 0 |
| `useEvalCoverage` polls while `pct < 100`, stops at 100 | unit / Vitest | `npm test -- --run src/hooks/__tests__/useEvalCoverage.test.tsx` | Wave 0 |
| `EvalCoverageHeader` renders with `data-testid` and hides when `isPending=false` | unit / Vitest + RTL | `npm test -- --run src/components/__tests__/EvalCoverageHeader.test.tsx` | Wave 0 |
| Per-metric caveat appears when `isPending=true` and is absent when `isPending=false` | unit / Vitest | `npm test -- --run src/components/insights/__tests__/EvalConfidenceTooltip.test.tsx` (extend existing test file) | ❌ (extend existing) |

### Sampling Rate

- Per task commit: run the task-relevant test file with `-x` (stop on first failure).
- Per wave merge: `uv run pytest` (full backend suite) + `npm test`.
- Phase gate: full suite green before `/gsd:verify-work`.

### Wave 0 Gaps

New test files needed:
- [ ] `tests/services/test_eval_drain.py` — covers cold-drain pick, idempotency, engine-None contract
- [ ] `tests/services/test_import_service_hot_lane.py` — covers stripped eval pass, covered-game gate, real-DB executemany for Stage 5c
- [ ] `tests/routers/test_eval_coverage.py` — covers `GET /imports/eval-coverage` route
- [ ] `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx` — covers polling stop/start logic
- [ ] `frontend/src/components/__tests__/EvalCoverageHeader.test.tsx` — covers render + hide logic

---

## Risk Register

### R-01: Cold drain starves live API users of Stockfish pool

**What could go wrong:** With `STOCKFISH_POOL_SIZE=4` (prod), the cold drain issues 20-40 `engine.evaluate()` calls per tick. If these saturate the pool, live API users calling analysis endpoints wait.

**Mitigation already in place:** `SCHED_IDLE` via `_sched_idle_preexec()` in `engine.py` — Stockfish workers are preempted by any other runnable process. The cold drain's eval calls yield CPU to Uvicorn/Postgres instantly when needed. The pool's `asyncio.Queue` naturally serializes requests so no pool slot is double-used.

**Residual risk:** Pool contention at the asyncio level (not CPU level) — a live API request waiting in the Queue while the drain holds all slots. The existing `_TIMEOUT_S = 2.0` per eval means a single drain batch holds each pool slot for at most 2 s. With pool size 4 and batch of 40 targets, worst-case API wait is ~20 s if drain starts a full batch 1 second before the API request. In practice, depth-15 evals on modern hardware complete in 200-400 ms, so the actual wait is 0.4-1.6 s. Acceptable for non-interactive analysis endpoints.

**If it becomes a problem:** Reduce `_DRAIN_BATCH_SIZE` from 10 to 5, or add a semaphore limiting drain concurrency to `STOCKFISH_POOL_SIZE - 1`. Deferred; not in Phase 91 scope.

### R-02: "Stuck" row at top of LIFO queue

**What could go wrong:** A game with a pathological PGN that makes `_board_at_ply` slow or that causes `engine.evaluate()` to always hit the 2 s timeout loops at the head of the LIFO queue, blocking all other games.

**Mitigation already in place:** `engine.evaluate()` has `_TIMEOUT_S = 2.0` per-eval timeout. A timeout returns `(None, None)` and restarts the worker. The drain then calls `_mark_evals_completed` for all 10 games in the batch, including the problematic one. The "stuck" game is marked done (with NULL eval_cp) and never re-picked. LIFO means the next tick processes the next 10 most-recent games.

**Net effect:** A "stuck" game causes at most 2 s delay per eval target + one drain-tick delay. Not a blocking issue.

### R-03: Backfill UPDATE at deploy time on large table

**What could go wrong:** The `UPDATE games SET evals_completed_at = ... WHERE evals_completed_at IS NULL` runs inside the Alembic transaction during `deploy/entrypoint.sh`. At 150k rows it takes ~2-5 seconds (estimated). During this time, Alembic holds the DDL lock and Uvicorn has not started yet, so no user traffic is affected.

**If prod row count grows to millions (future):** The transaction hold time scales linearly. At 1M rows, estimate ~15-30 s — still acceptable at deploy time. At 10M rows it would warrant a batched backfill instead. Current scale does not require this. [ASSUMED: timing estimates based on typical PostgreSQL UPDATE throughput on NVMe storage.]

### R-04: `games.evals_completed_at` not yet in `Game` SQLAlchemy model

**What could go wrong:** If the Alembic migration runs but the ORM model is not updated, `Game.evals_completed_at` attribute access raises `AttributeError`.

**Mitigation:** The planner must update `app/models/game.py` in the same plan as the Alembic migration. The model update is non-breaking — adding a new nullable column to the ORM model does not affect existing queries.

### R-05: Frontend `useEvalCoverage` called on pages where user has no token

**What could go wrong:** Guest users or unauthenticated states could trigger a 401 from `GET /imports/eval-coverage`, which is an authenticated endpoint.

**Mitigation:** The Endgames page and Openings Stats subtab are already behind authentication gates. `EvalCoverageHeader` should only mount in authenticated contexts. If the app ever adds guest access to these pages, add `enabled: !!isAuthenticated` to the hook. Not an issue for current scope.

### R-06: `_PositionRowsResult.game_eval_data` accumulation

**What could go wrong:** `game_eval_data` in `_PositionRowsResult` stores `list[tuple[int, str, list[PlyData]]]` — the full PGN string per game in-memory for the duration of `_flush_batch`. After the hot-lane refactor, this field is only read by `_collect_covered_game_ids`, which checks whether entry plies are already eval-covered. The data is then discarded at end of `_flush_batch`. Memory footprint: 12 games × ~5 KB PGN = ~60 KB per batch. Negligible.

**If `game_eval_data` is removed from `_PositionRowsResult` in Phase 91:** The `_collect_covered_game_ids` logic must then derive coverage from position rows already inserted into the DB (a SELECT) rather than from in-memory PlyData. This is more complex and not required — leave `game_eval_data` in place for Phase 91.

---

## Open Questions for Planner

**OQ-1: `EndgameTimePressureCard` / Clock Gap — eval-dependent?**

`EndgameTimePressureCard.tsx` has a `MetricStatPopover` with `name="Clock Gap"`. Clock Gap is the average clock time difference at endgame entry. It is based on game clock annotations, NOT Stockfish eval. It should NOT receive the eval-pending caveat. The `Cpu` icon does NOT appear next to Clock Gap in the current source (`EndgameTimePressureCard.tsx` line 17 imports `Swords`, not `Cpu`). Confirmed: Clock Gap is not eval-dependent. The planner should exclude `EndgameTimePressureCard` from the per-metric caveat touch sites.

**OQ-2: `OpeningStatsCard` and `OpeningFindingCard` — eval access pattern**

Both render `<Cpu />` icons and eval metrics but are used in the Openings/Stats and Openings/Insights contexts respectively. `EvalCoverageHeader` mounts on the Openings/Stats subtab (D-02), so users on that page see the header. Whether the per-metric caveat should ALSO appear in `OpeningStatsCard` and `OpeningFindingCard` is consistent with D-07 (which lists them). The planner should include both. The hook call in these components needs no special treatment — same `useEvalCoverage()` pattern.

**OQ-3: `updated_at` / `created_at` column discrepancy in D-08 backfill**

CONTEXT.md D-08 specifies `COALESCE(updated_at, created_at, NOW())` but the `games` table has neither `updated_at` nor `created_at` — only `imported_at`. The correct backfill expression is `COALESCE(imported_at, NOW())`. Confirmed from `app/models/game.py` — no `updated_at` or `created_at` column. The planner should use `COALESCE(imported_at, NOW())`.

---

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json`; treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | `GET /imports/eval-coverage` uses `current_active_user` dependency — same as all other authenticated imports endpoints |
| V3 Session Management | No | No session state involved in new endpoint |
| V4 Access Control | Yes | Endpoint scoped to `user.id` — returns only the authenticated user's data; no cross-user data exposure possible |
| V5 Input Validation | No | No user input; endpoint is GET with no query params |
| V6 Cryptography | No | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthenticated access to coverage endpoint | Spoofing | `current_active_user` dependency raises 401 for unauthenticated requests |
| Cross-user data exposure | Information Disclosure | `WHERE user_id = :uid` scoped to authenticated user in all repository queries |

---

## Sources

### Primary (HIGH confidence)

- Live code: `app/services/import_service.py` — exact line ranges for cut-points
- Live code: `app/services/engine.py` — EnginePool interface + `SCHED_IDLE` preexec confirmation
- Live code: `app/main.py` — exact `run_periodic_reaper` wiring pattern to mirror
- Live code: `app/routers/imports.py` — existing router prefix + dependency injection pattern
- Live code: `app/models/game.py` — confirmed `imported_at` column (not `updated_at`)
- Live code: `alembic/versions/20260504_*.py` — confirmed `postgresql_where` string form for partial indexes
- Live code: `alembic/versions/20260326_*.py` — confirmed `sa.text()` form alternative
- Live code: `frontend/src/hooks/useImport.ts` — `refetchInterval` conditional pattern
- Live code: `frontend/src/hooks/useEndgameInsights.ts` — `staleTime` + `refetchInterval` patterns
- Live code: `frontend/src/components/insights/EvalConfidenceTooltip.tsx` — body structure to amend
- Live code: `frontend/src/components/popovers/MetricStatPopover.tsx` + `MetricStatTooltip.tsx` — body structure
- SEED-023 — locked architecture (no alternatives researched per constraint)
- CONTEXT.md D-01–D-13 — all locked decisions
- `.planning/config.json` — `nyquist_validation: true` confirmed

### Secondary (MEDIUM confidence)

- TanStack Query docs [CITED: tanstack.com/query] — `queryKey` deduplication behaviour confirmed (multiple `useQuery` with same key share one in-flight request).

### Tertiary (LOW confidence — [ASSUMED])

- Backfill timing estimate (150k rows, 2-5 seconds): based on typical PostgreSQL UPDATE throughput on NVMe hardware. Verify at deploy time if concerned.
- Drain batch wall-time estimate (2-4 s per 10-game batch): based on existing comment in SEED-023 and engine.py `_TIMEOUT_S=2.0`. Actual time depends on prod CPU load.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all libraries already in use
- Architecture: HIGH — locked by SEED-023, validated against live code
- Pitfalls / risks: HIGH — grounded in live code reading and Phase 90 UAT history
- Backfill timing: LOW [ASSUMED] — estimate only

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (30 days; stack is stable, no third-party library changes)

---

## RESEARCH COMPLETE
