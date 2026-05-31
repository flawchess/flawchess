"""Drift test: committed cohort_cdf.tsv is byte-for-byte reproducible by _write_seed_tsv.

Guards two things simultaneously:

1. **Emitter determinism** -- running ``_write_seed_tsv`` over the same data twice
   produces byte-identical output (no floating-point ordering surprises, no
   timestamp injection, stable sort keys).

2. **Committed-artifact integrity** -- the TSV in ``app/data/cohort_cdf.tsv`` was
   produced by the current ``_write_seed_tsv`` implementation. If the emitter
   changes in a way that would alter output (column order, precision, sort order),
   this test catches the drift so the committed file can be regenerated.

Round-trip formulation (committed TSV -> cells dict -> emit -> compare) is used
intentionally so that:

- The test does NOT depend on the in-source ``COHORT_PERCENTILE_CDF`` registry
  (which Plan 04 removes). It runs against the committed artifact only.
- A fresh CI run after Plan 04 (registry gone) still passes because the cells
  dict is reconstructed from the TSV, not from the in-source literal.

This is the SC#4 canary: "regen drift test diffs the TSV content, not source bytes."
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path
from typing import cast

# Ensure scripts/ is importable (mirrors the pattern in test_gen_global_percentile_cdf_unchanged.py).
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from app.services.global_percentile_cdf import (  # noqa: E402
    CdfMetricId,
    CdfTable,
    TimeControlBucket,
)
from scripts.gen_global_percentile_cdf import _write_seed_tsv  # noqa: E402

_TSV_PATH: Path = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "cohort_cdf.tsv"

_EXPECTED_HEADER = [
    "metric",
    "anchor_elo",
    "tc",
    "percentile",
    "value",
    "n_users",
    "snapshot_month",
]


def _load_cells_from_tsv(
    tsv_path: Path,
) -> dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]]:
    """Reconstruct the cells dict from the committed TSV.

    Groups rows by (metric, anchor_elo, tc), collecting breakpoints in
    percentile order. Mirrors the shape expected by ``_write_seed_tsv``:
    ``dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]]``.

    Returns a dict reconstruction that avoids importing the in-source registry
    (so the test survives Plan 04 which removes ``COHORT_PERCENTILE_CDF``).
    The ``CdfTable`` dataclass and the ``CdfMetricId``/``TimeControlBucket``
    type aliases are stable across plans -- only the registry literal is removed.
    """
    rows_by_cell: dict[tuple[str, int, str], list[tuple[int, float, int, str]]] = {}
    with tsv_path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            key = (row["metric"], int(row["anchor_elo"]), row["tc"])
            rows_by_cell.setdefault(key, []).append(
                (
                    int(row["percentile"]),
                    float(row["value"]),
                    int(row["n_users"]),
                    row["snapshot_month"],
                )
            )

    cells: dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]] = {}
    for (metric, anchor_elo, tc), pct_rows in rows_by_cell.items():
        # Sort by percentile to guarantee correct breakpoints order.
        pct_rows.sort(key=lambda r: r[0])
        breakpoints = tuple(r[1] for r in pct_rows)
        # n_users and snapshot_month are identical across a cell's rows -- take first.
        n_users = pct_rows[0][2]
        snapshot_month = pct_rows[0][3]
        metric_key = cast(CdfMetricId, metric)
        tc_key = cast(TimeControlBucket, tc)
        cells.setdefault(metric_key, {})[(anchor_elo, tc_key)] = CdfTable(
            breakpoints=breakpoints,
            n_users=n_users,
            snapshot_month=snapshot_month,
        )
    return cells


def test_committed_tsv_header() -> None:
    """TSV header row matches the expected seven-column spec (D-02)."""
    with _TSV_PATH.open(newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
    assert header == _EXPECTED_HEADER, f"Header mismatch: {header!r}"


def test_committed_tsv_row_count() -> None:
    """TSV has more than 100,000 data rows (one per breakpoint)."""
    with _TSV_PATH.open() as f:
        # Subtract 1 for header.
        line_count = sum(1 for _ in f) - 1
    assert line_count > 100_000, f"Expected >100k data rows, got {line_count}"


def test_write_seed_tsv_round_trip() -> None:
    """Emitting from the TSV-reconstructed cells produces byte-identical output.

    Round-trip: committed TSV -> cells dict -> _write_seed_tsv -> compare.
    This guards both emitter determinism and committed-artifact integrity.
    """
    cells = _load_cells_from_tsv(_TSV_PATH)
    committed_text = _TSV_PATH.read_text()

    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=True) as tmp:
        tmp_path = Path(tmp.name)
        # Write using the same emitter that produced the committed file.
        _write_seed_tsv(cells, tmp_path)
        regenerated_text = tmp_path.read_text()

    assert regenerated_text == committed_text, (
        "Regenerated TSV content does not match the committed app/data/cohort_cdf.tsv.\n"
        'Either the committed file is stale (re-run: uv run python -c "..._write_seed_tsv...") '
        "or _write_seed_tsv changed its output format.\n"
        f"Committed length: {len(committed_text)}, regenerated length: {len(regenerated_text)}"
    )
