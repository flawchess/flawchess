"""Feature-route service: fail-closed state parsing and action routing.

The route state is only ever written by feature_route_repository's guarded
single-statement UPDATEs; this module parses the stored state for the profile (failing
closed on corruption) and routes client actions. Impersonated sessions never write;
guests write like everyone (D-19).
"""

import datetime

import sentry_sdk
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import feature_route_repository, feedback_ask_repository
from app.schemas.feature_route import (
    FEATURE_ROUTE_KEY,
    FeatureRouteAction,
    FeatureRouteActionRequest,
    FeatureRouteState,
    FeatureRouteStepId,
)


class _CorruptRouteStateError(Exception):
    """The stored route state failed validation; callers fail closed (no dot)."""


def _capture_corrupt_state(user_id: int, exc: ValidationError) -> _CorruptRouteStateError:
    """Report a corrupt stored state to Sentry (constant message, id via context)."""
    sentry_sdk.set_context("feature_route", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    return _CorruptRouteStateError()


def build_feature_route_view(user: User) -> FeatureRouteState | None:
    """Parse the stored route state for the profile response. No I/O.

    Absent state is an empty route. A stored value that fails validation is captured to
    Sentry and gives None (the client then shows no dot) instead of a 500.
    """
    raw = user.prompt_state.get(FEATURE_ROUTE_KEY)
    if raw is None:
        return FeatureRouteState()
    try:
        return FeatureRouteState.model_validate(raw)
    except ValidationError as exc:
        _capture_corrupt_state(user.id, exc)
        return None


async def _count_active_days(session: AsyncSession, user_id: int, today: datetime.date) -> int:
    """Distinct UTC activity days up to and including today (D-11).

    Same today-inclusive count as profile.active_days: today always counts because the
    caller is active right now, and rows are counted strictly before today so a row the
    middleware wrote for today never counts twice.
    """
    before = await feedback_ask_repository.count_active_days_before(
        session, user_id=user_id, today=today
    )
    return before + 1


async def _transition(
    session: AsyncSession,
    action: FeatureRouteAction,
    *,
    user_id: int,
    step: FeatureRouteStepId,
    today: datetime.date,
) -> FeatureRouteState | None:
    """Route an action to its single guarded UPDATE; None means an idempotent no-op."""
    match action:
        case "done":
            return await feature_route_repository.apply_done(
                session, user_id=user_id, step=step, today=today
            )
        case "current":
            active_days = await _count_active_days(session, user_id, today)
            return await feature_route_repository.apply_current(
                session, user_id=user_id, step=step, active_days=active_days
            )
        case "skip":
            active_days = await _count_active_days(session, user_id, today)
            return await feature_route_repository.apply_skip(
                session, user_id=user_id, step=step, today=today, active_days=active_days
            )


async def apply_feature_route_action(
    session: AsyncSession,
    user: User,
    body: FeatureRouteActionRequest,
    *,
    now_utc: datetime.datetime,
    impersonated: bool,
) -> FeatureRouteState | None:
    """Apply one client action and return the resulting route state.

    Always succeeds and is idempotent (a repeat or a stale tab is a no-op that returns
    the stored state), so no 4xx reaches Sentry. Impersonated sessions get the
    read-only view. None means the stored state is corrupt (fail closed).
    """
    if impersonated:
        return build_feature_route_view(user)
    today = now_utc.date()
    try:
        state = await _transition(
            session, body.action, user_id=user.id, step=body.step, today=today
        )
        if state is None:
            # No-op: the step was already done (maybe by a concurrent tab), re-read.
            state = await feature_route_repository.get_state(session, user_id=user.id)
    except ValidationError as exc:
        # A corrupt stored state made the UPDATE's RETURNING value fail validation.
        # Fail closed like the profile path: report with context, roll back the
        # already-executed UPDATE so the invalid value is never committed.
        _capture_corrupt_state(user.id, exc)
        await session.rollback()
        return None
    return state if state is not None else FeatureRouteState()
