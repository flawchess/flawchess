---
status: partial
phase: 87-section-3-per-type-endgame-type-breakdown-cards
source: [87-VERIFICATION.md]
started: 2026-05-14T00:00:00Z
updated: 2026-05-14T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Desktop 3-col grid layout
expected: At ≥1024px viewport width, the 5 per-type cards arrange as 3 cards on row 1 and 2 cards on row 2 (left-aligned, with the rightmost slot empty). All 5 cards visible with no horizontal overflow. Card order follows the backend-sorted total-desc order delivered in `statsData.categories` (typically Mixed first when filters are broad, but varies per user).
result: [pending]

### 2. Tablet 2-col grid
expected: At 768px-1023px viewport width, the 5 cards arrange as 2-2-1 (rows 1 and 2 carry 2 cards each, row 3 carries the last card in a single column). No horizontal overflow; the per-card content scales naturally.
result: [pending]

### 3. Mobile single-column stack
expected: At <768px viewport width, the 5 cards stack single-column in DOM order. Each card occupies the full content width with no horizontal scroll.
result: [pending]

### 4. CRITICAL: Mobile real-device density check at 375px (per SEC3-05)
expected: On a real iOS or Android device at 375px viewport width (iPhone 12/13 mini, iPhone SE 3rd gen, or equivalent), scroll through the entire section. Each card carries: 2 gauges + WDL bar + Games deep-link + Conv peer bullet + Recov peer bullet. **Decision criteria**: if the per-card content is so tall that vertical scrolling becomes uncomfortable (user must scroll past ~3 screen heights to walk through all 5 cards, or any card alone exceeds one screen height), flip `SHOW_WDL_BAR_IN_TYPE_CARDS = false` in `frontend/src/lib/endgameMetrics.ts`. If the density is acceptable, keep `true`. Document the final decision, the device tested, and the viewport (real device vs DevTools emulation) in the `result:` line below.

**If this test fires the fallback**, the executor must (1) flip the flag in `frontend/src/lib/endgameMetrics.ts`, (2) update the page-level h2 InfoPopover copy in `Endgames.tsx` to mention "Each card shows Conv + Recov gauges and peer bullets only; the per-type WDL bar is omitted on mobile-density grounds — aggregate WDL is available via the Endgame Type filter on the Games tab", (3) re-run `cd frontend && npm test -- --run` to confirm the WDL-flag-gating test (Plan 02 Task 3 Test 3) still passes under the flipped flag, (4) commit the flip in a separate commit citing "Phase 87 D-04: real-device density check fired fallback".
result: [pending]

### 5. `?type=...` URL deep-link hydration
expected: Click the Games icon on the Rook card. URL changes to `/endgames/games?type=rook` and the games tab loads with the type filter pre-set to "Rook". Refresh the page at `/endgames/games?type=rook` and verify the type filter is still pre-set on reload (sharable URL works end-to-end, not just via the in-app `onCategorySelect` callback). Repeat with at least one other class (e.g. Mixed, slug `mixed`) to confirm the slug mapping is correct.
result: [pending]

### 6. Per-card title InfoPopover
expected: Hover (or tap on mobile) the HelpCircle next to each card's class label. The one-sentence type description renders (matches `ENDGAME_TYPE_DESCRIPTIONS` from `lib/endgameMetrics.ts`). Verify all 5 cards have a working title popover: Rook, Minor Piece, Pawn, Queen, Mixed.
result: [pending]

### 7. Per-bullet MetricStatPopover
expected: Hover the HelpCircle inside each peer-bullet row (Conv + Recov on every card, so 10 popovers total across the 5 cards when both opponent samples are above the gate). Each popover renders the locked D-10 content: an explanation (Conv = "your win rate... eval ≥ +1.0... compared to opponents... Filter-responsive."; Recov = "your save rate... eval ≤ −1.0..."), followed by the methodology block ("Score: per-bucket headline rate ... Test: Wald-z ... Confidence interval: 95% normal-approx on the diff."). Confirm the popover also shows the p-value, CI, and confidence level chip.
result: [pending]

### 8. Page-level h2 InfoPopover (D-12)
expected: Hover the HelpCircle next to the "Endgame Type Breakdown" h2. The popover renders 4 framing paragraphs (taxonomy intro, Conv/Recov definitions, gauge-zone explainer, peer-bullet explainer) followed by the 5 per-type one-sentence descriptions (Rook / Minor Piece / Pawn / Queen / Mixed). Pawnless is NOT mentioned (filtered out per HIDDEN_ENDGAME_CLASSES).
result: [pending]

### 9. Empty / sparse class handling
expected: Apply a filter that produces at least one sparse class (`total > 0 && total < 10`) and ideally one empty class (`total == 0`). Verify: the **empty class** card's gauge row renders at `opacity-50` (washed out) with "Not enough data yet" body text; WDL row and peer-bullet rows are suppressed; the card still occupies its grid cell (5-card layout stable). Verify: the **sparse class** card's body wrapper has reduced opacity (UNRELIABLE_OPACITY); an `n=N` chip appears next to the title; gauges, WDL, and peer-bullet rows all still render. Verify: per-metric sparse-opponent fallback — when `opp_conversion_games < 10` or `opp_recovery_games < 10`, that metric's peer-bullet row is replaced with "Conversion — n < 10, baseline unavailable" (or "Recovery — n < 10, baseline unavailable"); the OTHER metric's peer-bullet row still renders if its opp sample is large enough.
result: [pending]

### 10. Filter responsiveness
expected: Apply a filter that changes the cohort (e.g. Opponent Strength: Stronger; Time Control: Blitz; Color: White only). The You / Opp / Diff values on each card update to reflect the new cohort. Verify: gauge values update (since `conversion_pct` / `recovery_pct` reflect the filtered sample); gauge BANDS stay the same (the per-class p25/p75 bands from `PER_CLASS_GAUGE_ZONES` are fixed). Verify: sig-gated diff color paints correctly under the new filter (a previously confident green diff might fade to default if the new cohort's sample is below the gates, or vice versa).
result: [pending]

### 11. Legacy removal visual confirmation
expected: The legacy per-type WDL table (formerly rendered above the section by `EndgameWDLChart`, with row-per-class and columns for Type / Games / Win-Draw-Loss / You / Opp / Diff / You-Opp) is GONE. The legacy gauge-only mini-card strip (formerly rendered below by `EndgameConvRecovChart`, with 5-6 small cards each carrying just two unlabeled gauges) is also GONE. Only the new 5-card grid (`EndgameTypeBreakdownSection`) is visible under the "Endgame Type Breakdown" h2.
result: [pending]

## Summary

total: 11
passed: 0
issues: 0
pending: 11
skipped: 0
blocked: 0

## Gaps
