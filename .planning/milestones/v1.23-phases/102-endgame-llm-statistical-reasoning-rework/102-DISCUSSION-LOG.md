# Phase 102: Endgame LLM Statistical-Reasoning Rework (v1.23) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 102-endgame-llm-statistical-reasoning-rework-v1-23
**Areas discussed:** CI bounds, Data Analysis length policy, Time-pressure percentile framing, Percentile-as-gate guard (LLM-03)

---

## Gray-area selection

Most of this phase was pre-decided in the `/gsd-explore` note
(`.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md`). The note explicitly
deferred four decisions to discuss-phase. Those four were presented for selection.

| Option | Description | Selected |
|--------|-------------|----------|
| CI bounds: IN or OUT | Final call on confidence-interval fields (note recommends OUT) | ✓ |
| Data Analysis length policy | How to relax the ~300-word `overview` cap | ✓ |
| Time-pressure percentile framing | Per-TC vs page-weighted percentile for time-pressure metrics | ✓ |
| Percentile-as-gate guard (LLM-03) | Final lock on approach (a), percentile-only under the zone gate | ✓ |

**User's choice:** "the provided info should be enough to let you make [an] informed decision."
The user delegated all four decisions to Claude.

---

## CI bounds

**Claude's resolution:** OUT (D-01). Locked to the note's "LIKELY NO" recommendation.
Rationale: `sample_quality` + within-noise + `[near edge]` markers already cover precision/hedging;
raw CI bounds invite jargon recitation that `feedback_popover_copy_minimalism` /
`feedback_llm_prompt_design` steer away from.

## Data Analysis length policy

**Claude's resolution:** Signal-gated relaxation (D-08). Default ~250-300 words; MAY extend to
~500 words / 5 paragraphs only when ≥3 distinct non-overlapping non-typical-zone signals exist.
All existing guards (silence-invalid, no-fabrication, within-noise, flat-trend) preserved.

## Time-pressure percentile framing

**Claude's resolution:** Percentiles ON where TPCTL is available, granularity-matched (D-06):
per-TC narration uses direct per-TC TPCTL (no weighting), page-aggregated metrics use
game-count-weighted, under the same zone gate. Plan-time verification of TPCTL availability and
narration granularity required (D-07).

## Percentile-as-gate guard (LLM-03)

**Claude's resolution:** Approach (a) locked (D-04). Percentile-only enrichment under the zone
gate; no parallel sig fields; prompt guard must forbid an extreme percentile in a `typical` zone
from opening the gate. Cohort framing matches the chips (D-05).

---

## Claude's Discretion

All four deferred decisions were delegated to Claude and resolved as D-01, D-04, D-06, and D-08
in CONTEXT.md. The planner retains normal latitude on implementation mechanics (payload field
names, prompt prose structure) within those locks.

## Deferred Ideas

- Recommendations-section rework — `SEED-034`, not in Phase 102 scope.
- Restoring Phase 88.1-removed surfaces on the page — not needed; payload-only phase.
