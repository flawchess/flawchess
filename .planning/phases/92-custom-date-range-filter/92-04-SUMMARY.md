---
phase: 92-custom-date-range-filter
plan: "04"
subsystem: frontend-ui-primitives
tags: [calendar, shadcn, react-day-picker, vaul, drawer, date-range]
dependency_graph:
  requires: [92-03]
  provides: [calendar-primitive, drawer-nested-export]
  affects: [frontend/src/components/ui/calendar.tsx, frontend/src/components/ui/drawer.tsx]
tech_stack:
  added: [react-day-picker@10.0.1]
  patterns: [shadcn-registry-install, vaul-nested-root-wrapper]
key_files:
  created:
    - frontend/src/components/ui/calendar.tsx
  modified:
    - frontend/src/components/ui/drawer.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/knip.json
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - shadcn add calendar produced working calendar.tsx but with three CLAUDE.md violations that were auto-fixed
  - button.tsx needed restoration after shadcn clobbered brand-outline variant and secondary hover; only buttonVariants export was kept
  - month_grid classNames key used instead of table (react-day-picker v10 API rename)
  - knip ignoreIssues for drawer.tsx exports to suppress DrawerNested until Plan 05 wires it
metrics:
  duration: ~25 minutes
  completed: 2026-05-22
  tasks_completed: 2
  files_changed: 6
---

# Phase 92 Plan 04: Calendar Primitive Install + DrawerNested Summary

shadcn Calendar primitive installed via registry (react-day-picker 10.0.1) with CLAUDE.md compliance fixes; DrawerNested wrapper added to drawer.tsx for vaul nested-sheet support.

## Tasks

| Task | Status | Commit |
|------|--------|--------|
| Task 1: Legitimacy checkpoint for react-day-picker | PRE-APPROVED by orchestrator | skipped |
| Task 2: shadcn add calendar + audit + DrawerNested | Complete | 66fe3f2f |

### Task 1: Pre-approved

Task 1 was a `checkpoint:human-verify` for `react-day-picker` legitimacy. Pre-approved by the orchestrator on 2026-05-22 per the checkpoint_preapproval block. No human prompt issued.

Verification performed:
- Maintainer: `gpbl` (Giampaolo Bellavite) confirmed
- Created: 2014-12-29 (~11 years old)
- Weekly downloads: 40,887,518 (well above 1M threshold)
- Repo: github.com/gpbl/react-day-picker -- active
- Version: 10.0.1 (matches expected 10.x)

## What Was Built

**frontend/src/components/ui/calendar.tsx** -- shadcn Calendar primitive wrapping react-day-picker `DayPicker` with `mode="range"` support. Passes all props through, uses theme tokens throughout (`bg-primary`, `bg-muted`, `bg-accent`, `text-primary-foreground`), no raw hex colors. Exports `Calendar` and `CalendarDayButton`.

**frontend/src/components/ui/drawer.tsx** -- Extended with `DrawerNested` function wrapping `DrawerPrimitive.NestedRoot` with `data-slot="drawer-nested"`. Added to export block. Exported but awaiting Plan 05 consumer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] shadcn clobbered button.tsx project variants**
- **Found during:** Task 2 Step 2 (shadcn install)
- **Issue:** `npx shadcn@latest add calendar --overwrite` rewrote `button.tsx`, removing the project-specific `brand-outline` variant, changing `secondary` hover behavior (`hover:brightness-125` → `hover:bg-secondary/80`), changing `lg` size padding (`pr-3/pl-3` → `pr-2/pl-2`), and changing the base active state (`active:translate-y-px` → `active:not-aria-[haspopup]:translate-y-px`). These variants are used throughout the app (CLAUDE.md mandates `brand-outline` for secondary actions).
- **Fix:** Restored all original project content while keeping the new `buttonVariants` export that `calendar.tsx` requires.
- **Files modified:** `frontend/src/components/ui/button.tsx`
- **Commit:** 66fe3f2f

**2. [Rule 2 - Missing functionality] text-sm floor violations in generated calendar.tsx**
- **Found during:** Task 2 Step 3 (audit)
- **Issue:** shadcn-emitted `calendar.tsx` used `text-[0.8rem]` (12.8px, below the 14px `text-sm` floor per CLAUDE.md) for `weekday` and `week_number` classNames, and `[&>span]:text-xs` for span children of day buttons.
- **Fix:** Changed `text-[0.8rem]` → `text-sm` on both class slots; `[&>span]:text-xs` → `[&>span]:text-sm` on the day button. Added inline comment at each override explaining the reason.
- **Files modified:** `frontend/src/components/ui/calendar.tsx`
- **Commit:** 66fe3f2f

**3. [Rule 1 - Bug] TypeScript error: `table` classNames key not valid in react-day-picker v10**
- **Found during:** Task 2 Step 5 (tsc check)
- **Issue:** `npx tsc --noEmit` reported `error TS2353: Object literal may only specify known properties, and 'table' does not exist in type 'Partial<ClassNames>'`. The `table` class name was renamed to `month_grid` in react-day-picker v10 (matches `UI.MonthGrid = "month_grid"` enum value).
- **Fix:** Renamed `table` → `month_grid` in the `classNames` prop.
- **Files modified:** `frontend/src/components/ui/calendar.tsx`
- **Commit:** 66fe3f2f

**4. [Rule 2 - Missing functionality] data-testid absent from day buttons**
- **Found during:** Task 2 Step 3 (audit, plan pre-noted)
- **Issue:** shadcn-emitted `CalendarDayButton` had no `data-testid` (CLAUDE.md Browser Automation Rules require it on interactive elements).
- **Fix:** Added `data-testid={`calendar-day-${format(day.date, 'yyyy-MM-dd')}`}` on the `Button` element. Also imported `format` from `date-fns`.
- **Files modified:** `frontend/src/components/ui/calendar.tsx`
- **Commit:** 66fe3f2f

**5. [Rule 3 - Blocking] knip failures for infrastructure-only exports**
- **Found during:** Task 2 Step 5 (knip run)
- **Issue:** knip reported `calendar.tsx` (new file, no consumer yet), `react-day-picker` (used by ignored `calendar.tsx`), and `DrawerNested` (no consumer until Plan 05) as unused.
- **Fix:** Added `calendar.tsx` to knip `ignore` array (same pattern as `popover.tsx`), added `react-day-picker` to `ignoreDependencies`, added `ignoreIssues: { "src/components/ui/drawer.tsx": ["exports"] }` to suppress the single-export flag until Plan 05 wires it.
- **Files modified:** `frontend/knip.json`
- **Commit:** 66fe3f2f

## Known Stubs

None. The Calendar component is a complete primitive ready for `mode="range"` usage. DrawerNested is a complete wrapper, not a stub. No hardcoded data or placeholder copy.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundaries introduced. The shadcn registry install is a supply-chain event -- covered by the pre-approved legitimacy checkpoint.

## Self-Check

- [x] `frontend/src/components/ui/calendar.tsx` exists
- [x] `frontend/src/components/ui/drawer.tsx` contains `DrawerNested` (declaration + export)
- [x] `react-day-picker` in `frontend/package.json` and `frontend/package-lock.json`
- [x] No raw hex in `calendar.tsx` (0 matches for `#[0-9a-fA-F]{6}`)
- [x] Commit `66fe3f2f` exists in git log
- [x] tsc: zero errors
- [x] lint: zero errors
- [x] knip: zero issues
- [x] tests: 611/611 passed (no regressions)

## Self-Check: PASSED
