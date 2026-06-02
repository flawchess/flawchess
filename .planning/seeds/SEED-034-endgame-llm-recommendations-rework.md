---
id: SEED-034
status: open
planted: 2026-06-01
planted_during: /gsd-explore session opening v1.23 (Endgame LLM Statistical-Reasoning Rework, Phase 102). User flagged that the **Recommendations** part of the endgame LLM report also needs a rework, but explicitly said "don't plan that yet" — capture only.
trigger_when: After v1.23 Phase 102 (statistical-reasoning rework) ships and its UAT settles. The recommendations rework should build on the percentile-aware, time-pressure-aware payload Phase 102 establishes, not race ahead of it. Promote via /gsd-review-backlog when the v1.23 statistical-reasoning work is stable.
scope: phase (TBD) — LLM-only; reworks the `recommendations` field of the endgame insights report (the 2-4 actionable bullets), not the page. Likely shares the Phase 102 payload + prompt-version machinery.
depends_on: v1.23 Phase 102 (statistical-reasoning rework). Recommendations should consume the same percentile / zone-gated signals Phase 102 wires in.
---

# SEED-034: Endgame LLM Recommendations rework

## The ask

The endgame LLM report has a `recommendations` field — 2-4 actionable bullets, currently
"grounded in weak/typical-zone metrics only" per the system prompt output contract
(`app/prompts/endgame_insights.md`). The user wants this section reworked as a follow-up to the
v1.23 statistical-reasoning phase, but deliberately **deferred planning** until Phase 102 lands.

## Why deferred, not folded into Phase 102

Phase 102 reworks *how the model reasons over stats* (percentile annotations, time-pressure
narration, prompt-vocab audit, zone-as-gate preserved). The recommendations rework is a distinct
concern — *what advice the model gives and how actionable it is* — and would balloon Phase 102's
already UAT-heavy scope. Keeping it separate also lets the recommendations build on the
percentile-aware payload Phase 102 establishes rather than co-designing two moving targets.

## What to figure out when this is promoted (NOT now)

- What's wrong with the current recommendations? (Too generic? Not tied to the strongest signals?
  Repetitive across users? Not actionable enough? — gather concrete UAT examples first.)
- Should recommendations key off percentile extremes, zone weakness, time-pressure findings, or a
  ranked combination?
- Preserve the `feedback_llm_significance_signal` gate: recommendations should still be driven by
  the zone signal, not raw significance.
- Does this need its own prompt version bump, or can it ride the Phase 102 `endgame_v36` bump?

## Cross-references

- Phase 102 scope: `.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md`.
- Output contract for `recommendations`: `app/prompts/endgame_insights.md`.
- Memory: `feedback_llm_prompt_design`, `feedback_llm_significance_signal`.
