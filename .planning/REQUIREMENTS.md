# Requirements: Chessalytics

**Defined:** 2026-03-11
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Import

- [x] **IMP-01**: User can import games from chess.com by entering their username
- [x] **IMP-02**: User can import games from lichess by entering their username
- [x] **IMP-03**: User can re-sync to fetch only new games since last import (incremental)
- [x] **IMP-04**: User sees import progress and status while games are being fetched
- [x] **IMP-05**: All available game metadata is stored (PGN, time control, rated flag, result, opponent, color, platform URL, timestamps)
- [x] **IMP-06**: Position hashes (white, black, full Zobrist) are precomputed and stored for every half-move at import time

### Analysis

- [ ] **ANL-01**: User can specify a target position by playing moves on an interactive chess board
- [x] **ANL-02**: User can filter position matches by white pieces only, black pieces only, or both sides
- [x] **ANL-03**: User sees win/draw/loss counts and percentages for all matching games

### Filters

- [x] **FLT-01**: User can filter analysis results by time control (bullet, blitz, rapid, classical)
- [x] **FLT-02**: User can filter analysis results by rated vs casual games
- [x] **FLT-03**: User can filter analysis results by game recency (week, month, 3 months, 6 months, 1 year, all time)
- [x] **FLT-04**: User can filter analysis results by color played (white or black)

### Results Display

- [x] **RES-01**: User sees a list of matching games showing opponent name, result, date, and time control
- [x] **RES-02**: Each matching game has a clickable link to the game on chess.com or lichess
- [x] **RES-03**: User always sees the total games denominator ("X of Y games matched")

### Auth & Multi-User

- [x] **AUTH-01**: User can create an account and log in
- [x] **AUTH-02**: Each user's games and analyses are isolated (row-level data scoping)

### Infrastructure

- [x] **INFRA-01**: Database schema supports efficient position-based queries using indexed Zobrist hash columns
- [x] **INFRA-02**: Game import runs as a background task (does not block the API server)
- [x] **INFRA-03**: Duplicate games are prevented via unique constraint on (platform, platform_game_id)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Analysis Enhancements

- **ANL-04**: User can choose strict move order matching (exact move sequence) vs any-order (position reached at any point)
- **ANL-05**: User sees additional stats (average opponent rating, performance over time, average game length)

### Import Enhancements

- **IMP-07**: Optional lichess OAuth token for faster imports
- **IMP-08**: Manual PGN file upload

### UX Enhancements

- **RES-04**: User sees ending position thumbnail for each matching game
- **RES-05**: User can enter FEN strings directly as an alternative to the interactive board

## Out of Scope

| Feature | Reason |
|---------|--------|
| In-app game viewer/replay | Link to source platform instead; avoids building a move navigator |
| Engine/Stockfish analysis | Explodes scope and user expectations; defer indefinitely |
| Opening name/ECO display | Contradicts core value of position-based analysis |
| Mobile app | Web-first; responsive design sufficient for v1 |
| Real-time game tracking | Not an analysis use case |
| Social features | Not relevant to the core value |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 2: Import Pipeline | Complete |
| IMP-02 | Phase 2: Import Pipeline | Complete |
| IMP-03 | Phase 2: Import Pipeline | Complete |
| IMP-04 | Phase 2: Import Pipeline | Complete |
| IMP-05 | Phase 1: Data Foundation | Complete |
| IMP-06 | Phase 1: Data Foundation | Complete |
| ANL-01 | Phase 4: Frontend and Auth | In Progress (Zobrist JS port done; board UI in 04-03) |
| ANL-02 | Phase 3: Analysis API | Complete |
| ANL-03 | Phase 3: Analysis API | Complete |
| FLT-01 | Phase 3: Analysis API | Complete |
| FLT-02 | Phase 3: Analysis API | Complete |
| FLT-03 | Phase 3: Analysis API | Complete |
| FLT-04 | Phase 3: Analysis API | Complete |
| RES-01 | Phase 3: Analysis API | Complete |
| RES-02 | Phase 3: Analysis API | Complete |
| RES-03 | Phase 3: Analysis API | Complete |
| AUTH-01 | Phase 4: Frontend and Auth | Complete |
| AUTH-02 | Phase 4: Frontend and Auth | Complete |
| INFRA-01 | Phase 1: Data Foundation | Complete |
| INFRA-02 | Phase 2: Import Pipeline | Complete |
| INFRA-03 | Phase 1: Data Foundation | Complete |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-12 after 04-02 completion (ANL-01 in progress — Zobrist JS port done, interactive board in 04-03)*
