---
status: partial
phase: 68-endgame-score-timeline-dual-line-shaded-gap
source: [68-VERIFICATION.md]
started: 2026-04-24T15:51:01Z
updated: 2026-04-24T15:51:01Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Chart renders correctly at desktop width
expected: Endgames tab, Overall Performance section, card below WDL table shows a chart titled "Endgame vs Non-Endgame Score over Time" with two visible lines (endgame brand blue, non-endgame muted neutral) and a shaded band between them — green where endgame > non-endgame + 1%, red where endgame < non-endgame - 1%, nothing within epsilon. Y-axis 0-100%, X-axis weekly date ticks.
result: [pending]

### 2. Chart renders correctly on mobile (<=400px viewport)
expected: Chart fits 375px viewport with no horizontal page scroll, legend readable, info popover opens without overflow, axis labels and tooltips legible.
result: [pending]

### 3. Info popover content reads cleanly
expected: Clicking the `(i)` icon next to the chart title shows three short paragraphs: factual definition (trailing window + weekly sampling), shading color-coding explanation, sample-quality footnote (n < 10 hidden). No "Score Gap is a comparison, not an absolute measure" caveat anywhere.
result: [pending]

### 4. Tooltip hover behavior
expected: Hovering a weekly point shows week-of date, endgame %, non-endgame %, n= game counts for each side, and a signed gap (e.g. "Gap: +5%"). Color swatches match line colors.
result: [pending]

### 5. First LLM insights run after cache invalidation produces sane narration
expected: Fresh endgame insights report (cache invalidated by `endgame_v13` prompt bump) narrates the endgame/non-endgame score relationship neutrally without defaulting to "weak endgame" when the gap is negative. No mention of "Score Gap Timeline" or "comparison, not an absolute measure" in the narrative.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
