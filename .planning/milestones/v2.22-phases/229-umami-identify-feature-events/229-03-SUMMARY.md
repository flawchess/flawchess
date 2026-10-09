---
phase: 229-umami-identify-feature-events
plan: 03
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, panels, navigation]

requires: [229-02]
provides:
  - "panel-open on desktop sidebar strip opens (filters, tags, bookmarks) and all 8 mobile filter/tag/bookmark drawers"
  - "panel-open more-drawer, nav-click {value: more-drawer} and panel-open settings on every settings entry point"
  - "filter-change endgame-type on the Endgames endgame type select"
affects: [229-08]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 72a7089c36a24c42712f83bd125145c925284fb0
plan_head_after: ef1f96d5cbbc5f2546c2f1aa2562c6326cbe4091

key-files:
  created:
    - frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx
  modified:
    - frontend/src/components/layout/SidebarLayout.tsx
    - frontend/src/components/filters/MobileFilterDrawer.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/components/settings/SettingsDialogButton.tsx
    - frontend/src/components/settings/SettingsSheetButton.tsx
    - frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx
    - frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx

key-decisions:
  - "MobileFilterDrawer is the one effect-style tracking site: parents open it from their own trigger state, so the false-to-true transition of `open` is the tap; the ref starts at the mount value so a drawer mounted open fires nothing (D-03)"
  - "SidebarPanelConfig.id typed SidebarPanelId; GamesTab/FlawsTab panel arrays annotated SidebarPanelConfig[] (no casts)"
  - "Admin/Activity excluded from nav-click via navDestinationOf returning null; Links use onClick tracking, no data-umami-event"

requirements-completed: [D-03, D-12, D-13, D-14]

coverage:
  - id: C1
    description: "Sidebar strip open fires one panel-open with the panel id; close and outside-click fire nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx#SidebarLayout"
        status: pass
    human_judgment: false
  - id: C2
    description: "MobileFilterDrawer fires once per open transition, nothing on re-render or mount-open; every call site names its panel (build gate)"
    verification:
      - kind: unit
        ref: "frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx#MobileFilterDrawer"
        status: pass
      - kind: build
        ref: "npm run build (tsc -b)"
        status: pass
    human_judgment: false
  - id: C3
    description: "More button, drawer nav items (locked and Admin/Activity silent) and drawer Settings row"
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#229 nav and drawer tracking"
        status: pass
    human_judgment: false
  - id: C4
    description: "Desktop settings dialog and mobile settings sheet fire panel-open settings per open"
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx#panel-open tracking"
        status: pass
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx#panel-open tracking"
        status: pass
    human_judgment: false
  - id: C5
    description: "Endgames endgame-type select fires filter-change"
    verification:
      - kind: build
        ref: "npm run build (typed registry gate); behaviour deferred to Plan 08 browser UAT per plan"
        status: pass
    human_judgment: true

duration: 12min
completed: 2026-10-03
---

# Phase 229 Plan 03: Panel and navigation tracking Summary

Typed `panel-open` discovery events on every desktop sidebar panel, all 8 mobile filter/tag/bookmark drawers, the More drawer and every settings entry point, plus `nav-click` for More-drawer items (never Admin/Activity) and `filter-change` for the Endgames endgame type.

## What was built

- `SidebarLayout`: `handleStripClick` fires `panel-open` only on the opening click; the closing click and outside-click close send nothing.
- `MobileFilterDrawer`: required `panel: SidebarPanelId` prop and a ref-guarded open-transition effect; all 8 call sites pass `filters`, `tags` or `bookmarks`.
- `App.tsx`: More button fires `panel-open more-drawer`; module-private `trackMoreDrawerNav` calls `navDestinationOf` and sends `nav-click {target, value: 'more-drawer'}`; the drawer Settings row fires `panel-open settings`.
- `SettingsDialogButton` / `SettingsSheetButton` use `useTrackedOpen` (every open counted).
- `Endgames.tsx` endgame-type select sends `filter-change {target: 'endgame-type', value}`.

## Verification

- `npx vitest run` full frontend suite: 290 files, 4725 tests pass.
- `npm run lint` clean; `npm run build` (tsc -b + vite) clean.
- Acceptance greps: 8 drawers carry `panel=`; `id: SidebarPanelId` x1; `trackFeature('nav-click'` x1 in App.tsx; `useTrackedOpen(` x1 per settings button; `target: 'endgame-type'` x1; `data-umami-event` count in App.tsx unchanged (pre-existing, none added).
- No suite mocking `@/lib/analytics` renders a touched component (SettingsPanel/EngineReadyGate/ImportAskActions mocks are untouched and pass).

## Programmatic drawer opens (step 3 audit)

None found for the 8 mobile drawers: all parent open setters (`setMobileFiltersOpen(true)`, `openFilterSidebar`, `openBookmarkSidebar`) are called from trigger click handlers. One programmatic open exists on the desktop sidebar only: `Openings.tsx` SuggestionsModal `onSaved` calls `sidebar.setSidebarOpen('bookmarks')`. It bypasses `SidebarLayout.handleStripClick`, so it fires no `panel-open` (correct per D-03). Not refactored.

## Deviations from Plan

None - plan executed exactly as written. `npm ci` was run once in the fresh worktree's `frontend/` (no package added).

## Known Stubs

None.

## Threat Flags

None. T-229-11 (Admin/Activity never named) is covered by the superuser App.test case; T-229-12 by the mount-open drawer test.

## Notes

- Endgames endgame-type select has no unit test (page needs heavy query mocks); covered by the typed registry build gate and Plan 08 browser UAT, as the plan specified.
- knip was not run (deferred to Plan 08 per the plan).

## Self-Check: PASSED

- Commits `d63eca205` (Task 1) and `ef1f96d5c` (Task 2) exist on the worktree branch; all key-files exist.
