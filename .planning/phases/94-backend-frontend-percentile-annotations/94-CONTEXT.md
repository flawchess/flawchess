# Phase 94: Backend & Frontend Percentile Annotations - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface percentile annotations end-to-end on the **4 chipped ΔES rows** (per SEED-019 empirical refinement). Two halves:

- **Backend half:** For each of the 4 in-scope metrics, interpolate the user's value against `GLOBAL_PERCENTILE_CDF` (already shipped in Phase 93) via the existing `interpolate_percentile(metric_id, value) -> float | None` helper, gate by a metric-specific minimum-N reliability floor (PCTL-06), and emit a nullable `{metric}_percentile` field on the endgame API response alongside the existing value / CI / zone fields. Additive and non-breaking.
- **Frontend half:** Render a compact "top X%" chip beside the metric value on the 4 affected rows — `EndgameOverallScoreGapRow.tsx` (Endgame Score Gap row + Achievable Score Gap row) and `EndgameMetricCard.tsx` (Parity card ΔES bullet + Conversion card ΔES bullet). Desktop + mobile parity, theme-driven colors, metric-aware popover copy.

The 4 in-scope metrics (inherited from Phase 93, locked):

- `score_gap` (Endgame Score Gap, page-level) — skill-isolating popover framing
- `achievable_score_gap` (Achievable Score Gap, page-level) — skill-isolating
- `section2_score_gap_parity` (Section 2 Parity ΔES) — skill-isolating
- `section2_score_gap_conv` (Section 2 Conversion ΔES) — improvement-focus

Recovery ΔES and the 3 raw % gauges (Conv / Parity / Recov Win/Save %) keep their existing IQR zone bands but get NO chips. No new metric IDs, no new schemas — additive fields on existing endgame response schemas.

</domain>

<decisions>
## Implementation Decisions

### Chip styling + popover trigger (discussed)

- **D-01: Chip is the popover trigger.** Tap/hover the chip itself opens the popover. NO adjacent HelpCircle next to the chip. The chip carries semantic meaning ("top X%") rather than being decorative metadata, so it makes sense to read as a tappable element directly. This is a deliberate deviation from the existing `MetricStatPopover` HelpCircle-trigger pattern used elsewhere on these rows — the chip is primary content, not a metadata icon, so it earns its own trigger affordance.
- **D-02: Banded color zones from `theme.ts`** — three discrete bands:
  - Percentile <p25 → theme red
  - Percentile p25..p75 → theme neutral
  - Percentile >p75 → theme green
  (Existing `theme.ts` semantic colors — danger / muted / success / similar. Planner picks the exact constants to reuse; no new theme colors introduced.) Mirrors the IQR zone-band convention already used elsewhere on these cards (raw % gauges, ΔES zone bands), so the chip color reads consistently with the rest of the row.
- **D-03: Lucide `Flame` icons stack inside the chip for the top-percentile tiers** (top 10% / 5% / 1% are honest at the cohort's tail-resolution — see PCTL-04 / SEED-019 §"Open Decisions"):
  - Top 10% (percentile ≥90) → 1 flame
  - Top 5% (percentile ≥95) → 2 flames
  - Top 1% (percentile ≥99) → 3 flames
  Flames stack additively (3 flames means top 1% AND top 5% AND top 10% are all true — render the highest tier only). Lucide `Flame` from `lucide-react` is the icon source (already used elsewhere in the codebase; no new icon dep). Bottom tiers get no icon — flames are a positive-tier-only motif. The tier thresholds (p90 / p95 / p99) match the most rightward breakpoint at which the cohort tail is sample-honest (~20 observations per breakpoint per SEED-019 / Phase 93 D-06); finer flame tiers (e.g. top 0.5%) would be dishonest at the current pooled n≈2000.
- **D-04: Pill/badge with colored background fill.** Rounded background in the banded color (red / neutral / green), contrasting text (white or theme-readable). Distinct from the metric value visually but inline alongside it. Reads clearly as a UI element. Theme drives both background and text colors (no hard-coded values per PCTL-05).
- **D-05: Inline, right-aligned on the row.** Metric value on the left edge of the row, chip floats to the right edge of the row. Reads as "metadata" separate from the value while staying on the same horizontal line. Mobile parity: at 375px the chip stays on the same row when there's space; planner decides the wrap behavior when there isn't (a wrap to the next line at narrow widths is acceptable as long as both desktop and mobile remain readable).

### Phrasing + sign conventions (locked by ROADMAP / REQUIREMENTS — not re-discussed)

- **D-06: "Top X%" phrasing always.** NO "bottom Y%" wording anywhere. A user at p1 renders as "top 99%"; a user at p99 renders as "top 1%"; a user near p50 renders as "top 50%". Honest rounding (no spurious decimals — e.g. "top 0.1%" not "top 0.137%"). Locked by PCTL-03.
- **D-07: Render literally near the median.** "Top 49%" / "top 50%" / "top 51%" render exactly as the rounded value indicates; no neutral "≈ average" band suppresses the label. Rationale: PCTL-03's example shows "top 50%" rendering literally, and a "near average" band would mute the very chip the user came to read. (User opted not to re-discuss this gray area; the SEED-019 "open decision" defaults to the literal-render path.)

### Metric-aware popover framing (locked by ROADMAP / REQUIREMENTS — not re-discussed)

- **D-08: Two popover flavors, metric-routed.**
  - Skill-isolating flavor — Endgame Score Gap, Achievable Score Gap, Parity ΔES (d ≤ 0.32): "Where you rank vs all players. Mostly independent of rating — reveals endgame ability separate from overall strength."
  - Improvement-focus flavor — Conversion ΔES only (d = 1.37, skew −0.95): "Where you rank vs all players. Conversion tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO."
  Exact copy is the planner's call within the discipline of `feedback_popover_copy_minimalism.md` (WHAT + sign convention only, no jargon, no caveats). Both flavors must be visible side-by-side on the same Stats page (Endgame Score Gap chip popover + Conversion ΔES chip popover are both rendered for any user whose sample clears both gates), so they must read as deliberate companions, not contradictions.
- **D-09: Conversion ΔES chip renders at all percentiles** (no suppression in the right tail, no percentile capping). The improvement-focus popover framing is the mitigation for the strong-player "uninformative top 5%" case — popover copy honestly labels the chip as rating-coupled. The right-tail skew noise (−0.95) is accepted as the cost of an honest distribution; the chip rounds to whole percent, so per-user noise stays bounded. (User opted not to re-discuss this gray area; SEED-019's "always render" default holds.)

### Reliability gating + schema shape (locked by ROADMAP / REQUIREMENTS — not re-discussed)

- **D-10: Per-metric minimum-N reliability gate.** A misleading percentile is worse than none (PCTL-06). The gate semantics:
  - Endgame Score Gap — gated on `endgame_n` AND `non_endgame_n` (both wings of the gap must clear the floor).
  - Achievable Score Gap — gated on the endgame-entry span count that the metric itself is computed from.
  - Section 2 Parity ΔES — gated on the parity span count (the same `_n` already used to gate `_p_value` and `_ci_*`).
  - Section 2 Conversion ΔES — gated on the conversion span count (same shape as parity).
  Recommended default: reuse `PVALUE_RELIABILITY_MIN_N = 10` from `app/services/endgame_service.py:205` for all 4 metrics — it's the existing floor that already gates `_p_value` and `_ci_*` on the same metrics, so percentile reuses the same gate to stay consistent. Planner is free to argue for a stricter per-metric floor if the CDF generation pipeline's inclusion floors (≥30 endgame AND ≥30 non-endgame for Endgame Score Gap; ≥20 entry spans for Achievable; ≥20 spans/bucket for Section 2 ΔES — see Phase 93 D-08 discretion list) reveal a sharper threshold for chip rendering. Document the chosen value(s) in PLAN.md.
- **D-11: `{metric_id}_percentile` field naming convention.** Nullable `float | None` in [0, 100]. Field names mirror the `MetricId` literal exactly:
  - `score_gap_percentile` (on `EndgameOverviewStats` or equivalent — alongside existing `score_gap`, `score_gap_p_value`, `score_gap_ci_low`, `score_gap_ci_high`).
  - `achievable_score_gap_percentile` (same schema, next to the existing `achievable_score_gap_*` fields).
  - `section2_score_gap_parity_percentile` (Section 2 schema, next to existing `section2_score_gap_parity_*` fields).
  - `section2_score_gap_conv_percentile` (Section 2 schema, next to existing `section2_score_gap_conv_*` fields).
  Additive nullable — does not disturb existing consumers (FE, LLM payload). No new schema files; planner places fields on the smallest set of existing schemas that already carry the sibling `_p_value` / `_ci_*` fields. (User opted not to re-discuss this gray area; SEED-019's "schema additive" default holds and the field-name convention follows the existing `_p_value` / `_ci_*` pattern on the same metrics.)

### Phase 93 inheritance (locked, not re-discussed)

- **D-12: 4-metric scope is fixed.** Endgame Score Gap, Achievable Score Gap, Section 2 Parity ΔES, Section 2 Conversion ΔES. No chip on Recovery ΔES (opponent-confounded, d=0.95 inverted). No chip on the 3 raw % gauges (redundant — same card's ΔES row is already chipped). No chip on per-type cards, timelines, or Time Pressure metrics. Inherited from Phase 93 / SEED-019 / `reports/benchmarks-gap-metrics-percentile-candidacy.md`.
- **D-13: Backend imports `interpolate_percentile` from `app/services/global_percentile_cdf.py`.** No re-implementation. The helper already returns `None` for out-of-scope metric IDs and for `NaN` input; the reliability gate is layered on top in the service / router layer.

### Claude's Discretion

The user picked chip styling + popover trigger as the only gray area worth a full discussion. The remaining decisions noted above default to the ROADMAP / SEED-019 / REQUIREMENTS path. The planner has flexibility on:

- The exact `theme.ts` constant names to reuse for the red / neutral / green chip bands (recommend reusing the existing gauge-zone palette to keep the visual language consistent — semantic danger / muted / success roles).
- The exact pill background opacity / contrast / padding / size (the `MetricStatPopover` and existing zone-band styling are reference points; planner picks values that pass the CLAUDE.md min font-size discipline and remain readable on mobile at 375px).
- Whether the flame icon stacks horizontally inline (`<Flame /><Flame /><Flame />`) or compresses (e.g. a single flame with a "×3" suffix). Recommend horizontal stacking up to 3 — three lucide flames at the chip's text-size are still compact and read instantly; "×3" needs explanation. Verify on mobile.
- The reliability-floor value (default `PVALUE_RELIABILITY_MIN_N = 10`, see D-10).
- Where the chip component lives — recommend a single new `frontend/src/components/charts/PercentileChip.tsx` (or `frontend/src/components/percentile/PercentileChip.tsx`) that both row components import, rather than inlining the chip markup in each row. The chip is non-trivial (banded color + flame logic + popover trigger + theme integration) and renders in 4 places, so it earns its own component.
- The exact popover copy strings (within `feedback_popover_copy_minimalism.md` discipline; cite `/benchmarks` semantics rather than re-deriving).
- Whether to add a UI test exercising the gate-below-N case (chip absent when `{metric}_percentile` is `null`) — recommend yes, as a single Vitest assertion per row.

These are HOW decisions inside the locked WHAT. Planner can resolve them in PLAN.md without coming back to the user, but should document the chosen shape briefly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source of truth
- `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` — canonical design doc for Phases 93/94/95. Includes the empirical refinement note, 4-metric scope, two-task split, popover framing rationale, and open decisions deferred to phase planning. **Note:** the seed's TS codegen guidance is superseded by Phase 93 D-01 (Python-only artifact, no TS mirror).
- `reports/benchmarks-gap-metrics-percentile-candidacy.md` (2026-05-22) — empirical pre-flight that justified the 4-metric scope, Recovery drop, and Conversion ΔES "improvement-focus" framing. Tier table downstream of this report.
- `.planning/REQUIREMENTS.md` §PCTL-02 / §PCTL-03 / §PCTL-04 / §PCTL-05 / §PCTL-06 — the user-facing milestone requirements Phase 94 fulfills.
- `.planning/ROADMAP.md` Phase 94 section — phase scope and success criteria.
- `.planning/phases/93-global-percentile-benchmark-artifact/93-CONTEXT.md` — Phase 93 hand-off, including D-01 (no TS mirror), D-04 (module path), and the discretion list shipped by the planner.

### Code touchpoints — backend
- `app/services/global_percentile_cdf.py` — Phase 93 output. Exports `GLOBAL_PERCENTILE_CDF: Mapping[CdfMetricId, CdfTable]` and `interpolate_percentile(metric_id: MetricId, value: float) -> float | None`. Phase 94 backend imports this helper; do NOT re-implement interpolation.
- `app/services/endgame_service.py:205` — `PVALUE_RELIABILITY_MIN_N = 10` lives here (NOT in `endgame_zones.py`, per Phase 93 CONTEXT correction of SEED-019 misattribution). Phase 94's chip gate reuses this constant by default (see D-10).
- `app/schemas/endgames.py` — defines the `MetricId` Literal that `interpolate_percentile` keys off of and that holds the existing per-metric `_n` / `_p_value` / `_ci_low` / `_ci_high` fields. Phase 94 grows the 4 nullable `*_percentile: float | None` siblings here. No new MetricId values.
- `app/services/endgame_service.py` — Phase 94 service-layer change site: compute percentile for each of the 4 metrics after the existing CI / p-value computation, gate by N, attach to the response struct.

### Code touchpoints — frontend
- `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` — 2 chips (Endgame Score Gap row + Achievable Score Gap row), desktop + mobile.
- `frontend/src/components/charts/EndgameMetricCard.tsx` — 2 chips on the ΔES bullet rows of the Parity and Conversion cards (Recovery card and all 3 raw % gauges unchanged), desktop + mobile.
- `frontend/src/components/popovers/MetricStatPopover.tsx` — existing hover/tap popover pattern (HelpCircle trigger). Phase 94 reuses the popover *shell* mechanics (Radix popover root, hover-open delay, portal + content positioning, fade/zoom animation classes) but the trigger is the chip itself, not a HelpCircle (D-01).
- `frontend/src/lib/theme.ts` — source of truth for ALL chip colors (red / neutral / green bands + flame icon color). No hard-coded color values per PCTL-05 and per CLAUDE.md Frontend §Code Style.
- `lucide-react` `Flame` icon — already a dependency; used for the top-10% / top-5% / top-1% tier escalation (D-03).

### Out of scope code (do NOT touch in Phase 94)
- `EndgameTypeCard.tsx` — per-type cards explicitly out of scope (sample-thin, deferred).
- `EndgameScoreOverTimeChart.tsx` / `EndgameEloTimelineSection.tsx` / `EndgameClockDiffOverTimeChart.tsx` — timelines (scalar percentile can't annotate a trend line; Endgame ELO Timeline is a logistic stretch of Score Gap, so already implicitly chipped via the page-level Score Gap row).
- `EndgameTimePressureSection.tsx` / `EndgameTimePressureCard.tsx` — Time Pressure metrics (direction ambiguous, deferred).
- `scripts/gen_endgame_zones_ts.py` / `frontend/src/generated/endgameZones.ts` — Phase 93 D-01 locked Python-only artifact; no TS mirror needed for Phase 94's request-time scalar emission.
- `app/services/endgame_zones.py` — ZoneSpec / IQR-band registry; unchanged shape; do NOT graft CDF tables into this file.

### Inherited from prior decisions / memories
- Project memory `feedback_popover_copy_minimalism.md` — popover prose covers WHAT + sign convention only (no jargon like "sigmoid" / "Wilson", no caveats). Phase 94 chip popovers must obey.
- Project memory `feedback_benchmark_source_of_truth.md` — `/benchmarks` is the source of truth for "typical"; the chip's "top X%" wording is downstream of the same source; verify popover normative copy against `reports/benchmarks-latest.md`.
- Project memory `feedback_llm_significance_signal.md` — do not add parallel sig-test signals; the chip surfaces the cohort comparison only. (Phase 95 handles LLM-side reasoning; Phase 94 does NOT add anything to the LLM payload — that's LLM-05's job.)
- Project memory `feedback_no_dev_db_reset_in_plans.md` — Phase 94 plan must not gate completion on `bin/reset_db.sh`. Verification must work against existing dev DB or flag as HUMAN-UAT.

### LLM hand-off (Phase 95, not this phase)
- `app/prompts/endgame_insights.md` / `_PROMPT_VERSION` in `app/services/insights_llm.py` — Phase 95 wires the chipped percentiles into the LLM payload + prompt. Phase 94 does NOT touch these files; it only exposes the API fields that Phase 95 will consume.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`interpolate_percentile(metric_id, value)` in `app/services/global_percentile_cdf.py`** — Phase 93 output. Returns `float | None` (None for out-of-scope IDs and NaN input). Backend uses this directly; no re-implementation.
- **`PVALUE_RELIABILITY_MIN_N = 10` in `app/services/endgame_service.py:205`** — existing minimum-N constant already used to gate `_p_value` and `_ci_*` on the same 4 metrics. Default reuse for the chip gate (D-10).
- **`MetricStatPopover` (Radix popover shell) at `frontend/src/components/popovers/MetricStatPopover.tsx`** — hover/tap shell with `HOVER_OPEN_DELAY_MS = 100`, Portal + Content side/sideOffset, animation classes. Phase 94 reuses the *shell mechanics* but swaps the HelpCircle trigger for the chip itself (D-01).
- **`theme.ts` semantic color tokens** — red / neutral / green band colors driven from `frontend/src/lib/theme.ts` (already the source of truth for the IQR zone-band palette on raw % gauges and ΔES rows). New chip palette reuses existing tokens; no new theme entries.
- **`lucide-react` `Flame` icon** — already a dependency, no new icon library.
- **Existing per-metric `_n` / `_p_value` / `_ci_*` field shape on `EndgameOverviewStats` and the Section 2 stats schema** — the `_percentile` fields land alongside this exact sibling group on the same schemas.

### Established Patterns
- **Per-metric MetricId Literal in `app/schemas/endgames.py`** — chip field naming follows the same `{metric_id}_<suffix>` convention used by `_p_value`, `_ci_low`, `_ci_high` on the same metrics.
- **Per-metric reliability gate emitting `None` to the wire** — backend already does this for `_p_value` / `_ci_*` when `n < PVALUE_RELIABILITY_MIN_N`. The new `_percentile` field uses the same gate semantics so the chip absence path is identical to the existing CI-absence path.
- **Banded color zones from `theme.ts`** — gauge zone bands on raw % gauges and ΔES rows already paint with semantic danger / muted / success tokens. The chip palette reuses this language.
- **Component-per-card-element discipline** — `MetricStatPopover` / `MetricStatTooltip` / `BulletConfidencePopover` / `ScoreGapPopover` etc. live as siblings under `frontend/src/components/popovers/`. New `PercentileChip` lives under `frontend/src/components/charts/` (or `frontend/src/components/percentile/`) and is imported by both `EndgameOverallScoreGapRow.tsx` and `EndgameMetricCard.tsx`.
- **Test scaffolding** — `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` etc. are the precedent for component-level Vitest rendering. New chip + gate-below-N tests follow this pattern.

### Integration Points
- **Backend service → schema**: `endgame_service.py` computes percentile via `interpolate_percentile(metric_id, value)`, gates by N, writes the result to the response model (`EndgameOverviewStats` for the page-level pair, Section 2 stats for parity / conv). No new repository / DB work.
- **Schema → frontend type**: TypeScript types are derived from the FastAPI OpenAPI schema (existing project pipeline); 4 new nullable optional fields appear on the frontend types automatically once the Pydantic schemas grow them.
- **Frontend row → chip**: `EndgameOverallScoreGapRow.tsx` and `EndgameMetricCard.tsx` consume the new nullable fields, conditionally render `<PercentileChip percentile={…} flavor="skill-isolating" | "improvement-focus" />` on the right edge of the row when the field is non-null.
- **No router changes**: existing endgame endpoints already return the response models that grow the new fields. No new endpoint, no new query parameter.
- **No migration**: pure compute-and-attach; no DB column changes.

</code_context>

<specifics>
## Specific Ideas

- **Flame icon tiers honest at p90 / p95 / p99 — not finer.** SEED-019 / Phase 93 D-06 bound the breakpoint set at p1..p99 (n≈20 observations per tail breakpoint, SE ~2-3pp at chip-rounding granularity). Top 0.5% / top 0.1% would not be honest at the current cohort and are excluded.
- **Chip on the right edge of the row, not adjacent to the value.** Reads as metadata. Inline same row on desktop; mobile keeps right-alignment but may wrap to a second line if space is tight.
- **Pill background with theme-driven fill** — same visual language as existing IQR zone bands paint cards, not a Tailwind-default badge color.
- **Both popover flavors visible side-by-side on the Stats page.** Endgame Score Gap chip (skill-isolating) + Conversion ΔES chip (improvement-focus) both render for any user whose sample clears both gates, so the two copy flavors must read as deliberate companions, not contradictions.

</specifics>

<deferred>
## Deferred Ideas

- **LLM payload + prompt rework consuming the percentiles** — Phase 95 (LLM-05). Phase 94 only exposes the API fields; Phase 95 wires them into the LLM payload and teaches the prompt to narrate them. Locked split per ROADMAP.
- **Per-type-card percentile chips** (rook / minor / pawn / queen / mixed) — out of scope for v1.19 per SEED-019 / REQUIREMENTS §Future Requirements (per-type samples are sample-thin). Revisit with a hard sample gate in a follow-on phase.
- **Opening Insights percentile annotations** — out of scope for v1.19; candidate for a future Opening Insights v2 milestone.
- **Recovery ΔES chip** — explicitly rejected (opponent-confounded, d=0.95 inverted). Re-considering would require a methodology change (e.g. opponent-strength normalization) — out of scope.
- **Client-side CDF viz** — sparkline of user's position on the global distribution, "what value puts me in the top X%" interactive widget. Would justify the Python→TS codegen mirror that Phase 93 D-01 deferred. No v1.19 requirement; revisit if/when a viz ships.
- **Percentile-aware sorting / filtering of the per-type cards** (e.g. "show me my weakest endgame type by percentile") — interesting but out of scope for v1.19; revisit alongside the per-type chip phase.
- **Conversion ΔES tail suppression / capping** — accepted as honest distribution per D-09; revisit only if user feedback flags the right tail as misleading after v1.19 ships.
- **Neutral "≈ average" band near the median** — rejected for v1.19 per D-07 (literal-render path); revisit if "top 49% / 51%" reads awkwardly in production after v1.19 ships.

</deferred>

---

*Phase: 94-backend-frontend-percentile-annotations*
*Context gathered: 2026-05-22*
