"""Pure unit tests for app/services/maia_flaw_stats.py (D-01, D-15). No DB, no ORT."""

from __future__ import annotations

import random

import chess
import pytest

from app.services.maia_flaw_stats import (
    MaiaFlawStats,
    compute_maia_flaw_stats,
    compute_refutation_stats,
    null_maia_stats,
    null_refutation_stats,
)
from tests.services.maia_fakes import fake_full_policy

_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
# Both sides keep castling rights and the e-pawn is gone, so O-O / O-O-O are legal.
_CASTLING_FEN = "r3k2r/pppq1ppp/2n1bn2/3pp3/3PP3/2N1BN2/PPPQ1PPP/R3K2R w KQkq - 0 1"
_UNIFORM_K = 5
_TOL = 1e-9


def _stats(
    probs: dict[str, float], played: str, best: str | None = "a", second: str | None = "b"
) -> tuple[MaiaFlawStats | None, list[str]]:
    stats, reasons = compute_maia_flaw_stats(
        probs, played_uci=played, best_uci=best, second_uci=second
    )
    return stats, list(reasons)


def test_rank_strict_greater_with_ties() -> None:
    stats, _ = _stats({"a": 0.4, "b": 0.3, "c": 0.3}, "c")
    assert stats is not None
    assert stats["maia_played_rank"] == 2  # tie with b, only a is strictly higher
    stats, _ = _stats({"a": 0.3, "b": 0.3, "c": 0.2}, "c")
    assert stats is not None
    assert stats["maia_played_rank"] == 3  # move just below a tied pair
    stats, _ = _stats({"a": 0.4, "b": 0.3, "c": 0.3}, "a")
    assert stats is not None
    assert stats["maia_played_rank"] == 1
    assert stats["maia_best_rank"] == 1
    assert stats["maia_second_rank"] == 2


def test_effective_moves_uniform_and_single() -> None:
    uniform = {f"m{i}": 1.0 / _UNIFORM_K for i in range(_UNIFORM_K)}
    stats, _ = _stats(uniform, "m0", best="m0", second="m1")
    assert stats is not None
    assert stats["maia_effective_moves"] == pytest.approx(float(_UNIFORM_K), abs=_TOL)

    stats, reasons = _stats({"a": 1.0}, "a", best="a", second="b")
    assert stats is not None
    assert stats["maia_effective_moves"] == pytest.approx(1.0, abs=_TOL)
    assert stats["maia_top_prob"] == 1.0
    assert stats["maia_second_prob"] is None
    assert stats["maia_second_rank"] is None
    assert reasons == ["single_legal_move"]


def test_played_not_legal_and_empty() -> None:
    assert _stats({}, "a") == (None, ["played_not_legal"])
    assert _stats({"a": 0.6, "b": 0.4}, "z") == (None, ["played_not_legal"])


def test_order_independent() -> None:
    items = list(fake_full_policy(_START_FEN, 1500.0).items())
    shuffled = items[:]
    random.Random(7).shuffle(shuffled)
    assert shuffled != items
    first = _stats(dict(items), "e2e4", best="d2d4", second="g1f3")
    second = _stats(dict(shuffled), "e2e4", best="d2d4", second="g1f3")
    assert first == second


def test_best_pair_reasons() -> None:
    probs = {"a": 0.5, "b": 0.3, "c": 0.2}
    stats, reasons = _stats(probs, "c", best=None, second="b")
    assert reasons == ["best_missing"]
    assert stats is not None
    assert stats["maia_best_prob"] is None and stats["maia_best_rank"] is None
    assert stats["maia_played_prob"] == 0.2
    assert stats["maia_top_prob"] == 0.5
    assert stats["maia_effective_moves"] is not None
    assert stats["maia_second_rank"] == 2

    stats, reasons = _stats(probs, "c", best="zz", second="b")
    assert reasons == ["best_not_legal"]
    assert stats is not None
    assert stats["maia_best_prob"] is None and stats["maia_best_rank"] is None
    assert stats["maia_played_rank"] == 3


def test_second_pair_reasons_d15() -> None:
    probs = {"a": 0.5, "b": 0.3, "c": 0.2}
    cases = (("", "second_missing"), ("a", "second_equals_best"), ("zz", "second_not_legal"))
    for second, expected in cases:
        stats, reasons = _stats(probs, "c", best="a", second=second)
        assert reasons == [expected], second
        assert stats is not None
        assert stats["maia_second_prob"] is None
        assert stats["maia_second_rank"] is None
        assert stats["maia_best_rank"] == 1
        assert stats["maia_played_rank"] == 3
        assert stats["maia_top_prob"] == 0.5
        assert stats["maia_effective_moves"] is not None
    stats, reasons = _stats(probs, "c", best="a", second=None)
    assert reasons == ["second_missing"]
    assert stats is not None and stats["maia_second_prob"] is None


def test_null_maia_stats_has_eight_d01_keys() -> None:
    nulls = null_maia_stats()
    assert set(nulls) == {
        "maia_played_prob",
        "maia_played_rank",
        "maia_best_prob",
        "maia_best_rank",
        "maia_second_prob",
        "maia_second_rank",
        "maia_top_prob",
        "maia_effective_moves",
    }
    assert all(value is None for value in nulls.values())


def test_fake_full_policy_deterministic() -> None:
    for fen in (_START_FEN, _CASTLING_FEN):
        probs = fake_full_policy(fen, 1500.0)
        legal = {move.uci() for move in chess.Board(fen).legal_moves}
        assert set(probs) == legal
        assert sum(probs.values()) == pytest.approx(1.0, abs=_TOL)
        assert len(set(probs.values())) == len(probs)
        assert fake_full_policy(fen, 2200.0) == probs
    assert "e1g1" in fake_full_policy(_CASTLING_FEN, 1500.0)


# ---------------------------------------------------------------------------
# Phase 248 refutation pair (pure)
# ---------------------------------------------------------------------------


def test_refutation_stats_strict_greater_rank_ties_share() -> None:
    probs = {"a": 0.4, "b": 0.3, "c": 0.3}
    stats, reason = compute_refutation_stats(probs, "c")
    assert reason is None
    assert stats["maia_refutation_rank"] == 2  # tie with b, only a is strictly higher
    stats, _ = compute_refutation_stats({"a": 0.3, "b": 0.3, "c": 0.2}, "c")
    assert stats["maia_refutation_rank"] == 3  # move just below a tied pair
    stats, _ = compute_refutation_stats(probs, "a")
    assert stats["maia_refutation_rank"] == 1


def test_refutation_stats_prob_float_rank_int() -> None:
    stats, reason = compute_refutation_stats({"a": 0.75, "b": 0.25}, "b")
    assert reason is None
    assert isinstance(stats["maia_refutation_prob"], float)
    assert isinstance(stats["maia_refutation_rank"], int)
    assert stats["maia_refutation_prob"] == pytest.approx(0.25, abs=_TOL)
    assert stats["maia_refutation_rank"] == 2


def test_refutation_stats_empty_policy_is_no_legal_reply() -> None:
    stats, reason = compute_refutation_stats({}, "e2e4")
    assert reason == "no_legal_reply"
    assert stats == null_refutation_stats()


def test_refutation_stats_missing_and_not_legal() -> None:
    probs = {"a": 0.6, "b": 0.4}
    stats, reason = compute_refutation_stats(probs, None)
    assert (stats, reason) == (null_refutation_stats(), "refutation_missing")
    stats, reason = compute_refutation_stats(probs, "z")
    assert (stats, reason) == (null_refutation_stats(), "refutation_not_legal")


def test_refutation_stats_matches_full_policy_rank() -> None:
    probs = fake_full_policy(_START_FEN, 0.0)
    for uci, own in probs.items():
        stats, reason = compute_refutation_stats(probs, uci)
        assert reason is None
        assert stats["maia_refutation_rank"] == 1 + sum(1 for p in probs.values() if p > own)
