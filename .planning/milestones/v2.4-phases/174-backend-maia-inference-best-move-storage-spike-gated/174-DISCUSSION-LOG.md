# Phase 174: Backend Maia Inference + Best-Move Storage (spike-gated) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-16
**Phase:** 174-backend-maia-inference-best-move-storage-spike-gated
**Areas discussed:** Spike-gate parity/fail-path, ONNX session & prod RAM, ELO clamping, Storage column types

---

## Spike-gate — parity tolerance & fail path

| Option | Description | Selected |
|--------|-------------|----------|
| Tier-stability + loose eps | Pass iff every fixture ply lands in the same gem/great/neither tier both sides, raw prob within ~±0.02. Fail → phase pauses for re-scope; worker-fallback is a documented escape hatch, not auto-taken. | ✓ |
| Tight raw epsilon | Require maia_prob within ~±0.005 on every ply regardless of tier — a faithful numeric reimplementation. | |

**User's choice:** Tier-stability + loose epsilon.
**Notes:** Tiers are coarse buckets (Gem ≤ 0.20, Great (0.20, 0.50]); tier agreement is what protects stored classification. Benign CPU-vs-WebGPU drift is acceptable if it never flips a tier.

---

## ONNX InferenceSession lifecycle & prod RAM

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy singleton | Load on first gate-passing candidate ply; idle games never pay. | |
| Eager at startup | Load once at app boot; predictable latency, constant residency. | ✓ |

**User's choice:** "is stockfish lazy or eager-loaded? I think we should do the same with maia."
**Notes:** Verified Stockfish is eager-loaded at FastAPI lifespan startup (`app/main.py:96` → `start_engine()`; `stop_engine()` at shutdown). Decision: mirror it with `start_maia()`/`stop_maia()` on the same lifespan (eager). Guardrails added: no-op when onnxruntime absent (deps are group-isolated); measure steady-state RSS vs the OOM history before enabling in prod.

---

## ELO clamping for out-of-band movers

| Option | Description | Selected |
|--------|-------------|----------|
| Clamp to nearest edge | Mirror frontend clampToLadderBounds; still store a row. | ✓ (corrected band) |
| Skip / NULL maia_prob | Store the row but leave maia_prob NULL for out-of-band movers. | |

**User's choice:** "The maia range is 600-2600 lichess blitz equivalent ELO. Clamp outside this interval."
**Notes:** User corrected my framing. The "1100–2000 validated band" is Maia-3's validated draw-rate sub-band; the actual frontend `MAIA_ELO_LADDER` clamps to **600–2600** (21 rungs, step 100). Backend mirrors `clampToLadderBounds` to [600, 2600] so DB-stored and live-board gems never disagree.

---

## Storage column types

| Option | Description | Selected |
|--------|-------------|----------|
| Raw cp ints | Store best_cp/second_cp (+ mate flags); ES conversion query-time. Matches second_best_map + game_positions.eval_cp; fully retunable. | ✓ |
| ES floats | Store pre-converted expected-score floats; simpler query but bakes the sigmoid/mate convention into the corpus. | |

**User's choice:** Raw cp ints.
**Notes:** Keeps cp→ES conversion + mate handling query-time in one place, retunable with zero re-analysis. The 0.05 candidate gate still computes ES at write time to decide row storage; that is independent of what is persisted. Matches SEED-108 D-4's own example column set (best_cp, second_cp).

## Claude's Discretion

- Exact new-table column names/types beyond cp/maia_prob (mate representation, whether to denormalize fen/best_move), uv group name, parity-fixture corpus source, and precise eval-apply insertion point — left to researcher/planner within the locked decisions.

## Deferred Ideas

- Gem/Great ceiling calibration against real per-game frequency (post-pipeline retune; constants-only, GEMS-07).
- Board/EvalPoint consumption + `useGemSweep.ts` retirement + Library gem/great filter → Phase 175.
- Corpus backfill via tier-4 lottery → Phase 176.
- Reviewed-not-folded todos: `172-deferred-review-findings.md` (resolves_phase 175), `2026-03-11-bitboard-storage-...` (unrelated DB idea).
