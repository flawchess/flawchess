"""Tests for scripts/engine_throughput_226_verdict.py — Phase 226 gate verdict.

Task 1 covers the end-to-end gate slice: frozen constants, data layout, and
the underfill throughput criterion (A2 vs the step-0 A0 baseline) flowing
through the CLI to a written verdict JSON, plus the design-input-unset gate
(D-10, D-16) and the root-split-column data-validity check (RESEARCH
Pitfall 1, D-08). Every test drives the module through its public CLI
entrypoint, `main(argv)`, never by calling the evaluate_*/validate_* helpers
directly (mirrors tests/scripts/test_engine_search_fixes_verdict.py), so the
tests exercise the same path a real gate run does.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Mirrors tests/scripts/test_engine_search_fixes_verdict.py's sys.path bootstrap.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.engine_throughput_226_verdict import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_INVALID,
    THROUGHPUT_CONFIGS,
    _DESIGN_INPUT_NAMES,
    main,
)

POSITIONS_16 = [f"p{i:02d}" for i in range(16)]

THROUGHPUT_HEADER = (
    "position",
    "depth",
    "wall_ms",
    "grade_cpu_ms",
    "nodes_evaluated",
    "maia_peak_inflight",
    "maia_fifo",
    "root_split_calls",
    "root_split_premise_violations",
)


def _write_tsv(path: Path, header: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(str(row.get(col, "")) for col in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _throughput_rows(
    wall_ms: float,
    root_split_calls: str = "0",
    root_split_premise_violations: str = "0",
    positions: list[str] | None = None,
) -> list[dict[str, object]]:
    positions = positions or POSITIONS_16
    return [
        {
            "position": pos,
            "depth": "ladder",
            "wall_ms": wall_ms,
            "grade_cpu_ms": wall_ms / 2,
            "nodes_evaluated": "500",
            "maia_peak_inflight": "1",
            "maia_fifo": "true",
            "root_split_calls": root_split_calls,
            "root_split_premise_violations": root_split_premise_violations,
        }
        for pos in positions
    ]


def write_step0_throughput(tmp_path: Path, config: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / "step0" / "throughput" / config / "engine-grading-depth-ab-x.tsv",
        THROUGHPUT_HEADER,
        rows,
    )


def write_gate_throughput(
    tmp_path: Path, arm: str, config: str, rows: list[dict[str, object]]
) -> None:
    _write_tsv(
        tmp_path / "gate" / arm / "throughput" / config / "engine-grading-depth-ab-x.tsv",
        THROUGHPUT_HEADER,
        rows,
    )


def write_full_underfill_layout(tmp_path: Path, a2_ratio: float = 0.95) -> None:
    for config in THROUGHPUT_CONFIGS:
        write_step0_throughput(tmp_path, config, _throughput_rows(wall_ms=100.0))
        write_gate_throughput(tmp_path, "a2", config, _throughput_rows(wall_ms=100.0 * a2_ratio))


def _set_design_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sets every design-input constant to a harmless non-None value — Task 1
    only exercises the underfill throughput criterion, which needs none of
    these values itself, but `gates` refuses to run at all while any is
    unset (D-10, D-16)."""
    import scripts.engine_throughput_226_verdict as module

    monkeypatch.setattr(module, "EXPECTED_MQ_POSITIONS", 50)
    monkeypatch.setattr(module, "MQ_ALLOWANCE_OFF", 1)
    monkeypatch.setattr(module, "MQ_ALLOWANCE_ON", 1)
    monkeypatch.setattr(module, "CALIBRATION_THRESHOLD_MAIA", 85.0)
    monkeypatch.setattr(module, "CALIBRATION_THRESHOLD_SF", 50.0)
    monkeypatch.setattr(module, "ROOT_SPLIT_MAX_T50_WALL_RATIO", 0.97)
    monkeypatch.setattr(module, "CONTENT_MAX_WARM_MEAN_ABS_DES", 0.03)
    monkeypatch.setattr(module, "CONTENT_MAX_CLEAR_MEAN_ABS_DES", 0.02)
    monkeypatch.setattr(module, "STOP_RULE_MAX_WALL_MS", 12_100.0)
    monkeypatch.setattr(module, "CANDIDATE_CAP_ARM_ACTIVE", False)


def _run_gates(tmp_path: Path) -> tuple[int, dict[str, Any]]:
    out_json = tmp_path / "verdict.json"
    code = main(["gates", "--data-dir", str(tmp_path), "--out-json", str(out_json)])
    return code, json.loads(out_json.read_text(encoding="utf-8"))


def _set_design_inputs_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forces every design-input constant back to `None` (#226-08: the module
    default was `None` before the constants were frozen from
    design-inputs.json; this fixture keeps the unset-constants gate testable
    now that the module-level default is the real, non-None value)."""
    import scripts.engine_throughput_226_verdict as module

    for name in _DESIGN_INPUT_NAMES:
        monkeypatch.setattr(module, name, None)


def test_gates_with_every_design_input_unset_exits_incomplete_and_lists_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Every design-input constant forced back to None (module default is now
    # the frozen, non-None value — see _set_design_inputs_none).
    _set_design_inputs_none(monkeypatch)
    write_full_underfill_layout(tmp_path)
    capsys.readouterr()
    code, verdict = _run_gates(tmp_path)
    assert code == EXIT_INCOMPLETE
    assert verdict["status"] == "incomplete"
    out = capsys.readouterr().out
    for name in _DESIGN_INPUT_NAMES:
        assert name in out
        assert any(name in entry for entry in verdict["missing"])


def test_underfill_throughput_passes_when_a2_is_95_percent_of_a0_in_all_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_design_inputs(monkeypatch)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    code, verdict = _run_gates(tmp_path)
    # Task 2: with no MQ/stop/content/calibration data present at all, every
    # OTHER criterion soft-skips to None (no directory -> no "missing" entry)
    # and `status` reaches "complete" — but underfill's own MQ criterion is
    # None too, which D-15 treats as NOT passing (fail-closed on absent MQ
    # data), so every item holds and the shipped-items-only refit is "no-refit".
    assert code == 0
    assert verdict["status"] == "complete"
    underfill = verdict["criteria"]["underfill_throughput"]
    assert underfill["passed"] is True
    for config in THROUGHPUT_CONFIGS:
        assert underfill["configs"][config]["admissible"] is True
        assert underfill["configs"][config]["ratio"] == pytest.approx(0.95)
    assert verdict["criteria"]["underfill_mq"] is None
    assert verdict["criteria"]["guard_s1"] is None
    assert verdict["criteria"]["guard_s2"] is None
    assert verdict["criteria"]["guard_mq"] is None
    assert verdict["criteria"]["root_split_determinism"] is None
    assert verdict["criteria"]["root_split_content"] == {"clear": None, "warm": None}
    assert verdict["criteria"]["root_split_mq"] == {"off": None, "on": None}
    assert verdict["criteria"]["candidate_cap_throughput"] is None
    assert verdict["criteria"]["candidate_cap_mq"] is None
    assert verdict["items"]["underfill"]["outcome"] == "hold"
    assert verdict["items"]["guard"]["outcome"] == "hold"
    assert verdict["items"]["root_split"]["outcome"] == "hold"
    assert verdict["items"]["candidate_cap"] is None
    assert verdict["refit"]["decision"] == "no-refit"


def test_underfill_throughput_fails_when_one_config_is_106_percent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_design_inputs(monkeypatch)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    write_gate_throughput(tmp_path, "a2", "t400-p4", _throughput_rows(wall_ms=100.0 * 1.06))
    code, verdict = _run_gates(tmp_path)
    assert code == 0  # no data error — a failed criterion is a legitimate complete hold
    assert verdict["status"] == "complete"
    underfill = verdict["criteria"]["underfill_throughput"]
    assert underfill["passed"] is False
    assert underfill["configs"]["t400-p4"]["admissible"] is False
    assert underfill["configs"]["t50-p4"]["admissible"] is True
    assert verdict["items"]["underfill"]["outcome"] == "hold"


def test_a21s_throughput_row_with_zero_root_split_calls_is_invalid_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_design_inputs(monkeypatch)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    write_gate_throughput(
        tmp_path, "a21s", "t50-p4", _throughput_rows(wall_ms=90.0, root_split_calls="0")
    )
    out_json = tmp_path / "verdict.json"
    code = main(["gates", "--data-dir", str(tmp_path), "--out-json", str(out_json)])
    assert code == EXIT_INVALID
    assert not out_json.exists()  # invalid data never writes a verdict JSON


def test_a2_throughput_row_with_nonzero_root_split_calls_is_invalid_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_design_inputs(monkeypatch)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    write_gate_throughput(
        tmp_path, "a2", "t50-p4", _throughput_rows(wall_ms=95.0, root_split_calls="1")
    )
    out_json = tmp_path / "verdict.json"
    code = main(["gates", "--data-dir", str(tmp_path), "--out-json", str(out_json)])
    assert code == EXIT_INVALID


def test_a21s_root_split_premise_violation_is_invalid_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_design_inputs(monkeypatch)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    write_gate_throughput(
        tmp_path,
        "a21s",
        "t50-p4",
        _throughput_rows(wall_ms=90.0, root_split_calls="4", root_split_premise_violations="1"),
    )
    out_json = tmp_path / "verdict.json"
    code = main(["gates", "--data-dir", str(tmp_path), "--out-json", str(out_json)])
    assert code == EXIT_INVALID


# ==============================================================================
# Task 2 behaviors — full criteria, item decisions, reruns, calibration/refit.
# ==============================================================================

MQ_HEADER = ("id", "delta_bot", "verdict_bot")
MQ_IDS = ["mq0", "mq1", "mq2", "mq3"]

STOP_HEADER = (
    "position",
    "stop_rule",
    "wall_ms",
    "stop_reason",
    "nodes_evaluated_at_stop",
    "exposure_snapshots",
    "eligible_snapshots",
)

CONTENT_HEADER = (
    "position",
    "position_set",
    "hash_mode",
    "split_source",
    "k",
    "n_candidates",
    "single_ms",
    "split_wall_ms",
    "split_cpu_ms",
    "mean_abs_dcp",
    "max_abs_dcp",
    "mean_abs_des",
    "max_abs_des",
    "noise_mean_abs_des",
    "noise_max_abs_des",
    "root_argmax_flip",
)


def _mq_rows(delta_bot: list[float], ids: list[str] | None = None) -> list[dict[str, object]]:
    ids = ids or MQ_IDS
    return [
        {"id": ids[i], "delta_bot": delta_bot[i], "verdict_bot": "n/a"} for i in range(len(ids))
    ]


def write_step0_mq(
    tmp_path: Path, pass_label: str, mode: str, rows: list[dict[str, object]]
) -> None:
    _write_tsv(
        tmp_path / "step0" / "mq" / pass_label / f"mq-{mode}" / "engine-move-quality-x.tsv",
        MQ_HEADER,
        rows,
    )


def write_gate_mq(tmp_path: Path, arm: str, mode: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / "gate" / arm / f"mq-{mode}" / "engine-move-quality-x.tsv", MQ_HEADER, rows
    )


def write_gate_mq_rerun(tmp_path: Path, arm: str, mode: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / "gate" / arm / f"mq-{mode}-rerun" / "engine-move-quality-x.tsv",
        MQ_HEADER,
        rows,
    )


def _stop_rows(wall_values: list[float], stop_reasons: list[str]) -> list[dict[str, object]]:
    return [
        {
            "position": pos,
            "stop_rule": "on",
            "wall_ms": wall_values[i],
            "stop_reason": stop_reasons[i],
            "nodes_evaluated_at_stop": 8 + i,
            "exposure_snapshots": 1,
            "eligible_snapshots": 2,
        }
        for i, pos in enumerate(POSITIONS_16)
    ]


def write_gate_stop(tmp_path: Path, arm: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / "gate" / arm / "stop" / "engine-dispatch-stop-rule-x.tsv", STOP_HEADER, rows
    )


def _content_rows(hash_mode: str, mean_abs_des: float, n: int = 4) -> list[dict[str, object]]:
    return [
        {
            "position": f"c{i}",
            "position_set": "throughput",
            "hash_mode": hash_mode,
            "split_source": "pool",
            "k": 2,
            "n_candidates": 10,
            "single_ms": 100,
            "split_wall_ms": 60,
            "split_cpu_ms": 120,
            "mean_abs_dcp": 5.0,
            "max_abs_dcp": 10.0,
            "mean_abs_des": mean_abs_des,
            "max_abs_des": mean_abs_des * 2,
            "noise_mean_abs_des": 0.01,
            "noise_max_abs_des": 0.02,
            "root_argmax_flip": "false",
        }
        for i in range(n)
    ]


def write_gate_content(tmp_path: Path, hash_mode: str, rows: list[dict[str, object]]) -> None:
    _write_tsv(
        tmp_path / "gate" / "a21s" / "content" / hash_mode / "engine-root-split-content-x.tsv",
        CONTENT_HEADER,
        rows,
    )


def write_determinism(tmp_path: Path, passed: bool = True) -> None:
    text = "PASS: calibration determinism\n" if passed else "FAIL: calibration determinism\n"
    path = tmp_path / "gate" / "a21s" / "determinism.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _family_result(shift: float, within: bool = True) -> dict[str, object]:
    return {
        "null_control": {
            "shift": 0.0,
            "se_shift": 1.0,
            "threshold": 999.0,
            "within_threshold": within,
        },
        "pooled": {
            "shift": shift,
            "se": 1.0,
            "threshold": 999.0,
            "within_threshold": True,
            "n_cells": 4,
        },
        "exposed_cells": [],
    }


def _parity_payload(
    maia_shift: float = 5.0, sf_shift: float = 2.0, valid: bool = True
) -> dict[str, object]:
    return {
        "maia": _family_result(maia_shift, within=valid),
        "sf": _family_result(sf_shift, within=valid),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }


def write_calibration_verdict(tmp_path: Path, label: str, payload: dict[str, object]) -> None:
    path = tmp_path / "gate" / "calibration" / f"verdict-{label}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_full_passing_layout(tmp_path: Path) -> None:
    """A complete gate layout where underfill, guard, and root split all
    ship (candidate cap stays inactive) — every individual-criterion test
    below starts from this baseline and perturbs exactly one thing."""
    for config in THROUGHPUT_CONFIGS:
        write_step0_throughput(tmp_path, config, _throughput_rows(wall_ms=100.0))
        write_gate_throughput(tmp_path, "a2", config, _throughput_rows(wall_ms=90.0))
        write_gate_throughput(tmp_path, "a21", config, _throughput_rows(wall_ms=90.0))
        a21s_wall = 81.0 if config == "t50-p4" else 90.0
        write_gate_throughput(
            tmp_path,
            "a21s",
            config,
            _throughput_rows(wall_ms=a21s_wall, root_split_calls="4"),
        )

    write_step0_mq(tmp_path, "a0a", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a2", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a2", "on", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21", "on", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21s", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21s", "on", _mq_rows([0.1] * 4))

    write_gate_stop(tmp_path, "a2", _stop_rows([3000.0] * 16, ["early-stop"] * 9 + ["budget"] * 7))
    write_gate_stop(tmp_path, "a21", _stop_rows([9000.0] * 16, ["early-stop"] * 7 + ["budget"] * 9))
    write_gate_stop(
        tmp_path, "a21s", _stop_rows([9000.0] * 16, ["early-stop"] * 7 + ["budget"] * 9)
    )

    write_gate_content(tmp_path, "clear", _content_rows("clear", mean_abs_des=0.01))
    write_gate_content(tmp_path, "warm", _content_rows("warm", mean_abs_des=0.02))

    write_determinism(tmp_path, passed=True)

    write_calibration_verdict(tmp_path, "a2-vs-a0a", _parity_payload())
    write_calibration_verdict(tmp_path, "a21-vs-a2", _parity_payload())
    write_calibration_verdict(tmp_path, "a21s-vs-a21", _parity_payload())


def _set_task2_design_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.engine_throughput_226_verdict as module

    monkeypatch.setattr(module, "EXPECTED_MQ_POSITIONS", 4)
    monkeypatch.setattr(module, "MQ_ALLOWANCE_OFF", 1)
    monkeypatch.setattr(module, "MQ_ALLOWANCE_ON", 1)
    monkeypatch.setattr(module, "CALIBRATION_THRESHOLD_MAIA", 85.0)
    monkeypatch.setattr(module, "CALIBRATION_THRESHOLD_SF", 50.0)
    monkeypatch.setattr(module, "ROOT_SPLIT_MAX_T50_WALL_RATIO", 0.97)
    monkeypatch.setattr(module, "CONTENT_MAX_WARM_MEAN_ABS_DES", 0.03)
    monkeypatch.setattr(module, "CONTENT_MAX_CLEAR_MEAN_ABS_DES", 0.02)
    monkeypatch.setattr(module, "STOP_RULE_MAX_WALL_MS", 12_100.0)
    monkeypatch.setattr(module, "CANDIDATE_CAP_ARM_ACTIVE", False)


def test_full_passing_layout_ships_underfill_guard_and_root_split(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["status"] == "complete"
    assert verdict["items"]["underfill"]["outcome"] == "ship"
    assert verdict["items"]["guard"]["outcome"] == "ship"
    assert verdict["items"]["root_split"]["outcome"] == "ship"
    assert verdict["items"]["candidate_cap"] is None
    assert verdict["refit"]["decision"] == "no-refit"


def test_paired_mq_three_reproduced_flips_and_one_regression_to_pass_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3 pass-to-regression flips (all reproduced by reruns) + 1
    regression-to-pass, allowance 1 -> net 3-1=2 > 1 -> HOLD."""
    import scripts.engine_throughput_226_verdict as module

    _set_task2_design_inputs(monkeypatch)
    monkeypatch.setattr(module, "EXPECTED_MQ_POSITIONS", 5)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    ids = ["mq0", "mq1", "mq2", "mq3", "mq4"]
    # base: mq0 regresses (will pass in arm -> regression-to-pass), mq1-3 pass (will
    # regress in arm -> pass-to-regression), mq4 pass (stays pass).
    base = _mq_rows([-0.10, 0.1, 0.1, 0.1, 0.1], ids=ids)
    arm = _mq_rows([0.1, -0.10, -0.10, -0.10, 0.1], ids=ids)
    rerun = _mq_rows([-0.10, -0.10, -0.10], ids=["mq1", "mq2", "mq3"])  # all reproduce
    write_step0_mq(tmp_path, "a0a", "off", base)
    write_gate_mq(tmp_path, "a2", "off", arm)
    write_gate_mq_rerun(tmp_path, "a2", "off", rerun)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    mq = verdict["criteria"]["underfill_mq"]
    assert mq["status"] == "evaluated"
    assert mq["net"] == 2
    assert mq["passed"] is False
    assert verdict["items"]["underfill"]["outcome"] == "hold"


def test_paired_mq_only_one_reproduced_flip_gives_net_zero_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same shape, but only 1 of the 3 pass-to-regression flips reproduces ->
    net = 1 - 1 = 0 <= allowance 1 -> PASS."""
    import scripts.engine_throughput_226_verdict as module

    _set_task2_design_inputs(monkeypatch)
    monkeypatch.setattr(module, "EXPECTED_MQ_POSITIONS", 5)
    write_full_underfill_layout(tmp_path, a2_ratio=0.95)
    ids = ["mq0", "mq1", "mq2", "mq3", "mq4"]
    base = _mq_rows([-0.10, 0.1, 0.1, 0.1, 0.1], ids=ids)
    arm = _mq_rows([0.1, -0.10, -0.10, -0.10, 0.1], ids=ids)
    # Only mq1 reproduces; mq2/mq3 recover on rerun (unconfirmed).
    rerun = _mq_rows([-0.10, 0.1, 0.1], ids=["mq1", "mq2", "mq3"])
    write_step0_mq(tmp_path, "a0a", "off", base)
    write_gate_mq(tmp_path, "a2", "off", arm)
    write_gate_mq_rerun(tmp_path, "a2", "off", rerun)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    mq = verdict["criteria"]["underfill_mq"]
    assert mq["net"] == 0
    assert mq["passed"] is True


def test_reruns_lists_a2_off_for_unreproduced_flip_and_clears_once_rerun_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_task2_design_inputs(monkeypatch)
    # `reruns` reads every gate MQ pair unconditionally (it is meant to run
    # against a fully-populated data dir), so every pair needs a base+arm
    # TSV present even though only one carries the flip under test.
    write_step0_mq(tmp_path, "a0a", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a2", "off", _mq_rows([0.1] * 3 + [-0.10]))
    write_gate_mq(tmp_path, "a2", "on", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21", "on", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21s", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21s", "on", _mq_rows([0.1] * 4))
    capsys.readouterr()
    code = main(["reruns", "--data-dir", str(tmp_path)])
    assert code == 0
    assert "RERUN a2 off" in capsys.readouterr().out

    write_gate_mq_rerun(tmp_path, "a2", "off", _mq_rows([0.1] * 3 + [-0.10]))
    capsys.readouterr()
    code2 = main(["reruns", "--data-dir", str(tmp_path)])
    assert code2 == 0
    assert "NO RERUNS REQUIRED" in capsys.readouterr().out


def test_s1_fails_when_a21_max_wall_exceeds_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    reasons = ["early-stop"] * 7 + ["budget"] * 9
    walls = [9000.0] * 15 + [12_101.0]
    write_gate_stop(tmp_path, "a21", _stop_rows(walls, reasons))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["guard_s1"]["passed"] is False
    assert verdict["items"]["guard"]["outcome"] == "hold"


def test_s2_fails_when_a21_early_stops_below_half_of_a2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_gate_stop(
        tmp_path, "a21", _stop_rows([9000.0] * 16, ["early-stop"] * 4 + ["budget"] * 12)
    )
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["guard_s2"]["passed"] is False
    assert verdict["items"]["guard"]["outcome"] == "hold"


def test_s2_passes_trivially_when_a2_has_zero_early_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_gate_stop(tmp_path, "a2", _stop_rows([3000.0] * 16, ["budget"] * 16))
    write_gate_stop(tmp_path, "a21", _stop_rows([9000.0] * 16, ["budget"] * 16))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["guard_s2"]["trivial"] is True
    assert verdict["criteria"]["guard_s2"]["passed"] is True


def test_root_split_holds_when_t50_ratio_exceeds_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    # a21 t50-p4 wall is 90; ROOT_SPLIT_MAX_T50_WALL_RATIO is 0.97 -> bound is
    # 90*0.97=87.3; push a21s above it.
    write_gate_throughput(
        tmp_path, "a21s", "t50-p4", _throughput_rows(wall_ms=88.0, root_split_calls="4")
    )
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["root_split_throughput"]["t50_passed"] is False
    assert verdict["items"]["root_split"]["outcome"] == "hold"


def test_root_split_holds_when_warm_content_mean_exceeds_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_gate_content(tmp_path, "warm", _content_rows("warm", mean_abs_des=0.05))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["root_split_content"]["warm"]["passed"] is False
    assert verdict["items"]["root_split"]["outcome"] == "hold"


def test_root_split_holds_when_determinism_pass_line_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_determinism(tmp_path, passed=False)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["criteria"]["root_split_determinism"]["passed"] is False
    assert verdict["items"]["root_split"]["outcome"] == "hold"


def test_guard_held_root_split_ships_with_s1_and_mq_on_report_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard held (S1 at A21 fails) but root split's OWN guard-independent
    criteria all pass -> split still ships; its S1@A21S and MQ(on) results
    are recorded but not decisive."""
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    reasons = ["early-stop"] * 7 + ["budget"] * 9
    walls = [9000.0] * 15 + [12_101.0]
    write_gate_stop(tmp_path, "a21", _stop_rows(walls, reasons))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["items"]["guard"]["outcome"] == "hold"
    assert verdict["items"]["root_split"]["outcome"] == "ship"


def test_underfill_held_cascades_to_guard_root_split_and_cap_all_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    import scripts.engine_throughput_226_verdict as module

    monkeypatch.setattr(module, "CANDIDATE_CAP_ARM_ACTIVE", True)
    write_full_passing_layout(tmp_path)
    for config in THROUGHPUT_CONFIGS:
        write_gate_throughput(
            tmp_path, "a21sc", config, _throughput_rows(wall_ms=85.0, root_split_calls="4")
        )
    write_gate_mq(tmp_path, "a21s", "off", _mq_rows([0.1] * 4))  # baseline for cap
    write_gate_mq(tmp_path, "a21sc", "off", _mq_rows([0.1] * 4))
    write_gate_mq(tmp_path, "a21sc", "on", _mq_rows([0.1] * 4))
    # Break underfill's own throughput criterion.
    write_gate_throughput(tmp_path, "a2", "t50-p4", _throughput_rows(wall_ms=200.0))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["items"]["underfill"]["outcome"] == "hold"
    assert verdict["items"]["guard"]["outcome"] == "hold"
    assert verdict["items"]["root_split"]["outcome"] == "hold"
    assert verdict["items"]["candidate_cap"]["outcome"] == "hold"


def test_calibration_real_shift_on_shipped_underfill_gives_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_calibration_verdict(tmp_path, "a2-vs-a0a", _parity_payload(maia_shift=100.0))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["items"]["underfill"]["outcome"] == "ship"
    assert verdict["refit"]["decision"] == "refit"


def test_calibration_real_shift_on_held_guard_alone_gives_no_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    reasons = ["early-stop"] * 7 + ["budget"] * 9
    walls = [9000.0] * 15 + [12_101.0]
    write_gate_stop(tmp_path, "a21", _stop_rows(walls, reasons))  # holds guard
    write_calibration_verdict(tmp_path, "a21-vs-a2", _parity_payload(maia_shift=100.0))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["items"]["guard"]["outcome"] == "hold"
    assert verdict["refit"]["decision"] == "no-refit"


def test_calibration_void_verdict_for_shipped_item_gives_escalate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)
    write_full_passing_layout(tmp_path)
    write_calibration_verdict(tmp_path, "a2-vs-a0a", _parity_payload(valid=False))
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["items"]["underfill"]["outcome"] == "ship"
    assert verdict["refit"]["decision"] == "escalate"


def test_candidate_cap_inactive_requires_no_a21sc_data_and_is_absent_from_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_task2_design_inputs(monkeypatch)  # CANDIDATE_CAP_ARM_ACTIVE is False
    write_full_passing_layout(tmp_path)
    code, verdict = _run_gates(tmp_path)
    assert code == 0
    assert verdict["status"] == "complete"  # no a21sc data required for completeness
    assert verdict["items"]["candidate_cap"] is None
    assert verdict["criteria"]["candidate_cap_throughput"] is None
    assert verdict["criteria"]["candidate_cap_mq"] is None


# ==============================================================================
# Task 3 behaviors — design-inputs (D-16, D-17) and cells-to-json.
# ==============================================================================


def write_fixture(tmp_path: Path, n_rows: int) -> Path:
    path = tmp_path / "move-quality-226.tsv"
    lines = [
        "# purpose comment line 1",
        "# purpose comment line 2",
        "id\tfen\tcorrect_move\teval_gap_cp\tnote\tsource",
    ]
    for i in range(n_rows):
        lines.append(f"mq{i}\tfen{i}\tmove{i}\t50\tnote\tsource")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_step0_calibration_verdict(tmp_path: Path, name: str, payload: dict[str, object]) -> None:
    path = tmp_path / "step0" / "calibration" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_step0_content(tmp_path: Path, rows: list[dict[str, object]]) -> None:
    # One TSV per hash mode, as the step-0 driver writes them (content/{clear,warm}/).
    for hash_mode in ("clear", "warm"):
        mode_rows = [row for row in rows if row["hash_mode"] == hash_mode]
        if mode_rows:
            _write_tsv(
                tmp_path / "step0" / "content" / hash_mode / "engine-root-split-content-x.tsv",
                CONTENT_HEADER,
                mode_rows,
            )


def write_step0_profile(tmp_path: Path, budget: int, run: int, share: float) -> None:
    path = tmp_path / "step0" / "profile" / f"profile-{budget}-run{run}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"totals": {"nonRootGt8Share": share}}), encoding="utf-8")


def write_step0_stop(tmp_path: Path, rows: list[dict[str, object]]) -> None:
    _write_tsv(tmp_path / "step0" / "stop" / "engine-dispatch-stop-rule-x.tsv", STOP_HEADER, rows)


def _run_design_inputs(
    tmp_path: Path, fixture_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    capsys.readouterr()
    code = main(["design-inputs", "--data-dir", str(tmp_path), "--fixture-path", str(fixture_path)])
    return code, capsys.readouterr().out


def test_expected_mq_positions_equals_fixture_data_row_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 6)
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT EXPECTED_MQ_POSITIONS 6" in out


def test_mq_allowance_is_max_1_and_run_to_run_flip_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    # off mode: 1 flip (mq0 regresses in a0a only) -> d0=1 -> allowance=1
    write_step0_mq(tmp_path, "a0a", "off", _mq_rows([-0.10, 0.1, 0.1, 0.1]))
    write_step0_mq(tmp_path, "a0b", "off", _mq_rows([0.1, 0.1, 0.1, 0.1]))
    # on mode: 2 flips -> d0=2 -> allowance=2
    write_step0_mq(tmp_path, "a0a", "on", _mq_rows([-0.10, -0.10, 0.1, 0.1]))
    write_step0_mq(tmp_path, "a0b", "on", _mq_rows([0.1, 0.1, 0.1, 0.1]))
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT MQ_ALLOWANCE_OFF 1" in out
    assert "DESIGN-INPUT MQ_ALLOWANCE_ON 2" in out


def test_calibration_thresholds_follow_null_check_and_escalate_prints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_calibration_verdict(
        tmp_path, "verdict-a0b-vs-a0a.json", _parity_payload(maia_shift=200.0, sf_shift=5.0)
    )
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    # model_check_fired inflates the threshold to |shift| (200.0), and the
    # shift exceeds 2x the 85.0 base threshold -> escalate.
    assert "DESIGN-INPUT CALIBRATION_THRESHOLD_MAIA 200.0" in out
    assert "DESIGN-INPUT-ESCALATE calibration maia" in out
    assert "DESIGN-INPUT-ESCALATE calibration sf" not in out


def test_root_split_ratio_p_012_gives_g_006_ratio_094(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_throughput(tmp_path, "t50-p4", _throughput_rows(wall_ms=100.0))  # sum 1600
    write_step0_content(
        tmp_path,
        [
            {
                "position": f"p{i}",
                "position_set": "throughput",
                "hash_mode": "clear",
                "split_source": "prototype",
                "k": 2,
                "n_candidates": 10,
                "single_ms": 112.0,  # gain 12 * 16 = 192 -> P = 192/1600 = 0.12
                "split_wall_ms": 100.0,
                "split_cpu_ms": 120,
                "mean_abs_dcp": 1.0,
                "max_abs_dcp": 2.0,
                "mean_abs_des": 0.01,
                "max_abs_des": 0.02,
                "noise_mean_abs_des": 0.02,
                "noise_max_abs_des": 0.03,
                "root_argmax_flip": "false",
            }
            for i in range(16)
        ],
    )
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT ROOT_SPLIT_MAX_T50_WALL_RATIO 0.94" in out


def test_root_split_ratio_p_004_floors_g_at_003_ratio_097(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_throughput(tmp_path, "t50-p4", _throughput_rows(wall_ms=100.0))  # sum 1600
    write_step0_content(
        tmp_path,
        [
            {
                "position": f"p{i}",
                "position_set": "throughput",
                "hash_mode": "clear",
                "split_source": "prototype",
                "k": 2,
                "n_candidates": 10,
                "single_ms": 104.0,  # gain 4 * 16 = 64 -> P = 64/1600 = 0.04
                "split_wall_ms": 100.0,
                "split_cpu_ms": 120,
                "mean_abs_dcp": 1.0,
                "max_abs_dcp": 2.0,
                "mean_abs_des": 0.01,
                "max_abs_des": 0.02,
                "noise_mean_abs_des": 0.02,
                "noise_max_abs_des": 0.03,
                "root_argmax_flip": "false",
            }
            for i in range(16)
        ],
    )
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT ROOT_SPLIT_MAX_T50_WALL_RATIO 0.97" in out


def test_content_bounds_warm_noise_floor_002_gives_warm_003_clear_002(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    # noise_mean_abs_des is a separate column from mean_abs_des; override it directly.
    rows = _content_rows("warm", mean_abs_des=0.5, n=4)
    for row in rows:
        row["noise_mean_abs_des"] = 0.02
    write_step0_content(tmp_path, rows)
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT CONTENT_MAX_WARM_MEAN_ABS_DES 0.03" in out
    assert "DESIGN-INPUT CONTENT_MAX_CLEAR_MEAN_ABS_DES 0.02" in out


def test_d17_shares_055_045_at_50_nodes_mean_050_fires_cap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_profile(tmp_path, 50, 1, 0.55)
    write_step0_profile(tmp_path, 50, 2, 0.45)
    write_step0_profile(tmp_path, 400, 1, 0.10)
    write_step0_profile(tmp_path, 400, 2, 0.10)
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT CANDIDATE_CAP_ARM_ACTIVE True" in out


def test_d17_shares_below_half_at_both_budgets_do_not_fire_cap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_profile(tmp_path, 50, 1, 0.40)
    write_step0_profile(tmp_path, 50, 2, 0.42)
    write_step0_profile(tmp_path, 400, 1, 0.30)
    write_step0_profile(tmp_path, 400, 2, 0.35)
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT CANDIDATE_CAP_ARM_ACTIVE False" in out


def test_stop_rule_max_wall_ms_is_12100_when_a0_max_is_below_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_stop(tmp_path, _stop_rows([9000.0] * 16, ["budget"] * 16))
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT STOP_RULE_MAX_WALL_MS 12100.0" in out


def test_stop_rule_escalates_when_a0_max_meets_or_exceeds_ceiling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = write_fixture(tmp_path, 4)
    write_step0_stop(tmp_path, _stop_rows([9000.0] * 15 + [12_100.0], ["budget"] * 16))
    _code, out = _run_design_inputs(tmp_path, fixture, capsys)
    assert "DESIGN-INPUT-ESCALATE stop-rule" in out
    assert "DESIGN-INPUT STOP_RULE_MAX_WALL_MS None" in out


def test_design_inputs_on_empty_dir_exits_incomplete(tmp_path: Path) -> None:
    code = main(["design-inputs", "--data-dir", str(tmp_path)])
    assert code == EXIT_INCOMPLETE


def test_cells_to_json_round_trips_through_load_old_cells(tmp_path: Path) -> None:
    from calibration_parity_verdict import load_old_cells

    cells_tsv = tmp_path / "a0a-cells.tsv"
    cells_tsv.write_text(
        "bot_elo\tbot_blend\tanchor\twins\tdraws\tlosses\n"
        "1300\t0.05\tmaia1100\t5\t2\t3\n"
        "1300\t0.05\tmaia1500\t6\t1\t3\n"
        "1300\t0.05\tsf3\t4\t3\t3\n"
        "1300\t0.05\tsf5\t5\t2\t3\n",
        encoding="utf-8",
    )
    out_json = tmp_path / "a0a-cells.json"
    code = main(["cells-to-json", "--cells-tsv", str(cells_tsv), "--out-json", str(out_json)])
    assert code == 0
    assert out_json.exists()
    loaded = load_old_cells(str(out_json))
    assert (1300, 0.05) in loaded


# ==============================================================================
# Task 2 (226-08): design-input constants are frozen from the committed
# design-inputs.json — pinning test (D-10). Reads the SAME committed file the
# module's constants were transcribed from, so an edit to either one without
# the other fails this test.
# ==============================================================================

_DESIGN_INPUTS_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "reports"
    / "data"
    / "engine-throughput-226"
    / "step0"
    / "design-inputs.json"
)


def test_design_input_constants_match_committed_json() -> None:
    """Every design-input constant on the module equals the corresponding key
    in the committed reports/data/engine-throughput-226/step0/design-inputs.json
    — the exact value `design-inputs` computed, floats compared exactly as
    serialized (not rounded or approximated). Fails loudly if either the
    module constants or the committed JSON drifts out of sync with the other,
    or if the committed file goes missing."""
    import scripts.engine_throughput_226_verdict as module

    assert _DESIGN_INPUTS_JSON.exists(), (
        f"missing committed design-inputs.json: {_DESIGN_INPUTS_JSON}"
    )
    committed = json.loads(_DESIGN_INPUTS_JSON.read_text(encoding="utf-8"))["values"]

    for name in _DESIGN_INPUT_NAMES:
        expected = committed[name]
        actual = getattr(module, name)
        assert actual == expected, f"{name}: module has {actual!r}, committed JSON has {expected!r}"
