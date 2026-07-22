"""calibration_persona_fit.py — Phase 184 (CAL-04) per-persona rating fit.

Converts the persona-calibration sweep's per-(persona, anchor) aggregate TSV
into a calibrated, per-persona internal-scale rating + approximate-blitz-ELO
conversion, keyed by `PersonaId` (never `(bot_elo, bot_blend)` — Pitfall 1:
multiple distinct personas legitimately collide on that pair post-retargeting,
e.g. every rung-1800 persona shares `(botElo=2300, blend=0.5)`).

Mirrors `calibration_anchor_fit.py`'s bot-cell fit path (`fit_bot_cell_rating`,
reused UNMODIFIED — never re-derived) and `gen_bot_strength_curves.py`'s
`approx_blitz` conversion (`g_preset_combined` + `BLITZ_OFFSET_C`, both READ
from their canonical sources at run time, never hardcoded literals — Pitfall
2/T-184-02-01). Every persona cell is fit TWICE: once against its bracket's
Maia-family anchors only (`rating_vs_maia`), once against its SF-family
anchors only (`rating_vs_sf`) — the two families are NEVER merged before
fitting, mirroring `fit_all_bot_cells`'s "never merge" discipline.

stdlib-only (`argparse`/`json`/`subprocess`/`sys`) — no numpy/scipy, matching
`calibration_anchor_fit.py`'s convention. This is a standalone research tool
(`scripts/`, not `app/`) — no Sentry capture (CLAUDE.md Sentry rules apply to
`app/services`/`app/routers` only).

Usage (fit from a real sweep aggregate):
    uv run python scripts/calibration_persona_fit.py \\
        --input reports/data/persona-calibration-cells.tsv \\
        --out-json reports/data/persona-calibration.json

Usage (bootstrap — retargeting only, no sweep data needed yet):
    uv run python scripts/calibration_persona_fit.py --bootstrap

Usage (fixture self-test, the Python analog of the `.check.mjs` convention):
    uv run python scripts/calibration_persona_fit.py --self-test
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

import calibration_anchor_fit as anchor_fit
import gen_bot_strength_curves as bot_curves

_REPO_ROOT = Path(__file__).resolve().parent.parent

# --- The 24-persona invariant (T-184-02-01 fail-loud guard) --------------------
EXPECTED_PERSONA_COUNT = 24

# --- Per-(persona, anchor) aggregate TSV column contract -----------------------
REQUIRED_COLUMNS = (
    "persona_id",
    "style",
    "rung",
    "blend",
    "bot_elo",
    "anchor",
    "wins",
    "draws",
    "losses",
)
BEYOND_LADDER_COLUMN = "beyond_ladder"

# --- Canonical source paths (read at run time — never transcribed literals) ----
DEFAULT_INPUT_TSV = str(_REPO_ROOT / "reports" / "data" / "persona-calibration-cells.tsv")
DEFAULT_OUTPUT_JSON = str(_REPO_ROOT / "reports" / "data" / "persona-calibration.json")
DEFAULT_LOOKUP_JSON = str(_REPO_ROOT / "reports" / "data" / "bot-strength-lookup.json")
DEFAULT_INTERNAL_SCALE_JSON = anchor_fit.DEFAULT_INTERNAL_SCALE_JSON

# Node one-liner used ONLY by --bootstrap (no sweep data exists yet): dumps the
# 24 persona identities + D-01 retargeted botElo straight from the JS source of
# truth (personaRegistry.ts via calibration-persona-cell-schedule.mjs) — Python
# never duplicates/hardcodes the style/rung->blend mapping (avoids drift).
_BOOTSTRAP_NODE_SCRIPT = (
    "import { ALL_PERSONA_CELLS } from './scripts/lib/calibration-persona-cell-schedule.mjs';"
    "const slim = ALL_PERSONA_CELLS.map(({ styleParams, ...rest }) => rest);"
    "process.stdout.write(JSON.stringify(slim));"
)


class PersonaScheduleCell(TypedDict):
    """One `ALL_PERSONA_CELLS` entry as dumped by `_BOOTSTRAP_NODE_SCRIPT`
    (i.e. minus `styleParams`, which the fit never needs)."""

    personaId: str
    style: str
    rung: int
    blend: float
    botElo: int


class PersonaCellFit(TypedDict):
    """One fitted persona: two per-family ratings, the converted approx_blitz,
    and the D-01/D-06 provenance fields the codegen script (Task 2) consumes."""

    preset: str
    rung: int
    blend: float
    bot_elo: int
    rating_vs_maia: float
    rating_vs_sf: float
    approx_blitz: float
    beyond_ladder: bool


@dataclass
class _PersonaAccum:
    style: str
    rung: int
    blend: float
    bot_elo: int
    beyond_ladder: bool = False
    wdl_vs_maia: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    wdl_vs_sf: dict[str, tuple[float, float, float]] = field(default_factory=dict)


def load_persona_cells(path: str) -> dict[str, _PersonaAccum]:
    """Reads the persona-calibration sweep's per-(persona_id, anchor) aggregate TSV.

    Fail-loud (T-184-02-01, mirrors `load_bot_cells`'s discipline): raises
    `ValueError` on a missing required column, a malformed/truncated row, a
    persona whose metadata (style/rung/blend/bot_elo) disagrees across its own
    rows, or a persona count that is not exactly `EXPECTED_PERSONA_COUNT` —
    never coerces a missing/inconsistent persona to a default.
    """
    with open(path, encoding="utf-8") as f:
        rows = [line.rstrip("\n") for line in f if line.strip()]
    if not rows:
        raise ValueError(f"load_persona_cells: {path!r} is empty")

    header = rows[0].split("\t")
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(
            f"load_persona_cells: TSV missing required column(s) {missing!r}; header={header!r}"
        )
    idx = {c: header.index(c) for c in header}
    has_beyond = BEYOND_LADDER_COLUMN in header

    accum: dict[str, _PersonaAccum] = {}
    for line in rows[1:]:
        fields = line.split("\t")
        if len(fields) != len(header):
            raise ValueError(
                f"load_persona_cells: malformed row (expected {len(header)} columns, got {len(fields)}): {line!r}"
            )
        persona_id = fields[idx["persona_id"]]
        style = fields[idx["style"]]
        rung = int(fields[idx["rung"]])
        blend = float(fields[idx["blend"]])
        bot_elo = int(fields[idx["bot_elo"]])
        anchor = fields[idx["anchor"]]
        wdl = (
            float(fields[idx["wins"]]),
            float(fields[idx["draws"]]),
            float(fields[idx["losses"]]),
        )

        acc = accum.get(persona_id)
        if acc is None:
            acc = _PersonaAccum(style=style, rung=rung, blend=blend, bot_elo=bot_elo)
            accum[persona_id] = acc
        elif (acc.style, acc.rung, acc.blend, acc.bot_elo) != (style, rung, blend, bot_elo):
            raise ValueError(
                f"load_persona_cells: inconsistent metadata for persona {persona_id!r} across rows "
                f"(saw both {(acc.style, acc.rung, acc.blend, acc.bot_elo)!r} and {(style, rung, blend, bot_elo)!r})"
            )

        # Reuses the SAME family classifier as the bot-cell fit path (Pitfall 2:
        # the two families are never merged before fitting) — never re-derived.
        family = anchor_fit._anchor_family(anchor)  # noqa: SLF001 -- shared classifier, single source of truth
        if family == "maia":
            acc.wdl_vs_maia[anchor] = wdl
        else:
            acc.wdl_vs_sf[anchor] = wdl
        if has_beyond and fields[idx[BEYOND_LADDER_COLUMN]].strip().lower() == "true":
            acc.beyond_ladder = True

    if len(accum) != EXPECTED_PERSONA_COUNT:
        raise ValueError(
            f"load_persona_cells: expected exactly {EXPECTED_PERSONA_COUNT} distinct persona_id rows, "
            f"got {len(accum)}: {sorted(accum)!r}"
        )
    return accum


def load_g_preset_combined(path: str) -> dict[str, float]:
    """Reads `components.<preset>.g_preset_combined` per preset from the shipped
    Phase-181 lookup artifact — NEVER hardcoded (T-184-02-01/prohibition)."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    components = payload.get("components")
    if not isinstance(components, dict) or not components:
        raise ValueError(f"load_g_preset_combined: {path!r} has no non-empty 'components' object")
    result: dict[str, float] = {}
    for preset, entry in components.items():
        g = entry.get("g_preset_combined")
        if g is None:
            raise ValueError(
                f"load_g_preset_combined: preset {preset!r} missing 'g_preset_combined' in {path!r}"
            )
        result[preset] = float(g)
    return result


def _preset_for_blend(blend: float) -> str:
    """Maps a persona's raw blend value to its preset name, reusing the SAME
    blend->preset dict `gen_bot_strength_curves.py` uses (never re-derived).
    Fail-loud on an unrecognized blend — a persona-cell schedule has no
    legitimate "unknown preset" case."""
    preset = bot_curves.PRESETS.get(blend)
    if preset is None:
        raise ValueError(
            f"_preset_for_blend: blend={blend!r} does not match any of the named presets "
            f"{sorted(bot_curves.PRESETS)!r}"
        )
    return preset


def fit_persona_cell(
    persona_id: str,
    acc: _PersonaAccum,
    fixed_ratings: dict[str, float],
    g_preset_combined: dict[str, float],
) -> PersonaCellFit:
    """Fits ONE persona TWICE (vs-Maia, vs-SF) — mirrors `fit_all_bot_cells`'s
    "never merge before fitting" discipline (Pitfall 2) — then converts
    `rating_vs_maia` to `approx_blitz` via the PRESET's pooled
    `g_preset_combined` (never a per-persona refit, never `rating_vs_sf`)."""
    preset = _preset_for_blend(acc.blend)
    if preset not in g_preset_combined:
        raise ValueError(
            f"fit_persona_cell: preset {preset!r} (persona {persona_id!r}) missing from g_preset_combined"
        )

    wins_maia, games_maia = anchor_fit._fold_wdl(acc.wdl_vs_maia)  # noqa: SLF001 -- shared fold helper
    wins_sf, games_sf = anchor_fit._fold_wdl(acc.wdl_vs_sf)  # noqa: SLF001
    rating_vs_maia = anchor_fit.fit_bot_cell_rating(wins_maia, games_maia, fixed_ratings)
    rating_vs_sf = anchor_fit.fit_bot_cell_rating(wins_sf, games_sf, fixed_ratings)
    approx_blitz = rating_vs_maia - g_preset_combined[preset] + bot_curves.BLITZ_OFFSET_C

    return PersonaCellFit(
        preset=preset,
        rung=acc.rung,
        blend=acc.blend,
        bot_elo=acc.bot_elo,
        rating_vs_maia=rating_vs_maia,
        rating_vs_sf=rating_vs_sf,
        approx_blitz=approx_blitz,
        beyond_ladder=acc.beyond_ladder,
    )


def fit_all_personas(
    accum: dict[str, _PersonaAccum],
    fixed_ratings: dict[str, float],
    g_preset_combined: dict[str, float],
) -> dict[str, PersonaCellFit]:
    return {
        persona_id: fit_persona_cell(persona_id, acc, fixed_ratings, g_preset_combined)
        for persona_id, acc in sorted(accum.items())
    }


def _write_persona_json(path: str, fits: dict[str, PersonaCellFit]) -> None:
    payload = {
        "_caveat": anchor_fit.INTERNAL_SCALE_HEADER,
        "personas": fits,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_placeholder_cells_tsv(path: str) -> None:
    """Writes a header-only placeholder aggregate (T-184-02 bootstrap): no
    sweep has run yet, so there is no real per-(persona, anchor) data — this
    just commits the schema/shape so the pipeline is runnable + CI-stable
    before the overnight sweep (Plan 04) replaces it with real rows."""
    header = "\t".join((*REQUIRED_COLUMNS, BEYOND_LADDER_COLUMN))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(header + "\n", encoding="utf-8")


def _dump_persona_cells_via_node() -> list[PersonaScheduleCell]:
    """Invokes Node to dump the 24 `ALL_PERSONA_CELLS` entries as JSON — the
    JS source of truth (`personaRegistry.ts` via
    `calibration-persona-cell-schedule.mjs`) is read directly rather than
    duplicated/hardcoded here (avoids drift, WR-02)."""
    result = subprocess.run(
        [
            "node",
            "--import",
            "./scripts/lib/frontend-alias-hook.mjs",
            "--input-type=module",
            "-e",
            _BOOTSTRAP_NODE_SCRIPT,
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"_dump_persona_cells_via_node: node exited {result.returncode}: {result.stderr}"
        )
    cells = json.loads(result.stdout)
    if not isinstance(cells, list) or len(cells) != EXPECTED_PERSONA_COUNT:
        raise RuntimeError(
            f"_dump_persona_cells_via_node: expected {EXPECTED_PERSONA_COUNT} persona cells, "
            f"got {len(cells) if isinstance(cells, list) else type(cells)!r}"
        )
    return cells


def run_bootstrap(out_json: str, out_cells_tsv: str) -> None:
    """--bootstrap: retargeting-only, no sweep required (D-01). `botElo` is the
    REAL Phase-181-retargeted value; `approx_blitz` is a provisional,
    HONEST pre-measurement placeholder (`= rung`, never fabricated to look
    measured) so the generated file is committed and type-correct before the
    overnight sweep (Plan 04) replaces it with fitted values."""
    cells = _dump_persona_cells_via_node()
    fits: dict[str, PersonaCellFit] = {}
    for cell in cells:
        persona_id = str(cell["personaId"])
        rung = int(cell["rung"])
        blend = float(cell["blend"])
        bot_elo = int(cell["botElo"])
        preset = _preset_for_blend(blend)
        fits[persona_id] = PersonaCellFit(
            preset=preset,
            rung=rung,
            blend=blend,
            bot_elo=bot_elo,
            rating_vs_maia=float("nan"),
            rating_vs_sf=float("nan"),
            approx_blitz=float(rung),
            beyond_ladder=False,
        )
    _write_persona_json(out_json, fits)
    _write_placeholder_cells_tsv(out_cells_tsv)
    print(f"Wrote {out_json} (bootstrap, {len(fits)} personas, provisional approx_blitz=rung)")
    print(f"Wrote {out_cells_tsv} (header-only placeholder)")


# --- --self-test: a small hardcoded fixture, the Python analog of .check.mjs ---


def _self_test_fixture() -> tuple[dict[str, float], str]:
    """A tiny 4-anchor fixed-rating fixture (2 maia + 2 sf) — NOT the real
    10-anchor internal scale — used only to prove `fit_persona_cell`'s wiring
    (twice-per-cell fit + approx_blitz conversion), independent of any real
    data file."""
    return {"maia1100": 1100.0, "maia1900": 1900.0, "sf3": 1300.0, "sf8": 1900.0}, "human"


def run_self_test() -> None:
    fixed_ratings, preset = _self_test_fixture()
    g_preset_combined = {preset: 40.0}

    # A persona that beats the weak anchors and loses to the strong ones both
    # families — its fitted rating should land clearly BETWEEN the two anchor
    # tiers (~1100-1900), not degenerate to +/-infinity (continuity correction).
    acc = _PersonaAccum(
        style="Attacker",
        rung=1200,
        blend=0.0,
        bot_elo=1900,
        wdl_vs_maia={"maia1100": (8.0, 0.0, 2.0), "maia1900": (2.0, 0.0, 8.0)},
        wdl_vs_sf={"sf3": (7.0, 0.0, 3.0), "sf8": (1.0, 0.0, 9.0)},
    )
    fit = fit_persona_cell("attacker-1200", acc, fixed_ratings, g_preset_combined)
    assert 1100.0 < fit["rating_vs_maia"] < 1900.0, (
        f"rating_vs_maia out of expected band: {fit['rating_vs_maia']}"
    )
    assert 1100.0 < fit["rating_vs_sf"] < 1900.0, (
        f"rating_vs_sf out of expected band: {fit['rating_vs_sf']}"
    )
    expected_approx_blitz = (
        fit["rating_vs_maia"] - g_preset_combined[preset] + bot_curves.BLITZ_OFFSET_C
    )
    assert fit["approx_blitz"] == expected_approx_blitz, (
        "approx_blitz must use rating_vs_maia, never rating_vs_sf"
    )
    assert fit["preset"] == preset

    # An unknown blend must fail loud, never silently default to a preset.
    try:
        _preset_for_blend(0.37)
    except ValueError:
        pass
    else:
        raise AssertionError("_preset_for_blend(0.37) should have raised ValueError")

    # A <24-persona TSV must fail loud (T-184-02-01 guard) — build a fixture
    # with only 2 persona_id rows and confirm load_persona_cells refuses it.
    import tempfile

    header = "\t".join((*REQUIRED_COLUMNS, BEYOND_LADDER_COLUMN))
    lines: list[str] = [header]
    for pid, rung in (("attacker-800", 800), ("attacker-1000", 1000)):
        lines.append(f"{pid}\tAttacker\t{rung}\t0.0\t1100\tmaia1100\t5\t0\t5\tfalse")
    tsv_text = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as tmp:
        tmp.write(tsv_text)
        tmp_path = tmp.name
    try:
        load_persona_cells(tmp_path)
    except ValueError as exc:
        assert "24" in str(exc), f"expected the 24-count guard message, got: {exc}"
    else:
        raise AssertionError(
            "load_persona_cells with only 2 personas should have raised ValueError"
        )
    finally:
        Path(tmp_path).unlink()

    print("OK: calibration_persona_fit self-test passed.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", default=DEFAULT_INPUT_TSV, help="Per-(persona_id, anchor) aggregate TSV"
    )
    parser.add_argument(
        "--out-json", default=DEFAULT_OUTPUT_JSON, help="Output path for persona-calibration.json"
    )
    parser.add_argument(
        "--out-cells-tsv",
        default=DEFAULT_INPUT_TSV,
        help="Output path for the --bootstrap placeholder TSV",
    )
    parser.add_argument(
        "--lookup-json",
        default=DEFAULT_LOOKUP_JSON,
        help="Path to bot-strength-lookup.json (g_preset_combined source)",
    )
    parser.add_argument(
        "--internal-scale-json",
        default=DEFAULT_INTERNAL_SCALE_JSON,
        help="Path to the 10 fixed anchor INTERNAL_RATING values",
    )
    parser.add_argument(
        "--bootstrap", action="store_true", help="Retargeting-only mode, no sweep data required"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run the fixture self-test and exit"
    )
    args = parser.parse_args(argv)

    if args.self_test:
        run_self_test()
        return

    if args.bootstrap:
        run_bootstrap(args.out_json, args.out_cells_tsv)
        return

    fixed_ratings = anchor_fit.load_fixed_ratings(args.internal_scale_json)
    g_preset_combined = load_g_preset_combined(args.lookup_json)
    accum = load_persona_cells(args.input)
    fits = fit_all_personas(accum, fixed_ratings, g_preset_combined)
    _write_persona_json(args.out_json, fits)
    print(f"Wrote {args.out_json} ({len(fits)} personas)")


if __name__ == "__main__":
    main(sys.argv[1:])
