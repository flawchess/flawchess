"""Node-budget engine call contract tests (EVAL-02). Phase 116 Wave 0.

Tests the evaluate_nodes() module-level function and EnginePool.evaluate_nodes()
method introduced in Phase 116. The node-budget path uses chess.engine.Limit(nodes=1_000_000)
instead of Limit(depth=15); timeout is 5.0s (_NODES_TIMEOUT_S) rather than 2.0s.
"""

import asyncio
import os
from unittest.mock import MagicMock, patch

import chess
import chess.engine
import pytest

from app.services.engine import _STOCKFISH_PATH, evaluate_nodes
from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

# Reuse the same stockfish-presence detection as test_engine.py.
stockfish_missing = not (os.path.isfile(_STOCKFISH_PATH) and os.access(_STOCKFISH_PATH, os.X_OK))
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish binary not found")

# Known position for real-engine smoke test
KQ_VS_K_WHITE_WINS = "8/8/8/8/8/8/4Q3/4K2k w - - 0 1"

# ─── Constants (CLAUDE.md: no magic numbers) ──────────────────────────────────
EXPECTED_NONE_RESULT: tuple[None, None] = (None, None)
MOCK_EVAL_CP: int = 150
MOCK_EVAL_MATE: int = 3


class TestEvaluateNodesPoolUnset:
    """Tests that run unconditionally — no Stockfish binary required.

    Mirrors TestEngineNotStarted in test_engine.py. Tests the not-started branch
    which is independent of binary presence (EVAL-02).

    NOTE: We patch the module-level _pool to None instead of calling stop_engine(),
    so we don't destroy the session-scoped engine_started state for other test classes
    running in the same xdist worker session.
    """

    async def test_evaluate_nodes_returns_none_if_pool_unset(self) -> None:
        """evaluate_nodes() returns (None, None) when pool is not started.

        Mirrors test_evaluate_returns_none_tuple_if_engine_not_started.
        Must NOT be marked skip_if_no_stockfish — tests the not-started branch.
        Patches _pool to None instead of calling stop_engine() to avoid
        disrupting the session-scoped engine_started fixture in xdist runs.
        """
        import app.services.engine as engine_module

        with patch.object(engine_module, "_pool", None):
            result = await evaluate_nodes(chess.Board())
        assert result == EXPECTED_NONE_RESULT


class TestEvaluateNodesWithMock:
    """Unit tests using a mocked UciProtocol to verify Limit and timeout behavior.

    These tests verify the exact Limit(nodes=1_000_000) contract without requiring
    a real Stockfish binary — EVAL-02 compliance tests.
    """

    async def test_evaluate_nodes_uses_limit_nodes(self) -> None:
        """evaluate_nodes() calls protocol.analyse with Limit(nodes=1_000_000).

        Records the Limit instance passed to analyse() and asserts nodes=1_000_000
        is used, NOT depth. This is the EVAL-02 core contract.
        """
        from app.services.engine import EnginePool, _NODES_BUDGET

        # Create a pool and mock its internal protocol
        pool = EnginePool(size=1)
        pool._started = True

        # Build a mock InfoDict with a valid score
        mock_score = MagicMock(spec=chess.engine.PovScore)
        mock_white_score = MagicMock()
        mock_white_score.score.return_value = MOCK_EVAL_CP
        mock_white_score.mate.return_value = None
        mock_score.white.return_value = mock_white_score

        mock_info: chess.engine.InfoDict = chess.engine.InfoDict({"score": mock_score})  # type: ignore[misc]

        captured_limits: list[chess.engine.Limit] = []

        async def mock_analyse(
            board: chess.Board,
            limit: chess.engine.Limit,
            *args: object,
            **kwargs: object,
        ) -> chess.engine.InfoDict:
            captured_limits.append(limit)
            return mock_info

        mock_protocol = MagicMock(spec=chess.engine.UciProtocol)
        mock_protocol.analyse = mock_analyse

        pool._transports = [None]
        pool._protocols = [mock_protocol]
        pool._available.put_nowait(0)

        board = chess.Board()
        await pool.evaluate_nodes(board)

        assert len(captured_limits) == 1, "Expected exactly one analyse() call"
        limit = captured_limits[0]
        assert limit.nodes == _NODES_BUDGET, (
            f"Expected nodes={_NODES_BUDGET}, got nodes={limit.nodes}"
        )
        assert limit.depth is None, (
            f"Expected depth=None (not a depth-limited call), got depth={limit.depth}"
        )

    async def test_evaluate_nodes_timeout_returns_none(self) -> None:
        """evaluate_nodes() returns (None, None) and restarts worker on TimeoutError.

        When asyncio.wait_for times out, the worker must be restarted and
        (None, None) must be returned. Same contract as EnginePool.evaluate().
        """
        from app.services.engine import EnginePool

        pool = EnginePool(size=1)
        pool._started = True

        async def mock_analyse_slow(
            board: chess.Board,
            limit: chess.engine.Limit,
            *args: object,
            **kwargs: object,
        ) -> chess.engine.InfoDict:
            # Simulate a hung engine by sleeping longer than _NODES_TIMEOUT_S
            await asyncio.sleep(9999)
            raise AssertionError("Should have been cancelled before this")  # unreachable

        mock_protocol = MagicMock(spec=chess.engine.UciProtocol)
        mock_protocol.analyse = mock_analyse_slow

        pool._transports = [None]
        pool._protocols = [mock_protocol]
        pool._available.put_nowait(0)

        # Patch _restart_worker to avoid spawning a real process
        restart_called = False

        async def mock_restart(idx: int) -> bool:
            nonlocal restart_called
            restart_called = True
            return True

        pool._restart_worker = mock_restart  # ty: ignore[invalid-assignment]

        # Patch _NODES_TIMEOUT_S to a near-zero value so the test doesn't actually wait 5s
        with patch("app.services.engine._NODES_TIMEOUT_S", 0.01):
            result = await pool.evaluate_nodes(chess.Board())

        assert result == EXPECTED_NONE_RESULT, f"Expected (None, None) on timeout, got {result}"
        assert restart_called, "Expected _restart_worker to be called on timeout"

    async def test_evaluate_nodes_engine_error_returns_none(self) -> None:
        """evaluate_nodes() returns (None, None) on chess.engine.EngineError."""
        from app.services.engine import EnginePool

        pool = EnginePool(size=1)
        pool._started = True

        async def mock_analyse_error(
            board: chess.Board,
            limit: chess.engine.Limit,
            *args: object,
            **kwargs: object,
        ) -> chess.engine.InfoDict:
            raise chess.engine.EngineError("mock engine error")

        mock_protocol = MagicMock(spec=chess.engine.UciProtocol)
        mock_protocol.analyse = mock_analyse_error

        pool._transports = [None]
        pool._protocols = [mock_protocol]
        pool._available.put_nowait(0)

        restart_called = False

        async def mock_restart(idx: int) -> bool:
            nonlocal restart_called
            restart_called = True
            return True

        pool._restart_worker = mock_restart  # ty: ignore[invalid-assignment]

        result = await pool.evaluate_nodes(chess.Board())
        assert result == EXPECTED_NONE_RESULT
        assert restart_called

    async def test_evaluate_nodes_null_protocol_returns_none(self) -> None:
        """evaluate_nodes() returns (None, None) if the worker's protocol is None.

        This models a permanently-failed worker slot (restart returned False).
        """
        from app.services.engine import EnginePool

        pool = EnginePool(size=1)
        pool._started = True
        pool._transports = [None]
        pool._protocols = [None]  # simulates a failed/dead worker
        pool._available.put_nowait(0)

        result = await pool.evaluate_nodes(chess.Board())
        assert result == EXPECTED_NONE_RESULT


@skip_if_no_stockfish
class TestEvaluateNodesRealEngine:
    """Optional integration test requiring real Stockfish binary.

    Skipped cleanly when Stockfish is absent. Uses the module-level evaluate_nodes()
    which routes through the pool started by start_engine(). Each test ensures the
    engine is running before use — start_engine() is idempotent, so calling it after
    a stop_engine() (e.g., from TestEngineNotStarted in another test file) restarts
    the pool safely without requiring the session-scoped engine_started fixture.
    """

    async def test_white_winning_returns_positive_eval(self) -> None:
        """White-winning position returns positive eval_cp through the real budget call.

        At 1M nodes the engine reliably finds the KQ vs K advantage.
        """
        from app.services.engine import start_engine

        await start_engine()
        cp, mate = await evaluate_nodes(chess.Board(KQ_VS_K_WHITE_WINS))
        # Either positive cp OR positive forced-mate — both are correct.
        assert (cp is not None and cp >= 100) or (mate is not None and mate > 0), (
            f"Expected white-winning eval, got cp={cp} mate={mate}"
        )

    async def test_evaluate_nodes_returns_bounded_values(self) -> None:
        """evaluate_nodes() results are within the same clamped range as evaluate()."""
        from app.services.engine import start_engine

        await start_engine()
        cp, mate = await evaluate_nodes(chess.Board(KQ_VS_K_WHITE_WINS))
        if cp is not None:
            assert -EVAL_CP_MAX_ABS <= cp <= EVAL_CP_MAX_ABS
        if mate is not None:
            assert -EVAL_MATE_MAX_ABS <= mate <= EVAL_MATE_MAX_ABS
