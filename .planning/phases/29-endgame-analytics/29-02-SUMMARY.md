---
phase: "29"
plan: "02"
subsystem: frontend
tags: [endgames, charts, ui, tanstack-query, typescript]
dependency_graph:
  requires: ["29-01"]
  provides: ["endgame-frontend-statistics-tab"]
  affects: ["frontend/src/App.tsx"]
tech_stack:
  added: []
  patterns:
    - "URL-driven sub-tab routing (location.pathname)"
    - "TanStack Query hooks with filter params as query keys"
    - "Inline stacked WDL bars with per-row interactivity"
key_files:
  created:
    - frontend/src/types/endgames.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/pages/Endgames.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
decisions:
  - "EndgameWDLChart uses custom per-row buttons instead of Recharts layout to enable click-to-select interactivity and inline conversion/recovery metrics below each bar — Recharts hidden in .sr-only for legend/config context"
  - "Filter sidebar inlines Time Control, Platform, Recency directly; Rated and Opponent in More filters collapsible — avoids FilterPanel as-is since it renders all fields together"
  - "color and matchSide fields fixed in FilterState but not exposed in UI — endgame stats are color-agnostic per D-02"
  - "isActive() helper in App.tsx extended to handle /endgames/* prefix matching"
  - "ProtectedLayout suppresses MobileHeader for /endgames/* routes (same pattern as /openings/*)"
metrics:
  duration: "~20 minutes"
  completed: "2026-03-26T09:49:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 2
---

# Phase 29 Plan 02: Frontend Endgames Statistics Tab Summary

Endgames page frontend with Statistics sub-tab featuring stacked WDL bars and inline conversion/recovery metrics per category, URL-driven routing, filter sidebar without color filter, and category selection state.

## What Was Built

### Task 1: TypeScript types, API client, and hooks

- **`frontend/src/types/endgames.ts`** — `EndgameClass` union type, `ConversionRecoveryStats`, `EndgameCategoryStats`, `EndgameStatsResponse`, `EndgameGamesResponse` — TypeScript mirrors of backend Pydantic schemas
- **`frontend/src/api/client.ts`** — `endgameApi.getStats()` (no color param per D-02) and `endgameApi.getGames()` appended after existing API objects
- **`frontend/src/hooks/useEndgames.ts`** — `useEndgameStats` and `useEndgameGames` TanStack Query hooks; `buildEndgameParams` helper extracts endgame-relevant filters (no color/matchSide)

### Task 2: EndgameWDLChart and Endgames page

- **`frontend/src/components/charts/EndgameWDLChart.tsx`** — Stacked horizontal WDL bars per endgame category, inline conversion/recovery metric text below each bar, click-to-select row highlighting (`bg-muted/50 ring-1 ring-primary/40`), click-to-deselect on same row
- **`frontend/src/pages/Endgames.tsx`** — Full Endgames page with:
  - Two URL-driven sub-tabs at `/endgames/statistics` and `/endgames/games`
  - Redirect from `/endgames` and `/endgames/` to `/endgames/statistics`
  - Desktop: `md:grid-cols-[280px_1fr]` two-column layout with filter sidebar
  - Mobile: collapsible Filters trigger + More filters trigger + tabs
  - Filter sidebar shows Time Control, Platform, Recency directly; Rated and Opponent Type under "More filters" collapsible
  - No color filter anywhere (color/matchSide fixed in state but not rendered)
  - Games tab placeholder — Plan 03 will wire `GameCardList`
- **`frontend/src/App.tsx`** — Added `/endgames/*` route, `TrophyIcon` Endgames nav entry between Openings and Statistics, `ROUTE_TITLES` entry, `isActive` prefix matching for `/endgames`, `ProtectedLayout` suppresses mobile header for endgames routes

## Verification

- `npm run build --prefix frontend` exits 0
- `tsc --noEmit --project frontend/tsconfig.app.json` exits 0
- `EndgameWDLChart` has `data-testid="endgame-wdl-chart"` and per-category `data-testid="endgame-category-{slug}"`
- Endgames page has `data-testid="endgames-page"` and all required testids from UI spec
- No color filter in Endgames page code

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 | c937abc | feat(29-02): add endgame types, API client, and TanStack Query hooks |
| Task 2 | 0bcd922 | feat(29-02): add EndgameWDLChart component, Endgames page, and nav routing |

## Deviations from Plan

### Auto-resolved design decisions

**1. [Rule 2 - Missing Critical Functionality] Inline filter split instead of FilterPanel as-is**

- **Found during:** Task 2 implementation
- **Issue:** The plan noted FilterPanel renders all filters together (including Rated and Opponent Type), but the UI spec requires Time Control/Platform/Recency in main area and Rated/Opponent in "More filters" collapsible.
- **Fix:** Inlined the specific filter controls (Time Control, Platform, Recency) directly in the main sidebar area. Rated and Opponent Type rendered only inside the "More filters" collapsible. Used same visual patterns as FilterPanel for consistency.
- **Files modified:** `frontend/src/pages/Endgames.tsx`

**2. [Rule 1 - Design Choice] Custom per-row buttons for EndgameWDLChart instead of Recharts layout**

- **Found during:** Task 2 implementation
- **Issue:** Recharts `BarChart` with `layout="vertical"` doesn't natively support click events per row combined with inline text below each bar for conversion/recovery metrics.
- **Fix:** Custom `<button>` per category row with inline stacked bar div segments. Recharts `BarChart` hidden in `.sr-only` div for potential chart legend/config use. This approach enables click-to-select interactivity and inline metrics naturally.
- **Files modified:** `frontend/src/components/charts/EndgameWDLChart.tsx`

## Known Stubs

- **Games tab content** — `frontend/src/pages/Endgames.tsx` (~line 196): Games tab shows a placeholder message instead of `GameCardList`. Plan 03 will wire the actual games list with pagination. This is intentional — Plan 02 scope covers Statistics tab only.

## Self-Check: PASSED

- `frontend/src/types/endgames.ts` — FOUND
- `frontend/src/api/client.ts` — FOUND (endgameApi appended)
- `frontend/src/hooks/useEndgames.ts` — FOUND
- `frontend/src/components/charts/EndgameWDLChart.tsx` — FOUND
- `frontend/src/pages/Endgames.tsx` — FOUND
- Commit c937abc — FOUND
- Commit 0bcd922 — FOUND
