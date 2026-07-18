# Phase 177: Worker-side MultiPV-2 gem-candidate searches, protocol v2 - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning

<domain>
## Phase Boundary

The server does **zero Stockfish work when applying an atomic game submit**. Workers compute the gem-candidate runner-up (MultiPV-2) data themselves via a targeted re-search after their MultiPV-1 full pass (only plies where played == worker best; the full pass stays MultiPV-1, preserving the Phase 146 D-03 eval-parity invariant) and include it in the submit payload. The server's apply path becomes pure Maia inference + classification + DB writes. `WORKER_SCHEMA_VERSION` bumps to 2 with gating at the atomic LEASE (v1 workers get 204 no-work on that lane). Tier-4b (~416k already-analyzed games, the whole payoff) gets a worker route with server-computed candidate plies and a reclassification-skipping minimal submit. The server-side fallback stays as an instrumented rare safety net.

Expected impact: fleet engines from ~68% to ~95%+ busy and near-linear backfill scaling with added workers (baseline 2026-07-17 in SEED-111).

</domain>

<decisions>
## Implementation Decisions

### Locked upstream by SEED-111 (do not re-litigate)
- **S-01:** Targeted re-search, NOT a blanket MultiPV-2 full pass. The full-ply pass stays MultiPV-1 (guarded by `test_eval_positions_uses_multipv1_no_second_best`); the worker runs a second targeted `evaluate_nodes_multipv2` only for plies where played == its own best.
- **S-02:** Trust boundary unchanged — the server never trusts worker judgement, only numbers. It re-applies the played==best check, out-of-book gate, and inaccuracy gate itself from submitted evals before running Maia. Submitted entries are ply-keyed and tamper-guarded (in-range check, 422 on garbage).
- **S-03:** Version gating at LEASE, not just submit. `WORKER_SCHEMA_VERSION` → 2; version in the atomic-lease request; v1 workers get 204 (no work) on the atomic lane and idle harmlessly until upgraded. Entry-ply and flaw-blob lanes may stay v1-compatible if convenient.
- **S-04:** Server fallback kept as a rare safety net, instrumented (Sentry tag/metric) so silently re-growing server Stockfish load is visible. Expected steady-state: near zero worker-path fallbacks.
- **S-05:** Tier-4b lease must carry **server-computed candidate plies** (played == stored best_move, out-of-book, from existing best_move/pv columns + book filter) — the SEED-076 incremental filter means a fully-analyzed game leases with no plies for the worker to run a full pass on. Worker compute is exactly the N candidate runner-up searches.
- **S-06:** Tier-4b submits skip reclassification — write `game_best_moves` + stamp `best_moves_completed_at`, touch nothing else (avoids the FLAWCHESS-8D StaleDataError surface churn).
- **S-07:** Worker-side Maia inference rejected (bit-consistency risk across fleet, no throughput win — uvicorn incl. Maia is ~0.5 core).

### Tier-4b worker lane shape
- **D-01:** Workers reach tier-4b by **extending the idle fall-through**: `scope=idle` falls through to tier-4b after tier-3 empties — only for v2 workers and only when `BEST_MOVE_BACKFILL_ENABLED`. No new worker-side scheduling; the existing ladder preserves lane priority (fresh work first).
- **D-02:** Tier-4b results return via a **dedicated submit endpoint** (e.g. `/bestmove-submit`) with its own small schema (game_id + per-ply runner-up evals). The minimal apply path is structural — no worker-supplied discriminator can route a fresh-analysis submit around reclassification. Mirrors the flaw-blob-lease/submit pair pattern.
- **D-03:** Candidate-ply validation is a **stateless recompute at apply**: the server recomputes the candidate-ply set from its own stored best_move/pv columns + book filter and drops/422s any submitted ply outside it. No lease state persisted; server fully authoritative.
- **D-04:** **One flag gates both**: `BEST_MOVE_BACKFILL_ENABLED=off` means no tier-4b work leases to anyone (workers or drain). Single switch, consistent with the v2.4 D-05 rollout pattern.

### Drain's role after the shift
- **D-05:** The in-process server drain **stays a tier-4b consumer with a tier-aware minimal path** — candidate searches only, minimal write, no reclassify — reusing the same server-side candidate/writer code as the fallback. This also fixes the existing bug where `run_one_full_eval_tick` ignores tier (eval_drain.py:908) and re-evaluates every ply of a tier-4b game at MultiPV-2 and reclassifies from scratch. The freed 8-engine pool (~1/3 of current fleet capacity) keeps contributing to backfill.
- **D-06:** Fallback instrumentation is **tagged by source path**: drain-local inline candidate computation (expected — locally-drained fresh games have no worker) vs worker-submit fallback (the regression signal, expected ~zero). The regression watch reads only the worker-submit dimension.
- **D-07:** The phase includes an **explicit post-deploy before/after measurement step** (HUMAN-UAT/verification): re-measure games/h stamped, worker engine busy %, server pool utilization, and fallback counts against the 2026-07-17 baseline recorded in SEED-111.

### Double-claim / TTL leases
- **D-08:** TTL-lease escalation (D-4) is **deferred**. The D-07 measurement step also records the double-claim rate; if it stays around ~12% or grows post-shift, TTL leases become their own follow-up (seed/phase). Measure before optimizing.

### Claude's Discretion
- **Fresh-lane lease details** (area not selected for discussion): follow the seed's lean — include `move_uci` per position in the lease response (simpler than deriving from consecutive positions); out-of-book filtering stays server-side (worker computes second-best for ALL played==best plies, server drops in-book ones). Optionally carry the book-ply count in the lease to trim the superset if cheap.
- Exact endpoint/scope naming, lease/submit Pydantic schema shapes, Sentry tag names, and worker-side retry behavior for failed targeted searches.
- v1→v2 fleet upgrade sequencing (Adrian operates all 4 worker hosts; v1 workers idling on the atomic lane during rollout is acceptable by design).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (primary)
- `.planning/seeds/SEED-111-worker-side-multipv2-gem-candidates.md` — the full design sketch, the code-verified 2026-07-17 tier-4b amendment (three gaps the planner must cover), alternatives considered, open questions, and the measured baseline for D-07. This is the phase's spec in all but name.

### Code surfaces (from SEED-111 references, verified present)
- `app/services/eval_apply.py` — `_build_best_move_candidates` (line ~1823): the Pitfall-1 fallback to remove from the hot path; becomes the instrumented safety net + the reusable server-side candidate/writer code for drain + tier-4b validation.
- `app/routers/eval_remote.py` — `atomic_lease_eval_game` (384), `_apply_atomic_submit` (1002), `atomic_submit_eval` (1237); `worker_schema_version` "accepted but not gated on" (1255); `_lease_position_redundant` (197, the SEED-076 incremental filter behind S-05); flaw-blob lease/submit pair (723/937) as the pattern for the new dedicated submit.
- `scripts/remote_eval_worker.py` — `WORKER_SCHEMA_VERSION = 1` (102); `_eval_atomic_game` (331, MultiPV-1 full pass + blob pass); `_run_cycle` (588) worker ladder.
- `app/services/engine.py` — `evaluate_nodes_multipv2`, the 1M-node call being shifted.
- `app/services/eval_queue_service.py` — `_claim_tier4_bestmove` (666), `claim_eval_job` (749) scope ladder (`idle` 204s after tier-3 today; `None` bundles tier-4 lanes).
- `app/services/eval_drain.py` — `run_one_full_eval_tick` (~908) ignores tier (`_ = tier`); needs the D-05 tier-aware minimal path.

### Invariants that must survive
- Phase 146 D-03 eval-parity invariant: full-ply pass is MultiPV-1; guarded by `test_eval_positions_uses_multipv1_no_second_best`.
- SEED-076 lease gotchas (post-move shift / `preserve_existing_evals`; delete-then-insert reclassify with snapshot/restore) — the tier-4b minimal path exists precisely to bypass the reclassify surface, not to modify it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Flaw-blob lease/submit endpoint pair (`/flaw-blob-lease` + `/flaw-blob-submit`) — the structural template for the dedicated tier-4b submit (D-02) and the token/tamper-guard spirit for D-03.
- `_build_best_move_candidates` already contains the candidate-selection logic (played==best, out-of-book, inaccuracy gate) — refactor so the same code serves: (a) worker-submit validation recompute, (b) drain minimal path, (c) instrumented fallback.
- Worker script already has a MultiPV-2 pass helper (`_eval_atomic_blob_nodes` / `_eval_flaw_blob_positions`) showing the `asyncio.gather` + pool pattern for the new targeted gem-candidate re-search.

### Established Patterns
- Version handling: `worker_schema_version` already flows through submit schemas and heartbeats (`heartbeat_worker_schema_version`) — v2 gating extends existing plumbing rather than inventing new.
- 204-as-no-work is the established lease-lane empty signal; v1 gating on the atomic lane reuses it.
- Sentry rules (CLAUDE.md): tags for filterable dimensions, `set_context` for structured data, never embed variables in messages — applies to the D-06 fallback instrumentation.

### Integration Points
- `claim_eval_job` scope ladder in `eval_queue_service.py` — D-01 extends `scope=idle` fall-through under v2 + flag gating.
- `_apply_atomic_submit` — fresh-lane apply consumes worker-submitted second-best entries into `second_best_map` instead of triggering the fallback.
- `eval_drain.py` tick — gains the tier-aware branch (D-05).

</code_context>

<specifics>
## Specific Ideas

- The measurement deliverable (D-07) compares against the exact numbers in SEED-111 §"Measured baseline (2026-07-17)": ~550 games/h stamped, 629 worker submits/h, server pool ~92% busy, local worker engines ~68% busy, 8.6 stored rows/game.
- Expected steady-state after the shift: worker-submit fallback count ~zero; any sustained non-zero rate is the regression signal D-06 exists for.

</specifics>

<deferred>
## Deferred Ideas

- **TTL-lease escalation (D-4)** — double-claim mitigation deferred (D-08); revisit as its own seed/phase if the post-shift measured double-claim rate stays ~12% or grows.
- **uvicorn single-thread bottleneck** (Maia + classify + PGN parse, ~0.5 core today) — next candidate bottleneck at much higher submit rates; measure before optimizing (Maia batch inference / thread offload only if it shows). Per SEED-111 open question #3.

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md` — client-side gem-sweep review warnings (WR-01/03/05/06); frontend, unrelated to the worker protocol; likely partially obsolete since Phase 175 demoted the sweep.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — unrelated DB feature (partial-position queries).

</deferred>

---

*Phase: 177-worker-side-multipv2-gem-candidates*
*Context gathered: 2026-07-17*
