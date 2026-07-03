---
quick_id: 260703-vg3
title: Code-review hardening batch — auth/import-status, index time-bomb, SECRET_KEY, worker bounds
date: 2026-07-03
status: complete
source: reports/code-review-fable-2026-07-02.md
triage: .planning/notes/2026-07-03-code-review-fable-triage.md
---

# Summary — Code-review security/ops hardening batch (260703-vg3)

Landed the 4 committable code fixes from the "Fix now" tier of the 2026-07-02 fable
review triage, each as an atomic commit on `main`, plus one operational dev-DB restore.
One item (#5 ANALYZE) is a prod-only op flagged for confirmation.

## Commits

| # | Item | Commit | Files |
|---|------|--------|-------|
| 1 | #1 Auth + sanitize `GET /imports/{job_id}` | `8f77e484` | `app/routers/imports.py`, `app/services/import_service.py`, `tests/test_imports_router.py`, `tests/test_import_service.py` |
| 2 | #3 Index autogen time-bomb + drift guard | `968ef5ca` | `alembic/env.py`, `tests/test_migration_only_indexes_exist.py` |
| 3 | #1.2 SECRET_KEY fail-closed guard | `2cadc0f8` | `app/core/config.py`, `app/main.py`, `tests/test_config_secret_key.py` |
| 4 | #11 Worker eval bound-validation | `39cdd6f6` | `app/schemas/eval_remote.py`, `tests/test_eval_remote_schema_bounds.py` |

## What changed & why

- **#1** — `GET /imports/{job_id}` was the only import route with no `current_active_user`
  and no user scoping. Added the dependency + a 404 IDOR guard (never 403) on both the
  in-memory and DB-fallback paths. Sanitized the client-facing error **at the source**
  (`import_service.py` generic-exception handler) so it covers `/{job_id}` AND `/active`:
  `ValueError` (the codebase's deliberate user-facing error, e.g. "user not found") is
  kept verbatim; any other exception is replaced with a fixed generic message. Raw exc
  still goes to Sentry.
  - Deviation from the literal todo (sanitize at the router): fixing at the service
    source is strictly better — one place, both endpoints, and it preserves the existing
    user-actionable ValueError messages (the todo's "map to sanitized" would have
    regressed "user not found" UX and broken `test_failed_import_sets_error`).

- **#3** — Added `ix_game_flaws_blob_backfill` to `_AUTOGEN_INDEX_IGNORELIST` (it was one
  `--autogenerate` away from dropping prod's ~348M-scan index). Verified: a fresh
  `alembic revision --autogenerate` now emits a clean no-op (no `drop_index`). Added
  `test_migration_only_indexes_exist` as a drift guard against the freshly-migrated test
  DB. The 4 "dev-missing" partials were **local dev drift, not a migration bug** (the
  migrations create them unconditionally and never drop them in `upgrade()`); restored
  them in the local dev DB via idempotent `CREATE INDEX IF NOT EXISTS`.

- **#1.2** — `assert_secret_key_configured()` in `config.py`, called first in the app
  lifespan (mirrors the D-22 deploy-blocker pattern — a **runtime** check, not an
  import-time model_validator, so Alembic/maintenance scripts that import `settings` are
  unaffected). Raises when `ENVIRONMENT != "development"` and SECRET_KEY is the default.
  Tests set a real key, so they stay green.

- **#11** — Added `ge`/`le`/`max_length` Field bounds to `SubmitEval`, `AtomicSubmitEval`,
  `EntrySubmitEval` (eval_cp/eval_mate = SMALLINT range, best_move = String(5), pv = 512
  chars, ply ≤ 2048). Stops an out-of-range worker value from reaching the DB
  (DBAPIError → 500 → unresolvable retry-loop) and blocks multi-MB pv payloads. Fields
  stay required-nullable; None still passes.

## Verification

- `test_imports_router.py::TestGetImportStatus` (7 tests incl. unauth→401, cross-user→404
  in-memory + DB) — pass.
- `test_import_service.py` sanitization (ValueError kept, RuntimeError→generic) — pass.
- `test_migration_only_indexes_exist` — pass; `--autogenerate` probe = clean no-op.
- `test_config_secret_key.py` (prod+default→raise; dev/custom→ok) — pass.
- `test_eval_remote_schema_bounds.py` (out-of-range→ValidationError/422) — pass.
- **Full pre-merge gate**: `ruff check` clean, `ty check app/ tests/` clean,
  `pytest -n auto` = **3188 passed, 18 skipped**. Frontend untouched (backend-only
  batch), so the frontend lint/test gate is not relevant to these commits.

## Follow-ups (NOT done — require action/confirmation)

- **#5 ANALYZE `opening_position_eval`** — prod-only stats refresh (prod planner
  n_live_tup 59k vs 1.69M actual). Not run: the prod DB MCP is read-only and this is a
  **prod write** that needs explicit go-ahead. To apply:
  `ssh flawchess "cd /opt/flawchess && docker compose exec -T db psql -U flawchess -d flawchess -c 'ANALYZE opening_position_eval;'"`.
  The triage note defers the durable autovacuum-tuning fix for this insert-only table to
  a separate task.
- The "Fix soon" / "Defer" tiers of the triage note remain open (pipeline/tactic
  correctness phase; SEED-077/078).
