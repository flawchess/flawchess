---
phase: 88-time-pressure-stats-rework
reviewed: 2026-05-17T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - app/repositories/endgame_repository.py
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_service.py
  - app/services/score_confidence.py
  - frontend/src/components/charts/EndgameTimePressureCard.tsx
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
  - frontend/src/generated/endgameZones.ts
  - frontend/src/lib/pressureBulletConfig.ts
  - frontend/src/lib/pressureBulletConfig.test.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
  - scripts/gen_endgame_zones_ts.py
findings:
  critical: 1
  warning: 6
  info: 6
  total: 13
status: issues_found
---

# Phase 88: Code Review Report

**Reviewed:** 2026-05-17
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 88 replaces the legacy clock-pressure table and time-pressure line chart
with a 4-card per-TC grid. The math helper (`compute_score_delta_vs_reference`)
is well-tested and the bullet primitives are reused cleanly. The card / section
components meet most CLAUDE.md frontend rules (theme constants via `theme.ts`,
text-sm floor, `data-testid` coverage).

Three thematic concerns dominate:

1. **Cohort scope mismatch.** `query_cohort_clock_rows` builds an unfiltered,
   global cohort across every user in the DB on every endgame-overview call.
   This deviates from CONTEXT D-05's "filter-responsive mirror-bucket per
   `(rating × TC × color × opponent-type)`" and additionally creates a real
   OOM/availability risk on production scale (cf. the documented Phase 41.1
   OOM lineage in CLAUDE.md).
2. **Small-N cohort references.** `_compute_cohort_lookup` emits a
   `cohort_score` from any `(TC, quintile)` bin with `n >= 1`. Combined with
   `_wilson_score_test_vs_ref`'s `se_null == 0` short-circuit when `ref` is
   0.0 or 1.0, this can produce spurious "sure-signal" p-values against a
   meaningless reference.
3. **Dead-code accretion.** Multiple constants (`CLOCK_PRESSURE_TIMELINE_WINDOW`,
   `MIN_GAMES_FOR_CLOCK_STATS`, `NUM_BUCKETS`, `BUCKET_WIDTH_PCT`,
   `MIN_GAMES_PER_PRESSURE_BIN`) survived the migration unreferenced, and
   generated TS comments still claim "PLACEHOLDER" after Plan 08 calibration.

The score_confidence math is correct and well-bounded. Schema definitions
are clean. The card component nesting depth and logic-LOC are within
CLAUDE.md limits.

## Critical Issues

### CR-01: Unfiltered global cohort query on every overview request (correctness + OOM risk)

**File:** `app/repositories/endgame_repository.py:876-943`, called from
`app/services/endgame_service.py:2415`

**Issue:** `query_cohort_clock_rows` fetches every endgame-qualifying game
for every user except the requesting one, materialising per-game `ply_array`
and `clock_array` lists in Python. There is:

- No `time_control` / `platform` / `rated` / `opponent_type` / `recency`
  filter (no `apply_game_filters` call; the docstring on lines 894-898
  explicitly states "the cohort represents the broader population, not a
  mirror of the user's own filters").
- No pagination / sampling / LIMIT.
- No caching layer — the query runs on every `/api/endgames/overview`
  request.

Two distinct defects flow from this:

1. **Doctrine deviation from CONTEXT D-05.** D-05 locks the cohort as the
   "mirror-bucket per v1.17 doctrine: same `(rating tier × TC × color ×
   opponent-type)` as the user's games in the cell. Filter-responsive."
   The implementation ships a global cohort instead — the per-(TC, quintile)
   `cohort_score` references are population-wide rather than peer-comparable.
   A 800-rated user comparing against a TC-quintile mean dominated by 2000+
   players will see systematically negative deltas painted "weak/red". This
   is a user-visible correctness bug if D-05 was the binding spec.

2. **Availability risk.** Reading every endgame game in the DB into Python
   arrays on every endgame-overview load is exactly the failure mode that
   triggered the Phase 41.1 / FLAWCHESS-3Q OOM (cf. CLAUDE.md "Production
   Server" section). At benchmark-DB scale (~1.9k users in the v1.17
   snapshot) it survives test loads; at production scale with active users
   it can quietly turn an overview request into a multi-second / multi-GB
   read, doubly so because `array_agg(clock_seconds)` per game multiplies
   row count by typical endgame length.

**Fix:** Either (a) restore D-05 by filtering the cohort to the user's
mirror-bucket using `apply_game_filters` with the same `(rating, TC, color,
opponent-type)` slicing the rest of the page uses, or (b) precompute the
cohort `(TC, quintile) → mean_score` table at benchmark-calibration time
and ship it as a constant the same way `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`
is shipped, OR (c) add a request-scoped cache + minimum-N gate. Status
quo cannot ship to production safely.

```python
# Suggested option (c) shape — minimum to mitigate availability + small-N
# defects without re-locking the doctrine question:

async def query_cohort_clock_rows(
    session: AsyncSession,
    *,
    exclude_user_id: int,
    time_control: Sequence[str] | None,
    recency_cutoff: datetime.datetime | None,
    # ... pass through apply_game_filters args
) -> list[Row[Any]]:
    ...
    stmt = apply_game_filters(stmt, time_control, ...)  # mirror user filters
    ...

# And in _compute_cohort_lookup, gate small N:
MIN_COHORT_GAMES_PER_BIN: int = 50
for (tc, q), (w, d, los) in bucket_wdl.items():
    n = w + d + los
    if n >= MIN_COHORT_GAMES_PER_BIN:
        lookup[(tc, q)] = (w + 0.5 * d) / n
```

## Warnings

### WR-01: Small-N cohort_score produces spurious "sure-signal" p-values

**File:** `app/services/endgame_service.py:626-631`
(`_compute_cohort_lookup`); interacts with
`app/services/score_confidence.py:124-141` (`_wilson_score_test_vs_ref`).

**Issue:** `_compute_cohort_lookup` admits any bin with `n >= 1` into the
returned `lookup`. If a `(TC, quintile)` cohort cell has a single game with
a win, `cohort_score = 1.0` is published as the reference. The user's
delta is then computed against this trivially extreme reference and fed
into `_wilson_score_test_vs_ref`, which has a `se_null == 0.0`
short-circuit at `ref == 0.0` or `ref == 1.0` returning `0.0` (sure
signal) whenever `score != ref`. The triple-gate in the card uses
`p < 0.05` and will paint the bullet red/green with high confidence
against a reference built from one cohort game.

In production this is unlikely at popular quintiles, but classical Q0
and bullet Q4 historically have sparse cohort data — exactly the bins
where calibration capped at ±0.06 and where the planner specifically
warned that "extreme-quintile cohort noise" was a known risk.

**Fix:** Add a `MIN_COHORT_GAMES_PER_BIN` gate inside
`_compute_cohort_lookup` (suggest ≥ 50). Bins below the gate are omitted
from the lookup, which the existing `bullets` builder already handles by
emitting a `cohort_score=None` row with all stats None.

```python
MIN_COHORT_GAMES_PER_BIN: int = 50  # cohort reference reliability gate

lookup: dict[tuple[str, int], float] = {}
for (tc, quintile), (w, d, los) in bucket_wdl.items():
    n = w + d + los
    if n >= MIN_COHORT_GAMES_PER_BIN:
        lookup[(tc, quintile)] = (w + 0.5 * d) / n
return lookup
```

### WR-02: Broken `aria-labelledby` reference

**File:** `frontend/src/components/charts/EndgameTimePressureSection.tsx:22`

**Issue:** The `<section>` element declares
`aria-labelledby="time-pressure-heading"`, but no element with
`id="time-pressure-heading"` exists in the section or its consumers.
`grep -rn 'time-pressure-heading'` returns only this attribute. Screen
readers will announce the section with no accessible name (worse than
omitting the attribute — the browser treats a dangling reference as a
failure rather than falling back to nested content).

**Fix:** Either remove the attribute and let the `<p>` sub-question copy
serve as the labelling content via an `aria-label`, or add a matching
heading element. Suggested:

```tsx
<section
  data-testid="time-pressure-cards-section"
  aria-label="Time pressure analysis"
>
```

Or, if the consumer page's `<h2>Time Pressure</h2>` (in `Endgames.tsx:532`)
should label this section, give that `h2` an `id="time-pressure-heading"`
and either move the `aria-labelledby` to a wrapper around both or remove it
here.

### WR-03: Unsafe type assertion + non-null bang on Record index access

**File:** `frontend/src/components/charts/EndgameTimePressureCard.tsx:140`

**Issue:** With `noUncheckedIndexedAccess: true` (CLAUDE.md requirement)
the access
```ts
PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][bin.quintile_index as 0 | 1 | 2 | 3 | 4]!
```
double-launders runtime safety:

1. `bin.quintile_index: number` is cast to a literal-union type with no
   validation.
2. The `!` non-null assertion then erases the
   `noUncheckedIndexedAccess`-injected `undefined` from the Record
   lookup.

If the backend ever emits `quintile_index = 5` (e.g. a future schema
extension or a bug in
`min(4, int(user_clk_pct * 5))`), the next line `neutralBand.max` raises
`TypeError: Cannot read properties of undefined`. CLAUDE.md explicitly
forbids using `!` to suppress `noUncheckedIndexedAccess` errors and
requires narrowing.

**Fix:**

```ts
const q = bin.quintile_index;
if (q < 0 || q > 4) return null; // defensive — schema invariant
const neutralBand = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q as 0 | 1 | 2 | 3 | 4];
if (!neutralBand) return null;
```

Or split the lookup into a typed helper that returns
`{ min: number; max: number } | null` after narrowing.

### WR-04: Frontend duplicates backend thresholds with no shared source of truth

**File:** `frontend/src/components/charts/EndgameTimePressureCard.tsx:39-43`

**Issue:** `MIN_GAMES_PER_TC_CARD = 20` and
`MIN_GAMES_PER_PRESSURE_BIN = 5` are hard-coded literals in the card
component. Identical literals live in
`app/services/endgame_service.py:1258` (`MIN_GAMES_PER_TC_CARD`) and
`:1263` (`MIN_GAMES_PER_PRESSURE_BIN`). Both are user-visible gating
thresholds. If a future calibration retunes either constant on one side,
the other drifts silently — the backend will start filtering at a
different `n` than the frontend renders for. Phase 88's own zone-codegen
pipeline (`gen_endgame_zones_ts.py`) exists precisely to prevent this
shape of drift for zone constants.

**Fix:** Add the two thresholds to the codegen output and import them
from `@/generated/endgameZones` (or a sibling generated module). Same
pattern as `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`.

### WR-05: `MIN_GAMES_PER_PRESSURE_BIN` defined but never used in backend

**File:** `app/services/endgame_service.py:1263`

**Issue:** The backend declares
`MIN_GAMES_PER_PRESSURE_BIN: int = 5` with a 4-line docstring describing
its intent, but the symbol is referenced nowhere in `app/`. The
frontend re-declares it as a magic literal (see WR-04). This is dead
code that misleads readers into thinking backend enforces the gate; in
practice every bin with `n >= 1` is emitted with whatever delta /
p_value / ci `compute_score_delta_vs_reference` returns, including
bins where the math helper's own n-gates are the only protection.

**Fix:** Either wire the constant into `_build_quintile_bullets` (and
emit n-only / None-stats rows below the gate explicitly), delete the
constant, or move it to the codegen surface (per WR-04) so the
frontend is the canonical consumer.

### WR-06: Insights findings silently regress to empty without surfacing the regression

**File:** `app/services/insights_service.py:953-974`, `978-981`

**Issue:** `_finding_clock_diff_timeline` and
`_finding_time_pressure_vs_performance` now hard-return
`_empty_finding(...)` because the legacy data shapes were deleted. The
docstrings note "until a follow-up phase". `_findings_time_pressure_at_entry`
also always emits an empty `net_timeout_rate` finding (line 974). The LLM
prompt assembler will be handed three empty findings every run and the
generated insight prose for these subsections silently degrades — no
sentinel flags this to the developer or the LLM. The Phase 88 plan
documents this as expected, but the change isn't reflected in
`SubsectionFinding`'s metadata (e.g. an `unavailable_reason` field) so a
downstream consumer reading findings programmatically can't distinguish
"no data for this user" from "feature deprecated server-side".

**Fix:** At minimum, log a single Sentry breadcrumb at orchestrator-init
documenting the deprecation, or extend `_empty_finding` with a reason
tag and filter these subsections out of LLM prompts entirely until a
replacement lands. Belongs in the same phase as the schema migration —
silent permanent empty findings are a maintainability landmine.

## Info

### IN-01: Dead constants from legacy clock-pressure pipeline

**File:** `app/services/endgame_service.py:1254`, `:1269-1270`, `:1291`

**Issue:** After deleting `_compute_clock_pressure_timeline`,
`_compute_time_pressure_chart`, and `_build_bucket_series`, several
module-level constants survived unreferenced:

- `MIN_GAMES_FOR_CLOCK_STATS = 10` (line 1254)
- `NUM_BUCKETS = 10` (line 1269)
- `BUCKET_WIDTH_PCT = 10` (line 1270)
- `CLOCK_PRESSURE_TIMELINE_WINDOW = 100` (line 1291)

Ruff's unused-constant detection didn't trip because these are
module-level. Knip-equivalent for Python (`vulture`, `ruff` with `--select=F401` plus
manual cleanup) would catch them.

**Fix:** Delete or move to a deprecation section with comment.

### IN-02: Generated TS still labels calibrated values as "PLACEHOLDER"

**File:** `frontend/src/generated/endgameZones.ts:89-91`, `:102`

**Issue:** Plan 08 calibrated `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` and
`CLOCK_GAP_NEUTRAL_MIN/MAX` from the benchmark cohort. The generator
template in `scripts/gen_endgame_zones_ts.py:218-220` and `:233` still
emits the literal string "PLACEHOLDER" in the comments:

```ts
// PLACEHOLDER values — calibrated by benchmarks §3.3.3 in Plan 08.
...
// Phase 88: Clock Gap scalar neutral band (placeholder until benchmarks §3.3.1).
```

The values themselves are correct (the codegen sources them from the
calibrated Python module), but the comments are now misleading. Next
reader will reasonably assume these constants are still stubs.

**Fix:** Edit the comment strings in `gen_endgame_zones_ts.py` and
regenerate. Suggested wording: `// Calibrated from benchmarks
reports/benchmarks-latest.md §3.3.3 (Plan 08 / 2026-05-17).`

### IN-03: `ARRAY(SmallIntegerType)` vs `ARRAY(FloatType())` inconsistency

**File:** `app/repositories/endgame_repository.py:904, 908`

**Issue:** The new `query_cohort_clock_rows` mirrors the (pre-existing)
inconsistency in `query_clock_stats_rows`:
`ARRAY(SmallIntegerType)` passes the class, `ARRAY(FloatType())`
passes an instance. SQLAlchemy accepts both, but the asymmetry is
noise.

**Fix:** Pick one style across the repo. Low priority — pre-existing
style debt amplified, not introduced.

### IN-04: Cohort docstring contradicts CONTEXT D-05

**File:** `app/repositories/endgame_repository.py:894-898`

**Issue:** The docstring explicitly states:
> "The requesting user's own filter preferences (time_control, platform,
> rated, opponent_type) do NOT apply to the cohort: the cohort represents
> the broader population, not a mirror of the user's own filters (Phase
> 88 Research Q3 / mirror-bucket doctrine)."

CONTEXT D-05 says the opposite ("Filter-responsive. Matches Phases 85–87
exactly"). One of the two documents is wrong about the design intent.
Whichever wins, the contradiction should be resolved in writing so the
next reviewer doesn't have to triangulate. See CR-01 for the underlying
behavioural concern.

**Fix:** Either update the docstring to cite CONTEXT D-05 verbatim and
restore the filter-responsive behaviour, or amend CONTEXT D-05 with a
follow-up entry noting "superseded by Research Q3 — cohort is global".

### IN-05: Tests don't catch broken ARIA attribute

**File:**
`frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx:173-178`

**Issue:** The section wrapper test asserts presence of
`time-pressure-cards-section` testid but never checks
`aria-labelledby` resolves. WR-02's broken ARIA attribute slipped through
the suite.

**Fix:** Add `expect(section.getAttribute('aria-labelledby')).toBe(null)`
once WR-02 is fixed, or `expect(document.getElementById('time-pressure-heading')).not.toBeNull()`
if you keep the attribute.

### IN-06: Quintile index narrowing pattern could be a typed helper

**File:** `frontend/src/components/charts/EndgameTimePressureCard.tsx:140`

**Issue:** The pattern of looking up a `Record<0|1|2|3|4, ...>` keyed by
a `number` recurs once here and would recur in any future per-bin
component. Worth factoring into
`@/generated/endgameZones` as
`getPressureBinBand(tc: ..., quintile: number): PressureBinBand | null`
once WR-03 is fixed.

**Fix:** Add a typed getter alongside the constant in the codegen
template.

---

_Reviewed: 2026-05-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
