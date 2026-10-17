"""Pure interval-ladder scheduler for Train.

No I/O, no DB, stdlib only. Every function here is a pure transform over
plain `datetime.date`/`int`/`bool` values — no SQLAlchemy, no session, no
network. Fully unit-testable in isolation; see
tests/services/test_train_scheduler.py.

Day-boundary convention (LOCKED): `local_today` is THE ONE conversion
site from a UTC instant to a user's local calendar day, via the stored IANA
timezone string on `train_settings`. Every other Train day computation
(due-date snapping, session windows, the streak tick machine) reuses this
and never re-derives `.date()` from a naive UTC datetime elsewhere.

Streak model: a per-scheduled-day tick with a 0-7 depletable buffer of
freezes (`shield_level`; `TickSnapshot`/`TickView`/`tick_days`). A completed
scheduled-day session ticks the shield/count up (capped at `SHIELD_CAP`), a
missed scheduled day drains the shield by one (floored at 0, resetting the
count when the shield empties), and a scheduled day before the user ever had
trainable material is neutral.

`apply_result`'s `fail_count` is a LIFETIME lapse counter with two park doors:
Door A (never solved + 3 lifetime lapses, `PARK_FAIL_THRESHOLD`) and Door B
(6 lifetime lapses regardless of `ever_correct`, see `LEECH_FAIL_THRESHOLD`).
Door B exists because an item that alternates solved/failed never reaches
`MASTERED` (3 *consecutive* correct solves; alternation caps the streak at 1)
and is past Door A after its first correct solve.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.drill_item import DrillStatus

# ---------------------------------------------------------------------------
# Named constants (CLAUDE.md: no magic numbers)
# ---------------------------------------------------------------------------

# streak -> day offset from the solve day. streak 0 means "the next scheduled
# session" (offset 0, i.e. as soon as possible); streak 1 -> 3 days out;
# streak 2 -> 10 days out.
LADDER_DAYS: dict[int, int] = {0: 0, 1: 3, 2: 10}

# 3 consecutive spaced-correct solves masters an item.
MASTERY_STREAK_THRESHOLD: int = 3

# Door A: 3 fails with zero ever-correct solves parks an item.
PARK_FAIL_THRESHOLD: int = 3

# Door B: 6 LIFETIME lapses parks an item regardless of
# ever_correct. The counter is never reset by a correct solve, so an item the
# user alternately solves and fails can still leave the pool. 6, not Anki's
# leech default of 8: a Train session holds far fewer slots than an Anki
# deck, so each wasted slot costs proportionally more. At 6, a genuine
# coin-flip item retires, while a 70%-recall item (expected ~2 lifetime
# lapses) almost never does.
LEECH_FAIL_THRESHOLD: int = 6

# Default timezone for a brand-new train_settings row.
DEFAULT_TIMEZONE: str = "UTC"

# All 7 weekday bits set (Monday=0..Sunday=6) — the complementary "every day
# scheduled" representation to the empty mask (see DEFAULT_WEEKDAY_MASK
# below and scheduled_days_per_week's None case for the mask==0 identity).
ALL_WEEKDAYS_MASK: int = 0b1111111

# Bug fix: the empty mask (`0`, "train anytime")
# rendered the weekday picker with every chip UNCHECKED, which read as "no
# schedule configured" rather than its actual meaning ("any day works").
# Defaulting brand-new rows to ALL_WEEKDAYS_MASK instead shows every chip
# CHECKED out of the box — the same "any day works" meaning, spelled out
# explicitly rather than via the empty-set identity case. This is a pure
# display-default change: `is_scheduled_day`/`scheduled_days_per_week` never
# distinguish "every day scheduled" from "train anytime" behaviorally.
DEFAULT_WEEKDAY_MASK: int = ALL_WEEKDAYS_MASK

# Default puzzles per session. 6 is a gentler first-touch default than 12
# (5 SR + 1 herring per compose_slots' 75/25 split at n=6).
DEFAULT_PUZZLES_PER_SESSION: int = 6

# Number of days in a week — the search bound for next_scheduled_day's
# forward scan (a full week always contains a scheduled day when the mask is
# non-zero).
_DAYS_IN_WEEK: int = 7

# The maximum shield_level a tick can ever reach (±1 symmetric drain, cap 7).
# Do NOT tune by shrinking this below 7 —
# past that point the grace-collapse problem the model exists to fix
# returns.
SHIELD_CAP: int = 7

# The number of reveal-tour parts. `reveal_tour_stage`
# counts completed parts, so a stage of REVEAL_TOUR_STAGE_MAX means the whole
# tour is done. The single source of truth for the model's CHECK; the frontend
# mirrors it as `TOUR_PART_COUNT`.
REVEAL_TOUR_STAGE_MAX: int = 3

# Default state for a never-configured user's
# reminder settings. `DEFAULT_REMINDER_HOUR` (18) is the stated
# default local hour -- the single source of truth for the model's
# CheckConstraint, get_or_create_settings' create-on-first-touch INSERT, and
# the Pydantic Field bound on TrainSettingsUpdate.reminder_hour, so none of
# the three ever drifts from the others.
DEFAULT_REMINDER_ENABLED: bool = False
DEFAULT_REMINDER_HOUR: int = 18
REMINDER_HOUR_MIN: int = 0
REMINDER_HOUR_MAX: int = 23


def local_today(tz_name: str, now_utc: datetime.datetime) -> datetime.date:
    """Convert a UTC instant to a user's local calendar day.

    THE ONE conversion site from a UTC instant to a local calendar day for
    all of Train's day-boundary math. Every other function in this module
    (and the streak tick machine) must call this rather than re-deriving
    `.date()` from a naive/aware UTC datetime elsewhere.

    Args:
        tz_name: An IANA timezone string (e.g. "America/New_York"), as
            stored on `train_settings.timezone`. An unrecognised name falls
            back to DEFAULT_TIMEZONE rather than raising, so a stale/typo'd
            stored value never crashes composition.
        now_utc: The current UTC instant.

    Returns:
        The local calendar date at `now_utc` in the given timezone.

    Sign/timezone convention matches session_window and next_scheduled_day
    (both consume a date already resolved via this function, never a raw
    UTC datetime).
    """
    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError, ValueError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    return now_utc.astimezone(zone).date()


def local_hour(tz_name: str, now_utc: datetime.datetime) -> int:
    """Convert a UTC instant to a user's local clock hour.

    The companion to `local_today` -- the ONLY place the reminder job may
    resolve a user's local hour. Identical fallback shape: an
    unrecognised `tz_name` falls back to DEFAULT_TIMEZONE rather than
    raising, so a stale/typo'd stored timezone can never crash a tick for
    every other user.

    Args:
        tz_name: An IANA timezone string (e.g. "Asia/Kathmandu"), as stored
            on `train_settings.timezone`.
        now_utc: The current UTC instant.

    Returns:
        The local clock hour (0-23) at `now_utc` in the given timezone.
    """
    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError, ValueError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    return now_utc.astimezone(zone).hour


# The end-of-local-day instant a push TTL is bounded by.
# 23:59:59 rather than "next local midnight" -- midnight is a nonexistent
# local time in a handful of midnight-DST-transition zones (Cuba,
# historically Brazil); `zoneinfo` will not raise either way, but the
# arithmetic below is only obviously correct against an existing instant.
_END_OF_DAY_HOUR = 23
_END_OF_DAY_MINUTE = 59
_END_OF_DAY_SECOND = 59


def seconds_until_end_of_local_day(tz_name: str, now_utc: datetime.datetime) -> int:
    """Seconds remaining in the user's local calendar day.

    Bounds a push message's RFC 8030 TTL by the same end-of-local-day rule
    the scheduler already claims to hold (the reminder hour gate is unbounded
    within the local day). Computed as "today at 23:59:59 local minus now",
    never "next local midnight": midnight is a nonexistent local time in a
    few zones with midnight DST transitions, so only the end-of-today form
    is obviously correct.

    Identical fallback shape to `local_today`/`local_hour`: an
    unrecognised `tz_name` falls back to DEFAULT_TIMEZONE rather than
    raising, so one stale/typo'd stored timezone can never crash a tick for
    every other user.

    No floor and no cap. A tick at 23:52 local yields roughly 480 seconds,
    and that is correct by design: a reminder that cannot be delivered
    before the day ends SHOULD expire, reproducing the old TTL-0 behavior
    only in this degenerate near-midnight case. The `max(..., 0)` below is
    insurance against a future caller passing a `now_utc` already past
    end-of-day, not a floor on the intended range.

    Args:
        tz_name: An IANA timezone string, as stored on `train_settings.timezone`.
        now_utc: The current UTC instant.

    Returns:
        Seconds from `now_utc` (converted to local time) to 23:59:59 local,
        clamped at 0.
    """
    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError, ValueError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    local_now = now_utc.astimezone(zone)
    end_of_day = local_now.replace(
        hour=_END_OF_DAY_HOUR, minute=_END_OF_DAY_MINUTE, second=_END_OF_DAY_SECOND, microsecond=0
    )
    return max(int((end_of_day - local_now).total_seconds()), 0)


def next_scheduled_day(after: datetime.date, weekday_mask: int) -> datetime.date:
    """Return the first day >= `after` whose weekday bit is set in `weekday_mask`.

    Args:
        after: The earliest acceptable date (inclusive).
        weekday_mask: A 7-bit mask, bit `date.weekday()` (Monday=0 .. Sunday=6)
            set means that weekday is scheduled. `weekday_mask == 0` is the
            empty-schedule ("train anytime") case — every day is scheduled, so
            this returns `after` unchanged (identity).

    Returns:
        The first scheduled date >= `after`.

    Cross-reference: `session_window` calls this to compute the "open
    until the next scheduled session day" window; `apply_result`
    calls this to snap a ladder-computed ideal due date onto a real session
    day.
    """
    if weekday_mask == 0:
        return after
    for offset in range(_DAYS_IN_WEEK):
        candidate = after + datetime.timedelta(days=offset)
        if weekday_mask & (1 << candidate.weekday()):
            return candidate
    # Unreachable: weekday_mask != 0 guarantees at least one bit is set within
    # any 7-day window, per the CHECK constraint bounding weekday_mask to
    # [0, 127] (7 weekday bits).
    raise ValueError(f"weekday_mask={weekday_mask!r} has no scheduled day in a 7-day window")


@dataclass(frozen=True)
class ItemState:
    """The SR-relevant fields of a `drill_items` row, as a pure value type.

    `status` is `app.models.drill_item.DrillStatus` — imported, not
    redeclared, so the enum has exactly one definition across the model and
    scheduler layers.
    """

    status: DrillStatus
    streak: int
    due_date: datetime.date
    fail_count: int
    ever_correct: bool


def apply_result(
    state: ItemState, *, correct_move: bool, today: datetime.date, weekday_mask: int
) -> ItemState:
    """Advance a drill_items row's SR state after one solve.

    Args:
        state: The item's state before this solve.
        correct_move: Whether the played move matched the puzzle's answer.
            There is deliberately NO `guess` parameter — mastery/parking is
            driven by move correctness alone. The metacognition "critical vs
            several" guess is graded and recorded separately
            (`drill_solves.correct_guess`) and can never advance or reset a
            streak; folding it in here would let scoring leak into SR
            mechanics, which the design forbids.
        today: The local session day this solve happened on (from
            `local_today`), used as the base for due-date snapping.
        weekday_mask: The user's scheduled-day bitmask, passed through to
            `next_scheduled_day` for the re-snap.

    Returns:
        The item's new state.

    Correct-move branch: `streak + 1`; at MASTERY_STREAK_THRESHOLD the item
    becomes MASTERED with `due_date` left UNTOUCHED (a mastered item is never
    re-scheduled); otherwise ACTIVE with a due date snapped via
    `next_scheduled_day(today + LADDER_DAYS[new_streak] days, weekday_mask)`.
    Either way `fail_count` is carried through UNCHANGED (it is a
    lifetime lapse count, never reset by a correct solve) and `ever_correct`
    becomes True.

    Wrong-move branch: `streak` resets to 0. `fail_count` increments
    unconditionally — the counter is monotonic non-decreasing for
    the life of the item, regardless of `ever_correct`. The park check runs
    BEFORE the re-snap and evaluates two independent doors: Door A fires when
    `not ever_correct and new_fail_count >= PARK_FAIL_THRESHOLD`
    (never-solved); Door B fires when
    `new_fail_count >= LEECH_FAIL_THRESHOLD` regardless of `ever_correct`
    (the leech door). Either door parks the item with `due_date`
    left UNTOUCHED and `ever_correct` propagated from the incoming state (not
    hardcoded) — Door B can fire with `ever_correct` True, so hardcoding
    `False` would silently rewrite a solved item's history. Otherwise the
    item stays ACTIVE with `due_date = next_scheduled_day(today,
    weekday_mask)`.

    Cross-reference: `next_scheduled_day` is the sibling this function must
    agree with on every due-date snap; `session_window` is the sibling for
    the *session's* (not the item's) open-window boundary.
    """
    if correct_move:
        new_streak = state.streak + 1
        if new_streak >= MASTERY_STREAK_THRESHOLD:
            return ItemState(
                status=DrillStatus.MASTERED,
                streak=new_streak,
                due_date=state.due_date,
                # Bug fix: this used to hardcode 0, which zeroed the
                # lifetime lapse counter on every correct solve. That made
                # Door B unreachable for any item ever solved once, since the
                # counter could never climb back to a park threshold.
                fail_count=state.fail_count,
                ever_correct=True,
            )
        ideal_due = today + datetime.timedelta(days=LADDER_DAYS[new_streak])
        return ItemState(
            status=DrillStatus.ACTIVE,
            streak=new_streak,
            due_date=next_scheduled_day(ideal_due, weekday_mask),
            # Bug fix: see the MASTERED branch above — carry the
            # lifetime lapse count through instead of zeroing it.
            fail_count=state.fail_count,
            ever_correct=True,
        )

    # The increment is unconditional — fail_count is a lifetime
    # lapse counter, not one gated on ever_correct being False.
    new_fail_count = state.fail_count + 1
    door_a_never_solved = not state.ever_correct and new_fail_count >= PARK_FAIL_THRESHOLD
    door_b_leech = new_fail_count >= LEECH_FAIL_THRESHOLD
    if door_a_never_solved or door_b_leech:
        return ItemState(
            status=DrillStatus.PARKED,
            streak=0,
            due_date=state.due_date,
            fail_count=new_fail_count,
            # Silent-corruption trap: this used to hardcode False,
            # which was safe only because the sole caller path (Door A) had
            # already proven ever_correct false. Door B can now fire with
            # ever_correct True, so the flag must be propagated from the
            # incoming state or a leech park would silently rewrite a solved
            # item's history to "never solved".
            ever_correct=state.ever_correct,
        )
    return ItemState(
        status=DrillStatus.ACTIVE,
        streak=0,
        due_date=next_scheduled_day(today, weekday_mask),
        fail_count=new_fail_count,
        ever_correct=state.ever_correct,
    )


def session_window(session_date: datetime.date, weekday_mask: int) -> datetime.date:
    """A session stays open until the NEXT scheduled session day starts.

    Args:
        session_date: The local date the session was composed on.
        weekday_mask: The user's scheduled-day bitmask.

    Returns:
        The first scheduled day strictly after `session_date` — the moment
        the session expires.

    With every day scheduled (either the empty mask `0`, or the default
    `ALL_WEEKDAYS_MASK`), the window collapses to "end of the same local day":
    `session_date + 1 day`, NOT a multi-day grace window as under a sparse mask
    (e.g. Tue/Fri).
    Cross-reference: shares its forward-scan logic with `next_scheduled_day`,
    which this function calls directly rather than re-implementing the scan.
    """
    day_after = session_date + datetime.timedelta(days=1)
    return next_scheduled_day(day_after, weekday_mask)


def is_session_expired(expires_on: datetime.date, today: datetime.date) -> bool:
    """Whether a `drill_sessions` row has expired.

    Args:
        expires_on: The session's `expires_on` date, from `session_window`.
        today: The local date to check against (from `local_today`).

    Returns:
        True when `today >= expires_on` — the boundary is INCLUSIVE on the
        expiry date: the arrival of the next scheduled day ends the window,
        it does not merely start counting down.

    Cross-reference: `expires_on` must always be a value previously produced
    by `session_window`, so this predicate and that function agree on what
    "expired" means. The tick machine reuses this SAME primitive
    (via `session_window`) as its elapsed-scheduled-day boundary — never a
    bare `day < today` comparison, which is wrong under a sparse mask.
    """
    return today >= expires_on


def week_start(d: datetime.date) -> datetime.date:
    """Return the Monday of the Mon-Sun week containing `d`.

    Uses `date.weekday()` (Monday=0..Sunday=6) — the IDENTICAL convention
    `next_scheduled_day` uses for `weekday_mask` bits, so week boundaries and
    the schedule bitmask never disagree.

    This bucketing is purely a DISPLAY concern (the "This
    week: N of M sessions" hint's `current_week_completed`) — it is fully
    decoupled from settlement. Nothing in `tick_days`/`_judge_one_day` reads
    week boundaries; the tick machine walks individual scheduled days.
    """
    return d - datetime.timedelta(days=d.weekday())


def is_scheduled_day(day: datetime.date, weekday_mask: int) -> bool:
    """True when `day`'s weekday bit is set, or `weekday_mask == 0` ("train
    anytime" — every day is scheduled).

    Shared by every scheduled-day check: one bit-test, every caller.
    """
    return weekday_mask == 0 or bool(weekday_mask & (1 << day.weekday()))


def scheduled_days_per_week(weekday_mask: int) -> int | None:
    """The count of scheduled days per week — a plain popcount, no gating.

    Returns `None` at `weekday_mask == 0` ("train anytime" has no
    denominator to show); otherwise `weekday_mask.bit_count()`. No
    special-casing: this is the honest count of scheduled days, including 7;
    nothing gates on it.
    """
    if weekday_mask == 0:
        return None
    return weekday_mask.bit_count()


# ---------------------------------------------------------------------------
# Per-scheduled-day tick + depletable shield (the freezes shown in the UI).
#
# A settled day is frozen FOREVER once judged: tick_days only ever walks
# days strictly after `snapshot.settled_through`, so a later weekday_mask or
# timezone change can never re-judge a day that already settled.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TickSnapshot:
    """The persisted per-day tick snapshot — exactly what lives on
    `train_settings` (`streak_count`, `shield_level`, `streak_settled_through`).
    """

    streak_count: int
    shield_level: int
    settled_through: datetime.date | None


@dataclass(frozen=True)
class TickView:
    """The full result of one `tick_days` call.

    `settled` is the (possibly advanced) snapshot to persist when `changed`
    is True. Deliberately carries NO display-overlay field: under the eager
    write, a completed session's shield/count update the SAME moment the user
    sees them, so there is no gap between "the user should see progress"
    and "the state is settled." `streak_reset_notice` is derived from the
    RESULTING state (not from "did this call settle the reset"), so it
    survives a page reload.
    """

    settled: TickSnapshot
    current_week_completed: int
    streak_reset_notice: bool
    changed: bool


#: The four-value discriminant `_judge_one_day` resolves per scheduled day.
#: A `(fulfilled, eligible)` boolean pair cannot express this: it encodes one
#: impossible combination (`fulfilled=True, eligible=False`) and has no way
#: to say "credit the shield without moving the count or the boundary" —
#: exactly what the off-day/late-completion callers need.
DayOutcome = Literal["fulfilled", "missed", "neutral", "credit_only"]


def _judge_one_day(
    snapshot: TickSnapshot, *, day: datetime.date, outcome: DayOutcome
) -> TickSnapshot:
    """Advance the snapshot by exactly one scheduled day. THE ONLY place in
    `app/` where shield/count arithmetic happens — every caller (the lazy
    `tick_days` walk here, and the eager session-completion tick in
    train_repository) goes through this
    single function so the two paths structurally cannot diverge.

    Args:
        snapshot: The state before this day is judged.
        day: The scheduled day being judged. Accepted for all four outcomes;
            IGNORED by `credit_only` (that day is either unscheduled or
            already frozen — the boundary must not move for either).
        outcome:
            - `"neutral"`: the day is before the user ever had trainable
              material. Advances `settled_through` only.
            - `"fulfilled"`: a completed session on this scheduled day.
              Advances `streak_count` (+1), `shield_level` (+1, capped at
              `SHIELD_CAP`), and `settled_through`.
            - `"missed"`: no completed session on this scheduled day.
              `shield_level` drops by 1 (floored at 0); `streak_count`
              resets to 0 exactly when the shield reaches 0, otherwise stays
              frozen. Advances `settled_through`.
            - `"credit_only"`: an ad-hoc off-day completion or a late
              completion of an already-frozen day. Raises `shield_level`
              only (same cap), leaving `streak_count` AND `settled_through`
              untouched.

    Returns:
        The advanced `TickSnapshot`.
    """
    if outcome == "neutral":
        return TickSnapshot(
            streak_count=snapshot.streak_count,
            shield_level=snapshot.shield_level,
            settled_through=day,
        )
    if outcome == "missed":
        new_shield = max(snapshot.shield_level - 1, 0)
        new_count = 0 if new_shield == 0 else snapshot.streak_count
        return TickSnapshot(streak_count=new_count, shield_level=new_shield, settled_through=day)

    # "fulfilled" and "credit_only" share this ONE shield-credit expression —
    # the single place in the whole app/ tree the SHIELD_CAP clamp bounds an
    # incremented shield (the eager-tick path calls this function
    # instead of re-deriving the clamp; a divergence gate greps for exactly
    # one occurrence).
    credited = TickSnapshot(
        streak_count=snapshot.streak_count,
        shield_level=min(snapshot.shield_level + 1, SHIELD_CAP),
        settled_through=snapshot.settled_through,
    )
    if outcome == "credit_only":
        return credited
    return TickSnapshot(
        streak_count=credited.streak_count + 1,
        shield_level=credited.shield_level,
        settled_through=day,
    )


def tick_days(
    snapshot: TickSnapshot,
    completed_session_dates: Sequence[datetime.date],
    *,
    weekday_mask: int,
    today: datetime.date,
    pool_eligible_since: datetime.date | None,
) -> TickView:
    """Advance the tick snapshot over every scheduled day whose window has
    closed.

    Args:
        snapshot: The persisted `TickSnapshot` before this call (the
            all-zero/all-null `TickSnapshot(0, 0, None)` for a brand-new
            row — this is what triggers a full-history replay on the first
            call).
        completed_session_dates: Every `drill_sessions.session_date` with
            `status='completed'` for this user (already tz-resolved plain
            local dates, never re-converted). Order-insensitive.
        weekday_mask: The user's CURRENT scheduled-day bitmask. Only ever
            applied to days strictly after `snapshot.settled_through` (a
            settled day is frozen forever) and to newly-walked days.
        today: The local calendar day (from `local_today`).
        pool_eligible_since: The eligibility watermark. `None` means
            the user has never had qualifying material — every day judged
            (if any) resolves NEUTRAL. A scheduled day strictly before this
            watermark is also NEUTRAL; on/after it, the day is judged
            fulfilled/missed normally.

    Returns:
        A `TickView` with the advanced (or unchanged) snapshot, the
        display-only current-week count, and the reset notice.

    The elapsed-day boundary is `is_session_expired(session_window(day,
    weekday_mask), today)` — NEVER a bare `day < today` comparison. Under a
    sparse mask this is a real generalization (a Monday scheduled day under
    a Mon/Wed/Fri mask is not judged on Tuesday, only from Wednesday); under
    a dense mask (`weekday_mask in (0, ALL_WEEKDAYS_MASK)`) `session_window`
    collapses to `day + 1`, so this is identical to the naive boundary for
    the default user — a strict superset of correctness, not a behavior
    change for the common case.

    A settled day is frozen forever: this walk only ever starts strictly
    after `snapshot.settled_through`, so a later `weekday_mask` or timezone
    change can never re-judge a day that already settled.
    """
    completed_set = set(completed_session_dates)
    if snapshot.settled_through is not None:
        start = next_scheduled_day(
            snapshot.settled_through + datetime.timedelta(days=1), weekday_mask
        )
    else:
        start = next_scheduled_day(pool_eligible_since or today, weekday_mask)

    settled = snapshot
    day = start
    while is_session_expired(session_window(day, weekday_mask), today):
        eligible = pool_eligible_since is not None and day >= pool_eligible_since
        outcome: DayOutcome
        if not eligible:
            outcome = "neutral"
        elif day in completed_set:
            outcome = "fulfilled"
        else:
            outcome = "missed"
        settled = _judge_one_day(settled, day=day, outcome=outcome)
        day = next_scheduled_day(day + datetime.timedelta(days=1), weekday_mask)

    changed = settled != snapshot

    current_week_start = week_start(today)
    current_week_completed = sum(
        1 for d in completed_session_dates if week_start(d) == current_week_start
    )

    streak_reset_notice = (
        settled.shield_level == 0 and settled.streak_count == 0 and len(completed_session_dates) > 0
    )

    return TickView(
        settled=settled,
        current_week_completed=current_week_completed,
        streak_reset_notice=streak_reset_notice,
        changed=changed,
    )


__all__ = [
    "ALL_WEEKDAYS_MASK",
    "DEFAULT_PUZZLES_PER_SESSION",
    "DEFAULT_REMINDER_ENABLED",
    "DEFAULT_REMINDER_HOUR",
    "DEFAULT_TIMEZONE",
    "DEFAULT_WEEKDAY_MASK",
    "LADDER_DAYS",
    "LEECH_FAIL_THRESHOLD",
    "MASTERY_STREAK_THRESHOLD",
    "PARK_FAIL_THRESHOLD",
    "REMINDER_HOUR_MAX",
    "REMINDER_HOUR_MIN",
    "SHIELD_CAP",
    "DayOutcome",
    "ItemState",
    "TickSnapshot",
    "TickView",
    "apply_result",
    "is_scheduled_day",
    "is_session_expired",
    "local_hour",
    "local_today",
    "next_scheduled_day",
    "scheduled_days_per_week",
    "seconds_until_end_of_local_day",
    "session_window",
    "tick_days",
    "week_start",
]
