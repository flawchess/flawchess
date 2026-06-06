---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "03"
subsystem: backend
tags: [predicate-builder, game_flaws, EXISTS, query_utils, SEED-038, D-02]
dependency_graph:
  requires:
    - phase: 108-01
      provides: "GameFlaw ORM model (app/models/game_flaw.py)"
    - phase: 108-02
      provides: "game_flaws_repository: _SEVERITY_INT, _TEMPO_INT, bulk_insert_game_flaws"
  provides:
    - "library_repository.py: build_flaw_filter_clauses — shared family-aware predicate builder"
    - "library_repository.py: flaw_exists_from_table — game_flaws-backed EXISTS wrapper"
    - "query_utils.py: apply_game_filters updated to game_flaws EXISTS + flaw_tags param"
    - "tests/test_flaw_predicate.py: 17-test suite (unit + integration)"
  affects:
    - "Plans 108-04..08 — Flaws endpoint and Games migration share build_flaw_filter_clauses"
    - "Plan 108-05 Flaws SELECT path reuses build_flaw_filter_clauses"
tech_stack:
  added: []
  patterns:
    - "build_flaw_filter_clauses: OR within family, AND across families (SEED-038)"
    - "flaw_exists_from_table: game_flaws-backed correlated EXISTS (replaces window-scan)"
    - "_SEVERITY_INT/_TEMPO_INT imported from game_flaws_repository (single source)"
    - "true() returned when no filter (match all games)"
    - "test_split_flaws_across_plies: the make-or-break single-flaw EXISTS assertion"
key_files:
  created:
    - tests/test_flaw_predicate.py
  modified:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - tests/test_library_repository.py
key-decisions:
  - "Retired window-scan helpers (_per_ply_drop_subquery, _drop_filter, _user_ply_filter, flaw_exists_subquery, flagged_plies_for_severity) — D-02 migration complete"
  - "Retired TestCrossCheck (SQL<->kernel cross-check) — game_flaws IS the materialized kernel output, no SQL path can drift"
  - "flaw_exists_from_table returns true() (not false()) for empty filter — caller semantics: no filter = match all"
  - "Updated test_library_repository.py TestExistsFilter tests to seed game_flaws rows; retired position-based EXISTS tests"
requirements-completed: [D-02, D-03]
duration: 13min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 1
files_modified: 3
---

# Phase 108 Plan 03: Shared Predicate Builder, game_flaws EXISTS Wrapper, and Predicate Unit Test Summary

**One shared family-aware predicate builder (OR within / AND across families) reused by both the Games EXISTS filter and the Flaws SELECT path, with window-scan helpers retired and 17-test predicate suite proving single-flaw EXISTS semantics, family boolean logic, and cross-user isolation**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-06-06T15:37:53Z
- **Completed:** 2026-06-06T15:51:06Z
- **Tasks:** 3
- **Files modified/created:** 4

## Accomplishments

- Added `build_flaw_filter_clauses(severity, tags)` to `library_repository.py` — OR within each tag family (tempo/opportunity/impact), AND across families; phase tags (opening/middlegame/endgame) intentionally produce no clause; imports `_SEVERITY_INT`/`_TEMPO_INT` from `game_flaws_repository` (single source, no duplication)
- Added `flaw_exists_from_table(user_id, severity, tags)` — correlated EXISTS over `game_flaws` scoped to `user_id + Game.id`; returns `true()` when no filter (match all); replaces the Phase 106 window-scan `flaw_exists_subquery`
- Retired all window-scan helpers: `_per_ply_drop_subquery`, `_drop_filter`, `_user_ply_filter`, `flaw_exists_subquery`, `flagged_plies_for_severity` — the window-scan SQL path that duplicated the Python kernel is gone
- Updated `apply_game_filters` in `query_utils.py` — new keyword-only `flaw_tags: Sequence[str] | None`; EXISTS block calls `flaw_exists_from_table` (D-02 migration); ValueError when either flaw filter is set without `user_id`
- Created `tests/test_flaw_predicate.py` with 17 tests:
  - 8 unit tests (no DB): clause count assertions for empty/single/multi-family inputs; phase-tag exclusion; MIN-threshold invariant
  - 9 integration tests (real DB): the make-or-break split-flaw test; single-flaw both-families match; OR within tempo and opportunity families; severity MIN-threshold; cross-user isolation; no-flaw exclusion; empty-filter = `true()`
- Updated `tests/test_library_repository.py` — retired `TestCrossCheck` (now obsolete post-D-02); updated `TestExistsFilter` tests to use `game_flaws` rows instead of position-based window-scan; retired direct `flaw_exists_subquery` usage

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Shared predicate builder + game_flaws-backed EXISTS wrapper | 74b42d2b | app/repositories/library_repository.py, tests/test_library_repository.py |
| 2 | Migrate apply_game_filters EXISTS to game_flaws + add flaw_tags param | 722e20a7 | app/repositories/query_utils.py, tests/test_library_repository.py |
| 3 | Predicate builder unit test (Wave 0 stub) | fc43a6a9 | tests/test_flaw_predicate.py |

## Files Created/Modified

- `app/repositories/library_repository.py` — module doc updated (D-02 context); dead window-scan helpers removed; new `build_flaw_filter_clauses` + `flaw_exists_from_table`; imports cleaned (`_SEVERITY_INT/_TEMPO_INT` from game_flaws_repository, `FlawTag`, `GameFlaw`, `true`)
- `app/repositories/query_utils.py` — new `flaw_tags: Sequence[str] | None = None` param; EXISTS block replaced (`flaw_exists_from_table`); docstring updated
- `tests/test_library_repository.py` — `TestCrossCheck` retired; `_sql_flagged_set` helper removed; `TestExistsFilter` rewritten to use `game_flaws` rows; `TestQueryFilteredGames.test_severity_filter_narrows_to_blunder_games` updated; removed dead imports (`flaw_exists_subquery`, `eval_cp_to_expected_score`, `BLUNDER_DROP`, `_run_all_moves_pass`, `_cp_for_white_drop`)
- `tests/test_flaw_predicate.py` (new) — 17-test predicate suite

## Decisions Made

- `flaw_exists_from_table` returns `true()` for empty filter (not `false()`) — this correctly means "no filter applied, match all games" when neither severity nor tags are set. The caller (`apply_game_filters`) only calls the function when at least one of `flaw_severity`/`flaw_tags` is non-empty, so `true()` is never actually added to the statement in practice.
- `TestCrossCheck` retired rather than adapted — the cross-check was needed because the window-scan duplicated the Python kernel in SQL. After D-02, `game_flaws` IS the materialized kernel output; there is no separate SQL path to check for drift. The new invariant (materialized rows match classifier output) is tested in `test_flaws_materialization.py` (Plan 02).
- `TestExistsFilter` tests updated to seed `game_flaws` rows — the tests now directly verify the game_flaws-backed EXISTS semantics rather than relying on position-based window-scan behavior.

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Updated test_library_repository.py TestExistsFilter tests**

- **Found during:** Task 2 implementation
- **Issue:** After migrating `apply_game_filters` to the `game_flaws`-backed EXISTS, `TestExistsFilter` tests that seeded `game_positions` rows (but no `game_flaws` rows) would always return 0 matching games, making the assertions vacuously false or incorrectly failing.
- **Fix:** Rewrote `TestExistsFilter` to seed `game_flaws` rows directly; added a `_seed_game_flaw` helper. Added three new test cases (user-scoping, MIN-threshold, no-match exclusion) that more directly test the new semantics.
- **Files modified:** `tests/test_library_repository.py`
- **Verification:** All 8 tests in test_library_repository.py pass; 2383 total tests pass.

---

**Total deviations:** 1 auto-fixed (Rule 2 — test migration for D-02 semantic change)
**Impact on plan:** Necessary for a correct, non-vacuous test suite. No scope creep — the update is in-scope for the D-02 migration task.

## Issues Encountered

None beyond the test migration deviation documented above.

## Known Stubs

None — all outputs are fully functional: the predicate builder is production-ready; `apply_game_filters` is migrated; the test suite verifies all critical invariants.

## Threat Flags

No new network endpoints or auth paths introduced. T-108-06 and T-108-07 mitigations from the plan's threat model are fully implemented and verified:

| Flag | File | Description |
|------|------|-------------|
| (none — T-108-06 mitigated) | app/repositories/library_repository.py | Tag/severity inputs map through `_SEVERITY_INT`/`_TEMPO_INT` dicts + parameterized SQLAlchemy comparisons — no string interpolation |
| (none — T-108-07 mitigated) | app/repositories/library_repository.py | `flaw_exists_from_table` always includes `GameFlaw.user_id == user_id`; verified by `test_cross_user_isolation` |

## Verification

```
uv run pytest tests/test_flaw_predicate.py -x   → 17 passed
uv run pytest -n auto -x                         → 2383 passed, 10 skipped
uv run ty check app/ tests/                      → All checks passed!
```

## Self-Check: PASSED
