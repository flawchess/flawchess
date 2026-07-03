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
- **Root cause:** a **remote worker's** Stockfish (`scripts/remote_eval_worker.py`, same
  `EnginePool` from `app.services.engine`) hit its **per-eval wall-clock timeout**
  (`_NODES_TIMEOUT_S = 5.0s`, `engine.py:100`) on the **slowest positions (openings, high
  branching factor)** on **weaker Hetzner hardware**. Timed-out evals return the `(None, …)`
  sentinel; the worker submits partial evals via `/atomic-submit`. The server counts the
  missing plies as holes (D-116-07 mark-and-continue), re-leases up to `MAX_EVAL_ATTEMPTS = 3`,
  then the **Path-C cap** (`eval_remote.py:1300`) stamps the games complete with residual
  holes → permanently "complete", never revisited.
- **The user's original hypothesis was CORRECT** — weaker remote workers hitting timeouts.
  (An earlier draft of this note wrongly blamed the in-process server pool; see the
  "Correction" section — that was a log-buffer artifact.)

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

1. **Remote worker engine** (`scripts/remote_eval_worker.py` → `app.services.engine`): the
   worker fans its leased game's plies across its local `EnginePool`, calling
   `evaluate_nodes_multipv2` at a 1M-node budget with a defensive wall-clock timeout
   `_NODES_TIMEOUT_S = 5.0s` (`engine.py:100`; = 4× *prod* p90 of 1.277s). On a weaker box
   the p90 is higher, so the slowest searches cross 5s. On timeout the pool returns the
   `(None, …)` sentinel and restarts the worker in place. The worker code itself calls this
   out (`remote_eval_worker.py:114`: *"with `_NODES_TIMEOUT_S=5s` the worst case is
   ~(100/--workers) × 5s if every position times out"*). `engine.py:106-118` documents the
   same class: *"a slower/busier host times out more searches, leaving eval_cp=NULL."*
2. **Which positions** — the **openings** (high branching factor → longest wall-clock at a
   fixed 1M-node budget) are the ones that cross 5s on slow hardware. The worker submits
   whatever resolved; timed-out opening plies are simply **absent** from its submitted map.
3. **Server apply** (`_apply_atomic_submit` → `_apply_full_eval_results`,
   `app/routers/eval_remote.py`): a missing ply → no eval in the map → counted as a hole
   (`failed_ply_count`, D-116-07 mark-and-continue). Under the atomic path there is **no
   opening dedup** (`dedup_map = {}`, `eval_remote.py:290-291`) — the worker is expected to
   eval every position — so a worker timeout is not backfilled from the cache.
4. **Cap / Path C** — the game is re-leased up to `MAX_EVAL_ATTEMPTS = 3`; a slow worker keeps
   timing out on the same opening positions, then Path C (`eval_remote.py:1300`) stamps
   `full_evals_completed_at` + `full_pv_completed_at` anyway (D-116-07 no-loop invariant) and
   fires ONE Sentry warning per game. Once stamped, the drain's
   `WHERE full_evals_completed_at IS NULL` never revisits it.

## Why only user 218

User 218 was the large batch being farmed out to remote workers during 08:36–10:02, so a
weak Hetzner worker leased and timed out on a share of *its* games. The other 61 users'
games today were smaller / processed at other times / by faster workers (or the in-process
pool), so they didn't accumulate the same worker-timeout holes. It is batch-exposure +
which-worker-drew-the-game, not anything intrinsic to 218's positions.

## Who processed the games — DEFINITIVE (Sentry)

Sentry issue **FLAWCHESS-8B** = `atomic-submit: stamping complete after MAX_EVAL_ATTEMPTS
with residual holes`:
- **45 events, first seen `2026-07-03T08:36:10.475Z`, last seen `10:04:30Z`** — user 218's
  exact processing window (the first event is 2 ms after the first holey game's completion).
- Culprit `/api/eval/remote/atomic-submit`; tag `source: remote_eval_worker`;
  **`user.geo: DE` (Germany)** → the submitting worker was a **Hetzner** box
  (95.217.146.94 / 88.198.19.214), NOT the Swiss local box (194.191.211.24, geo CH).
- Sample event context: `game_id 1666938, hole_count 11, attempts 3` (game 1666938 = user
  218; had 11 holes at Path-C time, self-healed to 2 later — see below).
- **No `full_eval_drain:` (server-pool) issue fired in 24h** → the in-process pool did NOT
  Path-C-stamp any of these; the holes are 100% the remote atomic path.

### CORRECTION — my earlier "server-pool did it" claim was wrong

An earlier pass concluded the remote workers were idle (all `atomic-lease` → `204`) and the
in-process server pool did everything. **That was a log-buffer artifact.** Docker's
json-file buffer for this chatty backend only retains ~1h; `docker compose logs --since 8h`
returned only ~11:59–13:00 (AFTER user 218 finished, backlog drained), whose `204`s I
mis-read as the state *during* 08:36–10:02. The real submit traffic from the window had
already rotated out. Sentry (durable) settles it: remote atomic workers processed the
holey games. **Lesson: don't infer worker activity from a rotated docker log window; use
Sentry / a durable store for anything older than ~1h on prod.**

### 45 events vs 36 currently-holey games

Some Path-C games self-healed after stamping (e.g. game 1666938: 11 holes → 2). Likely a
later idempotent re-submit for the same game landed more plies before the final stamp, or a
duplicate lease resolved some positions. So 45 Path-C stampings collapse to ~36 games still
showing mid-game holes now; a few dropped below the "≥2-from-end" mid-game threshold.

## Dead ends ruled out

- **Not a Phase-116 backfill artifact.** Both clean and holey games were stamped today; the
  full-eval stamp does not mirror `evals_completed_at`.
- **Not NULL-poisoned dedup cache.** `opening_position_eval` has **0 rows with NULL eval**,
  and the atomic path doesn't dedup anyway — the holes are worker-side engine timeouts.

## Remediation (see TODO + SEED)

- **Self-heal the 36 games:** re-NULL `full_evals_completed_at` AND `full_pv_completed_at`
  AND reset `full_eval_attempts = 0` so a drain tick reprocesses them. The **in-process
  server-pool** re-drain (scope=None) DOES use opening dedup, and the `opening_position_eval`
  cache is now **warm** for these openings, so it fills the holes via cheap **dedup
  transplants** — no engine, no timeouts. **Trap:** if you do not also reset
  `full_eval_attempts` (stored 2 → next attempt = 3 = MAX), any residual hole re-hits Path C
  immediately and re-stamps.
- **Durable fix (worker timeout, not pool load):** on `/atomic-submit` Path C, don't
  permanently stamp a game whose residual holes are worker **timeouts** — re-route it to the
  in-process server pool (which dedups the openings) or a stronger worker instead of
  accepting the weak worker's partial submit. Options: distinguish timeout-holes from
  deterministically-unevaluable holes; have the worker retry its own timed-out plies (or fall
  back to a lower node budget) before submitting; or exclude weak/slow workers from full-eval
  leases (keep them on tier-4 blob work) via a capability/latency signal.

Related: `.planning/notes/eval-completion-columns.md` (the 4 completion columns), D-116-07
(no-loop invariant), WR-05 (circuit breaker), SEED-044 (post-move eval shift), SEED-049
(terminal NULL).
