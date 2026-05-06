---
phase: quick-260506-u2b
plan: 01
status: complete
date: 2026-05-06
---

# Quick Task 260506-u2b — Summary

Aligned the Openings **Insights** card (`OpeningFindingCard`) with the **Stats** card (`OpeningStatsCard`) layout. Insights now renders the shared `WDLChartRow` plus an MG-entry eval bullet row mirroring the Stats card, while preserving its score-zone left border and on-board candidate-move arrow color.

## What changed

### Backend
- `app/schemas/opening_insights.py` — added six MG-entry eval fields to `OpeningInsightFinding` (`avg_eval_pawns`, `eval_n`, `eval_ci_low_pawns`, `eval_ci_high_pawns`, `eval_confidence`, `eval_p_value`) and `eval_baseline_pawns_white` / `eval_baseline_pawns_black` to `OpeningInsightsResponse`.
- `app/services/opening_insights_service.py` — `_apply_eval_metrics_to_finding` helper + batched enrichment in `compute_insights()`. MG-entry eval data is computed by reusing the existing `query_opening_phase_entry_metrics_batch` helper from the Stats path (no duplicated SQL or aggregation logic) keyed on the `resulting_full_hash` of each finding.

### Frontend
- `frontend/src/types/insights.ts` — TS types mirror the backend additions.
- `frontend/src/components/insights/OpeningFindingCard.tsx` — replaced the legacy `MiniBulletChart` score bullet + `ScoreConfidencePopover` with `WDLChartRow`; added an MG-entry eval bullet row below it (same `MiniBulletChart` config + signed pawns text + `BulletConfidencePopover` as `OpeningStatsCard`); abbreviated prose to `Score X% after <move>`. Card border + arrow keep `scoreZoneColor(finding.score)`. Both mobile and desktop branches updated.
- `frontend/src/components/insights/OpeningInsightsBlock.tsx` — passes the per-color `evalBaselinePawns` prop down to each `OpeningFindingCard` (with a `FindingsKey` type alias to keep TS strict-mode happy on the build path).
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — tests cover new prose, WDL row, eval bullet, removal of the old score-bullet testid.

### Quality gates (all green)
- `uv run ruff check .` ✓
- `uv run ty check app/ tests/` ✓
- `uv run pytest tests/services/test_opening_insights_service.py tests/repositories/` ✓ (48 passed)
- `npm run lint` ✓ (0 errors)
- `npx vitest run` ✓ (281 passed across 24 files)
- `npm run knip` ✓
- `npm run build` ✓ (PWA + bundle generated)

`uv run ruff format --check .` flags 92 files, all unrelated to this task — pre-existing repo state.

## Commits

| Hash | Message |
|------|---------|
| `99b3a7b3` | docs(260506-u2b): pre-dispatch plan |
| `e9feae23` | feat(quick-260506-u2b): extend OpeningInsightFinding with MG-entry eval fields |
| `524aca88` | feat(quick-260506-u2b): refactor OpeningFindingCard to match OpeningStatsCard layout |
| `dfea82e2` | fix(quick-260506-u2b): narrow FindingsKey type to avoid TS error on build |
| `d8526fcd` | style(quick-260506-u2b): ruff format backend files |
| `37c37bb4` | chore: merge quick task worktree (260506-u2b) |

## Constraints honored

- `frontend/src/components/stats/OpeningStatsCard.tsx` untouched (`git diff 99b3a7b3..HEAD -- ...` returns empty).
- Card primary color zone stays score-driven; only the new inner eval bullet row uses eval-zone semantics.
- MG-eval computation reuses the Stats helper (`query_opening_phase_entry_metrics_batch`) — no parallel SQL.
