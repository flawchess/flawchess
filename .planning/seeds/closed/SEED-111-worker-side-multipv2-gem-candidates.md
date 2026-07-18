---
id: SEED-111
status: scheduled (Phase 177 added 2026-07-17 — move to closed/ when the phase ships)
planted: 2026-07-17
planted_during: Conversation on 2026-07-17 investigating why the best-move (gem/great) backfill runs at only ~550 games/h. Measured evidence — prod backend container at 798% CPU with all 8 local Stockfish pool engines pinned at ~92%, while the worker fleet's engines idle ~32% of every cycle (local 8-engine worker sampled at ~68% busy over 60s with zero CPU contention and work always leasable). Root cause — the gem-candidate MultiPV-2 runner-up searches (1M nodes each, ~8.6+ stored candidates/game, pre-gate superset larger) run on the SERVER's pool, synchronously inside every atomic-submit request (eval_apply.py _build_best_move_candidates, "Pitfall 1 remote lane" fallback). Maia inference is NOT the bottleneck — uvicorn (Maia + API + classify + PGN parse) uses ~0.5 of one core total.
trigger_when: Now viable — no external trigger needed. Sequencing consideration only — the lichess-eval lane (~21k games left, ~1.6 days at current rate) will be done before this ships; the payoff is the tier-4b population (~416k games), where the current architecture caps fleet scaling.
scope: medium (one GSD phase — worker script re-search pass + lease/submit schema v2 + apply-path switch + version gating + tests)
priority: high (throughput cap on a ~416k-game backfill; also removes the incentive to keep the prod box CPU-saturated 24/7)
references:
  - app/services/eval_apply.py            # _build_best_move_candidates — Pitfall-1 fallback to remove from the hot path
  - app/routers/eval_remote.py            # _apply_atomic_submit (synchronous apply), worker_schema_version "accepted but not gated on"
  - scripts/remote_eval_worker.py         # WORKER_SCHEMA_VERSION=1; _eval_atomic_game MultiPV-1 full pass + MultiPV-2 blob pass
  - app/services/engine.py                # evaluate_nodes_multipv2 — the 1M-node call the server currently absorbs per candidate
  - app/services/eval_queue_service.py    # atomic lease lanes (needs-engine + lichess residual + tier-4b)
---

# SEED-111: Move gem-candidate MultiPV-2 searches from server to workers (protocol v2)

## Goal

The server should do **zero Stockfish work when applying an atomic game submit**. Workers
compute the runner-up (MultiPV-2) data for gem candidates themselves and include it in the
submit payload; the server's apply path becomes pure Maia inference + classification + DB
writes. Frees the prod 8-engine pool for the drain (or for nothing), unclogs the synchronous
submit path that currently blocks fleet engines ~32% of each cycle, and makes backfill
throughput scale near-linearly with added workers instead of being capped by the server box.

Expected impact: fleet engines go from ~68% to ~95%+ busy (~1.4×+ with the current fleet),
and each future worker added actually adds its full capacity.

## Design sketch

1. **Targeted re-search, NOT a blanket MultiPV-2 full pass.** The full-ply pass stays
   MultiPV-1 (Phase 146 D-03 invariant, guarded by
   `test_eval_positions_uses_multipv1_no_second_best` — MultiPV-2 splits the node budget and
   would change eval_cp semantics/lichess parity). After the MultiPV-1 pass, the worker knows
   its own best move per ply; it runs a second targeted `evaluate_nodes_multipv2` only for
   plies where played == its best move (mirror of what the server's fallback does today).
   Extra worker cost ≈ 20-35% more search per game, spread across the fleet.
2. **Worker needs the played move per ply.** Either derive it from consecutive leased
   positions or (simpler) include `move_uci` per position in the lease response. Out-of-book
   filtering can stay server-side (worker computes second-best for ALL played==best plies; the
   server drops in-book ones — cheap, avoids shipping book logic to workers). Optionally the
   lease can carry the book-ply count to trim the superset.
3. **Trust boundary unchanged.** Same pattern as flaw-blob hints: the server never trusts the
   worker's *judgement*, only its *numbers*. Submitted second-best entries are keyed by ply and
   tamper-guarded like blob tokens (in-range ply check, 422 on garbage); the server still
   applies the played==best check, the out-of-book gate, and the inaccuracy gate itself from
   the submitted evals before running Maia.
4. **Version gating at LEASE, not just submit.** `worker_schema_version` already exists in the
   submit schema but is "accepted but not gated on" (eval_remote.py:1255). Bump
   `WORKER_SCHEMA_VERSION` to 2, add the version to the atomic-lease request, and have the
   server return 204 (no work) to v1 workers on the atomic lane — they idle harmlessly until
   upgraded. Entry-ply and flaw-blob lanes can stay v1-compatible if convenient.
5. **Keep the server fallback as a rare safety net, instrumented.** Path-B/C retries, holes,
   or a v2 worker that failed a targeted search can still hit the old fallback — but log/count
   it (Sentry tag or metric) so a regression that silently re-grows server Stockfish load is
   visible. Expected steady-state: near zero fallback calls.

## Amendment 2026-07-17: tier-4b lease shape (code-verified — planner must cover this)

The design sketch above is written for the fresh-analysis lanes (needs-engine + lichess
residual), where the worker's own MultiPV-1 pass is genuinely needed. It does NOT hold for
the tier-4b population (~416k already-analyzed games), which is the whole payoff. Three
gaps, verified against current code:

1. **Workers have no route to tier-4b at all.** `_claim_tier4_bestmove` is only reachable
   via `claim_eval_job(scope=None)` (eval_queue_service.py:864), whose sole consumer is the
   in-process server-pool drain. The worker ladder uses `scope=explicit`/`scope=idle`, and
   idle 204s after tier-3. Giving workers a tier-4b lane (extend the idle fall-through
   under v2 gating, or a dedicated lease) is an explicit deliverable, not an assumption.
2. **The "worker knows its own best move per ply" premise fails for tier-4b.** The
   SEED-076 incremental filter (`_lease_position_redundant`) strips every already-eval'd
   ply from an engine-game lease, so a fully-analyzed game leases as ~just the terminal
   donor — the worker runs no full pass and cannot find played==best plies itself. (Upside:
   this same filter means the worker also never redoes the flaw-blob MultiPV-2 walk — no
   leased plies, no hint-classify, no blobs.) The v2 lease for tier-4b must therefore carry
   **server-computed candidate plies** (played == stored best_move, out-of-book, from the
   game's existing best_move/pv columns + book filter). Worker compute is then exactly the
   N gem-candidate runner-up searches and nothing else.
3. **Tier-4b submits should skip reclassification.** `_apply_atomic_submit` runs the
   delete-then-insert `_classify_and_fill_oracle` with blob/tag snapshot-restore; for a
   tier-4b submit the evals are unchanged, so this is a no-op rewrite that only adds churn
   on the FLAWCHESS-8D StaleDataError surface. A tier-4b-only submit should write
   `game_best_moves` + stamp `best_moves_completed_at` and touch nothing else.

Related: the drain's `run_one_full_eval_tick` ignores tier (`_ = tier`, eval_drain.py:908),
so a drain-picked tier-4b game today re-evaluates EVERY ply at MultiPV-2 and reclassifies
from scratch — accidentally masked by fallback starvation. If the drain remains a tier-4b
consumer after this phase, it needs the same tier-aware minimal path (ties into open
question #1 below).

## Alternatives considered (and why not)

- **Async server-side fallback queue** (decouple fallback from the submit request): unblocks
  worker cycles but does NOT reduce server pool load — the 8-core box remains the throughput
  cap and fleet scaling stays sublinear. Strictly worse than shifting the work.
- **Blanket MultiPV-2 full pass on workers**: simplest protocol but breaks the Phase 146 D-03
  eval-parity invariant and costs ~2× nodes on every ply instead of ~25% on a subset.
- **Worker-side Maia inference** (discussed 2026-07-17, rejected): Maia is ~2% of a core at
  current rates (all of uvicorn incl. Maia + PGN parse + classify = ~0.5 core) so there is no
  throughput win, while the costs are real — maia_prob decides gem/great tiers and must be
  bit-consistent across the fleet (server enforces this via model SHA-256 check at load; a
  stale model/onnxruntime on one worker would silently skew stored probabilities), workers
  would need onnxruntime+numpy deps, and the lease would have to carry rating/platform/TC
  metadata for ELO pinning. If uvicorn ever saturates, escalate server-locally instead:
  ONNX batching, thread offload (run() releases the GIL), or a same-box sidecar.

## Open questions for the phase

- Does the drain's local (non-worker) lane keep computing second-best inline as today, or
  should the drain also be demoted now that the pool is free for it? (Today the drain
  completes ~nothing because fallbacks starve it.)
- Double-claim waste (~12%/h observed, plain-SELECT lottery, no locking) becomes relatively
  more expensive once throughput rises — is it time for the deferred TTL-lease escalation
  (D-4), or still acceptable?
- After the shift, uvicorn's single thread (Maia + classify + PGN parse, ~0.5 core today) is
  the next candidate bottleneck at much higher submit rates — measure before optimizing
  (Maia batch inference / thread offload only if it shows).

## Measured baseline (2026-07-17, for before/after comparison)

- ~550 games/h stamped; 629 worker submits/h (4 worker hosts: local 8-engine box 370/h,
  Hetzner workers 104/83/72/h).
- Server: 8 pool engines ~92% busy; uvicorn ~51% of one core.
- Local worker: ~9.7s/game cycle, engines ~68% busy over 60s (idle time = submit round-trip).
- 8.6 stored game_best_moves rows/game (pre-gate fallback superset larger).
