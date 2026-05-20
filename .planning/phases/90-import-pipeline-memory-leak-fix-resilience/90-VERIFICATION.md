---
phase: 90-import-pipeline-memory-leak-fix-resilience
verified: 2026-05-20T18:00:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "RSS stays flat across a real 5k+ game import"
    expected: "RSS stays within +/-15% of baseline across the full import; does not climb linearly with batch count"
    why_human: "Requires a live chess.com/lichess API fetch with the Stockfish eval pool running — too heavy for CI. docker stats / ps rss sampling needed during a real import."
  - test: "Reaper fires after a Postgres-only restart (backend stays up)"
    expected: "A stranded in_progress job transitions to 'failed' within 5 minutes of the next reaper tick; the reaper does NOT kill a <3h-old job"
    why_human: "Requires killing the Postgres Docker container mid-import and confirming the failure-state recording or the reaper picks up the orphan — cannot automate safely in CI."
  - test: "Sentry issues FLAWCHESS-56 and FLAWCHESS-3Q do not recur after deploy"
    expected: "No new occurrences of the per-batch SQL-cache-growth or stuck-in_progress patterns after a production deploy and a real large import"
    why_human: "Production-only signal; requires monitoring Sentry for 48h after deploy."
---

# Phase 90: Import Pipeline Memory Leak Fix + Resilience Verification Report

**Phase Goal:** Eliminate the per-batch unique-SQL leak in `_flush_batch` Stage 5 that caused the 2026-05-16 production OOM (FLAWCHESS-56 / FLAWCHESS-3Q), scope AsyncSession per batch in `run_import` as defense-in-depth, and land leak-independent resilience defects (orphan-job reaper, retry-on-DB-recovery, atomic duplicate-import guard).
**Verified:** 2026-05-20T18:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

Note on scope: the phase goal mentions "atomic duplicate-import guard" as one of the resilience defects. The three PLANs (90-01, 90-02, 90-03) explicitly exclude it — all have `requirements: []` and none contain a task or artifact for it. CLAUDE.md confirms this is still deferred ("Keep this low until the orphan-reaper / atomic-import-guard follow-up phase lands" — line 74 of `import_service.py`). The phase goal text used the CLAUDE.md phrasing from the original FLAWCHESS-56 note; the actual scoped deliverables are exactly what the three plans describe. This is not a gap — it is the expected deferred item, confirmed in code by the inline comment.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_flush_batch` Stage 5 emits two invariant SQL texts (move_count UPDATE + result_fen UPDATE) regardless of which game ids are in the batch | VERIFIED | `bindparam("b_id")`, `bindparam("b_mc")`, `bindparam("b_rf")` at lines 746-747, 766-767. `case` removed from imports (line 27). `test_stage5_sql_text_invariant_across_batches` passes with `literal_binds=True` assertion (line 1751 of tests). |
| 2 | Games without a parsed `result_fen` keep their prior value (or stay NULL); never overwritten to NULL by Stage 5 | VERIFIED | Group (b) filters `if fen is not None` (line 759-762). `test_result_fen_none_preserved` passes. |
| 3 | Games with a parsed `result_fen` have that value persisted | VERIFIED | Group (b) executes `fen_stmt` when `fen_params` is non-empty (lines 763-769). `test_move_count_lands_for_all_games` passes. |
| 4 | `move_count` is persisted for every game in the batch | VERIFIED | Group (a) issues `move_count_stmt` for all entries in `rows_result.move_counts` (lines 744-753). |
| 5 | `run_import` opens a fresh `AsyncSession` for each batch, plus a bootstrap session and a completion session — three distinct scopes | VERIFIED | `_bootstrap_import_job` (line 430), `_flush_batch_with_progress` (line 458), `_complete_import_job` (line 483) each own one `async with async_session_maker()`. `grep -c 'async with async_session_maker() as'` = 5 (bootstrap + 2 per-batch helpers + completion + `cleanup_orphaned_jobs`). `test_one_session_per_batch` passes. |
| 6 | `previous_job.last_synced_at` survives bootstrap session close as a plain scalar; no DetachedInstanceError risk | VERIFIED | Scalar extracted inside `_bootstrap_import_job` at line 444-445. `_make_game_iterator` accepts `previous_last_synced_at: datetime | None` (line 601). `grep -n 'previous_job\.'` finds exactly 1 match (the extraction line). `test_previous_job_last_synced_at_scalar_survives_close` passes. |
| 7 | `run_periodic_reaper` runs every `_REAPER_INTERVAL_SECONDS` (5 min) with `orphan_age_threshold=timedelta(seconds=IMPORT_TIMEOUT_SECONDS)` (3h); started in `lifespan`, cancelled+awaited on shutdown | VERIFIED | `run_periodic_reaper` at line 292. `asyncio.create_task(run_periodic_reaper(), ...)` at `app/main.py:64`. Cancel-and-await with `try/finally` wrapping `stop_engine()` at lines 72-81. `test_reaper_calls_cleanup_at_interval` and `test_reaper_passes_age_threshold` pass. |
| 8 | `_record_failure_with_retry` retries the failure-state UPDATE up to 5 times on `OperationalError` with 2/4/8/16s backoff; Sentry capture only on final exhaustion | VERIFIED | `_record_failure_with_retry` at line 322. Loop `for attempt in range(_FAILURE_RECORD_MAX_RETRIES)` (line 361), `except OperationalError` (line 409), Sentry at exhaustion (line 426). `test_exhausts_retries_and_captures_once` pins `sleep_calls == [2, 4, 8, 16]` and `capture_exception.call_count == 1`. |
| 9 | Both `except TimeoutError` and `except Exception` branches in `run_import` use `_record_failure_with_retry` — no duplicated inline retry logic remains | VERIFIED | Lines 568 and 588 both call `_record_failure_with_retry(...)`. Neither branch contains its own `try: async with async_session_maker()` inline. |

**Score:** 9/9 truths verified

### Deferred Items

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Atomic duplicate-import guard (race window in `start_import` router) | Explicitly deferred | Not in scope for Phase 90 plans (all `requirements: []`); acknowledged in `import_service.py` line 74 comment; carried forward from CLAUDE.md FLAWCHESS-56 note. No later phase explicitly schedules it yet — Phase 90 is the last active phase. This is expected behavior, not a gap. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/import_service.py` | Stage 5 rewrite, three session scopes, `run_periodic_reaper`, `_record_failure_with_retry`, four constants | VERIFIED | All present. Confirmed via grep and direct read. |
| `app/repositories/import_job_repository.py` | `fail_orphaned_jobs` with `orphan_age_threshold` parameter; `ImportJobNotFound` exception class; `must_exist` on `update_import_job` | VERIFIED | Lines 11-18 (`ImportJobNotFound`), line 59 (`must_exist`), line 181 (`orphan_age_threshold`). |
| `app/main.py` | Lifespan-wired reaper task with `asyncio.create_task` + cancel-and-await on shutdown inside `try/finally` | VERIFIED | Lines 64 (create_task), 72-81 (cancel/await in try/finally wrapping `stop_engine`). |
| `tests/test_import_service.py` | Five test classes: `TestFlushBatchStage5`, `TestRunImportSessionPerBatch`, `TestFailOrphanedJobsAgeThreshold`, `TestPeriodicReaper`, `TestRecordFailureWithRetry` | VERIFIED | All five classes found (lines 1330, 2283, 1785, 1936, 2049). Total: 53 tests pass. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_flush_batch Stage 5` | `sqlalchemy.update + bindparam` | `session.execute(move_count_stmt, move_count_params)` | WIRED | Lines 744-753, 755-769. No `case()` call in Stage 5 body (only in comment at line 729). |
| `run_import` | `async_session_maker` | three `async with` helpers (bootstrap, per-batch, completion) | WIRED | `_bootstrap_import_job` line 439, `_flush_batch_with_progress` line 467, `_complete_import_job` line 492. |
| `app/main.py::lifespan` | `import_service.run_periodic_reaper` | `asyncio.create_task(run_periodic_reaper(), name="periodic-orphan-reaper")` | WIRED | `app/main.py` line 64; import confirmed on line 21. |
| `_record_failure_with_retry` | `sqlalchemy.exc.OperationalError` | `except OperationalError as exc: last_exc = exc; continue` | WIRED | Line 409. `OperationalError` imported at line 28. |
| `run_import except blocks` | `_record_failure_with_retry` | direct `await` call | WIRED | `except TimeoutError` line 568, `except Exception` line 588. No inline session/retry code in either branch. |
| `fail_orphaned_jobs` | `started_at < cutoff` WHERE clause | `cutoff = datetime.now(timezone.utc) - orphan_age_threshold` (Python-computed) | WIRED | Lines 203-205. Bound as parameter (not SQL `NOW()` function) per plan spec. |

---

### Data-Flow Trace (Level 4)

Not applicable — Phase 90 ships no data-rendering components. All artifacts are service/repository/task code with no frontend rendering path.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 90 test classes green | `uv run pytest tests/test_import_service.py::TestFlushBatchStage5 tests/test_import_service.py::TestRunImportSessionPerBatch tests/test_import_service.py::TestFailOrphanedJobsAgeThreshold tests/test_import_service.py::TestPeriodicReaper tests/test_import_service.py::TestRecordFailureWithRetry -x -q` | `21 passed in 0.19s` | PASS |
| Full test_import_service.py suite | `uv run pytest tests/test_import_service.py -x -q` | `53 passed in 0.23s` | PASS |
| Ruff clean | `uv run ruff check app/services/import_service.py app/repositories/import_job_repository.py app/main.py` | `All checks passed!` | PASS |
| ty clean | `uv run ty check app/ tests/` | `All checks passed!` | PASS |
| `bindparam` count >= 4 | `grep -c 'bindparam("b_' app/services/import_service.py` | `4` (lines 746, 747, 766, 767) | PASS |
| `case` not imported | `grep '^from sqlalchemy import' app/services/import_service.py` | `bindparam, select, update` (no `case`) | PASS |
| `previous_job.` at most 1 match | `grep -c 'previous_job\.' app/services/import_service.py` | `1` (scalar extraction line 445 only) | PASS |
| Reaper wired in lifespan | `grep 'asyncio.create_task(run_periodic_reaper' app/main.py` | found at line 64 | PASS |
| `stop_engine()` in `finally` | `app/main.py` lifespan structure | lines 67-81: outer `try/finally` with inner `try/except CancelledError/except Exception` | PASS (WR-03 fixed) |
| `_flush_batch` does NOT commit | `sed -n '653,772p' ... grep session.commit` | comment only (line 689), no live call | PASS (WR-05 fixed) |

---

### Probe Execution

No probe scripts discovered under `scripts/*/tests/probe-*.sh`. Not applicable.

---

### Requirements Coverage

Phase 90 plans all declare `requirements: []`. Phase 90 is a post-v1.17 carry-forward defect-fix that predates any formal requirement in `REQUIREMENTS.md`. No requirement IDs to cross-reference. The phase is scoped entirely by the goals in the plan `<objective>` blocks and the roadmap entry in `STATE.md`.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TBD/FIXME/XXX/TODO/HACK markers found in any modified file. No stub returns. No empty handlers. |

Note on WR-02 (docstring accuracy): the REVIEW identified a docstring/comment claiming "2/4/8/16/30s" but the actual schedule is 2/4/8/16s (30s total). The REVIEW fix commit `2262fb15` corrected this. The corrected docstring at line 338-341 of `import_service.py` now reads "2/4/8/16s = 30s total" and `test_exhausts_retries_and_captures_once` pins `sleep_calls == [2, 4, 8, 16]`. Verified correct.

---

### Human Verification Required

#### 1. RSS-flat import behavior (primary leak prevention goal)

**Test:** Start `bin/run_local.sh`, import a real ~5k+ game chess.com or lichess account. While the import runs, sample RSS every 5 seconds: `while true; do ps -o rss= -p $(pgrep -f uvicorn) 2>/dev/null; sleep 5; done` (or `docker stats flawchess-dev-backend --no-stream --format "{{.MemUsage}}"` in a loop).
**Expected:** RSS stays within +/-15% of the baseline reading taken after the first batch. It must NOT climb linearly with batch count (pre-fix behavior was ~0.48 MB/game growth). A flat or gently oscillating profile across the full import constitutes passing.
**Why human:** Requires a live chess.com/lichess API connection and the full Stockfish eval pool running. Cannot be reproduced in CI without external API credentials and heavy compute. Measurement must be over a large enough import (5k+ games = 400+ batches) to distinguish flat from slow-drift.

#### 2. Postgres-only restart mid-import (reaper and retry-helper behavior)

**Test:**
```bash
# While a large import is running:
docker compose -f docker-compose.dev.yml -p flawchess-dev kill postgres
sleep 2
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d postgres

# Expected outcome A (import still alive in backend):
# _record_failure_with_retry should ride out the ~2s recovery window
# and write the failed status within 30s.

# Expected outcome B (import died with backend):
# After backend recovery, within 5 min the periodic reaper should
# reap the orphaned in_progress job (3h threshold not reached).
```
**Expected:** Within 5 minutes of Postgres recovery, no `in_progress` jobs remain stranded. The job row transitions to `failed` either via the retry helper or the reaper.
**Why human:** Requires killing the Docker container mid-import without also killing the backend, which is not safely automatable in CI.

#### 3. Sentry FLAWCHESS-56 / FLAWCHESS-3Q do not recur in production

**Test:** After `bin/deploy.sh` promotes Phase 90 to the `production` branch: trigger a large import (~5k games) for a real user. Monitor https://flawchess.sentry.io for 48h for new occurrences of FLAWCHESS-56 (memory growth) or FLAWCHESS-3Q (stuck in_progress) patterns.
**Expected:** No new occurrences. Both issues should be closeable.
**Why human:** Production-only signal requiring real traffic and time-based observation.

---

### Gaps Summary

No gaps. All 9 must-haves are verified in the codebase with direct code evidence and passing tests. The duplicate-import guard is explicitly deferred (not scoped to Phase 90 in any plan) and its absence is documented in the codebase itself.

The REVIEW's 8 critical/warning findings (CR-01 + WR-01..WR-07) are all closed per the REVIEW's "Fixes Applied" section and confirmed by code inspection:

- **CR-01:** `ImportJobNotFound` exception + `must_exist=True` param — present in `import_job_repository.py` lines 11-18, 59, 75-76; handled in `_record_failure_with_retry` lines 393-408.
- **WR-01:** Three helper functions extracted from `run_import` (`_bootstrap_import_job`, `_flush_batch_with_progress`, `_complete_import_job`) — nesting in `run_import` body is now at most 4 levels (try → asyncio.timeout → httpx.AsyncClient → async for).
- **WR-02:** Docstring corrected to "2/4/8/16s (30s total)"; backoff schedule pinned in `test_exhausts_retries_and_captures_once`.
- **WR-03:** `stop_engine()` unconditional via `try/finally` wrapping the reaper cancel-and-await — `app/main.py` lines 67-81.
- **WR-04:** `literal_binds=True` compilation + integer-id absence assertion in `test_stage5_sql_text_invariant_across_batches` (line 1751).
- **WR-05:** `_flush_batch` does not call `session.commit()`; caller (`_flush_batch_with_progress`) owns the single atomic transaction per batch.
- **WR-06:** `_make_game_iterator` signature uses `Callable[[], None]` and returns `AsyncIterator[NormalizedGame]` (lines 602-603).
- **WR-07:** Explicit `except asyncio.CancelledError: raise` in `_record_failure_with_retry` (line 389-392); cancellation contract documented in docstring.

---

_Verified: 2026-05-20T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
