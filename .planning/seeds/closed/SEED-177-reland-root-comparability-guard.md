---
id: SEED-177
status: closed. Resolved by the 2026-10-02 owner override in Phase 226 (shipped; reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md)
promoted_to: null
planted: 2026-10-01
planted_during: v2.19, Phase 226 plan 226-13 (verdict applied, root guard held by the stacked rule)
trigger_when: SEED-176 (underfill fix) is resolved in favor of shipping, or the next time bot early-stop quality is the priority
scope: small (code exists at arm A21 and passed every one of its own criteria); depends on SEED-176
---

# SEED-177: Re-land the root comparability guard (passed its own criteria, held only by stacking)

## Why This Matters

The guard keeps the bot's clear-winner early stop from firing until every in-window root child has
been looked at once (boost-aware window `W = 0.09`, `ROOT_GUARD_BOOST_ALLOWANCE = 0.04`). It was
held at Phase 225 and again at Phase 226 only because it is stacked on the underfill fix, which is
held (accept rule section 6: a held predecessor holds its dependents).

## Phase 226 result

From `reports/engine-throughput-226/verdict.json` (rendered in
`reports/engine-throughput-226/report.md`), every guard criterion passed:

- Guard S1 (A21 max stop-rule wall): 8,321 ms against the 12,100 ms ceiling.
- Guard S2 (early-stop retention): A21 10 early stops, A2 10.
- Guard MQ (A21 vs A2, stop rule on): net 0 against allowance 1.
- Calibration (report-only): Maia -22.2 +- 27.0, SF -46.7 +- 27.1 pooled, within thresholds 85.0 /
  53.5, no powered shape-guard cell (Phase 199 parity verdict: holds). The SF pooled shift is
  within 7 Elo of the threshold, so this is the closest of the three items; the largest cell was
  (1300, 0.05) SF -111.8 (z 2.24) with Maia 0.0.
- Throughput: no effect by design (CPU-normalized 0.99-1.02). The large raw ratios at t400-p4
  (1.61) and t50-p2 (1.31) are per-grade CPU drift in A21's own runs.

## What to do

Ship together with SEED-176 if the owner overrides the underfill verdict. Standalone, the guard
cannot ship under the accept rule because it was measured on top of the underfill fix.

## Breadcrumbs

- Arm A21 commit `29f543f2730621f8567923c83c113e62f4f13519` (reverted in `c6b314c4f`). Phase 225
  A21 was `27beff12f`.
- `reports/engine-throughput-226/report.md`, `verdict.json`, `accept-rule.md` section 6
- `frontend/src/lib/engine/mctsSearch.ts`, `types.ts`, `botBudget.ts` (guard window and
  `rootGuardBoostAllowance`)
- SEED-171 (parent), SEED-176 (prerequisite)
