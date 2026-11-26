---
phase: 258-library-stats-recent-sample-snapshots
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, postgres, window-function, react, library-stats]

requires:
  - phase: 257-facepalm-rate-library-stats
    provides: the /library comparison endpoints and the analyzed-game seam (_analyzed_game_ids_subquery)
provides:
  - fetch_recent_window_rows, one ranked statement: newest 1000 games per TC within 36 months (or the selected period)
  - months_before, recent_window_start, summarize_window, TcWindowSummary, _fetch_recent_window (shared window for plan 02)
  - windowed GET /library/flaw-comparison with sample_since, cap_reached, history_analyzed_n per TC and recency_filtered, window_months, games_cap on the response
  - Flaw Stats basis line (librarySampleBasisText) stating the sample
affects: [258-02 facepalm and tactic windows, 258-03 quiet-TC page state and default-TC fallback, 258-04 prod timing]

actuals:
  tokens: 62000
  tasks: 2
  commits: 3

plan_head_before: f878aeb4c74691e2afd0d58c6164b08265c99e33
plan_head_after: 2075270ec77b8b2d79aa60c75e59e91e9d764211

tech-stack:
  added: []
  patterns:
    - "Window ids restrict the existing analyzed seam through one bound int[] param (game_ids_any_predicate), no fetch signature changes"
    - "Service split along DB / pure seam (_fetch_flaw_comparison_inputs + _build_flaw_comparison_tcs)"

key-files:
  created:
    - frontend/src/lib/__tests__/flawComparisonMeta.test.ts
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - app/routers/library.py
    - tests/test_library_router.py
    - tests/services/test_flaw_comparison.py
    - tests/services/test_tactic_comparison_service.py
    - tests/routers/test_library_tactic_comparison.py
    - frontend/src/types/library.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx

key-decisions:
  - "Window bound computed in Python from dev_now_utc (months_before), not SQL NOW(); nothing persisted has to match it"
  - "analyzed_n / total_n keep their names and become windowed, so the gate slot, coverage hint, popover basis and default TC move to windowed numbers for free"
  - "Offered TCs stay 'TCs with an analyzed game in the unwindowed filtered set' so a quiet TC keeps its switch slot (D-15); its window numbers are zero"
  - "The fresh-import line keeps its unwindowed text (libraryFreshImportBasisText)"
  - "A to_date-only custom range counts as an explicit recency filter (research A4)"

patterns-established:
  - "Rank over the filtered base first; analyzed is an output column, never a pre-rank predicate (D-05)"

requirements-completed: [D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-10, D-11, D-12, D-13, D-15]

coverage:
  - id: C1
    description: "GET /library/flaw-comparison is computed on the recent window (cap 1000 per TC, 36 months or the selected period) and follows the dev clock"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/test_library_router.py#TestGetFlawComparison::test_window_follows_the_pinned_clock"
        status: pass
      - kind: integration
        ref: "tests/test_library_router.py#TestGetFlawComparison::test_recency_filter_replaces_the_window_bound"
        status: pass
    human_judgment: false
  - id: C2
    description: "Response carries the window metadata (recency_filtered, window_months, games_cap, per-TC sample_since, cap_reached, history_analyzed_n)"
    requirement: "D-13"
    verification:
      - kind: integration
        ref: "tests/test_library_router.py#TestGetFlawComparison::test_returns_per_tc_shape_with_auth"
        status: pass
    human_judgment: false
  - id: C3
    description: "Flaw Stats basis line states the sample in the D-13 structure and keeps icon, hint, guest CTA and info popover"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/flawComparisonMeta.test.ts"
        status: pass
    human_judgment: false
  - id: C4
    description: "Wording and placement of the filter phrase in the basis line read well to the owner"
    verification: []
    human_judgment: true
    rationale: "D-13 locks the structure but allows polish; wording is a UAT call"
  - id: C5
    description: "Existing comparison tests are migrated to dated seeds and a fixed clock with assertions untouched"
    verification:
      - kind: integration
        ref: "uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py tests/routers/test_library_tactic_comparison.py"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-21
status: complete
---

# Phase 258 Plan 01: Flaw snapshot on the recent window Summary

**The Library Stats flaw comparison now ranks the newest 1000 games per time control (36 months or the selected period) in one window statement, aggregates exactly the analyzed games of that window, and the Flaw Stats basis line states the sample ("Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed.").**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (tracer with RED/GREEN, then the seed migration)
- **Files modified:** 14 (13 modified, 1 created)

## Accomplishments

- `fetch_recent_window_rows`: `ROW_NUMBER() OVER (PARTITION BY time_control_bucket ORDER BY played_at DESC, id DESC)` over `_filtered_games_base`, `rn <= cap`; NULL `played_at`, NULL/0 `ply_count` and NULL TC never take a slot; `analyzed` / `tactic_ready` are output columns (D-05); every sidebar filter including colour applies before the ranking (D-11); the benchmark ranked-window builders are not used (D-08).
- `_analyzed_game_ids_subquery(user_id, game_ids=...)` restricts the analyzed seam to the window through one bound int[] param (D-06), so `fetch_flaw_comparison` and later the facepalm and tactic fetches stay untouched.
- Service: `months_before` (PostgreSQL-style month clamping, tz kept), `recent_window_start` (None for any explicit from/to, D-04), pure `summarize_window`, `_fetch_recent_window` (shared with plan 02), and `get_flaw_comparison` split into `_fetch_flaw_comparison_inputs` + `_build_flaw_comparison_tcs`. A TC with analyzed games but none in the window stays in `tcs` with zeros (D-15). `below_gate` uses the windowed `analyzed_n` (D-10).
- API: per-TC `sample_since`, `cap_reached`, `history_analyzed_n`; response `recency_filtered`, `window_months`, `games_cap`; route takes `now_utc` from `dev_now_utc`, no new request parameter (D-07). `/flaw-stats` untouched (D-02).
- Frontend: `librarySampleBasisText` (four D-13 variants plus the filter phrase), `libraryFreshImportBasisText`, `CoverageBasisLine` takes `text`, `BASIS_FILTER_FIELDS` drives the "in the current filters" suffix. `libraryCoverageBasisText` is removed.
- Seed migration: every comparison test seeds `played_at` inside a fixed `_NOW`, all 29 `get_flaw_comparison` test calls pass `now_utc`.

## TDD Gate Compliance

- **RED** (`fa890afda`): `tests/test_library_router.py` window tests and the frontend basis-line expectations. Evidence: `test_returns_per_tc_shape_with_auth` failed on the key-set assertion (three window keys missing), `test_window_follows_the_pinned_clock` failed `assert 4 == 3` (the 4-year-old game was counted), `test_recency_filter_replaces_the_window_bound` failed on the missing `recency_filtered` key, and 5 frontend tests failed on the old coverage wording. Semantic assessment: all target tests executed and failed on the planned assertions, not on collection or fixture faults. The `gsd_run check tdd-red-evidence` classifier was not run (pytest console output is not one of its supported formats).
- **GREEN** (`2d545c3d4`): window repository, service, schema, router and frontend wiring; the five router tests and 158 library-stats frontend tests pass.
- **REFACTOR:** none needed.

## Task Commits

1. RED: `fa890afda` test(258-01): add failing tests for the recent-window flaw comparison and basis line
2. Task 1 GREEN: `2d545c3d4` feat(258-01): compute the flaw comparison on the recent window and state it in the basis line
3. Task 2: `2075270ec` test(258-01): seed dated games and pass now_utc in the comparison tests

## Deviations from Plan

### Auto-added

**1. [Rule 2 - Missing critical] Unit table test for `librarySampleBasisText`**
- **Found during:** Task 1
- **Issue:** the plan's frontend test only covers DEFAULT_FILTERS, so the recency and filter-suffix variants of the D-13 wording had no test.
- **Fix:** added `frontend/src/lib/__tests__/flawComparisonMeta.test.ts` (eight combinations, singular "game", missing since date, fresh-import line).
- **Commit:** `2d545c3d4`

**2. [Rule 3 - Blocking] Dropped now-redundant function-local `import datetime`** in `_seed_analyzed` of two test files after adding a module-level import (ruff F811). Commit `2075270ec`.

**Total deviations:** 2 auto-fixed. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-258-01 (user scoping) holds: the window statement filters `Game.user_id == user_id` in the base and the predicates, and the window ids only come from the user's own window. The dedicated two-user isolation test is 258-02 Task 1.

## Deferred / Notes for later plans

- Tactic and facepalm endpoints still read the lifetime analyzed set (plan 02). `tests/routers/test_library_tactic_comparison.py` only gained dated seeds; its HTTP clock pin comes with plan 02.
- `libraryBasisText` popover wording still says "in the current filters" (plan 03, research open question 1).
- The tracer verify was automated-only, so the end-of-phase mode re-ran it instead of raising a checkpoint: backend router tests, frontend tests, `npm run build`, `ty` and the depth gate all green. Full frontend suite (6711 tests), lint and knip pass; full backend comparison files (226 tests) pass.
- No prod measurement was taken here (D-18/D-19 are plan 04).

## Self-Check: PASSED

All created and modified files exist; commits `fa890afda`, `2d545c3d4`, `2075270ec` are ancestors of HEAD; acceptance greps of both tasks match their expected counts.
