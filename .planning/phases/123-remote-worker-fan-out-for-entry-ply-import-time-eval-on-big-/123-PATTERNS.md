# Phase 123: Remote-worker fan-out for entry-ply (import-time) eval - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 7 surfaces (1 new migration, 5 modified, 1 test extension)
**Analogs found:** 7 / 7 (every surface has an in-repo analog)

> **Read-the-research-first note (from RESEARCH §Metadata "decision conflicts"):**
> D-01 says the server path mirrors "the same SKIP LOCKED LIFO claim shape as the remote endpoint,"
> but **neither the server lease nor the remote `/entry-lease` exists yet.** Today
> `_pick_pending_game_ids` is a plain unlocked `SELECT … ORDER BY id DESC LIMIT n` (eval_drain.py:1016-1030).
> Both new claim sites must call **one shared new SKIP-LOCKED helper** (the SEED-051 D-3 shape).
> The closest *shape* analog to copy is `_claim_queued_job` (eval_queue_service.py:190-223), which locks
> `eval_jobs`; here you lock `games`. Do NOT go hunting for a pre-existing entry-ply lease — there is none.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `alembic/versions/<new>_phase_123_entry_eval_lease.py` | migration | DDL/batch | `20260614_150000_phase_119_eval_drain_coverage.py` (col+index) / `20260521_..._add_evals_completed_at_to_games.py` (nullable col+partial index) | exact (add nullable cols to `games`) |
| `app/models/game.py` (2 mapped_columns) | model | — | existing `evals_completed_at` / `full_evals_completed_at` mapped_columns (game.py:154-170) | exact |
| `app/services/eval_drain.py` (shared claim helper + D-01 lease in `_pick_pending_game_ids` + constants) | service | event-driven / batch-claim | `_claim_queued_job` SKIP-LOCKED CTE (eval_queue_service.py:190-223) for the claim; `_pick_pending_game_ids` (eval_drain.py:1016) for the call site | exact (shape) / role-match (call site is unlocked today) |
| `app/services/eval_queue_service.py` (`scope` param on `claim_eval_job`) | service | request-response | `claim_eval_job` (eval_queue_service.py:456) decomposed into `_claim_queued_job` + `_claim_tier3_derived` | exact (thin selector) |
| `app/routers/eval_remote.py` (`scope` param, `/entry-lease`, `/entry-submit`, `X-Worker-Id`) | router | request-response | `/lease`+`/submit` endpoints + `_build_lease_positions` + `_apply_submit` (eval_remote.py:108-426) | exact |
| `app/schemas/eval_remote.py` (Entry* schemas) | schema | — | `LeasePosition`/`LeaseResponse`/`SubmitEval`/`SubmitRequest`/`SubmitResponse` (eval_remote.py schemas, full file) | exact |
| `scripts/remote_eval_worker.py` (ladder, `--worker-id`, `X-Worker-Id`, depth-15 path) | utility/CLI | request-response loop | `_run_cycle`/`_run_loop`/`_eval_positions`/`parse_args` (remote_eval_worker.py:75-300) | exact |
| `tests/test_eval_worker_endpoints.py` (entry-lease/submit/scope/worker-id tests) | test | — | existing lease/submit/Tier1 tests + fixtures (test_eval_worker_endpoints.py:1-235) | exact |

---

## Pattern Assignments

### `alembic/versions/<new>_phase_123_entry_eval_lease.py` (migration, DDL)

**Analog:** `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` (nullable col + partial index on `games`) and `20260614_150000_phase_119_eval_drain_coverage.py` (manual revision IDs, multi-op upgrade, explicit downgrade).

**Current Alembic head (use as `down_revision`):** `7d5a4aa09a47` (verified via `uv run alembic heads`). RESEARCH §Code Examples says `20260615_202440_7d5a4aa09a47`.

**Manual revision header pattern** (119 migration, lines 15-24 — this project hand-writes revision IDs, does NOT autogenerate the file scaffold):
```python
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260616..."          # new manual ID (date-stamp style)
down_revision: Union[str, None] = "7d5a4aa09a47"   # current head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Upgrade — add two nullable cols** (mirror evals_completed_at migration lines 41-44 for the col; D-09 forces `String(16)` for `entry_eval_leased_by`, NOT `Text`):
```python
def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("entry_eval_lease_expiry", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "games",
        sa.Column("entry_eval_leased_by", sa.String(16), nullable=True),  # D-09: VARCHAR(16), not TEXT
    )
```

**Downgrade — reverse order** (119 migration lines 64-80 pattern):
```python
def downgrade() -> None:
    op.drop_column("games", "entry_eval_leased_by")
    op.drop_column("games", "entry_eval_lease_expiry")
```

**Index strategy (Claude's Discretion / RESEARCH Assumption A2):** the existing `ix_games_evals_pending` (on `id`, `WHERE evals_completed_at IS NULL`, defined in the evals_completed_at migration lines 49-55) already backs both the LIFO `ORDER BY id DESC` claim and the D-5 `OFFSET` probe. **No new index is required for v1.** Add one only if a measured plan regression appears (deferred-tuning). NO backfill needed — NULL = unclaimed is the correct default (contrast: both analog migrations DO backfill; this one must NOT).

---

### `app/models/game.py` (model — 2 new mapped_columns)

**Analog:** `evals_completed_at` / `full_evals_completed_at` / `lichess_evals_at` mapped_columns (game.py:154-170).

**Existing timestamp-column shape** (game.py:154-156):
```python
evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
```

**New columns to add** (place in the same Timestamps/eval-marker block; the `String(16)` mirrors D-09):
```python
# Phase 123 SEED-051 D-3/D-9: entry-ply (import-time) lease for remote-worker fan-out.
entry_eval_lease_expiry: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
entry_eval_leased_by: Mapped[str | None] = mapped_column(
    sa.String(16), nullable=True  # D-09: worker-id label; VARCHAR(16) not TEXT
)
```

**`__table_args__` note** (game.py:47-72): partial indexes on `games` live in the **migration only**, declared as a comment here (see the Phase 119 SEED-046 comment at lines 69-71). Follow that convention — do NOT add a new `Index(...)` to `__table_args__` unless the migration adds one (it should not, per A2).

---

### `app/services/eval_drain.py` (service — shared claim helper + D-01 + constants)

**Analog for the claim shape:** `_claim_queued_job` SKIP-LOCKED CTE (eval_queue_service.py:190-223). **Analog for the call site:** `_pick_pending_game_ids` (eval_drain.py:1016-1030, currently UNLOCKED).

**Constants placement (D-03)** — module-level named constants near the helper. Mirror the `eval_queue_service.py` constant block (lines 60-69) and the inline-comment-with-rationale style:
```python
# ─── Phase 123 SEED-051: entry-ply remote-fan-out lease constants (D-03/D-04/D-05) ───
ENTRY_LEASE_TTL_SECONDS: int = 20          # D-04: short — entry batches are seconds of work; << full-ply LEASE_TTL_SECONDS=120
ENTRY_LEASE_BATCH_SIZE: int = 50           # D-5 starting knob
ENTRY_LEASE_BACKLOG_THRESHOLD: int = 300   # D-5 starting knob; probe uses THRESHOLD-1 as OFFSET
```
(Planner picks the exact TTL value per D-04 — RESEARCH Pitfall 3 recommends 15-30s.)

**Shared SKIP-LOCKED LIFO claim helper (NEW — the canonical primitive, RESEARCH Pattern 1).** Copy the parameter-binding discipline of `_claim_queued_job` (every value bound as `:param`, NO f-string). Locks `games` instead of `eval_jobs`:
```python
async def _claim_entry_eval_games(
    session: AsyncSession, worker_id: str, batch_size: int, ttl_seconds: int
) -> list[int]:
    """Atomically claim up to batch_size pending entry-ply games (LIFO id DESC) and
    stamp their lease. Shared by _pick_pending_game_ids (server, D-01) and /entry-lease
    (remote, D-05/D-07). SEED-051 D-3 shape; mirrors _claim_queued_job's bound-param rule."""
    result = await session.execute(
        sa.text("""
            UPDATE games
            SET entry_eval_lease_expiry = now() + (:ttl || ' seconds')::interval,
                entry_eval_leased_by = :worker_id
            WHERE id IN (
                SELECT id FROM games
                WHERE evals_completed_at IS NULL
                  AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
                ORDER BY id DESC                       -- LIFO: newest import first (D-3)
                LIMIT :batch
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
        """),
        {"ttl": str(ttl_seconds), "worker_id": worker_id, "batch": batch_size},
    )
    return [row[0] for row in result.all()]
```
Note the `(:ttl || ' seconds')::interval` and `str(ttl_seconds)` binding are copied **verbatim** from `_claim_queued_job` line 217 + 222 — same TTL idiom.

**D-01: `_pick_pending_game_ids` becomes a lease claim.** Today (eval_drain.py:1016-1030) it is an unlocked `SELECT`. Replace its body with a call to `_claim_entry_eval_games(session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS)`. Keep the short-session wrapper (`async with async_session_maker() as session:`) and **commit** so the lease is durable before the engine work begins (mirror `claim_eval_job`'s commit-then-release discipline, eval_queue_service.py:473-475). Import `WORKER_ID_SERVER_POOL` from `eval_queue_service` (it is the existing "server-pool" constant, eval_queue_service.py:69).

**FEN derivation reuse (D-2, RESEARCH Pattern 2):** `/entry-lease` calls `_collect_eval_targets_from_db(session, game_ids, pgn_map)` (eval_drain.py:1066) — already a single-walk-per-game builder returning `_EvalTarget` objects each carrying `.game_id`, `.ply`, `.board` (a `board.copy()` snapshot at the pre-push ply). Build the lease payload as `{game_id, ply, fen}` via `target.board.fen()` (same `.fen()` the full-ply `_build_lease_positions` uses at eval_remote.py:144). PGNs come from `_load_pgns_for_games` (eval_drain.py:1033).

**Entry-submit write path reuse (D-2 / SEED-044, RESEARCH Pattern 4):** use these three EXISTING helpers (the SAME ones `run_eval_drain` uses for entry-ply):
- `_apply_eval_results(session, eval_targets, eval_results)` (eval_drain.py:959) — **position-keyed, NO +1 shift.** Critical: do NOT use `_apply_full_eval_results` (that one shifts; it is the full-ply path used by `/submit`). See Anti-pattern below.
- `_classify_and_insert_flaws(session, game_ids)` (eval_drain.py:1133) — ON CONFLICT DO NOTHING, idempotent.
- `_mark_evals_completed(session, game_ids)` (eval_drain.py:1040) — executemany UPDATE stamping `evals_completed_at = now()`; permanent lease release (the queue predicate `evals_completed_at IS NULL` stops matching).

---

### `app/services/eval_queue_service.py` (`scope` param on `claim_eval_job`, D-05)

**Analog:** `claim_eval_job` (eval_queue_service.py:456-509) — already decomposed; `scope` is a thin selector, not a rewrite. **Real function names** (RESEARCH Pattern 3 correction to CONTEXT D-05): tier-1/2 = `_claim_queued_job` (line 171), tier-3 = `_claim_tier3_derived` (line 241).

**Current structure to branch on** (lines 467-509): sweep → `_claim_queued_job` → if None, gate on `EVAL_AUTO_DRAIN_ENABLED` → `_claim_tier3_derived`.

**Add the param** (mirror the `Literal` discipline already in this file, e.g. `EvalJobStatus` at line 72; CLAUDE.md "never bare str for fixed sets"):
```python
async def claim_eval_job(
    worker_id: str = WORKER_ID_SERVER_POOL,
    scope: Literal["explicit", "idle"] | None = None,   # D-05: None = today's bundled tier1>2>3
) -> ClaimedJob | None:
```
- `scope is None` → **unchanged** existing flow (backward-compat for old workers — Pitfall 4).
- `scope == "explicit"` → run only `_claim_queued_job`; return None if empty (skip tier-3 fallthrough).
- `scope == "idle"` → skip `_claim_queued_job`; run only `_claim_tier3_derived` (still gated by `EVAL_AUTO_DRAIN_ENABLED`, line 492).

---

### `app/routers/eval_remote.py` (router — `scope` param, `/entry-lease`, `/entry-submit`, `X-Worker-Id`)

**Analog:** `/lease`+`/submit` endpoints (eval_remote.py:313-426), `_build_lease_positions` (108), `_apply_submit` (160), `require_operator_token` (70), `_WORKER_ID_REMOTE` (60).

**Auth reuse (unchanged):** every new endpoint takes `_auth: Annotated[None, Depends(require_operator_token)]` (eval_remote.py:315). Operator token is the only authz gate.

**`X-Worker-Id` header (D-10)** — mirror the existing `X-Operator-Token` header dependency (eval_remote.py:70-71, `Header(alias=...)` + None default → fallback). The worker-id is **advisory only** (RESEARCH §Security V4 — never derive ownership from it):
```python
async def worker_id_label(
    x_worker_id: Annotated[str | None, Header(alias="X-Worker-Id")] = None,
) -> str:
    # D-10: absent header (old worker) → fall back to "remote-worker" (same backward-compat as scope).
    return x_worker_id or _WORKER_ID_REMOTE
```
Then pass this label into the claim (`claim_eval_job(worker_id=...)` and `_claim_entry_eval_games(..., worker_id=...)`). For the full-ply `/lease` (line 337) this REPLACES the hardcoded `_WORKER_ID_REMOTE` so `eval_jobs.leased_by` becomes per-worker. (Note: `eval_jobs.leased_by` is `String(100)`, so the 16-char cap only bites on the new `games.entry_eval_leased_by` — RESEARCH Pitfall 5.)

**`scope` param on `/lease` (D-05)** — add a query param and pass through to `claim_eval_job`. Keep `response_model=None` and the `Response | LeaseResponse` return (eval_remote.py:313-316). Absent `scope` → today's exact bundled behavior.

**NEW `/entry-lease` endpoint (D-07).** Structure mirrors `/lease` (eval_remote.py:313-395) but batched:
1. D-5 backlog existence probe FIRST (RESEARCH Pattern 5; `OFFSET = ENTRY_LEASE_BACKLOG_THRESHOLD - 1`, Pitfall 6). If not deep enough → `Response(status_code=status.HTTP_204_NO_CONTENT)` (worker falls to `scope=idle`):
```python
probe = await session.execute(
    sa.text("""
        SELECT 1 FROM games
        WHERE evals_completed_at IS NULL
        ORDER BY id DESC
        LIMIT 1 OFFSET :offset
    """),
    {"offset": ENTRY_LEASE_BACKLOG_THRESHOLD - 1},
)
if probe.scalar_one_or_none() is None:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```
2. `game_ids = await _claim_entry_eval_games(session, worker_id_label, ENTRY_LEASE_BATCH_SIZE, ENTRY_LEASE_TTL_SECONDS)`; if empty → 204.
3. Derive `{game_id, ply, fen}[]` via `_collect_eval_targets_from_db` + `target.board.fen()` (D-2).
4. Return an `EntryLeaseResponse`.
   - Session discipline: mirror the existing read-session-then-close pattern in `_apply_submit` (eval_remote.py:172-205) and `/lease` (358-382). The claim UPDATE must `commit()` before the engine work the worker does — but here the worker is remote, so commit the claim, return the FENs, and let `/entry-submit` open its own write session.

**NEW `/entry-submit` endpoint (D-07).** Structure mirrors `/submit` + `_apply_submit` (eval_remote.py:160-305, 398-425) but **batched across games** and using the **no-shift** write path:
- D-5 SF-version gate FIRST (eval_remote.py:413-420) — copy verbatim.
- For each submitted game: re-derive `_EvalTarget`s server-side from `game_id` (so ply/endgame_class are server-controlled — Pitfall 1), zip the worker's `{ply: (eval_cp, eval_mate)}` onto them by ply.
- Apply via `_apply_eval_results` (NO shift) → `_classify_and_insert_flaws` → `_mark_evals_completed` (the three eval_drain helpers above). This is the ONE place the entry-submit diverges from `/submit` (which uses `_apply_full_eval_results` WITH shift).
- Idempotent by construction (completion stamp + ON CONFLICT DO NOTHING). Optionally NULL `entry_eval_lease_expiry` for a clean "in flight" view (RESEARCH Open Q2 — correctness comes from the completion stamp regardless).

---

### `app/schemas/eval_remote.py` (Pydantic schemas)

**Analog:** `LeasePosition`/`LeaseResponse`/`SubmitEval`/`SubmitRequest`/`SubmitResponse` (full file).

**Existing shapes to copy** (note `Field(ge=0)` on ply, `Field(max_length=MAX_SUBMIT_EVALS)` cap — RESEARCH §Security V5):
```python
class LeasePosition(BaseModel):
    ply: int = Field(ge=0)
    fen: str
    is_terminal: bool

class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None
    pv: str | None

class SubmitRequest(BaseModel):
    ...
    evals: list[SubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)
```

**New entry-ply schemas** (entry-ply carries NO best_move/pv — depth-15 returns only cp/mate; batched across games, so each position needs `game_id`):
```python
class EntryLeasePosition(BaseModel):
    game_id: int
    ply: int = Field(ge=0)
    fen: str

class EntryLeaseResponse(BaseModel):
    positions: list[EntryLeasePosition]
    leased_at: datetime

class EntrySubmitEval(BaseModel):
    game_id: int
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None

class EntrySubmitRequest(BaseModel):
    sf_version: str
    evals: list[EntrySubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)  # reuse existing cap (V5 DoS guard)

class EntrySubmitResponse(BaseModel):
    game_ids: list[int]
    stamped_count: int
```
(Reuse the existing `MAX_SUBMIT_EVALS = 1024` constant, schemas line 10 — or bump it if a 50-game batch × ~3 plies exceeds it; 150 < 1024, so it fits as-is.)

---

### `scripts/remote_eval_worker.py` (CLI — ladder, `--worker-id`, `X-Worker-Id`, depth-15)

**Analog:** `_eval_positions` (75-99), `_run_cycle` (141-193), `parse_args` (243-300), client header wiring (220-224).

**Depth-15 entry eval (NEW helper, RESEARCH §Code Examples).** Copy `_eval_positions` (lines 75-99) but call `pool.evaluate(b)` (engine.py:451, returns `tuple[int|None, int|None]` at `_DEPTH=15`) NOT `pool.evaluate_nodes_with_pv(b)` (line 89, the 1M-node full-ply mode — Anti-pattern below). Output carries only `eval_cp`/`eval_mate`:
```python
async def _eval_entry_positions(pool, positions):
    boards = [chess.Board(str(p["fen"])) for p in positions]
    results = await asyncio.gather(*(pool.evaluate(b) for b in boards))  # depth-15
    return [
        {"game_id": p["game_id"], "ply": p["ply"], "eval_cp": r[0], "eval_mate": r[1]}
        for p, r in zip(positions, results)
    ]
```

**D-06 ladder in `_run_cycle`** (restructure lines 154-193). Current cycle is a single `client.post("/api/eval/remote/lease")`. New order: `scope=explicit` → if 204, `/entry-lease` → if 204, `scope=idle`:
```python
lease_resp = await client.post("/api/eval/remote/lease", params={"scope": "explicit"})
if lease_resp.status_code == 204:
    entry_resp = await client.post("/api/eval/remote/entry-lease")  # gated by D-5 probe
    if entry_resp.status_code == 204:
        lease_resp = await client.post("/api/eval/remote/lease", params={"scope": "idle"})
        # ... tier-3 handling as today ...
    else:
        # ... _eval_entry_positions (depth-15) → POST /entry-submit ...
```
The full-ply submit path (lines 177-191) is the analog for the `/entry-submit` POST body shape (`{sf_version, evals, ...}`).

**`X-Worker-Id` header (D-10)** — set once on the `httpx.AsyncClient` alongside the existing `X-Operator-Token` (lines 220-224). No per-call change:
```python
async with httpx.AsyncClient(
    base_url=base_url,
    headers={"X-Operator-Token": token, "X-Worker-Id": worker_id},
    timeout=HTTP_TIMEOUT_S,
) as client:
```

**`--worker-id` flag (D-10)** — mirror the `--workers`/`--idle-sleep` validation pattern in `parse_args` (lines 266-300). Random base36 default (~8 chars), operator override validated `< 10` chars (Pitfall 5: must fit `VARCHAR(16)`):
```python
parser.add_argument("--worker-id", default=None, metavar="ID",
    help="Distinctive worker identity for leased_by columns. Default: random ~8-char base36.")
...
# after parse, in main() or parse_args:
if args.worker_id is not None and len(args.worker_id) >= 10:
    parser.error(f"--worker-id must be < 10 chars, got {len(args.worker_id)}")
```
Generate the random default at process startup (e.g. base36 of `secrets`/`uuid` truncated to 8). Thread it through `run_worker` → the client header.

---

### `tests/test_eval_worker_endpoints.py` (test extension)

**Analog:** existing lease/submit auth tests + `TestTier1Claiming` + the fixture block (lines 1-235). **No new conftest infra needed** (RESEARCH §Wave 0).

**Reusable fixtures/helpers (extend directly):**
- `eval_worker_session_maker` (line 65), `eval_worker_test_user` (line 71).
- `_insert_game(...)` (line 97) — **note: it sets `evals_completed_at=now()` by default** (line 119). For entry-ply pending-queue tests you MUST pass `evals_completed_at=None` (add a kwarg, mirroring the existing `full_evals_completed_at` kwarg at line 102). This is the single fixture change required.
- `_insert_game_positions` (line 131), `_get_game_position` (line 163), `_delete_games` (line 203).
- `_make_client()` (line 217) — ASGI transport client.
- `_patch_router_session(monkeypatch, session_maker)` (line 222) — routes the router's `async_session_maker` to the test DB. Reuse verbatim.
- `_TEST_TOKEN` (line 55), `_TEST_USER_ID` (line 58), `_TWO_MOVE_PGN` (line 52).

**Test shapes to copy:** `test_lease_returns_positions` (line 295, for `/entry-lease` 200 + payload), `test_submit_applies_post_move_shift` (line 422, but INVERT — assert entry evals land at `ply` NOT `ply-1`), `test_submit_idempotent` (line 556), `test_submit_stamps_full_evals_completed_at` (line 501, but check `evals_completed_at`). `TestTier1Claiming` (line 676) + `_seed_eval_job` (line 649) are the analog for the `scope` tests.

**New tests required (RESEARCH §Test Map):** `entry_lease` (payload), `entry_lease_gate` (204 when backlog < threshold — insert exactly threshold-1 vs threshold pending games), `entry_submit_no_shift`, `entry_submit_stamps`, `entry_submit_idempotent`, `scope` (explicit=tier1/2 only, idle=tier3 only, absent=bundled), `worker_id` (header populates `leased_by`/`entry_eval_leased_by`; absent → "remote-worker"), `lease_partition` (two concurrent `_claim_entry_eval_games` calls return disjoint id sets — the SKIP-LOCKED contract).

---

## Shared Patterns

### Auth (operator token)
**Source:** `require_operator_token` (eval_remote.py:70-100) — fail-closed (403 unconfigured), 401 wrong token, `hmac.compare_digest` over UTF-8 bytes.
**Apply to:** every new endpoint (`/entry-lease`, `/entry-submit`) via `Depends(require_operator_token)`. UNCHANGED — do not re-implement.

### Bound-param SKIP-LOCKED claim (security rule)
**Source:** `_claim_queued_job` (eval_queue_service.py:190-223) — `sa.text` with ALL values bound as `:params`, NEVER f-string interpolated (file docstring lines 32-35).
**Apply to:** the new `_claim_entry_eval_games` helper AND the D-5 probe. `worker_id`, `ttl`, `batch`, `offset` are ALL `:params` (RESEARCH §Security; Anti-pattern below).

### Short-session discipline (no lock across engine work)
**Source:** `claim_eval_job` (eval_queue_service.py:467-475) — sweep+commit, then claim+commit in a fresh session; the SKIP-LOCKED lock releases on commit, never held across the gather. `_apply_submit` (eval_remote.py:172-205) — read session closed BEFORE CPU work.
**Apply to:** `_pick_pending_game_ids` (commit the lease before drain runs) and `/entry-lease` (commit the claim before returning FENs). Never `asyncio.gather` on one open session (CLAUDE.md hard rule).

### Backward-compat-by-optional-param (mixed-fleet rollout)
**Source:** Phase 121's additive `/lease` release path + the `X-Operator-Token` `Header(default=None)` pattern (eval_remote.py:71).
**Apply to:** `scope=None → bundled` (D-05) and `X-Worker-Id absent → "remote-worker"` (D-10). Both new params MUST default such that an un-updated worker gets the exact pre-phase behavior (Pitfall 4). Deploy server first, upgrade workers at leisure.

### Idempotent submit
**Source:** `_classify_and_insert_flaws` (ON CONFLICT DO NOTHING) + `_mark_evals_completed` (re-stamp is harmless) + the queue predicate `evals_completed_at IS NULL`.
**Apply to:** `/entry-submit` — double-submit and server/remote overlap are correctness-safe (RESEARCH Pitfall 2). The completion stamp is the permanent lease release.

---

## Anti-Patterns (from RESEARCH — the planner MUST encode these as guardrails)

| Anti-pattern | Correct pattern | Source |
|--------------|-----------------|--------|
| Using `_apply_full_eval_results` (+1 shift) in `/entry-submit` | Use `_apply_eval_results` (eval_drain.py:959, NO shift) — entry-ply evals are position-keyed at the entry ply | Pitfall 1 / Pattern 4 |
| Calling `pool.evaluate_nodes_with_pv` for entry-ply (1M-node, 10x slower) | Call `pool.evaluate` (engine.py:451, depth-15) | Anti-Patterns / engine.py |
| f-string-interpolating `worker_id`/`ttl`/`offset` into `sa.text` | Bind every value as `:param` | Security V5 / `_claim_queued_job` |
| Gating the server pool on backlog depth | D-02: only `/entry-lease` runs the D-5 probe; server always drains | D-02 |
| Worker deriving entry-ply targets from `game_id` | Server ships `{game_id, ply, fen}`; worker returns `{game_id, ply, eval_cp, eval_mate}` (D-2) | Anti-Patterns |
| `OFFSET 300` for threshold 300 | `OFFSET = THRESHOLD - 1` (= 299) | Pitfall 6 |
| Deriving ownership/authz from `X-Worker-Id` | Advisory label only; owner derived from the game row (eval_remote.py:189) | Security V4 |
| `Text` for `entry_eval_leased_by` | `String(16)` — D-09 | D-09 |

## No Analog Found

None. Every surface in this phase has a direct in-repo analog (this is an integration-mapping phase, not a greenfield one). The single nuance — the shared SKIP-LOCKED `games` claim is NEW — has a structural analog in `_claim_queued_job` (locks `eval_jobs`); only the locked table differs.

## Metadata

**Analog search scope:** `app/routers/eval_remote.py`, `app/services/eval_queue_service.py`, `app/services/eval_drain.py`, `app/services/engine.py`, `app/models/game.py`, `app/schemas/eval_remote.py`, `scripts/remote_eval_worker.py`, `alembic/versions/` (3 migrations read), `tests/test_eval_worker_endpoints.py`.
**Files scanned (read in full or targeted):** 9.
**Current Alembic head (down_revision for new migration):** `7d5a4aa09a47` (verified via `uv run alembic heads`).
**Pattern extraction date:** 2026-06-16
