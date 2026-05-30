---
phase: quick-260530-pll
plan: 01
subsystem: frontend/endgames
tags: [accordion, collapsible, endgame-metrics, elo-timeline, primary-tc]
dependency_graph:
  requires: [computePrimaryTc, Accordion primitive, EndgameTypeBreakdownSection pattern]
  provides: [collapsible EndgameMetricsByTcCard, primary-TC default expand, primary-TC timeline visibility]
  affects: [Endgames.tsx, EndgameMetricsByTcCard.tsx, EndgameMetricsByTcSection.tsx, EndgameEloTimelineSection.tsx]
tech_stack:
  added: []
  patterns: [Radix Accordion type="multiple" controlled, computePrimaryTc reuse across sections]
key_files:
  created: []
  modified:
    - frontend/src/components/charts/EndgameMetricsByTcCard.tsx
    - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx
decisions:
  - "Used Accordion type=multiple (independent fold/unfold) matching Phase 98 precedent"
  - "computeDefaultHiddenByPrimaryTc: fallback to showing all combos (empty hidden set) when computePrimaryTc returns null (no TC clears MIN_GAMES_PER_TC_CARD floor)"
  - "Removed MAX_DEFAULT_VISIBLE and MIN_ACTIVE_WEEKS_RATIO constants — no longer needed after replacing old heuristic"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-30"
  tasks_completed: 2
  files_modified: 7
---

# Phase quick-260530-pll Plan 01: Collapsible TC Endgame Metrics Cards + Primary-TC Timeline Summary

Per-TC Endgame Metrics cards converted to collapsible accordion items with primary-TC default-expand, and the ELO Timeline defaulted to the primary-TC series using the shared `computePrimaryTc` heuristic.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Make per-TC Endgame Metrics cards collapsible with primary-TC default-expand | 3c7e1340 | EndgameMetricsByTcCard.tsx, EndgameMetricsByTcSection.tsx, Endgames.tsx, EndgameMetricsByTcSection.test.tsx |
| 2 | Default Endgame ELO Timeline to primary TC across both platforms | ee599f00 | EndgameEloTimelineSection.tsx, EndgameEloTimelineSection.test.tsx |
| fix | Wrap EndgameMetricsByTcCard unit tests in Accordion (Rule 1 bug fix) | 982901d7 | EndgameMetricsByTcCard.test.tsx |

## What Was Built

**Task 1:** `EndgameMetricsByTcCard` is now an `AccordionItem` that must live inside the `Accordion` orchestrated by `EndgameMetricsByTcSection`. The header band (TimeControlIcon + TC label + games count) is the `AccordionTrigger`; the three-metric body (Conversion / Parity / Recovery) is `AccordionContent`. The chevron is supplied by the shared `AccordionTrigger` primitive. `EndgameMetricsByTcSection` now holds `useState<string[]>` for `expandedTcs`, seeded with the primary TC via `computePrimaryTc`, and resets on `filterKey` change. `Endgames.tsx` passes `filterKey={JSON.stringify(appliedFilters)}`.

**Task 2:** `EndgameEloTimelineSection` replaces `computeDefaultHidden` (active-weeks ratio + top-1-by-games cap) with `computeDefaultHiddenByPrimaryTc`, which: sums `per_week_total_games` per TC across platforms, calls `computePrimaryTc(byTc, MIN_GAMES_PER_TC_CARD)`, and returns a hidden-keys `Set` containing all combo keys whose `time_control !== primaryTc`. Both chess.com and lichess combos for the primary TC are visible by default. Fallback: if `computePrimaryTc` returns null, nothing is hidden (show all). The `MAX_DEFAULT_VISIBLE` and `MIN_ACTIVE_WEEKS_RATIO` constants were removed entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EndgameMetricsByTcCard unit tests needed Accordion wrapper**

- **Found during:** Full test suite run after Task 2
- **Issue:** `EndgameMetricsByTcCard.test.tsx` rendered the card directly. Once the card became an `AccordionItem`, Radix threw `AccordionItem must be used within Accordion` at runtime.
- **Fix:** Updated all `render()` calls in the test file to wrap the card in `<Accordion type="multiple" defaultValue={[card.tc]}>` with `defaultValue` set to the card's TC so content is expanded and visible in tests.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx`
- **Commit:** 982901d7

## Known Stubs

None — all data flows from real API responses. No hardcoded placeholders introduced.

## Verification Gates

- lint: passed (eslint clean)
- tests: 735/735 passed
- build: succeeded (TypeScript clean, no type errors)
- knip: clean (no dead exports; MAX_DEFAULT_VISIBLE/MIN_ACTIVE_WEEKS_RATIO removed along with computeDefaultHidden)
- HUMAN-UAT: On the Endgames page with multi-TC data — metrics cards collapse/expand with chevron, primary-TC card is open by default and others closed, ELO Timeline shows only the primary TC enabled (both platforms if played on both).

## Self-Check: PASSED

- 3c7e1340 exists: yes (feat: collapsible metrics cards)
- ee599f00 exists: yes (feat: primary-TC timeline visibility)
- 982901d7 exists: yes (fix: Accordion wrapper in unit tests)
- All modified files confirmed present in worktree
