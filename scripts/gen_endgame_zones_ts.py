"""Generate frontend/src/generated/endgameZones.ts from the Python zone registry.

Python (app/services/endgame_zones.py) is the authoritative source per Phase 63
D-01. This script emits a TypeScript mirror consumed by TypeTable (the per-class
typical ranges, read as plain lower/upper bounds), EndgameEloTimelineSection
(MIN_GAMES_PER_TC_CARD) and EndgameClockDiffOverTimeChart (NEUTRAL_PCT_THRESHOLD).
CI runs `git diff --exit-code` on the generated file to block drift.

Only constants with an FE consumer are emitted (Phase 238 pruned the rest when the
gauge, chip and per-TC card components were retired). Every other zone constant
stays Python-only: the insights pipeline and the benchmark reports read it from
app/services/endgame_zones.py directly.

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
    MIN_GAMES_PER_TC_CARD,  # Phase 88.1 WR-04 (Plan 88-10)
    NEUTRAL_PCT_THRESHOLD,
    PER_CLASS_TC_GAUGE_ZONES,  # Phase 98: per-(class × TC) conv/recov/score-gap bands
)

_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "endgameZones.ts"


def _format_per_class_tc_gauge_zones() -> str:
    """Emit PER_CLASS_TC_GAUGE_ZONES as a nested TS Record literal (Phase 98).

    Outer key: endgame class (rook/minor_piece/pawn/queen/mixed).
    Inner key: TC string ('bullet'|'blitz'|'rapid'|'classical').
    Each entry has { conversion: [lo, hi], recovery: [lo, hi], achievable_score_gap: [lo, hi] }.
    """
    lines: list[str] = []
    for cls, tc_map in PER_CLASS_TC_GAUGE_ZONES.items():
        tc_entries: list[str] = []
        for tc, bands in tc_map.items():
            c_lo, c_hi = bands.conversion
            r_lo, r_hi = bands.recovery
            g_lo, g_hi = bands.achievable_score_gap
            tc_entries.append(
                f"    {tc}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}],"
                f" achievable_score_gap: [{g_lo}, {g_hi}] }},"
            )
        lines.append(f"  {cls}: {{\n" + "\n".join(tc_entries) + "\n  },")
    return "\n".join(lines) + "\n"


def _format_class_key_union() -> str:
    """Emit the union of endgame class keys that carry per-TC bands (pawnless is omitted)."""
    return " | ".join(f"'{cls}'" for cls in PER_CLASS_TC_GAUGE_ZONES)


def _render() -> str:
    """Build the full TypeScript source as a single string.

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: app/services/endgame_zones.py\n"
        "// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py\n"
        "\n"
        "// Half-width (percentage points) of the neutral band used for clock-difference\n"
        "// shading on the Average Clock Difference over Time chart.\n"
        f"export const NEUTRAL_PCT_THRESHOLD = {NEUTRAL_PCT_THRESHOLD};\n"
        "\n"
        "// Phase 88 D-03 / Phase 88.1 WR-04: minimum games per TC to qualify (e.g. as the primary TC).\n"
        "// Source of truth: app/services/endgame_zones.py (codegen-mirrored to avoid drift).\n"
        f"export const MIN_GAMES_PER_TC_CARD = {MIN_GAMES_PER_TC_CARD};\n"
        "\n"
        "// Phase 98: per-(class × TC) typical ranges for Conv/Recov/ScoreGap.\n"
        "// Read as plain [lower, upper] bounds (the Endgame Type Breakdown table draws them\n"
        "// as the grey typical range behind each cell).\n"
        "// Source: reports/benchmark/benchmarks-latest.md §3.4.1 (TC marginal p25/p75).\n"
        "// Cohen's d ≈ 1.2–1.7 per class across TCs → all classes keep-separate.\n"
        "// Score Gap TC d ≈ 0.07–0.18 (collapse) — four near-identical ΔES bands per\n"
        "// class by design (Score Gap forced per-TC for visual consistency, D-04/D-14).\n"
        "// pawnless omitted: n below per-class TC floor; hidden in the table UI.\n"
        "export const PER_CLASS_TC_GAUGE_ZONES: Record<\n"
        f"  {_format_class_key_union()},\n"
        "  Record<\n"
        "    'bullet' | 'blitz' | 'rapid' | 'classical',\n"
        "    { conversion: [number, number]; recovery: [number, number]; achievable_score_gap: [number, number] }\n"
        "  >\n"
        "> = {\n" + _format_per_class_tc_gauge_zones() + "} as const;\n"
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
