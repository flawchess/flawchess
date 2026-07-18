---
phase: 177-worker-side-multipv2-gem-candidates
plan: 03
subsystem: api
tags: [asyncio, sqlalchemy, sentry, eval-drain, tier-4b-backfill]

# Dependency graph
requires:
  - phase: 177-01 (Protocol-v2 schema + lease version gate + second_best wiring)
    provides: "_build_best_move_candidates(source=...) — the generalized fallback source-tagging param"
  - phase: 177-02 (Tier-4b lease/submit pair)
    provides: "_build_bestmove_lease_positions, _eval_of_position_map, _stamp_best_moves_completed_directly, _upsert_best_move_rows"
provides:
  - "_tier4b_minimal_drain_tick — the in-process minimal candidate-only drain path for a claimed TIER_BESTMOVE_BACKFILL game"
  - "_full_drain_tick's tier branch — routes TIER_BESTMOVE_BACKFILL claims away from the full every-ply gather + apply_full_eval reclassify"
affects: [177-04/05 (worker script rung + measurement) — the server-pool drain now contributes tier-4b throughput without a full reclassify tax]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "In-process reuse of a wire-endpoint's server-side reconstruction primitives (Plan 02's _build_bestmove_lease_positions + the Pitfall-1 inverse-shift engine_result_map rebuild) instead of an HTTP round-trip, for a same-process caller (the server-pool drain) that wants the identical minimal write path a remote worker gets via /bestmove-lease + /bestmove-submit"
    - "Conditional second_best_map population (only a real runner-up result is recorded) mirrors the existing _full_drain_tick pattern (line ~816), deliberately letting a failed targeted search fall through to _build_best_move_candidates's own Pitfall-1 fallback rather than special-casing it"

key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py

key-decisions:
  - "_tier4b_minimal_drain_tick does NOT call _apply_bestmove_submit directly (which hardcodes source='tier4b-backfill') — it inlines the same reconstruction + _build_best_move_candidates + _upsert_best_move_rows + _mark_best_moves_completed sequence so it can pass source='drain-local' (D-06), matching the plan's explicit requirement that the drain-local fallback be Sentry-distinguishable from the worker-submit-fallback regression signal"
  - "Rule 2 auto-fix: preserved the Phase 176 D-01 maia_available guardrail (apply_completion_decision's maia_available param) inside the new minimal path — the new path bypasses apply_completion_decision entirely, so without an explicit maia_engine.is_maia_available() check before _mark_best_moves_completed, a Maia-absent backend would incorrectly stamp best_moves_completed_at with zero candidate rows written (row count cannot distinguish 'Maia ran, zero candidates' from 'Maia absent'). Caught by the plan's own pre-existing test_maia_absent_never_stamps_best_moves_completed_at, which failed until this guard was added"
  - "second_best_map is populated conditionally (only when second_cp is not None or second_uci is not None), mirroring the main tick's existing pattern, rather than unconditionally like _apply_bestmove_submit's wire-boundary map — this lets a genuinely failed targeted search for a leased ply fall through to _build_best_move_candidates's own Pitfall-1 fallback (a second, defensive re-search) instead of silently producing a (None, None) runner-up that would always fail the margin gate"
  - "The zero-candidate/over-cap _stamp_best_moves_completed_directly branch is NOT gated on maia_available (matches Plan 02's /bestmove-lease precedent) — when the position-only prefilter already found zero candidates there is nothing Maia could have scored regardless of availability, so stamping is safe self-termination in both cases"

requirements-completed: [DRAIN-01, OBS-01]

coverage:
  - id: D1
    description: "A claimed TIER_BESTMOVE_BACKFILL game runs the minimal candidate-only path: writes game_best_moves + stamps best_moves_completed_at, calls evaluate_nodes_multipv2 EXACTLY twice (only the 2 leased candidate plies), and never calls apply_full_eval"
    requirement: "DRAIN-01"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_full_drain_tick_tier4b_minimal_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "A non-tier-4b claim (tier=3) is unchanged — still runs the full every-ply gather (9 evaluate_nodes_multipv2 calls) + apply_full_eval reclassify"
    requirement: "DRAIN-01"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_non_tier4b_claim_still_takes_full_path"
        status: pass
    human_judgment: false
  - id: D3
    description: "When the minimal drain path's own targeted search returns no usable runner-up for a leased candidate ply, _build_best_move_candidates's Pitfall-1 fallback fires a second engine call and tags the Sentry event source='drain-local'"
    requirement: "OBS-01"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_tier4b_drain_local_fallback_tagged_source"
        status: pass
    human_judgment: false
  - id: D4
    description: "A Maia-absent backend never stamps best_moves_completed_at on the new minimal path, even though score_move is mocked to succeed (guardrail, mutation-test-style negative assertion)"
    requirement: "DRAIN-01"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_maia_absent_never_stamps_best_moves_completed_at"
        status: pass
    human_judgment: false
  - id: D5
    description: "asyncio.gather in _tier4b_minimal_drain_tick never runs inside an AsyncSession scope (CLAUDE.md hard rule)"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestGatherOutsideSession::test_gather_outside_session_tier4b_minimal_path"
        status: pass
    human_judgment: false

# Metrics
duration: 16min
completed: 2026-07-17
status: complete
---

# Phase 177 Plan 03: Tier-aware minimal drain path for tier-4b gem-candidate backfill Summary

**`_full_drain_tick` now branches on `claimed.tier` before the full every-ply gather — a `TIER_BESTMOVE_BACKFILL` pick runs a new `_tier4b_minimal_drain_tick` that reuses Plan 02's candidate-ply reconstruction + Plan 01's source-tagged `_build_best_move_candidates` to write only `game_best_moves` + `best_moves_completed_at`, fixing the documented `_ = tier` no-op.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-07-17T16:24:00Z
- **Completed:** 2026-07-17T16:40:00Z
- **Tasks:** 1
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments
- Added `_tier4b_minimal_drain_tick(game_id, user_id) -> bool` to `app/services/eval_drain.py`: leases candidate plies via Plan 02's `_build_bestmove_lease_positions` (no engine calls), rebuilds `targets` + the inverse-shift `engine_result_map` via the same primitives `_apply_bestmove_submit` uses, runs ONE targeted `asyncio.gather(evaluate_nodes_multipv2)` over exactly those plies (NO session open), delegates to `_build_best_move_candidates(source="drain-local")`, and writes `game_best_moves` + stamps `best_moves_completed_at` in one late write session — never `apply_full_eval`, never `_classify_and_fill_oracle`.
- Wired the tier branch into `_full_drain_tick`: `if tier == TIER_BESTMOVE_BACKFILL: return await _tier4b_minimal_drain_tick(game_id, user_id)` immediately after `job_id` is captured, before the Step-2 PGN load / Step-3 full gather. Removed the `_ = tier` discard (tier is now consumed).
- Preserved the Phase 176 D-01 Maia-availability guardrail inside the new path (Rule 2 auto-fix — see Deviations): `best_moves_completed_at` is stamped only when `maia_engine.is_maia_available()`, matching `apply_completion_decision`'s existing behavior that the new path otherwise bypasses.
- Zero-candidate / over-`MAX_SUBMIT_EVALS` picks stamp `best_moves_completed_at` directly via Plan 02's `_stamp_best_moves_completed_directly` (Pitfall 2 forward-progress), mirroring `/bestmove-lease`'s own behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tier-aware minimal drain path for TIER_BESTMOVE_BACKFILL** - `59065f46` (feat)

_No TDD RED/GREEN split — tests and implementation were committed together, consistent with 177-01/177-02's precedent for small, tightly-scoped `tdd="true"` tasks verified by the same commit's test additions._

## Files Created/Modified
- `app/services/eval_drain.py` - `_tier4b_minimal_drain_tick`; the new tier branch in `_full_drain_tick`; `_ = tier` discard removed; imports added (`TIER_BESTMOVE_BACKFILL`, `MAX_SUBMIT_EVALS`, `maia_engine`, and Plan 01/02's `_build_bestmove_lease_positions` / `_eval_of_position_map` / `_mark_best_moves_completed` / `_stamp_best_moves_completed_directly` / `_upsert_best_move_rows` re-exported from `eval_apply.py`)
- `tests/services/test_full_eval_drain.py` - `TestBestMoveBackfill` updated: `_seed_backfill_game` now seeds `game_positions.best_move` on the candidate plies (the new path's candidacy source is stored data, not a fresh engine pass); `_engine_mock` reduced to the 2 targeted calls the minimal path actually makes. New tests: `test_full_drain_tick_tier4b_minimal_path` (renamed/expanded from the old `test_backfill_pick_drains_and_stamps_best_moves_completed_at`, now also asserting `apply_full_eval` is never called and the engine mock's call count is exactly 2), `test_non_tier4b_claim_still_takes_full_path` (regression: tier=3 still runs the full 9-call gather + calls `apply_full_eval`), `test_tier4b_drain_local_fallback_tagged_source` (D-06 Sentry tag). `test_maia_absent_never_stamps_best_moves_completed_at` updated to the new seeding/mock shape (assertions unchanged). `TestGatherOutsideSession` gained `test_gather_outside_session_tier4b_minimal_path`, the same AST scan targeting the new function.

## Decisions Made
- `_tier4b_minimal_drain_tick` inlines the reconstruction + write sequence rather than calling `_apply_bestmove_submit` verbatim, specifically so it can pass `source="drain-local"` into `_build_best_move_candidates` (`_apply_bestmove_submit` hardcodes `source="tier4b-backfill"` for the wire endpoint) — required by the plan's D-06 Sentry-tagging requirement and the `files_modified` scope (this plan does not touch `eval_apply.py`).
- Rule 2 auto-fix: added the `maia_engine.is_maia_available()` guardrail before `_mark_best_moves_completed` in the new path. This was not called out explicitly in the plan's action text, but the plan's own pre-existing test (`test_maia_absent_never_stamps_best_moves_completed_at`, carried over from Phase 176 Plan 01) encodes it as a correctness requirement, and it failed once the tier branch bypassed `apply_completion_decision` (the sole enforcer of this guardrail in the old full path). Fixed inline before proceeding, per the deviation-rule shared process (fix → verify → continue).
- `second_best_map` in the new path is populated conditionally (only a real runner-up recorded), matching the existing `_full_drain_tick`'s own pattern rather than `_apply_bestmove_submit`'s unconditional wire-boundary map — lets a failed targeted search fall through to `_build_best_move_candidates`'s own Pitfall-1 fallback (used to build the D-06 Sentry-tag test deterministically) instead of silently producing an always-failing margin comparison.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Maia-availability guardrail bypassed by the new tier branch**
- **Found during:** Task 1, while running the plan's own pre-existing `test_maia_absent_never_stamps_best_moves_completed_at` test against the new minimal path.
- **Issue:** The old full path's `apply_completion_decision` gates `_mark_best_moves_completed` on `maia_available` (Phase 176 D-01: a Maia-absent backend must never stamp `best_moves_completed_at`, since `_build_best_move_candidates` returns `[]` for both "Maia ran, zero candidates" and "Maia absent" — row count cannot distinguish them). The new `_tier4b_minimal_drain_tick` bypasses `apply_completion_decision` entirely, so without an explicit check it unconditionally stamped the completion marker regardless of Maia availability.
- **Fix:** Added `maia_available = maia_engine.is_maia_available()` before the write session and gated `_mark_best_moves_completed` on it.
- **Files modified:** `app/services/eval_drain.py`
- **Commit:** `59065f46`

### Test seed/mock updates (not a behavior deviation)

The two pre-existing `TestBestMoveBackfill` tests (added in Phase 176 Plan 01) exercised the OLD full-pipeline behavior: candidacy was derived from a fresh `evaluate_nodes_multipv2` gather's own `best_uci`, not from stored `game_positions.best_move`. Under the new minimal path, candidacy is `_build_bestmove_lease_positions`'s stored-data test — the seed helper had to start setting `best_move` on the candidate rows, and the engine mock's call count/order changed from 9 (full gather + terminal donor) to 2 (only the leased candidate plies). This is expected given the plan's explicit fix, not an unplanned deviation; the resulting assertions are unchanged in intent (ply-6 candidate written, ply-7 sub-margin rejected, self-termination proven).

## Issues Encountered
None beyond the Maia-guardrail gap above (caught and fixed by the plan's own test suite, as designed).

## User Setup Required
None - no external service configuration required. `BEST_MOVE_BACKFILL_ENABLED` stays off by default; this plan changes only the in-process server-pool drain's internal routing for tier-4b claims, which only fire when that flag is on.

## Next Phase Readiness
- The server-pool drain (`run_full_eval_drain`) now contributes real tier-4b throughput without the full-reclassify tax RESEARCH.md's Pitfall 3 documented — this was latent (masked by fallback starvation) and would have surfaced precisely as Phase 177 reduces fallback traffic via the worker-side protocol.
- Plans 04/05 (worker script rung + measurement) are unaffected by this plan's file scope and can proceed independently — this plan only touched `app/services/eval_drain.py` and its test file.

---
*Phase: 177-worker-side-multipv2-gem-candidates*
*Completed: 2026-07-17*

## Self-Check: PASSED

Both modified files (`app/services/eval_drain.py`, `tests/services/test_full_eval_drain.py`) verified present on disk; task commit hash `59065f46` verified present in git log.
