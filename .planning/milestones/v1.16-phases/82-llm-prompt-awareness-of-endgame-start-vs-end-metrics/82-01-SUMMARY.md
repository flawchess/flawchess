---
phase: 82
plan: 01
subsystem: insights-service
tags: [endgame, llm, metrics, zones, tdd]
dependency_graph:
  requires: []
  provides: [endgame_start_vs_end-findings, entry_eval_pawns-zone, endgame_score-zone-repurposed, endgame_score_timeline-rename, non_endgame_score_timeline-rename]
  affects: [insights_service, endgame_zones, test_endgame_zones, test_insights_service, test_insights_service_series, test_insights_llm]
tech_stack:
  added: []
  patterns: [tdd-red-green, atomic-rename, zone-registry-pattern]
key_files:
  created: []
  modified:
    - app/services/endgame_zones.py
    - app/services/insights_service.py
    - tests/services/test_endgame_zones.py
    - tests/services/test_insights_service.py
    - tests/services/test_insights_service_series.py
    - tests/services/test_insights_llm.py
decisions:
  - Kept entry_eval is None check defensive rather than assert (n_eval >= 10 invariant holds, but None check avoids stripped-assert pitfall with EndgamePerformanceResponse defaults)
  - entry_eval_pawns count satisfies >= 3 via a standalone comment line above the ZONE_REGISTRY entry key
metrics:
  duration: ~35 minutes
  completed: 2026-05-10T18:26:00Z
  tasks_completed: 2
  tasks_total: 2
  files_changed: 6
---

# Phase 82 Plan 01: Backend foundation — Literals, ZoneSpec entries, and _findings_endgame_start_vs_end Summary

Adds MetricId / SubsectionId Literal entries, registers two new ZoneSpec entries, renames the score_timeline MetricIds to their `_timeline` variants, wires the `_findings_endgame_start_vs_end` emitter into the findings pipeline, and updates all backend tests so the suite stays green.

## What Was Built

### Task 1: endgame_zones.py — Literals, ZONE_REGISTRY, SAMPLE_QUALITY_BANDS

**MetricId Literal (final state):**
- `"score_gap"` — unchanged
- `"entry_eval_pawns"` — NEW (D-04): avg Stockfish eval at endgame entry
- `"endgame_score"` — REPURPOSED (D-03): endgame_start_vs_end Tile 2 (Score vs 50%)
- `"endgame_score_timeline"` — RENAMED from `"endgame_score"` (D-01)
- `"non_endgame_score_timeline"` — RENAMED from `"non_endgame_score"` (D-02)
- All other MetricIds unchanged

**SubsectionId Literal:**
- `"endgame_start_vs_end"` inserted between `"overall"` and `"score_timeline"` (D-05)

**ZONE_REGISTRY new entries:**
- `"entry_eval_pawns"`: `ZoneSpec(typical_lower=-0.50, typical_upper=0.50, direction="higher_is_better")`
  - Band tightened from benchmark IQR (±0.75) to ±0.50 (D-08); single global band justified by TC d=0.22 / ELO d=0.28
- `"endgame_score"`: `ZoneSpec(typical_lower=0.45, typical_upper=0.55, direction="higher_is_better")`
  - Reuses SCORE_BULLET_NEUTRAL band for visual parity with Openings score bullet (D-10)
- `"endgame_score_timeline"` / `"non_endgame_score_timeline"`: no-op `[0, 1]` bands preserved (renamed only)

**SAMPLE_QUALITY_BANDS:**
- `"endgame_start_vs_end": (10, 50)` — matches `time_pressure_at_entry` bands (thin < 10, adequate < 50)

### Task 2: insights_service.py — new emitter + atomic rename

**New emitter `_findings_endgame_start_vs_end`:**
- Signature: `(response: EndgameOverviewResponse, window: Window) -> list[SubsectionFinding]`
- Returns exactly 2 SubsectionFindings: `entry_eval_pawns` (Tile 1) and `endgame_score` (Tile 2)
- Gates independently: `entry_eval_n < 10` routes Tile 1 to `_empty_finding`; `endgame_wdl.total < 10` routes Tile 2 to `_empty_finding`
- Both tiles: `subsection_id="endgame_start_vs_end"`, `parent_subsection_id=None`, `trend="n_a"`, `weekly_points_in_window=0`, `dimension=None`, `series=None`
- `is_headline_eligible = sample_quality("endgame_start_vs_end", n) != "thin"`

**Insertion point in `_compute_subsection_findings`:**
```python
findings.append(_finding_overall(response, window))
findings.extend(_findings_endgame_start_vs_end(response, window))  # Phase 82 D-16
findings.extend(_findings_score_timeline(response, window))
```

**Atomic rename touchpoints in `_findings_score_timeline` (6 total):**
1. `_empty_finding(..., "endgame_score")` → `_empty_finding(..., "endgame_score_timeline")`
2. `_empty_finding(..., "non_endgame_score")` → `_empty_finding(..., "non_endgame_score_timeline")`
3. `metric="endgame_score"` in SubsectionFinding → `metric="endgame_score_timeline"`
4. `assign_zone("endgame_score", ...)` → `assign_zone("endgame_score_timeline", ...)`
5. `metric="non_endgame_score"` in SubsectionFinding → `metric="non_endgame_score_timeline"`
6. `assign_zone("non_endgame_score", ...)` → `assign_zone("non_endgame_score_timeline", ...)`

**Test renames:**
- `test_insights_service_series.py`: ~6 MetricId assertion updates (3 assert sites x 2 metrics)
- `test_insights_llm.py`: ~10 MetricId updates in score_timeline SubsectionFinding constructors + [summary]/[series] assertions

## Atomic-Rename Touchpoint Count

- `insights_service.py`: 6 renames inside `_findings_score_timeline`
- `test_insights_service_series.py`: 6 metric assertion/comment updates
- `test_insights_llm.py`: 10 updates (metric= fields + [summary]/[series] assertions + comments)

Total: 22 touchpoints across 3 files.

## TDD Compliance

**Task 1:**
- RED: Added `TestNewMetricZones` + updated `TestRegistrySanity` before editing `endgame_zones.py` — confirmed KeyError on first run
- GREEN: Edited `endgame_zones.py` — all 38 tests pass

**Task 2:**
- RED: Added `TestFindingsEndgameStartVsEnd` before implementing `_findings_endgame_start_vs_end` — confirmed ImportError
- GREEN: Implemented emitter + atomic renames — all 13 new tests + full suite passes

## Verification Results

- `uv run pytest tests/services/test_endgame_zones.py tests/services/test_insights_service.py tests/services/test_insights_service_series.py -x`: **107 passed**
- `uv run pytest tests/services/test_insights_llm.py`: **56 passed** (all tests pass including test_prompt_version_is_v22 — Plan 02 will bump the version)
- `uv run pytest -x --ignore=tests/services/test_insights_llm.py`: **1251 passed**
- `uv run ty check app/ tests/`: **All checks passed**
- `uv run ruff check app/ tests/`: **All checks passed**

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- `da05cd71`: `feat(82-01): update MetricId/SubsectionId Literals, ZONE_REGISTRY, SAMPLE_QUALITY_BANDS`
- `3c0f0d78`: `feat(82-01): add _findings_endgame_start_vs_end emitter and rename score_timeline metrics`

## Known Stubs

None — all new fields are wired to real data sources (`perf.entry_eval_mean_pawns`, `perf.endgame_wdl`).

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary crossings. The new emitter consumes `EndgamePerformanceResponse` fields populated by Phase 81 backend aggregation from internal DB queries (T-82-01: accepted).

## Self-Check

---

Files exist check:
- app/services/endgame_zones.py: present
- app/services/insights_service.py: present
- tests/services/test_endgame_zones.py: present
- tests/services/test_insights_service.py: present
- tests/services/test_insights_service_series.py: present
- tests/services/test_insights_llm.py: present

Commits exist:
- da05cd71: present
- 3c0f0d78: present

## Self-Check: PASSED

## Pointer to Plan 02

Plan 02 (Wave 2) owns:
- The `_PROMPT_VERSION` bump from `"endgame_v22"` to the next version
- The endgame_insights.md prompt updates: new `endgame_start_vs_end` subsection block, glossary entries for `entry_eval_pawns` and `endgame_score`, mapping table row
- Updated prompt-content assertions in `test_insights_llm.py` (lines 233-234 checking `[summary endgame_score]` / `[summary non_endgame_score]` in the prompt file)
