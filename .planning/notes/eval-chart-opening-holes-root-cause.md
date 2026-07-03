# Eval-chart opening holes — root-cause investigation (user 218)

**Date:** 2026-07-03
**Context:** `/gsd-explore` session. Prod user 218's imported games showed gaps in the
eval chart (missing per-ply evals mid-game). Goal: quantify how many game analyses are
incomplete and find out why. Investigation used the prod read-only DB + prod backend
access logs + code read of `eval_drain.py` / `engine.py` / `eval_remote.py`.

## TL;DR

- **Two distinct phenomena** hide behind "gaps in the eval chart":
  1. **Benign terminal gap** — *every* game's last ply has no eval (the position after the
     final move is terminal / unevaluable). Cosmetic; renders as a 1-point gap at the chart's
     right edge. Not a bug (SEED-049 legitimate NULL).
  2. **Real mid-game holes** — **36 games / 642 plies, all user 218**, stamped
     `full_evals_completed_at` yet missing evals in the middle of the game.
- **Root cause:** the in-process `server-pool` Stockfish drain's **per-eval wall-clock
  timeout** (`_NODES_TIMEOUT_S = 5.0s`, `engine.py:100`) fired on the **slowest positions
  (openings, high branching factor)** while user 218's **1,220-game single-user batch**
  saturated the pool of 6. Timed-out evals return the `(None, …)` sentinel + restart the
  worker → NULL holes (D-116-07 mark-and-continue). After `MAX_EVAL_ATTEMPTS = 3` retries
  hitting the same slow positions, the **Path-C cap** stamped the games complete with
  residual holes → they are permanently "complete" and never revisited.
- **The user's intuition was directionally right** ("timeouts + forced restart") but wrong
  about the *actor*: not the two weak remote Hetzner workers (they were idle the whole time,
  every lease returned `204`), but the backend's own Stockfish pool under batch load.

## Quantification (prod, 2026-07-03)

User 218: 1,222 games, all `full_evals_completed_at` set today, all engine-written
(`lichess_evals_at IS NULL`), 0 lichess-provenance.

| slice | count |
|---|---|
| games with a terminal last-ply gap | 1,220 (every game) — benign |
| games with penultimate-ply gap | 391 — mostly game-ending, low concern |
| **games with genuine mid-game holes** | **36** |
| **mid-game hole plies** | **642** |
| all 36 holey games belong to | **user 218** (0 holes in other 61 users' 1,466 games today) |

**Hole distribution is opening-weighted with a clean monotonic gradient** across the 36
games: decile 1 (opening) 65% missing → declining smoothly to ~4% by decile 9 → decile 11
(terminal) 100% (the benign gap). All 36 have `full_eval_attempts = 2` stored; because
Path C does not write `full_eval_attempts`, the real attempt count is **3** (`= MAX`).

## The mechanism, end to end

1. **Engine layer** (`app/services/engine.py`): the full-game drain calls
   `evaluate_nodes_multipv2` at a 1M-node budget with a defensive wall-clock timeout
   `_NODES_TIMEOUT_S = 5.0s` (line 100; = 4× prod p90 of 1.277s). On timeout/crash the
   worker returns the failure sentinel `(None, …)` and **restarts in place** (lines 41-42,
   247-248, 379-380). The file's own NOTE (lines 106-118) already documents this class:
   *"this wall-clock timeout is machine-speed-dependent — a slower/busier host times out more
   searches, leaving eval_cp=NULL."*
2. **Load** — user 218 was a 1,220-game single-user batch, 45% of all engine work prod did
   today, fanned across `STOCKFISH_POOL_SIZE=6`. That saturation stretched wall-clock per
   position; the **slowest searches (openings: high branching factor at fixed node budget)**
   intermittently crossed 5s → `(None, …)` → hole.
3. **Drain** (`app/services/eval_drain.py`): a timed-out position gets no eval into
   `engine_result_map`; `_resolve_full_eval` returns `(None, None, …)` → `_apply_full_eval_results`
   counts it as a hole (`failed_ply_count`, D-116-07 mark-and-continue, line ~627). The
   **WR-05 circuit breaker** (line ~2564) leaves a game pending only when *all* its engine
   calls fail; partial (opening-concentrated) failures **proceed**.
4. **Cap / Path C** — game re-leased 3× (`MAX_EVAL_ATTEMPTS = 3`, `eval_drain.py:111`),
   same slow positions time out each time, then Path C stamps `full_evals_completed_at` +
   `full_pv_completed_at` anyway (D-116-07 no-loop invariant) and fires ONE aggregated
   Sentry warning ("...stamping complete after MAX_EVAL_ATTEMPTS with residual holes").
   Once stamped, the drain's `WHERE full_evals_completed_at IS NULL` never revisits it.

## Why only user 218

Only user 218 had a batch large enough to saturate pool=6 and push opening evals past the
5s wall-clock timeout. The other 61 users' smaller / interleaved workloads today stayed
under the threshold → zero holes.

## Who processed the games (log evidence)

Prod backend access logs (`docker compose logs backend`) over the window showed **1,422
`atomic-lease` requests, ALL returning `204 No Content`** from all three remote worker IPs
(194.191.211.24 local Swiss box; 95.217.146.94 + 88.198.19.214 Hetzner). **Zero
`atomic-submit`** requests. So remote workers were idle; the in-process `server-pool` drain
did 100% of the work (no HTTP trace — it applies evals in-process). This disproves the
weak-remote-worker hypothesis as the *actor* (though the timeout+restart *mechanism* is
identical, just on the local pool).

## Dead ends ruled out

- **Not a Phase-116 backfill artifact.** Both clean and holey games were stamped today; the
  full-eval stamp does not mirror `evals_completed_at`.
- **Not NULL-poisoned dedup cache.** `opening_position_eval` currently has **0 rows with
  NULL eval**. A dedup *hit* always yields a valid eval, so the opening holes are cache-*miss*
  positions routed to the engine that then timed out — not bad cache donors.

## Remediation (see TODO + SEED)

- **Self-heal the 36 games:** re-NULL `full_evals_completed_at` AND `full_pv_completed_at`
  AND reset `full_eval_attempts = 0` so the next drain tick reprocesses them. The
  `opening_position_eval` cache is now **warm** for these openings, so the re-drain fills the
  opening holes via cheap **dedup transplants** (no engine, no timeouts). **Trap:** if you
  do not also reset `full_eval_attempts` (stored 2 → next attempt = 3 = MAX), any residual
  hole re-hits Path C immediately and re-stamps.
- **Durable fix:** distinguish timeout-holes from deterministically-unevaluable holes so
  Path-C timeout-holes remain re-drainable (e.g. once the opening cache warms), and/or
  throttle pool concurrency / lower per-user in-flight fan-out for single-user mega-batches.

Related: `.planning/notes/eval-completion-columns.md` (the 4 completion columns), D-116-07
(no-loop invariant), WR-05 (circuit breaker), SEED-044 (post-move eval shift), SEED-049
(terminal NULL).
