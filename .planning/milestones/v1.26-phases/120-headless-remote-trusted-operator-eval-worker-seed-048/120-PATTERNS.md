# Phase 120: Headless Remote Trusted-Operator Eval Worker — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/routers/eval_remote.py` | router | request-response | `app/routers/admin.py` | role-match (thin router, Depends auth, service call) |
| `app/schemas/eval_remote.py` | schema | transform | `app/schemas/imports.py` | exact |
| `app/core/config.py` (extend) | config | — | `app/core/config.py` (self) | exact — add two fields |
| `app/services/engine.py` (extend) | service/utility | request-response | `app/services/engine.py` (self) | exact — add one helper |
| `scripts/remote_eval_worker.py` | CLI worker | request-response (HTTP) + batch | `scripts/backfill_eval.py` | role-match (EnginePool + asyncio + argparse) |
| `tests/routers/test_eval_remote_router.py` | test | CRUD | `tests/routers/test_imports_tier1_enqueue.py` | exact (ASGI transport, operator-header, seeded games) |
| `app/main.py` (extend) | config | — | `app/main.py` (self) | exact — add one import + include_router call |

---

## Pattern Assignments

### `app/routers/eval_remote.py` (router, request-response)

**Analog:** `app/routers/admin.py`

**Imports pattern** (admin.py lines 1-18):
```python
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.config import settings
from app.schemas.eval_remote import LeaseResponse, SubmitRequest, SubmitResponse
from app.services.eval_drain import (
    _collect_full_ply_targets,
    _apply_full_eval_results,
    _classify_and_fill_oracle,
    _mark_full_evals_completed,
    _mark_full_pv_completed,
    _signal_flaw_completion,
    MAX_EVAL_ATTEMPTS,
)
from app.services.eval_queue_service import _claim_tier3_derived
```

**Router declaration** (admin.py line 20):
```python
router = APIRouter(prefix="/eval/remote", tags=["eval-remote"])
```

**Auth dependency pattern** — new for this router (no existing analog; defined inline per RESEARCH.md Q5):
```python
import hmac
from fastapi import Header

async def require_operator_token(
    x_operator_token: Annotated[str, Header(alias="X-Operator-Token")],
) -> None:
    configured = settings.EVAL_OPERATOR_TOKEN
    if not configured:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Operator token not configured on server")
    if not hmac.compare_digest(configured, x_operator_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid operator token")
```

**Thin endpoint pattern** (admin.py lines 22-47 — validate, auth dep, service call, shape response):
```python
@router.post("/lease", response_model=LeaseResponse)
async def lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
) -> LeaseResponse:
    ...

@router.post("/submit", response_model=SubmitResponse)
async def submit_eval(
    body: SubmitRequest,
    _auth: Annotated[None, Depends(require_operator_token)],
) -> SubmitResponse:
    ...
```

**Session discipline pattern** (matches eval_drain.py `_full_drain_tick` — documented in RESEARCH.md pitfall 5):
- Open a SHORT read session, load data, CLOSE.
- Do CPU/logic work with no session open.
- Open ONE write session for the entire atomic game write, commit, CLOSE.
- Never pass a session between the read and write phases.

**Sentry pattern for unexpected errors** (CLAUDE.md + RESEARCH.md Q10 security):
```python
import sentry_sdk

# In the cap-reached path of submit:
sentry_sdk.set_context("eval", {"game_id": body.game_id, "hole_count": failed_ply_count})
sentry_sdk.set_tag("source", "remote_eval_worker")
sentry_sdk.capture_message(
    "remote-worker: stamping complete after MAX_EVAL_ATTEMPTS with residual holes",
    level="warning",
)
```

**Error handling pattern** (admin.py lines 68-73 — HTTPException for expected conditions; do NOT capture to Sentry):
```python
if game is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
```

---

### `app/schemas/eval_remote.py` (schema, transform)

**Analog:** `app/schemas/imports.py`

**Schema file pattern** (imports.py lines 1-8):
```python
"""Pydantic v2 schemas for the eval remote API endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
```

**Response model pattern** (imports.py lines 13-16, 47-56 — concise fields, docstring, no @classmethod unless needed):
```python
class LeasePosition(BaseModel):
    ply: int
    fen: str           # board.fen() — full FEN including turn, castling, en passant
    is_terminal: bool  # True for the terminal eval-donor

class LeaseResponse(BaseModel):
    game_id: int
    user_id: int            # echoed back so worker includes in SubmitRequest
    is_lichess_eval_game: bool
    positions: list[LeasePosition]
    leased_at: datetime

class SubmitEval(BaseModel):
    ply: int
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None   # UCI string
    pv: str | None          # space-joined UCI, up to 12 plies

class SubmitRequest(BaseModel):
    game_id: int
    user_id: int            # from LeaseResponse; avoids extra DB query in submit
    sf_version: str         # e.g. "Stockfish 18" — for D-5 version gate
    evals: list[SubmitEval]

class SubmitResponse(BaseModel):
    game_id: int
    stamp_complete: bool
    failed_ply_count: int
```

---

### `app/core/config.py` (extend — add two fields)

**Analog:** `app/core/config.py` itself (self-extension)

**Pattern for new optional settings** (config.py lines 68-74 — comment explains default and prod override):
```python
# Automatic background full-eval toggle (Phase 117). When False, the tier-3
# idle-backlog derived pick is suppressed ...
# Default False (safe for dev/CI ...). Prod opts in explicitly via its .env.
EVAL_AUTO_DRAIN_ENABLED: bool = False
```

**New fields to add** (after `EVAL_AUTO_DRAIN_ENABLED`, before `model_config`):
```python
# Operator token for the remote eval worker (Phase 120 SEED-048).
# Empty string = endpoints return 403 (disabled in dev/CI).
# Prod sets a strong random secret in .env.
EVAL_OPERATOR_TOKEN: str = ""

# Expected Stockfish version string (Phase 120 D-5 version gate).
# e.g. "Stockfish 18". Empty = any version accepted (dev/CI).
# Prod sets to the version installed on the server.
EXPECTED_SF_VERSION: str = ""
```

---

### `app/services/engine.py` (extend — add `get_stockfish_version()`)

**Analog:** `app/services/engine.py` itself (self-extension)

**Pattern for standalone async helper functions** in the engine module (RESEARCH.md Q7):
```python
async def get_stockfish_version() -> str:
    """Read Stockfish version string via UCI handshake.

    Returns e.g. 'Stockfish 18'. Called once by the remote worker CLI at
    startup to populate sf_version in SubmitRequest (Phase 120 D-5).
    Opens and immediately quits a single UCI connection; does not use EnginePool.
    """
    transport, protocol = await chess.engine.popen_uci(
        _STOCKFISH_PATH, **_engine_popen_kwargs()
    )
    version = str(protocol.id.get("name", "unknown"))
    await protocol.quit()
    return version
```

Note: `_STOCKFISH_PATH` and `_engine_popen_kwargs()` are module-level in `engine.py`. Import nothing extra; add the function near the bottom of the module before `EnginePool`.

---

### `scripts/remote_eval_worker.py` (CLI worker, request-response + batch)

**Analog:** `scripts/backfill_eval.py` (primary) and `scripts/resweep_holed_games.py` (path bootstrap)

**Path bootstrap pattern** (resweep_holed_games.py lines 23-24):
```python
import sys
from pathlib import Path

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

**Model registry import pattern** (resweep_holed_games.py lines 33-35 — needed when ORM models have FK relationships):
```python
import app.models.oauth_account  # noqa: E402, F401
import app.models.user  # noqa: E402, F401
```

**App import block after bootstrap** (backfill_eval.py lines 75-81 — noqa comments required):
```python
from app.core.config import settings  # noqa: E402
from app.services.engine import EnginePool, get_stockfish_version  # noqa: E402
```

**Logging helper pattern** (backfill_eval.py lines 113-116):
```python
def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
```

**EnginePool startup/teardown pattern** (backfill_eval.py — EnginePool used with async context):
```python
pool = EnginePool(workers)
await pool.start()
try:
    sf_version = await get_stockfish_version()
    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"X-Operator-Token": token},
        timeout=30.0,
    ) as client:
        await _run_loop(client, pool, sf_version, idle_sleep, dry_run)
finally:
    await pool.stop()
```

**Worker eval fan-out pattern** (RESEARCH.md Q8 — asyncio.gather across the pool, NO open session):
```python
async def _eval_positions(
    pool: EnginePool, positions: list[dict]
) -> list[dict]:
    boards = [chess.Board(pos["fen"]) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))
    return [
        {"ply": pos["ply"], "eval_cp": r[0], "eval_mate": r[1], "best_move": r[2], "pv": r[3]}
        for pos, r in zip(positions, results)
    ]
```

**Main entry point pattern** (backfill_eval.py lines 879-903):
```python
async def main() -> None:
    args = parse_args()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _log(f"Starting remote eval worker: base_url={args.base_url} workers={args.workers}")
    await run_worker(
        base_url=args.base_url,
        token=args.token,
        workers=args.workers,
        idle_sleep=args.idle_sleep,
        dry_run=args.dry_run,
        loop=not args.once,
    )
    _log("Done.")

if __name__ == "__main__":
    asyncio.run(main())
```

**argparse pattern** (backfill_eval.py lines 830-876 — constants for defaults, no magic numbers):
```python
DEFAULT_WORKERS = 1
DEFAULT_IDLE_SLEEP = 5.0

parser = argparse.ArgumentParser(description="...")
parser.add_argument("--base-url", required=True, help="e.g. https://flawchess.com")
parser.add_argument("--token", default=os.environ.get("EVAL_OPERATOR_TOKEN", ""),
                    help="Operator token (or set EVAL_OPERATOR_TOKEN env var)")
parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
parser.add_argument("--idle-sleep", type=float, default=DEFAULT_IDLE_SLEEP,
                    help="Seconds between empty-queue polls")
parser.add_argument("--dry-run", action="store_true",
                    help="Lease only, print positions, do not submit")
parser.add_argument("--once", action="store_true",
                    help="Process one game then exit (default: loop forever)")
```

---

### `tests/routers/test_eval_remote_router.py` (test, request-response)

**Analog:** `tests/routers/test_imports_tier1_enqueue.py`

**ASGI transport pattern** (test_imports_tier1_enqueue.py lines 43-60):
```python
async with httpx.AsyncClient(
    transport=httpx.ASGITransport(app=app), base_url="http://test"
) as client:
    response = await client.post(
        "/api/eval/remote/lease",
        headers={"X-Operator-Token": "test-secret"},
    )
```

**Operator token header pattern** (RESEARCH.md Q5 — for tests, monkeypatch settings):
```python
@pytest.mark.asyncio
async def test_lease_requires_operator_token(monkeypatch) -> None:
    """No token → 403 (token not configured on server)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/eval/remote/lease")
    assert response.status_code == 403
```

**Monkeypatch for settings** (RESEARCH.md Q9 — patch the settings object directly):
```python
monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "test-secret-123")
monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "Stockfish 18")
```

**Game seed pattern** (test_imports_tier1_enqueue.py lines 83-89 — committed session, not rollback):
```python
async def _seed_game(test_engine, game: Game) -> int:
    """Insert a game via committed session and return the assigned id."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        session.add(game)
        await session.commit()
        return int(game.id)  # type: ignore[arg-type]
```

**Session maker monkeypatch** (RESEARCH.md Q9 — route app session to test DB):
```python
from app.core.database import async_session_maker as _app_session_maker
import app.routers.eval_remote as eval_remote_module

monkeypatch.setattr(
    eval_remote_module,
    "async_session_maker",
    async_sessionmaker(test_engine, expire_on_commit=False),
)
```

**Cleanup pattern** (test_imports_tier1_enqueue.py lines 102-109):
```python
async def _delete_seeded_games(test_engine, user_id: int) -> None:
    from sqlalchemy import delete
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.user_id == user_id))
        await session.commit()
```

---

### `app/main.py` (extend — register new router)

**Analog:** `app/main.py` itself (self-extension)

**Router import pattern** (main.py lines 21-26):
```python
from app.routers.admin import router as admin_router
# ... add:
from app.routers.eval_remote import router as eval_remote_router
```

**Router registration pattern** — find the block of `app.include_router(...)` calls and add:
```python
app.include_router(eval_remote_router, prefix="/api")
# Results in routes: /api/eval/remote/lease, /api/eval/remote/submit
```

---

## Shared Patterns

### Operator Token Auth
**Source:** `app/routers/eval_remote.py` (new — no existing project analog)
**Apply to:** Both `POST /eval/remote/lease` and `POST /eval/remote/submit`
```python
_auth: Annotated[None, Depends(require_operator_token)]
```
Use `hmac.compare_digest()` not `!=` for constant-time comparison (RESEARCH.md Q10 / ASVS V2).

### Session Discipline (read-then-write)
**Source:** `app/services/eval_drain.py` `_full_drain_tick` session pattern (documented in module docstring lines 14-20)
**Apply to:** Both endpoints in `eval_remote.py`
- Never share a session across the read and write phases.
- Never call `asyncio.gather` inside an open `AsyncSession`.
- The write session opens LATE (after all reads are closed) and encompasses the entire atomic game write.

### Error Handling — Expected Conditions
**Source:** `app/routers/admin.py` lines 68-73 and module docstring
**Apply to:** `eval_remote.py`
- 404 (game not found), 403 (token not configured), 401 (wrong token), 422 (SF version mismatch) are EXPECTED conditions — raise `HTTPException`, do NOT call `sentry_sdk.capture_exception()`.
- Only unexpected internal errors (e.g., cap-reached residual holes) go to Sentry via `capture_message`.

### Pydantic Schema Style
**Source:** `app/schemas/imports.py`
**Apply to:** `app/schemas/eval_remote.py`
- Module-level docstring naming the phase.
- One `BaseModel` per DTO, no nesting beyond what the wire format requires.
- `Literal` for fixed-string fields. `int | None` for nullable numeric fields.
- No `@classmethod from_dict` unless there is a non-trivial mapping.

### CLI Script Bootstrap
**Source:** `scripts/resweep_holed_games.py` lines 23-35, `scripts/backfill_eval.py` lines 72-84
**Apply to:** `scripts/remote_eval_worker.py`
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# then all app.* imports with # noqa: E402
import app.models.oauth_account  # noqa: E402, F401  (ORM registry)
import app.models.user            # noqa: E402, F401
from app.core.config import settings  # noqa: E402
```

### Constants Over Magic Numbers
**Source:** `scripts/backfill_eval.py` lines 91-105
**Apply to:** `scripts/remote_eval_worker.py`
```python
DEFAULT_WORKERS: int = 1
DEFAULT_IDLE_SLEEP: float = 5.0
```

---

## No Analog Found

All files have clear analogs in the codebase. No fallback to RESEARCH.md patterns required.

---

## Critical Pitfalls for Planner (from RESEARCH.md)

These must appear as explicit guard notes in PLAN.md action steps:

1. **Worker must NOT apply post-move shift (D-2).** `evaluate_nodes_with_pv(board)` returns position-keyed evals — pass them as-is. The server's `_apply_full_eval_results` applies the `_post_move_eval` +1 shift. Double-shifting breaks flaw detection.

2. **Lease endpoint must call `_claim_tier3_derived()` directly**, not `claim_eval_job()`. The latter is gated by `EVAL_AUTO_DRAIN_ENABLED` and mixes tiers.

3. **Lease must include the terminal eval-donor** (`include_terminal=True` in `_collect_full_ply_targets`). Without it, the last played ply's `eval_cp` stays NULL after submit.

4. **For v1, return 204 when `is_lichess_eval_game=True`** at the lease endpoint. Lichess PV-backfill game handling (flaw-adjacent filtering) is deferred.

5. **Submit endpoint must not use `asyncio.gather` inside an open session.** The worker gathers locally; the server's write path is sequential.

6. **`_collect_full_ply_targets` needs `game_positions_rows` as `list[tuple[int, int, int|None, int|None]]`** — `(ply, full_hash, eval_cp, eval_mate)` — loaded from DB before calling it.

---

## Metadata

**Analog search scope:** `app/routers/`, `app/schemas/`, `app/core/`, `app/services/engine.py`, `scripts/`, `tests/routers/`
**Files scanned:** 9 source files read directly
**Pattern extraction date:** 2026-06-14
