---
title: Endgame ELO rebuild — Performance Rating direct from endgame / non-endgame scores (drop K)
date: 2026-05-17
context: Captured during `/gsd-explore` reviewing the just-shipped Phase 87.5. The additive `endgame_elo = actual_elo + K · eg_score_gap` mapping is well-behaved but contains a free constant K = 450 calibrated by eyeball against §3.1.6 percentiles (`reports/benchmarks-latest.md`). The FIDE Performance Rating formula derives Endgame ELO and Non-Endgame ELO directly from the per-side scores against the per-side average opponent rating — no free constant, no calibration, mathematically defensible. By Adrian's intuition (confirmed below) actual_elo ≈ midpoint(PR_E, PR_N), so the "lifts up / holds back" semantics are preserved by construction while K is deleted wholesale.
supersedes:
  - .planning/todos/pending/calibrate-endgame-elo-k.md
related_files:
  - app/services/endgame_service.py
  - app/repositories/endgame_repository.py
  - app/schemas/endgames.py
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
  - frontend/src/types/endgames.ts
  - reports/benchmarks-latest.md
related_phases: [57, 87.4, 87.5, 87.6]
---

# Endgame ELO rebuild — Performance Rating direct, drop K

## The motivating finding

Phase 87.5 (shipped 2026-05-17) parameterizes Endgame ELO with a free constant:

```python
# app/services/endgame_service.py:1305
K: float = 450.0
endgame_elo = round(actual_elo + K · eg_score_gap)
```

The comment block above the constant (lines 1283–1304) is candid that K was eyeballed against the §3.1.6 benchmark Lichess percentile table so that p25/p75 lands in a "targeted 30–60 ELO band" and p05/p95 near ±100 ELO. No loss function, no regression, no derivation. A `calibrate-endgame-elo-k.md` todo exists but its procedure is itself an eyeball.

Adrian's question: can Endgame Score derive Endgame ELO **directly**, without K?

Yes. The FIDE **Performance Rating** formula does exactly this:

```
PR = R_opp_avg + 400 · log10(s / (1 − s))
```

Applied to endgame games alone (and to non-endgame games alone), it produces an **Endgame ELO** and a **Non-Endgame ELO** with no free parameters. The `400` is fixed by Elo's logistic-skill assumption (the same `400` in the Elo expected-score formula `E = 1 / (1 + 10^((R_opp − R_user) / 400))`) — it is not a calibration knob.

## Why the multiplicative form was retired before, and why it's right *now*

Phase 87.5's docstring (`_endgame_elo_from_score_gap`, lines 1323–1328) explicitly notes the multiplicative `400·log10(s/(1-s))` mapping was retired. The cited reason was strong-player bias: with Conv ΔES as input, ELO Cohen's d = 1.62, and the mapping produced 200–500 ELO gaps for strong players regardless of how they played.

**That argument killed the input, not the mapping.** Switching the input to within-player score (or score gap) eliminates the bias by construction — the §3.1.6 score-gap metric has ELO d = 0.17, essentially flat across rating buckets. Applying the multiplicative form to per-side **scores** (PR_E from endgame games, PR_N from non-endgame games, each against its own opponent pool) inherits that flatness because the bias cancels in either subset on its own.

## The midpoint property (confirms "lifts/holds" semantics survive)

Worked example, realistic case, equal opponent pool R_opp:

| Quantity | Value |
|---|---|
| Endgame score s_E | 0.55 |
| Non-endgame score s_N | 0.45 |
| Actual score s_all | 0.50 |
| PR_E = R_opp + 400·log10(0.55/0.45) | R_opp + 34.8 |
| PR_N = R_opp + 400·log10(0.45/0.55) | R_opp − 34.8 |
| midpoint(PR_E, PR_N) | **R_opp** |
| PR_all (s=0.50) | **R_opp** |

The midpoint equals actual PR exactly in the symmetric case, and approximately whenever `s_E` and `s_N` straddle 0.5 with similar opponent pools. The logit is nearly linear near s=0.5; nonlinearity only bites at extremes (e.g. s_E=0.95, s_N=0.55 → midpoint 273 vs PR_all 191, an 82-ELO discrepancy). The §3.1.6 score-gap percentiles all sit well inside the linear neighborhood (|gap| < 0.23 even at p05/p95), so the midpoint property holds tightly across the entire data range.

Practical consequence: **the Actual ELO line is bracketed by Endgame ELO and Non-Endgame ELO by construction**. No anchoring math, no `actual_elo + Δ` rewrite — just compute the two PRs and plot all three lines on the same axis.

## Gap amplification table (UX continuity)

Near s = 0.5, the PR slope is `400 / (ln(10) · 0.25) ≈ 695` per unit score (one-sided: ≈ 348 from midpoint). So at the same underlying score gap, the rendered Endgame–Non-Endgame ELO gap is **~1.5× the K=450 gap** Phase 87.5 displays today:

| Percentile | Score gap | Phase 87.5 (K=450, vs Actual) | Phase 87.6 (PR_E − PR_N) | Phase 87.6 (PR_E − Actual) |
|---|---|---|---|---|
| p05 | −0.227 | −102 ELO | −158 ELO | −79 ELO |
| p25 | −0.104 | −47 ELO | −72 ELO | −36 ELO |
| p50 | −0.014 | −6 ELO | −10 ELO | −5 ELO |
| p75 | +0.073 | +33 ELO | +51 ELO | +25 ELO |
| p95 | +0.202 | +91 ELO | +140 ELO | +70 ELO |

The "30–60 ELO band" Phase 87.5 calibrated K to becomes a "50–75 ELO band" in the new chart (between the Endgame and Non-Endgame lines). Honest framing for the popover: "Today's chart shows Endgame ELO scaled by an arbitrary constant against Actual ELO; the new chart shows Endgame and Non-Endgame Performance Rating directly — same data, no fudge factor, slightly bigger visual gap." This is a feature given the "rigorous and defensible" goal.

## Boundary singularity (and the fix)

`log10(s/(1-s))` is singular at s=0 and s=1. With a trailing 100-game window this is rare but not impossible — a hot/cold streak of 100/100 wins or losses on the endgame side, or a heavy bias for one side reaching endgames. The standard fix is **Laplace smoothing**:

```
s* = (wins + 0.5·draws + 1) / (n + 2)
```

For n=100 this clips PR delta at roughly ±900 ELO either side — well outside realistic territory for any actual user but mathematically bounded. Apply to both PR_E and PR_N independently. No clamping at the output stage — the smoothing at the input stage is sufficient.

## Schema-of-computation change

`query_endgame_performance_rows` (`app/repositories/endgame_repository.py:458`) currently returns 5 columns per row: `played_at, result, user_color, platform, time_control_bucket`. It does NOT carry opponent ratings, which the PR formula requires.

Required additions:
- Add `white_rating, black_rating` to the SELECT (both branches: endgame_stmt + non_endgame_stmt).
- Derive `opp_rating = white_rating if user_color == 'black' else black_rating` in the service-layer accumulator.
- Extend `ScoreGapTimelinePoint` (or introduce a parallel `EndgameEloTimelinePoint`-style row) to carry: `endgame_score`, `non_endgame_score`, `endgame_opp_rating_avg`, `non_endgame_opp_rating_avg`, plus the existing date / window-count fields. With these four values per week, both PR_E and PR_N are computable in the weekly producer.
- Compute PR per side at the weekly emission step. Pure function, deterministic, easy to unit test.

`query_endgame_elo_timeline_rows` already returns `white_rating, black_rating` (it drives the Actual ELO line). That repo function stays as-is — the rebuild is upstream of it, not adjacent.

## Naming policy

Use plain ELO terminology in user-facing surfaces:
- **Endgame ELO** — the PR computed on endgame games only.
- **Non-Endgame ELO** — the PR computed on non-endgame games only.
- **Actual ELO** — the system rating sampled at the window cutoff.

Strictly speaking these are Performance Ratings, not Elo ratings (Elo accumulates; PR is a single-window measurement). The popover body can explain the distinction once — body text stays in plain ELO terms because users won't care about the formal distinction and the "rigorous and defensible" claim rests on the math, not the label.

## LLM payload

Option (b) chosen: keep `eg_score_gap` (and the §3.1.6 zone bounds it references) as the primary signal in the LLM payload, **add** `endgame_elo` / `non_endgame_elo` / `actual_elo` as supplementary fields for narration.

Rationale: the existing `endgame_v33` prompt anchors zone language ("strong / typical / weak") to score-gap percentile bands. Migrating those bands to PR-ELO units would be a separate calibration exercise (regenerate from §3.1.6 with the PR slope) — out of scope for the rebuild. With score gap as primary signal and PR-ELO as display fields, the prompt prose can naturally reference both: "Your Endgame ELO this period sits at 1734, vs 1682 in non-endgame games — your endgame play is lifting your rating by ~50 ELO. This places your endgame strength in the [strong / typical / weak] band for your rating cohort."

The `_PROMPT_VERSION` bumps to `endgame_v34`.

## Visual design — dual lines + signed band

Per-combo chart layout:

- **Actual ELO**: bold central line (combo color, `strokeWidth ≈ 2`).
- **Endgame ELO + Non-Endgame ELO**: fine lines (same combo color, `strokeWidth ≈ 1`). Combo identification stays on color; semantics live in the fill below.
- **Signed band** between Endgame ELO and Non-Endgame ELO: green when Endgame ≥ Non-Endgame, red when Endgame < Non-Endgame. Crossovers handled by a horizontal `<linearGradient>` with two coincident stops at each sign-flip x-position — identical to the algorithm shipped in `EndgameScoreOverTimeChart.tsx:99-165`. Reuse, don't reinvent.

Reusability win: extract the gradient-stops helper out of `EndgameScoreOverTimeChart.tsx` into a shared util (`frontend/src/lib/signedBandGradient.ts` or equivalent), taking `{x, y_low, y_high, sign}[]` and returning `GradientStop[]`. Both charts then call the same helper. Worth doing inside this phase — it costs little and removes a duplication that would otherwise calcify.

Layering (Recharts draws in document order — emit accordingly so Actual ELO renders on top of the band):
1. `<Area>` (y_low = min(PR_E, PR_N), y_high = max(PR_E, PR_N), fill = signed gradient).
2. `<Line>` PR_E (fine, combo color).
3. `<Line>` PR_N (fine, combo color).
4. `<Line>` Actual ELO (bold, combo color).

Up to 8 combos render simultaneously (4 TCs × 2 platforms). Existing `hiddenKeys` legend toggles already let users dim down to 1–3 active combos; same plumbing covers the new dual-line + band overlays. No new crowding strategy needed.

## Rejected alternatives

1. **Anchored form `actual_elo + (PR_E − PR_N)`** (option b from the first exploration round): mathematically nearly identical to plotting PR_E directly, since actual_elo ≈ midpoint. Adds an arithmetic indirection for no semantic gain. Plot PR_E directly.

2. **Two half-bands tinted from Actual ELO** (one semantic color per side, regardless of direction): solves direction-at-a-glance, but conflicts with combo color identification in the fills, and the signed-band-between-the-two-PRs design (reusing the Score Gap chart's algorithm) is simpler and ships faster.

3. **Per-(platform, TC) PR slope**: the `400` in the PR formula is theory-fixed; no per-TC tuning available or desirable. The previous K-knob is gone, not regionalised.

4. **Single combined PR_all line as replacement for Actual ELO**: PR_all on all games combined is interesting but doesn't match the user's rating identity (Actual ELO is what users see on the platforms); replacing it would confuse "what's my rating". Keep Actual ELO as-is, sampled at window cutoff via the existing `query_endgame_elo_timeline_rows` query.

## What this deletes

- `K: float = 450.0` constant (`app/services/endgame_service.py:1305`).
- `_endgame_elo_from_score_gap` rewritten or replaced (the additive K math vanishes; the per-side PR computation replaces it).
- `.planning/todos/pending/calibrate-endgame-elo-k.md` (obsoleted — K is removed, not calibrated). This note supersedes it.
- The "calibrated against §3.1.6 percentile table" comment block above K, replaced with a one-paragraph derivation pointing at this note.
