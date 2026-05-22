---
id: SEED-025
status: planted
planted: 2026-05-22
last_refined: 2026-05-22
planted_during: /gsd-explore session ("could we create percentiles also for the TC cards in the Time Pressure section?") — explored mid Phase 93 planning, scoped as a follow-on phase rather than a Phase 93 expansion
promoted_to: not yet — trigger condition below
scope: phase (single, ~3-4 plans) — per-TC empirical CDFs for the Time Pressure section + tooltip-level percentile annotations on Clock Gap / Net Flag Rate / per-quintile Score Gap rows
depends_on: v1.19 shipped (Phases 93/94/95) — the global-pooled CDF + chip + LLM payload pattern is the parent design; this seed extends it to per-TC surfaces
---

# SEED-025: Per-TC percentile annotations on Time Pressure cards

## Why This Matters

SEED-019 / Phases 93–95 ship percentile chips on 4 ΔES metrics, all **global-pooled** (across TC and ELO). The Time Pressure section is structurally different: its cards are **per-TC by construction** (one card each for bullet / blitz / rapid / classical), and the user-meaningful comparison there is "top X% of *bullet* players", not "top X% of all players". That forces a separate per-TC CDF artifact whose architecture inverts the global-pooling decision baked into Phase 93 D-02/D-05.

The chip surface is also different. Time Pressure percentiles would live **inside the hover tooltip** on each row (Clock Gap, Net Flag Rate, per-quintile Score Gap), not as a prominent card-header chip. That lower-stakes UX placement raises sample-size tolerance — users opt in to detail by hovering, so noisier tail estimates (p10/p90 over p5/p95) are acceptable.

Without this, the Time Pressure section keeps its zone bands but never lets a bullet player see "you're in the top 15% of bullet players on clock advantage at endgame entry" — a comparison the rest of the dashboard (after v1.19) will have conditioned them to expect.

## When to Surface

**Trigger condition:** v1.19 ships and Phases 93/94/95 are in production for long enough to observe user behavior around the global ΔES chips. Only then evaluate whether to invest in per-TC time-pressure variants. Two signals worth waiting for:

- Do users engage with the global chips (popover clicks, dwell time, LLM-prompt influence)? If chips are largely ignored, the per-TC expansion is dead weight.
- Does feedback or support traffic surface confusion about "where do I stand in bullet specifically?" — i.e. is the global pooling actually masking what users want to know?

This is a v1.20+ candidate, not a v1.19 in-flight scope expansion. Phase 93 is locked at 4 global-pooled CDFs and should stay there.

## Proposed Scope (24 per-TC CDFs)

| Bucket | # CDFs | Cohort per cell (est.) | Tail bound |
|---|---|---|---|
| Clock Gap × 4 TCs | 4 | ~500 users / TC | p5/p95 marginal — likely p10/p90 |
| Net Flag Rate × 4 TCs | 4 | ~500 users / TC | p10/p90 |
| Quintile Score Gap × 4 TCs × 4 quintiles (Q0–Q3) | 16 | ~100–500 / (TC, quintile) | p10/p90 |
| **Total** | **24** | | |

**Q4 excluded** — the 80–100% clock-remaining bucket is hidden in the UI per Plan 88-13 A-4 (see `frontend/src/components/charts/ScoreGapByTimePressureChart.tsx:6, 52`). The CDF mirrors that hiding — no percentile artifact for cells whose UI never renders.

**Per-(TC, quintile) cell variability** — bullet/blitz games skew toward low-time quintiles (Q0/Q1); classical skews toward high-time. At a ≥20-games-per-(TC, quintile) inclusion floor, "natural" cells will hold ~300–500 users and off-quintile cells ~100–300. p10/p90 SE at n=100 is ~3-4pp — usable in a tooltip context, not for a chip-header.

**Pooling axes** — per-TC required by product framing. ELO **pooled within TC** (mirrors the global-CDF framing of "top X% of [bullet] players", which is the comparison users actually want). Per-(TC, ELO) cells would split the cohort further to no clear product benefit.

## Open Design Questions (defer to discuss step)

1. **Net Flag Rate chip direction.** Lower-is-better; "top 5%" = fewest net timeouts. Inverted direction from the ΔES chips on the same card. Risk: user reads "top 5%" and assumes "most flags" the way "top 5% on score gap" means "biggest gap". Resolution likely: bake the direction into the popover prose ("you flag less than 95% of bullet players") rather than relying on raw "top X%" framing.

2. **Clock Gap chip semantics.** Signed metric. Is "top 5%" the user with the most clock-advantage at endgame entry (i.e. furthest positive)? Or the user closest to zero (most balanced clock management)? Almost certainly the former for product purposes, but worth confirming against actual user-question phrasing.

3. **Opponent-confound check for per-quintile ΔES.** D-02 dropped Recovery from Phase 93 because of an opponent-confounded d=0.95 inversion. The per-quintile Score Gap uses a same-game opponent-quintile split (`app/services/score_confidence.py:126-128`, `app/services/endgame_service._build_quintile_bullets`), which likely insulates against the Recovery-style confound — but this needs an empirical pass (a /benchmarks subchapter mirroring `reports/benchmarks-gap-metrics-percentile-candidacy.md`) before any of these distributions are chipped.

4. **Tooltip rendering — placement and prose.** Tooltip rows currently carry zone-band context; adding a percentile line per row could crowd the surface. Whether to show all metric percentiles inline or behind a secondary "show vs cohort" affordance is an interaction-design call deferred to the implementation phase.

5. **Whether to ship Net Flag Rate + Clock Gap percentiles or only the per-quintile Score Gaps.** Net Flag Rate has its own gauge zone (NEUTRAL_TIMEOUT_THRESHOLD = 5.0pp in `endgame_zones.py:159`); a percentile may be redundant. Worth testing in discuss whether the per-quintile chips alone deliver enough value to justify the artifact's complexity.

## Tier Placement

SEED-019 established an implicit tier hierarchy:

- **Tier 1** — global ΔES percentiles (Phase 93/94/95, shipping in v1.19).
- **Tier 2** — *this seed* — per-TC time-pressure percentiles in tooltips.
- **Tier 3** — per-class CDFs (per-endgame-type Conv/Recov/Score/Score Gap) — deferred per REQUIREMENTS.md §Future Requirements; per-type samples currently too thin.
- **Tier 4** — opening insights percentile annotations — candidate for a future Opening Insights v2 milestone.

This seed claims tier 2 because the per-TC pool (~500 users/cell) is samples-rich enough to support a real artifact today, and the tooltip placement is forgiving of marginal tail noise.

## What This Seed Is Not

- Not a Phase 93 scope expansion. Phase 93 stays locked at 4 global-pooled CDFs.
- Not a chip on the Time Pressure card header. Tooltip-only placement is the design intent.
- Not a per-(TC, ELO) artifact. ELO is pooled within TC; "top X% of bullet players" is the framing.
- Not a per-class extension. Per-type CDFs remain deferred per SEED-019 and REQUIREMENTS.md.
- Not a backend-only artifact. Unlike Phase 93's scalar `{metric}_percentile` field, tooltip rendering may want bracket-level data (e.g. "p25 / p50 / p75 within bullet Q0") for richer comparisons — final shape is a discuss-step decision.

## Cross-references

- Sibling to [[SEED-019]] — global percentile annotations on Endgame metrics. Parent design and rationale for the percentile-chip pattern.
- Mirrors the tier deferral logic in [[SEED-019]] §Per-Metric Verdict (tier 3 per-class, tier 4 opening insights).
- Methodology to inherit (when promoted): `.claude/skills/benchmarks/SKILL.md` Chapter 4 (added by Phase 93) — Standard CTE, sparse-cell exclusion, equal-footing filter, game-time ELO bucketing. The per-TC CDFs **do not** drop the TC dimension from the CTE; everything else carries verbatim.
- Source-of-truth for Time Pressure card schema: `app/schemas/endgames.py:709-757` (`TimePressureTcCard`, `PressureQuintileBullet`).
- Source-of-truth for quintile boundary definition: `app/services/endgame_service.py:1713-1714` (`min(4, int(clk_pct * 5))` — fixed per-cohort boundaries at 0/20/40/60/80%).
- Source-of-truth for Q4 hiding: `frontend/src/components/charts/ScoreGapByTimePressureChart.tsx:6, 52` (Plan 88-13 A-4).
