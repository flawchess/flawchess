---
title: Endgame Stats Card Redesign (v1.17 candidate)
date: 2026-05-12
context: gsd-explore session — replace three table-driven sections on the Endgames page with the established WDL+ScoreBullet card pattern
---

# Endgame Stats Card Redesign

Replaces three table-driven sections on the Endgames page (`frontend/src/pages/Endgames.tsx`) with the established WDL+ScoreBullet card pattern already used in `EndgameStartVsEndSection.tsx` ("What you do with it" tile) and `OpeningStatsCard.tsx`.

## Doctrine: Score Bullet H0

Every Score Bullet on the new cards tests user's rate against the **cohort p50** (per-user pooled median from `reports/benchmarks-2026-05-10.md`), with neutral band = `[p25, p75]` matching the gauge band exactly. This makes gauge and bullet tell one coherent story:

- gauge: rate-vs-cohort-band (visual)
- bullet: same rate, plus CI whiskers and Wilson p-value vs cohort p50 (statistical)

Significance gating follows the existing convention from `EndgameStartVsEndSection.tsx`:

- font color painted only when `n ≥ MIN_GAMES_FOR_RELIABLE_STATS (10)` AND `p < 0.05` AND value lands outside the neutral band
- `p < 0.01` → high confidence; `p < 0.05` → medium; else low (matches `scoreConfidence.computeScoreConfidence`)

Trade-off explicitly accepted: drops the `You / Opp / Diff / You − Opp` self-calibrating opponent signal entirely. The cohort baseline is statistically stronger (real population, Wilson CI, p-value) but no longer responds to the `Opponent Strength` filter.

## Section 1 — Games with vs without Endgame

Replaces the `EndgamePerformanceSection` table.

Layout: two side-by-side cards on lg+, stacked on mobile, plus a full-width footer row.

```
[ Endgame No card ]    [ Endgame Yes card ]
  WDL bar                WDL bar
  Score row              Score row
    label + %              label + %
    + popover              + popover
    + bullet vs 50%        + bullet vs 50%

[ Score Gap footer (spans both cards)      ]
  "Score Gap: +4%   ────●──── (vs 0)"
```

- Each card's Score bullet: center = 0.50, neutral [SCORE_BULLET_NEUTRAL_MIN, SCORE_BULLET_NEUTRAL_MAX], CI from Wilson on (W+0.5D, n).
- Footer Score Gap bullet: signed-diff axis, center = 0, neutral [SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX] (already in `generated/endgameZones.ts`).
- Coexists with the existing "Endgame Start vs End" twin-tile section (above) — duplication accepted; iterate after seeing the build.

## Section 2 — Endgame Metrics

Replaces the `EndgameScoreGapSection` table and its 4-gauge strip.

Layout: 4 cards side-by-side on lg+, stacked on mobile.

```
[ Conversion (Win) ] [ Parity (Score) ] [ Recovery (Save) ] [ Endgame Skill ]
  gauge                gauge               gauge               gauge
  percent + games      percent + games     percent + games     percent
  WDL bar              WDL bar             WDL bar             —
  bullet vs p50        bullet vs p50       bullet vs p50       bullet vs p50
```

Per-bucket cohort p50 / neutral band (from `reports/benchmarks-2026-05-10.md` §171-177):

| bucket     | p50    | p25    | p75    | rate definition       |
|------------|-------:|-------:|-------:|-----------------------|
| Conversion | 0.7186 | 0.6556 | 0.7692 | Win rate (W/n)        |
| Parity     | 0.5000 | 0.4434 | 0.5625 | Chess score (W+½D)/n  |
| Recovery   | 0.3010 | 0.2426 | 0.3636 | Save rate ((W+D)/n)   |
| Skill      | 0.5083 | 0.4661 | 0.5484 | mean of the three     |

- Per-bucket neutral bands already encoded as `FIXED_GAUGE_ZONES.{conversion,parity,recovery}` in `generated/endgameZones.ts`. Bullet reuses the same band so the colored axis strip matches the gauge's blue zone.
- Skill card has no WDL bar — it's an arithmetic mean of three rate definitions, not directly tied to W/D/L. p-value handling for the Skill bullet is an open question (Wilson on a mean of three rates is not straightforward; may need to skip the sig test on this card and keep only the cohort band visual).

Removed: `You / Opp / Diff / You − Opp` columns, mirror-bucket opponent baseline (`opponentRate` / `MIRROR_BUCKET` / `MIN_OPPONENT_BASELINE_GAMES` logic in `EndgameScoreGapSection.tsx`).

## Section 3 — Endgame Type Breakdown

Replaces the section's `EndgameWDLChart` (grouped horizontal-bar overview) AND extends `EndgameConvRecovChart` (per-type gauge-only cards) into full cards.

Layout: 5 per-type cards (rook, minor_piece, pawn, queen, mixed; pawnless hidden per `HIDDEN_ENDGAME_CLASSES`), 3-col grid on lg+, 2-col on sm, 1-col on mobile.

```
Per-type card:
  Type name + (sparse n indicator)
  ┌─────────────┬─────────────┐
  │ Conversion  │  Recovery   │  ← side-by-side gauges
  │   gauge     │   gauge     │
  └─────────────┴─────────────┘
  WDL bar
  Conv bullet vs per-type p50
  Recov bullet vs per-type p50
  Games link → /endgames/games?type=…
```

- Each type has its own cohort p50/p25/p75 (Rook Conv differs from Pawn Conv). Per-type bands already encoded as `PER_CLASS_GAUGE_ZONES[<class>].{conversion,recovery}` in `generated/endgameZones.ts`.
- The grouped `EndgameWDLChart` is removed entirely — each card carries its own WDL bar, so cross-type comparison is reconstructable by scanning the grid.

Removed: the global `EndgameWDLChart` component (used only here), and the You/Opp/Diff treatment that never existed in this section anyway.

## Open questions for plan-phase

1. **Per-type p50 source.** `PER_CLASS_GAUGE_ZONES` carries band bounds (`[p25, p75]` per class per bucket). Confirm the explicit per-type p50 is available — either already in the codegen pipeline or as an extension to `gen_endgame_zones_ts.py` / `app/services/endgame_zones.py`. Section 3 bullets cannot render their center tick without it.

2. **Skill bullet p-value.** Endgame Skill is a mean of three different rate definitions. Wilson CI on the composite is not directly defined. Options: (a) skip the sig test on the Skill card (cohort band visual only), (b) treat Skill as a synthetic score and approximate CI via the per-bucket Wilson CIs, (c) compute Skill on the raw underlying outcomes (e.g. weighted by bucket game count) and Wilson on that. Decide during plan-phase.

3. **Gauge significance gating.** Today gauges are always colored. Bullets gate font color on `n≥10 ∧ p<0.05`. With the new design they share the cohort frame — a sparse-data card could show a vivid gauge color but a neutral-grey bullet font, which may confuse. Either leave both as-is (gauge always-on, bullet gated) per established convention, or extend the gate to the gauge for visual consistency. Keep as-is for v1 unless feedback in iteration says otherwise.

4. **Section 1 / EndgameStartVsEndSection duplication.** The new "Endgame Yes" card's Score bullet vs 50% duplicates the existing "What you do with it" tile bullet. Locked for v1.17 to iterate on the layout; revisit after seeing the build.

5. **Mobile density on Section 3.** 5 cards × (2 gauges + WDL + 2 bullets + popovers + games link) is denser than today's gauge-only treatment. Check scroll length on real device before locking the card height.

## What this is not

- Not a backend change. Conv/Parity/Recovery rates, cohort bands, WDL aggregates, score-gap, per-type stats all already exist on the response schema.
- Not a new statistical method. Reuses existing Wilson CI / p-value machinery (`scoreConfidence.ts`, `wilsonBounds`, `computeScoreConfidence`).
- Not a benchmark refresh. Uses the existing `reports/benchmarks-2026-05-10.md` percentile table.

## Related work

- Phase 81 / `EndgameStartVsEndSection.tsx` — the gold-standard card pattern being extended.
- `OpeningStatsCard.tsx` — same idiom on the Openings page (WDL row + Score bullet + Eval bullet stacked).
- `EndgameConvRecovChart.tsx` — the per-type gauge cards this redesign extends.
- `reports/benchmarks-2026-05-10.md` §171-177 — cohort percentile source of truth.
