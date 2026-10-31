---
title: Opponent-mirror as a self-calibrating cohort reference for action metrics
date: 2026-05-17
context: Captured during a /gsd-explore session on a proposed Conversion ΔES timeline (SEED-020). The user proposed computing opponents' Conv ΔES against the user as a reference line, instead of pulling from a /benchmarks-derived cohort band. The idea generalizes beyond that one chart, but only to action metrics (see the governing rule). The Conv ΔES use case that motivated the note was retracted on 2026-10-31.
related_files:
  - app/services/canonical_slice_sql.py
  - app/services/global_percentile_cdf.py
  - app/services/endgame_zones.py
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - reports/benchmarks-latest.md
related_seeds: [SEED-019, SEED-020, SEED-206]
related_phases: [87.2, 87.6, 88]
updated: 2026-10-31 (governing rule added after the SEED-206 peer-basis challenge; sharpened the same day to classify any split of a zero-sum quantity as shared-state, which retracts the Conversion/Recovery mirror and revises SEED-020)
---

# Opponent-mirror as a self-calibrating cohort reference

## Governing rule: which peer reference a metric gets

FlawChess has two ways to say "compared to players at your level":

- **You vs. your opponents** (Library Stats gap bars, the mirror lines in this note): the user's value
  against their opponents' value in the same games.
- **Peer distribution** (Endgames percentile chips, SEED-206): the user's value ranked against a
  rating × TC benchmark CDF, built with the canonical-slice builder.

The choice is decided by one question:

> **Does each player generate their own events for this metric, or is the underlying per-game
> quantity zero-sum between the two players?**

| Metric kind | Definition | Examples | Reference |
|---|---|---|---|
| **Action metric** | Each side produces its own events. The opponent's value cannot be derived from the game's shared state. | flaw rates, tactic motifs, clock remaining, running out of time | **You vs. your opponents** preferred. A peer CDF of the you-minus-opponent delta is also valid. |
| **Shared-state metric** | Built on a per-game quantity that is zero-sum between the players (result, eval, ΔES), **including any split or conditioned subset of it** | eval at a ply, came out of the opening worse/better, Conversion / Parity / Recovery ΔES and rates, score under time pressure, phase reached, game length | **Peer distribution only** |

**The rule is one-directional.** Shared-state metrics must not use the mirror. Action metrics can use
either reference: the mirror is the natural default, and a CDF chip that ranks the you-minus-opponent
delta (as `clock_gap` and `net_flag_rate` do) uses both at once, which is fine.

**Why:** for a zero-sum quantity, the opponent's value is a function of the user's in the same game
(centred eval: `opp = −user`; result: `opp = 1 − user`). The mirror then adds no information. Every
"you vs. opponent" comparison reduces to a comparison of the user with themselves.

**Splitting the games does not escape it.** Conditioning a zero-sum quantity on who is ahead (Conversion
vs. Recovery, came out worse vs. better, user under time pressure vs. opponent under time pressure)
assigns each game to one side's bucket. The opponent's value in their bucket is then the user's value in
the opposite bucket, negated. The two samples are drawn from disjoint games, but the comparison still
pits the user against themselves:

- Opponent's "came out worse" rate against the user = the user's "came out better" rate. Comparing them
  re-encodes the net and hides the predictive worse rate (SEED-206).
- Opponent's Conv ΔES against the user = −(the user's Recov ΔES). Comparing them re-encodes the user's
  combined Conv + Recov ΔES and misattributes one subskill to the other. Worked example: a user with
  typical conversion (Conv ΔES 0) and weak recovery (Recov ΔES −0.10). Their opponents convert at
  +0.10 against them, so the mirror reads "you convert worse than your opponents", while the user's
  conversion is fine and the weakness is in recovery.

**Test before choosing:** write the opponent's value of the metric, game by game, as a function of game
data. If it is a function of a zero-sum quantity in that game (result, eval, ΔES), the metric is
shared-state. This holds even when the user's own value of this particular metric is undefined in that
game because the split assigned the game to the other side's bucket.

**Corollary:** to put a shared-state question on the mirror, swap it for its action counterpart. For
"came out of the opening worse", that is the opening-phase flaw delta, which is noise-dominated
(benchmark §5.6). When the action counterpart is noise, the peer distribution is the only option.

**What the two references have in common (keep them consistent):**
- Both condition on rating: the mirror through matchmaking, per game; the CDF through the
  rating × TC cell.
- Both use a benchmark-derived typical band for the verdict, and colour only past a 99% gate.
- Only the mirror follows page filters. A peer-distribution value is a trait (canonical slice, ignores
  filters) and must say so in its popover.
- Only the mirror cancels measurement bias: both sides are scored by the same engine in the same
  games. A peer-distribution metric built on evals must check that the user's eval source matches the
  cohort's (lichess server evals vs. local Stockfish, ply convention) before its percentiles are
  trusted.

## Applied to the current CDF metrics (2026-10-31)

All 11 `CdfMetricId` families (`app/services/global_percentile_cdf.py`) were checked against the rule.
None should move to the mirror.

| CDF metric | Opponent's value in the same games | Kind | Verdict |
|---|---|---|---|
| `score_gap`, `achievable_score_gap`, `score_gap_parity`, `parity_rate` | `−user` (or `1 − user`) on the same games | shared-state | Keep the CDF |
| `score_gap_conv`, `recovery_score_gap` | Opponent's Conv ΔES = −(user's Recov ΔES), and the reverse | shared-state (split) | Keep the CDF |
| `conversion_rate`, `recovery_rate` | Opponent's conversion rate is roughly 1 − user's recovery rate | shared-state (split) | Keep the CDF |
| `time_pressure_score_gap` | Already built as a mirror on score: `S｜user pressured − (1 − S｜opp pressured)` | shared-state (split) | Keep the CDF. The value is a composite (handling your own time trouble plus exploiting the opponent's), so popover copy must not claim "you handle time pressure better than your opponents". |
| `clock_gap` | Each side's own clock | action | Already a you-minus-opponent delta, and the CDF ranks that delta. Clock data is not engine-scored, so the eval-source caveat does not apply. Switching to gap bars would only buy filter-following and consistency with Library Stats. No change. |
| `net_flag_rate` | Each side runs out of time on its own | action | Same as `clock_gap`: already `opp flags − user flags`. No change. |

## The idea in one sentence

For any **action** metric the user cares about, the user's *opponents'* value of that same metric,
computed across the user's imported games, is a personalized, rating-matched, TC-matched,
platform-correct reference cohort that requires no /benchmarks lookup and drifts with the user
automatically.

## Why it works

Online chess matchmaking on both chess.com and lichess pairs players within a narrow rating window. Across a user's import:

- **Rating-matched.** Opponents cluster near the user's rating at the time of each game.
- **TC-matched.** Bullet games pair with bullet-rated opponents; rapid with rapid. The opponent pool for each TC is calibrated to the user's TC-specific rating.
- **Self-calibrating temporally.** As the user climbs in rating, opponents climb with them. The reference is anchored to *what the user is actually facing now*, not a frozen benchmark snapshot.
- **Platform-correct.** No Lichess-vs-chess.com sigmoid calibration question, since the comparison is intra-platform per combo by construction.
- **No external dependency.** Everything derives from the user's own games. No /benchmarks DB hit at request time, no `endgame_zones.py` table to maintain for this reference.

The same reference addresses the cohort drift that makes raw rate timelines hard to read: the user's
line and the mirror line drift together, so deviation between them (not absolute level) is the signal.

## The interpretation caveat (must appear in any popover)

The opponent mirror is **not** "peer cohort average." It is **"this user's opponents' value of the
metric, in games against this user."** Even for action metrics the user influences the opponent's
value: a user who plays sharp, forcing chess raises their opponents' blunder rate, and a fast player
pushes opponents into time trouble. Labels must say "your opponents vs you", never "average player".

## Retracted: the Conversion/Recovery mirror (2026-05-17 → 2026-10-31)

The original version of this note argued that Conversion and Recovery ΔES were mirror-eligible because
`S_user` (games where the user entered the endgame up) and `S_opp` (games where the opponent did) are
disjoint, so the two values are independent samples rather than an algebraic negation. It accepted that
the mirror "folds in the user's recovery skill" and called the composite reading a feature.

The disjoint-sets argument is true but beside the point. Independent samples are not new information:
the opponent's Conv ΔES over `S_opp` is exactly the negated user Recov ΔES over the same games, a number
the user already has. The comparison is therefore user-vs-self, and it misattributes skill between the
two subskills (worked example in the governing rule). This is the same structure as "came out worse vs.
came out better" (SEED-206), which the note had already rejected. Conversion, Parity and Recovery ΔES and
their raw rates are shared-state metrics and get the peer distribution. SEED-020 was revised
accordingly.

## Where this is reusable

| Surface | Mirror metric | Notes |
|---|---|---|
| Library Stats gap bars | Opponents' flaw rates and tactic motifs vs user | Already shipped; the reference implementation of this note. |
| Time-management metrics | Opponents' clock and flag values | Already partially in place: `clock_gap` and `net_flag_rate` are user − opponent deltas (with a CDF chip on top). |
| Time-management timelines (hypothetical) | Opponents' clock at endgame entry vs user, per week | The cleanest timeline use case: pure action metric, no engine in the loop. |
| Endgame ELO timeline | Already covered | Non-Endgame ELO is the self-baseline; a mirror would duplicate it. |

## When *not* to use this

- **Shared-state metrics, including any split of one.** Conversion / Parity / Recovery ΔES and rates,
  entry evals, came out of the opening worse/better, score under time pressure. See the governing rule.
- **Sample-too-thin combos.** The same active-weeks gate that applies to the user's line must apply to the mirror, and the mirror sample can be smaller. Drop the combo, do not show only one line.
- **When the user's import is small.** Mirror lines are noisy below ~30 games per combo. The same threshold guidance that gates the user's line should gate the mirror.

## Timelines: mirror vs. peer distribution

SEED-019 produces a cohort CDF for percentile annotations on scalar values. For *timelines*, a chip on
every weekly point is unreadable, so the reference has to be a line or a band.

- **Action-metric timelines** get the mirror line: personalized, rating-drift-aware by construction.
- **Shared-state timelines** (e.g. Conv ΔES, SEED-020) get a peer band instead: the cohort CDF's typical
  range (p25–p75) at the user's rating anchor and TC for each week, read from `benchmark_cohort_cdf`.
  The band moves with the user's rating, which supplies the drift-awareness the mirror was supposed to
  give. A bare zero line is a poor fallback for metrics whose typical band sits off zero (Conversion
  and Recovery, see `endgame_zones.py`).

## Implementation cost reuse

A frontend timeline component that renders a (user, reference) pair can serve both: a mirror line for
action metrics and a shaded peer band for shared-state metrics. Each new chart is then a backend
aggregator plus a thin component variant.

## Cross-references

- Revised by this rule: SEED-020 (Conv ΔES timeline), now a peer band instead of a mirror line.
- Shared-state precedent: SEED-206 (came out of the opening worse/better).
- Adjacent approach: SEED-019 (cohort percentile annotations for scalar metrics).
- Benchmark cohort effect anchor: `reports/benchmarks-latest.md` §3.2.2, §3.2.3.
- Visual / structural template: `frontend/src/components/charts/EndgameEloTimelineSection.tsx`.
- Popover discipline: project memory `feedback_popover_copy_minimalism.md`.
