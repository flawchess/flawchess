# Phase 145: Corpus Backfill + Rollout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 145-corpus-backfill-rollout
**Areas discussed:** Backfill mechanism, Old-worker churn safety, Retag role + sequencing, SC4 lichess-gating

---

## Backfill mechanism — fleet path

| Option | Description | Selected |
|--------|-------------|----------|
| Re-arm (resweep-style) | Clear `full_evals_completed_at`, fleet re-drains the whole game (re-eval + re-classify + blobs). Zero new contract, but redundant compute + flaw-set drift risk. | |
| Narrow blob-only remote job | New job computes only MultiPV-2 second-best for flaw PV-line nodes; no re-eval, no re-classify; server reconstructs PV walk from stored `game_positions.pv`. | ✓ |
| You decide / research | Surface both, let research pick on corpus size. | |

**User's choice:** Narrow blob-only remote job.
**Notes:** The bulk compute must go to the remote fleet (founding directive). Narrow job avoids redundant full re-eval and avoids re-classify drift.

---

## Backfill mechanism — job lane / queue

| Option | Description | Selected |
|--------|-------------|----------|
| New tier on `eval_jobs` | Reuse `eval_jobs` table + lease/submit with a new kind/tier. | |
| Separate `backfill_jobs` table | Dedicated table + endpoints. | |
| (User redirect) Reuse the tier-3 table-less lottery | Tier-3 drain uses NO `eval_jobs` table (`job_id=None`); reuse that lottery for the blob-only jobs. | ✓ |

**User's choice:** "No table. Note that tier-3 eval drain also doesn't use the `eval_jobs` table. Maybe we can reuse the tier-3 drain lottery for the blob-only jobs?"
**Notes:** Grounded against `_claim_tier3_derived` (ES weighted lottery, predicate-driven, self-deduping). Became D-02/D-03.

---

## Backfill mechanism — lease priority

| Option | Description | Selected |
|--------|-------------|----------|
| Lowest tier (after tier-3) | Tier-4 lottery, fires only on spare capacity, `EVAL_AUTO_DRAIN_ENABLED`-gated. Never starves live work; finishes eventually. | ✓ |
| Above tier-3 idle backlog | Faster rollout but delays first-time analysis for active users. | |
| You decide / research | Let research place it by backlog size. | |

**User's choice:** Lowest tier (after tier-3).
**Notes:** Spare-capacity drain; live analysis always wins.

---

## Backfill mechanism — lease/submit payload shape (Option 1 vs 2 weighed in prose)

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse per-game ply-keyed lease, worker agnostic | One endpoint, no new schema; but line-continuation nodes aren't game plies → overload `ply` as a node index AND branch the live `_apply_submit` handler anyway (blast-radius risk). | |
| Dedicated token-keyed flaw-line schema | New lease/submit modeled on the Phase 123 entry-ply batch; honest `(flaw_ply, line, node_k)` keys; isolated from live eval ingest; worker stays token-opaque. | ✓ |
| You decide / research | Confirm worker multipv-2 capability, pick minimal-change shape. | |

**User's choice:** Lock Option 2 (after requesting an explicit pros/cons weighing).
**Notes:** Decisive factors: the positions are PV-line nodes (not game plies), and Option 1's "less surface" is illusory because it still branches the safety-critical live submit handler. Became D-04/D-04a.

---

## Old-worker churn safety

| Option | Description | Selected |
|--------|-------------|----------|
| Sentinel blob write | Write `[]` for un-fillable flaws so they stop matching the `IS NULL` predicate. Self-cleaning, no migration. | ✓ |
| `blob_attempts` counter column | Attempt counter + max-attempts cap. Explicit telemetry but needs a migration. | |
| You decide / research | Check how common un-fillable flaws are first. | |

**User's choice:** Sentinel blob write.
**Notes:** Old-worker half of the risk already dissolved by Option 2 (new endpoint = capability signal). The real residual was poison-pill un-fillable flaws → sentinel. Became D-05/D-06.

---

## Retag role + sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Decoupled repeatable retag sweep | Keep blob-submit assemble-only; apply tags via repeatable `retag_flaws.py --db prod`. Clean isolation; needs a progress signal. | |
| Per-game retag inside blob-submit | After writing a game's blobs, run `_classify_tactic_gated` for that game → rolling rollout, each game lands complete. Re-introduces re-classify into the submit path. | ✓ |
| You decide / research | Weigh isolation vs rolling convenience. | |

**User's choice:** Per-game retag inside blob-submit.
**Notes:** User's reasoning — the endpoint is transitional; once backfill/retag is done it goes quiet and new games get blobs from full analysis anyway, so the isolation tradeoff is low-stakes. Captured that `retag_flaws.py --db prod` is still needed for already-blobbed stale-tag games (D-08).

---

## SC4 lichess-gating

| Option | Description | Selected |
|--------|-------------|----------|
| Cover lichess games too | Backfill predicate spans engine + lichess games with NULL blobs; lichess needs real engine second-best (fleet work). Matches SC4 literal wording; uniform denoising. | ✓ |
| Engine games only (this phase) | Scope to `lichess_evals_at IS NULL`; lichess keeps ungated tags; lichess gate coverage becomes a follow-up. | |
| You decide / research | Confirm lichess games have stored flaw PVs first. | |

**User's choice:** Cover lichess games too.
**Notes:** Verified the multipv2 pass runs unconditionally in `_full_drain_tick`, but the tier-3 predicate rarely selects lichess games on prod. Logged the D-09a feasibility flag: `_fill_engine_game_flaw_pvs` no-ops for lichess, so lichess flaws may lack stored PVs to walk — research must confirm before planning.

---

## Claude's Discretion

- SC3 per-motif chip-count before/after snapshot mechanism + timing (rolling rollout).
- Backfill progress / observability signal (count of still-NULL-blob flaws).
- Exact tier-4 endpoint paths, Pydantic schema names, token encoding, batch size, prod pacing.
- Dev-first end-to-end validation before `--db prod`.

## Deferred Ideas

- resweep-style full re-arm (rejected, D-01).
- Solver-only blob storage (141 D-03 deferral).
- Raising `STOCKFISH_POOL_SIZE` to 8 (separate 24h-soak gate).
- Lichess coverage fallback to a follow-up phase if D-09a feasibility fails.
