---
status: passed
phase: 88-time-pressure-stats-rework
source: [88-VERIFICATION.md]
started: 2026-05-17T19:24:35Z
updated: 2026-05-17T20:30:00Z
supersedes: [88-VERIFICATION.md prior pass (2026-05-17T16:50:18Z, plans 88-09..88-12 cycle)]
notes: "UAT executed in-browser across xl/lg/base widths; findings drove post-UAT polish commits 76e6e518 (round 1), 3d512e82 (round 2), 19606970 (round 3), and 7a246e96 (Score Delta popover copy). All tests pass after polish."
---

## Current Test

[complete]

## Tests

### 1. Responsive Time Pressure card grid + A-1 chrome
expected: Render the Endgames page in a real browser at xl (≥1280px), lg (≥1024px), and base (<1024px) widths. Apply various sidebar filter combinations. 4-col (xl) / 2-col (lg) / 1-col (base) grid. Each visible TC card sits in its own charcoal container with clear inter-card spacing. The section heading "Time Pressure" sits directly above the cards with no enclosing chrome (matches the EndgameTypeBreakdownSection convention; A-1 removed the outer wrap).
result: passed (post-polish — copy + layout tweaks landed in 3d512e82 / 19606970)

### 2. Per-card top zone — Clock Gap + 3-stat row (A-3 + WR-04)
expected: On each rendered TC card, the top zone shows 1 Clock Gap bullet, then a 3-stat row reading "My avg time: X% (Ys)", "Opp avg time: X% (Ys)", "Net flag rate: ±X.X%". Net flag rate is green when positive past NEUTRAL_TIMEOUT_THRESHOLD, red when negative past it, neutral inside the band. The InfoPopover trigger next to the net flag rate value is reachable and explains the WDL convention. Em-dash fallback on null averages renders cleanly.
result: passed

### 3. Four quintile bullets with qualitative labels + ±30% axis (A-4 + A-5)
expected: Only 4 quintile bullets render per card, labelled "High Pressure (0-20%)", "Medium Pressure (20-40%)", "Low Pressure (40-60%)", "Very Low Pressure (60-80%)". The 80-100% bin does not appear. The bullet axis extends to ±30% and bullets at the extreme ends of the data range still fit without clipping.
result: passed (Score Delta popover copy simplified post-UAT in 7a246e96 — drops "quintile" jargon)

### 4. Restored "Average Clock Difference over Time" line chart (A-2 + WR-01 + WR-02)
expected: Chart visible below the card grid, above the SectionInsightSlot. With a recency filter applied (e.g. last 30 days), hover over the first visible point. The "trailing 100" tooltip count is at or near 100, not 1/2/3 (WR-01 pre-fill works). Y-axis allows values outside ±30% to render above/below the envelope instead of silently clipping (WR-02). Line color is MY_SCORE_COLOR. Per-week volume bars render in the bottom 20% of the canvas. Chart hides cleanly when no clock-eligible games exist.
result: passed

### 5. Mobile parity at 375px
expected: At 375px width, chart caption, tooltip, and axis labels render legibly without horizontal scroll. InfoPopovers on the chart header, net flag rate, and bullets open and close cleanly with tap targets ≥44px. No text below text-sm anywhere. Caption "Are you banking time into the endgame or burning it down?" reads cleanly. Tooltip on the line chart doesn't overflow horizontally.
result: passed

### 6. Screen-reader announcements (chart + WR-04 popover)
expected: VoiceOver / NVDA announces the chart as "Average clock difference over time" (role="img" + aria-label). Net flag rate context is reachable without sighted clues via the new InfoPopover. The card section retains its aria-label="Time pressure analysis" (88-09..88-11 invariant).
result: passed

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None — all post-UAT findings landed in commits 76e6e518, 3d512e82, 19606970, and 7a246e96.
