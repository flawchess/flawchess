---
phase: 259-facepalm-first-principles-refit
plan: 12
subsystem: release
tags: [facepalm, release, switch, d-11, d-15, d-16, d-18, jit]

requires:
  - phase: 259-11
    provides: "readiness gate held, covering index on prod, D-15 decision (both cuts 0.7)"
provides:
  - "Switch release live on prod: server 8e90f094, schema e2f6a8b0d259"
  - "FACEPALM_SCORE_MIN 0.7 and FACEPALM_STATS_MIN 0.7 in the code, constants pinned by tests"
  - "reports/blunder-check/facepalm-jit-259.md, D-18 decision: keep"
  - "benchmark DB at e2f6a8b0d259 with the covering index"
affects: [259-13, 259-14, 259-15]

actuals:
  tasks: 3
  commits: 3
commits: 3

key-files:
  created:
    - reports/blunder-check/facepalm-jit-259.md
  modified:
    - app/services/blunder_check_rules.py
    - tests/scripts/test_fit_facepalm.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_facepalm_owner_fixtures.py
    - CHANGELOG.md

key-decisions:
  - "Owner go-ahead for the switch release: \"Ship the switch\", 2026-11-22"
  - "D-18 decision: keep (disable_jit_for_transaction stays). Comparison statement: JIT on 287.2 ms against 253.1 ms off, ratio 1.13, above the 1.05 rule; counts 195.6 against 188.4, ratio 1.04."
  - "Frontend untouched: FACEPALM_STATS_MIN did not move, FACEPALM_HIGH_CUTOFF stays 70; nothing in the frontend pins the drill cut"
---

# Phase 259 Plan 12: Switch Release Summary

**The switch is live: every user's facepalm score now comes from the first-principles inputs with the drill cut at 0.70, and the JIT measurement says keep JIT off for the facepalm readers.**

## Performance

- **Executed by:** an executor for Task 1, the orchestrator for Tasks 2 and 3
- **Completed:** 2026-11-22
- **Tasks:** 3/3

## Task 1: constants, pins, changelog, gate

- `a7041316c` feat(259-12): `FACEPALM_SCORE_MIN` 0.7 with a 259 D-15 comment (254 and 256 history kept); the constants block comment names the 2026-11-22 TSV, fit report and decision date; the six coefficients are unchanged and equal the fit report's "## Constants" block.
- Tests: `test_shipped_constants_reproduce_from_the_committed_features` (new), `test_window_14_is_not_selected_by_the_shipped_model` (re-added), `test_owner_fixtures_stay_on_the_accepted_side_of_the_cut` (new, both fixtures below the cut), window-14 constants test re-pointed to the 2026-11-22 TSV, `test_known_d04_constants` pins 0.7. In `test_facepalm_stats_min_is_the_high_preset_cut` the assertion `stats_min != FACEPALM_SCORE_MIN` was dropped (both cuts are 0.7 now; they stay separate constants).
- `8164f4e4d` docs(259-12): the D-16 CHANGELOG bullet under `[Unreleased]` / `### Changed`.
- Frontend: `facepalm.ts` and `gapBar.test.ts` untouched (stats cut unchanged, no frontend pin of the drill cut).
- Gate exit codes: ruff format 0 (no diffs), ruff check 0, ty 0, analysis ty 0, function size 0, `uv run pytest -n auto -x` 0 (6919 passed, 8 skipped), frontend lint 0, build 0, test 0, knip 0. Dev status for user 28: `user_blunders_with_score=10241 user_blunders_qualifying=3109`.
- Serial suite `uv run pytest -x` (orchestrator): 0, 6919 passed, 8 skipped in 394.44 s.

## Task 2: readiness re-check, release, prod verification

- Readiness re-check right before the go-ahead: `reply_pending_games=0`, `reply_residue_losing=0`, `line_pending_games=0`; `build_facepalm_inputs_index.py --db prod --check-only` exit 0 (valid, definition equals the expected text). `git branch --merged main | grep -c facepalm-prelim-bands` prints 0.
- Shown to the owner before the go-ahead: 776,783 qualifying user blunders at 0.70 (972,755 under the old score at 0.50); median 414 usable windows per user; 84 of 601 users under 50 own windows (68 at 0.50), rendered from the cached prod sample at threshold 0.7.
- Owner go-ahead: "Ship the switch", 2026-11-22.
- SW cycle closed: squash commit `03a935bf7` on main (tree identical to the phase branch), phase branch deleted, main pushed, `0 0` against origin.
- Deploy via the /deploy flow: PR #498, CI green without fixes, squash-merged as `8e90f0941`, `bin/deploy.sh` finished 2026-11-22T12:09Z, server at `8e90f094`, forward-port pushed (`2efa228c6`).
- Prod after the deploy: `alembic_version` `e2f6a8b0d259`, `indisvalid` true, site HTTP 200, backend up. `--status --mode spread`: `user_blunders_total=2365168 user_blunders_with_score=2209621 user_blunders_qualifying=776783` (plan 11's switched-code count was 2,209,608 scored).
- Benchmark DB: `bin/benchmark_db.sh start` applied `e2f6a8b0d259`, index valid; nothing listening on :8001.
- Sentry: no issue first seen in the two hours up to a few minutes after the deploy; re-checked at the end of the phase.

## Task 3: D-18 JIT measurement

Report: `reports/blunder-check/facepalm-jit-259.md` (`3fb40e94a` on main). User 95, read-only, one connection, four runs per setting.

| Statement | jit off warm median | jit on warm median | ratio |
|---|---|---|---|
| counts | 188.4 ms | 195.6 ms | 1.04 |
| comparison | 253.1 ms | 287.2 ms | 1.13 |

Both statements read `game_flaws` through `Index Only Scan using ix_game_flaws_facepalm_inputs` with JIT on and off. `Heap Fetches: 90021` (pages not yet all-visible after the backfill; autovacuum will reduce it).

**decision: keep.** Plan 14 leaves `disable_jit_for_transaction` and its callers in place.

## Task Commits

1. `a7041316c` feat(259-12): drill cut 0.70, constants confirmed and pinned by tests
2. `8164f4e4d` docs(259-12): D-16 changelog bullet
3. `3fb40e94a` docs(259-12): D-18 JIT re-measure (on main)

The first two are inside the SW squash `03a935bf7`.

## Deviations from Plan

- The serial suite ran in the orchestrator, not in the executor.
- The JIT statements were compiled with a new gitignored script (`temp/facepalm-259/jit_measure.py`): the Phase 257 generator calls `fetch_facepalm_share_counts`, which is now `fetch_facepalm_counts`.
- The Phase 252 feeder was running during the readiness re-check and the JIT measurement (owner-approved exception from plan 11).
- The SW squash also carries one commit from another session (`3dc3c57c3`, a planted seed doc).

## Issues Encountered

- The first JIT run failed on `smallint %% integer`: SQLAlchemy's literal compile doubles `%`. Fixed in the script by un-doubling and using `exec_driver_sql`.

## Known Stubs

None.

## Threat Flags

None. T-259-29: readiness and index re-checked minutes before the deploy. T-259-30: stats cut unchanged. T-259-31: 16 EXPLAIN ANALYZE runs on one read-only connection.

## Next Phase Readiness

Plan 13 starts on a fresh DROP cycle branch off origin/main. D-18 is "keep".

## Self-Check: PASSED
