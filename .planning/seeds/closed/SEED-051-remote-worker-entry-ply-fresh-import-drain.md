---
id: SEED-051
status: planted
planted: 2026-06-16
planted_during: /gsd-explore session on leveraging the remote worker pool to cut fresh-import (entry-ply) eval latency on big first imports
trigger_when: SEED-048 / Phase 120 (headless remote trusted-operator worker) has landed and is draining full-ply tier 1-3 in production, AND big-first-import latency (time until a new user sees flaws / phase-transition evals) becomes a priority. Promote via a focused /gsd-plan-phase.
scope: phase-sized (1 games column + 1 batched lease/submit endpoint pair reusing the SEED-048 protocol + a depth-15 mode in the existing worker CLI) — NOT a milestone
---

# SEED-051: Remote-worker fan-out for entry-ply (import-time) eval on big first imports

## What This Is

Extend the headless remote worker pool (SEED-048 / Phase 120) — which today only helps drain
**full-ply** tier 1-3 (1M nodes, gated on `full_evals_completed_at`) — to also help drain the
**entry-ply** eval that runs at game import (depth 15, the 2-3 phase-transition positions per
game: midgame entry + per-class endgame-span heads, gated on `games.evals_completed_at IS NULL`).

Today entry-ply is drained by the **prod server pool alone** (`run_eval_drain`, FIFO id DESC).
On a **big first import** (hundreds-to-low-thousands of games → ~1-3k cheap depth-15 evals) that
single pool is the latency bottleneck for a brand-new user waiting to see their flaws populate.
This seed lets the existing remote workers attack that same import's entry-ply positions in
parallel, so first-import latency drops by roughly the worker fan-out factor.

## Problem Shape (why this is narrow)

- **Goal = fresh-import latency, NOT backlog throughput.** Incremental syncs (≈20 games) are
  already fast and must NOT be slowed by lease/round-trip tax — the fan-out is only worth it on
  big imports. (Implementation may gate worker fan-out on a per-import game-count threshold;
  small imports stay server-pool-only.)
- **The pain is concentrated on big *first* imports.** That is the design target.
- Entry-ply work is **cheap and tiny**: depth-15 ≈90ms/position, only 2-3 positions/game. The
  expensive thing crossing the wire must be exactly the Stockfish call, not protocol overhead —
  hence batching across games is mandatory (one game at a time is mostly overhead).

## Locked Decisions (2026-06-16)

- **D-1 — Three-rung priority ladder; entry-ply is SECOND, below tier-1 (refined 2026-06-16).**
  The worker's between-games claim follows a strict priority order:
  1. **Tier-1 explicit single-game analysis** (full-ply, 1M nodes) — absolute top, unchanged.
  2. **Entry-ply fresh-import drain** (depth-15, batched) — this seed's new tier.
  3. **Tier-3 idle backlog** full-ply (deprecated tier-2 alongside) — bottom.

  Entry-ply sits *below* tier-1, not at the top, because tier-1 is the strongest attention
  signal (a user actively waiting on one specific game) and is tiny/bursty (one game per click),
  so keeping it first delays a big import by at most one game (~3-20s) per click — negligible —
  while the reverse (tier-1 starving for minutes behind a 1000-game import) is a bad,
  asymmetric downside. Two safety properties fall out: **entry-ply can't starve tier-1** (tier-1
  is claimed first), and **imports can't starve tier-1** (same reason). The only cost: entry-ply's
  worst-case pivot latency is "one in-flight full-ply game + any queued tier-1 game" instead of
  just one full-ply game — still bounded and small since tier-1 is single-game and rare.

  The check happens **between full-ply games** at the natural claim boundary. **No preemption**
  of an in-flight game (entry-ply batches are seconds of work — a between-games check is enough;
  preempting to save 1-2s isn't worth the partial-work complexity), and **no reserved/idle
  capacity**. (Both preemption and reserved capacity were considered and rejected given the
  bounded ~20s pivot ceiling.)

- **D-2 — Server ships FENs; worker stays a dumb Stockfish-over-HTTP node.** The batched lease
  returns a flat list of `{game_id, ply, fen}` spanning several fresh-import games. The server
  owns target derivation (the existing `_collect_eval_targets` / phase-transition selection from
  PGN + PlyData) and ALL storage convention (SEED-044 post-move shift, terminal donor, flaw
  classification, `evals_completed_at` stamp). The worker just runs depth-15 on each FEN and
  posts back `{game_id, ply, eval_cp, eval_mate}`. **Rejected:** shipping `game_id`s and having
  the worker self-derive entry-ply targets — that would duplicate the phase-classification logic
  onto the worker and force it to stay in sync with the server. The expensive part (Stockfish)
  is the only thing that needs to leave the box; the derive is cheap and stays server-side.
  Consistent with SEED-048 D-2 ("worker is a dumb FEN→eval function").

- **D-3 — No new table; ONE new column on `games` as a lightweight lease.** The queue already
  exists as the predicate `games.evals_completed_at IS NULL` (exactly how tier-3 uses
  `full_evals_completed_at IS NULL`). FENs are derived on demand and never stored, so there is
  **no per-position and no per-job table**. Add a single nullable column to `games`
  (e.g. `entry_eval_lease_expiry`, optionally `entry_eval_leased_by` for observability) and claim
  the same way `eval_jobs` does:
  ```sql
  UPDATE games SET entry_eval_lease_expiry = now() + INTERVAL '<TTL>'
  WHERE id IN (
    SELECT id FROM games
    WHERE evals_completed_at IS NULL
      AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
    ORDER BY id DESC            -- LIFO: newest import first
    LIMIT <N>
    FOR UPDATE SKIP LOCKED
  )
  RETURNING id;
  ```
  `SKIP LOCKED` gives each worker a *different* batch with no coordination; the TTL reclaims
  crashed-worker batches; `evals_completed_at = NOW()` on submit ends the lease permanently. The
  in-process server-side drain (`run_eval_drain`) becomes just one more claimer through the same
  lease, so server + remote workers **divide** the import instead of fighting over it.

- **D-4 — Do NOT reuse tier-3's "no lease at all" (lottery-only) model here.** Tier-3 tolerates
  zero leasing (SEED-048 D-4/D-7) because it lotteries over a *huge* backlog where independent
  pickers rarely collide and rare duplicate work is mopped up by idempotent writes. Fresh import
  is the opposite shape: a **tiny, sharply LIFO-ordered hot set** (just this import's newest
  unfinished games) with **N claimers that must partition the work**. A lottery over a small head
  just makes every worker grab the *same* newest games → ~N× redundant depth-15 evals on exactly
  the hot set, destroying the parallelism the workers were added for. The one lease column is the
  price of *non-redundant* fan-out. (A truly zero-schema pure-predicate version exists but was
  explicitly rejected for this reason.)

- **D-5 — Invite workers by *backlog depth at lease time*, not import size (added 2026-06-16).**
  Import size is unknowable mid-stream (games stream in async), so don't gate on it. Instead, the
  entry-ply lease endpoint checks the live backlog when a worker asks for work and only hands out
  a batch if the backlog is deep enough to be worth the lease/round-trip tax; otherwise it returns
  empty and the worker falls back to full-ply tier-3 (or sleeps). This one runtime signal subsumes
  every case a per-import threshold couldn't: streaming imports (threshold crosses as games land),
  **concurrent** imports (aggregate into one backlog), and the server pool falling behind for any
  reason (backlog grows → workers help → shrinks → back off; self-correcting). Mechanics:
  - **Gate on game count, not position count.** Positions need a PGN parse to derive — too
    expensive for a gate. Games are a cheap indexed `WHERE evals_completed_at IS NULL` proxy
    (~2-3 positions each). Threshold = **300 games** (≈600-900 positions) as the starting knob.
  - **Threshold is set by the D-1 pivot latency, NOT by amortization.** The threshold's real job
    is "is there more backlog than the server pool can clear within one worker-pivot window?"
    Below that line a worker can't arrive in time to help: D-1 means a busy worker takes up to
    ~20s to pivot off its current full-ply game, while the server pool is draining entry-ply
    locally the whole time. A ~100-game backlog (~250 positions) is cleared by the server in well
    under 20s, so inviting workers there just wastes a lease (worker pivots in to find the games
    already drained — idempotent but pure waste). So set threshold ≈ `server_entry_ply_throughput
    × pivot_latency`, i.e. roughly what the server clears in ~20s under import contention — a few
    hundred games, hence 300. Going *lower* (e.g. 100) only trips useless leases on marginal
    imports the server already clears fast; it does NOT help big imports, which blow past any
    threshold in this range anyway. **Measure the true value once the worker is live**; 300 is the
    starting guess.
  - **Probe, don't `COUNT`.** Only "is backlog ≥ threshold?" matters, so use a bounded existence
    probe — `SELECT 1 FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 1 OFFSET
    299` — constant-ish cost regardless of true depth, vs a full `COUNT(*)` over a large gated set
    on every lease request.
  - **Batch = 50 games (~125 positions); claim unit stays the game.** Claim 50 games via the D-3
    SKIP-LOCKED lease (≈125 positions at 2-3/game), derive and ship those FENs. 50 games is a few
    seconds of fanned-across-cores work per worker — comfortably above the round-trip amortization
    floor and granular enough that the tail doesn't lump. Batch size is tuned for amortization +
    tail granularity, independent of the threshold (which is tuned for pivot latency, above).
  - **The tail falls out for free.** A big import keeps the backlog well above threshold until its
    last stretch, then drops below → workers stop being invited → the final ≲300 games are mopped
    up by the server pool alone. Exactly right: the tail (where per-position worker tax stops
    paying off) is handled locally with zero special-casing. The `300`/`50` are tuning knobs; the
    mechanism (existence-probe gate + game-count + 50-game/~125-position batches) is the decision.

## What Already Exists (the delta is small)

- **SEED-048 / Phase 120** built the trusted-operator lease/submit protocol + headless worker
  CLI + operator-token auth + SF-version pinning. This seed adds a **second, higher-priority
  work type** to that same worker, not a new worker.
- `app/services/eval_drain.py` — `run_eval_drain` (entry-ply server drain),
  `_collect_eval_targets_*` / `_collect_target_specs` (the FEN derivation D-2 reuses verbatim).
- `app/services/engine.py` — `EnginePool.evaluate(board)` at depth 15 (the entry-ply engine
  mode the worker needs, alongside its existing `evaluate_nodes_with_pv` 1M-node mode).
- `games.evals_completed_at` — the existing entry-ply gate / queue predicate.

**Missing pieces (the v1 work):**
1. One nullable lease column on `games` + migration (D-3).
2. A **batched entry-ply lease** endpoint: claim N fresh games via the SKIP-LOCKED lease, derive
   their target plies, return `{game_id, ply, fen}[]`.
3. A **batched entry-ply submit** endpoint: accept `{game_id, ply, eval_cp, eval_mate}[]`, apply
   SEED-044 convention, classify flaws, stamp `evals_completed_at` per fully-covered game, clear
   the lease.
4. Worker CLI: add a **depth-15 mode** + the between-full-ply-games priority check (D-1).
5. The D-5 backlog-depth gate (existence probe) in the lease endpoint, so incremental syncs stay
   server-pool-only and workers are invited only when backlog ≥ threshold.

## Open / Deferred (not v1)

- **Lease TTL sizing** for entry-ply — batches are seconds of work, so a short TTL (well under
  the full-ply 120s) is fine; pick during planning.
- **Server-pool participation through the same lease** — make `run_eval_drain` claim via the new
  lease column so it can't double-evaluate games a remote worker holds. Decide whether this is
  v1 or a fast-follow; without it the server pool could redundantly re-evaluate leased games
  (idempotent, so correctness-safe, just wasted CPU — same tradeoff as SEED-048 D-4 but avoidable
  here since the lease already exists).
- **Backlog-gate threshold tuning** — the exact game-count (D-5 starting knob = 300) above which
  workers are invited; revisit against real server-pool throughput once the worker is live.
- **macOS background scheduling** caveat from SEED-048 applies unchanged (depth-15 spawns at
  default priority on the MacBook worker).

## Cross-References

- **[[SEED-048-headless-remote-eval-worker]]** — parent; built the worker + lease/submit
  protocol this seed extends with a new top-priority entry-ply tier. Sequence AFTER it lands and
  settles in prod.
- **[[SEED-012-client-side-stockfish-tactics]]** — grandparent; D-8 pluggable-worker model.
- **SEED-044** — storage convention (post-move shift, terminal donor, completion stamp) the
  server keeps owning per D-2.
- `app/services/eval_drain.py`, `app/services/engine.py`, `app/services/eval_queue_service.py` —
  the drain, engine pool, and lease abstractions the work plugs into.
