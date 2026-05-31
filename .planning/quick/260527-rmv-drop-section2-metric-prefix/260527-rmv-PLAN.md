---
quick_id: 260527-rmv
type: plan
created: 2026-05-27
---

# Quick Task 260527-rmv: Drop `section2_` prefix from metric names

## Goal

Remove the `section2_` prefix from metric names across the codebase. The
prefix was historical from when the conv/parity score-gap metrics lived
under "Section 2" of the endgame analytics page. The naming was
inconsistent with the third bucket (`recovery_score_gap`, prefix-free)
and with the rest of the metric family. Dropping the prefix gives a
clean `score_gap_{conv,parity,recov}` triad without collision.

## Scope

- DB enum: `benchmark_metric` values `section2_score_gap_conv` →
  `score_gap_conv`, `section2_score_gap_parity` → `score_gap_parity`
  (alembic migration with `ALTER TYPE ... RENAME VALUE ...`).
- Python: `CdfMetricId` Literal, `MetricId` Literal, Pydantic schema
  fields on `ScoreGapMaterialResponse`, all service code, helper
  functions (`per_user_cte_section2` → `per_user_cte_score_gap_bucket`,
  `_SECTION2_BUCKETS` → `_SCORE_GAP_BUCKETS`,
  `SECTION2_MIN_SPANS_PER_BUCKET` → `SCORE_GAP_BUCKET_MIN_SPANS`).
- Frontend: types, components, generated `endgameZones.ts` exports
  (`SECTION2_SCORE_GAP_*` → `SCORE_GAP_*`), `SECTION2_DISPLAY_SHIFT` →
  `SCORE_GAP_BUCKET_DISPLAY_SHIFT`, local var simplification.
- Test fixtures: 8 SQL golden files renamed
  (`section2_score_gap_conv__{tc}.sql` → `score_gap_conv__{tc}.sql`,
  same for parity).
- LLM prompt template: glossary identifiers updated.

## Out of scope

- Historical alembic migration files (`20260524…`, `20260526…`)
  preserved as-is — they represent past schema state.
- `.planning/`, `reports/`, `CHANGELOG.md` historical narrative
  preserved.
- Long version-history string in `_PROMPT_VERSION` (insights_llm.py)
  preserved — it's a historical changelog.

## Verification

- No collisions verified: `score_gap_{conv,parity,recov,skill}` did
  not exist anywhere prior.
- `ruff format`, `ruff check`, `ty check app/ tests/`,
  `uv run pytest` (2176 passed), `npm run lint`, `npm test`
  (673 passed), `npm run build`, `npm run knip`.
- Alembic upgrade applied cleanly to dev DB.
- `gen_endgame_zones_ts.py` regen produces no drift beyond the
  intended rename.
