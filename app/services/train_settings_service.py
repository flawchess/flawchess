"""Orchestration of PUT /train/settings (Phase 251 D-04..D-06).

Both session sizes are editable at any time and the change acts on today's open session and
today's streak within the same request. The sequence is fixed:

1. read the stored row and resolve the optional fields against it (absent keeps the stored value);
2. refuse a resolved pair that would switch both modes off (D-05, mapped to 422 by the router);
3. `upsert_settings` (settle-before-mutate against the OLD schedule, unchanged);
4. resize today's open blunder-check session when its size changed (D-06);
5. close today's open puzzle session when puzzles were switched off;
6. `apply_day_completion` for today, last, so a change that completes the day credits it once
   (the call is idempotent through `streak_credited_on`, so it is safe on every PUT).

All steps are sequential awaits on the one `AsyncSession` (CLAUDE.md: never `asyncio.gather`)
inside the caller's single transaction.
"""

from __future__ import annotations

import datetime
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import train_repository
from app.repositories.train_repository import TrainSettingsRow
from app.services.train_scheduler import BlunderCheckLevel, local_today

_BOTH_MODES_OFF_MESSAGE: Final = "At least one of puzzles and blunder check must stay on"


class TrainSettingsInvalidError(Exception):
    """The resolved settings would switch both modes off (D-05, mapped to 422).

    Expected user input, not a bug, so it is never sent to Sentry. The message is a constant;
    the sizes are not embedded (CLAUDE.md: variable data fragments Sentry grouping).
    """

    def __init__(self) -> None:
        super().__init__(_BOTH_MODES_OFF_MESSAGE)


async def apply_settings_update(
    session: AsyncSession,
    *,
    user_id: int,
    timezone: str,
    weekday_mask: int,
    puzzles_per_session: int,
    blunder_check_per_session: int | None,
    blunder_check_level: BlunderCheckLevel | None,
    reminder_enabled: bool,
    reminder_hour: int,
    reminder_intent_at: datetime.datetime | None,
    now_utc: datetime.datetime,
) -> TrainSettingsRow:
    """Persist a settings PUT and act on today's sessions and streak (D-04, D-06).

    `blunder_check_per_session` / `blunder_check_level` of None keep the stored value (the PUT
    contract: installed pre-release PWAs omit them). Raises `TrainSettingsInvalidError` when the
    resolved sizes are both 0, before anything is written.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        timezone: A validated IANA timezone string.
        weekday_mask: 7-bit scheduled-day mask, 0-127.
        puzzles_per_session: Puzzle session size, 0-50 (0 = off).
        blunder_check_per_session: Blunder-check session size, 0-30 (0 = off), or None to keep.
        blunder_check_level: Stored blunder-check level, or None to keep.
        reminder_enabled: Whether Train reminders are on.
        reminder_hour: The local hour reminders fire at.
        reminder_intent_at: The install-intent instant, or None to clear it.
        now_utc: The current UTC instant (from the `dev_now_utc` dependency).
    """
    old_row = await train_repository.get_or_create_settings(session, user_id=user_id)
    resolved_bc_size = (
        old_row.blunder_check_per_session
        if blunder_check_per_session is None
        else blunder_check_per_session
    )
    if puzzles_per_session == 0 and resolved_bc_size == 0:
        raise TrainSettingsInvalidError

    new_row = await train_repository.upsert_settings(
        session,
        user_id=user_id,
        timezone=timezone,
        weekday_mask=weekday_mask,
        puzzles_per_session=puzzles_per_session,
        blunder_check_per_session=resolved_bc_size,
        blunder_check_level=blunder_check_level,
        reminder_enabled=reminder_enabled,
        reminder_hour=reminder_hour,
        reminder_intent_at=reminder_intent_at,
        now_utc=now_utc,
    )
    # "Today" is resolved with the NEW timezone: the user is acting on the day they now live in.
    today = local_today(new_row.timezone, now_utc)
    await train_repository.apply_day_completion(
        session, user_id=user_id, day=today, now_utc=now_utc
    )
    # The day credit moves streak and shield columns, so return the row as persisted.
    refreshed = await train_repository.get_settings(session, user_id=user_id)
    assert refreshed is not None  # upsert_settings above guarantees the row exists.
    return refreshed
