---
id: SEED-019
status: open
planted: 2026-05-16
planted_during: /gsd-explore session ("rework the Endgame Skill to be percentile based") — explored the broader question of which Endgames→Stats metrics should carry a percentile, concluded percentiles should be *added as annotations* across many metrics rather than *replacing* any single one
trigger_when: After Phase 87.4 (Conversion ELO Timeline, supersedes the retracted 87.3) ships, surface this seed when either (a) users keep asking "is this good vs everyone else?" on metrics in the Endgames Stats page, or (b) the next endgame analytics milestone is being scoped and a global empirical-CDF benchmark artifact can be produced in the same /benchmarks pass.
scope: phase (single, ~3-4 plans) — global empirical-CDF benchmark artifact + percentile annotation chip on Tier-1/Tier-2 metrics + sample-size gating + LLM payload awareness
depends_on: Phase 87.4 (replaces the retracted Phase 87.3 — see .planning/notes/endgame-skill-dropped-conversion-elo.md)
---

# SEED-019: Global percentile annotations on Endgame metrics

> **Note (2026-05-16):** This seed was planted during the same /gsd-explore session that produced Phase 87.3. Phase 87.3 has since been **retracted** (see [[endgame-skill-dropped-conversion-elo]]) — the percentile-of-ΔES design failed UAT review on opponent-error confound + timeline volatility, and "Endgame Skill" is being removed as a product concept (Phase 87.4). The core idea in *this* seed survives unchanged because it is about percentile **annotation** of existing metrics, not percentile substitution as a metric's value. Where the original body referenced "the global-CDF artifact from 87.3", read that as "a fresh global-CDF artifact this phase produces" — no 87.3 artifact exists to inherit.

## Why This Matters

Users like comparing themselves to others, and the benchmark cohort (~2,400 stratified Lichess users, ~1.37M games) is rich enough to place a user against the whole population on most endgame metrics. The product instinct from the /gsd-explore session was "make Endgame Skill percentile-based" — Phase 87.3 attempted to do that for the Skill composite, but that approach was retracted (see note above). The broader, durable idea is bigger than one metric and qualitatively different from the retracted approach:

- **The retracted 87.3 would have redefined a single metric's *value*** as a cohort percentile of the Conv+Parity ΔES composite (feeding the Endgame ELO formula). The percentile *was* the metric. This is what failed UAT.
- **This seed adds a percentile *annotation* next to many existing metric numbers**, without replacing them. The raw value stays (a 72% conversion rate is meaningful on its own); a compact "top 8% / bottom 32%" chip is rendered beside it. Annotation, not substitution — confirmed as the explicit design direction in the explore session, and unaffected by 87.3's retraction.

The decision that shapes everything: **comparison pool is global-only** (the whole benchmark population, not the user's own ELO×TC cell). This is a deliberate product call — it's the bragging-rights number users actually want — and it splits the metrics into a strong case and a weak-but-still-wanted case (see Design Decisions).

Without this, the Stats page keeps showing zone bands (IQR p25/p75 color regions) but never answers the literal question users ask: "where do I rank against everyone?"

## When to Surface

Trigger any of:

1. Phase 87.3 has shipped and a user asks "is my Conversion / Score Gap good vs everyone?" on a metric *other than* Endgame Skill.
2. The next endgame-zones recalibration sweep (sister to SEED-006), where the global-CDF artifact can be produced in the same /benchmarks pass.
3. Roadmap planning for an Endgame Analytics v3 / Insights v2 milestone.
4. The 87.3 percentile lands well and the pattern obviously wants generalizing to the gap metrics.

**Do NOT trigger before Phase 87.4 has shipped and been used in production for at least one phase cycle.** Phase 87.3 was retracted before merge (no percentile-as-metric machinery shipped — see [[endgame-skill-dropped-conversion-elo]]); Phase 87.4 replaces it and lands the affine-recentered Conversion ELO Timeline. This seed should establish a *fresh* global empirical-CDF artifact in its own phase rather than inheriting from 87.3 (which doesn't exist) or 87.4 (which doesn't need a CDF — it uses an affine recenter, not a percentile transform). The equal-footing filter convention (`|opp_rating − user_rating| ≤ 100`) is the only relevant inheritance and is already canonical in the /benchmarks skill.

## Per-Metric Judgment (the core analytical output)

Deciding factors applied: (1) single number, not a curve — a chip can't annotate a trend line; (2) "higher" must be unambiguously better — needed for "top X%" to read as an achievement; (3) does global comparison add signal or just re-measure ELO; (4) per-user sample deep enough for a stable percentile.

### Tier 1 — Yes, percentile is genuinely insightful (skill-isolating gap / ΔES metrics)

These are eval-baseline-adjusted, so a global rank is *not* a rating proxy — it means the same thing at 1200 or 2000.

| Metric | Note |
|---|---|
| **Skill Score Gap** | Honest flagship: "you outperform your own positions better than X% of all players." Likely already the 87.3 composite — align, do not duplicate. |
| **Achievable Score Gap** | Pure over/under-performance vs Stockfish ceiling. |
| **Endgame Score Gap** | Self-relative (endgame vs your own non-endgame). Direction clear. |
| **Conversion Score Gap** | ΔES, skill-isolating. |
| **Parity Score Gap** | ΔES, skill-isolating. |
| **Recovery Score Gap** | ΔES, skill-isolating, **but** Recovery is opponent-confounded (the same finding that made Phase 87.3 drop Recovery from the composite). Gate hard on sample size and consider footnoting the confound, or defer Recovery to Tier 4. |

### Tier 2 — Yes for motivational value, but it's a rating proxy (raw rates)

Global percentile here mostly re-measures ELO (a 2000 player is ~top 10% on all of these; a 1200 player ~bottom 30%). Still the brag users want — ship it, but label honestly and don't pretend it isolates skill.

| Metric | Note |
|---|---|
| **Endgame Skill (raw composite)** | The marquee bragging number. Note: 87.3 may already replace this value with a percentile — reconcile before adding a second one. |
| **Conversion / Parity / Recovery** | Direction-clear single numbers. Recovery needs the same sample gate / opponent-confound caveat as above. |

### Tier 3 — No percentile

| Metric | Why |
|---|---|
| **Endgame Entry Eval**, **Achievable Score** | Measure *what positions you reach* (opponent/variance-driven), not earned skill. "You reach better positions than X%" is conceptually muddy and a pure rating proxy. |
| **Non-Endgame Score** | It's the baseline you're measured *against*, not an endgame achievement. Ranking it is odd. |
| **All clock / time-pressure metrics** (avg clock diff, my/opp time, net timeout) | Direction ambiguous — more clock than opponent isn't unambiguously good (can mean under-thinking). "Top X% at having time left" doesn't read as an achievement. |
| **All timelines & charts** (Score-over-time, ELO timeline, Time-pressure-vs-performance) | A percentile chip can't annotate a trend line. |

### Tier 4 — Defer (per-type breakdown)

Per-type **Conversion / Recovery / Score / Score Gap**: same metrics as Tier 1/2 but split 5 ways, so per-user samples are thin. A percentile off 8 rook-conversion spans is noise. Only with a hard sample gate, and not in the first cut. (Mirrors the per-type-sample concern already noted in SEED-016.)

## Proposed Scope (3-4 plans)

### Plan 1 — Global empirical-CDF benchmark artifact

The blocker: current benchmark machinery only stores IQR `[p25, p75]` zones. "Top 0.1% / bottom 32%" needs the **full global distribution of per-user values** per metric, pooled across all benchmark users (not cell-bucketed).

- Extend `/benchmarks` SKILL.md with a section that, per Tier-1/Tier-2 metric, computes the per-user value (same canonical CTE: lichess_username join, `bic.status='completed'`, sparse-cell exclusion) and emits a compact CDF — e.g. 101 evenly-spaced quantile breakpoints (p0..p100) or a denser tail (p0.1, p0.5, p1, p2.5, p5, p10..p90, p95, p97.5, p99, p99.5, p99.9) so the extremes ("top 0.1%") are representable.
- **Equal-footing-filter question — resolve first (likely inherited from 87.3):** Chapter 2–3 benchmark metrics apply `|opp_rating − user_rating| ≤ 100`. The global CDF should use the *same* per-user definition Phase 87.3 settled on, for consistency. Confirm what 87.3 chose before planning.
- Lock the breakpoint tables into `app/services/endgame_zones.py` (e.g. `GLOBAL_PERCENTILE_CDF`) and regenerate `frontend/src/generated/endgameZones.ts`. A user's percentile = interpolate their value against the breakpoints; no live cohort query needed at request time.

This is the **critical** plan — every other plan is cosmetic without it.

### Plan 2 — Backend: attach percentile + gate to each Tier-1/Tier-2 metric

- For each in-scope metric, interpolate the user's value against `GLOBAL_PERCENTILE_CDF` → a percentile in [0, 100].
- **Sample-size gate:** emit `null` (render no chip) when the user's metric rests on too few games. Reuse `PVALUE_RELIABILITY_MIN_N = 10` as the floor, or a metric-specific threshold for Recovery / per-type. A misleading percentile is worse than none.
- Schema: add `{metric}_percentile` (nullable) alongside existing value/CI fields. Do not overload the existing zone fields.

### Plan 3 — Frontend: the annotation chip

- A small chip next to the metric value: above-median → "top X%", below-median → "bottom Y%" (asymmetric phrasing reads better than a bare "42nd percentile"). Round sensibly (no "top 0.137%"; "top 0.1%").
- Renders only when `{metric}_percentile != null`. Theme-colored consistent with the existing zone palette (above/typical/below) — pull from `theme.ts`, no hard-coded colors.
- **Apply to both desktop and mobile** layouts of every touched card (per CLAUDE.md mobile-parity rule).
- For Tier-2 raw rates, tooltip copy must be honest about the rating-proxy nature without jargon (per memory `feedback_popover_copy_minimalism`): WHAT it compares + sign convention only.

### Plan 4 — (Optional, small) LLM payload + glossary awareness

- Add the percentile fields to the insights payload and glossary in `app/prompts/endgame_insights.md` so the LLM can say "your conversion gap ranks above 88% of all players" instead of re-deriving it. Bump `_PROMPT_VERSION` in `insights_llm.py`.
- Split as a /gsd-quick after Plans 1-3.

## Design Decisions Captured Now

- **Annotation, not replacement.** The raw value carries standalone meaning; the percentile is additive social context. Confirmed explicitly by the user in the explore session. (Contrast 87.3, where the percentile *becomes* the Skill value by design — that is a different, deliberate choice for that one composite.)
- **Global-only comparison pool, accepted with eyes open.** Same-cohort percentile would isolate skill from rating; global does not for raw rates. The user chose global only — it's the bragging number. The mitigation is *honest labeling* on Tier-2 metrics and *reserving the "this is real skill" framing* for Tier-1 gap metrics, not switching pools.
- **Why gap/ΔES metrics are the strong case.** They are already eval-baseline-adjusted, so a global rank is invariant to rating. "You beat your own positions better than 88% of everyone" is true and actionable at any ELO.
- **Why raw rates still ship despite being a rating proxy.** Motivation. "Better endgame player than 70% of all chess players" is what users came for, even though it largely tracks ELO. Tier-2, not Tier-1, and never dressed up as skill-isolating.
- **Why Entry Eval / Achievable Score / Non-Endgame Score get no percentile.** They measure inputs (positions reached) or the baseline itself, not an earned outcome. Ranking them is conceptually muddy and adds no insight.
- **Why no percentile on clock/time metrics.** Direction is ambiguous — "top X% at having clock left" is not unambiguously an achievement (can signal under-thinking). A percentile demands a monotone "more is better" axis.
- **Why charts get nothing.** A scalar percentile cannot annotate a trend line or scatter without itself becoming a (different) chart — out of scope and visually noisy.
- **Sample-size gate is non-negotiable.** Recovery and per-type are thin. Show nothing rather than a percentile built on <10 games.

## Open Decisions (defer until phase planning)

- Reconcile with Phase 87.3: if 87.3 already turns Endgame Skill into a (cohort) percentile, does this seed (a) leave Skill alone and only annotate the *other* Tier-1/Tier-2 metrics, or (b) also offer a *global* Skill percentile beside 87.3's cohort one? Lean (a) to avoid two competing percentiles on the same card.
- CDF granularity: uniform p0..p100 (simple, coarse at the tails) vs tail-densified breakpoints (lets "top 0.1%" be honest). Lean tail-densified — the extremes are exactly where bragging users look.
- Recovery: Tier-1 with a hard gate + confound footnote, or demote to Tier-4 entirely given the opponent-confound that knocked it out of the 87.3 composite. Decide after seeing 87.3's rationale in production.
- Chip phrasing near the median: "top 51%" / "bottom 49%" both read oddly around p50. Consider a neutral "≈ average" band (e.g. p40–p60) instead of a forced top/bottom label.
- Whether the global CDF reuses the equal-footing filter (almost certainly yes, inheriting 87.3's choice — but confirm 87.3 actually applied it before locking).

## Methodology Lessons Inherited from SEED-013/014/015

If Plan 1 touches /benchmarks — and it must — copy the canonical CTE verbatim. Every gotcha applies: lichess_username join (NOT benchmark_user_id), `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing filter, mate handling per SEED-014 Plan 1. A spike that bypasses the canonical CTE produces a wrong global distribution and therefore wrong percentiles for every user. The global CDF is *more* sensitive to this than zone bands — a bad tail skews "top 0.1%" dramatically.

## Estimated Effort

3-4 plans. Plan 1 (~half to one day): /benchmarks territory, well-trodden, but the CDF artifact is new shape and tail granularity needs care. Plan 2 (~half a day): mechanical interpolation + gating, mirrors existing zone-attach plumbing. Plan 3 (~half a day): chip component + desktop/mobile parity across ~8 cards. Plan 4 (~1 hour): /gsd-quick. Comparable to SEED-015; the data-plumbing reuse from 87.3 keeps it bounded.

## Cross-references

- Retracted predecessor: Phase 87.3 (Endgame Skill v2 — Conv+Parity percentile composite) — never merged; see [[endgame-skill-dropped-conversion-elo]] for the retraction rationale. The CDF artifact this seed plans must be built fresh.
- Successor / actual predecessor: Phase 87.4 (Drop Endgame Skill, rewire timeline as Conversion ELO from Conv ΔES) — `.planning/milestones/v1.17-ROADMAP.md`; must ship first. Note 87.4 uses an affine recenter, not a percentile transform, so it produces no CDF for this seed to inherit.
- Predecessor metric: Phase 87.2 (Section 2 eval-based ΔES Score Gap) — PR #98; defines the Tier-1 gap metrics this annotates
- Predecessor seed: `.planning/seeds/closed/SEED-015-predicted-vs-achieved-endgame-gap-as-first-class-metric.md` — `achievable_score_gap` metric (Tier-1 here)
- Predecessor seed: `.planning/seeds/closed/SEED-016-per-span-eval-delta-endgame-metric.md` — per-span ΔES + the per-type-sample-thinness concern (Tier-4 here)
- Zone recalibration sibling: `.planning/seeds/closed/SEED-006-benchmark-population-zone-recalibration.md`
- /benchmarks skill + canonical CTE: `.claude/skills/benchmarks/SKILL.md`
- Zone registry to extend: `app/services/endgame_zones.py`; codegen `scripts/gen_endgame_zones_ts.py` → `frontend/src/generated/endgameZones.ts`
- Reliability floor constant: `PVALUE_RELIABILITY_MIN_N` in `app/services/endgame_zones.py`
- Card components to annotate: `EndgameMetricCard.tsx`, `EndgameSkillCard.tsx`, `EndgameOverallScoreGapRow.tsx`, `EndgameOverallPerformanceSection.tsx`, `EndgameTypeCard.tsx` (Tier-4)
- Popover copy discipline: project memory `feedback_popover_copy_minimalism.md`; honest-labeling rationale per this session
