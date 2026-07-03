---
id: SEED-076
status: open
planted: 2026-07-03
planted_during: /gsd-explore session investigating prod user 218's eval-chart gaps. Quantified 36 games / 642 opening-weighted hole plies stamped complete via the Path-C cap. Root cause (confirmed via Sentry FLAWCHESS-8B, `atomic-submit ... residual holes`, geo DE): a **weak Hetzner remote worker** ran the same engine (`_NODES_TIMEOUT_S = 5.0s`, engine.py:100) and timed out on high-branching opening positions on slower hardware, submitting partial evals; the server re-leased 3× and Path-C-stamped (`eval_remote.py:1300`). NOT the in-process server pool. Full evidence: `.planning/notes/eval-chart-opening-holes-root-cause.md`.
trigger_when: Next eval-pipeline / remote-worker phase, OR when Sentry FLAWCHESS-8B (`atomic-submit: stamping complete after MAX_EVAL_ATTEMPTS with residual holes`) recurs on a large single-user import, OR when a user reports eval-chart gaps again. Watch it when the remote fleet grows (more heterogeneous / weaker boxes) or when a slow worker's leases climb.
scope: phase (1-2 plans) — mostly a server-side change on the `/atomic-submit` Path-C branch (don't permanently stamp worker-timeout holes) plus optional worker-side retry/backoff. No new data model likely needed (reuse `full_eval_attempts`, `opening_position_eval` cache). Add a regression test that simulates a worker submitting a partial (opening-missing) eval set and asserts the game is NOT permanently Path-C-stamped without a re-drain path.
depends_on: none hard. Pairs with the self-heal TODO (`.planning/todos/pending/self-heal-eval-holes-user218.md`) which fixes the existing 36 rows; this seed prevents recurrence.
---

# SEED-076: Harden `/atomic-submit` against weak-worker timeout holes

## The problem

The Path-C cap (D-116-07 no-loop invariant) is a *correctness* safety valve — it stops a
deterministically-unevaluable position from looping forever. But on the `/atomic-submit`
path it currently cannot tell a **deterministic** hole (terminal / illegal / genuinely
unevaluable) apart from a **worker-side timeout** hole (a slow opening position the remote
worker's Stockfish couldn't finish within `_NODES_TIMEOUT_S = 5s` on weaker hardware). Both
hit the same cap, so a game a *weak worker* couldn't fully evaluate gets stamped
`full_evals_completed_at` **permanently** and is never revisited — even though the in-process
server pool (which dedups the now-warm openings) or a stronger worker would fill it trivially.

Observed impact: a Hetzner worker on user 218's batch produced 36 games with 642
opening-weighted holes, all permanently stamped (Sentry FLAWCHESS-8B, 45 events). Scales
with how much a weak/slow worker is handed and gets worse as the remote fleet grows more
heterogeneous.

## Directions to consider (not yet decided)

1. **Don't let a weak worker's partial submit be final.** On `/atomic-submit` Path C, if the
   residual holes are timeout-class (worker returned the `(None,…)` sentinel, not a
   terminal/unevaluable position), do NOT permanently stamp — re-route the game to the
   in-process server pool (which dedups openings via `opening_position_eval`, so it's cheap)
   or re-lease to a different worker. This is the primary lever.
2. **Worker self-retry before submit.** Have the worker retry its own timed-out plies (or
   fall back to a lower node budget for just those) before submitting, so a slow box doesn't
   ship a hole-riddled game in the first place.
3. **Capability-aware leasing.** Keep slow/weak workers on tier-4 blob work (they already do
   this fine) and exclude them from full-eval `atomic-lease` via a latency/capability signal,
   so full-eval games only go to workers that can finish them under the timeout.
4. **Adaptive / higher node-timeout on slow workers** — riskier; `_NODES_TIMEOUT_S = 5.0` is
   already 4× *prod* p90, and a weak box's p90 is higher, so a per-worker calibrated timeout
   could help, but it trades throughput for coverage. Prefer (1)–(3).

## Why not just fix it now

Out of scope for an explore session, and it needs a real design pass (which lever, and a
regression test that reproduces a partial-timeout game). The immediate 36 stuck rows are
handled by the separate self-heal TODO; this seed is the go-forward prevention.
