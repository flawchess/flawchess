"""Pydantic v2 schemas for llm_logs writes.

LlmLogEndpoint is a single-member Literal in Phase 64 — extend it when new
LLM features ship (Phase 65+ adds nothing; future milestones add more).

All fields come from the caller:
  - user_id, endpoint, prompt_version, findings_hash, filter_context,
    user_prompt, cache_hit, error — request/context
  - model — the pydantic-ai model string (e.g. `anthropic:claude-haiku-4-5-20251001`)
  - response_json — parsed EndgameInsightsReport dict, or None on error
  - input_tokens, output_tokens — from pydantic-ai RunResult.usage()
  - latency_ms — wall-clock time caller measured around Agent.run()

Fields NOT on LlmLogCreate (repo/DB compute):
  - id (DB auto)
  - created_at (DB default)
  - cost_usd (repo: genai-prices.calc_price)
"""

from typing import Any, Literal

from pydantic import BaseModel

LlmLogEndpoint = Literal["insights.endgame"]


class LlmLogFilterContext(BaseModel):
    """Minimal filter state persisted per log row.

    The insights router rejects (HTTP 400) any filter other than
    `opponent_strength` that is non-default, so every log row's filter context
    collapses to just this one field. Keeping the shape narrow matches what
    actually varies; widen it if future versions lift the full-history gate.
    """

    opponent_strength: Literal["any", "stronger", "similar", "weaker"]


class LlmLogCreate(BaseModel):
    user_id: int
    endpoint: LlmLogEndpoint
    model: str  # pydantic-ai provider:model format, e.g. "anthropic:claude-haiku-4-5-20251001"
    prompt_version: str
    findings_hash: str  # 64-char sha256 hex from insights_service.compute_findings (Phase 63)
    filter_context: LlmLogFilterContext
    user_prompt: str
    response_json: dict[str, Any] | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool = False
    # Thinking/reasoning tokens when the provider reports them (Gemini 3 via
    # pydantic-ai's `usage.details["thoughts_tokens"]`). None otherwise.
    thinking_tokens: int | None = None
    error: str | None = None
