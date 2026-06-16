# Phase 117: Priority Queue + Flaw Integration — Research

**Researched:** 2026-06-13
**Domain:** PostgreSQL job-queue, async SQLAlchemy session discipline, python-chess PV capture, Alembic migration on 44M rows
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-117-01: `best_move` (PV[0], UCI) on EVERY evaluated `game_positions` row.
- D-117-02: Full PV only at the position AFTER each flawed move; ~12-ply cap; space-joined UCI.
- D-117-03: `best_move`/`pv` stored as UCI. Frontend converts UCI→SAN via chess.js.
- D-117-04: Within-tier ordering: classical > rapid > blitz > bullet, then most-recent-game-first. One `CASE` in `ORDER BY`.
- D-117-05: All three tier pick mechanisms + lease/report contract built in Phase 117. Tier-3 goes live on deploy. Tier-1/tier-2 user triggers deferred to Phase 118.
- D-117-06: New `games.lichess_evals_at` (nullable TIMESTAMPTZ) — set ONLY when lichess %evals ingested at import.
- D-117-07: Repoint D-116-04 and WR-02 off `white_blunders` onto `lichess_evals_at`.
- D-117-08: `classify_game_flaws` fills oracle count columns (white/black inaccuracies/mistakes/blunders) for engine-analyzed games.
- D-117-09: `is_analyzed` intentionally becomes "has flaw counts (lichess OR engine)" after D-117-08.
- D-117-10: One-time migration backfill: `lichess_evals_at` = `imported_at` where `white_blunders IS NOT NULL`.
- D-117-11: Cache invalidation per-user, debounced, on game completion.
- D-117-12: No mass re-enqueue of pre-117-analyzed games; demand-driven via tier-1/re-touch. Second completion marker `full_pv_completed_at` needed.

### Claude's Discretion
- Final column types: `best_move` varchar(5) UCI; `pv` Text UCI string.
- Jobs/lease table schema + lease/report mechanics (lease TTL, status states, requeue-on-expiry).
- Job/lease granularity: game-unit for tiers 2/3; tier-1 whole-pool fan-out.
- Round-robin fairness state implementation.
- `classify_game_flaws` idempotency mechanics.
- Internal tier-1 trigger shape.
- Exact debounce window and flaw-dependent cache set.

### Deferred Ideas (OUT OF SCOPE)
- User-facing "analyze more" button, auto-window-on-import, coverage indicators, in-flight UX — Phase 118.
- Guest account-promotion UX — Phase 118.
- Full multi-source `eval_source` provenance column — SEED-012 D-8 phase 2.
- Pool-priority (tier-aware EnginePool scheduling) — deferred per 116-CONTEXT.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-04 | `best_move` (PV[0] UCI) on every evaluated position; full PV at position after each flawed move (~12-ply cap); opening dedup transplants `best_move` alongside `eval_cp`. | §2 PV capture, §1 drain wiring, §3 dedup extension |
| EVAL-06 | Auto-classify `game_flaws` on full-eval completion; oracle count columns filled for engine games. | §6 classify hook, §5 WR-02 repoint |
| QUEUE-01 | Tiered priority queue: explicit > automatic window > idle backlog. | §3 queue design |
| QUEUE-02 | Round-robin per user within tier; TC-weighted + recency within user. | §3 ordering |
| QUEUE-03 | Tier-1 fans one game's positions across entire pool (~10s wall-clock). | §3 tier-1 fan-out, §8 internal trigger |
| QUEUE-05 | Idle workers drain backlog; cores never idle. | §3 tier-3 pick |
| QUEUE-06 | Lease/report pluggable-worker contract. | §3 lease design |
| QUEUE-08 | Guest exclusion from all tiers (already live via D-116-10, re-asserted in queue). | §3 queue pick WHERE |
</phase_requirements>

---

## Summary

Phase 117 extends the Phase 116 full-ply drain (`run_full_eval_drain` / `_full_drain_tick` in `app/services/eval_drain.py`) in three coordinated areas: (1) swap the interim LIFO pick for a three-tier priority queue backed by a PostgreSQL `eval_jobs` lease table, using `SELECT ... FOR UPDATE SKIP LOCKED`; (2) capture `best_move` (PV[0] UCI) for every evaluated position and the full PV (~12-ply cap) for the position after each flawed move, threading these through the existing `_FullPlyEvalTarget` → dedup → write pipeline; and (3) automatically invoke `classify_game_flaws` + fill oracle count columns when `full_evals_completed_at` is set, then debounce per-user flaw-dependent cache invalidation.

The drain architecture is already well-suited: `_full_drain_tick` cleanly separates pick, load, gather-outside-session, and write. Phase 117's changes touch the pick step (queue lease instead of LIFO), add `best_move` to the `_FullPlyEvalTarget` dataclass and dedup transplant, add a flaw PV path in the write step, and add a post-game classify + mark hook. The `run_full_eval_drain` loop is untouched; only `_full_drain_tick` changes internally.

The migration adds four nullable columns — two on `game_positions` (`best_move`, `pv`) and two on `games` (`lichess_evals_at`, `full_pv_completed_at`) — plus one partial index and one backfill UPDATE. Nullable additions on PostgreSQL are instant metadata operations; no table rewrite. The backfill `UPDATE games SET lichess_evals_at = imported_at WHERE white_blunders IS NOT NULL` must be batched on prod to avoid a long lock on the 44M-row table (though `games` is much smaller — ~558k rows).

**Primary recommendation:** Build the `eval_jobs` queue table with `SELECT FOR UPDATE SKIP LOCKED` as the claim primitive; thread `best_move` through `_FullPlyEvalTarget` and `_fetch_dedup_evals`; add a `_classify_and_fill_oracle` step to `_full_drain_tick`'s write session after the existing `_apply_full_eval_results`; and use a per-user in-process `dict[int, asyncio.Task]` debounce for cache invalidation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Priority queue claim/release | DB (PostgreSQL) | API/Backend | `FOR UPDATE SKIP LOCKED` is the canonical Postgres job-queue primitive; atomicity is required |
| Tier-3 idle drain pick | Backend (drain coroutine) | — | Already a background asyncio task wired in lifespan |
| Tier-1 fan-out (whole pool) | Backend (EnginePool.gather) | — | All workers analyze one game's positions via asyncio.gather outside session scope |
| PV capture | Backend (engine.py) | — | `protocol.analyse()` already returns PV in the same search; zero added cost |
| `classify_game_flaws` hook | Backend (eval_drain.py post-write) | — | Triggered in same write session after eval commits |
| Oracle count column writes | Backend (new `_fill_oracle_counts`) | — | Must run BEFORE `full_evals_completed_at` is set (atomic with flaw insert) |
| `lichess_evals_at` set | Backend (import_service.py normalization) | — | Written at import time, not analysis time |
| Cache invalidation | Backend (in-process debounce dict) | — | Per-user asyncio.Task pattern, no Redis needed at current scale |

---

## 1. The Full-Ply Drain: Precise Map

**File:** `app/services/eval_drain.py` [VERIFIED: codebase read]

### The D-116-08 second coroutine

`run_full_eval_drain()` (line 1030) is the thin loop. It calls `_full_drain_tick()` (line 891) which is the extractable unit. The loop sleeps `_DRAIN_IDLE_SLEEP_SECONDS = 5` when the tick returns `False`; loops immediately on `True`.

### The interim LIFO pick (lines 916–938) — the thing the queue replaces

```python
# Step 1 inside _full_drain_tick():
async with async_session_maker() as pick_session:
    pick_result = await pick_session.execute(
        select(Game.id, Game.pgn, Game.white_blunders.isnot(None).label("is_analyzed"), Game.user_id)
        .join(User, Game.user_id == User.id)
        .where(
            Game.full_evals_completed_at.is_(None),
            User.is_guest == False,
        )
        .order_by(Game.id.desc())  # <-- LIFO interim (D-116-09) — replaced by queue lease
        .limit(1)
    )
    row = pick_result.one_or_none()
```

**Phase 117 change:** Replace this entire block with a queue lease call. The queue determines which game to analyze next; the drain just claims a lease and gets back `(game_id, is_analyzed, user_id)`.

The `is_analyzed` label on line 926 currently reads `Game.white_blunders.isnot(None)`. After D-117-07 this must become `Game.lichess_evals_at.isnot(None)` — same SQL semantics post-backfill but semantically correct.

### `_collect_full_ply_targets` (lines 121–166)

Walks the PGN mainline once, yielding one `_FullPlyEvalTarget` per non-terminal ply. The `_FullPlyEvalTarget` dataclass (lines 100–118) currently holds: `game_id, ply, full_hash, board, eval_cp, eval_mate`.

**Phase 117 change:** Add `best_move: str | None = None` field to `_FullPlyEvalTarget`. No logic change needed here — it stays `None` until the write step fills it from engine results.

### `_fetch_dedup_evals` (lines 169–207) — WR-02 gate

The WR-02 gate on line 201:
```python
Game.white_blunders.is_(None),  # WR-02: engine-written sources only
```
**Phase 117 change (D-117-07):** Replace with:
```python
Game.lichess_evals_at.is_(None),  # WR-02 repointed: lichess_evals_at IS NULL means engine-written
```

The query currently returns `dict[int, tuple[int | None, int | None]]` (full_hash → (eval_cp, eval_mate)).

**Phase 117 change (EVAL-04):** Extend to also return `best_move` from the source row:
```python
select(GamePosition.full_hash, GamePosition.eval_cp, GamePosition.eval_mate, GamePosition.best_move)
```
Return type becomes `dict[int, tuple[int | None, int | None, str | None]]`.

All callers of `_fetch_dedup_evals` must be updated to unpack the new tuple. Currently there is only one call site (line 973 in `_full_drain_tick`).

### `_apply_full_eval_results` (lines 246–290) — the write path

Currently calls `session.execute(stmt.values(eval_cp=eval_cp, eval_mate=eval_mate))` per row. 

**Phase 117 change:** Thread `best_move` through `_resolve_full_eval` and write it in the same UPDATE:
```python
stmt.values(eval_cp=eval_cp, eval_mate=eval_mate, best_move=best_move_uci)
```

The flaw PV (`pv` column) is NOT written here — it requires knowing which plies are flaws, which is only determined by `classify_game_flaws` after all evals are written. The flaw PV write is a separate step after classification.

### `_mark_full_evals_completed` (lines 293–306)

Sets `full_evals_completed_at` unconditionally. No change needed here. The new `full_pv_completed_at` marker is set in the same write session after `_apply_full_eval_results` completes (only when all `best_move` values are non-NULL, or unconditionally — planner to decide).

### The post-game hook point (EVAL-06 / D-117-08)

The existing `_classify_and_insert_flaws` (lines 718–781) in `run_eval_drain` (the entry-ply drain) shows the pattern. The full-ply drain's `_full_drain_tick` write session (lines 1011–1026) currently calls only `_apply_full_eval_results` + `_mark_full_evals_completed`. 

**Phase 117 adds** after `_apply_full_eval_results` but before `_mark_full_evals_completed` (same atomicity requirement as in the entry-ply drain — evals committed before classification, marker set after):
1. `await _classify_and_fill_oracle(write_session, game_id)` — new function that runs `classify_game_flaws`, writes `game_flaws` rows (via `bulk_insert_game_flaws`), fills oracle counts, and writes flaw PVs.
2. `await _mark_full_evals_completed(write_session, game_id)` — unchanged.
3. `await _mark_full_pv_completed(write_session, game_id)` — new, sets `full_pv_completed_at`.

---

## 2. PV / `best_move` Capture from python-chess

**[VERIFIED: codebase read + python-chess inspect]**

`protocol.analyse(board, limit)` returns an `InfoDict`. The default `info=Info.ALL` (value 31) includes all info types. `InfoDict` is typed as:
```python
pv: List[chess.Move]   # the principal variation
score: PovScore        # the engine score
```

`info["pv"]` is `list[chess.Move]`. `info["pv"][0]` is the best move (what the engine would play). `move.uci()` gives the UCI string (e.g. `"e2e4"`, `"g1f3"`, `"e1g1"` for kingside castling). UCI is always 4 chars for normal moves, 5 chars for promotions (e.g. `"e7e8q"`).

**Current `evaluate_nodes` signature** (engine.py line 391–398) calls `self._analyse(board, Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S)`. The `_analyse` method (lines 349–385) calls `protocol.analyse(board, limit)` — since `info=Info.ALL` is the default and is not overridden, **the PV is already present in the returned InfoDict**. Only `_score_to_cp_mate` is applied to the result, discarding the PV.

**No extra engine cost:** The PV is a byproduct of the search (Stockfish reports it in `info` lines). Requesting it does not add nodes, depth, or time.

**Phase 117 change to `engine.py`:**

Add a new method `evaluate_nodes_with_pv` (or extend `_analyse` to return a richer result) that also extracts `pv`:

```python
async def evaluate_nodes_with_pv(
    self,
    board: chess.Board,
) -> tuple[int | None, int | None, str | None]:
    """Evaluate at 1M nodes, returning (eval_cp, eval_mate, best_move_uci).

    best_move_uci is info["pv"][0].uci() when PV is present, else None.
    Zero extra search cost — PV falls out of the same search (EVAL-04).
    """
    ...
```

The `_score_to_cp_mate` function (lines 240–257) is a pure extractor; add a parallel `_pv_to_best_move` extractor:

```python
def _pv_to_best_move(info: chess.engine.InfoDict) -> str | None:
    pv = info.get("pv")
    if not pv:
        return None
    return pv[0].uci()

def _pv_to_uci_string(info: chess.engine.InfoDict, cap: int = 12) -> str | None:
    pv = info.get("pv")
    if not pv:
        return None
    return " ".join(m.uci() for m in pv[:cap])
```

**Sign/perspective note:** `info["pv"]` is from the perspective of the side to move. `pv[0].uci()` is the engine's best move from the pre-push position. Since `best_move` is stored per `game_positions` row (which records the pre-push board state), no perspective conversion is needed. The `pv` string is also from the side-to-move's perspective (for SEED-039's cook classifiers which consume `(board, line, pov)` — the PV starting from the position after the flawed move uses the opponent's POV; the cook classifiers handle this internally).

**multiPV:** `EVAL-02` locks `multiPV=1` (SEED-012 D-6). No change needed. The single PV is sufficient for both `best_move` and the flaw refutation line.

**Full PV cap (D-117-02, ~12 plies):** SEED-039's tactic classifier works on the refutation line. Cook.py's tier-1 and tier-2 motifs need 1–2 plies; tier-3 needs 3+. The `~12-ply cap` covers all tiers with margin. At 1M nodes Stockfish typically returns 15–25 ply of PV; cap at `min(len(pv), 12)` in `_pv_to_uci_string`. The UCI string for 12 moves is at most `12 × 5 + 11 = 71` chars — fits easily in `Text` or even `varchar(100)`.

**Engine interface change:** The `evaluate_nodes` module-level function (line 227) stays unchanged for the drain's eval-only path. The new `evaluate_nodes_with_pv` is the Phase 117 addition used by the full-ply drain. ENG-03 invariant (UCI options only in engine.py) is unaffected since no new UCI options are needed.

---

## 3. Tiered Priority Queue + Lease/Report Contract

### Queue table schema (D-8 pluggable worker, QUEUE-06)

New table: `eval_jobs`

```sql
CREATE TABLE eval_jobs (
    id            BIGSERIAL PRIMARY KEY,
    tier          SMALLINT NOT NULL,        -- 1=explicit, 2=auto-window, 3=idle-backlog
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id       INTEGER NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | leased | completed | failed
    leased_by     VARCHAR(100),             -- worker identity (e.g. "server-pool", future "browser-abc")
    lease_expiry  TIMESTAMPTZ,             -- NULL when not leased
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    CONSTRAINT uq_eval_jobs_game UNIQUE (game_id)  -- one outstanding job per game
);
-- Index for tier-ordered pick (QUEUE-01 / QUEUE-02)
CREATE INDEX ix_eval_jobs_pick ON eval_jobs (tier, user_id, created_at)
    WHERE status = 'pending';
-- Index for lease-expiry requeue sweep
CREATE INDEX ix_eval_jobs_leased ON eval_jobs (lease_expiry)
    WHERE status = 'leased';
```

**Status lifecycle:** `pending` → `leased` (via claim) → `completed` (via report) or `failed` (all-fail circuit breaker). Expired leases: requeue to `pending` by a requeue sweep called at the top of each tick.

**Lease TTL:** Tier-1 game completes in ~10s (pool-wide fan-out). Tier-2/3 game per single worker ~60s × 0.98 s/pos ≈ 60s for a 60-ply game. Recommend `LEASE_TTL_SECONDS = 120` (2× the slowest case). A requeue sweep (in the same pick transaction or a dedicated short step) resets status = 'pending' for rows where `lease_expiry < now()`.

**QUEUE-08:** The pick query includes `eval_jobs.user_id IN (SELECT id FROM users WHERE NOT is_guest)`. Since `user_id` is a FK on `eval_jobs`, this is safe. Alternatively, exclude guest jobs at insertion time (simpler: never insert rows for guest users).

### Claim-with-lease idiom (`SELECT ... FOR UPDATE SKIP LOCKED`)

`SELECT FOR UPDATE SKIP LOCKED` is the canonical PostgreSQL advisory-lock-free job queue primitive. [ASSUMED] It is the same pattern used by pg-boss, Oban (Erlang), and Que (Ruby) — tested at massive scale.

```sql
-- Claim one job: tier-ordered, round-robin per user (single statement)
WITH candidate AS (
    SELECT id, game_id, user_id, tier
    FROM eval_jobs
    WHERE status = 'pending'
    ORDER BY tier ASC,
             -- Round-robin: pick the user with the oldest job in this tier
             -- (approximated by created_at of the oldest pending job per user)
             (SELECT MIN(created_at) FROM eval_jobs j2
              WHERE j2.user_id = eval_jobs.user_id AND j2.status = 'pending') ASC,
             -- Within a user: TC-weighted, then recency (D-117-04)
             CASE games.time_control_bucket
                 WHEN 'classical' THEN 0
                 WHEN 'rapid'     THEN 1
                 WHEN 'blitz'     THEN 2
                 WHEN 'bullet'    THEN 3
                 ELSE 4
             END ASC,
             games.played_at DESC
    JOIN games ON games.id = eval_jobs.game_id
    LIMIT 1
    FOR UPDATE OF eval_jobs SKIP LOCKED
)
UPDATE eval_jobs
SET status = 'leased',
    leased_by = :worker_id,
    lease_expiry = now() + interval '120 seconds'
WHERE id = (SELECT id FROM candidate)
RETURNING id, game_id, user_id;
```

**SQLAlchemy async implementation:**

```python
async def _claim_eval_job(
    session: AsyncSession,
    worker_id: str,
    lease_ttl_seconds: int,
) -> tuple[int, int, int] | None:
    """Claim one pending job. Returns (job_id, game_id, user_id) or None."""
    # Short transaction: claim + return, session caller commits.
    result = await session.execute(
        sa.text("""
            WITH candidate AS (
                SELECT ej.id, ej.game_id, ej.user_id
                FROM eval_jobs ej
                JOIN games g ON g.id = ej.game_id
                WHERE ej.status = 'pending'
                ORDER BY
                    ej.tier ASC,
                    (SELECT MIN(j2.created_at) FROM eval_jobs j2
                     WHERE j2.user_id = ej.user_id AND j2.status = 'pending') ASC,
                    CASE g.time_control_bucket
                        WHEN 'classical' THEN 0 WHEN 'rapid' THEN 1
                        WHEN 'blitz'     THEN 2 WHEN 'bullet' THEN 3
                        ELSE 4
                    END ASC,
                    g.played_at DESC NULLS LAST
                LIMIT 1
                FOR UPDATE OF ej SKIP LOCKED
            )
            UPDATE eval_jobs ej
            SET status = 'leased',
                leased_by = :worker_id,
                lease_expiry = now() + (:ttl || ' seconds')::interval
            FROM candidate
            WHERE ej.id = candidate.id
            RETURNING ej.id, ej.game_id, ej.user_id
        """),
        {"worker_id": worker_id, "ttl": lease_ttl_seconds},
    )
    row = result.one_or_none()
    return (row[0], row[1], row[2]) if row is not None else None
```

**AsyncSession + SKIP LOCKED discipline:** Each claim runs in its own short session (open → execute → commit → close). Never hold the session open during the engine gather. This mirrors the existing drain session discipline exactly. [VERIFIED: codebase read — eval_drain.py lines 909–913 show the pattern]

### Tier-1 fan-out granularity (QUEUE-03, D-4 addendum SEED-012)

Tier-1 fans ALL of one game's positions across the ENTIRE EnginePool via `asyncio.gather`. This is already the Phase 116 pattern in `_full_drain_tick` (lines 979–985) — the only change is that for tier-1 the gather includes every non-dedup'd ply at once (not just one game at a time from a pool of games). Since one game has ~60 plies and the pool has 6–8 workers, completion is ~60/6 × 0.98s ≈ ~10s wall-clock. [VERIFIED: spike 003 measurement]

Tiers 2/3: game-granularity per worker — one game per tick, one worker claims it. No change from current behavior.

### Tier-3 backlog: derived pick vs queue rows

**Recommendation:** Tier-3 does NOT need rows in `eval_jobs`. The tier-3 pick is a derived query directly on `games WHERE full_evals_completed_at IS NULL AND NOT is_guest`. This avoids pre-populating 558k rows at deploy time and keeps the queue table lean (only tiers 1 and 2 create explicit rows).

Implementation: `_claim_eval_job` first checks `eval_jobs` for tier-1 or tier-2 rows. If none, falls through to the tier-3 derived pick (the current LIFO pick, repointed with TC-weighted ordering). The combined pick function returns the same `(game_id, user_id, is_analyzed)` triple; the drain tick is unaware of which tier was served. The tier-3 path bypasses the lease table entirely — no row is written since there is nothing to "report back" (the drain marks `full_evals_completed_at` directly).

**Alternatively** (if QUEUE-06 pluggable-worker contract requires all workers use the same lease API): insert tier-3 rows lazily at pick time (insert if not exists, then claim). But this is more complex with no immediate benefit since browser workers (the future QUEUE-06 use case) will primarily handle tier-1/2 explicit requests.

**Planner decision needed:** Whether to keep tier-3 as a derived pick (simpler, no row population) or to insert synthetic rows. The research recommends the derived pick for Phase 117 since the QUEUE-06 pluggable-worker contract is satisfied as long as tiers 1 and 2 use the lease mechanism.

### Tier-1 enqueue service function (D-117-05)

```python
async def enqueue_tier1_game(game_id: int, user_id: int) -> None:
    """Insert a tier-1 eval_job for one game (upsert — idempotent)."""
    async with async_session_maker() as session:
        await session.execute(
            pg_insert(EvalJob).values(
                tier=1, user_id=user_id, game_id=game_id, status="pending"
            ).on_conflict_do_nothing(index_elements=["game_id"])
        )
        await session.commit()
```

The internal/admin trigger (D-117-05) is a thin admin endpoint or a test utility that calls this function for a specific `game_id`. Phase 118 wires it to user-facing actions.

---

## 4. New Columns + Alembic Migration

### Column additions

**`game_positions.best_move`:** `VARCHAR(5)` nullable. UCI moves are always 4 chars (normal) or 5 chars (promotion). `VARCHAR(5)` is a safe cap. At 44.4M rows: 44.4M × (5 bytes + overhead) ≈ +240 MB data as stated in D-117-01. [VERIFIED: codebase read — game_position.py confirms 44M row context]

**`game_positions.pv`:** `TEXT` nullable. Stored only at flaw-adjacent plies (a small fraction of rows). 12-move PV at most `12 × 5 + 11 = 71` chars, but Text avoids any length management. ~0 data overhead at population time (flaw rows are rare).

**`games.lichess_evals_at`:** `TIMESTAMPTZ` nullable. New provenance column (D-117-06). Set at import time in `app/services/normalization.py` (the lichess analysis ingestion path).

**`games.full_pv_completed_at`:** `TIMESTAMPTZ` nullable. Mirrors `full_evals_completed_at` for the PV/best_move completion dimension (D-117-12). Set after `best_move` is written for all plies in a game.

### Instant vs rewrite

Adding nullable columns to PostgreSQL 18 is a pure catalog update — zero table rewrite, zero locking beyond an `ACCESS EXCLUSIVE` lock held for milliseconds. [ASSUMED based on well-established PostgreSQL behavior for nullable column addition; confirmed to be the case in PG 11+ with no column default requiring table rewrite] On a 44M-row table this is safe to run in the migration without batching.

### Partial index for PV-pending pick (D-117-12)

```sql
CREATE INDEX ix_games_full_pv_pending ON games (id)
    WHERE full_pv_completed_at IS NULL;
```
Mirrors `ix_games_full_evals_pending` (added in Phase 116 migration). The drain can pick games where `best_move` is missing even if `full_evals_completed_at` is set.

### One-time backfill (D-117-10)

```sql
UPDATE games
SET lichess_evals_at = COALESCE(imported_at, NOW())
WHERE white_blunders IS NOT NULL
  AND lichess_evals_at IS NULL;
```

**On prod (`games` table, ~558k rows, not 44M):** A single-statement UPDATE on the `games` table holds a row-level lock on each updated row for the duration of the transaction. With `white_blunders IS NOT NULL` covering approximately the currently-analyzed lichess subset (likely a fraction of the ~558k games), this is well within safe bounds for a migration-time UPDATE. No batching needed on `games` (it's not 44M rows). [ASSUMED: the `games` table is of manageable size; the 44M rows are in `game_positions`]

The migration file follows the Phase 116 pattern (`20260612_120000_add_full_evals_completed_at.py`) — inline `op.execute()` for the backfill.

### Migration structure (one migration, multiple steps)

```python
def upgrade() -> None:
    # Step 1: game_positions nullable columns (instant — no table rewrite)
    op.add_column("game_positions", sa.Column("best_move", sa.String(5), nullable=True))
    op.add_column("game_positions", sa.Column("pv", sa.Text(), nullable=True))
    
    # Step 2: games nullable columns (instant)
    op.add_column("games", sa.Column("lichess_evals_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("games", sa.Column("full_pv_completed_at", sa.DateTime(timezone=True), nullable=True))
    
    # Step 3: partial index for PV-pending pick (D-117-12)
    op.create_index(
        "ix_games_full_pv_pending", "games", ["id"],
        postgresql_where="full_pv_completed_at IS NULL",
    )
    
    # Step 4: eval_jobs table + indexes (QUEUE-01/06)
    op.create_table("eval_jobs", ...)
    op.create_index("ix_eval_jobs_pick", "eval_jobs", ["tier", "user_id", "created_at"],
                    postgresql_where="status = 'pending'")
    op.create_index("ix_eval_jobs_leased", "eval_jobs", ["lease_expiry"],
                    postgresql_where="status = 'leased'")
    
    # Step 5: D-117-10 backfill lichess_evals_at (games table only, ~558k rows max)
    op.execute("""
        UPDATE games
        SET lichess_evals_at = COALESCE(imported_at, NOW())
        WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL
    """)
```

---

## 5. Repoint D-116-04 + WR-02 — Complete Edit List

**[VERIFIED: codebase grep, all occurrences listed]**

Every site that uses `white_blunders IS [NOT] NULL` as the lichess-%eval discriminator must be repointed after D-117-07. The analysis:

### Sites that MUST change (lichess-provenance discriminator)

1. **`eval_drain.py` line 201** — `_fetch_dedup_evals` WR-02 gate:
   ```python
   Game.white_blunders.is_(None),  # ← change to Game.lichess_evals_at.is_(None)
   ```
   **Why:** This is the WR-02 engine-source-only gate. Post-117, engine-analyzed games also have `white_blunders IS NOT NULL` (D-117-08), so the old gate would incorrectly exclude their evals from the dedup source.

2. **`eval_drain.py` line 926** — `_full_drain_tick` pick query:
   ```python
   Game.white_blunders.isnot(None).label("is_analyzed"),  # ← Game.lichess_evals_at.isnot(None)
   ```
   **Why:** The `is_analyzed` label here drives the D-116-04 preserve-vs-overwrite gate in `_apply_full_eval_results`. After D-117-07, "has lichess %evals" is now `lichess_evals_at IS NOT NULL`, not `white_blunders IS NOT NULL`.

   Also, after the queue replaces this pick, the `is_analyzed` value must still be fetched — it moves into the queue claim return value or a separate load step.

### Sites that KEEP using `white_blunders` (correct behavior post-117)

After D-117-08, `white_blunders IS NOT NULL` is true for both lichess-analyzed and engine-analyzed games. These sites use `is_analyzed` / `white_blunders` for the correct post-117 meaning ("has flaw counts from any source") and do NOT need to change:

3. **`app/models/game.py` lines 179/184** — `is_analyzed` hybrid property:
   ```python
   return self.white_blunders is not None
   ```
   **Keep as-is.** After D-117-08 fills `white_blunders` for engine games, `is_analyzed` correctly means "has flaw analysis (any source)" per D-117-09.

4. **`app/repositories/library_repository.py` line 931** — `Game.is_analyzed` in coverage query:
   ```python
   .where(Game.id.in_(select(base_subq.c.id)), Game.is_analyzed)
   ```
   **Keep as-is.** The coverage badge correctly counts all analyzed games.

5. **`app/repositories/library_repository.py` lines 618, 639** — `white_blunders`/`black_blunders` in flaw trend queries:
   **Keep as-is.** These read the actual blunder count values (not using them as a discriminator).

6. **`app/services/library_service.py` lines 301, 420, 428, 435** — `is_analyzed` gate in library card building:
   **Keep as-is.** These correctly gate on "has flaw data" for card rendering.

7. **`app/services/normalization.py` line 436** — writes `white_blunders` at lichess import time:
   **Keep as-is.** This is the legitimate write path for lichess games. A new write path for engine games goes via `_fill_oracle_counts` in `eval_drain.py`.

8. **`app/schemas/normalization.py` line 59** — `NormalizedGame.white_blunders`:
   **Keep as-is.** Schema for the import pipeline.

### New write site for engine games (D-117-08)

`_classify_and_fill_oracle` (new function in `eval_drain.py`) after `classify_game_flaws` returns, calls `count_game_severities` (already exists in `flaws_service.py`, lines 665–706) and updates the `games` table:

```python
async def _fill_oracle_counts(
    session: AsyncSession,
    game: Game,
    positions: list[GamePosition],
) -> None:
    """Fill oracle count columns from engine analysis (D-117-08).
    
    count_game_severities is user-scoped (game.user_color); we call it for
    both colors by temporarily swapping user_color. Alternatively, derive
    counts from the both-player classify_game_flaws output directly.
    """
    counts_white = count_game_severities(
        game_with_color(game, "white"), positions
    )
    counts_black = count_game_severities(
        game_with_color(game, "black"), positions
    )
    if isinstance(counts_white, GameNotAnalyzed) or isinstance(counts_black, GameNotAnalyzed):
        return  # < 90% eval coverage — skip
    await session.execute(
        update(Game.__table__)
        .where(Game.__table__.c.id == game.id)
        .values(
            white_inaccuracies=counts_white["inaccuracy"],
            white_mistakes=counts_white["mistake"],
            white_blunders=counts_white["blunder"],
            black_inaccuracies=counts_black["inaccuracy"],
            black_mistakes=counts_black["mistake"],
            black_blunders=counts_black["blunder"],
        )
    )
```

`count_game_severities` takes a `Game` and `positions`. It only reads `game.user_color`. To count for white, pass a `Game`-like object with `user_color = "white"` (or just pass a dataclass / simple object). Since `count_game_severities` reads only `user_color`, a thin wrapper or a copy-with-replacement pattern suffices.

**Simpler alternative:** `classify_game_flaws` already emits FlawRecords for BOTH players (since Phase 113). Count by `flaw["side"]` directly from the returned list:
```python
flaws = classify_game_flaws(game, positions)
if not isinstance(flaws, GameNotAnalyzed):
    white_B = sum(1 for f in flaws if f["side"]=="white" and f["severity"]=="blunder")
    # etc. — but inaccuracies are NOT in the FlawRecord list (D-03)
```
For inaccuracies, `count_game_severities` is still needed. Both calls together count all three tiers for both colors.

---

## 6. `classify_game_flaws` Hook — Operational Details

**[VERIFIED: codebase read — flaws_service.py, eval_drain.py]**

`classify_game_flaws` signature (flaws_service.py line 595):
```python
def classify_game_flaws(game: Game, positions: list[GamePosition]) -> GameFlawsResult:
```
Pure function (no I/O, no DB). Takes a `Game` ORM object and ordered `list[GamePosition]`. Returns `list[FlawRecord] | GameNotAnalyzed`.

**What it writes via the caller:** The caller (`_classify_and_insert_flaws` in eval_drain.py) calls `bulk_insert_game_flaws(session, rows)` which uses `ON CONFLICT DO NOTHING` on the PK `(user_id, game_id, ply)` — **idempotent by construction** (game_flaws_repository.py line 135).

**Oracle counts:** The `games` table UPDATE for oracle counts is a straightforward `UPDATE ... WHERE id = game_id`. It is safe to run multiple times (idempotent: same input → same output). The `white_blunders IS NOT NULL` → `is_analyzed = True` sentinel means once oracle counts are written the game appears in the analyzed denominator.

**Flaw PV write:** After `classify_game_flaws` returns the FlawRecord list, for each FlawRecord the flaw-adjacent position is at ply `flaw["ply"] + 1` (the position AFTER the flawed move — D-117-02). The PV for that ply comes from the engine result for `_FullPlyEvalTarget` at `ply + 1`. Write it to `game_positions.pv` for that ply in the same write session.

**The position that gets the PV column:** The flaw is at ply `N` (the move played was wrong). D-117-02 says "full PV at the position AFTER each flawed move" — that is ply `N` (the pre-move board FROM which the engine would have played better). Wait — re-reading D-117-02: "the position AFTER each flawed move" means the board after the bad move was played, which is the game_positions row at ply `N+1`. The engine's 1M-node search on that board gives the PV (engine's best continuation from the opponent's perspective at the resulting position). This is what SEED-039's cook detectors consume.

Actually, the terminology needs clarification. Let me re-read D-117-02 carefully: "at the position after each flawed move — the refutation line SEED-039's tactic-motif classifier consumes." In SEED-039: "detected in the **refutation line** (the best reply to the flawed move)." The flawed move is at ply N. The refutation is from the position AFTER the flawed move is played, i.e., the board at ply N (which is the board the opponent now faces). In `_full_drain_tick`, the target at ply N has a board snapshot BEFORE ply N's move is pushed. So the "position after the flawed move" corresponds to the board at ply N+1 — but wait, the existing targets only have boards BEFORE each move (pre-push snapshots). 

**Clarification:** In `_collect_full_ply_targets` (lines 121–166), for ply N, `board = board.copy()` is taken BEFORE `board.push(node.move)`. So target at ply N has the board BEFORE move N is played. The "position after the flawed move" (ply N) is the board BEFORE move N+1, which is the target at ply N+1. So the flaw PV is stored in `game_positions.pv` at the `ply = N+1` row (the opponent's position to refute from). This is consistent with the engine call for that target.

The flaw PV write: for each FlawRecord at ply `flaw["ply"]`, find the engine result for ply `flaw["ply"] + 1` in the `engine_result_map` (which holds the full PV from the with-PV engine call), and write it to `game_positions.pv` at ply `flaw["ply"] + 1`.

**Re-running classify:** If `full_evals_completed_at` is set but `full_pv_completed_at` is NULL (pre-117-analyzed game re-touched via tier-1), the drain re-runs the analysis. The `ON CONFLICT DO NOTHING` on `game_flaws` means duplicate flaw rows are silently skipped. Oracle count column writes are idempotent (same result). This is safe.

---

## 7. Cache Invalidation (D-117-11)

**[VERIFIED: codebase read — library_service.py, library_repository.py, flaws_service.py]**

### Flaw-dependent caches

The following endpoints read data affected by progressive flaw appearance:

| Cache surface | Endpoint | Flaw-dependent? | How affected |
|---|---|---|---|
| `GET /api/library/flaw-stats` | `get_flaw_stats` | Yes — `analyzed_n`, per-severity counts, you-vs-opponent bullets | New engine-analyzed games join the analyzed set |
| `GET /api/library/games` | `get_games_page` + `get_game_card` | Partially — card shows flaw rows, severity counts | New `game_flaws` rows appear |
| `GET /api/library/flaw-trend` | `get_flaw_trend` | Yes — oracle count columns drive the trend chart | New oracle counts |
| `GET /api/insights/openings` (structural) | LLM insights cache | No — insights gate on `evals_completed_at`, not flaw analysis | Not affected |
| `GET /api/insights/endgame` (structural) | LLM insights cache | No | Not affected |

**Current cache layer:** There is no in-process cache on these endpoints. The library service computes fresh from the DB on every request. The "260611-fast import-completion invalidation hooks" mentioned in CONTEXT.md refer to the `percentile_compute_registry.mark(uid)` + `compute_stage_b` pattern (eval_drain.py lines 866–870), not a library/flaw-stat cache.

**Recommendation for D-117-11:** Since there is no existing caching layer for flaw-stats, the "debounced per-user cache invalidation" from D-117-11 is a forward-looking design for when caching is added. For Phase 117:

1. **No new caching needed** — the library stats compute fresh on every request. Progressive flaw appearance simply means new requests see updated counts.
2. **`full_pv_completed_at` + `full_evals_completed_at`** serve as the staleness signals for Phase 118's coverage UX.
3. If a simple in-process mark is wanted: use a `set[int]` of recently-analyzed user IDs that a future cache layer can check. Pattern: add `_recently_analyzed_users: set[int]` module-level, add user_id to it after `_mark_full_evals_completed`, and expose a `was_recently_analyzed(user_id) -> bool` helper for future use.

The debounce window and the precise caching layer design are Claude's Discretion per CONTEXT.md. For Phase 117, the simplest compliant approach is: write a `_signal_flaw_completion(user_id)` hook in `eval_drain.py` that is called after the write session commits. Initially it's a no-op or a simple set insert. Phase 118 wires it to actual cache invalidation when caching lands.

---

## 8. Internal Tier-1 Trigger + QUEUE-03 Verification

**Internal trigger shape (D-117-05):**

```python
# app/routers/admin.py (already exists)
@router.post("/eval/enqueue-tier1/{game_id}", tags=["admin"])
async def admin_enqueue_tier1(
    game_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
) -> dict[str, str]:
    """Enqueue a tier-1 eval job for one game (admin/internal use only).
    
    Used to verify QUEUE-03's ~10s fan-out live on the prod pool.
    NOT the user-facing "analyze this game" endpoint (Phase 118).
    """
    from app.services.eval_queue_service import enqueue_tier1_game
    game = await session.get(Game, game_id)
    if game is None:
        raise HTTPException(404, "Game not found")
    await enqueue_tier1_game(game_id=game_id, user_id=game.user_id)
    return {"status": "enqueued", "game_id": str(game_id)}
```

This follows the existing admin router pattern (`app/routers/admin.py`). The `current_active_superuser` guard ensures non-admin users cannot trigger it.

**Measuring ~10s fan-out:** After enqueuing a tier-1 job for a game with ~60 plies at pool size 6:
- The drain's next tick claims the tier-1 job.
- The gather fans all 60 engine calls across 6 workers: ~60/6 × 0.98s ≈ 9.8s.
- Check: `SELECT full_evals_completed_at - now() FROM games WHERE id = $game_id` should show ≤ 15s from the enqueue time.

In tests: mock `evaluate_nodes_with_pv` to return `(0, None, "e2e4")` instantly. The test drives `_full_drain_tick()` directly (the existing testability pattern from `test_full_eval_drain.py`), inserts a tier-1 row, and asserts the game's `full_evals_completed_at` is set and the eval job is `completed`.

---

## Architecture Patterns

### System Architecture Diagram

```
[import pipeline]
      |
      v lichess: sets lichess_evals_at + white/black_blunders
[games table]
      |
      v full_evals_completed_at IS NULL, NOT guest
[eval_jobs table] ←── enqueue_tier1_game() (admin or Phase 118 UX)
      |
      v SELECT FOR UPDATE SKIP LOCKED (tier ordered, round-robin, TC-weighted)
[_full_drain_tick()]
      |
      |--→ load PGN + game_positions rows (short read session)
      |         |
      |         v opening region (ply ≤ 20)
      |     [_fetch_dedup_evals]
      |         |-- dedup hit → (eval_cp, eval_mate, best_move) from source game
      |         |-- cache miss → engine call
      |
      |--→ asyncio.gather(evaluate_nodes_with_pv, ...) [NO session open]
      |         |
      |         v returns (eval_cp, eval_mate, best_move_uci, pv_uci_string) per ply
      |
      v write session (open LATE)
  _apply_full_eval_results  → UPDATE game_positions SET eval_cp, eval_mate, best_move
  _classify_and_fill_oracle → classify_game_flaws + bulk_insert game_flaws
                              + count_game_severities → UPDATE games oracle columns
                              + UPDATE game_positions.pv at flaw-adjacent plies
  _mark_full_evals_completed → UPDATE games SET full_evals_completed_at
  _mark_full_pv_completed    → UPDATE games SET full_pv_completed_at
  report_job_complete(job_id) → UPDATE eval_jobs SET status='completed'
      |
      v commit + close session
  _signal_flaw_completion(user_id)  → debounce hook (Phase 118 wires caching)
```

### Key Patterns

**Session discipline (unchanged from Phase 116):**
- Step 0: gate check — short session, close.
- Step 1: queue claim — short session, commit, close.
- Step 2: load PGN + positions — short session, close.
- Step 3: `asyncio.gather(evaluate_nodes_with_pv, ...)` — NO session open.
- Step 4: write session — open LATE, all UPDATEs + inserts + markers, commit, close.

**`_classify_and_fill_oracle` atomicity:** Runs inside the Step 4 write session. This ensures flaw rows, oracle counts, flaw PVs, and completion markers commit together. No partial state (evals committed but flaws not yet written).

### Anti-Patterns to Avoid

- **`asyncio.gather` inside an AsyncSession scope:** Hard rule per CLAUDE.md. The drain enforces this structurally; do not weaken it when threading `best_move` through.
- **Per-ply Sentry events:** WR-05 — aggregate per game, not per ply. The 60+ engine calls per game would flood Sentry if each failure emitted an event.
- **Embedding variables in Sentry messages:** CLAUDE.md — use `set_context()`/`set_tag()` for `game_id`, `ply`, `user_id`.
- **Writing `lichess_evals_at` in eval_drain:** It is a provenance column set at import time (normalization.py), never by the drain.
- **Using `white_blunders IS NULL` as engine-source discriminator after D-117-07:** The WR-02 gate must use `lichess_evals_at IS NULL`. Using `white_blunders IS NULL` post-117 would exclude engine-analyzed games from dedup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job queue | Custom polling + lock table | `SELECT FOR UPDATE SKIP LOCKED` | Atomic claim; zero deadlock risk; standard PG pattern |
| PV extraction | Second engine call | `info["pv"]` from existing `analyse()` | Zero extra cost; PV is in the same InfoDict |
| Inaccuracy counting | Count from FlawRecord list | `count_game_severities()` (flaws_service.py:665) | FlawRecord list never contains inaccuracies (D-03) |
| Flaw insert dedup | Custom INSERT logic | `ON CONFLICT DO NOTHING` (game_flaws_repository.py:135) | Already idempotent |
| UCI-to-SAN conversion | Server-side | `chess.js` in frontend | D-117-03; board arrow display needs from/to squares which UCI gives directly |

---

## Common Pitfalls

### Pitfall 1: SKIP LOCKED Requires Its Own Transaction
**What goes wrong:** Calling `FOR UPDATE SKIP LOCKED` inside a long-lived session that has other reads open causes the lock to span the entire read + engine gather duration, blocking other workers.
**Why it happens:** SQLAlchemy AsyncSession accumulates reads in one transaction unless explicitly committed.
**How to avoid:** Claim is always a SHORT session: open → execute (with `SKIP LOCKED`) → commit → close. Never reuse the claim session for loading PGN or positions.
**Warning signs:** Engine gather takes 10s but the next worker claims nothing until the first completes.

### Pitfall 2: WR-02 Gate Must Move BEFORE Oracle Counts Are Written
**What goes wrong:** If the WR-02 gate is repointed to `lichess_evals_at IS NULL` but oracle counts are written AFTER the drain run, then a re-analyzed engine game would have `white_blunders IS NOT NULL` in the NEXT drain cycle but `lichess_evals_at IS NULL`, which would (correctly) still allow it into the dedup source. But if the gate is changed to `white_blunders IS NULL` by mistake in the transition period, a game with oracle counts freshly written but `lichess_evals_at IS NULL` would be wrongly excluded.
**How to avoid:** Change WR-02 gate first (to `lichess_evals_at IS NULL`), then enable oracle count writes.

### Pitfall 3: `count_game_severities` Returns Inaccuracies; `classify_game_flaws` Does Not
**What goes wrong:** Using `len([f for f in classify_game_flaws(...)` to count inaccuracies returns 0 because `classify_game_flaws` emits M+B only (see flaws_service.py D-03 comment). Inaccuracy counts in oracle columns require `count_game_severities`.
**How to avoid:** Use `count_game_severities` for the oracle count fill path. The FlawRecord list from `classify_game_flaws` gives M+B rows only.

### Pitfall 4: Flaw PV Ply Index Off-by-One
**What goes wrong:** The flaw at ply N should trigger PV storage at the `game_positions` row for ply N+1 (the position after the flawed move — the opponent's refutation board). Writing to ply N instead stores the PV for the flawed position itself (the engine's suggestion at the pre-flaw board — that's `best_move`, not `pv`).
**How to avoid:** For `FlawRecord.ply = N`, write `pv` at `game_positions.ply = N + 1`.
**Warning signs:** Cook detector sees the PV starting from a board where the user (not opponent) is to move.

### Pitfall 5: `lichess_evals_at` Backfill Must Run BEFORE Oracle Count Writes Land
**What goes wrong:** If oracle count writes for engine games go live before the backfill runs, `white_blunders IS NOT NULL` on those games would be from the engine (not lichess). Then the backfill `WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL` would incorrectly set `lichess_evals_at` for engine-analyzed games.
**How to avoid:** The migration backfill runs at deploy time before any new drain traffic. The drain's oracle count writes only start after the migration completes. This ordering is guaranteed by the Alembic migration running before the backend starts (deploy/entrypoint.sh).

### Pitfall 6: `eval_jobs` UNIQUE Constraint Prevents Duplicate Enqueues
**What goes wrong:** Calling `enqueue_tier1_game` twice for the same game inserts a duplicate.
**How to avoid:** `UNIQUE (game_id)` constraint with `ON CONFLICT DO NOTHING` at insert time. A game already in any status (pending, leased, completed) is not re-enqueued. Completed jobs should be deleted or the unique constraint should allow re-enqueue after completion — the planner must decide cleanup policy (delete rows on `completed_at`, or make the constraint partial: `WHERE status != 'completed'`).

### Pitfall 7: Round-Robin Approximation Bias
**What goes wrong:** The round-robin subquery `MIN(created_at) per user` approximates "oldest job per user" but can be slow on a large `eval_jobs` table if many users have pending jobs.
**How to avoid:** The `ix_eval_jobs_pick` partial index on `(tier, user_id, created_at) WHERE status = 'pending'` covers this subquery. At Phase 117 scale (at most a few hundred users with tier-2 jobs), the subquery is cheap. If it becomes a bottleneck, the planner can introduce a `user_last_served_at` column for true round-robin state.

---

## Runtime State Inventory

This section is omitted — Phase 117 is not a rename/refactor/migration that requires runtime state audit. It adds new columns and a new table; no renaming of existing keys, IDs, or strings.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/services/test_full_eval_drain.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-04 | `best_move` populated on all non-dedup'd plies | unit | `pytest tests/services/test_full_eval_drain.py -k best_move` | ❌ Wave 0 |
| EVAL-04 | `best_move` transplanted via dedup (opening region) | unit | `pytest tests/services/test_full_eval_drain.py -k dedup_best_move` | ❌ Wave 0 |
| EVAL-04 | `pv` written only at flaw-adjacent ply+1 | unit | `pytest tests/services/test_full_eval_drain.py -k flaw_pv` | ❌ Wave 0 |
| EVAL-06 | `classify_game_flaws` called after full eval complete | integration | `pytest tests/services/test_full_eval_drain.py -k classify_hook` | ❌ Wave 0 |
| EVAL-06 | Oracle count columns written for engine-analyzed game | integration | `pytest tests/services/test_full_eval_drain.py -k oracle_counts` | ❌ Wave 0 |
| QUEUE-01 | Tier-1 job picked before tier-3 | unit | `pytest tests/services/test_eval_queue.py -k tier_priority` | ❌ Wave 0 |
| QUEUE-02 | Round-robin: user B gets turn after user A | unit | `pytest tests/services/test_eval_queue.py -k round_robin` | ❌ Wave 0 |
| QUEUE-02 | TC ordering: classical picked before bullet within user | unit | `pytest tests/services/test_eval_queue.py -k tc_ordering` | ❌ Wave 0 |
| QUEUE-03 | Tier-1 fan-out: all plies gathered in parallel (AST test) | unit | `pytest tests/services/test_full_eval_drain.py -k gather_outside_session` | Partial (existing QUEUE-07 AST test) |
| QUEUE-05 | Tier-3 derived pick: game with no eval_jobs row | unit | `pytest tests/services/test_eval_queue.py -k tier3_derived` | ❌ Wave 0 |
| QUEUE-06 | Lease claimed and reported; expired lease requeued | unit | `pytest tests/services/test_eval_queue.py -k lease_expiry` | ❌ Wave 0 |
| QUEUE-08 | Guest games excluded from all tiers | unit | `pytest tests/services/test_eval_queue.py -k guest_exclusion` | ❌ Wave 0 |
| D-117-07 | WR-02 gate uses `lichess_evals_at IS NULL` (not `white_blunders`) | unit | `pytest tests/services/test_full_eval_drain.py -k wr02_repointed` | ❌ Wave 0 |
| Migration | `lichess_evals_at` backfill: only pre-existing analyzed games | integration | `pytest tests/test_migration_117.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_full_eval_drain.py tests/services/test_eval_queue.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_eval_queue.py` — covers QUEUE-01/02/05/06/08
- [ ] `tests/test_migration_117.py` — covers D-117-10 backfill + column additions
- [ ] Extend `tests/services/test_full_eval_drain.py` — covers EVAL-04 (`best_move`), EVAL-06 (classify hook), D-117-07 (WR-02 repoint)

---

## Security Domain

Validation (V5): queue claim uses parameterized queries (no SQL injection surface). The lease table `user_id` is a FK to `users` with CASCADE — no orphan rows. The `leased_by` column is server-assigned (`"server-pool"`) for Phase 117; no user-controlled input. No authentication/session/crypto concerns for the backend-only queue.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adding nullable columns to PG 18 is instant (no table rewrite) | §4 | Migration could take minutes on 44M rows — verify with EXPLAIN DDL if needed; PG docs confirm this for ≥ PG 11 |
| A2 | `SELECT FOR UPDATE SKIP LOCKED` is the canonical PG job queue primitive | §3 | Alternative approaches (advisory locks, LISTEN/NOTIFY) exist; risk is low since SKIP LOCKED is used in production at pg-boss/Oban scale |
| A3 | The `games` table has ~558k rows (not 44M) | §4 | If games count is higher, the migration backfill UPDATE needs batching; verify with `SELECT count(*) FROM games` |
| A4 | Round-robin approximation via `MIN(created_at)` per user is performant at Phase 117 scale | §3 | Subquery cost scales with concurrent user count; at <1k users with pending jobs it's fine |
| A5 | The flaw PV belongs at `game_positions.ply = flaw_ply + 1` (position after flawed move) | §6 | D-117-02 says "position after each flawed move" — confirmed by SEED-039's "refutation line from position after the blunder" |
| A6 | `info=Info.ALL` (the default) is what `protocol.analyse()` uses in the current drain | §2 | If the engine call somehow suppresses PV, `info["pv"]` would be absent — confirmed by engine.py source inspection: no `info=` override is passed |

**If this table is empty:** Not applicable — six assumptions identified; planner should treat A3 as a must-verify before writing migration.

---

## Open Questions

1. **`eval_jobs` UNIQUE constraint scope for completed jobs**
   - What we know: `UNIQUE (game_id)` prevents duplicate enqueues for the same game while a job is pending or leased.
   - What's unclear: Should completed jobs be deleted from `eval_jobs`, or should the UNIQUE constraint be partial (`WHERE status != 'completed'`) to allow re-enqueue after completion?
   - Recommendation: Partial unique constraint `WHERE status IN ('pending', 'leased')` + archive completed rows (or leave them for audit). Planner to decide based on audit needs.

2. **`_fill_oracle_counts`: count both colors via two `count_game_severities` calls or via one `classify_game_flaws` call**
   - What we know: `count_game_severities` handles inaccuracies (not in FlawRecord); `classify_game_flaws` returns M+B for both sides.
   - What's unclear: Cleaner to call `classify_game_flaws` once (already called for game_flaws rows) and derive M+B counts from the result, then call `count_game_severities` TWICE (white/black) for inaccuracies only.
   - Recommendation: Call `classify_game_flaws` once (already needed for game_flaws). Derive mistake/blunder counts from the list. Call `count_game_severities` twice for inaccuracies (but swap `user_color` — needs a Game copy or a minimal duck-typed object since `count_game_severities` only reads `user_color`). Alternatively, extend `count_game_severities` to accept a `color` parameter directly.

3. **Tier-3 derived pick vs queue rows**
   - What we know: 558k backlog games; queue rows are only for explicit tier-1/2 requests.
   - What's unclear: Whether the QUEUE-06 pluggable-worker contract requires all tiers to use the same lease table.
   - Recommendation: Tier-3 as derived pick (no queue rows). The contract only requires tiers 1/2 use the lease API; tier-3 is a fallback when the queue is empty.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 | Queue table, SKIP LOCKED | ✓ | 18.x (Docker) | — |
| python-chess 1.11.x | PV extraction | ✓ | Installed (from existing engine.py usage) | — |
| Stockfish | Engine calls | ✓ | Prod/dev path configured | — |
| Alembic | Migration | ✓ | Existing | — |
| pytest-asyncio | Queue tests | ✓ | Existing (see test_full_eval_drain.py) | — |

---

## Sources

### Primary (HIGH confidence)
- `app/services/eval_drain.py` — full source read; all function signatures, line numbers, and logic confirmed
- `app/services/engine.py` — `EnginePool._analyse`, `evaluate_nodes`, `_score_to_cp_mate` confirmed; `Info.ALL` default confirmed via python-chess inspect
- `app/models/game.py` — `is_analyzed` hybrid, oracle count columns (lines 134–139), `full_evals_completed_at` (line 158) confirmed
- `app/models/game_position.py` — `DEDUP_MAX_PLY`, column list, index definitions confirmed
- `app/services/flaws_service.py` — `classify_game_flaws`, `count_game_severities`, `FlawRecord.ply` semantics confirmed
- `app/repositories/game_flaws_repository.py` — `bulk_insert_game_flaws` ON CONFLICT DO NOTHING confirmed
- `app/main.py` — lifespan wiring of `run_full_eval_drain` (line 80) confirmed
- `alembic/versions/20260612_120000_add_full_evals_completed_at.py` — migration pattern confirmed
- `tests/services/test_full_eval_drain.py` — existing test structure and testability pattern confirmed
- python-chess `InfoDict` — `pv: List[chess.Move]` confirmed via `inspect.getsource`; `protocol.analyse` signature confirmed with `info=Info.ALL` default

### Secondary (MEDIUM confidence)
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` §"Amendment (2026-06-12)" — locked decisions D-1..D-8, throughput numbers
- `.planning/seeds/SEED-039-tactic-family-cause-of-error-flaw-tags.md` — PV consumption pattern, SEED-039 tier structure (1–3 ply depth requirements confirmed as ~12-ply cap is sufficient)
- `.planning/spikes/003-catchup-queue-sizing/` — tier-1 ~10s wall-clock, 558k backlog (cited in CONTEXT.md as VALIDATED)

### Tertiary (LOW confidence)
- PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` as canonical job queue primitive — [ASSUMED] based on established production usage at pg-boss, Oban, and Que scale; not verified against a specific PG 18 changelog

---

## Metadata

**Confidence breakdown:**
- Full-ply drain map: HIGH — direct source read, all line numbers verified
- PV capture mechanics: HIGH — python-chess InfoDict inspected live
- Queue schema/lease design: MEDIUM — pattern is well-established; exact SQL and edge cases are implementation detail for planner
- Migration plan: HIGH — mirrors Phase 116 migration pattern exactly
- `is_analyzed`/`white_blunders` repoint site list: HIGH — exhaustive grep confirmed all occurrences
- Cache invalidation: MEDIUM — no existing flaw-stat cache found; D-117-11 deferred to a hook/signal pattern

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable stack; no fast-moving dependencies)
