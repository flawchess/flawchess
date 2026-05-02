# Phase 78: Stockfish-Eval Cutover for Endgame Classification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 78-stockfish-eval-cutover-for-endgame-classification
**Areas discussed:** Engine wrapper concurrency, Backfill execution & batching, Import-path failure handling + index INCLUDE shape

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Engine wrapper concurrency | Single shared UCI vs pool, lock-per-eval, lifespan | ✓ |
| Stockfish install & version pin | apt vs official binary vs source build | (skipped — Claude's discretion) |
| Backfill execution & batching | Where it runs, batch size, dedup, parallelism | ✓ |
| Import-path failure handling + index INCLUDE shape | Engine error handling + ix_gp_user_endgame_game INCLUDE shape | ✓ |

**User's choice:** Engine wrapper concurrency, Backfill execution & batching, Import-path failure handling + index INCLUDE shape (3 of 4)

---

## Engine wrapper concurrency

### Concurrency model

| Option | Description | Selected |
|--------|-------------|----------|
| Single engine + asyncio.Lock | One long-lived UCI per worker, Lock serializes evaluate(). Simplest, deterministic, matches ENG-01. | ✓ |
| Engine pool (N=2 or 4) | Pool of UCI processes; round-robin or queue. Higher throughput but multiplies RAM on a swap-bound box. | |
| Single engine, no lock | Trust chess.engine internal queueing. Less code but undocumented behavior under contention. | |

**User's choice:** Single engine + asyncio.Lock
**Notes:** None — recommended option accepted.

### Engine lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI lifespan handler | Start in app/main.py lifespan, quit on shutdown. Engine ready before first request. | ✓ |
| Lazy on first evaluate() | Spawn on first call. Saves resources but first-eval latency includes ~200-500 ms spin-up. | |
| Module-level singleton at import | Side effect at import time; breaks test setup. | |

**User's choice:** FastAPI lifespan handler
**Notes:** None.

### Stockfish UCI options

| Option | Description | Selected |
|--------|-------------|----------|
| Hash=64 MB, Threads=1 | Modest RAM, fits with Postgres on 7.6 GB. Single thread = predictable CPU sharing. | ✓ |
| Hash=128 MB, Threads=2 | Faster per-eval but doubles RAM ceiling and steals CPU from uvicorn. | |
| Hash=16 MB, Threads=1 | Stockfish default. Slowest, risks IMP-02 sub-1s budget on long span sequences. | |

**User's choice:** Hash=64 MB, Threads=1
**Notes:** None.

---

## Backfill execution & batching

### Where it runs

| Option | Description | Selected |
|--------|-------------|----------|
| On the prod server, via `docker compose exec backend` | Same pattern as reclassify_positions.py. Network-local DB. | |
| Locally, via `bin/prod_db_tunnel.sh` | Run from laptop through tunnel. | |
| Both — benchmark locally, prod on server | Splits the runbook. | |
| **(operator's freeform answer)** | Run all three (dev / benchmark / prod) from local machine, before phase deploy. Add `--user-id` filter. | ✓ |

**User's choice:** All three rounds run from local machine. "I want to backfill the dev DB first to test the implementation. Then, I'll refill the prod DB from my local machine, before deploying the phase/milestone. So at the moment of deployment, the prod DB already has the backfilled evals ready for the hard cutover. And for game import, the engine needs to run locally for local import testing, and in prod. Also, the backfill script should take an optional user-id param to fill in evals just for one user."
**Notes:** This means Stockfish is also a local-host prereq (operator runs the engine locally during dev import testing and during prod backfill via tunnel). Locked in CONTEXT D-07 + D-08. Cutover ordering is dev → benchmark + VAL-01 → prod (pre-deploy) → merge + deploy → VAL-02 smoke.

### Hash dedup

| Option | Description | Selected |
|--------|-------------|----------|
| DB lookup on existing eval'd rows | Check if any row with same full_hash has eval; copy if so. Persists across resume. | |
| In-memory dict only | Fast lookup, rebuilt on resume. | |
| Both — in-memory + DB fallback | Best of both. | |
| **(operator's freeform answer)** | No dedup. "I think we don't need to dedupe, it makes no sense. We are talking about the endgame phase here. A cache hit is astronomically unlikely." | ✓ |

**User's choice:** No cross-row hash dedup.
**Notes:** Span-entry endgame positions are effectively unique across games. CONTEXT flags this as a SPEC drift on FILL-02 to resolve during planning (relax FILL-02 wording or ack drift in PLAN.md). Row-level idempotency (skip rows where eval is already populated) is preserved — that still satisfies FILL-04 lichess-no-overwrite.

### Batching

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential, commit every 100 rows | One engine, ~7s per batch, granular progress. | ✓ |
| Sequential, commit every 1000 rows | Larger transactions, less DB chatter, more loss on kill. | |
| Parallel — N=2 engines + asyncio.gather | Halves wall-clock, 2x RAM, conflicts with same-AsyncSession rule. | |

**User's choice:** Sequential, commit every 100 rows.
**Notes:** None.

---

## Import-path failure handling + index INCLUDE shape

### Import-path failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip row, log + Sentry, import succeeds | Leave eval NULL on engine error/timeout, Sentry context, continue. | ✓ |
| Hard timeout per eval (e.g. 2s), then skip | Same skip-and-log behavior plus explicit asyncio.wait_for. | (folded into chosen option as defensive measure) |
| Abort the game, mark import_job failed | Penalizes whole-game success on transient hiccups. | |

**User's choice:** Skip row, log + Sentry, import succeeds.
**Notes:** Claude added a defensive 2s asyncio.wait_for timeout (CONTEXT D-05) — depth 15 normally <100 ms but a wedged UCI is unbounded. On timeout, restart engine before next eval.

### Index INCLUDE shape (REFAC-04)

| Option | Description | Selected |
|--------|-------------|----------|
| INCLUDE(eval_cp, eval_mate) | Minimum needed; drops material_imbalance from INCLUDE (column itself stays per REFAC-05). | ✓ |
| INCLUDE(eval_cp, eval_mate, material_imbalance) | Conservative: keep material_imbalance in case other queries project it. | |
| Defer to planner | Enumerate every consumer of the index and produce a minimal INCLUDE. | |

**User's choice:** INCLUDE(eval_cp, eval_mate)
**Notes:** Planner should still grep for any other consumer of `ix_gp_user_endgame_game` and bump INCLUDE only if a real query depends on additional columns.

---

## Claude's Discretion

- **Stockfish install method (skipped from gray-areas multiselect)** — Claude chose pinned official Linux binary downloaded in the Dockerfile (D-06). apt's stockfish is too stale; building from source is overkill. Pinned tag (e.g. `sf_17`), checksum-verified, installed to `/usr/local/bin/stockfish`.
- **Defensive 2s `asyncio.wait_for` timeout in import path (D-05)** — operator chose "skip + log + Sentry" without specifying timeout; Claude added the defensive timeout because depth 15's wall-clock is bounded but a wedged UCI process is not.
- **Wrapper API exact signature (D-04)** — `async def evaluate(board) -> tuple[int | None, int | None]`. Tuple chosen for symmetry with `eval_cp` / `eval_mate` column pair; planner can switch to a dataclass if validation needs richer metadata.

## Deferred Ideas

- **Backfill progress reporting / ETA** — current plan logs at COMMIT boundaries; richer `tqdm`-style progress is nice-to-have.
- **Wrapper return-type richness** — tuple → dataclass migration if VAL-01 surfaces metadata needs.
- **Per-class threshold tuning, parity validation, rating-stratified offset analysis** — out of scope (SEED-002 / SEED-006).
- **Eval coverage for opening / middlegame positions** — out of scope (SEED-010 Library).
- **Bumping `ix_gp_user_endgame_game` INCLUDE for non-conv/recov consumers** — only if planner finds a real consumer.
