#!/usr/bin/env python3
"""Interleaved throughput driver for the Phase 227 gate (D-04, D-17).

Why this exists: Phase 226's raw-wall throughput gate failed its underfill on
machine drift between runs (about +/-12% run to run on the dev box), and the
interleaved re-test driver that fixed the protocol was ad hoc and lost (only its
log is committed). D-17 judges the interleaved raw wall NORMALIZED BY an
external machine-speed probe, so the interleaving, the load gating and the probe
are committed tooling here, not orchestrator improvisation.

Protocol, per step: wait for a 1-minute load average below `LOAD_GATE_MAX`
(bounded wait, logged, never fatal), run `scripts/engine-speed-probe.mjs` (fixed
Stockfish node searches plus fixed Maia inferences, about 15 s), run the step's
pinned command, append one manifest row. Arms alternate and the config order
rotates every round, so drift hits both arms equally. At least `MIN_ROUNDS`
rounds are required for judged configs.

OPERATOR NOTES (orchestrator only; never launch this from an executor subagent)

  Launch from the orchestrator, from the repo root, with nothing else running:

      setsid nohup uv run python scripts/engine_interleave_227.py run \\
          --data-dir reports/data/continuous-dispatch-227/gate/throughput \\
          > <scratch>/interleave.log 2>&1 &

  then follow it with Monitor on the log (one `load=...` line before each step,
  one `done ... rc=...` line after). Do not run it in the foreground of a tool
  call (the Bash cap is 10 min and the session is hours) and never from a
  subagent (a backgrounded child dies when the agent returns).

  The box must stay idle for the whole session: no test suites, builds, sweeps
  or other agents. Stop the local `remote_eval_worker` first, and only with the
  user's permission. Expected duration is about 4.5-5.5 h for the default 3
  rounds (the two t400 configs dominate).

  To abort: SIGTERM the running NODE process (find it with `pgrep -f 'engine-(dispatch|grading)'`),
  NOT the Python driver. The driver records that step with its non-zero rc and
  stops (exit 1) instead of starting the next step. Relaunch the identical
  command with `--resume`: steps that already have an rc 0 row are skipped, and
  any failed row is moved out of `manifest.tsv` (into `manifest-failed.tsv`) so
  the verdict twin only ever sees clean rows.

  `--dry-run` prints the schedule and every argv without running anything (use
  it to check the order). `--configs smoke --rounds 1 --arms a0` runs the tooling
  self-check (a one-position stop-rule step); `smoke` rows are ignored by the
  verdict twin and `--rounds` below 3 is refused for every other config.
  `--load-wait-max-s` (default 600, the judged value) exists only so a smoke run
  on a busy box does not sit out the full gate; never lower it for a judged run.
  A `LOAD-GATE-TIMEOUT` line in the log means that step ran under load (the twin
  reports it as a warning); a judged session should have none.

Outputs under `--data-dir`: `manifest.tsv` (the column contract
`scripts/engine_dispatch_227_verdict.py` reads, appended per finished step),
`run-meta.json` (tooling commit, start time, schedule), step output directories
`r{round}/{config}/{arm}/`, and `logs/` (one log per step, one per probe, and
`driver.log`).

Usage:
  uv run python scripts/engine_interleave_227.py run --data-dir DIR
      [--rounds N] [--configs a,b] [--arms a0,a1] [--resume] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, NamedTuple, TypeIs

Config = Literal["stop-p4", "t400-p4", "t50-p2", "t400-p2", "smoke"]
Arm = Literal["a0", "a1"]
DispatchMode = Literal["round", "continuous"]

#: A0 is A21S in round mode, A1 is continuous mode (D-15).
ARM_MODE: dict[Arm, DispatchMode] = {"a0": "round", "a1": "continuous"}

#: The four judged throughput configs (D-04), in schedule order.
JUDGED_CONFIGS: tuple[Config, ...] = ("stop-p4", "t400-p4", "t50-p2", "t400-p2")
#: Tooling self-check config; never judged, never needs MIN_ROUNDS.
SMOKE_CONFIG: Config = "smoke"
ALL_CONFIGS: tuple[Config, ...] = (*JUDGED_CONFIGS, SMOKE_CONFIG)
DEFAULT_ARMS: tuple[Arm, ...] = ("a0", "a1")

#: Fewest rounds a judged session may run (D-17).
MIN_ROUNDS = 3
#: A step starts only below this 1-minute load average.
LOAD_GATE_MAX = 2.0
#: Seconds between load polls while waiting for the gate.
LOAD_POLL_S = 15
#: Longest a step waits for the gate before running anyway (logged, never fatal).
LOAD_WAIT_MAX_S = 600

#: The column contract `engine_dispatch_227_verdict._MANIFEST_COLUMNS` reads.
MANIFEST_COLUMNS: tuple[str, ...] = (
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

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADAVG_PATH = Path("/proc/loadavg")
MANIFEST_NAME = "manifest.tsv"
FAILED_MANIFEST_NAME = "manifest-failed.tsv"
RUN_META_NAME = "run-meta.json"
LOGS_DIR_NAME = "logs"
DRIVER_LOG_NAME = "driver.log"

EXIT_OK = 0
EXIT_STEP_FAILED = 1
EXIT_USAGE = 2

_NODE_PREFIX = ("node", "--import", "./scripts/lib/frontend-alias-hook.mjs")
_STOP_SCRIPT = "scripts/engine-dispatch-stop-rule.mjs"
_DEPTH_AB_SCRIPT = "scripts/engine-grading-depth-ab.mjs"
_PROBE_SCRIPT = "scripts/engine-speed-probe.mjs"
#: Common D-04 settings every config shares (16 positions, depth-8 tree, 1500 Elo).
_OPENINGS_JUDGED = "12"
_OPENINGS_SMOKE = "1"
_PLIES = "8"
_ELO = "1500"
_STOP_PROCS = "4"
_STOP_POOL = "4"
_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_PROBE_PATTERN = re.compile(
    r"^SPEED-PROBE sf_ms=([0-9]+(?:\.[0-9]+)?) maia_ms=([0-9]+(?:\.[0-9]+)?) "
    r"total_ms=([0-9]+(?:\.[0-9]+)?)$"
)


class DepthAbShape(NamedTuple):
    """Node budget, search concurrency and Stockfish pool size of a ladder-only config."""

    nodes: int
    procs: int
    pool_size: int


#: t400-p4 is the analysis path, t50-p2 is the bot-move budget over a 2-worker pool
#: (mobile-shaped), t400-p2 is analysis over a pool of 2 with concurrency 2 (226 D-04).
_DEPTH_AB_SHAPES: dict[str, DepthAbShape] = {
    "t400-p4": DepthAbShape(nodes=400, procs=4, pool_size=4),
    "t50-p2": DepthAbShape(nodes=50, procs=4, pool_size=2),
    "t400-p2": DepthAbShape(nodes=400, procs=2, pool_size=2),
}


class Step(NamedTuple):
    """One scheduled measurement: round (1-based), global step number (1-based), config, arm."""

    round: int
    step: int
    config: Config
    arm: Arm


class ProbeReading(NamedTuple):
    sf_ms: float
    maia_ms: float
    total_ms: float


class StepKey(NamedTuple):
    round: int
    config: str
    arm: str


def is_config(name: str) -> TypeIs[Config]:
    return name in ALL_CONFIGS


def is_arm(name: str) -> TypeIs[Arm]:
    return name in ARM_MODE


# ==============================================================================
# Pure pieces: schedule, argv, probe line, load gate, resume keys
# ==============================================================================


def build_schedule(rounds: int, configs: Sequence[Config], arms: Sequence[Arm]) -> list[Step]:
    """Ordered steps. In round r (1-based) the configs are rotated left by r - 1,
    and within each config the arms run in the given order for odd r and reversed
    for even r, so neither arm is systematically first or on the same side of a
    machine-speed drift."""
    steps: list[Step] = []
    for round_no in range(1, rounds + 1):
        shift = (round_no - 1) % len(configs)
        rotated = [*configs[shift:], *configs[:shift]]
        arm_order = list(arms) if round_no % 2 == 1 else list(reversed(arms))
        for config in rotated:
            for arm in arm_order:
                steps.append(Step(round_no, len(steps) + 1, config, arm))
    return steps


def step_out_dir(step: Step) -> str:
    """The step's output directory, relative to the data dir (what the manifest records)."""
    return f"r{step.round}/{step.config}/{step.arm}"


def build_command(config: Config, arm: Arm, out_dir: str) -> list[str]:
    """The exact argv for one step (D-04 pinned commands). `out_dir` is passed
    through verbatim as `--out-dir`."""
    mode = ARM_MODE[arm]
    if config in ("stop-p4", "smoke"):
        openings = _OPENINGS_SMOKE if config == "smoke" else _OPENINGS_JUDGED
        return [
            *_NODE_PREFIX,
            _STOP_SCRIPT,
            "--dispatch-mode",
            mode,
            "--procs",
            _STOP_PROCS,
            "--pool-size",
            _STOP_POOL,
            "--openings",
            openings,
            "--maia-fifo",
            "--out-dir",
            out_dir,
        ]
    shape = _DEPTH_AB_SHAPES[config]
    return [
        *_NODE_PREFIX,
        _DEPTH_AB_SCRIPT,
        "--dispatch-mode",
        mode,
        "--nodes",
        str(shape.nodes),
        "--ladder-only",
        "--procs",
        str(shape.procs),
        "--pool-size",
        str(shape.pool_size),
        "--plies",
        _PLIES,
        "--elo",
        _ELO,
        "--openings",
        _OPENINGS_JUDGED,
        "--maia-fifo",
        "--out-dir",
        out_dir,
    ]


def probe_command() -> list[str]:
    return [*_NODE_PREFIX, _PROBE_SCRIPT]


def parse_probe_line(text: str) -> ProbeReading:
    """Extract the three floats from the probe's single `SPEED-PROBE` line; raise
    ValueError when there is not exactly one well-formed line or a time is not positive."""
    matches = [m for line in text.splitlines() if (m := _PROBE_PATTERN.match(line.strip()))]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one SPEED-PROBE line, found {len(matches)}")
    sf_ms, maia_ms, total_ms = (float(g) for g in matches[0].groups())
    if min(sf_ms, maia_ms, total_ms) <= 0:
        raise ValueError("SPEED-PROBE times must be positive")
    return ProbeReading(sf_ms, maia_ms, total_ms)


def read_loadavg_1m() -> float:
    """First field of /proc/loadavg."""
    return float(LOADAVG_PATH.read_text(encoding="utf-8").split()[0])


def wait_for_load(
    read_load: Callable[[], float],
    sleep: Callable[[float], None],
    max_wait_s: float = LOAD_WAIT_MAX_S,
) -> tuple[float, bool]:
    """Poll the 1-minute load every `LOAD_POLL_S` until it is below `LOAD_GATE_MAX`
    or `max_wait_s` has elapsed. Returns the last reading and whether the wait timed
    out (the caller logs it; a timeout is never fatal)."""
    waited = 0.0
    load = read_load()
    while load >= LOAD_GATE_MAX:
        if waited >= max_wait_s:
            return load, True
        sleep(LOAD_POLL_S)
        waited += LOAD_POLL_S
        load = read_load()
    return load, False


def _read_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def completed_steps(manifest_path: Path) -> set[StepKey]:
    """(round, config, arm) of every manifest row that finished with rc 0."""
    return {
        StepKey(int(row["round"]), row["config"], row["arm"])
        for row in _read_manifest_rows(manifest_path)
        if row["rc"] == "0"
    }


def _write_rows(path: Path, rows: Sequence[dict[str, str]], append: bool) -> None:
    """Write `rows` under the contract header (header only when the file is new or empty)."""
    needs_header = not append or not path.is_file() or path.stat().st_size == 0
    with path.open("a" if append else "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, delimiter="\t")
        if needs_header:
            writer.writeheader()
        writer.writerows(rows)
        f.flush()


def append_manifest_row(path: Path, row: dict[str, str]) -> None:
    """Append one finished step (crash-safe: the file is flushed per row)."""
    _write_rows(path, [row], append=True)


def drop_failed_rows(manifest_path: Path, failed_path: Path) -> int:
    """On resume, move every non-rc-0 row out of the manifest (into `failed_path`) so
    the verdict twin only sees clean rows and the re-run does not collide as a
    duplicate. Returns how many rows were moved."""
    rows = _read_manifest_rows(manifest_path)
    failed = [row for row in rows if row["rc"] != "0"]
    if not failed:
        return 0
    _write_rows(failed_path, failed, append=True)
    _write_rows(manifest_path, [row for row in rows if row["rc"] == "0"], append=False)
    return len(failed)


# ==============================================================================
# Impure pieces, injectable for tests
# ==============================================================================


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _git_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _run_command_logged(argv: Sequence[str], log_path: Path) -> int:
    """Run `argv` from the repo root in the FOREGROUND with stdout and stderr to `log_path`."""
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(argv, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT)
    return completed.returncode


def _run_probe(log_path: Path) -> str:
    """Run the machine-speed probe; its full output goes to `log_path` and is returned."""
    completed = subprocess.run(
        probe_command(), cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"speed probe exited with rc {completed.returncode}")
    return completed.stdout


@dataclass
class Deps:
    """Everything with a side effect, so tests can drive the driver deterministically."""

    read_load: Callable[[], float] = read_loadavg_1m
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], datetime] = _utc_now
    git_sha: Callable[[], str] = _git_head_sha
    run_command: Callable[[Sequence[str], Path], int] = _run_command_logged
    run_probe: Callable[[Path], str] = _run_probe
    out: Callable[[str], None] = field(default=lambda line: print(line, flush=True))


# ==============================================================================
# The run
# ==============================================================================


@dataclass
class RunOptions:
    data_dir: Path
    rounds: int
    configs: list[Config]
    arms: list[Arm]
    resume: bool
    dry_run: bool
    load_wait_max_s: float


def _stamp(deps: Deps) -> str:
    return deps.now().strftime(_TS_FORMAT)


class _Logger:
    """Timestamped line log to the injected `out` and (when enabled) `driver.log`."""

    def __init__(self, deps: Deps, log_path: Path | None) -> None:
        self._deps = deps
        self._log_path = log_path

    def __call__(self, message: str) -> None:
        line = f"{_stamp(self._deps)} {message}"
        self._deps.out(line)
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


def _print_dry_run(options: RunOptions, schedule: Sequence[Step], deps: Deps) -> None:
    done = completed_steps(options.data_dir / MANIFEST_NAME) if options.resume else set()
    deps.out(f"DRY-RUN {len(schedule)} steps, probe: {' '.join(probe_command())}")
    for step in schedule:
        key = StepKey(step.round, step.config, step.arm)
        skip = "SKIP(rc 0 row) " if key in done else ""
        argv = build_command(step.config, step.arm, str(options.data_dir / step_out_dir(step)))
        deps.out(
            f"step {step.step:02d} r{step.round} {step.config} {step.arm} "
            f"mode={ARM_MODE[step.arm]}: {skip}{' '.join(argv)}"
        )


def _write_run_meta(options: RunOptions, schedule: Sequence[Step], deps: Deps) -> None:
    path = options.data_dir / RUN_META_NAME
    entry = {"at": _stamp(deps), "tooling_sha": deps.git_sha()}
    if options.resume and path.is_file():
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta.setdefault("resumes", []).append(entry)
    else:
        meta = {
            "tooling_sha": entry["tooling_sha"],
            "started_at": entry["at"],
            "rounds": options.rounds,
            "configs": options.configs,
            "arms": options.arms,
            "load_wait_max_s": options.load_wait_max_s,
            "schedule": [step._asdict() for step in schedule],
        }
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def run_step(step: Step, options: RunOptions, deps: Deps, log: _Logger) -> int:
    """Load gate, probe, pinned command, manifest row. Returns the command's rc;
    raises when the probe itself fails (no meaningful measurement to record)."""
    tag = f"r{step.round}-{step.config}-{step.arm}"
    logs_dir = options.data_dir / LOGS_DIR_NAME
    load, timed_out = wait_for_load(deps.read_load, deps.sleep, options.load_wait_max_s)
    note = " LOAD-GATE-TIMEOUT (running anyway)" if timed_out else ""
    log(f"load={load:.2f} step {step.step} {step.config} {step.arm} r{step.round}{note}")
    probe = parse_probe_line(deps.run_probe(logs_dir / f"{tag}.probe.log"))
    out_rel = step_out_dir(step)
    (options.data_dir / out_rel).mkdir(parents=True, exist_ok=True)
    started = _stamp(deps)
    rc = deps.run_command(
        build_command(step.config, step.arm, str(options.data_dir / out_rel)),
        logs_dir / f"{tag}.log",
    )
    row = {
        "round": str(step.round),
        "step": str(step.step),
        "config": step.config,
        "arm": step.arm,
        "dispatch_mode": ARM_MODE[step.arm],
        "started_at": started,
        "finished_at": _stamp(deps),
        "load1": f"{load:.2f}",
        "probe_sf_ms": f"{probe.sf_ms:.1f}",
        "probe_maia_ms": f"{probe.maia_ms:.1f}",
        "probe_total_ms": f"{probe.total_ms:.1f}",
        "rc": str(rc),
        "out_dir": out_rel,
    }
    append_manifest_row(options.data_dir / MANIFEST_NAME, row)
    log(f"done {step.config} {step.arm} r{step.round} rc={rc} probe_total_ms={probe.total_ms:.1f}")
    return rc


def run_session(options: RunOptions, deps: Deps) -> int:
    schedule = build_schedule(options.rounds, options.configs, options.arms)
    if options.dry_run:
        _print_dry_run(options, schedule, deps)
        return EXIT_OK
    manifest_path = options.data_dir / MANIFEST_NAME
    if not options.resume and _read_manifest_rows(manifest_path):
        deps.out(f"{manifest_path} already has rows: pass --resume to continue that session")
        return EXIT_USAGE
    (options.data_dir / LOGS_DIR_NAME).mkdir(parents=True, exist_ok=True)
    log = _Logger(deps, options.data_dir / LOGS_DIR_NAME / DRIVER_LOG_NAME)
    _write_run_meta(options, schedule, deps)
    moved = drop_failed_rows(manifest_path, options.data_dir / FAILED_MANIFEST_NAME)
    if moved:
        log(f"resume: moved {moved} failed row(s) to {FAILED_MANIFEST_NAME}")
    done = completed_steps(manifest_path)
    log(f"start {len(schedule)} steps, {len(done)} already complete")
    for step in schedule:
        if StepKey(step.round, step.config, step.arm) in done:
            continue
        if run_step(step, options, deps, log) != 0:
            log(f"STOPPED: step {step.step} failed; relaunch with --resume after fixing")
            return EXIT_STEP_FAILED
    log("finished")
    return EXIT_OK


# ==============================================================================
# CLI
# ==============================================================================


def _parse_configs(raw: str) -> list[Config]:
    configs: list[Config] = []
    for name in raw.split(","):
        if not is_config(name):
            raise argparse.ArgumentTypeError(f"unknown config {name!r}; choose from {ALL_CONFIGS}")
        configs.append(name)
    return configs


def _parse_arms(raw: str) -> list[Arm]:
    arms: list[Arm] = []
    for name in raw.split(","):
        if not is_arm(name):
            raise argparse.ArgumentTypeError(f"unknown arm {name!r}; choose from {tuple(ARM_MODE)}")
        arms.append(name)
    return arms


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 227 interleaved throughput driver (D-17).")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run (or dry-run) the interleaved session")
    run.add_argument("--data-dir", type=Path, required=True)
    run.add_argument("--rounds", type=int, default=MIN_ROUNDS)
    run.add_argument("--configs", type=_parse_configs, default=list(JUDGED_CONFIGS))
    run.add_argument("--arms", type=_parse_arms, default=list(DEFAULT_ARMS))
    run.add_argument("--resume", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument(
        "--load-wait-max-s",
        type=float,
        default=LOAD_WAIT_MAX_S,
        help="longest a step waits for the load gate (default is the judged value; "
        "lower it only for tooling smoke runs on a busy box)",
    )
    return parser


def _validate(options: RunOptions) -> str | None:
    """A usage error message, or None when the options are runnable."""
    smoke_only = options.configs == [SMOKE_CONFIG]
    if options.rounds < 1:
        return "--rounds must be at least 1"
    if options.rounds < MIN_ROUNDS and not smoke_only:
        return f"--rounds {options.rounds} refused: judged configs need at least {MIN_ROUNDS}"
    if len(set(options.configs)) != len(options.configs) or len(set(options.arms)) != len(
        options.arms
    ):
        return "--configs and --arms must not repeat a value"
    return None


def main(argv: Sequence[str] | None = None, deps: Deps | None = None) -> int:
    args = _build_parser().parse_args(argv)
    deps = deps or Deps()
    options = RunOptions(
        data_dir=args.data_dir.resolve(),
        rounds=args.rounds,
        configs=args.configs,
        arms=args.arms,
        resume=args.resume,
        dry_run=args.dry_run,
        load_wait_max_s=args.load_wait_max_s,
    )
    problem = _validate(options)
    if problem is not None:
        deps.out(problem)
        return EXIT_USAGE
    return run_session(options, deps)


if __name__ == "__main__":
    sys.exit(main())
