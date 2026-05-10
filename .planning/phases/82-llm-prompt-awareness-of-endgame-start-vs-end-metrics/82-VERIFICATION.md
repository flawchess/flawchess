---
phase: 82-llm-prompt-awareness-of-endgame-start-vs-end-metrics
verified: 2026-05-10T21:35:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Navigate to /endgames on dev DB with a user having 50+ endgame games, generate insights, and confirm the LLM narration mentions both entry_eval_pawns and endgame_score in the Endgame Overall Performance section using the setup→execution framing"
    expected: "LLM narration references 'where you start'/'entry eval' AND 'what you do with it'/'endgame score' as a pair; no tile-vs-LLM color mismatch (green tile = narrated strength, neutral tile = silent or near-edge only)"
    why_human: "LLM output is non-deterministic and cannot be asserted programmatically; UAT scenario A from Plan 04 confirms this ran and passed post-fix, but a human reviewer should confirm the wiring on the current codebase state"
---

# Phase 82: LLM Prompt Awareness of Endgame Start vs End Metrics — Verification Report

**Phase Goal:** Wire the two Phase 81 metrics (`entry_eval_mean_pawns` + `endgame_score_p_value` against 50%) through the Endgame Insights LLM pipeline so the narrated Endgame Insights section can mention them alongside Conversion / Parity / Recovery and the score-gap timeline. Closes the gap where user-visible "Endgame Start vs End" tiles existed in production but `app/services/insights_service.py` emitted no findings for either metric and `app/prompts/endgame_insights.md` had no glossary or subsection for them.
**Verified:** 2026-05-10T21:35:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | MetricId Literal carries `entry_eval_pawns`, `endgame_score`, `endgame_score_timeline`, `non_endgame_score_timeline` (old bare `endgame_score` / `non_endgame_score` gone) | VERIFIED | `app/services/endgame_zones.py` lines 32–44: all four present; old bare `endgame_score` slot is repurposed (D-03), old `non_endgame_score` is gone (D-02) |
| 2 | SubsectionId Literal carries `endgame_start_vs_end` | VERIFIED | `app/services/endgame_zones.py` line 57: `"endgame_start_vs_end"` inserted between `"overall"` and `"score_timeline"` |
| 3 | `ZONE_REGISTRY["entry_eval_pawns"] = ZoneSpec(typical_lower=-0.50, typical_upper=0.50, direction="higher_is_better")` | VERIFIED | `app/services/endgame_zones.py` lines 141–149: exact band confirmed |
| 4 | `ZONE_REGISTRY["endgame_score"] = ZoneSpec(typical_lower=0.45, typical_upper=0.55, direction="higher_is_better")` | VERIFIED | `app/services/endgame_zones.py` lines 151–158: exact band confirmed |
| 5 | `SAMPLE_QUALITY_BANDS` includes `endgame_start_vs_end -> (10, 50)` | VERIFIED | `app/services/endgame_zones.py` line 275: confirmed |
| 6 | `_findings_endgame_start_vs_end` exists in `insights_service.py` and emits two `SubsectionFinding`s (`entry_eval_pawns` + `endgame_score`) | VERIFIED | Lines 443–501: full implementation; independently gated on `entry_eval_n < 10` (Tile 1) and `endgame_wdl.total < 10` (Tile 2); wired via `findings.extend(_findings_endgame_start_vs_end(response, window))` at line 385 |
| 7 | `_compute_subsection_findings` calls `_findings_endgame_start_vs_end` BETWEEN `_finding_overall` and `_findings_score_timeline` | VERIFIED | Lines 384–386: `_finding_overall` (line 384), `_findings_endgame_start_vs_end` (line 385), `_findings_score_timeline` (line 386) — correct ordering |
| 8 | `_PROMPT_VERSION == "endgame_v23"` in `app/services/insights_llm.py` | VERIFIED | Line 66: `_PROMPT_VERSION = "endgame_v23"` with cumulative D-25 changelog text |
| 9 | `endgame_insights.md` contains `### Subsection: endgame_start_vs_end` with "setup → execution" framing, 5 example narration patterns, Time Pressure cross-link ([low-time-gap]), and single-tile case guidance | VERIFIED | Lines 250–278: all required content present |
| 10 | `endgame_start_vs_end` subsection listed in `_SECTION_LAYOUT` under section_id `overall`, between `overall` and `score_timeline` | VERIFIED | `app/services/insights_llm.py` lines 1322–1324: `("subsection", "overall")`, `("subsection", "endgame_start_vs_end")`, `("subsection", "score_timeline")` — UAT regression that was caught and fixed during Plan 04 |
| 11 | `entry_eval_pawns` renders in PAWNS (decimal, e.g. `+0.46`) not centipawns — `_NON_FRACTIONAL_METRICS` includes `entry_eval_pawns` and `_VALUE_PRECISION["entry_eval_pawns"] = 2` | VERIFIED | `app/services/insights_llm.py` lines 100–119: `entry_eval_pawns` in `_NON_FRACTIONAL_METRICS`; `_VALUE_PRECISION = {"entry_eval_pawns": 2}`; test `test_endgame_start_vs_end_findings_render_in_prompt` asserts `mean=+0.46` and `(typical -0.50 to +0.50)` NOT `mean=+46` or `(typical -50 to +50)` |
| 12 | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS == ±0.5` in frontend and tile color rule implements D-12 (`zone AND p < 0.05`) | VERIFIED | `frontend/src/lib/endgameEntryEvalZones.ts` lines 23/27: `-0.5` and `0.5`; `EndgameStartVsEndSection.test.tsx` confirms 0.46+p<0.001 is neutral (D-14) and 0.5+p<0.001 is ZONE_SUCCESS (D-12 boundary) |

**Score:** 12/12 truths verified

### Deferred Items

No deferred items — all D-06 (verdict field rejected, honored by absence), D-07 (sig-test not propagated, honored by absence), and D-11 (per-ELO `ENDGAME_SCORE_ZONES` deferred) items are explicitly honored-by-absence decisions documented in CONTEXT.md.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/endgame_zones.py` | Updated MetricId/SubsectionId Literals + ZoneSpec entries + SAMPLE_QUALITY_BANDS | VERIFIED | All Literal updates, ZONE_REGISTRY entries at exact D-08/D-10 bands, `endgame_start_vs_end: (10, 50)` in SAMPLE_QUALITY_BANDS |
| `app/services/insights_service.py` | `_findings_endgame_start_vs_end` emitter + renamed score_timeline usages | VERIFIED | Function at lines 443–501; 6 atomic renames in `_findings_score_timeline`; wired at line 385 |
| `app/services/insights_llm.py` | `_PROMPT_VERSION = "endgame_v23"`, `entry_eval_pawns` in `_NON_FRACTIONAL_METRICS`, `_VALUE_PRECISION`, `_SECTION_LAYOUT` update | VERIFIED | All four updates confirmed; CR-01 fix (pawn unit) included; `_NO_BAND_METRICS` uses renamed timeline identifiers |
| `app/prompts/endgame_insights.md` | New subsection block + glossary entries + mapping table row + line-125 rename | VERIFIED | `### Subsection: endgame_start_vs_end` at line 250; `**entry_eval_pawns**` and `**endgame_score**` (repurposed) glossary entries; renamed `**endgame_score_timeline**` / `**non_endgame_score_timeline**`; mapping row at line 378 in correct position (between `overall` and `score_timeline`) |
| `frontend/src/lib/endgameEntryEvalZones.ts` | Constants tightened to ±0.5 | VERIFIED | Lines 23/27: exact literals `-0.5` and `0.5`; no stale ±0.75 references |
| `tests/services/test_endgame_zones.py` | `TestNewMetricZones` class + updated `TestRegistrySanity` | VERIFIED | `TestNewMetricZones` at line 105 |
| `tests/services/test_insights_service.py` | `TestFindingsEndgameStartVsEnd` class | VERIFIED | Class at line 714 |
| `tests/services/test_insights_llm.py` | Updated version assertion + new content tests + CR-01 regression test | VERIFIED | `test_prompt_version_is_v23`, 4 new content tests, `test_endgame_start_vs_end_findings_render_in_prompt` (pawn unit regression test) |
| `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` | Boundary assertions at ±0.5 | VERIFIED | 3 test cases: neutral inside band, SUCCESS at/above +0.5, DANGER at/below -0.5 |
| `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | D-12/D-14 test cases | VERIFIED | D-14 case (0.46 + p<0.001 neutral), D-12 boundary (0.5 + p<0.001 SUCCESS), D-12 negative (-0.6 + p<0.05 DANGER); prop-forwarding at ±0.5 |
| `CHANGELOG.md` | Phase 82 entries under `## [Unreleased]` | VERIFIED | 3 bullets present under `### Added` and `### Changed` referencing Phase 82, `endgame_start_vs_end`, `endgame_v23`, ±0.5 band |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `insights_service.py::_compute_subsection_findings` | `_findings_endgame_start_vs_end` | `findings.extend(...)` at line 385 | VERIFIED | Call site confirmed between `_finding_overall` (line 384) and `_findings_score_timeline` (line 386) |
| `_findings_endgame_start_vs_end` | `endgame_zones.py::assign_zone` | `assign_zone("entry_eval_pawns", ...)` and `assign_zone("endgame_score", ...)` | VERIFIED | Lines 471 and 493 |
| `insights_llm.py::_SECTION_LAYOUT` | `endgame_start_vs_end` subsection findings | `("subsection", "endgame_start_vs_end")` at line 1323 | VERIFIED | Fixed during Plan 04 UAT; regression test `test_endgame_start_vs_end_findings_render_in_prompt` guards it |
| `_format_zone_bounds` | `_NO_BAND_METRICS` skip list | `if metric_id in _NO_BAND_METRICS: return ""` at line 373 | VERIFIED | Skip list uses renamed `endgame_score_timeline` / `non_endgame_score_timeline` — the new bare `endgame_score` (with real band) correctly absent |
| `endgameEntryEvalZones.ts` | `EndgameStartVsEndSection.tsx` | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` + `endgameEntryEvalZoneColor` imports | VERIFIED | Component logic `isConfident(evalLevel) && evalIsInColoredZone` naturally implements D-12 once constants tighten to ±0.5 |
| Score_timeline metric assertions | `test_insights_service_series.py` | `metric == "endgame_score_timeline"` / `"non_endgame_score_timeline"` | VERIFIED | Lines 499, 500, 545, 546, 634, 635 all use `_timeline` variants |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `_findings_endgame_start_vs_end` | `perf.entry_eval_mean_pawns`, `perf.endgame_wdl` | `EndgamePerformanceResponse` — populated by Phase 81 backend from DB queries on `game_positions` | Yes — Phase 81 already populates these four fields from live DB aggregation | FLOWING |
| `endgame_insights.md` (prompt) | All `[summary entry_eval_pawns]` / `[summary endgame_score]` blocks | `_assemble_user_prompt` in `insights_llm.py` traverses `_SECTION_LAYOUT` including `endgame_start_vs_end` | Yes — UAT confirmed both `[summary]` blocks appear in the prompt; `test_endgame_start_vs_end_findings_render_in_prompt` asserts this programmatically | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `entry_eval_pawns` renders in pawns (not centipawns) | `uv run pytest tests/services/test_insights_llm.py::TestPromptAssembly::test_endgame_start_vs_end_findings_render_in_prompt -v` | 1 passed | PASS |
| `_PROMPT_VERSION == "endgame_v23"` | `uv run pytest tests/services/test_insights_llm.py::TestPromptVersionAndBody::test_prompt_version_is_v23 -v` | 1 passed | PASS |
| Prompt contains `### Subsection: endgame_start_vs_end` | `uv run pytest tests/services/test_insights_llm.py::TestPromptVersionAndBody::test_prompt_contains_endgame_start_vs_end_subsection -v` | 1 passed | PASS |
| Mapping table row in correct position | `uv run pytest tests/services/test_insights_llm.py::TestPromptVersionAndBody::test_prompt_mapping_table_includes_endgame_start_vs_end_row -v` | 1 passed | PASS |
| Full backend suite | `uv run pytest -x -q` | 1322 passed, 6 skipped | PASS |
| ty type check | `uv run ty check app/ tests/` | All checks passed | PASS |
| ruff linter | `uv run ruff check app/ tests/` | All checks passed | PASS |
| Frontend test suite | `npm test -- --run` (in `frontend/`) | 340 passed (29 test files) | PASS |
| D-14 keystone: 0.46 + p<0.001 renders neutral | Frontend test: "Tile 1 value text is unstyled for value 0.46 + p<0.001" | PASS (confirmed in verbose test output) | PASS |
| D-12 boundary: 0.5 + p<0.001 renders ZONE_SUCCESS | Frontend test: "Tile 1 value text is ZONE_SUCCESS at the ±0.5 boundary" | PASS | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| D-01 | 82-01 | `endgame_score` → `endgame_score_timeline` rename | SATISFIED | `endgame_zones.py` + `insights_service.py` + all tests |
| D-02 | 82-01 | `non_endgame_score` → `non_endgame_score_timeline` rename | SATISFIED | Same files |
| D-03 | 82-01 | Repurposed `endgame_score` MetricId for new subsection | SATISFIED | `endgame_zones.py` line 33 |
| D-04 | 82-01 | New `entry_eval_pawns` MetricId | SATISFIED | `endgame_zones.py` line 32 |
| D-05 | 82-01 | New `endgame_start_vs_end` SubsectionId | SATISFIED | `endgame_zones.py` line 57 |
| D-06 | 82-01 | REJECTED: no `verdict` field on SubsectionFinding (honored by absence) | SATISFIED | No `verdict` field present in `SubsectionFinding` or any emitter |
| D-07 | 82-01 | Sig-test outcome NOT propagated to LLM (honored by absence) | SATISFIED | No `entry_eval_p_value` or `endgame_score_p_value` in `SubsectionFinding` |
| D-08 | 82-01 | `ZONE_REGISTRY["entry_eval_pawns"]` at ±0.50 | SATISFIED | `endgame_zones.py` lines 141–149 |
| D-09 | 82-03 | Frontend `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` tightened to ±0.5 | SATISFIED | `endgameEntryEvalZones.ts` lines 23/27 |
| D-10 | 82-01 | `ZONE_REGISTRY["endgame_score"]` at [0.45, 0.55] | SATISFIED | `endgame_zones.py` lines 151–158 |
| D-11 | 82-01 | DEFERRED: per-ELO `ENDGAME_SCORE_ZONES` (honored by absence) | SATISFIED | No per-ELO registry added |
| D-12 | 82-03 | Tile color: `(value in zone) AND p < 0.05` | SATISFIED | Existing `isConfident && evalIsInColoredZone` gate + tightened ±0.5 constants; 3 new frontend tests |
| D-13 | 82-03 | Tile color amendment ships in-phase (not a separate task) | SATISFIED | Plan 03 executed in Wave 2 |
| D-14 | 82-03 | Borderline 0.46 + p<0.001 reads neutral on tile AND not narrated | SATISFIED | Frontend test + prompt guidance for within-noise / [near edge] |
| D-15 | 82-03 | Theme constants from `theme.ts` (ZONE_SUCCESS/DANGER/NEUTRAL) | SATISFIED | `EndgameStartVsEndSection.tsx` untouched; existing constants used |
| D-16 | 82-01 | `_findings_endgame_start_vs_end` wired in `_compute_subsection_findings` | SATISFIED | Lines 384–386 of `insights_service.py` |
| D-17 | 82-01 | Sample size gate: `entry_eval_n >= 10` / `total >= 10` | SATISFIED | Lines 461 and 482 of `insights_service.py` |
| D-18 | 82-01 | `is_headline_eligible = sample_quality != "thin"` | SATISFIED | Lines 476 and 498 |
| D-19 | 82-01 | `dimension=None` for both findings | SATISFIED | Lines 477 and 499 |
| D-20 | 82-01 | `series=None` (not timeline metrics) | SATISFIED | No `series` field set; defaults to None per schema |
| D-21 | 82-01 | `findings_hash` recompute safe; cache invalidation via `_PROMPT_VERSION` bump | SATISFIED | Append-only-safe field ordering; `endgame_v23` bump auto-invalidates |
| D-22 | 82-02 | Two new glossary entries + renamed timeline entries | SATISFIED | `endgame_insights.md` lines 305–324 |
| D-23 | 82-02 | `### Subsection: endgame_start_vs_end` block with setup→execution + Time Pressure cross-link | SATISFIED | Lines 250–278 of `endgame_insights.md` |
| D-24 | 82-02 | Mapping table row `endgame_start_vs_end | overall` between `overall` and `score_timeline` | SATISFIED | Line 378; position verified programmatically |
| D-25 | 82-02 | `_PROMPT_VERSION` bumped to `endgame_v23` with D-25 changelog text | SATISFIED | `insights_llm.py` line 66 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/prompts/endgame_insights.md` | 14 | "placeholder" in comment | Info | Intentional LLM instruction telling the model to use placeholder strings that the server overwrites; not a code stub |
| `app/services/insights_llm.py` | 104 | "placeholder" in comment | Info | Describes the no-op `[0, 1]` band design intentionally; not a code stub |
| `app/services/insights_service.py` | 202 | `findings_hash=""` placeholder | Info | Standard pattern — hash is computed and replaced immediately after construction; not a stub |

No blockers found. All "placeholder" occurrences are in comments describing intentional design patterns, not empty implementations for Phase 82's deliverables.

### Human Verification Required

#### 1. End-to-end LLM narration of both `endgame_start_vs_end` tiles

**Test:** Start the dev server (`bin/run_local.sh`), log in as a user with 50+ endgame games, navigate to `/endgames`, generate insights, and read the "Endgame Overall Performance" section of the narrated report.

**Expected:**
- LLM narration mentions BOTH `entry_eval_pawns` ("where you start" / "Stockfish eval at endgame entry") AND `endgame_score` ("what you do with it" / overall score in endgame games) in the same paragraph, framed as setup → execution.
- If the user's entry-eval tile is neutral (gray) and endgame-score is also neutral: LLM is silent on this subsection or uses [near edge] framing only — does NOT assert a pattern.
- If the user's entry-eval is green (strong) but endgame-score is gray (neutral, e.g. borderline +0.46 with high sig): tile reads neutral AND LLM does NOT narrate it as "significantly better than zero" or "above null". This is the D-14 keystone behavior.
- Conv/Parity/Recovery section still narrates correctly (no regression).
- Score-gap timeline still narrates under the renamed `endgame_score_timeline` / `non_endgame_score_timeline` MetricIds (user-facing phrasing is unchanged; internal names are transparent).

**Why human:** LLM output is non-deterministic and depends on real user data. The Plan 04 UAT confirmed this passed after the `_SECTION_LAYOUT` bug was fixed (commit `cdb36ac2` / `fe9b9430` from REVIEW.md resolution), but a final human confirmation on the current codebase state is needed because the prompt assembler path (finding → `_SECTION_LAYOUT` → rendered prompt → LLM response) cannot be fully exercised by unit tests alone.

### Gaps Summary

No gaps found. All 12 must-have truths are VERIFIED by code inspection and passing test suites. The single item requiring human verification is the end-to-end LLM narration quality check — automated tests confirm both metrics reach the prompt in the correct format (`mean=+0.46` not `mean=+46`; zone band `-0.50 to +0.50` not `-50 to +50`) and the `_SECTION_LAYOUT` wiring is tested by a regression test. The human check covers the non-deterministic LLM output layer only.

Note on code review findings: The REVIEW.md documents that CR-01 (unit mismatch: `entry_eval_pawns` rendering in centipawns) and all warnings (WR-01 through WR-03, IN-01 through IN-03) were resolved before phase completion (commits `cdb36ac2` and `fe9b9430`). This verification confirms those fixes are present in the current codebase.

---

_Verified: 2026-05-10T21:35:00Z_
_Verifier: Claude (gsd-verifier)_
