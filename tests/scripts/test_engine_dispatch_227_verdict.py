"""Tests for scripts/engine_dispatch_227_verdict.py — Phase 227 gate verdict.

The twin of `reports/continuous-dispatch-227/accept-rule.md` (D-00..D-04, D-07,
D-15, D-17, D-20). Two groups of tests:

* Move quality (Task 1): the frozen constants, the D-01 signed point-estimate
  rule, the D-03 net-regression allowance, the round-mode tripwire and the
  invalid/incomplete exit codes.
* Throughput, WebGPU, calibration and the composed `gates` verdict (Task 2).

Boundary behavior is pinned through the small pure helpers (`d01_passes`,
`mq_allowance`) because hand-building TSV data whose mean lands exactly on a
float margin is fragile; end-to-end behavior is driven through `main(argv)`,
the same path a real gate run takes.

Mutation checks (recorded in 227-03-SUMMARY.md): flipping `d01_passes` to a
strict `>` fails `test_d01_exact_margin_passes`. Plan 227-09 (owner direction
2026-10-02: very similar is good enough) turned the round-repeat determinism
check into a report-only rate; restoring the raise fails
`test_round_repeat_disagreement_is_valid_and_report_only`.
"""

from __future__ import annotations

import csv
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Mirrors tests/scripts/test_engine_throughput_226_verdict.py's sys.path
# bootstrap: the twin's own bare `import engine_throughput_226_calibration`
# needs `scripts/` on sys.path directly.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import scripts.engine_dispatch_227_verdict as twin  # noqa: E402
from scripts.engine_dispatch_227_verdict import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_INVALID,
    MQ_REPEATS,
    MQ_SIGNED_MARGIN,
    d01_passes,
    evaluate_mq_cell,
    main,
    mq_allowance,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BASELINE_A21S = _REPO_ROOT / "reports" / "data" / "engine-throughput-226" / "gate" / "a21s"


def _fixture_ids() -> list[str]:
    """The 60 move-quality fixture ids, read independently of the twin."""
    with (_REPO_ROOT / "fixtures" / "engine" / "move-quality-226.tsv").open(
        encoding="utf-8", newline=""
    ) as f:
        lines = [line for line in f if not line.startswith("#")]
    return [row["id"] for row in csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)]


IDS = _fixture_ids()

MQ_HEADER = (
    "arm",
    "stop_rule",
    "id",
    "bot_move",
    "es_bot",
    "es_correct",
    "delta_bot",
    "verdict_bot",
    "analysis_move",
    "es_analysis",
    "nodes_evaluated",
    "stop_reason",
    "grade_depth",
    "dispatch_mode",
    "repeat",
    "hash_mode",
    "maia_fifo",
)


def _write_tsv(path: Path, header: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(str(row.get(col, "")) for col in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mq_rows(
    mode: str,
    *,
    es: Callable[[str, int], float] = lambda i, r: 0.5,
    move: Callable[[str, int], str] = lambda i, r: "e2e4",
    regress: Callable[[str, int], bool] = lambda i, r: False,
    es_analysis: Callable[[str, int], float] = lambda i, r: 0.5,
    repeats: int = MQ_REPEATS,
    ids: list[str] | None = None,
    grade_depth: int = 20,
    hash_mode: str = "warm",
    maia_fifo: str = "true",
    stop: str = "off",
) -> list[dict[str, Any]]:
    """One MQ TSV's rows. A regression row carries the harness's own
    `verdict_bot` text; es_correct is fixed at 0.5 so delta = es - 0.5."""
    rows: list[dict[str, Any]] = []
    for repeat in range(1, repeats + 1):
        for pid in ids if ids is not None else IDS:
            value = es(pid, repeat)
            rows.append(
                {
                    "arm": "x",
                    "stop_rule": stop,
                    "id": pid,
                    "bot_move": move(pid, repeat),
                    "es_bot": f"{value:.6f}",
                    "es_correct": "0.500000",
                    "delta_bot": f"{value - 0.5:.6f}",
                    "verdict_bot": "regression" if regress(pid, repeat) else "pass",
                    "analysis_move": move(pid, repeat),
                    "es_analysis": f"{es_analysis(pid, repeat):.6f}",
                    "nodes_evaluated": "50",
                    "stop_reason": "budget",
                    "grade_depth": str(grade_depth),
                    "dispatch_mode": mode,
                    "repeat": str(repeat),
                    "hash_mode": hash_mode,
                    "maia_fifo": maia_fifo,
                }
            )
    return rows


def write_cell(
    data_dir: Path,
    arm_mode: str,
    stop: str,
    rows: list[dict[str, Any]],
    base: str = "gate/mq",
) -> None:
    _write_tsv(
        data_dir / base / arm_mode / f"mq-{stop}" / f"engine-move-quality-{arm_mode}-{stop}.tsv",
        MQ_HEADER,
        rows,
    )


def write_passing_mq(data_dir: Path) -> None:
    """Both judged cells, round == continuous (D = 0, net = 0)."""
    for stop in ("off", "on"):
        write_cell(data_dir, "round", stop, mq_rows("round", stop=stop))
        write_cell(data_dir, "continuous", stop, mq_rows("continuous", stop=stop))


def run_mq(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["mq", "--data-dir", str(data_dir)])
    return rc, capsys.readouterr().out


def cell_line(out: str, cell: str) -> str:
    lines = [ln for ln in out.splitlines() if ln.startswith(f"MQ {cell} ")]
    assert len(lines) == 1, out
    return lines[0]


# ==============================================================================
# Frozen constants (T-227-05)
# ==============================================================================


def test_frozen_constants() -> None:
    assert twin.MQ_SIGNED_MARGIN_K == 1.5
    assert twin.MQ_CONTENT_FLOOR == 0.016804127272727273
    assert twin.MQ_SIGNED_MARGIN == 0.02520619090909091
    assert twin.MQ_REPEATS == 5
    assert twin.MQ_GRADE_DEPTH == 20
    assert twin.MQ_NODES == 50
    assert twin.MQ_A400_NODES == 400
    assert twin.MQ_REGRESSION_MARGIN == 0.05
    assert twin.MQ_ALLOWANCE_FLOOR == 1
    assert twin.EXPECTED_MQ_POSITIONS == 60
    assert twin.JUDGED_MQ_CELLS == ("off", "on")
    assert twin.BOOTSTRAP_SAMPLES == 10000
    assert twin.BOOTSTRAP_SEED == 227
    assert twin.BOOTSTRAP_CONFIDENCE == 0.95
    assert twin.THROUGHPUT_SHIP_GAIN == 0.15
    assert twin.THROUGHPUT_MAX_RATIO == 1.03
    assert twin.POOL2_MIN_TOLERANCE == 0.03
    assert twin.THROUGHPUT_MIN_ROUNDS == 3
    assert twin.EXPECTED_THROUGHPUT_POSITIONS == 16
    assert twin.SHIP_BAR_CONFIGS == ("stop-p4", "t400-p4")
    assert twin.POOL2_CONFIGS == ("t50-p2", "t400-p2")
    assert twin.LOAD_GATE_MAX == 2.0
    assert twin.WEBGPU_MAX_RATIO == 1.03
    assert twin.WEBGPU_MIN_ROUNDS == 3
    assert twin.WEBGPU_SCHEMA == "engine-bench-227/v1"
    assert twin.CALIBRATION_THRESHOLD_MAIA == 85.0
    assert twin.CALIBRATION_THRESHOLD_SF == 53.542812708469995
    assert twin.SHAPE_GUARD_Z == 1.96
    assert twin.GAMES_PER_CELL_ANCHOR == 50
    assert twin.ARM_SEED == 1
    assert twin.EXIT_INVALID == 1
    assert twin.EXIT_INCOMPLETE == 2
    assert twin.ARM_MODE == {"a0": "round", "a1": "continuous"}


def test_frozen_paths() -> None:
    assert twin.DEFAULT_DATA_DIR.endswith("reports/data/continuous-dispatch-227")
    assert twin.DEFAULT_VERDICT_JSON.endswith("reports/continuous-dispatch-227/verdict.json")
    assert twin.BASELINE_A21S_DIR.endswith("reports/data/engine-throughput-226/gate/a21s")
    assert twin.FIXTURE_PATH.endswith("fixtures/engine/move-quality-226.tsv")


_ACCEPT_RULE = _REPO_ROOT / "reports" / "continuous-dispatch-227" / "accept-rule.md"
#: Locations, not thresholds: the pin test does not require them in the rule's table.
_PATH_CONSTANTS = frozenset(
    {"DEFAULT_DATA_DIR", "DEFAULT_VERDICT_JSON", "BASELINE_A21S_DIR", "FIXTURE_PATH"}
)


def _accept_rule_constant_rows() -> list[tuple[str, str]]:
    """Every `| NAME | value | decision |` row of the accept rule's section 2,
    as (name, value) with the markdown backticks stripped."""
    text = _ACCEPT_RULE.read_text(encoding="utf-8")
    section = text.split("\n## 2.", 1)[1].split("\n## 3.", 1)[0]
    rows: list[tuple[str, str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        name = cells[0].strip("`")
        if name == "NAME" or set(name) <= set("-: "):
            continue
        rows.append((name, cells[1].removeprefix("`").removesuffix("`")))
    return rows


def test_accept_rule_matches_twin_constants() -> None:
    """The accept rule's frozen-constants table equals the twin's frozen block:
    every row's value is the exact `repr` of the twin constant of that name, and
    every public UPPER_CASE twin constant (except the path constants) appears in
    the table exactly once. Editing either side alone fails this test."""
    rows = _accept_rule_constant_rows()
    names = [name for name, _ in rows]
    assert len(names) == len(set(names)), "duplicate constant rows in accept-rule.md section 2"
    frozen = {
        name
        for name in dir(twin)
        if name.isupper() and not name.startswith("_") and name not in _PATH_CONSTANTS
    }
    assert set(names) == frozen, (
        f"table-only: {sorted(set(names) - frozen)}, twin-only: {sorted(frozen - set(names))}"
    )
    for name, value in rows:
        assert value == repr(getattr(twin, name)), f"{name}: rule says {value}"


def test_accept_rule_has_every_section_and_pinned_command() -> None:
    """Sections 1 to 10 exist, and the pinned commands the gate runs are in the
    rule (a gate run copies them from here)."""
    text = _ACCEPT_RULE.read_text(encoding="utf-8")
    for number in range(1, 11):
        assert f"\n## {number}. " in text, f"section {number} missing"
    for needle in (
        "scripts/engine-move-quality.mjs",
        "--repeats 5 --maia-fifo --hash warm --grade-depth 20",
        "--repeats 1 --maia-fifo --hash clear",
        "--nodes 400 --stop-rule off",
        "scripts/engine_interleave_227.py run",
        "reports/data/continuous-dispatch-227/gate/throughput",
        "PRESET_SUPERVISOR_DISPATCH_MODE",
        "PRESET_SUPERVISOR_ANCHORS",
        "PRESET_SUPERVISOR_GAMES=50",
        "cells-to-json",
        "verdict-a1-vs-a0.json",
        "webgpu/continuous-leg.json",
        "399780bf8",
        "cef88fd87",
        "Virtual-loss trigger",
        "separate dated override",
    ):
        assert needle in text, needle


def test_margin_is_k_times_floor() -> None:
    assert abs(twin.MQ_SIGNED_MARGIN - twin.MQ_SIGNED_MARGIN_K * twin.MQ_CONTENT_FLOOR) < 1e-12


def test_no_threshold_is_reachable_from_the_cli(capsys: pytest.CaptureFixture[str]) -> None:
    """The argparse surface carries data locations only: an attempt to pass a
    threshold flag is a usage error (argparse exits 2, never silently accepted)."""
    for flag in ("--margin", "--repeats", "--ship-gain", "--max-ratio"):
        with pytest.raises(SystemExit):
            main(["mq", "--data-dir", ".", flag, "1"])
        capsys.readouterr()


# ==============================================================================
# D-01 — signed point-estimate rule
# ==============================================================================


def test_d01_exact_margin_passes() -> None:
    assert d01_passes(-MQ_SIGNED_MARGIN) is True


def test_d01_just_below_margin_fails() -> None:
    assert d01_passes(-MQ_SIGNED_MARGIN - 1e-9) is False


def test_d01_positive_difference_passes() -> None:
    assert d01_passes(0.2) is True


def test_mq_cli_better_continuous_passes_d01(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A continuous mode that picks BETTER moves passes (D-00): D > 0."""
    for stop in ("off", "on"):
        write_cell(tmp_path, "round", stop, mq_rows("round", stop=stop))
        write_cell(
            tmp_path,
            "continuous",
            stop,
            mq_rows("continuous", stop=stop, es=lambda i, r: 0.9 if i == IDS[0] else 0.5),
        )
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    line = cell_line(out, "off")
    assert "d01=pass" in line
    assert "D=0.006667" in line


def test_mq_cli_much_worse_continuous_fails_d01_and_still_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Four positions lose 0.5 each: D = -2/60 = -0.0333, below -margin.
    Complete and valid inputs exit 0 even on a failing verdict: pass/fail is
    read from the printed line, never from the exit code."""
    worse = set(IDS[:4])
    for stop in ("off", "on"):
        write_cell(tmp_path, "round", stop, mq_rows("round", stop=stop))
        write_cell(
            tmp_path,
            "continuous",
            stop,
            mq_rows("continuous", stop=stop, es=lambda i, r: 0.0 if i in worse else 0.5),
        )
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    assert "d01=fail" in cell_line(out, "off")
    assert "d01=fail" in cell_line(out, "on")


def test_d01_uses_the_mean_over_repeats_of_each_arm() -> None:
    """Position i: continuous alternates 0.0 / 0.4 over five repeats (mean
    0.16), round is 0.5. Per-position difference = -0.34, pooled over repeats
    BEFORE the position mean (not the worst repeat, not repeat 1)."""
    pid = IDS[0]
    cont_es = {1: 0.0, 2: 0.4, 3: 0.0, 4: 0.4, 5: 0.0}
    result = evaluate_mq_cell(
        "off",
        mq_rows("round"),
        mq_rows("continuous", es=lambda i, r: cont_es[r] if i == pid else 0.5),
    )
    assert result["decision_d"] == pytest.approx(-0.34 / len(IDS))


# ==============================================================================
# D-03 — net regressions with a repeat-flip allowance
# ==============================================================================


def test_mq_allowance_floor_is_one_when_repeats_agree() -> None:
    assert mq_allowance(mq_rows("continuous")) == 1


def test_mq_allowance_is_max_over_repeat_pairs() -> None:
    """Repeat 1 regresses on positions 0..2; repeat 2 regresses on 3..4. Pair
    (1,2): pass->regression 2 (3,4), regression->pass 3 (0,1,2): |N| = 1. Pair
    (1,3) where repeat 3 regresses on nothing: regression->pass 3 -> |N| = 3."""
    regress_by_repeat = {
        1: set(IDS[0:3]),
        2: set(IDS[3:5]),
        3: set(),
        4: set(),
        5: set(),
    }
    rows = mq_rows("continuous", regress=lambda i, r: i in regress_by_repeat[r])
    assert mq_allowance(rows) == 3


def test_mq_allowance_is_signed_net_not_flip_count() -> None:
    """Two repeats that SWAP one regression for another have net flips 0 even
    though two positions flipped: the allowance stays at the floor."""
    regress_by_repeat = {1: {IDS[0]}, 2: {IDS[1]}, 3: {IDS[0]}, 4: {IDS[1]}, 5: {IDS[0]}}
    rows = mq_rows("continuous", regress=lambda i, r: i in regress_by_repeat[r])
    assert mq_allowance(rows) == 1


def test_d03_net_uses_fractional_continuous_regression_rate() -> None:
    """Position 0 regresses in 2 of 5 continuous repeats, round never: rho =
    0.4, so net = 0.4 (not 1, not 0)."""
    pid = IDS[0]
    result = evaluate_mq_cell(
        "off",
        mq_rows("round"),
        mq_rows("continuous", regress=lambda i, r: i == pid and r <= 2),
    )
    assert result["net"] == pytest.approx(0.4)


def test_d03_continuous_fix_lowers_net() -> None:
    """Round regresses on position 0 (every repeat, deterministic); continuous
    never does: the fix counts in continuous's favor, net = -1."""
    pid = IDS[0]
    result = evaluate_mq_cell(
        "off",
        mq_rows("round", regress=lambda i, r: i == pid),
        mq_rows("continuous"),
    )
    assert result["net"] == pytest.approx(-1.0)
    assert result["pass_d03"] is True


def test_d03_net_equal_to_allowance_passes_and_above_fails() -> None:
    """Allowance 1 (repeats agree). One position regressing in every
    continuous repeat gives net exactly 1 -> pass; two give net 2 -> fail."""
    one = {IDS[0]}
    two = {IDS[0], IDS[1]}
    at_limit = evaluate_mq_cell(
        "off", mq_rows("round"), mq_rows("continuous", regress=lambda i, r: i in one)
    )
    assert (at_limit["net"], at_limit["allowance"], at_limit["pass_d03"]) == (1.0, 1, True)
    above = evaluate_mq_cell(
        "off", mq_rows("round"), mq_rows("continuous", regress=lambda i, r: i in two)
    )
    assert (above["net"], above["allowance"], above["pass_d03"]) == (2.0, 1, False)


def test_mq_cli_d03_failure_is_printed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = set(IDS[:3])
    for stop in ("off", "on"):
        write_cell(tmp_path, "round", stop, mq_rows("round", stop=stop))
        write_cell(
            tmp_path,
            "continuous",
            stop,
            mq_rows("continuous", stop=stop, regress=lambda i, r: i in bad),
        )
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    line = cell_line(out, "on")
    assert "net=3.0" in line
    assert "allowance=1" in line
    assert "d03=fail" in line


# ==============================================================================
# Invalid (exit 1) and incomplete (exit 2) data
# ==============================================================================


def test_round_repeat_disagreement_is_valid_and_report_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Owner direction 2026-10-02: bit-identical round results are not required
    with concurrent (worker-thread) Maia, so round repeats that pick different
    moves are VALID data, not a harness leak. The disagreement rate is reported
    and the decision math just averages over repeats (D) and uses the
    fractional net (D-03). Restoring the old `InvalidDataError` raise fails
    this test (mutation proof)."""
    write_passing_mq(tmp_path)
    write_cell(
        tmp_path,
        "round",
        "off",
        mq_rows(
            "round",
            move=lambda i, r: "a2a3" if (i == IDS[0] and r == 2) else "e2e4",
            es=lambda i, r: 0.1 if (i == IDS[0] and r == 2) else 0.5,
            regress=lambda i, r: i == IDS[0] and r == 2,
        ),
    )
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    off_report = next(ln for ln in out.splitlines() if ln.startswith("MQ-REPORT off "))
    on_report = next(ln for ln in out.splitlines() if ln.startswith("MQ-REPORT on "))
    assert f"round_repeat_disagreement=1/{len(IDS)} (0.0167)" in off_report
    assert f"round_repeat_disagreement=0/{len(IDS)} (0.0000)" in on_report
    # D averages the position over repeats: (0.5 - (4 * 0.5 + 0.1) / 5) / 60.
    assert "d01=pass" in cell_line(out, "off") and "d03=pass" in cell_line(out, "off")


def test_round_repeat_disagreement_is_in_the_cell_report() -> None:
    """The statistic lives in the verdict JSON's report-only section (the
    cell's `report`), counts positions whose `bot_move` differs across round
    repeats, and cannot change D-01 or D-03."""
    pid = IDS[0]
    agreeing = evaluate_mq_cell("off", mq_rows("round"), mq_rows("continuous"))
    assert agreeing["report"]["round_repeat_disagreement_positions"] == 0
    assert agreeing["report"]["round_repeat_disagreement_rate"] == 0.0

    result = evaluate_mq_cell(
        "off",
        mq_rows(
            "round",
            move=lambda i, r: "a2a3" if (i == pid and r in (2, 4)) else "e2e4",
            es=lambda i, r: 0.1 if (i == pid and r in (2, 4)) else 0.5,
            regress=lambda i, r: i == pid and r in (2, 4),
        ),
        mq_rows("continuous"),
    )
    report = result["report"]
    assert report["round_repeat_disagreement_positions"] == 1
    assert report["round_repeat_disagreement_rate"] == pytest.approx(1 / len(IDS))
    # Two of five round repeats at 0.1: round mean 0.34, so D = 0.16 / 60 > 0.
    assert result["decision_d"] == pytest.approx(0.16 / len(IDS))
    assert result["net"] == pytest.approx(-0.4)
    assert result["passed"] is True


def test_invalid_continuous_tsv_labeled_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_passing_mq(tmp_path)
    write_cell(tmp_path, "continuous", "on", mq_rows("round", stop="on"))
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INVALID


@pytest.mark.parametrize(
    "overrides",
    [
        {"maia_fifo": "false"},
        {"hash_mode": "clear"},
        {"grade_depth": 18},
    ],
    ids=["maia-fifo-off", "clear-hash", "wrong-grade-depth"],
)
def test_invalid_judged_cell_conditions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], overrides: dict[str, Any]
) -> None:
    write_passing_mq(tmp_path)
    write_cell(tmp_path, "continuous", "off", mq_rows("continuous", **overrides))
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INVALID


def test_invalid_id_not_in_fixture(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_passing_mq(tmp_path)
    write_cell(
        tmp_path,
        "continuous",
        "off",
        mq_rows("continuous", ids=[*IDS[:-1], "not-a-fixture-id"]),
    )
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INVALID


def test_incomplete_missing_cell_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_passing_mq(tmp_path)
    for tsv in (tmp_path / "gate" / "mq" / "continuous" / "mq-on").glob("*.tsv"):
        tsv.unlink()
    (tmp_path / "gate" / "mq" / "continuous" / "mq-on").rmdir()
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INCOMPLETE


def test_incomplete_fewer_positions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_passing_mq(tmp_path)
    write_cell(tmp_path, "continuous", "off", mq_rows("continuous", ids=IDS[:-1]))
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INCOMPLETE


def test_incomplete_fewer_repeats(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_passing_mq(tmp_path)
    write_cell(tmp_path, "continuous", "off", mq_rows("continuous", repeats=MQ_REPEATS - 1))
    rc, _ = run_mq(tmp_path, capsys)
    assert rc == EXIT_INCOMPLETE


def test_incomplete_never_prints_a_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run_mq(tmp_path, capsys)
    assert rc == EXIT_INCOMPLETE
    assert "d01=pass" not in out


# ==============================================================================
# Report-only fields never change pass/fail
# ==============================================================================


def test_report_only_fields_are_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_passing_mq(tmp_path)
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    report = [ln for ln in out.splitlines() if ln.startswith("MQ-REPORT off ")]
    assert len(report) == 1
    for key in (
        "bootstrap_lcb=",
        "k_unstable=",
        "unsigned_mean_abs_des=",
        "mcnemar_p=",
        "analysis_d=",
        "margin_flips=",
        "round_repeat_disagreement=",
    ):
        assert key in report[0], key


def test_report_only_inputs_cannot_change_the_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catastrophic analysis-selector values, a catastrophic Clear-Hash cell and
    a catastrophic analysis-400 cell leave d01/d03 untouched (D-02, D-20)."""
    write_passing_mq(tmp_path)
    _, base_out = run_mq(tmp_path, capsys)

    for stop in ("off", "on"):
        write_cell(
            tmp_path,
            "continuous",
            stop,
            mq_rows("continuous", stop=stop, es_analysis=lambda i, r: 0.0),
        )
        for arm_mode in ("round", "continuous"):
            write_cell(
                tmp_path,
                arm_mode,
                stop,
                mq_rows(
                    arm_mode,
                    stop=stop,
                    repeats=1,
                    hash_mode="clear",
                    es=lambda i, r, m=arm_mode: 0.0 if m == "continuous" else 0.5,
                ),
                base="gate/mq-clear",
            )
    for arm_mode in ("round", "continuous"):
        write_cell(
            tmp_path,
            arm_mode,
            "off",
            mq_rows(
                arm_mode,
                repeats=1,
                es=lambda i, r, m=arm_mode: 0.0 if m == "continuous" else 0.5,
            ),
            base="gate/mq-a400",
        )
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    for cell in ("off", "on"):
        before, after = cell_line(base_out, cell), cell_line(out, cell)
        assert before == after
        assert "d01=pass" in after and "d03=pass" in after
    assert any(ln.startswith("MQ-CLEAR off ") for ln in out.splitlines())
    assert any(ln.startswith("MQ-A400 off ") for ln in out.splitlines())


@pytest.mark.parametrize("empty_arms", [("round", "continuous"), ("continuous",), ("round",)])
def test_report_only_cell_with_an_empty_arm_is_unreadable_not_a_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], empty_arms: tuple[str, ...]
) -> None:
    """Review WR-01: a header-only TSV in a report-only cell used to escape as
    TypeError / ZeroDivisionError and abort the whole run."""
    write_passing_mq(tmp_path)
    for arm_mode in ("round", "continuous"):
        rows = [] if arm_mode in empty_arms else mq_rows(arm_mode, repeats=1, hash_mode="clear")
        write_cell(tmp_path, arm_mode, "off", rows, base="gate/mq-clear")
    rc, out = run_mq(tmp_path, capsys)
    assert rc == 0
    line = next(ln for ln in out.splitlines() if ln.startswith("MQ-CLEAR off "))
    assert "status=unreadable" in line
    assert "d01=pass" in cell_line(out, "off")


def test_report_only_k_and_flip_unit_reading() -> None:
    """Position 0 picks a different move in repeat 2 (K = 1) and that changed
    pick is worth 0.4 es: margin / flip size = 0.0252 / 0.4, i.e. 3.78 flips
    over 60 positions."""
    pid = IDS[0]
    result = evaluate_mq_cell(
        "off",
        mq_rows("round"),
        mq_rows(
            "continuous",
            move=lambda i, r: "g1f3" if (i == pid and r == 2) else "e2e4",
            es=lambda i, r: 0.1 if (i == pid and r == 2) else 0.5,
        ),
    )
    report = result["report"]
    assert report["k_unstable"] == 1
    assert report["flip_mean_size"] == pytest.approx(0.4)
    assert report["margin_flip_fraction"] == pytest.approx(MQ_SIGNED_MARGIN / 0.4)
    assert report["margin_flips"] == pytest.approx(MQ_SIGNED_MARGIN / 0.4 * len(IDS))


def test_report_only_analysis_selector_is_its_own_d() -> None:
    result = evaluate_mq_cell(
        "off",
        mq_rows("round"),
        mq_rows("continuous", es_analysis=lambda i, r: 0.2),
    )
    assert result["report"]["analysis_d"] == pytest.approx(-0.3)
    assert result["decision_d"] == pytest.approx(0.0)
    assert result["pass_d01"] is True


def test_report_only_bootstrap_is_seeded_and_reproducible() -> None:

    def lower(i: str, r: int) -> float:
        return 0.4 if i in IDS[:6] else 0.5

    a = evaluate_mq_cell("off", mq_rows("round"), mq_rows("continuous", es=lower))
    b = evaluate_mq_cell("off", mq_rows("round"), mq_rows("continuous", es=lower))
    assert a["report"]["bootstrap_lcb"] == b["report"]["bootstrap_lcb"]
    assert a["report"]["bootstrap_lcb"] <= a["decision_d"]


# ==============================================================================
# Tripwire — round mode against the committed 226 a21s data (D-11, D-18)
# ==============================================================================

BASELINE_HEADER = (
    "arm",
    "stop_rule",
    "id",
    "bot_move",
    "es_bot",
    "delta_bot",
    "verdict_bot",
    "analysis_move",
    "es_analysis",
    "nodes_evaluated",
    "stop_reason",
    "grade_depth",
)


def _baseline_rows(grade_depth: int = 18) -> list[dict[str, Any]]:
    rows = mq_rows("round", repeats=1, grade_depth=grade_depth)
    return [{k: v for k, v in row.items() if k in BASELINE_HEADER} for row in rows]


def _write_baseline(root: Path, rows_by_mode: dict[str, list[dict[str, Any]]]) -> Path:
    """226-shaped baseline: no dispatch_mode / repeat / hash_mode / maia_fifo."""
    for stop, rows in rows_by_mode.items():
        _write_tsv(
            root / f"mq-{stop}" / f"engine-move-quality-a21s-{stop}.tsv", BASELINE_HEADER, rows
        )
    return root


def _write_candidate(root: Path, rows_by_mode: dict[str, list[dict[str, Any]]]) -> Path:
    for stop, rows in rows_by_mode.items():
        _write_tsv(root / f"mq-{stop}" / f"engine-move-quality-x-{stop}.tsv", MQ_HEADER, rows)
    return root


def _tripwire(
    candidate: Path, baseline: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    rc = main(["tripwire", "--mq-dir", str(candidate), "--baseline-dir", str(baseline)])
    return rc, capsys.readouterr().out


def test_tripwire_identical_rows_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    cand = _write_candidate(
        tmp_path / "cand",
        {
            "off": mq_rows("round", repeats=1, grade_depth=18),
            "on": mq_rows("round", repeats=1, grade_depth=18, stop="on"),
        },
    )
    rc, out = _tripwire(cand, base, capsys)
    assert rc == 0
    assert "TRIPWIRE off rows=60 diffs=0" in out
    assert "TRIPWIRE on rows=60 diffs=0" in out
    assert out.strip().splitlines()[-1] == "TRIPWIRE PASS"


def test_tripwire_one_bot_move_diff_fails_and_lists_the_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    cand = _write_candidate(
        tmp_path / "cand",
        {
            "off": mq_rows("round", repeats=1, grade_depth=18),
            "on": mq_rows(
                "round",
                repeats=1,
                grade_depth=18,
                stop="on",
                move=lambda i, r: "h2h3" if i == IDS[7] else "e2e4",
            ),
        },
    )
    rc, out = _tripwire(cand, base, capsys)
    assert rc == EXIT_INVALID
    assert "TRIPWIRE on rows=60 diffs=1" in out
    assert IDS[7] in out
    assert "TRIPWIRE PASS" not in out


def test_tripwire_compares_es_only_at_equal_grade_depth(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same picks but different es_bot: a diff at equal grade_depth, ignored
    when the candidate graded at a different depth (d20 vs the d18 baseline)."""
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})

    def shifted(i: str, r: int) -> float:
        return 0.45

    same_depth = _write_candidate(
        tmp_path / "same",
        {
            "off": mq_rows("round", repeats=1, grade_depth=18, es=shifted),
            "on": mq_rows("round", repeats=1, grade_depth=18, stop="on", es=shifted),
        },
    )
    rc, _ = _tripwire(same_depth, base, capsys)
    assert rc == EXIT_INVALID
    other_depth = _write_candidate(
        tmp_path / "other",
        {
            "off": mq_rows("round", repeats=1, grade_depth=20, es=shifted),
            "on": mq_rows("round", repeats=1, grade_depth=20, stop="on", es=shifted),
        },
    )
    rc, out = _tripwire(other_depth, base, capsys)
    assert rc == 0
    assert "TRIPWIRE PASS" in out


def test_tripwire_every_repeat_must_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    cand = _write_candidate(
        tmp_path / "cand",
        {
            "off": mq_rows(
                "round",
                repeats=3,
                grade_depth=18,
                move=lambda i, r: "h2h3" if (i == IDS[1] and r == 3) else "e2e4",
            ),
            "on": mq_rows("round", repeats=3, grade_depth=18, stop="on"),
        },
    )
    rc, out = _tripwire(cand, base, capsys)
    assert rc == EXIT_INVALID
    assert "TRIPWIRE off rows=180 diffs=1" in out


def test_tripwire_requires_round_dispatch_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    cand = _write_candidate(
        tmp_path / "cand",
        {
            "off": mq_rows("continuous", repeats=1, grade_depth=18),
            "on": mq_rows("round", repeats=1, grade_depth=18, stop="on"),
        },
    )
    rc, _ = _tripwire(cand, base, capsys)
    assert rc == EXIT_INVALID


def test_tripwire_baseline_without_repeat_column_reads_as_repeat_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Self-comparison of a 226-shaped directory (no dispatch_mode, no repeat)."""
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    rc, out = _tripwire(base, base, capsys)
    assert rc == 0
    assert "TRIPWIRE PASS" in out


def test_tripwire_missing_directory_is_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_baseline(tmp_path / "base", {"off": _baseline_rows(), "on": _baseline_rows()})
    rc, out = _tripwire(tmp_path / "nothing-here", base, capsys)
    assert rc == EXIT_INCOMPLETE
    assert "TRIPWIRE PASS" not in out


@pytest.mark.skipif(not _BASELINE_A21S.is_dir(), reason="committed 226 a21s data not present")
def test_tripwire_committed_226_data_self_comparison(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The reader and comparison work on the real committed files."""
    rc = main(["tripwire", "--mq-dir", str(_BASELINE_A21S)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "TRIPWIRE off rows=60 diffs=0" in out
    assert "TRIPWIRE on rows=60 diffs=0" in out
    assert out.strip().splitlines()[-1] == "TRIPWIRE PASS"


def test_module_exposes_the_documented_surface() -> None:
    """Names later plans and the accept-rule pin test import."""
    for name in (
        "evaluate_tripwire",
        "evaluate_mq_cell",
        "mq_allowance",
        "d01_passes",
        "main",
    ):
        assert callable(getattr(twin, name)), name
    assert json.dumps(twin.ARM_MODE)  # JSON-serializable mapping


# ==============================================================================
# Task 2 — throughput (D-04 as amended by D-17), pool-2, WebGPU (D-07),
# calibration (D-15) and the composed `gates` verdict (D-08, D-00)
# ==============================================================================

ALL_CONFIGS = ("stop-p4", "t400-p4", "t50-p2", "t400-p2")
MANIFEST_HEADER = (
    "round",
    "step",
    "config",
    "arm",
    "dispatch_mode",
    "started_at",
    "finished_at",
    "load1",
    "probe_sf_ms",
    "probe_maia_ms",
    "probe_total_ms",
    "rc",
    "out_dir",
)
STOP_STEP_HEADER = (
    "position",
    "dispatch_mode",
    "wall_ms",
    "grade_cpu_ms",
    "maia_peak_inflight",
    "maia_fifo",
)
LADDER_STEP_HEADER = ("position", "depth", *STOP_STEP_HEADER[1:])
PASSING_RATIOS: dict[str, float | list[float]] = {
    "stop-p4": 0.80,
    "t400-p4": 0.97,
    "t50-p2": 1.0,
    "t400-p2": 1.0,
}
DEFAULT_A0_WALL_MS = 16000.0
DEFAULT_PROBE_MS = 1000.0
FLAT_DEPTH_DECOY_WALL_MS = 99999999


def write_throughput(
    data_dir: Path,
    ratios: dict[str, float | list[float]],
    *,
    rounds: int = 3,
    a0_walls: dict[str, list[float]] | None = None,
    step_overrides: dict[tuple[int, str, str], dict[str, Any]] | None = None,
) -> Path:
    """A manifest plus every step TSV. `ratios` is each config's a1/a0 wall
    ratio (a number or one per round); `step_overrides` keyed (round, config,
    arm) can replace wall_ms (total), probe_ms, load1, rc, tsv_mode (the TSV's
    own dispatch_mode), fifo, peak and positions."""
    root = data_dir / "gate" / "throughput"
    overrides = step_overrides or {}
    manifest: list[dict[str, Any]] = []
    for round_number in range(1, rounds + 1):
        for config, ratio in ratios.items():
            a0_wall = (a0_walls or {}).get(config, [DEFAULT_A0_WALL_MS] * rounds)[round_number - 1]
            round_ratio = ratio[round_number - 1] if isinstance(ratio, list) else ratio
            for arm, mode in (("a0", "round"), ("a1", "continuous")):
                ov = overrides.get((round_number, config, arm), {})
                wall = ov.get("wall_ms", a0_wall if arm == "a0" else a0_wall * round_ratio)
                probe = ov.get("probe_ms", DEFAULT_PROBE_MS)
                out_dir = f"r{round_number}/{config}/{arm}"
                n_rows = ov.get("positions", 16)
                rows = [
                    {
                        "position": f"p{i:02d}",
                        "depth": "ladder",
                        "dispatch_mode": ov.get("tsv_mode", mode),
                        "wall_ms": wall / n_rows,
                        "grade_cpu_ms": wall / n_rows / 2,
                        "maia_peak_inflight": ov.get("peak", "1"),
                        "maia_fifo": ov.get("fifo", "true"),
                    }
                    for i in range(n_rows)
                ]
                if config == "stop-p4":
                    _write_tsv(
                        root / out_dir / "engine-dispatch-stop-rule-x.tsv", STOP_STEP_HEADER, rows
                    )
                else:
                    # Flat-depth rows must be ignored: only `ladder` rows count.
                    flat = [
                        {**row, "depth": "14", "wall_ms": FLAT_DEPTH_DECOY_WALL_MS} for row in rows
                    ]
                    _write_tsv(
                        root / out_dir / "engine-grading-depth-ab-x.tsv",
                        LADDER_STEP_HEADER,
                        [*flat, *rows],
                    )
                manifest.append(
                    {
                        "round": round_number,
                        "step": len(manifest) + 1,
                        "config": config,
                        "arm": arm,
                        "dispatch_mode": mode,
                        "started_at": "2026-10-02T10:00:00Z",
                        "finished_at": "2026-10-02T10:10:00Z",
                        "load1": ov.get("load1", 0.5),
                        "probe_sf_ms": probe / 2,
                        "probe_maia_ms": probe / 2,
                        "probe_total_ms": probe,
                        "rc": ov.get("rc", 0),
                        "out_dir": out_dir,
                    }
                )
    _write_tsv(root / "manifest.tsv", MANIFEST_HEADER, manifest)
    return root / "manifest.tsv"


def run_cmd(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(argv)
    return rc, capsys.readouterr().out


def line_for(out: str, prefix: str) -> str:
    lines = [ln for ln in out.splitlines() if ln.startswith(prefix)]
    assert len(lines) == 1, (prefix, out)
    return lines[0]


# --- ship bar ---------------------------------------------------------------


def test_throughput_gain_20_percent_meets_the_ship_bar(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "stop-p4": 0.80})
    result = twin.evaluate_throughput(manifest)
    assert result["configs"]["stop-p4"]["gain"] == pytest.approx(0.20)
    assert result["ship_bar"]["gain_met"] is True
    assert result["ship_bar"]["no_regression"] is True
    assert result["ship_bar"]["passed"] is True


def test_throughput_gain_14_percent_misses_the_ship_bar(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "stop-p4": 0.86, "t400-p4": 1.0})
    result = twin.evaluate_throughput(manifest)
    assert result["configs"]["stop-p4"]["gain"] == pytest.approx(0.14)
    assert result["ship_bar"]["gain_met"] is False
    assert result["ship_bar"]["passed"] is False


def test_throughput_either_ship_bar_config_may_carry_the_gain(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "stop-p4": 1.0, "t400-p4": 0.80})
    assert twin.evaluate_throughput(manifest)["ship_bar"]["passed"] is True


def test_throughput_regression_on_t400_p4_fails_even_when_stop_p4_gains(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "stop-p4": 0.70, "t400-p4": 1.04})
    result = twin.evaluate_throughput(manifest)
    assert result["ship_bar"]["gain_met"] is True
    assert result["ship_bar"]["no_regression"] is False
    assert result["ship_bar"]["passed"] is False


def test_throughput_uses_the_geometric_mean_over_rounds(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "stop-p4": [0.5, 0.8, 1.0]})
    result = twin.evaluate_throughput(manifest)
    assert result["configs"]["stop-p4"]["geometric_mean"] == pytest.approx(0.4 ** (1 / 3))


def test_throughput_probe_normalization_cancels_machine_speed(tmp_path: Path) -> None:
    """Doubling BOTH wall and probe for one step (a slower machine for that
    step) leaves that round's ratio unchanged; a doubled wall alone doubles it."""
    base = write_throughput(tmp_path / "base", PASSING_RATIOS)
    slow = write_throughput(
        tmp_path / "slow",
        PASSING_RATIOS,
        step_overrides={
            (2, "stop-p4", "a1"): {"wall_ms": DEFAULT_A0_WALL_MS * 0.8 * 2, "probe_ms": 2000.0}
        },
    )
    base_ratios = twin.evaluate_throughput(base)["configs"]["stop-p4"]["ratios"]
    slow_ratios = twin.evaluate_throughput(slow)["configs"]["stop-p4"]["ratios"]
    assert slow_ratios == pytest.approx(base_ratios)
    unnormalized = write_throughput(
        tmp_path / "raw",
        PASSING_RATIOS,
        step_overrides={(2, "stop-p4", "a1"): {"wall_ms": DEFAULT_A0_WALL_MS * 0.8 * 2}},
    )
    raw_ratios = twin.evaluate_throughput(unnormalized)["configs"]["stop-p4"]["ratios"]
    assert raw_ratios[1] == pytest.approx(1.6)


def test_throughput_flat_depth_rows_are_ignored(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, PASSING_RATIOS)
    assert twin.evaluate_throughput(manifest)["configs"]["t400-p4"]["gain"] == pytest.approx(0.03)


def test_throughput_raw_and_grade_elapsed_ratios_are_report_only(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, PASSING_RATIOS)
    config = twin.evaluate_throughput(manifest)["configs"]["stop-p4"]
    assert config["raw_geometric_mean"] == pytest.approx(0.80)
    assert config["grade_geometric_mean"] is not None


def test_throughput_smoke_config_is_ignored(tmp_path: Path) -> None:
    manifest = write_throughput(tmp_path, {**PASSING_RATIOS, "smoke": 5.0})
    assert "smoke" not in twin.evaluate_throughput(manifest)["configs"]


def test_throughput_load_gate_breach_is_a_report_only_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_throughput(tmp_path, PASSING_RATIOS, step_overrides={(2, "t50-p2", "a1"): {"load1": 2.5}})
    rc, out = run_cmd(["throughput", "--data-dir", str(tmp_path)], capsys)
    assert rc == 0
    assert "t50-p2" in line_for(out, "LOAD-WARNING")


def test_throughput_incomplete_below_three_rounds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_throughput(tmp_path, PASSING_RATIOS, rounds=2)
    rc, _ = run_cmd(["throughput", "--data-dir", str(tmp_path)], capsys)
    assert rc == EXIT_INCOMPLETE


def test_throughput_incomplete_missing_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, _ = run_cmd(["throughput", "--data-dir", str(tmp_path)], capsys)
    assert rc == EXIT_INCOMPLETE


@pytest.mark.parametrize(
    "override",
    [
        {"tsv_mode": "round"},  # an a1 TSV that says round (mislabeled arm)
        {"fifo": "false"},
        {"peak": "2"},
        {"rc": 1},
        {"positions": 15},
    ],
    ids=["mislabeled-mode", "maia-fifo-off", "maia-peak-above-1", "nonzero-rc", "row-count"],
)
def test_throughput_invalid_step_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], override: dict[str, Any]
) -> None:
    write_throughput(tmp_path, PASSING_RATIOS, step_overrides={(2, "stop-p4", "a1"): override})
    rc, out = run_cmd(["throughput", "--data-dir", str(tmp_path)], capsys)
    assert rc == EXIT_INVALID
    assert "THROUGHPUT-BAR" not in out


def test_throughput_invalid_manifest_dispatch_mode_disagrees_with_arm(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = write_throughput(tmp_path, PASSING_RATIOS)
    text = manifest.read_text(encoding="utf-8")
    needle = "\ta1\tcontinuous\t"
    first_a1 = text.index(needle)
    manifest.write_text(
        text[:first_a1] + "\ta1\tround\t" + text[first_a1 + len(needle) :], encoding="utf-8"
    )
    rc, _ = run_cmd(["throughput", "--data-dir", str(tmp_path)], capsys)
    assert rc == EXIT_INVALID


# --- pool-2 -----------------------------------------------------------------


def _pool2_verdict(tmp_path: Path, ratio: float, a0_walls: list[float]) -> dict[str, Any]:
    manifest = write_throughput(
        tmp_path, {**PASSING_RATIOS, "t50-p2": ratio}, a0_walls={"t50-p2": a0_walls}
    )
    result = twin.evaluate_throughput(manifest)
    return dict(twin.evaluate_pool2(result["configs"])["t50-p2"])


def test_pool2_small_regression_inside_the_minimum_tolerance_passes(tmp_path: Path) -> None:
    verdict = _pool2_verdict(tmp_path, 1.02, [16000.0, 16160.0, 15840.0])
    assert verdict["noise"] == pytest.approx(0.01)
    assert verdict["tolerance"] == pytest.approx(1.03)
    assert verdict["passed"] is True


def test_pool2_regression_above_the_measured_noise_fails(tmp_path: Path) -> None:
    verdict = _pool2_verdict(tmp_path, 1.05, [16000.0, 16640.0, 15360.0])
    assert verdict["noise"] == pytest.approx(0.04)
    assert verdict["tolerance"] == pytest.approx(1.04)
    assert verdict["passed"] is False


def test_pool2_regression_inside_a_noisier_session_passes(tmp_path: Path) -> None:
    verdict = _pool2_verdict(tmp_path, 1.05, [16000.0, 16960.0, 15040.0])
    assert verdict["noise"] == pytest.approx(0.06)
    assert verdict["passed"] is True


def test_pool2_noise_is_judged_on_the_probe_normalized_a0_walls(tmp_path: Path) -> None:
    """A0 walls that differ only because the probe differs are not noise."""
    manifest = write_throughput(
        tmp_path,
        PASSING_RATIOS,
        a0_walls={"t50-p2": [16000.0, 32000.0, 16000.0]},
        step_overrides={
            (2, "t50-p2", "a0"): {"probe_ms": 2000.0},
            (2, "t50-p2", "a1"): {"probe_ms": 2000.0},
        },
    )
    result = twin.evaluate_throughput(manifest)
    assert twin.evaluate_pool2(result["configs"])["t50-p2"]["noise"] == pytest.approx(0.0)


# --- WebGPU -----------------------------------------------------------------

WEBGPU_POSITIONS = ["pos-a", "pos-b"]


def webgpu_payload(
    ratios: list[float],
    *,
    backend: str = "webgpu",
    observed: str | None = None,
    leg: str = "interleaved",
    schema: str = "engine-bench-227/v1",
) -> dict[str, Any]:
    bot_move: list[dict[str, Any]] = []
    for index, ratio in enumerate(ratios, start=1):
        for mode, factor in (("round", 1.0), ("continuous", ratio)):
            for pid in WEBGPU_POSITIONS:
                bot_move.append(
                    {
                        "round": index,
                        "mode": mode,
                        "modeObserved": observed or mode,
                        "positionId": pid,
                        "wallMs": 1000.0 * factor,
                        "nodes": 50,
                        "backend": backend,
                    }
                )
    return {
        "schema": schema,
        "leg": leg,
        "env": {"userAgent": "test"},
        "maiaLatency": [
            {
                "backend": "webgpu",
                "condition": "idle",
                "available": True,
                "n": 30,
                "medianMs": 15.0,
                "p90Ms": 18.0,
            }
        ],
        "botMove": bot_move,
    }


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_webgpu_median_ratio_102_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0, 1.02, 1.05]))
    rc, out = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == 0
    assert "pass" in line_for(out, "WEBGPU ")
    result = twin.evaluate_webgpu(path)
    assert result["median_ratio"] == pytest.approx(1.02)
    assert result["passed"] is True


def test_webgpu_median_ratio_104_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.04, 1.04, 1.04]))
    rc, out = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == 0
    assert "fail" in line_for(out, "WEBGPU ")


def test_webgpu_wasm_backend_row_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0, 1.0, 1.0], backend="wasm"))
    rc, _ = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == EXIT_INVALID


def test_webgpu_unobserved_mode_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0, 1.0, 1.0], observed="round"))
    rc, _ = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == EXIT_INVALID


def test_webgpu_schema_mismatch_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0] * 3, schema="engine-bench/v0"))
    rc, _ = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == EXIT_INVALID


def test_webgpu_fewer_than_three_rounds_is_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0, 1.0]))
    rc, _ = run_cmd(["webgpu", "--json", str(path)], capsys)
    assert rc == EXIT_INCOMPLETE


def test_webgpu_missing_file_is_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, _ = run_cmd(["webgpu", "--json", str(tmp_path / "absent.json")], capsys)
    assert rc == EXIT_INCOMPLETE


def test_webgpu_round_leg_is_not_a_judged_input(tmp_path: Path) -> None:
    path = write_json(tmp_path / "round.json", webgpu_payload([1.0] * 3, leg="round"))
    with pytest.raises(twin.InvalidDataError):
        twin.evaluate_webgpu(path)


def test_webgpu_maia_latency_table_is_reported(tmp_path: Path) -> None:
    path = write_json(tmp_path / "leg.json", webgpu_payload([1.0] * 3))
    table = twin.evaluate_webgpu(path)["maia_latency"]
    assert table[0]["backend"] == "webgpu"
    assert table[0]["medianMs"] == 15.0


# --- calibration ------------------------------------------------------------


def parity_payload(
    *, maia_shift: float = 0.0, sf_shift: float = 0.0, null_ok: bool = True
) -> dict[str, Any]:
    def family(pooled_shift: float) -> dict[str, Any]:
        return {
            "null_control": {
                "shift": 0.0,
                "se_shift": 1.0,
                "threshold": 999.0,
                "within_threshold": null_ok,
            },
            "pooled": {
                "shift": pooled_shift,
                "se": 10.0,
                "threshold": 999.0,
                "within_threshold": True,
                "n_cells": 4,
            },
            "exposed_cells": [],
        }

    return {
        "maia": family(maia_shift),
        "sf": family(sf_shift),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }


def test_calibration_real_shift_means_refit(tmp_path: Path) -> None:
    path = write_json(tmp_path / "v.json", parity_payload(maia_shift=100.0))
    result = twin.evaluate_calibration(path)
    assert result["refit_if_shipped"] == "refit"
    assert result["powered"]["maia"]["threshold"] == 85.0
    assert result["powered"]["sf"]["threshold"] == 53.542812708469995


def test_calibration_uses_the_frozen_sf_threshold(tmp_path: Path) -> None:
    """53.0 is inside 53.54, 54.0 is outside: the reducer reads the frozen value."""
    inside = write_json(tmp_path / "in.json", parity_payload(sf_shift=53.0))
    outside = write_json(tmp_path / "out.json", parity_payload(sf_shift=54.0))
    assert twin.evaluate_calibration(inside)["refit_if_shipped"] == "no-refit"
    assert twin.evaluate_calibration(outside)["refit_if_shipped"] == "refit"


def test_calibration_void_null_control_escalates(tmp_path: Path) -> None:
    path = write_json(tmp_path / "v.json", parity_payload(maia_shift=100.0, null_ok=False))
    assert twin.evaluate_calibration(path)["refit_if_shipped"] == "escalate"


def test_calibration_no_shift_means_no_refit(tmp_path: Path) -> None:
    path = write_json(tmp_path / "v.json", parity_payload())
    assert twin.evaluate_calibration(path)["refit_if_shipped"] == "no-refit"


def test_calibration_missing_file_is_incomplete(tmp_path: Path) -> None:
    with pytest.raises(twin.IncompleteDataError):
        twin.evaluate_calibration(tmp_path / "absent.json")


# --- gates ------------------------------------------------------------------


def write_full_layout(
    data_dir: Path,
    *,
    ratios: dict[str, float | list[float]] | None = None,
    webgpu_ratios: list[float] | None = None,
    parity: dict[str, Any] | None = None,
) -> None:
    write_passing_mq(data_dir)
    write_throughput(data_dir, ratios or PASSING_RATIOS)
    write_json(
        data_dir / "webgpu" / "continuous-leg.json", webgpu_payload(webgpu_ratios or [0.9] * 3)
    )
    write_json(
        data_dir / "gate" / "calibration" / "verdict-a1-vs-a0.json", parity or parity_payload()
    )


def run_gates_cli(
    data_dir: Path, out_json: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    return run_cmd(["gates", "--data-dir", str(data_dir), "--out-json", str(out_json)], capsys)


def load_verdict(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def test_gates_all_passing_is_ship_eligible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path)
    out_json = tmp_path / "out" / "verdict.json"
    rc, out = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "ship-eligible"
    assert verdict["reasons"] == []
    assert verdict["virtual_loss_trigger"] is False
    assert verdict["refit_if_shipped"] == "no-refit"
    assert "ship-eligible" in out


def test_gates_d03_failure_holds_and_triggers_virtual_loss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path)
    bad = set(IDS[:3])
    write_cell(
        tmp_path,
        "continuous",
        "on",
        mq_rows("continuous", stop="on", regress=lambda i, r: i in bad),
    )
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "hold"
    assert verdict["virtual_loss_trigger"] is True
    assert any("MQ on" in reason and "D-03" in reason for reason in verdict["reasons"])


def test_gates_throughput_miss_holds_without_a_virtual_loss_trigger(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path, ratios={**PASSING_RATIOS, "stop-p4": 1.0, "t400-p4": 1.0})
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "hold"
    assert verdict["virtual_loss_trigger"] is False
    assert any("ship bar" in reason for reason in verdict["reasons"])


def test_gates_pool2_regression_holds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_full_layout(tmp_path, ratios={**PASSING_RATIOS, "t400-p2": 1.2})
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "hold"
    assert any("t400-p2" in reason for reason in verdict["reasons"])


def test_gates_webgpu_slowdown_holds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_full_layout(tmp_path, webgpu_ratios=[1.1, 1.1, 1.1])
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "hold"
    assert any("WebGPU" in reason for reason in verdict["reasons"])


def test_gates_calibration_decides_the_refit_and_never_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path, parity=parity_payload(maia_shift=100.0))
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "ship-eligible"
    assert verdict["refit_if_shipped"] == "refit"


@pytest.mark.parametrize(
    "missing",
    [
        "webgpu/continuous-leg.json",
        "gate/calibration/verdict-a1-vs-a0.json",
        "gate/throughput/manifest.tsv",
    ],
)
def test_gates_missing_judged_input_is_incomplete_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    write_full_layout(tmp_path)
    (tmp_path / missing).unlink()
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == EXIT_INCOMPLETE
    assert not out_json.exists()


def test_gates_missing_mq_cell_is_incomplete_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path)
    for tsv in (tmp_path / "gate" / "mq" / "continuous" / "mq-on").glob("*.tsv"):
        tsv.unlink()
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == EXIT_INCOMPLETE
    assert not out_json.exists()


def test_gates_invalid_input_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_full_layout(tmp_path)
    write_json(
        tmp_path / "webgpu" / "continuous-leg.json", webgpu_payload([1.0] * 3, backend="wasm")
    )
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == EXIT_INVALID
    assert not out_json.exists()


def test_gates_empty_directory_is_incomplete_never_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run_cmd(["gates", "--data-dir", str(tmp_path / "empty")], capsys)
    assert rc == EXIT_INCOMPLETE
    assert "ship-eligible" not in out


def test_gates_report_only_round_leg_and_clear_hash_cannot_change_the_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A garbage round-leg JSON (report-only) and a catastrophic Clear-Hash MQ
    cell leave a ship-eligible verdict ship-eligible."""
    write_full_layout(tmp_path)
    write_json(tmp_path / "webgpu" / "round-leg.json", {"schema": "garbage"})
    for arm_mode in ("round", "continuous"):
        for stop in ("off", "on"):
            write_cell(
                tmp_path,
                arm_mode,
                stop,
                mq_rows(
                    arm_mode,
                    stop=stop,
                    repeats=1,
                    hash_mode="clear",
                    es=lambda i, r, m=arm_mode: 0.0 if m == "continuous" else 0.5,
                ),
                base="gate/mq-clear",
            )
    out_json = tmp_path / "verdict.json"
    rc, _ = run_gates_cli(tmp_path, out_json, capsys)
    assert rc == 0
    verdict = load_verdict(out_json)
    assert verdict["mechanical"] == "ship-eligible"
    assert verdict["mq"]["clear"]["off"]["status"] == "ok"
