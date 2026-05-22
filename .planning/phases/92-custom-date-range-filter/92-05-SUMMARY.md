---
phase: 92-custom-date-range-filter
plan: "05"
subsystem: frontend-ui
tags: [calendar, popover, drawer, filters, date-range, custom-range]
dependency_graph:
  requires: [92-04]
  provides: [custom-range-ui, FilterPanel-custom-item]
  affects:
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/filters/CustomRangePopover.tsx
    - frontend/src/components/filters/CustomRangeDrawer.tsx
tech_stack:
  added: []
  patterns:
    - PopoverAnchor asChild wrapping Select trigger (Radix D-03 two-step pattern)
    - vaul DrawerNested for nested mobile sheet (D-06)
    - queueMicrotask deferral to avoid Select close / Popover open focus race (RESEARCH.md §Pitfall 6)
    - useIsMobile inline breakpoint hook (768px threshold, same as ScoreChart.tsx)
    - DateRange ↔ FilterState.customRange shape conversion (from: Date|undefined vs from?: Date)
key_files:
  created:
    - frontend/src/components/filters/CustomRangePopover.tsx
    - frontend/src/components/filters/CustomRangeDrawer.tsx
  modified:
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/knip.json
decisions:
  - "formatCustomRangeLabel co-located in CustomRangePopover.tsx with eslint-disable comment (mirrors FilterPanel pattern for non-component exports)"
  - "useIsMobile defined inline in FilterPanel.tsx (no shared hook file exists; consistent with ScoreChart pattern)"
  - "initialFocus prop removed — react-day-picker v10 removed this prop (was v8 API)"
  - "DateRange.from is Date|undefined (required key) vs FilterState.customRange.from is Date|undefined (optional key) — explicit conversion at component boundaries"
  - "knip.json: removed calendar.tsx from ignore, date-fns and react-day-picker from ignoreDependencies, drawer.tsx ignoreIssues — all now traced through import chain"
metrics:
  duration: ~35 minutes
  completed: 2026-05-22
  tasks_completed: 2
  files_changed: 4
---

# Phase 92 Plan 05: FilterPanel Custom Range UI Summary

Desktop Popover (two-month Calendar, auto-closes on full range pick) and mobile nested Vaul Drawer (single-month Calendar + Apply CTA, backdrop=cancel) wired into FilterPanel's Recency Select as a 9th "Custom range…" item.

## What Was Built

### Task 1: CustomRangePopover + CustomRangeDrawer

**frontend/src/components/filters/CustomRangePopover.tsx** — Desktop popover body (PopoverContent) containing a two-month range-mode Calendar.

- `formatCustomRangeLabel(range)` exported helper: formats both/from/to bounds as `"MMM d, yyyy – MMM d, yyyy"`, `"From MMM d, yyyy"`, `"Until MMM d, yyyy"`, or `"Custom range…"` for display on the Select trigger (D-04/D-17).
- Auto-close (D-05): `onSelect` fires `onOpenChange(false)` immediately when both `from` and `to` are set.
- Does NOT contain the `<Popover>` root — FilterPanel owns that so `<PopoverAnchor asChild>` can wrap the Select.
- Uses `PopoverContent` with `w-auto p-0` to accommodate the two-month Calendar width (~580 px).

**frontend/src/components/filters/CustomRangeDrawer.tsx** — Mobile nested sheet (DrawerNested > DrawerContent) with a single-month Calendar and Apply CTA.

- Maintains `localRange` state; parent `onChange` is called ONLY when user taps Apply (D-07).
- Backdrop dismiss fires vaul's `onOpenChange(false)` without touching `onChange` (D-08).
- Apply button is `disabled` when `!localRange?.from` (D-15 frontend prevention).
- Calendar `data-testid="custom-range-calendar"` present in both components; day-cell `calendar-day-${YYYY-MM-DD}` testids come from the `CalendarDayButton` in `calendar.tsx` (Plan 04).

### Task 2: FilterPanel.tsx wiring

- Added `useIsMobile` inline hook (same 768 px threshold as ScoreChart.tsx, not a shared file).
- Added `const [customOpen, setCustomOpen] = useState(false)` for popover/drawer state.
- **Recency Select** now wrapped in `<Popover open={customOpen && !isMobile} onOpenChange={setCustomOpen}><PopoverAnchor asChild>`.
- 9th `<SelectItem value="custom" data-testid="filter-recency-custom">Custom range…</SelectItem>` added at bottom.
- `onValueChange`: when `v === 'custom'`, defers `setCustomOpen(true)` via `queueMicrotask` (RESEARCH.md §Pitfall 6); for any preset, calls `update({ recency: ..., customRange: null })` to clear the custom range.
- `<SelectTrigger>` content: when `filters.recency === 'custom'`, renders `formatCustomRangeLabel(filters.customRange)` string; otherwise renders `<SelectValue />` (normal preset label).
- `<CustomRangePopover>` rendered inside the `<Popover>` tree (desktop branch, gated `!isMobile`).
- `<CustomRangeDrawer>` rendered after the Popover (mobile branch, gated `isMobile`).
- **knip.json**: removed `calendar.tsx` from `ignore`, `date-fns` and `react-day-picker` from `ignoreDependencies`, and the `ignoreIssues` for `drawer.tsx` — all are now reachable via the import graph from FilterPanel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] react-day-picker v10 removed `initialFocus` prop**
- **Found during:** Task 1 TypeScript check
- **Issue:** TypeScript error — `initialFocus` does not exist on DayPickerProps in react-day-picker v10 (was a v8 prop).
- **Fix:** Removed `initialFocus` from the Calendar in CustomRangePopover.tsx.
- **Files modified:** `frontend/src/components/filters/CustomRangePopover.tsx`
- **Commit:** a92eb4d3

**2. [Rule 1 - Bug] DateRange type mismatch — `from` is required key in react-day-picker but optional in FilterState**
- **Found during:** Task 1 TypeScript check
- **Issue:** `DateRange = { from: Date | undefined; to?: Date }` (required key `from`, even if `undefined`) vs. `FilterState.customRange = { from?: Date; to?: Date }` (optional key). Passing `value` directly to Calendar `selected` and `useState` failed type check.
- **Fix:** Added explicit conversion at component boundaries: `{ from: value.from, to: value.to }` (required key, possibly undefined value) when constructing DateRange from FilterState, and the reverse when committing.
- **Files modified:** `frontend/src/components/filters/CustomRangePopover.tsx`, `frontend/src/components/filters/CustomRangeDrawer.tsx`
- **Commit:** a92eb4d3

**3. [Rule 2 - Missing critical functionality] eslint-disable-next-line for formatCustomRangeLabel export**
- **Found during:** Task 1 lint check
- **Issue:** Exporting a non-component function (`formatCustomRangeLabel`) from a file that also exports a component triggers `react-refresh/only-export-components`. Identical situation to `areFiltersEqual` in FilterPanel.tsx (line 34 already has the same disable).
- **Fix:** Added `// eslint-disable-next-line react-refresh/only-export-components` immediately before the `export function formatCustomRangeLabel` declaration.
- **Files modified:** `frontend/src/components/filters/CustomRangePopover.tsx`
- **Commit:** a92eb4d3

**4. [Rule 2 - Missing critical functionality] knip.json cleanup — remove now-unnecessary ignores**
- **Found during:** Task 2 knip check (knip reported "Configuration hints")
- **Issue:** After FilterPanel wired the Calendar via CustomRangePopover, knip could now trace: `FilterPanel → CustomRangePopover → calendar.tsx → react-day-picker + date-fns`. The `ignore` entry for `calendar.tsx` and `ignoreDependencies` entries for `date-fns` and `react-day-picker` (added in Plan 04) were now unnecessary. Additionally, `DrawerNested` is now consumed (no longer flagged), so the `ignoreIssues` for `drawer.tsx` was removed.
- **Fix:** Removed the 4 obsolete entries from `knip.json`.
- **Files modified:** `frontend/knip.json`
- **Commit:** bf42ed14

## Known Stubs

None. Both CustomRangePopover and CustomRangeDrawer are complete UI features. The Calendar is wired to the FilterState.customRange field (committed from Plan 03). Range commits flow through `update({ recency: 'custom', customRange: range })` which is consumed by all 7 hooks via `resolveDateRange()` (committed in Plan 03).

## Threat Flags

None. This plan adds two new interactive UI surfaces (Calendar day buttons, Apply CTA) with no new network endpoints, auth paths, or trust boundaries. T-92-05-01/02/03 from the plan's threat register are all accepted: range ordering is enforced by Calendar click order + disabled Apply, testids are non-secret, backdrop dismiss = cancel is implemented correctly.

## Self-Check

Checking created files exist:
- `frontend/src/components/filters/CustomRangePopover.tsx` — YES
- `frontend/src/components/filters/CustomRangeDrawer.tsx` — YES

Checking commits exist:
- `a92eb4d3` (Task 1): YES
- `bf42ed14` (Task 2): YES

Checking acceptance criteria:
- `data-testid="custom-range-popover"` in CustomRangePopover.tsx: 1 match — YES
- `data-testid="custom-range-calendar"` in both files: 2 matches — YES
- `data-testid="drawer-custom-range"` in CustomRangeDrawer.tsx: 1 match — YES
- `data-testid="btn-apply-custom-range"` in CustomRangeDrawer.tsx: 1 match — YES
- `data-testid="filter-recency-custom"` in FilterPanel.tsx: 1 match — YES
- `queueMicrotask` in FilterPanel.tsx: 1 match — YES
- `PopoverAnchor` in FilterPanel.tsx: 2 matches (import + use) — YES
- `customRange: null` in FilterPanel.tsx: 2 matches (preset pick + Reset) — YES
- `filters.recency === 'custom'` in FilterPanel.tsx: 2 matches (Select value + label) — YES
- No `text-xs` in new component files — YES
- No raw hex colors in new component files — YES
- `npm run lint`: PASSED
- `npx tsc -p tsconfig.app.json --noEmit`: PASSED (0 errors)
- `npm test -- --run`: PASSED (611/611)
- `npm run knip`: PASSED (0 issues)

## Self-Check: PASSED
