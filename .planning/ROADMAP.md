# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- ✅ **v1.4 Improvements** — Phase 24 (shipped 2026-03-22)
- ✅ **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33 (shipped 2026-03-28)
- 🚧 **v1.6 UI Polish & Improvements** — Phases 34-37 (in progress)

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2024-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2024-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2024-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2024-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2024-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2024-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2024-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2024-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2024-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2024-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2024-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2024-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2024-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2024-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2024-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2024-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2024-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2024-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2024-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2024-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2024-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2024-03-21

</details>

<details>
<summary>✅ v1.3 Project Launch (Phases 20-23) — SHIPPED 2026-03-22</summary>

- [x] Phase 20: Rename & Branding (2/2 plans) — completed 2026-03-21
- [x] Phase 21: Docker & Deployment (2/2 plans) — completed 2026-03-21
- [x] Phase 22: CI/CD & Monitoring (2/2 plans) — completed 2026-03-21
- [x] Phase 23: Launch Readiness (4/4 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.4 Improvements (Phase 24) — SHIPPED 2026-03-22</summary>

- [x] Phase 24: Web Analytics (2/2 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.5 Game Statistics & Endgame Analysis (Phases 26-33) — SHIPPED 2026-03-28</summary>

- [x] Phase 26: Position Classifier & Schema (2/2 plans) — completed 2026-03-23
- [x] Phase 27: Import Wiring & Backfill (2/2 plans) — completed 2026-03-24
- [x] Phase 27.1: Optimize game_positions columns (via quick tasks) — completed 2026-03-26
- [x] Phase 28: Engine Analysis Import (2/3 plans, 28-03 deferred) — completed 2026-03-25
- [x] Phase 28.1: Import lichess analysis metrics (1/1 plan) — completed 2026-03-26
- [x] Phase 29: Endgame Analytics (3/3 plans) — completed 2026-03-26
- [x] Phase 31: Endgame classification redesign (2/2 plans) — completed 2026-03-26
- [x] Phase 32: Endgame Performance Charts (3/3 plans) — completed 2026-03-27
- [x] Phase 33: Homepage, README & SEO Update (3/3 plans) — completed 2026-03-28

</details>

## v1.6 UI Polish & Improvements

- [x] **Phase 34: Theme Improvements** — Centralize theme constants, charcoal containers with noise texture, filter button layout, consistent WDL chart styling, active subtab highlighting (completed 2026-03-28)
- [x] **Phase 35: WDL Chart Refactoring** — Create shared WDL chart component based on endgame charts, replace all inconsistent WDL charts (custom and Recharts), clean up unused code (completed 2026-03-28)
- [x] **Phase 36: Most Played Openings** — Add "Most Played Openings" sections (White/Black) to Opening Statistics subtab with top 5 openings as WDL charts, ECO codes, minimum 10 games threshold (completed 2026-03-28)
- [ ] **Phase 37: Openings Reference Table & Most Played Openings Redesign** — Create openings DB table from TSV dataset with PGN/FEN/ply_count, redesign most played openings with filter support, dedicated table UI, minimap popover, SQL-side WDL aggregation, top 10

## Phase Details

### Phase 37: Openings Reference Table & Most Played Openings Redesign
**Goal**: Create an openings reference table from the TSV dataset, then redesign the Most Played Openings feature with filter support, dedicated table UI, opening PGN/FEN display, minimap popover, and SQL-side WDL aggregation
**Depends on**: Phase 36 (Most Played Openings baseline)
**Requirements**: ORT-01, ORT-02, ORT-03, ORT-04, ORT-05
**Success Criteria** (what must be TRUE):
  1. openings table contains all ~3641 rows from TSV with correct ply_count and fen values computed via python-chess
  2. Deduplicated view returns one row per (eco, name) pair
  3. Endpoint returns top 10 openings per color with WDL stats computed in SQL, filtered by recency/time_control/platform/rated/opponent_type, excluding openings below ply threshold
  4. Frontend renders a dedicated table with ECO/name/PGN, game count link, and mini WDL bar per row
  5. Hovering/tapping a row shows a minimap popover of the opening position
**Plans**: 0 plans
**UI hint**: yes

Plans:
- [ ] TBD (run /gsd:plan-phase 37 to break down)

### Phase 36: Most Played Openings
**Goal**: Opening Statistics subtab shows the user's top 5 most played openings for White and Black as WDL charts, with ECO codes and a minimum 10 games threshold
**Depends on**: Phase 35 (WDL chart infrastructure)
**Requirements**: MPO-01, MPO-02, MPO-03, MPO-04
**Success Criteria** (what must be TRUE):
  1. "Most Played Openings: White" and "Most Played Openings: Black" sections appear at the top of the Opening Statistics subtab in a shared charcoal container
  2. Each section lists the top 5 openings by game count, based on opening_eco/opening_name from the games table
  3. Openings with fewer than 10 games are excluded; if no openings meet the threshold, an explanatory message is shown
  4. Openings are displayed as WDL charts (same component as "Results by Opening") with ECO code in parentheses in the title
**Plans**: 1 plan
**UI hint**: yes

Plans:
- [x] 36-01-PLAN.md — Backend endpoint + frontend rendering for most played openings by color

### Phase 35: WDL Chart Refactoring
**Goal**: All WDL charts (except move list) use a single shared component, eliminating inconsistent custom and Recharts implementations
**Depends on**: Phase 34 (theme infrastructure)
**Requirements**: WDL-01, WDL-02, WDL-03, WDL-04
**Success Criteria** (what must be TRUE):
  1. A shared WDL chart component exists with configurable title, games link, and optional game count bar
  2. All WDL charts across the app (Results by Time Control, Results by Color, Results by Opening, endgame type charts, etc.) use the shared component — except the moves list in the Moves tab
  3. No unused WDL-related constants, CSS classes, or Recharts chart code remains
  4. Visual appearance matches the current endgame type WDL charts (the reference implementation)
**Plans**: 2 plans

Plans:
- [x] 35-01-PLAN.md — Shared WDLChartRow component + WDLRowData type, reimplement WDLBar as wrapper
- [x] 35-02-PLAN.md — Replace GlobalStatsCharts/WDLBarChart/EndgameWDLChart/EndgamePerformanceSection with WDLChartRow, delete dead code

### Phase 34: Theme Improvements
**Goal**: Users see a visually consistent, polished UI with centralized theme management across all pages
**Depends on**: Nothing (first phase of v1.6)
**Requirements**: THEME-01, THEME-02, THEME-03, THEME-04, THEME-05
**Success Criteria** (what must be TRUE):
  1. All theme-relevant constants (container colors, spacing, chart styles) are defined in theme.ts and CSS variables — no ad-hoc color values scattered across components
  2. Content containers appear with a charcoal background and subtle noise texture, visually distinct from the page background
  3. Filter buttons in the sidebar are laid out horizontally, spanning the full available width with even spacing
  4. WDL charts (both custom bar and Recharts-based) share identical corner rounding and rendering style across all pages
  5. The active subtab is clearly highlighted so the user always knows which sub-section they are viewing
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 34-01-PLAN.md — Theme infrastructure: CSS variables, charcoal texture class, tabs brand variant, filter layout, WDL chart rounding
- [x] 34-02-PLAN.md — Apply charcoal containers to pages, collapsible styling, nav header polish, subtab highlighting, visual checkpoint

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2024-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2024-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2024-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2024-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2024-03-13 |
| 6. Browser Automation | v1.0 | 2/2 | Complete | 2024-03-13 |
| 7. Game Statistics | v1.0 | 3/3 | Complete | 2024-03-14 |
| 8. Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2024-03-14 |
| 9. Game Cards & Import | v1.0 | 8/8 | Complete | 2024-03-15 |
| 10. Auto Bookmarks | v1.0 | 4/4 | Complete | 2024-03-15 |
| 11. Schema & Pipeline | v1.1 | 1/1 | Complete | 2024-03-16 |
| 12. Next-Moves API | v1.1 | 2/2 | Complete | 2024-03-16 |
| 13. Move Explorer UI | v1.1 | 2/2 | Complete | 2024-03-16 |
| 14. UI Restructuring | v1.1 | 3/3 | Complete | 2024-03-17 |
| 15. Enhanced Import | v1.1 | 3/3 | Complete | 2024-03-18 |
| 16. Game Card UI | v1.1 | 3/3 | Complete | 2024-03-18 |
| 17. PWA Foundation + Dev Workflow | v1.2 | 1/1 | Complete | 2024-03-20 |
| 18. Mobile Navigation | v1.2 | 1/1 | Complete | 2024-03-20 |
| 19. Mobile UX Polish + Install Prompt | v1.2 | 3/3 | Complete | 2024-03-21 |
| 20. Rename & Branding | v1.3 | 2/2 | Complete | 2026-03-21 |
| 21. Docker & Deployment | v1.3 | 2/2 | Complete | 2026-03-21 |
| 22. CI/CD & Monitoring | v1.3 | 2/2 | Complete | 2026-03-21 |
| 23. Launch Readiness | v1.3 | 4/4 | Complete | 2026-03-22 |
| 24. Web Analytics | v1.4 | 2/2 | Complete | 2026-03-22 |
| 26. Position Classifier & Schema | v1.5 | 2/2 | Complete    | 2026-03-23 |
| 27. Import Wiring & Backfill | v1.5 | 2/2 | Complete    | 2026-03-24 |
| 28. Engine Analysis Import | v1.5 | 2/3 | Complete (03 deferred) | 2026-03-25 |
| 28.1. Import lichess analysis metrics | v1.5 | 1/1 | Complete | 2026-03-26 |
| 29. Endgame Analytics | v1.5 | 3/3 | Complete | 2026-03-26 |
| 27.1. Optimize game_positions columns | v1.5 | N/A | Complete | 2026-03-26 |
| 31. Endgame classification redesign | v1.5 | 2/2 | Complete | 2026-03-26 |
| 32. Endgame Performance Charts | v1.5 | 3/3 | Complete | 2026-03-27 |
| 33. Homepage, README & SEO Update | v1.5 | 3/3 | Complete | 2026-03-28 |
| 34. Theme Improvements | v1.6 | 2/2 | Complete    | 2026-03-28 |
| 35. WDL Chart Refactoring | v1.6 | 2/2 | Complete   | 2026-03-28 |
| 36. Most Played Openings | v1.6 | 1/1 | Complete    | 2026-03-28 |
| 37. Openings Reference Table & Redesign | v1.6 | 0/0 | Not Started | — |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.2: Python Static Type Checker in CI (BACKLOG)

**Goal:** Add a Python static type checker to the CI pipeline to catch type-level bugs (typos, bare `str` where `Literal` is needed, wrong function names) that ruff cannot detect. Evaluate [ty](https://docs.astral.sh/ty/) (from Astral, same team as ruff/uv) vs pyright vs mypy.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

