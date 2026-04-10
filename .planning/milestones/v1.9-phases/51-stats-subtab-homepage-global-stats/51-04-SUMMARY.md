---
phase: 51-stats-subtab-homepage-global-stats
plan: 04
subsystem: frontend-nav, frontend-global-stats
tags: [nav-rename, global-stats, filters, opponent-type, opponent-strength, GSTA-01, GSTA-02]
dependency_graph:
  requires: [51-01]
  provides: [Global Stats rename end-to-end (nav + h1 + testids), opponent + opponentStrength filters visible on Global Stats FilterPanel]
  affects: [App.tsx, GlobalStats.tsx]
tech_stack:
  added: []
  patterns: [label-to-testid auto-derivation via label.toLowerCase().replace(/\s+/g, '-'), visibleFilters prop controls FilterPanel section visibility]
key_files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/GlobalStats.tsx
decisions:
  - "URL route /global-stats stays unchanged per D-17; only display label changes"
  - "h1 placed inside main before SidebarLayout so both desktop and mobile viewports see a single h1 (not duplicated per viewport)"
  - "h1 styled with text-2xl font-bold mb-4 md:mb-6 to match feature-section h2 sizing in Home.tsx"
  - "Bot games excluded by default on Global Stats page (opponentType='human' from DEFAULT_FILTERS) — visible behavior change from previous all-games inclusion (D-21)"
metrics:
  duration: ~10 minutes
  completed: "2026-04-10T14:42:12Z"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 2
---

# Phase 51 Plan 04: Global Stats Rename and Opponent Filters Summary

## One-liner

Renamed "Stats" to "Global Stats" across all nav surfaces and added a top-level h1, then enabled the opponent_type and opponent_strength FilterPanel controls on the Global Stats page — making bot-game exclusion the default.

## What Was Built

### Task 1: App.tsx nav rename (GSTA-01 / D-15 / D-16 / D-17)

Three single-word → two-word label swaps in `frontend/src/App.tsx`:

- `NAV_ITEMS[3].label`: `'Stats'` → `'Global Stats'`
- `BOTTOM_NAV_ITEMS[3].label`: `'Stats'` → `'Global Stats'`
- `ROUTE_TITLES['/global-stats']`: `'Stats'` → `'Global Stats'`

The existing label-to-testid derivation pattern (`label.toLowerCase().replace(/\s+/g, '-')`) automatically produces the renamed testids:
- `nav-global-stats` (desktop nav)
- `mobile-nav-global-stats` (mobile bottom bar)
- `drawer-nav-global-stats` (mobile More drawer)

No manual testid changes needed. The mobile page title (MobileHeader) reads from `ROUTE_TITLES` so it also updated automatically.

URL route `/global-stats` and `/rating` redirect preserved unchanged.

### Task 2: GlobalStats.tsx h1 + FilterPanel filters (GSTA-01/GSTA-02 / D-15 / D-21)

Two edits to `frontend/src/pages/GlobalStats.tsx`:

1. Added `<h1 data-testid="global-stats-page-title" className="text-2xl font-bold mb-4 md:mb-6">Global Stats</h1>` as the first child of `<main>`, before the desktop SidebarLayout and mobile drawer sections. Single h1 renders for both viewports.

2. Changed `visibleFilters` on both the desktop SidebarLayout FilterPanel and the mobile Drawer FilterPanel from `['platform', 'recency']` to `['platform', 'recency', 'opponent', 'opponentStrength']`. Plan 01 already wired the hooks (`useRatingHistory`, `useGlobalStats`) to accept and pass `filters.opponentType` and `filters.opponentStrength`, so enabling the UI controls immediately connects end-to-end.

## Visible Behavior Change

The Global Stats page now defaults to excluding bot games (`opponentType='human'` from `DEFAULT_FILTERS`). Previously the page included all games in global WDL and rating history because the opponent_type filter was not surfaced. This is the intended behavior per D-21.

## Decisions Made

1. **URL route unchanged** — `/global-stats` stays per D-17. No redirect from old routes needed.
2. **Single h1 placement** — inside `<main>` before both SidebarLayout and mobile div, so neither viewport duplicates it.
3. **h1 styling** — `text-2xl font-bold` matching feature-section h2 sizing in Home.tsx; `mb-4 md:mb-6` matching the `py-2 md:py-6` rhythm of the main container padding.
4. **Both FilterPanel instances updated** — CLAUDE.md "Always apply changes to mobile too" rule enforced: desktop SidebarLayout and mobile Drawer FilterPanel both get the 4-item visibleFilters array.

## Deviations from Plan

None — plan executed exactly as written. The precondition check (Plan 01's `filters.opponentType`/`filters.opponentStrength` wiring in `GlobalStats.tsx`) was verified before Task 2 execution.

Note: The worktree required a `git reset --soft` + `git checkout HEAD -- .` to restore to the correct Wave 1 base (`f77dbf3`) — the initial worktree HEAD was at `45c5b80` (main branch tip) rather than the expected base. This is a worktree initialization concern, not a code deviation.

## Threat Surface Scan

No new security surface introduced:
- Static h1 text — no PII, no new endpoints
- Testid renames are automation hooks only
- FilterPanel opponent controls inherit Plan 01's `Literal` validation mitigations (T-51-12 already mitigated)

## Known Stubs

None. All filter changes are fully wired end-to-end via Plan 01.

## Task 3 Status

Task 3 is `type="checkpoint:human-verify"` — execution paused at this checkpoint. Human verification of all 4 Phase 51 plans combined (9 verification steps) is required before the plan can be marked complete.

## Self-Check: PASSED

- `frontend/src/App.tsx` modified and committed at `019e8d4`
- `frontend/src/pages/GlobalStats.tsx` modified and committed at `9a58bd5`
- Both commits exist in git log
- `npm run lint`, `npm run knip`, `npm run build` all exit 0
