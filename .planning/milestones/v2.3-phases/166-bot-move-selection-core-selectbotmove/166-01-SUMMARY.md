---
phase: 166-bot-move-selection-core-selectbotmove
plan: 01
subsystem: frontend-engine
tags: [bot-play, engine, sampling, mcts, chess-js]
status: complete
dependency-graph:
  requires: [types.ts, guardrail.ts, mctsSearch.ts, select.ts]
  provides: [selectBotMove, botSampling]
  affects: [phase-168-calibration-harness, phase-169-play-loop]
tech-stack:
  added: []
  patterns:
    - "impure orchestrator + pure sync helpers split (mirrors mctsSearch.ts vs select.ts)"
    - "mulberry32 seeded PRNG for deterministic sampling"
    - "softmax over RankedLine.practicalScore with max-subtraction stability"
key-files:
  created:
    - frontend/src/lib/engine/botSampling.ts
    - frontend/src/lib/engine/selectBotMove.ts
    - frontend/src/lib/engine/__tests__/botSampling.test.ts
    - frontend/src/lib/engine/__tests__/selectBotMove.test.ts
  modified: []
decisions:
  - "Kept TAU_EPSILON = 1e-9 (Claude's discretion) as a cheap short-circuit even though sampleRankedLines already uses max-subtraction stability, per RESEARCH Open Question 1's recommendation to implement both defenses"
  - "BotSettings/BotMoveDeps co-located in selectBotMove.ts (not types.ts) per RESEARCH Open Question 2 — a Phase-166-owned contract layered on top of the frozen Phase 153 core, not a modification to it"
metrics:
  duration: 25min
  completed: 2026-07-11
---

# Phase 166 Plan 01: Bot Move Selection Core (`selectBotMove`) Summary

Delivered a pure, provider-agnostic `selectBotMove` orchestrator plus its pure `botSampling.ts` helpers, implementing the full blend-regime dispatch (raw-Maia sampling at `blend=0` → softmax-over-practicalScore in between → deterministic argmax at `blend=1`) that both the Phase 169 play loop and the Phase 168 calibration harness will import unchanged.

## What Was Built

- **`frontend/src/lib/engine/botSampling.ts`** — five pure, synchronous exports: `mulberry32` (seeded PRNG, D-11), `samplePolicy` (weighted pick over a raw Maia policy), `sampleRankedLines` (softmax over `practicalScore` with max-subtraction stability, D-04), `argmaxLine` (explicit `practicalScore` scan, UCI-ascending tie-break, D-06), and `fallbackMove` (chess.js-derived uniform-random legal move, throws only on a genuine terminal position, D-13/D-14). A module-internal `weightedPick` implements the shared UCI-ascending cumulative-distribution walk (D-12).
- **`frontend/src/lib/engine/selectBotMove.ts`** — the impure async orchestrator. Dispatches on `settings.blend`: `<=0` calls `deps.policy` exactly once and never touches `deps.search`/`mctsSearch` (BOT-02); `>=1` runs `deps.search ?? mctsSearch` once then returns the deterministic argmax; `(0,1)` computes `tau = TAU_MAX * (1 - blend)` (`TAU_MAX = 0.10`) and softmax-samples, short-circuiting to argmax when `tau <= TAU_EPSILON`. `budget.elo` is always built symmetrically as `{ w: elo, b: elo }` (BOT-03) with `policyTemperature` intentionally omitted (D-02). Exports `BotSettings`, `BotMoveDeps`, `TAU_MAX`, `TAU_EPSILON`.
- Two co-located test files covering every `<behavior>` item in the plan: 17 tests in `botSampling.test.ts` (determinism, degenerate-null returns, array-order independence for both `argmaxLine` and `sampleRankedLines`, softmax stability at tiny tau, terminal-position throw, `rng()===1` clamp), 12 tests in `selectBotMove.test.ts` (single-Maia-inference invariant, symmetric-ELO budget capture, blend dispatch determinism, fallback on degenerate distributions, side derivation, signal default/forwarding).

## Deviations from Plan

None — plan executed exactly as written. All three tasks (pure helpers, orchestrator, type-check/lint/full-suite gate) completed with zero auto-fixes needed; the Task 3 gate (`tsc -b`, `npm run lint` including knip, `npm test -- --run`) passed clean on the first run.

## Verification Evidence

- `cd frontend && npx vitest run src/lib/engine/__tests__/botSampling.test.ts` — 17/17 passed.
- `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts` — 12/12 passed.
- `cd frontend && npx tsc -b` — zero type errors.
- `cd frontend && npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/` files, unrelated to this phase).
- `cd frontend && npm run knip` — clean, no dead exports flagged (all new `botSampling.ts`/`selectBotMove.ts` exports are consumed by the two new test files).
- `cd frontend && npm test -- --run` — full suite: 1794/1794 tests passed across 141 files.
- `grep -n "practicalScore" botSampling.ts` and `grep -n "maxScore" botSampling.ts` confirm `argmaxLine`/`sampleRankedLines` scan `practicalScore` explicitly with the max-subtraction stability trick present.
- `grep -n "policyTemperature" selectBotMove.ts` shows only a documenting comment, no assignment onto the budget object (D-02).
- `grep -n "elo: { w:" selectBotMove.ts` confirms the symmetric-ELO budget construction (BOT-03).

## Self-Check

- `frontend/src/lib/engine/botSampling.ts` — FOUND
- `frontend/src/lib/engine/selectBotMove.ts` — FOUND
- `frontend/src/lib/engine/__tests__/botSampling.test.ts` — FOUND
- `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` — FOUND
- Commit `5db109e3` (Task 1: botSampling.ts) — FOUND in `git log --oneline`
- Commit `ebf86105` (Task 2: selectBotMove.ts) — FOUND in `git log --oneline`

## Self-Check: PASSED

## Requirements Delivered

- **BOT-01** — `blend=0` samples raw Maia; `blend=1` returns argmax practicalScore; `blend` in `(0,1)` softmax-samples with `τ(b)` sharpness. Proven by `selectBotMove.test.ts`'s "blend=0/blend=1/blend=0.5" describe blocks.
- **BOT-02** — `blend=0` issues exactly one `deps.policy` call and zero `deps.search` calls. Proven by the "single Maia inference" call-count assertions.
- **BOT-03** — `budget.elo = {w: elo, b: elo}`; no player-strength input anywhere in the signature. Proven by the "symmetric ELO" captured-budget test.
- **BOT-04** — degenerate policy/rankedLines fall back to a legal move; a zero-legal-move (terminal) position throws. Proven by both `botSampling.test.ts`'s `fallbackMove` throw test and `selectBotMove.test.ts`'s fallback + terminal-position tests.

## Known Stubs

None — no placeholder data, hardcoded empty values, or unwired components. This is a pure library module with no UI surface.

## Threat Flags

None. The plan's `<threat_model>` already covers this phase's only two trust boundaries (provider-supplied UCI strings via `fallbackMove`'s chess.js re-validation; the never-aborting default `AbortSignal` for DoS mitigation), and no new network endpoints, auth paths, file access, or schema changes were introduced.
