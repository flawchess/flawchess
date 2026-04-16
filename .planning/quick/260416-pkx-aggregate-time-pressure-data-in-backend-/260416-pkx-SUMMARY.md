---
quick_id: 260416-pkx
type: execute
status: complete
completed_date: 2026-04-16
commits:
  - 994d617: "test(260416-pkx): add failing tests for pooled time pressure response"
  - e5d3654: "feat(260416-pkx): pool time pressure chart across time controls in backend"
  - aa1bc56: "refactor(260416-pkx): drop frontend aggregateSeries, consume pooled backend shape"
tdd_gates:
  red: 994d617
  green: e5d3654
  refactor: aa1bc56
key_files:
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/pages/Endgames.tsx
metrics:
  tests_added: 1
  tests_updated: 15
  backend_tests_pass: 722
  frontend_tests_pass: 73
---

# Quick 260416-pkx: Aggregate Time Pressure Data in Backend — Summary

Moved the weighted-average aggregation for the Time Pressure vs Performance chart from the frontend into the backend. The backend now returns a single pooled `user_series` + `opp_series` (10 buckets each) across all time controls that pass `MIN_GAMES_FOR_CLOCK_STATS`, dropping the per-time-control rows the frontend previously re-aggregated.

## Before → After Shape of `TimePressureChartResponse`

### Before (per-TC rows, frontend re-aggregated)

```python
class TimePressureChartRow(BaseModel):
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str
    total_endgame_games: int
    user_series: list[TimePressureBucketPoint]   # 10
    opp_series: list[TimePressureBucketPoint]    # 10

class TimePressureChartResponse(BaseModel):
    rows: list[TimePressureChartRow]
```

### After (flat pooled shape)

```python
class TimePressureChartResponse(BaseModel):
    user_series: list[TimePressureBucketPoint]   # 10, pooled across qualifying TCs
    opp_series: list[TimePressureBucketPoint]    # 10, pooled across qualifying TCs
    total_endgame_games: int                     # sum across qualifying TCs
```

`TimePressureChartRow` was deleted from both the Pydantic schema (`app/schemas/endgames.py`) and the TypeScript mirror (`frontend/src/types/endgames.ts`).

## What Changed on the Frontend

- Deleted the `aggregateSeries()` helper in `EndgameTimePressureSection.tsx` (~30 lines). Its weighted-average formula (`score_sum += pt.score * pt.game_count`, `scoredCount += pt.game_count`, `score = scoredCount > 0 ? scoreSum / scoredCount : null`) is now implemented by `_compute_time_pressure_chart` in `app/services/endgame_service.py` — identical math, same boundary behaviour.
- Removed the `TimePressureChartRow` interface from `frontend/src/types/endgames.ts`.
- `buildChartData` is now a simple index-aligned map over `data.user_series` / `data.opp_series`.
- Empty-state guard switched from `data.rows.length === 0` to `data.total_endgame_games === 0`. The `Endgames.tsx` `showTimePressureChart` flag follows the same field.
- Removed the now-unused `TimePressureBucketPoint` import from `EndgameTimePressureSection.tsx`; the type is still exported from `types/endgames.ts` as a member of the response schema.

## Where `MIN_GAMES_FOR_RELIABLE_STATS` Lives Now

Still on the frontend, in `buildChartData`. Intentional: this threshold is a **render-time visual suppression gate** ("don't draw a dot for buckets with fewer than 10 games") — it's a display concern, not a data concern. Keeping it on the frontend means the backend stays unaware of presentation thresholds, and future UI variants (e.g. a denser debug view) can choose their own floor without needing a new API surface. Note this is distinct from `MIN_GAMES_FOR_CLOCK_STATS`, which gates whole time controls at the aggregation step (backend concern).

## New Backend Test Result

`tests/test_endgame_service.py::TestComputeTimePressureChart::test_user_and_opp_game_count_totals_are_equal` — PASSED.

Builds 22 fixture games across two time controls (10 bullet + 12 rapid) with mixed colors, mixed W/D/L, and clocks that place user and opponent in different buckets. Asserts:

```python
sum(p.game_count for p in result.user_series) == sum(p.game_count for p in result.opp_series) == 22
```

This enforces same-game symmetry: every endgame contributes exactly one data point to the user series and one to the opponent series, so the totals must match by construction. If a future change in bucketing, clamping, or filtering accidentally skips one side of the pair (user-only or opp-only exclusion), the invariant catches it.

## Verification Battery

| Check                            | Result                   |
| -------------------------------- | ------------------------ |
| `uv run ruff check .`            | Pass                     |
| `uv run ty check app/ tests/`    | Pass (zero errors)       |
| `uv run pytest`                  | 722 passed, 1 skipped    |
| `cd frontend && npm run lint`    | Pass                     |
| `cd frontend && npm run build`   | Pass                     |
| `cd frontend && npm run knip`    | Pass (no dead exports)   |
| `cd frontend && npm test`        | 73 passed                |
| Grep `TimePressureChartRow`      | 0 hits (app/tests/frontend) |
| Grep `aggregateSeries`           | 0 hits (frontend/src)    |
| Grep `time_pressure_chart.*\.rows` | 0 hits (app/tests/frontend) |

## Deviations from Plan

None structurally — plan executed as written. One minor cleanup beyond the plan:

- **[Rule 2 - Hygiene]** After the initial rewrite of `buildChartData`, the refactor comment mentioned the deleted `aggregateSeries()` helper by name, which would have left a single grep hit for `aggregateSeries` in the final verification. Reworded the comment so the Task 3 grep returns zero hits as specified. Captured in the same commit (`aa1bc56`).

## TDD Gate Compliance

| Gate     | Commit   | Message                                                                        |
| -------- | -------- | ------------------------------------------------------------------------------ |
| RED      | 994d617  | `test(260416-pkx): add failing tests for pooled time pressure response`        |
| GREEN    | e5d3654  | `feat(260416-pkx): pool time pressure chart across time controls in backend`   |
| REFACTOR | aa1bc56  | `refactor(260416-pkx): drop frontend aggregateSeries, consume pooled backend shape` |

RED commit's test changes were verified to fail against the pre-change service (`AttributeError: 'TimePressureChartResponse' object has no attribute 'total_endgame_games'`). GREEN commit's service rewrite made all 17 chart tests pass. REFACTOR commit shrank the frontend component without changing behaviour.

## Known Stubs

None. No placeholder data, hardcoded empty values, or TODO/FIXME markers introduced.

## Self-Check: PASSED

- File `app/schemas/endgames.py`: FOUND
- File `app/services/endgame_service.py`: FOUND
- File `tests/test_endgame_service.py`: FOUND
- File `frontend/src/types/endgames.ts`: FOUND
- File `frontend/src/components/charts/EndgameTimePressureSection.tsx`: FOUND
- File `frontend/src/pages/Endgames.tsx`: FOUND
- Commit 994d617: FOUND
- Commit e5d3654: FOUND
- Commit aa1bc56: FOUND
