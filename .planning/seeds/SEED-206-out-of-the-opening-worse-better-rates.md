---
id: SEED-206
status: dormant
planted: 2026-10-31
planted_during: v2.27 (after Phase 242), /gsd-explore session on opening narration → sketch 013
trigger_when: owner opens the next Openings milestone/phase, or asks to implement sketch 013 / the "out of the opening" stat
scope: small-medium (slimmed 2026-10-31); one phase, ~3–4 plans. Backend first (canonical-slice builder, CDF regen, Stage B family, ranked read path + parity test incl. per-eval-source check), then frontend (Stats-tab section + popover histogram). No per-opening bars.
priority: solid contained improvement, not urgent; a good candidate when a milestone has room for an Openings phase, but don't displace higher-impact work for it
---

# SEED-206: "Out of the opening": peer-ranked worse/better rates on the Openings Stats tab

## Why This Matters

The Openings tab has no answer to "compared to players at my level, how solid am I out of the
opening?". The benchmark shows that the share of games a player leaves the opening clearly worse is:

- a reliable per-player trait (reliability 0.95 at ≥100 games);
- the opening signal that best predicts results within a rating × TC cell (−1.06 pp score per SD). The
  mean eval adds nothing once this rate is known.

The opening-phase flaw delta can't answer the question: it is noise-dominated (simulated noise share
about 70% of the between-player IQR per TC, benchmark §5.6/§5.15; the closed-form 183% overstates it).
The Library "Game phase → Opening" row shows that delta, so it is no substitute for this stat. This
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
- **Copy:** "an eval 1.0 or more below a typical opening position" ("above" for better). Never use
  "pawns" as the eval unit; say "eval" where a term is needed.

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
  - **The worse rate is the primary row** (it carries the predictive signal, −1.06 pp score per SD).
  - **The better rate is secondary context** (about +0.04 pp per SD). It is kept for the sharp vs.
    solid distinction, styled as the lesser row and never driving the card's headline.
- Words carry the inverted meaning: "Fewer worse games than 58% of peers".
- Below-floor and pending states as on Endgames.
- **Not a stacked worse / even / better bar**: it reads as W/D/L.

### Popover
- Explains what the rate means.
- Shows a histogram of the player's eval after the opening, with the ±1.0 cuts and the selected side
  dark.
- The footer gives counts, the peer band and the percentile in words, plus the percentile-chip
  disclosures: who the peers are, ranked games only, filter independence, rating dependence.

### Per opening: cut from scope (owner, 2026-10-31)
- **No worse/better bars in the repertoire expanded card.** They would mostly duplicate the Phase 242
  "Eval after opening" verdict bar, and at 20–60 games per opening a tail rate is noisier than the
  mean (SE about 6.4 pp at n=40, p=0.21).
- Current form per opening stays with the existing filter-following eval and score bars.
- Original design, in case it is revisited: same two bars, against the peer typical band at the
  user's rating × TC, dot colour from a 99% binomial test against the peer median, faded under 20 games.

## Rejected (do not reopen without new evidence)

- **Within-player SD of the eval after the opening as "solidity":** it mixes both tails and mostly
  tracks rating (ELO d 3.85).
- **"You vs. your opponents" (the 010-style zero-centred gap):** for a shared eval, "opponent came out
  worse" ≡ "you came out better". Both rates collapse into one identity (better − worse), so a sharp
  30/30 player reads the same as a solid 12/12 one. Unlike the Conversion/Recovery case, this is a
  pure identity, not a composite (see `opponent-mirror-as-self-calibrating-cohort.md`, "Governing
  rule": shared-state metrics get a peer distribution). Dropping the better rate does not escape it:
  "came out worse vs. opponents" alone still compares against the user's own better rate.
- **A custom ~200-game "current" window:** it breaks the canonical-slice symmetry between the CDF and
  the user value, and the percentile is too wobbly (SE ≈ 2.8 pp against a ~13 pp peer IQR).
- **Per opening-family peer comparison:** n is too thin and the cells too sparse.
- **Ranking a "net" (better − worse):** it re-encodes the mean eval and dilutes the worse rate's signal.

## Feasibility findings (prod + benchmark DB, 2026-10-31)

### Floor coverage (prod, canonical slice, non-guest, ≥30 qualifying games per colour × TC)

| TC | users with slice games | ≥1 colour passes | both colours pass |
|---|---:|---:|---:|
| rapid | 489 | 377 | 363 |
| blitz | 428 | 304 | 298 |
| bullet | 108 | 70 | 69 |
| classical | 186 | 27 | 23 |
| **any TC** | **528** | **458** | **451** |

- About the same reach as the broadest Endgames chips (`score_gap`, `clock_gap`: about 480 users),
  more than conversion/parity/recovery (270–360). Only classical is thin.
- Eval coverage at middlegame entry: 99.4% of the games that reach the middlegame. Games that end in
  the opening by result add about 5% qualifying games. Benchmark coverage is also near 100%.

### Eval source: not a blocker

- **The sources differ between CDF and user.** At middlegame entry, the benchmark DB is mostly
  entry-lane evals (depth 15, aligned ply convention): 89% bullet, 69% blitz, 59% rapid, 29%
  classical, the rest lichess or local full. Prod slice games are about 90% local full evals, about 10%
  lichess, about 0% entry-lane only.
- **Benchmark, local-full vs. entry-only within rating × TC cells** (local full is assigned by the
  random lottery, so this isolates the instrument): worse-rate differences of −2.9 to +2.5 pp over
  18 cells (sampling SE about 1.4 pp), average about −0.3 pp. Mean centred eval about +5 cp on local
  full.
- **Prod, paired per user × TC, lichess-eval vs. local games** (214 pairs, ≥30 each, lichess
  platform): worse rate −0.08 pp (SE 0.43), better rate +0.56 pp, mean eval +5 cp. This also rules
  out a sign or convention bug on the local path.
- **Conclusion:** at ±1.0 the instrument and ply-convention differences move the rate by under about
  1 pp against a ~13 pp peer IQR. Keep a per-source parity check in the phase's tests, but it is no
  longer a gate.

### Expected high skew for FlawChess users

- The pooled prod mean centred eval at middlegame entry is about **+40 cp** for the user, against
  about 0 in every benchmark cell. Owner's read (2026-10-31): FlawChess users are a self-selected,
  ambitious population (fringe-tool seekers, GM Noel Studer's newsletter), not a random lichess or
  chess.com sample. This is expected, not a bug.
- **Consequence:** against the lichess peer CDF, many users will land above the median, and the 99%
  gate will colour green more often than red. The popover's "who the peers are" disclosure carries
  real weight; the copy must not imply the peers are other FlawChess users.

## Open for discuss-phase

- One CDF per TC pooled over colours, or one per colour.
- The exact definition of the section's 99% significance test.
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
