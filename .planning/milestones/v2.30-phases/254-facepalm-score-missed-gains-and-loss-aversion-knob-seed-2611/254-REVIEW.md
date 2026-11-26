---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
reviewed: 2026-11-16T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py
  - alembic/versions/20261116_120000_c9f4e1a3d254_phase_254_drop_stored_score.py
  - app/models/game.py
  - app/models/game_flaw.py
  - app/repositories/blunder_check_repository.py
  - app/repositories/game_flaws_repository.py
  - app/repositories/library_repository.py
  - app/schemas/library.py
  - app/services/blunder_check_rules.py
  - app/services/facepalm_score.py
  - app/services/library_service.py
  - app/services/line_material.py
  - app/services/maia_flaw_scoring.py
  - app/services/maia_flaw_stats.py
  - scripts/backfill_maia_flaws.py
  - scripts/blunder_check/facepalm_features.py
  - scripts/blunder_check/fit_facepalm.py
  - scripts/blunder_check/metrics.py
  - scripts/blunder_check/miss_labels.py
  - scripts/blunder_check/render.py
  - scripts/blunder_check/sample.py
  - scripts/blunder_check/spot_check.py
  - tests/facepalm_seed.py
  - tests/facepalm_models.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 254: Code Review Report

**Reviewed:** 2026-11-16
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Scope was the Phase 254 diff (`adbdf856a~1..main`) of the listed files. No blocker was found.

What was verified rather than read:

- **SQL/Python twin parity.** I built the SQL twin (`facepalm_score_sql`) over a TEMP table with REAL/SMALLINT/SMALLINT[] columns on the dev database and compared it to `facepalm_score` on 55,800 random cases: 36 model shapes (material form x spread form x missed floor x optional coefficients, including the shipped shape) x lambda {0, 0.5, 1} x 600 rows with NULL played prob / spread / best prob / pre spread, NULL arrays, NULL slots inside arrays, mate plies 0-5. Zero mismatches (tolerance 1e-6, Python inputs rounded to float4 as the REAL columns do). The compiled asyncpg SQL binds every constant as `::FLOAT`, so the comparison precision claim in `_facepalm_clause` holds. NULL handling is sound: `LEAST`/`GREATEST` never see a NULL because the loss and missed terms use explicit CASE guards, and a NULL loss still NULLs `z` even when the gated spread CASE falls through to its ELSE branch.
- `tests/services/test_facepalm_score.py` passes (104 tests). `ruff check`, `ruff format --check`, `ty check scripts/blunder_check`, `check_function_size.py app/` and `alembic check` are all clean; the alembic chain has a single head (`c9f4e1a3d254`) and the model metadata matches the migrations.
- No remaining reader of the dropped columns (`facepalm_score`, `line_loss_*`) exists in `app/`, `scripts/` or `bin/`.
- Row/column index mapping in `sample._flaw_row` against `_load_flaws`, the `FACEPALM_COLUMNS` / `FacepalmStats` / `LINE_ROW_COLUMNS` key sets, the best-line ply convention (best move = ply 0, `opponent_mate_ply` counts from 1 over the remaining tokens, mate-in-2 = 2) and the spread/line/pre write modes under the per-game advisory lock + fingerprint re-read were traced and are consistent.

Necessity (#4100) was not assessed in this pass and no `necessity:` count is emitted.

## Warnings

### WR-01: An unknown best-move probability scores as the most-findable best move, inflating pure-miss scores

**File:** `app/services/facepalm_score.py:237` (Python) and `app/services/facepalm_score.py:333` (SQL twin)
**Issue:** `_best_prob_term` / `_best_prob_sql` return 0.0 when `maia_best_prob` is NULL. The shipped model uses `spread_form="best_prob_for_misses"` with `FACEPALM_BEST_PROB_COEF = +1.0405`, so on every row with `loss <= 0` the best-prob term is `1.0405 * ln(best_prob + 0.01)`, which is always <= ~0.01. NULL therefore maps to the maximum possible value of the term, i.e. "the best move was trivially easy to find", the most facepalm-like reading. Checked with the shipped constants: a no-loss blunder with a rarely played move (`p = 0.01`) and best_prob NULL scores z = -0.7583 - 0.4146 * ln(0.02) = 0.86, score ~0.70, above `FACEPALM_SCORE_MIN` (0.5). The same row with a known, hard-to-find best move (`best_prob = 0.05`) scores ~0.11. D-18 documents "unknown contributes nothing" for the missed material term (where 0 is a neutral value) but for this term 0 is the extreme, not the neutral value. NULL arises whenever the best move is absent from `pv@ply` and `best_move`, or is not in Maia's policy (`best_move_missing` reason), and those rows stay scored and can be drawn by the drill and shown in the library.
**Fix:** Either leave such rows unscored in both twins (a NULL `best_prob` on a `loss <= 0` row under `best_prob_for_misses` returns None / NULL, as a NULL spread already does under `always`), or substitute a neutral value (for example the pool median of `ln(best_prob + offset)`, as a named constant) in both twins. If the current behaviour is intended, record it in the `facepalm_score.py` module docstring so it is a decision and not an accident. SQL sketch of the first option inside `_spread_sql`:
```python
pure_miss = case(
    (columns.best_prob.is_(None), null()),
    else_=model.best_prob_coef * func.ln(columns.best_prob + PLAYED_PROB_OFFSET),
)
```
and in `_spread_term` return `None` when `facts.best_prob is None` for that form.

### WR-02: Destructive migration takes ACCESS EXCLUSIVE on the 7.6M-row `game_flaws` table with no lock timeout and no protection for the old-code window

**File:** `alembic/versions/20261116_120000_c9f4e1a3d254_phase_254_drop_stored_score.py:49-56` (also `alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py:69-90`)
**Issue:** `upgrade()` issues six separate `DROP COLUMN` statements in one transaction. The first acquires ACCESS EXCLUSIVE on `game_flaws` and holds it until commit; there is no `SET LOCAL lock_timeout`. If any long query or open transaction touches `game_flaws` (the module docstring itself names the Maia backfill, calibration and feature builder; also a Sentry-visible slow library query, an analytics session, an idle-in-transaction pool connection), the migration queues behind it and every later reader and writer of `game_flaws` queues behind the migration, stalling the app at startup, because migrations run at backend startup. The "no operator script may be running" deploy rule is a human precondition, not enforced anywhere. Additionally, after the drop commits any still-running old-model process that selects `GameFlaw` (the ORM selects every mapped column) fails with "column does not exist"; the docstring covers operator scripts but not an overlapping old backend container.
**Fix:** Bound the wait so a blocked migration fails fast instead of freezing the table, and collapse the statements:
```python
def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "ALTER TABLE game_flaws DROP COLUMN facepalm_score, DROP COLUMN line_loss_9, "
        "DROP COLUMN line_loss_7, DROP COLUMN line_loss_5, DROP COLUMN line_loss_3, "
        "DROP COLUMN line_loss_1"
    )
```
Apply the same `lock_timeout` to the R1 migration (`ADD COLUMN` x5, `ADD CONSTRAINT ... NOT VALID` x2 on `game_flaws`).

### WR-03: The fit excludes rows the shipped model would score, so the fitted population differs from the scored population

**File:** `scripts/blunder_check/fit_facepalm.py:324-327`
**Issue:** `_exclusion_reason` drops every row with `reply_spread is None` (`REASON_NO_SPREAD`) regardless of the spread form being fitted. Under `loss_only` and `best_prob_for_misses` the spread term is not read on rows with `loss <= 0` (both twins score them), and `spec_row_values` itself guards with `gated_off` but still calls `_require(row.reply_spread)` on line 581 before that guard, so a NULL-spread pure miss raises `FitError("design matrix needs usable rows only")` if it were not pre-filtered. The effect today is a silent selection bias: pure-miss and no-loss rows whose post-blunder policy was unavailable are excluded from the miss-heavy part of the fit (the exact population that stage 2 / D-07 is choosing a spread form for), while production scores them. The same file is the source of the shipped constants (`--check-constants`), so the bias is baked into `FACEPALM_BEST_PROB_COEF` / `FACEPALM_MISSED_COEF`.
**Fix:** Make the exclusion spread-form aware: keep a NULL-spread row when the candidate's spread form is gated and the row's loss is <= 0, and read the spread lazily in `spec_row_values`:
```python
spread = row.reply_spread
gated_off = spec.spread_form != "always" and loss <= 0
if spread is None and not gated_off:
    raise FitError("design matrix needs usable rows only")
values = [1.0, math.log(...), 0.0 if gated_off else spread]
```
Report the number of rows that only qualify under a gated form in `_data_section`.

## Info

### IN-01: Stale comments describing the removed stored score / pre-254 state

**File:** `app/models/game.py:283`, `scripts/blunder_check/facepalm_features.py:151-154`, `scripts/backfill_maia_flaws.py:277-278`
**Issue:** `game.py` still says the line stamp marks the pass that writes "line losses, mate ply, facepalm_score"; none of the `line_loss_*` / `facepalm_score` columns exist any more (it now writes the two material arrays, both mate plies). `facepalm_features._pre_inputs` says "Plan 254-16 adds `pre_blunder_spread` ... until then the app's `reply_spread` is the one implementation", but `pre_blunder_spread` exists in `maia_flaw_stats.py` and the sibling `miss_labels.py` already uses it, so the two scripts use different functions for the same input. `ShardReport` says the score counters cover "every mode that writes the score"; nothing writes a score any more, the counters are in-memory counts.
**Fix:** Update the three comments. In `facepalm_features._pre_inputs` call `pre_blunder_spread(policy)` (imported from `app.services.maia_flaw_stats`) so the feature builder follows the same named function the hook and the miss sampler use.

### IN-02: The two shape CHECK constraints are left NOT VALID for good

**File:** `alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py:78-89`, `app/models/game_flaw.py:37-48`
**Issue:** The constraints are added `NOT VALID` and never validated. Every row existing at migration time had NULL in both columns, so validation would succeed, but until `VALIDATE CONSTRAINT` runs the planner cannot use the constraints and `pg_constraint.convalidated` stays false (a later `pg_dump`/restore or tool that checks it will treat them as unproven). Enforcement on new writes works as intended; this is only a loose end.
**Fix:** Add a follow-up migration (or one-off operator statement) `ALTER TABLE game_flaws VALIDATE CONSTRAINT ck_game_flaws_played_line_material_shape` and the same for `best_line_material`; it takes only SHARE UPDATE EXCLUSIVE and does not block writes.

### IN-03: `_loss_at_depth` now settles on an opponent mate for the played line too, which contradicts the "pre-refit model reproduces Phase 250 exactly" claim in rare cases

**File:** `app/services/line_material.py:231-239`
**Issue:** The 254 change `mated = any(step.blunderer_mated or step.opponent_mated ...)` is shared by the played line and the best line (needed for the best line, D-09). For the played line, a blunder whose stored refutation line ends with the blunderer mating the opponent within three plies used to yield `None` ("too short to tell", row unscored) and now yields a loss value, so such rows become scored. The module docstring and `FacepalmModel` ("its pre-refit values reproduce the Phase 250 score exactly, D-12") do not carve this out. The population is tiny (a stored "refutation" that mates the blunderer's own opponent is an engine/line anomaly), so this is documentation precision, not a ranking risk.
**Fix:** Either note the exception beside the D-12 statement in `facepalm_score.py` / `line_material.py`, or keep the played-line behaviour by passing a flag into `_loss_at_depth` (`settle_on_opponent_mate=True` only from `best_line_facts`).

---

_Reviewed: 2026-11-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
