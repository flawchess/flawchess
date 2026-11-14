---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 16
subsystem: backend-services
tags: [facepalm-score, maia, post-commit-hook, fingerprint, advisory-lock, tdd]
requires:
  - phase: 254-01
    provides: "line_facts / best_line_facts and LineFacts.material_array / opponent_mate_ply"
  - phase: 254-02
    provides: "R1 storage columns (played_line_material, best_line_material, best_line_mate_ply, maia_best_prob, maia_pre_spread, games.facepalm_pre_completed_at) and facepalm_expr"
  - phase: 254-15
    provides: "FacepalmFacts with best_3 / best_mate_ply / best_prob / pre_spread inputs and the lam-aware twins"
provides:
  - "Hook writes both line arrays and both mate plies for every scorable user blunder (D-09), still dual-writing line_loss_1..9 and facepalm_score"
  - "Hook writes maia_best_prob and maia_pre_spread from the SAME full_policy call as maia_played_prob (D-08), no extra inference"
  - "Six-element FlawFingerprint (best pv and best_move at the flaw ply added) closing T-254-05"
  - "FACEPALM_PRE_COLUMNS, mark_facepalm_pre_completed, four-stamp clear_maia_flaws_completed"
  - "best_move_uci, pre_blunder_spread, MaiaPreStats, MaiaReason best_move_missing"
affects: [254-17, 254-18, facepalm-readers, facepalm-backfill, facepalm-fit]
tech-stack:
  added: []
  patterns:
    - "A second aliased GamePosition outer join at the flaw ply feeds the best line into the shared load/in-lock-re-read SELECT, so the fingerprint stays comparable"
    - "Derived values stay out of the fingerprint (stored_best_prob / stored_pre_spread), same rule as stored_played_prob"
    - "_derive_flaw_values returns a NamedTuple (_FlawValues) instead of a growing positional tuple"
key-files:
  created: []
  modified:
    - app/services/maia_flaw_scoring.py
    - app/services/maia_flaw_stats.py
    - app/repositories/game_flaws_repository.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/test_maia_flaw_stats.py
    - tests/services/maia_fakes.py
key-decisions:
  - "The three new fact columns join FACEPALM_COLUMNS, so spread and line backfill modes also recompute the material arrays and best-line mate ply from the stored lines (they have the board and the fingerprinted best line); the two pre keys are a separate FACEPALM_PRE_COLUMNS tuple written in full mode only"
  - "Best move = first token of the best pv, else best_move, else None (research Pitfall 7); best_line_facts reads best_pv or best_move, so the best-move probability and the best-line facts describe the same move"
  - "maia_pre_spread is stored even when the best move is missing: the two pre inputs are independent, only maia_best_prob is NULL and the reason best_move_missing is counted"
  - "Spread and line modes pass the STORED best prob and pre spread into the dual-written score, so the stored score stays correct once the refit turns those terms on"
requirements-completed: [D-01, D-08, D-09, D-12]
coverage:
  - id: D1
    description: "D-09: the hook stores played_line_material, best_line_material, line_mate_ply and best_line_mate_ply equal to line_facts / best_line_facts on the stored lines (9 slots), with the legacy line_loss columns still written"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_writes_both_line_arrays"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_without_best_line_keeps_best_facts_null"
        status: pass
    human_judgment: false
  - id: D2
    description: "T-254-05: the pv and best_move at the flaw ply are in the fingerprint; a rewrite between read and write gives fingerprint_changed and writes nothing"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_fingerprint_includes_best_line"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-01 / D-12: facepalm_expr(FACEPALM_DRILL_LAMBDA) over the stored facts equals the dual-written stored score within 1e-6, and the stored score is the Phase 250 value"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_stored_score_equals_expression"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_facepalm_tracer_user_blunder_scored_and_three_stamps"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-08: maia_best_prob and maia_pre_spread come from the flaw-position policy call; full_policy is called once per scorable flaw plus once per scorable user blunder"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_writes_pre_inputs"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_pre_inputs_reuse_the_flaw_policy_call"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_stats.py#test_pre_blunder_spread_uniform"
        status: pass
    human_judgment: false
  - id: D5
    description: "Missing or out-of-policy best move: maia_best_prob NULL, best_move_missing counted, best arrays NULL, row still scored on the loss alone"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_best_move_missing_keeps_loss_only_score"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_best_move_outside_the_policy_counts_best_move_missing"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full mode stamps facepalm_pre_completed_at with the other three stamps; clear_maia_flaws_completed clears all four; spread and line rows never carry the pre keys"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_sets_pre_stamp_with_the_others"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_clear_maia_flaws_completed_clears_pre_stamp"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_reclassify_clear_helper_clears_all_four_stamps"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_spread_and_line_rows_never_carry_pre_inputs"
        status: pass
    human_judgment: false
  - id: D7
    description: "Behaviour unchanged (D-12): no reader moved, full backend suite green"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -q (6527 passed, 19 skipped)"
        status: pass
    human_judgment: false
duration: 50 min
completed: 2026-11-14
status: complete
plan_head_before: 7c79541733c96db4aa67c68fc6637473d30cf718
plan_head_after: 55b5a257deec650983e3208336cb16b00a9c106f
commits: 3
actuals:
  tokens: 13800
  tasks: 2
  commits: 3
---

# Phase 254 Plan 16: R1 hook writer for the line facts and the pre-blunder Maia inputs Summary

**The post-commit hook now writes both signed line-material arrays, both mate plies and the two pre-blunder Maia inputs (best-move probability, pre-blunder spread) for every scorable user blunder, under a fingerprint that covers the best line, while the stored score stays the Phase 250 value and equals `facepalm_expr(FACEPALM_DRILL_LAMBDA)`.**

## Performance

- **Duration:** about 50 min (estimate; the start time was not captured)
- **Completed:** 2026-11-14
- **Tasks:** 2 (a tracer and a TDD task)
- **Files modified:** 6 (0 created, 6 modified)

## Accomplishments

- `_flaw_fingerprint_select` adds a second aliased `GamePosition` outer join at the flaw ply (`pv` and `best_move`); `FlawFingerprint` is now `(ply, fen, severity, refutation pv, best pv, best_move)`. Mutating the fingerprint back to four elements makes `test_fingerprint_includes_best_line` fail (both parametrizations), so the test does exercise the new members.
- `_facepalm_values` computes `line_facts` for the played line and `best_line_facts(board, best_pv or best_move)` for the best line, stores `played_line_material` / `best_line_material` (NULL when every slot is unsettled) and `best_line_mate_ply` (the best facts' `opponent_mate_ply`), and keeps dual-writing `line_loss_*`, `line_mate_ply` and `facepalm_score` (lam = `FACEPALM_DRILL_LAMBDA`). The best-move fallback `best_move_uci` follows research Pitfall 7.
- `_derive_flaw_values` takes `maia_best_prob = probs[best_uci]` and `maia_pre_spread = pre_blunder_spread(probs)` from the policy already computed at the flaw position. `test_pre_inputs_reuse_the_flaw_policy_call` pins the full_policy call list to exactly the flaw position and the post-blunder position, so the inference count per game is unchanged.
- Full mode stamps `facepalm_pre_completed_at` with the other three stamps (`mark_facepalm_pre_completed`); `clear_maia_flaws_completed` clears and detects all four. Spread and line modes carry `FACEPALM_COLUMNS` only (now including the three new fact columns) and read `stored_best_prob` / `stored_pre_spread` for the dual-written score.

## Task Commits

1. **Task 1 (tracer): both line arrays and mate plies under a best-line fingerprint** - `2c68261c0` (feat)
2. **Task 2 (TDD RED): pre-blunder inputs, pre stamp and four-stamp clear tests** - `0276127fc` (test)
3. **Task 2 (TDD GREEN): pre-blunder inputs from the flaw policy call, pre stamp, four-stamp clear** - `55b5a257d` (feat)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (the Task 1 tests plus the 251-test related set, `ty`, the function-size gate) before the expansion task; it passed, so expansion continued.

## TDD Gate Compliance

- **RED:** 14 tests failed. The stubs `pre_blunder_spread` / `null_maia_pre_stats` raised `NotImplementedError` and the hook did not yet write the pre keys or the fourth stamp, so the target tests failed on the missing behaviour (the first RED attempt was an ImportError for the not-yet-existing names, so the stubs were added to make the failure semantic). The `gsd_run check tdd-red-evidence` classifier was not run (no TAP/JUnit record captured); the pytest output was inspected by hand.
- **GREEN:** `tests/services/test_maia_flaw_scoring.py` and `tests/services/test_maia_flaw_stats.py` 80 passed; full suite 6527 passed.
- **REFACTOR:** none needed.

## Files Created/Modified

- `app/services/maia_flaw_scoring.py` - second join, six-element fingerprint, `best_move_uci`, best-line facts, `_pre_inputs`, `_stored_pre`, `_FlawValues`, four-stamp `_mark_stamps`, docstrings
- `app/services/maia_flaw_stats.py` - `FacepalmStats` array keys, `MaiaPreStats`, `null_maia_pre_stats`, `pre_blunder_spread`, `best_move_missing`
- `app/repositories/game_flaws_repository.py` - `FACEPALM_COLUMNS` (+3), `FACEPALM_PRE_COLUMNS`, `mark_facepalm_pre_completed`, four-stamp `clear_maia_flaws_completed`
- `tests/services/test_maia_flaw_scoring.py` - `make_game(best_moves=)`, the new tests, the stale-values fixture and the four-stamp clear test
- `tests/services/test_maia_flaw_stats.py` - `pre_blunder_spread` and `null_maia_pre_stats` tests
- `tests/services/maia_fakes.py` - `assert_maia_lane_state` checks the fourth stamp and the pre columns

## Decisions Made

See key-decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests pinned the old key and stamp sets**
- **Found during:** Task 1 and Task 2 (test runs)
- **Issue:** the direct `FlawMaiaInput(...)` construction in `test_target_boards_are_never_mutated` lacked the new required fields; `_STALE_FACEPALM` (compared against `FACEPALM_COLUMNS`) lacked the three new columns; the stamp-clear parametrization and `maia_fakes.assert_maia_lane_state` knew only three stamps.
- **Fix:** added the new fields and columns to those fixtures, renamed `test_reclassify_clear_helper_clears_all_three_stamps` to `..._all_four_stamps` over four stamp columns, and extended `assert_maia_lane_state` to the pre stamp and pre columns.
- **Files modified:** tests/services/test_maia_flaw_scoring.py, tests/services/maia_fakes.py
- **Verification:** 80 passed in the two scoring test files; full suite green.
- **Committed in:** `2c68261c0`, `55b5a257d`

---

**Total deviations:** 1 auto-fixed (blocking test expectations). **Impact on plan:** none; no scope change.

## Issues Encountered

- The per-plan commit ledger could not be written from the worktree (the compound git command is refused), so `plan_head_before` is the dispatch base SHA and `commits: 3` was measured with `git rev-list --count` against it.
- Duration is an estimate (the start time was not captured). `actuals.tokens` is chars/4 over the realized diff of the three commits (55,171 chars).
- The first `uv run pytest -n auto -x` was moved to the background by the 120 s tool timeout; it completed with 6527 passed, 19 skipped.

## Known Stubs

None. (The `NotImplementedError` stubs of the RED commit were replaced in the GREEN commit.)

## Threat Flags

None. T-254-05 mitigated (best pv and best_move at the flaw ply are in the fingerprint re-read under the per-game advisory lock, verified by a mutation check); T-254-06 mitigated (the new columns live in `FACEPALM_COLUMNS` / `FACEPALM_PRE_COLUMNS`, which `flaw_record_to_row` never emits, so the diff/upsert preserves them by omission).

## Next Phase Readiness

New blunders carry both line arrays, both mate plies and the two pre-blunder inputs, and the stored score is unchanged. The backfill modes (a `pre` mode for old games, the sign-flipped copy of `line_loss_*` into `played_line_material`, a post-252 line pass) and the reader switch to `facepalm_expr` are separate plans; `FACEPALM_PRE_COLUMNS` and `mark_facepalm_pre_completed` are ready for a `pre` backfill mode.

## Self-Check: PASSED

Files exist (`app/services/maia_flaw_scoring.py`, `app/services/maia_flaw_stats.py`, `app/repositories/game_flaws_repository.py`, the three test files); commits `2c68261c0`, `0276127fc`, `55b5a257d` are on HEAD. Verified: `uv run pytest -n auto -q` 6527 passed / 19 skipped, `uv run ty check app/ tests/ scripts/` clean, `ruff check .` and `ruff format --check` clean, `check_function_size.py app/ --fail-over-depth 4` clean; acceptance greps (`best_line_facts(`, `def best_move_uci(`, `FACEPALM_PRE_COLUMNS`, `async def mark_facepalm_pre_completed(`, `"best_move_missing"`, `def pre_blunder_spread(`) match.
