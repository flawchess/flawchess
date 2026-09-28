"""Tests for scripts/engine_search_fixes_allowance.py — Phase 225 D-02 allowance calculator.

Pure-function unit tests over `scripts.engine_search_fixes_allowance` — no DB, no
engines. `load_root_trace_deltas` is exercised against small tmp_path TSV files
shaped like `scripts/engine-dispatch-stop-rule.mjs --root-trace` output.

Covers every bullet in 225-01-PLAN.md's Task 1 `<behavior>` block:
- percentile matches statistics.quantiles(..., method="inclusive")[pct - 1];
  fewer than 2 values raises ValueError.
- round_up_to_step avoids the float-artifact bump (0.07/0.01) but still rounds
  up a genuine fraction (0.071/0.01).
- a pooled p90 at or below 0 yields allowance 0.0 with METHOD measured.
- fewer than D02_MIN_SAMPLES pooled deltas yields the fallback allowance.
- two root-trace TSVs at different ELOs produce two per-ELO rows plus a
  pooled summary.
- a root-trace TSV missing the `delta` column raises ValueError naming the
  file and column.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Mirrors tests/scripts/test_cohort_cdf_seed_artifact.py's sys.path bootstrap.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.engine_search_fixes_allowance import (  # noqa: E402
    D02_FALLBACK_ALLOWANCE,
    D02_MIN_SAMPLES,
    RootTraceDelta,
    compute_allowance,
    load_root_trace_deltas,
    percentile,
    round_up_to_step,
)

TRACE_HEADER = (
    "position",
    "elo",
    "stop_rule",
    "root_move",
    "snapshot_nodes",
    "pre_value",
    "post_value",
    "delta",
)

# Named tolerances (no magic numbers in assertions below).
FLOAT_TOLERANCE = 1e-9


def _write_trace_tsv(
    path: Path, rows: list[dict[str, object]], header: tuple[str, ...] = TRACE_HEADER
) -> None:
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(str(row.get(col, "")) for col in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trace_row(position: str, elo: int, root_move: str, delta: float) -> dict[str, object]:
    return {
        "position": position,
        "elo": elo,
        "stop_rule": "off",
        "root_move": root_move,
        "snapshot_nodes": 3,
        "pre_value": 0.40,
        "post_value": 0.40 + delta,
        "delta": f"{delta:.6f}",
    }


def test_percentile_matches_statistics_quantiles_and_rejects_singleton() -> None:
    import statistics

    values = [0.01, 0.05, 0.02, 0.09, 0.03, 0.11, 0.04]
    assert percentile(values, 90) == pytest.approx(
        statistics.quantiles(values, n=100, method="inclusive")[89]
    )

    with pytest.raises(ValueError, match="at least 2"):
        percentile([0.5], 90)


def test_round_up_to_step_avoids_float_artifact_but_rounds_up_genuine_fraction() -> None:
    assert round_up_to_step(0.07, 0.01) == pytest.approx(0.07)
    assert round_up_to_step(0.071, 0.01) == pytest.approx(0.08)


def test_pooled_p90_at_or_below_zero_yields_measured_zero_allowance() -> None:
    deltas: list[RootTraceDelta] = [
        RootTraceDelta(position=f"p{i}", elo=1500, root_move="e2e4", delta=-0.05)
        for i in range(D02_MIN_SAMPLES)
    ]
    result = compute_allowance(deltas)
    assert result["method"] == "measured"
    assert result["allowance"] == pytest.approx(0.0)


def test_fewer_than_min_samples_falls_back() -> None:
    deltas: list[RootTraceDelta] = [
        RootTraceDelta(position=f"p{i}", elo=1500, root_move="e2e4", delta=0.05)
        for i in range(D02_MIN_SAMPLES - 1)
    ]
    result = compute_allowance(deltas)
    assert result["method"] == "fallback"
    assert result["allowance"] == pytest.approx(D02_FALLBACK_ALLOWANCE)
    assert result["pooled_p90"] is None


def test_two_elo_trace_files_produce_two_per_elo_rows_plus_pooled(tmp_path: Path) -> None:
    rows_1300 = [_trace_row("italian", 1300, "e2e4", 0.02 + 0.001 * i) for i in range(20)]
    rows_1900 = [_trace_row("middlegame", 1900, "d2d4", 0.01 + 0.001 * i) for i in range(20)]
    _write_trace_tsv(tmp_path / "engine-root-trace-round-elo1300-stopoff-a.tsv", rows_1300)
    _write_trace_tsv(tmp_path / "engine-root-trace-round-elo1900-stopoff-b.tsv", rows_1900)

    deltas = load_root_trace_deltas(tmp_path)
    assert len(deltas) == 40

    result = compute_allowance(deltas)
    assert result["method"] == "measured"
    assert {row["elo"] for row in result["per_elo"]} == {1300, 1900}
    assert len(result["per_elo"]) == 2
    assert result["pooled_n"] == 40
    assert result["pooled_p90"] is not None


def test_missing_delta_column_raises_naming_file_and_column(tmp_path: Path) -> None:
    bad_header = (
        "position",
        "elo",
        "stop_rule",
        "root_move",
        "snapshot_nodes",
        "pre_value",
        "post_value",
    )
    trace_path = tmp_path / "engine-root-trace-round-elo1500-stopoff-c.tsv"
    _write_trace_tsv(
        trace_path,
        [
            {
                "position": "italian",
                "elo": 1500,
                "stop_rule": "off",
                "root_move": "e2e4",
                "snapshot_nodes": 3,
                "pre_value": 0.4,
                "post_value": 0.47,
            }
        ],
        header=bad_header,
    )

    with pytest.raises(ValueError) as excinfo:
        load_root_trace_deltas(tmp_path)
    message = str(excinfo.value)
    assert str(trace_path) in message
    assert "delta" in message


def test_no_matching_files_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No files matching"):
        load_root_trace_deltas(tmp_path)
