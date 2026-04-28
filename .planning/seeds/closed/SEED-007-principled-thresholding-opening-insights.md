---
id: SEED-007
status: closed_folded_into_v1_14
planted: 2026-04-28
planted_during: v1.13 Opening Weakness/Strength Insights (shipped)
closed: 2026-04-28
closed_during: v1.14 milestone planning (`/gsd-explore`)
disposition: |
  Folded into v1.14 milestone (Phases 75-76). Option A (Wilson on score, 0.50 pivot) is locked in.
  Option B (user-baseline shrinkage) was rejected — Lichess/chess.com matchmaking already centers
  users near 50% score, and the opponent-strength filter handles drift cases. User-baseline would
  break user-agnostic arrow color reads on shared positions. See notes/opening-insights-v1.14-design.md
  for the full reasoning.
trigger_when: opening insights gain LLM narration, OR user feedback flags a meaningful false-positive rate, OR a v1.x polish pass touches opening-insights thresholding
scope: phase
related_files:
  - app/services/opening_insights_constants.py
  - app/services/opening_insights_service.py
  - app/repositories/openings_repository.py
  - frontend/src/lib/arrowColor.ts
related_notes:
  - opening-insights-statistical-framing.md
---

# SEED-007: Principled thresholding for Opening Insights

## Why This Matters

The current opening-insights classifier (Phase 70/71) uses fixed absolute thresholds on raw loss rate — `> 0.55` minor weakness, `>= 0.60` major — applied to every `(entry_hash, candidate_san)` transition with `N >= 20`. The threshold has three known issues, captured in `notes/opening-insights-statistical-framing.md`:

1. At `N = 20` the false-positive rate against a fair-coin null is ~25% for the 60% threshold and ~41% for the 55% threshold.
2. The implicit null (50% loss rate) doesn't match real player baselines (~30-45% loss rate after pool matchmaking centers each user near 50% *score*).
3. Loss rate ignores draws, so the threshold's effective stringency varies with the user's draw rate.

Today this is acceptable because:
- Line-dedupe drops effective test count to 5-30 per user
- The product positioning is "candidate hint, look here" rather than "diagnosed weakness"
- The Move Explorer deep-link lets users sanity-check the underlying data themselves

**The picture changes if we add LLM narration over opening findings.** The endgame side already has `insights_llm.py` generating prose paragraphs. If we extend that to openings, the LLM will quote "major weakness in the Caro-Kann" verbatim — a small-sample noise flag becomes a confidently narrated diagnosis. At that point the cheap UI-reframe (renaming labels, showing `n=22` badges) is no longer enough.

## When to Surface

**Trigger A:** A phase plans to add LLM narration over opening insights (parallel to endgame `insights_llm.py`). Reframing-only is insufficient at that point — the LLM amplifies the labels.

**Trigger B:** User feedback or a benchmark-DB analysis shows a meaningful false-positive rate in flagged opening weaknesses (e.g., users reporting flagged lines that match their overall loss rate; or the research question in `.planning/research/questions.md` returns a high effective-test count).

**Trigger C:** A v1.x polish pass touches opening-insights thresholding for any reason — at that point, this seed should be considered alongside the cheaper UI-reframe captured in the explore conversation.

Until any trigger fires, this stays dormant.

## What to Build

Two candidate approaches, in order of complexity. The phase planner should pick one, not both.

### Option A: Wilson lower bound on score

Replace `loss_rate` with `score = (W + 0.5D) / N`. Replace the fixed cutoffs with the **Wilson 95% lower bound** on score:

- "Worth a closer look" / minor weakness: Wilson lower bound on score < 0.45
- Stronger weakness signal: Wilson lower bound < 0.40

Equivalent to "we are 95% confident your true score in this line is below X." Filters out nearly all small-sample noise without raising `MIN_GAMES`. Symmetric on the strength side via Wilson upper bound > 0.55 / 0.60.

**Implementation footprint:**
- Compute Wilson bounds in `_classify_row` (or as a SQL expression)
- Update the HAVING clause in `query_opening_transitions` (or move classification to Python)
- Mirror in `frontend/src/lib/arrowColor.ts` and the CI-enforced consistency test
- Update labels and any cached findings

### Option B: Empirical-Bayes shrinkage against the user's baseline

More principled, more work. Compute the user's overall score across all games (under the same filter set). Use that as the prior. Shrink each line's observed score toward the prior with weight inversely proportional to N. Threshold on the *posterior excess* below baseline, with Benjamini-Hochberg FDR correction across the (already line-deduped) set of tested transitions.

Most defensible if multiple insight surfaces consume the same findings (LLM, dashboard cards, charts) and we want a single statistical claim that holds up.

**Implementation footprint:**
- Materialize per-user overall score under the active filters (one extra query, or piggy-back on the existing aggregate)
- Posterior computation in `_classify_row` (closed form for Beta-Binomial)
- BH-FDR sort + cutoff after dedupe but before ranking
- Heavier rework of `arrowColor.ts` since the per-position color now depends on the user's baseline (the arrow board today is user-agnostic)

## Out of Scope for This Seed

- Renaming the UI labels from "Weakness / Strength" to softer phrasing — that's SEED-008, an independent and cheaper UI-only path. SEED-008 should fire before this seed regardless of which threshold method is chosen here, so the math change lands under already-calibrated copy.
- Raising `MIN_GAMES` beyond 20 — a brute-force version of Option A but without the per-test confidence improvement.
- Changing the dedupe rules in `_dedupe_continuations` and `_dedupe_within_section`.

## Open Questions for Discuss-Phase

1. Wilson on score or Wilson on loss rate? (Score is more defensible against draw-rate variance; loss rate is what the UI labels emphasize today.)
2. If Option B: do we share the user-baseline computation across the openings tab, the move explorer arrows, and any future LLM prompt? Or per-feature?
3. Does the arrowColor.ts mirror still make sense if classification becomes user-baseline-relative? The board arrows are currently user-agnostic at a given position.
