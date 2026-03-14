---
phase: quick-19
plan: 01
subsystem: ui
tags: [recharts, react, typescript, rating-chart]

requires: []
provides:
  - Adaptive equal-distance x-axis ticks in RatingChart (numeric timestamp axis)
affects: []

tech-stack:
  added: []
  patterns:
    - "Numeric timestamp x-axis in Recharts: use type='number' scale='time' with dateTs field and computeXTicks helper"

key-files:
  created: []
  modified:
    - frontend/src/components/stats/RatingChart.tsx

key-decisions:
  - "Numeric timestamp x-axis (type='number' scale='time') over category string axis — Recharts places ticks at exact timestamp positions without duplicating labels"
  - "computeXTicks generates first-of-month UTC timestamps at adaptive intervals (1/2/3/6/12 months) based on data span"
  - "Tooltip label formatted from dateTs number to full readable date (e.g. Mar 14, 2026)"

patterns-established:
  - "RatingChart adaptive x-axis: dateTs numeric field + computeXTicks + domain=[minTs,maxTs]"

requirements-completed: [QUICK-19]

duration: 5min
completed: 2026-03-14
---

# Quick-19: Fix X-Axis in Rating Charts — Adaptive Equal-Distance Ticks

**Numeric timestamp x-axis with adaptive monthly/quarterly/yearly tick intervals eliminates repeated month labels in RatingChart**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T21:57:21Z
- **Completed:** 2026-03-14T22:02:00Z
- **Tasks:** 1 (+ 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Replaced category string x-axis with numeric timestamp axis (`type="number"` `scale="time"`)
- Added `dateTs` field (millisecond timestamp) to each chartData row
- Implemented `computeXTicks()` helper that picks tick interval adaptively (1, 2, 3, 6, or 12 months) based on data span
- Updated tooltip to format `dateTs` number as a readable date string ("Mar 14, 2026")
- Removed old `formatDate` string-based helper; replaced with `formatTs` (timestamp-based)

## Task Commits

1. **Task 1: Implement adaptive equal-distance x-axis ticks** - `c997dcc` (feat)

**Plan metadata:** pending final docs commit

## Files Created/Modified

- `frontend/src/components/stats/RatingChart.tsx` - Numeric timestamp x-axis with adaptive tick computation

## Decisions Made

- **Numeric timestamp approach over category snap-to-nearest:** Using `type="number"` `scale="time"` lets Recharts place ticks at exact positions without requiring tick values to match actual data dates. This is cleaner than the category-string approach of snapping ideal ticks to nearest data points.
- **UTC-based tick generation:** `computeXTicks` uses `Date.UTC()` so tick boundaries are always the 1st of the month at midnight UTC, regardless of local timezone.
- **Adaptive interval thresholds:** <=6 months = monthly, <=18 = bimonthly, <=36 = quarterly, <=72 = semi-annual, >72 = annual.

## Deviations from Plan

None - plan executed exactly as written. Used the preferred "numeric approach" specified in the plan.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RatingChart x-axis now shows evenly spaced, non-repeating date labels
- Ready for human visual verification via Task 2 checkpoint

---
*Phase: quick-19*
*Completed: 2026-03-14*
