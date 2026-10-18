---
phase: 242-openings-stats-insights-rework
plan: 05
subsystem: ui
tags: [react, openings, stats, umami, localstorage, sticky-switch]

requires:
  - phase: 242-01
    provides: server-side most-played twin drop for bookmarked positions
provides:
  - "OpeningColorSwitch: sticky White | Black switch, Umami option-change target opening-stats-color"
  - "statsColor state in OpeningsPage and StatsTab props color / onColorChange (spine for 242-06 and 242-07)"
  - "removeRetiredBookmarkChartKeys: one-time sweep of bookmark-chart-enabled-* localStorage keys"
affects: [242-06, 242-07, 242-09, openings-frontend]

requirements-completed: [D-00, D-16]

actuals:
  tokens: 10750
  tasks: 3
  commits: 4
plan_head_before: 80340bcade8733228a6136505a9f93fd1e61d3f1
plan_head_after: 0e1863926443890a7a13fccb5066bbb94660b963

tech-stack:
  added: []
  patterns:
    - "Switch tracks only on a click that changes the selection (early return on same colour), never on mount"
    - "Phone switch shares the existing sticky Filters row; desktop gets its own lg-only sticky bar inside StatsTab"

key-files:
  created:
    - frontend/src/components/openings/stats/OpeningColorSwitch.tsx
    - frontend/src/components/openings/__tests__/OpeningColorSwitch.test.tsx
    - frontend/src/lib/retiredLocalStorage.ts
    - frontend/src/lib/__tests__/retiredLocalStorage.test.ts
  modified:
    - frontend/src/lib/analytics.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/openings/useOpeningsChartData.ts
    - frontend/src/pages/openings/OpeningsDesktopSidebar.tsx
    - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
    - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
    - frontend/src/hooks/usePositionBookmarks.ts

key-decisions:
  - "RETIRED_BOOKMARK_CHART_KEY_PREFIX is module-private: knip flags unused exports and only the sweep function needs it"
  - "On the Insights subtab the mobile sticky row renders an aria-hidden spacer on the left so the Filters button stays right-aligned (justify-between)"
  - "The bookmarks info popovers (desktop + mobile) lost the paragraph describing the retired chart toggle"

duration: 25min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 05: Sticky colour switch and bookmark toggle retirement Summary

**The Openings Stats tab now shows one colour at a time behind a sticky, non-persisted White | Black switch (desktop bar, or inside the phone Filters row) with a click-only Umami event, and the per-bookmark "Include in opening results" toggle plus its localStorage keys are fully retired.**

## Accomplishments

- `OpeningColorSwitch` (aria-pressed Buttons, `min-h-11` touch targets on phones, colour swatches) fires `trackFeature('option-change', { target: 'opening-stats-color', value })` only when the selection changes. `opening-stats-color` is registered in `OPTION_TARGETS` and `OptionChangeProps`.
- `statsColor` lives in `OpeningsPage`, seeded from the Played-as filter, never persisted and never written back to the filter store. `StatsTab` takes `color` / `onColorChange`, renders only the selected colour's bookmark section, ScoreChart (that colour's bookmarks) and most-played section, and a desktop-only sticky bar `opening-stats-color-bar` (`hidden lg:flex sticky top-0 z-20`). No ancestor of the bar carries `overflow-*`.
- On phones the switch sits on the left of the existing sticky Filters row (`justify-between`), so there is still exactly one `top-0` sticky row.
- The toggle is gone end to end: card button and props, list and sidebar/drawer pass-through, deferred drawer state, `chartToggleVersion`, `chartEnabledMap` memo with its eslint-disable, and the `chartBookmarks` subset. Phase-entry and time-series requests now take every bookmark.
- `removeRetiredBookmarkChartKeys` (collect-then-remove, returns the count, catches storage errors and returns 0) runs in a mount-only effect on the Openings page; the delete-time key removal and the `bookmark-chart` toggle target were removed.

## Task Commits

1. **Task 1 (tracer): sticky White | Black switch drives the Stats tab** - `315ae70cb` (feat)
2. **Task 2: retire the bookmark include/exclude toggle** - `317d201c2` (refactor)
3. **Task 3 RED: failing sweep test** - `ffd01e986` (test)
4. **Task 3 GREEN: sweep retired keys, drop analytics target** - `0e1863926` (feat)

Tracer gate (auto/end-of-phase, automated-only verify): the tracer `<verify>` (switch + analytics + Openings render tests, `npm run build`) passed before expansion, so no checkpoint was synthesized.

## Verification

- `npm test -- --run` full frontend suite: 5655 passed.
- `npm run lint`: clean. `npm run build` (tsc -b + vite): clean. `npm run knip`: exit 0 (two pre-existing configuration hints only).
- Acceptance greps: `bookmark-chart-toggle` in the card = 0, `chartEnabledMap` in the desktop sidebar = 0, `localChartEnabled` in the mobile drawers = 0, `chartBookmarks` in `useOpeningsChartData.ts` = 0, `'bookmark-chart'` in `analytics.ts` = 0, no `bookmark-chart-enabled-` outside the sweep module and its test.
- Not run here: the browser UAT of sticky behaviour at 390 / 768 / 1280 px (assigned to `/gsd-verify-work` by the plan).

## Deviations from Plan

None - plan executed exactly as written. (Minor choices, not deviations: the key prefix constant is not exported because knip rejects unused exports; the OpeningColorSwitch test mocks `@/lib/analytics` with a hoisted `trackFeature` mock instead of a `window.umami` stub.)

## Known Stubs

None.

## Threat Flags

None. T-242-13 (literal `'white' | 'black'` payload) and T-242-14 (fixed-prefix sweep, storage errors caught) are implemented as planned.

## Self-Check: PASSED

- FOUND: frontend/src/components/openings/stats/OpeningColorSwitch.tsx
- FOUND: frontend/src/components/openings/__tests__/OpeningColorSwitch.test.tsx
- FOUND: frontend/src/lib/retiredLocalStorage.ts
- FOUND: frontend/src/lib/__tests__/retiredLocalStorage.test.ts
- FOUND commits: 315ae70cb, 317d201c2, ffd01e986, 0e1863926
