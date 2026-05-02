"""Engine wrapper contract tests (ENG-02). Phase 78 Wave 0."""
import shutil

import chess
import pytest

from app.services.engine import evaluate
from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

stockfish_missing = shutil.which("stockfish") is None
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish not on PATH")

# Known positions (chosen for deterministic depth-15 outcome)
KQ_VS_K_WHITE_WINS = "8/8/8/8/8/8/4Q3/4K2k w - - 0 1"
K_VS_Q_BLACK_WINS = "8/8/8/8/8/8/4q3/4k2K w - - 0 1"  # white to move, severely losing
NEAR_EQUAL_AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
# Forced mate positions: simple known mate-in-1 positions
MATE_IN_1_WHITE = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"  # Ra8# is mate in 1
MATE_IN_1_BLACK = "1r4k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1"  # Rb1# is mate in 1 for black


@skip_if_no_stockfish
@pytest.mark.usefixtures("engine_started")
class TestEngineWrapper:
    async def test_white_winning_returns_positive_cp(self) -> None:
        cp, mate = await evaluate(chess.Board(KQ_VS_K_WHITE_WINS))
        # Either Stockfish reports cp >= 100, OR it sees the forced mate and reports eval_mate.
        # Both are correct — assert at least one of (cp >= 100, mate is not None and mate > 0).
        assert (cp is not None and cp >= 100) or (mate is not None and mate > 0)

    async def test_black_winning_returns_negative_cp(self) -> None:
        cp, mate = await evaluate(chess.Board(K_VS_Q_BLACK_WINS))
        assert (cp is not None and cp <= -100) or (mate is not None and mate < 0)

    async def test_near_equal_returns_small_cp(self) -> None:
        cp, mate = await evaluate(chess.Board(NEAR_EQUAL_AFTER_E4))
        assert mate is None
        assert cp is not None and abs(cp) < 100

    async def test_mate_for_white_returns_positive_mate(self) -> None:
        cp, mate = await evaluate(chess.Board(MATE_IN_1_WHITE))
        assert mate is not None and mate > 0

    async def test_mate_for_black_returns_negative_mate(self) -> None:
        cp, mate = await evaluate(chess.Board(MATE_IN_1_BLACK))
        assert mate is not None and mate < 0

    async def test_clamp_bounds(self) -> None:
        cp, mate = await evaluate(chess.Board(KQ_VS_K_WHITE_WINS))
        if cp is not None:
            assert -EVAL_CP_MAX_ABS <= cp <= EVAL_CP_MAX_ABS
        if mate is not None:
            assert -EVAL_MATE_MAX_ABS <= mate <= EVAL_MATE_MAX_ABS


class TestEngineNotStarted:
    async def test_evaluate_returns_none_tuple_if_engine_not_started(self) -> None:
        """When start_engine() has not been called, evaluate() degrades to (None, None).

        Required for tests that don't bring up the engine and for the import-time
        graceful-degradation path (D-11).

        NOTE: This test must NOT be marked with @skip_if_no_stockfish — it tests
        the not-started branch which is independent of binary presence.
        NOTE: This test must run in isolation from engine_started (no autouse).
        """
        from app.services.engine import stop_engine

        # Ensure engine is stopped before testing the not-started path.
        # This makes the test resilient to collection order, since session-scoped
        # engine_started may have started the engine earlier in the session.
        await stop_engine()
        cp, mate = await evaluate(chess.Board())
        assert (cp, mate) == (None, None)
