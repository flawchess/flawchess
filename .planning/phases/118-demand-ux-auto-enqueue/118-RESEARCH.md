# Phase 118: Demand UX + Auto-Enqueue — Research

**Researched:** 2026-06-14
**Domain:** Auto-enqueue triggers + analysis UX on top of the Phase 117 priority queue
**Confidence:** HIGH (all findings verified against actual codebase; no greenfield guesswork)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Auto-enqueue triggers & window (QUEUE-04)
- **D-118-01**: Two triggers, both backend-only. (a) Import completion enqueues the user's tier-2 window. (b) The window enqueue is hooked into `last_activity` middleware write (`app/middleware/last_activity.py`), throttled ≤1/hr per authenticated user. Rejected: frontend lazy trigger; standalone periodic sweep.
- **D-118-02**: Window = 200 most recent unanalyzed games. Single named constant so prod can retune without an API/schema change.
- **D-118-03**: Tier-2 window targets only `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`. Lichess games with imported %evals are NOT enqueued in tier-2.
- **D-118-04**: `_claim_tier3_derived` ORDER BY refinements: (1) active-users-first via `users.last_activity DESC`; (2) needs-eval before PV-backfill-only via `lichess_evals_at IS NOT NULL` pushed last, behind the existing TC-weight + recency terms.
- Enqueue is idempotent: skip games already pending/leased/completed.

#### Analyze affordances (EVUX-01)
- **D-118-05**: Ship BOTH affordances. Per-game tier-1 "Analyze this game" AND bulk "Analyze more" tier-2 button.
- **D-118-06**: Bulk "Analyze more" = next-chunk, disabled-until-drained. Enqueues next ~200 needs-eval games (D-118-03 predicate). Disabled while user has any tier-2 job in-flight (pending/leased). Re-enabled when tier-2 drains. Repeatable.
- **D-118-07**: Lichess-eval games (`lichess_evals_at IS NOT NULL`, hence `is_analyzed`) show NO "Analyze this game" button. Best_move/PV backfilled in background via tier-3. Per-game button visibility: guest → sign-up CTA (D-118-13); else not-`is_analyzed` → "Analyze this game" (tier-1); else (analyzed, incl. lichess-eval) → no affordance.
- Progress reuses `useEvalCoverage` polling — no new analysis-job entity/table.

#### Coverage indicators (EVUX-02)
- **D-118-08**: Scope = Library flaw surfaces only. Upgrade: FlawDenominatorPill, FlawComparisonGrid, NoAnalysisState pill, NoEngineAnalysisFlawsState. Replace `analysisCoverageCopy.tsx` "partial / coming soon" with real "N of M analyzed" + CTA. Endgames/Openings/GlobalStats gates untouched.
- **D-118-09**: Low-coverage CTA threshold = named constant `LOW_COVERAGE_THRESHOLD`, default ~80%.
- **D-118-10**: Single coverage notion = `is_analyzed` (`white_blunders IS NOT NULL`). Planner must verify `count_pending_evals` alignment (see Critical Finding below).

#### In-flight status (EVUX-03)
- **D-118-11**: Aggregate + per-game-tier-1 granularity. "N of M analyzed · K in progress" on coverage badge (polled); localized "Analyzing…" on the specific game the user tier-1-clicked.
- **D-118-12**: Extend `/imports/eval-coverage` with in-flight (queued/leased) counts. One polled call drives coverage %, bulk-button disabled-state, and in-flight status.

#### Guest experience (ROADMAP criterion 5 / QUEUE-08)
- **D-118-13**: Swap CTA for sign-up prompt in the same slots where users see "Analyze more" / "Analyze this game". Never silently no-op buttons.

### Claude's Discretion
- Exact `LOW_COVERAGE_THRESHOLD` and tier-2 window-size constant values (start ~80% / 200).
- Polling cadence for `useEvalCoverage` (reuse the import-status interval pattern).
- The user-facing tier-1 endpoint shape: auth, guest-exclusion, optional rate-limit. Router stays thin.
- Exact SQL for the "user has tier-2 in-flight" check and any supporting index.
- Whether the bulk-button "N of M" label reuses aggregate coverage numbers or a tier-2-window-scoped subset.
- New reusable analyze-upsell component vs inlining the Endgames pattern.

### Deferred Ideas (OUT OF SCOPE)
- Engine-best-move step-through display / board-arrow viewer.
- Separate PV/best_move coverage indicator (lands with SEED-039).
- Filter-scoped analysis batch.
- Endgames/Openings/GlobalStats coverage-messaging redo.
- Per-card in-flight spinners across the whole archive.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUEUE-04 | Import completion and user activity automatically enqueue the user's ~200 most recent unanalyzed games (tier 2) | `enqueue_tier2_window` function to add to `eval_queue_service.py`; hook points in `_complete_import_job` (import_service.py:485) and `LastActivityMiddleware.__call__` (middleware/last_activity.py:77-89) |
| EVUX-01 | User can trigger "analyze more games" explicitly and see progress | New `POST /imports/eval/tier1/{game_id}` endpoint + new `POST /imports/eval/tier2` endpoint; extend `useEvalCoverage` hook with polling; `FlawCard` + `LibraryGameCard` NoAnalysisState slot for tier-1 button |
| EVUX-02 | User can see their analysis coverage (% of games analyzed / N of M) on eval-dependent surfaces, with a CTA when coverage is low | Replace `analysisCoverageCopy.tsx`; extend `EvalCoverageResponse` with `analyzed_count`/`in_flight_count`; new `count_is_analyzed` repository function (see Critical Finding) |
| EVUX-03 | User sees in-flight analysis state (queued/analyzing) for their games without refreshing blindly | Extend `/imports/eval-coverage` response; `useEvalCoverage` hook re-exposes `inFlightCount`; `FlawDenominatorPill` reads it |
</phase_requirements>

---

## Summary

Phase 118 is a pure extension phase. Phases 116/117 built the engine, priority queue, `eval_jobs` table, lease/report contract, and `enqueue_tier1_game`. Phase 118 adds (a) two automatic backend triggers that call a new `enqueue_tier2_window` service function, (b) user-facing "Analyze" affordances on Library flaw surfaces and per-game in the LibraryGameCard modal, (c) real coverage numbers ("N of M analyzed") replacing the stale "coming soon" copy, and (d) in-flight status via an extended `/imports/eval-coverage` response.

The research found one critical correctness gap in the existing codebase: `count_pending_evals` in `game_repository.py` counts games with `evals_completed_at IS NULL` (the **entry-ply** cold-drain marker), which is **different** from `is_analyzed` (`white_blunders IS NOT NULL`). The `get_eval_coverage` endpoint calls this function, meaning the existing eval-coverage percentage counts entry-ply eval completion, not flaw-analysis readiness. D-118-10 requires coverage = `is_analyzed`, so a new repository function and extension to the endpoint response are both needed.

A second finding: `enqueue_tier2_window` does not exist yet in `eval_queue_service.py`. It must be added before the two hook sites (import completion, last_activity middleware) can call it.

**Primary recommendation:** Add `enqueue_tier2_window(user_id)` to `eval_queue_service.py` first (the shared dependency of both trigger sites), then wire the two triggers, then extend the eval-coverage endpoint, then update the frontend hook and components in sequence.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auto-enqueue on import completion | API / Backend | — | `_complete_import_job` already owns the post-import hook (compute_stage_a, compute_stage_b); tier-2 enqueue is the same pattern |
| Auto-enqueue on user activity | API / Backend | — | `LastActivityMiddleware` runs after each request; already throttled to ≤1/hr; no frontend coupling needed |
| Tier-1 user-facing endpoint | API / Backend | — | Auth required, IDOR guard, guest exclusion all live in backend; router stays thin |
| Tier-2 user-facing endpoint | API / Backend | — | Same as tier-1; checks "tier-2 in-flight" via eval_jobs count |
| Coverage indicator data | API / Backend | — | `is_analyzed` count + in-flight count from DB; one extended `/imports/eval-coverage` response |
| In-flight count | API / Backend | — | COUNT over eval_jobs WHERE user_id + tier=2 + status IN ('pending','leased') |
| Coverage badge / CTA | Frontend / Browser | — | FlawDenominatorPill reads `useEvalCoverage`; no SSR needed |
| Analyze buttons | Frontend / Browser | — | LibraryGameCard + NoAnalysisState; trigger via TanStack mutation |
| Guest promotion CTA | Frontend / Browser | — | Same slot, `useUserProfile().is_guest` gates which copy shows |
| Polling | Frontend / Browser | — | `useEvalCoverage` refetchInterval pattern; existing 3-second constant |

---

## Standard Stack

No new dependencies. All work is within the existing stack.

### Core (already installed)
| Library | Purpose | Note |
|---------|---------|------|
| FastAPI 0.13x | New endpoints (`/imports/eval/tier1/{game_id}`, `/imports/eval/tier2`) | Existing router |
| SQLAlchemy 2.x async | `enqueue_tier2_window` service function; new `count_is_analyzed` repo function; in-flight count query | Existing patterns |
| TanStack Query | `useMutation` for tier-1/tier-2 triggers; extended `useEvalCoverage` | Existing hook |
| Pydantic v2 | Extended `EvalCoverageResponse` schema | Existing schema file |

### Package Legitimacy Audit

No new packages. This section is not applicable — Phase 118 installs zero external dependencies.

---

## Architecture Patterns

### System Architecture Diagram

```
User activity (any authenticated request)
    → LastActivityMiddleware.__call__
        → [throttle: ≤1/hr per user_id in _last_updated cache]
        → enqueue_tier2_window(user_id)   [NEW]
            → INSERT eval_jobs (tier=2) ON CONFLICT DO NOTHING
              WHERE games: full_evals_completed_at IS NULL AND lichess_evals_at IS NULL
              ORDER BY played_at DESC LIMIT TIER2_WINDOW_SIZE (200)

Import completion
    → import_service._complete_import_job(job, job_id)
        → [existing: compute_stage_a, compute_stage_b]
        → asyncio.create_task(enqueue_tier2_window(job.user_id))   [NEW, fire-and-forget]

User clicks "Analyze this game" [NEW user-facing tier-1]
    → POST /imports/eval/tier1/{game_id}
        → current_active_user (auth dependency)
        → IDOR: verify game.user_id == user.id (404 otherwise)
        → enqueue_tier1_game(game_id, user_id)   [EXISTING — guest no-op built in]
        → return {"status": "enqueued"|"already_queued"|"skipped_guest"}

User clicks "Analyze more" [NEW user-facing tier-2]
    → POST /imports/eval/tier2
        → current_active_user
        → check: has_tier2_in_flight(user_id) → 409 Conflict if in-flight
        → enqueue_tier2_window(user_id)
        → return {"status": "enqueued"|"in_flight"|"skipped_guest"}

Polling: GET /imports/eval-coverage   [EXTENDED]
    → count_is_analyzed_games(user_id)   [NEW repo fn: white_blunders IS NOT NULL]
    → count_in_flight(user_id)           [NEW repo fn: eval_jobs WHERE pending|leased]
    → EvalCoverageResponse {
          pending_count,   [kept for backward compat — Endgames/Openings/GlobalStats use it]
          total_count,
          pct_complete,
          analyzed_count,   [NEW: games where is_analyzed = True]
          in_flight_count   [NEW: eval_jobs pending+leased for this user]
      }

Frontend: useEvalCoverage [EXTENDED]
    → exposes: pendingCount, totalCount, pct, analyzedCount, inFlightCount, isPending
    → poll stops when: pct_complete=100 AND total_count>0 AND in_flight_count=0

FlawDenominatorPill [EXTENDED]
    → "124 of 400 Games analyzed · 12 in progress" when in_flight_count > 0
    → CTA button when analyzedCount/totalCount < LOW_COVERAGE_THRESHOLD (0.80)

NoAnalysisState [EXTENDED]
    → guest: "Sign up to unlock analysis" (links /login?tab=register)
    → not is_analyzed + not in_flight: "Analyze this game" button → useTier1Enqueue mutation
    → not is_analyzed + in_flight (this game's user): "Analyzing…" pulse
    → is_analyzed: no affordance shown

NoEngineAnalysisFlawsState [REPLACED]
    → guest: "Sign up to unlock full-game analysis"
    → non-guest with no analyzed games: "Analyze your games" bulk CTA → useTier2Enqueue mutation
```

### Recommended Project Structure (additions only)

```
app/
├── routers/
│   └── imports.py           # Add POST /eval/tier1/{game_id} + POST /eval/tier2
├── repositories/
│   └── game_repository.py   # Add count_is_analyzed_games(), count_in_flight_evals()
├── services/
│   └── eval_queue_service.py  # Add enqueue_tier2_window(user_id)
└── schemas/
    └── imports.py           # Extend EvalCoverageResponse with analyzed_count, in_flight_count

frontend/src/
├── hooks/
│   ├── useEvalCoverage.ts   # Extend return shape: analyzedCount, inFlightCount
│   └── useEnqueueGame.ts    # NEW: useTier1Enqueue(gameId), useTier2Enqueue()
├── types/
│   └── api.ts               # Extend EvalCoverageResponse
└── components/library/
    ├── analysisCoverageCopy.tsx   # REPLACE stale copy with real dynamic copy
    ├── NoAnalysisState.tsx        # Add tier-1 button / guest CTA / in-flight state
    ├── NoEngineAnalysisFlawsState.tsx  # Replace with bulk CTA / guest CTA
    └── FlawDenominatorPill.tsx    # (in FlawStatsPanel.tsx) Add in-flight badge + CTA
```

### Pattern 1: `enqueue_tier2_window` service function

```python
# Source: extends eval_queue_service.py — mirrors enqueue_tier1_game pattern

TIER2_WINDOW_SIZE: int = 200  # D-118-02: tunable constant

async def enqueue_tier2_window(user_id: int) -> int:
    """Insert tier-2 eval_jobs for the user's ~200 most recent needs-eval games.

    D-118-03: targets full_evals_completed_at IS NULL AND lichess_evals_at IS NULL.
    Idempotent: ON CONFLICT DO NOTHING on uq_eval_jobs_game_active (status IN
    ('pending','leased')). QUEUE-08: skips guest users (no-op).

    Returns count of newly inserted rows.
    """
    async with async_session_maker() as session:
        # Guest guard (QUEUE-08)
        user_result = await session.execute(select(User.is_guest).where(User.id == user_id))
        is_guest = user_result.scalar_one_or_none()
        if is_guest is None or is_guest:
            return 0

        # Select the window of games needing full eval (D-118-03 predicate).
        # Game.needs_engine_full_evals == full_evals_completed_at IS NULL AND lichess_evals_at IS NULL.
        subq = (
            select(Game.id)
            .where(
                Game.user_id == user_id,
                Game.needs_engine_full_evals,
            )
            .order_by(Game.played_at.desc().nullslast())
            .limit(TIER2_WINDOW_SIZE)
            .subquery()
        )
        game_ids_result = await session.execute(select(subq))
        game_ids = [row[0] for row in game_ids_result.fetchall()]

        if not game_ids:
            return 0

        # Bulk insert with ON CONFLICT DO NOTHING
        rows = [
            {"tier": TIER_AUTO_WINDOW, "user_id": user_id, "game_id": gid, "status": "pending"}
            for gid in game_ids
        ]
        stmt = (
            pg_insert(EvalJob)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=["game_id"],
                index_where=sa.text("status IN ('pending', 'leased')"),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0
```

### Pattern 2: Hook into `LastActivityMiddleware`

```python
# Source: app/middleware/last_activity.py — extend the try block at line 77-89
# [ASSUMED] — exact line numbers verified but integration approach is new code

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

            # D-118-01: auto-enqueue tier-2 window on activity (fire-and-forget)
            # Runs AFTER the last_activity write so users.last_activity is current
            # for the D-118-04 ordering refinement. asyncio.create_task is safe here
            # because LastActivityMiddleware runs after self.app() returns (the
            # request response is already sent), so task failure can't corrupt the
            # response. The throttle above ensures at most 1 enqueue/hr/user.
            import asyncio
            from app.services.eval_queue_service import enqueue_tier2_window
            asyncio.create_task(enqueue_tier2_window(user_id))

        except Exception:
            logger.debug("Failed to update last_activity for user %s", user_id, exc_info=True)
```

### Pattern 3: Hook into `_complete_import_job`

```python
# Source: app/services/import_service.py — extend _complete_import_job (line 485)
# After the existing compute_stage_b block (line 527+)

    # D-118-01: auto-enqueue tier-2 window on import completion (fire-and-forget)
    # Fires unconditionally — even for 0-new-games syncs, which confirms we're
    # caught up and may promote older unanalyzed games into the tier-2 window.
    asyncio.create_task(enqueue_tier2_window(job.user_id))
```

### Pattern 4: User-facing tier-1 endpoint

```python
# Source: app/routers/imports.py — new endpoint in the existing router

@router.post("/eval/tier1/{game_id}", response_model=EnqueueTier1Response)
async def enqueue_tier1(
    game_id: int,
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnqueueTier1Response:
    """Tier-1 explicit request: 'Analyze this game' (QUEUE-03, EVUX-01).

    IDOR guard: verifies game.user_id == user.id (404 if not owned or not found).
    QUEUE-08: enqueue_tier1_game returns False for guests (no-op).
    D-118-07: caller is responsible for not showing this button for is_analyzed games.
    No rate-limit added (D: Claude's Discretion — the 1M-node search is per-game,
    pool-shared, and the existing SKIP LOCKED prevents duplicate active jobs).
    """
    game = await session.get(Game, game_id)
    if game is None or game.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")

    inserted = await enqueue_tier1_game(game_id=game_id, user_id=user.id)
    # [reuse EnqueueTier1Response from admin.py / move to imports schema]
    ...
```

### Pattern 5: User-facing tier-2 endpoint

```python
@router.post("/eval/tier2", response_model=EnqueueTier2Response)
async def enqueue_tier2(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnqueueTier2Response:
    """Tier-2 bulk request: 'Analyze more' (EVUX-01, D-118-06).

    Disabled-until-drained: returns 'in_flight' if the user already has any
    tier-2 job with status pending|leased.
    QUEUE-08: enqueue_tier2_window returns 0 for guests.
    """
    if user.is_guest:
        return EnqueueTier2Response(status="skipped_guest", enqueued_count=0)
    in_flight = await game_repository.count_tier2_in_flight(session, user.id)
    if in_flight > 0:
        return EnqueueTier2Response(status="in_flight", enqueued_count=0)
    count = await enqueue_tier2_window(user.id)
    return EnqueueTier2Response(
        status="enqueued" if count > 0 else "nothing_to_enqueue",
        enqueued_count=count,
    )
```

### Pattern 6: Extended `EvalCoverageResponse` + new repository functions

```python
# app/schemas/imports.py — extend EvalCoverageResponse
class EvalCoverageResponse(BaseModel):
    pending_count: int      # kept: evals_completed_at IS NULL (entry-ply — used by readiness)
    total_count: int
    pct_complete: int       # kept: backward compat with Endgames/Openings/GlobalStats gates

    # NEW (D-118-10, D-118-12):
    analyzed_count: int     # white_blunders IS NOT NULL (is_analyzed — the flaw-surface denominator)
    in_flight_count: int    # eval_jobs WHERE user_id + status IN ('pending','leased')

# app/repositories/game_repository.py — new functions
async def count_is_analyzed_games(session: AsyncSession, user_id: int) -> int:
    """Count games where white_blunders IS NOT NULL (is_analyzed = True, D-118-10)."""
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.is_analyzed)
    )
    return result.scalar_one()

async def count_tier2_in_flight(session: AsyncSession, user_id: int) -> int:
    """Count pending/leased tier-2 eval_jobs for this user (D-118-06 disabled-state)."""
    from app.models.eval_jobs import EvalJob, TIER_AUTO_WINDOW
    result = await session.execute(
        select(func.count())
        .select_from(EvalJob)
        .where(
            EvalJob.user_id == user_id,
            EvalJob.tier == TIER_AUTO_WINDOW,
            EvalJob.status.in_(["pending", "leased"]),
        )
    )
    return result.scalar_one()

async def count_in_flight_evals(session: AsyncSession, user_id: int) -> int:
    """Count ALL pending/leased eval_jobs for this user (D-118-12 in-flight badge)."""
    from app.models.eval_jobs import EvalJob
    result = await session.execute(
        select(func.count())
        .select_from(EvalJob)
        .where(
            EvalJob.user_id == user_id,
            EvalJob.status.in_(["pending", "leased"]),
        )
    )
    return result.scalar_one()
```

### Pattern 7: Frontend `useEvalCoverage` extension

```typescript
// frontend/src/hooks/useEvalCoverage.ts — extend return shape
// Current EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000 (already defined, reuse)

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
      // Stop polling only when both evals and in-flight are drained AND we have games
      if (data && data.pct_complete === 100 && data.total_count > 0 && data.in_flight_count === 0)
        return false;
      return EVAL_COVERAGE_POLL_INTERVAL_MS;
    },
  });

  const data = query.data;
  const isPending = (data?.pct_complete ?? 100) < 100;
  const inFlightCount = data?.in_flight_count ?? 0;
  const analyzedCount = data?.analyzed_count ?? 0;

  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    analyzedCount,      // NEW
    inFlightCount,      // NEW
    isPending,
    isLoading: query.isLoading,
  };
}
```

### Pattern 8: Guest CTA — the established `useUserProfile` pattern

```typescript
// Pattern from frontend/src/pages/Import.tsx lines 292-308
// profile is from useUserProfile(), is_guest is in UserProfile type

const { data: profile } = useUserProfile();
if (profile?.is_guest) {
  // render "Sign up to unlock full-game analysis" CTA
  // navigate to /login?tab=register (mirroring Import page's logoutForPromotion pattern)
}
```

### Anti-Patterns to Avoid

- **Calling `enqueue_tier2_window` inside the LastActivityMiddleware's existing `async with` session block**: The middleware opens its session for the `sa_update(User)` write; opening a SECOND session inside that block would create a second connection. Instead, fire-and-forget via `asyncio.create_task` AFTER the existing `async with` block closes.
- **Using `asyncio.gather` on the same `AsyncSession`**: CLAUDE.md hard rule. Never pass one session to two concurrent queries. Each `count_*` call in the extended `get_eval_coverage` endpoint must be sequential on the same session.
- **Registering `enqueue_tier2_window` as a top-level import at module load**: Import inside the function or use a local import to avoid circular imports (middleware → service → database).
- **Counting `evals_completed_at IS NULL` as "not analyzed"**: This is the entry-ply marker (used by `count_pending_evals`), not the flaw-analysis marker. For the coverage badge, use `white_blunders IS NULL` (`NOT is_analyzed`).
- **Adding an in-flight index scan without the partial index**: A full table scan over `eval_jobs` for in-flight counts per user at 3-second polling intervals would be expensive. The existing `ix_eval_jobs_pick` covers `(tier, user_id, created_at) WHERE status = 'pending'`. A new partial index on `(user_id) WHERE status IN ('pending', 'leased')` is needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Bulk insert with conflict-skip | Custom loop | `pg_insert(...).on_conflict_do_nothing(index_elements=["game_id"], index_where=sa.text("status IN ('pending', 'leased')"))`  — same pattern as `enqueue_tier1_game` |
| Idempotent tier-2 enqueue | Track inserted IDs | `uq_eval_jobs_game_active` partial unique index already enforces one active job per game |
| Auth + IDOR on tier-1 endpoint | Custom JWT parse | `Depends(current_active_user)` + `game.user_id != user.id → 404` pattern from `app/routers/library.py:111-126` |
| Guest detection in frontend | Custom token decode | `useUserProfile().data?.is_guest` — `UserProfile` type has `is_guest: boolean` |
| Polling stop condition | Custom interval manager | TanStack Query `refetchInterval` callback returning `false` — existing pattern in `useEvalCoverage` and `useReadiness` |
| In-flight count | WebSocket / SSE | Simple polled COUNT query on `eval_jobs`; acceptable latency at 3s interval |

---

## Critical Finding: `count_pending_evals` Does NOT Align with `is_analyzed`

**This is a correctness gate (D-118-10).**

`app/repositories/game_repository.py:85-92`:
```python
async def count_pending_evals(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.evals_completed_at.is_(None))
    )
    return result.scalar_one()
```

This counts games where `evals_completed_at IS NULL` — the **entry-ply cold drain** completion marker. A game can have `evals_completed_at IS NOT NULL` (entry-ply done, endgame stats ready) but STILL be `white_blunders IS NULL` (`is_analyzed = False`) if full-game analysis hasn't run yet.

The current `GET /imports/eval-coverage` calls this function, so `pending_count` and `pct_complete` currently measure entry-ply coverage, NOT flaw-analysis coverage. This was correct for the readiness gate (Endgames/Openings use it to know when endgame stats are ready), but it is WRONG for the D-118-08/D-118-10 flaw-surface coverage badge.

**Resolution:** Add a new `count_is_analyzed_games(session, user_id)` function using `Game.is_analyzed` (`white_blunders IS NOT NULL`) and expose it as `analyzed_count` in the extended response. Keep the existing `pending_count`/`pct_complete` keys unchanged (backward-compatible; the readiness-gate consumers — Endgames/Openings/GlobalStats — still need entry-ply coverage, not flaw coverage).

---

## Common Pitfalls

### Pitfall 1: Circular import in LastActivityMiddleware
**What goes wrong:** `from app.services.eval_queue_service import enqueue_tier2_window` at the top of `last_activity.py` triggers a circular import chain: middleware → eval_queue_service → database → ... → middleware.
**Why it happens:** `last_activity.py` is loaded early in the ASGI middleware stack; service modules that import `async_session_maker` from `app.core.database` are also loaded early.
**How to avoid:** Use a local import inside the `try` block where the call happens. The import is cached after the first call, so performance impact is negligible.

### Pitfall 2: asyncio.create_task outside a running event loop
**What goes wrong:** `asyncio.create_task(enqueue_tier2_window(user_id))` will raise `RuntimeError: no running event loop` if called from a non-async context.
**Why it happens:** The `LastActivityMiddleware.__call__` method is async (it `await`s `self.app()`), so `asyncio.create_task` is always safe there. But if the function is called from a sync context (e.g., a test helper), it breaks.
**How to avoid:** The middleware `__call__` is already `async`. No issue in production. In tests, mock `asyncio.create_task` or await `enqueue_tier2_window` directly.

### Pitfall 3: SKIP LOCKED race in `_claim_tier3_derived`
**What goes wrong:** Two concurrent workers can claim the same tier-3 game (no locking). The Phase 117 code notes this at line 195: "duplicate work is idempotent but wastes engine calls."
**Why it happens:** The tier-3 pick is a plain SELECT with no `FOR UPDATE SKIP LOCKED`.
**How to avoid:** Phase 118's D-118-04 only adds ORDER BY clauses to this query — don't introduce locking changes (that's a future phase concern per the existing comment). The idempotency of flaw classification (`ON CONFLICT DO NOTHING`) protects correctness.

### Pitfall 4: N+1 queries in the extended `/imports/eval-coverage`
**What goes wrong:** Adding `count_is_analyzed_games` and `count_in_flight_evals` to the endpoint naively creates three sequential DB round-trips per poll at 3-second intervals.
**Why it happens:** Each new `count_*` function opens an implicit read within the same session.
**How to avoid:** Keep all three counts on the same session object (one connection). CLAUDE.md forbids `asyncio.gather` on the same session, but sequential execution on one session is fine — three lightweight COUNT queries on an indexed table are fast. Alternatively, combine into a single SQL query with multiple aggregates (optional optimization, not required for correctness).

### Pitfall 5: The bulk "Analyze more" button showing when tier-2 is in-flight
**What goes wrong:** User clicks "Analyze more", button stays enabled on next render, user clicks again — results in a harmless no-op (the endpoint returns `in_flight`) but confusing UX.
**Why it happens:** The disabled-state check depends on `useEvalCoverage` polling which lags by up to 3 seconds.
**How to avoid:** On mutation success (from `useTier2Enqueue`), immediately invalidate the `['imports', 'eval-coverage']` query key via `queryClient.invalidateQueries`. The poll refetches immediately, reflecting the new in-flight count, and the button disables reactively within one render cycle.

### Pitfall 6: `enqueue_tier2_window` inserting rows for already-completed games
**What goes wrong:** The `ON CONFLICT DO NOTHING` on `uq_eval_jobs_game_active` only blocks conflicts for `status IN ('pending','leased')`. A game with a COMPLETED `eval_jobs` row can be re-inserted. The window predicate `full_evals_completed_at IS NULL` catches this case correctly — if a game was analyzed via the queue, its `full_evals_completed_at` will be set, so it won't appear in the window. No extra check needed.
**Why it doesn't happen in practice:** The D-118-03 predicate (`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`) is the exact condition for "genuinely needs analysis." Games that completed the drain have `full_evals_completed_at IS NOT NULL` and are naturally excluded.

### Pitfall 7: In-flight count index missing
**What goes wrong:** `count_in_flight_evals` and `count_tier2_in_flight` scan `eval_jobs` with `status IN ('pending', 'leased')`. At 3-second polling intervals with potentially thousands of eval_jobs rows, a missing index causes per-query full scans.
**Why it happens:** The existing `ix_eval_jobs_pick` partial index only covers `status = 'pending'`. The lease-expiry index `ix_eval_jobs_leased` covers `status = 'leased'`. Neither covers combined `pending|leased` by `user_id`.
**How to avoid:** Add a migration with a partial index: `CREATE INDEX ix_eval_jobs_user_active ON eval_jobs (user_id) WHERE status IN ('pending', 'leased')`. This index is small at steady state (completed jobs are excluded), fast to create, and makes the in-flight count O(log n).

---

## Runtime State Inventory

Not applicable. Phase 118 is a feature-addition phase, not a rename/refactor/migration phase. No stored data, live service config, OS-registered state, secrets, or build artifacts need renaming.

---

## Code Examples

### Exact verified signatures and shapes

**`enqueue_tier1_game` (existing — to be called from new user-facing endpoint):**
```python
# [VERIFIED: app/services/eval_queue_service.py:314-359]
async def enqueue_tier1_game(game_id: int, user_id: int) -> bool:
    # Returns True if inserted, False for guest or already-queued.
    # ON CONFLICT DO NOTHING on uq_eval_jobs_game_active (game_id WHERE status IN ('pending','leased'))
```

**`EvalCoverageResponse` (existing — to extend):**
```python
# [VERIFIED: app/schemas/imports.py:47-53]
class EvalCoverageResponse(BaseModel):
    pending_count: int   # evals_completed_at IS NULL count
    total_count: int
    pct_complete: int    # 0-100, rounded
    # TO ADD: analyzed_count: int  # white_blunders IS NOT NULL count
    # TO ADD: in_flight_count: int # eval_jobs pending|leased for this user
```

**`EvalCoverageResponse` TypeScript type (existing — to extend):**
```typescript
// [VERIFIED: frontend/src/types/api.ts:192-196]
export interface EvalCoverageResponse {
  pending_count: number;
  total_count: number;
  pct_complete: number;  // 0-100, rounded
  // TO ADD: analyzed_count: number;
  // TO ADD: in_flight_count: number;
}
```

**`useEvalCoverage` current poll interval:**
```typescript
// [VERIFIED: frontend/src/hooks/useEvalCoverage.ts:5-6]
const EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000;
const EVAL_COVERAGE_STALE_TIME_MS = 3_000;
// AnalysisUX polling reuses this same constant (D: Claude's Discretion)
```

**`analysisCoverageCopy.tsx` (to replace):**
```typescript
// [VERIFIED: frontend/src/components/library/analysisCoverageCopy.tsx:11-14]
// Three consumers: NoAnalysisState, NoEngineAnalysisFlawsState, FlawDenominatorPill
// The ANALYSIS_COVERAGE_PARAGRAPHS array and ANALYSIS_COVERAGE_COPY JSX are both stale.
// Phase 118 replaces with real "N of M analyzed" copy driven by useEvalCoverage.
```

**`is_analyzed` hybrid property:**
```python
# [VERIFIED: app/models/game.py:181-199]
@hybrid_property
def is_analyzed(self) -> bool:
    return self.white_blunders is not None

@is_analyzed.inplace.expression
@classmethod
def _is_analyzed_expression(cls) -> sa.ColumnElement[bool]:
    return cls.white_blunders.isnot(None)
# Safe to use in SQLAlchemy select() expressions as Game.is_analyzed
```

**`EvalJob` tier/status constants:**
```python
# [VERIFIED: app/models/eval_jobs.py:14-16]
TIER_EXPLICIT: int = 1
TIER_AUTO_WINDOW: int = 2
TIER_IDLE_BACKLOG: int = 3
# Status varchar(20): "pending" | "leased" | "completed" | "failed"
```

**`_claim_tier3_derived` current ORDER BY (to extend per D-118-04):**
```python
# [VERIFIED: app/services/eval_queue_service.py:196-218]
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
# D-118-04 adds BEFORE these terms:
# 1. User.last_activity.desc().nullslast()  → active-users-first
# D-118-04 adds AFTER the TC-weight + recency terms (pushes PV-backfill-only games last):
# 2. Game.lichess_evals_at.isnot(None).asc()  → needs-eval first (False=0 before True=1)
```

**`FlawDenominatorPill` (existing — to extend):**
```typescript
// [VERIFIED: frontend/src/components/library/FlawStatsPanel.tsx:27-43]
// Currently: analyzedN, totalN props + ANALYSIS_COVERAGE_COPY popover.
// D-118-08/D-118-11: add inFlightCount prop + optional CTA when coverage < threshold.
```

**`NoAnalysisState` (existing — to extend):**
```typescript
// [VERIFIED: frontend/src/components/library/NoAnalysisState.tsx:19-37]
// Currently: Cpu icon + "No Analysis" label + ANALYSIS_COVERAGE_COPY popover.
// D-118-07/D-118-11/D-118-13: replace with branching:
//   guest        → "Sign up to unlock analysis" CTA
//   not analyzed → "Analyze this game" button (tier-1 mutation trigger)
//   in-flight    → "Analyzing…" pulse (localized for this game)
//   analyzed     → no affordance shown (D-118-07: lichess-eval games excluded here by caller)
```

**`NoEngineAnalysisFlawsState` (existing — to replace):**
```typescript
// [VERIFIED: frontend/src/components/library/NoEngineAnalysisFlawsState.tsx]
// Currently: "Engine analysis coming soon" + ANALYSIS_COVERAGE_PARAGRAPHS
// D-118-08/D-118-13: replace with:
//   guest         → "Sign up to unlock full-game analysis" CTA
//   non-guest     → "Analyze your games" bulk CTA → useTier2Enqueue mutation
//                   "Analyzing your games… N of M" when tier-2 in-flight
```

**`_complete_import_job` hook site:**
```python
# [VERIFIED: app/services/import_service.py:485-537]
# Current last line of the function body (after the compute_stage_b block):
asyncio.create_task(compute_stage_b(job.user_id))
# After this block (line ~537+), add:
# asyncio.create_task(enqueue_tier2_window(job.user_id))
```

**`LastActivityMiddleware` hook site:**
```python
# [VERIFIED: app/middleware/last_activity.py:77-89]
# After _last_updated[user_id] = now  (line 89), add:
# asyncio.create_task(enqueue_tier2_window(user_id))
# using a local import inside the try block to avoid circular imports.
```

**Guest `is_guest` field access pattern:**
```typescript
// [VERIFIED: frontend/src/types/users.ts:6, frontend/src/pages/Import.tsx:292]
// Pattern: const { data: profile } = useUserProfile();
//          if (profile?.is_guest) { ... }
// UserProfile interface has is_guest: boolean — no need for useAuth token decode.
```

**Admin tier-1 schema to reuse:**
```python
# [VERIFIED: app/schemas/admin.py:42-50]
class EnqueueTier1Response(BaseModel):
    status: Literal["enqueued", "skipped_guest", "already_queued"]
    game_id: int
# Move to app/schemas/imports.py or create a new EnqueueResponse in imports.py
# for the user-facing endpoints. Admin router can import from there.
```

---

## D-118-04 Tier-3 Ordering Refinement (Exact SQL Extension)

The `_claim_tier3_derived` ORDER BY must be extended in two places:

**Add BEFORE the existing TC-weight CASE (active-users-first):**
```python
User.last_activity.desc().nullslast(),
```

**Add AFTER the existing recency term (needs-eval before PV-backfill-only):**
```python
# lichess_evals_at IS NOT NULL games go LAST (they only need PV backfill, not evals)
# False (needs eval) < True (PV-only), so asc() puts needs-eval first.
Game.lichess_evals_at.isnot(None).asc(),
```

The final ORDER BY:
```python
.order_by(
    User.last_activity.desc().nullslast(),      # D-118-04 #1: active users first
    sa.case(
        (Game.time_control_bucket == "classical", 0),
        (Game.time_control_bucket == "rapid", 1),
        (Game.time_control_bucket == "blitz", 2),
        (Game.time_control_bucket == "bullet", 3),
        else_=4,
    ).asc(),
    Game.played_at.desc().nullslast(),
    Game.lichess_evals_at.isnot(None).asc(),   # D-118-04 #2: needs-eval before PV-only
)
```

Note: the `.join(User, Game.user_id == User.id)` is already in `_claim_tier3_derived` (for `NOT users.is_guest`), so `User.last_activity` is available without adding a new join.

---

## Endpoint Routing

The two new user-facing enqueue endpoints belong in `app/routers/imports.py` (already has the `prefix="/imports"` router), not in a new router or in `admin.py`. This follows the existing pattern where all import/eval-coverage routes live in the imports router.

- `POST /imports/eval/tier1/{game_id}` — user-facing tier-1
- `POST /imports/eval/tier2` — user-facing tier-2

The existing admin endpoint `POST /admin/eval/enqueue-tier1/{game_id}` remains unchanged and is used only for prod verification.

---

## Index Addition Required

Add to an Alembic migration alongside the code changes:

```sql
CREATE INDEX ix_eval_jobs_user_active
ON eval_jobs (user_id)
WHERE status IN ('pending', 'leased');
```

In SQLAlchemy model terms (for the migration autogenerate to pick up — or declare manually):
```python
Index(
    "ix_eval_jobs_user_active",
    "user_id",
    postgresql_where=sa.text("status IN ('pending', 'leased')"),
),
```

This index is used by both `count_tier2_in_flight` and `count_in_flight_evals`. At steady state it is small (only active jobs remain; completed/failed are excluded).

---

## State of the Art

| Old Approach | Current Approach | Impact for 118 |
|--------------|------------------|----------------|
| "Coming soon" coverage copy | Real N/M analyzed count | Replace `analysisCoverageCopy.tsx` entirely |
| No user-facing analyze trigger | Tier-1 per-game + Tier-2 bulk | New router endpoints + frontend mutations |
| Auto-analysis via tier-3 only (idle drain) | Tier-2 auto-window on import/activity | `enqueue_tier2_window` + two hook sites |
| In-flight status: none | Extended eval-coverage poll response | `in_flight_count` in response |
| `evals_completed_at` for coverage % | `is_analyzed` (`white_blunders IS NOT NULL`) | New `count_is_analyzed_games` repo fn |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio + pytest-xdist |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/services/test_eval_queue.py tests/routers/test_imports_eval_coverage.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUEUE-04 | `enqueue_tier2_window` inserts tier-2 rows for D-118-03 predicate games | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier2` | ❌ Wave 0 (extend existing) |
| QUEUE-04 | `enqueue_tier2_window` is idempotent (ON CONFLICT DO NOTHING) | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier2_idempotent` | ❌ Wave 0 |
| QUEUE-04 | Guest user: `enqueue_tier2_window` returns 0 | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier2_guest` | ❌ Wave 0 |
| QUEUE-04 | Lichess-eval games excluded from tier-2 window (D-118-03) | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier2_lichess_excluded` | ❌ Wave 0 |
| EVUX-01 | `POST /imports/eval/tier1/{game_id}` returns 200 for valid owned game | integration | `uv run pytest tests/routers/ -x -k test_tier1_enqueue` | ❌ Wave 0 |
| EVUX-01 | `POST /imports/eval/tier1/{game_id}` returns 404 for IDOR attempt | integration | `uv run pytest tests/routers/ -x -k test_tier1_idor` | ❌ Wave 0 |
| EVUX-01 | `POST /imports/eval/tier2` returns `in_flight` when tier-2 jobs exist | integration | `uv run pytest tests/routers/ -x -k test_tier2_in_flight` | ❌ Wave 0 |
| EVUX-02/03 | `GET /imports/eval-coverage` returns `analyzed_count` + `in_flight_count` | integration | `uv run pytest tests/routers/test_imports_eval_coverage.py -x` | ✅ (extend) |
| EVUX-02 | `analyzed_count` uses `is_analyzed` predicate, not `evals_completed_at` | integration | `uv run pytest tests/routers/test_imports_eval_coverage.py -x -k analyzed_count` | ❌ Wave 0 |
| D-118-04 | `_claim_tier3_derived` orders active users before inactive | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier3_ordering` | ❌ Wave 0 |
| D-118-04 | `_claim_tier3_derived` orders needs-eval before PV-backfill-only | unit | `uv run pytest tests/services/test_eval_queue.py -x -k tier3_pv_ordering` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_eval_queue.py tests/routers/test_imports_eval_coverage.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_eval_queue.py` — add test class for `enqueue_tier2_window` (tier-2 insert, idempotency, guest exclusion, lichess-eval exclusion, D-118-04 ordering)
- [ ] `tests/routers/test_imports_tier1_enqueue.py` — new file for `POST /imports/eval/tier1/{game_id}` (success, IDOR, guest, already-queued)
- [ ] `tests/routers/test_imports_tier2_enqueue.py` — new file for `POST /imports/eval/tier2` (success, in-flight gate, guest)
- [ ] `tests/routers/test_imports_eval_coverage.py` — extend with `analyzed_count` / `in_flight_count` shape tests

Frontend tests (Vitest):
- [ ] `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx` — extend for new return fields
- [ ] `frontend/src/components/library/__tests__/NoAnalysisState.test.tsx` — new: guest/analyze/in-flight branches

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | `Depends(current_active_user)` on both new endpoints |
| V4 Access Control | Yes | IDOR guard: `game.user_id != user.id → 404` on tier-1 endpoint (T-112-01 pattern) |
| V5 Input Validation | Yes | `game_id: int` path param — FastAPI rejects non-integers with 422 |
| V3 Session Management | No | Stateless JWT; no session objects |
| V6 Cryptography | No | No new crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on tier-1 endpoint (user analyzes another user's game) | Elevation of Privilege | `game.user_id != user.id → 404` (same pattern as `GET /library/games/{game_id}`) |
| Guest account bypassing analysis gate | Elevation of Privilege | `enqueue_tier1_game` has built-in guest no-op; new endpoints also check `is_guest` |
| Tier-2 spam (rapid re-clicks before poll reflects in-flight) | Denial of Service | `ON CONFLICT DO NOTHING` on `uq_eval_jobs_game_active`; `count_tier2_in_flight` check in endpoint |
| SQL injection in queue CTE | Tampering | All bound values use `:params`; no f-string interpolation in `sa.text()` calls (existing security note in eval_queue_service.py header) |

---

## Environment Availability

No external dependencies beyond those already in production. Stockfish pool, PostgreSQL, and the eval drain are all live.

---

## Open Questions

1. **Should `EnqueueTier1Response` be moved from `app/schemas/admin.py` to `app/schemas/imports.py`?**
   - What we know: the type is currently only used by the admin endpoint; the user-facing tier-1 endpoint will need the same shape.
   - What's unclear: whether to move the existing admin schema or create a parallel one in imports.py.
   - Recommendation: move to `imports.py` and import from there in `admin.py` (avoids duplication). The shape is identical.

2. **Does the `useEvalCoverage` poll stop condition need to include `in_flight_count === 0`?**
   - What we know: currently stops when `pct_complete === 100 && total_count > 0`. With the new response, analysis can be in-flight (non-zero `in_flight_count`) even when entry-ply evals are 100% complete.
   - What's unclear: whether Endgames/Openings/GlobalStats consumers care about in-flight (they don't show flaw affordances).
   - Recommendation: yes, extend stop condition to `pct_complete === 100 && total_count > 0 && in_flight_count === 0`. The existing consumers only read `isPending`, which will remain True while in-flight, so they correctly keep polling. No regression.

3. **Should the bulk "Analyze more" button live in `FlawsTab.tsx` or `NoEngineAnalysisFlawsState.tsx`?**
   - What we know: `NoEngineAnalysisFlawsState` is the full-width empty state shown when `analyzed_n === 0`. When some games are analyzed but low coverage, the FlawDenominatorPill/CTA is the better placement.
   - Recommendation: Put the primary CTA in `NoEngineAnalysisFlawsState` for the zero-analyzed case; put a secondary smaller CTA in `FlawDenominatorPill` for the low-coverage (but non-zero) case. Both trigger the same `useTier2Enqueue` mutation.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asyncio.create_task(enqueue_tier2_window(user_id))` in LastActivityMiddleware is safe because `__call__` is async | Pattern 2 | Low: LastActivityMiddleware.__call__ is verified async; task creation always valid in async context |
| A2 | The tier-2 bulk endpoint returning HTTP 409 Conflict for in-flight is the right status code | Pattern 5 | Low: could use 200 with status="in_flight" body instead; either works, 200-with-body is more client-friendly (TanStack won't treat as error) — planner should choose |
| A3 | `last_activity` column exists on `users` table and is updated by the middleware | Pattern 2, D-118-04 | Low: verified in `last_activity.py` line 84-86 that `sa_update(User).values(last_activity=now)` is the actual write |

**Assumption A2 note:** HTTP 200 with `{"status": "in_flight"}` is better than 409 for TanStack Query — a 409 triggers the mutation's `onError` callback, but "in-flight" is not really an error; it's an expected no-op state. Recommend HTTP 200 with `status: Literal["enqueued", "in_flight", "nothing_to_enqueue", "skipped_guest"]`.

---

## Sources

### Primary (HIGH confidence)
- `app/services/eval_queue_service.py` — verified `enqueue_tier1_game`, `_claim_tier3_derived`, `TIER_AUTO_WINDOW`, `LEASE_TTL_SECONDS` [VERIFIED: codebase grep]
- `app/middleware/last_activity.py` — verified `_ACTIVITY_THROTTLE`, impersonation skip, session discipline [VERIFIED: codebase grep]
- `app/routers/imports.py` — verified `get_eval_coverage` endpoint, `EvalCoverageResponse` keys, `_complete_import_job` call site [VERIFIED: codebase grep]
- `app/repositories/game_repository.py` — verified `count_pending_evals` uses `evals_completed_at`, NOT `is_analyzed` [VERIFIED: codebase grep]
- `app/models/game.py` — verified `is_analyzed` hybrid property, `full_evals_completed_at`, `lichess_evals_at` column names [VERIFIED: codebase grep]
- `app/models/eval_jobs.py` — verified `TIER_AUTO_WINDOW=2`, `uq_eval_jobs_game_active` partial index, `ix_eval_jobs_pick` partial index [VERIFIED: codebase grep]
- `app/schemas/imports.py` — verified current `EvalCoverageResponse` shape [VERIFIED: codebase grep]
- `frontend/src/hooks/useEvalCoverage.ts` — verified `EVAL_COVERAGE_POLL_INTERVAL_MS=3000`, return shape [VERIFIED: codebase grep]
- `frontend/src/types/api.ts` — verified `EvalCoverageResponse` TypeScript interface [VERIFIED: codebase grep]
- `frontend/src/types/users.ts` — verified `is_guest: boolean` in `UserProfile` [VERIFIED: codebase grep]
- `frontend/src/components/library/analysisCoverageCopy.tsx` — verified stale "coming soon" copy and its three consumers [VERIFIED: codebase grep]
- `frontend/src/components/library/NoAnalysisState.tsx` — verified current shape + imports [VERIFIED: codebase read]
- `frontend/src/components/library/FlawStatsPanel.tsx` — verified `FlawDenominatorPill` props + `ANALYSIS_COVERAGE_COPY` use [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- `118-CONTEXT.md` — locked decisions D-118-01 through D-118-13 [CITED: .planning/phases/118-demand-ux-auto-enqueue/118-CONTEXT.md]
- `117-CONTEXT.md` — D-117-05, D-117-09, D-117-11, D-117-12 invariants [CITED: .planning/phases/117-priority-queue-flaw-integration/117-CONTEXT.md]
- `116-CONTEXT.md` — `/imports/eval-coverage` origin, D-116 response key names [CITED: .planning/phases/116-all-ply-engine-core/116-CONTEXT.md]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns are existing codebase patterns
- Architecture: HIGH — verified exact function signatures, class structures, and hook points
- Pitfalls: HIGH — derived from reading actual code and identifying real divergences
- Critical finding (count_pending_evals misalignment): HIGH — verified line-by-line

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable codebase; valid until the next phase that touches eval_queue_service or game_repository)
