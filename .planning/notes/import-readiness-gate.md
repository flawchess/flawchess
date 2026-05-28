---
title: Import Readiness Gate — tiered per-page gating until eval data is ready
date: 2026-05-28
context: Explore session. Replaces the window.location.reload()-on-eval-complete hack with a two-tier per-page gate.
---

# Import Readiness Gate

## Problem

The current pipeline unlocks the rest of the app as soon as the **hot import**
finishes (route nav unlocks on first `*_last_sync_at`; see
`frontend/src/App.tsx` `profileHasCompletedImport()`). But several surfaces
depend on the **cold eval drain** (`app/services/eval_drain.py`) and the
Stage B percentile compute that follows it:

- Endgames page Conversion / Parity / Recovery cards + eval-dependent `PercentileChip`s
- Openings page one-row eval-based metrics across subtabs (each: metric label +
  value + tooltip + bullet chart), marked with the Cpu icon

While the drain is still running these render with **partial, biased** data
(samples restricted to already-evaluated games), with no signal to the user
beyond an info tooltip showing a running eval counter — which users can't be
relied on to read. The recent `useEvalCoverage` hook fires a one-shot
`window.location.reload()` when eval coverage hits 100%, but that's a band-aid:
it doesn't prevent the user from seeing wrong data *before* the reload, and it
races Stage B (see Constraint 1).

## Decision — two-tier per-page gate

Don't block the whole app. Gate per-page on a readiness *tier*, letting users
into surfaces that are already correct and locking only what would mislead.

**Tier 1 — hot lane done** (no import job `pending`/`in_progress`):
- **Openings** and **Overview** unlock.

**Tier 2 — fully ready** (Tier 1 **AND** `pending_count == 0` **AND** Stage A/B
percentiles persisted):
- **Endgames** unlocks.
- Openings eval-based metrics reveal (until then they're hidden — see Constraint 6).

### Per-page behavior

| Page | Gate | During first-import hot lane | Incremental import |
|---|---|---|---|
| Import | — | the holding page (state machine, Constraint 2) | n/a |
| Openings | Tier 1 to enter; eval metrics on Tier 2 | held on import page (empty acct) | **stays usable**; eval metrics behind Cpu bar until Tier 2 |
| Overview | Tier 1 | held on import page (empty acct) | **stays usable** |
| Endgames | Tier 2 | locked (processing state, eval X/Y) | **locked** until Tier 2 (incremental too) |

Incremental imports keep Openings/Overview usable throughout (existing data
shifts slightly as games land — acceptable); only Endgames locks, because
partial-eval endgame stats are actively misleading.

### Why this granularity (not one global gate)

The messiness is contained: **Endgames is gated whole-page** (clean, no
per-component work), and **Openings gets one repeating placeholder treatment**
over its eval metrics, not N bespoke loading containers. Letting users explore
already-correct Openings/Overview immediately is a real UX win over a blunt
app-wide block.

### Why locking Endgames is cheap

The percentile/anchor math is NOT the bottleneck — confirmed by reading the
code. `interpolate_cohort_percentile` reads a precomputed in-memory artifact
(`COHORT_PERCENTILE_CDF` in the generated `app/services/global_percentile_cdf.py`),
and Stage A/B only query the *user's own* games (~4 TCs for Stage A; 7 families
× ~4 TCs ≈ 28 user-scoped cells for Stage B). That's **seconds**, even at 40k
games. The entire wait is the Stockfish eval drain at ~13–15 ev/s.

Drain timing (from `logs/import-stress-20k-each-prod-2026-05-27.log`):

| Scenario | Drain time Endgames is locked | Verdict |
|---|---|---|
| Incremental import (few hundred games) | seconds–~1 min | Imperceptible. |
| First import, typical (few hundred–2k) | seconds–~2 min | Fine. |
| First import, power user (~40k) | ~30–45 min | Rare tail; Openings/Overview already explorable. |

## Locked constraints (must hold in any plan)

1. **Gate on a "percentiles ready" signal, not the raw eval-coverage poll.**
   Stage B fires via `asyncio.create_task` when the drain hits zero pending
   (`eval_drain.py`). If the frontend reveals/unlocks the instant
   `/imports/eval-coverage` reads 100%, it can land *before* Stage B rows are
   committed → chips suppress or flicker. Need a single authoritative readiness
   endpoint exposing **both tiers**: Tier 1 = no active import; Tier 2 = Tier 1
   AND `pending_count == 0` AND Stage A/B rows persisted. Do NOT reuse
   `useEvalCoverage`'s 100% transition as the Tier-2 trigger.

2. **The gated import page must be informative, not a blank spinner** —
   especially for the long-tail power user. Drive it as a **state machine off
   the readiness endpoint**: fetching → importing → (Tier 1: "explore openings"
   CTA) → analyzing endgames (X / Y) → ready. Use the live eval counter that
   already exists.

3. **"Import complete" must mean what's-actually-ready, not hot-import-complete.**
   Today the import page shows a completion message at `status=completed` (hot
   import done) — *before* the eval drain + percentiles. Messaging must not
   over-claim: at Tier 1 say "games imported — openings ready; endgame analysis
   in progress (X/Y)"; the full "imported and analyzed" message waits for Tier 2.

4. **Unlock should be user-initiated / reactive, not a forced reload.** No
   forced `window.location.reload()`; retire the `useEvalCoverage` auto-reload.
   Two CTAs, two different mechanisms (the app uses **sonner** for toasts):
   - **Tier 1 — "Explore Openings": in-page CTA on the import page.** Only
     relevant on a first import (user is held there); on incremental, Openings
     is never gated so no CTA is needed. Not a toast — the user is already
     looking at the import page.
   - **Tier 2 — "Explore Endgames": a sonner action toast.** When percentiles
     finish, the user has almost certainly left the import page (browsing
     Openings, or elsewhere on incremental), so an in-page CTA can't reach them.
     Fire `toast(..., { action: { label: "Explore Endgames", onClick: nav } })`;
     clicking does client-side nav + query invalidation (no reload). Guards:
     fire **once** (dedupe like the existing `evalCompletionReloadFired` flag),
     and **suppress if the user is already on `/endgames`** (it reveals
     reactively there).
   - Beyond the CTAs, Tier-2 reveals (Endgames unlock, Openings eval metrics
     appearing) also happen **reactively** via the readiness poll + query
     invalidation, so a user already on the page sees data appear without acting
     on the toast.

5. **Preserve the Stockfish progress bar on ALL pages.** While the drain runs,
   the eval-coverage progress header (`EvalCoverageHeader` style) stays visible
   on every page — it's the global "still processing" signal. This is NOT
   collapsed to the import page.

6. **Openings eval metrics hide behind a pulsating-Cpu placeholder bar.** Each
   one-row eval-based metric on the Openings subtabs (label + value + tooltip +
   bullet chart) is, until Tier 2, replaced by a placeholder **bar with a
   pulsating Cpu icon, styled to match the Stockfish progress header bar**. One
   repeating treatment, not bespoke per-metric loaders. The rest of each subtab
   stays usable.

7. **Remove the live eval counter from the eval-metric tooltips.** The running
   counter inside `EvalConfidenceTooltip` (and any per-metric tooltip counter)
   goes away — the global progress bar (Constraint 5) and the Cpu placeholder
   (Constraint 6) now carry the in-progress signal. The bar/placeholder, not the
   tooltip, communicates progress.

## Rejected

- **Single global app-wide gate** — over-blocks already-correct Openings/Overview
  for the whole drain; worse UX. Superseded by the tiered model above.
- **N bespoke per-metric loading containers on Openings** — fragile; use one
  repeating Cpu-placeholder treatment (Constraint 6).
- **"Explore with partial data" escape hatch for Endgames** — reintroduces the
  partial-data problem the lock exists to remove. Skip.
- **Forced auto-reload on ready** — jarring and eats the completion message;
  reactive reveal + user-initiated CTA instead (Constraint 4).
