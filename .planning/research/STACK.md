# Stack Research

**Domain:** Chess analytics platform — per-position metadata enrichment and engine analysis import (v1.5)
**Researched:** 2026-03-23
**Confidence:** HIGH (API findings verified via official lichess YAML spec, chess.com API documentation, official python-chess 1.11.2 docs)

---

## Scope Note

This document covers ONLY new capabilities needed for v1.5 (game phase, material, endgame class, engine analysis import).
The base stack (FastAPI, React 19, PostgreSQL, SQLAlchemy async, python-chess, TanStack Query, Vite, Tailwind, shadcn/ui) is validated and in production.
Those choices are not re-evaluated here.

**Bottom line: no new libraries.** Every required capability is already available in the installed stack.

---

## Recommended Stack

### Core Technologies (No Changes for v1.5)

All v1.5 features are implemented using existing dependencies:

| Technology | Version in Use | Relevant Capability for v1.5 |
|------------|---------------|------------------------------|
| python-chess | >=1.10.0 (1.11.2 latest) | `board.pieces()` for material counting, `node.eval()` for PGN eval parsing, `node.nags` for move quality annotations |
| FastAPI | >=0.115.x | New `/endgames` router endpoints |
| SQLAlchemy 2.x async | >=2.0.0 | New columns on `game_positions` and `games`; new aggregation queries |
| PostgreSQL 18 | (Docker, pinned) | Composite B-tree indexes on new integer columns |
| httpx async | >=0.27.0 | Existing platform clients gain new query params only — no client changes |

### python-chess API Surface for New Computations

All methods confirmed available in python-chess 1.10.x+ (stable since 1.x):

**Material counting:**
```python
import chess

# Count pieces by type and color — returns SquareSet, use len()
len(board.pieces(chess.QUEEN, chess.WHITE))    # 0 or 1
len(board.pieces(chess.ROOK, chess.BLACK))     # 0–2
len(board.pieces(chess.BISHOP, chess.WHITE))   # 0–2
len(board.pieces(chess.KNIGHT, chess.BLACK))   # 0–2
len(board.pieces(chess.PAWN, chess.WHITE))     # 0–8

# Piece type constants: PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6

# Insufficient material check (useful for endgame branch)
board.has_insufficient_material(chess.WHITE)
board.has_insufficient_material(chess.BLACK)
board.is_insufficient_material()
```

**PGN eval parsing (already in python-chess, zero new imports):**
```python
import chess.pgn

node = ...  # chess.pgn.ChildNode from game.mainline()
score = node.eval()                     # chess.engine.PovScore | None
if score is not None:
    cp   = score.white().score()        # int centipawns from white's view; None if mate
    mate = score.white().mate()         # int mate-in-N from white's view; None if not mate
    depth = node.eval_depth()           # int depth annotation; None if not present
```

**NAG move quality annotations:**
```python
# Standard NAG integer constants:
# chess.pgn.NAG_GOOD_MOVE        = 1   (!)
# chess.pgn.NAG_MISTAKE          = 2   (?)
# chess.pgn.NAG_BRILLIANT_MOVE   = 3   (!!)
# chess.pgn.NAG_BLUNDER          = 4   (??)
# chess.pgn.NAG_SPECULATIVE_MOVE = 5   (!?)
# chess.pgn.NAG_DUBIOUS_MOVE     = 6   (?!)

node.nags   # set[int] — e.g. {4} = blunder
```

**Clock annotation (already used in `zobrist.py`):**
```python
node.clock()    # float | None — seconds remaining from [%clk ...]
```

---

## Platform API Integration Points

### chess.com — Accuracy Only, No Per-Move Evals

**What is available via the existing monthly archive endpoint:**

The game JSON object already fetched by `chesscom_client.py` includes an optional `accuracies` field:

```json
{
  "accuracies": {
    "white": 87.3,
    "black": 72.1
  }
}
```

This field is absent when the game has not been analyzed on chess.com. No additional API call is needed.

**What is NOT available (confirmed by chess.com moderators):**

Per-move evaluation scores, centipawn values, and move quality annotations are not exposed by the chess.com public API. No workaround exists within the documented public API. The CAPS accuracy algorithm output is only available as the game-level `accuracies` field.

**Integration:** One line in `normalize_chesscom_game()`. The raw game dict already flows through normalization — extract `game.get("accuracies", {})` and map `white`/`black` keys to new `games` table columns.

### lichess — Per-Move Evals and Per-Game Accuracy

lichess exposes two distinct data points that require two different approaches:

**1. Per-move evals — already stored in the database, no new API call:**

When lichess games have been analyzed, `[%eval ...]` annotations are embedded in the PGN. The PGN is already stored in the `games.pgn` TEXT column. python-chess parses these via `node.eval()`.

Example PGN from lichess with evals:
```
1. e4 { [%eval 0.17] [%clk 0:01:00] } 1... e5 { [%eval 0.19] [%clk 0:01:00] }
```

This means all historical games already in the database can have evals extracted (at migration time or lazily) by re-parsing stored PGNs — no API round-trips.

**2. Requesting evals at import time — add one param to existing client:**

Add `evals=True` to the params dict in `lichess_client.py`. This ensures PGN evals are included for future imports of analyzed games:

```python
# lichess_client.py — add to existing params dict:
params["evals"] = True
```

Note: `evals=true` returns data only for games that lichess has already analyzed. Not all games have analysis; the param is safe to add always.

**3. Per-game accuracy via JSON — add one param:**

The NDJSON streaming endpoint supports `accuracy=true`. This enriches the existing JSON game objects with accuracy data nested under `players`:

```json
{
  "players": {
    "white": {
      "accuracy": 88,
      "analysis": {
        "inaccuracy": 3,
        "mistake": 1,
        "blunder": 0,
        "acpl": 28
      }
    },
    "black": {
      "accuracy": 79,
      "analysis": { ... }
    }
  }
}
```

The `accuracy` integer and `analysis` object appear only when the game has been analyzed. Safe to request always.

```python
# lichess_client.py — add to existing params dict:
params["accuracy"] = True
```

**Integration:** Update `normalize_lichess_game()` to extract `players.white.accuracy` and `players.black.accuracy`.

Confirmed via: [lichess-org/api OpenAPI spec](https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/tags/games/api-games-user-username.yaml) — `evals` and `accuracy` are documented query parameters.

---

## New Database Columns

### On `game_positions` — per half-move metadata

Add these columns. All computed during the existing import loop with no additional I/O:

| Column | SQLAlchemy Type | Notes |
|--------|----------------|-------|
| `game_phase` | `SmallInteger`, NOT NULL | 0=opening, 1=middlegame, 2=endgame. Integer beats enum for composite index efficiency and range queries. |
| `material_white` | `SmallInteger`, NOT NULL | Total non-king material value for white using standard piece values (Q=9, R=5, B=3, N=3). Range 0–39. |
| `material_black` | `SmallInteger`, NOT NULL | Total non-king material value for black. Same scale. |
| `endgame_class` | `String(20)`, nullable | Normalized material signature string, e.g. `"KQvKR"`, `"KRvK"`, `"KPvK"`. NULL when `game_phase != 2`. |
| `eval_cp` | `SmallInteger`, nullable | Centipawn eval from `[%eval ...]` annotation; NULL if not available or if mate score. From white's perspective. |
| `eval_mate` | `SmallInteger`, nullable | Mate-in-N from eval annotation; NULL if not available or if not a mate score. From white's perspective. |

### On `games` — per-game accuracy from platform

| Column | SQLAlchemy Type | Notes |
|--------|----------------|-------|
| `white_accuracy` | `Float`, nullable | Game-level CAPS/accuracy % from chess.com `accuracies.white` or lichess `players.white.accuracy`. NULL if game not analyzed. |
| `black_accuracy` | `Float`, nullable | Same for black. |

### Indexing Strategy

The primary Endgames tab query pattern is:
```sql
WHERE user_id = $1 AND game_phase = 2 AND endgame_class = $2
```

Add one composite index to `game_positions`:
```python
Index("ix_gp_user_phase_class", "user_id", "game_phase", "endgame_class")
```

This index also accelerates `WHERE user_id = $1 AND game_phase = 2` (endgame stats without class filter) and `WHERE user_id = $1 AND game_phase = ?` (phase-level statistics). No partial indexes needed — the composite B-tree handles all three query shapes.

The four existing hash indexes (`ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash`, `ix_gp_user_full_hash_move_san`) are unchanged.

---

## Game Phase Detection — Implementation Recommendation

There is no standard built-in method in python-chess or any library. Use a material-threshold approach, which is what chess engines use (Stockfish, Crafty, others). No ply-count method is needed.

**Recommended thresholds (compute `total_material = material_white + material_black`):**

| Phase | Condition | Rationale |
|-------|-----------|-----------|
| Opening | `total_material >= 56` | Both queens + most pieces present. Full starting material = 78 (Q×2=18, R×4=20, B×4=12, N×4=12, pawns excluded from phase calc). Opening ends when 1–2 minor pieces have been traded. |
| Middlegame | `20 <= total_material < 56` | Active piece play with reduced force. |
| Endgame | `total_material < 20` | Queens traded or most heavy pieces gone. |

These thresholds are deliberately simple — they are for user-facing statistics categories, not engine evaluation. Exact boundary values can be tuned after seeing real data; the column is `SmallInteger` so a re-migration to adjust thresholds means a data backfill, not a schema change.

**Pawns excluded from phase threshold:** Pawns do not strongly signal game phase (a position with 16 pawns and no pieces is clearly an endgame). Use only Q/R/B/N material values.

---

## Endgame Classification — Material Signature

No library method exists. Build a compact string from `board.pieces()`:

- List piece letters (Q, R, B, N, P) for each side, most valuable first
- Format: `"K{white_pieces}vK{black_pieces}"` — always include K on both sides
- Examples: `"KQRvKR"`, `"KRvK"`, `"KBNvK"`, `"KPvK"`, `"KvK"` (bare kings)
- Only compute when `game_phase == 2` — store NULL otherwise to avoid polluting opening/middlegame rows

A `String(20)` column fits all realistic endgame signatures. The `v` separator keeps it unambiguous.

---

## Integration Points in the Existing Import Pipeline

The existing flow in `import_service.py::_flush_batch` → `zobrist.py::hashes_for_game`:

1. Parses PGN via `chess.pgn.read_game()`
2. Iterates `game.mainline()` node-by-node
3. Computes hashes via `compute_hashes(board)` at each ply
4. Pushes move to board
5. Appends a dict to `position_rows`

**New computations slot into step 3**, after `compute_hashes(board)` and before `board.push(node.move)`:

```python
game_phase    = compute_game_phase(board)           # uses board.pieces()
mat_w         = compute_material(board, chess.WHITE)
mat_b         = compute_material(board, chess.BLACK)
endgame_cls   = classify_endgame(board) if game_phase == 2 else None
eval_cp, eval_mate = parse_node_eval(node)          # node.eval()
```

All new values append to the existing `position_rows` dict. Zero additional DB round-trips. No async changes. The natural extension point is either `zobrist.py` (renamed to `position_metadata.py`) or a parallel `metadata.py` module that `_flush_batch` calls alongside `hashes_for_game`.

**Accuracy extraction** is a two-line change in each normalizer:
- `normalize_chesscom_game()` — extract `game.get("accuracies", {}).get("white")` and `black`
- `normalize_lichess_game()` — extract `players["white"].get("accuracy")` and `black`

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Local Stockfish (python-chess UCI) | OOM risk on 3.7GB server; async pipeline complexity; per-position eval during import would be catastrophically slow at scale; explicitly out of scope per PROJECT.md | Import platform-provided evals from existing PGN `[%eval ...]` annotations |
| `berserk` library | Blocking (not async); project constraint violation | Existing `httpx.AsyncClient` in `lichess_client.py` — add two params |
| JSONB columns for material data | 100–1000x slower than integer columns for the equality/range queries the Endgames tab requires | Separate `SmallInteger` columns for `material_white`, `material_black`, `game_phase` |
| Per-ply accuracy column | chess.com does not expose per-move accuracy; computing it requires local Stockfish | Per-game accuracy on `games` table is sufficient for phase-based statistics |
| Syzygy/Gaviota tablebase probing | Requires large binary files (10s of GB) incompatible with the 75GB Hetzner disk budget; overkill for statistics classification | Custom material-signature string built from `board.pieces()` |
| Re-fetching all lichess games with `evals=true` | Unnecessary — evals are already embedded in stored PGNs for analyzed games; re-fetching costs rate-limited API calls | Re-parse stored `games.pgn` column to extract `[%eval ...]` annotations at migration |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Material-count thresholds for phase detection | Ply-based opening boundary (e.g. ply <= 10 = opening) | Ply count is too rigid; a theoretical Sicilian Najdorf line can still be "opening" at ply 30. Material thresholds reflect the actual piece complexity of the position. |
| `SmallInteger` columns for phase/material | PostgreSQL enum type for `game_phase` | Enum requires a migration to add values; `SmallInteger` with application-layer constants (0/1/2) is simpler and equally fast for indexed queries. |
| Extract evals from stored PGN at migration | Request evals fresh from lichess API | Stored PGN already contains `[%eval ...]` for games that were analyzed. Re-parsing is free; re-fetching costs API rate limit budget. |
| Game-level accuracy on `games` table | Per-move accuracy on `game_positions` | chess.com only provides game-level accuracy; per-move values require local engine. Game-level is the right granularity for the conversion/recovery statistics use case. |

---

## Version Compatibility

| Package | Constraint | Notes |
|---------|------------|-------|
| `chess` (python-chess) | >=1.10.0 — 1.11.2 latest (Feb 2025) | `node.eval()`, `node.nags`, `board.pieces()`, `NAG_*` constants all stable since 1.x. The `eval()` off-by-one centipawn bug was fixed in 1.11.1 — already resolved in 1.11.2. |
| PostgreSQL | 18 (production Docker) | `SMALLINT` maps cleanly; composite B-tree syntax unchanged. |
| SQLAlchemy | >=2.0.0 | `mapped_column(SmallInteger, nullable=False)` for new columns; `select()` API unchanged. |
| lichess API | Current (no versioning) | `evals` and `accuracy` parameters confirmed in official OpenAPI YAML as of research date. |
| chess.com API | Published Data API (no versioning) | `accuracies` field confirmed in official documentation; field is optional/absent when not analyzed. |

---

## Sources

- [python-chess 1.11.2 Core docs](https://python-chess.readthedocs.io/en/latest/core.html) — `pieces()`, `piece_map()`, `has_insufficient_material()`, piece type constants — HIGH confidence
- [python-chess 1.11.2 PGN docs](https://python-chess.readthedocs.io/en/latest/pgn.html) — `node.eval()`, `node.eval_depth()`, `node.nags`, `node.clock()` — HIGH confidence
- [python-chess changelog](https://python-chess.readthedocs.io/en/latest/changelog.html) — 1.11.2 released Feb 2025, `eval()` off-by-one fix in 1.11.1 — HIGH confidence
- [lichess-org/api OpenAPI YAML](https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/tags/games/api-games-user-username.yaml) — `evals`, `accuracy`, `analysed` parameters confirmed, PGN comment format `[%eval cp]` / `[%eval #N]` — HIGH confidence
- [lichess accuracy API forum](https://lichess.org/forum/lichess-feedback/trying-to-find-accuracy-from-the-api) — `players.*.accuracy` and `players.*.analysis` fields in NDJSON with JSON Accept header — MEDIUM confidence (forum, consistent with spec)
- [chess.com Published-Data API documentation](https://gist.github.com/andreij/0e3309200c0a6bb26308817a168203f3) — `accuracies.white/black` field confirmed, absent when not analyzed — HIGH confidence
- [chess.com forum: no per-move evals in API](https://www.chess.com/forum/view/general/can-i-download-pgn-with-score-and-clock-using-api) — chess.com moderator confirmed evals/game-review data not available via public API — HIGH confidence
- [Chessprogramming wiki: Game Phases](https://www.chessprogramming.org/Game_Phases) — material-based phase detection rationale, tapered eval pattern — MEDIUM confidence (community reference)

---

*Stack research for: FlawChess v1.5 — game statistics & endgame analysis*
*Researched: 2026-03-23*
