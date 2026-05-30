# Phase 96: Import Readiness Gate - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 13 (4 new, 9 modified)
**Analogs found:** 13 / 13 (every new/modified file has an in-repo analog)

> RESEARCH.md already pinned exact files and line numbers. This map confirms each
> analog by reading it and extracts the concrete excerpts the planner should copy.
> No project skill is relevant to this UX-gating phase (skills are benchmarks /
> db-report / deploy / parallel-worktree — domain-specific, not applicable).

---

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `app/schemas/imports.py` (add `ReadinessResponse`) | mod | schema | request-response | `EvalCoverageResponse` (same file, lines 47-52) | exact |
| `app/routers/imports.py` (add `GET /readiness`) | mod | router | request-response | `get_eval_coverage` (same file, lines 129-147) | exact |
| `app/repositories/user_benchmark_percentiles_repository.py` (add `has_any_rows`) | mod | repository | CRUD (existence read) | `fetch_for_user` (same file, lines 127-172) | role+flow match |
| `tests/routers/test_imports_readiness.py` | NEW | test | request-response | `tests/routers/test_imports_eval_coverage.py` | exact |
| `frontend/src/types/api.ts` (add `ReadinessResponse`) | mod | type | request-response | `EvalCoverageResponse` (same file, lines 192-196) | exact |
| `frontend/src/hooks/useReadiness.ts` | NEW | hook | polling/request-response | `useEvalCoverage.ts` | exact |
| `frontend/src/hooks/__tests__/useReadiness.test.tsx` | NEW | test | polling | `useEvalCoverage.test.tsx` | exact |
| `frontend/src/hooks/useEvalCoverage.ts` (retire auto-reload) | mod | hook | polling | self (lines 9-11, 45-65 deleted) | n/a (deletion) |
| `frontend/src/components/EndgamesProcessingState.tsx` | NEW | component | event-driven (gate) | `EvalCoverageHeader.tsx` (styling + copy) | role-match |
| `frontend/src/components/stats/EvalCpuPlaceholder.tsx` | NEW | component | event-driven (gate) | `EvalCoverageHeader.tsx` (lines 17-30) | exact (styling) |
| `frontend/src/App.tsx` (gate signal swap + Tier-2 toast) | mod | router/provider | event-driven | `ImportRequiredRoute` (453-471) + `ImportJobWatcher` (46-56) | exact |
| `frontend/src/pages/Endgames.tsx` (in-place Tier-2 gate) | mod | page | event-driven | `ImportRequiredRoute` early-return pattern | role-match |
| `frontend/src/pages/Import.tsx` (state-machine copy) | mod | page | event-driven | `progressText` block (91-95) | exact |
| `frontend/src/components/stats/OpeningStatsCard.tsx` (swap to `tier2`) | mod | component | event-driven | self (lines 9, 60, 218-243) | self-edit |
| `frontend/src/components/insights/EvalConfidenceTooltip.tsx` (remove props) | mod | component | request-response | self (lines 55-59, 114-128) | deletion |
| `frontend/src/components/insights/BulletConfidencePopover.tsx` (remove props) | mod | component | request-response | self (lines 26-30, 47-48, 104-105) | deletion |

---

## Pattern Assignments

### `app/schemas/imports.py` — add `ReadinessResponse` (schema, request-response)

**Analog:** `EvalCoverageResponse` in the same file (lines 47-52). Copy its shape exactly: plain `BaseModel`, docstring naming the endpoint, scalar fields with a trailing comment per derived field.

Existing analog (lines 47-52):
```python
class EvalCoverageResponse(BaseModel):
    """Response for GET /imports/eval-coverage."""

    pending_count: int
    total_count: int
    pct_complete: int  # 0-100, rounded
```

New (per RESEARCH lines 675-687): four bool/int fields, docstring stating the tier semantics. No `Field()` validators needed (read-only, server-derived).

---

### `app/routers/imports.py` — add `GET /readiness` (router, request-response)

**Analog:** `get_eval_coverage` (lines 129-147). This is the canonical thin-router pattern for this exact concern and lives one function above where the new one goes.

**Imports / dependency-injection pattern** (lines 129-133) — copy verbatim, swap the response model:
```python
@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
```
- Auth: `Depends(current_active_user)` — V4 access-control control (user id always from the auth dep, never a query param). The new endpoint MUST use the same dep.
- Relative path in the decorator (`"/readiness"`) — the `prefix="/imports"` is on the router (line 29). Do NOT write `"/imports/readiness"` (CLAUDE.md router convention).

**Core sequential-read pattern** (lines 142-147) — note the early `total == 0` short-circuit and the strictly sequential `await` calls on one session (CLAUDE.md: never `asyncio.gather` on one `AsyncSession`):
```python
total = await game_repository.count_games_for_user(session, user.id)
if total == 0:
    return EvalCoverageResponse(pending_count=0, total_count=0, pct_complete=100)
pending = await game_repository.count_pending_evals(session, user.id)
pct = round(100 * (total - pending) / total)
return EvalCoverageResponse(pending_count=pending, total_count=total, pct_complete=pct)
```
For readiness, sequence (RESEARCH lines 186-199): `import_service.find_active_jobs_for_user(user.id)` → `count_games_for_user` → (skip `count_pending_evals` when `tier1=False`) → `has_any_rows` (skip when `total==0`). Available repo helpers already exist: `game_repository.count_games_for_user` (line 75), `game_repository.count_pending_evals` (line 83).

**Docstring convention** (lines 134-141): docstring records the locked design decisions (D-01/D-04). The readiness docstring should likewise note: dedicated endpoint per project precedent, Tier-1/Tier-2 definitions, and the in-memory-only active-job limitation (RESEARCH A3 / Open Question 1).

**Import-list edit:** add `ReadinessResponse` to the `from app.schemas.imports import (...)` block (lines 19-25).

---

### `app/repositories/user_benchmark_percentiles_repository.py` — add `has_any_rows` (repository, existence read)

**Analog:** `fetch_for_user` (lines 127-172) for the function signature/V4 convention; the body is a simpler `select(func.count(...))` EXISTS-style query (RESEARCH lines 653-668).

**Signature + V4 convention** (lines 127-131) — keyword-only `user_id`, never a query param:
```python
async def fetch_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]:
```
`has_any_rows` follows the same `(session, *, user_id: int) -> bool` shape. The V4 docstring note ("Caller MUST pass the authenticated user's ID … never accept `user_id` as a query parameter", lines 134-137) must be carried over.

**Query primitive** — `select`, `func` already imported (lines 31, 34). Use the bounded-count form (RESEARCH "Don't Hand-Roll", line 473):
```python
result = await session.execute(
    select(func.count(UserBenchmarkPercentile.user_id))
    .where(UserBenchmarkPercentile.user_id == user_id)
    .limit(1)
)
return (result.scalar() or 0) > 0
```
`UserBenchmarkPercentile` is already imported (line 36).

> CORRECTNESS NOTE (RESEARCH Wiring Decision 1): row existence is the Tier-2 signal,
> combined at the endpoint with `pending_count == 0` AND (`total == 0` OR row exists).
> `computed_at` is refreshed on every upsert (line 121, `"computed_at": func.now()`),
> so a row's presence is a post-commit signal with no Stage-B race.

---

### `tests/routers/test_imports_readiness.py` (NEW test, request-response)

**Analog:** `tests/routers/test_imports_eval_coverage.py` — same router, same seeding strategy, same auth helper. Copy its scaffolding wholesale.

**Module docstring + endpoint constant** (lines 1-30): list the covered behaviors (SC-1 truth table), then:
```python
EVAL_COVERAGE_ENDPOINT = "/api/imports/eval-coverage"
```
→ becomes `READINESS_ENDPOINT = "/api/imports/readiness"`.

**Seeding helper** (lines 43-59) — `_make_game(user_id, evals_completed_at=...)` builds a minimal `Game`; `evals_completed_at=None` = pending eval, a timestamp = drained. Reuse verbatim; for Tier-2 tests also insert a `UserBenchmarkPercentile` row to flip `has_any_rows`.

**Auth helper** (lines 65+) — `_register_and_login(email)` returns `(user_id, token)` via real HTTP register. Reuse.

**Seeding caveat** (lines 11-13): seed via committed sessions (`async_sessionmaker`), NOT the rollback-scoped `db_session` fixture, because HTTP requests use an independent session path. This is the single most important thing to copy correctly.

**Required cases** (RESEARCH test map, SC-1):
- `test_tier1_false_when_active_import` (needs an active in-memory job — register the job via `import_service` or assert on the no-job baseline)
- `test_tier2_false_when_evals_done_but_no_percentile_rows` (games with `evals_completed_at` set, zero percentile rows, but `total>0`)
- `test_tier2_true_when_evals_and_percentiles_ready`
- 401 unauthenticated + cross-user scoping (mirror eval-coverage T-91-14 / T-91-15).

---

### `frontend/src/types/api.ts` — add `ReadinessResponse` (type, request-response)

**Analog:** `EvalCoverageResponse` (lines 192-196). Mirror the backend Pydantic field names exactly (snake_case):
```typescript
export interface EvalCoverageResponse {
  pending_count: number;
  total_count: number;
  pct_complete: number;  // 0–100, rounded
}
```
New interface: `tier1: boolean; tier2: boolean; pending_count: number; total_count: number;`

---

### `frontend/src/hooks/useReadiness.ts` (NEW hook, polling)

**Analog:** `useEvalCoverage.ts` (entire file, 74 lines). This is a near-clone minus the auto-reload effect.

**Imports + interval constants** (lines 1-7) — copy, dropping `useEffect`/`useRef` (no reload effect in the new hook):
```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ReadinessResponse } from '@/types/api';

const READINESS_POLL_INTERVAL_MS = 3_000;
const READINESS_STALE_TIME_MS = 3_000;
```

**Query + conditional-stop refetch pattern** (lines 28-40) — this is the seam to copy; swap the stop condition to `data?.tier2`:
```typescript
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
```
New: `queryKey: ['imports', 'readiness']`, path `/imports/readiness`, stop when `data?.tier2`.

**Safe-defaults return shape** (lines 67-73) — copy the `?? fallback` idiom; defaults `tier1=false`, `tier2=false`, counts `0` (prevents unlocked-content flash, RESEARCH lines 236-241, 715-721):
```typescript
return {
  pendingCount: data?.pending_count ?? 0,
  totalCount: data?.total_count ?? 0,
  pct: data?.pct_complete ?? 100,
  isPending,
  isLoading: query.isLoading,
};
```

> DELETE from `useReadiness`: the `wasPendingRef` effect and `window.location.reload()`
> (do not port lines 9-11, 45-65 of the analog). Constraint 4 / SC-5.

---

### `frontend/src/hooks/useReadiness.test.tsx` (NEW test, polling)

**Analog:** `useEvalCoverage.test.tsx` (lines 1-55+). Copy the entire scaffold.

**Module mock + wrapper + fake-timers setup** (lines 1-40) — copy verbatim:
```typescript
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return { ...actual, apiClient: { get: vi.fn() } };
});
```
`makeWrapper()` builds a `QueryClient` with `retry: false` (lines 21-30). `beforeEach` does `mockReset()` + `vi.useFakeTimers()` (33-36); `afterEach` `vi.useRealTimers()` (38-40).

**Flush pattern** (lines 49-52) — `await act(async () => { await Promise.resolve(); })` to flush the initial fetch without firing refetch timers. Reuse for the polling-stop-on-tier2 assertion.

---

### `frontend/src/components/EndgamesProcessingState.tsx` (NEW component, gate)

**Analog:** `EvalCoverageHeader.tsx` for the Cpu+counter copy idiom; UI-SPEC §Component Inventory for layout.

**Counter copy pattern** (EvalCoverageHeader lines 16, 23-28) — derive `analysedCount` the same way, reuse the `toLocaleString()` "{X} / {Y} games" phrasing:
```tsx
const analysedCount = Math.max(totalCount - pendingCount, 0);
...
<Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
<span className="truncate">
  Stockfish: <strong>{analysedCount.toLocaleString()}</strong>
  {' / '}
  <strong>{totalCount.toLocaleString()}</strong> games
</span>
```
Per UI-SPEC: centered full-height flex block, `Cpu h-8 w-8 text-amber-600 animate-pulse`, heading "Analyzing endgames" `text-xl font-semibold`, subtext "Stockfish: {X} / {Y} games" `text-sm text-muted-foreground`, body line `text-sm`. `data-testid="endgames-processing-state"`. No CTA button. One component for first-import AND incremental (D-01/D-02).

---

### `frontend/src/components/stats/EvalCpuPlaceholder.tsx` (NEW component, gate)

**Analog:** `EvalCoverageHeader.tsx` lines 17-30 — the amber-bar container is the literal template (Constraint 6: "styled to match"). UI-SPEC §EvalCpuPlaceholder gives the exact markup:
```tsx
<div className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm">
  <Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
  <span className="text-muted-foreground text-sm truncate">Analyzing…</span>
</div>
```
`data-testid="eval-cpu-placeholder"`. Amber classes match the shared "Stockfish in-progress" accent (see Shared Patterns → Eval-progress amber accent).

---

### `frontend/src/App.tsx` — gate-signal swap + Tier-2 toast (router/provider, event-driven)

**Analog 1 — route gate:** `ImportRequiredRoute` (lines 453-471). Keep the structure; swap the backing signal from `profileHasCompletedImport(profile)` to `readiness.tier1` from `useReadiness()`.
```tsx
function ImportRequiredRoute({ children }: { children: React.ReactNode }) {
  const { data: profile, isLoading } = useUserProfile();
  const hasCompletedImport = profileHasCompletedImport(profile);
  const shouldRedirect = !isLoading && profile != null && !hasCompletedImport;
  ...
  if (isLoading) {
    return <div ... data-testid="import-required-loading">Loading...</div>;
  }
  if (shouldRedirect) {
    return <Navigate to="/import" replace />;
  }
  return <>{children}</>;
}
```
Keep the `isLoading` early-return (RESEARCH Pitfall 2 — prevents content flash). `tier1` defaults to `false`, equivalent to the current redirect-when-not-imported behavior.

**Nav-lock signal swap:** `profileHasCompletedImport` is the `locked`/`hasCompletedImport` source at lines 40-42, 107, plus the mobile-nav/drawer usages (RESEARCH lines 319-324). Re-point all of them at `readiness.tier1`. Apply to desktop nav, mobile bottom nav, AND drawer (CLAUDE.md "always apply to mobile too").

**Analog 2 — fire-once watcher:** `ImportJobWatcher` (lines 46-56) uses a status-transition `useEffect`; the Tier-2 toast mirrors this plus the module-level `evalCompletionReloadFired` dedup idiom from `useEvalCoverage.ts` (lines 9-11). RESEARCH Pattern 1 (lines 402-422) + Pitfall 4 (lines 629-637): use a `useRef` `wasTier2False` to fire only on a genuine `false→true` transition in-session, suppress when `location.pathname.startsWith('/endgames')`, reset on token change (mirror `hasRestoredRef`).

**Sonner action-toast** — `toast` already imported (line 8); use the `action` API (UI-SPEC §Tier-2 toast):
```tsx
toast('Endgame analysis complete!', {
  action: {
    label: 'Explore Endgames',
    onClick: () => { navigate('/endgames'); queryClient.invalidateQueries({ queryKey: ['endgameOverview'] }); },
  },
});
```
`queryClient` from `useQueryClient()` is already in scope in `AppRoutes` (line 496).

---

### `frontend/src/pages/Endgames.tsx` — in-place Tier-2 gate (page, event-driven)

**Analog:** `ImportRequiredRoute` early-return idiom (App.tsx 464-470). Apply the same guard-then-render shape at the TOP of the page component (RESEARCH lines 300-305):
```tsx
const { tier2, pendingCount, totalCount } = useReadiness();
if (!tier2) {
  return <EndgamesProcessingState pendingCount={pendingCount} totalCount={totalCount} />;
}
```
This is the whole-page lock (D-01/D-02) — uniform for first-import and incremental. Nav link stays enabled (UI-SPEC Interaction Contracts); the page carries the message.

---

### `frontend/src/pages/Import.tsx` — state-machine copy (page, event-driven)

**Analog (self):** the `progressText` block (lines 91-95) is the exact string to change. Current `isDone` branch over-claims completion (Constraint 3):
```typescript
const progressText = isDone
  ? (data.games_imported === 0 ? 'No new games found since last sync' : `Imported ${data.games_imported} games from ${data.platform}`)
  : isError ? `Import failed: ${data.error ?? 'Unknown error'}`
  : `Importing ${data.username} (${data.platform})... ${data.games_fetched} fetched, ${data.games_imported} saved`;
```
The `isDone` "Imported N games" message must become "Games imported — openings ready." (no "complete" at hot-import done). Drive the new states from `useReadiness` per UI-SPEC §Import Page State Machine (copy table verbatim). The Tier-1 "Explore Openings" CTA is an in-page `<Button variant="default" data-testid="btn-explore-openings">` (NOT a toast — Constraint 4).

**Invalidation idiom** (lines 73-81) — the existing interval already invalidates `['imports','eval-coverage']` and `['endgameOverview']`; add `['imports','readiness']` to the same set so the import page reacts to tier transitions.

---

### `frontend/src/components/stats/OpeningStatsCard.tsx` — swap to `tier2` (component, self-edit)

**Self-edit seams** (RESEARCH "Exact Seams", lines 568-595):
- Line 9: replace `import { useEvalCoverage } from '@/hooks/useEvalCoverage';` with `useReadiness`.
- Line 60: `const { isPending, pendingCount } = useEvalCoverage();` → `const { tier2 } = useReadiness();`.
- Lines 218-243 (`scoreEvalBlock` eval row): when `!tier2`, replace BOTH the bullet row (218-224) and the eval-text+popover row (225-243) with one `<EvalCpuPlaceholder />` spanning the 2-col grid. Score row (180-217) is unchanged (WDL is not eval-dependent).
- Remove `isPending`/`pendingCount` from the `<BulletConfidencePopover>` call (lines 239-240).

`Cpu` already imported (line 1). Grid container is `grid-cols-[minmax(0,1fr)_auto]` (line 179) — the placeholder should span both columns.

---

### `EvalConfidenceTooltip.tsx` + `BulletConfidencePopover.tsx` — prop removal (component, deletion)

**`EvalConfidenceTooltip.tsx`** — delete the props (lines 55-59 interface, 81-82 destructure) and the entire pending-caveat JSX block (lines 114-128, `data-testid="eval-pending-caveat"`). Also drop the now-unused `AlertTriangle` import.

**`BulletConfidencePopover.tsx`** — delete `isPending`/`pendingCount` from the interface (lines 26-30), the destructure (lines 47-48), and the forwarded props on `<EvalConfidenceTooltip>` (lines 104-105).

> KNIP (SC-8, RESEARCH Pitfall 5): removing these prop surfaces can trip `npm run knip`.
> Check `frontend/src/components/__tests__/Openings.statsBoard.test.tsx` (~line 168, renders
> `BulletConfidencePopover` directly) and remove any passed-through `isPending`/`pendingCount`.
> Run `npm run knip` before declaring done.

---

## Shared Patterns

### Auth / Access Control (V4)
**Source:** `app/routers/imports.py` lines 130-132; `user_benchmark_percentiles_repository.py` lines 134-137.
**Apply to:** the new `/readiness` endpoint and `has_any_rows`.
```python
user: Annotated[User, Depends(current_active_user)],
session: Annotated[AsyncSession, Depends(get_async_session)],
```
User id always derived from the auth dep (`user.id`), never a query param. `has_any_rows` takes `user_id` as a keyword-only arg supplied by the router from `user.id`.

### Sequential reads on one AsyncSession
**Source:** `get_eval_coverage` lines 142-147.
**Apply to:** `get_readiness`.
Strictly sequential `await` calls; CLAUDE.md hard rule forbids `asyncio.gather` on a single `AsyncSession`. Short-circuit cheap branches (`total == 0`, `tier1 == False`) to skip downstream queries (RESEARCH lines 196-202).

### Eval-progress amber accent ("Stockfish is working")
**Source:** `EvalCoverageHeader.tsx` lines 21-23.
**Apply to:** `EvalCoverageHeader` (existing), `EndgamesProcessingState`, `EvalCpuPlaceholder`.
```
border-amber-400/40 bg-amber-50/60 text-amber-700   (+ Cpu animate-pulse)
```
Reserved exclusively for the Stockfish-in-progress surface (UI-SPEC §Color). UI-SPEC permits optional extraction to `theme.ts` (`EVAL_PROGRESS_BORDER` / `_BG` / `_ICON_COLOR`) per CLAUDE.md semantic-color rule; executor's call given only 2-3 use sites.

### TanStack Query shared-key polling
**Source:** `useEvalCoverage.ts` lines 28-40.
**Apply to:** `useReadiness`.
Shared `queryKey` deduplicates all consumers into one in-flight request; `refetchInterval` callback returns `false` to stop polling at the terminal state, else the interval constant. Safe `?? fallback` defaults on every returned field.

### Fire-once session dedup
**Source:** `useEvalCoverage.ts` lines 9-11 (`evalCompletionReloadFired`) + `ImportJobWatcher` transition effect (App.tsx 46-56).
**Apply to:** Tier-2 toast in App.tsx.
Use a `useRef` `wasTier2False` (not a module boolean) to fire only on an in-session `false→true` transition; reset on token change (RESEARCH Pitfall 4).

### Router test scaffolding (httpx ASGITransport, committed seeding)
**Source:** `tests/routers/test_imports_eval_coverage.py` lines 16-69.
**Apply to:** `test_imports_readiness.py`.
Module-level endpoint constant; `_make_game` seeder; `_register_and_login` helper; seed via `async_sessionmaker` (committed), NOT the rollback `db_session` fixture; named constants for magic numbers.

### Frontend hook test scaffolding (fake timers, module mock)
**Source:** `useEvalCoverage.test.tsx` lines 1-52.
**Apply to:** `useReadiness.test.tsx`.
`vi.mock('@/api/client', importActual + get: vi.fn())`; `makeWrapper()` with `retry:false`; fake timers in `beforeEach`/`afterEach`; `await act(async () => { await Promise.resolve(); })` to flush initial fetch without firing refetch timers.

---

## No Analog Found

None. Every new and modified file has a strong in-repo analog (all in the imports / eval-coverage / percentiles surface that this phase extends). Three files are pure deletions/edits of themselves (`useEvalCoverage.ts`, `EvalConfidenceTooltip.tsx`, `BulletConfidencePopover.tsx`).

---

## Metadata

**Analog search scope:** `app/routers/`, `app/schemas/`, `app/repositories/`, `tests/routers/`, `frontend/src/hooks/`, `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/types/`, `.claude/skills/`.
**Files read for extraction:** `imports.py` (router), `imports.py` (schema), `user_benchmark_percentiles_repository.py`, `test_imports_eval_coverage.py`, `useEvalCoverage.ts`, `useEvalCoverage.test.tsx`, `EvalCoverageHeader.tsx`, `App.tsx` (1-120, 440-499), `OpeningStatsCard.tsx` (1-70, 178-247), `EvalConfidenceTooltip.tsx` (50-129), `BulletConfidencePopover.tsx`, `Import.tsx` (70-139), `api.ts` (188-196).
**Pattern extraction date:** 2026-05-28
