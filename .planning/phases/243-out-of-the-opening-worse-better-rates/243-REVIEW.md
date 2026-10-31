---
phase: 243-out-of-the-opening-worse-better-rates
reviewed: 2026-10-31T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py
  - app/models/benchmark_cohort_cdf.py
  - app/models/user_benchmark_percentile.py
  - app/repositories/opening_out_repository.py
  - app/repositories/user_benchmark_percentiles_repository.py
  - app/routers/openings.py
  - app/schemas/opening_out.py
  - app/services/canonical_slice_sql.py
  - app/services/endgame_ranked_service.py
  - app/services/global_percentile_cdf.py
  - app/services/opening_insights_constants.py
  - app/services/opening_out_stats_service.py
  - app/services/user_benchmark_percentiles_service.py
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/components/openings/stats/OutOfOpeningPopover.tsx
  - frontend/src/components/openings/stats/OutOfOpeningSection.tsx
  - frontend/src/components/openings/stats/outOfOpeningCopy.ts
  - frontend/src/hooks/useOutOfOpeningStats.ts
  - frontend/src/pages/Import.tsx
  - frontend/src/pages/openings/StatsTab.tsx
  - frontend/src/types/openingOut.ts
  - scripts/gen_global_percentile_cdf.py
  - scripts/opening_out_eval_source_report.py
  - tests/services/test_opening_out_rates_parity.py
  - tests/services/test_user_benchmark_percentiles_service.py
  - tests/routers/test_openings_out_of_opening.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 243: Code Review Report

**Reviewed:** 2026-10-31
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed the migration, shared SQL builders, Stage B fan-out, on-read service, CDF regen script, and the
frontend card/popover. I traced these specifically and found them correct:

- **Classification SQL.** Baseline parenthesisation (no `--` comment hazard). User-POV sign handling for
  both `eval_cp` and `eval_mate`, which matches `stats_repository` and the other builders. DISTINCT ON first
  `phase = 1` ply. Early-termination branch (`termination` enum values, `result <> '1/2-1/2'`, the
  `(result='1-0') = (color='white')` win test). Sub-800 floor. `count(side)` counting only qualifying games.
- **Percentile orientation.** The worse rate is `100 - raw`, the better rate is `raw`. The direction guard
  uses raw values on both sides.
- **Gate.** 95% z passed in explicitly, not the 99% path.
- **Weighting.** `peer_p50` is weighted with the same game weights as the headline.
- **Storage.** The 4-column ON CONFLICT target matches the new PK. `fetch_for_user` filters `color = 'all'`.
- **Migration.** Dead labels are deleted before the CHECK and logged. The ENUM-to-TEXT conversion and the
  cast/type drop are in a safe order. The downgrade drops the per-colour and opening rows before the PK and
  ENUM restore.
- **Cache invalidation.** The `['outOfOpeningStats']` key is invalidated on import completion, during
  polling, and on delete-all. The query is gated on `tier2`.
- **Seeded CDF cells.** `app/data/cohort_cdf.tsv` has 252 opening cells, 99 breakpoints each, monotone,
  inside [0, 1], with worse-rate medians falling with rating.

No critical defects found. The warnings are an incorrect card status in an edge state, a deploy-ordering
gap for existing users, and a UI robustness gap.

## Warnings

### WR-01: Card reports `below_floor` ("0 of 30") when every TC is `ranked` but none has a peer band

**File:** `app/services/opening_out_stats_service.py:117-120, 277-284, 308-310`
**Issue:** `_TcEntry.contributes` requires `status == "ranked"` AND `raw_percentile is not None` AND
`band is not None`. `status == "ranked"` comes from the persisted row (`rank_status`, line 191). `band` comes
from the CDF cell at the user's CURRENT rounded anchor (`_fetch_peer_bands`, line 159). These two are read at
different times and can disagree. Scenario: Stage B ranked the user against anchor cell A. A later Stage A
recompute (new import) moved the anchor to a grid step whose CDF cell is suppressed or absent. Examples are
the sparse (2400, classical) cell, or the 19 classical cells that exist against 35-36 for the other TCs. The
persisted row still has a non-NULL percentile, so the TC stays `ranked`, but `peer_bands` has no key for it.
`any(e.contributes ...)` is False, so `_unranked_card` runs. `_unranked_status` only handles `pending` and
`unranked`, so a set of `{"ranked"}` falls through to `"below_floor"`. With `matching = []`, `floor_n` is
`max([], default=0) = 0`. The user sees "0 of 30 games needed" on a colour with hundreds of games. The
per-TC popover list in the same response still shows that TC as ranked with a percentile (via `_tc_out`),
while the pooled `k`/`n`/footer exclude it.
**Fix:** Treat a ranked-but-bandless TC as `unranked` in `_tc_entry`, so status, headline and popover list
agree:
```python
status, floor_n, floor_required = rank_status(...)
band = inputs.peer_bands.get((metric, tc))
if status == "ranked" and band is None:
    status = "unranked"  # row percentile exists but the current anchor has no CDF cell
raw_percentile = row.percentile if status == "ranked" and row is not None else None
```
Alternatively add `"ranked"` to the `_unranked_status` precedence (map to `unranked`).

### WR-02: Existing users get no opening rows after deploy, and no in-app path recomputes them; seed-before-backfill ordering is silent

**File:** `app/services/user_benchmark_percentiles_service.py:633-641`, `app/routers/imports.py:289-295`
**Issue:** The opening rows are written only inside `compute_stage_b`, which runs on import completion and
on eval-drain completion. Existing prod users already have endgame rows, so `has_any_rows` is True, `stuck`
is False, and nothing re-triggers Stage B for them. After deploy, every existing user sees "Not ranked yet"
in the new section until they next import or a drain runs. The only recovery is a manual prod run of the
archived `scripts/archive/backfill_user_percentiles.py`, which appears only in the 243-05 SUMMARY/PLAN prose.
Ordering also matters. `scripts/seed_cohort_cdf.py` is a manual runbook step. If Stage B (or the backfill)
runs before the TSV is seeded, `interpolate_cohort_percentile(value, None)` returns None and
`upsert_percentile` persists a row with `percentile = NULL`. That row reads as `unranked` until Stage B
reruns, and nothing flags it. This is a release-ordering hazard that only the runbook prose guards against.
**Fix:** Pin the order in `docs/production-runbook.md` / the deploy checklist (migrate, seed CDF, backfill
Stage B). Then either (a) make `bin/deploy.sh` run the seed, or (b) add a cheap startup/readiness sweep that
queues `compute_stage_b` for users with an anchor but no opening rows. A test or assertion that the seeded
TSV contains the opening ids before the backfill runs would also help.

### WR-03: A failed background refetch replaces already-loaded card data with a LoadError

**File:** `frontend/src/components/openings/stats/OutOfOpeningSection.tsx:84-98`
**Issue:** The branch order is `!tier2`, then `isError`, then `!data`. TanStack Query keeps `data` when a
refetch fails, but `isError` becomes true. The import-complete and delete-all handlers call
`invalidateQueries(['outOfOpeningStats'])`, which triggers exactly such a background refetch. One transient
5xx or network blip right after an import therefore blanks a valid, already-rendered card into
"Failed to load" until the next successful fetch. The cached data was perfectly usable. `refetchOnWindowFocus`
is disabled, so there is no quick self-heal.
**Fix:** Prefer data over a background error:
```tsx
} else if (!data) {
  body = isError ? <LoadError .../> : <p ...>Loading out-of-the-opening stats...</p>;
} else { /* render cards */ }
```
or gate the error branch on `isError && !data`.

## Info

### IN-01: Frontend eval cut is a hand-mirrored duplicate, and its comment names a constant that does not exist

**File:** `frontend/src/components/openings/stats/outOfOpeningCopy.ts:15-16`
**Issue:** The comment says it "Mirrors OPENING_OUT_THRESHOLD in opening_insights_constants.py". The backend
constant is `OPENING_OUT_THRESHOLD_PAWNS` (`app/services/opening_insights_constants.py:94`). The value `1.0`
is a duplicated literal with no generated file or test tying it to the backend, so a future change to the cut
silently desyncs the popover copy from the SQL. The project already has `scripts/gen_*.py` for such mirrors.
**Fix:** Correct the name in the comment. Preferably add a test asserting
`OUT_OF_OPENING_EVAL_CUT === backend OPENING_OUT_THRESHOLD_PAWNS`, or emit it through the existing
generated-constants path.

### IN-02: Stale documentation and naming left behind

**File:** `frontend/src/components/endgames/stats/PercentileBar.tsx:75`, `tests/services/test_user_benchmark_percentiles_service.py:448`
**Issue:** `PercentileBar`'s `significant` prop is documented as "99% significance", but the new Openings
caller passes a 95% verdict. The shared component now serves both levels. The test
`test_upsert_called_with_3_column_pk_tuple` still names a "3 column" PK, though the PK and ON CONFLICT target
are now 4 columns.
**Fix:** Change the prop doc to "significance verdict (99% on Endgames, 95% on Openings)" and rename the test
to `..._4_column_pk_tuple`.

### IN-03: `eval_mate = 0` is classified as "even"

**File:** `app/services/canonical_slice_sql.py:1403, 1431`
**Issue:** `sign(0) = 0`, so a middlegame-entry ply whose stored mate is 0 (side to move already checkmated)
lands in the "even" bucket and counts as a qualifying game. The game's result already says who won, so the
D-01 rule "a mate score counts by its sign" is under-specified here. This is documented in the builder
docstring and is very unlikely at middlegame entry, so it is low impact. It is noted because a checkmated
position being "even" is the one place the classification contradicts the board.
**Fix:** If it can occur in the data, fall back to the result-based branch when `eval_mate = 0`
(`WHEN me.eval_mate = 0 THEN <same CASE as the no-middlegame branch>`). Otherwise leave as documented.

---

_Reviewed: 2026-10-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
