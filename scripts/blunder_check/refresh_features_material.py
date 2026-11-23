"""Recompute the stored material pair of a facepalm features table with the current rule (Phase 262 D-01).

A committed features table (``facepalm_features.py`` output) carries the raw lines of every blunder:
``pre_fen``, ``played_uci``, ``played_line`` (the stored refutation line) and ``best_line``. The stored
inputs ``loss`` / ``missed`` are a pure function of those lines (``facepalm_material_inputs``, the single
writer, 259 D-05), so a change of the material rule (262 D-01: a promotion counts as material) can be
applied to the committed table offline: no database, no Maia. That is how the refit gets its features
before anything changes on prod (CONTEXT, prod rollout), and it isolates the rule change: the
probabilities and labels are copied verbatim.

The previous ``loss`` / ``missed`` cells become ``loss_shipped`` / ``missed_shipped`` (the Phase 259 pair,
the baseline of the fit report's range check), replacing whatever older shipped columns the input held.
The per-depth ``played_mat_*`` / ``best_mat_*`` columns belong to a retired rule and would be stale under
this one, so they are dropped. A row with no ``pre_fen`` keeps its cells.

Usage::

    uv run python scripts/blunder_check/refresh_features_material.py \\
        --features reports/blunder-check/facepalm-features-<date>.tsv --out <new features TSV>
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import chess

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.facepalm_inputs import facepalm_material_inputs  # noqa: E402
from scripts.blunder_check.facepalm_features import FLOAT_SIGNIFICANT_DIGITS  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# What the recompute reads (and the two cells it replaces): a table without one of them cannot be refreshed.
RAW_INPUT_COLUMNS: tuple[str, ...] = (
    "pre_fen",
    "played_uci",
    "played_line",
    "best_line",
    "loss",
    "missed",
)
# Per-depth material slots of a retired rule: dropped, they would be stale under the current rule.
STALE_COLUMN_PREFIXES: tuple[str, ...] = ("played_mat_", "best_mat_")
SHIPPED_LOSS_COLUMN: str = "loss_shipped"
SHIPPED_MISSED_COLUMN: str = "missed_shipped"

EXIT_OK: int = 0
EXIT_BAD_TABLE: int = 2

TSV_DELIMITER: str = "\t"


class BadTableError(RuntimeError):
    """The input is not a features table this tool can refresh."""


@dataclass(frozen=True, slots=True)
class RefreshSummary:
    """What a refresh did: rows read, rows kept as they were for lack of raw inputs, rows that moved."""

    rows: int
    rows_without_raw_inputs: int
    # The `n` cell of every row whose loss or missed cell changed, in file order.
    changed_n: list[str]


def _cell(value: float | None) -> str:
    """One float cell in the features-table format (None is an empty cell)."""
    return "" if value is None else f"{value:.{FLOAT_SIGNIFICANT_DIGITS}g}"


def _same_number(old: str, new: str) -> bool:
    return old != "" and new != "" and float(old) == float(new)


def _keep_or_new(old: str, new: str) -> str:
    """The new cell, or the old one verbatim when it is the same number (no churn on unchanged rows)."""
    return old if _same_number(old, new) else new


def has_raw_inputs(record: dict[str, str]) -> bool:
    """Whether a row carries the position and the move the recompute needs."""
    return bool(record["pre_fen"]) and bool(record["played_uci"])


def refresh_row(record: dict[str, str]) -> dict[str, str]:
    """One row under the current rule: the old pair kept as `*_shipped`, `loss` / `missed` recomputed.

    Every other cell is copied verbatim. A row with no `pre_fen` or no `played_uci` keeps its
    `loss` / `missed` cells.
    """
    row = dict(record)
    row[SHIPPED_LOSS_COLUMN] = record["loss"]
    row[SHIPPED_MISSED_COLUMN] = record["missed"]
    if not has_raw_inputs(record):
        return row
    try:
        board = chess.Board(record["pre_fen"])
    except ValueError as exc:
        raise BadTableError("a row has an unusable pre_fen") from exc
    inputs = facepalm_material_inputs(
        board,
        record["played_uci"],
        record["played_line"] or None,
        record["best_line"] or None,
    )
    row["loss"] = _keep_or_new(record["loss"], _cell(inputs.loss))
    row["missed"] = _keep_or_new(record["missed"], _cell(inputs.missed))
    return row


def _output_columns(names: Sequence[str]) -> list[str]:
    """The input columns minus the stale ones, with the shipped pair right after `missed`."""
    kept = [name for name in names if not name.startswith(STALE_COLUMN_PREFIXES)]
    kept = [name for name in kept if name not in (SHIPPED_LOSS_COLUMN, SHIPPED_MISSED_COLUMN)]
    at = kept.index("missed") + 1
    return [*kept[:at], SHIPPED_LOSS_COLUMN, SHIPPED_MISSED_COLUMN, *kept[at:]]


def _read_table(src: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = src.read_text()
    except OSError as exc:
        raise BadTableError("features file unreadable") from exc
    reader = csv.DictReader(text.splitlines(), delimiter=TSV_DELIMITER, quoting=csv.QUOTE_NONE)
    names = list(reader.fieldnames or ())
    if any(column not in names for column in RAW_INPUT_COLUMNS) or "n" not in names:
        raise BadTableError("features file lacks the raw input columns")
    return names, list(reader)


def refresh_table(src: Path, dst: Path) -> RefreshSummary:
    """Write `src` with the current rule applied to `dst`; raises BadTableError before writing anything."""
    names, records = _read_table(src)
    columns = _output_columns(names)
    refreshed: list[dict[str, str]] = []
    changed: list[str] = []
    without_raw = 0
    for record in records:
        row = refresh_row(record)
        refreshed.append(row)
        if not has_raw_inputs(record):
            without_raw += 1
        elif (row["loss"], row["missed"]) != (record["loss"], record["missed"]):
            changed.append(record["n"])
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            delimiter=TSV_DELIMITER,
            quoting=csv.QUOTE_NONE,
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(refreshed)
    return RefreshSummary(rows=len(records), rows_without_raw_inputs=without_raw, changed_n=changed)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompute loss / missed of a features table with the current material rule."
    )
    parser.add_argument("--features", type=Path, required=True, help="features TSV to refresh")
    parser.add_argument("--out", type=Path, required=True, help="refreshed features TSV to write")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = refresh_table(args.features, args.out)
    except BadTableError as exc:
        print(f"refresh failed: {exc}", file=sys.stderr)
        return EXIT_BAD_TABLE
    print(
        f"wrote {args.out}: {summary.rows} rows, {summary.rows_without_raw_inputs} without raw "
        f"inputs, {len(summary.changed_n)} changed; changed rows (n): {' '.join(summary.changed_n)}"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
