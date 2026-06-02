---
phase: 102-endgame-llm-statistical-reasoning-rework-v1-23
plan: 04
subsystem: api
tags: [llm, insights, endgame, percentile, findings, schema]

# Dependency graph
requires:
  - phase: 102-endgame-llm-statistical-reasoning-rework-v1-23
    plan: 01
    provides: "pctl= annotations wired to 2 page-level metrics; time_pressure_cards + metric_percentiles on EndgameTabFindings"
  - phase: 97-endgame-metrics-cards
    provides: "PerTcBucketStats.percentile/rate_percentile + per-TC endgame_metrics_cards on EndgameOverviewResponse"
  - phase: 94-endgame-percentiles
    provides: "TimePressureTcCard percentile triplets; rating_anchors on EndgameOverviewResponse"
provides:
  - "MetricPercentileRecord schema: enriched per-metric record with percentile + value + n_games + anchor + tc"
  - "per_tc_metric_percentiles field on EndgameTabFindings: keyed '{metric}:{tc}', covers all 11 percentile-bearing metrics"
  - "Enriched pctl= token in prompt: 'pctl=N (vs ~A-rated {tc} peers | n_games=M | value=V)'"
  - "D-04 reversal: zone OR extreme-pctl (< 25 / > 75) is now the narration gate; percentile is primary preferred signal"
  - "Recovery naming bridge: 'recovery_score_gap' (DB) <-> 'score_gap_recov' (SubsectionFinding)"
  - "_PROMPT_VERSION endgame_v37 with full v37 changelog entry"
affects: [insights_service, insights_llm, insights schema, endgame_insights prompt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MetricPercentileRecord: richer than flat float; value field is in UI scale (×100 of DB fraction)"
    - "per_tc_metric_percentiles keying: '{metric_id}:{tc}' compound key; bridge alias for recovery naming gap"
    - "_lookup_pctl_record: checks page-level dict first, then per-TC dict with tc parsing from dim_key"
    - "_build_pctl_token: builds enriched pctl= token string from MetricPercentileRecord"
    - "_dominant_per_tc_row: picks max n_games row for page-level anchor attribution"

key-files:
  created: []
  modified:
    - app/schemas/insights.py
    - app/services/insights_service.py
    - app/services/insights_llm.py
    - app/prompts/endgame_insights.md
    - tests/services/test_insights_llm.py
    - tests/test_insights_schema.py

key-decisions:
  - "D-04 reversed: percentile is now a primary/preferred narration trigger (zone OR extreme-pctl gate, thresholds 25/75)"
  - "MetricPercentileRecord.value is in UI scale (×100 from DB fraction) so the pctl= token value= field matches the LLM payload mean= values"
  - "Recovery naming bridge: both 'score_gap_recov:tc' and 'recovery_score_gap:tc' keys are written in per_tc_metric_percentiles so renderers can look up either name"
  - "Page-level anchor attribution: _dominant_per_tc_row picks the TC with most games from score_gap_per_tc / achievable_score_gap_per_tc breakdown rows"
  - "cohort_anchors kwarg kept on _render_summary_block for backwards compat but no longer used for anchor resolution (record already carries the anchor)"
  - "Double-narration rule in prompt: pick Score-Gap or raw-rate percentile, not both for the same metric in one bullet"

patterns-established:
  - "_lookup_pctl_record: canonical lookup dispatches page-level first, then per-TC via dim_key parsing"
  - "pctl= token enrichment pattern: anchor + n_games + value appended in parentheses when present"

requirements-completed: []

# Metrics
duration: 60min
completed: 2026-06-01
---

# Phase 102 Plan 04: Percentile Enrichment and D-04 Reversal Summary

Enrich the LLM payload's percentile annotations and reverse the old D-04 gate rule so percentile becomes a primary, preferred narration signal alongside zone.

## What Was Built

### 1. MetricPercentileRecord Schema (app/schemas/insights.py)

Added `MetricPercentileRecord` Pydantic model replacing the flat `dict[str, float]` in `EndgameTabFindings.metric_percentiles`. Fields: `percentile`, `value` (UI scale), `n_games`, `anchor` (blended rating), `tc` (time control, None for page-level metrics).

Added `per_tc_metric_percentiles: dict[str, MetricPercentileRecord] | None` field on `EndgameTabFindings` for all 11 per-TC metrics, keyed as `"{metric_id}:{tc}"`.

### 2. Service Wiring (app/services/insights_service.py)

`compute_findings` now populates:
- `metric_percentiles`: score_gap and achievable_score_gap with enriched records; anchor from dominant per-TC breakdown row.
- `per_tc_metric_percentiles`: all 9 per-TC records covering score_gap_conv/parity/recov (ΔES-gap), conversion_win_pct/parity_score_pct/recovery_save_pct (raw-rate), time_pressure_score_gap/clock_gap/net_flag_rate per TC card.
- Recovery naming bridge: both `score_gap_recov:{tc}` and `recovery_score_gap:{tc}` keys written for the recovery bucket.

Helper `_dominant_per_tc_row` selects the TC with the most games from the per-TC breakdown for page-level anchor attribution.

### 3. Prompt Rendering (app/services/insights_llm.py)

- `_build_pctl_token`: builds enriched token string `pctl=N (vs ~A-rated {tc} peers | n_games=M | value=V)` from a `MetricPercentileRecord`.
- `_lookup_pctl_record`: dispatches lookup — page-level dict first, then per-TC dict with tc parsed from dim_key.
- `_summary_window_line`: signature updated to accept `pctl_record: MetricPercentileRecord | None` (replaces `percentile: float | None, cohort_label: str | None`).
- `_render_summary_block`: updated to use `_lookup_pctl_record`; `per_tc_metric_percentiles` threaded through.
- `_render_subsection_block`: `per_tc_metric_percentiles` added as parameter and forwarded to `_render_summary_block`.
- `_assemble_user_prompt`: passes `findings.per_tc_metric_percentiles` to `_render_subsection_block`.

### 4. Prompt Teaching (app/prompts/endgame_insights.md)

Rewrote "Percentile annotations (pctl=)" section:
- **D-04 reversed**: percentile is PRIMARY, PREFERRED signal. Gate: zone non-typical OR (pctl < 25 or pctl > 75 AND quality adequate/rich).
- Lead with percentile framing when pctl= present; use zone as supporting context.
- Rationale stated: percentile is cohort-relative vs equally-strong peers over ~3000 recent games; zone is vs whole Lichess sample.
- New enriched token format documented with all context fields.
- Reliability context: n_games calibration guidance.
- Double-narration rule: pick Score-Gap or raw-rate, not both.
- Three worked examples: page-level score_gap, per-TC net_flag_rate, per-TC Conversion Score Gap.
- Example of now-allowed story: extreme pctl inside typical zone.
- D-01/D-02/D-05/D-08 guards preserved; no CI bounds, no p-values.

### 5. Version Bump

`_PROMPT_VERSION`: `endgame_v36` -> `endgame_v37` with full changelog entry summarizing all changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed insights_service rate_finding_metric derivation**
- **Found during:** Task 1 (implementing per-TC metric wiring)
- **Issue:** The original draft had a convoluted string-replace approach to map bucket attribute names to rate finding metric ids.
- **Fix:** Replaced with a clean tuple of `(bucket_attr, gap_finding_metric, rate_finding_metric, db_gap_metric)` used in a loop.
- **Files modified:** app/services/insights_service.py

**2. [Rule 2 - Missing critical] Added recovery naming bridge to both dicts**
- **Found during:** Task 1 implementation
- **Issue:** The plan noted the naming gap between "recovery_score_gap" (DB) and "score_gap_recov" (SubsectionFinding) but the bridge needed to be written bidirectionally so any lookup strategy works.
- **Fix:** Both `score_gap_recov:{tc}` and `recovery_score_gap:{tc}` keys are written in per_tc_metric_percentiles.

**3. [Rule 1 - Bug] Fixed "ΔES" appearing in prompt outside forbidden-words context**
- **Found during:** Test run (test_prompt_glossary_defines_endgame_type_score_gap)
- **Issue:** New "Double-narration rule" and "Worked example" in prompt used "ΔES-gap" as a descriptor.
- **Fix:** Replaced with "Score-Gap" (user-facing vocabulary) in both locations.
- **Commit:** fec50b80

## Self-Check: PASSED

- [x] MetricPercentileRecord class exists in app/schemas/insights.py
- [x] per_tc_metric_percentiles field on EndgameTabFindings
- [x] _build_pctl_token in app/services/insights_llm.py
- [x] _lookup_pctl_record in app/services/insights_llm.py
- [x] _PROMPT_VERSION = "endgame_v37"
- [x] Prompt section rewritten with D-04 reversal
- [x] All 2224 tests pass, 10 skipped
- [x] ruff format + check clean
- [x] ty check zero errors
- [x] Commit fec50b80 verified in git log
