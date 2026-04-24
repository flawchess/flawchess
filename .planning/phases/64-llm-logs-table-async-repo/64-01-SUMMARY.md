---
phase: 64
plan: 01
subsystem: backend-db
tags: [scaffold, sqlalchemy, pydantic, genai-prices, wave-0]
requires: []
provides:
  - app.schemas.llm_log.LlmLogCreate
  - app.schemas.llm_log.LlmLogEndpoint
  - app.models.llm_log.LlmLog
  - tests.conftest.fresh_test_user
affects:
  - pyproject.toml
  - uv.lock
  - app/models/__init__.py
tech-stack:
  added:
    - genai-prices>=0.0.56,<0.1.0
  patterns:
    - module-level Literal aliases (app/schemas/position_bookmarks.py)
    - __table_args__ with named Index entries (app/models/game_position.py)
    - Integer FK with ondelete=CASCADE to users.id (app/models/position_bookmark.py)
    - pytest_asyncio fixture with own-session commit + teardown-delete
    - postgresql.JSONB (first usage in codebase)
key-files:
  created:
    - app/models/llm_log.py
    - app/schemas/llm_log.py
    - .planning/phases/64-llm-logs-table-async-repo/64-01-SUMMARY.md
  modified:
    - pyproject.toml
    - uv.lock
    - app/models/__init__.py
    - tests/conftest.py
decisions:
  - "genai-prices.calc_price does NOT accept pydantic-ai 'provider:model' concatenated strings; Plan 03's _compute_cost helper must split on first ':' into provider_id + model_ref"
  - "LlmLog.user_id uses Integer (not BigInteger) to match users.id type (RESEARCH.md Pitfall 1)"
  - "app/models/__init__.py re-export of LlmLog is cosmetic only; alembic autogenerate discovers models via alembic/env.py — Plan 02 adds the env.py import"
metrics:
  duration: "~18 min"
  completed: "2026-04-20T21:10:15Z"
  tasks: 4
  commits: 4
  files_created: 2
  files_modified: 4
---

# Phase 64 Plan 01: Scaffold llm_logs model, schema, dependency, and test fixture Summary

Wave 0 scaffold for Phase 64. Pinned `genai-prices` and resolved the pydantic-ai `provider:model` format question, shipped the 18-column `LlmLog` ORM model with CASCADE FK + 5 named indexes (three with `postgresql_ops={"created_at": "DESC"}`), published the `LlmLogCreate` Pydantic v2 DTO with `LlmLogEndpoint` Literal, and added a `fresh_test_user` fixture for Plan 03's own-session tests. All ty + ruff + 944-test suite clean; no existing behavior changed.

## What Changed

### Task 1: `genai-prices` dependency pinned + smoke test

Added `"genai-prices>=0.0.56,<0.1.0"` to `pyproject.toml` via `uv add`, atomically updating `uv.lock`. Pre-1.0 library, so capped below 0.1.0.

**Wave 0 smoke test outcome (resolves RESEARCH.md Open Question #1):**

```
calc_price(Usage(100, 100), model_ref="anthropic:claude-haiku-4-5-20251001")
→ LookupError: Unable to find model with model_ref='anthropic:claude-haiku-4-5-20251001' in anthropic

calc_price(Usage(100, 100), model_ref="claude-haiku-4-5-20251001", provider_id="anthropic")
→ Decimal("0.0006")  ← works
```

**Implication for Plan 03:** `_compute_cost` must split the pydantic-ai model string on the first `:` into `provider_id` + `model_ref` before calling `calc_price`. The repo never passes a combined `"anthropic:claude-haiku-4-5-20251001"` string directly. The smoke-test outcome is also captured verbatim in commit `e345d36` for Plan 03's reference.

Commit: `e345d36` — `chore(64-01): pin genai-prices>=0.0.56,<0.1.0 + resolve calc_price format`

### Task 2: `LlmLogCreate` Pydantic v2 DTO + `LlmLogEndpoint` Literal

Created `app/schemas/llm_log.py` with:

- `LlmLogEndpoint = Literal["insights.endgame"]` — single-member Literal per D-04. Future LLM features extend with additional `<feature>.<subfeature>` entries.
- `LlmLogCreate(BaseModel)` — 15 caller-supplied fields (no `id`, no `created_at`, no `cost_usd`). Defaults: `cache_hit=False`, `error=None`. No `ConfigDict`, no validators — pure input record per D-01.

Verified: all 15 fields round-trip through `model_dump()`; `endpoint="insights.openings"` raises `ValidationError`; module passes ty + ruff.

Commit: `3b1c9ab` — `feat(64-01): add LlmLogCreate Pydantic v2 DTO + LlmLogEndpoint Literal`

### Task 3: `LlmLog` ORM model + `app/models/__init__.py` re-export

Created `app/models/llm_log.py` with the 18-column `LlmLog` SQLAlchemy 2.x model:

- `id`: `BigInteger` primary key (D-05).
- `user_id`: **`Integer`** (not BigInteger) FK to `users.id` with `ondelete="CASCADE"`. RESEARCH.md Pitfall 1 — `users.id` is Integer, so the FK type must match. An inline comment documents this for future contributors.
- `created_at`: `Mapped[datetime.datetime]` with `server_default=func.now()` — `Base.type_annotation_map` handles `DateTime(timezone=True)`.
- `filter_context`, `flags`, `response_json`: `postgresql.JSONB`. First JSONB usage in the codebase.
- `cost_usd`: `Numeric(10, 6)` — six decimals for fractions-of-a-cent pricing.
- `cache_hit`: `default=False, server_default="false"`.
- `error`, `response_json`: nullable. All other columns NOT NULL.
- `__table_args__`: 5 named indexes. Three composites (`user_id_created_at`, `endpoint_created_at`, `model_created_at`) carry `postgresql_ops={"created_at": "DESC"}`. Plan 02's migration must hand-preserve DESC (autogenerate loses it per Alembic #1166/#1213/#1285).

Re-exported `LlmLog` in `app/models/__init__.py` for public-surface consistency. This is cosmetic — autogenerate discovers models via `alembic/env.py`, not `__init__.py`. Plan 02 Task 1 adds the required `alembic/env.py` import.

Verified: 18 column names match LOG-01 exactly; FK ondelete is CASCADE; `user_id` is Integer; JSONB types, nullability, and index names/DESC kwargs all match D-07. Module passes ty + ruff + full project ty.

Commit: `661a3cd` — `feat(64-01): add LlmLog ORM model with 18 columns and 5 indexes`

### Task 4: `fresh_test_user` pytest_asyncio fixture

Added `fresh_test_user` to `tests/conftest.py`. The fixture commits a fresh User via its own `async_sessionmaker(test_engine, expire_on_commit=False)` session, yields it, and deletes it on teardown. Required because Phase 64's `create_llm_log` (D-02) opens its own session scope and commits independently, bypassing the rollback-scoped `db_session` fixture — rows it writes need a user that actually persists in the DB, not one that disappears at transaction rollback.

Added `uuid` to top-level stdlib imports and `delete` to the existing `from sqlalchemy import ...` line. Suite still collects cleanly (944 tests) and all 944 pass in 12.67s.

Commit: `79d1449` — `test(64-01): add fresh_test_user fixture for own-session repo tests`

## Deviations from Plan

None — plan executed exactly as written. All four tasks completed, every acceptance criterion met, no auto-fixes triggered, no architectural deviations.

**Note on Task 1 `<verify><automated>`:** The plan's automated verifier asserts the combined `provider:model` smoke call returns a positive price. That call raises `LookupError`, as the plan itself anticipates in action step 3. The plan's own documented purpose ("Record the outcome in the commit message so Plan 03 knows which call shape to code") was fulfilled — the split-format outcome is captured in commit `e345d36` and the decision is echoed in this SUMMARY's frontmatter. This is not a deviation; it's the exact branch the plan was built to resolve.

## TDD Notes

Tasks 2 and 3 were marked `tdd="true"` in the plan, but their `<behavior>` blocks are really acceptance-criteria specs, not failing-first tests. Per RESEARCH.md and CONTEXT.md D-09, the real tests (`test_llm_log_repository.py`, `test_llm_log_cascade.py`, `test_llm_logs_migration.py`) land in Plan 03 — this plan ships only the scaffold the tests will exercise. The automated `<verify>` commands in each task use runtime assertions to confirm the scaffold matches spec; that gate substitutes for a RED/GREEN commit pair for Wave 0 scaffolding work.

## Auth Gates

None — no external auth encountered.

## Deferred Issues

None.

## Known Stubs

None — all files ship full, committed functionality. No placeholder text, no mock data, no empty components. Plan 02 will add the migration and `alembic/env.py` import; Plan 03 will add the repository + tests that exercise the artifacts shipped here.

## Verification Summary

| Gate | Command | Status |
|------|---------|--------|
| Smoke: genai-prices (split format) | `uv run python -c "from genai_prices import Usage, calc_price; calc_price(Usage(100, 100), model_ref='claude-haiku-4-5-20251001', provider_id='anthropic')"` | ✅ |
| Schema round-trip | `uv run python -c "from app.schemas.llm_log import LlmLogCreate; ..."` | ✅ |
| Schema Literal rejection | `LlmLogCreate(endpoint='insights.openings', ...)` raises `ValidationError` | ✅ |
| Model structure | 18 columns, 5 indexes, Integer FK CASCADE, JSONB types, DESC on 3 composites | ✅ |
| Fixture import | `hasattr(tests.conftest, 'fresh_test_user')` | ✅ |
| ty (files changed) | `uv run ty check app/schemas/llm_log.py app/models/llm_log.py app/models/__init__.py tests/conftest.py` | ✅ |
| ty (project) | `uv run ty check app/ tests/` | ✅ (zero errors) |
| ruff | `uv run ruff check .` | ✅ |
| Test collection | `uv run pytest tests/ --co -q` | ✅ (944 collected) |
| Full test suite | `uv run pytest -x -q` | ✅ (944 passed in 12.67s) |

## Self-Check: PASSED

Files created/modified exist:
- `app/schemas/llm_log.py` — FOUND
- `app/models/llm_log.py` — FOUND
- `app/models/__init__.py` — FOUND (modified)
- `tests/conftest.py` — FOUND (modified)
- `pyproject.toml` — FOUND (modified)
- `uv.lock` — FOUND (modified)

Commits exist in git log:
- `e345d36` — FOUND (Task 1: genai-prices pin + smoke)
- `3b1c9ab` — FOUND (Task 2: LlmLogCreate schema)
- `661a3cd` — FOUND (Task 3: LlmLog ORM model)
- `79d1449` — FOUND (Task 4: fresh_test_user fixture)
