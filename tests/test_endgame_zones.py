"""Tests for PER_CLASS_TC_GAUGE_ZONES registry (Phase 98)."""

import pytest

from app.services.endgame_zones import (
    PER_CLASS_GAUGE_ZONES,
    PER_CLASS_TC_GAUGE_ZONES,
)

_VISIBLE_CLASSES = {"rook", "minor_piece", "pawn", "queen", "mixed"}
_TC_KEYS = {"bullet", "blitz", "rapid", "classical"}


def test_per_class_tc_gauge_zones_has_five_visible_classes() -> None:
    """PER_CLASS_TC_GAUGE_ZONES must cover exactly the 5 visible endgame classes."""
    assert set(PER_CLASS_TC_GAUGE_ZONES.keys()) == _VISIBLE_CLASSES


def test_per_class_tc_gauge_zones_pawnless_absent() -> None:
    """pawnless is below the per-(class × TC) floor and must be omitted."""
    assert "pawnless" not in PER_CLASS_TC_GAUGE_ZONES


def test_per_class_tc_gauge_zones_all_four_tc_keys() -> None:
    """Each class must have entries for all four time controls."""
    for cls, tc_map in PER_CLASS_TC_GAUGE_ZONES.items():
        assert set(tc_map.keys()) == _TC_KEYS, f"Class '{cls}' missing TC keys"


def test_per_class_gauge_zones_unchanged_pawnless_present() -> None:
    """PER_CLASS_GAUGE_ZONES is the LLM path's source of truth — must remain
    unchanged and still include pawnless (D-15)."""
    assert "pawnless" in PER_CLASS_GAUGE_ZONES
    # Spot-check the rook entry from the pooled bands
    rook = PER_CLASS_GAUGE_ZONES["rook"]
    assert rook.conversion == (0.65, 0.75)
    assert rook.recovery == (0.26, 0.36)


def test_per_class_tc_spot_check_rook_classical_conversion() -> None:
    """Spot-check: rook classical conversion band matches benchmark table."""
    assert PER_CLASS_TC_GAUGE_ZONES["rook"]["classical"].conversion == (0.74, 0.87)


def test_per_class_tc_spot_check_queen_classical_recovery() -> None:
    """Queen classical recovery is a small-n band (n≈30–35); accepted as-is."""
    assert PER_CLASS_TC_GAUGE_ZONES["queen"]["classical"].recovery == (0.00, 0.09)


def test_per_class_tc_band_fields_are_two_floats() -> None:
    """All band tuples must be (float, float) with lower < upper."""
    for cls, tc_map in PER_CLASS_TC_GAUGE_ZONES.items():
        for tc, bands in tc_map.items():
            for field_name, (lo, hi) in [
                ("conversion", bands.conversion),
                ("recovery", bands.recovery),
                ("achievable_score_gap", bands.achievable_score_gap),
            ]:
                assert isinstance(lo, float), f"{cls}/{tc}/{field_name} lower not float"
                assert isinstance(hi, float), f"{cls}/{tc}/{field_name} upper not float"
                assert lo < hi, f"{cls}/{tc}/{field_name}: lower {lo} >= upper {hi}"


@pytest.mark.parametrize("cls", sorted(_VISIBLE_CLASSES))
def test_per_class_tc_achievable_score_gap_consistent_across_tc(cls: str) -> None:
    """Score Gap TC d ≈ 0.07–0.18 (all collapse). The four ΔES bands per class
    are near-identical by design (redundancy chosen per D-04/D-14)."""
    from typing import Literal, cast

    endgame_class = cast(Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"], cls)
    tc_map = PER_CLASS_TC_GAUGE_ZONES[endgame_class]
    tc_order: list[Literal["bullet", "blitz", "rapid", "classical"]] = [
        "bullet",
        "blitz",
        "rapid",
        "classical",
    ]
    gaps = [tc_map[tc].achievable_score_gap for tc in tc_order]
    # All four TCs should have identical achievable_score_gap bands (TC d collapses)
    assert len(set(gaps)) == 1, (
        f"Class '{cls}': achievable_score_gap differs across TCs (expected identical): {gaps}"
    )
