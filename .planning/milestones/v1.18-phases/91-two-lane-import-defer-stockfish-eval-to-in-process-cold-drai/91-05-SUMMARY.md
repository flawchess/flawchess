---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "05"
subsystem: infra
tags:
  - lifespan
  - background-task
  - fastapi
  - asyncio

dependency_graph:
  requires:
    - "91-02 (app/services/eval_drain.py with run_eval_drain() coroutine)"
  provides:
    - "app/main.py lifespan wiring for run_eval_drain as a named asyncio task"
    - "tests/test_main_lifespan.py lifespan smoke test for both background tasks"
  affects:
    - "Backend startup/shutdown lifecycle — eval drain now active on every boot"

tech_stack:
  added: []
  patterns:
    - "Parallel task cancellation: cancel() both tasks before awaiting either so cancellation enters in parallel"
    - "stop_engine() unconditionally runs last via inner try/finally after both task awaits"
    - "app.router.lifespan_context(app) for driving FastAPI lifespan in tests (no asgi-lifespan dep)"
    - "Monkeypatch logger.exception directly for reliable async test log capture"

key_files:
  created:
    - "tests/test_main_lifespan.py"
  modified:
    - "app/main.py"

key-decisions:
  - "Both reaper_task and drain_task are cancelled before either is awaited so cancellation enters in parallel (not sequential)"
  - "stop_engine() runs in the inner try/finally so it is unconditionally the LAST teardown step (T-91-20 ordering gate)"
  - "Used app.router.lifespan_context(app) to drive the lifespan in tests rather than adding asgi-lifespan as a new dev dependency"
  - "await asyncio.sleep(0) inside lifespan context required to let tasks start before checking they were called"
  - "Monkeypatched logger.exception directly (not caplog) for reliable capture in session-scoped async event loop"

requirements-completed:
  - "Phase 91 Scope #3 (cold-lane drain wired in lifespan)"
  - "CONTEXT.md D-13 (drain runs alongside run_periodic_reaper, not as a separate process)"

duration: 8min
completed: "2026-05-21"
---

# Phase 91 Plan 05: Lifespan Wiring for run_eval_drain Summary

**FastAPI lifespan wires `run_eval_drain` as a named asyncio task alongside `run_periodic_reaper`; both are cancelled in parallel on shutdown with `stop_engine()` running unconditionally last.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-21T02:20:00Z
- **Completed:** 2026-05-21T02:33:56Z
- **Tasks:** 2
- **Files modified:** 1 (app/main.py), 1 created (tests/test_main_lifespan.py)

## Accomplishments

- `run_eval_drain` is now spawned as `asyncio.create_task(..., name="eval-drain")` immediately after `reaper_task` in the lifespan, activating the cold lane on every backend boot.
- Both tasks are cancelled before either is awaited (parallel cancellation pattern), with `stop_engine()` guaranteed to run last via the inner `try/finally` block (T-91-20 ordering gate).
- Two lifespan smoke tests verify: (1) both tasks are spawned at startup, (2) a drain-side RuntimeError on shutdown is caught and logged via `logger.exception`, not propagated.

## Task Commits

1. **Task 5.1: Add drain_task to lifespan alongside reaper_task** - `bad78f1b` (feat)
2. **Task 5.2: Lifespan smoke test** - `a10d4a94` (test)

## Files Created/Modified

- `app/main.py` — Added `from app.services.eval_drain import run_eval_drain` import; added `drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")` spawn; added parallel cancel + await + exception logging for drain_task in finally block; updated comment to document T-91-20 ordering gate.
- `tests/test_main_lifespan.py` (new) — Two smoke tests: `test_both_background_tasks_spawned` and `test_drain_task_exception_on_shutdown_is_logged`. No real DB or engine connections; uses stubs and `app.router.lifespan_context(app)`. Constants: `EXPECTED_TASKS`, `STUB_SLEEP_SECONDS`. Runs in 0.10s wall time.

## Decisions Made

- **Parallel cancellation order:** Both `reaper_task.cancel()` and `drain_task.cancel()` appear before any `await reaper_task` or `await drain_task`. This is the plan's required shape — cancellation enters both tasks concurrently rather than serially.
- **`stop_engine()` placement:** Stays in the inner `finally:` block so it runs even if `await drain_task` raises a non-CancelledError. This is the T-91-20 ordering gate.
- **Test approach — `app.router.lifespan_context(app)` over `asgi-lifespan`:** The `asgi-lifespan` package was not in the project's dev dependencies. FastAPI's own `lifespan_context` is equally capable for this use case and avoids adding a new transitive dep.
- **`await asyncio.sleep(0)` in tests:** `asyncio.create_task()` schedules a coroutine but does not run it before the first yield. The tests call `await asyncio.sleep(0)` inside the context to give the stubs a chance to execute their first line (setting `called` flags, entering their sleep).
- **Logger monkeypatching over `caplog`:** In the project's session-scoped async event loop, `caplog` did not reliably capture records from `logger.exception()` called inside `await`ed tasks. Patching `main_module.logger.exception` directly is more reliable and correctly typed.

## Deviations from Plan

None — plan executed exactly as written. The plan's PATTERNS.md verbatim block for the modified lifespan was followed precisely.

## Known Stubs

None — `app/main.py` changes are fully wired. The drain task is a live coroutine from `app/services/eval_drain.py`.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The only change is wiring an existing internal coroutine (`run_eval_drain`) into the existing lifespan task management pattern. T-91-19 (drain task hangs on shutdown) is mitigated by `task.cancel()` + the drain's non-catching of `CancelledError`. T-91-20 (stop_engine before drain await) is mitigated by the `finally:` ordering confirmed in acceptance criteria.

## Self-Check: PASSED

- `app/main.py` modified: confirmed
- `tests/test_main_lifespan.py` created: confirmed
- Task 5.1 commit `bad78f1b` exists: confirmed
- Task 5.2 commit `a10d4a94` exists: confirmed
- `grep -c "from app.services.eval_drain import run_eval_drain" app/main.py` = 1: confirmed
- `grep -c 'asyncio.create_task(run_eval_drain()' app/main.py` = 1: confirmed
- `grep -c 'name="eval-drain"' app/main.py` = 1: confirmed
- `grep -c "drain_task.cancel()" app/main.py` = 1: confirmed
- `grep -c "await drain_task" app/main.py` = 1: confirmed
- Both cancel() calls appear before any await (lines 79-80 before lines 83, 89): confirmed
- `await stop_engine()` is last statement in outer finally (line 95): confirmed
- `uv run pytest tests/test_main_lifespan.py -x`: 2/2 PASSED in 0.10s
- `uv run ty check app/main.py tests/test_main_lifespan.py`: All checks passed
- `uv run ruff check app/main.py tests/test_main_lifespan.py`: All checks passed
- Full suite (excluding pre-existing failures): 1601 passed, 6 skipped

---
*Phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai*
*Completed: 2026-05-21*
