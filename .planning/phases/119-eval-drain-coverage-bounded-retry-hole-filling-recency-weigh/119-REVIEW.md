---
phase: 119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - app/services/eval_queue_service.py
  - app/services/eval_drain.py
  - app/models/game.py
  - app/repositories/game_repository.py
  - app/routers/imports.py
  - app/schemas/imports.py
  - alembic/versions/20260614_150000_phase_119_eval_drain_coverage.py
  - scripts/resweep_holed_games.py
  - frontend/src/components/library/EvalCoverageBadge.tsx
  - frontend/src/components/library/NoEngineAnalysisFlawsState.tsx
  - frontend/src/components/results/LibraryGameCardList.tsx
  - frontend/src/hooks/useEvalCoverage.ts
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/pages/library/FlawsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/types/api.ts
  - tests/services/test_eval_queue.py
  - tests/services/test_full_eval_drain.py
  - tests/routers/test_imports_eval_coverage.py
  - tests/test_game_repository.py
  - frontend/src/components/library/__tests__/EvalCoverageBadge.test.tsx
  - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 119: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Phase 119 reworks the eval-drain coverage pipeline: an Efraimidis–Spirakis recency-weighted tier-3 lottery, a hole-aware bounded-retry completion gate (`MAX_EVAL_ATTEMPTS`), a `resweep_holed_games` re-arm path, the `full_eval_attempts` column + partial index migration, and frontend repointing of the badge pulse / refresh effects from the removed `in_flight_count` to `analyzedCount`.

The core algorithms are correct on the focus points I was asked to scrutinize:

- **ES lottery (`_claim_tier3_derived`)**: The key `-ln(random())/weight` with default `ORDER BY ... ASC LIMIT 1` correctly selects the ES winner (minimum key). The weight `exp(-Δt/τ) + WEIGHT_FLOOR` is provably `> 0` (floor 0.005), so the division can never hit zero. The candidate predicate matches `needs_engine_full_evals` exactly and JOINs/EXISTS-filters guests. The residual PV-backfill tier is correctly gated behind the primary lottery and only it returns `is_lichess_eval_game=True`. All variable values are bound as `:params` — no f-string interpolation. Tests `test_tier3_*` cover distribution, guest exclusion, the lichess-leak fix, and the residual fallback.
- **Bounded-retry cap**: The decision tree (`new_attempts < MAX_EVAL_ATTEMPTS` → withhold; `>=` → stamp + one aggregated Sentry event via `set_context`, not interpolated message) is sound. The WR-05 all-fail circuit breaker returns before the write session opens, so a pool outage never consumes the retry budget (`test_all_fail_does_not_increment_attempts`). Mate-scored plies and terminal donors are correctly excluded from the hole count.
- **Async SQLAlchemy**: No `asyncio.gather` on a single session; the gather runs outside any session scope (guarded by an AST test). Sequential awaits in `get_eval_coverage` and `users_with_zero_pending`.
- **Migration**: up/down is symmetric and reversible — the downgrade re-creates `ix_eval_jobs_user_active` with the identical predicate from the Phase 118 migration.

No blockers found. The warnings below are correctness/robustness gaps that survive the happy path but degrade behavior in specific states; the info items are quality cleanups.

## Warnings

### WR-01: GlobalStats badge error state derives from a different query than its displayed numbers

**File:** `frontend/src/pages/GlobalStats.tsx:55,119-126`
**Issue:** The `EvalCoverageBadge` on the Stats tab takes `analyzedN={flawStatsData.analyzed_n}` / `totalN={flawStatsData.total_n}` (from `useLibraryFlawStats`), but `isCoverageError` is read from a *separate* query, `useEvalCoverage()`. If the `/imports/eval-coverage` endpoint fails while `/library/flaw-stats` succeeds, the badge renders the full-width "Failed to load analysis status…" error message (`EvalCoverageBadge` line 54-60) even though valid analyzed/total numbers are available from `flawStatsData`. Conversely, if flaw-stats fails but eval-coverage succeeds, `flawStatsData` is `undefined` so the badge is not rendered at all (line 119 guard), and the error surfaces only via `FlawStatsPanel`'s own `isError`. The badge's error signal and its data signal are decoupled, so the error message can be shown spuriously or the real data source's failure can be masked.
**Fix:** On the Stats tab, drive the badge's error state from the same query that supplies its numbers — pass `isCoverageError={flawStatsError}` (already available at line 52) rather than the unrelated `useEvalCoverage()` error. Then `useEvalCoverage()` is only needed if the badge still wants live polling here (it does not currently use `analyzedCount`/`totalCount` from it). Consider dropping the `useEvalCoverage()` call on this page entirely if `isError` is its only consumer.

### WR-02: Refresh effect fires a spurious invalidation on initial page load

**File:** `frontend/src/pages/library/GamesTab.tsx:210-217` and `frontend/src/pages/library/FlawsTab.tsx:240-249`
**Issue:** `prevAnalyzedRef` is initialized with `useRef(analyzedCount)`, which on the first render is the hook default `0` (before the eval-coverage fetch resolves). When the first fetch lands with any non-zero `analyzed_count` (the common case for a returning user who already has analyzed games), the effect sees `prev=0 < current=N` and immediately fires `invalidateQueries(['library-games'])` / `['library-flaws']` / `['library-flaw-stats']` / `['library-flaw-comparison']`. This is an extra network round-trip on every page visit for users with existing analysis, not just when analysis genuinely completes during the session. It does not loop (invalidating `library-*` does not change `analyzedCount`), so it is not a blocker, but it defeats the intent ("fire when a finished analysis flips the list").
**Fix:** Initialize the ref so the first resolved value is treated as the baseline, e.g. seed `prevAnalyzedRef` to a sentinel and skip the first transition:
```ts
const prevAnalyzedRef = useRef<number | null>(null);
useEffect(() => {
  const prev = prevAnalyzedRef.current;
  prevAnalyzedRef.current = analyzedCount;
  if (prev !== null && analyzedCount > prev) {
    void queryClient.invalidateQueries({ queryKey: ['library-games'] });
  }
}, [analyzedCount, queryClient]);
```

### WR-03: `resweep_holed_games` exception handler relies on `dir()` for scope inspection

**File:** `app/services/eval_drain.py:1666-1668`
**Issue:** The except block uses `len(game_ids) if "game_ids" in dir() else 0`. `dir()` with no arguments returns the names in the *current local scope*, which technically works here because `game_ids` is a function-local. But this is fragile and non-idiomatic: it depends on `dir()`'s no-arg behavior, and a refactor that moves the assignment into a nested scope (comprehension, helper) would silently make the guard always-False. The more conventional guard is `locals()` or simply initializing `game_ids` before the `try`. If the exception is raised by `session.execute(holed_game_ids_q)` (before `game_ids = ...`), `dir()` correctly excludes it — but the intent is opaque.
**Fix:** Initialize `game_ids: list[int] = []` before the `try`, then the handler is simply `{"game_count": len(game_ids)}` with no scope probe:
```python
async with async_session_maker() as session:
    game_ids: list[int] = []
    try:
        result = await session.execute(holed_game_ids_q)
        game_ids = [row[0] for row in result.all()]
        ...
    except Exception as exc:
        sentry_sdk.set_context("resweep", {"game_count": len(game_ids)})
        ...
```

### WR-04: `resweep_holed_games` clears markers in one unbounded UPDATE without batching

**File:** `app/services/eval_drain.py:1631-1662`
**Issue:** When `limit is None` (the documented "sweep all" prod path, and the `scripts/resweep_holed_games.py` default), the candidate query scans every stamped engine game with a non-terminal hole and the subsequent UPDATE rewrites `full_evals_completed_at`, `full_pv_completed_at`, and `full_eval_attempts` for the entire `game_ids` set in a single statement/transaction. Given the production backlog scale referenced throughout the codebase (~558k games), an unbounded sweep can re-arm a very large set at once, and clearing `full_evals_completed_at` flips all of them back into the tier-3 candidate pool simultaneously. The `IN (game_ids)` UPDATE also materializes the full id list in Python and binds it as parameters. This is an operational/correctness footgun for the documented one-liner: a prod operator running `resweep_holed_games()` (no limit) re-queues the whole holed backlog in one shot. Note the `IN (...)` UPDATE with a large list also risks exceeding parameter limits.
**Fix:** Document and default to a bounded `--limit` for the prod path, or batch the UPDATE in chunks (mirroring `_POSITION_CHUNK_SIZE` discipline elsewhere). At minimum, make `scripts/resweep_holed_games.py` require an explicit confirmation or a default limit for the all-games case so an operator cannot accidentally re-arm the entire backlog. Tests only exercise 1-2 games, so the at-scale behavior is unverified.

## Info

### IN-01: `tau_seconds` computation is correct but the inline comment inverts the derivation

**File:** `app/services/eval_queue_service.py:257-259`
**Issue:** The code computes `tau_seconds = RECENCY_HALF_LIFE_DAYS / math.log(2) * 86400.0`, which is τ = τ½ / ln2 in days, then × seconds/day. That is correct for `exp(-Δt/τ)` to halve at `Δt = τ½`. The comment on line 258 says "τ = τ½ / ln2" which matches, but the docstring at line 226-228 describes it as "τ = RECENCY_HALF_LIFE_DAYS / ln(2) converted to seconds" — consistent. No bug; flagging only because the two-step `/ log(2) * 86400.0` is easy to misread as `/(log(2)*86400)`. Consider parenthesizing or extracting `_SECONDS_PER_DAY = 86400` as a named constant (CLAUDE.md no-magic-numbers).
**Fix:** `tau_seconds = (RECENCY_HALF_LIFE_DAYS / math.log(2)) * _SECONDS_PER_DAY` with `_SECONDS_PER_DAY: int = 86400`.

### IN-02: Magic literal epoch `'1970-01-01'` inline in the ES SQL

**File:** `app/services/eval_queue_service.py:282`
**Issue:** The COALESCE fallback timestamp `'1970-01-01'::timestamptz` is a magic literal embedded in the `sa.text` string. It is safe (not user data) but conflicts with the no-magic-numbers guideline and is undocumented as "epoch-0 so exp term ≈ 0". The docstring explains the intent (line 265) but the literal itself has no inline note.
**Fix:** Acceptable as-is given it is a SQL constant, but a brief inline SQL comment (`-- epoch-0: NULL last_activity → floor weight`) would aid future readers. Not blocking.

### IN-03: `_signal_flaw_completion` set is unbounded (acknowledged, carried from Phase 117)

**File:** `app/services/eval_drain.py:668-682`
**Issue:** `_recently_flaw_completed_users` is a module-level `set[int]` that only ever grows (`.add`), with no eviction. The docstring acknowledges this ("intentionally not bounded — stays small in practice"). At 8.4k games/day across a few hundred users it is bounded in practice, but it is a slow leak over a long-lived process with many distinct users and no consumer draining it in Phase 119. Out of v1 perf scope, noting for the planned Phase 118+ cache-invalidation wiring.
**Fix:** When the consumer is wired, have it `.discard()` processed users, or switch to a bounded structure. No action required this phase.

### IN-04: `_GameColorView.__getattr__` forwards every attribute including potential typos silently

**File:** `app/services/eval_drain.py:652-665`
**Issue:** `__getattr__` proxies all non-`user_color` attribute access to the wrapped `Game`. This is intentional and minimal (D-117-08), but it means a future typo'd attribute on the view (e.g. `view.user_colour`) silently falls through to `getattr(self._game, "user_colour")` and raises a generic `AttributeError` from the ORM object rather than a clear "view has no such attribute". Low risk since `count_game_severities` is documented to read only `user_color`.
**Fix:** None required. If `count_game_severities` ever grows to read more fields, consider an explicit allowlist instead of a blanket proxy.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
