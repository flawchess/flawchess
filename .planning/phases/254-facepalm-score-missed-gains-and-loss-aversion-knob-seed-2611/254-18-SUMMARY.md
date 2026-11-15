---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 18
subsystem: backend-repositories
tags: [facepalm-score, library, query-time-expression, test-seeding, eval-chart-markers]
requires:
  - phase: 254-02
    provides: "facepalm_expr(lam) and tests/facepalm_seed.py (facepalm_fact_columns, SEED_FACEPALM_MARGIN)"
  - phase: 254-08
    provides: "Drill readers on the expression; the fact-seeding pattern and band-edge margins"
  - phase: 254-15
    provides: "FACEPALM_LIBRARY_LAMBDA and the lam-aware score twins"
provides:
  - "Facepalm range filter (Flaws and Games tabs) and the Flaws-tab chip on one facepalm_expr(FACEPALM_LIBRARY_LAMBDA) object per query"
  - "fetch_page_facepalm_scores: eval-chart tooltip and move-list marker scores from a repository query"
  - "Library tests seeding facts instead of a stored score"
affects: [254-09, 254-10]
tech-stack:
  added: []
  patterns:
    - "One bound query-time expression selected as the chip and passed into the WHERE builder (same object)"
    - "Chip added only to the paged statement, never to the count subquery"
key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/repositories/test_library_repository.py
    - tests/test_library_repository.py
    - tests/test_query_utils.py
    - tests/test_library_router.py
key-decisions:
  - "build_flaw_filter_clauses and _facepalm_clause take an optional bound score expression; query_flaws binds facepalm_expr(FACEPALM_LIBRARY_LAMBDA) once and passes it to both the filter and the chip, while the Games-tab EXISTS (no chip) builds a fresh one inside _facepalm_clause"
  - "The chip column is added with add_columns() on the paged statement only, so the count subquery does not compute it"
  - "_build_flaw_item takes facepalm_score as a required keyword argument instead of reading the ORM attribute"
  - "fetch_page_facepalm_scores returns both movers' scored rows with no severity gate; _build_eval_series keeps its existing severity == blunder gate"
requirements-completed: [D-01, D-04, D-12]
coverage:
  - id: D1
    description: "Flaws-tab chip and the Facepalm range filter agree on a facts grid straddling every whole percent: filtered set equals the set derived from the chips of the unfiltered query, for Low, Mid, High and two 5% slider bands"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/repositories/test_library_repository.py#test_chip_and_filter_agree_on_facts_grid"
        status: pass
    human_judgment: false
  - id: D2
    description: "Band edges seeded at 0.30 and 0.70 +- SEED_FACEPALM_MARGIN land in the expected bands; opponent and unscored rows never match a narrowed range"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/repositories/test_library_repository.py#test_band_edges_with_margins"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_library_repository.py#test_unscored_blunder_never_matches_narrowed_range"
        status: pass
    human_judgment: false
  - id: D3
    description: "Compiled SQL of the narrowed clause reads the fact columns, never the stored score column; the neutral range adds no clause; the Games-tab EXISTS follows"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/test_library_repository.py#TestFacepalmBuildFlawFilterClauses"
        status: pass
      - kind: unit
        ref: "tests/test_query_utils.py#TestFacepalmGate"
        status: pass
    human_judgment: false
  - id: D4
    description: "Eval-chart and move-list markers read the library-lambda expression from a user-scoped repository query (IDOR-safe), and the API payload keeps facepalm_score"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/test_library_router.py#test_flaw_marker_carries_expression_facepalm_score"
        status: pass
      - kind: integration
        ref: "tests/test_library_repository.py#TestFetchPageFacepalmScores"
        status: pass
      - kind: integration
        ref: "tests/test_library_router.py#TestFacepalmFilterEndToEnd"
        status: pass
    human_judgment: false
  - id: D5
    description: "No app reader of the stored score is left in the repositories or the library service; the full backend suite passes"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -q (6574 passed, 19 skipped)"
        status: pass
    human_judgment: false
duration: 35 min
completed: 2026-11-15
status: complete
plan_head_before: b9625a099afcf96ec88cdaf77650940cd680b0b8
plan_head_after: 9c08e44c16bc3232574061a44d3639686e5341b6
commits: 2
actuals:
  tokens: 11000
  tasks: 2
  commits: 2
---

# Phase 254 Plan 18: Library readers on the facepalm expression Summary

**The Flaws-tab chip, the Facepalm range filter on both tabs and the eval-chart / move-list markers now read `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` computed at query time from the stored facts, with library tests seeding facts instead of a stored score.**

## Performance

- **Duration:** about 35 min (estimate; start time not captured), including a 2 min full suite
- **Completed:** 2026-11-15
- **Tasks:** 2 (a tracer and an auto task)
- **Files modified:** 6

## Accomplishments

- `_facepalm_clause` compares one bound expression (`IS NOT NULL`, `>= min/100`, `< (max+1)/100`) instead of the stored REAL; the float note now says expression and bounds are both double precision. `build_flaw_filter_clauses` forwards an optional `facepalm_score` expression, so the Games-tab EXISTS (`flaw_exists_from_table`) follows unchanged in shape.
- `query_flaws` binds the expression once, passes it to the filter and selects it as the `facepalm_chip` column on the paged statement; `_build_flaw_item(..., facepalm_score=...)` takes the value as a parameter. `GameFlaw.user_id` and `player_only_gate` are untouched.
- `fetch_page_facepalm_scores(session, user_id, game_ids) -> dict[int, dict[int, float]]` selects game_id, ply and the library-lambda expression for the user's own rows, NULL scores skipped, empty input returns `{}`. `get_library_game` and `get_library_games` call it next to `fetch_page_game_flaws_both_colors` and pass `facepalm_by_ply` into `_build_card`; the in-Python derivation from the row list is gone.
- Tests: every library seed (`_seed_non_tactic_flaw`, `_seed_tactic_flaw`, `_seed_game_flaw`, `_seed_flaw_committed`) takes `facepalm_target` and seeds `facepalm_fact_columns(target, lam=FACEPALM_LIBRARY_LAMBDA)`; band targets use `SEED_FACEPALM_MARGIN` offsets (the 1.0 score cannot be reached by facts, so the top seed is 0.99); new property test over a 162-row grid (every whole percent 10..90, each at +- margin) sweeping five bands; compiled-SQL assertions point at `played_line_material` / `maia_played_prob`; three tests for `fetch_page_facepalm_scores` including the IDOR guard.
- Proof the property bites: shifting the lower bound to `(min_pct + 1) / 100` failed 3 of the 5 `-k "agree or edges"` tests, then restored.

## Task Commits

1. **Task 1 (tracer): library filter, chip and chart markers on one library-lambda expression** - `bc4e39890` (feat)
2. **Task 2: user-scoped marker score tests** - `9c08e44c1` (test)

Tracer gate: the tracer `<verify>` is automated-only; it was re-run end to end (46 `-k facepalm` and 206 whole-file tests passed) before the expansion task.

## Files Created/Modified

- `app/repositories/library_repository.py` - `_facepalm_clause`, `build_flaw_filter_clauses`, `_build_flaw_item`, `query_flaws` on the expression; new `fetch_page_facepalm_scores`
- `app/services/library_service.py` - `_build_card(facepalm_by_ply=...)`, repository-sourced at both call sites
- `tests/repositories/test_library_repository.py`, `tests/test_library_repository.py`, `tests/test_query_utils.py`, `tests/test_library_router.py` - facts seeding, margins, agreement property, SQL assertions, marker tests

## Decisions Made

See key-decisions. `app/repositories/query_utils.py` needed no change: it reaches the clause through `flaw_exists_from_table` and `build_flaw_filter_clauses`, so the Games tab picked up the expression automatically.

## Deviations from Plan

**1. [Rule 3 - Blocking] Task 2's service wiring landed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** The tracer `<verify>` runs `tests/test_library_router.py`, whose marker test reads `FlawMarker.facepalm_score`. With the chip and filter on facts but the service still deriving `facepalm_by_ply` from the (now unseeded) stored column, the tracer verify could not pass, and the plan forbids expanding past a red tracer.
- **Fix:** Committed `fetch_page_facepalm_scores` and the `library_service` wiring with the tracer commit; Task 2's own commit holds the tests for the new fetch (scoping, NULL skip, empty input), and its verify and full-suite gate ran after it.
- **Files modified:** `app/repositories/library_repository.py`, `app/services/library_service.py`
- **Commit:** `bc4e39890`

**Total deviations:** 1 auto-fixed (Rule 3). **Impact:** none on behaviour; only the split of work across the two commits differs from the plan text.

## Issues Encountered

- Prod EXPLAIN of the narrowed-range queries is plan 10's job (needs prod access, not done here). The compiled clause repeats the expression three times (`IS NOT NULL`, lower bound, upper bound) per narrowed range, since each is a separate comparison; PostgreSQL can evaluate the repeated deterministic expression per row, so the prod plan check should cover the Flaws and Games range queries.
- No dev database state was changed; Alembic head stays `a7d2c9e1b254`. No Game rows were inserted outside a rolled-back `db_session` or the existing committed fixtures with cleanup.

## Known Stubs

None.

## Threat Flags

None. T-254-22 mitigated (`GameFlaw.user_id == user_id` and `player_only_gate` kept in `query_flaws`; `fetch_page_facepalm_scores` is user-scoped and has an IDOR test); T-254-23 mitigated (one bound expression in SELECT and WHERE, plus the grid property test); T-254-25 mitigated (the lambda is the named constant, never a request parameter; router bounds unchanged). The API response shape is unchanged (`facepalm_score` on flaw rows and markers), so no frontend change.

## Next Phase Readiness

The library is on the expression. Plan 09 (operator scripts) follows on the same branch; plan 10 owns the prod EXPLAIN checks before shipping.

## Self-Check: PASSED

Commits `bc4e39890` and `9c08e44c1` are on HEAD. Verified: `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` present in `library_repository.py`; `async def fetch_page_facepalm_scores(` present; the stored-score grep over `app/repositories` and `app/services/library_service.py` prints 0 (library_repository count 0); `-k "agree or edges"` 5 passed; library test files 206 passed; router/service/chart suites 175 passed; `ty check app/ tests/ scripts/`, `ruff check .`, `ruff format --check` and `check_function_size.py app/ --fail-over-depth 4` clean; full `uv run pytest -n auto -q` 6574 passed, 19 skipped.
