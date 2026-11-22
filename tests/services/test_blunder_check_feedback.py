"""Tests for app/services/blunder_check_feedback.py (Phase 261 plan 01).

Coverage:
- allowed side : swing at the deepest settled odd depth on the committed label fixtures (D-08)
- short line   : a truncated line gives the last depth it still settles (D-08)
- mate         : mate counts only when the stored line reaches it, on the type side alone (D-09)
- missed side  : material swing from the owner miss fixtures, no swing for a lone non-mating best move (D-12)
- type side    : the other side's mate is never reported (seed "type line side")
- feedback     : the read-time decision, floor and hard-to-catch cut (seed "type line floor", D-06)

Fixtures are reused by label from tests/services/line_material_fixtures.py, never copied.
"""

from __future__ import annotations

import chess
import pytest

from app.services import blunder_check_feedback as feedback
from app.services import blunder_check_rules as rules
from app.services.blunder_check_feedback import TypeLineFacts, type_line_facts
from app.services.facepalm_material import loss_by_depth
from app.services.line_material import quiet_line_facts
from tests.services.line_material_fixtures import (
    LINE_FIXTURES,
    OWNER_MISS_FIXTURES,
    LineFixture,
    OwnerMissFixture,
)

_LINE_BY_LABEL: dict[int, LineFixture] = {f.label_n: f for f in LINE_FIXTURES}
_MISS_BY_GAME: dict[int, OwnerMissFixture] = {f.game_id: f for f in OWNER_MISS_FIXTURES}

# Plies of the label 154 line that settle depths 1 and 3 but not 5 (a short stored line).
_SHORT_LINE_TOKENS = 4
_SCHOLARS_PREFIX = "e2e4 e7e5 d1h5 b8c6"
_FOOLS_PREFIX = "f2f3 e7e5 g2g4"


def _board_after(moves: str) -> chess.Board:
    board = chess.Board()
    for uci in moves.split():
        board.push_uci(uci)
    return board


def _allowed(label: int, line: str | None = None) -> TypeLineFacts:
    fixture = _LINE_BY_LABEL[label]
    return type_line_facts(
        chess.Board(fixture.pre_fen),
        fixture.played_uci,
        fixture.line if line is None else line,
        None,
        "allowed_loss",
    )


@pytest.mark.parametrize(
    ("label", "swing"),
    [(13, 0), (154, 5), (153, 2)],
    ids=["won-back", "capped-loss", "late-loss"],
)
def test_allowed_swing_is_the_deepest_settled_depth(label: int, swing: int) -> None:
    facts = _allowed(label)
    assert facts.swing == swing
    assert facts.mate is False


def test_short_line_reads_the_last_settled_depth() -> None:
    fixture = _LINE_BY_LABEL[154]
    line = " ".join(fixture.line.split()[:_SHORT_LINE_TOKENS])
    played = quiet_line_facts(chess.Board(fixture.pre_fen), fixture.played_uci, line)
    series = loss_by_depth(played.material_array(), played.mate_ply, loss_floor=0)
    # The series holds depths 1, 3, 5, 7, 9 in that order.
    assert series[1] == 1.0, "depth 3 settles"
    assert series[2] is None, "depth 5 does not"
    assert _allowed(154, line).swing == 1


def test_allowed_mate_on_the_label_fixture() -> None:
    facts = _allowed(34)
    assert facts.mate is True


@pytest.mark.parametrize(
    ("prefix", "best_line"),
    [(_SCHOLARS_PREFIX, "f1c4 g8f6 h5f7"), (_FOOLS_PREFIX, "d8h4")],
    ids=["line-mate", "best-move-mates"],
)
def test_missed_mate_when_the_stored_best_line_mates(prefix: str, best_line: str) -> None:
    facts = type_line_facts(_board_after(prefix), "a7a6", "d1h5", best_line, "missed_win")
    assert facts.mate is True


@pytest.mark.parametrize("game_id", sorted(_MISS_BY_GAME), ids=lambda g: f"g{g}")
def test_missed_material_swing_reaches_the_floor(game_id: int) -> None:
    fixture = _MISS_BY_GAME[game_id]
    facts = type_line_facts(
        chess.Board(fixture.pre_fen),
        fixture.played_uci,
        fixture.refutation_line,
        fixture.best_line,
        "missed_win",
    )
    assert facts.mate is False
    assert facts.swing is not None
    assert facts.swing >= 2
    assert facts.swing == fixture.expected_best_3 - max(0, fixture.expected_played_3)


def test_lone_non_mating_best_move_gives_no_missed_swing() -> None:
    fixture = _MISS_BY_GAME[817357]
    lone_best_move = fixture.best_line.split()[0]
    facts = type_line_facts(
        chess.Board(fixture.pre_fen),
        fixture.played_uci,
        fixture.refutation_line,
        lone_best_move,
        "missed_win",
    )
    assert facts == TypeLineFacts(swing=None, mate=False)


def test_allowed_loss_never_reports_the_best_line_mate() -> None:
    # The best move d8h4 mates in the board after Fool's mate setup, but the type side is the loss.
    facts = type_line_facts(_board_after(_FOOLS_PREFIX), "a7a6", "d1h5", "d8h4", "allowed_loss")
    assert facts.mate is False


def test_missed_win_never_reports_the_played_line_mate() -> None:
    fixture = _LINE_BY_LABEL[34]
    facts = type_line_facts(
        chess.Board(fixture.pre_fen), fixture.played_uci, fixture.line, None, "missed_win"
    )
    assert facts.mate is False


def test_no_snapshot_gives_no_feedback() -> None:
    assert (
        feedback.blunder_feedback(
            score=None, loss=None, missed=None, type_swing=None, type_mate=None
        )
        is None
    )


@pytest.mark.parametrize(
    ("loss", "missed", "expected"),
    [(3.0, 0.0, "allowed_mate"), (0.0, 3.0, "missed_mate")],
)
def test_mate_wins_over_a_small_swing(loss: float, missed: float, expected: str) -> None:
    data = feedback.blunder_feedback(
        score=0.9, loss=loss, missed=missed, type_swing=1, type_mate=True
    )
    assert data is not None
    assert data.type_line == expected


@pytest.mark.parametrize(
    ("loss", "missed", "expected"),
    [(3.0, 0.0, "allowed_material"), (0.0, 3.0, "missed_material")],
)
def test_swing_at_the_floor_gives_the_material_line(
    loss: float, missed: float, expected: str
) -> None:
    data = feedback.blunder_feedback(
        score=0.9, loss=loss, missed=missed, type_swing=rules.TYPE_LINE_MIN_SWING, type_mate=False
    )
    assert data is not None
    assert data.type_line == expected


@pytest.mark.parametrize(
    "swing", [rules.TYPE_LINE_MIN_SWING - 1, None], ids=["below-floor", "unknown"]
)
def test_swing_below_the_floor_gives_no_line(swing: int | None) -> None:
    data = feedback.blunder_feedback(
        score=0.9, loss=3.0, missed=0.0, type_swing=swing, type_mate=False
    )
    assert data is not None
    assert data.type_line is None


def test_a_tie_is_the_allowed_side() -> None:
    # 257 D-02: loss == missed > 0 is an allowed loss, so the line names the loss, not the miss.
    data = feedback.blunder_feedback(score=0.9, loss=2.0, missed=2.0, type_swing=3, type_mate=False)
    assert data is not None
    assert data.type_line == "allowed_material"


def test_floor_is_a_read_time_constant() -> None:
    # The stored swing is raw: the floor only decides what is shown, never what is stored.
    assert rules.TYPE_LINE_MIN_SWING == 2
    assert _allowed(13).swing == 0, "a swing under the floor is stored as is"


@pytest.mark.parametrize(
    ("score", "hard"),
    [(0.4999, True), (rules.HARD_TO_CATCH_SCORE_BELOW, False), (0.95, False)],
    ids=["just-below", "at-the-cut", "high"],
)
def test_hard_to_catch_is_a_score_below_the_cut(score: float, hard: bool) -> None:
    data = feedback.blunder_feedback(
        score=score, loss=3.0, missed=0.0, type_swing=3, type_mate=False
    )
    assert data is not None
    assert data.hard_to_catch is hard
    assert data.score == score
