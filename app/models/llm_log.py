"""Llm log ORM model — one row per LLM cache-miss call.

Generic across future LLM features (naming convention: <feature>.<subfeature> for
`endpoint`, e.g. `insights.endgame`). See SEED-003 §"Log table schema" and
Phase 64 CONTEXT.md for the locked column set + index plan. D-02 explains
the repo-owned-session deviation from import_job_repository's co-transactional
pattern.
"""

import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class LlmLog(Base):
    __tablename__ = "llm_logs"
    __table_args__ = (
        Index("ix_llm_logs_created_at", "created_at"),
        Index(
            "ix_llm_logs_user_id_created_at",
            "user_id",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("ix_llm_logs_findings_hash", "findings_hash"),
        Index(
            "ix_llm_logs_endpoint_created_at",
            "endpoint",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index(
            "ix_llm_logs_model_created_at",
            "model",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # users.id is Integer (4-byte), NOT BigInteger. FK column type MUST match.
    # CONTEXT.md D-06 says "BigInt FK" but that is a misread of D-05 — see
    # RESEARCH.md Pitfall 1. Use Integer.
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    endpoint: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    findings_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    filter_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    # Thinking/reasoning tokens, when the provider reports them (Gemini 3 via
    # pydantic-ai's `usage.details["thoughts_tokens"]`). Null for providers that
    # don't expose a separate thinking count (Anthropic, OpenAI, test provider).
    # Not included in cost_usd — genai-prices already bills these inside
    # output_tokens for Google models.
    thinking_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
