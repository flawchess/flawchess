# Phase 256: Facepalm Refit on Material Aggregated over Depths - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-16
**Phase:** 256-facepalm-refit-material-aggregated-over-depths
**Areas discussed:** Phase creation, Short lines and 252 timing, Unknown best-move probability, Selection rule

---

## Phase creation

| Option | Description | Selected |
|--------|-------------|----------|
| Add Phase 256 | Hand-written ROADMAP entry in v2.29, depends on set 8 labels; seed marked as promoted | ✓ |
| Context only, no roadmap | Write the decisions into the seed file; create the phase later | |

**User's choice:** Add Phase 256.
**Notes:** The command was run on the seed file; no roadmap phase existed.

---

## Short lines and 252 timing

### When the refit runs

| Option | Description | Selected |
|--------|-------------|----------|
| When set 8 is labelled | Labels are the only gate; lines as they are then, repaired ones used if 252 is done | ✓ |
| Wait for 252 and the gap fill | Refit only after 252-06 and the gap-fill line pass | |
| Refit now, re-check after 252 | As option 1 plus a planned re-run after the gap fill | |

**User's choice:** When set 8 is labelled.

### Which rows get a material value

| Option | Description | Selected |
|--------|-------------|----------|
| Depth 3 still required | Coverage rule unchanged; the aggregate adds depths 5, 7, 9 where they exist | ✓ |
| Any known odd depth | Score from whatever exists, including depth 1 alone | |
| Fit report shows both, I decide | Decided at the owner checkpoint | |

**User's choice:** Depth 3 still required.
**Notes:** Claude flagged, without certainty, that depth 1 is the position right after the blunderer's own move
and can rarely show a loss.

---

## Unknown best-move probability (254 WR-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Unscored | Both twins return NULL for a no-loss row without a best-move probability; the fit drops such rows | ✓ |
| Neutral constant | Named constant (pool median of the term) in both twins | |
| Keep as is, document it | No behaviour change | |

**User's choice:** Unscored.

---

## Selection rule

### Role of set 8

| Option | Description | Selected |
|--------|-------------|----------|
| Hold-out check, then train | Choice by repeated CV over sets 1-8; each candidate also fitted on 1-7 and scored on 8; disagreement goes to the owner; final constants on all sets | ✓ |
| Training data only | Set 8 joins training, set 6 stays the only hold-out | |
| Set 8 hold-out decides | Best set 8 AUC ships | |

**User's choice:** Hold-out check, then train.

### Tie between decaying mean and depth 3

| Option | Description | Selected |
|--------|-------------|----------|
| Decaying mean wins ties | Depth 3 stays only if clearly better | ✓ |
| Depth 3 stays on a tie | No model change without a measured gain | |
| I decide at the checkpoint | No automatic rule | |

**User's choice:** Decaying mean wins ties.

### Same input for both terms

| Option | Description | Selected |
|--------|-------------|----------|
| Same input for both | Three candidates in total | ✓ |
| Same, plus one mixed reference | Adds loss at depth 3 with the missed gain as a mean | |
| Full grid | All 9 combinations | |

**User's choice:** Same input for both.

---

## Claude's Discretion

- Not selected for discussion, defaults taken from the seed and Phase 254 (owner asked to discuss the selection
  rule only): the "loses material" gate (threshold 1 against none, decided by the fit), the WR-03 fix, the release
  checks listed at the owner checkpoint.
- Mate handling in the aggregate, the gain floor and cap, the SQL form of the aggregate, constant names, where
  `decaying_mean.py` lives.

## Deferred Ideas

- Scoring rows with a played line shorter than depth 3.
- Mixed inputs and other single depths.
- "Simple capture of an undefended piece", "only winning move", a separate model for pure misses.
- Largest loss at any depth for "neither" rows.
