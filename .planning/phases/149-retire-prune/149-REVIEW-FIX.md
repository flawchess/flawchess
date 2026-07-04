---
phase: 149-retire-prune
fixed_at: 2026-07-04T13:18:00Z
review_path: .planning/phases/149-retire-prune/149-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 149: Code Review Fix Report

**Fixed at:** 2026-07-04T13:18:00Z
**Source review:** .planning/phases/149-retire-prune/149-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (explicitly requested: CR-01, WR-01, WR-02, IN-02)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: start_import's IntegrityError-only catch strands the in-memory job registry on any other DB failure

**Files modified:** `app/routers/imports.py`, `tests/test_imports_router.py`
**Commit:** f8a6bbdc
**Applied fix:** Added an `except Exception:` branch after the existing `except IntegrityError:` in `start_import`'s durable-insert try block. On any non-IntegrityError failure it now rolls back the session, calls `import_service.discard_job(job_id)` to clear the stuck in-memory `PENDING` entry, captures to Sentry with `set_context("import", {"user_id", "platform"})` (no variables embedded in the message), and re-raises. Added `test_non_integrity_db_failure_discards_stuck_in_memory_job`, which patches `create_import_job` to raise `sqlalchemy.exc.OperationalError` and asserts both that the call raises and that `find_active_job()` returns `None` afterward.

### WR-01: Heartbeat upsert is not isolated from the live-submit transaction

**Files modified:** `app/repositories/worker_heartbeat_repository.py`, `tests/test_worker_heartbeats.py`
**Commit:** ef32bb92
**Applied fix:** Added module constants `_WORKER_ID_MAX_LEN = 16` and `_SF_VERSION_MAX_LEN = 50` mirroring `WorkerHeartbeat`'s actual column widths (`last_ip` is `Text`/unbounded, so it needs no truncation — noted in a comment), and defensively truncate `worker_id`/`sf_version` before building the upsert statement. Wrapped `await session.execute(stmt)` in `async with session.begin_nested():` inside a try/except that captures any exception to Sentry (`set_context("heartbeat", {"worker_id"})`) and swallows it, so a heartbeat-only failure rolls back only its own savepoint and never the caller's real submit transaction. Added `test_upsert_worker_heartbeat_oversized_sf_version_never_aborts_caller_session`, which calls the repository function directly with a 200-char `sf_version` and asserts it does not raise and the outer session remains usable for a subsequent query.

### WR-02: Dead Gen-1 schema classes left behind after the endpoint deletion

**Files modified:** `app/schemas/eval_remote.py`, `tests/test_eval_remote_schema_bounds.py`, `tests/test_eval_worker_endpoints.py`
**Commit:** 54c3a89d
**Applied fix:** Grepped `app/ tests/ scripts/` with word-boundary patterns for `LeaseResponse`/`SubmitEval`/`SubmitRequest`/`SubmitResponse` and confirmed the only remaining hits were the class definitions themselves, historical prose comments (consistent with this codebase's existing convention of leaving comments that reference other already-deleted Gen-1 identifiers like `_apply_submit` for context), and tests that instantiate the schemas directly. Deleted the four dead classes (`LeaseResponse`, `SubmitEval`, `SubmitRequest`, `SubmitResponse`); kept `LeasePosition`, which is still live (reused by `AtomicLeaseResponse`). Deleted the two test functions in `tests/test_eval_worker_endpoints.py` that exercised only `SubmitEval`, and the eight `SubmitEval`-only bound tests in `tests/test_eval_remote_schema_bounds.py`, leaving the `AtomicSubmitEval`/`EntrySubmitEval` tests and imports untouched.

### IN-02: `assert` used for a production-path invariant

**Files modified:** `app/routers/imports.py`
**Commit:** 6cc1bf62
**Applied fix:** Replaced `assert existing_row is not None, (...)` with an explicit `if existing_row is None:` guard that calls `sentry_sdk.set_context("import", {"user_id", "platform"})`, builds a `RuntimeError` with a static message (no interpolated variables), calls `sentry_sdk.capture_exception(exc)`, and raises it — so the invariant holds even under `python -O`.

## Verification

- `uv run ruff format app/ tests/` — 1 file reformatted (a cosmetic single-line collapse in `app/routers/imports.py` from the CR-01/IN-02 edits); committed separately as `4cd29c1c style(149): apply ruff format after CR-01/IN-02 fixes`.
- `uv run ruff check app/ tests/ --fix` — all checks passed, no changes.
- `uv run ty check app/ tests/` — all checks passed, zero errors.
- `uv run pytest -n auto -x` — **3153 passed, 19 skipped** (pre-existing, unrelated skips), 4 warnings (pre-existing `StarletteDeprecationWarning`/SQLAlchemy identity-map warning, unrelated to this work). Full suite green.

All four fixes were applied in an isolated git worktree (`gsd-reviewfix/149-777437`, forked from `gsd/phase-149-retire-prune`) and fast-forwarded back onto the phase branch on completion.

---

_Fixed: 2026-07-04T13:18:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
