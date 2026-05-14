# Phase 87: Section 3 — Per-type Endgame Type Breakdown cards - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the legacy `EndgameWDLChart.tsx` (per-type WDL table + score-gap bullet) and `EndgameConvRecovChart.tsx` (per-type gauge-only mini cards) with **5 unified per-type cards** (rook / minor_piece / pawn / queen / mixed; pawnless hidden via the existing `HIDDEN_ENDGAME_CLASSES` set in `Endgames.tsx:53`) laid out in a responsive grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`). Each card carries:

1. Title row: class label + per-card title `InfoPopover` (one-sentence type description, lifted from `ENDGAME_TYPE_DESCRIPTIONS` in `EndgameWDLChart.tsx:30-37`) + Games deep-link (`Games: {sharePct}% ({count})` + `Swords` icon, navigates to `/endgames/games?type=…`).
2. Side-by-side gauge row: Conv gauge | Recov gauge using `PER_CLASS_GAUGE_ZONES[class].{conversion,recovery}` (p25/p75 — already in codegen registry from Phase 84 / DATA-02).
3. Full-game WDL bar (`MiniWDLBar` reading per-class `win_pct/draw_pct/loss_pct` from `EndgameCategoryStats`). Subject to mobile real-device fallback flag (`SHOW_WDL_BAR_IN_TYPE_CARDS`, see D-04).
4. Conv peer bullet row: `Conversion — You / Opp / Gap` + `MiniBulletChart` (signed `userConv − oppConv` vs 0) + per-bullet `MetricStatPopover` (methodology + CI + sig).
5. Recov peer bullet row: `Recovery — You / Opp / Gap` + `MiniBulletChart` + per-bullet `MetricStatPopover`.

Mirror-metric peer baseline applied per class (NOT per row): `opp_conv = 1 − user_recov` (uses user's per-class recovery W/D/L flipped), `opp_recov = 1 − user_conv` (uses user's per-class conversion W/D/L flipped). Identical semantics to Phase 86 `MIRROR_BUCKET`, applied per endgame class instead of across material buckets. Gated on per-class `MIN_OPPONENT_BASELINE_GAMES = 10` (recovery_games for the Conv bullet's opp; conversion_games for the Recov bullet's opp); sparse-n indicator shown when threshold not met.

Single-bullet doctrine: each peer bullet is `You − Opp` vs 0. No cohort bullets. No `Your Skill` composite at the per-type level (composite Skill stays at Section 2 page-level).

**Out of scope:**
- POLISH-01 (cell-specific peer-bullet neutral bands) — Phase 88. Until then, ±0.05 stays.
- POLISH-02 (gauge sig gating) — Phase 88. Gauges stay always-colored.
- POLISH-03 / POLISH-04 (consistent `data-testid` / ARIA / 375px audit) — Phase 88.
- Cross-type WDL aggregate view — reconstructable by scanning per-card WDL bars (SEC3-06).
- Backend changes to `_classify_endgame_bucket` / `phase` column / Stockfish eval (v1.15 stack untouched).

</domain>

<spec_lock>
## Locked Requirements (v1.17 REQUIREMENTS.md, SEC3)

SEC3-01, SEC3-02, SEC3-04, SEC3-05, SEC3-06, SEC3-07 cover this phase. The acceptance criteria below derive directly from those rows — discussion captures only **how** to implement, not whether to deliver them. Downstream agents MUST re-read `.planning/REQUIREMENTS.md` (SEC3 block) before planning.

- SEC3-01: 5 per-type cards in `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`; pawnless hidden via `HIDDEN_ENDGAME_CLASSES`.
- SEC3-02: Per-card composition = side-by-side Conv + Recov gauges + WDL bar + Conv peer bullet + Recov peer bullet + Games deep-link. No cohort bullets.
- SEC3-04: Per-class mirror-metric peer baseline gated on `MIN_OPPONENT_BASELINE_GAMES` per type with sparse-n indicator.
- SEC3-05: Mobile real-device density check during execute; if dense, fallback drops the WDL bar (not the peer bullets).
- SEC3-06: Legacy `EndgameWDLChart` removed; cross-type comparison reconstructable from per-card WDL bars.
- SEC3-07: `EndgameConvRecovChart` extended into the per-type card shell — no separate gauge-only chart component remains.

</spec_lock>

<decisions>
## Implementation Decisions

User direction at discuss-phase: **"Be consistent with the Phase 86 Endgame Metrics rework, the rest is up to you."** Decisions below mirror the Phase 86 pattern per-class.

### Peer-bullet sig test (LOCKED — backend wire-up, Phase 86 parity)

- **D-01: Backend per-class Conv + Recov diff fields** (mirrors Phase 86 D-01..D-03, D-05/D-06).
  - Add to `ConversionRecoveryStats` schema (`app/schemas/endgames.py`): `opp_conversion_pct: float | None`, `opp_recovery_pct: float | None`, `opp_conversion_games: int`, `opp_recovery_games: int`, `conv_diff_p_value: float | None`, `conv_diff_ci_low: float | None`, `conv_diff_ci_high: float | None`, `recov_diff_p_value: float | None`, `recov_diff_ci_low: float | None`, `recov_diff_ci_high: float | None`.
  - **Math per class:**
    - **Conv peer-diff:** user side = `(conversion_wins, conversion_draws, conversion_losses, conversion_games)`; opponent side = the SAME class's recovery W/D/L with W↔L flipped (mirror-metric symmetry): `(recovery_losses, recovery_draws, recovery_wins, recovery_games)`. Both sides plug into the existing `compute_score_difference_test()` helper at `app/services/score_confidence.py:255`. The "score" returned by that helper IS the rate per metric (Conv = wins/n, but since we want `userConv − oppConv = winRate_user − (1 − winRate_user_recovery)`, the helper's diff-of-rates output applies directly when we feed it the flipped W/D/L counts). `opp_conversion_pct = 1 − recovery_wins/recovery_games` (the loss-rate in recovery; matches Phase 86 `opponentRate` in `lib/endgameMetrics.ts:90-95`).
    - **Recov peer-diff:** user side = `(recovery_wins + recovery_draws, 0, recovery_losses, recovery_games)` if we treat saves as W. Cleanest path: redefine the helper call to operate on the chess-score directly — but for backward compatibility with Phase 86 D-01, follow the same per-bucket convention used there: feed the helper raw W/D/L; the helper computes chess-score per side and the diff. For Recov, the user's "headline rate" is `(W+D)/n`, so map: user W' = `recovery_wins + recovery_draws`, user D' = 0, user L' = `recovery_losses`. Opp side: opp's recovery = `(opp wins + opp draws)/n` in the same class's conversion bucket = `(conversion_losses + conversion_draws)/conversion_games`. Mapped: opp W' = `conversion_losses + conversion_draws`, opp D' = 0, opp L' = `conversion_wins`, opp n' = `conversion_games`.
    - Both diff tests reuse the existing `compute_score_difference_test()` helper — no new math primitive. (This is simpler than Phase 86's `compute_skill_diff_test`, which is a composite over three buckets; here we only have two per-class metrics each handled by a single per-side WDL.)
  - **Service wiring site:** the existing `categories` builder in `app/services/endgame_service.py` (or wherever `EndgameCategoryStats` rows are assembled). The accumulator already has per-class `conversion_wins/draws/losses` + `recovery_wins/draws/losses` per the existing `ConversionRecoveryStats` shape; no new DB query. Add the two diff-test calls per class inside the existing loop. Comment block citing Phase 87 + SEC3-04 + D-01.
  - **TS types mirror:** extend `frontend/src/types/endgames.ts` `ConversionRecoveryStats` with the same 10 new fields.
  - **Rationale:** Phase 86 consolidated sig-test logic server-side via `score_confidence.py`. Computing Wald-z client-side per class would duplicate that consolidation; backend wire-up keeps the single source of truth and matches the user's "be consistent" directive.

- **D-02: Reuse `compute_score_difference_test`** directly. Do NOT introduce a `compute_per_class_diff_test` helper unless the call sites need argument re-shaping; the helper's `(eg_w, eg_d, eg_l, eg_n, ne_w, ne_d, ne_l, ne_n) -> (p, ci_low, ci_high)` signature is exactly what we need with mirror-flipped opponent W/D/L. Planner may choose to add a thin per-class wrapper for readability (`_compute_conv_recov_peer_diff(category) -> tuple of two diff results`) but no new statistical math.

### Component file structure (LOCKED — sibling-component pattern, Phase 86 parity)

- **D-03: Fresh files, mirror Phase 86 `EndgameMetricsSection` + `EndgameMetricCard` pattern.**
  - `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` — orchestrator. Filters categories via `HIDDEN_ENDGAME_CLASSES`, computes per-class `sharePct` (`cat.total / totalGames * 100`), renders the responsive grid, mounts one `<EndgameTypeCard>` per surviving class. Carries the section's page-level h2 / sub-question / `InfoPopover` per D-06.
  - `frontend/src/components/charts/EndgameTypeCard.tsx` — per-class card shell. Props: `{ category: EndgameCategoryStats; sharePct: number; onCategorySelect: (cls: EndgameClass) => void; tileTestId: string }`. Renders title row + Games deep-link + side-by-side gauges row + WDL bar (gated by `SHOW_WDL_BAR_IN_TYPE_CARDS` per D-04) + Conv peer-bullet row + Recov peer-bullet row.
  - Delete `frontend/src/components/charts/EndgameWDLChart.tsx` (352 LOC) and `frontend/src/components/charts/EndgameConvRecovChart.tsx` (135 LOC) at the end of the plan sweep. SEC3-06 / SEC3-07.

- **D-04: Mobile WDL-bar fallback flag.** Hard-coded constant `SHOW_WDL_BAR_IN_TYPE_CARDS: boolean` (default `true`), exported from `frontend/src/lib/endgameMetrics.ts`. The real-device density check during execute (HUMAN-UAT step) determines whether to flip to `false` before merge. If `false`, the `MiniWDLBar` row simply renders nothing (no breakpoint hide — the Conv + Recov gauges already encode most of the cross-class WDL signal; a CSS-only hide on `<lg` would leave the desktop bar but kill it on mobile, creating layout inconsistency the user already rejected). Document the decision in `87-HUMAN-UAT.md` and update the page-level h2 `InfoPopover` copy accordingly if the flag flips. POLISH-04 (375px parity) is Phase 88, so the fallback decision in Phase 87 is the WDL-bar drop only.

- **D-05: Component file naming.** Final names locked:
  - `EndgameTypeBreakdownSection.tsx` (orchestrator). Replaces both legacy components.
  - `EndgameTypeCard.tsx` (per-class card shell).
  - No connector-arrows component for this section (Section 3 has no composite/parent card to point to — the page-level Endgame Skill in Section 2 is already a separate visual story).

### Card grid layout (LOCKED)

- **D-06: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`** on the orchestrator. Matches the existing `EndgameConvRecovChart` grid at `EndgameConvRecovChart.tsx:65` (the legacy file already uses this exact grid, validated by prior phases). 5 cards lay out as:
  - lg+: row 1 = 3 cards, row 2 = 2 cards (left-aligned, last column empty)
  - sm: row 1 = 2 cards, row 2 = 2 cards, row 3 = 1 card
  - mobile: stacked single column
- No `lg:col-start-X` placement tricks needed — natural flow is fine since there's no composite/target card below.

### Per-card layout (LOCKED — top-to-bottom)

- **D-07: Element order inside each card** (mirrors Phase 86 `EndgameMetricCard` structure):

  ```
  <h3>{cat.label}  <InfoPopover>{type description}</InfoPopover></h3>
  <flex column gap-4>
    <gauge row (Conv | Recov, side-by-side)>  ← opacity-50 when no games (D-13)
    {SHOW_WDL_BAR_IN_TYPE_CARDS && hasGames && (
      <wdl-row>
        <span>Win/Draw/Loss  <Games: X% (N) <Swords/> link></span>
        <MiniWDLBar />
      </wdl-row>
    )}
    {hasGames && hasConvOpponent && (
      <conv peer-bullet row>: "Conversion — You X% / Opp Y% / Gap Z%" + MetricStatPopover + MiniBulletChart
    )}
    {hasGames && hasRecovOpponent && (
      <recov peer-bullet row>: "Recovery — You X% / Opp Y% / Gap Z%" + MetricStatPopover + MiniBulletChart
    )}
    {(no opponent on either) → "n < 10, baseline unavailable" placeholder for that row}
    {!hasGames → "Not enough data yet"}
  </flex>
  ```

  - **Games deep-link** sits in the WDL row, mirroring Phase 86 `EndgameMetricCard.tsx:124-132`. NOT in the title row — Phase 86's title row carries only `{label} + title-info-popover`, and the Games link is anchored next to "Win/Draw/Loss". Keep the same layout for visual consistency.
  - If `SHOW_WDL_BAR_IN_TYPE_CARDS = false`, the Games deep-link moves to a standalone row immediately under the gauges (still using `Swords` icon, still `Games: {sharePct}% ({count})` format) so the deep-link doesn't disappear with the WDL bar.

- **D-08: Navigation — keep `onCategorySelect` callback AND URL.** The legacy `EndgameWDLChart` calls `onCategorySelect(cat.endgame_class)` on link click AND navigates to `/endgames/games` (see `EndgameWDLChart.tsx:108-117`). The callback syncs the parent filter state in `Endgames.tsx:511` (`handleCategorySelect`). Preserve both behaviors in `EndgameTypeCard`: `Link to={`/endgames/games?type=${slug}`} onClick={() => onCategorySelect(cat.endgame_class)}`. The `?type=…` query string is **net-new** per SEC3-02 — `/endgames/games` route handler may need a small read of `?type=` to pre-seed the filter (planner: check whether `handleCategorySelect` already syncs state to URL, or if a parallel URL-param hydration is needed in the games page).

### Sig-gating triple (LOCKED — Phase 86 carry-over)

- **D-09: Font-color gate** on each peer-bullet diff percent uses the same triple as `EndgameMetricCard`:
  - `level = deriveLevel(pValue, opponent_games)` from `EndgameOverallShared.ts`
  - `isConfident(level)` from `lib/significance.ts`
  - `outsideNeutral = diff < NEUTRAL_ZONE_MIN || diff >= NEUTRAL_ZONE_MAX` (±0.05 from `lib/endgameMetrics.ts`)
  - All three required → `diffStyle = { color: diff < 0 ? ZONE_DANGER : ZONE_SUCCESS }`; otherwise unstyled.
- Gauges stay always-colored (D-13 carry-over from Phase 86). WDL bar untinted.

### Per-bullet `MetricStatPopover` content (LOCKED — Claude's Discretion, Phase 86 parity)

- **D-10:** Per peer bullet, one short paragraph + methodology block. Mirrors Phase 86 D-16.
  - **Conv peer bullet** (`metricName="Conversion"`): "Your win rate among games where you entered this Endgame Type with a Stockfish eval ≥ +1.0, compared to your opponents' win rate in the same situation across the same Endgame Type. Filter-responsive: baseline shifts with rating × TC × color × opponent-type filters."
  - **Recov peer bullet** (`metricName="Recovery"`): "Your save rate (wins + draws count) among games where you entered this Endgame Type with a Stockfish eval ≤ −1.0, compared to your opponents' save rate in the same situation across the same Endgame Type. Filter-responsive."
  - Methodology block (identical for both, copied verbatim from Phase 86):
    > Score: per-bucket headline rate (Conv = wins, Recov = wins + draws).<br />
    > Test: Wald-z on the signed difference vs 0.<br />
    > Confidence interval: 95% normal-approx on the diff.
- Pass `vocabulary="score"`, `unit="percent"`, `relative`, `baselineLabel="0%"`, `neutralLower={NEUTRAL_ZONE_MIN}`, `neutralUpper={NEUTRAL_ZONE_MAX}` per Phase 86 conventions.

### Title `InfoPopover` content (LOCKED — Claude's Discretion)

- **D-11:** Per-card title `InfoPopover` carries the one-sentence type description from `ENDGAME_TYPE_DESCRIPTIONS` in `EndgameWDLChart.tsx:30-37`. Lift the constant to `frontend/src/lib/endgameMetrics.ts` (alongside the Phase 86 `BUCKET_DISPLAY_LABELS` map) so the new card can import it. Keys: `rook` / `minor_piece` / `pawn` / `queen` / `mixed`. `pawnless` is hidden so its description need not be lifted (planner: prune the `pawnless` entry during lift).

### Page-level h2 InfoPopover (LOCKED — Phase 86 parity)

- **D-12: Replace the legacy `EndgameWDLChart` h3 InfoPopover with a page-level h2 InfoPopover** on the existing "Endgame Type Breakdown" h2 at `Endgames.tsx:507`. Content absorbs:
  - The legacy `EndgameWDLChart` intro (Section structure: 5 cards, what each shows, single-game-counts-once-per-type caveat).
  - The legacy `EndgameConvRecovChart` intro (`EndgameConvRecovChart.tsx:38-49`): Conv = win rate when entering with eval ≥ +1.0; Recov = save rate when entering with eval ≤ −1.0; gauge zones are per-type typical bands from `PER_CLASS_GAUGE_ZONES`.
  - Sub-question copy under the h2: "Which Endgame Types do you convert best and defend best — and how does each compare to your opponents?" (planner may revisit).
- Per-card title `InfoPopover` (D-11) carries only the per-type one-sentence description (`ENDGAME_TYPE_DESCRIPTIONS` lifted to `lib/endgameMetrics.ts`). The taxonomy + metric definitions live at h2 level.
- Remove the per-card title `InfoPopover` if the h2 popover renders the per-type descriptions verbatim — but Phase 86 keeps both (h2 + per-card title) so this phase does the same: h2 = taxonomy + metric defs; per-card title = one-line type description.

### Empty / sparse handling (LOCKED — Phase 86 parity)

- **D-13: 0-games per class:** card renders with `opacity-50` on the gauge row (mirrors Phase 86 D-17 / `EndgameMetricCard.tsx:110`). WDL row and peer-bullet rows replaced with "Not enough data yet" placeholder. Card stays in the grid (don't omit) so the 5-card layout is stable across filter changes.
- **D-14: Sparse opponent (`opponent_games < 10`)** per metric: replace that metric's peer-bullet row with "n < 10, baseline unavailable" (mirrors `EndgameMetricCard.tsx:213-220`). The gauges and WDL bar still render (those depend on `cat.total > 0`, not on opponent sample size).
- **D-15: Sparse total class games (`total < MIN_GAMES_FOR_RELIABLE_STATS = 10`)**: legacy `EndgameWDLChart` mutes via `UNRELIABLE_OPACITY` (`EndgameWDLChart.tsx:91-96`) and shows `n={total}` indicator. Phase 87 keeps this convention: card body gets `style={{ opacity: UNRELIABLE_OPACITY }}` and a `n={total}` chip next to the title (visible only when sparse).

### Card testid scheme (LOCKED)

- **D-16:**
  - Section container: `data-testid="endgame-type-breakdown-section"` (replaces legacy `endgame-wdl-chart` + `conv-recov-chart`).
  - Per-card: `data-testid="type-card-{slug}"` where slug = `rook` / `minor-piece` / `pawn` / `queen` / `mixed` (preserve the hyphenated form from `EndgameWDLChart.tsx:21-28` `CLASS_TO_SLUG`). Matches the Phase 86 `tile-{bucket}` convention.
  - Sub-elements derive: `${tileTestId}-conv-gauge`, `${tileTestId}-recov-gauge`, `${tileTestId}-wdl`, `${tileTestId}-conv-you`, `${tileTestId}-conv-opp`, `${tileTestId}-conv-diff`, `${tileTestId}-conv-info`, `${tileTestId}-recov-you`, `${tileTestId}-recov-opp`, `${tileTestId}-recov-diff`, `${tileTestId}-recov-info`, `${tileTestId}-games-link`. Update any tests cross-referencing the legacy `endgame-category-{slug}-*` testids.

### Claude's Discretion

- **Plan sizing.** Phase 87 is smaller than Phase 86: ~3 plans likely sufficient.
  - Plan 1: Backend math + wire — 10 new fields on `ConversionRecoveryStats`; per-class `compute_score_difference_test` calls in the categories builder; TS type mirror; new pytest cases (per-class Conv + Recov diffs, sparse-opponent, 0-games safety).
  - Plan 2: Frontend prep — lift `ENDGAME_TYPE_DESCRIPTIONS` to `lib/endgameMetrics.ts` (prune `pawnless`); add `SHOW_WDL_BAR_IN_TYPE_CARDS` constant; build `EndgameTypeCard.tsx` + Vitest coverage.
  - Plan 3: Orchestrator + mount + delete — `EndgameTypeBreakdownSection.tsx` + page-level h2 `InfoPopover` content (D-12); swap mount in `Endgames.tsx:506-518` (both legacy mounts → single new mount); delete `EndgameWDLChart.tsx` + `EndgameConvRecovChart.tsx`; knip + ty + lint + npm test gate sweep; HUMAN-UAT real-device check on density (set `SHOW_WDL_BAR_IN_TYPE_CARDS` final value).
  - Planner may split Plan 3 if the deletion + gate sweep grows; final plan count is planner's call.
- **Backend wiring site.** The categories builder in `app/services/endgame_service.py` already assembles `ConversionRecoveryStats` per class. Add the two `compute_score_difference_test` calls inside that loop. No new DB query, no schema migration. Phase 86 D-03 wired similar fields on `_compute_score_gap_material`; planner should locate the parallel site for per-class assembly and add a similar comment block citing Phase 87 + SEC3-04 + D-01.
- **`/endgames/games?type=…` URL hydration.** Planner: verify whether `Endgames.tsx` `handleCategorySelect` already sets a URL param, or whether the games page reads from the parent's React state. If state-only, add a small `?type=…` reader on `/endgames/games` mount so the deep-link works for shareable URLs (browser back/forward, copy-paste). Low risk — pattern already exists for other filter URL params.
- **Test placement.** Backend tests in `tests/test_score_confidence.py` (new `TestPerClassPeerDiff` class — but only if a wrapper helper is added per D-02; otherwise the existing `compute_score_difference_test` tests suffice and the service-layer test verifies the wiring). Frontend tests:
  - `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` (per-card render: gauges, WDL gating by `SHOW_WDL_BAR_IN_TYPE_CARDS`, peer-bullet gating by `MIN_OPPONENT_BASELINE_GAMES`, empty class, sparse class, opacity).
  - `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` (orchestrator: 5 cards rendered, `pawnless` filtered out, grid class, h2 InfoPopover present).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.17 spec & roadmap
- `.planning/REQUIREMENTS.md` — SEC3-01, SEC3-02, SEC3-04, SEC3-05, SEC3-06, SEC3-07 (the six Section 3 requirements).
- `.planning/milestones/v1.17-ROADMAP.md` §Phase 87 — success criteria, card composition, legacy removal mandate, mobile fallback policy.
- `.planning/notes/v1.17-single-bullet-doctrine.md` — pivot rationale; same single-peer-bullet rule applies per-class here.

### Pattern templates (LOCKED — replicate these exactly per user direction)
- `frontend/src/components/charts/EndgameMetricsSection.tsx` — Phase 86 orchestrator pattern. Direct precedent for `EndgameTypeBreakdownSection.tsx`.
- `frontend/src/components/charts/EndgameMetricCard.tsx` — Phase 86 per-card shell. Direct precedent for `EndgameTypeCard.tsx` (gauge row + WDL row with embedded Games link + peer-bullet row with `MetricStatPopover`).
- `frontend/src/components/charts/EndgameOverallShared.ts` — `deriveLevel(pValue, n)` for the sig-gating triple.
- `frontend/src/components/popovers/MetricStatPopover.tsx` — popover component used for the per-bullet sig/CI/methodology.
- `frontend/src/lib/endgameMetrics.ts` — Phase 86's lifted helpers: `MIRROR_BUCKET`, `userRate`, `opponentRate`, `BULLET_DOMAIN`, `NEUTRAL_ZONE_MIN/MAX`, `MIN_OPPONENT_BASELINE_GAMES`, `FIXED_GAUGE_ZONES`, `formatScorePct`, `formatDiffPct`. Phase 87 extends this module with `ENDGAME_TYPE_DESCRIPTIONS` (lifted from `EndgameWDLChart.tsx:30-37`) and `SHOW_WDL_BAR_IN_TYPE_CARDS` constant.
- `frontend/src/lib/significance.ts` — `isConfident(level)`.

### Legacy to be deleted
- `frontend/src/components/charts/EndgameWDLChart.tsx` (352 LOC) — entire file. Per D-11 lift `ENDGAME_TYPE_DESCRIPTIONS` (sans `pawnless`) to `lib/endgameMetrics.ts` before deletion. Delete `CLASS_TO_SLUG` (move to `lib/endgameMetrics.ts` as `ENDGAME_CLASS_TO_SLUG` if reused for testids per D-16; otherwise inline in the card component).
- `frontend/src/components/charts/EndgameConvRecovChart.tsx` (135 LOC) — entire file. The gauge layout transfers verbatim into the new `EndgameTypeCard.tsx` (Conv + Recov side-by-side with `PER_CLASS_GAUGE_ZONES[class]` bands).
- `frontend/src/pages/Endgames.tsx:506-518` — both legacy mounts (`<EndgameWDLChart>` + `<EndgameConvRecovChart>`) collapse into a single `<EndgameTypeBreakdownSection>` mount. The h2 "Endgame Type Breakdown" stays, gets a new `InfoPopover` next to it per D-12.

### Reusable components & primitives
- `frontend/src/components/charts/EndgameGauge.tsx` — gauge primitive. Used twice per card (Conv + Recov).
- `frontend/src/components/charts/MiniBulletChart.tsx` — bullet primitive for each peer-bullet row.
- `frontend/src/components/stats/MiniWDLBar.tsx` — full-game per-class WDL bar.
- `frontend/src/components/ui/info-popover.tsx` — `InfoPopover` for title + h2 popovers.
- `frontend/src/components/ui/tooltip.tsx` — `Tooltip` wrapping the Games deep-link.
- `frontend/src/lib/theme.ts` — `MIN_GAMES_FOR_RELIABLE_STATS = 10`, `UNRELIABLE_OPACITY`, `ZONE_DANGER`, `ZONE_SUCCESS`, `colorizeGaugeZones`.
- `frontend/src/generated/endgameZones.ts` — `PER_CLASS_GAUGE_ZONES[class].{conversion,recovery}`. Codegen output from `app/services/endgame_zones.py`; do NOT regenerate (no Python changes in Phase 87).

### Backend additive fields (D-01)
- `app/schemas/endgames.py` — `ConversionRecoveryStats` model. Extend with 10 new fields per D-01.
- `app/services/endgame_service.py` — the existing per-class category builder. Add two `compute_score_difference_test` calls inside the loop. Planner: locate the parallel site to Phase 86's `_compute_score_gap_material` for the assembly point.
- `app/services/score_confidence.py:255` — `compute_score_difference_test(eg_w, eg_d, eg_l, eg_n, ne_w, ne_d, ne_l, ne_n) -> (p, ci_low, ci_high)`. Reuse as-is; no new helper unless planner wants a per-class wrapper for readability.
- `tests/test_score_confidence.py` — existing helper tests cover the math. Add service-layer tests at `tests/services/test_endgame_service.py` (or similar) for the wiring + mirror-flip correctness.
- `frontend/src/types/endgames.ts` — extend `ConversionRecoveryStats` TS type with the 10 new fields (mirror Phase 86 D-02 wire-shape pattern).

### Wire shape (already populated)
- `frontend/src/types/endgames.ts` — `EndgameCategoryStats` already exposes per-class `wins/draws/losses/total/win_pct/draw_pct/loss_pct` (for WDL bar) and nested `conversion: ConversionRecoveryStats` with per-class `conversion_*` + `recovery_*` W/D/L counts (for sig-test computation and gauges). No new query needed; Phase 87 augments the existing payload.

### Prior phase context (direct precedent)
- `.planning/milestones/v1.17-phases/86-section-2-endgame-metrics-4-card-layout/86-CONTEXT.md` — Phase 86 sibling-component pattern, sig-gating triple, mirror-bucket math, `MetricStatPopover` content style, h2 InfoPopover treatment, deferred POLISH-01/02 boundary. **This phase explicitly follows Phase 86's pattern per-class.**
- `.planning/milestones/v1.17-phases/85-section-1-games-with-vs-without-endgame-cards/85-CONTEXT.md` — Phase 85 originated the sibling-component scaffold and the `MetricStatPopover` convention.
- `.planning/milestones/v1.17-phases/85.1-hypothesis-tests-and-cis-for-endgame-score-differences/85.1-CONTEXT.md` (or DECISIONS) — Phase 85.1 backend math helper precedent for `compute_score_difference_test`.
- `.planning/milestones/v1.17-phases/84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit/84-CONTEXT.md` — Phase 84 mirror-rate audit confirming `PER_CLASS_GAUGE_ZONES` populates correctly for Phase 87's per-type gauges.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 86 `EndgameMetricsSection` + `EndgameMetricCard`** — direct template. The new `EndgameTypeBreakdownSection` + `EndgameTypeCard` mirror this pattern with two metrics (Conv + Recov) per card instead of one.
- **`lib/endgameMetrics.ts`** — Phase 86's shared module. Phase 87 extends with `ENDGAME_TYPE_DESCRIPTIONS` and `SHOW_WDL_BAR_IN_TYPE_CARDS`.
- **`EndgameGauge`** — gauge primitive. Used twice per card (side-by-side Conv + Recov), each with its own `PER_CLASS_GAUGE_ZONES[class]` band.
- **`MetricStatPopover`** — Phase 85/86 popover. Replaces the legacy `Tooltip` on Diff cells.
- **`compute_score_difference_test`** at `app/services/score_confidence.py:255` — Phase 85.1's per-bucket Wald-z helper. Reused for per-class Conv + Recov peer diffs with mirror-flipped opponent W/D/L.
- **`PER_CLASS_GAUGE_ZONES`** at `frontend/src/generated/endgameZones.ts` — already populated by Phase 84 / DATA-02. No codegen change.
- **`HIDDEN_ENDGAME_CLASSES`** at `Endgames.tsx:53` — already filters `pawnless`. Imported by the new section to apply the same hide.
- **`ENDGAME_TYPE_DESCRIPTIONS` + `CLASS_TO_SLUG`** at `EndgameWDLChart.tsx:21-37` — lift to `lib/endgameMetrics.ts` before deleting the source file.

### Established Patterns
- **`charcoal-texture rounded-md p-4`** tile container (Phase 81+ convention). All per-type cards reuse this.
- **`flex flex-col gap-4`** vertical stack inside each tile.
- **Sig-gating triple** (`isConfident(level) ∧ outside-neutral-band ∧ n >= MIN_OPPONENT_BASELINE_GAMES`): applies to each peer-bullet diff percent font color. Gauges always-colored; WDL bar untinted.
- **Page-level h2 + sub-question + `InfoPopover` trigger** — Phase 85/86 dropped section-level h3s in favor of this. Phase 87 carries forward: the existing "Endgame Type Breakdown" h2 at `Endgames.tsx:507` gets a new `InfoPopover`; section-level h3 inside cards is removed (titles live at card level only).
- **Mirror-metric symmetry** (Phase 60 / 86): `opp wins in metric A = user losses in metric mirror(A)`; per-class mirror is metric-mirrored within the same class (Conv ↔ Recov), NOT cross-class.
- **`opacity-50` on no-games card body** (Phase 86 D-17): preserved here for empty classes.

### Integration Points
- **`Endgames.tsx:506-518`** — section mount swap (both legacy mounts → single new mount). New h2 `InfoPopover` next to the existing h2 at line 507.
- **`Endgames.tsx:511` `handleCategorySelect`** — preserve callback wiring; the new `EndgameTypeCard` passes `onCategorySelect` down for filter-state sync (Plan 3 verifies URL hydration on `/endgames/games`).
- **`app/services/endgame_service.py`** — per-class `ConversionRecoveryStats` builder. Add diff-test calls inside the loop.
- **`app/schemas/endgames.py`** `ConversionRecoveryStats` — extend with 10 new fields per D-01.
- **knip CI** — must pass after deleting `EndgameWDLChart.tsx` + `EndgameConvRecovChart.tsx`. Verify with `npm run knip`.
- **ty CI** — `uv run ty check app/ tests/` must pass with the new schema fields and service-layer additions.

### Sentry
- No new exceptional paths. Per-class diff tests reuse the existing `compute_score_difference_test` (guarded by `n > 0` on each side, returns `None` triple when ungated). No new exception sites.

</code_context>

<specifics>
## Specific Ideas

- **Component file names:** `EndgameTypeBreakdownSection.tsx`, `EndgameTypeCard.tsx`. No `*Shared.ts` helper needed — `lib/endgameMetrics.ts` absorbs the new exports.
- **Schema fields** on `ConversionRecoveryStats` (10 new): `opp_conversion_pct`, `opp_recovery_pct`, `opp_conversion_games`, `opp_recovery_games`, `conv_diff_p_value`, `conv_diff_ci_low`, `conv_diff_ci_high`, `recov_diff_p_value`, `recov_diff_ci_low`, `recov_diff_ci_high`. All `float | None` except `opp_*_games: int`.
- **Mobile fallback flag:** `SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true` in `lib/endgameMetrics.ts`. Plan 3 HUMAN-UAT step decides whether to flip before merge.
- **Sub-question copy under h2:** "Which Endgame Types do you convert best and defend best — and how does each compare to your opponents?" (planner may revisit).
- **Card testids:** `type-card-{slug}` where slug uses the hyphenated form (`minor-piece`, not `minor_piece`) per `CLASS_TO_SLUG`. Sub-element testids: `${tileTestId}-conv-gauge`, `${tileTestId}-recov-gauge`, `${tileTestId}-wdl`, `${tileTestId}-conv-{you,opp,diff,info}`, `${tileTestId}-recov-{you,opp,diff,info}`, `${tileTestId}-games-link`.
- **`MetricStatPopover` props** per peer bullet — see D-10 for exact `name`, `explanation`, `methodology` text and `vocabulary="score"`, `unit="percent"`, `relative`, `baselineLabel="0%"`, `neutralLower/Upper={±0.05}` settings.
- **Comment block header** in new components referencing Phase 87 + single-bullet doctrine + Phase 86 parity, matching the Phase 86 header pattern at `EndgameMetricsSection.tsx:1-...`.

</specifics>

<deferred>
## Deferred Ideas

- **Cell-specific peer-bullet neutral bands** (POLISH-01) — Phase 88 scope. ±0.05 stays.
- **Gauge sig gating** (POLISH-02) — Phase 88 scope. Gauges stay always-colored.
- **`data-testid` / ARIA / semantic-HTML audit across all new card surfaces** (POLISH-03) — Phase 88. Phase 87 applies the testids per D-16, but the milestone-wide consistency sweep happens in Phase 88.
- **375px parity audit across Sections 1 / 2 / 3** (POLISH-04) — Phase 88. Phase 87's mobile real-device check (HUMAN-UAT) is narrowly scoped to WDL-bar density only.
- **Cross-type Conv/Recov aggregate trend over time** — out of scope for v1.17. Idea: per-type Conv / Recov timeline series alongside the existing `EndgameEloTimelineSection`. Capture for v1.18+ backlog.
- **Per-class composite Skill gauge** — explicitly rejected by the single-bullet doctrine; composite Skill lives at Section 2 page level only.

</deferred>

<next_steps>
## Next Steps

`/clear` then:

`/gsd-plan-phase 87`

Recommended plan slicing (planner's call — see Claude's Discretion in `<decisions>`):
1. Backend math + wire — schema additions, per-class `compute_score_difference_test` calls, TS type mirror.
2. Frontend prep — `EndgameTypeCard.tsx` + Vitest; lift `ENDGAME_TYPE_DESCRIPTIONS` to `lib/endgameMetrics.ts`; add `SHOW_WDL_BAR_IN_TYPE_CARDS` constant.
3. Orchestrator + mount + delete — `EndgameTypeBreakdownSection.tsx` + page-level h2 `InfoPopover`; swap mount in `Endgames.tsx`; delete `EndgameWDLChart.tsx` + `EndgameConvRecovChart.tsx`; gate sweep + HUMAN-UAT density check.

</next_steps>
