"""Pure unit tests for app/services/maia_flaw_stats.py (D-01, 250 D-11). No DB, no ORT."""

from __future__ import annotations

import random

import chess
import pytest

from app.services.maia_flaw_stats import (
    MaiaFlawStats,
    compute_maia_flaw_stats,
    null_maia_stats,
    reply_spread,
)
from tests.services.maia_fakes import fake_full_policy

_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
# Both sides keep castling rights and the e-pawn is gone, so O-O / O-O-O are legal.
_CASTLING_FEN = "r3k2r/pppq1ppp/2n1bn2/3pp3/3PP3/2N1BN2/PPPQ1PPP/R3K2R w KQkq - 0 1"
_UNIFORM_K = 5
_TOL = 1e-9


def _stats(probs: dict[str, float], played: str) -> tuple[MaiaFlawStats | None, list[str]]:
    stats, reasons = compute_maia_flaw_stats(probs, played_uci=played)
    return stats, list(reasons)


def test_played_prob_is_the_played_moves_probability() -> None:
    stats, reasons = _stats({"a": 0.4, "b": 0.3, "c": 0.3}, "c")
    assert reasons == []
    assert stats == {"maia_played_prob": 0.3}
    assert isinstance(stats["maia_played_prob"], float)


def test_played_not_legal_and_empty() -> None:
    assert _stats({}, "a") == (None, ["played_not_legal"])
    assert _stats({"a": 0.6, "b": 0.4}, "z") == (None, ["played_not_legal"])


def test_order_independent() -> None:
    items = list(fake_full_policy(_START_FEN, 1500.0).items())
    shuffled = items[:]
    random.Random(7).shuffle(shuffled)
    assert shuffled != items
    assert _stats(dict(items), "e2e4") == _stats(dict(shuffled), "e2e4")


def test_null_maia_stats_has_only_the_played_prob_key() -> None:
    nulls = null_maia_stats()
    assert set(nulls) == {"maia_played_prob"}
    assert all(value is None for value in nulls.values())


def test_reply_spread_uniform_and_single() -> None:
    uniform = {f"m{i}": 1.0 / _UNIFORM_K for i in range(_UNIFORM_K)}
    assert reply_spread(uniform) == pytest.approx(float(_UNIFORM_K), abs=_TOL)
    assert reply_spread({"a": 1.0}) == pytest.approx(1.0, abs=_TOL)


def test_fake_full_policy_deterministic() -> None:
    for fen in (_START_FEN, _CASTLING_FEN):
        probs = fake_full_policy(fen, 1500.0)
        legal = {move.uci() for move in chess.Board(fen).legal_moves}
        assert set(probs) == legal
        assert sum(probs.values()) == pytest.approx(1.0, abs=_TOL)
        assert len(set(probs.values())) == len(probs)
        assert fake_full_policy(fen, 2200.0) == probs
    assert "e1g1" in fake_full_policy(_CASTLING_FEN, 1500.0)
