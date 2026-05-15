---
title: Endgame Type card chart inventory — keep all 5 signals
date: 2026-05-15
context: /gsd-explore session after Phase 87.1 shipped the per-class Score Gap bullet, raising the question of whether the card carries too many signals (5 charts: Conv + Recov gauges, Score Gap bullet, WDL bar, Endgame Score bullet)
---

# Endgame Type card chart inventory — keep all 5 signals

## Decision

Keep all five chart elements on `EndgameTypeCard.tsx`:

1. Conv | Recov gauges (top row)
2. Score Gap bullet (Phase 87.1, between gauges and WDL)
3. WDL bar (`SHOW_WDL_BAR_IN_TYPE_CARDS = true`)
4. Endgame Score bullet (sig-gated against 50%)

Do **not** drop the WDL bar. Do **not** drop the Endgame Score bullet.

## Reasoning

Drove the decision off §3.4.3 of `reports/benchmarks-latest.md` (2026-05-15 snapshot), an agreement / redundancy analysis between per-user `user_class_score` (§3.4.1, ≥10 games) and `user_class_mean_gap` (§3.4.2, ≥20 spans), inner-joined on `(user_id, rating_bucket, tc_bucket, endgame_class)`. Zones were IQR-derived from the cohort itself (red = below p25, green = above p75), neutralizing the placeholder-band sensitivity in `endgame_zones.py` / `scoreBulletConfig.ts`.

Key numbers (pooled across 5 visible classes, n = 5,720):

- Pearson r = 0.48 — only 25% of the way from independence to collinearity
- Strict zone-agreement = 53.1% — only 25% of the way from the 37.5% independence baseline to 100% collinearity
- Strong (red ↔ green) disagreement = 3.8% — well below the 12.5% independence baseline
- ~20% confidence-disagreement — one bullet outside its IQR while the other stays inside (the position-difficulty adjustment doing its work)

Queen is the strongest single case for keeping Score Gap distinct: r = 0.23, score_IQR = 19.9pp vs gap_IQR = 9.2pp. Queen-endgame outcomes are dominated by *which positions you got into* (lottery factor); Score Gap strips that out almost cleanly.

Score and Score Gap are **not** redundant. Closer to independent than collinear, almost never contradicting in direction but routinely differing in magnitude — exactly the complementary-information case the rubric's "keep all three" verdict was written for.

## What the analysis didn't rule out

§3.4.3 doesn't directly compare WDL to anything — WDL isn't a per-user scalar, it's the visualization of the raw outcome that Score is computed from (Score = W + 0.5·D / N is the WDL bar in scalar form, plus Wilson CI). Informationally WDL is redundant with the Score bullet.

WDL's slot was kept on its **visual** role: pre-attentive red/gray/green color band, glance-distance legible, prior mobile UAT (Phase 87 D-04) ratified it. Not on its statistical role.

If a future UAT pass flags the 5-chart card as too dense, the WDL drop is the natural lever — see seed if planted, or revisit with §3.4.3 as the starting point. Do not re-litigate the Score vs Score Gap question without fresh data; that one is settled.

## References

- `reports/benchmarks-latest.md` §3.4.3 (Endgame Type Score vs Score Gap — agreement / redundancy analysis)
- `frontend/src/components/charts/EndgameTypeCard.tsx`
- `frontend/src/lib/endgameMetrics.ts` — `SHOW_WDL_BAR_IN_TYPE_CARDS`
- `.claude/skills/benchmarks/SKILL.md` §3.4.3 (methodology)
- Phase 87 D-04 (prior decision to keep WDL bar)
- Phase 87.1 SEED-016 (Score Gap addition)
