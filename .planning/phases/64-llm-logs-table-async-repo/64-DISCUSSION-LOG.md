# Phase 64: `llm_logs` Table & Async Repo - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 64-llm-logs-table-async-repo
**Areas discussed:** Repo API surface, Cost-computation boundary, Transaction/session semantics, endpoint column typing

---

## Gray-Area Selection

Four gray areas were presented; the user accepted all four recommendations without individual deep-dive (response: "your recommendations sound good, nothing to discuss"). The recommendations below were therefore adopted as the decisions and written to CONTEXT.md.

| Gray Area | Options Presented | Selected |
|-----------|-------------------|----------|
| Repo API surface | One `create_llm_log(**kwargs)` with 16 kwargs / **Pydantic `LlmLogCreate` input DTO** (Recommended) / TypedDict | ✓ Pydantic input DTO |
| Cost-computation boundary | **Repo owns `genai-prices`** (Recommended) / Caller pre-computes `cost_usd` | ✓ Repo owns it |
| Transaction/session semantics | Caller's `AsyncSession` (matches existing pattern) / **Repo opens its own session_maker scope** (Recommended) / Both signatures | ✓ Own session for durability |
| `endpoint` column typing | **String(50) + Literal module constant** (Recommended) / Postgres Enum / Free string, no typing | ✓ String(50) + Literal |

**User's choice:** Accept all four recommendations.
**Notes:** User confirmed via freeform response that the recommended defaults were acceptable. No individual area required deeper discussion because the phase is unusually locked by REQUIREMENTS.md (LOG-01–LOG-04 specify the 17-column schema, 5 indexes, cascade FK, and cost-fallback behavior) — only the repo-level API/integration choices remained as gray areas.

## Claude's Discretion

- Exact module layout within `app/models/` / `app/schemas/` / `app/repositories/` (follows existing pattern).
- `genai-prices` sync/async API selection and exception name to catch — researcher validates via context7.
- Pydantic field ordering and field-level validators inside `LlmLogCreate`.
- Whether `response_json` stores raw provider response vs parsed `EndgameInsightsReport` dict vs both (planner picks, documents in model docstring).
- Return type of `create_llm_log` (picked: full `LlmLog` ORM object).
- Whether to add a `CHECK (cache_hit = FALSE)` constraint (deferred — column exists for future hit-logging).

## Deferred Ideas

- Cache-hit logging policy (Phase 65 decision)
- Retention / archival schedule (future ops task)
- Cost dashboard / query views (YAGNI)
- Additional composite indexes (YAGNI until slow queries emerge)
- Async batching of writes (not needed; per-call writes are sub-ms)
- Frontend exposure of `llm_logs` (explicitly out of scope)
- PII redaction / encryption at rest (not needed in v1.11)
