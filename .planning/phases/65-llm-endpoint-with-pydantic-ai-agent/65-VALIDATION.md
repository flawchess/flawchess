---
phase: 65
slug: llm-endpoint-with-pydantic-ai-agent
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async-mode via pytest-asyncio) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) + `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/services/test_insights_llm.py tests/routers/test_insights_router.py tests/repositories/test_llm_log_repository_reads.py tests/services/test_insights_service_series.py -x` |
| **Full suite command** | `uv run pytest -x && uv run ruff check . && uv run ty check app/ tests/` |
| **Estimated runtime** | ~45 seconds (quick), ~3-5 minutes (full) |

---

## Sampling Rate

- **After every task commit:** Run the relevant test file for that task (e.g. schema task → `pytest tests/services/test_insights_service_series.py`)
- **After every plan wave:** Run the quick command above (all 4 new test files)
- **Before `/gsd-verify-work`:** Full suite must be green (tests + ruff + ty)
- **Max feedback latency:** 60 seconds for quick, 5 minutes for full

---

## Per-Task Verification Map

> This table gets populated by the planner. Each task row references its plan file, wave, requirement ID, and the specific pytest command that verifies it.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {populated-by-planner} | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 installs new dependencies and creates test scaffolding. Everything below must exist (or be explicitly created by Wave 0 tasks) before Wave 1+ tests can run.

- [ ] `pydantic-ai-slim[anthropic,google]` added to `pyproject.toml` (pinned `>=1.85,<2.0`)
- [ ] `uv.lock` regenerated via `uv lock`
- [ ] `tests/conftest.py` extended with `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` before any `from app...` import (mirrors existing `SENTRY_DSN` + `SECRET_KEY` pattern, per D-40)
- [ ] `tests/services/test_insights_llm.py` — stub file created for LLM-01, LLM-02, LLM-03, INS-04, INS-05, INS-06 tests
- [ ] `tests/routers/test_insights_router.py` — stub file for INS-07 + end-to-end envelope tests
- [ ] `tests/repositories/test_llm_log_repository_reads.py` — stub for new D-34 read helpers
- [ ] `tests/services/test_insights_service_series.py` — stub for D-03/D-04/D-05 resampling logic
- [ ] `tests/conftest.py` gains `fake_insights_agent(report)` fixture that monkeypatches `get_insights_agent()` with `TestModel(custom_output_args=report.model_dump())` per D-38
- [ ] `app/services/insights_prompts/endgame_v1.md` created (even if short) — startup validation requires the file to exist; tests require it too

*If none of the above exist before Wave 1, import errors will mask real failures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Startup aborts on missing `PYDANTIC_AI_MODEL_INSIGHTS` env | LLM-02 / D-22 | Requires actual Uvicorn startup in a dev shell; pytest can exercise the `get_insights_agent()` raise but not the full lifespan abort | `unset PYDANTIC_AI_MODEL_INSIGHTS && uv run uvicorn app.main:app` → confirm exit code non-zero + error message cites missing config |
| Real pydantic-ai call against Anthropic returns a valid `EndgameInsightsReport` | LLM-01 end-to-end | Costs real tokens; belongs to Phase 67 VAL-01 regression. Phase 65 verifies only via `TestModel` / `FunctionModel` per D-42 | Deferred to Phase 67 |
| Sentry error-grouping stays intact under a simulated provider outage | LOG-04 / D-36 / D-37 | Requires Sentry dashboard inspection, not a test runner | Trigger provider error locally, check https://flawchess.sentry.io/issues/ — confirm single issue, not one per `findings_hash` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for per-task, < 5min for full suite
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
