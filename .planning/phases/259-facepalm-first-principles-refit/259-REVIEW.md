---
phase: 259-facepalm-first-principles-refit
reviewed: 2026-11-22T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - alembic/versions/20261122_120000_d1e5f7a9c259_phase_259_facepalm_scalars.py
  - alembic/versions/20261122_130000_d2a6c8e0f259_phase_259_facepalm_reply_stamp.py
  - alembic/versions/20261124_120000_e2f6a8b0d259_phase_259_ix_game_flaws_facepalm_inputs.py
  - alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py
  - app/models/game.py
  - app/models/game_flaw.py
  - app/repositories/game_flaws_repository.py
  - app/repositories/library_repository.py
  - app/services/blunder_check_rules.py
  - app/services/facepalm_inputs.py
  - app/services/facepalm_material.py
  - app/services/facepalm_score.py
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
  - scripts/build_facepalm_inputs_index.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
  necessity: 1
status: issues_found
---

# Phase 259: Code Review Report

**Reviewed:** 2026-11-22
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

I reviewed the 24 files against `diff_base` c3ab036e8, reading each changed file in full. I also traced the write path end to end: `quiet_line_facts` / `quiet_best_line_facts`, then `material_inputs_from_facts`, then `_facepalm_values` and the full / line / spread / reply row builders, then `bulk_update_flaw_maia_stats` and the stamps. On the read side I traced the Python and SQL score twins, the type twins and the covering index.

I found nothing that breaks running code or loses data. The runtime path is sound.

- **Write-time inputs satisfy the DB constraints.** The loss floor (0), the cap (5) and the mate value (5) keep `material_loss` and `material_missed` non-negative, so the `ck_game_flaws_material_*` CHECKs hold. The pair is NULL together by construction, because `material_inputs_from_facts` returns `(None, None)` or a float pair.
- **The score twins agree on the NULL rules.** The SQL twin's first CASE branch, the `weight != 0` guard and the zero-coefficient omission all match the Python twin.
- **Row key sets are uniform per mode.** Reply mode is the only mode that writes `maia_best_reply_prob` outside full mode. Line mode never emits it, so it cannot NULL out a stored value.
- **Stamps.** All five are cleared together by `clear_maia_flaws_completed`, and each mode sets only its own.
- **Migrations.** They are consistent with the ORM declarations, and the index SQL pinned by `build_sql()` matches `CREATE_SQL`.

The findings are all in offline operator tooling plus one piece of dead generality in app code. Two are real latent defects in scripts that still compute from the old depth-3 rule.

## Warnings

### WR-01: `miss_labels` selects rows by the decaying-mean type but buckets them by the depth-3 gain, so `missed_size_bucket` can raise

**File:** `scripts/blunder_check/miss_labels.py:505-536` (consumer at `:578-587`, `:634-637`)
**Issue:** After Phase 259, `build_candidate` classifies each blunder with `material_type_of(inputs.loss, inputs.missed)`. Both are the stored decaying means over depths 1/3/5/7/9, and a "misses" row is one with `missed >= MIN_MISSED_GAIN`. But `MissCandidate.missed` is still the depth-3-only `_missed_gain(played_3, best_3)`, which returns `None` when either depth-3 slot is unsettled, or a value that can be 0 or negative.

`_group_cells` then calls `missed_size_bucket(candidate.missed, candidate.best_mate_ply)` for every pure-miss candidate. That function raises `ValueError` in two cases:
- `missed is None`, reached whenever the best-line mate ply is not within `LINE_DEPTH` and the depth-3 slot is None.
- `missed < 1` (smallest bucket `(1, 2)`), reached when the decaying mean is at least 1 but the depth-3 gain is 0. Example: the gain only appears at depth 5 or later, or the mate sits at ply 4-5.

The old rule used depth 3 for both the type and the bucket, so the two agreed. Under the new type rule a pure-miss candidate whose gain lands only at later depths crashes the whole sampler run. The same mismatch feeds `_key_entry` (`"missed": candidate.missed`), which records a number that is not the one that classified the row.

**Fix:** Make the candidate carry the stored scalar and bucket on it:
```python
# in build_candidate
missed_value = 0.0 if inputs.missed is None else inputs.missed
...
return MissCandidate(..., missed=missed_value, ...)

# missed_size_bucket takes a float and rounds down to the bucket grid
def missed_size_bucket(missed: float, best_mate_ply: int | None) -> int:
    if best_mate_ply is not None and best_mate_ply <= LINE_DEPTH:
        return len(MISSED_SIZE_BUCKETS) - 1
    for index, (low, high) in enumerate(MISSED_SIZE_BUCKETS):
        if missed >= low and (high is None or missed < high + 1):
            return index
    raise ValueError("missed gain below the smallest bucket")
```
Or keep the int grid and clamp the decaying mean with `max(MIN_MISSED_GAIN, round(missed))`. Either way the bucket must read the same number that made the row a "miss".

### WR-02: `facepalm_features` summary line counts "NULL score inputs" by the retired rule

**File:** `scripts/blunder_check/facepalm_features.py:624-628` (used by `summary_line` at `:642`)
**Issue:** `_has_null_score_input` still tests `row.reply_spread is None` and `loss_feature(row.facts.loss_at(3), row.facts.mate_ply, loss_floor=None) is None`. That is the Phase 254-258 input set (reply spread, depth-3 loss). The Phase 259 score reads `loss` (decaying mean), `reply_prob` when `loss > 0`, and `best_prob` otherwise. The spread is no longer an input.

Two consequences:
- A scorable row whose spread is missing is counted as having a NULL score input.
- A losing row whose `reply_prob` is missing, which the score treats as unscored (the `REASON_NO_REPLY_PROB` exclusion in `fit_facepalm`), is not counted.

The number printed at the end of the features pull, which the operator uses as the readiness check before a fit, is therefore wrong in both directions. This is also the only remaining production use of `loss_feature` outside tests.

**Fix:** Test the stored inputs the score reads:
```python
def _has_null_score_input(row: FeatureRow) -> bool:
    loss = row.quiet.loss
    if row.played_prob is None or loss is None:
        return True
    return row.reply_prob is None if loss > 0 else row.best_prob is None
```
This also drops the `loss_feature` import.

### WR-03: Generality without instantiation, three material inputs and two aggregate paths behind a constant that is never anything but `decaying_mean`

**File:** `app/services/facepalm_score.py:200-267` (`material_loss`, `material_missed`, `loss_feature`, `missed_feature`), `app/services/facepalm_material.py:46-168` (`first_stable`, `aggregate`, `AggregateInput`), `app/services/blunder_check_rules.py:109` (`MaterialInput`)
**Category:** necessity
**Issue:** The `material_input` parameter, the `"depth_3"` and `"first_stable"` branches, `first_stable`, `aggregate` and `AggregateInput` serve alternatives that the production write path can no longer reach. The only caller of `material_loss` / `material_missed` in `app/` or `scripts/` is `facepalm_inputs.material_inputs_from_facts` (grep `material_input=` returns only those two call sites). It passes `STORED_MATERIAL_INPUT: Final = "decaying_mean"`, and `tests/services/test_facepalm_score.py:621` pins that constant. `rg 'first_stable|aggregate\('` over `app/` and `scripts/` finds no other caller.

The fit no longer chooses an input: the fit docstring says the shape is fixed by first principles, and the stored scalar is the decaying mean (259 D-03). The only live references to the other branches are tests and the one stale use in WR-02.

The per-depth loop is also where the stored-value rule lives, so keeping three variants spreads the single rule over `facepalm_inputs`, `facepalm_score` and `facepalm_material`.

**Fix:** Collapse to the one stored rule. `material_loss` and `material_missed` take no `material_input`, call `decaying_mean(loss_by_depth(...))` and `decaying_mean(gain_by_depth(...))` directly, and `first_stable`, `aggregate`, `AggregateInput`, `loss_feature`, `missed_feature` and `MaterialInput` are deleted together with their tests. If the owner wants to keep the alternatives as a documented research option, move them out of `app/` into `scripts/blunder_check/`.

## Info

### IN-01: Stale docstrings still describe the dropped 9-slot Postgres arrays

**File:** `app/services/facepalm_material.py:1-14`, `app/services/line_material.py:20-24, 47-52, 118-125`
**Issue:** After `f3a7b9c1e259` the arrays no longer exist, but:
- `facepalm_material.py` says the writer "reads the odd depths ... of both stored 9-slot arrays" and that "query time never touches the arrays".
- `line_material.py` says "Stored arrays are 1-based in Postgres (`array[3]` = depth 3)" and "the score reads the depth-3 slot of the signed arrays".

The arrays are now only an in-memory list from `LineFacts.material_array()`, and the score reads the stored scalars. A reader following the comments goes looking for a column that is gone.
**Fix:** Reword to "the 9-slot signed list built by `LineFacts.material_array()` (an in-memory shape, no longer stored)" and drop the Postgres 1-based remark. `LINE_LOSS_DEPTHS`'s comment about "the score reads the depth-3 slot" should say that only `LINE_DEPTH` gates the mate and None shortcuts.

### IN-02: `CACHE_VERSION` comment and value disagree

**File:** `scripts/blunder_check/sample.py:82-86`
**Issue:** The comment block documents "Version 5 (Phase 259, D-15)" but the constant is `6`. There is no comment for 6; `tests/scripts/test_blunder_check_calibration.py:1143` says "CACHE_VERSION 6: the cache holds no 9-slot array", so 6 is the intended value. The next person bumping the version cannot tell what 6 changed.
**Fix:** Add a "Version 6 (Phase 259): the two 9-slot material arrays are dropped from the records; a version 5 cache still carries them and no longer loads." line above the constant.

---

_Reviewed: 2026-11-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
