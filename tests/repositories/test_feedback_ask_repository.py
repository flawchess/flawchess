"""Transition matrix for the feedback-ask repository against real Postgres (SEED-191 #6-#8).

Each transition is one guarded ``UPDATE ... RETURNING`` on ``users.prompt_state``; these
tests call the repository directly with explicit ``today`` / ``active_days`` so no clock
pinning is needed. Uses the rollback-scoped ``db_session`` fixture, so nothing leaks.
"""

import datetime
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_activity import UserActivity
from app.repositories import feedback_ask_repository as repo
from app.schemas.feedback_ask import (
    FEEDBACK_ASK_ID,
    FEEDBACK_ASK_MAX_VIEWS,
    FEEDBACK_ASK_REASK_GAP_DAYS,
    FeedbackAskState,
)
from tests.conftest import ensure_test_user

pytestmark = pytest.mark.asyncio

_USER_ID = 23400  # unique id range for this module

TODAY = datetime.date(2026, 3, 10)
YESTERDAY = TODAY - datetime.timedelta(days=1)
ACTIVE_DAYS = 6
SNOOZED_AT_DAYS = 6
# Round-2 boundary: the re-ask needs a full gap of further active days.
REASK_BOUNDARY = SNOOZED_AT_DAYS + FEEDBACK_ASK_REASK_GAP_DAYS
FAR_FUTURE_ACTIVE_DAYS = 100


async def _seed(session: AsyncSession, ask: dict[str, object] | None = None) -> None:
    await ensure_test_user(session, _USER_ID)
    state: dict[str, object] = {} if ask is None else {FEEDBACK_ASK_ID: ask}
    await session.execute(update(User).where(User.id == _USER_ID).values(prompt_state=state))


async def _stored(session: AsyncSession) -> dict[str, object]:
    result = await session.execute(select(User.prompt_state).where(User.id == _USER_ID))
    return dict(result.scalar_one())


async def _view(session: AsyncSession, today: datetime.date, active_days: int) -> object:
    return await repo.apply_view(session, user_id=_USER_ID, today=today, active_days=active_days)


def _asking(views: int, last_view: datetime.date) -> dict[str, object]:
    return {"round": 1, "views": views, "last_view_date": last_view.isoformat()}


def _snoozed(
    *, round_: int, by: str, at_days: int = SNOOZED_AT_DAYS, last_view: datetime.date = YESTERDAY
) -> dict[str, object]:
    return {
        "status": "snoozed",
        "round": round_,
        "views": FEEDBACK_ASK_MAX_VIEWS,
        "last_view_date": last_view.isoformat(),
        "snoozed_at_days": at_days,
        "snoozed_by": by,
    }


class TestView:
    async def test_first_view_on_empty_state(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        state = await _view(db_session, TODAY, ACTIVE_DAYS)
        assert state == FeedbackAskState(round=1, views=1, last_view_date=TODAY)

    async def test_same_day_view_is_noop(self, db_session: AsyncSession) -> None:
        await _seed(db_session, _asking(1, TODAY))
        assert await _view(db_session, TODAY, ACTIVE_DAYS) is None
        assert (await _stored(db_session))[FEEDBACK_ASK_ID] == _asking(1, TODAY)

    async def test_next_day_view_increments(self, db_session: AsyncSession) -> None:
        await _seed(db_session, _asking(1, YESTERDAY))
        state = await _view(db_session, TODAY, ACTIVE_DAYS)
        assert state == FeedbackAskState(round=1, views=2, last_view_date=TODAY)

    async def test_third_view_day_auto_snoozes(self, db_session: AsyncSession) -> None:
        await _seed(db_session, _asking(FEEDBACK_ASK_MAX_VIEWS - 1, YESTERDAY))
        state = await _view(db_session, TODAY, ACTIVE_DAYS)
        assert state == FeedbackAskState(
            status="snoozed",
            round=1,
            views=FEEDBACK_ASK_MAX_VIEWS,
            last_view_date=TODAY,
            snoozed_at_days=ACTIVE_DAYS,
            snoozed_by="views",
        )

    async def test_round_two_waits_for_the_full_gap(self, db_session: AsyncSession) -> None:
        await _seed(db_session, _snoozed(round_=1, by="click"))
        assert await _view(db_session, TODAY, REASK_BOUNDARY - 1) is None

    async def test_round_two_starts_at_the_gap_with_exact_state(
        self, db_session: AsyncSession
    ) -> None:
        await _seed(db_session, _snoozed(round_=1, by="click"))
        state = await _view(db_session, TODAY, REASK_BOUNDARY)
        assert state == FeedbackAskState(round=2, views=1, last_view_date=TODAY)
        # status / snoozed_* are gone, not merely null.
        assert (await _stored(db_session))[FEEDBACK_ASK_ID] == {
            "round": 2,
            "views": 1,
            "last_view_date": TODAY.isoformat(),
        }

    @pytest.mark.parametrize("by", ["click", "views"])
    async def test_exhausted_round_two_is_never_viewed_again(
        self, db_session: AsyncSession, by: str
    ) -> None:
        await _seed(db_session, _snoozed(round_=2, by=by))
        assert await _view(db_session, TODAY, FAR_FUTURE_ACTIVE_DAYS) is None

    async def test_done_is_never_viewed(self, db_session: AsyncSession) -> None:
        await _seed(db_session, {"status": "done", "round": 1, "views": 1})
        assert await _view(db_session, TODAY, FAR_FUTURE_ACTIVE_DAYS) is None

    async def test_guest_is_never_written(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        await db_session.execute(update(User).where(User.id == _USER_ID).values(is_guest=True))
        assert await _view(db_session, TODAY, ACTIVE_DAYS) is None
        assert await _stored(db_session) == {}


class TestSnooze:
    async def test_snooze_from_asking(self, db_session: AsyncSession) -> None:
        await _seed(db_session, _asking(2, YESTERDAY))
        state = await repo.apply_snooze(
            db_session, user_id=_USER_ID, today=TODAY, active_days=ACTIVE_DAYS
        )
        assert state == FeedbackAskState(
            status="snoozed",
            round=1,
            views=2,
            last_view_date=YESTERDAY,
            snoozed_at_days=ACTIVE_DAYS,
            snoozed_by="click",
        )

    async def test_snooze_during_third_view_grace_day_becomes_click(
        self, db_session: AsyncSession
    ) -> None:
        await _seed(db_session, _snoozed(round_=1, by="views", last_view=TODAY))
        state = await repo.apply_snooze(
            db_session, user_id=_USER_ID, today=TODAY, active_days=ACTIVE_DAYS + 1
        )
        assert state is not None
        assert state.snoozed_by == "click"
        assert state.snoozed_at_days == ACTIVE_DAYS + 1

    async def test_snooze_when_already_snoozed_by_click_is_noop(
        self, db_session: AsyncSession
    ) -> None:
        await _seed(db_session, _snoozed(round_=1, by="click"))
        assert (
            await repo.apply_snooze(
                db_session, user_id=_USER_ID, today=TODAY, active_days=ACTIVE_DAYS
            )
            is None
        )


class TestDone:
    @pytest.mark.parametrize(
        "ask",
        [
            _asking(2, YESTERDAY),
            _snoozed(round_=1, by="click"),
            _snoozed(round_=1, by="views", last_view=TODAY),
        ],
        ids=["from-asking", "from-snoozed", "from-grace"],
    )
    async def test_done_from_any_live_state(
        self, db_session: AsyncSession, ask: dict[str, object]
    ) -> None:
        await _seed(db_session, ask)
        state = await repo.apply_done(db_session, user_id=_USER_ID)
        assert state is not None
        assert state.status == "done"

    async def test_second_done_is_noop(self, db_session: AsyncSession) -> None:
        await _seed(db_session, {"status": "done", "round": 1})
        assert await repo.apply_done(db_session, user_id=_USER_ID) is None

    async def test_done_on_empty_state_creates_the_key(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        state = await repo.apply_done(db_session, user_id=_USER_ID)
        assert state == FeedbackAskState(status="done")


async def _snooze(session: AsyncSession) -> object:
    return await repo.apply_snooze(session, user_id=_USER_ID, today=TODAY, active_days=ACTIVE_DAYS)


async def _done(session: AsyncSession) -> object:
    return await repo.apply_done(session, user_id=_USER_ID)


@pytest.mark.parametrize(
    "transition",
    [
        lambda session: _view(session, TODAY, ACTIVE_DAYS),
        _snooze,
        _done,
    ],
    ids=["view", "snooze", "done"],
)
async def test_every_transition_preserves_unrelated_keys(
    db_session: AsyncSession, transition: Callable[[AsyncSession], Awaitable[object]]
) -> None:
    await ensure_test_user(db_session, _USER_ID)
    other: dict[str, object] = {"status": "done"}
    await db_session.execute(
        update(User).where(User.id == _USER_ID).values(prompt_state={"other_ask": other})
    )
    assert await transition(db_session) is not None
    stored = await _stored(db_session)
    assert stored["other_ask"] == other
    assert isinstance(stored[FEEDBACK_ASK_ID], dict)


async def test_count_active_days_before_is_strictly_before_today(
    db_session: AsyncSession,
) -> None:
    await ensure_test_user(db_session, _USER_ID)
    days = [
        YESTERDAY - datetime.timedelta(days=1),
        YESTERDAY,
        TODAY,
        TODAY + datetime.timedelta(days=1),
    ]
    db_session.add_all([UserActivity(user_id=_USER_ID, activity_date=day) for day in days])
    await db_session.flush()
    count = await repo.count_active_days_before(db_session, user_id=_USER_ID, today=TODAY)
    assert count == 2


async def test_get_state_absent_key_is_none(db_session: AsyncSession) -> None:
    await _seed(db_session)
    assert await repo.get_state(db_session, user_id=_USER_ID) is None
