---
phase: 86-section-2-endgame-metrics-4-card-layout
verified: 2026-05-14T14:39:24Z
status: human_needed
score: 24/24 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Desktop 4-card layout + connector arrows"
    expected: "At ≥1024px width, cards arrange Conv | Parity | Recov on row 1 with Endgame Skill alone in the middle column on row 2; SVG arrows visibly connect each of the 3 top cards to the Skill card (left→right-pointing into Skill's left edge, middle→down-pointing into Skill's top, right→left-pointing into Skill's right edge)."
    why_human: "Visual SVG geometry / DOM layout; ResizeObserver-driven coordinates can't be inspected programmatically without running a real browser."
  - test: "Mobile stacking + arrow hiding"
    expected: "At <1024px width, the 4 cards stack single-column in DOM order (Conv → Parity → Recov → Skill); connector arrows are hidden via the mobile-bail check in ConnectorArrows.compute()."
    why_human: "Visual responsive-layout check requires a real viewport."
  - test: "Per-card MetricStatPopover content (D-16)"
    expected: "Hovering the HelpCircle next to 'Diff:' on each Conv/Parity/Recov card opens the per-card explanation + methodology block. Skill card popover renders the composite explanation."
    why_human: "Hover/tap behavior + popover positioning + content readability are user-perception checks."
  - test: "Page-level h2 InfoPopover (D-11)"
    expected: "Hovering the HelpCircle next to the 'Endgame Metrics and ELO' h2 opens the lifted bucket-taxonomy + mirror-bucket explainer + ELO-uses-same-Skill closing note."
    why_human: "Visual popover trigger + content layering."
  - test: "Filter responsiveness"
    expected: "Applying a filter (e.g. Opponent Strength: Stronger) updates the You / Opp / Diff values on each card; gauges stay the same (gauge bands are fixed per D-13 / SEC2-04)."
    why_human: "Live filter-state propagation through TanStack Query + re-render; requires running backend + a real user-import of games."
  - test: "Legacy removal visual confirmation"
    expected: "The legacy 4-gauge strip and eval-stratified WDL table are gone; only the 4 new cards are visible under the h2."
    why_human: "User-perception confirmation that nothing was left dangling visually after the deletion."
---

# Phase 86: Section 2 Endgame Metrics 4-card Layout — Verification Report

**Phase Goal:** "Section 2 — Endgame Metrics: 4-card layout (Conv/Parity/Recov + composite Endgame Skill)"
**Verified:** 2026-05-14T14:39:24Z
**Status:** human_needed
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `compute_skill_diff_test` exists in `score_confidence.py`, returns 5-tuple, uses headline-rate variance per bucket, mirror identity, gating per D-01 | VERIFIED | `app/services/score_confidence.py:375` defines the helper. Private `_headline_rate` (line 77) + `_headline_rate_variance` (line 100) implement Conv = Bernoulli win, Recov = Bernoulli save, Parity = trinomial chess-score. Variance-0 trap + `math.erfc(|z|/sqrt(2))` + `CI_Z_95` CI all present. 7 unit tests in `TestComputeSkillDiffTest` (test_score_confidence.py:562) including the BLOCKER 2 regression `test_skill_diff_uses_per_bucket_headline_variance_not_chess_score_variance` pass. |
| 2 | `compute_per_bucket_diff_test` exists, signature `(bucket, user_row, opp_row)`, strict opp-side gate at N=10, parity self-mirror produces diff = 2·rate − 1 | VERIFIED | `app/services/score_confidence.py:497`. 6 tests in `TestComputePerBucketDiffTest` (line 780) including the BLOCKER 1 regression `test_parity_self_mirror_produces_nontrivial_diff` (line 813). All 13 score_confidence Phase 86 tests pass. |
| 3 | `ScoreGapMaterialResponse` exposes 5 new top-level Skill fields (`skill`, `opp_skill`, `skill_diff_p_value`, `skill_diff_ci_low`, `skill_diff_ci_high`) | VERIFIED | `app/schemas/endgames.py` lines 375, 378, 381, 384, 387. All `float \| None = None`. |
| 4 | `MaterialRow` exposes 3 new per-bucket diff fields (`diff_p_value`, `diff_ci_low`, `diff_ci_high`) | VERIFIED | `app/schemas/endgames.py` lines 282, 284, 286. All `float \| None = None`. |
| 5 | `_compute_score_gap_material` wires `compute_skill_diff_test` once (aggregate) and `compute_per_bucket_diff_test` per-bucket | VERIFIED | Imports at `app/services/endgame_service.py:75,78`. Skill aggregate call at line 912 (after rows_by_game loop). Per-bucket call at line 974 inside material_rows loop. `MaterialRow(... diff_p_value=...)` at line 988. `ScoreGapMaterialResponse(... skill=skill, opp_skill=opp_skill, skill_diff_p_value=..., ...)` at lines 1005-1006. |
| 6 | TS types mirror the new fields (3 per row + 5 top-level) | VERIFIED | `frontend/src/types/endgames.ts` lines 129-131 (MaterialRow) + 173-177 (ScoreGapMaterialResponse). All `number \| null`. |
| 7 | `lib/endgameMetrics.ts` exists with 13 exports (MIRROR_BUCKET, userRate, opponentRate, formatScorePct, formatDiffPct, BUCKET_DISPLAY_LABELS, BUCKET_DISPLAY_LABELS_WITH_METRIC, NEUTRAL_ZONE_MIN, NEUTRAL_ZONE_MAX, BULLET_DOMAIN, MIN_OPPONENT_BASELINE_GAMES, FIXED_GAUGE_ZONES, ENDGAME_SKILL_ZONES) | VERIFIED | All 13 exports present (lines 27, 37, 44, 54, 62, 75, 89, 100, 101, 106, 111, 122, 132). `endgameSkill()` correctly NOT lifted (D-04 retirement). |
| 8 | `EndgameOverallConnectorArrows.tsx` accepts 4 testid props + uses them in querySelector | VERIFIED | Props declared at lines 43-46; destructured at lines 51-54; template-literal selectors at lines 65, 68, 71, 74; useEffect deps at line 112. No hard-coded selectors remain. |
| 9 | Phase 85 call site (`EndgameOverallPerformanceSection.tsx`) passes 4 testids explicitly | VERIFIED | Lines 253-256 pass the 4 legacy testids (`tile-games-without-endgame`, `tile-at-endgame-entry`, `tile-games-with-endgame`, `endgame-score-differences`). |
| 10 | `EndgameMetricCard` renders gauge → games-count → WDL bar → peer-bullet for Conv/Parity/Recov; sig-gated diff color via deriveLevel + isConfident triple | VERIFIED | `EndgameMetricCard.tsx` lines 60-217. `EndgameGauge` at line 100 using `FIXED_GAUGE_ZONES[bucket]`. Games-count Swords row at lines 111-122. `MiniWDLBar` at line 124. Sig-gating triple at lines 82-87 (`deriveLevel` + `isConfident` + `outsideNeutral` + `MIN_OPPONENT_BASELINE_GAMES`). MetricStatPopover at line 164. Empty-state branch line 212. Missing-opponent branch line 203. |
| 11 | `EndgameSkillCard` renders gauge → games-count → peer-bullet (no WDL); empty state when skill === null | VERIFIED | `EndgameSkillCard.tsx` lines 56-195. `EndgameGauge` at line 88 using `ENDGAME_SKILL_ZONES`. Games-count at lines 99-107 (no share %). MetricStatPopover at line 142. No `MiniWDLBar` import (grep confirms 0 matches). Empty-state branch line 190. Missing-opponent branch line 181. |
| 12 | Card testids: `tile-conversion`, `tile-parity`, `tile-recovery`, `tile-endgame-skill` per D-09b | VERIFIED | `EndgameMetricsSection.tsx` lines 54-58 (TILE_TESTIDS), line 133 (`tile-endgame-skill`). All four reach DOM via the card components' `tileTestId` prop. |
| 13 | Per-bucket diff sig fields come from `row.diff_p_value` etc. (Plan 02 wire); Skill sig fields come from `pValue` / `ciLow` / `ciHigh` props | VERIFIED | `EndgameMetricCard.tsx:82` uses `row.diff_p_value`; lines 195-196 use `row.diff_ci_low/high`. `EndgameSkillCard.tsx:72` uses `pValue`; lines 173-174 use `ciLow`/`ciHigh`. Orchestrator at `EndgameMetricsSection.tsx:130-132` derives Skill props from `data.skill_diff_*`. |
| 14 | `EndgameMetricsSection.tsx` exists as orchestrator: mounts 3 MetricCard + 1 SkillCard in `relative grid grid-cols-1 lg:grid-cols-3 gap-4` with Skill at `lg:col-start-2` | VERIFIED | Lines 81-147. Grid at line 100-103. `ROW_ONE_BUCKETS.map(...)` mounts 3 cards (lines 104-121). `<div className="lg:col-start-2">` wraps SkillCard (line 125-135). `<ConnectorArrows>` at lines 137-143 with the four Phase 86 testids. |
| 15 | Section sub-question rendered: "Do you outperform your opponents at converting, holding, and recovering?" (D-10) — no section-level h3, no section-level InfoPopover | VERIFIED | `EndgameMetricsSection.tsx:91-93`. No h3 in file (grep confirms). |
| 16 | `Endgames.tsx` mounts `<EndgameMetricsSection data={scoreGapData} />` at the old `EndgameScoreGapSection` site | VERIFIED | Import at line 24; mount at line 523. Wrapped in `charcoal-texture` div at line 522. |
| 17 | Page-level h2 "Endgame Metrics and ELO" has new `<InfoPopover>` with lifted bucket-taxonomy + ELO-uses-same-Skill content (D-11) | VERIFIED | `Endgames.tsx` lines 458-521. `<InfoPopover ... testId="endgame-metrics-and-elo-info">` at line 461. Content: bucket taxonomy paragraph (lines 467-473), per-bucket ul (lines 478-492), gauges-vs-table explainer (lines 497-503), per-card peer-bullet paragraph replaces legacy "table" paragraph (lines 504-512), ELO closing note (lines 513-517). |
| 18 | `EndgameScoreGapSection.tsx` is deleted | VERIFIED | `test -f frontend/src/components/charts/EndgameScoreGapSection.tsx` returns non-zero. No active imports (only doc comments mention the name in MiniBulletChart.tsx, endgameMetrics.ts, generated/endgameZones.ts, EndgameMetricsSection.tsx). |
| 19 | Stale `vi.mock` in `Endgames.overallPerformance.test.tsx` updated to mock `EndgameMetricsSection` | VERIFIED | Lines 64-65 mock `@/components/charts/EndgameMetricsSection` returning `mock-endgame-metrics-section` testid. |
| 20 | Legacy testids gone (`material-row-*`, `material-card-*`, `endgame-gauge-strip`, `material-table`, `mock-endgame-score-gap-section`) | VERIFIED | `grep -rn "mock-endgame-score-gap-section\|material-row-conversion\|material-row-parity\|material-row-recovery\|endgame-gauge-strip\|material-table" frontend/src/` returns no matches. |
| 21 | `knip.json` adds `src/generated/endgameZones.ts` to ignore list (resolves codegen alias false-positive) | VERIFIED | `frontend/knip.json` line 19 includes the path. |
| 22 | Frontend `endgameSkill()` retired (D-04) — server now owns the composite | VERIFIED | `grep -rn "endgameSkill\(" frontend/src/` returns no matches. |
| 23 | Vitest coverage for the 3 new components passes (EndgameMetricCard / EndgameSkillCard / EndgameMetricsSection) | VERIFIED | Test files exist at `frontend/src/components/charts/__tests__/`. `npm test -- --run EndgameMetricCard EndgameSkillCard EndgameMetricsSection` reports 16 tests passing across 3 files. |
| 24 | Pytest covers schema-presence + n_active gating + sparse-opp gating on `_compute_score_gap_material` | VERIFIED | `test_score_gap_material_carries_skill_and_per_bucket_diff_fields` (line 4705), `test_score_gap_material_skill_gated_below_two_active_buckets` (line 4775), `test_score_gap_material_skill_gated_below_opponent_baseline` (line 4813) in `tests/test_endgame_service.py`. 26 selected tests pass. |

**Score:** 24/24 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/score_confidence.py` | `compute_skill_diff_test` + `compute_per_bucket_diff_test` + `_headline_rate` + `_headline_rate_variance` | VERIFIED | All 4 functions present (lines 77, 100, 375, 497). Imports `math.erfc`, `CI_Z_95`, `CONFIDENCE_MIN_N`. |
| `app/schemas/endgames.py` | 5 Skill + 3 per-row diff fields | VERIFIED | All 8 fields present; defaults to None; docstrings cite Phase 86 + SEC2-* IDs. |
| `app/services/endgame_service.py` | Both helpers imported + wired into `_compute_score_gap_material` | VERIFIED | Imports lines 75,78; calls lines 912, 974; constructor wiring at lines 988, 1005-1006. |
| `frontend/src/types/endgames.ts` | 3 + 5 new `number \| null` fields | VERIFIED | Lines 129-131 + 173-177. |
| `frontend/src/lib/endgameMetrics.ts` | 13 exports, no `endgameSkill` | VERIFIED | All 13 exports confirmed via grep; `endgameSkill` absent. 117 lines (≥80 min). |
| `frontend/src/components/charts/EndgameMetricCard.tsx` | Conv/Parity/Recov shared shell | VERIFIED | 217 lines (≥100 min). Wires gauge + WDL + peer-bullet + popover. |
| `frontend/src/components/charts/EndgameSkillCard.tsx` | Skill variant (no WDL) | VERIFIED | 195 lines (≥70 min). No `MiniWDLBar` import. |
| `frontend/src/components/charts/EndgameMetricsSection.tsx` | 4-card orchestrator | VERIFIED | 147 lines (≥80 min). Grid + ConnectorArrows + sub-question. |
| `frontend/src/components/charts/EndgameOverallConnectorArrows.tsx` | 4 testid props | VERIFIED | Interface, destructure, useEffect deps, all 4 querySelector usages parameterized. |
| `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` | Phase 85 call site passes 4 testids | VERIFIED | Lines 253-256. |
| `frontend/src/pages/Endgames.tsx` | Mount swap + h2 InfoPopover | VERIFIED | Import line 24, mount line 523, InfoPopover lines 461-519. |
| `frontend/src/components/charts/EndgameScoreGapSection.tsx` | DELETED | VERIFIED | File absent. |
| `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx` | mock retargeted to EndgameMetricsSection | VERIFIED | Lines 64-65. |
| `frontend/knip.json` | generated/endgameZones.ts in ignore list | VERIFIED | Line 19. |
| `tests/services/test_score_confidence.py` | TestComputeSkillDiffTest + TestComputePerBucketDiffTest with regression tests | VERIFIED | Classes at lines 562, 780. Both regression tests present (705, 813). 13 tests pass. |
| `tests/test_endgame_service.py` | 3 new service tests for Skill + per-bucket diff wiring | VERIFIED | Methods at lines 4705, 4775, 4813. Pass under `-k "skill or diff_p_value or diff_ci"`. |
| `frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx` | structural + sig-gated + empty + missing-opp tests | VERIFIED | Passes 6 tests. |
| `frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx` | structural + sig-gated + empty + tileTestId tests | VERIFIED | Passes 7 tests. |
| `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx` | full-render + Skill gating + DOM ordering | VERIFIED | Passes 3 tests. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_compute_score_gap_material` | `compute_skill_diff_test` | 6-tuple arg list, mirror identity | WIRED | line 912: `skill, opp_skill, skill_p, skill_ci_low, skill_ci_high = compute_skill_diff_test(conv_row, parity_row, recov_row, opp_conv_row, opp_parity_row, opp_recov_row)`. Mirror identity (`opp_conv_row = recov_row`, etc.) per swap dict — comment at line 884-888 documents the inversion contract. |
| `_compute_score_gap_material` (per-bucket loop) | `compute_per_bucket_diff_test` | per-bucket call with mirror W/D/L/N | WIRED | line 974: `diff_p, diff_ci_low_v, diff_ci_high_v = compute_per_bucket_diff_test(b2, user_row_b2, opp_row_b2)`. |
| `MaterialRow(...)` constructor | new diff fields | kwargs | WIRED | line 988: `diff_p_value=diff_p`, `diff_ci_low=diff_ci_low_v`, `diff_ci_high=diff_ci_high_v`. |
| `ScoreGapMaterialResponse(...)` constructor | new Skill fields | kwargs | WIRED | lines 1005-1006: `skill=skill`, `opp_skill=opp_skill`, `skill_diff_p_value=skill_p`, plus CI low/high. |
| `EndgameMetricCard` | `lib/endgameMetrics` | imports | WIRED | lines 24-36 import 11 helpers/constants. |
| `EndgameMetricCard` + `EndgameSkillCard` | `MetricStatPopover` | mount with D-16 props | WIRED | EndgameMetricCard.tsx:164; EndgameSkillCard.tsx:142. |
| `EndgameMetricCard` + `EndgameSkillCard` | `deriveLevel` (Phase 85 sig-triple) | import + call | WIRED | EndgameMetricCard.tsx:82, EndgameSkillCard.tsx:72. |
| `EndgameMetricsSection` | `EndgameMetricCard` + `EndgameSkillCard` + `ConnectorArrows` | 3 imports + JSX mounts | WIRED | lines 30-32; mounts lines 110-119, 126-134, 137-143. |
| `Endgames.tsx` | `EndgameMetricsSection` | swapped mount | WIRED | import line 24; mount line 523. |
| `Endgames.tsx` h2 | new `<InfoPopover>` | inline trigger | WIRED | lines 461-519, testId `endgame-metrics-and-elo-info`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EndgameMetricsSection` | `data: ScoreGapMaterialResponse` | Endgames.tsx page → `scoreGapData` TanStack Query against backend `_compute_score_gap_material` | Yes — backend computes from real `game_positions` aggregations (see Phase 60 + Phase 85.1 + Phase 86 wiring) | FLOWING |
| `EndgameMetricCard` | `row` + `mirror` (`MaterialRow`) | derived from `data.material_rows` in orchestrator | Yes | FLOWING |
| `EndgameSkillCard` | `skill` / `oppSkill` / sig fields | `data.skill`, `data.opp_skill`, `data.skill_diff_*` populated by Plan 02 wiring | Yes | FLOWING |
| `compute_skill_diff_test` / `compute_per_bucket_diff_test` | W/D/L/N integer tuples | `bucket_wins`/`bucket_draws`/`bucket_losses`/`bucket_games` accumulators built from `rows_by_game` loop in `_compute_score_gap_material` (lines 814-879 region) | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend Phase 86 unit tests | `uv run pytest tests/services/test_score_confidence.py::TestComputeSkillDiffTest tests/services/test_score_confidence.py::TestComputePerBucketDiffTest` | 13 passed | PASS |
| Service-layer wiring tests | `uv run pytest tests/test_endgame_service.py -k "skill or diff_p_value or diff_ci or skill_gated"` | 26 passed | PASS |
| Frontend Phase 86 component tests | `cd frontend && npm test -- --run EndgameMetricCard EndgameSkillCard EndgameMetricsSection` | 16 passed (3 files) | PASS |
| Existing Phase 85 connector arrows tests still green (regression) | covered by orchestrator gate sweep (see SUMMARY) | 391 frontend tests pass | PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` files exist for this project; phase is frontend-redesign + backend math addition, not a migration/tooling phase. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SEC2-01 | 86-05 | 4 cards in order Conversion → Parity → Recovery → Endgame Skill | SATISFIED | `EndgameMetricsSection.tsx`: `ROW_ONE_BUCKETS = ['conversion', 'parity', 'recovery']` map at line 36; SkillCard mounted after at line 126. DOM-order test in EndgameMetricsSection.test.tsx asserts Conv → Parity → Recovery → Skill. |
| SEC2-02 | 86-04, 86-05 | Conv/Parity/Recov identical layout: gauge → percent + games → WDL → peer bullet vs 0 | SATISFIED | `EndgameMetricCard.tsx` mounts gauge (line 100), games-count Swords row (lines 111-122), MiniWDLBar (line 124), peer-bullet text + MiniBulletChart (lines 134-200). All 3 buckets use the same component. |
| SEC2-03 | 86-04, 86-05 | Skill card: gauge → percent + games → peer bullet (no WDL) | SATISFIED | `EndgameSkillCard.tsx` lacks `MiniWDLBar` import (grep confirms 0). Has gauge (line 88), games-count (lines 99-107), peer bullet (lines 112-179). |
| SEC2-04 | 86-03, 86-04, 86-05 | Gauges use FIXED_GAUGE_ZONES; peer bullet neutral band per POLISH-01 | SATISFIED | `EndgameMetricCard.tsx:103` uses `FIXED_GAUGE_ZONES[bucket]`. Neutral band `[NEUTRAL_ZONE_MIN, NEUTRAL_ZONE_MAX] = [-0.05, 0.05]` from `lib/endgameMetrics.ts`. POLISH-01 (cell-specific bands) explicitly deferred to Phase 88 per CONTEXT D-12; baseline ±5pp is in effect now. |
| SEC2-06 | 86-01, 86-02, 86-05 | Peer bullet uses mirror-bucket rate; Wald-z sig test on signed diff vs 0, gated on MIN_OPPONENT_BASELINE_GAMES | SATISFIED | `compute_per_bucket_diff_test` (score_confidence.py:497) implements Wald-z with mirror-identity `1 − userRate(opp_row)`, strict opp-side gate at CONFIDENCE_MIN_N=10. Wired in `_compute_score_gap_material` per-bucket loop (line 974). |
| SEC2-07 | 86-03 | Mirror-bucket peer baseline logic preserved (opponentRate / MIRROR_BUCKET / MIN_OPPONENT_BASELINE_GAMES) | SATISFIED | All three helpers preserved in `lib/endgameMetrics.ts` (lines 62, 89, 111). Consumed by EndgameMetricCard.tsx + orchestrator. |
| SEC2-08 | 86-01, 86-02 | Skill peer-bullet sig-test methodology resolved (Wald-z on derived diff) | SATISFIED | `compute_skill_diff_test` (score_confidence.py:375) — Wald-z on aggregate skill diff with per-bucket headline-rate variance + 95% CI + gates (n_active<2 OR any opp sparse). |
| SEC2-09 | 86-04, 86-05 | InfoPopover on each peer bullet explains mirror-bucket interpretation and filter-responsiveness | SATISFIED | `MetricStatPopover` mount in both card components carries D-16 locked copy (metricExplanation prop from orchestrator at EndgameMetricsSection.tsx:39-46 explicitly cites "Filter-responsive" and "compared to your opponents in the mirror bucket"). Skill card popover at EndgameSkillCard.tsx:142-165. |
| SEC2-10 | 86-05 | Legacy `EndgameScoreGapSection` table and 4-gauge strip removed | SATISFIED | File deleted (confirmed via test -f). No active imports remain; legacy testids absent (grep confirms). knip clean (per SUMMARY gate report). |

No orphaned requirements found — all 9 SEC2-* IDs declared in plan frontmatter map to REQUIREMENTS.md entries that target Phase 86, and all are satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/endgame_service.py` | 745-1058 | `_compute_score_gap_material` is ~313 logic LOC (CLAUDE.md hard limit 200) | Warning | Pre-existing bloat; Phase 86 added ~70 LOC. Tracked in 86-REVIEW.md as WR-01 with explicit deferral to a `/gsd-quick` or Phase 88 follow-up. Not a blocker. |
| `frontend/src/components/charts/EndgameSkillCard.tsx` | 66-67 | Unreachable `oppSkill === null` branch (backend invariant guarantees joint null/non-null) | Info | Defensive code; harmless. Tracked in REVIEW as WR-02. |
| `frontend/src/components/charts/EndgameMetricCard.tsx` | 76-87 | `diff` computed from rounded `win_pct`-based rates while pValue/CI derive from unrounded backend math | Info | Sig-gating reads slightly different value than test that produced pValue; small numerical noise, no logical break. Tracked as WR-03. |
| `frontend/src/components/charts/EndgameSkillCard.tsx` | 72 | `deriveLevel(pValue, totalGames)` uses all-bucket sum as n-floor while backend p-value gates on per-bucket opp N | Info | Semantically misleading but benign — backend already returns `null` pValue when its gates fail, so frontend defaults to `'low'`. Tracked as WR-04. |

No `TBD`/`FIXME`/`XXX` debt markers were introduced. The `EndgameOverallConnectorArrows.tsx` already-existing `TODO` references (if any) are pre-existing. No empty implementations, no `return null` stubs, no console.log-only handlers in the new code.

### Human Verification Required

See `human_verification` block in frontmatter. Six items collected from 86-05-SUMMARY.md's deferred checkpoint:

1. **Desktop 4-card layout + SVG connector arrows** — geometry must be confirmed in a real viewport.
2. **Mobile stacking + arrow hiding** — responsive single-column verification at <1024px.
3. **Per-card MetricStatPopover content (D-16)** — hover/tap behavior + content readability for the 4 popovers.
4. **Page-level h2 InfoPopover (D-11)** — bucket-taxonomy + ELO closing note rendering.
5. **Filter responsiveness** — applying Opponent Strength: Stronger should shift You/Opp/Diff while gauges stay fixed.
6. **Legacy removal visual confirmation** — 4-gauge strip + WDL table absent under the h2.

### Gaps Summary

No gaps. All 24 must-have truths verified, all 19 required artifacts present at full Level-1/2/3 quality (exists, substantive, wired), data flow traced through to backend aggregations, requirements coverage complete (9/9 SEC2-* satisfied), behavioral spot-checks pass (16 frontend tests + 39+ backend tests confirmed green), no critical anti-patterns introduced.

The four review warnings (WR-01 function size, WR-02 unreachable branch, WR-03 raw-vs-rounded inconsistency, WR-04 misleading n-floor semantics) are tracked in 86-REVIEW.md and do not block the phase goal. Status is `human_needed` solely because Plan 86-05's documented `checkpoint:human-verify` task (deferred per autonomous-orchestration rules) remains outstanding — the visual layout / popovers / filter responsiveness must be confirmed in a running browser before Phase 86 is declared fully done.

---

_Verified: 2026-05-14T14:39:24Z_
_Verifier: Claude (gsd-verifier)_
