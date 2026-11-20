# Phase 257: Facepalm Rate in the Library Stats (SEED-261114-iuv) - Context

**Gathered:** 2026-11-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Facepalm statistics in the Library Stats, limited to what needs no benchmark:

1. A stats cut at 0.7 as its own constant, and a facepalm type per scored blunder (missed win / allowed loss)
   returned by the library API next to the score.
2. The facepalm chip tinted by type on every surface that shows it.
3. A facepalm-share chart below the Flaws Timeline (facepalm blunders / scored blunders over the rolling window).
4. A "Facepalm blunders" card in "You vs. your opponents": total, missed wins, allowed losses, paired per game.

Out of scope (SEED-261120-bzq): benchmark zones and verdict colours for the facepalm rows, the within-player
bias against a benchmark, the type-by-clock matrix, the training weighting.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (seed "Current scope" and roadmap, owner 2026-11-20; not re-discussed)
- **D-01: Stats cut.** A new named constant at 0.7 (the label meaning), separate from the drill's
  `FACEPALM_SCORE_MIN` (0.5). Scores use `FACEPALM_LIBRARY_LAMBDA`. A facepalm blunder in the stats is a scored
  blunder with score >= 0.7.
- **D-02: Type rule** on the model's raw material inputs (`loss`, `missed`, both in material units): allowed
  loss when `loss > 0 and loss >= missed`, missed win otherwise. Ties count as allowed loss; rows without
  material in either line count as missed win. The fitted coefficients are not used for typing.
- **D-03: Timeline metric.** Facepalm blunders / scored blunders, pooled over the rolling window (not a mean of
  per-game shares), not split by type. Its own small chart below the Flaws Timeline with the same x-axis,
  rolling window and per-time-control series. Source is `game_flaws`; unscored blunders are left out of both
  counts. Fallback if the share is too jumpy on real accounts: a rolling mean of the score.
- **D-04: No type-share statistic.** The types are never compared with each other (the model weights lost
  material about three times as much as a missed gain), only with the same type of the opponents. No chart or
  row puts the two type levels against each other as a split.
- **D-05: Copy rules.** State the comparison, do not diagnose. The score is a ranking, not a probability
  (253 D-03 still bans probability wording such as "chance you'd see it").
- **D-06: Opponent scores stay out of drill selection and the library tag filters** (user-only,
  `player_only_gate`).
- **D-07: Name and icon.** "Facepalm", lucide `TreePalm`, whole percent rounded down (253).

### Chip tint scope
- **D-08: All three surfaces are tinted.** Flaws-card chip (`FacepalmChip`), analysis move-list mini-chip
  (`FacepalmMoveChip`) and the `Facepalm 95%` line in the eval chart tooltip. Teal (`TAC_MISSED*`) for missed
  win, crimson (`TAC_ALLOWED*`) for allowed loss. The type therefore has to be in every payload that carries
  `facepalm_score` (`FlawListItem`, the game-card flaw item, `FlawMarker`).
- **D-09: Every scored blunder is tinted**, not only those at or above 70%. The neutral white facepalm chip
  (`FACEPALM_CHIP*`) is no longer used for scored blunders; a chip without a type does not exist.
- **D-10: The type is named in the popover, not on the chip.** Chip text stays `<TreePalm> Facepalm 94%`. The
  shared explanation (`FacepalmExplanation`) gains one line naming the type and what it means, e.g. "Missed
  win: the best move won material that was not taken." / "Allowed loss: the move gave away material." Colour is
  never the only signal.

### Vs-opponents placement and unit
- **D-11: A new "Facepalm blunders" card in the "You vs. your opponents" section**, next to the context-tag
  cards, reusing the row and popover components (`GapRow`, `GapPopover`). It sits behind the section's existing
  analyzed-games gate and follows the page's one TC switch.
- **D-12: Unit is per 100 of the user's moves**, like every other row in that section, with the same paired
  normalisation (both sides divided by the user's move count per game, so player rate minus opponent rate equals
  the delta). This deliberately replaces the seed's "per game" wording (owner, 2026-11-20). The comparison stays
  paired per game, never pooled.
- **D-13: Neutral bar, no verdict.** The rows have no grey benchmark band and no red/green colouring in this
  phase, like tactic rows without a viable band (`has_zone = false`). The gap, both rates and the event counts
  are shown; significance may be stated in the popover but drives no colour. Verdict colours arrive with the
  benchmark zones (SEED-261120-bzq).

### Row names and copy
- **D-14: Row labels.** "Facepalm blunders" (total), "Missed wins", "Allowed losses". The terms "chance
  blindness" and "threat blindness" do not appear anywhere in the UI in this phase: they name a verdict, and
  without a band there is no verdict to name.
- **D-15: Row hints name the 70% cut** (owner-selected direction; exact wording may be polished):
  - Facepalm blunders: "Blunders with a facepalm score of 70% or more"
  - Missed wins: "Facepalm blunders that passed up a material win"
  - Allowed losses: "Facepalm blunders that gave away material"
- **D-16: Card intro and popovers state the comparison only**, e.g. "Your facepalm blunders per 100 of your
  moves, next to your opponents' in the same games." No mention of focus, distraction, time trouble or
  blindness, and no sentence on what a higher rate means. The popover says there is no typical range for these
  rows yet.

### Claude's Discretion
- **Share chart floor and look** (area offered, owner left it to Claude; defaults announced and not objected to):
  a point needs the existing 10-game window floor and at least 20 scored blunders in the window (a named
  constant; the researcher should check on real accounts, including thin time controls, whether 20 is enough to
  keep the line from jumping); y-axis in percent fitted to the data; the same per-week volume bars, date ticks,
  inactivity markers and rolling-window caption as the Flaws Timeline; title "Facepalm share of blunders"; a
  text fallback below two points; a tooltip that gives the share and the two counts (facepalm / scored).
- Whether the share series is added to the existing flaw-stats response or its own endpoint, and whether the
  three facepalm rows join `FlawComparisonTc` or a separate payload.
- Position of the Facepalm card among the existing cards and its layout on phones.
- Popover type-line wording for opponent blunders on the analysis surfaces ("their level" variant already
  exists via `byOpponent`).
- Schema shape of the type (a `Literal["missed_win", "allowed_loss"]`, null when the score is null).
- Umami event targets and `data-testid` names (follow the existing library-stats patterns).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and decisions
- `.planning/seeds/SEED-261114-iuv-facepalm-rate-library-stats.md` — "Current scope (2026-11-20)" and the design
  note win over the older sections; prod measurements (32% of scored blunders at 0.7, type split) and cautions.
  Note: D-12 above overrides its "per game" unit.
- `.planning/seeds/SEED-261120-bzq-facepalm-benchmark-zones-and-clock-matrix.md` — everything deferred; do not
  build any of it here.
- `.planning/ROADMAP.md` §"Phase 257" — goal and dependencies.

### Prior phase decisions this phase builds on
- `.planning/phases/253-facepalm-score-library-ui/253-CONTEXT.md` — chip, popover copy (D-20 to D-23),
  probability-wording ban (D-03), percent rounding, filter presets (High = 70-100).
- `.planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-CONTEXT.md` — shipped model and
  constants, material inputs.
- `.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-CONTEXT.md` — `loss` and
  `missed` definitions (D-05), the lambda knob.
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 (ranking, not a probability), D-06.

### Benchmarks
- `reports/benchmark/benchmarks-latest.md` — source of truth for "typical"; it has no facepalm zones, which is
  why the rows are band-less (D-13).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/facepalm_score.py`: `facepalm_expr(lam)`, `_loss_sql` / `_missed_sql`, `material_loss` /
  `material_missed` — the type rule (D-02) needs a SQL and a Python twin on the same inputs.
- `app/services/blunder_check_rules.py`: `FACEPALM_SCORE_MIN` (0.5, drill), `FACEPALM_LIBRARY_LAMBDA`; the new
  0.7 stats constant belongs next to them.
- `app/repositories/library_repository.py`: `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` at the flaw list, game-card
  chip and `fetch_page_facepalm_scores` (the three places that need the type); `fetch_flaw_trend_rows`,
  `fetch_flaw_comparison`.
- `app/services/library_service.py`: `_compute_flaw_trend` / `_compute_flaw_trend_by_tc` (100-game window,
  `FLAW_TREND_WINDOW`, `MIN_GAMES_FOR_TIMELINE`, one point per ISO week), `_paired_series`, `_paired_gap_test`,
  `_build_flaw_bullet`, `_build_tactic_bullet` (band-less bullets).
- `app/schemas/library.py`: `FlawBullet` / tactic bullet shape with `has_zone`, `FlawTrendPoint`, `FlawTrendTc`.
- Frontend: `FlawTrendChart.tsx` (chart style to mirror), `stats/ContextTagCards.tsx`, `stats/GapRow.tsx`,
  `stats/GapPopover.tsx`, `stats/GapBar.tsx`, `stats/LibraryStatsSections.tsx` (`FlawTimeline`,
  `VsOpponentsSection`), `FacepalmChip.tsx`, `analysis/FacepalmMoveChip.tsx`, `FacepalmExplanation.tsx`,
  `EvalChart.tsx` (tooltip line), `lib/theme.ts` (`TAC_MISSED*`, `TAC_ALLOWED*`, `FACEPALM_CHIP*`),
  `lib/flawComparisonMeta.ts` (row labels, hints, definitions).

### Established Patterns
- The existing trend reads the games-table oracle columns; the share needs `game_flaws` (scored blunders), so
  it is a new query, not an extra column on the trend rows.
- Stats payloads are per TC; the selected TC is a client-side pick and never part of a query key.
- All game filtering goes through `apply_game_filters()`; you-vs-opponent rates normalise both sides by the
  user's move count.
- Colours with meaning live in `theme.ts`; minimum font size `text-sm` (the chip's `text-xs` is an existing,
  requested exception); every new interactive element gets a `data-testid` and its `trackFeature` event.

### Integration Points
- `FlawStatsSection` → new share chart directly under `FlawTimeline`, same selected TC.
- `VsOpponentsSection` → new Facepalm card alongside `ContextTagCards`.
- Library API schemas (`FlawListItem`, game-card flaw item, `FlawMarker`) → new type field next to
  `facepalm_score`; `frontend/src/types/library.ts` mirrors it.
- Opponent blunders are scored on prod, so the opponent side of the paired rows reads the same score expression;
  the tag filters and the drill must keep their user-only gates (D-06).

</code_context>

<specifics>
## Specific Ideas

- The 70% cut in the row hints should line up with the Facepalm Score filter's High preset (70-100), so a user
  can open exactly the blunders a row counts.
- The Facepalm rows should read like the Blunders row beside them: same unit, same bar, only without the grey
  band.

</specifics>

<deferred>
## Deferred Ideas

- Benchmark zones and red/green verdicts for the facepalm rows; "chance blindness" / "threat blindness" as named
  readings — SEED-261120-bzq.
- Within-player bias against a benchmark, type-by-clock matrix, training weighting by type — SEED-261120-bzq.

### Reviewed Todos (not folded)
- The todo matcher returned four keyword-only hits (`172-deferred-review-findings`, bitboard storage for
  partial-position queries, WR-01 invalid Tailwind class, variation-tree nested button). None relates to this
  phase.

</deferred>

---

*Phase: 257-facepalm-rate-library-stats*
*Context gathered: 2026-11-20*
