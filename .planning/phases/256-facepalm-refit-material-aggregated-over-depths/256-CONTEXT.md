# Phase 256: Facepalm Refit on Material Aggregated over Depths (SEED-261115-agg) - Context

**Gathered:** 2026-11-16
**Status:** Ready for planning (execution waits for the set 8 labels, D-01)

<domain>
## Phase Boundary

The facepalm score reads the played line's loss and the best line's missed gain at one depth (`LINE_DEPTH` = 3).
For misses that depth carries no signal: the 2026-11-15 refit gave the missed gain a coefficient of 0.0891 against
1.0129 for the loss. This phase replaces both material inputs with an aggregate over the stored odd depths
1, 3, 5, 7, 9, refits on label sets 1 to 8, and releases new constants. Deliverables:

1. The fit script (`scripts/blunder_check/fit_facepalm.py`) compares three material inputs inside the full model
   and states its choice in the fit report.
2. Both score twins (`facepalm_score` and `facepalm_score_sql` in `app/services/facepalm_score.py`) compute the
   chosen input from the stored arrays, pinned together by `tests/services/test_facepalm_score.py`.
3. Review findings 254 WR-01 and WR-03 fixed.
4. New `FACEPALM_*` constants, a features TSV and fit report under `reports/blunder-check/`, and the owner's
   `FACEPALM_SCORE_MIN` decision.

Not in this phase: new columns, migrations or prod passes; scoring rows whose played line stops before depth 3;
a separate model for pure misses; new inputs ("simple capture of an undefended piece", "only winning move");
opponent moves or mistakes; UI changes.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (not re-discussed)
- The score is a query-time expression over stored facts; a refit is a constants deploy with no UPDATE pass over
  prod (254 D-01). The Python and SQL twins stay in parity.
- The score is a ranking, never presented as a probability (250 D-01). False alarms are worse than misses
  (250 D-03). User-side blunders only, no engine at scoring time (250 D-06, D-07).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; `--check-constants` reproduces them
  from a committed features TSV (250 D-04). Fit choices are made by the fit script and confirmed by the owner,
  never hand-tuned.
- Label 1 means "the facepalm score should be above 70%" (254 D-23). One label file,
  `reports/blunder-check/facepalm-labels.tsv` (254 D-22).
- `FACEPALM_SCORE_MIN` is set by the owner at a blocking checkpoint (254 D-13). The report shows fair / unfair
  among passers at cuts from about 50% to 70%, split by loss-type and miss-type, and the drill pool size.
- An unknown best line contributes `missed = 0`; the row keeps its loss-only score (254 D-18).
- Owner's goal (seed, 2026-11-16): a meaningful score. How many pure misses pass the drill cut is secondary.
- Fixed by the seed, not fitted: the decay ratio is 1/2; the aggregate reads only the odd depths 1, 3, 5, 7, 9
  (even slots are mid-exchange values, 254 D-17); weights are normalised over the known depths.
- Drill and library lambda stay 1.0 (254 D-03, D-04).

### Timing and coverage
- **D-01: The refit runs when label set 8 is labelled.** The labels are the only gate (60 rows, n 241 to 300,
  0 labelled on 2026-11-16). The plan needs a first precondition step that stops when set 8 has unlabelled rows.
- **D-02: The phase does not wait for Phase 252.** Features are pulled from prod as the lines are at that time. If
  252's repair and the gap-fill line pass (254 D-21) are done by then, they are used; otherwise NULL slots are
  skipped. No planned re-run after 252.
- **D-03: Depth 3 is still required for a row to be scored.** The coverage rule is unchanged: a row whose played
  line does not reach depth 3 (and has no mate that settles it) stays unscored. The aggregate adds depths 5, 7, 9
  where they exist. Coverage grows through 252's repair, not through this phase. (Depth 1 alone is the position
  right after the blunderer's own move and can rarely show a loss.)

### Unknown best-move probability (254 WR-01)
- **D-04: A no-loss row with a NULL `maia_best_prob` is unscored.** Under the `best_prob_for_misses` spread form,
  both twins return None / NULL when the row's loss is not above the gate and the best-move probability is NULL,
  as a NULL spread already does under `always`. Rows that lose material are unaffected. Those rows leave the drill
  pool and the library Facepalm filter and show no chip. Prod size 2026-11-16: 14,826 of 2,178,931 rows with
  scoring inputs (0.68%) have a NULL best prob, 14,592 of them also lack a best line.
- **D-05: The fit follows the same rule.** A label row that the shipped model would leave unscored under D-04 is
  excluded from the fit under that spread form, and the report counts such rows.

### Selection rule
- **D-06: Three candidates, the same input for the loss and the missed gain.** (a) decaying mean, (b) first stable
  value (the same balance at two odd depths in a row), discounted by its onset, (c) depth 3 as the reference. No
  mixed candidates (for example loss at depth 3 with the missed gain as a mean) and no single-depth candidates
  other than depth 3.
- **D-07: The choice is made by repeated cross-validation over sets 1 to 8,** on seed means, with the script's
  existing criteria (cross-validated AUC, then the fair share at the selection threshold), as Phase 254 did for
  the forms.
- **D-08: Set 8 is also a hold-out check.** Each candidate is additionally fitted on sets 1 to 7 and scored on set
  8 untouched; the report shows both results per candidate. Reason: the decaying mean was picked as the best of
  about 11 candidates on sets 1 to 7, and set 8 is the only fresh data, drawn where the candidates differ. If the
  cross-validated choice and the set 8 hold-out disagree, the owner decides at the D-13 checkpoint.
- **D-09: The decaying mean wins ties against depth 3** (within `AUC_TIE_TOLERANCE` and
  `FAIR_SHARE_TIE_TOLERANCE`). Depth 3 stays only if it is clearly better. Reason: the owner finds a single depth
  unintuitive, and the mean gives misses a real material coefficient (0.15 to 0.39 in the seed's probe).
- **D-10: Final constants are fitted on all eight sets.**

### Defaults for the areas not discussed (owner: use the seed and Phase 254)
- **D-11: The "loses material" gate is decided by the fit.** Under a mean, `loss > 0` flips on any small late loss
  and switches the spread term between the loss form and the best-move-probability form. The fit compares a gate
  threshold of 1 against no gate (`loss > 0`) with the D-07 criteria; the report states the choice. The gate is one
  named constant used by both twins and by the fit.
- **D-12: WR-03 is fixed in the fit script.** The exclusion becomes spread-form aware: a NULL `reply_spread` row
  stays in the fit when the candidate's spread form is gated and the row's loss is not above the gate. The report
  counts the rows that qualify only under a gated form.
- **D-13: One blocking owner checkpoint** after the fit report: the owner confirms the chosen input (and settles a
  D-08 disagreement) and sets `FACEPALM_SCORE_MIN`. The report lists, as information and not as automatic gates:
  the two owner fixtures (games 817357 ply 24 and 820181 ply 65), the 15 commented set 7 rows with their expected
  range and old and new scores, window 14 (game 2099808 ply 23, must still fall below the cut), and the pure-miss
  pass rate at each cut.
- **D-14: The material-form, spread-form and optional-input stages of the fit are re-run** on the new input, as
  the 254 fit ran them; the shipped shape ("split", `best_prob_for_misses`) is not assumed.
- **D-15: Release as a normal constants and code release** with a changelog bullet. Scores change for every user
  (library chip, Facepalm filter, drill pool); no migration, no backfill.

### Claude's Discretion
- How a mate enters the aggregate (for example the mate value from the mate ply onward). A mate within depth 3
  must keep scoring as today's `MATE_LOSS` / `FACEPALM_MISSED_MATE` case, not as "nothing lost or missed".
- The per-depth floor and cap of the gain series (`decaying_mean.py` floors the per-depth gain at 0; the shipped
  `FACEPALM_MISSED_FLOOR` is None), decided by the fit.
- How the SQL twin expresses the aggregate over the 9-slot arrays, and whether `decaying_mean.py` moves into
  `app/services/` so the twins and the scripts share one implementation.
- Names of the new constants, the exact onset discount of the first stable value, report layout.
- `TRAIN_SETS` / `TEST_SET` bookkeeping in `fit_facepalm.py` (set 6 was the hold-out so far).
- Whether the calibration and spot-check reports are re-run in full or only the tables D-13 needs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed and evidence
- `.planning/seeds/SEED-261115-agg-facepalm-material-across-depths.md` — evidence tables, the 2026-11-16 probe,
  owner decisions, constraints.
- `reports/blunder-check/facepalm-fit-2026-11-15.md`, `reports/blunder-check/facepalm-features-2026-11-15.tsv` —
  the shipped fit and its features.
- `reports/blunder-check/facepalm-labels.tsv` — sets 1 to 8; set 8 (n 241 to 300) is blind and unlabelled.
- `.planning/quick/261116-mco-facepalm-label-set-8-sampler-disagreemen/261116-mco-SUMMARY.md` — how set 8 was
  drawn (strata, threshold 0.5), the decaying-mean helper, the key file location (gitignored, never commit).

### Prior phase decisions
- `.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-CONTEXT.md` — D-01
  (query-time score), D-05 (material definitions), D-06 to D-08 (forms), D-13, D-17, D-18, D-21 to D-23.
- `.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-REVIEW.md` — WR-01 and
  WR-03 with fix sketches.
- `.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-REVIEW-DISPOSITION.md` —
  prod counts for WR-01.
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 to D-07 (score meaning, material count).

### Project rules
- `CLAUDE.md` — `Literal` types, nesting depth gate, pre-merge gate, changelog rule.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/blunder_check/decaying_mean.py`: `loss_series`, `gain_series`, `decaying_mean`, `DECAY_DEPTHS`,
  `DECAY_RATIO = 0.5`, `DECAY_WEIGHTS`; pure, tested in `tests/scripts/test_decaying_mean.py`, with depth-3 parity
  against the shipped `loss_feature` / `missed_feature`.
- `app/services/facepalm_score.py`: `FacepalmModel`, `FacepalmFacts`, `FacepalmColumns`, `loss_feature`,
  `missed_feature`, the twins, `facepalm_expr(lam)`. Today the facts are `played_3` / `best_3`; the aggregate needs
  the arrays.
- `scripts/blunder_check/fit_facepalm.py`: `CandidateSpec`, staged selection (`select_material_form`,
  `select_spread_form`, `select_pre_inputs`), `choose_candidate`, `REPEAT_SEEDS`, `AUC_TIE_TOLERANCE`,
  `FAIR_SHARE_TIE_TOLERANCE`, `_holdout`, `--check-constants`.
- `scripts/blunder_check/facepalm_features.py`: builds the features TSV from prod.

### Established Patterns
- Constants block in `app/services/blunder_check_rules.py` (`FACEPALM_*`, `LINE_DEPTH`, `LOSS_CAP`, `MATE_LOSS`).
- An optional term with a zero coefficient is omitted at build time in both twins, so an unused NULL input never
  unscores a row.
- The chip percent and the filter come from the same SQL expression (253 D-10).

### Integration Points
- Readers of the expression: `app/repositories/library_repository.py`, `app/services/library_service.py`,
  `app/repositories/blunder_check_repository.py`, `app/services/blunder_check_candidates.py`,
  `scripts/blunder_check/sample.py`, `render.py`, `spot_check.py`, `miss_labels.py`.
- `fit_facepalm.py:318` `_exclusion_reason` and `:570` `spec_row_values` (WR-03); `facepalm_score.py:237`
  `_best_prob_term` and `:333` `_best_prob_sql` (WR-01).
- `app/models/game_flaw.py`: `played_line_material`, `best_line_material` (9 slots, `array[3]` = depth 3).

</code_context>

<specifics>
## Specific Ideas

- Probe numbers to beat or confirm (indicative, not from `fit_facepalm.py`): decaying mean 0.916, depth 3 0.880,
  first stable discounted 0.872; paired bootstrap gain 0.035 (0.007 to 0.065).
- The seed's queen-trade best line (1, 1, 1, 1, 10, 10, 1, 1, 1) is a real gain of 1; a good fixture for the
  aggregate.
- Rows like `-3, -3, 0, ...` are labelled fair: the early swing is itself the signal, which is why the stabilised
  balance lost in the probe.
- Fixtures: games 817357 ply 24 and 820181 ply 65 (dev DB, user 28) score 0.15 today.

</specifics>

<deferred>
## Deferred Ideas

- **Scoring rows with a played line shorter than depth 3:** not here (D-03); revisit only if 252's repair leaves
  a relevant share unscored.
- **Mixed inputs** (loss at depth 3, missed gain as a mean) and other single depths: left out to keep the
  candidate count low (D-06).
- **Other inputs from the 2026-11-15 review:** "the gain is a simple capture of an undefended piece", "the best
  move is the only winning move", a separate small model for pure misses.
- **Largest loss at any depth for "neither" rows** (AUC 0.73 on 23 rows in the probe).
- **Loss-aversion weight for the drill below 1.0:** waits for GM Noel Studer's answer (254 deferred).

</deferred>

---

*Phase: 256-facepalm-refit-material-aggregated-over-depths*
*Context gathered: 2026-11-16*
