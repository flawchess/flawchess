# Phase 28: Engine Analysis Import - Research

**Researched:** 2026-03-25
**Domain:** Chess game import pipeline — lichess PGN eval annotations, chess.com accuracy JSON, SQLAlchemy schema migration
**Confidence:** HIGH

## Summary

Phase 28 extends the existing import pipeline to capture engine analysis data that platforms already provide. Lichess embeds per-move Stockfish evaluations as `%eval` PGN comments when prior computer analysis exists. Chess.com provides game-level accuracy scores (`white_accuracy`, `black_accuracy`) in its game JSON for analyzed games. Both platforms omit these fields for unanalyzed games — this is the normal case, not an error.

The implementation is a well-defined additive change. Every integration point is already identified in CONTEXT.md. The new columns follow identical patterns to `clock_seconds` (nullable Float on `game_positions`) and `white_rating`/`black_rating` (nullable numerics on `games`). The python-chess `node.eval()` API mirrors `node.clock()` exactly: returns `None` when no annotation is present, returns a `PovScore` when `%eval` is present. No new libraries are needed.

The admin re-import script follows the Phase 27 `backfill_positions.py` pattern: standalone async script, batch_size=10 (OOM-safe), resumable if interrupted, `--user-id N | --all` CLI flags.

**Primary recommendation:** Implement as four tightly-scoped tasks — (1) schema migration, (2) normalization layer updates, (3) `_flush_batch` eval extraction wiring, (4) re-import script + tests. The chunk_size in `bulk_insert_positions` MUST be reduced from 2700 to 2300 to stay within asyncpg's 32,767 argument limit with 14 columns per row.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data Storage Schema**
- D-01: Per-move evals stored on `game_positions` table — two new nullable columns: `eval_cp` (SmallInteger, centipawns) and `eval_mate` (SmallInteger, mate-in-N moves, signed: positive = white mates, negative = black mates). Both NULL for unanalyzed games or chess.com games.
- D-02: Game-level accuracy stored on `games` table — two new nullable Float columns: `white_accuracy` and `black_accuracy`. Both sides stored (not just the user's) to support opponent scouting. Only populated for chess.com games that have accuracy data.
- D-03: Split storage matches data granularity: per-move data on positions, game-level data on games. No denormalization.

**Lichess Eval Extraction**
- D-04: Add `evals=true` to lichess API request params (in `lichess_client.py`). Unanalyzed games simply won't have `%eval` annotations — python-chess `node.eval()` returns `None`. Zero overhead for unanalyzed games.
- D-05: Eval representation: centipawns as SmallInteger (e.g., +18 for 0.18 pawns, -112 for -1.12). Mate scores in separate SmallInteger column (e.g., -7 means black mates in 7). python-chess `node.eval()` returns `PovScore` which provides both via `.white().score(mate_score=None)` and `.white().mate()`.
- D-06: Extract evals in the same PGN parsing loop where `hashes_for_game` or the per-ply classification runs. `node.eval()` is called per move node, same as `node.clock()`.

**Chess.com Accuracy Import**
- D-07: Chess.com accuracy lives at the game JSON level: `game["accuracies"]["white"]` and `game["accuracies"]["black"]` (floats, e.g., 83.53). Not all games have this field — only analyzed games.
- D-08: Extract accuracy in `normalize_chesscom_game()` — add `white_accuracy` and `black_accuracy` to the normalized game dict. Store both sides for opponent scouting potential.
- D-09: Games without `accuracies` key: both columns remain NULL. No error logged — this is normal for unanalyzed games.

**Backfill Strategy**
- D-10: No automatic backfill of existing games. Only newly imported games (going forward) get eval/accuracy data. Old games retain NULL values.
- D-11: Admin re-import script at `scripts/reimport_games.py` — deletes all games + positions for specified user(s), then re-imports from scratch using the updated pipeline. Clean slate approach: `uv run python scripts/reimport_games.py [--user-id N | --all]`.
- D-12: Full re-import via UI deferred to a future phase. For now, admin runs the script once after deploying Phase 28.

### Claude's Discretion
- How to extend `hashes_for_game()` or the per-ply loop to extract evals (refactor tuple or add a parallel extraction)
- Re-import script implementation details (batch size, progress reporting, error handling)
- Test structure and coverage approach
- Whether to update stored PGN column with eval-enriched PGN during lichess re-import (the new fetch includes `evals=true` so PGN will have `%eval` annotations)

### Deferred Ideas (OUT OF SCOPE)
- Full re-import via UI — user-triggerable re-import button on the Import page. Deferred to future phase.
- Human-like engine analysis — Stockfish + Maia Chess pipeline. Entirely different scope (v2+ feature). Captured in todo.
- Derive accuracy for lichess games — compute game-level accuracy from per-move evals. Future enhancement.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGINE-01 | System imports per-move eval (centipawns/mate) from lichess PGN annotations for games with prior computer analysis | `node.eval()` on python-chess `GameNode` returns `PovScore` or `None`; add `evals=true` param to lichess fetch; extract in `_flush_batch` position loop |
| ENGINE-02 | System imports game-level accuracy scores from chess.com for games where analysis exists | `game["accuracies"]["white/black"]` in chess.com JSON; extract in `normalize_chesscom_game()`; store on `games` table as nullable Float |
| ENGINE-03 | System gracefully handles missing analysis data (null fields, no errors) for unanalyzed games | `node.eval()` returns `None` when no `%eval` annotation; absent `accuracies` key means `.get("accuracies", {})` returns `{}`; all new columns nullable |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.10.x | PGN parsing, `node.eval()`, `PovScore` | Already in project; `node.eval()` API mirrors `node.clock()` |
| SQLAlchemy 2.x async | 2.x | ORM model updates, Alembic migration | Project standard |
| Alembic | Current | Schema migration (4 new nullable columns) | Project standard migration tool |

### No New Libraries Required
All required functionality is provided by existing project dependencies.

**Version verification:** Confirmed via direct code execution — python-chess `node.eval()` API tested in project's virtualenv, returning centipawn integers and signed mate values as expected.

## Architecture Patterns

### Recommended Project Structure
No new files needed beyond:
```
app/models/game.py              # Add white_accuracy, black_accuracy columns
app/models/game_position.py     # Add eval_cp, eval_mate columns
app/repositories/game_repository.py  # Update chunk_size comment (2700→2300)
app/services/normalization.py   # Extract accuracies in normalize_chesscom_game()
app/services/lichess_client.py  # Add evals=True to params
app/services/import_service.py  # Wire eval extraction in _flush_batch position loop
alembic/versions/XXXX_add_engine_analysis_columns.py  # Migration
scripts/reimport_games.py       # New: admin re-import script
tests/test_normalization.py     # Add accuracy extraction tests
tests/test_reimport.py          # New: re-import script tests
```

### Pattern 1: Eval Extraction in Classification Loop

The `_flush_batch` function already has a second PGN parse loop for `classify_nodes`. Per-move eval extraction integrates into this same loop since eval is per `GameNode`, just like `classify_position`.

**Key design choice (Claude's discretion):** The eval must be extracted from the SAME node as the classification (same `i` index in the loop), not from `hash_tuples`. The hash tuple loop in `hashes_for_game()` uses `game.mainline()` with a `board.push()` approach that doesn't expose the node object for `node.eval()` calls. The second parse loop (`classify_nodes`) already exposes nodes directly.

**Recommended approach:** Build a parallel `evals` list alongside the `classify_nodes` loop, then index into it during `position_rows` assembly:

```python
# Source: verified via direct execution
# In _flush_batch, second PGN parse section:

evals: list[tuple[int | None, int | None]] = []  # (eval_cp, eval_mate) per ply
if game_obj_for_classify and classify_nodes:
    for node in classify_nodes:
        pov = node.eval()
        if pov is not None:
            w = pov.white()
            evals.append((w.score(mate_score=None), w.mate()))
        else:
            evals.append((None, None))
else:
    evals = [(None, None)] * len(hash_tuples)

# Then in position row assembly:
eval_cp, eval_mate = evals[i] if i < len(evals) else (None, None)
row["eval_cp"] = eval_cp
row["eval_mate"] = eval_mate
```

Note: The final position row (no `move_san`) has no eval — `node.eval()` only exists on move nodes (nodes in `mainline()`), not after the last move. The final position row at `ply = len(nodes)` should always have `eval_cp=None, eval_mate=None`.

### Pattern 2: Chess.com Accuracy Extraction

`normalize_chesscom_game()` currently returns a dict with ~20 keys. Add accuracy extraction following the `.get()` with default `{}` pattern to handle the absent field:

```python
# Source: verified against chess.com API field name from CONTEXT.md
accuracies = game.get("accuracies", {})
white_accuracy = accuracies.get("white")   # float e.g. 83.53, or None
black_accuracy = accuracies.get("black")   # float e.g. 76.21, or None
```

Add both keys to the returned dict. The `Game` model and `bulk_insert_games` will pass them through as nullable Floats.

### Pattern 3: Lichess API Params Update

Single-line change in `lichess_client.py`:

```python
# Source: lichess API docs, confirmed in CONTEXT.md
params: dict[str, str | bool] = {
    "pgnInJson": True,
    "perfType": _PERF_TYPES,
    "moves": True,
    "tags": True,
    "opening": True,
    "evals": True,   # ADD THIS: include %eval annotations in PGN when available
}
```

Lichess only includes `%eval` when the game has prior computer analysis. Games without analysis return the same PGN as before (no `%eval` annotations).

### Pattern 4: Alembic Migration

Follow exact column type patterns already used in `game_positions` and `games`:

```python
# game_positions: two new SmallInteger nullable columns
op.add_column("game_positions", sa.Column("eval_cp", sa.SmallInteger(), nullable=True))
op.add_column("game_positions", sa.Column("eval_mate", sa.SmallInteger(), nullable=True))

# games: two new Float(24) nullable columns (same as clock_seconds pattern: REAL not DOUBLE)
op.add_column("games", sa.Column("white_accuracy", sa.Float(precision=24), nullable=True))
op.add_column("games", sa.Column("black_accuracy", sa.Float(precision=24), nullable=True))
```

`Float(24)` maps to PostgreSQL `REAL` (4 bytes). Accuracy is 0-100 with 2 decimal places — REAL precision is sufficient.

### Pattern 5: Re-import Script

Mirror `scripts/backfill_positions.py` structure exactly:

```python
# scripts/reimport_games.py
# Usage: uv run python scripts/reimport_games.py [--user-id N | --all]

# Key logic:
# 1. Parse CLI args: --user-id INT or --all (mutually exclusive)
# 2. For each target user:
#    a. Delete all game_positions (CASCADE handles it via delete(Game))
#    b. Delete all games for user
#    c. Fetch fresh from platform(s) via the updated import pipeline
#    d. Batch commit at _BATCH_SIZE=10 games
# 3. Print progress, final summary

# Important: use game_repository.delete_all_games_for_user() which already
# handles positions via CASCADE. Don't re-implement the delete.
```

The script must use `asyncio.run(main())` at the bottom and `sys.path.insert()` at the top — same as `backfill_positions.py`.

### Pattern 6: chunk_size Reduction (CRITICAL)

The asyncpg 32,767 argument limit requires updating `bulk_insert_positions`. Adding 2 columns (eval_cp, eval_mate) increases column count from 12 to 14:

```python
# Current (WRONG after Phase 28):
# Each position row has 12 columns ... chunk_size = 2700

# Correct after Phase 28:
# Each position row has 14 columns (8 original + 4 position metadata + 2 eval)
# max rows = floor(32767 / 14) = 2340; use 2300 for safety
chunk_size = 2300
```

Failure to update chunk_size will cause `asyncpg.exceptions.TooManyArguments` on games with many positions.

### Anti-Patterns to Avoid

- **Extracting evals from `hashes_for_game()` return values:** `hashes_for_game()` does not expose `GameNode` objects; it only returns computed tuples. Eval extraction must happen in the separate node-iteration loop that already exists in `_flush_batch`.
- **Using `Float(53)` (DOUBLE PRECISION) for accuracy:** `Float(24)` (REAL) is already established for `clock_seconds` and is sufficient for accuracy values (0–100 with 2 decimal places).
- **Logging warnings for absent `accuracies` key:** This is the normal case (~95% of chess.com games). Silent NULL is correct per D-09.
- **Calling `node.eval()` on the final position:** `game.mainline()` yields move nodes only (N moves for an N-move game). The final board position has no corresponding node. The final position row (ply = len(nodes)) always gets `eval_cp=None, eval_mate=None`.
- **Forgetting to update PGN comment in STATE.md:** The `bulk_insert_positions` doc comment currently says "12 columns" — update to 14.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PGN eval annotation parsing | Custom regex for `%eval` | `node.eval()` from python-chess | Handles `[%eval 0.18]`, `[%eval #5]`, `[%eval #-3]`, absent annotations; battle-tested |
| White-perspective score extraction | Manual PovScore decomposition | `.white().score(mate_score=None)` and `.white().mate()` | PovScore already handles perspective flip; returns `None` correctly for absent/non-applicable |
| Accuracy field presence detection | Complex JSON schema validation | `.get("accuracies", {}).get("white")` | Standard Python dict pattern; returns `None` when absent |
| User data deletion before re-import | Custom DELETE SQL | `game_repository.delete_all_games_for_user()` | Already deletes positions via CASCADE (FK ondelete=CASCADE) |

**Key insight:** python-chess's `GameNode.eval()` API is a first-class feature; the `PovScore.white()` accessor returns scores from White's perspective regardless of which side moved, making it safe to store as a signed integer.

## Runtime State Inventory

This phase adds columns to existing tables and introduces a re-import script. No string renames or key migrations.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing `game_positions` rows: NULL for `eval_cp`/`eval_mate`. Existing `games` rows: NULL for `white_accuracy`/`black_accuracy`. | NULL is correct per D-10 — no backfill needed. Admin re-import script available for opted-in users. |
| Live service config | Lichess API connection: adding `evals=true` param changes what data the streaming API returns. | Code edit in `lichess_client.py` only. No service reconfiguration needed. |
| OS-registered state | None | None — verified: no cron jobs, task scheduler entries, or pm2 processes reference game import. |
| Secrets/env vars | None | None — no new env vars or secrets required for this phase. |
| Build artifacts | None | None — no compiled artifacts or pip egg-info affected. |

## Common Pitfalls

### Pitfall 1: asyncpg 32,767 Argument Limit
**What goes wrong:** `asyncpg.exceptions.TooManyArguments: too many arguments; expected 32767` during `bulk_insert_positions` for games with long move counts.
**Why it happens:** Adding `eval_cp` and `eval_mate` increases columns from 12 to 14. The current `chunk_size = 2700` exceeds the limit: 2700 * 14 = 37,800 > 32,767.
**How to avoid:** Update chunk_size to 2300 (= floor(32767/14) - 40 safety margin). Update the comment to say "14 columns".
**Warning signs:** Test failure on games with >2300 positions (very long games or chunk boundary hitting in tests).

### Pitfall 2: Eval on Final Position Node
**What goes wrong:** `IndexError` or incorrect `None` handling if code tries to call `node.eval()` for the final position.
**Why it happens:** `game.mainline()` returns N nodes for an N-move game. The final position (ply = N) has no node in `mainline()`. The `hash_tuples` list has N+1 entries (ply 0..N) but `classify_nodes` has only N entries.
**How to avoid:** The `evals` list should be built from `classify_nodes` (length N), then indexed with `evals[i] if i < len(evals) else (None, None)` when assembling position rows.
**Warning signs:** Off-by-one errors in test assertions on final position rows.

### Pitfall 3: Centipawn vs Pawn Unit Confusion
**What goes wrong:** Storing 0.18 (pawns) instead of 18 (centipawns) in `eval_cp`.
**Why it happens:** Lichess PGN displays `[%eval 0.18]` in pawn units. python-chess `.white().score(mate_score=None)` returns centipawns (integer 18) — this is correct and matches D-05.
**How to avoid:** Use `.white().score(mate_score=None)` which returns centipawns (integer), not `.white().score()` which returns `Score` objects. Verify with `assert isinstance(eval_cp, int)` in tests.
**Warning signs:** Floating-point values stored in the integer SmallInteger column (would cause type error at insert time).

### Pitfall 4: Re-import Script Platform Scope
**What goes wrong:** Re-import script only re-imports one platform when user has both chess.com and lichess connected.
**Why it happens:** The script needs to re-import from all platforms the user has imported from, not just one.
**How to avoid:** Query `import_job_repository` for all platforms the user has previously imported from, or accept `--platform` flag. Alternatively, use `game_repository.count_games_by_platform()` to determine which platforms to re-import.
**Warning signs:** After re-import, one platform's games have eval data but the other doesn't because re-import wasn't triggered for it.

### Pitfall 5: Lichess evals=True on Incremental Sync
**What goes wrong:** Games that were analyzed on lichess AFTER the last sync won't get eval data on incremental sync (since they're already in the DB and `bulk_insert_games` uses ON CONFLICT DO NOTHING).
**Why it happens:** The incremental sync only fetches games newer than `last_synced_at`. Existing games won't be re-fetched.
**How to avoid:** This is explicitly accepted per D-10 — NULL values for old games is correct. The admin re-import script handles backfill when needed. Document this clearly in code comments.
**Warning signs:** User confusion about why some old games lack eval data — this is expected behavior.

## Code Examples

Verified patterns from official sources and direct code execution:

### python-chess node.eval() API
```python
# Source: verified by direct execution in project virtualenv
import chess.pgn, io

pgn = "1. e4 { [%eval 0.18] } 1... e5 { [%eval #-3] } *"
game = chess.pgn.read_game(io.StringIO(pgn))

for node in game.mainline():
    pov = node.eval()        # Returns PovScore or None
    if pov is not None:
        w = pov.white()
        cp = w.score(mate_score=None)   # int centipawns, or None if it's a mate score
        mate = w.mate()                  # int (positive=white mates, negative=black mates), or None
        # e4: cp=18, mate=None
        # e5: cp=None, mate=-3  (black mates in 3)
```

### Chess.com accuracy extraction
```python
# Source: CONTEXT.md D-07, verified against chess.com API structure
def normalize_chesscom_game(game: dict, username: str, user_id: int) -> dict | None:
    ...
    accuracies = game.get("accuracies", {})
    white_accuracy: float | None = accuracies.get("white")
    black_accuracy: float | None = accuracies.get("black")

    return {
        ...existing fields...,
        "white_accuracy": white_accuracy,
        "black_accuracy": black_accuracy,
    }
```

### Position row assembly with eval
```python
# Source: extends existing pattern in import_service.py _flush_batch
for i, (ply, white_hash, black_hash, full_hash, move_san, clock_seconds) in enumerate(hash_tuples):
    row: dict[str, Any] = {
        "game_id": game_id,
        "user_id": user_id,
        "ply": ply,
        ...
    }
    # Eval: indexed from evals list built from classify_nodes
    eval_cp, eval_mate = evals[i] if i < len(evals) else (None, None)
    row["eval_cp"] = eval_cp
    row["eval_mate"] = eval_mate
    ...
```

### Re-import script CLI pattern
```python
# Source: mirrors scripts/backfill_positions.py structure
import argparse, asyncio

def parse_args():
    parser = argparse.ArgumentParser(description="Re-import games for user(s)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", type=int, help="Re-import for single user")
    group.add_argument("--all", action="store_true", help="Re-import for all users")
    return parser.parse_args()

if __name__ == "__main__":
    asyncio.run(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No eval storage | Per-move eval in game_positions | Phase 28 | Enables future accuracy display, blunder detection |
| No accuracy storage | Game-level accuracy in games | Phase 28 | Enables future accuracy display, opponent scouting |

**Deprecated/outdated:**
- Nothing deprecated in this phase — purely additive changes.

## Open Questions

1. **Re-import script: update stored PGN with eval-enriched version?**
   - What we know: When lichess is re-fetched with `evals=true`, the returned PGN includes `%eval` annotations. The stored PGN currently lacks them.
   - What's unclear: Whether to UPDATE the `pgn` column with the eval-enriched version during re-import, or just store eval values without updating the PGN text.
   - Recommendation: Update the stored PGN during re-import (the new PGN is strictly more informative, and it's a clean slate operation anyway). For the forward-going import pipeline, new games will always have the eval-annotated PGN stored. Note this as Claude's discretion per CONTEXT.md.

2. **Re-import script: handle partial re-import if script is interrupted mid-user?**
   - What we know: The clean-slate approach deletes all games first, then re-imports. If interrupted after delete but before complete re-import, user loses data.
   - What's unclear: Whether to use a safer "delete+reinsert per game" approach or add a confirmation prompt.
   - Recommendation: Add a `--yes` / `-y` flag to skip confirmation, and add a prominent warning that data will be deleted before re-import begins. The script should also print the user ID and game count before proceeding.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (Docker) | Database | Confirmed | 18.x (docker-compose.dev.yml) | — |
| python-chess | `node.eval()` API | Confirmed | 1.10.x (in uv.lock) | — |
| asyncpg | DB driver | Confirmed | Current (in uv.lock) | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode = "auto") |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_normalization.py tests/test_reimport.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGINE-01 | Lichess game with `%eval` stores eval_cp and eval_mate on positions | integration | `uv run pytest tests/test_reimport.py::TestLichessEvalImport -x` | ❌ Wave 0 |
| ENGINE-01 | Ply 0 (no `%eval` annotation for pre-game position) stores NULL eval | unit | `uv run pytest tests/test_normalization.py::TestEvalExtraction -x` | ❌ Wave 0 |
| ENGINE-01 | Final position row (after last move) stores NULL eval | unit | `uv run pytest tests/test_normalization.py::TestEvalExtraction::test_final_position_eval_null -x` | ❌ Wave 0 |
| ENGINE-02 | Chess.com game with `accuracies` field stores white_accuracy and black_accuracy | unit | `uv run pytest tests/test_normalization.py::TestChesscomAccuracy -x` | ❌ Wave 0 |
| ENGINE-02 | Both sides' accuracy stored (not just user's side) | unit | `uv run pytest tests/test_normalization.py::TestChesscomAccuracy::test_both_sides_stored -x` | ❌ Wave 0 |
| ENGINE-03 | Lichess game without `%eval` imports cleanly with NULL eval columns | unit | `uv run pytest tests/test_normalization.py::TestEvalExtraction::test_no_eval_returns_null -x` | ❌ Wave 0 |
| ENGINE-03 | Chess.com game without `accuracies` key imports cleanly with NULL accuracy columns | unit | `uv run pytest tests/test_normalization.py::TestChesscomAccuracy::test_no_accuracies_key -x` | ❌ Wave 0 |
| ENGINE-03 | Game with no analysis on either platform imports without error, all engine fields NULL | integration | `uv run pytest tests/test_reimport.py::TestNoAnalysisImport -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_normalization.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reimport.py` — covers ENGINE-01 integration tests and ENGINE-03 integration test; needs `db_session` fixture from existing `conftest.py`
- [ ] `tests/test_normalization.py` additions — `TestChesscomAccuracy` and `TestEvalExtraction` test classes (add to existing file)

*(Existing test infrastructure: `conftest.py` with `db_session`, `test_engine`, `ensure_test_user` fixtures already available. No new framework setup needed.)*

## Sources

### Primary (HIGH confidence)
- Direct code execution in project virtualenv — python-chess `node.eval()` API behavior verified (centipawns as integers, `None` for absent annotations, signed mate values)
- `app/services/import_service.py` lines 343-464 — `_flush_batch()` implementation, exact integration point identified
- `app/services/zobrist.py` lines 77-136 — `hashes_for_game()` structure, confirmed it does NOT expose node objects
- `app/services/normalization.py` lines 141-230, 233-340 — normalizer structure, exact insertion point for accuracy
- `app/services/lichess_client.py` lines 44-50 — params dict, confirmed single-line change location
- `app/repositories/game_repository.py` lines 71-96 — `bulk_insert_positions` chunk_size calculation
- `app/models/game.py`, `app/models/game_position.py` — column type patterns (`Float(24)` for REAL, `SmallInteger` for small integers)
- `scripts/backfill_positions.py` — re-import script structural template
- `tests/test_backfill.py` — test pattern for standalone script testing
- `tests/conftest.py` — fixture availability confirmed

### Secondary (MEDIUM confidence)
- CONTEXT.md D-07: Chess.com accuracy field name `game["accuracies"]["white/black"]` verified by admin fetching actual Hikaru game API response (March 2026)
- CONTEXT.md specifics: Chess.com PGN has `%clk` only; accuracy is JSON-only field

### Tertiary (LOW confidence)
- None — all claims verified against source code or CONTEXT.md verified data.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, APIs verified by execution
- Architecture: HIGH — integration points are exact and verified against source code
- Pitfalls: HIGH — chunk_size limit is an exact calculation; eval/node relationship confirmed
- Test approach: HIGH — follows existing patterns in conftest.py and test_backfill.py

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable dependencies; lichess/chess.com API formats rarely change)

## Project Constraints (from CLAUDE.md)

Directives the planner must verify compliance with:

- **HTTP client:** Use `httpx.AsyncClient` only — never `requests`. Already the case; no new HTTP calls in this phase.
- **No SQLite:** PostgreSQL only. All storage uses existing PostgreSQL setup.
- **ORM:** SQLAlchemy 2.x async with `select()` API. Migration uses Alembic. No raw SQL in services.
- **PGN parsing:** Wrap per-game in try/except — `_flush_batch` already does this per D-06/existing pattern.
- **`board.board_fen()` not `board.fen()`:** Not relevant (no new board comparisons).
- **Foreign key constraints mandatory:** New columns are nullable data columns on existing tables — no new FK columns.
- **`data-testid` on interactive elements:** No frontend changes in this phase.
- **Batch size MUST be 10 games per commit:** Re-import script must use `_BATCH_SIZE = 10`.
- **Type safety:** All new function signatures must use Python type hints. `eval_cp: int | None`, `eval_mate: int | None`, `white_accuracy: float | None`, `black_accuracy: float | None`.
- **No magic numbers:** Extract `_BATCH_SIZE = 10` constant in re-import script (not bare `10`). Update chunk_size comment to explain the 14-column calculation.
- **Comment bug fixes:** Not applicable here; this is additive work.
