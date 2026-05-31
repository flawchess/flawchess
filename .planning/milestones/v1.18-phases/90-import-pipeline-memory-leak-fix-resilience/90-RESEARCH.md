# Phase 90: Import Pipeline Memory Leak Fix + Resilience — Research

**Researched:** 2026-05-20
**Domain:** SQLAlchemy 2.x async + asyncpg, session lifecycle, background-task resilience
**Confidence:** HIGH (the leak diagnosis is empirically settled in SEED-018 + debug note; the four scope items reduce to known, well-bounded code edits)

## Summary

The 2026-05-16 production OOM (FLAWCHESS-56 / FLAWCHESS-3Q) has a fully diagnosed root cause: `_flush_batch` Stage 5 builds a literal `case()`+`IN` UPDATE whose SQL text varies per batch (game-id set differs every batch). SQLAlchemy's compilation cache (`Compiled` objects with default `query_cache_size=500`) and asyncpg's per-connection prepared-statement LRU (`statement_cache_size`, default 100) both grow on the import-lifetime `AsyncSession`. Tracemalloc on a real-PGN harness localized the growth to `sqlalchemy/sql/compiler.py:1770` and `asyncpg/connection.py:481`, matching ~0.48 MB/game in prod.

The fix is a four-part code change in a single file (`app/services/import_service.py`) plus a small touch to `app/main.py`. No schema migrations. No new runtime dependencies. The hardest correctness landmine is the `result_fen` None-handling in Stage 5 — a naive `executemany` would silently NULL games without a `result_fen`. The cleanest preservation is **two `executemany` groups** (one updating `move_count` only; one updating `move_count` + `result_fen` for games where `result_fen is not None`).

**Primary recommendation:** Land all four items as one phase, one PR. The leak fix and session-recycle are tightly coupled (session-recycle is defense-in-depth for the same root cause); the reaper and failure-retry are leak-independent but small. Verification is manual against a real ~5k-game account in dev (watch backend container RSS via `docker stats`); no automated regression test per the scope-shaping note (already locked decision).

## User Constraints (from scope brief — equivalent to CONTEXT.md for this phase)

### Locked Decisions

1. **Primary leak fix** — replace `_flush_batch` Stage 5's literal `case()`+`IN` bulk UPDATE with bound-parameter `executemany`. Must preserve `result_fen` None-handling (two `executemany` groups, COALESCE, or keep-existing pattern). No silent NULL regression for games lacking a `result_fen`.
2. **Defense-in-depth session-recycle** — scope `AsyncSession` per batch inside `run_import`'s loop (currently one session for the whole import at `import_service.py:287`). Must cover job-record creation, the `previous_job` / `since` lookup, and per-batch progress commits.
3. **Scheduled / on-reconnect orphan-job reaper** — `cleanup_orphaned_jobs()` (currently only on backend startup, wired in `app/main.py` lifespan) must also run periodically and/or on a DB-reconnect signal so a Postgres-only restart doesn't strand `in_progress` jobs.
4. **Resilient failure-state recording** — bounded retry + backoff around the `except Exception` UPDATE in `run_import` (~lines 392–416) so a still-recovering DB doesn't swallow the `failed` transition.

### Claude's Discretion

- Exact mechanism for preserving `result_fen` None-handling (two `executemany` groups vs. COALESCE vs. Python-side merge). Recommend two groups (§A2).
- Reaper scheduling mechanism — periodic `asyncio.create_task` loop vs. on-reconnect engine event. Recommend a plain `while True: await asyncio.sleep(N)` loop wired in lifespan (§C2). No on-reconnect hook unless trivial.
- Retry helper shape — hand-rolled loop vs. add `tenacity`. Recommend hand-rolled, mirroring the existing `lichess_client.py` pattern (§D2). No new dependency.
- Reaper cadence and orphan-age threshold. Recommend every 5 min, orphan-age ≥ `IMPORT_TIMEOUT_SECONDS` (3 hours) (§C3).
- Retry budget. Recommend 5 attempts, exponential backoff starting at 2s, capped at ~60s total (§D3).

### Deferred Ideas (OUT OF SCOPE)

- **Atomic duplicate-import guard.** SEED-018 demoted from "load-bearing" to optional UX/data-hygiene after the OOM-causation premise was disproven (a single import OOMs alone). Real bug but not recurrence-preventing.
- **Automated regression test for the leak.** Both options (statement-text invariance assertion, tracemalloc/RSS growth assertion) were considered and rejected per the scope-shaping note: statement-text-invariance doesn't actually prove flat memory; tracemalloc/RSS is a 10+ min test-suite liability (the SEED-018 local harness already timed out at 600s reaching only batch 10).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Per-batch bulk UPDATE (Stage 5 rewrite) | Service (`import_service.py:_flush_batch`) | — | Mechanically owned by the orchestrator that already holds the `AsyncSession`; not large enough to extract into a repository helper. |
| Session lifecycle (per-batch scope) | Service (`import_service.py:run_import`) | — | The orchestrator owns the import-job lifecycle; pushing session-scope into repositories would invert ownership. |
| Periodic orphan reaper | Service (`import_service.py:cleanup_orphaned_jobs` already lives here) wired in App (`main.py` lifespan) | — | Reuses existing reaper function; `main.py` lifespan is the natural attach point. |
| Failure-state retry | Service (`import_service.py:run_import` except blocks) | — | Co-located with the failure handlers it wraps; not generic enough to extract. |
| DB access (bulk UPDATE primitive) | Repository (`game_repository.py`) — **stays as-is** | Service | The bulk-UPDATE is small and inline; matching the existing `bulk_insert_games` style is fine but not required. |

## Phase Requirements

This is a defect-fix phase, not requirement-tracked. No requirement IDs apply. The four scope items in "Locked Decisions" above stand as the phase's acceptance criteria.

## Standard Stack

Already in `pyproject.toml`. Nothing to add. `[VERIFIED: pyproject.toml read]`

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ≥2.0.0 (async) | ORM + Core, async session, `bindparam` / `executemany` | Already in stack; the documented executemany pattern is `session.execute(update_stmt, list_of_dicts)`. `[VERIFIED: pyproject.toml]` |
| asyncpg | ≥0.29.0 | PostgreSQL driver | Already in stack; statement-cache config available via `connect_args={"statement_cache_size": N}` if needed. `[VERIFIED: pyproject.toml]` |
| sentry-sdk[fastapi] | ≥2.54.0 | Error capture | Already in stack; per-CLAUDE.md "retry loops: capture on last attempt only". `[VERIFIED: pyproject.toml]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled retry loop | `tenacity` | New dep; the existing `lichess_client.py` retry pattern (manual `for attempt in range(_MAX_RETRIES + 1)` with `await asyncio.sleep(backoff)`) already covers this without adding surface area. **Use hand-rolled.** |
| Periodic `asyncio.create_task` loop | APScheduler / FastAPI BackgroundTasks | APScheduler is overkill (one periodic task); FastAPI `BackgroundTasks` is request-scoped, not lifespan-scoped. **Use plain `asyncio.create_task` + sleep loop in `lifespan`.** `[ASSUMED]` (no current periodic task in repo to confirm idiom) |
| Two `executemany` groups for None-handling | `COALESCE(:rf, result_fen)` in a single SQL | The `COALESCE` route is one statement but: (a) a search result flagged that SQLAlchemy 2.x can drop `COALESCE` expressions from `update().values()` in some executemany contexts (`text(str(stmt))` workaround), introducing fragility; (b) two groups is more explicit and matches the existing batched style. **Use two groups.** `[CITED: github.com/sqlalchemy/sqlalchemy/issues/9075]` |

**Installation:** none (no new packages).

**Version verification (already-installed dependencies):** `sqlalchemy>=2.0.0`, `asyncpg>=0.29.0`, `sentry-sdk>=2.54.0` per pyproject.toml. No version bumps required.

## Package Legitimacy Audit

> No new external packages are installed in this phase. The audit is N/A.

All code changes use libraries already pinned in `pyproject.toml` (SQLAlchemy, asyncpg, sentry-sdk, stdlib `asyncio`). No `npm install` / `uv add` / `pip install` actions.

## Architecture Patterns

### System Architecture (data flow through the import worker)

```
POST /imports  ──►  routers/imports.py
                       │
                       │  asyncio.create_task(run_import(job_id))
                       ▼
        ┌────────────────────────────────────────────────────────────────┐
        │ run_import (background task — never re-raises)                 │
        │                                                                │
        │  ┌─ async with asyncio.timeout(3h) ──────────────────────────┐ │
        │  │                                                           │ │
        │  │  Phase 90 change: open a *bootstrap* session for job-     │ │
        │  │  record creation + previous_job lookup, then close it.    │ │
        │  │                                                           │ │
        │  │  async for game_dict in game_iter:                         │ │
        │  │     batch.append(...)                                      │ │
        │  │     if len(batch) >= _BATCH_SIZE:                          │ │
        │  │        ┌─ Phase 90 change: per-batch session ──────────┐  │ │
        │  │        │ async with async_session_maker() as session:   │  │ │
        │  │        │   _flush_batch(session, batch, user_id)        │  │ │
        │  │        │     Stage 1: bulk_insert_games                 │  │ │
        │  │        │     Stage 2: bulk_insert_positions             │  │ │
        │  │        │     Stage 3/4: engine eval + apply_eval        │  │ │
        │  │        │     Stage 5: TWO executemany groups            │  │ │
        │  │        │       (a) move_count-only for ALL ids          │  │ │
        │  │        │       (b) move_count+result_fen for non-None   │  │ │
        │  │        │   update_import_job(progress)                  │  │ │
        │  │        │   session.commit()                             │  │ │
        │  │        └────────────────────────────────────────────────┘  │ │
        │  │        batch = []                                          │ │
        │  └───────────────────────────────────────────────────────────┘ │
        │                                                                │
        │  except Exception (Phase 90 change: bounded retry on UPDATE):  │
        │     for attempt in range(_FAILURE_RECORD_MAX_RETRIES + 1):     │
        │        try: open session, update job→failed, commit            │
        │        except transient DB error: await asyncio.sleep(backoff) │
        │        else: break                                             │
        │     # capture_exception on last attempt only (CLAUDE.md rule)  │
        └────────────────────────────────────────────────────────────────┘

        ┌────────────────────────────────────────────────────────────────┐
        │ lifespan (Phase 90 change: add periodic reaper task)           │
        │                                                                │
        │  await cleanup_orphaned_jobs()       # existing — startup once │
        │  reaper_task = asyncio.create_task(_periodic_reaper())         │
        │  try: yield                                                    │
        │  finally:                                                      │
        │     reaper_task.cancel(); await reaper_task                    │
        │     await stop_engine()                                        │
        │                                                                │
        │  async def _periodic_reaper():                                 │
        │     while True:                                                │
        │        await asyncio.sleep(_REAPER_INTERVAL_SECONDS)           │
        │        try: await cleanup_orphaned_jobs()                      │
        │        except Exception: log + capture_exception               │
        └────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| File | Function | Phase 90 change |
|------|----------|-----------------|
| `app/services/import_service.py` | `_flush_batch` Stage 5 (lines 544–557) | Rewrite to two `executemany` groups with `bindparam`. |
| `app/services/import_service.py` | `run_import` (lines 264–416) | Restructure session scope: bootstrap session for job creation, per-batch session inside the loop, bounded-retry session for failure recording. |
| `app/services/import_service.py` | New: `_periodic_reaper` coroutine | Lifespan-wired periodic loop calling `cleanup_orphaned_jobs()`. |
| `app/services/import_service.py` | New: `_record_failure_with_retry` helper | Encapsulate the bounded retry around `update_import_job(status="failed", ...)`. Reused by the `TimeoutError` and generic `except Exception` branches. |
| `app/main.py` | `lifespan` | Start/cancel the reaper task. |
| `app/repositories/import_job_repository.py` | `fail_orphaned_jobs` | Extend with an `orphan_age_threshold` parameter (default 3h) so the periodic reaper doesn't kill an in-flight slow import. **Critical** — see §F3 risk. |

### Pattern 1: SQLAlchemy 2.x `executemany` with `bindparam`

**What:** A single compiled UPDATE statement whose `:param` placeholders are filled per-row from a list of dicts. The SQL text is invariant across batches → SQLAlchemy compiles once + asyncpg prepares once → no per-batch cache growth.

**When to use:** Any bulk-UPDATE where the row count or row identities vary across calls.

**Example (the Stage 5 rewrite):**

```python
# Source: SQLAlchemy 2.x tutorial — UPDATE with bindparam executemany
# https://docs.sqlalchemy.org/en/20/tutorial/data_update.html
from sqlalchemy import bindparam, update

# Group (a): move_count-only update for ALL games in the batch
move_count_stmt = (
    update(Game)
    .where(Game.id == bindparam("b_id"))
    .values(move_count=bindparam("b_mc"))
)
move_count_params = [
    {"b_id": gid, "b_mc": mc}
    for gid, mc in rows_result.move_counts.items()
]
if move_count_params:
    await session.execute(move_count_stmt, move_count_params)

# Group (b): result_fen update ONLY for games where result_fen is not None.
# This preserves the existing behavior — games without a result_fen keep
# whatever default the column has (currently NULL), they are NOT actively
# overwritten to NULL.
fen_stmt = (
    update(Game)
    .where(Game.id == bindparam("b_id"))
    .values(result_fen=bindparam("b_rf"))
)
fen_params = [
    {"b_id": gid, "b_rf": fen}
    for gid, fen in rows_result.result_fens.items()
    if fen is not None
]
if fen_params:
    await session.execute(fen_stmt, fen_params)
```

**Gotchas:**
- The `where(Game.id == bindparam("b_id"))` placeholder names must NOT collide with the column names — SQLAlchemy will treat `bindparam("id")` ambiguously. Use a `b_` prefix (matches SEED-018's `b_id` / `mc` / `rf` example).
- `CursorResult.rowcount` is not reliable for executemany-style updates with some DBAPIs. Don't gate logic on it; the `len(rows_result.move_counts)` from the helper is the source of truth. `[CITED: docs.sqlalchemy.org/en/20/tutorial/data_update.html]`
- Empty parameter lists must short-circuit (don't call `execute(stmt, [])` — behavior is driver-specific and risks a no-op being treated as an error).

### Pattern 2: Per-batch `AsyncSession` scope

**What:** Open a fresh `AsyncSession` inside the batch loop; close it (via `async with`) before the next batch. The bootstrap work (job-record creation, previous-job lookup) happens in a separate session before the loop.

**When to use:** Long-running background workers that accumulate per-connection state (statement cache, identity map, transaction state).

**Example shape:**

```python
# Bootstrap session — short-lived, just for job-record + previous_job lookup
async with async_session_maker() as bootstrap_session:
    previous_job = await import_job_repository.get_latest_for_user_platform(
        bootstrap_session, job.user_id, job.platform, job.username,
    )
    await import_job_repository.create_import_job(
        bootstrap_session,
        job_id=job_id, user_id=job.user_id,
        platform=job.platform, username=job.username,
    )
    await bootstrap_session.commit()
# bootstrap_session is now closed — no state leaks into the batch loop

async with httpx.AsyncClient(timeout=60.0) as client:
    game_iter = _make_game_iterator(client, job, previous_job, _on_game_fetched)
    batch: list[NormalizedGame] = []
    async for game_dict in game_iter:
        batch.append(game_dict)
        if len(batch) >= _BATCH_SIZE:
            async with async_session_maker() as session:
                imported = await _flush_batch(session, batch, job.user_id)
                job.games_imported += imported
                await import_job_repository.update_import_job(
                    session, job_id=job_id, status="in_progress",
                    games_fetched=job.games_fetched,
                    games_imported=job.games_imported,
                )
                await session.commit()
            batch = []
    # ...trailing batch same pattern...

# Completion session — short-lived
async with async_session_maker() as session:
    await import_job_repository.update_import_job(session, job_id=job_id, **completion_fields)
    await session.commit()
```

**Gotchas:**
- `previous_job` is the only ORM-mapped object that needs to cross session boundaries. After the bootstrap session closes, `previous_job` becomes detached but its scalar columns (`last_synced_at`) are still accessible because `expire_on_commit=False` is set in `async_session_maker`. **Verify:** `previous_job.last_synced_at` access works post-close (it should — it's a loaded scalar). `[ASSUMED]` (must be confirmed by reading the value in the new flow; if it lazy-loads, switch to fetching just the timestamp into a local `datetime` variable inside the bootstrap session).
- Each batch session is one new connection acquisition from the pool. With `pool_size=20, max_overflow=30`, the per-batch overhead is ~1–5 ms against dev Postgres (per the scope-shaping note). Negligible.

### Pattern 3: Periodic reaper task wired in lifespan

**What:** A long-running coroutine started in `lifespan` startup, cancelled in lifespan shutdown.

**Example shape:**

```python
# app/services/import_service.py — new helpers
_REAPER_INTERVAL_SECONDS = 5 * 60  # 5 minutes


async def run_periodic_reaper() -> None:
    """Periodically mark stuck import jobs as failed.

    Companion to cleanup_orphaned_jobs (which only runs at backend startup).
    A Postgres-only restart leaves the backend up, so without this loop
    orphaned in_progress jobs would stay stuck until the next backend deploy.
    """
    while True:
        await asyncio.sleep(_REAPER_INTERVAL_SECONDS)
        try:
            await cleanup_orphaned_jobs()
        except Exception:
            logger.exception("Periodic orphan-job reaper failed")
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.capture_exception()


# app/main.py — lifespan modification
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()
    await cleanup_orphaned_jobs()
    await start_engine()
    reaper_task = asyncio.create_task(run_periodic_reaper())
    try:
        yield
    finally:
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        await stop_engine()
```

**Gotchas:**
- The reaper's first cleanup happens at `T + interval`, not at startup. The existing startup-time `cleanup_orphaned_jobs()` call still runs — keep it.
- Cancellation must be awaited (`await reaper_task` after `cancel()`) so the coroutine actually unwinds before `stop_engine()`. The `asyncio.CancelledError` is expected.
- `cleanup_orphaned_jobs()` currently has **no age threshold** — it marks ANY `in_progress` job as failed. This is safe at startup (no in-flight tasks survive a restart) but **unsafe periodically** during a live import. See §F3.

### Pattern 4: Bounded retry for failure-state recording

**What:** A small `for attempt in range(N): try ... except transient ... await asyncio.sleep(backoff)` loop. Mirrors `app/services/lichess_client.py:116–135`.

**Example shape (new helper in `import_service.py`):**

```python
from asyncpg.exceptions import CannotConnectNowError, ConnectionDoesNotExistError

_FAILURE_RECORD_MAX_RETRIES = 5
_FAILURE_RECORD_BACKOFF_BASE_SECONDS = 2
_FAILURE_RECORD_TRANSIENT_ERRORS = (CannotConnectNowError, ConnectionDoesNotExistError)


async def _record_failure_with_retry(
    job_id: str,
    *,
    status: str,
    games_fetched: int,
    games_imported: int,
    error_message: str,
    completed_at: datetime,
) -> None:
    """Persist a job's failure state with bounded retry against DB recovery.

    Bug fix (Phase 90): the original except-block in run_import opened a new
    session and immediately UPDATEd while Postgres was still in crash recovery
    (CannotConnectNowError, FLAWCHESS-3Q). That caused the job to stay
    in_progress forever. Retry across a ~60s recovery window before giving up.
    """
    last_exc: BaseException | None = None
    for attempt in range(_FAILURE_RECORD_MAX_RETRIES + 1):
        if attempt > 0:
            backoff = _FAILURE_RECORD_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            await asyncio.sleep(min(backoff, 30))
        try:
            async with async_session_maker() as session:
                await import_job_repository.update_import_job(
                    session, job_id=job_id, status=status,
                    games_fetched=games_fetched, games_imported=games_imported,
                    error_message=error_message, completed_at=completed_at,
                )
                await session.commit()
                return
        except _FAILURE_RECORD_TRANSIENT_ERRORS as exc:
            last_exc = exc
            continue
        except Exception as exc:
            # Non-transient — log + give up immediately (no point retrying).
            logger.exception("Non-transient failure recording job %s", job_id)
            sentry_sdk.capture_exception(exc)
            return

    # All retries exhausted — capture once per CLAUDE.md (last attempt only).
    logger.error(
        "Failed to record failure state for job %s after %d retries",
        job_id, _FAILURE_RECORD_MAX_RETRIES,
    )
    if last_exc is not None:
        sentry_sdk.capture_exception(last_exc)
```

**Gotchas:**
- CLAUDE.md "Retry loops: capture on last attempt only" — do **not** call `capture_exception` per attempt. Only after the loop exits unsuccessfully.
- The SQLAlchemy `DBAPIError` wraps asyncpg exceptions; `app/main.py:_sentry_before_send` already walks the `__cause__` chain. Catch the asyncpg types directly here too — the SQLAlchemy wrapper presents them as `DBAPIError` with `__cause__` set, so `except (CannotConnectNowError, ConnectionDoesNotExistError)` may not match. **Catch `sqlalchemy.exc.DBAPIError` and inspect `__cause__`** for robustness, OR catch `OperationalError` (the SQLAlchemy parent for connection issues). `[ASSUMED]` — verify with one local exception-type test against the dev DB.
- Total worst-case budget at 5 retries × backoff 2/4/8/16/30 = ~60s. The Postgres crash-recovery window in the 2026-05-16 incident was ~2s (06:22:02 → 06:22:04 per the debug note), so this is generous.

### Anti-Patterns to Avoid

- **Calling `asyncio.gather` on the same `AsyncSession` for the executemany rewrite.** CLAUDE.md hard rule. The existing per-batch eval pass already uses gather only on the engine pool, not on session writes. Don't change that.
- **Putting `COALESCE` in `values(result_fen=func.coalesce(bindparam("b_rf"), Game.result_fen))`.** A SQLAlchemy issue (#9075) reports that `update().values()` can drop the COALESCE expression in executemany contexts, requiring `text(str(stmt))` as a workaround. Use two groups instead.
- **Putting `asyncio.sleep` inside the batch loop.** Don't add artificial throttling — the per-batch session acquire is already the implicit pacing.
- **Reaping ALL in_progress jobs periodically.** Without an age threshold, the reaper would kill the live import it's competing with. See §F3.
- **Catching `Exception` in the retry loop and continuing.** Only catch transient connection errors. A non-transient bug (e.g. schema drift) must surface immediately.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk UPDATE with per-row values | A CASE/IN expression built dynamically per call | `update().where(col == bindparam(...)).values(col=bindparam(...))` + `session.execute(stmt, list_of_dicts)` | This is exactly what SQLAlchemy's executemany support is for; rolling your own re-introduces the leak. `[CITED: docs.sqlalchemy.org/en/20/tutorial/data_update.html]` |
| Exponential backoff | A custom backoff schedule with jitter etc. | The same `_RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))` pattern from `lichess_client.py` | Already in the codebase; consistency > novelty for a 5-attempt loop. |
| Periodic background task | APScheduler, Celery beat | Plain `asyncio.create_task` + `while True: await asyncio.sleep(N)` in lifespan | One periodic task; APScheduler is a new dep + new failure surface. |
| Transient DB error detection | New error-classification module | Catch `sqlalchemy.exc.OperationalError` (or `DBAPIError` and check `__cause__`); the existing `_sentry_before_send` already does the same walk. | `_DB_TRANSIENT_ERRORS = (ConnectionDoesNotExistError, CannotConnectNowError)` is already defined in `app/main.py` — could expose it as a public constant rather than duplicate. |

**Key insight:** Three of these four items are direct mirrors of existing patterns in the codebase (`lichess_client.py` retry, `app/main.py` transient-error classification, `app/main.py` lifespan). The only genuinely new pattern is the `executemany` rewrite, and that's textbook SQLAlchemy 2.x.

## Runtime State Inventory

> This phase is a code-fix, not a rename/refactor. The category is included only to confirm no runtime state is implicated.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no schema change. `import_jobs` table is read/written, but no columns are added or migrated. | None |
| Live service config | None — no Datadog / Cloudflare / external service tags reference the changed code paths. | None |
| OS-registered state | None — no systemd / Task Scheduler / launchd entries. The backend runs inside Docker on the prod host. | None |
| Secrets / env vars | None — `DATABASE_URL` unchanged. `STOCKFISH_POOL_SIZE`, `_BATCH_SIZE` unchanged (the latter is a Python constant). | None |
| Build artifacts | None — no Alembic migration, no codegen step (e.g. `gen_endgame_zones_ts.py`), no compiled binary. | None |

**Nothing found in any category.** Verified by: reading `app/services/import_service.py`, `app/main.py`, `app/repositories/import_job_repository.py`, `app/core/database.py`, and the seed/debug notes.

## Common Pitfalls

### Pitfall 1: Silent `result_fen` NULL regression
**What goes wrong:** A naive `executemany` with `update(Game).values(result_fen=bindparam("b_rf"))` writes whatever value the dict provides — including `None`. Games imported before the fix whose PGN parser couldn't extract a `result_fen` would get their (existing) `result_fen` overwritten to NULL on re-import. Worse, fresh imports of unparseable games would NULL the column they would previously have left untouched (`fen_case_map` filters None; `case(else_=None)` keeps the column current via the `else_` clause).
**Why it happens:** The current `case(fen_case_map, value=Game.id, else_=None)` is conditional in TWO ways: (a) only games WITH a fen go into `fen_case_map`, AND (b) `else_=None` is a SQLAlchemy idiom that — combined with `update().values()` semantics — does NOT generate a SQL `NULL` write for unmatched rows; SQLAlchemy emits a CASE that resolves to the column's current value for the `else_` branch. Re-read the current code carefully before designing the rewrite.
**How to avoid:** Two `executemany` groups. Group (a) updates `move_count` for all batch ids. Group (b) updates `result_fen` only for ids where the new `result_fen is not None`. Verify with a test that (i) `move_count` lands for all games, (ii) `result_fen` lands ONLY for games with a parsed fen, (iii) games without a parsed fen keep their prior `result_fen` value (or stay NULL if never set).
**Warning signs:** A test "game has move_count but no result_fen still has its old result_fen" failing post-rewrite. A quick check in dev: import a known-bad PGN that parses to `result_fen=None`, confirm the column is unchanged from a prior import.

### Pitfall 2: `previous_job` lazy-load across session boundary
**What goes wrong:** After moving job creation + previous-job lookup into a bootstrap session, the `previous_job` ImportJob instance is detached. If `_make_game_iterator` accesses any attribute that wasn't loaded during the bootstrap session, SQLAlchemy raises `DetachedInstanceError`.
**Why it happens:** `expire_on_commit=False` keeps already-loaded scalars accessible after commit, but does NOT protect against accessing relationships or columns that weren't part of the original SELECT.
**How to avoid:** `get_latest_for_user_platform` returns the full ORM instance and the downstream uses are limited to `previous_job.last_synced_at` (scalar) — that's safe. To be defensive, extract `last_synced_ms_or_dt = previous_job.last_synced_at` inside the bootstrap session and pass the scalar, not the ORM instance, to `_make_game_iterator`. This also tightens the type signature.
**Warning signs:** `DetachedInstanceError` on the first batch. Test: existing run_import tests should still pass — if they don't, the boundary is wrong.

### Pitfall 3: Periodic reaper killing the live import
**What goes wrong:** `cleanup_orphaned_jobs()` calls `fail_orphaned_jobs()` which marks ANY `in_progress` job as failed. Run periodically, this reaps the live import after one interval (5 min), even though it's healthy and progressing.
**Why it happens:** The current `fail_orphaned_jobs()` definition (lines 154–172 in `import_job_repository.py`) has no age filter — it was written for startup-only use where every `in_progress` job is by definition orphaned.
**How to avoid:** Add an `orphan_age_threshold: timedelta` parameter to `fail_orphaned_jobs` (or a new variant for the periodic case) that filters `WHERE started_at < NOW() - threshold`. Default for the startup call: 0 (no threshold, current behavior). Default for the periodic call: `IMPORT_TIMEOUT_SECONDS` (3 hours) — matches `asyncio.timeout` so anything still in_progress past 3h has by definition exceeded its budget. Even safer: also gate on the absence of a recent `games_imported` bump (last-progress timestamp), but a simple started_at-based threshold suffices for the v1 reaper.
**Warning signs:** A live import's job transitions to `failed` with `error_message="Server restarted while import was in progress"` while the in-memory `JobState` is still `IN_PROGRESS` (the in-memory and DB views diverge).

### Pitfall 4: `OperationalError` vs `CannotConnectNowError` exception type mismatch
**What goes wrong:** The retry loop catches `(CannotConnectNowError, ConnectionDoesNotExistError)` but SQLAlchemy wraps the asyncpg exception in `sqlalchemy.exc.DBAPIError` / `OperationalError`. The `except` clause never matches, and the loop falls through on the first attempt.
**Why it happens:** SQLAlchemy's exception hierarchy wraps DBAPI exceptions; the wrapping happens before our try/except sees the error.
**How to avoid:** Either (a) catch `sqlalchemy.exc.DBAPIError` and inspect `exc.__cause__ isinstance(_DB_TRANSIENT_ERRORS)`, OR (b) catch `sqlalchemy.exc.OperationalError` (the SQLAlchemy parent class for connection issues — covers `CannotConnectNow`, `ConnectionDoesNotExist`, and a few more). Option (b) is simpler and matches typical SQLAlchemy patterns.
**Warning signs:** The retry loop logs "Failed to record failure state" without any retry attempts. Test: write a unit test that monkeypatches `update_import_job` to raise `OperationalError("test")` and assert the retry loop tries 5 times.

### Pitfall 5: Tracemalloc/RSS verification methodology drift
**What goes wrong:** Verification reports flat RSS but the leak is still present, just smaller or slower.
**Why it happens:** Verifying on a fresh backend process with low pool reuse, or measuring container RSS instead of process RSS, or sampling at intervals that miss the growth pattern.
**How to avoid:** Use `docker stats --no-stream` periodically AND `ps -p <pid> -o rss=` on the backend Python process AND watch `/proc/$PID/status | grep VmRSS` from inside the container for a triple-source agreement. The dev verification target is a 5k+ game account — that's ~5k × 0.48 MB ≈ 2.4 GB of leakage today, vs. flat after fix. The signal-to-noise is high; a single-import on a 100-game test account won't show the leak.
**Warning signs:** RSS climbs <10 MB across 5k games — looks "flat" but isn't actually verified. Demand a delta of >2 GB pre-fix vs. <100 MB post-fix to call it a confirmed flat.

## Code Examples

### Example 1: Two-group executemany Stage 5 (the primary fix)

```python
# Source: SQLAlchemy 2.x — https://docs.sqlalchemy.org/en/20/tutorial/data_update.html
# Replaces the current case()+IN UPDATE at app/services/import_service.py:544–557

# Stage 5: per-game move_count + result_fen via two executemany groups.
# Two groups because the current code intentionally writes result_fen ONLY
# for games that have one (preserves prior value otherwise). Phase 90 fix.
if rows_result.move_counts:
    move_count_stmt = (
        update(Game)
        .where(Game.id == bindparam("b_id"))
        .values(move_count=bindparam("b_mc"))
    )
    move_count_params = [
        {"b_id": gid, "b_mc": mc}
        for gid, mc in rows_result.move_counts.items()
    ]
    await session.execute(move_count_stmt, move_count_params)

    fen_params = [
        {"b_id": gid, "b_rf": fen}
        for gid, fen in rows_result.result_fens.items()
        if fen is not None
    ]
    if fen_params:
        fen_stmt = (
            update(Game)
            .where(Game.id == bindparam("b_id"))
            .values(result_fen=bindparam("b_rf"))
        )
        await session.execute(fen_stmt, fen_params)
```

### Example 2: Lichess retry loop (the template for failure-state recording)

```python
# Source: app/services/lichess_client.py — existing, in-tree pattern to mirror
for attempt in range(_MAX_RETRIES + 1):
    if attempt > 0:
        backoff = _RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
        logger.warning("retrying in %ds (attempt %d/%d)", backoff, attempt, _MAX_RETRIES)
        await asyncio.sleep(backoff)
    try:
        # ... operation ...
        return
    except (RetryableError,) as exc:
        last_attempt_error = exc
        continue
# After loop:
raise last_attempt_error  # OR capture_exception + return, per context
```

### Example 3: Existing `cleanup_orphaned_jobs` to reuse

```python
# Source: app/services/import_service.py:146–156 (current)
async def cleanup_orphaned_jobs() -> None:
    async with async_session_maker() as session:
        count = await import_job_repository.fail_orphaned_jobs(session)
        await session.commit()
        if count:
            logger.info("Marked %d orphaned import job(s) as failed", count)
```

Phase 90 change: extend `fail_orphaned_jobs(session, orphan_age_threshold: timedelta | None = None)` and pass `timedelta(seconds=IMPORT_TIMEOUT_SECONDS)` from the periodic reaper.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `session.execute(stmt)` per row in a Python loop | `session.execute(stmt, list_of_dicts)` executemany with `bindparam` | SQLAlchemy 2.0 (2023) cemented this as the bulk-DML idiom | The pattern needed here is mainline, not experimental. |
| ORM `bulk_update_mappings` (deprecated, 1.x style) | `update()` + `bindparam` + `executemany` | SQLAlchemy 2.0 deprecated `bulk_update_mappings` in favor of explicit Core constructs | Don't use `bulk_update_mappings` — it's legacy. |
| Long-lived `AsyncSession` for background workers | Per-task / per-batch `AsyncSession` | SQLAlchemy 2.x async docs explicitly recommend short-lived sessions for background workers | This is the canonical guidance, not a workaround. `[ASSUMED]` — confirmed by widespread community pattern but not pulled from a single canonical doc page. |

**Deprecated/outdated:**
- `bulk_update_mappings` — use `update()` + `bindparam` + `executemany` instead.
- `session.bulk_save_objects` — same.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Plain `asyncio.create_task` + `await asyncio.sleep(N)` is the idiomatic periodic-task pattern for FlawChess (no existing periodic task in repo to confirm) | §C2 / Pattern 3 | Low — even if APScheduler would have been preferred elsewhere, this is one task and easy to swap later. |
| A2 | `previous_job.last_synced_at` is accessible after the bootstrap session closes (scalar load + `expire_on_commit=False`) | Pitfall 2 | Medium — if it lazy-loads, the bootstrap split breaks the import. Mitigation: extract the scalar into a local before closing. |
| A3 | SQLAlchemy wraps `CannotConnectNowError` / `ConnectionDoesNotExistError` in `OperationalError` such that catching `OperationalError` is correct | Pitfall 4 | Medium — if not, the retry loop never triggers. Mitigation: catch `DBAPIError` and inspect `__cause__` chain (the same pattern `_sentry_before_send` already uses in `app/main.py`). |
| A4 | The per-batch session-acquire overhead is negligible (~1–5 ms / batch) against pooled Postgres | Pattern 2 | Low — even if 50 ms, a 5k-game import is ~417 batches × 50 ms ≈ 20s extra, well under the 3-hour timeout. |
| A5 | Per-batch unique SQL text is the dominant leak source (vs. the secondary `pg_insert(...).values(list)` with variable list lengths) | §F1 | Low — already empirically established in the debug note tracemalloc localization. |

**If any of A2, A3 prove wrong:** the planner should add a small Wave 0 task to verify the assumption in dev before the main implementation tasks.

## Open Questions

1. **Should `_FAILURE_RECORD_TRANSIENT_ERRORS` be defined where, exactly?**
   - What we know: `_DB_TRANSIENT_ERRORS = (ConnectionDoesNotExistError, CannotConnectNowError)` already exists in `app/main.py` for the `_sentry_before_send` fingerprint.
   - What's unclear: whether to duplicate it in `import_service.py` or move it to a shared module (`app/core/db_errors.py` or similar).
   - Recommendation: duplicate (two definitions) for now — extracting into a shared module is a refactor outside Phase 90 scope. Add a code comment cross-referencing the `_sentry_before_send` definition.

2. **Should `fail_orphaned_jobs` get the age threshold via a new function or a parameter?**
   - What we know: the startup call needs no threshold (every in_progress at startup is orphaned); the periodic call needs the 3-hour threshold.
   - What's unclear: whether a `Default = None`-means-no-threshold parameter is clearer than two functions.
   - Recommendation: one function with an optional parameter (`orphan_age_threshold: timedelta | None = None`). Two functions would duplicate the UPDATE.

3. **Should the `_BATCH_SIZE = 12` hotfix be raised back closer to 28 after the leak is fixed?**
   - What we know: the hotfix dropped it 28 → 12 in PR #99 to slow the bleed. Once the leak is fixed, the original 28 is presumably safe again.
   - What's unclear: whether the per-batch Stockfish eval pass (also added in Phase 41.1) has its own memory cost that benefits from the lower batch size independent of the leak.
   - Recommendation: **out of scope** for Phase 90. The fix is to land all 4 items at `_BATCH_SIZE=12`, verify, then a follow-up phase / quick task can re-evaluate batch size with the leak fixed. The roadmap entry and scope brief don't list batch-size tuning.

## Environment Availability

> Skipped — this phase is pure code changes. No new external tools, services, or runtimes. Existing stack (Python 3.13, uv, PostgreSQL 18, Docker Compose) already provisioned and verified by `bin/run_local.sh` working today.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_import_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

This phase has no requirement IDs (defect fix). Mapping the four scope items to test coverage:

| Scope Item | Behavior | Test Type | Automated Command | File Exists? |
|------------|----------|-----------|-------------------|-------------|
| Leak fix (Stage 5 executemany) — backfill correctness | `move_count` lands for all games in batch | unit / integration | `uv run pytest tests/test_import_service.py::TestRunImport -x` | ✅ (existing tests assert games imported; extend one to assert move_count value on a game without a result_fen) |
| Leak fix — `result_fen` None-preservation | A game without a parsed `result_fen` keeps its prior value (or stays NULL); the new value isn't overwritten | unit | `uv run pytest tests/test_import_service.py -k result_fen -x` | ❌ Wave 0 — add a test that imports a game with `result_fen=None` and asserts no NULL overwrite of a pre-existing value |
| Session-recycle | Existing `run_import` tests still pass after session restructure | integration | `uv run pytest tests/test_import_service.py::TestRunImport -x` | ✅ (existing 1314-line test file covers run_import shape extensively) |
| Periodic reaper | A `started_at` older than threshold transitions in_progress → failed; younger does not | unit | `uv run pytest tests/test_import_service.py::TestCleanupOrphanedJobs -x` | ❌ Wave 0 — add age-threshold tests; existing tests cover the no-threshold (startup) case |
| Failure-state retry | Retry on `OperationalError`, success on 2nd attempt; exhaustion captures to Sentry once | unit | `uv run pytest tests/test_import_service.py -k failure_retry -x` | ❌ Wave 0 — new test class |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_import_service.py -x` (~1s; the file is fully mocked, no DB)
- **Per wave merge:** `uv run pytest` (full backend suite, ~30s)
- **Phase gate:** Full suite green + `uv run ruff check .` + `uv run ty check app/ tests/` + manual dev import of a real 5k+ game account with backend RSS observation (see Pitfall 5 methodology)

### Wave 0 Gaps
- [ ] `tests/test_import_service.py` — add `TestRunImportResultFenPreservation` (Pitfall 1)
- [ ] `tests/test_import_service.py` — add `TestPeriodicReaper` covering `orphan_age_threshold` behavior (Pitfall 3)
- [ ] `tests/test_import_service.py` — add `TestRecordFailureWithRetry` covering transient retry, non-transient pass-through, exhaustion + single Sentry capture (Pitfall 4)
- [ ] `app/repositories/import_job_repository.py` — extend `fail_orphaned_jobs` signature with `orphan_age_threshold: timedelta | None = None`
- [ ] Manual: bring up dev with `bin/run_local.sh`, import a known 5k+ game account, observe `docker stats` RSS

*(Existing test infrastructure already covers `_flush_batch`, `run_import`, `cleanup_orphaned_jobs` happy paths.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — change touches background-task internals, no auth surface |
| V3 Session Management | no | n/a — HTTP session unchanged |
| V4 Access Control | no | n/a — endpoint authorization unchanged |
| V5 Input Validation | no | n/a — same NormalizedGame validation; no new input surface |
| V6 Cryptography | no | n/a — no crypto |
| V7 Error Handling | yes | Sentry capture rules in CLAUDE.md; ensure new retry loop and reaper follow "capture on last attempt only" |
| V8 Data Protection | yes (minor) | Don't expose internal `job_id` or `user_id` in error_message bodies; the existing pattern uses `set_context` for variable data (CLAUDE.md). |

### Known Threat Patterns for FastAPI + SQLAlchemy async

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via bound parameters | Tampering | Use `bindparam()` / parameterized queries (the executemany rewrite uses bound params by definition — improves this surface vs. the existing `case()` map which is also parameterized; net-neutral). |
| DoS via unbounded retry | Availability | Bounded `_FAILURE_RECORD_MAX_RETRIES = 5` + capped backoff = total ~60s. Not an attacker-controlled loop. |
| Background task survives shutdown | Availability | `asyncio.CancelledError` in `_periodic_reaper` is awaited in lifespan finally — task is cancelled cleanly. |

## Project Constraints (from CLAUDE.md)

These directives apply to all code in Phase 90 and the planner must verify compliance:

1. **No `asyncio.gather` on the same `AsyncSession`.** The Stage 5 rewrite must run the two `executemany` calls **sequentially** on the same session. (Already true in the proposed pattern.)
2. **`httpx.AsyncClient` only** — `httpx` is already used for the platform clients; no `requests` introduced. No new HTTP surface in Phase 90.
3. **ty must pass.** New code: explicit return type annotations on all functions, `Sequence[T]` over `list[T]` for parameters accepting `list[Literal[...]]` values (none expected here), `# ty: ignore[rule-name]` with reason if a suppression is needed.
4. **No magic numbers.** `_REAPER_INTERVAL_SECONDS`, `_FAILURE_RECORD_MAX_RETRIES`, `_FAILURE_RECORD_BACKOFF_BASE_SECONDS` are all module-level constants.
5. **No bare `str` for fixed-value fields.** `status` in `update_import_job` calls is already `Literal["pending", "in_progress", "completed", "failed"]`-shaped (see existing call sites).
6. **Sentry capture rules.** Service-layer `except` blocks must call `sentry_sdk.capture_exception()`. Retry loops capture on **last attempt only**. Variable data via `set_context` / `set_tag`, never inline in error messages. Tag `source="import"` on new captures.
7. **Comment bug fixes.** Each of the 4 scope items is fixing a real bug — add a comment at the fix site noting the cause + Sentry issue / SEED reference (FLAWCHESS-56, FLAWCHESS-3Q, SEED-018) so future readers don't have to dig git history.
8. **Function size limits.** Nesting ≤3 (hard 4); logic LOC soft 100, hard 200. `run_import` is already ~150 lines and adding session-restructure + retry helper may push it over. **Plan:** extract `_record_failure_with_retry` as a module helper (already proposed) and the bootstrap-session + completion-session blocks may be left inline if each block is ≤30 lines of straight-line code. If `run_import` itself crosses 200 logic LOC after the restructure, extract the batch loop into a `_run_import_batches(client, job, previous_job_scalar, _on_game_fetched)` helper.
9. **Refactor bloated code on sight.** `import_service.py` is already large (~800 lines). Don't expand it gratuitously; the new code should be additive of ~60–100 lines net (the helper, retry constants, two periodic-reaper helpers).
10. **Communication style:** PR description and commit messages without sycophancy, em-dashes used sparingly.

## Sources

### Primary (HIGH confidence)
- `app/services/import_service.py` (read in full, lines 1–804) — current state of `_flush_batch`, `run_import`, `cleanup_orphaned_jobs`. `[VERIFIED]`
- `app/main.py` (read in full) — lifespan wiring of `cleanup_orphaned_jobs`, `_sentry_before_send` transient-error walking, `_DB_TRANSIENT_ERRORS` definition. `[VERIFIED]`
- `app/core/database.py` (read in full) — `async_session_maker(engine, expire_on_commit=False)`, `pool_size=20, max_overflow=30, pool_pre_ping=True`. `[VERIFIED]`
- `app/repositories/import_job_repository.py` (read in full) — `fail_orphaned_jobs`, `update_import_job`, `get_latest_for_user_platform`. `[VERIFIED]`
- `app/repositories/game_repository.py` (lines 1–110) — `bulk_insert_games`, `bulk_insert_positions` patterns to mirror. `[VERIFIED]`
- `app/services/lichess_client.py` (lines 100–160) — existing retry-loop pattern. `[VERIFIED]`
- `.planning/seeds/SEED-018-import-statement-cache-memory-leak.md` — empirical diagnosis. `[VERIFIED]`
- `.planning/debug/import-job-db-conn-closed.md` — tracemalloc localization to `compiler.py:1770` + `connection.py:481`. `[VERIFIED]`
- `.planning/notes/v1.18-import-pipeline-fix-scope.md` — scope decisions (4 items in, 2 out). `[VERIFIED]`
- `pyproject.toml` — dependency versions. `[VERIFIED]`
- CLAUDE.md — project constraints, OOM history, Sentry rules, GitLab Flow. `[VERIFIED]`

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x tutorial — UPDATE with bindparam executemany. `[CITED: https://docs.sqlalchemy.org/en/20/tutorial/data_update.html]`
- SQLAlchemy GitHub issue #9075 — COALESCE expression dropped in `update().values()` executemany contexts (motivates the two-group choice). `[CITED: https://github.com/sqlalchemy/sqlalchemy/issues/9075]`
- SQLAlchemy GitHub discussion #10246 — `prepared_statement_cache_size` and `statement_cache_size` connect_args for asyncpg. `[CITED: https://github.com/sqlalchemy/sqlalchemy/discussions/10246]`
- asyncpg API reference — `statement_cache_size` default 100 LRU. `[CITED: https://magicstack.github.io/asyncpg/current/api/index.html]`
- SQLAlchemy 2.x cache memory docs — `query_cache_size` default 500, savepoint-name leak history. `[CITED: https://docs.sqlalchemy.org/en/20/core/connections.html]`

### Tertiary (LOW confidence)
- "Per-task / per-batch `AsyncSession` is the canonical guidance for background workers" — widespread community pattern, no single canonical doc page cited. Flagged in Assumption A2. `[ASSUMED]`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in stack with versions verified.
- Architecture (executemany rewrite): HIGH — straightforward SQLAlchemy 2.x pattern, two-group split mechanically obvious from existing CASE structure.
- Architecture (session-recycle): MEDIUM — mechanically straightforward but assumption A2 (`previous_job` scalar accessibility post-close) needs verification; planner should add a Wave 0 check task.
- Architecture (periodic reaper): MEDIUM — `asyncio.create_task` + `while True: sleep` is idiomatic but no existing periodic task in repo (assumption A1).
- Architecture (failure retry): HIGH — direct mirror of `lichess_client.py` retry, except for the asyncpg exception type catch (assumption A3).
- Pitfalls: HIGH — all five drawn from the SEED-018 / debug note / lichess_client.py / repository code that's been read in full.

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (~30 days; the SQLAlchemy / asyncpg APIs in scope are stable, but FlawChess code under research may evolve)

## RESEARCH COMPLETE

**Phase:** 90 — Import Pipeline Memory Leak Fix + Resilience
**Confidence:** HIGH

### Key Findings
- **Stage 5 fix is mechanically obvious:** two `executemany` groups with `bindparam`, one for `move_count` over all batch ids, one for `result_fen` over ids where `result_fen is not None`. Preserves the existing None-handling without COALESCE fragility (SQLAlchemy issue #9075).
- **Session-recycle splits into three scopes:** a bootstrap session (job creation + previous-job lookup), per-batch sessions (the loop), and a completion session. The only state crossing the bootstrap boundary is `previous_job.last_synced_at` — extract as a scalar to avoid `DetachedInstanceError` risk.
- **Periodic reaper needs an age threshold.** `fail_orphaned_jobs` must learn a `timedelta` filter or the periodic reaper kills the live import. Default to `IMPORT_TIMEOUT_SECONDS = 3 hours` for periodic, `None` (current behavior) for startup.
- **Failure-state retry mirrors `lichess_client.py`** — 5 attempts, exponential backoff (2/4/8/16/30s, ~60s budget). Catch `sqlalchemy.exc.OperationalError` (the SQLAlchemy wrapper) rather than asyncpg exception types directly. Sentry capture on last attempt only per CLAUDE.md.
- **Zero new dependencies, zero schema migrations, zero new files** required. All four items land in `app/services/import_service.py` (+`app/main.py` lifespan touch, + `app/repositories/import_job_repository.py` signature extension).

### File Created
`/home/aimfeld/Projects/Python/flawchess/.planning/phases/90-import-pipeline-memory-leak-fix-resilience/90-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All deps already in pyproject.toml; no version bumps |
| Architecture (Stage 5 rewrite) | HIGH | Textbook SQLAlchemy 2.x; existing case-map already tells us the None-handling shape |
| Architecture (session-recycle) | MEDIUM | One assumption (A2: `previous_job.last_synced_at` post-close scalar access) — mitigated by extracting to a local |
| Architecture (reaper) | MEDIUM | No existing periodic task in repo to confirm idiom; `asyncio.create_task` + sleep loop is the obvious default |
| Architecture (retry) | HIGH | Direct mirror of in-tree `lichess_client.py` pattern; only the exception class needs verifying (A3) |
| Pitfalls | HIGH | Each pitfall traces to a specific code path read in full |

### Open Questions
1. Define `_FAILURE_RECORD_TRANSIENT_ERRORS` in `import_service.py` or share with `app/main.py`'s `_DB_TRANSIENT_ERRORS`? — recommend duplicate for Phase 90 scope, refactor later.
2. `fail_orphaned_jobs` — parameter vs. new function? — recommend parameter.
3. Raise `_BATCH_SIZE` back to 28 after leak fix? — OUT OF SCOPE for Phase 90.

### Ready for Planning
Research complete. Planner can now create PLAN.md files. Suggested plan partition (3 plans):
- **Plan 90-01** — Stage 5 executemany rewrite + `result_fen` preservation tests (the leak fix).
- **Plan 90-02** — Session-recycle restructure of `run_import` (defense-in-depth, depends on Plan 90-01 being green).
- **Plan 90-03** — Periodic reaper + failure-state retry (the two SEED-017 carry-forward items; lower risk, parallelizable with 90-02).
