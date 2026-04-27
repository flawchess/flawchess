---
status: testing
phase: 71-frontend-stats-subtab-openinginsightsblock
source:
  - .planning/phases/71-frontend-stats-subtab-openinginsightsblock/71-06-PLAN.md
  - .planning/phases/71-frontend-stats-subtab-openinginsightsblock/71-VALIDATION.md
started: 2026-04-27T09:18:10Z
updated: 2026-04-27T09:18:10Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Block placement
expected: |
  Navigate to /openings → Stats subtab. The Opening Insights block
  renders at the TOP of the Stats tab content stream — ABOVE the
  bookmarks white/black sections, the win-rate chart, and the most-
  played openings sections.
awaiting: user response

## Tests

### 1. Block placement
expected: Navigate to /openings → Stats subtab. The Opening Insights block renders at the TOP of the Stats tab content stream, ABOVE bookmarks, win-rate chart, and most-played openings sections.
result: [pending]

### 2. Heading and icons
expected: The block heading reads "Opening Insights" with a Lightbulb icon (gold glow class) on the left and an info popover (info icon) on the right.
result: [pending]

### 3. Info popover content
expected: Clicking the info icon shows the copy "Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%. This block always shows both colors, regardless of the active color filter."
result: [pending]

### 4. Four sections in fixed order
expected: The block renders four sections in this fixed order — White Opening Weaknesses → Black Opening Weaknesses → White Opening Strengths → Black Opening Strengths. Each section header has an icon (AlertTriangle for weakness, Star for strength), a piece-color square swatch (white square or black square), and the section name.
result: [pending]

### 5. Finding card chrome
expected: Each finding card shows a charcoal-textured background, a colored 4px-wide left border, a thumbnail board (~100px on desktop / ~105px on mobile), the opening display_name + ECO code in the header, an ExternalLink icon on the right, and a prose sentence below.
result: [pending]

### 6. Severity colors lock-step
expected: Major weakness (loss_rate ≥ 60%) → dark red border (#9B1C1C). Minor weakness (55% < loss_rate < 60%) → light red border (#E07070). Major strength (win_rate ≥ 60%) → dark green border (#1E6B1E). Minor strength (55% < win_rate < 60%) → light green border (#6BBF59). The percentage text in the prose is shaded the same color as the border.
result: [pending]

### 7. Move-sequence trimming (D-05)
expected: For a finding with 5+ entry plys, the prose starts with "..." and renders the last 2 entry plys + the candidate move. For example, Sicilian Najdorf with entry_san_sequence ["e4","c5","Nf3","d6","d4","cxd4"] and candidate Nxd4 renders as "...3.d4 cxd4 4.Nxd4".
result: [pending]

### 8. Per-section empty state
expected: A section with 0 findings (typically Strengths sections) shows a muted italic line: "No strength findings cleared the threshold under your current filters." (or "No weakness findings cleared..." for weakness sections).
result: [pending]

### 9. Empty-block state
expected: With aggressive filters that yield zero findings (e.g. recency=week, time_control=bullet only), the block shows "No opening findings cleared the threshold under your current filters. Try widening filters (longer recency window, more time controls) or import more games." No four section headers when block is empty.
result: [pending]

### 10. Loading skeleton
expected: Throttle network to Slow 3G in DevTools and refresh. The block shows 4 stacked skeleton sections each with a header bar + 2 card placeholders, all with animate-pulse. No spinner.
result: [pending]

### 11. Error state with retry
expected: Stop the backend (Ctrl+C uvicorn). Refresh the page. The block shows a red error notice "Failed to load opening insights. Something went wrong. Please try again in a moment." plus a "Try again" button (brand-outline variant). Restart the backend, click Try again — the block reloads correctly.
result: [pending]

### 12. Deep-link click navigation
expected: Click any finding card. In order — (1) URL changes to /openings/explorer, (2) active color filter at top of page switches to the finding's color, (3) the Move Explorer board renders the entry FEN exactly, (4) board is flipped (rank 8 at bottom) if finding is for Black, (5) page scrolls to top, (6) the candidate move arrow on the board is RED if weakness or GREEN if strength, in a SHADE matching the card's border-left color exactly (lock-step contract from arrowColor.ts).
result: [pending]

### 13. Filter reactivity
expected: Change a filter (e.g. recency from "year" to "month"). The block re-fetches and the findings list changes (or the empty-block message appears if no findings clear the new filter).
result: [pending]

### 14. Color filter independence (D-02)
expected: Change the global color filter (top of page) to "white" only. The block STILL shows all four sections including Black Weaknesses and Black Strengths — the block ignores the active color filter.
result: [pending]

### 15. Hidden when no games
expected: For a guest/empty user (no imported games), the block does NOT render — gated on mostPlayedData length per D-18.
result: [pending]

### 16. Mobile layout at 375px
expected: Open DevTools and set viewport to 375px width. The block fits with no horizontal scroll. Each card uses the mobile layout (header full-width on top, then board+prose row below). Board thumbnail is ~105px. Card click target is ≥ 44px tall (entire card is clickable). All section headers, swatches, and icons render correctly.
result: [pending]

### 17. No console errors
expected: Open DevTools console — no React warnings, no Sentry errors, no network 4xx/5xx (other than the deliberately-killed-backend test in test 11).
result: [pending]

### 18. Phase 72 regression check (Move Explorer arrows)
expected: After deep-link navigation in test 12, the Move Explorer red/green move arrows still render correctly via the existing nextMoves machinery — no regression in arrow rendering.
result: [pending]

## Summary

total: 18
passed: 0
issues: 0
pending: 18
skipped: 0

## Gaps

[none yet]
