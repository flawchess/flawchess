# Phase 27: Import Wiring & Backfill - Research

**Researched:** 2026-03-24
**Domain:** Python async import pipeline integration + PostgreSQL batch UPDATE backfill
**Confidence:** HIGH

## Summary

Phase 27 has two tightly scoped tasks. First, wire `classify_position(board)` into the existing per-ply loop in `import_service.py` so all 7 metadata columns are populated during new game imports. Second, write a standalone backfill script that re-parses stored PGN from the `games` table, replays moves, classifies each position, and batch-UPDATEs existing `game_positions` rows. Both tasks build on Phase 26 output (`classify_position`, `PositionClassification`, and the 7 nullable columns already migrated to production).

The import pipeline integration is a small targeted change: the per-ply loop at lines 401-413 of `import_service.py` assembles position row dicts. Calling `classify_position(board)` at each ply and merging the 7 fields into the dict is all that's required. The board state at each ply must be maintained in parallel with the existing `hashes_for_game` iteration — this is the key integration challenge since `hashes_for_game` returns tuples but does not expose intermediate board states.

The backfill script is a standalone async Python script using `async_session_maker` directly (same pattern as `import_service.py`). It queries games with NULL `game_phase` in batches of 10, re-parses each game's stored PGN, and issues batch UPDATEs. Memory safety is the primary constraint: batch_size=10 is hard-coded per the OOM incident documented in STATE.md.

**Primary recommendation:** Re-parse PGN inside the import pipeline (not in `hashes_for_game`) so that both hash computation and classification share a single PGN parse per game. For the backfill, perform UPDATE in per-game loops (not a single bulk UPDATE) to keep memory bounded.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Import Wiring**
- **D-01:** Call `classify_position(board)` inside the existing per-ply loop in `import_service.py` where `hashes_for_game` results are processed. Extend each `position_rows` dict with the 7 classifier fields before passing to `bulk_insert_positions`.

**Backfill Strategy**
- **D-02:** Backfill from stored PGN — re-parse each game's PGN from the `games` table, replay moves through `chess.Board`, call `classify_position()` at each ply, and UPDATE the 7 columns on existing `game_positions` rows. No external API calls, no re-importing.
- **D-03:** Resumability via NULL `game_phase` query — on each run, find games whose positions still have NULL `game_phase`. Self-healing: if interrupted, re-run and it picks up automatically. No state files or marker tables.
- **D-04:** Batch size = 10 games per DB commit, consistent with the import pipeline OOM constraint (STATE.md critical constraint).
- **D-05:** Script location at `scripts/backfill_positions.py` — standalone Python script, run with `uv run python scripts/backfill_positions.py`. Clear separation from app code for a one-time operation.

**Production Deployment**
- **D-06:** Run backfill live while app serves traffic — no maintenance window needed.
- **D-07:** Script runs `VACUUM ANALYZE game_positions` automatically after completion.

**Error Handling**
- **D-08:** Skip and log on per-game classification failure — log game_id and error via Sentry (`sentry_sdk.capture_exception()`), skip the game, continue backfill.
- **D-09:** Stdout progress summary — print progress every N games and a final summary. No log files.

### Claude's Discretion
- Import wiring approach (how exactly to integrate classify_position into the hashes_for_game loop or the position_rows assembly)
- Backfill UPDATE strategy (per-game UPDATE vs batch UPDATE)
- Progress reporting frequency (every 10, 50, or 100 games)
- Test structure and coverage approach

### Deferred Ideas (OUT OF SCOPE)
- Delete-and-reimport approach for engine analysis (deferred to Phase 29)
- Bitboard storage for partial-position queries (backlog)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PMETA-05 | System backfills position metadata for all previously imported games without requiring user re-import | D-02 through D-09 in CONTEXT.md provide a complete backfill design; research confirms the stored-PGN approach is feasible and memory-safe |
</phase_requirements>

---

## Standard Stack

### Core (all already in project dependencies — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.10.x | PGN parsing + board replay for classify_position | Already used by import pipeline and position_classifier |
| SQLAlchemy async | 2.0.48 | Async DB sessions, UPDATE statements | Project ORM — `async_session_maker` for script DB access |
| asyncpg | 0.31.0 | PostgreSQL async driver | Project driver — no change |
| sentry-sdk[fastapi] | 2.54.0 | Error capture in backfill script | Already initialized in app/main.py; script needs its own `sentry_sdk.init()` |
| asyncio | stdlib | Entry point for standalone async script | `asyncio.run(main())` pattern |

### No New Dependencies
Phase 27 requires zero new packages. Everything needed exists in the project venv.

**Verification:** Dev PostgreSQL is running (`flawchess-dev-db-1`, healthy on port 5432). Python 3.13.12 confirmed via `uv run`.

---

## Architecture Patterns

### Pattern 1: Import Wiring — Board Replay Alongside hashes_for_game

**What:** `hashes_for_game()` returns tuples `(ply, white_hash, black_hash, full_hash, move_san, clock_seconds)` but does NOT expose board state. For `classify_position(board)` to be called at each ply, the import loop must replay the board in parallel with iterating the hash tuples.

**Concrete approach:** In `import_service.py`, after the `hashes_for_game(pgn)` call (line 396), re-parse the PGN once more to get a board and the sequence of moves. Then iterate `hash_tuples` and `nodes` together (zip or index-based), calling `classify_position(board)` at each ply before pushing the move.

**Alternatively:** Extend `hashes_for_game` (or write a sibling function) to yield board snapshots. However, CONTEXT.md D-01 specifies the integration point as "inside the existing per-ply loop where hashes_for_game results are processed," meaning a second PGN parse (or refactoring `hashes_for_game`) are both valid — the choice is Claude's discretion.

**Recommended approach (discretion):** Re-parse the PGN a second time to build the node list and board. This avoids modifying the tested `hashes_for_game` function. The two-parse approach adds ~zero latency since PGN parsing is CPU-bound and tiny. Code structure:

```python
# Source: import_service.py lines 392-413 pattern — extended
for game_id, pgn in id_pgn_pairs:
    if not pgn:
        continue
    try:
        hash_tuples, result_fen = hashes_for_game(pgn)
    except Exception:
        logger.warning("Failed to compute hashes for game_id=%s", game_id)
        continue

    # Second parse for board state (classify_position needs the board at each ply)
    try:
        game_obj = chess.pgn.read_game(io.StringIO(pgn))
        nodes = list(game_obj.mainline()) if game_obj else []
        board = game_obj.board() if game_obj else None
    except Exception:
        board = None
        nodes = []

    for i, (ply, white_hash, black_hash, full_hash, move_san, clock_seconds) in enumerate(hash_tuples):
        row = {
            "game_id": game_id,
            "user_id": user_id,
            "ply": ply,
            "white_hash": white_hash,
            "black_hash": black_hash,
            "full_hash": full_hash,
            "move_san": move_san,
            "clock_seconds": clock_seconds,
        }
        if board is not None:
            classification = classify_position(board)
            row.update({
                "game_phase": classification.game_phase,
                "material_signature": classification.material_signature,
                "material_imbalance": classification.material_imbalance,
                "endgame_class": classification.endgame_class,
                "has_bishop_pair_white": classification.has_bishop_pair_white,
                "has_bishop_pair_black": classification.has_bishop_pair_black,
                "has_opposite_color_bishops": classification.has_opposite_color_bishops,
            })
            # Advance board to next ply (before next iteration)
            if i < len(nodes):
                board.push(nodes[i].move)
        position_rows.append(row)
```

**Key detail:** `classify_position(board)` must be called BEFORE `board.push(node.move)` — classification is for the position BEFORE the move is played, matching ply semantics in `hashes_for_game`.

### Pattern 2: Backfill Script Structure

**What:** Standalone async script at `scripts/backfill_positions.py`. Uses `asyncio.run(main())` entry point. Queries games with NULL `game_phase` via JOIN, processes in batches of 10, commits per batch.

**Resumability query pattern:**
```python
# Find game_ids that still have at least one NULL game_phase position
from sqlalchemy import select, distinct
from app.models.game_position import GamePosition

stmt = (
    select(distinct(GamePosition.game_id))
    .where(GamePosition.game_phase.is_(None))
    .limit(BATCH_SIZE)
)
```

**Per-game UPDATE pattern (discretion recommendation: per-game batch UPDATE):**
```python
from sqlalchemy import update as sa_update

# Build list of per-ply classification dicts, then issue individual UPDATEs
# grouped by game_id to keep memory bounded
for ply, classification in enumerate(classifications):
    await session.execute(
        sa_update(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.ply == ply)
        .values(
            game_phase=classification.game_phase,
            material_signature=classification.material_signature,
            material_imbalance=classification.material_imbalance,
            endgame_class=classification.endgame_class,
            has_bishop_pair_white=classification.has_bishop_pair_white,
            has_bishop_pair_black=classification.has_bishop_pair_black,
            has_opposite_color_bishops=classification.has_opposite_color_bishops,
        )
    )
```

**Alternative: build list and executemany via VALUES** — more efficient but more complex. For a one-time backfill on the Hetzner VPS, per-ply UPDATE is simple, correct, and within memory budget.

### Pattern 3: Sentry Initialization in Standalone Script

**What:** The backfill script runs outside the FastAPI app, so `sentry_sdk.init()` from `app/main.py` is not called. The script must initialize Sentry itself.

```python
import os
import sentry_sdk
from app.core.config import settings  # loads .env via pydantic-settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )
```

This matches the `main.py` pattern (conditional on SENTRY_DSN non-empty).

### Pattern 4: VACUUM ANALYZE After Backfill

**What:** PostgreSQL `VACUUM ANALYZE` runs outside a transaction. SQLAlchemy async requires execution with `AUTOCOMMIT` isolation level.

```python
# VACUUM cannot run inside a transaction block
async with engine.connect() as conn:
    await conn.execute(text("COMMIT"))  # end any implicit transaction
    await conn.execution_options(isolation_level="AUTOCOMMIT")
    await conn.execute(text("VACUUM ANALYZE game_positions"))
```

**Correct SQLAlchemy 2.x pattern:**
```python
async with engine.connect() as conn:
    await conn.execution_options(isolation_level="AUTOCOMMIT").execute(
        text("VACUUM ANALYZE game_positions")
    )
```

The `isolation_level="AUTOCOMMIT"` option must be set on the connection before execution. Using `session.execute` will fail because SQLAlchemy sessions always wrap statements in a transaction.

### Pattern 5: Progress Reporting

**Discretion recommendation: every 50 games.** Production data volume is unknown but likely thousands of games. Every 10 would be noisy; every 100 might feel stalled. Every 50 is a reasonable middle ground.

```python
_PROGRESS_INTERVAL = 50  # print progress every N games

if games_processed % _PROGRESS_INTERVAL == 0:
    print(f"Progress: {games_processed} games processed, {positions_updated} positions updated, {errors} errors")
```

### Anti-Patterns to Avoid
- **Calling board.push() before classify_position():** Classification must happen BEFORE the move is pushed. Pushing first would classify the NEXT ply's position.
- **Running VACUUM inside a session/transaction:** Causes `ERROR: VACUUM cannot run inside a transaction block`. Use AUTOCOMMIT isolation.
- **Loading all NULL-game_id rows at once:** SELECT all game_ids upfront would load potentially millions of rows. Use `LIMIT` with a loop.
- **Modifying hashes_for_game unnecessarily:** `hashes_for_game` is tested and works. Adding board exposure would couple two responsibilities. Two PGN parses is simpler.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Position classification | Custom board analysis | `classify_position(board)` from Phase 26 | Already implemented and tested |
| PGN parsing + board replay | Custom PGN reader | `chess.pgn.read_game()` + `board.push()` | python-chess handles all edge cases, promotions, en passant |
| Async DB session for script | Custom connection pool | `async_session_maker` from `app.core.database` | Already configured with correct DATABASE_URL, pool_size |
| Batch limiting | Manual offset tracking | `LIMIT` on the game_id query per batch loop | Simpler and self-healing (NULL check is the resume marker) |
| Error tracking | Log files | `sentry_sdk.capture_exception()` | Centralized error visibility per D-08 |

---

## Common Pitfalls

### Pitfall 1: Off-by-One Board State in Import Wiring
**What goes wrong:** `classify_position(board)` is called after `board.push(move)` instead of before. The position at ply N gets classified as the position at ply N+1.
**Why it happens:** The natural loop structure processes hash_tuples (pre-move hashes) while advancing the board. It's easy to advance the board first.
**How to avoid:** Always call `classify_position(board)` BEFORE `board.push(node.move)`. The hash_tuples from `hashes_for_game` confirm this: hashes are computed before the push.
**Warning signs:** Starting position (ply 0) shows middlegame classification instead of opening.

### Pitfall 2: VACUUM Inside a Transaction
**What goes wrong:** `await session.execute(text("VACUUM ANALYZE game_positions"))` raises `ProgrammingError: VACUUM cannot run inside a transaction block`.
**Why it happens:** SQLAlchemy `AsyncSession` implicitly wraps all statements in a transaction.
**How to avoid:** Use `engine.connect()` with `isolation_level="AUTOCOMMIT"`, not `async_session_maker`.
**Warning signs:** Error message mentioning "transaction block" during VACUUM step.

### Pitfall 3: OOM on Large Batches
**What goes wrong:** Backfill script loads too many rows into memory, causing PostgreSQL or Python to be OOM-killed on the Hetzner VPS.
**Why it happens:** batch_size=50 was already proven to OOM-kill PostgreSQL (STATE.md critical constraint).
**How to avoid:** Hard-code `_BATCH_SIZE = 10` (matching `_BATCH_SIZE` in `import_service.py`). Never increase without testing against a production-size DB snapshot with `docker stats` monitoring.
**Warning signs:** `docker stats` showing PostgreSQL memory usage approaching 3.7 GB.

### Pitfall 4: Infinite Loop on Skipped Games
**What goes wrong:** A game that consistently fails classification is never marked as processed (game_phase stays NULL), so the backfill loop selects it every run and never finishes.
**Why it happens:** The resumability check queries for NULL game_phase. If a game's positions can never be classified successfully, they stay NULL forever.
**How to avoid:** Track skipped game_ids in-memory during a run and exclude them from subsequent batch queries within the same run. Or, accept that a tiny number of permanently-failing games will be re-attempted on each run (they'll be skipped quickly via try/except).
**Warning signs:** Progress counter stops advancing despite active DB queries.

### Pitfall 5: Missing `scripts/` Directory
**What goes wrong:** `uv run python scripts/backfill_positions.py` fails with `ModuleNotFoundError` if the script is not in the Python path.
**Why it happens:** Running a script in a subdirectory may not have the project root on `sys.path`.
**How to avoid:** The script should use `uv run python scripts/backfill_positions.py` from the project root — `uv run` sets up the correct virtualenv and path. Alternatively, add a `if __name__ == "__main__": asyncio.run(main())` block and confirm imports resolve from project root.

---

## Code Examples

### bulk_insert_positions already handles 7 metadata fields (HIGH confidence)
```python
# Source: app/repositories/game_repository.py lines 71-97
# Docstring confirms: position_rows dicts may include optional keys:
# game_phase, material_signature, material_imbalance, endgame_class,
# has_bishop_pair_white, has_bishop_pair_black, has_opposite_color_bishops
# chunk_size = 2100 (15 columns per row, stays within asyncpg 32767 arg limit)
```

### VACUUM ANALYZE with AUTOCOMMIT (HIGH confidence — SQLAlchemy 2.x pattern)
```python
from sqlalchemy import text
async with engine.connect() as conn:
    await conn.execution_options(isolation_level="AUTOCOMMIT").execute(
        text("VACUUM ANALYZE game_positions")
    )
```

### Sentry init pattern matching app/main.py
```python
# Source: app/main.py lines 22-28
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
    )
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|---------|
| PostgreSQL (dev) | Backfill script, tests | Yes | 18-alpine (Docker) | — |
| python-chess | PGN replay + classify_position | Yes | in project venv | — |
| SQLAlchemy async | DB sessions | Yes | 2.0.48 | — |
| asyncpg | PostgreSQL driver | Yes | 0.31.0 | — |
| sentry-sdk | Error capture | Yes | 2.54.0 | Skip init if SENTRY_DSN empty |
| Docker | Dev DB | Yes | 29.3.0 | — |

No missing dependencies. All required tools confirmed available.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio (asyncio_mode = "auto") |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_import_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PMETA-05 | New imports populate all 7 metadata columns (non-null) | unit (mock) | `uv run pytest tests/test_import_service.py -x` | Yes (extend existing) |
| PMETA-05 | Backfill script updates NULL rows correctly | integration (real DB) | `uv run pytest tests/test_backfill.py -x` | No — Wave 0 gap |
| PMETA-05 | Backfill skips and logs games with bad PGN | unit (mock) | `uv run pytest tests/test_backfill.py -x` | No — Wave 0 gap |
| PMETA-05 | classify_position called with pre-move board (not post-move) | unit | `uv run pytest tests/test_import_service.py -x` | Yes (extend existing) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_import_service.py tests/test_position_classifier.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_backfill.py` — covers PMETA-05 backfill correctness and error handling
- [ ] `scripts/` directory — must be created (currently does not exist per glob search)

---

## Open Questions

1. **Import loop: two PGN parses vs. extending hashes_for_game**
   - What we know: CONTEXT.md D-01 says integrate at the position_rows loop. `hashes_for_game` iterates `game.mainline()` and pushes moves on a board internally but does not expose it.
   - What's unclear: Whether to add board snapshot yielding to `hashes_for_game` (more efficient, one parse) or do a second parse in import_service (simpler, no touching tested code).
   - Recommendation: Second parse in `import_service.py` — avoids touching `hashes_for_game` and its tests. Performance difference is negligible.

2. **Backfill UPDATE strategy: per-ply vs. per-game bulk VALUES**
   - What we know: Per-ply UPDATEs are simple. A per-game bulk VALUES approach with `executemany` or a CTE could be faster.
   - What's unclear: Whether update speed matters enough on a one-time backfill.
   - Recommendation: Per-ply individual UPDATEs for simplicity. The one-time script will run for minutes/hours either way; throughput optimization is premature.

3. **Progress reporting frequency**
   - Recommendation: Every 50 games (see Pattern 5 above).

---

## Sources

### Primary (HIGH confidence)
- `app/services/import_service.py` — Lines 392-434: exact integration point for position_rows assembly
- `app/services/position_classifier.py` — `classify_position(board)` API, `PositionClassification` fields
- `app/services/zobrist.py` — `hashes_for_game()` internals confirming board state not exposed
- `app/repositories/game_repository.py` — `bulk_insert_positions()` chunk_size=2100, optional 7 metadata keys confirmed in docstring
- `app/models/game_position.py` — All 7 nullable columns confirmed present
- `app/core/database.py` — `async_session_maker` access pattern
- `app/core/config.py` — `settings.DATABASE_URL`, `settings.SENTRY_DSN` for script initialization
- `app/main.py` — Sentry initialization pattern
- `.planning/STATE.md` — Critical constraint: batch_size=10, standalone script (not Alembic), chunk_size=2100
- SQLAlchemy 2.x docs — `isolation_level="AUTOCOMMIT"` required for VACUUM (verified against SQLAlchemy 2.0.48 in project)

### Secondary (MEDIUM confidence)
- PostgreSQL docs — `VACUUM ANALYZE` cannot run inside a transaction block (well-known constraint, verified via project experience)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project, versions verified
- Architecture patterns: HIGH — based on direct code reading of canonical files; integration points are unambiguous
- Pitfalls: HIGH — OOM constraint documented in STATE.md from production incident; VACUUM/transaction constraint is a PostgreSQL fundamental; board state ordering verified by reading hashes_for_game
- Test coverage: MEDIUM — existing test patterns are clear, but test_backfill.py doesn't exist yet

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable stack — no fast-moving dependencies)
