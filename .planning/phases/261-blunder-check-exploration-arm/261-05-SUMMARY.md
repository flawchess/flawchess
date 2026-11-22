---
phase: 261-blunder-check-exploration-arm
plan: 05
subsystem: blunder-check
tags: [calibration, wilson, readonly-script, facepalm, tdd]

requires:
  - phase: 261-01
    provides: blunder_check_windows.selection_arm and facepalm_score snapshot, WindowArm
provides:
  - scripts/blunder_check/caught_rate.py, the read-only caught-rate-by-score-band report and served-share verdict
affects: [261 acceptance after release, D-06 re-check of the hard-to-catch cut]

actuals:
  tokens: 11000
  tasks: 2
  commits: 2
plan_head_before: 40a07df2960659f37732b7d0a3a68014c9cf150b
plan_head_after: 58bad3e0eb51323e4abbb3309379d30f997f16b4

tech-stack:
  added: []
  patterns:
    - "correlated LIMIT 1 scalar subquery for the live score instead of a join on game_flaws"

key-files:
  created:
    - scripts/blunder_check/caught_rate.py
    - tests/scripts/test_caught_rate.py
  modified: []

key-decisions:
  - "Share verdict: insufficient below 500 windows, accept when the 95% Wilson interval overlaps [0.18, 0.26], fail when entirely outside (constants SHARE_MIN_WINDOWS, SHARE_ACCEPT_LOW, SHARE_ACCEPT_HIGH)"
  - "Bands split at 0.3, 0.5, 0.6, 0.7, 0.8, 0.9 so the D-06 cut at 0.5 can be re-read"
  - "Unscored windows (no snapshot and no live score) are counted per arm and left out of every band"

requirements-completed: [SEED-261121-t50, D-04, D-06]

coverage:
  - id: D1
    description: "Caught rate by score band per arm and origin, reached windows as denominator, false alarms beside, Wilson bounds from wilson_bounds"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/scripts/test_caught_rate.py#test_reached_is_caught_plus_missed_and_false_alarms_sit_beside"
        status: pass
    human_judgment: false
  - id: D2
    description: "Snapshot score wins; legacy windows fall back to the live facepalm_expr; none of either is unscored"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/scripts/test_caught_rate.py#test_legacy_window_falls_back_to_the_live_score"
        status: pass
    human_judgment: false
  - id: D3
    description: "Served exploration share with an accept / fail / insufficient verdict"
    requirement: "SEED-261121-t50"
    verification:
      - kind: unit
        ref: "tests/scripts/test_caught_rate.py#test_share_on_target_is_accepted"
        status: pass
    human_judgment: false
  - id: D4
    description: "Read-only, aggregates only: one read-only connection, SELECT only, no ids in the output"
    verification:
      - kind: unit
        ref: "tests/scripts/test_caught_rate.py#test_report_never_holds_ids"
        status: pass
      - kind: other
        ref: "uv run python scripts/blunder_check/caught_rate.py --db dev (exit 0, both sections printed)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-22
status: complete
---

# Phase 261 Plan 05: Caught-rate calibration script Summary

**A read-only script that prints the caught rate by facepalm-score band with 95% Wilson intervals per arm and origin, plus the served exploration share with an accept / fail / insufficient verdict, reading the Plan 01 snapshot (live score for legacy windows).**

## Accomplishments

- `scripts/blunder_check/caught_rate.py`: one command, `--db {dev,prod}`, optional `--since YYYY-MM-DD` and `--out PATH`. Uses `make_readonly_engine` (one connection, read-only transactions, statement timeout) and `wilson_bounds` from `score_confidence`; no new Wilson code.
- The statement selects arm, origin, snapshot score, a correlated `LIMIT 1` live-score subquery over `game_flaws` (blunder severity) and the outcome, for non-herring windows with a caught / missed / false-alarm outcome. No ids are selected, so the report is aggregates only.
- Report: title and meta line, `## Exploration share` (counts, share, interval, verdict, the rule), `## Caught rate by score band` with one table per arm (exploration, main, legacy; rows own / foreign / all per band) and the unscored count per arm.
- 27 pure tests (no DB) pin band bounds, the reached denominator, the origin split, the legacy fallback and snapshot precedence, all verdict boundaries (499 / 500 / 1000 windows, both sides), the SQL shape (no join, LIMIT in the subquery, herring filter) and that the report holds no id column.

## Task Commits

1. Task 1 (tracer): `4ffa4cdcf` feat, script end to end plus the tracer test
2. Task 2: `58bad3e0e` test, behavior tests (the functions already existed from the tracer, so the RED step was replaced by a mutation check)

Mutation check: flipping the share overlap rule, counting false alarms in the denominator and swapping the snapshot-over-live precedence made four tests fail; restored.

## Deviations from Plan

None - plan executed as written. Notes: Task 2's RED phase was vacuous because the tracer already contained the functions; proved the tests bite by mutation instead. `build_statement` is typed `Select[tuple[Any, ...]]` because ty infers a narrower row type than the nullable columns.

## Verification

- `uv run alembic current`: `a7c3e5f9b261 (head)` (precondition met)
- `uv run python scripts/blunder_check/caught_rate.py --db dev`: exit 0, both sections printed (13 dev windows, none with a recorded arm, verdict insufficient)
- `uv run pytest tests/scripts/test_caught_rate.py`: 27 passed
- `uv run ruff check scripts/ tests/`, `ruff format --check`, `uv run ty check app/ tests/ scripts/`: clean
- The script was not run against prod (not permitted from the worktree).

## Known Stubs

None.

## Threat Flags

None. SELECT only through a read-only one-connection engine (T-261-12); output has no ids (T-261-13).

## Self-Check: PASSED

- `scripts/blunder_check/caught_rate.py` and `tests/scripts/test_caught_rate.py` exist.
- Commits `4ffa4cdcf` and `58bad3e0e` are ancestors of HEAD.
