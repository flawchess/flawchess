---
status: partial
phase: 96-import-readiness-gate
source: [96-VERIFICATION.md]
started: 2026-05-28T19:12:22Z
updated: 2026-05-28T19:12:22Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. First-import route redirect
expected: With no import yet (empty account), navigating directly to `/openings` (or `/overview`) redirects to `/import` with no flash of opening content. Tier 1 not met → app held on import page.
result: [pending]

### 2. Incremental import split (Tier 1 vs Tier 2)
expected: During an active incremental import (account already has games), `/openings` and `/overview` stay usable while `/endgames` renders `EndgamesProcessingState` (not partial endgame data) until Tier 2.
result: [pending]

### 3. Import-page state machine progression
expected: A full import cycle progresses through fetching → importing → Tier 1 "Explore Openings" CTA → "Analyzing endgames (X / Y)" → "Ready. All analysis complete." Copy at each stage matches the tier; no message claims full completion at hot-import `status=completed`.
result: [pending]

### 4. Tier-2 "Explore Endgames" toast fires once
expected: On the Tier-2 false→true transition the sonner action toast fires exactly once (deduped), is suppressed when already on `/endgames`, and its action navigates client-side (with query invalidation) so Endgames unlocks without a full reload.
result: [pending]

### 5. Stockfish progress bar (EvalCoverageHeader) across pages during drain
expected: While the eval drain runs, the amber `EvalCoverageHeader` progress bar is visible on every page (Import, Openings, Overview/GlobalStats) as the global processing signal. Post-Tier-2 Endgames renders normally with no regression.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
