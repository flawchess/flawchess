# Phase 87 — Discussion Log

**Date:** 2026-05-14
**Mode:** default

## Pre-discuss analysis

**Domain:** Replace `EndgameWDLChart.tsx` (per-type WDL table + score-gap bullet) and `EndgameConvRecovChart.tsx` (per-type gauge-only mini cards) with 5 unified per-type cards (rook / minor_piece / pawn / queen / mixed) in a responsive grid (3-col lg+, 2-col sm, 1-col mobile). Each card: side-by-side Conv + Recov gauges, full-game WDL bar, Conv + Recov peer bullets vs 0 (mirror-metric baseline), Games deep-link.

**Carried forward (not re-asked):**
- Single-bullet doctrine (v1.17 pivot 2026-05-12).
- Mirror-metric peer baseline (Phase 86 `MIRROR_BUCKET` / `opponentRate`).
- `MIN_OPPONENT_BASELINE_GAMES = 10` gate with sparse-n indicator (Phase 86).
- Sig-gating triple (Phase 86 D-14): `isConfident(level) ∧ outside-neutral-band ∧ n >= 10` → diff font color only.
- ±0.05 neutral band, `BULLET_DOMAIN = 0.20` (POLISH-01 deferred to Phase 88).
- Gauges always-colored; WDL bar untinted (POLISH-02 deferred to Phase 88).
- Shared helpers in `frontend/src/lib/endgameMetrics.ts` (Phase 86 D-08).
- `MetricStatPopover` for per-bullet sig/CI/methodology (Phase 85/86 convention).
- `PER_CLASS_GAUGE_ZONES` already in `frontend/src/generated/endgameZones.ts` (Phase 84 / DATA-02).

## Gray areas presented

1. **Peer-bullet sig test computation site** — backend wire-up (mirror Phase 86) vs frontend math (FE Wald-z).
2. **Component architecture & navigation** — fresh sibling files vs in-place extension; `onCategorySelect` callback vs URL-only nav.
3. **Card internal layout & mobile fallback** — element order; WDL-bar drop policy (hard constant vs CSS-only); empty class handling.
4. **Popover taxonomy** — page-level h2 vs per-card title vs hybrid.

## User selection

User selected: **"Be consistent with the design, naming, and statistical decisions we made when reworking the Conversion and Recovery cards in the Endgame Metrics and ELO section. The rest is up to you."**

Interpretation: apply Phase 86 patterns verbatim per-class; defer to Phase 86's locked decisions on every axis. No drilldown discussion needed; Claude locks the implementation choices following Phase 86 parity.

## Decisions made (Claude's Discretion, Phase 86 parity)

### D-01: Peer-bullet sig test — backend wire-up
Mirrors Phase 86 D-01..D-06. 10 new fields on `ConversionRecoveryStats` (`opp_conversion_pct`, `opp_recovery_pct`, `opp_conversion_games`, `opp_recovery_games`, `conv_diff_p_value/ci_low/ci_high`, `recov_diff_p_value/ci_low/ci_high`). Service-layer wiring uses the existing `compute_score_difference_test` helper with mirror-flipped opponent W/D/L. TS types mirror. **Rationale:** Phase 86 just consolidated sig-test logic server-side; FE math would duplicate that consolidation and contradict the user's "be consistent" directive.

### D-02: Reuse `compute_score_difference_test` directly
No new statistical helper. Optional thin per-class wrapper for readability (planner's call).

### D-03: Component file structure — fresh sibling files
`EndgameTypeBreakdownSection.tsx` (orchestrator) + `EndgameTypeCard.tsx` (per-class shell). Delete `EndgameWDLChart.tsx` + `EndgameConvRecovChart.tsx`. Mirrors Phase 86 `EndgameMetricsSection` + `EndgameMetricCard`.

### D-04: Mobile WDL-bar fallback flag
Hard constant `SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true` in `lib/endgameMetrics.ts`. Flip during execute HUMAN-UAT if real-device density check fails. CSS-only hide rejected (would create inconsistent mobile/desktop layouts the user already rejected in prior phases).

### D-05: Final component names
`EndgameTypeBreakdownSection.tsx` + `EndgameTypeCard.tsx`. No connector arrows (no composite/target card).

### D-06: Grid layout
`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` — matches legacy `EndgameConvRecovChart` grid; natural flow handles the 5-card layout (3+2 on lg, 2+2+1 on sm, stacked on mobile).

### D-07: Per-card element order
Title row → gauge row (Conv | Recov side-by-side) → WDL row (with embedded Games deep-link, gated by `SHOW_WDL_BAR_IN_TYPE_CARDS`) → Conv peer-bullet row → Recov peer-bullet row. Mirrors Phase 86 `EndgameMetricCard`.

### D-08: Navigation — callback + URL
Preserve `onCategorySelect` callback (legacy `EndgameWDLChart` pattern) AND add `?type=…` to the URL. Planner verifies `/endgames/games` URL hydration.

### D-09: Sig-gating triple — Phase 86 carry-over
`deriveLevel(pValue, opponent_games)` + `isConfident(level)` + outside-neutral-band → diff font color only.

### D-10: `MetricStatPopover` content
Per peer bullet (Conv + Recov): one short paragraph + Phase 86 methodology block. `vocabulary="score"`, `unit="percent"`, `relative`, `baselineLabel="0%"`, `neutralLower/Upper={±0.05}`.

### D-11: Title `InfoPopover` content
One-sentence type description per card, lifted from legacy `EndgameWDLChart.tsx:30-37` `ENDGAME_TYPE_DESCRIPTIONS`. Move the constant to `lib/endgameMetrics.ts` (prune `pawnless`).

### D-12: Page-level h2 `InfoPopover`
New `InfoPopover` next to the existing "Endgame Type Breakdown" h2 at `Endgames.tsx:507`. Absorbs both legacy intros (taxonomy + metric definitions). Sub-question copy: "Which Endgame Types do you convert best and defend best — and how does each compare to your opponents?"

### D-13: Empty class handling
`opacity-50` on gauge row + "Not enough data yet" replacing WDL/bullet rows. Card stays in the grid for layout stability.

### D-14: Sparse opponent handling
Per-metric "n < 10, baseline unavailable" placeholder on the affected peer-bullet row. Gauges + WDL bar still render.

### D-15: Sparse total class games
`opacity={UNRELIABLE_OPACITY}` on card body + `n={total}` chip on title row when `total < MIN_GAMES_FOR_RELIABLE_STATS = 10`. Carry-forward from legacy `EndgameWDLChart.tsx:91-96`.

### D-16: Card testid scheme
Section: `endgame-type-breakdown-section`. Per-card: `type-card-{slug}` (hyphenated slug from legacy `CLASS_TO_SLUG`). Sub-elements: `${tileTestId}-conv-gauge` / `-recov-gauge` / `-wdl` / `-conv-{you,opp,diff,info}` / `-recov-{you,opp,diff,info}` / `-games-link`.

## Deferred ideas

- Cell-specific peer-bullet neutral bands (POLISH-01 / Phase 88).
- Gauge sig gating (POLISH-02 / Phase 88).
- Milestone-wide `data-testid` / ARIA audit (POLISH-03 / Phase 88).
- 375px parity audit across all sections (POLISH-04 / Phase 88).
- Cross-type Conv/Recov timeline (v1.18+ backlog).
- Per-class composite Skill gauge — rejected (single-bullet doctrine).

## Note on scope

The Phase 87 ROADMAP description calls this a frontend-only refactor. D-01 adds 10 new schema fields and service-layer wiring on the backend, mirroring the Phase 85.1 / Phase 86 caveat (both phases added small backend additions despite the "frontend-only" milestone framing). The user authorized the Phase 86 pattern verbatim at discuss-phase, which implicitly authorizes the equivalent backend additions here. Plan-phase should note this in the plan summary; the milestone-close summary should roll the Phase 87 backend additions into the existing Phase 85/86 amendment.
