---
quick_id: 261015-qxr
mode: quick
---

# Library Stats coverage line: salience + "still updating" hint

Make the per-TC full-analysis readout at the head of Flaw Stats (`CoverageBasisLine`) more
salient while coverage is incomplete, without adding a new element to the page top.

## Task 1: coverage line states

Files: `frontend/src/components/library/analysisCoverageCopy.tsx`,
`frontend/src/lib/flawComparisonMeta.ts`, `frontend/src/lib/theme.ts`,
`frontend/src/components/library/stats/LibraryStatsSections.tsx`,
`frontend/src/components/EvalCoverageHeader.tsx`, `frontend/src/components/stats/EvalCpuPlaceholder.tsx`

- Named threshold `COVERAGE_UPDATING_THRESHOLD = 0.98` (selected TC's analyzed/total).
- Below threshold:
  - authenticated: append "Stats below update as analysis continues.", amber tint (same tokens
    as the Quick Scan banner), pulsing Cpu icon.
  - guest: append "Only analyzed games are counted." with the same tint, no pulse (guests get
    no background analysis); existing sign-up CTA rule (LOW_COVERAGE_THRESHOLD) unchanged.
- At or above threshold: plain muted line, no pulse. Fully complete reads
  "All N <tc> games in the current filters are analyzed."
- Amber tint tokens move to `theme.ts` (ANALYSIS_PENDING_TINT_CLASS), reused by the Quick Scan
  banner and EvalCpuPlaceholder.
- No separate tactic coverage line (tactic tagging is near-instant).

Verify: `npm test -- --run src/components/library/stats`, `npm run lint`, `npm run build`, `npm run knip`.

## Task 2: tests

File: `frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx`

Cover: complete copy, near-complete (no hint, no pulse), authenticated in-progress hint + pulse,
guest in-progress hint without pulse, guest CTA rule unchanged.
