"""Node-budget engine call contract tests.

Tests the evaluate_nodes() module-level function and EnginePool.evaluate_nodes()
method. The node-budget path uses chess.engine.Limit(nodes=1_000_000)
instead of Limit(depth=15); timeout is 5.0s (_NODES_TIMEOUT_S) rather than 2.0s.
"""

import asyncio
import os
from unittest.mock import patch

import chess
import chess.engine
import pytest

from app.services.engine import (
    _HASH_MB,
    _NODES_BUDGET,
    _STOCKFISH_PATH,
    _THREADS,
    _collect_analysis_infos,
    _engine_popen_kwargs,
    evaluate_nodes,
)
from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS
from tests.services.engine_fakes import ScriptedAnalysisProtocol, make_info, make_pool

# Reuse the same stockfish-presence detection as test_engine.py.
stockfish_missing = not (os.path.isfile(_STOCKFISH_PATH) and os.access(_STOCKFISH_PATH, os.X_OK))
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish binary not found")

# Known position for real-engine smoke test
KQ_VS_K_WHITE_WINS = "8/8/8/8/8/8/4Q3/4K2k w - - 0 1"
# A dense middlegame (not a trivially-resolved endgame) so a 1M-node search
# cannot finish inside the sub-second cancellation window below.
DENSE_MIDDLEGAME_FEN = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1"

# ─── Constants (CLAUDE.md: no magic numbers) ──────────────────────────────────
# A chess.com custom-position root Stockfish dies on.
SIXTEEN_WHITE_PAWNS_FEN = "rnbqkbnr/pppppppp/8/8/8/PPPPPPPP/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EXPECTED_NONE_RESULT: tuple[None, None] = (None, None)
MOCK_EVAL_CP: int = 150
# Cancellation-safety probe budgets.
_CANCEL_PROBE_TIMEOUT_S: float = 0.05  # forces asyncio.wait_for to cancel mid-search
_REUSE_PROBE_DEPTH: int = 6  # cheap second search on the SAME protocol
_REUSE_PROBE_TIMEOUT_S: float = 10.0  # generous: a desync would hang, not be slow
_WARMUP_PROBE_DEPTH: int = 4  # gets `ucinewgame`/`isready` out of the way first


class TestEvaluateNodesPoolUnset:
    """Tests that run unconditionally — no Stockfish binary required.

    Mirrors TestEngineNotStarted in test_engine.py. Tests the not-started branch
    which is independent of binary presence.

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
    a real Stockfish binary.
    """

    async def test_evaluate_nodes_uses_limit_nodes(self) -> None:
        """evaluate_nodes() calls protocol.analysis with Limit(nodes=1_000_000).

        Records the Limit instance passed to analysis() and asserts nodes=1_000_000
        is used, NOT depth. This is the core contract.
        """
        protocol = ScriptedAnalysisProtocol([make_info(15, cp=MOCK_EVAL_CP, pv="e2e4")])
        pool = make_pool(protocol)

        board = chess.Board()
        await pool.evaluate_nodes(board)

        assert len(protocol.calls) == 1, "Expected exactly one analysis() call"
        limit, _multipv = protocol.calls[0]
        assert limit.nodes == _NODES_BUDGET, (
            f"Expected nodes={_NODES_BUDGET}, got nodes={limit.nodes}"
        )
        assert limit.depth is None, (
            f"Expected depth=None (not a depth-limited call), got depth={limit.depth}"
        )

    async def test_evaluate_nodes_timeout_returns_none_without_restart(self) -> None:
        """evaluate_nodes() returns (None, None) on TimeoutError WITHOUT restarting.

        A timeout means
        the box is slow, not that the engine is broken, so the worker is kept and
        only its slot is released. Restarting spawned a fresh Stockfish process on
        an already-overloaded machine and amplified one slow position into a block
        of holes.

        The contrast test is test_evaluate_nodes_engine_error_returns_none, which
        asserts a genuine EngineError DOES still restart — together the two are the
        regression test for the split except handlers.
        """
        # Hang mode: a search that never finishes (a hung engine).
        protocol = ScriptedAnalysisProtocol(mode="hang")
        pool = make_pool(protocol)

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
        assert not restart_called, (
            "260725-da3: a timeout must NOT restart the worker — a slow box is not a "
            "broken engine, and restarting amplifies holes (FLAWCHESS-8B)"
        )
        assert protocol.stop_calls == 1, "timeout must send UCI stop via `with analysis:`"
        assert pool._available.qsize() == 1, "slot must be released after a timeout"

    async def test_evaluate_nodes_engine_error_returns_none(self) -> None:
        """evaluate_nodes() returns (None, None) on chess.engine.EngineError."""
        protocol = ScriptedAnalysisProtocol(
            mode="error", error=chess.engine.EngineError("mock engine error")
        )
        pool = make_pool(protocol)

        restart_called = False

        async def mock_restart(idx: int) -> bool:
            nonlocal restart_called
            restart_called = True
            return True

        pool._restart_worker = mock_restart  # ty: ignore[invalid-assignment]

        # An engine crash must reach Sentry — the caller
        # only ever sees None, so the restart path was the only witness.
        with patch("app.services.engine.sentry_sdk.capture_exception") as capture:
            result = await pool.evaluate_nodes(chess.Board())
        assert result == EXPECTED_NONE_RESULT
        assert restart_called
        assert capture.call_count == 1
        assert isinstance(capture.call_args.args[0], chess.engine.EngineError)

    async def test_invalid_board_never_reaches_the_engine(self) -> None:
        """An impossible position (16 white pawns) returns (None, None) without
        calling protocol.analysis and without consuming the worker slot.

        Stockfish dies on such boards
        (chess.com custom-position games), taking a pool worker with it.
        """
        protocol = ScriptedAnalysisProtocol([make_info(15, cp=MOCK_EVAL_CP, pv="e2e4")])
        pool = make_pool(protocol)

        board = chess.Board(SIXTEEN_WHITE_PAWNS_FEN)
        assert not board.is_valid()

        result = await pool.evaluate_nodes(board)

        assert result == EXPECTED_NONE_RESULT
        assert protocol.calls == [], "invalid board must never reach protocol.analysis"
        assert pool._available.qsize() == 1, "worker slot must not be consumed"

    async def test_restart_worker_spawn_failure_captures_and_marks_slot_dead(self) -> None:
        """A failed respawn returns False, nulls the slot, and reaches Sentry.

        The slot stays permanently dead afterwards (every
        pickup returns None), which used to be invisible outside a log line.
        """
        from app.services.engine import EnginePool

        pool = EnginePool(size=1)
        pool._started = True
        pool._transports = [None]
        pool._protocols = [None]

        async def failing_popen(*args: object, **kwargs: object) -> object:
            raise OSError("stockfish binary missing")

        with (
            patch("chess.engine.popen_uci", failing_popen),
            patch("app.services.engine.sentry_sdk.capture_exception") as capture,
        ):
            ok = await pool._restart_worker(0)

        assert ok is False
        assert pool._protocols[0] is None
        assert capture.call_count == 1
        assert isinstance(capture.call_args.args[0], OSError)

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

    async def test_protocol_reusable_after_cancelled_analyse(self) -> None:
        """A cancelled search leaves the UCI protocol usable for the NEXT one.

        This is the correctness gate for skipping
        `_restart_worker` on `asyncio.TimeoutError`. Keeping a slot after a
        timeout is only safe if the cancellation does NOT desync the protocol,
        so this asserts it against the real binary rather than assuming it.

        The pool path is `_collect_analysis_infos` (`Protocol.analysis` plus
        `with analysis:`), which this test cancels under `asyncio.wait_for`.

        Why it holds (python-chess 1.11.2 source):
          - `with analysis:` exits through `AnalysisResult.__exit__` -> `.stop()` ->
            the `stop` hook installed by `UciAnalysisCommand.start`, which sends
            UCI `stop` (only if the end marker was not posted yet).
          - Stockfish answers `stop` with `bestmove`, which reaches
            `UciAnalysisCommand._bestmove` -> `set_finished()` -> resolves the
            command's `finished` future.
          - `Protocol.communicate` queues the NEXT command as `next_command` and
            only starts it once that `finished` future resolves, i.e. AFTER the
            stale `bestmove`. The next search is therefore serialized behind it
            instead of racing it.
        """
        transport, protocol = await chess.engine.popen_uci(
            _STOCKFISH_PATH, **_engine_popen_kwargs()
        )
        try:
            await protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})

            # Warm up so `first_game` is False: the very first analysis on a fresh
            # protocol sends `ucinewgame`/`isready` and only resolves its result
            # future from the async `readyok` handler, which is a different (and
            # much narrower) cancellation window than the steady-state one the
            # pool actually hits.
            await asyncio.wait_for(
                protocol.analyse(chess.Board(), chess.engine.Limit(depth=_WARMUP_PROBE_DEPTH)),
                timeout=_REUSE_PROBE_TIMEOUT_S,
            )

            board = chess.Board(DENSE_MIDDLEGAME_FEN)
            with pytest.raises((asyncio.TimeoutError, TimeoutError)):
                await asyncio.wait_for(
                    _collect_analysis_infos(
                        protocol, board, chess.engine.Limit(nodes=_NODES_BUDGET), None
                    ),
                    timeout=_CANCEL_PROBE_TIMEOUT_S,
                )

            # No restart, no re-popen: reuse the SAME protocol object. A desynced
            # protocol would hang here (caught by the wait_for) or raise.
            info = await asyncio.wait_for(
                protocol.analyse(board, chess.engine.Limit(depth=_REUSE_PROBE_DEPTH)),
                timeout=_REUSE_PROBE_TIMEOUT_S,
            )
            assert not isinstance(info, list), "expected a scalar InfoDict without multipv"
            score = info.get("score")
            assert score is not None, f"post-cancellation analyse returned no score: {info!r}"
            white = score.white()
            assert white.score() is not None or white.mate() is not None, (
                f"post-cancellation analyse returned an unusable score: {score!r}"
            )
        finally:
            try:
                await protocol.quit()
            except chess.engine.EngineError, chess.engine.EngineTerminatedError, RuntimeError:
                pass
            transport.close()


# Bound-line regression (SEED-261112-s4v). A chance-based smoke check against the real
# binary: planning probe saw 1 of 12 searches end on a 1-ply lowerbound line, with
# last-exact pvs of 8-26 plies. The deterministic proof lives in
# test_engine_bound_lines.py.
REPRO_FEN = "8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34"
BOUND_REGRESSION_ROUNDS: int = 4
BOUND_REGRESSION_TIMEOUT_S: float = 60.0  # generous: SCHED_IDLE starves under -n auto
MAX_TRUNCATED_PV_PLIES: int = 2
BOUND_KEYS: tuple[str, ...] = ("lowerbound", "upperbound")


@skip_if_no_stockfish
class TestRealEngineNoBoundLines:
    """Real 1M-node searches never return a bound line or a 1-2 ply pv."""

    async def test_no_bound_key_and_no_truncated_pv(self) -> None:
        from app.services.engine import EnginePool

        board = chess.Board(REPRO_FEN)
        board.push_uci("e6e7")
        pool = EnginePool(size=1)
        await pool.start()
        try:
            for _ in range(BOUND_REGRESSION_ROUNDS):
                for multipv in (None, 2):
                    result = await pool._acquire_and_analyse(
                        board,
                        chess.engine.Limit(nodes=_NODES_BUDGET),
                        BOUND_REGRESSION_TIMEOUT_S,
                        multipv=multipv,
                    )
                    assert result is not None
                    infos = result if isinstance(result, list) else [result]
                    for info in infos:
                        assert not any(key in info for key in BOUND_KEYS), info
                        assert len(info.get("pv", [])) > MAX_TRUNCATED_PV_PLIES, info
        finally:
            await pool.stop()
