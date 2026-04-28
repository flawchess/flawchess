---
status: partial
phase: 77-troll-opening-watermark-on-insights-findings
source: [77-VERIFICATION.md]
started: 2026-04-29
updated: 2026-04-29
---

## Current Test

[awaiting human testing]

## Tests

### 1. 375px mobile watermark visual check (D-03 + REVIEW WR-02)
expected: Troll-face watermark visible in bottom-right corner of OpeningFindingCard at ~30% opacity. On 375px mobile, the watermark must NOT visually obscure the Moves/Games link button text/icons.
result: [pending]

### 2. Move Explorer desktop placement + mobile suppression (D-06, D-07)
expected: On desktop, small troll-face icon appears next to qualifying SAN cells (sized like other inline glyphs, fully opaque). On 375px mobile, the icon is hidden via `hidden sm:inline-block`.
result: [pending]

### 3. Click pass-through under real DOM (D-04)
expected: Moves/Games buttons on the OpeningFindingCard remain clickable and navigate correctly even when the watermark visually overlaps them (the `<img>` has `pointer-events: none`).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
