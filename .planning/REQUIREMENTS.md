# Requirements: FlawChess v1.14 — Score-Based Opening Insights

**Milestone goal:** Migrate Opening Insights and Move Explorer color coding from loss-rate to chess score `(W + 0.5·D)/N`, gate findings on effect size against a 0.50 pivot, and annotate them with low/medium/high confidence badges. Replaces today's "Major/Minor Weakness" framing with a calibrated discovery surface that holds up under future LLM narration.

**Source:** SEED-007 (Option A only — Wilson on score) + SEED-008 (label reframe), folded together so the math, the labels, and the calibration cue ship under one consistent framing. Design decisions captured in `.planning/notes/opening-insights-v1.14-design.md`.

## v1.14 Requirements

### Backend — score metric and confidence annotation (INSIGHT-SCORE)

- [ ] **INSIGHT-SCORE-01**: Replace `loss_rate` / `win_rate` with chess score `score = (W + 0.5·D) / N` as the classification metric in `app/services/opening_insights_service.py` and `app/repositories/openings_repository.py`. Score is the metric returned to the frontend; raw `w / d / l / n_games` remain in the payload as the literal-data display (WDL bars stay).
- [ ] **INSIGHT-SCORE-02**: Threshold pivot stays at **0.50** (no user-baseline shrinkage). Rationale: chess.com / lichess matchmaking centers users near 50% score; the existing opponent-strength filter handles drift cases. Documented in the v1.14 design note.
- [ ] **INSIGHT-SCORE-03**: Effect-size gate on observed score:
  - Minor weakness: `score ≤ 0.45` (effect size ≥ 0.05 below pivot)
  - Major weakness: `score ≤ 0.40` (effect size ≥ 0.10 below pivot)
  - Symmetric on the strength side at `score ≥ 0.55` / `score ≥ 0.60`.
  - Strict `≤` / `≥` boundaries; eliminates the prior `loss_rate > 0.55` asymmetry.
  - Thresholds live in `opening_insights_constants.py` and remain configurable.
- [ ] **INSIGHT-SCORE-04**: Compute a **trinomial Wald 95% confidence interval** on score per (entry_position, candidate_move) pair. The formula uses per-game variance `(W + 0.25·D)/N − score²` (the actual variance under the trinomial result distribution X ∈ {0, 0.5, 1}) rather than the binomial Wilson approximation, which over-states uncertainty when draws are common. Standard formula for chess match statistics (BayesElo, Ordo). Bucket each surviving finding to `confidence: "low" | "medium" | "high"` based on the half-width: `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`. Strict `≤` boundaries. Pure Python `math` only — no scipy dependency. Bucket boundaries live in `opening_insights_constants.py` so they can be retuned against real data without touching service code.
- [ ] **INSIGHT-SCORE-05**: Drop `MIN_GAMES_PER_CANDIDATE` from 20 to 10 to support discovery framing — surfacing low-confidence candidate lines with the `(low)` badge replaces the prior hard-floor approach.
- [ ] **INSIGHT-SCORE-06**: Extend the `OpeningInsightFinding` API contract with two new fields: `confidence: "low" | "medium" | "high"` (the half-width bucket from INSIGHT-SCORE-04) and `p_value: float` (two-sided test of observed score vs the 0.50 pivot, computed via the same Z-statistic that drives the half-width). The existing `severity: "major" | "minor"` field stays, so the frontend can render severity (effect size), confidence (precision), and a tooltip-grade p_value per finding without overloading any one cue. Phase 75 also drops `loss_rate` and `win_rate` cleanly — only consumer is the v1.14 frontend (Phase 76) in this same milestone.
- [ ] **INSIGHT-SCORE-07**: Update the CI consistency test (`tests/services/test_opening_insights_arrow_consistency.py` or successor) to assert score-based threshold lock-step between backend classification and `frontend/src/lib/arrowColor.ts`. Test must catch any divergence between the two surfaces.

### Frontend — score-based coloring, confidence badges, label reframe (INSIGHT-UI)

- [ ] **INSIGHT-UI-01**: Migrate `frontend/src/lib/arrowColor.ts` from loss-rate to score. Color encoding is **effect-size only** — arrows show how far observed score sits from 0.50; no confidence cue (no opacity/dashing). Threshold pivot at 0.50; same effect-size thresholds as backend (`±0.05` minor, `±0.10` major).
- [ ] **INSIGHT-UI-02**: Migrate Move Explorer moves-list row background tint to score (same color encoding as arrows). WDL bars on each row stay unchanged — they remain the literal-data display.
- [ ] **INSIGHT-UI-03**: Extend the existing `(low)` indicator on Move Explorer moves-list rows to a three-level system: `(low)` / `(medium)` / `(high)`. High-confidence rows render unmarked (current default behavior). Confidence levels derived from the same Wilson buckets the backend exposes via INSIGHT-SCORE-04.
- [ ] **INSIGHT-UI-04**: Soften Opening Insights section titles and severity copy per SEED-008 — e.g. "Worth a closer look (White)" / "Played confidently (White)" instead of "White Opening Weaknesses / Strengths". Severity word ("Major" / "Minor") may stay inside the card but reads as a tone cue, not a verdict. Exact copy resolved during Phase 76 `/gsd-discuss-phase`; tone calibration follows `feedback_llm_prompt_design.md`.
- [ ] **INSIGHT-UI-05**: Add a confidence badge `(low)` / `(medium)` / `(high)` to each Opening Insights card (`OpeningFindingCard.tsx`), positioned next to the severity word. Badge consumes the new `confidence` field from the API. Underlying numbers (`L/N`, `n_games`) stay visible.
- [ ] **INSIGHT-UI-06**: Add an explainer popover triggered by a `?` icon on the Opening Insights section title. Popover content covers the score / sample-size / confidence framing in user-friendly language. Reuses existing popover pattern from elsewhere in the app.
- [ ] **INSIGHT-UI-07**: Mobile parity for all Move Explorer + Opening Insights changes (`arrowColor.ts`, moves-list row tint, confidence badges, section title copy, explainer popover). Verified at 375px width per CLAUDE.md frontend rules — no horizontal scroll, ≥ 44px touch targets, all interactive elements have `data-testid`.

## Future Requirements (deferred)

- **LLM narration of opening insights** — was previously deferred behind v1.13. v1.14 lands the calibrated data plumbing (effect size + confidence) that future LLM narration would consume; the LLM layer itself remains a separate future seed.
- **Population-relative weakness signals** — gated on full benchmark ingest (SEED-006). Not part of v1.14 because the design explicitly rejects user/population baselines (see Out of Scope below).

## Out of Scope

- **User-baseline / Bayesian shrinkage thresholds** — explicitly rejected. Lichess and chess.com matchmaking already center users near 50% score; the opponent-strength filter handles users whose baseline drifts. User-baseline would re-do work the platform and the filter UI already do, *and* would break user-agnostic arrow color reads on shared positions. See `.planning/notes/opening-insights-v1.14-design.md` § "What we rejected, and why".
- **Showing raw p-values on cards** — the low/medium/high badge is the user-facing surface; the Wilson math underneath derives the badge but is never exposed.
- **Confidence cue on board arrows (opacity/dashing)** — the board reads at-a-glance via effect-size color only; confidence lives on cards and moves-list rows where text can carry the badge.
- **Dropping the WDL bar from the move explorer** — the bar remains the literal-data display; the score-based color is the *threshold/classification* layer on top of it.
- **Changing the dedupe rules** in `_dedupe_continuations` and `_dedupe_within_section` — working as intended, out of scope.
- **Engine-eval-based weakness detection** — same rationale as v1.13.

## Traceability

| REQ-ID | Phase |
|--------|-------|
| INSIGHT-SCORE-01 | 75 |
| INSIGHT-SCORE-02 | 75 |
| INSIGHT-SCORE-03 | 75 |
| INSIGHT-SCORE-04 | 75 |
| INSIGHT-SCORE-05 | 75 |
| INSIGHT-SCORE-06 | 75 |
| INSIGHT-SCORE-07 | 75 |
| INSIGHT-UI-01 | 76 |
| INSIGHT-UI-02 | 76 |
| INSIGHT-UI-03 | 76 |
| INSIGHT-UI-04 | 76 |
| INSIGHT-UI-05 | 76 |
| INSIGHT-UI-06 | 76 |
| INSIGHT-UI-07 | 76 |

---
*Last updated: 2026-04-28 — milestone v1.14 opened. 14/14 requirements mapped (INSIGHT-SCORE-01..07 → Phase 75; INSIGHT-UI-01..07 → Phase 76). Phase 75 amendments: INSIGHT-SCORE-04 pivots from Wilson to trinomial Wald with half-width-based buckets (D-05); INSIGHT-SCORE-06 extends API contract to include `p_value` alongside `confidence` (D-09).*
