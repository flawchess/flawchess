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

Phase 254 (D-09): the same counting rules also run for the BEST line (``best_line_facts``: the
best move is the first move, the rest of ``game_positions.pv`` at the flaw ply is its line).
Facts expose a 9-slot signed array indexed by depth (``material_array``, slot N = depth N);
even depths are mid-exchange values (see ``LINE_MATERIAL_SLOTS``). Material is signed, positive =
the blunderer is up (``material_at(depth) == -loss_at(depth)``). Ply convention: the first move
(the blunder, or the best move) is ply 0, so line ply N is the Nth token of the stored line. A mate of either side inside the walked line settles
the depth; ``opponent_mate_ply`` is the ply after which the opponent is mated (a best move that
mates itself has ply 0, mate-in-2 has ply 2).

No I/O. The score that consumes these facts lives in ``app/services/facepalm_score.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import chess

# Odd depths (plies of the stored line) the Phase 250 fixtures are aligned with (D-05); the score
# reads the depth-3 slot of the signed arrays.
LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)

# Slots of the signed material arrays (D-09, D-17): slot N (1-based) = net material at depth N.
# Even depths are mid-exchange values: `_net_loss` takes only a blunderer capture at depth + 1,
# which at an even depth is an opponent ply, so the opponent's reply to the blunderer's last move
# is not counted yet (optimistic for the blunderer). Computed with the same counting rule, not
# "fixed", because nothing in the D-05 score reads them (research Pitfall 14).
LINE_MATERIAL_SLOTS: int = 9
LINE_MATERIAL_DEPTHS: tuple[int, ...] = tuple(range(1, LINE_MATERIAL_SLOTS + 1))

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
_MAX_WALK_PLIES: int = max(LINE_MATERIAL_DEPTHS) + 1


@dataclass(frozen=True, slots=True)
class LineFacts:
    """Net loss per stored depth and the mate plies, each None when not settled (D-05, D-09)."""

    loss_by_depth: Mapping[int, int | None]
    mate_ply: int | None
    # Ply after which the OPPONENT is mated, the first move counted as ply 0 (D-09); None if never.
    opponent_mate_ply: int | None = None

    def loss_at(self, depth: int) -> int | None:
        """Net material loss at `depth` plies; None when the line is too short to tell."""
        return self.loss_by_depth.get(depth)

    def material_at(self, depth: int) -> int | None:
        """Signed net material at `depth` plies (positive = blunderer up); None when not settled."""
        loss = self.loss_at(depth)
        return None if loss is None else -loss

    def material_array(self) -> list[int | None]:
        """Signed net material for depths 1..9 (slot N - 1 = depth N; positive = blunderer up)."""
        return [self.material_at(depth) for depth in LINE_MATERIAL_DEPTHS]


def material_at_depth(material: Sequence[int | None] | None, depth: int) -> int | None:
    """Signed material at `depth` read from a stored array; None for a missing or short array.

    Stored arrays are 1-based in Postgres (`array[3]` = depth 3); the Python list is 0-based.
    """
    if material is None or not 1 <= depth <= len(material):
        return None
    return material[depth - 1]


def null_line_facts() -> LineFacts:
    """Every depth None and no mate (a blunder with no usable stored line)."""
    return LineFacts(loss_by_depth=dict.fromkeys(LINE_MATERIAL_DEPTHS), mate_ply=None)


@dataclass(frozen=True, slots=True)
class _Step:
    """One legal ply of the stored line, as seen from the blunderer."""

    opponent_move: bool
    victim_value: int
    to_square: int
    blunderer_mated: bool
    opponent_mated: bool


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
        checkmate = board.is_checkmate()
        blunderer_mated = checkmate and board.turn == blunderer
        opponent_mated = checkmate and board.turn != blunderer
        steps.append(_Step(opponent_move, victim, move.to_square, blunderer_mated, opponent_mated))
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
    # A mate of EITHER side inside the walked line settles the depth (D-09: a best line may end
    # in the opponent's mate, which is not "line too short to tell").
    mated = any(step.blunderer_mated or step.opponent_mated for step in steps[:depth])
    if walked >= depth or mated:
        return loss
    return None


def _mate_ply(steps: list[_Step]) -> int | None:
    """1-based line ply after which the blunderer is checkmated, else None."""
    for ply, step in enumerate(steps, start=1):
        if step.blunderer_mated:
            return ply
    return None


def _opponent_mate_ply(steps: list[_Step]) -> int | None:
    """Ply after which the opponent is checkmated, the first move being ply 0, else None."""
    for ply, step in enumerate(steps, start=1):
        if step.opponent_mated:
            return ply
    return None


def _facts_after_first_move(
    pre_board: chess.Board, first: chess.Move, rest: list[str]
) -> LineFacts:
    """Shared counting for the played line and the best line (the 250 D-02 rules exist once).

    `first` is the blunderer's first move (the blunder, or the best move), already known to be
    legal on `pre_board`; `rest` the UCI tokens of the line that follows it. A first move that
    mates settles every depth at its capture value with opponent_mate_ply 0 (Pitfall 2).
    """
    board = pre_board.copy(stack=False)
    blunderer = board.turn
    first_victim = _victim_value(board, first)
    board.push(first)
    if board.is_checkmate():
        return LineFacts(
            loss_by_depth=dict.fromkeys(LINE_MATERIAL_DEPTHS, -first_victim),
            mate_ply=None,
            opponent_mate_ply=0,
        )
    steps, end_board = _replay_line(board, rest, blunderer)
    if not steps:
        return null_line_facts()
    credit = _recapture_credit(steps, end_board)
    return LineFacts(
        loss_by_depth={
            depth: _loss_at_depth(first_victim, steps, depth, credit)
            for depth in LINE_MATERIAL_DEPTHS
        },
        mate_ply=_mate_ply(steps),
        opponent_mate_ply=_opponent_mate_ply(steps),
    )


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
    return _facts_after_first_move(pre_board, played, pv.split(_PV_SEPARATOR))


def best_line_facts(pre_board: chess.Board, best_pv: str | None) -> LineFacts:
    """Line material facts for the best line (D-09; no I/O, `pre_board` is never mutated).

    `best_pv` is `game_positions.pv` at the flaw ply: the best move first, then its line. The
    same counting rules as `line_facts` apply with the best move as the first move. A missing,
    empty, malformed or illegal best line gives all-None facts and never raises; a best move
    that mates settles every depth with opponent_mate_ply 0, while a non-mating one-token line
    is "too short to tell" (None).
    """
    if not best_pv:
        return null_line_facts()
    tokens = best_pv.split(_PV_SEPARATOR)
    best = _parse_move(tokens[0])
    if best is None or best not in pre_board.legal_moves:
        return null_line_facts()
    return _facts_after_first_move(pre_board, best, tokens[1:])
