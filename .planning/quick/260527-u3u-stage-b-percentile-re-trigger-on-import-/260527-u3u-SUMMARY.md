---
quick_id: 260527-u3u
status: complete
completed: 2026-05-27
commit: 696db1df
files_modified:
  - app/services/import_service.py (+27 / -1)
  - tests/services/test_import_service.py (+155 / -1, incl. asyncio import)
  - CHANGELOG.md (+4)
---

# Quick 260527-u3u — Stage B Percentile Re-Trigger on Import Completion

## Outcome

Closed the stale-Stage-B gap for Stage-5c-covered incremental imports by adding a second Stage B trigger inside `_complete_import_job` (gated on the existing `users_with_zero_pending` check). The cold-drain trigger at `eval_drain.py:566-568` is preserved unchanged; both sites are idempotent (Stage A/B write disjoint rows, `compute_stage_b` is upsert-safe).

## Changes

1. **`app/services/import_service.py`** — imported `compute_stage_b` alongside `compute_stage_a` (line 37) and inserted a Stage B trigger block immediately after the existing Stage A spawn in `_complete_import_job`. The block opens a fresh `async_session_maker()` read session (mirrors the eval_drain pattern), calls `game_repository.users_with_zero_pending(read_session, [job.user_id])`, and schedules `asyncio.create_task(compute_stage_b(job.user_id))` only when the result is non-empty. Wrapped in `try / except asyncio.CancelledError: raise / except Exception` that captures to Sentry with `set_context("percentile_compute", {"user_id", "stage": "B", "trigger": "import_complete"})` and does not propagate.

2. **`tests/services/test_import_service.py`** — three new unit tests at the end of the file under the `Stage B import-complete trigger (quick-260527-u3u)` section:
   - `test_stage_b_fires_on_import_complete_when_zero_pending` — proves Stage B is scheduled exactly once and Stage A is still scheduled.
   - `test_stage_b_does_not_fire_when_pending_remains` — proves Stage B is NOT scheduled when the gate returns `[]`, while Stage A still fires.
   - `test_stage_b_gate_exception_is_swallowed_and_captured` — proves a `RuntimeError` from the gate is captured to Sentry exactly once and does not propagate; Stage A still fires; Stage B does not.

3. **`CHANGELOG.md`** — added a `### Fixed` bullet under `## [Unreleased]` documenting the fix.

## Pre-PR gate results

| Gate                                                                                   | Result                                                          |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `uv run ruff format app/ tests/`                                                       | 184 files left unchanged (after one reformat by ruff during run) |
| `uv run ruff check app/ tests/ --fix`                                                  | All checks passed                                               |
| `uv run ty check app/ tests/`                                                          | All checks passed (zero errors)                                 |
| `uv run pytest tests/services/test_import_service.py -x`                               | 7 passed                                                        |
| `uv run pytest tests/services/test_eval_drain.py tests/services/test_eval_drain_stage_b.py -x` | 14 passed, 4 skipped (pre-existing stubs, unrelated)            |

## Deviations from plan

None. Plan executed as written. One incidental observation: the regression-target file `tests/services/test_eval_drain.py` carries a pre-existing benign pytest warning (`test_gather_outside_session` is marked `@pytest.mark.asyncio` but is sync) — out of scope, logged here for awareness only.

## Constraints honoured

- Cold-drain Stage B trigger at `eval_drain.py:566-568` is **untouched**.
- Stage A trigger is **untouched**.
- Stage 5c marking logic in `_flush_batch` is **untouched**.
- No DB migration added.
- No frontend changes.
- Sentry capture in the new block does **not** re-raise; `asyncio.CancelledError` propagates per the lifespan-shutdown contract (mirrors WR-07).

## Manual verification (post-deploy, not a plan gate)

The fix is observable on prod by triggering a small incremental import for an affected user and confirming both Stage A and Stage B `computed_at` columns in `user_benchmark_percentiles` advance together (rather than diverging by hours as observed for user 28 on 2026-05-27).
