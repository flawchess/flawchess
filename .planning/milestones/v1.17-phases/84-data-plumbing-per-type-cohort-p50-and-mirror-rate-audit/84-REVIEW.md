---
phase: 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit
reviewed: 2026-05-13T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service_series.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 84: Code Review Report

**Reviewed:** 2026-05-13
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 84 extends `ConversionRecoveryStats` with four opponent-baseline fields (`opponent_conversion_pct`, `opponent_conversion_games`, `opponent_recovery_pct`, `opponent_recovery_games`) computed via same-game mirror identity. Tests cover the symmetric / below-threshold / at-threshold / zero-sample cases and a schema-shape guard. Other tests in `test_insights_llm.py` and `test_insights_service_series.py` were updated to supply the new required fields.

The core mirror-identity math is correct:
- `opponent_conversion_pct = recovery_losses / recovery_games * 100` — when the user is in the recovery bucket the opponent simultaneously entered the conversion bucket; the opponent wins iff the user loses.
- `opponent_recovery_pct = (conversion_losses + conversion_draws) / conversion_games * 100` — when the user is in the conversion bucket the opponent simultaneously entered the recovery bucket; the opponent "saves" iff the user does not win.

Both percentages are gated on the MIRROR bucket size against `_MIN_OPPONENT_SAMPLE` (10), which correctly reflects that the opponent's sample size IS the mirror bucket. No divide-by-zero risk — the gate guards the only division.

No critical bugs found. Two warning-level findings relate to test-helper inconsistencies and a schema drift with the frontend type mirror. Three info items cover comment/docstring inaccuracies introduced in the new block.

## Warnings

### WR-01: Test helper `_conv()` produces inconsistent `recovery_saves` vs `recovery_wins + recovery_draws`

**File:** `tests/services/test_insights_llm.py:1057-1085`
**Issue:** The Phase 84 edit reshaped the local `_conv()` helper to derive `conv_losses`, `recov_wins`, `recov_draws`, `recov_losses` from `int(...)` truncations, then computes mirror identities on those values. But it keeps the pre-existing `recovery_saves=int(n_recov * recov_pct / 100)`, which is *not* recomputed as `recov_wins + recov_draws`. With `n_recov=20, recov_pct=30`:
- `recov_wins = int(20 * 0.3 * 0.6) = int(3.6) = 3`
- `recov_draws = int(20 * 0.3 * 0.4) = int(2.4) = 2`
- `recovery_saves = int(20 * 0.3) = 6`, but `recov_wins + recov_draws = 5`

That breaks the documented invariant on `ConversionRecoveryStats` (`recovery_saves = recovery_wins + recovery_draws`, kept "for backward compat" per schema comment line 47). Any consumer that double-checks this invariant in a future test will fail spuriously. Phase 84 didn't introduce the underlying off-by-one, but it touched these same lines and is the natural place to fix it.
**Fix:**
```python
recov_wins = int(n_recov * recov_pct / 100 * 0.6)
recov_draws = int(n_recov * recov_pct / 100 * 0.4)
recov_losses = n_recov - recov_wins - recov_draws
# ...
recovery_saves=recov_wins + recov_draws,  # honor the documented invariant
```

### WR-02: Frontend `ConversionRecoveryStats` TS interface diverges from the new backend schema

**File:** `frontend/src/types/endgames.ts:9-20` (consumer of the modified `app/schemas/endgames.py`)
**Issue:** The backend `ConversionRecoveryStats` Pydantic model now ships four additional fields (`opponent_conversion_pct`, `opponent_conversion_games`, `opponent_recovery_pct`, `opponent_recovery_games`) on `/api/endgames/overview` and `/api/endgames/stats`. The TS mirror in `frontend/src/types/endgames.ts` does NOT declare them. Phase 84's plan explicitly disclaims frontend changes (DATA-02 is backend-only data plumbing for Phase 86), but the project's general convention is to keep the TS mirror in lockstep with the Pydantic schema — see the file's own docstring: "TypeScript mirrors of the Pydantic v2 endgame schemas from the backend." TypeScript will tolerate the extra runtime fields, but the schema drift will silently rot and complicate the future Phase 86 wire-up. Either update the interface now (zero risk, additive) or add a comment in the TS file pointing to Phase 86.
**Fix:**
```ts
export interface ConversionRecoveryStats {
  // ... existing fields ...
  recovery_draws: number;
  // Phase 84: per-class opponent baseline via same-game mirror identity.
  // Null when the MIRROR bucket sample < 10.
  opponent_conversion_pct: number | null;
  opponent_conversion_games: number;
  opponent_recovery_pct: number | null;
  opponent_recovery_games: number;
}
```

## Info

### IN-01: Stale line-number references in new comment block

**File:** `app/services/endgame_service.py:358-362`
**Issue:** The Phase 84 block's comment claims to reference `_MIN_OPPONENT_SAMPLE` at "line 233" — the constant is actually defined on line 234. The same comment cites `_compute_score_gap_material (~line 824)` for the precedent pattern, but the relevant `swap_games >= _MIN_OPPONENT_SAMPLE` check sits at line 866 (and the function itself starts at line 723). Line-number annotations rot quickly; either drop them or reference the symbol name only.
**Fix:**
```python
# Phase 84: per-class opponent baseline via same-game mirror identity.
# Conv is a win-rate, Recov is a save-rate, so the two mirror formulas
# are asymmetric. Reuses _MIN_OPPONENT_SAMPLE, gated on the MIRROR bucket
# size (not the own bucket). Phase 60 introduced the pattern for Section 2
# in _compute_score_gap_material.
```

### IN-02: Asymmetric local-variable scoping for `recovery_losses` vs `conversion_losses`

**File:** `app/services/endgame_service.py:345 vs 365`
**Issue:** `conversion_losses` is computed unconditionally at line 345 (then reused both for `ConversionRecoveryStats.conversion_losses=` and inside the mirror identity at line 374). `recovery_losses` is only computed *inside* the `if recovery_games >= _MIN_OPPONENT_SAMPLE:` branch at line 365, even though it's a one-liner. The asymmetry isn't a bug — both branches compute correct values — but it makes the new block harder to read at a glance and makes the two mirror formulas look more different than they are. Hoist `recovery_losses` to live next to `recovery_pct` for symmetry.
**Fix:**
```python
recovery_saves = recovery_wins + recovery_draws
recovery_losses = recovery_games - recovery_wins - recovery_draws  # mirrors conversion_losses
recovery_pct = (
    round(recovery_saves / recovery_games * 100, 1) if recovery_games > 0 else 0.0
)
# ... then in the gated block ...
if recovery_games >= _MIN_OPPONENT_SAMPLE:
    opponent_conversion_pct = round(recovery_losses / recovery_games * 100, 1)
```

### IN-03: Test docstring "symmetric_60_40" is misleading

**File:** `tests/test_endgame_service.py:393-399`
**Issue:** The test is named `test_per_type_opponent_baseline_symmetric_60_40` and the docstring describes the case as "Mirror identities: opp_conv == 60.0, opp_recov == 40.0". Those mirror values aren't structurally symmetric — they happen to equal 60/40 because conv_pct = 60% (so conv_loss_rate = 40%) and recov_save_rate = 40% (so recov_loss_rate = 60%) coincidentally match. The name implies the two mirror percentages must be equal in this scenario, which would mislead a reader updating the test later. Rename to something like `test_per_type_opponent_baseline_mirror_values` or `test_per_type_opponent_baseline_at_60_pct_conv_40_pct_recov`.
**Fix:** Rename the test method and clarify the docstring:
```python
def test_per_type_opponent_baseline_mirror_values(self):
    """Rook conv 6W/0D/4L → opp_recov == 40%; recov 2W/2D/6L → opp_conv == 60%.

    The two opponent rates need not be equal; they happen to invert here
    because conv_loss_rate(40%) == recov_save_rate(40%)."""
```

---

_Reviewed: 2026-05-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
