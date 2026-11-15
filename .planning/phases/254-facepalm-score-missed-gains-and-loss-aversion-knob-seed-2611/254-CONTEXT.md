# Phase 254: Facepalm Score Missed Gains and Loss-Aversion Knob (SEED-261114-mg7) - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

The facepalm score (Phase 250) only measures what the played move gives away, so an obvious missed win of material
scores near 0 (prod: 88% of allowed hanging pieces score >= 0.70 vs 21% of missed ones at the same material swing).
This phase makes the score see missed material gains, weighted by a lambda (the loss-aversion knob) that each
consumer sets. Deliverables:

1. Stored facts per user-side blunder on `game_flaws`: material along the played line and along the best line, a
   mate ply per side, and two pre-blunder Maia inputs.
2. The score computed at query time from those facts, with lambda as a parameter; the stored `facepalm_score`
   column is retired.
3. About 50 owner labels on misses, and one refit on Phase 252's repaired lines (absorbing plan 250-10).
4. Prod backfill: a Maia pass for the pre-blunder inputs and a line pass for the material facts.
5. A recheck of `FACEPALM_SCORE_MIN` and the drill pool size, decided by the owner.

Not in this phase: scoring opponent moves or mistakes, UI changes beyond what the changed score source forces,
rating-dependent line depth, the facepalm rate in stats (SEED-261114-iuv).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (not re-discussed)
- The knob is wanted regardless of how the loss-aversion question is answered (seed, owner 2026-11-14).
- Missed gains are valid drill items: the drill asks "Good move or blunder?" (seed).
- The score is a ranking, never presented as a probability or a share of peers (250 D-01, 253 D-03).
- False alarms are worse than misses; tune for the fair share among passers (250 D-03).
- Scope is user-side blunders only (250 D-06). No engine at scoring time (250 D-07).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; the fit lives in
  `scripts/blunder_check/` and `--check-constants` reproduces the constants from a committed features TSV (250 D-04).
- Long prod runs are started by the orchestrator, detached, never by an executor; operator connections stay under
  about 25 (prod `max_connections` 50).
- Library band cutoffs 30/70 are UI constants, independent of the drill cut (253 D-09).

### Where lambda lives
- **D-01: The score is computed at query time.** `game_flaws` stores only facts; every consumer calls the SQL score
  expression with its own lambda. A refit or a lambda change is a constants deploy with no UPDATE pass over prod.
  Consequence: plan 250-10's score recompute and its mixed-score window (T-250-38) no longer exist.
  - Measured on dev (user 28, 18.6k flaws, 4.6k scored): filter on the stored column 38 ms, on the full expression
    25 ms, same plan (`ix_game_flaws_user_severity`, then filter). No index on the score exists today. Dev only; not
    measured on prod or for the drill's foreign-pool queries, which probe flaws by game id.
  - The chip percent and the filter must come from the same SQL expression, so a score at a band edge cannot show in
    one band and filter into another (253 D-10, and the float note in `library_repository._facepalm_clause`).
  - The Python and SQL twins stay pinned together by `tests/services/test_facepalm_score.py`.
- **D-02: Drop the stored `facepalm_score` column in this phase,** as the last, human-gated plan (same shape as
  250-11): once every reader uses the expression and prod is checked, stop writing it in the hook and the backfill
  and drop it. — **Reversibility:** one-way — needs an Alembic migration; the values are re-derivable from the
  stored facts, but a rollback to the stored-column readers needs a column re-add and a prod pass.
- **D-03: Drill lambda = 1.0 (symmetric).** Blunder-check selection ships symmetric while GM Noel Studer's answer is
  pending. One named constant, lowered if he says the drill should be loss-averse. Expect a larger drill pool
  (no-refit estimate from the seed: 27% to 40% of blunders pass; direction only).
- **D-04: Library lambda = 1.0, as its own named constant.** Facepalm chip, Facepalm Score filter, analysis move
  list and eval chart tooltip use it. Separate from the drill constant so the two can diverge.

### Model form for misses
- **D-05: Material definitions** (depth `LINE_DEPTH` = 3, blunderer's side, baseline = position before the blunder):
  `loss = max(0, -played[3])`, `swing = best[3] - played[3]`, `missed = swing - loss`. Lambda multiplies the missed
  term: lambda = 0 reproduces a loss-only score, lambda = 1 is the model as fitted.

  | Case | played[3] | best[3] | loss | missed |
  |---|---|---|---|---|
  | Hangs a rook, nothing better was on | -5 | 0 | 5 | 0 |
  | Rxf5 (wins 5) instead of Qxh1 (wins 10) | +5 | +10 | 0 | 5 |
  | Hangs a rook and misses a free piece | -5 | +3 | 5 | 3 |

- **D-06: The fit script compares two forms** and picks by cross-validated AUC and the fair share at the cut (as
  250 did for the loss floor): (a) one material coefficient on `loss + missed`; (b) separate loss and missed
  coefficients. The fit report states the choice. Under (b), lambda = 1 means "as the owner labelled", not the
  symmetric swing.
- **D-07: Reply spread for pure misses is decided by the fit** among named forms: spread as today; spread applied
  only when `loss > 0`; spread replaced for misses by the best-move probability. Same selection criteria as D-06.
- **D-08: Store both pre-blunder Maia inputs; each must earn its coefficient.** Best-move probability (how findable
  the gain was; the `maia_best_prob` dropped in 250 D-11) and the pre-blunder policy spread (effective number of
  moves, the `maia_effective_moves` formula). Both come from the policy call at the flaw position that already
  yields `maia_played_prob`. An input enters the score only if it improves cross-validated AUC or the fair share at
  the cut; one that earns nothing stays stored for later refits.
- **D-09: Line facts as two symmetric arrays** (owner: symmetric for gains and losses, fewer columns):
  - `played_line_material SMALLINT[]`: the blunder move, then the opponent's stored best reply line (`pv` at flaw
    ply + 1). This is what `line_loss_1/3/5/7/9` hold today.
  - `best_line_material SMALLINT[]`: the best move from the pre-blunder position, then its stored line (`pv` at the
    flaw ply: first token is the move, the rest the line).
  - Slot N = net material at depth N, depths 1 to 9, signed, positive = blunderer up. This flips the sign of today's
    loss columns. A depth the line does not reach is NULL ("line too short to tell", as in 250 D-05).
  - One mate-ply column per side (today's `line_mate_ply` plus its best-line counterpart).
  - The five `line_loss_*` columns are replaced: existing values copy into the array with a plain UPDATE (sign
    flipped), no replay. Four columns in total instead of twelve.
  - Storage cost is an estimate, not measured: roughly 40 bytes more per scored blunder than split columns, about
    100 MB over prod's 2.3M user blunders. Unscored rows stay NULL.
  - 250 D-02's counting rules (captures only, recapture at depth + 1, desperado exclusion, static-exchange credit)
    apply to both lines.
  — **Reversibility:** costly — an Alembic migration plus changes to every reader of `line_loss_*` (hook, backfill,
  `scripts/blunder_check/`); the data itself is preserved.
- **D-10: No forcing flag.** Both stored lines are engine lines, so a depth-3 gain is against best defence whether
  or not the line is forcing. Obviousness is covered by reply spread (loss side) and best-move probability (gain
  side). Named fallback, not scope: if the fit shows quiet-move misses scoring too high, add a "best move is a
  capture or check" fact in the line pass.

### Refit sequencing
- **D-11: Plan 250-10 is folded into this phase.** One refit, on the repaired lines, with the new inputs and the
  miss labels. 250-10 is closed as superseded by Phase 254 and Phase 250 completes; record that in ROADMAP.md and
  the 250 phase docs.
- **D-12: Build everything now, behaviour unchanged until the refit.** Before Phase 252's prod repair finishes:
  columns and migration, hook, query-time expression, backfill tooling, the labelling, and the prod Maia pass (it
  does not read lines). Consumers switch to the expression with today's coefficients and a zero missed term, so
  scores stay as they are. After 252 (252-06 SUMMARY records EXIT_FULL=0 and `scripts/repair_short_lines.py status
  --db prod` shows nothing left): prod line pass, refit, new constants, then the D-02 column drop.
- **D-13: `FACEPALM_SCORE_MIN` is set by the owner at a blocking checkpoint,** keeping the 250 policy (somewhat
  below the precision-optimal cut, so drill answers cover both sides). The fit report must show fair / unfair among
  passers at several cuts, split by loss-type and miss-type, and the drill pool size per rating band, own and
  foreign.

- **D-21 (owner, 2026-11-15, during execution; amends D-11 and D-12): do not wait for Phase 252.** After the prod
  pre pass and the miss labels, plan 11 runs without the 252 precondition: the prod line pass, the refit and the
  `FACEPALM_SCORE_MIN` decision go ahead on the lines as they are. Where a Stockfish line is too short, the
  material gain / loss is skipped (NULL slot, D-18 behaviour), not guessed. Once 252's prod repair is done, one
  more line pass fills only the remaining gaps. Known cost, accepted by the owner: about a third of prod blunders
  have short lines today, so the refit sees a subset and the gap fill changes inputs under the fitted constants.

### Miss labels
- **D-14: About 50 new rows, mostly pure misses, stratified.** About 40 pure misses (loss 0) spread over missed size
  (1, 3, 5, 9+) and over best-move probability, so the fit sees easy and hard misses; about 10 mixed rows (loses and
  misses). Blind as in 250: score and inputs hidden while labelling; output a TSV like `leg2-labels-2026-11-11.tsv`.
- **D-15: Drawn from prod, all users, movers below 2000,** the population of the 180 existing labels, so the sets
  pool. Limited to rows whose stored lines are already repaired or were never short, so the features do not change
  after 252.
- **D-16: The 180 existing labels stay in the fit, on top of the 50** (about 230 labels). Their best lines are
  pulled from prod; the 17 no-loss rows labelled fair become miss-type evidence.

### Settled at plan time (owner, 2026-11-14, after research)
- **D-17: The line arrays have 9 slots indexed by depth** (`array[3]` = depth 3). Even slots are mid-exchange
  values, computed with the existing counting rule and documented as such; after the D-09 copy they stay NULL until
  the post-252 line pass fills them.
- **D-18: An unknown best line contributes `missed = 0`.** When the stored best line does not reach depth 3 and has
  no mate, the row keeps its loss-only score; it is not unscored. The fit report counts label rows with a NULL best
  line.
- **D-19: The final gated drop (D-02) also drops `line_loss_1/3/5/7/9`,** in the same one-way migration as
  `facepalm_score`.
- **D-20: The prod Maia `pre` pass runs from this machine with 8 workers (shards), alongside Phase 252.** The 252
  repair runs on a different machine and is not paused. The orchestrator records prod's connection count before
  starting; 252 stops itself if prod connections rise more than 10 above its own baseline (`MAX_CONNECTION_RISE`),
  so the pass must keep its total connection footprint below that.

### Claude's Discretion
- Column names, the array bounds check, and whether the best-line mate ply feeds a `MATE_LOSS`-style missed value
  (propose in the fit; a missed mate within `LINE_DEPTH` should not score as "nothing missed").
- Whether the missed term gets its own cap or shares `LOSS_CAP`; decided by the fit script.
- Minimum missed gain that defines a "miss" for the D-14 sample.
- Backfill shard count and pacing; whether the Maia pass and the line pass share the Phase 250 script.
- API shape: the score still travels as today (`facepalm_score` on the library schemas); lambda is not an API
  parameter.
- Whether the calibration and spot-check reports (`scripts/blunder_check/`) are re-run in full or only the supply
  table D-13 needs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed and evidence
- `.planning/seeds/SEED-261114-mg7-facepalm-missed-gain-loss-aversion-knob.md` — evidence table, owner decisions,
  proposed shape, open questions.
- `reports/blunder-check/leg2-labels-2026-11-11.tsv` — the 180 owner labels.
- `reports/blunder-check/facepalm-fit-2026-11-13.md`, `reports/blunder-check/facepalm-features-2026-11-13.tsv` — the
  current fit and its features.
- `reports/blunder-check/blunder-check-calibration-2026-11-14.md`, `reports/blunder-check/spot-check-2026-11-14.md`
  — current selection supply and spot check.

### Prior phase decisions
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 (score), D-02 (material count), D-05
  (storage), D-08 and D-18 (two-pass backfill), D-11 (dropped Maia columns this phase partly re-adds).
- `.planning/phases/250-facepalm-blunder-selection/250-10-PLAN.md` — the refit and line-pass run book folded in by
  D-11; reuse its preconditions and dispatch rules.
- `.planning/phases/253-facepalm-score-library-ui/253-CONTEXT.md` — library surfaces that read the score (D-04,
  D-09, D-10, D-20 to D-23).
- `.planning/phases/252-short-engine-line-repair-backfill-seed-261112-s4v/252-CONTEXT.md` — the line repair this
  phase waits for.

### Project rules
- `CLAUDE.md` — database design rules, `Literal` types, nesting depth gate, Sentry rules.
- `docs/production-runbook.md` — prod commands and limits for the backfill passes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/facepalm_score.py`: `FacepalmModel`, `facepalm_score` and `facepalm_score_sql` (twins),
  `loss_feature`. Extend with the missed term, lambda and the new Maia inputs.
- `app/services/line_material.py`: `line_facts(pre_board, played_uci, pv)` returns the per-depth losses and mate
  ply for the played line. The seed computed the gain by running it on the stored best line.
- `app/services/maia_flaw_scoring.py`: `_derive_flaw_values` already makes one `full_policy` call at the flaw
  position (source of `maia_played_prob`), so the pre-blunder inputs need no extra inference going forward;
  `_derive_reply_spread` is the effective-moves code to reuse.
- `scripts/backfill_maia_flaws.py`: hash-residue shards, stamp-as-checkpoint, `--mode line --cutoff`.
- `scripts/blunder_check/`: `facepalm_features.py`, `fit_facepalm.py` (`--check-constants`), `sample.py`,
  `render.py`, `spot_check.py`.

### Established Patterns
- Constants block in `app/services/blunder_check_rules.py` (`FACEPALM_*`, `LINE_DEPTH`, `LOSS_CAP`, `MATE_LOSS`).
- Fit choices (floor, form) are made by the fit script on cross-validated AUC and fair share, then confirmed by the
  owner; never hand-tuned.
- Column drops are the last, separately gated plan of a phase.

### Integration Points
- Readers of the stored `facepalm_score` to move onto the expression: `app/repositories/library_repository.py`
  (`_facepalm_clause`, flaw list item), `app/services/library_service.py` (flaw markers),
  `app/repositories/blunder_check_repository.py` (two selection predicates),
  `app/services/blunder_check_candidates.py`, `scripts/backfill_maia_flaws.py` (coverage counts),
  `scripts/blunder_check/sample.py`, `render.py`, `spot_check.py`.
- Writers: `app/services/maia_flaw_scoring.py` (`_spread_row`, `_line_row`, `_score_rows`).
- `app/models/game_flaw.py`: `line_loss_1/3/5/7/9`, `line_mate_ply`, `maia_reply_spread`, `facepalm_score`.

</code_context>

<specifics>
## Specific Ideas

- Fixtures (unblind, not part of the blind sample): game 817357 ply 24 (Ba3 instead of Qxg7, which wins the h8
  rook) and game 820181 ply 65 (Rxf5 wins 5 instead of Qxh1 wins 10); dev DB, user 28, both score 2% today and must
  score high after the refit.
- Window 14 (game 2099808, flaw ply 23) must still fall below `FACEPALM_SCORE_MIN` (250 specifics).
- The 250 material-count fixtures (#153, #156, #165, #170, #176, #177, #13, #35, #154, #184) keep passing after the
  sign flip.

</specifics>

<deferred>
## Deferred Ideas

- **Loss-aversion weight for the drill** below 1.0: waits for GM Noel Studer's answer; a constant change, no phase.
- **Forcing flag** ("best move is a capture or check"): only if the fit shows quiet-move misses scoring too high
  (D-10).
- **Rating-dependent line depth** and labels above 2000 (250 deferred): the arrays hold depths 1 to 9, so a later
  refit needs no prod pass.
- **Refit from drill answers** (250 deferred): unchanged.
- **Facepalm rate in stats:** SEED-261114-iuv.

</deferred>

---

*Phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-261114-mg7*
*Context gathered: 2026-11-14*
