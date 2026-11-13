"""Committed D-02 fixture positions for the line material count (Phase 250, plan 01).

Data only. Each entry is copied from the gitignored exploratory label caches
(``temp/blunder-check/fens.json`` + ``pvs.json`` for label sets 1-5, ``set6-lines.json`` for
set 6): the full FEN before the blunder (castling and en passant state intact), the blunder
as UCI, and the stored refutation line exactly as it was at label time. Game links only in
the label study, no usernames. The expected values are the output of the reference
``capture_loss`` (``temp/blunder-check/refine.py``) at depths 1 / 3 / 5 / 7 / 9, checked
against these exact strings before they were committed.

The tests never read the caches: they are gitignored and exist on one machine only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineFixture:
    """One labelled blunder: position, played move, stored line and the expected facts."""

    label_n: int
    pre_fen: str
    played_uci: str
    line: str
    expected_loss: tuple[int | None, ...]  # aligned with LINE_LOSS_DEPTHS
    expected_mate_ply: int | None
    note: str


LINE_FIXTURES: tuple[LineFixture, ...] = (
    LineFixture(
        label_n=13,
        pre_fen="rnbqk2r/ppp3pp/4p1n1/3Ppp2/1bP5/2N2N2/P4PPP/R1BQKB1R w KQkq - 0 9",
        played_uci="c1g5",
        line="b4c3 g5d2 c3d2 d1d2 e5e4 f3d4 e6e5 d4b5 a7a6 b5c3 e8g8 h2h4",
        expected_loss=(3, 0, 0, 0, 0),
        expected_mate_ply=None,
        note="fair position the refinements dropped: the opponent wins a knight at ply 1 and the blunderer recaptures by depth 3",
    ),
    LineFixture(
        label_n=35,
        pre_fen="8/6pk/1R3pp1/1p6/2Pp1PP1/p2P2B1/PP4B1/5K2 w - - 0 33",
        played_uci="c4b5",
        line="a3b2 g2e4 b2b1q f1g2 b1d1 b6c6 d1e2 g2h3 h7h8 b5b6 f6f5 g4f5",
        expected_loss=(0, 0, 0, 0, 0),
        expected_mate_ply=None,
        note="fair position the refinements dropped: the blunder captures a pawn and the count stays at zero",
    ),
    LineFixture(
        label_n=153,
        pre_fen="r1bqk1r1/ppp5/5pNp/3ppn2/6Q1/8/PPPN1PPP/R3R1K1 w q - 0 15",
        played_uci="g4a4",
        line="c8d7 a4b3 g8g6 g1h1 d7e6 f2f4 d8d6 b3b7 a8d8 f4e5 f6e5 c2c4",
        expected_loss=(0, 3, 3, 2, 1),
        expected_mate_ply=None,
        note="unfair passer: the piece was already hanging before the blunder",
    ),
    LineFixture(
        label_n=154,
        pre_fen="2kr2r1/ppqbpp2/5p2/PNpP3p/2P2n2/4Q3/1P3PPP/2R1RB1K b - - 1 22",
        played_uci="c7b8",
        line="e3c5 d7c6 d5c6 d8d6 c6b7 c8d8 b5d6 e7d6 c5f5 b8b7 f5f4 b7c7",
        expected_loss=(1, 1, 2, 4, 3),
        expected_mate_ply=None,
        note="fair position the refinements dropped: the loss grows with depth",
    ),
    LineFixture(
        label_n=156,
        pre_fen="r2qk2r/ppp2ppp/5n2/8/2Q2B1b/3P1P2/PPPK3P/R6R w kq - 3 16",
        played_uci="c4a4",
        line="d8d7 a1e1 h4e1 h1e1 e8d8 a4b4 b7b6 b4c4 h8e8 f4c7 d7c7 e1e8",
        expected_loss=(0, -3, -3, -3, -4),
        expected_mate_ply=None,
        note="unfair passer removed by the desperado rule (material given up by the blunderer's own line move)",
    ),
    LineFixture(
        label_n=165,
        pre_fen="r1bqkb1r/pppp1ppp/5n2/4n3/3pP3/1QP5/PP2BPPP/RNB1K1NR b KQkq - 6 6",
        played_uci="f6e4",
        line="b3d5 d8e7 d5e4 d4d3 g1f3 f7f6 e2d1 d7d5 e4e3 e5c4 e3e7 f8e7",
        expected_loss=(-1, 2, 2, 2, 2),
        expected_mate_ply=None,
        note="unfair passer: two-move pin wins the knight, judged too hard at 777",
    ),
    LineFixture(
        label_n=170,
        pre_fen="6r1/1r4P1/7p/2k5/2P2R2/p1K2P2/P4P2/6R1 b - - 1 34",
        played_uci="b7b2",
        line="g1g6 b2c2 c3c2 c5b4 f4f5 g8d8 g7g8q d8g8 g6g8 h6h5 c2d3 h5h4",
        expected_loss=(0, 0, 0, -9, -4),
        expected_mate_ply=None,
        note="unfair passer removed by the desperado rule (spite capture in a lost position)",
    ),
    LineFixture(
        label_n=176,
        pre_fen="8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34",
        played_uci="e6e7",
        line="h7e7",
        expected_loss=(0, 0, 0, 0, 0),
        expected_mate_ply=None,
        note="computation artifact: one-move stored line, settled by the static-exchange recapture credit",
    ),
    LineFixture(
        label_n=177,
        pre_fen="8/P1N1k3/7p/2KbN3/1P4pr/8/2P2p2/8 w - - 0 54",
        played_uci="c5d5",
        line="f2f1q e5c6 e7f6 c7e8 f6g5 a7a8q g4g3 a8d8 g5g4 d8d7 g4f3 d7f5",
        expected_loss=(-3, -3, -3, -3, -3),
        expected_mate_ply=None,
        note="unfair passer removed: the opponent 'material' is a promotion in an endgame race",
    ),
    LineFixture(
        label_n=184,
        pre_fen="r2qk1nr/ppp2ppp/3p4/2b1p3/2BnP1b1/2NP1N2/PPP1QPPP/R1B1K2R w KQkq - 3 7",
        played_uci="e2d2",
        line="g4f3 c3b5 d4b5 c4b5 c7c6 b5c6 b7c6 g2f3 d8h4 h1g1 g8e7 g1g4",
        expected_loss=(3, 0, -1, -1, -1),
        expected_mate_ply=None,
        note="fair position the refinements dropped: the opponent wins a knight at ply 1, regained by depth 5",
    ),
    LineFixture(
        label_n=34,
        pre_fen="r2qk2r/ppp2ppp/1b1p4/8/1PP1P1Q1/P1BP4/5PPP/R4RK1 b kq - 0 14",
        played_uci="e8g8",
        line="g4g7",
        expected_loss=(1, 1, 1, 1, 1),
        expected_mate_ply=1,
        note="1-ply mate line",
    ),
    LineFixture(
        label_n=108,
        pre_fen="r3k2r/pp2p2p/2p3p1/2n2bB1/6P1/1P6/P1P1QP1P/b3KB1R b Kkq - 0 16",
        played_uci="f5c2",
        line="e2e7",
        expected_loss=(0, 0, 0, 0, 0),
        expected_mate_ply=1,
        note="1-ply mate line, count 0 (mate dominates)",
    ),
    LineFixture(
        label_n=116,
        pre_fen="r1bqk2r/pppp1p1p/2n3p1/2bBp3/4P3/5Q2/PPPP1PPP/R1B1K1NR b KQkq - 0 7",
        played_uci="c6d4",
        line="f3f7",
        expected_loss=(1, 1, 1, 1, 1),
        expected_mate_ply=1,
        note="1-ply mate line",
    ),
    LineFixture(
        label_n=162,
        pre_fen="5r1k/QP4p1/7p/3B1q2/3p4/5PP1/8/6RK w - - 1 36",
        played_uci="b7b8q",
        line="f5h3",
        expected_loss=(0, 0, 0, 0, 0),
        expected_mate_ply=1,
        note="1-ply mate line after a promotion blunder",
    ),
    LineFixture(
        label_n=168,
        pre_fen="6k1/8/R5PK/7P/8/8/p5r1/8 b - - 2 51",
        played_uci="g2h2",
        line="a6a8",
        expected_loss=(0, 0, 0, 0, 0),
        expected_mate_ply=1,
        note="1-ply mate line, count 0",
    ),
    LineFixture(
        label_n=181,
        pre_fen="2k4r/ppp5/2n2p2/1N3q1p/2Q4P/5Pp1/PPnrN1P1/2R2K1R w - - 3 23",
        played_uci="c1c2",
        line="d2d1",
        expected_loss=(-3, -3, -3, -3, -3),
        expected_mate_ply=1,
        note="1-ply mate line, blunderer is up material at the mate",
    ),
    LineFixture(
        label_n=182,
        pre_fen="r4rk1/1b3pbp/p1qppnp1/1p4B1/4P3/P1N4P/BPP2PP1/R2QR1K1 w - - 2 15",
        played_uci="e4e5",
        line="c6g2",
        expected_loss=(1, 1, 1, 1, 1),
        expected_mate_ply=1,
        note="1-ply mate line",
    ),
)
