# Pitfalls Research: Chessalytics

---

## API Pitfalls

### Chess.com API: No Authentication, But Strict Rate Limits

Chess.com's public API (`api.chess.com/pub`) requires no API key for read access. However, it enforces aggressive rate limiting with no publicly documented hard numbers — observed behavior is roughly 1 request/second per IP before receiving 429s, with exponential backoff required. The monthly archive endpoint (`/pub/player/{username}/games/{year}/{month}`) returns all games for a month as a single payload, which can be several MB for active players.

**Warning signs:** 429 responses during bulk import; timeouts on large monthly archives (a player with 500+ bullet games in one month produces a large JSON blob).

**Prevention strategy:**
- Fetch archives sequentially with a small delay (100–300ms) between requests, not concurrently.
- Cache the list of available monthly archive URLs (`/pub/player/{username}/games/archives`) and only fetch months not yet stored.
- Store raw JSON responses to avoid re-fetching; parse lazily.
- Set a `User-Agent` header identifying your app — chess.com has historically been more lenient with identified clients.

**Phase to address:** Phase 1 (import pipeline). Get rate limiting right before anything else; it affects all subsequent development and testing.

---

### Lichess API: OAuth Required for Some Endpoints, Streaming for Others

Lichess uses a streaming NDJSON format for game exports (`/api/games/user/{username}`), not paginated JSON. Each line is a separate JSON object (or PGN block depending on `Accept` header). Authentication via OAuth2 bearer token is required to fetch private games or to avoid the strictest rate limits on public endpoints. Without a token, the games endpoint is limited to ~20 req/min. With a personal access token, limits are much higher (typically 50–100 req/min).

The lichess API also uses `since`/`until` parameters as Unix timestamps in milliseconds (not seconds), which is a common source of bugs when porting from other APIs.

**Warning signs:** Empty results when fetching recent games without `until` defaulting to now; getting only public rated games when user expects casual games too; responses that look like a single large string instead of parsed JSON (streaming not handled).

**Prevention strategy:**
- Always request NDJSON (`Accept: application/x-ndjson`) and handle the streaming format — read line by line.
- Guide users to provide a lichess personal access token during onboarding; document that it unlocks private games and higher limits.
- Use the `since` parameter with the timestamp of the last stored game to do incremental syncs.
- Validate that millisecond timestamps are used, not second-level.

**Phase to address:** Phase 1. The streaming format is architecturally different enough from chess.com that it needs a dedicated adapter pattern from the start.

---

### Data Format Differences Between Platforms

Chess.com returns games in a JSON envelope with PGN embedded as a string field. Lichess can return either pure PGN or NDJSON with a `pgn` field. The PGN header tags differ significantly:

| Field | Chess.com | Lichess |
|---|---|---|
| Time control | `[TimeControl "600"]` (seconds) | `[TimeControl "600+5"]` (base+increment) |
| Result | Standard `1-0`, `0-1`, `1/2-1/2` | Same, plus `*` for ongoing |
| Termination | `Normal`, `Time forfeit`, `Abandoned` | `Normal`, `Time forfeit`, `Rules infraction`, etc. |
| Player URLs | Not in PGN | `[Site "https://lichess.org/..."]` |
| Variant | Not always tagged | `[Variant "Standard"]` tag present |

Chess.com includes non-standard PGN tags like `[WhiteElo]`, `[BlackElo]`, and `[ECO]` consistently. Lichess includes `[Opening]` and `[LichessURL]` tags.

**Warning signs:** Time control normalization bugs (treating `600` and `600+0` as different time controls); variant games (Chess960, crazyhouse) polluting analysis of standard games.

**Prevention strategy:**
- Build a normalization layer that maps both platforms' metadata to a unified internal schema before storage.
- Explicitly filter `[Variant]` tags — only import `Standard` games for v1.
- Parse time controls into `(base_seconds, increment_seconds)` tuples during normalization, then bucket into bullet/blitz/rapid/classical using standard thresholds (≤180s = bullet, ≤600s = blitz, ≤1800s = rapid, else classical — applied to estimated game duration, not just base time).

**Phase to address:** Phase 1. Normalization schema must be defined before any data is stored, or migration becomes painful.

---

### Handling API Failures and Partial Imports

A user with 5 years of games across 60 monthly archives could have an import interrupted mid-way. If progress is not tracked per archive, the entire import must restart, and users with thousands of games will time out or give up.

Chess.com occasionally returns malformed PGN for certain game types (correspondence, daily chess with conditional moves) that will crash naive parsers.

**Warning signs:** Import jobs that silently fail for some months; users reporting "missing" games; PGN parse errors crashing the entire batch.

**Prevention strategy:**
- Track import progress per monthly archive with a status field (`pending`, `fetched`, `parsed`, `complete`, `failed`). Re-sync only processes incomplete archives.
- Wrap per-game PGN parsing in try/except; log failures with enough context (username, platform, game ID) to debug, but continue processing the rest of the batch.
- Expose import status in the UI so users can see progress and any skipped games.
- Store raw fetched data before parsing, so a parsing bug fix can reprocess without re-fetching.

**Phase to address:** Phase 1–2 boundary. Basic error handling in Phase 1; progress tracking and retry UI in Phase 2.

---

## Data Pitfalls

### PGN Parsing Edge Cases

python-chess's `chess.pgn.read_game()` is robust but has documented edge cases:

- **Null moves** (`--` in PGN): Legal in PGN spec for analysis annotations; python-chess handles them but they represent an invalid board state for position matching. Games with null moves must be detected and handled specially.
- **Variant games**: Chess960 (Fischer Random) castling uses different notation (`O-O` is valid but the king may end on a different square). If variant games slip through the normalization filter, position encoding will produce wrong results.
- **Malformed headers**: Some chess.com PGNs have non-UTF-8 characters in player names (usernames with special characters). This can cause UnicodeDecodeError if not explicitly handled with error handling on decode.
- **Multiple games in one PGN string**: Chess.com returns all games for a month in a single PGN string. `chess.pgn.read_game()` reads one game per call from a `StringIO` object; callers must loop until `read_game()` returns `None`.
- **Clocks and comments**: `{[%clk 0:05:00]}` clock annotations embedded in move comments are common in both platforms' PGNs. python-chess preserves these in the move tree but they are not positions — don't confuse comment nodes with move nodes when traversing the game tree.

**Warning signs:** `None` returned early from `read_game()` loop (malformed PGN terminates the stream); position counts not matching expected game length; Chess960 positions appearing in "standard" analysis results.

**Prevention strategy:**
- Wrap the PGN read loop to catch `ValueError` and `UnicodeDecodeError` per game.
- After parsing, validate `board.is_valid()` at each position before storing.
- Explicitly check and reject non-standard variants during normalization, before PGN parsing.
- Use `chess.pgn.read_game(io.StringIO(pgn_string))` in a loop with the pattern `while game := chess.pgn.read_game(handle)` to correctly iterate multi-game PGN strings.

**Phase to address:** Phase 1. Must be solid before any position data is stored.

---

### Position Representation Gotchas

FEN (Forsyth-Edwards Notation) is the standard position string, but full FEN includes state beyond piece placement: active color, castling rights, en passant target square, halfmove clock, fullmove number. Two positions that look visually identical can have different FEN strings due to these state fields.

For Chessalytics' core use case (matching positions regardless of how they were reached), the relevant representation is the **piece placement portion of FEN only** (the first space-delimited field), potentially combined with side to move. However, this creates a subtle problem: en passant rights and castling rights affect legal moves and could matter for some users' analysis.

Additionally, the project requires matching positions where the user specifies only their own pieces' placement, ignoring opponent piece positions. Standard FEN cannot represent this — it requires a custom "partial position" representation.

**Warning signs:** False negatives in position search (positions that should match don't) due to en passant/castling FEN fields; false positives (positions that match by piece placement but the user played with castling rights already lost); confusion between "position reached" and "position at move N."

**Prevention strategy:**
- Store both the full FEN and the piece-placement-only FEN (first field) for each position in the move sequence.
- For the "own pieces only" filter, build a separate normalized representation: extract just the user's pieces from the board and encode their squares. A Zobrist hash or a sorted list of `(piece_type, color, square)` tuples works well as a lookup key.
- Document clearly in the data model what each stored field means.
- For position matching queries, default to piece-placement + side-to-move (ignoring castling and en passant) with a toggle for strict FEN matching if needed in the future.

**Phase to address:** Phase 2 (position encoding must be designed before the search feature is built). The data model decision made here is very hard to change after positions are stored.

---

### Game Deduplication (Same Game on Both Platforms)

This is not a realistic problem for Chessalytics. Chess.com and lichess are separate platforms with no game sharing — a game played on chess.com does not appear on lichess and vice versa. Cross-platform duplicates do not exist in practice.

The real deduplication concern is within a single platform: **on-demand re-sync must not create duplicate game records**. Chess.com archives are immutable per month once the month has ended, but the current month's archive grows over time. Lichess streams all games matching date filters, including games already imported.

**Warning signs:** Game count growing abnormally on re-sync; win rates shifting after re-sync due to counted duplicates.

**Prevention strategy:**
- Use the platform's native game ID as the unique identifier (`[Site]` URL on lichess, the URL slug on chess.com). Store it as a unique constraint in the database.
- On re-sync, use `INSERT OR IGNORE` (SQLite) or `INSERT ... ON CONFLICT DO NOTHING` (Postgres) semantics.
- For chess.com, only re-fetch the current month's archive on re-sync; all past months are complete.
- For lichess, pass `since` = timestamp of the last stored game to avoid re-streaming old games.

**Phase to address:** Phase 1 (import) and Phase 2 (re-sync). The unique constraint must be in the initial schema.

---

## Performance Pitfalls

### Slow Position Queries at Scale

The core query — "find all games where this position appears" — naively requires scanning every position of every game for every user. At 10,000 games × 40 moves average = 400,000 positions per user, a full table scan with FEN string comparison is prohibitively slow.

The standard approach is to precompute and store a position hash (Zobrist hash or hash of the normalized FEN) for every position in every game, then index that hash column. This reduces the query to an indexed hash lookup, then a join to the games table.

**Warning signs:** Position search taking >1 second during development with only a few hundred games; `EXPLAIN` output showing sequential scans on the positions table.

**Prevention strategy:**
- Design the schema with a `positions` table: `(id, game_id, ply, position_hash, full_fen)`. Index `(user_id, position_hash)` — the user scoping is critical for multi-user correctness and query performance.
- Use a 64-bit integer hash (Zobrist) rather than the FEN string as the lookup key — integer equality is faster than string comparison and takes less index space.
- For the "own pieces only" filter, precompute a separate `own_position_hash` column scoped to the piece color, stored alongside the full position hash.
- Benchmark with realistic data (10k+ games) before committing to SQLite vs Postgres. SQLite handles this use case well up to ~50k games per user; above that, Postgres with a proper index performs significantly better.

**Phase to address:** Phase 2. Must be designed before position data is stored at scale — retrofitting an index after millions of rows are present is a painful migration.

---

### Import Bottlenecks for Users with Many Games

An active lichess player may have 50,000+ games. Fetching, parsing, and storing positions for all of them in a single synchronous request will time out any HTTP connection (typically 30–60 seconds) and block the server thread.

Chess.com's monthly archives make this slightly more tractable (batch by month) but the same problem exists for prolific players.

**Warning signs:** Import endpoint timing out for players with >1,000 games; server becoming unresponsive during a large import (blocking the event loop in async FastAPI).

**Prevention strategy:**
- Make import asynchronous from day one: the import endpoint enqueues a job and returns immediately with a job ID. The client polls a status endpoint.
- Use a task queue (Celery + Redis, or Python's `asyncio` with a background task queue) rather than running imports in the request handler.
- Process games in batches (e.g., 100 games at a time) with progress committed after each batch so partial progress is not lost on crash.
- Add a per-user import lock to prevent concurrent imports of the same user's games.
- For the initial v1 where simplicity is valued, FastAPI's `BackgroundTasks` provides a lightweight async option that avoids a full task queue — but document its limitations (no persistence across restarts, no retry).

**Phase to address:** Phase 1. Synchronous import is a local-only development shortcut; async import must be in place before any real-world testing.

---

### Frontend Chess Board Performance

Rendering a chess board with an interactive piece-placement UI sounds simple, but re-rendering on every move in a React component with naive state management can cause jank, especially on mobile. The bigger issue is that "specify a position by playing moves" requires maintaining a full `chess.js` game state on the frontend, and replaying from the start on every move update is O(n) in move count.

**Warning signs:** Noticeable lag when playing moves on the position-specification board; board flicker on piece drag; state desync where the board displays a position that doesn't match the app's internal FEN state.

**Prevention strategy:**
- Use an established chess board UI library (Chessground — used by lichess itself, MIT licensed; or react-chessboard) rather than building from scratch. These libraries handle piece rendering, drag-and-drop, and board state efficiently.
- Keep a single `chess.js` (or equivalent) instance as the source of truth for the position; derive board display state from it, don't maintain parallel state.
- When the user hits "search," send the FEN string to the backend — do not try to send move lists and reconstruct on the server.

**Phase to address:** Phase 3 (frontend). Library selection is the key decision; make it early in the frontend phase.

---

## UX Pitfalls

### Position Specification Confusion

Users may not understand the difference between "specify by playing moves" and "match any position with these pieces." A user who plays 1.e4 e5 2.Nf3 and then searches may expect to find all games where their knight is on f3 and their pawns are on e4 — but if they played a different move order to reach the same position, the result should still match.

The flip side: a user who plays 1.e4 and searches may be surprised that games where they played 1.d4 and then e4 on move 3 also appear in results, because their pawn ended up on e4 in both cases.

**Warning signs:** User feedback that "wrong games are appearing" or "my games aren't showing up" — both indicate a mismatch between the user's mental model and the search semantics.

**Prevention strategy:**
- Make the "strict move order" vs "any position" distinction prominent and clearly labeled in the UI, not buried in a settings panel.
- Show a live count of matching games as the user builds the position on the board (requires a fast search endpoint or debounced polling).
- Display a small sample of matched game positions (a miniature board thumbnail showing the actual game position) alongside the statistics, so users can verify the search matched their intent.
- Default to "any position" (the more useful mode) with a tooltip explaining the difference.

**Phase to address:** Phase 3 (frontend), but the API must support both modes from Phase 2.

---

### Move Order Matching Expectations

"Strict move order matching" has an ambiguity: does it mean the moves were played in exactly that order from the starting position, or that the moves were a subsequence of the game moves (allowing interspersed opponent moves)? Chess openings always involve both players moving, so "strict order" almost certainly means "the user's moves were played in that exact order, ignoring opponent moves" — but this is non-obvious.

A further edge case: transpositions. The position after 1.e4 e5 2.Nf3 Nc6 3.Bb5 is identical to the position after 1.e4 e5 3.Bb5 Nc6 2.Nf3 (if white plays Bb5 before Nf3). Under "strict move order" with user-only filtering, these should match. Under "strict full game move order" they should not. These are two different features.

**Warning signs:** Power users asking "why doesn't it find my transposed games?"; confusion reported during early user testing about what "strict" means.

**Prevention strategy:**
- For "strict move order" mode, define clearly in both code and UI: the user's moves (ignoring opponent moves) must appear in the same order as the search sequence.
- Avoid the term "strict move order" in the UI — use plain language like "I played these moves in this exact order" vs "I reached this exact position (any move order)."
- Document the transposition behavior explicitly in any help text.

**Phase to address:** Phase 2 (search algorithm design). The definition must be locked before implementation.

---

### Filter Combinations That Return No Results

A user searching for a rare position with filters for: "rated only + blitz + last 3 months" may legitimately have zero matching games. The app should distinguish between "no games match" and "there was an error" — and ideally help the user understand why.

**Warning signs:** Blank results page with no explanation; users reporting "broken search" when it's actually a valid empty result.

**Prevention strategy:**
- Always show the count of games searched (denominator) alongside matching games (numerator), e.g., "0 of 847 blitz games matched."
- When the result is zero, suggest relaxing filters: show what count would result from removing each filter individually.
- Never show an empty results page without context — at minimum show "no matching games found with current filters."

**Phase to address:** Phase 3 (frontend UI), but the API should return the denominator (total games searched) as part of every search response from Phase 2.

---

## Architecture Pitfalls

### Over-Engineering the Position Search

The temptation is to build a sophisticated position search engine with Zobrist hashing, bitboard representations, and inverted indexes from day one. For the actual scale of Chessalytics (thousands of games per user, not millions), this is premature. A simple indexed hash lookup on a positions table is sufficient and dramatically easier to build and debug.

The opposite problem also exists: storing only the final FEN of each game rather than all intermediate positions, which makes the "position appears at any point" query impossible without replaying every game.

**Warning signs:** Spending more than a day on position encoding before any games are importable; building custom bitboard logic when python-chess already provides it; schema designs with no positions table at all.

**Prevention strategy:**
- Store all intermediate positions (every ply) with an indexed hash. This is the minimum viable data model for the core feature.
- Use python-chess's `board.fen()` and the piece placement substring as the position key — no custom encoding needed for v1.
- Defer Zobrist hashing and bitboard optimization to a later phase when actual performance data justifies it.
- The positions table will be large (40 rows per game × 10k games = 400k rows) but this is entirely manageable with a simple integer index.

**Phase to address:** Phase 2. Accept the simple approach first; optimize only when benchmarks show a problem.

---

### Database Schema That Doesn't Scale

A schema that stores everything in one `games` table with PGN as a text blob has no path to efficient position search. A schema that normalizes too aggressively (separate rows for each piece on each square) creates impossibly complex queries.

The positions table approach is correct but requires careful design of the foreign key structure and index strategy from the start. Key decisions that are hard to change later:
- Whether `user_id` is on the positions table or only on the games table (affects query plan for the primary use case)
- Whether position hashes are stored as integers (fast) or strings (flexible but slow)
- Whether to use SQLite (simpler) or Postgres (more robust for concurrent writes during background imports)

**Warning signs:** Queries that require joining 3+ tables to answer "how many blitz games had this position?"; migration scripts touching the positions table (which may have millions of rows for active users).

**Prevention strategy:**
- Denormalize `user_id` onto the positions table for query efficiency — the primary query is `WHERE user_id = ? AND position_hash = ?`.
- Use `INTEGER` (64-bit) for position hashes, not `TEXT`.
- Include `color` (white/black) on each game record so time-control and color filtering can happen at the games table without the positions table.
- Start with SQLite for simplicity; design the schema to be Postgres-compatible from the start so migration is a schema dump and load, not a rewrite. SQLAlchemy's ORM abstracts the differences adequately.
- Add a `games.platform` column and `games.platform_game_id` unique constraint from day one — deduplication without this is extremely painful to add retroactively.

**Phase to address:** Phase 1 (initial schema). This is the highest-leverage architectural decision in the project. Get it right before any data is stored.

---

### Frontend-Backend Coupling

Building the frontend to call the backend's internal data structures directly (e.g., passing raw FEN strings from a database row to the UI, or having the UI reconstruct game trees from stored move sequences) creates tight coupling that makes both sides hard to change.

The specific risk for Chessalytics: if the position search API returns raw database rows with internal hash fields exposed, the frontend will start depending on those fields, making the search algorithm impossible to change without a frontend update.

**Warning signs:** Frontend JavaScript directly constructing SQL-like filter objects; API responses containing internal IDs used as display identifiers; frontend parsing FEN strings to display board positions rather than receiving display-ready data.

**Prevention strategy:**
- Define a stable API contract for the search endpoint early: request takes `{ fen, color_filter, time_control, rated, recency, move_order }`, response returns `{ total_games, matches: [{ game_id, platform, platform_url, result, opponent, date, position_fen }] }`. Internal hashes never appear in the API response.
- The "position_fen" in the response is the FEN at the matched position (for display), not the search key.
- Version the API (`/api/v1/`) from day one so breaking changes can be made in `/api/v2/` without breaking existing clients.
- Keep the FEN-to-board rendering entirely on the frontend using Chessground or react-chessboard; the backend never renders board images.

**Phase to address:** Phase 2–3 boundary. Define the API contract before frontend development begins.

---

*Research completed: 2026-03-11*
*Based on: chess.com Public API documentation, lichess API documentation, python-chess library documentation, common patterns in open-source chess analysis tools, and general experience with chess platform development.*
