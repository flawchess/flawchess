"""Generate frontend/src/generated/endgameZones.ts from the Python zone registry.

Python (app/services/endgame_zones.py) is the authoritative source per Phase 63
D-01. This script emits a TypeScript mirror that FE consumers will switch to in
Phase 66. Until then, the consistency test in
tests/services/test_endgame_zones_consistency.py guards against drift between
the inline FE constants and the Python registry.

The output shape matches what the current FE consumers expect so a future
find-and-replace import switch is trivial (see D-03).

Usage (local dev):
    uv run python scripts/gen_endgame_zones_ts.py

Usage (CI drift check):
    uv run python scripts/gen_endgame_zones_ts.py
    git diff --exit-code frontend/src/generated/endgameZones.ts
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from app.services.endgame_zones` works
# when this script is invoked directly (e.g. `python scripts/gen_endgame_zones_ts.py`).
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.endgame_zones import (  # noqa: E402
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD,
    ZONE_REGISTRY,
)

_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "endgameZones.ts"

# Score Gap neutral band boundaries are stored in ZONE_REGISTRY["score_gap"]; the
# FE currently exports them as SCORE_GAP_NEUTRAL_MIN/MAX so the TS mirror does too.
_SCORE_GAP_SPEC = ZONE_REGISTRY["score_gap"]


def _format_bucket_zones(bucket: str) -> str:
    """Emit the three-band array literal for one material bucket.

    Each bucket uses its own metric's band (conversion -> conversion_win_pct,
    parity -> parity_score_pct, recovery -> recovery_save_pct) — matches the
    FE FIXED_GAUGE_ZONES shape where each bucket shows the band for the
    per-bucket metric displayed in that gauge.
    """
    if bucket == "conversion":
        spec = BUCKETED_ZONE_REGISTRY["conversion_win_pct"]["conversion"]
    elif bucket == "parity":
        spec = BUCKETED_ZONE_REGISTRY["parity_score_pct"]["parity"]
    else:  # recovery
        spec = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"]
    return (
        f"    {{ from: 0, to: {spec.typical_lower} }},\n"
        f"    {{ from: {spec.typical_lower}, to: {spec.typical_upper} }},\n"
        f"    {{ from: {spec.typical_upper}, to: 1.0 }},\n"
    )


def _render() -> str:
    """Build the full TypeScript source as a single string.

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    skill = ZONE_REGISTRY["endgame_skill"]
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: app/services/endgame_zones.py\n"
        "// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py\n"
        "\n"
        'export type MaterialBucket = "conversion" | "parity" | "recovery";\n'
        "\n"
        "export interface GaugeZone {\n"
        "  from: number;\n"
        "  to: number;\n"
        "}\n"
        "\n"
        "export const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {\n"
        "  conversion: [\n" + _format_bucket_zones("conversion") + "  ],\n"
        "  parity: [\n" + _format_bucket_zones("parity") + "  ],\n"
        "  recovery: [\n" + _format_bucket_zones("recovery") + "  ],\n"
        "};\n"
        "\n"
        "export const ENDGAME_SKILL_ZONES: GaugeZone[] = [\n"
        f"  {{ from: 0, to: {skill.typical_lower} }},\n"
        f"  {{ from: {skill.typical_lower}, to: {skill.typical_upper} }},\n"
        f"  {{ from: {skill.typical_upper}, to: 1.0 }},\n"
        "];\n"
        "\n"
        f"export const NEUTRAL_PCT_THRESHOLD = {NEUTRAL_PCT_THRESHOLD};\n"
        f"export const NEUTRAL_TIMEOUT_THRESHOLD = {NEUTRAL_TIMEOUT_THRESHOLD};\n"
        f"export const SCORE_GAP_NEUTRAL_MIN = {_SCORE_GAP_SPEC.typical_lower};\n"
        f"export const SCORE_GAP_NEUTRAL_MAX = {_SCORE_GAP_SPEC.typical_upper};\n"
        f"export const NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = {NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD};\n"
    )


def main() -> None:
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(_render(), encoding="utf-8")
    print(f"Wrote {_OUTPUT.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
