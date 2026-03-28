# Phase 29: Endgame Analytics - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

New Endgames page (`/endgames/*`) with two sub-tabs: Statistics and Games. Statistics shows W/D/L rates per endgame category (rook, minor piece, pawn, queen, mixed, pawnless) with inline conversion/recovery stats. Games shows game cards filtered by selected endgame category. Filter sidebar (no chessboard) with time control, platform, recency, rated, and opponent type filters.

Backend: new API endpoints for endgame W/D/L aggregation and conversion/recovery stats per endgame category, plus game listing filtered by endgame type. Game phase and endgame class are derived at query time from `material_count` and `material_signature` (not stored as columns — Phase 26 design decision).

Frontend: new Endgames page mirroring Openings page structure (sub-tabs, filter sidebar), new route in navigation.

</domain>

<decisions>
## Implementation Decisions

### Page Structure
- **D-01:** Two sub-tabs: "Statistics" and "Games", mirroring the Openings page pattern. URL-driven tab state: `/endgames/statistics` and `/endgames/games`.
- **D-02:** Filter sidebar on the left (desktop) / collapsible on mobile. No chessboard. Filters: Time Control, Platform, Recency, plus "More filters" collapsible with Rated and Opponent Type. No color filter — color played is less relevant for endgame analysis than for openings.
- **D-03:** All filters apply to both Statistics and Games sub-tabs.

### Endgame Category Display (Statistics Tab)
- **D-04:** Stacked horizontal bar chart (same visual pattern as the existing "Results by Opening" `WDLBarChart`) with endgame categories as Y-axis labels. Each category shows W/D/L percentage bars plus game count outline bar.
- **D-05:** Categories sorted by game count descending (most-played endgame type first).
- **D-06:** Below each category's W/D/L bar, show inline conversion and recovery metrics: "Conversion: X% (n/m)" and "Recovery: Y% (n/m)".
- **D-07:** Six endgame categories: Rook, Minor Piece, Pawn, Queen, Mixed, Pawnless. Finer material signature drill-down (e.g., KRP vs KR) deferred to future phase (MATFLT-01).

### Conversion & Recovery Stats
- **D-08:** Conversion = win rate in games where the user entered that endgame type with a material advantage (positive `material_imbalance` from the user's perspective at the endgame transition point).
- **D-09:** Recovery = draw+win rate in games where the user entered that endgame type with a material disadvantage.
- **D-10:** Stats displayed inline below each endgame category row, not as a separate section. Shows percentage and game counts (e.g., "85% (34/40)").
- **D-11:** No breakdown by game phase (opening/middlegame/endgame) — single aggregate rate per endgame type is cleaner and more actionable.

### Games Sub-Tab
- **D-12:** User clicks an endgame category in the Statistics tab to select it. Selection persists when switching to the Games tab, which shows game cards for that category.
- **D-13:** All 6 categories always visible in the Statistics tab — selection only affects the Games tab content.
- **D-14:** Reuse the existing `GameCardList` component for displaying games.

### Navigation & Routing
- **D-15:** New top-level nav item "Endgames" between Openings and Statistics. Desktop: Import, Openings, Endgames, Statistics. Mobile bottom bar: same 4 items.
- **D-16:** Route: `/endgames/*` with sub-routes `/endgames/statistics` (default) and `/endgames/games`. Mirrors `/openings/*` pattern.

### Claude's Discretion
- How to derive endgame class from `material_signature` at query time (SQL logic or Python post-processing)
- Game phase threshold logic (material_count + ply boundaries for opening/middlegame/endgame classification)
- Whether to create a generic WDL bar chart component or a new `EndgameWDLChart` that follows the same visual pattern
- Empty state design for users with no endgame data
- Mobile layout details for the inline conversion/recovery metrics
- How to determine the "endgame transition point" for material imbalance (first position classified as endgame in a game)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Position Classification
- `app/services/position_classifier.py` — Pure function that computes `material_count`, `material_signature`, `material_imbalance`, `has_opposite_color_bishops`. Game phase and endgame class derived at query time from these values.

### Database Models
- `app/models/game_position.py` — `GamePosition` model with `material_count`, `material_signature`, `material_imbalance`, `has_opposite_color_bishops` columns (populated during import, Phase 27).

### Existing Chart Components
- `frontend/src/components/charts/WDLBarChart.tsx` — "Results by Opening" stacked bar chart with W/D/L + game count. Visual pattern to replicate for endgame categories (currently coupled to `PositionBookmarkResponse`).
- `frontend/src/components/charts/WinRateChart.tsx` — May be useful for conversion/recovery visualization.

### Filter & Layout Patterns
- `frontend/src/components/filters/FilterPanel.tsx` — Existing filter sidebar with `FilterState` interface. Endgames page needs a subset (no color, no matchSide).
- `frontend/src/pages/Openings.tsx` — Reference for sub-tab structure, filter sidebar layout, desktop/mobile split, and Games tab pattern.
- `frontend/src/App.tsx` lines 43-59 — `NAV_ITEMS`, `BOTTOM_NAV_ITEMS`, `ROUTE_TITLES` arrays and route definitions.

### Game Card Components
- `frontend/src/components/results/GameCardList.tsx` — Reusable game card list for the Games sub-tab.

### Backend Patterns
- `app/routers/stats.py` — Existing stats router pattern.
- `app/repositories/stats_repository.py` — Existing stats repository pattern.
- `app/repositories/game_repository.py` — Has endgame-related query patterns.

### Requirements
- `.planning/REQUIREMENTS.md` — ENDGM-01 through ENDGM-04 (endgame analytics), CONV-01 through CONV-03 (conversion/recovery). Note: CONV requirements reference game phase breakdown which has been superseded — conversion/recovery is now per endgame type instead.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FilterPanel` component: reusable with subset of filters (drop color/matchSide)
- `WDLBarChart`: visual pattern to replicate (stacked bars + game count outline)
- `GameCardList`: directly reusable for Games sub-tab
- `Tabs/TabsList/TabsTrigger/TabsContent` from shadcn/ui: same tab infrastructure as Openings
- `ChartContainer/ChartTooltip/ChartLegend` from shadcn/ui chart: Recharts wrapper

### Established Patterns
- Sub-tab pages use URL-driven state (`location.pathname`) not React state
- Filter state managed via `useState` + `useDebounce` in page component
- Desktop: sidebar + content layout. Mobile: collapsible filters + stacked content
- Both desktop and mobile markup maintained separately (Openings pattern)

### Integration Points
- `NAV_ITEMS` and `BOTTOM_NAV_ITEMS` arrays in `App.tsx` for adding nav entry
- `ROUTE_TITLES` map in `App.tsx` for mobile header
- New route under `<ProtectedLayout>` in `AppRoutes()`
- New API endpoints: likely `/api/endgames/stats` and `/api/endgames/games`
- New repository methods for endgame aggregation queries

</code_context>

<specifics>
## Specific Ideas

- The endgame category chart should follow the exact same visual pattern as the "Results by Opening" WDLBarChart — stacked W/D/L percentage bars with a transparent game count outline bar
- Conversion/recovery metrics displayed inline below each category's bar row, not as a separate section

</specifics>

<deferred>
## Deferred Ideas

- **MATFLT-01 — Material signature drill-down:** Finer-grained endgame breakdown by specific material configuration (e.g., KRP vs KR within rook endgames). Already tracked as a future requirement in REQUIREMENTS.md.
- **Conversion/recovery on Global Stats:** Could also surface aggregate conversion/recovery rates (across all endgame types) on the Global Stats page in a future phase.

</deferred>

---

*Phase: 29-endgame-analytics*
*Context gathered: 2026-03-26*
