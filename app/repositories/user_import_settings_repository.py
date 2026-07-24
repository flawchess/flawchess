"""Repository for user_import_settings: get / UPSERT / get-or-create.

Phase 186 Plan 01 (IMPORT-01). Implements the read/write path for the
per-user import-settings row (TC toggles + backlog game cap, D-01/D-02) that
both the settings API (GET/PATCH /users/me/import-settings) and the
forward-pass import filter (`import_service.py`) consume.

V4 Information Disclosure mitigation: every function requires `user_id` as a
keyword-only argument. Callers MUST pass the authenticated user's ID (from
the FastAPI-Users `current_active_user` dependency); never accept `user_id`
as a query/path parameter from the client. Mirrors
`app/repositories/user_rating_anchors_repository.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_import_settings import UserImportSettings

# Per-(platform, TC) backlog budget (D-01). Mirrors the DB
# `ck_user_import_settings_cap` CHECK constraint and the API's
# `ImportSettingsResponse`/`ImportSettingsUpdate` Literal (CLAUDE.md V5 rule:
# never bare int for a fixed-value-set field).
GameCap = Literal[1000, 3000, 5000]


@dataclass(frozen=True)
class ImportSettingsRow:
    """Internal dataclass for a single user_import_settings row.

    Frozen (immutable) per CLAUDE.md internal-structured-data rule. Only the
    columns this plan reads/writes are exposed here (TC toggles + cap); the
    backfill-cursor columns are reserved for Plan 02 and are not surfaced
    through this dataclass yet.
    """

    tc_bullet: bool
    tc_blitz: bool
    tc_rapid: bool
    tc_classical: bool
    game_cap: GameCap


# App-layer defaults for a brand-new user's first GET/PATCH (D-16: one code
# path for guests and registered users -- no guest-specific branch). Existing
# users at migration time get the DIFFERENT grandfathered values (D-13) via
# the migration's one-time INSERT ... SELECT, never through this constant.
DEFAULT_IMPORT_SETTINGS = ImportSettingsRow(
    tc_bullet=False,
    tc_blitz=True,
    tc_rapid=True,
    tc_classical=True,
    game_cap=1000,
)


def _import_scope_expanded(previous: ImportSettingsRow, updated: ImportSettingsRow) -> bool:
    """True when the new import settings want MORE backlog than the old ones.

    Scope expands when any TC bucket flips off->on or the cap increases --
    exactly the cases where the per-platform backfill cursor may have already
    walked past games the new scope wants (see the PATCH handler's reset
    comment). Pure preference reshuffles, narrowing, or no-op saves never
    reset progress.

    Moved here from app/routers/users.py (quick 260724-gnd) so both the PATCH
    endpoint and import_service.run_import's end-of-run scope re-check share
    ONE implementation instead of two copies drifting apart.
    """
    tc_enabled = any(
        getattr(updated, field) and not getattr(previous, field)
        for field in ("tc_bullet", "tc_blitz", "tc_rapid", "tc_classical")
    )
    return tc_enabled or updated.game_cap > previous.game_cap


def _to_row(row: UserImportSettings) -> ImportSettingsRow:
    # row.game_cap is DB CHECK-enforced to {1000, 3000, 5000} (ck_user_import_settings_cap)
    # but SQLAlchemy maps SmallInteger -> plain int; cast narrows to the Literal at the
    # ORM boundary, mirroring app/services/normalization.py's cast(Literal[...], ...) pattern.
    return ImportSettingsRow(
        tc_bullet=row.tc_bullet,
        tc_blitz=row.tc_blitz,
        tc_rapid=row.tc_rapid,
        tc_classical=row.tc_classical,
        game_cap=cast(GameCap, row.game_cap),
    )


async def get_settings(session: AsyncSession, *, user_id: int) -> ImportSettingsRow | None:
    """Return the user's settings row, or None if it does not exist yet.

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
    """
    result = await session.execute(
        select(UserImportSettings).where(UserImportSettings.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    return None if row is None else _to_row(row)


async def upsert_settings(
    session: AsyncSession,
    *,
    user_id: int,
    tc_bullet: bool,
    tc_blitz: bool,
    tc_rapid: bool,
    tc_classical: bool,
    game_cap: GameCap,
) -> ImportSettingsRow:
    """Insert or update one user's settings row.

    Uses `INSERT ... ON CONFLICT (user_id) DO UPDATE` so the operation is
    atomic and idempotent. The caller is responsible for committing the
    session (the `get_async_session` FastAPI dependency auto-commits after
    the route handler returns).

    Only the TC toggles + game_cap are written here -- the reserved
    backfill-cursor columns (chesscom_backfill_oldest_year/month,
    lichess_backfill_oldest_ms) are left untouched on conflict and default to
    NULL on insert (Plan 02 owns writing them).

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        tc_bullet / tc_blitz / tc_rapid / tc_classical: which TC buckets to import.
        game_cap: per-(platform, TC) backlog budget, one of {1000, 3000, 5000}
            (also DB-enforced via `ck_user_import_settings_cap`).
    """
    stmt = pg_insert(UserImportSettings).values(
        user_id=user_id,
        tc_bullet=tc_bullet,
        tc_blitz=tc_blitz,
        tc_rapid=tc_rapid,
        tc_classical=tc_classical,
        game_cap=game_cap,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "tc_bullet": stmt.excluded.tc_bullet,
            "tc_blitz": stmt.excluded.tc_blitz,
            "tc_rapid": stmt.excluded.tc_rapid,
            "tc_classical": stmt.excluded.tc_classical,
            "game_cap": stmt.excluded.game_cap,
        },
    )
    await session.execute(stmt)
    return ImportSettingsRow(
        tc_bullet=tc_bullet,
        tc_blitz=tc_blitz,
        tc_rapid=tc_rapid,
        tc_classical=tc_classical,
        game_cap=game_cap,
    )


async def get_or_create_settings(session: AsyncSession, *, user_id: int) -> ImportSettingsRow:
    """Return the user's settings, creating a default row on first touch (D-16).

    GET /users/me/import-settings and the import-service forward-pass filter
    both call this so a user with no settings row yet always sees a
    consistent shape (app-layer defaults) instead of a 404 or an implicit
    None. One code path for guests and registered users.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
    """
    existing = await get_settings(session, user_id=user_id)
    if existing is not None:
        return existing
    return await upsert_settings(
        session,
        user_id=user_id,
        tc_bullet=DEFAULT_IMPORT_SETTINGS.tc_bullet,
        tc_blitz=DEFAULT_IMPORT_SETTINGS.tc_blitz,
        tc_rapid=DEFAULT_IMPORT_SETTINGS.tc_rapid,
        tc_classical=DEFAULT_IMPORT_SETTINGS.tc_classical,
        game_cap=DEFAULT_IMPORT_SETTINGS.game_cap,
    )


async def get_chesscom_backfill_cursor(
    session: AsyncSession, *, user_id: int
) -> tuple[int, int] | None:
    """Return the persisted chess.com backward-walk cursor, or None.

    Phase 186 Plan 02 (IMPORT-03). The cursor is the (year, month) of the
    oldest archive month already ATTEMPTED by a previous backward walk (not
    necessarily one that yielded stored games -- 186-RESEARCH.md Pitfall 1).
    None means no backward walk has run yet for this user (or the settings
    row does not exist yet), so the walk starts at the current month.

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
    """
    result = await session.execute(
        select(
            UserImportSettings.chesscom_backfill_oldest_year,
            UserImportSettings.chesscom_backfill_oldest_month,
        ).where(UserImportSettings.user_id == user_id)
    )
    row = result.one_or_none()
    if row is None or row[0] is None or row[1] is None:
        return None
    return (row[0], row[1])


async def update_chesscom_backfill_cursor(
    session: AsyncSession, *, user_id: int, year: int, month: int
) -> None:
    """Persist the chess.com backward-walk cursor after an attempted month.

    Phase 186 Plan 02 (IMPORT-03, Pitfall 1). Called after EVERY attempted
    archive month, not just ones that yielded stored games -- the caller is
    responsible for calling this incrementally (mirrors the per-batch
    progress-persistence pattern in `import_service._flush_batch_with_progress`).
    Caller commits.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        year: Year of the oldest month now attempted.
        month: Month (1-12) of the oldest month now attempted.
    """
    await session.execute(
        update(UserImportSettings)
        .where(UserImportSettings.user_id == user_id)
        .values(chesscom_backfill_oldest_year=year, chesscom_backfill_oldest_month=month)
    )


async def get_lichess_backfill_cursor(session: AsyncSession, *, user_id: int) -> int | None:
    """Return the persisted lichess backward-walk `until` cursor (ms), or None.

    Phase 186 Plan 02 (IMPORT-03). None means no backward walk has run yet
    for this user (or the settings row does not exist yet), so the walk
    starts unbounded (most-recent pre-anchor games first).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
    """
    result = await session.execute(
        select(UserImportSettings.lichess_backfill_oldest_ms).where(
            UserImportSettings.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_lichess_backfill_cursor(
    session: AsyncSession, *, user_id: int, until_ms: int
) -> None:
    """Persist the lichess backward-walk `until` cursor after a fetched chunk.

    Phase 186 Plan 02 (IMPORT-03, Pitfall 1). Called after every fetched
    backward chunk with the oldest game's `played_at` in that chunk. Caller
    commits.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        until_ms: Unix millisecond timestamp of the oldest game fetched so far.
    """
    await session.execute(
        update(UserImportSettings)
        .where(UserImportSettings.user_id == user_id)
        .values(lichess_backfill_oldest_ms=until_ms)
    )


async def reset_backfill_cursors(session: AsyncSession, *, user_id: int) -> None:
    """NULL all three backward-walk cursor columns for a user.

    Phase 186 Plan 02 (IMPORT-03, Pitfall 4). Called by `delete_all_games` so a
    post-delete resync backfills the fresh account's full budget instead of
    resuming from a stale cursor, and by the import-settings PATCH when the
    scope expands (UAT 186: a TC turned on or the cap raised -- the old cursor
    has already walked past games the new scope wants). Deliberately leaves
    the TC toggles and game_cap PREFERENCE columns untouched -- only the
    progress cursors reset.
    Caller commits.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
    """
    await session.execute(
        update(UserImportSettings)
        .where(UserImportSettings.user_id == user_id)
        .values(
            chesscom_backfill_oldest_year=None,
            chesscom_backfill_oldest_month=None,
            lichess_backfill_oldest_ms=None,
        )
    )


__all__ = [
    "DEFAULT_IMPORT_SETTINGS",
    "GameCap",
    "ImportSettingsRow",
    "_import_scope_expanded",
    "get_chesscom_backfill_cursor",
    "get_lichess_backfill_cursor",
    "get_or_create_settings",
    "get_settings",
    "reset_backfill_cursors",
    "update_chesscom_backfill_cursor",
    "update_lichess_backfill_cursor",
    "upsert_settings",
]
