---
phase: 53-endgame-score-gap-material-breakdown
plan: "01"
subsystem: backend
tags: [endgames, analytics, schemas, service, tests]
dependency_graph:
  requires: []
  provides: [score_gap_material field in EndgameOverviewResponse]
  affects: [app/schemas/endgames.py, app/services/endgame_service.py, tests/test_endgame_service.py, tests/test_endgames_router.py]
tech_stack:
  added: []
  patterns: [WDL-to-score formula, material bucket assignment, entry_rows sharing across aggregations]
key_files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - tests/test_endgames_router.py
decisions:
  - No persistence check in material bucket assignment — uses user_material_imbalance only (unlike conversion/recovery which require both imbalance and imbalance_after)
  - entry_rows fetched once in get_endgame_overview and shared across stats, performance, and score_gap_material computations — eliminates redundant DB query
  - _get_endgame_performance_from_rows extracted as pure function accepting pre-fetched rows, enabling sharing
  - Verdict thresholds: good (>= overall), ok (>= overall - 0.05), bad (below)
metrics:
  duration: "~30 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  files_modified: 4
---

# Phase 53 Plan 01: Score Gap & Material Breakdown Backend Summary

Adds backend schemas and service logic for the Endgame Score Gap & Material Breakdown feature. Extends `GET /api/endgames/overview` with a new `score_gap_material` field containing the endgame score difference metric and a material-stratified WDL table.

## What Was Built

### Pydantic Schemas (`app/schemas/endgames.py`)

- `MaterialBucket = Literal["ahead", "equal", "behind"]` — typed bucket identifier
- `Verdict = Literal["good", "ok", "bad"]` — performance verdict relative to overall score
- `MaterialRow` — one row in the material-stratified WDL table: bucket, label, games, win_pct, draw_pct, loss_pct, score (0.0-1.0), verdict
- `ScoreGapMaterialResponse` — top-level response: endgame_score, non_endgame_score, score_difference (signed), overall_score, material_rows (always 3)
- `EndgameOverviewResponse.score_gap_material` — new field added to existing response model

### Service Logic (`app/services/endgame_service.py`)

- `_wdl_to_score(wdl)` — converts WDL summary to score: `(win_pct + draw_pct/2) / 100`; returns 0.0 for empty WDL
- `_compute_verdict(row_score, overall_score)` — good/ok/bad relative to overall with -0.05 threshold
- `_MATERIAL_BUCKET_LABELS` — display labels dict for all three buckets
- `_compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)` — zero extra DB queries; deduplicates by game_id; assigns buckets using user_material_imbalance only (no persistence check); always returns all 3 material_rows
- `_get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, entry_rows)` — pure function extracted from `get_endgame_performance` body, accepts pre-fetched rows
- `get_endgame_overview` refactored to fetch `entry_rows` once and share across stats, performance, and score_gap_material (eliminates one redundant `query_endgame_entry_rows` call that previously ran twice per overview request)

### Tests

- `TestScoreGapMaterial` (20 tests): covers `_wdl_to_score`, `_compute_verdict`, `_compute_score_gap_material` — bucket assignment (ahead/equal/behind with boundary cases), deduplication, None imbalance exclusion, empty rows, signed score_difference, weighted overall_score, no-persistence-check invariant
- `TestGetEndgameOverview` (3 tests): updated to mock repository layer (`query_endgame_entry_rows`, `query_endgame_performance_rows`, `count_filtered_games`) instead of old service-level mocks; asserts `score_gap_material is not None`
- `TestOverviewScoreGapMaterial` (1 test): HTTP integration test asserting `score_gap_material` key and shape in `GET /api/endgames/overview` response

## Commits

| Hash | Message |
|------|---------|
| 9616556 | feat(53-01): add score gap & material breakdown backend schemas and service logic |
| 70dafc2 | test(53-01): add TestScoreGapMaterial unit tests and router integration test |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all three material_rows are fully computed from real entry_rows data.

## Self-Check: PASSED

- `app/schemas/endgames.py` — contains `class MaterialRow`, `class ScoreGapMaterialResponse`, `MaterialBucket`, `Verdict`, `score_gap_material` field
- `app/services/endgame_service.py` — contains `_wdl_to_score`, `_compute_verdict`, `_compute_score_gap_material`, `_get_endgame_performance_from_rows`
- Commits 9616556 and 70dafc2 verified in git log
- `uv run ty check app/ tests/` — 0 errors
- `uv run ruff check .` — 0 errors
- `uv run pytest` — 625 passed, 1 skipped
