# Pitfalls Research

**Domain:** Per-position metadata enrichment, engine analysis import, and endgame classification for an existing chess analytics platform (FlawChess v1.5)
**Researched:** 2026-03-23
**Confidence:** HIGH (chess.com API limitations confirmed via official forum moderator statement; PostgreSQL behavior confirmed via official docs; python-chess material APIs confirmed from maintainer discussion); MEDIUM (lichess eval coverage rate, game phase edge cases from community sources)

---

## Critical Pitfalls

### Pitfall 1: chess.com Accuracy Data Is Absent for Most Games

**What goes wrong:**
The chess.com archive API (`/pub/player/{username}/games/{YYYY}/{MM}`) does include an `accuracies` field (`{"white": 87.6, "black": 23.6}`) — but only for games that have already been reviewed by the user via the "Game Review" feature. The vast majority of a user's games have never been reviewed. For those games, the `accuracies` field is either absent from the JSON or `null`. A chess.com moderator has confirmed: "game phase accuracy values only show for games with reviews and are not stored in the DB." The public API is also in **maintenance mode only** — no new analysis fields will be added.

There is no API endpoint to trigger a game review programmatically. Free users get 1 review per day; Diamond members get unlimited. Move-level evaluations (centipawn scores, accuracy per move) are not exposed at all through the public API — only the single overall accuracy float per player is available.

**Why it happens:**
Developers assume "chess.com shows accuracy so the API must return it" and design their import pipeline expecting a field that will be absent for 95%+ of games. The field name `accuracies` in the official docs sounds definitive but is actually conditional.

**How to avoid:**
- Store accuracy as `FLOAT NULL` on the `games` table — never `NOT NULL`
- On import, check `game.get("accuracies")` before accessing `.get("white")` / `.get("black")`
- Design the endgame analytics UI to degrade gracefully when accuracy is null — show "n/a" rather than 0% or crashing
- Do NOT advertise "import your accuracy data" as a core feature — it will be absent for most users
- Limit scope to the overall accuracy float that IS available; per-phase accuracy and per-move quality are not accessible

**Warning signs:**
- Import pipeline accesses `game["accuracies"]["white"]` with no null guard — fails immediately on first unreviewed game
- UI shows 0% accuracy for all endgame positions rather than "no data"

**Phase to address:** Engine analysis import phase (schema design + normalization)

---

### Pitfall 2: lichess Evals Are Absent for Non-Analyzed Games

**What goes wrong:**
lichess game exports support an `evals=true` parameter that embeds Stockfish centipawn annotations as `{ [%eval 0.17] }` comments inside PGN move nodes. However, this only returns data for games that have had computer analysis requested and computed. A game played without ever requesting "Request a computer analysis" on lichess will export with no eval annotations, even with `evals=true` passed to the API.

Many casual games, especially older ones, have never been analyzed. The `evals` annotations will be present for some games and completely absent for others in the same API response. Additionally, the format uses centipawns from White's perspective (e.g., `[%eval -3.15]`), and mate scores use the format `[%eval #5]` (White mates in 5) or `[%eval #-3]` (Black mates in 3) — the sign on the mate count is not obvious and easy to misparse.

**Why it happens:**
Developers add `evals=true` to the lichess API request and assume the response will contain eval data for all games. The conditional nature of lichess analysis is not clearly documented at the API level.

**How to avoid:**
- Parse `[%eval ...]` annotations defensively — always check that the annotation exists before using it
- Use python-chess's `node.eval()` API (returns `chess.engine.PovScore | None`) rather than regex-parsing PGN comment strings manually
- Store eval as `SMALLINT NULL` (centipawns) on `game_positions` — `None` for positions without analysis
- Never assume evals will exist — design queries and UI to work on the subset that has data
- For the current lichess request in `lichess_client.py`: add `"evals": True` to the params dict, but gate all downstream processing on the presence of the annotation

**Warning signs:**
- Regex-based eval extraction crashes or returns garbage on mate scores like `#-3`
- Import logs show parsing failures only for certain games (the unanalyzed ones have no `[%eval]` nodes — skipping silently is correct, crashing is not)

**Phase to address:** Engine analysis import phase (lichess client + PGN parsing)

---

### Pitfall 3: Backfilling game_positions for Existing Games Is an OOM Risk

**What goes wrong:**
Adding new columns to `game_positions` (e.g., `game_phase`, `material_signature`, `endgame_class`) and then running a backfill script that recomputes values for all existing rows will attempt to load and update a very large number of rows. The production server already hit an OOM kill at batch_size=50 during initial import — the same risk applies to backfill. A naive `UPDATE game_positions SET game_phase = compute(fen) WHERE game_phase IS NULL` across millions of rows will lock the table for minutes and likely trigger the OOM killer on the 3.7GB/2GB-swap Hetzner instance.

The `game_positions` table has no stored FEN — only Zobrist hashes. Computing `game_phase` requires replaying PGN moves from `games.pgn`, which means the backfill must join `game_positions` to `games`, re-parse each PGN, and update rows in chunks. This is a multi-step operation, not a simple column update.

**Why it happens:**
Backfill migrations are typically modeled as simple column-population scripts. For `game_positions`, the data needed (FEN/board state per ply) is not stored — it must be recomputed from PGN, making the backfill significantly more expensive and memory-intensive than it appears.

**How to avoid:**
- Add new columns as `NULL` (no `NOT NULL` constraint) via Alembic — PostgreSQL 18 adds nullable columns near-instantly with no table rewrite
- Write the backfill as a standalone Python script (not an Alembic migration) that processes one game at a time, calling `hashes_for_game` (or a new `metadata_for_game` function that also returns phase/material per ply), and batches position `UPDATE`s using primary key range pagination
- Use the same batch_size=10 games pattern from `import_service.py` — 10 games × ~40 positions = ~400 rows per UPDATE batch
- Add a `game_id` range parameter so the backfill can be resumed after interruption
- Run the backfill as a one-off script via `uv run python scripts/backfill_position_metadata.py` rather than inside an Alembic migration (migrations must be fast and transactional — backfills are neither)
- Monitor PostgreSQL memory during the first test run with `ssh flawchess "docker stats --no-stream"`

**Warning signs:**
- Backfill script does a single large `UPDATE ... WHERE game_phase IS NULL` without batching
- Alembic migration includes a Python loop that processes all games — will time out or OOM on production
- No resume capability — if the server OOMs midway, the half-backfilled state is hard to recover from

**Phase to address:** Database schema phase (add columns) + a dedicated backfill phase

---

### Pitfall 4: Material Signature Normalization Is Not Canonical Without a Convention

**What goes wrong:**
When computing endgame class, a material signature like "KRP vs KR" must be consistent regardless of which player is White. If the user played Black in a rook + pawn vs rook endgame, the raw position is "KR vs KRP" — but this should map to the same endgame class as "KRP vs KR". Without a normalization step, the same endgame class gets stored under two different strings, splitting statistics in half and making queries return wrong aggregates.

The convention used must also handle equal material (e.g., "KR vs KR" is symmetric and only has one form), unequal material where it's unclear which side has more (e.g., "KQRP vs KRR"), and the perspective issue (White may have more material but the user played Black).

**Why it happens:**
It is natural to compute pieces for White and Black separately and join with "vs" — but the result depends on which side is White. Without an explicit "stronger side always goes first" or "alphabetical sort" convention enforced at compute time, the normalization is inconsistent.

**How to avoid:**
- Define a canonical form: always sort the two sides so the side with higher material value goes first; if equal, use lexicographic ordering of the piece string
- Use abbreviations based on piece count: `K` + one letter per extra piece in piece-value-descending order (Q, R, B, N, P) — e.g., `KQRP` for a King + Queen + Rook + Pawn
- Store a separate `user_material_side` flag (stronger/weaker/equal) so queries can filter by whether the user was the stronger or weaker side, independent of the canonical form
- Test normalization with symmetric cases (KR_KR), asymmetric cases (KRP_KR and KR_KRP must map to the same canonical form), and edge cases like bare kings (KK) or promotion-related material mismatches
- Write a unit test: for any position, rotating the board (swapping colors) should produce the same `material_signature`

**Warning signs:**
- Analytics query for "rook endgames" returns half the expected games
- `material_signature` values like `KR_KRP` and `KRP_KR` both appear in the database
- Statistics vary depending on whether the user played White or Black in the same type of endgame

**Phase to address:** Material computation phase (signature normalization logic)

---

### Pitfall 5: Game Phase Boundaries Have No Universal Standard — Inconsistency Across Games

**What goes wrong:**
The terms "opening", "middlegame", and "endgame" have no universally agreed numerical definition. Chess.com classifies phase per game (their insight data is not in the API). Stockfish uses a tapered, continuous phase value — not a discrete threshold. Common heuristics disagree: some treat any queenless position as an endgame; others require both queens and at least two minor pieces to be off the board; others use total piece weight thresholds.

If the phase boundary heuristic is poorly chosen, a game where queens are traded on move 10 will be flagged as "endgame" for moves 10-60, including a long tactical middlegame played without queens. Conversely, a long pawn endgame might not be detected until well into the endgame phase.

**Why it happens:**
Phase detection seems simple ("count pieces") but real games have high variance: early queen trades, quick piece exchanges, games without queens but rich in minor pieces. A single threshold cannot fit all game types cleanly.

**How to avoid:**
- Use a tapered phase score derived from non-pawn, non-king material: `phase = sum(piece_phase_weights_for_remaining_pieces)` where weights are Queen=4, Rook=2, Knight=1, Bishop=1. Max is 24 (starting position). Normalize to 0-24.
- Classify as: phase >= 18 → opening; 8 <= phase < 18 → middlegame; phase < 8 → endgame. These thresholds match typical Stockfish-adjacent conventions (total minor+rook phase weight ≤ 8 indicates endgame-like material)
- Supplement with a ply floor: never classify ply < 10 as middlegame or endgame regardless of material (accounts for sacrificial openings)
- Accept that the boundary is a heuristic — document the exact formula so users can understand what they're looking at
- Do NOT attempt to match chess.com's undisclosed phase boundaries (not in API, not documented)

**Warning signs:**
- All queen trades on move 8 result in "endgame" label for the next 60 moves of a tactical game
- Stats show 60% of positions classified as "endgame" for blitz games (too aggressive threshold)
- Different games of the same type produce wildly different phase breakdowns

**Phase to address:** Phase computation phase (design + unit tests covering edge cases)

---

### Pitfall 6: Adding Many Nullable Columns to game_positions Risks Postgres Page Bloat

**What goes wrong:**
`game_positions` has ~40 rows per game. A user with 5,000 games has ~200,000 rows. A multi-user platform will have millions of rows total. Adding 4+ nullable columns (game_phase, material_signature, endgame_class, eval_cp) to this table does not require a table rewrite in PostgreSQL 18 (nullable columns with no default are near-instant). However, once the backfill runs and rows are updated, PostgreSQL creates new row versions (dead tuples) via MVCC. Without autovacuum catching up, dead tuple accumulation inflates table and index size, increasing query I/O and slowing the existing Zobrist hash queries.

The existing indexes `ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash` are critical for query performance. Excessive dead tuples after backfill can bloat these indexes.

**Why it happens:**
MVCC writes new row versions for every UPDATE. A backfill that touches every row in `game_positions` is essentially a full-table update — it creates as many dead tuples as there are rows. Autovacuum may not keep up with the rate of dead tuple generation during a fast backfill.

**How to avoid:**
- Run `ANALYZE game_positions;` after the backfill completes to update statistics
- Run `VACUUM game_positions;` (not FULL — that locks) after backfill to reclaim dead tuple space
- Set `autovacuum_vacuum_cost_delay` to a lower value temporarily if the table is idle during backfill
- Monitor with `SELECT n_dead_tup, n_live_tup FROM pg_stat_user_tables WHERE relname = 'game_positions';` before and after backfill
- For the small Hetzner instance, run the backfill during off-peak hours and pause between game batches to give autovacuum time to reclaim space

**Warning signs:**
- Zobrist hash queries become 3-10x slower after backfill completes
- `pg_stat_user_tables` shows `n_dead_tup` growing beyond `n_live_tup`
- `\d+ game_positions` in psql shows table size doubling after backfill with no corresponding data growth

**Phase to address:** Backfill phase (post-completion cleanup step)

---

### Pitfall 7: Lichess evals=true Parameter Changes the NDJSON Response Structure

**What goes wrong:**
The current `lichess_client.py` fetches games as NDJSON with `pgnInJson: True` and parses the `pgn` field from each JSON object. When `evals=True` is added, the PGN string will contain embedded `[%eval ...]` annotations inside move text nodes. If the existing `normalize_lichess_game` function stores the full PGN including eval annotations into `games.pgn`, then `hashes_for_game` (which re-parses the PGN) will encounter annotated PGN. python-chess handles annotated PGN correctly via `chess.pgn.read_game`, but any downstream code that does string-level PGN parsing or expects clean algebraic notation without comments will break silently.

There is also a risk that `evals=True` significantly increases the size of each NDJSON line for analyzed games, increasing streaming time and memory usage per line.

**Why it happens:**
Annotated PGN is a superset of plain PGN and looks identical when the game has no analysis. The difference only appears at runtime for games with analysis. Testing with non-analyzed games will pass; only analyzed games reveal the issue.

**How to avoid:**
- Always use `chess.pgn.read_game` for PGN parsing — it handles annotations correctly
- Never regex-parse move text from PGN strings for move extraction
- Test the import pipeline specifically on a lichess game that has computer analysis enabled
- Consider whether to store the annotated PGN (with evals inline) or strip annotations before storage: storing annotated PGN is fine since `hashes_for_game` uses `chess.pgn.read_game`, but it will increase `games.pgn` column size for analyzed games

**Warning signs:**
- `hashes_for_game` fails on a game whose PGN contains `[%eval 0.35]` annotations
- Eval extraction via `node.eval()` returns `None` even after adding `evals=True` to the request (means the game was never analyzed on lichess)

**Phase to address:** Engine analysis import phase (lichess client modification)

---

### Pitfall 8: Backfill Strategy Must Handle the games.pgn → game_positions Join Correctly

**What goes wrong:**
`game_positions` does not store a FEN per ply — only Zobrist hashes and `move_san`. To compute `game_phase`, `material_signature`, and `endgame_class` for each position row, the backfill must replay the PGN from `games.pgn` and, at each ply, capture the board state. The `game_positions` rows must then be updated with the computed values, matched by `(game_id, ply)`.

A common mistake is to write a per-position backfill that somehow derives game phase from only the data available in `game_positions` (hashes and move_san). There is not enough information — you need the full board state, which requires PGN replay.

**Why it happens:**
Developers look at the `game_positions` table columns and try to write a pure-SQL migration. The missing FEN makes that impossible for phase/material computation — the PGN must be re-parsed.

**How to avoid:**
- Write the backfill as: `SELECT g.id, g.pgn FROM games g WHERE EXISTS (SELECT 1 FROM game_positions gp WHERE gp.game_id = g.id AND gp.game_phase IS NULL LIMIT 1)` — iterate games, not positions
- For each game, call a new `metadata_for_game(pgn)` function that returns `List[(ply, game_phase, material_imbalance, material_signature, endgame_class)]`
- Use bulk `UPDATE game_positions SET game_phase = data.phase, ... FROM (VALUES ...) AS data(ply, ...) WHERE game_positions.game_id = $1 AND game_positions.ply = data.ply`
- Reuse the existing batch pattern from `import_service.py` — iterate games in batches of 10, build the UPDATE values in memory, execute as a single statement

**Warning signs:**
- Backfill script iterates `game_positions` rows individually and makes per-row DB calls
- Backfill query lacks a `LIMIT` / pagination mechanism — processes all rows in one transaction

**Phase to address:** Backfill phase (script design)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store `game_phase` as `VARCHAR` instead of a typed enum or SMALLINT | Easier to read in psql | Typo-prone; no DB-level constraint; string comparison slower than integer | Never — use SMALLINT (0=opening,1=middlegame,2=endgame) or a PG enum |
| Assume chess.com accuracy is always present; no null handling | One less null check | Crashes on first unreviewed game (likely the first game of every user) | Never |
| Run backfill inside an Alembic migration | Single deploy step | Migrations are transactional — a 10-minute Python loop blocks the migration lock and OOMs | Never for compute-heavy backfills |
| Compute material signature on-the-fly in queries | No schema change needed | Repeated PGN re-parsing per query; unindexable; query latency at scale | Never — compute at import time |
| Use a simple `ply < 20` threshold for opening phase | Zero computation | Wrong for gambits, short games, rapid piece trades | Never — use piece count heuristic |
| Skip VACUUM after backfill | Saves a step | Query performance degrades due to dead tuple bloat | Never — always VACUUM after large table updates |
| Store per-move eval in `game_positions` for moves without analysis as 0 | Simpler query | 0 is a valid eval (equal position) — impossible to distinguish "no data" from "equal" | Never — use NULL for absent evals |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| chess.com API + accuracy | Access `game["accuracies"]["white"]` directly | Always check `game.get("accuracies")` first; both white and black may be absent |
| chess.com API + move evals | Expect per-move centipawn from archive API | Move-level evals are not in the public API; only overall accuracy floats when reviewed |
| lichess API + evals | Expect evals for all games after adding `evals=True` | Evals only present for games with computer analysis; always check `node.eval()` for None |
| lichess PGN eval format | Parse `[%eval 0.17]` with regex | Use `chess.pgn.read_game` then `node.eval()` — returns `chess.engine.PovScore | None` |
| lichess mate eval format | Treat `[%eval #-3]` as centipawn value | `#N` = mate, `#-N` = mated; always branch on `PovScore.is_mate()` before `.score()` |
| python-chess + material count | Use `board.piece_map()` with dict comprehension | Use bitboard operations: `chess.popcount(board.occupied_co[WHITE] & board.queens)` for efficiency |
| PostgreSQL + new nullable columns | Add column with `NOT NULL DEFAULT 0` | Add as `NULL` first; backfill later; then add `NOT NULL` constraint after backfill completes |
| Alembic + compute-heavy backfill | Put Python backfill loop inside `op.execute()` or upgrade function | Use a separate script run after migration; migrations must be fast and transactional |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-position PGN re-parse in backfill | Backfill takes hours, OOMs on production | Parse PGN once per game, emit metadata for all plies at once | At ~5,000+ games (200k+ position rows) |
| Non-batched UPDATE during backfill | Single multi-hour transaction, table lock | Batch by game_id ranges; commit after each batch of 10 games | Any table size above ~1,000 rows |
| Dead tuple bloat after backfill | Existing Zobrist hash queries 3-10x slower | Run VACUUM game_positions after backfill | Immediately post-backfill |
| Endgame query with LIKE on material_signature | Slow full-table scan for "rook endgames" | Add index on material_signature; or use a `endgame_class` integer column with exact equality | At ~50k position rows or more |
| Joining game_positions to games for phase-based stats | N+1 query or expensive join without index | Denormalize game_phase onto game_positions at import time (which is the plan); never compute at query time | Any non-trivial dataset |
| Storing full eval annotations in games.pgn for analyzed lichess games | games.pgn column grows 3-5x for analyzed games | Acceptable at current scale; if PGN storage becomes significant, extract evals into separate table | At ~100k analyzed games |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Expose `material_signature` containing opponent piece counts in API response without auth check | Inadvertently exposing private game data via analytics endpoints | All endgame analytics endpoints must verify `user_id == current_user.id` before querying |
| Log PGN strings in full during backfill errors | PGN may contain username/rating data; logs accumulate and are not rotated | Log `game_id` only in backfill error messages, not the full PGN string |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Show accuracy statistics for "all games" when only reviewed games have accuracy data | User sees misleadingly low counts ("only 47 of 2,341 games have accuracy data") | Surface clearly: "Accuracy data available for X reviewed games" with a tooltip explaining reviews |
| Display "0.0" for centipawn eval when data is absent | User thinks every unanalyzed position is exactly equal | Show "—" or "n/a" when eval is NULL, not 0 |
| Endgame filter shows "no games" for users with few analyzed games | User thinks the feature is broken | Show a "No analyzed endgame data yet" empty state with an explanation |
| Phase boundaries produce counter-intuitive phase labels on short games | 10-move game shows "endgame" from move 8 due to early simplification | Enforce a ply floor: never label ply < 8 as endgame regardless of material |

---

## "Looks Done But Isn't" Checklist

- [ ] **chess.com accuracy:** Import pipeline tested against a game that has NOT been reviewed — `accuracies` field absent without crashing
- [ ] **chess.com accuracy:** Import pipeline tested against a game that HAS been reviewed — both `white` and `black` accuracy fields stored correctly
- [ ] **lichess evals:** Import pipeline tested against a lichess game with computer analysis — `[%eval ...]` annotations parsed correctly
- [ ] **lichess evals:** Import pipeline tested against a lichess game WITHOUT computer analysis — no crash, positions stored with `eval_cp = NULL`
- [ ] **lichess mate evals:** Import pipeline handles `[%eval #5]` and `[%eval #-3]` without crashing or treating mate as a centipawn value
- [ ] **Material signature:** Same endgame type produces identical `material_signature` regardless of which color the user played — verified by unit test
- [ ] **Material signature:** Symmetric positions (KR vs KR) produce a single canonical form, not two
- [ ] **Game phase:** Early queen trade (e.g., ply 12) does not immediately classify remaining 50 moves as "endgame"
- [ ] **Backfill:** Backfill script can be re-run safely after a partial run — idempotent (skips rows where `game_phase IS NOT NULL`)
- [ ] **Backfill:** Backfill completes on production without triggering OOM killer — tested with `docker stats` monitoring
- [ ] **Backfill:** VACUUM run after backfill completes — `pg_stat_user_tables.n_dead_tup` returns to near-zero
- [ ] **Endgame analytics:** Empty state shown for users with no endgame data (new users, users with no analyzed games)
- [ ] **Null evals UI:** Positions with `eval_cp = NULL` display "—" not "0" or crash

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Backfill OOM kills PostgreSQL | MEDIUM | Server restarts automatically; backfill script detects `game_phase IS NOT NULL` rows and resumes; reduce batch size to 5 games and retry |
| Inconsistent material_signature stored (non-canonical form) | HIGH | Write a fix script to re-normalize all stored signatures; add unit test to prevent regression; requires re-running backfill for affected rows |
| chess.com accuracy imported as 0 for unreviewed games | MEDIUM | Add NULL guard to import; run a targeted UPDATE to set `accuracy_white = NULL WHERE accuracy_white = 0 AND games were not reviewed` (requires cross-referencing import timestamp) |
| Dead tuple bloat post-backfill slows queries | LOW | `VACUUM game_positions;` immediately resolves; no data loss |
| Game phase boundary heuristic produces wrong results | MEDIUM | The phase value is recomputable from PGN — update the heuristic, drop the `game_phase` column, re-add it, re-run backfill |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| chess.com accuracy absent for unreviewed games | Engine analysis import phase | Import 100 games from a free user account; confirm most have `accuracy_white = NULL` without errors |
| lichess evals absent for non-analyzed games | Engine analysis import phase | Import a lichess game without analysis; confirm no crash and `eval_cp = NULL` on all positions |
| Lichess mate eval format misparse | Engine analysis import phase | Unit test for `[%eval #5]` and `[%eval #-3]` parsing |
| Non-canonical material signature | Material computation phase | Unit test: KR_KRP and KRP_KR map to same canonical form |
| Inconsistent phase boundaries | Phase computation phase | Unit test: early queen trade game does not become "endgame" by move 15 |
| Backfill OOM on production | Backfill phase | Run with `batch_size=10`, monitor with `docker stats` on staging first |
| Dead tuple bloat post-backfill | Backfill phase (cleanup step) | `n_dead_tup` near zero in `pg_stat_user_tables` after VACUUM |
| Backfill non-idempotent | Backfill phase | Re-run backfill on already-processed database; row counts unchanged, no duplicate updates |
| Annotated PGN breaks downstream parsing | Engine analysis import phase | `hashes_for_game` unit test on PGN with embedded `[%eval]` annotations |
| Null eval displayed as 0 in UI | Endgame analytics UI phase | QA: position without analysis shows "—" not "0.00" |

---

## Sources

- [chess.com forum: Insight data in public APIs (moderator confirms analysis data not in public API)](https://www.chess.com/forum/view/site-feedback/insight-data-in-public-apis)
- [chess.com API: Published-Data API official help article](https://support.chess.com/en/articles/9650547-published-data-api)
- [chess.com forum: accuracy field absent for unreviewed games](https://www.chess.com/forum/view/game-analysis/how-come-some-of-my-games-dont-show-anything-in-the-accuracy-column)
- [lichess forum: exporting PGN with computer analysis](https://lichess.org/forum/lichess-feedback/is-there-a-way-to-export-the-pgn-games-with-computer-analysis)
- [lichess API docs: evals parameter](https://lichess.org/api)
- [python-chess: efficient material balance (maintainer recommendation)](https://github.com/niklasf/python-chess/discussions/864)
- [Chessprogramming wiki: Tapered Eval — piece phase weights](https://www.chessprogramming.org/Tapered_Eval)
- [Chessprogramming wiki: Game Phases](https://www.chessprogramming.org/Game_Phases)
- [PostgreSQL docs: ALTER TABLE — adding nullable columns is near-instant](https://www.postgresql.org/docs/current/ddl-alter.html)
- [PostgreSQL: batch UPDATE strategy for large tables](https://blog.codacy.com/how-to-update-large-tables-in-postgresql)
- [ChessBase: endgame classification format (RB-RN notation)](http://help.chessbase.com/CBase/14/Eng/endgame_classification.htm)
- [FlawChess CLAUDE.md — batch_size=10 OOM history](../CLAUDE.md)

---
*Pitfalls research for: FlawChess v1.5 — per-position metadata, engine analysis import, and endgame analytics*
*Researched: 2026-03-23*
