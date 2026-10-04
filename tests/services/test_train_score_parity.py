"""CI-enforced parity: app/services/train_score.py must match frontend/src/lib/trainScore.ts.

The weekly leaderboard computes points server-side (Phase 230 D-01) while the
client stays the source of truth for per-session display. Change both together;
this test goes red when the two sides drift. Values are regex-extracted from
trainScore.ts.
"""

import re
from pathlib import Path

from app.models.drill_solve import DrillMoveQuality
from app.services.train_score import (
    GUESS_POINTS,
    MOVE_QUALITY_TIER,
    MOVE_TIER_POINTS,
    TRAIN_POINTS_PER_PUZZLE,
)

_TRAIN_SCORE_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/trainScore.ts"


def _extract_int(name: str) -> int:
    """Extract `export const NAME = <int>;` from trainScore.ts."""
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", _TRAIN_SCORE_TS.read_text())
    assert m, f"could not find export const {name} in trainScore.ts"
    return int(m.group(1))


def _extract_move_tier_points() -> dict[str, int]:
    """Extract the MOVE_TIER_POINTS object literal from trainScore.ts."""
    block = re.search(
        r"export\s+const\s+MOVE_TIER_POINTS[^=]*=\s*\{(.*?)\}", _TRAIN_SCORE_TS.read_text(), re.S
    )
    assert block, "could not find export const MOVE_TIER_POINTS in trainScore.ts"
    pairs = re.findall(r"(\w+)\s*:\s*(\d+)", block.group(1))
    assert pairs, "MOVE_TIER_POINTS literal has no key: value pairs"
    return {key: int(value) for key, value in pairs}


def test_guess_points_match_frontend() -> None:
    assert _extract_int("GUESS_POINTS") == GUESS_POINTS


def test_points_per_puzzle_match_frontend() -> None:
    assert _extract_int("TRAIN_POINTS_PER_PUZZLE") == TRAIN_POINTS_PER_PUZZLE


def test_move_tier_points_match_frontend() -> None:
    assert _extract_move_tier_points() == dict(MOVE_TIER_POINTS)


def test_move_quality_tier_maps_every_enum_member() -> None:
    assert set(MOVE_QUALITY_TIER) == set(DrillMoveQuality)
    assert {tier for tier in MOVE_QUALITY_TIER.values()} == set(MOVE_TIER_POINTS)


def test_move_quality_enum_values_equal_their_tier_points() -> None:
    """Guards the SQL CASE mapping against an enum renumbering."""
    for quality, tier in MOVE_QUALITY_TIER.items():
        assert int(quality) == MOVE_TIER_POINTS[tier]


def test_max_points_per_puzzle_is_guess_plus_best_move_tier() -> None:
    assert GUESS_POINTS + max(MOVE_TIER_POINTS.values()) == TRAIN_POINTS_PER_PUZZLE
