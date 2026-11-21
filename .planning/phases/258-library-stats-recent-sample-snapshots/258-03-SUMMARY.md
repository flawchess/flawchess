---
phase: 258-library-stats-recent-sample-snapshots
plan: 03
subsystem: ui
tags: [react, typescript, library-stats, quiet-tc, basis-line, vitest]

requires:
  - phase: 258-library-stats-recent-sample-snapshots
    provides: windowed flaw comparison payload (total_n, sample_since, cap_reached, history_analyzed_n, window_months) and the basis-line helpers (plan 01); facepalm and tactic windows that omit a quiet TC (plan 02)
provides:
  - isQuietTc, libraryNoRecentGamesText and NO_RECENT_GAMES_HINT
  - quiet-TC branch in Flaw Stats (message plus the full-history timeline) and hidden vs-opponents / tactic sections
  - quiet-aware default TC (pickDefaultLibraryTc)
  - "in the recent sample" popover basis wording and a table test over every basis-line variant
  - Flaws Timeline caption "All games in the current filters"
  - DEFAULT_FILTERS regression guard (D-01, D-08)
affects: [258-04 prod timing, UAT of the quiet state wording]

actuals:
  tokens: 16000
  tasks: 3
  commits: 5

plan_head_before: 9609e039238f0f937ec30c75dd106c9c4ea1bd69
plan_head_after: c0d7a109312aa8e33ed89078bf4ee50fc4ae490b

tech-stack:
  added: []
  patterns:
    - "A quiet TC is recognised by total_n === 0 on the flaw-comparison entry; sections that read a payload without the TC (tactic, facepalm) look it up in the flaw list"
    - "Hooks stay above the quiet early return in the sections"

key-files:
  created:
    - frontend/src/components/filters/__tests__/FilterPanel.defaults.test.ts
  modified:
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/__tests__/flawComparisonMeta.test.ts
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - frontend/src/hooks/useLibraryStatsTc.ts
    - frontend/src/hooks/__tests__/useLibraryStatsTc.test.ts
    - frontend/src/components/library/stats/GapPopover.tsx
    - frontend/src/components/library/stats/__tests__/GapPopover.test.tsx
    - frontend/src/components/library/stats/__tests__/FlawTiles.test.tsx
    - frontend/src/components/library/stats/__tests__/ContextTagCards.test.tsx
    - frontend/src/components/library/stats/__tests__/FacepalmCard.test.tsx
    - frontend/src/components/library/FlawTrendChart.tsx
    - frontend/src/components/library/__tests__/FlawTrendChart.test.tsx

key-decisions:
  - "The quiet message names the real Recency option label '5 years' (the select reads '5 years', not 'Past 5 years'); it is plain text with no button, so nothing touches the shared filter store (D-17)"
  - "Popover basis sentences say 'in the recent sample' because their number is the windowed count"
  - "A remembered quiet TC stays selected; only the un-chosen default avoids a quiet TC"
  - "The timeline caption is a module constant in FlawTrendChart, no prop"

patterns-established:
  - "Plan-level guard test for untouched shared defaults (FilterPanel.defaults.test.ts)"

requirements-completed: [D-01, D-08, D-09, D-12, D-13, D-14, D-15, D-16, D-17]

coverage:
  - id: C1
    description: "A quiet TC stays on the switch, shows the two-sentence message and the full-history timeline, and hides tiles, basis line, vs-opponents and tactic sections including headings"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx#quiet time control"
        status: pass
    human_judgment: false
  - id: C2
    description: "Default TC is never a quiet TC while another TC has recent games; all-quiet ranks by history_analyzed_n; a remembered quiet TC stays selected"
    requirement: "D-15"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useLibraryStatsTc.test.ts"
        status: pass
    human_judgment: false
  - id: C3
    description: "Every basis-line variant (cap, recency, other filters, singular) is pinned; the line renders once inside Flaw Stats; popovers read 'in the recent sample'"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/flawComparisonMeta.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx#basis line wording and placement"
        status: pass
    human_judgment: false
  - id: C4
    description: "Flaws Timeline carries the 'All games in the current filters' caption in both render states"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/FlawTrendChart.test.tsx"
        status: pass
    human_judgment: false
  - id: C5
    description: "DEFAULT_FILTERS.recency, customRange and opponentStrength stay untouched; FilterPanel and the filter store are not edited"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FilterPanel.defaults.test.ts"
        status: pass
    human_judgment: false
  - id: C6
    description: "Wording of the quiet message, the caption placement after the info icon and the wrapped header on narrow screens read well"
    verification: []
    human_judgment: true
    rationale: "Recorded plan assumptions, flagged for UAT"

duration: 15min
completed: 2026-11-21
status: complete
---

# Phase 258 Plan 03: Quiet time control, basis wording and timeline caption Summary

**A time control with games but none in the recent window now shows "No blitz games in the last 36 months." plus a Recency hint above its full-history timeline, the other snapshot sections disappear for it, it is never the default over a TC with recent games, and the Flaws Timeline is captioned "All games in the current filters".**

## Performance

- **Duration:** about 15 min
- **Tasks:** 3 (all TDD: RED commit then GREEN commit for tasks 1 and 3; task 2 test and wording together)
- **Files:** 14 (1 created, 13 modified); frontend only

## Accomplishments

- `isQuietTc` (true only for `total_n === 0`; false for the tactic payload shape without `total_n`), `libraryNoRecentGamesText`, `NO_RECENT_GAMES_HINT` in `flawComparisonMeta.ts`.
- `FlawStatsSection` quiet branch (`flaw-stats-no-recent`, two `<p>`, no button) followed by the timeline; `VsOpponentsSection` and `TacticMotifsSection` return null for a quiet TC (the tactic section looks the TC up in the flaw list because the tactic payload omits it). The switch still reads the flaw-comparison list, so the quiet TC keeps its slot.
- `pickDefaultLibraryTc`: non-quiet TCs first (gate rule unchanged), all-quiet falls back to `history_analyzed_n`; `LibraryTcCount` gained optional `total_n` and `history_analyzed_n`. The store is unchanged, so a remembered quiet TC stays.
- `scopeText` now reads "in the recent sample" (popover basis); tests of FlawTiles, ContextTagCards, FacepalmCard and GapPopover follow. A nine-row table test pins every cap / recency / filter variant; suffix-wiring tests and the rendered-once test (D-12) added.
- `FlawTrendChart`: `TIMELINE_CAPTION` constant, `flaw-trend-caption` span after the info icon, header `flex-wrap`. Popover text untouched (D-09).
- `FilterPanel.defaults.test.ts` guards D-01 and D-08; `FilterPanel.tsx` and the filter store are byte-identical to the plan base (`git diff --quiet` exit 0).

## TDD Gate Compliance

- **Task 1 RED** (`19d1d88bc`): 8 tests failed (missing `isQuietTc` / copy exports, no quiet branch, picker ranked a quiet TC). **GREEN** (`713fd4f24`): 87 tests pass, lint and build clean.
- **Task 2:** the popover wording change was a one-string edit with its updated tests in one commit (`14c60c435`); the table test pins `librarySampleBasisText`, which needed no change (the nine-case table matched plan 01's function).
- **Task 3 RED** (`dd8a8076f`): the two caption tests failed on the missing testid; the defaults test passed on first run by design (a guard over untouched code). **GREEN** (`c0d7a1093`).
- REFACTOR: none needed. `gsd_run check tdd-red-evidence` was not run (vitest output is not a supported format).

## Task Commits

1. Task 1 RED: `19d1d88bc` test(258-03): add failing tests for the quiet time control state and default TC
2. Task 1 GREEN: `713fd4f24` feat(258-03): show one message and the timeline for a time control without recent games
3. Task 2: `14c60c435` feat(258-03): pin the basis line variants and name the recent sample in the card popovers
4. Task 3 RED: `dd8a8076f` test(258-03): add the timeline caption tests and the default-filter regression guard
5. Task 3 GREEN: `c0d7a1093` feat(258-03): caption the Flaws Timeline as covering all games

## Deviations from Plan

None - plan executed exactly as written. (The only addition beyond the plan list: a `ignores sampleSince under the cap` unit case, which the behavior section names.)

## Known Stubs

None.

## Threat Flags

None. T-258-08 holds: `flaw-stats-no-recent` and `flaw-trend-caption` are static, non-interactive and not InfoPopover testIds.

## Flagged for UAT

- Quiet message wording ("5 years" as the option label) and the caption position after the info icon.
- Facepalm tile for a TC the switch offers with unanalyzed window games (plan 02 note) still reads zero-event rows.

## Verification

`npm run lint`, `npm run build` (tsc -b), `npm run knip` clean; full `npm test -- --run`: 379 files, 6736 tests pass. No backend file touched.

## Self-Check: PASSED

Created and modified files exist; commits `19d1d88bc`, `713fd4f24`, `14c60c435`, `dd8a8076f`, `c0d7a1093` are ancestors of HEAD; acceptance greps match (isQuietTc 1, libraryNoRecentGamesText 1, flaw-stats-no-recent 1, isQuietTc( in sections 3, flaw-trend-caption 1).
