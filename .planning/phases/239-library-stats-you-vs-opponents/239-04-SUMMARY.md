---
phase: 239-library-stats-you-vs-opponents
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, library, tactic-comparison, zone-registry]
requires:
  - phase: 239-02
    provides: "count_analyzed_by_tc, LOW_SAMPLE_MIN_FLAWS, LIBRARY_TC_ORDER, _bucket_rows_by_tc, ZONE_TC_FOR/ZoneBand/ZoneTc"
provides:
  - "GET /api/library/tactic-comparison returns tcs[] (per TC: analyzed_n, below_gate, 38 fixed-order bullets) + analyzed_gate"
  - "tactic_delta_zones: TacticFamily, TACTIC_FAMILIES, TacticSide, TACTIC_SIDES, TACTIC_DELTA_ZONES, tactic_delta_zone()"
  - "TacticBullet per 100 games with zone_lo/zone_hi/has_zone from the registry and low_sample"
affects: [239-07, 239-08]
tech-stack:
  added: []
  patterns:
    - "two orientation fetches bucketed per TC in Python, bullets interleaved missed/allowed per family"
    - "tactic registry shares the flaw registry's ZONE_TC_FOR (one stopgap mapping)"
key-files:
  created:
    - app/services/tactic_delta_zones.py
    - tests/services/test_tactic_delta_zones.py
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/services/test_tactic_comparison_service.py
    - tests/routers/test_library_tactic_comparison.py
    - tests/test_library_router.py
key-decisions:
  - "TACTIC_FAMILIES is spelled out in tactic_delta_zones.py rather than derived from FAMILY_TO_MOTIF_INTS: the schemas import the registry and the repository imports the schemas, so deriving it would be an import cycle. A parity test pins content and order."
  - "The registry ships with all 38 entries None (has_zone false), today's live behaviour; plan 239-07 writes the section-5 values."
  - "fetch_tactic_comparison excludes NULL time_control_bucket games in its anchor, consistent with count_analyzed_by_tc."
patterns-established:
  - "Zone lookup per bullet via tactic_delta_zone(family, side, tc); the D-08/D-09 stopgap lives only in ZONE_TC_FOR."
requirements-completed: [D-00h, D-02, D-03, D-06, D-08, D-09, D-11, D-12]
duration: 40min
completed: 2026-10-12
status: complete
actuals:
  tokens: 28000
  tasks: 2
  commits: 2
plan_head_before: 1b4ce6a6f65bd02bfe4dc4aa83988d87aa889369
plan_head_after: d720c5287b432bbeb1edc8e193837c75cc8b50c5
---

# Phase 239 Plan 04: Per-TC tactic comparison per 100 games Summary

**`/tactic-comparison` now answers per time control in one response (`tcs[]`, each with 38 fixed-order missed/allowed bullets, per 100 games, `low_sample` flag, zones from a new tactic registry that shares the silent blitz/bullet -> rapid stopgap); the Phase 129 top-6 ranking and overflow are gone.**

## Accomplishments

- `app/services/tactic_delta_zones.py` (new): `TacticFamily` (19 literals), `TACTIC_FAMILIES` (FAMILY_TO_MOTIF_INTS order), `TacticSide`, `TACTIC_SIDES`, `TACTIC_DELTA_ZONES` (38 entries, all `None` = unviable), `tactic_delta_zone(family, side, tc)`. Imports `ZONE_TC_FOR`, `ZoneBand`, `ZoneTc` from `flaw_delta_zones`.
- Schemas: `TacticBullet` (typed `family`/`orientation`, required `zone_lo`/`zone_hi`/`has_zone`/`low_sample`), `TacticComparisonTc`, `TacticComparisonResponse(tcs, analyzed_gate)`.
- Repository: `fetch_tactic_comparison` carries a `tc` column (anchor, select, group_by) and excludes NULL buckets; docstrings now say 19 families / 38 count columns. The join gate is unchanged.
- Service: `PER_100_GAMES`, `_build_tactic_bullet`, `_compute_tactic_bullets(rows, orientation, tc)` (iterates `TACTIC_FAMILIES`, multiplies counts by `PER_100_GAMES` in this one place), `_interleave_tactic_bullets`, per-TC `get_tactic_comparison` using `count_analyzed_by_tc(..., tactic_filter_orientation="either")`. Removed `_sort_key`, `_missed_rank_key`, the ranked/overflow block and the pooled gate early return. Sequential awaits only; no new query parameter; `tactic_families` filter retained.
- Router docstring describes the per-TC payload.

## Task Commits

1. Task 1 (tracer): `34b511855` feat: registry, schema, repository tc column, per-100-games service, router docstring, registry + service tests
2. Task 2: `d720c5287` test: below-gate, low-sample boundary, per-TC band wiring, two-user isolation, router contract

## Mutation checks (each failed the matching test, then reverted)

| Mutation | Test that failed |
|----------|------------------|
| `PER_100_GAMES = 1.0` (drop the scaling) | `test_per_100_games_unit` (`1.0 == 100.0`) and `test_fixed_order_per_tc` (`0.04 == 4.0`) |
| zone lookup hard-wired to `"blitz"` in `_build_tactic_bullet` | `test_zone_lookup_uses_each_bullets_tc` (`-2.0 == -1.0` on the classical TC) |

## Verification

- Targeted suites (flaw comparison, both zone registries, tactic service, tactic router, library router): 112 passed.
- Full backend suite `uv run pytest -n auto`: 5385 passed, 19 skipped.
- `ruff format`, `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Acceptance greps: `_missed_rank_key|overflow_families|def _sort_key` -> 0 matches; `PER_100_GAMES` -> 4 matches; router tests only touch `["bullets"]` inside the per-TC entry.

## Deviations from Plan

None - plan executed as written. Two small notes:

- Router test `test_tactic_families_filter` now seeds analyzed games (and one allowed-fork flaw) so the filter's population narrowing (3 -> 1) is actually asserted; the plan only asked for the filter test to be adjusted to the per-TC shape. Router tests that commit games clean them up in `finally` via `_delete_games`; service tests use `db_session`, which rolls back, so nothing persists.
- The stale module-scoped `tactic_comparison_state` fixture in `tests/test_library_router.py` (pre-existing, committed analyzed games, no teardown) was left as is; analyzed games are not eval-lottery candidates.

## Contract notes for downstream plans

- 239-07 fills `TACTIC_DELTA_ZONES` entries as `{"rapid": ZoneBand, "classical": ZoneBand}` or leaves `None`; the parity test `test_registry_values_are_none_or_cover_both_zone_tcs` enforces that shape.
- 239-08 can rely on: every listed TC has exactly 38 bullets (family order, missed before allowed); `delta`/rates are per 100 games; zero-event bullets have `delta`, rates, CI and p-value `None` with `low_sample` True; unviable bullets have `has_zone` False and zone bounds `0.0`.
- The frontend (`frontend/`) still reads the old `bullets`/`below_gate` top-level shape of this endpoint; plan 239-08 owns that migration. No `frontend/src/generated/*` files were touched.

## Known Stubs

None. The all-`None` registry is the documented interim state (plan 239-07 writes the values), not a stub that blocks this plan's goal.

## Threat Flags

None. No new endpoints or trust boundaries. T-239-08: `user_id` still only from `current_active_user`, anchor and count subqueries scoped by `Game.user_id`, join gate by `GameFlaw.user_id`; pinned by `test_two_user_isolation` (service) and the router filter test. T-239-09: unknown `tactic_families` keys still expand to no motif ints (existing test kept).

## Self-Check: PASSED

- FOUND: app/services/tactic_delta_zones.py, tests/services/test_tactic_delta_zones.py
- FOUND commits: 34b511855, d720c5287
