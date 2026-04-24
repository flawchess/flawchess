# Phase 64: `llm_logs` Table & Async Repo - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning
**Requirements:** LOG-01, LOG-02, LOG-03, LOG-04

<domain>
## Phase Boundary

Backend-only, DB-layer. Deliver a **generic** `llm_logs` Postgres table + Alembic migration + module-level async write repository that any future LLM feature can call. Not endgame-specific. Scope is exactly: one SQLAlchemy model (`app/models/llm_log.py`), one Alembic migration, one repository module (`app/repositories/llm_log_repository.py`) with a single write function and minimal read helpers needed by Phase 65's cache lookup, plus tests covering insert round-trip, cascade delete, and `cost_unknown` fallback. No endpoint, no service, no frontend. Phase 65 wires the repo into the insights endpoint; Phase 66 ships UI; Phase 67 validates.

</domain>

<decisions>
## Implementation Decisions

### Repo API Shape

- **D-01:** Single write entry point is `create_llm_log(data: LlmLogCreate) -> LlmLog`. `LlmLogCreate` is a Pydantic v2 model in `app/schemas/llm_log.py` mirroring the `llm_logs` columns except `id`, `created_at`, and `cost_usd` (the repo computes cost, see D-03). Callers (Phase 65) construct one instance and hand it in — no 16-kwarg signatures, type-safe, trivial to fixture in tests.
- **D-02:** The repo commits its own transaction, NOT the caller's session. It opens a fresh `async_session_maker()` scope inside `create_llm_log`, inserts, commits, and returns the persisted row. Rationale: the log's primary use case is capturing LLM failures — if the caller's request-scoped session rolls back (HTTPException, validation error, pydantic-ai crash), we must still have the log row. Existing `import_job_repository` passes `session` because it's co-transactional with game inserts; `llm_logs` is diagnostic infrastructure with the opposite durability requirement.

### Cost-Computation Boundary

- **D-03:** The repo owns `genai-prices`. Callers pass `(model, input_tokens, output_tokens)`; `create_llm_log` calls `genai-prices` internally, computes `cost_usd`, and on `ModelNotFound`-style failure sets `cost_usd = Decimal("0")` and appends `error = "cost_unknown:<model>"` to the log row (concatenating with any existing caller-supplied `error` as `"<caller_error>; cost_unknown:<model>"`). Rationale: single place for the LOG-02 "success OR failure writes exactly one row" invariant and the success-criterion #4 fallback; Phase 65 and any future LLM feature never imports `genai-prices` directly. Pin `genai-prices` in `pyproject.toml` as part of this phase.

### `endpoint` Column Typing

- **D-04:** DB side is `String(50)`, NOT a Postgres enum. Python side defines `LlmLogEndpoint = Literal["insights.endgame"]` in `app/schemas/llm_log.py` and `LlmLogCreate.endpoint: LlmLogEndpoint`. Future LLM features add their endpoint name to the Literal (e.g., `"insights.openings"`, `"insights.stats"`) with zero migration. Type-safe at call site, flexible at DB level, consistent with CLAUDE.md's "Literal over bare str" rule.

### Schema Specifics (per LOG-01 — locked, documenting for the planner)

- **D-05:** `id: BigInteger` primary key (anticipates multi-feature volume + long retention per SEED-003 §Retention). `cost_usd: Numeric(10, 6)` — six decimals covers fractions-of-a-cent pricing on cheap models. `filter_context: JSONB`, `flags: JSONB` (list of strings in app code; JSONB for queryability). `response_json: JSONB NULL`. `cache_hit: Boolean NOT NULL DEFAULT FALSE` (LOG-02 says "every cache-miss call" writes a row — the column exists for a future decision to also log hits, per SEED-003 Open Questions; Phase 64 does not enable hit-logging).
- **D-06:** `user_id: BigInt FK → users.id ON DELETE CASCADE NOT NULL` (matches `users.id` type convention of existing FKs). Cascade is mandatory per CLAUDE.md DB rules + GDPR (SEED-003 §Privacy).

### Indexes (per LOG-03 — locked)

- **D-07:** Exactly five indexes, all named and created in the migration:
  - `ix_llm_logs_created_at` on `(created_at)`
  - `ix_llm_logs_user_id_created_at` on `(user_id, created_at DESC)`
  - `ix_llm_logs_findings_hash` on `(findings_hash)`
  - `ix_llm_logs_endpoint_created_at` on `(endpoint, created_at DESC)`
  - `ix_llm_logs_model_created_at` on `(model, created_at DESC)`

### Error Handling & Sentry (LOG-04)

- **D-08:** The repo itself does not call `sentry_sdk.capture_exception` — that's the caller's job (Phase 65). What the repo does: on DB-write failures, propagate the exception to the caller, never swallow. On `genai-prices` lookup miss, do NOT raise — record as `error="cost_unknown:<model>"` per SC #4. Sentry `set_context` usage (LOG-04) is Phase 65 concern at call sites, but this phase's tests confirm no `f"...{user_id}..."`-style interpolation appears in any repo error message.

### Tests (for the planner — scope anchor, not full spec)

- **D-09:** Three mandatory test files under `tests/`:
  - `tests/repositories/test_llm_log_repository.py` — happy-path insert + read-back (SC #2), `cost_unknown` fallback populates `error` + `cost_usd=0` (SC #4), idempotent re-import safety (no unique constraints that would collide on retry).
  - `tests/models/test_llm_log_cascade.py` — integration test creating user + log row, deleting user, asserting row is gone (SC #3).
  - `tests/alembic/test_llm_logs_migration.py` (or equivalent smoke test) — `alembic upgrade head` creates table with all 17 columns and 5 indexes (SC #1). Reuse the Phase 59-era migration smoke test pattern if one exists; otherwise a single `sqlalchemy.inspect()` check is fine.

### Claude's Discretion

- Exact module layout: `app/models/llm_log.py` (ORM model), `app/schemas/llm_log.py` (Pydantic `LlmLogCreate` + `LlmLogEndpoint` Literal), `app/repositories/llm_log_repository.py` (module-level async `create_llm_log` + any read helper Phase 65 needs — likely `get_latest_cached_log_by_hash(findings_hash, prompt_version, model)` per SEED-003 §Cache, but the planner/researcher validates Phase 65's exact read pattern before locking).
- `genai-prices` invocation detail: whether to use its sync or async API, exception names to catch (`ModelNotFound`, `LookupError`, or whatever the library exposes in its current version) — researcher confirms via context7 or the package source.
- Whether to expose `create_llm_log` as a free function or via a small builder class — module-level async function is the established pattern (see `import_job_repository.py`), use it unless the planner finds a strong reason not to.
- The exact `LlmLogCreate` field ordering / grouping / field-level validators — Pydantic-v2-idiomatic; docstring on the model explains which fields come from pydantic-ai `Usage` vs caller-computed.
- Whether `response_json` stores the raw provider response, the parsed `EndgameInsightsReport` dict, or both — planner picks one, documents in the model docstring; Phase 65 has to agree.
- Whether to add a `CHECK (cache_hit = FALSE)` constraint in the migration — defer, since the column exists specifically to enable future hit-logging.
- Whether `create_llm_log` returns the full `LlmLog` ORM object or just the id — return the object (Phase 65 may want `latency_ms` / `created_at` in the response headers for debugging).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/seeds/SEED-003-llm-based-insights.md` — §"Log table schema" (lines 120–170 of the seed) sketches the SQLAlchemy model; §"Privacy" + §"Retention" motivate the cascade and the lack of redaction; §"Open Questions" lists the cache-hit-logging and `genai-prices` coverage questions. Read before writing the model or migration.
- `.planning/REQUIREMENTS.md` §LOG-01..LOG-04 — the 17-column schema, five indexes, cost-compute source, and Sentry grouping rule are all locked here. Any deviation needs an explicit override — the planner should not invent new columns or drop listed ones.
- `.planning/PROJECT.md` §"v1.11 LLM-first Endgame Insights" — milestone context.
- `.planning/phases/63-findings-pipeline-zone-wiring/63-CONTEXT.md` — Phase 63 owns `findings_hash` semantics. This phase's `findings_hash: String` column stores the SHA256 hex string that Phase 63's `compute_findings` produces; no hashing happens here.

### Existing Backend (read-only patterns)
- `app/models/base.py` — `Base(AsyncAttrs, DeclarativeBase)` with `type_annotation_map` for `datetime.datetime → DateTime(timezone=True)`. Use as-is.
- `app/models/import_job.py` — reference for FK + `ondelete="CASCADE"`, `server_default=func.now()`, `Mapped[str | None]` patterns. Follow identical structure where applicable.
- `app/models/opening.py` — reference for `__table_args__ = (Index(...), UniqueConstraint(...))` usage and `BigInteger` column typing.
- `app/models/game_position.py`, `app/models/position_bookmark.py` — JSONB column usage in the codebase (useful for the `filter_context` / `flags` / `response_json` columns).
- `app/repositories/import_job_repository.py` — the canonical repo pattern: module-level async functions accepting `session: AsyncSession`, module docstring, per-function docstrings. Deviate only on D-02 (llm_log repo opens its own session — document the deviation in the module docstring).
- `app/core/database.py::async_session_maker` — the factory `create_llm_log` uses to open its own scope (D-02).
- `app/services/import_service.py` (lines 1–60) — reference for `async_session_maker` usage inside a service (background task pattern).

### Migrations
- `alembic/versions/20260414_184435_179cfbd472ef_add_base_time_seconds_and_increment_.py` — latest migration; new migration's `down_revision` points here (or wherever head is at run time).
- `alembic/env.py` — confirms autogenerate works against `app.models.*`. Running `uv run alembic revision --autogenerate -m "create llm_logs"` after registering the new model in `app/models/__init__.py` (if that's the pattern — planner verifies) produces the migration skeleton; planner hand-edits to ensure all 5 indexes and the `ON DELETE CASCADE` FK land correctly.

### Project Conventions
- `CLAUDE.md` §"Coding Guidelines" — Literal types, no magic numbers, ty compliance (zero errors in `uv run ty check app/ tests/`). `LlmLogEndpoint` Literal, cost-fallback constant, etc. live in a constants section of the schema module.
- `CLAUDE.md` §"Database Design Rules" — FK with explicit `ondelete`, appropriate column types (BigInteger for id, Numeric for money, SmallInteger where a count fits).
- `CLAUDE.md` §"Error Handling & Sentry" — `sentry_sdk.capture_exception` only in service/router catch blocks (not this repo per D-08); never interpolate variables into error strings.
- `CLAUDE.md` §"Critical Constraints" — `AsyncSession` not safe for `asyncio.gather` (repo uses a single session inside its own scope — not a concern here, but document in the repo's docstring that concurrent callers each open their own scope).
- `CLAUDE.md` §"Version Control" — Phase 64 lands via a feature branch + PR; don't auto-deploy on merge.

### External Libraries
- [`genai-prices`](https://github.com/pydantic/genai-prices) — the library computing `cost_usd` from `(model, input_tokens, output_tokens)`. Researcher should query `context7` for the current API surface (function names, exception types for missing-model lookups) before the planner locks the D-03 implementation. Pin the version in `pyproject.toml` as part of this phase.
- [`pydantic-ai`](https://ai.pydantic.dev/) — Phase 65 concern, not this phase's. Mentioned only so the planner knows the `model` string format in the log column matches pydantic-ai's `provider:model` convention (e.g., `"anthropic:claude-haiku-4-5-20251001"`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app/models/base.py` `Base`** — inherit as-is; `datetime` columns automatically get `DateTime(timezone=True)`.
- **`app/core/database.py::async_session_maker`** — factory for the repo's own session (D-02). Used by `import_service.py` for background tasks.
- **`app/repositories/import_job_repository.py`** — module-level async function template. Copy shape; deviate only on session ownership (D-02).
- **No existing BigInt/JSONB log-style tables** — `game_position`, `opening`, `position_bookmark` use BigInteger/JSONB but for domain data, not logs. No prior log table to mirror; the `import_jobs` table is the closest analog but has different durability semantics.

### Established Patterns
- **Module-level async repo functions** accepting `session: AsyncSession`. Phase 64 deviates: `create_llm_log` takes `data: LlmLogCreate` only, opens its own session. Justify deviation in the module docstring (D-02).
- **Pydantic v2 input DTOs in `app/schemas/`** — used at system boundaries. Extending to a repo input is a minor but consistent application of the pattern.
- **Alembic autogenerate + hand-edit** — standard migration flow. Autogenerate misses explicit `Index(..., postgresql_ops={...})` for DESC order; planner should check the generated file and confirm DESC is preserved (Postgres respects DESC in multi-column indexes for ordered scans).
- **CASCADE FK to `users.id`** — every user-owned table uses `ondelete="CASCADE"`. `llm_logs` follows.
- **`ty` strict type-check in CI** — planner ensures no `# type: ignore`; use `# ty: ignore[rule]` with justification only where SQLAlchemy forward refs force it (see existing `game_position.py` for examples).

### Integration Points
- **Phase 65's cache-lookup** reads from `llm_logs`. Repo exposes at minimum one read helper — likely `get_latest_log_by_hash(findings_hash, prompt_version, model)` returning the most recent `response_json`-not-null row, per SEED-003 §Cache. The exact signature is a Phase 65 concern but Phase 64 stubs it now to avoid blocking.
- **Phase 65's rate limiter** queries `llm_logs` for misses-in-last-hour per user. Phase 64 leaves this unimplemented; the `(user_id, created_at DESC)` index (D-07) supports it.
- **Phase 67's ground-truth regression** reads `llm_logs` rows by `findings_hash` to compare outputs across prompt versions. The `findings_hash` + `prompt_version` indexes are sufficient.
- **`app/models/__init__.py`** — the new `LlmLog` model must be importable from here so `alembic env.py` sees it in autogenerate. Planner confirms this is the repo's convention (check existing imports).

</code_context>

<specifics>
## Specific Ideas

- **LlmLogCreate fields** (Pydantic v2 model, mirrors LOG-01 minus repo-computed fields):
  ```python
  class LlmLogCreate(BaseModel):
      user_id: int
      endpoint: LlmLogEndpoint
      model: str
      prompt_version: str
      findings_hash: str
      filter_context: dict[str, Any]
      flags: list[str]
      system_prompt: str
      user_prompt: str
      response_json: dict[str, Any] | None
      input_tokens: int
      output_tokens: int
      latency_ms: int
      cache_hit: bool = False
      error: str | None = None
  ```
  Repo computes `cost_usd` from `(model, input_tokens, output_tokens)` via `genai-prices`; appends `"; cost_unknown:<model>"` to `error` (or sets it standalone if `error` is None) when the model is unrecognized.
- **LlmLogEndpoint Literal**:
  ```python
  LlmLogEndpoint = Literal["insights.endgame"]
  ```
  Single-member Literal in Phase 64; extended in future phases as new LLM features ship. Naming convention: `<feature>.<subfeature>` dot-separated.
- **Cost fallback marker format**: `"cost_unknown:<model>"` — exactly as SC #4 states. When combined with a caller-supplied `error`, the repo concatenates with `"; "` separator (e.g., `"provider_rate_limit; cost_unknown:anthropic:claude-haiku-4-5-20251001"`). Keeps both failure modes queryable via `LIKE` on the `error` column.
- **Migration filename** follows existing convention (`alembic/versions/<timestamp>_<hash>_create_llm_logs.py`). Alembic generates the timestamp + hash; the descriptive tail is `create_llm_logs`.
- **Module docstrings** explicitly call out the D-02 deviation: `"""Llm log repository: async write/read for the llm_logs table. UNLIKE other repositories in this package, create_llm_log opens its own async session and commits independently so log rows survive caller rollbacks."""`.

</specifics>

<deferred>
## Deferred Ideas

- **Cache-hit logging policy** — `cache_hit` column exists but defaults to False; actually setting it True on cache-served requests is a Phase 65 decision per SEED-003 Open Questions. Phase 64 just provides the column.
- **Retention / archival** — SEED-003 §Retention says "keep indefinitely in MVP; revisit at ~1M rows or when cost-monitoring matures". Not in Phase 64 scope. Future phase or ops task.
- **Cost dashboard / query views** — no admin endpoint in v1.11. Cost monitoring is ad-hoc SQL via MCP until a proper dashboard is warranted.
- **Additional indexes** (e.g., composite `(endpoint, model, created_at DESC)` for per-feature-per-model cost rollups) — YAGNI until queries prove slow.
- **Async batching of writes** — log writes are per-call, sub-millisecond. No need for a write-queue or background flusher.
- **Row-level `prompt_version` history table** — denormalized versioning is sufficient; logs are append-only and `prompt_version` is already indexed transitively via findings_hash.
- **Exposing `llm_logs` rows in the frontend** — explicitly out of scope; logs are backend-only diagnostic infrastructure.
- **PII redaction / encryption at rest** — per SEED-003, prompts contain only aggregated user stats (no game PGNs, no opponent usernames), so no redaction needed in v1.11. Revisit if future LLM features log game moves or opponent text.

</deferred>

---

*Phase: 64-llm-logs-table-async-repo*
*Context gathered: 2026-04-20*
