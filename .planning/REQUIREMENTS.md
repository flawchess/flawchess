# Requirements: FlawChess

**Defined:** 2026-03-23
**Core Value:** Users can determine their success rate for any opening position they specify

## v1.5 Requirements

Requirements for v1.5 Game Statistics & Endgame Analysis milestone.

### Position Metadata

- [x] **PMETA-01**: System computes game phase (opening/middlegame/endgame) for every position during import using material-weight thresholds
- [x] **PMETA-02**: System computes material signature in canonical form (stronger side first, e.g., KRP_KR) for every position during import
- [x] **PMETA-03**: System computes material imbalance in centipawns for every position during import
- [x] **PMETA-04**: System classifies endgame type (rook/minor piece/pawn/queen/mixed/pawnless) for positions in endgame phase
- [x] **PMETA-05**: System backfills position metadata for all previously imported games without requiring user re-import

### Engine Analysis Import

- [ ] **ENGINE-01**: System imports per-move eval (centipawns/mate) from lichess PGN annotations for games with prior computer analysis
- [ ] **ENGINE-02**: System imports game-level accuracy scores from chess.com for games where analysis exists
- [ ] **ENGINE-03**: System gracefully handles missing analysis data (null fields, no errors) for unanalyzed games
- [x] **LMETRIC-01**: System stores per-player analysis metrics (ACPL, inaccuracy count, mistake count, blunder count) as nullable SmallInteger columns on the games table
- [x] **LMETRIC-02**: System imports lichess per-player analysis metrics (ACPL, inaccuracy, mistake, blunder counts) from the API response during game normalization

### Endgame Analytics

- [x] **ENDGM-01**: User can view W/D/L rates for each endgame category in a dedicated Endgames tab
- [x] **ENDGM-02**: User can filter endgame statistics by time control (bullet/blitz/rapid/classical)
- [x] **ENDGM-03**: User can filter endgame statistics by color played (white/black/both)
- [x] **ENDGM-04**: User can see game count per endgame category to assess statistical significance

### Conversion & Recovery Statistics

- [x] **CONV-01**: User can see win rate when up material, broken down by game phase (placement TBD: Stats tab or Endgames tab)
- [x] **CONV-02**: User can see draw/win rate when down material, broken down by game phase
- [x] **CONV-03**: User can filter conversion/recovery stats by time control

## v1.4 Requirements (Prior Milestone)

### Analytics

- [ ] **ANLY-01**: Site owner can view page visit counts and trends over time
- [ ] **ANLY-02**: Site owner can see top pages/routes by visit count
- [ ] **ANLY-03**: Site owner can see visitor referrer sources
- [x] **ANLY-04**: Analytics collection respects user privacy (no cookie consent banner required)
- [x] **ANLY-05**: Analytics solution has minimal server resource footprint (RAM/CPU)

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
| Local Stockfish analysis | Too CPU-intensive for Hetzner VPS; only import existing platform analysis |
| Per-phase accuracy for chess.com | chess.com API only provides game-level accuracy, not per-phase |
| Per-move quality classification (computing blunder/mistake/inaccuracy from engine evals) | Requires engine eval for every move; importing pre-computed game-level counts from lichess is in scope (Phase 28.1) |
| Chessboard in Endgames tab | Endgame positions too diverse for meaningful board-based exploration |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PMETA-01 | Phase 26 | Complete |
| PMETA-02 | Phase 26 | Complete |
| PMETA-03 | Phase 26 | Complete |
| PMETA-04 | Phase 26 | Complete |
| PMETA-05 | Phase 27 | Complete |
| ENGINE-01 | Phase 29 | Pending |
| ENGINE-02 | Phase 29 | Pending |
| ENGINE-03 | Phase 29 | Pending |
| ENDGM-01 | Phase 28 | Complete |
| ENDGM-02 | Phase 28 | Complete |
| ENDGM-03 | Phase 28 | Complete |
| ENDGM-04 | Phase 28 | Complete |
| CONV-01 | Phase 28 | Complete |
| CONV-02 | Phase 28 | Complete |
| CONV-03 | Phase 28 | Complete |
| LMETRIC-01 | Phase 28.1 | Complete |
| LMETRIC-02 | Phase 28.1 | Complete |

**Coverage:**
- v1.5 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after v1.5 roadmap creation*
