# Phase 82: Discussion Log

**Discussed:** 2026-05-10
**Mode:** /gsd-discuss-phase 82 (default — single-question turns)

## Areas Discussed

User selected (multiSelect): all four presented gray areas.

### Area 1 — Metric naming for the second tile

**Question 1.1:** How should the new "what you do with it" metric be named?
- Options: New MetricId / Reuse `endgame_score` / Rename existing
- Selected: **Rename existing**
- Rationale captured: clean naming wins despite higher blast radius.

**Question 1.2:** What should the renamed pair be?
- Options: `endgame_score_timeline` + new = `endgame_score` (Recommended) / `eg_score_over_time` / asymmetric (don't rename non_endgame_score)
- Selected: **`endgame_score_timeline` + new = `endgame_score`** (Recommended)
- Locked symmetric rename: `non_endgame_score` → `non_endgame_score_timeline` for parity.

### Area 2 — `verdict` field design on SubsectionFinding

**Question 2.1:** What literal values should `verdict` carry?
- Options: `above_null`/`null`/`below_null` (Recommended) / `sig_positive`/etc / `above`/`inconclusive`/`below`
- Selected: **`above_null`/`null`/`below_null`** (Recommended)
- Note: this answer was superseded by the architectural decision in 2.3 (verdict dropped entirely).

**Question 2.2:** How should the prompt instruct the LLM to combine `zone` with `verdict`?
- User declined to answer; raised an architectural concern instead:
  > "Explicit 3x3 matrix sounds good. but make sure very small effects are not over-emphasized... maybe we should just decrease the neutral zone, and narrate the significant effects in the green/red zones? Maybe the new significance signal is counterproductive?"

**Question 2.3 (reformulated):** Drop the `verdict` field design and use zone-only narration?
- Options: Drop `verdict` (Recommended) / Keep as qualifier / Keep original 3×3 design
- Selected: **Drop `verdict`. Use zone-only + Plan 6 in-phase**
- Major architectural simplification: no new field on `SubsectionFinding`, tile color rule (Plan 6) lands in-phase. LLM narrates by `zone` with the existing `[near edge]` suffix for borderlines. Saved as memory `feedback_llm_significance_signal.md`.
- This decision **collapsed Areas 2 + 4** into a single coherent design.

### Area 3 — Zone bands for the two new registries

**Question 3.1:** Endgame score zone registry shape?
- Options: Per-ELO `ENDGAME_SCORE_ZONES` (Recommended) / Single global pooled `[0.46, 0.56]` / Single global from existing tile constants
- Selected: **Single global from existing tile constants** (live shared `[0.45, 0.55]`)
- Trade-off accepted: simpler, no new registry; loses the ELO ramp the benchmark §0 says matters (max d=0.84). Per-ELO bands deferred (D-11) for a future iteration if pooled-band mis-classification surfaces.

**Question 3.2:** EG-entry eval (Tile 1) band — tighten or keep ±0.75?
- User declined the multi-option ask; clarified directly:
  > "How about we tighten to ±0.50, both for what's displayed and or narration? Ultimately, the IQR is a good baseline for zone boundaries, but if we think smaller effects are relevant, I think we can make a judgement call. And 0.5 pawns ahead or behind (on average!) seems quite a relevant effect to me."
- Locked: **±0.50 for both display and LLM** (single source of truth). Editorial judgment over the cohort IQR. Saved as memory `feedback_zone_band_judgement.md`.
- This **amends Phase 81 D-15** (which set the neutral band at ±0.75 to match the cohort IQR).

### Area 4 — Plan 6 (tile-color rule amendment) scope

- Pre-decided by Area 2's verdict-rejection: tile color rule (`zone × p<0.05`) lands **in-phase**, otherwise tile and LLM disagree on what is narratable. Locked as D-12 / D-13 in CONTEXT.md.

## Deferred Ideas Captured

- Per-ELO `ENDGAME_SCORE_ZONES` mirroring `ENDGAME_SKILL_ZONES` (D-11).
- `verdict`/sig-test field on `SubsectionFinding` (D-06 — rejected for this phase, open only if a future case genuinely requires it).
- Per-TC entry-eval bands.
- Distribution histogram view (carried over from Phase 81 deferred ideas).
- Pre-endgame eval over time chart (carried over from Phase 81 deferred ideas).
- LLM cross-section "composure-under-pressure" flag combining entry_eval × low-time-gap.

## Memories Saved

- `feedback_zone_band_judgement.md` — editorial judgment over IQR; keep tile + LLM aligned.
- `feedback_llm_significance_signal.md` — don't add a parallel sig-test field; tighten the cohort band instead.

## Claude's Discretion (refined during execution)

- Final ordering of `endgame_start_vs_end` paragraphs within the section (entry-eval first per Phase 81 D-17, but the LLM may reorder if cross-section story dictates).
- Plan-shape provisional in CONTEXT.md (4 plans) — refined during /gsd-plan-phase 82.
- Exact glossary copy in `endgame_insights.md` — iterate during execution.
- Prompt subsection block wording — iterate during execution.

## Scope Creep Redirected

None — user stayed entirely within the seed's scope plus structural/architectural questions about how to implement it.

---

*Discussion: 2026-05-10*
