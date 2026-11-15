"""Feature-route repository: the atomic prompt_state transitions.

Every state change is ONE guarded ``UPDATE ... RETURNING`` on ``users.prompt_state``
(never a Python read-modify-write), so two open tabs cannot lose updates; Postgres
re-evaluates the WHERE guard after the row lock (READ COMMITTED).

The transitions are raw ``text()`` statements (same shape as feedback_ask_repository,
verified against Postgres 18). Rules that keep them working:

* Every bind is CAST-typed: asyncpg cannot infer the type of an untyped parameter
  inside ``jsonb_build_object`` (IndeterminateDatatypeError).
  Dates travel as ISO strings (``CAST(:today AS text)``), never as ``date`` objects.
* Never bind Python ``None`` into the JSONB (it would write a JSON ``null``); every
  extracted value is wrapped in ``coalesce``.
* ``jsonb_set`` is avoided on purpose: it is strict and returns NULL (violating the
  NOT NULL column) when the new value is NULL. ``prompt_state || jsonb_build_object``
  cannot.
* Only the ``FEATURE_ROUTE_KEY`` key is replaced, so other keys (``feedback_v1``)
  survive every transition.
* The ``steps`` merge is nested: ``||`` is shallow, so the existing steps object is
  merged explicitly or a second step would replace the first.
* Guest rows are written like any other row (D-19): unlike the feedback ask there is
  no guest exclusion in the guards.

Never calls session.commit(); get_async_session commits after a clean request.
"""

import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.feature_route import (
    FEATURE_ROUTE_KEY,
    FEATURE_ROUTE_SKIP_ACTIVE_DAYS,
    FeatureRouteState,
    FeatureRouteStepId,
)

# DONE: absent or skipped -> done (a later visit upgrades a skip, useful for
# measurement). with_dot records whether the step was the current one.
_DONE_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:key AS text),
    coalesce(prompt_state->CAST(:key AS text), '{}'::jsonb)
    || jsonb_build_object('steps',
         coalesce(prompt_state->CAST(:key AS text)->'steps', '{}'::jsonb)
         || jsonb_build_object(CAST(:step AS text), jsonb_build_object(
              'status', 'done',
              'date', CAST(:today AS text),
              'with_dot', coalesce(prompt_state->CAST(:key AS text)->'current'->>'step', '')
                          = CAST(:step AS text)))))
WHERE id = :uid
  AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text)->>'status'
      IS DISTINCT FROM 'done'
RETURNING prompt_state->CAST(:key AS text)
"""
)

# CURRENT: stamp the step the dot sits on with the active-day count at that moment
# (D-10, D-11). The only write per step transition: a step that is already resolved or
# already current matches no row, so a repeat keeps the original since_days.
_CURRENT_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:key AS text),
    coalesce(prompt_state->CAST(:key AS text), '{}'::jsonb)
    || jsonb_build_object('current', jsonb_build_object(
         'step', CAST(:step AS text),
         'since_days', CAST(:active_days AS int))))
WHERE id = :uid
  AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text) IS NULL
  AND coalesce(prompt_state->CAST(:key AS text)->'current'->>'step', '')
      IS DISTINCT FROM CAST(:step AS text)
RETURNING prompt_state->CAST(:key AS text)
"""
)

# SKIP: the current step, unresolved, with the dot on it for FEATURE_ROUTE_SKIP_ACTIVE_DAYS
# active days (D-10). The WHERE guard is the server-side twin of the client rule, so a
# client cannot skip early. A skipped step always had the dot (with_dot true).
_SKIP_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:key AS text),
    coalesce(prompt_state->CAST(:key AS text), '{}'::jsonb)
    || jsonb_build_object('steps',
         coalesce(prompt_state->CAST(:key AS text)->'steps', '{}'::jsonb)
         || jsonb_build_object(CAST(:step AS text), jsonb_build_object(
              'status', 'skipped',
              'date', CAST(:today AS text),
              'with_dot', true))))
WHERE id = :uid
  AND prompt_state->CAST(:key AS text)->'current'->>'step' = CAST(:step AS text)
  AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text) IS NULL
  AND CAST(:active_days AS int) >=
      CAST(prompt_state->CAST(:key AS text)->'current'->>'since_days' AS int)
      + CAST(:skip_days AS int)
RETURNING prompt_state->CAST(:key AS text)
"""
)

# CLEAR CURRENT (D-23): replace the route object with itself minus its `current` key.
# The `current IS NOT NULL` guard makes this a no-op for rows without a stamp and keeps
# a row without any feature_route key untouched (the expression would otherwise write
# `feature_route: null`). Only this one key is replaced, so `steps` and `feedback_v1`
# survive.
_CLEAR_CURRENT_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:key AS text),
    (prompt_state->CAST(:key AS text)) - 'current')  -- parens: '-' binds tighter than '->'
WHERE id = :uid
  AND prompt_state->CAST(:key AS text)->'current' IS NOT NULL
"""
)


async def get_state(session: AsyncSession, *, user_id: int) -> FeatureRouteState | None:
    """Return the stored route state, or None when the user has no route key yet."""
    result = await session.execute(
        text("SELECT prompt_state->CAST(:key AS text) FROM users WHERE id = :uid"),
        {"key": FEATURE_ROUTE_KEY, "uid": user_id},
    )
    row = result.first()
    if row is None or row[0] is None:
        return None
    return FeatureRouteState.model_validate(row[0])


async def _run_transition(
    session: AsyncSession, statement: Any, params: dict[str, object]
) -> FeatureRouteState | None:
    """Run one guarded UPDATE ... RETURNING and validate the returned route object.

    Returns None when no row matched (an idempotent no-op). A ValidationError on the
    returned value propagates to the caller, which rolls back (validate on write).
    """
    result = await session.execute(statement, {"key": FEATURE_ROUTE_KEY, **params})
    row = result.first()
    if row is None:
        return None
    state = FeatureRouteState.model_validate(row[0])
    await session.flush()
    return state


async def apply_done(
    session: AsyncSession, *, user_id: int, step: FeatureRouteStepId, today: datetime.date
) -> FeatureRouteState | None:
    """Record a step as done; None when it is already done (an idempotent no-op)."""
    return await _run_transition(
        session,
        _DONE_SQL,
        {"uid": user_id, "step": step, "today": today.isoformat()},
    )


async def apply_current(
    session: AsyncSession, *, user_id: int, step: FeatureRouteStepId, active_days: int
) -> FeatureRouteState | None:
    """Stamp a step as current; None when it is resolved or already current (a no-op)."""
    return await _run_transition(
        session,
        _CURRENT_SQL,
        {"uid": user_id, "step": step, "active_days": active_days},
    )


async def apply_skip(
    session: AsyncSession,
    *,
    user_id: int,
    step: FeatureRouteStepId,
    today: datetime.date,
    active_days: int,
) -> FeatureRouteState | None:
    """Skip the current step once it has had the dot for the skip window; else a no-op."""
    return await _run_transition(
        session,
        _SKIP_SQL,
        {
            "uid": user_id,
            "step": step,
            "today": today.isoformat(),
            "active_days": active_days,
            "skip_days": FEATURE_ROUTE_SKIP_ACTIVE_DAYS,
        },
    )


async def clear_current(session: AsyncSession, *, user_id: int) -> None:
    """Remove the user's current stamp (D-23), in the caller's transaction.

    Called when all of a user's games are deleted: a step whose target needs games must
    not keep counting active days while the account has none, and the client stamps the
    step afresh when the target unlocks, so the clock restarts. Unconditional on which
    step is current because the server holds no games-requirement data (a games-free
    step just restarts its clock). Never commits.
    """
    await session.execute(_CLEAR_CURRENT_SQL, {"key": FEATURE_ROUTE_KEY, "uid": user_id})
