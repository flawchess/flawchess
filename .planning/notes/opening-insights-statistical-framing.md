---
title: Opening Insights — statistical framing of the weakness/strength thresholds
date: 2026-04-28
context: Captured during `/gsd-explore` after Adrian noticed the n=20 / 60% rule has a 25% false-positive rate against a fair-coin null
related_files:
  - app/services/opening_insights_constants.py
  - app/services/opening_insights_service.py
  - app/repositories/openings_repository.py
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/lib/openingInsights.ts
related_seeds: [SEED-005, SEED-007, SEED-008]
---

# Opening Insights — statistical framing

Reasoning we worked through about whether the current thresholds are statistically defensible. Captured so we don't re-derive it next time the topic surfaces.

## Current rule (Phase 70/71, v1.13)

`opening_insights_constants.py` + `opening_insights_service.py:62-78`:

- `MIN_GAMES_PER_CANDIDATE = 20`
- Entry plies 3..16
- `loss_rate > 0.55` → minor weakness (`loss_rate = L / N`, draws excluded from numerator)
- `loss_rate >= 0.60` → major weakness
- Symmetric thresholds for strengths on `win_rate`
- Per-line dedupe via `_dedupe_within_section` and `_dedupe_continuations`
- Caps: 10 weaknesses + 10 strengths per color section
- No LLM narration over opening findings (unlike endgames) — labels go straight to UI

## The math

**Per-test false-positive rate**, treating each surviving (entry_hash, candidate_san) tuple as one binomial test against the null `p_loss = 0.5` and ignoring draws:

| n games | P(loss_rate ≥ 0.60) | P(loss_rate ≥ 0.55) |
|--------:|--------------------:|--------------------:|
| 10 | 37.7% | 37.7% |
| 20 | 25.2% | 41.2% |
| 30 | 18.1% | 36.2% |
| 50 | 10.1% | 26.4% |
| 100 | 2.8% | 13.6% |
| 200 | 0.3% | 4.4% |

So at the n=20 floor, a quarter of "major weakness" flags and ~2 in 5 "minor weakness" flags from a perfectly average player are noise. Reaches the conventional p<0.05 line only around n≈65 for the 60% threshold and never for the 55% threshold below 200 games.

## Why the math is *worse* than a single test in three ways

1. **The null isn't 50%.** Lichess and chess.com matchmaking targets ~50% *score* (`(W + 0.5D) / N`), not 50% loss rate. A user's actual baseline `p_loss` ranges 30-45% depending on draw rate and rating volatility. Comparing per-opening loss rate to a fixed 60% absolute threshold means stronger players (low overall loss rate) almost never get flagged, while weaker players get half their openings flagged just for matching their personal mean. The "weakness" label collapses into "you lose a lot in general."

2. **Loss rate ignores draws asymmetrically.** Score = `(W + 0.5D) / N` is the metric chess actually uses. Loss rate alone makes the threshold drift with the user's draw rate: a high-draw player (1800+ rapid) almost never hits 60% losses even when their score is genuinely below average; a low-draw player (sub-1500 blitz) hits it easily. Score-based thresholds would be skill-comparable.

3. **Multiple comparisons.** Every `(entry_hash, candidate_san)` transition with N≥20 across plies 3-16 is independently tested against the same threshold. A user with thousands of games can have hundreds of surviving tuples pre-dedupe. *However:* Adrian flagged that the line-dedupe steps (`_dedupe_within_section` keeping deepest matching opening; `_dedupe_continuations` collapsing chains where deeper findings are downstream of a kept shallower one) reduce the effective independent test count to roughly the number of distinct opening lines played ≥20 times — typically 5-30 per user, not hundreds. So multi-comparisons is real but bounded; per-line noise dominates.

## Why the math is *not as bad* as it looks

- Line-dedupe drops the effective test count by 1-2 orders of magnitude, as above.
- "60% losses" is an attention-grabbing absolute, not a clinical claim. The product positioning is "candidate hint, look here" rather than "diagnosed weakness."
- The Move Explorer (the deep-link target) shows the user the underlying WDL bar, sample size, and candidate moves directly — so the user can sanity-check the flagged line. The insight surface is a navigation aid, not a verdict.

## Implications for fixes

Three rough tiers, in order of effort. **None are committed; this is just the menu.**

- **Cheap (UI-only).** Reframe the surface from diagnosis to hint: rename "Weakness/Strength" to wording like "Worth a closer look / Played confidently"; soften "Major / Minor" or hide the binary; show `(n=22)` near the n=20 floor so users see the sample size at a glance. No math change. This is what Adrian leaned toward in the explore conversation. The surface stops over-claiming; the math underneath stays as is. Captured in **SEED-008**.

- **Medium (statistical).** Threshold on Wilson 95% lower bound of *score* (not loss rate). Equivalent to "we are 95% confident your true score in this line is below X." Filters out nearly all small-sample noise without raising `MIN_GAMES`. Requires reworking `_classify_row` and the SQL HAVING clause + arrowColor.ts mirror.

- **Principled (Bayesian).** Empirical-Bayes shrinkage of per-line score against the user's overall score baseline. Each line's score gets pulled toward the user's overall, with the pull weakening as N grows. Threshold on *excess* below baseline, with BH-FDR correction across the (already deduped) tested transitions. Most defensible if we ever want to add LLM narration over opening findings — the LLM would otherwise quote "major weakness" verbatim and amplify the over-claim.

## Critical interaction with future LLM narration

If/when opening insights gain an LLM narrative pass (parallel to the endgame `insights_llm.py` prompt), the over-claim problem goes from "label on a card" to "paragraph of prose." At that point the cheap UI-reframe (SEED-008) is no longer sufficient on its own — the medium or principled tier (SEED-007) becomes load-bearing. SEED-008 should fire before SEED-007 regardless: softening the labels first means the threshold rework lands under copy that's already calibrated.
