---
phase: 258-library-stats-recent-sample-snapshots
plan: 05
subsystem: ui
tags: [library-stats, copy, gap-closure, vitest]
requires:
  - phase: 258-library-stats-recent-sample-snapshots
    provides: quiet-TC message and basis line (258-03)
provides:
  - quiet-TC first sentence carries " in the current filters" under a non-recency sidebar filter
  - quiet-TC hint reworded to "a longer period or a custom range"
affects: [library-stats]
tech-stack:
  added: []
  patterns: [one otherFiltersActive const read by both the basis line and the quiet message]
key-files:
  created: []
  modified:
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/__tests__/flawComparisonMeta.test.ts
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
key-decisions:
  - "Hint stays plain text with no button (258 D-17); it names Recency in general because the five-year preset bounds the offered TCs too"
patterns-established:
  - "libraryNoRecentGamesText reuses samplePlaceText(false, otherFiltersActive) so the qualifier phrase lives in one place"
requirements-completed: [D-13, D-16, D-17]
duration: 10min
completed: 2026-11-21
status: complete
actuals:
  tokens: 4000
  tasks: 2
  commits: 4
plan_head_before: 18fe499d3fb25a6fa43133b82f4bf6bf3e7426d4
plan_head_after: 6b8fdec37a8d61241b7ff5859d3751bd8cdf8ea3
---

# Phase 258 Plan 05: Quiet-TC message gap closure (G-258-3) Summary

The quiet time control message now follows the basis line's filter rule (" in the current filters" when a non-recency sidebar filter is active), and its hint reads "Choose a longer period or a custom range under Recency to include older games." instead of naming the five-year preset.

## Tasks

| Task | Name | Commits |
| ---- | ---- | ------- |
| 1 | Tracer: qualifier from helper through FlawStatsSection | 3320261b6 (RED), 3e0c5e386 (GREEN) |
| 2 | Reword the quiet-TC hint, lint, build | 51dc18b63 (RED), 6b8fdec37 (GREEN) |

## RED runs

Task 1 (2 failed, 70 passed):
- `flawComparisonMeta.test.ts > adds the filter qualifier ...`: Expected "No rapid games in the last 36 months in the current filters." / Received "No rapid games in the last 36 months."
- `LibraryStatsSections.test.tsx > adds "in the current filters" to the quiet message ...`: Expected "No blitz games in the last 36 months in the current filters." / Received "No blitz games in the last 36 months."

Task 2 (3 failed, 69 passed):
- `flawComparisonMeta.test.ts > points at a longer Recency period or a custom range`: Expected "Choose a longer period or a custom range under Recency to include older games." / Received "Choose "5 years" or a custom range under Recency to include older games."
- `LibraryStatsSections.test.tsx > shows the message and the timeline only, ...` (paragraph array, same hint diff)
- `LibraryStatsSections.test.tsx > adds "in the current filters" ...` (extended to both paragraphs, hint diff)

## Mutation run (Task 1, never committed)

With the fix in place, the quiet branch's third argument was changed from `otherFiltersActive` to `false`. Result: 1 failed, 53 passed in LibraryStatsSections.test.tsx; the only failure was the Played as Black test (Expected "No blitz games in the last 36 months in the current filters." / Received "No blitz games in the last 36 months."). The argument was restored and both test files re-ran green (72 passed).

## Verification

- Both test files: 72 passed.
- `npm run lint`: clean. `npm run build` (tsc -b + vite): succeeded.
- Acceptance greps: one `const otherFiltersActive = ...` line, one three-argument call, one `areFiltersEqual(` call, 2 pins of the "in the current filters." sentence, 0 occurrences of `5 years` in flawComparisonMeta.ts, 1 new hint in source and 3 across the two test files.
- CHANGELOG.md untouched (diff against a9a1c8657 is empty).

## Deviations from Plan

None - plan executed exactly as written. (The ledger file for `commits:` was written after the first RED commit rather than before it; it holds the plan base 18fe499d3, so the measured count of 4 is correct. The count excludes this SUMMARY's docs commit.)

## Known Stubs

None.

## Threat Flags

None. The message only reads `filters`, holds no button, adds no request or event (T-258-12 mitigated by the existing zero-button assertion).

## Notes for the orchestrator

Dev-app re-verification of 258-UAT test 3 (not a plan gate): as user 7 with Classic selected, expect "No classical games in the last 36 months." with default filters and "... in the current filters." with Played as Black, each followed by the new hint. The full pre-merge gate has to re-run before the phase squash-merge.

## Self-Check: PASSED

All four modified files exist; commits 3320261b6, 3e0c5e386, 51dc18b63, 6b8fdec37 are ancestors of HEAD.
