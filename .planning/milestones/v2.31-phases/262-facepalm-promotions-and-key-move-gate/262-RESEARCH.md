# Phase 262: Facepalm Promotions as Material and Key-Move Gate - Research

**Researched:** 2026-11-23
**Domain:** In-repo backend: material walk (python-chess), facepalm score twins (Python + SQLAlchemy), offline logistic refit, a targeted prod data pass
**Confidence:** HIGH (every claim below was checked against the code or measured on the dev DB in this session; no external library research was needed)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (not re-discussed)
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

#### Promotion value and cap
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

#### Key-move gate
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

#### Prod rollout
- **D-06: One release, then the pass in place.** The release ships the promotion rule (go-forward hook), the
  new gate and the new constants together. The pass over `material_loss` / `material_missed` runs straight
  after the deploy. For those minutes about 3.3% of rows carry old inputs under the new coefficients; accepted.
  No shadow columns, no migration. This relaxes 259 D-11 for this phase.
  Reversibility: costly. The pass overwrites the stored pair in place; going back needs a second pass
  with the old rule over the same rows (replay only, no engine).
- **D-07: The pass covers promotion rows only.** Blunders with a promotion token in the refutation line
  (`game_positions.pv` at ply + 1), the best line (`pv` or `best_move` at the flaw ply) or the played move.
  Prod estimate: about 165k candidates, about 145k rows change. Re-runnable, one connection (prod
  `max_connections` 50). A dry run first reports the rows that would change and checks on a sample that rows
  without a token replay to their stored values.
- The refit, the fit report and the checkpoint come before the release: the features are computed with the new
  rule from the lines (not from stored prod columns), so the constants exist before anything changes on prod.
- Release as a normal release with a changelog bullet: scores change for every user (259 D-16).

#### After the refit
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

### Deferred Ideas (OUT OF SCOPE)
- Re-deriving the provisional facepalm bands: after Phase 252 concludes, with the benchmark zones
  (SEED-261120-bzq). Until then the bands are from the Phase 259 model while missed-win passers drop by about
  16% before the refit.
- Benchmark DB material backfill: SEED-261120-bzq, after this phase so it runs once with the final rule.
- (ROADMAP out of scope) an eval term or a longer horizon for blunders with no material in either line; draw
  blunders (stalemate, threefold); a fit on user blunder-check answers; new label sets.
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped (ROADMAP: "Requirements: TBD"). The decisions D-01 to D-08 are the requirements;
this table maps each to the findings that enable it.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Promotion gain inside `_victim_value` | Finding 1: covers the walk, first move and SEE only if `_exchange_value` also reads `_victim_value` (one-line change); new fixture values computed |
| D-02 | Cap stays 5 | No constant changes; cap examples reproduced in code (1.129, 5.0) except one CONTEXT example that is wrong (Pitfall 3) |
| D-03 | Desperado test for a freshly promoted piece | Constructed fixture verified: old (0,0,0,0,0), new (1,1,1,1,1) |
| D-04 | Gate = type rule, shared condition | Finding 3: exact gate sites, NULL handling via `coalesce(missed, 0)`, every copy of `loss > 0` listed |
| D-05 | Old gate as a reference line in the fit report | Finding 4: offline refit preview of all four input/gate variants |
| D-06 | One release, pass in place, right after deploy | Finding 5: pass design, timing, undo log |
| D-07 | Pass covers promotion-token rows only, dry run, sample check | Finding 2 (710 vs 624 settled: float32 artifact), Finding 5 (SQL filter, float32 compare) |
| D-08 | Bands not re-derived, docstring note | `test_facepalm_zones.py` pins only literal half-widths: nothing breaks |
</phase_requirements>

## Summary

The phase is small in code and medium in operations. Three source files change behaviour
(`app/services/line_material.py`, `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py`), two fit
scripts follow the gate, one new pass script writes prod, and the caught-rate script gets a version split. Every
reader of the score already goes through `facepalm_expr` / `facepalm_type_expr`, so the gate change reaches the
library, stats, drill pool, analysis badge and exploration arm with no reader edits.

Five findings change how the plan should be written. (1) Adding the gain inside `_victim_value` alone does NOT
reach the static exchange: `_exchange_value` computes its own victim value from `_SEE_VALUES` and ignores
promotions. Making `_exchange_value` read `_victim_value(board, capture)` fixes it in one line (a victim is never
a king, so the values are identical otherwise); a real dev row (game 1461554 ply 63, best line ending
`b2b1q f1b1` with an `a2xb1=q` recapture in the SEE) changes only with that fix. (2) The 710 vs 624 dev
discrepancy is a probe artifact: `material_loss` / `material_missed` are `REAL` (float4) and
`promo_gate_probe_prod.py` compares float64 replays to stored float4 values with a 1e-9 tolerance. Compared
after rounding to float32, the count is exactly 624; 86 rows are pure rounding artifacts. The prod numbers in
CONTEXT ("inputs change on 144,810") carry the same inflation; expect roughly 127k real changes. (3) An offline
refit on the committed `facepalm-features-2026-11-22.tsv` (raw lines are in the file, no DB or Maia needed)
reproduces the shipped constants exactly and previews the new model: cross-validated AUC 0.889 vs 0.908 for the
shipped rule on the same lines, a gap of 0.019 against the 0.02 range. That is inside the range but by a hair,
so the checkpoint must hear it. (4) Four committed line fixtures (labels 35, 170, 162, 177) change expected
values by design, and label 177 (labelled unfair: "the opponent 'material' is a promotion in an endgame race")
gets a loss of 3.87 under the new rule. (5) A dedicated small pass script fits D-07 better than a line-mode flag.

**Primary recommendation:** Implement D-01 as a `_promotion_gain(move)` helper added in `_victim_value`, and make
`_exchange_value` use `_victim_value` for its gain; add one public `is_allowed_loss` (Python) and one
`_allowed_loss_sql` (SQL) shared by the four twins; build the new features table offline from the committed
2026-11-22 table; write a dedicated idempotent pass script that compares in float32 and updates only changed rows.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Promotion as material (D-01, D-03) | API / Backend (pure service `line_material.py`) | — | Write-time rule, no I/O; the hook, the pass and the features tool all call `facepalm_material_inputs` |
| Key-move gate (D-04) | Database / Storage (SQL twin evaluated at query time) | API / Backend (Python twin) | The score is a query-time SQL expression over stored scalars (254 D-01); the Python twin must match |
| Refit and constants (D-05) | Offline script (`scripts/blunder_check/fit_facepalm.py`) | API / Backend (constants in `blunder_check_rules.py`) | Fit reads only a committed TSV; app holds pasted constants |
| Promotion pass (D-06, D-07) | Operator script against Database | — | One connection, detached, over the tunnel; writes two REAL columns |
| Caught-rate version split | Offline script (`caught_rate.py`) | — | Read-only report; release-date constant, no column |
| Bands note (D-08) | API / Backend docstring | — | No value change |

## Standard Stack

No new dependencies. Everything uses what the repo already pins.

| Library | Version (verified) | Purpose | Note |
|---------|-------------------|---------|------|
| python-chess | 1.11.2 `[VERIFIED: uv run python -c "import chess; print(chess.__version__)"]` | Line replay, promotion moves | Promotion moves are generated in the order q, r, b, n (verified: `['b7a8q', 'b7a8r', 'b7a8b', 'b7a8n']`), so `min()` in `_best_recapture` picks the queen promotion first among a pawn's capture-promotions |
| numpy | 2.5.2 `[VERIFIED: uv run]` | IRLS fit in `fit_facepalm.py` | unchanged |
| SQLAlchemy 2.x async + asyncpg | repo pin | SQL twin, pass writes | unchanged |
| pytest (+ xdist) | repo pin | tests | baseline: 171 facepalm tests pass in ~13 s with `-n 4` (run this session) |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: the phase installs no external packages.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Key Findings (the questions the plan depends on)

### Finding 1: Does the gain inside `_victim_value` reach all three cases? Mostly; the static exchange needs one more line

Current code, quoted from `app/services/line_material.py` `[VERIFIED: app/services/line_material.py:56-64, 128-133, 147-156]`:

```python
PIECE_VALUES: Mapping[chess.PieceType, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}
...
def _victim_value(board: chess.Board, move: chess.Move) -> int:
    """Material value of the piece `move` captures on `board` (0 for a non-capture)."""
    if board.is_en_passant(move):
        return EN_PASSANT_VALUE
    piece = board.piece_at(move.to_square)
    return PIECE_VALUES[piece.piece_type] if piece else 0
...
def _exchange_value(board: chess.Board, capture: chess.Move) -> int:
    """Static exchange value of `capture` for the side making it (pawn units, may be negative)."""
    victim = board.piece_at(capture.to_square)
    if victim is not None:
        gain = _SEE_VALUES[victim.piece_type]
    else:
        gain = EN_PASSANT_VALUE if board.is_en_passant(capture) else 0
    after = board.copy(stack=False)
    after.push(capture)
    return gain - _best_recapture(after, capture.to_square)
```

How each case behaves once `_victim_value` adds `PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]`:

| Case | Mechanism | Reached by `_victim_value` alone? |
|---|---|---|
| First move (blunder or best move) is a promotion | `first_victim = _victim_value(board, first)` in `_quiet_facts_after_first_move` | Yes |
| Quiet walk continues through a recapture | `_quiet_walk_end` keeps walking while `steps[end].victim_value` is truthy; a promotion step now has victim 8 (queen) | Yes. Note it also continues INTO a promotion that is the next move after the depth (a promotion is now non-quiet, like a capture). Label 177 shows this: depth 5 reads -3 because White's `a7a8q` at ply 6 is consumed |
| Line ends on a promotion, settled by SEE | `_ends_in_exchange(steps)` is true when `last.victim_value` is non-zero, then `_best_recapture(end_board, last.to_square)` | Yes for the trigger. The SEE then prices the promoted queen at 9 via `_SEE_VALUES`, which is correct (promotion +8, capture of the queen -9, net the pawn) |
| A capture-promotion made INSIDE the SEE (e.g. `a2xb1=q` recapture) | `_exchange_value` computes `gain` itself from `_SEE_VALUES` and never adds the promotion gain | **No.** Needs `gain = _victim_value(board, capture)` in `_exchange_value` |
| D-03: blunderer promotes quietly, opponent takes the new piece on its square | `_count_step` sets the desperado square only when `step.victim_value == 0`; a quiet promotion now has victim 8, so no desperado square is set and the capture counts | Yes |

`_SEE_VALUES` differs from `PIECE_VALUES` only for the king (100 vs 0), and a king is never a victim, so
replacing the gain lines in `_exchange_value` with `gain = _victim_value(board, capture)` changes nothing for
non-promotion captures and keeps the king ordering of attackers (`_best_recapture` still sorts attackers by
`_SEE_VALUES`) `[VERIFIED: app/services/line_material.py:69-72, 136-144]`.

Measured on dev (read-only replay of all 21,180 blunders in line-stamped games, this session):

| Variant | Rows that change vs stored |
|---|---|
| Gain in `_victim_value` only (what the probes monkeypatch) | 624 |
| Gain in `_victim_value` and in `_exchange_value` | 624 (one row differs between the two variants: game 1461554 ply 63, missed 0.129 vs 0.161) |
| Non-token rows (20,381) under either variant | 0 |
| Stored values vs current-rule replay (float32 compare) | 0 mismatches |

`[VERIFIED: dev DB replay, scratchpad scripts variants_lined.py / nontoken.py]`

New expected values for the committed line fixtures that contain promotions (computed with the SEE-aware
variant; these tests break by design and get these values) `[VERIFIED: replay of tests/services/line_material_fixtures.py this session]`:

| Fixture | Old `expected_quiet_loss` | New | Why |
|---|---|---|---|
| n35 (`a3b2 g2e4 b2b1q ...`) | (0, 0, 0, 0, 0) | (0, 8, 8, 8, 8) | opponent queens at ply 3 |
| n170 (`... g7g8q d8g8 g6g8 ...`) | (0, 0, 0, -4, -4) | (0, 0, 0, 4, 4) | the old -4 was the "captured promoted queen credited 9" mispricing |
| n177 (`f2f1q ... a7a8q ...`) | (-3, -3, -3, -3, -3) | (5, 5, -3, -3, -3) | opponent queens at ply 1; White queens back at ply 6 (consumed at depth 5) |
| n162 (blunder `b7b8q`, mate in 1) | (0, 0, 0, 0, 0), mate 1 | (-8, -8, -8, -8, -8), mate 1 | the blunderer's own promotion; stored loss unchanged (mate dominates) |

The two owner miss fixtures (games 817357 / 820181) do not change (loss 0.0 / missed 3.0 and 0.0 / 5.0).

Constructed positions for the new synthetic tests (verified this session with the SEE-aware variant):

| Case | FEN / blunder / line | Per-depth loss (1,3,5,7,9) | Stored loss |
|---|---|---|---|
| Opponent queens next move, queen stays | `6k1/8/8/8/8/8/2p5/1R4K1 w - - 0 1`, `b1b3`, `c2c1q g1h2 g8f7 b3b7 f7e6 b7b6 e6d5 b6b5 d5c4 b5b8` | (8, 8, 8, 8, 8) | 5.0 |
| Opponent queens at ply 5, queen stays | same FEN, `g1h1`, `g8f7 h1g2 f7e6 b1b3 c2c1q b3b8 e6d5 b8b5 d5c4 b5b8` | (0, 0, 8, 8, 8) | 1.1290 |
| Opponent queens at ply 5, queen taken at once | same FEN, `g1h1`, `g8f7 h1g2 f7e6 b1a1 c2c1q a1c1 e6d5 c1c8 d5d4 c8c1` | (0, 0, -1, -1, -1) (old rule: (0, 0, -9, -9, -9)) | 0.0 |
| Line ends on the promotion, SEE recaptures | same FEN, `g1h1`, `c2c1q` | (-1, -1, -1, -1, -1) (old rule: (0, None, None, None, None)) | 0.0 |
| D-03: blunderer promotes, opponent takes the new queen | `1r4k1/P7/8/8/8/8/8/6K1 w - - 0 1`, `g1h1`, `g8f7 a7a8q b8a8 h1g1 f7e6 g1f2 e6d5 f2e3 d5c4 e3d2` | (1, 1, 1, 1, 1) (old rule: all 0) | 1.0 |

The existing desperado test (`_DESPERADO_FEN`, rook to a2 taken there) keeps its zero loss.

### Finding 2: Why the probe counts 710 changed inputs where the seed says 624

Settled. It is a float32 comparison artifact in `promo_gate_probe_prod.py`, not new rows, not a different candidate
set, not a rule difference.

- `material_loss` and `material_missed` are `REAL` columns `[VERIFIED: app/models/game_flaw.py:187-188]`:
  `material_loss: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)` and
  `material_missed: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)`.
- `promo_probe.py` (the seed's probe) compares the new float64 replay to the current-rule float64 replay; the
  prod probe compares the new float64 replay to the stored float4 value with
  `abs(l1 - l0) > 1e-9` (`spike/promo_gate_probe_prod.py:245`). Decaying means like 1.4516129... are not exactly
  representable in float4, so the stored value differs from the replay by about 1e-8.
- Measured on dev: same 797 candidate rows in both probes; change vs replay = 624; change vs stored at 1e-9 =
  710; change vs stored after rounding the replay to float32 = 624; float32 artifacts = 86
  `[VERIFIED: scratchpad discrepancy.py run on dev]`. The probe's extra `p1.move_san LIKE '%=%'` clause (the
  opponent's actual game move after the blunder, which is not an input) added 0 rows on dev.
- The probe's other counters (loss up 440 vs 354, missed up 313 vs 241, ...) are inflated the same way. Its
  enter / leave / type counts are not materially affected.

Consequence for the pass: its "would change" test must compare in float32 (or with a tolerance around 1e-6,
the precedent is `STORED_FLOAT_TOLERANCE = 1e-6` in `tests/services/test_facepalm_owner_fixtures.py`). The
CONTEXT prod estimate of "inputs change on 144,810 (3.3%)" is inflated by the same artifact; at the dev ratio
(624 / 710) the real number is about 127k `[ASSUMED: dev ratio applied to prod]`. The dry run gives the real one.

### Finding 3: Where the gate lives and what shares it

Gate and type today `[VERIFIED: app/services/facepalm_score.py:218-222, 261-271, 323-332, 343-358]`:

```python
def _key_move_term(model: FacepalmModel, facts: FacepalmFacts, loss: float) -> float | None:
    """The key-move term: the reply on a losing row, the best move otherwise (None = unscored)."""
    if loss > 0:
        return _log_term(model.reply_prob_coef, facts.reply_prob)
    return _log_term(model.best_prob_coef, facts.best_prob)
...
    return case(
        (columns.played_prob.is_(None) | columns.loss.is_(None), null()),
        (columns.loss > 0, _log_term_sql(model.reply_prob_coef, columns.reply_prob)),
        else_=_log_term_sql(model.best_prob_coef, columns.best_prob),
    )
...
    return "allowed_loss" if loss > 0 and loss >= missed else "missed_win"
...
    missed = func.coalesce(columns.missed, literal(0.0))
    ...
            (and_(columns.loss > 0, columns.loss >= missed), literal("allowed_loss")),
```

Recommended shape (one condition, four users):

- Python: a public `is_allowed_loss(loss: float, missed: float | None) -> bool` returning
  `loss > 0 and loss >= (0.0 if missed is None else missed)`. `facepalm_type_of` and `_key_move_term` call it
  (`_key_move_term` passes `facts.missed`). The NULL-missed-as-0 rule matches today's `facepalm_type`.
- SQL: `_allowed_loss_sql(columns) -> ColumnElement[bool]` returning
  `and_(columns.loss > 0, columns.loss >= func.coalesce(columns.missed, literal(0.0)))`, used by `_key_move_sql`
  (second CASE branch) and `facepalm_type_sql`. The NULL guard stays the first CASE branch.
- The gate compares the raw `missed`, never `lam * missed` (the type is lambda-free, 257 D-02).
- Compiled `facepalm_expr` is 549 characters today and the test limit is 2000 (`MAX_EXPRESSION_CHARS`), so the
  extra `coalesce` is safe `[VERIFIED: compiled this session]`.

NULL rules after the change: a row with `loss > 0 and loss >= missed` needs `maia_best_reply_prob`; every other
scored row needs `maia_best_prob`. Dev has 1,728 mixed rows (loss > 0, loss < missed) and none of them lacks
`maia_best_prob`, so no dev row loses its score `[VERIFIED: dev SQL count]`. CONTEXT reports about 1,600 on prod.

Other copies of `loss > 0` that should follow the shared condition (grep, then read):

| File:line | What it is | Action |
|---|---|---|
| `scripts/blunder_check/fit_facepalm.py:367` (`missing_reason`) and `:424` (`design_row`, `losing = loss > 0`) | the fit's gate | must change (the refit is defined by it); keep a gate switch for the D-05 old-gate line |
| `scripts/blunder_check/fit_facepalm.py:8` and `app/services/blunder_check_rules.py:90` | formula in docstring / comment | update text |
| `scripts/blunder_check/facepalm_features.py:631` (`_has_null_score_input`) | summary count of unscorable rows | use `is_allowed_loss` |
| `scripts/backfill_maia_flaws.py:1070-1078` (`reply_residue_losing` uses `GameFlaw.material_loss > 0`, `unscored_pure_miss_no_best` uses `material_loss <= 0`) | `--status --mode reply` residue counters | follow the shared condition so status matches what is unscored |
| `tests/facepalm_seed.py` `_seed_facts` (`loss > 0` picks where the key probability goes) | test seeding | candidates never mix loss and missed, so it stays correct; switching to `is_allowed_loss` is cosmetic |
| `scripts/blunder_check/metrics.py:186` (`material_type_of`, `loses = loss > 0`) | the D-15 table's loses / misses split | a different classification on purpose; leave |

Readers that need no edit: every reader uses `facepalm_expr` / `facepalm_type_expr` (library repository, train
repository `_game_move_is_facepalm`, blunder-check candidates and selection) or `facepalm_type_of`
(`blunder_check_selection.py:887`, `blunder_check_feedback.py:120`).

Tests that pin the twins and how they react:

| Test | Effect of the change | Action |
|---|---|---|
| `test_facepalm_score.py::test_formula_is_the_logistic_of_the_linear_predictor` (loss 3, missed 2; loss 0) | unchanged (3 >= 2 is an allowed loss) | add a mixed case (loss 1, missed 2 reads the best term) |
| `::test_missing_input_gives_none` | unchanged (default missed 0) | add: mixed row with NULL best is None, mixed row with NULL reply is scored |
| `::test_sql_twin_parity_grid`, `::test_sql_type_twin_parity_grid` | stay green if both twins change together; the grid already holds mixed rows (loss 2.0 with missed 3.0) and loss with missed None | none, they are the guard |
| `::test_expr_matches_python_twin_over_stored_facts` (`_STORED_FACT_ROWS`) | no mixed row in the seeded facts | add one mixed row (e.g. loss 1.0, missed 3.0, best 0.3, reply None) |
| `::test_known_d04_constants` pins `FACEPALM_SCORE_MIN == 0.7` | breaks only if the owner moves the drill cut | update with the owner's value |
| `::test_facepalm_stats_min_is_the_frontend_facepalm_cut` | breaks if the owner moves the stats cut: it parses `FACEPALM_HIGH_CUTOFF = 70` from `frontend/src/lib/facepalm.ts` | if moved, edit the frontend constant too (precedent: 259-12 listed `frontend/src/lib/facepalm.ts` and `frontend/src/lib/__tests__/gapBar.test.ts`) |
| `::test_window_14_is_not_selected_by_the_shipped_model` | must stay below the cut under the new model; preview scores 0.162 | none expected |
| `test_facepalm_owner_fixtures.py::test_owner_fixtures_stay_on_the_accepted_side_of_the_cut` | preview scores 0.130 and 0.218 (below 0.7) | none expected; re-verify after the real fit |
| `tests/scripts/test_fit_facepalm.py::test_shipped_constants_reproduce_from_the_committed_features` | breaks by design (new constants) | repoint `COMMITTED_FEATURES` to the new features file |
| `::test_synthetic_recovery_and_constants_block` | **breaks by design**: `synthetic_rows` draws labels with the old gate (`np.where(losing, reply..., best...)`, `losing` = loss > 0) while about a third of losing rows have missed > loss | generate with the type gate (`losing & (loss >= missed)`) |
| `::test_design_row_gates_reply_and_best_terms_by_loss` | unchanged (its losing row has loss 1.5 > missed 0.5) | add a mixed row reading the best term |
| `::test_fit_scoring_equals_the_app_twin` | stays green if fit and twin share the gate | repoint to the new features file |
| `test_facepalm_zones.py` | pins only the literal half-widths, which D-08 keeps | none (docstring note only) |
| `test_line_material.py::test_label_fixture_quiet_rule` and `::test_material_array_is_negated_loss_on_label_fixtures` | 4 fixtures change (table in Finding 1) | update `expected_quiet_loss` and the notes in `tests/services/line_material_fixtures.py` |
| `tests/scripts/test_facepalm_features.py::test_null_score_input_follows_the_shipped_score` | uses losing (2, 0) and level (0, 3) only | add a mixed case if `_has_null_score_input` changes |

### Finding 4: The fit tool, the features table and an offline refit

- `fit_facepalm.py` reads only a features TSV; the gate is hard-coded in `missing_reason` and `design_row`. The
  "shipped_baseline" shape today is the Phase 256 rule (`loss_shipped` / `missed_shipped`, spread on losing
  rows). Constants print as `FACEPALM_X: float = 0.1234` in a `## Constants` block; `--check-constants` compares
  each with `blunder_check_rules` within `CHECK_CONSTANTS_TOLERANCE = 1e-4` `[VERIFIED: scripts/blunder_check/fit_facepalm.py:76-79, 981-985, 1032-1045]`.
- `facepalm_features.py` computes `loss` / `missed` from the lines with the app's own functions
  (`material_inputs_from_facts(quiet_line_facts(...), quiet_best_line_facts(...))`), not from stored columns.
  A fresh pull needs prod (read-only) and Maia (`--group maia-inference`).
- The committed `reports/blunder-check/facepalm-features-2026-11-22.tsv` carries the raw inputs
  (`pre_fen`, `played_uci`, `played_line`, `best_line`, columns 42 to 45) and the probabilities, so the new
  material can be recomputed offline with no DB and no Maia. 13 labelled rows have a promotion token in those
  lines (the seed's "at least 13" is in fact exact for the committed lines); 8 of them change inputs.

Offline preview, this session (scratchpad `fit_preview.py`, the repo's `fit_logistic`, `cv_predictions`, `auc`,
`passer_table`; 268 usable rows in every variant):

| Inputs | Gate | Coefficients (intercept, played, loss, missed, best, reply) | CV AUC mean (5 seeds) | fair / unfair at 0.5, 0.6, 0.7 |
|---|---|---|---|---|
| current rule | `loss > 0` (shipped) | -1.4308, -0.6065, 0.8379, 0.4971, 2.0786, 0.9133 | 0.908 | 118/25, 109/18, 98/11 |
| current rule | type gate | -1.8026, -0.5985, 1.0898, 0.4213, 1.1590, 0.9248 | 0.896 | 114/23, 104/16, 94/10 |
| promotions | `loss > 0` (D-05 reference) | -1.3659, -0.6201, 0.6734, 0.4615, 2.1476, 0.8518 | 0.902 | 118/25, 109/21, 99/12 |
| promotions | type gate (the new model) | -1.7891, -0.6193, 0.8879, 0.3993, 1.1635, 0.8057 | 0.889 | 114/23, 106/17, 94/11 |

`[VERIFIED: offline run this session; the first row reproduces the shipped constants exactly, which validates the offline path]`

Read this as a preview, not the result: the plan's implementation must produce its own numbers. Three points
for the checkpoint: the new model is 0.019 below the shipped rule on the same lines (range 0.02); most of the
drop comes from the gate (-0.012), the rest from promotions (-0.006); the best-move coefficient roughly halves
(2.08 to 1.16) because the mixed rows now feed it. The changed label rows: 31 (fair, missed 0 to 5), 35 (fair,
loss 0 to 2.42), 57 (unfair, missed 0 to 0.13), 139 (unfair, loss 0.90 to 2.94, missed to 0), 170 (unfair),
177 (unfair, loss 0 to 3.87), 231 (fair), 266 (unfair, loss 0 to 1.13).

Recommended features path: an offline recompute that reads the 2026-11-22 table, keeps every probability, moves
its `loss` / `missed` (the Phase 259 rule) into `loss_shipped` / `missed_shipped`, and recomputes `loss` /
`missed` from the raw lines with the new rule. This isolates the rule change, needs no prod or Maia, and gives
the D-12 baseline ("the shipped rule on today's lines") directly. The `shipped_baseline` shape must then mean the
Phase 259 shape (reply probability on `loss > 0`) on the shipped pair, not the Phase 256 spread shape. A fresh
prod pull is possible but cannot produce the old-rule pair once `line_material.py` has changed.

D-05 old-gate line: a gate parameter on `design_row` / `missing_reason` (type gate default, `loss > 0` for the
reference), fitted on the same rows, reporting the CV AUC and the out-of-fold fair / unfair counts at 0.7.

### Finding 5: The pass

What `--mode line --cutoff` does today: selects every spread-stamped game whose `facepalm_line_completed_at` is
NULL or older than the cutoff, recomputes the line facts of every blunder of BOTH sides in the game (two
material scalars and both mate plies), writes them under per-game advisory locks with a fingerprint check, and
stamps the game `[VERIFIED: scripts/backfill_maia_flaws.py:21-32, 229-235, 267; app/services/maia_flaw_scoring.py:945-972, 1195-1266]`.
Its rows do not carry the stored material, so its dry run cannot report "would change".

Recommendation: a dedicated script (for example `scripts/backfill_promotion_material.py`), because D-07 is
row-scoped and asks for a would-change dry run plus a sample check, neither of which line mode has. Shape:

- Candidates (row-level, both sides, games already line-processed):

```sql
-- Source: game_flaws PK is (user_id, game_id, ply); game_positions PK is (user_id, game_id, ply).
SELECT f.user_id, f.game_id, f.ply, f.material_loss, f.material_missed
FROM game_flaws f
JOIN games g ON g.id = f.game_id
JOIN game_positions p0 ON p0.user_id = f.user_id AND p0.game_id = f.game_id AND p0.ply = f.ply
LEFT JOIN game_positions p1 ON p1.user_id = f.user_id AND p1.game_id = f.game_id AND p1.ply = f.ply + 1
WHERE f.severity = 2
  AND g.facepalm_line_completed_at IS NOT NULL
  AND (p1.pv ~ '(^| )[a-h][27][a-h][18][qrbn]( |$)'
       OR p0.pv ~ '(^| )[a-h][27][a-h][18][qrbn]( |$)'
       OR p0.best_move ~ '^[a-h][27][a-h][18][qrbn]$'
       OR p0.move_san LIKE '%=%')
```

  Stored formats `[VERIFIED: app/models/game_position.py:139-140, 163-171]`: `move_san` is the SAN of the move
  played FROM the position (`# SAN of the move played FROM this position (leading to ply+1)`), so the played
  blunder is `p0.move_san` and a promotion carries `=`; `best_move` is UCI, `# 4 chars normal (e.g. "e2e4") /
  5 chars promotion (e.g. "e7e8q").`; `pv` is space-joined UCI. Include rows whose stored loss is NULL: a short
  line that ends on a promotion can now settle (Finding 1). On dev this filter gives 799 rows (797 scored + 2
  stored-NULL), 624 change. The dev plan of the probe-style query (without `g` and stored values) is a parallel
  index-only scan of `ix_game_flaws_facepalm_inputs` plus two PK lookups per blunder, 213 ms for 58k blunders
  `[VERIFIED: EXPLAIN ANALYZE on dev]`; prod has about 4.4M blunders, so page it (keyset on the PK) or expect
  minutes.
- Replay with `replay_flaw_boards(pgn, plies)` and the `board.board_fen() == game_flaws.fen` guard (as line mode
  does), then `facepalm_material_inputs(board, played_uci, refutation_pv, best_pv or best_move)`.
- Compare in float32 (`struct.pack("f", x)` round trip, or a 1e-6 tolerance). Update only changed rows, guarded:
  `UPDATE game_flaws SET material_loss = :new_loss, material_missed = :new_missed WHERE user_id = :u AND
  game_id = :g AND ply = :p AND material_loss IS NOT DISTINCT FROM :old_loss AND material_missed IS NOT
  DISTINCT FROM :old_missed`. Bind the old values exactly as read (float4 to float8 is exact, so equality holds).
  A guard miss means the hook rewrote the row in between; count it and move on.
- Idempotent: a re-run recomputes the same values and finds 0 changes, so no stamp is needed.
- One connection (`pool_size=1, max_overflow=0`), batched transactions, `PYTHONUNBUFFERED=1`, `setsid nohup`,
  SIGTERM finishes the batch.
- Dry run: read-only engine (`scripts.blunder_check.sample.make_readonly_engine`, read-only and a statement
  timeout), reports candidates, would-change, loss up / down, missed up / down, NULL to value, type flips, board
  failures; plus the sample check: a seeded sample of non-token blunders replayed with the new code, mismatches
  vs stored in float32 (expected 0: on dev 0 of 20,381).
- Undo log: write `(user_id, game_id, ply, old_loss, old_missed, new_loss, new_missed)` per updated row to a
  gitignored file under `temp/` (memory: drafts go in `temp/<topic>/`; the log holds game ids). It turns the
  costly D-06 rollback into a replay-free UPDATE.
- Rough duration: dev replays about 1,300 rows per second in a single process (probe timing, 41 s for 21k rows
  with three variants), so 165k candidates are minutes of CPU; the candidate scan dominates
  `[ASSUMED: extrapolated from dev]`.

Theoretical gap in the token filter: with the SEE fix, a line that ends inside an exchange on the first or last
rank can gain a capture-promotion inside the SEE without any promotion token in the stored lines. On dev this
never happens (0 of 20,381 non-token rows change); the dry-run sample check is the prod guard.

### Finding 6: The covering index

Definition `[VERIFIED: app/models/game_flaw.py:38-51]`:

```python
        Index(
            "ix_game_flaws_facepalm_inputs",
            "user_id",
            "game_id",
            postgresql_include=[
                "ply",
                "maia_played_prob",
                "material_loss",
                "material_missed",
                "maia_best_prob",
                "maia_best_reply_prob",
            ],
            postgresql_where=text("severity = 2"),
        ),
```

The new gate reads `material_loss` and `material_missed`, both already in the INCLUDE list, so no migration and
no rebuild. EXPLAIN to run on prod before the release (precedent: `reports/blunder-check/facepalm-jit-259.md`):
compile `library_repository.fetch_facepalm_counts` and `fetch_facepalm_comparison` from the phase branch with the
PostgreSQL dialect and literal binds for user 95 (the largest account) with the default filters, then
`EXPLAIN (ANALYZE, BUFFERS)` on one read-only connection; pass when both read `game_flaws` through
`Index Only Scan using ix_game_flaws_facepalm_inputs`. The local helper `temp/facepalm-257/gen_shipped_sql.py` is
stale (it calls `fetch_facepalm_share_counts`, which no longer exists; verified this session), so the plan must
adapt it or build the selects again. After the pass, `Heap Fetches` rises until autovacuum marks the updated
pages all-visible; harmless.

### Finding 7: Phase 261 pieces that read score units

- `caught_rate.py` bins by the window snapshot (`blunder_check_windows.facepalm_score`), falls back to the live
  `facepalm_expr` for legacy windows, and filters `--since` on `ended_at` `[VERIFIED: scripts/blunder_check/caught_rate.py:327-361]`.
  The snapshot is taken when the session is composed; `blunder_check_sessions.started_at` has
  `server_default=func.now()` `[VERIFIED: app/models/blunder_check.py:129-131]`. Split on the session's
  `started_at` against a constant such as `FACEPALM_262_SWITCH_AT` (a timezone-aware datetime), not on
  `ended_at`: a session composed before the deploy and played after it carries old-version snapshots. The
  constant's value is the deploy time, so set it in the post-deploy plan (scripts are not deployed). Legacy
  windows use the live score and therefore switch version at the deploy; say so in the report.
- `HARD_TO_CATCH_SCORE_BELOW: float = 0.5` `[VERIFIED: app/services/blunder_check_rules.py:73]` is read only by
  `blunder_check_feedback.blunder_feedback` on the snapshot. A pre-release re-check is possible by re-scoring the
  snapshotted inputs of ended windows (`facepalm_played_prob`, `facepalm_loss`, `facepalm_missed`,
  `facepalm_best_prob`, `facepalm_reply_prob`) with the new model and gate and reading the caught rate by new
  band. The window counts are small so soon after Phase 261; treat it as indicative.
- `app/services/facepalm_zones.py`: docstring note only (D-08). `test_facepalm_zones.py` pins literal half-widths
  (`"facepalm": (0.53, 0.30, 0.30, 0.52)` etc.), unaffected `[VERIFIED: tests/services/test_facepalm_zones.py:23-27]`.
- The drill feedback type line (`blunder_check_feedback.type_line_facts`) walks the lines with the same
  functions, so after D-01 an allowed promotion shows "allows a material loss" (swing capped at 5). No code
  change; mention it in the changelog only if the owner wants.

## Architecture Patterns

### System Architecture Diagram

```
 import / eval drain ──► go-forward hook (score_game_flaws_after_apply)
                              │  replay board + stored lines (pv@ply+1, pv|best_move@ply)
                              ▼
                     line_material (quiet walk, _victim_value +promotion gain, SEE)
                              ▼
                     facepalm_inputs.facepalm_material_inputs ──► game_flaws.material_loss / material_missed (REAL)
                              ▲                                              │
  promotion pass (new script) ┘  (candidates by token filter,               │  query time
   dry run → would-change; real run → guarded UPDATE of changed rows)       ▼
                                                     facepalm_expr / facepalm_type_expr (SQL CASE,
                                                     shared allowed-loss condition, FACEPALM_* constants)
                                                                             │
                     ┌──────────────┬───────────────┬───────────────────────┼───────────────────┐
                     ▼              ▼               ▼                       ▼                   ▼
               library chip   stats / timeline   drill pool (main +    analysis "???"    caught_rate.py
               and filter     (index-only scan)  exploration arms,     badge             (snapshot score,
                                                 snapshot at compose)                     split by switch time)

 offline: facepalm-features-2026-11-22.tsv ──► recompute material with new rule ──► new features TSV
          ──► fit_facepalm.py (type gate; old-gate reference; shipped baseline) ──► report + constants block
          ──► owner checkpoint ──► paste into blunder_check_rules.py ──► --check-constants test
```

### Recommended file touch list

```
app/services/line_material.py        # _promotion_gain, _victim_value, _exchange_value gain, docstring rules
app/services/facepalm_score.py       # is_allowed_loss / _allowed_loss_sql, both twins, docstring
app/services/blunder_check_rules.py  # six FACEPALM_* constants, comment block (fit command, formula), cuts
app/services/facepalm_zones.py       # D-08 docstring note
scripts/blunder_check/fit_facepalm.py        # gate, old-gate reference line, shipped baseline = 259 shape
scripts/blunder_check/facepalm_features.py   # offline recompute mode (or a tiny sibling script); _has_null_score_input
scripts/blunder_check/caught_rate.py         # switch-time split
scripts/backfill_promotion_material.py       # new pass (name is a suggestion)
scripts/backfill_maia_flaws.py               # reply-status residue counters follow the shared condition
tests/...                                    # see Validation Architecture
reports/blunder-check/facepalm-features-<date>.tsv, facepalm-fit-<date>.md
docs/dev-tooling.md, CHANGELOG.md
```

### Pattern: one shared condition, two twins

```python
# Source: app/services/facepalm_score.py (current twins, extended)
def is_allowed_loss(loss: float, missed: float | None) -> bool:
    """257 D-02 / 262 D-04: the type rule and the key-move gate. A NULL missed reads as 0.0."""
    return loss > 0 and loss >= (0.0 if missed is None else missed)


def _allowed_loss_sql(columns: FacepalmColumns) -> ColumnElement[bool]:
    """SQL twin of `is_allowed_loss` (coalesce matches the Python NULL rule)."""
    return and_(columns.loss > 0, columns.loss >= func.coalesce(columns.missed, literal(0.0)))
```

### Anti-Patterns to Avoid
- **Monkeypatching `_victim_value`** (the probes do it): spike-only; the rule lives in the function.
- **Comparing stored REAL values to float64 at 1e-9:** produces about 12% phantom changes (Finding 2).
- **Re-defining `loss > 0` locally** in the fit or the status counters: import the shared condition.
- **Using `ended_at` for the score-version split:** the snapshot is taken at compose time.
- **Running the pass from an executor subagent:** backgrounded runs die with the agent; launch from the
  orchestrator (project memory).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Board before the blunder | own PGN loop | `replay_flaw_boards` (`app/services/maia_flaw_scoring.py`) | same guards as the line pass (unparseable PGN, invalid root) |
| Stored pair from lines | own walk / mean | `facepalm_material_inputs` | the single writer (259 D-05) |
| Read-only prod engine | ad hoc engine | `scripts.blunder_check.sample.make_readonly_engine` | one connection, read-only, statement timeout, URL never logged |
| DB URL | parsing `.env` | `app.core.config.db_url_for_target` | `.env` is hook-protected |
| Logistic fit, CV, AUC, passer table | new code | `fit_facepalm.fit_logistic`, `cv_predictions`, `auc`, `passer_table` | the preview reproduced the shipped constants exactly with these |
| Wilson intervals in the caught-rate split | own formula | `app.services.score_confidence.wilson_bounds` | project rule |

## Runtime State Inventory

The phase changes a write-time rule and rewrites stored values, so the inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | prod `game_flaws.material_loss` / `material_missed` on promotion-token blunders (about 165k candidates, about 127k real changes, estimate); dev DB the same rows (799 candidates, 624 changes) | data pass (new script), prod after deploy; rehearse on dev first |
| Stored data (kept) | `blunder_check_windows.facepalm_score` and the five snapshot inputs | none (261: served as served); split in `caught_rate.py` |
| Stored data (other DB) | benchmark DB material columns | none: deferred to SEED-261120-bzq |
| Live service config | none: the score is a query-time expression; no cache or materialized view holds it (grep of `app/` for facepalm readers) | none |
| OS-registered state | none | none |
| Secrets / env vars | none: the pass reads `DATABASE_URL_PROD` through `db_url_for_target` | none |
| Build artifacts | none (no migration, no generated frontend files; `FACEPALM_HIGH_CUTOFF` in `frontend/src/lib/facepalm.ts` only if the stats cut moves) | conditional frontend constant edit |

## Common Pitfalls

### Pitfall 1: SEE not promotion-aware
**What goes wrong:** a promotion made inside the static exchange is priced as a plain capture.
**Why:** `_exchange_value` has its own victim lookup.
**How to avoid:** `gain = _victim_value(board, capture)` in `_exchange_value`; test with the game 1461554 ply 63
best line or a constructed `a2xb1=q` recapture.

### Pitfall 2: float32 compare in the pass and its dry run
**What goes wrong:** about 12% phantom "changes", wrong dry-run numbers, needless writes.
**How to avoid:** compare after float32 rounding or with a 1e-6 tolerance; bind old values exactly as read in
the UPDATE guard.

### Pitfall 3: the CONTEXT cap example "queen is taken at once, 0, 0, 1, 1, 1, stored 0.23" is wrong
**What goes wrong:** pasting it as a unit-test expectation fails.
**Why:** under D-01 the opponent's promotion (+8) followed by the capture of the new queen (-9) nets -1 for the
blunderer (the opponent lost the pawn), clipped to 0 by `FACEPALM_LOSS_FLOOR = 0`: per-depth (0, 0, -1, -1, -1),
stored 0.0 (verified with a constructed position). The other examples (1.13, 5.00) reproduce.
**How to avoid:** build each fixture from a real position and line, as `test_line_material.py` does.

### Pitfall 4: a promotion is now non-quiet, also AFTER the depth
**What goes wrong:** surprise at depth values that include a promotion one ply past the depth.
**Why:** `_quiet_walk_end` consumes every following non-zero-victim step.
**How to avoid:** expected; document it in the module docstring next to "promotions are not material" (line 12,
which must be rewritten), and in the NULL rule (a short line ending on a promotion now settles every depth).

### Pitfall 5: desperado exclusion swallows a capture-promotion's gain
**What goes wrong:** an opponent capture-promotion onto the square the blunderer's last move reached quietly is
excluded as a whole, promotion gain included.
**Frequency:** 1 occurrence in the dev candidate lines (scratchpad `desperado.py`). D-01 keeps one number in
`_victim_value`; accept and document, or flag to the owner. Do not split `_Step` for this.

### Pitfall 6: synthetic fit test generated with the old gate
`tests/scripts/test_fit_facepalm.py::synthetic_rows` draws labels with `loss > 0`; with the new gate the
recovery test drifts. Change the generator with the fit.

### Pitfall 7: the AUC range check sits at the edge
The preview gives |0.889 - 0.908| = 0.019. A different but equally valid features path (fresh prod pull) could
cross 0.02. Present the number plainly at the checkpoint; D-01 says the range is a check, not a selector.

### Pitfall 8: stats cut couples to the frontend
`test_facepalm_stats_min_is_the_frontend_facepalm_cut` parses `FACEPALM_HIGH_CUTOFF = 70` from
`frontend/src/lib/facepalm.ts`. If the owner moves `FACEPALM_STATS_MIN`, the frontend constant (and its copy
strings, and `gapBar.test.ts`) move in the same commit, then `npm run build` and tests.

### Pitfall 9: prod operating rules
One operator connection (prod `max_connections` 50, app pool up to 20); no overlapping operator runs; the
02:15 UTC scheduled reboot kills the tunnel and long runs (the idempotent pass just restarts); launch with
`setsid nohup` and `PYTHONUNBUFFERED=1` from the orchestrator; prod SELECTs for the checkpoint (mixed rows
without `maia_best_prob`, newly passing rows) are run by the orchestrator, since subagents lack the prod MCP.

## Code Examples

### D-01 inside `_victim_value`, reused by the SEE

```python
# Source: app/services/line_material.py (proposed)
def _promotion_gain(move: chess.Move) -> int:
    """Promoted piece minus the pawn (262 D-01): queen 8, rook 4, bishop or knight 2, else 0."""
    if move.promotion is None:
        return 0
    return PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]


def _victim_value(board: chess.Board, move: chess.Move) -> int:
    """Material `move` wins on `board`: the captured piece plus the promotion gain (0 for a quiet move)."""
    if board.is_en_passant(move):
        return EN_PASSANT_VALUE
    piece = board.piece_at(move.to_square)
    captured = PIECE_VALUES[piece.piece_type] if piece else 0
    return captured + _promotion_gain(move)


def _exchange_value(board: chess.Board, capture: chess.Move) -> int:
    """Static exchange value of `capture` for the side making it (may be negative)."""
    gain = _victim_value(board, capture)  # 262: a capture-promotion inside the SEE gains its promotion too
    after = board.copy(stack=False)
    after.push(capture)
    return gain - _best_recapture(after, capture.to_square)
```

### float32 comparison for the pass

```python
import struct

def as_real(value: float | None) -> float | None:
    """The value PostgreSQL REAL stores for `value` (float4 round trip)."""
    return None if value is None else struct.unpack("f", struct.pack("f", value))[0]

changed = (as_real(new.loss), as_real(new.missed)) != (stored_loss, stored_missed)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Promotions are not material | Promotion credits promoted piece minus pawn | Phase 262 | about 3% of blunders change inputs; captured promoted queen no longer credited 9 |
| Key-move gate `loss > 0` | Gate = type rule `loss > 0 and loss >= missed` | Phase 262 | 1,728 dev mixed rows move to the best-move term; best-move coefficient roughly halves in the refit |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Real prod input changes are about 127k (dev ratio 624/710 applied to the probe's 144,810) | Finding 2, Inventory | Only the expectation of the dry run; the dry run measures the truth |
| A2 | The pass takes minutes of CPU plus the candidate scan (extrapolated from dev timing) | Finding 5 | Longer run; it is idempotent and restartable |
| A3 | Re-scoring the window snapshots gives a usable HARD_TO_CATCH re-check | Finding 7 | Too few windows; keep 0.5 and say so |
| A4 | The offline refit is acceptable to the owner as "re-measured on today's lines" (uses the 2026-11-22 lines) | Finding 4 | If the owner wants a fresh prod pull, the old-rule pair must be computed before `line_material.py` changes |
| A5 | Splitting caught-rate on session `started_at` matches when snapshots are composed | Finding 7 | A window snapshotted later than its session start would be misfiled; the model shows a single compose step |

## Open Questions

1. **Offline features vs fresh prod pull.** Recommendation: offline (isolates the rule, reproduces the shipped
   constants exactly). If a fresh pull is chosen, run it before the rule change for the old pair, then again.
2. **Desperado plus capture-promotion (1 dev occurrence).** Recommendation: accept, document in the docstring.
3. **Release-time constant for `caught_rate.py`.** Recommendation: commit it after the deploy with the real
   deploy timestamp (scripts run from the operator checkout).
4. **Spike probes.** Recommendation: delete them once the pass script and its dry run exist (they monkeypatch the
   rule and carry the float32 bug); the new script supersedes them.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | everything | ✓ | 0.10.9 | — |
| Python | backend, scripts | ✓ | 3.14.3 | — |
| Dev PostgreSQL (Docker `flawchess-dev-db-1`) | tests, dev rehearsal | ✓ (healthy) | 18 | — |
| `bin/prod_db_tunnel.sh` | EXPLAIN, dry run, pass, checkpoint SELECTs | ✓ (script present) | — | none (orchestrator opens it) |
| Maia (`--group maia-inference`) | only for a fresh features pull | not needed for the offline path | — | offline recompute |
| `bin/deploy.sh` / deploy skill | release | ✓ | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with xdist (repo pin) |
| Config file | `pyproject.toml` (`addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`) |
| Quick run command | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_inputs.py tests/services/test_facepalm_score.py tests/services/test_facepalm_owner_fixtures.py tests/services/test_facepalm_zones.py tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py tests/scripts/test_caught_rate.py -n 4 -x` (baseline 171 of these pass in about 13 s) |
| Full suite command | `uv run pytest -n auto -x` (plus the pre-merge gate in CLAUDE.md) |

### Decision to Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 | promotion gain per piece, capture + promotion, first-move promotion, walk through recapture, line ending on promotion settled by SEE, SEE capture-promotion; four fixture values updated | unit | `uv run pytest tests/services/test_line_material.py -x` | ✅ (extend) |
| D-01 | stored pair for the cap examples (5.0, 1.129, 0.0) via `facepalm_material_inputs` | unit | `uv run pytest tests/services/test_facepalm_inputs.py -x` | ✅ (extend) |
| D-02 | cap and floor constants unchanged | unit | `uv run pytest tests/services/test_facepalm_score.py -k "write_time_material_rule_is_pinned or known_d04" -x` | ✅ |
| D-03 | freshly promoted piece captured on its square counts (loss 1) | unit | `uv run pytest tests/services/test_line_material.py -k desperado -x` | ✅ (add case) |
| D-04 | shared condition; mixed row reads best term; NULL rules; SQL / Python parity incl. mixed stored row | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | ✅ (extend) |
| D-04 | fit design row and exclusions follow the gate; synthetic generator uses the type gate | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -x` | ✅ (extend) |
| D-05 | report contains the old-gate line (AUC, fair / unfair at 0.7) and the shipped-baseline range line | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k "old_gate or alternatives" -x` | ❌ Wave 0 (new test) |
| constants | `--check-constants` reproduces the pasted constants from the new features file | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k reproduce_from_the_committed_features -x` | ✅ (repoint) |
| D-06 / D-07 | token filter SQL (UCI and SAN), float32 compare, dry run writes nothing, real run updates only changed rows, re-run changes 0, guarded update skips a concurrent change, sample check | DB integration | `uv run pytest tests/scripts/test_backfill_promotion_material.py -x` | ❌ Wave 0 |
| D-07 | dev rehearsal: dry run reports 799 candidates / 624 would change; non-token sample mismatches 0 | operator smoke | `uv run python scripts/backfill_promotion_material.py --db dev --dry-run` | ❌ (script new) |
| D-08 | bands unchanged | unit | `uv run pytest tests/services/test_facepalm_zones.py -x` | ✅ (no change) |
| caught-rate split | rows split by session start vs switch constant | unit | `uv run pytest tests/scripts/test_caught_rate.py -x` | ✅ (extend) |
| index | index-only scan on prod | manual (prod EXPLAIN by the orchestrator) | see Finding 6 | manual-only (prod) |

### Sampling Rate
- **Per task commit:** the quick run command above (or the subset for the touched module).
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** the full CLAUDE.md pre-merge gate (ruff format, ruff check, ty on app/tests/scripts and
  analysis, nesting-depth gate, full pytest, frontend lint / build / test / knip) before the squash-merge.
  Memory: `-n auto` green is not serial-CI green; run the serial suite before the release.

### Wave 0 Gaps
- [ ] `tests/scripts/test_backfill_promotion_material.py` (or the chosen script name): seeded games with a
      promotion token in each of the three places, a non-token row, a stored-NULL row, a float32-only
      difference that must not count, a concurrent rewrite.
- [ ] Fit-report test for the D-05 old-gate line and the redefined shipped baseline.
- [ ] New features TSV under `reports/blunder-check/` (input of the `--check-constants` test).

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no (operator script, no endpoint) | — |
| V5 Input Validation | yes | stored UCI tokens are parsed with `_parse_move`, which never raises (T-250-01); SQL uses bound parameters only, the regex is a constant |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prod write pass corrupts rows | Tampering | dry run first, guarded UPDATE on the old pair, undo log, idempotent re-run |
| Prod overload | Denial of service | one connection, batched transactions, no overlap with other operator runs |
| Credential leak in logs | Information disclosure | `db_url_for_target`, URL never printed; undo log with game ids stays in gitignored `temp/` |

## Project Constraints (from CLAUDE.md)

- ty clean on `app/ tests/ scripts/`; explicit return types; `Sequence[...]` for covariant params; `# ty: ignore[rule]` only with a reason.
- No magic numbers: name the regex, the float tolerance, batch size, sample size, switch timestamp.
- Nesting depth <= 4 (`scripts/check_function_size.py app/ --fail-over-depth 4`); keep functions small.
- `Literal[...]` for fixed string sets (pass outcome labels, gate names in the fit).
- Sentry rules apply to `app/services/` (the pass script is a script; follow the existing backfill style).
- Never `asyncio.gather` on one `AsyncSession`.
- Comment bug fixes at the fix site (the SEE fix, the float32 compare).
- Changelog bullet under `## [Unreleased]`; release via PR `main → production` and `bin/deploy.sh` only.
- Never call eval "pawns" in copy or docs; em-dashes sparingly.
- No dev DB reset in plans; `.env` files are off limits.

## Sources

### Primary (HIGH confidence)
- Repo code read this session: `app/services/line_material.py`, `facepalm_score.py`, `facepalm_inputs.py`,
  `facepalm_material.py`, `blunder_check_rules.py`, `facepalm_zones.py`, `maia_flaw_scoring.py`,
  `blunder_check_feedback.py`, `app/models/game_flaw.py`, `game_position.py`, `blunder_check.py`,
  `scripts/blunder_check/fit_facepalm.py`, `facepalm_features.py`, `caught_rate.py`, `scripts/backfill_maia_flaws.py`,
  the tests listed above, the spike probes, the seed, ROADMAP Phase 262, CONTEXT.
- Dev DB measurements this session (read-only): both probes, float32 discrepancy, SEE variant, non-token sample,
  desperado edge count, mixed rows, candidate EXPLAIN.
- Offline refit preview on `reports/blunder-check/facepalm-features-2026-11-22.tsv`.

### Secondary / Tertiary
- None (no web sources needed).

## Metadata

**Confidence breakdown:**
- Material rule and SEE: HIGH (code read, real and constructed positions replayed)
- Gate and tests: HIGH (code read, compiled expression measured)
- Refit outcome: MEDIUM (preview, the plan's implementation produces the real numbers)
- Prod pass sizing and timing: MEDIUM / LOW (dev measurements extrapolated; the dry run settles it)

**Research date:** 2026-11-23
**Valid until:** 2026-12-07 (prod lines and labels move; re-run the dry run before trusting counts)
