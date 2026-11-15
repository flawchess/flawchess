---
id: SEED-261114-iuv
status: dormant
planted: 2026-11-14
planted_during: Phase 250 executing (facepalm-blunder selection); /gsd-explore session with the owner
trigger_when: after Phases 252 and 254 have fully run in the benchmark DB and the facepalm benchmarks by type (missed win, allowed loss) per Elo x TC exist (owner, 2026-11-15; replaces the earlier trigger). SEED-261114-0ke (facepalm filter and chip) should have shipped
scope: medium. Part A (operator-run): extend facepalm scoring to opponent blunders, including a Maia backfill about the size of Phase 250's. Part B: facepalm rate in the library stats (timeline line, you vs opponents)
---

# SEED-261114-iuv: Facepalm rate in the library stats (timeline and you vs opponents)

Add facepalm statistics to the library stats: a facepalm-rate line in the Flaws Timeline and a "you vs your
opponents" facepalm-rate comparison. Follow-up to SEED-261114-0ke (filter and card chip).

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

- `.planning/seeds/SEED-261114-0ke-facepalm-score-library-ui.md` (name, icon, filter, chip)
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
