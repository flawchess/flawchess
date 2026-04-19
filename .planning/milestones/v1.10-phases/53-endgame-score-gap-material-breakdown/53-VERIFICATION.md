---
phase: 53-endgame-score-gap-material-breakdown
verified: 2026-04-12T15:30:00Z
status: human_needed
score: 6/6
overrides_applied: 0
human_verification:
  - test: "Navigate to Endgames > Stats tab and scroll to the bottom of the section list"
    expected: "A new 'Endgame Score Gap & Material Breakdown' section appears after the Timeline section, showing a signed score difference number (green if >= 0, red if < 0) and a 3-row material table with Ahead/Equal/Behind rows, Games/Win/Draw/Loss/Score columns, and colored Good/OK/Bad verdict badges"
    why_human: "Visual appearance, color rendering of oklch verdict badge colors, and table layout cannot be verified programmatically"
  - test: "Change the time control or platform filter and click Apply"
    expected: "The score difference and material table update to reflect the filtered game subset"
    why_human: "Filter reactivity requires live interaction with the running app"
  - test: "Narrow browser to mobile width (~375px)"
    expected: "Section is visible in the Stats tab on mobile; material table horizontally scrolls instead of breaking layout"
    why_human: "Responsive layout and horizontal scroll behavior require visual inspection"
---

# Phase 53: Endgame Score Gap & Material Breakdown Verification Report

**Phase Goal:** Users see an endgame score difference metric (endgame score minus non-endgame score) and a material-stratified WDL table showing performance when ahead, equal, or behind at endgame entry — directly answering "how much worse do I score in endgames?" and "does my material situation at entry predict my result?"
**Verified:** 2026-04-12T15:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Endgame Score Difference displayed as signed number (green >= 0, red < 0) with Score = (Win% + Draw%/2) / 100 | VERIFIED | `EndgameScoreGapSection.tsx` lines 56-57: `text-green-500` / `text-red-500` conditional on `data.score_difference >= 0`; `_wdl_to_score` in `endgame_service.py` line 470: `(wdl.win_pct + wdl.draw_pct / 2) / 100` |
| 2 | Material-stratified WDL table shows 3 rows (Ahead >= +100cp, Equal, Behind <= -100cp) with Games, Win%, Draw%, Loss%, Score, and Verdict columns | VERIFIED | Component renders `data.material_rows.map(...)` with all 7 columns; `_compute_score_gap_material` builds 3 rows for all bucket keys `("ahead", "equal", "behind")` unconditionally; `_MATERIAL_ADVANTAGE_THRESHOLD = 100` |
| 3 | Material balance read from `material_imbalance` at first ply of each endgame span | VERIFIED | `endgame_repository.py` lines 103-110: `array_agg(material_imbalance ORDER BY ply)[1]` returns value at the minimum (entry) ply; same `entry_rows` used by `_compute_score_gap_material` via `row[4]` |
| 4 | Verdict calibration: score >= overall -> Good, within -0.05 -> OK, below -0.05 -> Bad | VERIFIED | `_compute_verdict` in `endgame_service.py` lines 473-485; 20 unit tests in `TestScoreGapMaterial` all pass including boundary cases at 0.00 and -0.05 |
| 5 | Both metrics appear in new "Endgame Score Gap & Material Breakdown" section on Stats tab, positioned after existing sections | VERIFIED | `Endgames.tsx` lines 271-275: `EndgameScoreGapSection` rendered last in `statisticsContent` fragment, after `EndgameTimelineChart` |
| 6 | All existing sidebar filters apply correctly to the new metrics | VERIFIED | `scoreGapData` derived from `overviewData` fetched via `useEndgameOverview(appliedFilters)` — same `appliedFilters` that drives all other sections; backend `get_endgame_overview` accepts and passes all filter parameters through to `query_endgame_entry_rows` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/endgames.py` | MaterialRow, ScoreGapMaterialResponse, updated EndgameOverviewResponse | VERIFIED | Contains `class MaterialRow(BaseModel)`, `class ScoreGapMaterialResponse(BaseModel)`, `MaterialBucket = Literal[...]`, `Verdict = Literal[...]`, `score_gap_material: ScoreGapMaterialResponse` in `EndgameOverviewResponse` |
| `app/services/endgame_service.py` | `_compute_score_gap_material`, `_wdl_to_score`, `_compute_verdict`, `_get_endgame_performance_from_rows`, refactored `get_endgame_overview` | VERIFIED | All four functions present; `get_endgame_overview` calls `query_endgame_entry_rows` once and passes `entry_rows` to `_get_endgame_performance_from_rows` and `_compute_score_gap_material` |
| `tests/test_endgame_service.py` | TestScoreGapMaterial test class | VERIFIED | `class TestScoreGapMaterial:` at line 871 with 20 tests; all pass |
| `tests/test_endgames_router.py` | score_gap_material presence test | VERIFIED | `test_overview_has_score_gap_material_field` in `TestOverviewScoreGapMaterial` at line 269; passes |
| `frontend/src/types/endgames.ts` | MaterialRow, ScoreGapMaterialResponse, updated EndgameOverviewResponse | VERIFIED | `MaterialBucket`, `Verdict`, `MaterialRow`, `ScoreGapMaterialResponse` types added; `EndgameOverviewResponse.score_gap_material` added |
| `frontend/src/components/charts/EndgameScoreGapSection.tsx` | EndgameScoreGapSection component | VERIFIED | File exists, exports `EndgameScoreGapSection`, substantive (127 lines), uses theme imports, all `data-testid` attributes present |
| `frontend/src/pages/Endgames.tsx` | Renders EndgameScoreGapSection in statisticsContent | VERIFIED | Imports at line 24, renders at lines 271-275 with guard condition |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/endgame_service.py` | `app/schemas/endgames.py` | imports ScoreGapMaterialResponse, MaterialRow | VERIFIED | Line 32-51: explicit imports of `MaterialBucket`, `MaterialRow`, `ScoreGapMaterialResponse`, `Verdict` |
| `get_endgame_overview` | `_compute_score_gap_material` | direct function call with entry_rows, endgame_wdl, non_endgame_wdl | VERIFIED | Lines 1059-1061: `score_gap_material = _compute_score_gap_material(performance.endgame_wdl, performance.non_endgame_wdl, entry_rows)` |
| `frontend/src/pages/Endgames.tsx` | `frontend/src/components/charts/EndgameScoreGapSection.tsx` | component import and render | VERIFIED | Import at line 24; rendered at line 273 with `data={scoreGapData}` |
| `EndgameScoreGapSection.tsx` | `frontend/src/types/endgames.ts` | type imports for ScoreGapMaterialResponse | VERIFIED | Line 9: `import type { ScoreGapMaterialResponse, Verdict } from '@/types/endgames'` |
| `EndgameScoreGapSection.tsx` | `frontend/src/lib/theme.ts` | theme color imports for verdict badges | VERIFIED | Line 8: `import { WDL_WIN, WDL_LOSS, GAUGE_WARNING } from '@/lib/theme'` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `EndgameScoreGapSection.tsx` | `data: ScoreGapMaterialResponse` | `overviewData?.score_gap_material` from `useEndgameOverview` TanStack Query hook → `endgameApi.getOverview` → `GET /api/endgames/overview` → `get_endgame_overview` → `_compute_score_gap_material` which aggregates `entry_rows` from `query_endgame_entry_rows` (real DB query on `game_positions`) | Yes — DB `array_agg(material_imbalance ORDER BY ply)` aggregation confirmed in `endgame_repository.py` lines 103-168 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_wdl_to_score` returns 0.5 for 45/10/45 WDL | `uv run pytest tests/test_endgame_service.py::TestScoreGapMaterial -x -q` | 20 passed in 0.32s | PASS |
| `_compute_verdict` boundaries | same test run | included in 20 passed | PASS |
| `_compute_score_gap_material` bucket assignment, deduplication, None handling | same test run | included in 20 passed | PASS |
| Router integration: `GET /api/endgames/overview` has `score_gap_material` key | `uv run pytest tests/test_endgames_router.py -x -q` | 15 passed in 0.71s | PASS |
| TypeScript compilation | `npx tsc --noEmit` (frontend) | 0 errors | PASS |
| ESLint | `npm run lint` (frontend) | 0 warnings | PASS |
| Dead exports | `npm run knip` (frontend) | 0 issues | PASS |
| Type checking (backend) | `uv run ty check app/schemas/endgames.py app/services/endgame_service.py` | All checks passed | PASS |

### Requirements Coverage

No explicit requirement IDs (phase spec is in `docs/endgame-analysis-v2.md` sections 1-2). All 6 roadmap success criteria verified above.

### Anti-Patterns Found

None found in modified files. No TODOs, FIXMEs, placeholder text, empty returns, or hardcoded empty values in any modified file.

### Human Verification Required

#### 1. Visual rendering of new section

**Test:** Start dev servers with `bin/run_local.sh`, log in, navigate to Endgames > Stats tab, scroll past all existing sections.
**Expected:** A new "Endgame Score Gap & Material Breakdown" section appears with: (a) a signed score difference number in green (if >= 0) or red (if < 0), showing endgame vs non-endgame subscript; (b) a table with 3 rows labelled "Ahead (>= +1)", "Equal", "Behind (<= -1)" and columns Material at entry, Games, Win, Draw, Loss, Score, Verdict; (c) colored verdict badges (green Good, amber OK, red Bad) using oklch colors.
**Why human:** oklch color rendering, visual layout quality, and table formatting require visual inspection.

#### 2. Filter reactivity

**Test:** Apply a time control filter (e.g., Bullet only) or a platform filter, then observe the new section.
**Expected:** Score difference and material breakdown table update to reflect the filtered game subset.
**Why human:** Filter reactivity with live data requires running app interaction.

#### 3. Mobile layout

**Test:** Narrow browser to ~375px (or use DevTools mobile simulation).
**Expected:** The section appears in the Stats tab on mobile. The material table triggers horizontal scroll rather than collapsing or breaking layout (due to `min-w-[480px]` and `overflow-x-auto`).
**Why human:** Responsive layout and horizontal scroll behavior require visual inspection.

### Gaps Summary

No gaps found. All 6 roadmap success criteria are met by the implementation. The 3 human verification items above are UI/UX quality checks, not blocking functional gaps.

---

_Verified: 2026-04-12T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
