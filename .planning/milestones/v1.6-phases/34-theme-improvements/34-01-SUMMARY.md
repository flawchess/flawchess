---
phase: 34-theme-improvements
plan: 01
subsystem: ui
tags: [tailwind, css-variables, react, typescript, recharts]

# Dependency graph
requires: []
provides:
  - CSS custom properties for brand-brown, brand-brown-hover, charcoal, sidebar-bg in :root
  - Tailwind utility classes bg-brand-brown, bg-charcoal, etc. via @theme inline
  - charcoal-texture CSS class with SVG feTurbulence noise overlay
  - Tabs brand variant with brand-brown active state for use in Plan 02
  - Filter buttons in equal-width grid layout spanning full sidebar width
  - Rounded outer corners on WDL stacked bar chart
  - PRIMARY_BUTTON_CLASS migrated to Tailwind utilities (no hardcoded hex)
affects: [34-02-theme-improvements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS custom properties in :root, registered as Tailwind utilities in @theme inline"
    - "charcoal-texture class with pseudo-element SVG noise overlay for textured backgrounds"
    - "CVA variant pattern extended with brand variant for tabs"

key-files:
  created: []
  modified:
    - frontend/src/index.css
    - frontend/src/lib/theme.ts
    - frontend/src/components/ui/tabs.tsx
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/charts/WDLBarChart.tsx

key-decisions:
  - "CSS variables defined in :root and exposed via @theme inline block (not hardcoded in Tailwind config)"
  - "charcoal-texture uses ::before pseudo-element for noise overlay so children don't need z-index workarounds — only direct children get z-index:1"
  - "Filter buttons use CSS grid (grid-cols-4/grid-cols-2) not flex-wrap for guaranteed equal-width columns"
  - "Recharts WDL bar radius on outermost bars only — Recharts 2.x lacks BarStack; zero-value bars have no visual effect"

patterns-established:
  - "Brand color constants: define in :root, register in @theme inline, reference as Tailwind utilities"
  - "Tabs brand variant: bg-charcoal container with group-data-[variant=brand] active state selectors"

requirements-completed: [THEME-01, THEME-03, THEME-04, THEME-05]

# Metrics
duration: 10min
completed: 2026-03-28
---

# Phase 34 Plan 01: Theme Infrastructure Summary

**CSS variable foundation with brand-brown/charcoal Tailwind utilities, charcoal-texture noise class, tabs brand variant, grid-based filter buttons, and rounded WDL chart bars**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-28T10:48:00Z
- **Completed:** 2026-03-28T10:58:06Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `--brand-brown`, `--brand-brown-hover`, `--charcoal`, `--sidebar-bg` CSS custom properties and registered as Tailwind utilities so components can use `bg-brand-brown`, `bg-charcoal`, etc.
- Created `.charcoal-texture` CSS class with SVG `feTurbulence` noise overlay via `::before` pseudo-element for textured dark backgrounds
- Migrated `PRIMARY_BUTTON_CLASS` from hardcoded `bg-[#8B5E3C]` hex to `bg-brand-brown` Tailwind utility
- Added `brand` variant to Tabs component with charcoal background and brand-brown active trigger state
- Changed Time Control (4 buttons) and Platform (2 buttons) filter containers from `flex flex-wrap` to CSS grid for equal-width full-width layout
- Added `w-full` and `flex-1` to Rated and Opponent ToggleGroup/ToggleGroupItem for consistent full-width distribution
- Rounded outer corners of WDL stacked bar chart (`win_pct` radius `[4,4,0,0]`, `loss_pct` radius `[0,0,4,4]`)

## Task Commits

Each task was committed atomically:

1. **Task 1: CSS variable foundation + charcoal texture + theme.ts migration** - `73fbc4c` (feat)
2. **Task 2: Tabs brand variant + filter grid layout + WDL chart rounding** - `5d158dd` (feat)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified
- `frontend/src/index.css` - Added brand-brown/charcoal CSS variables, @theme inline entries, charcoal-texture component class
- `frontend/src/lib/theme.ts` - PRIMARY_BUTTON_CLASS migrated to Tailwind utilities
- `frontend/src/components/ui/tabs.tsx` - Added brand variant to TabsList CVA and brand active state to TabsTrigger
- `frontend/src/components/filters/FilterPanel.tsx` - Grid layout for Time Control/Platform buttons, w-full/flex-1 on ToggleGroups
- `frontend/src/components/charts/WDLBarChart.tsx` - Rounded outer corners on win_pct and loss_pct bars

## Decisions Made
- CSS variables in `:root`, exposed via `@theme inline` — consistent with how existing shadcn variables work in the project
- `charcoal-texture` uses `::before` pseudo-element so children don't need individual z-index; only direct children get `z-index: 1`
- Grid layout for filter buttons over flex-wrap — guarantees equal-width columns regardless of label length
- Recharts outer-bar-only rounding — Recharts 2.x doesn't support BarStack; zero-value bars silently have no visual effect

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All theme infrastructure is in place for Plan 02 to use `charcoal-texture`, `bg-brand-brown`, and the `brand` tabs variant on page-level components
- Build passes, all 38 tests green

## Self-Check: PASSED

All files present and commits verified:
- `73fbc4c` feat(34-01): CSS variable foundation + charcoal texture + theme.ts migration
- `5d158dd` feat(34-01): tabs brand variant, filter grid layout, WDL chart rounding

---
*Phase: 34-theme-improvements*
*Completed: 2026-03-28*
