---
status: resolved
phase: 99-percentile-badges-for-conversion-parity-and-recovery
source: [99-VERIFICATION.md]
started: 2026-05-31
updated: 2026-05-31
---

## Current Test

[complete — both items signed off, see UAT Sign-off below]

## Tests

### 1. Desktop rate chip visual rendering
expected: On the per-TC Conversion/Parity/Recovery cards (desktop, ≥1024px), a title-line percentile chip renders right-aligned for users above the inclusion floor. The existing ΔES-gap chip coexists without displacement — two distinct chips per metric block, with different tooltip copy (rate chip says "Conversion Rate"/"Parity Rate"/"Recovery Rate"; gap chip unchanged). Below floor or with no anchor, no rate chip renders.
result: PASS

### 2. Mobile rate chip parity
expected: On a mobile viewport (<1024px), the same rate chips render with correct alignment (the MetricBlock is a single shared renderer, so desktop and mobile share the code path — this is a visual-alignment confirmation, not a behavioral one).
result: PASS

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

## UAT Sign-off — 2026-05-31

Both human UAT items were manually verified by Adrian and **PASS**:

- [x] **UAT-1** — Each per-TC Conversion / Parity / Recovery card shows the title-line rate chip, right-aligned and distinct from the ΔES-gap chip on the ScoreGapRow; classical suppresses when the cohort is below the inclusion floor. **PASS**
- [x] **UAT-2** — On a narrow mobile viewport (<1024px) the rate chips still render on the per-TC cards and do not displace the ΔES-gap chips. **PASS**

**Status: COMPLETE** — phase verification updated to `passed`.
