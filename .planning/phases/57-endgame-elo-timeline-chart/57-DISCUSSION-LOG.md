# Phase 57: Endgame ELO — Timeline Chart - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 57-endgame-elo-timeline-chart
**Areas discussed:** ELO formula, Skill source, Chart shape, Cold-start handling
**Note:** ELO formula decision also governs Phase 56 (captured at user's explicit request so Phase 56 can be planned later with the algorithm already locked).

---

## ELO Formula

| Option | Description | Selected |
|--------|-------------|----------|
| Performance rating from Skill | `avg(opp) + 400 · log10(skill/(1−skill))`, with skill clamped to [0.05, 0.95]; uses the existing Endgame Skill composite as the "score" | ✓ |
| Performance rating from raw W/D/L | Classic FIDE-style: ignores the composite, uses `(wins + 0.5·draws) / games` as the score | |
| Per-game performance then average | Compute `opp_rating_i + delta(score_i)` per game, then mean | |

**User's choice:** Performance rating from Skill, with skill clamped to [0.05, 0.95].

**Notes:**
- User asked whether Endgame Skill needs normalization to [0, 1]. Clarified: already [0, 1] by construction (mean of three [0, 1] rates). Only clamping to [0.05, 0.95] needed to bound log10.
- User asked whether Glicko-1 (chess.com) vs Glicko-2 (lichess) requires platform-specific formulas. Answered: no — per-platform segmentation keeps each combo on its native scale; proper Glicko performance would need RD/volatility we don't store; formula-choice noise is dwarfed by small-sample noise.
- User noted the math snippet only showed Endgame ELO ("I didn't see the hidden lines"). Added explicit Actual ELO formula: `avg(user_rating)` over the same rolling-100 pool of all games per weekly bin.

---

## Skill Source / Binning

| Option | Description | Selected |
|--------|-------------|----------|
| Per-bin recompute | Skill and opp-avg computed fresh per weekly bin / per breakdown row | |
| Cumulative up-to-date | All games up to that date; smoother but hides recent-period shifts | |
| Rolling window (last N games) | Fixed-size trailing window per point | ✓ |

**User's choice:** Rolling window, last 100 games, with weekly cadence — "like the other endgame timeline charts." Matches existing `_compute_weekly_rolling_series` (`endgame_service.py`) with `SCORE_GAP_TIMELINE_WINDOW = 100` and `CLOCK_PRESSURE_TIMELINE_WINDOW = 100` precedents.

**Notes:**
- User explicitly contrasted with Global Stats rating chart (daily datapoints) — the endgame family uses weekly cadence.
- Existing threshold `MIN_GAMES_FOR_TIMELINE = 10` reused (emit point only if window has ≥ 10 games). Naturally resolves cold-start.

---

## Chart Shape

| Option | Description | Selected |
|--------|-------------|----------|
| All combos on one chart, paired lines | Same hue per combo; bright = Endgame ELO, dark = Actual ELO. Matches SC-1. | ✓ |
| Tabs per combo | One pair per tab; cleaner but hides cross-combo comparison | |
| One chart, line-style differentiation | Solid vs dashed per combo; harder to scan | |

**User's choice:** All combos on one chart, paired lines.

**Notes:**
- Up to 16 lines (2 platforms × 4 TCs × 2 lines per combo) but sidebar filters usually narrow this.
- Legend click toggles individual combos on/off — reuses `hiddenKeys` pattern from `EndgameTimelineChart`.

---

## Cold-Start Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-hide via window threshold (≥ 10 games) | Reuse `MIN_GAMES_FOR_TIMELINE = 10` inside rolling-100 window; drop empty combos; chart-level empty state | ✓ |
| Stricter ≥ 20 games | Safer for the composite-of-3-buckets variance, but suppresses more early data | |
| Show everything with opacity dimming | Every point emitted; < 10 games → opacity 0.4; may still mislead | |

**User's choice:** Auto-hide via window threshold.

**Notes:**
- Three-tier dropout: per-point (window < 10), per-combo (zero points emitted), chart-level empty state (all combos dropped).
- Empty state copy: "Not enough endgame games yet for a timeline. Import more games or loosen the recency filter."

---

## Claude's Discretion

- Hue assignments per combo (from `frontend/src/lib/theme.ts`, contrast-checked).
- Bright-vs-dark implementation (opacity modifier vs separate theme constants).
- InfoPopover prose wording — covers formula, clamp, rolling-100 window, Glicko caveat.
- Mobile legend behavior (wrap or collapse) — subject to mobile-parity rule.
- Whether to surface `avg_opp_rating` and `games` in Phase 56's breakdown table — out of scope for this phase.

## Deferred Ideas

- Proper Glicko performance rating using RD/volatility (would need import-time schema change).
- Per-game Endgame Elo performance (alternative to skill-based aggregation).
- Material-bucket-level inline display on the timeline.
- Merged time-control combos for sparse samples.
