"""Unit tests for app.services.eval_utils — Stockfish eval to expected score.

Covers Phase 83 D-02 / D-03 (SEED-014): user-perspective expected score derived
from Stockfish eval (signed centipawns or mate-in-N) via the Lichess winning-
chances sigmoid (cp) and a direct 0/1 mapping (mate).

Sign convention (mirrors app/services/endgame_service.py _classify_endgame_bucket):
  - Raw eval_cp / eval_mate are white-perspective (python-chess / Stockfish).
  - A `sign = +1 if user_color == "white" else -1` flip yields user perspective.

Pitfall 1 (RESEARCH §"Pitfalls"): mate-for-user vs mate-against-user must be
covered for BOTH colors — Phase 82 was bitten by an asymmetric sign bug that
flat unit tests with only one color would have missed.
"""

import math

import pytest

from app.services.eval_utils import (
    LICHESS_K,
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)


class TestSigmoid:
    """Coverage for eval_cp_to_expected_score (Lichess winning-chances sigmoid)."""

    def test_lichess_k_constant_value(self) -> None:
        """LICHESS_K is the documented Lichess winning-chances constant (0.00368208)."""
        assert LICHESS_K == 0.00368208

    def test_zero_cp_returns_half(self) -> None:
        """eval_cp == 0 maps to expected score 0.5 for either color (centering)."""
        assert eval_cp_to_expected_score(0, "white") == pytest.approx(0.5, abs=1e-9)
        assert eval_cp_to_expected_score(0, "black") == pytest.approx(0.5, abs=1e-9)

    def test_positive_cp_white_user(self) -> None:
        """+100 cp from a white-user perspective sits at ~0.591 (sigmoid at +100)."""
        expected = 1.0 / (1.0 + math.exp(-LICHESS_K * 100))
        assert eval_cp_to_expected_score(+100, "white") == pytest.approx(expected, abs=1e-9)
        # Sanity: numerical value is ~0.591 (advantageous for white).
        assert eval_cp_to_expected_score(+100, "white") == pytest.approx(0.591, abs=1e-3)

    def test_positive_cp_black_user(self) -> None:
        """+100 cp from a black-user perspective sits at ~0.409 (sign-flipped sigmoid).

        White-perspective +100 means white is ahead, so the black user is *behind*.
        """
        expected = 1.0 / (1.0 + math.exp(+LICHESS_K * 100))
        assert eval_cp_to_expected_score(+100, "black") == pytest.approx(expected, abs=1e-9)
        assert eval_cp_to_expected_score(+100, "black") == pytest.approx(0.409, abs=1e-3)

    def test_white_black_symmetry(self) -> None:
        """f(+x, "white") + f(+x, "black") == 1.0 — the sigmoid is point-symmetric around 0.5."""
        for cp in (-1500, -300, -1, 0, 1, 50, 300, 1500):
            white = eval_cp_to_expected_score(cp, "white")
            black = eval_cp_to_expected_score(cp, "black")
            assert white + black == pytest.approx(1.0, abs=1e-9), (
                f"symmetry broken at cp={cp}: white={white}, black={black}"
            )

    def test_saturation_high(self) -> None:
        """At +1500 cp the white user is effectively winning — expected score > 0.99."""
        assert eval_cp_to_expected_score(+1500, "white") > 0.99
        # And the black user is effectively losing.
        assert eval_cp_to_expected_score(+1500, "black") < 0.01

    def test_saturation_low(self) -> None:
        """At -1500 cp the white user is effectively losing — expected score < 0.01."""
        assert eval_cp_to_expected_score(-1500, "white") < 0.01
        # And the black user is effectively winning.
        assert eval_cp_to_expected_score(-1500, "black") > 0.99

    def test_monotonic_in_cp_for_white_user(self) -> None:
        """Sigmoid is strictly monotonic in cp for a fixed color (white user, ascending cp)."""
        cps = [-1500, -500, -100, -1, 0, 1, 100, 500, 1500]
        scores = [eval_cp_to_expected_score(cp, "white") for cp in cps]
        for prev, nxt in zip(scores, scores[1:]):
            assert prev < nxt, f"non-monotonic: {prev} >= {nxt}"

    def test_monotonic_in_cp_for_black_user(self) -> None:
        """For a black user the function is strictly *decreasing* in white-perspective cp."""
        cps = [-1500, -500, -100, -1, 0, 1, 100, 500, 1500]
        scores = [eval_cp_to_expected_score(cp, "black") for cp in cps]
        for prev, nxt in zip(scores, scores[1:]):
            assert prev > nxt, f"non-monotonic (black user): {prev} <= {nxt}"

    def test_range_in_unit_interval(self) -> None:
        """Output is always in (0, 1) for any finite int cp."""
        for cp in (-100000, -1500, 0, 1500, 100000):
            for color in ("white", "black"):
                score = eval_cp_to_expected_score(cp, color)  # type: ignore[arg-type]
                assert 0.0 <= score <= 1.0, f"out of range at cp={cp}, color={color}: {score}"


class TestMate:
    """Coverage for eval_mate_to_expected_score (direct 0/1 mapping, no sigmoid)."""

    def test_white_mating_white_user(self) -> None:
        """eval_mate=+5 (white has mate-in-5) maps to 1.0 for a white user."""
        assert eval_mate_to_expected_score(+5, "white") == 1.0

    def test_white_mating_black_user(self) -> None:
        """eval_mate=+5 maps to 0.0 for a black user (white is mating us)."""
        assert eval_mate_to_expected_score(+5, "black") == 0.0

    def test_black_mating_white_user(self) -> None:
        """eval_mate=-5 (black has mate-in-5) maps to 0.0 for a white user."""
        assert eval_mate_to_expected_score(-5, "white") == 0.0

    def test_black_mating_black_user(self) -> None:
        """eval_mate=-5 maps to 1.0 for a black user (Pitfall 1 — symmetric coverage)."""
        assert eval_mate_to_expected_score(-5, "black") == 1.0

    def test_short_mate_for_each_color(self) -> None:
        """Mate-in-1 is treated identically to mate-in-N: pure 0/1 mapping, no sigmoid scaling."""
        assert eval_mate_to_expected_score(+1, "white") == 1.0
        assert eval_mate_to_expected_score(+1, "black") == 0.0
        assert eval_mate_to_expected_score(-1, "white") == 0.0
        assert eval_mate_to_expected_score(-1, "black") == 1.0

    def test_long_mate_for_each_color(self) -> None:
        """Mate-in-30 still maps to 0/1; the helper does not weigh distance to mate."""
        assert eval_mate_to_expected_score(+30, "white") == 1.0
        assert eval_mate_to_expected_score(+30, "black") == 0.0
        assert eval_mate_to_expected_score(-30, "white") == 0.0
        assert eval_mate_to_expected_score(-30, "black") == 1.0

    def test_mate_output_is_exactly_zero_or_one(self) -> None:
        """Outputs are exact floats 0.0 / 1.0 (no sigmoid rounding)."""
        cases = [(+5, "white", 1.0), (+5, "black", 0.0), (-5, "white", 0.0), (-5, "black", 1.0)]
        for eval_mate, color, expected in cases:
            actual = eval_mate_to_expected_score(eval_mate, color)  # type: ignore[arg-type]
            assert actual == expected
            assert isinstance(actual, float)
