---
phase: 64-llm-logs-table-async-repo
verified: 2026-04-20T22:00:00Z
status: passed
score: 4/4 roadmap success criteria verified
overrides_applied: 0
re_verification: null
deferred:
  - truth: "Full LOG-04 contract (Sentry set_context for user_id / findings_hash / model at the LLM call site, never embedding variables in error messages)"
    addressed_in: "Phase 65"
    evidence: "Phase 65 goal: 'writing one llm_logs row per miss. This is where the prompt engineering harness comes alive.' Phase 65 SC #4: 'Structured-output validation failures, provider errors, and startup misconfiguration (PYDANTIC_AI_MODEL_INSIGHTS missing/invalid) each surface via Sentry with user_id / findings_hash / model in set_context'. REQUIREMENTS.md maps LOG-04 to Phase 64 (repo side) + Phase 65 (router/service side). Repo side landed (no f-string interpolation in raises; FK CASCADE for GDPR) — LLM-call-site side requires Phase 65."
---

# Phase 64: llm-logs-table-async-repo Verification Report

**Phase Goal:** Generic Postgres log table with async write repository lands in prod so every LLM call (miss) can be captured with prompt, response, tokens, cost, latency, and error fields. Designed up-front to host future LLM features, not endgame-specific.

**Verified:** 2026-04-20T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `alembic upgrade head` creates `llm_logs` with all fields from LOG-01 (incl. `user_id` FK with `ON DELETE CASCADE`) plus the five indexes from LOG-03 | VERIFIED | Migration `alembic/versions/20260420_211450_85dfef624a19_create_llm_logs.py` emits `op.create_table("llm_logs", ...)` with 18 `sa.Column` entries, `sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")`, and 5 `op.create_index` calls with exact locked names. Applied to both dev DB (Docker PG18 per env note) and test DB (via `test_engine` session fixture). `tests/test_llm_logs_migration.py` inspects `get_columns`, `get_indexes`, `get_foreign_keys` at runtime and passes. |
| 2 | A developer can call the async repo to insert a log row with prompt, response, token counts, and computed `cost_usd` (via `genai-prices`) and read it back | VERIFIED | `app/repositories/llm_log_repository.py::create_llm_log` inserts via own `async_session_maker()` scope, computes `cost_usd` via `_compute_cost` (split `provider:model` → `calc_price(...)`). `get_latest_log_by_hash` reads with filter (`response_json IS NOT NULL AND error IS NULL`). `tests/test_llm_log_repository.py::test_create_llm_log_inserts_and_returns_row` asserts `row.id is not None`, `row.cost_usd > 0`, `row.error is None` round-trip. `tests/test_llm_log_repository.py::test_get_latest_log_by_hash_returns_most_recent_successful` asserts the read path works end-to-end. |
| 3 | Deleting a user cascades to delete their `llm_logs` rows (verified by integration test) | VERIFIED | `tests/test_llm_log_cascade.py::test_deleting_user_cascades_llm_logs` creates user → inserts log row → deletes user → asserts `select(LlmLog).where(LlmLog.id == log_id)` returns None. Test passes. FK CASCADE landed in migration (line 54 of migration: `sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")`) and in ORM model (`app/models/llm_log.py` line 51: `ForeignKey("users.id", ondelete="CASCADE")`). |
| 4 | `cost_usd` falls back to 0 with `error = "cost_unknown:<model>"` when `genai-prices` doesn't recognize the model, rather than failing the write | VERIFIED | `app/repositories/llm_log_repository.py::_finalize_cost_and_error` returns `(Decimal("0"), marker)` on `LookupError`. `tests/test_llm_log_repository.py::test_unknown_model_records_cost_unknown_and_zero_cost` asserts `row.cost_usd == Decimal("0")` and `row.error == "cost_unknown:fictional-vendor:fake-model-9000"`. `test_unknown_model_appends_to_existing_error` asserts append-to-existing-error semantics with `"; "` separator. |

**Score:** 4/4 roadmap success criteria verified.

### Deferred Items

Only the Sentry-call-site half of LOG-04 is deferred (see frontmatter `deferred:`). The repo-side half (no f-string interpolation in raised errors; FK CASCADE for GDPR) is covered by Phase 64's cascade test and the static absence of `sentry`/f-string-raise patterns in the repo module.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/llm_log.py` | `LlmLog` ORM class: 18 columns, 5 indexes (3 with `postgresql_ops={"created_at": "DESC"}`), Integer FK to users.id with CASCADE, JSONB types | VERIFIED | 73 lines; all required elements confirmed: `BigInteger` PK, `Integer` FK with `ondelete="CASCADE"`, `JSONB` on `filter_context`/`flags`/`response_json`, `Numeric(10, 6)` on `cost_usd`, 5 named indexes in `__table_args__`, `postgresql_ops={"created_at": "DESC"}` on the three composite indexes. |
| `app/schemas/llm_log.py` | `LlmLogEndpoint = Literal["insights.endgame"]`, `LlmLogCreate` with 15 caller-supplied fields | VERIFIED | 42 lines; both exports present. `LlmLogCreate` has `user_id`, `endpoint`, `model`, `prompt_version`, `findings_hash`, `filter_context`, `flags`, `system_prompt`, `user_prompt`, `response_json`, `input_tokens`, `output_tokens`, `latency_ms`, `cache_hit=False`, `error=None`. |
| `app/repositories/llm_log_repository.py` | `create_llm_log`, `get_latest_log_by_hash`, own-session commit pattern, LookupError catch | VERIFIED | 155 lines. Module exports `create_llm_log` (own-session path: `async with async_session_maker() as session: ... commit ... refresh`), `get_latest_log_by_hash` (caller-supplied session). `except LookupError:` catches unknown-model path; `_COST_UNKNOWN_PREFIX = "cost_unknown:"` constant. No `sentry` substring; no f-string interpolation in raise statements. |
| `alembic/versions/*create_llm_logs*.py` | Migration creates llm_logs with 18 columns, 5 indexes, CASCADE FK, `postgresql.JSONB`, DESC on 3 composites | VERIFIED | `20260420_211450_85dfef624a19_create_llm_logs.py`. `down_revision='179cfbd472ef'`. 18 `sa.Column`, 5 `op.create_index`, `postgresql.JSONB(astext_type=sa.Text())` on 3 JSON cols, inline `sa.ForeignKeyConstraint(..., ondelete="CASCADE")`, `postgresql_ops={"created_at": "DESC"}` on 3 composites, `sa.Integer()` (not BigInteger) for user_id FK. |
| `tests/test_llm_log_repository.py` | 4 tests covering happy path, cost_unknown standalone, cost_unknown append, cache lookup | VERIFIED | 4 async tests present (`test_create_llm_log_inserts_and_returns_row`, `test_unknown_model_records_cost_unknown_and_zero_cost`, `test_unknown_model_appends_to_existing_error`, `test_get_latest_log_by_hash_returns_most_recent_successful`). All pass. |
| `tests/test_llm_log_cascade.py` | 1 integration test proving FK CASCADE end-to-end | VERIFIED | `test_deleting_user_cascades_llm_logs` present and passing. |
| `tests/test_llm_logs_migration.py` | Schema smoke test asserting table, 18 cols, 5 indexes, CASCADE FK | VERIFIED | `test_llm_logs_table_exists_with_columns_indexes_and_cascade` uses `inspect()` against `test_engine` to assert all four properties. Passes. |
| `tests/conftest.py::fresh_test_user` | pytest_asyncio fixture commits fresh User via own session, deletes on teardown | VERIFIED | Fixture at lines 194-220 of conftest.py. Uses own `async_sessionmaker(test_engine, ...)`, commits + refreshes user, yields, deletes on teardown. |
| `pyproject.toml` | `genai-prices>=0.0.56,<0.1.0` pinned | VERIFIED | Line 19: `"genai-prices>=0.0.56,<0.1.0",` |
| `alembic/env.py` | `from app.models.llm_log import LlmLog  # noqa: F401` | VERIFIED | Line 18. |
| `app/models/__init__.py` | `LlmLog` re-exported | VERIFIED | Line 4 import, line 6 `__all__`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/models/llm_log.py::LlmLog` | `app/models/base.py::Base` | `class LlmLog(Base)` | WIRED | Confirmed in model file line 21. |
| `app/models/llm_log.py` | `users.id` | `ForeignKey("users.id", ondelete="CASCADE")` | WIRED | Line 51 of model; mirrored in migration line 54. |
| `app/repositories/llm_log_repository.py::create_llm_log` | `app/core/database.py::async_session_maker` | `async with async_session_maker() as session:` | WIRED | Line 59 of repo. Plan 03 SUMMARY documents the conftest.py patch that routes this to the test DB during tests. |
| `app/repositories/llm_log_repository.py::create_llm_log` | `genai_prices.calc_price` | `_compute_cost` with `except LookupError:` fallback | WIRED | `from genai_prices import Usage, calc_price` (line 25); `except LookupError:` (line 112); split-form call (`provider_id`/`model_ref`) matches Plan 01 smoke finding. |
| `alembic/env.py` | `app/models/llm_log.py::LlmLog` | `# noqa: F401` side-effect import | WIRED | Line 18. Without this, autogenerate would not see the model. |
| `tests/test_llm_log_cascade.py` | `llm_logs.user_id FK CASCADE` | `delete(User).where(...)` then `select(LlmLog).where(LlmLog.id == log_id)` assert None | WIRED | Test body lines 66-74. |

### Data-Flow Trace (Level 4)

Not applicable in the frontend sense (no UI artifact). For the repo's data flow:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `create_llm_log(data)` | `row.cost_usd`, `row.error` | `_finalize_cost_and_error(data)` which invokes real `genai_prices.calc_price` | Yes — real Decimal returned for known models (test asserts `cost_usd > 0` against live library) | FLOWING |
| `get_latest_log_by_hash` | returned `LlmLog` | real DB query against `llm_logs` | Yes — test inserts two rows then reads back the correct one | FLOWING |
| Migration DDL | `llm_logs` table in Postgres | `op.create_table` executed by alembic against PG18 | Yes — dev DB and test DB both hold the table (per env note and `test_engine` smoke test) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 64 test bundle green | `uv run pytest tests/test_llm_log_repository.py tests/test_llm_log_cascade.py tests/test_llm_logs_migration.py -x -q` | `6 passed in 0.24s` | PASS |
| Full suite per env note | (env check) `950 tests pass in ~13s` | confirmed by SUMMARY + env note | PASS |
| ty clean per env note | (env check) `ty check app/ tests/` clean | confirmed by env note | PASS |
| ruff clean per env note | (env check) `ruff check .` clean | confirmed by env note | PASS |
| Dev DB at migration head | (env check) local dev DB has `85dfef624a19` applied | confirmed by env note | PASS |

### Requirements Coverage

Phase 64 plans declare requirement IDs `LOG-01`, `LOG-02`, `LOG-03`, `LOG-04` across their frontmatter (64-01: LOG-01/LOG-02; 64-02: LOG-01/LOG-03; 64-03: LOG-02/LOG-04). All four roadmap IDs are claimed by at least one plan.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| LOG-01 | 64-01, 64-02 | llm_logs table with 18 fields incl. user_id FK ON DELETE CASCADE | SATISFIED | Migration applied; smoke test asserts columns + FK CASCADE; dev DB + test DB both migrated. |
| LOG-02 | 64-01, 64-03 | Every cache-miss LLM call writes one row capturing all fields; cost computed via genai-prices at write time | SATISFIED (repo side) | `create_llm_log` implements the write with cost computation. The "every cache-miss call" caller side lives in Phase 65; Phase 64 ships the repo API that Phase 65 will invoke. Repo-side contract is fully in place. |
| LOG-03 | 64-02 | 5 indexes: `(created_at)`, `(user_id, created_at DESC)`, `(findings_hash)`, `(endpoint, created_at DESC)`, `(model, created_at DESC)` | SATISFIED | Migration creates all 5 with correct names; `postgresql_ops={"created_at": "DESC"}` on the 3 composites; dev DB `pg_indexes.indexdef` inspection (per 64-02 SUMMARY) confirms `created_at DESC` landed in the DDL for all 3 composites. |
| LOG-04 | 64-03 | Sentry errors on LLM failures use set_context, never embedding variables in error messages, per CLAUDE.md grouping rules | SATISFIED (repo side) / DEFERRED (Sentry call site) | Repo-side: repo module contains no `sentry` substring, no f-string interpolation inside `raise` statements (static check). The only variable interpolation is the stable `cost_unknown:<model>` marker (non-raising, deliberately stable for LIKE queries). Sentry call site (in the LLM endpoint) is Phase 65 scope — see `deferred:` in frontmatter. REQUIREMENTS.md line 38 marks LOG-04 as Pending, which matches this split. |

No orphaned requirements: all 4 IDs in `.planning/REQUIREMENTS.md` Phase 64 coverage (LOG-01/02/03/04) appear in at least one Phase 64 plan frontmatter.

### Anti-Patterns Found

None.

- `grep TODO|FIXME|XXX|HACK|PLACEHOLDER` on `app/repositories/llm_log_repository.py` → no matches.
- `grep sentry` on the repo module → no matches (satisfies D-08 + LOG-04 grouping).
- No f-string interpolation inside `raise` statements (the module has no raises of its own; DB errors propagate verbatim from SQLAlchemy/asyncpg).
- No empty/stub returns. No hardcoded empty data. No console.log-only code paths.
- Only variable interpolation in the module is `f"{_COST_UNKNOWN_PREFIX}{data.model}"` and `f"{data.error}{_ERROR_JOIN_SEP}{marker}"` in `_finalize_cost_and_error`, which are the SC #4 contract (stable enum-like marker appended to a non-raising data field).

### Human Verification Required

None. All roadmap success criteria are programmatically verifiable and have passing tests. The deferred Sentry-side half of LOG-04 is explicitly scheduled for Phase 65 (Phase 65 SC #4 covers it) and is not a Phase 64 gap.

### Gaps Summary

No gaps. All 4 roadmap success criteria for Phase 64 are met:
1. Migration + table + 18 columns + 5 indexes + CASCADE FK are live in dev and test DBs.
2. Repo writes round-trip with computed cost; reads filter correctly on success criteria.
3. FK CASCADE verified end-to-end via integration test.
4. `cost_unknown:<model>` fallback implemented and tested in both standalone and append forms.

Phase requirements LOG-01 / LOG-02 / LOG-03 are fully satisfied. LOG-04 is half-satisfied on the repo side; the Sentry-call-site half is correctly scoped to Phase 65 per the roadmap. REQUIREMENTS.md already reflects this split (LOG-01/03 marked Complete; LOG-02/04 marked Pending until Phase 65 wires the caller).

Phase 64 goal: **achieved**.

---

_Verified: 2026-04-20T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
