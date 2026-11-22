---
phase: 260-facepalm-first-class-move-quality
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, flaw-filter, facepalm, pytest]

requires:
  - phase: 257-facepalm-library-stats
    provides: FACEPALM_STATS_MIN cut, facepalm_expr query-time score, player_only_gate
provides:
  - "FlawSeverityFilter Literal (facepalm / blunder / mistake) and _severity_clause in the shared flaw clause builder (D-08, D-12)"
  - "severity=facepalm accepted on /library/flaws, /library/games and the stats routes; stored FlawSeverity unchanged"
  - "fetch_page_facepalm_scores returns the scored plies of both sides, so opponent FlawMarkers carry facepalm_score and facepalm_type (D-24)"
affects: [260-02, 260-04, 260-05, 260-07]

actuals:
  tokens: 12600
  tasks: 3
  commits: 4
plan_head_before: 3b3d7d3948d2dc0b392f4f2ab35be02ee3536c7f
plan_head_after: c4083f8feab2e6a926346795b35792497b03b386

tech-stack:
  added: []
  patterns:
    - "Filter-value Literal owned by the repository and aliased by the router, so the HTTP boundary and the clause builder validate one type"
    - "Score expression rendered once per WHERE: coalesce for the Blunder-only branch, no score for Blunder + Facepalm"

key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/test_library_router.py
    - tests/test_flaw_predicate.py
    - tests/repositories/test_library_repository.py
    - tests/services/test_library_service.py
    - tests/test_library_repository.py
    - tests/services/test_maia_flaw_scoring.py

key-decisions:
  - "Blunder-only branch uses coalesce(score, 0.0) < FACEPALM_STATS_MIN so an unscored blunder is a Blunder (D-09) and the large score expression renders once"
  - "All three tags compile to mistake OR blunder (no score), keeping today's EXISTS meaning of 'game has one user flaw'"
  - "_DEFAULT_SEVERITY is all three tags, because two tags would now drop facepalm blunders from the default Flaws list"
  - "fetch_page_facepalm_scores drops the owner gate (D-24); every filter and drill path keeps player_only_gate"

requirements-completed: [D-07, D-08, D-09, D-12, D-23, D-24]

coverage:
  - id: D1
    description: "GET /library/flaws and /library/games accept severity=facepalm through the shared build_flaw_filter_clauses; inaccuracy and unknown values still return 422"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/test_library_router.py#TestFlawSeverityFacepalmEndToEnd"
        status: pass
      - kind: integration
        ref: "tests/test_library_router.py#test_invalid_severity_rejected_422"
        status: pass
    human_judgment: false
  - id: D2
    description: "The D-08 truth table (Facepalm, Blunder, Blunder + Facepalm, Mistake + Facepalm, nothing or all three) holds on query_flaws and the Games EXISTS; the opponent's above-cut blunder never matches"
    requirement: "D-08, D-09"
    verification:
      - kind: integration
        ref: "tests/repositories/test_library_repository.py#TestFlawSeverityTags"
        status: pass
      - kind: unit
        ref: "tests/test_flaw_predicate.py#TestBuildFlawFilterClausesUnit"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Flaws list default keeps facepalm blunders (default severity is all three tags)"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py#TestFlawsDefaultSeverity"
        status: pass
    human_judgment: false
  - id: D4
    description: "Opponent blunder markers carry facepalm_score and facepalm_type on the game card and /analysis payloads; counts and filters stay player-gated"
    requirement: "D-24, D-07"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py#TestOpponentFacepalmMarker"
        status: pass
      - kind: integration
        ref: "tests/test_library_repository.py#TestFetchPageFacepalmScores"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_facepalm_expr_scores_opponent_row_and_marker_reader_returns_it"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 01: Facepalm severity tag and two-sided facepalm scores Summary

**The Flaws and Games filters accept `severity=facepalm` through one shared `_severity_clause` (Blunder now means a blunder below the cut or unscored), and opponent blunder markers carry their facepalm score and type.**

## Performance

- **Duration:** about 45 min (start time not captured at spawn; estimated)
- **Completed:** 2026-11-22T13:36Z
- **Tasks:** 3
- **Files modified:** 10 (4 app, 6 tests)

## Accomplishments

- `FlawSeverityFilter = Literal["facepalm", "blunder", "mistake"]`, `FLAW_SEVERITY_FILTER_VALUES` and `_severity_clause` implement the D-08 table in `build_flaw_filter_clauses`. The router's `SeverityFilter` aliases the repository Literal, `apply_game_filters` casts to it, and the stored `FlawSeverity` / `_SEVERITY_INT` are untouched (no migration).
- The score expression is referenced only when exactly one of Blunder / Facepalm is selected, once (coalesce on the Blunder branch); `query_flaws` passes its bound chip expression so chip and clause cannot disagree. Compile-shape test pins the occurrence counts per subset.
- `get_library_flaws` defaults to all three tags, so facepalm blunders stay in the default Flaws list (research Pitfall 2).
- `fetch_page_facepalm_scores` no longer gates on the owner side (D-24): opponent `FlawMarker`s get `facepalm_score` and `facepalm_type` on the game card and `/analysis`. The Flaws filter, the Games EXISTS, drill selection and the severity counts keep `player_only_gate`.

## Task Commits

1. **Task 1: Tracer, severity=facepalm from HTTP through the clause builder** - `a3f1e8834` (feat)
2. **Task 2: D-08 truth table, compile shape, Flaws default** - `baa13a5dc` (test)
3. **Task 3: Opponent facepalm scores on markers** - RED `1450f12c5` (test), GREEN `c4083f8fe` (feat)

**Plan metadata:** committed in the docs commit that follows this file.

## TDD Gate Compliance

- Task 3 followed RED then GREEN. RED: the four updated or new tests (`test_both_sides_scored_rows_unscored_skipped`, `test_both_sides_scored_rows_black_owner`, `test_facepalm_expr_scores_opponent_row_and_marker_reader_returns_it`, `test_opponent_blunder_carries_facepalm_score`) failed on the planned assertions (`{2} == {2, 3}`, `{3} == {2, 3}`, opponent ply missing from the marker reader, `facepalm_score is None` on the ply-3 marker). Semantic assessment: each failure is the owner gate dropping the opponent row, the intended reason; no import, fixture or collection error. The evidence classifier does not support pytest output and `workflow.tdd_mode` is off (plan `type: execute`), so no `tdd-red-evidence` record was filed.
- Task 2 (`tdd="true"`) has no separate RED commit: the tracer (Task 1) already implemented the clause, so its tests were green on arrival. Instead of a RED run they were proven by mutation: dropping the `coalesce` in the Blunder branch failed 4 tests, restoring the old two-tag default failed 2 tests, and relaxing the Facepalm branch to every blunder failed 2 router tests. All mutations were reverted.

## Decisions Made

- Used `coalesce(expr, 0.0)` for the Blunder-only branch rather than `or_(expr.is_(None), expr < cut)`: it renders the large score expression once and keeps an unscored blunder a Blunder.
- Kept the "non-empty selection always emits a clause" behaviour, so all three tags still require the game to hold one user mistake or blunder (today's EXISTS meaning).
- Left `min_facepalm_pct` / `max_facepalm_pct` and `_facepalm_clause` untouched (D-23, removal is plan 07).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test selected 0.8-scored blunders with severity=["blunder"]**
- **Found during:** Task 3 full-suite run
- **Issue:** `TestQueryFlawsFacepalmType::test_typed_seeds_return_both_types` seeds two blunders at score 0.8 and asked for `severity=["blunder"]`; under D-08 those are facepalms, so the Blunder tag no longer lists them.
- **Fix:** the test now asks for `["blunder", "facepalm"]` (the plan said to fix the test, not the clause).
- **Files modified:** tests/test_library_repository.py
- **Commit:** c4083f8fe

**2. [Rule 3 - Blocking] Type errors in tests/test_flaw_predicate.py after the type change**
- **Found during:** Task 1 (`ty check`)
- **Issue:** two helpers cast to `Sequence[FlawSeverity]` and passed it to `flaw_exists_from_table`, now typed `Sequence[FlawSeverityFilter]`.
- **Fix:** cast to `FlawSeverityFilter` instead.
- **Files modified:** tests/test_flaw_predicate.py
- **Commit:** a3f1e8834

**3. [Doc touch] `get_library_flaws` docstring** said "defaults to M+B"; updated to the three-tag default in the Task 2 commit (`library_service.py` is in the plan's file list).

**Total deviations:** 2 auto-fixed (1 bug-in-test, 1 blocking type fix), 1 docstring touch. **Impact:** none on scope.

## Issues Encountered

- The Games-tab test case for an empty tag selection lists all five games, including the opponent-only one: with no tag the EXISTS is not applied (plain archive). The plan's "never the opponent-only game" holds for every non-empty selection, including all three tags, and that is what the test pins.

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary: T-260-01 (severity values 422-validated by FastAPI, mapped to ints and a bound float), T-260-02 (no `_SEVERITY_INT` lookup on a filter value, every non-empty subset tested) and T-260-04 (player gate and user scope kept, opponent above-cut blunder seeded in every truth table) are mitigated as planned.

## Verification

- `uv run pytest -n auto -q` full backend suite: 6899 passed, 8 skipped.
- `uv run ruff check .`, `uv run ty check app/ tests/ scripts/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: clean.
- Not run: the frontend gates (this plan touches no frontend file) and the full serial CI suite (`-n auto` only).

## Next Phase Readiness

Plans 260-02 (frontend table and chart split), 260-04 and 260-05 can read `facepalm_score` on opponent markers and send `severity=facepalm`. D-13 (range-parameter removal) stays for plan 07 after Phase 259 is on `main`.

## Self-Check: PASSED

All named files exist; commits a3f1e8834, baa13a5dc, 1450f12c5 and c4083f8fe are ancestors of HEAD.
