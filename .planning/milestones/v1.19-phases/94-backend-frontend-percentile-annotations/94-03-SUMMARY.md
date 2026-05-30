---
plan: 94-03
phase: 94
title: Wire PercentileChip into 4 in-scope render sites
status: complete
tasks_complete: 3
tasks_total: 3
---

# Plan 94-03 Summary

Wired the Wave-2 `PercentileChip` into the 4 in-scope ΔES render sites and
extended the existing component tests with chip-present / chip-absent /
recovery-no-chip assertions. Closed the phase via a blocking human-verify
checkpoint at 375px and walked four UAT iterations on chip placement.

## What shipped

- **`EndgameOverallScoreGapRow`** — new optional `chipSlot?: ReactNode` prop.
  The non-hasSlots branch (the 4 wired sites) is now a CSS Grid:
  - Desktop (>=640px): label/value/tooltip in row 1 col 1, chip right-aligned
    in row 1 col 2, bullet chart spanning row 2.
  - Mobile (<640px): label/value/tooltip in row 1, bullet chart in row 2,
    chip left-aligned in row 3 (below the bullet).
  The hasSlots branch (EndgameTypeCard, doesn't pass `chipSlot`) keeps its
  original flex-col layout unchanged.
- **`EndgameOverallPerformanceSection`** — chips on both page-level rows:
  Endgame Score Gap (`skill-isolating` flavor) and Achievable Score Gap
  (`skill-isolating`).
- **`EndgameMetricCard`** — chips on the conv and parity buckets: Conversion
  ΔES (`improvement-focus` flavor) and Parity ΔES (`skill-isolating`).
  Recovery card explicitly excluded per D-12 / PCTL-06.

## Commits

- `68c8a412` feat(94-03): add chipSlot prop to ScoreGapRow
- `3d31559c` feat(94-03): wire PercentileChip into 4 in-scope ScoreGapRow render sites
- `5625bb3c` chore: merge executor worktree (pre-checkpoint) — 94-03
- `647a45a9` fix(94-03): hide flames on mobile and reorder chip after tooltip
- `cbbad66f` fix(94-03): stack percentile chip on its own line on mobile
- `068a505c` fix(94-03): restore mobile flames and move chip above the row
- `0cc4d7a1` fix(94-03): move percentile chip below bullet chart on mobile, left-aligned

(The first two were committed inside the worktree; recovered from
`git fsck --lost-found` after a merge race deleted the worktree branch
before the merge completed.)

## Key files

- `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (new
  `chipSlot` prop; non-hasSlots branch refactored to CSS Grid for per-breakpoint
  chip placement)
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` (2 chip
  call sites)
- `frontend/src/components/charts/EndgameMetricCard.tsx` (2 chip call sites,
  recovery excluded)
- `frontend/src/components/charts/EndgameMetricsSection.tsx` (passes
  `scoreGapPercentile` through to `EndgameMetricCard`)
- `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx`
  (chip-present + chip-absent assertions for both page rows)
- `frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx`
  (chip-present for conv + parity, chip-absent for recovery, flavor routing)

## Verification

- `npx tsc --noEmit` — clean
- `npm run lint` — clean
- `npm run knip` — clean
- `npm test -- --run EndgameOverallPerformanceSection EndgameMetricCard PercentileChip` — 62/62 pass
- `npm test -- --run` (full frontend suite, post-checkpoint state) — pass
- `uv run pytest -x` (backend regression after wave 1) — 1642 pass / 6 skipped

## UAT findings and resolutions

The blocking human-verify checkpoint surfaced 4 mobile-layout iterations.
None of the underlying data, color bands, flame tiers, popover copy, or
null-fallback logic changed — purely placement on small screens.

| # | Finding | Resolution |
|---|---------|------------|
| 1 | Info `(i)` tooltip rendered to the right of the chip, not the score value | Reordered `ScoreGapRow` to render `tooltip` before `chipSlot`; `ml-auto` then floats the chip right of the tooltip on desktop. |
| 2 | At 375px, flames + chip text + value + long label overflowed the row | Initial fix: hid flames on mobile via `hidden sm:inline-flex` on the flame stack span. (Later reverted — see #4.) |
| 3 | After flame-hide, long labels still pushed the chip off-row | Added `flex-wrap` to the row with `basis-full sm:basis-auto` on the chip span so the chip wraps onto its own line on mobile. |
| 4 | Chip-above-row placement felt like a "header" rather than a footnote; flames could fit now that the chip had its own line | Restored mobile flames (`inline-flex`); replaced the wrap-with-`order-first` approach with an explicit CSS Grid layout on `ScoreGapRow`. Chip now lives in row 3 col 1-2 (below bullet, left-aligned) on mobile and row 1 col 2 (right of label, right-aligned) on desktop. Single DOM instance — no breakpoint-conditional duplicate that would break testid queries. |

## Deviations from plan

- **Layout strategy changed during UAT.** The plan called for the chip to sit
  inline at the right edge of the row at all breakpoints. UAT at 375px showed
  this overflowed with long labels even after dropping the flames. Final
  shipped layout uses CSS Grid to relocate the chip below the bullet on mobile
  (left-aligned) while preserving the inline desktop layout. This is a pure
  visual change; the chip's data contract, color bands, flame tiers, popover
  copy, and null-gate behavior are unchanged from the plan.
- **`ScoreGapRow` non-hasSlots branch is now a CSS Grid, not a flex row.**
  The hasSlots branch (EndgameTypeCard) still uses flex-col and is unchanged.
  All test queries still resolve uniquely (chip is rendered once in the DOM).

## Worktree recovery note for the next executor

Mid-checkpoint, the worktree merge for plan 94-03 failed because the main
working tree had an uncommitted copy of executor Task 1's diff to
`EndgameOverallScoreGapRow.tsx` — byte-identical to commit `68c8a412`.
Source of the duplicate diff in main is unclear (possibly an editor's
auto-save reflecting the worktree's edits via a shared file watcher). The
cleanup `git branch -D` ran before the merge succeeded, so the executor
commits became dangling. They were recovered via `git fsck --lost-found`,
re-branched, and merged cleanly. Worth investigating before the next
parallel worktree run if it recurs.
