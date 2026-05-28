# Phase 96: Import Readiness Gate - Research

**Researched:** 2026-05-28
**Domain:** UX gating, FastAPI endpoint design, React routing/state, TanStack Query
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Endgames locks fully on incremental imports, identically to first import (whole-page
  processing state, same component). No threshold-based or keep-prior-data variation.
- **D-02:** One generic processing/locked state component for both first-import and incremental.
  Same "Analyzing endgames (X/Y)" message; no returning-user-specific copy.

### Claude's Discretion
- How the backend authoritatively detects "Stage A/B percentiles persisted" without racing
  Stage B's `asyncio.create_task` (Constraint 1 forbids reusing eval-coverage 100% transition).
- Readiness endpoint shape: new `GET /imports/readiness` vs extending `GET /imports/eval-coverage`.
  Poll cadence; whether it replaces or coexists with the 3s eval-coverage poll.
- Locked-route UX: redirect to `/import`, in-place locked/processing state on the page, or
  disabled-nav (can't click), replacing `profileHasCompletedImport()` all-or-nothing lock.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope. Threshold-based incremental locking and
  returning-user-specific lock copy were considered and explicitly rejected (D-01/D-02).
</user_constraints>

---

## Summary

This phase replaces the `window.location.reload()` hack in `useEvalCoverage.ts` with an
authoritative two-tier readiness gate. The three "Claude's Discretion" wiring decisions were
fully resolved by reading the current code:

**Tier-2 signal:** The `UserBenchmarkPercentile` table already has a `computed_at` timestamp
column written on every `upsert_percentile` call. A simple `MAX(computed_at)` aggregation
gives a reliable "Stage B finished" timestamp without any schema changes. This is safer than
row-existence heuristics and avoids the race window entirely.

**Endpoint shape:** A new dedicated `GET /imports/readiness` endpoint returning both tiers.
This is clean, follows the project's recorded D-01/D-04 preference for dedicated endpoints,
and lets the frontend retire `useEvalCoverage`'s 100%-transition auto-reload entirely. The
existing `GET /imports/eval-coverage` remains for the `EvalCoverageHeader` global bar.

**Locked-route UX:** In-place locked/processing state on the page for Endgames (not a
redirect). Redirect to `/import` only for first-import Openings/Overview (no games yet). Nav
links for Endgames stay clickable on incremental imports; the page itself renders the locked
state. This satisfies the per-page table without changing `profileHasCompletedImport()` for
the Tier-1 gate (which already works correctly), while adding a new Tier-2 gate for Endgames.

**Primary recommendation:** Add `percentiles_ready_at: datetime | None` to
`ReadinessResponse` derived from `MAX(computed_at)` on `user_benchmark_percentiles` — no
migration needed; the column exists. Build `GET /imports/readiness` on top of three parallel
reads (active jobs, pending evals, max percentile timestamp). Replace the auto-reload in
`useEvalCoverage` with a `useReadiness` hook; feed both Tier flags to the routing layer and
the Endgames page gate.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tier-1 readiness (no active import) | API / Backend | — | Job registry is server-side (in-memory + DB); frontend cannot know |
| Tier-2 readiness (evals done + percentiles committed) | API / Backend | — | Requires DB queries to game rows + percentile table |
| Route locking / redirect (first import) | Frontend Server (client-side router) | — | React Router `<Navigate>` in `ImportRequiredRoute` |
| Endgames whole-page locked state | Frontend (page component) | — | In-place render guard keyed off `tier2` from readiness hook |
| Openings Cpu-placeholder per eval metric | Frontend (component) | — | `OpeningStatsCard` already has the Cpu icon seam |
| Import-page state machine | Frontend (page component) | — | Driven by readiness data + active-job state already on Import page |
| Sonner "Explore Endgames" toast (Tier-2 CTA) | Frontend (App.tsx / hook) | — | Module-level dedupe flag pattern already established |
| Tier-2 toast suppression when on /endgames | Frontend (App.tsx) | — | `useLocation` already in scope at AppRoutes level |
| EvalCoverageHeader global bar | Frontend (ProtectedLayout) | — | Already mounted once in ProtectedLayout; must stay there |

---

## Wiring Decision 1: Tier-2 Readiness Signal (CORRECTNESS-CRITICAL)

### Recommendation: `MAX(computed_at)` on `user_benchmark_percentiles` — no migration

**Race anatomy.** In `eval_drain.py` at line 568, after committing the eval write window:

```python
async with async_session_maker() as read_session:
    ...
    for uid in zero_pending:
        asyncio.create_task(compute_stage_b(uid))
```

`asyncio.create_task` schedules `compute_stage_b` as a *new* coroutine that will run on the
event loop when current coroutines yield. The drain loop immediately proceeds to the next
batch. There is a window — typically milliseconds to seconds — between `pending_count == 0`
(observable from `games.evals_completed_at`) and the final `session.commit()` inside
`compute_stage_b` (line 464). Any frontend check that fires the moment evals hit 0% pending
can land before Stage B commits.

**Candidate analysis:**

| Candidate | Race window | Testable (SC-1) | Notes |
|-----------|-------------|-----------------|-------|
| (a) `pending_count == 0` only | RACES. Stage B task is scheduled but not committed yet. `pending_count` reaches 0 before `compute_stage_b` commits its rows. | Hard to distinguish "drain done, Stage B pending" from "Stage B done" | Rejected |
| (b) Row existence (`COUNT(*) > 0` on `user_benchmark_percentiles`) | SAFER but ambiguous. Rows may be absent because user is below the floor for ALL (metric, tc) cells (legit no-op Stage B). Can't distinguish "not yet run" from "ran, zero above-floor rows". | Tests can seed above-floor data and assert row exists, but need to know floor semantics | Fragile |
| (c) `pending_count == 0 AND >= 1 percentile row` | Same ambiguity as (b); skips users who never get any rows | Testable but same legit-absence ambiguity | Fragile |
| (d) **`MAX(computed_at)` on `user_benchmark_percentiles` columns** | **No race.** `computed_at` is a server-side `func.now()` written by `upsert_percentile` (line 121 of `user_benchmark_percentiles_repository.py`). It is `None` before any Stage B rows exist and becomes a real timestamp after the first commit. The endpoint can return `percentiles_ready_at: datetime | None`; Tier 2 requires this to be non-None. | Test: seed games + evals done + no percentile rows → `tier2=False`; then add a row → `tier2=True`. Exact shape SC-1 requires. | **Recommended** |

**What `compute_stage_b` actually writes** (lines 393-471,
`user_benchmark_percentiles_service.py`): one `session.commit()` at line 464 after iterating
all `(family, tc)` combinations. All Stage B rows land in a SINGLE commit. So `MAX(computed_at)`
after that commit gives a stable, post-commit timestamp. Stage A (`compute_stage_a`,
lines 325-390) does the same — one `session.commit()` at line 382. Stage A writes
`score_gap` rows only; Stage B writes the other 7 families. Disjoint write sets.

**Implementation:** Add `count_percentile_rows_for_user(session, user_id)` to
`user_benchmark_percentiles_repository.py` (or inline in the readiness endpoint). Actually a
simpler query — `SELECT MAX(computed_at) FROM user_benchmark_percentiles WHERE user_id = ?`
— returning `datetime | None`. No schema change; `computed_at` already exists on the table
(line 122, `user_benchmark_percentile.py`).

**Users with no above-floor cells** (Stage B is a no-op; zero percentile rows written): for
these users `MAX(computed_at) IS NULL` forever. The readiness endpoint must handle this case:
if `pending_count == 0` AND no active import AND the user has never gotten any percentile
rows, it should still declare Tier 2 ready after Stage B would have run. The safest way is:
Tier 2 = `pending_count == 0` AND no active import AND (at least one percentile row exists OR
the user has no games). "No games" is trivially ready (nothing to drain); "has games but no
percentile rows" after drain is a below-floor user who should still see Endgames (with
percentile chips simply absent — the empty-row suppression already handles this). Therefore:

```
tier2 = (
    no_active_import
    AND pending_count == 0
    AND (total_games == 0 OR percentile_row_exists)
)
```

This produces a testable condition for SC-1: "evals done (`pending_count == 0`), active
import gone, but Stage B rows absent for a user who HAS above-floor data" → Tier 2 false.
In practice this window is the `asyncio.create_task` gap: milliseconds to a few seconds
depending on event-loop load. The 3s poll cadence will bridge it on the next tick.

**No migration required.** `computed_at` is a DB-server-default column present in all
existing rows.

---

## Wiring Decision 2: Readiness Endpoint Shape

### Recommendation: New `GET /imports/readiness`, replace `useEvalCoverage` auto-reload, keep eval-coverage poll for the global progress bar

**Why a new endpoint (not extending `GET /imports/eval-coverage`):**

The eval-coverage endpoint (line 129, `app/routers/imports.py`) has locked response keys per
docstring D-01/D-04: `pending_count`, `total_count`, `pct_complete`. Its concern is raw eval
drain progress. Tier-1/Tier-2 readiness is a *derived* semantic layer on top of multiple DB
queries (job registry + pending evals + percentile table). Extending eval-coverage would mix
concerns and break the D-01/D-04 contract. The project already recorded preference for
dedicated endpoints in the eval-coverage docstring; this phase should follow that pattern.

**Proposed Pydantic response schema** (`app/schemas/imports.py`):

```python
class ReadinessResponse(BaseModel):
    """Response for GET /imports/readiness.

    tier1: no import job in pending/in_progress for this user.
    tier2: tier1 AND pending_count==0 AND (no games OR percentile rows exist).
    pending_count: games still awaiting Stockfish eval (mirrors eval-coverage).
    total_count: total games for user (needed for import-page X/Y display).
    """
    tier1: bool
    tier2: bool
    pending_count: int
    total_count: int
```

The frontend needs `pending_count` and `total_count` to drive the import-page state machine
(Constraint 2: "analyzing endgames (X / Y)") and the Endgames locked-state progress display.
These fields come for free alongside the Tier computation — no second query needed.

**Backend endpoint** (`app/routers/imports.py`):

```python
@router.get("/readiness", response_model=ReadinessResponse)
async def get_readiness(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReadinessResponse:
    """Two-tier import readiness gate. Tier 1: no active import.
    Tier 2: Tier 1 AND evals done AND percentile rows committed."""
    has_active = bool(import_service.find_active_jobs_for_user(user.id))
    tier1 = not has_active
    total = await game_repository.count_games_for_user(session, user.id)
    pending = 0 if not tier1 else await game_repository.count_pending_evals(session, user.id)
    percentile_ready = total == 0 or await user_benchmark_percentiles_repository.has_any_rows(session, user.id)
    tier2 = tier1 and pending == 0 and percentile_ready
    return ReadinessResponse(tier1=tier1, tier2=tier2, pending_count=pending, total_count=total)
```

Note: `count_pending_evals` is skipped when `tier1=False` to avoid an unnecessary DB query
during an active import. The `has_any_rows` helper is a single `EXISTS` query.

**Poll cadence and hook design:**

The existing `useEvalCoverage` hook polls at 3s and feeds `EvalCoverageHeader`. That hook
must STAY for the global progress bar (Constraint 5 — `EvalCoverageHeader` is in
`ProtectedLayout`). The new `useReadiness` hook polls the readiness endpoint separately:

```typescript
// frontend/src/hooks/useReadiness.ts
const READINESS_POLL_INTERVAL_MS = 3_000;

export function useReadiness() {
  const query = useQuery<ReadinessResponse>({
    queryKey: ['imports', 'readiness'],
    queryFn: async () => { ... },
    staleTime: 3_000,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop when fully ready
      if (data?.tier2) return false;
      return READINESS_POLL_INTERVAL_MS;
    },
  });
  return {
    tier1: query.data?.tier1 ?? false,
    tier2: query.data?.tier2 ?? false,
    pendingCount: query.data?.pending_count ?? 0,
    totalCount: query.data?.total_count ?? 0,
    isLoading: query.isLoading,
  };
}
```

Safe defaults: `tier1=false` and `tier2=false` before first fetch. This prevents a flash of
unlocked content on initial load. Both `useEvalCoverage` (for the header bar) and
`useReadiness` (for gating) are in flight — this is two separate 3s polls, each making one
HTTP request. Sharing queryKey `['imports', 'readiness']` ensures all consumers deduplicate
into one in-flight request.

**Query invalidations on Tier transition:** When `tier2` transitions from false to true, the
Tier-2 "Explore Endgames" toast must also trigger query invalidations:

```typescript
queryClient.invalidateQueries({ queryKey: ['endgameOverview'] });
queryClient.invalidateQueries({ queryKey: ['imports', 'readiness'] });
```

The reactive reveals (Endgames unlock, Openings eval metrics) happen from the next poll
tick of `useReadiness` naturally — no forced navigation needed.

**Auto-reload retirement:** The `evalCompletionReloadFired` module-level guard and the
`useEffect` that calls `window.location.reload()` in `useEvalCoverage.ts` are deleted
(lines 49-65). The hook remains for `EvalCoverageHeader` but loses the reload logic. All
tests in `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx` that test the polling and
default-values behavior remain valid and require no changes. The auto-reload test case (if
it exists) is deleted.

---

## Wiring Decision 3: Locked-Route UX

### Recommendation: Hybrid — redirect for first-import Tier-1 (existing behavior preserved), in-place locked state for Endgames (Tier 2), no nav-link disabling for Endgames

**Analysis of the three candidates:**

| Approach | First-import | Incremental | Direct URL |
|----------|-------------|-------------|------------|
| Redirect to `/import` for ALL locked pages | Works for first-import, but wrong for incremental Endgames: user has games, Openings is usable, sending them to `/import` on Endgames tap is jarring | Poor | SC-2 passes for first-import; fails for incremental (should show processing state) |
| In-place locked state for ALL | Requires new "you need to import first" empty state on Openings/Overview for first import — replicates what the import page already does | Good | Works for both cases; more screens to build |
| **Hybrid (recommended)** | **`ImportRequiredRoute` (Tier 1) handles first-import redirect exactly as today; Endgames adds its own Tier-2 in-place gate inside the page** | **Openings/Overview stay usable (no gate); Endgames shows in-place processing state** | **SC-2: direct URL to Endgames → locked state; direct URL to Openings/Overview on first import → redirect** |

**Concrete implementation in `App.tsx`:**

`ImportRequiredRoute` already handles the first-import case for Openings and Overview
(lines 453-471). Its backing signal changes from `profileHasCompletedImport()` (which uses
`*_last_sync_at` timestamps) to `readiness.tier1` from `useReadiness`. This is equivalent:
`tier1 = no active import job`, which becomes true at the same moment
`*_last_sync_at` is set (after the first successful import). No behavioral change for
Openings/Overview first-import redirect — just a new signal source.

For Endgames, the gate is NOT `ImportRequiredRoute`. Instead, the `EndgamesPage` component
itself renders a whole-page `EndgamesProcessingState` when `!readiness.tier2`. This satisfies
D-01/D-02 (same state for first-import and incremental, one component) and SC-2 (direct URL
shows locked state, not partial data).

```tsx
// In App.tsx AppRoutes:
<Route path="/endgames/*" element={
  <ImportRequiredRoute>
    <EndgamesPage />  {/* EndgamesPage checks tier2 internally */}
  </ImportRequiredRoute>
} />
```

`EndgamesPage` (top of component):

```tsx
const { tier2, pendingCount, totalCount } = useReadiness();
if (!tier2) {
  return <EndgamesProcessingState pendingCount={pendingCount} totalCount={totalCount} />;
}
```

`EndgamesProcessingState` is the new component (D-02): shows the eval X/Y counter,
"Analyzing endgames" heading, and the `EvalCoverageHeader` bar. It maps directly to the
import-page state machine's "analyzing endgames" step visually.

**Nav-link disabling:** The current nav already disables all non-import links for users who
have never imported (the `locked` var based on `!hasCompletedImport`). For Endgames during
an incremental import, the nav link stays ENABLED — Tier-2 gating happens inside the page,
not at the nav. This is intentional: the user taps Endgames, sees the processing state with
the X/Y progress, and knows why they're waiting. Disabling the nav tap would be confusing
("can't tap Endgames while importing") and inconsistent with the informative-holding-page
design (Constraint 2).

**`profileHasCompletedImport()` fate:** This function is used as the `locked` nav signal
(lines 107, 248, 325 in `App.tsx`). It checks `*_last_sync_at` fields on the profile, which
are set immediately when the first import completes. `tier1` from `useReadiness` signals the
same moment (no active import = import job moved to `completed`/`failed`). The nav-locking
logic can be refactored to use `readiness.tier1` (or a derived `hasCompletedImport` from the
readiness hook) so there's one signal source. This is a straightforward swap.

---

## Standard Stack

### Core (existing — no new packages)

| Library | Version | Purpose | Role in Phase |
|---------|---------|---------|---------------|
| FastAPI | 0.115.x | HTTP routing | New `GET /imports/readiness` endpoint |
| SQLAlchemy async | 2.x | DB queries | `MAX(computed_at)` + existing query functions |
| Pydantic v2 | latest | Response schema | `ReadinessResponse` model |
| React + TanStack Query | 19 + v5 | Frontend hook | `useReadiness` hook, query invalidation |
| react-router-dom | v6 | Routing | `ImportRequiredRoute` gate signal change |
| sonner | latest | Toast | Tier-2 "Explore Endgames" action toast |

No new packages. All capabilities are built from existing stack.

### Package Legitimacy Audit

No external packages are being installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
GET /imports/readiness (new)
  ├── import_service.find_active_jobs_for_user()    [in-memory]
  ├── game_repository.count_games_for_user()         [DB]
  ├── game_repository.count_pending_evals()          [DB, skip if tier1=false]
  └── percentiles_repository.has_any_rows()          [DB, skip if tier1=false or no games]
       └── SELECT EXISTS ... FROM user_benchmark_percentiles WHERE user_id=?

ReadinessResponse {tier1, tier2, pending_count, total_count}
  │
  ▼
useReadiness() [3s poll, queryKey ['imports','readiness']]
  ├── App.tsx: tier1 → ImportRequiredRoute (replaces profileHasCompletedImport)
  ├── App.tsx: tier2 → Tier-2 toast watcher (fire-once, suppress on /endgames)
  ├── EndgamesPage: tier2 → in-place EndgamesProcessingState guard
  ├── OpeningsPage (StatsTab / OpeningStatsCard): tier2 → Cpu-placeholder vs real eval metric
  └── ImportPage: state machine (tier1, tier2, pending_count, total_count)

useEvalCoverage() [3s poll, queryKey ['imports','eval-coverage']] — STAYS, minus auto-reload
  └── EvalCoverageHeader (ProtectedLayout) — unchanged
```

### Recommended Project Structure

No new directories needed. New files:

```
app/
  routers/imports.py          — add GET /imports/readiness
  schemas/imports.py          — add ReadinessResponse
  repositories/
    user_benchmark_percentiles_repository.py  — add has_any_rows()
frontend/src/
  hooks/
    useReadiness.ts            — NEW: two-tier poll hook
  pages/
    Endgames.tsx               — add EndgamesProcessingState guard at top
  components/
    EndgamesProcessingState.tsx  — NEW: whole-page locked state (D-01/D-02)
    stats/OpeningStatsCard.tsx  — swap real eval rows for Cpu-placeholder when !tier2
tests/
  routers/
    test_imports_readiness.py  — NEW: truth-table tests for the two tiers
```

### Pattern 1: Tier-2 "fire-once" toast in App.tsx

Mirrors the existing `evalCompletionReloadFired` module-level guard:

```typescript
let tier2ToastFired = false;

// In AppRoutes, alongside the existing job-watcher logic:
useEffect(() => {
  if (!readiness.tier2 || tier2ToastFired) return;
  if (location.pathname.startsWith('/endgames')) return; // suppress if already there
  tier2ToastFired = true;
  toast('Endgame analysis complete!', {
    action: {
      label: 'Explore Endgames',
      onClick: () => {
        navigate('/endgames');
        queryClient.invalidateQueries({ queryKey: ['endgameOverview'] });
      },
    },
  });
}, [readiness.tier2, location.pathname, navigate, queryClient]);
```

Reset `tier2ToastFired` on token change (same pattern as `hasRestoredRef` in AppRoutes).

### Pattern 2: Openings Cpu-placeholder

`OpeningStatsCard` (line 60) already imports `useEvalCoverage` to get `isPending` /
`pendingCount`. Under Phase 96 the card switches to `useReadiness` and gates on `tier2`:

```tsx
// Before (to remove):
const { isPending, pendingCount } = useEvalCoverage();

// After:
const { tier2 } = useReadiness();
```

When `!tier2`, the `scoreEvalBlock` div replaces the eval row (lines 218-243) with a
single `EvalCpuPlaceholder` component:

```tsx
<div className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/60 px-3 py-2 text-sm">
  <Cpu className="h-4 w-4 shrink-0 text-amber-700 animate-pulse" aria-hidden="true" />
  <span className="text-muted-foreground text-sm truncate">Analyzing…</span>
</div>
```

This is a new component (`EvalCpuPlaceholder`) styled to match `EvalCoverageHeader`
(amber border/bg, pulsating Cpu icon) per Constraint 6.

The `isPending` / `pendingCount` props flow removed from `BulletConfidencePopover` →
`EvalConfidenceTooltip` as part of Constraint 7 (eval counter removal from tooltips).

### Anti-Patterns to Avoid

- **Reusing `useEvalCoverage`'s 100%-transition as Tier-2 trigger.** Explicitly forbidden by
  Constraint 1. The race window (Stage B not committed yet) is real: `asyncio.create_task`
  at line 568 of `eval_drain.py` fires BEFORE Stage B rows are in the DB.
- **`asyncio.gather` on the same `AsyncSession`.** The readiness endpoint makes 3-4 DB reads.
  They must run SEQUENTIALLY on one session (CLAUDE.md hard rule).
- **Calling `window.location.reload()` for Tier transitions.** Constraint 4 and SC-5 forbid
  this. Reactive reveal via poll + query invalidation only.
- **Disabling Endgames nav link during incremental import.** Contradicts the informative
  holding-page design; the page itself shows the processing state.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fire-once toast dedup | Custom localStorage flag | Module-level boolean (same as `evalCompletionReloadFired`) | Already established pattern; resets on page reload naturally |
| Shared in-flight readiness request | Multiple `fetch` calls from different components | TanStack Query `queryKey` dedup | Already how `useEvalCoverage` works across `EvalCoverageHeader` + callers |
| DB existence check | Raw SQL string | `select(func.count(1)).where(...).limit(1)` via SQLAlchemy | Consistent with repo layer |

---

## Current Code Inventory (what to retire / rewrite)

### Auto-reload to retire

`frontend/src/hooks/useEvalCoverage.ts` lines 49-65:

```typescript
const wasPendingRef = useRef(false);
useEffect(() => {
  if (isPending) { wasPendingRef.current = true; return; }
  if (wasPendingRef.current && !evalCompletionReloadFired && data && ...) {
    evalCompletionReloadFired = true;
    window.location.reload();  // <-- RETIRE THIS
  }
}, [isPending, data]);
```

Delete the entire `wasPendingRef` + effect + `evalCompletionReloadFired` guard. The hook
returns the same `{ pendingCount, totalCount, pct, isPending, isLoading }` shape so
`EvalCoverageHeader` is unaffected.

### `profileHasCompletedImport()` gate

`App.tsx` lines 40-42 + usages at lines 107, 248, 325:

```typescript
function profileHasCompletedImport(profile: UserProfile | null | undefined): boolean {
  return profile != null && (profile.chess_com_last_sync_at !== null || profile.lichess_last_sync_at !== null);
}
```

This function drives three nav-lock `locked` variables and `ImportRequiredRoute`. Replace its
backing data with `readiness.tier1` from `useReadiness`. The `*_last_sync_at` timestamps are
still available on the profile for `formatLastSync` display; we just stop using them for
gating. Function can be removed; its one-liner semantics inline into the `locked` expressions.

### Import-page over-claiming completion messaging

`Import.tsx` line 91-95 (`ImportProgressBar.progressText`):

```typescript
const progressText = isDone
  ? (data.games_imported === 0
    ? 'No new games found since last sync'
    : `Imported ${data.games_imported} games from ${data.platform}`)   // <-- OVER-CLAIMS
  : isError ? ...
  : `Importing ...`;
```

When `isDone` (hot-import `status=completed`), the current green "Imported N games from
platform" message implies full completion (Constraint 3 violation). This must change to:
"Games imported — openings ready; endgame analysis in progress."

The import-page state machine (Constraint 2, SC-3) drives this:

| State | Condition | Message / UI |
|-------|-----------|--------------|
| No games yet | `total_count == 0`, no active job | Import form |
| Importing | active job exists | progress bar (existing `ImportProgressBar`) |
| **Tier 1 reached** | `tier1=true`, `tier2=false` | "Games imported — openings ready." + "Explore Openings" CTA + eval X/Y progress |
| Analyzing | `tier1=true`, `tier2=false`, `pending_count > 0` | "Analyzing endgames (X / Y)" |
| **Tier 2 reached** | `tier2=true` | "Ready — all analysis complete." |

The Tier-1 "Explore Openings" CTA is an in-page `Button` that navigates to `/openings`
(Constraint 4 — NOT a toast; user is already looking at the import page).

### Eval counter in `EvalConfidenceTooltip`

`frontend/src/components/insights/EvalConfidenceTooltip.tsx` lines 114-128:

```tsx
{isPending === true && (pendingCount ?? 0) > 0 && (
  <p ... data-testid="eval-pending-caveat">
    ...Stockfish is still analysing {(pendingCount ?? 0).toLocaleString()} more...
  </p>
)}
```

Delete this JSX block and the `isPending` / `pendingCount` props from the component
interface (lines 56-60). The props propagate from `BulletConfidencePopover`; remove them
there too (lines 26-30, 48-49, 105 in `BulletConfidencePopover.tsx`). The `useEvalCoverage`
import in `OpeningStatsCard.tsx` (line 9) is replaced by `useReadiness`.

**Knip impact (SC-8):** Removing `isPending` / `pendingCount` from `EvalConfidenceTooltip`
props removes an export surface. Knip checks unused exports (`npm run knip`). If any tests
directly import `EvalConfidenceTooltip` with those props, those test usages must also be
updated. The existing `noEndgameSkillString.test.tsx` mocks `useEvalCoverage` — that mock
can stay since `EvalCoverageHeader` still uses it.

---

## Openings Eval-Based Metrics: Exact Seams

**Location:** `frontend/src/components/stats/OpeningStatsCard.tsx`

The Cpu-placeholder treatment (Constraint 6, SC-7) applies to the **eval row** inside
`scoreEvalBlock` (lines 218-243). Specifically:

- **Bullet chart row** (lines 218-225): `mgBulletContent` — a `MiniBulletChart` when
  `hasMgEval`, else `—`
- **Eval text + popover row** (lines 225-243): `mgEvalTextContent` (signed pawns + Cpu icon) +
  `BulletConfidencePopover`

Both of these together constitute the "one-row eval-based metric" per Constraint 6. When
`!tier2`, replace BOTH with one `EvalCpuPlaceholder` bar spanning the full 2-col grid.

The **score row** (lines 180-217) stays unaffected — WDL score is NOT eval-dependent.

The Cpu icon (`<Cpu>` from lucide-react) is already imported at line 1 of `OpeningStatsCard`.
The amber styling is already defined in `EvalCoverageHeader` — extract shared amber colors to
`theme.ts` as named constants per CLAUDE.md if they aren't already there.

`OpeningStatsCard` is used in `OpeningStatsSection` which is used in `StatsTab` of the
Openings page. No other subtab (`ExplorerTab`, `GamesTab`, `InsightsTab`) uses this
component. The `ExplorerTab` renders per-move eval arrows and the `GamesTab` renders
`EvalConfidenceTooltip` in position-level stats — check if `GamesTab` / `ExplorerTab`
also pass `isPending`/`pendingCount` (grep showed none; these eval displays are not
counter-based).

---

## Common Pitfalls

### Pitfall 1: Below-floor users lock themselves out of Endgames forever
**What goes wrong:** If `tier2 = pending_count == 0 AND percentile_row_exists`, a user whose
entire game history is below the Stage B floor never gets any rows. `tier2` stays `false`
forever even after the drain completes.
**Why it happens:** The "row existence implies above-floor" design means legitimate no-op
Stage B runs leave zero rows.
**How to avoid:** The Tier-2 condition must include `total_games == 0 OR percentile_row_exists`
— i.e., if the user has no games OR has at least one percentile row, they pass. After the
drain completes with zero rows written, `pending_count == 0` is satisfied; `total_games > 0`
is true; but `percentile_row_exists` is false. Without the `total_games == 0` escape, this
user sees the locked state forever.

Correct condition: `tier2 = tier1 AND pending_count == 0 AND (total_games == 0 OR percentile_row_exists)`.

### Pitfall 2: `tier1` defaults to `false` causes empty-account users to get stuck
**What goes wrong:** `useReadiness` default is `tier1=false`. A brand-new user with no games
hits `/openings` and is redirected to `/import` — which is correct. But if the readiness
endpoint takes 1-2s to respond, the `isLoading` period must also redirect, or users see a
flash of Openings before the redirect.
**How to avoid:** Keep the `isLoading` render path in `ImportRequiredRoute` (line 464):
`if (isLoading) return <div>Loading...</div>`. The new `readiness.isLoading` replaces
`profile.isLoading` there.

### Pitfall 3: `asyncio.create_task` fires Stage B multiple times during a drain
**Already handled.** `users_with_zero_pending` in `game_repository.py` (line 93) already
filters to users with `pending_count == 0 AND no active import_job`. Stage B cannot fire
during an active import. This is the Phase 94.1 Plan 13 gap-closure — documented in the
function's docstring.

### Pitfall 4: Tier-2 toast fires on every page load after Tier 2 is reached
**What goes wrong:** `tier2ToastFired` is a module-level JS boolean that resets on
hard reload. After the user navigates away and comes back in the same session, the toast
won't re-fire. But if they close and reopen the tab after Tier 2, the module reloads and
`tier2ToastFired = false` again, so the toast fires again on the first `tier2=true` poll.
**How to avoid:** Gate on `wasTier2False` using a `useRef` (same pattern as `wasPendingRef`
in the existing auto-reload). Only fire when `tier2` transitions FROM false TO true in the
current session. If `tier2` is already true on the first fetch, `wasTier2False.current`
is never set to `true`, so the toast never fires.

### Pitfall 5: Knip flags `isPending`/`pendingCount` removal as dead exports
**What goes wrong:** After removing `isPending`/`pendingCount` from `EvalConfidenceTooltip`
and `BulletConfidencePopover`, knip may flag them as unused if any test file still imports
the removed interface shape.
**How to avoid:** Update the test file `Openings.statsBoard.test.tsx` (line 168) which
directly renders `BulletConfidencePopover` — confirm the removed props are not passed there.
Run `npm run knip` before considering the feature complete (SC-8).

---

## Code Examples

### Backend: `has_any_rows` helper

```python
# app/repositories/user_benchmark_percentiles_repository.py
async def has_any_rows(session: AsyncSession, *, user_id: int) -> bool:
    """Return True if at least one percentile row exists for user_id.

    Used by GET /imports/readiness to distinguish:
    - Stage B not yet run (no rows, but pending_count > 0 or task not scheduled)
    - Stage B completed but user is below floor for all cells (no rows, pending_count == 0)
    Both appear as no-rows; caller must combine with pending_count == 0 check.
    """
    result = await session.execute(
        select(func.count(UserBenchmarkPercentile.user_id))
        .where(UserBenchmarkPercentile.user_id == user_id)
        .limit(1)
    )
    return (result.scalar() or 0) > 0
```

### Backend: `ReadinessResponse` Pydantic model

```python
# app/schemas/imports.py (addition)
class ReadinessResponse(BaseModel):
    """Response for GET /imports/readiness.

    tier1: no import job in pending/in_progress.
    tier2: tier1 AND pending_count==0 AND (no games OR percentile rows exist).
    pending_count: games still awaiting Stockfish eval.
    total_count: total games for user.
    """
    tier1: bool
    tier2: bool
    pending_count: int
    total_count: int
```

### Frontend: `useReadiness` hook (sketch)

```typescript
// frontend/src/hooks/useReadiness.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ReadinessResponse } from '@/types/api';

const READINESS_POLL_INTERVAL_MS = 3_000;
const READINESS_STALE_TIME_MS = 3_000;

export function useReadiness() {
  const query = useQuery<ReadinessResponse>({
    queryKey: ['imports', 'readiness'],
    queryFn: async () => {
      const response = await apiClient.get<ReadinessResponse>('/imports/readiness');
      return response.data;
    },
    staleTime: READINESS_STALE_TIME_MS,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.tier2) return false; // stop polling when fully ready
      return READINESS_POLL_INTERVAL_MS;
    },
  });

  return {
    tier1: query.data?.tier1 ?? false,
    tier2: query.data?.tier2 ?? false,
    pendingCount: query.data?.pending_count ?? 0,
    totalCount: query.data?.total_count ?? 0,
    isLoading: query.isLoading,
  };
}
```

---

## Validation Architecture

`nyquist_validation` is enabled. All 9 success criteria map to testable behaviors.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest-asyncio + httpx ASGITransport |
| Frontend framework | Vitest + @testing-library/react |
| Backend quick run | `uv run pytest tests/routers/test_imports_readiness.py -x` |
| Backend full suite | `uv run pytest -x` |
| Frontend quick run | `npm test -- --run` |

### Phase Requirements → Test Map

| SC | Behavior | Test Type | Automated Command |
|----|----------|-----------|-------------------|
| SC-1 | Tier 2 is false when evals done but Stage B rows absent | pytest integration | `test_imports_readiness.py::test_tier2_false_when_evals_done_but_no_percentile_rows` |
| SC-1 | Tier 2 is true when evals done AND percentile row exists | pytest integration | `test_imports_readiness.py::test_tier2_true_when_evals_and_percentiles_ready` |
| SC-1 | Tier 1 is false when active import exists | pytest integration | `test_imports_readiness.py::test_tier1_false_when_active_import` |
| SC-2 | Direct URL to /endgames without Tier 2 renders locked state | Frontend component | Endgames.readinessGate.test.tsx |
| SC-2 | Direct URL to /openings without Tier 1 redirects to /import | Frontend component | App.routing.test.tsx (or existing ImportRequiredRoute test) |
| SC-2 | Incremental import: Openings stays reachable, Endgames shows locked state | Frontend component | App.routing.test.tsx |
| SC-3 | Import page shows "Explore Openings" CTA at Tier 1, eval X/Y progress | Frontend component | Import.stateMachine.test.tsx |
| SC-4 | Import progress bar does not say "Import complete" at hot-import done | Frontend component | Import.stateMachine.test.tsx |
| SC-5 | No `window.location.reload()` in `useEvalCoverage` | Code review / unit | `useEvalCoverage.test.tsx` (existing + check for no-reload assertion) |
| SC-5 | Tier-2 toast fires once when tier2 transitions false→true | Frontend unit | useReadiness.test.tsx or App.tier2toast.test.tsx |
| SC-6 | `EvalCoverageHeader` visible on Openings while drain runs | Frontend component | Verify EvalCoverageHeader appears in ProtectedLayout tests |
| SC-7 | `OpeningStatsCard` shows Cpu placeholder (not eval row) when `!tier2` | Frontend component | OpeningStatsCard.test.tsx (new case) |
| SC-8 | `EvalConfidenceTooltip` no longer renders pending caveat | Frontend component | `EvalConfidenceTooltip.test.tsx` — assert `data-testid="eval-pending-caveat"` absent |
| SC-8 | `npm run knip` passes | CI gate | `npm run knip` |
| SC-9 | `ty check`, `ruff`, `pytest`, `lint`, `test` all green | CI gate | Standard pre-PR checklist |

### Wave 0 Gaps

- [ ] `tests/routers/test_imports_readiness.py` — new, covers SC-1 truth table
- [ ] `frontend/src/hooks/__tests__/useReadiness.test.tsx` — new, mirrors `useEvalCoverage.test.tsx` structure
- [ ] `frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx` — new, covers SC-2 Endgames locked state

---

## Security Domain

`security_enforcement` is not explicitly `false` in config.json, so this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users `current_active_user` dep on new endpoint |
| V3 Session Management | no | No session changes |
| V4 Access Control | yes | `has_any_rows` must use `user_id` from auth dep, never query param (existing V4 mitigation in repo docstring) |
| V5 Input Validation | no | No user input on readiness endpoint |
| V6 Cryptography | no | No crypto changes |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| User A reads User B's readiness | Information Disclosure | `user_id` always from `current_active_user` FastAPI dep; already enforced on `fetch_for_user` (repo docstring) |
| Tier-2 flag cached beyond its validity | Information Disclosure | `staleTime: 3_000ms`; Tier-2 = `false` is the safe default before first fetch |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `computed_at` on `user_benchmark_percentiles` is refreshed on every upsert (including re-runs) | Wiring Decision 1 | Low — confirmed in repo line 121: `"computed_at": func.now()` on every on-conflict update |
| A2 | Stage B never runs while an active import exists (Plan 13 gate) | Wiring Decision 1 | Low — confirmed in `users_with_zero_pending` docstring line 93-108, game_repository.py |
| A3 | `find_active_jobs_for_user` covers both in-memory and DB-persisted active jobs | Wiring Decision 2 | Medium — it checks only in-memory `_jobs` registry. After server restart, in-progress jobs are gone from memory. Mitigated: `get_active_imports` also checks DB for recently-failed jobs; the readiness endpoint can combine both signals if needed, or accept that restart-lost in-progress jobs are treated as "no active import" (existing behavior) |

**A3 mitigation note:** The existing `/imports/active` endpoint already handles the
"DB-persisted failed jobs after restart" case by returning failed DB jobs alongside
in-memory active ones. For readiness Tier 1, the relevant condition is
`pending/in_progress` status — after restart, an in-progress job either stays
`in_progress` in DB (orphaned) or is eventually reaped. An orphaned job in DB with
`in_progress` status WOULD make Tier 1 = false (active import exists). This is
CONSERVATIVE: the user sees "still importing" which is wrong but safe (never shows
partial data). The existing orphan reaper (`cleanup_orphaned_jobs()` at startup) handles
this. For the readiness endpoint, checking the in-memory registry is sufficient for the
hot path; the DB check for orphaned jobs is optional complexity.

---

## Open Questions

1. **Should `GET /imports/readiness` also check DB for orphaned in-progress jobs?**
   - What we know: `find_active_jobs_for_user` only scans the in-memory registry.
   - What's unclear: After a backend restart, an orphaned `in_progress` DB job could
     leave the user stuck with `tier1=false` until the orphan reaper runs.
   - Recommendation: For Phase 96, use only the in-memory registry (consistent with
     current behavior). Note the limitation in the endpoint docstring. A follow-up
     phase already deferred this (OOM recurrence notes in CLAUDE.md).

2. **Should the `EvalCoverageHeader` stop once `tier2=true`?**
   - What we know: `EvalCoverageHeader` returns `null` when `isPending=false`
     (pct_complete=100). This is unchanged.
   - What's unclear: Whether the header should also suppress before evals start
     (0% complete = 100% pending = `isPending=true`, which shows the bar even with 0
     games analyzed). This is existing behavior, unchanged by this phase.
   - Recommendation: Leave `EvalCoverageHeader` logic unchanged; only the auto-reload
     effect in `useEvalCoverage` is removed.

---

## Environment Availability

Step 2.6: This phase is code/config-only changes — no new external dependencies.

---

## Sources

### Primary (HIGH confidence)
- `app/services/eval_drain.py` lines 552-568 — Stage B `asyncio.create_task` exact location confirmed
- `app/models/user_benchmark_percentile.py` lines 122-126 — `computed_at` column confirmed present, server-default
- `app/repositories/user_benchmark_percentiles_repository.py` lines 62-124 — `upsert_percentile` writes `computed_at` on every upsert/update
- `app/repositories/game_repository.py` lines 93-164 — `users_with_zero_pending` Plan 13 gate confirmed
- `app/services/user_benchmark_percentiles_service.py` lines 325-471 — Stage A/B single-commit pattern confirmed
- `app/routers/imports.py` lines 129-147 — eval-coverage endpoint D-01/D-04 contract confirmed
- `frontend/src/hooks/useEvalCoverage.ts` lines 49-65 — exact auto-reload code to retire
- `frontend/src/App.tsx` lines 40-42, 453-471 — `profileHasCompletedImport` + `ImportRequiredRoute` confirmed
- `frontend/src/components/stats/OpeningStatsCard.tsx` lines 1-245 — exact eval-row seam for Cpu-placeholder confirmed
- `frontend/src/components/insights/EvalConfidenceTooltip.tsx` lines 56-60, 114-128 — exact counter props to remove

### Secondary (MEDIUM confidence)
- `.planning/notes/import-readiness-gate.md` — canonical spec, authoritative design contract
- `.planning/phases/96-import-readiness-gate/96-CONTEXT.md` — locked decisions D-01/D-02

---

## Metadata

**Confidence breakdown:**
- Tier-2 signal: HIGH — code read confirms `computed_at` exists, single-commit Stage B, race window anatomy
- Endpoint shape: HIGH — project precedent (D-01/D-04 docstring), requirements fully known from code
- Locked-route UX: HIGH — existing `ImportRequiredRoute` pattern is the template; Endgames in-place is the minimal extension
- Openings eval seams: HIGH — exact line numbers confirmed in `OpeningStatsCard`
- Knip impact: MEDIUM — requires running to confirm; two known prop surfaces removed

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable codebase; this is a UX phase with no upstream dependencies)
