---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
verified: 2026-04-24T15:48:40Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 68: Endgame Score Timeline Dual-Line Shaded Gap — Verification Report

**Phase Goal:** Replace the single-line "Endgame vs Non-Endgame Score Gap over Time" chart on the Endgame tab with a two-line "Endgame vs Non-Endgame Score over Time" chart (both absolute Score series, shaded area between them showing the gap). Rename the backend `score_gap_timeline` subsection to `score_timeline`, simplify the LLM prompt, and drop the "Score Gap is a comparison, not an absolute measure" caveat.

**Verified:** 2026-04-24T15:48:40Z
**Status:** human_needed (automated verification passed; mobile + rendered-chart visual spot-check needed)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Endgame Overall Performance section renders one chart titled "Endgame vs Non-Endgame Score over Time" with two lines (endgame, non-endgame, 0-100%) and green/red shaded area between them. Old single-line chart removed. | VERIFIED | `frontend/src/components/charts/EndgamePerformanceSection.tsx:334` contains `Endgame vs Non-Endgame Score over Time` title. Two `<Line>` elements at lines 457 (endgame) and 466 (non_endgame). Shaded `<g data-testid="score-band-above">` (green) at line 432 and `<g data-testid="score-band-below">` (red) at line 445. Old `ScoreGapTimelineChart` export gone (grep returns 0). `frontend/src/pages/Endgames.tsx:20,379` imports and mounts `EndgameScoreOverTimeChart`. 0-100% Y-axis via `SCORE_TIMELINE_Y_DOMAIN`. |
| 2 | Backend payload emits `score_timeline` subsection (renamed) with two series (`endgame` and `non_endgame`), each with its own `[series]` block. `[summary score_gap]` in `overall` subsection unchanged. | VERIFIED | `app/services/endgame_zones.py:44,210` has `score_timeline` SubsectionId member and SAMPLE_QUALITY_BANDS key. `app/services/insights_service.py:427` defines `_findings_score_timeline` returning TWO findings per window (endgame, non_endgame) with `dimension={"part": ...}`. `app/services/insights_service.py:379` uses `findings.extend(...)`. `suppress_summary` carve-out removed from `insights_llm.py` (grep returns 0). Integration test `tests/services/test_insights_service_series.py:580 test_score_timeline_end_to_end_payload` asserts two `[summary score_timeline]` blocks + two `[series ..., part=endgame|non_endgame]` blocks per window AND `[summary score_gap]` still present in `overall`. |
| 3 | `app/prompts/endgame_insights.md` no longer carries `score_gap` framing rule, `score_gap_timeline` "no [summary]" exception note is removed, all old chart name references updated. | VERIFIED | Grep shows 0 matches for `Framing rule`, `score_gap_timeline`, `one exception to the summary-per-metric`, `Score Gap over Time` in `app/prompts/endgame_insights.md`. Positive matches present: `score_timeline` (lines 137, 139, 354, 369), `part=endgame`, `part=non_endgame`, `weekly` in emitter-shape docs at line 139. Mapping table row at line 354: `score_timeline → overall`. Prose at line 369 updated. `_PROMPT_VERSION = "endgame_v13"` at `app/services/insights_llm.py:60`. |
| 4 | Info popover for the chart no longer contains the "Score Gap is a comparison, not an absolute measure" caveat. | VERIFIED | Grep for `the Score Gap is a comparison`, `absolute measure`, `positive value can mean stronger endgames` in `frontend/src/` returns 0 matches. The new chart's `InfoPopover` at `EndgamePerformanceSection.tsx:335-352` contains a clean 3-paragraph definition with the new shading-explanation sentence at line 345-346 ("The shaded area between the lines is color-coded: green when your endgame Score leads your non-endgame Score, red when it trails") and drops the caveat entirely. |
| 5 | Existing insights snapshot tests pass and endgame page renders correctly on mobile. | PARTIAL — automated PASSED, mobile visual NEEDS HUMAN | Backend tests: `uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py -x` → 68 passed. Frontend tests: `npm test -- --run EndgamePerformanceSection` → 8 passed (includes a `noHorizontalOverflow` smoke test at 375px per Plan 02 Test 8). Phase summary reports 1057 backend + 106 frontend tests pass overall. Mobile visual verification (legend readability, no layout regression, info popover interaction) must be done by a human in-browser. |

**Score:** 5/5 truths verified (1 truth has a visual/mobile sub-check routed to human verification).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/endgame_zones.py` | `SubsectionId` with `score_timeline` member | VERIFIED | Line 44 `"score_timeline"`, line 210 `SAMPLE_QUALITY_BANDS["score_timeline"]: (10, 52)`. No `score_gap_timeline` left in file. |
| `app/services/insights_service.py` | `_findings_score_timeline` returning two findings per window | VERIFIED | Lines 427-526: builder returns list of two `SubsectionFinding` (part=endgame, part=non_endgame), `metric="score_gap"` on both. Call site at line 379 uses `.extend(...)`. |
| `app/services/insights_llm.py` | Payload emitter renders two `[summary score_timeline]` + two `[series ..., part=X]` blocks, no `suppress_summary` | VERIFIED | `_PROMPT_VERSION = "endgame_v13"` at line 60. `suppress_summary` grep returns 0. Integration test confirms the emitted prompt string shape. |
| `frontend/src/types/endgames.ts` | `ScoreGapTimelinePoint` with `endgame_score`, `non_endgame_score` | VERIFIED | Lines 109-131 include both `endgame_score: number` and `non_endgame_score: number` as required fields with sanity comment. |
| `app/schemas/endgames.py` | Pydantic `ScoreGapTimelinePoint` extended with two absolute-score fields | VERIFIED | Lines 207-231: both fields documented and declared as `float`. Identity invariant documented. |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | New `EndgameScoreOverTimeChart` replacing `ScoreGapTimelineChart` | VERIFIED | Lines 257-483 define the new component. Old `ScoreGapTimelineChart` export gone (grep returns 0). Title, two lines, two testid-carrying band groups, tooltip, legend all present. |
| `frontend/src/pages/Endgames.tsx` | Mount site calls `EndgameScoreOverTimeChart` | VERIFIED | Line 20 imports `EndgameScoreOverTimeChart`, line 379 renders it with `timeline` + `window` props. `ScoreGapTimelineChart` import removed. |
| `frontend/src/lib/theme.ts` | Color tokens for score-timeline | VERIFIED | Lines 126-129 define `SCORE_TIMELINE_LINE_ENDGAME`, `SCORE_TIMELINE_LINE_NON_ENDGAME`, `SCORE_TIMELINE_FILL_ABOVE`, `SCORE_TIMELINE_FILL_BELOW`. |
| `app/prompts/endgame_insights.md` | Framing rule + summary-per-metric exception removed; subsection renamed; emitter-shape docs updated | VERIFIED | Negative greps 0; positive greps for `score_timeline`, `part=endgame`, `part=non_endgame`, `weekly` all match in the emitter-shape doc at line 139. |
| `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` | Vitest covering Tests 1-10 from Plan 02 | VERIFIED | File exists, 8 tests pass (title, band testids for mixed/above-only/neutral fixtures, legend labels, tooltip, mobile no-overflow, old-export-gone, mount-site-updated). |
| `tests/services/test_insights_service_series.py` | Integration test `test_score_timeline_end_to_end_payload` | VERIFIED | Class at line 576, test at line 580, asserts `[summary score_timeline]` count == 2/window, two series blocks with correct part tags, no `score_gap_timeline` leak, no `Framing rule` leak. |
| `CHANGELOG.md` | `### Changed` bullet for Phase 68 under `## [Unreleased]` | VERIFIED | Line 28 bullet mentions dual-line chart, `score_gap_timeline → score_timeline` rename, `endgame_v13` prompt bump, and the caveat removal. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `insights_service._findings_score_timeline` | `endgame_zones.SubsectionId` | `subsection_id="score_timeline"` | WIRED | Lines 511 and 526 in `insights_service.py` emit `subsection_id="score_timeline"`. |
| `insights_llm._render_subsection_block` | `compute_findings` output | Per-part dimension grouping | WIRED | Integration test at `test_insights_service_series.py:580` assembles a prompt end-to-end and finds both summary blocks + both series blocks with `part=endgame|non_endgame` tags; endgame emits first. |
| `Endgames.tsx` | `EndgameScoreOverTimeChart` | Named import + prop drilling | WIRED | Import at line 20, mount at line 379 with `timeline={scoreGapData.timeline}` + `window={scoreGapData.timeline_window}`. `scoreGapData` derived from `overviewData?.score_gap_material` at line 253. |
| `EndgameScoreOverTimeChart` | `theme.ts` tokens | ES import | WIRED | Component imports `SCORE_TIMELINE_LINE_ENDGAME`, `SCORE_TIMELINE_LINE_NON_ENDGAME`, `SCORE_TIMELINE_FILL_ABOVE`, `SCORE_TIMELINE_FILL_BELOW` and uses each in the Line/Area elements. |
| `frontend/src/types/endgames.ts::ScoreGapTimelinePoint` | `app/schemas/endgames.py::ScoreGapTimelinePoint` | Hand-maintained mirror | WIRED | Both add `endgame_score: float/number` and `non_endgame_score: float/number` in the same phase, no drift. |
| `_PROMPT_VERSION` | `llm_logs` cache key | `get_latest_log_by_hash(..., _PROMPT_VERSION, ...)` | WIRED | `insights_llm.py:1767` uses `_PROMPT_VERSION`; bump from v12 → v13 naturally invalidates cached reports. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EndgameScoreOverTimeChart` | `timeline: ScoreGapTimelinePoint[]` via `props.timeline` | `Endgames.tsx:377,380` passes `scoreGapData.timeline` from `overviewData?.score_gap_material` fetched via `useEndgameOverview` hook | FLOWING | Data flows from backend `_compute_score_gap_timeline` (weekly rolling window over real user games) → API response → TanStack Query → prop. The two new fields (`endgame_score`, `non_endgame_score`) are populated from `statistics.mean(endgame_window)` / `statistics.mean(non_endgame_window)` locals in `endgame_service.py:_compute_score_gap_timeline`. Identity invariant `score_difference == endgame_score - non_endgame_score` asserted by unit tests. |
| `_findings_score_timeline` series | `[(p.date, p.endgame_score, p.endgame_game_count) for p in timeline]` and mirror for non_endgame | `response.score_gap_material.timeline` (backend builder) | FLOWING | Both findings carry real weekly per-side absolute scores. Zone computed via existing `assign_zone("score_gap", ...)`. Integration test verifies the rendered prompt has non-empty `[series ...]` blocks. |
| Chart shaded band rendering | `band_above`, `band_below` arrays | Derived per-point in `EndgameScoreOverTimeChart` data map | FLOWING | `hasAboveBand`/`hasBelowBand` booleans gate which `<g data-testid=...>` wrapper renders. Epsilon-1% band avoids flicker at the crossover. Tests verify this with mixed-sign, above-only, and neutral fixtures. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend insights test subset (key Phase 68 suites) | `uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py -x` | 68 passed | PASS |
| Frontend chart component tests | `cd frontend && npm test -- --run EndgamePerformanceSection` | 8 passed | PASS |
| No `score_gap_timeline` leak in shipping code | `grep -rn "score_gap_timeline" app/services/ app/schemas/ frontend/src/components/ frontend/src/pages/ frontend/src/types/` | Only references are the internal helper function name `_compute_score_gap_timeline` and two legacy variable names inside test fixture code — not in shipping code identifiers | PASS |
| Prompt version bumped | `grep -n "endgame_v13" app/services/insights_llm.py` | Match at line 60 | PASS |
| Old chart export gone | `grep -rn "ScoreGapTimelineChart" frontend/src/` | 0 matches | PASS |
| Old caveat removed from frontend | `grep -rn "the Score Gap is a comparison\|absolute measure" frontend/src/` | 0 matches | PASS |
| CHANGELOG entry present | `grep -n "Phase 68\|endgame_v13" CHANGELOG.md` | Match at line 28 | PASS |

### Requirements Coverage

Phase 68 declares `requirements: []` in all four plan frontmatters. No REQUIREMENTS.md traceability needed — scope is defined by the ROADMAP Success Criteria (verified as truths above).

### Anti-Patterns Found

Scanned `frontend/src/components/charts/EndgamePerformanceSection.tsx`, `frontend/src/pages/Endgames.tsx`, `frontend/src/lib/theme.ts`, `app/services/insights_service.py`, `app/services/insights_llm.py`, `app/services/endgame_zones.py`, `app/schemas/endgames.py`, `app/prompts/endgame_insights.md`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | No TODO/FIXME/PLACEHOLDER/stub/hardcoded-empty-prop patterns introduced by this phase. The `= []`, `= null` matches in shipping code are all legitimate state initializers with data-fetch wiring (TanStack Query hooks populate them) or null-safety defaults. |

No blockers or warnings.

### Human Verification Required

Automated verification covers all code-level Success Criteria, but these qualitative behaviors can only be confirmed by a person in-browser:

#### 1. Chart renders correctly at desktop width

**Test:** Open the Endgames tab on a desktop browser (>=1024px). Navigate to the Overall Performance section.
**Expected:** The card below the WDL table renders a chart titled "Endgame vs Non-Endgame Score over Time" with two visible lines (endgame in brand blue, non-endgame in muted neutral), a colored shaded band between them (green segments where endgame > non-endgame + 1%, red segments where endgame < non-endgame - 1%, nothing when within epsilon). Y-axis is 0-100%. X-axis shows weekly date ticks.
**Why human:** Visual rendering of `<Area>` ranged-data bands across sign crossovers. jsdom does not compute fill colors reliably, so tests assert only on `data-testid` presence — a real browser is needed to see the green/red band colors and the anti-aliased line strokes.

#### 2. Chart renders correctly on mobile (<= 400px viewport)

**Test:** Open the Endgames tab in a 375px-wide viewport (Chrome DevTools iPhone SE profile). Scroll to the score-timeline chart.
**Expected:** Chart fits within the viewport (no horizontal scrollbar on the page), legend is readable, info popover opens above or below the trigger without overflowing, axis labels and tooltips remain legible.
**Why human:** Per CLAUDE.md's mobile-friendly rule. The `mobile no-overflow` vitest smoke test only checks `scrollWidth <= clientWidth` on a single synthetic container — it cannot verify font sizes, touch-target sizes, or legend-wrapping behavior.

#### 3. Info popover content reads cleanly

**Test:** Click/tap the `(i)` icon next to the chart title.
**Expected:** Popover shows three short paragraphs: a factual definition (trailing window + weekly sampling), a sentence explaining the shaded area color coding, and the sample-quality footnote (points with n < 10 hidden). No mention of "the Score Gap is a comparison, not an absolute measure."
**Why human:** Visual inspection of popover layout + copy — automated grep confirms strings are present/absent but not that the rendering is readable.

#### 4. Tooltip hover behavior

**Test:** Hover over a single weekly point on the chart.
**Expected:** Tooltip shows week-of date, endgame %, non-endgame %, `n=` game counts for each side, and a signed gap (e.g. "Gap: +5%" or "Gap: -3%"). Colors on the color swatches match the line colors above.
**Why human:** Tooltip pointer interaction cannot be reliably exercised in jsdom with Recharts' portaled/positioned tooltip layer.

#### 5. First LLM insights run after cache invalidation produces sane narration

**Test:** As a user with sufficient game history, trigger a fresh endgame insights report run (cache is invalidated by the `endgame_v13` prompt-version bump, so this will be a live LLM call).
**Expected:** The report narrates the endgame/non-endgame score relationship neutrally (describes both sides) without defaulting to "weak endgame" when the gap is negative. No mention of "Score Gap Timeline" or "comparison, not an absolute measure" in the narrative.
**Why human:** LLM output is non-deterministic; Success Criterion implicitly expects "existing insights snapshot tests pass" (which they do) but the lived quality of the narration — whether the v13 prompt's simplification actually reads well without the framing rule — is a judgment call that requires reviewing one or two real outputs.

### Gaps Summary

No code-level gaps. All five ROADMAP Success Criteria are satisfied by the codebase:

- Chart rework (Plan 02) landed cleanly with both absolute series, testid-carrying shaded bands, and the correct title.
- Backend subsection rename + two-findings-per-window shape (Plan 01) is complete; the `overall` subsection's `[summary score_gap]` aggregate is preserved (regression guarded by the new integration test).
- Prompt simplification (Plan 03) removed both the `score_gap` framing rule and the `score_gap_timeline` summary-suppression carve-out; `endgame_v13` bump invalidates cached reports.
- Info popover caveat is removed; the replacement sentence cleanly documents the shading semantics.
- Automated tests all pass (backend 68 passed on the targeted suites, plus the full 1057-test suite per Phase summary; frontend 8 passed on the targeted suite plus 106 overall).

Status is `human_needed` only because the phase ships visual/UX changes (mobile layout, chart rendering across sign crossovers, info popover UX, and a cache-invalidating prompt bump) that cannot be fully verified programmatically. The blocking question is not "does the code do what the plans say" (yes) but "does the rendered output and the first live LLM run look right" — that requires a human browser session and one fresh insights run.

---

_Verified: 2026-04-24T15:48:40Z_
_Verifier: Claude (gsd-verifier)_
