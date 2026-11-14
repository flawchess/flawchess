---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 03
subsystem: backend-operator-tooling
tags: [facepalm-score, maia, backfill, copy-tool, parity-check, tdd]
requires:
  - phase: 254-02
    provides: "R1 storage columns (played_line_material, best_line_material, best_line_mate_ply, maia_best_prob, maia_pre_spread, games.facepalm_pre_completed_at) and facepalm_expr"
  - phase: 254-16
    provides: "FACEPALM_PRE_COLUMNS, mark_facepalm_pre_completed, _pre_inputs / best_move_uci / pre_blunder_spread, the four-stamp clear and the dual-writing hook"
provides:
  - "backfill --mode pre: one pre-blunder Maia inference per user blunder fills maia_best_prob and maia_pre_spread on base-stamped games, stamp = checkpoint, hash-residue shards (D-08, D-20)"
  - "scripts/copy_line_material.py: batched, throttled, resumable sign-flipped copy of line_loss_* into played_line_material (D-09, D-17)"
  - "copy tool --status and read-only --parity (facepalm_expr(FACEPALM_DRILL_LAMBDA) vs the stored score, D-01 / D-12)"
  - "Tests proving line mode writes both arrays and both mate plies and spread mode never writes the pre keys"
affects: [254-06, 254-07, facepalm-readers, facepalm-fit]
tech-stack:
  added: []
  patterns:
    - "A new ScoringMode is one row builder, one _STAMP_COLUMN_BY_MODE entry and one _mark_stamps branch; the shared write path and the stamp/checkpoint selector need no other change"
    - "Operator status/parity functions take an AsyncSession and open their transaction with SET TRANSACTION READ ONLY, so they are read-only even through a writable engine; the CLI additionally opens the engine with default_transaction_read_only"
    - "Copy SQL fragments (pending predicate) are module constants shared by the UPDATE, the dry-run count and --status, so the three cannot disagree"
key-files:
  created:
    - scripts/copy_line_material.py
    - tests/scripts/test_copy_line_material.py
  modified:
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/services/test_maia_flaw_scoring.py
key-decisions:
  - "Pre mode applies the hook's own guards: it writes the two pre keys only when the played move is in the policy (compute_maia_flaw_stats), so a pre-pass row equals what the hook would have written; the values come from the plan 16 _pre_inputs helper, not a copy"
  - "The pre status returns user_blunders_total next to the four counts the plan names, as the denominator for the two with-value counts"
  - "--parity exits non-zero on max_abs_diff above PARITY_MAX_ABS_DIFF only (the plan's contract); cut_side_mismatches is printed for the operator but does not change the exit code"
  - "The parity test injects a real depth-3 loss into the hook-scored row: the Scotch mainline nets 0 material at depth 3, which hid a sign error in the copy (a mutation flipping the slot-3 sign passed until the fixture was fixed)"
patterns-established:
  - "Mutation-prove operator-tool tests: flip the sign in COPY_SQL and drop best_line_material from LINE_ROW_COLUMNS, watch the named tests fail, restore"
requirements-completed: [D-01, D-08, D-09, D-12, D-17, D-20]
coverage:
  - id: D1
    description: "D-08 / D-20: backfill --mode pre fills only maia_best_prob and maia_pre_spread with one pre-blunder inference per user blunder, stamps only facepalm_pre_completed_at, never touches the played prob, reply spread, line facts or stored score; resumable (a second run selects 0 games), hash-residue shards, status counts"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_pre_mode_writes_only_pre_keys_and_stamp"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_pre_mode_resumes"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_pre_mode_shard_partition_disjoint_exhaustive"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_pre_mode_status_counts"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_pre_mode_needs_maia"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_pre_mode_rows_carry_only_pre_keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-09 / D-17: the copy writes [-l1, NULL, -l3, NULL, -l5, NULL, -l7, NULL, -l9] only where the array IS NULL and some line_loss_* is set; rows without values and rows the hook wrote are untouched; a re-run updates 0 rows; resumable by --start-after; slice, stop request and dry run behave"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_copy_flips_sign_into_odd_slots"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_copy_skips_rows_without_values_and_rows_already_written"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_copy_is_idempotent_and_resumable"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_copy_batches_slices_stops_and_reports"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-01 / D-12: the read-only --parity check reports stored/expression/both scored counts, max_abs_diff and cut_side_mismatches, passes on a hook-scored row after the copy, flags a divergent score and a cut-side crossing and exits non-zero"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_status_and_parity"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_parity_flags_a_divergent_score_and_a_cut_side_mismatch"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_copy_line_material.py#test_status_and_parity_transactions_are_read_only"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-09: line mode writes both line arrays, both mate plies and the legacy columns from the stored lines and never a Maia value; spread mode never writes the two pre keys; a best line rewritten between line runs is picked up by a later cutoff"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_mode_writes_both_arrays_both_mate_plies_and_no_maia_value"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_mode_picks_up_a_changed_best_line_with_a_new_cutoff"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_spread_mode_writes_the_arrays_but_leaves_the_pre_keys_untouched"
        status: pass
    human_judgment: false
  - id: D5
    description: "Operator tools are safe to launch on prod: one connection per process, throttle, SIGTERM stops after a batch, resumable (T-254-08, T-254-10); the prod run itself is plans 06 and 07, run by the orchestrator"
    requirement: "D-20"
    verification: []
    human_judgment: true
    rationale: "The prod copy and the 8-shard pre pass are operator runs with prod access (orchestrator, plans 06 and 07); only the tools and their tests are this plan's deliverable"
duration: 75 min
completed: 2026-11-14
status: complete
plan_head_before: 56996ae9be480797a1be511220d65365df594d56
plan_head_after: e9b52b2bceb1a6d7e59d933bf276778bea18d923
commits: 4
actuals:
  tokens: 22200
  tasks: 3
  commits: 4
---

# Phase 254 Plan 03: R1 operator tooling for the pre inputs and the legacy line copy Summary

**A `pre` backfill mode that fills `maia_best_prob` and `maia_pre_spread` on existing rows with one pre-blunder inference per user blunder, plus `scripts/copy_line_material.py` that moves `line_loss_*` into `played_line_material` sign-flipped and can prove `facepalm_expr(FACEPALM_DRILL_LAMBDA)` equals the stored score before R2.**

## Performance

- **Duration:** about 75 min (estimate; the start time was not captured)
- **Completed:** 2026-11-14
- **Tasks:** 3 (a tracer, a TDD task, an auto task)
- **Files:** 6 (2 created, 4 modified)

## Accomplishments

- `ScoringMode` gains `"pre"`: `_pre_row` runs the hook's own board / fen / rating / played-in-policy guards, makes ONE `full_policy` call at the pre-blunder board with the mover's pinned Elo and derives both keys through the plan 16 `_pre_inputs` helper (no duplicated formula). The row carries the PK plus `FACEPALM_PRE_COLUMNS` only, `_mark_stamps` sets only `facepalm_pre_completed_at`, and `GameMaiaScore.pre_scored` counts rows with a non-NULL pre spread.
- `backfill_maia_flaws.py --mode pre`: `_PRE_PENDING_CLAUSE` (`g.facepalm_pre_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL`) is shared by the selector and the status; the mode needs Maia (exit 3 without it); `--status --mode pre` prints `pre_stamped_games`, `pre_pending_games`, `user_blunders_total`, `user_blunders_with_best_prob`, `user_blunders_with_pre_spread`; `pre_scored` / `pre_null` are tallied in the shard report, the progress line and the combined total. The module docstring carries the D-20 prod line (`--mode pre --workers 8 --throttle-ms 50`).
- `scripts/copy_line_material.py`: keyset over `games.id`, one transaction per batch running the Code Example 5 UPDATE (odd slots `-line_loss_N`, even slots NULL, only where the array IS NULL and some value exists), one-connection engine, throttle, SIGTERM / SIGINT stop after the batch, `--start-after`, `--limit-batches`, `--dry-run`, JSON report `copy-line-material-<stamp>.json`. `--status` gives `copy_pending_rows` / `copied_rows`; `--parity` compares the expression with the stored score over user blunders and exits 5 above `PARITY_MAX_ABS_DIFF`.
- Tests prove the line and spread modes carry the new key sets (and the spread mode never the pre keys), and that a best line rewritten between line runs is picked up by a later cutoff.

## Task Commits

1. **Task 1 (tracer): pre mode end to end** - `458e8bf0b` (feat)
2. **Task 2 (TDD RED): failing copy and parity tests** - `18bf801d9` (test)
3. **Task 2 (TDD GREEN): batched sign-flipped copy, status, parity** - `5f38411bb` (feat)
4. **Task 3: line and spread modes carry the new fact keys** - `e9b52b2bc` (test)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (the two named test files, `-n auto`: 112 passed, plus `ty` and the function-size gate) before the expansion task; it passed, so expansion continued.

## TDD Gate Compliance

- **RED:** 10 tests failed against a stub `scripts/copy_line_material.py` (signatures only). Nine failed with `NotImplementedError` from the target functions and the `--help` test failed on the missing flags (`assert '--start-after' in ''`), so every failure was on the planned behaviour, not on an import or fixture fault. The `gsd_run check tdd-red-evidence` classifier was not run (no TAP/JUnit record captured); the pytest output was inspected by hand.
- **GREEN:** `tests/scripts/test_copy_line_material.py` 10 passed. Two mutations proved the tests exercise the behaviour: flipping the slot-3 sign in `COPY_SQL` failed the sign, idempotence and parity tests; dropping `best_line_material` from `LINE_ROW_COLUMNS` failed both new line-mode tests. Both were restored.
- **REFACTOR:** none needed.

## Files Created/Modified

- `app/services/maia_flaw_scoring.py` - `"pre"` ScoringMode, `_pre_row` / `_pre_values`, `_USER_BLUNDER_ROW_BUILDERS`, `_STAMP_COLUMN_BY_MODE`, `_mark_stamps`, `pre_scored`, docstrings
- `scripts/backfill_maia_flaws.py` - `--mode pre`, `_PRE_PENDING_CLAUSE`, `_PRE_STATUS_QUERIES`, `_fetch_pre_status`, `_stamp_counts`, `pre_scored` / `pre_null` tallies, mode docstring (both lines, best-line mate ply, D-20 usage)
- `scripts/copy_line_material.py` - new operator tool (see Accomplishments)
- `tests/scripts/test_backfill_maia_flaws.py` - 7 pre-mode tests, 3 line/spread fact-key tests
- `tests/scripts/test_copy_line_material.py` - 10 tests
- `tests/services/test_maia_flaw_scoring.py` - 4 pre-mode scorer tests

## Decisions Made

See key-decisions. The copy tool imports `readonly_connect_args` from `scripts/blunder_check/sample.py` and the report constants from `backfill_maia_flaws` rather than redefining them (sample.py already imports from the backfill script).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Parity test could not see a sign error in the copy**
- **Found during:** Task 2 (mutation check after GREEN)
- **Issue:** the Scotch hook-scored fixture nets 0 material at depth 3 (`line_loss_3 = 0`), so flipping the slot-3 sign in the copy SQL left `test_status_and_parity` green.
- **Fix:** the helper injects a real depth-3 loss (4) into the hook-scored row and recomputes the stored score with `facepalm_score`; the mutation now fails the parity test too.
- **Files modified:** tests/scripts/test_copy_line_material.py
- **Verification:** mutation re-run, three tests fail; restored, 10 passed.
- **Committed in:** `5f38411bb`

**2. [Rule 3 - Blocking] Test assertions and helper shapes**
- **Found during:** Tasks 1 and 3 (test runs)
- **Issue:** an ORM-object helper hit `DetachedInstanceError` on a deferred column; a seeded REAL value (0.3) round-tripped as 0.30000001192092896.
- **Fix:** the helper selects columns by mapping inside the session; the seed uses the exact binary fraction 0.375.
- **Files modified:** tests/scripts/test_backfill_maia_flaws.py
- **Committed in:** `458e8bf0b`, `e9b52b2bc`

---

**Total deviations:** 2 auto-fixed (1 test bug, 1 blocking test shape). **Impact on plan:** none; no scope change.

## Issues Encountered

- The per-plan commit ledger file was written with the dispatch base SHA by hand (compound git commands are refused in this worktree); `commits: 4` was measured with `git rev-list --count` against it.
- Duration is an estimate (the start time was not captured). `actuals.tokens` is chars/4 over the realized diff of the four commits (88,987 chars of diff text).
- `asyncio.run` inside an async test fails, so the CLI `main()` tests run it through `asyncio.to_thread`.
- Nothing was run against the shared dev database or prod: both tools were exercised through the per-session test databases only. The dev rehearsal is plan 06, the prod runs are plans 06 and 07.

## Known Stubs

None. (The `NotImplementedError` stub of the RED commit was replaced in the GREEN commit.)

## Threat Flags

None. T-254-08 mitigated (the copy SQL and the pre mode clauses are module constants with bound parameters, the mode clause comes from a constant dict); T-254-09 mitigated (`test_copy_flips_sign_into_odd_slots` plus the `--parity` check, both mutation-verified); T-254-10 mitigated in the tools (one connection per process or shard, throttle flags, SIGTERM stops after a batch, resumable by predicate or stamp; launch limits are set in plans 06 and 07).

## Next Phase Readiness

Plan 06 can rehearse the copy on dev (`--dry-run`, then a slice, then `--status`, `--parity`) and plan 07 can run the prod copy and the 8-shard pre pass. Reminder for the operator: run `--parity` after the copy and before R2; the `--mode pre` prod command is in the backfill docstring.

## Self-Check: PASSED

Files exist (`scripts/copy_line_material.py`, `tests/scripts/test_copy_line_material.py`, the four modified files); commits `458e8bf0b`, `18bf801d9`, `5f38411bb`, `e9b52b2bc` are on HEAD. Verified: `uv run pytest -n auto -x` 6551 passed / 19 skipped, `uv run ty check app/ tests/ scripts/` clean, `ruff format` and `ruff check .` clean, `check_function_size.py app/ --fail-over-depth 4` clean; acceptance: `"pre"` in `BACKFILL_MODE_CHOICES`, `facepalm_pre_completed_at IS NULL`, `def _pre_row(`, `-k pre_mode` 7 passed, `played_line_material IS NULL` / `--parity` / `PARITY_MAX_ABS_DIFF: float = 1e-6` in the copy tool, `copy_line_material.py --help` exits 0 and lists `--start-after`, `--status`, `--parity`, `backfill_maia_flaws.py` test asserts best_line_material is written by the line mode and that spread leaves maia_best_prob untouched.
