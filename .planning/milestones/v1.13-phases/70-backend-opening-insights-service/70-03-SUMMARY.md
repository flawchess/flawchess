---
phase: 70-backend-opening-insights-service
plan: "03"
subsystem: backend-repository
tags: [opening-insights, repository, sql, lag-window, tdd]
dependency_graph:
  requires: [70-01, 70-02]
  provides: [query_opening_transitions, query_openings_by_hashes]
  affects:
    - app/repositories/openings_repository.py
    - tests/repositories/test_opening_insights_repository.py
tech_stack:
  added: []
  patterns: [lag-window-cte, having-strict-gt, cast-to-float, array_agg-window, batched-attribution-lookup]
key_files:
  created: []
  modified:
    - app/repositories/openings_repository.py
    - tests/repositories/test_opening_insights_repository.py
decisions:
  - "Repository owns module-level constants OPENING_INSIGHTS_MIN_ENTRY_PLY/MAX_ENTRY_PLY/MIN_GAMES_PER_CANDIDATE/LIGHT_THRESHOLD — the SQL embeds them and the service re-imports to avoid duplication"
  - "Single transition CTE per (user_id, color) — entry_hash via LAG, entry_san_sequence via array_agg window with rows BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING"
  - "Both Game.user_id == user_id and GamePosition.user_id == user_id predicates for defense-in-depth (denormalized column)"
  - "HAVING uses explicit `cast(wins, Float) / cast(n_games, Float)` per RESEARCH.md Pitfall 5 to avoid integer division"
  - "query_openings_by_hashes returns dict keyed by full_hash; max(ply_count) wins on ties (D-22 deepest attribution)"
metrics:
  shipped_in_pr: "#66 (df9b689)"
  repo_lines_added: 183
  repo_test_lines: 868
  tests_added: ~13
ship_status: shipped
---

# Phase 70 Plan 03: Repository Layer — query_opening_transitions + query_openings_by_hashes (retroactive summary)

**One-liner:** Landed the LAG-window transition CTE and the batched openings attribution lookup; all Wave 0 SQL contract tests turned green.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | `query_opening_transitions(...)` async function — single SQL aggregation per color (D-30) with embedded apply_game_filters | app/repositories/openings_repository.py |
| 2 | `query_openings_by_hashes(...)` async function — batched attribution lookup picking deepest ply_count per hash (D-22) | app/repositories/openings_repository.py |
| — | Replaced NotImplementedError stubs in repository test file with seed-and-assert bodies | tests/repositories/test_opening_insights_repository.py |

## What Was Built

- `query_opening_transitions(session, user_id, color, ...filters)` — composes the per-color CTE with `func.lag(GamePosition.full_hash).over(partition_by=game_id, order_by=ply)` and an `array_agg(move_san) OVER (...rows BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)` to pass `entry_san_sequence` to the service.
- Outer query joins to `Game`, applies WDL counters via the verbatim conditions copied from `stats_repository.query_top_openings_sql_wdl`, GROUP BY `(entry_hash, candidate_san)`, HAVING enforces `n >= 20` and strict `>` 0.55 win-rate or loss-rate.
- `apply_game_filters` chained AFTER the JOIN with `color=None` (per-color is already explicit at the JOIN-Game predicate to avoid double-filtering).
- `query_openings_by_hashes(session, full_hashes)` short-circuits empty input, filters `Opening.full_hash.is_not(None)` at SQL level, and picks max(ply_count) per hash in Python.
- Module-level constants `OPENING_INSIGHTS_*` namespaced to avoid collision with future repo-wide constants. Service module re-imports them.

## Deviations from Plan

None material. The plan's exact CTE shape, HAVING predicates, and acceptance gates were implemented as written.

## Verification

- All ~13 repository tests pass: ply boundaries (3..16 inclusive), LAG-NULL-on-first-ply, min-games floor, HAVING strict-gt-0.55 drops neutrals, user_color routing, recency narrowing, partial-index EXPLAIN check, resulting_full_hash pass-through, entry_san_sequence pass-through, attribution lookup empty/deepest/null cases.
- `EXPLAIN ANALYZE` on the canonical query shows `Index Only Scan using ix_gp_user_game_ply` (Plan 70-02 index).
- `grep -c "from app.services" app/repositories/openings_repository.py` = 0 (no circular imports).

## Self-Check

- [x] `async def query_opening_transitions` and `async def query_openings_by_hashes` defined
- [x] `func.lag(GamePosition.full_hash)` with PARTITION BY game_id present
- [x] `cast(wins, Float)` / `cast(losses, Float)` in HAVING
- [x] EXPLAIN test confirms ix_gp_user_game_ply Index Only Scan
- [x] Shipped as part of PR #66 (df9b689)
