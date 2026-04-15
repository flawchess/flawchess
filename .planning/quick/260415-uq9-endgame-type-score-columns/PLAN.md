---
id: 260415-uq9
slug: endgame-type-score-columns
date: 2026-04-15
---

# Add You/Opp/Diff/Bullet columns to Results by Endgame Type

Extend `EndgameWDLChart.tsx` to add four columns mirroring `EndgameScoreGapSection.tsx`:
- **You vs Opp**: chess score `(wins + draws/2) / total`
- **Opp vs You**: `(losses + draws/2) / total` (= 1 − you)
- **Diff**: color-coded `you − opp` pct with sign
- **You − Opp**: `MiniBulletChart` with ±0.05 neutral zone and ±0.30 domain

Note: for endgame types the same games are shared by both players, so `opp_score = 1 − user_score` by definition. The Diff column is effectively a score-gap view (2·you − 1). Neutral zone ±0.05 keeps semantics consistent with Conversion & Recovery.

## Tasks

1. Refactor `EndgameWDLChart.tsx`:
   - Desktop layout: switch from grid-row to a `<table>` similar to `EndgameScoreGapSection` desktop table. Columns: Type | Games | W/D/L bar | You vs Opp | Opp vs You | Diff | You − Opp.
   - Keep the frequency bar? It's a small bar under the WDL. Drop it — the Games column already conveys volume, and consistency with Conversion & Recovery wins. (The Conversion & Recovery table shows `pct% (count)` for games column — mirror that.)
   - Mobile: stacked cards analogous to `material-card-{bucket}` — label, games count, MiniWDLBar, You/Opp/Diff row, bullet chart.
   - Re-use `formatScorePct`, `formatDiffPct`, `ZONE_SUCCESS/NEUTRAL/DANGER`, `MiniBulletChart`.
   - Low-sample (`total < MIN_GAMES_FOR_RELIABLE_STATS`): keep the existing unreliable opacity; show `(low)` suffix as today; still render score columns (they're defined even at n=1).
   - Empty rows (`total === 0`): skip score columns (render empty cells) to avoid divide-by-zero; keep row visible with 0 games.

2. Update the info popover:
   - Add a paragraph explaining the new columns (You vs Opp = chess-score percentage, Opp vs You = your opponents' score in the same games, Diff = signed gap, bullet chart visualizes it with ±5pp neutral zone).
   - Keep the per-type descriptions.

3. `data-testid` additions:
   - `endgame-category-{slug}-you`
   - `endgame-category-{slug}-opp`
   - `endgame-category-{slug}-diff`
   - Mobile card variants: `endgame-category-card-{slug}-*`

4. Ensure responsive layout keeps the table fitting on lg+ without horizontal scroll when practical; reuse the `overflow-x-auto` fallback from Conversion & Recovery.

5. Lint + type check + build frontend.

## Out of scope

- Backend schema changes — none needed; existing `EndgameCategoryStats` already exposes wins/draws/losses/total.
- Gauge strip — Conversion & Recovery has per-bucket fixed gauges; endgame-type performance has no cohort reference band, so no gauge is appropriate here.

## Verification

- `npm run lint` clean
- `npm run build` clean
- Visual check of `/endgames` page desktop + mobile
