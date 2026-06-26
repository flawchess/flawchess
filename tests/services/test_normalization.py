"""Unit tests for app/services/normalization.py helpers.

Covers is_correspondence_time_control — no DB required, pure unit tests.
"""

from app.services.normalization import is_correspondence_time_control


class TestIsCorrespondenceTimeControl:
    """Parameterised coverage for the is_correspondence_time_control predicate."""

    def test_daily_one_day_returns_true(self) -> None:
        """chess.com '1/86400' (1 day per move) → True."""
        assert is_correspondence_time_control("1/86400") is True

    def test_daily_three_days_returns_true(self) -> None:
        """chess.com '1/259200' (3 days per move) → True."""
        assert is_correspondence_time_control("1/259200") is True

    def test_classical_1800_returns_false(self) -> None:
        """'1800' is a 30-minute rapid/classical game, not correspondence."""
        assert is_correspondence_time_control("1800") is False

    def test_rapid_with_increment_returns_false(self) -> None:
        """'600+5' (10 min + 5s increment) is rapid, not correspondence."""
        assert is_correspondence_time_control("600+5") is False

    def test_bullet_returns_false(self) -> None:
        """'60+0' (1 min bullet) → False."""
        assert is_correspondence_time_control("60+0") is False

    def test_fractional_increment_returns_false(self) -> None:
        """'10+0.1' (chess.com fractional increment) → False."""
        assert is_correspondence_time_control("10+0.1") is False

    def test_none_returns_false(self) -> None:
        """None (missing time_control_str) → False."""
        assert is_correspondence_time_control(None) is False

    def test_empty_string_returns_false(self) -> None:
        """Empty string → False."""
        assert is_correspondence_time_control("") is False

    def test_dash_returns_false(self) -> None:
        """'-' (missing TC sentinel) → False."""
        assert is_correspondence_time_control("-") is False
