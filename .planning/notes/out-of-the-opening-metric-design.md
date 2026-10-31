---
title: "Out of the opening" — worse/better rates, peer basis, and the reasoning behind them
date: 2026-10-31
context: Captured from a /gsd-explore session that started as "an LLM narration for the Openings tab" and narrowed to a new opening statistic. Records the full chain of reasoning, the benchmark numbers that drove each decision, and the options that were rejected, so the phase that implements SEED-206 does not re-litigate them.
related_files:
  - .planning/sketches/013-out-of-the-opening/index.html
  - .planning/sketches/013-out-of-the-opening/analysis/
  - app/services/canonical_slice_sql.py
  - app/services/user_benchmark_percentiles_service.py
  - app/services/endgame_ranked_service.py
  - app/services/position_classifier.py
  - app/services/opening_insights_constants.py
  - frontend/src/components/endgames/stats/RankedMetricRow.tsx
  - frontend/src/components/endgames/stats/PercentileBar.tsx
  - reports/benchmark/benchmarks-latest.md
related_notes:
  - .planning/notes/opponent-mirror-as-self-calibrating-cohort.md
  - .planning/notes/percentile-chip-canonical-slice.md
related_seeds: [SEED-204, SEED-206]
related_sketches: ["013"]
---

# "Out of the opening": worse/better rates

## How we got here

1. **Starting idea: an LLM narration for the Openings tab**, like the Endgame and time-management
   narration. It would answer: how do I do in the opening compared to players at my level, how do my
   favourite openings do, which positions should I study, and should I study openings or tactics?
2. **Scope cut to the Openings tab.** "Openings or tactics?" compares phases and would need the
   cross-page payload, so it was dropped from this scope.
3. **Data reality check** (benchmark §2.1 and §5):
   - The eval after the opening (at middlegame entry) is a real per-player signal. Players differ by
     58.5 cp (SD of their averages, baseline-centred), while one game's eval scatters by 237 cp.
   - The opening-phase flaw delta (you − opponent, §5.6) is noise-dominated: 183% noise share, and
     hasty×opening 227%. Any narration built on it would narrate noise.
   - No opening percentiles existed. The CDF table only held endgame and time metrics.
   - Phase 242 already turned per-opening findings into 99%-gated cards, so an LLM would mostly reword
     them unless it added peer comparison.
4. **The owner's idea: use the spread of the eval after the opening as a "solidity" measure.** We
   measured it instead of assuming it. Peer comparison then became the real question, so **the LLM
   narration was tabled** in favour of the statistic itself.

## Measurement (benchmark DB, 2026-10-31)

Scripts are in `.planning/sketches/013-out-of-the-opening/analysis/`. Each data point is one benchmark
cell: a user × colour × TC × game-time ELO bucket, with ≥20 games. The cohort recipe is the same as
§2.1 (equal footing, sub-800 dropped). The 9,109 cells match §2.1 exactly.

How to read the table:
- *Reliability* is the share of between-player variance that is real (not sampling noise), at ≥100
  games.
- *d* is Cohen's d across colours, TCs or ELO buckets; small means the metric "collapses" across that
  axis, so one zone can serve all of it.
- *Score per SD* is how many score points one SD of the metric moves, within ELO × TC.

| per user × colour metric | reliability ≥100 g | colour d | TC max\|d\| | ELO max\|d\| | score per SD (within ELO×TC) |
|---|---:|---:|---:|---:|---|
| mean centred eval | 0.92 | 0.03 | 0.18 | 0.08 | +0.93 pp alone; ≈0 once the worse rate is in |
| within-player SD | 0.98 | 0.01 | 0.54 | **3.85** | −0.60 pp (next to the mean) |
| worse rate (≤ −1.0) | 0.95 | −0.05 | 0.33 | 1.86 | **−1.06 pp** |
| better rate (≥ +1.0) | 0.92 | 0.08 | 0.37 | 2.48 | +0.04 pp |
| actual score | 0.52 | — | — | — | — |

What the numbers mean:
- **Within-player SD was rejected as "solidity".** It treats both tails the same, so a player whose
  opponents often blunder in the opening looks "unsolid". It correlates with both tails (0.76 and
  0.69), and it mostly tracks rating (325 cp at 800 down to 126 cp at 2400).
- **One-sided tail rates say what we mean.** Coming out busted is what costs points. In a regression
  with both, the worse rate absorbs the mean eval's effect (the mean's beta drops to −0.23).
- **Noise is not the problem here, unlike the flaw deltas.** The opening as a whole explains only about
  5% of score variance within a level (R² 0.054). That's useful context for any later "openings or
  tactics?" narration.
- **Colour collapses for every metric**, so one CDF can rank both colours.

## Metric definition (locked)

Per game, from the user's point of view:
1. **The game reaches the middlegame** (Lichess Divider rule, `position_classifier.assign_game_phases`;
   median entry at ply 21). Take the eval at the first middlegame ply and subtract the colour baseline
   (+0.25 White, −0.25 Black, `EVAL_BASELINE_PAWNS_*`). A mate score counts by its sign.
2. **The game ends in the opening** (about 5% of games; 3% at the per-player median):
   - resignation, checkmate or timeout counts by result (a loss is "worse", a win is "better");
   - abandoned games and draws are excluded.
   The §2.1 recipe silently drops these games, yet they are the clearest opening disasters.
3. **Worse** if the centred eval is −1.0 or below; **better** if it is +1.0 or above. Because of the
   centring, the raw cut is −0.75 for White and −1.25 for Black. User copy says "an eval 1.0 or more
   below a typical opening position" and never uses "pawns" as the eval unit.

**Threshold sweep** (`fetch_sweep.py` / `analyze_sweep.py`, counting games that end in the opening;
9,186 cells):

| threshold | worse rate median at 800 / 1600 / 2400 | score per SD | R² |
|---:|---|---:|---:|
| 0.5 | 41% / 32% / 25% | −0.81 | 0.031 |
| 0.75 | 37% / 26% / 17% | −0.95 | 0.042 |
| **1.0** | **35% / 21% / 13%** | **−0.99** | **0.046** |
| 1.5 | 30% / 15% / 8% | −1.00 | 0.047 |
| 2.0 | 26% / 11% / 5% | −0.98 | 0.046 |
| 3.0 | 20% / 7% / 3% | −1.00 | 0.047 |

Why ±1.0:
- It is the lowest cut on the predictive plateau. Higher cuts make the rate rare at high ratings
  (5% at 2400 for 2.0) and the per-player estimate noisier, for no gain.
- It matches chess convention: the middle of the Informant "±" (clear advantage) band, and about a 41%
  expected score on the lichess sigmoid.
- Reliability stays at 0.95 and colour stays collapsed (|d| ≤ 0.15) at every threshold.
- Counting games that end in the opening gives the better rate some predictive value (+0.64 pp at 1.0),
  but the worse rate stays the stronger signal.

## Display decisions

- **Per colour, collapsed over lines.** Per opening family was rejected: too few games per player
  (20–60 per cell), the peer CDF cells would be sparse, and Phase 242 already tests each opening against
  the absolute colour baseline.
- **No 100% stacked "worse / even / better" bar.** It reads as W/D/L whatever the colours.
- **Sketch 013, winner Variant A:**
  - one card per played TC, each with two `RankedMetricRow`s and the Endgames `PercentileBar`
    (*superseded 2026-10-31:* ranked per TC but displayed as one game-weighted card per colour, see
    SEED-206 "Cross-TC agreement");
  - words carry the inverted meaning for "worse" ("Fewer worse games than 58% of peers"), because a
    bare "58th" is ambiguous for a lower-is-better metric;
  - "even" stays implicit.
- **The popover** explains what the rate means and shows a histogram of the player's eval after the
  opening, with the ±1.0 cuts marked. Its footer gives counts, the peer band, the percentile in words,
  and the percentile-chip disclosures: who the peers are, ranked games only, filter independence,
  rating dependence.
- **Per opening:** the same two bars go in the repertoire expanded card, next to Score over Time:
  - against the peer typical band at the user's rating × TC, not a percentile;
  - the dot colour comes from a 99% binomial test against the peer median;
  - faded and verdict-neutral under 20 games.

## Peer basis: rating × TC canonical-slice CDFs, not "you vs. your opponents"

**The owner's challenge:** why not the Library approach, comparing you with your opponents in your own
games? It would come with rating control for free, follow the page filters, work per opening, and need
no CDF infrastructure. For a moment it looked better. It collapses one step later:

- **For a shared position-state metric, the opponent's centred eval is exactly minus yours**, because
  the eval is shared and the baselines mirror each other. So "your opponent came out worse" IS "you
  came out better", game by game.
- "Your worse vs. the opponent's worse" then equals "your worse vs. your better", and the "better"
  comparison is the same gap with the sign flipped. **The two metrics couple into one degree of
  freedom.**
- The rejected gap (better − worse) is well-behaved on its own terms (ELO d 0.09, TC d 0.20,
  reliability 0.90, see `analyze_opponent_gap.py`). But it can't tell a sharp 30/30 player from a solid
  12/12 one, and that distinction was the point of the feature.
- **This is worse than the Endgame Conversion/Recovery coupling.** There the opponent's value came from a
  disjoint set of games: a composite, but an independent sample. Here it is a pure identity, like the
  Parity case. `opponent-mirror-as-self-calibrating-cohort.md` already lists "entry eval" under "When
  not to use this".
- **Rating × TC CDFs keep the two rates independent.** Each rate is ranked against its own peer
  distribution, and the two are nearly uncorrelated within a cell (ρ 0.17).

## Window: the Endgames rule, not a custom "current" window

- **First proposal:** the player's most recent ~200 ranked games per colour and TC, so the section shows
  current form.
- **Rejected for two reasons:**
  - The live CDFs and the user's value are built by the **same** builder in `canonical_slice_sql.py`
    (most recent 3000 games within 36 months per TC, rated, ±100 opponents, floor 30). A custom window
    breaks that symmetry. The "200 ≈ benchmark per-player n" argument compared against §2.1 cells,
    which are not what the live CDFs are built from.
  - At 200 games and a 20% rate the standard error is about 2.8 pp against a ~13 pp peer IQR, so the
    95% interval spans roughly the 30th to 70th percentile.
- **Accepted trade-off:** the section is a trait like Elo, not a view. It does not follow page filters,
  and it moves slowly when a repertoire changes.
- **Current form lives in the per-opening cards**, which follow the page filters and the Phase 242
  current/past grouping. An "out of the opening over time" chart is a possible later addition.

## Open for discuss-phase

- **Prod distribution:** how many users clear the floor of 30 games per colour × TC on the canonical
  slice? Is the eval coverage at middlegame entry high enough on the local engine eval path?
- **One CDF per TC with both colours pooled** (colour collapses), or one per colour. Each user would
  contribute one point per colour either way.
- **Significance definitions.** The section gate is a 99% test of the rate against the peer median.
  The per-opening binomial test needs to be specified against the peer median at the user's anchor.
- **The eval ply convention** (`project_eval_cp_post_move_sampler_defect`): the §2.1 recipe reads
  `eval_cp` at the entry ply as is. Check that this is consistent for lichess-eval vs locally evaluated
  games before building the CDF.
- **The chess.com rating mapping** (`composed_chesscom_to_lichess_grid`) applies as for the Endgames
  anchors.
- **The tabled LLM narration** can later consume these two percentiles together with the Phase 242
  findings.
