# Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 142-multipv-2-engine-pass-eval-drain-remote-worker
**Areas discussed:** Compute location & contract, Backward-compat semantics, Node budget & validation

---

## Compute location

| Option | Description | Selected |
|--------|-------------|----------|
| Extend whole-game pass | Turn existing per-ply evaluate_nodes_with_pv into a multipv=2 variant; workers return second-best per ply; server assembles flaw-line blobs | ✓ |
| Flaw-only second pass | Separate engine pass on ~6–12 flaw-line nodes after classification (local/remote-lease) | |

**User's choice:** Extend whole-game pass
**Notes:** Reconciles SC3 (schema extension load-bearing), reuses remote fleet, marginal cost (2nd PV line at same node budget). `_run_multipv2_pass()` is an assembly+write step, not a separate engine pass. New `_analyse_multipv2()` on EnginePool required (return-type forbids reusing `_analyse_with_pv`).

---

## Contract shape

| Option | Description | Selected |
|--------|-------------|----------|
| Inline optional fields | second_cp / second_mate / second_uci (default None) on the per-ply SubmitEval row | ✓ |
| Separate optional list | parallel multipv2_evals list on SubmitRequest, indexed by ply | |

**User's choice:** Inline optional fields
**Notes:** Co-located with the ply, simplest, naturally backward-compatible (old workers omit → None, mirroring the existing job_id precedent).

---

## Worker gap (backward-compat)

| Option | Description | Selected |
|--------|-------------|----------|
| Leave NULL, 145 backfills | Old-worker games keep NULL blobs; backfill_multipv.py fills the tail in Phase 145 | ✓ |
| Server local fallback | Server computes MultiPV=2 locally for any flaw node missing second-best | |

**User's choice:** Leave NULL, 145 backfills
**Notes:** New games on upgraded workers get blobs immediately; MPV-02 "every newly analyzed game" is best-effort-for-upgraded-workers in 142, corpus guarantee lands in 145.

---

## Eval gap (dedup/lichess)

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror SEED-056 recovery | Locally recompute multipv only for flaw nodes lacking engine second-best (opening-dedup / lichess-covered) | ✓ |
| Leave NULL, 145 backfills | Don't special-case; fill in Phase 145 | |

**User's choice:** Mirror SEED-056 recovery
**Notes:** A few nodes per game (cheap), distinct from the worker-version gap (all nodes → defer). Follows the existing `_fill_engine_game_flaw_pvs` PV-recovery pattern.

---

## Node budget

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 1M, validate, bump if needed | Start at existing 1M budget; raise to 1.5–2M only if histogram fails >10%/±0.05 | ✓ |
| Start at 1.5M | Hedge upfront since multipv splits search across two root moves | |

**User's choice:** Keep 1M, validate, bump if needed
**Notes:** Note frames multipv=2 as "the increment" on the current 1M search; don't pre-pay cost.

---

## Validation deliverable

| Option | Description | Selected |
|--------|-------------|----------|
| Committed script + report | Re-runnable scripts/ tool + reports/ output on ≥200 dev flaw positions, gates merge | ✓ |
| One-off analysis in VERIFICATION | Run once, paste into VERIFICATION.md, no reusable tool | |

**User's choice:** Committed script + report
**Notes:** Must be repeatable because 144 (A/B) and 145 (rollout) re-tune the margin offline against the same stored evals.

---

## Claude's Discretion

- Exact `_analyse_multipv2()` / `_run_multipv2_pass()` signatures and helper names.
- The histogram tool's `scripts/`/`reports/` filenames and CLI flags.
- The transaction boundary for the blob write (recommended: same txn as the Step 4b oracle-count UPDATE).
- multipv search timeout tuning.

## Deferred Ideas

- Solver-only blob storage (later cost optimization; 141 D-03 locked every-node).
- Server-local MultiPV fallback for old-worker games (rejected for 142; 145 backfill instead).
- Offline re-tagger CLI + mate/defender tests + idempotency — Phase 143.
- User-28 A/B + final margin commit — Phase 144.
- backfill_multipv.py + prod rollout + chip-count monitoring — Phase 145.
- Raising STOCKFISH_POOL_SIZE to 8 — gated separately on a 24h soak.

## Research flag (noted, not a decision)

- PV1 drift: extending the whole-game pass to multipv=2 changes primary-line eval computation for
  every ply; the MPV-03 histogram only validates second-best ordering. Planner/researcher must confirm
  PV1 eval/best-move quality is preserved or guard it.
