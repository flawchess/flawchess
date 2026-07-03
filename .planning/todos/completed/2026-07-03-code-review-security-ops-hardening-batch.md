---
created: 2026-07-03T00:00:00.000Z
title: Code-review hardening batch — auth/import-status, index time-bomb, SECRET_KEY, worker bounds
area: security / ops
priority: high
source: reports/code-review-fable-2026-07-02.md
files:
  - app/routers/imports.py
  - app/services/import_service.py
  - app/core/config.py
  - alembic/env.py
  - app/schemas/eval_remote.py
---

## Scope

Trivial, low-blast-radius security + ops fixes from the 2026-07-02 review. Independent and
mechanical — run as ONE `/gsd-quick` batch (~1h). Rationale + full triage in
`.planning/notes/2026-07-03-code-review-fable-triage.md`.

## Items

1. **#1 — Authenticate `GET /api/imports/{job_id}` + sanitize `error`**
   `app/routers/imports.py:333` is the only route in the file without
   `Depends(current_active_user)`; `get_import_job` fallback has no user scoping. Add
   `current_active_user` + `job.user_id == user.id` (404 otherwise, matching the IDOR
   pattern used elsewhere). Map `job.error` (`import_service.py:619`, raw `str(exc)`) to a
   sanitized message so DB/httpx internals don't leak to unauthenticated clients.

2. **#3 — `ix_game_flaws_blob_backfill` autogenerate time-bomb** (highest payoff/effort)
   Add the index name to `_AUTOGEN_INDEX_IGNORELIST` (`alembic/env.py:74-86`) OR declare it
   in `GameFlaw.__table_args__` (the env.py "can't represent partial indexes" comment is
   wrong — models already declare several). Otherwise the next `--autogenerate` emits
   `op.drop_index` on prod's most-scanned `game_flaws` index (348M scans).
   - Restore the 4 dev-missing prod partial indexes (`ix_games_evals_pending`,
     `ix_games_full_evals_pending`, `ix_games_full_pv_pending`,
     `ix_games_needs_engine_full_evals`).
   - Add a startup/test assertion that the known migration-only index names exist in
     `pg_indexes` (drift detection).

3. **#1.2 — SECRET_KEY fail-closed guard**
   `app/core/config.py:26` defaults to `"change-me-in-production"` while `ENVIRONMENT`
   defaults to `"production"`. Raise at startup if `ENVIRONMENT != "development"` and the
   key is still the default (mirror the D-22 deploy-blocker pattern in
   `get_insights_agent()`).

4. **#11 — Worker eval bound-validation**
   `app/schemas/eval_remote.py:30-46`: add Pydantic `Field` bounds mirroring the server-side
   clamps — `eval_cp`/`eval_mate` ranges, `pv`/`best_move` `max_length`, `ply` upper bound.
   Prevents an out-of-range value → `DBAPIError` → 500 → worker retry-loop that never
   resolves the hole, and blocks multi-MB `pv` payloads.

5. **ANALYZE** — `ANALYZE opening_position_eval` (planner stats 28× off: n_live_tup 59k vs
   1.69M actual). One-off; consider autovacuum tuning for the insert-only table separately.

## Verification

- Unauthenticated GET on an import job id → 401/404; authenticated cross-user → 404;
  own job → 200 with sanitized `error`.
- `alembic revision --autogenerate` on a clean head emits NO `drop_index` for
  `ix_game_flaws_blob_backfill`.
- Dev `pg_indexes` contains all 4 restored index names; assertion passes.
- Non-dev boot with default SECRET_KEY raises; dev boot unaffected.
- Out-of-range worker submit → 422 at the boundary, not 500.
