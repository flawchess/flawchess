---
status: partial
phase: 99-percentile-badges-for-conversion-parity-and-recovery
source: [99-VERIFICATION.md]
started: 2026-05-31
updated: 2026-05-31
---

## Current Test

[awaiting human testing]

## Tests

### 1. Desktop rate chip visual rendering
expected: On the per-TC Conversion/Parity/Recovery cards (desktop, ≥1024px), a title-line percentile chip renders right-aligned for users above the inclusion floor. The existing ΔES-gap chip coexists without displacement — two distinct chips per metric block, with different tooltip copy (rate chip says "Conversion Rate"/"Parity Rate"/"Recovery Rate"; gap chip unchanged). Below floor or with no anchor, no rate chip renders.
result: [pending]

### 2. Mobile rate chip parity
expected: On a mobile viewport (<1024px), the same rate chips render with correct alignment (the MetricBlock is a single shared renderer, so desktop and mobile share the code path — this is a visual-alignment confirmation, not a behavioral one).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
