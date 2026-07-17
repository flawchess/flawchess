---
phase: 175-board-filter-gem-great-consumption
plan: 01
subsystem: api
tags: [sqlalchemy, postgres, fastapi, filters, gem-great, correlated-exists]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    provides: game_best_moves table + classify_best_move/GEM_MAIA_MAX_PROB/GREAT_MAIA_MAX_PROB constants
provides:
  - "best_move_tier_sql/_es_sql — SQLAlchemy Core twin of classify_best_move, importing (never re-declaring) all shared thresholds"
  - "best_move_exists_from_table — correlated EXISTS over game_best_moves, mirroring flaw_exists_from_table"
  - "apply_game_filters(has_gem=, has_great=) — single-implementation composition point"
  - "GET /library/games?has_gem=&has_great= — HTTP boundary for the Library games filter"
affects: [175-02, 175-03, 176-backend-corpus-backfill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQL-expression twin discipline (Python classifier + SQLAlchemy Core twin sharing constants, cross-referenced docstrings — mirrors decided_lost_sql/is_decided_lost)"
    - "Correlated EXISTS over a table with no user_id column, scoped entirely via outer Game.id correlation + player_only_gate"

key-files:
  created: []
  modified:
    - app/services/best_move_candidates.py
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/routers/library.py
    - app/services/library_service.py
    - tests/services/test_best_move_candidates.py
    - tests/test_query_utils.py
    - tests/test_library_repository.py
    - tests/test_library_router.py

key-decisions:
  - "best_move_tier_sql returns NULL where classify_best_move returns 'neither' — the EXISTS only ever tests membership in {'gem','great'}, so a bare NULL is the correct SQL equivalent (no ternary string needed in SQL)"
  - "Mover color for the filter's EXISTS is always Game.user_color, never re-derived per-row — only rows passing player_only_gate can satisfy the EXISTS, and for those rows the mover is provably the user"
  - "Renamed test methods to include the literal substring 'best_move_exists' / kept 'best_move' in test_query_utils.py test names so the plan's own -k selectors actually select the new tests (pytest -k is substring/case-sensitive against node ids)"

patterns-established:
  - "SQL twin sync discipline: a threshold retune (GEMS-07) touches ONE module (best_move_candidates.py) and both the board's Python classify_best_move and the filter's SQL best_move_tier_sql move together"

requirements-completed: [FILT-01]

coverage:
  - id: D1
    description: "best_move_tier_sql/_es_sql SQL-expression twin of classify_best_move, agreeing on the GEM/GREAT boundary, the narrow [0.05,0.10) margin band, and mate-based bests for both mover colors"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "tests/services/test_best_move_candidates.py::test_tier_sql_agrees_with_classify_best_move (11 parametrized cases, real DB evaluation)"
        status: pass
    human_judgment: false
  - id: D2
    description: "has_gem/has_great EXISTS filter composed into apply_game_filters, scoped to the user's own plies (D-04), union semantics (D-05), and composing with color/other filters (D-05a)"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "tests/test_query_utils.py::test_apply_game_filters_has_gem_composes_with_flaw_and_metadata_filters and siblings"
        status: pass
      - kind: integration
        ref: "tests/test_library_repository.py::TestBestMoveExistsFromTable (player-parity, union, color-compose, cross-user isolation — real Postgres)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /library/games?has_gem=/has_great= HTTP boundary — union, color composition, matched_count/pagination correctness across pages, cross-user isolation"
    requirement: "FILT-01"
    verification:
      - kind: integration
        ref: "tests/test_library_router.py::TestGetLibraryGamesBestMoveFilter (6 tests, real ASGI client against real Postgres)"
        status: pass
    human_judgment: false

# Metrics
duration: 42min
completed: 2026-07-16
status: complete
---

# Phase 175 Plan 01: SQL Twin + has_gem/has_great Library Filter Summary

**Backend `best_move_tier_sql` SQLAlchemy twin of `classify_best_move` plus a `has_gem`/`has_great` correlated-EXISTS filter on `GET /library/games`, composed through the single `apply_game_filters()` implementation.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-07-16T20:06:00Z (approx, session start)
- **Completed:** 2026-07-16T20:48:16Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- `_es_sql`/`best_move_tier_sql` added to `app/services/best_move_candidates.py` as SQLAlchemy Core `case()`/`func.exp()` expressions — the exact Option-B mate mapping + Lichess-K sigmoid math as `_eval_to_expected_score`/`classify_best_move`, importing (never re-declaring) `GEM_MAIA_MAX_PROB`, `GREAT_MAIA_MAX_PROB`, `MISTAKE_DROP`, `MATE_CP_EQUIVALENT`, `LICHESS_K`.
- Proved SQL/Python agreement via **real DB evaluation** (11 parametrized cases via `select(best_move_tier_sql(literal(...)))` against Postgres — `func.exp()` cannot be checked by reading code alone), covering both GEM/GREAT boundary values, the narrow `[0.05, 0.10)` margin band (Pitfall 3 — must classify NEITHER regardless of `maia_prob`), and mate-based bests for both mover colors.
- `best_move_exists_from_table(tiers)` added to `library_repository.py`, mirroring `flaw_exists_from_table`'s correlated-EXISTS + `true()`-sentinel shape. `game_best_moves` has no `user_id` column, so IDOR safety comes entirely from the `GameBestMove.game_id == Game.id` correlation to the caller's already user-scoped statement, plus `player_only_gate` for D-04 player-parity scoping.
- `apply_game_filters` extended with keyword-only `has_gem`/`has_great: bool | None`, assembling a single `tiers` list so both booleans set together is a **union** (gem OR great), never an intersection — composed alongside (not replacing) the existing flaw/tactic EXISTS.
- `GET /library/games` gained `has_gem`/`has_great` `bool | None` Query params, threaded unchanged through `library_service.get_library_games` → `query_filtered_games` → `apply_game_filters` (thin router, no logic).

## Task Commits

Each task was committed atomically:

1. **Task 1: SQL-expression twin of classify_best_move** - `ec36f2a2` (feat)
2. **Task 2: has_gem/has_great EXISTS filter wired through apply_game_filters + router** - `156c3290` (feat)

## Files Created/Modified
- `app/services/best_move_candidates.py` - `_es_sql`/`best_move_tier_sql` SQL twins
- `app/repositories/library_repository.py` - `best_move_exists_from_table` correlated EXISTS
- `app/repositories/query_utils.py` - `apply_game_filters(has_gem=, has_great=)` composition
- `app/routers/library.py` - `GET /library/games` `has_gem`/`has_great` Query params
- `app/services/library_service.py` - `get_library_games` param threading
- `tests/services/test_best_move_candidates.py` - fixture-matrix SQL/Python agreement tests (real DB)
- `tests/test_query_utils.py` - SQL-compile composition tests
- `tests/test_library_repository.py` - correlated-EXISTS integration tests (player-parity, union, color-compose, cross-user isolation)
- `tests/test_library_router.py` - HTTP-boundary tests (union, pagination, color-compose, cross-user isolation)

## Decisions Made
- `best_move_tier_sql` returns NULL (not a string) for the "neither" case — the SQL twin only needs to answer `.in_(['gem','great'])` membership, so a bare NULL is the correct and simpler SQL equivalent of Python's `"neither"` return value.
- `best_move_exists_from_table` always passes `Game.user_color` as the classifier's mover-color argument rather than deriving it per-row — this is safe because `player_only_gate` already restricts the EXISTS to rows where the mover IS the user, so `mover_color_for_ply(ply) == Game.user_color` holds by construction for every row the EXISTS considers.
- Renamed several new test methods (e.g. `TestBestMoveExistsFromTable`'s methods gained a `test_best_move_exists_` prefix) so the plan's own `-k best_move_exists` / `-k best_move` verification selectors actually match the new tests — `pytest -k` does a literal substring match against the node id, and a bare CamelCase class name like `TestBestMoveExistsFromTable` does not substring-match the snake_case keyword `best_move_exists`.

## Deviations from Plan

None - plan executed exactly as written. The one adjustment (test naming to satisfy the plan's own `-k` verify selectors) is a test-authoring detail, not a behavior or scope change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FILT-01 backend is fully delivered: `GET /library/games?has_gem=true&has_great=true` filters by the user's own gem/great moves with correct union semantics, correct `matched_count`/pagination, and proven cross-user isolation.
- `best_move_tier_sql` and `best_move_exists_from_table` are available for reuse — e.g. a future frontend filter UI plan can wire straight into the existing `has_gem`/`has_great` Query params with no further backend work.
- BOARD-01 (EvalPoint gem/great fields for the board) and the frontend filter UI toggles were explicitly out of scope for this plan (per files_modified) and remain for subsequent 175-series plans.

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-16*

## Self-Check: PASSED

All 9 modified files confirmed present on disk; both task commits (`ec36f2a2`, `156c3290`) confirmed in git history.
