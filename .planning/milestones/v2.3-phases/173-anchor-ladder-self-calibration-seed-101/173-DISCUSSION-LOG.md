# Phase 173: Anchor ladder self-calibration (SEED-101) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-15
**Phase:** 173-anchor-ladder-self-calibration-seed-101
**Areas discussed:** All four delegated to Claude ("you decide") with an info-efficiency directive

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Match schedule & game budget | Full round-robin vs sparse graph; games per pair | ✓ (delegated) |
| Rating model & fit tooling | Hand-rolled BT/logistic MLE vs BayesElo/Ordo; Python vs Node; draw handling | ✓ (delegated) |
| Harness integration | New script vs mode flag in calibration-harness.mjs; sf8/sf10 wiring | ✓ (delegated) |
| Output artifact & SEED-102 hand-off | Where the internal scale lives; run execution in scope? | ✓ (delegated) |

**User's choice:** "you decide. make sure we don't waste time testing combinations which don't give us useful information"
**Notes:** Single binding directive — information per game is the design criterion. Claude locked all decisions (D-01 … D-13 in CONTEXT.md): two-pass probe→measure schedule gated on the 0.2–0.8 score band, sparse pair graph with a connectivity guard, Python logistic MLE fit (no external rating binaries), new standalone harness script reusing lib modules, run execution + findings note in scope.

---

## Todos

| Option | Description | Selected |
|--------|-------------|----------|
| Fold neither (Recommended) | Both matches are keyword noise | ✓ |
| Fold 172 review findings | Frontend gem-sweep review deferrals | |
| Fold bitboard storage | Partial-position query storage idea | |

**User's choice:** Fold neither.

## Claude's Discretion

All four areas — user delegated with the info-efficiency directive. Researcher/planner may adjust details within D-01 (no wasted games) and D-04 (graph connectivity).

## Deferred Ideas

- Blend 0.05 vs 0.5 hedge probe (SEED-102 locate pass)
- Bot-harness anchor-window fixes (SEED-102)
- Human-ELO correction (SEED-103); lookup tables (SEED-104)
