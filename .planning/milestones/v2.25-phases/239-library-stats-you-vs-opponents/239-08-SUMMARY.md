---
phase: 239-library-stats-you-vs-opponents
plan: 08
subsystem: frontend
tags: [react, library-stats, tactic-motifs, gap-bar, accordion, vitest]
requires:
  - phase: 239-03
    provides: "GapBar, GapGateSlot, GapPopover, gapBar math"
  - phase: 239-04
    provides: "per-TC /tactic-comparison payload (38 bullets per TC, per 100 games, low_sample, zone registry)"
  - phase: 239-05
    provides: "LibraryStatsSections container, LibraryTcSwitch, flawStatsFixtures"
  - phase: 239-10
    provides: "You vs. your opponents section, knip-clean meta"
provides:
  - "TacticTables: three tactic tables (Piece Attacks, Checkmate Checks & Discoveries, collapsible Advanced) with Missed | Allowed gap bars per 100 games"
  - "ExpandHint exported from ShellyQuote (one place for the hint string and styling)"
  - "Tactic motifs section on the per-TC API with a synced TC switch, gate slot and LoadError"
  - "tacticBulletToGapCell, indefiniteArticle, tacticSideCopy, tacticTestIdSegment"
  - "Per-TC tactic types (TacticBullet, TacticComparisonTc, TacticComparisonResponse, TacticSide)"
  - "Tactic fixtures in flawStatsFixtures.ts (makeTacticBullet, makeTacticTcEntry, RAPID/BLITZ_TACTIC_ENTRY)"
affects: []
tech-stack:
  added: []
  patterns:
    - "Section data fetched inside the section component; selected TC is a client-side pick over one per-TC payload and never enters a query key"
    - "Collapsed-by-default band accordion: Accordion value controlled by useTrackedOpen({ once: true }), ExpandHint inside AccordionTrigger band"
key-files:
  created:
    - frontend/src/components/library/stats/TacticTables.tsx
    - frontend/src/components/library/stats/__tests__/TacticTables.test.tsx
  modified:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/lib/tacticComparisonMeta.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/components/insights/ShellyQuote.tsx
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
key-decisions:
  - "The Tactic motifs switch is fed by the tactic payload's own tcs list (same TC set as the flaw comparison under the same filters) so the section is self-contained and its switch never offers a TC the tactic payload lacks"
  - "A zero-flaw cell renders its own muted 'No flaws' (GapBar's 'No flaws yet' copy stays for other callers) and is not faded, since it is already muted"
  - "TacticFamily stays defined in tacticComparisonMeta.ts; types/library.ts imports it type-only (no runtime cycle)"
requirements-completed: [D-00a, D-00c, D-00d, D-00h, D-00i, D-00j, D-02, D-03, D-09, D-11, D-12]
duration: ~50min
completed: 2026-10-13
status: complete
actuals:
  tokens: 36000
  tasks: 2
  commits: 2
plan_head_before: 59bbd34b3c8fffb9e522c675a5b1dcecc59d0478
plan_head_after: ec8c2228baf50e698302eed1e68ca417cc0a5f6e
---

# Phase 239 Plan 08: Tactic motifs tables per time control Summary

**The Tactic motifs section now renders three tactic tables from the per-TC, per-100-games API in fixed group and family order, each cell a Missed or Allowed gap bar with a Search popover, Advanced collapsed behind the shared "Click or tap for details" hint, zero-flaw motifs listed under their table, and phones stacked; the old top-6 grid, its More tactics accordion and its helpers are gone.**

## What was built

- **Task 1 (tracer, 6945c8744)**
  - `types/library.ts`: `TacticSide`, reshaped `TacticBullet` (`family: TacticFamily`, `low_sample`, per-100-games comments), `TacticComparisonTc`, `TacticComparisonResponse { tcs, analyzed_gate }`.
  - `useTacticComparison(filters, flawFilter)` drops the tactic-family argument and key dimension (key `['library-tactic-comparison', params]`); the backend `tactic_families` parameter stays unused from here.
  - `tacticComparisonMeta.ts`: `tacticBulletToGapCell`, `indefiniteArticle` ("an" before a vowel letter or "x-"), `tacticSideCopy` (label "Missed fork", definition "Your opponent left a fork on the board and you did not play it." / "Your move handed your opponent a fork.", noun "flaws with a missed/an allowed fork"), `tacticTestIdSegment`.
  - `TacticTables`: one card per `TACTIC_GROUPS` entry, families in `TACTIC_COMPARISON_FAMILIES` order (never re-sorted), `md:grid-cols-[24%_38%_38%]`, Motif cell with "N of your flaws" (missed plus allowed, your side), `GapBar` plus `GapPopover` (`gap-popover-tactic-{family-kebab}-{side}-tc-{tc}`, unit "per 100 games").
  - `LibraryStatsSections`: `TacticMotifsSection` (h2 `font-brand`, `LibraryTcSwitch sectionId="library-tactics"`, sketch intro sentence, skeleton / `LoadError("tactic comparison")` / `GapGateSlot` / `TacticTables`). Deleted `TacticComparisonGrid.tsx` and its test.
- **Task 2 (ec8c2228b)**
  - `ExpandHint` exported from `ShellyQuote.tsx` and used by `ShellyQuote` and the Advanced header: the string and its `text-xs` styling exist once.
  - Advanced: `Accordion type="single" collapsible` with `value` controlled by `useTrackedOpen(..., { once: true })` firing `trackFeature('panel-open', { target: 'tactic-advanced' })`; the other two groups are plain `CardHeader` cards. testIds `tactic-group-{key}`, `tactic-group-advanced-trigger`.
  - "No flaws yet: X-ray, En passant." under each table; per-cell muted "No flaws" with no popover; low-sample cells use `UNRELIABLE_OPACITY`; phone side labels (`md:hidden`) with the header row `hidden md:grid`; footer line once.
  - `analytics.ts`: `tactic-advanced` added, `tactic-grid-more` removed (`tactic-motifs-more` kept). `tacticComparisonMeta.ts`: removed `isTacticDeltaSignificant`, `tacticDeltaZoneColor`, the `ZONE_*` imports and the unused `TacticBullet` re-export.

## Verification

- `npm test -- --run`: 329 files, 5578 tests pass. Targeted `src/components/library/stats src/components/insights`: 12 files, 176 tests pass.
- `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm run knip` clean (only the two pre-existing configuration hints).
- Both gap-bar paths are tested from API-shaped payloads: banded (`has_zone` true, fork missed) and band-less (`has_zone` false, every other cell), so the result does not depend on which zones plan 239-07 writes into the backend registry.
- Acceptance greps: `TacticComparisonGrid.tsx` absent; `tacticFamilies` absent from `useLibrary.ts`; `Click or tap for details` appears once in `ShellyQuote.tsx` and not in `components/library` (non-test); `tactic-advanced` 1, `tactic-grid-more` 0 in `analytics.ts`.

### Mutation checks (each failed the matching tests, then reverted)

| Mutation | Tests that failed |
|----------|-------------------|
| Sort the shown rows by your flaw count (`TacticGroupTable`) | "lists the Piece Attacks families in the filter panel order", "never lets the payload order decide the row order", "does not re-sort the rows by rate" |
| Advanced accordion `value={group.key}` (open by default) | "starts collapsed with a chevron trigger and the shared hint", "sends exactly one panel-open event per mount" |

## Deviations from Plan

None needing a deviation rule. Scope notes:

- **Switch TC list.** The plan says to feed the switch with "the flaw-comparison TC list the other sections use"; the section uses the tactic payload's own `tcs` instead (identical TC set under the same filters, and it keeps the section independent of the flaw query). The selected TC still comes from the one shared `library_stats_tc` store, so all three switches stay in sync (tested in both directions, no extra request).
- **Cell testIds.** The cell wrapper is `tactic-cell-{family-kebab}-{side}`; the bar is `...-bar` (words `...-bar-words`, band `...-bar-band`, dot `...-bar-dot`); the empty cell is `...-empty`.
- **Fixtures** (`flawStatsFixtures.ts`, not in `files_modified`) gained the tactic builders, reusable by later plans.
- **LibraryStatsSections test** edits: the "still mounts the existing tactic grid" test and its stub were removed; the empty-payload test now expects the empty copy in three sections.

## Auth gates

None.

## Known Stubs

None.

## Threat Flags

None. T-239-16 mitigated: `tactic-advanced` is a registered literal `PANEL_TARGETS` entry; popover testIds are built from family keys, the side and the TC segment only (`popoverTargetFromTestId` strips the TC). Values render as React text only.

## Deleted files

- `frontend/src/components/library/TacticComparisonGrid.tsx`
- `frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx`

## Self-Check: PASSED

- FOUND: `frontend/src/components/library/stats/TacticTables.tsx`, `frontend/src/components/library/stats/__tests__/TacticTables.test.tsx`
- MISSING (intended): `TacticComparisonGrid.tsx` and its test
- FOUND commits 6945c8744 and ec8c2228b (ancestors of HEAD)
