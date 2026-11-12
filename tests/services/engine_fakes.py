"""Scripted UCI analysis stream fake for engine wrapper tests.

Builds a real `chess.engine.AnalysisResult` and feeds scripted info lines through
`AnalysisResult.post()`, so the merged `.info` / `.multipv` state is polluted exactly
as in prod (including a stale `lowerbound: True` key). No Stockfish binary needed.
"""

from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import Literal
from unittest.mock import MagicMock

import chess
import chess.engine

from app.services.engine import EnginePool

BoundKind = Literal["lower", "upper"]


def make_info(
    depth: int,
    *,
    cp: int | None = None,
    mate: int | None = None,
    pv: str = "",
    multipv: int | None = None,
    bound: BoundKind | None = None,
    turn: chess.Color = chess.WHITE,
) -> chess.engine.InfoDict:
    """Build one UCI info line as python-chess's parser would produce it.

    `pv` is a space-separated UCI move string; empty means no pv key at all.
    """
    info: dict[str, object] = {"depth": depth}
    if mate is not None:
        info["score"] = chess.engine.PovScore(chess.engine.Mate(mate), turn)
    elif cp is not None:
        info["score"] = chess.engine.PovScore(chess.engine.Cp(cp), turn)
    if pv:
        info["pv"] = [chess.Move.from_uci(uci) for uci in pv.split()]
    if multipv is not None:
        info["multipv"] = multipv
    if bound == "lower":
        info["lowerbound"] = True
    elif bound == "upper":
        info["upperbound"] = True
    return typing.cast(chess.engine.InfoDict, info)


def make_string_info(text: str) -> chess.engine.InfoDict:
    """An `info string ...` line (no pv, no score)."""
    return typing.cast(chess.engine.InfoDict, {"string": text})


class ScriptedAnalysisProtocol:
    """Stand-in for `UciProtocol.analysis` that replays a scripted info stream.

    mode "finish": post every line, then set_finished(BestMove(first pv move)).
    mode "error": post every line, then set_exception(error).
    mode "hang": post nothing and never finish (for timeout tests).
    """

    def __init__(
        self,
        lines: Sequence[chess.engine.InfoDict] = (),
        *,
        mode: Literal["finish", "error", "hang"] = "finish",
        error: Exception | None = None,
    ) -> None:
        self.lines = list(lines)
        self.mode = mode
        self.error = error
        self.calls: list[tuple[chess.engine.Limit, int | None]] = []
        # Every call's `root_moves` kwarg (None when the caller did not pass it); kept
        # apart from `calls` because existing tests assert that tuple's shape.
        self.root_moves_calls: list[Sequence[chess.Move] | None] = []
        self.boards: list[chess.Board] = []
        self.stop_calls = 0

    def _on_stop(self) -> None:
        self.stop_calls += 1

    async def analysis(
        self,
        board: chess.Board,
        limit: chess.engine.Limit | None = None,
        *,
        multipv: int | None = None,
        **kwargs: object,
    ) -> chess.engine.AnalysisResult:
        assert limit is not None
        self.calls.append((limit, multipv))
        root_moves = kwargs.get("root_moves")
        self.root_moves_calls.append(
            list(typing.cast(Sequence[chess.Move], root_moves)) if root_moves is not None else None
        )
        self.boards.append(board)
        result = chess.engine.AnalysisResult(stop=self._on_stop)
        if self.mode == "hang":
            return result
        for line in self.lines:
            result.post(line)
        if self.mode == "error":
            assert self.error is not None
            result.set_exception(self.error)
            return result
        first_pv = next((line["pv"] for line in self.lines if line.get("pv")), None)
        result.set_finished(chess.engine.BestMove(first_pv[0] if first_pv else None, None))
        return result


def make_pool(protocol: ScriptedAnalysisProtocol) -> EnginePool:
    """A started size-1 EnginePool whose only worker uses the scripted protocol."""
    pool = EnginePool(size=1)
    pool._started = True
    mock_protocol = MagicMock(spec=chess.engine.UciProtocol)
    mock_protocol.analysis = protocol.analysis
    pool._transports = [None]
    pool._protocols = [mock_protocol]
    pool._available.put_nowait(0)
    return pool
