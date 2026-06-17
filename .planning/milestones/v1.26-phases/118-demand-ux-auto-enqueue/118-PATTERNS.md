# Phase 118: Demand UX + Auto-Enqueue - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 16 new/modified files
**Analogs found:** 16 / 16

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/eval_queue_service.py` (add `enqueue_tier2_window`) | service | CRUD | same file: `enqueue_tier1_game` (lines 314-359) | exact |
| `app/services/eval_queue_service.py` (modify `_claim_tier3_derived` ORDER BY) | service | CRUD | same file: `_claim_tier3_derived` (lines 196-218) | exact |
| `app/services/import_service.py` (hook `_complete_import_job`) | service | event-driven | same file: `asyncio.create_task(compute_stage_a)` pattern (lines 505-536) | exact |
| `app/middleware/last_activity.py` (hook enqueue) | middleware | request-response | same file: throttled write block (lines 77-92) | exact |
| `app/routers/imports.py` (add `POST /eval/tier1/{game_id}`, `POST /eval/tier2`) | router | request-response | same file: `get_eval_coverage` (lines 260-278); `start_import` (lines 43-80) | exact |
| `app/routers/imports.py` (modify `GET /eval-coverage`) | router | request-response | same file: `get_eval_coverage` (lines 260-278) | exact |
| `app/repositories/game_repository.py` (add `count_is_analyzed_games`, `count_tier2_in_flight`, `count_in_flight_evals`) | repository | CRUD | same file: `count_pending_evals` (lines 85-92), `count_games_for_user` (lines 77-82) | exact |
| `app/schemas/imports.py` (extend `EvalCoverageResponse`) | schema | — | same file: `EvalCoverageResponse` (lines 47-53) | exact |
| `app/schemas/admin.py` → `app/schemas/imports.py` (`EnqueueTier1Response` move) | schema | — | `app/schemas/admin.py` lines 42-50 | exact |
| `alembic/versions/<new>_phase_118_...py` (partial index `ix_eval_jobs_user_active`) | migration | — | `alembic/versions/20260613_120000_phase_117_queue_pv.py` lines 126-138 | exact |
| `frontend/src/hooks/useEvalCoverage.ts` (add `analyzedCount`, `inFlightCount`, update stop condition) | hook | request-response | same file (full file, 53 lines) | exact |
| `frontend/src/hooks/useEnqueueGame.ts` (NEW: `useTier1Enqueue`, `useTier2Enqueue`) | hook | request-response | `frontend/src/hooks/useImport.ts` `useImportTrigger` (lines 24-31) | exact |
| `frontend/src/types/api.ts` (extend `EvalCoverageResponse`) | type | — | same file lines 192-196 | exact |
| `frontend/src/components/library/analysisCoverageCopy.tsx` (replace) | component | — | `frontend/src/pages/Import.tsx` guest-promo copy (lines 292-311) | role-match |
| `frontend/src/components/library/NoAnalysisState.tsx` (add tier-1 button + guest CTA + in-flight) | component | event-driven | same file (37 lines) + `Import.tsx` guest-promo pattern | exact + role-match |
| `frontend/src/components/library/NoEngineAnalysisFlawsState.tsx` (replace body) | component | event-driven | same file (30 lines) + `Import.tsx` guest-promo pattern | exact + role-match |
| `frontend/src/components/library/FlawStatsPanel.tsx` (`FlawDenominatorPill` — add `inFlightCount` + CTA) | component | request-response | same file: `FlawDenominatorPill` (lines 27-44) | exact |

---

## Pattern Assignments

### `enqueue_tier2_window(user_id)` in `app/services/eval_queue_service.py`

**Analog:** `enqueue_tier1_game` — `app/services/eval_queue_service.py` lines 314-359

**Imports pattern** (lines 29-43 — already present in file, no new imports needed):
```python
from app.core.database import async_session_maker
from app.models.eval_jobs import EvalJob, TIER_EXPLICIT, TIER_AUTO_WINDOW, TIER_IDLE_BACKLOG
from app.models.game import Game
from app.models.user import User
from sqlalchemy.dialects.postgresql import insert as pg_insert
import sqlalchemy as sa
from sqlalchemy import select
```

**Core pattern — guest guard + idempotent insert** (lines 314-359):
```python
async def enqueue_tier1_game(game_id: int, user_id: int) -> bool:
    async with async_session_maker() as session:
        # Guest guard (QUEUE-08)
        user_result = await session.execute(select(User.is_guest).where(User.id == user_id))
        is_guest = user_result.scalar_one_or_none()
        if is_guest is None or is_guest:
            return False

        stmt = (
            pg_insert(EvalJob)
            .values(tier=TIER_EXPLICIT, user_id=user_id, game_id=game_id, status="pending")
            .on_conflict_do_nothing(
                index_elements=["game_id"],
                index_where=sa.text("status IN ('pending', 'leased')"),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
    return (result.rowcount or 0) > 0  # ty: ignore[unresolved-attribute]
```

**Key differences for `enqueue_tier2_window`:**
- Return type is `int` (count of rows inserted), not `bool`.
- Add a named constant above the function: `TIER2_WINDOW_SIZE: int = 200`
- Before the bulk insert, run a subquery to select up to `TIER2_WINDOW_SIZE` game IDs matching D-118-03 via the canonical `Game.needs_engine_full_evals` hybrid property (= `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`; do NOT hand-roll the two `is_(None)` clauses), ordered by `Game.played_at.desc().nullslast()`.
- Use `TIER_AUTO_WINDOW` (not `TIER_EXPLICIT`) in the values dict.
- Pass a list of `{"tier": ..., "user_id": ..., "game_id": gid, "status": "pending"}` dicts to `.values(rows)` for bulk insert.
- Return `result.rowcount or 0` as int.

---

### `_claim_tier3_derived` ORDER BY in `app/services/eval_queue_service.py`

**Analog:** current ORDER BY — `app/services/eval_queue_service.py` lines 206-216

**Current ORDER BY to be extended** (lines 206-216):
```python
.order_by(
    sa.case(
        (Game.time_control_bucket == "classical", 0),
        (Game.time_control_bucket == "rapid", 1),
        (Game.time_control_bucket == "blitz", 2),
        (Game.time_control_bucket == "bullet", 3),
        else_=4,
    ).asc(),
    Game.played_at.desc().nullslast(),
)
```

**Key differences for D-118-04:**
- Prepend `User.last_activity.desc().nullslast()` before the `sa.case()` term (active-users-first). The `User` join at line 203 already exists — no new join needed.
- Append `Game.lichess_evals_at.isnot(None).asc()` after `Game.played_at` (needs-eval before PV-backfill-only; `False < True` in ascending order puts needs-eval games first).
- Final ORDER BY: `User.last_activity DESC NULLS LAST`, then TC-weight CASE, then `Game.played_at DESC NULLS LAST`, then `Game.lichess_evals_at IS NOT NULL ASC`.

---

### `_complete_import_job` hook in `app/services/import_service.py`

**Analog:** existing `asyncio.create_task(compute_stage_a(...))` call — `app/services/import_service.py` lines 505-536

**Current tail of `_complete_import_job`** (lines 505-536, condensed):
```python
    asyncio.create_task(compute_stage_a(job.user_id))

    try:
        async with async_session_maker() as read_session:
            zero_pending = await game_repository.users_with_zero_pending(...)
            if zero_pending:
                percentile_compute_registry.mark(job.user_id)
                asyncio.create_task(compute_stage_b(job.user_id))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        sentry_sdk.set_context("percentile_compute", {...})
        sentry_sdk.capture_exception(exc)
```

**Key difference for D-118-01:**
- After the entire `try/except` block (i.e., after Stage B scheduling), add one line:
  ```python
  asyncio.create_task(enqueue_tier2_window(job.user_id))
  ```
- Use a local import inside `_complete_import_job` (or at the top of the file) to avoid circular imports: `from app.services.eval_queue_service import enqueue_tier2_window`.
- No Sentry wrap needed — `enqueue_tier2_window` has no user-visible effect on failure; the tier-3 idle drain is the fallback.

---

### `LastActivityMiddleware` hook in `app/middleware/last_activity.py`

**Analog:** throttled write block — `app/middleware/last_activity.py` lines 77-92

**Current throttled write block** (lines 77-92):
```python
        try:
            now = datetime.now(timezone.utc)
            last = _last_updated.get(user_id)
            if last is not None and (now - last) < _ACTIVITY_THROTTLE:
                return

            async with async_session_maker() as session:
                await session.execute(
                    sa_update(User).where(User.id == user_id).values(last_activity=now)
                )
                await session.commit()
            _last_updated[user_id] = now
        except Exception:
            logger.debug("Failed to update last_activity for user %s", user_id, exc_info=True)
```

**Key differences for D-118-01:**
- After `_last_updated[user_id] = now` (line 89), and still inside the `try` block, add:
  ```python
  import asyncio
  from app.services.eval_queue_service import enqueue_tier2_window
  asyncio.create_task(enqueue_tier2_window(user_id))
  ```
- Use a local import (inside the `try` block) to avoid circular imports — `middleware → service → database` chain. The import is cached after first call; negligible overhead.
- `asyncio.create_task` is safe here because `__call__` is `async` (line 44). The task runs AFTER `self.app()` has returned and the route handler's session has committed, so `users.last_activity` is already written when `enqueue_tier2_window` reads it for D-118-04 ordering.

---

### New `POST /imports/eval/tier1/{game_id}` and `POST /imports/eval/tier2` in `app/routers/imports.py`

**Analog:** `get_eval_coverage` + `start_import` — `app/routers/imports.py` lines 43-80, 260-278

**Auth + session dependency pattern** (lines 260-264):
```python
@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
```

**IDOR guard pattern** — referenced from `app/routers/library.py`; replicate inline:
```python
    game = await session.get(Game, game_id)
    if game is None or game.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")
```

**Fire-and-forget service call pattern** (start_import, lines 61-80):
```python
    user_id = user.id  # Extract before create_task — Depends only works in request scope
    asyncio.create_task(some_service_fn(user_id))
    return SomeResponse(status="enqueued")
```

**Key differences for new tier-1/tier-2 endpoints:**
- Tier-1: `@router.post("/eval/tier1/{game_id}", response_model=EnqueueTier1Response)`. Import `Game` model. After IDOR check, call `await enqueue_tier1_game(game_id=game_id, user_id=user.id)` (already async, no create_task). Return `EnqueueTier1Response` with `status="enqueued"|"already_queued"|"skipped_guest"`.
- Tier-2: `@router.post("/eval/tier2", response_model=EnqueueTier2Response)`. Check `user.is_guest` directly (no IDOR needed — no game_id). Check `count_tier2_in_flight(session, user.id)` → return `status="in_flight"` if > 0. Call `await enqueue_tier2_window(user.id)` → return `status="enqueued"|"nothing_to_enqueue"`. Use HTTP 200 for all statuses (including in_flight) — avoids TanStack `onError` for an expected no-op state.
- Move `EnqueueTier1Response` from `app/schemas/admin.py` to `app/schemas/imports.py`; import from there in both `admin.py` and `imports.py`.
- Add `EnqueueTier2Response` to `app/schemas/imports.py`: `status: Literal["enqueued", "in_flight", "nothing_to_enqueue", "skipped_guest"]`, `enqueued_count: int`.

---

### Extended `GET /imports/eval-coverage` in `app/routers/imports.py`

**Analog:** current handler — `app/routers/imports.py` lines 260-278

**Current handler** (lines 260-278):
```python
@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
    total = await game_repository.count_games_for_user(session, user.id)
    if total == 0:
        return EvalCoverageResponse(pending_count=0, total_count=0, pct_complete=100)
    pending = await game_repository.count_pending_evals(session, user.id)
    pct = round(100 * (total - pending) / total)
    return EvalCoverageResponse(pending_count=pending, total_count=total, pct_complete=pct)
```

**Key differences for D-118-12:**
- Add two sequential `await` calls (never `asyncio.gather` on same session — CLAUDE.md):
  ```python
  analyzed = await game_repository.count_is_analyzed_games(session, user.id)
  in_flight = await game_repository.count_in_flight_evals(session, user.id)
  ```
- Extend `EvalCoverageResponse(...)` with `analyzed_count=analyzed, in_flight_count=in_flight`.
- Early-return for `total == 0` must also include the two new fields (both 0).
- Keep `pending_count` / `pct_complete` semantics unchanged (backward compat with Endgames/Openings/GlobalStats gates).

---

### New `count_is_analyzed_games`, `count_tier2_in_flight`, `count_in_flight_evals` in `app/repositories/game_repository.py`

**Analog:** `count_pending_evals` + `count_games_for_user` — `app/repositories/game_repository.py` lines 77-92

**count_pending_evals pattern** (lines 85-92):
```python
async def count_pending_evals(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.evals_completed_at.is_(None))
    )
    return result.scalar_one()
```

**Key differences per new function:**
- `count_is_analyzed_games`: replace predicate with `Game.is_analyzed` hybrid property expression (verified `app/models/game.py` lines 181-199: `Game.white_blunders.isnot(None)`). This is the D-118-10 correctness fix — do NOT use `evals_completed_at`.
- `count_tier2_in_flight`: selects from `EvalJob` (not `Game`). Predicate: `EvalJob.user_id == user_id, EvalJob.tier == TIER_AUTO_WINDOW, EvalJob.status.in_(["pending", "leased"])`. Import: `from app.models.eval_jobs import EvalJob, TIER_AUTO_WINDOW`.
- `count_in_flight_evals`: selects from `EvalJob`. Predicate: `EvalJob.user_id == user_id, EvalJob.status.in_(["pending", "leased"])`. Counts all tiers (aggregate badge).

---

### Extended `EvalCoverageResponse` in `app/schemas/imports.py`

**Analog:** current class — `app/schemas/imports.py` lines 47-53

**Current class** (lines 47-53):
```python
class EvalCoverageResponse(BaseModel):
    """Response for GET /imports/eval-coverage."""
    pending_count: int
    total_count: int
    pct_complete: int  # 0-100, rounded
```

**Key difference:** Add two fields after `pct_complete`:
```python
    analyzed_count: int   # white_blunders IS NOT NULL (is_analyzed — flaw-surface denominator)
    in_flight_count: int  # eval_jobs pending|leased for this user (D-118-12)
```
Update docstring to note D-118-12 extension. No existing fields change.

---

### `EnqueueTier1Response` move + new `EnqueueTier2Response` in `app/schemas/imports.py`

**Analog:** `EnqueueTier1Response` in `app/schemas/admin.py` lines 42-50

**Current admin schema** (lines 42-50):
```python
class EnqueueTier1Response(BaseModel):
    """Response for POST /admin/eval/enqueue-tier1/{game_id}."""
    status: Literal["enqueued", "skipped_guest", "already_queued"]
    game_id: int
```

**Key differences:**
- Move this class verbatim to `app/schemas/imports.py`. In `app/schemas/admin.py`, replace the class body with `from app.schemas.imports import EnqueueTier1Response  # noqa: F401 — re-export`.
- Add alongside it in `imports.py`:
  ```python
  class EnqueueTier2Response(BaseModel):
      status: Literal["enqueued", "in_flight", "nothing_to_enqueue", "skipped_guest"]
      enqueued_count: int
  ```

---

### New Alembic migration — partial index `ix_eval_jobs_user_active`

**Analog:** partial index creation in `alembic/versions/20260613_120000_phase_117_queue_pv.py` lines 126-138

**Existing partial index pattern** (lines 126-138):
```python
    op.create_index(
        "uq_eval_jobs_game_active",
        "eval_jobs",
        ["game_id"],
        unique=True,
        postgresql_where="status IN ('pending', 'leased')",
    )
    op.create_index(
        "ix_eval_jobs_pick",
        "eval_jobs",
        ["tier", "user_id", "created_at"],
        unique=False,
        postgresql_where="status = 'pending'",
    )
```

**Key difference for new migration:**
```python
    op.create_index(
        "ix_eval_jobs_user_active",
        "eval_jobs",
        ["user_id"],
        unique=False,
        postgresql_where="status IN ('pending', 'leased')",
    )
```
- This index covers both `count_tier2_in_flight` and `count_in_flight_evals` queries (D-118-12, Pitfall 7).
- File naming convention: `YYYYMMDD_HHMMSS_<hash>_phase_118_user_active_index.py`.
- `down_revision` must point to the Phase 117.1 migration (`20260614_120000_...`).
- Downgrade: `op.drop_index("ix_eval_jobs_user_active", table_name="eval_jobs")`.

---

### `useEvalCoverage` extension in `frontend/src/hooks/useEvalCoverage.ts`

**Analog:** current hook (full file, 53 lines):
```typescript
const EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000;
const EVAL_COVERAGE_STALE_TIME_MS = 3_000;

export function useEvalCoverage() {
  const query = useQuery<EvalCoverageResponse>({
    queryKey: ['imports', 'eval-coverage'],
    queryFn: async () => {
      const response = await apiClient.get<EvalCoverageResponse>('/imports/eval-coverage');
      return response.data;
    },
    staleTime: EVAL_COVERAGE_STALE_TIME_MS,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.pct_complete === 100 && data.total_count > 0) return false;
      return EVAL_COVERAGE_POLL_INTERVAL_MS;
    },
  });

  const data = query.data;
  const isPending = (data?.pct_complete ?? 100) < 100;

  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending,
    isLoading: query.isLoading,
  };
}
```

**Key differences:**
- Stop condition: add `&& data.in_flight_count === 0` to the `refetchInterval` guard (keeps polling while analysis is in-flight even when entry-ply evals are 100%).
- Return shape: add `analyzedCount: data?.analyzed_count ?? 0` and `inFlightCount: data?.in_flight_count ?? 0`.
- Existing consumers of `pendingCount`, `totalCount`, `pct`, `isPending` are unaffected.

---

### New `useEnqueueGame.ts` in `frontend/src/hooks/`

**Analog:** `useImportTrigger` in `frontend/src/hooks/useImport.ts` lines 24-31

**Import trigger mutation pattern** (lines 24-31):
```typescript
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export function useImportTrigger() {
  return useMutation<ImportStartedResponse, Error, ImportRequest>({
    mutationFn: async (request: ImportRequest) => {
      const response = await apiClient.post<ImportStartedResponse>('/imports', request);
      return response.data;
    },
  });
}
```

**Key differences for `useTier1Enqueue(gameId)` and `useTier2Enqueue()`:**
- `useTier1Enqueue`: `mutationFn` POSTs to `/imports/eval/tier1/${gameId}`. On `onSuccess`, call `queryClient.invalidateQueries({ queryKey: ['imports', 'eval-coverage'] })` to refresh the badge immediately.
- `useTier2Enqueue`: `mutationFn` POSTs to `/imports/eval/tier2` (no body). Same `onSuccess` invalidation.
- Import `useQueryClient` from `@tanstack/react-query` and call inside `onSuccess` (Pitfall 5 fix — button disables on next render).
- Add response types `EnqueueTier1Response` and `EnqueueTier2Response` to `frontend/src/types/api.ts` matching the backend schemas.

---

### Extended `EvalCoverageResponse` in `frontend/src/types/api.ts`

**Analog:** current interface — `frontend/src/types/api.ts` lines 192-196

**Current interface** (lines 192-196):
```typescript
export interface EvalCoverageResponse {
  pending_count: number;
  total_count: number;
  pct_complete: number;  // 0–100, rounded
}
```

**Key difference:** Add two fields:
```typescript
  analyzed_count: number;   // games where is_analyzed = true (white_blunders IS NOT NULL)
  in_flight_count: number;  // eval_jobs pending|leased for this user
```
Also add:
```typescript
export interface EnqueueTier1Response {
  status: 'enqueued' | 'skipped_guest' | 'already_queued';
  game_id: number;
}
export interface EnqueueTier2Response {
  status: 'enqueued' | 'in_flight' | 'nothing_to_enqueue' | 'skipped_guest';
  enqueued_count: number;
}
```

---

### `analysisCoverageCopy.tsx` replacement

**Analog:** guest-promo copy in `frontend/src/pages/Import.tsx` lines 292-311; and the current "coming soon" copy in `analysisCoverageCopy.tsx` (full file, 23 lines)

**Current file to REPLACE** (full file, 23 lines):
```typescript
export const ANALYSIS_COVERAGE_PARAGRAPHS: readonly string[] = [
  'Flaw analysis requires full Stockfish game analysis. ...',
  'FlawChess currently performs only partial Stockfish analysis ... coming soon.',
];
export const ANALYSIS_COVERAGE_COPY = (
  <div className="space-y-2">
    {ANALYSIS_COVERAGE_PARAGRAPHS.map((para) => (
      <p key={para}>{para}</p>
    ))}
  </div>
);
```

**Key differences:** The stale "coming soon" paragraphs and JSX are replaced. The module is repurposed to export the new named constant `LOW_COVERAGE_THRESHOLD: number = 0.8` and any shared copy strings the components need. The three consumers (`NoAnalysisState`, `NoEngineAnalysisFlawsState`, `FlawDenominatorPill`) no longer import static paragraphs — they receive dynamic counts from `useEvalCoverage` props. The file may become very small or be deleted; all three consumers must be updated to remove the import.

---

### `NoAnalysisState.tsx` extension

**Analog:** current component (37 lines) + `Import.tsx` guest-promo pattern

**Current component** (`NoAnalysisState.tsx` full, 37 lines):
```typescript
import { Cpu } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { ANALYSIS_COVERAGE_COPY } from './analysisCoverageCopy';

interface NoAnalysisStateProps {
  gameId: number;
}

export function NoAnalysisState({ gameId }: NoAnalysisStateProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold text-muted-foreground"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      aria-label="No engine analysis available for this game"
      data-testid={`no-analysis-${gameId}`}
    >
      <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
      No Analysis
      <InfoPopover ...>{ANALYSIS_COVERAGE_COPY}</InfoPopover>
    </span>
  );
}
```

**Key differences for D-118-07/D-118-11/D-118-13:**
- Extend props: add `isGuest: boolean`, `isAnalyzed: boolean`, `isInFlight?: boolean`.
- Branch rendering:
  - `isGuest` → "Sign up to unlock analysis" `<Button variant="brand-outline">` linking to `/login?tab=register`. `data-testid="btn-signup-for-analysis"`, `aria-label="Sign up to unlock game analysis"`.
  - `!isAnalyzed && !isInFlight` → "Analyze this game" `<Button>` calling `useTier1Enqueue(gameId)`. `data-testid={`btn-analyze-game-${gameId}`}`.
  - `!isAnalyzed && isInFlight` → pulsing "Analyzing…" text span (no button).
  - `isAnalyzed` → render nothing (`null`) — caller already excludes lichess-eval games from showing this component (D-118-07).
- Keep the outer `<span>` styling as the pill container for the non-button states.
- Add `data-testid` and `aria-label` to every interactive element (CLAUDE.md).

---

### `NoEngineAnalysisFlawsState.tsx` replacement

**Analog:** current component (30 lines) + `Import.tsx` guest-promo pattern

**Current component** (`NoEngineAnalysisFlawsState.tsx` full, 30 lines):
```typescript
import { Cpu } from 'lucide-react';
import { ANALYSIS_COVERAGE_PARAGRAPHS } from './analysisCoverageCopy';

export function NoEngineAnalysisFlawsState() {
  return (
    <div
      data-testid="flaws-no-engine-analysis"
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 px-4 py-12 text-center"
    >
      <Cpu className="h-8 w-8 text-amber-600" aria-hidden="true" />
      <h2 className="text-xl font-semibold text-foreground">Engine analysis coming soon</h2>
      {ANALYSIS_COVERAGE_PARAGRAPHS.map((para) => (
        <p key={para} className="text-sm text-muted-foreground max-w-sm">{para}</p>
      ))}
    </div>
  );
}
```

**Key differences for D-118-08/D-118-13:**
- Add `isGuest: boolean` and `inFlightCount: number` to props.
- Replace the `<h2>` and paragraph body entirely:
  - `isGuest` → heading "Sign up to unlock full-game analysis" + `<Button variant="brand-outline">` linking to `/login?tab=register`. `data-testid="btn-signup-for-analysis-flaws"`.
  - `!isGuest && inFlightCount > 0` → heading "Analyzing your games…" + `<p>` showing "N of M analyzed". No button (already in-flight).
  - `!isGuest && inFlightCount === 0` → heading "Analyze your games" + `<Button variant="default">` calling `useTier2Enqueue()`. `data-testid="btn-analyze-more"`, `aria-label="Analyze more games"`.
- Keep the outer `<div>` structure, icon, and `data-testid="flaws-no-engine-analysis"` unchanged.

---

### `FlawDenominatorPill` in `frontend/src/components/library/FlawStatsPanel.tsx`

**Analog:** current `FlawDenominatorPill` (lines 14-44 of `FlawStatsPanel.tsx`)

**Current component** (lines 27-44):
```typescript
interface FlawDenominatorPillProps {
  analyzedN: number;
  totalN: number;
}

export function FlawDenominatorPill({ analyzedN, totalN }: FlawDenominatorPillProps) {
  return (
    <div
      className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold shrink-0"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      data-testid="flaw-stats-denominator"
    >
      <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span style={{ color: 'white', fontWeight: 700 }}>{analyzedN}</span>
      <span className="text-muted-foreground">of</span>
      <span style={{ color: 'white', fontWeight: 700 }}>{totalN}</span>
      <span className="text-muted-foreground">Games</span>
      <InfoPopover ariaLabel="About game analysis coverage" testId="flaw-stats-denominator-info">
        {ANALYSIS_COVERAGE_COPY}
      </InfoPopover>
    </div>
  );
}
```

**Key differences for D-118-08/D-118-11:**
- Add `inFlightCount: number` and `isGuest: boolean` to props.
- After the "Games" span, conditionally append `· {inFlightCount} in progress` text when `inFlightCount > 0`. `aria-label` should update accordingly.
- When `analyzedN / totalN < LOW_COVERAGE_THRESHOLD` and `inFlightCount === 0` and `!isGuest`, render a small CTA button "Analyze more" (secondary, `variant="brand-outline"`) after the pill. `data-testid="btn-analyze-more-pill"`. Calls `useTier2Enqueue()` mutation.
- Replace `ANALYSIS_COVERAGE_COPY` in the InfoPopover with updated copy that no longer mentions "coming soon".
- Import `LOW_COVERAGE_THRESHOLD` from a constants file or `analysisCoverageCopy.tsx` (wherever the planner places it).

---

## Shared Patterns

### Auth dependency pattern
**Source:** `app/routers/imports.py` lines 47-48, 262-263
**Apply to:** Both new `POST /imports/eval/tier1/...` and `POST /imports/eval/tier2` endpoints
```python
user: Annotated[User, Depends(current_active_user)],
session: Annotated[AsyncSession, Depends(get_async_session)],
```

### Fire-and-forget `asyncio.create_task`
**Source:** `app/services/import_service.py` lines 508, 527
**Apply to:** `last_activity.py` hook and `_complete_import_job` hook
```python
asyncio.create_task(enqueue_tier2_window(job.user_id))
```
Pattern: always fire AFTER the preceding `async with session` block closes, never inside an open session context.

### `pg_insert + on_conflict_do_nothing` with partial index target
**Source:** `app/services/eval_queue_service.py` lines 337-354
**Apply to:** `enqueue_tier2_window` bulk insert
```python
.on_conflict_do_nothing(
    index_elements=["game_id"],
    index_where=sa.text("status IN ('pending', 'leased')"),
)
```

### `select(func.count()).select_from(Model).where(...)` count query
**Source:** `app/repositories/game_repository.py` lines 77-92
**Apply to:** all three new repository functions
```python
result = await session.execute(
    select(func.count()).select_from(Game).where(Game.user_id == user_id, <predicate>)
)
return result.scalar_one()
```

### TanStack `useMutation` with `onSuccess` cache invalidation
**Source:** `frontend/src/hooks/useImport.ts` lines 24-31 (mutation) + `frontend/src/hooks/usePositionBookmarks.ts` lines 14-22 (with `onSuccess`)
**Apply to:** `useTier1Enqueue`, `useTier2Enqueue` in new `useEnqueueGame.ts`
```typescript
const queryClient = useQueryClient();
return useMutation({
  mutationFn: async () => { ... },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['imports', 'eval-coverage'] });
  },
});
```

### Guest gate via `useUserProfile`
**Source:** `frontend/src/pages/Import.tsx` lines 292-311
**Apply to:** `NoAnalysisState`, `NoEngineAnalysisFlawsState`, `FlawDenominatorPill`
```typescript
const { data: profile } = useUserProfile();
if (profile?.is_guest) {
  // render sign-up CTA with data-testid and aria-label
}
```

### `data-testid` + `aria-label` on every interactive element
**Source:** CLAUDE.md browser-automation rules
**Apply to:** every new button, link, and interactive container
- `data-testid="btn-analyze-game-{gameId}"` for per-game tier-1 button
- `data-testid="btn-analyze-more"` for bulk tier-2 button
- `data-testid="btn-signup-for-analysis"` and `data-testid="btn-signup-for-analysis-flaws"` for guest CTAs
- `aria-label` required on all icon-only or ambiguous-context buttons

---

## No Analog Found

All files have close analogs in the codebase. No greenfield patterns required.

---

## Metadata

**Analog search scope:** `app/services/`, `app/routers/`, `app/repositories/`, `app/schemas/`, `app/middleware/`, `alembic/versions/`, `frontend/src/hooks/`, `frontend/src/types/`, `frontend/src/components/library/`, `frontend/src/pages/`
**Files scanned:** 18 source files read directly; additional grep searches across the repo
**Pattern extraction date:** 2026-06-14
