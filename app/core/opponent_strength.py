"""Opponent-strength preset helpers shared across routers, services, and repositories.

The Opponent Strength filter is a (gap_min, gap_max) range over opponent_rating
- user_rating, with four named preset shortcuts. This module centralises the
mapping between range and preset so router/service/repository layers can all
agree on the four canonical buckets without duplicating the thresholds.
"""

from typing import Literal

# Preset thresholds (Elo gap, opponent − user) used to map between the four
# preset shortcuts (any / stronger / similar / weaker) and the gap-based
# range filter. Spike 001 locked these values.
PRESET_THRESHOLD = 50

OpponentStrengthPreset = Literal["any", "stronger", "similar", "weaker", "custom"]


def preset_to_range(
    preset: Literal["any", "stronger", "similar", "weaker"],
) -> tuple[int | None, int | None]:
    """Map a preset name to (gap_min, gap_max). Inverse of derive_preset."""
    if preset == "any":
        return (None, None)
    if preset == "stronger":
        return (PRESET_THRESHOLD, None)
    if preset == "similar":
        return (-PRESET_THRESHOLD, PRESET_THRESHOLD)
    return (None, -PRESET_THRESHOLD)


def derive_preset(
    opponent_gap_min: int | None,
    opponent_gap_max: int | None,
) -> OpponentStrengthPreset:
    """Map a (gap_min, gap_max) range to the closest preset name.

    Returns "any" / "stronger" / "similar" / "weaker" when the range exactly
    matches one of the four preset ranges, else "custom".

    Preset ranges (None = unbounded):
      any      → (None, None)
      stronger → (50, None)
      similar  → (-50, 50)
      weaker   → (None, -50)
    """
    if opponent_gap_min is None and opponent_gap_max is None:
        return "any"
    if opponent_gap_min == PRESET_THRESHOLD and opponent_gap_max is None:
        return "stronger"
    if opponent_gap_min == -PRESET_THRESHOLD and opponent_gap_max == PRESET_THRESHOLD:
        return "similar"
    if opponent_gap_min is None and opponent_gap_max == -PRESET_THRESHOLD:
        return "weaker"
    return "custom"
