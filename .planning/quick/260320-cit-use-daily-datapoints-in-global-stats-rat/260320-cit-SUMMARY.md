---
phase: quick-260320-cit
plan: "01"
subsystem: frontend
tags: [charts, rating, granularity, ux]
dependency_graph:
  requires: []
  provides: [adaptive-granularity-rating-chart]
  affects: [GlobalStatsPage]
tech_stack:
  added: []
  patterns: [adaptive-date-granularity, ISO-week-bucketing]
key_files:
  created: []
  modified:
    - frontend/src/components/stats/RatingChart.tsx
decisions:
  - "ISO week start (Monday) computed via UTC date arithmetic to avoid DST shifts"
  - "determineGranularity uses data array span from first to last date point"
  - "chartData useMemo returns { chartData, granularity } so tooltip and XAxis share the same granularity value"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-20"
  tasks_completed: 1
  files_modified: 1
---

# Phase quick-260320-cit Plan 01: Adaptive Granularity Rating Chart Summary

**One-liner:** Daily/weekly/monthly adaptive grouping in RatingChart based on data date span, with matching axis and tooltip label formats.

## What Was Built

Added adaptive date granularity to `RatingChart.tsx`:

- `determineGranularity(data)`: computes span in days between first and last data point — daily for < 365 days, weekly for 1-3 years, monthly for 3+ years.
- `getBucketKey(dateStr, granularity)`: maps a date string to its bucket key — YYYY-MM-DD for day, ISO week Monday for week, YYYY-MM for month.
- `formatBucketLabel(key, granularity)`: formats bucket key for display — "Mar 15" for day/week, "Mar '26" for month.
- Refactored `chartData` useMemo to return `{ chartData, granularity }` so both XAxis `tickFormatter` and tooltip `content` use the same granularity.
- Updated XAxis `dataKey` from `"month"` to `"bucket"`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add adaptive granularity logic to RatingChart | 5c7fa4a | frontend/src/components/stats/RatingChart.tsx |

## Verification

- `npx tsc --noEmit`: no errors
- `npm run build`: succeeded

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- File exists: frontend/src/components/stats/RatingChart.tsx — FOUND
- Commit 5c7fa4a — FOUND
