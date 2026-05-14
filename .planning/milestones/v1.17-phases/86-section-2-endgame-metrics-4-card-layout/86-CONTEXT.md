# Phase 86: Section 2 — Endgame Metrics 4-card layout - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace `EndgameScoreGapSection.tsx` (533 LOC: 4-gauge strip + eval-stratified WDL table) with **4 side-by-side cards** on lg+ (Conversion → Parity → Recovery → Endgame Skill), stacked on mobile. Single-bullet doctrine: each card carries one peer bullet (`You − Opp` vs 0) using the mirror-bucket opponent baseline. No cohort bullet.

Scope:
1. **New orchestrator + sibling cards** (per Phase 85's pattern): `EndgameMetricsSection.tsx` + `EndgameMetricCard.tsx` (Conv / Parity / Recov shared shell — gauge + games-count row + WDL bar + peer bullet) + `EndgameSkillCard.tsx` (Skill variant — gauge + games-count row + peer bullet, no WDL).
2. **Backend additions** for the Skill peer-bullet sig test (mirror Phase 85.1 pattern):
   - New helper `compute_skill_diff_test()` in `app/services/score_confidence.py`.
   - New fields on `ScoreGapMaterialResponse`: `skill`, `opp_skill`, `skill_diff_p_value`, `skill_diff_ci_low`, `skill_diff_ci_high`.
   - The frontend `endgameSkill()` helper at `EndgameScoreGapSection.tsx:155-165` is retired in favor of the server values.
3. **Peer-bullet sig test** on Conv / Parity / Recov cards: Wald-z on `userRate − opponentRate` per bucket, two-sided, gated on `MIN_OPPONENT_BASELINE_GAMES = 10`. Computation site TBD by planner (frontend reuse of the existing `opponentRate()` math, or backend addition per-bucket — flag at plan-phase).
4. **Per-card MetricStatPopover** replaces the section-level InfoPopover for sig + CI + per-metric explanation. The conceptual InfoPopover (bucket taxonomy + mirror-bucket interpretation) moves up to the page-level h2 "Endgame Metrics and ELO" trigger at `Endgames.tsx:458`.
5. **Removal:** delete `EndgameScoreGapSection.tsx` entirely (knip-clean) — both the gauge strip and the eval-stratified WDL table go.
6. **Polish (POLISH-01, POLISH-02) explicitly deferred to Phase 88:** peer-bullet neutral band stays `±0.05` and gauge sig-gating stays always-colored.

**Out of scope:** Cell-specific peer-bullet neutral bands (POLISH-01 / Phase 88), gauge sig gating (POLISH-02 / Phase 88), per-type Section 3 cards (Phase 87), changes to `EndgameEloTimelineSection`, changes to the legacy `endgame_elo` ELO timeline composite (which uses its own server-side Skill computation already).

</domain>

<spec_lock>
## Locked Requirements (v1.17 REQUIREMENTS.md, SEC2)

SEC2-01..04, SEC2-06..10 cover this phase. The acceptance criteria below derive directly from those rows — discussion captures only **how** to implement, not whether to deliver them. Downstream agents MUST re-read `.planning/REQUIREMENTS.md` lines 28-40 before planning.

- SEC2-01: 4 cards in order Conv → Parity → Recov → Skill.
- SEC2-02: Conv/Parity/Recov layout = gauge → percent + games → WDL → peer bullet `You − Opp` vs 0.
- SEC2-03: Skill layout = gauge → percent + games → peer bullet `Your Skill − Opp Skill` vs 0 (no WDL).
- SEC2-04: Gauge bands per card use `FIXED_GAUGE_ZONES.{conversion,parity,recovery}` (p25/p75) unchanged.
- SEC2-06: Peer bullets use mirror-bucket rates (`Opp Conv = 1 − myRecov`, `Opp Recov = 1 − myConv`, `Opp Parity = 1 − myParity`, `Opp Skill = composite(1−myRecov, 1−myConv, 1−myParity)`).
- SEC2-07: Mirror-bucket peer baseline logic preserved.
- SEC2-08: Skill peer-bullet sig-test methodology — **LOCKED in D-01 below**.
- SEC2-09: Per-bullet `MetricStatPopover` explains mirror-bucket interpretation + filter-responsiveness.
- SEC2-10: Legacy `EndgameScoreGapSection` table + 4-gauge strip removed (knip clean).

</spec_lock>

<decisions>
## Implementation Decisions

### Skill peer-bullet sig test (SEC2-08, LOCKED)

- **D-01: Wald-z on aggregate diff with empirical trinomial variance, computed backend.** Mirrors the Phase 85.1 pattern: math helpers live in `app/services/score_confidence.py`, schema fields on `ScoreGapMaterialResponse`, frontend reads server values.
  - **Math:** `Your Skill = mean(userRate(conversion), userRate(parity), userRate(recovery))` over active buckets (games > 0). `Opp Skill = mean(1 − userRate(recovery), 1 − userRate(parity), 1 − userRate(conversion))` over the same active buckets. SE_user = `sqrt(sum(var_bucket / n_bucket)) / n_active` where `var_bucket = max(0, (W + 0.25·D) / n − score²)` (the same trinomial variance used in `compute_score_difference_test`). Same for opp using the mirror bucket's variance. `SE_diff = sqrt(SE_user² + SE_opp²)`. `z = (skill − opp_skill) / SE_diff`. P-value = `erfc(|z| / sqrt(2))`. CI = `diff ± 1.96·SE_diff`.
  - **Helper name:** `compute_skill_diff_test(conv_row, parity_row, recov_row, opp_conv_row, opp_parity_row, opp_recov_row) -> tuple[float | None, float | None, float | None, float | None, float | None]` returning `(skill, opp_skill, p_value, ci_low, ci_high)`. Signature is the **per-bucket aggregate** form — pass W/D/L counts per bucket, not pre-computed rates, so the variance reconstruction stays on the helper.
  - **Gating:** p_value and CI return `None` when fewer than 2 buckets are active (composite undefined) OR when any active opponent component has `mirror_games < MIN_OPPONENT_BASELINE_GAMES = 10`.
  - **Independence caveat:** the Conv and Recov mirror identities share games at the opponent level (your Recov games are opponent's Conv games), so treating bucket variances as independent over-estimates precision slightly. Acceptable for v1.17 — flag in plan-phase if the planner wants to revisit. The Skill metric is a heuristic composite to begin with, so high-fidelity stats on it is false precision.

- **D-02: Schema additions** to `ScoreGapMaterialResponse` (`app/schemas/endgames.py:285-303`), all required `float | None`:
  - `skill: float | None` — composite of active per-bucket user rates.
  - `opp_skill: float | None` — composite of active per-bucket mirror opponent rates.
  - `skill_diff_p_value: float | None` — gated per D-01.
  - `skill_diff_ci_low: float | None` / `skill_diff_ci_high: float | None` — Wald CI on the diff, gated per D-01.
  Field order: append at the end of the model. No defaults (consistent with the rest of the schema).

- **D-03: Service wiring site.** Add the call in `_compute_score_gap_material` in `app/services/endgame_service.py` (the same place that produces `MaterialRow` opponent_score fields per Phase 60). The accumulator already has per-bucket W/D/L; no new DB query. Comment block citing Phase 86 + SEC2-08 + D-01.

- **D-04: Frontend retirement.** Delete `endgameSkill()` at `EndgameScoreGapSection.tsx:155-165` along with the rest of the file. The new `EndgameSkillCard` reads `data.skill`, `data.opp_skill`, and the three sig fields from `ScoreGapMaterialResponse` directly. The skill formula now has a single source of truth (backend).

> **Milestone-boundary note (flag to planner):** The v1.17 ROADMAP description says "Frontend-only refactor". D-01..D-03 add 5 fields + 1 helper to the backend, mirroring Phase 85's D-01 caveat. The user authorized it at discuss-phase. Plan-phase should note this in the plan summary and the milestone description should be amended (or rolled into the existing Phase 85 amendment) at phase close.

### Peer-bullet sig test for Conv / Parity / Recov (LOCKED)

- **D-05: Wald-z per bucket on `userRate − opponentRate`** with the same trinomial variance per side. Two-sided p-value, 95% CI on the diff. Gated on `opponent_games >= MIN_OPPONENT_BASELINE_GAMES = 10` (matches existing `EndgameScoreGapSection.tsx:53`).
- **D-06: Computation site — backend, on `MaterialRow`** (recommended) or **frontend, in a new `lib/endgameDiffTest.ts` helper** (alternative). Planner picks at plan-phase. Recommend backend for consistency with D-01..D-03 and Phase 85.1; the existing trinomial variance helper already exists, so adding three more fields (`diff_p_value`, `diff_ci_low`, `diff_ci_high`) per `MaterialRow` is mechanical. If the planner decides frontend, the FE helper signature is `computeDiffTest(myRow: MaterialRow, oppRow: MaterialRow) -> { pValue, ciLow, ciHigh }` reusing the same variance formula.

### Component file structure (LOCKED)

- **D-07: Sibling-component pattern, mirroring Phase 85.**
  - `frontend/src/components/charts/EndgameMetricsSection.tsx` — orchestrator. Reads `scoreGap` + (if D-01 plumbs them via `ScoreGapMaterialResponse`) skill fields. Renders the 4-card grid.
  - `frontend/src/components/charts/EndgameMetricCard.tsx` — shared shell for Conv / Parity / Recov. Props-driven: `{ bucket: MaterialBucket; row: MaterialRow; mirror: MaterialRow | undefined; sharePct: number; metricName: string; metricExplanation: ReactNode }`. Renders gauge + games-count row + WDL bar + peer bullet + `MetricStatPopover`.
  - `frontend/src/components/charts/EndgameSkillCard.tsx` — Skill variant. Props: `{ skill: number | null; oppSkill: number | null; activeGames: number; pValue: number | null; ciLow: number | null; ciHigh: number | null }`. Gauge + games-count row + peer bullet + `MetricStatPopover`. **No WDL bar** (single-ply composite, no W/D/L definable).
- **D-08: Lift shared helpers to a new `frontend/src/lib/endgameMetrics.ts`** (lifted from `EndgameScoreGapSection.tsx`): `MIRROR_BUCKET`, `userRate`, `opponentRate`, `formatScorePct`, `formatDiffPct`, `BUCKET_DISPLAY_LABELS`, `BUCKET_DISPLAY_LABELS_WITH_METRIC`. Phase 87 will reuse these for per-type cards.

### Card grid layout (LOCKED)

- **D-09: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`** — mobile 1-col, tablet 2x2, desktop 4-up. Order: Conv → Parity → Recov → Skill. Card titles wrap at 1024-1100px is acceptable; gauges stay legible.

### Section header treatment (LOCKED)

- **D-10: Drop the section-level h3 + InfoPopover.** Keep only the section sub-question line under the page-level h2 "Endgame Metrics and ELO":

  > Do you outperform your opponents at converting, holding, and recovering?

  (Replaces the legacy "How well do you convert a winning endgame into a win, and recover when you're losing?" — the new phrasing matches the peer-frame story Section 2 now tells. Planner may revisit copy.)

- **D-11: Move the bucket-taxonomy + mirror-bucket explainer InfoPopover up to the page-level h2 "Endgame Metrics and ELO" trigger** (`Endgames.tsx:458`). The lifted popover content covers both Section 2 and the ELO timeline that lives under the same h2 (the ELO composite uses the same Skill metric, so the explainer is dual-purpose). Add an `InfoPopover` next to the h2 with content adapted from `EndgameScoreGapSection.tsx:184-235`. The h2 InfoPopover is **net-new** scope at Phase 86 — Plan-phase needs a small Endgames.tsx edit beyond the section swap.

### Peer-bullet neutral band & gauge sig gating (DEFERRED to Phase 88)

- **D-12: Reuse existing `NEUTRAL_ZONE_MIN/MAX = ±0.05` and `BULLET_DOMAIN = 0.20`** from `EndgameScoreGapSection.tsx:42-48`, lifted into `lib/endgameMetrics.ts`. POLISH-01 explicitly defers cell-specific bands to Phase 88; do not derive `CONV_DIFF_NEUTRAL_*` / `RECOV_DIFF_NEUTRAL_*` in this phase.
- **D-13: Gauges stay always-colored** (current behavior). POLISH-02 explicitly defers any gauge sig gating to Phase 88. The font-color sig gating applies only to the **diff percent** in the peer-bullet row (matches Phase 85's per-card score-row pattern).

### Sub-bullet sig-gating triple (LOCKED — Phase 85 carry-over)

- **D-14: Font-color gate** on the peer-bullet diff percent uses Phase 85's `deriveLevel(pValue, n)` + `isConfident(level)` + outside-neutral-band triple (see `EndgameOverallShared.ts`, also at `EndgameStartVsEndSection.tsx:73-78`). The `n` here is `MIN_OPPONENT_BASELINE_GAMES` (= 10) per the existing convention.

### Games-count display (LOCKED)

- **D-15: Match Phase 85's pattern** at `EndgameOverallCard.tsx:88-100`: `Games: {sharePct}% ({total.toLocaleString()})` with the `Swords` icon. `sharePct` for Conv/Parity/Recov = `row.games / totalMaterialGames` (preserve existing semantics from `EndgameScoreGapSection.tsx:330-333`). Skill card uses `totalMaterialGames` directly (no share since it spans all buckets).

### MetricStatPopover content (LOCKED — Claude's Discretion)

- **D-16:** Per-card `MetricStatPopover` content follows Phase 85's pattern (`EndgameOverallPerformanceSection.tsx:168-191`). One short paragraph per metric:
  - **Conversion:** "Your win rate (only wins count) when you entered the endgame with a Stockfish eval ≥ +1.0, compared to your opponents in the mirror bucket. Filter-responsive."
  - **Parity:** "Your chess score (wins + ½ draws) when you entered the endgame with an eval between −1.0 and +1.0, compared to your opponents in the mirror bucket. Filter-responsive."
  - **Recovery:** "Your save rate (wins + draws count) when you entered the endgame with an eval ≤ −1.0, compared to your opponents in the mirror bucket. Filter-responsive."
  - **Endgame Skill:** "A composite of your Conversion, Parity, and Recovery rates compared to the same composite for your opponents in the mirror bucket. One-number summary of overall endgame proficiency."
  Methodology block: "Score: per-bucket headline rate (Conv = wins, Parity = wins + ½ draws, Recov = wins + draws). Test: Wald-z on the signed difference vs 0. Confidence interval: 95% normal-approx on the diff."

### Skill card empty-state (LOCKED — Claude's Discretion)

- **D-17:** When fewer than 2 buckets are active (rare — only happens with extremely sparse data), show `"Not enough data yet"` per Phase 85 convention (`EndgameOverallCard.tsx:110`). The gauge stays at 0% with `opacity-50` like the existing Skill gauge fallback at `EndgameScoreGapSection.tsx:277, 515`.

### Claude's Discretion

- **Peer-bullet sig-test computation site (D-06).** Recommend backend for Conv/Parity/Recov diff fields (mirror D-01). Planner picks at plan-phase based on whether the existing `_compute_score_gap_material` site can host the additional fields cleanly.
- **Test placement.** Backend Skill test goes in `tests/test_score_confidence.py` (new `TestComputeSkillDiffTest` class) alongside the Phase 85.1 helpers. Frontend tests live in `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx` and per-card test files.
- **`EndgameEloTimelineSection` color story.** The page-level h2 InfoPopover relocation in D-11 means the ELO timeline section visually inherits the explainer. Planner should verify no current ELO-section-specific InfoPopover content is lost; if there is one, decide whether to merge into the h2-level popover or keep an ELO-specific one inside the section.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.17 spec & roadmap
- `.planning/REQUIREMENTS.md` lines 28-40 — SEC2-01 through SEC2-10 (the nine Section 2 requirements).
- `.planning/milestones/v1.17-ROADMAP.md` §Phase 86 — success criteria, card ordering (Conv → Parity → Recov → Skill), legacy removal mandate.
- `.planning/notes/v1.17-single-bullet-doctrine.md` — pivot rationale; explains why cohort bullets were dropped from Section 2.

### Pattern templates (LOCKED — replicate these)
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` — Phase 85 orchestrator pattern: imports sibling card components, derives per-card values from one response, renders a responsive grid.
- `frontend/src/components/charts/EndgameOverallCard.tsx` — Phase 85 per-card shell pattern: `charcoal-texture rounded-md p-4` tile, `flex flex-col gap-4` body, games-count row with `Swords` icon, `MetricStatPopover` for sig/CI/explainer.
- `frontend/src/components/charts/EndgameOverallShared.ts` — `deriveLevel`, `ENDGAME_TILE_SCORE_DOMAIN`. Reuse `deriveLevel` for the peer-bullet diff font-color gate.
- `frontend/src/components/popovers/MetricStatPopover.tsx` — popover with name + explanation + value + baseline + gameCount + level + pValue + neutral band + methodology.

### Legacy to be deleted
- `frontend/src/components/charts/EndgameScoreGapSection.tsx:1-533` — entire file. Per D-08 lift `MIRROR_BUCKET`, `userRate`, `opponentRate`, `BUCKET_DISPLAY_LABELS`, `BUCKET_DISPLAY_LABELS_WITH_METRIC`, `formatScorePct`, `formatDiffPct`, `NEUTRAL_ZONE_MIN/MAX`, `BULLET_DOMAIN`, `MIN_OPPONENT_BASELINE_GAMES` to `frontend/src/lib/endgameMetrics.ts` before deletion. Per D-04 retire `endgameSkill()` entirely (server-side replacement via D-01).
- `frontend/src/pages/Endgames.tsx:458-461` — mount swap site: `<EndgameScoreGapSection data={scoreGapData} />` → `<EndgameMetricsSection data={scoreGapData} />`. Also at this site: add the page-level h2 InfoPopover per D-11.

### Reusable components & utilities
- `frontend/src/components/charts/EndgameGauge.tsx` — gauge primitive. Reuse for all 4 cards.
- `frontend/src/components/charts/MiniBulletChart.tsx` — bullet primitive for the peer-bullet row.
- `frontend/src/components/stats/MiniWDLBar.tsx` — per-card WDL bar (Conv/Parity/Recov only).
- `frontend/src/lib/theme.ts` — `MIN_GAMES_FOR_RELIABLE_STATS = 10`, `ZONE_DANGER`, `ZONE_NEUTRAL`, `ZONE_SUCCESS`, `colorizeGaugeZones`.
- `frontend/src/lib/significance.ts` — `isConfident(level)`.
- `frontend/src/generated/endgameZones.ts` — `FIXED_GAUGE_ZONES.{conversion,parity,recovery}`, `ENDGAME_SKILL_ZONES`, `SCORE_GAP_NEUTRAL_MIN/MAX`.

### Backend additive fields (D-01..D-03)
- `app/schemas/endgames.py:285-303` — `ScoreGapMaterialResponse` schema (extend with 5 new fields per D-02).
- `app/services/endgame_service.py` — `_compute_score_gap_material` (the function that builds `material_rows` and computes `score_difference` per Phase 60). Add the Skill computation here.
- `app/services/score_confidence.py:161-243` — `compute_score_difference_test` + `compute_paired_difference_test` (Phase 85.1 helpers). Add `compute_skill_diff_test` alongside.
- `tests/test_score_confidence.py` — Phase 85.1 boundary tests for the existing two helpers. Add `TestComputeSkillDiffTest` (symmetric 50/50, asymmetric, one-bucket-active, sparse-opponent-gating, no-active-buckets safety).
- `frontend/src/types/endgames.ts` — extend `ScoreGapMaterialResponse` TS type with the 5 new fields (mirror `EndgamePerformanceResponse` extension in Phase 85.1).

### Wire shape (already populated for Conv/Parity/Recov)
- `frontend/src/types/endgames.ts` — `MaterialRow` with `opponent_score`, `opponent_games` already on the wire per Phase 60. Phase 86 reads these directly for the per-card peer bullets.
- `frontend/src/types/endgames.ts` — `ScoreGapMaterialResponse.material_rows` already loaded by the existing overview query in `Endgames.tsx`. No new query.

### Prior phase context
- `.planning/milestones/v1.17-phases/85-section-1-games-with-vs-without-endgame-cards/85-CONTEXT.md` — Phase 85 sibling-component pattern, MetricStatPopover usage, sig-gating triple convention. **Direct precedent for Phase 86.**
- `.planning/milestones/v1.17-phases/85.1-hypothesis-tests-and-cis-for-endgame-score-differences/85.1-DECISIONS.md` — Phase 85.1 backend math helper pattern (`compute_score_difference_test`, `compute_paired_difference_test`). **Direct precedent for D-01 backend placement.**
- `.planning/milestones/v1.17-phases/84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit/84-CONTEXT.md` — Phase 84 mirror-bucket audit confirming `opponent_score` + `opponent_games` are already on the wire for Conv/Parity/Recov.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 85's sibling-component scaffold** (`EndgameOverallPerformanceSection.tsx` + sibling cards) — direct template for Phase 86's orchestrator + cards.
- **`EndgameGauge`** — gauge primitive already used by `EndgameScoreGapSection`. No changes needed.
- **`MetricStatPopover`** — Phase 85's locked popover component. Replaces the section-level `InfoPopover` for per-card sig/CI.
- **`MIRROR_BUCKET` + `userRate()` + `opponentRate()`** at `EndgameScoreGapSection.tsx:111-146` — verbatim lift to `lib/endgameMetrics.ts`. Phase 87 will reuse for per-type cards.
- **`compute_score_difference_test` + `compute_paired_difference_test`** at `app/services/score_confidence.py:161+` — Phase 85.1 helpers. New `compute_skill_diff_test` slots in alongside, sharing the trinomial-variance pattern.
- **`FIXED_GAUGE_ZONES.{conversion,parity,recovery}` + `ENDGAME_SKILL_ZONES`** at `frontend/src/generated/endgameZones.ts` — gauge bands already calibrated. No regeneration.

### Established Patterns
- **`charcoal-texture rounded-md p-4`** tile container (Phase 81+ convention). All 4 cards reuse this class set.
- **`flex flex-col gap-4`** vertical stack inside each tile (separates rows).
- **Sig-gating triple** (`isConfident(level) ∧ outside-neutral-band ∧ n >= threshold`): Phase 85 convention. Applied to the peer-bullet diff percent font color (not the gauge, not the WDL bar).
- **Page-level h2 + sub-question + InfoPopover trigger** — Phase 85 dropped the section-level h3 in favor of this. Phase 86 D-10/D-11 carry the convention forward; the lifted Section-2 InfoPopover content now sits next to the h2.
- **Mirror-bucket symmetry** (Phase 60): `opp_wins[X] = user_losses[mirror(X)]`; the existing trinomial variance helper at `score_confidence.py:174-178` extends to the per-bucket case naturally.

### Integration Points
- **`Endgames.tsx:458-461`** — section mount + new h2 InfoPopover trigger.
- **`app/services/endgame_service.py:_compute_score_gap_material`** — backend wiring for D-01..D-03 (Skill + diff test) and optionally D-06 (per-MaterialRow diff fields).
- **`app/schemas/endgames.py` `ScoreGapMaterialResponse`** — schema extension for 5 new Skill fields (and optionally 3 new per-MaterialRow diff fields if D-06 → backend).
- **knip CI** — must pass after `EndgameScoreGapSection.tsx` deletion. Verify with `npm run knip`.

### Sentry
- No new exceptional paths. The Skill diff test reuses the variance + erfc + Wald patterns already present at Phase 85.1. All arithmetic is guarded by the per-bucket `n > 0` check and the `min_opponent_baseline_games` gate.

</code_context>

<specifics>
## Specific Ideas

- **Component file names:** `EndgameMetricsSection.tsx`, `EndgameMetricCard.tsx`, `EndgameSkillCard.tsx`.
- **Helper module:** `frontend/src/lib/endgameMetrics.ts` for `MIRROR_BUCKET`, `userRate`, `opponentRate`, `formatScorePct`, `formatDiffPct`, label maps, neutral-band/domain constants.
- **Backend helper:** `compute_skill_diff_test()` in `app/services/score_confidence.py` alongside `compute_score_difference_test` and `compute_paired_difference_test`.
- **Schema fields** on `ScoreGapMaterialResponse`: `skill`, `opp_skill`, `skill_diff_p_value`, `skill_diff_ci_low`, `skill_diff_ci_high` (all `float | None`).
- **Sub-question copy:** "Do you outperform your opponents at converting, holding, and recovering?" (planner may revisit).
- **h2 InfoPopover content:** adapt from `EndgameScoreGapSection.tsx:184-235` (the existing section-level explainer). Add a one-liner about the ELO timeline below it: the ELO composite uses the same Skill metric.
- **Comment in new components** referencing Phase 86 + single-bullet doctrine, matching the Phase 85 header block pattern at `EndgameOverallPerformanceSection.tsx:1-23`.

</specifics>

<deferred>
## Deferred Ideas

- **Cell-specific peer-bullet neutral bands** (POLISH-01) — Phase 88 scope. Until then, ±0.05 stays.
- **Gauge sig gating** (POLISH-02) — Phase 88 scope. Gauges stay always-colored until then.
- **Independence-aware Skill diff variance** — D-01 uses the simple per-bucket variance sum; a future iteration could account for the shared-game correlation across Conv/Recov mirror identities. False precision for a heuristic composite; defer.
- **Per-class Skill metric** (Section 3) — out of scope per REQUIREMENTS.md; Skill is a global composite only.
- **Section-level merging with `EndgameEloTimelineSection`** — D-11 hints at this by lifting the InfoPopover to the shared h2, but the two sections stay as separate components for now.
- **Frontend-side diff test for Conv/Parity/Recov** — D-06 leans backend; if planner picks frontend, document the choice and update plan-phase scope.
- **Removing `EndgameStartVsEndSection.tsx` and `EndgamePerformanceSection.tsx`** — already deleted at Phase 85; nothing carries over here.

</deferred>

---

*Phase: 86-section-2-endgame-metrics-4-card-layout*
*Context gathered: 2026-05-14*
