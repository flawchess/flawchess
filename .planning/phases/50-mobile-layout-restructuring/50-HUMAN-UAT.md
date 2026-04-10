---
status: partial
phase: 50-mobile-layout-restructuring
source: [50-VERIFICATION.md]
started: 2026-04-10T11:30:00Z
updated: 2026-04-10T11:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Mobile Openings page at 375px viewport — unified control row visible and tappable
expected: At 375px width, the unified control row shows Moves/Games/Stats tabs, color toggle, bookmark button, and filter button on a single flex line with no horizontal scroll. All three icon buttons are comfortably tappable. Tab labels fit at text-xs without truncation.
result: [pending]

### 2. Mobile Openings board collapse — unified row and collapse handle stay visible
expected: Tap the collapse handle. The board region collapses (grid-rows 1fr -> 0fr animation plays). After collapse, the unified control row (Tabs + color + bookmark + filter) remains visible and tappable, and the collapse handle is still present below it. Tap it again and the board expands back.
result: [pending]

### 3. Mobile Openings visual — sticky wrapper backdrop-blur effect
expected: When scrolling content below the sticky region, the unified row and collapse handle strip show a glassy translucent blur (scroll content faintly visible through). When board is expanded, the blur is mostly visible around padding and the collapse handle. No heavy dropshadow under the sticky region.
result: [pending]

### 4. Endgames mobile sticky row reads as visual sibling of Openings mobile unified row
expected: Navigate from Openings (mobile) to Endgames (mobile). The sticky top row on Endgames has the same 44px height, same translucent blurred surface, same bottom border, same h-11 w-11 filter button footprint as the Openings unified row. Stats/Games tabs fill the row. Pages feel consistent.
result: [pending]

### 5. Mobile collapse handle — 44px tappable strip (touch ergonomics)
expected: The collapse handle is a clearly visible 44px strip below the unified row, with a 20px ChevronDown icon centered. Tapping anywhere in the strip toggles the collapse. The old sliver-sized handle was hard to tap; this one is comfortable.
result: [pending]

### 6. WR-01 from REVIEW.md — InfoPopover sizing in vertical column
expected: The InfoPopover icon inside the vertical board-action column should visually balance against the four 48x48 board control buttons. If it looks noticeably undersized (16x16 HelpCircle inside a bare span), this is a known warning (not a blocker) deferred from REVIEW.md.
result: [pending]

### 7. WR-02 from REVIEW.md — color toggle tooltip action-oriented wording
expected: The color toggle tooltip currently reads "Playing as {color}" (state description) while the sibling buttons use action-oriented "Open bookmarks" / "Open filters". The desktop sidebar button uses "Switch to {other color}". User decides whether this inconsistency is acceptable for Phase 50 or deferred to a follow-up.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
