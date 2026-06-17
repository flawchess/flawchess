# Phase 120: Headless Remote Trusted-Operator Eval Worker (SEED-048) — Research

**Researched:** 2026-06-14
**Domain:** FastAPI HTTP endpoints + operator-token auth + headless Python CLI worker + EnginePool
**Confidence:** HIGH (all findings sourced from direct codebase reading)

---

## Summary

Phase 120 adds two HTTP endpoints to the prod server and a standalone Python CLI worker script. The server endpoints act as a leasing protocol: a remote trusted-operator machine calls `POST /api/eval/remote/lease` to claim a tier-3 game plus its unanalyzed `(ply, FEN)` positions, evaluates them locally using `EnginePool`, then calls `POST /api/eval/remote/submit` to post back `{ply: (eval_cp, eval_mate, best_move, pv)}`. The server applies the existing SEED-044 storage convention (post-move shift, terminal eval-donor, `full_evals_completed_at` stamping) identically to how `_full_drain_tick` does it.

The delta is intentionally small: the entire eval pipeline (queue pick, target collection, SEED-044 write path, flaw classification) already exists in `eval_queue_service.py` and `eval_drain.py`. The new code is a thin HTTP adapter layer over those services, plus the worker CLI (`scripts/remote_eval_worker.py`).

**Primary recommendation:** Build a new `app/routers/eval_remote.py` router (prefix `/eval/remote`), reusing `_claim_tier3_derived` → `_collect_full_ply_targets` → `_apply_full_eval_results` → `_classify_and_fill_oracle` → `_mark_full_evals_completed` in exact the same order as `_full_drain_tick`. The worker CLI mirrors `scripts/backfill_eval.py`'s `EnginePool` startup/teardown pattern and `scripts/resweep_holed_games.py`'s path bootstrapping pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Game lease pick (tier-3 lottery) | API / Backend | — | `_claim_tier3_derived()` in `eval_queue_service.py`; server owns all scheduling |
| Position collection (ply, FEN) | API / Backend | — | Server derives FEN from PGN replay via `_collect_full_ply_targets()`; worker is dumb (D-2) |
| Stockfish evaluation | Remote CLI worker | — | Worker owns `EnginePool`; server never runs engine for this path |
| SEED-044 storage convention | API / Backend | — | D-2: server owns all storage rules; worker returns raw `(eval_cp, eval_mate, best_move, pv)` keyed by ply |
| Flaw classification + oracle counts | API / Backend | — | `_classify_and_fill_oracle()` runs on submit, same as `_full_drain_tick` Step 4 |
| Completion stamping | API / Backend | — | `_mark_full_evals_completed()` / `_mark_full_pv_completed()` called by submit endpoint |
| Auth (operator token) | API / Backend | — | `X-Operator-Token` header dependency; static secret from `Settings` |
| SF version gate | API / Backend | — | Server reads `EXPECTED_SF_VERSION` from settings; rejects mismatched submit (D-5) |

---

## Research Findings by Question

### Q1: Current tier-3 lease path (post-Phase-119)

**File:** `app/services/eval_queue_service.py` [VERIFIED: direct codebase read]

`claim_eval_job(worker_id: str = WORKER_ID_SERVER_POOL) -> ClaimedJob | None` (lines 353–406) is the top-level API. It:
1. Sweeps expired leases via `_sweep_expired_leases()`.
2. Tries tier-1/2 via `_claim_queued_job()` (SKIP LOCKED against `eval_jobs`).
3. If no tier-1/2 row, and if `settings.EVAL_AUTO_DRAIN_ENABLED`, falls through to `_claim_tier3_derived()`.

**`_claim_tier3_derived(session)` (lines 212–347):** Two-step process:
- **Step 1 (weighted user pick):** Efraimidis–Spirakis lottery over non-guest users with `needs_engine_full_evals = True` (i.e., `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`). Weight = `exp(-Δt/τ) + WEIGHT_FLOOR` where `τ = RECENCY_HALF_LIFE_DAYS / ln2 * 86400 = 124,716 s` and `WEIGHT_FLOOR = 0.005`. Order key: `-ln(random()) / weight LIMIT 1`.
- **Step 2 (best game for user):** Within the chosen user, picks the best `needs_engine_full_evals` game by TC bucket (classical > rapid > blitz > bullet > other) then `played_at DESC NULLS LAST`.
- **Residual fallback:** If no `needs_engine` candidate exists anywhere, picks a `lichess_evals_at IS NOT NULL` PV-backfill-only game → returns `is_lichess_eval_game=True`.

**Return type:** `tuple[game_id, user_id, is_lichess_eval_game]` (or None).

**`ClaimedJob` dataclass (lines 95–114):**
```python
@dataclass(frozen=True)
class ClaimedJob:
    game_id: int
    user_id: int
    tier: int
    is_lichess_eval_game: bool
    job_id: int | None  # None for tier-3 derived pick
```

**Key constants:**
- `LEASE_TTL_SECONDS: int = 120` (line 65)
- `WORKER_ID_SERVER_POOL: str = "server-pool"` (line 69)
- `TIER_IDLE_BACKLOG = 3` (imported from `app.models.eval_jobs`)

**For the remote lease endpoint:** The endpoint calls `_claim_tier3_derived()` directly (not `claim_eval_job()`) to skip tiers 1 and 2. The tier-3 path has no `eval_jobs` row, so D-4 (accept duplicate work) is already the natural behavior — two workers can race and write idempotent results.

**The `EVAL_AUTO_DRAIN_ENABLED` gate does NOT apply** to the remote lease endpoint: tier-1 explicit jobs are not gated, and the remote endpoint is an explicit external request analogous to tier-1. The auto-drain gate is specifically for the background tier-3 idle loop. The endpoint should bypass the flag and call `_claim_tier3_derived()` directly.

---

### Q2: EnginePool surface

**File:** `app/services/engine.py` [VERIFIED: direct codebase read]

**Primary function for the worker:**
```python
# EnginePool.evaluate_nodes_with_pv(board: chess.Board) -> tuple[int | None, int | None, str | None, str | None]
# Returns: (eval_cp, eval_mate, best_move_uci, pv_uci_string)
# At 1M nodes (_NODES_BUDGET = 1_000_000), timeout _NODES_TIMEOUT_S = 5.0s
# Returns (None, None, None, None) on engine failure
```

**Pool construction (lines 329–355):**
```python
pool = EnginePool(size=N)
await pool.start()   # spawns N UCI subprocesses, configures Hash=32MB, Threads=1
# ...
await pool.stop()    # quits all UCI processes
```

**Pool size for the worker:** Read from `STOCKFISH_POOL_SIZE` env var (default 1). The worker CLI should accept `--workers N` and build `EnginePool(N)` directly (same pattern as `scripts/backfill_eval.py`).

**Stockfish binary discovery** (lines 63–76, `_resolve_stockfish_path()`):
1. `STOCKFISH_PATH` env var (wins if set)
2. `/usr/local/bin/stockfish` (prod Docker)
3. `~/.local/stockfish/sf` (dev install via `bin/install_stockfish.sh`)
4. `stockfish` on PATH (Homebrew/apt)

**Stockfish version detection** (confirmed via live test):
```python
transport, protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
version_string = protocol.id.get("name", "")  # e.g. "Stockfish 18"
```
`protocol.id` is populated during the UCI handshake (the `id name` / `id author` lines). The worker must start the pool to get the version, then include it in the submit payload. The server compares against `settings.EXPECTED_SF_VERSION` (a new setting to add).

**SCHED_IDLE handling** (lines 149–182): Already handled in `_engine_popen_kwargs()`:
- Linux: `preexec_fn=_sched_idle_preexec` → Stockfish runs at SCHED_IDLE priority
- macOS/Windows: returns `{}` → default priority (SEED-048 open item: macOS worker competes with foreground)

**PV constants:** `PV_CAP_PLIES: int = 12` (line 99) — the pv string is already capped at 12 plies.

---

### Q3: SEED-044 storage convention — what the submit endpoint must replicate

**File:** `app/services/eval_drain.py` [VERIFIED: direct codebase read]

The submit endpoint must replicate **exactly what `_full_drain_tick` does in Steps 2–4**, adapted for server-supplied (not engine-computed) results.

**Key functions to reuse:**

**`_collect_full_ply_targets(game_id, pgn_text, game_positions_rows, include_terminal) -> list[_FullPlyEvalTarget]`** (lines 149–229):
- Takes `game_positions_rows: Sequence[tuple[int, int, int | None, int | None]]` = `(ply, full_hash, eval_cp, eval_mate)` from DB.
- Returns one target per ply, including an optional terminal eval-donor.
- Engine games: `include_terminal=True`. Lichess games: `include_terminal=False`.
- The terminal target has `is_terminal=True` and `ply = <number of plies played>`.

**`_post_move_eval(pos_eval, ply) -> tuple[int | None, int | None]`** (lines 344–357): The SINGLE site of the +1 shift. `pos_eval[ply + 1]` is the stored value for row `ply`.

**`_apply_full_eval_results(session, targets, dedup_map, engine_result_map, is_lichess_eval_game) -> int`** (lines 360–453):
- Takes `engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]]` = `{ply: (eval_cp, eval_mate, best_move, pv_string)}`.
- Returns `failed_ply_count` (non-terminal plies with NULL result after write).
- The submit endpoint supplies the `engine_result_map` from the worker's payload — `dedup_map` is empty `{}` (no dedup for remote submissions; worker already evaluated all positions).

**`_classify_and_fill_oracle(session, game_id, engine_result_map)`** (lines 490–617):
- Classifies `game_flaws`, inserts via `bulk_insert_game_flaws` (ON CONFLICT DO NOTHING — idempotent), updates oracle count columns.
- Must run AFTER `_apply_full_eval_results` and BEFORE completion stamps.

**`_mark_full_evals_completed(session, game_id)`** (lines 456–472): Sets `full_evals_completed_at = NOW()`.

**`_mark_full_pv_completed(session, game_id)`** (lines 474–487): Sets `full_pv_completed_at = NOW()`.

**Phase 119 SEED-045 bounded-retry logic** (lines 1431–1519):
- The submit endpoint must also load `Game.full_eval_attempts` and apply the same decision tree:
  - Path A: `failed_ply_count == 0` → stamp complete.
  - Path B: holes remain AND `current_attempts + 1 < MAX_EVAL_ATTEMPTS (3)` → increment `full_eval_attempts`, do NOT stamp.
  - Path C: holes remain AND cap reached → stamp anyway (no-loop invariant), emit Sentry warning.

**`MAX_EVAL_ATTEMPTS: int = 3`** (line 103).

**Signal hook:** `_signal_flaw_completion(user_id)` (line 683) — call after commit if `stamp_complete=True`.

---

### Q4: What positions need evaluating — the lease response shape

**FEN is NOT stored in `game_positions`.** The model stores: `ply`, `full_hash`, `white_hash`, `black_hash`, `move_san`, `eval_cp`, `eval_mate`, `best_move`, `pv`, `phase`, `endgame_class`, `piece_count`, etc. No `fen` column. [VERIFIED: direct model read]

**For the lease response, the server must:**
1. Load `Game.pgn` and all `game_positions` rows for the game (ply, full_hash, eval_cp, eval_mate).
2. Call `_collect_full_ply_targets()` to determine which plies need evaluation.
3. Replay the PGN to extract `board.fen()` at each target ply's pre-push board snapshot.

**Position filter for engine games (`is_lichess_eval_game=False`):**
- ALL plies whose row exists in `game_positions` (one per half-move), plus the terminal eval-donor.
- `_collect_full_ply_targets` returns them all; the drain does NOT pre-filter by `eval_cp IS NULL` here — it evaluates everything and the write path handles idempotency.

**Position filter for lichess games (`is_lichess_eval_game=True`):**
- Only plies where `eval_cp IS NULL AND eval_mate IS NULL`, plus flaw-adjacent plies (for PV capture).
- This filtering is done in `_full_drain_tick` lines 1362–1366 before the gather.

**Important:** For the remote worker (engine games only per the tier-3 needs-engine predicate), the lease response sends ALL positions (no pre-filtering). The worker evaluates all of them; the server applies the write-time preservation gate.

**FEN for the worker:** Use `board.fen()` (full FEN with turn, castling, en passant) not `board.board_fen()`. The engine needs the full board state for accurate analysis. `board.board_fen()` is for comparing positions (Zobrist hash). The worker reconstructs `chess.Board(fen_string)` from the FEN the server provides.

**Lease response schema:**
```python
class LeasePosition(BaseModel):
    ply: int
    fen: str          # board.fen() — full FEN including turn, castling, en passant
    is_terminal: bool # True for the terminal eval-donor

class LeaseResponse(BaseModel):
    game_id: int
    is_lichess_eval_game: bool
    positions: list[LeasePosition]
    leased_at: datetime   # for worker-side TTL tracking
```

**Submit request schema:**
```python
class SubmitEval(BaseModel):
    ply: int
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None  # UCI
    pv: str | None         # space-joined UCI, up to 12 plies

class SubmitRequest(BaseModel):
    game_id: int
    sf_version: str   # e.g. "Stockfish 18" — for D-5 version gate
    evals: list[SubmitEval]
```

---

### Q5: Auth pattern for operator token

**Pattern:** A simple `X-Operator-Token: <secret>` HTTP header dependency. No FastAPI-Users integration needed — the operator token is a static shared secret, not a user session. [VERIFIED: direct codebase read + training knowledge]

**Implementation approach:**
```python
# app/core/config.py — add to Settings:
EVAL_OPERATOR_TOKEN: str = ""   # empty = disabled in dev/CI; prod sets via .env

# app/routers/eval_remote.py — dependency:
from fastapi import Header, HTTPException, status
from app.core.config import settings

async def require_operator_token(
    x_operator_token: str = Header(alias="X-Operator-Token"),
) -> None:
    if not settings.EVAL_OPERATOR_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator token not configured")
    if x_operator_token != settings.EVAL_OPERATOR_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid operator token")
```

**Why not `current_superuser`:** The remote worker is not a human user with an email/password account. The operator token is a machine credential passed as a request header, appropriate for a server-to-server call over HTTPS.

**Why not FastAPI `Security` + `APIKeyHeader`:** The explicit `Header` dependency is simpler and matches the project's style (thin router conventions). `APIKeyHeader` auto-handles 403 on missing header; the explicit approach gives the same behavior with clearer error messages.

**New settings fields to add to `app/core/config.py`:**
- `EVAL_OPERATOR_TOKEN: str = ""` — the shared secret. Set in prod `.env`; empty in dev/CI (endpoints return 403 if unconfigured).
- `EXPECTED_SF_VERSION: str = ""` — e.g. `"Stockfish 18"`. Set in prod `.env` to the version installed on the server. Empty = any version accepted (dev/CI).

---

### Q6: Router/service/repository layout

**New router:** `app/routers/eval_remote.py` with `APIRouter(prefix="/eval/remote", tags=["eval-remote"])`. [VERIFIED: direct codebase read]

**Pattern** (from `app/routers/admin.py` lines 20–21):
```python
router = APIRouter(prefix="/eval/remote", tags=["eval-remote"])

@router.post("/lease", response_model=LeaseResponse)
async def lease_eval_game(...): ...

@router.post("/submit", response_model=SubmitResponse)
async def submit_eval(...): ...
```

**Registration in `app/main.py`:** Add `from app.routers.eval_remote import router as eval_remote_router` and `app.include_router(eval_remote_router, prefix="/api")`. Routes become `/api/eval/remote/lease` and `/api/eval/remote/submit`.

**No new repository needed.** The submit endpoint reuses `eval_drain._apply_full_eval_results`, `eval_drain._classify_and_fill_oracle`, `eval_drain._mark_full_evals_completed`, and `eval_drain._mark_full_pv_completed` — all of which take an `AsyncSession` from the router's `get_async_session` dependency.

**Session discipline:** Both endpoints must open sessions themselves (not shared with the `require_operator_token` dependency). The submit endpoint opens ONE write session for the entire atomic game write (following the same session discipline as `_full_drain_tick` Step 4).

**Service layer:** Because the endpoints are thin (validate → call existing eval_drain functions), a dedicated service module is optional. The router can call eval_drain functions directly, but for testability it's cleaner to extract an `eval_remote_service.py` module with `lease_game(session_maker)` and `apply_remote_evals(session, ...)`.

---

### Q7: Stockfish version detection

**Worker-side version reporting** (confirmed via live test on dev box):
```python
transport, protocol = await chess.engine.popen_uci(stockfish_path)
sf_version = protocol.id.get("name", "unknown")  # "Stockfish 18"
await protocol.quit()
```
`protocol.id` is populated during the UCI `uci` command handshake. The `.id` dict has keys `"name"` and `"author"`. The version is in `protocol.id["name"]`, e.g. `"Stockfish 18"`.

**Server-side version gate (D-5):**
```python
# In submit endpoint:
if settings.EXPECTED_SF_VERSION and submit_req.sf_version != settings.EXPECTED_SF_VERSION:
    raise HTTPException(status_code=422, detail=f"SF version mismatch: got {submit_req.sf_version!r}, expected {settings.EXPECTED_SF_VERSION!r}")
```

**Worker reads version at startup** (during pool `start()` which calls `popen_uci`). The pool currently does not expose `protocol.id` publicly. Two options:
1. (Simpler) Run a separate `popen_uci` call before starting the pool, read `protocol.id["name"]`, then quit that connection. Add a helper `get_stockfish_version(path: str) -> str` in `engine.py` or inline in the worker script.
2. Extend `EnginePool` to expose `pool.sf_version` after `start()` — adds an attribute but keeps the pool as the single source of truth.

**Recommendation:** Option 1 — a standalone `get_stockfish_version()` helper in `engine.py` (8 lines, reusable):
```python
async def get_stockfish_version() -> str:
    """Read Stockfish version string via UCI handshake. Returns e.g. 'Stockfish 18'."""
    transport, protocol = await chess.engine.popen_uci(_STOCKFISH_PATH, **_engine_popen_kwargs())
    version = protocol.id.get("name", "unknown")
    await protocol.quit()
    return version
```

---

### Q8: CLI worker conventions — structural template

**Primary template:** `scripts/backfill_eval.py` (most relevant — uses `EnginePool` + async + `httpx` pattern). `scripts/resweep_holed_games.py` shows the minimal path bootstrapping pattern. [VERIFIED: direct codebase read]

**Bootstrap pattern** (from both scripts):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # loads .env automatically
```

**Main async entry point pattern** (from `backfill_eval.py` lines 879–902):
```python
async def main() -> None:
    args = parse_args()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    await run_worker(...)

if __name__ == "__main__":
    asyncio.run(main())
```

**httpx.AsyncClient pattern for the worker:**
```python
import httpx

async def run_worker(base_url: str, token: str, workers: int, ...) -> None:
    pool = EnginePool(workers)
    await pool.start()
    sf_version = await get_stockfish_version()
    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Operator-Token": token},
            timeout=30.0,
        ) as client:
            while True:
                lease = await client.post("/api/eval/remote/lease")
                if lease.status_code == 204:
                    await asyncio.sleep(idle_sleep)
                    continue
                data = lease.json()
                evals = await _eval_positions(pool, data["positions"])
                submit_body = {"game_id": data["game_id"], "sf_version": sf_version, "evals": evals}
                await client.post("/api/eval/remote/submit", json=submit_body)
    finally:
        await pool.stop()
```

**Worker's eval loop (fan-out via asyncio.gather):**
```python
async def _eval_positions(pool: EnginePool, positions: list[dict]) -> list[dict]:
    boards = [chess.Board(pos["fen"]) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))
    return [
        {"ply": pos["ply"], "eval_cp": r[0], "eval_mate": r[1], "best_move": r[2], "pv": r[3]}
        for pos, r in zip(positions, results)
    ]
```

**CLI arguments:**
- `--base-url` (e.g. `https://flawchess.com`) — REQUIRED
- `--token` (operator token) — REQUIRED (or read from env `EVAL_OPERATOR_TOKEN`)
- `--workers` (default 1, use as many as machine cores allow)
- `--idle-sleep` (seconds between empty-queue polls, default 5)
- `--dry-run` (lease only, don't submit — for testing connectivity)
- `--loop` / `--once` (run one game or loop forever; default loop)

**File location:** `scripts/remote_eval_worker.py` — consistent with other maintenance scripts.

---

### Q9: Testing approach

**Router test pattern** (from `tests/routers/test_imports_tier1_enqueue.py`): [VERIFIED: direct codebase read]
- `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")`
- Register user, get JWT token, include as `Authorization: Bearer <token>` header
- For operator-token tests: use `X-Operator-Token: <secret>` header directly

**Service/drain test pattern** (from `tests/services/test_full_eval_drain.py`):
- `monkeypatch app.services.eval_drain.async_session_maker` to `test_engine`-bound session maker
- Patch `engine_service.evaluate_nodes_with_pv` with `AsyncMock` returning fake tuples
- Seed committed test data (not rollback-scoped) so HTTP requests see them

**Test surface for Phase 120:**

`tests/routers/test_eval_remote_router.py`:
- `test_lease_requires_operator_token` — no token → 401/403
- `test_lease_wrong_token` → 401
- `test_lease_no_pending_games` → 204 (empty queue)
- `test_lease_returns_positions` — seed a game with `needs_engine_full_evals=True`, lease returns `{game_id, positions: [{ply, fen, is_terminal}]}`
- `test_submit_requires_operator_token` → 401/403
- `test_submit_sf_version_mismatch` (D-5) — `EXPECTED_SF_VERSION` set, wrong version → 422
- `test_submit_applies_post_move_shift` — verify `eval_cp` written at correct ply
- `test_submit_stamps_full_evals_completed_at` — verify `full_evals_completed_at IS NOT NULL` after submit
- `test_submit_idempotent` — submit twice → no error, same data

**Session patching strategy:** Monkeypatch `app.services.eval_drain.async_session_maker` and `app.routers.eval_remote.async_session_maker` (or the service module's session maker) to route to test DB.

**Note:** The `EVAL_OPERATOR_TOKEN` setting must be patched in tests via `monkeypatch` on `app.core.config.settings.EVAL_OPERATOR_TOKEN`.

---

### Q10: Pitfalls and landmines

**Pitfall 1 — AsyncSession concurrent use:** The submit endpoint must never call `asyncio.gather` inside an open `AsyncSession`. The `_apply_full_eval_results` calls run sequentially inside the write session. The worker's gather runs BEFORE the submit HTTP call; the server never gathers.

**Pitfall 2 — Post-move shift ownership (D-2):** The worker returns evals keyed by ply in the **position-keyed** convention (eval OF that ply's position, which is what `evaluate_nodes_with_pv(board)` returns). The server applies the `_post_move_eval(pos_eval, ply)` shift at write time via `_apply_full_eval_results`. The worker must NOT apply the shift itself — doing so would double-shift.

**Pitfall 3 — Terminal eval-donor:** The lease response must include `is_terminal=True` positions. The submit payload includes the terminal's eval (keyed by its ply). `_apply_full_eval_results` already handles terminal targets correctly (skips DB write for `is_terminal=True`, uses its eval as `pos_eval[last_ply + 1]`).

**Pitfall 4 — `full_eval_attempts` load race:** The submit endpoint must load `Game.full_eval_attempts` in the read phase (before the write session) to avoid a race where two workers both read `attempts=0`, both write, and both stamp complete on what should have been a retry. For v1 (D-4 accept-duplicate-work), this is acceptable: duplicate evals are idempotent (same engine, same nodes, same FEN → deterministically same or very close eval). Do not try to lock here.

**Pitfall 5 — SF version string format:** `protocol.id["name"]` returns `"Stockfish 18"` (including the word "Stockfish"). The `EXPECTED_SF_VERSION` setting should store the full string (e.g. `"Stockfish 18"`), not just the number. Be consistent.

**Pitfall 6 — Lichess games via tier-3:** The tier-3 residual fallback CAN return `is_lichess_eval_game=True` (PV-backfill-only games). The lease endpoint must handle this: for lichess games, the position filter must exclude plies where `eval_cp IS NOT NULL OR eval_mate IS NOT NULL` (these are already populated by lichess %evals — don't send them to the worker). Only flaw-adjacent plies and `eval IS NULL` plies go to the worker. For v1 simplicity, the planner may choose to skip lichess games at the lease endpoint (return 204 when `is_lichess_eval_game=True`) and only serve engine games. Document this scope decision.

**Pitfall 7 — `EVAL_AUTO_DRAIN_ENABLED` flag:** The lease endpoint must NOT be gated by `settings.EVAL_AUTO_DRAIN_ENABLED`. The `_claim_tier3_derived()` call in the lease endpoint is an explicit external request, not the background auto-drain loop. Calling `claim_eval_job()` would incorrectly gate it.

**Pitfall 8 — 120s lease TTL vs slow workers:** The 120s TTL was sized for the server-side pool (60 plies × 0.98s/ply ≈ 59s → 2× = 120s). A remote worker on a slow machine with 1 core could take longer. For v1 with D-4 (no strict leasing), this is moot — tier-3 has no `eval_jobs` row so the TTL has no effect. The 120s TTL is only relevant for tier-1/2 job rows. Document for the planner: no TTL extension needed in v1.

**Pitfall 9 — `_classify_and_fill_oracle` needs `engine_result_map`:** The submit endpoint receives `evals` as a list of `{ply, eval_cp, eval_mate, best_move, pv}`. Before calling `_classify_and_fill_oracle`, convert this to `engine_result_map: dict[int, tuple[...]]` keyed by ply. The terminal ply eval goes into the map as well (it's needed for the last played-ply's `_post_move_eval`).

**Pitfall 10 — `_collect_full_ply_targets` needs `game_positions_rows`:** The lease endpoint loads `(ply, full_hash, eval_cp, eval_mate)` from DB via:
```python
select(GamePosition.ply, GamePosition.full_hash, GamePosition.eval_cp, GamePosition.eval_mate)
.where(GamePosition.game_id == game_id)
```
Pass as `[(ply, full_hash, eval_cp, eval_mate)]` tuples (matching the function's expected shape at line 154).

---

## Standard Stack

### Core (existing — no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.115.0 | New router + dependency | Project standard |
| httpx | >=0.27.0 | Worker HTTP client (async) | CLAUDE.md: `httpx.AsyncClient` only |
| python-chess | >=1.10.0 | Board replay (FEN extraction) + worker engine board | Project standard |
| SQLAlchemy 2.x async | >=2.0.0 | Session handling in endpoints | Project standard |
| Pydantic v2 | >=2.0.0 | Request/response schemas | Project standard |

### No New Packages
This phase installs zero new packages. All required libraries are already in `pyproject.toml`. The worker script is a plain Python script using existing project dependencies (`chess`, `httpx`, `EnginePool`, `asyncio`).

## Package Legitimacy Audit

> No new packages are installed in this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Remote Worker (home box / MacBook)
  [scripts/remote_eval_worker.py]
    ↓ POST /api/eval/remote/lease  (X-Operator-Token header)
    ↓ (HTTPS to flawchess.com)
    ↑ {game_id, positions: [{ply, fen, is_terminal}]}
    ↓
  EnginePool.evaluate_nodes_with_pv(board) × N positions
  (asyncio.gather, no session)
    ↓
  POST /api/eval/remote/submit  (X-Operator-Token header)
  body: {game_id, sf_version, evals: [{ply, eval_cp, eval_mate, best_move, pv}]}

Prod Server (app/routers/eval_remote.py)
  POST /lease:
    require_operator_token()
    _claim_tier3_derived(session)  → (game_id, user_id, is_lichess_eval_game)
    load Game.pgn + game_positions (ply, full_hash, eval_cp, eval_mate)
    _collect_full_ply_targets(game_id, pgn, gp_rows, include_terminal)
    replay PGN → board.fen() per target
    return LeaseResponse

  POST /submit:
    require_operator_token()
    check sf_version == settings.EXPECTED_SF_VERSION (D-5)
    load Game.pgn + full_eval_attempts (read session, close)
    load game_positions rows (read session, close)
    reconstruct targets via _collect_full_ply_targets
    open write session:
      _apply_full_eval_results(session, targets, {}, engine_result_map, is_lichess_eval_game)
      _classify_and_fill_oracle(session, game_id, engine_result_map)
      SEED-045: if failed_ply_count == 0 → stamp complete
               elif under cap → increment full_eval_attempts
               else → stamp anyway + Sentry
      commit
    _signal_flaw_completion(user_id)
    return SubmitResponse

PostgreSQL (game_positions, games, game_flaws, eval_jobs)
```

### Recommended Project Structure

```
app/
├── routers/
│   └── eval_remote.py          # new: POST /eval/remote/lease + /submit
├── schemas/
│   └── eval_remote.py          # new: LeaseResponse, SubmitRequest, SubmitResponse
├── core/
│   └── config.py               # extend: EVAL_OPERATOR_TOKEN, EXPECTED_SF_VERSION
├── services/
│   ├── engine.py               # extend: get_stockfish_version() helper
│   └── eval_drain.py           # reuse existing functions (no changes needed)
scripts/
└── remote_eval_worker.py       # new: CLI worker
tests/
├── routers/
│   └── test_eval_remote_router.py  # new: endpoint tests
└── services/
    └── test_eval_remote.py         # new: service-level submit logic tests (optional)
```

### Pattern 1: Thin Router → Existing Service Functions

The router calls `eval_drain` functions directly (no new service module required unless the router logic exceeds ~50 lines):

```python
# app/routers/eval_remote.py
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

Note: `_collect_full_ply_targets` and the other underscore-prefixed functions are module-level within `eval_drain.py`. They are already well-tested via `test_full_eval_drain.py`. Importing private functions from a sibling service is acceptable given the tight coupling of this phase to the existing drain logic. Alternatively, promote them to non-underscore names in `eval_drain.py` as a pre-step.

### Pattern 2: Operator Token Dependency

```python
from fastapi import Header, HTTPException, status, Depends
from typing import Annotated
from app.core.config import settings

async def require_operator_token(
    x_operator_token: Annotated[str, Header(alias="X-Operator-Token")],
) -> None:
    configured = settings.EVAL_OPERATOR_TOKEN
    if not configured:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator token not configured on server")
    if x_operator_token != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid operator token")

@router.post("/lease", response_model=LeaseResponse)
async def lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LeaseResponse:
    ...
```

### Pattern 3: Worker CLI Loop

The worker's main loop follows the same shape as the drain's `run_full_eval_drain` but with HTTP instead of direct DB calls:

```python
async def _run_loop(client: httpx.AsyncClient, pool: EnginePool, sf_version: str, idle_sleep: float) -> None:
    while True:
        lease_resp = await client.post("/api/eval/remote/lease")
        if lease_resp.status_code == 204:  # no work
            await asyncio.sleep(idle_sleep)
            continue
        lease_resp.raise_for_status()
        data = lease_resp.json()
        evals = await _eval_positions(pool, data["positions"])
        submit_resp = await client.post("/api/eval/remote/submit", json={
            "game_id": data["game_id"],
            "sf_version": sf_version,
            "evals": evals,
        })
        submit_resp.raise_for_status()
```

### Anti-Patterns to Avoid

- **Anti-pattern: worker applies post-move shift.** The worker returns `(eval_cp, eval_mate)` exactly as `evaluate_nodes_with_pv()` returns them — no +1 shift. D-2: server owns storage convention.
- **Anti-pattern: calling `claim_eval_job()` in the lease endpoint.** This would gate on `EVAL_AUTO_DRAIN_ENABLED` and mix tiers. Call `_claim_tier3_derived()` directly.
- **Anti-pattern: using `asyncio.gather` inside a write session.** The server's submit endpoint never gathers; the worker gathers locally before the HTTP submit call.
- **Anti-pattern: opening a new session per position write.** The entire game's write (all position UPDATEs, flaw classify, oracle counts, completion stamps) must be in ONE transaction in ONE session.
- **Anti-pattern: re-implementing `_post_move_eval`.** Call the existing function from `eval_drain.py`; never duplicate the +1 logic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SEED-044 post-move shift | Custom ply-shift logic in submit endpoint | `_post_move_eval()` + `_apply_full_eval_results()` from `eval_drain.py` | Single source of truth; already tested |
| Tier-3 lottery pick | New scheduling query | `_claim_tier3_derived()` from `eval_queue_service.py` | Phase 119's SEED-046 ES lottery already implemented |
| Flaw classification on submit | Re-implement classify | `_classify_and_fill_oracle()` from `eval_drain.py` | Same kernel as the drain; must not drift |
| EnginePool for worker | Custom SF subprocess | `EnginePool` from `app/services/engine.py` | Handles restart-on-crash, SCHED_IDLE, pool queue |
| FEN → chess.Board in worker | Custom PGN parser | `chess.Board(fen_string)` | python-chess is the project standard |

---

## Common Pitfalls

### Pitfall 1: Worker applies post-move shift
**What goes wrong:** Worker applies `stored_eval = eval_of_position_ply_plus_1` before posting. Server then applies `_post_move_eval()` again. Every eval is off by one ply.
**Why it happens:** Misreading D-2 as "worker knows storage convention."
**How to avoid:** D-2 is explicit: worker returns position-keyed evals from `evaluate_nodes_with_pv(board)`, zero transformation.
**Warning signs:** Flaw detection fires at wrong plies; oracle counts disagree with drain-processed games.

### Pitfall 2: Gating lease on `EVAL_AUTO_DRAIN_ENABLED`
**What goes wrong:** Remote workers get 204 "no work" on prod (or dev) because the flag is `False`.
**Why it happens:** Calling `claim_eval_job()` instead of `_claim_tier3_derived()` directly.
**How to avoid:** Call `_claim_tier3_derived(session)` directly in the lease endpoint. The auto-drain flag controls the background loop's idle polling, not explicit external requests.

### Pitfall 3: Lichess game leak to worker
**What goes wrong:** A lichess PV-backfill game (residual fallback from `_claim_tier3_derived`) leaks to the worker. Worker evaluates all ~60 positions including those with existing lichess %evals, server overwrites them.
**Why it happens:** `_apply_full_eval_results(is_lichess_eval_game=True)` preserves lichess evals at write time, but still burns CPU on the worker to evaluate every position.
**How to avoid:** For v1, return 204 when `is_lichess_eval_game=True` at the lease endpoint. Document this as a deferred enhancement.

### Pitfall 4: Missing terminal eval-donor in lease
**What goes wrong:** The last played move's `eval_cp` is NULL after submit (the terminal donor's eval, needed for `_post_move_eval(pos_eval, last_ply)`, is missing from the map).
**Why it happens:** Lease response omits positions with `is_terminal=True`. Worker doesn't evaluate the terminal board. Server's `pos_eval[last_ply + 1]` lookup returns `(None, None)`.
**How to avoid:** Ensure `_collect_full_ply_targets(include_terminal=True)` includes the terminal target and the lease response lists it with `is_terminal=True`. Worker evaluates it like any other FEN.

### Pitfall 5: Session shared across concurrent operations
**What goes wrong:** Submit endpoint uses one session for both reading `game_positions` and writing evals. AsyncSession is not safe for concurrent use.
**Why it happens:** Putting load + gather + write in one session context manager.
**How to avoid:** Follow `_full_drain_tick` session discipline: one short read session (close), gather (no session), one write session (open LATE, close on commit).

---

## Code Examples

### Lease endpoint — position collection

```python
# Source: direct reading of eval_drain.py + eval_queue_service.py
async def lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
) -> LeaseResponse:
    # Step 1: claim tier-3 game (short session, close)
    async with async_session_maker() as session:
        derived = await _claim_tier3_derived(session)
    if derived is None:
        return Response(status_code=204)  # no work
    game_id, user_id, is_lichess_eval_game = derived

    # For v1: skip lichess games (PV-backfill path)
    if is_lichess_eval_game:
        return Response(status_code=204)

    # Step 2: load PGN + game_positions (short read session, close)
    async with async_session_maker() as session:
        pgn_row = await session.execute(select(Game.pgn).where(Game.id == game_id))
        pgn_text = pgn_row.scalar_one_or_none()
        if pgn_text is None:
            return Response(status_code=204)
        pos_rows = await session.execute(
            select(GamePosition.ply, GamePosition.full_hash, GamePosition.eval_cp, GamePosition.eval_mate)
            .where(GamePosition.game_id == game_id)
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_rows.all()]

    # Step 3: collect targets, extract FEN per target (no session)
    targets = _collect_full_ply_targets(game_id, pgn_text, gp_rows, include_terminal=True)
    
    # Build ply -> FEN map by replaying PGN
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    fen_by_ply: dict[int, str] = {}
    if game is not None:
        board = game.board()
        for ply, node in enumerate(game.mainline()):
            fen_by_ply[ply] = board.fen()  # pre-push board at this ply
            board.push(node.move)
        # terminal position
        fen_by_ply[len(fen_by_ply)] = board.fen()

    positions = [
        LeasePosition(ply=t.ply, fen=fen_by_ply.get(t.ply, ""), is_terminal=t.is_terminal)
        for t in targets
        if t.ply in fen_by_ply
    ]

    return LeaseResponse(
        game_id=game_id,
        is_lichess_eval_game=is_lichess_eval_game,
        positions=positions,
        leased_at=datetime.now(timezone.utc),
    )
```

### Submit endpoint — apply results (atomic write)

```python
# Source: direct reading of eval_drain.py _full_drain_tick Step 4
async def submit_eval(
    body: SubmitRequest,
    _auth: Annotated[None, Depends(require_operator_token)],
) -> SubmitResponse:
    # D-5: SF version gate
    if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION:
        raise HTTPException(422, f"SF version mismatch")

    # Read phase: load game + positions
    async with async_session_maker() as session:
        pgn_row = await session.execute(
            select(Game.pgn, Game.full_eval_attempts, Game.lichess_evals_at)
            .where(Game.id == body.game_id)
        )
        row = pgn_row.one_or_none()
        if row is None:
            raise HTTPException(404, "Game not found")
        pgn_text, current_attempts, lichess_evals_at = row
        is_lichess_eval_game = lichess_evals_at is not None
        pos_result = await session.execute(
            select(GamePosition.ply, GamePosition.full_hash, GamePosition.eval_cp, GamePosition.eval_mate)
            .where(GamePosition.game_id == body.game_id)
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]

    # Reconstruct targets
    targets = _collect_full_ply_targets(body.game_id, pgn_text, gp_rows, include_terminal=not is_lichess_eval_game)

    # Build engine_result_map from submitted evals
    engine_result_map: dict[int, tuple[int|None, int|None, str|None, str|None]] = {
        e.ply: (e.eval_cp, e.eval_mate, e.best_move, e.pv)
        for e in body.evals
    }

    # Write phase: atomic session
    async with async_session_maker() as write_session:
        failed_ply_count = await _apply_full_eval_results(
            write_session, targets, {}, engine_result_map, is_lichess_eval_game
        )
        await _classify_and_fill_oracle(write_session, body.game_id, engine_result_map)

        new_attempts = current_attempts + 1
        games_table = Game.__table__
        stamp_complete: bool
        if failed_ply_count == 0:
            await _mark_full_evals_completed(write_session, body.game_id)
            await _mark_full_pv_completed(write_session, body.game_id)
            stamp_complete = True
        elif new_attempts < MAX_EVAL_ATTEMPTS:
            await write_session.execute(
                update(games_table).where(games_table.c.id == body.game_id)
                .values(full_eval_attempts=new_attempts)
            )
            stamp_complete = False
        else:
            await _mark_full_evals_completed(write_session, body.game_id)
            await _mark_full_pv_completed(write_session, body.game_id)
            sentry_sdk.set_context("eval", {"game_id": body.game_id, "hole_count": failed_ply_count, "attempts": new_attempts})
            sentry_sdk.set_tag("source", "remote_eval_worker")
            sentry_sdk.capture_message("remote-worker: stamping complete after MAX_EVAL_ATTEMPTS with residual holes", level="warning")
            stamp_complete = True

        await write_session.commit()

    if stamp_complete:
        game_result = ...  # get user_id
        _signal_flaw_completion(user_id)

    return SubmitResponse(game_id=body.game_id, stamp_complete=stamp_complete, failed_ply_count=failed_ply_count)
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio + httpx |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `uv run pytest tests/routers/test_eval_remote_router.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| D-1 | Lease endpoint returns `(ply, FEN)` positions for a tier-3 game | integration | `pytest tests/routers/test_eval_remote_router.py::test_lease_returns_positions -x` |
| D-2 | Submit applies SEED-044 post-move shift server-side | integration | `pytest tests/routers/test_eval_remote_router.py::test_submit_applies_post_move_shift -x` |
| D-3 | Submit is per-game, atomic (all positions in one transaction) | integration | `pytest tests/routers/test_eval_remote_router.py::test_submit_stamps_full_evals_completed_at -x` |
| D-4 | Duplicate lease → no error, idempotent result | integration | `pytest tests/routers/test_eval_remote_router.py::test_submit_idempotent -x` |
| D-5 | SF version mismatch rejected (422) | integration | `pytest tests/routers/test_eval_remote_router.py::test_submit_sf_version_mismatch -x` |
| D-6 | No auth token → 401/403 | integration | `pytest tests/routers/test_eval_remote_router.py::test_lease_requires_operator_token -x` |
| — | Empty queue → 204 | integration | `pytest tests/routers/test_eval_remote_router.py::test_lease_no_pending_games -x` |
| — | Worker CLI connects + leases (dry-run) | manual/e2e | `uv run python scripts/remote_eval_worker.py --base-url https://flawchess.com --token <tok> --dry-run` |

### Sampling Rate
- **Per task commit:** Run relevant test file (`uv run pytest tests/routers/test_eval_remote_router.py -x`)
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/routers/test_eval_remote_router.py` — covers D-1 through D-6
- [ ] `app/schemas/eval_remote.py` — Pydantic models for request/response
- [ ] `app/routers/eval_remote.py` — the router itself (Wave 1 creation)
- [ ] Extend `app/core/config.py` with `EVAL_OPERATOR_TOKEN` + `EXPECTED_SF_VERSION`
- [ ] `app/services/engine.py` — add `get_stockfish_version()` helper
- [ ] `scripts/remote_eval_worker.py` — the CLI worker

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Operator token header dependency (`X-Operator-Token`); constant-time comparison recommended |
| V3 Session Management | no | Stateless endpoints; no session |
| V4 Access Control | yes | Operator token gates both endpoints; no user-scoped access on remote eval endpoints |
| V5 Input Validation | yes | Pydantic v2 `SubmitRequest` validates `game_id: int`, `sf_version: str`, `evals: list[SubmitEval]`; `eval_cp: int | None` constrained by `EVAL_CP_MAX_ABS` at write time in `_score_to_cp_mate` |
| V6 Cryptography | no | Operator token is a static shared secret over HTTPS (TLS is enforced by Caddy on flawchess.com); no additional crypto needed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Operator token brute-force | Elevation of Privilege | HTTPS only (Caddy enforces TLS); token is a strong random secret set in `.env` |
| Replay / duplicate submit | Tampering | Eval writes are idempotent (`ON CONFLICT DO NOTHING` for game_flaws, `_apply_full_eval_results` only writes non-NULL results); duplicate stamping of `full_evals_completed_at` is a re-stamp (idempotent) |
| Malicious `eval_cp` injection (hostile worker) | Tampering | D-6: trusted-operator token; no untrusted writer in v1. Values clamped by `EVAL_CP_MAX_ABS` / `EVAL_MATE_MAX_ABS` at write time. |
| SF version spoofing | Tampering | Server checks `submit_req.sf_version == settings.EXPECTED_SF_VERSION` (D-5). Spoofing the version string bypasses the gate — this is accepted risk for the trusted-operator trust class (D-6). |
| SQL injection via eval fields | Tampering | All values are Pydantic-validated Python types passed as bound parameters via SQLAlchemy ORM `update()` / `values()`; no string interpolation in SQL. |

**Security constraint (from CLAUDE.md):** Never embed variables in error messages. Use `sentry_sdk.set_context()` for `game_id`, `sf_version`, etc. before `capture_exception()`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Stockfish | Worker CLI (`EnginePool`) | ✓ | Stockfish 18 (at `~/.local/stockfish/sf`) | Install via `bin/install_stockfish.sh` |
| httpx | Worker CLI (HTTP client) | ✓ | in `pyproject.toml` >=0.27.0 | — |
| python-chess | Worker CLI (Board) + server (PGN replay) | ✓ | in `pyproject.toml` >=1.10.0 | — |
| PostgreSQL | Server endpoints | ✓ | 18 (Docker) | — |

**Missing dependencies with no fallback:** none

**macOS scheduling note (from SEED-048 open items):** The worker CLI on macOS spawns Stockfish at **default priority** (not SCHED_IDLE — `os.sched_setscheduler` is Linux-only). This is handled transparently by `_engine_popen_kwargs()` in `engine.py` (returns `{}` on non-Linux). The MacBook worker works but competes with foreground apps for CPU. The SEED-048 deferred item (macOS `taskpolicy -b` wrapper) is out of scope for v1.

---

## Open Questions (RESOLVED)

1. **Lichess PV-backfill games via lease endpoint**
   - What we know: `_claim_tier3_derived()` residual fallback returns `is_lichess_eval_game=True`. These games need PV at flaw-adjacent plies only, not full-game re-eval.
   - What's unclear: Should the lease endpoint serve lichess games (with filtered position set) or return 204 for them?
   - Recommendation: For v1 (scope), return 204 when `is_lichess_eval_game=True`. The complexity of flaw-adjacent filtering and lichess-specific write conventions is a follow-up. Document in PLAN.md.
   - **RESOLVED:** lease endpoint returns 204 for lichess games (`is_lichess_eval_game=True`); flaw-adjacent PV-backfill deferred to a follow-up (v1 serves engine games only). Implemented in 120-02 Task 1.

2. **User_id lookup in submit endpoint for `_signal_flaw_completion`**
   - What we know: `_signal_flaw_completion(user_id)` needs `user_id`. The `game_id` is submitted but not `user_id`.
   - What's unclear: Should the submit payload include `user_id` (worker knows it from lease response), or should the server load it?
   - Recommendation: Include `user_id` in the `LeaseResponse` and `SubmitRequest` to avoid an extra DB query in the submit path. Worker echoes back what the lease gave it.
   - **RESOLVED:** `user_id` is threaded `LeaseResponse → worker → SubmitRequest` (worker echoes it back); the submit endpoint signals flaw completion with `body.user_id`, no extra DB query. Schemas in 120-01, wired in 120-02/120-03.

3. **Constant-time comparison for operator token**
   - What we know: `settings.EVAL_OPERATOR_TOKEN != submitted_token` is a direct string comparison (timing-attack vulnerable if tokens are long and distinct character by character).
   - What's unclear: Does the threat model require constant-time comparison for a server-to-server API over TLS?
   - Recommendation: Use `hmac.compare_digest(settings.EVAL_OPERATOR_TOKEN, submitted_token)` instead of `!=`. It's two lines and eliminates the timing oracle entirely.
   - **RESOLVED:** `require_operator_token` uses `hmac.compare_digest` (never `!=`), fail-closed when the server token is unconfigured. Implemented in 120-02 Task 1; covered by T-120-01.

4. **`_collect_full_ply_targets` is private (underscore-prefixed)**
   - What we know: The function lives in `eval_drain.py` and is imported by the new router.
   - What's unclear: Should it be promoted to a non-underscore name as part of this phase?
   - Recommendation: Rename `_collect_full_ply_targets` → `collect_full_ply_targets` and `_claim_tier3_derived` → `claim_tier3_derived` as part of this phase, since they are now part of a public interface used by two callers.
   - **RESOLVED:** keep private names, import cross-service; rationale: avoid churn in heavily-tested eval_drain/eval_queue_service (sanctioned by PATTERNS.md for this tight coupling).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `require_operator_token` using `Header(alias="X-Operator-Token")` is the right pattern for FastAPI static-secret auth | Q5 Auth pattern | Low — FastAPI Header dependency is well-established; alternative is `APIKeyHeader(name="X-Operator-Token")` which is nearly identical |
| A2 | The worker's `httpx.AsyncClient` timeout of 30s is sufficient for lease/submit round-trips | Q8 CLI | Low — both endpoints are fast DB operations; the 30s covers transient latency |

**If this table is short:** Nearly all claims are verified from direct codebase reading. The architecture is additive over well-understood existing code.

---

## Sources

### Primary (HIGH confidence — direct codebase reads)
- `app/services/eval_queue_service.py` — `_claim_tier3_derived`, `LEASE_TTL_SECONDS`, `WORKER_ID_SERVER_POOL`, `ClaimedJob`
- `app/services/eval_drain.py` — `_collect_full_ply_targets`, `_post_move_eval`, `_apply_full_eval_results`, `_classify_and_fill_oracle`, `_mark_full_evals_completed`, `_mark_full_pv_completed`, `_signal_flaw_completion`, `MAX_EVAL_ATTEMPTS`, `_full_drain_tick`
- `app/services/engine.py` — `EnginePool`, `evaluate_nodes_with_pv`, `_NODES_BUDGET`, `_NODES_TIMEOUT_S`, `_sched_idle_preexec`, `_engine_popen_kwargs`, `PV_CAP_PLIES`
- `app/core/config.py` — `Settings`, `EVAL_AUTO_DRAIN_ENABLED`
- `app/routers/admin.py` — `current_superuser` dependency pattern, thin router style
- `app/routers/imports.py` — `eval/tier1` endpoint pattern, `APIRouter(prefix=...)` convention
- `app/main.py` — router registration pattern
- `app/models/game.py` — `full_evals_completed_at`, `lichess_evals_at`, `needs_engine_full_evals`, `full_eval_attempts`
- `app/models/game_position.py` — column set (no FEN column confirmed)
- `.planning/seeds/SEED-048-headless-remote-eval-worker.md` — D-1 through D-6 locked decisions
- `scripts/backfill_eval.py` — `EnginePool` usage, worker CLI pattern
- `scripts/resweep_holed_games.py` — script path bootstrap, argparse, asyncio.run pattern
- `tests/routers/test_imports_tier1_enqueue.py` — httpx ASGITransport test pattern
- `tests/services/test_full_eval_drain.py` — session monkeypatching pattern

### Secondary (MEDIUM confidence — live execution)
- `protocol.id` → `{"name": "Stockfish 18", ...}` — confirmed via live `chess.engine.popen_uci` call on dev machine

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all libraries confirmed in `pyproject.toml`
- Architecture: HIGH — all functions directly read; patterns confirmed in existing code
- Storage convention: HIGH — traced through `_post_move_eval` → `_apply_full_eval_results` in full
- Pitfalls: HIGH — derived from direct reading of `_full_drain_tick` session discipline and D-2/SEED-044 comments

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable domain; `eval_drain.py` changes would invalidate Section Q3)
