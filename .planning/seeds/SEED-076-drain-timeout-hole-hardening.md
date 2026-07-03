---
id: SEED-076
status: open
planted: 2026-07-03
planted_during: /gsd-explore session investigating prod user 218's eval-chart gaps. Quantified 36 games / 642 opening-weighted hole plies stamped complete via the D-116-07 Path-C cap. Root cause traced to the per-eval 5s wall-clock timeout (engine.py:100 `_NODES_TIMEOUT_S`) firing on slow opening positions while a 1,220-game single-user batch saturated `STOCKFISH_POOL_SIZE=6`. Full evidence: `.planning/notes/eval-chart-opening-holes-root-cause.md`.
trigger_when: Next eval-pipeline / full-drain phase, OR when Sentry "stamping complete after MAX_EVAL_ATTEMPTS with residual holes" warnings recur on a large single-user import, OR when a user reports eval-chart gaps again. Also surface if `STOCKFISH_POOL_SIZE` is raised (8 target) — higher fan-out widens the timeout-under-contention window.
scope: phase (1-2 plans) — drain-side change to make timeout-holes re-drainable and/or throttle per-user in-flight engine fan-out. No new data model likely needed (reuse `full_eval_attempts`, `opening_position_eval` cache). Backend-only; add a regression test that simulates a partial-timeout game and asserts it is NOT permanently Path-C-stamped without a warm-cache re-drain path.
depends_on: none hard. Pairs with the self-heal TODO (`.planning/todos/pending/self-heal-eval-holes-user218.md`) which fixes the existing 36 rows; this seed prevents recurrence.
---

# SEED-076: Harden the full-eval drain against timeout-induced permanent holes

## The problem

The full-eval drain's Path-C cap (D-116-07 no-loop invariant) is a *correctness* safety
valve — it stops a deterministically-unevaluable position from looping forever. But it
currently cannot tell a **deterministic** hole (terminal / illegal / genuinely unevaluable)
apart from a **transient timeout** hole (a slow opening position that crossed the 5s
wall-clock limit under pool contention). Both hit the same cap, so a purely load-induced
hole gets stamped `full_evals_completed_at` **permanently** and is never revisited — even
though a re-drain in a calmer moment (or with a warm dedup cache) would fill it trivially.

Observed impact: user 218's 1,220-game batch produced 36 games with 642 opening-weighted
holes, all permanently stamped. Scales with batch size and pool contention; will recur on
the next large single-user import and gets *worse* if `STOCKFISH_POOL_SIZE` is raised to 8.

## Directions to consider (not yet decided)

1. **Make timeout-holes re-drainable.** On Path C, if the residual holes are timeout-class
   (engine returned the `(None,…)` sentinel, not a terminal/unevaluable position), leave the
   game re-claimable — e.g. a separate low-priority "residual-hole" sweep that reprocesses
   after the opening cache warms, capped so it still can't loop on truly-unevaluable plies.
   The dedup cache being warm on the second pass is what makes this cheap (transplant, no
   engine).
2. **Throttle per-user in-flight fan-out.** The drain fans ALL of one game's plies across
   the pool simultaneously; a 1,220-game single-user batch compounds this into sustained
   saturation. Cap concurrent games-in-flight per user (or globally) so wall-clock per
   position stays under the 5s timeout. Cheapest lever, no schema change.
3. **Adaptive / higher node-timeout under load** — riskier; `_NODES_TIMEOUT_S = 5.0` is
   already 4× p90, and raising it trades throughput for coverage. Prefer (1)/(2).
4. **Distinguish hole classes in the counter.** `_apply_full_eval_results` already special-cases
   terminal donors (SEED-049) vs engine holes; extend so Path C can branch on whether any
   residual hole is timeout-class before stamping permanently.

## Why not just fix it now

Out of scope for an explore session, and it needs a real design pass (which lever, and a
regression test that reproduces a partial-timeout game). The immediate 36 stuck rows are
handled by the separate self-heal TODO; this seed is the go-forward prevention.
