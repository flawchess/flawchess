# Phase 57: Endgame ELO — Timeline Chart - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A timeline chart on the Endgames tab showing **Endgame ELO vs Actual ELO over time**, one paired line-per-combo, for each qualifying (platform, time-control). Uses weekly cadence with a trailing 100-game rolling window. Sidebar filters narrow which combos appear. Cold-start (new accounts with recency filters active) produces no artifacts — an empty-state message is shown instead.

**Scope note:** This discussion also locks the **Endgame ELO calculation formula** — a Phase 56 concern, captured here at the user's explicit request so Phase 56 can be planned later with the algorithm already decided.

</domain>

<decisions>
## Implementation Decisions

### Endgame ELO Formula (shared with Phase 56)

- **D-01:** `endgame_elo = round(avg_opp_rating + 400 · log10(skill_clamped / (1 − skill_clamped)))`
  - `skill = endgame_skill(endgame_games_in_scope)` — the existing composite: mean of Conversion Win %, Parity Score %, Recovery Save %, excluding buckets with 0 games
  - `avg_opp_rating = avg(opponent_rating)` across the same endgame games
  - `skill_clamped = clamp(skill, 0.05, 0.95)` to bound log10 at the extremes (caps contribution at roughly ±510 Elo, well beyond realistic performance-rating territory)
- **D-02:** **One formula for both platforms.** No Glicko-1 vs Glicko-2 branching. Justified because (a) each rating column is stored on the platform's native scale, (b) the breakdown table and timeline are already segmented per (platform, TC) so scales never mix within a combo, (c) proper Glicko performance would need RD/volatility we don't store, (d) noise from the formula choice is dwarfed by small-sample noise. Info popover (Phase 56 ELO-04) should mention that chess.com (Glicko-1) and lichess (Glicko-2) ratings aren't directly comparable *across* platforms.
- **D-03:** **Endgame Skill must move to the backend.** Currently a frontend-only helper (`endgameSkill()` in `EndgameScoreGapSection.tsx`). Phase 56 ports the computation server-side so the timeline and breakdown endpoints can return per-scope skill values. Frontend can either keep its helper (render-time summary) or switch to the backend value — out of scope for Phase 57 but Phase 56 plan should address.

### Actual ELO Line (dark line)

- **D-04:** `actual_elo_point = avg(user_rating)` over the **same rolling-100 pool of ALL games** (not just endgame games) for that combo at that weekly timestamp. `user_rating` derived from `white_rating`/`black_rating` via `user_color`, same pattern as existing `query_rating_history`. Rolling-100 over all games (not endgame-only) keeps the Actual ELO line faithful to the user's real rating trajectory — the *gap* to Endgame ELO (bright line) is the interesting signal.

### Timeline Binning

- **D-05:** **Weekly cadence with 100-game rolling window** via the existing `_compute_weekly_rolling_series` pattern. New constant: `ENDGAME_ELO_TIMELINE_WINDOW = 100`, matching `SCORE_GAP_TIMELINE_WINDOW` and `CLOCK_PRESSURE_TIMELINE_WINDOW` already defined in `app/services/endgame_service.py`.
- **D-06:** Threshold: reuse `MIN_GAMES_FOR_TIMELINE = 10`. A weekly point is emitted only when the trailing 100-game endgame window has ≥ 10 endgame games. This is the Phase 57 cold-start defense (SC-3).
- **D-07:** Two series are co-computed per combo per weekly timestamp: one skill+opp_avg pair (for Endgame ELO) and one user_rating average (for Actual ELO). Both land in the same weekly point payload so they render on aligned X coordinates.

### Chart Shape

- **D-08:** **One chart, paired lines per (platform, time-control)** — matches ROADMAP SC-1 literally. Same hue per combo; bright line = Endgame ELO, dark line = Actual ELO. Legend click toggles individual combos. Up to 8 combos (2 platforms × 4 TCs), so up to 16 lines, but sidebar filters usually narrow this.
- **D-09:** Filter interaction: sidebar platform + time-control filters restrict which combos enter the chart. Single-combo selection renders two lines. No tabs. Rated / recency / color / opponent-type filters restrict the game pool before bin computation, same as all other endgame sections.

### Cold-Start / Sparse Data Handling

- **D-10:** Three-tier hiding, all by construction from D-06:
  1. **Per-point:** not emitted when rolling-100 endgame window < 10 games (handled inside `_compute_weekly_rolling_series`).
  2. **Per-combo:** drop combo from chart + legend if it emits zero points across the whole filter window.
  3. **Chart-level:** empty state ("Not enough endgame games yet for a timeline. Import more games or loosen the recency filter.") when all combos drop. Mirrors Phase 56's "Insufficient data" text but phrased for the chart context.

### Claude's Discretion

- Exact hue assignments per combo (pick from `frontend/src/lib/theme.ts`, ensure accessibility contrast).
- Bright-vs-dark implementation: opacity modifier vs separate theme constants — planner decides.
- InfoPopover copy: planner writes short prose covering the formula, the clamp, the 100-game window, and the Glicko caveat. Keep it under 4 short paragraphs, em-dashes sparingly (CLAUDE.md).
- Mobile layout: legend may wrap or collapse below the chart on small screens — planner/UI phase decides, subject to the mobile-parity rule (CLAUDE.md).
- Whether to render the frontend Endgame Skill composite from the new backend value or keep the existing `endgameSkill()` helper (Phase 56 concern; out of scope here).
- Whether the breakdown table (Phase 56) should also surface `avg_opp_rating` and `games` alongside Endgame ELO / Actual ELO / gap — planner's call during Phase 56 discuss.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Algorithm & requirements
- `.planning/ROADMAP.md` §Phase 56 and §Phase 57 — goals, requirements (ELO-01..06), success criteria
- `.planning/milestones/v1.8-REQUIREMENTS.md` §v1.9 Advanced Analytics — original ELO-01..ELO-06 definitions

### Existing endgame timeline patterns (reuse)
- `app/services/endgame_service.py` — `_compute_weekly_rolling_series` (weekly cadence + rolling window), `SCORE_GAP_TIMELINE_WINDOW = 100`, `CLOCK_PRESSURE_TIMELINE_WINDOW = 100` precedents
- `app/services/openings_service.py` — `MIN_GAMES_FOR_TIMELINE = 10` constant, `derive_user_result`, `recency_cutoff`
- `frontend/src/components/charts/EndgameTimelineChart.tsx` — existing Recharts line chart patterns, legend toggling via `hiddenKeys`, `niceWinRateAxis` (axis shape — for Elo we'll want a different axis helper)

### Existing rating-history computation (reuse for Actual ELO line)
- `app/repositories/stats_repository.py` — `user_rating_expr` case statement for white/black_rating based on user_color
- `app/services/stats_service.py` — `get_rating_history`, `query_rating_history` per-platform aggregation

### Endgame Skill composite (Phase 56 will port to backend)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — `endgameSkill()` helper (current frontend definition, lines ~167-177), `ENDGAME_SKILL_ZONES` (lines 101-105)
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-PLAN.md` — plan that introduced the composite
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` — decisions (45-55% blue band semantics, typical ~52%)

### Domain spec
- `docs/endgame-analysis-v2.md` — overall endgame analytics spec; §1-2 define Score, Material buckets, Parity (inputs to Endgame Skill); §5 min-sample-size convention (10 games)

### Project conventions
- `CLAUDE.md` §Frontend — theme constants in `theme.ts`, `noUncheckedIndexedAccess`, mobile parity rule, primary vs secondary buttons, `data-testid` rules
- `CLAUDE.md` §Coding Guidelines — type safety, ty compliance, no magic numbers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_compute_weekly_rolling_series` (`app/services/endgame_service.py`) — drop-in pattern for weekly+rolling series; adapt its inner payload to emit skill, opp_avg, user_rating instead of win_rate.
- `query_rating_history` + `user_rating_expr` (`app/repositories/stats_repository.py`) — already derives user rating per game from white/black_rating + user_color. The Actual ELO line aggregation can lift from this.
- `apply_game_filters` (`app/repositories/query_utils.py`, per CLAUDE.md) — the single place for platform / time-control / rated / opponent / recency / color filtering. Timeline query must use it; never duplicate filter logic.
- `MaterialRow` schema (backend side of Phase 53) — provides Conversion/Parity/Recovery inputs; Phase 56 will add a backend `endgame_skill()` function over these.
- `ChartContainer` / `LineChart` / `Line` from Recharts, `InfoPopover` — existing chart infrastructure, use as-is.
- `niceWinRateAxis` — **not** a direct reuse for Elo (operates in 0-1). Need a sibling helper (e.g. `niceEloAxis`) producing rating-scale ticks, or just use Recharts' default auto-scaling with padding.

### Established Patterns
- **Timeline window constants live in `endgame_service.py`** as module-level uppercase constants; `ENDGAME_ELO_TIMELINE_WINDOW = 100` should follow.
- **Theme colors always imported from `frontend/src/lib/theme.ts`** — add `ELO_COMBO_COLORS` or reuse/extend existing palette. No literal hex values in components.
- **Info popovers added via `InfoPopover` component**, content is JSX `<p>` paragraphs inside `<div className="space-y-2">`.
- **Empty state**: plain `<div className="text-center text-muted-foreground py-8">` with message text, consistent with existing `EndgameTimelineChart` empty handling.
- **Legend toggle**: `hiddenKeys` `Set<string>` state + `handleLegendClick` pattern from `EndgameTimelineChart` — reuse verbatim.

### Integration Points
- **Backend:** new router method on `app/routers/endgame.py` (or extend existing), returning per-combo per-week timeline. Schema in `app/schemas/endgame.py` with `EndgameEloTimelinePoint` (combo_key, date, endgame_elo, actual_elo, games_in_window) and `EndgameEloTimelineResponse` (one series per combo).
- **Frontend:** new `EndgameEloTimelineSection.tsx` under `frontend/src/components/charts/`. Page wiring in `frontend/src/pages/Endgames.tsx` — append after Endgame ELO breakdown section (Phase 56) in the new "Endgame ELO" container. Types in `frontend/src/types/endgames.ts`. Fetch hook in `frontend/src/hooks/` mirroring existing endgame hooks.
- **Mobile parity:** same component renders on desktop + mobile; legend should wrap (or collapse behind a toggle) rather than overflow on small screens — subject to UI/UX review during planning.
- **Browser automation:** chart container gets `data-testid="endgame-elo-timeline-chart"`, section container `data-testid="endgame-elo-timeline-section"` (CLAUDE.md §Browser Automation Rules).

</code_context>

<specifics>
## Specific Ideas

- **User's explicit framing:** "calculate Endgame ELO for a platform × time-control combination, based on opponent ELO and Endgame Skill." The chosen performance-rating formula satisfies this exactly.
- **Normalization check:** Endgame Skill is already in [0, 1] by construction (mean of three [0, 1] rates), so no extra normalization — only clamping to [0.05, 0.95].
- **"Hidden lines" note:** formulas must show BOTH lines — Endgame ELO (bright) and Actual ELO (dark). D-04 captures the Actual ELO line spec.
- **Glicko worry surfaced by user:** answered in D-02 — no platform-specific formula needed because we segment by platform.
- **Referenced prior charts:** "use weekly datapoints like in the other endgame timeline charts" and "last 100 game rolling window like for the other charts" → resolved to `_compute_weekly_rolling_series` with `ENDGAME_ELO_TIMELINE_WINDOW = 100`.
- **Global Stats ELO chart uses daily datapoints** — explicitly NOT the pattern to follow here; this chart follows the endgame-timeline family convention.

</specifics>

<deferred>
## Deferred Ideas

- **Proper Glicko performance rating** (using RD/volatility per opponent) — would require storing opponent RD/volatility at import time. Marginal gain over the Elo performance approximation given typical sample sizes. Not in scope for v1.10.
- **Per-game Endgame Elo performance** (per-game `opp_rating + delta(score)` then averaged) — rejected in favor of skill-based aggregation, but still a theoretically valid alternative if the skill-composite approach ever produces unintuitive results in practice.
- **Endgame Skill breakdown per material bucket displayed inline on the timeline** — would be information-dense noise. Users interested in bucket-level detail have the breakdown table (Phase 53).
- **Materially collapsed time controls** (e.g. blitz+rapid together if per-combo samples too thin) — handled passively by the < 10 games threshold dropping combos rather than merging them. If merging becomes valuable, add as a future phase.
- **Info popover A/B copy** — keep short per CLAUDE.md em-dash guidance; precise wording is planner's call.

</deferred>

---

*Phase: 57-endgame-elo-timeline-chart*
*Context gathered: 2026-04-18*
