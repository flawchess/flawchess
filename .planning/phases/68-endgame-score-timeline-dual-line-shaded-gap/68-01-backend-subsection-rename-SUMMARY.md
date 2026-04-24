---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 01
subsystem: insights
tags:
  - insights
  - endgame
  - backend
  - schema
requires:
  - SubsectionId `score_gap_timeline` literal (to be renamed)
  - ScoreGapTimelinePoint Pydantic schema + TS interface
  - _finding_score_gap_timeline builder in insights_service
  - suppress_summary carve-out in insights_llm._render_subsection_block
provides:
  - SubsectionId `score_timeline` (renamed member)
  - ScoreGapTimelinePoint.endgame_score / non_endgame_score (Py + TS)
  - _findings_score_timeline builder (list of TWO findings per window)
  - Two-summary + two-series emitter output (natural, no carve-out)
  - `part=endgame` / `part=non_endgame` dim-tagged series headers
affects:
  - Plan 02 (frontend dual-line chart) — consumes endgame_score / non_endgame_score directly
  - Plan 03 (prompt simplification) — will drop the score_gap framing rule + rename subsection refs
tech-stack:
  added: []
  patterns:
    - Per-dimension fanout — same shape as endgame_elo_timeline per-combo series
    - Finding ordering as deterministic emission contract (endgame before non_endgame)
key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/schemas/insights.py
    - app/services/endgame_service.py
    - app/services/endgame_zones.py
    - app/services/insights_llm.py
    - app/services/insights_service.py
    - frontend/src/types/endgames.ts
    - tests/services/test_insights_llm.py
    - tests/services/test_insights_service_series.py
    - tests/test_endgame_service.py
    - tests/test_insights_schema.py
decisions:
  - Pinned `score_timeline` at weekly granularity across both windows via a new branch in `_series_granularity` — matches the ISO-week grain of `_compute_score_gap_timeline` and the two-line chart's weekly points. Same shape pattern as `type_win_rate_timeline` (always-monthly) but inverted.
  - Series-block headers now carry the dim_key suffix (`[series <metric>, <window>, <granularity>, part=endgame]`) via a minimal extension to `_render_series_block`. Reuses `_dim_key_for_finding` so the header format mirrors the summary-block labelling.
  - Both per-part findings share `metric="score_gap"` and the aggregate `value` (response.score_gap_material.score_difference). Zone is the same across both findings; differentiation is entirely by `dimension={"part": ...}`. Non-endgame finding has `is_headline_eligible=False` so it never drives an insight on its own.
metrics:
  duration: ~25m
  completed: 2026-04-24
---

# Phase 68 Plan 01: Backend Subsection Rename Summary

**One-liner:** Renamed `score_gap_timeline` → `score_timeline`, switched the subsection from a single signed-difference series to TWO per-part absolute-score findings per window, and deleted the `suppress_summary` carve-out in the LLM payload emitter.

## What Changed

### Subsection rename (Python-wide)

- `app/services/endgame_zones.py`: `SubsectionId` literal member `score_gap_timeline` → `score_timeline`. `SAMPLE_QUALITY_BANDS` key renamed with the same `(10, 52)` bounds.
- `app/services/insights_service.py`: `_TIMELINE_SUBSECTION_IDS` frozenset member renamed.
- `app/services/insights_llm.py`: `_TIMELINE_SUBSECTION_IDS` + `_SECTION_LAYOUT` entry renamed.
- `app/schemas/insights.py`: docstring comment renamed.
- Per W5, `MetricId` was **not** changed — both new findings use the existing `"score_gap"` metric so the zone mapping (`ZONE_REGISTRY["score_gap"]`) applies unchanged. The two findings are distinguished by `dimension={"part": "endgame"|"non_endgame"}`.

### ScoreGapTimelinePoint schema extension (Py + TS, atomic)

Both Pydantic and hand-maintained TypeScript interface now carry two new required float fields:

- `endgame_score: float` — absolute rolling-window mean score (0.0-1.0) for endgame games only.
- `non_endgame_score: float` — absolute rolling-window mean score (0.0-1.0) for non-endgame games only.

Invariant: `abs((endgame_score - non_endgame_score) - score_difference) < 1e-9` per bucket.

`_compute_score_gap_timeline` in `app/services/endgame_service.py` already computed `endgame_mean` and `non_endgame_mean` locals — this plan just persists them onto the emitted `data_by_week[...]` dict so they flow through to the schema.

### Finding builder: two findings per window

`_finding_score_gap_timeline` (single finding) replaced by `_findings_score_timeline` (returns `list[SubsectionFinding]` with exactly two entries per window):

```
Finding A: subsection_id="score_timeline", metric="score_gap",
           dimension={"part": "endgame"},
           value=aggregate score_difference,
           zone=assign_zone("score_gap", aggregate),
           series=[TimePoint(date, endgame_score, endgame_game_count) for p in timeline],
           is_headline_eligible = trend != "n_a"

Finding B: subsection_id="score_timeline", metric="score_gap",
           dimension={"part": "non_endgame"},
           value=aggregate score_difference,   # same aggregate value
           zone=same zone as A,
           series=[TimePoint(date, non_endgame_score, non_endgame_game_count) for p in timeline],
           is_headline_eligible = False        # partner never a headline on its own
```

Order matters: endgame finding emits first so the prompt reads "your endgame side first". The per-part series uses `_weekly_points_to_time_points(..., "last_3mo")` so the helper's pass-through branch is taken and the points stay weekly in both windows (no monthly resampling).

### LLM payload emitter: two-summary + two-series naturally

- Deleted `suppress_summary = subsection_id == "score_gap_timeline"` branch entirely from `_render_subsection_block`. The remaining per-finding summary loop now emits two `[summary score_gap | part=X]` blocks for this subsection — one per finding — which is exactly what Plan 03 wants.
- `_series_granularity` gained a branch pinning `score_timeline` at `"weekly"` across both windows (matches the ISO-week grain of the backend computation).
- `_render_series_block` now suffixes `, <dim_key>` onto the header when the finding carries a dimension. Mirrors the labelling style `_dim_key_for_finding` produces for summary blocks. This is how `endgame_elo_timeline` already groups its per-combo series; the tag syntax is consistent across all dimensioned subsections now.

### Rendered subsection (example)

```
### Subsection: score_timeline
[summary score_gap | part=endgame]
  all_time: mean=+5, n=487, buckets=52 (weekly), zone=typical (typical -10 to +10), quality=rich, trend=improving, std=3
  last_3mo: mean=+5, n=487, buckets=13 (weekly), zone=typical (typical -10 to +10), quality=adequate, trend=improving, std=2
  shift=+0
[series score_gap, all_time, weekly, part=endgame]
2024-01-01: +55 (n=12)
2024-01-08: +56 (n=14)
...
[summary score_gap | part=non_endgame]
  all_time: mean=+5, n=487, buckets=52 (weekly), zone=typical (typical -10 to +10), quality=rich, trend=improving, std=3
  last_3mo: mean=+5, n=487, buckets=13 (weekly), zone=typical (typical -10 to +10), quality=adequate, trend=improving, std=2
  shift=+0
[series score_gap, all_time, weekly, part=non_endgame]
2024-01-01: +50 (n=12)
2024-01-08: +50 (n=14)
...
```

Both summary blocks carry the **same** aggregate mean (the score_gap, narrated once per part), both resolve to the same zone. The series blocks carry **different** per-side absolute values. The prompt can then narrate "endgame side trending up from 55% to 60%, non-endgame flat at 50%" instead of "score_difference = 0.10".

## Deviations from Plan

None — plan executed as written. All W-notes and B4 option c directives applied:

- W5 honoured: `MetricId` unchanged; both findings keep `metric="score_gap"`.
- W7 honoured: weekly bucketing preserved end-to-end; no migration to monthly.
- B4 option c honoured: two `[summary score_timeline]` blocks emitted naturally via per-finding loop; no suppression mechanism.
- B3 honoured: TS interface fields added as `required`, not optional — Plan 02 can consume `p.endgame_score` / `p.non_endgame_score` directly without a fallback.

## Follow-ups

- **Plan 02 (frontend dual-line chart):** consumes `ScoreGapTimelinePoint.endgame_score` / `non_endgame_score` directly. The TS type change is the contract.
- **Plan 03 (prompt simplification):** `app/prompts/endgame_insights.md` still contains `score_gap_timeline` in 5 places (lines 137, 139, 298, 356, 371) plus the `score_gap` framing rule at ~line 290 — all explicitly out of scope for Plan 01 per the plan's success criteria. Plan 03 renames them to `score_timeline`, deletes the summary-per-metric exception paragraph at line 139, and bumps `prompt_version`.
- The `suppress_summary` branch is gone module-wide; Plan 03 can simplify the prompt without worrying about backend carve-outs.

## Verification

- `uv run ruff check app/ tests/` — clean
- `uv run ty check app/ tests/` — zero errors
- `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_service_series.py tests/services/test_insights_llm.py tests/test_insights_schema.py tests/test_endgame_service.py` — 351 passed
- Full non-DB test suite: `uv run pytest tests/ --ignore=tests/integration --ignore=tests/test_reclassify.py` — 1053 passed
- `cd frontend && npx tsc --noEmit` — clean
- `cd frontend && npm run lint` — clean
- `cd frontend && npm test -- --run` — 98 passed
- `grep -rn "score_gap_timeline" app/services/ app/schemas/ tests/services/` — only incidental variable names + one intentional Phase 68 docstring note remain
- `grep -n "suppress_summary" app/services/insights_llm.py` — zero matches

## Self-Check: PASSED

- bd7ab26 (Task 1) — FOUND
- 56559b1 (Task 2) — FOUND
- `app/schemas/endgames.py` — FOUND, `endgame_score` + `non_endgame_score` present
- `app/services/endgame_service.py` — FOUND, both fields populated in `data_by_week[...]`
- `app/services/endgame_zones.py` — FOUND, `score_timeline` member + SAMPLE_QUALITY_BANDS key
- `app/services/insights_service.py` — FOUND, `_findings_score_timeline` builder
- `app/services/insights_llm.py` — FOUND, `suppress_summary` removed, `_series_granularity` pins weekly, `_render_series_block` includes dim_key
- `frontend/src/types/endgames.ts` — FOUND, both new fields required
- Tests: all updates committed, test suites pass
