# Requirements: Chessalytics

**Defined:** 2026-03-11
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.0 Requirements (Complete)

All 21 v1.0 requirements shipped. See MILESTONES.md for details.

- [x] IMP-01 through IMP-06 (Import pipeline)
- [x] ANL-01 through ANL-03 (Analysis)
- [x] FLT-01 through FLT-04 (Filters)
- [x] RES-01 through RES-03 (Results display)
- [x] AUTH-01, AUTH-02 (Auth & multi-user)
- [x] INFRA-01 through INFRA-03 (Infrastructure)

## v1.1 Requirements

Requirements for milestone v1.1: Opening Explorer & UI Restructuring.

### Move Explorer

- [x] **MEXP-01**: game_positions table has a `move_san` column storing the SAN of the move played from each position (NULL at final position and ply 0)
- [x] **MEXP-02**: game_positions has a covering index on `(user_id, full_hash, move_san)` for fast aggregation
- [x] **MEXP-03**: Import pipeline populates `move_san` for every position during game import
- [x] **MEXP-04**: Backend endpoint returns next moves for a given position hash with game count and W/D/L stats per move, respecting all existing filters
- [x] **MEXP-05**: Transpositions are handled correctly — each game counted only once per move even if position reached via different move orders
- [x] **MEXP-06**: Move Explorer tab displays a 3-column table (Move, Games, Results) with a W/D/L stacked bar in the Results column
- [x] **MEXP-07**: Clicking a move row advances the board to the resulting position and refreshes the explorer with the new position's next moves
- [x] **MEXP-10**: Next-moves endpoint returns transposition count (total games reaching the resulting position via any move order) alongside direct game count
- [x] **MEXP-11**: Move Explorer shows a transposition warning icon with hover tooltip when the resulting position has been reached through other move orders
- [x] **MEXP-12**: Chessboard displays transparent arrows for all next moves from the current position, with opacity proportional to move frequency

### UI Restructuring

- [x] **UIRS-01**: Openings tab has three sub-tabs: Move Explorer, Games, Statistics — with shared filter sidebar (board, position bookmarks, more filters)
- [x] **UIRS-02**: Filter state persists when switching between sub-tabs (no reset on tab change)
- [x] **UIRS-03**: Dedicated Import page replaces the import modal, showing import controls, username management, and sync functionality
- [x] **UIRS-04**: Navigation updated: Import | Openings | Rating | Global Stats

### Chart Consolidation and Polish

- [x] **CHRT-01**: Rating tab removed from nav; rating charts appear above Results by Time Control on Global Stats page
- [x] **CHRT-02**: Platform filter (chess.com / lichess) added to Global Stats page, filtering both rating and WDL charts
- [x] **CHRT-03**: Rating charts show one chart per platform; each chart shows per-time-control lines (conditionally hidden when platform filter excludes it)
- [x] **CHRT-04**: Consistent monthly aggregation across all time-series charts (RatingChart uses monthly buckets like WinRateChart)
- [x] **CHRT-05**: Chart titles added to Statistics sub-tab of Openings tab (WDLBarChart and WinRateChart)

### Enhanced Game Import Data

- [x] **EIGD-01**: game_positions table has a `clock_seconds` column storing seconds remaining from PGN `%clk` annotations (NULL when not present)
- [x] **EIGD-02**: games table has `termination_raw` (platform string) and `termination` (normalized bucket: checkmate, resignation, timeout, draw, abandoned, unknown) columns
- [x] **EIGD-03**: Time control bucket boundary fixed: 180+0 classified as blitz (not bullet), matching chess.com/lichess conventions
- [x] **EIGD-04**: Import sync boundary scoped by username — importing a second username on the same platform fetches full history independently
- [x] **EIGD-05**: Data isolation between users — logging out clears TanStack Query cache so another user sees only their own data
- [x] **EIGD-06**: Google SSO login updates `last_login` timestamp on the User record
- [x] **EIGD-07**: Analysis API `GameRecord` response includes `termination` and `time_control_str` fields
- [x] **EIGD-08**: Game cards display normalized termination reason and exact time control (e.g. "Blitz · 10+5")

### Game Card UI Improvements

- **GCUI-01**: `result_fen` column added to games table, computed at import time from `board.board_fen()` at end of PGN replay
- **GCUI-02**: `result_fen` included in `GameRecord` API response schema (backend and frontend types)
- **GCUI-03**: Game cards display 3-row layout: Row 1 (result badge + players + platform), Row 2 (opening name with BookOpen icon), Row 3 (metadata with Clock/Calendar/Swords/Hash icons)
- **GCUI-04**: Null metadata fields omitted entirely (no NaN for daily games, no dash placeholders) — opening null shows "Unknown Opening"
- **GCUI-05**: Game cards show hover minimap (120px MiniBoard) on desktop and tap-to-expand inline minimap on mobile, oriented from user perspective

## Future Requirements

### Move Explorer Enhancements

- **MEXP-08**: Move sorting by frequency, win rate, or alphabetical
- **MEXP-09**: Show resulting position FEN/thumbnail on move hover

### Analysis Enhancements

- **ANL-04**: User can choose strict move order matching vs any-order position matching
- **ANL-05**: User sees additional stats (average opponent rating, performance over time)
- **ANL-06**: Human-like engine analysis — engine evaluation filtered by human move plausibility at target Elo

### Import Enhancements

- **IMP-07**: Optional lichess OAuth token for faster imports
- **IMP-08**: Manual PGN file upload

## Out of Scope

| Feature | Reason |
|---------|--------|
| Visual opening tree (branching diagram) | Complex to render, misleading at small sample sizes, flat table is faster to read |
| Engine evaluation per move | Opens Stockfish integration rabbit hole, undermines personal-stats positioning |
| Move sorting options | Frequency-first is standard; sorting is a polish feature for later |
| In-app game viewer/replay | Link to source platform instead |
| Mobile app | Web-first; responsive design sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MEXP-01 | Phase 11 | Complete |
| MEXP-02 | Phase 11 | Complete |
| MEXP-03 | Phase 11 | Complete |
| MEXP-04 | Phase 12 | Complete |
| MEXP-05 | Phase 12 | Complete |
| MEXP-06 | Phase 13 | Complete |
| MEXP-07 | Phase 13 | Complete |
| MEXP-10 | Phase 12 | Complete |
| MEXP-11 | Phase 13 | Complete |
| MEXP-12 | Phase 13 | Complete |
| UIRS-01 | Phase 14 | Complete |
| UIRS-02 | Phase 14 | Complete |
| UIRS-03 | Phase 14 | Complete |
| UIRS-04 | Phase 14 | Complete |
| CHRT-01 | Phase 15 (old) | Complete |
| CHRT-02 | Phase 15 (old) | Complete |
| CHRT-03 | Phase 15 (old) | Complete |
| CHRT-04 | Phase 15 (old) | Complete |
| CHRT-05 | Phase 15 (old) | Complete |
| EIGD-01 | Phase 15 | Complete |
| EIGD-02 | Phase 15 | Complete |
| EIGD-03 | Phase 15 | Complete |
| EIGD-04 | Phase 15 | Complete |
| EIGD-05 | Phase 15 | Complete |
| EIGD-06 | Phase 15 | Complete |
| EIGD-07 | Phase 15 | Complete |
| EIGD-08 | Phase 15 | Complete |
| GCUI-01 | Phase 16 | Planned |
| GCUI-02 | Phase 16 | Planned |
| GCUI-03 | Phase 16 | Planned |
| GCUI-04 | Phase 16 | Planned |
| GCUI-05 | Phase 16 | Planned |

**Coverage:**
- v1.1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-18 after Phase 16 planning (Game Card UI Improvements)*
