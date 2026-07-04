---
phase: 149-retire-prune
verified: 2026-07-04T13:23:37Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 149: Retire & Prune Verification Report

**Phase Goal:** Shrink the eval-pipeline surface before Phase 150 refactors it — delete the dead Gen-1 protocol and other dead weight, and land two small durability migrations, so Phase 150 consolidates 2 copies of the write path rather than 3.
**Verified:** 2026-07-04T13:23:37Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PRUNE-01: Dead Gen-1 protocol (`/lease`, `/submit`, `_apply_submit`, worker `_handle_full_ply_response`) no longer exists; `/flaw-blob-*` and all live lanes remain; full suite green | ✓ VERIFIED | `grep '@router.post("/lease"'`/`'"/submit"'`/`"async def _apply_submit"` in `app/routers/eval_remote.py` → 0 hits; `_handle_full_ply_response` absent from `scripts/remote_eval_worker.py`; all 6 live routes present (`/atomic-lease`, `/entry-lease`, `/entry-submit`, `/flaw-blob-lease`, `/flaw-blob-submit`, `/atomic-submit`); `tests/test_eval_worker_endpoints.py` collects 68 tests (was 95: -29 Gen-1, +4 atomic replacement, -2 WR-02 dead-schema tests); 5 KEEP classes present (`TestFlawBlobLeaseEndpoint`, `TestFlawBlobSubmitEndpoint`, `TestBlobAssemblyHelper`, `TestAtomicLeaseEndpoint`, `TestAtomicSubmitEndpoint`); `TestTier1Claiming`/`TestMultipv2BlobsRemote` gone |
| 2 | PRUNE-02: `hashes_for_game`, `Game.needs_engine_full_evals`, dead Table-3 `chesscom_to_lichess` lookups, `TIER_AUTO_WINDOW` removed; Tables 1/2 + `eval_jobs.tier` column kept; no live-path behavior change | ✓ VERIFIED | `grep -rn "hashes_for_game" app/ scripts/` → empty; `grep -rn "LICHESS_BLITZ_INTRA_TC\|lookup_uscf_from_lichess_blitz\|lookup_fide_from_lichess_blitz\|_LICHESS_BLITZ_KEYS" app/ tests/` → empty; `composed_chesscom_to_lichess_grid`/`convert_chesscom_to_lichess` still imported/used in `canonical_slice_sql.py`; `needs_engine_full_evals`/`_needs_engine_full_evals_expression` absent from `app/models/game.py`; `TIER_AUTO_WINDOW` absent from `app/`; `tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)` still present in `app/models/eval_jobs.py` |
| 3 | PRUNE-03: unrecognized chess.com result → skip (`None`) + Sentry `set_context` capture; `GameResult` literal NOT widened (3 members) | ✓ VERIFIED | `app/services/normalization.py:189` `_normalize_chesscom_result(...) -> GameResult \| None`, unknown branch returns `None` (line 218); `normalize_chesscom_game` (lines 264-275) calls `sentry_sdk.set_context("chesscom_result", {...})` + constant `capture_message(...)` on `None`, then returns `None` flowing through the pre-existing `if normalized is not None` skip gate; `app/schemas/normalization.py:13` `GameResult = Literal["1-0", "0-1", "1/2-1/2"]` unchanged (3 members); "safe fallback" string gone |
| 4 | PRUNE-04: `worker_schema_version` telemetry recorded on submits | ✓ VERIFIED | `app/routers/eval_remote.py`: atomic-submit passes `worker_schema_version=body.worker_schema_version` (line 1341); entry/flaw-blob submits pass `worker_schema_version=None` (lines 653, 909); repository coalesce guard prevents NULL-clobber (verified in truth 6) |
| 5 | PRUNE-05: durable `import_jobs` row created in `start_import` (not the background task) + partial unique index `(user_id, platform) WHERE status IN ('pending','in_progress')`; IntegrityError→existing-job-200; broad-exception cleanup discards stuck in-memory job | ✓ VERIFIED | `app/routers/imports.py:99-151`: `create_import_job` + `session.commit()` called inside `start_import` before `asyncio.create_task`; `except IntegrityError` rolls back, discards in-memory job, re-fetches scoped by `user_id`+`platform`, returns existing job with 200; `except Exception` (CR-01 fix) also rolls back + discards + Sentry-captures + re-raises; `create_import_job` absent from `app/services/import_service.py`; migration `20260704_123013_..._import_jobs_partial_unique_index.py` creates `uq_import_jobs_user_platform_active` with `postgresql_where=sa.text("status IN ('pending', 'in_progress')")`, textually matching `get_active_job_for_user_platform`'s `.in_(("pending", "in_progress"))` |
| 6 | PRUNE-06: `worker_heartbeats` populated server-side from all 3 live submit lanes via shared upsert helper; zero worker-side change; heartbeat failures cannot abort a real submit (WR-01 fix) | ✓ VERIFIED | `app/models/worker_heartbeat.py` defines `WorkerHeartbeat` with exact column set from spec; `upsert_worker_heartbeat()` (repository) called exactly 3x in `eval_remote.py` (lines 648, 904, 1336), none within 40 lines of any `/entry-lease`, `/atomic-lease`, `/flaw-blob-lease` decorator (lines 355, 453, 692); `worker_schema_version` uses `sa.func.coalesce(excluded, current)`; WR-01 fix confirmed — upsert wrapped in `async with session.begin_nested():` inside try/except that captures to Sentry and swallows, isolating heartbeat failures from the caller's real submit transaction; `scripts/remote_eval_worker.py` untouched by this feature (worker sends the same fields it always did) |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/worker_heartbeat.py` | `WorkerHeartbeat` model | ✓ VERIFIED | Exact columns per spec, no FK (documented), registered in `app/models/__init__.py` |
| `app/repositories/worker_heartbeat_repository.py` | `upsert_worker_heartbeat` helper | ✓ VERIFIED | `pg_insert(...).on_conflict_do_update(...)`, savepoint-isolated (WR-01), truncation guards |
| `alembic/versions/20260704_112059_b4ea823c85be_add_worker_heartbeats_table.py` | worker_heartbeats migration | ✓ VERIFIED | Reversible (upgrade/downgrade/upgrade round-tripped live) |
| `alembic/versions/20260704_123013_12d3df9c5373_import_jobs_partial_unique_index.py` | partial unique index migration | ✓ VERIFIED | Chains after heartbeats migration (`down_revision = b4ea823c85be`); reversible |
| `tests/test_worker_heartbeats.py` | dedicated heartbeat tests | ✓ VERIFIED | 3 tests pass (accumulation, NULL client, oversized sf_version isolation) |
| `app/services/normalization.py` (modified) | unknown-result skip + Sentry capture | ✓ VERIFIED | See truth 3 |
| `app/routers/eval_remote.py` (modified) | Gen-1 deleted, live lanes + heartbeat wiring intact | ✓ VERIFIED | See truths 1, 6 |
| `scripts/remote_eval_worker.py` (modified) | `_handle_full_ply_response` removed | ✓ VERIFIED | grep empty |
| `app/services/zobrist.py`, `app/services/chesscom_to_lichess.py`, `app/models/game.py`, `app/models/eval_jobs.py` (modified) | dead-weight removed, live paths kept | ✓ VERIFIED | See truth 2 |
| `app/routers/imports.py`, `app/repositories/import_job_repository.py`, `app/services/import_service.py` (modified) | durable import-job guard | ✓ VERIFIED | See truth 5 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `entry_submit_eval`/`flaw_blob_submit`/`atomic_submit_eval` | `upsert_worker_heartbeat` | direct call inside each handler's existing write session | ✓ WIRED | 3 call sites confirmed, no new session/gather |
| `normalize_chesscom_game` | `chesscom_client.py`'s `if normalized is not None: yield` gate | unknown → `None` return | ✓ WIRED | Confirmed by 149-02-SUMMARY and direct code read — zero caller change |
| `start_import` | `import_job_repository.create_import_job` / `get_active_job_for_user_platform` | synchronous call before `asyncio.create_task` | ✓ WIRED | Direct read of `app/routers/imports.py:99-151` |
| index predicate (migration) | `get_active_job_for_user_platform` WHERE clause | textual identity of the pending/in_progress set | ✓ WIRED | `'pending', 'in_progress'` (SQL) vs `("pending", "in_progress")` (Python tuple) — same two values |
| `canonical_slice_sql.py` | `chesscom_to_lichess.py` Tables 1/2 | `composed_chesscom_to_lichess_grid`/`convert_chesscom_to_lichess` imports | ✓ WIRED | grep confirms live imports still resolve; `ty check` clean |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend suite green | `uv run pytest -n auto -x` | 3154 passed, 18 skipped, 4 pre-existing warnings | ✓ PASS |
| Type check clean | `uv run ty check app/ tests/` | All checks passed | ✓ PASS |
| Lint clean | `uv run ruff check app/ tests/` | All checks passed | ✓ PASS |
| Format clean | `uv run ruff format --check app/ tests/` | 275 files already formatted | ✓ PASS |
| Alembic single linear head | `uv run alembic heads` | `12d3df9c5373 (head)` — exactly one | ✓ PASS |
| Both migrations reversible | `alembic downgrade -1` x2, `alembic upgrade head` | Clean round-trip through both new migrations back to head | ✓ PASS |
| Heartbeat-specific tests | `uv run pytest tests/test_worker_heartbeats.py -v` | 3 passed (accumulation, NULL-client, oversized-sf_version isolation) | ✓ PASS |
| CR-01 regression test | `uv run pytest tests/test_imports_router.py::TestPostImports::test_non_integrity_db_failure_discards_stuck_in_memory_job` | passed | ✓ PASS |
| Normalization regression tests | `uv run pytest tests/test_normalization.py -k unrecognized` | 2 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PRUNE-01 | 149-03 | Delete Gen-1 protocol, keep flaw-blob + live lanes | ✓ SATISFIED | Truth 1 |
| PRUNE-02 | 149-04 | Remove dead weight (hashes_for_game, Table-3, needs_engine_full_evals, TIER_AUTO_WINDOW) | ✓ SATISFIED | Truth 2 |
| PRUNE-03 | 149-02 | Unknown chess.com result → skip + Sentry, GameResult unwidened | ✓ SATISFIED | Truth 3 |
| PRUNE-04 | 149-01 | worker_schema_version telemetry on submits | ✓ SATISFIED | Truth 4 |
| PRUNE-05 | 149-05 | Durable import_jobs row + partial unique index | ✓ SATISFIED | Truth 5 |
| PRUNE-06 | 149-01 | worker_heartbeats registry, server-side only | ✓ SATISFIED | Truth 6 |

No orphaned requirements — all 6 PRUNE IDs are declared across the 5 plans and all are marked `[x]` in `.planning/REQUIREMENTS.md` with a matching "Complete" status row.

### Anti-Patterns Found

None blocking. A scan of all files modified across the phase's 5 plans plus the 4 code-review fixes found no unresolved `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers introduced by this phase. Historical comments in `app/routers/eval_remote.py`, `app/schemas/eval_remote.py`, `app/services/eval_queue_service.py`, and `app/services/eval_drain.py` reference already-deleted Gen-1 symbols (`_apply_submit`, `LeaseResponse`, `SubmitRequest`, `SubmitEval`) by name in prose explaining what changed and why — this is the project's pre-existing convention (confirmed by 149-REVIEW-FIX.md's WR-02 fix note) and not a residual-code issue; no live function/class definitions with those names remain.

The 149-REVIEW.md code review found 1 blocker (CR-01) and 2 warnings (WR-01, WR-02) plus 2 info items (IN-01, IN-02). All 4 in-scope findings (CR-01, WR-01, WR-02, IN-02) were fixed per 149-REVIEW-FIX.md and independently re-verified against the live code in this pass (see truths 5, 6 and the dedicated regression-test spot-checks above). IN-01 (asymmetric `last_ip` non-coalesce) was explicitly left as a documented, accepted design choice ("no fix required now") — not a gap.

### Human Verification Required

None required to certify the phase goal. One operationally-scoped item is worth flagging for whoever ships this branch:

1. **Re-run the prod-log zero-legacy-traffic grep before deploying.** 149-RESEARCH.md's Runtime State Inventory and 149-03-SUMMARY.md both flag that the "zero `/lease`+`/submit` hits" claim backing the Gen-1 deletion was last independently verified in the CONTEXT.md planning session (2026-07-04, 11.3h window), not re-run at execution or at this verification pass. This is explicitly scoped by the plan itself as a deploy-time check ("deferred to the deploy/ship step per CLAUDE.md's deploy skill"), not a phase-completion blocker — the code deletion is correct and complete; the only open question is whether a stale worker could still be pointed at the now-404 routes at the moment this ships. Recommended action: `ssh flawchess "docker compose logs backend | grep -c '/eval/remote/submit '"` (or equivalent recent-window check) immediately before `bin/deploy.sh`.

## Gaps Summary

None. All 6 ROADMAP success criteria are observably true in the live codebase, all 6 requirement IDs (PRUNE-01 through PRUNE-06) are satisfied with direct code evidence (not just SUMMARY claims), the full backend suite is green (3154 passed), type-checking/linting/formatting are clean, both new Alembic migrations are reversible and chain to a single linear head, and all 4 code-review findings (1 blocker + 2 warnings + 1 info item, per 149-REVIEW.md) were verified fixed in the live code. The phase goal — shrinking the eval-pipeline surface so Phase 150 consolidates 2 write-path copies instead of 3 — is achieved: the Gen-1 protocol (the third copy) is fully deleted from source and tests, while both surviving lanes (`/entry-*`, `/atomic-*`) and the isolated `/flaw-blob-*` pair remain intact and tested.

---

_Verified: 2026-07-04T13:23:37Z_
_Verifier: Claude (gsd-verifier)_
