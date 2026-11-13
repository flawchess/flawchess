"""Blunder-check session orchestration (Phase 249).

Business logic between the router and the repository: start a session or resume the open one,
start a window, grade answers (the server owns every grade, D-12/D-13/D-18) and finish a session.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Final, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blunder_check import (
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.drill_solve import DrillMoveQuality
from app.repositories import blunder_check_repository
from app.repositories.blunder_check_repository import GameInfoRow, SessionProgress
from app.repositories.query_utils import mover_is_white_at_ply
from app.services import blunder_check_selection
from app.services.blunder_check_grading import (
    ANSWER_KIND_BY_NAME,
    MOVE_QUALITY_BY_TIER,
    MOVE_TIMER_SECONDS,
    MS_PER_SECOND,
    OUTCOME_BY_NAME,
    OUTCOME_NAME_BY_VALUE,
    PLIES_PER_USER_MOVE,
    RESULT_BY_NAME,
    RESULT_NAME_BY_VALUE,
    AnswerGrade,
    AnswerKindName,
    AnswerResultName,
    MoveTierName,
    OutcomeName,
    better_move_graded_moves,
    effective_answer,
    elapsed_ms,
    fen_before_ply,
    grade_answer,
    is_legal_uci,
    resolve_better_move_tier,
    score_pct,
    timer_remaining_ms,
    uci_at,
    window_ucis,
)
from app.services.train_pool import ServerGradedMove
from app.services.blunder_check_rules import BLUNDER_POINTS
from app.services.train_score import MOVE_QUALITY_TIER, MOVE_TIER_POINTS

ConflictReason = Literal[
    "window_ended",
    "previous_window_open",
    "session_closed",
    "not_started",
    "stale_prompt",
    "windows_open",
    "not_caught",
    "better_move_done",
    "window_open",
]
WindowCaseName = Literal["allowed", "pure_miss", "mixed"]

_NOT_FOUND_MESSAGE: Final = "Blunder-check session or window not found"
_CONFLICT_MESSAGE: Final = "Blunder-check request conflicts with the window state"
_MISSING_SNAPSHOT_MOVE: Final = "Blunder-check window snapshot is missing a judged move"
_FIRST_MOVE_INDEX: Final = 1
_ILLEGAL_MOVE_MESSAGE: Final = "Illegal blunder-check better move"
_MISSING_FALSE_ALARM_ROW: Final = "Blunder-check false-alarm window has no false-alarm answer row"
_WINDOW_CASE_NAME: Final[dict[WindowCase, WindowCaseName]] = {
    WindowCase.ALLOWED: "allowed",
    WindowCase.PURE_MISS: "pure_miss",
    WindowCase.MIXED: "mixed",
}


class BlunderCheckNotFoundError(Exception):
    """Unknown session or window, or one that belongs to another user (mapped to 404)."""

    def __init__(self) -> None:
        super().__init__(_NOT_FOUND_MESSAGE)


class BlunderCheckConflictError(Exception):
    """The request does not fit the window state (mapped to 409 with `reason` as the detail)."""

    def __init__(self, reason: ConflictReason) -> None:
        super().__init__(_CONFLICT_MESSAGE)
        self.reason: ConflictReason = reason


class BlunderCheckIllegalMoveError(Exception):
    """The submitted better move is not legal in the pre-blunder position (mapped to 422)."""

    def __init__(self) -> None:
        super().__init__(_ILLEGAL_MOVE_MESSAGE)


@dataclass(frozen=True)
class PromptData:
    """The one open prompt: its index and the UCI of the judged move (the arrow)."""

    move_index: int
    move_uci: str


@dataclass(frozen=True)
class AnsweredMoveData:
    """An answered judged move with the reply that followed it."""

    move_index: int
    move_uci: str
    reply_uci: str | None
    result: AnswerResultName
    points_awarded: int
    points_forfeited: int


@dataclass(frozen=True)
class WindowStart:
    """Everything the window start (or a reload) hands to the client."""

    position: int
    start_fen: str
    orientation: Literal["white", "black"]
    lead_in_ucis: list[str]
    answered: list[AnsweredMoveData]
    prompt: PromptData
    timer_remaining_ms: int
    window_points: int
    session_points: int
    # The still-open better-move task of a caught window (a reload during that step), else None.
    better_move: BetterMoveData | None = None


@dataclass(frozen=True)
class WindowResult:
    """One finished window in the session result."""

    position: int
    outcome: OutcomeName
    points_scored: int
    points_possible: int


@dataclass(frozen=True)
class SessionResult:
    """A finished session: points, points possible (frozen per window) and Score % (D-14)."""

    session_id: int
    session_points: int
    points_possible: int
    score_pct: int
    windows: list[WindowResult]


@dataclass(frozen=True)
class BetterMoveData:
    """The better-move task: pre-blunder FEN, the key and the server-graded moves (D-17)."""

    fen: str
    key_uci: str
    server_graded_moves: tuple[ServerGradedMove, ...]


@dataclass(frozen=True)
class AnswerOutcome:
    """The server's grade for one answer plus what the user may see next."""

    move_index: int
    result: AnswerResultName
    points_awarded: int
    points_forfeited: int
    window_points: int
    session_points: int
    window_ended: bool
    outcome: OutcomeName | None
    reply_uci: str | None
    next_prompt: PromptData | None
    timer_remaining_ms: int | None
    better_move: BetterMoveData | None


async def compose_or_resume(
    session: AsyncSession, *, user_id: int, now_utc: datetime.datetime
) -> SessionProgress | None:
    """The user's open session, composing and persisting a new one when there is none.

    Returns None when nothing could be composed (no usable supply). A lost race against a
    concurrent start (the one-open-session index fired) resumes the winner's session.
    """
    existing = await blunder_check_repository.open_session_progress(session, user_id=user_id)
    if existing is not None:
        return existing
    windows = await blunder_check_selection.compose_windows(
        session, user_id=user_id, rng=blunder_check_selection.new_session_rng()
    )
    if not windows:
        return None
    # Result ignored: None means the race loser, and either way the open session is readable.
    await blunder_check_repository.insert_session(
        session, user_id=user_id, windows=windows, now_utc=now_utc
    )
    return await blunder_check_repository.open_session_progress(session, user_id=user_id)


# ---------------------------------------------------------------------------
# Window start
# ---------------------------------------------------------------------------


def _lead_start(window: BlunderCheckWindow) -> int:
    """Game ply of `move_ucis[0]`."""
    return window.first_ply - window.lead_in_plies


def _arrow_uci(window: BlunderCheckWindow, ply: int) -> str:
    """UCI of the judged move at `ply` from the snapshot (it always holds every judged move)."""
    uci = uci_at(window_ucis(window.move_ucis), _lead_start(window), ply)
    if uci is None:
        raise RuntimeError(_MISSING_SNAPSHOT_MOVE)
    return uci


def _answered_move(window: BlunderCheckWindow, row: BlunderCheckAnswer) -> AnsweredMoveData:
    assert row.result is not None  # answered rows carry a result (CHECK constraint)
    return AnsweredMoveData(
        move_index=row.move_index,
        move_uci=_arrow_uci(window, row.ply),
        reply_uci=uci_at(window_ucis(window.move_ucis), _lead_start(window), row.ply + 1),
        result=RESULT_NAME_BY_VALUE[AnswerResult(row.result)],
        points_awarded=row.points_awarded,
        points_forfeited=row.points_forfeited,
    )


def _open_row(rows: list[BlunderCheckAnswer]) -> BlunderCheckAnswer | None:
    """The unanswered prompt row (the lowest move_index without an answer)."""
    return next((row for row in rows if row.answered_at is None), None)


def _check_startable(header: BlunderCheckSession, window: BlunderCheckWindow) -> None:
    if header.status != "open":
        raise BlunderCheckConflictError("session_closed")
    if window.outcome is not None:
        raise BlunderCheckConflictError("window_ended")


def _better_move_pending(window: BlunderCheckWindow) -> bool:
    return window.outcome == int(WindowOutcome.CAUGHT) and window.better_move_tier is None


async def _resume_better_move(
    session: AsyncSession, window: BlunderCheckWindow, *, session_id: int
) -> WindowStart:
    """A reload during the better-move step: the answered moves and the task again.

    Bug fix (Phase 249 review): this used to answer 409 `window_ended`, so the better-move
    points stayed in `points_possible` but could never be earned.
    """
    rows = await blunder_check_repository.answers_for_window(session, window_id=window.id)
    answered = [row for row in rows if row.answered_at is not None]
    if not answered:
        raise BlunderCheckConflictError("window_ended")
    caught = answered[-1]
    return WindowStart(
        position=window.position,
        start_fen=window.start_fen,
        orientation="white" if mover_is_white_at_ply(window.first_ply) else "black",
        lead_in_ucis=window_ucis(window.move_ucis)[: window.lead_in_plies],
        answered=[_answered_move(window, row) for row in answered],
        prompt=PromptData(caught.move_index, _arrow_uci(window, caught.ply)),
        timer_remaining_ms=0,
        window_points=window.points_scored,
        session_points=await blunder_check_repository.session_points(
            session, session_id=session_id
        ),
        better_move=await _better_move_task(session, window),
    )


async def start_window(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    position: int,
    now_utc: datetime.datetime,
) -> WindowStart:
    """Start window `position`, or reload it: the lead-in, answered moves and the open prompt.

    Idempotent: the open prompt keeps its original `prompted_at`, so a reload reports the real
    time left and never buys time (D-18).
    """
    found = await blunder_check_repository.get_window_for_user(
        session, user_id=user_id, session_id=session_id, position=position
    )
    if found is None:
        raise BlunderCheckNotFoundError
    header, window = found
    if header.status == "open" and _better_move_pending(window):
        return await _resume_better_move(session, window, session_id=session_id)
    _check_startable(header, window)
    if not await blunder_check_repository.earlier_windows_ended(
        session, session_id=session_id, position=position
    ):
        # T-249-14: windows are played in their frozen order.
        raise BlunderCheckConflictError("previous_window_open")
    await blunder_check_repository.mark_window_started(
        session, window_id=window.id, now_utc=now_utc
    )
    await blunder_check_repository.insert_prompt(
        session,
        window_id=window.id,
        move_index=_FIRST_MOVE_INDEX,
        ply=window.first_ply,
        prompted_at=now_utc,
    )
    rows = await blunder_check_repository.answers_for_window(session, window_id=window.id)
    open_row = _open_row(rows)
    if open_row is None:
        raise BlunderCheckConflictError("window_ended")
    return WindowStart(
        position=window.position,
        start_fen=window.start_fen,
        orientation="white" if mover_is_white_at_ply(window.first_ply) else "black",
        lead_in_ucis=window_ucis(window.move_ucis)[: window.lead_in_plies],
        answered=[_answered_move(window, row) for row in rows if row.answered_at is not None],
        prompt=PromptData(open_row.move_index, _arrow_uci(window, open_row.ply)),
        timer_remaining_ms=timer_remaining_ms(open_row.prompted_at, now_utc),
        window_points=window.points_scored,
        session_points=await blunder_check_repository.session_points(
            session, session_id=session_id
        ),
    )


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------


async def _load_answerable(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    position: int,
    move_index: int,
) -> tuple[BlunderCheckWindow, BlunderCheckAnswer]:
    """The window (row-locked) and its open prompt row, or the 404/409 that says why not."""
    found = await blunder_check_repository.get_window_for_user(
        session, user_id=user_id, session_id=session_id, position=position, for_update=True
    )
    if found is None:
        raise BlunderCheckNotFoundError
    _, window = found
    if window.started_at is None:
        raise BlunderCheckConflictError("not_started")
    if window.outcome is not None:
        raise BlunderCheckConflictError("window_ended")
    rows = await blunder_check_repository.answers_for_window(session, window_id=window.id)
    open_row = _open_row(rows)
    if open_row is None or open_row.move_index != move_index:
        raise BlunderCheckConflictError("stale_prompt")
    return window, open_row


async def _persist_grade(
    session: AsyncSession,
    *,
    window: BlunderCheckWindow,
    row: BlunderCheckAnswer,
    grade: AnswerGrade,
    answer: AnswerKindName,
    client_elapsed_ms: int,
    server_elapsed_ms: int,
    now_utc: datetime.datetime,
) -> None:
    """Claim the prompt row, then apply its points and outcome (only after a successful claim)."""
    claimed = await blunder_check_repository.claim_answer(
        session,
        window_id=window.id,
        move_index=row.move_index,
        answer=ANSWER_KIND_BY_NAME[answer],
        result=RESULT_BY_NAME[grade.result],
        points_awarded=grade.points_awarded,
        points_forfeited=grade.points_forfeited,
        client_elapsed_ms=client_elapsed_ms,
        server_elapsed_ms=server_elapsed_ms,
        answered_at=now_utc,
    )
    if not claimed:
        # Lost a double-submit race: nothing was applied.
        raise BlunderCheckConflictError("stale_prompt")
    await blunder_check_repository.apply_window_result(
        session,
        window_id=window.id,
        points_delta=grade.points_awarded - grade.points_forfeited,
        outcome=None if grade.outcome is None else OUTCOME_BY_NAME[grade.outcome],
        ended_at=now_utc,
    )


async def _better_move_task(session: AsyncSession, window: BlunderCheckWindow) -> BetterMoveData:
    """Pre-blunder FEN plus the key and graded set (derived the same way for every case, D-17)."""
    blunder_ply = window.blunder_ply
    key_uci = window.key_uci
    assert blunder_ply is not None and key_uci is not None  # a caught window has both
    fen = _fen_before(window, blunder_ply)
    moves = await _graded_moves(session, window, blunder_ply=blunder_ply, key_uci=key_uci, fen=fen)
    return BetterMoveData(fen=fen, key_uci=key_uci, server_graded_moves=moves)


async def _continue_window(
    session: AsyncSession,
    *,
    window: BlunderCheckWindow,
    row: BlunderCheckAnswer,
    now_utc: datetime.datetime,
) -> PromptData:
    """Stamp the next prompt and return its arrow."""
    next_ply = row.ply + PLIES_PER_USER_MOVE
    await blunder_check_repository.insert_prompt(
        session,
        window_id=window.id,
        move_index=row.move_index + 1,
        ply=next_ply,
        prompted_at=now_utc,
    )
    return PromptData(row.move_index + 1, _arrow_uci(window, next_ply))


async def _build_outcome(
    session: AsyncSession,
    *,
    window: BlunderCheckWindow,
    row: BlunderCheckAnswer,
    grade: AnswerGrade,
    window_points: int,
    now_utc: datetime.datetime,
) -> AnswerOutcome:
    """Assemble the response: reply only when the window goes on (or cleared), better move on caught."""
    next_prompt: PromptData | None = None
    timer_ms: int | None = None
    if not grade.window_ends:
        next_prompt = await _continue_window(session, window=window, row=row, now_utc=now_utc)
        timer_ms = MOVE_TIMER_SECONDS * MS_PER_SECOND
    # The reply after a judged move is shown while the window goes on or once it cleared;
    # after a caught/missed blunder or a false alarm it stays hidden until the solution.
    reveals_reply = not grade.window_ends or grade.outcome == "cleared"
    reply = (
        uci_at(window_ucis(window.move_ucis), _lead_start(window), row.ply + 1)
        if reveals_reply
        else None
    )
    return AnswerOutcome(
        move_index=row.move_index,
        result=grade.result,
        points_awarded=grade.points_awarded,
        points_forfeited=grade.points_forfeited,
        window_points=window_points,
        session_points=await blunder_check_repository.session_points(
            session, session_id=window.session_id
        ),
        window_ended=grade.window_ends,
        outcome=grade.outcome,
        reply_uci=reply,
        next_prompt=next_prompt,
        timer_remaining_ms=timer_ms,
        better_move=await _better_move_task(session, window) if grade.better_move else None,
    )


async def answer_prompt(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    position: int,
    move_index: int,
    answer: AnswerKindName,
    client_elapsed_ms: int,
    now_utc: datetime.datetime,
) -> AnswerOutcome:
    """Grade one answer against the secret key and reveal only what the grade allows (D-16)."""
    window, row = await _load_answerable(
        session, user_id=user_id, session_id=session_id, position=position, move_index=move_index
    )
    server_elapsed_ms = elapsed_ms(row.prompted_at, now_utc)
    window_points = window.points_scored
    grade = grade_answer(
        is_blunder_move=row.ply == window.blunder_ply,
        is_last_judged_move=move_index == window.window_length,
        answer=effective_answer(answer, server_elapsed_ms),
        window_points=window_points,
    )
    await _persist_grade(
        session,
        window=window,
        row=row,
        grade=grade,
        answer=answer,
        client_elapsed_ms=client_elapsed_ms,
        server_elapsed_ms=server_elapsed_ms,
        now_utc=now_utc,
    )
    return await _build_outcome(
        session,
        window=window,
        row=row,
        grade=grade,
        window_points=window_points + grade.points_awarded - grade.points_forfeited,
        now_utc=now_utc,
    )


# ---------------------------------------------------------------------------
# Finish (D-14)
# ---------------------------------------------------------------------------


async def finish_session(
    session: AsyncSession, *, user_id: int, session_id: int, now_utc: datetime.datetime
) -> SessionResult:
    """Complete the session and return points, points possible and Score % (D-14).

    Points possible is the sum of the per-window values frozen at composition, so a blunder
    never reached after a false alarm still counts. A completed session returns its result
    again (idempotent).
    """
    windows = await blunder_check_repository.windows_for_session(
        session, user_id=user_id, session_id=session_id
    )
    if not windows:
        raise BlunderCheckNotFoundError
    if any(window.outcome is None for window in windows):
        raise BlunderCheckConflictError("windows_open")
    await blunder_check_repository.complete_session(session, session_id=session_id, now_utc=now_utc)
    points = sum(window.points_scored for window in windows)
    possible = sum(window.points_possible for window in windows)
    return SessionResult(
        session_id=session_id,
        session_points=points,
        points_possible=possible,
        score_pct=score_pct(points, possible),
        windows=[
            WindowResult(
                position=window.position,
                outcome=OUTCOME_NAME_BY_VALUE[WindowOutcome(window.outcome)],
                points_scored=window.points_scored,
                points_possible=window.points_possible,
            )
            for window in windows
            if window.outcome is not None
        ],
    )


# ---------------------------------------------------------------------------
# Better move (D-17)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BetterMoveResult:
    """The server-resolved tier of the better move and the points it earned."""

    tier: MoveTierName
    points_awarded: int
    window_points: int
    session_points: int


def _check_better_move_claimable(header: BlunderCheckSession, window: BlunderCheckWindow) -> None:
    """409 unless the session is open, the window was caught and its better move is still free."""
    if header.status != "open":
        raise BlunderCheckConflictError("session_closed")
    if window.outcome != int(WindowOutcome.CAUGHT):
        raise BlunderCheckConflictError("not_caught")
    if window.better_move_tier is not None:
        raise BlunderCheckConflictError("better_move_done")


async def _resolve_window_tier(
    session: AsyncSession,
    *,
    window: BlunderCheckWindow,
    fen: str,
    played_uci: str,
    client_tier: MoveTierName,
) -> MoveTierName:
    """Resolve the tier with the live blob's graded set (empty when the game is gone)."""
    blunder_ply = window.blunder_ply
    key_uci = window.key_uci
    assert blunder_ply is not None and key_uci is not None  # a caught window has both
    graded = await _graded_moves(session, window, blunder_ply=blunder_ply, key_uci=key_uci, fen=fen)
    return resolve_better_move_tier(
        played_uci=played_uci,
        key_uci=key_uci,
        blunder_uci=_arrow_uci(window, blunder_ply),
        graded_moves=graded,
        client_tier=client_tier,
    )


async def submit_better_move(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    position: int,
    played_uci: str,
    client_tier: MoveTierName,
    now_utc: datetime.datetime,
) -> BetterMoveResult:
    """Grade and score the one better move of a caught window (server-only points, D-17).

    The window row is locked like the answer path, so two concurrent submits serialize and
    the claiming UPDATE is the second line of defence against a double award (T-249-15).
    """
    found = await blunder_check_repository.get_window_for_user(
        session, user_id=user_id, session_id=session_id, position=position, for_update=True
    )
    if found is None:
        raise BlunderCheckNotFoundError
    header, window = found
    _check_better_move_claimable(header, window)
    blunder_ply = window.blunder_ply
    assert blunder_ply is not None  # a caught window has a blunder ply
    fen = _fen_before(window, blunder_ply)
    if not is_legal_uci(fen, played_uci):
        raise BlunderCheckIllegalMoveError
    tier = await _resolve_window_tier(
        session, window=window, fen=fen, played_uci=played_uci, client_tier=client_tier
    )
    points = MOVE_TIER_POINTS[tier]
    claimed = await blunder_check_repository.claim_better_move(
        session,
        window_id=window.id,
        played_uci=played_uci,
        tier=MOVE_QUALITY_BY_TIER[tier],
        points=points,
        now_utc=now_utc,
    )
    if not claimed:
        raise BlunderCheckConflictError("better_move_done")
    return BetterMoveResult(
        tier=tier,
        points_awarded=points,
        window_points=window.points_scored + points,
        session_points=await blunder_check_repository.session_points(
            session, session_id=session_id
        ),
    )


# ---------------------------------------------------------------------------
# Solution (D-09, D-10, D-14, D-16)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlunderSolutionData:
    """A caught or missed window's full reveal."""

    outcome: Literal["caught", "missed"]
    is_own: bool
    window_case: WindowCaseName
    game_id: int | None
    analysis_ply: int
    fen: str
    blunder_uci: str
    key_uci: str
    better_move_uci: str | None
    better_move_tier: MoveTierName | None
    # The graded alternatives at the blunder position (the better-move task's set), so the
    # solution can badge the moves that were also good. Safe to send: the window has ended.
    server_graded_moves: tuple[ServerGradedMove, ...]
    game_info: GameInfoRow | None
    window_points: int
    # The breakdown of `window_points`: the safe calls before the blunder, the catch itself
    # and the better move (None when none was played).
    safe_points: int
    blunder_points: int
    better_move_points: int | None


@dataclass(frozen=True)
class HerringSolutionData:
    """A cleared herring window's reveal: every judged move was fine."""

    is_own: bool
    game_id: int | None
    analysis_ply: int
    fen: str
    # Every ply from the first judged move on, replies included, so the client can replay it.
    sequence_ucis: list[str]
    game_info: GameInfoRow | None
    window_points: int


@dataclass(frozen=True)
class FalseAlarmSolutionData:
    """A false alarm's reveal: the flagged move, its position, its game and the best move there.

    Phase 249 UAT: a false alarm gets the same lines and Analyze as the other solutions. The
    window's case and its unreached blunder are still not sent.
    """

    is_own: bool
    game_id: int | None
    analysis_ply: int
    flagged_uci: str
    fen: str
    # Stockfish's best move at the flagged position, None when it is not stored or not legal.
    key_uci: str | None
    game_info: GameInfoRow | None
    window_points: int


SolutionData = BlunderSolutionData | HerringSolutionData | FalseAlarmSolutionData


async def _foreign_game_info(
    session: AsyncSession, window: BlunderCheckWindow
) -> GameInfoRow | None:
    """Neutral facts of a stranger's game that still exists (own windows use the library card)."""
    if window.is_own or window.game_id is None:
        return None
    return await blunder_check_repository.game_info_for(session, game_id=window.game_id)


def _fen_before(window: BlunderCheckWindow, ply: int) -> str:
    return fen_before_ply(window.start_fen, window_ucis(window.move_ucis), _lead_start(window), ply)


async def _graded_moves(
    session: AsyncSession,
    window: BlunderCheckWindow,
    *,
    blunder_ply: int,
    key_uci: str,
    fen: str,
) -> tuple[ServerGradedMove, ...]:
    """The better-move graded set from the live blob (empty when the game is gone)."""
    blob = await blunder_check_repository.missed_pv_lines_at(
        session, game_id=window.game_id, ply=blunder_ply
    )
    return better_move_graded_moves(
        blunder_ply=blunder_ply, key_uci=key_uci, missed_pv_lines=blob, fen=fen
    )


async def _blunder_solution(
    session: AsyncSession, window: BlunderCheckWindow
) -> BlunderSolutionData:
    blunder_ply = window.blunder_ply
    key_uci = window.key_uci
    assert blunder_ply is not None and key_uci is not None  # a blunder window has both
    tier = (
        None
        if window.better_move_tier is None
        else MOVE_QUALITY_TIER[DrillMoveQuality(window.better_move_tier)]
    )
    fen = _fen_before(window, blunder_ply)
    caught = window.outcome == int(WindowOutcome.CAUGHT)
    blunder_points = BLUNDER_POINTS if caught else 0
    better_move_points = None if tier is None else MOVE_TIER_POINTS[tier]
    return BlunderSolutionData(
        outcome="caught" if caught else "missed",
        is_own=window.is_own,
        window_case=_WINDOW_CASE_NAME[WindowCase(window.window_case)],
        game_id=window.game_id,
        analysis_ply=blunder_ply,
        fen=fen,
        blunder_uci=_arrow_uci(window, blunder_ply),
        key_uci=key_uci,
        better_move_uci=window.better_move_uci,
        better_move_tier=tier,
        server_graded_moves=await _graded_moves(
            session, window, blunder_ply=blunder_ply, key_uci=key_uci, fen=fen
        ),
        game_info=await _foreign_game_info(session, window),
        window_points=window.points_scored,
        # What is left of the window's points once the catch and the better move are taken out.
        safe_points=window.points_scored - blunder_points - (better_move_points or 0),
        blunder_points=blunder_points,
        better_move_points=better_move_points,
    )


async def _herring_solution(
    session: AsyncSession, window: BlunderCheckWindow
) -> HerringSolutionData:
    return HerringSolutionData(
        is_own=window.is_own,
        game_id=window.game_id,
        analysis_ply=window.first_ply,
        fen=_fen_before(window, window.first_ply),
        sequence_ucis=window_ucis(window.move_ucis)[window.lead_in_plies :],
        game_info=await _foreign_game_info(session, window),
        window_points=window.points_scored,
    )


def _legal_uci(fen: str, uci: str | None) -> str | None:
    """`uci` when it is a legal move in `fen`, else None."""
    return uci if uci is not None and is_legal_uci(fen, uci) else None


async def _false_alarm_solution(
    session: AsyncSession, window: BlunderCheckWindow
) -> FalseAlarmSolutionData:
    """The flagged move with its game and best move: never the case or the unreached blunder."""
    rows = await blunder_check_repository.answers_for_window(session, window_id=window.id)
    alarm = next((row for row in rows if row.result == int(AnswerResult.FALSE_ALARM)), None)
    if alarm is None:
        raise RuntimeError(_MISSING_FALSE_ALARM_ROW)
    fen = _fen_before(window, alarm.ply)
    best_move = await blunder_check_repository.best_move_at(
        session, game_id=window.game_id, ply=alarm.ply
    )
    return FalseAlarmSolutionData(
        is_own=window.is_own,
        game_id=window.game_id,
        analysis_ply=alarm.ply,
        flagged_uci=_arrow_uci(window, alarm.ply),
        fen=fen,
        key_uci=_legal_uci(fen, best_move),
        game_info=await _foreign_game_info(session, window),
        window_points=window.points_scored,
    )


async def window_solution(
    session: AsyncSession, *, user_id: int, session_id: int, position: int
) -> SolutionData:
    """The post-window reveal; refused until the window ended (D-16).

    A false alarm reveals the flagged move's position and game, but not the window's case
    or the blunder the user never reached (D-10).
    """
    found = await blunder_check_repository.get_window_for_user(
        session, user_id=user_id, session_id=session_id, position=position
    )
    if found is None:
        raise BlunderCheckNotFoundError
    _, window = found
    if window.outcome is None:
        raise BlunderCheckConflictError("window_open")
    if window.outcome == int(WindowOutcome.FALSE_ALARM):
        return await _false_alarm_solution(session, window)
    if window.outcome == int(WindowOutcome.CLEARED):
        return await _herring_solution(session, window)
    return await _blunder_solution(session, window)
