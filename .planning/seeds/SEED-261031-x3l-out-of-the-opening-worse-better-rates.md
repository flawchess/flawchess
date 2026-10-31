---
id: SEED-261031-x3l
status: dormant
planted: 2026-10-31
planted_during: v2.27 (after Phase 242), /gsd-explore session on opening narration → sketch 013
trigger_when: owner opens the next Openings milestone/phase, or asks to implement sketch 013 / the "out of the opening" stat
scope: medium; one phase with several plans, backend wave first (canonical-slice builder, CDF regen, Stage B family, ranked read path + parity test, per-opening rates on the openings endpoints), then frontend (section, popover histogram, expanded-card bars)
---

# SEED-261031-x3l: "Out of the opening": peer-ranked worse/better rates on the Openings Stats tab

## Why This Matters

The Openings tab has no answer to "compared to players at my level, how solid am I out of the
opening?". The benchmark shows that the share of games a player leaves the opening clearly worse is:

- a reliable per-player trait (reliability 0.95 at ≥100 games);
- the opening signal that best predicts results within a rating × TC cell (−1.06 pp score per SD). The
  mean eval adds nothing once this rate is known.

The opening-phase flaw delta can't answer the question: it is noise-dominated (183% noise share). This
stat replaces the tabled LLM opening narration as the first step, and a later narration can consume it.

Full reasoning, benchmark tables and rejected options: `.planning/notes/out-of-the-opening-metric-design.md`.

## Locked decisions (owner, 2026-10-31)

### Metric
- Take the user-POV eval at the first middlegame ply minus the colour baseline (+0.25 White,
  −0.25 Black, `EVAL_BASELINE_PAWNS_*`).
  - **Worse** if it is −1.0 or below, **better** if +1.0 or above. A mate score counts by its sign.
- **Games ending before the middlegame count by result** when they end by resignation, checkmate or
  timeout (a loss is worse, a win is better). Abandoned games and draws are excluded.
- **Why ±1.0:** it is the lowest threshold on the predictive plateau in a 0.5–3.0 sweep, and it matches
  the Informant "±" clear-advantage band (about a 41% expected score).
- **Copy:** "a pawn or more worse than a typical opening position". Never quote raw evals or say
  "pawns".

### Peer basis
- **Rating × TC CDFs on the Endgames canonical slice.** Add a new builder in
  `app/services/canonical_slice_sql.py`, reused by both `gen_global_percentile_cdf.py` and
  `user_benchmark_percentiles_service.py`.
  - Slice: most recent 3000 games within 36 months per TC, rated, opponents within ±100.
  - Floor: 30 games per colour × TC.
  - 99% significance gate for red/green. Filter-independent.
- **Colour collapses** (|d| ≤ 0.15), so one CDF per TC can rank both colours.

### Section UI (sketch 013, Variant A)
- A new "Out of the opening" section at the top of the Stats tab, under the sticky White | Black
  switch.
- One card per played TC, each with two `RankedMetricRow` + `PercentileBar` rows.
- Words carry the inverted meaning: "Fewer worse games than 58% of peers".
- Below-floor and pending states as on Endgames.
- **Not a stacked worse / even / better bar**: it reads as W/D/L.

### Popover
- Explains what the rate means.
- Shows a histogram of the player's eval after the opening, with the ±1.0 cuts and the selected side
  dark.
- The footer gives counts, the peer band and the percentile in words, plus the percentile-chip
  disclosures: who the peers are, ranked games only, filter independence, rating dependence.

### Per opening
- The same two bars go in the repertoire expanded card, next to Score over Time.
- The reference is the peer typical band at the user's rating × TC, not a percentile.
- The dot colour comes from a 99% binomial test against the peer median.
- Faded and verdict-neutral under 20 games. Follows the page filters, so current form shows here.

## Rejected (do not reopen without new evidence)

- **Within-player SD of the eval after the opening as "solidity":** it mixes both tails and mostly
  tracks rating (ELO d 3.85).
- **"You vs. your opponents" (the 010-style zero-centred gap):** for a shared eval, "opponent came out
  worse" ≡ "you came out better". Both rates collapse into one identity (better − worse), so a sharp
  30/30 player reads the same as a solid 12/12 one. Unlike the Conversion/Recovery case, this is a
  pure identity, not a composite (see `opponent-mirror-as-self-calibrating-cohort.md`, "When not to
  use this").
- **A custom ~200-game "current" window:** it breaks the canonical-slice symmetry between the CDF and
  the user value, and the percentile is too wobbly (SE ≈ 2.8 pp against a ~13 pp peer IQR).
- **Per opening-family peer comparison:** n is too thin and the cells too sparse.
- **Ranking a "net" (better − worse):** it re-encodes the mean eval and dilutes the worse rate's signal.

## Open for discuss-phase

- How many prod users clear the floor of 30 per colour × TC, and what the eval coverage is at
  middlegame entry.
- One CDF per TC pooled over colours, or one per colour.
- The exact definitions of the significance tests (section and per opening).
- Eval ply convention consistency, lichess-eval vs local
  (`project_eval_cp_post_move_sampler_defect`).
- Whether the eventual opening LLM narration consumes these percentiles.

## Breadcrumbs

- Sketch: `.planning/sketches/013-out-of-the-opening/` (index.html; `analysis/` holds the benchmark
  scripts: `fetch_cells.py`, `analyze.py`, `fetch_sweep.py`, `analyze_sweep.py`,
  `analyze_opponent_gap.py`).
- Reasoning note: `.planning/notes/out-of-the-opening-metric-design.md`.
- Backend: `app/services/canonical_slice_sql.py`, `app/services/user_benchmark_percentiles_service.py`,
  `app/services/endgame_ranked_service.py`, `app/repositories/benchmark_cohort_cdf_repository.py`,
  `app/services/position_classifier.py` (phase rule), `app/services/opening_insights_constants.py`
  (baseline), `scripts/gen_global_percentile_cdf.py`.
- Frontend: `frontend/src/components/endgames/stats/RankedMetricRow.tsx`, `PercentileBar.tsx`,
  `RankedMetricPopover.tsx`; `frontend/src/pages/openings/StatsTab.tsx`;
  `frontend/src/components/openings/stats/RepertoireCard.tsx` (expanded card).
- Related: SEED-204 / Phase 242 (Openings Stats rework, baseline centring, current/past grouping);
  `.planning/notes/percentile-chip-canonical-slice.md`; benchmark §2.1 and §5.6/§5.15.
