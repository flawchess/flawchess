"""ORM model for train_settings table.

One settings row per user
controlling the Train schedule: the IANA timezone string used for every
"session day" boundary computation (`app.services.train_scheduler.local_today`),
the weekday bitmask (0 = empty set = "train anytime", the identity case
for `next_scheduled_day`), and the puzzles-per-session count.

Mirrors `app/models/user_import_settings.py`'s create-on-first-touch shape
exactly: PK = `user_id`, no migration-time backfill for new users, defaults
(`app.services.train_scheduler.DEFAULT_TIMEZONE` /
`DEFAULT_WEEKDAY_MASK` / `DEFAULT_PUZZLES_PER_SESSION`) applied at the
application layer on first GET/PUT via
`app.repositories.train_repository.get_or_create_settings`.

The streak snapshot is a per-scheduled-day tick + a 0-7 depletable
streak buffer (the UI's "freezes"): `streak_count` is the number of completed
scheduled-day sessions, `shield_level` is the buffer, `streak_settled_through`
is the last judged day, and `pool_eligible_since` is the eligibility watermark
— never judge a scheduled day earlier than the date the user first had
qualifying material. A settled day is frozen
forever — `GET /train/progress` only ever walks days strictly after
`streak_settled_through`, so a later `weekday_mask`/`timezone` change can
never re-judge a day that already settled. See
`app.services.train_scheduler.tick_days` for the pure tick logic and
`app.repositories.train_repository.settle_streak_snapshot` for the single
mutation entry point (shared by `GET /train/progress` and
`PUT /train/settings`).
"""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.services.train_scheduler import (
    REMINDER_HOUR_MAX,
    REMINDER_HOUR_MIN,
    REVEAL_TOUR_STAGE_MAX,
    SHIELD_CAP,
)


class TrainSettings(Base):
    """One row per user: Train timezone, weekday schedule, session size,
    and the per-day tick machine's persisted snapshot."""

    __tablename__ = "train_settings"
    __table_args__ = (
        CheckConstraint("weekday_mask BETWEEN 0 AND 127", name="ck_train_settings_weekday_mask"),
        CheckConstraint("puzzles_per_session BETWEEN 1 AND 50", name="ck_train_settings_puzzles"),
        CheckConstraint(
            f"shield_level BETWEEN 0 AND {SHIELD_CAP}", name="ck_train_settings_shield_level"
        ),
        CheckConstraint(
            f"reminder_hour BETWEEN {REMINDER_HOUR_MIN} AND {REMINDER_HOUR_MAX}",
            name="ck_train_settings_reminder_hour",
        ),
        CheckConstraint(
            f"reveal_tour_stage BETWEEN 0 AND {REVEAL_TOUR_STAGE_MAX}",
            name="ck_train_settings_reveal_tour_stage",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    # Defaults are 127/6 — see
    # app.services.train_scheduler.DEFAULT_WEEKDAY_MASK/
    # DEFAULT_PUZZLES_PER_SESSION for the full rationale (both are also the
    # single source of truth the repository/app layer actually applies on
    # first touch; these server_defaults exist for direct-INSERT parity).
    weekday_mask: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="127")
    puzzles_per_session: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="6"
    )
    # Per-day tick snapshot. streak_count counts completed
    # scheduled-day sessions (never an in-flight/unsettled day — see
    # tick_days). shield_level is a plain SmallInteger + range CHECK (not an
    # IntEnum/TEXT+CHECK): it is a count, not a named state, matching
    # CLAUDE.md's "SMALLINT backed by ... or TEXT+CHECK" rule for a bounded
    # non-categorical integer. streak_settled_through is the last day this
    # machine has finished judging; NULL means nothing has settled yet (the
    # all-null-equivalent snapshot every pre-existing row gets from the
    # streak-snapshot migration, which is exactly what triggers a full-history
    # replay on first settlement).
    streak_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    shield_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    streak_settled_through: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # The eligibility watermark — never judge a scheduled day
    # earlier than the date the user first had qualifying (drillable)
    # material. NULL means never yet stamped (a brand-new user, or an
    # existing user with zero drill_items at migration time — see the
    # migration's module docstring). Stamped lazily, once, by
    # `app.repositories.train_repository._stamp_pool_eligibility`.
    pool_eligible_since: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # reminder_enabled/reminder_hour are
    # user-owned configuration exposed through GET/PUT /train/settings;
    # reminder_hour is a plain bounded local-hour integer (a count,
    # not a named state), so SmallInteger + range CHECK per CLAUDE.md, never
    # a native enum -- mirrors shield_level's shape exactly.
    # reminder_last_sent_on is the "already sent today" watermark,
    # structurally identical to streak_settled_through: compared against
    # train_scheduler.local_today(timezone, now_utc), and written ONLY by
    # the reminder job's claim UPDATE -- never client-writable
    # (it never appears in TrainSettingsUpdate/TrainSettingsResponse or in
    # upsert_settings' ON CONFLICT DO UPDATE set_ dict).
    # The three server_defaults below exist for direct-INSERT parity only;
    # the real defaults are train_scheduler.DEFAULT_REMINDER_ENABLED/
    # DEFAULT_REMINDER_HOUR, applied at the application layer in
    # train_repository.get_or_create_settings, same as weekday_mask/
    # puzzles_per_session.
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reminder_hour: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="18")
    reminder_last_sent_on: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # Opposite access pattern from
    # reminder_last_sent_on directly above: reminder_intent_at IS
    # client-writable and appears in BOTH TrainSettingsUpdate and
    # TrainSettingsResponse. It is stamped when the user expresses install
    # intent from the iOS install-affordance tap -- an instant, not a
    # calendar watermark, so it uses DateTime(timezone=True) rather than
    # Date (mirrors the codebase's nullable-instant convention, e.g.
    # drill_session.py, eval_jobs.py, herring_pool.py -- never a naive
    # DateTime). No backfill: every row that predates this column reads back
    # NULL, meaning "no install intent expressed yet."
    reminder_intent_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Server-side onboarding state for the Train bot steppers. Two
    # first-write-wins "explanation seen" timestamps (intro_seen_at: guess-bubble
    # intro; sr_explained_at: first-completed-session SR explanation) plus the
    # forward-only `reveal_tour_stage` counter (completed reveal-tour parts,
    # 0..REVEAL_TOUR_STAGE_MAX; it replaced an earlier walkthrough timestamp).
    # All three are Response-ONLY: the
    # closer access-pattern sibling is reminder_last_sent_on, which is likewise
    # absent from TrainSettingsUpdate. They are written ONLY by
    # POST /train/onboarding/{step} on stepper completion; an abandoned stepper
    # leaves its state untouched and replays next time. The timestamps are
    # instants, not calendar watermarks, so DateTime(timezone=True) (mirrors the
    # codebase's nullable-instant convention, never a naive DateTime). The stage
    # is a plain SmallInteger + range CHECK (a count, not a named state),
    # mirroring shield_level. No backfill for the timestamps; the stage
    # migration set stage 3 for users who had finished the old tour.
    intro_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sr_explained_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reveal_tour_stage: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


__all__ = ["TrainSettings"]
