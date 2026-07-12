# SEED-095: Harden calibration-harness D-10 adjudication for bit-for-bit determinism

**Captured:** 2026-07-11
**Source:** Phase 168 verification (168-VERIFICATION.md gap; accepted via override)
**Status:** open

## Idea

The Phase 168 calibration harness's D-09 determinism check
(`scripts/lib/calibration-determinism.check.mjs`) is **probabilistic**, not a
hard guarantee: under real CPU load, two `blend=1` games with an identical
`--seed`/opening/color can diverge after a few plies.

Root cause (proven in Phase 168 via an A/B test against the untouched pre-pool
Plan-02 code — this is **pre-existing**, not a Stockfish-pool regression): D-10's
adjudication path (`evalPositionCp` in `scripts/calibration-harness.mjs`) runs a
`movetime`-bound (not depth-capped) Stockfish search after every ply. The depth
it actually reaches is sensitive to wall-clock CPU availability, and its side
effect on the shared engine's transposition table then cascades into every
subsequent `grade()` call for the rest of the game.

## Proposed fix (scoped)

Reset the Stockfish hash before **every individual** `go` (bot grade, anchor
move, and adjudication eval) — not just once per game via `ucinewgame` — OR
depth-cap the adjudication search so its reached depth is CPU-independent.
Either makes the determinism check a reliable CI regression gate.

## Why deferred (not done in Phase 168)

- It does **not** affect the phase's actual deliverable: CAL-01's aggregate
  W/D/L strength map depends on statistics across many games, not single-game
  bit-identical replay. The phase goal (measure real engine strength) is met.
- Resetting the hash before every `go` has a plausible throughput cost, which
  matters because grading is already the harness bottleneck (see [[project_flawchess_engine_prior_art]]
  and the Phase 168 spike: the multi-process Stockfish pool exists precisely to
  parallelize `grade()`). The fix should be measured against that cost.

## Trigger to promote

Promote when bit-for-bit single-game reproducibility becomes needed — e.g. a CI
regression gate on the harness, or debugging a specific game replay.
