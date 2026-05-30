---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
reviewed: 2026-05-31T12:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - app/services/canonical_slice_sql.py
  - app/services/user_benchmark_percentiles_service.py
  - app/services/endgame_service.py
  - app/schemas/endgames.py
  - app/models/user_benchmark_percentile.py
  - scripts/gen_global_percentile_cdf.py
  - frontend/src/components/charts/EndgameMetricsByTcCard.tsx
  - frontend/src/types/endgames.ts
  - alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py
  - alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py
  - tests/services/test_canonical_slice_sql.py
  - tests/services/test_endgame_service.py
  - tests/services/test_user_benchmark_percentiles_service.py
  - tests/models/test_user_benchmark_percentile.py
  - tests/integration/test_benchmark_metric_enum.py
  - frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 99: Code Review Report

**Reviewed:** 2026-05-31T12:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 99 adds three raw-rate percentile chip families (conversion, parity, recovery) to the per-TC endgame metric cards. The implementation correctly follows the established pooled-per-user builder pattern, wires new ENUM values through two sequential migrations, generates CDF data, and renders title-line `PercentileChip` instances in the frontend.

The SQL builders are structurally sound: `user_id` is projected in `per_user_values` (Pitfall 1 mitigated), the HAVING floor uses the named constant `MINIMUM_RATE_BUCKET_SPANS`, source-mode parity holds (`_ = source`), and the formulas match the spec (conv = wins/spans; parity = (wins + 0.5 * draws)/spans; recovery = (wins + draws)/spans). The D-01 coexistence constraint (two chips per block without colliding) is correctly implemented.

Two Warnings were found: stale metric-family counts in docstrings that overstate the old count even after Phase 99 extended the tuple. Four Info items cover a numerical error in a model comment, a stale integration test function name, and two redundant NULL-guard filters.

No Critical findings.

---

## Warnings

### WR-01: `compute_stage_b` docstring says "7 eval-dependent metric families" after Phase 99 extended to 10

**File:** `app/services/user_benchmark_percentiles_service.py:467`

**Issue:** The `compute_stage_b` function docstring reads:

```
Compute the 7 eval-dependent metric families × user's above-floor TCs.
```

After Phase 99 appended `conversion_rate`, `parity_rate`, and `recovery_rate` to `STAGE_B_METRIC_FAMILIES`, the tuple is now 10 entries. The count "7" is incorrect. A reader who trusts the docstring for the contract (e.g. when reasoning about Stage B cost or coverage) gets the wrong answer.

The same stale count appears in the module-level docstring at line 10:

```
Stage B now iterates ``STAGE_B_METRIC_FAMILIES`` (7-tuple) × the user's above-floor TCs
```

**Fix:** Update both docstrings:

```python
# app/services/user_benchmark_percentiles_service.py line 10 (module docstring)
# Change:
#   Stage B now iterates ``STAGE_B_METRIC_FAMILIES`` (7-tuple) × the user's above-floor TCs
# To:
#   Stage B now iterates ``STAGE_B_METRIC_FAMILIES`` (10-tuple) × the user's above-floor TCs

# Line 467 (function docstring)
# Change:
#   """Compute the 7 eval-dependent metric families × user's above-floor TCs.
# To:
#   """Compute the 10 eval-dependent metric families × user's above-floor TCs.
```

---

### WR-02: `per_user_cte_recovery_rate_tc` bucket classification structure diverges from the two sibling builders without explanation

**File:** `app/services/canonical_slice_sql.py:1029-1039`

**Issue:** The `per_user_cte_parity_rate_tc` builder (line 950-966) uses the canonical nested CASE structure identical to `per_user_cte_score_gap_bucket_tc`:

```sql
CASE
  WHEN s.entry_eval_mate IS NOT NULL THEN
    CASE WHEN (mate*sign) > 0 THEN 'conversion' ELSE 'recovery' END
  WHEN s.entry_eval_cp IS NOT NULL THEN
    CASE WHEN ... >= 100 THEN 'conversion'
         WHEN ... <= -100 THEN 'recovery'
         ELSE 'parity' END
  ELSE 'parity'
END
```

The `per_user_cte_recovery_rate_tc` builder (line 1029-1040) uses a structurally different flat CASE:

```sql
CASE
  WHEN (mate IS NOT NULL AND mate*sign > 0) OR (cp IS NOT NULL AND cp*sign >= 100)
  THEN 'conversion'
  WHEN mate IS NOT NULL
    OR (cp IS NOT NULL AND cp*sign <= -100)
  THEN 'recovery'
  ELSE 'parity'
END
```

The two are logically equivalent (as traced in this review), but the structural difference is a trap for future maintainers: the recovery builder's second WHEN clause (`WHEN s.entry_eval_mate IS NOT NULL`) looks redundant or wrong at first glance — it is only correct because WHEN 1 already consumed the `mate IS NOT NULL AND positive` case, leaving only `mate IS NOT NULL AND not-positive` for WHEN 2. This is not documented and will mislead any engineer who edits it.

A further concern: the recovery builder's WHEN 2 condition `WHEN s.entry_eval_mate IS NOT NULL OR (...)` — the `OR` logic means that a row with non-null mate AND eval_cp <= -100 goes to recovery via the mate branch (not both branches together), which is correct but obscure. The parity builder's nested form makes the precedence visible.

**Fix:** Rewrite `per_user_cte_recovery_rate_tc`'s `bucket_rows` CASE to match the nested form used by `per_user_cte_parity_rate_tc` and `per_user_cte_score_gap_bucket_tc`. This eliminates the implicit-precedence reliance and makes future edits safe:

```sql
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN s.entry_eval_mate IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion'
          ELSE 'recovery'
        END
      WHEN s.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100
          THEN 'conversion'
          WHEN (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100
          THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'
    END AS bucket,
    ...
```

The logical output is identical to the current code; only the structural form changes. This also unblocks the source-parity tests from running against a misleadingly different CASE tree.

---

## Info

### IN-01: `user_benchmark_percentile.py` module docstring has "11 new values" where 3 × 4 = 12

**File:** `app/models/user_benchmark_percentile.py:12`

**Issue:** Line 12 reads:

```
Phase 99 extends the ENUM with 11 new values (3 rate-metric families × 4 TCs),
```

But 3 × 4 = 12. The first migration (`3981239fd391`) adds exactly 12 TC-suffixed values. The number "11" is a transcription error. The surrounding context ("11 metric families" on line 13) is correct (8 Phase-94.4 families + 3 Phase-99 families = 11 families), which likely caused the confusion.

**Fix:**

```python
# Line 12: change "11 new values" to "12 new values"
Phase 99 extends the ENUM with 12 new values (3 rate-metric families × 4 TCs),
```

---

### IN-02: Integration test function name `test_benchmark_metric_enum_has_exactly_four_labels` is stale — asserts 23 labels

**File:** `tests/integration/test_benchmark_metric_enum.py:114`

**Issue:** The function is named `test_benchmark_metric_enum_has_exactly_four_labels` (preserved from Phase 94.1 when the ENUM had 4 values). The docstring correctly says "exactly 23 expected labels" and the assertion is correct, but the function name contradicts the actual test purpose. Anyone running pytest with `-k four_labels` gets a false sense of what passes, and the name makes the test suite misleading in CI reports.

**Fix:** Rename the test function to reflect its current assertion:

```python
async def test_benchmark_metric_enum_has_exactly_expected_labels(
    test_engine: AsyncEngine,
) -> None:
```

The test body and EXPECTED_ENUM_LABELS constant require no change.

---

### IN-03: Redundant `WHERE wins IS NOT NULL` guard in all three rate builders

**File:** `app/services/canonical_slice_sql.py:913` (conv), `app/services/canonical_slice_sql.py:991` (parity), `app/services/canonical_slice_sql.py:1065` (recovery)

**Issue:** Each `per_user_values` CTE filters `WHERE conv_wins IS NOT NULL` (or `parity_wins`, `recov_wins`). In PostgreSQL, `sum(integer_expression) FILTER (WHERE condition)` returns NULL only when the filter matches zero rows. The preceding HAVING clause (`HAVING count(*) FILTER (...) >= 30`) guarantees at least 30 rows in the relevant bucket, so the aggregate can never be NULL at this point. The guard is unreachable dead code.

The same redundant pattern exists in the existing `per_user_cte_achievable_tc` builder (`WHERE achievable_gap IS NOT NULL`), where it is defensively correct because `avg()` can return NULL on an empty set. For the new rate builders, however, the HAVING gate makes the filter logically impossible to trigger.

This does not produce incorrect results but misleads readers into thinking a NULL escape path exists.

**Fix:** Remove the guards from the three new builders:

```sql
-- per_user_values for conv rate
per_user_values AS (
  SELECT user_id,
    conv_wins / NULLIF(conv_n, 0) AS metric_value,
    conv_n::int AS n_games
  FROM per_user
  -- WHERE conv_wins IS NOT NULL  ← remove: impossible after HAVING count >= 30
)
```

Apply the same removal to the parity and recovery `per_user_values` blocks. The NULLIF already guards against the only remaining NULL source (division by zero when `conv_n = 0`, which is itself impossible after HAVING, but NULLIF is a belt-and-suspenders guard worth keeping).

---

### IN-04: `compute_stage_b` docstring comment about Stage B families is stale in the module docstring

**File:** `app/services/user_benchmark_percentiles_service.py:9-10`

**Issue:** The module-level docstring at lines 9-10 reads:

```
The old flat 12-name TC-suffixed Stage B metric tuple retires; Stage B now iterates
``STAGE_B_METRIC_FAMILIES`` (7-tuple) × the user's above-floor TCs
```

After Phase 99's extension, `STAGE_B_METRIC_FAMILIES` is a 10-tuple. The "(7-tuple)" parenthetical is stale. (This is a separate occurrence from WR-01, which covers the `compute_stage_b` function docstring at line 467. Both need fixing.)

**Fix:**

```python
# Change "(7-tuple)" to "(10-tuple)" at line 10
Stage B now iterates ``STAGE_B_METRIC_FAMILIES`` (10-tuple) × the user's above-floor TCs
```

Note: WR-01 already covers the `compute_stage_b` function docstring. This IN-04 covers the module-level docstring occurrence. Both should be fixed together.

---

_Reviewed: 2026-05-31T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
