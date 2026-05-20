---
phase: 90-import-pipeline-memory-leak-fix-resilience
reviewed: 2026-05-20T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/main.py
  - app/repositories/import_job_repository.py
  - app/services/import_service.py
  - tests/test_import_service.py
findings:
  critical: 1
  warning: 7
  info: 5
  total: 13
status: issues_found
---

# Phase 90: Code Review Report

**Reviewed:** 2026-05-20
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 90 ships three substantive changes: (1) Stage 5 `_flush_batch` rewrite from `case()+IN` to two `bindparam` executemany groups (memory-leak fix); (2) three-scope `AsyncSession` lifecycle in `run_import` (bootstrap / per-batch / completion) to bound session lifetime; (3) a periodic orphan-job reaper and a bounded-retry helper for failure-state recording.

The executemany rewrite is correctly implemented — bind-param shape is invariant across batches, `result_fen=None` games are correctly excluded from group (b), and the SQL injection surface is zero (all values pass through SQLAlchemy bind params, no string interpolation). The reaper is wired into the FastAPI lifespan and uses the `IMPORT_TIMEOUT_SECONDS` threshold to avoid killing live imports.

However, several defects warrant attention. The most important one is a **silent data-loss path** in the new bootstrap-scope structure: if anything fails before the bootstrap session commits (creating the DB row), the failure-state UPDATE silently no-ops because `update_import_job` returns early when the row is missing, leaving the job recorded only in the in-memory registry. There is also a real **nesting-depth violation** in `run_import` (6 levels deep, hard limit is 4 per CLAUDE.md), a **docstring-vs-code mismatch** in the retry backoff schedule, and a `lifespan` shutdown ordering issue where `stop_engine()` is skipped if the awaited reaper task raises a non-`CancelledError` BaseException.

The test additions are thorough (1,333 new lines) and the DB-backed `TestFailOrphanedJobsAgeThreshold` correctly pins the Pitfall 3 mitigation, but the SQL-text invariance assertion in `test_stage5_sql_text_invariant_across_batches` compiles the statement without supplying multiparams, which means the executemany expansion is never exercised and the test can pass even if a future regression reintroduced variable SQL text. See WR-04.

## Critical Issues

### CR-01: Silent failure-state loss when bootstrap session never commits

**File:** `app/services/import_service.py:428–446` (bootstrap scope) and `app/services/import_service.py:539–557` (except-block calling `_record_failure_with_retry`); `app/repositories/import_job_repository.py:45–58` (no-op behavior of `update_import_job`)

**Issue:** The new three-scope structure introduces an observable window where the in-memory `JobState` exists but no DB row exists yet — specifically between `_jobs[job_id] = JobState(...)` (in `create_job`, called from the router) and `bootstrap_session.commit()` (line 446 of `import_service.py`). If `get_latest_for_user_platform` or `create_import_job` raises during the bootstrap scope (e.g. transient DB error, `OperationalError` on connection acquire, schema drift), control falls into `except Exception`, which calls `_record_failure_with_retry(...)`. That helper executes `update_import_job(session, job_id=..., status="failed", ...)`. But `update_import_job` in the repository (lines 53–55) does `job = await get_import_job(session, job_id); if job is None: return` — a silent no-op when the DB row doesn't exist. The retry helper observes no exception, commits an empty transaction, and returns successfully.

Result: the job is marked FAILED in `_jobs` (in-memory), but no DB record exists at all. The user sees no "failed" entry in their `get_unseen_failed_jobs_for_user` view, the periodic reaper has no row to reap, and on the next backend restart the in-memory `_jobs` registry is gone — the failure is silently dropped. Sentry does fire via `capture_exception(exc)` for the original exception, so an operator can see it, but end-user UX shows "import disappeared".

This is *not* strictly a regression — the previous single-session code had the same vulnerability (no commit could happen before the bootstrap-equivalent work succeeded). But the new structure makes the window slightly more visible and the design is the natural place to fix it.

**Fix:** Either (a) make `update_import_job` raise when the job is missing, optionally gated by a `must_exist=True` kwarg for the retry helper's call site so existing callers preserve no-op behaviour, or (b) detect the missing-row case in `_record_failure_with_retry` and insert a minimal failed job row directly:

```python
async def _record_failure_with_retry(...) -> None:
    ...
    try:
        async with async_session_maker() as session:
            existing = await import_job_repository.get_import_job(session, job_id)
            if existing is None:
                # Bootstrap scope never committed — create a minimal failed row.
                job_state = _jobs.get(job_id)
                if job_state is None:
                    logger.error("No JobState for %s; cannot persist failure", job_id)
                    return
                await import_job_repository.create_import_job(
                    session,
                    job_id=job_id,
                    user_id=job_state.user_id,
                    platform=job_state.platform,
                    username=job_state.username,
                )
            await import_job_repository.update_import_job(
                session, job_id=job_id, status=status,
                games_fetched=games_fetched, games_imported=games_imported,
                error_message=error_message, completed_at=completed_at,
            )
            await session.commit()
            return
    except OperationalError as exc:
        ...
```

Either path closes the silent-loss window. Add a regression test that mocks `create_import_job` to raise once and asserts the failure-state row exists after `run_import` returns.

## Warnings

### WR-01: `run_import` nesting depth violates CLAUDE.md hard limit (6 vs 4)

**File:** `app/services/import_service.py:416–515`

**Issue:** Counting indentation levels inside the function body: `try` (1) → `async with asyncio.timeout` (2) → `async with httpx.AsyncClient` (3) → `async for game_dict` (4) → `if len(batch) >= _BATCH_SIZE` (5) → `async with async_session_maker()` (6). Six levels deep. CLAUDE.md sets a hard limit of 4 and a soft limit of 3. The Plan 90-02 restructure split the single session into three scopes, which added an extra `async with` level inside the loop.

The function is also ~100 logic LOC for the body, near the soft limit. The new code interleaves session-acquire bookkeeping (lines 463, 481, 507) with the actual import work in a way that obscures the pipeline shape.

**Fix:** Extract the per-batch unit into a helper that owns its own session scope. This collapses two nesting levels at the call site and reads as a list of pipeline stages:

```python
async def _flush_batch_with_progress(
    batch: list[NormalizedGame], job: JobState, job_id: str
) -> None:
    async with async_session_maker() as session:
        imported = await _flush_batch(session, batch, job.user_id)
        job.games_imported += imported
        await import_job_repository.update_import_job(
            session, job_id=job_id, status="in_progress",
            games_fetched=job.games_fetched, games_imported=job.games_imported,
        )
        await session.commit()

# In run_import:
async for game_dict in game_iter:
    batch.append(game_dict)
    if len(batch) >= _BATCH_SIZE:
        await _flush_batch_with_progress(batch, job, job_id)
        batch = []
if batch:
    await _flush_batch_with_progress(batch, job, job_id)
```

Bootstrap and completion can move into their own private helpers too. This brings the orchestrator down to ~3 levels and a list-of-stages shape that CLAUDE.md explicitly recommends for pipeline orchestrators.

### WR-02: Retry backoff schedule mismatches docstring ("2/4/8/16/30s" vs actual 2/4/8/16s)

**File:** `app/services/import_service.py:79–83, 318–393`

**Issue:** Constants are `_FAILURE_RECORD_MAX_RETRIES = 5` and `_FAILURE_RECORD_BACKOFF_CAP_SECONDS = 30`. The docstring (line 333) and comment (line 82) claim the schedule is `2/4/8/16/30s (~60s total budget)`. The actual loop runs `range(5)` = attempts 0..4, with sleeps before attempts 1..4 only. Computed backoffs: `min(2*2^0,30)=2`, `min(2*2^1,30)=4`, `min(2*2^2,30)=8`, `min(2*2^3,30)=16`. So 4 sleeps totalling 30s, never hitting the 30s cap. The "30s" element of the documented schedule never executes; the "~60s total budget" is actually ~30s.

The unit test `test_retries_on_operational_error_then_succeeds` only verifies sleeps `[2, 4]`. `test_exhausts_retries_and_captures_once` asserts `len(sleep_calls) == _FAILURE_RECORD_MAX_RETRIES - 1 = 4` but never asserts the actual backoff values, so the documented schedule isn't pinned.

**Fix:** Either bump `_FAILURE_RECORD_MAX_RETRIES = 6` (gives sleeps 2/4/8/16/30 = 60s total, matching docs), or correct the docstring/comment to say "2/4/8/16s (30s total budget)". Given the 2026-05-16 recovery window was ~2s and the helper succeeded with attempt 2 in real life, 30s is already plenty — fixing the docstring is the lower-risk option. Also add `assert sleep_calls == [2, 4, 8, 16]` to `test_exhausts_retries_and_captures_once` so the schedule is regression-locked.

### WR-03: `stop_engine()` skipped if reaper task raises non-CancelledError BaseException at shutdown

**File:** `app/main.py:62–70`

**Issue:**

```python
finally:
    reaper_task.cancel()
    try:
        await reaper_task
    except asyncio.CancelledError:
        pass  # expected on shutdown
    await stop_engine()
```

The `try/except` only catches `asyncio.CancelledError`. If `run_periodic_reaper` somehow exits with any other `BaseException` subtype (or even an `Exception` that escaped the inner `except Exception:` — e.g. an exception raised from inside the `except Exception:` block itself, since the Sentry call could conceivably raise during shutdown when the DSN connection is torn down), `await reaper_task` re-raises it, the `try/except` doesn't catch it, and `stop_engine()` never runs. The long-lived Stockfish UCI process leaks across shutdown.

**Fix:** Use `try/finally` so `stop_engine()` always runs:

```python
finally:
    reaper_task.cancel()
    try:
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Periodic reaper task raised on shutdown")
    finally:
        await stop_engine()
```

Or even simpler: wrap `await reaper_task` in `contextlib.suppress(Exception, asyncio.CancelledError)` if you don't care to log.

### WR-04: SQL-text invariance test doesn't compile with multiparams, so executemany expansion is never exercised

**File:** `tests/test_import_service.py:1612–1646` (in `test_stage5_sql_text_invariant_across_batches`)

**Issue:** The test captures `call.args[0]` (the SQL Statement) and compiles it via `call.args[0].compile(dialect=dialect)` *without supplying `compile_kwargs={"literal_binds": True}` and without passing the multiparams list*. With a `bindparam("b_id")` + executemany pattern, SQLAlchemy's compiled SQL string is *already* invariant regardless of the params dict, because the bind expansion happens at execution time (asyncpg binds), not at compile time. So this test would pass even on the OLD `case()+IN` code if you compiled the Statement object before SQLAlchemy expanded the `IN (1,2,3)` — and it would pass trivially on the new code regardless of whether the executemany params actually drive different SQL.

The intent of the test ("the SQL text is invariant across batches") is correct, but the assertion as written doesn't exercise the executemany param-expansion path. It tells you the *Statement template* is invariant, not that the *executed SQL* is invariant.

**Fix:** Either compile with `literal_binds=True` and assert that the rendered SQL contains no game-id integers, or capture the actual `asyncpg`/`statement_cache_size` metric in an integration test. A simpler regression guard: assert that the captured `call.args[0]` Statement object compiles to a string containing no integer literals from the batch ids:

```python
for sql_text in sql_texts_batch_a:
    for gid in [101, 102, 103]:
        assert str(gid) not in sql_text, (
            f"Game id {gid} appears in SQL text — regression to literal binds. "
            f"SQL: {sql_text!r}"
        )
```

This catches the actual regression (literal embedded ids) rather than testing a property the new code provides trivially.

### WR-05: Two commits per batch on the same `AsyncSession` split insert and progress-counter into separate transactions

**File:** `app/services/import_service.py:461–477` and `app/services/import_service.py:730` (commit inside `_flush_batch`)

**Issue:** `_flush_batch` calls `await session.commit()` at the end. After it returns, `run_import` calls `update_import_job(...)` then `await session.commit()` *again* on the same session. So each batch is **two transactions**: (1) game/position INSERTs + Stage 5 UPDATEs, (2) progress-counter UPDATE on the `import_jobs` row. If the second commit fails (DB blip, OperationalError between the two commits), the rows are persisted but `games_imported` on the job row is stale. The user sees `games_imported=N` on the dashboard but the DB actually has `N + _BATCH_SIZE` games for the user. On re-sync, duplicates would be detected via `platform_game_id`, so no data corruption — but the counter divergence is observable.

More subtle: the second commit happens while the in-memory `job.games_imported` was already bumped (line 465 increments it before the UPDATE). If commit (2) fails and the helper raises, control falls to `except Exception`, which records `games_imported=job.games_imported` (the new, possibly-uncommitted value) into the failure state. The eventual DB row will show `games_imported = N + _BATCH_SIZE` (failure state), even though commit (2) for the previous batch *also* set it to that value but rolled back. End-state is correct by accident.

**Fix:** Move the `update_import_job(status="in_progress", ...)` call *inside* `_flush_batch` before its commit, so each batch is exactly one transaction containing both the rows and the counter bump. Or remove the `await session.commit()` inside `_flush_batch` (let the caller commit). Pick one ownership boundary — currently `_flush_batch` half-owns the transaction (commits at the end) and the caller continues using the same session afterward, which is a confusing contract.

### WR-06: `_make_game_iterator` missing return type annotation and uses `Any` for callback (ty / CLAUDE.md violation)

**File:** `app/services/import_service.py:560–565`

**Issue:** Signature is `async def _make_game_iterator(client, job, previous_last_synced_at, on_game_fetched: Any):` — no return type, and `on_game_fetched: Any` is a Callable. CLAUDE.md requires explicit return type annotations on all functions and prohibits bare `Any` where a concrete type is available. While the parameter `previous_last_synced_at: datetime | None` is correctly tightened (the Phase 90 win), `on_game_fetched` was left as `Any` and the function still has no return annotation.

**Fix:**

```python
from collections.abc import AsyncIterator, Callable

async def _make_game_iterator(
    client: httpx.AsyncClient,
    job: JobState,
    previous_last_synced_at: datetime | None,
    on_game_fetched: Callable[[], None],
) -> AsyncIterator[NormalizedGame]:
    ...
```

CLAUDE.md notes the "refactor on sight" rule: since Phase 90 already edits this signature (the param rename is part of Pitfall 2 mitigation), tightening these annotations is in scope rather than leaving pre-existing technical debt.

### WR-07: `_record_failure_with_retry` swallows `CancelledError` indirectly via `last_exc` capture / no rollback on cancel

**File:** `app/services/import_service.py:347–392`

**Issue:** When the lifespan cancels the reaper task during shutdown, any `_record_failure_with_retry` invocation currently awaiting `asyncio.sleep(backoff)` will receive `CancelledError`. Because `CancelledError` is a `BaseException` (not `Exception`) in Python 3.13, neither `except OperationalError` nor `except Exception` catches it — good, it propagates up. However, the helper is also called from `run_import`'s outer `except Exception` block (lines 539, 550). At that point, the original exception has been recorded to Sentry, but if the helper is cancelled mid-retry, the failure-state UPDATE doesn't land. The `_jobs[job_id]` registry shows FAILED, but the DB row still shows IN_PROGRESS until the periodic reaper picks it up.

This isn't strictly a bug (the reaper exists precisely for this case), but the cancellation path during shutdown is not pinned by any test, and the helper's docstring doesn't mention the cancellation contract.

**Fix:** Add a docstring note explicitly stating that the helper is cancellation-aware (CancelledError propagates without retry) and add a unit test that monkeypatches `asyncio.sleep` to raise `CancelledError` and asserts the helper re-raises rather than retrying. Optional: wrap the inner try in a `try/except asyncio.CancelledError: raise` to make the contract explicit at the code level.

## Info

### IN-01: `update_import_job` accepts `**kwargs` with no validation — violates "no bare str" Literal rule

**File:** `app/repositories/import_job_repository.py:45–58`

**Issue:** Pre-existing pattern but exercised by new Phase 90 code. `update_import_job(session, job_id, **kwargs)` lets the caller pass any field name and value with no schema check. Phase 90 introduces `_record_failure_with_retry` which calls `update_import_job(status="failed", ...)`. Since `status` is one of `Literal["pending", "in_progress", "completed", "failed"]` per the `JobStatus` enum, the call site (line 363) should pass a typed value. The helper's parameter is `status: Literal["failed"]` (good — tight), but the repo function loses that typing.

**Fix (small):** Introduce a typed wrapper specifically for status transitions:

```python
async def set_job_status(
    session: AsyncSession,
    job_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    **other_fields: Any,
) -> None:
    await update_import_job(session, job_id, status=status, **other_fields)
```

Then the call sites in `run_import` (5 places) gain a typed status param. Lower priority than the other findings.

### IN-02: Duplicate import of `datetime, timedelta, timezone` inside `get_unseen_failed_jobs_for_user`

**File:** `app/repositories/import_job_repository.py:123–125`

**Issue:** Line 3 already imports `datetime, timedelta, timezone`. Lines 123–125 import them again inside the function. Pre-existing dead-code style issue, harmless but messy. The Phase 90 diff didn't introduce this but did add a top-level `timedelta` import, making the inner re-imports doubly redundant.

**Fix:** Remove the in-function imports at lines 123–125.

### IN-03: Test helper `test_stage5_sql_text_invariant_across_batches` accesses `pgn_results` indirectly via `sql_texts_batch_*` but never asserts both UPDATE groups were emitted

**File:** `tests/test_import_service.py:1612–1646`

**Issue:** The test asserts `len(sql_texts_batch_a) == len(sql_texts_batch_b)` and pairwise SQL equality, but doesn't assert that the count equals **2** (one for move_count, one for result_fen) for batches where all games have non-None result_fen. If a future regression dropped the fen UPDATE entirely (e.g. accidentally moved the `if fen_params:` guard outside), this test would still pass (both batches produce 1 UPDATE call instead of 2 — still equal).

**Fix:** Add `assert len(sql_texts_batch_a) == 2, "Expected exactly 2 UPDATE statements (move_count + fen)"`.

### IN-04: `previous_job` ORM instance retained as local in bootstrap scope despite scalar extraction

**File:** `app/services/import_service.py:429–437`

**Issue:** The code extracts `previous_last_synced_at` as a scalar but the `previous_job` ORM instance reference is still held in the local until the scope ends (line 447). It's harmless — Python's reference counting will drop it on scope exit — but the comment "only `previous_last_synced_at` (a plain scalar) carries state into the batch loop" could be reinforced by `del previous_job` after the scalar extraction. Minor.

**Fix:** Either `del previous_job` after line 437, or inline the lookup:

```python
previous_last_synced_at = (
    (await import_job_repository.get_latest_for_user_platform(
        bootstrap_session, job.user_id, job.platform, job.username
    )).last_synced_at
    if await import_job_repository.get_latest_for_user_platform(...) is not None
    else None
)
```

(That's a double-call, ugly — `del previous_job` is the cleaner option.)

### IN-05: `_record_failure_with_retry` reuses `last_exc` only across `OperationalError` retries — non-transient errors aren't included in final Sentry capture

**File:** `app/services/import_service.py:374–392`

**Issue:** When `_record_failure_with_retry` catches a non-transient `Exception` (line 377), it captures and returns immediately. Good. But if attempts 1–4 raise `OperationalError` and attempt 5 raises `ValueError` (some non-transient schema drift), only the `ValueError` is captured (early return path), and the four prior `OperationalError`s are lost from Sentry context. Conversely, if the loop exhausts on `OperationalError` x5, `last_exc` is set and captured at line 392 — fine.

The mixed case (transient followed by non-transient) loses context. Practically rare, but worth a single-line comment noting the trade-off.

**Fix:** Add a comment near line 377 explaining that the non-transient path doesn't include prior transient context, OR call `sentry_sdk.set_context("retry", {"prior_transient_attempts": attempt})` before capture for visibility.

---

_Reviewed: 2026-05-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
