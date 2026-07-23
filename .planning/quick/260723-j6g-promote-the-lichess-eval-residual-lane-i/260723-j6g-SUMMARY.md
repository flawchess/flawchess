---
phase: quick-260723-j6g
plan: 01
subsystem: eval-queue
tags: [eval-queue, tier-3-lottery, starvation-fix, queue-03]
dependency-graph:
  requires: []
  provides:
    - "Unified tier-3 ES lottery over needs-engine ∪ lichess-eval-pv-incomplete games"
  affects:
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py
tech-stack:
  added: []
  patterns:
    - "Single Efraimidis–Spirakis (ES) recency-weighted lottery over a UNION predicate, instead of a primary-lottery + residual-fallback two-lane design"
    - "Guest asymmetry expressed per-branch inside a unified SQL predicate rather than via a blanket outer filter"
key-files:
  created: []
  modified:
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py
decisions:
  - "DELIBERATE precedence change vs 174-07/SEED-109: lichess-eval-pv-incomplete games now compete in the SAME tier-3 lottery as needs-engine games, instead of running only when the needs-engine backlog is globally empty — fixes prod lichess-eval starvation behind a 63.5k-game needs-engine import (verified 2026-07-23)"
  - "is_lichess_eval_game is derived per-picked-game via a PK-indexed Game.lichess_evals_at lookup after Step 2, not assumed from which union branch 'should' have matched — more robust and consistent with how tier-1/2 and tier-4b already resolve the same flag"
  - "No new guest-asymmetry test added: test_tier3_guest_excluded_from_lottery already asserts exactly the required scenario (a guest's needs-engine-only game is never picked across draws) and continues to pass unchanged under the unified query"
  - "No migration: both union branches are already covered by existing partial indexes (ix_games_needs_engine_full_evals, ix_games_lichess_pv_backfill_pending), so PostgreSQL can BitmapOr them for the unified Step-1 EXISTS predicate"
metrics:
  duration: "~35 min"
  completed: 2026-07-23
status: complete
---

# Phase quick-260723-j6g Plan 01: Promote the lichess-eval residual lane into the tier-3 lottery Summary

Unified the tier-3 idle-backlog lottery so lichess-eval-pv-incomplete games compete on equal footing with needs-engine games in one recency-weighted Efraimidis–Spirakis draw, instead of only draining via a residual fallback when the needs-engine backlog is globally empty.

## What Was Built

`_claim_tier3_derived` in `app/services/eval_queue_service.py` was rewritten from a two-lane design (Step 1/Step 2 primary needs-engine lottery, then a separate residual-fallback lottery for lichess-eval games) into a single unified lottery:

- **Step 1** — `_es_weighted_user_pick` now runs with `include_guests=True` and a `candidate_exists_sql` that is the OR of two branches: (a) needs-engine (`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`), guarded by `u.is_guest = false`; (b) lichess-eval-pv-incomplete (`full_pv_completed_at IS NULL AND lichess_evals_at IS NOT NULL`), unguarded so guests qualify. The outer guest filter that `_es_weighted_user_pick` normally applies is dropped; the per-branch guard on branch (a) is what now enforces QUEUE-08.
- **Step 2** — `_es_weighted_game_pick` mirrors the same union, scoped to `g.user_id = :picked_user`, with the needs-engine branch guarded by an `EXISTS (SELECT 1 FROM users u WHERE u.id = :picked_user AND u.is_guest = false)` subquery.
- After Step 2 returns a `game_id`, `is_lichess_eval_game` is derived via a fresh PK-indexed lookup on `Game.lichess_evals_at`, rather than assumed from which branch matched.
- If Step 1 returns `None` → return `None`. If Step 2 returns `None` (a race where the picked user's matching games drained between the two steps) → return `None`, no fallback lane. The residual `_es_weighted_game_pick` call and its trailing `select(Game.user_id)` lookup were deleted entirely.
- Module-level and function docstrings were rewritten to describe the unified design, explicitly state the deliberate precedence change relative to 174-07/SEED-109, and cite the prod starvation motivation (user 235's 63.5k-game needs-engine import starving user 28's 3 returning lichess-eval games).

Test changes in `tests/services/test_eval_queue.py`:

- `test_tier3_never_picks_lichess_while_engine_candidate_exists` (encoded the now-false OLD contract) was replaced with `test_tier3_lichess_and_engine_both_participate`: a non-guest user owning both game types has BOTH picked at least once over 200 draws.
- Added `test_tier3_lichess_does_not_starve_behind_mass_importer`: two equally-recent non-guest users (one needs-engine, one lichess-eval) both win draws — the direct proof of the core starvation fix.
- No new guest-asymmetry test was added: `test_tier3_guest_excluded_from_lottery` already asserts the exact required scenario and needed no changes.
- The seven `test_residual_fallback_*` / `test_tier3_residual_fallback` tests were left with unchanged assertions (they still pass — see Verification below); two docstrings were lightly reworded from "residual tier/fallback" framing to "unified lottery, branch (b) of the union" framing since the old framing was no longer accurate.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written for Task 1's source rewrite.

**1. [Task 2 scope decision] Skipped adding a duplicate guest-asymmetry test**
- **Found during:** Task 2
- **Issue:** The plan asked to add a new test proving "a guest user owning ONLY a needs-engine game is NEVER returned across ~10 draws." `test_tier3_guest_excluded_from_lottery` (pre-existing, in the same `TestTier3Lottery` class) already asserts exactly this scenario verbatim (guest with `full_evals_completed_at=None, lichess_evals_at=None`, 10 draws, never picked).
- **Fix:** Verified the existing test still passes unchanged under the new unified query (guest is excluded from branch (a) both in Step 1 and Step 2's EXISTS guard); did not add a duplicate.
- **Files modified:** None (verification only).
- **Commit:** N/A (no code change for this item).

## Mutation Verification

Per the plan's verification section, reverted Task 1's source change (via `git show HEAD~1` restore) and re-ran the two new tests:

```
FAILED tests/services/test_eval_queue.py::TestTier3Lottery::test_tier3_lichess_and_engine_both_participate
FAILED tests/services/test_eval_queue.py::TestTier3Lottery::test_tier3_lichess_does_not_starve_behind_mass_importer
```

`test_tier3_lichess_does_not_starve_behind_mass_importer` failed with `count_b == 0` — the exact starvation this quick fixes. This confirms the new tests assert real behavior, not symbol presence. The source file was restored to the Task-1 committed state afterward (verified via `git diff` showing a clean tree before Task 2's commit).

## Verification

- `uv run pytest tests/services/test_eval_queue.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py` — 184 passed.
- `uv run ruff check app/ tests/` — clean.
- `uv run ty check app/ tests/` — zero errors.
- No migration needed (confirmed): both union branches are covered by existing partial indexes (`ix_games_needs_engine_full_evals`, `ix_games_lichess_pv_backfill_pending`).

## Known Stubs

None.

## Threat Flags

None — this quick only reshapes the internal tier-3 candidate predicate (trusted hardcoded SQL fragments, all variable values bound as params); no new trust boundary, endpoint, or schema surface introduced. Matches the plan's `<threat_model>` disposition (T-j6g-01 mitigate, T-j6g-02 accept).

## Self-Check: PASSED

- `app/services/eval_queue_service.py` — FOUND
- `tests/services/test_eval_queue.py` — FOUND
- Commit `537b332b` (feat: unify lichess-eval residual lane) — FOUND in git log
- Commit `ec9940f6` (test: rewrite obsolete test + add starvation-fix coverage) — FOUND in git log
