# Phase 174: Backend Maia Inference + Best-Move Storage - Pattern Map

**Mapped:** 2026-07-16
**Files analyzed:** 11 (new + modified)
**Analogs found:** 9 / 11 (2 have no direct analog — encoding port, uv group isolation — RESEARCH.md's code examples substitute)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/maia_encoding.py` (NEW) | utility | transform | `frontend/src/lib/maiaEncoding.ts` (port target, not a backend analog) | no-backend-analog |
| `app/services/maia_engine.py` (NEW) | service | request-response (lazy singleton) | `app/services/engine.py:220-241` (`start_engine`/`stop_engine`) | exact (lifecycle shape) |
| `app/models/game_best_move.py` (NEW) | model | CRUD (sibling table) | `app/models/game_flaw.py` + `app/models/bot_game_settings.py` | exact (combine both) |
| `alembic/versions/<ts>_add_game_best_moves_table.py` (NEW) | migration | batch | most recent migration under `alembic/versions/` adding a sibling table (find latest via `ls -t`) | role-match |
| `app/main.py` (MODIFIED, ~93-96, 139-140) | config/lifespan | event-driven | itself — extend existing lifespan block | exact |
| `app/services/eval_apply.py` (MODIFIED, ~1208-1316, ~1687) | service | event-driven (write-session pipeline stage) | `_build_flaw_multipv2_blobs` (same file, session-closed-then-gather pattern) | exact |
| `pyproject.toml` / `Dockerfile` / `Dockerfile.worker` (MODIFIED) | config | build | itself — `[dependency-groups].dev` is the existing group-isolation precedent | role-match |
| `tests/services/test_maia_encoding.py` (NEW) | test | unit | `tests/services/test_eval_utils.py` (pure-math module test) | exact |
| `tests/services/test_maia_engine.py` (NEW) | test | unit | pattern of `tests/services/test_engine.py` if present, else lifecycle-guard unit tests | role-match |
| `tests/models/test_game_best_move.py` (NEW) | test | integration (DB) | `tests/models/test_game_flaw.py` or equivalent sibling-table constraint test | role-match |
| `scripts/maia_parity_spike.py` (NEW) | utility | batch (standalone script) | no analog — greenfield spike script; structure per RESEARCH.md Code Examples | no-analog |

## Pattern Assignments

### `app/services/maia_engine.py` (service, singleton lifecycle)

**Analog:** `app/services/engine.py:220-241`

**Core lifecycle pattern to mirror** (lines 220-241):
```python
async def start_engine() -> None:
    """Start the module-level engine pool. Idempotent: a second call is a no-op."""
    global _pool
    if _pool is not None:
        return
    pool = EnginePool(size=_read_pool_size())
    await pool.start()
    _pool = pool


async def stop_engine() -> None:
    """Stop the module-level engine pool. Safe to call without start (no-op)."""
    global _pool
    if _pool is None:
        return
    try:
        await _pool.stop()
    finally:
        _pool = None
```

**Adaptation for Maia (D-03a no-op guard when onnxruntime absent)** — per RESEARCH.md:
```python
_session: "onnxruntime.InferenceSession | None" = None  # type: ignore[name-defined]

async def start_maia() -> None:
    global _session
    try:
        import onnxruntime  # deferred import — group-isolated, may not be installed (D-03a)
    except ImportError:
        logger.info("maia_engine: onnxruntime not installed — Maia inference disabled")
        return
    if _session is not None:
        return
    _session = onnxruntime.InferenceSession(_MODEL_PATH, providers=["CPUExecutionProvider"])

async def stop_maia() -> None:
    global _session
    _session = None
```

Note the difference from `engine.py`: `start_engine`/`stop_engine` never guard against a missing
binary (Stockfish is a hard dependency); `start_maia` MUST additionally guard the import itself,
not just the idempotency check. Keep both guards.

---

### `app/main.py` (lifespan, MODIFIED)

**Analog:** itself, lines ~93-96 and ~139-140 (existing `start_engine`/`stop_engine` calls)

**Insertion pattern**:
```python
# ~line 96, alongside existing Phase 78 D-02 comment block
await start_engine()
await start_maia()   # NEW — no-op if onnxruntime absent (D-03a)
...
# ~line 140, in the finally block, AFTER stop_engine (no cross-dependency, order flexible)
finally:
    await stop_engine()
    await stop_maia()  # NEW
```
Follow the existing comment convention in this file (each addition gets a `# Phase N / D-xx:` comment
explaining why it's positioned where it is — see the block from line 82 onward for the established
style, e.g. `# Phase 78 D-02: long-lived Stockfish UCI process...`).

---

### `app/models/game_best_move.py` (NEW model, sibling table)

**Analogs:** `app/models/game_flaw.py` (composite-key / FK-cascade sibling-table shape) +
`app/models/bot_game_settings.py` (`CheckConstraint` + `REAL` column pattern)

**Imports pattern** (from `bot_game_settings.py` lines 1-13):
```python
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
```

**Composite natural-key + FK-cascade pattern** (from `game_flaw.py` lines 21-40):
```python
class GameFlaw(Base):
    __tablename__ = "game_flaws"
    __table_args__ = (
        Index("ix_game_flaws_user_severity", "user_id", "severity"),
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True, index=True,
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
```

**CheckConstraint pattern** (from `bot_game_settings.py` lines 19-24):
```python
__table_args__ = (
    CheckConstraint(
        "rating_source IN ('lichess', 'chesscom', 'blended')",
        name="ck_bot_game_settings_rating_source",
    ),
)
```

**Column-type convention** (from `game_position.py` lines 159-172, `eval_cp`/`best_move`) — mirror
for `best_cp`/`second_cp`: raw `SmallInteger` centipawns, never a pre-converted float (D-05):
```python
eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
eval_mate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
best_move: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
```

**RESEARCH.md's own combined sketch** (GEMS-01) — use this as the starting skeleton, note it uses
`UniqueConstraint` + a single `game_id` PK, whereas `game_flaws` uses a *composite* PK
(`user_id, game_id, ply`) — decide per Claude's Discretion whether `game_best_moves` needs
`user_id` in the key at all (best-move candidacy is a property of the position, not the user, unlike
a flaw which is inherently a specific user's mistake — likely `(game_id, ply)` suffices, no `user_id`):
```python
class GameBestMove(Base):
    __tablename__ = "game_best_moves"
    __table_args__ = (
        UniqueConstraint("game_id", "ply", name="uq_game_best_moves_game_ply"),
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    maia_prob: Mapped[float] = mapped_column(REAL, nullable=False)
    best_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    best_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

---

### `app/services/eval_apply.py` (MODIFIED — candidate-row builder)

**Analog:** `_build_flaw_multipv2_blobs` (same file, lines 1208-1316) — the session-closed-then-gather
pattern is a hard project rule (CLAUDE.md: never `asyncio.gather` on an open `AsyncSession`).

**Core pattern to mirror** (lines 1229-1233, 1273-1280):
```python
async with async_session_maker() as session:
    flaw_result = await _classify_with_overlay(
        game_id, session, overlay=True, pos_eval=pos_eval
    )
if flaw_result is None:
    return {}
# session closed — now safe to gather engine calls with no open AsyncSession
...
continuation_results = await asyncio.gather(
    *(engine_service.evaluate_nodes_multipv2(b) for b in gather_boards)
)
```

**Insertion point:** call the new candidate-row builder from/near `apply_full_eval` (line ~1687),
same shared write-session body both `_full_drain_tick` (local) and `_apply_atomic_submit` (remote)
funnel through — this is what guarantees "every newly analyzed game" without touching worker code.

**Pitfall 1 gotcha (must handle):** `second_best_map` is populated only for the local-drain lane and
for the remote worker's flaw-hinted plies — NEVER for non-flaw "played == best" plies from the
remote-worker lane, which is exactly GEMS-02's target population. For any out-of-book,
played==best-move ply lacking a second-best value, issue a targeted extra
`engine_service.evaluate_nodes_multipv2(board)` call (same pool, same gather-after-session-close
shape) before assembling the candidate row. Do not assume full coverage.

---

### `app/services/eval_utils.py` (REUSE verbatim, do not modify)

**Reuse pattern** (lines 34-63) — the cp→ES sigmoid GEMS-07's query-time classification and D-05a's
write-time candidate gate both need:
```python
LICHESS_K: float = 0.00368208

def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float:
    sign = 1 if user_color == "white" else -1
    return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))
```
Mate handling: mirror `flaws_service.py`'s `MATE_CP_EQUIVALENT = 1000` "Option B" convention (map
mate to ±1000cp BEFORE the sigmoid), not `eval_mate_to_expected_score` (hard 0/1 — wrong for
per-ply drop math).

---

### Dependency isolation (`pyproject.toml`, `Dockerfile`, `Dockerfile.worker`)

**Analog:** existing `[dependency-groups]` block (`pyproject.toml` lines 24-29):
```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    ...
]
```
Add a new sibling group (name per Claude's Discretion, e.g. `maia-inference`):
```toml
[dependency-groups]
maia-inference = [
    "onnxruntime==1.20.1",
    "numpy",
]
```

**Docker install pattern** — both `Dockerfile` and `Dockerfile.worker` currently run identical
`uv sync --locked --no-dev` (confirmed: `Dockerfile:15`, `Dockerfile.worker:31`) with no
`--group`/`--extra` flag, so a new opt-in group is naturally EXCLUDED from both images unless the
backend `Dockerfile` explicitly adds `--group maia-inference` to its `uv sync` invocation. Leave
`Dockerfile.worker` untouched (GEMS-06 hard requirement — worker image must stay lean).

---

## Shared Patterns

### Engine process lifecycle (start/stop singleton, no-op guard)
**Source:** `app/services/engine.py:220-241`, wired at `app/main.py:93-96,139-140`
**Apply to:** `app/services/maia_engine.py`
Idempotent global-singleton start/stop; extend with an import-guard for D-03a (onnxruntime may be
absent by design in worker/lean images).

### Session-closed-then-gather (never `asyncio.gather` on an open `AsyncSession`)
**Source:** `app/services/eval_apply.py:1208-1316` (`_build_flaw_multipv2_blobs`)
**Apply to:** the new candidate-row builder in `eval_apply.py`, and any Pitfall-1 targeted extra
Stockfish call
This is a CLAUDE.md hard rule, not just a local convention — close the read session before any
`asyncio.gather` over engine/inference calls, then open a write session late to persist results.

### cp→expected-score sigmoid (single source of truth)
**Source:** `app/services/eval_utils.py:34-63`
**Apply to:** both the write-time candidate gate (D-05a) and any query-time classification helper
(GEMS-07, though the read endpoint itself is out of scope for Phase 174)
Never re-derive; import `eval_cp_to_expected_score` directly. Mate handling uses
`flaws_service.py`'s `MATE_CP_EQUIVALENT = 1000` convention, not `eval_mate_to_expected_score`.

### Sibling-table model shape (composite key / FK-cascade / CheckConstraint)
**Source:** `app/models/game_flaw.py:21-40` + `app/models/bot_game_settings.py:16-24`
**Apply to:** `app/models/game_best_move.py`
Mandatory `ForeignKey(..., ondelete="CASCADE")` on any `games.id` reference (CLAUDE.md DB rule);
`SmallInteger` for cp columns, `REAL` for `maia_prob`; TEXT+CHECK (not native enum) if a mate-sign
or similar low-cardinality column is added.

### uv dependency-group isolation
**Source:** `pyproject.toml:24-29` (`[dependency-groups].dev`), `Dockerfile:15` vs `Dockerfile.worker:31`
**Apply to:** the new `onnxruntime`/`numpy` group (GEMS-06)
A new group is excluded from `uv sync --locked --no-dev` unless explicitly requested with `--group`;
only the backend `Dockerfile` should add that flag.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/services/maia_encoding.py` | utility | transform | No backend precedent for ONNX board-tensor encoding; port target is `frontend/src/lib/maiaEncoding.ts` (TS, not a backend analog) plus the verified prior Python repro referenced in `.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md` (recover/reconstruct as starting point per RESEARCH.md Assumption A1) |
| `scripts/maia_parity_spike.py` | utility (script) | batch | Greenfield spike script, no structural analog in `scripts/`; nearest sibling in spirit is Phase 168's Node-based Maia feasibility spike (different runtime) — use RESEARCH.md's Code Examples section for the fixture-corpus + tier-tolerance shape |

## Metadata

**Analog search scope:** `app/services/`, `app/models/`, `app/main.py`, `pyproject.toml`,
`Dockerfile`, `Dockerfile.worker`, `frontend/src/lib/maiaEncoding.ts`
**Files scanned:** `app/services/engine.py`, `app/main.py`, `app/models/game_flaw.py`,
`app/models/bot_game_settings.py`, `app/models/game_position.py`, `app/services/eval_apply.py`,
`app/services/eval_utils.py`, `pyproject.toml`, `Dockerfile`, `Dockerfile.worker`
**Pattern extraction date:** 2026-07-16
