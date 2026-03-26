# Phase 31: Endgame Classification Redesign - Research

**Researched:** 2026-03-26
**Domain:** PostgreSQL data migration, SQLAlchemy ORM, endgame analytics query redesign
**Confidence:** HIGH

## Summary

Phase 31 redesigns the endgame analytics system from a per-game single-transition-point model to a per-position model. Currently, each game produces one row in the analytics pipeline (the MIN-ply position where `piece_count <= 6`). The new design stores `endgame_class` directly on every `game_positions` row that qualifies as an endgame position, then counts distinct games per class that meet a 6-ply minimum dwell threshold.

The backfill is straightforward: `material_signature` and `piece_count` are already stored on every position row, so `endgame_class` can be derived entirely in SQL via character counting — identical to the technique used in the `piece_count` backfill migration (Phase 26). No PGN replay is needed.

The query redesign replaces the MIN-ply subquery approach in `endgame_repository.py` with a GROUP BY `(game_id, endgame_class)` + HAVING `COUNT(*) >= 6` approach. The result is a flat list of `(game_id, endgame_class, material_imbalance_at_first_position)` rows that feeds the existing `_aggregate_endgame_stats()` aggregation in `endgame_service.py` with minimal changes to that function's logic.

**Primary recommendation:** Implement as a single Alembic migration (add column + SQL backfill using PL/pgSQL batched UPDATE), wire `endgame_class` computation into `_flush_batch()` using the existing `classify_endgame_class()` function, and rewrite `query_endgame_entry_rows()` to use the per-position GROUP BY approach.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Keep the same Endgames tab UI (Statistics + Games sub-tabs, filters, charts). No frontend changes needed. The backend queries become simpler and more accurate.
- **D-02:** A game can count in **multiple endgame classes**. If a game passes through a rook endgame and then a pawn endgame, it counts in both categories — each game outcome (W/D/L) is counted in every endgame class the game participated in.
- **D-03:** **6 plies minimum threshold** — a game only counts in an endgame class if it spent at least 6 plies (3 full moves) in that class. This filters out tactical transitions (piece sacrifices into checkmate, quick class changes) and captures only sustained endgame play.
- **D-04:** Conversion/recovery uses **material_imbalance at the first position** of each endgame class span. Same semantics as today's transition point, applied per-class: "you entered this endgame type up/down material."
- **D-05:** Do NOT store `game_phase` — it's easily derived from `piece_count <= 6` at query time. Only store `endgame_class`.
- **D-06:** Add `endgame_class` as **SmallInteger** column to `game_positions` — mapped to an IntEnum (1-6) in Python. 2 bytes per row, fastest for GROUP BY. NULL for non-endgame positions. No VARCHAR overhead on the largest table.
- **D-07:** Endgame class derivation stays as a **separate function** from `classify_position()`. The existing `classify_endgame_class(material_signature)` in `endgame_service.py` is the source of truth. It should be called during import for new games and during backfill for existing rows.
- **D-08:** **Alembic data migration** for backfill — single migration adds the column AND populates it from existing `material_signature` + `piece_count` data. No PGN replay needed.

### Claude's Discretion

- SQL query structure for counting plies per (game_id, endgame_class) and filtering by threshold
- Whether to move `classify_endgame_class()` to position_classifier.py or keep it in endgame_service.py
- Batching strategy for the Alembic data migration UPDATE
- Index strategy for the new endgame_class column (if needed for GROUP BY performance)

### Deferred Ideas (OUT OF SCOPE)

- **Position-level endgame drill-down** — Explore specific endgame positions on a board (like Openings tab for endgames). Builds on stored per-position endgame_class but is a separate feature.
- **MATFLT-01 — Material signature drill-down** — Finer breakdown by specific material configuration (e.g., KRP vs KR within rook endgames). Already tracked in REQUIREMENTS.md.
- **Material signature BIGINT encoding** — Encode material_signature as a single BIGINT (40 bits: 4 bits × 5 piece types × 2 sides) instead of VARCHAR(40). Saves ~25 bytes/row worst case. Could fold into Phase 27.1 (column type optimization).
</user_constraints>

---

## Standard Stack

No new libraries are needed. This phase uses the established project stack exclusively.

### Core (existing)
| Component | Version | Purpose | Role in Phase |
|-----------|---------|---------|---------------|
| SQLAlchemy 2.x async | 2.x | ORM + query building | Add mapped column, rewrite queries |
| Alembic | current | Schema migrations | Add column + batched SQL backfill |
| asyncpg | current | PostgreSQL async driver | Executes migration and queries |
| python-chess | 1.10.x | Chess logic | Not touched (classify_position unchanged) |
| FastAPI + Pydantic v2 | 0.115.x | API layer | Minimal changes (service signatures stable) |

**No installation required** — all dependencies already present in `pyproject.toml`.

---

## Architecture Patterns

### Current Architecture (per-game, to be replaced)

```
query_endgame_entry_rows():
  Subquery: MIN(ply) per game WHERE piece_count <= 6
  Join: game_positions at entry_ply to get material_signature + imbalance
  Returns: [(game_id, result, user_color, material_signature, user_material_imbalance)]

endgame_service._aggregate_endgame_stats(rows):
  Calls classify_endgame_class(material_signature) for each row
  Accumulates W/D/L + conversion/recovery per class
```

**Limitation:** One game = one endgame class. A game transiting rook→pawn only counts in rook.

### Target Architecture (per-position, multi-class per game)

```
query_endgame_entry_rows():   ← RENAMED or redesigned
  CTE/subquery: per (game_id, endgame_class) span
    - COUNT(ply) per (game_id, endgame_class) — must be >= 6
    - MIN(ply) per (game_id, endgame_class) — for entry imbalance lookup
  Join: game_positions at min_ply to get material_imbalance (D-04)
  Join: games for result, user_color, and game filters
  Returns: [(game_id, endgame_class, result, user_color, user_material_imbalance)]
                                     ^--- endgame_class stored in DB now

endgame_service._aggregate_endgame_stats(rows):
  No classify_endgame_class() call needed (class already in row)
  Same W/D/L + conversion/recovery accumulation logic
  Multi-class per game: game_id can appear multiple times (once per class)
```

### Pattern 1: SQL Query Structure for Per-Position Grouping

The key insight is two levels of aggregation:
1. Count plies per `(game_id, endgame_class)` → filter by `>= ENDGAME_PLY_THRESHOLD`
2. Get `material_imbalance` at the **first** ply of each span (MIN ply) → D-04

```python
# Source: existing patterns in endgame_repository.py, adapted for multi-class
from sqlalchemy import func, select, case

ENDGAME_PLY_THRESHOLD = 6  # minimum plies in an endgame class to count (D-03)

# Subquery 1: count plies and find entry ply per (game_id, endgame_class)
# Only positions with endgame_class IS NOT NULL (endgame positions only)
span_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        GamePosition.endgame_class.label("endgame_class"),
        func.count(GamePosition.ply).label("ply_count"),
        func.min(GamePosition.ply).label("entry_ply"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    .group_by(GamePosition.game_id, GamePosition.endgame_class)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("span")
)

# Subquery 2: get material_imbalance at the entry ply for each span
entry_pos_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        GamePosition.ply.label("ply"),
        GamePosition.material_imbalance.label("material_imbalance"),
    )
    .where(GamePosition.user_id == user_id)
    .subquery("entry_pos")
)

# Main query: join spans → entry positions → games
color_sign = case((Game.user_color == "white", 1), else_=-1)

stmt = (
    select(
        Game.id.label("game_id"),
        span_subq.c.endgame_class,
        Game.result,
        Game.user_color,
        (entry_pos_subq.c.material_imbalance * color_sign).label("user_material_imbalance"),
    )
    .join(span_subq, Game.id == span_subq.c.game_id)
    .join(
        entry_pos_subq,
        (entry_pos_subq.c.game_id == span_subq.c.game_id)
        & (entry_pos_subq.c.ply == span_subq.c.entry_ply),
    )
    .where(Game.user_id == user_id)
)
stmt = _apply_game_filters(stmt, ...)
```

**Note on endgame_class encoding:** D-06 specifies SmallInteger storage with IntEnum mapping. The SQL GROUP BY groups on the integer value. Python converts via the IntEnum to `EndgameClass` string before returning rows to the service. Alternatively, the service can receive integer values and map them — see Pattern 3.

### Pattern 2: Alembic Data Migration Backfill

The backfill follows the exact same PL/pgSQL batched UPDATE pattern as the `piece_count` backfill (migration `265efff85685`). The endgame_class mapping must be expressed in pure SQL. Since the 6 class values are simple character-presence tests on `material_signature`, they translate directly to SQL CASE expressions:

```sql
-- In Alembic upgrade() via op.execute():
DO $$
DECLARE
    batch_size INT := 50000;
    min_id BIGINT;
    max_id BIGINT;
    current_min BIGINT;
BEGIN
    SELECT MIN(id), MAX(id) INTO min_id, max_id
    FROM game_positions
    WHERE piece_count IS NOT NULL
      AND piece_count <= 6
      AND endgame_class IS NULL;

    IF min_id IS NULL THEN
        RETURN;
    END IF;

    current_min := min_id;
    WHILE current_min <= max_id LOOP
        UPDATE game_positions
        SET endgame_class = CASE
            -- Multi-family test first (mixed = 2+ piece families)
            WHEN (
                (material_signature ~ '[Q]') AND
                (material_signature ~ '[RBN]')
            ) OR (
                (material_signature ~ '[R]') AND
                (material_signature ~ '[BN]')
            ) THEN 5  -- mixed
            -- Single piece family
            WHEN material_signature ~ '[Q]' THEN 4  -- queen
            WHEN material_signature ~ '[R]' THEN 1  -- rook
            WHEN material_signature ~ '[BN]' THEN 2  -- minor_piece
            WHEN material_signature ~ '[P]' THEN 3  -- pawn
            ELSE 6  -- pawnless (bare kings)
        END
        WHERE id >= current_min
          AND id < current_min + batch_size
          AND piece_count IS NOT NULL
          AND piece_count <= 6
          AND endgame_class IS NULL
          AND material_signature IS NOT NULL;

        current_min := current_min + batch_size;
    END LOOP;
END $$;
```

**IntEnum mapping (Python side):**
```python
from enum import IntEnum

class EndgameClassInt(IntEnum):
    ROOK = 1
    MINOR_PIECE = 2
    PAWN = 3
    QUEEN = 4
    MIXED = 5
    PAWNLESS = 6

# Mapping to existing EndgameClass Literal strings
_INT_TO_CLASS: dict[int, EndgameClass] = {
    1: "rook",
    2: "minor_piece",
    3: "pawn",
    4: "queen",
    5: "mixed",
    6: "pawnless",
}

_CLASS_TO_INT: dict[EndgameClass, int] = {v: k for k, v in _INT_TO_CLASS.items()}
```

### Pattern 3: Import Pipeline Wiring

The import pipeline in `_flush_batch()` already calls `classify_position()` per position. Adding `endgame_class` is a single conditional assignment:

```python
# In _flush_batch(), inside the per-position loop, after classify_position() is called:
from app.services.endgame_service import classify_endgame_class, _CLASS_TO_INT

if classification.piece_count is not None and classification.piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD:
    endgame_class_str = classify_endgame_class(classification.material_signature)
    row["endgame_class"] = _CLASS_TO_INT[endgame_class_str]
else:
    row["endgame_class"] = None
```

`ENDGAME_PIECE_COUNT_THRESHOLD` is already importable from `endgame_repository.py`.

### Pattern 4: query_endgame_games Redesign

`query_endgame_games` currently fetches all entry rows and classifies in Python. With `endgame_class` stored in the DB, filtering by class becomes a simple WHERE predicate:

```python
# Revised approach: use the same span_subq filtered to a specific endgame_class integer
# This eliminates the Python-side classify loop entirely
```

The existing function can be simplified to filter directly on `endgame_class` in the spans subquery:
```python
.where(span_subq.c.endgame_class == _CLASS_TO_INT[endgame_class])
```

### Pattern 5: _aggregate_endgame_stats() Row Shape Change

The aggregation function currently receives rows shaped as:
```
(game_id, result, user_color, material_signature, user_material_imbalance)
```

After redesign, rows will be shaped as:
```
(game_id, endgame_class_int, result, user_color, user_material_imbalance)
```

The inner loop no longer calls `classify_endgame_class()`. The `endgame_class_int` is converted to an `EndgameClass` string via `_INT_TO_CLASS`. The W/D/L accumulation logic is unchanged.

### Anti-Patterns to Avoid

- **Don't call classify_endgame_class() in _aggregate_endgame_stats() after the redesign.** The class is now in the DB; the service aggregation function should use the pre-computed integer value from the query result.
- **Don't filter piece_count in the new query.** The `endgame_class IS NOT NULL` condition already implies `piece_count <= 6` — the column was only set on endgame positions. Double-filtering adds noise.
- **Don't use a self-join on game_positions twice in the main query.** One join on `entry_pos_subq` is sufficient since we pre-computed `entry_ply` in `span_subq`. Two independent joins blow up execution plan.
- **Don't add `endgame_class` to `PositionClassification` dataclass.** CONTEXT.md D-07 and the `position_classifier.py` docstring are explicit: game_phase and endgame_class are NOT part of `classify_position()` output.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Batched SQL UPDATE in migration | Custom Python batching script | PL/pgSQL DO block in Alembic (established pattern) | Already working in `265efff85685`; runs inside the migration transaction cleanly |
| endgame_class SQL expression | Custom SQL function | SQL CASE on `material_signature` using regex matching | Pure SQL, no extension dependency, identical logic to existing Python function |
| IntEnum-to-string mapping | Ad-hoc dict | Python `IntEnum` + bidirectional dict (Pattern 2 above) | Type-safe, DRY, localized in one module |

---

## Common Pitfalls

### Pitfall 1: asyncpg 32767-argument limit — chunk_size recalculation required

**What goes wrong:** `bulk_insert_positions()` currently has `chunk_size = 1900` based on 17 columns (from the comment in `game_repository.py`: "Each position row has 17 columns"). After adding `endgame_class`, the row has **19 columns** (18 existing + 1 new). Floor(32767 / 19) = 1724. The existing 1900 chunk_size will exceed the limit.

**Why it happens:** asyncpg sends each value as a separate bound parameter. The 32,767 limit is hard.

**How to avoid:** Update `chunk_size = 1700` (safety margin below 1724). Update the comment in `bulk_insert_positions()`.

**Verification:** Check that the comment in `game_repository.py` reflects the new column count.

**Current column count:** 18 (confirmed by inspecting the `GamePosition` mapper at runtime: id, game_id, user_id, ply, full_hash, white_hash, black_hash, move_san, clock_seconds, material_count, material_signature, material_imbalance, has_opposite_color_bishops, piece_count, backrank_sparse, mixedness, eval_cp, eval_mate). Adding `endgame_class` = 19 total.

### Pitfall 2: endgame_games query double-counts games already in v1 tests

**What goes wrong:** Existing `test_endgame_repository.py` tests seed `GamePosition` rows without `endgame_class`. After the redesign, `query_endgame_entry_rows` will use `endgame_class IS NOT NULL` — so tests with NULL `endgame_class` will return 0 rows.

**Why it happens:** Test fixtures (`_seed_game_position`) don't set `endgame_class`. The old query used `piece_count <= threshold`, which still works on NULL `endgame_class`.

**How to avoid:** Update `_seed_game_position()` fixture in `test_endgame_repository.py` to accept and set `endgame_class` parameter. Update all existing test cases to seed `endgame_class` values.

### Pitfall 3: SQL regex for endgame_class backfill must handle the underscore separator

**What goes wrong:** `material_signature` format is `KR_KR` — the `_` separator is between white and black sides. A naive regex `~ 'Q'` will match `Q` anywhere in the string (including the underscore side), which is correct. The underscore itself does not contain QRBN letters, so letter-presence checks are safe.

**Why it happens:** The underscore separator is just a divider and contains none of the piece letters.

**How to avoid:** The backfill SQL CASE above is correct as-is. The mixed detection (two piece families) must check that **combining both sides** has 2+ families — which is already true since the regex checks the whole signature string (both sides combined).

**Warning sign:** If bare-king endgames `K_K` are being classified as `pawnless` but showing a non-zero regex match for piece letters, there's a bug.

### Pitfall 4: endgame_games circular import between endgame_repository and endgame_service

**What goes wrong:** Currently `query_endgame_games` uses `from app.services.endgame_service import classify_endgame_class` via a local import to avoid circular imports. After the redesign, if `endgame_class` values need Python-side conversion (int → string), that mapping must live somewhere accessible from both the repository and service.

**Why it happens:** The `_INT_TO_CLASS` mapping will be needed in the repository layer (to filter by class in the query) but also in the service layer (to display labels).

**How to avoid:** Place `EndgameClassInt`, `_INT_TO_CLASS`, and `_CLASS_TO_INT` in `endgame_service.py` alongside `classify_endgame_class()`. The repository can import the mapping from the service (using a local import if needed to preserve import order).

Alternatively: place the IntEnum and mapping in `endgame_schemas.py` — a neutral location with no business logic that neither repository nor service imports _from_.

### Pitfall 5: Production table size — backfill must be batched

**What goes wrong:** An unbatched `UPDATE game_positions SET endgame_class = ...` on the full table will hold a long exclusive lock, block concurrent reads/writes, and potentially OOM the production server.

**Why it happens:** game_positions is the largest table in the database (every position of every game for all users). Production has had OOM kills during large operations.

**How to avoid:** Use the PL/pgSQL batched UPDATE pattern from `265efff85685` with `batch_size = 50000` (same as the piece_count migration that ran successfully). The backfill only touches rows with `piece_count IS NOT NULL AND piece_count <= 6 AND endgame_class IS NULL`.

---

## Code Examples

### Example 1: Adding endgame_class to GamePosition model

```python
# app/models/game_position.py — add after eval_mate column
# endgame_class: SmallInteger IntEnum (1-6), NULL for non-endgame positions
# 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless
# Computed from material_signature at import time (see endgame_service.classify_endgame_class)
endgame_class: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

### Example 2: Wiring into _flush_batch() in import_service.py

```python
# After row.update({...classify_position output...}):
from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD
from app.services.endgame_service import classify_endgame_class, _CLASS_TO_INT

piece_count = classification.piece_count
if (
    piece_count is not None
    and piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD
    and classification.material_signature is not None
):
    ec_str = classify_endgame_class(classification.material_signature)
    row["endgame_class"] = _CLASS_TO_INT[ec_str]
else:
    row["endgame_class"] = None
```

This is placed inside the `if classify_board is not None:` block, after the `row.update({...})` call that sets `piece_count`.

### Example 3: _aggregate_endgame_stats() with redesigned row shape

```python
# Rows now: (game_id, endgame_class_int, result, user_color, user_material_imbalance)
for _game_id, endgame_class_int, result, user_color, user_material_imbalance in rows:
    endgame_class = _INT_TO_CLASS[endgame_class_int]  # replaces classify_endgame_class() call
    outcome = derive_user_result(result, user_color)
    # ... rest of accumulation logic unchanged
```

---

## Index Strategy (Claude's Discretion)

The new query groups and filters on `(user_id, endgame_class)` within `game_positions`. The existing index `ix_gp_user_full_hash` (covering `user_id, full_hash`) does not help.

**Recommendation: Add a partial index on endgame positions only.**

```python
# In GamePosition.__table_args__:
Index(
    "ix_gp_user_endgame_class",
    "user_id",
    "endgame_class",
    postgresql_where=text("endgame_class IS NOT NULL"),
),
```

**Rationale:**
- Endgame positions are a small fraction of total rows (perhaps 20-30% at most). A partial index covers only those rows.
- The GROUP BY `(game_id, endgame_class)` with HAVING benefits from this index to filter by `user_id` first.
- Without an index, the query does a full table scan on `game_positions` for every endgame stats request.
- The existing hash indexes don't help endgame queries at all.

**Alternative:** If the partial index adds excessive migration complexity, a non-partial `(user_id, endgame_class)` index also works but is slightly larger.

---

## classify_endgame_class() Placement (Claude's Discretion)

**Recommendation: Keep it in `endgame_service.py`.**

Rationale:
- The function takes a `material_signature: str` and returns an `EndgameClass` string — it's pure business logic, not a low-level classifier.
- `position_classifier.py` is documented as a pure function returning raw metrics from a `chess.Board`. Adding string-to-category mapping there changes its character.
- The import pipeline only needs to call `classify_endgame_class()` from `endgame_service.py` — the circular import concern is manageable via local import (already done in `query_endgame_games`).
- Moving it to `position_classifier.py` would make `position_classifier.py` depend on `EndgameClass` schema types, tightening a coupling that should remain loose.

The `_CLASS_TO_INT` and `_INT_TO_CLASS` dicts should live alongside `classify_endgame_class()` in `endgame_service.py`.

---

## Runtime State Inventory

> Not applicable — this is a schema migration + query redesign, not a rename/refactor. No runtime state outside the database is affected.

---

## Environment Availability

This phase is purely backend code and Alembic migration. No new external dependencies.

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| PostgreSQL 18 (Docker) | All DB operations | Required — not checked here | Standard dev setup |
| Python 3.13 + uv | Backend tests | Required — standard dev setup | |

**No missing dependencies.**

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_endgame_service.py tests/test_endgame_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `endgame_class` column in GamePosition model | unit (model inspection) | `uv run pytest tests/test_endgame_repository.py -x` | Update existing |
| Import pipeline sets `endgame_class` on endgame positions | integration | `uv run pytest tests/test_import_service.py -x` | Update existing |
| Import pipeline sets `endgame_class = NULL` for non-endgame positions | integration | `uv run pytest tests/test_import_service.py -x` | Update existing |
| `query_endgame_entry_rows` returns multi-class rows per game | integration | `uv run pytest tests/test_endgame_repository.py -x` | Update existing |
| `query_endgame_entry_rows` filters by 6-ply threshold (HAVING) | integration | `uv run pytest tests/test_endgame_repository.py -x` | New test |
| `query_endgame_entry_rows` returns one row per (game, class) not per game | integration | `uv run pytest tests/test_endgame_repository.py -x` | New test |
| `_aggregate_endgame_stats` uses endgame_class_int from row directly | unit | `uv run pytest tests/test_endgame_service.py -x` | Update row shape |
| `query_endgame_games` filters by class via DB column | integration | `uv run pytest tests/test_endgame_repository.py -x` | Update existing |
| `chunk_size` in bulk_insert_positions updated for 19 columns | unit | `uv run pytest tests/test_game_repository.py -x` | Review existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_endgame_service.py tests/test_endgame_repository.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test cases in `tests/test_endgame_repository.py` for 6-ply threshold filtering (HAVING COUNT >= 6) and multi-class per game behavior
- [ ] Update `_seed_game_position` fixture to accept and set `endgame_class` parameter — existing tests break without this
- [ ] Update existing `test_returns_one_row_per_game_min_ply` test — behavior changes from "one row per game" to "one row per (game, class)"

---

## Open Questions

1. **Should `endgame_games` count include `total_games` correctly?**
   - What we know: `endgame_games` in `EndgameStatsResponse` is currently computed as `sum(c.total for c in categories)`. With multi-class per game, a game appearing in two categories will be counted twice in this sum.
   - What's unclear: Is the current `endgame_games` field semantically "unique games that reached an endgame" or "total (game, class) combinations"?
   - Recommendation: The planner should decide whether `endgame_games` should count distinct game_ids (requires `COUNT(DISTINCT game_id)` in a separate query) or continue as a sum of per-category totals. The CONTEXT.md doesn't address this. If it stays as-is, document the double-counting as intentional in a comment.

2. **The `endgame_class` SQL CASE logic — integer ordering matters**
   - What we know: The Python `classify_endgame_class()` checks `piece_families >= 2` for mixed FIRST, before single-family checks. The SQL CASE must preserve this ordering (mixed before queen/rook/minor).
   - What's unclear: The regex approach `material_signature ~ '[Q]' AND material_signature ~ '[RBN]'` is correct. Double check: if signature is `KQR_K` — has Q and R, both present → mixed=5. Correct.
   - Recommendation: Add a test in migration to validate a known mixed signature (`KQR_K`) produces 5.

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `app/repositories/endgame_repository.py` — current query structure to be redesigned
- Direct code reading: `app/services/endgame_service.py` — `classify_endgame_class()`, `_aggregate_endgame_stats()`
- Direct code reading: `app/models/game_position.py` — 18 existing columns (confirmed via SQLAlchemy mapper inspection)
- Direct code reading: `app/repositories/game_repository.py` — `bulk_insert_positions()` with chunk_size=1900 for 17-column comment
- Direct code reading: `alembic/versions/265efff85685_*.py` — batched PL/pgSQL UPDATE pattern (piece_count backfill)
- Direct code reading: `app/services/import_service.py` `_flush_batch()` — exact wiring point for endgame_class
- Direct code reading: `tests/test_endgame_repository.py`, `tests/test_endgame_service.py` — existing test coverage
- Direct code reading: `.planning/phases/31-endgame-classification-redesign/31-CONTEXT.md` — locked decisions D-01 through D-08

### Secondary (MEDIUM confidence)
- `STATE.md` accumulated context: `chunk_size` history (4000 → 2100 → 2700 → 2300 → 1900) and reasoning
- `STATE.md`: "Every endgame aggregation query must use COUNT(DISTINCT game_id), not COUNT(*)" — important constraint for the new query counting rows per (game_id, endgame_class)

---

## Metadata

**Confidence breakdown:**
- Schema change: HIGH — direct model inspection confirms 18 existing columns; adding 1 = 19; chunk_size recalculation is arithmetic
- Migration pattern: HIGH — identical PL/pgSQL pattern from `265efff85685` is proven to work in production
- Query redesign: HIGH — direct reading of current query structure; new GROUP BY approach is standard SQL
- Import wiring: HIGH — direct reading of `_flush_batch()`; integration point is clear
- Test update requirements: HIGH — direct reading of test fixtures; `_seed_game_position` missing `endgame_class` will break tests

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable domain — no external dependencies)
