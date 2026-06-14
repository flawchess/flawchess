---
id: SEED-048
status: promoted
promoted_to: Phase 120 (2026-06-14)
planted: 2026-06-14
planted_during: /gsd-explore session on running Stockfish eval jobs off-box to help the server drain tier-3
trigger_when: Phase 119 (tier-3 drain rework — bounded retry, recency lottery, in_flight removal) has landed and settled, AND the eval-pipeline owner wants to add off-box eval capacity. Promote via /gsd-new-milestone or a focused /gsd-plan-phase.
scope: phase-sized (2 HTTP endpoints + operator auth + a headless worker CLI) — NOT a milestone
---

# SEED-048: Headless remote trusted-operator eval worker

## What This Is

A small **headless Python CLI worker** that runs on a trusted off-box machine (Adrian's home
dev box, the work MacBook Pro), leases eval jobs from prod over HTTPS, runs the **existing
`EnginePool`** locally, and posts evals back. It adds off-box CPU to the tier-3 eval drain
without touching the prod server's core budget. Two permanent workers already in mind = 2
extra machines helping the prod pool drain the ~558k-game backlog.

This is the **headless-trusted-operator rung** of [[SEED-012-client-side-stockfish-tactics]]'s
D-8 "pluggable worker" model — a middle tier between the in-process `server-pool` and the
(deferred) untrusted public-browser worker. SEED-012 D-8 jumped straight from server to
untrusted browser; this seed fills the gap with the cheap, safe, trusted version.

## The Three Trust Classes (why this rung is cheap)

The whole feature family splits by **who is allowed to write where**, decided by worker
identity/auth:

1. **Trusted off-box worker (THIS SEED)** — operator token → may write the **shared** tier-3
   store. Trusted because the operator controls the machine. Native Stockfish, no WASM. *Cheap,
   near-term.*
2. **A user's own browser** (Half A) — user session → writes only **that user's own** games.
   No trust layer needed (blast radius = own stats, per SEED-012 D-4). Deferred.
3. **Untrusted public browser** draining shared tier-3 — needs the WASM-calibration +
   redundancy/spot-check trust layer. The "even better," **deferred indefinitely**.

This seed is class 1 only. Classes 2–3 stay in SEED-012.

## Why Headless (not browser) for This Rung

For a machine the operator controls, the "no install / just a browser tab" constraint does not
apply, and a headless CLI is strictly better than a browser worker:

- **Reuses `app/services/engine.py` `EnginePool` as-is** — same native Stockfish binary, same
  `_NODES_BUDGET = 1_000_000`, NNUE, multiPV=1. No `stockfish.wasm`, no COOP/COEP, no
  SharedArrayBuffer, no iOS Safari fragility.
- **Calibration is a non-issue.** Cross-machine `eval_cp` is already accepted as
  non-reproducible and "not worth fixing" (see the project memory note on eval non-determinism
  dev vs prod). An ARM/macOS worker vs x86/Linux prod adds the *same already-tolerated* noise —
  as long as it pins the same SF **version** + 1M nodes + NNUE net. The worker reports its SF
  version; the server rejects a version mismatch.
- **Trusted → may write shared tier-3 directly**, which is the actual goal ("help the server").

## What Already Exists (the delta is small)

The queue was deliberately built pluggable (SEED-012 D-8):

- `app/services/eval_queue_service.py` — `claim_eval_job(worker_id: str = "server-pool")`
  already parameterized by worker identity; comment notes "Future browser workers will supply
  their own identity." Three tiers (TIER_EXPLICIT=1, TIER_AUTO_WINDOW=2, TIER_IDLE_BACKLOG=3),
  120s `LEASE_TTL_SECONDS`, SKIP LOCKED leasing for tier-1/2, derived pick for tier-3.
- `app/services/engine.py` — `EnginePool.evaluate_nodes_with_pv(board) -> (eval_cp, eval_mate,
  best_move_uci, pv_uci)` at the 1M-node budget. Reusable verbatim by the CLI worker.
- Storage convention (SEED-044) — post-move shift, terminal eval-donor, completion stamping —
  all already server-side.

**Missing pieces (the v1 work):**
1. HTTP endpoint: **lease a game** → returns the game's unanalyzed `(ply, FEN)` positions.
2. HTTP endpoint: **submit a game's evals** → batch of `(ply, eval_cp, eval_mate, best_move,
   pv)`; server applies SEED-044 convention + stamps `full_evals_completed_at`.
3. **Operator-token auth** on both endpoints (admin-gated; HTTPS to flawchess.com).
4. The **worker CLI** (~100 lines): loop { lease → eval all FENs via `EnginePool` → submit }.

## Locked Decisions (2026-06-14)

- **D-1 — Headless Python CLI worker, native Stockfish.** Browser path NOT in scope here
  (stays deferred in SEED-012).
- **D-2 — Worker is a dumb FEN→eval function.** Server hands it `(ply, FEN)` pairs; worker
  returns evals keyed by ply. The server owns ALL storage convention (SEED-044 post-move shift,
  terminal donor, completion stamp). The worker never touches storage rules → can't get
  ply-alignment wrong, and the subtle convention stays in one place.
- **D-3 — Per-game granularity, single batched submit.** Lease unit = one game; response =
  all of that game's unanalyzed positions; worker evals all locally (fanning the game's ~60
  positions across its cores, ~10s wall-clock), then posts **one** batch so the server applies
  the post-move shift + terminal donor + completion stamp atomically per game. NOT per-position
  HTTP (~120 round-trips/game where latency dwarfs the ~1s eval). NOT a partial submit (would
  leave a half-evaled game).
- **D-4 — Accept idempotent duplicate work for v1; add leasing for tier-3 later.** Tier-3 is a
  derived pick with no `eval_jobs` row, so prod-pool + the two remote workers can pick the same
  game. Eval writes are idempotent (same game → same `eval_cp`), so a collision is wasted CPU,
  not bad data. Combined with SEED-046's recency-weighted lottery (independent pickers rarely
  collide on a short window), v1 ships without strict tier-3 leasing. Materialize the lottery
  pick into a leased `eval_jobs` row (TTL) **later** if collision waste proves material — that
  would also restore the in-flight visibility Phase 119 is removing.
- **D-5 — SF version pinning + server-side mismatch rejection.** Worker reports its Stockfish
  version on submit; server rejects evals from a mismatched version to keep the population on
  one engine generation. (1M nodes + NNUE + multiPV=1 must match prod — D-6 of SEED-012.)
- **D-6 — Trusted-only write scope.** The operator token authorizes writing the shared tier-3
  store. No untrusted writer is introduced, so SEED-012's D-4 "no eval validation" non-goal
  still holds — nothing here needs a redundancy/agreement trust layer. That layer is only owed
  if/when untrusted public browsers (trust class 3) land.

## Sequencing

**Build AFTER Phase 119 lands and settles.** Phase 119 is actively reworking the exact tier-3
pick logic this worker leases against (SEED-046 recency lottery, `in_flight_count` removal,
SEED-045 bounded-retry hole-filling). Building on top of in-flight changes invites conflicts;
let 119 settle, then the worker reuses its improved pick.

## Open / Deferred (not v1)

- Strict tier-3 leasing (D-4 "later").
- Worker heartbeat / lease extension for slow workers (a 60-position game on a few-core box
  could approach the 120s TTL; with accept-duplicate-work this barely matters, but note it if a
  worker is genuinely slow).
- **macOS background scheduling (the MacBook worker).** `app/services/engine.py:171-172` —
  the SCHED_IDLE preexec is **Linux-only** (`os.sched_setscheduler` doesn't exist on macOS), so
  Stockfish workers on the MacBook spawn at **default priority** and compete with foreground
  apps as equals. A macOS equivalent (background QoS, e.g. wrapping the engine spawn in
  `taskpolicy -b`, or `setpriority`/nice) would restore the "only uses idle CPU" behaviour the
  Linux box gets for free. **Disposition: build it if it's cheap (a small spawn-flag tweak);
  defer if it turns out to need real platform plumbing.** Without it the MacBook still works as
  a worker — it just isn't polite about foreground responsiveness while draining. (Note: the
  prod-throughput estimates assume full-tilt cores; on a machine you're actively using, the
  point of idle-scheduling is responsiveness, not throughput.)
- Browser worker trust classes 2–3 — stay in [[SEED-012-client-side-stockfish-tactics]].

## Cross-References

- **[[SEED-012-client-side-stockfish-tactics]]** — parent. D-8 pluggable-worker model; this
  seed is the trusted-operator rung it didn't contemplate. Server-first v1 (D-1..D-8 there) is
  the in-process worker this one runs alongside.
- **SEED-045 / SEED-046** — Phase 119 tier-3 drain rework this worker sequences after and
  reuses.
- `app/services/eval_queue_service.py`, `app/services/engine.py` — the lease abstraction and
  engine pool the worker plugs into.
