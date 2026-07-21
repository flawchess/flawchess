"""Bot-strength lookup-curve generator tests (D-01/D-02/D-06/D-07/D-08/D-10). Phase 181 Plan 01.

Pure-function unit tests over `scripts.gen_bot_strength_curves` — no DB, no
engines, no TSV files on disk. Uses small in-memory synthetic points for the
PAVA/offset/inversion behaviors, plus the real frozen
reports/data/bot-curves-internal-scale.json for the cell-retention check.
Mirrors tests/scripts/test_calibration_anchor_fit.py's "public API import, not
CLI-only" convention; purely synchronous (no asyncio marker) since the fit is
pure stdlib math over static data.

Tests cover (one function per behavior):
- test_pava_pools_light_dip: PAVA pools Light's non-monotone bot_elo 1100/1300
  pair into one block (D-07).
- test_pava_deep_plateau_is_ceiling: PAVA pools Deep's 2300/2600 dip into its
  ceiling block (D-07).
- test_pava_human_noop: PAVA is a no-op on Human's already-monotone points.
- test_inversion_lowest_bot_elo_wins: inversion returns the LOWEST bot_elo in a
  plateau/merged block, never the highest (D-07).
- test_offset_uses_pooled_g_not_per_cell_or_vs_sf: offset subtracts the pooled
  g_preset_combined starting from rating_vs_maia (D-01).
- test_all_cells_retained: all 5 measured cells per preset (including the two
  Human beyond_ladder cells) are present after loading — none dropped (D-08).
- test_range_rounds_inward: range floor rounds UP, ceiling rounds DOWN to the
  nearest GRID_STEP (D-10) — asserts the rounding RULE, not a hardcoded number.
- test_preset_band_derives_from_c_and_mean_ci_halfwidth: the band is derived
  from C_UNCERTAINTY_HALF_BAND + mean CI half-width, not a hardcoded number.
- test_loader_fails_loud_on_missing_cells: load_internal_scale raises ValueError
  naming the missing field on empty 'cells' / missing 'per_preset'.
- test_json_has_components_and_derived: the lookup JSON payload has both a
  `components` and a `derived` section, each covering all three presets (D-02).
- test_disclaimer_present_both_outputs: APPROX_ELO_DISCLAIMER appears verbatim
  in both the JSON payload and the TS render (D-06).
- test_render_is_deterministic: rendering the real frozen fixture twice yields
  byte-identical JSON and TS (the invariant the CI drift check relies on).
- test_deep_range_ceiling_below_1900: sanity check against D-07 — Deep's
  measured plateau must not be marketed as reaching the seed's hoped ~2600.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.gen_bot_strength_curves import (
    GRID_STEP,
    _INPUT,
    APPROX_ELO_DISCLAIMER,
    approx_blitz_points,
    compute_artifact,
    invert_lookup,
    isotonic_fit,
    load_internal_scale,
    preset_band,
    _render_lookup_json,
    _render_ts,
)

# Named tolerances (no magic numbers in assertions below).
FIT_VALUE_TOLERANCE = 0.05  # rating points; PAVA pooled-mean arithmetic is exact float math
OFFSET_TOLERANCE = 0.05

# Real Phase-180 measured points, rating_vs_maia, sorted ascending by bot_elo
# (RESEARCH.md Pattern 2 — hand-verified against reports/data/bot-curves-internal-scale.json).
LIGHT_POINTS = [
    (1100.0, 1638.8857921090334),
    (1300.0, 1512.799070855996),
    (1500.0, 1604.9588103460424),
    (1700.0, 1608.3062011102434),
    (1900.0, 1783.4932121675113),
]
DEEP_POINTS = [
    (1100.0, 1783.4932121675113),
    (1500.0, 1966.5462349734019),
    (1900.0, 1991.9470260676576),
    (2300.0, 2118.2517211716095),
    (2600.0, 2064.2873232082993),
]
HUMAN_POINTS = [
    (700.0, 882.1991289099648),
    (1100.0, 1006.242446396252),
    (1500.0, 1143.0499118913096),
    (1900.0, 1405.0476538550313),
    (2300.0, 1474.4617525888584),
]

# Human's per_preset.g_preset_combined vs its bot_elo=700 per-cell g_preset —
# the two must differ (D-01: the fit uses the pooled value, never the per-cell one).
HUMAN_G_PRESET_COMBINED = 40.947876930543565
HUMAN_BOT_ELO_700_G_PRESET = 108.07089014379801


def test_pava_pools_light_dip() -> None:
    blocks = isotonic_fit(LIGHT_POINTS)
    # bot_elo 1100 (1638.89) > bot_elo 1300 (1512.80) violates monotonicity —
    # PAVA must pool them into ONE block valued at their weighted mean.
    assert blocks[0].x_lo == 1100.0
    assert blocks[0].x_hi == 1300.0
    assert blocks[0].weight == 2.0
    expected_pooled = (1638.8857921090334 + 1512.799070855996) / 2
    assert blocks[0].value == pytest.approx(expected_pooled, abs=FIT_VALUE_TOLERANCE)
    # The remaining three points stay singleton blocks (already non-decreasing).
    assert [b.x_lo for b in blocks[1:]] == [1500.0, 1700.0, 1900.0]
    # Fit is non-decreasing overall.
    values = [b.value for b in blocks]
    assert values == sorted(values)


def test_pava_deep_plateau_is_ceiling() -> None:
    blocks = isotonic_fit(DEEP_POINTS)
    # bot_elo 2300 (2118.25) > bot_elo 2600 (2064.29) violates monotonicity —
    # PAVA pools them into Deep's ceiling (plateau) block.
    assert blocks[-1].x_lo == 2300.0
    assert blocks[-1].x_hi == 2600.0
    assert blocks[-1].weight == 2.0
    expected_pooled = (2118.2517211716095 + 2064.2873232082993) / 2
    assert blocks[-1].value == pytest.approx(expected_pooled, abs=FIT_VALUE_TOLERANCE)
    values = [b.value for b in blocks]
    assert values == sorted(values)


def test_pava_human_noop() -> None:
    blocks = isotonic_fit(HUMAN_POINTS)
    # Human's raw points are already non-decreasing — PAVA must not merge anything.
    assert len(blocks) == len(HUMAN_POINTS)
    for block, (x, y) in zip(blocks, HUMAN_POINTS, strict=True):
        assert block.x_lo == block.x_hi == x
        assert block.value == pytest.approx(y, abs=FIT_VALUE_TOLERANCE)


def test_inversion_lowest_bot_elo_wins() -> None:
    # bot_elo 1200 (1500) > bot_elo 1400 (1300) violates monotonicity, so PAVA
    # pools them into a plateau block spanning bot_elo 1200-1400; bot_elo 1000
    # stays a separate, lower singleton block.
    blocks = isotonic_fit([(1000.0, 1000.0), (1200.0, 1500.0), (1400.0, 1300.0)])
    assert len(blocks) == 2
    assert blocks[-1].x_lo == 1200.0
    assert blocks[-1].x_hi == 1400.0

    lookup = invert_lookup(blocks, g_preset_combined=0.0, c=0.0)
    # A target landing inside the plateau (approx_blitz 1200-1400) must resolve
    # to the LOWEST bot_elo in that block (1200), never the highest (1400) or a
    # midpoint. Reverting invert_lookup's x_lo tie-break to x_hi would make
    # this assertion fail.
    assert lookup[1300] == 1200


def test_offset_uses_pooled_g_not_per_cell_or_vs_sf() -> None:
    blocks = isotonic_fit(HUMAN_POINTS)
    c = 40.0
    approx = approx_blitz_points(blocks, HUMAN_G_PRESET_COMBINED, c)
    first_bot_elo, first_blitz = approx[0]
    assert first_bot_elo == 700.0
    # D-01: offset subtracts the POOLED g, not the noisier per-cell g.
    expected = HUMAN_POINTS[0][1] - HUMAN_G_PRESET_COMBINED + c
    assert first_blitz == pytest.approx(expected, abs=OFFSET_TOLERANCE)
    wrong_with_per_cell_g = HUMAN_POINTS[0][1] - HUMAN_BOT_ELO_700_G_PRESET + c
    assert first_blitz != pytest.approx(wrong_with_per_cell_g, abs=OFFSET_TOLERANCE)


def test_all_cells_retained() -> None:
    payload = load_internal_scale(str(_INPUT))
    by_blend: dict[float, list[dict]] = {}
    for cell in payload["cells"]:
        by_blend.setdefault(float(cell["bot_blend"]), []).append(cell)
    for blend in (0.0, 0.05, 0.5):
        cells = by_blend[blend]
        assert len(cells) == 5, f"blend {blend} has {len(cells)} cells, expected 5"
    # D-08: the two Human beyond_ladder cells (bot_elo 700, 1100) are present, not dropped.
    human_beyond_ladder_elos = {c["bot_elo"] for c in by_blend[0.0] if c.get("beyond_ladder")}
    assert human_beyond_ladder_elos == {700, 1100}


def test_range_rounds_inward() -> None:
    blocks = isotonic_fit(HUMAN_POINTS)
    lookup = invert_lookup(blocks, HUMAN_G_PRESET_COMBINED, 40.0)
    approx = approx_blitz_points(blocks, HUMAN_G_PRESET_COMBINED, 40.0)
    first_blitz = approx[0][1]
    last_blitz = approx[-1][1]

    import math

    expected_floor = math.ceil(first_blitz / GRID_STEP) * GRID_STEP
    expected_ceiling = math.floor(last_blitz / GRID_STEP) * GRID_STEP
    assert min(lookup) == expected_floor
    assert max(lookup) == expected_ceiling
    # The rounding RULE, not a hardcoded number: floor must round UP (>= raw
    # value), ceiling must round DOWN (<= raw value).
    assert expected_floor >= first_blitz
    assert expected_ceiling <= last_blitz


def test_preset_band_derives_from_c_and_mean_ci_halfwidth() -> None:
    cells = [
        {"ci_vs_maia": [900.0, 1100.0]},  # halfwidth 100
        {"ci_vs_maia": [950.0, 1050.0]},  # halfwidth 50
    ]
    # (C_UNCERTAINTY_HALF_BAND=100 + mean halfwidth 75) / 25 rounded * 25 = 175.
    assert preset_band(cells) == 175


def test_loader_fails_loud_on_missing_cells(tmp_path: Path) -> None:
    empty_cells = tmp_path / "empty-cells.json"
    empty_cells.write_text(json.dumps({"cells": [], "per_preset": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="cells"):
        load_internal_scale(str(empty_cells))

    missing_per_preset = tmp_path / "missing-per-preset.json"
    missing_per_preset.write_text(
        json.dumps({"cells": [{"bot_elo": 1100, "bot_blend": 0.0}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="per_preset"):
        load_internal_scale(str(missing_per_preset))


def _real_artifact() -> dict:
    payload = load_internal_scale(str(_INPUT))
    return compute_artifact(payload)


def test_json_has_components_and_derived() -> None:
    artifact = _real_artifact()
    assert set(artifact) == {"components", "derived", "disclaimer"}
    for name in ("human", "light", "deep"):
        assert name in artifact["components"]
        assert name in artifact["derived"]
        assert "range" in artifact["derived"][name]
        assert artifact["derived"][name]["lookup"]  # non-empty


def test_disclaimer_present_both_outputs() -> None:
    artifact = _real_artifact()
    json_text = _render_lookup_json(artifact)
    ts_text = _render_ts(artifact)
    assert APPROX_ELO_DISCLAIMER in json_text
    assert json.dumps(APPROX_ELO_DISCLAIMER) in ts_text


def test_render_is_deterministic() -> None:
    artifact_first = _real_artifact()
    artifact_second = _real_artifact()
    assert _render_lookup_json(artifact_first) == _render_lookup_json(artifact_second)
    assert _render_ts(artifact_first) == _render_ts(artifact_second)


def test_deep_range_ceiling_below_1900() -> None:
    # D-07 sanity check: Deep's measured plateau (~1950-2100 internal) must not
    # be marketed as reaching the seed's hoped ~2600 approx-blitz.
    artifact = _real_artifact()
    assert artifact["derived"]["deep"]["range"]["ceiling"] < 1900
