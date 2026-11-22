"""Guard: registered users never land on a hard-coded test user id.

Tests hard-code user ids below 10M and ensure_test_user reuses an existing
row, so a user registered through the real auth endpoint (committed past the
db_session rollback) must never be handed one of those ids. tests/conftest.py
starts the users sequence at _REGISTERED_USER_ID_START in every run DB.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _REGISTERED_USER_ID_START


@pytest.mark.asyncio
async def test_users_sequence_starts_above_hard_coded_ids(db_session: AsyncSession) -> None:
    # nextval is non-transactional, so this burns one id; harmless.
    next_id = (
        await db_session.execute(text("SELECT nextval(pg_get_serial_sequence('users', 'id'))"))
    ).scalar_one()
    assert next_id >= _REGISTERED_USER_ID_START
