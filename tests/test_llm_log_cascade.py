"""SC #3 / LOG-04: ON DELETE CASCADE on llm_logs.user_id.

Deleting a user MUST delete that user's llm_logs rows. This is a GDPR
requirement (SEED-003 §Privacy) enforced by the FK `ondelete="CASCADE"`
declared in app/models/llm_log.py and materialized in the Phase 64
migration (Plan 02).

This test explicitly creates + deletes its own user (not via the
fresh_test_user fixture) because the fixture auto-deletes on teardown and
this test needs to control the delete timing.

Per RESEARCH.md Pitfall 5, cannot use db_session: create_llm_log opens its
own async_session_maker() scope which commits outside the fixture's
rollback transaction.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.llm_log import LlmLog
from app.models.user import User
from app.repositories.llm_log_repository import create_llm_log
from app.schemas.llm_log import LlmLogCreate


@pytest.mark.asyncio
async def test_deleting_user_cascades_llm_logs(test_engine: Any) -> None:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    # Setup: create a user via own-session commit (NOT db_session — would roll back).
    async with session_maker() as session:
        user = User(
            email=f"cascade-{uuid.uuid4()}@example.com",
            hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Act 1: insert a log row for this user.
    data = LlmLogCreate(
        user_id=user_id,
        endpoint="insights.endgame",
        model="anthropic:claude-haiku-4-5-20251001",
        prompt_version="endgame_v1",
        findings_hash="e" * 64,
        filter_context={},
        flags=[],
        system_prompt="s",
        user_prompt="u",
        response_json={"overview": "ok", "sections": []},
        input_tokens=10,
        output_tokens=5,
        latency_ms=100,
    )
    row = await create_llm_log(data)
    log_id = row.id
    assert log_id is not None

    # Act 2: delete the user.
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()

    # Assert: the log row is gone (cascaded).
    async with session_maker() as session:
        result = await session.execute(select(LlmLog).where(LlmLog.id == log_id))
        assert result.scalar_one_or_none() is None, (
            "llm_logs row was not cascaded — FK ON DELETE CASCADE is broken"
        )
