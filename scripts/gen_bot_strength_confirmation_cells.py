"""Generate the off-grid confirmation-cell prediction file (D-11/D-12/D-13).

Sibling to scripts/gen_bot_strength_curves.py (Plan 01) — reuses its fit
machinery (isotonic_fit, approx_blitz_points, load_internal_scale,
compute_artifact, PRESETS, BLITZ_OFFSET_C, GRID_STEP) rather than
re-implementing any of it (D-05: gen_bot_strength_curves.py is never modified
by this script).

For each preset, picks 2-3 deterministic off-grid target blitz ELOs inside the
shipped lookup range (D-12), interpolates the PREDICTED bot_elo along the
fitted approx-blitz curve (an off-grid inverse — contrast Plan 01's
invert_lookup, which snaps to the lowest grid-aligned bot_elo reaching a
target), predicts the internal rating at that bot_elo, and computes an honest
interpolated 95% CI (D-13). Emits a self-documenting JSON the operator runs as
HUMAN-UAT: reports/data/bot-strength-confirmation-predictions.json, each row
carrying the exact scripts/calibration-harness.mjs + calibration_anchor_fit.py
commands to run it.

D-12 target selection (deterministic, no hand-picked magic numbers):
    Per preset, pick `floor + GRID_STEP`, the midpoint rounded to the nearest
    GRID_STEP, and `ceiling - GRID_STEP` (from Plan 01's lookup `range`) when
    the range spans >= MIDPOINT_TARGET_MIN_GRID_STEPS grid steps. When it
    spans fewer (Light's real shipped range is only ~1 GRID_STEP wide, Deep's
    only ~2 — narrower than the literal formula can honor without landing ON
    the floor/ceiling themselves), falls back to two targets 1/3 and 2/3 of
    the way across the range — still strictly interior, still deterministic,
    just not necessarily GRID_STEP-aligned when the range itself is narrower
    than one full GRID_STEP multiple.

D-13 interpolated 95% CI rule (resolves RESEARCH.md Open Question 1 / A1):
    For a predicted off-grid bot_elo that falls INSIDE a merged PAVA block (a
    plateau — the block's x_lo != x_hi), pool the merged member cells'
    ci_vs_maia bounds by inverse-variance weighting: weight each cell by
    1 / half_width^2 (half_width = (ci_hi - ci_lo) / 2, the same technique
    calibration_anchor_fit.py's combine_preset_g_preset uses for
    G_preset_combined), pool the center as the weighted mean of rating_vs_maia,
    then WIDEN the resulting band beyond the standard inverse-variance combined
    standard error by adding the between-cell spread of the pooled points'
    own rating_vs_maia values. This is deliberate: PAVA only merges cells
    BECAUSE their unpooled values disagree with monotonicity, so treating them
    as independent noisy estimates of one shared "block truth" (the standard
    inverse-variance formula alone) would understate real uncertainty — the
    plateau genuinely IS less certain than either measured point alone
    (RESEARCH.md Pitfall 3). The resulting band is always at least as wide as
    either individual merged cell's own CI. For a bot_elo that falls BETWEEN
    two distinct (non-merged) blocks, linearly interpolate each bound between
    the two neighboring blocks' own (possibly pooled) CIs, using the same
    x_lo-to-x_lo fraction the point-estimate interpolation uses.

Usage (local dev, writes the prediction file):
    uv run python scripts/gen_bot_strength_confirmation_cells.py

Usage (drift check — exits 1 if the committed file differs from a fresh render):
    uv run python scripts/gen_bot_strength_confirmation_cells.py --check
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.gen_bot_strength_curves import (  # noqa: E402
    BLITZ_OFFSET_C,
    GRID_STEP,
    PRESETS,
    _Block,
    _INPUT,
    approx_blitz_points,
    compute_artifact,
    isotonic_fit,
    load_internal_scale,
)

_PREDICTIONS_JSON = _REPO_ROOT / "reports" / "data" / "bot-strength-confirmation-predictions.json"

# D-12: >= this many GRID_STEPs wide gets a 3rd (midpoint) target; narrower
# ranges (Light/Deep's real shipped ranges) fall back to a two-target split.
MIDPOINT_TARGET_MIN_GRID_STEPS = 3

# RESEARCH.md's "Confirmation-cell operator invocation" example invocation.
GAMES_PER_CELL = 24
STOCKFISH_PROCS = 4

# Same 95% z-score constant as calibration_anchor_fit.py's NORMAL_95_Z, needed
# here to convert a stored ci_vs_maia half-width back to a standard error.
NORMAL_95_Z = 1.959963985

PASS_CRITERION = (
    "D-13: the confirmation cell's measured rating_vs_maia (same fit basis as "
    "the shipped lookup) must fall within [ci95_lo, ci95_hi] recorded below. "
    "On failure, fold the confirmation games into the fit dataset and re-run "
    "scripts/gen_bot_strength_curves.py to regenerate the lookup + TS artifact "
    "(D-14) -- no hand-tuning, no band-widening to paper over a miss."
)


def select_confirmation_targets(preset_range: dict[str, int]) -> list[int]:
    """D-12 deterministic off-grid target picker. See module docstring."""
    floor = preset_range["floor"]
    ceiling = preset_range["ceiling"]
    span = ceiling - floor
    if span >= MIDPOINT_TARGET_MIN_GRID_STEPS * GRID_STEP:
        midpoint = round((floor + ceiling) / 2 / GRID_STEP) * GRID_STEP
        targets = [floor + GRID_STEP, midpoint, ceiling - GRID_STEP]
        deduped: list[int] = []
        for target in targets:
            if target not in deduped:
                deduped.append(target)
        return deduped

    offset = max(1, round(span / 3))
    first = floor + offset
    second = ceiling - offset
    if second <= first:
        second = first + 1
    return [first, second]


def interpolate_bot_elo(approx_points: list[tuple[float, float]], target: float) -> float:
    """Off-grid inverse: linear interpolation of bot_elo at `target` blitz ELO
    along the fitted approx-blitz curve. `approx_points` must be pre-sorted
    ascending by bot_elo (approx_blitz_points already returns them that way).

    Contrast Plan 01's invert_lookup, which snaps to the LOWEST grid-aligned
    bot_elo reaching a target (D-07's lowest-wins tie-break for the shipped
    lookup) — this function instead interpolates strictly between the two
    bracketing measured points, so a target strictly inside a bracket yields a
    bot_elo strictly between two grid points: the true test of the shipped
    inversion (D-11/D-12).
    """
    for i in range(len(approx_points) - 1):
        x1, y1 = approx_points[i]
        x2, y2 = approx_points[i + 1]
        if y1 <= target <= y2:
            fraction = (target - y1) / (y2 - y1)
            return x1 + fraction * (x2 - x1)
    raise ValueError(f"interpolate_bot_elo: target {target} outside fitted curve range")


def interpolate_internal(blocks: list[_Block], bot_elo: float) -> float:
    """Predicted internal rating at bot_elo: flat within a merged PAVA block
    (plateaus are flat by construction, D-07 -- never invent slope inside a
    measured plateau), else linearly interpolated between the two neighboring
    blocks' (x_lo, value) points."""
    for block in blocks:
        if block.x_lo <= bot_elo <= block.x_hi:
            return block.value
    for i in range(len(blocks) - 1):
        b1, b2 = blocks[i], blocks[i + 1]
        if b1.x_lo <= bot_elo <= b2.x_lo:
            fraction = (bot_elo - b1.x_lo) / (b2.x_lo - b1.x_lo)
            return b1.value + fraction * (b2.value - b1.value)
    raise ValueError(f"interpolate_internal: bot_elo {bot_elo} outside fitted block range")


def _pooled_ci(cells: list[dict[str, Any]]) -> tuple[float, float]:
    """Inverse-variance-pooled, spread-widened CI for a merged PAVA plateau's
    member cells. See the module docstring's D-13 section for the full rule
    and rationale."""
    centers = [float(c["rating_vs_maia"]) for c in cells]
    half_widths = [(c["ci_vs_maia"][1] - c["ci_vs_maia"][0]) / 2.0 for c in cells]
    ses = [hw / NORMAL_95_Z for hw in half_widths]
    weights = [1.0 / (se * se) for se in ses]
    weight_total = sum(weights)
    pooled_center = sum(w * c for w, c in zip(weights, centers, strict=True)) / weight_total
    pooled_se = math.sqrt(1.0 / weight_total)
    spread_half_width = (max(centers) - min(centers)) / 2.0
    pooled_half_width = spread_half_width + NORMAL_95_Z * pooled_se
    return (pooled_center - pooled_half_width, pooled_center + pooled_half_width)


def _block_ci(preset_cells: list[dict[str, Any]], block: _Block) -> tuple[float, float]:
    """Block-level 95% CI: a singleton block's own cell CI, or the
    inverse-variance-pooled CI of a merged PAVA plateau's member cells."""
    members = [c for c in preset_cells if block.x_lo <= c["bot_elo"] <= block.x_hi]
    if len(members) == 1:
        lo, hi = members[0]["ci_vs_maia"]
        return (float(lo), float(hi))
    return _pooled_ci(members)


def interpolate_ci(
    preset_cells: list[dict[str, Any]], blocks: list[_Block], bot_elo: float
) -> tuple[float, float]:
    """Locked D-13 interpolated 95% CI rule. See module docstring for the full
    rationale."""
    for block in blocks:
        if block.x_lo <= bot_elo <= block.x_hi:
            return _block_ci(preset_cells, block)
    for i in range(len(blocks) - 1):
        b1, b2 = blocks[i], blocks[i + 1]
        if b1.x_lo <= bot_elo <= b2.x_lo:
            lo1, hi1 = _block_ci(preset_cells, b1)
            lo2, hi2 = _block_ci(preset_cells, b2)
            fraction = (bot_elo - b1.x_lo) / (b2.x_lo - b1.x_lo)
            return (lo1 + fraction * (lo2 - lo1), hi1 + fraction * (hi2 - hi1))
    raise ValueError(f"interpolate_ci: bot_elo {bot_elo} outside fitted block range")


def _group_cells_by_preset(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Groups+sorts payload['cells'] by preset name, ascending bot_elo. Mirrors
    gen_bot_strength_curves.compute_artifact's own grouping -- needed here
    because interpolate_ci needs the raw per-cell ci_vs_maia/rating_vs_maia
    rows, which compute_artifact's returned components/derived structure does
    not expose."""
    cells_by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in PRESETS.values()}
    for cell in payload["cells"]:
        blend = float(cell["bot_blend"])
        cells_by_name[PRESETS[blend]].append(cell)
    for cells in cells_by_name.values():
        cells.sort(key=lambda c: c["bot_elo"])
    return cells_by_name


def _build_row(
    name: str,
    blend: float,
    target: int,
    approx_points: list[tuple[float, float]],
    blocks: list[_Block],
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    """Builds one confirmation-cell prediction row for `target` blitz ELO."""
    predicted_bot_elo = int(round(interpolate_bot_elo(approx_points, target)))
    predicted_internal = interpolate_internal(blocks, predicted_bot_elo)
    ci95_lo, ci95_hi = interpolate_ci(cells, blocks, predicted_bot_elo)
    out_dir = f"reports/data/confirmation-{name}-{predicted_bot_elo}"
    return {
        "preset": name,
        "blend": blend,
        "target_blitz_elo": target,
        "predicted_bot_elo": predicted_bot_elo,
        "predicted_internal": predicted_internal,
        "ci95_lo": ci95_lo,
        "ci95_hi": ci95_hi,
        "harness_cmd": (
            "node --import ./scripts/lib/frontend-alias-hook.mjs "
            f"scripts/calibration-harness.mjs --elo {predicted_bot_elo} "
            f"--blends {blend:g} --games-per-cell {GAMES_PER_CELL} "
            f"--stockfish-procs {STOCKFISH_PROCS} --out-dir {out_dir}"
        ),
        "fit_cmd": (
            "uv run python scripts/calibration_anchor_fit.py "
            f"--bot-input {out_dir}/*-cells.tsv "
            f"--out-bot-curves {out_dir}-fit.json"
        ),
    }


def compute_confirmation_predictions(payload: dict[str, Any]) -> dict[str, Any]:
    """Runs target-selection -> off-grid interpolation -> interpolated-CI for
    every preset. Reuses Plan 01's compute_artifact() for the shipped `range`
    (single source of truth for the floor/ceiling rounding rule, D-10) and
    isotonic_fit/approx_blitz_points for the fit itself -- never
    re-implemented here (D-05)."""
    artifact = compute_artifact(payload)
    cells_by_name = _group_cells_by_preset(payload)
    per_preset_payload = payload["per_preset"]

    rows: list[dict[str, Any]] = []
    for blend, name in PRESETS.items():
        cells = cells_by_name[name]
        points = [(float(c["bot_elo"]), float(c["rating_vs_maia"])) for c in cells]
        blocks = isotonic_fit(points)
        g_preset_combined = float(per_preset_payload[f"{blend:g}"]["g_preset_combined"])
        approx_points = approx_blitz_points(blocks, g_preset_combined, BLITZ_OFFSET_C)
        preset_range_entry = artifact["derived"][name]["range"]

        for target in select_confirmation_targets(preset_range_entry):
            rows.append(_build_row(name, blend, target, approx_points, blocks, cells))

    return {"pass_criterion": PASS_CRITERION, "rows": rows}


def _render_confirmation_json(predictions: dict[str, Any]) -> str:
    """Serializes the prediction payload as pretty-printed, deterministic JSON."""
    return json.dumps(predictions, indent=2) + "\n"


def main() -> None:
    check_mode = "--check" in sys.argv
    payload = load_internal_scale(str(_INPUT))
    predictions = compute_confirmation_predictions(payload)
    content = _render_confirmation_json(predictions)
    if check_mode:
        if (
            not _PREDICTIONS_JSON.exists()
            or _PREDICTIONS_JSON.read_text(encoding="utf-8") != content
        ):
            print(
                f"DRIFT: {_PREDICTIONS_JSON.relative_to(_REPO_ROOT)} is out of date. "
                "Run `uv run python scripts/gen_bot_strength_confirmation_cells.py` to regenerate.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"OK: {_PREDICTIONS_JSON.relative_to(_REPO_ROOT)} is up to date.")
    else:
        _PREDICTIONS_JSON.parent.mkdir(parents=True, exist_ok=True)
        _PREDICTIONS_JSON.write_text(content, encoding="utf-8")
        print(f"Wrote {_PREDICTIONS_JSON.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
