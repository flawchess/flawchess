"""Feedback-ask service: server-decided eligibility and the view/snooze/done lifecycle.

SEED-191 #1 (eligibility: non-guest, >= FEEDBACK_ASK_MIN_ACTIVE_DAYS active days, no
feedback from any source), #6 (snooze, one re-ask after +FEEDBACK_ASK_REASK_GAP_DAYS
active days, then never), #7 (a view is at most one per UTC day, the
FEEDBACK_ASK_MAX_VIEWS-th auto-snoozes), #8 (server-side state, atomic writes).

The state is only ever written by feedback_ask_repository's guarded single-statement
UPDATEs; this module decides eligibility (pure ``resolve_feedback_ask``) and routes
actions. Guests and impersonated sessions never write and never see the ask.
"""

import datetime
from typing import NamedTuple

import sentry_sdk
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import feedback_ask_repository, feedback_repository
from app.schemas.feedback_ask import (
    FEEDBACK_ASK_ID,
    FEEDBACK_ASK_MAX_ROUNDS,
    FEEDBACK_ASK_MIN_ACTIVE_DAYS,
    FEEDBACK_ASK_REASK_GAP_DAYS,
    FeedbackAskAction,
    FeedbackAskState,
    FeedbackAskView,
)

_INACTIVE = FeedbackAskView(active=False)


class FeedbackAskSnapshot(NamedTuple):
    """Profile-side result: today-inclusive active days plus the ask view."""

    active_days: int
    view: FeedbackAskView


class _CorruptAskStateError(Exception):
    """The stored ask state failed validation; callers fail closed (ask inactive)."""


def resolve_feedback_ask(
    state: FeedbackAskState | None,
    *,
    active_days: int,
    has_feedback: bool,
    is_guest: bool,
    today: datetime.date,
) -> bool:
    """Decide whether the ask is active now. Pure: no I/O, no clock.

    Mirrors the WHERE guards of the repository transitions.
    """
    if is_guest or has_feedback or active_days < FEEDBACK_ASK_MIN_ACTIVE_DAYS:
        return False
    if state is None or state.status is None:
        return True  # round 1, or round 2 in progress
    if state.status == "done":
        return False
    # Snoozed. The view that auto-snoozed the ask keeps it showing for the rest of that
    # UTC day on every surface (a snooze by click hides immediately).
    if state.snoozed_by == "views" and state.last_view_date == today:
        return True
    return (
        state.round < FEEDBACK_ASK_MAX_ROUNDS
        and state.snoozed_at_days is not None
        and active_days >= state.snoozed_at_days + FEEDBACK_ASK_REASK_GAP_DAYS
    )


def _capture_corrupt_state(user_id: int, exc: ValidationError) -> _CorruptAskStateError:
    """Report a corrupt stored state to Sentry (constant message, id via context)."""
    sentry_sdk.set_context("feedback_ask", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    return _CorruptAskStateError()


def _stored_state(user: User) -> FeedbackAskState | None:
    """Parse the user's stored ask state; raises _CorruptAskStateError when invalid."""
    raw = user.prompt_state.get(FEEDBACK_ASK_ID)
    if raw is None:
        return None
    try:
        return FeedbackAskState.model_validate(raw)
    except ValidationError as exc:
        raise _capture_corrupt_state(user.id, exc) from exc


async def _count_active_days(session: AsyncSession, user_id: int, today: datetime.date) -> int:
    """Distinct UTC activity days up to and including today.

    Today always counts because the caller is active right now (the middleware only
    writes today's row after the response); rows are counted strictly before today so
    a row written for today never counts twice.
    """
    before = await feedback_ask_repository.count_active_days_before(
        session, user_id=user_id, today=today
    )
    return before + 1


def _base_eligible(*, active_days: int, has_feedback: bool) -> bool:
    return active_days >= FEEDBACK_ASK_MIN_ACTIVE_DAYS and not has_feedback


async def build_feedback_ask_snapshot(
    session: AsyncSession, user: User, *, now_utc: datetime.datetime, impersonated: bool
) -> FeedbackAskSnapshot:
    """Compute active_days and the ask view for the profile response."""
    today = now_utc.date()
    active_days = await _count_active_days(session, user.id, today)
    # Cheap short-circuits BEFORE the feedback EXISTS query.
    if user.is_guest or impersonated or active_days < FEEDBACK_ASK_MIN_ACTIVE_DAYS:
        return FeedbackAskSnapshot(active_days, _INACTIVE)
    has_feedback = await feedback_repository.has_feedback(session, user.id)
    try:
        state = _stored_state(user)
    except _CorruptAskStateError:
        return FeedbackAskSnapshot(active_days, _INACTIVE)  # fail closed: never nag
    active = resolve_feedback_ask(
        state,
        active_days=active_days,
        has_feedback=has_feedback,
        is_guest=user.is_guest,
        today=today,
    )
    return FeedbackAskSnapshot(active_days, FeedbackAskView(active=active))


async def _transition(
    session: AsyncSession,
    action: FeedbackAskAction,
    *,
    user_id: int,
    today: datetime.date,
    active_days: int,
) -> FeedbackAskState | None:
    """Route an action to its single guarded UPDATE; None means an idempotent no-op."""
    match action:
        case "view":
            return await feedback_ask_repository.apply_view(
                session, user_id=user_id, today=today, active_days=active_days
            )
        case "snooze":
            return await feedback_ask_repository.apply_snooze(
                session, user_id=user_id, today=today, active_days=active_days
            )
        case "done":
            return await feedback_ask_repository.apply_done(session, user_id=user_id)


async def apply_feedback_ask_action(
    session: AsyncSession,
    user: User,
    action: FeedbackAskAction,
    *,
    now_utc: datetime.datetime,
    impersonated: bool,
) -> FeedbackAskView:
    """Apply one client action and return the recomputed ask view.

    Always succeeds and is idempotent: guests, impersonation, an ineligible user or a
    stale tab get a no-op and the current view, so no 4xx reaches Sentry.
    """
    if user.is_guest or impersonated:
        return _INACTIVE  # Pitfall 7: nobody answers or burns views on a user's behalf
    today = now_utc.date()
    active_days = await _count_active_days(session, user.id, today)
    has_feedback = await feedback_repository.has_feedback(session, user.id)
    # WR-02: view and snooze only run inside the eligibility rule (SEED-191 #1); a stale
    # or buggy client could otherwise write ask state for an ineligible user (e.g. a
    # click-snooze at 2 active days would push the re-ask out to 12). done stays
    # unconditional because it only ever shrinks exposure.
    if action != "done" and not _base_eligible(active_days=active_days, has_feedback=has_feedback):
        return _INACTIVE
    try:
        state = await _transition(
            session, action, user_id=user.id, today=today, active_days=active_days
        )
        if state is None:
            # No-op: a concurrent tab may have written, so re-read the stored state.
            state = await feedback_ask_repository.get_state(session, user_id=user.id)
    except ValidationError as exc:
        # WR-01: a corrupt stored state (e.g. an unknown key) made the UPDATE's RETURNING
        # value fail validation, which used to surface as a 500 on this write path. Fail
        # closed like the snapshot path: report to Sentry with context, roll back the
        # already-executed UPDATE so the invalid value is never committed, return inactive.
        _capture_corrupt_state(user.id, exc)
        await session.rollback()
        return _INACTIVE
    active = resolve_feedback_ask(
        state,
        active_days=active_days,
        has_feedback=has_feedback,
        is_guest=user.is_guest,
        today=today,
    )
    return FeedbackAskView(active=active)
