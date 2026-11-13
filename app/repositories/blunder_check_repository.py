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

from sqlalchemy import ColumnElement, and_, case, exists, func, not_, select, tablesample, update
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
from app.models.drill_solve import DrillMoveQuality
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.game_flaws_repository import _SEVERITY_INT
from app.repositories.query_utils import ANALYTICS_INCLUDED_PLATFORMS, apply_game_filters
from app.services.blunder_check_rules import FACEPALM_SCORE_MIN

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


async def open_session_progress(session: AsyncSession, *, user_id: int) -> SessionProgress | None:
    """The user's open session with its window progress, or None when there is none."""
    header = (
        await session.execute(
            select(BlunderCheckSession.id, BlunderCheckSession.window_count).where(
                BlunderCheckSession.user_id == user_id,
                BlunderCheckSession.status == "open",
            )
        )
    ).one_or_none()
    if header is None:
        return None
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
                BlunderCheckWindow.session_id == header.id,
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
    return SessionProgress(session_id=header.id, window_count=header.window_count, windows=windows)


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


async def insert_session(
    session: AsyncSession,
    *,
    user_id: int,
    windows: Sequence[NewWindow],
    now_utc: datetime.datetime,
) -> int | None:
    """Insert an open session with its frozen windows; return the new id.

    Returns None when a concurrent request already holds the user's open session (the
    partial unique index fired inside the SAVEPOINT); the caller resumes that session.
    """
    try:
        async with session.begin_nested():
            header = BlunderCheckSession(
                user_id=user_id, status="open", window_count=len(windows), started_at=now_utc
            )
            session.add(header)
            # Surfaces uq_blunder_check_sessions_user_open here if a concurrent request won.
            await session.flush()
            for w in windows:
                session.add(
                    BlunderCheckWindow(
                        session_id=header.id,
                        position=w.position,
                        user_id=user_id,
                        game_id=w.game_id,
                        is_own=w.is_own,
                        window_length=w.window_length,
                        blunder_position=w.blunder_position,
                        first_ply=w.first_ply,
                        blunder_ply=w.blunder_ply,
                        window_case=int(w.window_case),
                        mover_elo=w.mover_elo,
                        start_fen=w.start_fen,
                        move_ucis=w.move_ucis,
                        lead_in_plies=w.lead_in_plies,
                        key_uci=w.key_uci,
                        refutation_uci=w.refutation_uci,
                        points_possible=w.points_possible,
                    )
                )
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


def _unserved_qualifying_blunder_exists(
    game_id_col: SQLColumnExpression[int], user_id: int
) -> ColumnElement[bool]:
    """EXISTS a qualifying blunder (facepalm_score >= FACEPALM_SCORE_MIN) this user was not served yet.

    "Served" is a window of this user on the same game whose blunder_ply is the blunder's ply
    (250 D-17). The probe uses ix_game_flaws_game_id for the flaw rows and
    ix_blunder_check_windows_user_game for the NOT EXISTS; no new index (research Q3 item 5).
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
    return exists().where(
        and_(
            GameFlaw.game_id == game_id_col,
            GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN,
            not_(already_served),
        )
    )


async def pick_own_game_ids(
    session: AsyncSession,
    *,
    user_id: int,
    limit: int,
    exclude_ids: Sequence[int],
    require_facepalm: bool = False,
) -> list[int]:
    """Random ids of the user's fully evaluated games (index scan on ix_games_user_full_evals).

    Platform is filtered at load time, not here, to keep the scan on the index. No age
    weighting: ordering by age needs the heap and defeats the index scan. `require_facepalm`
    keeps only games holding a qualifying blunder the user has not been served yet; the EXISTS
    probes ix_game_flaws_game_id per candidate game.
    """
    stmt = select(Game.id).where(Game.user_id == user_id, Game.full_evals_completed_at.isnot(None))
    if exclude_ids:
        stmt = stmt.where(Game.id.notin_(exclude_ids))
    if require_facepalm:
        stmt = stmt.where(_unserved_qualifying_blunder_exists(Game.id, user_id))
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
    """Qualifying stored blunders per game: severity blunder with facepalm_score >= FACEPALM_SCORE_MIN.

    The threshold is a plain SQL filter on game_flaws (250 D-05 / D-09); NULL scores drop out by
    SQL semantics. Opponent rows carry a NULL score (the fit scores user blunders only) and drop
    out too, but parity is still re-checked in the pure layer.
    """
    by_game: dict[int, list[BlunderFlawRow]] = defaultdict(list)
    if not game_ids:
        return by_game
    stmt = (
        select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.severity,
            GameFlaw.is_miss,
            GameFlaw.facepalm_score,
        )
        .where(
            GameFlaw.game_id.in_(game_ids),
            GameFlaw.severity == _SEVERITY_INT["blunder"],
            GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN,
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
    session: AsyncSession, *, user_id: int, game_ids: Sequence[int]
) -> ServedSets:
    """Blunder plies of every window served and the judged ply ranges of every window served.

    The no-repeat rule is permanent (250 D-17 amends 249 D-10): a blunder counts as served as soon
    as a window carrying it was served, whether or not its ply was ever answered. A window that
    ended on a false alarm before the blunder was reached still burns that blunder, so the
    249 false-alarm exception is gone. The judged range of a window is (first_ply, last judged
    ply): the blunder ply for a blunder window, else the last user move of the window.
    """
    served: dict[int, set[int]] = defaultdict(set)
    ranges: dict[int, list[tuple[int, int]]] = defaultdict(list)
    if not game_ids:
        return ServedSets(served_blunder_plies=served, judged_ranges=ranges)
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
) -> None:
    """Mark an open session completed; a completed session is left untouched."""
    await session.execute(
        update(BlunderCheckSession)
        .where(BlunderCheckSession.id == session_id, BlunderCheckSession.status == "open")
        .values(status="completed", completed_at=now_utc)
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
