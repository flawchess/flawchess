# Phase 78: Stockfish-Eval Cutover for Endgame Classification — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/engine.py` | service (NEW) | request-response | `app/services/zobrist.py` (module-level globals, eval sign convention) + `app/main.py` (lifespan pattern) | role-match |
| `app/main.py` | config (MODIFY) | request-response | `app/main.py` itself — lifespan `@asynccontextmanager` block (lines 44-52) | exact |
| `app/services/zobrist.py` | service (MODIFY) | transform | `app/services/zobrist.py` lines 183-204 — endgame_class detection and eval write | exact |
| `app/services/import_service.py` | service (MODIFY) | batch | `app/services/import_service.py` `_flush_batch` (lines 399-506) | exact |
| `app/repositories/endgame_repository.py` | repository (MODIFY) | CRUD | `app/repositories/endgame_repository.py` lines 145-260 — `query_endgame_entry_rows` current span_subq | exact |
| `app/services/endgame_service.py` | service (MODIFY) | transform | `app/services/endgame_service.py` lines 176-266 — `_aggregate_endgame_stats` | exact |
| `app/models/game_position.py` | model (MODIFY) | config | `app/models/game_position.py` lines 26-31 — `ix_gp_user_endgame_game` Index definition | exact |
| `alembic/versions/<rev>_reshape_ix_gp_user_endgame_game.py` | migration (NEW) | batch | `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` | exact |
| `scripts/backfill_eval.py` | utility (NEW) | batch | `scripts/reclassify_positions.py` | role-match |
| `tests/services/test_engine.py` | test (NEW) | request-response | `tests/test_zobrist.py` (fixture + pure-function unit test pattern) | role-match |
| `tests/test_endgame_repository.py` | test (MODIFY) | CRUD | `tests/test_endgame_repository.py` itself — `_seed_game_position` + `TestQueryEndgameEntryRows` | exact |
| `tests/test_endgame_service.py` | test (MODIFY) | transform | `tests/test_endgame_service.py` itself — `_FakeRow` NamedTuple + classification tests | exact |

---

## Pattern Assignments

### `app/services/engine.py` (service, NEW)

**Analogs:** `app/services/zobrist.py` (eval sign convention and module-level constants) + `app/main.py` (lifespan hook target)

**Imports pattern** — copy from `app/services/zobrist.py` lines 1-24 and `app/main.py` lines 1-20; adapt:
```python
import asyncio
import os

import chess
import chess.engine
import sentry_sdk

from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS
```
The project convention is to import project constants from their canonical module rather than redeclaring them. `EVAL_CP_MAX_ABS` and `EVAL_MATE_MAX_ABS` already live in `app/services/zobrist.py` lines 111-112. The engine wrapper imports from there to share the clamp bounds rather than duplicating them.

**Module-level globals pattern** — `app/services/zobrist.py` uses module-level constants with underscore-prefixed private names. Replicate for the engine state:
```python
# app/services/zobrist.py lines 111-112 (clamp bounds — import don't copy)
EVAL_CP_MAX_ABS = 10000  # ±100 pawns
EVAL_MATE_MAX_ABS = 200  # no realistic mate-in-N exceeds this

# Engine wrapper follows the same naming convention:
_STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "/usr/local/bin/stockfish")
_HASH_MB = 64
_THREADS = 1
_DEPTH = 15
_TIMEOUT_S = 2.0

_transport: asyncio.SubprocessTransport | None = None
_protocol: chess.engine.UciProtocol | None = None
_lock = asyncio.Lock()
```

**Eval sign convention** — `app/services/zobrist.py` lines 183-197 (the canonical white-perspective pattern the wrapper must match byte-for-byte):
```python
# zobrist.py lines 183-197
pov = node.eval()
if pov is not None:
    w = pov.white()
    eval_cp = w.score(mate_score=None)
    eval_mate = w.mate()
    if eval_cp is not None:
        eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
    if eval_mate is not None:
        eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))
```
The wrapper's `evaluate()` function must apply `pov_score.white()`, then `.score(mate_score=None)` and `.mate()`, then the same clamp logic. The clamp uses the same `EVAL_CP_MAX_ABS` / `EVAL_MATE_MAX_ABS` constants imported from `zobrist.py`.

**Return type and error handling** — D-04/D-05: return `tuple[int | None, int | None]`; on `asyncio.TimeoutError` or `chess.engine.EngineError`/`EngineTerminatedError` restart the engine and return `(None, None)`. The import path's D-11 handling (`sentry_sdk.capture_exception`) lives at the call site, not inside the wrapper.

**What to change vs. the analogs:** The engine wrapper does NOT exist yet. The RESEARCH.md section "Wrapper Implementation Pattern" (lines 144-228 of RESEARCH.md) provides the full target implementation — use that as the primary source. The analog files supply the conventions (imports style, clamp bounds source, type annotations).

---

### `app/main.py` (config, MODIFY)

**Analog:** `app/main.py` lines 44-52 — the existing lifespan handler

**Existing lifespan pattern** (lines 44-52):
```python
# app/main.py lines 44-52
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # D-22: validate insights Agent FIRST — startup failure is a deploy-blocker.
    # Orphan cleanup is best-effort and must not run if the app can't serve
    # the insights endpoint.
    get_insights_agent()
    await cleanup_orphaned_jobs()
    yield
```

**Target pattern** — add engine start/stop around the `yield`:
```python
# New import to add at top of file:
from app.services.engine import start_engine, stop_engine

# Modified lifespan (D-02):
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()
    await cleanup_orphaned_jobs()
    await start_engine()          # NEW — must come after existing startup steps
    try:
        yield
    finally:
        await stop_engine()       # NEW — guaranteed cleanup
```

**What to replicate:** The `try/finally` pattern around `yield` for guaranteed shutdown. The engine start comes AFTER `get_insights_agent()` and `cleanup_orphaned_jobs()` so a Stockfish startup failure does not suppress existing deploy-blocker validation. The `try/finally` is the key addition — the bare `yield` in the existing code does not guarantee cleanup on exceptions.

**What to change:** Only the lifespan body — everything else in `main.py` stays unchanged.

---

### `app/services/zobrist.py` (service, MODIFY)

**Analog:** `app/services/zobrist.py` lines 199-226 — the endgame_class detection block and the `PlyData` dict construction that follows

**Existing endgame detection block** (lines 199-226):
```python
# zobrist.py lines 199-226
# Compute endgame_class for endgame positions (piece_count <= threshold)
endgame_class: int | None = None
if classification.piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD:
    ec_str = classify_endgame_class(classification.material_signature)
    endgame_class = _CLASS_TO_INT[ec_str]

# 6. Advance board to next ply
board.push(node.move)

plies.append(
    PlyData(
        ply=ply,
        ...
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        ...
        endgame_class=endgame_class,
    )
)
```

**Insertion point for IMP-01:** After `endgame_class = _CLASS_TO_INT[ec_str]` is set (line ~203), BEFORE `board.push(node.move)`, the engine call goes here — but only for span-entry plies. The planner must design span-entry detection in-loop: track the first ply seen per `endgame_class` and count plies per class. When the loop ends, evaluate span-entry plies whose `eval_cp` and `eval_mate` are both None. Because this is a single sequential PGN walk, the board state must be captured before `board.push()`.

**Sentry error pattern from `zobrist.py`** (lines 157-160):
```python
# zobrist.py lines 157-160 — exception capture pattern in the same module
try:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
except Exception:
    sentry_sdk.capture_exception()
    return None
```
D-11's import-time error handling follows this: `sentry_sdk.set_context("eval", {...})` then `sentry_sdk.capture_exception(exc)` then `continue`.

**What to replicate:** The in-loop board-state-before-push semantics and the `endgame_class` detection block. The engine call slots in after `endgame_class` is set and before `board.push()`. The `PlyData` TypedDict already carries `eval_cp` and `eval_mate` — no schema change needed.

**What to change:** The function becomes `async def process_game_pgn(...)` if it is not already (check current signature). The engine handle must be passed in or imported from the module-level global in `engine.py`. The RESEARCH.md "Import-Path Integration" section (lines 454-518) contains the full call-site design.

---

### `app/services/import_service.py` (service, MODIFY)

**Analog:** `app/services/import_service.py` lines 399-506 — `_flush_batch` function

**Engine dependency injection pattern** — the file already imports `process_game_pgn` from `zobrist.py` (line 28). The engine wrapper follows the same import pattern:
```python
# import_service.py line 28 (existing)
from app.services.zobrist import process_game_pgn

# Add alongside it:
from app.services import engine as engine_service
```

**Bulk insert then UPDATE pattern** (lines 488-505):
```python
# import_service.py lines 488-505
# 5. Bulk insert positions
if position_rows:
    await game_repository.bulk_insert_positions(session, position_rows)

# 6. Bulk UPDATE move_count / result_fen
if move_counts:
    ...
    await session.execute(update(Game)...)

await session.commit()
```
The new eval UPDATE step (IMP-01) must come BETWEEN step 5 (bulk insert positions) and the final `session.commit()` at line 505. It uses `sa_update(GamePosition).where(...).values(eval_cp=..., eval_mate=...)` — the same `sa_update` import pattern already present.

**Sentry context pattern** (lines 452-455):
```python
# import_service.py lines 452-455
sentry_sdk.set_context("import", {"game_id": game_id})
sentry_sdk.capture_exception()
```
D-11 extends this with eval-specific context: `sentry_sdk.set_context("eval", {"game_id": game_id, "ply": span_entry_ply, "endgame_class": ec})`.

**What to replicate:** The sequential UPDATE pattern within the existing session (no new session), the `sa_update(GamePosition).where(...).values(...)` idiom, and the Sentry capture pattern. No `asyncio.gather` — CLAUDE.md critical constraint.

**What to change:** Insert a new step 6a (eval UPDATE) between step 5 (positions inserted) and the final commit. The RESEARCH.md "Option A call site" (lines 480-513) gives the exact implementation.

---

### `app/repositories/endgame_repository.py` (repository, MODIFY)

**Analog:** `app/repositories/endgame_repository.py` lines 145-260 — `query_endgame_entry_rows` (the current span_subq + main query shape)

**Current span_subq pattern** (lines 181-222) — the part being replaced:
```python
# endgame_repository.py lines 181-222 — THIS PATTERN IS DELETED
entry_imbalance_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]

raw_imbalance_after = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[PERSISTENCE_PLIES + 1]

ply_at_persistence = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[PERSISTENCE_PLIES + 1]

imbalance_after_persistence_agg = case(
    (ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES, raw_imbalance_after),
    else_=None,
)

span_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        GamePosition.endgame_class.label("endgame_class"),
        entry_imbalance_agg.label("entry_imbalance"),
        imbalance_after_persistence_agg.label("entry_imbalance_after"),
    )
    .where(GamePosition.user_id == user_id, GamePosition.endgame_class.isnot(None))
    .group_by(GamePosition.game_id, GamePosition.endgame_class)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("span")
)
```

**Target pattern** — same `type_coerce` + `ARRAY(SmallIntegerType)[1]` idiom, applied to `eval_cp` and `eval_mate` instead of `material_imbalance`. The `PERSISTENCE_PLIES` array_agg and the contiguity `case` expression are deleted entirely. The `color_sign` case expression (lines 226-229) and the main query join structure (lines 231-257) remain structurally identical — only the projected column names change from `user_material_imbalance` / `user_material_imbalance_after` to `eval_cp` / `eval_mate` (white-perspective from DB, sign flip moves to service layer per RESEARCH.md recommendation).

**Color sign and main query join** (lines 226-257 — shape to KEEP):
```python
# endgame_repository.py lines 226-257 — structure is preserved, column names change
color_sign = case(
    (Game.user_color == "white", 1),
    else_=-1,
)

stmt = (
    select(
        Game.id.label("game_id"),
        span_subq.c.endgame_class,
        Game.result,
        Game.user_color,
        (span_subq.c.entry_imbalance * color_sign).label("user_material_imbalance"),
        (span_subq.c.entry_imbalance_after * color_sign).label("user_material_imbalance_after"),
    )
    .join(span_subq, Game.id == span_subq.c.game_id)
    .where(Game.user_id == user_id)
)
```
The RESEARCH.md recommends projecting raw `eval_cp` / `eval_mate` (white-perspective) and applying the color flip in the service layer. If the planner chooses that approach, the `color_sign` multiplication moves out of the query; if it stays in SQL the labels change to `user_eval_cp` / `user_eval_mate`. Either is acceptable — the planner picks one and applies it consistently to all three queries.

**What to replicate:** The `type_coerce(func.array_agg(aggregate_order_by(...)), ARRAY(SmallIntegerType))[1]` idiom exactly — this is the proven index-only-scan pattern. Apply it to `eval_cp` and `eval_mate` instead of `material_imbalance`.

**What to delete:** `PERSISTENCE_PLIES` constant (line 71), the `raw_imbalance_after` array_agg, the `ply_at_persistence` array_agg, the `imbalance_after_persistence_agg` case expression, and the `entry_imbalance_after` label from the span_subq. Repeated across three queries (lines 181-220, 310-340, 849-870 approximately).

---

### `app/services/endgame_service.py` (service, MODIFY)

**Analog:** `app/services/endgame_service.py` lines 176-266 — `_aggregate_endgame_stats` (the primary classification loop)

**Current classification pattern** (lines 209-266):
```python
# endgame_service.py lines 209-266
for (
    _game_id,
    endgame_class_int,
    result,
    user_color,
    user_material_imbalance,
    user_material_imbalance_after,
) in rows:
    ...
    # Conversion check (lines 240-248):
    if (
        user_material_imbalance is not None
        and user_material_imbalance >= _MATERIAL_ADVANTAGE_THRESHOLD
        and user_material_imbalance_after is not None
        and user_material_imbalance_after >= _MATERIAL_ADVANTAGE_THRESHOLD
    ):
        conv[endgame_class]["games"] += 1
        ...
    # Recovery check (lines 250-266):
    if (
        user_material_imbalance is not None
        and user_material_imbalance <= -_MATERIAL_ADVANTAGE_THRESHOLD
        and user_material_imbalance_after is not None
        and user_material_imbalance_after <= -_MATERIAL_ADVANTAGE_THRESHOLD
    ):
        recov[endgame_class]["games"] += 1
        ...
```

**Target pattern** — replace the tuple destructuring column names and the double-threshold check with a call to a new `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` helper. The loop structure, accumulator dicts, and `derive_user_result` call all stay the same. The Sentry context block (lines 220-228) stays unchanged.

**`_MATERIAL_ADVANTAGE_THRESHOLD` deletion** — this constant is defined at line 164 of `endgame_service.py`. Replace it with `EVAL_ADVANTAGE_THRESHOLD = 100` (same numeric value, new name). The new constant lives in `endgame_service.py` (same file, same line area) so callers change minimally.

**New helper location** — add `_classify_endgame_bucket` above `_aggregate_endgame_stats` in the file. It is pure Python (no DB), so tests can import and call it directly without a DB fixture. See RESEARCH.md lines 606-636 for the full target implementation.

**What to replicate:** The tuple-unpack-then-accumulate loop pattern (it avoids `ty` attribute errors on Row objects). The `sentry_sdk.set_context` + `capture_exception` pattern for unexpected class ints.

**What to change:** The tuple field names in the destructuring (`user_material_imbalance`, `user_material_imbalance_after` → `eval_cp`, `eval_mate`), the double-threshold condition (replaced by single helper call), and the constant name. Apply the same changes to `_compute_score_gap_material` and `_endgame_skill_from_bucket_rows` in the same file (RESEARCH.md Deletion Checklist, lines 643-653).

---

### `app/models/game_position.py` (model, MODIFY)

**Analog:** `app/models/game_position.py` lines 22-51 — existing `__table_args__` Index definitions

**Existing `ix_gp_user_endgame_game` definition** (lines 26-31):
```python
# game_position.py lines 26-31
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["material_imbalance"],
),
```

**Target definition** — change only `postgresql_include`:
```python
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["eval_cp", "eval_mate"],
),
```

**What to replicate:** The surrounding comment block (lines 22-25) should be updated to reflect that INCLUDE now covers eval columns for index-only scans of `array_agg(eval_cp ORDER BY ply)` and `array_agg(eval_mate ORDER BY ply)`.

**What to change:** Only the `postgresql_include` list and the comment. The index key columns (`user_id`, `game_id`, `endgame_class`, `ply`) and the WHERE predicate stay identical. The actual schema change happens via Alembic migration — this model change keeps SQLAlchemy's in-memory representation in sync.

---

### `alembic/versions/<rev>_reshape_ix_gp_user_endgame_game.py` (migration, NEW)

**Analog:** `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` — the migration that originally created `ix_gp_user_endgame_game` with `postgresql_include=["material_imbalance"]`

**Full analog file** (lines 1-39):
```python
# befacc0fce23 — the pattern to replicate
revision: str = 'befacc0fce23'
down_revision: Union[str, Sequence[str], None] = 'b7198d53627c'
...

def upgrade() -> None:
    op.create_index(
        'ix_gp_user_endgame_game',
        'game_positions',
        ['user_id', 'game_id', 'endgame_class', 'ply'],
        unique=False,
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
        postgresql_include=['material_imbalance'],
    )

def downgrade() -> None:
    op.drop_index('ix_gp_user_endgame_game', table_name='game_positions',
                  postgresql_where=sa.text('endgame_class IS NOT NULL'))
```

**Target pattern** — drop then recreate in `upgrade()`, recreate then drop in `downgrade()`:
```python
def upgrade() -> None:
    op.drop_index(
        'ix_gp_user_endgame_game',
        table_name='game_positions',
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
    )
    op.create_index(
        'ix_gp_user_endgame_game',
        'game_positions',
        ['user_id', 'game_id', 'endgame_class', 'ply'],
        unique=False,
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
        postgresql_include=['eval_cp', 'eval_mate'],
    )

def downgrade() -> None:
    op.drop_index(
        'ix_gp_user_endgame_game',
        table_name='game_positions',
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
    )
    op.create_index(
        'ix_gp_user_endgame_game',
        'game_positions',
        ['user_id', 'game_id', 'endgame_class', 'ply'],
        unique=False,
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
        postgresql_include=['material_imbalance'],
    )
```

**Second analog:** `alembic/versions/20260427_125405_4be323b0e0fd_drop_redundant_ix_gp_user_full_hash_and_.py` — shows the `op.drop_index` pattern with `postgresql_where` string (not `sa.text()`). Either form works; use `sa.text()` to match the original creation (befacc0fce23).

**What to replicate:** The file header boilerplate (revision, down_revision, branch_labels, depends_on typed as `Union[str, Sequence[str], None]`), the docstring comment explaining what the migration does, and the symmetric upgrade/downgrade structure.

**What to change:** `down_revision` must point to the latest current revision (run `uv run alembic current` to get it), and `postgresql_include` changes from `['material_imbalance']` to `['eval_cp', 'eval_mate']`.

---

### `scripts/backfill_eval.py` (utility, NEW)

**Analog:** `scripts/reclassify_positions.py` — full file (297 lines)

**Module docstring pattern** (lines 1-19):
```python
# reclassify_positions.py lines 1-19
"""Reclassify existing game_positions rows with latest position metadata.
...
Usage (local dev):
    uv run python scripts/reclassify_positions.py --all --yes
    uv run python scripts/reclassify_positions.py --user-id 42

Usage (production):
    The runtime image has no `uv` on the host — run inside the backend
    container using the venv's Python directly:
        ssh flawchess "cd /opt/flawchess && docker compose exec backend /app/.venv/bin/python scripts/..."
"""
```
Copy this docstring skeleton, adapting the usage section to include the three-round runbook (dev → benchmark → prod) per D-07 and the `--db {dev|benchmark|prod}` CLI shape per D-08.

**sys.path bootstrap pattern** (lines 29-30):
```python
# reclassify_positions.py lines 29-30
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
Copy verbatim — required so `app.*` imports work when running as a standalone script.

**`_log` utility** (lines 57-61):
```python
# reclassify_positions.py lines 57-61
def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
```
Copy verbatim.

**CLI arg parser skeleton** (lines 63-87):
```python
# reclassify_positions.py lines 63-87
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(...)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", type=int, ...)
    group.add_argument("--all", action="store_true", dest="all_users", ...)
    parser.add_argument("--yes", "-y", action="store_true", ...)
    return parser.parse_args()
```
Adapt: add `--db {dev|benchmark|prod}` (required, not mutually exclusive), `--dry-run` (count without writing), `--limit <int>` (cap rows for testing), `--user-id <int>` (optional, not required). Drop `--all` (default = all users when `--user-id` absent).

**Batch commit loop pattern** (lines 232-274):
```python
# reclassify_positions.py lines 232-274
while True:
    async with async_session_maker() as session:
        game_ids = await get_unprocessed_game_ids(...)
        if not game_ids:
            break
        ...
        for game_id, pgn in id_pgn_pairs:
            try:
                positions = await backfill_game(session, game_id, pgn)
            except Exception as e:
                sentry_sdk.capture_exception(e)
                ...
                continue
        await session.commit()
```
The backfill script's inner loop differs: it iterates rows (not games), calls `engine.evaluate(board)`, and issues `sa_update(GamePosition).where(GamePosition.id == row.id).values(...)`. COMMIT every 100 evals (D-09) rather than per game-batch. Use `i % EVAL_BATCH_SIZE == 0` to gate commits.

**VACUUM ANALYZE pattern** (lines 179-188):
```python
# reclassify_positions.py lines 179-188
async def run_vacuum() -> None:
    """Run VACUUM ANALYZE on game_positions outside a transaction.
    VACUUM cannot run inside a transaction block — use AUTOCOMMIT isolation.
    """
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("VACUUM ANALYZE game_positions"))
```
Copy verbatim — the backfill script should call this after completion (per RESEARCH.md open question #4).

**Sentry init pattern** (lines 193-195):
```python
# reclassify_positions.py lines 193-195
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
```
Copy verbatim.

**`async_session_maker` usage** — `reclassify_positions.py` imports `async_session_maker` from `app.core.database` (line 39). The backfill script needs a dynamic session maker per `--db` target. The RESEARCH.md "DB Target Selection" pattern (lines 439-449) shows how to build a per-target `async_session_maker` from a constructed URL. The script reads credentials from `app.core.config.settings` (env vars) and computes the URL from the `--db` flag.

**What to replicate:** The entire structural skeleton (docstring, sys.path bootstrap, `_log`, arg parser, Sentry init, count query, confirmation prompt, loop, VACUUM, summary log, `if __name__ == "__main__": asyncio.run(main())`).

**What to change:** The inner loop body (span-entry SELECT instead of game-level NULL check, engine call instead of PGN replay, UPDATE by row.id instead of UPDATE by ply range), the CLI shape (D-08), and the DB target selection (D-07/D-09). Engine start/stop lives in `main()` — the backfill script is standalone, not a FastAPI app, so it calls `start_engine()` / `stop_engine()` directly rather than relying on the lifespan handler.

---

### `tests/services/test_engine.py` (test, NEW)

**Analogs:** `tests/test_zobrist.py` (pure unit test pattern, board fixtures) + `tests/test_endgame_service.py` lines 65-80 (class-based unit tests with no DB)

**Fixture pattern** (`tests/test_zobrist.py` lines 28-48):
```python
# test_zobrist.py lines 28-48
@pytest.fixture
def board_after_e4():
    b = chess.Board()
    b.push_san("e4")
    return b
```
The engine tests use board fixtures constructed from FEN strings rather than push sequences (faster, more deterministic for endgame positions).

**skipif pattern** (from RESEARCH.md test strategy, lines 761-766 — no codebase analog, but follows CLAUDE.md `ty` compliance style):
```python
import shutil
stockfish_missing = shutil.which("stockfish") is None
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish not on PATH")
```

**Class-based async test pattern** (`tests/test_endgame_service.py` lines 65-80):
```python
# test_endgame_service.py lines 65-80
class TestClassifyEndgameClass:
    def test_rook_endgame(self):
        assert classify_endgame_class("KR_KR") == "rook"
```
The engine tests extend this with `@pytest.mark.asyncio` (since pytest-asyncio is configured with `asyncio_mode = "auto"` in `pyproject.toml`) and a `scope="class"` fixture for engine start/stop.

**What to replicate:** Module-level `skip_if_no_stockfish` mark, class-scoped `engine_started` fixture that calls `start_engine()` / `stop_engine()`, individual `async def test_*` methods (no DB fixtures needed).

**What to change:** This is a new file; the test structure follows the RESEARCH.md "ENG-02 Engine Wrapper Unit Tests" section (lines 791-819) for the full set of known-position tests.

---

### `tests/test_endgame_repository.py` (test, MODIFY)

**Analog:** `tests/test_endgame_repository.py` itself — the `_seed_game_position` helper (lines 95-128) and `TestQueryEndgameEntryRows` tests (lines 136-230)

**`_seed_game_position` pattern** (lines 95-128):
```python
# test_endgame_repository.py lines 95-128
async def _seed_game_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    piece_count: int = 2,
    material_count: int = 1000,
    material_signature: str = "KR_KR",
    material_imbalance: int = 0,
    endgame_class: int | None = 1,
) -> GamePosition:
    pos = GamePosition(
        game_id=game.id,
        ...
        material_imbalance=material_imbalance,
        endgame_class=endgame_class,
    )
    session.add(pos)
    await session.flush()
    return pos
```

**What to change:** Add `eval_cp: int | None = None, eval_mate: int | None = None` parameters to `_seed_game_position`. Tests for conversion/recovery must seed `eval_cp` / `eval_mate` values instead of `material_imbalance`. Tests that assert on row tuple shape must update the destructuring from `(game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after)` to the new column names.

**Row assertion pattern** (lines 199-209):
```python
# test_endgame_repository.py lines 199-209 — pattern to update
(
    game_id,
    endgame_class,
    result,
    user_color,
    user_material_imbalance,       # → eval_cp (or user_eval_cp)
    user_material_imbalance_after,  # → eval_mate (or user_eval_mate, deleted if no persistence)
) = rows[0]
```

---

### `tests/test_endgame_service.py` (test, MODIFY)

**Analog:** `tests/test_endgame_service.py` lines 48-63 — `_FakeRow` NamedTuple

**`_FakeRow` pattern** (lines 48-63):
```python
# test_endgame_service.py lines 48-63
class _FakeRow(NamedTuple):
    """Lightweight stand-in for a SQLAlchemy Row used by endgame service tests."""
    game_id: int
    endgame_class: int
    result: str
    user_color: str
    user_material_imbalance: Any
    user_material_imbalance_after: Any
```

**What to change:** Update `_FakeRow` field names to `eval_cp` and `eval_mate` (dropping `user_material_imbalance_after`). Add tests for the new `_classify_endgame_bucket` helper (pure Python, no DB) following the `TestClassifyEndgameClass` pattern (lines 65-80). The RESEARCH.md test cases (lines 826-850) list the required test scenarios.

---

## Shared Patterns

### Sentry error capture
**Source:** `app/services/import_service.py` lines 452-455 + `app/services/zobrist.py` lines 157-160
**Apply to:** `app/services/engine.py` (import-time error capture), `scripts/backfill_eval.py` (row-level error handling)
```python
sentry_sdk.set_context("eval", {
    "game_id": game_id,
    "ply": span_entry_ply,
    "endgame_class": ec,
})
sentry_sdk.set_tag("source", "import")
sentry_sdk.capture_exception(exc)
```
The wrapper itself does NOT call Sentry on timeout/crash — it restarts and returns `(None, None)`. Sentry capture is the call site's responsibility (import path per D-11, backfill script logs and skips).

### Eval sign convention (white-perspective)
**Source:** `app/services/zobrist.py` lines 183-197
**Apply to:** `app/services/engine.py` `evaluate()` function — the `pov.white().score(mate_score=None)` / `.mate()` / clamp pattern must be byte-for-byte identical.

### VACUUM ANALYZE after bulk write
**Source:** `scripts/reclassify_positions.py` lines 179-188
**Apply to:** `scripts/backfill_eval.py` — call after the full backfill loop completes, using the same AUTOCOMMIT pattern.

### Sequential DB updates (no asyncio.gather)
**Source:** CLAUDE.md critical constraint + `scripts/reclassify_positions.py` lines 232-274
**Apply to:** `scripts/backfill_eval.py` and `app/services/import_service.py` eval step — all DB writes on the same `AsyncSession` are sequential.

### Commit-every-N batch pattern
**Source:** `scripts/reclassify_positions.py` lines 273-274 (`await session.commit()` inside the while loop)
**Apply to:** `scripts/backfill_eval.py` — commit every 100 evals (`EVAL_BATCH_SIZE = 100`) rather than per game. The `(i + 1) % EVAL_BATCH_SIZE == 0` gate is from RESEARCH.md lines 430-432.

### ty compliance — tuple unpacking over attribute access
**Source:** `app/services/endgame_service.py` lines 209-216 (existing tuple destructuring in `_aggregate_endgame_stats`)
**Apply to:** All service functions consuming the new row shape — use tuple unpacking `for (game_id, ec, result, user_color, eval_cp, eval_mate) in rows` rather than `row.eval_cp` attribute access to avoid `ty: ignore[unresolved-attribute]` suppression.

---

## No Analog Found

No files in this phase lack a close codebase analog. All patterns have direct precedents.

| File | Role | Data Flow | Note |
|---|---|---|---|
| `app/services/engine.py` | service | request-response | Closest analogs are `zobrist.py` (eval convention) + lifespan in `main.py`. No existing async engine wrapper to copy from — RESEARCH.md "Wrapper Implementation Pattern" (lines 144-228) provides the target implementation. |

---

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/models/`, `app/main.py`, `scripts/`, `tests/`, `alembic/versions/`
**Files scanned:** 15 source files read directly; 12 file entries matched to analogs
**Pattern extraction date:** 2026-05-02
