# Phase 262: Facepalm Promotions as Material and Key-Move Gate (SEED-261122-s0j) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-23
**Phase:** 262-facepalm-promotions-and-key-move-gate
**Areas discussed:** Minimum loss for the gate, Queen promotion and the cap, Prod rollout of the pass

Before the questions, the prod probe named in the ROADMAP was run (10% game sample plus an exact SQL run of the
gate change); the numbers are in CONTEXT.md under Specifics.

---

## Minimum loss for the gate

| Option | Description | Selected |
|--------|-------------|----------|
| No floor | Gate = type rule; tiny losses put 4,585 prod rows over 0.7 (0.4% of passers) | ✓ |
| Floor in gate and type | Allowed loss only from a floor (for example 0.25); about 213k rows change type | |
| Floor in the gate only | Type as today, best move below the floor; gate and type differ again | |
| Decide at the checkpoint | Fit report shows both variants | |

**User's choice:** No floor.

| Option | Description | Selected |
|--------|-------------|----------|
| New gate, old as reference | One comparison line for the old gate: AUC and fair / unfair at 0.7 | ✓ |
| New gate only | Just the new model against the shipped one | |
| Also list the moved rows | Plus the labelled rows that change side of the cut | |

**User's choice:** New gate, old as reference.

---

## Queen promotion and the cap

| Option | Description | Selected |
|--------|-------------|----------|
| Keep the cap at 5 | A promotion scores like a hung queen or a mate at the same depth | ✓ |
| Credit a promotion lower | For example +4, a promotion-only value | |
| Raise both caps | Changes stored inputs of rows outside the promotion set | |
| Compare at the checkpoint | Cap 5 against one alternative on the labelled promotion rows | |

**User's choice:** First "Explain the per-depth cap"; after the explanation (per-depth balance, clip to 0..5,
decaying mean, with a table of example lines): "Yes, keep the cap at 5".

| Option | Description | Selected |
|--------|-------------|----------|
| Piece minus pawn | Queen +8, rook +4, bishop or knight +2 | ✓ |
| Always as a queen | Every promotion +8 | |

**User's choice:** Piece minus pawn.

---

## Prod rollout of the pass

| Option | Description | Selected |
|--------|-------------|----------|
| In-place pass right after deploy | One release, then the pass; minutes of old inputs on 3.3% of rows | ✓ |
| Pass before the deploy | New inputs under today's coefficients until the release; second short pass | |
| Shadow columns, strict switch | As in 259: two migrations, index rebuild, 4.7M-row copy | |

**User's choice:** In-place pass right after deploy.

| Option | Description | Selected |
|--------|-------------|----------|
| Promotion rows only | Rows with a promotion token; dry run and a no-token sample check first | ✓ |
| All blunders | Full line pass over about 4.7M rows | |

**User's choice:** Promotion rows only.

---

## Bands and snapshots after refit (not selected)

Proposed defaults at the closing question: re-derive the provisional bands in this phase, leave the 261
snapshots, split the calibration by a release-date constant, re-check the 0.5 "hard to catch" cut.

**User's choice:** "We don't need to re-derive the provisional bands. We'll update them once phase 252
concludes". The other defaults were not objected to.

## Claude's Discretion

- Calibration split by a release-date constant; re-check of `HARD_TO_CATCH_SCORE_BELOW` at the checkpoint.
- Covering index confirmation by EXPLAIN, pass mechanics, spot-check row selection, fate of the spike probes.

## Deferred Ideas

- Provisional facepalm bands: after Phase 252 concludes (SEED-261120-bzq).
- Benchmark DB material backfill: SEED-261120-bzq.
