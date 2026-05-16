---
phase: 87.4-drop-endgame-skill-conversion-elo-timeline
plan: 01
subsystem: backend
tags: [endgame, conversion-elo, refactor, schema-rename]
requires:
  - .planning/milestones/v1.17-phases/87.4-drop-endgame-skill-conversion-elo-timeline/01-PLAN.md
  - .planning/milestones/v1.17-phases/87.4-drop-endgame-skill-conversion-elo-timeline/87.4-CONTEXT.md
  - .planning/milestones/v1.17-phases/87.4-drop-endgame-skill-conversion-elo-timeline/87.4-RESEARCH.md
  - .planning/notes/endgame-skill-dropped-conversion-elo.md
provides:
  - PIVOT, ALPHA, CALIBRATION_VERSION module constants on app/services/endgame_service.py
  - _affine_recenter_conv_delta(conv_delta_es) -> s helper
  - _conversion_elo_from_skill (renamed from _endgame_elo_from_skill)
  - _windowed_conv_delta_es bucket-row aggregator (replaces _endgame_skill_from_bucket_rows)
  - EndgameEloTimelinePoint.conversion_elo Pydantic field
  - EndgameOverviewResponse.conversion_elo_timeline Pydantic field
  - MetricId Literal "conversion_elo_gap"; SubsectionId Literal "conversion_elo_timeline"
affects:
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - app/schemas/endgames.py
  - app/repositories/endgame_repository.py
  - scripts/gen_endgame_zones_ts.py
  - frontend/src/generated/endgameZones.ts
tech-stack:
  added: []
  patterns:
    - module-level frozen constants with CALIBRATION_VERSION stamp
    - affine recenter helper sitting between a calibrated metric and the Phase 57 ELO formula
    - per-row Conv ΔES proxy (game_result_score − ES_entry via Lichess sigmoid) where span-level ΔES is unavailable to the timeline query
key-files:
  created:
    - tests/services/test_conversion_elo_recenter.py
    - tests/schemas/test_endgames_schema.py
  modified:
    - app/services/endgame_service.py
    - app/services/endgame_zones.py
    - app/services/insights_service.py
    - app/services/insights_llm.py
    - app/schemas/endgames.py
    - app/repositories/endgame_repository.py
    - scripts/gen_endgame_zones_ts.py
    - frontend/src/generated/endgameZones.ts
    - tests/services/test_endgame_zones.py
    - tests/test_endgame_service.py
    - tests/services/test_insights_service.py
    - tests/services/test_insights_service_series.py
    - tests/services/test_insights_llm.py
    - tests/test_endgames_router.py
    - tests/test_integration_routers.py
decisions:
  - "ALPHA = 2.025 chosen by the pin-upper rule (pin s(+0.002) = 0.60 at benchmark p75); the asymmetric typical band [-0.108, +0.002] then maps to s ∈ [0.378, 0.600] — slightly tighter than nominal 0.40 on the lower end, comfortably inside the Phase 57 clamp [0.05, 0.95]."
  - "CALIBRATION_VERSION = \"conv_delta_v1_260516\" stamped on the helper so future benchmark refreshes are explicit code commits, not silent drift."
  - "Per-game Conv ΔES proxy: terminal-only (game_result_score − Lichess-sigmoid(eval_cp, user_color)) over conversion-bucket rows. Rationale: query_endgame_elo_timeline_rows does not carry next-span eval, so the full _compute_span_gap can't run; per-game proxy is the option (b) approach RESEARCH.md §Open Q #1 endorsed. Parity / recovery rows are excluded so the input matches the Section 2 ``section2_score_gap_conv`` bullet user-facingly."
  - "_compute_skill_score_gap deleted alongside the field deletion (no surviving caller). _endgame_skill_from_material_rows similarly deleted (sole caller — the aggregate endgame_skill finding emitter — was removed in the same change)."
  - "insights_llm.py string literals were renamed (endgame_elo_gap, endgame_elo_timeline) to keep ty clean against the renamed Literal types. User-facing prompt prose ([summary endgame_elo …]) was left intact; Plan 03 owns prompt rewrites + _PROMPT_VERSION bump."
  - "Existing parity-bucket timeline test fixtures were rewritten to conversion-bucket wins (eval_cp=+200, result='1-0'). Under _windowed_conv_delta_es, parity rows no longer contribute, so the old parity-only fixtures would have emitted zero points and broken every downstream assertion. The Phase 57 median-coincide invariant moved to TestConversionEloInvariant in tests/services/test_conversion_elo_recenter.py."
metrics:
  duration_minutes: 75
  tasks_completed: 3
  tasks_total: 3
  commits:
    - 422784ba test(87.4-01): add Wave 0 RED tests for affine recenter + schema rename
    - f0596c5f refactor(87.4-01): zone registry — delete Skill + rename endgame_elo → conversion_elo
    - 4d0f4fab refactor(87.4-01): schema rename + Conversion ELO rewire + Skill retirement
  completed_date: 2026-05-16
---

# Phase 87.4 Plan 01: Conversion ELO Backend Rewire Summary

Hard-deleted the Endgame Skill concept from the backend, introduced the frozen
affine recenter helper that wires Conv ΔES Score Gap into the unchanged Phase 57
`s → ELO` formula, and renamed `endgame_elo` → `conversion_elo` end-to-end on the
backend wire (Pydantic field, Literal Subsection / Metric IDs, dict key in the
weekly-series loop, derived findings).

The recenter math: `s = clamp(0.5 + ALPHA · (conv_ΔES − PIVOT), 0.05, 0.95)`,
with `PIVOT = -0.0474` (benchmark p50 from `reports/benchmarks-latest.md §3.2.2`)
and `ALPHA = 2.025` (pin-upper calibration; `s(+0.002) = 0.60`). At
`conv_ΔES = PIVOT`, `s = 0.5` and the Phase 57 formula returns
`actual_elo_at_date` unchanged — the median-coincide invariant survives the
input swap by construction.

## Tasks

### Task 1 — Wave 0 RED tests
Two new test files holding the invariant + schema contract:
- `tests/services/test_conversion_elo_recenter.py` — `_affine_recenter_conv_delta(PIVOT) == 0.5`,
  `ALPHA ∈ [1.65, 2.05]`, `CALIBRATION_VERSION` exposed, calibrated-band-maps-inside-spec,
  clamp behavior at extreme inputs, full pipeline preserving `actual_elo`.
- `tests/schemas/test_endgames_schema.py` — `EndgameEloTimelinePoint` accepts
  `conversion_elo`, rejects legacy `endgame_elo`; `ScoreGapMaterialResponse`
  drops all 6 Skill fields; `EndgameOverviewResponse.conversion_elo_timeline`
  present and `endgame_elo_timeline` absent.

Initially RED (helpers / constants / renames not yet implemented) — turned
GREEN by Tasks 2 + 3.

### Task 2 — Zone registry + Literal renames + codegen
- `app/services/endgame_zones.py`: deleted `"section2_score_gap_skill"` and
  `"endgame_skill"` from MetricId Literal + ZONE_REGISTRY entries; renamed
  `"endgame_elo_gap"` → `"conversion_elo_gap"`; renamed `"endgame_elo_timeline"`
  → `"conversion_elo_timeline"` in SubsectionId Literal + SAMPLE_QUALITY_BANDS;
  renamed `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` →
  `NOTABLE_CONVERSION_ELO_DIVERGENCE_THRESHOLD`.
- `scripts/gen_endgame_zones_ts.py`: dropped `ENDGAME_SKILL_ZONES` emission and
  `SECTION2_SCORE_GAP_SKILL_NEUTRAL_*` exports (Rule 3 — `ZONE_REGISTRY[
  "endgame_skill"]` lookup would have raised after Task 2's delete).
- `frontend/src/generated/endgameZones.ts`: regenerated from the updated script.
- `tests/services/test_endgame_zones.py`: `assign_zone("endgame_skill", …)`
  cases repointed to `"win_rate"` (same `[0.45, 0.55]` band shape — preserves
  boundary-semantics coverage). Registry-keys assertion set updated.

### Task 3 — Schema rename + service rewire
Single atomic edit pass spanning schema, service, repository, and tests to
avoid a ty partial-deletion state.

**Backend service** (`app/services/endgame_service.py`):
- New constants block: `PIVOT`, `ALPHA`, `CALIBRATION_VERSION` with inline
  pin-upper rationale and citations.
- New `_affine_recenter_conv_delta(conv_delta_es) -> float` helper.
- `_endgame_elo_from_skill` → `_conversion_elo_from_skill` (formula unchanged).
- `_endgame_skill_from_bucket_rows` replaced with `_windowed_conv_delta_es`
  (conv-bucket rows only; per-game proxy via Lichess sigmoid; mean over the
  trailing window).
- `_compute_skill_score_gap` deleted (no surviving caller).
- Weekly-series loop wired through the new helpers; dict key renamed
  `"endgame_elo"` → `"conversion_elo"`.
- `EndgameOverviewResponse(...)` kwarg renamed
  `endgame_elo_timeline=` → `conversion_elo_timeline=`.
- Skill kwargs + the `endgame_skill_rate_mean` block deleted from the
  `ScoreGapMaterialResponse(...)` return.
- Unused `CI_Z_95` import dropped.

**Schema** (`app/schemas/endgames.py`):
- `EndgameEloTimelinePoint.endgame_elo: int` → `conversion_elo: int`
  (docstring updated to describe the affine recenter pipeline).
- `EndgameOverviewResponse.endgame_elo_timeline` → `conversion_elo_timeline`.
- Deleted `section2_score_gap_skill_{mean,n,p_value,ci_low,ci_high}` (5 fields)
  and `endgame_skill_rate_mean` (1 field).
- Pydantic class names `EndgameEloTimelinePoint` / `EndgameEloTimelineCombo` /
  `EndgameEloTimelineResponse` preserved (per D-06 trade-off — frontend
  consumes via Plan 02 rename).

**Insights layer** (`app/services/insights_service.py`):
- Aggregate `endgame_skill` finding emitter removed.
- `_endgame_skill_from_material_rows` deleted.
- `_SECTION2_BUCKETS`: dropped the `("skill", "section2_score_gap_skill")`
  tuple.
- `_findings_endgame_elo_timeline` → `_findings_conversion_elo_timeline`.
- Subsection / metric Literal renames throughout (`endgame_elo_timeline` /
  `endgame_elo_gap` → `conversion_elo_*`).
- `p.endgame_elo` / `last.endgame_elo` → `.conversion_elo`.
- Header docstring updated.

**LLM payload string-literal renames** (`app/services/insights_llm.py`):
String literals typed against the renamed `MetricId` / `SubsectionId` Literals
were renamed in lockstep so ty stays clean. Includes `_NON_FRACTIONAL_METRICS`,
`_TIMELINE_SUBSECTION_IDS`, `_SECTION_LAYOUT`, plus three `metric_id == "…"`
comparison sites. **Prompt prose** (the `[summary endgame_elo | …]` literal,
`### Subsection: …` headers, glossary entries, `_PROMPT_VERSION` bump) was
deliberately **left intact** — Plan 03 (Wave 2 LLM/prompt) owns those edits.

**Repository** (`app/repositories/endgame_repository.py`):
Docstring touch-ups; function name `query_endgame_elo_timeline_rows` preserved
(internal — no semantic load, no FE consumer).

**Tests**: rewrote timeline-test fixtures from parity-bucket draws (no longer
contribute under `_windowed_conv_delta_es`) to conversion-bucket wins; deleted
`TestEndgameSkillFromBucketRows` + `TestEndgameSkillRateMean` classes and the
four ΔES Skill test methods on `TestPhase872PerBucketDeltaES`; updated
3-bucket iteration counts (4→3) on insights tests; renamed `endgame_elo*`
string literals across `tests/services/test_insights_*.py` and
`tests/test_integration_routers.py`.

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ALPHA = 2.025 (pin-upper) | Asymmetric band [-0.108, +0.002]; pinning the upper end keeps the typical-strong boundary at the calibrated +0.002 mark. Lower end lands at s≈0.378 — well inside the Phase 57 [0.05, 0.95] clamp. | ✓ Inside SC#4 spec; documented in helper module docstring. |
| Per-game Conv ΔES proxy (terminal-only) | `query_endgame_elo_timeline_rows` does not carry next-span eval; full `_compute_span_gap` cannot run. RESEARCH.md §Open Q #1 option (b). | ✓ Approximation is consistent with the Section 2 bullet (same conv-bucket population, same Lichess sigmoid baseline). |
| Delete `_compute_skill_score_gap` proactively | Sole caller removed in the same change. Leaving dead code would have invited future drift. | ✓ Out-of-scope-creep-free deletion. |
| Rename string literals in `insights_llm.py` | Required to keep ty clean against the renamed `MetricId` / `SubsectionId` Literals. Plan 01 leaves the file in a compilable state for Plan 03 to land prose changes on top. | ✓ ty clean; prose changes deferred to Plan 03. |
| Rewrite parity-bucket timeline test fixtures | The new helper restricts input to the conversion bucket. Parity-bucket fixtures would have emitted zero points and broken every downstream assertion. | ✓ All 14 timeline tests pass on the new helper. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocker] Codegen script `KeyError("endgame_skill")`**
- **Found during:** Task 2 (after deleting the zone entries).
- **Issue:** `scripts/gen_endgame_zones_ts.py` line 114 reads
  `ZONE_REGISTRY["endgame_skill"]` and line 65 reads
  `ZONE_REGISTRY["section2_score_gap_skill"]`. After Task 2's delete the
  next `uv run python scripts/gen_endgame_zones_ts.py` would have raised.
- **Fix:** Dropped both `ZONE_REGISTRY[...]` lookups and the corresponding
  emission blocks (`ENDGAME_SKILL_ZONES`,
  `SECTION2_SCORE_GAP_SKILL_NEUTRAL_*`).
- **Files modified:** `scripts/gen_endgame_zones_ts.py`.
- **Commit:** `f0596c5f` (Task 2).

**2. [Rule 3 — Blocker] `insights_llm.py` Literal string drift**
- **Found during:** Task 3 (ty run after the zone Literal rename in Task 2).
- **Issue:** Plan Task 3 instructed only `insights_service.py` rename. But
  several `insights_llm.py` sites compare against the renamed Literal IDs
  (`metric_id == "endgame_elo_gap"`, `_NON_FRACTIONAL_METRICS` set entry,
  `_TIMELINE_SUBSECTION_IDS`, `_SECTION_LAYOUT` tuple, sparse-history
  `block_id == "endgame_elo_timeline"`). Behaviour would have silently
  broken (non-fractional scaling, near-edge proximity, sentinel rendering)
  while ty stayed green — string compares are loose.
- **Fix:** Renamed all `endgame_elo_gap` / `endgame_elo_timeline` string
  literals to `conversion_elo_*` in `insights_llm.py`. Left user-facing
  prompt prose (`[summary endgame_elo | …]`, `### Subsection: …` headers,
  glossary terms) intact for Plan 03.
- **Files modified:** `app/services/insights_llm.py`.
- **Commit:** `4d0f4fab` (Task 3).

**3. [Rule 3 — Blocker] Many test files reference renamed/deleted symbols**
- **Found during:** Task 3 ty/pytest sweep.
- **Issue:** Plan Task 3 acceptance criteria require `uv run pytest
  tests/test_endgame_service.py -x` to pass and `uv run ty check app/
  tests/` to be clean. The renames touched 6 additional test files beyond
  the planned scope (`tests/services/test_insights_service.py`,
  `test_insights_service_series.py`, `test_insights_llm.py`,
  `tests/test_endgames_router.py`,
  `tests/test_integration_routers.py`).
- **Fix:** Bulk-renamed Literal strings + attribute accesses; updated
  Skill-counted assertions (4→3 ΔES findings; aggregate `endgame_skill`
  finding must be absent); rewrote parity-bucket timeline fixtures.
- **Files modified:** five additional test files (above).
- **Commit:** `4d0f4fab` (Task 3).

### Rewritten Timeline Test Fixtures (Scope-Adjacent)

The plan's per-task instructions cover the rename of test classes
(`TestEndgameElo → TestConversionElo`, `TestEndgameEloTimeline →
TestConversionEloTimeline`) and the deletion of
`TestEndgameSkillFromBucketRows` / Skill kwargs. **What the plan did NOT
spell out** is that fourteen timeline test methods fed parity-bucket
fixtures (`eval_cp = 0`, `result = "1/2-1/2"`) which under the new
`_windowed_conv_delta_es` no longer contribute — so the timeline would
emit zero points and break every downstream assertion. I rewrote those
fixtures to conversion-bucket wins (`eval_cp = +200`, `result = "1-0"`)
and softened the "neutral skill ⇒ `conversion_elo == actual_elo`"
assertion (the exact invariant moved to
`TestConversionEloInvariant.test_pivot_pipeline_invariant_actual_elo_preserved`
in the Wave 0 unit-test file). This is faithful to the plan's intent
("Update any test fixture that references … kwargs in
`ScoreGapMaterialResponse(...)` construction") but the scope is broader
than the bullet implied.

## Authentication Gates

None — backend-only refactor; no external services touched.

## Verification

- `uv run ty check app/ tests/` — clean.
- `uv run ruff check .` — clean.
- `uv run python scripts/gen_endgame_zones_ts.py --check` — `OK: …
  endgameZones.ts is up to date`.
- `uv run pytest tests/` — **1527 passed, 6 skipped** in 22.6s. No new
  failures; no regressions on existing test files. (Phase 87.4-out-of-scope
  benchmark / chess.com integration tests that need the dev DB are among
  the 6 skipped, unchanged from baseline.)
- `uv run pytest tests/services/test_conversion_elo_recenter.py
  tests/schemas/test_endgames_schema.py tests/services/test_endgame_zones.py
  tests/test_endgame_service.py tests/services/test_insights_service.py
  tests/services/test_insights_llm.py -x` — all green.

## Regenerated endgameZones.ts diff highlights

The committed regen drops 8 lines and tightens 2 — net diff
`+2 / −8`:

- **Vanished:** `ENDGAME_SKILL_ZONES: GaugeZone[]` (3-band array literal),
  `SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN`,
  `SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX`.
- **Unchanged:** Conv / Parity / Recov bucket bands, all `PER_CLASS_GAUGE_ZONES`,
  `entry_expected_score` helpers, all other per-metric NEUTRAL_* exports.

The Plan 02 frontend rewrite will need to either drop or stub references to
the removed exports (`EndgameSkillCard.tsx` imports them today). Plan 02
explicitly tracks the `EndgameSkillCard.tsx` deletion.

## Known Stubs

None.

## Threat Flags

No new untrusted surfaces introduced. The per-row Conv ΔES proxy runs on the
same rows already iterated by the timeline loop — no new SQL paths, no new
external network calls, no new auth surface. T-87.4-04 (DoS on the new windowed
computation) is `accept` per plan threat model — O(N) on existing input set,
no algorithmic change.

## Self-Check: PASSED

- `app/services/endgame_service.py:_affine_recenter_conv_delta` exists.
- `app/services/endgame_service.py:_conversion_elo_from_skill` exists.
- `app/services/endgame_service.py:_windowed_conv_delta_es` exists.
- `app/services/endgame_service.py:PIVOT = -0.0474` line present.
- `app/services/endgame_service.py:ALPHA = 2.025` line present.
- `app/services/endgame_service.py:CALIBRATION_VERSION = "conv_delta_v1_260516"` present.
- `EndgameEloTimelinePoint.conversion_elo` field present in `app/schemas/endgames.py`.
- `EndgameOverviewResponse.conversion_elo_timeline` field present in `app/schemas/endgames.py`.
- `ZONE_REGISTRY` lacks `endgame_skill` and `section2_score_gap_skill` keys
  (`tests/services/test_endgame_zones.py::TestRegistrySanity` asserts the
  full key set).
- `frontend/src/generated/endgameZones.ts` is byte-stable against
  `gen_endgame_zones_ts.py --check`.
- Commits exist: 422784ba, f0596c5f, 4d0f4fab.
