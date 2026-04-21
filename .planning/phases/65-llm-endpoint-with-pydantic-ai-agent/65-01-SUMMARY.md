---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: "01"
subsystem: backend
tags: [pydantic-ai, llm, configuration, system-prompt, testing]
dependency_graph:
  requires: []
  provides:
    - pydantic-ai-slim v1.85.0 installed and importable
    - Settings.PYDANTIC_AI_MODEL_INSIGHTS and INSIGHTS_HIDE_OVERVIEW fields
    - app/services/insights_prompts/endgame_v1.md system prompt
    - tests/conftest.py PYDANTIC_AI_MODEL_INSIGHTS=test env var
  affects:
    - Wave 2+ plans (65-02 through 65-06) that import app.services.insights_llm
tech_stack:
  added:
    - pydantic-ai-slim[anthropic,google]==1.85.0
  patterns:
    - env-var-before-import pattern in conftest.py (matches existing SENTRY_DSN/SECRET_KEY pattern)
    - versioned system prompt as standalone Markdown file loaded once at startup
key_files:
  created:
    - app/services/insights_prompts/__init__.py
    - app/services/insights_prompts/endgame_v1.md
  modified:
    - pyproject.toml
    - uv.lock
    - app/core/config.py
    - .env.example
    - tests/conftest.py
decisions:
  - pydantic-ai-slim[anthropic,google] pinned >=1.85,<2.0 (slim extras cover anthropic:* and google-gla:* model strings; <2.0 cap guards against API renames per RESEARCH.md)
  - PYDANTIC_AI_MODEL_INSIGHTS default is empty string (treated as unconfigured; lifespan raises on empty — enforced by PLAN 05)
  - System prompt in endgame_v1.md with 7 ## sections including full metric glossary inline (D-30)
  - Test provider "test" set in conftest.py before all app imports (D-40)
metrics:
  duration_minutes: 3
  completed_date: "2026-04-21"
  tasks_completed: 5
  tasks_total: 5
  files_created: 2
  files_modified: 5
---

# Phase 65 Plan 01: Wave-1 Prep — pydantic-ai Dependency, Config, System Prompt Summary

pydantic-ai-slim v1.85.0 installed with anthropic+google extras; Settings extended with two LLM config fields; versioned system prompt committed; conftest bootstrapped with test provider env var.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add pydantic-ai-slim dependency and regenerate lockfile | d646b95 | pyproject.toml, uv.lock |
| 2 | Add PYDANTIC_AI_MODEL_INSIGHTS + INSIGHTS_HIDE_OVERVIEW to Settings | 47d350d | app/core/config.py |
| 3 | Document new env vars in .env.example | 5c9794a | .env.example |
| 4 | Create the Phase 65 system prompt file (endgame_v1.md) | d7a3f12 | app/services/insights_prompts/__init__.py, app/services/insights_prompts/endgame_v1.md |
| 5 | Extend tests/conftest.py with PYDANTIC_AI_MODEL_INSIGHTS env var | ce749f2 | tests/conftest.py |

## Key Artifacts

### pydantic-ai-slim Version

Installed version: **1.85.0** (from uv.lock `name = "pydantic-ai-slim"`, `version = "1.85.0"`).

Pin: `pydantic-ai-slim[anthropic,google]>=1.85,<2.0` in pyproject.toml.

Transitive deps added: anthropic v0.96.0, google-genai v1.73.1, pydantic-graph v1.85.0, and supporting libs.

### System Prompt Sections

`app/services/insights_prompts/endgame_v1.md` contains **7 `## ` headings** (55 lines total):

1. Output contract
2. Section gating
3. Cross-section flags (all 4 flag IDs: `baseline_lift_mutes_score_gap`, `clock_entry_advantage`, `no_clock_entry_advantage`, `notable_endgame_elo_divergence`)
4. Series interpretation (all 4 timeline IDs: `score_gap_timeline`, `clock_diff_timeline`, `endgame_elo_timeline`, `type_win_rate_timeline`)
5. Overview rule
6. Metric glossary (10 metrics with UI-consistent definitions)
7. Tone

### Test Suite Count

- **Before plan:** 949 passed, 1 skipped (baseline as of 2026-04-21)
- **After plan:** 949 passed, 1 skipped (no regressions; plan adds no new tests — Wave 2+ adds tests)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This plan adds no data-rendering components. The `PYDANTIC_AI_MODEL_INSIGHTS` default of `""` is intentional (unconfigured sentinel); enforcement via lifespan is PLAN 05 scope.

## Threat Flags

None. `.env.example` uses placeholder `sk-ant-...` (not a real key). No new network endpoints or auth paths introduced in this plan.

## Self-Check: PASSED

- `app/services/insights_prompts/__init__.py` exists: FOUND
- `app/services/insights_prompts/endgame_v1.md` exists: FOUND (55 lines, 7 `##` sections)
- Commit d646b95 exists: FOUND (pyproject.toml + uv.lock)
- Commit 47d350d exists: FOUND (app/core/config.py)
- Commit 5c9794a exists: FOUND (.env.example)
- Commit d7a3f12 exists: FOUND (insights_prompts package + endgame_v1.md)
- Commit ce749f2 exists: FOUND (tests/conftest.py)
- `uv run ty check app/ tests/`: 0 errors
- `uv run ruff check .`: 0 errors
- `uv run pytest -x -q`: 949 passed, 1 skipped
