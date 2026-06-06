---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "04"
subsystem: backend
tags: [game_flaws, D-02, D-03, library_service, library_repository, eval-coverage]
dependency_graph:
  requires:
    - phase: 108-03
      provides: "build_flaw_filter_clauses, flaw_exists_from_table, fetch_page_game_flaws, fetch_page_analyzed_set, fetch_stats_aggregates, fetch_stats_trend, fetch_total_user_moves"
  provides:
    - "library_service.py: _curate_chips_from_rows (GameFlaw-backed, replaces FlawRecord-based _curate_chips)"
    - "library_service.py: _build_card (sync, batch-fetch based, no kernel re-call)"
    - "library_service.py: get_library_games (two batch queries: fetch_page_game_flaws + fetch_page_analyzed_set)"
    - "library_service.py: _build_tag_distribution (SQL aggregate kwargs, replaces per-game FlawRecord loop)"
    - "library_service.py: get_flaw_stats (four repo calls replace _load_analyzed_flaws N+1 loop)"
    - "tests/services/test_library_service.py: 16-test suite with game_flaws seeding for DB tests"
  affects:
    - "Plans 108-05..08 — Flaws tab can now rely on game_flaws as the single source for M+B data"
tech_stack:
  added: []
  patterns:
    - "Two batch queries replace N+1 per-game kernel re-call in get_library_games"
    - "fetch_stats_aggregates: COUNT(*) FILTER for all tag columns in one scan"
    - "fetch_stats_trend: LEFT JOIN game_flaws for zero-flaw games in trend"
    - "fetch_total_user_moves: CASE WHEN ply%2 aggregate over game_positions"
    - "Inaccuracy: oracle columns (white_/black_inaccuracies) for cards, 0 for stats panel (D-03)"
    - "Analysis state: eval-coverage gate (not game_flaws presence) — never false 0/0/0"
key_files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/services/test_library_service.py
key-decisions:
  - "Inaccuracy in get_library_games cards: oracle columns (white_/black_inaccuracies), defaulting to 0 (D-03)"
  - "Inaccuracy in get_flaw_stats stats panel: 0 (D-03 accepted — different thresholds, no kernel scan)"
  - "analysis_state gated on eval-coverage (fetch_page_analyzed_set), not game_flaws row count — LIBG-02"
  - "_curate_chips_from_rows reads boolean columns + tempo int (not FlawRecord tags) — no kernel re-call"
  - "test_result_changing_rate: seeds game_flaws rows with is_result_changing column instead of kernel output"
requirements-completed: [D-02, D-03]
duration: 55min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 0
files_modified: 3
---

# Phase 108 Plan 04: Games-Surface Backend Migration to game_flaws (D-02) Summary

**get_library_games and get_flaw_stats migrated off the on-the-fly classifier re-call onto the game_flaws materialized table, with two batch queries replacing the N+1 per-game kernel loop and SQL COUNT(*) FILTER aggregates replacing the per-game FlawRecord distribution scan**

## Performance

- **Duration:** ~55 min (including context reconstruction from previous session)
- **Completed:** 2026-06-06
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **Task 1 (get_library_games migration):** Rewrote `_build_card` as a sync function (no DB access); reads M+B counts from pre-fetched `GameFlaw` rows. Added `_curate_chips_from_rows` — reads boolean columns (`is_miss`, `is_lucky_escape`, `is_while_ahead`, `is_result_changing`) and tempo int via `_TEMPO_INT_TO_TAG`; phase tags excluded via `_CHIP_ORDER`. Inaccuracy from oracle columns (`white_/black_inaccuracies`), defaulting to 0 (D-03). Analysis state from `fetch_page_analyzed_set` (eval-coverage gate, not game_flaws row count). Two batch queries in `get_library_games` replace the N+1 per-game `classify_game_flaws` re-call.

- **Task 2 (get_flaw_stats migration):** Replaced `_load_analyzed_flaws` kernel loop with four repository calls: `count_filtered_and_analyzed`, `fetch_stats_aggregates` (single game_flaws scan via COUNT(*) FILTER), `fetch_stats_trend` (LEFT JOIN game_flaws for zero-flaw games), `fetch_total_user_moves` (CASE WHEN ply parity over game_positions). Added inverse encoding maps (`_SEVERITY_INT_TO_TAG`, `_TEMPO_INT_TO_TAG`, `_PHASE_INT_TO_TAG`) to `library_repository.py`. Retired `_GameFlaws`, `_count_user_moves`, `_load_analyzed_flaws`, `_aggregate_counts`, `_compute_tag_distribution`. `_build_tag_distribution` now takes scalar SQL aggregates as keyword args.

- **Task 3 (test migration):** Rewrote `TestCardChips` tests to use `_curate_chips_from_rows` with in-memory `GameFlaw` objects (new `_make_game_flaw` builder). Added `_seed_db_flaw` helper for DB tests. Updated `test_per_100_moves_and_counts` and `test_result_changing_rate_and_distribution` to seed game_flaws rows alongside game_positions. Migrated `test_miss_rate_and_lucky_escape_rate` from `_compute_tag_distribution`/`_GameFlaws` to game_flaws row seeding + API assertion. Rewrote `test_while_ahead_rate` and `test_rates_zero_when_no_mb_flaws` as pure unit tests calling `_build_tag_distribution` with direct kwargs. 16 tests pass.

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1+2 | Migrate Games-surface backend to game_flaws (D-02) | 180d9982 | app/repositories/library_repository.py, app/services/library_service.py |
| 3 | Update library-service tests for D-02 game_flaws migration | e6c4af1f | tests/services/test_library_service.py |

## Files Created/Modified

- `app/repositories/library_repository.py` — added inverse encoding maps (`_SEVERITY_INT_TO_TAG`, `_TEMPO_INT_TO_TAG`, `_PHASE_INT_TO_TAG`); added five repository functions: `fetch_page_game_flaws`, `fetch_page_analyzed_set`, `fetch_stats_aggregates`, `fetch_stats_trend`, `fetch_total_user_moves`
- `app/services/library_service.py` — module docstring updated (D-02 context); added `_curate_chips_from_rows` (GameFlaw-backed); rewrote `_build_card` as sync; rewrote `get_library_games` (two batch queries); added `_build_tag_distribution` with scalar kwargs; rewrote `get_flaw_stats` (four repo calls); retired `_GameFlaws`, `_load_analyzed_flaws`, `_aggregate_counts`, `_compute_tag_distribution`, `FlawRecord`/`classify_game_flaws` imports
- `tests/services/test_library_service.py` — added `_make_game_flaw` in-memory builder; added `_seed_db_flaw` helper; migrated `TestCardChips` to `_curate_chips_from_rows`; updated all `TestFlawStats` DB tests to seed game_flaws rows; migrated pure-unit tests to `_build_tag_distribution` kwargs

## Decisions Made

- Inaccuracy in game cards uses oracle columns (`white_/black_inaccuracies`) from chess.com/lichess API — D-03 accepted. NULL defaults to 0.
- Inaccuracy in stats panel is 0 — D-03 accepted. Oracle columns use platform-specific thresholds (not kernel-equivalent); a full game_positions kernel scan would negate the D-02 performance win.
- Analysis state gated on eval coverage (not game_flaws row count) — LIBG-02 invariant: an analyzed game with zero M+B flaws must return `analysis_state="analyzed"`, never a false "no_engine_analysis".
- `fetch_total_user_moves` uses CASE WHEN ply%2 to count user plies (white=even, black=odd); requires `.select_from(GamePosition)` to establish join base when joining to `Game` (SQLAlchemy join ambiguity fix).

## Deviations from Plan

**1. [Rule 1 - Bug] SQLAlchemy `.c` deprecation on Select — added `.subquery()` before `.c` access**

- **Found during:** Task 2 implementation
- **Issue:** `_filtered_games_base()` returns a `Select` object; accessing `.c.id` directly raises `CompileError` ("Select.c is deprecated..."). Fix: call `.subquery("name")` first.
- **Files modified:** `app/repositories/library_repository.py`

**2. [Rule 1 - Bug] SQLAlchemy `case()` syntax — positional tuples not nested tuple**

- **Found during:** Task 2 implementation
- **Issue:** Used `case((tuple1, tuple2), else_=...)`. SQLAlchemy 2.x `case()` takes positional `*whens`. Fix: `case(tuple1, tuple2, else_=...)`.
- **Files modified:** `app/repositories/library_repository.py`

**3. [Rule 1 - Bug] SQL join ambiguity in `fetch_total_user_moves` — added `.select_from(GamePosition)`**

- **Found during:** Task 2 implementation
- **Issue:** "Don't know how to join to Game — use .select_from()". Fix: added `.select_from(GamePosition)` before `.join(Game, ...)`.
- **Files modified:** `app/repositories/library_repository.py`

**4. [Rule 2 - Missing critical functionality] Seed game_flaws rows in DB tests**

- **Found during:** Task 3 implementation
- **Issue:** DB tests seeded only game_positions; `get_flaw_stats` now reads from game_flaws, so blunder counts were 0 without game_flaws rows.
- **Fix:** Added `_seed_db_flaw` helper; seeded game_flaws rows in `test_per_100_moves_and_counts`, `test_result_changing_rate_and_distribution`, and `test_miss_rate_and_lucky_escape_rate`.
- **Files modified:** `tests/services/test_library_service.py`

---

**Total deviations:** 3 auto-fixed bugs (Rule 1) + 1 auto-added critical test functionality (Rule 2)

## Known Stubs

None — all outputs are fully functional. The stats panel inaccuracy field reports 0 as a documented D-03 decision, not a stub (the field is intentionally zero-valued with a code comment explaining the rationale).

## Threat Flags

No new network endpoints or auth paths introduced. All user input flows through the existing `apply_game_filters` / `build_flaw_filter_clauses` path (parameterized SQLAlchemy, no string interpolation) already verified in Plan 03.

## Verification

```
uv run pytest tests/services/test_library_service.py   → 16 passed
uv run pytest -n auto -x                               → 2388 passed, 10 skipped
uv run ty check app/ tests/                            → All checks passed!
```

## Self-Check: PASSED
