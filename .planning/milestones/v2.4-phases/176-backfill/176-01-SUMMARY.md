---
phase: 176-backfill
plan: 01
subsystem: api
tags: [postgres, alembic, eval-queue, es-lottery, gems-detection, eval-drain, maia]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    provides: "game_best_moves table + _build_best_move_candidates / apply_completion_decision write choke-point that this phase's guardrail and lottery rung build on"
  - phase: 174-07
    provides: "Precedent pattern for an opportunistic self-terminating backfill lottery + partial-index alembic-check drift lesson"
provides:
  - "best_moves_completed_at TIMESTAMPTZ column on games + ix_games_bestmove_backfill_pending partial index (D-01/D-04)"
  - "maia_engine.is_maia_available() public accessor + Maia-absent stamping guardrail in apply_completion_decision (D-01 correctness requirement)"
  - "New tier-4b _claim_tier4_bestmove ES weighted lottery rung + BEST_MOVE_BACKFILL_ENABLED gate (D-02/D-03/D-05)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Independent completion-marker guardrail signal (maia_engine.is_maia_available()) decoupled from candidate-row count, since the underlying candidate builder returns [] for both 'ran, found nothing' and 'absent' cases"
    - "New parallel lottery rung (tier-4b) mirroring an existing rung's ES two-stage shape rather than broadening the existing rung's predicate, to keep worker-offloadable and backend-only backfill populations orthogonal"

key-files:
  created:
    - alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py
  modified:
    - app/models/game.py
    - app/models/eval_jobs.py
    - app/core/config.py
    - app/services/maia_engine.py
    - app/services/eval_apply.py
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py
    - tests/services/test_full_eval_drain.py

key-decisions:
  - "TIER_BESTMOVE_BACKFILL constant added a task early (Task 3, not Task 4) to unblock Task 3's drain-tick tests without a forward dependency on Task 4's lottery rung — ClaimedJob.tier is inert downstream in _full_drain_tick, so this had zero behavioral impact on Task 3's verification"
  - "Guardrail test isolates the availability signal from candidate-row production by mocking score_move to succeed while forcing maia_engine._session to None — proving the stamp is gated by is_maia_available(), not by best_move_rows being non-empty (mutation-test-style negative assertion per MEMORY.md)"
  - "Reused TIER4_*_HALF_LIFE_DAYS / TIER4_*_WEIGHT_FLOOR / GAME_TC_WEIGHTS unchanged for the new rung rather than introducing BEST_MOVE_*-specific tunables, per CONTEXT.md's stated default"

requirements-completed: [BACK-01]

coverage:
  - id: D1
    description: "best_moves_completed_at column + ix_games_bestmove_backfill_pending partial index added, migration round-trips cleanly (up/down/up) with alembic check reporting no drift; D-04 one-time stamp populates existing game_best_moves coverage"
    requirement: BACK-01
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic check"
        status: pass
    human_judgment: false
  - id: D2
    description: "maia_engine.is_maia_available() + _mark_best_moves_completed guardrail: best_moves_completed_at stays NULL when Maia is absent (negative assertion) and stamps when a session is present (positive), independent of best_move_rows row count"
    requirement: BACK-01
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_maia_absent_never_stamps_best_moves_completed_at"
        status: pass
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_backfill_pick_drains_and_stamps_best_moves_completed_at"
        status: pass
    human_judgment: false
  - id: D3
    description: "_claim_tier4_bestmove picks a PV-complete, best-move-incomplete, non-lichess-eval, non-guest game via the ES two-stage lottery; excludes guests, PV-incomplete games, already-stamped games, and lichess-eval games (D-03 boundary)"
    requirement: BACK-01
    verification:
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill (9 tests: null_pick_on_empty_pool, picks_eligible_game, excludes_guests, excludes_pv_incomplete, excludes_already_stamped, excludes_lichess_eval, dispatch_via_claim, gated_off, claimed_job_fields)"
        status: pass
    human_judgment: false
  - id: D4
    description: "claim_eval_job dispatches TIER_BESTMOVE_BACKFILL only after tier-3 AND tier-4-blob both return None, gated independently by BEST_MOVE_BACKFILL_ENABLED (checked before the DB round-trip) in addition to EVAL_AUTO_DRAIN_ENABLED (D-05)"
    requirement: BACK-01
    verification:
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill::test_dispatch_via_claim"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill::test_gated_off"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full backend suite green after all changes (3412 passed, 21 pre-existing skips); ty check clean apart from the 3 pre-existing onnxruntime/numpy isolated-group import errors (confirmed unrelated via git stash comparison); ruff format/check clean"
    verification:
      - kind: other
        ref: "uv run pytest -n auto"
        status: pass
      - kind: other
        ref: "uv run ty check app/ tests/"
        status: pass
    human_judgment: false
  - id: D6
    description: "SC3 coverage-growth observation (snapshot-diff of game_best_moves count over time) — opportunistic, ES-lottery-driven, no ETA/100% promise per the tier-4 backfill-measurement precedent"
    requirement: BACK-01
    verification: []
    human_judgment: true
    rationale: "Manual-Only per 176-VALIDATION.md — requires BEST_MOVE_BACKFILL_ENABLED=true in a running environment with idle drain over time; not a pass/fail automated test at merge time. BEST_MOVE_BACKFILL_ENABLED stays False in this merge (D-05) — enabling in prod is a separate, deliberately observed flag flip."

duration: ~20min
completed: 2026-07-17
status: complete
---

# Phase 176 Plan 01: Backfill Summary

**Backend-only tier-4b spare-capacity ES lottery (`_claim_tier4_bestmove`) that opportunistically drains the already-analyzed chess.com-dominant corpus through the Phase 174 best-move pipeline, gated by a dedicated `BEST_MOVE_BACKFILL_ENABLED` kill-switch and a Maia-absence guardrail that prevents any game from being permanently locked out of the lottery.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 4
- **Files modified:** 8 (1 created: migration; 7 modified: 2 models, config, maia_engine, eval_apply, eval_queue_service, 2 test files)

## Accomplishments

- Added `best_moves_completed_at` TIMESTAMPTZ completion marker on `games` + `ix_games_bestmove_backfill_pending` partial index (byte-identical predicate in `app/models/game.py` and the migration, per the 174-07 alembic-check drift lesson), plus a D-04 one-time stamp for games that already have `game_best_moves` coverage. Migration round-trips cleanly (up/down/up) with `alembic check` reporting no drift.
- Added `maia_engine.is_maia_available()` (cheap `_session is not None` check) and threaded a new `maia_available: bool` parameter through `apply_completion_decision`, gating a new `_mark_best_moves_completed` stamp on Path A/C ONLY when Maia actually ran — never inferred from `best_move_rows` being non-empty, since `_build_best_move_candidates` returns `[]` for both "Maia ran, zero candidates" and "Maia absent" (structurally unsound as an availability signal). Proven by a dedicated negative-assertion guardrail test (`maia_engine._session = None` + `score_move` mocked to SUCCEED still leaves `best_moves_completed_at` NULL) alongside its positive counterpart.
- Added `_claim_tier4_bestmove` — a near-verbatim copy of `_claim_tier4_blob`'s two-stage ES weighted (user → game) lottery reusing the existing `TIER4_*` constants and `GAME_TC_WEIGHTS` unchanged — with the predicate `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL AND lichess_evals_at IS NULL` in both stages. The `lichess_evals_at IS NULL` clause is load-bearing (D-03): it keeps this rung's population disjoint from 174-07's residual lichess-eval-game fallback.
- Wired the new rung into `claim_eval_job`'s bundled `scope=None` ladder, dispatched only after tier-3 AND tier-4-blob both return `None`, gated by a new dedicated `BEST_MOVE_BACKFILL_ENABLED` setting (default `False`) checked in addition to `EVAL_AUTO_DRAIN_ENABLED` and BEFORE the DB round-trip (avoids wasted queries per idle tick when disabled). `ClaimedJob.is_lichess_eval_game=False` is correct by construction since the predicate structurally excludes lichess-eval games.
- 11 new tests: 9 in `TestTier4bBestMoveBackfill` (lottery predicate correctness, guest/PV-incomplete/already-stamped/lichess-eval exclusions, dispatch ordering, gate independence, claimed-job fields) and 2 in `TestBestMoveBackfill` (end-to-end drain + self-termination, and the Maia-absent guardrail negative assertion).
- Full backend suite green (3412 passed, 21 pre-existing skips), `ty check` clean apart from 3 pre-existing `onnxruntime`/`numpy` isolated-group import errors (confirmed unrelated to this phase via a `git stash` comparison), `ruff format`/`check` clean.

## Task Commits

Each task was committed atomically:

1. **Task 1 (Wave 0): Test scaffolding — extend _insert_game, stub tier-4b + backfill test classes incl. the Maia-absent guardrail negative assertion** - `3c34f002` (test)
2. **Task 2: Migration + model column + partial index + D-04 one-time stamp** - `8f122e0a` (feat)
3. **Task 3: Maia-absent stamping guardrail — is_maia_available() + best_moves_completed_at stamp at the single choke-point** - `7de36d83` (feat)
4. **Task 4: Config gate + TIER_BESTMOVE_BACKFILL constant + _claim_tier4_bestmove rung wired into claim_eval_job; full quick suite green** - `661da61d` (feat)

_Note: TIER_BESTMOVE_BACKFILL was actually added in Task 3's commit (not Task 4's) — see Deviations below._

## Files Created/Modified

- `alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py` - column + partial index + D-04 one-time stamp
- `app/models/game.py` - `best_moves_completed_at` column + `ix_games_bestmove_backfill_pending` index declaration
- `app/models/eval_jobs.py` - `TIER_BESTMOVE_BACKFILL: int = 5` constant + updated tier comment block
- `app/core/config.py` - `BEST_MOVE_BACKFILL_ENABLED: bool = False` (D-05 independent gate)
- `app/services/maia_engine.py` - `is_maia_available()` public accessor
- `app/services/eval_apply.py` - `_mark_best_moves_completed` + `maia_available` param threaded through `apply_completion_decision`; `apply_full_eval` computes `maia_available = maia_engine.is_maia_available()`
- `app/services/eval_queue_service.py` - `_claim_tier4_bestmove` + tier-4b rung wired into `claim_eval_job`'s bundled ladder
- `tests/services/test_eval_queue.py` - `_insert_game` gained `best_moves_completed_at` kwarg; `TestTier4bBestMoveBackfill` (9 tests)
- `tests/services/test_full_eval_drain.py` - `TestBestMoveBackfill` (2 tests: end-to-end drain + self-termination, Maia-absent guardrail)

## Decisions Made

See `key-decisions` in frontmatter. Summary: moved the `TIER_BESTMOVE_BACKFILL` constant addition from Task 4 to Task 3 to avoid a forward dependency in Task 3's own verification tests (the constant is inert on `ClaimedJob` downstream, so this had no behavioral effect); isolated the guardrail signal from candidate-row production in the test by mocking `score_move` to succeed while forcing `maia_engine._session` to `None`; reused the existing `TIER4_*` constants unchanged for the new rung per CONTEXT.md's stated default.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] TIER_BESTMOVE_BACKFILL constant needed one task earlier than planned**
- **Found during:** Task 3, running the guardrail tests (`tests/services/test_full_eval_drain.py::TestBestMoveBackfill`)
- **Issue:** The plan's Task 3 tests use `ClaimedJob(tier=TIER_BESTMOVE_BACKFILL, ...)` to route a mocked claim through the drain tick, but `TIER_BESTMOVE_BACKFILL` was planned to be added in Task 4. Running Task 3's verify command as written would fail on an `ImportError` for a symbol Task 4 hadn't created yet.
- **Fix:** Added `TIER_BESTMOVE_BACKFILL: int = 5` to `app/models/eval_jobs.py` as part of Task 3's commit (a single, side-effect-free constant — `ClaimedJob.tier` is inert downstream in `_full_drain_tick`, only consumed meaningfully by `tests/services/test_eval_queue.py`'s lottery-dispatch tests, which still exercise it correctly in Task 4). Task 4 did not re-add the constant, only the config gate, the lottery function, and the dispatch wiring.
- **Files modified:** `app/models/eval_jobs.py`
- **Verification:** Task 3's guardrail tests pass (`tests/services/test_full_eval_drain.py::TestBestMoveBackfill tests/services/test_maia_engine.py -x -q` → 6 passed, 2 skipped); Task 4's full quick suite and `uv run pytest -n auto` both green afterward.
- **Committed in:** `7de36d83` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — a plan task-ordering wrinkle, not a design or correctness issue; no scope creep, no files touched beyond what the plan already listed for the constant)
**Impact on plan:** Purely sequencing — same total code shipped, same task boundaries in spirit (constant vs. lottery-rung logic), just committed one task earlier.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required. `BEST_MOVE_BACKFILL_ENABLED` stays `False` by default; enabling it in prod is a deliberate, separately-observed operational step (D-05), not part of this merge.

## Next Phase Readiness

- Phase 176 was the final phase of the v2.4 Backend Gem & Great Detection milestone's dependency graph (wave B, alongside Phase 175) — both Phase 175 (board + Library-filter consumption) and this phase depend only on Phase 174, not on each other.
- SC3 (coverage-growth observation) is left as a manual, ongoing operational check once `BEST_MOVE_BACKFILL_ENABLED` is flipped on in prod — no code changes needed for that step, just a config flag flip after observing backend RSS/CPU (mirrors 174 D-03b's posture).

---
*Phase: 176-backfill*
*Completed: 2026-07-17*

## Self-Check: PASSED
- FOUND: alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py
- FOUND: app/models/game.py
- FOUND: app/models/eval_jobs.py
- FOUND: app/core/config.py
- FOUND: app/services/maia_engine.py
- FOUND: app/services/eval_apply.py
- FOUND: app/services/eval_queue_service.py
- FOUND: tests/services/test_eval_queue.py
- FOUND: tests/services/test_full_eval_drain.py
- FOUND: 3c34f002 (Task 1 commit)
- FOUND: 8f122e0a (Task 2 commit)
- FOUND: 7de36d83 (Task 3 commit)
- FOUND: 661da61d (Task 4 commit)
