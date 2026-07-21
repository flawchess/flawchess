"""Generate the shipping per-preset bot-strength lookup artifact.

Reads the frozen Phase-180 sweep output (reports/data/bot-curves-internal-scale.json:
15 measured cells across the Human/Light/Deep presets on the internal anchor-ladder
scale) and produces:

1. A monotone (Pool-Adjacent-Violators, hand-rolled — matches
   calibration_anchor_fit.py's stdlib-only convention) fit
   `internal_rating = f_preset(bot_elo)` per preset.
2. An approximate-human-blitz-ELO conversion via
   `approx_blitz = internal - G_preset_combined + C` (D-01: pooled G, never
   per-cell g_preset, never rating_vs_sf).
3. A `target_blitz_elo -> bot_elo` inversion in 100-ELO steps, lowest-bot_elo-wins
   on flat/plateau segments (D-07), with inward-rounded per-preset ranges (D-10).

Ships two artifacts: reports/data/bot-strength-lookup.json (components + derived,
D-02) and frontend/src/generated/botStrengthCurves.ts (generated TS mirror,
CI-drift-checked, D-04). Phase 180's reports/data/bot-curves-internal-scale.json
stays frozen upstream — this script only reads it (D-05: a clean new script, not
an extension of calibration_anchor_fit.py).

Usage (local dev, writes both artifacts):
    uv run python scripts/gen_bot_strength_curves.py

Usage (drift check — exits 1 if either committed output differs from a fresh render):
    uv run python scripts/gen_bot_strength_curves.py --check

Usage (CI drift check):
    uv run python scripts/gen_bot_strength_curves.py
    git diff --exit-code frontend/src/generated/botStrengthCurves.ts \\
                          reports/data/bot-strength-lookup.json
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INPUT = _REPO_ROOT / "reports" / "data" / "bot-curves-internal-scale.json"
_LOOKUP_JSON = _REPO_ROOT / "reports" / "data" / "bot-strength-lookup.json"
_TS_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "botStrengthCurves.ts"

# Blend -> shipping preset name (Phase 180-locked blend values: 0.0/0.05/0.5).
PRESETS: dict[float, str] = {0.0: "human", 0.05: "light", 0.5: "deep"}

# Every preset must consume exactly this many measured cells (D-08 — none may be
# silently dropped, including the beyond_ladder-flagged Human cells).
EXPECTED_CELLS_PER_PRESET = 5

# D-02: the shared internal-scale -> approx-blitz zero-point offset. A literature
# constant (SEED-104), NOT refit from data — retuning it is a one-line change +
# regenerate, no refit.
BLITZ_OFFSET_C = 40

# D-03: half-width of C's own uncertainty band, folded into preset_band().
C_UNCERTAINTY_HALF_BAND = 100

# D-10 / SEED-104: lookup granularity in ELO points, and the rounding grid for
# per-preset range endpoints (floor rounds UP, ceiling rounds DOWN).
GRID_STEP = 100

# D-03: preset_band() rounds its derived value to the nearest 25 ELO — a coarser
# grid than GRID_STEP so the band reads as "approximate" rather than a precise number.
BAND_ROUNDING_STEP = 25

# D-06: the canonical user-facing disclaimer. Every future surface that shows a
# labeled bot strength (custom bot builder, preset cards, SEED-098 personas)
# must import this exact string rather than writing its own copy.
APPROX_ELO_DISCLAIMER = (
    "This is an APPROXIMATE Lichess blitz ELO, derived from an internal "
    "calibration scale rather than measured against real players. It carries a "
    "per-preset uncertainty band and should be read as a rough guide, not a "
    "precise rating."
)


def load_internal_scale(path: str) -> dict[str, Any]:
    """Fail-loud loader/validator for the frozen Phase-180 sweep output (T-181-01).

    Never coerces a missing/malformed field to a default or NaN — mirrors
    calibration_anchor_fit.py's load_fixed_ratings/load_bot_cells idiom.
    """
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    cells = payload.get("cells")
    if not cells:
        raise ValueError(f"load_internal_scale: {path!r} has no non-empty 'cells' array")
    per_preset = payload.get("per_preset")
    if not per_preset:
        raise ValueError(f"load_internal_scale: {path!r} has no non-empty 'per_preset' object")
    return payload


@dataclass
class _Block:
    """One PAVA block: a (possibly pooled) run of non-decreasing points."""

    x_lo: float  # smallest bot_elo in this block — the D-07 inversion answer
    x_hi: float  # largest bot_elo in this block
    weight: float  # number of original points pooled into this block
    value: float  # pooled (weighted-mean) internal rating for this block


def isotonic_fit(points: list[tuple[float, float]]) -> list[_Block]:
    """Pool-Adjacent-Violators, stack-of-blocks (D-07).

    `points` MUST be pre-sorted ascending by x (bot_elo). Scans left to right,
    merging backward by weighted mean whenever monotonicity is violated. O(n).
    """
    blocks: list[_Block] = []
    for x, y in points:
        block = _Block(x_lo=x, x_hi=x, weight=1.0, value=y)
        blocks.append(block)
        while len(blocks) >= 2 and blocks[-2].value > blocks[-1].value:
            b2 = blocks.pop()
            b1 = blocks.pop()
            total_weight = b1.weight + b2.weight
            blocks.append(
                _Block(
                    x_lo=b1.x_lo,
                    x_hi=b2.x_hi,
                    weight=total_weight,
                    value=(b1.value * b1.weight + b2.value * b2.weight) / total_weight,
                )
            )
    return blocks


def approx_blitz_points(
    blocks: list[_Block], g_preset_combined: float, c: float
) -> list[tuple[float, float]]:
    """Per-block (bot_elo, approx_blitz) conversion (D-01).

    Uses each block's x_lo (never x_hi or a midpoint) so a flat/merged block's
    strength is attributed to its LOWEST bot_elo — the same tie-break the D-07
    inversion depends on. Subtracts the POOLED g_preset_combined (never a
    per-cell g_preset, never rating_vs_sf — the caller already fit on
    rating_vs_maia).
    """
    return [(b.x_lo, b.value - g_preset_combined + c) for b in blocks]


def invert_lookup(blocks: list[_Block], g_preset_combined: float, c: float) -> dict[int, int]:
    """target_blitz_elo -> bot_elo, lowest-bot_elo-wins (D-07), inward-rounded (D-10).

    Floor rounds UP to the next GRID_STEP, ceiling rounds DOWN, so only targets
    fully inside the measured/fitted curve are offered. For each target, walks
    the blocks in ascending bot_elo order and returns the first block whose
    approx_blitz reaches the target — its x_lo. A target landing inside a
    merged/flat block always resolves to that block's LOWEST bot_elo, never a
    higher one that also reaches the target.
    """
    approx = approx_blitz_points(blocks, g_preset_combined, c)
    floor = int(math.ceil(approx[0][1] / GRID_STEP) * GRID_STEP)
    ceiling = int(math.floor(approx[-1][1] / GRID_STEP) * GRID_STEP)
    lookup: dict[int, int] = {}
    for target in range(floor, ceiling + GRID_STEP, GRID_STEP):
        for bot_elo, blitz in approx:  # ascending bot_elo order — first hit wins
            if blitz >= target:
                lookup[target] = int(bot_elo)
                break
    return lookup


def preset_range(lookup: dict[int, int]) -> dict[str, int]:
    """{floor, ceiling} approx-blitz range for a preset's inverted lookup (D-10)."""
    return {"floor": min(lookup), "ceiling": max(lookup)}


def preset_band(cells: list[dict[str, Any]]) -> int:
    """Blanket +/- uncertainty band per preset (D-03).

    Derived, not a magic number: C's own +/-C_UNCERTAINTY_HALF_BAND plus the
    preset's mean fit-CI half-width (the average, over its measured cells, of
    (ci_vs_maia[1] - ci_vs_maia[0]) / 2), rounded to the nearest BAND_ROUNDING_STEP.
    """
    half_widths = [(c["ci_vs_maia"][1] - c["ci_vs_maia"][0]) / 2.0 for c in cells]
    mean_half_width = sum(half_widths) / len(half_widths)
    raw = C_UNCERTAINTY_HALF_BAND + mean_half_width
    return round(raw / BAND_ROUNDING_STEP) * BAND_ROUNDING_STEP


def compute_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    """Runs the full fit -> offset -> inversion pipeline over every preset.

    Returns the components+derived+disclaimer structure (D-02) that both
    `_render_lookup_json` and `_render_ts` consume. Raises `ValueError` if a
    preset's cell count is not exactly EXPECTED_CELLS_PER_PRESET (D-08 guard —
    a silently dropped cell must fail loud, not ship a quietly-narrower curve).
    """
    per_preset_payload = payload["per_preset"]
    cells_by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in PRESETS.values()}
    for cell in payload["cells"]:
        blend = float(cell["bot_blend"])
        name = PRESETS.get(blend)
        if name is None:
            raise ValueError(f"compute_artifact: unknown bot_blend {blend!r} in input cells")
        cells_by_name[name].append(cell)

    components: dict[str, Any] = {}
    derived: dict[str, Any] = {}
    for blend, name in PRESETS.items():
        cells = sorted(cells_by_name[name], key=lambda c: c["bot_elo"])
        if len(cells) != EXPECTED_CELLS_PER_PRESET:
            raise ValueError(
                f"compute_artifact: preset {name!r} has {len(cells)} cells, "
                f"expected {EXPECTED_CELLS_PER_PRESET} (D-08 — none may be dropped)"
            )
        points = [(float(c["bot_elo"]), float(c["rating_vs_maia"])) for c in cells]
        blocks = isotonic_fit(points)
        g_preset_combined = float(per_preset_payload[f"{blend:g}"]["g_preset_combined"])
        lookup = invert_lookup(blocks, g_preset_combined, BLITZ_OFFSET_C)

        components[name] = {
            "fit_points": [{"bot_elo": b.x_lo, "internal_rating": b.value} for b in blocks],
            "g_preset_combined": g_preset_combined,
            "c_offset": BLITZ_OFFSET_C,
            "band": preset_band(cells),
            "extrapolated_bot_elos": sorted(
                int(c["bot_elo"]) for c in cells if c.get("beyond_ladder")
            ),
        }
        derived[name] = {"range": preset_range(lookup), "lookup": lookup}

    return {"components": components, "derived": derived, "disclaimer": APPROX_ELO_DISCLAIMER}


def _render_lookup_json(artifact: dict[str, Any]) -> str:
    """Serializes the artifact as pretty-printed, deterministically-ordered JSON."""
    return json.dumps(artifact, indent=2) + "\n"


def _format_lookup_record(derived: dict[str, Any]) -> str:
    """Emits BOT_STRENGTH_LOOKUP's body: preset -> { targetBlitzElo: botElo, ... }."""
    lines: list[str] = []
    for name in PRESETS.values():
        entries = ", ".join(
            f"{target}: {bot_elo}" for target, bot_elo in sorted(derived[name]["lookup"].items())
        )
        lines.append(f"  {name}: {{ {entries} }},")
    return "\n".join(lines) + "\n"


def _format_ranges_record(derived: dict[str, Any]) -> str:
    """Emits BOT_STRENGTH_RANGES's body: preset -> { floor, ceiling }."""
    lines: list[str] = []
    for name in PRESETS.values():
        preset_range_entry = derived[name]["range"]
        lines.append(
            f"  {name}: {{ floor: {preset_range_entry['floor']},"
            f" ceiling: {preset_range_entry['ceiling']} }},"
        )
    return "\n".join(lines) + "\n"


def _format_bands_record(components: dict[str, Any]) -> str:
    """Emits BOT_STRENGTH_BANDS's body: preset -> band (a single number)."""
    lines: list[str] = []
    for name in PRESETS.values():
        lines.append(f"  {name}: {components[name]['band']},")
    return "\n".join(lines) + "\n"


def _render_ts(artifact: dict[str, Any]) -> str:
    """Build the full TypeScript source as a single string.

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    components = artifact["components"]
    derived = artifact["derived"]
    preset_union = " | ".join(f'"{name}"' for name in PRESETS.values())
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: scripts/gen_bot_strength_curves.py, reports/data/bot-curves-internal-scale.json\n"
        "// Regenerate with: uv run python scripts/gen_bot_strength_curves.py\n"
        "\n"
        f"export type BotStrengthPreset = {preset_union};\n"
        "\n"
        f"export const APPROX_ELO_DISCLAIMER = {json.dumps(APPROX_ELO_DISCLAIMER)};\n"
        "\n"
        "export const BOT_STRENGTH_LOOKUP: Record<BotStrengthPreset, Record<number, number>> = {\n"
        + _format_lookup_record(derived)
        + "} as const;\n"
        "\n"
        "export const BOT_STRENGTH_RANGES: Record<\n"
        "  BotStrengthPreset,\n"
        "  { floor: number; ceiling: number }\n"
        "> = {\n" + _format_ranges_record(derived) + "} as const;\n"
        "\n"
        "export const BOT_STRENGTH_BANDS: Record<BotStrengthPreset, number> = {\n"
        + _format_bands_record(components)
        + "} as const;\n"
    )


def main() -> None:
    check_mode = "--check" in sys.argv
    payload = load_internal_scale(str(_INPUT))
    artifact = compute_artifact(payload)
    outputs = [
        (_render_lookup_json(artifact), _LOOKUP_JSON),
        (_render_ts(artifact), _TS_OUTPUT),
    ]
    if check_mode:
        drifted = [
            output_path
            for content, output_path in outputs
            if not output_path.exists() or output_path.read_text(encoding="utf-8") != content
        ]
        if drifted:
            names = ", ".join(str(p.relative_to(_REPO_ROOT)) for p in drifted)
            print(
                f"DRIFT: {names} out of date. "
                "Run `uv run python scripts/gen_bot_strength_curves.py` to regenerate.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("OK: bot strength curve artifacts are up to date.")
    else:
        for content, output_path in outputs:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"Wrote {output_path.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
