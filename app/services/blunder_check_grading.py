"""Pure grading rules for the blunder-check drill (Phase 249, D-12, D-13, D-17, D-18).

No DB access here: the service feeds these functions rows it already loaded, so every
point, forfeit and timeout is decided by one tested state machine. The server is the only
grader (D-16: the key never leaves the server before the window ends).

Window move math (snapshot built by `blunder_check_selection.build_snapshot`):
  - `lead_start = first_ply - lead_in_plies` is the ply of `move_ucis[0]`.
  - the judged ply of move i (1-based) is `first_ply + 2 * (i - 1)` (only the user's moves
    are judged, every other ply).
  - the opponent reply after judged ply p is the UCI at ply p + 1 when the snapshot has it.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

import chess

from app.models.blunder_check import AnswerKind, AnswerResult, WindowOutcome
from app.models.drill_solve import DrillMoveQuality, DrillSource
from app.services.blunder_check_rules import BLUNDER_POINTS, SAFE_POINTS
from app.services.train_score import MOVE_QUALITY_TIER, MoveTier
from app.services.train_pool import (
    ServerGradedMove,
    answer_key_for,
    legal_answer_key,
    legal_server_graded_moves,
    server_graded_moves_for,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

MS_PER_SECOND: Final[int] = 1000
# D-13: the per-move countdown.
MOVE_TIMER_SECONDS: Final[int] = 10
# The client animation before a freshly shown prompt's countdown starts (the lead-in replay,
# or the feedback display plus move + reply). Used ONLY in the answer ceiling, never in the
# remaining-time report, so a reload cannot buy time (D-18).
PROMPT_ANIMATION_ALLOWANCE_S: Final[int] = 3
NETWORK_GRACE_S: Final[int] = 2
# D-18: a non-timeout answer later than this after `prompted_at` is graded as a timeout.
ANSWER_CEILING_S: Final[int] = MOVE_TIMER_SECONDS + PROMPT_ANIMATION_ALLOWANCE_S + NETWORK_GRACE_S
# Only the user's moves are judged, so judged plies are two apart.
PLIES_PER_USER_MOVE: Final[int] = 2

AnswerKindName = Literal["safe", "blunder", "timeout"]
AnswerResultName = Literal[
    "correct_safe", "false_alarm", "caught", "missed", "timeout_safe", "timeout_blunder"
]
OutcomeName = Literal["cleared", "caught", "missed", "false_alarm"]

ANSWER_KIND_BY_NAME: Final[dict[AnswerKindName, AnswerKind]] = {
    "safe": AnswerKind.SAFE,
    "blunder": AnswerKind.BLUNDER,
    "timeout": AnswerKind.TIMEOUT,
}
RESULT_BY_NAME: Final[dict[AnswerResultName, AnswerResult]] = {
    "correct_safe": AnswerResult.CORRECT_SAFE,
    "false_alarm": AnswerResult.FALSE_ALARM,
    "caught": AnswerResult.CAUGHT,
    "missed": AnswerResult.MISSED,
    "timeout_safe": AnswerResult.TIMEOUT_SAFE,
    "timeout_blunder": AnswerResult.TIMEOUT_BLUNDER,
}
RESULT_NAME_BY_VALUE: Final[dict[AnswerResult, AnswerResultName]] = {
    value: name for name, value in RESULT_BY_NAME.items()
}
MoveTierName = MoveTier
MOVE_QUALITY_BY_TIER: Final[dict[MoveTierName, DrillMoveQuality]] = {
    tier: quality for quality, tier in MOVE_QUALITY_TIER.items()
}
OUTCOME_BY_NAME: Final[dict[OutcomeName, WindowOutcome]] = {
    "cleared": WindowOutcome.CLEARED,
    "caught": WindowOutcome.CAUGHT,
    "missed": WindowOutcome.MISSED,
    "false_alarm": WindowOutcome.FALSE_ALARM,
}
OUTCOME_NAME_BY_VALUE: Final[dict[WindowOutcome, OutcomeName]] = {
    value: name for name, value in OUTCOME_BY_NAME.items()
}


@dataclass(frozen=True)
class AnswerGrade:
    """The verdict for one answer: points, forfeit, and whether/how the window ends."""

    result: AnswerResultName
    points_awarded: int
    points_forfeited: int
    window_ends: bool
    outcome: OutcomeName | None
    better_move: bool


# ---------------------------------------------------------------------------
# Grading state machine (D-12, D-13)
# ---------------------------------------------------------------------------


def _grade_blunder_move(answer: AnswerKindName, window_points: int) -> AnswerGrade:
    """The prompt on the blunder itself: flagging it is the only way to keep the window."""
    if answer == "blunder":
        return AnswerGrade("caught", BLUNDER_POINTS, 0, True, "caught", True)
    # "safe" or a timeout on the blunder both let it through: the safe points are forfeited.
    result: AnswerResultName = "missed" if answer == "safe" else "timeout_blunder"
    return AnswerGrade(result, 0, window_points, True, "missed", False)


def grade_answer(
    *,
    is_blunder_move: bool,
    is_last_judged_move: bool,
    answer: AnswerKindName,
    window_points: int,
) -> AnswerGrade:
    """Grade one answer. `window_points` is what the window has accumulated before it.

    A false alarm ends the window and keeps the safe points; a timeout on a safe move
    scores 0, forfeits the accumulated safe points and lets the window continue (D-13).
    The window clears only when the last judged move of a herring is answered.
    """
    if is_blunder_move:
        return _grade_blunder_move(answer, window_points)
    if answer == "blunder":
        return AnswerGrade("false_alarm", 0, 0, True, "false_alarm", False)
    outcome: OutcomeName | None = "cleared" if is_last_judged_move else None
    if answer == "timeout":
        return AnswerGrade("timeout_safe", 0, window_points, is_last_judged_move, outcome, False)
    return AnswerGrade("correct_safe", SAFE_POINTS, 0, is_last_judged_move, outcome, False)


# ---------------------------------------------------------------------------
# Timer (D-18)
# ---------------------------------------------------------------------------


def elapsed_ms(prompted_at: datetime.datetime, now: datetime.datetime) -> int:
    """Server-side milliseconds since the prompt was stamped, never negative (clock skew)."""
    return max(0, int((now - prompted_at).total_seconds() * MS_PER_SECOND))


def effective_answer(answer: AnswerKindName, server_elapsed_ms: int) -> AnswerKindName:
    """A non-timeout answer arriving past the ceiling is graded as a timeout (D-18)."""
    if answer != "timeout" and server_elapsed_ms > ANSWER_CEILING_S * MS_PER_SECOND:
        return "timeout"
    return answer


def timer_remaining_ms(prompted_at: datetime.datetime, now: datetime.datetime) -> int:
    """Real time left on the original stamp, clamped to [0, MOVE_TIMER_SECONDS].

    No animation allowance here: a reload keeps the original `prompted_at` and must not
    buy time (D-18). The allowance lives only in `ANSWER_CEILING_S`.
    """
    full = MOVE_TIMER_SECONDS * MS_PER_SECOND
    return max(0, min(full, full - elapsed_ms(prompted_at, now)))


def score_pct(points: int, possible: int) -> int:
    """D-14: floor(100 * points / possible), 0 when nothing was possible."""
    if possible <= 0:
        return 0
    return (100 * points) // possible


# ---------------------------------------------------------------------------
# Window move helpers
# ---------------------------------------------------------------------------


def window_ucis(move_ucis: str) -> list[str]:
    """The snapshot's UCI list (space separated, from the lead-in start on)."""
    return move_ucis.split()


def judged_ply(first_ply: int, move_index: int) -> int:
    """Game ply of the user's `move_index`-th (1-based) judged move."""
    return first_ply + PLIES_PER_USER_MOVE * (move_index - 1)


def uci_at(ucis: Sequence[str], lead_start: int, ply: int) -> str | None:
    """The snapshot UCI played at `ply`, None when the snapshot does not reach it."""
    index = ply - lead_start
    if 0 <= index < len(ucis):
        return ucis[index]
    return None


def fen_before_ply(start_fen: str, ucis: Sequence[str], lead_start: int, ply: int) -> str:
    """Full FEN of the board before the move at `ply` (start FEN plus the earlier snapshot moves)."""
    board = chess.Board(start_fen)
    for uci in ucis[: ply - lead_start]:
        board.push_uci(uci)
    return board.fen()


def is_legal_uci(fen: str, uci: str) -> bool:
    """True when `uci` parses and is a legal move in `fen`."""
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return False
    return move in board.legal_moves


# ---------------------------------------------------------------------------
# Better-move task (D-17)
# ---------------------------------------------------------------------------


def better_move_graded_moves(
    *,
    blunder_ply: int,
    key_uci: str,
    missed_pv_lines: list[Any] | None,
    fen: str,
) -> tuple[ServerGradedMove, ...]:
    """The server-graded move set for the better-move task, derived like a personalized puzzle.

    One derivation for allowed, pure-miss and mixed windows (D-17: no branch on the case):
    the key is the Stockfish best move at the blunder ply, the graded set is the blob's vetted
    alternatives (plus a sharp runner-up), legal in `fen`. An empty or missing blob gives an
    empty tuple, so the browser grades every non-key move itself.
    """
    key = answer_key_for(
        source=DrillSource.SR_ITEM,
        ply=blunder_ply,
        missed_pv_lines=missed_pv_lines,
        best_move=key_uci,
        ladder=None,
        filler_solution_uci=None,
    )
    moves = server_graded_moves_for(
        source=DrillSource.SR_ITEM,
        ply=blunder_ply,
        missed_pv_lines=missed_pv_lines,
        best_move=key_uci,
        ladder=None,
        herring_mover_color=None,
        key=key,
    )
    legal_key = legal_answer_key(key, fen).key_uci
    return legal_server_graded_moves(moves, fen, legal_key_uci=legal_key)


def resolve_better_move_tier(
    *,
    played_uci: str,
    key_uci: str,
    blunder_uci: str,
    graded_moves: Sequence[ServerGradedMove],
    client_tier: MoveTierName,
) -> MoveTierName:
    """The tier of the user's better move, decided like a personalized puzzle (D-17).

    The server owns every move it can judge: the key is "good", the user's own blunder is
    "wrong" (a stored blunder needs no search), a server-graded entry takes its own tier
    (the first match, `_resolve_grade` path 1). Only an off-key, ungraded move takes the
    browser engine's tier (path 3). Never branches on the window case.
    """
    if played_uci == key_uci:
        return "good"
    if played_uci == blunder_uci:
        return "wrong"
    for entry in graded_moves:
        if entry.uci == played_uci:
            return entry.tier
    return client_tier
