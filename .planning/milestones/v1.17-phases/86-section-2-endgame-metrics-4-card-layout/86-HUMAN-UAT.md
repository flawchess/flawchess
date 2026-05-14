---
status: partial
phase: 86-section-2-endgame-metrics-4-card-layout
source: [86-VERIFICATION.md]
started: 2026-05-14T14:39:24Z
updated: 2026-05-14T14:39:24Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Desktop 4-card layout + connector arrows
expected: At ≥1024px width, cards arrange Conv | Parity | Recov on row 1 with Endgame Skill alone in the middle column on row 2; SVG arrows visibly connect each of the 3 top cards to the Skill card (left→right-pointing into Skill's left edge, middle→down-pointing into Skill's top, right→left-pointing into Skill's right edge).
result: [pending]

### 2. Mobile stacking + arrow hiding
expected: At <1024px width, the 4 cards stack single-column in DOM order (Conv → Parity → Recov → Skill); connector arrows are hidden via the mobile-bail check in ConnectorArrows.compute().
result: [pending]

### 3. Per-card MetricStatPopover content (D-16)
expected: Hovering the HelpCircle next to "Diff:" on each Conv/Parity/Recov card opens the per-card explanation + methodology block. Skill card popover renders the composite explanation.
result: [pending]

### 4. Page-level h2 InfoPopover (D-11)
expected: Hovering the HelpCircle next to the "Endgame Metrics and ELO" h2 opens the lifted bucket-taxonomy + mirror-bucket explainer + ELO-uses-same-Skill closing note.
result: [pending]

### 5. Filter responsiveness
expected: Applying a filter (e.g. Opponent Strength: Stronger) updates the You / Opp / Diff values on each card; gauges stay the same (gauge bands are fixed per D-13 / SEC2-04).
result: [pending]

### 6. Legacy removal visual confirmation
expected: The legacy 4-gauge strip and eval-stratified WDL table are gone; only the 4 new cards are visible under the h2.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
