---
title: Import Readiness Gate — hold user on import page until data is fully ready
date: 2026-05-28
context: Explore session. Replaces the window.location.reload()-on-eval-complete hack with a global gate.
---

# Import Readiness Gate

## Problem

The current pipeline unlocks the rest of the app as soon as the **hot import**
finishes (route nav unlocks on first `*_last_sync_at`; see
`frontend/src/App.tsx` `profileHasCompletedImport()`). But several surfaces
depend on the **cold eval drain** (`app/services/eval_drain.py`) and the
Stage B percentile compute that follows it:

- Endgames page Conversion / Parity / Recovery cards
- The eval-dependent `PercentileChip` flavors
- Openings-page stats marked with the Cpu icon (eval-dependent)

While the drain is still running these render with **partial, biased** data
(samples restricted to already-evaluated games), with no signal to the user
beyond an info tooltip showing a running eval counter — which users can't be
relied on to read. The recent `useEvalCoverage` hook fires a one-shot
`window.location.reload()` when eval coverage hits 100%, but that's a band-aid:
it doesn't prevent the user from seeing wrong data *before* the reload, and it
races Stage B (see Constraint 1).

## Decision

**Hold the user on the import page until everything is ready, then unlock all
routes with one clean reload.** Prefer a single coarse global gate over
per-surface loading containers.

### Why global over per-surface

The eval-dependent metrics are **scattered** across pages (Openings Cpu-icon
stats, Endgame cards, percentile chips). Per-component gating is fragile: every
new eval-dependent metric is a place you can forget to gate, and N bespoke
loading containers is a maintenance tax. One coarse gate is simpler and
correct-by-construction.

### Why the over-blocking cost is acceptable

The percentile/anchor math is NOT the bottleneck — confirmed by reading the
code. `interpolate_cohort_percentile` reads a precomputed in-memory artifact
(`COHORT_PERCENTILE_CDF` in the generated `app/services/global_percentile_cdf.py`),
and Stage A/B only query the *user's own* games (~4 TCs for Stage A; 7 families
× ~4 TCs ≈ 28 user-scoped cells for Stage B). That's **seconds**, even at 40k
games. The entire wait is the Stockfish eval drain at ~13–15 ev/s.

Two-window analysis (drain rate from `logs/import-stress-20k-each-prod-2026-05-27.log`):

| Scenario | Drain time gated | Verdict |
|---|---|---|
| Incremental import (few hundred games) | seconds–~1 min | Imperceptible. Gate is free. |
| First import, typical (few hundred–2k) | seconds–~2 min | Fine. |
| First import, power user (~40k) | ~30–45 min | The only real cost. Rare tail, empty account, nothing worth showing anyway. |

So the gate is cheap in every case except the power-user first import, and that
user self-selected into a huge import on an empty account.

## Locked constraints (must hold in any plan)

1. **Gate on a "percentiles ready" signal, not the raw eval-coverage poll.**
   Stage B fires via `asyncio.create_task` when the drain hits zero pending
   (`eval_drain.py`). If the frontend reloads the instant `/imports/eval-coverage`
   reads 100%, it can land *before* Stage B rows are committed → chips suppress
   or flicker. Need a single authoritative readiness endpoint that returns ready
   only when: **no active import AND `pending_count == 0` AND Stage A/B rows
   persisted.** Do NOT reuse `useEvalCoverage`'s 100% transition as the unlock
   trigger.

2. **The gated import page must be informative, not a blank spinner** —
   especially for the long-tail power user. Drive it as a **state machine off
   the readiness endpoint**: fetching → importing → analyzing endgames (X / Y)
   → computing stats → ready. Use the live eval counter that already exists.
   A legible 30-min wait is tolerable; an opaque one isn't.

3. **"Import complete" must mean readiness-complete, not hot-import-complete.**
   Today the import page shows a completion message at `status=completed`
   (hot import done) — which is *before* the eval drain + percentiles. That's
   the same premature-"done" bug the gate exists to fix. Move the celebratory
   "N games imported and analyzed" message to the **ready** state.

4. **Unlock should be user-initiated, not a forced reload.** A forced
   `window.location.reload()` is jarring AND drops any transient completion
   toast. Instead, the **ready** state shows the success message in-page with an
   enabled **"Explore" CTA**; clicking it navigates (with a hard refresh if
   cache freshness requires it). This preserves the message and gives the user
   control. Retire the `useEvalCoverage` auto-reload.

5. **Eval progress collapses to the import page only.** Today eval coverage is
   surfaced in multiple places — `EvalCoverageHeader.tsx`, the
   `EvalConfidenceTooltip` eval counters, and `useEvalCoverage` consumers inside
   the Endgame cards (`EndgameMetricCard`, `EndgameTypeCard`,
   `EndgameOverallEntryCard`, `EndgameOverallPerformanceSection`) and
   `OpeningFindingCard` / `PositionResultsPanel`. Once a surface only ever
   renders at 100% coverage (the gate guarantees this), it has no in-progress
   state to communicate. **Remove the eval-progress UI from all non-import
   surfaces** and show it only on the gated import page state machine. Expect a
   knip cleanup of the now-unused exports.

## Rejected

- **Per-surface loading containers** — too fragile/messy (the original concern).
- **"Explore with partial data" escape hatch** — reintroduces exactly the
  partial-data messiness the gate exists to remove. Skip.
- **Forced auto-reload on ready** — jarring and eats the completion message;
  use a user-initiated "Explore" CTA instead (Constraint 4).
