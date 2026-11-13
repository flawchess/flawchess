"""Blunder-check router (Phase 249).

Beta-gated (D-01): every route depends on `current_beta_user`, so the API itself refuses
non-beta users with 403, not only the hidden frontend tab. Every handler scopes strictly
by the authenticated user's id, never a client-supplied id (IDOR guard).

Time-dependent handlers take "now" from the `dev_now_utc` dependency (`NowUtc`), never
`datetime.now()` inline.
"""

from __future__ import annotations

import datetime
from collections.abc import Awaitable, Sequence
from typing import Annotated, Final, TypeVar, cast

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dev_clock import dev_now_utc
from app.models.blunder_check import WindowOutcome
from app.models.user import User
from app.repositories import blunder_check_repository
from app.repositories.blunder_check_repository import GameInfoRow, SessionProgress
from app.schemas.blunder_check import (
    AnsweredMove,
    AnswerRequest,
    AnswerResponse,
    BetterMoveRequest,
    BetterMoveResponse,
    BetterMoveTask,
    BlunderCheckSessionResponse,
    BlunderSolution,
    FalseAlarmSolution,
    GameInfo,
    HerringSolution,
    Prompt,
    SessionResultResponse,
    TimeControlBucketWire,
    WindowOutcomeWire,
    WindowProgress,
    WindowResultItem,
    WindowSolutionResponse,
    WindowStartResponse,
    WindowState,
)
from app.schemas.train import ServerGradedMove
from app.services import blunder_check_service
from app.services.blunder_check_grading import MOVE_TIMER_SECONDS
from app.users import current_active_user

router = APIRouter(prefix="/blunder-check", tags=["blunder-check"])

#: The current UTC instant, dev-clock-shiftable. Real clock outside development.
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]

# blunder_check_sessions.id is int4; a larger session_id would raise in asyncpg and reach
# Sentry as a 500, so a Path bound turns it into a 422 before any SQL runs.
_SESSION_ID_MAX: Final = 2**31 - 1
# blunder_check_windows.position is SmallInteger; same reasoning as _SESSION_ID_MAX.
_WINDOW_POSITION_MAX: Final = 2**15 - 1

SessionIdPath = Annotated[int, Path(ge=0, le=_SESSION_ID_MAX)]
PositionPath = Annotated[int, Path(ge=0, le=_WINDOW_POSITION_MAX)]

_NOT_FOUND_DETAIL: Final = "Not found"
_ILLEGAL_MOVE_DETAIL: Final = "Illegal move"
_T = TypeVar("_T")

_OUTCOME_WIRE: Final[dict[WindowOutcome, WindowOutcomeWire]] = {
    WindowOutcome.CLEARED: "cleared",
    WindowOutcome.CAUGHT: "caught",
    WindowOutcome.MISSED: "missed",
    WindowOutcome.FALSE_ALARM: "false_alarm",
}


async def current_beta_user(user: Annotated[User, Depends(current_active_user)]) -> User:
    """Authenticated user with beta access, else 403 (D-01: the API refuses too)."""
    if not user.beta_enabled:
        raise HTTPException(status_code=403, detail="Not available")
    return user


BetaUser = Annotated[User, Depends(current_beta_user)]


def _outcome_wire(outcome: WindowOutcome | None) -> WindowOutcomeWire | None:
    return None if outcome is None else _OUTCOME_WIRE[outcome]


def _window_state(row: blunder_check_repository.WindowProgressRow) -> WindowState:
    if row.outcome is not None:
        return "ended"
    return "active" if row.started_at is not None else "pending"


def _pending_better_move_position(
    windows: Sequence[blunder_check_repository.WindowProgressRow],
) -> int | None:
    """The latest started window, when it is a caught blunder still waiting for its better move.

    Bug fix (Phase 249 review): a reload during the better-move step skipped to the next window,
    because the caught window already had an outcome, and its better-move points could never be
    earned. Such a window stays the session's current one until the better move is played.
    """
    started = [row for row in windows if row.started_at is not None]
    if not started:
        return None
    latest = max(started, key=lambda row: row.position)
    return latest.position if latest.better_move_pending else None


def _session_response(progress: SessionProgress) -> BlunderCheckSessionResponse:
    windows = [
        WindowProgress(
            position=row.position,
            state=_window_state(row),
            outcome=_outcome_wire(row.outcome),
            points_scored=row.points_scored,
        )
        for row in progress.windows
    ]
    open_positions = [row.position for row in progress.windows if row.outcome is None]
    resume_position = _pending_better_move_position(progress.windows)
    if resume_position is not None:
        open_positions.append(resume_position)
    return BlunderCheckSessionResponse(
        session_id=progress.session_id,
        window_count=progress.window_count,
        current_position=min(open_positions) if open_positions else None,
        session_points=sum(row.points_scored for row in progress.windows),
        windows=windows,
    )


@router.post("/sessions", response_model=BlunderCheckSessionResponse)
async def start_session(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
    now_utc: NowUtc,
) -> BlunderCheckSessionResponse:
    """Start a blunder-check session, or resume the open one (idempotent)."""
    try:
        progress = await blunder_check_service.compose_or_resume(
            session, user_id=user.id, now_utc=now_utc
        )
        if progress is None:
            raise HTTPException(status_code=409, detail="No blunder-check sequences available")
        await session.commit()
    except HTTPException:
        # Expected "no supply" outcome: not a bug, so not captured.
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("blunder_check", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
    return _session_response(progress)


@router.get("/sessions/open", response_model=BlunderCheckSessionResponse | None)
async def get_open_session(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
) -> BlunderCheckSessionResponse | None:
    """The caller's open blunder-check session with window progress, or null."""
    try:
        progress = await blunder_check_repository.open_session_progress(session, user_id=user.id)
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("blunder_check", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
    return None if progress is None else _session_response(progress)


# ---------------------------------------------------------------------------
# Drill: window start and answers (plan 04)
# ---------------------------------------------------------------------------


async def _guarded(
    session: AsyncSession,
    call: Awaitable[_T],
    *,
    user_id: int,
    session_id: int,
    position: int | None = None,
) -> _T:
    """Run a service call: commit on success, map domain errors, capture anything else.

    A 404 or 409 is an expected outcome (rolled back, never sent to Sentry); any other
    exception is a bug and is captured once with ids as context (not in the message).
    """
    try:
        result = await call
        await session.commit()
        return result
    except blunder_check_service.BlunderCheckNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL) from None
    except blunder_check_service.BlunderCheckConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=exc.reason) from None
    except blunder_check_service.BlunderCheckIllegalMoveError:
        await session.rollback()
        raise HTTPException(status_code=422, detail=_ILLEGAL_MOVE_DETAIL) from None
    except Exception:
        await session.rollback()
        sentry_sdk.set_context(
            "blunder_check",
            {"user_id": str(user_id), "session_id": str(session_id), "position": str(position)},
        )
        sentry_sdk.capture_exception()
        raise


def _prompt_schema(prompt: blunder_check_service.PromptData) -> Prompt:
    return Prompt(move_index=prompt.move_index, move_uci=prompt.move_uci)


def _start_response(start: blunder_check_service.WindowStart) -> WindowStartResponse:
    return WindowStartResponse(
        position=start.position,
        start_fen=start.start_fen,
        orientation=start.orientation,
        lead_in_ucis=start.lead_in_ucis,
        answered=[
            AnsweredMove(
                move_index=move.move_index,
                move_uci=move.move_uci,
                reply_uci=move.reply_uci,
                result=move.result,
                points_awarded=move.points_awarded,
                points_forfeited=move.points_forfeited,
            )
            for move in start.answered
        ],
        prompt=_prompt_schema(start.prompt),
        timer_remaining_ms=start.timer_remaining_ms,
        move_timer_seconds=MOVE_TIMER_SECONDS,
        window_points=start.window_points,
        session_points=start.session_points,
        better_move=_better_move_schema(start.better_move),
    )


def _better_move_schema(task: blunder_check_service.BetterMoveData | None) -> BetterMoveTask | None:
    if task is None:
        return None
    return BetterMoveTask(
        fen=task.fen,
        key_uci=task.key_uci,
        server_graded_moves=[
            ServerGradedMove(uci=move.uci, tier=move.tier) for move in task.server_graded_moves
        ],
    )


def _answer_response(outcome: blunder_check_service.AnswerOutcome) -> AnswerResponse:
    return AnswerResponse(
        move_index=outcome.move_index,
        result=outcome.result,
        points_awarded=outcome.points_awarded,
        points_forfeited=outcome.points_forfeited,
        window_points=outcome.window_points,
        session_points=outcome.session_points,
        window_ended=outcome.window_ended,
        outcome=outcome.outcome,
        reply_uci=outcome.reply_uci,
        next_prompt=None if outcome.next_prompt is None else _prompt_schema(outcome.next_prompt),
        timer_remaining_ms=outcome.timer_remaining_ms,
        better_move=_better_move_schema(outcome.better_move),
    )


@router.post("/sessions/{session_id}/windows/{position}/start", response_model=WindowStartResponse)
async def start_window(
    session_id: SessionIdPath,
    position: PositionPath,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
    now_utc: NowUtc,
) -> WindowStartResponse:
    """Start (or reload) a window: the lead-in, answered moves and the single open prompt."""
    start = await _guarded(
        session,
        blunder_check_service.start_window(
            session, user_id=user.id, session_id=session_id, position=position, now_utc=now_utc
        ),
        user_id=user.id,
        session_id=session_id,
        position=position,
    )
    return _start_response(start)


@router.post("/sessions/{session_id}/windows/{position}/answers", response_model=AnswerResponse)
async def answer_prompt(
    session_id: SessionIdPath,
    position: PositionPath,
    body: AnswerRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
    now_utc: NowUtc,
) -> AnswerResponse:
    """Answer the open prompt; the server grades it and reveals only what the grade allows."""
    outcome = await _guarded(
        session,
        blunder_check_service.answer_prompt(
            session,
            user_id=user.id,
            session_id=session_id,
            position=position,
            move_index=body.move_index,
            answer=body.answer,
            client_elapsed_ms=body.client_elapsed_ms,
            now_utc=now_utc,
        ),
        user_id=user.id,
        session_id=session_id,
        position=position,
    )
    return _answer_response(outcome)


@router.post("/sessions/{session_id}/finish", response_model=SessionResultResponse)
async def finish_session(
    session_id: SessionIdPath,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
    now_utc: NowUtc,
) -> SessionResultResponse:
    """Finish the session once every window ended: points, points possible and Score %."""
    result = await _guarded(
        session,
        blunder_check_service.finish_session(
            session, user_id=user.id, session_id=session_id, now_utc=now_utc
        ),
        user_id=user.id,
        session_id=session_id,
    )
    return SessionResultResponse(
        session_id=result.session_id,
        session_points=result.session_points,
        points_possible=result.points_possible,
        score_pct=result.score_pct,
        windows=[
            WindowResultItem(
                position=window.position,
                outcome=window.outcome,
                points_scored=window.points_scored,
                points_possible=window.points_possible,
            )
            for window in result.windows
        ],
    )


# ---------------------------------------------------------------------------
# Better move and solution (plan 05)
# ---------------------------------------------------------------------------


def _game_info_schema(info: GameInfoRow | None) -> GameInfo | None:
    if info is None:
        return None
    return GameInfo(
        time_control_str=info.time_control_str,
        time_control_bucket=cast(TimeControlBucketWire | None, info.time_control_bucket),
        played_at=info.played_at,
        mover_rating=info.mover_rating,
    )


def _blunder_solution_schema(data: blunder_check_service.BlunderSolutionData) -> BlunderSolution:
    return BlunderSolution(
        kind="blunder",
        outcome=data.outcome,
        is_own=data.is_own,
        window_case=data.window_case,
        game_id=data.game_id,
        analysis_ply=data.analysis_ply,
        fen=data.fen,
        blunder_uci=data.blunder_uci,
        key_uci=data.key_uci,
        better_move_uci=data.better_move_uci,
        better_move_tier=data.better_move_tier,
        server_graded_moves=[
            ServerGradedMove(uci=move.uci, tier=move.tier) for move in data.server_graded_moves
        ],
        game_info=_game_info_schema(data.game_info),
        window_points=data.window_points,
        safe_points=data.safe_points,
        blunder_points=data.blunder_points,
        better_move_points=data.better_move_points,
    )


def _solution_response(
    data: blunder_check_service.SolutionData,
) -> BlunderSolution | HerringSolution | FalseAlarmSolution:
    """Map the service's per-outcome data to the matching member of the discriminated union."""
    if isinstance(data, blunder_check_service.FalseAlarmSolutionData):
        return FalseAlarmSolution(
            kind="false_alarm",
            outcome="false_alarm",
            is_own=data.is_own,
            game_id=data.game_id,
            analysis_ply=data.analysis_ply,
            flagged_uci=data.flagged_uci,
            fen=data.fen,
            key_uci=data.key_uci,
            game_info=_game_info_schema(data.game_info),
            window_points=data.window_points,
        )
    if isinstance(data, blunder_check_service.HerringSolutionData):
        return HerringSolution(
            kind="herring",
            outcome="cleared",
            is_own=data.is_own,
            game_id=data.game_id,
            analysis_ply=data.analysis_ply,
            fen=data.fen,
            sequence_ucis=data.sequence_ucis,
            game_info=_game_info_schema(data.game_info),
            window_points=data.window_points,
        )
    return _blunder_solution_schema(data)


@router.post(
    "/sessions/{session_id}/windows/{position}/better-move", response_model=BetterMoveResponse
)
async def submit_better_move(
    session_id: SessionIdPath,
    position: PositionPath,
    body: BetterMoveRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
    now_utc: NowUtc,
) -> BetterMoveResponse:
    """Grade and score the one better move after a caught blunder (server-only points)."""
    result = await _guarded(
        session,
        blunder_check_service.submit_better_move(
            session,
            user_id=user.id,
            session_id=session_id,
            position=position,
            played_uci=body.played_uci,
            client_tier=body.client_tier,
            now_utc=now_utc,
        ),
        user_id=user.id,
        session_id=session_id,
        position=position,
    )
    return BetterMoveResponse(
        tier=result.tier,
        points_awarded=result.points_awarded,
        window_points=result.window_points,
        session_points=result.session_points,
    )


@router.get(
    "/sessions/{session_id}/windows/{position}/solution", response_model=WindowSolutionResponse
)
async def window_solution(
    session_id: SessionIdPath,
    position: PositionPath,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: BetaUser,
) -> BlunderSolution | HerringSolution | FalseAlarmSolution:
    """What the solution screen shows after a window ended (409 while it is still open)."""
    data = await _guarded(
        session,
        blunder_check_service.window_solution(
            session, user_id=user.id, session_id=session_id, position=position
        ),
        user_id=user.id,
        session_id=session_id,
        position=position,
    )
    return _solution_response(data)
