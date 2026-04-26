"""CI-enforced consistency: opening_insights_service constants must match
frontend/src/lib/arrowColor.ts. Catches future arrow-color drift."""

import re
from pathlib import Path

import pytest

_ARROW_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/arrowColor.ts"

# Import lazily so the file is always collectable, but tests skip if service missing.
try:
    from app.services.opening_insights_service import DARK_THRESHOLD, LIGHT_THRESHOLD

    _SERVICE_AVAILABLE = True
except ImportError:
    _SERVICE_AVAILABLE = False
    LIGHT_THRESHOLD: float = 0.0  # type: ignore[assignment]
    DARK_THRESHOLD: float = 0.0  # type: ignore[assignment]


def _extract(name: str) -> int:
    text = _ARROW_TS.read_text()
    m = re.search(rf"{name}\s*=\s*(\d+)", text)
    assert m, f"could not find {name} in arrowColor.ts"
    return int(m.group(1))


@pytest.mark.skipif(not _SERVICE_AVAILABLE, reason="Wave 0 — service module not yet implemented")
def test_light_threshold_matches_frontend() -> None:
    assert _extract("LIGHT_COLOR_THRESHOLD") == int(LIGHT_THRESHOLD * 100)


@pytest.mark.skipif(not _SERVICE_AVAILABLE, reason="Wave 0 — service module not yet implemented")
def test_dark_threshold_matches_frontend() -> None:
    assert _extract("DARK_COLOR_THRESHOLD") == int(DARK_THRESHOLD * 100)
