---
quick_id: 260527-rmv
type: summary
status: complete
completed: 2026-05-27
files_modified: 36
files_renamed: 8
new_files: 3
tags: [refactor, rename, db-enum, metrics, score-gap]
---

# Quick Task 260527-rmv: Drop `section2_` prefix from metric names

## One-liner

Renamed the `section2_score_gap_{conv,parity,recov,skill}` metric family
to `score_gap_{conv,parity,recov,skill}` end-to-end: DB enum (alembic
`ALTER TYPE ... RENAME VALUE`), Pydantic schema fields, `CdfMetricId` /
`MetricId` literals, all service helpers (`per_user_cte_section2` →
`per_user_cte_score_gap_bucket`), frontend types/components/generated
zones, LLM prompt glossary identifiers, and 8 SQL golden fixtures.
No collisions, no behavior change.

## What shipped

- **Alembic migration** `4c42ebc87b7f_rename_section2_benchmark_metric_values.py`:
  two `ALTER TYPE benchmark_metric RENAME VALUE ...` statements (non-
  destructive, preserves all rows).
- **DB enum (ORM)** `app/models/user_benchmark_percentile.py`:
  `benchmark_metric_enum` values updated to match the renamed Postgres
  ENUM.
- **Python identifier renames** (across 23 files):
  - Metric IDs: `section2_score_gap_conv/parity/recov/skill` →
    `score_gap_conv/parity/recov/skill` in `CdfMetricId` and `MetricId`
    Literals and all f-string `getattr(..., f"…_{bucket_id}_…")` sites.
  - SQL helpers: `per_user_cte_section2(_tc)` →
    `per_user_cte_score_gap_bucket(_tc)`; non-TC variant and per-TC
    variant updated in lockstep across the service, scripts, and tests.
  - Constants: `_SECTION2_BUCKETS` → `_SCORE_GAP_BUCKETS`,
    `SECTION2_MIN_SPANS_PER_BUCKET` → `SCORE_GAP_BUCKET_MIN_SPANS`.
- **Pydantic schema** `app/schemas/endgames.py`: 24 fields on
  `ScoreGapMaterialResponse` renamed
  (`section2_score_gap_{conv,parity,recov,skill}_{mean,n,p_value,ci_low,ci_high,percentile}`
  → `score_gap_*`).
- **Frontend** `frontend/src/types/endgames.ts` + components +
  `generated/endgameZones.ts`:
  - `SECTION2_SCORE_GAP_*_NEUTRAL_{MIN,MAX}` exports renamed.
  - `SECTION2_DISPLAY_SHIFT` → `SCORE_GAP_BUCKET_DISPLAY_SHIFT`.
  - Local vars `section2NeutralMin/Max` in `EndgameMetricCard.tsx`
    simplified to `neutralMin/Max`.
- **Test fixtures**: 8 SQL goldens under
  `tests/scripts/fixtures/global_percentile_cdf/` renamed via
  `git mv` (`section2_score_gap_conv__{bullet,blitz,rapid,classical}.sql`
  → `score_gap_conv__*.sql`, same for parity).
- **LLM prompt** `app/prompts/endgame_insights.md`: glossary
  identifiers `(section2_score_gap_*)` → `(score_gap_*)` for the 4
  bucket metrics.

## Why

The `section2_` prefix was historical from when conv/parity/recov
lived under "Section 2" of the endgame analytics page. The naming
was inconsistent:

- `section2_score_gap_conv` (prefixed) vs `recovery_score_gap`
  (prefix-free) inside the same metric family.
- ORM enum (`recovery_score_gap`) vs Pydantic schema
  (`section2_score_gap_recov_mean`) — same metric, two names.
- `_SECTION2_BUCKETS`, `SECTION2_DISPLAY_SHIFT`,
  `per_user_cte_section2` — UI-section terminology leaking into
  domain-level identifiers.

Dropping the prefix gives a clean `score_gap_{conv,parity,recov}`
triad. No collisions: `score_gap_{conv,parity,recov,skill}` did not
exist as identifiers anywhere prior.

## Files modified

Backend (Python): `app/models/user_benchmark_percentile.py`,
`app/prompts/endgame_insights.md`, `app/schemas/endgames.py`,
`app/services/canonical_slice_sql.py`,
`app/services/endgame_service.py`, `app/services/endgame_zones.py`,
`app/services/global_percentile_cdf.py`,
`app/services/insights_llm.py`, `app/services/insights_service.py`,
`app/services/user_benchmark_percentiles_service.py`,
`scripts/backfill_user_percentiles.py`,
`scripts/gen_endgame_zones_ts.py`,
`scripts/gen_global_percentile_cdf.py`.

Backend tests (15 files):
`tests/integration/test_benchmark_metric_enum.py`,
`tests/repositories/test_user_benchmark_percentiles_repository.py`,
`tests/schemas/test_endgames_schema.py`,
`tests/scripts/test_backfill_user_percentiles.py`,
`tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`,
`tests/services/test_canonical_slice_sql.py`,
`tests/services/test_endgame_service_chip_decoupling.py`,
`tests/services/test_endgame_zones.py`,
`tests/services/test_insights_llm.py`,
`tests/services/test_insights_service.py`,
`tests/services/test_user_benchmark_percentiles_service.py`,
`tests/services/test_user_benchmark_percentiles_service_real_data.py`,
`tests/test_endgame_service.py`, `tests/test_endgames_router.py`.

Frontend: `frontend/src/__tests__/noEndgameSkillString.test.tsx`,
`frontend/src/components/charts/EndgameMetricCard.tsx`,
`frontend/src/components/charts/EndgameMetricsSection.tsx`,
`frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx`,
`frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx`,
`frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx`,
`frontend/src/generated/endgameZones.ts`,
`frontend/src/lib/__tests__/scoreBulletShift.test.ts`,
`frontend/src/lib/endgameMetrics.ts`,
`frontend/src/types/endgames.ts`.

New: `alembic/versions/20260527_080000_4c42ebc87b7f_rename_section2_benchmark_metric_values.py`,
`.planning/quick/260527-rmv-drop-section2-metric-prefix/260527-rmv-PLAN.md`,
`.planning/quick/260527-rmv-drop-section2-metric-prefix/260527-rmv-SUMMARY.md`.

Renamed: 8 SQL golden fixtures under
`tests/scripts/fixtures/global_percentile_cdf/`.

## Out of scope (deliberately untouched)

- Historical alembic migrations (`20260524_000000_*.py`,
  `20260526_000000_*.py`, `20260526_222651_*.py`) — they represent
  past schema state at their respective points in time.
- `.planning/`, `reports/`, `CHANGELOG.md` — historical narrative
  preserved.
- The long version-history changelog inside `_PROMPT_VERSION` in
  `app/services/insights_llm.py` — historical entries reference
  `section2_*` metric names that existed at the time.

## Gates

- `uv run ruff format app/ tests/ scripts/` — clean (4 files reformatted
  by sed-fallout, then clean).
- `uv run ruff check app/ tests/ scripts/ --fix` — All checks passed.
- `uv run ty check app/ tests/` — All checks passed.
- `uv run pytest` — 2176 passed, 16 skipped, 1 env-dependent test
  deselected (`test_backfill_target_prod_refuses_when_tunnel_down`,
  fails on Adrian's machine because the prod tunnel is currently open
  on port 15432 — pre-existing environment dependency, unrelated to
  the rename).
- `npm run lint` — clean.
- `npm test -- --run` — 673 passed.
- `npm run build` — clean.
- `npm run knip` — clean (no dead exports introduced).
- `uv run alembic upgrade head` — migration `4c42ebc87b7f` applied
  cleanly to dev DB.
- `uv run python scripts/gen_endgame_zones_ts.py` — regenerated; no
  drift beyond the intended rename (7 lines, all
  `SECTION2_SCORE_GAP_*` → `SCORE_GAP_*`).
