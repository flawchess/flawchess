"""Confirmation-cell prediction generator tests (D-11/D-12/D-13). Phase 181 Plan 02.

Pure-function unit tests over `scripts.gen_bot_strength_confirmation_cells` --
no DB, no engines, no TSV files on disk. Uses small in-memory synthetic
points/cells for the target-selection and CI-pooling behaviors, plus the real
frozen reports/data/bot-curves-internal-scale.json for the
off-grid-vs-measured-grid check against the actual shipped prediction rows.
Mirrors tests/scripts/test_gen_bot_strength_curves.py's "public API import,
not CLI-only" convention; purely synchronous (no asyncio marker) since the fit
is pure stdlib math over static data.

Tests cover (one function per behavior):
- test_targets_off_grid_and_inside_range: select_confirmation_targets returns
  2-3 targets strictly inside [floor, ceiling], none equal to the endpoints
  (D-12), for both a wide (>=3 grid step) and a narrow (<3 grid step) range.
- test_predicted_bot_elo_not_on_measured_grid: every row's predicted_bot_elo
  in the real generated prediction payload is NOT one of its preset's 5
  measured bot_elo grid points (D-11/D-12) -- the true test of the off-grid
  inversion.
- test_plateau_ci_is_inverse_variance_pooled_not_lerp: interpolate_ci for a
  bot_elo inside a merged PAVA block returns the inverse-variance-pooled
  bound, provably different from (and wider than) a plain two-bound average
  (D-13).
- test_row_has_runbook_commands: every row carries target_blitz_elo,
  predicted_bot_elo, predicted_internal, ci95_lo/hi, harness_cmd, fit_cmd; the
  payload has a top-level pass_criterion.
- test_prediction_render_deterministic: rendering the real frozen fixture
  twice (and recomputing from scratch) yields byte-identical JSON.
"""

from __future__ import annotations

from typing import Any

from scripts.gen_bot_strength_confirmation_cells import (
    GRID_STEP,
    _INPUT,
    _pooled_ci,
    _render_confirmation_json,
    compute_confirmation_predictions,
    interpolate_ci,
    select_confirmation_targets,
)
from scripts.gen_bot_strength_curves import PRESETS, isotonic_fit, load_internal_scale

# Named tolerances (no magic numbers in assertions below).
FLOAT_TOLERANCE = 1e-6  # exact-arithmetic comparisons after pure float math

# Minimum row count: >=2 targets per preset, 3 presets (D-12).
MIN_ROWS_PER_PRESET = 2
PRESET_COUNT = 3


def test_targets_off_grid_and_inside_range() -> None:
    wide = select_confirmation_targets({"floor": 900, "ceiling": 1400})
    assert len(wide) == 3
    for target in wide:
        assert 900 < target < 1400
        assert target % GRID_STEP == 0
    assert len(set(wide)) == len(wide)

    narrow = select_confirmation_targets({"floor": 1500, "ceiling": 1600})
    assert len(narrow) == 2
    for target in narrow:
        assert 1500 < target < 1600
    assert len(set(narrow)) == len(narrow)


def test_predicted_bot_elo_not_on_measured_grid() -> None:
    payload = load_internal_scale(str(_INPUT))
    predictions = compute_confirmation_predictions(payload)

    measured_grid_by_preset: dict[str, set[int]] = {name: set() for name in PRESETS.values()}
    for cell in payload["cells"]:
        name = PRESETS[float(cell["bot_blend"])]
        measured_grid_by_preset[name].add(int(cell["bot_elo"]))

    assert len(predictions["rows"]) >= MIN_ROWS_PER_PRESET * PRESET_COUNT
    for row in predictions["rows"]:
        assert row["predicted_bot_elo"] not in measured_grid_by_preset[row["preset"]]


def test_plateau_ci_is_inverse_variance_pooled_not_lerp() -> None:
    # Two cells PAVA pools into one plateau block (non-monotone: y drops from
    # bot_elo 1100 to 1300, matching Light's real measured dip shape).
    cells: list[dict[str, Any]] = [
        {"bot_elo": 1100, "rating_vs_maia": 1638.89, "ci_vs_maia": [1532.95, 1757.77]},
        {"bot_elo": 1300, "rating_vs_maia": 1512.80, "ci_vs_maia": [1421.97, 1604.96]},
        {"bot_elo": 1500, "rating_vs_maia": 1605.0, "ci_vs_maia": [1520.64, 1698.80]},
    ]
    points = [(float(c["bot_elo"]), float(c["rating_vs_maia"])) for c in cells]
    blocks = isotonic_fit(points)
    plateau = blocks[0]
    assert plateau.x_lo == 1100.0
    assert plateau.x_hi == 1300.0  # confirms PAVA actually pooled these two cells

    lo, hi = interpolate_ci(cells, blocks, bot_elo=1200.0)  # strictly inside the plateau

    naive_lo = (1532.95 + 1421.97) / 2
    naive_hi = (1757.77 + 1604.96) / 2
    assert abs(lo - naive_lo) > FLOAT_TOLERANCE
    assert abs(hi - naive_hi) > FLOAT_TOLERANCE

    # Pooled band must be at least as wide as EITHER single merged cell's own
    # CI -- a genuinely divergent plateau is less certain than either
    # measured point alone (RESEARCH.md Pitfall 3), never narrower.
    assert (hi - lo) >= (1757.77 - 1532.95)
    assert (hi - lo) >= (1604.96 - 1421.97)

    # Revert-provability: swapping the rule to a plain average of the two
    # bounds changes the result -- proves the pooling rule is genuinely
    # exercised, not a no-op that happens to coincide with a lerp.
    reverted = _pooled_ci(cells[:2])
    naive_avg = (naive_lo, naive_hi)
    assert reverted != naive_avg
    assert (lo, hi) == reverted  # interpolate_ci delegates to _pooled_ci for this block


def test_row_has_runbook_commands() -> None:
    payload = load_internal_scale(str(_INPUT))
    predictions = compute_confirmation_predictions(payload)

    assert predictions["pass_criterion"]
    required_keys = {
        "preset",
        "blend",
        "target_blitz_elo",
        "predicted_bot_elo",
        "predicted_internal",
        "ci95_lo",
        "ci95_hi",
        "harness_cmd",
        "fit_cmd",
    }
    for row in predictions["rows"]:
        assert required_keys <= row.keys()
        assert "scripts/calibration-harness.mjs" in row["harness_cmd"]
        assert "scripts/calibration_anchor_fit.py" in row["fit_cmd"]
        assert str(row["predicted_bot_elo"]) in row["harness_cmd"]
        assert row["ci95_lo"] < row["predicted_internal"] < row["ci95_hi"]


def test_prediction_render_deterministic() -> None:
    payload = load_internal_scale(str(_INPUT))
    predictions = compute_confirmation_predictions(payload)
    first = _render_confirmation_json(predictions)
    second = _render_confirmation_json(predictions)
    assert first == second

    # Also stable across a fresh recompute, not just a re-render of one dict.
    third = _render_confirmation_json(compute_confirmation_predictions(payload))
    assert first == third
