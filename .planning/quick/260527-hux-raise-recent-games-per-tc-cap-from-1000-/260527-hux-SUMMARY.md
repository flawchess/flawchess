---
type: quick
slug: hux-raise-recent-games-per-tc-cap-from-1000
status: complete
completed: 2026-05-27
branch: gsd/phase-94.4-peer-relative-percentile-chip-refinement
commits:
  - 9d2dec13  # chore(canonical-slice): raise RECENT_GAMES_PER_TC_CAP 1000 -> 3000
  - f03da4f3  # copy(percentile-chip): update tooltip + explainer to recent 3000 games
---

# Raise RECENT_GAMES_PER_TC_CAP 1000 -> 3000 — Summary

## What changed

Bumped `RECENT_GAMES_PER_TC_CAP` in `app/services/canonical_slice_sql.py` from `1000` to `3000`, and cascaded the new number through every docstring, frontend tooltip / explainer string, and test assertion that hardcoded "1000" in the recent-games-per-TC context.

Purpose: heavy single-users (e.g. user 8 with 5861 eligible blitz endgame games) currently have ~82% of their data discarded by the 1000-cap. Lifting the cap to 3000 keeps roughly 3x more games in the per-user chip computation without changing methodology.

## Files touched

**Task 1 — backend (commit `9d2dec13`):**

- `app/services/canonical_slice_sql.py` — constant bump + 5 docstring/comment cascades (module docstring, `_recent_capped_cte`, `_recent_capped_per_tc_cte`, `per_user_cte_score_gap`, `per_user_cte_median_anchor`, plus the inline `<= 1000` reference in the pooled-aggregate shape block).
- `app/services/user_benchmark_percentiles_service.py` — docstring "recent-1000 ×" -> "recent-3000 ×".
- `app/models/user_rating_anchors.py` — 3 docstring updates (module-level + class-attr docstring).
- `app/models/user_benchmark_percentile.py` — docstring "TC's recent-1000 pool" -> "TC's recent-3000 pool".
- `scripts/backfill_user_percentiles.py` — docstring "recent-1000 × 36-month pool" -> "recent-3000 × 36-month pool".
- `tests/services/test_canonical_slice_sql.py` — class docstring + 2 test names / failure messages; one test renamed (`test_recent_1000_per_tc_cap_substrings_present` -> `test_recent_per_tc_cap_substrings_present`).
- `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` — replaced hardcoded `assert "<= 1000" in sql` with `assert f"<= {RECENT_GAMES_PER_TC_CAP}" in sql` (now references the constant, so future bumps don't break this test again).
- `tests/scripts/fixtures/global_percentile_cdf/*.sql` (32 fixtures) — regenerated via the snippet in the canary test's module docstring (intentional drift; required by the canary contract).

**Task 2 — frontend (commit `f03da4f3`):**

- `frontend/src/components/charts/PercentileChip.tsx` — tooltip bullet 2 (per-TC and aggregated variants).
- `frontend/src/pages/Endgames.tsx` — percentile-badge explainer steps 1 and 3.
- `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` — 2 `it(...)` titles + 2 `expect(body).toContain(...)` assertions.
- `frontend/src/types/endgames.ts` — TSDoc example strings for `PercentileBadgeRatingAnchorDisclosure` (caught off-plan; same `last 1000 games / 36 months` cascade).

## Commits

| SHA        | Subject                                                              |
| ---------- | -------------------------------------------------------------------- |
| `9d2dec13` | `chore(canonical-slice): raise RECENT_GAMES_PER_TC_CAP 1000 -> 3000` |
| `f03da4f3` | `copy(percentile-chip): update tooltip + explainer to recent 3000 games` |

## Deviations from plan

1. **Plan said "No SUMMARY.md required (quick task)"** — overridden per orchestrator instructions; quick tasks DO require a SUMMARY.md.

2. **Extra in-scope sites the plan's grep missed** (Rule 3, blocking fixes — the plan's verify regex would have failed without them, or the tests would have failed):
   - `app/services/canonical_slice_sql.py` line 47 — inline `played_at DESC <= 1000` reference in the module-level "Pooled-aggregate shape" block.
   - `tests/services/test_canonical_slice_sql.py` lines 148, 152, 163 — class docstring "1000-per-TC cap", test method name `test_recent_1000_per_tc_cap_substrings_present`, and failure message string. Test was renamed and the message generalised.
   - `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` lines 106, 111 — `assert "<= 1000" in sql` (hardcoded literal) was failing once the constant changed. Replaced with `assert f"<= {RECENT_GAMES_PER_TC_CAP}" in sql` so the assertion tracks the constant for any future bump.
   - `frontend/src/types/endgames.ts` lines 349, 354 — TSDoc example strings for the per-TC rating-anchor disclosure type referenced "last 1000 games / 36 months" twice. Both updated to "last 3000 games / 36 months".

3. **Canary fixture regen** — `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` is an intentional drift canary; its module docstring explicitly documents the regen snippet for the exact situation we hit (`SQL surface changes intentionally`). The 32 fixtures under `tests/scripts/fixtures/global_percentile_cdf/` were regenerated with the documented snippet. No test logic change.

## Cohort regen NOT performed

The cohort CDF (`global_percentile_cdf`) was deliberately NOT regenerated. Rationale: benchmark users are imported at `max_games=1000` per TC at ingest time (`scripts/import_benchmark_users.py` passes that to the Lichess API), so the 3000-cap is non-binding for cohort CDF rows — `benchmark_user_metric_values_v1` would produce identical output. The cap bump only relaxes the per-user pool.

## Test results

- `uv run ruff format app/ tests/ scripts/` — clean, 196 files left unchanged.
- `uv run ruff check app/ tests/ scripts/ --fix` — all checks passed.
- `uv run ty check app/ tests/` — all checks passed.
- `uv run pytest --deselect tests/scripts/test_backfill_user_percentiles.py::test_backfill_target_prod_refuses_when_tunnel_down` — **2176 passed, 16 skipped, 1 deselected**. The deselected test is environment-dependent (asserts `localhost:15432` has no listener); Adrian currently has the prod tunnel up via `bin/prod_db_tunnel.sh`, which makes the test report a false failure. Unrelated to this change.
- `cd frontend && npm run lint` — clean.
- `cd frontend && npm test -- --run` — **675 passed (56 files)**.

## Follow-ups (not in this task)

- The `least()` symmetry referenced in `canonical_slice_sql.py:683` is still deferred per the plan note.
- The per-user anchor rows (`user_rating_anchors`) refresh organically on the next import / eval drain; no backfill triggered here.
- If/when the benchmark Lichess-ingest cap is also lifted past 1000, the cohort CDF would then need regenerating — out of scope for this quick task.
