---
phase: 243-out-of-the-opening-worse-better-rates
fixed_at: 2026-10-31T00:00:00Z
review_path: .planning/phases/243-out-of-the-opening-worse-better-rates/243-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 243: Code Review Fix Report

**Fixed at:** 2026-10-31
**Source review:** .planning/phases/243-out-of-the-opening-worse-better-rates/243-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03; Info findings out of scope)
- Fixed: 3
- Skipped: 0

Edits and commits were made directly in the main checkout on branch
`gsd/phase-243-out-of-the-opening-worse-better-rates` (no temporary worktree), as directed by the
caller, so the frontend gates could run with the real `node_modules`. Verification therefore ran in
the main checkout and is reproducible from it.

## Fixed Issues

### WR-01: Card reports `below_floor` ("0 of 30") when every TC is `ranked` but none has a peer band

**Files modified:** `app/services/opening_out_stats_service.py`, `tests/services/test_opening_out_stats_service.py`
**Commit:** 0d422b160
**Status:** fixed: requires human verification (logic/status-precedence change)
**Applied fix:** Adapted the review's alternative option rather than its primary one. The primary
suggestion (downgrade the per-TC status to `unranked` in `_tc_entry`) would contradict the existing
A3 test `test_ranked_tc_without_cdf_cell_is_excluded_from_headline_and_gate`, which pins a bandless
TC as listed `ranked` in the popover. Instead `_unranked_status` now returns `unranked` when any
entry is `ranked` (but nothing contributes), with a comment at the fix site explaining what broke.
Per-TC rows keep their status; only the card-level status changes. `floor_n` is only rendered for
`below_floor`, so no UI copy depends on it here. Added regression test
`test_card_is_unranked_not_below_floor_when_every_ranked_tc_lacks_a_peer_band`; confirmed it fails
with the fix stashed and passes with it.
**Verification:** `uv run pytest tests/services/ tests/routers/test_openings_out_of_opening.py -n auto`
(2357 passed, 16 skipped), `ruff check`/`ruff format` clean, `ty check` clean on touched files.

### WR-02: Existing users get no opening rows after deploy, and no in-app path recomputes them; seed-before-backfill ordering is silent

**Files modified:** `docs/production-runbook.md`, `tests/scripts/test_cohort_cdf_seed_artifact.py`
**Commit:** 3a275ad31
**Applied fix:** Documentation plus a guard test, as scoped. Added a "Releasing a new percentile
metric family" section to `docs/production-runbook.md` pinning the order: deploy (migration), seed
CDF (`python -m scripts.seed_cohort_cdf` in the backend container), then Stage B backfill
(`uv run python -m scripts.archive.backfill_user_percentiles --target prod` via the prod tunnel),
with the reasons. Script paths and invocations were verified to exist; `--help` confirmed the `-m`
form works. Noted in the runbook that the `python scripts/archive/...` form in the script docstring
fails with `No module named 'app'`, and that `--skip-anchors` has no effect without `--metric`
(the Phase 243 SUMMARY's suggested flag is harmless but not useful). Added
`test_committed_tsv_contains_the_opening_metrics` asserting the committed `app/data/cohort_cdf.tsv`
has cells for both opening metric ids.
**Deferred (out of phase scope, not implemented):** the code-level options from the review, making
`bin/deploy.sh` run the seed and adding a startup/readiness sweep that queues `compute_stage_b` for
users with an anchor but no opening rows. `bin/deploy.sh` was not modified. The ordering hazard
remains runbook-guarded rather than code-enforced.

### WR-03: A failed background refetch replaces already-loaded card data with a LoadError

**Files modified:** `frontend/src/components/openings/stats/OutOfOpeningSection.tsx`, `frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx`
**Commit:** 255c961f4
**Applied fix:** The error branch is now `isError && !data`, so cached data keeps rendering when a
background refetch (import-complete invalidation) fails; a comment explains why. Added test
`keeps showing cached data when a background refetch fails`; confirmed it fails without the fix.
**Verification (from `frontend/`):** `npm run lint` clean, `npm run build` clean, `npm test -- --run`
341 files / 5703 tests passed.

---

_Fixed: 2026-10-31_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
