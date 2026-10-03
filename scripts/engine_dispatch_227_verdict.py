"""engine_dispatch_227_verdict.py — Phase 227 gate verdict.

The machine-readable twin of `reports/continuous-dispatch-227/accept-rule.md`
(D-00, D-01..D-04, D-07, D-15, D-17, D-20): every threshold constant below is
fixed BEFORE any continuous-mode data exists and is NOT reachable from any CLI
flag, environment variable, or config file. The only legitimate way to change
one is to edit this file and the accept-rule doc together, before the affected
gate runs; an owner override is a separate document, never a rule edit.

Judging philosophy (D-00): round mode is a comparison arm, not a reference
answer. The ground truth for move quality is the d20 Stockfish evaluation, so
D-01 is a one-sided non-inferiority test on ABSOLUTE quality (a continuous mode
that picks better moves passes), judged as a point estimate. Closeness to round
mode (unsigned divergence, McNemar, the bootstrap lower bound) is reported and
never judged.

The twin never reports a pass on missing, duplicate or mislabeled data:

* exit 0 — inputs complete and valid, whatever the pass/fail outcome (read
  pass/fail from the printed lines and the verdict JSON, never the exit code);
* exit 1 (`EXIT_INVALID`) — data that cannot be trusted (a TSV whose
  `dispatch_mode` disagrees with its arm, a non-FIFO Maia, a wrong grade depth,
  a duplicate row, ...). Never read as noise. A difference between round-mode
  REPEATS is not in this list: the owner decided on 2026-10-02 that bit-identical
  round results are not required with concurrent (worker-thread) Maia, so under
  `--hash warm` round repeats differ slightly run to run and the disagreement
  rate is a report-only statistic (`round_repeat_disagreement_*`);
* exit 2 (`EXIT_INCOMPLETE`) — data not present yet (missing directory or file,
  too few positions, repeats or rounds).

stdlib-only (`argparse`/`csv`/`json`/`math`/`random`/`statistics`/`fractions`)
plus the 226 calibration reducer, imported rather than re-implemented. Standalone
research tool (`scripts/`, not `app/`): exempt from CLAUDE.md's Sentry-capture
rules, which apply only to `app/services` and `app/routers`.

Usage:
    uv run python scripts/engine_dispatch_227_verdict.py tripwire \\
        --mq-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/worker \\
        --baseline-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/main

    uv run python scripts/engine_dispatch_227_verdict.py mq \\
        --data-dir reports/data/continuous-dispatch-227

    uv run python scripts/engine_dispatch_227_verdict.py throughput \\
        --data-dir reports/data/continuous-dispatch-227

    uv run python scripts/engine_dispatch_227_verdict.py webgpu \\
        --json reports/data/continuous-dispatch-227/webgpu/continuous-leg.json

    uv run python scripts/engine_dispatch_227_verdict.py gates \\
        --data-dir reports/data/continuous-dispatch-227 \\
        [--out-json reports/continuous-dispatch-227/verdict.json]

Pinned data layout under the data dir: `tripwire/mq-{off,on}/`;
`gate/mq/{round,continuous}/mq-{off,on}/` (judged); `gate/mq-clear/...` and
`gate/mq-a400/...` (report-only); `gate/throughput/manifest.tsv` with step dirs
`r{round}/{config}/{arm}/`; `gate/calibration/verdict-a1-vs-a0.json`;
`webgpu/continuous-leg.json` (judged) and `webgpu/round-leg.json` (report-only).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
import sys
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal, TypedDict

import engine_throughput_226_calibration as calib
from calibration_parity_verdict import Family
from engine_search_fixes_verdict import read_single_tsv
from engine_throughput_226_verdict import _mcnemar_one_sided_p

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# Frozen constants (D-00..D-04, D-07, D-15, D-17, D-20) — fixed before data.
# ==============================================================================

DispatchArm = Literal["a0", "a1"]
DispatchMode = Literal["round", "continuous"]
StopMode = Literal["off", "on"]
ThroughputConfig = Literal["stop-p4", "t400-p4", "t50-p2", "t400-p2"]
RefitDecision227 = Literal["refit", "no-refit", "escalate"]
Mechanical = Literal["ship-eligible", "hold"]

#: A0 is A21S in round mode, A1 is continuous mode (D-15).
ARM_MODE: dict[DispatchArm, DispatchMode] = {"a0": "round", "a1": "continuous"}

#: D-01: k x the 226 warm content floor.
MQ_SIGNED_MARGIN_K = 1.5
#: 226 `CONTENT_MAX_CLEAR_MEAN_ABS_DES`, the content-instrument floor (mean
#: |des| between differently warmed single-call grades).
MQ_CONTENT_FLOOR = 0.016804127272727273
#: D-01 margin = `MQ_SIGNED_MARGIN_K * MQ_CONTENT_FLOOR` (also 226's warm
#: `CONTENT_MAX`). Judged as a POINT ESTIMATE of D, never a CI lower bound
#: (RESEARCH Q1: an LCB rule fails a neutral change ~30% of the time).
MQ_SIGNED_MARGIN = 0.02520619090909091
#: D-02: repeats per arm per judged cell (RESEARCH Q3: the D-03 allowance is
#: calibrated at R = 5, about a 4-5% null false-fail, vs 8-10% at R = 3).
MQ_REPEATS = 5
#: D-01: the d20 ground truth. The MQ script defaults to 18, so this is passed
#: explicitly and validated on every judged row.
MQ_GRADE_DEPTH = 20
#: Judged MQ cells run the bot-move path at this node budget (c4, pool 4).
MQ_NODES = 50
#: The report-only analysis-400 MQ cell (D-02, D-20).
MQ_A400_NODES = 400
#: Move-quality regression margin on the bot's pick (226 D-14, unchanged).
MQ_REGRESSION_MARGIN = 0.05
#: D-03: `A = max(MQ_ALLOWANCE_FLOOR, ceil(max over continuous repeat pairs))`.
MQ_ALLOWANCE_FLOOR = 1
#: The widened fixture's row count (226 D-14).
EXPECTED_MQ_POSITIONS = 60
#: Judged MQ cells: the stop rule off (isolates search quality) and on (the
#: shipped bot path).
JUDGED_MQ_CELLS: tuple[StopMode, ...] = ("off", "on")
#: Report-only bootstrap over positions (repeats kept together).
BOOTSTRAP_SAMPLES = 10000
BOOTSTRAP_SEED = 227
BOOTSTRAP_CONFIDENCE = 0.95

#: D-04 as amended by D-17: gain on stop-p4 OR t400-p4 of at least this much.
THROUGHPUT_SHIP_GAIN = 0.15
#: D-04: neither ship-bar config may regress beyond this wall ratio.
THROUGHPUT_MAX_RATIO = 1.03
#: D-04: the pool-2 tolerance floor, applied as `1 + max(noise, this)`.
POOL2_MIN_TOLERANCE = 0.03
#: D-04: interleaved rounds required per judged config.
THROUGHPUT_MIN_ROUNDS = 3
#: SEED-126's 16 canonical positions (carried from 225/226).
EXPECTED_THROUGHPUT_POSITIONS = 16
SHIP_BAR_CONFIGS: tuple[ThroughputConfig, ...] = ("stop-p4", "t400-p4")
POOL2_CONFIGS: tuple[ThroughputConfig, ...] = ("t50-p2", "t400-p2")
#: A step started above this 1-minute load average is a report-only warning.
LOAD_GATE_MAX = 2.0

#: D-07: continuous/round bot-move wall ratio on the WebGPU machine.
WEBGPU_MAX_RATIO = 1.03
WEBGPU_MIN_ROUNDS = 3
WEBGPU_SCHEMA = "engine-bench-227/v1"

#: D-15: 226's powered calibration machinery, unchanged (RESEARCH Q4).
CALIBRATION_THRESHOLD_MAIA = 85.0
CALIBRATION_THRESHOLD_SF = 53.542812708469995
SHAPE_GUARD_Z = 1.96
GAMES_PER_CELL_ANCHOR = 50
ARM_SEED = 1

#: Data that cannot be trusted; distinct from `EXIT_INCOMPLETE`.
EXIT_INVALID = 1
#: Data not present yet.
EXIT_INCOMPLETE = 2

DEFAULT_DATA_DIR = str(_REPO_ROOT / "reports" / "data" / "continuous-dispatch-227")
DEFAULT_VERDICT_JSON = str(_REPO_ROOT / "reports" / "continuous-dispatch-227" / "verdict.json")
#: The committed 226 A21S round-mode MQ data the tripwire compares against.
BASELINE_A21S_DIR = str(_REPO_ROOT / "reports" / "data" / "engine-throughput-226" / "gate" / "a21s")
FIXTURE_PATH = str(_REPO_ROOT / "fixtures" / "engine" / "move-quality-226.tsv")


class InvalidDataError(ValueError):
    """Data that cannot be trusted (mislabeled, leaking, duplicated). `main`
    maps it to `EXIT_INVALID`; never read as noise."""


class IncompleteDataError(ValueError):
    """Data not present yet (missing directory/file/column, too few rows,
    repeats or rounds). `main` maps it to `EXIT_INCOMPLETE`."""


# ==============================================================================
# Data layout — relative paths under `--data-dir`.
# ==============================================================================


def _mq_cell_dir(data_dir: Path, base: str, arm_mode: DispatchMode, stop: StopMode) -> Path:
    return data_dir / "gate" / base / arm_mode / f"mq-{stop}"


#: Judged MQ cells live under `gate/mq/{round,continuous}/mq-{off,on}`; the
#: report-only Clear-Hash cells under `gate/mq-clear/...` (both stop modes, one
#: repeat) and the analysis-400 cell under `gate/mq-a400/.../mq-off`.
_MQ_JUDGED_BASE = "mq"
_MQ_CLEAR_BASE = "mq-clear"
_MQ_A400_BASE = "mq-a400"
_MQ_A400_CELLS: tuple[StopMode, ...] = ("off",)

# ==============================================================================
# TSV reading
# ==============================================================================

_MQ_TSV_PATTERN = "engine-move-quality-*.tsv"
#: Columns the 226 baseline files carry (the tripwire's required set).
_MQ_BASE_COLUMNS = (
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
#: Columns Plan 227-04's harness appends; required on judged data.
_MQ_JUDGED_COLUMNS = (*_MQ_BASE_COLUMNS, "dispatch_mode", "repeat", "hash_mode", "maia_fifo")
#: Tripwire string-compared fields (es_bot additionally at equal grade_depth).
_TRIPWIRE_FIELDS = ("bot_move", "analysis_move", "nodes_evaluated", "stop_reason")
_VERDICT_REGRESSION = "regression"
_VERDICT_PASS = "pass"

Row = Mapping[str, str]
#: One repeat's rows keyed by position id.
RowsById = dict[str, Row]


def _read_mq_dir(directory: Path, columns: Sequence[str]) -> list[dict[str, str]]:
    """Exactly one `engine-move-quality-*.tsv` per directory. A missing
    directory, a missing or duplicate file, or a missing column is a
    "can't judge yet" (`IncompleteDataError`), never a pass."""
    try:
        return read_single_tsv(directory, _MQ_TSV_PATTERN, columns)
    except ValueError as exc:
        raise IncompleteDataError(str(exc)) from exc


def _repeat_of(row: Row) -> int:
    """The row's repeat number; a 226 baseline file has no `repeat` column and
    reads as repeat 1."""
    raw = row.get("repeat")
    if raw is None or raw == "":
        return 1
    try:
        return int(raw)
    except ValueError as exc:
        raise InvalidDataError(f"non-integer repeat {raw!r} for id {row.get('id')!r}") from exc


def _group_by_repeat(rows: Sequence[Row], label: str) -> dict[int, RowsById]:
    grouped: dict[int, RowsById] = {}
    for row in rows:
        bucket = grouped.setdefault(_repeat_of(row), {})
        if row["id"] in bucket:
            raise InvalidDataError(
                f"{label}: duplicate row for id {row['id']!r} repeat {_repeat_of(row)}"
            )
        bucket[row["id"]] = row
    return grouped


def load_fixture_ids(path: str = FIXTURE_PATH) -> frozenset[str]:
    """The move-quality fixture's ids (non-comment rows, header first)."""
    fixture = Path(path)
    if not fixture.is_file():
        raise IncompleteDataError(f"load_fixture_ids: fixture not found: {fixture}")
    with fixture.open(encoding="utf-8", newline="") as f:
        lines = [line for line in f if not line.startswith("#")]
    reader = csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    ids = [row["id"] for row in reader]
    if len(ids) != EXPECTED_MQ_POSITIONS or len(set(ids)) != len(ids):
        raise InvalidDataError(
            f"load_fixture_ids: {fixture} has {len(ids)} rows ({len(set(ids))} distinct), "
            f"expected {EXPECTED_MQ_POSITIONS}"
        )
    return frozenset(ids)


# ==============================================================================
# Tripwire — round mode against the committed 226 a21s data (D-11, D-18)
# ==============================================================================


class TripwireModeResult(TypedDict):
    rows: int
    diffs: list[str]


class TripwireResult(TypedDict):
    modes: dict[str, TripwireModeResult]
    passed: bool


def _tripwire_row_fields(row: Row, base: Row) -> list[str]:
    """Fields on which a candidate round-mode row disagrees with the baseline
    row for the same id. `es_bot` (6-decimal string) is compared only when both
    files graded at the same depth (a d20 candidate cannot match d18 values);
    when the candidate carries `dispatch_mode` it must be `round`."""
    fields = [name for name in _TRIPWIRE_FIELDS if row[name] != base[name]]
    if row["grade_depth"] == base["grade_depth"] and row["es_bot"] != base["es_bot"]:
        fields.append("es_bot")
    dispatch_mode = row.get("dispatch_mode")
    if dispatch_mode is not None and dispatch_mode != "round":
        fields.append("dispatch_mode")
    return fields


def _tripwire_mode(candidate: Sequence[Row], baseline: Sequence[Row]) -> TripwireModeResult:
    base_by_id = {row["id"]: row for row in baseline}
    diffs: list[str] = []
    seen: set[str] = set()
    for row in candidate:
        seen.add(row["id"])
        reference = base_by_id.get(row["id"])
        repeat = _repeat_of(row)
        if reference is None:
            diffs.append(f"{row['id']} repeat={repeat} fields=id")
            continue
        fields = _tripwire_row_fields(row, reference)
        if fields:
            diffs.append(f"{row['id']} repeat={repeat} fields={','.join(fields)}")
    diffs.extend(f"{pid} missing" for pid in sorted(set(base_by_id) - seen))
    return {"rows": len(candidate), "diffs": diffs}


def evaluate_tripwire(mq_dir: Path, baseline_dir: Path) -> TripwireResult:
    """Every row of every repeat in `mq_dir/mq-{off,on}` must match the 226
    baseline row with the same id. Strict, and meant for `--hash clear`, where
    worker-thread Maia and main-thread Maia are bit-identical (Plan 227-08):

        tripwire --mq-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/worker \\
                 --baseline-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/main

    Plan 227-10 re-runs that check after the `mctsSearch` helper extraction. Under
    `--hash warm` with worker Maia the round mode is NOT bit-identical to the
    committed 226 a21s data (owner direction 2026-10-02: very similar is good
    enough), so the default `--baseline-dir` comparison is report-only similarity
    there, never a gate. A mismatch at `--hash clear` is a harness leak, never
    noise."""
    modes: dict[str, TripwireModeResult] = {}
    for stop in JUDGED_MQ_CELLS:
        candidate = _read_mq_dir(mq_dir / f"mq-{stop}", _MQ_BASE_COLUMNS)
        baseline = _read_mq_dir(baseline_dir / f"mq-{stop}", _MQ_BASE_COLUMNS)
        modes[stop] = _tripwire_mode(candidate, baseline)
    return {"modes": modes, "passed": all(not m["diffs"] for m in modes.values())}


# ==============================================================================
# Move quality — D-01 (signed point estimate) and D-03 (net regressions)
# ==============================================================================


def d01_passes(decision_d: float) -> bool:
    """D-01: pass iff `D >= -MQ_SIGNED_MARGIN`. Inclusive: a continuous mode
    exactly at the margin passes, and any positive D (a BETTER continuous mode)
    passes (D-00). A point estimate, never a CI lower bound."""
    return decision_d >= -MQ_SIGNED_MARGIN


class MqReport(TypedDict):
    """Report-only statistics. Nothing here can change pass/fail."""

    bootstrap_lcb: float
    k_unstable: int
    unsigned_mean_abs_des: float
    mcnemar_p: float | None
    mcnemar_b: int
    mcnemar_c: int
    analysis_d: float
    flip_mean_size: float | None
    margin_flip_fraction: float | None
    margin_flips: float | None
    round_regressions: float
    continuous_regressions: float
    #: Positions whose `bot_move` differs across this cell's ROUND repeats, and
    #: that count over the positions (owner direction 2026-10-02: report-only).
    round_repeat_disagreement_positions: int
    round_repeat_disagreement_rate: float


class MqCellResult(TypedDict):
    cell: StopMode
    positions: int
    repeats: int
    decision_d: float
    margin: float
    pass_d01: bool
    net: float
    allowance: int
    pass_d03: bool
    passed: bool
    report: MqReport


def _is_regression(row: Row) -> bool:
    verdict = row["verdict_bot"]
    if verdict not in (_VERDICT_REGRESSION, _VERDICT_PASS):
        raise InvalidDataError(
            f"id {row['id']!r} repeat {_repeat_of(row)}: unknown verdict_bot {verdict!r}"
        )
    return verdict == _VERDICT_REGRESSION


def mq_allowance(cont_rows: Sequence[Row]) -> int:
    """D-03: `A = max(MQ_ALLOWANCE_FLOOR, ceil(max over continuous repeat pairs
    r<s of |N_rs|))` where `N_rs` = (pass->regression) - (regression->pass)
    between repeats r and s. A signed net, so two repeats that swap one
    regression for another do not widen the allowance."""
    by_repeat = _group_by_repeat(cont_rows, "continuous")
    flags = {
        repeat: {pid: _is_regression(row) for pid, row in rows.items()}
        for repeat, rows in by_repeat.items()
    }
    worst = 0
    for first, second in itertools.combinations(sorted(flags), 2):
        shared = flags[first].keys() & flags[second].keys()
        gained = sum(1 for pid in shared if not flags[first][pid] and flags[second][pid])
        lost = sum(1 for pid in shared if flags[first][pid] and not flags[second][pid])
        worst = max(worst, abs(gained - lost))
    return max(MQ_ALLOWANCE_FLOOR, math.ceil(worst))


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _per_position_means(
    by_repeat: Mapping[int, RowsById], ids: Sequence[str], column: str
) -> dict[str, float]:
    """Mean over repeats of `column`, per position."""
    return {pid: _mean([float(rows[pid][column]) for rows in by_repeat.values()]) for pid in ids}


def _signed_diffs(
    round_by: Mapping[int, RowsById],
    cont_by: Mapping[int, RowsById],
    ids: Sequence[str],
    column: str,
) -> list[float]:
    """Per position: mean over repeats of continuous `column` minus mean over
    repeats of round `column`."""
    round_means = _per_position_means(round_by, ids, column)
    cont_means = _per_position_means(cont_by, ids, column)
    return [cont_means[pid] - round_means[pid] for pid in ids]


def _bootstrap_lcb(diffs: Sequence[float]) -> float:
    """One-sided `BOOTSTRAP_CONFIDENCE` lower bound of the mean difference,
    resampling POSITIONS with replacement (a position's repeats are already
    pooled into its difference, so repeats stay together). Report-only."""
    rng = random.Random(BOOTSTRAP_SEED)
    size = len(diffs)
    means = sorted(_mean(rng.choices(diffs, k=size)) for _ in range(BOOTSTRAP_SAMPLES))
    return means[int((1 - BOOTSTRAP_CONFIDENCE) * BOOTSTRAP_SAMPLES)]


def _flip_sizes(
    round_by: Mapping[int, RowsById], cont_by: Mapping[int, RowsById], ids: Sequence[str]
) -> list[float]:
    """|es_cont - es_round| for every (position, repeat) where the continuous
    pick differs from round mode's repeat-1 pick (round repeats can differ
    slightly under warm hash and worker Maia): the size of a changed pick, used
    only to express the margin in flips (report-only)."""
    first_round = round_by[min(round_by)]
    sizes: list[float] = []
    for rows in cont_by.values():
        for pid in ids:
            if rows[pid]["bot_move"] != first_round[pid]["bot_move"]:
                sizes.append(abs(float(rows[pid]["es_bot"]) - float(first_round[pid]["es_bot"])))
    return sizes


def _regression_counts(by_repeat: Mapping[int, RowsById], ids: Sequence[str]) -> dict[str, int]:
    """Per position: in how many repeats the bot's pick is a regression."""
    return {pid: sum(_is_regression(rows[pid]) for rows in by_repeat.values()) for pid in ids}


def _build_report(
    round_by: Mapping[int, RowsById], cont_by: Mapping[int, RowsById], ids: Sequence[str]
) -> MqReport:
    diffs = _signed_diffs(round_by, cont_by, ids, "es_bot")
    round_counts = _regression_counts(round_by, ids)
    cont_counts = _regression_counts(cont_by, ids)
    # Position-level regression for McNemar: a majority of the repeats.
    majority = {
        pid: (round_counts[pid] * 2 > len(round_by), cont_counts[pid] * 2 > len(cont_by))
        for pid in ids
    }
    pass_to_regression = sum(1 for was, now in majority.values() if now and not was)
    regression_to_pass = sum(1 for was, now in majority.values() if was and not now)
    sizes = _flip_sizes(round_by, cont_by, ids)
    flip_size = _mean(sizes) if sizes and _mean(sizes) > 0 else None
    flip_fraction = MQ_SIGNED_MARGIN / flip_size if flip_size is not None else None
    unstable = sum(
        1 for pid in ids if len({rows[pid]["bot_move"] for rows in cont_by.values()}) > 1
    )
    disagreeing = round_repeat_disagreement_positions(round_by, ids)
    return {
        "bootstrap_lcb": _bootstrap_lcb(diffs),
        "k_unstable": unstable,
        "unsigned_mean_abs_des": _mean([abs(d) for d in diffs]),
        "mcnemar_p": _mcnemar_one_sided_p(pass_to_regression, regression_to_pass),
        "mcnemar_b": pass_to_regression,
        "mcnemar_c": regression_to_pass,
        "analysis_d": _mean(_signed_diffs(round_by, cont_by, ids, "es_analysis")),
        "flip_mean_size": flip_size,
        "margin_flip_fraction": flip_fraction,
        "margin_flips": flip_fraction * len(ids) if flip_fraction is not None else None,
        "round_regressions": sum(round_counts.values()) / len(round_by),
        "continuous_regressions": sum(cont_counts.values()) / len(cont_by),
        "round_repeat_disagreement_positions": disagreeing,
        "round_repeat_disagreement_rate": disagreeing / len(ids),
    }


def _check_ids_known(
    label: str, by_repeat: Mapping[int, RowsById], expected: frozenset[str]
) -> None:
    for repeat, rows in by_repeat.items():
        unknown = sorted(set(rows) - expected)
        if unknown:
            raise InvalidDataError(
                f"{label}: repeat {repeat} has ids not in the fixture: {unknown[:5]}"
            )


def _check_complete(
    label: str, by_repeat: Mapping[int, RowsById], expected: frozenset[str]
) -> None:
    """Exactly `MQ_REPEATS` repeats (numbered 1..N), each with every fixture id.
    Fewer is data not present yet; more, or odd numbering, is mislabeled."""
    if len(by_repeat) > MQ_REPEATS:
        raise InvalidDataError(f"{label}: {len(by_repeat)} repeats, expected {MQ_REPEATS}")
    if len(by_repeat) < MQ_REPEATS:
        raise IncompleteDataError(f"{label}: {len(by_repeat)} repeats, expected {MQ_REPEATS}")
    if sorted(by_repeat) != list(range(1, MQ_REPEATS + 1)):
        raise InvalidDataError(
            f"{label}: repeats are {sorted(by_repeat)}, expected 1..{MQ_REPEATS}"
        )
    for repeat, rows in sorted(by_repeat.items()):
        if set(rows) != expected:
            raise IncompleteDataError(
                f"{label}: repeat {repeat} has {len(rows)} of {len(expected)} fixture ids"
            )


def _check_judged_labels(
    label: str, arm_mode: DispatchMode, by_repeat: Mapping[int, RowsById]
) -> None:
    """Every judged row must be what its arm claims: the arm's dispatch mode,
    the app-faithful Maia FIFO, the warm hash and the d20 ground truth."""
    for repeat, rows in sorted(by_repeat.items()):
        for pid, row in rows.items():
            where = f"{label} id {pid!r} repeat {repeat}"
            if row["dispatch_mode"] != arm_mode:
                raise InvalidDataError(
                    f"{where}: dispatch_mode {row['dispatch_mode']!r}, expected {arm_mode!r}"
                )
            if row["maia_fifo"].lower() != "true":
                raise InvalidDataError(f"{where}: maia_fifo {row['maia_fifo']!r}, expected true")
            if row["hash_mode"] != "warm":
                raise InvalidDataError(f"{where}: hash_mode {row['hash_mode']!r}, expected warm")
            if row["grade_depth"] != str(MQ_GRADE_DEPTH):
                raise InvalidDataError(
                    f"{where}: grade_depth {row['grade_depth']!r}, expected {MQ_GRADE_DEPTH}"
                )


def round_repeat_disagreement_positions(
    by_repeat: Mapping[int, RowsById], ids: Sequence[str]
) -> int:
    """Number of positions whose `bot_move` is not the same in every round repeat.

    Report-only (owner direction 2026-10-02, Plan 227-09): bit-identical round
    results are not required with concurrent worker-thread Maia, and under
    `--hash warm` round repeats differ slightly run to run (Plan 227-04 measured
    the minority pick on `cBFTV` in about 8 to 11 percent of repeats). This used
    to raise `InvalidDataError`; it no longer can. D already averages each
    position over repeats and D-03's net is already fractional, so the decision
    math needs no other change."""
    return sum(1 for pid in ids if len({rows[pid]["bot_move"] for rows in by_repeat.values()}) > 1)


def evaluate_mq_cell(
    cell: StopMode,
    round_rows: Sequence[Row],
    cont_rows: Sequence[Row],
    expected_ids: frozenset[str] | None = None,
) -> MqCellResult:
    """One judged cell: validity first, then D-01 and D-03.

    D = mean over positions of (mean over repeats of continuous `es_bot` minus
    mean over repeats of round `es_bot`); D-01 passes iff `D >= -MQ_SIGNED_MARGIN`.
    D-03 net = sum over positions of the continuous regression fraction minus
    the round regression fraction (a continuous fix lowers it), compared exactly
    (`Fraction`) against the allowance from `mq_allowance`."""
    expected = expected_ids if expected_ids is not None else load_fixture_ids()
    round_by = _group_by_repeat(round_rows, "round")
    cont_by = _group_by_repeat(cont_rows, "continuous")
    _check_ids_known("round", round_by, expected)
    _check_ids_known("continuous", cont_by, expected)
    _check_complete("round", round_by, expected)
    _check_complete("continuous", cont_by, expected)
    _check_judged_labels("round", "round", round_by)
    _check_judged_labels("continuous", "continuous", cont_by)

    ids = sorted(expected)
    decision_d = _mean(_signed_diffs(round_by, cont_by, ids, "es_bot"))
    round_total = sum(_regression_counts(round_by, ids).values())
    cont_total = sum(_regression_counts(cont_by, ids).values())
    net = Fraction(cont_total - round_total, MQ_REPEATS)
    allowance = mq_allowance(cont_rows)
    pass_d01 = d01_passes(decision_d)
    pass_d03 = net <= allowance
    return {
        "cell": cell,
        "positions": len(ids),
        "repeats": MQ_REPEATS,
        "decision_d": decision_d,
        "margin": MQ_SIGNED_MARGIN,
        "pass_d01": pass_d01,
        "net": float(net),
        "allowance": allowance,
        "pass_d03": pass_d03,
        "passed": pass_d01 and pass_d03,
        "report": _build_report(round_by, cont_by, ids),
    }


# ------------------------------------------------------------------------------
# Report-only cells: Clear-Hash (D-02) and analysis-400 (D-20)
# ------------------------------------------------------------------------------


class ReportOnlyCell(TypedDict):
    """Signed mean and regression counts for a cell that can never change the
    mechanical outcome. `status` is `absent` (directory not there), `unreadable`
    (present but malformed; `reason` says why) or `ok`."""

    status: Literal["ok", "absent", "unreadable"]
    reason: str | None
    positions: int | None
    repeats: int | None
    signed_mean: float | None
    round_regressions: float | None
    continuous_regressions: float | None
    net: float | None


def _empty_report_only(
    status: Literal["absent", "unreadable"], reason: str | None
) -> ReportOnlyCell:
    return {
        "status": status,
        "reason": reason,
        "positions": None,
        "repeats": None,
        "signed_mean": None,
        "round_regressions": None,
        "continuous_regressions": None,
        "net": None,
    }


def evaluate_mq_report_only(round_rows: Sequence[Row], cont_rows: Sequence[Row]) -> ReportOnlyCell:
    """Signed mean (continuous minus round, over the positions both arms
    cover) and per-repeat-average regression counts. No validity gating: this
    is information, never a verdict."""
    round_by = _group_by_repeat(round_rows, "round")
    cont_by = _group_by_repeat(cont_rows, "continuous")
    # Phase 227 review WR-01: an arm with no data rows used to escape as
    # TypeError (set.intersection with no arguments) or ZeroDivisionError
    # (len(cont_by) == 0), which the caller's `except ValueError` did not catch,
    # so a report-only cell could abort the whole verdict run.
    if not round_by or not cont_by:
        raise IncompleteDataError("report-only cell: an arm has no data rows")
    shared: set[str] = set.intersection(
        *(set(rows) for rows in (*round_by.values(), *cont_by.values()))
    )
    ids = sorted(shared)
    if not ids:
        raise InvalidDataError(
            "report-only cell: no position is present in every repeat of both arms"
        )
    round_reg = sum(_regression_counts(round_by, ids).values()) / len(round_by)
    cont_reg = sum(_regression_counts(cont_by, ids).values()) / len(cont_by)
    return {
        "status": "ok",
        "reason": None,
        "positions": len(ids),
        "repeats": len(cont_by),
        "signed_mean": _mean(_signed_diffs(round_by, cont_by, ids, "es_bot")),
        "round_regressions": round_reg,
        "continuous_regressions": cont_reg,
        "net": cont_reg - round_reg,
    }


def _report_only_cell(data_dir: Path, base: str, stop: StopMode) -> ReportOnlyCell:
    round_dir = _mq_cell_dir(data_dir, base, "round", stop)
    cont_dir = _mq_cell_dir(data_dir, base, "continuous", stop)
    if not round_dir.is_dir() and not cont_dir.is_dir():
        return _empty_report_only("absent", None)
    try:
        return evaluate_mq_report_only(
            _read_mq_dir(round_dir, _MQ_JUDGED_COLUMNS), _read_mq_dir(cont_dir, _MQ_JUDGED_COLUMNS)
        )
    except ValueError as exc:
        return _empty_report_only("unreadable", str(exc))


class MqGateResult(TypedDict):
    cells: dict[str, MqCellResult]
    clear: dict[str, ReportOnlyCell]
    a400: dict[str, ReportOnlyCell]
    virtual_loss_trigger: bool


def virtual_loss_trigger(cells: Mapping[str, MqCellResult]) -> bool:
    """D-08: true iff D-01 or D-03 fails in any judged cell (a virtual-loss arm
    runs only if exclusion is shown to hurt quality)."""
    return any(not (cell["pass_d01"] and cell["pass_d03"]) for cell in cells.values())


def run_mq_gate(data_dir: Path) -> MqGateResult:
    """Both judged cells (strict: any missing/invalid input raises) plus the
    report-only Clear-Hash and analysis-400 cells (lenient: never raise)."""
    cells: dict[str, MqCellResult] = {}
    for stop in JUDGED_MQ_CELLS:
        round_rows = _read_mq_dir(
            _mq_cell_dir(data_dir, _MQ_JUDGED_BASE, "round", stop), _MQ_JUDGED_COLUMNS
        )
        cont_rows = _read_mq_dir(
            _mq_cell_dir(data_dir, _MQ_JUDGED_BASE, "continuous", stop), _MQ_JUDGED_COLUMNS
        )
        cells[stop] = evaluate_mq_cell(stop, round_rows, cont_rows)
    return {
        "cells": cells,
        "clear": {
            stop: _report_only_cell(data_dir, _MQ_CLEAR_BASE, stop) for stop in JUDGED_MQ_CELLS
        },
        "a400": {stop: _report_only_cell(data_dir, _MQ_A400_BASE, stop) for stop in _MQ_A400_CELLS},
        "virtual_loss_trigger": virtual_loss_trigger(cells),
    }


# ==============================================================================
# Throughput — D-04 as amended by D-17 (interleaved, probe-normalized)
# ==============================================================================

_THROUGHPUT_CONFIGS: tuple[ThroughputConfig, ...] = (*SHIP_BAR_CONFIGS, *POOL2_CONFIGS)
#: A driver smoke run's config name; its manifest rows are never judged.
_SMOKE_CONFIG = "smoke"
_STOP_CONFIG: ThroughputConfig = "stop-p4"
_STOP_TSV_PATTERN = "engine-dispatch-stop-rule-*.tsv"
_DEPTH_AB_TSV_PATTERN = "engine-grading-depth-ab-*.tsv"
#: `depth-ab` TSVs also carry a flat-depth pass; only the ladder rows are judged.
_LADDER_DEPTH = "ladder"
_STEP_COLUMNS = (
    "wall_ms",
    "grade_cpu_ms",
    "dispatch_mode",
    "maia_fifo",
    "maia_peak_inflight",
)
#: The app's Maia is one-in-flight; a harness step that overlapped inferences is
#: not app-faithful (RESEARCH Pitfall 4).
_MAIA_MAX_PEAK_INFLIGHT = 1
#: Plan 227-07's driver writes exactly these manifest columns.
_MANIFEST_COLUMNS = (
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


def _manifest_path(data_dir: Path) -> Path:
    return data_dir / "gate" / "throughput" / "manifest.tsv"


class StepMetrics(TypedDict):
    wall_ms: float
    grade_ms: float
    probe_ms: float
    load1: float


class ConfigThroughput(TypedDict):
    """One config's interleaved a1-vs-a0 comparison over its rounds."""

    rounds: list[int]
    #: Per round `(W_a1 / P_a1) / (W_a0 / P_a0)`: the JUDGED quantity (D-17).
    ratios: list[float]
    raw_ratios: list[float]
    grade_ratios: list[float | None]
    a0_normalized_walls: list[float]
    geometric_mean: float
    gain: float
    raw_geometric_mean: float
    grade_geometric_mean: float | None


class ShipBar(TypedDict):
    gain_met: bool
    no_regression: bool
    passed: bool
    gains: dict[str, float]
    ratios: dict[str, float]


class ThroughputResult(TypedDict):
    configs: dict[str, ConfigThroughput]
    ship_bar: ShipBar
    load_warnings: list[str]


class Pool2Result(TypedDict):
    median_ratio: float
    noise: float
    tolerance: float
    passed: bool


StepKey = tuple[str, int, DispatchArm]


def _read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise IncompleteDataError(f"throughput manifest not found: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        missing = [c for c in _MANIFEST_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise InvalidDataError(f"throughput manifest {path} is missing column(s): {missing}")
        return list(reader)


def _manifest_arm(row: Row, where: str) -> DispatchArm:
    arm = row["arm"]
    if arm == "a0":
        return "a0"
    if arm == "a1":
        return "a1"
    raise InvalidDataError(f"{where}: unknown arm {arm!r}")


def _validate_manifest_row(row: Row, where: str) -> DispatchArm:
    """The manifest's own labels: a known arm, the dispatch mode that arm runs,
    and a clean exit code. A failed step is never judged."""
    arm = _manifest_arm(row, where)
    if row["dispatch_mode"] != ARM_MODE[arm]:
        raise InvalidDataError(
            f"{where}: manifest dispatch_mode {row['dispatch_mode']!r}, expected {ARM_MODE[arm]!r}"
        )
    if row["rc"] != "0":
        raise InvalidDataError(f"{where}: step exited with rc {row['rc']!r}")
    return arm


def _read_step_rows(directory: Path, config: str) -> list[dict[str, str]]:
    is_stop = config == _STOP_CONFIG
    pattern = _STOP_TSV_PATTERN if is_stop else _DEPTH_AB_TSV_PATTERN
    columns = _STEP_COLUMNS if is_stop else (*_STEP_COLUMNS, "depth")
    try:
        rows = read_single_tsv(directory, pattern, columns)
    except ValueError as exc:
        raise IncompleteDataError(str(exc)) from exc
    return rows if is_stop else [row for row in rows if row["depth"] == _LADDER_DEPTH]


def _validate_step_rows(rows: Sequence[Row], arm: DispatchArm, where: str) -> None:
    if len(rows) != EXPECTED_THROUGHPUT_POSITIONS:
        raise InvalidDataError(
            f"{where}: {len(rows)} judged rows, expected {EXPECTED_THROUGHPUT_POSITIONS}"
        )
    for row in rows:
        if row["dispatch_mode"] != ARM_MODE[arm]:
            raise InvalidDataError(
                f"{where}: TSV dispatch_mode {row['dispatch_mode']!r}, expected {ARM_MODE[arm]!r}"
            )
        if row["maia_fifo"].lower() != "true":
            raise InvalidDataError(f"{where}: maia_fifo {row['maia_fifo']!r}, expected true")
        if int(row["maia_peak_inflight"]) > _MAIA_MAX_PEAK_INFLIGHT:
            raise InvalidDataError(
                f"{where}: maia_peak_inflight {row['maia_peak_inflight']!r} above "
                f"{_MAIA_MAX_PEAK_INFLIGHT}"
            )


def _step_metrics(rows: Sequence[Row], manifest_row: Row, where: str) -> StepMetrics:
    wall = math.fsum(float(row["wall_ms"]) for row in rows)
    probe = float(manifest_row["probe_total_ms"])
    if wall <= 0 or probe <= 0:
        raise InvalidDataError(f"{where}: non-positive wall ({wall}) or probe ({probe}) time")
    return {
        "wall_ms": wall,
        "grade_ms": math.fsum(float(row["grade_cpu_ms"]) for row in rows),
        "probe_ms": probe,
        "load1": float(manifest_row["load1"]),
    }


def _load_steps(manifest_path: Path) -> dict[StepKey, StepMetrics]:
    """Every judged manifest row, validated, with its step TSV read. A config
    named `smoke` is ignored; any other unknown config is mislabeled data."""
    steps: dict[StepKey, StepMetrics] = {}
    for row in _read_manifest(manifest_path):
        config = row["config"]
        if config == _SMOKE_CONFIG:
            continue
        where = f"throughput round {row['round']} config {config} arm {row['arm']}"
        if config not in _THROUGHPUT_CONFIGS:
            raise InvalidDataError(f"{where}: unknown config")
        arm = _validate_manifest_row(row, where)
        key: StepKey = (config, int(row["round"]), arm)
        if key in steps:
            raise InvalidDataError(f"{where}: duplicate manifest row")
        rows = _read_step_rows(manifest_path.parent / row["out_dir"], config)
        _validate_step_rows(rows, arm, where)
        steps[key] = _step_metrics(rows, row, where)
    return steps


def _geometric_mean(values: Sequence[float]) -> float:
    return math.exp(math.fsum(math.log(v) for v in values) / len(values))


def _grade_ratio(a0: StepMetrics, a1: StepMetrics) -> float | None:
    """`(W_a1 / G_a1) / (W_a0 / G_a0)`, wall normalized by the arm's own summed
    grade elapsed time. Report-only: contention inflates grade elapsed in
    continuous mode and flatters this ratio (RESEARCH Pitfall 5)."""
    if a0["grade_ms"] <= 0 or a1["grade_ms"] <= 0:
        return None
    return (a1["wall_ms"] / a1["grade_ms"]) / (a0["wall_ms"] / a0["grade_ms"])


def _config_throughput(config: str, steps: Mapping[StepKey, StepMetrics]) -> ConfigThroughput:
    rounds = sorted(
        {r for (c, r, arm) in steps if c == config and arm == "a0" and (c, r, "a1") in steps}
    )
    if len(rounds) < THROUGHPUT_MIN_ROUNDS:
        raise IncompleteDataError(
            f"throughput {config}: {len(rounds)} interleaved rounds with both arms, "
            f"need {THROUGHPUT_MIN_ROUNDS}"
        )
    pairs = [(steps[(config, r, "a0")], steps[(config, r, "a1")]) for r in rounds]
    ratios = [
        (a1["wall_ms"] / a1["probe_ms"]) / (a0["wall_ms"] / a0["probe_ms"]) for a0, a1 in pairs
    ]
    raw_ratios = [a1["wall_ms"] / a0["wall_ms"] for a0, a1 in pairs]
    grade_ratios = [_grade_ratio(a0, a1) for a0, a1 in pairs]
    grade_values = [g for g in grade_ratios if g is not None]
    geometric_mean = _geometric_mean(ratios)
    return {
        "rounds": rounds,
        "ratios": ratios,
        "raw_ratios": raw_ratios,
        "grade_ratios": grade_ratios,
        "a0_normalized_walls": [a0["wall_ms"] / a0["probe_ms"] for a0, _ in pairs],
        "geometric_mean": geometric_mean,
        "gain": 1 - geometric_mean,
        "raw_geometric_mean": _geometric_mean(raw_ratios),
        "grade_geometric_mean": (
            _geometric_mean(grade_values) if len(grade_values) == len(grade_ratios) else None
        ),
    }


def _ship_bar(configs: Mapping[str, ConfigThroughput]) -> ShipBar:
    """D-04 as amended by D-17: a gain of at least `THROUGHPUT_SHIP_GAIN` on
    the bot-move path OR on analysis-400, AND neither regressing beyond
    `THROUGHPUT_MAX_RATIO`. Judged on the probe-normalized geometric mean."""
    gains: dict[str, float] = {config: configs[config]["gain"] for config in SHIP_BAR_CONFIGS}
    ratios: dict[str, float] = {
        config: configs[config]["geometric_mean"] for config in SHIP_BAR_CONFIGS
    }
    gain_met = any(gain >= THROUGHPUT_SHIP_GAIN for gain in gains.values())
    no_regression = all(ratio <= THROUGHPUT_MAX_RATIO for ratio in ratios.values())
    return {
        "gain_met": gain_met,
        "no_regression": no_regression,
        "passed": gain_met and no_regression,
        "gains": gains,
        "ratios": ratios,
    }


def evaluate_throughput(manifest_path: Path) -> ThroughputResult:
    """Read the interleaved session's manifest and every step TSV, validate them
    (dispatch_mode matches the arm, one-in-flight FIFO Maia, rc 0, 16 positions)
    and judge the ship bar. Raises `IncompleteDataError` below
    `THROUGHPUT_MIN_ROUNDS` interleaved rounds for any judged config."""
    steps = _load_steps(manifest_path)
    configs: dict[str, ConfigThroughput] = {
        config: _config_throughput(config, steps) for config in _THROUGHPUT_CONFIGS
    }
    warnings = [
        f"round {r} {config} {arm} load1={metrics['load1']:.2f} >= {LOAD_GATE_MAX}"
        for (config, r, arm), metrics in sorted(steps.items())
        if metrics["load1"] >= LOAD_GATE_MAX
    ]
    return {"configs": configs, "ship_bar": _ship_bar(configs), "load_warnings": warnings}


def evaluate_pool2(configs: Mapping[str, ConfigThroughput]) -> dict[str, Pool2Result]:
    """D-04: the Node pool-2 configs must not regress beyond their measured
    noise. `noise = max over rounds |A0_r / median(A0) - 1|` on the
    probe-normalized A0 walls of the same interleaved session; a config passes
    iff `median(ratio_r) <= 1 + max(noise, POOL2_MIN_TOLERANCE)`."""
    results: dict[str, Pool2Result] = {}
    for config in POOL2_CONFIGS:
        walls = configs[config]["a0_normalized_walls"]
        median_wall = statistics.median(walls)
        noise = max(abs(wall / median_wall - 1) for wall in walls)
        median_ratio = statistics.median(configs[config]["ratios"])
        tolerance = 1 + max(noise, POOL2_MIN_TOLERANCE)
        results[config] = {
            "median_ratio": median_ratio,
            "noise": noise,
            "tolerance": tolerance,
            "passed": median_ratio <= tolerance,
        }
    return results


class ThroughputGate(TypedDict):
    throughput: ThroughputResult
    pool2: dict[str, Pool2Result]


def run_throughput_gate(data_dir: Path) -> ThroughputGate:
    throughput = evaluate_throughput(_manifest_path(data_dir))
    return {"throughput": throughput, "pool2": evaluate_pool2(throughput["configs"])}


# ==============================================================================
# WebGPU — D-07 (the one blocking point of the WebGPU measurement)
# ==============================================================================

_WEBGPU_BACKEND = "webgpu"
_WEBGPU_JUDGED_LEG = "interleaved"
_WEBGPU_ROUND_LEG = "round"
_BOT_ROW_KEYS = ("round", "mode", "modeObserved", "positionId", "wallMs", "nodes", "backend")
_BOT_MODES = ("round", "continuous")


class WebgpuResult(TypedDict):
    leg: str
    rounds: list[int]
    #: Per round: sum of continuous bot-move wall over sum of round wall.
    ratios: list[float]
    median_ratio: float
    max_ratio: float
    passed: bool
    maia_latency: list[dict[str, Any]]


class RoundLegReport(TypedDict):
    """The early round-mode-only leg: report-only (D-07), never judged."""

    status: Literal["ok", "absent", "unreadable"]
    reason: str | None
    maia_latency: list[dict[str, Any]]
    round_rows: int


def _load_bench_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise IncompleteDataError(f"engine-bench JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidDataError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(payload, dict) or payload.get("schema") != WEBGPU_SCHEMA:
        raise InvalidDataError(f"{path}: schema is not {WEBGPU_SCHEMA!r}")
    return payload


def _bench_list(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise InvalidDataError(f"engine-bench JSON: {key!r} is not a list of objects")
    return rows


def _validate_bot_row(row: Mapping[str, Any]) -> None:
    """Every judged row is on the WebGPU backend and ran the mode it claims:
    a wasm row measures the wrong Maia, an unobserved mode the wrong loop."""
    missing = [key for key in _BOT_ROW_KEYS if key not in row]
    where = f"botMove round {row.get('round')} position {row.get('positionId')}"
    if missing:
        raise InvalidDataError(f"{where}: missing key(s) {missing}")
    if row["mode"] not in _BOT_MODES:
        raise InvalidDataError(f"{where}: unknown mode {row['mode']!r}")
    if row["modeObserved"] != row["mode"]:
        raise InvalidDataError(
            f"{where}: modeObserved {row['modeObserved']!r} != requested mode {row['mode']!r}"
        )
    if row["backend"] != _WEBGPU_BACKEND:
        raise InvalidDataError(f"{where}: backend {row['backend']!r}, expected {_WEBGPU_BACKEND!r}")


def _group_bot_rows(
    rows: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, float]]]:
    """round -> mode -> positionId -> wallMs."""
    grouped: dict[int, dict[str, dict[str, float]]] = {}
    for row in rows:
        walls = grouped.setdefault(int(row["round"]), {}).setdefault(row["mode"], {})
        if row["positionId"] in walls:
            raise InvalidDataError(
                f"botMove round {row['round']} mode {row['mode']}: duplicate position "
                f"{row['positionId']!r}"
            )
        walls[row["positionId"]] = float(row["wallMs"])
    return grouped


def _round_wall_ratio(modes: Mapping[str, Mapping[str, float]], round_number: int) -> float:
    round_walls, cont_walls = modes["round"], modes["continuous"]
    if set(round_walls) != set(cont_walls):
        raise InvalidDataError(
            f"botMove round {round_number}: round and continuous cover different positions"
        )
    return math.fsum(cont_walls.values()) / math.fsum(round_walls.values())


def evaluate_webgpu(json_path: Path) -> WebgpuResult:
    """D-07: continuous/round bot-move wall ratio on the WebGPU machine, the
    median over at least `WEBGPU_MIN_ROUNDS` interleaved rounds, must be at most
    `WEBGPU_MAX_RATIO`. Only `interleaved`-leg rows on the `webgpu` backend whose
    observed mode equals the requested mode are admissible."""
    payload = _load_bench_json(json_path)
    if payload.get("leg") != _WEBGPU_JUDGED_LEG:
        raise InvalidDataError(
            f"{json_path}: leg {payload.get('leg')!r}, the judged leg is {_WEBGPU_JUDGED_LEG!r}"
        )
    rows = _bench_list(payload, "botMove")
    for row in rows:
        _validate_bot_row(row)
    grouped = _group_bot_rows(rows)
    complete = {r: modes for r, modes in grouped.items() if all(m in modes for m in _BOT_MODES)}
    if len(complete) < WEBGPU_MIN_ROUNDS:
        raise IncompleteDataError(
            f"{json_path}: {len(complete)} rounds with both modes, need {WEBGPU_MIN_ROUNDS}"
        )
    rounds = sorted(complete)
    ratios = [_round_wall_ratio(complete[r], r) for r in rounds]
    median_ratio = statistics.median(ratios)
    return {
        "leg": _WEBGPU_JUDGED_LEG,
        "rounds": rounds,
        "ratios": ratios,
        "median_ratio": median_ratio,
        "max_ratio": WEBGPU_MAX_RATIO,
        "passed": median_ratio <= WEBGPU_MAX_RATIO,
        "maia_latency": _bench_list(payload, "maiaLatency"),
    }


def read_webgpu_round_leg(json_path: Path) -> RoundLegReport:
    """The early round-only leg (report-only): Maia latency table and row count.
    Lenient by design: it can never change the mechanical outcome."""
    if not json_path.is_file():
        return {"status": "absent", "reason": None, "maia_latency": [], "round_rows": 0}
    try:
        payload = _load_bench_json(json_path)
        if payload.get("leg") != _WEBGPU_ROUND_LEG:
            raise InvalidDataError(f"leg {payload.get('leg')!r}, expected {_WEBGPU_ROUND_LEG!r}")
        return {
            "status": "ok",
            "reason": None,
            "maia_latency": _bench_list(payload, "maiaLatency"),
            "round_rows": len(_bench_list(payload, "botMove")),
        }
    except ValueError as exc:
        return {"status": "unreadable", "reason": str(exc), "maia_latency": [], "round_rows": 0}


# ==============================================================================
# Calibration — D-15 (226's powered machinery, unchanged)
# ==============================================================================


class CalibrationResult(TypedDict):
    powered: calib.PoweredVerdict
    refit_if_shipped: RefitDecision227


def evaluate_calibration(verdict_json: Path) -> CalibrationResult:
    """A1-vs-A0 `ParityVerdictResult` JSON through 226's `powered_verdict` with
    the frozen thresholds and z-guard, turned into `refit_if_shipped`: escalate
    on a void comparison, refit on a real (powered) shift, else no-refit."""
    if not verdict_json.is_file():
        raise IncompleteDataError(f"calibration verdict not found: {verdict_json}")
    parity = calib.load_parity_verdict(verdict_json)
    thresholds: dict[Family, float] = {
        "maia": CALIBRATION_THRESHOLD_MAIA,
        "sf": CALIBRATION_THRESHOLD_SF,
    }
    try:
        powered = calib.powered_verdict("a1", parity, thresholds, SHAPE_GUARD_Z)
    except (KeyError, TypeError) as exc:
        raise InvalidDataError(f"{verdict_json}: malformed parity verdict ({exc!r})") from exc
    if powered["validity"] == "void":
        decision: RefitDecision227 = "escalate"
    elif powered["real_shift"]:
        decision = "refit"
    else:
        decision = "no-refit"
    return {"powered": powered, "refit_if_shipped": decision}


# ==============================================================================
# Composed verdict — D-08, D-04, D-00
# ==============================================================================


class WebgpuGate(TypedDict):
    judged: WebgpuResult
    round_leg: RoundLegReport


class GatesVerdict(TypedDict):
    status: Literal["complete"]
    #: Mechanical outcome; the OWNER decides ship or hold from the evidence (D-00).
    mechanical: Mechanical
    reasons: list[str]
    #: D-08: true iff D-01 or D-03 fails in any judged cell.
    virtual_loss_trigger: bool
    refit_if_shipped: RefitDecision227
    mq: MqGateResult
    throughput: ThroughputResult
    pool2: dict[str, Pool2Result]
    webgpu: WebgpuGate
    calibration: CalibrationResult


def _mq_reasons(mq: MqGateResult) -> list[str]:
    reasons: list[str] = []
    for stop, cell in mq["cells"].items():
        if not cell["pass_d01"]:
            reasons.append(
                f"MQ {stop}: D-01 failed (D={cell['decision_d']:.6f} below -{cell['margin']:.6f})"
            )
        if not cell["pass_d03"]:
            reasons.append(
                f"MQ {stop}: D-03 failed (net regressions {cell['net']} above "
                f"allowance {cell['allowance']})"
            )
    return reasons


def _throughput_reasons(
    throughput: ThroughputResult, pool2: Mapping[str, Pool2Result]
) -> list[str]:
    reasons: list[str] = []
    bar = throughput["ship_bar"]
    if not bar["gain_met"]:
        gains = ", ".join(f"{config}={gain:.3f}" for config, gain in bar["gains"].items())
        reasons.append(
            f"throughput: ship bar not met (gain {gains}; need >= {THROUGHPUT_SHIP_GAIN} on either)"
        )
    for config, ratio in bar["ratios"].items():
        if ratio > THROUGHPUT_MAX_RATIO:
            reasons.append(
                f"throughput: {config} ratio {ratio:.4f} above the no-regression bar "
                f"{THROUGHPUT_MAX_RATIO}"
            )
    for config, result in pool2.items():
        if not result["passed"]:
            reasons.append(
                f"pool-2 {config}: median ratio {result['median_ratio']:.4f} above tolerance "
                f"{result['tolerance']:.4f}"
            )
    return reasons


def _webgpu_reasons(webgpu: WebgpuResult) -> list[str]:
    if webgpu["passed"]:
        return []
    return [
        f"WebGPU: continuous/round bot-move wall ratio {webgpu['median_ratio']:.4f} above "
        f"{webgpu['max_ratio']} (D-07)"
    ]


def run_gates(data_dir: Path) -> GatesVerdict:
    """Compose every judged input. Any missing input raises
    `IncompleteDataError` and any untrustworthy one `InvalidDataError`, so a
    verdict exists only when everything it rests on does. `mechanical` is
    ship-eligible iff both MQ cells pass D-01 and D-03, the throughput ship bar
    is met, every pool-2 config passes and the WebGPU point passes.
    Calibration never blocks: it decides the refit."""
    mq = run_mq_gate(data_dir)
    throughput_gate = run_throughput_gate(data_dir)
    webgpu: WebgpuGate = {
        "judged": evaluate_webgpu(data_dir / "webgpu" / "continuous-leg.json"),
        "round_leg": read_webgpu_round_leg(data_dir / "webgpu" / "round-leg.json"),
    }
    calibration = evaluate_calibration(data_dir / "gate" / "calibration" / "verdict-a1-vs-a0.json")
    reasons = [
        *_mq_reasons(mq),
        *_throughput_reasons(throughput_gate["throughput"], throughput_gate["pool2"]),
        *_webgpu_reasons(webgpu["judged"]),
    ]
    return {
        "status": "complete",
        "mechanical": "hold" if reasons else "ship-eligible",
        "reasons": reasons,
        "virtual_loss_trigger": mq["virtual_loss_trigger"],
        "refit_if_shipped": calibration["refit_if_shipped"],
        "mq": mq,
        "throughput": throughput_gate["throughput"],
        "pool2": throughput_gate["pool2"],
        "webgpu": webgpu,
        "calibration": calibration,
    }


# ==============================================================================
# Printing
# ==============================================================================


def _fmt(value: float | None, spec: str = ".6f") -> str:
    return "n/a" if value is None else format(value, spec)


def _print_tripwire(result: TripwireResult) -> None:
    for stop, mode in result["modes"].items():
        print(f"TRIPWIRE {stop} rows={mode['rows']} diffs={len(mode['diffs'])}")
    for stop, mode in result["modes"].items():
        for diff in mode["diffs"]:
            print(f"TRIPWIRE DIFF {stop} {diff}")
    print("TRIPWIRE PASS" if result["passed"] else "TRIPWIRE FAIL")


def _print_report_only(prefix: str, stop: str, cell: ReportOnlyCell) -> None:
    if cell["status"] != "ok":
        print(f"{prefix} {stop} status={cell['status']} reason={cell['reason']}")
        return
    print(
        f"{prefix} {stop} status=ok positions={cell['positions']} repeats={cell['repeats']} "
        f"D={_fmt(cell['signed_mean'])} round_reg={_fmt(cell['round_regressions'], '.3f')} "
        f"cont_reg={_fmt(cell['continuous_regressions'], '.3f')} net={_fmt(cell['net'], '.3f')} "
        "(report-only)"
    )


def print_mq_gate(result: MqGateResult) -> None:
    for stop, cell in result["cells"].items():
        print(
            f"MQ {stop} D={cell['decision_d']:.6f} margin={cell['margin']:.6f} "
            f"d01={'pass' if cell['pass_d01'] else 'fail'} net={cell['net']} "
            f"allowance={cell['allowance']} d03={'pass' if cell['pass_d03'] else 'fail'}"
        )
    for stop, cell in result["cells"].items():
        report = cell["report"]
        print(
            f"MQ-REPORT {stop} bootstrap_lcb={report['bootstrap_lcb']:.6f} "
            f"k_unstable={report['k_unstable']} "
            f"unsigned_mean_abs_des={report['unsigned_mean_abs_des']:.6f} "
            f"mcnemar_p={_fmt(report['mcnemar_p'], '.4f')} "
            f"analysis_d={report['analysis_d']:.6f} "
            f"margin_flips={_fmt(report['margin_flips'], '.2f')} "
            f"round_repeat_disagreement={report['round_repeat_disagreement_positions']}/"
            f"{cell['positions']} "
            f"({report['round_repeat_disagreement_rate']:.4f}) (report-only)"
        )
    for stop, clear in result["clear"].items():
        _print_report_only("MQ-CLEAR", stop, clear)
    for stop, a400 in result["a400"].items():
        _print_report_only("MQ-A400", stop, a400)
    print(f"VIRTUAL-LOSS-TRIGGER {str(result['virtual_loss_trigger']).lower()}")


def print_throughput_gate(gate: ThroughputGate) -> None:
    throughput = gate["throughput"]
    for config, result in throughput["configs"].items():
        print(
            f"THROUGHPUT {config} rounds={len(result['rounds'])} "
            f"ratio={result['geometric_mean']:.6f} gain={result['gain']:.6f} "
            f"raw_ratio={result['raw_geometric_mean']:.6f} "
            f"grade_ratio={_fmt(result['grade_geometric_mean'])} (raw and grade report-only)"
        )
        for round_number, ratio in zip(result["rounds"], result["ratios"], strict=True):
            print(f"THROUGHPUT-ROUND {config} r{round_number} ratio={ratio:.6f}")
    bar = throughput["ship_bar"]
    print(
        f"THROUGHPUT-BAR gain_met={str(bar['gain_met']).lower()} "
        f"no_regression={str(bar['no_regression']).lower()} passed={str(bar['passed']).lower()}"
    )
    for config, pool2 in gate["pool2"].items():
        print(
            f"POOL2 {config} median_ratio={pool2['median_ratio']:.6f} noise={pool2['noise']:.6f} "
            f"tolerance={pool2['tolerance']:.6f} {'pass' if pool2['passed'] else 'fail'}"
        )
    for warning in throughput["load_warnings"]:
        print(f"LOAD-WARNING {warning} (report-only)")


def _print_maia_latency(prefix: str, table: Sequence[Mapping[str, Any]]) -> None:
    for row in table:
        print(
            f"{prefix} backend={row.get('backend')} condition={row.get('condition')} "
            f"available={row.get('available')} n={row.get('n')} "
            f"median_ms={row.get('medianMs')} p90_ms={row.get('p90Ms')} (report-only)"
        )


def print_webgpu(result: WebgpuResult) -> None:
    print(
        f"WEBGPU rounds={len(result['rounds'])} median_ratio={result['median_ratio']:.6f} "
        f"max={result['max_ratio']} {'pass' if result['passed'] else 'fail'}"
    )
    for round_number, ratio in zip(result["rounds"], result["ratios"], strict=True):
        print(f"WEBGPU-ROUND r{round_number} ratio={ratio:.6f}")
    _print_maia_latency("WEBGPU-MAIA", result["maia_latency"])


def print_gates(verdict: GatesVerdict) -> None:
    print_mq_gate(verdict["mq"])
    print_throughput_gate({"throughput": verdict["throughput"], "pool2": verdict["pool2"]})
    print_webgpu(verdict["webgpu"]["judged"])
    round_leg = verdict["webgpu"]["round_leg"]
    print(
        f"WEBGPU-ROUND-LEG status={round_leg['status']} rows={round_leg['round_rows']} (report-only)"
    )
    _print_maia_latency("WEBGPU-ROUND-LEG-MAIA", round_leg["maia_latency"])
    powered = verdict["calibration"]["powered"]
    print(
        f"CALIBRATION validity={powered['validity']} real_shift={powered['real_shift']} "
        f"maia_shift={powered['maia']['pooled_shift']:.3f} sf_shift={powered['sf']['pooled_shift']:.3f}"
    )
    print(f"REFIT-IF-SHIPPED {verdict['refit_if_shipped']}")
    print(f"GATES mechanical={verdict['mechanical']}")
    for reason in verdict["reasons"]:
        print(f"REASON {reason}")
    print("The owner decides ship or hold from this evidence (D-00, D-08).")


# ==============================================================================
# CLI
# ==============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tripwire = subparsers.add_parser(
        "tripwire",
        help="Strict MQ equality, used at --hash clear (worker vs main-thread Maia, "
        "parity-clear); not a warm-hash gate",
    )
    tripwire.add_argument("--mq-dir", required=True)
    tripwire.add_argument("--baseline-dir", default=BASELINE_A21S_DIR)

    mq = subparsers.add_parser("mq", help="Judge both MQ cells: D-01 and D-03")
    mq.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    throughput = subparsers.add_parser(
        "throughput", help="Judge the interleaved throughput session and the pool-2 configs (D-17)"
    )
    throughput.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    webgpu = subparsers.add_parser("webgpu", help="Judge the WebGPU continuous leg (D-07)")
    webgpu.add_argument("--json", required=True)

    gates = subparsers.add_parser(
        "gates", help="Compose every judged input into the mechanical verdict"
    )
    gates.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    gates.add_argument("--out-json", default=DEFAULT_VERDICT_JSON)
    return parser


def _write_verdict_json(verdict: GatesVerdict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "tripwire":
        tripwire = evaluate_tripwire(Path(args.mq_dir), Path(args.baseline_dir))
        _print_tripwire(tripwire)
        return 0 if tripwire["passed"] else EXIT_INVALID
    if args.command == "mq":
        print_mq_gate(run_mq_gate(Path(args.data_dir)))
        return 0
    if args.command == "throughput":
        print_throughput_gate(run_throughput_gate(Path(args.data_dir)))
        return 0
    if args.command == "webgpu":
        print_webgpu(evaluate_webgpu(Path(args.json)))
        return 0
    if args.command == "gates":
        # The verdict JSON is written only after every judged input was read
        # and validated: an incomplete or invalid run leaves no verdict behind.
        verdict = run_gates(Path(args.data_dir))
        _write_verdict_json(verdict, Path(args.out_json))
        print_gates(verdict)
        return 0
    return EXIT_INVALID


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except IncompleteDataError as exc:
        print(f"ERROR (incomplete): {exc}")
        return EXIT_INCOMPLETE
    except ValueError as exc:
        print(f"ERROR (invalid): {exc}")
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
