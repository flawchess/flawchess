"""Integration tests for the feedback repository.

Coverage:
- TestFeedbackRepository: create_feedback returns row with populated PK,
  rating stored as 1-5 integer (including None case).
- source round-trip and the ck_feedback_source CHECK backstop (SEED-191 #9).
"""

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.repositories.feedback_repository import create_feedback
from app.schemas.feedback import FeedbackCreate


# ---------------------------------------------------------------------------
# Test user IDs (FK constraints require valid user_id)
# ---------------------------------------------------------------------------

_TEST_USER_IDS = [1001, 1002]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in the users table before each test."""
    from tests.conftest import ensure_test_user

    for uid in _TEST_USER_IDS:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# TestFeedbackRepository
# ---------------------------------------------------------------------------


class TestFeedbackRepository:
    """Verify create_feedback repository function."""

    @pytest.mark.asyncio
    async def test_create_feedback_returns_row_with_populated_id(
        self, db_session: AsyncSession
    ) -> None:
        """create_feedback returns a Feedback ORM object with PK populated post-flush."""
        data = FeedbackCreate(
            text="Great analysis feature!",
            rating=5,
            page_url="/openings",
        )
        feedback = await create_feedback(db_session, user_id=1001, data=data)

        assert feedback.id is not None
        assert feedback.id > 0
        assert feedback.user_id == 1001
        assert feedback.text == "Great analysis feature!"
        assert feedback.page_url == "/openings"
        assert feedback.rating == 5

    @pytest.mark.asyncio
    async def test_create_feedback_stores_rating_value(self, db_session: AsyncSession) -> None:
        """create_feedback stores each 1-5 star rating value as-is."""
        for rating in (1, 2, 3, 4, 5):
            data = FeedbackCreate(
                text="Test feedback",
                rating=rating,
                page_url="/endgames",
            )
            feedback = await create_feedback(db_session, user_id=1001, data=data)
            assert feedback.rating == rating

    @pytest.mark.asyncio
    async def test_create_feedback_stores_none_rating(self, db_session: AsyncSession) -> None:
        """create_feedback stores None when rating is omitted."""
        data = FeedbackCreate(
            text="Anonymous feedback without rating",
            page_url="/openings",
        )
        feedback = await create_feedback(db_session, user_id=1002, data=data)

        assert feedback.id is not None
        assert feedback.rating is None

    @pytest.mark.asyncio
    async def test_create_feedback_user_id_from_argument_not_data(
        self, db_session: AsyncSession
    ) -> None:
        """user_id on the row comes from the passed argument, not from request data (V4)."""
        data = FeedbackCreate(
            text="V4 access control test",
            page_url="/stats",
        )
        # Pass user_id=1002 explicitly — the schema has no user_id field
        feedback = await create_feedback(db_session, user_id=1002, data=data)

        assert feedback.user_id == 1002

    @pytest.mark.asyncio
    async def test_create_feedback_stores_default_source(self, db_session: AsyncSession) -> None:
        """A FeedbackCreate without source persists 'floating_button'."""
        data = FeedbackCreate(text="Default source", page_url="/openings")
        feedback = await create_feedback(db_session, user_id=1001, data=data)

        assert feedback.source == "floating_button"

    @pytest.mark.asyncio
    async def test_create_feedback_stores_milestone_ask_source(
        self, db_session: AsyncSession
    ) -> None:
        """create_feedback writes the schema's source onto the row."""
        data = FeedbackCreate(text="From the ask", page_url="/openings", source="milestone_ask")
        feedback = await create_feedback(db_session, user_id=1001, data=data)

        assert feedback.source == "milestone_ask"

    @pytest.mark.asyncio
    async def test_check_constraint_rejects_unknown_source(self, db_session: AsyncSession) -> None:
        """ck_feedback_source is the DB backstop under the Pydantic Literal."""
        db_session.add(Feedback(user_id=1001, page_url="/x", text="bad source", source="bogus"))
        with pytest.raises(IntegrityError, match="ck_feedback_source"):
            await db_session.flush()
