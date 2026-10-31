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
  (since removed). It runs against the committed artifact only.
- A fresh CI run (registry gone) still passes because the cells
  dict is reconstructed from the TSV, not from the in-source literal.

This is the canary: "regen drift test diffs the TSV content, not source bytes."
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

# Ensure scripts/ is importable (mirrors the pattern in test_gen_global_percentile_cdf_unchanged.py).
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from app.services.global_percentile_cdf import (  # noqa: E402
    BREAKPOINT_PERCENTILES,
    CdfTable,
)
from scripts.gen_global_percentile_cdf import (  # noqa: E402
    CdfCells,
    _write_seed_tsv,
    load_cells_from_tsv,
    merge_cells,
)

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


def test_committed_tsv_header() -> None:
    """TSV header row matches the expected seven-column spec."""
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
    cells = load_cells_from_tsv(_TSV_PATH)
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


def _synthetic_opening_cells() -> CdfCells:
    """Two synthetic opening cells (one per metric) with a full 99-breakpoint curve."""
    breakpoints = tuple(i / 200 for i in range(len(BREAKPOINT_PERCENTILES)))
    table = CdfTable(breakpoints=breakpoints, n_users=123, snapshot_month="2026-05")
    return {
        "opening_worse_rate": {(1500, "blitz"): table},
        "opening_better_rate": {(1500, "blitz"): table},
    }


def test_merged_tsv_keeps_existing_rows_as_exact_prefix() -> None:
    """Merging fresh opening cells leaves the committed rows byte-identical, in order.

    Scoped regen guarantee (Phase 243): only the selected metrics' rows may differ. The
    opening metrics sort last in ``IN_SCOPE_METRICS``, so the merged file starts with
    every non-opening line of the committed file and is followed only by opening rows.
    """
    existing = load_cells_from_tsv(_TSV_PATH)
    fresh = _synthetic_opening_cells()
    merged = merge_cells(existing, fresh, ["opening_worse_rate", "opening_better_rate"])

    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=True) as tmp:
        tmp_path = Path(tmp.name)
        _write_seed_tsv(merged, tmp_path)
        merged_lines = tmp_path.read_text().splitlines()

    committed_lines = [
        line
        for line in _TSV_PATH.read_text().splitlines()
        if not line.startswith(("opening_worse_rate\t", "opening_better_rate\t"))
    ]
    assert merged_lines[: len(committed_lines)] == committed_lines
    tail = merged_lines[len(committed_lines) :]
    assert tail, "merged file must carry the synthetic opening rows"
    assert all(line.startswith(("opening_worse_rate\t", "opening_better_rate\t")) for line in tail)
    assert len(tail) == 2 * len(BREAKPOINT_PERCENTILES)


def test_committed_tsv_contains_the_opening_metrics() -> None:
    """The release runbook seeds this TSV before the Stage B backfill (docs/production-runbook.md).

    If the opening metric ids were missing, the backfill would persist NULL-percentile rows for
    every existing user (interpolation against a missing cell returns None) and nothing would
    flag it, so pin their presence in the committed artifact.
    """
    cells = load_cells_from_tsv(_TSV_PATH)
    for metric in ("opening_worse_rate", "opening_better_rate"):
        assert cells.get(metric), f"{metric} has no cells in the committed cohort_cdf.tsv"
