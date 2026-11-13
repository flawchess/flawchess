"""Pydantic v2 schemas for the blunder-check API (Phase 249).

Wire contract (D-16): no payload sent BEFORE a window ends may carry game ids, plies,
the window's case or whether it contains a blunder, only what the client needs to render
the current move. The opponent reply after a judged move travels only in the response to that
move's own answer, and no payload carries the window length or a remaining-prompt count.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final, Literal

from pydantic import BaseModel, Field

from app.schemas.train import ServerGradedMove
from app.services.blunder_check_rules import MAX_BLUNDER_POSITION

WindowOutcomeWire = Literal["cleared", "caught", "missed", "false_alarm"]
WindowState = Literal["pending", "active", "ended"]
AnswerKindWire = Literal["safe", "blunder", "timeout"]
AnswerResultWire = Literal[
    "correct_safe", "false_alarm", "caught", "missed", "timeout_safe", "timeout_blunder"
]

# blunder_check_answers.client_elapsed_ms is int4; a larger value would raise in asyncpg (500),
# so the request bound turns it into a 422 first.
_INT4_MAX: Final = 2**31 - 1


class WindowProgress(BaseModel):
    """Progress of one window in a session: outcome only once the window has ended.

    Carries NO game id, ply or case (D-16): the progress strip must not leak which windows
    contain a blunder.
    """

    position: int
    state: WindowState
    outcome: WindowOutcomeWire | None
    points_scored: int


class BlunderCheckSessionResponse(BaseModel):
    """Session header plus the per-window progress strip.

    `current_position` is the lowest position whose outcome is NULL, None when every
    window has ended.
    """

    session_id: int
    window_count: int
    current_position: int | None
    session_points: int
    windows: list[WindowProgress]


class Prompt(BaseModel):
    """The one judged move the user must rate right now: its UCI is the arrow on the board."""

    move_index: int
    move_uci: str


class AnsweredMove(BaseModel):
    """A judged move already answered, with the opponent reply that followed it (if any)."""

    move_index: int
    move_uci: str
    reply_uci: str | None
    result: AnswerResultWire
    points_awarded: int
    points_forfeited: int


class BetterMoveTask(BaseModel):
    """The better-move task handed out only when the blunder was caught (D-17)."""

    fen: str
    key_uci: str
    server_graded_moves: list[ServerGradedMove]


class WindowStartResponse(BaseModel):
    """Window start (or reload): the lead-in, answered moves so far and the single open prompt.

    No game id, ply, case, is_own, window length or remaining-prompt count (D-16).
    """

    position: int
    start_fen: str
    orientation: Literal["white", "black"]
    lead_in_ucis: list[str]
    answered: list[AnsweredMove]
    prompt: Prompt
    timer_remaining_ms: int
    move_timer_seconds: int
    window_points: int
    session_points: int
    # Set only on a reload after a caught blunder whose better move is still open: `answered`
    # then ends with the caught move, `prompt` repeats it and no prompt timer runs.
    better_move: BetterMoveTask | None


class AnswerRequest(BaseModel):
    """One answer to the open prompt; the server grades it (client time is stored, not trusted)."""

    move_index: int = Field(ge=1, le=MAX_BLUNDER_POSITION)
    answer: AnswerKindWire
    client_elapsed_ms: int = Field(ge=0, le=_INT4_MAX)


class AnswerResponse(BaseModel):
    """The server's grade for one answer plus what the user may see next."""

    move_index: int
    result: AnswerResultWire
    points_awarded: int
    points_forfeited: int
    window_points: int
    session_points: int
    window_ended: bool
    outcome: WindowOutcomeWire | None
    reply_uci: str | None
    next_prompt: Prompt | None
    timer_remaining_ms: int | None
    better_move: BetterMoveTask | None


class WindowResultItem(BaseModel):
    """One finished window in the session result (the session is over, so the outcome is public)."""

    position: int
    outcome: WindowOutcomeWire
    points_scored: int
    points_possible: int


class SessionResultResponse(BaseModel):
    """Finished session: points, points possible (frozen per window) and Score % (D-14)."""

    session_id: int
    session_points: int
    points_possible: int
    score_pct: int
    windows: list[WindowResultItem]


# ---------------------------------------------------------------------------
# Better move and solution (plan 05)
# ---------------------------------------------------------------------------

MoveTierWire = Literal["good", "inaccuracy", "wrong"]
TimeControlBucketWire = Literal["bullet", "blitz", "rapid", "classical"]
WindowCaseWire = Literal["allowed", "pure_miss", "mixed"]


class BetterMoveRequest(BaseModel):
    """The better move a user played after a caught blunder, with the browser engine's tier.

    The tier is only used for an off-key move the server cannot grade itself (D-17).
    """

    played_uci: str = Field(pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")
    client_tier: MoveTierWire


class BetterMoveResponse(BaseModel):
    """The server-resolved tier of the better move and the points it earned."""

    tier: MoveTierWire
    points_awarded: int
    window_points: int
    session_points: int


class GameInfo(BaseModel):
    """Neutral facts about a stranger's game (D-09): no usernames, emails or user ids."""

    time_control_str: str | None
    time_control_bucket: TimeControlBucketWire | None
    played_at: datetime | None
    mover_rating: int | None


class BlunderSolution(BaseModel):
    """Solution of a caught or missed blunder window (D-14)."""

    kind: Literal["blunder"]
    outcome: Literal["caught", "missed"]
    is_own: bool
    window_case: WindowCaseWire
    game_id: int | None
    analysis_ply: int
    fen: str
    blunder_uci: str
    key_uci: str
    better_move_uci: str | None
    better_move_tier: MoveTierWire | None
    server_graded_moves: list[ServerGradedMove]
    game_info: GameInfo | None
    window_points: int
    # The breakdown of `window_points`, for the verdict's point badges (Phase 249 UAT).
    safe_points: int
    blunder_points: int
    better_move_points: int | None


class HerringSolution(BaseModel):
    """Solution of a cleared herring window: the judged moves were all fine."""

    kind: Literal["herring"]
    outcome: Literal["cleared"]
    is_own: bool
    game_id: int | None
    analysis_ply: int
    fen: str
    sequence_ucis: list[str]
    game_info: GameInfo | None
    window_points: int


class FalseAlarmSolution(BaseModel):
    """Solution of a false alarm: the flagged move, its game and the best move there.

    Deliberately no case and no blunder, so an unreached blunder is not handed out (D-10).
    """

    kind: Literal["false_alarm"]
    outcome: Literal["false_alarm"]
    is_own: bool
    game_id: int | None
    analysis_ply: int
    flagged_uci: str
    fen: str
    key_uci: str | None
    game_info: GameInfo | None
    window_points: int


WindowSolutionResponse = Annotated[
    BlunderSolution | HerringSolution | FalseAlarmSolution, Field(discriminator="kind")
]
