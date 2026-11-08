"""Deterministic Maia fakes shared by the Phase 247 tests (helper, not a test module).

Plans 02-05 monkeypatch ``maia_flaw_scoring.full_policy`` with ``fake_full_policy``
when a test sets ``maia_engine._session`` to an ``object()`` sentinel, so DB-backed
tests exercise the scorer without a real ORT session.
"""

from __future__ import annotations

import chess


def fake_full_policy(fen: str, elo: float) -> dict[str, float]:
    """Deterministic stand-in for ``maia_engine.full_policy``.

    Covers exactly the position's legal moves, sorted by UCI, with weights
    n, n-1, ..., 1 normalized to sum 1: every legal move gets a distinct value
    (distinct ranks) and the result is independent of ``elo``.
    """
    ucis = sorted(move.uci() for move in chess.Board(fen).legal_moves)
    n = len(ucis)
    total = n * (n + 1) / 2
    return {uci: (n - i) / total for i, uci in enumerate(ucis)}
