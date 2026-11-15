---
id: SEED-261115-sgs
status: dormant
planted: 2026-11-15
planted_during: v2.29, Phase 254 executing; /gsd-explore session with the owner
trigger_when: when the next Openings stats page or opening-insights phase is planned, or when a user reports misreading a slump in the "Score over time" chart
scope: small. One extra per-game series in the opening timeline payload, a window constant change, a second line in ScoreChart, reference line moved to the colour baseline, typical band dropped
---

# SEED-261115-sgs: Opening "Score over time" chart, eval-expected score as the primary line

Change the per-opening "Score over time" chart on the opening stats page so that the primary line is the
**eval-expected score** over a rolling **100-game** window, with the actual score as a fainter secondary line
on the same axis (owner decision, 2026-11-15).

- **Eval-expected score:** per game, take the Stockfish eval at middlegame entry (first `phase=1` row, user
  perspective, mate handled), convert it with `eval_utils.eval_cp_to_expected_score`, then average over the
  window. Convert per game and average; never convert the mean eval.
- **Window:** 100 games instead of today's 50 (`ROLLING_WINDOW_SIZE` in `app/services/openings_service.py`).
- **Actual score:** kept, drawn fainter, same axis.

## Why This Matters

The chart is meant to answer four questions: is the opening holding up, do I need to study it more, is my
study paying off, and how does it compare with my other openings. Today's rolling-50 score line mostly shows
chance. A player sees a slump and blames the opening (or a bad phase) when nothing real changed.

Measured on 2026-11-15. Each opening's games were split into consecutive non-overlapping blocks of W games;
"noise" is the wobble chance alone produces, "signal" is real movement between blocks. Standard deviations in
percentage points.

Benchmark DB (80 openings with 300+ games, 77 users, 94% eval coverage):

| Window | Score noise | Score signal | Eval-expected noise | Eval-expected signal |
|---|---|---|---|---|
| 25 | 9.6 | 1.9 | 3.9 | 1.5 |
| 50 | 6.8 | 1.5 | 2.7 | 1.1 |
| 100 | 4.8 | 1.0 | 1.9 | 1.6 |

Dev DB (26 openings with 600+ games, 6 heavy users):

| Window | Score noise | Score signal | Eval-expected noise | Eval-expected signal |
|---|---|---|---|---|
| 50 | 5.5 | 3.3 | 1.8 | 1.9 |
| 100 | 3.9 | 3.0 | 1.3 | 1.0 |
| 200 | 2.8 | 2.8 | 0.9 | 0.6 |

- The score line is about 95% chance at 50 and at 100 games in the benchmark population. Matchmaking pins
  score near 50%, so there is little real drift to show.
- The eval-expected line has similar real drift but 2.5x less noise, so signal and noise are about equal at
  100 games. Usable for "is it holding up", marginal for "is my study paying off".
- Heavy users with long histories show about 3 points of real score drift, so the score line still carries
  something for them.
- The signal figures are differences of two variances and are rough; treat 1.1 and 1.6 as the same number.
- Grouping was by `games.opening_name`, not by position hash as the app does.

## Decided Against

- **Twin axis (eval in cp on a second axis):** the two scales are arbitrary relative to each other, so
  apparent agreement or divergence is an artefact of axis choice. Converting eval to expected score puts both
  lines on one axis.
- **Correcting for overall form** (subtracting the user's other same-colour games over the same period): it
  raised noise from 6.8 to 11.3 points at 50 games and from 4.8 to 8.5 at 100, because players with many
  games in one opening have only 30 to 50 other same-colour games per block. Correlation between the opening's
  score and those other games was 0.05 at 50 games and 0.25 at 100. A baseline reference line would be as
  jumpy as the line it is meant to explain.
- **Noise bands:** clutter (owner).

## Locked Decisions (owner, 2026-11-15)

1. **Openings under 100 games:** keep today's behaviour. The window is "last up to 100 games" and a point is
   emitted once it holds `MIN_GAMES_FOR_TIMELINE` (10) games. No hard 100-game floor.
2. **Reference line and typical band:** move the reference line from 50% to the colour baseline of the
   eval-expected line (the +25 cp / -25 cp baseline from `opening_insights_constants.EVAL_BASELINE_*`
   converted with the same curve, about 52.3% for White and 47.7% for Black). Drop the typical band: it is
   calibrated for actual score and no benchmark band for eval-expected exists. A new band is out of scope.
3. **Level gap between the lines:** ship without recalibrating the curve. One popover sentence says the
   expected line reflects only the position reached out of the opening, so the actual line can sit above or
   below it. For one dev user, actual score sat 4 to 11 points above eval-expected in all six openings
   checked; whether that is real post-opening outperformance or the Lichess curve being fit on 2300+ rapid
   is not settled and belongs to SEED-203.
4. **Games without an eval:** skip them in the eval-expected average, keep them in the actual score. The two
   lines can rest on different game counts, so the tooltip shows the eval game count.
5. **Names:** "Expected score from opening eval" (primary) and "Actual score" (secondary). The chart title
   stays "Score over time". Copy says "eval", never "pawns".

## Implementation Notes

- **Not decided:** whether the chart's shared score verdict fields move to the eval-expected series. Leave
  them on actual score unless the owner says otherwise.
- **Query cost:** the timeline needs the middlegame-entry eval per game across full history. The existing
  aggregate query is `stats_repository` (`OpeningPhaseEntryMetrics`). Check the plan on a heavy user.
- **Window constant:** `ROLLING_WINDOW_SIZE` is used only by the openings timeline; the endgame charts have
  their own.
- **Isolation:** if a phase is executing in the main checkout, run this in a separate worktree.

## When to Surface

**Trigger:** when the next Openings stats page or opening-insights phase is planned, or when a user reports
misreading a slump in the "Score over time" chart.

## Scope Estimate

**Small.** Backend: add a per-game eval-expected value to the rows feeding the timeline builder in
`openings_service.py`, widen the window constant, emit a second rolling series. Frontend: second line in
`ScoreChart.tsx`, colours from `theme.ts`, popover copy.

## Breadcrumbs

- `app/services/openings_service.py`: `ROLLING_WINDOW_SIZE`, `MIN_GAMES_FOR_TIMELINE`, `_rolling_score`, the
  weekly timeline builder
- `app/repositories/openings_repository.py`: the full-history rolling-window query
- `app/repositories/stats_repository.py`: `OpeningPhaseEntryMetrics`, middlegame-entry row selection
- `app/services/eval_utils.py`: `LICHESS_K`, `eval_cp_to_expected_score`
- `app/services/train_pool.py`: `expected_score_sql` (SQL form of the same sigmoid, mate handling)
- `app/services/opening_eval.py`: per-colour eval baseline (Phase 242)
- `frontend/src/components/charts/ScoreChart.tsx`, `frontend/src/components/openings/stats/RepertoireCard.tsx`
- SEED-203 (expected-score curve refit per Elo x TC)
