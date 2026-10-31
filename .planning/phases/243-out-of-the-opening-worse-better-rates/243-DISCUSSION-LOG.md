# Phase 243: Out of the Opening Worse/Better Rates (SEED-206) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-31
**Phase:** 243-out-of-the-opening-worse-better-rates
**Areas discussed:** CDF shape per TC, popover histogram content

Areas offered but not selected: the 95% gate definition, and the weights and below-floor TCs. SEED-206's proposals
were adopted as defaults.

---

## CDF shape per TC

| Option | Description | Selected |
|--------|-------------|----------|
| Pooled over colours | One CDF per TC per rate from user × colour points; 2 metric ids | ✓ |
| One CDF per colour | Separate White/Black CDFs per TC; 4 metric ids, half the points per cell | |
| Pooled per user | Combine both colours per peer; mismatches the per-colour user value | |

**User's choice:** Pooled over colours.

---

## Popover histogram content

Proposed questions: which games feed the histogram, how games that ended before the middlegame are shown, and the
bin layout.

**User's choice (free text):** "I think we shouldn't show a histogram in the popover tooltips, we don't do that for
any other percentile tooltips either."

**Notes:** The histogram was dropped. The popover follows the `RankedMetricPopover` structure. The per-TC breakdown
from SEED-206 stays as a compact list. The footer uses a 95% CI and keeps the filter-independence disclosure.

---

## Claude's Discretion

- 95% gate: a Wilson 95% CI on the pooled count must exclude the game-weighted peer median (SEED-206 proposal).
- Weights are qualifying games. Below-floor TCs are dropped from the headline and the gate, and listed in the
  popover.
- The per-user percentile storage shape (no colour column in `user_benchmark_percentiles`).
- The API shape, and the Umami popover target.

## Deferred Ideas

- Opening LLM narration consuming these percentiles.
- Per-opening worse/better bars (cut by the owner).
- An "out of the opening over time" chart.
