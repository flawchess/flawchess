# Phase 123: Remote-worker fan-out for entry-ply (import-time) eval on big first imports - Research

**Researched:** 2026-06-16
**Domain:** Async job-queue lease/fan-out over an existing FastAPI + asyncpg + SQLAlchemy-2.x remote eval worker
**Confidence:** HIGH (this is an integration-mapping phase; all anchors verified by reading the live code)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01…D-10 — NOT re-opened)
- **D-01:** The in-process server drain claims through the new lease column in v1 — server and remote workers strictly partition the same import; neither double-evaluates a game. `_pick_pending_game_ids` (`app/services/eval_drain.py`) gains the lease predicate `(entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())` and **sets** the lease when it picks (same `SKIP LOCKED` LIFO claim shape as the remote endpoint). Lease ends naturally: stamping `evals_completed_at = now()` on completion is the permanent release; a crashed server pick is reclaimed by the TTL.
- **D-02:** The D-5 backlog-depth gate stays remote-lease-only. The server pool always drains regardless of backlog depth; the existence-probe gate governs only whether `/entry-lease` hands a batch to a remote worker.
- **D-03:** Threshold (300 games), batch size (50 games), and the entry-ply lease TTL are **named module-level constants**, not env vars. Place near the drain / endpoint they govern.
- **D-04:** Entry-ply lease **TTL value** chosen during planning — short, well under the 120s full-ply TTL.
- **D-05:** Worker orchestrates the ladder; `/eval/remote/lease` gains an **optional `scope` param**: absent → today's bundled tier-1>2>3 (un-updated workers unchanged); `scope=explicit` → tier-1/2 only (`_claim_tier1_2_queued`); `scope=idle` → tier-3 only (`_claim_tier3_derived`).
- **D-06:** New worker per cycle: `scope=explicit` → if 204, `/entry-lease` (gated batch) → if empty, `scope=idle`. Up to 3 round-trips, only on the idle path.
- **D-07:** Endpoints stay single-purpose: separate **batched `/entry-lease`** and **batched `/entry-submit`**, NOT a discriminated-union overload of `/lease`.
- **D-08:** Entry-ply is **ON by default** in the upgraded worker (no opt-in flag); the D-5 backlog gate makes always-on safe.
- **D-09:** Add optional **`entry_eval_leased_by` VARCHAR(16)** on `games` alongside `entry_eval_lease_expiry` (worker-identifier, set at lease time). Do NOT use `TEXT`.
- **D-10:** Each worker self-assigns a **distinctive ID** (random per process, ~8-char base36; `--worker-id` override validated < 10 chars) instead of the constant `_WORKER_ID_REMOTE = "remote-worker"`. Used for **both** `eval_jobs.leased_by` and the new `entry_eval_leased_by`. Transport: `X-Worker-Id` HTTP header; absent header → server falls back to `"remote-worker"`.

### Claude's Discretion
- Exact lease-claim SQL shape for the server-side path (mirror the remote endpoint's `SKIP LOCKED` LIFO claim).
- Exact module placement of the constants.
- `X-Worker-Id` exact header name.
- base36 length/charset for the random worker ID (must fit `VARCHAR(16)`).
- Migration index strategy for the new lease columns (reuse / extend `ix_games_evals_pending` where it helps).

### Deferred Ideas (OUT OF SCOPE)
- Backlog-gate threshold tuning (300/50/TTL re-measured once live).
- macOS background-scheduling caveat (depth-15 at default priority on a MacBook worker) — no v1 action.
</user_constraints>

## Summary

This is a small, well-bounded delta over the Phase 120/121 remote eval worker. Every decision is locked; the work is "wire a second, higher-priority work type (entry-ply, depth-15) into the existing lease/submit machinery." There is no new architecture to discover, only existing shapes to mirror.

The five integration surfaces are all present and clean: (1) `eval_drain.py` already owns the entry-ply FEN-derivation pipeline (`_collect_eval_targets_from_db` → `_collect_eval_targets_per_game` → `_collect_target_specs`/`_snapshot_boards`) and the completion stamp (`_mark_evals_completed`); (2) `eval_remote.py` has the auth dependency, the SEED-044 write split, and the `/lease`+`/submit` contract to copy; (3) `eval_queue_service.py` already decomposes into `_claim_queued_job` (tier-1/2) and `_claim_tier3_derived` (tier-3), so the D-05 `scope` param is a thin selector; (4) the worker CLI's `_run_cycle` is a single lease→eval→submit call to extend into the D-06 ladder; (5) `EnginePool.evaluate(board)` is the depth-15 mode the worker needs (it currently only calls `evaluate_nodes_with_pv`).

**One naming reality the planner must absorb:** D-01 says the server path mirrors "the same `SKIP LOCKED` LIFO claim shape as the remote endpoint." Today `_pick_pending_game_ids` is a plain unlocked `SELECT … ORDER BY id DESC LIMIT n` (NO lease, NO `SKIP LOCKED`). The remote `/entry-lease` endpoint does not exist yet. So both the server lease and the remote lease are NEW in this phase and must share a single canonical claim shape (the SEED-051 D-3 SQL block). The planner should write one helper that both call, not "copy the existing one."

**Primary recommendation:** Build one shared `SKIP LOCKED` LIFO claim function over `games` (the SEED-051 D-3 `UPDATE … RETURNING id` block), parameterize it by batch size and worker_id, and have BOTH `_pick_pending_game_ids` (D-01, server) and the new `/entry-lease` endpoint (D-05/D-07, remote) call it. Reuse `_collect_eval_targets_from_db` verbatim for FEN derivation; reuse `_apply_eval_results` + `_classify_and_insert_flaws` + `_mark_evals_completed` verbatim for the `/entry-submit` write path. Keep the worker a dumb depth-15 FEN→eval node (D-2).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Entry-ply lease claim (server + remote) | API/Service (`eval_drain` + `eval_remote`) | DB (`games` lease column, `SKIP LOCKED`) | Claim is a DB-atomic operation; the predicate/partition lives server-side (D-1/D-2) |
| Entry-ply FEN derivation | API/Service (`eval_drain._collect_eval_targets_*`) | DB (read GamePosition + Game.pgn) | D-2: derive stays server-side; worker never parses PGN |
| Depth-15 Stockfish eval | Remote worker (`EnginePool.evaluate`) | — | The only compute that crosses the wire (D-2) |
| Entry-ply storage (post-move shift, flaw classify, stamp) | API/Service (`_apply_eval_results`, `_classify_and_insert_flaws`, `_mark_evals_completed`) | DB | D-2 + SEED-044: server owns ALL storage convention |
| Backlog-depth gate (existence probe) | API/Service (`/entry-lease` only) | DB (`ix_games_evals_pending`) | D-02: remote-lease-only; server always drains |
| Worker ladder orchestration | Remote worker (`_run_cycle`/`_run_loop`) | — | D-05/D-06: worker drives the 3-rung order across endpoints |
| Worker identity | Remote worker (gen) → API (`X-Worker-Id` header → `entry_eval_leased_by`/`leased_by`) | DB | D-10: observability column population |

## Standard Stack

This phase adds **no new packages.** It is pure integration within the existing backend stack.

### Core (already present, verified by reading the code)
| Library | Version (pinned) | Purpose | Why Standard |
|---------|------------------|---------|--------------|
| FastAPI | 0.13x (CLAUDE.md) | the `/eval/remote/*` router | already hosts `/lease`+`/submit` |
| SQLAlchemy (async) | 2.x | `select()`/`update()` + `sa.text()` raw CTE for the claim | project standard; `_claim_queued_job` already uses `sa.text` SKIP LOCKED |
| asyncpg | — | Postgres driver | project standard |
| python-chess | 1.11.x | PGN replay → FEN, board eval | `_build_lease_positions`, `_collect_eval_targets_per_game` |
| httpx (AsyncClient) | — | worker→API transport | already used in `remote_eval_worker.py` |
| Pydantic | v2 | request/response schemas in `app/schemas/eval_remote.py` | `LeasePosition`/`LeaseResponse`/`SubmitRequest`/`SubmitResponse` exist |
| Alembic | — | the one new migration (2 nullable `games` columns) | project standard |

**Installation:** none. `npm/pip/uv` add nothing.

## Package Legitimacy Audit

Not applicable — no external packages are installed in this phase. (All dependencies are already in `pyproject.toml` and exercised by the Phase 120/121 code this extends.)

## Architecture Patterns

### System Architecture Diagram (the D-06 worker ladder + dual claimers)

```
                          ┌─────────────────────────────────────────────┐
                          │  games WHERE evals_completed_at IS NULL      │
                          │  (entry-ply queue; LIFO id DESC)             │
                          │  + entry_eval_lease_expiry / _leased_by      │ ← NEW lease cols (D-3/D-9)
                          └───────────────▲───────────────▲──────────────┘
                                          │               │  SKIP LOCKED LIFO claim (shared helper)
              ┌───────── server pool ─────┘               └───── remote worker(s) ─────┐
              │ run_eval_drain (in-proc)                          /entry-lease (D-07)   │
              │ _pick_pending_game_ids                            (gated by D-5 probe)  │
              │   + lease predicate (D-01) ──┐                                          │
              │                              │   both derive FENs via                   │
              │                              ▼   _collect_eval_targets_from_db (D-2)    │
              │                     {game_id, ply, fen}[]  ───────────────────────────► │ worker:
              │                                                                         │ EnginePool.evaluate(b)
              │                                                                         │ depth-15 (D-08)
              │  write path (server owns ALL storage, SEED-044):                        │
              │  _apply_eval_results → _classify_and_insert_flaws → _mark_evals_completed
              │                                          ▲                              │
              └──────────────────────────────────────────┘   /entry-submit (D-07) ◄─────┘
                                                              {game_id, ply, eval_cp, eval_mate}[]

  Worker per-cycle ladder (D-06, in _run_cycle):
    POST /lease?scope=explicit  ──204──►  POST /entry-lease  ──empty──►  POST /lease?scope=idle
        │ (tier-1/2)                          │ (entry-ply, gated)            │ (tier-3)
        └─ 200 → eval+/submit                 └─ 200 → eval+/entry-submit     └─ 200 → eval+/submit
```

### Recommended Project Structure (no new files except the migration + worker-id helper)
```
app/
├── services/
│   ├── eval_drain.py          # ADD: shared SKIP-LOCKED entry-ply claim helper;
│   │                          #      D-01 lease predicate in _pick_pending_game_ids;
│   │                          #      entry-ply TTL/threshold/batch constants (D-03)
│   ├── eval_queue_service.py  # ADD: scope param plumbed into claim_eval_job (D-05);
│   │                          #      _claim_queued_job already = "tier1/2"; _claim_tier3_derived = "idle"
│   └── engine.py              # NO change (EnginePool.evaluate already = depth-15)
├── routers/
│   └── eval_remote.py         # ADD: scope param on /lease; new /entry-lease + /entry-submit;
│   │                          #      X-Worker-Id header → leased_by (D-10)
├── schemas/
│   └── eval_remote.py         # ADD: EntryLeasePosition/EntryLeaseResponse/EntrySubmit* schemas
├── models/
│   └── game.py                # ADD: entry_eval_lease_expiry, entry_eval_leased_by mapped_columns
alembic/versions/
│   └── <new>_phase_123_entry_eval_lease.py   # 2 nullable cols + index strategy
scripts/
│   └── remote_eval_worker.py  # ADD: D-06 ladder in _run_cycle; --worker-id flag; X-Worker-Id header;
│                              #      entry-ply depth-15 path (pool.evaluate, NOT evaluate_nodes_with_pv)
tests/
    └── test_eval_worker_endpoints.py  # EXTEND for /entry-lease + /entry-submit + scope param + worker-id
```

### Pattern 1: Shared `SKIP LOCKED` LIFO claim over `games` (the canonical new primitive)
**What:** One function that atomically picks N pending games AND stamps their lease, mirroring the SEED-051 D-3 block. Used by both the server (`_pick_pending_game_ids`, D-01) and the remote `/entry-lease`.
**When to use:** Every entry-ply claim site. Do NOT write two copies.
**Example (the SEED-051 D-3 shape, parameterized — bind values, never f-string per the project Security rule):**
```python
# Source: SEED-051 D-3; mirror of _claim_queued_job's sa.text SKIP LOCKED pattern in
# app/services/eval_queue_service.py:190-223 (params bound, no interpolation).
result = await session.execute(
    sa.text("""
        UPDATE games
        SET entry_eval_lease_expiry = now() + (:ttl || ' seconds')::interval,
            entry_eval_leased_by = :worker_id
        WHERE id IN (
            SELECT id FROM games
            WHERE evals_completed_at IS NULL
              AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
            ORDER BY id DESC            -- LIFO: newest import first (D-11 / SEED-051)
            LIMIT :batch
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id
    """),
    {"ttl": str(ttl_seconds), "worker_id": worker_id, "batch": batch_size},
)
return [row[0] for row in result.all()]
```
Note: this is the canonical `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING` job-queue idiom — identical structure to the existing `_claim_queued_job` (which locks `eval_jobs`); here we lock `games`. `_claim_queued_job` is the verified in-repo precedent for the parameter-binding discipline.

### Pattern 2: FEN derivation reuse (D-2) — the worker never parses PGN
**What:** `/entry-lease` claims game_ids, then derives `{game_id, ply, fen}` exactly as the server drain does.
**Where:** `_collect_eval_targets_from_db(session, game_ids, pgn_map)` (eval_drain.py:1066) returns `_EvalTarget` objects each carrying `game_id`, `ply`, `eval_kind`, `endgame_class`, and a `chess.Board`. For the lease response you need the FEN: `target.board.fen()` (the pre-push board at that ply — same convention `_build_lease_positions` uses for full-ply at line 144). Build `{game_id, ply, fen}` from the returned targets.
**Key:** `_EvalTarget.board` is already a `board.copy()` snapshot at the correct pre-push ply (`_snapshot_boards`, eval_drain.py:807). `board.fen()` gives the full FEN with turn/castling/ep — the worker reconstructs with `chess.Board(fen)` exactly as `_eval_positions` already does (remote_eval_worker.py:88).

### Pattern 3: `scope` param as a thin selector (D-05)
**What:** `claim_eval_job` currently runs tier-1/2 (`_claim_queued_job`) then falls through to tier-3 (`_claim_tier3_derived`). Add a `scope: Literal["explicit", "idle"] | None = None` param:
- `None` → today's exact behavior (tier-1/2 then tier-3) — **backward-compat for un-updated workers**.
- `"explicit"` → run only `_claim_queued_job`; return None if empty (skip tier-3 fallthrough).
- `"idle"` → run only `_claim_tier3_derived` (still gated by `EVAL_AUTO_DRAIN_ENABLED`).
**Where:** `app/services/eval_queue_service.py:456` (`claim_eval_job`). The `/lease` endpoint reads `scope` from the request (query param or body) and passes it through.
**Note:** The naming in CONTEXT D-05 says `_claim_tier1_2_queued` / `_claim_tier3_derived`; the actual function names in the code are **`_claim_queued_job`** (tier-1/2) and **`_claim_tier3_derived`** (tier-3). Same intent, slightly different name for the tier-1/2 helper — the planner should reference the real names.

### Pattern 4: SEED-044 write path reuse for `/entry-submit`
**What:** `/entry-submit` accepts `{game_id, ply, eval_cp, eval_mate}[]` and applies them through the SAME helpers `run_eval_drain` uses:
- `_apply_eval_results(session, eval_targets, eval_results)` (eval_drain.py:959) — applies per-row UPDATEs, position-keyed (NOT the full-ply `_apply_full_eval_results` +1 shift). **Critical:** entry-ply uses `_apply_eval_results`, which writes `eval_cp`/`eval_mate` directly at `target.ply` with NO post-move shift. The +1 shift in `_post_move_eval` is for the FULL-ply path only. Entry-ply targets are already at the correct row (midgame/endgame-span entry plies), so the submit applies them as-is — but the server must re-derive the `_EvalTarget` list from `game_id` (so it controls ply/endgame_class), then zip the worker's submitted evals onto them by ply.
- `_classify_and_insert_flaws(session, game_ids)` (eval_drain.py:1133) — ON CONFLICT DO NOTHING (idempotent).
- `_mark_evals_completed(session, game_ids)` (eval_drain.py:1040) — stamps `evals_completed_at` (permanent lease release per D-01) and clears the lease implicitly (the predicate `evals_completed_at IS NULL` no longer matches).
**Lease clearing:** Because the queue predicate is `evals_completed_at IS NULL`, stamping completion removes the row from the candidate set permanently. You do NOT need to explicitly NULL `entry_eval_lease_expiry` on completion (the SEED-051 D-3 design relies on this). You MAY clear it for tidiness, but the partition correctness comes from the completion stamp.

### Pattern 5: D-5 backlog existence probe (remote-only, D-02)
**What:** Before `/entry-lease` hands out a batch, check whether backlog ≥ threshold using a bounded existence probe (constant-ish cost, no `COUNT(*)`):
```python
# Source: SEED-051 D-5. OFFSET = threshold - 1 (299 for threshold 300).
probe = await session.execute(
    sa.text("""
        SELECT 1 FROM games
        WHERE evals_completed_at IS NULL
        ORDER BY id DESC
        LIMIT 1 OFFSET :offset
    """),
    {"offset": ENTRY_LEASE_BACKLOG_THRESHOLD - 1},
)
backlog_deep_enough = probe.scalar_one_or_none() is not None
```
If not deep enough → return 204 (worker falls to `scope=idle`). The server pool (D-02) never runs this probe; it always drains.

### Anti-Patterns to Avoid
- **Do NOT add a post-move +1 shift in `/entry-submit`.** Entry-ply evals are position-keyed at the entry ply and written directly (`_apply_eval_results`). The +1 shift belongs to the full-ply path only. Mixing them corrupts entry-ply rows. (See Pitfall 1.)
- **Do NOT have the worker derive entry-ply targets from `game_id`.** That duplicates phase-classification (D-2 explicitly rejects it). The worker gets `{game_id, ply, fen}` and returns `{game_id, ply, eval_cp, eval_mate}`.
- **Do NOT f-string-interpolate `worker_id`/`ttl`/`offset` into `sa.text`.** Bind every value as a `:param` (project Security rule, mirrored throughout `eval_queue_service.py`).
- **Do NOT gate the server pool on backlog depth.** D-02: only `/entry-lease` runs the probe.
- **Do NOT call `evaluate_nodes_with_pv` for entry-ply.** That's the 1M-node full-ply mode. Entry-ply is `EnginePool.evaluate(board)` (depth-15). Mixing modes silently makes entry-ply 10x slower and wrong-budget.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic multi-row claim with crash recovery | Manual `SELECT` then `UPDATE` in two statements | `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING` (Pattern 1) | Single-statement atomicity; `SKIP LOCKED` gives each claimer a disjoint batch; TTL reclaims crashes |
| Entry-ply FEN derivation | New PGN-walk in the router | `_collect_eval_targets_from_db` (eval_drain.py:1066) | Already single-walk, already handles lichess-%eval skip (T-78-17), already reused by the server drain |
| Post-move storage / flaw classify / completion stamp | New write logic in `/entry-submit` | `_apply_eval_results` + `_classify_and_insert_flaws` + `_mark_evals_completed` | SEED-044 convention lives in exactly these helpers; idempotent (ON CONFLICT DO NOTHING) |
| Operator auth | New auth check | `Depends(require_operator_token)` (eval_remote.py:70) | Constant-time, fail-closed, already tested |
| Idempotent submit safety | Dedup/locking in the submit path | The existing idempotency (ON CONFLICT for flaws; completion-stamp re-write is a no-op) | Server/remote partition can re-cover the same game harmlessly |
| Stockfish depth-15 eval | New engine call | `EnginePool.evaluate(board)` (engine.py:451) | Already the depth-15 mode; worker already owns an `EnginePool` |

**Key insight:** Nearly every piece this phase needs already exists and is already reused across the server drain and the Phase-120 `/lease`+`/submit`. The phase is "thread the entry-ply work type through the existing seams," not "build new mechanisms."

## Runtime State Inventory

This is **not** a rename/refactor phase (it adds columns + endpoints, changes no stored string keys). The standard 5-category inventory does not apply. The one durable-state consideration:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New `games.entry_eval_lease_expiry`, `games.entry_eval_leased_by` columns — nullable, no backfill needed (NULL = unclaimed, the correct default) | Migration only; no data migration |
| Live service config | None — no external service stores the new column names | None |
| OS-registered state | None | None — verified: no Task Scheduler / systemd refs to entry-ply |
| Secrets/env vars | None new (reuses `EVAL_OPERATOR_TOKEN`, `EXPECTED_SF_VERSION`, `EVAL_AUTO_DRAIN_ENABLED`) | None |
| Build artifacts | None | None |

**Mixed-fleet rollout (the real "runtime state" concern):** Deploy server first; old workers (no `scope`, no `X-Worker-Id`) keep working via the absent-param defaults (D-05/D-10). The new lease columns are nullable so old server code reading `games` is unaffected. No coordinated deploy needed.

## Common Pitfalls

### Pitfall 1: Applying the full-ply +1 post-move shift to entry-ply submits
**What goes wrong:** Entry-ply evals get written one row off, corrupting the midgame/endgame-span-entry eval used by stats.
**Why it happens:** The full-ply path (`_apply_full_eval_results` → `_post_move_eval`, eval_drain.py:366) applies a +1 shift; `/submit` (full-ply) deliberately uses it. A copy-paste from `/submit` to `/entry-submit` would inherit the shift.
**How to avoid:** `/entry-submit` uses `_apply_eval_results` (no shift), the SAME helper `run_eval_drain` uses for entry-ply. Re-derive `_EvalTarget`s server-side from `game_id` (so `endgame_class`/`ply` are server-controlled) and zip the worker's `{ply: (eval_cp, eval_mate)}` onto them.
**Warning signs:** A test asserting entry-ply eval lands at `ply` (not `ply-1`) fails; or stats show entry evals shifted.

### Pitfall 2: Server + remote double-evaluating the same game (the bug D-01 fixes)
**What goes wrong:** Without the D-01 server-side lease, `_pick_pending_game_ids` (unlocked `SELECT`) and a remote `/entry-lease` both grab the same newest games → ~2x wasted depth-15 CPU on exactly the hot set.
**Why it happens:** Today `_pick_pending_game_ids` is `SELECT … ORDER BY id DESC LIMIT n` with NO lease (verified at eval_drain.py:1016-1030). It must become the SKIP-LOCKED claim that also SETS the lease.
**How to avoid:** Both server and remote go through Pattern 1's shared claim. `SKIP LOCKED` + the lease predicate guarantee disjoint batches; the completion stamp ends the lease. Correctness is still safe even on overlap (idempotent submit), but the point of D-01 is to avoid the wasted CPU.
**Warning signs:** Prod metric: entry-ply eval count > positions actually pending; duplicate work in logs.

### Pitfall 3: TTL too long → crashed worker's batch stalls the import tail
**What goes wrong:** A worker claims 50 games, crashes; with a 120s-style TTL those 50 sit leased for 2 minutes before the server pool can reclaim them — visible as a first-import latency spike at the tail.
**Why it happens:** Copying the full-ply `LEASE_TTL_SECONDS = 120` (eval_queue_service.py:65). Entry-ply batches are only **seconds** of work (50 games × 2-3 positions × ~90ms ÷ N cores).
**How to avoid:** D-04 — a short entry-ply TTL as a NEW named constant (e.g. on the order of 15-30s; planner picks the exact value, well under 120s). Place it near the claim helper (D-03).
**Warning signs:** Tail-of-import latency; leased-but-stale games visible in `games WHERE entry_eval_lease_expiry > now()` for longer than a batch should take.

### Pitfall 4: `scope`/`X-Worker-Id` absent-default regressions (backward compat)
**What goes wrong:** An old worker (no `scope`, no `X-Worker-Id`) gets a 422/500 or a behavior change → mixed-fleet breakage during rollout.
**Why it happens:** Making the new params required, or not defaulting `scope=None → bundled` and `X-Worker-Id absent → "remote-worker"`.
**How to avoid:** `scope: ... | None = None` (None = today's bundled behavior). `X-Worker-Id` via `Header(default=None)`; when None, fall back to `_WORKER_ID_REMOTE = "remote-worker"` for `leased_by`. This mirrors Phase 121's additive-optional style and the existing `require_operator_token` header handling (eval_remote.py:71).
**Warning signs:** A test sending no `scope`/`X-Worker-Id` to `/lease` returns anything other than the pre-phase response.

### Pitfall 5: `VARCHAR(16)` overflow from a too-long worker ID
**What goes wrong:** A worker ID > 16 chars truncates or raises on insert into `entry_eval_leased_by` / `leased_by` (note: `eval_jobs.leased_by` is `String(100)` — eval_jobs.py:79 — so the constraint is only on the new `games` column).
**Why it happens:** `--worker-id` accepting an arbitrary string, or a base36 generator producing > 16 chars.
**How to avoid:** D-10 validates `--worker-id < 10 chars`; random base36 default ~8 chars. Both fit `VARCHAR(16)` with headroom. Validate length in `parse_args` (mirror the existing `--workers`/`--idle-sleep` validation, remote_eval_worker.py:296).
**Warning signs:** asyncpg `value too long for type character varying(16)`.

### Pitfall 6: Existence-probe OFFSET off-by-one
**What goes wrong:** Threshold semantics are "backlog ≥ 300 games"; `OFFSET 300` would require 301 to trigger.
**Why it happens:** SEED-051 D-5 literally writes `OFFSET 299` for threshold 300 (the 300th row is at offset 299, 0-indexed).
**How to avoid:** `OFFSET = threshold - 1`. Encode as `ENTRY_LEASE_BACKLOG_THRESHOLD - 1` so the constant stays the human-readable "300."
**Warning signs:** Off-by-one in a backlog-gate test (exactly-300-pending should hand out a batch).

## Code Examples

### Worker depth-15 entry-ply eval (mirror `_eval_positions`, but `evaluate` not `evaluate_nodes_with_pv`)
```python
# Source: app/scripts/remote_eval_worker.py:75-99 (existing full-ply helper) adapted for entry-ply.
# Entry-ply returns only (eval_cp, eval_mate) — no best_move/pv (depth-15, D-2 / engine.py:451).
async def _eval_entry_positions(
    pool: EnginePool, positions: list[dict[str, object]]
) -> list[dict[str, object]]:
    boards = [chess.Board(str(p["fen"])) for p in positions]
    results = await asyncio.gather(*(pool.evaluate(b) for b in boards))  # depth-15
    return [
        {"game_id": p["game_id"], "ply": p["ply"], "eval_cp": r[0], "eval_mate": r[1]}
        for p, r in zip(positions, results)
    ]
```

### Worker ladder in `_run_cycle` (D-06)
```python
# Source: app/scripts/remote_eval_worker.py:141-193, restructured per D-06.
# explicit → if 204, entry-lease → if empty, idle.
lease_resp = await client.post("/api/eval/remote/lease", params={"scope": "explicit"})
if lease_resp.status_code == 204:
    entry_resp = await client.post("/api/eval/remote/entry-lease")  # gated by D-5 probe
    if entry_resp.status_code == 204:
        lease_resp = await client.post("/api/eval/remote/lease", params={"scope": "idle"})
        # ... handle tier-3 as today ...
    else:
        # ... eval entry positions (depth-15), POST /entry-submit ...
```
(The `X-Worker-Id` header is set once on the `httpx.AsyncClient` alongside `X-Operator-Token`, remote_eval_worker.py:220-224 — no per-call change.)

### Migration shape (mirror the project's manual-revision style)
```python
# Source: alembic/versions/20260614_150000_phase_119_eval_drain_coverage.py (manual revision/down_revision,
# non-concurrent partial index, explicit upgrade/downgrade). down_revision = current head (20260615 202440 7d5a4aa09a47).
def upgrade() -> None:
    op.add_column("games", sa.Column("entry_eval_lease_expiry", sa.DateTime(timezone=True), nullable=True))
    op.add_column("games", sa.Column("entry_eval_leased_by", sa.String(16), nullable=True))
    # Index strategy (Discretion): ix_games_evals_pending (on id, WHERE evals_completed_at IS NULL)
    # already backs both the LIFO claim ORDER BY id DESC and the D-5 OFFSET probe. The new lease
    # predicate (entry_eval_lease_expiry IS NULL OR < now()) is evaluated on the already-narrow
    # candidate set the partial index returns — no new index is strictly required for v1. The planner
    # MAY add one only if a measured plan regression appears (deferred-tuning territory).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Entry-ply drained by server pool alone (`run_eval_drain`, plain `SELECT`) | Server + remote workers partition the same import via a `games` lease | This phase (SEED-051) | First-import latency drops ~ worker fan-out factor |
| Remote worker bundled `/lease` (tier-1>2>3 in one call) | Worker orchestrates a 3-rung ladder across `/lease?scope=` + `/entry-lease` | This phase (D-05/D-06) | Entry-ply slots between tier-1 and tier-3 |
| `leased_by` always `"remote-worker"` | Distinctive per-process worker IDs via `X-Worker-Id` | This phase (D-10) | Per-worker observability in `leased_by`/`entry_eval_leased_by` |

**Deprecated/outdated:** none introduced. The existing `/lease` (scope-absent) and the constant `_WORKER_ID_REMOTE` remain as backward-compat fallbacks, NOT removed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Entry-ply submit must use `_apply_eval_results` (no shift), not `_apply_full_eval_results` (+1 shift) | Pattern 4 / Pitfall 1 | If wrong, entry evals land one row off — but this is grounded in reading both helpers; risk LOW |
| A2 | The existing `ix_games_evals_pending` (on `id`) is sufficient for v1's claim + probe; no new index required | Migration | If the lease predicate forces a heap re-check that regresses the plan, a new partial index may be needed; deferred-tuning per Discretion. Risk LOW (candidate set is already tiny at steady state) |
| A3 | A short TTL (~15-30s) is the right order of magnitude for D-04 | Pitfall 3 | Planner sets the exact value; SEED-051 says "well under 120s, seconds of work." Risk LOW |

**Note:** These are engineering-judgment assumptions grounded in reading the code, not unverified package/compliance claims. The locked decisions (D-01…D-10) are authoritative and carry no assumptions.

## Open Questions (RESOLVED)

1. **RESOLVED: Does `_entry-submit` need to handle the lichess-%eval skip the same way the server drain does?**
   - What we know: `_collect_target_specs` already skips plies where lichess `%eval` populated `eval_cp`/`eval_mate` (T-78-17, eval_drain.py:774,793). So a lichess game contributes fewer (or zero) entry targets; `/entry-lease` would return fewer positions for it.
   - What's unclear: whether big *first* imports that include lichess-analyzed games meaningfully reduce the entry-ply backlog the gate measures (the gate counts games, not positions, per D-5).
   - Recommendation: No special handling needed — the existing skip is inside the shared derivation. The game-count gate intentionally over-counts (D-5 accepts games as a cheap proxy). Lease returns whatever targets exist; a game with zero entry targets is still marked complete by `_mark_evals_completed` (matching `run_eval_drain`'s "mark all picked games regardless" semantics, eval_drain.py:1258).

2. **RESOLVED: Should `/entry-submit` clear `entry_eval_lease_expiry` explicitly, or rely solely on the completion stamp?**
   - What we know: The queue predicate is `evals_completed_at IS NULL`, so the completion stamp removes the game from the candidate set permanently (SEED-051 D-3 relies on this).
   - Recommendation: Rely on the completion stamp for correctness; optionally NULL the lease for tidiness/observability. Either is correct; the planner picks. (Clearing it makes `games WHERE entry_eval_lease_expiry > now()` a clean "currently in flight" view.)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Stockfish binary | worker depth-15 eval | ✓ (already used by Phase 120 worker + server drain) | pinned via `EXPECTED_SF_VERSION` | — |
| PostgreSQL 18 (dev Docker) | migration + claim tests | ✓ (per CLAUDE.md dev DB) | 18 | — |
| `EVAL_OPERATOR_TOKEN` set | endpoint auth in tests | ✓ (monkeypatched in tests) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` → this section applies.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (per-run DB clone from migrated template) |
| Config file | `pyproject.toml` (addopts) + `tests/conftest.py` (per-run DB isolation) |
| Quick run command | `uv run pytest tests/test_eval_worker_endpoints.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map
No formal REQ-IDs (seed-driven). Behavior → test mapping:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `/entry-lease` returns `{game_id, ply, fen}[]` for pending games | integration | `pytest tests/test_eval_worker_endpoints.py -k entry_lease -x` | ❌ Wave 0 |
| `/entry-lease` returns 204 when backlog < threshold (probe gate) | integration | `pytest tests/test_eval_worker_endpoints.py -k entry_lease_gate -x` | ❌ Wave 0 |
| `/entry-submit` writes entry evals at the correct ply (NO +1 shift) | integration | `pytest tests/test_eval_worker_endpoints.py -k entry_submit_no_shift -x` | ❌ Wave 0 |
| `/entry-submit` stamps `evals_completed_at` + classifies flaws | integration | `pytest tests/test_eval_worker_endpoints.py -k entry_submit_stamps -x` | ❌ Wave 0 |
| `/entry-submit` idempotent (double submit safe) | integration | `pytest tests/test_eval_worker_endpoints.py -k entry_submit_idempotent -x` | ❌ Wave 0 |
| `scope=explicit` returns only tier-1/2; `scope=idle` only tier-3; absent = bundled | integration | `pytest tests/test_eval_worker_endpoints.py -k scope -x` | ❌ Wave 0 |
| `X-Worker-Id` header populates `leased_by`/`entry_eval_leased_by`; absent → "remote-worker" | integration | `pytest tests/test_eval_worker_endpoints.py -k worker_id -x` | ❌ Wave 0 |
| Server lease (`_pick_pending_game_ids`) + remote `/entry-lease` partition (SKIP LOCKED, no overlap) | unit/integration | `pytest tests/test_eval_worker_endpoints.py -k lease_partition -x` | ❌ Wave 0 |
| Migration adds 2 nullable cols; existing migration tests pattern | migration | `pytest tests/ -k migration -x` | partial (precedent in `test_migration_*` files) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_eval_worker_endpoints.py -x`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** full suite green + `uv run ruff check .` + `uv run ty check app/ tests/` before `/gsd-verify-work` (CLAUDE.md Pre-PR checklist).

### Wave 0 Gaps
- [ ] New tests in `tests/test_eval_worker_endpoints.py` for `/entry-lease`, `/entry-submit`, `scope`, `X-Worker-Id`, and the backlog probe. The existing file's fixtures (`eval_worker_session_maker`, `eval_worker_test_user`, `_insert_game`, `_insert_game_positions`, `_patch_router_session`, `_make_client`) extend directly — no new conftest infra needed.
- [ ] A claim-partition test that inserts > batch_size pending games and asserts two concurrent claims return disjoint id sets (mirrors the `SKIP LOCKED` contract).
- [ ] Framework install: none needed (pytest already present).

## Security Domain

`security_enforcement` is not `false` in config → applies.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `X-Operator-Token` via `require_operator_token` (constant-time, fail-closed) — reused unchanged for the new endpoints |
| V3 Session Management | no | stateless operator-token model |
| V4 Access Control | yes | trusted-operator only; `X-Worker-Id` is **untrusted/advisory** (observability label, not authz) — never derive ownership from it. The submit already derives `owner_id` from the game row, not the payload (eval_remote.py:189) |
| V5 Input Validation | yes | Pydantic schemas with `Field(ge=0)` on ply, `max_length` on the evals list (mirror `MAX_SUBMIT_EVALS=1024`); validate `--worker-id` length < 10 |
| V6 Cryptography | no | no new crypto; token comparison stays `hmac.compare_digest` |

### Known Threat Patterns for FastAPI + asyncpg + raw-SQL CTE
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `worker_id`/`ttl`/`offset` in `sa.text` | Tampering | Bind ALL values as `:params` — never f-string (existing rule, `eval_queue_service.py`) |
| Malicious worker posts oversized `/entry-submit` body | DoS | `Field(max_length=...)` cap on the evals list (mirror `MAX_SUBMIT_EVALS`) |
| Spoofed `X-Worker-Id` to mislabel another worker's lease | Spoofing | Accept it only as an advisory label; never use for authz or ownership. Operator-token is the real gate |
| Worker submits evals for a game it doesn't own | Tampering | Server re-derives targets from `game_id` and owner from the game row; the worker's payload can only set `eval_cp`/`eval_mate` for plies the server chose |

## Sources

### Primary (HIGH confidence — read directly this session)
- `app/services/eval_drain.py` (full) — claim/derive/write helpers, `_pick_pending_game_ids` (unlocked SELECT today), `_collect_eval_targets_*`, `_apply_eval_results`, `_mark_evals_completed`, `run_eval_drain`.
- `app/routers/eval_remote.py` (full) — `require_operator_token`, `_build_lease_positions`, `_apply_submit`, `/lease`, `/submit`, `_WORKER_ID_REMOTE`.
- `app/services/eval_queue_service.py` (full) — `claim_eval_job`, `_claim_queued_job` (= "tier1/2"), `_claim_tier3_derived`, `LEASE_TTL_SECONDS=120`, `WORKER_ID_SERVER_POOL`.
- `app/services/engine.py` (full) — `EnginePool.evaluate` (depth-15, `_DEPTH=15`, `_TIMEOUT_S=2.0`), `evaluate_nodes_with_pv` (1M-node), `get_stockfish_version`.
- `scripts/remote_eval_worker.py` (full) — `_run_cycle`/`_run_loop`, `_eval_positions`, CLI `parse_args`, httpx client header wiring.
- `app/schemas/eval_remote.py` (full) — Lease/Submit Pydantic schemas, `MAX_SUBMIT_EVALS`.
- `app/models/game.py` (cols + `__table_args__`) — `evals_completed_at`, `ix_games_evals_pending` reference; `eval_jobs.leased_by = String(100)`.
- `alembic/versions/20260521_…_add_evals_completed_at_to_games.py` + `20260614_150000_phase_119_eval_drain_coverage.py` — `ix_games_evals_pending` definition + migration conventions (manual revision IDs, non-concurrent partial index).
- `tests/test_eval_worker_endpoints.py` (fixtures + lease/submit tests) — extension patterns.
- `app/main.py` — router mount (`/api`), drain task wiring; `app/core/config.py` — `EVAL_OPERATOR_TOKEN`/`EXPECTED_SF_VERSION`/`EVAL_AUTO_DRAIN_ENABLED`.
- `.planning/seeds/SEED-051-…`, `.planning/phases/123-…/123-CONTEXT.md` — locked decisions + D-3 claim SQL.

### Secondary
- SEED-048 referenced via SEED-051 cross-references (the SEED-048 file itself is not present at `.planning/seeds/SEED-048-…`; its protocol is fully embodied in the Phase-120/121 code read above, so the integration anchors are HIGH-confidence regardless).

### Tertiary
- none.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all surfaces read directly.
- Architecture: HIGH — every integration point located and quoted with line anchors.
- Pitfalls: HIGH — derived from the actual shift logic, lease shape, and backward-compat patterns in the code.

**Decision conflicts flagged:** One nuance (not a conflict): D-01 says "mirror the same SKIP LOCKED LIFO claim shape as the remote endpoint," but neither the server lease NOR the remote `/entry-lease` exists yet — and today's `_pick_pending_game_ids` is an **unlocked plain SELECT**. The planner should build ONE shared SKIP-LOCKED claim helper (SEED-051 D-3 shape) that both new call sites use, rather than "copy an existing endpoint." This is consistent with all locked decisions; flagged only so the planner doesn't go looking for a pre-existing entry-ply lease to copy.

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 (stable internal codebase; 30 days)
