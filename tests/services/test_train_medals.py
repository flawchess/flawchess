"""Unit tests for app.services.train_medals.due_weeks (Phase 231). DB-free.

Every test name carries the due_weeks rule token so the VALIDATION map can select them
with pytest -k due_weeks. Each passes `start` explicitly (the production value is
MEDALS_START_WEEK = 2026-10-05, a Monday).
"""

from __future__ import annotations

import datetime

from app.services.train_medals import MEDALS_START_WEEK, due_weeks

UTC = datetime.UTC
START = datetime.date(2026, 10, 5)
SECOND = datetime.date(2026, 10, 12)
THIRD = datetime.date(2026, 10, 19)


def test_due_weeks_the_production_start_week_is_the_locked_monday() -> None:
    assert MEDALS_START_WEEK == START
    assert START.weekday() == 0


def test_due_weeks_nothing_is_due_before_the_start_week_ends() -> None:
    assert due_weeks(datetime.datetime(2026, 10, 8, 12, 0, tzinfo=UTC), set(), start=START) == []
    assert due_weeks(datetime.datetime(2026, 9, 28, 0, 0, tzinfo=UTC), set(), start=START) == []


def test_due_weeks_first_production_week_waits_for_the_grace_window() -> None:
    before = datetime.datetime(2026, 10, 12, 0, 4, 59, tzinfo=UTC)
    at = datetime.datetime(2026, 10, 12, 0, 5, 0, tzinfo=UTC)

    assert due_weeks(before, set(), start=START) == []
    assert due_weeks(at, set(), start=START) == [START]


def test_due_weeks_skips_finalized_weeks() -> None:
    now = datetime.datetime(2026, 10, 20, 12, 0, tzinfo=UTC)

    assert due_weeks(now, {START}, start=START) == [SECOND]
    assert due_weeks(now, {START, SECOND}, start=START) == []


def test_due_weeks_returns_every_open_week_ascending() -> None:
    now = datetime.datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

    assert due_weeks(now, set(), start=START) == [START, SECOND, THIRD]


def test_due_weeks_far_after_start_only_lists_unfinalized_weeks() -> None:
    now = datetime.datetime(2027, 1, 20, 9, 30, tzinfo=UTC)
    finalized = {START + datetime.timedelta(weeks=k) for k in range(0, 15) if k != 6}

    weeks = due_weeks(now, finalized, start=START)

    # 2027-01-18 is the open week (k=15), so k=0..14 are closed and only k=6 is missing.
    assert weeks == [START + datetime.timedelta(weeks=6)]
