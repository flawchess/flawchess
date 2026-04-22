"""Smoke test: Phase 64 Alembic migration creates llm_logs with locked schema.

Covers SC #1 (LOG-01 table + columns) and partial SC #1 (LOG-03 named indexes —
DESC ordering is verified manually against the dev DB via pg_indexes in Plan 02
Task 3; SQLAlchemy's inspect API does not expose index column ordering).

Uses the session-scoped test_engine fixture which runs `alembic upgrade head`
against flawchess_test once per pytest session (see tests/conftest.py lines 69-99).
"""

import pytest


@pytest.mark.asyncio
async def test_llm_logs_table_exists_with_columns_indexes_and_cascade(test_engine) -> None:
    def _inspect(sync_conn) -> None:
        from sqlalchemy import inspect

        insp = inspect(sync_conn)

        assert "llm_logs" in insp.get_table_names()

        cols = {c["name"] for c in insp.get_columns("llm_logs")}
        expected_cols = {
            "id",
            "user_id",
            "created_at",
            "endpoint",
            "model",
            "prompt_version",
            "findings_hash",
            "filter_context",
            "flags",
            "system_prompt",
            "user_prompt",
            "response_json",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "latency_ms",
            "cache_hit",
            "thinking_tokens",
            "error",
        }
        assert cols == expected_cols, f"missing={expected_cols - cols} extra={cols - expected_cols}"

        ix_names = {i["name"] for i in insp.get_indexes("llm_logs")}
        expected_ix = {
            "ix_llm_logs_created_at",
            "ix_llm_logs_user_id_created_at",
            "ix_llm_logs_findings_hash",
            "ix_llm_logs_endpoint_created_at",
            "ix_llm_logs_model_created_at",
        }
        assert expected_ix <= ix_names, f"missing indexes: {expected_ix - ix_names}"

        fks = insp.get_foreign_keys("llm_logs")
        user_fk = next((f for f in fks if "user_id" in f["constrained_columns"]), None)
        assert user_fk is not None, "FK on user_id missing"
        assert user_fk["referred_table"] == "users"
        assert user_fk["referred_columns"] == ["id"]
        assert user_fk.get("options", {}).get("ondelete") == "CASCADE", (
            f"expected ondelete=CASCADE, got options={user_fk.get('options')}"
        )

    async with test_engine.connect() as conn:
        await conn.run_sync(_inspect)
