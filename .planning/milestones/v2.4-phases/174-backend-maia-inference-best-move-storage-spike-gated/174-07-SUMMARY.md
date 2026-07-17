---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 07
subsystem: backend-eval-pipeline
tags: [postgres, alembic, eval-queue, es-lottery, gems-detection, eval-drain]

# Dependency graph
requires:
  - phase: 174-06
    provides: "Unified full MultiPV-2 pass for lichess-eval games (targets filter retired); hole-counting parity so a genuine engine failure withholds full_pv_completed_at instead of silently completing"
provides:
  - "Broadened residual PV-backfill fallback in _claim_tier3_derived: predicate changed from full_evals_completed_at IS NULL to full_pv_completed_at IS NULL (same precedence, strict superset population) — covers the ~43k lichess-eval backlog games that are already eval-complete but best-move/PV-incomplete"
  - "ix_games_lichess_pv_backfill_pending partial index backing the broadened predicate at scale; supersedes and replaces ix_games_pv_backfill_pending"
  - "End-to-end proof that a backlog pick flows through the real claim_eval_job -> _claim_tier3_derived -> _full_drain_tick -> game_best_moves + full_pv_completed_at stamp, and self-terminates out of the predicate afterward"
affects: [176]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Broadening an existing lottery rung's WHERE predicate (superset population, same precedence) instead of adding a new rung, to avoid introducing a new starvation dynamic"

key-files:
  created:
    - alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py
  modified:
    - app/services/eval_queue_service.py
    - app/models/game.py
    - tests/services/test_eval_queue.py
    - tests/services/test_full_eval_drain.py

key-decisions:
  - "Dropped the now-superseded ix_games_pv_backfill_pending in the same migration that adds ix_games_lichess_pv_backfill_pending — its predicate (full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL) no longer matches any query after the broadening, so leaving it would be permanent dead weight"
  - "Self-termination is verified via a direct SQL predicate check against the specific game_id post-drain (not by re-running the lottery), keeping the assertion deterministic and independent of any other backlog rows that might exist in the shared test DB"
  - "The double-claim/idempotency test forces the SAME game_id via a mocked claim across two ticks (not a real concurrent lottery draw), which is the actual scenario the module docstring's 'D-7 residual-duplicate acceptance' describes and is deterministic to reproduce"

requirements-completed: [GEMS-01, GEMS-03]

coverage:
  - id: D1
    description: "Residual PV-backfill fallback broadened from full_evals_completed_at IS NULL to full_pv_completed_at IS NULL at its existing precedence (final fallback after the needs-engine tier-3 pick) — no new rung, no new starvation dynamic; scope stays lichess-eval-only and guest-excluded"
    requirement: GEMS-01
    verification:
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_includes_full_evals_stamped_backlog_game"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_excludes_pv_already_covered_lichess_game"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_excludes_engine_game_missing_pv"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_excludes_guest_backlog_game"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_fires_under_contention"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier3Lottery::test_residual_fallback_es_weighted_recency"
        status: pass
    human_judgment: false
  - id: D2
    description: "ix_games_lichess_pv_backfill_pending partial index backs the broadened predicate at scale (mirrors ix_games_needs_engine_full_evals); superseded ix_games_pv_backfill_pending dropped in the same migration; migration applies cleanly (up and down) on the existing dev DB with no alembic-check drift"
    verification:
      - kind: integration
        ref: "uv run alembic upgrade head / downgrade -1 / upgrade head round-trip (manual verification during execution)"
        status: pass
      - kind: other
        ref: "uv run alembic check — No new upgrade operations detected"
        status: pass
    human_judgment: false
  - id: D3
    description: "A lichess-eval backlog game selected by the real (unmocked) claim_eval_job/residual fallback drains through the unified 174-06 pass end to end: gets a game_best_moves row at its out-of-book played==best ply (GEMS-02 gate stays selective — a sub-margin ply correctly yields none), keeps stored lichess %evals untouched, and self-terminates out of the 174-07 predicate"
    requirement: GEMS-03
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestLichessBestMoveBackfill::test_backfill_pick_drains_gets_best_moves_and_self_terminates"
        status: pass
    human_judgment: false
  - id: D4
    description: "Two picks of the same backlog game (double-claim under the plain non-locking residual-fallback SELECT) do not produce duplicate game_best_moves rows — upsert on (game_id, ply) is idempotent"
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestLichessBestMoveBackfill::test_double_pick_of_same_backlog_game_does_not_duplicate_best_moves"
        status: pass
    human_judgment: false
  - id: D5
    description: "Dev-DB reasoning check (no reset, read-only query): the broadened predicate correctly identifies the eval-complete-but-pv-incomplete lichess backlog on the real dev DB, distinct from the old predicate's narrower count"
    verification: []
    human_judgment: true
    rationale: "A read-only count query was run during execution (3862 broadened-backlog vs 567 old-predicate-backlog, out of 4539 total lichess-eval games, 677 already covered) and confirmed the planner uses the new index via EXPLAIN — this is a point-in-time observation against live dev data, not a repeatable automated test, so it is left as a human-reviewable data point rather than a pass/fail automated check."

duration: ~35min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 07: Lichess best-move backfill (residual fallback broadening) Summary

**Broadened the existing tier-3 residual PV-backfill fallback from `full_evals_completed_at IS NULL` to `full_pv_completed_at IS NULL` (same precedence, same ES weighted-random key) so it opportunistically drains the ~43k lichess-eval backlog games that are eval-complete but best-move-incomplete, backed by a new partial index and proven self-terminating end-to-end.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2
- **Files modified:** 5 (1 created: migration; 4 modified: eval_queue_service.py, models/game.py, 2 test files)

## Accomplishments

- Broadened `_claim_tier3_derived`'s existing residual fallback predicate (the final rung after the needs-engine tier-3 pick) from `full_evals_completed_at IS NULL` to `full_pv_completed_at IS NULL`, keeping everything else (guest exclusion, ES weighted-random game_weight key, precedence) unchanged — a strict superset of the old population, so no new starvation dynamic.
- Added 8 new tests proving: the broadening includes the full_evals-stamped backlog case the old predicate missed; already-pv-covered lichess games are excluded (self-termination proven at the query level); engine games (`lichess_evals_at IS NULL`) stay out of scope; guest backlog games stay excluded; the fallback fires with frequency > 0 under contention; and selection is still governed by the ES weighted-random key (recency + non-starvation), not a deterministic first-row pick.
- Added `ix_games_lichess_pv_backfill_pending` (partial index mirroring `ix_games_needs_engine_full_evals`) backing the broadened predicate at scale, dropping the now-superseded `ix_games_pv_backfill_pending` in the same migration since its predicate no longer matches any query. Updated the matching `Index()` declaration in `app/models/game.py` so `alembic check` stays drift-free (the old index WAS declared in `__table_args__`, not migration-only as an earlier comment implied).
- Proved the full pipeline end-to-end with the REAL (unmocked) `claim_eval_job` → `_claim_tier3_derived` selection routed into one `_full_drain_tick`: a lichess backlog game is selected, drained through the 174-06 unified pass, gets a `game_best_moves` row at its out-of-book played==best ply (while a sub-margin ply correctly yields none — the GEMS-02 gate stays selective), keeps its stored lichess %evals byte-for-byte unchanged, and afterward no longer matches the backfill predicate (self-termination, checked directly via SQL against the specific game_id).
- Proved double-claim idempotency: two picks of the same backlog game across two ticks upsert on `(game_id, ply)` rather than duplicating.
- Verified against the real dev DB (read-only, no reset): the broadened predicate identifies 3,862 eligible backlog games vs the old predicate's 567 (out of 4,539 total lichess-eval games, 677 already fully covered), and `EXPLAIN` confirms the planner uses the new index.

## Task Commits

Each task was committed atomically:

1. **Task 1: ES-weighted backfill selection for lichess-eval games lacking best-move coverage** - `88cf3486` (feat)
2. **Task 2: Route backfill picks through the 174-06 pass + supporting partial index; prove self-termination** - `bb4dec9a` (feat)

## Files Created/Modified

- `app/services/eval_queue_service.py` - `_claim_tier3_derived`'s residual fallback predicate broadened (`full_evals_completed_at IS NULL` → `full_pv_completed_at IS NULL`); docstrings/comments updated to describe the broadened best-move-backfill intent
- `app/models/game.py` - `Index("ix_games_pv_backfill_pending", ...)` renamed to `ix_games_lichess_pv_backfill_pending` with the broadened predicate, matching the migration (keeps `alembic check` drift-free)
- `alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py` - drops the superseded `ix_games_pv_backfill_pending`, creates `ix_games_lichess_pv_backfill_pending`
- `tests/services/test_eval_queue.py` - `_insert_game` gained a `full_pv_completed_at` param; 8 new tests in `TestTier3Lottery` covering the broadening
- `tests/services/test_full_eval_drain.py` - new `TestLichessBestMoveBackfill` class: end-to-end real-selection drain test + double-claim idempotency test

## Decisions Made

See `key-decisions` in frontmatter. Summary: dropped the now-dead superseded index in the same migration rather than leaving permanent dead weight; verified self-termination via a direct SQL predicate check on the specific game_id (deterministic, independent of shared-test-DB state) rather than re-running the lottery; simulated the double-claim race via a mocked claim forcing the same game_id across two ticks, matching the exact scenario the module's own "D-7 residual-duplicate acceptance" docstring describes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The old `ix_games_pv_backfill_pending` index was declared in `app/models/game.py`, not migration-only as its own comment claimed**
- **Found during:** Task 2, running `uv run alembic check` after creating the migration
- **Issue:** `alembic check` flagged drift (`remove_index ix_games_lichess_pv_backfill_pending`, `add_index ix_games_pv_backfill_pending`) because the model's `__table_args__` still declared the OLD index under its old name/predicate — contrary to a nearby comment on a *different* index claiming these partial indexes are "migration-only." Left unfixed, this would have caused every subsequent `alembic revision --autogenerate` to propose reverting the new index and recreating the old one.
- **Fix:** Updated the `Index(...)` declaration in `app/models/game.py` to `ix_games_lichess_pv_backfill_pending` with the broadened predicate, matching the migration exactly.
- **Files modified:** `app/models/game.py`
- **Verification:** `uv run alembic check` reports "No new upgrade operations detected" after the fix; confirmed via a full `alembic downgrade -1` / `upgrade head` round-trip.
- **Committed in:** `bb4dec9a` (Task 2 commit)

**2. [Rule 1 - Bug] Superseded index left as permanent dead weight**
- **Found during:** Task 2, while designing the migration
- **Issue:** The pre-existing `ix_games_pv_backfill_pending` (predicate `full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL`) is no longer matched by any query after Task 1's broadening — every lichess-eval game reaching this predicate today is also caught by the new `full_pv_completed_at IS NULL` predicate, and the reverse is not true, so the old index would sit unused indefinitely.
- **Fix:** Dropped `ix_games_pv_backfill_pending` in the same migration that creates the replacement index (with a symmetric `downgrade()`).
- **Files modified:** `alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py`
- **Verification:** `uv run alembic upgrade head` / `downgrade -1` / `upgrade head` round-trip succeeds; `EXPLAIN` confirms the new index is used by the planner for the broadened predicate.
- **Committed in:** `bb4dec9a` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — direct, necessary consequences of the Task 1 predicate broadening; no scope creep beyond the migration/model files the plan already listed)
**Impact on plan:** Both fixes were required for the migration to be schema-consistent and non-drifting; neither touched files outside the plan's declared `files_modified` scope.

## Issues Encountered

None beyond the deviations above. The plan's stated test path `tests/services/test_eval_queue_service.py` does not exist — the residual-fallback/lottery tests actually live in `tests/services/test_eval_queue.py` (confirmed by reading the existing `TestTier3Lottery::test_tier3_residual_fallback` test before extending it); used the real path.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 176 (general corpus backfill) can build on this precedent: an existing lottery rung broadened via a superset-population predicate change is the established pattern for opportunistic, self-terminating backfills with no operator script and no completion deadline.
- The dev-DB snapshot (3,862 broadened-backlog lichess games) gives Phase 176 planning a concrete starting point for how much of the corpus this plan's rung will have already drained by the time that phase starts.

---
*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Completed: 2026-07-16*

## Self-Check: PASSED
- FOUND: alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py
- FOUND: app/services/eval_queue_service.py
- FOUND: app/models/game.py
- FOUND: tests/services/test_eval_queue.py
- FOUND: tests/services/test_full_eval_drain.py
- FOUND: 88cf3486 (Task 1 commit)
- FOUND: bb4dec9a (Task 2 commit)
