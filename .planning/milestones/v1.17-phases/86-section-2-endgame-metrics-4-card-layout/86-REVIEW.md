---
phase: 86-section-2-endgame-metrics-4-card-layout
reviewed: 2026-05-14T14:34:59Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - app/services/score_confidence.py
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/services/test_score_confidence.py
  - tests/test_endgame_service.py
  - frontend/src/lib/endgameMetrics.ts
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameMetricCard.tsx
  - frontend/src/components/charts/EndgameSkillCard.tsx
  - frontend/src/components/charts/EndgameMetricsSection.tsx
  - frontend/src/components/charts/EndgameOverallConnectorArrows.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 86: Code Review Report

**Reviewed:** 2026-05-14T14:34:59Z
**Depth:** standard
**Files Reviewed:** 14 (15 listed; tests-against-backend count + 1)
**Status:** issues_found

## Summary

Phase 86 replaces the legacy `EndgameScoreGapSection` with a 4-card layout
(Conv → Parity → Recov → Skill) and adds two backend math helpers
(`compute_skill_diff_test`, `compute_per_bucket_diff_test`) plus 8 new wire
fields. The statistical work is solid: variance formulas correctly use
HEADLINE-RATE variance per bucket (Bernoulli on Conv win, Bernoulli on Recov
save, trinomial on Parity), the variance-0 trap is handled, gating logic
matches D-01 / D-05, and regression tests pin the math against the two
plan-checker BLOCKER scenarios (chess-score vs headline-rate variance,
parity self-mirror). No critical bugs found.

Notable findings:

- **WR-01 (backend, function size)**: `_compute_score_gap_material` is now
  ~313 LOC, well past the CLAUDE.md hard limit of 200 logic LOC. Phase 86
  added ~70 LOC to a function that was already bloated.
- **WR-02 (frontend, dead code branch)**: `EndgameSkillCard`'s
  `oppSkill === null` half of the `hasOpponent` gate is unreachable —
  backend invariants guarantee skill and opp_skill are jointly null or
  jointly non-null.
- **WR-03 (frontend, raw-vs-rounded inconsistency)**: `EndgameMetricCard`
  computes `diff` from rounded `win_pct`-based percents (via `userRate` /
  `opponentRate`), but the displayed p-value, CI whiskers, and `value`
  passed to `MetricStatPopover` all derive from unrounded backend math.
  The sig-gating triple's `outsideNeutral` check therefore reads a
  slightly different value than the test that produced `pValue`.
- **WR-04 (frontend, mismatched n-floor semantics)**: `EndgameSkillCard`
  uses `totalGames` (all-bucket sum) as the n-floor for `deriveLevel`,
  but the backend p-value is gated on per-bucket `opp_row.N >= 10` AND
  `n_active >= 2`. These are different gates over different cohorts; the
  frontend defaults to `'low'` when `pValue === null` so behavior is
  benign, but the `n` argument is semantically misleading.

Info-level items cover lifted-but-redundant constants, magic timeouts and
DOM-traversal patterns inherited from Phase 85, and a minor naming nit in
the schema docstring.

## Warnings

### WR-01: `_compute_score_gap_material` exceeds CLAUDE.md function size limit

**File:** `app/services/endgame_service.py:745-1058`
**Issue:** The function spans 313 lines of mixed logic (W/D/L accumulation,
mirror-bucket diffing, sig-test wiring, opponent baseline derivation,
material_rows construction). CLAUDE.md mandates a hard 200-logic-LOC limit
and "refactor bloated code on sight." Phase 86 added ~70 LOC on top of an
already-bloated function, deepening the violation rather than fixing it.
The new helper calls (`compute_skill_diff_test`, three
`compute_per_bucket_diff_test` calls) are independent pipeline stages and
could be extracted cleanly.

**Fix:** Extract three private helpers as part of a follow-up `/gsd-quick`
or Phase 88 polish task:

```python
def _accumulate_bucket_wdl(
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> tuple[dict[MaterialBucket, int], dict[MaterialBucket, int], ...]:
    """Walk entry_rows, pick one span per game, return per-bucket W/D/L/N dicts."""

def _build_material_rows(
    bucket_wins, bucket_draws, bucket_losses, bucket_games,
) -> list[MaterialRow]:
    """Build the 3-row eval-stratified table including per-bucket diff sig test."""

def _compute_skill_composite(
    bucket_wins, bucket_draws, bucket_losses, bucket_games,
) -> tuple[float | None, ...]:
    """Wrap compute_skill_diff_test with the user/mirror row construction."""
```

The CLAUDE.md "refactor bloated code on sight" rule explicitly applies
here; flag separately because Phase 86's plan didn't include the refactor.

### WR-02: `EndgameSkillCard` `oppSkill === null` branch is unreachable dead logic

**File:** `frontend/src/components/charts/EndgameSkillCard.tsx:66-67`
**Issue:** The `hasOpponent` gate reads
```ts
const hasOpponent =
  skill !== null && oppSkill !== null && totalGames >= MIN_OPPONENT_BASELINE_GAMES;
```
But per `compute_skill_diff_test`'s contract (`app/services/score_confidence.py:455-456`
and `492-493`), `skill` and `opp_skill` are computed together over the
same active-bucket set and returned jointly — both are non-null exactly
when `n_active >= 1`, and both are None when `n_active == 0`. The
`oppSkill === null` half of the conjunction can therefore never fire
independently of `skill === null`. This creates ghost defensiveness that
implies the two fields can disagree, which is incorrect and may confuse
readers about the wire contract.

**Fix:** Drop `oppSkill !== null` from the conjunction and rely on the
type narrowing from the `skill !== null` check (or add a comment that
both are tied together by backend invariant). Alternatively, add a
`zod`/runtime assertion at the orchestrator level that the two fields are
jointly populated.

```ts
const hasOpponent =
  skill !== null && totalGames >= MIN_OPPONENT_BASELINE_GAMES;
// Backend invariant (compute_skill_diff_test): skill and opp_skill are
// jointly null or jointly non-null. The non-null assertions below are
// safe; oppSkill === null when skill !== null cannot occur.
```

Without the change, the `as number` casts on `oppSkill` further down (lines
129, 139, 145, 176) are correct per invariant but are not obviously safe
to a reader.

### WR-03: `EndgameMetricCard` `diff` mixes rounded display values with unrounded backend stats

**File:** `frontend/src/components/charts/EndgameMetricCard.tsx:69-76, 82-86`
**Issue:** `userR = userRate(row)` reads `row.win_pct / 100` (or
`row.score`), all of which are rounded to 1 decimal in the backend
(`app/services/endgame_service.py:930-932`). `oppR = opponentRate(...)`
similarly reads `mirror.loss_pct / 100`. The computed `diff = userR - oppR`
is therefore a rounded value. But:

1. `row.diff_p_value` was computed by `compute_per_bucket_diff_test` from
   raw integer (W, D, L, N) tuples — unrounded.
2. The CI whiskers (`row.diff_ci_low / high`) and the `value` passed to
   `MetricStatPopover` (`userR - (oppR as number)`) come from these
   inconsistent sources: the popover's `value` uses rounded inputs while
   its `pValue` uses unrounded math.
3. The `outsideNeutral` gate compares a rounded `diff` against
   `NEUTRAL_ZONE_MIN/MAX = ±0.05`. In edge cases (true diff = 0.049, raw
   p < 0.01) the gate fails on the rounded value but the test reports
   "high" confidence — readers see a confidence label that disagrees with
   the un-colored display.

This is inherited from the legacy section (lifted into `lib/endgameMetrics.ts`),
not new in Phase 86, but Phase 86 newly mounts it next to the unrounded
backend p-value, making the inconsistency more visible. The Skill card
does NOT have this issue — it consumes `data.skill` / `data.opp_skill`
directly (both unrounded), and the metric card should match.

**Fix:** Either expose raw rates on `MaterialRow` (add `user_rate` /
`opponent_rate` as `float` fields populated server-side from
`_headline_rate`), or compute `userR / oppR` from raw integer fields if
they're added (requires schema change). Minimum fix: align by rounding
the Skill scalars to match, or document the discrepancy at the call site.
Lowest-cost path is to populate `user_rate` and `opponent_rate` directly
from the backend so `formatDiffPct` and `outsideNeutral` operate on the
same source as `diff_p_value`.

### WR-04: `EndgameSkillCard` n-floor semantics don't match backend gating

**File:** `frontend/src/components/charts/EndgameSkillCard.tsx:72`
**Issue:** `deriveLevel(pValue, totalGames)` is called with
`totalGames = sum across all material buckets`. But the backend p-value
gating (`compute_skill_diff_test`, `app/services/score_confidence.py:490-493`)
is the conjunction `n_active >= 2 AND every active opp_row.N >= 10`. The
`totalGames` floor is therefore neither a tight upper nor lower bound on
the true gating predicate.

Behavior is benign in practice: when backend gating fails, it returns
`pValue=None`, and `deriveLevel` short-circuits to `'low'` regardless of
the `n` argument. But this means the `totalGames` argument is purely
cosmetic, and a future refactor that changes `deriveLevel`'s `n` floor
(e.g. an enforce-it-on-the-frontend-too tightening) could silently
re-introduce wrongly-confident gating.

**Fix:** Either (a) pass a more semantically meaningful n (e.g. the min
of the three active opp `N` values, which the backend would need to
expose), or (b) document the mismatch in a comment and rely on
`pValue === null` as the true gate. The Phase 86 sibling card
`EndgameMetricCard.tsx:82` has the same shape but uses
`row.opponent_games` which IS the gate variable — Skill should match
that pattern but currently can't because backend only exposes the
aggregate p-value, not the underlying per-bucket gating state.

```tsx
// Document the mismatch:
// pValue is null when n_active < 2 OR any active opp_row.N < 10
// (compute_skill_diff_test gating). totalGames is informational only.
// deriveLevel short-circuits on null pValue, so the strict gate still
// holds even when totalGames >= 10.
const level = deriveLevel(pValue, totalGames);
```

Alternative: surface a backend field like `skill_diff_min_opp_n: int | null`
to use as the gate variable.

## Info

### IN-01: Magic numbers `ARROW_BAR_PX`, `ARROW_HEAD_LEN_PX`, `ARROW_HEAD_HALF_HEIGHT_PX` survive in shared component

**File:** `frontend/src/components/charts/EndgameOverallConnectorArrows.tsx:24-26`
**Issue:** CLAUDE.md mandates "no magic numbers — extract thresholds,
limits, and configuration values into named constants." The constants are
named here (good), but Plan 03 generalized this file to serve both Phase
85 and Phase 86 layouts; the per-pixel geometry now applies to a wider
surface and arguably warrants moving the constants to a layout-tokens
module (e.g. `frontend/src/lib/connectorArrowGeometry.ts`) where Phase
87's per-type cards can also consume them. Not a bug — flag only because
Phase 87 is imminent.

**Fix:** Move the three constants to `lib/connectorArrowGeometry.ts`
when Phase 87 starts to need them. No change required for Phase 86.

### IN-02: `MetricStatPopover` `value` is the rounded display value, not the test statistic

**File:** `frontend/src/components/charts/EndgameMetricCard.tsx:167`
**Issue:** `value={userR - (oppR as number)}` passes the rounded display
diff into the popover's value-line renderer
(`MetricStatTooltip:135` formats it as `(value * 100).toFixed(1) + '%'`).
The popover's `pValue` field comes from unrounded backend math. A reader
hovering the popover sees, e.g., "-3.0% Conversion ... p=0.001" — but the
backend computed p=0.001 against -2.7% (the unrounded diff). The
discrepancy is bounded (<1pp) but the popover suggests a precision
contract the data doesn't honor.

**Fix:** Subsumed by WR-03 — fixing WR-03 (populating raw rates on
`MaterialRow`) resolves this automatically.

### IN-03: `EndgameMetricsSection.buildZeroRow` silently fills missing buckets

**File:** `frontend/src/components/charts/EndgameMetricsSection.tsx:64-79, 104-105`
**Issue:** When the backend response is missing a bucket from
`material_rows` (which the backend invariant
`sum(material_rows.games) == endgame_wdl.total` makes very unlikely —
all three buckets are always emitted, even with games=0), the
orchestrator silently fabricates a zero row. This is correct defensively
but hides backend contract violations: if a future refactor stops
emitting one of the three rows, the UI will quietly show
"Not enough data yet" instead of surfacing the regression in tests.

**Fix:** Add a Sentry breadcrumb when `buildZeroRow` fires, or convert
to an assertion in non-prod (`process.env.NODE_ENV !== 'production'`).

```tsx
function buildZeroRow(bucket: MaterialBucket): MaterialRow {
  if (process.env.NODE_ENV !== 'production') {
    console.warn(`EndgameMetricsSection: backend missing ${bucket} row, falling back to zero row`);
  }
  // ...existing zero row...
}
```

Cheap, makes a contract drift loud, doesn't break the user.

### IN-04: Schema docstring on `MaterialRow.diff_*` fields doesn't note variance-0 trap behavior

**File:** `app/schemas/endgames.py:280-286`
**Issue:** The three new `diff_*` docstrings describe gating but not the
variance-0 trap behavior (when SE_diff=0, p=0 for non-zero diff, p=1 for
zero diff, CI collapses to point estimate). The helper's docstring
covers this, but a schema-consumer reading the type-hint hover popup
would see only the gating note and might assume p=None covers all
"degenerate" cases.

**Fix:** Add a one-liner reference to the helper's variance-0 trap:

```python
diff_p_value: float | None = None
"""...None when opp_row.N < 10 (D-05 strict-opp-gate) or user-side games == 0.
At SE_diff=0 (both sides degenerate), p resolves to 0.0 (diff != 0) or
1.0 (diff == 0); see compute_per_bucket_diff_test for variance-0 trap."""
```

---

_Reviewed: 2026-05-14T14:34:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
