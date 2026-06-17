---
phase: 119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh
plan: 01
subsystem: database, api
tags: [alembic, sqlalchemy, eval-drain, sentry, postgresql, partial-index]

# Dependency graph
requires:
  - phase: 118-demand-ux-auto-enqueue
    provides: ix_eval_jobs_user_active (dropped here), eval_queue_service claim_eval_job

provides:
  - games.full_eval_attempts SmallInteger column (NOT NULL default 0) via migration 20260614150000
  - ix_games_needs_engine_full_evals partial index (SEED-046 lottery candidate pool)
  - MAX_EVAL_ATTEMPTS=3 constant in eval_drain.py
  - Hole-aware completion gate in _full_drain_tick Step 4 (3-path decision tree)
  - resweep_holed_games() function + scripts/resweep_holed_games.py CLI

affects:
  - 119-02 (SEED-046 recency-weighted lottery reads ix_games_needs_engine_full_evals and full_eval_attempts)
  - 119-03 (dead index ix_eval_jobs_user_active is dropped here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hole-aware drain: stamp only when failed_ply_count==0 OR attempts >= MAX_EVAL_ATTEMPTS"
    - "All-fail circuit breaker (WR-05) does NOT consume full_eval_attempts budget"
    - "Aggregated Sentry at cap: set_context(eval, {game_id, hole_count, attempts}) + capture_message"
    - "Re-enqueue sweep: clear completion markers + reset attempts instead of extending backfill_eval.py"

key-files:
  created:
    - alembic/versions/20260614_150000_phase_119_eval_drain_coverage.py
    - scripts/resweep_holed_games.py
  modified:
    - app/models/game.py
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py
    - CHANGELOG.md

key-decisions:
  - "D-119-01: Re-enqueue sweep chosen over backfill_eval.py extension (wrong shape for all-ply scan)"
  - "D-119-02: Attempts increment ONLY on some-succeeded-but-holes-remain path; all-fail stays on WR-05 circuit breaker to prevent pool outages from exhausting budget"
  - "D-119-03: Cap Sentry event replaces former per-tick Sentry call (was noise on retried games)"
  - "D-119-04: full_pv_completed_at withheld alongside full_evals_completed_at on under-cap path (eval and PV land together)"

patterns-established:
  - "Phase 119 hole definition: eval_cp IS NULL AND eval_mate IS NULL on a non-terminal, non-mate ply"
  - "Migration-only indexes: both new indexes (SEED-046) are migration-only, matching Phase 118 precedent"

requirements-completed:
  - SEED-045
  - Schema migration for the whole phase

# Metrics
duration: 42min
completed: 2026-06-14
---

# Phase 119 Plan 01: Bounded-Retry Hole-Filling + Phase-Wide Migration Summary

**Hole-aware full-eval drain with MAX_EVAL_ATTEMPTS=3 cap, backfill sweep, and single phase-wide migration adding games.full_eval_attempts + SEED-046 partial index**

## Performance

- **Duration:** ~42 min
- **Started:** 2026-06-14T13:54:00Z
- **Completed:** 2026-06-14T14:36:37Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Phase-wide Alembic migration (revision 20260614150000) adds `games.full_eval_attempts` SmallInteger, creates `ix_games_needs_engine_full_evals` partial index for the SEED-046 lottery, and drops the dead `ix_eval_jobs_user_active` index — all round-trip verified
- `_full_drain_tick` Step 4 implements a 3-path decision tree: (A) no holes → stamp complete; (B) holes + under cap → increment `full_eval_attempts`, return pending; (C) holes + cap reached → stamp anyway + ONE aggregated Sentry event with `set_context` (per CLAUDE.md rules — no interpolated IDs)
- WR-05 all-fail circuit breaker path unchanged: pool outages do NOT increment `full_eval_attempts` so a transient outage cannot exhaust the retry budget and silently drop coverage
- `resweep_holed_games(limit, dry_run)` + `scripts/resweep_holed_games.py` CLI re-arms already-stamped engine games carrying non-terminal holes by clearing completion markers + resetting `full_eval_attempts=0`
- 5 new TDD behavior tests (Phase 119 SEED-045) + 3 resweep tests; 3 existing tests updated to reflect hole-aware behavior (full suite: 2614 passed)

## Task Commits

1. **Task 1: Phase-wide Alembic migration** - `79430900` (feat)
2. **Task 2 RED: Failing tests for hole-aware gate** - `465fffa3` (test)
3. **Task 2 GREEN: Hole-aware completion gate + bounded re-pick + aggregated Sentry** - `0e1f880c` (feat)
4. **Task 3: Backfill sweep for already-stamped-with-holes games** - `fccd7ff6` (feat)

## Files Created/Modified

- `alembic/versions/20260614_150000_phase_119_eval_drain_coverage.py` — Phase-wide migration: full_eval_attempts column, ix_games_needs_engine_full_evals partial index, drop ix_eval_jobs_user_active
- `app/models/game.py` — Add `full_eval_attempts: Mapped[int]` column; comment in `__table_args__` noting migration-only SEED-046 index
- `app/services/eval_drain.py` — Add `MAX_EVAL_ATTEMPTS=3` constant; load `full_eval_attempts` in Step 2; 3-path Step 4 write session; updated `_mark_full_evals_completed` docstring; add `resweep_holed_games()` function
- `tests/services/test_full_eval_drain.py` — Add Phase 119 user fixture; update `_insert_game` to accept `full_eval_attempts`/`full_pv_completed_at`; add 5 `TestHoleAwareCompletionGate` tests + 3 `TestResweepHoledGames` tests; update 4 existing tests for hole-aware behavior
- `scripts/resweep_holed_games.py` — Thin CLI argparse wrapper (`--dry-run`, `--limit`)
- `CHANGELOG.md` — Add Phase 119 fixed entry under `[Unreleased]`

## Decisions Made

- **Re-enqueue sweep over backfill_eval.py** (D-119-01): `backfill_eval.py` is span-entry/middlegame-focused with its own streaming collectors — wrong shape for an all-ply "find stamped games with non-terminal holes" scan. A targeted SQL sweep + re-enqueue is cleaner and re-uses the already-correct drain.
- **All-fail path does NOT increment attempts** (D-119-02): WR-05 circuit breaker returns early before the write session. The attempts increment is gated inside the write session's `failed_ply_count > 0 AND some_evals_succeeded` branch. Pool outages cannot exhaust the budget.
- **Cap Sentry replaces per-tick Sentry** (D-119-03): The former `capture_message("full-drain engine returned None tuple")` at every tick with holes was replaced by a single aggregated cap-only event. Firing on every retry tick was noise; firing only at the cap signals a genuine "deterministically holed" game.
- **full_pv_completed_at withheld alongside full_evals_completed_at** (D-119-04): Eval and PV land in the same drain pass; an incomplete game should not be PV-marked complete while evals are missing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 4 existing tests that relied on old D-116-07 "stamp-even-with-holes" behavior**
- **Found during:** Task 2 GREEN (after implementing hole-aware gate)
- **Issue:** Existing tests used PGN/position setups that left post-move holes (not all ply rows present), which now correctly returns `processed=False` under Phase 119 semantics. Four tests failed: `test_marker_set_after_drain`, `test_marker_set_with_holes`, `test_best_move_written_after_tick`, `test_dedup_best_move_transplanted`.
- **Fix:** Updated each test to either provide complete position rows (no holes) or explicitly test the new under-cap behavior. Renamed `test_marker_set_with_holes` → `test_marker_withheld_with_holes_under_cap`.
- **Files modified:** `tests/services/test_full_eval_drain.py`
- **Committed in:** `0e1f880c` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — existing tests were testing old behavior that Phase 119 intentionally changes)
**Impact on plan:** Essential for test correctness. No scope creep.

## Issues Encountered

None — plan executed cleanly. The test update was expected when changing drain semantics.

## User Setup Required

None — no external service configuration required. To re-arm already-stamped holed games on prod:
```bash
uv run python scripts/resweep_holed_games.py --dry-run   # preview
uv run python scripts/resweep_holed_games.py              # run
```

## Next Phase Readiness

- Migration `20260614150000` is applied to the dev DB (head) — plans 02 and 03 can build on it
- `full_eval_attempts` column is live; `ix_games_needs_engine_full_evals` partial index exists
- `MAX_EVAL_ATTEMPTS` constant is importable from `app.services.eval_drain`
- Plan 02 can add the SEED-046 recency-weighted lottery using the new index
- Plan 03 can remove `count_in_flight_evals` (its dead `ix_eval_jobs_user_active` index was dropped here)

## Threat Flags

No new network endpoints, auth paths, or schema changes at trust boundaries beyond what the plan's threat model covers. The `resweep_holed_games` function is internal only (no HTTP surface).

## Self-Check: PASSED

All created files exist and all commits are in git log.

---
*Phase: 119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh*
*Completed: 2026-06-14*
