"""Generate frontend/src/generated/endgameZones.ts from the Python zone registry.

Python (app/services/endgame_zones.py) is the authoritative source per Phase 63
D-01. This script emits a TypeScript mirror consumed by EndgameScoreGapSection,
EndgameClockPressureSection, and EndgamePerformanceSection. CI runs
`git diff --exit-code` on the generated file to block drift.

Only constants with an FE consumer are emitted. `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD`
stays Python-only (backend-only usage in endgame_service.py).

Usage (local dev):
    uv run python scripts/gen_endgame_zones_ts.py

Usage (drift check — exits 1 if generated output differs from the committed file):
    uv run python scripts/gen_endgame_zones_ts.py --check

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
    MIN_GAMES_PER_PRESSURE_BIN,  # Phase 88.1 WR-04 / WR-05 (Plan 88-10)
    MIN_GAMES_PER_TC_CARD,  # Phase 88.1 WR-04 (Plan 88-10)
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    PER_CLASS_GAUGE_ZONES,
    PRESSURE_BIN_SCORE_NEUTRAL_ZONES,  # Phase 88
    TC_METRIC_BANDS,  # Phase 97: per-TC conv/recov gauge + DeltaES bullet bands
    ZONE_REGISTRY,
)

_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "endgameZones.ts"

# Score Gap neutral band boundaries are stored in ZONE_REGISTRY["score_gap"]; the
# FE currently exports them as SCORE_GAP_NEUTRAL_MIN/MAX so the TS mirror does too.
_SCORE_GAP_SPEC = ZONE_REGISTRY["score_gap"]

# 260514-kei: Achievable Score Gap gets a dedicated band (±5pp) so Card 3's
# Achievable row can tighten without affecting the Endgame Score Gap row
# (which stays at ±10pp). Mirrors the SCORE_GAP_NEUTRAL_* export pattern.
_ACHIEVABLE_SCORE_GAP_SPEC = ZONE_REGISTRY["achievable_score_gap"]

# Phase 87.1 (SEED-016 D-04): per-span, per-type version of achievable_score_gap.
# Frontend constant uses the user-facing "Endgame Type Score Gap" label (D-02);
# the registry key keeps the internal "achievable" math-family name for
# grep-ability with the page-level metric.
_ENDGAME_TYPE_SCORE_GAP_SPEC = ZONE_REGISTRY["endgame_type_achievable_score_gap"]

# Phase 83 D-16: codegen the entry_expected_score helpers so Plan 3 imports them
# from frontend/src/generated/endgameZones.ts (CI drift gate enforces parity).
_ENTRY_XS_SPEC = ZONE_REGISTRY["entry_expected_score"]

# Phase 87.2 (D-02): per-bucket Section 2 ΔES Score Gap neutral bands.
# Each bucket gets its own ZoneSpec from ZONE_REGISTRY; placeholder ±5pp bands
# until /benchmarks §3.4.4 Cohen's-d calibration updates them.
_SCORE_GAP_CONV_SPEC = ZONE_REGISTRY["score_gap_conv"]
_SCORE_GAP_PARITY_SPEC = ZONE_REGISTRY["score_gap_parity"]
_SCORE_GAP_RECOV_SPEC = ZONE_REGISTRY["score_gap_recov"]
# Phase 87.4 (D-05): SCORE_GAP_SKILL_SPEC dropped alongside the
# score_gap_skill ZoneSpec deletion.

# Phase 88: clock_gap_pct scalar zone spec for the Clock Gap bullet.
# PLACEHOLDER band until benchmarks §3.3.1 clock-gap-% runs calibrate it.
_CLOCK_GAP_SPEC = ZONE_REGISTRY["clock_gap_pct"]


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


def _format_per_class_gauge_zones() -> str:
    """Emit the PER_CLASS_GAUGE_ZONES object literal.

    Each class entry has { conversion: [lower, upper], recovery: [lower, upper],
    achievable_score_gap: [lower, upper] } (Phase 87.1 — SEED-016 D-04).
    Consumers wrap with colorizeGaugeZones() on the FE side, same as FIXED_GAUGE_ZONES.
    """
    lines: list[str] = []
    for cls, bands in PER_CLASS_GAUGE_ZONES.items():
        c_lo, c_hi = bands.conversion
        r_lo, r_hi = bands.recovery
        g_lo, g_hi = bands.achievable_score_gap  # Phase 87.1 — SEED-016 D-04
        lines.append(
            f"  {cls}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}],"
            f" achievable_score_gap: [{g_lo}, {g_hi}] }},"
        )
    return "\n".join(lines) + "\n"


def _format_pressure_bin_zones() -> str:
    """Emit PRESSURE_BIN_SCORE_NEUTRAL_ZONES as a nested TS Record literal.

    Each TC entry contains 5 quintile keys (0-4) with { min, max } bands.
    Mirrors _format_per_class_gauge_zones() structure.
    """
    lines: list[str] = []
    for tc, quintile_map in PRESSURE_BIN_SCORE_NEUTRAL_ZONES.items():
        q_entries = ", ".join(
            f"{q}: {{ min: {band.lower}, max: {band.upper} }}" for q, band in quintile_map.items()
        )
        lines.append(f"  {tc}: {{ {q_entries} }},")
    return "\n".join(lines) + "\n"


def _format_tc_metric_bands() -> str:
    """Emit TC_METRIC_BANDS as a nested TS Record literal (Phase 97).

    Each TC entry has { convRate, recovRate, convScoreGap, recovScoreGap } with
    [lower, upper] tuples. Mirrors _format_per_class_gauge_zones() structure.
    """
    lines: list[str] = []
    for tc, bands in TC_METRIC_BANDS.items():
        cr_lo, cr_hi = bands.conv_rate
        rr_lo, rr_hi = bands.recov_rate
        cg_lo, cg_hi = bands.conv_score_gap
        rg_lo, rg_hi = bands.recov_score_gap
        lines.append(
            f"  {tc}: {{ convRate: [{cr_lo}, {cr_hi}], recovRate: [{rr_lo}, {rr_hi}],"
            f" convScoreGap: [{cg_lo}, {cg_hi}], recovScoreGap: [{rg_lo}, {rg_hi}] }},"
        )
    return "\n".join(lines) + "\n"


def _render() -> str:
    """Build the full TypeScript source as a single string.

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    # Phase 87.4 (D-05): ENDGAME_SKILL_ZONES emission dropped (Endgame Skill
    # concept retracted end-to-end).
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: app/services/endgame_zones.py\n"
        "// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py\n"
        "\n"
        'import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from "@/lib/theme";\n'
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
        f"export const NEUTRAL_PCT_THRESHOLD = {NEUTRAL_PCT_THRESHOLD};\n"
        f"export const NEUTRAL_TIMEOUT_THRESHOLD = {NEUTRAL_TIMEOUT_THRESHOLD};\n"
        f"export const SCORE_GAP_NEUTRAL_MIN = {_SCORE_GAP_SPEC.typical_lower};\n"
        f"export const SCORE_GAP_NEUTRAL_MAX = {_SCORE_GAP_SPEC.typical_upper};\n"
        f"export const ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN = {_ACHIEVABLE_SCORE_GAP_SPEC.typical_lower};\n"
        f"export const ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX = {_ACHIEVABLE_SCORE_GAP_SPEC.typical_upper};\n"
        "// Phase 87.1 (SEED-016 D-04): per-span, per-type Score Gap neutral band.\n"
        '// User-facing label: "Endgame Type Score Gap" (concepts) / "Score Gap" (card row).\n'
        "// Internal registry key is `endgame_type_achievable_score_gap` for math-family grep.\n"
        f"export const ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN = {_ENDGAME_TYPE_SCORE_GAP_SPEC.typical_lower};\n"
        f"export const ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX = {_ENDGAME_TYPE_SCORE_GAP_SPEC.typical_upper};\n"
        "// Phase 87.2 (D-02): per-bucket Section 2 ΔES Score Gap neutral bands.\n"
        f"export const SCORE_GAP_CONV_NEUTRAL_MIN = {_SCORE_GAP_CONV_SPEC.typical_lower};\n"
        f"export const SCORE_GAP_CONV_NEUTRAL_MAX = {_SCORE_GAP_CONV_SPEC.typical_upper};\n"
        f"export const SCORE_GAP_PARITY_NEUTRAL_MIN = {_SCORE_GAP_PARITY_SPEC.typical_lower};\n"
        f"export const SCORE_GAP_PARITY_NEUTRAL_MAX = {_SCORE_GAP_PARITY_SPEC.typical_upper};\n"
        f"export const SCORE_GAP_RECOV_NEUTRAL_MIN = {_SCORE_GAP_RECOV_SPEC.typical_lower};\n"
        f"export const SCORE_GAP_RECOV_NEUTRAL_MAX = {_SCORE_GAP_RECOV_SPEC.typical_upper};\n"
        "// Phase 87.4 (D-05): SCORE_GAP_SKILL_NEUTRAL_* emission dropped\n"
        "// alongside the Endgame Skill concept retirement.\n"
        "\n"
        "// Phase 83 D-14/D-17: per-user entry_expected_score cohort band.\n"
        "// Source: reports/benchmarks-2026-05-11.md §7 (pooled IQR aligned with\n"
        "// endgame_score band for visual parity with the §0 final-score zone).\n"
        f"export const ENTRY_EXPECTED_SCORE_NEUTRAL_MIN = {_ENTRY_XS_SPEC.typical_lower};\n"
        f"export const ENTRY_EXPECTED_SCORE_NEUTRAL_MAX = {_ENTRY_XS_SPEC.typical_upper};\n"
        "\n"
        "/**\n"
        " * Pick the zone color for the EG-entry expected-score bullet relative to the\n"
        " * cohort neutral band. Pure presentation — gating on confidence happens in the\n"
        " * consumer (mirrors endgameEntryEvalZoneColor).\n"
        " */\n"
        "export function entryExpectedScoreZoneColor(value: number): string {\n"
        "  if (value >= ENTRY_EXPECTED_SCORE_NEUTRAL_MAX) return ZONE_SUCCESS;\n"
        "  if (value <= ENTRY_EXPECTED_SCORE_NEUTRAL_MIN) return ZONE_DANGER;\n"
        "  return ZONE_NEUTRAL;\n"
        "}\n"
        "\n"
        "// Per-endgame-class typical bands for Conversion, Recovery, and Score Gap.\n"
        "// Source: reports/benchmarks-2026-05-01.md (pooled p25/p75 per class).\n"
        "// Phase 87.1 (SEED-016 D-04): achievable_score_gap added as a placeholder\n"
        "// mirroring ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN/MAX until §3.4.2 calibration.\n"
        "// Each entry: { conversion: [lower, upper], recovery: [lower, upper],\n"
        "// achievable_score_gap: [lower, upper] }.\n"
        "// Wrap with colorizeGaugeZones() before passing to EndgameGauge (same\n"
        "// pattern as FIXED_GAUGE_ZONES in EndgameScoreGapSection).\n"
        "export const PER_CLASS_GAUGE_ZONES = {\n"
        + _format_per_class_gauge_zones()
        + "} as const;\n"
        "\n"
        "export type EndgameClassKey = keyof typeof PER_CLASS_GAUGE_ZONES;\n"
        "\n"
        "// Phase 88 D-02: per-(TC, pressure-quintile) neutral bands.\n"
        "// Quintile 0 = 0-20% clock remaining (max pressure), 4 = 80-100%.\n"
        "// Calibrated from reports/benchmarks-latest.md §3.3.3 (Phase 88-08, 2026-05-17).\n"
        "// Sanity-rerun against opp-quintile semantics in Plan 88-12.\n"
        "export const PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Record<\n"
        "  'bullet' | 'blitz' | 'rapid' | 'classical',\n"
        "  Record<0 | 1 | 2 | 3 | 4, { min: number; max: number }>\n"
        "> = {\n" + _format_pressure_bin_zones() + "} as const;\n"
        "\n"
        "// Phase 88 D-03 / Phase 88.1 WR-04: gating thresholds shared with backend.\n"
        "// Source of truth: app/services/endgame_zones.py (codegen-mirrored to avoid drift).\n"
        f"export const MIN_GAMES_PER_TC_CARD = {MIN_GAMES_PER_TC_CARD};\n"
        f"export const MIN_GAMES_PER_PRESSURE_BIN = {MIN_GAMES_PER_PRESSURE_BIN};\n"
        "\n"
        "/**\n"
        " * Look up the neutral band for a (TC, quintile) cell with explicit narrowing.\n"
        " * Phase 88.1 IN-06 / WR-03 — replaces the unsafe `[q as 0|1|2|3|4]!` pattern\n"
        " * with a defensive range check. Returns null if quintile is outside 0..4.\n"
        " */\n"
        "export function getPressureBinBand(\n"
        "  tc: 'bullet' | 'blitz' | 'rapid' | 'classical',\n"
        "  quintile: number,\n"
        "): { min: number; max: number } | null {\n"
        "  if (quintile < 0 || quintile > 4) return null;\n"
        "  const q = quintile as 0 | 1 | 2 | 3 | 4;\n"
        "  const band = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q];\n"
        "  return band ?? null;\n"
        "}\n"
        "\n"
        "// Phase 88: Clock Gap scalar neutral band.\n"
        "// Calibrated from reports/benchmarks-latest.md §3.3.1 clock-gap-% (Phase 88-08, 2026-05-17).\n"
        f"export const CLOCK_GAP_NEUTRAL_MIN = {_CLOCK_GAP_SPEC.typical_lower};\n"
        f"export const CLOCK_GAP_NEUTRAL_MAX = {_CLOCK_GAP_SPEC.typical_upper};\n"
        "\n"
        "// Phase 97: per-TC gauge + DeltaES bullet bands for Conversion and Recovery.\n"
        "// Source: reports/benchmark/benchmarks-latest.md §3.2.1 (rates) and §3.2.2 (DeltaES gaps).\n"
        "export const TC_METRIC_BANDS: Record<\n"
        "  'bullet' | 'blitz' | 'rapid' | 'classical',\n"
        "  { convRate: [number, number]; recovRate: [number, number]; convScoreGap: [number, number]; recovScoreGap: [number, number] }\n"
        "> = {\n"
        + _format_tc_metric_bands()
        + "} as const;\n"
    )


def main() -> None:
    check_mode = "--check" in sys.argv
    content = _render()
    if check_mode:
        if not _OUTPUT.exists():
            print(f"DRIFT: {_OUTPUT.relative_to(_REPO_ROOT)} does not exist.", file=sys.stderr)
            sys.exit(1)
        existing = _OUTPUT.read_text(encoding="utf-8")
        if existing != content:
            print(
                f"DRIFT: {_OUTPUT.relative_to(_REPO_ROOT)} is out of date. "
                "Run `uv run python scripts/gen_endgame_zones_ts.py` to regenerate.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"OK: {_OUTPUT.relative_to(_REPO_ROOT)} is up to date.")
    else:
        _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT.write_text(content, encoding="utf-8")
        print(f"Wrote {_OUTPUT.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
