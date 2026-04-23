---
quick_id: 260423-a4a
slug: remove-system-prompt-fix-thinking-tokens
status: complete
date: 2026-04-23
---

# Quick Task 260423-a4a — Summary

## Task 1 — `system_prompt` column removed ✓

- **Migration:** `alembic/versions/20260423_052228_c72eeee6a61a_drop_llm_logs_system_prompt.py` (upgrade drops column, downgrade re-creates as `Text NOT NULL`).
- **ORM:** removed from `app/models/llm_log.py`.
- **Schema:** removed `system_prompt: str` from `LlmLogCreate` (`app/schemas/llm_log.py`); docstring updated.
- **Service:** dropped `system_prompt=_SYSTEM_PROMPT` kwarg from the `LlmLogCreate(...)` call in `app/services/insights_llm.py:generate_insights`. The two `Agent(system_prompt=_SYSTEM_PROMPT, ...)` kwargs stay — those are pydantic-ai agent init, not DB writes.
- **Tests:** removed `system_prompt=` from fixture calls in `tests/test_llm_log_repository{,_reads,_cascade}.py`, `tests/services/test_insights_llm.py`, `tests/test_insights_router.py`, and from the expected column set in `tests/test_llm_logs_migration.py`. The `test_system_prompt_loaded_from_file` test (insights_llm) was kept — it exercises file loading, unrelated to the DB column.

**Verification:**
- `uv run alembic upgrade head` ✓
- `uv run ruff check` ✓
- `uv run ty check app/ tests/` ✓
- All 59 tests touching llm_logs fixtures pass ✓
- Full suite: 1033 pass / 8 pre-existing `test_reclassify` FK-violation failures (unrelated — verified by re-running the failing test after `git stash`).

## Task 2 — `thinking_tokens` NULL for Gemini: not a code bug

**Root cause:** config choice, not a wiring bug.

Verified with live `google-gla:gemini-3-flash-preview` calls:

| `GEMINI_THINKING_LEVEL` | `usage.details` | thinking tokens persisted |
| ---------------------- | --------------- | -------------------------- |
| `low` (current default) | `{'text_prompt_tokens': N}` | NULL |
| `high`                  | `{'thoughts_tokens': 463, 'text_prompt_tokens': N}` | 463 |

Why: pydantic-ai's Google adapter (`pydantic_ai/models/google.py:1453`) only copies the key when non-zero — `if thoughts_token_count := (metadata.thoughts_token_count or 0): details['thoughts_tokens'] = thoughts_token_count`. Gemini-3 at `thinking_level='low'` returns `thoughts_token_count=0` (regardless of structured-output shape, system-prompt length, or `include_thoughts`), so the key is omitted. Our extraction at `insights_llm.py:693` — `usage.details.get("thoughts_tokens") or None` — correctly returns None.

**Production check (local dev DB):** 8 successful Gemini calls, all with `thinking_tokens=NULL` as expected for the current config. Prod DB does not yet have the `llm_logs` table (Phase 64 not deployed).

**Recommendation (not implemented — decision left to user):**
- If actual thinking is desired for quality reasons, set `GEMINI_THINKING_LEVEL=high` in `.env`.
- Trade-off: the high-level test call produced ~3× more output tokens and noticeably higher latency. Cost increase is real and per-call.
- No code change required — only a `.env` flip. Decision depends on whether measurable quality lift justifies the spend for this feature.

## Files touched

```
alembic/versions/20260423_052228_c72eeee6a61a_drop_llm_logs_system_prompt.py  (new)
app/models/llm_log.py
app/schemas/llm_log.py
app/services/insights_llm.py
tests/test_llm_log_cascade.py
tests/test_llm_log_repository.py
tests/test_llm_log_repository_reads.py
tests/test_llm_logs_migration.py
tests/services/test_insights_llm.py
tests/test_insights_router.py
```
