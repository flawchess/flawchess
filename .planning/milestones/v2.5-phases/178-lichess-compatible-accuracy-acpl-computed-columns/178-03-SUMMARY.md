---
phase: 178-lichess-compatible-accuracy-acpl-computed-columns
plan: 03
subsystem: database
tags: [chess, stockfish, lichess, accuracy, acpl, eval-apply, python]

# Dependency graph
requires:
  - phase: 178-01
    provides: "Migration adding *_imported columns, canonical white_accuracy/black_accuracy/white_acpl/black_acpl NULLed and repurposed for the uniform computed formula"
  - phase: 178-02
    provides: "app/services/accuracy_acpl.py — compute_game_accuracy_acpl(positions) shared compute path"
provides:
  - "Live-hook wiring in app/services/eval_apply.py::_classify_and_fill_oracle — the four canonical columns (white_accuracy/black_accuracy/white_acpl/black_acpl) are written atomically with oracle counts on every full-eval completion (server drain + remote atomic-submit)"
affects: [178-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single compute call reuses the already-loaded positions list — zero extra query — and its result is folded into the existing atomic UPDATE .values() call rather than a second statement, guaranteeing torn-write-free commits (T-178-03-T)"

key-files:
  created: []
  modified:
    - app/services/eval_apply.py
    - tests/services/test_full_eval_drain.py

key-decisions:
  - "Compute call placed immediately after the counts_white/counts_black computation and the coverage-gate defensive return, right before the games_table UPDATE — keeps the None short-circuit local to the four accuracy/acpl keys via a ternary-per-key pattern rather than branching the whole UPDATE, so the oracle-count keys are visually and structurally unchanged (T-178-03-I)."
  - "Hole test uses a DIRECT call to _classify_and_fill_oracle (not a full drain tick) — the full drain tick's own SEED-045 completion-stamp gate ties full_evals_completed_at to THIS PASS's engine-call failures, which is a different hole concept than the accuracy module's interior-eval Complete-Sequence Gate over the game_positions table's CURRENT state. A direct call cleanly demonstrates D-03 (stamp independent of this function; compute's own gate is authoritative) without fighting the drain tick's unrelated stamping logic."
  - "Hole-free test reuses the exact _SIX_PLY_PGN + _blunder_eval_sequence() fixture from the pre-existing TestOracleCounts, extending it with accuracy/acpl range assertions — no new DB harness introduced, per plan direction."

requirements-completed: []

coverage:
  - id: D1
    description: "T-178-03-T: the four canonical columns ride the SAME atomic UPDATE .values() as oracle counts — never a second statement"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestAccuracyAcplHook::test_accuracy_acpl_filled_after_hole_free_drain_tick"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live hook reuses the already-loaded positions list — zero extra query — calling the exact same compute_game_accuracy_acpl the backfill (Plan 04) will use"
    verification:
      - kind: unit
        ref: "app/services/eval_apply.py::_classify_and_fill_oracle (code review — single compute call over the existing `positions` variable)"
        status: pass
    human_judgment: false
  - id: D3
    description: "T-178-03-I / D-03: a compute None result (interior hole) leaves all four columns NULL while the oracle-count UPDATE still executes and any pre-existing completion stamp is untouched"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestAccuracyAcplHook::test_accuracy_acpl_null_on_interior_hole"
        status: pass
    human_judgment: false
  - id: D4
    description: "Oracle-count keys and the coverage-gate `if \"reason\" in ...` early-return are structurally unchanged"
    verification:
      - kind: unit
        ref: "app/services/eval_apply.py::_classify_and_fill_oracle (diff review) + full backend suite green"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-18
status: complete
---

# Phase 178 Plan 03: Live-Hook Accuracy/ACPL Wiring Summary

**Wired the Plan 02 shared compute path into `eval_apply.py::_classify_and_fill_oracle`'s existing atomic `UPDATE games` statement, so every full-eval completion (server drain + remote atomic-submit) now writes lichess-compatible `white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl` atomically with oracle counts, correctly leaving them NULL on an interior eval hole.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-18T09:04Z (STATE.md handoff from 178-02)
- **Completed:** 2026-07-18T09:12Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `app/services/eval_apply.py::_classify_and_fill_oracle`: imports `compute_game_accuracy_acpl` from Plan 02's `accuracy_acpl.py`, calls it once on the already-loaded `positions` list (zero extra query), and folds its result into the existing atomic `UPDATE games ... .values(...)` call that also writes oracle counts — the four new keys (`white_accuracy`, `black_accuracy`, `white_acpl`, `black_acpl`) each resolve to the compute's field when non-None, else `None`, via a per-key ternary so a partial (e.g. 1-move-game) result correctly nulls only the missing color's fields.
- Oracle-count keys, the `if "reason" in flaw_result: return` coverage gate, and the `positions` load are all byte-for-byte unchanged — verified by diff review and the full 3505-test backend suite passing unmodified elsewhere.
- No second UPDATE, no new query, no hook added at lichess import — the single shared seam (both drain and remote atomic-submit converge on `_classify_and_fill_oracle` via `apply_full_eval`) covers every completion route per the plan's single-path guarantee.
- Two new integration tests in `tests/services/test_full_eval_drain.py::TestAccuracyAcplHook` (selectable via `-k accuracy`): a hole-free full drain tick proving the four columns are non-NULL, in range, and land atomically with `full_evals_completed_at`; and a direct `_classify_and_fill_oracle` call with a hand-placed interior eval hole (ply 2 NULL) proving the compute's Complete-Sequence Gate authoritatively nulls all four columns while the oracle-count UPDATE still executes and a pre-existing completion stamp is left untouched (D-03).

## Task Commits

Each task was committed atomically:

1. **Task 1: Call the shared compute and add the four canonical columns to the atomic UPDATE** - `6f5aa9cc` (feat)
2. **Task 2: Drain-tick integration test — canonical columns filled (and NULL on a hole)** - `53e257c4` (test)

## Files Created/Modified
- `app/services/eval_apply.py` - Added `compute_game_accuracy_acpl` import; the four canonical accuracy/acpl keys now ride the existing atomic oracle-count `UPDATE games` statement in `_classify_and_fill_oracle`.
- `tests/services/test_full_eval_drain.py` - New `TestAccuracyAcplHook` class: hole-free drain-tick fill test + interior-hole direct-call NULL test.

## Decisions Made
- **Compute call placement:** immediately after `counts_white`/`counts_black` are computed and the coverage-gate defensive `return` (which can only trip when `classify_game_flaws`'s own identical gate already passed — see the existing "Shouldn't happen... but be defensive" comment), right before the `games_table` UPDATE. Per-key ternaries (`accuracy_acpl_result.white_accuracy if accuracy_acpl_result is not None else None`) keep the None short-circuit scoped to only the four new keys, leaving the oracle-count keys structurally untouched.
- **Hole test uses a direct function call, not a full drain tick:** the drain tick's own SEED-045 completion-stamp logic (`full_eval_attempts`/`failed_ply_count`) gates `full_evals_completed_at` on THIS PASS's engine-call failures — a different concept from the accuracy module's Complete-Sequence Gate, which inspects the CURRENT `game_positions` table state regardless of how it got there. Forcing a hole through the drain tick's engine mock would either fail to stamp completion at all (contradicting the D-03 scenario the plan asks for) or require an intricate missing-gp-row construction to decouple the two gates. A direct call to `_classify_and_fill_oracle` — pre-setting `full_evals_completed_at` and hand-placing one interior NULL position — demonstrates the exact D-03 invariant cleanly: the stamp is untouched by this function, and the compute's own gate is authoritative regardless of any external completion state.
- **Hole-free test reuses `_SIX_PLY_PGN` + `_blunder_eval_sequence()` verbatim** from the pre-existing `TestOracleCounts` class (same fixture, same engine mock sequence), only extending the assertions — no new DB harness, per the plan's explicit instruction.

## Deviations from Plan

None. Plan executed exactly as written: one compute call reusing the loaded `positions`, four keys folded into the existing atomic UPDATE, None short-circuits to NULL for all four columns while oracle counts still write, no second UPDATE, no new import-time hook.

## Issues Encountered

None. `uv run ty check app/ tests/` was zero-error on the first pass; the full backend suite (`uv run pytest -n auto -x`, 3505 tests) passed unmodified elsewhere.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The live half of D-06 (SEED-110) is complete: every game that finishes full-eval analysis going forward gets its uniform lichess-formula accuracy/ACPL written atomically, via the single shared compute path.
- Plan 04 (corpus backfill script) can now call the exact same `compute_game_accuracy_acpl` for the ~718k-game historical backfill, with both the live hook and the backfill sharing zero divergent formula logic.
- No blockers.

---
*Phase: 178-lichess-compatible-accuracy-acpl-computed-columns*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: app/services/eval_apply.py (modified)
- FOUND: tests/services/test_full_eval_drain.py (modified)
- FOUND: .planning/phases/178-lichess-compatible-accuracy-acpl-computed-columns/178-03-SUMMARY.md
- FOUND commit: 6f5aa9cc (feat)
- FOUND commit: 53e257c4 (test)
