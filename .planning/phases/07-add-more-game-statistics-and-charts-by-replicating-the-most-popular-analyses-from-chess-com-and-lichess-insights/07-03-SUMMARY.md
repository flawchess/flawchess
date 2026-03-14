---
phase: 07-add-more-game-statistics-and-charts
plan: 03
subsystem: ui
tags: [react, typescript, recharts, shadcn, stats, rating-history, wdl, charts]

# Dependency graph
requires:
  - phase: 07-01
    provides: GET /stats/rating-history and GET /stats/global backend endpoints
  - phase: 07-02
    provides: /rating and /global-stats placeholder routes and navigation structure
provides:
  - Full Rating page with two per-platform LineCharts (Chess.com + Lichess), togglable TC lines, recency filter
  - Full Global Stats page with WDL stacked horizontal bar charts by time control and color, recency filter
  - frontend/src/types/stats.ts with RatingDataPoint, RatingHistoryResponse, WDLByCategory, GlobalStatsResponse interfaces
  - frontend/src/api/client.ts statsApi with getRatingHistory and getGlobalStats methods
  - frontend/src/hooks/useStats.ts with useRatingHistory and useGlobalStats TanStack Query hooks
  - frontend/src/components/stats/RatingChart.tsx — per-platform LineChart with 4 TC lines
  - frontend/src/components/stats/GlobalStatsCharts.tsx — WDL stacked bars by time control and color
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RatingChart uses flat row-per-game data array where each row has only one TC key set — Recharts renders gaps naturally for absent keys"
    - "WDLCategoryChart is a local component within GlobalStatsCharts.tsx — avoids exporting non-component values while keeping chart logic co-located"
    - "connectNulls=true on rating Lines — connect same-TC rating points across dates without other TCs creating gaps"

key-files:
  created:
    - frontend/src/types/stats.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/components/stats/RatingChart.tsx
    - frontend/src/components/stats/GlobalStatsCharts.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/pages/Rating.tsx
    - frontend/src/pages/GlobalStats.tsx

key-decisions:
  - "RatingChart data model: flat array of {date, [tc]: rating} rows (one per game) — each row has only one TC key, Recharts handles gaps between TC lines naturally"
  - "WDLCategoryChart as local component (not exported) — avoids react-refresh/only-export-components lint violation while keeping chart logic co-located in GlobalStatsCharts.tsx"
  - "Pre-existing lint errors in shadcn/ui files (tabs.tsx, toggle.tsx, badge.tsx, button.tsx) and FilterPanel.tsx are out of scope — no new lint errors introduced"

patterns-established:
  - "Stats pages: useState(null) for recency, pass to hook, hook normalizes 'all'->null before sending to API"

requirements-completed: [STATS-03, STATS-04]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 7 Plan 03: Rating and Global Stats Frontend Pages Summary

**Recharts LineChart rating-over-time pages (Chess.com + Lichess with TC toggle) and WDL stacked bar Global Stats page wired to backend stats endpoints via TanStack Query hooks**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T09:33:05Z
- **Completed:** 2026-03-14T09:35:59Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created TypeScript interfaces matching backend Pydantic schemas (RatingDataPoint, RatingHistoryResponse, WDLByCategory, GlobalStatsResponse)
- Added statsApi to api/client.ts with getRatingHistory and getGlobalStats (follow existing bookmarksApi pattern)
- Created useRatingHistory and useGlobalStats TanStack Query hooks in useStats.ts
- Implemented RatingChart: per-platform LineChart with 4 TC lines (bullet/blitz/rapid/classical), togglable via legend click, connectNulls=true, empty state per platform
- Implemented GlobalStatsCharts: WDL stacked horizontal bar charts for "Results by Time Control" and "Results by Color", empty state per chart
- Replaced Rating.tsx placeholder with full implementation: two RatingChart instances + recency Select filter
- Replaced GlobalStats.tsx placeholder with full implementation: GlobalStatsCharts + recency Select filter
- All interactive elements have data-testid attributes per CLAUDE.md Browser Automation Rules

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript types, API client, and hooks for stats** - `9cc99d9` (feat)
2. **Task 2: Rating page with per-platform rating charts and Global Stats page with WDL charts** - `94606ab` (feat)

## Files Created/Modified
- `frontend/src/types/stats.ts` - RatingDataPoint, RatingHistoryResponse, WDLByCategory, GlobalStatsResponse interfaces
- `frontend/src/api/client.ts` - Added statsApi with getRatingHistory and getGlobalStats
- `frontend/src/hooks/useStats.ts` - useRatingHistory and useGlobalStats TanStack Query hooks
- `frontend/src/components/stats/RatingChart.tsx` - Per-platform LineChart with 4 TC lines, legend toggle, empty state
- `frontend/src/components/stats/GlobalStatsCharts.tsx` - WDL stacked bar charts for TC and color categories, local WDLCategoryChart
- `frontend/src/pages/Rating.tsx` - Full Rating page with two RatingChart instances and recency filter
- `frontend/src/pages/GlobalStats.tsx` - Full Global Stats page with GlobalStatsCharts and recency filter

## Decisions Made
- RatingChart data model: flat array of {date, [tc]: rating} rows (one per game) where each row has only one TC key set — Recharts handles gaps between TC lines naturally without needing a merge step
- WDLCategoryChart defined as local (unexported) component inside GlobalStatsCharts.tsx — avoids react-refresh/only-export-components lint violation while keeping chart logic co-located
- Pre-existing lint errors in shadcn/ui files (tabs.tsx, toggle.tsx, badge.tsx, button.tsx) and FilterPanel.tsx are out of scope per CLAUDE.md deviation rules — no new lint errors introduced by this plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing ESLint `react-refresh/only-export-components` errors in shadcn/ui component files (badge.tsx, button.tsx, tabs.tsx, toggle.tsx) and FilterPanel.tsx — out of scope, not introduced by this plan. All plan-created files pass lint with zero warnings.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 7 is complete — all 3 plans done
- Rating and Global Stats pages are fully implemented and wired to backend
- Stats.tsx dead code can be cleaned up now (noted in STATE.md)

---
*Phase: 07-add-more-game-statistics-and-charts*
*Completed: 2026-03-14*

## Self-Check: PASSED

All files present. All commits verified: 9cc99d9, 94606ab.
