"""Deterministic tests for the engine wrapper's "keep the last exact info line" rule.

SEED-261112-s4v: a node-limited Stockfish search can end on a lowerbound/upperbound
info line with a 1-2 ply pv. python-chess's one-shot analyse() merged that line over
the last complete iteration. `_select_final_infos` / `_collect_analysis_infos` read the
raw stream instead. No Stockfish binary needed: the streams are scripted.
"""

from __future__ import annotations

from unittest.mock import patch

import chess
import chess.engine

from app.services.engine import (
    _NODES_BUDGET,
    PV_CAP_PLIES,
    EnginePool,
    _select_final_infos,
)
from tests.services.engine_fakes import (
    ScriptedAnalysisProtocol,
    make_info,
    make_pool,
    make_string_info,
)

# Repro numbers from the planning probe (real sf, 1M nodes, white to move).
EXACT_DEPTH: int = 17
EXACT_CP: int = 302
EXACT_PV_PLIES: int = 24
BOUND_DEPTH: int = 18
BOUND_CP: int = 365
BOUND_PV: str = "h7e7"
SECOND_LINE_CP: int = 150
SHORT_BOUND_PLIES: int = 2
NEAR_ZERO_TIMEOUT_S: float = 0.01
MATE_ROOT_DEPTH: int = 0
MATE_ZERO: int = 0


def _long_pv(plies: int, start_file: int = 0) -> str:
    """A UCI-valid pv string of `plies` distinct moves (legality is not checked)."""
    moves = []
    for i in range(plies):
        file_from = chr(ord("a") + (start_file + i) % 8)
        file_to = chr(ord("a") + (start_file + i + 1) % 8)
        rank = 1 + (i % 7)
        moves.append(f"{file_from}{rank}{file_to}{rank + 1}")
    return " ".join(moves)


EXACT_PV: str = _long_pv(EXACT_PV_PLIES)
SECOND_EXACT_PV: str = _long_pv(10, start_file=3)
REPRO_BOARD_FEN: str = "8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34"


def _repro_board() -> chess.Board:
    board = chess.Board(REPRO_BOARD_FEN)
    board.push_uci("e6e7")
    return board


def _as_list(result: chess.engine.InfoDict | list[chess.engine.InfoDict]) -> list:
    return result if isinstance(result, list) else [result]


class TestSelectFinalInfos:
    def test_trailing_lowerbound_loses_to_last_exact_line(self) -> None:
        exact = make_info(EXACT_DEPTH, cp=EXACT_CP, pv=EXACT_PV)
        bound = make_info(BOUND_DEPTH, cp=BOUND_CP, pv=BOUND_PV, bound="lower")
        result = _select_final_infos([exact, bound], None)
        assert isinstance(result, dict)
        assert result is exact
        assert result["depth"] == EXACT_DEPTH
        assert len(result["pv"]) == EXACT_PV_PLIES
        assert "lowerbound" not in result

    def test_multipv_2_picks_last_exact_per_index_in_order(self) -> None:
        idx1 = make_info(16, cp=EXACT_CP, pv=EXACT_PV, multipv=1)
        idx2 = make_info(16, cp=SECOND_LINE_CP, pv=SECOND_EXACT_PV, multipv=2)
        bound1 = make_info(17, cp=BOUND_CP, pv="h7e7", multipv=1, bound="upper")
        bound2 = make_info(17, cp=BOUND_CP, pv="h7e7 f6e7", multipv=2, bound="lower")
        result = _select_final_infos([idx1, idx2, bound1, bound2], 2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is idx1
        assert result[1] is idx2
        assert all("lowerbound" not in r and "upperbound" not in r for r in result)

    def test_stale_bound_key_does_not_leak_into_later_exact_line(self) -> None:
        # Merged-dict implementations (analysis.info) fail this: dict.update never
        # removes the `lowerbound` key set by the middle line.
        first = make_info(15, cp=EXACT_CP, pv=EXACT_PV)
        bound = make_info(16, cp=BOUND_CP, pv=BOUND_PV, bound="lower")
        final = make_info(16, cp=EXACT_CP, pv=_long_pv(22))
        result = _select_final_infos([first, bound, final], None)
        assert isinstance(result, dict)
        assert result is final
        assert "lowerbound" not in result
        assert len(result["pv"]) == 22

    def test_no_exact_line_falls_back_to_last_bound_line(self) -> None:
        low = make_info(1, cp=10, pv="e2e4", bound="lower")
        high = make_info(2, cp=20, pv="e2e4 e7e5", bound="upper")
        result = _select_final_infos([low, high], None)
        assert result is high
        assert result["depth"] == 2

    def test_pvless_lines_after_exact_line_are_ignored(self) -> None:
        exact = make_info(EXACT_DEPTH, cp=EXACT_CP, pv=EXACT_PV)
        string_line = make_string_info("NNUE evaluation using nn.nnue")
        currmove = make_info(18)
        result = _select_final_infos([exact, string_line, currmove], None)
        assert result is exact

    def test_mated_root_returns_score_only_line(self) -> None:
        mated = make_info(MATE_ROOT_DEPTH, mate=MATE_ZERO)
        result = _select_final_infos([mated], None)
        assert result is mated
        assert "pv" not in result

    def test_only_string_lines_yield_empty_infodict_scalar(self) -> None:
        result = _select_final_infos([make_string_info("hello")], None)
        assert result == {}

    def test_only_string_lines_yield_one_empty_infodict_list_for_multipv(self) -> None:
        result = _select_final_infos([make_string_info("hello")], 2)
        assert result == [{}]

    def test_empty_stream_multipv_never_returns_empty_list(self) -> None:
        assert _select_final_infos([], 2) == [{}]
        assert _select_final_infos([], None) == {}


class TestPoolPath:
    async def test_evaluate_nodes_with_pv_uses_last_exact_line(self) -> None:
        exact = make_info(EXACT_DEPTH, cp=EXACT_CP, pv=EXACT_PV)
        bound = make_info(BOUND_DEPTH, cp=BOUND_CP, pv=BOUND_PV, bound="lower")
        protocol = ScriptedAnalysisProtocol([exact, bound])
        pool = make_pool(protocol)

        cp, mate, best, pv_string = await pool.evaluate_nodes_with_pv(_repro_board())

        assert cp == EXACT_CP
        assert mate is None
        assert best == EXACT_PV.split()[0]
        assert pv_string == " ".join(EXACT_PV.split()[:PV_CAP_PLIES])

    async def test_stale_bound_key_trap_through_pool(self) -> None:
        first = make_info(15, cp=EXACT_CP, pv=EXACT_PV)
        bound = make_info(16, cp=BOUND_CP, pv=BOUND_PV, bound="lower")
        final = make_info(16, cp=EXACT_CP, pv=EXACT_PV)
        pool = make_pool(ScriptedAnalysisProtocol([first, bound, final]))

        result = await pool._acquire_and_analyse(
            _repro_board(), chess.engine.Limit(nodes=_NODES_BUDGET), 5.0
        )

        assert isinstance(result, dict)
        assert "lowerbound" not in result
        assert result is final

    async def test_evaluate_nodes_multipv2_uses_exact_lines(self) -> None:
        lines = [
            make_info(16, cp=EXACT_CP, pv=EXACT_PV, multipv=1),
            make_info(16, cp=SECOND_LINE_CP, pv=SECOND_EXACT_PV, multipv=2),
            make_info(17, cp=BOUND_CP, pv="h7e7", multipv=1, bound="upper"),
            make_info(17, cp=BOUND_CP, pv="h7e7 f6e7", multipv=2, bound="lower"),
        ]
        pool = make_pool(ScriptedAnalysisProtocol(lines))

        (
            cp,
            mate,
            best,
            pv_string,
            second_cp,
            second_mate,
            second_uci,
        ) = await pool.evaluate_nodes_multipv2(_repro_board())

        assert cp == EXACT_CP
        assert mate is None
        assert best == EXACT_PV.split()[0]
        assert pv_string == " ".join(EXACT_PV.split()[:PV_CAP_PLIES])
        assert second_cp == SECOND_LINE_CP
        assert second_mate is None
        assert second_uci == SECOND_EXACT_PV.split()[0]

    async def test_limit_and_multipv_reach_analysis_unchanged(self) -> None:
        protocol = ScriptedAnalysisProtocol([make_info(16, cp=EXACT_CP, pv=EXACT_PV, multipv=1)])
        pool = make_pool(protocol)

        await pool.evaluate_nodes_multipv2(_repro_board())

        assert len(protocol.calls) == 1
        limit, multipv = protocol.calls[0]
        assert limit.nodes == _NODES_BUDGET
        assert limit.depth is None
        assert multipv == 2

    async def test_timeout_returns_none_stops_search_and_releases_slot(self) -> None:
        protocol = ScriptedAnalysisProtocol(mode="hang")
        pool = make_pool(protocol)
        restart_calls: list[int] = []

        async def spy_restart(idx: int) -> bool:
            restart_calls.append(idx)
            return True

        pool._restart_worker = spy_restart  # ty: ignore[invalid-assignment] -- test spy

        with patch("app.services.engine._NODES_TIMEOUT_S", NEAR_ZERO_TIMEOUT_S):
            result = await pool.evaluate_nodes_with_pv(_repro_board())

        assert result == (None, None, None, None)
        assert restart_calls == [], "a timeout must not restart the worker (FLAWCHESS-8B)"
        assert protocol.stop_calls == 1
        assert pool._available.qsize() == 1

    async def test_engine_error_returns_none_captures_restarts_and_releases(self) -> None:
        exact = make_info(EXACT_DEPTH, cp=EXACT_CP, pv=EXACT_PV)
        protocol = ScriptedAnalysisProtocol(
            [exact], mode="error", error=chess.engine.EngineError("mock engine error")
        )
        pool = make_pool(protocol)
        restart_calls: list[int] = []

        async def spy_restart(idx: int) -> bool:
            restart_calls.append(idx)
            return True

        pool._restart_worker = spy_restart  # ty: ignore[invalid-assignment] -- test spy

        with patch("app.services.engine.sentry_sdk.capture_exception") as capture:
            result = await pool.evaluate_nodes_with_pv(_repro_board())

        assert result == (None, None, None, None)
        assert restart_calls == [0]
        assert capture.call_count == 1
        assert isinstance(capture.call_args.args[0], chess.engine.EngineError)
        assert pool._available.qsize() == 1

    async def test_invalid_board_never_calls_analysis_or_takes_slot(self) -> None:
        protocol = ScriptedAnalysisProtocol([make_info(16, cp=EXACT_CP, pv=EXACT_PV)])
        pool: EnginePool = make_pool(protocol)
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/PPPPPPPP/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert not board.is_valid()

        result = await pool.evaluate_nodes_with_pv(board)

        assert result == (None, None, None, None)
        assert protocol.calls == []
        assert pool._available.qsize() == 1
