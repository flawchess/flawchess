---
status: partial
phase: 57-endgame-elo-timeline-chart
source: [57-VERIFICATION.md]
started: 2026-04-18T19:55:00Z
updated: 2026-04-18T19:55:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual hue/contrast of paired bright/dark lines
expected: Bright solid Actual ELO line is clearly distinguishable from the dark dashed Endgame ELO line within each combo; adjacent combos read as different hues. (Phase 57.1: the bright line tracks the user's actual rating directly via asof-join, so it should match the user's real rating curve at each date rather than a rolling mean.)
result: [pending]

### 2. Legend click toggles BOTH lines of a combo
expected: Clicking `endgame-elo-legend-chess_com_blitz` hides both the bright and dark chess.com Blitz lines and greys out the button (aria-pressed=false, line-through)
result: [pending]

### 3. Tooltip shows per-week game count + per-combo endgame + actual + gap
expected: Hovering a point shows a multi-line tooltip with: date header at top, then a "Games this week: N (visible combos)" line summing per_week_endgame_games across currently-visible combos (Phase 57.1 D-11), then one block per visible combo with combo label, Actual ELO value, Endgame ELO value, signed gap, and "(past N games)" sourced from endgame_games_in_window. Toggling a combo off via legend must update the "Games this week" sum.
result: [pending]

### 4. Info popover content matches LOCKED UI-SPEC copy verbatim
expected: Opening the popover icon next to 'Endgame ELO Timeline' h3 shows 4 paragraphs — (1) skill-adjusted rating formula `actual_elo + 400 · log10(skill / (1 - skill))` with the composite explanation, (2) bright Actual ELO + dark dashed Endgame ELO convention plus the 75%/25% skill ⇒ ±190 Elo intuition and the "gap is the signal" framing, (3) trailing-100 window + ≥10-games threshold + 5–95% skill clamp, (4) Glicko-1 vs Glicko-2 cross-platform caveat. The old Phase-57 framing (the two-word phrase starting with "performance" and ending with "rating") must NOT appear anywhere in the popover.
result: [pending]

### 5. Mobile legend wraps to multiple rows without horizontal scroll
expected: On Chrome devtools viewport 375x812 (iPhone-ish), the legend flows across multiple rows via flex-wrap; chart remains readable; no horizontal scrollbar
result: [pending]

### 6. Cold-start empty state keeps info popover visible (Pitfall 4)
expected: With recency set to 'Past week' on a sparse account so no combo qualifies, the card renders the h3 + info popover icon + empty-state copy "Not enough endgame games yet for a timeline." / "Import more games or loosen the recency filter." Info popover icon still opens.
result: [pending]

### 7. Filter responsiveness narrows combos
expected: Changing platform to 'chess.com only' drops lichess combos from legend + chart; changing time control to 'Bullet only' reduces to at most 2 combos
result: [pending]

### 8. Component-level error state renders locked copy
expected: Stopping the backend (kill uvicorn) and reloading /endgames eventually shows "Failed to load Endgame ELO timeline" / "Something went wrong. Please try again in a moment." inside the card (the `endgame-elo-timeline-error` testid container)
result: [pending]

### 9. Volume bars render at chart bottom, scale with visible combos
expected: A muted volume-bar series renders at the bottom ~20% of the chart canvas, one bar per emitted week. Bar fill is muted (e.g. low-opacity gray on the charcoal-texture surface) and reads as "context, not data". Bar height for each week equals the SUM of per_week_endgame_games across currently-visible combos — toggling a combo off via the legend must shrink that week's bar; toggling all combos off renders no bars (or all zero-height). The right Y-axis is fully hidden. Bars do not appear in the legend.
result: [pending]

## Summary

total: 9
passed: 0
issues: 0
pending: 9
skipped: 0
blocked: 0

## Gaps

<!-- Revised in Phase 57.1 (2026-04-18): items 1, 3, 4 superseded inline; new item 9 added for volume-bars verification. See 57.1-CONTEXT.md D-12/D-13/D-14/D-16/D-17 for the source decisions. -->
