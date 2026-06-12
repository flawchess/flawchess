# Phase 116: All-Ply Engine Core - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

The eval drain analyzes every non-terminal ply of queued games at the Lichess-parity
search budget (1,000,000 nodes, NNUE, multiPV=1, Hash=32MB, Threads=1 — SEED-012 D-6),
storing results directly in `game_positions.eval_cp`/`eval_mate` (D-5), with a ply≤20
`full_hash` dedup (EVAL-03), a full-analysis completion marker distinct from
`evals_completed_at` (EVAL-05), and an explicitly measured + documented memory bound
for the worker pool against the backend container's 4g limit (QUEUE-07).

Requirements: EVAL-01, EVAL-02, EVAL-03, EVAL-05, QUEUE-07.

NOT in this phase: the tiered priority queue, lease/report contract, PV capture, and
flaw flow-through (Phase 117); demand UX, auto-enqueue, and coverage indicators
(Phase 118). The interim full-ply pick is LIFO id-DESC, replaced by 117's queue.

</domain>

<decisions>
## Implementation Decisions

### Dedup + eval provenance (EVAL-03)
- **D-116-01 — Parity-only dedup.** The ply≤20 dedup reuses ONLY 1M-parity evals.
  Legacy depth-15 server evals are never reused. Worst case is the already-accepted
  +26% cost ceiling (EVAL-01).
- **D-116-02 — Marker-gated source set.** Dedup consults only `game_positions` rows
  belonging to games whose full-analysis marker is set — parity by construction (the
  pipeline writes 1M evals and preserves lichess %evals). No provenance column, no
  fuzzy legacy backfill. Hit rate starts low and grows with coverage; acceptable
  because dedup is purely a cost optimization.
- **D-116-03 — Overwrite legacy depth-15 evals.** When the full pass analyzes a game,
  populated depth-15 entry-ply evals are overwritten with 1M evals so the game comes
  out uniformly at parity. One-time small shift in eval-derived endgame stats is
  accepted (consistent with the existing eval non-determinism stance).
- **D-116-04 — `Game.is_analyzed` is the %eval discriminator.** Within a game being
  analyzed: if `is_analyzed` (`white_blunders IS NOT NULL`, `app/models/game.py:160`)
  → populated evals are lichess %evals (parity) → preserve (T-78-17). Otherwise →
  populated evals are legacy depth-15 → overwrite (D-116-03). No heuristic needed.
- Note: dedup's eval-IS-NOT-NULL predicate naturally skips NULL holes in
  marker-complete source games (see D-116-07).

### Completion marker (EVAL-05)
- **D-116-05 — Timestamp column.** `full_evals_completed_at` on `games`, mirroring
  `evals_completed_at` exactly (nullable timestamp + partial index WHERE NULL for the
  pending pick). In-flight/queued state belongs to Phase 117's queue table, not here.
- **D-116-06 — Verified backfill at migration time.** Pre-mark games where every
  non-terminal ply already has `eval_cp`/`eval_mate` populated — provable by SQL, not
  trusting `is_analyzed` blindly. Seeds the dedup source set immediately from the
  lichess-analyzed population and makes coverage stats correct from day one.
- **D-116-07 — Mark complete with holes (D-09 carried forward).** Engine
  timeout/crash → row stays NULL, game still gets the marker, Sentry captures
  failures. No retry loop, no threshold gating.

### Interim drain structure (pre-117)
- **D-116-08 — Second coroutine.** `run_eval_drain` (entry-ply, depth-15,
  `evals_completed_at`) stays untouched so fresh imports keep getting endgame stats
  fast. A NEW full-ply drain coroutine owns the new marker and its own pick. Phase 117
  replaces only the new drain's pick logic with the queue.
- **D-116-09 — Live in prod with the 116 deploy.** The full drain starts eating the
  backlog on deploy, LIFO id-DESC interim pick (D-11 carried forward). Provides
  real-world memory/latency soak validating QUEUE-07 before the queue lands.
- **D-116-10 — Guest filter from day one.** The interim pick excludes guest users
  (`users.is_guest`) — QUEUE-08 is formally Phase 117, but one WHERE clause now avoids
  burning weeks of backlog compute on cleanup-candidate guest games.
- **D-116-11 — Gate between games.** Before picking each game, the full drain checks:
  active import job exists OR entry-ply work pending → sleep and re-check. Both
  predicates are instant via existing partial indexes. Worst-case intrusion on the
  quick lane = the one in-flight game (~10s pool-wide).

### Memory bound (QUEUE-07)
- **D-116-12 — Measure + document, no runtime machinery.** Measure real per-worker
  RSS at the 1M-node budget (spike-style), document the accounting (N workers ×
  footprint + active import + headroom vs the 4g container limit) in CLAUDE.md's prod
  section and a code comment next to the pool constants. The bound is a deploy-time
  decision, like `_BATCH_SIZE`/`_HASH_MB` today.
- **D-116-13 — Target pool size 8, contingent on checks; fallback 6.** Prod has run
  STOCKFISH_POOL_SIZE=6 stable for weeks (CLAUDE.md's "pool lowered" note is STALE —
  correct it in this phase's docs pass). Bump to 8 (all vCPUs) only if (a) the memory
  accounting fits 4g with headroom AND (b) a brief prod soak shows API latency
  unaffected (same check spike 002 did at 6). Otherwise stay at 6. All milestone
  throughput numbers (5.83 pos/s, 8.4k games/day) were measured at 6.

### Claude's Discretion
- Engine call plumbing: how `engine.py` exposes the node-budget search alongside the
  existing depth-15 call (new parameter, second function, per-pool config) — keep
  UCI options centralized in `engine.py` per ENG-03.
- The per-eval timeout for 1M-node calls (existing `_TIMEOUT_S = 2.0` is far too
  small at ~1s mean / heavier tail — pick a sane bound from spike latency data).
- Dedup index shape: a cross-user `full_hash` lookup index does not exist today (all
  existing `full_hash` indexes are user-scoped and partial `ply <= 28`); design the
  new index/partial predicate + the marker-gate join.
- Fan-out granularity per game (whole-game gather vs pool-size chunks) and the write
  transaction shape for ~60 row-updates per game.
- Terminal-position exclusion mechanics (game-over detection during the mainline walk).
- Verified-backfill execution shape (migration vs one-shot script) based on prod query
  cost.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of truth for this milestone
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` — §"Amendment (2026-06-12)" contains the locked decisions D-1..D-8 (budget, storage, dedup, marker, queue shape) and measured throughput. The phase implements D-5/D-6 and the all-ply collector.
- `.planning/REQUIREMENTS.md` — EVAL-01, EVAL-02, EVAL-03, EVAL-05, QUEUE-07 definitions and the traceability table.

### Spike findings (measured numbers, not estimates)
- `.planning/spikes/MANIFEST.md` — index of spikes 001–003, all VALIDATED.
- `.planning/spikes/001-sf-1m-node-latency-local/` — per-position latency at 1M nodes, Hash 32 vs 64 (no difference), depth-15 comparison (~10× premium).
- `.planning/spikes/002-sf-1m-node-latency-prod/` — prod CPX42: 0.98 s/position mean, 6 SCHED_IDLE workers scale linearly, API latency unaffected. NOTE: no memory measurements — QUEUE-07's measurement happens in this phase.
- `.planning/spikes/003-catchup-queue-sizing/` — backlog sizing (~558k unanalyzed games, ~66-day tier-3 drain at 6 workers).

### Code being extended
- `app/services/eval_drain.py` — the existing entry-ply drain (stays untouched per D-116-08); its session discipline (short transactions, gather OUTSIDE session scope) is the mandatory pattern for the new coroutine.
- `app/services/engine.py` — `EnginePool`, SCHED_IDLE spawn, UCI option centralization (ENG-03), `_score_to_cp_mate` sign convention.
- `app/models/game.py` — `evals_completed_at` + partial-index pattern to mirror; `is_analyzed` hybrid property (D-116-04 discriminator); stale-pool-size comment territory.
- `app/models/game_position.py` — existing user-scoped partial `full_hash` indexes (`ply <= 28`); the dedup index is NEW, not a reuse.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EnginePool` (`app/services/engine.py`): worker pool with per-worker restart, SCHED_IDLE scheduling — the 1M-node call rides the same pool; only the `Limit` and timeout change.
- Drain skeleton (`app/services/eval_drain.py:run_eval_drain`): pick → load PGNs → collect targets → gather outside session → short write tx → mark. The full-ply coroutine copies this shape with a different collector and marker.
- `_snapshot_boards` walk pattern: extend to snapshot every non-terminal ply instead of selected target plies.
- `_mark_evals_completed` executemany discipline (`Game.__table__` + bindparam) for the new marker.
- `ix_games_evals_pending`-style partial index pattern for the new marker's pending pick.

### Established Patterns
- AsyncSession never shared across coroutines; asyncio.gather only outside session scope (CLAUDE.md hard rule — structurally enforced in the drain).
- D-09 failure semantics: (None, None) → NULL row + game marked, Sentry, no retry loop.
- T-78-17: lichess %evals are never overwritten.
- UCI options live only in `engine.py` (ENG-03 grep gate).
- Sentry: no variables in messages; context/tags for game_id/ply/source.

### Integration Points
- New coroutine wired in `app/main.py` lifespan alongside `run_eval_drain` and the reaper.
- The yield gate (D-116-11) reads import-job activity + entry-ply pending — both have indexed predicates.
- Phase 117 will swap the interim LIFO pick for the queue and attach flaw classification (EVAL-06) + PV capture (EVAL-04) to this drain — keep the pick and the post-game hook point cleanly separated.

</code_context>

<specifics>
## Specific Ideas

- Lichess "Request a computer analysis" is the explicit UX/quality reference: same 1M-node fishnet budget, so users can verify FlawChess evals against lichess's own review (D-6 rationale).
- Prod reality check from the user: STOCKFISH_POOL_SIZE has been 6 in prod for several weeks, stable — CLAUDE.md's hotfix-era note saying it was lowered is stale and should be corrected when documenting the memory accounting.

</specifics>

<deferred>
## Deferred Ideas

- Pool-priority mechanism inside `EnginePool` (tier-aware worker scheduling) — Phase 117 territory if the gate-between-games policy proves too coarse.
- Window-capped automatic analysis (last ~200 games per user) — Phase 117/118 (QUEUE-04, D-3).
- `eval_source` provenance column — only if/when client workers land (SEED-012 D-8 phase 2).

</deferred>

---

*Phase: 116-All-Ply Engine Core*
*Context gathered: 2026-06-12*
