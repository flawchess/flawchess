"""CI-enforced consistency: opening_insights_constants must match the frontend
score-verdict constants that colour the board arrows. Catches future score-threshold
drift between the backend classifier and the board arrow colors.
Values are regex-extracted from the TypeScript sources.

Phase 242 D-35: arrowColor.ts no longer carries its own SCORE_PIVOT / SCORE_BOUNDARY /
MIN_GAMES_FOR_COLOR. getArrowColor routes through openingVerdict (the same 95%,
20-game, +/-5-point rule as the Stats cards), so the constants live in
scoreBulletConfig.ts (pivot and band) and openingVerdict.ts (game floor). The single FE
band (0.05) corresponds to the backend `OPENING_INSIGHTS_MINOR_EFFECT`; the backend
`MAJOR_EFFECT` (0.10) has no FE counterpart.
"""

import re
from pathlib import Path

import pytest

_FE_LIB = Path(__file__).resolve().parents[2] / "frontend/src/lib"
_ARROW_TS = _FE_LIB / "arrowColor.ts"
_SCORE_BULLET_TS = _FE_LIB / "scoreBulletConfig.ts"
_OPENING_VERDICT_TS = _FE_LIB / "openingVerdict.ts"

# Import lazily so the file is always collectable, but tests skip if the
# constants module is missing (e.g. during initial development).
try:
    from app.services.opening_insights_constants import (
        OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
        OPENING_INSIGHTS_MINOR_EFFECT,
        OPENING_INSIGHTS_SCORE_PIVOT,
    )

    _CONSTANTS_AVAILABLE = True
except ImportError:
    _CONSTANTS_AVAILABLE = False
    OPENING_INSIGHTS_SCORE_PIVOT: float = 0.0  # type: ignore[assignment]
    OPENING_INSIGHTS_MINOR_EFFECT: float = 0.0  # type: ignore[assignment]
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 0  # type: ignore[assignment]


def _extract_float(path: Path, name: str) -> float:
    """Extract `export const NAME = <float>;` from a TypeScript source."""
    text = path.read_text()
    # Match floats like 0.50, .05, 1, 10, 0.10
    m = re.search(rf"export\s+const\s+{name}\s*=\s*([0-9]*\.?[0-9]+)\s*;", text)
    assert m, f"could not find export const {name} in {path.name}"
    return float(m.group(1))


def _extract_int(path: Path, name: str) -> int:
    """Extract `export const NAME = <int>;` from a TypeScript source."""
    text = path.read_text()
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", text)
    assert m, f"could not find export const {name} in {path.name}"
    return int(m.group(1))


def test_arrow_color_routes_through_the_opening_verdict() -> None:
    """D-35: the arrows use openingVerdict, so the constants below are the arrow rule."""
    text = _ARROW_TS.read_text()
    assert re.search(r"from\s+'@/lib/openingVerdict'", text)
    assert "openingVerdict(" in text


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_score_pivot_matches_frontend() -> None:
    """SCORE_BULLET_CENTER must match OPENING_INSIGHTS_SCORE_PIVOT."""
    assert _extract_float(_SCORE_BULLET_TS, "SCORE_BULLET_CENTER") == OPENING_INSIGHTS_SCORE_PIVOT


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_score_boundary_matches_frontend() -> None:
    """SCORE_BULLET_NEUTRAL_MAX (the FE single band) must match OPENING_INSIGHTS_MINOR_EFFECT."""
    assert (
        _extract_float(_SCORE_BULLET_TS, "SCORE_BULLET_NEUTRAL_MAX")
        == OPENING_INSIGHTS_MINOR_EFFECT
    )


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_min_games_matches_frontend() -> None:
    """The FE verdict floor matches the Insights candidate floor and the D-36 most-played
    floor, so every surfaced row can carry a verdict."""
    from app.services.stats_service import MOST_PLAYED_MIN_GAMES

    fe_floor = _extract_int(_OPENING_VERDICT_TS, "REPERTOIRE_MIN_GAMES_FOR_VERDICT")
    assert fe_floor == OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE == MOST_PLAYED_MIN_GAMES


def test_compute_confidence_bucket_is_single_implementation() -> None:
    """Structural assertion that
    score_confidence.compute_confidence_bucket is the only implementation of the
    Wilson score-test formula (migrated from trinomial Wald).
    The boundary behavior is exercised by tests/services/test_score_confidence.py.
    """
    from app.services import score_confidence

    assert hasattr(score_confidence, "compute_confidence_bucket"), (
        "score_confidence.compute_confidence_bucket must exist (Phase 76 D-06)"
    )

    # opening_insights_service must NOT define a local _compute_confidence
    from app.services import opening_insights_service

    assert not hasattr(opening_insights_service, "_compute_confidence"), (
        "_compute_confidence must be migrated to score_confidence (Phase 76 D-06); "
        "duplicate definition would re-introduce the formula divergence risk."
    )

    # openings_service must import compute_confidence_bucket (the second consumer)
    import inspect

    from app.services import openings_service

    source = inspect.getsource(openings_service)
    assert "compute_confidence_bucket" in source, (
        "openings_service must use the shared score_confidence helper (Phase 76 D-06); "
        "found no reference to compute_confidence_bucket."
    )
