# Phase 262: Facepalm Promotions as Material and Key-Move Gate (SEED-261122-s0j) - Context

**Gathered:** 2026-11-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the facepalm score see pawn breakthroughs and score every blunder on the move that matches its type, in one
refit. Backend only.

- Promotions count as material in the stored inputs (`material_loss` / `material_missed`), in
  `app/services/line_material.py`.
- The key-move term of the score follows the type rule (`loss > 0 and loss >= missed`) instead of `loss > 0`,
  in both twins.
- One refit on label sets 1 to 8 with the new inputs and the new gate, new `FACEPALM_*` constants, one blocking
  owner checkpoint.
- A prod pass over the rows that carry a promotion, in place.

Out of scope (ROADMAP): an eval term or a longer horizon for blunders with no material in either line; draw
blunders (stalemate, threefold); a fit on user blunder-check answers; the benchmark DB backfill; new label sets.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (not re-discussed)
- First principles decide the model shape, the AUC is only a range check: the cross-validated AUC of the final
  model stays within about 0.02 of the shipped rule re-measured on today's lines (259 D-01, D-12).
- Label sets 1 to 8 as they are, no new label set (259 D-14). Fitted values are named constants, pasted as
  printed, reproduced by `--check-constants` (250 D-04).
- One blocking owner checkpoint after the fit report: the owner confirms the model and sets
  `FACEPALM_SCORE_MIN` and `FACEPALM_STATS_MIN`, with the fair / unfair table at cuts from about 50% to 70% and
  the drill pool size (259 D-15).
- The quiet rule, the decaying mean over the odd depths 1 to 9, the decay ratio 1/2 and the 9-ply horizon stay
  (259 D-02 to D-04, seed).
- The score stays a SQL expression with a Python twin; a coefficient or gate change is a constants deploy with no
  UPDATE pass (254 D-01). A material-rule change needs a recompute pass that replays games and stored lines, no
  engine and no Maia (259 D-05).
- The type rule itself is unchanged: allowed loss when `loss > 0 and loss >= missed`, a tie is an allowed loss
  (257 D-02).
- The drill's snapshotted scores on `blunder_check_windows` stay as served (261).

### Promotion value and cap
- **D-01: A promotion credits the promoting side with the promoted piece minus the pawn,** from the existing
  piece values 1 / 3 / 3 / 5 / 9: queen +8, rook +4, bishop or knight +2. A promotion with capture adds the
  captured piece as today. The gain is added inside `_victim_value`, so the quiet walk continues through a
  recapture, the first move is covered, and a line that ends on a promotion is settled by the static exchange.
  A captured promoted piece then nets out to the pawn.
- **D-02: The per-depth cap stays at 5 for promotions** (`LOSS_CAP`, `FACEPALM_MISSED_CAP`). A queen promotion
  counts like a hung queen or a mate at the same depth. No cap or floor constant changes, so no row outside the
  promotion set changes its stored inputs. Owner confirmed after an explanation of the cap (per-depth balance,
  clip to 0..5, then the decaying mean).
- **D-03: Desperado test (ROADMAP).** The capture of a freshly promoted piece on its promotion square must
  count. With D-01 a blunderer's promotion has a non-zero value and no longer sets the desperado square; a test
  pins this.

### Key-move gate
- **D-04: No minimum loss. The gate is exactly the type rule.** The score reads the opponent's reply
  (`maia_best_reply_prob`) when `loss > 0 and loss >= missed`, and the best move (`maia_best_prob`) otherwise.
  One shared condition for `facepalm_score`, `facepalm_score_sql` and the type twins. Prod evidence: of the
  allowed-loss rows with a loss below 0.25, 4,585 pass 0.7 (about 0.4% of 1.2M passers); a floor would matter
  only in the score range no cut reads, and would either split gate and type again or retype about 213k rows.
- **D-05: The fit report shows the old gate as a reference line.** The model is fit with the new gate. The
  report adds one comparison for the old gate (`loss > 0`) on the same inputs: AUC and the fair / unfair counts
  at 0.7. Information only, the fit does not choose (259 D-01).
- The NULL rules follow the gate: an allowed loss with a NULL reply probability and any other row with a NULL
  best-move probability are unscored. On prod about 1,600 mixed rows lose their score this way (no
  `maia_best_prob`); accepted, listed in the fit report.

### Prod rollout
- **D-06: One release, then the pass in place.** The release ships the promotion rule (go-forward hook), the
  new gate and the new constants together. The pass over `material_loss` / `material_missed` runs straight
  after the deploy. For those minutes about 3.3% of rows carry old inputs under the new coefficients; accepted.
  No shadow columns, no migration. This relaxes 259 D-11 for this phase.
  — **Reversibility:** costly — the pass overwrites the stored pair in place; going back needs a second pass
  with the old rule over the same rows (replay only, no engine).
- **D-07: The pass covers promotion rows only.** Blunders with a promotion token in the refutation line
  (`game_positions.pv` at ply + 1), the best line (`pv` or `best_move` at the flaw ply) or the played move.
  Prod estimate: about 165k candidates, about 145k rows change. Re-runnable, one connection (prod
  `max_connections` 50). A dry run first reports the rows that would change and checks on a sample that rows
  without a token replay to their stored values.
- The refit, the fit report and the checkpoint come before the release: the features are computed with the new
  rule from the lines (not from stored prod columns), so the constants exist before anything changes on prod.
- Release as a normal release with a changelog bullet: scores change for every user (259 D-16).

### After the refit
- **D-08: The provisional bands in `app/services/facepalm_zones.py` are not re-derived in this phase.** Owner:
  "We'll update them once phase 252 concludes" (the benchmark re-walk that the benchmark zones of
  SEED-261120-bzq wait for). The module docstring gets a note that the bands are from the Phase 259 model.
  The planner checks whether `tests/services/test_facepalm_zones.py` pins anything the refit breaks.

### Claude's Discretion
The owner did not select "Bands and snapshots after refit"; apart from D-08 these defaults were proposed and
not objected to:
- The 261 snapshots stay untouched. The caught-rate calibration (`scripts/blunder_check/caught_rate.py`)
  separates answers from before and after the switch by a release-date constant, not by a new column.
- `HARD_TO_CATCH_SCORE_BELOW` (0.5, in Phase 259 score units) is re-checked at the checkpoint on the new score.
- The covering index `ix_game_flaws_facepalm_inputs`: the new gate reads the same five columns, so no rebuild is
  expected; the planner confirms index-only scans with EXPLAIN on prod before the release.
- How the pass is built (a mode of `scripts/backfill_maia_flaws.py` line pass or a small script), how the token
  filter is expressed in SQL, sharding and the report format.
- Which labelled promotion rows and which about 20 newly passing rows the checkpoint spot-check shows (ROADMAP:
  about 20 rows that newly pass 0.7).
- Whether the spike probes are deleted or kept as a script under `scripts/blunder_check/`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition and evidence
- `.planning/ROADMAP.md` (Phase 262) — goal, the two changes, open points, out of scope, downstream order.
- `.planning/seeds/SEED-261122-s0j-facepalm-promotions-as-material.md` — problem, dev replay numbers, the
  key-move gate table, example row (dev game 1457348 ply 99), "checked and dropped".
- `.planning/phases/262-facepalm-promotions-and-key-move-gate/spike/promo_probe.py` — dev probe of the seed.
- `.planning/phases/262-facepalm-promotions-and-key-move-gate/spike/promo_gate_probe_prod.py` — read-only probe
  for four variants (current, promotions, gate, both) on a game sample; run with `PYTHONPATH=.` from the main
  checkout, `--db prod --mod 10`.

### Prior decisions
- `.planning/phases/259-facepalm-first-principles-refit/259-CONTEXT.md` — D-01 to D-05 (principle, quiet rule,
  decaying mean, storage), D-11 (one switch, relaxed here by D-06), D-12 to D-17 (acceptance, checkpoint, index).
- `.planning/phases/261-blunder-check-exploration-arm/261-CONTEXT.md` — snapshots, D-06 (hard-to-catch cut),
  the calibration script.
- `.planning/phases/260-facepalm-first-class-move-quality/260-CONTEXT.md` — readers of the score and the type.

### Fit and labels
- `reports/blunder-check/facepalm-labels.tsv` — the one label file.
- `reports/blunder-check/facepalm-fit-2026-11-22.md` — the shipped fit report (format of the checkpoint table).
- `reports/blunder-check/quiet-rule-review-2026-11-21.md` — format of a rule review with before / after rows.
- `docs/dev-tooling.md` — `scripts/backfill_maia_flaws.py` modes (`--mode line --cutoff`), prod run rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/line_material.py` — `_victim_value` (the one place for D-01), `_count_step` (desperado
  exclusion), `_quiet_walk_end`, `_exchange_value` / `_best_recapture` (the static exchange has its own victim
  lookup via `_SEE_VALUES`; check that a line ending on a promotion is settled as the ROADMAP says).
- `app/services/facepalm_inputs.py` — `facepalm_material_inputs`, the single writer used by the hook, the line
  pass and the features pull.
- `app/services/facepalm_score.py` — `_key_move_term` / `_key_move_sql` (the gate, D-04), `facepalm_type_of` /
  `facepalm_type_sql` (the condition to share), the module docstring that states the gate.
- `app/services/facepalm_material.py` — `loss_by_depth`, `gain_by_depth` (per-depth caps), `decaying_mean`.
- `app/services/blunder_check_rules.py` — `FACEPALM_*` constants and the comment block naming the fit command.
- `scripts/blunder_check/fit_facepalm.py`, `scripts/blunder_check/facepalm_features.py` — the fit tool and the
  features pull; `scripts/backfill_maia_flaws.py` — the Maia-free line pass.
- Tests: `tests/services/test_line_material.py`, `test_facepalm_inputs.py`, `test_facepalm_score.py` (pins the
  twins), `test_facepalm_owner_fixtures.py`, `tests/scripts/test_fit_facepalm.py` (`--check-constants`).

### Established Patterns
- Python and SQL twins change together; a NULL guard is the first CASE branch in the SQL twin.
- Prod operator runs: one at a time, detached (`setsid nohup`, `PYTHONUNBUFFERED=1`), from the orchestrator,
  over `bin/prod_db_tunnel.sh`.
- Monkeypatching `_victim_value` (as the probes do) is spike-only; the real rule lives in the function.

### Integration Points
- Go-forward hook and the line pass both call `facepalm_material_inputs`, so D-01 reaches new rows with the
  deploy and old rows with the pass.
- Readers of the score: library chip and filter, stats, drill pool, exploration arm (260, 261); none changes.

</code_context>

<specifics>
## Specific Ideas

### Prod probe, 2026-11-23 (the ROADMAP's first step)
10% game sample of prod (442,844 scored blunders, scaled x10), today's coefficients, so before the refit. The
gate-only numbers were also computed exactly on all prod rows in SQL (74,060 leave, 16,766 enter) and agree.

| Rows at 0.7 or above | Today | Promotions only | Gate only | Both |
|---|---|---|---|---|
| All | 1,542,010 | 1,562,190 (+1.3%) | 1,484,350 (-3.7%) | 1,503,510 (-2.5%) |
| Enter / leave | | 24,150 / 3,970 | 16,280 / 73,940 | 38,600 / 77,100 |
| Allowed loss | 1,206,800 | 1,223,180 | 1,206,800 | 1,223,180 (+1.4%) |
| Missed win | 335,210 | 339,010 | 277,550 | 280,330 (-16.4%) |
| Player's own blunders | 776,780 | 786,810 | 745,310 | 754,940 (-2.8%) |

- "Player's own blunders" is a proxy for the drill pool; the drill's other filters are not applied.
- Promotion rule: 165,740 candidate rows (3.7%), inputs change on 144,810 (3.3%); loss up / down 86,060 /
  16,180, missed up / down 70,090 / 22,950; type missed win to allowed loss 44,820, reverse 9,140.
- Gate: all of the effect is in the 392,571 rows with a loss that are typed missed win; their mean score goes
  from 0.607 to 0.417.
- Allowed-loss rows by loss (all prod, score on the reply vs on the best move, rows at 0.7 or above):
  loss up to 0.07: 49,634 rows, 797 vs 268; below 0.25: 163,537 rows, 3,788 vs 1,260; below 0.5: 192,878 rows,
  7,130 vs 2,387; below 1: 239,187 rows, 36,487 vs 7,734; 1 or more: 1,624,519 rows, 1,153,667 vs 467,060.
- Dev check: the probe reproduces the seed's cut and type numbers (121 / 25, 345 / 49, 243 / 44) but counts
  710 changed inputs where the seed says 624. Not explained; the planner or researcher should settle it before
  the pass's dry-run numbers are trusted.

### Cap examples shown to the owner (D-02)
| Case | Per-depth values (1, 3, 5, 7, 9) | Stored loss |
|---|---|---|
| Queen hung on the next move | 5, 5, 5, 5, 5 | 5.00 |
| Opponent queens on the next move, queen stays | 5, 5, 5, 5, 5 | 5.00 |
| Opponent queens at ply 5, queen stays | 0, 0, 5, 5, 5 | 1.13 |
| Opponent queens at ply 5, queen is taken at once | 0, 0, 1, 1, 1 | 0.23 |
| Knight lost at ply 3 | 0, 3, 3, 3, 3 | 1.45 |

These are natural unit-test fixtures for the new rule.

</specifics>

<deferred>
## Deferred Ideas

- Re-deriving the provisional facepalm bands: after Phase 252 concludes, with the benchmark zones
  (SEED-261120-bzq). Until then the bands are from the Phase 259 model while missed-win passers drop by about
  16% before the refit.
- Benchmark DB material backfill: SEED-261120-bzq, after this phase so it runs once with the final rule.

</deferred>

---

*Phase: 262-Facepalm Promotions as Material and Key-Move Gate (SEED-261122-s0j)*
*Context gathered: 2026-11-23*
