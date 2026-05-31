---
phase: 98-per-tc-collapsible-endgame-type-cards
plan: "01"
subsystem: endgame-analytics
tags: [backend, codegen, endgame, per-tc, benchmark-bands, analytics]

dependency_graph:
  requires: []
  provides:
    - PER_CLASS_TC_GAUGE_ZONES in endgame_zones.py + generated endgameZones.ts
    - _aggregate_endgame_stats_by_tc in endgame_service.py
    - categories_by_tc optional field on EndgameStatsResponse (Python + TS)
  affects:
    - frontend/src/generated/endgameZones.ts (regenerated, CI drift gate green)
    - app/services/endgame_service.py (new aggregation + overview wiring)
    - app/schemas/endgames.py (additive schema field)
    - frontend/src/types/endgames.ts (additive TS interface field)

tech_stack:
  added: []
  patterns:
    - PerClassTcBands dataclass alongside PerClassBands (additive, D-15 safe)
    - Single-pass bucket_rows aggregation by (tc, class) following Phase 97 pattern
    - Optional Pydantic field + optional TS field for back-compat (Pitfall 6)
    - D-15 invariant: LLM path reads only categories (pooled), never categories_by_tc

key_files:
  created:
    - tests/test_endgame_zones.py (12 tests for PER_CLASS_TC_GAUGE_ZONES)
  modified:
    - app/services/endgame_zones.py (PerClassTcBands + PER_CLASS_TC_GAUGE_ZONES)
    - scripts/gen_endgame_zones_ts.py (_format_per_class_tc_gauge_zones + emission block)
    - frontend/src/generated/endgameZones.ts (regenerated: new PER_CLASS_TC_GAUGE_ZONES export)
    - app/services/endgame_service.py (_aggregate_endgame_stats_by_tc + query_endgame_overview wiring)
    - app/schemas/endgames.py (categories_by_tc optional field)
    - frontend/src/types/endgames.ts (categories_by_tc optional field)
    - tests/test_endgame_service.py (TestAggregateEndgameStatsByTc — 10 tests)
    - tests/services/test_insights_service.py (TestD15LlmPathInvariant — 2 tests)

decisions:
  - "Accepted queen classical small-n bands (0.88,1.00)/(0.00,0.09) as-is per benchmark rule"
  - "PerClassTcBands is a new dataclass alongside PerClassBands, not replacing it (D-15)"
  - "categories_by_tc is optional (None default) on EndgameStatsResponse for back-compat"
  - "No eval aggregation per-(tc, class) in _aggregate_endgame_stats_by_tc (tiles only need WDL+conv/recov+score)"

metrics:
  duration: ~45 minutes
  completed_date: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 8
  files_created: 1
---

# Phase 98 Plan 01: Backend Foundation for Per-TC Collapsible Endgame Type Cards Summary

One-liner: Per-(class × TC) benchmark band registry (20 entries, 5 classes × 4 TCs) codegen'd to TS via drift gate, plus a single-pass `_aggregate_endgame_stats_by_tc` aggregator exposing `categories_by_tc` on the endgame overview response — all additive, LLM path provably unaffected.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add PER_CLASS_TC_GAUGE_ZONES registry + regenerate endgameZones.ts | 7155ac54 | endgame_zones.py, gen_endgame_zones_ts.py, endgameZones.ts, test_endgame_zones.py |
| 2 | Add _aggregate_endgame_stats_by_tc + categories_by_tc on EndgameStatsResponse | 1a79a0ff | endgame_service.py, endgames.py (schema), endgames.ts, test_endgame_service.py, test_insights_service.py |

## What Was Built

**Task 1: Per-(class × TC) Gauge Zone Registry**

Added `PerClassTcBands` frozen dataclass and `PER_CLASS_TC_GAUGE_ZONES` mapping (5 classes × 4 TCs = 20 entries) to `app/services/endgame_zones.py`. Populated from `reports/benchmark/benchmarks-latest.md §3.4.1` p25/p75 tables — all 5 visible classes have "keep-separate" Cohen's d verdict (d ≈ 1.19–1.67) confirming per-TC bands are required. Score Gap (achievable_score_gap) uses identical bands across TCs per class (TC d ≈ 0.07–0.18, all collapse), with the redundancy chosen per D-04/D-14. Queen classical bands noted as small-n artifact (n≈30–35).

Extended `scripts/gen_endgame_zones_ts.py` with `_format_per_class_tc_gauge_zones()` and a new emission block in `_render()`. Regenerated `frontend/src/generated/endgameZones.ts` — CI drift gate confirmed green.

The new registry sits alongside `PER_CLASS_GAUGE_ZONES` (unchanged) and `assign_per_class_zone` (unchanged), preserving the LLM insights path (D-15).

**Task 2: Backend Per-(class × TC) Aggregation**

Added `_aggregate_endgame_stats_by_tc()` to `app/services/endgame_service.py`: single pass over already-fetched `bucket_rows`, grouping by `(row[6] tc, row[1] endgame_class_int)`. Reuses the same WDL/conv/recov accumulation, `derive_user_result`, `_classify_endgame_bucket`, `_compute_span_scores`, and `compute_paired_difference_test` helpers as `_aggregate_endgame_stats`. Returns `dict[Literal[TC], list[EndgameCategoryStats]]` in fixed `_TIME_CONTROL_ORDER` with per-(class, TC) `score_p_value`.

Wired into `query_endgame_overview` after `_compute_per_tc_metric_cards` — no new DB query (T-98-01 mitigation). Added optional `categories_by_tc` field to `EndgameStatsResponse` (Pydantic schema and TypeScript interface), both optional for back-compat.

## Verification Results

- `uv run pytest tests/ -k "endgame_zones or endgame_service or insights"` — 752 passed, 3 skipped
- `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` — green (drift gate)
- `uv run ruff check app/ tests/ scripts/` — all checks passed
- `uv run ty check app/ tests/` — all checks passed
- D-15 invariant: `grep -v '^#' app/services/insights_service.py | grep -c "categories_by_tc"` = 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The `categories_by_tc` field is populated with real aggregated data in `query_endgame_overview`; the optional `None` default is only for back-compat with the separate `get_endgame_stats` path (which doesn't have `bucket_rows` available).

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-98-01 mitigated | app/services/endgame_service.py | `categories_by_tc` derived from already-authorized `bucket_rows` scoped to authenticated user via existing `apply_game_filters` + user_id scoping. No new query, no cross-user data path. |

## Self-Check: PASSED

- `app/services/endgame_zones.py` contains `PER_CLASS_TC_GAUGE_ZONES`: FOUND
- `frontend/src/generated/endgameZones.ts` contains `PER_CLASS_TC_GAUGE_ZONES`: FOUND
- `app/services/endgame_service.py` contains `_aggregate_endgame_stats_by_tc`: FOUND
- `app/schemas/endgames.py` contains `categories_by_tc`: FOUND
- `frontend/src/types/endgames.ts` contains `categories_by_tc`: FOUND
- `tests/test_endgame_zones.py` exists: FOUND (12 tests)
- Commit 7155ac54 exists: FOUND
- Commit 1a79a0ff exists: FOUND
