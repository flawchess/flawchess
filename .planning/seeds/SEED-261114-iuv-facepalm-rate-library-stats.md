---
id: SEED-261114-iuv
status: dormant
planted: 2026-11-14
planted_during: Phase 250 executing (facepalm-blunder selection); /gsd-explore session with the owner
trigger_when: now (owner, 2026-11-20). Scope narrowed to the benchmark-free part; the deferred part is SEED-261120-bzq
scope: medium. Facepalm rate in the library stats (timeline line, you vs opponents, per type), chip colour by type. Part A (opponent scoring) is done on prod
---

# SEED-261114-iuv: Facepalm rate in the library stats (timeline and you vs opponents)

Add facepalm statistics to the library stats: a facepalm-rate line in the Flaws Timeline and a "you vs your
opponents" facepalm-rate comparison. Follow-up to SEED-261114-0ke (filter and card chip).

## Current scope (2026-11-20, supersedes conflicting text below)

This seed is the part that is built now. Everything that reads a benchmark zone moved to
`SEED-261120-bzq-facepalm-benchmark-zones-and-clock-matrix.md`. The sections below are kept as history; where
they conflict with this section, this section wins.

**In scope**

1. Stats cut: a new constant at 0.7, separate from `FACEPALM_SCORE_MIN` (0.5). Lambda: `FACEPALM_LIBRARY_LAMBDA`.
2. Facepalm type per blunder: allowed loss when `loss > 0 and loss >= missed` (raw material inputs of the
   model), missed win otherwise. Returned by the library API next to the score.
3. Chip colour by type: `TAC_MISSED` (teal) for missed win, `TAC_ALLOWED` (crimson) for allowed loss.
4. Timeline: the facepalm share of the player's blunders over time, not split by type (owner, 2026-11-20;
   replaces the per-game line of decisions 1 and 2 below). It answers "how many of my blunders are facepalm
   blunders, and how does that change". Details:
   - The Flaws Timeline axis is flaws per 100 moves, so a share (percent) cannot be a line on it. It is its own
     small chart below the Flaws Timeline, with the same x-axis, rolling window and per-time-control series.
   - Share = facepalm blunders / scored blunders, pooled over the rolling window (not a mean of per-game
     shares: games without blunders have none). Unscored blunders are left out of both counts, so the Phase 252
     gap does not depress the share.
   - The share was chosen over a rolling mean of the score (owner, 2026-11-20): it reads as a count of the
     same blunders the rows and chips use, and the score is a ranking, not a probability. The mean is the
     fallback if the share is too jumpy on real accounts.
   - Source is `game_flaws` (the existing trend reads the games-table oracle columns). Needs a minimum number of
     scored blunders per point; pick the floor in discuss-phase.
5. You vs your opponents: facepalm blunders per game, paired per game. Total, and one row per type.
6. Versus-opponent bias (chance / threat blindness): see the design note (accepted by the owner, 2026-11-20).

**Design note: no type-share statistic (accepted 2026-11-20)**

The owner's concern: the model weights lost material about three times as much as a missed gain, so allowed
losses pass the 0.7 cut more easily. Any statistic that compares the two types with each other (the missed
share of facepalm blunders, or two type lines on one axis) mostly shows that weighting.

Decision: never compare the types with each other. Each type is compared only with the same type of the
opponents, where the weighting is identical on both sides and cancels:

- chance blindness = the player's missed-win facepalm rate minus the opponents', paired per game;
- threat blindness = the player's allowed-loss facepalm rate minus the opponents', paired per game.

They are two separate readings, not the ends of one axis (this replaces decision 4 of the 2026-11-15
extension); a player can show both or neither. The timeline shows the total facepalm share only, so no chart puts
the two type levels side by side. Copy states the comparison and does not diagnose.

**Out of scope** (deferred seed): benchmark zones, the within-player bias against a benchmark, the type-by-clock
matrix, the training weighting.

## Why This Matters

The facepalm score separates careless blunders from hard ones. A rate over time shows whether a player's
careless blunders are going up or down, and the comparison with opponents shows whether they facepalm more than
the players they face. The owner's hypothesis: a higher rate than your opponents may point to a lack of focus or
too many distractions.

## Decisions (owner, 2026-11-14)

1. **Metric: facepalm rate, not the average score.** Facepalms per game = blunders scoring above a cut (starting
   point: the drill's `FACEPALM_SCORE_MIN`, 0.7). The average score is taken over blunders only, so it measures
   how bad blunders are when they happen, not how often the player facepalms.
2. **Timeline:** the rate is in the same unit as the Flaws Timeline (per game), so it is one more line on the
   existing axis. No twin axis. A separate timeline is the fallback if the chart gets crowded.
3. **You vs opponents:** compared per game (paired), like the existing you-vs-opponent flaw deltas, not pooled.
4. **Name and icon:** "Facepalm" with the lucide `tree-palm` icon, as in SEED-261114-0ke.

## Prerequisite: score opponent blunders

Today only user-side blunders are scored (Phase 250 D-06: a scope decision, because the score was built for
drill selection and the drill only serves the user's own blunders; inherited from Phase 248). There is no
technical obstacle to scoring opponents:

- `maia_played_prob` is already stored for every flaw of both players (Phase 247).
- The line loss is a pure replay of the stored line (`game_positions.pv` at flaw ply + 1), no engine.
- `maia_reply_spread` is the missing input: one Maia inference per opponent blunder at the opponent's pinned
  Elo. That means a backfill about the size of Phase 250's (roughly 2.3M user blunders there) plus lifting the
  `_is_user_blunder` gate in the live scoring hook.

The model was fitted on the owner's labels for user blunders below 2000. It has no labels for opponent blunders.
For a like-for-like comparison with the same model on both sides this matters less, and opponents are rated
close to the user, but it is unvalidated.

The opponent scores must not leak into drill selection or into the library tag filters, which stay user-only
(`player_only_gate`).

## Cautions

- **Copy must not diagnose.** A higher facepalm rate than opponents may be distraction, but equally time
  trouble. State the comparison, do not explain it.
- **Not a probability** (250 D-01): the score is a ranking. A rate based on a cut is a count of blunders above
  that cut, and copy must not present it as a share of peers.
- **The cut moves with refits.** Rates shift when the model or the cut changes; they are recomputed for all
  history, so the timeline stays internally consistent.
- **Coverage:** blunders without a stored line have no score and count as non-facepalms. Check the NULL share
  after the Phase 252 repair before trusting the rate.

## When to Surface

**Trigger:** after Phases 252 and 254 have fully run in the benchmark DB and the per-type facepalm benchmarks
exist (see the frontmatter and the 2026-11-15 extension below).

## Scope Estimate

**Medium**, two parts:
- A: scoring extension for opponent blunders (scorer gate, backfill script modes, prod backfill run by the
  operator).
- B: stats (backend aggregation in the library stats service, a line in the Flaws Timeline, a you-vs-opponents
  row or tile).

Part B's timeline line for the user alone does not need Part A and could ship first.

## Breadcrumbs

- `.planning/seeds/closed/SEED-261114-0ke-facepalm-score-library-ui.md` (name, icon, filter, chip)
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` (D-01 score, D-06 scope, D-08 backfill)
- `app/services/maia_flaw_scoring.py` (`_is_user_blunder`, spread and line backfill modes)
- `scripts/backfill_maia_flaws.py`, `scripts/blunder_check/fit_facepalm.py`
- `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py` (`FACEPALM_SCORE_MIN`)
- `app/services/library_service.py`, `app/routers/library.py`, `app/schemas/library.py` (library stats)
- `frontend/src/components/library/FlawTrendChart.tsx`,
  `frontend/src/components/library/stats/LibraryStatsSections.tsx`

## Notes

Open details for discuss-phase: the cut for the rate (0.7 or a separate constant), whether a benchmark zone for
the you-vs-opponents delta is wanted (would need the benchmark DB scored too), where the comparison sits in the
stats table.

## Extension (owner, 2026-11-15, /gsd-explore): facepalm types, bias, clock matrix

Phase 254 adds missed gains to the score, so a facepalm blunder (score at or above the label cut, 70%) can be
typed, analogous to the missed / allowed tactic categories.

**Decisions**

1. **Type = dominant term.** Each facepalm blunder gets exactly one type: allowed loss when `loss` is the larger
   term, missed win when `lambda * missed` is larger (254 D-05 definitions). The two types partition the facepalm
   blunders, so their lines sum to the total. Open: the tie rule (suggestion: ties count as allowed loss, since
   that loss happened on the board).
2. **Wait for the benchmark DB.** Run Phases 252 and 254 fully in the benchmark DB first, then compute benchmarks
   for the two types per Elo bucket and time control. Question to answer there: are there systematic
   missed-vs-allowed biases, and how do they change with player level and time control?
3. **Bias statistic, in two steps.** First within-player: the missed share of the player's own facepalm
   blunders, read against the benchmark zone for their Elo and TC (needs no opponent scoring). Then versus
   opponents (needs Part A on prod and on the benchmark DB). Plot the player's and the opponents' bias on the
   same chart over time; the gap between the lines is the versus-opponent bias. Details to refine later.
4. **Bias names: chance blindness and threat blindness.** Chance blindness = the player misses easy wins more
   than they allow easy losses; threat blindness = the reverse. The two are the ends of one axis and name what
   was overlooked, not why (copy must not diagnose). They apply to the statistic only; a single blunder keeps the
   type names "missed win" and "allowed loss", matching the tactic categories.

**Ideas to build on this**

- Flaws Timeline: two more lines, missed-win and allowed-loss facepalm blunders per game.
- A "Facepalm blunders" stats section like "You vs. your opponent": overall, and split by type.
- A type-by-clock matrix like "Clock by game phase". Questions it should answer: under time pressure, do I allow
  more obvious material wins than my opponents do? Do I miss more easy wins than they do? When unrushed, do I
  miss more quick wins or allow more?
- Blunder-check training: serve more of the type the player is worse at spotting.

**Measurements (prod, 2026-11-15)**

- Maia `pre` pass: 1,203,184 of 2,170,692 user blunders (55%). `best_line_material`: 1,114 rows (454 games, 10
  users, apparently from the live scoring hook); the bulk line pass has not run.
- On those rows, all blunders, lambda 1: pure allowed 291 (26%), pure missed 263 (24%), mixed 127 (12%), neither
  419 (38%). Mixed: 31 loss-dominant, 57 missed-dominant, 39 ties (3.5% of blunders). Thin sample, indication only.
- Not countable yet at the facepalm level: the shipped model is pre-refit (`FACEPALM_MISSED_COEF = 0.0`).

**Cautions**

- Phase 254 does not score opponent blunders (254-CONTEXT, "Not in this phase"); Part A above is still the
  prerequisite for everything versus opponents.
- The type split depends on the refit: a small missed coefficient leaves the missed-win line nearly empty.
- Labels exist only below 2000; trends in the 2000 and 2400 buckets are extrapolated.
- This split is by material at depth 3, the tactic missed / allowed split is by motif. They overlap but will not
  agree row for row.
- Facepalm blunders are rare; type x clock x side cells get thin. Check counts before designing the matrix.

## Part A sequencing (owner, 2026-11-16): after Phase 256, before the prod feed

Decision: finish Phase 256 first, then start the Maia backfill for opponent blunders. It does not have to wait
for the end of the Phase 252 repair, but the order of the steps matters.

**Findings (prod, 2026-11-16)**

- Opponent blunders: 2,331,306 rows, `maia_played_prob` on 2,312,811, and 0 rows with `maia_reply_spread`,
  `maia_pre_spread`, `maia_best_prob` or line material. User blunders are fully covered.
- The Phase 252 `repair` step only rewrites `game_positions.pv`; it touches no Maia stamp or column. The best
  move is pinned (252 D-01), so all three Maia columns are independent of the repair.
- The `feed` step is the hazard: it hands games back to tier 4, and every tier-4 blob submit runs the Maia hook
  in full mode. `_flaw_row` writes NULL into the facepalm and pre keys of non-user blunders, so a backfill run
  before the hook change is wiped for every fed game.
- Lines vs games (0.5% sample, 5,380 games): 30% of allowed and 35% of missed blunder lines are short, but 91%
  of games have at least one short flaw line (upper bound of the fed set). The rescore is per game.
- The score stays NULL while `played_line_material` is NULL (`_loss_sql`). Two readers have no side gate and
  rely on that: the drill's unserved-blunder EXISTS (`blunder_check_repository.py`) and
  `fetch_page_facepalm_scores`. Gate them before opponent line facts are written.

**Order**

1. Full mode fills the three Maia columns for opponent blunders (line facts stay user-only for now). In full
   mode the two pre inputs are free (same policy as `maia_played_prob`); the reply spread is one inference.
2. Deploy step 1, before the prod feed starts.
3. New backfill mode for opponent blunders: both inferences in one pass, selected by row
   (`maia_reply_spread IS NULL AND maia_played_prob IS NOT NULL`), so no new stamp column. About 4.7M
   inferences; the Phase 250 spread pass (half that) took 5 to 6 hours locally.
4. Line facts for opponents and the reader gates come with the rest of Part A, after the repair.

The benchmark DB needs the same order; its feed pilot started on 2026-11-16.

## Refinement (owner, 2026-11-20): phase split, cut, type rule after the Phase 256 model

**State.** Part A is done on prod: opponent blunders carry the Maia columns (99.2%) and line facts (93.9%),
the same coverage as user blunders (99.9%, 93.8%). The benchmark DB was not checked. The "Decisions" cut
reference above is stale: `FACEPALM_SCORE_MIN` is now 0.5 (the drill's choice).

**Decisions**

1. **Stats cut: a separate constant at 0.7** (the label meaning), not `FACEPALM_SCORE_MIN`. Lambda is
   `FACEPALM_LIBRARY_LAMBDA`.
2. **Two phases.** Phase 1 is built now and holds everything that needs no benchmark. Phase 2 holds everything
   that reads a benchmark zone and waits for the Phase 252 repair and the benchmark DB scoring. The Phase 252
   gap (6% of blunders without line facts) is the same on both sides, so it does not skew the paired comparison.
3. **Phase 1 starts with the total rate:** a timeline line and a you-vs-opponents row. The clock matrix and
   the training weighting stay in this seed.

**Proposed, not yet confirmed by the owner**

- Type rule on the raw material inputs (the model's `loss` and `missed`, both in material units): allowed loss
  when `loss > 0 and loss >= missed`, missed win otherwise. Ties count as allowed loss; a row with no material
  in either line follows the model's pure-miss branch (`loss = 0`) and counts as missed win. The fitted
  coefficients (loss 1.16, missed 0.35) are not used for typing: they would move 85% of the rows to allowed loss.
- Per-type lines and the versus-opponent bias (chance / threat blindness) need no benchmark, so they can be in
  Phase 1. The within-player bias against a benchmark zone is Phase 2.

**Measurements (prod, 2026-11-20, 10% sample by `game_id % 10 = 0`, hand-written SQL twin of the score, not
verified row by row against `facepalm_expr`)**

| Side | Blunders | Scored | Score >= 0.5 | Score >= 0.7 | Games with a blunder of that side |
|---|---|---|---|---|---|
| User | 235,005 | 219,510 | 96,707 | 70,209 | 83,967 |
| Opponent | 235,350 | 218,686 | 95,023 | 68,474 | 85,913 |

Facepalm blunders at 0.7 are not rare: 32% of scored blunders, about 0.8 per game that has a blunder of that
side. This overrides the "facepalm blunders are rare" caution above.

Type split of the user's facepalm blunders at 0.7 (opponents within one point): allowed loss 74.0%, missed win
24.0%, tie 1.7%, neither 0.4%. By composition: both terms above 0 in 56%, loss only 33%, missed only 10%.

**Follow-up (owner, 2026-11-20)**

- The type rule above is accepted (raw inputs, ties to allowed loss, no-material rows to missed win).
- **Chip colour by type:** the facepalm score chip is tinted by type with the existing tactic colours
  (`TAC_MISSED` teal for missed win, `TAC_ALLOWED` crimson for allowed loss, `frontend/src/lib/theme.ts`).
  Needs the type in the library API next to the score.
- **Caution on the 74 / 24 split:** it is not a population finding about threat vs chance blindness. The model
  weights loss about three times as much as a missed gain (1.16 vs 0.35), so loss-heavy blunders pass the 0.7
  cut more easily. Among all blunders the two were about even on 2026-11-15 (pure allowed 26%, pure missed 24%,
  thin sample). The bias statistic must therefore be read against opponents or a benchmark, never against 50%.
