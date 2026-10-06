"""Feedback-ask repository: active-day count and the atomic prompt_state transitions.

SEED-191 #8: every state change is ONE guarded ``UPDATE ... RETURNING`` on
``users.prompt_state`` (never a Python read-modify-write), so two open tabs cannot
lose updates; Postgres re-evaluates the WHERE guard after the row lock
(READ COMMITTED), which is what makes two concurrent same-day views count once.

The transitions are raw ``text()`` statements because the CASE-heavy
``jsonb_build_object`` logic was verified in exactly this shape against Postgres 18
(234-RESEARCH.md "Verified transition SQL"). Rules that keep them working:

* Every bind is CAST-typed: asyncpg cannot infer the type of an untyped parameter
  inside ``jsonb_build_object`` (IndeterminateDatatypeError, RESEARCH Pitfall 4).
  Dates travel as ISO strings (``CAST(:today AS text)``), never as ``date`` objects.
* Never bind Python ``None`` into the JSONB (it would write a JSON ``null``); every
  extracted value is wrapped in ``coalesce``.
* ``jsonb_set`` is avoided on purpose: it is strict and returns NULL (violating the
  NOT NULL column) when the new value is NULL. ``prompt_state || jsonb_build_object``
  cannot.
* Keys other than ``FEEDBACK_ASK_ID`` survive every transition because only that
  key is replaced.

Never calls session.commit(); get_async_session commits after a clean request.
"""

import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_activity import UserActivity
from app.schemas.feedback_ask import (
    FEEDBACK_ASK_ID,
    FEEDBACK_ASK_MAX_ROUNDS,
    FEEDBACK_ASK_MAX_VIEWS,
    FEEDBACK_ASK_REASK_GAP_DAYS,
    FeedbackAskState,
)

# VIEW: count at most one view per UTC day, auto-snooze on the FEEDBACK_ASK_MAX_VIEWS-th
# view, and start round 2 when a snoozed ask's re-ask gap has elapsed (the WHERE
# guarantees eligibility for that branch). Mirrors resolve_feedback_ask().
_VIEW_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:ask_id AS text),
    CASE WHEN prompt_state->CAST(:ask_id AS text)->>'status' = 'snoozed'
         THEN jsonb_build_object(
                  'round', coalesce((prompt_state->CAST(:ask_id AS text)->>'round')::int, 1) + 1,
                  'views', 1,
                  'last_view_date', CAST(:today AS text))
         ELSE coalesce(prompt_state->CAST(:ask_id AS text), '{}'::jsonb)
              || jsonb_build_object(
                  'round', coalesce((prompt_state->CAST(:ask_id AS text)->>'round')::int, 1),
                  'views', coalesce((prompt_state->CAST(:ask_id AS text)->>'views')::int, 0) + 1,
                  'last_view_date', CAST(:today AS text))
    END
    || CASE WHEN (CASE WHEN prompt_state->CAST(:ask_id AS text)->>'status' = 'snoozed' THEN 1
                       ELSE coalesce((prompt_state->CAST(:ask_id AS text)->>'views')::int, 0) + 1
                  END) >= CAST(:max_views AS int)
            THEN jsonb_build_object('status', 'snoozed',
                                    'snoozed_at_days', CAST(:active_days AS int),
                                    'snoozed_by', 'views')
            ELSE '{}'::jsonb END)
WHERE id = :uid
  AND NOT is_guest
  AND coalesce(prompt_state->CAST(:ask_id AS text)->>'last_view_date', '') <> CAST(:today AS text)
  AND ( prompt_state->CAST(:ask_id AS text)->>'status' IS NULL
     OR ( prompt_state->CAST(:ask_id AS text)->>'status' = 'snoozed'
          AND coalesce((prompt_state->CAST(:ask_id AS text)->>'round')::int, 1)
              < CAST(:max_rounds AS int)
          AND CAST(:active_days AS int)
              >= (prompt_state->CAST(:ask_id AS text)->>'snoozed_at_days')::int
                 + CAST(:gap AS int) ) )
RETURNING prompt_state->CAST(:ask_id AS text)
"""
)

# SNOOZE (explicit "Maybe later"): allowed while asking, or on the 3rd-view grace day
# (snoozed_by views and last_view_date today), where it upgrades the snooze to a click.
_SNOOZE_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:ask_id AS text),
    coalesce(prompt_state->CAST(:ask_id AS text), '{}'::jsonb)
    || jsonb_build_object('status', 'snoozed',
                          'snoozed_at_days', CAST(:active_days AS int),
                          'snoozed_by', 'click'))
WHERE id = :uid
  AND NOT is_guest
  AND ( prompt_state->CAST(:ask_id AS text)->>'status' IS NULL
     OR ( prompt_state->CAST(:ask_id AS text)->>'snoozed_by' = 'views'
          AND prompt_state->CAST(:ask_id AS text)->>'last_view_date' = CAST(:today AS text) ) )
RETURNING prompt_state->CAST(:ask_id AS text)
"""
)

# DONE ("Sure!"): from any state that is not already done, even one never viewed.
_DONE_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:ask_id AS text),
    coalesce(prompt_state->CAST(:ask_id AS text), '{}'::jsonb) || '{"status": "done"}'::jsonb)
WHERE id = :uid
  AND NOT is_guest
  AND prompt_state->CAST(:ask_id AS text)->>'status' IS DISTINCT FROM 'done'
RETURNING prompt_state->CAST(:ask_id AS text)
"""
)


async def count_active_days_before(
    session: AsyncSession, *, user_id: int, today: datetime.date
) -> int:
    """Count the user's user_activity rows dated strictly before ``today``.

    (user_id, activity_date) is unique, so the row count equals the distinct-day
    count and is served by the leading-user_id unique index. Today is excluded on
    purpose: the caller adds 1 for today, so a row the middleware wrote for today
    can never count twice.
    """
    result = await session.execute(
        select(func.count())
        .select_from(UserActivity)
        .where(UserActivity.user_id == user_id, UserActivity.activity_date < today)
    )
    return int(result.scalar_one())


async def get_state(session: AsyncSession, *, user_id: int) -> FeedbackAskState | None:
    """Return the stored ask state, or None when the user has no ask key yet."""
    result = await session.execute(
        text("SELECT prompt_state->CAST(:ask_id AS text) FROM users WHERE id = :uid"),
        {"ask_id": FEEDBACK_ASK_ID, "uid": user_id},
    )
    row = result.first()
    if row is None or row[0] is None:
        return None
    return FeedbackAskState.model_validate(row[0])


async def _run_transition(
    session: AsyncSession, statement: Any, params: dict[str, object]
) -> FeedbackAskState | None:
    """Run one guarded UPDATE ... RETURNING and validate the returned ask object.

    Returns None when no row matched (an idempotent no-op). A ValidationError on the
    returned value propagates and rolls the request back (validate on write).
    """
    result = await session.execute(statement, {"ask_id": FEEDBACK_ASK_ID, **params})
    row = result.first()
    if row is None:
        return None
    state = FeedbackAskState.model_validate(row[0])
    await session.flush()
    return state


async def apply_view(
    session: AsyncSession, *, user_id: int, today: datetime.date, active_days: int
) -> FeedbackAskState | None:
    """Record one view (at most one per UTC day); None when the guard did not match."""
    return await _run_transition(
        session,
        _VIEW_SQL,
        {
            "uid": user_id,
            "today": today.isoformat(),
            "active_days": active_days,
            "max_views": FEEDBACK_ASK_MAX_VIEWS,
            "max_rounds": FEEDBACK_ASK_MAX_ROUNDS,
            "gap": FEEDBACK_ASK_REASK_GAP_DAYS,
        },
    )


async def apply_snooze(
    session: AsyncSession, *, user_id: int, today: datetime.date, active_days: int
) -> FeedbackAskState | None:
    """Snooze by click; None when already snoozed/done (an idempotent no-op)."""
    return await _run_transition(
        session,
        _SNOOZE_SQL,
        {"uid": user_id, "today": today.isoformat(), "active_days": active_days},
    )


async def apply_done(session: AsyncSession, *, user_id: int) -> FeedbackAskState | None:
    """End the ask forever; None when it is already done."""
    return await _run_transition(session, _DONE_SQL, {"uid": user_id})
