---
title: Endgame Stats Card Redesign (v1.17 candidate)
date: 2026-05-12
context: gsd-explore session — replace three table-driven sections on the Endgames page with the established WDL+ScoreBullet card pattern
---

# Endgame Stats Card Redesign

Replaces three table-driven sections on the Endgames page (`frontend/src/pages/Endgames.tsx`) with the established WDL+ScoreBullet card pattern already used in `EndgameStartVsEndSection.tsx` ("What you do with it" tile) and `OpeningStatsCard.tsx`.

## Doctrine: Two-bullet design (cohort + peer)

Each card with a non-tautological opponent mirror carries **two bullets**, telling complementary stories:

- **Cohort bullet** — user's rate vs **cohort p50** (per-user pooled median from `reports/benchmarks-2026-05-10.md`), neutral band `[p25, p75]` matching the gauge band exactly. Population-relative frame: "where do I sit in the global player base?" Wilson CI + Wilson p-value vs p50.
- **Peer bullet** — `You − Opp` on a signed-diff axis, center 0, neutral band around 0 (e.g. `SCORE_GAP_NEUTRAL_MIN/MAX` pattern from Section 1 footer). Peer-relative frame: "do I have an edge over the opponents I actually played?" Wald-z p-value vs 0. Filter-responsive on both sides (user's filtered pool + opponent's mirror-bucket rate from the same pool). Reuses existing `MIRROR_BUCKET` / `MIN_OPPONENT_BASELINE_GAMES` logic.

The gauge shares the cohort bullet's reference frame (same `[p25, p75]` band, same global anchor). Gauge + cohort bullet = one coherent population-relative read; peer bullet = independent self-calibrating read.

Significance gating follows the existing convention from `EndgameStartVsEndSection.tsx`:

- font color painted only when `n ≥ MIN_GAMES_FOR_RELIABLE_STATS (10)` AND `p < 0.05` AND value lands outside the neutral band
- `p < 0.01` → high confidence; `p < 0.05` → medium; else low (matches `scoreConfidence.computeScoreConfidence`)

**Known property of the cohort frame (accepted, document in popover):** The p50 anchors from §171-177 are pooled across all rating × TC cells, not per-bucket. A stronger player will systematically sit above p50 and a weaker player below, regardless of within-tier skill. The verdict is therefore "rating-tier signal + within-tier skill, weighted toward the former." Cell-specific cohort baselines are deferred (would require benchmarks-skill rework and per-cell `gen_endgame_zones_ts.py` extension). The peer bullet partially compensates by giving a tier-independent read.

**Where the peer bullet applies (v1.17 — uniform layout, revisit after seeing the build):**

- ✅ Conv card — Opp Conv = `1 − myRecov` (mirror games where I was down). Non-trivial signal.
- ✅ Parity card — Opp Parity = `1 − myParity` in the same games. **Statistically redundant** with the cohort bullet at p50 = 0.500 (both test `myParity > 0.5`), but **kept for layout uniformity** across Conv/Parity/Recov. After v1 ships and we see real cards, decide whether to demote Parity's peer bullet to a compact `You / Opp / Diff` text row or drop it entirely.
- ✅ Recov card — Opp Recov = `1 − myConv` (mirror games where I was up). Non-trivial signal.
- ❌ Skill card — composite of three rates, no clean mirror. Keep cohort bullet only.
- ❌ Section 1 cards — same-games complement; the cohort bullet at p50 ≈ 0.5 already doubles as the peer test by the same symmetry argument as Parity. Section 1's footer Score Gap bullet provides the cross-card delta (Yes vs No), which is a different question. Hold v1.17 at cohort-only on Section 1 cards; revisit if the build reads thin.

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
  bullet vs cohort p50 bullet vs cohort p50 bullet vs cohort p50 bullet vs p50
  bullet You−Opp vs 0  bullet You−Opp vs 0  bullet You−Opp vs 0  —
```

Conv/Parity/Recov cards share an identical layout for v1.17 (gauge → percent → WDL → cohort bullet → peer bullet). Parity's peer bullet is mathematically redundant with its cohort bullet at p50 = 0.500 (both test `myParity > 0.5`); accepted for now in exchange for visual consistency across the card row. Revisit after seeing the build — likely demoted to a compact text row or dropped in v1.18.

Per-bucket cohort p50 / neutral band (from `reports/benchmarks-2026-05-10.md` §171-177):

| bucket     | p50    | p25    | p75    | rate definition       |
|------------|-------:|-------:|-------:|-----------------------|
| Conversion | 0.7186 | 0.6556 | 0.7692 | Win rate (W/n)        |
| Parity     | 0.5000 | 0.4434 | 0.5625 | Chess score (W+½D)/n  |
| Recovery   | 0.3010 | 0.2426 | 0.3636 | Save rate ((W+D)/n)   |
| Skill      | 0.5083 | 0.4661 | 0.5484 | mean of the three     |

- Per-bucket neutral bands already encoded as `FIXED_GAUGE_ZONES.{conversion,parity,recovery}` in `generated/endgameZones.ts`. Cohort bullet reuses the same band so the colored axis strip matches the gauge's blue zone.
- Skill card has no WDL bar — it's an arithmetic mean of three rate definitions, not directly tied to W/D/L. p-value handling for the Skill bullet is an open question (Wilson on a mean of three rates is not straightforward; may need to skip the sig test on this card and keep only the cohort band visual).
- Peer bullet (`You − Opp`) on Conv + Parity + Recov (uniform layout). Skill card is composite — no clean mirror, cohort bullet only. Reuse Section 1 footer's signed-diff bullet pattern (`SCORE_GAP_NEUTRAL_MIN/MAX` in `generated/endgameZones.ts`). Wald-z sig test vs 0 on the difference, gated on `MIN_OPPONENT_BASELINE_GAMES`.
- Parity peer bullet is statistically redundant with its cohort bullet (`p50 = 0.500` by benchmark-population symmetry). Both bullets answer the same question: "is `myParity > 0.5`?". Layout uniformity wins for v1.17; revisit after real-build review.

Removed: `You / Opp / Diff / You − Opp` *table presentation*. **Preserved**: the underlying signal — mirror-bucket opponent baseline (`opponentRate` / `MIRROR_BUCKET` / `MIN_OPPONENT_BASELINE_GAMES` logic) stays alive and feeds the peer bullet on Conv + Parity + Recov cards.

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
  Conv bullet vs per-type cohort p50
  Recov bullet vs per-type cohort p50
  Conv bullet You − Opp vs 0  (per-type, mirror class)
  Recov bullet You − Opp vs 0  (per-type, mirror class)
  Games link → /endgames/games?type=…
```

- Each type has its own cohort p50/p25/p75 (Rook Conv differs from Pawn Conv). Per-type bands already encoded as `PER_CLASS_GAUGE_ZONES[<class>].{conversion,recovery}` in `generated/endgameZones.ts`.
- Peer bullets use the per-type mirror class (opponent's mirror Conv/Recov rate in the same per-type pool). Gated on `MIN_OPPONENT_BASELINE_GAMES` per type.
- The grouped `EndgameWDLChart` is removed entirely — each card carries its own WDL bar, so cross-type comparison is reconstructable by scanning the grid.
- **Mobile density fallback (explicit):** 7 visual elements per card × 5 cards is dense. If real-device testing during execute reveals scroll bloat, the peer bullets are the first to drop on Section 3 — keep cohort bullets, drop diff bullets, document the loss in a popover. Do NOT discover this mid-execute; test on mobile before locking.

Removed: the global `EndgameWDLChart` component (used only here). Per-type table presentation removed; per-type mirror-bucket signal preserved via peer bullets.

## Open questions for plan-phase

1. **Per-type p50 source.** `PER_CLASS_GAUGE_ZONES` carries band bounds (`[p25, p75]` per class per bucket). Confirm the explicit per-type p50 is available — either already in the codegen pipeline or as an extension to `gen_endgame_zones_ts.py` / `app/services/endgame_zones.py`. Section 3 bullets cannot render their center tick without it.

2. **Skill bullet p-value.** Endgame Skill is a mean of three different rate definitions. Wilson CI on the composite is not directly defined. Options: (a) skip the sig test on the Skill card (cohort band visual only), (b) treat Skill as a synthetic score and approximate CI via the per-bucket Wilson CIs, (c) compute Skill on the raw underlying outcomes (e.g. weighted by bucket game count) and Wilson on that. Decide during plan-phase.

3. **Gauge significance gating.** Today gauges are always colored. Bullets gate font color on `n≥10 ∧ p<0.05`. With the new design they share the cohort frame — a sparse-data card could show a vivid gauge color but a neutral-grey bullet font, which may confuse. Either leave both as-is (gauge always-on, bullet gated) per established convention, or extend the gate to the gauge for visual consistency. Keep as-is for v1 unless feedback in iteration says otherwise.

4. **Section 1 / EndgameStartVsEndSection duplication.** The new "Endgame Yes" card's Score bullet vs 50% duplicates the existing "What you do with it" tile bullet. Locked for v1.17 to iterate on the layout; revisit after seeing the build.

5. **Mobile density on Section 3.** 5 cards × (2 gauges + WDL + 2 cohort bullets + 2 peer bullets + popovers + games link) is significantly denser than today's gauge-only treatment. Real-device check is required before locking; fallback is to drop the per-type peer bullets and keep only the cohort bullets on Section 3 (see Section 3 body). Section 2 peer bullets are not at risk — only 4 cards, less stacking.

6. **Peer bullet neutral band.** Section 1 footer Score Gap reuses `SCORE_GAP_NEUTRAL_MIN/MAX` (a ±band around 0 for chess-score deltas). For Conv-rate and Recov-rate signed-diff bullets the appropriate neutral band may differ (Conv differences live on win-rate scale, not score scale). Parity's peer bullet stays on the score-delta scale so `SCORE_GAP_NEUTRAL_MIN/MAX` fits cleanly. Options: reuse the existing constant across all three (simplest, accept small semantic stretch on Conv/Recov) or introduce dedicated `CONV_DIFF_NEUTRAL_*` / `RECOV_DIFF_NEUTRAL_*` from the benchmarks distribution of `(myRate − mirrorRate)` per-user. Decide during plan-phase.

7. **Parity peer-bullet redundancy.** After v1.17 ships, review whether the Parity peer bullet adds enough interpretive clarity to justify the redundant visual, or whether it should be demoted to a compact `You X% · Opp Y% · Diff +Z%` text row or dropped. Same review applies to Section 1 cards if a peer text row is added there.

## What this is not

- Not a backend change. Conv/Parity/Recovery rates, cohort bands, WDL aggregates, score-gap, per-type stats all already exist on the response schema.
- Not a new statistical method. Reuses existing Wilson CI / p-value machinery (`scoreConfidence.ts`, `wilsonBounds`, `computeScoreConfidence`).
- Not a benchmark refresh. Uses the existing `reports/benchmarks-2026-05-10.md` percentile table.

## Related work

- Phase 81 / `EndgameStartVsEndSection.tsx` — the gold-standard card pattern being extended.
- `OpeningStatsCard.tsx` — same idiom on the Openings page (WDL row + Score bullet + Eval bullet stacked).
- `EndgameConvRecovChart.tsx` — the per-type gauge cards this redesign extends.
- `reports/benchmarks-2026-05-10.md` §171-177 — cohort percentile source of truth.
