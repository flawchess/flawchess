"""engine_throughput_226_verdict.py — Phase 226 gate verdict.

The machine-readable twin of `reports/engine-throughput-226/accept-rule.md`
(D-10, D-16): every threshold constant below carries the exact number from
`reports/engine-throughput-226/step0-protocol.md` and is NOT reachable from
any CLI flag, environment variable, or config file. The design-input
constants (section below) are now FROZEN (Plan 226-08, Task 2): each one was
set from this module's own `design-inputs` subcommand output over the
committed step-0 data, transcribed verbatim into
`reports/engine-throughput-226/design-inputs.md` and pinned by
`tests/scripts/test_engine_throughput_226_verdict.py::test_design_input_constants_match_committed_json`,
which reads the same committed
`reports/data/engine-throughput-226/step0/design-inputs.json` this module's
constants were transcribed from — never chosen by eye. The only legitimate
way to change a frozen constant is to edit this file, design-inputs.md and
the accept-rule doc together, before any gate arm runs.

Reads the pinned per-run data layout under `reports/data/engine-throughput-226/`
(`step0/` for the one-time step-0 re-measurement, `gate/{arm}/` for the
stacked-arm gate data — arm in `a2`, `a21`, `a21s`, `a21sc`; A0's own data
lives under `step0/`, never a `gate/a0/` directory) and renders every Phase
226 gate criterion mechanically. It never reports a pass on missing,
unconfirmed, or mislabeled data: a missing TSV, a duplicate TSV, an unrerun
move-quality flip, a missing required calibration file, or a throughput row
whose root-split-activity columns disagree with its arm (RESEARCH Pitfall 1,
D-08) all make `gates` exit non-zero rather than silently pass.

stdlib-only (`argparse`/`csv`/`json`/`math`/`statistics`/`pathlib`) — no
numpy/scipy, matching `calibration_anchor_fit.py`'s and
`calibration_parity_verdict.py`'s convention. Standalone research tool
(`scripts/`, not `app/`) — exempt from CLAUDE.md's Sentry-capture rules,
which apply only to `app/services` and `app/routers`.

Usage:
    uv run python scripts/engine_throughput_226_verdict.py gates \\
        --data-dir reports/data/engine-throughput-226 \\
        [--out-json reports/engine-throughput-226/verdict.json]

    uv run python scripts/engine_throughput_226_verdict.py design-inputs \\
        --data-dir reports/data/engine-throughput-226 \\
        [--out-json reports/data/engine-throughput-226/design-inputs.json]

    uv run python scripts/engine_throughput_226_verdict.py reruns \\
        --data-dir reports/data/engine-throughput-226

    uv run python scripts/engine_throughput_226_verdict.py cells-to-json \\
        --cells-tsv reports/data/engine-throughput-226/gate/a2-cells.tsv \\
        --out-json reports/data/engine-throughput-226/gate/calibration/a2-cells.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict, cast

import calibration_anchor_fit as anchor_fit
import engine_throughput_226_calibration as calib
from calibration_parity_verdict import Family, fit_new_cells
from engine_search_fixes_verdict import _ladder_rows, cells_to_payload, read_single_tsv

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# Frozen constants (D-10, D-16) — transcribed verbatim from
# reports/engine-throughput-226/step0-protocol.md. Fixed BEFORE any step-0 run
# existed; not editable after, and not reachable from any CLI flag,
# environment variable, or config file.
# ==============================================================================

Arm = Literal["a0", "a0a", "a0b", "a2", "a21", "a21s", "a21sc"]
StopMode = Literal["off", "on"]
ThroughputConfig = Literal["t50-p4", "t400-p4", "t50-p2", "t400-p2"]

#: step-0 item 9 — 50 games per (calibration cell, pinned anchor).
GAMES_PER_CELL_ANCHOR = 50
#: step-0 item 9 (D-19) — A0a on the supervisor default seed.
A0A_SEED = 1
#: step-0 item 9 (D-19) — A0b on `PRESET_SUPERVISOR_SEED=2`.
A0B_SEED = 2
#: Every gate arm's calibration cell runs on this seed.
ARM_SEED = 1
#: Base calibration thresholds (Phase 199/225, unchanged) — the floor
#: `null_check` (engine_throughput_226_calibration.py) compares against.
CALIBRATION_BASE_THRESHOLD: dict[Family, float] = {"maia": 85.0, "sf": 50.0}
#: 95% normal quantile — the se-multiplier `null_check` uses to derive a
#: powered per-family threshold from the A0a-vs-A0b null (D-10).
NULL_MODEL_SE_MULTIPLIER = 1.96
#: A null drift beyond this multiple of the base threshold escalates to the
#: user regardless of threshold inflation (D-10, section 3).
NULL_ESCALATION_FACTOR = 2.0
#: Z-based shape guard replacing the Phase 199 CI-overlap guard (D-10).
SHAPE_GUARD_Z = 1.96
#: No-regression bound with 5% idle-box wall noise (carried from Phase 225).
THROUGHPUT_MAX_WALL_RATIO = 1.05
#: D-16 §7 floor: `G = max(ROOT_SPLIT_MIN_GAIN, ROOT_SPLIT_GAIN_FRACTION * P)`.
ROOT_SPLIT_MIN_GAIN = 0.03
ROOT_SPLIT_GAIN_FRACTION = 0.5
#: D-16 §7: the warm content bound is this multiple of the warm noise floor.
CONTENT_WARM_MULTIPLIER = 1.5
#: D-16 §7: the Clear-Hash content bound is this multiple of the SAME warm
#: noise floor (the split may not move content further than the shipped warm
#: hash already does, even measured under Clear-Hash).
CONTENT_CLEAR_MULTIPLIER = 1.0
#: D-14/D-15 move-quality regression margin on the argmaxLine pick.
MQ_REGRESSION_MARGIN = 0.05
#: D-14 §4: `A = max(MQ_ALLOWANCE_FLOOR, d0)`.
MQ_ALLOWANCE_FLOOR = 1
#: D-13 amended S2 (carried from Phase 225): guard must not disable the
#: clear-winner branch below this fraction of A2's early-stop count.
STOP_RULE_MIN_EARLY_STOP_RETENTION = 0.5
#: `--guard-window` (Phase 225 D-02, unchanged).
GUARD_WINDOW = 0.09
#: D-17 §5: candidate-cap arm activation share.
D17_DOMINANCE_SHARE = 0.5
#: D-17 §5: "more than 8 candidates" bucket boundary.
D17_CANDIDATE_THRESHOLD = 8
#: D-17 §5: the cap value itself, non-root nodes only.
NON_ROOT_CANDIDATE_CAP = 8
#: The candidate cap's own throughput gain bar (t400-p4 ratio ceiling is
#: `1 - CANDIDATE_CAP_MIN_T400_GAIN`).
CANDIDATE_CAP_MIN_T400_GAIN = 0.03
#: SEED-126's 16 canonical positions (reused verbatim, carried from Phase 225).
EXPECTED_THROUGHPUT_POSITIONS = 16
EXPECTED_STOP_POSITIONS = 16
#: Phase 225's own `STOP_RULE_MAX_WALL_MS` — the expected value `design-inputs`
#: derives `STOP_RULE_MAX_WALL_MS` from, per step0-protocol.md section 7.
STOP_RULE_225_CEILING_MS = 12_100

DEFAULT_DATA_DIR = str(_REPO_ROOT / "reports" / "data" / "engine-throughput-226")
DEFAULT_VERDICT_JSON = str(_REPO_ROOT / "reports" / "engine-throughput-226" / "verdict.json")
FIXTURE_PATH = str(_REPO_ROOT / "fixtures" / "engine" / "move-quality-226.tsv")

#: `gates`/`design-inputs` return this on a root-split-column mismatch
#: (RESEARCH Pitfall 1, D-08) — a data-integrity violation, never a silent
#: pass, distinct from `EXIT_INCOMPLETE`'s "data not present yet".
EXIT_INVALID = 1
#: `gates`/`design-inputs` return this when any design-input constant is
#: unset, or any required file/directory is absent — status is `incomplete`,
#: never a silent pass on absent data.
EXIT_INCOMPLETE = 2

# ==============================================================================
# Design-input constants (D-16) — FROZEN (Plan 226-08, Task 2) from
# reports/data/engine-throughput-226/step0/design-inputs.json, computed by
# this module's OWN `design-inputs` subcommand over the committed step-0 data
# (tooling commit T = 27121e329 or later; fixture commit fc3086475), per the
# formulas in step0-protocol.md section 7 and transcribed verbatim into
# reports/engine-throughput-226/design-inputs.md. NEVER hand-chosen, and NEVER
# reachable from a CLI flag, environment variable, or config file. Pinned by
# tests/scripts/test_engine_throughput_226_verdict.py::test_design_input_constants_match_committed_json.
# `gates` still refuses to evaluate anything if any of these is `None` (D-10,
# D-16) — the type stays `X | None` so a future hand-edit that clears one back
# to `None` is caught by the same unset-constants gate, not by a type error.
# ==============================================================================

EXPECTED_MQ_POSITIONS: int | None = 60
MQ_ALLOWANCE_OFF: int | None = 1
MQ_ALLOWANCE_ON: int | None = 1
CALIBRATION_THRESHOLD_MAIA: float | None = 85.0
CALIBRATION_THRESHOLD_SF: float | None = 53.542812708469995
ROOT_SPLIT_MAX_T50_WALL_RATIO: float | None = 0.97
CONTENT_MAX_WARM_MEAN_ABS_DES: float | None = 0.02520619090909091
CONTENT_MAX_CLEAR_MEAN_ABS_DES: float | None = 0.016804127272727273
STOP_RULE_MAX_WALL_MS: float | None = 12100.0
CANDIDATE_CAP_ARM_ACTIVE: bool | None = False

#: Order matters only for the printed/`missing`-list message, not semantics.
_DESIGN_INPUT_NAMES: tuple[str, ...] = (
    "EXPECTED_MQ_POSITIONS",
    "MQ_ALLOWANCE_OFF",
    "MQ_ALLOWANCE_ON",
    "CALIBRATION_THRESHOLD_MAIA",
    "CALIBRATION_THRESHOLD_SF",
    "ROOT_SPLIT_MAX_T50_WALL_RATIO",
    "CONTENT_MAX_WARM_MEAN_ABS_DES",
    "CONTENT_MAX_CLEAR_MEAN_ABS_DES",
    "STOP_RULE_MAX_WALL_MS",
    "CANDIDATE_CAP_ARM_ACTIVE",
)


def _unset_design_inputs() -> list[str]:
    """The subset of `_DESIGN_INPUT_NAMES` still `None` on THIS module object
    (read via `sys.modules`, not a snapshot import, so a test's
    `monkeypatch.setattr(module, name, value)` is observed)."""
    module = sys.modules[__name__]
    return [name for name in _DESIGN_INPUT_NAMES if getattr(module, name) is None]


def _design_inputs_snapshot() -> dict[str, object]:
    module = sys.modules[__name__]
    return {name: getattr(module, name) for name in _DESIGN_INPUT_NAMES}


# ==============================================================================
# Data layout (Task 1 action) — relative paths under `--data-dir`.
# ==============================================================================

THROUGHPUT_CONFIGS: tuple[ThroughputConfig, ...] = ("t50-p4", "t400-p4", "t50-p2", "t400-p2")

#: Stacked gate arms in D-12 order (never includes "a0" — A0's own data lives
#: under `step0/`).
_GATE_ARMS: tuple[str, ...] = ("a2", "a21", "a21s", "a21sc")


def _step0_throughput_dir(data_dir: Path, config: str) -> Path:
    return data_dir / "step0" / "throughput" / config


def _throughput_dir(data_dir: Path, arm: str, config: str) -> Path:
    return data_dir / "gate" / arm / "throughput" / config


def _mq_dir(data_dir: Path, arm: str, mode: str) -> Path:
    return data_dir / "gate" / arm / f"mq-{mode}"


def _mq_rerun_dir(data_dir: Path, arm: str, mode: str) -> Path:
    return data_dir / "gate" / arm / f"mq-{mode}-rerun"


def _step0_mq_dir(data_dir: Path, pass_label: str, mode: str) -> Path:
    return data_dir / "step0" / "mq" / pass_label / f"mq-{mode}"


def _stop_dir(data_dir: Path, arm: str) -> Path:
    return data_dir / "gate" / arm / "stop"


def _content_dir(data_dir: Path, hash_mode: str) -> Path:
    return data_dir / "gate" / "a21s" / "content" / hash_mode


def _determinism_path(data_dir: Path) -> Path:
    return data_dir / "gate" / "a21s" / "determinism.txt"


def _warm_arm_dir(data_dir: Path, arm: str) -> Path:
    return data_dir / "gate" / arm / "warm-arm"


def _calibration_cells_path(data_dir: Path, arm: str) -> Path:
    return data_dir / "gate" / "calibration" / f"{arm}-cells.json"


def _calibration_verdict_path(data_dir: Path, label: str) -> Path:
    return data_dir / "gate" / "calibration" / f"verdict-{label}.json"


def _step0_calibration_path(data_dir: Path, name: str) -> Path:
    return data_dir / "step0" / "calibration" / name


def _step0_profile_path(data_dir: Path, budget: int, run: int) -> Path:
    return data_dir / "step0" / "profile" / f"profile-{budget}-run{run}.json"


def _step0_content_dir(data_dir: Path, hash_mode: str) -> Path:
    # Per-hash subdirectories, mirroring gate/a21s/content/{clear,warm}/: the
    # clear and warm runs each write their own TSV, and read_single_tsv needs
    # exactly one match per directory (a flat step0/content/ held two).
    return data_dir / "step0" / "content" / hash_mode


def _step0_stop_dir(data_dir: Path) -> Path:
    return data_dir / "step0" / "stop"


def _step0_trace_dir(data_dir: Path, label: str) -> Path:
    return data_dir / "step0" / "trace" / label


# ==============================================================================
# Throughput (all four configs, arm-vs-immediate-predecessor per D-12)
# ==============================================================================

_THROUGHPUT_TSV_PATTERN = "engine-grading-depth-ab-*.tsv"
_THROUGHPUT_REQUIRED_COLUMNS = (
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


class ThroughputPairResult(TypedDict):
    ratio: float
    positions: int
    admissible: bool
    base_wall_ms: float
    arm_wall_ms: float


class RootSplitDataError(ValueError):
    """Raised by `validate_root_split_columns` on a root-split-activity
    mismatch (RESEARCH Pitfall 1, D-08). Deliberately a `ValueError`
    subclass (the plan's stated contract) but NEVER caught as "missing
    data" — `main` maps it to `EXIT_INVALID`, distinct from
    `EXIT_INCOMPLETE`."""


#: Arms where the root-split code path is dormant — every ladder row must
#: show zero root-split calls (D-08: split code stays inert before A21S).
_PRE_SPLIT_ARMS: frozenset[str] = frozenset({"a0", "a0a", "a0b", "a2", "a21"})
#: Arms where the root split is active — every ladder row must show at
#: least one root-split call and zero premise violations (D-08: the
#: "whole pool idle at round 1" invariant held).
_SPLIT_ARMS: frozenset[str] = frozenset({"a21s", "a21sc"})


def validate_root_split_columns(arm: str, rows: Sequence[Mapping[str, str]]) -> None:
    """RESEARCH Pitfall 1 / D-08: an `a0`/`a0a`/`a0b`/`a2`/`a21` throughput row
    with ANY root-split call, or an `a21s`/`a21sc` row with ZERO root-split
    calls or any premise violation, means the data was mislabeled or the
    split fired when it should not have. Raises `RootSplitDataError` (a
    `ValueError`) rather than silently passing."""
    if arm in _PRE_SPLIT_ARMS:
        for row in rows:
            if int(row["root_split_calls"]) != 0:
                raise RootSplitDataError(
                    f"validate_root_split_columns: arm {arm!r} position {row.get('position')!r} "
                    f"has root_split_calls={row['root_split_calls']!r}, expected 0 (root split is "
                    "dormant before A21S, D-08)"
                )
    elif arm in _SPLIT_ARMS:
        for row in rows:
            if int(row["root_split_calls"]) < 1:
                raise RootSplitDataError(
                    f"validate_root_split_columns: arm {arm!r} position {row.get('position')!r} "
                    f"has root_split_calls={row['root_split_calls']!r}, expected >= 1 (root split "
                    "must fire for this arm)"
                )
            if int(row["root_split_premise_violations"]) != 0:
                raise RootSplitDataError(
                    f"validate_root_split_columns: arm {arm!r} position {row.get('position')!r} "
                    f"has root_split_premise_violations="
                    f"{row['root_split_premise_violations']!r}, expected 0 (D-08 whole-pool-idle "
                    "premise violated)"
                )
    else:
        raise RootSplitDataError(f"validate_root_split_columns: unknown arm {arm!r}")


def evaluate_throughput_pair(
    base_rows: Sequence[Mapping[str, str]],
    arm_rows: Sequence[Mapping[str, str]],
    max_ratio: float,
) -> ThroughputPairResult:
    """Ratio of ladder `wall_ms` sums (`arm` over `base`), with the 225
    validity rules: identical ladder position sets, exactly
    `EXPECTED_THROUGHPUT_POSITIONS` rows per side, and `maia_peak_inflight
    == "1"` / `maia_fifo == "true"` on every judged row."""
    base_ladder = _ladder_rows(base_rows)
    arm_ladder = _ladder_rows(arm_rows)
    for label, ladder in (("base", base_ladder), ("arm", arm_ladder)):
        if len(ladder) != EXPECTED_THROUGHPUT_POSITIONS:
            raise ValueError(
                f"evaluate_throughput_pair: expected {EXPECTED_THROUGHPUT_POSITIONS} ladder rows "
                f"for {label}, got {len(ladder)}"
            )
        for row in ladder:
            if row["maia_peak_inflight"] != "1" or row["maia_fifo"] != "true":
                raise ValueError(
                    f"evaluate_throughput_pair: inadmissible ladder row for {label} position "
                    f"{row['position']!r} (maia_peak_inflight={row['maia_peak_inflight']!r}, "
                    f"maia_fifo={row['maia_fifo']!r})"
                )
    base_by_pos = {row["position"]: row for row in base_ladder}
    arm_by_pos = {row["position"]: row for row in arm_ladder}
    if set(base_by_pos) != set(arm_by_pos):
        raise ValueError(
            f"evaluate_throughput_pair: position-label mismatch: base={sorted(base_by_pos)} "
            f"arm={sorted(arm_by_pos)}"
        )
    base_wall_ms = sum(float(row["wall_ms"]) for row in base_ladder)
    arm_wall_ms = sum(float(row["wall_ms"]) for row in arm_ladder)
    if base_wall_ms <= 0:
        raise ValueError("evaluate_throughput_pair: base ladder wall_ms sums to zero")
    ratio = arm_wall_ms / base_wall_ms
    return {
        "ratio": ratio,
        "positions": len(base_ladder),
        "admissible": ratio <= max_ratio,
        "base_wall_ms": base_wall_ms,
        "arm_wall_ms": arm_wall_ms,
    }


def _read_throughput_rows(data_dir: Path, arm: str, config: str) -> list[dict[str, str]]:
    """Reads one arm's throughput TSV for one config and validates its
    root-split columns. A `RootSplitDataError` is NEVER caught here — it
    must propagate uncaught to `main` (EXIT_INVALID). Any other `ValueError`
    (missing/duplicate file, missing column) is left for the caller to treat
    as "missing" (EXIT_INCOMPLETE)."""
    directory = _throughput_dir(data_dir, arm, config)
    rows = read_single_tsv(directory, _THROUGHPUT_TSV_PATTERN, _THROUGHPUT_REQUIRED_COLUMNS)
    try:
        validate_root_split_columns(arm, _ladder_rows(rows))
    except RootSplitDataError as exc:
        raise RootSplitDataError(f"{exc} (file(s) under {directory})") from exc
    return rows


def _read_step0_throughput_rows(data_dir: Path, config: str) -> list[dict[str, str]]:
    directory = _step0_throughput_dir(data_dir, config)
    rows = read_single_tsv(directory, _THROUGHPUT_TSV_PATTERN, _THROUGHPUT_REQUIRED_COLUMNS)
    try:
        validate_root_split_columns("a0", _ladder_rows(rows))
    except RootSplitDataError as exc:
        raise RootSplitDataError(f"{exc} (file(s) under {directory})") from exc
    return rows


# ==============================================================================
# Move quality (paired, RESEARCH Pitfall 8 rerun-confirmation rule, D-14/D-15)
# ==============================================================================

_MQ_TSV_PATTERN = "engine-move-quality-*.tsv"
_MQ_REQUIRED_COLUMNS = ("id", "delta_bot", "verdict_bot")


class MoveQualityPairResult(TypedDict):
    label: str
    status: Literal["evaluated", "rerun-required"]
    passed: bool | None
    net: int | None
    allowance: int
    pass_to_regression: list[str]
    regression_to_pass: list[str]
    reproduced_pass_to_regression: list[str]
    unconfirmed_pass_to_regression: list[str]
    rerun_required_ids: list[str]
    mcnemar_p: float | None


def _mq_regresses(row: Mapping[str, str]) -> bool:
    """A row regresses iff `delta_bot <= -MQ_REGRESSION_MARGIN` on the bot's
    own `argmaxLine` pick (D-14 section 4)."""
    return float(row["delta_bot"]) <= -MQ_REGRESSION_MARGIN


def _mq_rows_by_id(rows: Sequence[Mapping[str, str]], label: str) -> dict[str, Mapping[str, str]]:
    if EXPECTED_MQ_POSITIONS is None:
        raise ValueError("_mq_rows_by_id: EXPECTED_MQ_POSITIONS is unset (design input)")
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != EXPECTED_MQ_POSITIONS:
        raise ValueError(
            f"evaluate_move_quality_paired: expected {EXPECTED_MQ_POSITIONS} rows for {label}, "
            f"got {len(by_id)}"
        )
    return by_id


def _mcnemar_one_sided_p(b: int, c: int) -> float | None:
    """One-sided exact McNemar p-value on the discordant pair counts
    (pass-to-regression `b`, regression-to-pass `c`):
    `P(X <= min(b, c))` under `Binomial(b + c, 0.5)` — report-only, never a
    gate criterion (step0-protocol.md section 4)."""
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    total = 2**n
    cumulative = sum(math.comb(n, i) for i in range(k + 1))
    return cumulative / total


def evaluate_move_quality_paired(
    base_rows: Sequence[Mapping[str, str]],
    arm_rows: Sequence[Mapping[str, str]],
    rerun_rows: Sequence[Mapping[str, str]] | None,
    allowance: int,
    label: str,
) -> MoveQualityPairResult:
    """The paired MQ criterion (D-14 section 4): a pass-to-regression flip
    counts only if the rerun row for that id ALSO regresses (RESEARCH
    Pitfall 8); `net = counted pass-to-regression - regression-to-pass`;
    HOLD iff `net > allowance`."""
    base_by_id = _mq_rows_by_id(base_rows, f"{label} base")
    arm_by_id = _mq_rows_by_id(arm_rows, f"{label} arm")
    if set(base_by_id) != set(arm_by_id):
        raise ValueError(
            f"evaluate_move_quality_paired: {label} id-set mismatch: "
            f"base={sorted(base_by_id)} arm={sorted(arm_by_id)}"
        )
    base_regressed = {rid for rid, row in base_by_id.items() if _mq_regresses(row)}
    arm_regressed = {rid for rid, row in arm_by_id.items() if _mq_regresses(row)}
    pass_to_regression = sorted(arm_regressed - base_regressed)
    regression_to_pass = sorted(base_regressed - arm_regressed)

    if pass_to_regression and rerun_rows is None:
        return {
            "label": label,
            "status": "rerun-required",
            "passed": None,
            "net": None,
            "allowance": allowance,
            "pass_to_regression": pass_to_regression,
            "regression_to_pass": regression_to_pass,
            "reproduced_pass_to_regression": [],
            "unconfirmed_pass_to_regression": [],
            "rerun_required_ids": pass_to_regression,
            "mcnemar_p": None,
        }

    reproduced: list[str] = []
    unconfirmed: list[str] = []
    if pass_to_regression and rerun_rows is not None:
        rerun_by_id = {row["id"]: row for row in rerun_rows}
        for rid in pass_to_regression:
            rerun_row = rerun_by_id.get(rid)
            if rerun_row is None:
                raise ValueError(
                    f"evaluate_move_quality_paired: {label} rerun is missing flipped id {rid!r}"
                )
            if _mq_regresses(rerun_row):
                reproduced.append(rid)
            else:
                unconfirmed.append(rid)

    net = len(reproduced) - len(regression_to_pass)
    return {
        "label": label,
        "status": "evaluated",
        "passed": net <= allowance,
        "net": net,
        "allowance": allowance,
        "pass_to_regression": pass_to_regression,
        "regression_to_pass": regression_to_pass,
        "reproduced_pass_to_regression": sorted(reproduced),
        "unconfirmed_pass_to_regression": sorted(unconfirmed),
        "rerun_required_ids": [],
        "mcnemar_p": _mcnemar_one_sided_p(len(pass_to_regression), len(regression_to_pass)),
    }


class _MqPairSpec(TypedDict):
    label: str
    arm: str
    mode: str
    base_dir: Path
    arm_dir: Path
    rerun_dir: Path


def _mq_pair_specs(data_dir: Path) -> list[_MqPairSpec]:
    """The gate MQ pairs (D-12 stacked-arm attribution, mirroring the
    calibration verdict labels `a2-vs-a0a`/`a21-vs-a2`/`a21s-vs-a21`/
    `a21sc-vs-a21s`): A2 vs the step-0 A0a baseline (off only), A21 vs A2
    (on only), A21S vs A21 (both modes), A21SC vs A21S (both modes, only
    when the candidate cap is active)."""
    specs: list[_MqPairSpec] = [
        {
            "label": "a2-vs-a0a",
            "arm": "a2",
            "mode": "off",
            "base_dir": _step0_mq_dir(data_dir, "a0a", "off"),
            "arm_dir": _mq_dir(data_dir, "a2", "off"),
            "rerun_dir": _mq_rerun_dir(data_dir, "a2", "off"),
        },
        {
            "label": "a21-vs-a2",
            "arm": "a21",
            "mode": "on",
            "base_dir": _mq_dir(data_dir, "a2", "on"),
            "arm_dir": _mq_dir(data_dir, "a21", "on"),
            "rerun_dir": _mq_rerun_dir(data_dir, "a21", "on"),
        },
        {
            "label": "a21s-vs-a21",
            "arm": "a21s",
            "mode": "off",
            "base_dir": _mq_dir(data_dir, "a21", "off"),
            "arm_dir": _mq_dir(data_dir, "a21s", "off"),
            "rerun_dir": _mq_rerun_dir(data_dir, "a21s", "off"),
        },
        {
            "label": "a21s-vs-a21",
            "arm": "a21s",
            "mode": "on",
            "base_dir": _mq_dir(data_dir, "a21", "on"),
            "arm_dir": _mq_dir(data_dir, "a21s", "on"),
            "rerun_dir": _mq_rerun_dir(data_dir, "a21s", "on"),
        },
    ]
    if CANDIDATE_CAP_ARM_ACTIVE:
        specs.append(
            {
                "label": "a21sc-vs-a21s",
                "arm": "a21sc",
                "mode": "off",
                "base_dir": _mq_dir(data_dir, "a21s", "off"),
                "arm_dir": _mq_dir(data_dir, "a21sc", "off"),
                "rerun_dir": _mq_rerun_dir(data_dir, "a21sc", "off"),
            }
        )
        specs.append(
            {
                "label": "a21sc-vs-a21s",
                "arm": "a21sc",
                "mode": "on",
                "base_dir": _mq_dir(data_dir, "a21s", "on"),
                "arm_dir": _mq_dir(data_dir, "a21sc", "on"),
                "rerun_dir": _mq_rerun_dir(data_dir, "a21sc", "on"),
            }
        )
    return specs


def required_reruns(data_dir: Path) -> list[tuple[str, str]]:
    """The (arm, mode) pairs whose move-quality flips lack a rerun dir yet."""
    reruns: list[tuple[str, str]] = []
    for spec in _mq_pair_specs(data_dir):
        base_rows = read_single_tsv(spec["base_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
        arm_rows = read_single_tsv(spec["arm_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
        rerun_rows = None
        if spec["rerun_dir"].is_dir():
            rerun_rows = read_single_tsv(spec["rerun_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
        allowance = MQ_ALLOWANCE_OFF if spec["mode"] == "off" else MQ_ALLOWANCE_ON
        if allowance is None:
            raise ValueError(f"required_reruns: MQ allowance for mode {spec['mode']!r} is unset")
        result = evaluate_move_quality_paired(
            base_rows, arm_rows, rerun_rows, allowance, spec["label"]
        )
        if result["status"] == "rerun-required":
            reruns.append((spec["arm"], spec["mode"]))
    return reruns


# ==============================================================================
# Stop rule (S1 per-arm wall ceiling; S2 A21-vs-A2 early-stop retention)
# ==============================================================================

_STOP_TSV_PATTERN = "engine-dispatch-stop-rule-*.tsv"
_STOP_REQUIRED_COLUMNS = (
    "position",
    "stop_rule",
    "wall_ms",
    "stop_reason",
    "nodes_evaluated_at_stop",
    "exposure_snapshots",
    "eligible_snapshots",
)


class StopS1Result(TypedDict):
    arm: str
    max_wall_ms: float
    passed: bool


class StopS2Result(TypedDict):
    passed: bool
    trivial: bool
    a2_early_stops: int
    a21_early_stops: int


def evaluate_stop_rule_s1(rows: Sequence[Mapping[str, str]], arm: str) -> StopS1Result:
    if STOP_RULE_MAX_WALL_MS is None:
        raise ValueError("evaluate_stop_rule_s1: STOP_RULE_MAX_WALL_MS is unset (design input)")
    if len(rows) != EXPECTED_STOP_POSITIONS:
        raise ValueError(
            f"evaluate_stop_rule_s1: expected {EXPECTED_STOP_POSITIONS} rows for {arm}, "
            f"got {len(rows)}"
        )
    for row in rows:
        if row["stop_rule"] != "on":
            raise ValueError(
                f"evaluate_stop_rule_s1: {arm} row for position {row['position']!r} has "
                f"stop_rule={row['stop_rule']!r}, expected 'on'"
            )
    max_wall_ms = max(float(row["wall_ms"]) for row in rows)
    return {"arm": arm, "max_wall_ms": max_wall_ms, "passed": max_wall_ms <= STOP_RULE_MAX_WALL_MS}


def evaluate_stop_rule_s2(
    a2_rows: Sequence[Mapping[str, str]], a21_rows: Sequence[Mapping[str, str]]
) -> StopS2Result:
    for label, rows in (("a2", a2_rows), ("a21", a21_rows)):
        if len(rows) != EXPECTED_STOP_POSITIONS:
            raise ValueError(
                f"evaluate_stop_rule_s2: expected {EXPECTED_STOP_POSITIONS} rows for {label}, "
                f"got {len(rows)}"
            )
    a2_early = sum(1 for row in a2_rows if row["stop_reason"] == "early-stop")
    a21_early = sum(1 for row in a21_rows if row["stop_reason"] == "early-stop")
    trivial = a2_early == 0
    passed = True if trivial else a21_early >= STOP_RULE_MIN_EARLY_STOP_RETENTION * a2_early
    return {
        "passed": passed,
        "trivial": trivial,
        "a2_early_stops": a2_early,
        "a21_early_stops": a21_early,
    }


# ==============================================================================
# Root-split content bound (gate/a21s/content, split_source == "pool")
# ==============================================================================

# Must match the filename scripts/engine-root-split-content.mjs writes
# (`engine-root-split-content-{hash}-{source}-{stamp}.tsv`); the earlier
# "split-root-content-*" glob matched nothing the tool produced.
_CONTENT_TSV_PATTERN = "engine-root-split-content-*.tsv"
_CONTENT_REQUIRED_COLUMNS = (
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


class ContentResult(TypedDict):
    hash_mode: str
    mean_abs_des: float
    bound: float
    passed: bool
    root_argmax_flip_rate: float
    n_rows: int


def _candidate_weighted_mean(rows: Sequence[Mapping[str, str]], column: str) -> float:
    total_weight = sum(int(row["n_candidates"]) for row in rows)
    if total_weight <= 0:
        raise ValueError(
            f"_candidate_weighted_mean: total n_candidates is zero over {len(rows)} rows"
        )
    return sum(int(row["n_candidates"]) * float(row[column]) for row in rows) / total_weight


def evaluate_content(
    rows: Sequence[Mapping[str, str]], hash_mode: str, bound: float
) -> ContentResult:
    pool_rows = [row for row in rows if row["split_source"] == "pool"]
    if not pool_rows:
        raise ValueError(f"evaluate_content: no split_source=pool rows for hash_mode={hash_mode!r}")
    mean_abs_des = _candidate_weighted_mean(pool_rows, "mean_abs_des")
    flip_rate = sum(1 for row in pool_rows if row["root_argmax_flip"] == "true") / len(pool_rows)
    return {
        "hash_mode": hash_mode,
        "mean_abs_des": mean_abs_des,
        "bound": bound,
        "passed": mean_abs_des <= bound,
        "root_argmax_flip_rate": flip_rate,
        "n_rows": len(pool_rows),
    }


# ==============================================================================
# D-08 determinism check (gate/a21s/determinism.txt)
# ==============================================================================

_DETERMINISM_PASS_LINE = "PASS: calibration determinism"


def evaluate_determinism(text: str) -> bool:
    return _DETERMINISM_PASS_LINE in text


# ==============================================================================
# Item decisions (D-12, D-15, D-16, D-17 stacked-arm ship/hold rules)
# ==============================================================================


class ItemVerdict(TypedDict):
    outcome: Literal["ship", "hold"]
    reasons: list[str]


def _item_verdict(ok: bool, reason: str) -> ItemVerdict:
    return {"outcome": "ship" if ok else "hold", "reasons": [] if ok else [reason]}


def _mq_ok(result: MoveQualityPairResult | None) -> bool:
    return result is not None and result["passed"] is True


def decide_items(
    underfill_throughput_passed: bool | None,
    underfill_mq: MoveQualityPairResult | None,
    guard_s1: StopS1Result | None,
    guard_s2: StopS2Result | None,
    guard_mq: MoveQualityPairResult | None,
    root_split_determinism_passed: bool | None,
    root_split_t50_passed: bool | None,
    root_split_others_passed: bool | None,
    root_split_content_clear: ContentResult | None,
    root_split_content_warm: ContentResult | None,
    root_split_mq_off: MoveQualityPairResult | None,
    root_split_s1: StopS1Result | None,
    root_split_mq_on: MoveQualityPairResult | None,
    cap_t400_passed: bool | None,
    cap_t50_passed: bool | None,
    cap_mq_off: MoveQualityPairResult | None,
    cap_mq_on: MoveQualityPairResult | None,
) -> dict[str, ItemVerdict | None]:
    """D-12/D-15/D-16/D-17: underfill ships iff its own throughput+MQ pass;
    guard and root split both REQUIRE underfill to ship first (stacked
    arms — an underfill hold cascades to hold every downstream item); guard
    ships iff S1/S2/MQ(on) also pass; root split's OWN criteria (determinism,
    T-50 gain bar, the other three throughput configs, both content bounds,
    MQ off) are evaluated independent of the guard's ship status — when the
    guard SHIPS, S1@A21S and MQ(on)@A21S-vs-A21 additionally become
    decisive; when the guard is HELD, those two stay report-only and do not
    block the split. The candidate cap (when active) ships iff the root
    split ships and its own throughput+MQ criteria pass."""
    underfill_ok = bool(underfill_throughput_passed) and _mq_ok(underfill_mq)
    underfill = _item_verdict(
        underfill_ok, "underfill throughput or MQ criterion failed or is missing"
    )

    guard_ok = (
        underfill_ok
        and guard_s1 is not None
        and guard_s1["passed"]
        and guard_s2 is not None
        and guard_s2["passed"]
        and _mq_ok(guard_mq)
    )
    guard = _item_verdict(
        guard_ok, "guard S1/S2/MQ criterion failed or is missing, or underfill held"
    )

    split_own_ok = (
        underfill_ok
        and bool(root_split_determinism_passed)
        and bool(root_split_t50_passed)
        and bool(root_split_others_passed)
        and root_split_content_clear is not None
        and root_split_content_clear["passed"]
        and root_split_content_warm is not None
        and root_split_content_warm["passed"]
        and _mq_ok(root_split_mq_off)
    )
    if guard_ok:
        split_ok = (
            split_own_ok
            and root_split_s1 is not None
            and root_split_s1["passed"]
            and _mq_ok(root_split_mq_on)
        )
    else:
        split_ok = split_own_ok
    root_split = _item_verdict(
        split_ok, "root split criterion failed or is missing, or underfill held"
    )

    candidate_cap: ItemVerdict | None = None
    if CANDIDATE_CAP_ARM_ACTIVE:
        cap_ok = (
            split_ok
            and bool(cap_t400_passed)
            and bool(cap_t50_passed)
            and _mq_ok(cap_mq_off)
            and _mq_ok(cap_mq_on)
        )
        candidate_cap = _item_verdict(
            cap_ok, "candidate cap criterion failed or is missing, or root split held"
        )

    return {
        "underfill": underfill,
        "guard": guard,
        "root_split": root_split,
        "candidate_cap": candidate_cap,
    }


# ==============================================================================
# gates subcommand
# ==============================================================================

GateStatus = Literal["complete", "incomplete"]


class GateVerdict(TypedDict):
    status: GateStatus
    missing: list[str]
    rerun_required: list[str]
    design_inputs: dict[str, object]
    criteria: dict[str, object]
    items: dict[str, object] | None
    refit: dict[str, object] | None


def _throughput_pair_or_none(
    data_dir: Path,
    base_arm: str,
    arm_arm: str,
    config: str,
    bound: float | None,
    read_soft: Callable[..., list[dict[str, str]] | None],
    missing: list[str],
) -> ThroughputPairResult | None:
    """One arm-vs-predecessor throughput comparison, soft-skipped (`None`,
    no `missing` entry) when either side's directory is absent or `bound`
    itself is unset — keeps `run_gates`'s per-config loops at nesting depth
    <= 4 (CLAUDE.md)."""
    if bound is None:
        return None
    if not (
        _throughput_dir(data_dir, base_arm, config).is_dir()
        and _throughput_dir(data_dir, arm_arm, config).is_dir()
    ):
        return None
    base_rows = read_soft(_read_throughput_rows, data_dir, base_arm, config)
    arm_rows = read_soft(_read_throughput_rows, data_dir, arm_arm, config)
    if base_rows is None or arm_rows is None:
        return None
    try:
        return evaluate_throughput_pair(base_rows, arm_rows, bound)
    except ValueError as exc:
        missing.append(str(exc))
        return None


def run_gates(data_dir: Path) -> GateVerdict:
    missing: list[str] = []
    rerun_required: list[str] = []

    def read_soft(
        reader: Callable[..., list[dict[str, str]]], *args: object
    ) -> list[dict[str, str]] | None:
        try:
            return reader(*args)
        except RootSplitDataError:
            raise
        except ValueError as exc:
            missing.append(str(exc))
            return None

    # ---- underfill throughput (A2 vs the step-0 A0 baseline) ----
    underfill_configs: dict[str, ThroughputPairResult | None] = {}
    for config in THROUGHPUT_CONFIGS:
        base_rows = read_soft(_read_step0_throughput_rows, data_dir, config)
        arm_rows = read_soft(_read_throughput_rows, data_dir, "a2", config)
        result: ThroughputPairResult | None = None
        if base_rows is not None and arm_rows is not None:
            try:
                result = evaluate_throughput_pair(base_rows, arm_rows, THROUGHPUT_MAX_WALL_RATIO)
            except ValueError as exc:
                missing.append(str(exc))
        underfill_configs[config] = result
    underfill_throughput_passed: bool | None = None
    if all(result is not None for result in underfill_configs.values()):
        underfill_throughput_passed = all(
            cast(ThroughputPairResult, result)["admissible"]
            for result in underfill_configs.values()
        )

    # Data-integrity validation for every OTHER stacked arm's throughput data
    # that happens to be present (RootSplitDataError must surface regardless
    # of which criteria consume that arm's data).
    for arm in _GATE_ARMS:
        if arm == "a2":
            continue  # already read above
        for config in THROUGHPUT_CONFIGS:
            if _throughput_dir(data_dir, arm, config).is_dir():
                read_soft(_read_throughput_rows, data_dir, arm, config)

    # ---- move quality (paired, per D-12 stacked-arm attribution) ----
    mq_results: dict[str, MoveQualityPairResult | None] = {}
    for spec in _mq_pair_specs(data_dir):
        key = f"{spec['label']}:{spec['mode']}"
        if not spec["base_dir"].is_dir() or not spec["arm_dir"].is_dir():
            mq_results[key] = None
            continue
        base_rows = read_soft(
            read_single_tsv, spec["base_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
        )
        arm_rows = read_soft(
            read_single_tsv, spec["arm_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
        )
        rerun_rows = None
        if spec["rerun_dir"].is_dir():
            rerun_rows = read_soft(
                read_single_tsv, spec["rerun_dir"], _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
            )
        result: MoveQualityPairResult | None = None
        if base_rows is not None and arm_rows is not None:
            allowance = MQ_ALLOWANCE_OFF if spec["mode"] == "off" else MQ_ALLOWANCE_ON
            try:
                result = evaluate_move_quality_paired(
                    base_rows, arm_rows, rerun_rows, cast(int, allowance), spec["label"]
                )
            except ValueError as exc:
                missing.append(str(exc))
        if result is not None and result["status"] == "rerun-required":
            rerun_required.append(f"{spec['arm']} {spec['mode']}")
        mq_results[key] = result

    underfill_mq = mq_results.get("a2-vs-a0a:off")
    guard_mq = mq_results.get("a21-vs-a2:on")
    root_split_mq_off = mq_results.get("a21s-vs-a21:off")
    root_split_mq_on = mq_results.get("a21s-vs-a21:on")
    cap_mq_off = mq_results.get("a21sc-vs-a21s:off")
    cap_mq_on = mq_results.get("a21sc-vs-a21s:on")

    # ---- stop rule (S1 per-arm, S2 A21-vs-A2) ----
    guard_s1: StopS1Result | None = None
    a21_stop_dir = _stop_dir(data_dir, "a21")
    if a21_stop_dir.is_dir():
        rows = read_soft(read_single_tsv, a21_stop_dir, _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
        if rows is not None:
            try:
                guard_s1 = evaluate_stop_rule_s1(rows, "a21")
            except ValueError as exc:
                missing.append(str(exc))

    guard_s2: StopS2Result | None = None
    a2_stop_dir = _stop_dir(data_dir, "a2")
    if a2_stop_dir.is_dir() and a21_stop_dir.is_dir():
        a2_stop_rows = read_soft(
            read_single_tsv, a2_stop_dir, _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS
        )
        a21_stop_rows = read_soft(
            read_single_tsv, a21_stop_dir, _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS
        )
        if a2_stop_rows is not None and a21_stop_rows is not None:
            try:
                guard_s2 = evaluate_stop_rule_s2(a2_stop_rows, a21_stop_rows)
            except ValueError as exc:
                missing.append(str(exc))

    root_split_s1: StopS1Result | None = None
    a21s_stop_dir = _stop_dir(data_dir, "a21s")
    if a21s_stop_dir.is_dir():
        rows = read_soft(read_single_tsv, a21s_stop_dir, _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
        if rows is not None:
            try:
                root_split_s1 = evaluate_stop_rule_s1(rows, "a21s")
            except ValueError as exc:
                missing.append(str(exc))

    # ---- D-08 determinism ----
    root_split_determinism_passed: bool | None = None
    determinism_path = _determinism_path(data_dir)
    if determinism_path.is_file():
        root_split_determinism_passed = evaluate_determinism(
            determinism_path.read_text(encoding="utf-8")
        )

    # ---- root-split content bound ----
    content_clear: ContentResult | None = None
    content_warm: ContentResult | None = None
    if CONTENT_MAX_CLEAR_MEAN_ABS_DES is not None:
        clear_dir = _content_dir(data_dir, "clear")
        if clear_dir.is_dir():
            rows = read_soft(
                read_single_tsv, clear_dir, _CONTENT_TSV_PATTERN, _CONTENT_REQUIRED_COLUMNS
            )
            if rows is not None:
                try:
                    content_clear = evaluate_content(rows, "clear", CONTENT_MAX_CLEAR_MEAN_ABS_DES)
                except ValueError as exc:
                    missing.append(str(exc))
    if CONTENT_MAX_WARM_MEAN_ABS_DES is not None:
        warm_dir = _content_dir(data_dir, "warm")
        if warm_dir.is_dir():
            rows = read_soft(
                read_single_tsv, warm_dir, _CONTENT_TSV_PATTERN, _CONTENT_REQUIRED_COLUMNS
            )
            if rows is not None:
                try:
                    content_warm = evaluate_content(rows, "warm", CONTENT_MAX_WARM_MEAN_ABS_DES)
                except ValueError as exc:
                    missing.append(str(exc))

    # ---- root-split throughput (A21S vs gate A21) ----
    root_split_configs: dict[str, ThroughputPairResult | None] = {}
    for config in THROUGHPUT_CONFIGS:
        bound = ROOT_SPLIT_MAX_T50_WALL_RATIO if config == "t50-p4" else THROUGHPUT_MAX_WALL_RATIO
        root_split_configs[config] = _throughput_pair_or_none(
            data_dir, "a21", "a21s", config, bound, read_soft, missing
        )
    root_split_t50 = root_split_configs.get("t50-p4")
    root_split_t50_passed = root_split_t50["admissible"] if root_split_t50 is not None else None
    _other_split_results = [
        root_split_configs.get(config) for config in THROUGHPUT_CONFIGS if config != "t50-p4"
    ]
    root_split_others_passed = (
        all(cast(ThroughputPairResult, r)["admissible"] for r in _other_split_results)
        if all(r is not None for r in _other_split_results)
        else None
    )

    # ---- candidate-cap throughput (A21SC vs gate A21S, only when active) ----
    cap_configs: dict[str, ThroughputPairResult | None] = {}
    cap_t400_passed: bool | None = None
    cap_t50_passed: bool | None = None
    if CANDIDATE_CAP_ARM_ACTIVE:
        for config in ("t400-p4", "t50-p4"):
            bound = (
                (1.0 - CANDIDATE_CAP_MIN_T400_GAIN)
                if config == "t400-p4"
                else THROUGHPUT_MAX_WALL_RATIO
            )
            cap_configs[config] = _throughput_pair_or_none(
                data_dir, "a21s", "a21sc", config, bound, read_soft, missing
            )
        cap_t400 = cap_configs.get("t400-p4")
        cap_t400_passed = cap_t400["admissible"] if cap_t400 is not None else None
        cap_t50 = cap_configs.get("t50-p4")
        cap_t50_passed = cap_t50["admissible"] if cap_t50 is not None else None

    # ---- item decisions ----
    items = decide_items(
        underfill_throughput_passed,
        underfill_mq,
        guard_s1,
        guard_s2,
        guard_mq,
        root_split_determinism_passed,
        root_split_t50_passed,
        root_split_others_passed,
        content_clear,
        content_warm,
        root_split_mq_off,
        root_split_s1,
        root_split_mq_on,
        cap_t400_passed,
        cap_t50_passed,
        cap_mq_off,
        cap_mq_on,
    )

    # ---- calibration (D-10) and the shipped-items-only refit decision (D-11) ----
    calibration_labels: dict[calib.Item, str] = {
        "underfill": "a2-vs-a0a",
        "guard": "a21-vs-a2",
        "root_split": "a21s-vs-a21",
    }
    if CANDIDATE_CAP_ARM_ACTIVE:
        calibration_labels["candidate_cap"] = "a21sc-vs-a21s"

    powered_verdicts: dict[calib.Item, calib.PoweredVerdict] = {}
    if CALIBRATION_THRESHOLD_MAIA is not None and CALIBRATION_THRESHOLD_SF is not None:
        thresholds: dict[Family, float] = {
            "maia": CALIBRATION_THRESHOLD_MAIA,
            "sf": CALIBRATION_THRESHOLD_SF,
        }
        for item_name, label in calibration_labels.items():
            verdict_path = _calibration_verdict_path(data_dir, label)
            if not verdict_path.is_file():
                continue
            try:
                parity = calib.load_parity_verdict(verdict_path)
            except ValueError as exc:
                missing.append(str(exc))
                continue
            powered_verdicts[item_name] = calib.powered_verdict(
                label, parity, thresholds, SHAPE_GUARD_Z
            )

    shipped: dict[calib.Item, bool] = {
        cast(calib.Item, name): (verdict["outcome"] == "ship")
        for name, verdict in items.items()
        if verdict is not None
    }
    refit: calib.RefitDecision | None = None
    if shipped:
        refit = calib.refit_decision(powered_verdicts, shipped)

    criteria: dict[str, object] = {
        "underfill_throughput": {
            "configs": underfill_configs,
            "passed": underfill_throughput_passed,
        },
        "underfill_mq": underfill_mq,
        "guard_s1": guard_s1,
        "guard_s2": guard_s2,
        "guard_mq": guard_mq,
        "root_split_determinism": (
            {"passed": root_split_determinism_passed}
            if root_split_determinism_passed is not None
            else None
        ),
        "root_split_throughput": {
            "configs": root_split_configs,
            "t50_passed": root_split_t50_passed,
            "others_passed": root_split_others_passed,
        },
        "root_split_content": {"clear": content_clear, "warm": content_warm},
        "root_split_mq": {"off": root_split_mq_off, "on": root_split_mq_on},
        "candidate_cap_throughput": (
            {
                "configs": cap_configs,
                "t400_passed": cap_t400_passed,
                "t50_passed": cap_t50_passed,
            }
            if CANDIDATE_CAP_ARM_ACTIVE
            else None
        ),
        "candidate_cap_mq": (
            {"off": cap_mq_off, "on": cap_mq_on} if CANDIDATE_CAP_ARM_ACTIVE else None
        ),
    }

    status: GateStatus = "complete" if (not missing and not rerun_required) else "incomplete"

    return {
        "status": status,
        "missing": missing,
        "rerun_required": rerun_required,
        "design_inputs": _design_inputs_snapshot(),
        "criteria": criteria,
        "items": cast(dict[str, object], items),
        "refit": cast(dict[str, object], refit) if refit is not None else None,
    }


def _print_gate_table(verdict: GateVerdict) -> None:
    print(f"STATUS {verdict['status']}")
    underfill = cast(dict[str, object], verdict["criteria"]["underfill_throughput"])
    print(f"UNDERFILL_THROUGHPUT: passed={underfill['passed']}")
    items = verdict["items"]
    if items is not None:
        for name, item_verdict in items.items():
            if item_verdict is not None:
                print(f"{name.upper()}: {cast(dict[str, object], item_verdict)['outcome']}")
    if verdict["refit"] is not None:
        print(f"REFIT: {verdict['refit']['decision']}")
    if verdict["missing"]:
        print("MISSING:")
        for entry in verdict["missing"]:
            print(f"  - {entry}")
    if verdict["rerun_required"]:
        print("RERUN REQUIRED:")
        for entry in verdict["rerun_required"]:
            print(f"  RERUN {entry}")


# ==============================================================================
# design-inputs subcommand (D-16, D-17) — every formula from step0-protocol.md
# section 7, computed mechanically over committed step-0 data. Never chosen
# by eye; the A0 commit (Plan 226-08) transcribes this output verbatim into
# the frozen design-input constants above.
# ==============================================================================


class DesignInputsResult(TypedDict):
    missing: list[str]
    escalations: list[str]
    values: dict[str, object]
    context: dict[str, object]


def _expected_mq_positions(fixture_path: Path) -> int:
    """The widened fixture's non-comment data-row count (the header line is
    the first non-comment line, excluded from the count)."""
    if not fixture_path.is_file():
        raise ValueError(f"_expected_mq_positions: fixture not found: {fixture_path}")
    lines = fixture_path.read_text(encoding="utf-8").splitlines()
    data_lines = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if len(data_lines) < 2:
        raise ValueError(f"_expected_mq_positions: no data rows in {fixture_path}")
    return len(data_lines) - 1


def _mq_allowance(data_dir: Path, mode: str) -> int:
    """`A = max(MQ_ALLOWANCE_FLOOR, d0)` where `d0` is the count of ids whose
    regression classification (from `delta_bot`, not the unvalidated
    `verdict_bot` text) differs between the MQ A0a and A0b step-0 runs for
    this stop mode."""
    a0a_rows = read_single_tsv(
        _step0_mq_dir(data_dir, "a0a", mode), _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
    )
    a0b_rows = read_single_tsv(
        _step0_mq_dir(data_dir, "a0b", mode), _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
    )
    a0a_by_id = {row["id"]: row for row in a0a_rows}
    a0b_by_id = {row["id"]: row for row in a0b_rows}
    if set(a0a_by_id) != set(a0b_by_id):
        raise ValueError(f"_mq_allowance: {mode} id-set mismatch between A0a and A0b")
    d0 = sum(
        1 for rid in a0a_by_id if _mq_regresses(a0a_by_id[rid]) != _mq_regresses(a0b_by_id[rid])
    )
    return max(MQ_ALLOWANCE_FLOOR, d0)


def _calibration_null_check(data_dir: Path) -> dict[Family, calib.FamilyNullCheck]:
    """Powered per-family calibration thresholds from the in-session A0b-vs-A0a
    null (step0-protocol.md section 3, `null_check` from Plan 226-03)."""
    path = _step0_calibration_path(data_dir, "verdict-a0b-vs-a0a.json")
    if not path.is_file():
        raise ValueError(f"_calibration_null_check: missing {path}")
    null_parity = calib.load_parity_verdict(path)
    return calib.null_check(
        null_parity, CALIBRATION_BASE_THRESHOLD, NULL_MODEL_SE_MULTIPLIER, NULL_ESCALATION_FACTOR
    )


def _root_split_max_t50_ratio(data_dir: Path) -> float:
    """`ROOT_SPLIT_MAX_T50_WALL_RATIO = 1 - G`, `G = max(ROOT_SPLIT_MIN_GAIN,
    ROOT_SPLIT_GAIN_FRACTION * P)` floored DOWN to the nearest 0.01, `P =
    (sum(single_ms - split_wall_ms) over the 16 throughput positions,
    Clear-Hash prototype content) / (sum of A0 T-50 pool-4 ladder wall_ms)`."""
    content_rows = read_single_tsv(
        _step0_content_dir(data_dir, "clear"), _CONTENT_TSV_PATTERN, _CONTENT_REQUIRED_COLUMNS
    )
    clear_proto = [
        row
        for row in content_rows
        if row["hash_mode"] == "clear"
        and row["position_set"] == "throughput"
        and row["split_source"] == "prototype"
    ]
    if not clear_proto:
        raise ValueError("_root_split_max_t50_ratio: no clear/throughput/prototype content rows")
    gain_ms = sum(float(row["single_ms"]) - float(row["split_wall_ms"]) for row in clear_proto)
    t50_rows = _read_step0_throughput_rows(data_dir, "t50-p4")
    a0_t50_wall_ms = sum(float(row["wall_ms"]) for row in _ladder_rows(t50_rows))
    if a0_t50_wall_ms <= 0:
        raise ValueError("_root_split_max_t50_ratio: A0 T-50 pool-4 ladder wall_ms sums to zero")
    p = gain_ms / a0_t50_wall_ms
    g = max(ROOT_SPLIT_MIN_GAIN, ROOT_SPLIT_GAIN_FRACTION * p)
    g_floored = math.floor(g * 100) / 100
    return 1.0 - g_floored


def _warm_noise_floor(data_dir: Path) -> float:
    """Candidate-weighted mean `noise_mean_abs_des` over every warm-mode
    step-0 content row (single-vs-single on two differently-warmed engines)."""
    content_rows = read_single_tsv(
        _step0_content_dir(data_dir, "warm"), _CONTENT_TSV_PATTERN, _CONTENT_REQUIRED_COLUMNS
    )
    warm_rows = [row for row in content_rows if row["hash_mode"] == "warm"]
    if not warm_rows:
        raise ValueError("_warm_noise_floor: no warm content rows")
    return _candidate_weighted_mean(warm_rows, "noise_mean_abs_des")


def _candidate_cap_active(data_dir: Path) -> tuple[bool, dict[str, float]]:
    """D-17 section 5: fires iff the mean-of-two-runs
    `totals.nonRootGt8Share` (from `profile_search.mjs`'s own JSON output)
    is >= D17_DOMINANCE_SHARE at EITHER judged budget."""
    shares: dict[str, float] = {}
    for budget in (50, 400):
        run_shares: list[float] = []
        for run in (1, 2):
            path = _step0_profile_path(data_dir, budget, run)
            if not path.is_file():
                raise ValueError(f"_candidate_cap_active: missing {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            run_shares.append(float(payload["totals"]["nonRootGt8Share"]))
        shares[str(budget)] = sum(run_shares) / len(run_shares)
    active = any(share >= D17_DOMINANCE_SHARE for share in shares.values())
    return active, shares


def _stop_rule_max_wall_ms(data_dir: Path) -> tuple[float | None, float]:
    """`STOP_RULE_MAX_WALL_MS` is the frozen `STOP_RULE_225_CEILING_MS` when
    the step-0 A0 idle-box max stop wall is below it; otherwise there is no
    valid derived value (escalate) — returns `(None, measured_max)`."""
    rows = read_single_tsv(_step0_stop_dir(data_dir), _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
    if len(rows) != EXPECTED_STOP_POSITIONS:
        raise ValueError(
            f"_stop_rule_max_wall_ms: expected {EXPECTED_STOP_POSITIONS} rows, got {len(rows)}"
        )
    a0_max_wall_ms = max(float(row["wall_ms"]) for row in rows)
    if a0_max_wall_ms < STOP_RULE_225_CEILING_MS:
        return float(STOP_RULE_225_CEILING_MS), a0_max_wall_ms
    return None, a0_max_wall_ms


def design_inputs(data_dir: Path, fixture_path: Path) -> DesignInputsResult:
    missing: list[str] = []
    escalations: list[str] = []
    values: dict[str, object] = dict.fromkeys(_DESIGN_INPUT_NAMES)
    context: dict[str, object] = {}

    def attempt(fn: Callable[[], object]) -> object | None:
        try:
            return fn()
        except ValueError as exc:
            missing.append(str(exc))
            return None

    expected_mq = attempt(lambda: _expected_mq_positions(fixture_path))
    if expected_mq is not None:
        values["EXPECTED_MQ_POSITIONS"] = expected_mq

    allowance_off = attempt(lambda: _mq_allowance(data_dir, "off"))
    if allowance_off is not None:
        values["MQ_ALLOWANCE_OFF"] = allowance_off
    allowance_on = attempt(lambda: _mq_allowance(data_dir, "on"))
    if allowance_on is not None:
        values["MQ_ALLOWANCE_ON"] = allowance_on

    null_checks = attempt(lambda: _calibration_null_check(data_dir))
    if null_checks is not None:
        null_checks = cast(dict[Family, calib.FamilyNullCheck], null_checks)
        values["CALIBRATION_THRESHOLD_MAIA"] = null_checks["maia"]["threshold"]
        values["CALIBRATION_THRESHOLD_SF"] = null_checks["sf"]["threshold"]
        context["calibration_null"] = cast(object, null_checks)
        family: Family
        for family in ("maia", "sf"):
            if null_checks[family]["escalate"]:
                escalations.append(f"calibration {family}")

    ratio = attempt(lambda: _root_split_max_t50_ratio(data_dir))
    if ratio is not None:
        values["ROOT_SPLIT_MAX_T50_WALL_RATIO"] = ratio

    noise_floor = attempt(lambda: _warm_noise_floor(data_dir))
    if noise_floor is not None:
        floor = cast(float, noise_floor)
        values["CONTENT_MAX_WARM_MEAN_ABS_DES"] = CONTENT_WARM_MULTIPLIER * floor
        values["CONTENT_MAX_CLEAR_MEAN_ABS_DES"] = CONTENT_CLEAR_MULTIPLIER * floor
        context["warm_noise_floor"] = floor

    cap = attempt(lambda: _candidate_cap_active(data_dir))
    if cap is not None:
        active, shares = cast(tuple[bool, dict[str, float]], cap)
        values["CANDIDATE_CAP_ARM_ACTIVE"] = active
        context["d17_shares"] = cast(object, shares)

    stop = attempt(lambda: _stop_rule_max_wall_ms(data_dir))
    if stop is not None:
        max_wall_ms, a0_max_wall_ms = cast(tuple[float | None, float], stop)
        values["STOP_RULE_MAX_WALL_MS"] = max_wall_ms
        context["step0_a0_max_stop_wall_ms"] = a0_max_wall_ms
        if max_wall_ms is None:
            escalations.append("stop-rule")

    return {
        "missing": missing,
        "escalations": escalations,
        "values": values,
        "context": context,
    }


# ==============================================================================
# CLI
# ==============================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gates_parser = subparsers.add_parser(
        "gates", help="Render every Phase 226 gate criterion from the pinned data layout"
    )
    gates_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    gates_parser.add_argument("--out-json", default=DEFAULT_VERDICT_JSON)

    reruns_parser = subparsers.add_parser(
        "reruns",
        help="Print the move-quality reruns required by unconfirmed pass->regression flips",
    )
    reruns_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    design_parser = subparsers.add_parser(
        "design-inputs",
        help="Derive every design-input constant from committed step-0 data (D-16, D-17)",
    )
    design_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    design_parser.add_argument("--fixture-path", default=FIXTURE_PATH)
    design_parser.add_argument("--out-json", default=None)

    cells_parser = subparsers.add_parser(
        "cells-to-json", help='Fit *-cells.tsv files into a {"cells": [...]} payload'
    )
    cells_parser.add_argument("--cells-tsv", action="append", default=None, required=True)
    cells_parser.add_argument("--out-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "gates":
        data_dir = Path(args.data_dir)
        unset = _unset_design_inputs()
        if unset:
            print("STATUS incomplete")
            print("UNSET DESIGN INPUTS:")
            for name in unset:
                print(f"  - {name}")
            verdict: GateVerdict = {
                "status": "incomplete",
                "missing": [f"design input unset: {name}" for name in unset],
                "rerun_required": [],
                "design_inputs": _design_inputs_snapshot(),
                "criteria": {},
                "items": None,
                "refit": None,
            }
            out_path = Path(args.out_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            return EXIT_INCOMPLETE
        try:
            verdict = run_gates(data_dir)
        except RootSplitDataError as exc:
            print(f"ERROR: {exc}")
            return EXIT_INVALID
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return EXIT_INVALID
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _print_gate_table(verdict)
        return 0 if verdict["status"] == "complete" else EXIT_INCOMPLETE

    if args.command == "reruns":
        data_dir = Path(args.data_dir)
        unset = _unset_design_inputs()
        if unset:
            print("STATUS incomplete")
            print("UNSET DESIGN INPUTS:")
            for name in unset:
                print(f"  - {name}")
            return EXIT_INCOMPLETE
        try:
            reruns = required_reruns(data_dir)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return EXIT_INVALID
        if not reruns:
            print("NO RERUNS REQUIRED")
        else:
            for arm, mode in reruns:
                print(f"RERUN {arm} {mode}")
        return 0

    if args.command == "design-inputs":
        data_dir = Path(args.data_dir)
        fixture_path = Path(args.fixture_path)
        result = design_inputs(data_dir, fixture_path)
        for name in _DESIGN_INPUT_NAMES:
            print(f"DESIGN-INPUT {name} {result['values'][name]}")
        for escalation in result["escalations"]:
            print(f"DESIGN-INPUT-ESCALATE {escalation}")
        for key, value in result["context"].items():
            print(f"CONTEXT {key} {value}")
        if args.out_json:
            out_path = Path(args.out_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
        if result["missing"]:
            print("MISSING:")
            for entry in result["missing"]:
                print(f"  - {entry}")
            return EXIT_INCOMPLETE
        return 0

    if args.command == "cells-to-json":
        fixed_ratings = anchor_fit.load_fixed_ratings(anchor_fit.DEFAULT_INTERNAL_SCALE_JSON)
        cells = fit_new_cells(
            args.cells_tsv,
            fixed_ratings,
            anchor_fit.DEFAULT_BOOTSTRAP_SAMPLES,
            anchor_fit.DEFAULT_BOOTSTRAP_SEED,
        )
        payload = cells_to_payload(cells)
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {args.out_json}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
