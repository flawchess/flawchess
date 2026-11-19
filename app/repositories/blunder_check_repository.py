"""DB access for the blunder check (Phase 249).

All SQL lives here. Every query that reads a solver's windows or sessions filters by the
solver's `user_id`, which always comes from the auth dependency (IDOR guard).
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, cast

from sqlalchemy import (
    ColumnElement,
    and_,
    case,
    delete,
    exists,
    func,
    not_,
    select,
    tablesample,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from sqlalchemy.sql.expression import SQLColumnExpression

from app.models.blunder_check import (
    AnswerKind,
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.game_flaws_repository import _SEVERITY_INT
from app.repositories.query_utils import ANALYTICS_INCLUDED_PLATFORMS, apply_game_filters
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_SCORE_MIN
from app.services.facepalm_score import facepalm_expr

# The partial unique index that makes the one-open-session invariant a DB guarantee.
_OPEN_SESSION_INDEX: Final = "uq_blunder_check_sessions_user_open"
# A window judges the user's moves only, every other ply: N moves span 2N - 1 plies.
_PLIES_PER_USER_MOVE: Final = 2


@dataclass(frozen=True)
class WindowProgressRow:
    """One window's progress as the session strip needs it."""

    position: int
    outcome: WindowOutcome | None
    started_at: datetime.datetime | None
    points_scored: int
    # A caught blunder whose better move was not played yet (the window is ended but not done).
    better_move_pending: bool


@dataclass(frozen=True)
class SessionProgress:
    """An open session header plus its windows ordered by position."""

    session_id: int
    window_count: int
    windows: list[WindowProgressRow]


async def _progress_for_header(
    session: AsyncSession, *, user_id: int, session_id: int, window_count: int
) -> SessionProgress:
    """The session's windows as progress rows, ordered by position."""
    rows = (
        await session.execute(
            select(
                BlunderCheckWindow.position,
                BlunderCheckWindow.outcome,
                BlunderCheckWindow.started_at,
                BlunderCheckWindow.points_scored,
                BlunderCheckWindow.better_move_tier,
            )
            .where(
                BlunderCheckWindow.session_id == session_id,
                BlunderCheckWindow.user_id == user_id,
            )
            .order_by(BlunderCheckWindow.position)
        )
    ).all()
    windows = [
        WindowProgressRow(
            position=row.position,
            outcome=None if row.outcome is None else WindowOutcome(row.outcome),
            started_at=row.started_at,
            points_scored=row.points_scored,
            better_move_pending=(
                row.outcome == int(WindowOutcome.CAUGHT) and row.better_move_tier is None
            ),
        )
        for row in rows
    ]
    return SessionProgress(session_id=session_id, window_count=window_count, windows=windows)


async def open_session_progress(
    session: AsyncSession, *, user_id: int, today: datetime.date
) -> SessionProgress | None:
    """The user's open session with its window progress, or None when there is none.

    An open row whose window has elapsed (`expires_on <= today`) is not current: the read path
    ignores it and never writes (the compose path expires it, see `expire_stale_sessions`).
    """
    header = (
        await session.execute(
            select(BlunderCheckSession.id, BlunderCheckSession.window_count).where(
                BlunderCheckSession.user_id == user_id,
                BlunderCheckSession.status == "open",
                BlunderCheckSession.expires_on > today,
            )
        )
    ).one_or_none()
    if header is None:
        return None
    return await _progress_for_header(
        session, user_id=user_id, session_id=header.id, window_count=header.window_count
    )


async def completed_session_in_window(
    session: AsyncSession, *, user_id: int, today: datetime.date
) -> SessionProgress | None:
    """The user's newest completed session still inside its window, or None.

    Bug fix: finishing a session flips it to 'completed', so the open-session lookup stopped
    seeing it and a second Start on an already finished day composed a brand-new session. A done
    day must show its recap until the next session day starts, so compose returns this session
    instead of composing (same rule as the puzzle twin `train_repository.completed_session_in_window`).

    In-window means `expires_on > today`; `expire_stale_sessions` never touches completed rows,
    so this date predicate is the only window authority.
    """
    header = (
        await session.execute(
            select(BlunderCheckSession.id, BlunderCheckSession.window_count)
            .where(
                BlunderCheckSession.user_id == user_id,
                BlunderCheckSession.status == "completed",
                BlunderCheckSession.expires_on > today,
            )
            .order_by(BlunderCheckSession.id.desc())
            .limit(1)
        )
    ).one_or_none()
    if header is None:
        return None
    return await _progress_for_header(
        session, user_id=user_id, session_id=header.id, window_count=header.window_count
    )


async def expire_stale_sessions(
    session: AsyncSession, *, user_id: int, today: datetime.date
) -> None:
    """Close out the user's open sessions whose window has elapsed (`expires_on <= today`).

    Flips them to 'expired', then deletes their windows that were never started (A9): a blunder
    the user was never shown goes back to the pool. Windows that were shown stay stored (D-01),
    so a shown blunder is never served again (the served-set lookup reads them).
    """
    expired_ids = (
        (
            await session.execute(
                update(BlunderCheckSession)
                .where(
                    BlunderCheckSession.user_id == user_id,
                    BlunderCheckSession.status == "open",
                    BlunderCheckSession.expires_on <= today,
                )
                .values(status="expired")
                .returning(BlunderCheckSession.id)
            )
        )
        .scalars()
        .all()
    )
    if not expired_ids:
        return
    await session.execute(
        delete(BlunderCheckWindow)
        .where(
            BlunderCheckWindow.session_id.in_(expired_ids),
            BlunderCheckWindow.user_id == user_id,
            BlunderCheckWindow.started_at.is_(None),
        )
        .execution_options(synchronize_session=False)
    )


async def get_session_date(
    session: AsyncSession, *, user_id: int, session_id: int
) -> datetime.date | None:
    """The local day the user's session was composed on; None for an unknown or foreign id."""
    return (
        await session.execute(
            select(BlunderCheckSession.session_date).where(
                BlunderCheckSession.id == session_id,
                BlunderCheckSession.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Session insert (one-open race)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NewWindow:
    """One composed window, ready to insert (the plan 03 composer's output row)."""

    position: int
    game_id: int
    is_own: bool
    window_length: int
    blunder_position: int | None
    first_ply: int
    blunder_ply: int | None
    window_case: WindowCase
    mover_elo: int | None
    start_fen: str
    move_ucis: str
    lead_in_plies: int
    key_uci: str | None
    refutation_uci: str | None
    points_possible: int
    prior_uci: str | None = None


def _window_row(*, session_id: int, user_id: int, window: NewWindow) -> BlunderCheckWindow:
    """The frozen window row for a composed `NewWindow` (shared by insert and extension)."""
    return BlunderCheckWindow(
        session_id=session_id,
        position=window.position,
        user_id=user_id,
        game_id=window.game_id,
        is_own=window.is_own,
        window_length=window.window_length,
        blunder_position=window.blunder_position,
        first_ply=window.first_ply,
        blunder_ply=window.blunder_ply,
        window_case=int(window.window_case),
        mover_elo=window.mover_elo,
        start_fen=window.start_fen,
        move_ucis=window.move_ucis,
        lead_in_plies=window.lead_in_plies,
        prior_uci=window.prior_uci,
        key_uci=window.key_uci,
        refutation_uci=window.refutation_uci,
        points_possible=window.points_possible,
    )


async def insert_session(
    session: AsyncSession,
    *,
    user_id: int,
    windows: Sequence[NewWindow],
    now_utc: datetime.datetime,
    session_date: datetime.date,
    expires_on: datetime.date,
) -> int | None:
    """Insert an open session with its frozen windows; return the new id.

    `session_date` is the user's local day (`train_scheduler.local_today`) and `expires_on` the
    first local day the session is no longer current (`train_scheduler.session_window`).

    Returns None when a concurrent request already holds the user's open session (the
    partial unique index fired inside the SAVEPOINT); the caller resumes that session.
    """
    try:
        async with session.begin_nested():
            header = BlunderCheckSession(
                user_id=user_id,
                status="open",
                window_count=len(windows),
                started_at=now_utc,
                session_date=session_date,
                expires_on=expires_on,
            )
            session.add(header)
            # Surfaces uq_blunder_check_sessions_user_open here if a concurrent request won.
            await session.flush()
            for w in windows:
                session.add(_window_row(session_id=header.id, user_id=user_id, window=w))
            await session.flush()
            return header.id
    except IntegrityError as exc:
        # Only the one-open-session index is an expected race loss; any other integrity
        # failure (a CHECK, a bad FK) is a real bug and must surface.
        if _OPEN_SESSION_INDEX not in str(exc.orig):
            raise
        return None


# ---------------------------------------------------------------------------
# Candidate game picks
# ---------------------------------------------------------------------------


async def puzzle_cooled_pairs(
    session: AsyncSession, *, user_id: int, since: datetime.date
) -> list[tuple[int, int]]:
    """(game_id, ply) of every flaw served as a puzzle (SR row) to this user since `since`.

    "Served" means actually shown (owner decision on WR-01): only a row that was attempted
    (`solved_at IS NOT NULL`) counts. Composition pre-inserts every row of a puzzle session with
    `solved_at = NULL` (a status read on every Today mount does it), so without this filter a
    user who only plays blunder check would have their own flaws cooled for puzzles never shown.

    Cross-mode cooldown (Phase 251 D-16): a flaw shown in a puzzle session is ineligible for blunder
    check until `CROSS_MODE_COOLDOWN_DAYS` local days after its last serve. `since` is
    `today - CROSS_MODE_COOLDOWN_DAYS` from the caller's resolved local today, compared with the
    puzzle session's local `session_date`. The scan starts from drill_sessions (filtered on
    user_id and session_date) because drill_solves has no user index. Herring and sharp-filler
    rows carry no own flaw, and a row whose game was deleted has a NULL `game_id`.
    """
    rows = (
        await session.execute(
            select(DrillSolve.game_id, DrillSolve.ply)
            .join(DrillSession, DrillSession.id == DrillSolve.session_id)
            .where(
                DrillSession.user_id == user_id,
                DrillSession.session_date >= since,
                DrillSolve.source == DrillSource.SR_ITEM,
                DrillSolve.game_id.isnot(None),
                # WR-01: only attempted rows were shown; pre-materialised rows have NULL solved_at.
                DrillSolve.solved_at.isnot(None),
            )
            .distinct()
        )
    ).all()
    return [(int(game_id), int(ply)) for game_id, ply in rows]


def _unserved_qualifying_blunder_exists(
    game_id_col: SQLColumnExpression[int],
    user_id: int,
    *,
    flaw_owner_id: int | None = None,
    cooled_pairs: Sequence[tuple[int, int]] = (),
) -> ColumnElement[bool]:
    """EXISTS a qualifying blunder (drill facepalm score >= FACEPALM_SCORE_MIN) this user was not served yet.

    The score is the query-time expression over the stored facts with the drill lambda
    (`facepalm_expr(FACEPALM_DRILL_LAMBDA)`, 254 D-01 / D-03), not a stored column. NULL scores
    (unscored rows, opponent rows without facts) drop out by SQL semantics.

    "Served" is a window of this user on the same game whose blunder_ply is the blunder's ply
    (250 D-17). The probe uses ix_game_flaws_game_id for the flaw rows and
    ix_blunder_check_windows_user_game for the NOT EXISTS; no new index (research Q3 item 5).

    `flaw_owner_id` pins game_flaws.user_id (the game owner, redundant with the game id) when
    the caller knows it. Bug fix: without it the own-game pick had no selective predicate on
    game_flaws, so on prod the planner hashed a sequential scan of the whole table (17.8 s for
    one session start). With it the probe is a primary-key lookup per game (about 0.4 s).

    `cooled_pairs` are (game_id, ply) flaws served as puzzles inside the cross-mode cooldown
    (D-16); those flaw rows do not count as unserved here.
    """
    # correlate_except: the games table (or the TABLESAMPLE alias) sits two SELECT levels up, past
    # the flaw EXISTS, so auto-correlation would pull it into this FROM list as a cross join.
    already_served = (
        exists()
        .where(
            BlunderCheckWindow.user_id == user_id,
            BlunderCheckWindow.game_id == game_id_col,
            BlunderCheckWindow.blunder_ply == GameFlaw.ply,
        )
        .correlate_except(BlunderCheckWindow)
    )
    conditions: list[ColumnElement[bool]] = [
        GameFlaw.game_id == game_id_col,
        facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN,
        not_(already_served),
    ]
    if flaw_owner_id is not None:
        conditions.append(GameFlaw.user_id == flaw_owner_id)
    if cooled_pairs:
        conditions.append(tuple_(GameFlaw.game_id, GameFlaw.ply).not_in(list(cooled_pairs)))
    return exists().where(and_(*conditions))


async def pick_own_game_ids(
    session: AsyncSession,
    *,
    user_id: int,
    limit: int,
    exclude_ids: Sequence[int],
    require_facepalm: bool = False,
    cooled_pairs: Sequence[tuple[int, int]] = (),
) -> list[int]:
    """Random ids of the user's fully evaluated games (index scan on ix_games_user_full_evals).

    Platform is filtered at load time, not here, to keep the scan on the index. No age
    weighting: ordering by age needs the heap and defeats the index scan. `require_facepalm`
    keeps only games holding a qualifying blunder the user has not been served yet; the EXISTS
    probes ix_game_flaws_game_id per candidate game. `cooled_pairs` (flaws served as puzzles inside
    the cross-mode cooldown, D-16) never count as such a blunder.
    """
    stmt = select(Game.id).where(Game.user_id == user_id, Game.full_evals_completed_at.isnot(None))
    if exclude_ids:
        stmt = stmt.where(Game.id.notin_(exclude_ids))
    if require_facepalm:
        stmt = stmt.where(
            _unserved_qualifying_blunder_exists(
                Game.id, user_id, flaw_owner_id=user_id, cooled_pairs=cooled_pairs
            )
        )
    stmt = stmt.order_by(func.random()).limit(limit)
    return [int(i) for i in (await session.execute(stmt)).scalars().all()]


async def pick_foreign_game_ids(
    session: AsyncSession,
    *,
    user_id: int,
    raw_low: int,
    raw_high: int,
    limit: int,
    exclude_ids: Sequence[int],
    sample_percent: float,
    require_facepalm: bool = False,
) -> list[int]:
    """Ids of other users' fully evaluated games whose owner's rating at game time is in range (D-09).

    Uses TABLESAMPLE SYSTEM so the pick never scans the whole games table. Guests are
    excluded (their games never get the full pipeline) and so are the caller's own games.
    `require_facepalm` keeps only games holding a qualifying blunder the caller has not been
    served yet (the NOT EXISTS is scoped to the caller's own windows).
    Only game ids leave the repository: no usernames, emails or owner ids.
    """
    sampled = tablesample(Game.__table__, func.system(sample_percent), name="g")
    owner_rating = case(
        (sampled.c.user_color == "white", sampled.c.white_rating),
        else_=sampled.c.black_rating,
    )
    stmt = (
        select(sampled.c.id)
        .join(User, User.id == sampled.c.user_id)
        .where(
            sampled.c.user_id != user_id,
            User.is_guest.is_(False),
            sampled.c.full_evals_completed_at.isnot(None),
            sampled.c.platform.in_(ANALYTICS_INCLUDED_PLATFORMS),
            owner_rating.between(raw_low, raw_high),
        )
    )
    if exclude_ids:
        stmt = stmt.where(sampled.c.id.notin_(exclude_ids))
    if require_facepalm:
        stmt = stmt.where(_unserved_qualifying_blunder_exists(sampled.c.id, user_id))
    stmt = stmt.limit(limit)
    return [int(i) for i in (await session.execute(stmt)).scalars().all()]


# ---------------------------------------------------------------------------
# Batch loaders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateGame:
    """The per-game columns the composer needs (owner rating side resolved by user_color)."""

    game_id: int
    user_color: Literal["white", "black"]
    platform: str
    time_control_bucket: str | None
    time_control_str: str | None
    white_rating: int | None
    black_rating: int | None
    pgn: str


async def load_candidate_games(
    session: AsyncSession, game_ids: Sequence[int]
) -> list[CandidateGame]:
    """Games by id, restricted to the analytics-included platforms, ordered by id."""
    if not game_ids:
        return []
    stmt = (
        select(
            Game.id,
            Game.user_color,
            Game.platform,
            Game.time_control_bucket,
            Game.time_control_str,
            Game.white_rating,
            Game.black_rating,
            Game.pgn,
        )
        .where(Game.id.in_(game_ids), Game.platform.in_(ANALYTICS_INCLUDED_PLATFORMS))
        .order_by(Game.id)
    )
    return [
        CandidateGame(
            game_id=row[0],
            user_color=cast(Literal["white", "black"], row[1]),
            platform=row[2],
            time_control_bucket=row[3],
            time_control_str=row[4],
            white_rating=row[5],
            black_rating=row[6],
            pgn=row[7],
        )
        for row in (await session.execute(stmt)).all()
    ]


async def load_positions(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, list[GamePosition]]:
    """Per-game position rows ordered by ply, with only the columns the windowing reads."""
    by_game: dict[int, list[GamePosition]] = defaultdict(list)
    if not game_ids:
        return by_game
    stmt = (
        select(GamePosition)
        .options(
            load_only(
                GamePosition.game_id,
                GamePosition.ply,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
                GamePosition.move_san,
                GamePosition.best_move,
                GamePosition.pv,
                # The early-ply floor reads the phase (judge_game).
                GamePosition.phase,
            )
        )
        .where(GamePosition.game_id.in_(game_ids))
        .order_by(GamePosition.game_id, GamePosition.ply)
    )
    for position in (await session.execute(stmt)).scalars().all():
        by_game[position.game_id].append(position)
    return by_game


@dataclass(frozen=True)
class BlunderFlawRow:
    """A stored blunder with its facepalm score (structurally the candidates FlawLike protocol)."""

    ply: int
    severity: int
    is_miss: bool
    facepalm_score: float | None


async def load_blunder_flaws(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, list[BlunderFlawRow]]:
    """Qualifying stored blunders per game: severity blunder with drill facepalm score >= FACEPALM_SCORE_MIN.

    The score is `facepalm_expr(FACEPALM_DRILL_LAMBDA)` over the stored facts (254 D-01 / D-03),
    bound once and used both as the selected `facepalm_score` column and in the filter. The
    threshold is a plain SQL filter (250 D-05 / D-09); NULL scores drop out by SQL semantics.
    Opponent rows carry no facts, so their expression is NULL and they drop out too, but parity
    is still re-checked in the pure layer.
    """
    by_game: dict[int, list[BlunderFlawRow]] = defaultdict(list)
    if not game_ids:
        return by_game
    # One bound expression: the selected value and the filter are the same object.
    score = facepalm_expr(FACEPALM_DRILL_LAMBDA)
    stmt = (
        select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.severity,
            GameFlaw.is_miss,
            score.label("facepalm_score"),
        )
        .where(
            GameFlaw.game_id.in_(game_ids),
            GameFlaw.severity == _SEVERITY_INT["blunder"],
            score >= FACEPALM_SCORE_MIN,
        )
        .order_by(GameFlaw.game_id, GameFlaw.ply)
    )
    for row in (await session.execute(stmt)).all():
        by_game[row[0]].append(BlunderFlawRow(*row[1:]))
    return by_game


# ---------------------------------------------------------------------------
# Served sets (D-10 no-repeats)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServedSets:
    """What this solver has already been served, per game."""

    served_blunder_plies: dict[int, set[int]]
    judged_ranges: dict[int, list[tuple[int, int]]]


async def served_for_games(
    session: AsyncSession,
    *,
    user_id: int,
    game_ids: Sequence[int],
    cooled_pairs: Sequence[tuple[int, int]] = (),
) -> ServedSets:
    """Blunder plies of every window served and the judged ply ranges of every window served.

    The no-repeat rule is permanent (250 D-17 amends 249 D-10): a blunder counts as served as soon
    as a window carrying it was served, whether or not its ply was ever answered. A window that
    ended on a false alarm before the blunder was reached still burns that blunder, so the
    249 false-alarm exception is gone. The judged range of a window is (first_ply, last judged
    ply): the blunder ply for a blunder window, else the last user move of the window.

    `cooled_pairs` (flaws served as puzzles inside the cross-mode cooldown, D-16) are added to the
    served blunder plies, so the Python judge skips them like a window already served. They never
    enter `judged_ranges`: only blunder plies are cooled, not the surrounding herring runs.
    """
    served: dict[int, set[int]] = defaultdict(set)
    ranges: dict[int, list[tuple[int, int]]] = defaultdict(list)
    if not game_ids:
        return ServedSets(served_blunder_plies=served, judged_ranges=ranges)
    wanted = set(game_ids)
    for cooled_game_id, cooled_ply in cooled_pairs:
        if cooled_game_id in wanted:
            served[cooled_game_id].add(cooled_ply)
    window_stmt = select(
        BlunderCheckWindow.game_id,
        BlunderCheckWindow.first_ply,
        BlunderCheckWindow.blunder_ply,
        BlunderCheckWindow.window_length,
    ).where(BlunderCheckWindow.user_id == user_id, BlunderCheckWindow.game_id.in_(game_ids))
    for game_id, first_ply, blunder_ply, window_length in (
        await session.execute(window_stmt)
    ).all():
        if blunder_ply is not None:
            served[game_id].add(blunder_ply)
        last = (
            blunder_ply
            if blunder_ply is not None
            else first_ply + _PLIES_PER_USER_MOVE * (window_length - 1)
        )
        ranges[game_id].append((first_ply, last))
    return ServedSets(served_blunder_plies=served, judged_ranges=ranges)


# ---------------------------------------------------------------------------
# Elo source
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EloSourceRow:
    """One recent rated game of the user: what the rating-band derivation needs."""

    platform: str
    time_control_bucket: str | None
    time_control_str: str | None
    rating: int


async def recent_rated_games(
    session: AsyncSession, *, user_id: int, limit: int
) -> list[EloSourceRow]:
    """The user's most recent rated games against humans (by played_at), user-side rating present.

    250 D-14: the level behind the foreign rating band must not echo a bot's rating, so the rated
    and opponent_type predicates come from `apply_game_filters` (never hand-rolled, see
    current_strength_repository for the bot-rating echo this prevents). The default platform
    population (no flawchess / pgn practice games) applies as well.
    """
    user_rating = case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)
    stmt = select(
        Game.platform, Game.time_control_bucket, Game.time_control_str, user_rating
    ).where(Game.user_id == user_id, user_rating.isnot(None))
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=True,
        opponent_type="human",
        from_date=None,
        to_date=None,
    )
    stmt = stmt.order_by(Game.played_at.desc()).limit(limit)
    return [
        EloSourceRow(
            platform=row[0], time_control_bucket=row[1], time_control_str=row[2], rating=row[3]
        )
        for row in (await session.execute(stmt)).all()
    ]


# ---------------------------------------------------------------------------
# Drill: window lookups, prompts, answers (plan 04)
# ---------------------------------------------------------------------------


async def get_window_for_user(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    position: int,
    for_update: bool = False,
) -> tuple[BlunderCheckSession, BlunderCheckWindow] | None:
    """The caller's session and window at `position`, None for unknown or foreign ids (IDOR guard).

    `for_update` row-locks the window so two concurrent answers to the same window serialize
    (the loser then reads the winner's committed state and gets a 409).
    """
    stmt = (
        select(BlunderCheckSession, BlunderCheckWindow)
        .join(BlunderCheckWindow, BlunderCheckWindow.session_id == BlunderCheckSession.id)
        .where(
            BlunderCheckSession.id == session_id,
            BlunderCheckSession.user_id == user_id,
            BlunderCheckWindow.position == position,
        )
    )
    if for_update:
        stmt = stmt.with_for_update(of=BlunderCheckWindow)
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return None
    return row[0], row[1]


async def mark_window_started(
    session: AsyncSession, *, window_id: int, now_utc: datetime.datetime
) -> None:
    """Stamp `started_at` once; a restart keeps the original stamp."""
    await session.execute(
        update(BlunderCheckWindow)
        .where(BlunderCheckWindow.id == window_id, BlunderCheckWindow.started_at.is_(None))
        .values(started_at=now_utc)
        .execution_options(synchronize_session=False)
    )


async def insert_prompt(
    session: AsyncSession,
    *,
    window_id: int,
    move_index: int,
    ply: int,
    prompted_at: datetime.datetime,
) -> None:
    """Pre-insert the unanswered row for a prompt; an existing row keeps its original stamp."""
    await session.execute(
        pg_insert(BlunderCheckAnswer)
        .values(window_id=window_id, move_index=move_index, ply=ply, prompted_at=prompted_at)
        .on_conflict_do_nothing(index_elements=["window_id", "move_index"])
    )


async def answers_for_window(session: AsyncSession, *, window_id: int) -> list[BlunderCheckAnswer]:
    """Every answer row of the window (answered or open), ordered by move_index."""
    stmt = (
        select(BlunderCheckAnswer)
        .where(BlunderCheckAnswer.window_id == window_id)
        .order_by(BlunderCheckAnswer.move_index)
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(stmt)).scalars().all())


async def claim_answer(
    session: AsyncSession,
    *,
    window_id: int,
    move_index: int,
    answer: AnswerKind,
    result: AnswerResult,
    points_awarded: int,
    points_forfeited: int,
    client_elapsed_ms: int,
    server_elapsed_ms: int,
    answered_at: datetime.datetime,
) -> bool:
    """Claim the open prompt row: True when this call answered it, False when already answered.

    The `answered_at IS NULL` guard makes a double submit award nothing twice
    (the drill_solves claiming-UPDATE precedent).
    """
    stmt = (
        update(BlunderCheckAnswer)
        .where(
            BlunderCheckAnswer.window_id == window_id,
            BlunderCheckAnswer.move_index == move_index,
            BlunderCheckAnswer.answered_at.is_(None),
        )
        .values(
            answer=int(answer),
            result=int(result),
            points_awarded=points_awarded,
            points_forfeited=points_forfeited,
            client_elapsed_ms=client_elapsed_ms,
            server_elapsed_ms=server_elapsed_ms,
            answered_at=answered_at,
        )
        .returning(BlunderCheckAnswer.move_index)
        .execution_options(synchronize_session=False)
    )
    return (await session.execute(stmt)).first() is not None


async def apply_window_result(
    session: AsyncSession,
    *,
    window_id: int,
    points_delta: int,
    outcome: WindowOutcome | None,
    ended_at: datetime.datetime,
) -> None:
    """Add `points_delta` to the window's points in SQL and, when it ended, store the outcome."""
    values: dict[str, Any] = {
        "points_scored": BlunderCheckWindow.points_scored + points_delta,
    }
    if outcome is not None:
        values["outcome"] = int(outcome)
        values["ended_at"] = ended_at
    await session.execute(
        update(BlunderCheckWindow)
        .where(BlunderCheckWindow.id == window_id)
        .values(**values)
        .execution_options(synchronize_session=False)
    )


async def session_points(session: AsyncSession, *, session_id: int) -> int:
    """Sum of every window's points in the session."""
    total = (
        await session.execute(
            select(func.coalesce(func.sum(BlunderCheckWindow.points_scored), 0)).where(
                BlunderCheckWindow.session_id == session_id
            )
        )
    ).scalar_one()
    return int(total)


async def missed_pv_lines_at(
    session: AsyncSession, *, game_id: int | None, ply: int
) -> list[Any] | None:
    """The stored best-move PV blob at a flaw ply, None when the game or blob is gone."""
    if game_id is None:
        return None
    stmt = (
        select(GameFlaw.missed_pv_lines)
        .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def best_move_at(session: AsyncSession, *, game_id: int | None, ply: int) -> str | None:
    """The stored Stockfish best move at a ply, None when the game or the move is gone."""
    if game_id is None:
        return None
    stmt = (
        select(GamePosition.best_move)
        .where(GamePosition.game_id == game_id, GamePosition.ply == ply)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def earlier_windows_ended(session: AsyncSession, *, session_id: int, position: int) -> bool:
    """True when every window before `position` already has an outcome (window order, T-249-14)."""
    open_earlier = (
        await session.execute(
            select(func.count())
            .select_from(BlunderCheckWindow)
            .where(
                BlunderCheckWindow.session_id == session_id,
                BlunderCheckWindow.position < position,
                BlunderCheckWindow.outcome.is_(None),
            )
        )
    ).scalar_one()
    return open_earlier == 0


async def windows_for_session(
    session: AsyncSession, *, user_id: int, session_id: int
) -> list[BlunderCheckWindow]:
    """The caller's session windows ordered by position; empty for unknown or foreign ids."""
    stmt = (
        select(BlunderCheckWindow)
        .where(BlunderCheckWindow.session_id == session_id, BlunderCheckWindow.user_id == user_id)
        .order_by(BlunderCheckWindow.position)
    )
    return list((await session.execute(stmt)).scalars().all())


async def complete_session(
    session: AsyncSession, *, session_id: int, now_utc: datetime.datetime
) -> bool:
    """Mark an open session completed; True only for the call that moved it from open.

    A completed session is left untouched and reports False, so the caller (the streak credit)
    acts exactly once per session however often finish is repeated.
    """
    moved = (
        await session.execute(
            update(BlunderCheckSession)
            .where(BlunderCheckSession.id == session_id, BlunderCheckSession.status == "open")
            .values(status="completed", completed_at=now_utc)
            .returning(BlunderCheckSession.id)
            .execution_options(synchronize_session=False)
        )
    ).scalar_one_or_none()
    return moved is not None


# ---------------------------------------------------------------------------
# Resize of an open session (Phase 251 D-06)
# ---------------------------------------------------------------------------

ResizeOutcome = Literal["none", "expired", "completed", "shortened", "needs_extension"]


async def _delete_unstarted_windows(
    session: AsyncSession, *, user_id: int, session_id: int, from_position: int = 0
) -> None:
    """Delete the session's windows at `from_position` or later that were never shown.

    Only `started_at IS NULL` rows go: a shown window stays stored so its blunder is never
    served again (D-01, A9). The rows were never shown, so no outcome or points exist to lose.
    """
    await session.execute(
        delete(BlunderCheckWindow)
        .where(
            BlunderCheckWindow.session_id == session_id,
            BlunderCheckWindow.user_id == user_id,
            BlunderCheckWindow.position >= from_position,
            BlunderCheckWindow.started_at.is_(None),
        )
        .execution_options(synchronize_session=False)
    )


async def _count_windows(
    session: AsyncSession, *, user_id: int, session_id: int, ended_only: bool = False
) -> int:
    """How many windows the session holds, optionally only the ended ones (outcome set)."""
    stmt = (
        select(func.count())
        .select_from(BlunderCheckWindow)
        .where(
            BlunderCheckWindow.session_id == session_id,
            BlunderCheckWindow.user_id == user_id,
        )
    )
    if ended_only:
        stmt = stmt.where(BlunderCheckWindow.outcome.isnot(None))
    return int((await session.execute(stmt)).scalar_one())


async def resize_open_session(
    session: AsyncSession,
    *,
    user_id: int,
    today: datetime.date,
    new_size: int,
    now_utc: datetime.datetime,
) -> ResizeOutcome:
    """Apply the D-06 resize rules to the user's open, unexpired session for a new size.

    The session is locked (SELECT ... FOR UPDATE, scoped by `user_id`, never a client-supplied
    session id, T-251-15). With `ended` = windows that have an outcome:

    - `new_size == 0`: the session is marked 'expired' (the mode is not required today, A4) and
      its never-started windows are deleted; points on ended windows stay. -> "expired".
    - `0 < new_size <= ended`: never-started windows are deleted, `window_count` becomes the
      number of rows left (a shown-but-unended window stays, D-01) and the session is completed
      now via `complete_session`. -> "completed" (the caller credits the day).
    - `ended < new_size < window_count`: windows at position >= new_size (all never started,
      windows run in order) are deleted and `window_count` becomes `new_size`. -> "shortened".
    - `new_size > window_count`: nothing is written; the service composes the extra windows and
      appends them. -> "needs_extension".
    - `new_size == window_count`, or no open session: nothing to do. -> "none".

    A completed session is never found here (only `status = 'open'` rows are), so it never
    reopens. No outcome or points value is ever written to an existing window.
    """
    header = (
        await session.execute(
            select(BlunderCheckSession.id, BlunderCheckSession.window_count)
            .where(
                BlunderCheckSession.user_id == user_id,
                BlunderCheckSession.status == "open",
                BlunderCheckSession.expires_on > today,
            )
            .with_for_update()
        )
    ).one_or_none()
    if header is None:
        return "none"
    session_id, window_count = header.id, header.window_count
    if new_size == 0:
        await session.execute(
            update(BlunderCheckSession)
            .where(BlunderCheckSession.id == session_id, BlunderCheckSession.user_id == user_id)
            .values(status="expired")
            .execution_options(synchronize_session=False)
        )
        await _delete_unstarted_windows(session, user_id=user_id, session_id=session_id)
        return "expired"
    ended = await _count_windows(session, user_id=user_id, session_id=session_id, ended_only=True)
    if new_size <= ended:
        await _delete_unstarted_windows(session, user_id=user_id, session_id=session_id)
        remaining = await _count_windows(session, user_id=user_id, session_id=session_id)
        await session.execute(
            update(BlunderCheckSession)
            .where(BlunderCheckSession.id == session_id, BlunderCheckSession.user_id == user_id)
            .values(window_count=remaining)
            .execution_options(synchronize_session=False)
        )
        await complete_session(session, session_id=session_id, now_utc=now_utc)
        return "completed"
    if new_size < window_count:
        await _delete_unstarted_windows(
            session, user_id=user_id, session_id=session_id, from_position=new_size
        )
        await session.execute(
            update(BlunderCheckSession)
            .where(BlunderCheckSession.id == session_id, BlunderCheckSession.user_id == user_id)
            .values(window_count=new_size)
            .execution_options(synchronize_session=False)
        )
        return "shortened"
    if new_size > window_count:
        return "needs_extension"
    return "none"


async def append_windows(
    session: AsyncSession, *, user_id: int, session_id: int, windows: Sequence[NewWindow]
) -> None:
    """Insert extra composed windows into the user's session and raise `window_count` to match.

    The windows come from `compose_windows(start_position=<current window_count>)`, so their
    positions continue after the existing ones. `window_count` is set to the number of rows the
    session now holds, so a short extension (thin supply) leaves a consistent header. Scoped by
    `user_id`: another user's session id updates nothing.
    """
    if not windows:
        return
    for window in windows:
        session.add(_window_row(session_id=session_id, user_id=user_id, window=window))
    await session.flush()
    total = await _count_windows(session, user_id=user_id, session_id=session_id)
    await session.execute(
        update(BlunderCheckSession)
        .where(BlunderCheckSession.id == session_id, BlunderCheckSession.user_id == user_id)
        .values(window_count=total)
        .execution_options(synchronize_session=False)
    )


# ---------------------------------------------------------------------------
# Better move and solution (plan 05)
# ---------------------------------------------------------------------------


async def claim_better_move(
    session: AsyncSession,
    *,
    window_id: int,
    played_uci: str,
    tier: DrillMoveQuality,
    points: int,
    now_utc: datetime.datetime,
) -> bool:
    """Claim the one better move of a caught window: True when this call stored it.

    The `outcome = CAUGHT AND better_move_tier IS NULL` guard makes a double submit (or a
    submit on a missed/cleared/false-alarm window) award nothing (T-249-15). Points are added
    in SQL, never from a client value.
    """
    stmt = (
        update(BlunderCheckWindow)
        .where(
            BlunderCheckWindow.id == window_id,
            BlunderCheckWindow.outcome == int(WindowOutcome.CAUGHT),
            BlunderCheckWindow.better_move_tier.is_(None),
        )
        .values(
            better_move_uci=played_uci,
            better_move_tier=int(tier),
            better_move_at=now_utc,
            points_scored=BlunderCheckWindow.points_scored + points,
        )
        .returning(BlunderCheckWindow.id)
        .execution_options(synchronize_session=False)
    )
    return (await session.execute(stmt)).first() is not None


@dataclass(frozen=True)
class GameInfoRow:
    """Neutral facts about a game: nothing that identifies its owner (D-09)."""

    time_control_str: str | None
    time_control_bucket: str | None
    played_at: datetime.datetime | None
    mover_rating: int | None


async def game_info_for(session: AsyncSession, *, game_id: int) -> GameInfoRow | None:
    """Time control, date and the owner side's rating of a game, None when it no longer exists."""
    owner_rating = case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)
    row = (
        await session.execute(
            select(Game.time_control_str, Game.time_control_bucket, Game.played_at, owner_rating)
            .where(Game.id == game_id)
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        return None
    return GameInfoRow(
        time_control_str=row[0],
        time_control_bucket=row[1],
        played_at=row[2],
        mover_rating=row[3],
    )
