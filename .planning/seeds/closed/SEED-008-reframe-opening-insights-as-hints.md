---
id: SEED-008
status: closed_folded_into_v1_14
planted: 2026-04-28
planted_during: v1.13 Opening Weakness/Strength Insights (shipped)
closed: 2026-04-28
closed_during: v1.14 milestone planning (`/gsd-explore`)
disposition: |
  Folded into v1.14 milestone (Phase 76). Label softening lands together with the score-metric
  migration and the new low/medium/high confidence badges so the math, the labels, and the
  calibration cue all ship under one consistent framing. See notes/opening-insights-v1.14-design.md.
trigger_when: next time `OpeningInsightsBlock.tsx` / `openingInsights.ts` copy is touched, OR a v1.x polish pass on the Insights block, OR before SEED-007 (principled thresholding) is built — whichever fires first
scope: phase
related_files:
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/lib/openingInsights.ts
related_notes:
  - opening-insights-statistical-framing.md
  - opening-insights-v1.14-design.md
related_seeds: [SEED-005, SEED-007]
---

# SEED-008: Reframe Opening Insights from diagnosis to candidate hint

## Why This Matters

The current UI labels Opening Insights findings as **"Major Weakness" / "Minor Weakness" / "Major Strength" / "Minor Strength"** with section titles like "White Opening Weaknesses". The classifier underneath is statistically a low-confidence per-test signal at the `MIN_GAMES = 20` floor — see `notes/opening-insights-statistical-framing.md` for the math (≈25% per-test false-positive rate at n=20 against a fair-coin null, before accounting for the null actually being the user's pool baseline).

The product positioning Adrian articulated during the explore conversation is **"candidate hint, not confident diagnosis"** — but the current copy reads like a verdict. Users coming off the Move Explorer's literal WDL bars see "Major Weakness: Caro-Kann" and reasonably interpret it as a clinical claim, not a "worth a second look" prompt.

This is the cheapest fix on the menu — pure UI / copy work, no math change. It is independent of SEED-007 (the threshold mechanism rework) and can ship before, after, or instead of it.

## When to Surface

**Trigger A:** Any phase that touches `OpeningInsightsBlock.tsx` or `openingInsights.ts` copy. The reframe should be folded into that work rather than left as a dangling polish task.

**Trigger B:** A general v1.x polish pass on the Insights block.

**Trigger C:** Before SEED-007 is implemented. If we move to Wilson lower bound or Bayesian shrinkage *and* keep the current "Major / Minor Weakness" labels, the threshold improvement gets undermined by language that still claims more than the math supports. Reframing first means the math change can be a clean enhancement under copy that's already calibrated.

Until any trigger fires, this stays dormant.

## What to Build

The exact wording is for design/discuss-phase to settle, but the direction is:

- **Section titles:** soften from "White Opening Weaknesses" / "White Opening Strengths" toward "Worth a closer look (White)" / "Played confidently (White)" — or some equivalent that frames each section as a navigation suggestion, not a verdict.
- **Severity labels on cards:** drop or de-emphasize the Major / Minor binary. Either replace with a sample-size cue (`n=22`, `n=58`) or with a confidence cue (high/medium based on Wilson lower-bound width — even without Option A from SEED-007, a simple "small sample" badge for findings near `n=20` would help).
- **Card copy:** any verbs like "you struggle with" or "you dominate" should soften to "this line is worth a second look" / "this line has been a strong area." See `feedback_llm_prompt_design.md` for the tone calibration that already governs endgame insights — the same OK / not-OK examples apply.
- **Optional explainer popover:** a `?` icon on the section title, opening a short note: "Findings are based on patterns in your past games. Sample sizes start at 20; smaller samples are noisier. Use the Move Explorer link on each card to see the underlying win/draw/loss bars."

## Why Now-vs-Later

**If LLM narration over opening findings (parallel to endgame `insights_llm.py`) is on the roadmap**, this seed should fire first. The LLM will quote section titles and severity labels verbatim — softening them at the source means the prose downstream stays calibrated automatically. Hardening "Major Weakness" into a paragraph of LLM prose makes the over-claim much louder than it is on a card.

**If LLM narration is not on the roadmap**, this is still worth doing as a small polish pass — but lower urgency.

## Out of Scope for This Seed

- Changing the threshold mechanism — that's SEED-007.
- Hiding the underlying numbers (`L/N`, `n_games`) from the cards. Those should stay visible; the reframe is about the *labels* surrounding them.
- Renaming the API response fields (`white_weaknesses`, `severity: "major"|"minor"`). Internal naming can stay; this is a presentation-layer reframe only.
