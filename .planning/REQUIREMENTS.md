# Requirements: FlawChess

**Defined:** 2026-03-28
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.6 Requirements

Requirements for v1.6 — UI Polish & Improvements.

### Theme

- [x] **THEME-01**: User sees all visual constants (container colors, spacing, chart styles) centralized in theme.ts and CSS variables
- [x] **THEME-02**: User sees content containers with charcoal background and subtle SVG feTurbulence noise texture, visually distinct from page background
- [x] **THEME-03**: User sees filter buttons in sidebar spaced horizontally across full available width
- [x] **THEME-04**: User sees consistent WDL chart styling (unified corners and rendering) across all chart types (custom and Recharts-based)
- [x] **THEME-05**: User sees clear visual highlighting on the active subtab

### WDL Chart Refactoring

- [x] **WDL-01**: A shared WDL chart component exists with configurable title, games link, and optional game count bar
- [x] **WDL-02**: All WDL charts across the app (Results by Time Control, Results by Color, Results by Opening, endgame type charts) use the shared component — except the moves list in the Moves tab
- [x] **WDL-03**: No unused WDL-related constants, CSS classes, or Recharts bar chart code remains
- [x] **WDL-04**: Visual appearance of all WDL charts matches the current endgame type WDL charts (glass overlay, inline legend, game count bars)

### Most Played Openings

- [x] **MPO-01**: "Most Played Openings" section with White and Black subsections appears at the top of the Opening Statistics subtab in a shared charcoal container
- [x] **MPO-02**: Each subsection lists the top 5 openings by game count, based on opening_eco/opening_name from the games table
- [x] **MPO-03**: Openings with fewer than 10 games are excluded; if no openings meet the threshold, an explanatory message is shown
- [x] **MPO-04**: Openings are displayed as WDL charts (same WDLChartRow component) with ECO code in parentheses in the title label

### Openings Reference Table & Redesign

- [x] **ORT-01**: `openings` table contains all ~3641 rows from TSV with correct `ply_count` and `fen` values computed via python-chess
- [x] **ORT-02**: Deduplicated view returns one row per `(eco, name)` pair
- [ ] **ORT-03**: Endpoint returns top 10 openings per color with WDL stats computed in SQL, filtered by recency/time_control/platform/rated/opponent_type, excluding openings below ply threshold
- [x] **ORT-04**: Frontend renders a dedicated table with ECO/name/PGN, game count link, and mini WDL bar per row
- [x] **ORT-05**: Hovering/tapping a row shows a minimap popover of the opening position

### Opening Statistics & Bookmark Suggestions Rework

- [x] **STAT-01**: Statistics tab sections appear in order: Results by Opening, Win Rate Over Time, Most Played Openings as White, Most Played Openings as Black
- [x] **STAT-02**: When no bookmarks exist, Results by Opening and Win Rate Over Time charts show data from top 3 most-played openings per color (white with played-as-white filter, black with played-as-black filter)
- [ ] **STAT-03**: Bookmark suggestions derive from most-played openings data (no backend suggestions API call), skip already-bookmarked positions, show fallback message when all are bookmarked
- [ ] **STAT-04**: Each bookmark card has a chart-enable toggle (default: enabled, persisted in localStorage) controlling inclusion in Results by Opening and Win Rate Over Time charts
- [ ] **STAT-05**: Bookmark card layout: bigger minimap (~72px), button row below piece filter with chart toggle (left), load (middle), delete (right)
- [ ] **STAT-06**: Position Bookmarks popover explains Piece filter and chart-enable toggle functionality

## Future Requirements

### Pawn Structure Analysis

- **PAWN-01**: System computes pawn structure hash for grouping similar structures (e.g., Carlsbad, isolated d-pawn)

### Tactical Features

- **TACT-01**: System detects per-position tactical flags (passed pawn, opposite-colored bishops, open file)

### Material Config Filter

- **MATFLT-01**: User can filter endgame stats by specific material signature (e.g., KRP vs KR)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dark/light mode toggle | Not requested for v1.6; current dark theme is the only mode |
| Fine borders on containers | Explicitly excluded — charcoal background with texture only |
| Image-based background textures | Use lightweight SVG feTurbulence instead of asset files |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| THEME-01 | Phase 34 | Complete |
| THEME-02 | Phase 34 | Complete |
| THEME-03 | Phase 34 | Complete |
| THEME-04 | Phase 34 | Complete |
| THEME-05 | Phase 34 | Complete |
| WDL-01 | Phase 35 | Complete |
| WDL-02 | Phase 35 | Complete |
| WDL-03 | Phase 35 | Complete |
| WDL-04 | Phase 35 | Complete |
| MPO-01 | Phase 36 | Complete |
| MPO-02 | Phase 36 | Complete |
| MPO-03 | Phase 36 | Complete |
| MPO-04 | Phase 36 | Complete |
| ORT-01 | Phase 37 | Complete |
| ORT-02 | Phase 37 | Complete |
| ORT-03 | Phase 37 | Not started |
| ORT-04 | Phase 37 | Complete |
| ORT-05 | Phase 37 | Complete |
| STAT-01 | Phase 38 | Not started |
| STAT-02 | Phase 38 | Not started |
| STAT-03 | Phase 38 | Not started |
| STAT-04 | Phase 38 | Not started |
| STAT-05 | Phase 38 | Not started |
| STAT-06 | Phase 38 | Not started |

**Coverage:**
- v1.6 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-29 after Phase 38 planning*
