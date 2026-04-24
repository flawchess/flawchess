# Phase 63: Findings Pipeline & Zone Wiring - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning
**Requirements:** FIND-01, FIND-02, FIND-03, FIND-04, FIND-05

<domain>
## Phase Boundary

Backend-only. Build `app/services/insights_service.py` and `app/schemas/insights.py` that transform the existing `endgame_service.get_endgame_overview()` composite into a deterministic `EndgameTabFindings` object — per-subsection-per-window findings (zone, trend, sample_quality), four cross-section flags, and a stable `findings_hash`. No LLM, no new DB table, no frontend changes other than the small Recovery-band TS edit captured in the decisions below. Phases 64 (log table), 65 (LLM endpoint), 66 (frontend block), 67 (validation) build on top.

</domain>

<decisions>
## Implementation Decisions

### Constants & Colocation (FIND-02)

- **D-01:** Python is the authoritative home for gauge thresholds. Create `app/services/endgame_zones.py` exporting a structured registry `ZONE_REGISTRY: Mapping[MetricId, ZoneSpec]` (dataclass) plus an `assign_zone(metric_id, value) -> Zone` helper. Frontend gauge components currently hold these values inline (`EndgameScoreGapSection.tsx`, `EndgameClockPressureSection.tsx`); Python becomes source of truth.
- **D-02:** Add `scripts/gen_endgame_zones_ts.py` that emits `frontend/src/generated/endgameZones.ts` from the Python registry. The generated TS file IS committed. CI re-runs the generator and uses `git diff --exit-code` on the generated file to block drift. A separate Python test parses the inline constants in `EndgameScoreGapSection.tsx` and `EndgameClockPressureSection.tsx` (regex against the existing `FIXED_GAUGE_ZONES`, `ENDGAME_SKILL_ZONES`, `NEUTRAL_PCT_THRESHOLD`, `NEUTRAL_TIMEOUT_THRESHOLD`, `SCORE_GAP_NEUTRAL_MIN/MAX` literals) and asserts they equal the registry values; this catches drift until the FE consumers are switched in a follow-up.
- **D-03:** FE consumers (`EndgameScoreGapSection.tsx`, `EndgameClockPressureSection.tsx`, `EndgamePerformanceSection.tsx`) keep their current inline imports in Phase 63. Switching them to import from `frontend/src/generated/endgameZones.ts` is a follow-up quick task or rolls into Phase 66 (frontend insights block). Phase 63 itself stays backend-only as the roadmap states.
- **D-04:** Scope of constants moved: numeric thresholds only — `FIXED_GAUGE_ZONES` (per material bucket: conversion, even, recovery → conv/parity/recov), `ENDGAME_SKILL_ZONES`, `NEUTRAL_PCT_THRESHOLD`, `NEUTRAL_TIMEOUT_THRESHOLD`, `SCORE_GAP_NEUTRAL_MIN/MAX`, plus a new `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = 100` (see D-09). Color tokens stay in `frontend/src/lib/theme.ts` — backend never needs them.

### Zone Schema (FIND-01, FIND-02)

- **D-05:** `Zone = Literal["weak", "typical", "strong"]`. Three zones, not five. Maps 1:1 onto the existing 3-zone gauge bands so insights narrative and chart visuals "agree by construction" (FIND-02) without any FE change. SEED-003's 5-zone schema is aspirational — revisit in v1.12 alongside SEED-002 population baselines.
- **D-06:** `ZoneSpec` is a frozen dataclass with explicit fields: `typical_lower: float`, `typical_upper: float`, `direction: Literal["higher_is_better", "lower_is_better"]`. `assign_zone(metric_id, value) -> Zone` reads direction from the registry to map values correctly: Score Gap, Clock Diff, Conv/Parity/Recov, Endgame Skill = `higher_is_better`; Net Timeout Rate = `lower_is_better`. Signed-around-zero metrics (Score Gap, Clock Diff) use a centered typical band; the registry handles them via the same (typical_lower, typical_upper) pair (e.g., Score Gap: -0.10 / +0.10, Clock Diff: -10 / +10).
- **D-07:** Initial registry contents include all 10 subsection-level metrics — `score_gap`, `endgame_skill`, `conversion_win_pct`, `parity_score_pct`, `recovery_save_pct` (the latter three keyed under `FIXED_GAUGE_ZONES` per material bucket: `conversion`, `even`, `recovery`), `avg_clock_diff_pct`, `net_timeout_rate`, `endgame_elo_gap`. The bucket-keyed conversion metrics are looked up via `(metric_id, bucket)` rather than fanned-out top-level entries — keeps the `MetricId` namespace finite.
- **D-08:** `MetricId` is a `Literal[...]` type alias enumerating every metric in the registry. `assign_zone` accepts `MetricId | tuple[MetricId, MaterialBucket]` (or two overloads) so bucket-keyed lookups stay type-safe. Planner picks the cleanest signature.

### Cross-Section Flags & Bands (FIND-02, FIND-03)

- **D-09:** Ship FOUR cross-section flags. `FlagId = Literal["baseline_lift_mutes_score_gap", "clock_entry_advantage", "no_clock_entry_advantage", "notable_endgame_elo_divergence"]`. Threshold definitions, all referencing registry constants:
  - `baseline_lift_mutes_score_gap`: `endgame_skill.zone == "strong" AND score_gap.zone in {"typical", "weak"}`
  - `clock_entry_advantage`: `avg_clock_diff_pct > NEUTRAL_PCT_THRESHOLD` (currently 10)
  - `no_clock_entry_advantage`: `abs(avg_clock_diff_pct) <= NEUTRAL_PCT_THRESHOLD`
  - `notable_endgame_elo_divergence`: `max over (platform, tc) combos of abs(endgame_elo - actual_elo) > NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` (default 100). Closes SEED-003 regression assertion #5 (the LLM must not double-count Endgame Skill and Endgame ELO gap as independent corroborations).
- **D-10:** Recovery typical band re-centered to `[0.25, 0.35]` (was `[0.30, 0.40]`). This is the ONLY band change in Phase 63. Touches both `endgame_zones.py` (Python registry) and `frontend/src/components/charts/EndgameScoreGapSection.tsx` (`FIXED_GAUGE_ZONES.recovery` boundary, single-line edit). Pooled benchmark median is 0.32 — re-centering makes "typical" honest and aligns insights narrative with population reality. The CI parsing test from D-02 expects the new value on both sides.
- **D-11:** Other benchmark-recommended tightenings — Score Gap `±10pp → ±8pp`, Clock Diff `±10% → ±7%`, Endgame Skill upper `0.55 → 0.59` — are NOT in Phase 63 scope. Ship as a separate `/gsd-quick` task between Phase 64 and Phase 65 so the calibration change is reviewable in isolation.
- **D-12:** Flag rules locked per SEED-003. No tighter `baseline_lift` gate, no looser variant. All comparison thresholds reference registry constants so a future band change auto-propagates to the flags.

### Findings Schema & Quality Gates (FIND-01, FIND-04, FIND-05)

- **D-13:** `SubsectionFinding` carries `parent_subsection_id: str | None` (None for top-level findings; populated for `type_win_rate_timeline` pointing at `results_by_endgame_type`) and `is_headline_eligible: bool`. The latter is False when a gated timeline (`score_gap_timeline`, `clock_diff_timeline`) fails the trend-quality gate, demoting it to supporting. No `lookback_role` / `lookback_behavior` field — gating is precomputed implicitly via `is_headline_eligible`, not exposed to the LLM (per SEED-003).
- **D-14:** Endgame ELO fans out: one `SubsectionFinding` (subsection_id `endgame_elo_timeline`, metric `endgame_elo_gap`) per `(platform, time_control)` combo present in the user's data, with the per-combo `endgame_elo - actual_elo` as the value. Combo identity is encoded in a `dimension: dict[str, str] | None` field (e.g., `{"platform": "chess.com", "time_control": "blitz"}`) — keeps `value: float` contract intact. Findings volume is bounded (≤ 8 entries: 2 platforms × 4 time-controls).
- **D-15:** Trend-quality gate combines BOTH conditions per FIND-04: `weekly_points_in_window >= TREND_MIN_WEEKLY_POINTS` (default 20) AND `slope_to_volatility_ratio >= TREND_MIN_SLOPE_VOL_RATIO` (default 0.5 — placeholder, planner/researcher tunes against the SEED-001 fixture and revisits in Phase 67). Either failure → `trend = "n_a"`. Computation reuses the existing `_compute_weekly_rolling_series` pattern in `endgame_service.py`.
- **D-16:** Sample-quality bands are per-subsection in the registry: `SAMPLE_QUALITY_BANDS: dict[SubsectionId, tuple[int, int]]` mapping subsection_id to `(thin_max, adequate_max)` — `value < thin_max` → `thin`, `< adequate_max` → `adequate`, otherwise `rich`. Initial values to lock in the registry: `score_gap (50, 200)`, `results_by_endgame_type (10, 40)` per-type, others picked by the planner from the existing endgame_service queries (e.g., `endgame_metrics`, `time_pressure_at_entry`). Per-subsection denominators stay honest — type breakdown splits 5 ways, so its bands are 5× smaller.

### Claude's Discretion

- File layout details: `app/services/insights_service.py` (compute), `app/services/endgame_zones.py` (registry), `app/schemas/insights.py` (Pydantic schemas: `Zone`, `Trend`, `SampleQuality`, `Window`, `MetricId`, `SubsectionId`, `SectionId`, `FlagId`, `FilterContext`, `SubsectionFinding`, `EndgameTabFindings`), `scripts/gen_endgame_zones_ts.py` (codegen), `frontend/src/generated/endgameZones.ts` (output, committed), `tests/services/test_insights_service.py` (unit tests for zone assignment, flag computation, trend gating, hash stability), `tests/services/test_endgame_zones_consistency.py` (parses TS sources, asserts registry equivalence).
- `findings_hash` implementation: SHA256 of `EndgameTabFindings.model_dump_json(exclude={"as_of"})` with sorted keys. Use Pydantic v2's `model_dump_json` with `by_alias=False`; if Pydantic doesn't emit deterministically-sorted keys for nested dicts, post-process by serializing through `json.dumps(..., sort_keys=True, separators=(",", ":"))` on `model_dump(mode="json")`. Planner picks the cleanest path; the test asserts hash stability across two sessions.
- `FilterContext` field set: mirror SEED-003 verbatim — `recency`, `opponent_strength`, `color`, `time_controls`, `platforms`, `rated_only`. `color` and `rated_only` are included in the findings input (filter-faithful) even though they're not fed to the LLM (INS-03) — that's a Phase 65 prompt-assembly concern, not a Phase 63 schema concern.
- Empty-window handling: when a subsection has zero qualifying games for a window (e.g., `last_3mo` with tight filters), emit a finding with `value=NaN` (or `0.0`), `zone="typical"`, `trend="n_a"`, `sample_size=0`, `sample_quality="thin"`, `is_headline_eligible=False`. Planner picks the exact null-value convention; whichever is chosen, document it in the schema docstring so Phase 65 prompt-assembly knows to skip rather than render.
- Bucket-aware Conv/Parity/Recov findings: emit one finding per `(material_bucket, metric)` pair under `endgame_metrics` subsection. Bucket appears in `dimension` field (consistent with D-14's combo handling). Roughly 9 entries (3 buckets × 3 metrics) plus 1 for `endgame_skill`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/seeds/SEED-003-llm-based-insights.md` — full architecture rationale, prompt design, schema sketches, antipattern list. Read end-to-end. The "What the findings pipeline computes", "Zone bands", "Naming collisions to watch", and "Antipatterns to catch in review" sections are load-bearing.
- `.planning/REQUIREMENTS.md` §FIND-01..FIND-05 — locked requirements for this phase.
- `.planning/PROJECT.md` §"v1.11 LLM-first Endgame Insights" — milestone goal, target features, key context.
- `reports/benchmarks-2026-04-18.md` — population calibration source. Read alongside SEED-003's "Zone bands" section. Background context only per FIND-02 — Phase 63 honors the current in-code constants except for the Recovery re-center (D-10).

### Existing Backend (read-only inputs)
- `app/services/endgame_service.py::get_endgame_overview` (line 1895) — the composite that `insights_service.py` consumes. Returns `EndgameOverviewResponse`. NEVER bypass with direct repository calls (SEED-003 antipattern).
- `app/services/endgame_service.py::_compute_weekly_rolling_series` — existing weekly-bucketing pattern; reuse for trend detection.
- `app/services/endgame_service.py` Phase-57 `_endgame_skill_from_bucket_rows` — Endgame Skill formula reference.
- `app/schemas/endgames.py::EndgameOverviewResponse` (line 413) and constituent schemas (`EndgameStatsResponse`, `EndgamePerformanceResponse`, `EndgameTimelineResponse`, `ScoreGapMaterialResponse`, `ClockPressureResponse`, `TimePressureChartResponse`, `EndgameEloTimelineResponse`) — the data shapes feeding the findings pipeline.
- `app/repositories/query_utils.py::apply_game_filters` — referenced indirectly via `get_endgame_overview`; insights_service inherits filter semantics by construction.

### Existing Frontend (constants source — read for current values, regex-parse in test)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` lines 79–101 — `FIXED_GAUGE_ZONES`, `ENDGAME_SKILL_ZONES` definitions. The Recovery boundary on line 79 area gets edited per D-10.
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` lines 18, 23 — `NEUTRAL_PCT_THRESHOLD = 10`, `NEUTRAL_TIMEOUT_THRESHOLD = 5`.
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` lines 36–46 — `SCORE_GAP_NEUTRAL_MIN/MAX = ±0.10`, `SCORE_GAP_TIMELINE_NEUTRAL_PCT = 10`.

### Project Conventions
- `CLAUDE.md` §"Coding Guidelines" — type safety, ty compliance, no magic numbers, `Literal[...]` for enums.
- `CLAUDE.md` §"Critical Constraints" — `AsyncSession` not safe for `asyncio.gather`. (Phase 63 has no DB calls of its own; relevant only insofar as `insights_service` runs synchronous Python over the data `endgame_service` already fetched.)
- `CLAUDE.md` §"Error Handling & Sentry" — `sentry_sdk.capture_exception` in non-trivial except blocks; use `set_context` for variable data.
- `CLAUDE.md` §"Frontend" — theme constants in `theme.ts` (only relevant here because we keep colors out of the migration per D-04).

### Related Quick Tasks
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` — Endgame Skill composite + `ENDGAME_SKILL_ZONES` introduction; relevant to the registry entries.
- `.planning/quick/260416-pkx-aggregate-time-pressure-data-in-backend-/` — Time Pressure backend aggregation; relevant to `time_pressure_vs_performance` subsection finding.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`endgame_service.get_endgame_overview`** (app/services/endgame_service.py:1895) — the only entry point `insights_service.py` should call to read user data. Composite returns all 7 data shapes the subsections render. FIND-01 enforces this.
- **`_compute_weekly_rolling_series`** (app/services/endgame_service.py) — existing weekly-bucketing pattern for the timeline subsections. Reuse as-is for trend slope/volatility computation; do not reimplement.
- **`endgameSkill()` formula** — already inlined in `endgame_service.py` for `endgame_elo_timeline`. The same per-bucket computation drives `endgame_skill` zone assignment.
- **`EndgameOverviewResponse` and its child schemas** (app/schemas/endgames.py:413) — well-typed Pydantic models; insights_service reads from these without unpacking.
- **Frontend gauge constants** — current source of truth (until Phase 63 inverts that). Their literal values determine the registry's initial values (modulo D-10's Recovery edit).

### Established Patterns
- **Service-only access from upstream services** — insights_service consumes endgame_service, not repositories. Mirrors the layering CLAUDE.md mandates (routers → services → repositories) and matches FIND-01.
- **Pydantic v2 with `Literal[...]` for enums** — every state field on the schemas (`Zone`, `Trend`, `SampleQuality`, `Window`, `MetricId`, `SubsectionId`, `SectionId`, `FlagId`, `direction`) is a `Literal`. ty compliance follows.
- **No magic numbers** — every threshold lives in `endgame_zones.py` as a named constant or registry entry; both the flag-rule code and the assign_zone helper read from there.
- **Codegen-and-commit + CI diff guard** — pattern to consider for the Python→TS bridge. Not previously used in this repo, so the planner should design the guard wiring fresh; common form is `python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts`.

### Integration Points
- **Phase 65 (LLM endpoint)** consumes `insights_service.compute_findings(filter_context, session, user_id) -> EndgameTabFindings`. Schema is the contract; downstream prompt-assembly reads field names directly. Lock field names carefully — renaming after Phase 65 ships forces a prompt revision.
- **Phase 67 (regression test)** depends on `findings_hash` being stable across Python sessions — implementation must avoid Python's hash randomization, dict ordering quirks, and float repr differences (use `json.dumps(..., sort_keys=True, separators=(",", ":"))` on `model_dump(mode="json")`).
- **`tests/services/test_insights_service.py`** is in scope for Phase 63. Cover at minimum: zone assignment for each direction (higher/lower-is-better), each flag's true/false branches, trend gating (count fail, ratio fail, both pass), hash stability across sessions. Use the existing `seeded_user` fixture (Phase 61) where helpful.
- **`tests/services/test_endgame_zones_consistency.py`** is the FE-drift guard from D-02.

</code_context>

<specifics>
## Specific Ideas

- **MetricId Literal** explicitly enumerates: `"score_gap"`, `"endgame_skill"`, `"conversion_win_pct"`, `"parity_score_pct"`, `"recovery_save_pct"`, `"avg_clock_diff_pct"`, `"net_timeout_rate"`, `"endgame_elo_gap"`. Per-bucket variants of conversion/parity/recovery use the bucket-keyed lookup (D-07).
- **SubsectionId Literal** mirrors SEED-003's "Sections in Scope" table: `"overall"`, `"score_gap_timeline"`, `"endgame_metrics"`, `"endgame_elo_timeline"`, `"time_pressure_at_entry"`, `"clock_diff_timeline"`, `"time_pressure_vs_performance"`, `"results_by_endgame_type"`, `"conversion_recovery_by_type"`, `"type_win_rate_timeline"`. Total 10.
- **SectionId Literal** = `"overall" | "metrics_elo" | "time_pressure" | "type_breakdown"`. Not on `SubsectionFinding` directly — section grouping happens at `EndgameTabFindings` consumption time (Phase 65).
- **FilterContext** is a dataclass-like Pydantic model mirroring the existing `apply_game_filters` arg surface — `recency`, `opponent_strength`, `color`, `time_controls`, `platforms`, `rated_only`. Field names match the `endgame_service.get_endgame_overview` parameters (`opponent_strength` = `Literal["any", "stronger", "similar", "weaker"]` per the existing signature).
- **Recovery band edit (D-10)** touches exactly two source locations: `app/services/endgame_zones.py` (initial registry) and `frontend/src/components/charts/EndgameScoreGapSection.tsx` (`FIXED_GAUGE_ZONES.recovery` typical-band coordinates). The CI consistency test catches it if either is out of sync.
- **ZoneSpec dataclass** (illustrative — planner finalizes):
  ```python
  @dataclass(frozen=True)
  class ZoneSpec:
      typical_lower: float
      typical_upper: float
      direction: Literal["higher_is_better", "lower_is_better"]
  ```
  Plus a separate `BUCKETED_ZONE_REGISTRY: Mapping[Literal["conversion_win_pct", "parity_score_pct", "recovery_save_pct"], Mapping[MaterialBucket, ZoneSpec]]` for the per-bucket Conv/Parity/Recov entries.
- **Trend computation note** — slope/volatility is computed on the weekly-rolling series for the window in question. For `last_3mo` window with weekly resolution, ~13 weekly points exist by definition, so the count gate fails by construction → trend always `n_a` for `last_3mo`. This is correct: trend is an `all_time`-window concern. The planner should confirm and document this in the schema docstring so the LLM prompt knows to look at `all_time` for trend, `last_3mo` for "recent state".

</specifics>

<deferred>
## Deferred Ideas

- **5-zone schema (`very_weak / weak / typical / strong / very_strong`)** — revisit in v1.12 alongside SEED-002 population baselines. The 3-zone collapse is the MVP simplification; SEED-002's larger benchmark sample (rating-stratified Lichess data) makes p10/p90 estimates non-noisy enough to justify the extra zones.
- **Benchmark-recommended band tightenings** — Score Gap `±10pp → ±8pp`, Clock Diff `±10% → ±7%`, Endgame Skill upper `0.55 → 0.59`. Ship as a `/gsd-quick` task between Phase 64 and Phase 65 (coordinated Python+TS edit, easy to review/revert in isolation).
- **Frontend gauge components consume `frontend/src/generated/endgameZones.ts`** — quick task or rolled into Phase 66 (frontend insights block). Phase 63 keeps the FE inline-constants in place; the consistency parsing test from D-02 deletes itself once consumers switch.
- **`lookback_behavior` / `lookback_role` schema field** — SEED-001's deferred parts. Not exposed to the LLM in v1.11 per SEED-003. Headline gating in v1.11 is implicit via `is_headline_eligible` (D-13).
- **Per-game / per-position insights** — engine-analysis territory, separate milestone (PROJECT.md Out of Scope).
- **Cache-hit logging policy** — SEED-003 Open Questions item; decision belongs in Phase 65 (LLM endpoint), not Phase 63.
- **Info-popover text → Python module** — SEED-003 Open Questions item (option (a) extract to `app/services/insights_prompts/popovers.py`). Decision belongs in Phase 65 prompt-assembly.

</deferred>

---

*Phase: 63-findings-pipeline-zone-wiring*
*Context gathered: 2026-04-20*
