---
phase: 145-corpus-backfill-rollout
plan: "02"
subsystem: eval-queue
tags: [tier-4, blob-backfill, eval-queue, idempotent-lottery]
dependency_graph:
  requires: [145-01-PLAN.md]
  provides: [TIER_BLOB_BACKFILL constant, _claim_tier4_blob lottery, claim_eval_job tier-4 dispatch]
  affects: [app/services/eval_queue_service.py, app/models/eval_jobs.py, tests/services/test_eval_queue.py]
tech_stack:
  added: []
  patterns: [table-less idempotent lottery, SA text() parameterized SQL, spare-capacity tier gating]
key_files:
  created: []
  modified:
    - app/models/eval_jobs.py
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py
decisions:
  - "JSONB null vs SQL NULL: asyncpg JSONB codec serializes Python None as JSON null atom (null::jsonb), not SQL NULL; _insert_game_flaw omits allowed_pv_lines when None to get SQL NULL from DB default"
metrics:
  duration: 16min
  completed: 2026-06-30
  tasks: 2
  files: 3
status: complete
---

# Phase 145 Plan 02: Tier-4 Blob-Backfill Lottery Summary

Added the lowest-priority tier-4 blob-backfill lottery and dispatch branch to the eval queue service, distributing bulk MultiPV-2 flaw-blob compute across the remote fleet on spare capacity.

## Tasks Completed

### Task 1: TIER_BLOB_BACKFILL constant + _claim_tier4_blob lottery

- Added `TIER_BLOB_BACKFILL = 4` to `app/models/eval_jobs.py` alongside the existing `TIER_EXPLICIT/AUTO_WINDOW/IDLE_BACKLOG` constants.
- Re-exported `TIER_BLOB_BACKFILL` from `eval_queue_service.py` on the noqa F401 import line.
- Implemented `_claim_tier4_blob(session) -> tuple[int, int] | None`: single-level random pick over `game_flaws JOIN games JOIN users WHERE allowed_pv_lines IS NULL AND full_evals_completed_at IS NOT NULL AND is_guest = false ORDER BY random() LIMIT 1`, returning `(game_id, user_id)` or None.
- No eval_jobs row created (table-less, idempotent-by-construction lottery per D-03).
- No ES user weighting (spare-capacity only — plain random pick per plan spec).
- `is_lichess_eval_game` explicitly deferred to Plan-03 lease handler (Pitfall 6).

**Commit:** `66de3c2b`

### Task 2: Dispatch tier-4 after tier-3 in claim_eval_job + tests

- Extended `claim_eval_job` to fall through to `_claim_tier4_blob` after tier-3 yields None.
- Both scope="idle" and scope=None bundled flows now include tier-4 as the final fallback.
- Tier-4 is gated by the same `settings.EVAL_AUTO_DRAIN_ENABLED` flag as tier-3 (D-02); live tier-1/2/3 work always preempts tier-4.
- `scope="explicit"` still returns None after tier-1/2 (no tier-3/4 fallthrough).
- Returns `ClaimedJob(tier=TIER_BLOB_BACKFILL, job_id=None, is_lichess_eval_game=False)`.
- Added `TestTier4BlobBackfill` class with 8 tests: null-blob pick, empty-queue None, guest exclusion, unanalyzed exclusion, blobbed-game idempotency, dispatch via claim_eval_job, disabled-drain gate, and ClaimedJob field validation.

**Commit:** `6d26a77a`

## Verification

- `uv run pytest tests/services/test_eval_queue.py -x` — 24 passed (8 new tier-4 tests + 16 existing)
- `uv run ruff check app/ tests/` — all checks passed
- `uv run ty check app/ tests/` — zero errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncpg JSONB null vs SQL NULL in test helper**

- **Found during:** Task 1 test execution
- **Issue:** The `_insert_game_flaw` test helper set `flaw.allowed_pv_lines = None`, but asyncpg's JSONB codec serializes Python `None` as the JSON null atom (`null::jsonb`), not as SQL NULL. The `_claim_tier4_blob` predicate `allowed_pv_lines IS NULL` only matches SQL NULL, causing the test to return None even though the flaw row was correctly inserted.
- **Fix:** Changed `_insert_game_flaw` to omit `allowed_pv_lines` entirely when the argument is None. When a nullable column with no `server_default` is omitted from an INSERT, PostgreSQL stores SQL NULL — matching the behavior of production rows that were migrated to NULL by the ALTER TABLE ADD COLUMN in Phase 141.
- **Files modified:** `tests/services/test_eval_queue.py`
- **Note:** The production lottery SQL predicate `gf.allowed_pv_lines IS NULL` is correct. Production game_flaw rows are inserted without explicit `allowed_pv_lines` (the drain service only sets core fields), so they have SQL NULL. The fix is test-side only; no change to the lottery SQL.

## Known Stubs

None — the lottery function returns real `(game_id, user_id)` pairs from the database. `is_lichess_eval_game=False` in the `ClaimedJob` is explicitly documented as a stub resolved in Plan-03; this is intentional and tracked in the plan dependency graph.

## Threat Surface Scan

No new network endpoints or trust boundary changes in this plan. The `_claim_tier4_blob` function is server-internal SQL with no external input. The SQL predicate values are all static literals (no f-string interpolation). Guest exclusion (`u.is_guest = false`) is enforced in the WHERE clause (T-145-04 mitigation). The `ix_game_flaws_blob_backfill` partial index from Plan 01 backs the `allowed_pv_lines IS NULL` predicate (T-145-03 mitigation).

## Self-Check: PASSED

- `app/models/eval_jobs.py` exists with `TIER_BLOB_BACKFILL = 4` ✓
- `app/services/eval_queue_service.py` exists with `_claim_tier4_blob` function ✓
- `tests/services/test_eval_queue.py` exists with `TestTier4BlobBackfill` class ✓
- Commits `66de3c2b` and `6d26a77a` present in git log ✓
