---
phase: 119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh
plan: 02
subsystem: eval-drain, eval-queue
tags: [eval-drain, eval-queue, lottery, efraimidis-spirakis, lichess-leak, postgresql]

# Dependency graph
requires:
  - phase: 119-01
    provides: ix_games_needs_engine_full_evals partial index (consumed by the ES lottery query)

provides:
  - SEED-046 recency-weighted ES user lottery in _claim_tier3_derived
  - lichess-eval-game leak fix (candidate predicate is now needs_engine_full_evals)
  - Residual fallback tier for PV-backfill-only lichess games
  - is_lichess_eval_game rename (was is_analyzed, collision with Game hybrid property)

affects:
  - eval_drain.py: _apply_full_eval_results, _full_drain_tick (field rename only)
  - tests: test_eval_queue.py (6 new lottery tests), test_full_eval_drain.py (4 rename fixes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Efraimidis-Spirakis weighted reservoir sampling: ORDER BY -ln(random())/weight LIMIT 1"
    - "ES user lottery weight = exp(-Δt/τ) + WEIGHT_FLOOR, weight always > 0 (div-by-zero guard)"
    - "Two-step tier-3: (1) pick user by ES lottery over needs-engine candidates, (2) pick best game for that user by TC→played_at"
    - "Residual fallback: when lottery pool is empty, drain a PV-backfill-only lichess game"
    - "τ and floor as tunable module constants (RECENCY_HALF_LIFE_DAYS, WEIGHT_FLOOR)"

key-files:
  modified:
    - app/services/eval_queue_service.py
    - app/services/eval_drain.py
    - tests/services/test_eval_queue.py
    - tests/services/test_full_eval_drain.py
    - CHANGELOG.md

key-decisions:
  - "D-119-02-01: ES lottery weights the USER not the game (prevents large-backlog users drowning small-backlog users at same recency)"
  - "D-119-02-02: τ½=1d (RECENCY_HALF_LIFE_DAYS=1.0) — returning user gets ~65-70% share immediately against floor-dominated stale pool; retune live per SEED-046"
  - "D-119-02-03: WEIGHT_FLOOR=0.005 — anti-starvation + div-by-zero guard; must stay ≤0.01 to avoid swamping recency signal"
  - "D-119-02-04: SQL ES key uses sa.text with :params binding — never f-string interpolated (RESEARCH §Security V5)"
  - "D-119-02-05: Plain DISTINCT replaced by EXISTS subquery — PostgreSQL planner converts EXISTS to Nested Loop Semi Join using ix_games_needs_engine_full_evals; 4ms on dev, sub-100ms at prod scale"
  - "D-119-02-06: Statistical recency test uses N=400 draws with 65% threshold — avoids flaky exact-ordering assertions while covering the probabilistic behavior"

metrics:
  duration: 45min
  completed: 2026-06-14
---

# Phase 119 Plan 02: SEED-046 ES Recency-Weighted Lottery + Lichess Leak Fix Summary

**Efraimidis-Spirakis user lottery replacing winner-take-all last_activity ordering; fixes live prod tier-3 lichess-eval throughput waste (~70% of engine budget); renames is_analyzed→is_lichess_eval_game**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-06-14
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added module constants `RECENCY_HALF_LIFE_DAYS: float = 1.0` and `WEIGHT_FLOOR: float = 0.005` with tuning notes (SEED-046 / RESEARCH-NOTES)
- Rewrote `_claim_tier3_derived` as a two-step ES lottery:
  1. Weighted user pick via `ORDER BY -ln(random()) / (exp(-Δt/τ) + floor) LIMIT 1` over non-guest users with at least one needs-engine game; τ and floor bound as `:params` (no f-string)
  2. Best game for the picked user by TC→played_at order, WHERE predicate = `needs_engine_full_evals` (full_evals_completed_at IS NULL AND lichess_evals_at IS NULL)
- Fixed the live prod lichess leak: old WHERE clause was `full_evals_completed_at IS NULL` only, relying on a dead `lichess_evals_at` tiebreaker that never fired (played_at broke ties first), causing ~70% engine throughput waste re-analyzing lichess games; new predicate excludes them entirely
- Dropped dead D-118-04 `User.last_activity.desc()` top key and `Game.lichess_evals_at.isnot(None).asc()` tiebreaker
- Added residual fallback: when the lottery pool is empty (no needs-engine candidates), drain a PV-backfill-only lichess game; the only path returning `is_lichess_eval_game=True`
- Renamed `ClaimedJob.is_analyzed` → `is_lichess_eval_game` throughout eval_queue_service.py and eval_drain.py (removes collision with `Game.is_analyzed` hybrid property which tests `white_blunders IS NOT NULL`, a different concept)
- Replaced deterministic D-118-04 ordering tests with 6 new probabilistic lottery tests; updated 4 drain tests for the field rename

## EXPLAIN Verification (Task 2)

**Query:** the ES weighted user pick (`EXISTS` subquery formulation)

```sql
SELECT u.id
FROM users u
WHERE u.is_guest = false
  AND EXISTS (
    SELECT 1 FROM games g
    WHERE g.user_id = u.id
      AND g.full_evals_completed_at IS NULL
      AND g.lichess_evals_at IS NULL
  )
ORDER BY -ln(random()) / (exp(-EXTRACT(EPOCH FROM ...)/tau) + floor)
LIMIT 1;
```

**EXPLAIN (ANALYZE, BUFFERS) on dev DB:**

```
Limit  (cost=12.70..12.70 rows=1) (actual time=3.902..3.903 rows=1)
  Sort  (actual time=3.901)
    Sort Method: top-N heapsort  Memory: 25kB
    Nested Loop Semi Join  (actual time=0.676..3.848 rows=17)
      Seq Scan on users u  (actual time=0.255..0.261 rows=19)
        Filter: (NOT is_guest)
        Rows Removed by Filter: 14
      Index Only Scan using ix_games_needs_engine_full_evals on games g
        Index Cond: (user_id = u.id)
        Heap Fetches: 17
        Index Searches: 19
Planning Time: 2.827 ms
Execution Time: 4.004 ms
```

**Index strategy:** PostgreSQL chose a `Nested Loop Semi Join` with `Index Only Scan using ix_games_needs_engine_full_evals` — exactly the partial index added by migration 119-01. The planner converts `EXISTS` to a semi-join and uses the index to check each non-guest user's backlog existence.

**Sub-100ms judgment:** The query scans `users` (33 rows on dev, 66 on prod) and does one index seek per user. At prod scale (~66 non-guest users with a 557k-row index), execution time will be proportional to the number of users, NOT the 557k rows. Estimated prod time: ~8ms (2× dev user count × 4ms). The partial index approach is well within the sub-100ms target. **Skip-scan (recursive CTE) is NOT needed** — the EXISTS-based join is already using the index efficiently.

**τ/floor prod-tuning note:**
- `RECENCY_HALF_LIFE_DAYS=1.0` (τ½=1d, τ=1.44d): a returning user (Δt~0) gets ~65-70% of draws against a floor-dominated stale pool of 59 users. Best serves the "fast catch-up on return" priority.
- `WEIGHT_FLOOR=0.005`: 59-user floor mass ≈ 0.30; lone returner share ≈ 70%. Do NOT raise above 0.01 (floor=0.05 → mass=2.95, returner share drops to ~16%).
- To retune: update `RECENCY_HALF_LIFE_DAYS` and `WEIGHT_FLOOR` constants in `app/services/eval_queue_service.py` — no SQL or migration needed. τ½=2-3d is a reasonable alternative for smoother idle sharing.

## Task Commits

1. **Task 1 RED: Failing tests for ES lottery + leak fix** - `b044d96a` (test)
2. **Task 1 GREEN: SEED-046 ES lottery + lichess leak fix + rename** - `1342aac3` (feat)
3. **Task 2: is_analyzed→is_lichess_eval_game in eval_drain.py + CHANGELOG** - `dbf4878f` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 4 drain tests that used `ClaimedJob(is_analyzed=...)` which broke after the rename**
- **Found during:** Task 2 (running the full eval-drain test suite)
- **Issue:** `test_full_eval_drain.py` constructs `ClaimedJob` directly via `_patch_drain_for_tick_tests`; after renaming the field, 5 tests raised `TypeError: unexpected keyword argument 'is_analyzed'`
- **Fix:** Renamed the helper param `is_analyzed → is_lichess_eval_game` and updated all callers; updated docstring/comment references
- **Files modified:** `tests/services/test_full_eval_drain.py`
- **Committed in:** `dbf4878f`

## Threat Flags

No new network endpoints or auth paths introduced. The ES lottery query touches only the `users` and `games` tables (read-only in this context), with all variable values bound as `:params` (T-119-06 mitigated). Guest exclusion preserved via `is_guest = false` filter in both the lottery WHERE and the residual fallback WHERE (T-119-04 mitigated). WEIGHT_FLOOR ensures weight > 0 always (T-119-05 mitigated).

## Self-Check: PASSED

All created/modified files exist; all commits are in git log. Full suite: 43 tests passed (eval_queue + eval_drain).
