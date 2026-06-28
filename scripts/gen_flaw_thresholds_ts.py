"""Generate frontend/src/generated/flawThresholds.ts from flaws_service.py constants.

Python (app/services/flaws_service.py) is the authoritative source per Phase 110
D-04. This script emits a TypeScript mirror consumed by the flaw-tag definition
popover in tagDefinitions.ts — no hard-coded percentages in TS copy. CI runs
`git diff --exit-code` on the generated file to block drift.

Only constants with a frontend consumer are emitted (the four ES impact thresholds
and the four tempo thresholds the popover copy interpolates).

Usage (local dev):
    uv run python scripts/gen_flaw_thresholds_ts.py

Usage (drift check — exits 1 if generated output differs from the committed file):
    uv run python scripts/gen_flaw_thresholds_ts.py --check

Usage (CI drift check):
    uv run python scripts/gen_flaw_thresholds_ts.py
    git diff --exit-code frontend/src/generated/flawThresholds.ts
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from app.services.flaws_service` works
# when this script is invoked directly (e.g. `python scripts/gen_flaw_thresholds_ts.py`).
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.eval_utils import LICHESS_K  # noqa: E402  # winning-chances sigmoid coeff
from app.services.flaws_service import (  # noqa: E402
    BLUNDER_DROP,  # ES drop >= 0.15 = blunder (live free-move classification)
    FROM_WINNING_ES,  # squandered entry (>= 85%: overwhelming advantage)
    HASTY_MOVE_ABS_SECONDS,  # fallback when base_time unknown
    HASTY_MOVE_FRACTION,  # < 1% of base = fast move on comfortable clock
    INACCURACY_DROP,  # ES drop >= 0.05 = inaccuracy
    LOSING_LINE_ES,  # reversed exit (<= 30%: clearly losing)
    MATE_CP_EQUIVALENT,  # mate mapped to ±this cp before the sigmoid
    MISTAKE_DROP,  # ES drop >= 0.10 = mistake
    SQUANDERED_EXIT_ES,  # squandered exit (<= 60%: erased back to roughly even)
    TIME_PRESSURE_CLOCK_ABS_SECONDS,  # fallback when base_time unknown
    TIME_PRESSURE_CLOCK_FRACTION,  # < 5% of base = low clock
    WINNING_LINE_ES,  # reversed entry (>= 70%: clearly winning, ~+2.3 eval)
)

_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "flawThresholds.ts"


def _render() -> str:
    """Build the full TypeScript source as a single string.

    The exact bytes emitted by this function are what gets committed. CI runs
    the script and uses `git diff --exit-code` to block any drift.
    """
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: app/services/flaws_service.py, app/services/eval_utils.py\n"
        "// Regenerate with: uv run python scripts/gen_flaw_thresholds_ts.py\n"
        "\n"
        f"export const WINNING_LINE_ES = {WINNING_LINE_ES};\n"
        f"export const LOSING_LINE_ES = {LOSING_LINE_ES};\n"
        f"export const FROM_WINNING_ES = {FROM_WINNING_ES};\n"
        f"export const SQUANDERED_EXIT_ES = {SQUANDERED_EXIT_ES};\n"
        f"export const TIME_PRESSURE_CLOCK_FRACTION = {TIME_PRESSURE_CLOCK_FRACTION};\n"
        f"export const TIME_PRESSURE_CLOCK_ABS_SECONDS = {TIME_PRESSURE_CLOCK_ABS_SECONDS};\n"
        f"export const HASTY_MOVE_FRACTION = {HASTY_MOVE_FRACTION};\n"
        f"export const HASTY_MOVE_ABS_SECONDS = {HASTY_MOVE_ABS_SECONDS};\n"
        "\n"
        "// Expected-score drop tiers + sigmoid inputs for live move classification\n"
        "// (Quick w8k item 4 — classifying freely-played moves with the live engine).\n"
        f"export const INACCURACY_DROP = {INACCURACY_DROP};\n"
        f"export const MISTAKE_DROP = {MISTAKE_DROP};\n"
        f"export const BLUNDER_DROP = {BLUNDER_DROP};\n"
        f"export const MATE_CP_EQUIVALENT = {MATE_CP_EQUIVALENT};\n"
        f"export const LICHESS_K = {LICHESS_K};\n"
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
                "Run `uv run python scripts/gen_flaw_thresholds_ts.py` to regenerate.",
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
