---
title: Library Stats-tab restructure — move FlawStatsPanel out of the Games subtab
date: 2026-06-06
context: Phase 107 UAT-checkpoint decision. The Games subtab currently leads with a large FlawStatsPanel that gets in the way of browsing the filtered game list. Restructure decided via /gsd-explore. This note is the implementation spec for a parallel UAT/iteration session — it stays inside phase 107 scope (no new phase).
related_files:
  - frontend/src/pages/library/LibraryPage.tsx
  - frontend/src/pages/library/OverviewTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/components/library/FlawStatsPanel.tsx
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/hooks/useFilterStore.ts
---

# Library Stats-tab restructure

Captured during `/gsd-explore` on 2026-06-06. This is an implementation spec, not a fuzzy
idea — it can be handed to a `/gsd-quick` task or implemented directly inside phase 107.

## Problem

The Library → **Games** subtab leads with a large `FlawStatsPanel` stacked above the
filtered game list (`GamesTab.tsx:215`). The panel gets in the way of the core job of the
Games tab — browsing the filtered list of games. The flaw stats are interesting and worth
keeping (and improving later), but they belong with the other *stats*, not on top of a
browser.

Both the Openings and Endgames pages already have a dedicated **Stats** tab. The Library's
**Overview** tab is the natural home for the flaw stats and should be renamed to match.

## Decisions (locked)

1. **Rename `Overview` → `Stats`.** Route `/library/overview` → `/library/stats`. Matches
   the Openings (`/openings/stats`) and Endgames (`/endgames/stats`) precedent.

2. **Move `FlawStatsPanel` from the Games subtab into the Stats tab.** It joins the existing
   global content there (rating charts + WDL breakdown charts from `GlobalStatsPage`).

3. **Stats tab is driven by the shared global filter store with the FULL filter panel.**
   Today the Overview/GlobalStats tab deliberately exposes only `visibleFilters={['platform',
   'recency']}` (`GlobalStats.tsx:121,175`). Expand this to the full filter set (time control,
   color, opponent, recency, platform). The shared `useFilterStore` already holds the full
   `FilterState` (`useFilterStore.ts` → `FilterState`), and the global query hooks already
   receive the full `filters` object (`GlobalStats.tsx:22-26`), so no query plumbing changes
   are needed — only the UI exposure widens.

4. **"Accept the collapse" — full filtering is a feature, not a regression.** The global WDL
   charts are *breakdowns by* TC and color (`by_time_control` / `by_color`,
   `GlobalStats.tsx:93-94`), not filtered by them. Filtering to a single TC/color collapses
   those breakdown charts to one slice — and that is desirable: it lets the user view
   "Results by Color" for one time control, or "Results by Time Control" for one color, and it
   filters the FlawStatsPanel meaningfully. This mirrors the existing Endgames pattern, where
   a TC filter hides TC-specific cards in some sections while filtering the data in others.

5. **The severity (blunder/mistake) filter stays in the Games tab, scoped to the game list
   only.** It is NOT part of `FilterState` and must NOT drive the FlawStatsPanel or the global
   stats. Today `severityFilter` is local `useState` in `GamesTab` (`GamesTab.tsx:57`) and is
   passed to both `useLibraryGames` (`:165`) and `useLibraryFlawStats` (`:171`). After the
   move, it drives only `useLibraryGames`.

6. **Games tab becomes a lean filtered browser:** filter panel (with the severity filter) +
   `LibraryGameCardList`. No stats panel.

7. **App-level landing (separate, "for now, may change"):** route returning users (who have
   games) to the **Openings** page, not into the Library. This revisits the recent
   `51537b63` flip that sent returning users to `/library/games`. Treat as a small, reversible
   navigation decision.

## Concrete change checklist

- **`LibraryPage.tsx`**
  - Rename the `overview` tab label/value to `stats`; update the `TabsTrigger`/`TabsContent`
    in both the desktop block (`:52-81`) and the mobile block (`:85-142`).
  - Update `activeTab` derivation (`:36-40`) to recognize `/library/stats` (and treat it as
    the default instead of `overview`).
  - Update the returning-user redirect (`:27-34`) per decision 7 (returning-user-with-games →
    Openings; no-games → `/library/import` unchanged). Confirm the within-Library default
    subtab still resolves sensibly (Stats as primary content tab).
  - Update `data-testid`s referencing `overview`.

- **`OverviewTab.tsx` → Stats tab composition**
  - This file wraps `GlobalStatsPage`. The Stats tab should render the existing global content
    **plus** `FlawStatsPanel`. Decide placement (see open detail below). Rename the
    file/component to `StatsTab` for clarity (optional but preferred for consistency with
    Openings' `StatsTab`).

- **`GlobalStats.tsx`**
  - Change both `FilterPanel` usages from `visibleFilters={['platform', 'recency']}` to the
    full set (`:121` desktop, `:175` mobile drawer). Drop the "GlobalStats only uses recency +
    platforms" comments (`:17`, `:42-44`) — no longer true.
  - Mount `FlawStatsPanel` here (or in the renamed `StatsTab` wrapper). Feed it the shared
    `filters` from `useFilterStore` and an **empty** severity argument.

- **`GamesTab.tsx`**
  - Remove `FlawStatsPanel` (`:215`) and its `useLibraryFlawStats` call (`:171`) and import.
  - Keep `severityFilter` (`:57`) wired to `useLibraryGames` only.
  - Keep the `LibraryFilterPanel` + `LibraryGameCardList`. The tab is now just filters + list.

- **`FlawStatsPanel` query** (`useLibraryFlawStats`)
  - Drop the `severityFilter` argument at its new call site. If the hook signature requires it,
    pass an empty array, or simplify the hook signature to remove the param. Verify no other
    caller depends on the severity argument.

## Out of scope (do NOT bundle into this restructure)

- **FlawStatsPanel content/visual improvements.** The "with some improvements it could be
  interesting" idea is deferred. Land the structural move first, then iterate on the panel
  separately. Park this thought rather than scope-creeping the move.
- The smaller phase-107 UAT bugs/UI tweaks — handle those in the normal UAT fix loop
  (`/gsd-fast`), independent of this restructure.

## Open detail (low stakes, implementer's call)

- **Vertical order on the Stats tab:** FlawStatsPanel above or below the rating + WDL
  breakdown charts. Suggest leading with the global performance overview (rating + WDL) and
  placing FlawStatsPanel below, but either is fine — confirm during UAT.
- **Within-Library default subtab** when a user navigates directly to `/library`: default to
  Stats (matches Endgames → stats). Only relevant if decision 7's app-level redirect is not
  the sole entry path.
