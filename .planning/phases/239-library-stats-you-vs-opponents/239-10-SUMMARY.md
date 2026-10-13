---
phase: 239-library-stats-you-vs-opponents
plan: 10
subsystem: frontend
tags: [react, library-stats, what-stands-out, context-tags, tc-switch, vitest]
requires:
  - phase: 239-03
    provides: "gapBar math, GapBar/GapGateSlot, GapRow, GapPopover, pickStandouts"
  - phase: 239-05
    provides: "LibraryStatsSections container, LibraryTcSwitch, FLAW_GAP_META, per-TC types, flawStatsFixtures"
provides:
  - "WhatStandsOut: top 3 strengths and weaknesses over the 10 context tags plus a Typical line"
  - "ContextTagCards: Clock, Game phase, Opponent errors, Lost advantages"
  - "CONTEXT_TAG_CARDS, CONTEXT_TAG_METRICS, ContextTagMetric, flawMetricCell, metricTestIdSegment"
  - "You vs. your opponents section with its own synced TC switch and D-03 gate slot"
affects: [239-08]
tech-stack:
  added: []
  patterns:
    - "Second section reads the same TanStack comparison query (one cache entry) and the same TC store: no extra request"
    - "ContextTagMetric = Exclude<FlawDeltaMetric, 'blunder' | 'mistake'> makes D-13 a compile-time property"
key-files:
  created:
    - frontend/src/components/library/stats/WhatStandsOut.tsx
    - frontend/src/components/library/stats/ContextTagCards.tsx
    - frontend/src/components/library/stats/__tests__/WhatStandsOut.test.tsx
    - frontend/src/components/library/stats/__tests__/ContextTagCards.test.tsx
  modified:
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
    - frontend/src/components/icons/SeverityGlyphIcon.tsx
    - frontend/src/pages/library/GamesTab.tsx
key-decisions:
  - "Both sections show 'No analyzed games in the current filters yet.' when no TC has analyzed games (consistent copy; the existing empty-state test now expects two matches)"
  - "The section's comparison LoadError reads 'Failed to load opponent comparison' so it never collides with Flaw Stats' own error text"
  - "No separate legend line under the cards; the axis caption, intro sentence and popovers carry the explanation (plan action steps do not list it)"
requirements-completed: [D-00a, D-00b, D-00c, D-00d, D-00f, D-00g, D-00j, D-02, D-03, D-12, D-13]
duration: ~40min
completed: 2026-10-12
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: b56555c36f378c396827de15116bbd631f36ef36
plan_head_after: 97c3679e188ed7e988969a3d9918924c8347993c
---

# Phase 239 Plan 10: You vs. your opponents section Summary

**The Library Stats tab now shows What stands out (top 3 strengths and weaknesses among the 10 context tags, plus a Typical line) and four context-tag cards per selected time control, on a TC switch synced with Flaw Stats; the legacy comparison-grid metadata and the severity/combo theme constants are gone and knip is clean.**

## What was built

- **Task 1 (tracer, d6e2cb4f9)**
  - `flawComparisonMeta.ts`: `ContextTagCardKey`, `ContextTagMetric` (blunder and mistake excluded by type), `CONTEXT_TAG_CARDS` (Clock, Game phase, Opponent errors, Lost advantages with the sketch subtitles), `CONTEXT_TAG_METRICS` (flattened in card order), `flawMetricCell`, `metricTestIdSegment` (`low_clock` -> `low-clock`).
  - `WhatStandsOut`: Card with Strengths and Weaknesses columns (stacked on phones) fed by `pickStandouts` over the 10 context rows; coloured gap words, hint, GapPopover (`gap-popover-standout-{metric}-tc-{tc}`); empty side reads "Nothing outside the typical range."; "Typical: ..." line in card order, omitted when empty.
  - `ContextTagCards`: four Cards (two columns from lg), CardHeader band with title and muted subtitle, one `GapRow` per tag (`context-row-{metric}`, popover `gap-popover-{metric}-tc-{tc}`, omitted when the row has no gap), axis caption worse / same as opponents / better.
  - `LibraryStatsSections`: new `VsOpponentsSection` between Flaw Stats and Tactic motifs (`vs-opponents-section`, own `LibraryTcSwitch sectionId="library-vs-opponents"`, sketch intro sentence, `GapGateSlot` below the gate). It reuses `useLibraryFlawComparison` (same query key, one cache entry) and the one `library_stats_tc` store, so a click in either switch moves both with no new request.
- **Task 2 (97c3679e1)**: `flawComparisonMeta.ts` lost the family colour map and list, per-tag meta, confidence/significance/zone-colour/p-value helpers and their imports (it keeps `FlawIcon`); `theme.ts` lost `FAM_SEVERITY(_BG)` and `FAM_COMBO(_BG)`; stale comments in `SeverityGlyphIcon.tsx` and `GamesTab.tsx` rewritten. `MiniBulletChart` untouched.

## Verification

- `npm test -- --run src/components/library/stats src/components/filters`: 10 files, 171 tests pass. Full frontend suite: 329 files, 5561 tests pass.
- `npm run lint`, `npm run build` (tsc -b + vite) clean; `npm run knip` exit 0 (only the two pre-existing configuration hints).
- Acceptance greps: `FLAW_COMPARISON_FAMILIES|FLAW_FAMILY_COLORS` 0, `export type FlawIcon` 1, `FAM_SEVERITY|FAM_COMBO` in theme.ts 0, no stale component names in the two comments.
- D-00d: `LibraryStatsSections.test.tsx` asserts the rendered text of the tiles, What stands out, the four cards and the whole section does not match `/\bevents?\b/i`, and the same for the blunder, standout and context popover bodies.
- **Mutation check (D-13, reverted afterwards)**: removed `cell.lowSample` from `effectiveVerdict` in `lib/gapBar.ts` (so `pickStandouts` keeps low-sample rows). "drops a low-sample row from both lists and from the Typical line (D-12, D-13)" failed with `expected <li ...> to be null`; after restoring, all 11 WhatStandsOut tests pass.

## Deviations from Plan

### Auto-fixed Issues

None.

### Scope notes

- **`ContextTagCards` has no `analyzedN` prop.** The plan signature listed `{ tcStats, analyzedN }`, but `tcStats.analyzed_n` already carries it; a second prop would only be able to disagree.
- **`ContextTagCardDef.metrics` is `readonly ContextTagMetric[]`** (plan: `FlawDeltaMetric[]`) so blunder and mistake cannot be passed to the cards or `pickStandouts` at compile time (D-13).
- **Fixtures extended** (`flawStatsFixtures.ts`, not in `files_modified`): `makeTcEntry` takes per-metric `overrides`, and `SKETCH_RAPID_ENTRY` holds the sketch's real rapid gaps and bands. Used by the new tests and reusable by 239-08.
- **Existing tests adjusted** in `LibraryStatsSections.test.tsx`: the h2 list now includes "You vs. your opponents", and the empty-payload test expects the empty copy twice (once per section).
- **Axis caption** ends where the bar track ends via `mr-34` (words column plus popover), a small visual refinement over the sketch's fixed 108px.

## Auth gates

None.

## Known Stubs

None. The Tactic motifs section still mounts the legacy `TacticComparisonGrid` until plan 239-08 (documented in 239-05).

## Threat Flags

None. T-239-18 accepted: all values render as React text, no `dangerouslySetInnerHTML`; popover testIds are built from metric keys and the TC segment only.

## Self-Check: PASSED

- FOUND: WhatStandsOut.tsx, ContextTagCards.tsx, WhatStandsOut.test.tsx, ContextTagCards.test.tsx under `frontend/src/components/library/stats/`
- FOUND commits d6e2cb4f9 and 97c3679e1 (ancestors of HEAD)
