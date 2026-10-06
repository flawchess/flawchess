"""Pure truth table for resolve_feedback_ask (SEED-191 #1, #6, #7). No DB, no clock."""

import datetime

import pytest

from app.schemas.feedback_ask import (
    FEEDBACK_ASK_MAX_ROUNDS,
    FEEDBACK_ASK_MAX_VIEWS,
    FEEDBACK_ASK_MIN_ACTIVE_DAYS,
    FEEDBACK_ASK_REASK_GAP_DAYS,
    FeedbackAskState,
)
from app.services.feedback_ask_service import resolve_feedback_ask

TODAY = datetime.date(2026, 3, 10)
YESTERDAY = TODAY - datetime.timedelta(days=1)
SNOOZED_AT = 6

_ELIGIBLE_DAYS = FEEDBACK_ASK_MIN_ACTIVE_DAYS


def _snoozed(*, by: str, round_: int = 1, last_view: datetime.date = YESTERDAY) -> FeedbackAskState:
    return FeedbackAskState.model_validate(
        {
            "status": "snoozed",
            "round": round_,
            "views": FEEDBACK_ASK_MAX_VIEWS,
            "last_view_date": last_view,
            "snoozed_at_days": SNOOZED_AT,
            "snoozed_by": by,
        }
    )


@pytest.mark.parametrize(
    ("state", "active_days", "has_feedback", "is_guest", "expected"),
    [
        pytest.param(None, _ELIGIBLE_DAYS, False, True, False, id="guest"),
        pytest.param(None, _ELIGIBLE_DAYS, True, False, False, id="has-feedback"),
        pytest.param(None, _ELIGIBLE_DAYS - 1, False, False, False, id="below-threshold"),
        pytest.param(None, _ELIGIBLE_DAYS, False, False, True, id="at-threshold-no-state"),
        pytest.param(
            FeedbackAskState(round=1, views=2, last_view_date=YESTERDAY),
            _ELIGIBLE_DAYS,
            False,
            False,
            True,
            id="asking",
        ),
        pytest.param(
            FeedbackAskState(status="done"), _ELIGIBLE_DAYS, False, False, False, id="done"
        ),
        pytest.param(_snoozed(by="click"), SNOOZED_AT, False, False, False, id="snoozed-by-click"),
        pytest.param(
            _snoozed(by="views", last_view=TODAY), SNOOZED_AT, False, False, True, id="grace-day"
        ),
        pytest.param(_snoozed(by="views"), SNOOZED_AT, False, False, False, id="day-after-grace"),
        pytest.param(
            _snoozed(by="click"),
            SNOOZED_AT + FEEDBACK_ASK_REASK_GAP_DAYS - 1,
            False,
            False,
            False,
            id="reask-one-day-early",
        ),
        pytest.param(
            _snoozed(by="click"),
            SNOOZED_AT + FEEDBACK_ASK_REASK_GAP_DAYS,
            False,
            False,
            True,
            id="reask-at-gap",
        ),
        pytest.param(
            _snoozed(by="click", round_=FEEDBACK_ASK_MAX_ROUNDS),
            SNOOZED_AT + 10 * FEEDBACK_ASK_REASK_GAP_DAYS,
            False,
            False,
            False,
            id="exhausted-round-two",
        ),
    ],
)
def test_resolve_feedback_ask(
    state: FeedbackAskState | None,
    active_days: int,
    has_feedback: bool,
    is_guest: bool,
    expected: bool,
) -> None:
    assert (
        resolve_feedback_ask(
            state,
            active_days=active_days,
            has_feedback=has_feedback,
            is_guest=is_guest,
            today=TODAY,
        )
        is expected
    )
