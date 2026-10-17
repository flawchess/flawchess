---
phase: 239-library-stats-you-vs-opponents
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, library, flaw-comparison, zone-registry]
requires: []
provides:
  - "GET /api/library/flaw-comparison returns tcs[] (per time control: analyzed_n, below_gate, 12 bullets)"
  - "GET /api/library/flaw-stats returns trend_by_tc[] plus coverage counts"
  - "flaw_delta_zones: per-zone-TC registry with ZONE_TC_FOR blitz/bullet -> rapid stopgap"
  - "library_repository.count_analyzed_by_tc (reusable by the tactic comparison)"
  - "library_service: LOW_SAMPLE_MIN_FLAWS, LIBRARY_TC_ORDER, _bucket_rows_by_tc"
affects: [239-03, 239-04, 239-05, 239-07, 239-08]
tech-stack:
  added: []
  patterns:
    - "one response per endpoint listing every offered TC; the TC switch is client-side"
    - "single per-game row fetch bucketed per TC in Python (no per-TC query)"
key-files:
  created:
    - tests/services/test_flaw_delta_zones.py
  modified:
    - app/services/flaw_delta_zones.py
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/services/test_flaw_comparison.py
    - tests/services/test_library_service.py
    - tests/test_library_repository.py
    - tests/test_library_router.py
key-decisions:
  - "Bullets are always computed for every listed TC, also below the 20-game gate (D-03); the old pooled early return is gone."
  - "NULL time_control_bucket games are excluded at the repository level (count, comparison rows, trend rows) and implicitly by iterating LIBRARY_TC_ORDER."
  - "Registry carries today's 12 pooled bands unchanged under both zone TCs; plan 239-07 writes the recomputed values."
patterns-established:
  - "Per-zone-TC registry lookup via flaw_delta_zone(metric, tc): silent D-08/D-09 stopgap lives only in ZONE_TC_FOR."
requirements-completed: [D-00e, D-00f, D-00k, D-01, D-02, D-03, D-08, D-09, D-12]
duration: 55min
completed: 2026-10-12
status: complete
actuals:
  tokens: 32000
  tasks: 3
  commits: 3
plan_head_before: 58cb1ee58c2337595d829dfbbf0eac5d166be234
plan_head_after: b58df8083f56a28739b7f2730f4868e4c55acc5d
---

# Phase 239 Plan 02: Per-TC flaw comparison and Flaws Timeline backend Summary

**`/flaw-comparison` and `/flaw-stats` now answer per time control in one response each (tcs[] with 12 registry-banded bullets and a server-side low_sample flag; trend_by_tc[]), on a per-zone-TC registry with the silent blitz/bullet -> rapid stopgap; combo tags, overall flaw rate, `domain` and the unused flaw-stats aggregates are gone.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 of 3
- **Files modified:** 10 (1 created)

## Accomplishments

- `flaw_delta_zones.py` rewritten to the contract: `FlawDeltaMetric`, `FLAW_DELTA_METRICS` (12), `ZoneTc`, `ZONE_TC_FOR`, `ZoneBand`, `FLAW_DELTA_ZONES[metric][zone_tc]`, `flaw_delta_zone()`. Today's 12 bands carried forward unchanged for both zone TCs.
- `FlawBullet` gains `low_sample` (you + opponent flaws < `LOW_SAMPLE_MIN_FLAWS` = 40) and loses `domain`; `FlawComparisonTc` / per-TC `FlawComparisonResponse` (`tcs`, `analyzed_gate`).
- `count_analyzed_by_tc` (filtered base ∩ analyzed subquery, grouped by bucket, NULL excluded); `fetch_flaw_comparison` and `fetch_flaw_trend_rows` carry a `tc` column; the flaw-rate and two combo column pairs are deleted (24 count columns remain).
- `get_flaw_comparison`: counts per TC, one row fetch, `_bucket_rows_by_tc`, `_compute_bullets(rows, tc)` per TC in `LIBRARY_TC_ORDER`; no `asyncio.gather`, no new query parameter.
- `get_flaw_stats`: `trend_by_tc` + `analyzed_pct/analyzed_n/total_n`; `SeverityRates`, `TagDistribution`, `fetch_stats_aggregates`, `fetch_stats_per_game_rates`, `_macro_per_100_rates`, `_build_rates`, `_build_tag_distribution` removed. Grep before deletion: the only callers were `get_flaw_stats` and `TestStatsAggregatesPlayerOnly` (deleted with it).

## Task Commits

1. **Task 1: per-TC comparison end to end** - `23f1d4aae` (feat)
2. **Task 2: gate/filter/NULL/low-sample/band/isolation edges + router contract tests** - `829756aff` (test)
3. **Task 3: per-TC Flaws Timeline, aggregates removed** - `b58df8083` (feat)

## Mutation checks (all failed the matching test, then reverted)

| Mutation | Test that failed |
|----------|------------------|
| `get_flaw_comparison` feeds all rows to every TC (pooling) | `test_per_tc_split` (`assert 25 == 0` on rapid mistake events) |
| NULL-bucket guard dropped from `count_analyzed_by_tc` | `test_null_time_control_bucket_excluded` (`{'blitz': 20, 'None': 5} != {'blitz': 20}`) |
| `<` changed to `<=` in the low_sample expression | `test_low_sample_boundary[at_threshold]` |
| trend built over all rows for every TC | `test_trend_by_tc_is_computed_per_time_control` |

## Decisions Made

- The NULL-bucket guard is defence in depth: iterating `LIBRARY_TC_ORDER` already drops unknown buckets in the service, so a service-level assertion alone cannot detect a removed repository guard. The NULL test therefore also pins `count_analyzed_by_tc` and `fetch_flaw_comparison` output directly (that is what made the guard mutation fail).
- The classical/bullet band test monkeypatches the registry, because rapid and classical hold identical values until plan 239-07 writes the recomputed bands; without the patch the test could not tell the two zone TCs apart.
- `db_session` rolls back every test transaction, so the new tests need no finally-cleanup for the committed-lottery concern; seeded users/games never persist.

## Deviations from Plan

None - plan executed as written. (Clarification: the Task 2 mutation "drop the NULL-bucket guard" required the extra repository-level assertions described above to be observable; no production code changed in Task 2.)

## Issues Encountered

None blocking. Full backend suite after Task 3: 5290 passed, 19 skipped (`uv run pytest -n auto`). `ruff check`, `ruff format`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` all clean.

## Contract notes for downstream plans

- `FlawBullet.tag` is now `FlawDeltaMetric`; `has_zone` is always True for flaw bullets.
- `count_analyzed_by_tc` already accepts the tactic keywords (`tactic_families`, `tactic_filter_orientation`) so plan 239-04 can reuse it unchanged.
- The frontend (`frontend/`) still reads the old shapes (`bullets`, `domain`, `per_severity_counts`, `rates`, `trend`); plans 239-03/05/08 own that migration. No `frontend/src/generated/*` files were touched.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries; `user_id` still comes only from `current_active_user` and every new query is scoped by `Game.user_id` (T-239-03 covered by `test_two_user_isolation`).

## Self-Check: PASSED

- FOUND: app/services/flaw_delta_zones.py, tests/services/test_flaw_delta_zones.py
- FOUND commits: 23f1d4aae, 829756aff, b58df8083
