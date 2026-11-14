"""line_material.py - pure material count along a stored refutation line (Phase 250 D-02, D-05).

Given the position before a blunder, the blunder move and the stored engine line that
punishes it (``game_positions.pv`` at flaw ply + 1, space-separated UCI starting with the
opponent's reply), count the material the blunderer is down after following the line for
1 / 3 / 5 / 7 / 9 plies, and find the ply at which the blunderer is mated, if ever.

Semantics follow the exploratory reference (``capture_loss`` in
``temp/blunder-check/refine.py``, gitignored) that the owner's label study was run with:

- piece values 1 / 3 / 3 / 5 / 9, only captures count, promotions are not material;
- the blunder move's own capture counts in the blunderer's favour (the baseline is the
  position before the blunder);
- the blunderer's recapture at depth + 1 is included, an opponent capture at depth + 1 is not;
- an opponent capture of a piece that the blunderer's previous line move placed on that
  square without capturing is ignored (engine desperado or spite check in a lost position);
- a line that ends on an opponent capture before depth + 1 gets a static-exchange recapture
  credit (the best recapture on that square, least valuable attacker first).

D-05 NULL rule: a depth the stored line does not reach is None ("line too short to tell"),
not 0, unless the blunderer is mated within the walked line or the recapture credit settled
the short line. A missing, empty, malformed or illegal line gives all-None facts and never
raises. The caller's board is never mutated.

No I/O. The score that consumes these facts lives in ``app/services/facepalm_score.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import chess

# Depths (plies of the stored line) whose net loss is stored on game_flaws (D-05).
LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)

# game_flaws column holding the net loss at each depth.
LINE_LOSS_COLUMNS: Mapping[int, str] = {depth: f"line_loss_{depth}" for depth in LINE_LOSS_DEPTHS}

# game_flaws column holding the ply at which the blunderer is mated within the line.
LINE_MATE_PLY_COLUMN: str = "line_mate_ply"

# Material values (pawn units). The king is never captured; 0 keeps the table total.
PIECE_VALUES: Mapping[chess.PieceType, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

# An en passant capture removes a pawn that is not on the destination square.
EN_PASSANT_VALUE: int = 1

# Attacker ordering for the static exchange: the king must recapture last, so it is priced
# above every other piece (same ordering as the reference's value table).
_SEE_KING_VALUE: int = 100
_SEE_VALUES: Mapping[chess.PieceType, int] = {**PIECE_VALUES, chess.KING: _SEE_KING_VALUE}

# Separator of the stored line; matches game_positions.pv (space-joined UCI), kept local so this
# module stays free of the scorer's imports.
_PV_SEPARATOR: str = " "

# One ply beyond the deepest stored depth is read (the blunderer's recapture at depth + 1).
_MAX_WALK_PLIES: int = max(LINE_LOSS_DEPTHS) + 1


@dataclass(frozen=True, slots=True)
class LineFacts:
    """Net loss per stored depth and the mate ply, each None when not settled (D-05)."""

    loss_by_depth: Mapping[int, int | None]
    mate_ply: int | None

    def loss_at(self, depth: int) -> int | None:
        """Net material loss at `depth` plies; None when the line is too short to tell."""
        return self.loss_by_depth.get(depth)

    def as_columns(self) -> dict[str, int | None]:
        """The five line_loss_N values plus line_mate_ply, keyed by game_flaws column."""
        columns: dict[str, int | None] = {
            LINE_LOSS_COLUMNS[depth]: self.loss_at(depth) for depth in LINE_LOSS_DEPTHS
        }
        columns[LINE_MATE_PLY_COLUMN] = self.mate_ply
        return columns


def null_line_facts() -> LineFacts:
    """Every depth None and no mate (a blunder with no usable stored line)."""
    return LineFacts(loss_by_depth=dict.fromkeys(LINE_LOSS_DEPTHS), mate_ply=None)


@dataclass(frozen=True, slots=True)
class _Step:
    """One legal ply of the stored line, as seen from the blunderer."""

    opponent_move: bool
    victim_value: int
    to_square: int
    blunderer_mated: bool


def _victim_value(board: chess.Board, move: chess.Move) -> int:
    """Material value of the piece `move` captures on `board` (0 for a non-capture)."""
    if board.is_en_passant(move):
        return EN_PASSANT_VALUE
    piece = board.piece_at(move.to_square)
    return PIECE_VALUES[piece.piece_type] if piece else 0


def _best_recapture(board: chess.Board, square: int) -> int:
    """Best net gain (>= 0) the side to move gets by capturing on `square`, least valuable attacker first."""
    captures = [m for m in board.legal_moves if m.to_square == square and board.is_capture(m)]
    if not captures:
        return 0
    cheapest = min(
        captures, key=lambda m: _SEE_VALUES[board.piece_type_at(m.from_square) or chess.PAWN]
    )
    return max(0, _exchange_value(board, cheapest))


def _exchange_value(board: chess.Board, capture: chess.Move) -> int:
    """Static exchange value of `capture` for the side making it (pawn units, may be negative)."""
    victim = board.piece_at(capture.to_square)
    if victim is not None:
        gain = _SEE_VALUES[victim.piece_type]
    else:
        gain = EN_PASSANT_VALUE if board.is_en_passant(capture) else 0
    after = board.copy(stack=False)
    after.push(capture)
    return gain - _best_recapture(after, capture.to_square)


def _parse_move(token: str) -> chess.Move | None:
    """The UCI token as a move, or None when malformed (worker-supplied strings, T-250-01)."""
    try:
        return chess.Move.from_uci(token)
    except ValueError:
        return None


def _replay_line(
    board: chess.Board, tokens: list[str], blunderer: chess.Color
) -> tuple[list[_Step], chess.Board]:
    """Replay the legal prefix of `tokens` on `board` (mutated), stopping at the first bad token.

    Returns the steps and the board after the last legal token.
    """
    steps: list[_Step] = []
    for token in tokens:
        move = _parse_move(token)
        if move is None or move not in board.legal_moves:
            break
        opponent_move = board.turn != blunderer
        victim = _victim_value(board, move)
        board.push(move)
        mated = board.turn == blunderer and board.is_checkmate()
        steps.append(_Step(opponent_move, victim, move.to_square, mated))
    return steps, board


def _recapture_credit(steps: list[_Step], end_board: chess.Board) -> int | None:
    """Static-exchange credit for a line that ended on an opponent capture, else None.

    Only a line shorter than every walk limit can need it; a mated blunderer gets none.
    """
    if not steps or len(steps) >= _MAX_WALK_PLIES:
        return None
    last = steps[-1]
    if not (last.opponent_move and last.victim_value and not last.blunderer_mated):
        return None
    return _best_recapture(end_board, last.to_square)


def _net_loss(first_victim: int, steps: list[_Step], depth: int) -> int:
    """Net material the blunderer is down over the first `depth` plies plus a depth + 1 recapture."""
    loss = -first_victim
    quiet_blunderer_square: int | None = (
        None  # where the blunderer's last move landed without capturing
    )
    for index, step in enumerate(steps[: depth + 1], start=1):
        if index == depth + 1 and (step.opponent_move or step.victim_value == 0):
            break  # only a blunderer capture is taken at depth + 1
        if step.opponent_move:
            if step.victim_value and step.to_square != quiet_blunderer_square:
                loss += step.victim_value
            quiet_blunderer_square = None
        else:
            loss -= step.victim_value
            quiet_blunderer_square = step.to_square if step.victim_value == 0 else None
    return loss


def _loss_at_depth(
    first_victim: int, steps: list[_Step], depth: int, credit: int | None
) -> int | None:
    """Net loss at `depth`, or None when the stored line is too short to settle it (D-05)."""
    walked = min(len(steps), depth + 1)
    if walked == 0:
        return None
    loss = _net_loss(first_victim, steps, depth)
    if credit is not None and len(steps) <= depth:
        return loss - credit  # the line ended on an opponent capture inside the walk: settled
    mated = any(step.blunderer_mated for step in steps[:depth])
    if walked >= depth or mated:
        return loss
    return None


def _mate_ply(steps: list[_Step]) -> int | None:
    """1-based line ply after which the blunderer is checkmated, else None."""
    for ply, step in enumerate(steps, start=1):
        if step.blunderer_mated:
            return ply
    return None


def line_facts(pre_board: chess.Board, played_uci: str, pv: str | None) -> LineFacts:
    """Line material facts for one blunder (no I/O, `pre_board` is never mutated).

    `pre_board` is the position before the blunder (blunderer to move), `played_uci` the
    blunder and `pv` the stored line from the position after it. A missing line, a
    malformed or illegal played move or first token gives all-None facts.
    """
    if not pv:
        return null_line_facts()
    played = _parse_move(played_uci)
    if played is None or played not in pre_board.legal_moves:
        return null_line_facts()
    board = pre_board.copy(stack=False)
    blunderer = board.turn
    first_victim = _victim_value(board, played)
    board.push(played)
    steps, end_board = _replay_line(board, pv.split(_PV_SEPARATOR), blunderer)
    if not steps:
        return null_line_facts()
    credit = _recapture_credit(steps, end_board)
    return LineFacts(
        loss_by_depth={
            depth: _loss_at_depth(first_victim, steps, depth, credit) for depth in LINE_LOSS_DEPTHS
        },
        mate_ply=_mate_ply(steps),
    )
