"""Server-side mirror of the Train scoring constants (Phase 230 D-01).

`frontend/src/lib/trainScore.ts` stays the single source of truth for the
per-session score a user sees. The weekly leaderboard needs the same points on
the server (it aggregates every trainer's `drill_solves` rows in SQL), so this
module is a deliberate server port of the three scoring constants, used only by
`app.repositories.train_leaderboard_repository`.

`tests/services/test_train_score_parity.py` regex-extracts the same constants
from trainScore.ts and fails when the two sides drift. Change both together.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal

from app.models.drill_solve import DrillMoveQuality

MoveTier = Literal["good", "inaccuracy", "wrong"]

# Points awarded for a correct guess (trainScore.ts GUESS_POINTS).
GUESS_POINTS: Final[int] = 1

# Move points per tier (trainScore.ts MOVE_TIER_POINTS), read-only.
MOVE_TIER_POINTS: Final[Mapping[MoveTier, int]] = MappingProxyType(
    {"good": 2, "inaccuracy": 1, "wrong": 0}
)

# Max points one puzzle can award (trainScore.ts TRAIN_POINTS_PER_PUZZLE).
TRAIN_POINTS_PER_PUZZLE: Final[int] = 3

# DrillMoveQuality (DB int) -> score tier. The leaderboard SQL CASE is built
# from this mapping and MOVE_TIER_POINTS, never from the raw enum value.
MOVE_QUALITY_TIER: Final[Mapping[DrillMoveQuality, MoveTier]] = MappingProxyType(
    {
        DrillMoveQuality.GOOD: "good",
        DrillMoveQuality.INACCURACY: "inaccuracy",
        DrillMoveQuality.WRONG: "wrong",
    }
)

__all__ = [
    "GUESS_POINTS",
    "MOVE_QUALITY_TIER",
    "MOVE_TIER_POINTS",
    "MoveTier",
    "TRAIN_POINTS_PER_PUZZLE",
]
