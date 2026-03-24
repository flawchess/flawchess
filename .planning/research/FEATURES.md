# Feature Research

**Domain:** Chess analytics — per-position game statistics, endgame classification, and material tracking
**Researched:** 2026-03-23
**Confidence:** HIGH (endgame categories, material notation, game phase algorithms from chessprogramming.org and Wikipedia); MEDIUM (competitor feature comparison — lichess/chess.com UIs are live but change without notice); LOW (exact API field availability for accuracy scores — chess.com has confirmed engine accuracy is NOT in the public API; lichess is different and DOES expose it)

---

> This file covers features for v1.5: Game Statistics & Endgame Analysis.
> v1.0–v1.4 features are already shipped. Focus: game phase detection, endgame classification, material signatures, engine accuracy import, and a new Endgames analytics tab.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that a chess analytics platform with endgame analysis must provide. Missing these = the Endgames tab feels incomplete or misleading.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Endgame type breakdown by W/D/L | Every chess analytics competitor (lichess Insights, chess.com Insights, Aimchess) shows performance broken down by game phase. Users expect to know "do I win my rook endgames?" | MEDIUM | Classification at import time into ~6 buckets (pawn, rook, minor piece, queen, no-pawns, complex). Aggregate W/D/L per bucket in a new Endgames tab. Depends on endgame class computed during import. |
| Game phase annotation per position | Lichess Insights filters every metric by opening/middlegame/endgame. Without this, per-position stats can't be phase-contextualized. | MEDIUM | Compute phase (opening/middlegame/endgame) at import for every position. Store as enum column on `game_positions`. Phase boundary algorithm based on non-pawn material count (see Architecture notes). |
| Material signature per position | ChessBase search, Syzygy tablebases, Stockfish endgame probing all use material signature notation (KRKP, KRPKR, etc.). Users expecting endgame filtering need this. | MEDIUM | Compute canonical material signature string (e.g. "KRPKRP") at import. Store on `game_positions`. Use white-dominant canonical form (White material first, heavier pieces first within each side). |
| Filter endgame stats by endgame type | Lichess Insights filters by game phase; users naturally want to filter by "show me only rook endgames". Lack of this makes the Endgames tab shallow. | LOW | Filter UI — same sidebar pattern as existing Openings tab filters. Filter values map directly to endgame class enum. |
| W/D/L in endgame when up/down material | Aimchess explicitly tracks "conversion rate" (winning when up) and "resourcefulness" (saving when down). Users expect to see whether they squander material advantages. | HIGH | Requires material imbalance column on `game_positions`. Query: group by (material_advantage_bucket, game_phase) → W/D/L. Buckets: down ≥2 pawns, down 1 pawn, equal, up 1 pawn, up ≥2 pawns. Define in pawn units. |
| Opening / middlegame / endgame accuracy (when available) | Chess.com Insights shows accuracy per phase. Lichess exports eval/accuracy per game when analysis is available. Users who have analyzed games expect these numbers. | HIGH | Import-time: parse accuracy from chess.com API `accuracies` field (game level only, not phase-level). For lichess, eval annotations per move are available via `?evals=true` in NDJSON. Phase-level accuracy requires per-move eval data — compute centipawn loss per phase. This is the most complex import feature. |

### Differentiators (Competitive Advantage)

Features that go beyond what lichess/chess.com/Aimchess provide, exploiting FlawChess's unique Zobrist hash position matching.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Material configuration drill-down (KRP vs KR) | No public tool lets you filter by exact material signature. ChessBase does it in database search but not as analytics. FlawChess can expose this natively since material signature is stored per position. | MEDIUM | UI: after selecting an endgame type (e.g. "rook endgames"), show a secondary breakdown by specific material signature. Toggle between type-level and signature-level granularity. The data is already in the DB if material signature is computed at import. |
| Phase transition point analysis | FlawChess can show which specific board positions are where users' win rates drop — combining Zobrist hash position matching with phase annotation. No competitor does this. | HIGH | Cross-tab feature: from the Endgames tab, click a position in the move explorer to see that position's stats filtered to endgame phase only. Requires phase column on `game_positions` and a phase filter in the existing Openings analysis query. |
| Conversion rate broken out by time control | Did I fail to convert a won rook endgame in bullet but convert it in rapid? Unique because FlawChess already has time control as a filter. | LOW | Minimal extra complexity — already have time control filter; just expose it on the Endgames tab alongside the existing filter sidebar. |
| Per-position endgame stats in the Move Explorer | The existing move explorer shows next-move W/D/L from any position. Annotating each position with its game phase and material class makes the explorer more informative without building a new UI. | LOW | Surface phase label and material signature as tooltip/badge on the board or stats panel. The data is already stored if computed at import. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Running engine analysis on the server | Users want computer evaluations for games not previously analyzed | Stockfish analysis is CPU-intensive. A single 15-move position analysis can take 0.5–5s at depth 20. Multi-user platform on 2-vCPU Hetzner VPS would be overwhelmed immediately. Chess.com limits analysis to Diamond subscribers for this reason. | Import accuracy/eval from chess.com and lichess APIs when already computed. Flag games with no eval data; defer server-side analysis to a future dedicated compute tier. |
| Storing per-move eval for all positions | Allows full accuracy computation at any depth | PGN eval annotations exist only if analysis was requested by the user on lichess/chess.com before import. For games without evals, there is nothing to import. Attempting to compute evals at import time hits the compute problem above. | Store evals where available from the API (lichess `?evals=true`, chess.com `accuracies` field). Mark games with `has_eval: bool`. Analytics only applies to eval-annotated subset. |
| Syzygy tablebase lookups at analysis time | True endgame Win/Draw/Loss by force (not user's historical stats) | Requires 150 GB+ of tablebase files for 7-piece endings. Even 5-piece Syzygy is ~880 MB. Impractical on VPS with 75 GB NVMe. | Use material signature + historical W/D/L from user's own games. This is FlawChess's core value anyway — personal statistics, not theoretical results. |
| Named endgame position bookmarks (Lucena, Philidor) | Advanced users want to track theoretical positions | Requires a curated endgame position database, manual FEN entry, or expert-tagged library. High editorial burden, low traffic for most users. | The existing bookmark system already allows any position to be bookmarked. Power users can bookmark the Lucena position themselves. No special support needed in v1.5. |
| Side-by-side endgame comparison vs. opponents | "How does my KRP endgame compare to player X's?" | Requires other users' data to be queryable. Privacy implications, multi-user aggregation complexity. | Defer to opponent scouting feature (already on roadmap). Stick to single-user analytics for endgames in v1.5. |

---

## Feature Dependencies

```
Endgame analytics tab (Endgames page)
    └──requires──> Endgame class per game_position (computed at import)
    └──requires──> Game phase per game_position (computed at import)
    └──requires──> Material imbalance per game_position (computed at import)
    └──requires──> Material signature per game_position (computed at import)

Endgame class computation
    └──requires──> Material signature computation (endgame class is derived from signature)
    └──requires──> Game phase computation (endgame class only meaningful in endgame phase)

Game phase computation
    └──requires──> python-chess board state at each ply (already available during import)
    └──uses──> Non-pawn material count threshold (no external dependency)

Material signature computation
    └──requires──> python-chess board state at each ply (already available during import)
    └──produces──> canonical string "KRPKR" (white-dominant, sorted by piece value)

Material imbalance computation
    └──requires──> python-chess board state at each ply (already available during import)
    └──produces──> signed integer in centipawn units (positive = white ahead)

Engine accuracy import (chess.com)
    └──requires──> chess.com game archive API (already integrated)
    └──note──> Only game-level accuracy available (white/black scalar), NOT phase-level
    └──note──> Field present as `accuracies.white` / `accuracies.black` in game JSON

Engine accuracy import (lichess)
    └──requires──> lichess NDJSON game export with `?evals=true` parameter
    └──note──> Per-move eval and judgment available for analyzed games
    └──note──> lichess does NOT compute accuracy for unanalyzed games at export time

Per-phase accuracy computation
    └──requires──> Per-move eval annotations (lichess with evals=true)
    └──requires──> Game phase label per ply (game phase computation)
    └──derives──> Average centipawn loss per phase = endgame accuracy proxy

Material conversion/recovery stats
    └──requires──> Material imbalance per position
    └──requires──> Game phase per position
    └──requires──> Game result (already stored)

Filter by endgame type
    └──requires──> Endgame class column on game_positions
    └──enhances──> Endgames tab (drives the primary filter)

Filter by material configuration
    └──requires──> Material signature column on game_positions
    └──enhances──> Endgames tab (secondary drill-down filter)
```

### Dependency Notes

- **Import pipeline is the critical path:** All analytics features depend on per-position metadata being computed at import time. There is no retroactive computation shortcut — the DB schema must be migrated and all existing positions re-enriched (or a full re-import triggered).
- **Engine accuracy is a split story:** chess.com provides only a single accuracy scalar per player per game (not per phase) via the public API. Lichess provides full per-move eval when the user has requested analysis. Phase-level accuracy is only possible for lichess analyzed games, not chess.com games.
- **Endgame class requires phase first:** The endgame class (rook endgame, pawn endgame, etc.) is only meaningful to classify positions that are already in the endgame phase. For positions in the opening or middlegame, endgame class is irrelevant.
- **Material imbalance and material signature are independent computations** that both run on the same board state at each ply. They should be computed in a single pass to avoid iterating positions twice.

---

## MVP Definition

### Launch With (v1.5)

Minimum viable endgame analytics — enough to make the Endgames tab genuinely useful.

- [ ] Game phase computed per position at import (opening/middlegame/endgame enum stored in `game_positions`)
- [ ] Material signature computed per position at import (canonical "KRPKR" string)
- [ ] Endgame class derived from material signature (6-category enum: pawn, rook, minor_piece, queen, mixed, pawnless)
- [ ] Material imbalance computed per position (signed integer, centipawn units)
- [ ] Endgames tab: W/D/L breakdown by endgame type (using same W/D/L display components as Openings tab)
- [ ] Endgames tab: filter by endgame type, time control, color, recency (reuse existing filter sidebar)
- [ ] Conversion stats: W/D/L when up/down material, broken down by game phase

### Add After Validation (v1.5.x)

Features to add once the core Endgames tab is live and users engage with it.

- [ ] Engine accuracy import from chess.com API (`accuracies` field) — add if users request accuracy tracking
- [ ] Per-move eval import from lichess (`?evals=true`) — add if accuracy-by-phase analytics is validated as high-value
- [ ] Material configuration drill-down (KRP vs KR level) — add if users navigate past top-level endgame types
- [ ] Phase label in Move Explorer tooltip — low-effort enhancement once phase data is available

### Future Consideration (v2+)

- [ ] Per-phase accuracy for chess.com games — not feasible with the public API; would require a chess.com partnership or local engine analysis
- [ ] Endgame training module (retry endgame positions) — crosses into training product territory, outside FlawChess's analytics-first scope
- [ ] Endgame comparison vs. opponent (scouting) — natural extension of opponent scouting, separate milestone

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Game phase computation at import | HIGH | MEDIUM | P1 |
| Material signature computation at import | HIGH | LOW | P1 |
| Endgame class derivation | HIGH | LOW | P1 |
| Material imbalance computation | HIGH | LOW | P1 |
| Endgames tab: W/D/L by endgame type | HIGH | MEDIUM | P1 |
| Filter by endgame type | HIGH | LOW | P1 |
| Conversion stats (up/down material) | HIGH | MEDIUM | P1 |
| Engine accuracy import (chess.com game-level) | MEDIUM | LOW | P2 |
| Eval import from lichess per-move | MEDIUM | HIGH | P2 |
| Phase-level accuracy (lichess) | MEDIUM | HIGH | P2 |
| Material signature drill-down UI | MEDIUM | MEDIUM | P2 |
| Phase label in Move Explorer | LOW | LOW | P2 |

**Priority key:**
- P1: Must have for v1.5 launch
- P2: Should have, add when time permits
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

### Endgame Classification Categories

All major tools use the same 5-6 top-level endgame types derived from chess theory (Chess Informant, Dvoretsky's Manual). The "most valuable piece remaining" principle determines the category:

| Category | Classification Rule | Frequency (estimated) | Notes |
|----------|--------------------|-----------------------|-------|
| Pawn endgame | Only kings and pawns remain | ~5% of games | Pure pawn endings; king activity decisive |
| Rook endgame | Rooks present, no queens, pawns present | ~8-10% of games | Most common endgame type; Lucena/Philidor positions |
| Minor piece endgame | Bishops and/or knights, no rooks or queens, pawns present | ~5-7% of games | Knight vs bishop is a classic sub-type |
| Queen endgame | Queens present (no rooks), pawns present | ~3-5% of games | Perpetual check risk, complex technique |
| Complex/mixed endgame | Multiple different piece types remain | ~10-15% of games | Rook + minor piece, or queen + rook, etc. |
| Pawnless endgame | No pawns remain | Rare (~1-2%) | Often drawn; tablebase-decidable |

Note: Frequency statistics are approximate from community sources. Rook endgames are widely cited as the most common specific endgame type. Exact frequency data across amateur games is not authoritatively published.

### Game Phase Detection Algorithms

| Tool | Algorithm | Thresholds |
|------|-----------|------------|
| Lichess (Scalachess) | Non-public (source not documented in forums) | Likely material-based; forum speculation about centrality scores |
| Stockfish (tapered eval) | Non-pawn material count as phase weight | Start: 6400 units (4N + 4B + 4R + 2Q using N=300, B=300, R=500, Q=1000). Endgame = 0. Interpolates between. |
| Chessprogramming standard | Piece count threshold | Endgame when combined non-pawn material ≤ ~1300 centipawns per side (roughly: no queens, or ≤ 1 rook + 1 minor per side) |
| Chess theory (Speelman) | Material threshold | Each side ≤ 13 points (not counting king). Pawns = 1, N/B = 3, R = 5, Q = 9. |
| Chess theory (Minev) | Piece count | ≤ 4 non-king non-pawn pieces total on board |
| Chess theory (Fine) | Queen presence | Endgame = no queens on board |

**Recommended approach for FlawChess:** Use a two-threshold piece-weight system. Opening ends when both sides have castled or move 15 is reached (ply 30). Endgame begins when total non-pawn material (excluding kings) drops below a threshold (approximately: equivalent to ≤ 1 rook + 1 minor piece per side, or ~1300cp per side). Middlegame is the gap between. This is deterministic, fast to compute with python-chess, and aligns with how chess players think about phases.

### Platform Comparison

| Feature | lichess Insights | chess.com Insights | Aimchess | FlawChess v1.5 plan |
|---------|------------------|--------------------|----------|---------------------|
| Game phase stats | Opening/middlegame/endgame accuracy (requires prior computer analysis) | Opening/middlegame/endgame accuracy (Diamond only) | Phase accuracy as one of 6 performance scores | W/D/L by phase; accuracy if eval available |
| Endgame type breakdown | None — no endgame-type filtering | None — game phases only, no endgame categories | Tracks endgame as single bucket ("conversion", "resourcefulness") | W/D/L by 6 endgame type categories |
| Material signature filtering | None | None | None | W/D/L by specific material configuration (KRP vs KR) |
| Material imbalance stats | Available as a dimension (filter/group-by) | Not directly exposed | "Advantage capitalization" score | W/D/L when up/down material by phase |
| Accuracy per game | Yes (analyzed games only) | Yes (game-level, analyzed games only) | Yes (aggregated) | Yes (chess.com: game-level; lichess: per-move eval when available) |
| Accuracy per phase | Yes (lichess analyzed games) | Yes (Diamond only) | Yes | Possible for lichess analyzed games only |
| Requires prior engine analysis | Yes | Yes (Diamond plan) | Yes | Only for accuracy features; W/D/L stats require no engine analysis |
| Free tier | Yes (lichess is free) | No (Diamond = $14/mo) | Partial (free tier limited) | Yes — core endgame stats are free (no engine required) |

### Key Insight: FlawChess's Advantage

Lichess and chess.com phase/endgame accuracy require prior per-game engine analysis. FlawChess's W/D/L endgame stats (the P1 features) require NO engine analysis — they derive from game results and position metadata. This means FlawChess can provide meaningful endgame analytics for 100% of imported games, not just the subset users happened to analyze.

---

## Engine Accuracy API Notes

### chess.com Public API
- Field: `accuracies.white` and `accuracies.black` on each game object in archive JSON
- Availability: Only present if game was previously analyzed via Game Review; absent otherwise
- Granularity: Single scalar per player per game (not per phase, not per move)
- Confirmed limitation: Game phase accuracy values are NOT stored in the database and NOT available via API (chess.com forum, confirmed by chess.com staff)
- Source: chess.com forum "Insight data in public APIs" — LOW confidence (community post, but consistent with API inspection)

### lichess API
- Field: Per-move eval comments in PGN when `?evals=true` parameter used on game export
- Availability: Only for games where user requested computer analysis on lichess; absent otherwise
- Granularity: Per-move eval (centipawn) and judgment (inaccuracy/mistake/blunder) annotations in PGN
- Accuracy field: `players.white.analysis.accuracy` / `players.black.analysis.accuracy` in JSON format (integer 0-100)
- Phase-level accuracy: Computable from per-move eval + phase annotation, but must be derived — not returned directly
- Source: lichess API docs (`?evals=true` param documented) — HIGH confidence

---

## Sources

- [Chess endgame — Wikipedia](https://en.wikipedia.org/wiki/Chess_endgame) — HIGH confidence (endgame categories, frequency stats)
- [Game Phases — Chessprogramming wiki](https://www.chessprogramming.org/Game_Phases) — HIGH confidence (engine algorithms)
- [Stockfish endgame.h material notation](https://github.com/evijit/material-chess-android/blob/master/app/src/main/jni/stockfish/endgame.h) — HIGH confidence (KRPKR notation standard)
- [Lichess Insights live interface](https://lichess.org/insights/Chess-Network) — MEDIUM confidence (UI observed directly, may change)
- [chess.com Insights Help Center](https://support.chess.com/en/articles/8708925-what-is-insights-on-chess-com) — HIGH confidence (official docs)
- [chess.com game review API fields](https://www.chess.com/announcements/view/published-data-api) — HIGH confidence
- [chess.com forum: phase accuracy not in API](https://www.chess.com/forum/view/site-feedback/insight-data-in-public-apis) — LOW confidence (community post)
- [Aimchess feature description](https://eliteai.tools/tool/aimchess) — MEDIUM confidence (third-party summary)
- [ChessBase material search](https://en.chessbase.com/post/material-searches-in-chebase-9-part-one) — MEDIUM confidence
- [Rook endings frequency (~10% of games)](https://centaur.reading.ac.uk/65694/4/URE.pdf) — MEDIUM confidence (academic paper)
- [Chess Informant endgame classification system](https://chessforallages.blogspot.com/2012/03/chess-informant-endgames.html) — MEDIUM confidence
- [lichess API: evals export parameter](https://lichess.org/api) — HIGH confidence (official API docs)

---

*Feature research for: FlawChess v1.5 — game statistics & endgame analysis*
*Researched: 2026-03-23*
