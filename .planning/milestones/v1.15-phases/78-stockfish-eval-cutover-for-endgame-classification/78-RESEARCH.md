# Phase 78: Stockfish-Eval Cutover for Endgame Classification — Research

**Researched:** 2026-05-02
**Domain:** python-chess async engine API, Stockfish Docker install, SQLAlchemy 2.x async UPDATE, Alembic partial-index reshaping, FastAPI lifespan, Sentry error capture
**Confidence:** HIGH (all major claims verified against codebase or official API source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Single shared UCI process per backend worker, asyncio.Lock serialization.
- **D-02:** Engine lifecycle in FastAPI lifespan handler (startup/shutdown in `app/main.py`).
- **D-03:** Stockfish UCI options: `Hash=64 MB`, `Threads=1` (single source of truth in wrapper).
- **D-04:** Wrapper API: `async def evaluate(board: chess.Board) -> tuple[int | None, int | None]` returning `(eval_cp, eval_mate)` in white-perspective. Sign flip at read time, not write time.
- **D-05:** Per-eval `asyncio.wait_for(..., timeout=2.0)`. On timeout, restart engine before next eval.
- **D-06:** Pinned official Stockfish Linux binary (`stockfish-ubuntu-x86-64-avx2`) from GitHub releases at a pinned tag (e.g. `sf_17`), installed to `/usr/local/bin/stockfish`. Read from env var `STOCKFISH_PATH` with that default.
- **D-07:** Backfill from operator's local machine in three rounds: dev → benchmark → prod, before phase merge/deploy.
- **D-08:** Script CLI: `--db {dev|benchmark|prod}`, `--user-id <int>` (optional), `--dry-run`, `--limit <int>`.
- **D-09:** Sequential, single engine, COMMIT every 100 evals. Resume via `SELECT WHERE eval_cp IS NULL AND eval_mate IS NULL` over span-entry rows.
- **D-10:** No cross-row hash dedup. Row-level idempotency only.
- **D-11:** Engine error/timeout during import: skip row, Sentry capture with context (`game_id`, `ply`, `endgame_class`), continue.
- **D-12:** `ix_gp_user_endgame_game` migrated to `INCLUDE(eval_cp, eval_mate)` only (drop `material_imbalance` from INCLUDE).

### SPEC Drift

**FILL-02 hash-dedup relaxed:** SPEC says backfill dedupes by `full_hash`. Operator decision (D-10) overrides: row-level idempotency only (`eval_cp IS NULL AND eval_mate IS NULL` check). PLAN.md must explicitly acknowledge this drift.

### Deferred Ideas (OUT OF SCOPE)

- Backfill progress reporting / ETA dashboard (nice-to-have, not blocking)
- Wrapper return-type richness beyond `(eval_cp, eval_mate)` tuple
- Per-class threshold tuning, parity validation, rating-stratified offset analysis (SEED-002 / SEED-006)
- Eval coverage for opening / middlegame positions (SEED-010)
- Bumping INCLUDE of `ix_gp_user_endgame_game` speculatively

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENG-01 | Stockfish in backend image, long-lived UCI process | D-01/D-02/D-06; verified `chess.engine.popen_uci()` is native async; wrapper pattern documented below |
| ENG-02 | Async-friendly engine wrapper, depth 15, white-perspective | `chess.engine.analyse()` async API verified; `PovScore.white().score()` / `.mate()` pattern documented |
| ENG-03 | Single shared wrapper for backfill and import | Backfill script imports same `app/services/engine.py` wrapper; ENG-03 acceptance test is grep-based |
| FILL-01 | Span-entry NULL-eval backfill script with SAN replay | `scripts/reclassify_positions.py` skeleton reusable; span-entry subquery documented |
| FILL-02 | Idempotent, resumable (hash-dedup relaxed per D-10) | Row-level `WHERE eval_cp IS NULL AND eval_mate IS NULL`; COMMIT-every-100 pattern |
| FILL-03 | Benchmark first, prod second, operator-gated | VAL-01 is hard gate; plan task order documented |
| FILL-04 | Prod span-entry rows fully populated; lichess values never overwritten | Skip condition `if eval_cp is None and eval_mate is None` verified in zobrist.py pattern |
| IMP-01 | Import-time evaluation of new span entries | Insertion point at zobrist.py ~line 203; span-entry detection design tradeoff documented |
| IMP-02 | Sub-1s eval budget per typical game | Depth-15 wall-clock documented; 1-3 spans x ~50-100ms = well under 1s |
| REFAC-01 | Endgame queries threshold on eval, not material | Three queries fully mapped; new span-entry subquery shape documented |
| REFAC-02 | Color-sign flip + ±100 cp + mate rule | Rule precisely specified; service-layer callers also need update |
| REFAC-03 | Proxy constants and patterns deleted | All occurrences catalogued: `endgame_repository.py` + `endgame_service.py` |
| REFAC-04 | `ix_gp_user_endgame_game` migrated for index-only on eval columns | Alembic drop+recreate recipe documented; no other query consumers found |
| REFAC-05 | `material_imbalance` column retained | Column kept; only conv/recov read path stops using it |
| VAL-01 | `/conv-recov-validation` re-run shows ~100% agreement | Re-run existing skill against benchmark DB post-backfill |
| VAL-02 | Live-UI gauge smoke check on representative users | Operator manual check; no automated coverage needed |

</phase_requirements>

---

## Summary

- **Hard cutover:** This phase replaces a material-proxy classifier with Stockfish eval in one surgical pass. There is no fallback. The `eval_cp` and `eval_mate` columns already exist on `game_positions` with the correct white-perspective sign convention (from lichess `%eval`); the wrapper must match that convention byte-for-byte.
- **Two codepaths, one wrapper:** The backfill script (`scripts/`) and the import path (`app/services/zobrist.py`) both call the same `app/services/engine.py` wrapper. The wrapper owns all UCI option configuration; callers do nothing engine-specific.
- **Service-layer refactor is substantial:** The classification logic is not only in `endgame_repository.py` but also in `endgame_service.py` (`_aggregate_endgame_stats`, `_compute_score_gap_material`, `_endgame_skill_from_bucket_rows`). The row shape emitted by the three repository queries changes: `(user_material_imbalance, user_material_imbalance_after)` → `(user_eval_cp, user_eval_mate)` (sign-flipped versions). All service-layer consumers of those columns must be updated simultaneously with the repository queries.
- **FILL-02 drift acknowledged:** Hash dedup is dropped per D-10. Row-level idempotency (`WHERE eval_cp IS NULL AND eval_mate IS NULL`) is sufficient. PLAN.md must state this explicitly.

**Primary recommendation:** Implement in this order: engine wrapper → lifespan hook → backfill script → import-path integration → repository+service refactor (as one atomic change) → index migration → tests → validation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Engine lifecycle | API/Backend (`app/main.py` lifespan) | — | Long-lived process; must start before first request and stop on shutdown |
| Engine evaluation | API/Backend (`app/services/engine.py`) | — | Shared across import workers and backfill; owns UCI options |
| Import-time span-entry detection | API/Backend (`app/services/zobrist.py`) | — | Knows ply, endgame_class, and eval from same PGN walk |
| Backfill script | Operator CLI (`scripts/`) | — | Runs from operator machine; owns DB target selection |
| Repository query refactor | API/Backend (`app/repositories/endgame_repository.py`) | — | SQL-level: eval column projection and span-entry MIN(ply) |
| Classification rule | API/Backend (`app/services/endgame_service.py`) | — | Python-side: color flip + ±100 cp threshold + mate shortcut |
| Index migration | Database (Alembic) | — | PostgreSQL INCLUDE reshape; must run before first query using new shape |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.10.x (already in `pyproject.toml`) | Engine subprocess, UCI protocol, board replay | Already a project dependency; `chess.engine` submodule is the native async UCI client |
| SQLAlchemy 2.x async | 2.0+ (already in use) | Async DB session, UPDATE statements | Project standard; asyncpg backend |
| Alembic | 1.13+ (already in use) | Index migration | Project standard |

No new Python dependencies required. Stockfish binary is a Docker-layer addition only.

**Version verification:** `chess` package at `.venv/lib/python3.13/site-packages/chess/engine.py` confirmed present. [VERIFIED: codebase grep]

---

## python-chess Engine API

### ENG-01 / ENG-02: popen_uci and analyse

`chess.engine.popen_uci()` is a **native async coroutine** (line 2840 of `chess/engine.py`):

```python
# Source: .venv/lib/python3.13/site-packages/chess/engine.py:2840
async def popen_uci(
    command: Union[str, List[str]],
    *,
    setpgrp: bool = False,
    **popen_args: Any
) -> Tuple[asyncio.SubprocessTransport, UciProtocol]:
    ...
```

It returns `(transport, protocol)`. The `protocol` object is a `UciProtocol` with:

```python
# chess/engine.py:1039
async def configure(self, options: ConfigMapping) -> None: ...

# chess/engine.py:1095-1100 (async analyse, returns InfoDict for single, List[InfoDict] for multipv)
async def analyse(
    self, board: chess.Board, limit: Limit,
    *, game: object = None, info: Info = INFO_ALL,
    root_moves=None, options: ConfigMapping = {}
) -> InfoDict: ...

# chess/engine.py:1192
async def quit(self) -> None: ...
```

### Wrapper Implementation Pattern

```python
# app/services/engine.py (new module)
import asyncio
import os
import chess
import chess.engine

_STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "/usr/local/bin/stockfish")
_HASH_MB = 64
_THREADS = 1
_DEPTH = 15
_TIMEOUT_S = 2.0

_transport: asyncio.SubprocessTransport | None = None
_protocol: chess.engine.UciProtocol | None = None
_lock = asyncio.Lock()


async def start_engine() -> None:
    """Called from FastAPI lifespan startup."""
    global _transport, _protocol
    _transport, _protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
    await _protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})


async def stop_engine() -> None:
    """Called from FastAPI lifespan shutdown."""
    global _transport, _protocol
    if _protocol is not None:
        await _protocol.quit()
    _transport = None
    _protocol = None


async def _restart_engine() -> None:
    """Called internally after timeout/crash to restore a valid engine state."""
    global _transport, _protocol
    if _protocol is not None:
        try:
            await _protocol.quit()
        except Exception:
            pass
    _transport, _protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
    await _protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})


async def evaluate(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate board at depth 15. Returns (eval_cp, eval_mate) in white perspective.

    - eval_cp: centipawn score, None if position is a forced mate
    - eval_mate: moves to mate (positive = white mates, negative = black mates), None if not mate
    - Returns (None, None) on engine error/timeout — caller skips the row.
    """
    async with _lock:
        if _protocol is None:
            return None, None
        try:
            info = await asyncio.wait_for(
                _protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
                timeout=_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, chess.engine.EngineError, chess.engine.EngineTerminatedError):
            await _restart_engine()
            return None, None

    pov_score = info.get("score")
    if pov_score is None:
        return None, None

    # chess.engine returns score from the side to move's perspective.
    # .white() normalizes to white perspective regardless of board.turn.
    white_score = pov_score.white()
    eval_cp: int | None = white_score.score(mate_score=None)  # None if mate
    eval_mate: int | None = white_score.mate()               # None if not mate

    # Clamp to SMALLINT-safe bounds (mirrors zobrist.py EVAL_CP_MAX_ABS / EVAL_MATE_MAX_ABS)
    if eval_cp is not None:
        from app.services.zobrist import EVAL_CP_MAX_ABS
        eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
    if eval_mate is not None:
        from app.services.zobrist import EVAL_MATE_MAX_ABS
        eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))

    return eval_cp, eval_mate
```

**Sign convention:**
- `pov_score` from `analyse()` has attribute `turn` indicating which side's POV it is.
- `pov_score.white()` always returns the score from white's perspective, regardless of `board.turn`. [VERIFIED: chess/engine.py:351-361]
- `white_score.score(mate_score=None)` returns `None` for mate positions and the centipawn int otherwise. [VERIFIED: chess/engine.py:415-429]
- `white_score.mate()` returns `None` if not mate, a positive int if white mates in N, a negative int if black mates in N. [VERIFIED: chess/engine.py:431-443]
- This exactly matches the lichess `%eval` convention already in `app/services/zobrist.py:184-197`.

**SMALLINT range:** `eval_cp` is stored as `SmallInteger` (±32767). `EVAL_CP_MAX_ABS = 10000` and `EVAL_MATE_MAX_ABS = 200` are the existing clamp bounds (zobrist.py:111-112). These are safe for depth-15 output. [VERIFIED: codebase]

**Wall-clock at depth 15:** Stockfish at depth 15 with `Hash=64MB, Threads=1` on endgame positions typically completes in 20-100 ms. 3 span entries × 100 ms = 300 ms, comfortably under the 1s IMP-02 budget. [ASSUMED — no measurement on the 4-vCPU Hetzner box; planner should add timing instrumentation in the import path as a verification step]

**Exceptions raised:**
- `chess.engine.EngineError` — protocol error (unexpected engine response)
- `chess.engine.EngineTerminatedError` — engine process died (subclass of EngineError)
- `asyncio.TimeoutError` — raised by `asyncio.wait_for()` on 2s expiry
- On timeout or crash: the engine state is indeterminate. The wrapper must restart before the next call (`_restart_engine()`). [VERIFIED: chess/engine.py:84-85, 1244]

### FastAPI Lifespan Hook

Current `app/main.py` lifespan (line 44-52):
```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()          # existing — must stay first
    await cleanup_orphaned_jobs() # existing
    yield
```

New pattern (insert engine start/stop):
```python
from app.services.engine import start_engine, stop_engine

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()
    await cleanup_orphaned_jobs()
    await start_engine()          # NEW: ENG-01
    try:
        yield
    finally:
        await stop_engine()       # NEW: clean shutdown
```

The engine is ready before the first request because lifespan completes before uvicorn starts serving. [VERIFIED: FastAPI docs pattern]

---

## Stockfish Docker Install

### Dockerfile Pattern

Current `Dockerfile` (builder + runtime two-stage, line 1-23) uses `python:3.13-slim`. The Stockfish install must go in the **runtime** stage, after the builder copy, as a separate cacheable layer.

```dockerfile
# In runtime stage, after COPY --from=builder:
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates \
    && wget -q "https://github.com/official-stockfish/Stockfish/releases/download/sf_17/stockfish-ubuntu-x86-64-avx2.tar" \
       -O /tmp/stockfish.tar \
    && tar -xf /tmp/stockfish.tar -C /tmp \
    && mv /tmp/stockfish/stockfish-ubuntu-x86-64-avx2 /usr/local/bin/stockfish \
    && chmod +x /usr/local/bin/stockfish \
    && rm -rf /tmp/stockfish.tar /tmp/stockfish \
    && apt-get purge -y wget && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV STOCKFISH_PATH=/usr/local/bin/stockfish
```

**Verify checksum:** Download the `.sha256` file from the same GitHub release and verify:
```dockerfile
RUN echo "<sha256hash>  /usr/local/bin/stockfish" | sha256sum -c -
```
The sha256 hash must be pinned in the Dockerfile at commit time. [CITED: github.com/official-stockfish/Stockfish/releases]

**AVX2 on Hetzner CX32:** The server is documented as 4 vCPUs, Hetzner Cloud. Common Hetzner CX-series use Intel Skylake or newer, which includes AVX2. The `stockfish-ubuntu-x86-64-avx2` binary requires AVX2. [ASSUMED — the exact CPU generation for this specific server was not verified; operator should run `grep avx2 /proc/cpuinfo | head -1` on the prod server before finalizing the Dockerfile. If AVX2 is absent, use `stockfish-ubuntu-x86-64` (popcnt baseline) instead.]

**Image size:** The Stockfish binary for sf_17 is approximately 50 MB. This adds one small layer to the image; since it downloads from a stable URL pinned by release tag it caches well between deploys. The 3 GB BuildKit cap (daily prune) is unlikely to be stressed by a single extra 50 MB layer. [ASSUMED size; verify `du -sh /usr/local/bin/stockfish` after first build]

**Local dev:** `apt install stockfish` on Ubuntu/Debian installs an older version (likely sf_16 or earlier). This is acceptable for local development because the operator's local machine only runs the backfill (one-shot per DB round), and the same engine version runs for the entire backfill round. Version drift between local and Docker affects reproducibility of the backfill results, but each DB round is atomic so this is not a correctness issue. [VERIFIED: CONTEXT.md specifics note]

---

## Backfill Script Patterns

### Span-Entry Row Definition

A "span entry" is the `MIN(ply)` row for each `(game_id, endgame_class)` group where `COUNT(ply) >= ENDGAME_PLY_THRESHOLD`. [VERIFIED: SPEC.md FILL-01, endgame_repository.py:208-222]

**SQL subquery pattern (for backfill SELECT):**

```sql
-- Identify span-entry game_position IDs that need evaluation
SELECT gp.id, gp.game_id, gp.ply, gp.user_id, g.pgn
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.eval_cp IS NULL
  AND gp.eval_mate IS NULL
  AND gp.endgame_class IS NOT NULL
  AND gp.ply = (
      SELECT MIN(inner_gp.ply)
      FROM game_positions inner_gp
      WHERE inner_gp.game_id = gp.game_id
        AND inner_gp.endgame_class = gp.endgame_class
        AND inner_gp.user_id = gp.user_id
      GROUP BY inner_gp.game_id, inner_gp.endgame_class
      HAVING COUNT(inner_gp.ply) >= 6
  )
ORDER BY gp.game_id, gp.ply
```

**SQLAlchemy 2.x async equivalent (for script):**

```python
# Span-entry subquery: MIN(ply) per (game_id, endgame_class) with count >= threshold
span_min_ply_subq = (
    select(
        GamePosition.game_id,
        GamePosition.endgame_class,
        func.min(GamePosition.ply).label("min_ply"),
    )
    .where(GamePosition.endgame_class.isnot(None))
    .group_by(GamePosition.game_id, GamePosition.endgame_class)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("span_min")
)

stmt = (
    select(GamePosition.id, GamePosition.game_id, GamePosition.ply, Game.pgn)
    .join(Game, Game.id == GamePosition.game_id)
    .join(
        span_min_ply_subq,
        (GamePosition.game_id == span_min_ply_subq.c.game_id)
        & (GamePosition.endgame_class == span_min_ply_subq.c.endgame_class)
        & (GamePosition.ply == span_min_ply_subq.c.min_ply),
    )
    .where(
        GamePosition.eval_cp.is_(None),
        GamePosition.eval_mate.is_(None),
    )
)
if user_id is not None:
    stmt = stmt.where(GamePosition.user_id == user_id)
stmt = stmt.order_by(GamePosition.game_id, GamePosition.ply)
```

### SAN Replay to Span-Entry Ply

Replay the PGN up to (but not beyond) the span-entry ply, then evaluate:

```python
import io
import chess
import chess.pgn

def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to target_ply (0-indexed). Returns the board BEFORE the move at that ply."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i == target_ply:
            # board is at pre-move state for ply `target_ply` — this is the span-entry position
            return board
        board.push(node.move)
    # ply is the final position (no more moves)
    return board
```

This mirrors `scripts/reclassify_positions.py:136-176` exactly. [VERIFIED: codebase]

**The ply stored in `game_positions` is 0-indexed and pre-push:** verified at `app/services/zobrist.py:172-175`. Position at `ply=N` is the board state BEFORE the N-th move is pushed. The replay loop must stop at iteration `i == target_ply` without pushing the move.

### COMMIT-every-100 Pattern (SQLAlchemy 2.x async)

```python
EVAL_BATCH_SIZE = 100
committed = 0

async with async_session_maker() as session:
    rows = await session.execute(stmt)
    rows = rows.fetchall()

# Process outside the fetch session to allow re-use
async with async_session_maker() as session:
    for i, row in enumerate(rows):
        board = _board_at_ply(row.pgn, row.ply)
        if board is None:
            continue
        eval_cp, eval_mate = await engine.evaluate(board)
        if eval_cp is None and eval_mate is None:
            # Engine error/timeout — skip, log, continue
            continue
        await session.execute(
            sa_update(GamePosition)
            .where(GamePosition.id == row.id)
            .values(eval_cp=eval_cp, eval_mate=eval_mate)
        )
        if (i + 1) % EVAL_BATCH_SIZE == 0:
            await session.commit()
            committed += i + 1
    await session.commit()  # flush remainder
```

**No `asyncio.gather` on same session** — CLAUDE.md critical constraint. All updates are sequential within the same session. [VERIFIED: CLAUDE.md]

### DB Target Selection (CLI)

```python
DB_URLS = {
    "dev":       "postgresql+asyncpg://flawchess:...@localhost:5432/flawchess",
    "benchmark": "postgresql+asyncpg://flawchess:...@localhost:5433/flawchess_benchmark",
    "prod":      "postgresql+asyncpg://flawchess:...@localhost:15432/flawchess",
}
```

The script reads DB credentials from env vars or settings, not hardcoded. The `--db` flag selects the target host/port. This mirrors how `reclassify_positions.py` uses `app.core.config.settings` which reads from `.env`. [VERIFIED: reclassify_positions.py:39-40]

---

## Import-Path Integration

### Insertion Point

Current flow in `app/services/import_service.py` (function `_flush_batch`, ~line 399-506):
1. `process_game_pgn(pgn)` calls `zobrist.py` → returns `plies: list[PlyData]`
2. Each `ply_data` already has `eval_cp` and `eval_mate` from lichess `%eval` (or None for chess.com)
3. All position rows are inserted via `bulk_insert_positions`

The engine call must happen AFTER the bulk insert (so `game_positions.id` values exist for UPDATE) but BEFORE the final `session.commit()`. This means the integration lives in `_flush_batch` after step 5 (bulk insert positions).

However, the engine call needs to know which rows are span entries. At import time, we do not yet know the final `COUNT(ply)` for each `(game_id, endgame_class)` group — the game has not been committed yet and we are building position rows in memory.

**Design recommendation: post-insert pass within the same session.**

After `bulk_insert_positions` but before `session.commit()`:
1. Identify span-entry plies from the in-memory `plies` list: group by `endgame_class`, find the first ply of each group, count how many plies in that group. Groups with `count >= ENDGAME_PLY_THRESHOLD` → the first ply is a span entry.
2. For span-entry plies that have `eval_cp is None and eval_mate is None`, call `evaluate(board)`.
3. Issue an UPDATE for those rows by `(game_id, ply)` (the `game_id` is known, `ply` is known; no extra SELECT needed).

This approach requires replaying the board state during import, but the PGN replay already happened inside `process_game_pgn`. The boards are not retained. **Two options:**

**Option A (recommended): Re-derive boards in-memory from the already-parsed plies list.**
The `plies` list from `process_game_pgn` is still in scope. To get the board at each span-entry ply, call `_board_at_ply(pgn, target_ply)` — a second PGN parse for span-entry plies only. Cost: 1-3 PGN re-parses per game (for span-entry plies). Typical PGN parse is <1ms. This is simpler than threading the board objects through the PlyData TypedDict.

**Option B: Extend PlyData to carry board snapshots.** Adds memory pressure; `chess.Board` objects are ~10KB each; a 100-move game × 100 positions = 1MB per game. Not recommended.

**Option A call site (inside `_flush_batch`, after bulk insert):**

```python
# After bulk_insert_positions, before final commit:
# Identify span-entry plies: group plies by endgame_class, find MIN(ply) for groups >= threshold
from collections import defaultdict

class_plies: dict[int, list[int]] = defaultdict(list)
for pd in processing_result["plies"]:
    if pd["endgame_class"] is not None:
        class_plies[pd["endgame_class"]].append(pd["ply"])

for ec, ply_list in class_plies.items():
    if len(ply_list) < ENDGAME_PLY_THRESHOLD:
        continue
    span_entry_ply = min(ply_list)
    span_pd = next(p for p in processing_result["plies"] if p["ply"] == span_entry_ply and p["endgame_class"] == ec)
    if span_pd["eval_cp"] is None and span_pd["eval_mate"] is None:
        board = _board_at_ply(pgn, span_entry_ply)
        if board is not None:
            try:
                eval_cp, eval_mate = await asyncio.wait_for(engine.evaluate(board), timeout=2.0)
            except (asyncio.TimeoutError, chess.engine.EngineError, chess.engine.EngineTerminatedError) as exc:
                import sentry_sdk
                sentry_sdk.set_context("eval", {"game_id": game_id, "ply": span_entry_ply, "endgame_class": ec})
                sentry_sdk.capture_exception(exc)
                continue  # D-11: skip, don't fail the import
            if eval_cp is not None or eval_mate is not None:
                await session.execute(
                    sa_update(GamePosition)
                    .where(GamePosition.game_id == game_id, GamePosition.ply == span_entry_ply,
                           GamePosition.endgame_class == ec)
                    .values(eval_cp=eval_cp, eval_mate=eval_mate)
                )
```

**IMP-02 budget:** 1-3 evaluations × ~70ms average + 1-3 PGN re-parses × <1ms = ~200-300ms added per game at p50. Well under 1s. [ASSUMED timing; to verify: add `time.perf_counter()` instrumentation and log p50 over 100 imports]

**Important:** The `engine.evaluate()` wrapper already applies the 2s timeout via `asyncio.wait_for` internally (D-05). The import call site does NOT need to wrap it again. Keep the call simple: `await engine.evaluate(board)`.

**D-11 Sentry pattern:**
```python
import sentry_sdk
sentry_sdk.set_context("eval", {
    "game_id": game_id,
    "ply": span_entry_ply,
    "endgame_class": ec,
})
sentry_sdk.set_tag("source", "import")
sentry_sdk.capture_exception(exc)
continue
```

---

## Repository Query Refactor

### Scope of Change

Three queries must be rewritten (REFAC-01). Additionally, `_MATERIAL_ADVANTAGE_THRESHOLD` is defined in **both** `endgame_repository.py` (as a constant, not exported) and `endgame_service.py:164`. The service-layer functions `_aggregate_endgame_stats`, `_compute_score_gap_material`, and `_endgame_skill_from_bucket_rows` all consume `user_material_imbalance` / `user_material_imbalance_after` from the row shape. These must be updated simultaneously.

### Three Repository Queries: Current → Target Shape

**`query_endgame_entry_rows` (line 145-258):**
- Current output columns: `(game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after)`
- Target output columns: `(game_id, endgame_class, result, user_color, user_eval_cp, user_eval_mate)` where `user_eval_cp` is `eval_cp * color_sign` (or just `eval_cp` with color flip logic moved to service)

**Simpler approach:** Project `eval_cp` and `eval_mate` directly (white-perspective from DB), and let the service layer apply the color sign flip at classification time. This is consistent with how the DB stores them and avoids a SQL multiplication of a nullable column.

**`query_endgame_bucket_rows` (line 261-386):**
- Current: same shape as entry_rows
- Target: same as entry_rows target

**`query_endgame_elo_timeline_rows` (line 800-956):**
- Current: projects `user_material_imbalance`, `user_material_imbalance_after` in bucket_stmt
- Target: projects `eval_cp`, `eval_mate`

### New Span-Entry Subquery (for all three queries)

Replace the `entry_imbalance_agg` / `raw_imbalance_after` / `imbalance_after_persistence_agg` pattern with a simpler `MIN(ply)` aggregation that fetches `eval_cp` and `eval_mate` at the entry ply:

```python
# New span-entry subquery pattern (replaces the entire array_agg block)
entry_eval_cp_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.eval_cp, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]

entry_eval_mate_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.eval_mate, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]

span_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        GamePosition.endgame_class.label("endgame_class"),
        entry_eval_cp_agg.label("entry_eval_cp"),
        entry_eval_mate_agg.label("entry_eval_mate"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    .group_by(GamePosition.game_id, GamePosition.endgame_class)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("span")
)
```

The `ARRAY(SmallIntegerType)[1]` trick fetches the value at the MIN ply position — same pattern already used in the codebase for `material_imbalance`. [VERIFIED: endgame_repository.py:181-184]

**Index-only scan:** After the migration (D-12), `ix_gp_user_endgame_game` will `INCLUDE(eval_cp, eval_mate)`. The new `array_agg(eval_cp ORDER BY ply)` and `array_agg(eval_mate ORDER BY ply)` fetches will use this index for index-only scans, matching the current `material_imbalance` behavior. [VERIFIED: index defined at game_position.py:26-31; Alembic migration befacc0fce23 shows the precedent]

### Service-Layer Classification Rule (REFAC-02)

Current classification in `endgame_service.py:240-266` (and mirrored in `_compute_score_gap_material:710-737` and `_endgame_skill_from_bucket_rows:938-942`):

```python
# CURRENT: material proxy with persistence check
if imb >= _MATERIAL_ADVANTAGE_THRESHOLD and imb_after >= _MATERIAL_ADVANTAGE_THRESHOLD:
    # conversion
if imb <= -_MATERIAL_ADVANTAGE_THRESHOLD and imb_after <= -_MATERIAL_ADVANTAGE_THRESHOLD:
    # recovery
```

New rule (REFAC-02 spec): **user-color sign flip first, then single-point eval threshold.**

```python
EVAL_ADVANTAGE_THRESHOLD = 100  # centipawns (replaces _MATERIAL_ADVANTAGE_THRESHOLD)

def _classify_endgame_bucket(
    eval_cp: int | None,
    eval_mate: int | None,
    user_color: str,
) -> Literal["conversion", "parity", "recovery"]:
    """Apply user-color sign flip, then threshold. Single entry-ply eval, no persistence."""
    if eval_cp is None and eval_mate is None:
        return "parity"
    sign = 1 if user_color == "white" else -1
    # Mate shortcut: any mate score is max advantage
    if eval_mate is not None:
        user_mate = eval_mate * sign
        if user_mate > 0:
            return "conversion"
        if user_mate < 0:
            return "recovery"
        return "parity"  # mate_in_0 edge case (shouldn't happen at span entry)
    # Centipawn threshold
    assert eval_cp is not None
    user_cp = eval_cp * sign
    if user_cp >= EVAL_ADVANTAGE_THRESHOLD:
        return "conversion"
    if user_cp <= -EVAL_ADVANTAGE_THRESHOLD:
        return "recovery"
    return "parity"
```

This helper can live in `endgame_service.py` and be called from `_aggregate_endgame_stats`, `_compute_score_gap_material`, and `_endgame_skill_from_bucket_rows`. **No persistence check** — eval already factors compensation.

### Deletion Checklist (REFAC-03)

All must be deleted:

| Symbol | File | Location |
|--------|------|----------|
| `PERSISTENCE_PLIES = 4` | `endgame_repository.py` | Line 71 |
| `_MATERIAL_ADVANTAGE_THRESHOLD = 100` | `endgame_service.py` | Line 164 |
| `entry_imbalance_agg` pattern | `endgame_repository.py` | Lines 181-184, 310-313, 849-852 |
| `raw_imbalance_after` pattern | `endgame_repository.py` | Lines 193-196, 320-323, 853-856 |
| `ply_at_persistence` pattern | `endgame_repository.py` | Lines 198-201, 325-328, 857-860 |
| `imbalance_after_persistence_agg` CASE expr | `endgame_repository.py` | Lines 203-206, 335-338, 863-866 |
| `user_material_imbalance` labels | `endgame_repository.py` | Lines 238-239, 367-368, 896-898 |
| `user_material_imbalance` / `user_material_imbalance_after` | `endgame_service.py` | Lines 181,214-215,243-260,693,712-713,727-733,898-902,932-942 |

After deletion, verify:
```bash
grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD|PERSISTENCE_PLIES" app/ scripts/ tests/
grep -n "imbalance_after|aggregate_order_by.*PERSISTENCE" app/repositories/endgame_repository.py
```

### REFAC-05: material_imbalance column is kept

The column still exists in `game_position.py:77`, still populated in `import_service.py:479`, still set in `zobrist.py:220,249`. Only the conv/recov read path in the three endgame queries stops projecting it. No schema migration needed for this. [VERIFIED: codebase]

---

## Index INCLUDE Migration

### Current Definition (`game_position.py:26-31`)

```python
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["material_imbalance"],
)
```

### Target Definition

```python
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["eval_cp", "eval_mate"],
)
```

### Alembic Migration Recipe

Pattern from `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py`:

```python
def upgrade() -> None:
    # Drop old index with material_imbalance INCLUDE, recreate with eval columns
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

**Other consumers of this index:** Grep confirms no query outside `endgame_repository.py` references or depends on `material_imbalance` via this index. `query_endgame_timeline_rows` (line 578) and `query_clock_stats_rows` (line 731) use the index for the `(user_id, game_id, endgame_class, ply)` key columns only, not for INCLUDE columns. They will continue to work with the new INCLUDE shape. [VERIFIED: endgame_repository.py full read]

**EXPLAIN verification query (run post-migration on benchmark DB):**
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT game_id, endgame_class,
       (array_agg(eval_cp ORDER BY ply))[1]   AS entry_eval_cp,
       (array_agg(eval_mate ORDER BY ply))[1]  AS entry_eval_mate
FROM game_positions
WHERE user_id = <test_user_id>
  AND endgame_class IS NOT NULL
GROUP BY game_id, endgame_class
HAVING COUNT(ply) >= 6;
```

Expected output: `Index Only Scan using ix_gp_user_endgame_game` with `Heap Fetches: 0` (after `VACUUM ANALYZE game_positions`).

**Note:** A `CREATE INDEX` without `CONCURRENTLY` on a large table will briefly lock writes. On the prod DB (which has ~5M+ rows in `game_positions`), this lock window will be seconds, not minutes, because the partial index only covers endgame rows. The operator should schedule the migration during low-traffic hours. If lock duration is a concern, Alembic does not natively support `CONCURRENTLY` but a raw SQL migration can use it:
```python
op.execute("CREATE INDEX CONCURRENTLY ix_gp_user_endgame_game_new ON ...")
op.execute("DROP INDEX ix_gp_user_endgame_game")
op.execute("ALTER INDEX ix_gp_user_endgame_game_new RENAME TO ix_gp_user_endgame_game")
```
This is a lower-risk option but requires wrapping in `with op.get_bind().execution_options(isolation_level="AUTOCOMMIT")`. [ASSUMED risk level; operator can assess based on prod traffic patterns]

---

## Test Strategy

### ENG-02: Engine Wrapper Unit Tests (`tests/test_engine.py`)

All tests require Stockfish on PATH. Mark with `skipif`:

```python
import shutil
import pytest

stockfish_missing = shutil.which("stockfish") is None
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish not on PATH")
```

**Test positions (FEN-based):**

| Position | FEN | Expected |
|----------|-----|---------|
| White queen up (conversion) | `8/4Q3/8/8/8/8/4k3/4K3 w - - 0 1` | `eval_cp >= 100`, `eval_mate is None` |
| Black queen up (recovery from white POV) | `8/4q3/8/8/8/8/4K3/4k3 b - - 0 1` | `eval_cp <= -100`, `eval_mate is None` |
| White mates in 3 | `r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4` (scholar's approach) | needs a real forced mate FEN |
| Near-equal | `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1` | `abs(eval_cp) < 100` (starting position + e4) |
| Black mates in 2 | (use a known forced mate FEN where black wins) | `eval_mate < 0` (negative = black mates) |

**Practical known FENs for the wrapper test (use positions where Stockfish at depth 15 gives deterministic results):**

```python
# KQ vs K — white wins trivially
SIMPLE_QUEEN_UP = "8/8/8/8/8/8/4Q3/4K2k w - - 0 1"
# K vs Q — black wins; from white's perspective eval_cp << -100
SIMPLE_QUEEN_DOWN = "8/8/8/8/8/8/4q3/4k2K b - - 0 1"
# Checkmate position: white already mated (eval_mate = 0 for side to move? no, MateGiven)
# Use a position where white is about to deliver mate in 1
MATE_IN_1_WHITE = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"  # adjust as needed
```

**Recommended test structure:**

```python
@skip_if_no_stockfish
@pytest.mark.asyncio
class TestEngineWrapper:
    @pytest_asyncio.fixture(autouse=True, scope="class")
    async def engine_started(self):
        from app.services.engine import start_engine, stop_engine
        await start_engine()
        yield
        await stop_engine()

    async def test_white_winning_returns_positive_eval_cp(self):
        import chess
        from app.services.engine import evaluate
        board = chess.Board(SIMPLE_QUEEN_UP)
        eval_cp, eval_mate = await evaluate(board)
        assert eval_cp is not None and eval_cp >= 100

    async def test_black_winning_returns_negative_eval_cp(self):
        ...

    async def test_mate_returns_eval_mate_not_eval_cp(self):
        ...

    async def test_near_equal_returns_abs_cp_lt_100(self):
        ...
```

### REFAC-02: Classification Rule Unit Tests

The `_classify_endgame_bucket` helper is pure Python — no DB needed.

```python
class TestClassifyEndgameBucket:
    def test_white_positive_cp_gte_100_is_conversion(self):
        assert _classify("white", eval_cp=150, eval_mate=None) == "conversion"

    def test_black_positive_with_user_black_is_conversion(self):
        # black is winning: eval_cp = -300 (from white's perspective), user is black
        assert _classify("black", eval_cp=-300, eval_mate=None) == "conversion"

    def test_user_mate_positive_is_conversion(self):
        # white mates in 3: eval_mate=3, user=white → user_mate=3 → conversion
        assert _classify("white", eval_cp=None, eval_mate=3) == "conversion"

    def test_user_mated_is_recovery(self):
        # black mates in 3 (white is being mated): eval_mate=-3, user=white → user_mate=-3 → recovery
        assert _classify("white", eval_cp=None, eval_mate=-3) == "recovery"

    def test_abs_cp_lt_100_is_parity(self):
        assert _classify("white", eval_cp=50, eval_mate=None) == "parity"

    def test_null_eval_is_parity(self):
        assert _classify("white", eval_cp=None, eval_mate=None) == "parity"

    def test_recovery_case(self):
        assert _classify("white", eval_cp=-200, eval_mate=None) == "recovery"
```

### Existing Tests That Must Not Regress

`tests/test_endgame_repository.py` — tests use `material_imbalance`-based assertions. After the refactor, these tests must be updated to seed `eval_cp`/`eval_mate` and assert on the new row shape. [VERIFIED: test_endgame_repository.py:head]

`tests/test_endgame_service.py` — `TestScoreGapMaterialInvariant` (explicitly mentioned at endgame_service.py:691) must be updated for the new classification API.

`tests/test_aggregation_sanity.py` — uses `material_imbalance` in `_make_endgame_row` helper (line 112, 124). Must be updated.

### Backfill Script Integration Test

Seed 3-5 span-entry rows with NULL eval in the dev DB, run `scripts/backfill_eval.py --db dev --dry-run`, verify count = 5, then run without `--dry-run`, verify eval columns populated. This is an operator-run test, not CI.

### CI Considerations

The engine wrapper tests require Stockfish on the CI runner. Options:
1. `apt install stockfish` in the GitHub Actions workflow (adds ~30s to CI)
2. Mark tests `@skip_if_no_stockfish` and add Stockfish install to CI `.github/workflows/ci.yml`

Option 2 is recommended: install stockfish in CI with `apt-get install -y stockfish`, which provides a fast prebuilt package (may be sf_16). The wrapper tests test the API contract, not the exact eval value, so minor version differences are acceptable. [ASSUMED: CI runner is Ubuntu-based; verify in `.github/workflows/ci.yml`]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_engine.py tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENG-01 | Stockfish binary in container | manual | `docker compose exec backend stockfish --help` | N/A |
| ENG-02 | Wrapper returns correct eval | unit | `uv run pytest tests/test_engine.py -x` | ❌ Wave 0 |
| ENG-03 | Engine options only in wrapper | grep | `grep -rn "stockfish\|UCI\|setoption" app/ scripts/` | N/A |
| FILL-01 | Backfill populates span-entry rows | operator | `uv run python scripts/backfill_eval.py --db dev --dry-run` | ❌ Wave 0 |
| FILL-02 | Idempotent, resumable | operator | run twice, count engine calls = 0 on second run | N/A |
| FILL-03 | Benchmark-first run order | plan gate | VAL-01 between benchmark and prod | N/A |
| FILL-04 | Zero NULL span-entry rows post-backfill | SQL | post-backfill count query on prod | N/A |
| IMP-01 | Import evaluates new span entries | integration | `uv run pytest tests/test_import_service.py -k engine` | ❌ Wave 0 |
| IMP-02 | Sub-1s eval budget | timing | log instrumentation + manual timing check | N/A |
| REFAC-01 | Queries use eval, not material | unit | `uv run pytest tests/test_endgame_repository.py -x` | ✅ (needs update) |
| REFAC-02 | Classification rule unit tests | unit | `uv run pytest tests/test_endgame_service.py -x` | ✅ (needs update) |
| REFAC-03 | Proxy constants deleted | grep | `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` | N/A |
| REFAC-04 | Index-only scan confirmed | operator | `EXPLAIN (ANALYZE, BUFFERS)` on benchmark DB | N/A |
| REFAC-05 | material_imbalance column retained | grep | `grep "material_imbalance" app/models/game_position.py` | N/A |
| VAL-01 | Conv-recov validation ≥99% agreement | operator | `/conv-recov-validation` skill re-run on benchmark DB | N/A |
| VAL-02 | Live-UI gauges sensible on prod | operator | manual smoke check on 3-5 representative users | N/A |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_engine.py tests/test_endgame_service.py tests/test_endgame_repository.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_engine.py` — new file; covers ENG-02 (wrapper unit tests with known positions)
- [ ] `tests/test_import_service.py` additions — IMP-01 test (import evaluates span entries; requires engine mock or skipif)
- [ ] Update `tests/test_endgame_repository.py` — seed `eval_cp`/`eval_mate` instead of `material_imbalance`; assert on new row shape
- [ ] Update `tests/test_endgame_service.py` — `TestScoreGapMaterialInvariant` + classification rule tests

---

## Risks & Landmines

### Risk 1: Service-layer scope larger than repository-only

The SPEC and CONTEXT.md focus on `endgame_repository.py`, but the classification logic is duplicated in `endgame_service.py` in three places: `_aggregate_endgame_stats` (line 240-260), `_compute_score_gap_material` (line 710-737), and `_endgame_skill_from_bucket_rows` (line 938-942). Additionally, `_MATERIAL_ADVANTAGE_THRESHOLD` is defined in `endgame_service.py:164`. These must all change atomically with the repository refactor or the service will misclassify.

**Mitigation:** Planner must treat the repository refactor + service-layer update as a single wave task, not two separate tasks.

### Risk 2: ty type-check failures on new row shape

The row shape changes from `(user_material_imbalance, user_material_imbalance_after)` to `(eval_cp, eval_mate)`. The service-layer functions destructure rows using attribute access (`r.user_material_imbalance`). After renaming, ty will flag unresolved attribute errors on `Row` objects. Pattern in codebase: use `ty: ignore[unresolved-attribute]` with a comment, or use positional tuple unpacking (already done in `_endgame_skill_from_bucket_rows:924-934` via tuple unpacking).

**Mitigation:** Prefer tuple unpacking for the new row shape in service functions, which avoids attribute name ty errors. Update docstrings to document the new tuple shape.

### Risk 3: FILL-02 drift must be explicit in PLAN.md

If the plan-checker reads SPEC.md FILL-02 literally, it will flag the missing hash-dedup as a BLOCKER. The plan must include an explicit drift acknowledgment: "FILL-02 hash-dedup relaxed per D-10: row-level idempotency only." This is a plan-checker concern, not a runtime concern.

### Risk 4: AVX2 binary on Hetzner prod server

If the Hetzner prod VM does not support AVX2 instructions, the avx2 binary will segfault at startup. This is an operator-verification step before finalizing the Dockerfile. Check: `grep -c avx2 /proc/cpuinfo` on the prod server; if 0, use the `stockfish-ubuntu-x86-64` (popcnt) binary instead. [ASSUMED safe; must be verified]

### Risk 5: Prod SSH tunnel drops mid-backfill

`bin/prod_db_tunnel.sh` forwards `localhost:15432` → prod. If the tunnel drops mid-backfill, SQLAlchemy will raise a connection error on the next `session.execute()`. The COMMIT-every-100 pattern ensures all committed rows are preserved. On reconnect, the resume SELECT (`WHERE eval_cp IS NULL AND eval_mate IS NULL`) skips committed rows automatically. No data loss, but the operator must restart the script. Document this in the backfill runbook.

### Risk 6: `asyncio.wait_for` on `_lock`-held coroutine

The wrapper's `_lock` is acquired before `asyncio.wait_for`. If the engine times out, the lock is still held while `_restart_engine()` runs. During restart, other import workers calling `evaluate()` will queue on `_lock`. This is safe (CLAUDE.md: no asyncio.gather on same session; no parallel engine calls anyway) but the restart duration adds latency to queued callers. At `Hash=64MB, Threads=1`, a timeout at 2s means worst case 2s + restart overhead per caller. Acceptable.

### Risk 7: `eval_cp` SmallInteger range

`eval_cp` is `SmallInteger` (±32767). `EVAL_CP_MAX_ABS = 10000`. Depth-15 Stockfish on endgame positions will not produce cp scores beyond ±10000 in practice. The wrapper must apply the same clamps as `zobrist.py:194-197` before writing. [VERIFIED: game_position.py:91; zobrist.py:111-112]

### Risk 8: Existing `test_endgame_repository.py` and `test_aggregation_sanity.py` will break

These tests seed rows with `material_imbalance` and assert on `user_material_imbalance`. They will break after the refactor. This is expected breakage that must be fixed in the same wave as the repository refactor. The planner should include "update existing repository and service tests" as an explicit task.

### Risk 9: Index rebuild lock on prod

`DROP INDEX` + `CREATE INDEX` without `CONCURRENTLY` briefly locks writes to `game_positions`. The partial index covers only endgame rows, so the rebuild is fast, but it is not instantaneous on a 5M+ row table. The operator should run the migration during off-peak hours, or use the `CONCURRENTLY` SQL approach described above.

---

## Open Questions for Planner

1. **AVX2 verification on prod:** Has the operator confirmed `grep -c avx2 /proc/cpuinfo` on the Hetzner prod server? The Dockerfile binary selection depends on this. If unconfirmed, build with the popcnt fallback binary as a safe default, or add a startup check.

2. **Engine wrapper location:** The CONTEXT.md says "e.g. `app/services/engine.py`". The planner should confirm this name and add it to the canonical refs.

3. **Global engine reference in backfill script:** The backfill script is a standalone asyncio script (not a FastAPI app), so it cannot use the lifespan-managed global. The script must create its own engine instance (call `start_engine()` / `stop_engine()` directly within its `main()` async context). Confirm this is the intended pattern.

4. **VACUUM ANALYZE after backfill:** The `reclassify_positions.py` script runs `VACUUM ANALYZE game_positions` after completion. The backfill script should do the same, since it writes many `eval_cp` / `eval_mate` values that the planner will query immediately with `EXPLAIN (ANALYZE, BUFFERS)`.

5. **CI stockfish install:** Should `apt-get install -y stockfish` be added to the GitHub Actions CI workflow, or should engine tests be `skipif(stockfish_missing)`? If CI installs stockfish, the tests run on every PR and catch regressions early. If skipif, engine tests only run locally.

6. **Task ordering for import-path integration:** The engine call in `_flush_batch` requires the wrapper to be importable at module load time. If `start_engine()` has not been called (e.g. during test), `_protocol` is None and `evaluate()` returns `(None, None)`. This is the intended fallback. Confirm tests can rely on this without needing to start a real engine.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Depth-15 wall-clock is ~50-100ms on Hetzner CX32 | python-chess Engine API | Import timing blows IMP-02 budget; must add instrumentation and potentially lower depth or tune Threads |
| A2 | Hetzner CX32 supports AVX2 | Stockfish Docker Install | avx2 binary segfaults; use popcnt fallback |
| A3 | Stockfish sf_17 binary is ~50MB | Stockfish Docker Install | Different actual size; doesn't affect correctness, only image layer estimate |
| A4 | CI runner is Ubuntu-based | Test Strategy | `apt install stockfish` fails; alternative install method needed |

---

## Sources

### Primary (HIGH confidence)

- `app/repositories/endgame_repository.py` — full read; all three queries mapped, proxy pattern documented
- `app/services/endgame_service.py:164-266, 638-755, 884-960` — service-layer classification logic fully catalogued
- `app/services/zobrist.py:1-230` — eval sign convention, PlyData TypedDict, EVAL_CP_MAX_ABS/EVAL_MATE_MAX_ABS
- `app/services/import_service.py:399-506` — `_flush_batch` insertion point and position row construction
- `app/models/game_position.py` — column types, index definition at line 26-31
- `app/main.py` — lifespan handler; existing startup order
- `.venv/lib/python3.13/site-packages/chess/engine.py` — `popen_uci` (line 2840), `analyse` (line 1095-1100), `PovScore.white()` (line 351), `Score.score()` / `.mate()` (lines 415, 431), exception types (lines 80-84)
- `scripts/reclassify_positions.py` — full read; CLI skeleton, COMMIT batching pattern, VACUUM call
- `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` — exact Alembic recipe for drop+recreate with postgresql_include
- `tests/test_endgame_repository.py`, `tests/test_aggregation_sanity.py` — existing tests that require update
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md` — all locked decisions
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md` — 16 requirements, acceptance criteria

### Secondary (MEDIUM confidence)

- `reports/conv-recov-validation-2026-05-02.md` — benchmark population sizes and eval coverage (22.4% of qualifying games have eval at span entry)
- `pyproject.toml` — dependency versions confirmed (chess>=1.10.0, sqlalchemy>=2.0.0, pytest-asyncio>=0.23.0)

### Tertiary (LOW confidence / ASSUMED)

- Depth-15 wall-clock estimate (~50-100ms) — based on general Stockfish knowledge, unverified on this hardware
- AVX2 support on Hetzner CX32 — based on Intel Skylake typical availability, not verified on this specific VM

---

## Metadata

**Confidence breakdown:**
- Engine wrapper API: HIGH — verified directly from installed chess package source
- Repository refactor scope: HIGH — full read of endgame_repository.py and endgame_service.py
- Index migration recipe: HIGH — exact precedent in existing Alembic migration
- Backfill SAN replay: HIGH — mirrors existing reclassify_positions.py pattern
- Performance estimates: LOW — untested on target hardware; instrumentation required

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (stable ecosystem; chess/SQLAlchemy APIs don't change fast)
