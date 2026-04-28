# Phase 75 Discussion Log

**Date:** 2026-04-28
**Mode:** discuss (default), advisor mode off

This log captures the question-by-question flow of `/gsd-discuss-phase 75`. Human-readable only; downstream agents consume `75-CONTEXT.md`, not this file.

## Pre-discussion

- Phase 75 is not parsed by `gsd-sdk roadmap.get-phase` because it lives under a `### 🚧 v1.14 ...` milestone heading rather than the backlog `### Phase X.X:` pattern. Phase data was sourced from `.planning/milestones/v1.14-ROADMAP.md` directly. **Action item for tooling:** the SDK's roadmap parser doesn't index active-milestone bullet entries; Phase 70 / 71 / 71.1 had the same issue when they were active. Not a Phase 75 blocker, but worth fixing in the SDK.
- SPEC.md not present (this is a discuss-only flow). Design lock-in lives in `.planning/notes/opening-insights-v1.14-design.md` and REQUIREMENTS.md INSIGHT-SCORE-01..07.

## Area selection

**Question:** Which areas do you want to discuss for Phase 75?

**Options presented (multiSelect):**

- ☑ Confidence bucket rule
- ☐ API backward-compat for loss_rate/win_rate
- ☑ Wilson computation — SQL vs Python
- ☑ Constants + CI consistency-test scope

**User selected:** Confidence bucket rule, Wilson computation, Constants + CI consistency-test scope.

**Skipped → default locked:** API backward-compat — drop `loss_rate` / `win_rate` cleanly. The only consumer ships in the same milestone (Phase 76); a deprecation window adds dead weight to the contract. See CONTEXT.md D-09.

## Area 1 — Confidence bucket rule

**Initial framing:** Two proposals were live — (a) direction-based (REQUIREMENTS INSIGHT-SCORE-04 default), (b) half-width-based (milestone roadmap alt). Asked the user to pick.

**User pushed back.** Their instinct was half-width-based with `≤0.10 → high`, `≤0.20 → medium`, else `low`, but they questioned whether **Wilson** was the right CI for chess scores. Pointed out that:

1. Chess outcomes are trinomial (W/D/L), not binomial.
2. Two standard chess-stat treatments exist:
   - **Half-point binomial** — treat each game as 2 half-point Bernoulli trials, apply binomial / Wilson to `(2W + D)` successes out of `2N` trials.
   - **Trinomial Wald** — use the actual per-game variance: `Var(X) = (W + 0.25·D)/N − score²`. Standard for chess match statistics (BayesElo, Ordo).
3. Provided a concrete p-value table (10/20/50/100 games at score 0.6) showing significance kicks in around n=50.

**My response:** Acknowledged the pushback. Naive Wilson on `(W + 0.5·D)/N` assumes per-game variance `score · (1 − score)`, which over-states uncertainty when draws are common. Trinomial Wald is the correct chess-stats variance formula. Sanity-checked the user's significance numbers against trinomial Wald with typical 30% draw rate at score 0.6:

| n | half-width (trinomial Wald) | bucket |
|---|---|---|
| 10 | 0.272 | low |
| 20 | 0.193 | medium |
| 50 | 0.122 | medium (borderline high) |
| 100 | 0.086 | high |

This matches the user's "significance kicks in around n=50" intuition almost exactly. Offered three options: trinomial Wald (recommended), half-point binomial Wilson, naive Wilson on score.

**Question:** Which CI formula should Phase 75 use for the half-width buckets?

**Options presented:**

- ☑ Trinomial Wald (Recommended)
- ☐ Half-point binomial Wilson
- ☐ Naive Wilson on score

**User selected:** Trinomial Wald.

**Locked decisions (Area 1):**

- Trinomial Wald 95% CI: `half_width = 1.96 · sqrt(((W + 0.25·D)/N − score²)/N)`
- Two-sided p-value via standard normal: `p = math.erfc(|z|/sqrt(2))` where `z = (score − 0.50)/SE`. Pure Python `math` only.
- Bucket boundaries: `≤0.10 → high`, `≤0.20 → medium`, else `low`.
- Amend INSIGHT-SCORE-04 in REQUIREMENTS.md: replace "Wilson 95% confidence interval" with "trinomial Wald 95% confidence interval"; bucket rule moves from direction-based to half-width-based.

## Area 2 — Computation location

**Framing:** Three sub-locations in play: (a) HAVING gate (must be SQL — pre-aggregation filter), (b) score calculation (already Python in `_classify_row`), (c) trinomial Wald half-width + bucket. Asked specifically about (c).

**Trade-offs presented:**

- **SQL CTE inline** — single round-trip; classifier reads precomputed `half_width` column. SQL gets messy (score² expansion in plain SQL). Bucket constants split between SQL and Python.
- **Python post-aggregation (recommended)** — pure helper, trivially testable, all policy in `opening_insights_constants.py`. Negligible perf cost (tens of surviving rows).
- **Hybrid** — half-width in SQL, bucketing in Python.

**Question:** Where should the trinomial Wald half-width and bucketing run?

**Options presented:**

- ☑ Python post-aggregation (Recommended)
- ☐ SQL CTE inline
- ☐ Hybrid — half-width in SQL, bucketing in Python

**User selected:** Python post-aggregation.

**Locked decisions (Area 2):**

- Trinomial Wald + bucket assignment: pure helper in `opening_insights_service.py` (post-aggregation in `compute_insights`).
- HAVING in SQL stays scoped to the effect-size gate: `n_games >= 10 AND ((wins + 0.5*draws)/n_games <= 0.45 OR >= 0.55)`.
- Confidence bucket constants live in `opening_insights_constants.py` next to effect-size constants.

## Area 3 — Constants + CI consistency-test scope

**Framing:** Two sub-decisions — (a) constants naming/values, (b) Phase 75 → 76 ordering for the CI test.

**Constants proposed (no separate question, taken as recommended default):**

```python
OPENING_INSIGHTS_SCORE_PIVOT = 0.50
OPENING_INSIGHTS_MINOR_EFFECT = 0.05
OPENING_INSIGHTS_MAJOR_EFFECT = 0.10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH = 0.10
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH = 0.20
OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE = 10  # was 20
# kept: MIN_ENTRY_PLY = 3, MAX_ENTRY_PLY = 16
```

**Question 1 of 2:** How should Phase 75 handle the CI consistency test given the Phase 75 → 76 ordering?

**Options:**

- ☑ Option (b) — add JS constants now (Recommended)
- ☐ Option (a) — `pytest.mark.skipif` until Phase 76
- ☐ Option (c) — shared JSON fixture

**User selected:** Option (b). Phase 75 adds `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` to `arrowColor.ts` as pure-additive named exports (no function-body changes). CI test passes from day one. Phase 76 rewrites `getArrowColor()` to consume them.

**Question 2 of 2:** Should the CI test also assert confidence bucket boundaries (0.10 / 0.20 half-width) match between Python and TS?

**Options:**

- ☑ No — effect-size only (Recommended)
- ☐ Yes — add confidence bucket constants now

**User selected:** No, effect-size only — but with an addition: **include the p-value in the API response** so the frontend can show it in a tooltip when hovering over the confidence indicator.

**Locked decisions (Area 3):**

- Constants laid out as above (D-10).
- `_classify_row` rewritten to operate on score with strict `≤` / `≥` boundaries (D-11).
- `arrowColor.ts` gains pure-additive `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` exports in Phase 75; function body untouched (D-12).
- CI consistency test asserts SCORE_PIVOT / MINOR_EFFECT / MAJOR_EFFECT / MIN_GAMES lock-step (D-13). Confidence buckets NOT in CI test.
- API contract gains both `confidence: low|medium|high` AND `p_value: float` (D-09). The p-value is for tooltip use; the bucket is the user-facing categorical surface.
- Amend INSIGHT-SCORE-06 in REQUIREMENTS.md: include `p_value: float` alongside `confidence`.

## Wrap-up

Three areas explored, two REQUIREMENTS.md amendments queued (INSIGHT-SCORE-04, INSIGHT-SCORE-06), backward-compat default locked. Ready for `/gsd-plan-phase 75`.

## Tooling notes

- `gsd-sdk query init.phase-op 75` and `gsd-sdk query roadmap.get-phase 75` both returned `phase_found: false` because the SDK's roadmap parser only matches the backlog `### Phase X.X:` heading pattern, not the active-milestone `- [ ] Phase N: ...` bullet under `### 🚧 v1.X` headings. Worked around by reading `.planning/milestones/v1.14-ROADMAP.md` directly. Not a blocker for this phase.
