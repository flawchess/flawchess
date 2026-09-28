"""engine_search_fixes_allowance.py — Phase 225 D-02 ROOT_GUARD_BOOST_ALLOWANCE
measurement.

Computes the D-02 measured design input for the visit-guard boost-aware
window (`ROOT_GUARD_BOOST_ALLOWANCE`, CONTEXT.md D-01/D-02): the root-child
value change at first expansion (post minus pre `practicalScore`) across the
`scripts/engine-dispatch-stop-rule.mjs --no-stop-rule --root-trace` position
set, at the bot ELO range, taken at roughly the 90th percentile.

Selection-bias caveat (RESEARCH C-2): only children PUCT actually expands are
sampled, i.e. the higher-Q, higher-prior ones. Those are exactly the
in-window population the guard cares about, so the bias is acceptable — but
it means this allowance is NOT a distribution over every legal root move,
only over the ones root PUCT chose to expand.

This is a standalone research tool (`scripts/`, not `app/`) — stdlib only
(`argparse`/`csv`/`json`/`math`/`statistics`), exempt from CLAUDE.md's
Sentry-capture rules (those apply to app/services and app/routers only).

Usage:
    uv run python scripts/engine_search_fixes_allowance.py allowance \\
        --trace-dir reports/data \\
        [--out-json reports/data/d02-allowance.json]

The last two stdout lines of a real run are always, in order:
    METHOD measured|fallback
    ALLOWANCE 0.xx
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict

# ==============================================================================
# Pre-registered D-02 constants. Fixed BEFORE the accept rule is committed and
# before any gate arm runs (CONTEXT.md D-02, D-11). Naming and placement are
# Claude's discretion per CONTEXT.md "Claude's Discretion".
# ==============================================================================
D02_PERCENTILE = 90
ALLOWANCE_ROUNDING_STEP = 0.01
D02_MIN_SAMPLES = 30
D02_FALLBACK_ALLOWANCE = 0.10

ROOT_TRACE_GLOB = "engine-root-trace-*.tsv"

REQUIRED_COLUMNS: tuple[str, ...] = ("position", "elo", "root_move", "delta")

AllowanceMethod = Literal["measured", "fallback"]


class RootTraceDelta(TypedDict):
    """One row of a root-trace TSV — a single root child's first-expansion delta."""

    position: str
    elo: int
    root_move: str
    delta: float


class EloSummary(TypedDict):
    """Per-ELO delta distribution summary."""

    elo: int
    n: int
    p50: float
    p90: float
    max: float


class AllowanceResult(TypedDict):
    """The D-02 allowance computation result — printed, and optionally written as JSON."""

    method: AllowanceMethod
    allowance: float
    pooled_n: int
    pooled_p90: float | None
    per_elo: list[EloSummary]


def load_root_trace_deltas(trace_dir: Path) -> list[RootTraceDelta]:
    """Reads every `engine-root-trace-*.tsv` file in `trace_dir`.

    Raises ValueError when no file matches, or when a required column
    (position, elo, root_move, delta) is missing from a matched file — the
    message names the file and the missing column.
    """
    paths = sorted(trace_dir.glob(ROOT_TRACE_GLOB))
    if not paths:
        raise ValueError(f"No files matching {ROOT_TRACE_GLOB!r} found in {trace_dir}")

    deltas: list[RootTraceDelta] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = reader.fieldnames or ()
            for column in REQUIRED_COLUMNS:
                if column not in fieldnames:
                    raise ValueError(f"{path}: missing required column {column!r}")
            for row in reader:
                deltas.append(
                    RootTraceDelta(
                        position=row["position"],
                        elo=int(row["elo"]),
                        root_move=row["root_move"],
                        delta=float(row["delta"]),
                    )
                )
    return deltas


def percentile(values: Sequence[float], pct: int) -> float:
    """The `pct`-th percentile of `values`, inclusive method (matches Excel/pandas 'linear').

    Raises ValueError when fewer than 2 values are given — `statistics.quantiles`
    itself requires at least 2 data points.
    """
    if len(values) < 2:
        raise ValueError(f"percentile requires at least 2 values, got {len(values)}")
    return statistics.quantiles(values, n=100, method="inclusive")[pct - 1]


def round_up_to_step(value: float, step: float) -> float:
    """Rounds `value` UP to the nearest multiple of `step`, 2-decimal display precision.

    The inner `round(..., 9)` guards float artifacts such as `0.07 / 0.01 ==
    7.000000000000001`, which would otherwise ceil to 8 instead of 7.
    """
    steps = round(value / step, 9)
    return round(math.ceil(steps) * step, 2)


def compute_allowance(deltas: list[RootTraceDelta]) -> AllowanceResult:
    """Computes the D-02 allowance from a flat list of root-trace deltas.

    Per-ELO summaries (n, p50, p90, max) are always reported for any ELO with
    at least 2 samples. The pooled count gates the method: fewer than
    `D02_MIN_SAMPLES` pooled deltas falls back to `D02_FALLBACK_ALLOWANCE`
    (METHOD fallback); otherwise the allowance is `max(0.0, pooled p90 rounded
    up to ALLOWANCE_ROUNDING_STEP)` (METHOD measured).
    """
    pooled = [d["delta"] for d in deltas]
    elos = sorted({d["elo"] for d in deltas})

    per_elo: list[EloSummary] = []
    for elo in elos:
        values = [d["delta"] for d in deltas if d["elo"] == elo]
        if len(values) < 2:
            continue
        per_elo.append(
            EloSummary(
                elo=elo,
                n=len(values),
                p50=percentile(values, 50),
                p90=percentile(values, 90),
                max=max(values),
            )
        )

    if len(pooled) < D02_MIN_SAMPLES:
        return AllowanceResult(
            method="fallback",
            allowance=D02_FALLBACK_ALLOWANCE,
            pooled_n=len(pooled),
            pooled_p90=None,
            per_elo=per_elo,
        )

    pooled_p90 = percentile(pooled, D02_PERCENTILE)
    allowance = max(0.0, round_up_to_step(pooled_p90, ALLOWANCE_ROUNDING_STEP))
    return AllowanceResult(
        method="measured",
        allowance=allowance,
        pooled_n=len(pooled),
        pooled_p90=pooled_p90,
        per_elo=per_elo,
    )


def _print_table(result: AllowanceResult) -> None:
    print("| ELO | n | p50 | p90 | max |")
    print("|---|---|---|---|---|")
    for row in result["per_elo"]:
        print(
            f"| {row['elo']} | {row['n']} | {row['p50']:.4f} | {row['p90']:.4f} | {row['max']:.4f} |"
        )
    pooled_p90_str = f"{result['pooled_p90']:.4f}" if result["pooled_p90"] is not None else "n/a"
    print(f"| pooled | {result['pooled_n']} | - | {pooled_p90_str} | - |")


def _cmd_allowance(args: argparse.Namespace) -> int:
    trace_dir = Path(args.trace_dir)
    deltas = load_root_trace_deltas(trace_dir)
    result = compute_allowance(deltas)

    _print_table(result)
    if args.out_json is not None:
        Path(args.out_json).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Wrote {args.out_json}")

    # Last two stdout lines of a real run, always in this order.
    print(f"METHOD {result['method']}")
    print(f"ALLOWANCE {result['allowance']:.2f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    allowance_parser = subparsers.add_parser(
        "allowance", help="Compute the D-02 ROOT_GUARD_BOOST_ALLOWANCE from root-trace TSVs."
    )
    allowance_parser.add_argument(
        "--trace-dir", required=True, help="Directory containing engine-root-trace-*.tsv files."
    )
    allowance_parser.add_argument(
        "--out-json", default=None, help="Optional path to write the AllowanceResult as JSON."
    )
    allowance_parser.set_defaults(func=_cmd_allowance)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
