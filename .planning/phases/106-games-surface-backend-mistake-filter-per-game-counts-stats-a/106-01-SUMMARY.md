---
phase: 106-games-surface-backend-mistake-filter-per-game-counts-stats-a
plan: 01
subsystem: backend
tags: [mistakes, library, sql-window-scan, severity-filter, kernel-seam]
requires:
  - "app/services/mistakes_service.py (Phase 105 kernel: _run_all_moves_pass, _compute_eval_coverage, constants)"
  - "app/services/eval_utils.py (LICHESS_K, eval_cp_to_expected_score)"
  - "app/repositories/query_utils.py (apply_game_filters)"
provides:
  - "mistakes_service.count_game_severities(game, positions) -> SeverityCounts | GameNotAnalyzed"
  - "mistakes_service.SeverityCounts (TypedDict: inaccuracy/mistake/blunder)"
  - "library_repository.mistake_exists_subquery(user_id, severities) -> EXISTS clause (user-color-scoped)"
  - "library_repository.flagged_plies_for_severity(...) (per-ply observation helper / cross-check)"
  - "library_repository._drop_threshold(severity)"
  - "apply_game_filters keyword-only mistake_severity + user_id params"
affects:
  - "106-02 (card counts/chips via count_game_severities + EXISTS filter)"
  - "106-03 (stats panel + analyzed denominator builds on the SQL seam)"
tech-stack:
  added: []
  patterns:
    - "SQLAlchemy window function (func.lag().over(partition_by, order_by)) in a correlated EXISTS"
    - "ES sigmoid transcribed to SQL via func.exp with imported LICHESS_K"
    - "TypedDict union discrimination on the 'reason' key (both erase to dict)"
key-files:
  created:
    - app/repositories/library_repository.py
    - tests/test_library_repository.py
    - tests/services/test_library_service.py
  modified:
    - app/services/mistakes_service.py
    - app/repositories/query_utils.py
decisions:
  - "D1 (locked) confirmed: SQL handles ONLY the EXISTS filter + per-ply flag observation; tags come from the kernel downstream. No public-API refactor of the 105 private tag functions."
  - "apply_game_filters gained a keyword-only user_id param (default None) alongside mistake_severity — required to scope the EXISTS game_positions read (T-106-AC). All existing callers unaffected (both default None)."
  - "Cross-check observes per-ply flags via flagged_plies_for_severity (highest-tier-wins resolution in the test) rather than reverse-engineering the boolean EXISTS — keeps the seam guard precise on (ply, severity)."
metrics:
  duration_minutes: 13
  completed: "2026-06-05"
  tasks: 2
  files_created: 3
  files_modified: 2
---

# Phase 106 Plan 01: Games-surface Backend — Severity-Math Seam Summary

The shared severity-math seam both Phase 106 endpoints depend on: a count-only kernel sibling (`count_game_severities`) for per-game B/M/I counts incl. inaccuracy, plus the single SQL transcription of the ES-drop math (sigmoid + mate Option-B + eval-AFTER LAG pairing) in a new `library_repository`, surfaced as a user-color-scoped `mistake_severity` EXISTS on `apply_game_filters` and guarded by the load-bearing SQL↔kernel cross-check fixture test.

## What was built

### Task 1 — `count_game_severities` + `SeverityCounts` (kernel)
- `SeverityCounts(TypedDict)` with int fields `inaccuracy`/`mistake`/`blunder`, defined near `FlawRecord`/`GameNotAnalyzed`.
- `count_game_severities(game, positions) -> SeverityCounts | GameNotAnalyzed`: the count-only sibling of `classify_game_mistakes`. Reuses `_compute_eval_coverage` for the identical `EVAL_COVERAGE_MIN` gate (returns `GameNotAnalyzed` on miss) and `_run_all_moves_pass` for per-ply severities, tallying all three tiers where `mover == game.user_color`. No FEN recompute, no tags, no SQL.
- Inaccuracy count is genuinely independent of the M+B `FlawRecord` set (Pitfall 3) — proven by `test_inaccuracy_only_game_distinct_from_not_analyzed`.

### Task 2 — SQL ES-drop transcription + user-color EXISTS (`library_repository`)
- `library_repository.py` (NEW): `_drop_threshold`, `_cp_equiv` (mate Option-B CASE), `_es_expr` (sigmoid with imported `LICHESS_K`), `_per_ply_drop_subquery` (LAG of eval_cp/eval_mate over `PARTITION BY game_id ORDER BY ply`), `_drop_filter` (interior/leading null exclusion), `_user_ply_filter` (mover-parity == `Game.user_color`), `mistake_exists_subquery`, and `flagged_plies_for_severity`.
- All thresholds and `LICHESS_K`/`MATE_CP_EQUIVALENT` are imported constants — no literal thresholds in SQL, one source of truth with the kernel.
- `apply_game_filters` gained keyword-only `mistake_severity: Sequence[str] | None = None` and `user_id: int | None = None`. When `mistake_severity` is set it appends the EXISTS (lazy-imported to avoid a `query_utils ↔ library_repository` cycle). Default-None leaves all existing callers unchanged.

## Criterion 5 (the seam guard)
- **B1 (user-color scope):** `mistake_exists_subquery` restricts flagged plies to those whose parity matches the correlated `Game.user_color`. Test `test_exists_filter_excludes_opponent_only_blunder` seeds a game where only the white opponent blunders (user is black) and asserts `severity=["blunder"]` does NOT match it.
- **B2 (cross-check):** `test_cross_check_sql_equals_kernel_subset` seeds mixed evals on both colors and asserts the SQL-flagged `(ply, severity)` set equals exactly `{(ply, sev) for ply, (mover, sev, _, _) in _run_all_moves_pass(positions).items() if mover == game.user_color and sev in ("mistake","blunder")}`.
- User-scoping of the read is additionally pinned by `test_exists_filter_subquery_scoped_to_user` (a different `user_id` matches nothing — T-106-AC).

## Wave-0 scaffolds laid down
- `tests/test_library_repository.py`: `exists_filter` (incl. opponent-only B1 + user-scope), `cross_check` (B2), `analyzed_denominator` (skipped → 106-03).
- `tests/services/test_library_service.py`: `count_game_severities` + `no_engine_analysis`, plus skipped `chips` (106-02) / `stats` (106-03) placeholder classes.

## Deviations from Plan

### Auto-fixed / additive (Rule 2/3)

**1. [Rule 3 - Blocking] `apply_game_filters` needs `user_id` to scope the EXISTS**
- **Found during:** Task 2.
- **Issue:** `mistake_exists_subquery(user_id, ...)` requires the authenticated user's id to scope the `game_positions` read (T-106-AC), but `apply_game_filters` had no `user_id` param.
- **Fix:** Added a keyword-only `user_id: int | None = None` to `apply_game_filters`; it raises `ValueError` if `mistake_severity` is set without `user_id`. Both params default None, so every existing caller is unaffected (verified by `tests/test_query_utils.py` + the `apply_game_filters` regression run).
- **Files modified:** app/repositories/query_utils.py
- **Commit:** 33c3cf9e

No architectural changes (Rule 4) were required. On-the-fly only: no column, table, migration, or backfill added.

## Verification

- `uv run pytest tests/test_library_repository.py tests/services/test_library_service.py -x` → 9 passed, 3 skipped.
- `uv run pytest tests/test_library_repository.py -k "exists_filter or cross_check" -x` → 4 passed (B1 + B2 included).
- `uv run pytest tests/services/test_library_service.py -k "count_game_severities or no_engine_analysis" -x` → passes.
- Regression: `tests/test_query_utils.py`, `tests/test_mistakes_repository.py`, `tests/services/test_mistakes_service.py` all green (existing `apply_game_filters` callers unaffected).
- `uv run ruff check app/ tests/`, `uv run ruff format --check ...`, `uv run ty check app/ tests/` → all clean.

## Known Stubs
None. `analyzed_denominator` (repo) and `chips`/`stats` (service) are explicitly skipped scaffolds with reasons pointing to 106-02 / 106-03 — they are intentional Wave-0 placeholders, not stubbed runtime behavior.

## Acceptance Criteria
- [x] `count_game_severities` returns `GameNotAnalyzed` for all-null-eval, `SeverityCounts` (all three tiers, user moves only) for analyzed, inaccuracy-only → mistake=0/blunder=0/inaccuracy>0.
- [x] `apply_game_filters` supports a boolean `mistake_severity` EXISTS, default None, callers unaffected, user-scoped (opponent-only blunders excluded — B1).
- [x] SQL ES-drop math transcribed once in `library_repository`, matches the user-color-filtered M+B kernel subset on a fixture (B2).
- [x] Constants imported (no SQL literals); no f-string interpolation of user input; parameterized binds only.
- [x] ruff/ty clean for touched files; cross-check + B1 exclusion tests present and green.

## Self-Check: PASSED
- FOUND: app/repositories/library_repository.py
- FOUND: tests/test_library_repository.py
- FOUND: tests/services/test_library_service.py
- FOUND: app/services/mistakes_service.py (count_game_severities @512, SeverityCounts @111)
- FOUND commit 9ac99912 (feat 106-01 kernel helper)
- FOUND commit 33c3cf9e (feat 106-01 SQL EXISTS)
