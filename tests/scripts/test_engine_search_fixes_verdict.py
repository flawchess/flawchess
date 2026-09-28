"""Tests for scripts/engine_search_fixes_verdict.py — Phase 225 gate verdict.

Covers Task 1's `<behavior>` block from 225-02-PLAN.md: throughput (T-50/T-400),
move quality (MQ-2/MQ-1) including the rerun-confirmation rule, stop rule
(S1/S2), and the "holds, not a near miss" calibration success path. Task 2's
calibration fail-branch / cells-converter tests live in a later section of
this file.

Every test builds a synthetic per-arm data layout under `tmp_path` (shaped
like `reports/data/engine-search-fixes-225/`) and drives the module through
its public CLI entrypoint, `main(argv)`, asserting on the returned exit code
and the written verdict JSON — never by calling the evaluate_* helpers
directly, so the tests exercise the same path a real gate run does.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

# Mirrors tests/scripts/test_cohort_cdf_seed_artifact.py's sys.path bootstrap.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.engine_search_fixes_verdict import (  # noqa: E402
    EXIT_INCOMPLETE,
    MQ_REGRESSION_MARGIN,
    main,
)

POSITIONS_16 = [f"p{i:02d}" for i in range(16)]
MQ_IDS_12 = [f"mq{i:02d}" for i in range(12)]

THROUGHPUT_HEADER = (
    "position",
    "depth",
    "wall_ms",
    "grade_cpu_ms",
    "nodes_evaluated",
    "maia_peak_inflight",
    "maia_fifo",
)
STOP_HEADER = (
    "position",
    "stop_rule",
    "wall_ms",
    "stop_reason",
    "nodes_evaluated_at_stop",
    "exposure_snapshots",
    "eligible_snapshots",
)
MQ_HEADER = ("id", "delta_bot", "verdict_bot", "delta_analysis", "verdict_analysis")

HOLDS_A21_VS_JULY = {
    "verdict": "holds",
    "maia": {"pooled": {"shift": 10.0, "threshold": 85.0}},
    "sf": {"pooled": {"shift": 5.0, "threshold": 50.0}},
}


def _write_tsv(path: Path, header: Sequence[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(str(row.get(col, "")) for col in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _throughput_rows(
    wall_ms: float,
    grade_cpu_ms: float,
    nodes_evaluated: str = "500",
    maia_peak_inflight: str = "1",
    maia_fifo: str = "true",
    positions: list[str] | None = None,
) -> list[dict[str, object]]:
    positions = positions or POSITIONS_16
    return [
        {
            "position": pos,
            "depth": "ladder",
            "wall_ms": wall_ms,
            "grade_cpu_ms": grade_cpu_ms,
            "nodes_evaluated": nodes_evaluated,
            "maia_peak_inflight": maia_peak_inflight,
            "maia_fifo": maia_fifo,
        }
        for pos in positions
    ]


def write_throughput(tmp_path: Path, arm: str, budget: int, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / arm / f"throughput-{budget}" / "engine-grading-depth-ab-x.tsv",
        THROUGHPUT_HEADER,
        rows,
    )


def _stop_rows(
    wall_values: list[float],
    stop_reasons: list[str],
    stop_rule: str = "on",
    nodes_at_stop: list[int] | None = None,
) -> list[dict[str, object]]:
    nodes_at_stop = nodes_at_stop or [8 + i for i in range(16)]
    return [
        {
            "position": pos,
            "stop_rule": stop_rule,
            "wall_ms": wall_values[i],
            "stop_reason": stop_reasons[i],
            "nodes_evaluated_at_stop": nodes_at_stop[i],
            "exposure_snapshots": 1,
            "eligible_snapshots": 2,
        }
        for i, pos in enumerate(POSITIONS_16)
    ]


def write_stop(tmp_path: Path, arm: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(tmp_path / arm / "stop" / "engine-dispatch-stop-rule-x.tsv", STOP_HEADER, rows)


def _mq_rows(
    delta_bot: list[float],
    verdict_bot: list[str] | None = None,
    delta_analysis: list[float] | None = None,
    verdict_analysis: list[str] | None = None,
    ids: list[str] | None = None,
) -> list[dict[str, object]]:
    ids = ids or MQ_IDS_12
    delta_analysis = delta_analysis if delta_analysis is not None else delta_bot
    verdict_bot = verdict_bot or [
        "regression" if d <= -MQ_REGRESSION_MARGIN else "pass" for d in delta_bot
    ]
    verdict_analysis = verdict_analysis or [
        "regression" if d <= -MQ_REGRESSION_MARGIN else "pass" for d in delta_analysis
    ]
    return [
        {
            "id": ids[i],
            "delta_bot": delta_bot[i],
            "verdict_bot": verdict_bot[i],
            "delta_analysis": delta_analysis[i],
            "verdict_analysis": verdict_analysis[i],
        }
        for i in range(len(ids))
    ]


def write_mq(tmp_path: Path, arm: str, mode: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(tmp_path / arm / mode / "engine-move-quality-x.tsv", MQ_HEADER, rows)


def write_calibration(tmp_path: Path, name: str, payload: Mapping[str, object]) -> None:
    path = tmp_path / "calibration" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def write_full_passing_layout(tmp_path: Path) -> None:
    """A21 vs A2 early-stop counts (7 vs 9) and A21 max wall (9000 ms) mirror
    the plan's own worked examples so a single default fixture supports every
    boundary variant below with minimal per-test overrides."""
    for budget in (50, 400):
        write_throughput(tmp_path, "a0", budget, _throughput_rows(wall_ms=100.0, grade_cpu_ms=50.0))
        write_throughput(tmp_path, "a2", budget, _throughput_rows(wall_ms=80.0, grade_cpu_ms=40.0))

    a2_reasons = ["early-stop"] * 9 + ["budget"] * 7
    a21_reasons = ["early-stop"] * 7 + ["budget"] * 9
    write_stop(tmp_path, "a2", _stop_rows([3000.0] * 16, a2_reasons))
    write_stop(tmp_path, "a21", _stop_rows([9000.0] * 16, a21_reasons))

    write_mq(tmp_path, "a0", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-on", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a21", "mq-on", _mq_rows([0.1] * 12))

    write_calibration(tmp_path, "verdict-a21-vs-july.json", dict(HOLDS_A21_VS_JULY))


def _run_gates(tmp_path: Path) -> tuple[int, dict[str, Any]]:
    out_json = tmp_path / "verdict.json"
    code = main(["gates", "--data-dir", str(tmp_path), "--out-json", str(out_json)])
    return code, json.loads(out_json.read_text(encoding="utf-8"))


# ==============================================================================
# Task 1 behaviors
# ==============================================================================


def test_all_criteria_passing_ships_both_items_and_status_complete(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["status"] == "complete"
    assert verdict["items"]["item2"] == "ship"
    assert verdict["items"]["item1"] == "ship"
    assert verdict["items"]["item3"] == "independent"
    assert verdict["missing"] == []
    assert verdict["rerun_required"] == []


def test_throughput_regression_at_400_fails_and_holds_both_items(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_throughput(tmp_path, "a2", 400, _throughput_rows(wall_ms=100.0 * 1.06, grade_cpu_ms=40.0))
    code, verdict = _run_gates(tmp_path)
    assert code == 0  # complete computation — a regression is a valid HOLD, not incompleteness
    assert verdict["status"] == "complete"
    assert verdict["throughput"]["400"]["passed"] is False
    assert verdict["items"]["item2"] == "hold"
    assert verdict["items"]["item1"] == "hold"  # item 1 is only measured on top of item 2


def test_s2_fails_when_a21_early_stops_below_half_of_a2_holds_item1_only(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    a2_reasons = ["early-stop"] * 9 + ["budget"] * 7
    a21_reasons = ["early-stop"] * 4 + ["budget"] * 12
    write_stop(tmp_path, "a2", _stop_rows([3000.0] * 16, a2_reasons))
    write_stop(tmp_path, "a21", _stop_rows([9000.0] * 16, a21_reasons))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["stop_rule"]["s2_passed"] is False
    assert verdict["items"]["item1"] == "hold"
    assert verdict["items"]["item2"] == "ship"


def test_s1_fails_above_the_12100ms_ceiling(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    reasons = ["early-stop"] * 7 + ["budget"] * 9
    walls = [9000.0] * 15 + [12_101.0]
    write_stop(tmp_path, "a21", _stop_rows(walls, reasons))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["stop_rule"]["s1_passed"] is False
    assert verdict["items"]["item1"] == "hold"


def test_s1_passes_at_exactly_the_12100ms_ceiling_inclusive(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    reasons = ["early-stop"] * 7 + ["budget"] * 9
    walls = [9000.0] * 15 + [12_100.0]
    write_stop(tmp_path, "a21", _stop_rows(walls, reasons))
    code, verdict = _run_gates(tmp_path)
    assert verdict["stop_rule"]["s1_passed"] is True


def test_mq2_flip_without_rerun_is_incomplete_and_reruns_lists_a2_off(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_mq(tmp_path, "a0", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-off", _mq_rows([0.1] * 11 + [-0.10]))
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert verdict["status"] == "incomplete"
    assert "a2 off" in verdict["rerun_required"]

    reruns_code = main(["reruns", "--data-dir", str(tmp_path)])
    assert reruns_code == 0


def test_reruns_stops_listing_a2_off_once_rerun_dir_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_passing_layout(tmp_path)
    write_mq(tmp_path, "a0", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-off", _mq_rows([0.1] * 11 + [-0.10]))
    write_mq(tmp_path, "a2", "mq-off-rerun", _mq_rows([0.1] * 11 + [-0.10]))
    capsys.readouterr()
    assert main(["reruns", "--data-dir", str(tmp_path)]) == 0
    assert "NO RERUNS REQUIRED" in capsys.readouterr().out


def test_mq2_flip_with_rerun_passing_again_is_not_counted(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_mq(tmp_path, "a0", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-off", _mq_rows([0.1] * 11 + [-0.10]))
    write_mq(tmp_path, "a2", "mq-off-rerun", _mq_rows([0.1] * 12))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["status"] == "complete"
    assert verdict["move_quality"]["MQ-2"]["passed"] is True
    assert verdict["items"]["item2"] == "ship"


def test_mq2_flip_with_rerun_regressing_again_is_counted(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_mq(tmp_path, "a0", "mq-off", _mq_rows([0.1] * 12))
    write_mq(tmp_path, "a2", "mq-off", _mq_rows([0.1] * 11 + [-0.10]))
    write_mq(tmp_path, "a2", "mq-off-rerun", _mq_rows([0.1] * 11 + [-0.10]))
    code, verdict = _run_gates(tmp_path)
    assert verdict["move_quality"]["MQ-2"]["passed"] is False
    assert verdict["items"]["item2"] == "hold"


def test_inadmissible_ladder_row_maia_peak_inflight_2_recorded_as_missing(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_throughput(
        tmp_path,
        "a2",
        50,
        _throughput_rows(wall_ms=80.0, grade_cpu_ms=40.0, maia_peak_inflight="2"),
    )
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert verdict["status"] == "incomplete"
    assert any("inadmissible" in m for m in verdict["missing"])


def test_zero_a0_wall_sum_recorded_as_missing_not_crash(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_throughput(tmp_path, "a0", 50, _throughput_rows(wall_ms=0.0, grade_cpu_ms=50.0))
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any("wall_ms sums to zero" in m for m in verdict["missing"])


def test_inadmissible_ladder_row_maia_fifo_false_recorded_as_missing(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    write_throughput(
        tmp_path, "a2", 50, _throughput_rows(wall_ms=80.0, grade_cpu_ms=40.0, maia_fifo="false")
    )
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any("inadmissible" in m for m in verdict["missing"])


def test_position_label_mismatch_between_arms_recorded_as_missing(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    mismatched_positions = [*POSITIONS_16[:15], "different-position"]
    write_throughput(
        tmp_path,
        "a2",
        50,
        _throughput_rows(wall_ms=80.0, grade_cpu_ms=40.0, positions=mismatched_positions),
    )
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any("position-label mismatch" in m for m in verdict["missing"])


def test_duplicate_tsv_in_one_subdir_recorded_as_missing_naming_directory(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    duplicate_dir = tmp_path / "a2" / "stop"
    _write_tsv(
        duplicate_dir / "engine-dispatch-stop-rule-y.tsv",
        STOP_HEADER,
        _stop_rows([3000.0] * 16, ["budget"] * 16),
    )
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any(str(duplicate_dir) in m and "found 2" in m for m in verdict["missing"])


def test_no_tsv_in_a_required_subdir_recorded_as_missing_naming_directory(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    missing_dir = tmp_path / "a0" / "throughput-50"
    for child in missing_dir.glob("*"):
        child.unlink()
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any(str(missing_dir) in m and "found 0" in m for m in verdict["missing"])


def test_delta_verdict_disagreement_recorded_as_missing(tmp_path: Path) -> None:
    write_full_passing_layout(tmp_path)
    # delta_bot says regression (<= -margin) but verdict_bot claims "pass" — margin drift.
    rows = _mq_rows([0.1] * 11 + [-0.10], verdict_bot=["pass"] * 12)
    write_mq(tmp_path, "a2", "mq-off", rows)
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert any("disagrees" in m for m in verdict["missing"])


# ==============================================================================
# Task 2 behaviors — calibration fail branch (D-13 amended / RESEARCH C-6) and
# the A0-cells converter.
# ==============================================================================

from calibration_parity_verdict import (  # noqa: E402
    CellKey,
    CellStats,
    FamilyResult,
    ParityVerdictResult,
    Verdict,
    load_old_cells,
)

from scripts.engine_search_fixes_verdict import (  # noqa: E402
    calibration_branch,
    calibration_item_decisions,
    cells_to_payload,
)


def _family_result(shift: float, threshold: float) -> FamilyResult:
    """Only `pooled.shift`/`pooled.threshold` are read by this module's
    calibration functions — `null_control`/`exposed_cells` are harmless,
    structurally-valid placeholders to satisfy the full `FamilyResult` shape."""
    return {
        "null_control": {
            "shift": 0.0,
            "se_shift": 1.0,
            "threshold": 999.0,
            "within_threshold": True,
        },
        "pooled": {
            "shift": shift,
            "se": 1.0,
            "threshold": threshold,
            "within_threshold": abs(shift) <= threshold,
            "n_cells": 4,
        },
        "exposed_cells": [],
    }


def _parity_verdict(
    verdict: Verdict, maia_shift: float, maia_threshold: float, sf_shift: float, sf_threshold: float
) -> ParityVerdictResult:
    return {
        "maia": _family_result(maia_shift, maia_threshold),
        "sf": _family_result(sf_shift, sf_threshold),
        "shape_guard_triggered": [],
        "verdict": verdict,
    }


def test_calibration_branch_fails_verdict_gives_decision() -> None:
    primary = _parity_verdict("fails", 5.0, 85.0, 2.0, 50.0)
    assert calibration_branch(primary) == "decision"


def test_calibration_branch_void_verdict_gives_decision() -> None:
    primary = _parity_verdict("void", 5.0, 85.0, 2.0, 50.0)
    assert calibration_branch(primary) == "decision"


def test_calibration_branch_holds_with_near_miss_gives_report_only() -> None:
    # Maia |-70| / 85 = 82.4% > 75% -> report-only, even though SF is far inside.
    primary = _parity_verdict("holds", -70.0, 85.0, -9.9, 50.0)
    assert calibration_branch(primary) == "report-only"


def test_calibration_branch_holds_well_inside_thresholds_gives_none() -> None:
    primary = _parity_verdict("holds", -57.7, 85.0, -9.9, 50.0)
    assert calibration_branch(primary) == "none"


def test_calibration_branch_boundary_exactly_75_percent_gives_none() -> None:
    # Exactly 75% of threshold does NOT trigger near-miss — only strictly above does.
    primary = _parity_verdict("holds", -63.75, 85.0, -9.9, 50.0)
    assert calibration_branch(primary) == "none"


def test_calibration_item_decisions_decision_branch_with_drift() -> None:

    primary = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    a0_vs_july = _parity_verdict("fails", 90.0, 85.0, 10.0, 50.0)  # baseline drift: not holds
    a2_vs_a0_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)
    a21_vs_a2_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)

    decision = calibration_item_decisions(
        primary, a0_vs_july, None, a2_vs_a0_holds, a21_vs_a2_holds
    )
    assert decision["baseline_drift"] is True
    assert decision["item2_pass"] is True
    assert decision["item1_pass"] is True

    a21_vs_a2_fails = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    decision2 = calibration_item_decisions(
        primary, a0_vs_july, None, a2_vs_a0_holds, a21_vs_a2_fails
    )
    assert decision2["item2_pass"] is True  # item2 only depends on a2_vs_a0
    assert decision2["item1_pass"] is False  # item1 needs a21_vs_a2 to ALSO hold

    a2_vs_a0_fails = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    decision3 = calibration_item_decisions(
        primary, a0_vs_july, None, a2_vs_a0_fails, a21_vs_a2_holds
    )
    assert decision3["item2_pass"] is False
    assert decision3["item1_pass"] is False  # item1 requires item2 to pass first


def test_calibration_item_decisions_decision_branch_without_drift() -> None:

    primary = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    a0_vs_july_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)  # no baseline drift
    a2_vs_july_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)

    decision = calibration_item_decisions(primary, a0_vs_july_holds, a2_vs_july_holds, None, None)
    assert decision["baseline_drift"] is False
    assert decision["item2_pass"] is True
    assert decision["item1_pass"] is False  # A21 already failed against July — item1 is held

    a2_vs_july_fails = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    decision2 = calibration_item_decisions(primary, a0_vs_july_holds, a2_vs_july_fails, None, None)
    assert decision2["item2_pass"] is False
    assert decision2["item1_pass"] is False


def test_calibration_item_decisions_void_secondary_counts_as_not_holds() -> None:

    primary = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    a0_vs_july_void = _parity_verdict(
        "void", 5.0, 85.0, 2.0, 50.0
    )  # void counts as drift (not holds)
    a2_vs_a0_void = _parity_verdict("void", 5.0, 85.0, 2.0, 50.0)
    a21_vs_a2_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)

    decision = calibration_item_decisions(
        primary, a0_vs_july_void, None, a2_vs_a0_void, a21_vs_a2_holds
    )
    assert decision["baseline_drift"] is True
    assert decision["item2_pass"] is False  # a2_vs_a0 is void, not holds


def test_calibration_item_decisions_report_only_branch() -> None:

    primary = _parity_verdict("holds", -70.0, 85.0, -9.9, 50.0)  # near miss -> report-only
    a2_vs_a0_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)
    a21_vs_a2_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)

    decision = calibration_item_decisions(primary, None, None, a2_vs_a0_holds, a21_vs_a2_holds)
    assert decision["branch"] == "report-only"
    assert decision["item2_pass"] is True
    assert decision["item1_pass"] is True
    assert decision["attribution"]["a2_vs_a0"] == "holds"
    assert decision["attribution"]["a21_vs_a2"] == "holds"
    assert decision["follow_up_seed_recommended"] is False

    a21_vs_a2_fails = _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    decision2 = calibration_item_decisions(primary, None, None, a2_vs_a0_holds, a21_vs_a2_fails)
    assert decision2["item2_pass"] is True
    assert decision2["item1_pass"] is True
    assert decision2["follow_up_seed_recommended"] is True


def test_calibration_item_decisions_report_only_branch_missing_file_raises() -> None:

    primary = _parity_verdict("holds", -70.0, 85.0, -9.9, 50.0)
    a2_vs_a0_holds = _parity_verdict("holds", 5.0, 85.0, 2.0, 50.0)

    try:
        calibration_item_decisions(primary, None, None, a2_vs_a0_holds, None)
        raise AssertionError("expected ValueError for a missing report-only secondary file")
    except ValueError:
        pass


def test_gates_decision_branch_missing_secondary_file_is_incomplete_and_branch_prints_decision(
    tmp_path: Path,
) -> None:
    write_full_passing_layout(tmp_path)
    write_calibration(
        tmp_path, "verdict-a21-vs-july.json", _parity_verdict("fails", 100.0, 85.0, 100.0, 50.0)
    )
    # No verdict-a0-vs-july.json written — the decision branch's first required file.
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert verdict["status"] == "incomplete"
    assert verdict["calibration_branch"] == "decision"

    branch_code = main(["branch", "--data-dir", str(tmp_path)])
    assert branch_code == 0


def test_cells_to_payload_round_trips_through_load_old_cells(tmp_path: Path) -> None:
    cells: dict[CellKey, CellStats] = {
        (1300, 0.05): {
            "bot_elo": 1300,
            "bot_blend": 0.05,
            "rating_vs_maia": 1500.0,
            "ci_vs_maia": (1420.0, 1580.0),
            "rating_vs_sf": 1300.0,
            "ci_vs_sf": (1240.0, 1360.0),
        },
        (1900, 0.05): {
            "bot_elo": 1900,
            "bot_blend": 0.05,
            "rating_vs_maia": 1900.0,
            "ci_vs_maia": (1820.0, 1980.0),
            "rating_vs_sf": 1700.0,
            "ci_vs_sf": (1640.0, 1760.0),
        },
    }
    payload = cells_to_payload(cells)
    out_path = tmp_path / "a0-cells.json"
    out_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_old_cells(str(out_path))
    assert loaded[(1300, 0.05)]["rating_vs_maia"] == cells[(1300, 0.05)]["rating_vs_maia"]
    assert loaded[(1300, 0.05)]["ci_vs_maia"] == cells[(1300, 0.05)]["ci_vs_maia"]
    assert loaded[(1900, 0.05)]["rating_vs_sf"] == cells[(1900, 0.05)]["rating_vs_sf"]
    assert loaded[(1900, 0.05)]["ci_vs_sf"] == cells[(1900, 0.05)]["ci_vs_sf"]
