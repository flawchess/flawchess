---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
plan: 01
subsystem: backend (schemas + services + tests)
tags: [phase-81, backend, endgame, aggregation, statistics, wave-1]
requires: []
provides:
  - "EndgamePerformanceResponse 6 new fields (entry-eval mean / n / p-value / CI low / CI high + endgame_score_p_value)"
  - "_get_endgame_performance_from_rows entry-eval aggregation backing the Phase 81 twin-tile section"
affects:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - tests/test_endgames_router.py
tech-stack:
  added: []
  patterns:
    - per-game dedupe over multi-class entry_rows (mirrors _compute_score_gap_material)
    - sign-flipped Wald-z one-sample mean test via existing compute_eval_confidence_bucket helper
    - Wilson score-test of WDL vs 50% via existing compute_confidence_bucket helper
    - reliability-gate-to-None on p-values when n < 10 (D-11)
key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - tests/test_endgames_router.py
decisions:
  - "Used min(game_rows, key=lambda r: r.endgame_class) for per-game pick — deterministic and mirrors priority-3 fallback in _compute_score_gap_material (Pitfall 1 / Pattern B)"
  - "Did not propagate `# ty: ignore` comment onto the lambda line — ty did not flag .endgame_class in lambda context, comment was unused"
  - "CI bound gate at n>=2 (mirroring stats_service Wald-z consumption pattern); n<2 surfaces None rather than synthesized zero spread"
metrics:
  duration_minutes: 16
  completed_date: 2026-05-09
  total_tasks: 4
  total_commits: 4
  files_modified: 4
---

# Phase 81 Plan 01: Backend — entry-eval / endgame-score aggregation Summary

Wires Phase 81's six new response fields onto the existing `/api/endgames/overview` payload by aggregating already-fetched entry rows in `_get_endgame_performance_from_rows`. No SQL changes (D-12 reuse mandate satisfied), no new repository function.

## What Shipped

1. **`EndgamePerformanceResponse` extended (D-11)** with six fields, all defaulted for backward compat (Pitfall 7):
   - `entry_eval_mean_pawns: float = 0.0`
   - `entry_eval_n: int = 0`
   - `entry_eval_p_value: float | None = None`
   - `endgame_score_p_value: float | None = None`
   - `entry_eval_ci_low_pawns: float | None = None`
   - `entry_eval_ci_high_pawns: float | None = None`

2. **`_get_endgame_performance_from_rows` aggregation (D-12)** — replaces the prior `del entry_rows` no-op:
   - Per-game dedupe via `defaultdict(list)` + `min(..., key=lambda r: r.endgame_class)` (Pattern B; Pitfall 1).
   - Mate-row exclusion: explicit `if eval_mate is not None: continue` (D-07; Pitfall 3).
   - NULL `eval_cp` exclusion: explicit `if eval_cp is None: continue` (Pitfall 3).
   - Sign-flip per `user_color` so positive = user is ahead (Pitfall 2; mirrors `_classify_endgame_bucket`).
   - Wald-z mean-vs-0 p-value via `compute_eval_confidence_bucket` (D-07).
   - Wilson score-test vs 50% p-value via `compute_confidence_bucket` (D-08).
   - p-values gated to `None` below n=10 / total<10 (Pitfall 5).
   - CI bounds (signed pawns) gated below n=2 where variance is undefined.

3. **Test coverage**:
   - `tests/test_endgame_service.py::TestEntryEvalAggregation` (9 tests): empty input defaults, n=9 gate, n=10 zero-mean p≈1.0, per-game dedupe, sign flip, mate exclusion, NULL exclusion, endgame-score p-value gate, CI bound exposure.
   - `tests/test_endgames_router.py::TestOverviewStartVsEndFields` (1 test): asserts all 6 keys present + correct types + empty-user default contract on `/api/endgames/overview`.

## Tasks (commits)

| Task | Name                                                              | Commit    | Files                                            |
| ---- | ----------------------------------------------------------------- | --------- | ------------------------------------------------ |
| 1    | Extend EndgamePerformanceResponse with 6 new fields               | `238ca00a`| `app/schemas/endgames.py`                        |
| 2    | RED — write failing TestEntryEvalAggregation (9 tests)            | `525e1e47`| `tests/test_endgame_service.py`                  |
| 3    | GREEN — implement entry-eval + endgame-score aggregation          | `08c7438c`| `app/services/endgame_service.py`                |
| 4    | API contract test for /api/endgames/overview new fields           | `d78f5f5b`| `tests/test_endgames_router.py`                  |

## Verification Results

```
uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py -x -q
  227 passed (211 service + 16 router)

uv run ty check app/ tests/
  All checks passed!

uv run ruff check app/ tests/
  All checks passed!
```

`entry_eval_mean_pawns` field-name occurrences: schemas=4, service=2, service-tests=7, router-tests=3. All four files reference the new contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Removed unused `# ty: ignore[unresolved-attribute]` on lambda line**
- **Found during:** Task 3 verification (`uv run ty check`)
- **Issue:** ty raised `unused-ignore-comment` warning on `min(game_rows, key=lambda r: r.endgame_class)  # ty: ignore[unresolved-attribute]`. Plan suggested mirroring the per-game dedupe pattern from `_compute_score_gap_material`, which carries the suppression on the `.append(row)` call (where it IS needed because `Sequence[Row | tuple]` parameter type makes attribute access ambiguous). On the `min(... lambda r: r.endgame_class)` call, ty does not flag the lambda — the suppression was pre-emptive and unused.
- **Fix:** Removed the `# ty: ignore` comment from the lambda line; kept the one on the preceding `.append()` line where it IS load-bearing.
- **Files modified:** `app/services/endgame_service.py`
- **Commit:** Folded into `08c7438c` (Task 3) — caught during the verify gate before commit.

No other deviations. The plan was executed as written.

## Authentication Gates

None — backend-only change with no external API or auth changes.

## Known Stubs

None. All six response fields are wired end-to-end from `entry_rows` aggregation through to JSON wire format. The `endgame_win_rate` field on the response is unchanged (existing).

## Self-Check

**Files exist:**
- `app/schemas/endgames.py` — FOUND
- `app/services/endgame_service.py` — FOUND
- `tests/test_endgame_service.py` — FOUND
- `tests/test_endgames_router.py` — FOUND

**Commits exist on branch (`worktree-agent-af4fc83142cfb74a6`):**
- `238ca00a` — FOUND
- `525e1e47` — FOUND
- `08c7438c` — FOUND
- `d78f5f5b` — FOUND

## Self-Check: PASSED
