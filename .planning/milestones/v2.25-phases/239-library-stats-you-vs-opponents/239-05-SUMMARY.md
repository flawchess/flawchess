---
phase: 239-library-stats-you-vs-opponents
plan: 05
subsystem: frontend
tags: [react, library-stats, flaw-stats, tc-switch, gap-bar, vitest]
requires:
  - phase: 239-02
    provides: "per-TC /flaw-comparison and /flaw-stats payloads"
  - phase: 239-03
    provides: "GapBar, GapPopover, TcSwitchButtons, useLibraryStatsTc"
provides:
  - "LibraryStatsSections container (Flaw Stats + Tactic motifs) mounted on the Stats tab"
  - "LibraryTcSwitch: section switch bound to the one Library TC store, click-only tracking"
  - "FlawTiles: Blunders and Mistakes tiles with gap bar, Search popover, D-03 gate slot"
  - "FLAW_GAP_META, flawBulletToGapCell, libraryBasisText, librarySectionBasisText"
  - "Per-TC frontend types (FlawDeltaMetric, FlawComparisonTc, FlawTrendTc, reshaped FlawBullet/Response)"
affects: [239-08, 239-10]
tech-stack:
  added: []
  patterns:
    - "TC switch is a client-side pick over one per-TC payload; the selected TC never enters a query key"
    - "Section data is fetched inside the section component so the page function stays under the complexity baseline"
key-files:
  created:
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/LibraryTcSwitch.tsx
    - frontend/src/components/library/stats/FlawTiles.tsx
    - frontend/src/components/library/stats/__tests__/FlawTiles.test.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
  modified:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/pages/GlobalStats.tsx
key-decisions:
  - "Section basis line ('Your 1,841 analyzed rapid games in the current filters.') is a separate export (librarySectionBasisText) from the popover basis ('Based on your ...'), sharing one scope string"
  - "Empty comparison payload: heading and coverage badge stay, switch hidden, line 'No analyzed games in the current filters yet.'"
  - "Timeline has its own loading/error state ('Failed to load flaws timeline') so a timeline failure never hides the tiles"
  - "Removed the TempoTag type (orphaned by deleting TagDistribution) so plan 239-10 has one less knip item"
patterns-established:
  - "Test fixtures for per-TC payloads in components/library/stats/__tests__/flawStatsFixtures.ts (reusable by 239-08/10)"
  - "Query-key invariance test: real hooks + mocked libraryApi, assert call counts stay 1 after a TC click"
requirements-completed: [D-00a, D-00b, D-00c, D-00d, D-00e, D-00j, D-00k, D-01, D-02, D-03, D-04, D-05]
duration: ~30min
completed: 2026-10-12
status: complete
actuals:
  tokens: 11000
  tasks: 1
  commits: 1
plan_head_before: 1b4ce6a6f65bd02bfe4dc4aa83988d87aa889369
plan_head_after: 9d734ac734a255988c9d3218b1dd67fed13bf5b9
---

# Phase 239 Plan 05: Flaw Stats section per time control Summary

**The Library Stats tab now renders Flaw Stats per time control: Blunders and Mistakes tiles with zero-centred gap bars and Search popovers, a per-TC Flaws Timeline, and a TC switch bound to the one remembered `library_stats_tc` store; the old band, comparison grid and bullet popover are gone.**

## What was built

- **Types** (`types/library.ts`): `FlawDeltaMetric`, reshaped `FlawBullet` (no `domain`, adds `low_sample`), `FlawComparisonTc`, `FlawComparisonResponse { tcs, analyzed_gate }`, `FlawTrendTc`, slimmed `FlawStatsResponse { trend_by_tc, trend_window, analyzed_pct, analyzed_n, total_n }`. `SeverityRates`, `TagDistribution` and the orphaned `TempoTag` are deleted.
- **Meta** (`lib/flawComparisonMeta.ts`): `FLAW_GAP_META` (12 metrics; thresholds interpolated from `@/generated/flawThresholds`), `flawBulletToGapCell`, `libraryBasisText`, `librarySectionBasisText`. Legacy grid exports are untouched (plan 239-10 deletes them).
- **Analytics**: `library-stats-tc` option target and `OptionChangeProps` variant.
- **Components**: `LibraryTcSwitch` (skips the already selected TC, tracks only from the click), `FlawTiles` (never faded, `—` for a null rate, `GapGateSlot` below the gate, popover testId `gap-popover-{metric}-tc-{tc}`), `LibraryStatsSections` (Flaw Stats with coverage badge, switch, basis line, tiles, timeline; Tactic motifs section mounting the existing `TacticComparisonGrid` until plan 239-08).
- **Page**: `GlobalStats.tsx` swaps the old Flaw Stats block and `useLibraryFlawStats` call for `<LibraryStatsSections>`; ELO Ratings and Results Breakdown h2s gain `font-brand` (headings only).
- **Deleted**: `FlawStatsPanel`, `FlawStatsBand`, `FlawComparisonGrid` (+ test), `FlawBulletPopover`. `MiniBulletChart` untouched.

## Verification

- `npm test -- --run src/components/library/stats`: 4 files, 49 tests pass (FlawTiles 8, LibraryStatsSections 15 new).
- Full frontend suite: 327 files, 5532 tests pass.
- `npm run build` (tsc -b + vite) and `npm run lint` clean.
- Mutation check (reverted afterwards): put the selected TC into the `['library-flaw-stats', ...]` query key and passed it from the section. The test "re-renders the tiles for the clicked TC, tracks once, and makes no new request" failed with `expected "vi.fn()" to be called 1 times, but got 2 times`; after the revert all 15 pass. (The comparison hook takes no TC parameter, so the mutation was applied to the stats query, which the same test also counts.)
- `npm run knip` was deliberately not a gate. Current output (all for plan 239-10): unused exports `FLAW_FAMILY_COLORS`, `FLAW_COMPARISON_FAMILIES`, `FLAW_COMPARISON_META`, `flawConfidenceLevel`, `isFlawDeltaSignificant`, `flawDeltaZoneColor`, `formatPValue` in `flawComparisonMeta.ts`. The theme.ts severity/combo family aliases are not yet reported because `FLAW_FAMILY_COLORS` still imports them; they go once it is deleted.

## Deviations from Plan

None - plan executed as written, with these small notes:

- **[Scope note] `TempoTag` removed.** Deleting `TagDistribution` orphaned it (knip), so it was removed here rather than left for 239-10.
- **[Scope note] Extra export `librarySectionBasisText`.** The behavior bullet's section line ("Your 1,841 analyzed rapid games in the current filters.") differs from the popover basis ("Based on your ..."), so it gets its own tiny export beside `libraryBasisText`.
- **[Observation] Duplicate heading until 239-08.** The existing `TacticComparisonGrid` renders its own h3 "Tactic Motifs" under the new h2 "Tactic motifs" (per plan). Plan 239-08 replaces the grid and removes the duplicate.

## Auth gates

None.

## Known Stubs

None. The Tactic motifs section deliberately still mounts the legacy grid (documented in the plan; plan 239-08 replaces it).

## Threat Flags

None. T-239-10 mitigated: the event value is typed `TimeControlBucket` and sent only from the click handler (tests assert no tracking on restore, default, or re-click of the selected TC). T-239-11: values render as React text only.

## Self-Check: PASSED

- FOUND: LibraryStatsSections.tsx, LibraryTcSwitch.tsx, FlawTiles.tsx and the three test/fixture files under `frontend/src/components/library/stats/`
- FOUND: deleted `FlawStatsBand.tsx`, `FlawComparisonGrid.tsx`, `FlawBulletPopover.tsx`, `FlawStatsPanel.tsx`
- FOUND commit 9d734ac73 (ancestor of HEAD)
- `library-stats-tc` appears 2 times in `analytics.ts` (target const and union variant); `LibraryStatsSections` and `font-brand` (2) present in `GlobalStats.tsx`
