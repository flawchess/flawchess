# Phase 150: Consolidate Write Path - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 150-consolidate-write-path
**Areas discussed:** R3 equivalence proof, R3 blob/tag preservation semantics

---

## Area selection (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| R3 equivalence proof | How to prove diff/upsert == delete-then-insert | ✓ |
| Blob-preserve semantics | The correctness heart of R3 (8D territory) | ✓ |
| Module split shape (R7) | eval_apply.py home + eval_drain.py split depth | |
| Ride-alongs + rollout (R5/R6) | ride-along firmness + merge granularity | |

**User's choice:** The two R3 areas. Module-split and ride-alongs/rollout delegated as sensible defaults.

---

## R3 — Equivalence proof

| Option | Description | Selected |
|--------|-------------|----------|
| Dual-run, test-first | Keep old path, assert both produce identical state on same inputs, then delete old. Claude's recommendation. | |
| Golden snapshot | Capture today's `game_flaws` state as committed golden data; assert new diff/upsert reproduces it. | ✓ |
| Hand-authored matrix | Write expected end-states by reasoning about intended behavior. | |

**User's choice:** Golden snapshot.
**Notes:** Claude flagged the drift risk (golden can go stale / could encode old quirks). Accepted mitigation captured in CONTEXT D-01: generate the golden from current HEAD (post-149, post-8D-fix, so it captures correct behavior) and commit the reproducible generator script so a reviewer can regenerate before trusting the assertion.

## R3 — Preserved-column set location

| Option | Description | Selected |
|--------|-------------|----------|
| Single source of truth | Derive the 10 preserved columns from one constant / model introspection so a future column can't be silently nulled. | ✓ |
| Inline list, keep as-is | Keep an explicit literal at the one upsert site. | |

**User's choice:** Single source of truth.
**Notes:** Directly removes the "add a column, forget to preserve it" seam — the exact latent-bug class the phase targets. Captured as CONTEXT D-04.

## R3 — Scenario matrix exhaustiveness

| Option | Description | Selected |
|--------|-------------|----------|
| Full matrix | All 7 known incremental-retry cases (fresh, residual-hole retry, ply-out/8D, ply-in, entry-pass replace, dedup-transplant []-sentinel, blobs_pending suppression). | ✓ |
| Core 3 only | Fresh + residual-hole retry + ply-flips-out; leave exotic paths to existing endpoint tests. | |

**User's choice:** Full matrix.
**Notes:** These scenarios ARE the bug history (FLAWCHESS-8D, SEED-076, quick 260703-qgp, Phase 147). Captured as CONTEXT D-02.

## Final check

| Option | Description | Selected |
|--------|-------------|----------|
| Ready for context | Write CONTEXT.md; delegate the rest. | ✓ |
| Discuss the rest | Deep-dive module-split / ride-alongs / rollout. | |

**User's choice:** Ready for context.

---

## Claude's Discretion

- **R7 module split (D-05):** `apply_full_eval` in new `app/services/eval_apply.py`; split `eval_drain.py` entry/full/shared-write; router stops importing private drain helpers. Flag if the split fights the code.
- **R5/R6 ride-alongs (D-06):** both firmly in; planner may defer R6 if R3 balloons — flag, don't drop silently.
- **Sequencing & rollout (D-07):** R1→R4→R3→R7 in order; single local squash-merge after full gate; no incremental prod deploys (pure no-behavior-change refactor).

## Deferred Ideas

None new. Milestone-level deferrals already recorded in SEED-080 (entry/full lane merge, post-move convention, queue/broker rewrite, worker protocol, R14 tier-3 lease, SEED-078 streaming, 426 gate).
