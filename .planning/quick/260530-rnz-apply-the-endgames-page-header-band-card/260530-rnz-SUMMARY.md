---
status: complete
phase: quick-260530-rnz
plan: "01"
subsystem: frontend
tags: [style, header-band, openings, overview, bookmarks]
completed: "2026-05-30T18:07:26Z"
duration: ~10 min
tasks_completed: 3
tasks_total: 3
key_files:
  modified:
    - frontend/src/components/stats/GlobalStatsCharts.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/components/charts/PositionResultsPanel.tsx
    - frontend/src/pages/openings/GamesTab.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/components/charts/ScoreChart.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
decisions:
  - "Endgames.tsx PositionResultsPanel className cleaned (not in plan scope but required for correctness)"
---

# Quick Task 260530-rnz: Apply Endgames Header-Band Card Style Summary

**One-liner:** Full-bleed `bg-black/20` header bands with `overflow-hidden` card shells applied to 5 surface areas across Overview, Openings, and Bookmarks pages.

## Objective

Apply the Endgames-page header-band card grammar (recessed `<h3>` band + `overflow-hidden` wrapper + `p-4` content div) to Overview rating cards, WDL charts, PositionResultsPanel, OpeningStatsCard/OpeningFindingCard accent cards, and the Score over Time chart. Style-only: no behavior or data changes.

## Tasks Completed

| Task | Name | Commit | Key files |
|------|------|--------|-----------|
| 1 | Overview cards + Results-by-Color split + position-results card | a1433a2d | GlobalStatsCharts.tsx, GlobalStats.tsx, PositionResultsPanel.tsx, GamesTab.tsx, Endgames.tsx |
| 2 | Openings Stats + Insights accent cards + Score over Time | 2824668a | OpeningStatsCard.tsx, OpeningFindingCard.tsx, ScoreChart.tsx, StatsTab.tsx, OpeningStatsCard.test.tsx |
| 3 | Full frontend gate fix | a9ade8cf | OpeningFindingCard.test.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OpeningFindingCard.test.tsx border assertions also needed updating**
- **Found during:** Task 3 (full gate run)
- **Issue:** `OpeningFindingCard.test.tsx` had 3 tests asserting `borderLeftColor` on the card root (`opening-finding-card-N`) — same pattern as OpeningStatsCard, but the plan only mentioned updating `OpeningStatsCard.test.tsx`. After Task 2 moved `border-l-4` to the content div, the FindingCard tests failed.
- **Fix:** Updated the 3 border zone assertions to query `opening-finding-card-N-content` instead of the card root.
- **Files modified:** `frontend/src/components/insights/OpeningFindingCard.test.tsx`
- **Commit:** a9ade8cf

**2. [Rule 2 - Missing] Endgames.tsx PositionResultsPanel className cleanup**
- **Found during:** Task 1
- **Issue:** `Endgames.tsx` also passes `className="charcoal-texture rounded-md p-4"` to `PositionResultsPanel`. After the component started owning its own shell, this would have duplicated the shell classes.
- **Fix:** Updated `className=""` on the Endgames.tsx caller (same as GamesTab.tsx). Not in plan scope but required for correctness.
- **Files modified:** `frontend/src/pages/Endgames.tsx`
- **Commit:** a1433a2d

## Pattern Applied

Every targeted card now follows the canonical grammar from `EndgameScoreOverTimeChart.tsx`:

```
<div class="charcoal-texture rounded-md overflow-hidden">
  <h3 class="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold" data-testid="...-header">
    Title [+ InfoPopover]
  </h3>
  <div class="p-4">...body...</div>
</div>
```

**Accent cards (OpeningStatsCard, OpeningFindingCard) special handling:**
- `border-l-4` + `borderLeftColor` moved from card root to `<div data-testid="...-content">` so the header band is un-accented (full-width, plain recessed).
- Opacity muting (`isCardMuted` / `isUnreliable`) remains on the card root so the entire card (including header) mutes.

**ChartTitle removed:** The `ChartTitle` helper function in `GlobalStatsCharts.tsx` was replaced by the inline header-band pattern. Knip stays green.

## Verification

- `npm run lint`: pass
- `npm test -- --run`: 735/735 pass
- `npm run knip`: pass
- `grep -rl "bg-black/20 border-b border-border/40"` returns all 5 target files
- No `Accordion`, `AccordionTrigger`, `ChevronDown`, or `ChevronUp` added to any touched card

## Self-Check: PASSED

- All 3 task commits exist: a1433a2d, 2824668a, a9ade8cf
- All 5 targeted files contain the band pattern (grep confirmed above)
- 735 tests passing, lint clean, knip clean
- No stubs introduced — pure structural styling transform
