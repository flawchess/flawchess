# Phase 250: Facepalm-Blunder Selection (SEED-261110-p7k) - Context

**Gathered:** 2026-11-12, revised 2026-11-13 (facepalm score replaces the hard rule; own / foreign / herring window
mix). Distilled from SEED-261110-p7k, the label study in
`reports/blunder-check/leg2-labels-2026-11-11.tsv` and owner answers in session; not a discuss-phase run)
**Status:** Un-parked (owner, 2026-11-13): plan and build now, including the prod backfill. Nothing in this phase
waits for the short-stored-line repair (Phase 252). Instead the line-dependent values are recomputed once that repair
has finished on prod (D-18): the line losses, the mate ply and `facepalm_score`. Until then they are computed from
the lines as stored, and the score coefficients are the fit on those lines.

<domain>
## Phase Boundary

Phase 249 selects blunder-check windows with a findability rule (249 D-06) built on single-move Maia probabilities.
Owner spot checks showed it lets through blunders that are too hard to see (Window 14). A label study (180 owner
labels in the TSV, six sets, the last five blind) produced a replacement that needs no new Stockfish work. On
2026-11-13 the owner turned its three hard conditions into one facepalm score and changed where windows come from.
This phase stores what the score needs, backfills it, swaps the selection predicate, changes the window mix, and
retires the Maia columns the old rule used. Deliverables:

1. Stored per user-side blunder on `game_flaws`: the reply spread, the line material result, and the derived
   facepalm score.
2. A scorer used by both the go-forward hook (new games) and a prod backfill script.
3. The blunder-check candidate predicate rewritten onto the score, with one named threshold.
4. The window mix: herring / own blunder / strength-matched foreign blunder at one third each.
5. A re-run of the calibration and spot-check reports against the new selection.
6. Removal of the nine Maia columns nothing reads any more.

</domain>

<decisions>
## Implementation Decisions

### The facepalm score (owner, 2026-11-13; replaces the hard rule of 2026-11-12)
- **D-01: One score for every user blunder.** `facepalm_score` in [0, 1] at the mover's level: 0 = basically no
  chance the player could have seen it, 1 = a very careless blunder the player should absolutely have avoided. A
  user-side blunder (engine drop >= `BLUNDER_DROP`, unchanged) qualifies for the drill when its score is >=
  `FACEPALM_SCORE_MIN`. No special cases for missed punishments. This replaces 249 D-06 and overturns 249 D-08
  ("no capture/check/mate rule").
  - **Form:** a logistic regression fitted on the owner labels. Coefficients are named constants in app code; the
    fit itself lives in a script under `scripts/blunder_check/` so it can be re-run.
  - **Inputs** (all stored, no engine at scoring time):
    1. **Peers rarely play it:** `maia_played_prob`, log-transformed. Already stored (Phase 247).
    2. **The punishment is obvious:** reply spread = effective number of opponent replies at ply+1: `exp(entropy)`
       of the full Maia policy (all legal moves) at the user's pinned Elo (`pinned_elo_for_mover`). This is the
       `maia_effective_moves` formula (Phase 247) applied one ply later; reuse that code. No truncation (owner,
       2026-11-13): the label study used the top moves up to 90% mass, max 8, only because that was what the
       exploratory cache held. Recomputed on all 180 labels the two correlate at 0.98 and separate equally well
       (AUC 0.717 full, 0.712 truncated; score model 0.836 both). Full-policy values run higher (median 3.0 vs
       2.1), so the retired hard rule's "<= 3.0" cut does not carry over.
    3. **It loses material fast:** net material the blunderer is down after following the stored refutation line
       (`game_positions.pv` at flaw ply + 1) for `LINE_DEPTH` (3) plies, capped; mate within the depth counts as a
       large loss. The cap (5) and the mate value (+5) are provisional picks from the 2026-11-13 quick fit.
  - **Provisional coefficients** (2026-11-13, old line-3 count, truncated spread): ln(played_prob + 0.01) -0.71,
    reply spread -0.69, loss +0.32. They are placeholders: the phase must refit on the D-02 refined count, the
    full-policy spread and (for the final lock) the repaired lines, and compare this form against raw played
    probability with a binary "loses >= 2 or mate" input, which did about as well.
  - Engine drop and Elo were tried as extra inputs and added nothing.
  - **Measured 2026-11-13** (163 decided labels with a stored line, 10-fold cross-validated, old line-3 count,
    unrepaired lines), fair / unfair among passers: score >= 0.8: 59 / 5 (92%); >= 0.7: 67 / 8 (89%); >= 0.5:
    81 / 20 (80%); the hard rule: 66 / 6 (92%). AUC 0.85.
  - **Threshold deliberately below the precision-optimal cut** (owner, 2026-11-13): also serve blunders believed
    a bit too hard, so drill answers cover both sides of the eventual cut and the later refit can move it either
    way. Starting value 0.7 (0.8 matched the hard rule's precision); set the final value at planning after the
    refit on repaired lines. This knowingly trades some of D-03's precision for data.
  - **A ranking, not a probability.** The label sets are mostly rule passers, so the values are not calibrated to
    all blunders. No copy may present the score as a share of peers.
- **D-02: Material count along the line** (reference implementation: `capture_loss` in
  `temp/blunder-check/refine.py`, exploratory, to be rewritten as app code with tests):
  - piece values 1 / 3 / 3 / 5 / 9; only captures count, promotions are not material;
  - the blunder move's own capture counts in the blunderer's favour (baseline is the position before the blunder);
  - the blunderer's recapture at depth + 1 is included when the line has it;
  - an opponent capture of a piece that the blunderer's previous line move placed there without capturing is
    ignored (engine desperado or spite check in a lost position);
  - a line that ends on an opponent capture before depth + 1 gets a static-exchange recapture credit;
  - a blunder with no stored line gets no score (NULL) and does not qualify (about 7% of sampled user blunders
    before the Phase 252 repair).
- **D-03: False alarms are worse than misses** (owner). Tune for the share of fair positions among passers, not for
  coverage. 85% fair was accepted as good enough for the beta; the refined count measured 62 fair / 2 unfair on the
  labels under the hard rule (in-sample for set 6). Expect the selection to drop roughly half of what the owner
  would call a facepalm blunder.
- **D-04: Named constants** next to the existing blunder-check selection constants: `FACEPALM_SCORE_MIN`, the
  score coefficients, `LINE_DEPTH`, the material cap and the mate value. One depth for all ratings in this phase.

### Window mix (owner with GM Noel Studer, 2026-11-13)
- **D-12: Three sources at one third each,** drawn independently per window: a red herring, a blunder from the
  user's own games, a blunder from another user's game. Not a fixed 1-1-1 per three windows (the third would be
  guessable). Probabilities are named constants. Replaces 249 D-09 (own first, foreign as fallback) and D-11.
  How this composes with the 249 hazard model (which draws herrings at about 30%) is for the planner.
- **D-13: Foreign blunders are strength-matched.** The mover's rating at game time is within
  `FOREIGN_RATING_BAND` (150) of the drilling user's level. Rating only, no time-control match. The score was
  computed at the mover's rating, so it applies unchanged.
- **D-14: The user's level** is the lichess-blitz-normalised pinned Elo of their most-played time control. Reuse
  the existing Elo source (`EloSourceRow` in `app/repositories/blunder_check_repository.py`); planner to confirm it
  fits.
- **D-15: No own supply.** A user with no imported or analysed games, or whose own unserved supply is used up,
  gets foreign blunders in place of own ones. Same code path.
- **D-16: Herrings follow the same own / foreign ratio as blunders,** so recognising one's own game does not give
  the answer away (herrings are about 91% foreign today). Falls back to foreign when the user has no own supply.
- Own vs foreign stays recorded per window; copy never says "your move" on a foreign game (249 D-09, unchanged).

### Storage (Claude's recommendation, owner to confirm at planning)
- **D-05: Store the raw facts and the derived score,** so a refit is a plain UPDATE with no engine work. On `game_flaws`,
  nullable, NULL = not scored:
  - `maia_reply_spread` REAL;
  - the net line loss at depths 1, 3, 5, 7 and 9 (five SMALLINT) and the ply of mate within the line (SMALLINT,
    NULL = no mate). Depths 1, 3, 5 were measured in the study. Depths 7 and 9 (owner, 2026-11-13) are stored for
    later refits at higher ratings, where a tactic cashes in a few moves later; the score does not read them in
    this phase and there are no labels above 2000 to back them. A depth the stored line does not reach is NULL
    ("line too short to tell"), not 0, unless D-02's mate or recapture-credit rule settles it earlier. Kept as
    stored columns on purpose (owner, 2026-11-13): about 12 bytes per row, against a multi-hour PGN and line
    replay over the tunnel to recompute them for a refit;
  - `facepalm_score` REAL, derived from the facts above and `maia_played_prob`.
  The planner may propose a tighter shape, but the predicate must stay a plain SQL filter on `game_flaws`.
- **D-06: Scope = user-side blunders only** (severity blunder, mover is the game's user), as in Phase 248's
  refutation stats. Not mistakes, not the opponent's moves.

### Computation
- **D-07: No Stockfish, no worker lane.** Reply spread is one Maia inference at ply+1 on the server, added to the
  existing post-apply Maia hook (`score_game_flaws_after_apply`; Phase 248's refutation scoring already runs Maia at
  ply+1 there). The line loss is a pure replay of the stored line.
- **D-08: Backfill script** for the roughly 2.3M existing user blunders, same pattern as
  `scripts/backfill_maia_flaws.py` (hash-residue shards, stamp-as-checkpoint, resumable). Same scorer as the hook.
- **D-09: Selection swap.** `app/services/blunder_check_candidates.py` and
  `app/repositories/blunder_check_repository.py` filter on `facepalm_score` in place of the best / refutation
  pairs. Other Phase 249 selection decisions stand (Good bar, eval band, no repeats), except supply order and
  composition, which D-12 to D-16 replace.
- **D-10: Calibration re-run.** Re-run the Phase 248 calibration and spot-check scripts on prod with the new
  predicate (`scripts/blunder_check/`), and report supply per rating band, own and foreign (foreign supply within
  +-150 matters most at the rating extremes): the hard rule passed about 16-30% of user
  blunders below 2000, 17% at 2000-2399 and 7% at 2400+ in the samples, so pool size at low game counts and at
  high ratings must be checked.

### Serving
- **D-17: A sequence is shown to a user once** (owner, 2026-11-13). No spaced repetition for blunder check, so
  Phase 251 has no reviews of missed-blunder windows. 249 D-10's no-repeat rule becomes permanent, not MVP-only.
  Its exception is removed: a blunder window that ended on a false alarm before the blunder was reached no longer
  returns to the pool. This phase removes that code path.

### Recompute after the Phase 252 line repair (owner, 2026-11-13)
- **D-18: A line-only recompute pass, run once Phase 252's prod pv repair is complete.** It recomputes the line
  losses (all depths), the mate ply and `facepalm_score` for every scored user blunder, and scores blunders that had
  no stored line before the repair. `maia_played_prob` and `maia_reply_spread` do not depend on the stored line and
  are not recomputed. Consequences for the plan:
  - the backfill is built as two separable passes: a Maia pass (reply spread) and a line pass (line losses, mate
    ply, score). The line pass needs no Maia and no engine, must be re-runnable over rows that already hold values
    (not only NULL rows), and is the tool for D-18;
  - the score refit is part of D-18: refit on the labels with the repaired lines, update the coefficient constants
    and `FACEPALM_SCORE_MIN`, then run the line pass so the stored scores match;
  - the first prod backfill may run while the Phase 252 repair is still writing `game_positions.pv`. Keep operator
    connections within the prod limit (max_connections 50, both runs together under about 25) and expect rows whose
    line changes mid-run; D-18 is what makes that harmless;
  - D-18 and the column drop (D-11) are the last, separately runnable, human-gated steps of the phase. Long prod
    runs are run by the orchestrator, not a backgrounded executor.

### Column cleanup (owner intent 2026-11-11, confirmed direction 2026-11-12)
- **D-11: Keep `maia_played_prob`. Drop the other nine** once the new selection is live and checked on prod:
  `maia_played_rank`, `maia_best_prob`, `maia_best_rank`, `maia_second_prob`, `maia_second_rank`, `maia_top_prob`,
  `maia_effective_moves`, `maia_refutation_prob`, `maia_refutation_rank`. Readers today are the Maia scoring and
  backfill code, the D-06 selection, and the calibration scripts; no frontend or API reader. The drop is the last
  plan of the phase so a rollback to D-06 stays possible until then. Stop computing them in the hook at the same
  time. Check SEED-261110-cqk (chess.com-style miss classification) for a claim on `maia_best_*` before dropping.

### Claude's Discretion
- Column names for the line-loss values and where the scorer module lives.
- Whether the line loss is computed in the same hook as reply spread or at flaw-classification time.
- Backfill shard count and pacing (prod RAM and DB are the binding constraints, not CPU).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/seeds/SEED-261110-p7k-blunder-check-peer-loss-selection.md` — full history: rules tried, the label
  study, set 5 and 6 results, refinements, the knob table, cautions.
- `reports/blunder-check/leg2-labels-2026-11-11.tsv` — 180 owner labels (105 fair, 68 unfair, 7 undecided) with per-row values.
- `.planning/phases/249-blunder-check-playable-mvp/249-CONTEXT.md` — D-03..D-11 selection decisions that stand,
  D-06 and D-08 that this phase replaces.
- `temp/blunder-check/refine.py`, `pvmat.py`, `mech.py`, `set6.py` — exploratory reference code (gitignored, on the
  dev box only): `capture_loss`, reply spread via `peer_legs.top_moves` + `mech.eff`.
- `app/services/maia_flaw_scoring.py`, `app/repositories/game_flaws_repository.py`, `scripts/backfill_maia_flaws.py`
  — Phase 247/248 scoring and backfill pattern to extend.

</canonical_refs>

<specifics>
## Specific Ideas

- Fixtures for the material count should include the six unfair set-6 passers (#153, #156, #165, #170, #176, #177)
  and the four fair positions the refinements dropped (#13, #35, #154, #184); the seed lists what each one shows.
- Window 14 (game 2099808, flaw ply 23) must fall below the score threshold (reply spread 4.4, no material loss).

</specifics>

<deferred>
## Deferred Ideas

- **Library side-panel range filter on the facepalm score** (owner, 2026-11-13: deferred): needs the score for
  whatever the filter covers and a decision on opponent blunders and mistakes; labels cover user blunders below
  2000 only.
- **Refit from drill answers** (owner, 2026-11-13): after launch, users' answers act as labels and the curve is
  refitted on them. D-01's lowered threshold is what gives the refit data on blunders believed slightly too hard; below that
  threshold there is still no data. Phase 250 only has to make sure the served
  flaw is identifiable per drill item, which Phase 249 persistence already does.
- **Rating-dependent line depth** (5 to 7 plies above 2000, to catch forks that cash in later): enlarges the pool
  there but has no labels to back it.
- **Short stored engine lines** (1-2 plies with no obvious reason): separate investigation started 2026-11-12; this
  phase only handles them with the D-02 recapture credit.
- **Stockfish-based legs** (expected loss, reply loss, practical loss, worker lane): the fallback design in the
  seed, not needed by the score.
- **A fresh blind label set** for the refined count, and labels above 2000 from a stronger player.

</deferred>

---

*Phase: 250-facepalm-blunder-selection*
*Context gathered: 2026-11-12*
