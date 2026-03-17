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

**Coverage:**
- v1.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-16 after milestone v1.1 roadmap creation*
