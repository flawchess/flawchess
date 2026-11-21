# Phase 259: Facepalm Score Refit on First Principles (SEED-261121-tau) - Context

**Gathered:** 2026-11-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The facepalm score misreads material in two ways and lacks one input. Found on prod game 2883555 ply 47
(24...Kd7, score 0.918): the best line Bxf4 Qxf4 Qxf4 Rxf4 is an even trade but was stored as
`best_line_material = [9, 9, 0, ...]` and scored as a missed gain of 2.58; and the model has no input for how
findable the punishing move Nxe6 is (Maia 21%), only the reply spread.

This phase delivers:

1. A material rule that reads every depth at a quiet point, so an equal exchange of any length is neutral.
2. Two stored numbers per blunder, the material `loss` and the `missed` gain, computed in Python. The 9-slot
   material arrays are dropped.
3. A stored Maia probability of the engine's best reply to the blunder, which replaces the reply spread in the
   model.
4. A refit on the owner's labels, new `FACEPALM_*` constants, and the owner's checkpoint.
5. The backfill of the new columns on prod.

Not in this phase: a fit on user blunder-check answers; serving blunder-check sequences with any facepalm score;
the `detect_sacrifice` gap for an offered sacrifice the engine declines; the benchmark DB backfill and the
facepalm benchmark zones (SEED-261120-bzq); UI changes beyond what the new score values cause.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (not re-discussed)
- The score is a ranking, never presented as a probability or a share of peers (250 D-01). False alarms are worse
  than misses (250 D-03). No engine at scoring time (250 D-06, D-07).
- The score is a SQL expression evaluated at query time, with a Python twin; a coefficient refit or a lambda change
  is a constants deploy with no UPDATE pass over prod (254 D-01). The chip percent and the filter come from the
  same expression (253 D-10). This phase keeps that; only the inputs of the expression change (D-05).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; `--check-constants` reproduces them
  from a committed features TSV (250 D-04). Fit choices are confirmed by the owner, never hand-tuned.
- Label 1 means "the facepalm score should be above 70%" (254 D-23). One label file,
  `reports/blunder-check/facepalm-labels.tsv`.
- `FACEPALM_SCORE_MIN` (drill, 0.50 today) and `FACEPALM_STATS_MIN` (library stats, 0.70) are set by the owner at
  a blocking checkpoint (254 D-13, 257 D-01).
- Drill and library lambda stay 1.0 (254 D-03, D-04). An unknown best line contributes `missed = 0` (254 D-18).
- Facepalm type (allowed loss / missed win) is decided on the same `loss` and `missed` inputs the score reads
  (257 D-02).

### Owner principle for this phase
- **D-01: First principles decide, the AUC is only a range check.** The owner (2026-11-21) prefers the model shape
  that makes the most sense over a small AUC gain: the labels are few (268 usable rows) and "very subjective".
  A candidate is acceptable when its cross-validated AUC is within about 0.02 of the shipped rule on today's
  lines (0.897 in the spike, D-12). No choice between shapes by AUC differences inside that range.

### Material rule
- **D-02: Every depth is read at a quiet point.** The balance at depth N is taken after walking the line N plies
  and then on while the next line move is a capture, on any square. A line that stops inside an exchange is
  settled by a static exchange on that square (the opponent's recapture counts against the blunderer, the
  blunderer's for them). This generalises today's "one blunderer recapture at depth + 1". Same-square-only
  extension is ruled out (spike CV AUC 0.883). The other 250 D-02 counting rules stay (captures only, piece values
  1 / 3 / 3 / 5 / 9, the first move's own capture counts for the blunderer, the desperado exclusion, mate rules).
- **D-03: The aggregate stays the decaying mean** over the odd depths 1, 3, 5, 7, 9, for both the loss and the
  missed gain. Reading: the material a player sees when their look-ahead depth varies, shallow looks being
  likelier. It keeps the early-swing signal of rows like `-3, -3, 0`, which the owner labelled fair in Phase 256.
  The "first stable value" is not a candidate, and the input is not chosen by the fit.
- **D-04: The decay ratio stays 1/2, fixed, not fitted** (`MATERIAL_DECAY_RATIO`).

### Storage
- **D-05: Store `loss` and `missed` as two scalar columns on `game_flaws`, drop the material arrays.** The quiet
  walk and the decaying mean run in Python when the row is written (go-forward hook and backfill). The SQL score
  expression reads the two numbers; it no longer aggregates arrays, so the SQL twins of the aggregation
  (`facepalm_material` SQL builders) go away. Coefficient refits and lambda changes stay constants deploys. A
  change to the material rule itself (the quiet rule, the decay ratio, the caps and floors, the mate values) needs
  a recompute pass that replays the games and stored lines (no engine, no Maia). The owner chose this over
  (a) rule-applied 9-slot arrays, (b) raw per-ply arrays with the rule in SQL, (c) raw plus rule-applied arrays,
  and (d) a stored final score.
  — **Reversibility:** one-way — dropping `played_line_material` and `best_line_material` needs an Alembic
  migration, and the arrays can only be rebuilt by a prod pass over about 4.4M rows.
- **D-06: The drop is the last, human-gated step,** as 254 D-02 was: once no reader of the arrays is left in app,
  scripts or tests and prod is checked.
  — **Reversibility:** one-way — same migration as D-05.
- The mate ply columns (`line_mate_ply`, `best_line_mate_ply`) and the Maia columns (`maia_played_prob`,
  `maia_best_prob`, `maia_reply_spread`, `maia_pre_spread`) stay stored. Whether the mate plies are still needed
  once mates are folded into `loss` and `missed` is for the planner (Claude's Discretion).

### Best-reply probability
- **D-07: A new stored column** (working name `maia_best_reply_prob`): Maia's probability of the engine's best
  reply to the blunder, at the **blunderer's** pinned Elo. Reading: "would a player of your level see this
  punishment". It comes from the same full-policy call that yields `maia_reply_spread`, so it is free going
  forward; existing rows need a re-inference backfill.
- **D-08: It replaces the reply spread in the model** on blunders that lose material. Both types then read only
  the probability of the key move: `maia_best_prob` for a missed win, the best-reply probability for an allowed
  loss (the pre-blunder spread already fitted to 0). The `maia_reply_spread` column stays stored and is no longer
  read by the score.

### Rule review before the build
- **D-09: The plan starts with a review report the owner confirms.** In the spike the quiet rule changed at least
  one odd-depth value on 113 played lines and 139 best lines of 290, more than the exchange artifact alone
  explains. The report groups the changes by cause (longer exchange settled, a later capture pulled one step
  earlier, line ended inside an exchange) and shows about 10 before / after positions with analysis links. The
  recompute is built only after the owner confirms the rule.

### Scope of the recompute and rollout
- **D-10: Both sides' blunders, on prod only.** The score is one expression used for the player's and the
  opponents' blunders (Phase 257 comparison), so both get the new columns. Prod size 2026-11-21: 4,687,707
  `game_flaws` rows carry a reply spread, 4,417,251 a played-line array, 4,415,594 a best-line array (4,707,735
  blunders of 7,813,403 flaws). The benchmark DB backfill is **not** in this phase (owner, 2026-11-21, reversing
  an earlier answer in the same session); it belongs to the benchmark zones work (SEED-261120-bzq). The code
  must still run there: the migration applies to the benchmark DB and its rows stay unscored until that backfill.
- **D-11: New columns, one switch.** The new columns are filled while the app keeps scoring from the old arrays;
  one release switches the expression and the constants together; a later migration drops the arrays (D-06).
  Users never see half-converted scores. Prod operator runs go one at a time (prod `max_connections` is 50, the
  app pool takes up to 20).
- **D-17: The covering index follows the inputs.** `ix_game_flaws_blunder_facts` includes both material arrays
  today. A covering partial index with the new scalar inputs (`loss`, `missed`, the best-reply probability, and
  the other columns `_game_flaw_columns` reads) must exist on prod before the switch release (built
  `CONCURRENTLY`), otherwise the score queries fall back to heap fetches. The old index is dropped before or with
  the array drop (D-06), since it depends on the array columns.
- **D-18: JIT is re-measured, not assumed.** The score and type expressions are 14.2 KB (98 CASE) and 17.7 KB
  (124 CASE) today, nearly all of it the per-slot array aggregation; that is why 257 D-21 runs the facepalm
  statements with `SET LOCAL jit = off`. With scalar inputs the expressions shrink to a short logistic. After the
  switch, the plan runs EXPLAIN ANALYZE on the largest prod account with JIT on and off, and removes
  `disable_jit_for_transaction` only if the numbers support it. A stored final score stays ruled out (254 D-01,
  D-05 option d): every coefficient refit would be a prod UPDATE pass over about 4.7M rows.
- **The preliminary facepalm bands are held.** The `quick/facepalm-prelim-bands` worktree derives bands from the
  current score; they are not merged before this refit ships and are re-derived from the new score.

### Acceptance (defaults accepted by the owner, not discussed in depth)
- **D-12: AUC range check:** cross-validated AUC of the final model within about 0.02 of 0.897 (the shipped rule
  on today's lines, spike baseline). The plan re-measures the baseline, since lines keep changing.
- **D-13: Fixture:** prod game 2883555 ply 47 must have a missed gain of 0 under the new rule (best line
  Bxf4 Qxf4 Qxf4 Rxf4). Its new score is reported at the checkpoint, not gated.
- **D-14: No new label set.** The refit uses label sets 1 to 8 as they are.
- **D-15: One blocking owner checkpoint** after the fit report: the owner confirms the model and sets
  `FACEPALM_SCORE_MIN` and `FACEPALM_STATS_MIN`, with the fair / unfair table at cuts from about 50% to 70% and
  the drill pool size, as in Phase 256 D-13.
- **D-16: Release** as a normal release with a changelog bullet: scores change for every user (library chip,
  Facepalm filter, Facepalm rate in the stats, drill pool).

### Claude's Discretion
- Names and types of the new columns, and how NULL is encoded ("line too short to tell" must still leave the row
  unscored, 256 D-03; an unknown best line still gives `missed = 0`).
- How mates enter the stored `loss` and `missed` (a mate within depth 3 must keep scoring as today's `MATE_LOSS` /
  `FACEPALM_MISSED_MATE` case) and whether the mate ply columns can then be dropped too.
- Which move is "the best reply": the first token of the stored refutation line (`game_positions.pv` at flaw
  ply + 1), consistent with the line the material is counted on.
- How the reply probability is gated for pure misses (the spike used it only on rows that lose material and 0
  elsewhere, mirroring `best_prob_for_misses`), and how a NULL reply probability unscores a row (mirror 256 D-04).
- Whether the staged form selection of `fit_facepalm.py` is re-run or the shape is fixed by D-03 and D-08 with
  the alternatives listed as information only (D-01 says the fit does not choose).
- Backfill mechanics: sharding, order of the Maia re-inference and the material pass, resumability, the readiness
  gate before the switch release.
- Whether the spike scripts move into `scripts/blunder_check/` or are rewritten.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed and evidence
- `.planning/seeds/SEED-261121-tau-facepalm-first-principles-refit.md` — the motivating case with its term
  breakdown, the two parts, the owner decision. Its Part 2 proposal ("settled value plus onset discount") is
  superseded by D-03, and "recompute the stored line material" by D-05.
- `.planning/phases/259-facepalm-first-principles-refit/spike/quiet_spike.py` — the quiet walk used for the
  numbers below (`quiet_loss`, `quiet_array`) and the reply-probability pull. Throwaway quality; a reference for
  the rule, not production code.
- `.planning/phases/259-facepalm-first-principles-refit/spike/reply_prob_check.py` — the add-one-column check of
  the reply probability.
- `reports/blunder-check/facepalm-fit-2026-11-16.md`, `reports/blunder-check/facepalm-features-2026-11-16.tsv` —
  the shipped fit and its features.
- `reports/blunder-check/facepalm-labels.tsv` — label sets 1 to 8.

### Prior phase decisions
- `.planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-CONTEXT.md` — D-03 (depth 3 coverage),
  D-04 (NULL best prob), D-06 to D-13 (the selection rule this phase does not repeat), the note on `-3, -3, 0`
  rows.
- `.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-CONTEXT.md` — D-01
  (query-time score), D-02 and D-19 (the gated column drop, the pattern for D-06), D-05 (material definitions),
  D-17, D-18.
- `.planning/phases/257-facepalm-rate-library-stats/257-CONTEXT.md` — D-01 (stats cut), D-02 (facepalm type on the
  material inputs), the opponents' scoring.
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 to D-07 (score meaning, counting rules).

### Dependent work
- `.planning/seeds/SEED-261120-bzq-facepalm-benchmark-zones-and-clock-matrix.md` — needs the new columns filled
  in the benchmark DB, which this phase leaves to it.

### Project rules
- `CLAUDE.md` — `Literal` types, nesting depth gate, pre-merge gate, changelog rule, database design rules.
- `docs/production-runbook.md` — prod commands and limits for the operator runs.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/line_material.py`: `_replay_line`, `_victim_value`, `_best_recapture`, `_exchange_value`, the
  `_Step` record and the desperado rule in `_net_loss`. The quiet walk extends `_net_loss`'s loop past the depth.
- `app/services/facepalm_material.py`: `decaying_mean`, `loss_by_depth`, `gain_by_depth` (Python side stays; the
  `*_sql` builders become unused under D-05).
- `app/services/facepalm_score.py`: `FacepalmModel`, `FacepalmFacts`, `FacepalmColumns`, the score and type twins.
  The SQL twin shrinks to scalar columns.
- `app/services/maia_flaw_scoring.py`: `_derive_reply_spread` (the post-blunder full-policy call the reply
  probability reads), `replay_flaw_boards`, `OPPONENT_ROW_COLUMNS`, `LINE_ROW_COLUMNS`, the existing backfill
  passes.
- `scripts/blunder_check/facepalm_features.py` (features TSV from prod) and `fit_facepalm.py` (staged fit,
  `--check-constants`).

### Established Patterns
- Constants block in `app/services/blunder_check_rules.py`.
- An optional term with a zero coefficient is omitted at build time in both twins, so an unused NULL input never
  unscores a row.
- Phase 254's release sequence: readers moved to the new source first, a human-gated one-way drop last.

### Integration Points
- Readers of the score and type expressions: `app/repositories/library_repository.py`,
  `app/services/library_service.py`, `app/repositories/blunder_check_repository.py`,
  `app/services/blunder_check_selection.py`, and the scripts under `scripts/blunder_check/`.
- Readers of the arrays: `app/models/game_flaw.py`, `app/repositories/game_flaws_repository.py`,
  `app/services/maia_flaw_stats.py`, `app/services/maia_flaw_scoring.py`, `app/services/facepalm_score.py`.
  Nothing in the frontend reads them.
- A fresh worktree has no local database config: the spike ran with the working directory set to the main
  checkout so the prod tunnel credentials resolved.

</code_context>

<specifics>
## Specific Ideas

### Spike numbers (2026-11-21, 290 of 291 rows, one game gone from prod; 268 usable in the fit)

| Material rule | Aggregate | CV AUC | Set-8 AUC |
|---|---|---|---|
| Shipped rule, today's lines | decaying mean | 0.897 | 0.815 |
| Quiet, any capture | decaying mean | 0.903 | 0.851 |
| Quiet, any capture | first stable | 0.886 | 0.904 |
| Quiet, same-square recaptures only | decaying mean | 0.883 | 0.813 |

| Variant (quiet rule, decaying mean) | CV AUC | Reply-prob coefficient |
|---|---|---|
| Shape as shipped | 0.903 | |
| Plus reply probability | 0.910 | +0.670 (spread shrinks from -0.347 to -0.237) |
| Reply probability instead of spread | 0.907 | +0.913 |

- The reply probability was known for 279 of 290 rows; quartiles 0.18 / 0.53 / 0.74.
- Material on today's lines differs from the committed features TSV on 40 rows (lines changed since 2026-11-16),
  so the baseline must be re-measured, not read from the old report.

### Fixtures
- Prod game 2883555 ply 47 (user 28, rapid): played line Nxe6 f4 Nxc7 Kxc7, best line Bxf4 Qxf4 Qxf4 Rxf4.
- Phase 256's queen-trade best line `(1, 1, 1, 1, 10, 10, 1, 1, 1)`, a real gain of 1.

</specifics>

<deferred>
## Deferred Ideas

- **Blunder-check sequences with any facepalm score:** serve a small random share of sequences drawn from all
  scored blunders, flagged with a known sampling rate, to validate the score on user outcomes over the whole
  range and later fit on them. Open points: the outcome ("avoided it in a drill") is not the owner's label; the
  share must stay small because low-score blunders are the unfair ones; whether they count towards medals and
  streaks. A drill-selection change, its own phase.
- **A fit on user blunder-check answers:** once enough exist. Today nothing below a score of 0.50 is served.
- **Total probability of all punishing replies** instead of the best reply only: needs evaluations of every reply.
- **`detect_sacrifice` misses an offered sacrifice the engine declines** (same row has no allowed tactic tag): a
  new detector condition, to be checked against the precision fixtures.
- **Benchmark DB backfill of `loss`, `missed` and the reply probability:** with SEED-261120-bzq.
- **Decay ratio by rating** (stronger players look deeper): not fitted here (D-04).
- From Phase 256, still open: "the gain is a simple capture of an undefended piece", "the best move is the only
  winning move", a separate model for pure misses.

</deferred>

---

*Phase: 259-facepalm-first-principles-refit*
*Context gathered: 2026-11-21*
