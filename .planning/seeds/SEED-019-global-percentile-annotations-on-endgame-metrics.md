---
id: SEED-019
status: promoted
planted: 2026-05-16
last_refined: 2026-05-22
planted_during: /gsd-explore session ("rework the Endgame Skill to be percentile based") — explored the broader question of which Endgames→Stats metrics should carry a percentile, concluded percentiles should be *added as annotations* across many metrics rather than *replacing* any single one
promoted_to: milestone v1.19 — Phases 93 (CDF artifact), 94 (backend + chip), 95 (LLM payload + prompt rework). See `.planning/milestones/v1.19-ROADMAP.md`. This seed is the canonical design doc for those phases; refine it here, then sync phase artifacts.
scope: phase (single, ~3-4 plans) — global empirical-CDF benchmark artifact + percentile annotation chip on 4 ΔES metrics + sample-size gating + LLM payload awareness
depends_on: v1.17 shipped (Endgame Stats Card Redesign — Phases 84–88.4, including 87.4 Endgame Skill removal + 87.5/87.6 Endgame ELO Timeline)
---

# SEED-019: Global percentile annotations on Endgame metrics

> **⚠ Superseded by [SEED-026 v2](./SEED-026-percentile-chip-refinement.md) (Phase 94.4, shipped 2026-05-27).**
>
> Phase 94.4 pivoted the chip from global-pool to peer-relative cohort framing. The "Final Tier-1 chip set" section below (rendered here as `### Ship (4 chips)`) is superseded — Recovery Score Gap and Conversion Score Gap are rescued from the v1 drop list under peer-relative framing (per CONTEXT D-05 / D-05a). The Cohen's d / Spearman ρ analysis is preserved as historical context but is no longer load-bearing — the cohort comparison absorbs the rating coupling the candidacy table was designed to flag.
>
> For the current Phase 94.4 design source-of-truth, see SEED-026 v2.

> **Refinement note (2026-05-22):** Seed planted alongside the retracted Phase 87.3 (Endgame Skill percentile composite). Phase 87.4 removed the Endgame Skill concept end-to-end (`EndgameSkillCard.tsx`, `endgame_skill_*` fields, ZoneSpec — all hard-deleted). Phase 87.5/87.6 shipped the Endgame ELO Timeline (logistic stretch from Endgame Score Gap, not a percentile transform). Phase 88/88.x shipped the Time Pressure card grid. v1.17 shipped 2026-05-19. This seed has since been promoted to v1.19 as Phases 93/94/95.
>
> **Phase 93 discuss refinement (2026-05-22):** The TS codegen mirror (`scripts/gen_endgame_zones_ts.py` extension + `frontend/src/generated/` artifact + CI Python→TS drift-guard) is **dropped from Phase 93 scope**. The CDF table has no frontend consumer in v1.19: Phase 94 backend interpolates the user's value against `GLOBAL_PERCENTILE_CDF` at request time and ships a scalar `{metric}_percentile`; the chip + popover render from that scalar. The TS mirror was a pattern-match against `endgame_zones.py`, which needs a TS mirror because gauge band painting happens client-side; the CDF is server-side-only. If a future phase ships a client-side CDF viz (sparkline, "what value puts me in the top X%" widget), the codegen mirror is added then. See `.planning/phases/93-global-percentile-benchmark-artifact/93-CONTEXT.md` for the locked decision.
>
> **Empirical refinement (2026-05-22):** A focused /benchmarks pass (`reports/benchmarks-gap-metrics-percentile-candidacy.md`) measured per-user distributions and rating-coupling (Cohen's d) for the 5 candidate ΔES metrics. Findings overturned the seed's original tier table on three points: (1) Endgame Score Gap is the *cleanest* skill-isolating metric (d=0.19), not a "self-relative noise" candidate as a pre-data critique suggested; (2) Conversion Score Gap is a heavy rating-proxy (d=1.37), not the seed's original "Tier-1 honest flagship" — but its chip is still useful under an "improvement focus" framing; (3) Recovery Score Gap is decisively rejected (d=0.95 inverted, opponent-confounded). The chip set has been narrowed to **4 metrics**, all on ΔES rows; raw % gauges keep their zone bands but get no chips.

## Why This Matters

Users like comparing themselves to others, and the benchmark cohort (~2,400 stratified Lichess users, ~1.37M games) is rich enough to place a user against the whole population on most endgame metrics. The product goal that emerged from refinement: **help the player identify what to focus on to improve.** A chip can serve this goal two ways:

- **Skill-isolating chips** (low-d metrics) — answer "what's your hidden endgame talent, separate from rating?" Useful primarily to **stronger / improving players** who can spot within-rating skill gaps.
- **Rating-coupled chips** (high-d metrics) — answer "where do you stand vs everyone?" Useful primarily to **weaker players** who learn "you have the largest single improvement available right here" (e.g. a 1200 in the bottom decile on conversion gains real ELO by practicing conversion technique).

Both subserve "improvement focus" but for different segments. The popover copy must encode *which kind* of percentile each chip is, so users read the right advice.

This is qualitatively different from the retracted Phase 87.3, which would have *redefined* a single metric's value as a cohort percentile. **Annotation, not substitution** — the raw value stays, the chip is additive context.

Without this, the Stats page keeps showing zone bands (IQR p25/p75 color regions) but never answers the literal question users ask: "where do I rank against everyone?"

## When to Surface

**Already surfaced.** Promoted to milestone v1.19, currently in planning as Phases 93 (CDF artifact), 94 (backend + chip), 95 (LLM payload + prompt rework).

The equal-footing filter convention (`|opp_rating − user_rating| ≤ 100`) is canonical in the /benchmarks skill and inherited as-is. The global CDF is built fresh in Phase 93 — no upstream artifact inherits (87.3 was retracted, 87.5/87.6's Endgame ELO uses a logistic recenter rather than a percentile transform).

## Per-Metric Verdict (empirically grounded — 2026-05-22 /benchmarks pass)

Decision factors: (1) single number, not a curve — a chip can't annotate a trend line; (2) "higher" must be unambiguously better; (3) distribution must be unimodal and reasonably symmetric (skew within ~|0.5|); (4) per-user sample deep enough for a stable percentile; (5) Cohen's d magnitude across the 800–2400 rating range — informs popover framing (low-d → skill-isolating copy, high-d → improvement-focus copy), and at extreme d (>~1.0 inverted, opponent-confounded) → drop.

Full data in `reports/benchmarks-gap-metrics-percentile-candidacy.md`.

### Ship (4 chips) — all on ΔES rows, none on raw % gauges

> **SUPERSEDED 2026-05-27 (Phase 94.4):** the 4-chip set recommended in this section was computed under global-pool framing. Phase 94.4 ships 8 chip families under peer-relative framing — Endgame Score Gap, Achievable Score Gap, Parity ΔES, Conversion ΔES, **Recovery ΔES (rescued)**, plus per-TC Time Pressure family (Time Pressure Score Gap, Clock Gap, Net Flag Rate). See SEED-026 v2 for current design.

| Metric | Card / row | d (800↔2400) | Popover framing | Notes |
|---|---|---:|---|---|
| **Endgame Score Gap** (page) | `EndgameOverallScoreGapRow.tsx` | **0.19** | Skill-isolating ("endgame strength separate from rating") | Cleanest distribution: skew +0.02, excess kurt −0.03, textbook normal. The earlier "self-relative noise" concern was empirically wrong — per-bucket medians shift only 4pp across 1600 ELO, well within within-bucket IQR. |
| **Achievable Score Gap** (page) | `EndgameOverallScoreGapRow.tsx` (Achievable row) | **0.32** | Skill-isolating (with mild rating coupling) | Mild left skew (−0.28), modestly heavy-tailed. Stockfish ceiling does most of the rating-stripping work. Acceptable Tier-1. |
| **Parity Score Gap** (Section 2) | `EndgameMetricCard.tsx` (Parity card, ΔES bullet row) | **0.30** | Skill-isolating ("parity skill is mostly independent of rating") | Cleanest Section-2 candidate. Near-symmetric (skew −0.16), no sigmoid bias (ES_entry ≈ 0.5, no ceiling/floor compression). |
| **Conversion Score Gap** (Section 2) | `EndgameMetricCard.tsx` (Conversion card, ΔES bullet row) | **1.37** | Improvement-focus ("conversion tracks rating; if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO") | Heavy rating-proxy, but the *advice it generates for weak players is correct*: practice converting up-material positions. Strong players see uninformative "top X%" confirmation; low cost. Left-skewed (skew −0.95, kurt +1.42) — the "top X%" framing in the right tail is squashed and the popover copy must not oversell upper percentiles. |

### No chip (gauge / bullet keeps its zone bands)

| Metric | Card / row | Why |
|---|---|---|
| Conversion Win % gauge | `EndgameMetricCard.tsx` (Conversion gauge) | Same card already has a chip on the Conv ΔES row. Adding a second chip would be redundant decoration on top of the existing color-coded gauge zones. |
| Parity Score % gauge | `EndgameMetricCard.tsx` (Parity gauge) | Same: ΔES row chip carries the signal. |
| Recovery Save % gauge | `EndgameMetricCard.tsx` (Recovery gauge) | Recovery is opponent-confounded — see Recovery Score Gap below. |
| **Recovery Score Gap** (Section 2) | `EndgameMetricCard.tsx` (Recovery card, ΔES bullet row) | **Actively misleading on the improvement axis.** d=0.95 inverted (weak players' opponents gift recoveries; strong players' opponents don't). Weak player reads "top 30% — I'm good at recoveries"; strong player reads "bottom 30% — I'm bad at recoveries"; both readings are **opposite** of the truth. Same opponent-confound mechanism that knocked Recovery out of the retracted Phase 87.3 composite. Drop the chip; keep the value + zone band. |
| Endgame Entry Eval, Achievable Score (raw), Endgame Score (raw), Non-Endgame Score | `EndgameOverallPerformanceSection.tsx` | Measure inputs (positions reached) or baselines, not earned outcomes. Already established as Tier 3 in the prior refinement. |
| Endgame Score Timeline, Endgame ELO Timeline, Avg Clock Diff over Time | timeline charts | Scalar percentile can't annotate a trend line. Endgame ELO Timeline is also a logistic stretch of Endgame Score Gap, so its "percentile" is already implicit in the Endgame Score Gap chip — would be double annotation. |
| All Time Pressure metrics (My/Opp Clock %, Clock Gap %, Net Flag Rate, Score Gap by Time Pressure quintile chart) | `EndgameTimePressureSection.tsx` / `EndgameTimePressureCard.tsx` | Direction ambiguous; quintile chart is multi-band. |
| Per-type cards (rook/minor/pawn/queen/mixed) | `EndgameTypeCard.tsx` | Per-type samples are thin (~8 rook conversion spans per user is noise). Deferred to a follow-on phase with a hard sample gate. |

## Proposed Scope (3-4 plans → v1.19 Phases 93/94/95)

### Plan 1 — Global empirical-CDF benchmark artifact (→ Phase 93)

The blocker: current benchmark machinery only stores IQR `[p25, p75]` zones. "Top 0.1% / bottom 32%" needs the **full global distribution of per-user values** per metric, pooled across all benchmark users.

The artifact is produced by **two complementary mechanisms with distinct roles** — skill = methodology source of truth, script = deterministic mechanization. Both are needed; one alone is insufficient. This split should be reflected as two tasks in the Phase 93 plan.

#### Task A — Extend `/benchmarks` SKILL.md with the CDF subchapter

- Add a new subchapter (e.g. §3.5 or a top-level Chapter 4) documenting the methodology: in-scope metrics (the 4 chipped ΔES metrics above), canonical CTE (lichess_username join, `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing filter, game-time ELO bucketing, sub-800 dropped), and the breakpoint set **p1, p2.5, p5, p10..p90, p95, p97.5, p99** (tail-bounded at p1/p99 — see Open Decisions for the sample-size rationale; p0.1 / p99.9 are not honestly supported at the current n ≈ 2000 pooled cohort and are out of v1.19 scope).
- SQL templates per metric (reuse the same patterns the empirical pre-flight at `reports/benchmarks-gap-metrics-percentile-candidacy.md` validated).
- Output written to `reports/global-percentile-cdf-latest.md` (with the rotation rule applied — archive prior dated report on re-run).
- The report includes per-metric breakpoint table + per-rating-bucket medians + skew/kurtosis as sanity checks, so the calibrator can eyeball whether the distribution is still well-shaped before locking the artifact.
- **Purpose**: human-inspectable distribution snapshots, calibration cycles, "should we retune the CDF / add a metric / drop a metric" decisions. This is the methodology source of truth — when in scope expands later, the skill subchapter changes first.

#### Task B — Write `scripts/gen_global_percentile_cdf.py`

- Connects to the benchmark DB (same connection-config pattern as `scripts/backfill_eval.py --db benchmark`).
- Runs the canonical CTE queries for each in-scope metric deterministically (no LLM in the loop).
- Emits the breakpoint tables as committed Python source at `app/services/global_percentile_cdf.py` (NOT `endgame_zones.py` — that file is the ZoneSpec / IQR-band registry; a 25-breakpoint CDF per metric is a different artifact shape and belongs in a sibling module).
- Runtime contract: a request-time helper interpolates a user's per-metric value against `GLOBAL_PERCENTILE_CDF[metric]` → percentile in [0, 100]. No live cohort query at request time.
- **Codegen mirror**: regenerate `frontend/src/generated/endgameZones.ts` (or a sibling generated file like `globalPercentileCdf.ts`) via the existing `scripts/gen_endgame_zones_ts.py` plumbing (or a sibling script). CI drift-gates this Python→TS step exactly like the existing zone codegen.
- **What CI does NOT drift-gate**: the DB→Python step. Generating the CDF requires the benchmark DB running locally, which CI doesn't have — same situation as `backfill_eval.py`. The Python source is committed and treated as a calibrated artifact; refreshing it is a manual recalibration step run when needed.
- **Purpose**: deterministic, reproducible artifact regeneration. The script encodes the locked decision the skill arrived at.

#### Why both

The skill comes first (decide what to compute, eyeball the distribution shape, validate against per-bucket medians, decide if the metric set should change). The script then mechanizes the locked decision so any developer with a running benchmark DB can reproduce the artifact bit-for-bit. Without the skill, the script would silently encode whatever was true at write time with no methodology audit trail. Without the script, the artifact would require an LLM-in-the-loop step on every refresh, which is a footgun for a load-bearing data file.

**Scope reduced**: only the 4 chipped metrics need a CDF. The empirical pass already at `reports/benchmarks-gap-metrics-percentile-candidacy.md` is the dry run — the skill subchapter formalizes that report's methodology into a reusable shape.

This is the **critical** plan — every other plan is cosmetic without it.

### Plan 2 — Backend: attach percentile + gate to each chipped metric (→ Phase 94 backend half)

- For each of the 4 metrics, interpolate the user's value against `GLOBAL_PERCENTILE_CDF` → a percentile in [0, 100].
- **Sample-size gate:** emit `null` (no chip) when the user's metric rests on too few games. Reuse `PVALUE_RELIABILITY_MIN_N = 10` as the floor, or a metric-specific threshold if needed. A misleading percentile is worse than none.
- Schema: add `{metric}_percentile` (nullable) alongside existing value/CI fields. Do not overload the existing zone fields.

### Plan 3 — Frontend: the annotation chip (→ Phase 94 frontend half)

- Small chip next to the metric value: above-median → "top X%", below-median → "bottom Y%". Round sensibly (no "top 0.137%"; "top 0.1%"). Consider a neutral "≈ average" band around p50 (e.g. p40–p60) to avoid the awkward "top 51%" / "bottom 49%" phrasing.
- Renders only when `{metric}_percentile != null`. Theme-colored consistent with the zone palette — pull from `theme.ts`, no hard-coded colors.
- **Hover tooltip / popover** carries the metric-aware framing:
  - **Skill-isolating chips** (Endgame Score Gap, Achievable Score Gap, Parity Score Gap): "Where you rank vs all players. This metric is mostly independent of rating — your percentile here reveals endgame ability separate from your overall strength."
  - **Improvement-focus chip** (Conversion Score Gap): "Where you rank vs all players. Conversion tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO."
- **Apply to both desktop and mobile** layouts (per CLAUDE.md mobile-parity rule).
- **Component touchpoints**: `EndgameOverallScoreGapRow.tsx` (page-level: 2 chips on Endgame Score Gap + Achievable Score Gap rows) and `EndgameMetricCard.tsx` (Section 2: 2 chips on Parity card ΔES bullet + Conversion card ΔES bullet; Recovery card unchanged).

### Plan 4 — LLM payload + glossary awareness (→ Phase 95)

- Add the 4 percentile fields to the insights payload and glossary in `app/prompts/endgame_insights.md` so the LLM can reason about them directly. Important for Phase 95: the LLM benefits most from the **skill-isolating** metrics (clean rating-invariant signal — "user's parity skill is top 12% even though they're 1500" is much more useful for narrative than rating-proxy framing).
- Bump `_PROMPT_VERSION` in `insights_llm.py` (currently `endgame_v35` per v1.17 closeout).
- Phase 95 also covers the broader LLM statistical-reasoning rework (p-values, CI bounds, percentiles, guardrails) — scope is larger than a payload extension; see v1.19-ROADMAP for the full Phase 95 brief.

## Design Decisions Captured Now

- **Goal: improvement focus, two paths.** Skill-isolating chips help stronger/improving players identify within-rating skill gaps; rating-coupled chips help weaker players see "biggest single ELO improvement available right here." Same chip shape, metric-aware popover copy.
- **Annotation, not replacement.** The raw value carries standalone meaning; the percentile is additive context. Confirmed in the original explore session; reinforced by the data pass.
- **One chip per row, not per card.** Each of the 3 Section-2 cards has a raw % gauge and a ΔES bullet row; the chip goes on the ΔES row only. Reasons: (a) the raw % gauge already paints color zones for the "where do you stand" signal, (b) the ΔES is the more honest improvement signal (subtracts position quality), (c) two chips per card would be visual noise.
- **Global-only comparison pool — empirically validated, with caveats.** The 4 chipped metrics all have d ≤ 1.4 across 1600 ELO points; within-bucket variance dominates between-bucket variance for the low-d set (Endgame, Achievable, Parity), making global percentile genuinely informative there. Conversion (d=1.37) is the edge case — popover labels it honestly as rating-coupled.
- **Why Endgame ELO Timeline gets no chip.** It's a logistic stretch of Endgame Score Gap (Phase 87.6 invariant: `endgame_elo + non_endgame_elo == 2 · actual_elo`), so its "percentile" is already implicit in the Endgame Score Gap chip. Double-annotation would be redundant.
- **Why Recovery gets no chip.** Opponent confound + heavy inverted rating coupling (d=0.95) means the chip would say "top X%" to weak players whose opponents gifted recoveries, and "bottom Y%" to strong players whose opponents played accurately — both are the **opposite** of the truth as users would read it.
- **Why per-type cards get no chips in v1.19.** Sample-thin per-type slices (Tier 4 in the original tier table). A percentile off 8 rook-conversion spans is noise. Revisit with a hard sample gate in a follow-on phase.
- **Sample-size gate is non-negotiable.** Below `PVALUE_RELIABILITY_MIN_N` games, no chip renders. A misleading percentile is worse than none.

## Open Decisions (defer until Phase 93/94 planning)

- CDF granularity / tail bounds (**decided 2026-05-22**): bound the breakpoint set at **p1 / p99** rather than p0.1 / p99.9. Rationale: at the current pooled cohort (n ≈ 2000 across the 4 metrics), p0.1 / p99.9 are estimated from ~2 observations each — sampling SE is 5+pp at the very tail, so "top 0.1%" would swing pp-magnitudes based on whether one outlier user is in the pool. p1 / p99 have ~20 observations each and an SE of ~2-3pp, which is honest at chip-rounding granularity. Final breakpoint set: **p1, p2.5, p5, p10..p90, p95, p97.5, p99**. Tighter tails are a future ops task (re-run `select_benchmark_users.py --per-cell 1000`, re-ingest), not a v1.19 scope item.
- Chip phrasing near the median: "top 51%" / "bottom 49%" both read oddly. Lean toward a neutral "≈ average" band (e.g. p40–p60) instead of a forced top/bottom label.
- Conversion Score Gap chip — render at all percentiles, or gate to "weak-cohort-only" (e.g. render only when percentile < p50) since the improvement signal is asymmetric (Goal-A relevance drops sharply at the top end)? The honest version renders always; the asymmetric version is less misleading at the right tail but mechanically weird.
- Skew handling on Conversion ΔES (skew −0.95): "top X%" rounding in the right tail obscures tail asymmetry. Mitigation options: (a) only render percentile when |percentile − 50| ≥ some threshold, (b) cap the displayed percentile at p95 / floor at p05, (c) accept the rounding noise. Decide during Plan 3.

## Methodology Lessons Inherited from SEED-013/014/015

Plan 1 must touch /benchmarks — copy the canonical CTE verbatim. Every gotcha applies: lichess_username join (NOT benchmark_user_id), `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing filter, mate handling per SEED-014 Plan 1, game-time ELO bucketing (NOT snapshot rating_bucket). A spike that bypasses the canonical CTE produces a wrong global distribution and therefore wrong percentiles for every user. The global CDF is *more* sensitive to this than zone bands — a bad tail skews "top 0.1%" dramatically.

## Estimated Effort

3-4 plans, mapped to Phases 93/94/95 in v1.19. Plan 1 (~half to one day): /benchmarks territory, well-trodden; the dry run in `reports/benchmarks-gap-metrics-percentile-candidacy.md` already validated the method. Plan 2 (~half a day): mechanical interpolation + gating, mirrors existing zone-attach plumbing. Plan 3 (~half a day): chip component + popover copy + desktop/mobile parity across 4 rows (2 page-level + 2 Section-2). Plan 4 (~1 hour) standalone, but Phase 95's broader LLM rework is larger — see v1.19-ROADMAP.

## Cross-references

- **Promoted to:** milestone v1.19 — `.planning/milestones/v1.19-ROADMAP.md` (Phases 93, 94, 95). **Note:** v1.19-ROADMAP.md Phase 93 success criteria still names "Skill Score Gap" in the Tier-1 list and references the old broader chip set — sync the roadmap to this refined seed before Phase 93 planning starts.
- **Empirical pre-flight:** `reports/benchmarks-gap-metrics-percentile-candidacy.md` (2026-05-22) — per-user distributions, Cohen's d, skew/kurtosis for all 5 candidate ΔES metrics. The tier table in this seed is downstream of that report.
- **Retracted predecessor:** Phase 87.3 (Endgame Skill v2 — Conv+Parity percentile composite) — never merged; see [[endgame-skill-dropped-conversion-elo]] for retraction rationale.
- **Shipped predecessors (v1.17):**
  - Phase 87.2 (Section 2 eval-based ΔES Score Gap) — defines the Tier-1 Conv/Parity/Recov gap metrics this annotates.
  - Phase 87.4 (Drop Endgame Skill) — removed `EndgameSkillCard.tsx` and `endgame_skill_*` fields end-to-end. See [[endgame-skill-dropped-conversion-elo]].
  - Phase 87.5/87.6 (Endgame ELO Timeline — logistic recenter from Endgame Score Gap). See [[endgame-elo-rebuild-on-score-gap]], [[endgame-elo-logistic-anchored]].
  - Phase 88/88.x (Time Pressure cards + Clock Diff timeline).
- **Predecessor seeds:**
  - `.planning/seeds/closed/SEED-015-predicted-vs-achieved-endgame-gap-as-first-class-metric.md` — `achievable_score_gap` metric (chipped here).
  - `.planning/seeds/closed/SEED-016-per-span-eval-delta-endgame-metric.md` — per-span ΔES + per-type-sample-thinness concern (deferred to a follow-on phase).
- **Zone recalibration sibling:** `.planning/seeds/closed/SEED-006-benchmark-population-zone-recalibration.md`.
- **/benchmarks skill + canonical CTE:** `.claude/skills/benchmarks/SKILL.md`.
- **New artifact module (Task B output):** `app/services/global_percentile_cdf.py` — holds `GLOBAL_PERCENTILE_CDF` (per-metric breakpoint tables). Separate from `app/services/endgame_zones.py` (ZoneSpec / IQR-band registry — unchanged shape).
- **New generation script (Task B):** `scripts/gen_global_percentile_cdf.py` — DB→Python, manual recalibration step, not CI-gated.
- **Codegen mirror to TS:** extend `scripts/gen_endgame_zones_ts.py` (or sibling script) to also emit the CDF; CI drift-gates the Python→TS step.
- **Existing zone registry (unchanged shape, may grow a new ZoneSpec for chip rendering):** `app/services/endgame_zones.py`; codegen `scripts/gen_endgame_zones_ts.py` → `frontend/src/generated/endgameZones.ts`.
- **Reliability floor constant:** `PVALUE_RELIABILITY_MIN_N` in `app/services/endgame_zones.py`.
- **Card components to annotate (verified 2026-05-22):**
  - `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` — 2 chips (Endgame Score Gap row + Achievable Score Gap row).
  - `frontend/src/components/charts/EndgameMetricCard.tsx` — 2 chips on the ΔES bullet rows of the Parity and Conversion cards (Recovery card and all 3 raw % gauges unchanged).
- **Out of scope (no chip):** `EndgameScoreOverTimeChart.tsx`, `EndgameEloTimelineSection.tsx`, `EndgameClockDiffOverTimeChart.tsx`, `EndgameTimePressureSection.tsx`, `EndgameTimePressureCard.tsx`, `EndgameTypeCard.tsx` (per-type, deferred).
- **LLM payload + prompt:** `app/prompts/endgame_insights.md`; `_PROMPT_VERSION` in `app/services/insights_llm.py` (currently `endgame_v35`).
- **Popover copy discipline:** project memory `feedback_popover_copy_minimalism.md`; metric-aware framing rationale captured above in Plan 3.
