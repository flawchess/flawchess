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
expected: Bright Endgame ELO line is clearly distinguishable from the dark Actual ELO line within each combo; adjacent combos read as different hues
result: [pending]

### 2. Legend click toggles BOTH lines of a combo
expected: Clicking `endgame-elo-legend-chess_com_blitz` hides both the bright and dark chess.com Blitz lines and greys out the button (aria-pressed=false, line-through)
result: [pending]

### 3. Tooltip shows per-combo endgame + actual + gap + games-in-window
expected: Hovering a point shows a multi-line tooltip: date header, then one block per VISIBLE combo with combo label, Endgame ELO value, Actual ELO value, signed gap, and `(past N games)`
result: [pending]

### 4. Info popover content matches LOCKED UI-SPEC copy verbatim
expected: Opening the popover icon next to 'Endgame ELO Timeline' h3 shows 4 paragraphs — formula explanation, bright/dark convention + gap signal, 100-game window + 10-game threshold + 5-95% clamp, Glicko cross-platform caveat
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

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps
