"""Tests for scripts/engine_interleave_227.py: the Phase 227 interleave driver (D-04, D-17).

Covers the pieces that decide whether a throughput session is trustworthy:
schedule rotation and arm alternation (drift hits both arms equally), the exact
pinned argv per config and arm, the speed-probe line parser, the bounded load
gate, resume (only rc 0 steps are skipped, failed rows never reach the verdict
twin), the manifest column contract the verdict twin reads, and dry-run.

Mutation check (recorded in 227-07-SUMMARY.md): disabling the even-round arm
reversal in `build_schedule` fails `test_schedule_arms_alternate_between_rounds`.
"""

from __future__ import annotations

import csv
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import scripts.engine_dispatch_227_verdict as twin  # noqa: E402
import scripts.engine_interleave_227 as drv  # noqa: E402
from scripts.engine_interleave_227 import (  # noqa: E402
    ARM_MODE,
    JUDGED_CONFIGS,
    LOAD_GATE_MAX,
    LOAD_POLL_S,
    LOAD_WAIT_MAX_S,
    MANIFEST_COLUMNS,
    MIN_ROUNDS,
    Deps,
    Step,
    build_command,
    build_schedule,
    completed_steps,
    main,
    parse_probe_line,
    wait_for_load,
)

_PROBE_OK = "SPEED-PROBE sf_ms=7500.0 maia_ms=5600.0 total_ms=13100.0\n"
_NODE_PREFIX = ["node", "--import", "./scripts/lib/frontend-alias-hook.mjs"]


# ==============================================================================
# Schedule
# ==============================================================================


def test_schedule_three_rounds_four_configs_has_24_steps() -> None:
    schedule = build_schedule(3, list(JUDGED_CONFIGS), ["a0", "a1"])
    assert len(schedule) == 24
    assert [s.step for s in schedule] == list(range(1, 25))
    assert {s.round for s in schedule} == {1, 2, 3}


def test_schedule_rotates_configs_left_each_round() -> None:
    schedule = build_schedule(3, list(JUDGED_CONFIGS), ["a0", "a1"])
    by_round = {
        r: [s.config for s in schedule if s.round == r and s.arm == "a0"] for r in (1, 2, 3)
    }
    assert by_round[1] == ["stop-p4", "t400-p4", "t50-p2", "t400-p2"]
    assert by_round[2] == ["t400-p4", "t50-p2", "t400-p2", "stop-p4"]
    assert by_round[3] == ["t50-p2", "t400-p2", "stop-p4", "t400-p4"]


def test_schedule_arms_alternate_between_rounds() -> None:
    schedule = build_schedule(3, list(JUDGED_CONFIGS), ["a0", "a1"])
    for config in JUDGED_CONFIGS:
        orders = {
            r: [s.arm for s in schedule if s.round == r and s.config == config] for r in (1, 2, 3)
        }
        assert orders[1] == ["a0", "a1"]
        assert orders[2] == ["a1", "a0"]
        assert orders[3] == ["a0", "a1"]


def test_schedule_every_config_arm_pair_runs_once_per_round() -> None:
    schedule = build_schedule(3, list(JUDGED_CONFIGS), ["a0", "a1"])
    keys = [(s.round, s.config, s.arm) for s in schedule]
    assert len(set(keys)) == len(keys) == 24


# ==============================================================================
# Pinned argv
# ==============================================================================


def test_build_command_stop_p4_both_arms() -> None:
    for arm, mode in (("a0", "round"), ("a1", "continuous")):
        assert build_command("stop-p4", arm, "OUT") == [
            *_NODE_PREFIX,
            "scripts/engine-dispatch-stop-rule.mjs",
            "--dispatch-mode",
            mode,
            "--procs",
            "4",
            "--pool-size",
            "4",
            "--openings",
            "12",
            "--maia-fifo",
            "--out-dir",
            "OUT",
        ]


def _depth_ab(mode: str, nodes: str, procs: str, pool: str) -> list[str]:
    return [
        *_NODE_PREFIX,
        "scripts/engine-grading-depth-ab.mjs",
        "--dispatch-mode",
        mode,
        "--nodes",
        nodes,
        "--ladder-only",
        "--procs",
        procs,
        "--pool-size",
        pool,
        "--plies",
        "8",
        "--elo",
        "1500",
        "--openings",
        "12",
        "--maia-fifo",
        "--out-dir",
        "OUT",
    ]


@pytest.mark.parametrize(
    ("config", "nodes", "procs", "pool"),
    [("t400-p4", "400", "4", "4"), ("t50-p2", "50", "4", "2"), ("t400-p2", "400", "2", "2")],
)
def test_build_command_depth_ab_configs_both_arms(
    config: str, nodes: str, procs: str, pool: str
) -> None:
    assert drv.is_config(config)
    assert build_command(config, "a0", "OUT") == _depth_ab("round", nodes, procs, pool)
    assert build_command(config, "a1", "OUT") == _depth_ab("continuous", nodes, procs, pool)


def test_build_command_smoke_is_stop_p4_with_one_opening() -> None:
    smoke = build_command("smoke", "a0", "OUT")
    stop = build_command("stop-p4", "a0", "OUT")
    assert smoke[smoke.index("--openings") + 1] == "1"
    assert [t for i, t in enumerate(smoke) if i != smoke.index("--openings") + 1] == [
        t for i, t in enumerate(stop) if i != stop.index("--openings") + 1
    ]


# ==============================================================================
# Probe line
# ==============================================================================


def test_parse_probe_line_good() -> None:
    reading = parse_probe_line("noise\n" + _PROBE_OK)
    assert (reading.sf_ms, reading.maia_ms, reading.total_ms) == (7500.0, 5600.0, 13100.0)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "no probe here\n",
        "SPEED-PROBE sf_ms=1 maia_ms=2\n",
        "SPEED-PROBE sf_ms=abc maia_ms=2 total_ms=3\n",
        "SPEED-PROBE sf_ms=0 maia_ms=2 total_ms=2\n",
        _PROBE_OK + _PROBE_OK,
    ],
)
def test_parse_probe_line_malformed_raises(text: str) -> None:
    with pytest.raises(ValueError):
        parse_probe_line(text)


# ==============================================================================
# Load gate
# ==============================================================================


def _reader(values: Sequence[float]) -> Callable[[], float]:
    iterator = iter(values)
    last = values[-1]

    def read() -> float:
        return next(iterator, last)

    return read


def test_load_gate_immediate_pass_never_sleeps() -> None:
    slept: list[float] = []
    load, timed_out = wait_for_load(_reader([0.5]), slept.append)
    assert (load, timed_out) == (0.5, False)
    assert slept == []


def test_load_gate_passes_after_polls() -> None:
    slept: list[float] = []
    load, timed_out = wait_for_load(_reader([3.0, 2.5, LOAD_GATE_MAX - 0.01]), slept.append)
    assert not timed_out
    assert load == LOAD_GATE_MAX - 0.01
    assert slept == [LOAD_POLL_S, LOAD_POLL_S]


def test_load_gate_boundary_is_exclusive() -> None:
    """A reading exactly at the gate does not pass (the gate is 'below')."""
    _, timed_out = wait_for_load(_reader([LOAD_GATE_MAX]), lambda _s: None, max_wait_s=LOAD_POLL_S)
    assert timed_out


def test_load_gate_timeout_returns_last_reading_and_flag() -> None:
    slept: list[float] = []
    load, timed_out = wait_for_load(_reader([4.0, 3.5, 3.0]), slept.append, max_wait_s=30)
    assert timed_out
    assert load == 3.0
    assert sum(slept) == 30


def test_load_gate_default_wait_bound_is_the_frozen_constant() -> None:
    slept: list[float] = []
    _, timed_out = wait_for_load(_reader([9.0]), slept.append)
    assert timed_out
    assert sum(slept) == LOAD_WAIT_MAX_S


# ==============================================================================
# Driver run with injected dependencies
# ==============================================================================


class _Clock:
    def __init__(self) -> None:
        self.seconds = 0

    def now(self) -> datetime:
        self.seconds += 1
        return datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC).replace(second=self.seconds % 60)


class _Fake:
    """Records every command the driver runs; rc per (config, arm) is configurable."""

    def __init__(self, rc_for: Callable[[str, str], int] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.probes = 0
        self.lines: list[str] = []
        self._rc_for = rc_for or (lambda _c, _a: 0)

    def deps(self) -> Deps:
        return Deps(
            read_load=lambda: 0.5,
            sleep=lambda _s: None,
            now=_Clock().now,
            git_sha=lambda: "deadbeef",
            run_command=self._run_command,
            run_probe=self._run_probe,
            out=self.lines.append,
        )

    def _run_command(self, argv: Sequence[str], log_path: Path) -> int:
        self.commands.append(list(argv))
        log_path.write_text("log\n", encoding="utf-8")
        mode = argv[argv.index("--dispatch-mode") + 1]
        config_arm = ("a0", "round") if mode == "round" else ("a1", "continuous")
        script = argv[len(_NODE_PREFIX)]
        config = "stop-p4" if "stop-rule" in script else "depth-ab"
        return self._rc_for(config, config_arm[0])

    def _run_probe(self, log_path: Path) -> str:
        self.probes += 1
        log_path.write_text(_PROBE_OK, encoding="utf-8")
        return _PROBE_OK


def _manifest(data_dir: Path) -> list[dict[str, str]]:
    with (data_dir / "manifest.tsv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def test_manifest_header_equals_the_verdict_twin_contract() -> None:
    assert MANIFEST_COLUMNS == twin._MANIFEST_COLUMNS
    assert set(JUDGED_CONFIGS) == set(twin._THROUGHPUT_CONFIGS)
    assert ARM_MODE == twin.ARM_MODE


def test_run_writes_one_contract_row_per_step_and_run_meta(tmp_path: Path) -> None:
    fake = _Fake()
    rc = main(
        ["run", "--data-dir", str(tmp_path), "--rounds", "3", "--configs", "stop-p4,t50-p2"],
        fake.deps(),
    )
    assert rc == 0
    rows = _manifest(tmp_path)
    assert len(rows) == 12
    with (tmp_path / "manifest.tsv").open(encoding="utf-8") as f:
        assert tuple(f.readline().rstrip("\n").split("\t")) == MANIFEST_COLUMNS
    first = rows[0]
    assert first["config"] == "stop-p4" and first["arm"] == "a0"
    assert first["dispatch_mode"] == "round" and first["rc"] == "0"
    assert first["load1"] == "0.50" and float(first["probe_total_ms"]) == 13100.0
    assert first["out_dir"] == "r1/stop-p4/a0"  # relative to the data dir
    assert (tmp_path / first["out_dir"]).is_dir()
    assert fake.probes == 12
    assert (tmp_path / "logs" / "r1-stop-p4-a0.log").is_file()
    assert (tmp_path / "logs" / "r1-stop-p4-a0.probe.log").is_file()
    meta = json.loads((tmp_path / "run-meta.json").read_text(encoding="utf-8"))
    assert meta["tooling_sha"] == "deadbeef"
    assert len(meta["schedule"]) == 12
    # The command saw the absolute step output dir under the data dir.
    assert fake.commands[0][-1] == str(tmp_path / "r1" / "stop-p4" / "a0")


def test_run_manifest_is_readable_by_the_verdict_twin(tmp_path: Path) -> None:
    fake = _Fake()
    main(["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"], fake.deps())
    rows = twin._read_manifest(tmp_path / "manifest.tsv")
    assert [r["config"] for r in rows] == ["smoke", "smoke"]


def test_run_refuses_to_clobber_an_existing_manifest_without_resume(tmp_path: Path) -> None:
    fake = _Fake()
    args = ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"]
    assert main(args, fake.deps()) == 0
    again = _Fake()
    assert main(args, again.deps()) == drv.EXIT_USAGE
    assert again.commands == []


def test_resume_skips_only_rc_zero_steps_and_drops_failed_rows(tmp_path: Path) -> None:
    args = ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"]
    first = _Fake(rc_for=lambda _c, arm: 143 if arm == "a1" else 0)
    assert main(args, first.deps()) == drv.EXIT_STEP_FAILED
    assert [r["rc"] for r in _manifest(tmp_path)] == ["0", "143"]
    assert completed_steps(tmp_path / "manifest.tsv") == {drv.StepKey(1, "smoke", "a0")}

    resumed = _Fake()
    assert main([*args, "--resume"], resumed.deps()) == 0
    assert len(resumed.commands) == 1  # only the failed a1 step re-ran
    assert resumed.commands[0][resumed.commands[0].index("--dispatch-mode") + 1] == "continuous"
    rows = _manifest(tmp_path)
    assert [(r["arm"], r["rc"]) for r in rows] == [("a0", "0"), ("a1", "0")]
    failed = tmp_path / "manifest-failed.tsv"
    assert failed.is_file() and "143" in failed.read_text(encoding="utf-8")
    meta = json.loads((tmp_path / "run-meta.json").read_text(encoding="utf-8"))
    assert len(meta["resumes"]) == 1


def test_failed_step_stops_the_session(tmp_path: Path) -> None:
    fake = _Fake(rc_for=lambda _c, _a: 1)
    rc = main(
        ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"], fake.deps()
    )
    assert rc == drv.EXIT_STEP_FAILED
    assert len(fake.commands) == 1  # did not start the next step


def test_load_timeout_is_logged_and_run_continues(tmp_path: Path) -> None:
    fake = _Fake()
    deps = fake.deps()
    deps.read_load = lambda: 5.0
    rc = main(
        [
            "run",
            "--data-dir",
            str(tmp_path),
            "--rounds",
            "1",
            "--configs",
            "smoke",
            "--arms",
            "a0",
            "--load-wait-max-s",
            "15",
        ],
        deps,
    )
    assert rc == 0
    assert any("LOAD-GATE-TIMEOUT" in line for line in fake.lines)
    assert _manifest(tmp_path)[0]["load1"] == "5.00"


# ==============================================================================
# Refusals and dry-run
# ==============================================================================


@pytest.mark.parametrize("rounds", ["1", "2"])
def test_rounds_below_minimum_refused_for_judged_configs(tmp_path: Path, rounds: str) -> None:
    fake = _Fake()
    assert main(["run", "--data-dir", str(tmp_path), "--rounds", rounds], fake.deps()) == 2
    assert fake.commands == [] and fake.probes == 0
    assert any(str(MIN_ROUNDS) in line for line in fake.lines)


def test_rounds_below_minimum_refused_when_smoke_is_mixed_in(tmp_path: Path) -> None:
    fake = _Fake()
    args = ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke,stop-p4"]
    assert main(args, fake.deps()) == 2


def test_smoke_alone_may_run_one_round(tmp_path: Path) -> None:
    fake = _Fake()
    args = ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"]
    assert main(args, fake.deps()) == 0


def test_unknown_config_and_arm_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["run", "--data-dir", str(tmp_path), "--configs", "bogus"], _Fake().deps())
    with pytest.raises(SystemExit):
        main(["run", "--data-dir", str(tmp_path), "--arms", "a2"], _Fake().deps())


def test_dry_run_prints_24_steps_and_runs_nothing(tmp_path: Path) -> None:
    fake = _Fake()
    assert main(["run", "--data-dir", str(tmp_path), "--dry-run"], fake.deps()) == 0
    assert fake.commands == [] and fake.probes == 0
    step_lines = [line for line in fake.lines if line.startswith("step ")]
    assert len(step_lines) == 24
    assert "mode=round" in step_lines[0] and "mode=continuous" in step_lines[1]
    # Round 2 reverses the arm order: first step of round 2 is the continuous arm.
    round2 = [line for line in step_lines if " r2 " in line]
    assert "mode=continuous" in round2[0]
    assert not (tmp_path / "manifest.tsv").exists()
    assert not (tmp_path / "run-meta.json").exists()


def test_dry_run_marks_steps_a_resume_would_skip(tmp_path: Path) -> None:
    args = ["run", "--data-dir", str(tmp_path), "--rounds", "1", "--configs", "smoke"]
    main(args, _Fake().deps())
    fake = _Fake()
    main([*args, "--resume", "--dry-run"], fake.deps())
    assert sum("SKIP(rc 0 row)" in line for line in fake.lines) == 2


def test_step_tuple_shape() -> None:
    step = Step(1, 1, "stop-p4", "a0")
    assert step._asdict() == {"round": 1, "step": 1, "config": "stop-p4", "arm": "a0"}
