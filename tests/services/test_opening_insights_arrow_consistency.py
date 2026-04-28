"""CI-enforced consistency: opening_insights_constants must match
frontend/src/lib/arrowColor.ts. Catches future score-threshold drift
between the backend classifier (Phase 75) and the board arrow colors
(Phase 76). Float values, regex-extracted from arrowColor.ts."""

import re
from pathlib import Path

import pytest

_ARROW_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/arrowColor.ts"

# Import lazily so the file is always collectable, but tests skip if the
# constants module is missing (e.g. during initial Phase 75 Plan 01 mid-flight).
try:
    from app.services.opening_insights_constants import (
        OPENING_INSIGHTS_MAJOR_EFFECT,
        OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
        OPENING_INSIGHTS_MINOR_EFFECT,
        OPENING_INSIGHTS_SCORE_PIVOT,
    )

    _CONSTANTS_AVAILABLE = True
except ImportError:
    _CONSTANTS_AVAILABLE = False
    OPENING_INSIGHTS_SCORE_PIVOT: float = 0.0  # type: ignore[assignment]
    OPENING_INSIGHTS_MINOR_EFFECT: float = 0.0  # type: ignore[assignment]
    OPENING_INSIGHTS_MAJOR_EFFECT: float = 0.0  # type: ignore[assignment]
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 0  # type: ignore[assignment]


def _extract_float(name: str) -> float:
    """Extract `export const NAME = <float>;` from arrowColor.ts."""
    text = _ARROW_TS.read_text()
    # Match floats like 0.50, .05, 1, 10, 0.10
    m = re.search(rf"export\s+const\s+{name}\s*=\s*([0-9]*\.?[0-9]+)\s*;", text)
    assert m, f"could not find export const {name} in arrowColor.ts"
    return float(m.group(1))


def _extract_int(name: str) -> int:
    """Extract `export const NAME = <int>;` from arrowColor.ts."""
    text = _ARROW_TS.read_text()
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", text)
    assert m, f"could not find export const {name} in arrowColor.ts"
    return int(m.group(1))


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_score_pivot_matches_frontend() -> None:
    """SCORE_PIVOT must match OPENING_INSIGHTS_SCORE_PIVOT (D-13)."""
    assert _extract_float("SCORE_PIVOT") == OPENING_INSIGHTS_SCORE_PIVOT


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_minor_effect_matches_frontend() -> None:
    """MINOR_EFFECT_SCORE must match OPENING_INSIGHTS_MINOR_EFFECT (D-13)."""
    assert _extract_float("MINOR_EFFECT_SCORE") == OPENING_INSIGHTS_MINOR_EFFECT


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_major_effect_matches_frontend() -> None:
    """MAJOR_EFFECT_SCORE must match OPENING_INSIGHTS_MAJOR_EFFECT (D-13)."""
    assert _extract_float("MAJOR_EFFECT_SCORE") == OPENING_INSIGHTS_MAJOR_EFFECT


@pytest.mark.skipif(not _CONSTANTS_AVAILABLE, reason="constants module not yet available")
def test_min_games_matches_frontend() -> None:
    """MIN_GAMES_FOR_COLOR must match OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE (D-13)."""
    assert _extract_int("MIN_GAMES_FOR_COLOR") == OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE


def test_compute_confidence_bucket_is_single_implementation() -> None:
    """Phase 76 D-22 fallback: structural assertion that
    score_confidence.compute_confidence_bucket is the only implementation of the
    trinomial Wald formula. The boundary behavior is exercised by
    tests/services/test_score_confidence.py.
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

    # openings_service must import compute_confidence_bucket (the second consumer per D-05/D-06)
    import inspect

    from app.services import openings_service

    source = inspect.getsource(openings_service)
    assert "compute_confidence_bucket" in source, (
        "openings_service must use the shared score_confidence helper (Phase 76 D-06); "
        "found no reference to compute_confidence_bucket."
    )
