---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
reviewed: 2026-05-03T14:00:00Z
depth: deep
files_reviewed: 24
files_reviewed_list:
  - app/services/eval_confidence.py
  - app/schemas/stats.py
  - app/repositories/stats_repository.py
  - app/services/stats_service.py
  - tests/services/test_eval_confidence.py
  - tests/test_stats_schemas.py
  - tests/services/test_stats_service_phase_entry.py
  - tests/test_stats_repository_phase_entry.py
  - frontend/src/types/stats.ts
  - frontend/src/components/charts/MiniBulletChart.tsx
  - frontend/src/components/insights/ConfidencePill.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/lib/clockFormat.ts
  - frontend/src/components/charts/EndgameClockPressureSection.tsx
  - frontend/src/lib/openingStatsZones.ts
  - frontend/src/lib/openingsBoardLayout.ts
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
  - frontend/src/components/insights/__tests__/ConfidencePill.test.tsx
  - frontend/src/lib/__tests__/clockFormat.test.ts
  - frontend/src/lib/__tests__/openingStatsZones.test.ts
  - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
  - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 80: Code Review Report

**Reviewed:** 2026-05-03T14:00:00Z
**Depth:** deep
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 80 is a well-scoped, well-tested addition. The statistical helper is sound, the SQL single-pass pattern is correct, the schema additivity is clean, and the frontend components follow established patterns. No security vulnerabilities or data-corruption risks found.

Four warnings deserve attention before shipping:

1. The opponent-clock row in the test seed carries `eval_cp` and `eval_mate` from the MG-entry row — this inflates `eval_n_mg` by 1 in the tests and could mask the `ROW_NUMBER() OVER (ORDER BY ply)` picking the wrong entry row in certain edge cases.
2. The `ConfidenceTooltipContent` reuse is semantically broken for eval confidence: it renders "Score: 50% (at 50% baseline)" and "strength/weakness" language when `score` is not passed, which is confusing and misleading for users who hover the eval confidence pill.
3. The `gp_entry` inner join does not filter `gp_entry.user_id == user_id`. While safe today (game_id is globally unique), it deviates from the established pattern and leaves a silent correctness dependency on the uniqueness of `game_id`.
4. The `clock_diff_pct` formula is mathematically sound but semantically inconsistent with `avg_clock_diff_seconds`: seconds is a per-game average, pct is a sum-weighted ratio. For heterogeneous base times, these tell slightly different stories.

---

## Warnings

### WR-01: Opponent-clock seed row copies `eval_cp`/`eval_mate` — inflates `eval_n_mg` in tests

**File:** `tests/test_stats_repository_phase_entry.py:168-182`

**Issue:** The `_make_game_with_phase_entries` helper creates the opponent-clock row (ply = MG_ENTRY_PLY + 1, phase = 1) with the same `eval_cp=mg_eval_cp` and `eval_mate=mg_eval_mate` as the MG-entry row. That row is a `phase=1` row at a different ply. The SQL query's `ROW_NUMBER() OVER (PARTITION BY game_id, phase ORDER BY ply)` picks the *lowest* ply as `rn=1` — so the MG-entry row at ply=10 wins over the opponent-clock row at ply=11. However, the opponent-clock row still matches the opening's `full_hash` and `phase=1`, so in `eval_n_mg` counting via the `GROUP BY full_hash`, the `has_continuous_in_domain_eval` predicate is evaluated against `gp_entry.eval_cp` (which is the entry-ply row only, since that's what `gp_entry` is joined to). So the eval counting is NOT double-counted — the `gp_entry` join correctly lands on ply=10. The bug is narrower: the opponent-clock row carries `eval_cp` that is meaningless on that row (it's the opponent's ply), but since that row is never fetched via `gp_entry`, it does not corrupt the aggregation.

However, the test in `test_stats_service_phase_entry.py:_seed_game_with_phases` (line 199-213) does the same thing and also sets `phase=1` on the opponent-clock row. If a future phase changes the `ROW_NUMBER()` ordering or uses `MIN(ply)` differently, the extra eval-bearing phase=1 row at ply+1 will affect results. Additionally, the partition invariant test (`test_partition_invariant_phase_entry_total` line 406-408) expects 5 EG rows but seeds 5 games all with `eg_eval_cp=None, eg_eval_mate=None` by default — but the inner query scans `phase IN (1,2)` and then picks `rn=1` per phase; games with no EG row contribute zero EG entries, which is correct. That test assertion passes because the seeder always creates one EG row per game. So the invariant count of 5 is correct.

The actual fragility is that the opponent-clock row's `eval_cp` being non-NULL could cause a test to fail in unexpected ways if the ROW_NUMBER semantics changed (e.g., if the ordering were reversed). The row should not carry `eval_cp`.

**Fix:** Remove `eval_cp=mg_eval_cp` and `eval_mate=mg_eval_mate` from the opponent-clock row in both seed helpers:

```python
# tests/test_stats_repository_phase_entry.py:168-182 — remove eval fields
session.add(
    GamePosition(
        game_id=game.id,
        user_id=user_id,
        ply=OPP_CLOCK_PLY,
        full_hash=full_hash,
        white_hash=full_hash + 1000,
        black_hash=full_hash + 2000,
        phase=1,
        # No eval_cp / eval_mate — this row represents opponent's clock only
        clock_seconds=opp_clock,
    )
)
```

Same fix in `tests/services/test_stats_service_phase_entry.py:199-213`.

---

### WR-02: `ConfidenceTooltipContent` tooltip semantics are wrong for eval confidence pills

**File:** `frontend/src/components/insights/ConfidencePill.tsx:37-42`

**Issue:** `ConfidencePill` passes `score ?? 0.5` to `ConfidenceTooltipContent`. When used from `MostPlayedOpeningsTable` with no `score` prop (all four call sites omit it), the tooltip reads:

- "Score: 50% (at 50% baseline)"
- "Possibly a real **strength**" / "Likely a real **strength**"
- "Probability: X% of such a difference resulting from pure chance"

The "score / strength / weakness" language is WDL-centric and makes no sense for an eval confidence pill. A user hovering a "high" pill on the eval column will read about "score 50%" and "strength" with no connection to the Stockfish centipawn mean being tested.

**Fix:** Add an optional `noun` prop to `ConfidenceTooltipContent` (or a `variant: 'wdl' | 'eval'` prop) so eval pills render an eval-appropriate message, e.g. "Avg eval significantly differs from 0 at p < 0.05." Alternatively, add an optional `tooltipContent` slot to `ConfidencePill` to allow callers to override the tooltip body for different statistical contexts. The minimum viable fix is a `noun` override:

```tsx
// ConfidenceTooltipContent: add optional noun override
interface ConfidenceTooltipContentProps {
  level: ConfidenceLevel;
  pValue: number;
  score: number;
  gameCount: number;
  // When provided, replaces the score line with an eval-centric description
  evalMeanPawns?: number | null;
}
```

And in `ConfidencePill`, pass `evalMeanPawns` through when the caller is in eval context.

---

### WR-03: `gp_entry` and `gp_opp` joins missing `user_id` filter (implicit safety dependency)

**File:** `app/repositories/stats_repository.py:658-668`

**Issue:** The joins to `gp_entry` and `gp_opp` (aliased `GamePosition`) use only `(game_id, ply)` as join keys. The established pattern across the codebase (all other `GamePosition` queries in `stats_repository.py`, `endgame_repository.py`) always includes `GamePosition.user_id == user_id` in join conditions or WHERE clauses when the table is directly accessed. The `gp_entry` join is safe *today* because `game_id` is a globally unique PK (games belong to exactly one user), but the pattern deviation makes future readers incorrectly infer the join is unscoped, and it will silently return wrong data if the schema ever allows game_id reuse (unlikely but defensible to guard against).

```python
.join(
    gp_entry,
    (gp_entry.game_id == phase_entry_subq.c.game_id)
    & (gp_entry.ply == phase_entry_subq.c.entry_ply)
    & (gp_entry.user_id == user_id),  # add this
)
.outerjoin(
    gp_opp,
    (gp_opp.game_id == phase_entry_subq.c.game_id)
    & (gp_opp.ply == phase_entry_subq.c.entry_ply + 1)
    & (gp_opp.user_id == user_id),  # add this
)
```

---

### WR-04: `clock_diff_pct` is sum-weighted ratio, not avg-of-per-game-pcts — inconsistent with `avg_clock_diff_seconds`

**File:** `app/services/stats_service.py:437-438`

**Issue:** `avg_clock_diff_seconds = clock_diff_sum / clock_diff_n` is a per-game arithmetic mean of the absolute diff. `avg_clock_diff_pct = (clock_diff_sum / base_time_sum) * 100.0` is a sum-of-diffs / sum-of-base-times ratio. For uniform base times these are equivalent, and the tests only cover uniform base times. For users who mix bullet and blitz (or whose games have varying base_times due to increment), the two statistics describe slightly different things:

- `avg_clock_diff_seconds`: mean of per-game diffs (equal weight per game)
- `avg_clock_diff_pct`: total clock diff as a fraction of total base time (games with larger base time have more weight)

The formula is not wrong per se — sum-weighted ratio is a defensible way to express the percent and avoids the degenerate case where a few very short games pull the per-game-pct average. But the tooltip says "Difference between your remaining clock and your opponent's at middlegame entry. Shown as percent of base time and absolute seconds." — this doesn't reflect the weighting difference. The test `test_get_most_played_openings_clock_diff_pct_signed` (line 367-389) uses uniform base_time=300 for all 5 games, so it cannot detect a weighting mismatch.

**Fix:** Either document the weighting explicitly in the schema comment and tooltip, or compute `avg_clock_diff_pct` consistently as `avg_clock_diff_seconds / avg_base_time_seconds * 100`:

```python
# Option A: per-game average ratio (consistent with avg_clock_diff_seconds)
avg_base_time = pe.base_time_sum / pe.clock_diff_n
avg_clock_diff_pct = (avg_clock_diff_seconds / avg_base_time) * 100.0 if avg_base_time > 0 else None

# Option B: keep sum-weighted, but document it
# avg_clock_diff_pct = (pe.clock_diff_sum / pe.base_time_sum) * 100.0
```

At minimum, add a heterogeneous-base-time test case.

---

## Info

### IN-01: `ConfidencePill` missing `testId` on mobile instances in `MostPlayedOpeningsTable`

**File:** `frontend/src/components/stats/MostPlayedOpeningsTable.tsx:263,291`

**Issue:** Mobile line 2 and line 3 `ConfidencePill` instances (lines 263-267, 291-296) omit the `testId` prop. The `data-testid` rules in CLAUDE.md require interactive elements to have test IDs. Per the Browser Automation Rules, the pill's `<span>` is the only element inside the Tooltip that a test tool can target for the mobile layout.

**Fix:** Add `testId` props:
```tsx
// Mobile MG pill (line 263)
<ConfidencePill
  level={o.eval_confidence}
  pValue={o.eval_p_value}
  gameCount={o.eval_n}
  testId={`${testIdPrefix}-confidence-mobile-${rowKey}-info`}
/>

// Mobile EG pill (line 291)
<ConfidencePill
  level={o.eval_endgame_confidence}
  pValue={o.eval_endgame_p_value}
  gameCount={o.eval_endgame_n}
  testId={`${testIdPrefix}-eg-confidence-mobile-${rowKey}-info`}
/>
```

Same applies to the two mobile `ConfidencePill` instances in `Openings.tsx` `MobileMostPlayedRows` (lines 217-221, 266-270).

---

### IN-02: `MostPlayedOpeningsTable` `<button>` elements missing `type="button"`

**File:** `frontend/src/components/stats/MostPlayedOpeningsTable.tsx:169,396`

**Issue:** The games-count button (line 169) and the More/Less toggle (line 396) are bare `<button>` elements without `type="button"`. HTML default is `type="submit"` for buttons inside a form; while these buttons are not inside a form today, CLAUDE.md's semantic HTML convention and React best practices require explicit `type="button"` on non-submit buttons.

**Fix:**
```tsx
<button type="button" className="flex items-center ...">
```

---

### IN-03: `formatSignedPct1` rounding edge case: `toFixed(1)` after `Math.round(pct * 10) / 10` is redundant

**File:** `frontend/src/lib/clockFormat.ts:30-31`

**Issue:** The implementation rounds to one decimal place twice:
```ts
const rounded = Math.round(pct * 10) / 10;
if (rounded > 0) return `+${rounded.toFixed(1)}%`;
return `${rounded.toFixed(1)}%`;
```
`Math.round(pct * 10) / 10` already gives a value with at most one decimal place (e.g., 8.2, -3.2, 0.0). `toFixed(1)` then formats it, which is correct. This is not a bug but the logic is clearer if the comment explains the two-step: round first to eliminate floating-point tails, then format.

Minor: `Math.round(0.05 * 10) / 10` = `Math.round(0.5) / 10` = `0.1` (JS "round half up"), but `Math.round(-0.05 * 10) / 10` = `Math.round(-0.5) / 10` = `-0.0` in JS, formatted as `'-0.0%'`. This is a cosmetic edge case (a -0.05% diff renders as "-0.0%") but is unlikely to occur in practice since clock diffs are typically larger.

---

### IN-04: `eval_confidence` schema field uses `= "low"` default rather than `Optional` — inconsistency with other Phase 80 fields

**File:** `app/schemas/stats.py:69,93`

**Issue:** `eval_confidence` and `eval_endgame_confidence` default to `"low"` (not `None`). All other new Phase 80 fields that carry computed values (`avg_eval_pawns`, `eval_p_value`, etc.) default to `None`. The design decision is documented (eval_n=0 row should show `eval_confidence="low"`), but the TypeScript interface at `frontend/src/types/stats.ts:53,66` treats them as required non-optional string literals (`eval_confidence: 'low' | 'medium' | 'high'` — no `?`). This matches the schema default. However, `eval_n` is also required with a default of `0` in the schema, yet the TypeScript type also has `eval_n: number` without `?`. The asymmetry between the `?`-optional CI fields and the required-with-default count/confidence fields is intentional but could confuse callers who pass `undefined` for `eval_confidence` from partial objects.

No change needed if the intent is intentional; add a comment to the schema clarifying the design choice.

---

### IN-05: `test_n_below_min_returns_low_even_with_strong_mean` contains a comment with incorrect arithmetic

**File:** `tests/services/test_eval_confidence.py:56-61`

**Issue:** The test comment at line 57 says `sumsq = 9 * 100^2 = 90000` for zero variance, but then uses `eval_sumsq=81000` (which is `9 * 90^2` or `9 * 100 * 90`). The assertion at line 61 verifies `ci_half_width == 0.0`. The comment on lines 57-59 correctly notes that `max(0, (81000 - 90000)/8) = 0` (negative clamped to zero), so the test body is correct. But the comment says "sumsq must be n * mean^2 for zero variance" after using a different sumsq — the self-correction in the comment is confusing, not the code.

Not a bug; just a misleading comment that should be cleaned up to avoid confusion when reading the test.

---

## Verdict: warnings only

No blocking issues. The four warnings are correctness/semantic problems that should be fixed before shipping, but none cause incorrect behavior in the common case (all tests pass with uniform base times; the tooltip misleads users but shows valid p-value and game count data; the join safety dependency is currently protected by schema constraints). The most important fix is WR-02 (tooltip semantics) since it's user-visible and permanently confusing.

---

_Reviewed: 2026-05-03T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
