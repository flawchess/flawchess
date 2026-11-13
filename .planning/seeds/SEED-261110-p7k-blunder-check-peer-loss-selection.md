---
id: SEED-261110-p7k
status: active
planted: 2026-11-10
planted_during: Phase 249 planning (owner spot-check of the Phase 248 sample)
trigger_when: Phase 250 planning, after the Phase 252 line repair has run on prod
scope: medium (two stored facts + one derived score on game_flaws, server-side Maia, backfill, selection swap; no Stockfish, no worker lane)
---

# SEED-261110-p7k: Facepalm score for blunder-check selection (replaces findability D-06)

## Current direction (owner, 2026-11-13)

Read this section first. Everything below it is the history that led here; where they disagree, this section wins.

### Facepalm score

One number per blunder in [0, 1], at the mover's level: 0 = basically no chance the player could have seen it,
1 = a very careless blunder the player should absolutely have seen and avoided. Name: "facepalm score" (owner
agreed; "stupidity" would insult the user in a filter).

- **It replaces the hard three-condition rule** in the drill. Selection keeps blunders with score >=
  `FACEPALM_SCORE_MIN` (a lower bound; one named constant instead of three thresholds).
- **The threshold sits a little below the precision-optimal cut on purpose** (owner, 2026-11-13): blunders believed
  a bit too hard are served too, so drill answers cover both sides of the eventual cut. Starting value 0.7.
- **Form:** a logistic regression on the owner labels over the stored facts: played probability (log), reply
  spread, and material lost along the stored line (capped, mate counted as a large loss). Engine drop and Elo
  added nothing.
- **Measured 2026-11-13** on the 163 decided labels with a stored line, 10-fold cross-validated, old line-3 count,
  lines as stored before the Phase 252 repair. Counts are fair / unfair among passers:

  | Selection | Passers | Share fair |
  |---|---|---|
  | Hard rule | 66 / 6 | 92% |
  | Score >= 0.8 | 59 / 5 | 92% |
  | Score >= 0.7 | 67 / 8 | 89% |
  | Score >= 0.5 | 81 / 20 | 80% |

  AUC 0.85 cross-validated; 0.79 trained on sets 1-5 and tested on set 6. The score matches the hard rule's
  precision, it does not beat it. What it buys is one knob and a range filter.
- **It is a ranking, not a probability.** Sets 5 and 6 are mostly rule passers, so the fitted values are not
  calibrated to all blunders. Do not present 0.8 as "80% of peers see this".
- **Storage:** the raw facts (250-CONTEXT D-05) plus one derived REAL column for SQL filtering. A refit is a plain
  UPDATE from the stored facts, no engine work. Facts: `maia_played_prob` (exists), `maia_reply_spread`, the
  line loss at depths 1, 3, 5, 7, 9 and the mate ply. The score reads depth 3; 7 and 9 are stored for later
  refits at higher ratings (no labels there yet).
- **Reply spread uses the full Maia policy** (owner, 2026-11-13), not the top moves up to 90% mass / max 8 that
  the label study below used. Recomputed on all 180 labels: correlation 0.98, AUC 0.717 full vs 0.712 truncated,
  score model 0.836 both. Same formula as `maia_effective_moves`, at ply+1. Values run higher (median 3.0 vs
  2.1), so the "<= 3.0" cut in the history below is on the truncated scale.
- **Refit on repaired lines** before the threshold is locked: the material feature reads the stored lines that
  Phase 252 is repairing.
- **Label file:** `reports/blunder-check/leg2-labels-2026-11-11.tsv` holds 180 rows (105 fair, 68 unfair, 7
  undecided). Planning docs said 190; the file is the source.

### Window mix (owner with GM Noel Studer, 2026-11-13)

- Each window is drawn independently, one third each: a red herring, a blunder from the user's own games, a
  blunder from another user's game. Not a fixed 1-1-1 per three windows, which would make the third one guessable.
- **Foreign blunders are strength-matched:** the mover's rating at game time is within +-150 of the drilling
  user's level. Rating only, no time-control match. The score was computed at the mover's rating, so it stays valid.
- **The user's level:** lichess-blitz-normalised pinned Elo of their most-played time control (reuse the existing
  Elo source in `app/repositories/blunder_check_repository.py`).
- **No imported or analysed games:** all blunders come from strength-matched users. Same code path.
- **Herrings follow the same own / foreign ratio as blunders.** Otherwise recognising one's own game gives the
  answer away (herrings are about 91% foreign today).
- Replaces 249 D-09 (own first, foreign as fallback) and D-11 (composition from the hazard model alone).

### Deferred

- **Library side-panel range filter** on the facepalm score (owner, 2026-11-13: deferred). Needs a decision on
  scoring opponent blunders and mistakes; the labels cover user blunders below 2000 only.
- **Refit from drill answers** (owner, 2026-11-13): once blunder check ships, users' answers act as labels (did a
  player at that level spot the blunder) and the curve is refitted on them. The lowered threshold above is what
  gives the refit data on blunders believed slightly too hard; below it there is still none.
- **No spaced repetition for blunder check** (owner, 2026-11-13): a sequence is shown to a user once. Phase 251
  drops its review item.

## Why This Matters

The current selection rule (249-CONTEXT D-06) judges whether a blunder is a face-palm from the Maia probability of
**one move** (the engine's best reply, or the best move for missed punishments) at one Elo. In the owner's spot-check
this let through a window that is not a face-palm, and every single-move repair broke on the next example. Whether a
blunder is easy to see depends on the whole spread of likely moves, which we do not store.

Triggering example: spot-check `<800` Window 14, https://flawchess.com/analysis?game_id=2099808&ply=23, 12... Qxf6
at Elo 712. Only Nxf6 is Good (Maia 33%); the natural gxf6 (50%) is also inaccurate; after Qxf6 the engine's best
reply is the quiet Nf3 (13%) and the user is still better (ES 0.73 → 0.54). It passed D-06 as a pure miss
(`maia_best_prob` 0.33 ≥ 0.2).

## Rules tried and why each failed (2026-11-10 session)

| Rule | Why it fails |
|---|---|
| Best move at least as likely as the played blunder | Window 14's blunder has only 9.5% (rank 3); the natural wrong move is a third move |
| Best move is Maia's top choice (`maia_best_rank = 1`) | Flips with rating: Window 14 would pass at 1000 but not at 700 or 1600; Maia curves are not monotone |
| Maia refutation test + "one clear punishing reply" (best reply beats second by ≥ 0.15 ES) | Excludes a hung piece that can be taken two ways, or a check followed by the capture |
| Maia refutation test alone, for all blunders | Scores only the engine's best reply; fails when a different reply also punishes |
| Stored-data bound `p·d1 + (1−p)·d2 ≥ 0.15` (p = refutation prob, d1/d2 = drop vs best/second reply) | Passes 71%, including 8% with p < 0.1; only two replies are stored, so it cannot be made tight |

Owner constraints from the session: one rule for every blunder (no allowed / miss split); Maia probabilities are
not always plausible, so do not hang the rule on one move's probability or rank; the punishment need not be a
single move; blunders only (engine drop ≥ `BLUNDER_DROP`), mistakes never.

## The idea: two expected-loss legs from the full move spread

Both legs are the same calculation on two positions (owner's definition, 2026-11-11): the **expected loss of the
side to move**, i.e. `Σ maia_prob(move) × ES loss(move)` over the moves a peer would play, with the ES loss taken
against that side's best move. Maia at the user's pinned Elo (`pinned_elo_for_mover`) as weights, Stockfish as evals.

- **Expected loss (leg 1, `maia_expected_loss`):** at the blunder ply, user to move. How much a peer loses in
  this position on average. Low = peers handle the position.
- **Reply loss (leg 2, `maia_reply_loss`):** at ply + 1, opponent to move (Maia still at the user's
  Elo, as in Phase 248). How much of the blunder a peer opponent gives back on average. Low = peers punish it.
- **Practical loss** (derived, not stored): engine drop − reply loss = what the blunder costs against a
  peer's replies. A rule on reply loss alone ignores how big the blunder is (0.15 blunder with refutation
  loss 0.05 costs 0.10; 0.50 blunder with reply loss 0.20 still costs 0.30), so leg 2 thresholds the
  practical loss.

**Not decided:**

- **Whether leg 1 is needed at all** (owner unsure, 2026-11-11). Argument for it: leg 2 alone passes blunders whose
  loss does not depend on the reply (the chance is simply gone), where only leg 1 tests whether the better move was
  findable. In the sample leg 1 removes about half of what leg 2 passes; whether that half is unfair windows or
  fair ones needs owner labels. Both blobs are stored either way, so dropping leg 1 later costs nothing.
- **Leg 1's form:** plain expected loss vs good-move share (Maia mass on moves losing < `INACCURACY_DROP`) vs a
  capped loss. A plain average cannot tell "half of peers lose 0.30" from "all peers lose 0.15".
- **Thresholds**, and whether to fold both into one number (practical loss − expected loss).
- **Product tension:** a strict leg 1 excludes the typical blunders of a level (moves most peers also play), which
  SEED-261108-dk0 says should be trained. How strict leg 1 is, is the owner's call.

## Measurement (2026-11-10, exploratory)

`temp/blunder-check/peer_legs.py` (gitignored), read-only on prod, local Maia + Stockfish, 1M nodes per multi-line
search. Report: `reports/blunder-check/peer-legs-2026-11-10.md`; each blunder window in
`reports/blunder-check/spot-check-2026-11-10.md` carries a "Peer legs" line. Tested rule: expected loss ≤ 0.10 and
practical loss ≥ 0.15.

- 569 random user blunders (up to 100 per Elo bucket): the current D-06 passes about 74%, leg 1 52%, leg 2 55%,
  both 26% (per bucket about ±10 points). Leg 2 alone at practical loss ≥ 0.10 / 0.15 / 0.20: 73% / 55% / 39%.
- Medians: engine drop 0.24, expected loss 0.10, reply loss 0.07, practical loss 0.16.
- Almost a pure tightening of D-06: 2% pass the tested rule but fail D-06; 49% pass D-06 but fail the tested rule.
- Missed punishments are 34% of the passing blunders, with no special case.
- Window 14: engine drop 0.20, expected loss 0.09, reply loss 0.10, practical loss 0.10. It passes leg 1 at
  0.10 and fails only on practical loss (the earlier good-move-share form of leg 1, 0.33 < 0.5, rejected it too).
- 31 of 600 sampled blunders lose less than 0.10 at this budget (multi-line search is shallower per move than the
  pipeline's evals; values also move slightly between runs).
- The numbers say how many pass, not whether the right ones pass. No labelled ground truth exists yet.

## Label study (2026-11-11): a Maia-only rule may be enough

The owner labelled 90 blunders fair / unfair / undecided in four sets (one labeller, treated as one opinion; all
below 2000 Elo). Data: `reports/blunder-check/leg2-labels-2026-11-11.tsv` (set 5, #91-120, a
blind random sample, is still unlabelled). Sets 2-4 were labelled with the values hidden.

Findings, on 74 decided labels (40 fair, 34 unfair):

- **A higher engine-drop threshold does not replace leg 2.** Among large-drop, low-practical-loss blunders the
  owner called 7 of 10 unfair (set 3).
- **Reply spread is the best leg 2.** Reply spread = effective number of opponent replies at ply+1,
  `exp(entropy)` of the Maia distribution at the pinned Elo (computed here from the cached top moves: 90% mass,
  max 8). Cut fixed at <= 3.0 before set 3 and confirmed on it blind (11 of 12 fair kept, 1 of 8 unfair kept).
  It separates as well as practical loss (rank correlation with it -0.72), keeps more fair positions at the same
  share fair, and needs no Stockfish. Adding practical loss on top gains little.
- **Known failure mode of reply spread:** one obvious reply that does not punish (#53: spread 1.3, reply loss
  0.25, labelled unfair). Only reply loss catches it; rare in the labels so far.
- **Reply spread alone is not enough** (set 4, all spread <= 3.0: 9 fair, 7 unfair). A leg 1 is needed.
- **Expected loss is the wrong leg 1.** It scales with blunder size, so a huge blunder that 20% of peers play
  fails it (#72: drop 0.91, expected loss 0.21, labelled fair). It removed 6 of 9 fair positions in set 4.
- **Candidate leg 1 without Stockfish: the stored `maia_played_prob` <= 0.3** (peers rarely play the blunder).
  With reply spread <= 3.0 it keeps 35 of 40 fair and 8 of 34 unfair, and passes about 49% of user blunders
  (expected loss <= 0.10 with reply spread: 30 / 8, 33%). The good-move share >= 0.3 does about the same (32 / 9)
  but needs the Stockfish search.
- Window 14 fails this rule on reply spread (4.4), though it passes played probability (0.09).

Caveats: the 0.3 cut was chosen on set 4's 16 decided labels (in-sample); sets 1-3 only contained positions
passing expected loss; played probability is a single move's Maia probability, which the owner flagged as
unreliable and possibly non-monotonic across Elo (not yet checked for this rule). Set 5 is the unbiased test.

### Set 5 (2026-11-12, blind validation): Maia-only falls short, "hangs material" closes the gap

Set 5 = 40 random passers of the Maia-only rule (played probability <= 0.3, reply spread <= 3.0) plus 10
non-passers, below 2000 Elo, labelled blind. Counts are fair / unfair.

- **The Maia-only rule does not hold at 81%.** Out of sample 26 / 13 of its passers are fair (67%). It is a good
  exclusion filter (non-passers: 1 / 9) but lets through one false alarm in three. Tighter Maia cuts do not help
  (67-69% at any played-probability or spread cut tried).
- **Unfair passers are mostly quiet positional blunders** with no winning capture for the opponent.
- **A mechanical "hangs material" test fixes most of it without Stockfish.** `hang >= 2` = after the blunder the
  opponent has a capture that wins at least 2 points by static exchange (board only, exploratory
  implementation in `temp/blunder-check/mech.py`). Maia rule plus `hang >= 2`: 14 / 1 on set 5, 13 / 1 on sets
  1-4 (93% both), passing about 19% of user blunders below 2000. `hang >= 2` alone: 14 / 1 and 14 / 3, about 27%.
- **Expected loss is the Stockfish alternative.** Maia rule plus expected loss <= 0.10: 22 / 3 on set 5 (88%),
  30 / 7 on sets 1-4 (81%), about 29% of blunders. It keeps positional blunders the material test drops, at the
  cost of one Stockfish search per blunder.
- Totals: 130 labels, one labeller. Thresholds for the material test were not tuned on set 5 (2 points was the
  first value tried on sets 1-4), but the test itself was chosen after seeing those sets.

### Material along the stored engine line (2026-11-12): best rule so far, no new searches

Owner points: the material condition alone may be enough; mate must count; above 2000 a fork that cashes in a
move or two later should still be caught. Tested with the refutation line already stored per flaw
(`game_positions.pv` at ply+1, about 12 plies; 560 of 600 sampled blunders have one). Exploratory code:
`temp/blunder-check/pvmat.py`.

`line N` = playing the stored line for N plies (plus the blunderer's next move, so a recapture counts), the
blunderer is down >= 2 points of material relative to the position before the blunder, or is mated. Counts are
fair / unfair over all decided labels with a stored line.

| Rule | Set 5 | Sets 1-4 | All | Pass rate below 2000 | 2000-2399 | 2400+ |
|---|---|---|---|---|---|---|
| Board test alone (capture wins >= 2, or mate in 1) | 14 / 1 | 14 / 2 | 28 / 3 (90%) | 25-38% | 17% | 8% |
| line 3 alone | 14 / 3 | 21 / 4 | 35 / 7 (83%) | 21-39% | 25% | 14% |
| Board test and Maia rule | 13 / 1 | 12 / 1 | 25 / 2 (93%) | 16-22% | 14% | 6% |
| line 1 and Maia rule | 11 / 0 | 12 / 0 | 23 / 0 | 13-17% | 8% | 7% |
| **line 3 and Maia rule** | 14 / 0 | 18 / 0 | **32 / 0** | 16-25% | 17% | 7% |
| line 5 and Maia rule | 14 / 0 | 18 / 1 | 32 / 1 | 16-23% | 21% | 12% |
| line 7 and Maia rule | 15 / 0 | 18 / 1 | 33 / 1 | 16-27% | 21% | 12% |

Maia rule = played probability <= 0.3 and reply spread <= 3.0.

- The engine line alone is worse than the board test: it finds material wins that peers do not see. Maia is what
  removes those, so the material condition alone is not enough and Maia does earn its place here.
- line 3 with the Maia rule let through none of the 53 unfair labels and kept 32 of 60 fair ones. With zero
  false alarms in 32 passers the true false-alarm rate could still be up to about 9%; about 20 rules were tried
  on these labels, so this needs a fresh blind check.
- Depth 5-7 raises the pool above 2000 (2000-2399: 17% to 21%; 2400+: 7% to 12%) at one extra unfair label in
  33. A rating-dependent depth (3 below 2000, 5-7 above) fits the owner's point about forks; there are no labels
  above 2000 to confirm it.
- Everything needed is stored or cheap: `maia_played_prob` (stored), the refutation line (stored), reply spread
  (one server-side Maia inference at ply+1). No Stockfish searches, no JSONB columns, no worker lane.
- Gaps: 7% of sampled blunders have no stored line; promotions are counted by material only.

### Set 6 (2026-11-12): fresh blind check of the line-3 rule, 85% fair

Set 6 = a new prod draw (not the 600 used before), scored without Stockfish: 40 passers of the exact rule
(played probability <= 0.3, reply spread <= 3.0, down >= 2 points or mated within 3 plies of the stored line),
10 per rating band below 2000, plus 10 non-passers, labelled blind. Script: `temp/blunder-check/set6.py`.

- **Passers: 34 fair, 6 unfair (85%; with 40 labels the plausible range is roughly 70-94%).** The 32 / 0 on the
  earlier labels was optimistic, as expected after trying about 20 rules on them.
- By band: below 800 8 / 2, 800-1199 7 / 3, 1200-1599 9 / 1, 1600-1999 10 / 0.
- Non-passers: 4 fair, 6 unfair, so the rule still drops a fair share of fair blunders.
- Pass rate in the fresh sample of 600: 21% overall (16-30% per band).
- The six unfair passers:
  - #176: computation artifact. The stored line is one move long (a rook trade into a lost pawn ending), so the
    recapture was never counted. Needs a rule for lines shorter than depth + 1.
  - #170, #156: the material is given up by the blunderer's own move in the engine line (desperado or spite
    check in a lost position), not won by an opponent capture.
  - #177: the "material" is an opponent promotion in an endgame race.
  - #153: the piece was already hanging before the blunder.
  - #165: a real two-move tactic (pin wins the knight) that the owner judged too hard at 777.
- Tighter Maia cuts do not clearly help on this set (played probability <= 0.1: 26 / 3).
- Not done on purpose: tuning the line computation on these six, which would spend the blind set. The first
  three bullets are candidate refinements to test on new labels.

### Refined material count (2026-11-12, owner: 85% acceptable, apply the quick wins)

Three refinements to the line-3 material count (`capture_loss` in `temp/blunder-check/refine.py`):
only captures count, so promotions are not material; an opponent capture of a piece the blunderer's previous
line move placed there without capturing is ignored (engine desperado or spite check); a line that ends on an
opponent capture before depth + 1 gets a static-exchange recapture credit. Counts are fair / unfair among
passers, with the Maia conditions.

| Material count | Sets 1-5 | Set 6 | All |
|---|---|---|---|
| Old line 3 | 32 / 0 | 34 / 6 | 66 / 6 (92%) |
| Refined line 1 | 23 / 0 | 24 / 0 | 47 / 0 |
| Refined line 3 | 30 / 0 | 32 / 2 | 62 / 2 (97%) |
| Refined line 5 | 29 / 1 | 30 / 2 | 59 / 3 (95%) |

The refinements remove four of the six unfair set-6 passers (#156, #170, #176, #177) and cost four fair ones
(#13, #35, #154, #184). They were designed on set 6, so its 94% is in-sample; sets 1-5 are the cleaner check and
barely move. Remaining unfair passers: #153 (piece already hanging) and #165 (two-move pin at 777).

### Tuning knobs: how facepalmy a blunder must be

All are constants applied to stored values, so changing them needs no recomputation.

| Knob | Now | Stricter | Effect seen in the labels |
|---|---|---|---|
| Line depth | 3 plies | 1 ply | Strongest knob. At 1 ply only immediate losses count: 47 fair, 0 unfair, about a quarter fewer positions. At 5 plies it loosens: slightly more positions, one more unfair. |
| Material lost | >= 2 points | >= 3 (a full piece) | Removes exchange-for-minor and two-pawn cases. On set 6 with the old count: 28 / 4, little gain. |
| Played probability | <= 0.3 | <= 0.1 | "Almost no peer plays this." Small gain on set 6 (26 / 3 against 34 / 6) for a quarter fewer positions. |
| Reply spread | <= 3.0 | <= 2.0 | "Only one sensible reply." No measurable gain on sets 5 and 6. |
| Engine drop | >= 0.15 | >= 0.25 | Bigger blunders only. Did not separate fair from unfair in the labels. |
| Mate | counts | n/a | On or off; all labelled mate cases were fair. |

Depth and material can be set per rating band, for example 1 ply below 1200 (set 6's weakest band: 15 fair,
5 unfair with the old count) and 3 or more above. Deeper lines above 2000 are untested (no labels there).

Short stored lines (1-2 plies with no obvious reason, as in #176) are a known oddity on the analysis board and
puzzle solutions too; a separate investigation of how many stored lines are affected was started 2026-11-12.

Superseded by the table above: given the owner direction (false alarms worse than misses, Maia-only preferred), the leading candidate is:
played probability <= 0.3, reply spread <= 3.0, and the opponent wins >= 2 points of material. No Stockfish, no
JSONB columns, no worker lane; new stored values are the reply spread and the material test result.

Owner direction (2026-11-11): a Maia-only rule (no Stockfish) would be preferred. Missing some facepalm blunders
is acceptable; false alarms (unfair blunders in the drill) are the worse error, so tune thresholds for the share
fair among passers, not for coverage.

If the Maia-only rule holds, the consequences are: no Stockfish searches, no JSONB columns, no worker lane; one
new stored value (reply spread at ply+1, server-side Maia); `maia_played_prob` is kept, not retired. The storage,
cost and worker-lane sections below then become the fallback design.

## Proposed storage (owner direction, 2026-11-10 / 11)

Store the raw inputs once so any metric can be recomputed without an engine, plus the two derived metrics for
SQL selection. Four nullable columns on `game_flaws`, user-side blunders only (`severity = 2`, ply parity =
`user_color`, about 2.3M on prod), named after the existing `maia_played_prob` / `maia_refutation_prob`:

| Column | Type | Content |
|---|---|---|
| `maia_move_evals` | JSONB, deferred | Peer's likely moves at the blunder ply: move, Maia probability, raw Stockfish eval (cp / mate, never a pre-converted ES) |
| `maia_reply_evals` | JSONB, deferred | Opponent's likely replies at ply + 1, same shape |
| `maia_expected_loss` | REAL | Leg 1, derived from `maia_move_evals` |
| `maia_reply_loss` | REAL | Leg 2, derived from `maia_reply_evals` |

- Move lists: Maia's top moves up to about 95% of the probability (cap near 10); before the blunder add the played
  move and the stored best move, after it add the stored refutation.
- Maia at the pinned Elo only (owner: no ±200 grid). Evals do not depend on rating, so Maia can be re-run on the
  stored moves later if rating flips matter.
- **Two multi-line Stockfish searches per blunder**, restricted to those move lists (owner). Where no best move is
  stored, the baseline is the best evaluated move; no third search.
- If the formula changes, the derived columns are recomputed from the blobs (no engine).

## Existing Maia columns (owner intent 2026-11-11: retire them)

The owner expects the ten existing columns (Phase 247: `maia_played_prob/rank`, `maia_best_prob/rank`,
`maia_second_prob/rank`, `maia_top_prob`, `maia_effective_moves`; Phase 248: `maia_refutation_prob/rank`) to become
redundant, and Phase 249's selection code will be rewritten onto the new derived metrics. Checked 2026-11-11:

- **Consumers today:** only blunder-check selection (`maia_best_prob/rank`, `maia_refutation_prob/rank`) and the
  calibration scripts (`maia_played_prob/rank` for arrow oddness). Nothing in the frontend, stories or any other
  service reads them. `maia_effective_moves` has no reader at all. The Flaws-tab face-palm filter and the data
  story from SEED-261108-zkp were never built.
- **Derivable from the blobs:** played, best, top and refutation probabilities (those moves are always in the
  lists) and their ranks when inside Maia's top moves. Not derivable as stored: the second-best move's pair unless
  that move is added to the list, exact ranks outside the list, and `maia_effective_moves` (needs the full
  policy; it could be written into the blob as one number at scoring time, or re-run later with Maia alone).
- **Coverage gap:** the Phase 247 columns cover every stored flaw (mistakes and blunders, both players' moves in
  the user's games, about 7.6M rows). The blobs as scoped cover user-side blunders only (about 2.3M). Opponents
  are mostly not FlawChess users, so their moves are scored only as rows of the user's game. Full redundancy
  would need the blob scoring extended to mistakes and opponent moves, about 3x the Stockfish cost.
- **Proposed:** new code reads only the blobs and the two derived metrics; drop the ten columns in this phase's
  cleanup once selection no longer reads them and no prefilter needs `maia_refutation_prob`. Maia-only values
  can be recomputed in about half a day (Phase 247 backfill tooling) if a later feature wants them.

## Cost and cheaper alternatives (the open risk)

Full backfill: about 4.6M multi-line searches for 2.3M blunders. At the 1M-node budget used in the measurement
that is on the order of tens of CPU-days, plus an estimated 1-2 GB of JSONB on prod. Neither figure is measured.
The owner expects this may be too costly. Options, roughly cheapest first:

1. **Score lazily, only what gets served.** A per-user pool (precedent: `herring_pool`) filled by a background
   job: take candidates that pass the cheap SQL filters, score them, keep the passers. A user needs a few hundred
   windows, not their whole history; the MVP beta needs a handful of users.
2. **Prefilter with stored data before any engine work:** D-06 (loses about 1% of eventual passers, cuts a
   quarter), the eval band, window fit (enough Good user moves before the blunder), and the stored-data bound
   `p·d1 + (1−p)·d2` as a necessary condition for leg 2 (about 29% fail it).
3. **Lower search budget.** Selection needs a rough practical loss, not pipeline-grade evals. Measure how leg
   values and pass/fail change at 100k-250k nodes or a fixed shallow depth before choosing.
4. **Stage the passes.** Run the cheaper leg first and the second search only for blunders that survive it.
5. **Fewer moves per search:** 90% mass or a cap of 6 instead of 95% / 10; the tail contributes little.
6. **Stay with stored columns** and accept an imperfect rule, tightened by thresholds (e.g. a higher engine drop).
   Known failure modes are listed in the table above.

### Where the work runs (owner constraints, 2026-11-11)

The owner does not want the Stockfish searches on the prod server (bottleneck) and does not want Maia on the
remote workers. Both hold if the job is split by engine:

- **Maia stays on the server.** It already runs there per game after eval apply (`score_game_flaws_after_apply`).
  That step would write the move lists with probabilities into the two JSONB columns, evals still empty. Maia is
  the small part of the cost (one policy inference per position, against two multi-line searches).
- **Stockfish goes to the workers** through a new isolated lease/submit pair (precedent: `/bestmove-lease` and
  `/bestmove-submit`). The lease hands out position + move list; the worker returns raw evals; the server fills
  the blobs and computes the two derived columns on submit. Workers need no Maia and no new dependency.
- **Backlog:** a dev-box script writes the Maia move lists (same shape as the Phase 247 backfill); the worker
  fleet then drains the Stockfish side through the same lane as new games.

Not decided: whether to build any of this before the owner's spot checks settle that the two values work and
whether both legs are needed (one leg halves the Stockfish cost).

## Before building

1. Owner labels the 86 spot-check blunder windows fair / unfair (thin, but enough to rule out clearly wrong
   formulas). Score every leg-1 / single-number variant against the labels; the script already keeps per-move data.
2. Measure runtime and blob size on a sample at two or three search budgets; pick the budget and the lazy vs
   backfill route from that.
3. Phase 249 ships on D-06. Keep selection behind one findability predicate so this can replace it.

## Breadcrumbs

- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md` (feature design, face-palm test v1 / v2 history)
- `.planning/phases/249-blunder-check-playable-mvp/249-CONTEXT.md` D-06, D-07, D-08
- `reports/blunder-check/blunder-check-calibration-2026-11-10.md`, `spot-check-2026-11-10.md`,
  `peer-legs-2026-11-10.md`
- `scripts/blunder_check/metrics.py` `findable`, `app/services/maia_flaw_scoring.py` (Phase 247 / 248 scorer and
  backfill tooling), `app/services/maia_engine.py` `full_policy`, `app/models/game_flaw.py` (PV blob precedent)
- Analysis-board Maia card: computes the same move-quality spread in the browser
- Related: FlawChess Engine practical-play expectimax (Maia as static weights, SEED-082 prior art)
