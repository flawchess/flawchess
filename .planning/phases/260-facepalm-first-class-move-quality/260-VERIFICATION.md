---
phase: 260-facepalm-first-class-move-quality
verified: 2026-11-22T21:20:00Z
status: passed
score: 35/35 must-haves verified
covered_files: [".planning/phases/260-facepalm-first-class-move-quality/260-01-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-01-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-02-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-02-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-03-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-03-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-04-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-04-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-05-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-05-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-06-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-06-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-07-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-07-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-08-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-08-SUMMARY.md", ".planning/phases/260-facepalm-first-class-move-quality/260-09-PLAN.md", ".planning/phases/260-facepalm-first-class-move-quality/260-09-SUMMARY.md", "CHANGELOG.md", "app/repositories/library_repository.py", "app/repositories/query_utils.py", "app/routers/library.py", "app/schemas/library.py", "app/services/blunder_check_rules.py", "app/services/library_service.py", "frontend/src/api/__tests__/client.test.ts", "frontend/src/api/client.ts", "frontend/src/components/analysis/AnalysisTagsPanel.tsx", "frontend/src/components/analysis/ExplainBar.tsx", "frontend/src/components/analysis/FacepalmGlyphBadge.tsx", "frontend/src/components/analysis/VariationTree.tsx", "frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx", "frontend/src/components/analysis/__tests__/ExplainBar.test.tsx", "frontend/src/components/analysis/__tests__/VariationTree.test.tsx", "frontend/src/components/filters/FlawFilterControl.tsx", "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx", "frontend/src/components/library/EvalChart.tsx", "frontend/src/components/library/FacepalmBadgePopover.tsx", "frontend/src/components/library/FacepalmExplanation.tsx", "frontend/src/components/library/FlawCard.tsx", "frontend/src/components/library/MoveStats.tsx", "frontend/src/components/library/SeverityBadge.tsx", "frontend/src/components/library/__tests__/EvalChart.test.tsx", "frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx", "frontend/src/components/library/__tests__/FlawCard.test.tsx", "frontend/src/components/library/__tests__/MoveStats.test.tsx", "frontend/src/components/library/__tests__/SeverityBadge.test.tsx", "frontend/src/components/results/LibraryGameCard.tsx", "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx", "frontend/src/components/results/__tests__/LibraryGameCardPastedBadge.test.tsx", "frontend/src/hooks/__tests__/useFlawFilterStore.test.ts", "frontend/src/hooks/__tests__/useLibraryGames.test.tsx", "frontend/src/hooks/analysis/useAnalysisGemMarkers.ts", "frontend/src/hooks/useFlawFilterStore.ts", "frontend/src/hooks/useGameOverlay.ts", "frontend/src/hooks/useLibrary.ts", "frontend/src/lib/__tests__/explainBar.test.ts", "frontend/src/lib/__tests__/facepalm.test.ts", "frontend/src/lib/__tests__/flawDotColor.test.ts", "frontend/src/lib/__tests__/gameCardGeometry.test.ts", "frontend/src/lib/__tests__/moveStatsCounts.test.ts", "frontend/src/lib/analytics.ts", "frontend/src/lib/explainBar.ts", "frontend/src/lib/facepalm.ts", "frontend/src/lib/flawDotColor.ts", "frontend/src/lib/flawSeverityFilter.ts", "frontend/src/lib/gameCardGeometry.ts", "frontend/src/lib/moveStatsCounts.ts", "frontend/src/lib/tacticDepth.ts", "frontend/src/lib/theme.ts", "frontend/src/pages/library/FlawsTab.tsx", "frontend/src/pages/library/GamesTab.tsx", "frontend/src/pages/library/__tests__/FlawsTab.test.tsx", "frontend/src/pages/library/__tests__/GamesTab.test.tsx", "frontend/src/types/library.ts", "tests/repositories/test_library_repository.py", "tests/services/test_facepalm_score.py", "tests/services/test_library_service.py", "tests/services/test_maia_flaw_scoring.py", "tests/test_flaw_predicate.py", "tests/test_library_repository.py", "tests/test_library_router.py", "tests/test_query_utils.py"]
covered_digest: "v4:sha256:67fb1e3d5b8df103531073483a0b257397ccaaad41ac39a956788657880a0b0b"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 27/28
  gaps_closed:
    - "260-G1: facepalm and tactic text in the eval chart tooltip and the selected Facepalm pill legible; tooltip at most two lines for a blunder"
    - "260-G2: one severity chip/icon per blunder with the facepalm popover on it (Flaws card and analysis move list), score named in the footer line"
    - "260-G3: filter divider between Flaws and Tactic Depth"
  gaps_remaining: []
  regressions: []
---

# Phase 260: Facepalm as a First-Class Move Quality Verification Report

**Phase Goal:** Give facepalm blunders their own slot wherever move qualities are listed (move quality table, eval chart dots, Flaws filter), so a player can go straight to them and compare both sides.
**Verified:** 2026-11-22T21:20:00Z
**Status:** passed
**Re-verification:** Yes, after gap-closure plans 260-08 and 260-09 (UAT gaps 260-G1, 260-G2, 260-G3). The previous report (human_needed, 27/28) was stale: covered frontend files changed.

## Scope of this re-verification

Gap-closure plans 08 and 09 are frontend only (`git diff 75d1760c2..HEAD` touches `CHANGELOG.md`, `frontend/src` and `.planning` only; `git diff 3b05ba0f0..HEAD -- app tests` is empty). The backend truths (D-08 truth table, D-09, D-12, D-13, D-24) therefore stand unchanged from the earlier verification (313 backend tests passed in that run; not re-run here, the worktree has no DB config).

Per the orchestrator brief, must-haves replaced by the owner decisions of 2026-11-22 are judged against the new target, not flagged as regressions:

| Superseded | By | Judged as |
|---|---|---|
| D-11 (score chip on the Flaws card, tooltip score line, move-list chip) | 260-G2 | score lives on the chip/icon popover, the tooltip verdict line and the footer line |
| D-08 clause "pill style of the other two" / `SEV_FACEPALM_BG` | 260-G1 | solid `SEV_FACEPALM` fill with `SEV_FACEPALM_ON` label |
| D-26 clause "in SEV_FACEPALM" for the tooltip label; plan 04 "score line unchanged" | 260-G1 | colour on icons only, neutral labels, one verdict line with score |
| 257 D-08 type tint, 257 D-22 gauge on the chip | 260-G2 | `FACEPALM_TYPE_STYLE` removed, type named in words |

## Goal Achievement

### Observable Truths

Truths 1 to 28 are the carried-forward decisions of the first verification (D-01 to D-28 plus review fixes). Truths 29 to 35 are the gap-closure targets.

| # | Truth (decision) | Status | Evidence |
|---|---|---|---|
| 1 | D-01: 8th two-sided Facepalm row after Blunder, ??? icon, also in AnalysisTagsPanel | VERIFIED | Unchanged since the first verification (`MOVE_STAT_CATEGORY_ORDER` ends `blunder, facepalm`); MoveStats and AnalysisTagsPanel tests pass in the full vitest run. |
| 2 | D-02 / D-03: Blunder and Facepalm disjoint; facepalm = blunder with `isFacepalmBlunder(score)`; unscored stays Blunder | VERIFIED | `flawMoveCategory` / `isFacepalmBlunder` (`lib/facepalm.ts`: `score != null && toFacepalmPct(score) >= FACEPALM_HIGH_CUTOFF`); moveStatsCounts tests green. |
| 3 | D-04 / D-19: Blunder cell cycles/highlights only ?? plies, Facepalm cell only ??? plies | VERIFIED | Unchanged; LibraryGameCard / AnalysisTagsPanel tests green. UAT 4 browser check: per-side highlighting confirmed. |
| 4 | D-05: mobile compact row Gem, Great, Best, Mistake, Blunder, Facepalm + chevron | VERIFIED | Unchanged; UAT 4 browser check at 390px confirms 6 cells + chevron, no overflow. |
| 5 | D-06: info popover lists Facepalm definition and the blunders+facepalms = Lichess count sentence | VERIFIED | Unchanged; UAT 4 confirms popover text; game 3257944 Lichess 4 = Blunder 3 + Facepalm 1. |
| 6 | D-07: split only on table, chart, Flaws tags (and the "???" board badge / Explain bar); Lichess meaning elsewhere | VERIFIED | `flawMoveCategory` importers unchanged; `explainBar.ts` still sets the facepalm state through `flawMoveCategory(marker) === 'facepalm'`. |
| 7 | D-08: Flaws row Facepalm, Blunder, Mistake (singular, OR, ??? icon); backend table | VERIFIED | `SEVERITY_BUTTONS` order facepalm, blunder, mistake in `FlawFilterControl.tsx`. Pill style now solid per 260-G1 (truth 33). Backend `_severity_clause` and `TestFlawSeverityTags` unchanged and verified earlier. |
| 8 | D-08 "nothing or all three" is no narrowing on backend and frontend | VERIFIED | Unchanged (`is_full_severity_selection`, `isSeverityNarrowed`). UAT 4: all three = none = 16829 flaws. |
| 9 | D-09: Blunder tag = blunders below the cut or unscored | VERIFIED | Backend unchanged. UAT 4: facepalm 3038 + blunder 6942 = 9980 (blunder+facepalm). |
| 10 | D-10: Facepalm Score range filter removed from UI | VERIFIED | Repo-wide grep (non-test) for `FacepalmFilter`, `facepalmMin/Max`, `SEV_FACEPALM_BG`, `FacepalmChip`, `FacepalmMoveChip`, `FACEPALM_TYPE_STYLE`, `FacepalmTooltipLine`, `filter-best-moves-divider`, `facepalm-move-popover` returns nothing. |
| 11 | D-11 (superseded by 260-G2): facepalm score stays visible | VERIFIED (new target) | Score is on: the Flaws card chip popover (`FacepalmBadgePopover` + `FacepalmExplanation`), the analysis glyph popover, the tooltip verdict line (`toFacepalmPct` in `FlawTooltipVerdict`), the footer line (`facepalmPct`). Not on the chip face, as the gap requires. |
| 12 | D-12: severity filter accepts `facepalm`; 422 for unknown; no migration | VERIFIED | Backend unchanged; UAT 4: unknown severity 422. |
| 13 | D-13: range parameters and helpers removed through router, service, repo, `query_utils` | VERIFIED | Unchanged; UAT 4: old `min_facepalm_pct` param ignored (200). |
| 14 | D-14: frontend store, query params, `lib/facepalm.ts` range helpers removed; stale persisted fields load cleanly | VERIFIED | `lib/facepalm.ts` now holds only the cut, `toFacepalmPct`, `isFacepalmBlunder`, copy, `FACEPALM_TYPE_LABEL`/`SENTENCE`, `facepalmScoreLabel`. |
| 15 | D-15 / D-16: miniboard grows with the 8-row table, chart and lane follow; mobile untouched | VERIFIED | UAT 1 (headless Chrome, 20 cards at 1440px): board 248, move quality card bottom delta 0px on all 20. |
| 16 | D-17: facepalm dot dark red `SEV_FACEPALM`, both sides, all states | VERIFIED | `flawMarkerColor(marker)` drives the dot renderer (EvalChart l.442); UAT 2: dots oklch(0.42 0.17 25) vs blunder oklch(0.58 0.19 25) in normal, highlighted, dimmed. |
| 17 | D-18 / D-26 (label colour superseded by 260-G1): tooltip shows the ??? icon, reads "You / Opponent . Facepalm" | VERIFIED (new target) | `FlawTooltipVerdict` renders `FacepalmBlunderIcon` and "{You\|Opponent} · Facepalm N%"; icon carries the colour, label is `text-foreground`. |
| 18 | D-20: filter ring marks each selected tag's user cell; none/all three no ring | VERIFIED | Unchanged logic; UAT 3 (browser): desktop table and mobile compact row. |
| 19 | D-21: cut never changed or stated as a literal in new code, copy, tests | VERIFIED | `FACEPALM_HIGH_CUTOFF` unchanged; gap-closure tests derive scores from the constant and percents from `toFacepalmPct` (FlawCard test uses `ABOVE_CUT_SCORE` / `BELOW_CUT_SCORE` and `toFacepalmPct`). The two stale "70%" explanatory comments are unchanged info items. |
| 20 | D-22: final visual UAT after the 259-12 switch release | VERIFIED | 259-12 to 259-15 are on this branch; UAT tests 1 to 5 in `260-UAT.md` (headless Chrome 158 at 1440px and 390px, plus the gap-closure check) cover Games, Flaws tab and /analysis. Gaps found there are the closed G1 to G3. |
| 21 | D-23: D-12 early, D-13 last after 259 | VERIFIED | Unchanged. |
| 22 | D-24: opponent blunders carry their facepalm score; Flaws filter and drill stay user-only | VERIFIED | Backend unchanged. UAT 2 shows opponent facepalm dots (hollow squares) and tooltips with scores. |
| 23 | D-25: desktop eval chart takes the extra board height | VERIFIED | UAT 1: chart area 127px, slider 20px, tags card 93px (identical to main). Info: see geometry note below. |
| 24 | D-27: SeverityBadge ring follows the badge's own tag (Facepalm for ???) | VERIFIED | `ownFilterTag` + `isSeverityNarrowed` in `SeverityBadge.tsx`; ring colour is `palette.ring` = `SEV_FACEPALM` for the facepalm badge; UAT 3: Flaws card badges ring under facepalm, blunder, blunder+facepalm, facepalm+mistake and not under none / all three. |
| 25 | D-28: has gem / has great tags ring their user cells; no ring in AnalysisTagsPanel | VERIFIED | Unchanged; UAT 3 (mobile Gem/Great, /analysis no ring). |
| 26 | Discretion: analytics `facepalm` target removed, `severity` gains `facepalm`; CHANGELOG bullets | VERIFIED | CHANGELOG [Unreleased] now also carries the one-chip bullet (l.43) and the tooltip / solid-tag bullet (l.44), no "pawn" wording. |
| 27 | Plan 05: URL `?severity=` values outside the three tags dropped; Flaws default all three | VERIFIED | Unchanged. |
| 28 | Review fixes WR-01, WR-02, IN-02, IN-03, IN-05, IN-06 hold | VERIFIED | IN-05 note: `SEV_FACEPALM_BG` is gone, `FACEPALM_OKLCH` is still the single source for `FACEPALM_BAND_FILL`, `FACEPALM_BAND_SWATCH`, `SEV_FACEPALM`; `SEV_FACEPALM_ON` is a fixed near-white. Backend fixes unchanged. |
| 29 | 260-G2 Flaws card: ONE severity chip ("??? Facepalm" / "?? Blunder"), no score on its face, no separate score chip | VERIFIED | `FlawCard.tsx` `tagsRow` renders only `<FlawSeverityChip flaw={flaw} />` before the tactic chips; `FacepalmChip.tsx` deleted; `SeverityBadge` label is "Facepalm" for `facepalm && severity==='blunder'`, else "Blunder"; `showCount={false}` so no number. UAT gap-closure check: one chip per card, no percent on any face. FlawCard test "One severity chip and the facepalm popover (260-G2)" passes. |
| 30 | 260-G2: that chip is the facepalm popover trigger for every scored blunder (score and type), none for unscored blunders and mistakes; testid `facepalm-badge-{gameId}-{ply}`; accessible names "Facepalm N%, type" / "Blunder, facepalm score N%, type" | VERIFIED | `FlawSeverityChip`: `scored = severity==='blunder' && score != null && type != null` wraps the badge in `FacepalmBadgePopover testId={`facepalm-badge-${game_id}-${ply}`}`; trigger `aria-label={facepalmScoreLabel(score, type)}`, which branches on `isFacepalmBlunder`. FlawCard tests assert zero `facepalm-badge-*` triggers for unscored blunders and mistakes; facepalm.test.ts covers both label shapes. Browser: aria names "Facepalm 95%, allowed loss" and "Blunder, facepalm score 52%, allowed loss". |
| 31 | 260-G2 analysis move list: blunder = `??`/`???` icon plus tactic chip; score chip gone on desktop and mobile list; icon opens the popover on every scored blunder; tap does not navigate; unscored blunder keeps a plain `??`, a score without a type never shows `???` | VERIFIED | `MoveListMarker` returns `FacepalmGlyphBadge` alone for severity blunder with `facepalmScore` and `facepalmType`; `FacepalmGlyphBadge` picks the icon via `isFacepalmBlunder` and wraps `InfoPopover` in a span stopping click/pointerdown; `severityIcon` requires the type for `???`. `MoveListMarker` is used by the desktop rows, sideline blocks and the mobile `trailing` slot (VariationTree l.687, 691, 773, 948). `FacepalmMoveChip.tsx` deleted, no residual reference. Browser: 8 glyph triggers, 0 percent chips, tap on `???` opens the popover without navigating. VariationTree tests (10b, 10c) pass. |
| 32 | 260-G2 footer line names a facepalm's score ("Qf6+ ???: Facepalm 76% · missed checkmate in 7"), ordinary blunder line unchanged | VERIFIED | `explainHeadline` sets `facepalmPct: toFacepalmPct(score)` only when `flawMoveCategory === 'facepalm'`; `Headline` renders `Facepalm {pct}%` (testid `analysis-explain-facepalm`, `text-foreground`), then a middle dot before tactics; shared by the explain and got-it states. explainBar and ExplainBar tests pass. Browser: "c4 ???: Facepalm 95% · allowed hanging-piece in 1" with Best and Punish present. |
| 33 | 260-G1 pill: selected Facepalm tag and Facepalm chip are a solid `SEV_FACEPALM` fill with `SEV_FACEPALM_ON` label; Blunder and Mistake keep tinted style; the light colour lives in `theme.ts`; D-27 ring still rings, now in `SEV_FACEPALM` | VERIFIED | `SEVERITY_BUTTONS[0]`: `color: SEV_FACEPALM, bg: SEV_FACEPALM, selectedText: SEV_FACEPALM_ON`, applied as `color: selectedText ?? color`; `SeverityBadge.badgePalette(...)` returns foreground `SEV_FACEPALM_ON`, background and border `SEV_FACEPALM` for the facepalm chip; `export const SEV_FACEPALM_ON = 'oklch(0.985 0 0)'` in `theme.ts`; no colour literal in either component. Browser: pill and badge solid oklch(0.42 0.17 25) with label oklch(0.985 0 0). |
| 34 | 260-G1 tooltip: one verdict line "??? You · Facepalm 95%" / "?? You · Blunder 12%" for every scored blunder; missed win / allowed loss text only without a tactic row; colour on icons only, neutral labels; box 85% opaque (owner follow-up 2026-11-22: opacity lowered from 95%; a separate score line was tried in 54a8616ca and reverted on the owner's call), no blur; text and icons one step larger | VERIFIED | `FlawTooltipVerdict`: icon by category (`FacepalmBlunderIcon` / `BlunderIcon` / `MarkerGlyph`), label in `text-foreground`, `scoreText` for any blunder with a score. `FlawTooltipDetail`: type line `eval-chart-tooltip-facepalm-type` only when `tactics.length === 0`; tactic rows keep orientation colour on the icon only, labels `text-foreground`. `ChartTooltipBox className="bg-background/85 text-sm whitespace-nowrap"`; `TOOLTIP_ICON_CLASS = 'h-3.5 w-3.5'` (14px); no `backdrop-blur` in EvalChart. EvalChart tests pass (FlawTooltipVerdict, FlawTooltipDetail). Browser, four cases confirmed, label oklch(0.985 0 0), 14px. |
| 35 | 260-G3: divider sits below Flaws, above Tactic Depth, only when the tactic section renders; old divider after Best Moves is gone; Context section border not doubled | VERIFIED | `FlawFilterControl.tsx`: `{showTactics && <div className="border-t border-border/40" data-testid="filter-tactics-divider" />}` directly after the Flaws block; `filter-best-moves-divider` appears nowhere; Context keeps its own `pt-3 border-t`. FlawFilterControl tests assert exactly one divider with tactics, none without (l.751-781). Browser (Flaws tab): one divider between Flaws and Tactic Depth. |

**Score:** 35/35 truths verified (0 behavior-unverified).

### Required Artifacts (gap-closure)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `components/library/SeverityBadge.tsx` | Facepalm label, solid palette (`SEV_FACEPALM_ON`) | VERIFIED | Present, substantive, used by FlawCard and TrainPuzzleCard (no `facepalm`, ring off). |
| `components/library/FlawCard.tsx` | one chip wrapped in `FacepalmBadgePopover` | VERIFIED | `FlawSeverityChip` module-level, rendered once in `tagsRow` (shared by mobile and desktop bodies). |
| `lib/facepalm.ts` | `facepalmScoreLabel`, type tint removed | VERIFIED | Exported and used by `FacepalmBadgePopover` and `FacepalmGlyphBadge`. |
| `lib/theme.ts` | `SEV_FACEPALM_ON` | VERIFIED | Present; `SEV_FACEPALM_BG` removed. |
| `components/filters/FlawFilterControl.tsx` | solid tag, `filter-tactics-divider` | VERIFIED | As truths 33, 35. |
| `components/analysis/FacepalmGlyphBadge.tsx` | `??`/`???` glyph popover | VERIFIED | New file, imported by VariationTree. |
| `lib/explainBar.ts`, `components/analysis/ExplainBar.tsx` | `facepalmPct` and headline text | VERIFIED | Wired as truth 32. |
| `components/library/EvalChart.tsx` | `FlawTooltipDetail`, neutral near-opaque tooltip | VERIFIED | Wired into the tooltip JSX (l.1277). |
| `CHANGELOG.md` | gap-closure bullets | VERIFIED | l.43, l.44 under [Unreleased]. |
| Deleted: `FacepalmChip.tsx`, `FacepalmMoveChip.tsx` | no residual readers | VERIFIED | No import or identifier remains outside negative test assertions. |

### Key Link Verification (gap-closure)

| From | To | Via | Status |
|---|---|---|---|
| `FlawCard.FlawSeverityChip` | `FacepalmBadgePopover` | wraps the badge for scored blunders | WIRED |
| `FacepalmBadgePopover`, `FacepalmGlyphBadge` | `facepalmScoreLabel` | trigger aria-label | WIRED |
| `FlawFilterControl` | `theme.SEV_FACEPALM_ON` | `selectedText` | WIRED |
| `VariationTree.MoveListMarker` | `FacepalmGlyphBadge` | scored blunder with type | WIRED |
| `ExplainBar.Headline` | `explainHeadline().facepalmPct` | `headline.facepalmPct` | WIRED |
| `EvalChart` tooltip | `FlawTooltipDetail` -> `FlawTooltipVerdict` -> `toFacepalmPct` / `FACEPALM_TYPE_LABEL` | direct render | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|---|---|---|---|---|
| Flaws card chip popover | `flaw.facepalm_score`, `facepalm_type` | `/library/flaws` payload, SQL facepalm expression | Yes (UAT: "Facepalm 95%, allowed loss" on real data) | FLOWING |
| Move-list glyph popover, footer line | `FlawMarkerEntry.facepalmScore/Type` via `useAnalysisGemMarkers` from `flaw_markers` | game payload, both sides (D-24) | Yes (UAT: /analysis footer "c4 ???: Facepalm 95%") | FLOWING |
| Chart tooltip verdict | `marker.facepalm_score` | same `flaw_markers` | Yes (UAT: four tooltip cases on game 3257944) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Frontend lint | `npm run lint` (frontend/) | clean | PASS |
| Type check and bundle | `npm run build` | `tsc -b && vite build` OK, PWA generated | PASS |
| Full frontend suite (run once) | `npm test -- --run` | 381 files, 6795 tests passed | PASS |
| Dead code gate | `npm run knip` | no issues (two pre-existing configuration hints only) | PASS |
| Removed-symbol sweep | `/usr/bin/grep -rn` for the removed components, constants and testids in non-test files | no hits | PASS |
| Debt markers in gap-closure files | grep `TBD\|FIXME\|XXX` | none | PASS |

Backend pytest not run: the worktree has no DB config. No backend file changed since the previous verification (`git diff 3b05ba0f0..HEAD -- app tests` empty).

### Probe Execution

SKIPPED: no probes declared by the phase.

### Requirements Coverage

No REQUIREMENTS.md for this phase. Decisions D-01 to D-28 plus gap items 260-G1 to 260-G3 are accounted for in truths 1 to 35 (plan 08 requirements D-08, D-11, D-27 map to truths 29 to 33, 35 and 24; plan 09 requirements D-11, D-18, D-26 map to truths 31, 32, 34, 17). No orphaned decisions.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|---|---|---|---|
| `frontend/src/lib/gameCardGeometry.ts` | part constants `EVAL_SLIDER_ROW_PX = 16` and `DESKTOP_TAGS_CARD_PX = 97` do not match the measured real layout (20 and 93, UAT 1); the two errors cancel so the derived chart height (127px) and the level board/table bottoms are right | Info | Fragile only if one constant is corrected without the other; plan 09 explicitly told the executor not to touch the file. Fix both together in a later cleanup. |
| `app/services/blunder_check_rules.py` l.67, `frontend/src/lib/facepalm.ts` l.60 | explanatory comments still name "70%" | Info | Pre-existing; revisit only if the cut moves. |

No TODO/FIXME/XXX debt marker in any file modified by the gap-closure plans.

### Human Verification Required

None open. The five human items of the first verification are recorded and resolved in `260-UAT.md` (tests 1 to 5: three passed, two issues, both issues closed by plans 08 and 09 and re-checked in a headless browser). Residual, low-risk surfaces the UAT section lists as not exercised: the Games-tab filter panel and mobile-drawer divider (the same `FlawFilterControl` component the Flaws tab check exercised, unit-pinned), a tap on a `??` glyph and hover-open on the Flaws card chip (the same popover shells as the exercised `???` tap and the unit-tested hover path), the Train card ring (code passes `showActiveFilterRing={false}`), desktop Gem/Great rings, an unanalysed card's geometry, and a real phone. None is a must-have without code or test evidence, so they are noted, not gated.

### Gaps Summary

No gaps. All three UAT gaps are closed in the code, not only in the summaries: one chip/icon per blunder carrying the facepalm popover on both the Flaws card and the analysis move list, the footer line naming a facepalm's score, the chart tooltip as one neutral verdict line with the score for every scored blunder, the solid dark red Facepalm tag and chip with a theme-held light label, and the divider moved below Flaws. The core phase goal (8-category move quality with Facepalm, split Blunder, Flaws filter with three tags, removed range filter, ring behaviour, card geometry) is verified unchanged and re-confirmed by the browser UAT. Lint, build, the full frontend suite and knip are green on this HEAD.

---

_Verified: 2026-11-22T21:20:00Z_
_Verifier: Claude (gsd-verifier)_

## Squash-merge onto main (2026-11-22, orchestrator)

The digest above was recomputed on the squash branch after merging onto `main` (which had gained Phase 261). Merge adaptations: `FacepalmGlyphBadge` passes `audience` to `FacepalmExplanation` (261 renamed `byOpponent`); 261's `FacepalmChip.test.tsx` removed with the component it tested. Full pre-merge gate on the merged tree: ruff format and check, ty (app/tests/scripts and analysis), nesting-depth gate, `pytest -n auto -x` (6965 passed, 8 skipped), frontend lint, build, vitest (381 files, 6821 tests) and knip, all green. No verifier re-run on the merged tree.
