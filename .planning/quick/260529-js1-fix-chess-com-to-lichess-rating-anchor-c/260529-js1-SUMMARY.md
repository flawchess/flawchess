---
status: complete
phase: quick-260529-js1
plan: 01
subsystem: rating-anchors
tags: [chesscom-conversion, percentile-anchors, sql, bugfix]
requires: [convert_chesscom_to_lichess, CHESSCOM_INTRA_TC, CHESSCOM_BLITZ_TO_LICHESS]
provides: [composed_chesscom_to_lichess_grid, native-rating-keyed anchor conversion]
affects: [user_rating_anchors pipeline, benchmark cohort CDF generation]
tech-stack:
  added: []
  patterns: [single-source-of-truth grid composition, derive bounds from snapshot constants]
key-files:
  created: []
  modified:
    - app/services/chesscom_to_lichess.py
    - app/services/canonical_slice_sql.py
    - tests/services/test_chesscom_to_lichess.py
    - tests/services/test_canonical_slice_sql.py
    - tests/services/test_user_benchmark_percentiles_service.py
decisions:
  - "Grid step 15 (not the planned 25): a 25-pt step left a 26-pt worst-case nearest-anchor error in the steep classical/rapid range, over the 20-pt tolerance; 15 caps it at 16."
  - "classical bucket maps to chess.com rapid source TC (chess.com has no classical; Daily dropped upstream)."
metrics:
  duration: ~25 min
  completed: 2026-05-29
---

# Phase quick Plan 260529-js1: Fix chess.com to Lichess Rating Anchor Conversion Summary

The `user_rating_anchors` SQL pipeline was converting every chess.com game's native rating against a chess.com **Blitz** lookup table regardless of the game's actual time control. The fix composes the conversion grid by keying it on native chess.com ratings per source TC (bullet/blitz/rapid) and producing each lichess-equivalent through the canonical `convert_chesscom_to_lichess`, so the existing nearest-anchor LATERAL join now applies the correct intra-TC inversion. Rapid/classical anchors are no longer inflated, bullet is no longer deflated, and blitz is unchanged.

## What Changed

- **`composed_chesscom_to_lichess_grid(source_tc, target_tc)`** (new public function in `chesscom_to_lichess.py`): builds a `list[tuple[int, int]]` of (native chess.com rating, lichess equiv) rows by stepping native ratings on a fixed 15-pt grid and calling the canonical converter for each. Single source of truth: no SQL-side reimplementation of inversion or interpolation. Native-rating bounds are derived from the table constants (`CHESSCOM_INTRA_TC` columns for bullet/rapid, `CHESSCOM_BLITZ_TO_LICHESS` key range for blitz), so a future snapshot refit stays in sync.
- **`_chesscom_conversion_values_sql`** (`canonical_slice_sql.py`): now builds the VALUES table from `composed_chesscom_to_lichess_grid(source_tc, target_tc)` via the new `_BUCKET_TO_CHESSCOM_SOURCE_TC` Final mapping (bullet→bullet, blitz→blitz, rapid→rapid, classical→rapid). The `chesscom_anchor` column is now a NATIVE chess.com rating for the bucket's source TC. The nearest-anchor LATERAL join in `_per_user_cte_median_anchor_blended` is correct as-is and was not changed.
- Docstrings of `_chesscom_conversion_values_sql`, `_per_user_cte_median_anchor_blended`, and the `per_user_cte_median_anchor` blended-mode section updated to state the native-keyed semantics, the bucket→source_tc mapping, and the classical→rapid choice. The T-94.4-10-02 security note (Python-controlled snapshot, no user-input surface) is preserved.
- Tests: new pure-Python equivalence test (all 4 buckets, exhaustive native probe sweep, nearest-anchor reconstruction within tolerance, blitz exactness, None-omission, and the rapid-inflation bug-repro). Repaired the A6 snapshot-row test to read a native-rapid-keyed row dynamically.

## Dead → Live Status Change

`convert_chesscom_to_lichess`, `_invert_intra_tc`, and `CHESSCOM_INTRA_TC` are now **LIVE** — referenced by the anchor pipeline through `composed_chesscom_to_lichess_grid`. They were previously exercised only by their own unit tests.

## Bug-Repro Confirmation

- Native chess.com **rapid** ~1461 now maps to ~1795 lichess-rapid (corrected) instead of the old ~1915 (blitz-keyed inflation). Asserted in `test_composed_grid_fixes_rapid_inflation_bug`.
- Native chess.com **bullet** 1800 now converts to 2064 (nearest-anchor on the composed bullet grid) instead of the old blitz-keyed 2000. Asserted in the repaired `test_b3_pure_chesscom_user_anchor` (DB-backed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Grid step changed from planned 25 to 15**
- **Found during:** Task 1
- **Issue:** With `_COMPOSED_GRID_STEP=25` the measured worst-case nearest-anchor error vs the converter was 26 pts (classical bucket, source_tc=rapid, high range where Table 1's rapid column is flat so a native-rapid step inverts to a larger Blitz step that Table 2 amplifies). That exceeds the 20-pt tolerance the equivalence test asserts.
- **Fix:** Set `_COMPOSED_GRID_STEP=15`, which caps the measured worst-case error at 16 pts across all 4 buckets, comfortably inside the 20-pt tolerance. The derivation is documented in the constant comment and the test tolerance comment (both record the empirical 25→26pt vs 15→16pt measurement).
- **Files modified:** `app/services/chesscom_to_lichess.py`, `tests/services/test_chesscom_to_lichess.py`
- **Commit:** 36e87c74

**2. [Rule 1 - Bug] Repaired `test_b3_pure_chesscom_user_anchor` (not in plan's files_modified)**
- **Found during:** Task 3 full pytest gate
- **Issue:** `tests/services/test_user_benchmark_percentiles_service.py::test_b3_pure_chesscom_user_anchor` is a DB-backed test that encoded the OLD blitz-keyed behavior: it seeded chess.com **bullet** games at native rating 1800 and asserted `anchor_rating == CHESSCOM_BLITZ_TO_LICHESS[1800]['bullet'] == 2000`. After the fix the correct value is 2064.
- **Fix:** Repointed the assertion to the nearest-anchor pick on `composed_chesscom_to_lichess_grid('bullet','bullet')` (mirroring the SQL `ORDER BY ABS(anchor - rating) LIMIT 1`), read dynamically so it self-updates. Updated the stale `_USER_RATING_BULLET` comment. The `test_b1_mixed_platform_user_blended_anchor` test (chess.com **blitz** at 2200) was unaffected because blitz is unchanged by the fix, and still passes.
- **Files modified:** `tests/services/test_user_benchmark_percentiles_service.py`
- **Commit:** 1632b17e

## Known Env-Dependent Failure (not a regression)

`tests/scripts/test_backfill_user_percentiles.py::test_backfill_target_prod_refuses_when_tunnel_down` fails in the full suite. This is the documented env-dependent failure (STATE.md): it fails only when the local prod tunnel is open on port 15432, which it was during execution (verified). It is unrelated to this change. All other 2108 tests pass; the targeted gate (`-k "chesscom or canonical_slice or user_rating_anchors"`) is 438 passed / 0 failed.

## Gates

- `uv run ruff format --check app/ tests/` — clean (187 files)
- `uv run ruff check app/ tests/` — All checks passed
- `uv run ty check app/ tests/` — All checks passed (zero errors)
- `uv run pytest` — 2108 passed, 16 skipped, 1 failed (the known prod-tunnel env failure above)

## HUMAN Follow-ups (DATA RECOMPUTE — do NOT gate on bin/reset_db.sh)

These are deliberate human steps. The dev DB now has stale anchors after this change; per CLAUDE.md and project memory, do **not** run `bin/reset_db.sh` or any DB reset.

1. **Recompute `user_rating_anchors`.** Existing rows for chess.com-containing users in the **bullet / rapid / classical** buckets are now stale (blitz unchanged). Recompute via `compute_anchors_for_user` (`app/services/user_benchmark_percentiles_service.py`) for affected users. Downstream `user_benchmark_percentiles` rows recompute from the new anchors.
2. **Regenerate the benchmark cohort CDF.** The benchmark CDF was built by this same SQL path, so a full correctness story implies regenerating benchmarks (`scripts/gen_global_percentile_cdf.py`). NOTE: the benchmark DB is Lichess-only by construction, so the cohort CDF's chess.com conversion path is not exercised there — the CDF impact is limited, but call it out for completeness. Do NOT attempt the regeneration in this task.

## Self-Check: PASSED

- `app/services/chesscom_to_lichess.py` — FOUND (composed_chesscom_to_lichess_grid present)
- `app/services/canonical_slice_sql.py` — FOUND (_BUCKET_TO_CHESSCOM_SOURCE_TC + composed grid wired)
- Commit 36e87c74 — FOUND
- Commit 64e1892d — FOUND
- Commit 1632b17e — FOUND
