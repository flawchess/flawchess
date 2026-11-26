# Phase 259: Facepalm Score Refit on First Principles (SEED-261121-tau) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-21
**Phase:** 259-facepalm-first-principles-refit
**Areas discussed:** Material aggregate, Reply probability term, Scope of the recompute (Acceptance and labels offered, not selected, defaults accepted)

---

## Before the areas: spike

Run before any question so the discussion started from numbers. The material of 290 labelled rows was recomputed
from today's prod lines with a quiet rule, and `fit_facepalm.py` re-run. Results are in CONTEXT.md, "Specific
Ideas". Scripts in `spike/`.

## Material aggregate

| Option | Description | Selected |
|--------|-------------|----------|
| Decaying mean | Weighted mean over depths 1, 3, 5, 7, 9 of the quiet values. CV 0.903, set 8 0.851. | ✓ |
| Settled value, onset discount | First balance the next depth confirms, discounted by onset. CV 0.886, set 8 0.904. Drops early swings. | |
| Fit decides again | Both in the refit, script chooses. | |

**User's choice:** Decaying mean.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 1/2 fixed | No change to `MATERIAL_DECAY_RATIO`. | ✓ |
| Compare a few ratios | 1/3, 1/2, 2/3 reported as information. | |

**User's choice:** Keep 1/2 fixed.

| Option | Description | Selected |
|--------|-------------|----------|
| Breakdown plus examples | Changes grouped by cause plus about 10 before / after positions, owner confirms before the build. | ✓ |
| Breakdown only | Grouped counts in the fit report. | |
| No extra check | The spike's AUC is enough. | |

**User's choice:** Breakdown plus examples.

| Option | Description | Selected |
|--------|-------------|----------|
| Any capture | Walk on while the next line move is a capture, any square; static exchange at a line end. | ✓ |
| You decide after the review | Start from any capture, refine after the breakdown. | |

**User's choice:** Any capture.

## Reply probability term

| Option | Description | Selected |
|--------|-------------|----------|
| Replace the spread | Only the probability of the key move on both sides. CV 0.907. | ✓ |
| Add next to the spread | Both terms. CV 0.910. | |
| Fit decides | Script compares both shapes. | |

**User's choice:** Replace the spread.

| Option | Description | Selected |
|--------|-------------|----------|
| The blunderer's Elo | "Would a player of your level see this punishment"; free from the existing policy call. | ✓ |
| The opponent's Elo | "Would this opponent find it"; a second policy call. | |

**User's choice:** The blunderer's.

## Scope of the recompute

The first set of questions (rollout, benchmark DB, preliminary bands) was declined: the user asked why the
material arrays change at all, expecting only the aggregation to change.

**Clarification given:** the stored slots are not raw balances. Slot N holds the balance after N plies plus the
blunderer's capture at N + 1, computed in Python with the board at write time; the quiet rule is a different
look-ahead and therefore changes the slot values. Neither capture plies nor raw per-ply balances are stored.

Storage options discussed:

| Option | Description | Selected |
|--------|-------------|----------|
| 1. Rule-applied 9-slot arrays | Quiet rule at write time, SQL unchanged, a rule change needs a replay pass. | |
| 2. Raw per-ply arrays, rule in SQL | Purest separation; heavy SQL expression, line-end settlement still stored. | |
| 3. Raw plus rule-applied arrays | Rule change is an in-database rewrite; one extra array column. Claude's first lean. | |
| 4. Stored final score (user's idea) | Drop the arrays, recompute scores from the lines on any change. Reverses 254 D-01; every refit a prod pass. | |
| Variant: stored `loss` and `missed` | Two scalars computed in Python, score stays a small SQL expression, arrays dropped. Claude's recommendation after option 4 was raised. | ✓ |

**User's choice:** "go with the variant, stored loss and missed".
**Notes:** the user's option 4 prompted the variant; its advantage (the rule lives only in Python) is kept, its
main cost (every coefficient refit becomes a prod pass) is avoided.

| Option | Description | Selected |
|--------|-------------|----------|
| Benchmark DB not in this phase | Prod only, SEED-261120-bzq fills the benchmark DB. Recommended by Claude. | |
| Include it | Same backfill on the benchmark DB in this phase. | ✓ |

**User's choice:** Include it, then reversed after the context was written: "let's exclude the benchmark db
backfill". Final: not in this phase.

| Option | Description | Selected |
|--------|-------------|----------|
| Hold until the refit ships | Bands in `quick/facepalm-prelim-bands` are not merged, re-derived from the new score. | ✓ |
| Ship now, re-derive later | Merge as they are. | |
| Only note the dependency | Not this phase's decision. | |

**User's choice:** Hold until the refit ships.

The rollout question was not re-asked: with new scalar columns the sequence is fixed (fill, one switch release,
gated drop).

## Acceptance (not selected as an area)

Defaults proposed by Claude and accepted with "I'm ready for context": AUC within about 0.02 of 0.897
cross-validated, game 2883555 ply 47 as a fixture, no new label set, one owner checkpoint for the model and the
cuts.

## Claude's Discretion

Column names and NULL encoding, mates in the stored inputs, which move is the best reply, gating of the reply
probability for pure misses, whether the fit's staged selection is re-run, backfill mechanics, the fate of the
spike scripts.

## Deferred Ideas

- Blunder-check sequences with any facepalm score as validation data (raised by the user mid-discussion).
- A fit on user blunder-check answers.
- Total probability of all punishing replies.
- The `detect_sacrifice` gap for a declined offered sacrifice.
- Decay ratio by rating.
