"""CI-enforced parity: app/schemas/train.py telemetry caps must match frontend/src/lib/trainTelemetry.ts.

The frontend clamps durations and stamps the schema version before sending
(Phase 233 D-04), the server clamps again at the boundary. Change both sides
together; this test goes red when they drift. Values are regex-extracted from
trainTelemetry.ts, so the TS constants must stay plain integer literals
(`export const NAME = 1800000;`, no type annotation, no arithmetic).
"""

import re
from pathlib import Path

import pytest

from app.schemas.train import (
    REVIEW_TELEMETRY_SCHEMA_VERSION,
    TELEMETRY_CARDS_CAP,
    TELEMETRY_DURATION_CAP_MS,
    TELEMETRY_EXPLORE_MOVES_CAP,
    TELEMETRY_LINE_STEPS_CAP,
    TELEMETRY_SCHEMA_VERSION,
)

_TRAIN_TELEMETRY_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/trainTelemetry.ts"

# (constant name, Python value).
_MIRRORED_CONSTANTS: tuple[tuple[str, int], ...] = (
    ("TELEMETRY_SCHEMA_VERSION", TELEMETRY_SCHEMA_VERSION),
    ("REVIEW_TELEMETRY_SCHEMA_VERSION", REVIEW_TELEMETRY_SCHEMA_VERSION),
    ("TELEMETRY_DURATION_CAP_MS", TELEMETRY_DURATION_CAP_MS),
    ("TELEMETRY_LINE_STEPS_CAP", TELEMETRY_LINE_STEPS_CAP),
    ("TELEMETRY_EXPLORE_MOVES_CAP", TELEMETRY_EXPLORE_MOVES_CAP),
    ("TELEMETRY_CARDS_CAP", TELEMETRY_CARDS_CAP),
)


def _extract_int(name: str) -> int:
    """Extract `export const NAME = <int>;` from trainTelemetry.ts."""
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", _TRAIN_TELEMETRY_TS.read_text())
    assert m, f"could not find export const {name} in trainTelemetry.ts"
    return int(m.group(1))


@pytest.mark.parametrize(("name", "python_value"), _MIRRORED_CONSTANTS)
def test_telemetry_constant_matches_frontend(name: str, python_value: int) -> None:
    assert _extract_int(name) == python_value
