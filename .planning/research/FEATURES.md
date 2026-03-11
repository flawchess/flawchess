# Features Research: Chessalytics

> Research based on analysis of lichess, chess.com Insights, ChessBase, Chess Tempo, and similar platforms.
> Complexity estimates: Low (days), Medium (1–2 weeks), High (weeks+).

---

## Table Stakes (must have or users leave)

These are the features every chess analysis tool provides. Missing any of them makes the product feel unfinished to the target audience.

### Game Import
- **Import by username from chess.com and lichess** — Both platforms expose public REST APIs. Chess.com returns monthly archives as PGN/JSON; lichess streams NDJSON. Handling pagination, rate limits, and partial syncs is the main complexity. *Complexity: Medium*
- **Re-sync / incremental fetch** — Users expect to add new games without re-importing everything. Requires storing the last-fetched timestamp or game ID per source. *Complexity: Low (once import works)*
- **Import progress feedback** — A progress indicator during long imports (hundreds of games) is expected. Silent background jobs that fail without feedback cause user abandonment. *Complexity: Low*

### Game Storage and Metadata
- **Store full PGN / move list** — Required to compute positions later. Cannot analyze what you didn't store. *Complexity: Low (schema design matters)*
- **Store standard metadata** — Result, date, time control, rated/casual, platform, opponent username, opening name from platform, game URL. Chess.com and lichess both provide this. *Complexity: Low*
- **Correct color assignment** — Know which side the importing user played. Both APIs provide this. *Complexity: Low*

### Position-Based Analysis (the core product)
- **Interactive board for position entry** — Users play moves on a board to define a target position rather than typing FEN strings. This is the primary UX decision. *Complexity: Medium (needs a chess board component — chessboard.js, react-chessboard, or cm-chessboard are established options)*
- **Position matching against stored games** — For each game, determine if the target position was reached. Requires replaying move sequences with python-chess. *Complexity: Medium (the key algorithmic challenge; FEN normalization is straightforward with python-chess)*
- **Win/draw/loss rates for matching games** — Aggregate results for matched games, split by color. *Complexity: Low (pure aggregation once matching works)*
- **List of matching games** — Show individual matched games with opponent, result, date, time control, and link back to chess.com or lichess. *Complexity: Low*

### Filters
- **Filter by color (white / black / both)** — Core to the product's value proposition. Users need to isolate their own piece placement. *Complexity: Low*
- **Filter by time control** — Bullet / blitz / rapid / classical. Users' styles differ drastically by time control; mixing them produces misleading stats. Every platform provides this. *Complexity: Low*
- **Filter by rated vs. casual** — Casual games are often throwaway; mixing them skews stats. *Complexity: Low*
- **Filter by recency** — Last week / month / 3 months / 6 months / 1 year / all time. Results from 3 years ago may not reflect current play. *Complexity: Low*

### Authentication and Multi-User
- **User accounts** — Each user manages their own imported games and analyses. *Complexity: Medium (standard auth; session management)*
- **User data isolation** — Users only see their own games. *Complexity: Low (row-level filtering)*

---

## Differentiators (competitive advantage)

These are features Chessalytics has or could have that lichess Explorer and chess.com Insights lack.

### Position-Based Filtering Independent of Opening Name
**This is the core differentiator.** Lichess's Opening Explorer and chess.com's Openings tab both group games by ECO code or opening name. If lichess calls 1.e4 d6 2.d4 Nf6 3.Nc3 g6 the "Pirc Defense" and a slight move-order variation the "Czech Defense," those games are siloed — even if the user played identical moves and reached the same position. Chessalytics groups by actual board state, not by naming convention.

- **Any-order position matching** — Match games where a target position was reached regardless of move order. Useful for transpositions (e.g., reaching the same King's Indian structure via different move orders). *Complexity: High (compute a canonical FEN after each half-move; match against stored FEN snapshots; precomputing FEN snapshots per game at import time makes queries fast)*
- **Strict move-order matching** — Match only games where moves were played in the exact sequence entered. Useful when the user cares about the specific line, not just the resulting position. *Complexity: Medium (compare move prefix sequences directly)*
- **Own-pieces-only filtering** — The user defines a position using only their own pieces; opponent piece placement is ignored when matching. This is explicitly not possible in any existing consumer tool. *Complexity: Medium (mask opponent pieces from FEN before comparison)*

### Per-User Personal Game Database
Lichess Explorer works against a global master database or all lichess games — not your personal history. Chess.com Insights shows aggregate stats but does not let you query by position. Chessalytics is the only tool that lets a club-level player ask "what is my personal win rate from this exact pawn structure?"

### Transparent, Queryable Filters
Chess.com Insights buries its filter logic. Chessalytics exposes all filter combinations simultaneously, making the effect of each filter immediately visible.

---

## Anti-Features (things to deliberately NOT build for v1)

These features are tempting but impose disproportionate complexity for the value they deliver at v1 scale.

### Manual PGN Upload
Already excluded in PROJECT.md. Adds a file parsing pipeline (handling malformed PGNs, variant headers, encoding issues) without covering a use case not already served by the API path. Every user who has PGN games also has a chess.com or lichess account. Defer to v2 or permanently exclude.

### In-App Game Viewer / Move Replay
Already excluded. Linking to the source platform is sufficient. Building a full move-by-move viewer requires a synchronized board + move list component, keyboard navigation, annotation support, and engine integration expectations from users. Enormous surface area for v1.

### Engine Analysis / Stockfish Integration
Players will immediately expect "show me the blunder" functionality once they see a game viewer. Engine integration (evaluation bar, best move arrows, mistake classification) is a separate product. Avoid even partial implementation; it anchors user expectations.

### Opening Name Display / ECO Codes
Displaying ECO codes or opening names alongside position results seems helpful but requires maintaining an opening book database (or using the platform-supplied name, which is the exact inconsistency Chessalytics is solving). It adds confusion without improving the core value proposition.

### Opponent Analysis
"How do I do against 1.d4 players?" is a natural follow-on question, but it requires different data modeling (filtering on opponent metadata, not user positions) and a separate UX surface. V2.

### Performance Over Time / Trend Charts
Time-series charts of win rate by opening are compelling but require sufficient data density to be meaningful (most users won't have enough games per position per month). False signal is worse than no signal for a new user. V2 once data volume is understood.

### Rating-Based Filtering
Filtering games by opponent Elo band (e.g., "only games vs. 1600–1800") is a ChessBase staple but requires storing opponent ratings, adds a filter dimension that multiplies the number of segments, and dilutes already-small sample sizes. V2.

### Social / Sharing Features
Sharing a position analysis URL with friends, or publishing opening repertoires publicly. Adds auth complexity (public vs. private), URL scheme design, and no clear v1 user value. V2.

### Browser Extension / Auto-Import
Some tools auto-detect when a user finishes a game and import immediately. Technically fragile (scraping, browser API changes) and out of scope for a web platform. Not worth the maintenance burden.

---

## Feature Dependencies

Build order follows the dependency chain. Each layer must exist before the next is useful.

### Layer 0 — Infrastructure (no dependencies)
1. User auth (accounts, sessions)
2. Database schema (users, games, game_moves or game_fens)
3. chess.com API client (fetch games by username, paginate, rate-limit)
4. lichess API client (NDJSON stream, handle large archives)

### Layer 1 — Import Pipeline (depends on Layer 0)
5. Game import endpoint — accepts username + platform, calls API client, stores games + metadata
6. Incremental re-sync — track last-fetched marker per user+platform, fetch only new games
7. FEN snapshot generation at import time — replay each game with python-chess, store FEN after every half-move. This is the key precomputation that makes position queries fast.

### Layer 2 — Position Matching (depends on Layer 1)
8. FEN normalization — strip en-passant / castling rights from FEN for position-only comparison (python-chess handles this)
9. Own-pieces-only FEN masking — zero out opponent piece squares before comparison
10. Strict move-order match query — compare move prefix string against stored moves
11. Any-order position match query — look up target FEN in stored FEN snapshots

### Layer 3 — Analysis UI (depends on Layer 2)
12. Interactive board component — lets user input a position by playing moves
13. Filter controls — color, time control, rated/casual, recency
14. W/D/L results display — counts and percentages for matched games
15. Matching games list — table with opponent, result, date, platform link

### Layer 4 — Polish (depends on Layer 3)
16. Import progress indicator
17. Empty states (no games yet, no matching games, filters too narrow)
18. Error handling for API failures (chess.com/lichess downtime, invalid usernames)
19. Re-sync button with "last synced at" timestamp

### Key constraint: FEN snapshots at import time
Storing a FEN string after every half-move at import is the design decision that makes Layer 2 queries viable. Without it, every position query requires replaying all games on the fly, which becomes slow at thousands of games. The tradeoff is storage (roughly 50–80 bytes × average 40 moves × thousands of games = tens of MB per active user, which is acceptable for SQLite or Postgres).

---

*Research completed: 2026-03-11. Based on direct knowledge of lichess, chess.com, ChessBase, Chess Tempo, and Scid vs. PC feature sets.*
