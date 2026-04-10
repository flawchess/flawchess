---
status: partial
phase: 50-mobile-layout-restructuring
source: [50-VERIFICATION.md]
started: 2026-04-10T11:30:00Z
updated: 2026-04-10T11:45:00Z
---

## Current Test

[awaiting human re-verification after gap-closure fixes in commit 4f7f0c6]

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

### 8. GAP-A — Subtab pills render at full drawer-button height
expected: The Moves/Games/Stats tab pills inside the unified control row should visually fill the 44px row height, matching the height of the color toggle, bookmark, and filter icon buttons next to them. No visible vertical shortfall.
result: [pending — fix applied in 4f7f0c6, needs visual confirmation]

### 9. GAP-B — Smaller gap between chessboard and drawer buttons
expected: The vertical gap between the bottom of the chessboard region and the top of the unified control row (drawer buttons) should look tight — approximately 4px instead of the previous 8px.
result: [pending — fix applied in 4f7f0c6, needs visual confirmation]

### 10. GAP-C — Vertical gap between collapse handle and drawer buttons
expected: A small (~4px) breathing gap is visible between the bottom of the unified control row and the top of the collapse handle strip. The handle no longer sits flush against the drawer buttons.
result: [pending — fix applied in 4f7f0c6, needs visual confirmation]

## Summary

total: 10
passed: 0
issues: 3
pending: 10
skipped: 0
blocked: 0

## Gaps

### GAP-A: Subtab pills rendered visibly shorter than drawer buttons
status: resolved
found: 2026-04-10 (human verification)
fix_commit: 4f7f0c6
root_cause: TabsList brand variant applies `p-[3px]` by default, plus TabsTrigger uses `h-[calc(100%-1px)]`. Inside the h-11 (44px) unified row this produced 37px tall tab pills while the neighboring icon buttons were 44px.
fix: Added `!p-0` override to the mobile TabsList className so the brand variant padding is removed for this instance. Tab pills now fill the full 44px row, matching the icon buttons.
test: #8

### GAP-B: Gap between chessboard and drawer buttons too large
status: resolved
found: 2026-04-10 (human verification)
fix_commit: 4f7f0c6
root_cause: `pb-1` on the board flex row plus `mt-1` on the unified control row combined for an 8px vertical gap, which read as excessive whitespace on mobile.
fix: Removed `pb-1` from the board flex row. Final gap is 4px (`mt-1` alone).
test: #9

### GAP-C: No vertical gap between collapse handle and drawer buttons
status: resolved
found: 2026-04-10 (human verification)
fix_commit: 4f7f0c6
root_cause: Collapse handle button abutted the unified control row with only a `border-t` line between them — no breathing room.
fix: Added `mt-1` (4px) to the collapse handle button. The border-t remains but now has a 4px strip of sticky-container background above it, visually separating the handle from the drawer row.
test: #10
