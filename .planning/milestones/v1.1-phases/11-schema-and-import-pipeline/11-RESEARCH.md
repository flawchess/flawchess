# Phase 11: Schema and Import Pipeline - Research

**Researched:** 2026-03-16
**Domain:** SQLAlchemy 2.x schema migration, python-chess SAN extraction, PostgreSQL covering indexes
**Confidence:** HIGH

## Summary

Phase 11 adds a `move_san` column to `game_positions` and populates it during import. The column stores the SAN of the move played **from** each position (leading to the next ply), so `NULL` appears on the final position row and on ply-0 only when ply-0 is also the final position (i.e., a game with no moves). Per STATE.md, the db wipe strategy is already settled: no backfill migration is needed — users will reimport after the schema change.

The changes touch three layers: (1) the SQLAlchemy model (`GamePosition`), (2) the Alembic migration, and (3) the import pipeline in `zobrist.py` and `_flush_batch()` in `import_service.py`. The critical python-chess constraint is that `board.san(move)` must be called **before** `board.push(move)` — the board must be in the pre-move position to compute SAN correctly. The existing `hashes_for_game()` function already iterates moves in the correct order; it needs to be extended to also return `move_san` alongside each hash tuple.

The covering index `(user_id, full_hash, move_san)` enables index-only scans on the next-moves aggregation query that Phase 12 will build. This is a new index alongside the existing `ix_gp_user_full_hash` — not a replacement.

**Primary recommendation:** Extend `hashes_for_game()` to return a 5-tuple `(ply, wh, bh, fh, move_san)`, update `_flush_batch()` to include `move_san` in `position_rows`, add the column and index via Alembic, and drop + recreate the DB before re-importing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEXP-01 | game_positions has a `move_san` column (nullable, NULL on final position and ply-0 of a no-moves game) | SQLAlchemy `Optional[str]` mapped column; Alembic `op.add_column` with `nullable=True` |
| MEXP-02 | Covering index `(user_id, full_hash, move_san)` exists and is used by EXPLAIN ANALYZE | PostgreSQL index-only scan; SQLAlchemy `Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san")` in `__table_args__` + Alembic `op.create_index` |
| MEXP-03 | Import pipeline populates `move_san` during import; re-import produces identical values with no duplicates | Extend `hashes_for_game()` to yield `move_san`; update `_flush_batch()` dict construction; idempotency guaranteed by `ON CONFLICT DO NOTHING` on games + positions inserted only for newly-inserted game IDs |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | >=1.10.0 (project constraint) | `board.san(move)` for SAN extraction; `board.push(move)` for position advance | Only chess logic library used in project |
| SQLAlchemy 2.x async | >=2.0.0 (project constraint) | `Mapped[Optional[str]]` column definition, `Index` in `__table_args__` | Project ORM |
| Alembic | >=1.13.0 (project constraint) | `op.add_column`, `op.create_index` for migration | Project migration tool |

### No New Dependencies
Phase 11 requires zero new packages. All tooling is already in the lockfile.

## Architecture Patterns

### Recommended Project Structure
No new files needed. Changes are confined to:
```
app/
├── models/game_position.py       # Add move_san column + new index
├── services/zobrist.py           # Extend hashes_for_game() return signature
└── services/import_service.py   # Update _flush_batch() to populate move_san
alembic/versions/
└── YYYYMMDD_HHMMSS_xxxx_add_move_san_to_game_positions.py  # New migration
tests/
├── test_zobrist.py               # New tests for move_san in hashes_for_game
└── test_game_repository.py       # Update position row fixtures to include move_san
```

### Pattern 1: python-chess SAN Before Push

**What:** `board.san(move)` must be called while the board is in the position FROM which the move is played. After `board.push(move)`, the board is in the resulting position and `board.san(move)` would be invalid (or ambiguous).

**When to use:** Every position row except the final ply gets the SAN of the next move.

**Example:**
```python
# Source: verified empirically against python-chess 1.10.x
board = game.board()  # starting position

for i, move in enumerate(moves):
    move_san = board.san(move)   # BEFORE push — board at ply i
    board.push(move)             # advance to ply i+1
    # position at ply i has move_san = move_san (the move played FROM it)
    # position at ply i+1 (final) will have move_san = None

# After loop: board is at final position (ply = len(moves))
# The final position row gets move_san = None
```

### Pattern 2: Extended hashes_for_game() Return Signature

**What:** Change the return type from `list[tuple[int, int, int, int]]` to `list[tuple[int, int, int, int, str | None]]`, adding `move_san` as the 5th element.

**Backward compatibility concern:** All callers of `hashes_for_game()` must be updated. Current callers:
- `import_service._flush_batch()` — unpacks `for ply, white_hash, black_hash, full_hash in hash_tuples:`
- `tests/test_zobrist.py` — accesses result by index `results[0][1]` etc.

**Example of updated function:**
```python
# app/services/zobrist.py
def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int, str | None]]:
    """Returns (ply, white_hash, black_hash, full_hash, move_san) for every half-move."""
    ...
    for i, move in enumerate(moves):
        move_san: str | None = board.san(move)   # before push
        board.push(move)
        wh, bh, fh = compute_hashes(board)
        results.append((i + 1, wh, bh, fh, None))  # ply i+1 — does NOT have move_san yet

    # This approach is WRONG — the above attaches None to the position we just arrived at
    # The correct approach attaches move_san to the ORIGIN position:

    # CORRECT LOOP:
    board = game.board()
    # ply 0: initial position, move_san = first move played from it (or None if no moves)
    # We need to look-ahead one move to know the san for ply 0

    results = []
    for i, move in enumerate(moves):
        move_san = board.san(move)       # san of move played FROM current position (ply i)
        wh, bh, fh = compute_hashes(board)
        results.append((i, wh, bh, fh, move_san))   # ply i, move played from it
        board.push(move)

    # Final position (ply = len(moves)): no move played from it
    wh, bh, fh = compute_hashes(board)
    results.append((len(moves), wh, bh, fh, None))

    return results
```

**Note:** This restructures the loop relative to the existing implementation. The existing code computes ply-0 hashes before the loop and appends them, then iterates `enumerate(moves, start=1)`. The new structure must compute hashes AND san together in the same loop iteration, then append the final position after the loop.

### Pattern 3: Alembic Migration for Nullable Column + Index

**What:** A single Alembic revision that adds the nullable column and the covering index. The `autogenerate` command picks up both changes from the updated model.

**Example:**
```python
# alembic/versions/YYYYMMDD_add_move_san_to_game_positions.py
def upgrade() -> None:
    op.add_column('game_positions',
        sa.Column('move_san', sa.String(length=10), nullable=True)
    )
    op.create_index(
        'ix_gp_user_full_hash_move_san',
        'game_positions',
        ['user_id', 'full_hash', 'move_san'],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index('ix_gp_user_full_hash_move_san', table_name='game_positions')
    op.drop_column('game_positions', 'move_san')
```

### Pattern 4: SQLAlchemy Model Column + Index

```python
# app/models/game_position.py
from typing import Optional
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        Index("ix_gp_user_full_hash", "user_id", "full_hash"),
        Index("ix_gp_user_white_hash", "user_id", "white_hash"),
        Index("ix_gp_user_black_hash", "user_id", "black_hash"),
        Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),  # NEW
    )
    ...
    move_san: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
```

**SAN length bound:** The longest possible SAN strings are around 7-8 characters (e.g., `Nxd7+`, `O-O-O`, `Qxf8#`, `exd8=Q+`). `String(10)` is safe with margin.

### Anti-Patterns to Avoid

- **Call `board.san(move)` AFTER `board.push(move)`:** SAN will be based on the wrong position. The board must be in the source position.
- **Attach move_san to ply N+1 (the arrived-at position):** The semantics require `move_san` at ply N = move played FROM ply N. Attaching it to the resulting position is semantically wrong and breaks the Phase 12 query.
- **Replace `ix_gp_user_full_hash` with the new covering index:** The existing index is used by white_hash/black_hash queries too (via separate indexes). The new covering index is additive.
- **Use `board.uci(move)` instead of `board.san(move)`:** UCI notation (e.g., `e2e4`) is not human-readable and is not what the Move Explorer UI expects.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SAN generation | Custom algebraic notation formatter | `board.san(move)` from python-chess | Handles ambiguity (Nbd2 vs Nfd2), special cases (O-O, promotions), check/checkmate indicators |
| Move disambiguation | Custom piece-conflict detection | python-chess handles automatically | Requires scanning all same-type pieces for ambiguous moves |

**Key insight:** SAN is context-dependent and deceptively complex. `Nf3` vs `Ndf3` vs `N1f3` depend on which other knights can reach f3. Only python-chess has the complete board state to compute this correctly.

## Common Pitfalls

### Pitfall 1: Wrong Loop Structure in hashes_for_game()
**What goes wrong:** The existing loop uses `enumerate(moves, start=1)` and computes ply-0 hashes before the loop. If you naively add `board.san(move)` inside the loop, you'll associate the SAN with the position the move LEADS TO (ply N+1), not the position it was played FROM (ply N).
**Why it happens:** It's natural to think "this move results in this position" and attach the SAN to the resulting position dict.
**How to avoid:** Restructure the loop: compute hashes and SAN BEFORE push for each ply, then append the final position (with `move_san=None`) AFTER the loop.
**Warning signs:** Tests show move_san at ply 1 = 'e4' (the move that LED to ply 1) instead of ply 0 = 'e4' (the move played FROM ply 0).

### Pitfall 2: Forgetting to Update All Callers of hashes_for_game()
**What goes wrong:** `_flush_batch()` in `import_service.py` unpacks the tuple with `for ply, white_hash, black_hash, full_hash in hash_tuples:` — adding a 5th element without updating this unpack causes `ValueError: too many values to unpack`.
**Why it happens:** The return type change is a breaking change to all callers.
**How to avoid:** Search for all uses of `hashes_for_game()` before changing its signature. In this codebase: only `import_service._flush_batch()` and test files.
**Warning signs:** `ValueError: too many values to unpack` at import time.

### Pitfall 3: NULL Semantics Mismatch
**What goes wrong:** Ply-0 gets `NULL` for `move_san` when it should get the SAN of the first move. The phase requirement says "NULL at final position and ply 0" — but STATE.md clarifies ply-0 has `move_san = move played FROM ply 0` (which is non-NULL for non-empty games).
**Why it happens:** Misreading the requirement. "NULL at ply 0" in the requirements doc means ply-0 of a game with NO moves. For normal games, ply-0 has `move_san = first move`.
**How to avoid:** Re-read STATE.md: "move_san on ply N = move played FROM position at ply N (leading to ply N+1); final position row has NULL; ply-0 has NULL" — the "ply-0 has NULL" refers to the special case where ply-0 IS the final position (0-move game). For games with moves, ply-0 will have a non-NULL `move_san`.
**Warning signs:** Tests show `move_san=None` at ply 0 for a game like "1. e4 e5 *".

### Pitfall 4: EXPLAIN ANALYZE Shows Bitmap Heap Scan Instead of Index Only Scan
**What goes wrong:** PostgreSQL uses a Bitmap Heap Scan instead of Index Only Scan, even with the covering index.
**Why it happens:** The visibility map may not be updated (freshly inserted data). In production this resolves after `VACUUM`. In tests with rolled-back transactions, the visibility map is never populated, so Index Only Scan may not appear.
**How to avoid:** For the EXPLAIN ANALYZE verification in success criteria, run `VACUUM ANALYZE game_positions` first, then test against a table with real data (not a rolled-back transaction). Alternatively, accept "Index Scan" as passing since it still uses the covering index.
**Warning signs:** EXPLAIN ANALYZE shows `Heap Fetches: N` > 0 in an Index Only Scan, or falls back to Bitmap Heap Scan on fresh data.

### Pitfall 5: Alembic autogenerate Missing the Index
**What goes wrong:** `alembic revision --autogenerate` generates the `add_column` but not the `create_index`.
**Why it happens:** Alembic autogenerate detects `Index` objects in `__table_args__` but only if the model file has been imported (via `env.py`'s `target_metadata`). If the models import chain is broken, indexes are silently skipped.
**How to avoid:** After generating the migration, inspect it manually and confirm both `op.add_column` AND `op.create_index` are present. If the index is missing, add it manually.
**Warning signs:** Generated migration only has `op.add_column`, no `op.create_index`.

## Code Examples

### Correct hashes_for_game() with move_san

```python
# app/services/zobrist.py — updated signature
def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int, str | None]]:
    """Parse pgn_text and return (ply, white_hash, black_hash, full_hash, move_san) for every half-move.

    move_san is the SAN of the move played FROM this position (leading to the next ply).
    It is None for the final position row (no move played from it).
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []

    if game is None:
        return []

    moves = list(game.mainline_moves())
    if not moves:
        return []

    results: list[tuple[int, int, int, int, str | None]] = []
    board = game.board()

    for ply, move in enumerate(moves):
        move_san: str = board.san(move)        # BEFORE push: board at ply 'ply'
        wh, bh, fh = compute_hashes(board)
        results.append((ply, wh, bh, fh, move_san))
        board.push(move)

    # Final position: no move played from it
    wh, bh, fh = compute_hashes(board)
    results.append((len(moves), wh, bh, fh, None))

    return results
```

### Updated _flush_batch() tuple unpack

```python
# app/services/import_service.py — inside _flush_batch()
for ply, white_hash, black_hash, full_hash, move_san in hash_tuples:
    position_rows.append({
        "game_id": game_id,
        "user_id": user_id,
        "ply": ply,
        "white_hash": white_hash,
        "black_hash": black_hash,
        "full_hash": full_hash,
        "move_san": move_san,   # NEW
    })
```

### EXPLAIN ANALYZE verification query

```sql
-- Run after VACUUM ANALYZE game_positions
EXPLAIN ANALYZE
SELECT move_san, COUNT(*) AS cnt
FROM game_positions
WHERE user_id = 1 AND full_hash = -1234567890123456789
GROUP BY move_san;
-- Expected: Index Only Scan using ix_gp_user_full_hash_move_san
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No move_san in game_positions | move_san column on game_positions | Phase 11 | Enables next-moves aggregation without joining games table |
| ix_gp_user_full_hash (2 columns) | ix_gp_user_full_hash_move_san (3 columns, covering) | Phase 11 | Index-only scan for move explorer aggregation |

## Open Questions

1. **EXPLAIN ANALYZE test environment**
   - What we know: The success criteria requires EXPLAIN ANALYZE shows the covering index is used
   - What's unclear: Test DB transactions are rolled back — visibility map not updated, so Index Only Scan may not appear even with the index. May show Index Scan instead.
   - Recommendation: Verify against a populated DB with `VACUUM ANALYZE` run first. Accept "Index Scan using ix_gp_user_full_hash_move_san" as passing if "Index Only Scan" requires vacuum.

2. **ply-0 NULL semantics edge case**
   - What we know: STATE.md says "ply-0 has NULL" but in practice ply-0 has move_san for games with moves
   - What's unclear: The requirement language says "NULL appears on ply-0 rows" — this seems to conflict with STATE.md semantics
   - Recommendation: Follow STATE.md semantics: ply-0 gets the SAN of the first move (non-NULL for normal games). The "ply-0 NULL" in requirements likely refers to: NULL only appears on the final row (and if there are somehow 0 moves, ply-0 = final position = NULL). Verify by re-reading success criteria: "NULL appears on ply-0 rows and the final position row" — this reads as if ply-0 always has NULL. This contradicts STATE.md. **Resolve before implementing:** check with user or treat STATE.md as authoritative.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/test_zobrist.py tests/test_game_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEXP-01 | GamePosition model has nullable move_san column | unit | `uv run pytest tests/test_game_repository.py -x -k move_san` | ❌ Wave 0 |
| MEXP-01 | Alembic migration adds move_san column to DB | integration | `uv run pytest tests/test_game_repository.py -x -k move_san` | ❌ Wave 0 |
| MEXP-02 | Covering index ix_gp_user_full_hash_move_san exists | integration | `uv run pytest tests/test_game_repository.py -x -k covering_index` | ❌ Wave 0 |
| MEXP-03 | hashes_for_game returns move_san at each ply | unit | `uv run pytest tests/test_zobrist.py -x -k move_san` | ❌ Wave 0 |
| MEXP-03 | move_san is NULL on final position row | unit | `uv run pytest tests/test_zobrist.py -x -k move_san` | ❌ Wave 0 |
| MEXP-03 | position_rows include move_san during import | unit | `uv run pytest tests/test_import_service.py -x -k move_san` | ❌ Wave 0 |
| MEXP-03 | Re-import produces identical move_san values | integration | `uv run pytest tests/test_game_repository.py -x -k reimport` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_zobrist.py` — add `test_hashes_for_game_returns_move_san`, `test_hashes_for_game_move_san_null_on_final_ply`, `test_hashes_for_game_move_san_ply_zero`
- [ ] `tests/test_game_repository.py` — update `_make_position_row()` helpers to include `move_san` field; add `test_bulk_insert_positions_with_move_san`
- [ ] `tests/test_import_service.py` — update `position_rows` assertion to verify `move_san` key is present

*(Existing test infrastructure covers all execution — only new test cases needed, not new framework setup)*

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection — `app/services/zobrist.py`, `app/services/import_service.py`, `app/models/game_position.py`, `app/repositories/game_repository.py`
- `tests/test_zobrist.py`, `tests/test_import_service.py`, `tests/test_game_repository.py` — existing test patterns
- `.planning/STATE.md` — locked decisions (db wipe, move_san semantics)
- `.planning/REQUIREMENTS.md` — MEXP-01, MEXP-02, MEXP-03 definitions
- Empirical python-chess verification via `uv run python` — confirmed `board.san(move)` must be called before `board.push(move)`

### Secondary (MEDIUM confidence)
- PostgreSQL covering index / index-only scan behavior — standard PostgreSQL documentation pattern; verified against project's asyncpg/PostgreSQL stack

### Tertiary (LOW confidence)
- None — all claims verified directly against codebase or empirically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all tools verified in lockfile
- Architecture: HIGH — all patterns verified empirically against codebase; python-chess API confirmed
- Pitfalls: HIGH — loop restructuring pitfall verified empirically; NULL semantics flagged as open question needing resolution

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable dependencies, no fast-moving ecosystem)
