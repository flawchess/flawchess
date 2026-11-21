---
phase: 258-library-stats-recent-sample-snapshots
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, postgres, window-function, library-stats, facepalm, tactics]

requires:
  - phase: 258-library-stats-recent-sample-snapshots
    provides: _fetch_recent_window, fetch_recent_window_rows, summarize_window and the game_ids restriction of _analyzed_game_ids_subquery (plan 01)
provides:
  - decision tests that pin the recent window (cap, 36-month bound, explicit period, unanalyzed slots, colour-first, tiebreak, exclusions, isolation, gate, quiet TC)
  - GET /library/facepalm-comparison computed on the shared recent window, JIT off from the window statement on
  - GET /library/tactic-comparison computed on the shared recent window, counted on its tactic-ready games
affects: [258-03 frontend quiet-TC state, 258-04 prod timing and JIT decision]

actuals:
  tokens: 15000
  tasks: 3
  commits: 3

plan_head_before: e91d63c37b5cc3201907c9d9f713c8fd62cfdcd2
plan_head_after: d2623d6400725ba6452e996d83e0794a21c11218

tech-stack:
  added: []
  patterns:
    - "All three snapshot services build one _filter_kwargs dict, read _fetch_recent_window, and restrict the existing fetch through _analyzed_game_ids_subquery(user_id, game_ids=...)"
    - "A set-aside list rule per endpoint: flaw = TCs with analyzed games (unwindowed), facepalm = TCs with a window game, tactic = TCs with a tactic-ready window game"

key-files:
  created:
    - tests/services/test_library_window.py
  modified:
    - app/services/library_service.py
    - app/routers/library.py
    - app/schemas/library.py
    - tests/services/test_library_service.py
    - tests/services/test_flaw_comparison.py
    - tests/services/test_tactic_comparison_service.py
    - tests/routers/test_library_tactic_comparison.py
    - tests/test_library_router.py

key-decisions:
  - "Facepalm lists every TC with a window game (analyzed or not); a listed TC with no analyzed window game carries three zero-event rows, so a TC the switch offers never leaves the Facepalm tile on its skeleton"
  - "The tactic path drops its separate unwindowed blob-gated count; the window's tactic_analyzed_n carries the same gate, one statement fewer"
  - "JIT is switched off in the facepalm service before the window statement; the flaw and tactic paths leave JIT alone until plan 04's prod EXPLAIN decides"

patterns-established:
  - "Pin a reused window by decision tests before a second consumer builds on it, and prove the tests by reverting a predicate and watching them fail"

requirements-completed: [D-02, D-03, D-04, D-05, D-06, D-10, D-11, D-15]

coverage:
  - id: C1
    description: "The flaw-side window decisions (cap, bound, explicit period, unanalyzed slots, colour-first, tiebreak, exclusions, isolation, windowed counts, gate, quiet TC) are pinned by tests"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/services/test_library_window.py"
        status: pass
    human_judgment: false
  - id: C2
    description: "The Flaws Timeline is not windowed: analyzed games four years old still produce a point"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py#TestFlawStats::test_trend_full_history"
        status: pass
    human_judgment: false
  - id: C3
    description: "The facepalm rows aggregate exactly the analyzed games of the recent window, the low-coverage rule sees only window rows, every TC with a window game is listed, JIT is off before the window statement"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/services/test_flaw_comparison.py#test_facepalm_same_game_set_on_the_window"
        status: pass
      - kind: integration
        ref: "tests/services/test_flaw_comparison.py#test_facepalm_low_coverage_on_the_window"
        status: pass
      - kind: integration
        ref: "tests/services/test_flaw_comparison.py#test_facepalm_lists_window_tcs"
        status: pass
      - kind: integration
        ref: "tests/services/test_flaw_comparison.py#test_facepalm_jit_is_off_before_the_window_statement"
        status: pass
    human_judgment: false
  - id: C4
    description: "The tactic rows, analyzed_n and below_gate read the tactic-ready games of the recent window; a quiet TC is absent and a selected period brings it back"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/services/test_tactic_comparison_service.py#test_tactic_window_ids"
        status: pass
      - kind: integration
        ref: "tests/services/test_tactic_comparison_service.py#test_tactic_gate_on_window"
        status: pass
      - kind: integration
        ref: "tests/services/test_tactic_comparison_service.py#test_tactic_quiet_tc_absent"
        status: pass
    human_judgment: false
  - id: C5
    description: "Both routes take now_utc from dev_now_utc and run under a pinned clock in the router tests"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/routers/test_library_tactic_comparison.py and tests/test_library_router.py (FacepalmComparison, TacticComparisonDualOrientation)"
        status: pass
    human_judgment: false
  - id: C6
    description: "A TC the switch offers whose recent games are all unanalyzed shows zero-event Facepalm rows rather than a skeleton or a withheld card"
    verification: []
    human_judgment: true
    rationale: "Recorded assumption (Claude's discretion): the list-rule change is flagged for UAT, no test asserts how the Facepalm tile reads it"

duration: 10min
completed: 2026-11-21
status: complete
---

# Phase 258 Plan 02: Facepalm and tactic snapshots on the recent window Summary

**The facepalm and tactic comparison endpoints now read the same recent window as the flaw comparison (newest 1000 games per time control within 36 months, or the selected period) through one shared helper, with the window itself pinned by 19 decision tests and the Flaws Timeline proven unwindowed.**

## Performance

- **Duration:** about 10 min of executor time (three tasks, three commits)
- **Tasks:** 3 (Task 1 tests only, Tasks 2 and 3 RED/GREEN-style service changes with their tests)
- **Files:** 9 (1 created, 8 modified); backend only, no frontend file touched

## Accomplishments

- `tests/services/test_library_window.py` (19 tests): months_before clamping, summarize_window, per-TC cap and the real 1000 cap, the 36-month bound, an explicit from_date or to_date replacing the bound with the cap kept (D-04), unanalyzed games taking cap slots (D-05), colour applied before the cap (D-11), the game-id tiebreak, NULL played_at / zero / NULL ply_count / NULL TC exclusions, two-user isolation, windowed analyzed_n / total_n (D-06), the flaw gate on the window (D-10), the quiet TC kept in tcs (D-15). `test_trend_full_history` proves the timeline is unwindowed (D-02).
- Mutation check of the pinned window (reverted afterwards, no source change kept): dropping the ply_count predicate, flipping the id tiebreak, deleting the window bound and dropping the NULL played_at predicate each fail named tests.
- `get_facepalm_comparison` takes `now_utc`, awaits `disable_jit_for_transaction` before the window statement, aggregates the analyzed window ids, and lists every TC with a window game. `_facepalm_low_coverage` is untouched and now sees window rows only.
- `get_tactic_comparison` takes `now_utc`, drops the separate blob-gated count, aggregates the tactic-ready window ids, and `analyzed_n` / `below_gate` are the windowed tactic-ready count.
- `/facepalm-comparison` and `/tactic-comparison` take `now_utc` from `dev_now_utc` (3 routes now). Schema docstrings describe the window and the per-endpoint TC list rule.

## TDD Gate Compliance

- Task 1: tests only over plan 01's implementation, all passing on first run; proven by reverting four window predicates one at a time and seeing the matching tests fail.
- Task 2 RED: the nine pre-existing facepalm tests failed with `TypeError: get_facepalm_comparison() got an unexpected keyword argument 'now_utc'` once migrated to the new call shape; GREEN: all 46 tests of `tests/services/test_flaw_comparison.py` pass. The JIT-order test was shown to fail with the service-level `disable_jit_for_transaction` call removed.
- Task 3: the signature change and the three window tests landed together; the tests were proven by mutation (swapping `tactic_analyzed_n` for `analyzed_n`, and dropping `game_ids=tactic_ids`, each fail `test_tactic_window_ids`). The `gsd_run check tdd-red-evidence` classifier was not run (pytest console output is not a supported format).

## Task Commits

1. Task 1: `70c389d03` test(258-02): pin the recent window decisions and the unwindowed timeline
2. Task 2: `d80568e3e` feat(258-02): read the facepalm rows on the recent window with JIT off
3. Task 3: `d2623d640` feat(258-02): read the tactic rows on the recent window

## Deviations from Plan

### Auto-added

**1. [Rule 2 - Missing critical] Service-level JIT ordering test**
- **Found during:** Task 2
- **Issue:** the must-have "JIT off for the whole request transaction, the window statement included" had no test; the existing JIT test only covers the repository readers.
- **Fix:** `test_facepalm_jit_is_off_before_the_window_statement` spies on `_fetch_recent_window` and asserts `SHOW jit` is `off`.
- **Commit:** `d80568e3e`

**2. [Rule 1 - Test hardening] NULL played_at exclusion without a lower bound**
- **Found during:** Task 1 mutation check
- **Issue:** with the 36-month bound or any date filter active, the NULL-dated game is excluded before the `played_at IS NOT NULL` predicate is reached, so deleting that predicate failed no test.
- **Fix:** `test_excluded_rows` also calls `fetch_recent_window_rows(window_start=None, cap=1)`.
- **Commit:** `70c389d03`

**Total deviations:** 2 auto-added, both extra test coverage. **Impact:** none on scope; no production file changed in Task 1 (the window needed no fix).

## Issues Encountered

None. Router tests for `/facepalm-comparison` in `tests/test_library_router.py` still run on the real clock (their seeds are dated January 2026, inside the window until early 2029); the plan only asked for the clock pin on the tactic router tests.

## Known Stubs

None.

## Threat Flags

None. T-258-05 holds: both services read the user-scoped window and restrict the analyzed subquery with `Game.user_id == user_id`; the existing two-user isolation tests in both files run on the windowed services, plus the new window isolation test. T-258-06 is mitigated for the facepalm path (JIT off before the window statement); the flaw and tactic paths are left for plan 04's prod EXPLAIN.

## Handoff to 258-03

No response field was added or removed; frontend types need no change. Behaviour changes the page state should expect:

- `/facepalm-comparison` `tcs` now lists every TC with a window game, analyzed or not. A listed TC with no analyzed window game has `low_coverage: false` and three zero-event bullets (`delta`, rates `null`, events 0). A TC with no window game (quiet TC) is absent, so the Facepalm tile of a quiet TC has no entry; the tile should key off the flaw list, as the quiet-TC state in plan 03 already does.
- `/tactic-comparison` `tcs` lists only TCs with a tactic-ready window game; `analyzed_n` is the windowed tactic-ready count. A quiet TC is absent.
- Both endpoints follow `dev_now_utc`, no new query parameter.

## Next Phase Readiness

Plan 03 (frontend) can proceed; plan 04 can measure the window statement on prod. `count_analyzed_by_tc(require_tactic_blobs=...)` in the repository has no production caller any more (only its own parameter handling remains); left in place, outside this plan's scope.

## Self-Check: PASSED

Created and modified files exist; commits `70c389d03`, `d80568e3e`, `d2623d640` are ancestors of HEAD. Acceptance greps: 19 tests in the window file, 1 `test_trend_full_history`, `disable_jit_for_transaction` in the service, `now_utc: NowUtc` 3 times in the router, `require_tactic_blobs=True` 0 in the service, `_fetch_recent_window(` 4 in the service, `now_utc=_NOW` 41 in `test_flaw_comparison.py` and 15 in `test_tactic_comparison_service.py`, `dev_now_utc` 5 in the tactic router test. Plan verification: 253 tests across the six touched test files pass; ruff check, ruff format --check, ty and the depth gate are clean.
