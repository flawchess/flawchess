# Phase 116: All-Ply Engine Core - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 5 (2 modified, 1 new coroutine in existing file, 1 new migration, 1 model column)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/engine.py` | service | request-response | self (extend existing) | exact |
| `app/services/eval_drain.py` | service | batch, event-driven | self (extend with new coroutine) | exact |
| `app/models/game.py` | model | — | self (add column) | exact |
| `app/models/game_position.py` | model | — | self (add index) | exact |
| `alembic/versions/<ts>_add_full_evals_completed_at.py` | migration | batch | `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` | exact |

---

## Pattern Assignments

### `app/services/engine.py` — add `evaluate_nodes()` + constants

**Analog:** same file — extend alongside existing `evaluate()` / `EnginePool.evaluate()`

**New constants pattern** (insert after line 85, alongside `_DEPTH` and `_TIMEOUT_S`):
```python
# D-03: UCI options live ONLY in this module (ENG-03 grep gate)
_DEPTH: int = 15
_TIMEOUT_S: float = 2.0

# Phase 116 EVAL-02: node-budget constants for full-game analysis drain.
# _NODES_TIMEOUT_S is distinct from _TIMEOUT_S — depth-15 mean ~0.09s; 1M-node
# mean ~0.98s (prod spike 002 p90 = 1.277s). _TIMEOUT_S = 2.0 would time out ~50%
# of node-budget calls on prod. 5.0s = ~4x prod p90 (spike 002).
_NODES_BUDGET: int = 1_000_000   # EVAL-02: Lichess fishnet parity (D-6 SEED-012)
_NODES_TIMEOUT_S: float = 5.0    # 4x prod p90 (1.277s, spike 002)
```

**Module-level function pattern** (lines 179-192 — mirror `evaluate()` exactly):
```python
async def evaluate(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at depth 15. Returns (eval_cp, eval_mate) in white perspective."""
    if _pool is None:
        return None, None
    return await _pool.evaluate(board)

# New — same shape, different limit:
async def evaluate_nodes(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at 1M nodes. Returns (eval_cp, eval_mate) in white perspective.

    EVAL-02: Lichess-parity budget for full-game analysis drain.
    Returns (None, None) on engine failure — same contract as evaluate().
    Do NOT pass multipv to analyse() here — PV capture is EVAL-04 / Phase 117.
    Scalar InfoDict returned directly, handled by existing _score_to_cp_mate().
    """
    if _pool is None:
        return None, None
    return await _pool.evaluate_nodes(board)
```

**`EnginePool.evaluate_nodes()` method pattern** (lines 297-323 — mirror `EnginePool.evaluate()` with `_NODES_BUDGET` / `_NODES_TIMEOUT_S`):
```python
async def evaluate(self, board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate a position on the next idle worker. Same contract as evaluate()."""
    if not self._started:
        return None, None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None, None
        try:
            info = await asyncio.wait_for(
                protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
                timeout=_TIMEOUT_S,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await self._restart_worker(idx)
            return None, None
        return _score_to_cp_mate(info)
    finally:
        self._available.put_nowait(idx)

# New — identical structure, swap Limit and timeout:
async def evaluate_nodes(self, board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate at 1M nodes on the next idle worker. EVAL-02."""
    if not self._started:
        return None, None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None, None
        try:
            info = await asyncio.wait_for(
                protocol.analyse(board, chess.engine.Limit(nodes=_NODES_BUDGET)),
                timeout=_NODES_TIMEOUT_S,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await self._restart_worker(idx)
            return None, None
        return _score_to_cp_mate(info)
    finally:
        self._available.put_nowait(idx)
```

**Key constraints:**
- Do NOT pass `multipv` to `analyse()` — no PV in Phase 116; scalar `InfoDict` returned, handled by existing `_score_to_cp_mate(info)` unchanged.
- `_score_to_cp_mate` (lines 195-212) is reused verbatim — sign convention is the same.
- UCI options (`Hash`, `Threads`) are configured once in `start()` / `_restart_worker()` — no per-call options change for node-budget.

---

### `app/services/eval_drain.py` — add `run_full_eval_drain()` + all-ply helpers

**Analog:** same file — `run_eval_drain()` (lines 561-665) is the mandatory template.

**New dataclass pattern** (insert after `_EvalTarget` / `_TargetSpec` at lines 92-120):
```python
@dataclass(slots=True)
class _FullPlyEvalTarget:
    """One position scheduled for full-ply eval (Phase 116 EVAL-01).

    ply: game_positions.ply (0-indexed; 0 = initial position before first move)
    full_hash: for dedup batch-lookup at ply <= _DEDUP_MAX_PLY (EVAL-03)
    board: board snapshot for the engine call (if not dedup'd)
    """
    game_id: int
    ply: int
    full_hash: int
    board: chess.Board
```

**All-ply board collector pattern** (mirrors `_snapshot_boards` at lines 169-195, but collects ALL plies):
```python
def _snapshot_boards(pgn_text: str, target_plies: set[int]) -> dict[int, chess.Board]:
    # existing: early-break when targets exhausted
    ...

# New: walk entire mainline, no early break, no target filtering
def _collect_full_ply_targets(
    game_id: int,
    pgn_text: str,
    game_positions_rows: Sequence[tuple[int, int, int | None, int | None]],
    # (ply, full_hash, eval_cp, eval_mate) from DB
) -> list[_FullPlyEvalTarget]:
    """Collect one target per non-terminal ply (EVAL-01).

    Terminal exclusion: mainline iterator yields positions BEFORE each push.
    Post-last-move board (game-over) is never visited. No is_game_over() guard needed.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []
    if game is None:
        return []

    ply_meta: dict[int, tuple[int, int | None, int | None]] = {
        ply: (fh, cp, mt)
        for ply, fh, cp, mt in game_positions_rows
    }

    board = game.board()
    targets: list[_FullPlyEvalTarget] = []
    for ply, node in enumerate(game.mainline()):
        meta = ply_meta.get(ply)
        if meta is not None:
            fh, _cp, _mt = meta
            targets.append(_FullPlyEvalTarget(game_id=game_id, ply=ply, full_hash=fh, board=board.copy()))
        board.push(node.move)
    # board is now terminal — NOT added.
    return targets
```

**Dedup batch lookup pattern** (new helper, no existing analog — use `_collect_eval_targets_from_db` style):
```python
# Pattern: session.execute(select(...).join(...).where(...)) returning dict
# Reference: _collect_eval_targets_from_db (lines 428-492)

async def _fetch_dedup_evals(
    session: AsyncSession,
    full_hashes: Sequence[int],
) -> dict[int, tuple[int | None, int | None]]:
    """Batch-fetch parity evals for opening-region hashes (EVAL-03, D-116-02).

    Marker gate: source games must have full_evals_completed_at IS NOT NULL
    (parity by construction — D-116-02). Do NOT use evals_completed_at here
    (that gate includes depth-15 source rows — Pitfall 4 in RESEARCH.md).
    """
    if not full_hashes:
        return {}
    result = await session.execute(
        select(GamePosition.full_hash, GamePosition.eval_cp, GamePosition.eval_mate)
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.full_hash.in_(full_hashes),
            GamePosition.ply <= _DEDUP_MAX_PLY,
            Game.full_evals_completed_at.isnot(None),
            sa.or_(GamePosition.eval_cp.isnot(None), GamePosition.eval_mate.isnot(None)),
        )
        .distinct(GamePosition.full_hash)
        .limit(len(full_hashes))
    )
    return {row[0]: (row[1], row[2]) for row in result.all()}
```

**Write pattern for ~60 row-updates** (mirrors `_apply_eval_results` at lines 321-370):
```python
# Existing pattern — per-target update(GamePosition).where().values():
stmt = update(GamePosition).where(
    GamePosition.game_id == target.game_id,
    GamePosition.ply == target.ply,
)
await session.execute(stmt.values(eval_cp=eval_cp, eval_mate=eval_mate))

# New drain: same shape but no endgame_class filter needed (PK is user_id, game_id, ply).
# D-116-03/D-116-04: overwrite legacy depth-15 evals unless game.is_analyzed
# (lichess %evals — T-78-17 preservation). Apply the is_analyzed check once per game
# before the write loop, not per-row.
```

**Completion marker pattern** (mirrors `_mark_evals_completed` at lines 402-420):
```python
# Existing (batch executemany for entry-ply drain):
async def _mark_evals_completed(session: AsyncSession, game_ids: Sequence[int]) -> None:
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == bindparam("b_id"))
        .values(evals_completed_at=now_ts)
    )
    await session.execute(stmt, [{"b_id": gid} for gid in game_ids])

# New (single-game update for full-ply drain — one game per loop iteration):
async def _mark_full_evals_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game as fully analyzed. D-116-07: mark even with eval holes."""
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(full_evals_completed_at=now_ts)
    )
    await session.execute(stmt)
```

**`run_full_eval_drain()` coroutine skeleton** (mandatory 4-step session discipline, mirrors `run_eval_drain` lines 561-665):
```python
# Mandatory session discipline from run_eval_drain() — apply verbatim:
# Step 1: short read tx -> pick ONE game -> close session
# Step 2: short read tx -> load PGN + game_positions rows -> close session
# Step 3: asyncio.gather() with NO session open  <-- CLAUDE.md hard rule
# Step 4: short write tx -> ~60 UPDATEs + full marker -> commit -> close

async def run_full_eval_drain() -> None:
    """Continuously evaluate all non-terminal plies for games with full_evals_completed_at IS NULL.

    Phase 116 EVAL-01/EVAL-02/EVAL-03/EVAL-05 / D-116-08.
    D-116-09: LIFO id-DESC interim pick (replaced by queue in Phase 117).
    D-116-10: guest filter from day one (WHERE NOT users.is_guest join).
    D-116-11: yield gate — sleep if active import OR entry-ply pending.
    """
    while True:
        try:
            # [Yield gate] D-116-11
            # [Pick 1 game] short read tx, close
            # [Load PGN + positions] short read tx, close
            # [Dedup batch lookup] short read tx, close (or inline with load session)
            # [asyncio.gather — NO session open] engine_service.evaluate_nodes per non-dedup target
            # [Write session — open LATE] UPDATEs + mark + commit
            ...
        except asyncio.CancelledError:
            raise
        except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
            logger.warning("full_eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS)
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception(exc)
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        except Exception:
            logger.exception("full_eval_drain: unexpected error — continuing")
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception()
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
```

**Yield gate helper** (new — uses existing partial indexes):
```python
# Pattern reference: _pick_pending_game_ids (lines 378-392) + existing import job queries
async def _any_active_import_or_entry_ply_pending(session: AsyncSession) -> bool:
    """True if the full drain should yield to higher-priority work (D-116-11)."""
    active_import = await session.scalar(
        select(sa.func.count())
        .select_from(ImportJob)
        .where(ImportJob.status.in_(["pending", "in_progress"]))
    )
    if active_import:
        return True
    entry_ply_pending = await session.scalar(
        select(sa.func.count())
        .select_from(Game)
        .where(Game.evals_completed_at.is_(None))
        .limit(1)
    )
    return bool(entry_ply_pending)
```

**Sentry error capture pattern** (lines 349-357 — replicate for full drain):
```python
# Existing in _apply_eval_results:
ctx: dict[str, Any] = {"game_id": target.game_id, "ply": target.ply}
sentry_sdk.set_context("eval", ctx)
sentry_sdk.set_tag("source", "eval_drain")
sentry_sdk.set_tag("eval_kind", target.eval_kind)
sentry_sdk.capture_message("cold-drain engine returned None tuple", level="warning")

# New drain: same shape, tag source="full_eval_drain"
```

---

### `app/models/game.py` — add `full_evals_completed_at` column

**Analog:** `evals_completed_at` column + `__table_args__` index (lines 147-153 + `__table_args__` lines 47-69).

**Column pattern** (insert after `evals_completed_at` at line 153):
```python
# Phase 91: entry-ply eval completion marker
evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
# Phase 116 EVAL-05: full-game (all-ply) analysis completion marker.
# Mirrors evals_completed_at exactly. NULL = pending for full-ply drain.
# Partial index ix_games_full_evals_pending WHERE NULL is in the migration.
full_evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
```

**Partial index pattern** (in `__table_args__`, mirrors `ix_games_user_evals_pending` at lines 62-68):
```python
# Existing:
Index(
    "ix_games_user_evals_pending",
    "user_id",
    postgresql_where=sa.text("evals_completed_at IS NULL"),
),
# New — on id (for LIFO drain pick), not user_id:
Index(
    "ix_games_full_evals_pending",
    "id",
    postgresql_where=sa.text("full_evals_completed_at IS NULL"),
),
```

Note: `ix_games_evals_pending` (the entry-ply analog, on `id`) is NOT in `__table_args__` — it was created in the migration only. Check whether to put the new index in `__table_args__` or migration-only to maintain consistency with the existing pattern.

---

### `app/models/game_position.py` — add cross-user dedup index

**Analog:** existing partial hash indexes at lines 56-80.

**New index pattern** (insert into `__table_args__`, after the existing partial hash indexes):
```python
# Existing user-scoped partial indexes:
Index("ix_gp_user_white_hash", "user_id", "white_hash", postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}")),
Index("ix_gp_user_black_hash", "user_id", "black_hash", postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}")),
Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san", postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}")),

# New — cross-user, no user_id column (EVAL-03 dedup lookup). ply <= 20 predicate
# matches _DEDUP_MAX_PLY constant; tighter than MAX_EXPLORER_PLY (28) intentionally.
Index(
    "ix_gp_full_hash_opening",
    "full_hash",
    postgresql_where=text("ply <= 20"),   # matches _DEDUP_MAX_PLY constant in eval_drain.py
),
```

---

### `alembic/versions/<ts>_add_full_evals_completed_at.py` — new migration

**Analog:** `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` (exact structural match).

**Migration structure pattern** (entire file from analog):
```python
"""add full_evals_completed_at to games

Phase 116 EVAL-05: full-game (all-ply) analysis completion marker. Mirrors
evals_completed_at (Phase 91) exactly: nullable TIMESTAMPTZ + partial index
WHERE NULL for the LIFO drain pick. The partial index on id (not user_id)
enables fast ORDER BY id DESC LIMIT 1 picks by the full-ply drain.

D-116-06: verified backfill — mark games where every non-terminal ply already
has eval_cp/eval_mate populated (parity evals from is_analyzed games).

Revision ID: <hash>
Revises: <previous>
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "<hash>"
down_revision: Union[str, None] = "<previous>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: nullable TIMESTAMPTZ column
    op.add_column(
        "games",
        sa.Column("full_evals_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Step 2: partial index for drain pick (matches ix_games_evals_pending pattern)
    op.create_index(
        "ix_games_full_evals_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where="full_evals_completed_at IS NULL",
    )
    # Step 3: new dedup index on game_positions (EVAL-03)
    op.create_index(
        "ix_gp_full_hash_opening",
        "game_positions",
        ["full_hash"],
        unique=False,
        postgresql_where="ply <= 20",
    )
    # Step 4: D-116-06 verified backfill. See Pitfall 6 in RESEARCH.md.
    # If this times out on prod, split into DDL-only migration + post-deploy script.
    op.execute("""
        UPDATE games g
        SET full_evals_completed_at = COALESCE(g.imported_at, NOW())
        WHERE g.full_evals_completed_at IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM game_positions gp
              WHERE gp.game_id = g.id
                AND gp.eval_cp IS NULL
                AND gp.eval_mate IS NULL
          )
    """)


def downgrade() -> None:
    op.drop_index("ix_gp_full_hash_opening", table_name="game_positions", postgresql_where="ply <= 20")
    op.drop_index("ix_games_full_evals_pending", table_name="games", postgresql_where="full_evals_completed_at IS NULL")
    op.drop_column("games", "full_evals_completed_at")
```

---

### `app/main.py` — wire `run_full_eval_drain()` in lifespan

**Analog:** `drain_task = asyncio.create_task(run_eval_drain(), ...)` at lines 77-99.

**Wiring pattern** (lines 77-99 — add full_drain_task alongside drain_task):
```python
# Existing:
drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")

# New — add immediately after:
from app.services.eval_drain import run_eval_drain, run_full_eval_drain
full_drain_task = asyncio.create_task(run_full_eval_drain(), name="full-eval-drain")

# In finally block — cancel + await pattern mirrors drain_task exactly:
full_drain_task.cancel()
try:
    await full_drain_task
except asyncio.CancelledError:
    pass
except Exception:
    logger.exception("Full eval drain task raised on shutdown")
```

---

## Shared Patterns

### Session Discipline (CLAUDE.md hard rule — applies to ALL new coroutine code)
**Source:** `app/services/eval_drain.py` module docstring (lines 1-34) + `run_eval_drain()` steps (lines 580-625)
**Apply to:** `run_full_eval_drain()` in eval_drain.py
```python
# Session discipline per tick — MANDATORY for full drain:
# 1. Pick game: short read tx -> close
# 2. Load PGN + positions: short read tx -> close
# 3. Dedup lookup: short read tx -> close (or combined with step 2)
# 4. asyncio.gather(evaluate_nodes(...) for each target)  <-- NO session open here
# 5. Write session: open LATE, all UPDATEs + marker commit -> close
```

### Sentry Capture Pattern (no variables in messages)
**Source:** `app/services/eval_drain.py` lines 349-357
**Apply to:** all `except` blocks in new coroutine and helpers
```python
sentry_sdk.set_context("eval", {"game_id": target.game_id, "ply": target.ply})
sentry_sdk.set_tag("source", "full_eval_drain")
sentry_sdk.capture_message("...", level="warning")  # no f-strings in message
```

### DB Outage Retry Loop
**Source:** `app/services/eval_drain.py` lines 649-665
**Apply to:** `run_full_eval_drain()` outer exception handlers — copy `_RETRIABLE_DB_OUTAGE_ERRORS` tuple verbatim.

### `update(GamePosition)` Write Pattern
**Source:** `app/services/eval_drain.py` lines 362-369
**Apply to:** per-ply UPDATE in `run_full_eval_drain()` write session
```python
stmt = update(GamePosition).where(
    GamePosition.game_id == target.game_id,
    GamePosition.ply == target.ply,
)
await session.execute(stmt.values(eval_cp=eval_cp, eval_mate=eval_mate))
# No endgame_class filter for full-ply drain (PK (user_id, game_id, ply) is unique per ply)
```

### `Game.__table__` + `bindparam` executemany
**Source:** `app/services/eval_drain.py` lines 413-420
**Apply to:** `_mark_full_evals_completed()` — use single `update(games_table).where(games_table.c.id == game_id)` (no batch; one game per tick)

---

## No Analog Found

All files have close analogs. No new-pattern territory.

| File | Role | Note |
|------|------|-------|
| `_fetch_dedup_evals()` helper | utility | No existing cross-user hash batch-lookup; pattern derived from `_collect_eval_targets_from_db` session style |

---

## Critical Constraints for Planner

1. **`evaluate_nodes()` must NOT pass `multipv` to `analyse()`** — Phase 116 skips PV capture (EVAL-04 is Phase 117). Scalar `InfoDict` returned; existing `_score_to_cp_mate(info)` works unchanged.
2. **Dedup must join `full_evals_completed_at IS NOT NULL`**, NOT `evals_completed_at IS NOT NULL` — Pitfall 4 in RESEARCH.md.
3. **D-116-04 overwrite gate**: check `game.is_analyzed` once per game before the write loop; if True, skip rows where `eval_cp IS NOT NULL OR eval_mate IS NOT NULL` (T-78-17 preservation).
4. **Backfill contingency (A2 in RESEARCH.md)**: planner should include a wave-gate checkpoint — run `EXPLAIN (ANALYZE, BUFFERS)` on the backfill SQL against dev DB before committing to in-migration execution. If cost is too high, split into DDL-only migration + `scripts/backfill_full_evals.py`.
5. **`ix_games_evals_pending` is migration-only** (not in `Game.__table_args__`). Verify whether the new `ix_games_full_evals_pending` should follow the same convention or go in `__table_args__`. Keep consistent with the existing pattern.
6. **CLAUDE.md stale comment update**: correct the "STOCKFISH_POOL_SIZE lowered" note in engine.py (lines 100-105) to reflect current prod pool size 6, and document the Phase 116 memory accounting (D-116-12).

## Metadata

**Analog search scope:** `app/services/`, `app/models/`, `alembic/versions/`, `app/main.py`
**Files scanned:** 6
**Pattern extraction date:** 2026-06-12
