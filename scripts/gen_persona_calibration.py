"""Generate the shipping per-persona calibration artifact.

Reads `reports/data/persona-calibration.json` (Task 1's fit output — 24
`PersonaId`-keyed entries, `scripts/calibration_persona_fit.py`) and produces
`frontend/src/generated/personaCalibration.ts`: a `Record<PersonaId, {
botElo: number; label: string }>`.

Pipeline per style column (D-04 weak monotonicity, ties allowed, never an
inversion): reuses `gen_bot_strength_curves.py`'s hand-rolled
Pool-Adjacent-Violators `isotonic_fit` VERBATIM — 4 INDEPENDENT pooling
passes, one per style, each over that style's 6 `(rung, approx_blitz)`
points sorted ascending by RUNG (not `bot_elo` — two rungs may already
collide on `bot_elo` post-retargeting). The D-07 global ceiling (1800) is
applied AFTER pooling (clamping first would corrupt the monotonicity fit for
lower rungs in the same column), then D-03 rounds to the nearest 50.

`botElo` in the output Record is the D-01 retargeted engine-facing value
(untouched by PAVA/pooling — that only shapes the DISPLAY label from
`approx_blitz`).

CI-drift-checked exactly like `botStrengthCurves.ts` (`--check` mode +
`git diff --exit-code`, mirrors `gen_bot_strength_curves.py:302-330`).

Usage (local dev, writes the generated TS + rewrites the JSON):
    uv run python scripts/gen_persona_calibration.py

Usage (drift check — exits 1 if the committed output differs from a fresh render):
    uv run python scripts/gen_persona_calibration.py --check
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import gen_bot_strength_curves as bot_curves

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INPUT = _REPO_ROOT / "reports" / "data" / "persona-calibration.json"
_LOOKUP_JSON = _REPO_ROOT / "reports" / "data" / "persona-calibration.json"
_TS_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "personaCalibration.ts"

# T-184-02-01 / D-08: every preset must consume exactly 24 personas across
# exactly 4 styles x 6 rungs each — none may be silently dropped.
EXPECTED_PERSONA_COUNT = 24
EXPECTED_STYLE_COUNT = 4
EXPECTED_RUNGS_PER_STYLE = 6

# The 4 named styles, in the SAME display order as
# `frontend/src/lib/personas/personaRegistry.ts`'s `STYLE_SECTION_ORDER` —
# purely for deterministic/readable output ordering, no behavior depends on it.
STYLE_ORDER = ("Attacker", "Trickster", "Grinder", "Wall")

# D-07: no persona label ever exceeds this, applied AFTER PAVA pooling.
GLOBAL_CEILING = 1800

# D-03: labels round to the nearest 50 — GLOBAL_CEILING is itself a multiple
# of this step, so clamp-then-round can never push a label past the ceiling.
ROUND_STEP = 50


def _style_from_persona_id(persona_id: str) -> str:
    """Derives a persona's style from its id (`'attacker-1200' -> 'Attacker'`).

    `persona-calibration.json`'s per-persona records deliberately carry no
    `style` field (Task 1's literal output shape) — the id itself is the
    single source of truth, mirroring `personaId()`'s
    `${style.toLowerCase()}-${rung}` construction in `personaRegistry.ts`.
    """
    prefix = persona_id.split("-", 1)[0]
    return prefix[:1].upper() + prefix[1:]


def load_persona_calibration(path: str) -> dict[str, dict[str, Any]]:
    """Fail-loud loader/validator for Task 1's fit output (T-184-02-01).

    Never coerces a missing/malformed field to a default — mirrors
    `gen_bot_strength_curves.py`'s `load_internal_scale` idiom. Raises
    `ValueError` if the input lacks exactly `EXPECTED_PERSONA_COUNT` personas
    or any style column lacks exactly `EXPECTED_RUNGS_PER_STYLE` distinct rungs.
    """
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    personas = payload.get("personas")
    if not personas or len(personas) != EXPECTED_PERSONA_COUNT:
        raise ValueError(
            f"load_persona_calibration: {path!r} has "
            f"{len(personas) if personas else 0} persona entries, expected exactly {EXPECTED_PERSONA_COUNT}"
        )

    by_style: dict[str, dict[int, str]] = {}
    for persona_id, entry in personas.items():
        style = _style_from_persona_id(persona_id)
        rung = int(entry["rung"])
        by_style.setdefault(style, {})
        if rung in by_style[style]:
            raise ValueError(
                f"load_persona_calibration: duplicate rung {rung} in style {style!r} "
                f"(persona_ids {by_style[style][rung]!r} and {persona_id!r})"
            )
        by_style[style][rung] = persona_id

    if len(by_style) != EXPECTED_STYLE_COUNT:
        raise ValueError(
            f"load_persona_calibration: expected exactly {EXPECTED_STYLE_COUNT} styles, "
            f"got {sorted(by_style)!r}"
        )
    for style, rungs in by_style.items():
        if len(rungs) != EXPECTED_RUNGS_PER_STYLE:
            raise ValueError(
                f"load_persona_calibration: style {style!r} has {len(rungs)} rungs "
                f"{sorted(rungs)!r}, expected exactly {EXPECTED_RUNGS_PER_STYLE}"
            )

    return personas


def _cap_and_round(value: float) -> int:
    """D-07 (global ceiling, post-pooling) then D-03 (round to nearest 50)."""
    capped = min(value, GLOBAL_CEILING)
    return min(round(capped / ROUND_STEP) * ROUND_STEP, GLOBAL_CEILING)


def compute_artifact(personas: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Runs the per-style PAVA-pool -> cap -> round pipeline (D-04/D-07/D-03).

    Returns a `PersonaId -> {botElo, label, approx_blitz_pooled}` mapping;
    `approx_blitz_pooled` is retained for `_write_persona_json`'s rewritten
    JSON sibling (traceability), not consumed by the TS render.
    """
    by_style: dict[str, list[tuple[int, str]]] = {}
    for persona_id, entry in personas.items():
        style = _style_from_persona_id(persona_id)
        by_style.setdefault(style, []).append((int(entry["rung"]), persona_id))

    artifact: dict[str, dict[str, Any]] = {}
    for style, rung_ids in by_style.items():
        rung_ids.sort(key=lambda pair: pair[0])  # ascending by RUNG, never bot_elo (Pitfall 1)
        points = [(float(rung), float(personas[pid]["approx_blitz"])) for rung, pid in rung_ids]
        blocks = bot_curves.isotonic_fit(points)  # D-04: PAVA pooling, verbatim reuse
        # Map each rung back to its (possibly pooled) block's value.
        pooled_by_rung: dict[int, float] = {}
        for block in blocks:
            for rung, _pid in rung_ids:
                if block.x_lo <= rung <= block.x_hi:
                    pooled_by_rung[rung] = block.value

        for rung, persona_id in rung_ids:
            entry = personas[persona_id]
            pooled = pooled_by_rung[rung]
            label_value = _cap_and_round(pooled)
            artifact[persona_id] = {
                "botElo": int(entry["bot_elo"]),
                "label": f"~{label_value}",
                "approx_blitz_pooled": pooled,
            }

    return artifact


def _render_lookup_json(artifact: dict[str, dict[str, Any]], source_payload: dict[str, Any]) -> str:
    """Rewrites `persona-calibration.json` with the pooled/capped/rounded
    labels folded back in (traceability sibling, mirrors
    `gen_bot_strength_curves.py`'s two-output convention)."""
    payload = dict(source_payload)
    personas = payload.get("personas", {})
    for persona_id, calc in artifact.items():
        if persona_id in personas:
            personas[persona_id] = {
                **personas[persona_id],
                "label": calc["label"],
                "approx_blitz_pooled": calc["approx_blitz_pooled"],
            }
    payload["personas"] = personas
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _persona_ids_in_order(artifact: dict[str, dict[str, Any]]) -> list[str]:
    """Orders PersonaId keys by STYLE_ORDER then ascending rung — purely for
    readable, deterministic TS output (no behavior depends on key order)."""

    def sort_key(persona_id: str) -> tuple[int, int]:
        style = _style_from_persona_id(persona_id)
        style_idx = STYLE_ORDER.index(style) if style in STYLE_ORDER else len(STYLE_ORDER)
        rung = int(persona_id.rsplit("-", 1)[1])
        return (style_idx, rung)

    return sorted(artifact, key=sort_key)


def is_measured(personas: dict[str, dict[str, Any]]) -> bool:
    """True only when every persona carries finite per-family fitted ratings.

    The `--bootstrap` fit writes `rating_vs_maia`/`rating_vs_sf` as NaN and
    `approx_blitz = rung` — provisional placeholders, not measurements. The
    frontend disclosure popover must not claim "measured" while that is the
    case (it would assert a measurement that never happened), so this flag is
    emitted alongside the labels and flips to `true` on its own the first time
    a real sweep is fitted. NaN is the discriminator because it is exactly
    what the bootstrap path writes and no real fit can produce.
    """
    return all(
        math.isfinite(float(entry["rating_vs_maia"]))
        and math.isfinite(float(entry["rating_vs_sf"]))
        for entry in personas.values()
    )


def _render_ts(artifact: dict[str, dict[str, Any]], measured: bool) -> str:
    """Builds the full TypeScript source as a single string (D-10).

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    entries = "\n".join(
        f"  '{persona_id}': {{ botElo: {artifact[persona_id]['botElo']}, label: '{artifact[persona_id]['label']}' }},"
        for persona_id in _persona_ids_in_order(artifact)
    )
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: scripts/gen_persona_calibration.py, reports/data/persona-calibration-cells.tsv\n"
        "// Regenerate with: uv run python scripts/gen_persona_calibration.py\n"
        "\n"
        "// STALENESS (D-11): changing botStyleBundles.ts style params or the anchor\n"
        "// ladder invalidates this calibration — re-run the persona sweep\n"
        "// (bin/run_persona_calibration_sweep.sh) before regenerating. No hash-guard\n"
        "// automation enforces this — it is a documented operator policy only.\n"
        "\n"
        "import type { PersonaId } from '@/lib/personas/personaRegistry';\n"
        "\n"
        "// False while the labels are provisional (`--bootstrap` fit: approx_blitz =\n"
        "// rung, ratings NaN). The ELO disclosure popover reads this so it never\n"
        "// claims a measurement that has not happened; it flips to true on the first\n"
        "// real sweep refit.\n"
        f"export const PERSONA_CALIBRATION_MEASURED = {'true' if measured else 'false'};\n"
        "\n"
        "export const PERSONA_CALIBRATION: Record<PersonaId, { botElo: number; label: string }> = {\n"
        f"{entries}\n"
        "} as const;\n"
    )


def main() -> None:
    check_mode = "--check" in sys.argv
    with open(_INPUT, encoding="utf-8") as f:
        source_payload = json.load(f)
    personas = load_persona_calibration(str(_INPUT))
    artifact = compute_artifact(personas)
    outputs = [
        (_render_lookup_json(artifact, source_payload), _LOOKUP_JSON),
        (_render_ts(artifact, is_measured(personas)), _TS_OUTPUT),
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
                "Run `uv run python scripts/gen_persona_calibration.py` to regenerate.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("OK: persona calibration artifacts are up to date.")
    else:
        for content, output_path in outputs:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"Wrote {output_path.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
