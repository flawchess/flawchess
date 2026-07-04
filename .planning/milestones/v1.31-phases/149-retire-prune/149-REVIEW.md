---
phase: 149-retire-prune
reviewed: 2026-07-04T13:00:58Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - app/models/worker_heartbeat.py
  - app/repositories/worker_heartbeat_repository.py
  - app/routers/eval_remote.py
  - app/routers/imports.py
  - app/repositories/import_job_repository.py
  - app/services/import_service.py
  - app/services/normalization.py
  - app/services/zobrist.py
  - app/services/chesscom_to_lichess.py
  - app/services/eval_drain.py
  - app/services/eval_queue_service.py
  - app/models/game.py
  - app/models/eval_jobs.py
  - app/models/import_job.py
  - app/models/__init__.py
  - alembic/versions/20260704_112059_b4ea823c85be_add_worker_heartbeats_table.py
  - alembic/versions/20260704_123013_12d3df9c5373_import_jobs_partial_unique_index.py
  - scripts/remote_eval_worker.py
  - tests/test_worker_heartbeats.py
  - tests/test_eval_worker_endpoints.py
  - tests/test_normalization.py
  - tests/test_imports_router.py
  - tests/test_import_service.py
  - tests/test_game_repository.py
  - tests/services/test_chesscom_to_lichess.py
  - tests/test_zobrist.py
  - tests/test_seed_openings.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 149: Code Review Report

**Reviewed:** 2026-07-04T13:00:58Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed the four Phase 149 "Retire & Prune" changes: (1) `worker_heartbeats` upsert wired into the three live eval-submit lanes, (2) the durable `import_jobs` partial-unique-index guard with IntegrityError-as-idempotency, (3) the chess.com unknown-result skip replacing the silent draw fallback, and (4) deletion of the Gen-1 `/lease`+`/submit` protocol.

The heartbeat accumulation/coalesce logic is correct (atomic `ON CONFLICT DO UPDATE` with `submit_count`/`evals_submitted` incremented server-side, `worker_schema_version` coalesced against clobber-by-NULL exactly as documented and tested). The unknown-result skip is correctly wired end-to-end (returns `None` → `chesscom_client.py` skips + continues, `GameResult` literal unwidened, Sentry capture uses `set_context`, not message interpolation). The Gen-1 endpoint/handler deletion itself is clean — no dangling router-level references to `_apply_submit`, `/lease`, or `/submit` remain, and `WORKER_ID_SERVER_POOL`/`needs_engine_full_evals` references were consistently updated everywhere they were touched.

Two real issues surfaced during deeper tracing:

1. A **BLOCKER**: the new durable-import-job guard in `start_import` only catches `IntegrityError`. Any other exception during the job-row insert/commit (a transient DB outage — a documented recurring class of incident in this project's history) leaves the in-memory `JobState` permanently registered as `PENDING` with no scheduled background task, silently locking the affected user out of importing that platform again until the backend process restarts.
2. A **WARNING**: the new `upsert_worker_heartbeat()` call is un-isolated inside the same write transaction as the real eval/blob/flaw writes in all three submit lanes, so a failure specific to the heartbeat write (most plausibly an oversized `sf_version` hitting the new `String(50)` column when `EXPECTED_SF_VERSION` is unconfigured) aborts the whole submit and discards freshly-computed Stockfish work, contrary to the "passive telemetry, submits only, never a gate" design intent.

A second WARNING and two INFO items round out incomplete-cleanup / minor-robustness observations from the deletion work.

## Critical Issues

### CR-01: start_import's IntegrityError-only catch strands the in-memory job registry on any other DB failure

**File:** `app/routers/imports.py:85-124`
**Issue:**

```python
job_id = import_service.create_job(user_id, request.platform, request.username)

try:
    await import_job_repository.create_import_job(
        session, job_id=job_id, user_id=user_id,
        platform=request.platform, username=request.username,
    )
    await session.commit()
except IntegrityError:
    await session.rollback()
    import_service.discard_job(job_id)
    ...
    return ImportStartedResponse(job_id=existing_row.id, status=existing_row.status)

asyncio.create_task(import_service.run_import(job_id))
return ImportStartedResponse(job_id=job_id, status="pending")
```

`import_service.create_job()` registers `_jobs[job_id] = JobState(status=PENDING)` in the module-level in-memory dict *before* the try block. The except clause only handles `IntegrityError` (the expected concurrent-duplicate race) and calls `import_service.discard_job(job_id)` to clean up the in-memory entry on that path.

Any *other* exception raised by `create_import_job`'s internal `flush()` or by `session.commit()` — e.g. `OperationalError`/`InterfaceError`/`DBAPIError` from a transient Postgres outage, exactly the class of error `import_service._RETRIABLE_DB_OUTAGE_ERRORS` and `_record_failure_with_retry` exist to handle elsewhere in this same file — is **not caught here**. It propagates as an unhandled 500, but `discard_job(job_id)` is never called, so the `JobState(status=PENDING)` stays in `_jobs` forever. No background task was ever scheduled (`asyncio.create_task` is only reached after the try block succeeds), so nothing will ever transition this job to `COMPLETED`/`FAILED`, and no periodic reaper touches the in-memory registry (`run_periodic_reaper`/`cleanup_orphaned_jobs` only reap DB rows via `fail_orphaned_jobs`).

The practical effect: `find_active_job(user_id, platform)` will report this phantom job as active on every subsequent `POST /imports` for that user+platform, permanently returning the stuck job with 200 instead of starting a new import — until the backend process is restarted (the only thing that resets the module-level `_jobs` dict). This is a regression introduced by moving the durable-row insert into the synchronous request path (PRUNE-05): under the old design the DB write happened *inside* the already-scheduled background task, so a DB hiccup there was retried via `_record_failure_with_retry` and never blocked `find_active_job`.

This exact non-`IntegrityError` failure path (a transient DB outage during commit) is untested — `tests/test_imports_router.py` only exercises the `IntegrityError` race.

**Fix:** Either broaden the except clause to also discard the in-memory job on any failure (re-raising afterward so the client still sees the error), or reuse the existing retriable-error taxonomy:

```python
try:
    await import_job_repository.create_import_job(...)
    await session.commit()
except IntegrityError:
    await session.rollback()
    import_service.discard_job(job_id)
    ...
    return ImportStartedResponse(job_id=existing_row.id, status=existing_row.status)
except Exception:
    await session.rollback()
    import_service.discard_job(job_id)  # never leak a phantom PENDING job
    raise
```

## Warnings

### WR-01: Heartbeat upsert is not isolated from the live-submit transaction

**File:** `app/routers/eval_remote.py:648-655` (entry-submit), `:903-912` (flaw-blob-submit), `:1335-1345` (atomic-submit); `app/repositories/worker_heartbeat_repository.py:33-58`
**Issue:** `upsert_worker_heartbeat()` is called as an ordinary statement inside each lane's existing write session, immediately before `commit()`. Per the docstrings this is meant to be "passive telemetry only ... never a gate", but there is no isolation: if the INSERT/UPDATE for the heartbeat row itself raises, the exception propagates through the same code path as a genuine eval/classify/blob failure, and the entire transaction (including the real submitted evals) is rolled back.

The most concrete trigger: `sf_version` is a required, unconstrained `str` on `EntrySubmitRequest`/`FlawBlobSubmitRequest`/`AtomicSubmitRequest` (no `max_length`), but `worker_heartbeats.sf_version` is `String(50)`. The `EXPECTED_SF_VERSION` gate that runs earlier in each handler only rejects a *mismatched* value and only when `settings.EXPECTED_SF_VERSION` is configured (default `""`, i.e. unset in dev/test and any environment where an operator forgets to set it) — it never bounds the string's length. A worker sending `sf_version` longer than 50 chars in that configuration would hit a Postgres `StringDataRightTruncation` (`DataError`) on the heartbeat insert, aborting the whole submit and discarding the real Stockfish work that was about to be committed alongside it.

For `entry_submit_eval` this additionally triggers the "best-effort release leases" fallback and re-raises to the client as a 500; for `flaw_blob_submit`/`atomic_submit_eval` there is no wrapping try/except at all, so it surfaces as a bare 500 with the transaction rolled back.

**Fix:** Wrap the heartbeat call in its own try/except that logs + Sentry-captures locally but never propagates, so a telemetry-only failure genuinely can never break the request path:

```python
try:
    await upsert_worker_heartbeat(write_session, worker_id=worker_id, ...)
except Exception:
    sentry_sdk.set_tag("source", "worker_heartbeat")
    sentry_sdk.capture_exception()
```

(Note this still requires the heartbeat statement to run before `commit()` to land in the same transaction on the happy path — the fix is exception isolation, not session isolation.) Independently, consider adding a `max_length=50` (or similar) bound to the `sf_version` field on the three submit schemas, consistent with the existing per-field bounds pattern already used for `eval_cp`/`eval_mate`/`best_move`/`pv` in the same file (code-review 2026-07-02, #11).

### WR-02: Dead Gen-1 schema classes left behind after the endpoint deletion

**File:** `app/schemas/eval_remote.py:35-73` (`LeaseResponse`, `SubmitEval`, `SubmitRequest`, `SubmitResponse`)
**Issue:** 149-03-SUMMARY.md documents dropping the now-unused `SubmitRequest`/`SubmitResponse`/`LeaseResponse` *imports* from `app/routers/eval_remote.py`, but the schema class *definitions* themselves were left in `app/schemas/eval_remote.py`. Grepping the full tree confirms zero non-test, non-schema-file references remain — these four classes are exercised only by `tests/test_eval_remote_schema_bounds.py` and parts of `tests/test_eval_worker_endpoints.py` that validate schema-level bounds in isolation, not any live endpoint. For a phase whose stated purpose is to "retire and prune" the Gen-1 protocol, this is an incomplete cleanup: the schemas (and their now-orphaned tests) are dead weight that will keep confusing future readers into thinking `/lease`+`/submit` still exist.
**Fix:** Delete `LeaseResponse`, `SubmitEval`, `SubmitRequest`, `SubmitResponse` from `app/schemas/eval_remote.py` along with the tests that only assert their standalone validation bounds, in a follow-up cleanup pass.

## Info

### IN-01: `last_ip` is unconditionally overwritten (no coalesce), unlike `worker_schema_version`

**File:** `app/repositories/worker_heartbeat_repository.py:44-53`
**Issue:** The upsert coalesces `worker_schema_version` specifically to avoid a lane that omits it clobbering a previously-recorded value with NULL, but `last_ip` has no such protection — `request.client` being `None` on any single request (confirmed possible and tested for the ASGI test transport) overwrites a previously-good `last_ip` with NULL. In production this should not fire (`--proxy-headers` keeps `request.client.host` populated), and the docstring states this is intentional ("overwrites ... with the latest values"), but the asymmetry with the `worker_schema_version` coalesce guard is worth a second look if `last_ip` NULL-flapping is ever observed in the new table.
**Fix:** None required now; if prod ever shows NULL flapping, consider `sa.func.coalesce(stmt.excluded.last_ip, WorkerHeartbeat.last_ip)` to match the `worker_schema_version` pattern.

### IN-02: `assert` used for a production-path invariant

**File:** `app/routers/imports.py:119-122`
**Issue:** `assert existing_row is not None, (...)` guards a genuinely-should-never-happen post-`IntegrityError` re-fetch. `assert` statements are stripped when Python runs with `-O` (not currently the case for this project's deploy, so no live risk today), and an `AssertionError` here surfaces as an undifferentiated 500 rather than a clearly-labeled internal-error response.
**Fix:** Low priority; if this code path is ever touched again, prefer raising an explicit `RuntimeError`/`HTTPException(500)` with a Sentry capture instead of a bare `assert`.

---

_Reviewed: 2026-07-04T13:00:58Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
