# Phase 176: Backfill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-17
**Phase:** 176-backfill
**Areas discussed:** Self-termination signal, Lottery keying, Corpus scope, Operational safety

---

## Self-termination signal

| Option | Description | Selected |
|--------|-------------|----------|
| New `best_moves_completed_at` column | Nullable timestamp stamped by the drain tick (both paths); predicate `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`. Clean, unambiguous, handles no-gem games. | ✓ |
| Sentinel row in `game_best_moves` | ply=-1 sentinel so EXISTS becomes a reliable marker; no migration but pollutes the domain table. | |
| Temporal cutoff on `full_pv_completed_at` | Hard-coded 174-deploy timestamp; fragile, non-durable. | |

**User's choice:** New `best_moves_completed_at` column (D-01)
**Notes:** Flagged the coupling — the go-forward write path must also stamp the marker, else fresh games re-enter the pool forever.

---

## Lottery keying

| Option | Description | Selected |
|--------|-------------|----------|
| New parallel tier-4b rung | `_claim_tier4_bestmove`, copy of `_claim_tier4_blob`, ordered after it in the bundled `scope=None` path; backend-only. | ✓ |
| OR-broaden the tier-4-blob rung | Fold best-move condition into the blob rung's predicate. Risky: that rung feeds the worker `/flaw-blob-lease`. | |
| Extend tier-3 residual fallback | 176 games have `full_pv_completed_at NOT NULL`, so no real reuse; competes with needs-engine. | |

**User's choice:** New parallel tier-4b rung (D-02)
**Notes:** User asked whether a new rung means updating all workers. Verified: NO — best-move rows require Maia, which is backend-only (onnxruntime excluded from `Dockerfile.worker`, GEMS-06). Remote workers never reach the bundled tier-4 path (they use `scope=idle` + `/flaw-blob-lease`). So the rung is backend-only with zero worker changes; giving workers a `/best-move-lease` is a non-starter. This collapsed the choice to backend-only new-rung vs OR-broaden; OR-broaden rejected because the blob rung doubles as the worker lease source.

---

## Corpus scope

| Option | Description | Selected |
|--------|-------------|----------|
| Engine-only (`lichess_evals_at IS NULL`) | Drains games WE analyzed (all chess.com + engine-analyzed lichess/bot); lichess imported-eval games stay 174-07's job. | ✓ |
| All analyzed games (drop lichess filter) | 176 and 174-07 both target undrained lichess games — redundant double coverage. | |

**User's choice:** Engine-only (D-03)
**Notes:** User raised: "we've only talked about lichess games; how do chess.com games get best-move rows?" Verified against dev DB — `lichess_evals_at` is the eval *source*, not the platform. chess.com (149,553 games, 6,106 pv-complete targets, ~94% of the target population) is entirely in the engine bucket and IS covered by the engine-only predicate. Terminology clarification captured in CONTEXT.md so the planner doesn't misread the predicate as "exclude the lichess platform."

### Init-stamp sub-decision

| Option | Description | Selected |
|--------|-------------|----------|
| One-time migration stamp | Stamp `best_moves_completed_at` WHERE EXISTS(game_best_moves) in the same migration; avoids re-draining already-covered games. | ✓ |
| No migration stamp | Let the lottery re-drain covered games once (idempotent); simplest, small wasted compute. | |

**User's choice:** One-time migration stamp (D-04)

---

## Operational safety

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated `BEST_MOVE_BACKFILL_ENABLED` flag | Independent kill-switch (default False); rung checks it AND `EVAL_AUTO_DRAIN_ENABLED`. Enable in prod after observing RSS/CPU. | ✓ |
| Ride `EVAL_AUTO_DRAIN_ENABLED` only | Matches tier-4-blob precedent, but no independent control if backend CPU pressure appears. | |

**User's choice:** Dedicated `BEST_MOVE_BACKFILL_ENABLED` flag (D-05)
**Notes:** Decisive factor — best-move backfill load is backend-only (can't shed to the 4-worker box that carries ~85% of blob backfill), so it needs an independent pause. RAM risk negligible (Maia session already resident); D-02 preemption protects live analysis latency.

## Claude's Discretion

- Exact column type (`TIMESTAMPTZ`), index name, and whether to reuse `TIER4_*` half-life/floor constants or add `BEST_MOVE_*` ones.
- SC3 coverage-growth verification via snapshot-diff of `game_best_moves` counts (no ETA/100% promise).
- Routing the tier-4b claim through the existing `run_one_full_eval_tick` (backfill must re-run the full multipv=2 + Maia pass; per-ply second-best cp isn't persisted for non-flaw plies).
- Maia-absent stamping guardrail: only stamp `best_moves_completed_at` when Maia actually ran, else Maia-absent backends would lock games out permanently.

## Deferred Ideas

- Gem/great threshold calibration against real per-game frequency (GEMS-07, query-time constants, future retune).
- Maia-on-workers escape hatch — rejected (174 D-02); best-move backfill stays backend-only.
