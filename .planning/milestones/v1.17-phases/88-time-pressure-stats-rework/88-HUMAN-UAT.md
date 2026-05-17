---
status: partial
phase: 88-time-pressure-stats-rework
source: [88-VERIFICATION.md]
started: 2026-05-17T16:50:18Z
updated: 2026-05-17T16:50:18Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Responsive Time Pressure card grid
expected: Render the Endgames page in a real browser at xl (≥1280px), lg (≥1024px), and base (<1024px) widths with various sidebar filter combinations (all TCs / bullet-only / classical-only / rated-only). 4-col (xl) / 2-col (lg) / 1-col (base) grid renders. TC cards with total < 20 games are hidden. Each rendered card shows 6 rows (1 Clock Gap + 5 quintiles). Score-delta values now reflect `user_score − opp_score` (D-07), not the prior cohort frame; popover copy reads "vs opponent".
result: [pending]

### 2. Sparse-bin three-state rendering with new gate
expected: For a real user, find a bin where `0 < min(n_user, n_opp) < 5` (dimmed at UNRELIABLE_OPACITY + n=X chip), a bin where n=0 (dash + "no games" empty row), and a confidently-rendered bin (full opacity). Three visually-distinct sparse states. The n-gate is now `min(n_user, n_opp) ≥ MIN_GAMES_PER_PRESSURE_BIN` (changed from the prior single-side gate), so a few previously-rendered bins may drop into the dimmed state — confirm this is acceptable.
result: [pending]

### 3. MetricStatPopover at 375px
expected: MetricStatPopover on a Clock Gap row and a Score-Delta row at 375px width. Popover opens with the new "vs opponent" / "same-game opp-quintile" methodology copy; readable and reachable on mobile; dismisses cleanly.
result: [pending]

### 4. Screen reader announces "Time pressure analysis"
expected: ARIA accessible name on the Time Pressure section is announced as "Time pressure analysis" by a screen reader (VoiceOver / NVDA), not silently degrading to no accessible name (which was the WR-02 state pre-fix).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
