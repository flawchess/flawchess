---
id: SEED-176
status: closed. Resolved by the 2026-10-02 owner override in Phase 226 (shipped; reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md)
promoted_to: null
planted: 2026-10-01
planted_during: v2.19, Phase 226 plan 226-13 (verdict applied, underfill held)
trigger_when: the next time bot-move latency or analysis-board wall time is the priority, or if the owner records an override of the Phase 226 underfill verdict
scope: small (the fix itself exists and is tested at arm A2); the open question is the measurement, not the code
---

# SEED-176: Re-land the round underfill fix (held at Phase 226 on one raw-wall config)

## Why This Matters

`selectPath` in `mctsSearch.ts` gives up instead of backtracking, so a round on a peaked position
collapses to 1-2 effective concurrency. The fix makes rounds denser and is throughput-positive. It
has now been held twice: Phase 225 (a single move-quality flip) and Phase 226 (one raw-wall
throughput config).

## Phase 226 result

Pre-registered verdict, `reports/engine-throughput-226/verdict.json` (rendered in
`reports/engine-throughput-226/report.md`):

- Underfill throughput (A2 vs step-0 A0a, bound 1.05): t50-p4 1.0376, t400-p4 0.9918, t50-p2
  0.9833, **t400-p2 1.1252 (fail)**. This is the only failed criterion for the item.
- Underfill MQ passes (net 1 against allowance 1): the `cBFTV` flip reproduces, was classified a
  side effect in D-13 (denser rounds move the same leaf expansion three rounds earlier), and is
  inside the allowance.
- Powered calibration (report-only): Maia +18.7 +- 27.1, SF +12.6 +- 27.2, within thresholds
  85.0 / 53.5, no shape-guard cell. No refit indicated.
- Report-only CPU-normalized analysis
  (`reports/engine-throughput-226/analysis-2026-10-01-cpu-normalized-throughput.md`): raw wall
  tracks per-grade Stockfish CPU, which drifted up to 1.75x between runs. Normalized, the fix is
  about 5-8% less wall per unit of work on the desktop pool, about 4% at t50-p2 and about 1% at
  t400-p2. The failing t400-p2 ratio matches a 13% per-grade CPU rise with unchanged pipeline
  efficiency (0.991).

## What to do

Either the owner records a dated override of the raw-wall criterion citing the normalized
analysis (then the guard, SEED-177, becomes shippable on its own passing criteria), or a re-run
that measures throughput against a same-session baseline (A0 and A2 interleaved on the same idle
box, so per-grade CPU drift cancels) replaces the cross-day A0a comparison. Do not edit
`accept-rule.md`.

## Breadcrumbs

- Arm A2 commit `756d2a4a1604b0ff050dcf62ce6b94e7b8f4cb76` (reverted in `746848d25`; revert it
  to get the code back). Baseline A0 `3fe340ce948f07646852d37eae2a42e6729c8894`.
- `reports/engine-throughput-226/report.md`, `verdict.json`, `accept-rule.md`,
  `design-inputs.md` (section 4: D-13 `cBFTV` explanation)
- `frontend/src/lib/engine/mctsSearch.ts` (`selectPath`, round dispatch)
- SEED-171 (parent), SEED-177 (root guard, stacked on this), SEED-178 (root split, stacked on this)
