# Stack Research

**Domain:** Chess tactic analysis — MultiPV=2 engine pass + JSONB persistence (v1.30 Forcing-Line Gate)
**Researched:** 2026-06-29
**Confidence:** HIGH (both topics verified against official docs + existing codebase patterns)

---

## Context

This is a **subsequent-milestone stack note**, not a greenfield survey. The full backend stack
(FastAPI / Python 3.13 / SQLAlchemy 2.x async + asyncpg / PostgreSQL 18 / python-chess 1.11.x /
Stockfish 18 via `EnginePool`) is already built and shipped. The scope here is exactly two new
mechanics: running Stockfish with `multipv=2` and storing the results as JSONB on `game_flaws`.

**Verdict up front: no new PyPI dependency is required.**

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-chess | 1.11.x (installed) | MultiPV=2 analysis via `engine.analyse(..., multipv=2)` | Already ships the multipv overload; zero upgrade needed |
| SQLAlchemy `dialects.postgresql.JSONB` | 2.x (installed) | JSONB column type for `allowed_pv_lines` / `missed_pv_lines` | Already used in `llm_log.py`; asyncpg codec wired automatically by the dialect |
| asyncpg | installed | Async PostgreSQL driver | Auto-configures json.loads/dumps as JSONB codec; no manual `set_type_codec()` needed |
| PostgreSQL 18 | 18 (prod) | JSONB storage + TOAST | JSONB is a first-class type; TOAST is automatic for large values (not triggered at our blob size) |

### Supporting Libraries

None new. All mechanics are in already-installed packages.

---

## python-chess MultiPV=2 — Exact API

### `engine.analyse()` with `multipv=2`

The python-chess `UciProtocol.analyse()` method has a typed overload that changes its return
type based on whether `multipv` is passed:

```python
# Without multipv — returns a single InfoDict (existing usage in engine.py)
info: chess.engine.InfoDict = await protocol.analyse(board, limit)

# With multipv=2 — returns List[InfoDict], best-first
info_list: list[chess.engine.InfoDict] = await protocol.analyse(board, limit, multipv=2)
```

The overload signature is (from python-chess 1.11.2 docs):

```python
async def analyse(
    self,
    board: Board,
    limit: Limit,
    *,
    multipv: int,
    game: object = None,
    info: Info = INFO_ALL,
    root_moves: Iterable[Move] | None = None,
    options: Mapping[str, str | int | bool | None] = {},
) -> List[InfoDict]: ...
```

Internally, when `multipv` is an int, `analyse()` returns `analysis.multipv` (a list) rather
than `analysis.info` (a single dict).

### Ordering and Access

`info_list[0]` is the best line (multipv rank 1), `info_list[1]` is the second-best (rank 2).
The `"multipv"` key inside each `InfoDict` holds the 1-based rank integer.

**Edge case: if the position has only one legal move, the list has 1 element.** Callers must
guard `len(info_list) > 1` before accessing `info_list[1]`. This naturally handles terminal
positions and near-terminal forced mates — the gate logic should treat a missing second line as
"no second-best exists" (i.e. the move is trivially only-move).

### Extracting Scores and Moves

The `PovScore` interface is identical to what `_score_to_cp_mate()` and `_pv_to_best_move()`
already use. For the MultiPV=2 case:

```python
info_list = await protocol.analyse(board, limit, multipv=2)

# Best line (always present if engine returned anything)
best = info_list[0]
best_white: chess.engine.Score = best["score"].white()   # white-perspective Score
best_cp: int | None = best_white.score(mate_score=None)  # None when it is a mate score
best_mate: int | None = best_white.mate()                # None when it is a cp score
best_pv = best.get("pv") or []
best_move_uci: str | None = best_pv[0].uci() if best_pv else None

# Second-best line (may not exist)
if len(info_list) > 1:
    second = info_list[1]
    second_white = second["score"].white()
    second_cp = second_white.score(mate_score=None)
    second_mate = second_white.mate()
    second_pv = second.get("pv") or []
    second_move_uci: str | None = second_pv[0].uci() if second_pv else None
else:
    second_cp = second_mate = second_move_uci = None
```

The `LICHESS_K` sigmoid in `eval_utils.py` applies to both best and second evals identically.
The gate formula `p(best) - p(second) > 0.35` (from the design note) computes:

```python
from app.services.eval_utils import eval_cp_to_expected_score

# White-perspective margin: "user_color" convention is not relevant here because both
# sides of the subtraction share the same perspective (white). Pick "white" for both.
p_best = eval_cp_to_expected_score(best_cp, "white")      # works for cp scores
p_second = eval_cp_to_expected_score(second_cp, "white")
is_only_move = (p_best - p_second) > 0.35
```

Mate scores must be mapped first via `eval_mate_to_expected_score()` if `best_cp is None` or
`second_cp is None`. The design note's blobs store raw cp/mate, so the gate can re-derive this
offline without the engine.

### Integration with Existing EnginePool

`EnginePool._analyse_with_pv()` currently calls `protocol.analyse(board, limit)` (no `multipv`)
and returns a single `InfoDict`. Passing `multipv=2` changes the return type to `List[InfoDict]`
— this is not a runtime surprise but a typed overload resolution. The existing method cannot be
repurposed in-place; it needs a parallel sibling.

**Required addition — new EnginePool method:**

```python
async def _analyse_multipv2(
    self,
    board: chess.Board,
    limit: chess.engine.Limit,
    timeout: float,
) -> list[chess.engine.InfoDict] | None:
    """Worker acquisition / analyse / restart path returning List[InfoDict] for multipv=2.

    Returns None on timeout/crash (same failure semantics as _analyse_with_pv).
    Caller must handle len(result) < 2 (only one legal move in position).
    """
    if not self._started:
        return None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None
        try:
            info_list = await asyncio.wait_for(
                protocol.analyse(board, limit, multipv=2),
                timeout=timeout,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await self._restart_worker(idx)
            return None
        return info_list
    finally:
        self._available.put_nowait(idx)
```

The public module-level wrapper follows the pattern of `evaluate_nodes_with_pv()`:

```python
async def evaluate_nodes_multipv2(
    board: chess.Board,
) -> list[chess.engine.InfoDict] | None:
    """Evaluate at 1M nodes with multipv=2. Returns List[InfoDict] (best first) or None."""
    if _pool is None:
        return None
    return await _pool._analyse_multipv2(
        board, chess.engine.Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S
    )
```

**Existing `_NODES_BUDGET` (1M nodes) and `_NODES_TIMEOUT_S` (5.0s) are the right starting
budget.** MultiPV=2 costs roughly 1.5–2x vs MultiPV=1 at the same node count, but the
pv_lines pass runs only over flaw positions along a ~6–12-ply line — a tiny fraction of a
full-game pass. Tune the node budget empirically during implementation; 1M nodes is the correct
starting point.

**No changes to UCI `Hash` or `Threads` configuration.** The existing 32 MB Hash and 1 Thread
per worker are fine for the second-line ordering stability needed at this node budget.

---

## SQLAlchemy 2.x JSONB — Exact Declaration

### Column Declaration

Follow the existing `llm_log.py` pattern exactly. The only difference is the Python type
annotation: blobs are JSON arrays (not objects), so `list[Any]` instead of `dict`:

```python
# app/models/game_flaw.py — additions

from typing import Any                            # add to imports if not present
from sqlalchemy.dialects.postgresql import JSONB  # same import as llm_log.py

# Inside GameFlaw class:
allowed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
missed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
```

The blob shape per the design note (one element per PV node, white-perspective cp):

```python
# Python value written to the column:
[
    {"b": 350, "bm": None, "s": 280, "sm": None, "su": "e2e4"},
    {"b": 320, "bm": None, "s": 250, "sm": None, "su": "d2d4"},
    # ... up to 12 nodes
]
```

For ty compliance, `list[Any]` is the correct annotation because the inner dict structure
varies (nullable fields). A stricter `list[dict[str, int | str | None]]` is valid too if ty
can infer it — use whichever passes `uv run ty check app/ tests/` with zero errors.

### MutableDict — Not Needed

`MutableDict.as_mutable(JSONB)` emits SQLAlchemy change events when a dict is mutated
**in-place between two flushes** (e.g. `flaw.col["key"] = val` without reassigning `flaw.col`).
For write-once blobs:

- During backfill: the entire column is assigned once (`flaw.allowed_pv_lines = [...]`).
- After storage: the column is read by the re-tagger but never mutated in-place.

Plain `mapped_column(JSONB, nullable=True)` is sufficient and avoids mutation-tracking overhead.
Do not add `MutableDict`. The existing `llm_log.py` columns (`filter_context`, `response_json`)
confirm this — neither uses `MutableDict`.

### asyncpg Codec — Automatic

SQLAlchemy's asyncpg dialect (already active via the project's
`create_async_engine("postgresql+asyncpg://...")` call) auto-registers `json.loads`/`json.dumps`
as the JSONB codec for every connection via the dialect's `on_connect()` hook. No manual
`connection.set_type_codec()` call is needed in the project. A Python `list[dict]` is
transparently serialized to a JSONB array on write and deserialized back to `list[dict]` on
read. This is confirmed by the working `filter_context` and `response_json` JSONB columns in
`llm_log.py`.

### TOAST Behavior

PostgreSQL automatically stores JSONB values out-of-line (TOAST) only after compression if the
compressed result exceeds ~2KB (~one quarter of an 8KB page). A 12-node pv_lines blob:

```
[{"b": 350, "bm": null, "s": 280, "sm": null, "su": "e2e4"}, ...]
```

Each node is roughly 50 bytes; 12 nodes = approximately 600 bytes. **TOAST does not apply at
this size.** Blobs are stored inline on the `game_flaws` page.

Even if a future blob exceeded the threshold and was TOASTed, PostgreSQL fetches TOAST values
only when explicitly SELECTed. Queries scanning `game_flaws` without selecting the pv_lines
columns (e.g. flaw-comparison aggregation, tactic-stats queries) are unaffected — TOAST
deferred loading is automatic and requires no application-side configuration.

**Starting inline is correct.** The design note's "sidecar table fallback" (`game_flaw_pv_lines`
FK + two blobs) is not needed at launch. Defer unless profiling shows `game_flaws` page bloat
affecting aggregation queries that do not select the JSONB columns.

---

## Alembic Migration

Two nullable JSONB columns, one migration. Generated output will be:

```python
op.add_column("game_flaws", sa.Column("allowed_pv_lines", postgresql.JSONB(), nullable=True))
op.add_column("game_flaws", sa.Column("missed_pv_lines", postgresql.JSONB(), nullable=True))
```

No index on either column. The re-tagger fetches batches of `game_flaws` rows by `(user_id,
game_id, ply)` — an existing primary-key scan — and processes the blobs in Python. No SQL
filtering on JSONB content is required.

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| New PyPI package | python-chess `multipv` and SQLAlchemy `JSONB` already ship in installed versions |
| `MutableDict.as_mutable(JSONB)` | Write-once blobs; plain `mapped_column(JSONB)` is correct and matches existing `llm_log.py` pattern |
| Manual `set_type_codec()` / asyncpg codec setup | SQLAlchemy asyncpg dialect wires json.loads/dumps automatically |
| TOAST configuration | Automatic; blobs are ~600 bytes, well below the ~2KB threshold |
| `game_flaw_pv_lines` sidecar table | Not warranted at launch; start inline; revisit only if page bloat is observed in production |
| Increased `_NODES_BUDGET` for the multipv pass | Start at existing 1M nodes; tune empirically during implementation |
| Changes to `_HASH_MB` or `_THREADS` UCI settings | Same 32 MB / 1 thread per worker is fine for multipv ordering stability |
| JSONB GIN index on pv_lines columns | No SQL filtering on pv_lines content; the re-tagger reads all rows and processes in Python |

---

## Sources

- [python-chess 1.11.2 engine docs](https://python-chess.readthedocs.io/en/latest/engine.html) — `analyse()` overloads, multipv return type `List[InfoDict]`, PovScore `.white()` / `.score()` / `.mate()` API (MEDIUM confidence, websearch)
- [python-chess _modules/chess/engine.html](https://python-chess.readthedocs.io/en/latest/_modules/chess/engine.html) — implementation: `analysis.multipv` returned when multipv is int; list ordered best-first by rank (MEDIUM confidence, websearch)
- [SQLAlchemy discussion #11318 — JSONB typing](https://github.com/sqlalchemy/sqlalchemy/discussions/11318) — maintainer confirms `Mapped[dict | None]` correct; JSONB class used directly as column type arg (MEDIUM confidence, websearch)
- [asyncpg + SQLAlchemy JSONB codec](https://github.com/sqlalchemy/sqlalchemy/issues/5584) — SQLAlchemy asyncpg dialect sets json.loads as default JSONB decoder automatically (MEDIUM confidence, websearch)
- `app/models/llm_log.py` (codebase) — existing `from sqlalchemy.dialects.postgresql import JSONB` import, `Mapped[dict | None]` annotation, no MutableDict (HIGH confidence, verified in source)
- `app/services/engine.py` (codebase) — `_analyse_with_pv()` / `evaluate_nodes_with_pv()` patterns; `_NODES_BUDGET` / `_NODES_TIMEOUT_S` constants; `_score_to_cp_mate()` / `_pv_to_best_move()` helpers (HIGH confidence, verified in source)

---

*Stack research for: FlawChess v1.30 Forcing-Line Tactic Gate — MultiPV=2 + JSONB storage*
*Researched: 2026-06-29*
