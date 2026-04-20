"""Consistency test: FE inline constants match the Python zone registry.

Regex-parses the two FE consumer TSX files (EndgameScoreGapSection.tsx and
EndgameClockPressureSection.tsx) and asserts their inline constants
(FIXED_GAUGE_ZONES, ENDGAME_SKILL_ZONES, NEUTRAL_PCT_THRESHOLD,
NEUTRAL_TIMEOUT_THRESHOLD) equal the Python registry values.

This test is throwaway — it gets deleted when Phase 66 switches FE consumers to
import from frontend/src/generated/endgameZones.ts. Until then, it catches
drift that the CI diff guard on the generated TS file can't see (the inline
FE constants are a separate source, not the generated mirror).
"""

import re
from pathlib import Path

import pytest

from app.services.endgame_zones import (
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    ZONE_REGISTRY,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCORE_GAP_TSX = _REPO_ROOT / "frontend/src/components/charts/EndgameScoreGapSection.tsx"
_CLOCK_TSX = _REPO_ROOT / "frontend/src/components/charts/EndgameClockPressureSection.tsx"


class TestFERegistryConsistency:
    """Assert FE inline constants match Python registry (thrown away in Phase 66)."""

    def test_conversion_typical_lower(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(r"conversion:\s*\[.*?from:\s*0,\s*to:\s*([\d.]+)", src, re.DOTALL)
        assert m, "conversion bucket not found in FIXED_GAUGE_ZONES"
        assert float(m.group(1)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["conversion_win_pct"]["conversion"].typical_lower
        )

    def test_conversion_typical_upper(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(
            r"conversion:\s*\[.*?to:\s*[\d.]+.*?from:\s*[\d.]+,\s*to:\s*([\d.]+)",
            src,
            re.DOTALL,
        )
        assert m
        assert float(m.group(1)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["conversion_win_pct"]["conversion"].typical_upper
        )

    def test_parity_typical_lower(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(r"parity:\s*\[.*?from:\s*0,\s*to:\s*([\d.]+)", src, re.DOTALL)
        assert m
        assert float(m.group(1)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["parity_score_pct"]["parity"].typical_lower
        )

    def test_parity_typical_upper(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(
            r"parity:\s*\[.*?to:\s*[\d.]+.*?from:\s*[\d.]+,\s*to:\s*([\d.]+)",
            src,
            re.DOTALL,
        )
        assert m
        assert float(m.group(1)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["parity_score_pct"]["parity"].typical_upper
        )

    def test_recovery_typical_lower_d10(self) -> None:
        """D-10: recovery band re-centered to [0.25, 0.35] in BOTH sources."""
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(r"recovery:\s*\[.*?from:\s*0,\s*to:\s*([\d.]+)", src, re.DOTALL)
        assert m
        fe_val = float(m.group(1))
        py_val = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"].typical_lower
        assert fe_val == pytest.approx(py_val), (
            f"Recovery typical_lower mismatch: FE={fe_val}, Python={py_val}. "
            "Did D-10 edit land in both sources?"
        )

    def test_recovery_typical_upper_d10(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(
            r"recovery:\s*\[.*?to:\s*[\d.]+.*?from:\s*[\d.]+,\s*to:\s*([\d.]+)",
            src,
            re.DOTALL,
        )
        assert m
        fe_val = float(m.group(1))
        py_val = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"].typical_upper
        assert fe_val == pytest.approx(py_val)

    def test_endgame_skill_lower_boundary(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(
            r"ENDGAME_SKILL_ZONES[^\[]*\[.*?from:\s*0,\s*to:\s*([\d.]+)",
            src,
            re.DOTALL,
        )
        assert m
        assert float(m.group(1)) == pytest.approx(ZONE_REGISTRY["endgame_skill"].typical_lower)

    def test_endgame_skill_upper_boundary(self) -> None:
        src = _SCORE_GAP_TSX.read_text(encoding="utf-8")
        m = re.search(
            r"ENDGAME_SKILL_ZONES[^\[]*\[.*?to:\s*[\d.]+.*?from:\s*[\d.]+,\s*to:\s*([\d.]+)",
            src,
            re.DOTALL,
        )
        assert m
        assert float(m.group(1)) == pytest.approx(ZONE_REGISTRY["endgame_skill"].typical_upper)

    def test_neutral_pct_threshold(self) -> None:
        src = _CLOCK_TSX.read_text(encoding="utf-8")
        m = re.search(r"NEUTRAL_PCT_THRESHOLD\s*=\s*([\d.]+)", src)
        assert m, "NEUTRAL_PCT_THRESHOLD not found in EndgameClockPressureSection.tsx"
        assert float(m.group(1)) == pytest.approx(NEUTRAL_PCT_THRESHOLD)

    def test_neutral_timeout_threshold(self) -> None:
        src = _CLOCK_TSX.read_text(encoding="utf-8")
        m = re.search(r"NEUTRAL_TIMEOUT_THRESHOLD\s*=\s*([\d.]+)", src)
        assert m
        assert float(m.group(1)) == pytest.approx(NEUTRAL_TIMEOUT_THRESHOLD)
