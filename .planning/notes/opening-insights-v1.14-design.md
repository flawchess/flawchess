---
title: Opening Insights v1.14 — design decisions (score metric, effect-size gate, confidence annotation)
date: 2026-04-28
context: Captured during `/gsd-explore` to crystallize the design before planning v1.14 phases. Folds in SEED-007 (Option A only) and SEED-008.
related_files:
  - app/services/opening_insights_constants.py
  - app/services/opening_insights_service.py
  - app/repositories/openings_repository.py
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/lib/openingInsights.ts
  - frontend/src/lib/arrowColor.ts
related_notes:
  - opening-insights-statistical-framing.md
related_seeds: [SEED-007, SEED-008]
---

# Opening Insights v1.14 — design decisions

Pre-planning design lock-in for the v1.14 milestone. Captures what we decided and, more importantly, what we **rejected** so the planner doesn't re-litigate it.

## The model we landed on

Three changes, one consistent framing across all surfaces (arrow color, move-list row tint, insight cards):

1. **Metric: chess score** = `(W + 0.5·D) / N`. Replaces loss rate (and win rate on the strength side) everywhere a threshold or color is computed. Score is draw-rate-robust and matches what chess actually uses.

2. **Pivot: 0.50** (absolute, not user-baseline). Rationale below.

3. **Effect-size gate, confidence annotation.** Two separate things:
   - **Effect size** decides what shows up. `|score − 0.50| ≥ effect_threshold`. e.g. minor weakness/strength = 0.05, major = 0.10. Roughly today's loss-rate thresholds re-expressed in score terms, so no recalibration shock.
   - **Confidence** (low / medium / high) is an *annotation* on what survives the gate. Derived from p-value or Wilson 95% half-width. Surfaced as a badge on insight cards and (extended from the existing `(low)`) on moves-list rows. Discovery framing: a 0.55 finding at n=20 is interesting even with low confidence; a 0.51 finding at n=1000 is not interesting even with high confidence.

This inverts the standard statistical workflow (pre-register α, threshold on p, interpret effect size). For a discovery UI it's the right inversion — the user's question is "is this worth my attention" not "is this statistically significant."

## What we rejected, and why

### Rejected: user-baseline shrinkage (Option B from SEED-007)

Initial idea: compute the user's overall score under the active filter and pivot the threshold there (so a 35%-baseline user's 40% line is a strength; a 60%-baseline user's 50% line is a weakness).

**Killed because:** Lichess and chess.com matchmaking already centers users near 50% score. Users whose baseline drifts off 50% (Hikaru-style smurfing, lower-rated-only sessions, new accounts) have the **opponent-strength filter** to compensate. User-baseline shrinkage would re-do work the platform and the filter UI already do, *and* it would introduce "different colors for the same position depending on who's looking" — breaking the at-a-glance reading of the move explorer arrows.

So SEED-007 collapses to **Option A only** (Wilson on score with 0.50 pivot).

### Rejected: showing raw p-values on cards

Considered exposing p-values directly. Killed because most users won't interpret them and they clutter the UI. The low/medium/high badge is the user-facing surface; the Wilson math underneath is what *derives* the badge.

### Rejected: confidence cue on board arrows

Considered desaturating low-confidence arrows or dashing their stroke. Decided against:

- **Arrows show effect size only.** Color intensity = how far from 0.50.
- **Confidence lives on insight cards and moves-list rows**, where there's already text to attach a badge to.

Rationale: the board is the at-a-glance summary; the moves-list and insight cards are the calibration surfaces. Adding a second visual dimension (opacity, dashing) to arrows would compete with the WDL bar's own information density.

## Consequences for surfaces

| Surface | What changes |
|---------|--------------|
| Move Explorer arrows (`arrowColor.ts`) | Color computed from score (not loss rate). Threshold pivot at 0.50. No confidence cue — effect size only. Arrows still drawn at min-games floor. |
| Move Explorer moves-list rows | Background tint computed from score. The existing `(low)` indicator at games < 10 extends to a low/medium/high system, consistent with insight cards. |
| Opening Insights cards | Severity label softened per SEED-008 ("Worth a closer look", "Played confidently") with a `(low)` / `(medium)` / `(high)` confidence badge. Underlying numbers (`L/N`, `n_games`) stay visible. |
| Backend (`opening_insights_service.py`, `openings_repository.py`) | Replace `loss_rate` with score; classify on score against 0.50 with effect-size thresholds; compute Wilson 95% half-width and bucket to low/medium/high; expose `confidence` field on the API response. |
| MIN_GAMES floor | Drop from 20 → 10, matching the existing moves-list `(low)` cue. The badge handles the discovery-vs-noise tradeoff. |

## Why this works under future LLM narration

The original concern in SEED-007 was that adding LLM narration over opening findings would amplify the over-claim — "Major Weakness in the Caro-Kann" becomes a paragraph of confident prose. With v1.14:

- Effect-size gate keeps trivial findings (0.51 at n=1000) out of the LLM's input entirely.
- Confidence annotation is structured data the LLM can quote ("you score below baseline in this line, though the sample is small at n=18"), not a binary verdict it has to either parrot or hedge.
- Softened labels (SEED-008) mean the LLM has calibrated copy to mirror.

So future LLM narration can land on top of v1.14 without re-doing the threshold or framing work.

## Out of scope for v1.14

- **LLM narration over opening findings.** Stays a future seed. v1.14 lands the data plumbing and the calibrated UI; LLM is a deliberate next step.
- **Changing the dedupe rules** (`_dedupe_continuations`, `_dedupe_within_section`). Working as intended.
- **Population-relative thresholds.** Argued against in SEED-005 and v1.13 — book-move equality means self-referential is sufficient.
- **Engine-eval-based weakness detection.** Out of scope for the same reasons as v1.13.
