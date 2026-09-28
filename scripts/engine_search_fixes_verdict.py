"""engine_search_fixes_verdict.py — Phase 225 gate verdict.

The machine-readable twin of `reports/engine-search-fixes-225/accept-rule.md`
(D-11): every threshold constant below carries the exact number from that
document and is NOT reachable from any CLI flag, environment variable, or
config file. The only legitimate way to change one is to edit this file and
the accept-rule doc together, before any gate arm runs.

Reads the pinned per-arm data layout under `reports/data/engine-search-fixes-225/`
(one directory per arm — `a0`, `a2`, `a21`, `final` — each holding the
throughput/move-quality/stop-rule TSVs plus a shared `calibration/` directory
of `calibration_parity_verdict.py`-shaped verdict JSONs) and renders every
Phase 225 gate criterion mechanically: throughput T-50/T-400 (A2 vs A0), move
quality MQ-2 (A2 vs A0, stop rule off) and MQ-1 (A21 vs A2, stop rule on),
stop rule S1/S2 (A21 vs A2), the calibration fail-branch table (D-13
amended), then the per-item ship/hold mapping (D-14). It never reports a pass
on missing or unconfirmed data (T-225-03) — a missing TSV, a duplicate TSV,
an unrerun move-quality flip, or a missing required calibration file all make
`gates` exit non-zero with `status: incomplete`.

stdlib-only (`argparse`/`csv`/`json`/`statistics`/`pathlib`) — no numpy/scipy,
matching `calibration_anchor_fit.py`'s and `calibration_parity_verdict.py`'s
convention. Standalone research tool (`scripts/`, not `app/`) — exempt from
CLAUDE.md's Sentry-capture rules, which apply only to `app/services` and
`app/routers`.

Usage:
    uv run python scripts/engine_search_fixes_verdict.py gates \\
        --data-dir reports/data/engine-search-fixes-225 \\
        [--out-json reports/engine-search-fixes-225/verdict.json]

    uv run python scripts/engine_search_fixes_verdict.py reruns \\
        --data-dir reports/data/engine-search-fixes-225

    uv run python scripts/engine_search_fixes_verdict.py branch \\
        --data-dir reports/data/engine-search-fixes-225

    uv run python scripts/engine_search_fixes_verdict.py cells-to-json \\
        --cells-tsv reports/data/engine-search-fixes-225/a0/a0-cells.tsv \\
        --out-json reports/data/engine-search-fixes-225/calibration/a0-cells.json
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict

import calibration_anchor_fit as anchor_fit
from calibration_parity_verdict import (
    CellKey,
    CellStats,
    ParityVerdictResult,
    Verdict,
    fit_new_cells,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# Frozen constants (D-11) — transcribed verbatim from
# reports/engine-search-fixes-225/accept-rule.md. Fixed BEFORE any gate arm
# ran; not editable after, and not reachable from any CLI flag, environment
# variable, or config file.
# ==============================================================================

#: The two judged budgets (bot 50/c4, analysis 400/c4) — D-13's throughput arm.
THROUGHPUT_BUDGETS = (50, 400)
#: No-regression bound with 5% idle-box wall noise (item 2 is a confirmed bug
#: fix expected to LOWER wall clock, so this only catches a real slowdown).
THROUGHPUT_MAX_WALL_RATIO = 1.05
#: SEED-126's four canonical positions widened to 16 via --openings 12
#: (reports/continuous-dispatch/accept-rule.md §1), reused verbatim here.
EXPECTED_THROUGHPUT_POSITIONS = 16
#: Same 16-position set for the stop-rule arm.
EXPECTED_STOP_POSITIONS = 16
#: fixtures/engine/maia-blindness.tsv — 12 positions (Phase 195 §4b).
EXPECTED_MQ_POSITIONS = 12
#: leaf-wdl accept rule §4b margin, expected-score units.
MQ_REGRESSION_MARGIN = 0.05
#: computeThinkDeadlineMs at the 5+3 preset full clock: 300000/30 + 3000*0.7
#: (RESEARCH C-7) — the tightest common-preset deadline not already binding at A0.
STOP_RULE_MAX_WALL_MS = 12_100
#: D-13 amended S2: the guard must not effectively disable the clear-winner branch.
STOP_RULE_MIN_EARLY_STOP_RETENTION = 0.5
#: Operationalizes D-13's "notable shift": a holds verdict within this fraction
#: of its own pooled threshold, in either family, is a near miss (report-only).
CALIBRATION_NEAR_MISS_FRACTION = 0.75

DEFAULT_DATA_DIR = str(_REPO_ROOT / "reports" / "data" / "engine-search-fixes-225")
DEFAULT_VERDICT_JSON = str(_REPO_ROOT / "reports" / "engine-search-fixes-225" / "verdict.json")
#: `gates` returns this when anything is missing or a move-quality flip needs
#: a rerun — status is `incomplete`, never a silent pass on absent data.
EXIT_INCOMPLETE = 2

_THROUGHPUT_TSV_PATTERN = "engine-grading-depth-ab-*.tsv"
_THROUGHPUT_REQUIRED_COLUMNS = (
    "position",
    "depth",
    "wall_ms",
    "grade_cpu_ms",
    "nodes_evaluated",
    "maia_peak_inflight",
    "maia_fifo",
)
_MQ_TSV_PATTERN = "engine-move-quality-*.tsv"
_MQ_REQUIRED_COLUMNS = ("id", "delta_bot", "verdict_bot", "delta_analysis", "verdict_analysis")
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

ItemOutcome = Literal["ship", "hold"]
CalibrationBranch = Literal["none", "report-only", "decision"]
GateStatus = Literal["complete", "incomplete"]


class ThroughputResult(TypedDict):
    budget: int
    passed: bool
    ratio: float
    a0_wall_ms: float
    a2_wall_ms: float
    grade_cpu_ratio: float
    per_position_ratio: dict[str, float]
    positions_above_one: list[str]
    nodes_evaluated_mismatches: list[str]


class MoveQualityResult(TypedDict):
    criterion: str
    status: Literal["evaluated", "rerun-required"]
    passed: bool | None
    base_regressions: int
    candidate_regressions: int
    confirmed_regressions: int
    unconfirmed_flip_ids: list[str]
    rerun_required_ids: list[str]
    analysis_base_regressions: int
    analysis_candidate_regressions: int


class StopRuleResult(TypedDict):
    s1_passed: bool
    a21_max_wall_ms: float
    s2_passed: bool
    s2_trivial: bool
    a2_early_stops: int
    a21_early_stops: int
    median_nodes_at_stop: dict[str, float]
    p90_nodes_at_stop: dict[str, float]
    deadline_exposure: dict[str, float]


class CalibrationAttribution(TypedDict):
    a2_vs_a0: Verdict | None
    a21_vs_a2: Verdict | None


class CalibrationDecision(TypedDict):
    branch: CalibrationBranch
    item2_pass: bool
    item1_pass: bool
    baseline_drift: bool | None
    attribution: CalibrationAttribution
    follow_up_seed_recommended: bool


class ItemDecisions(TypedDict):
    item2: ItemOutcome
    item1: ItemOutcome
    item3: Literal["independent"]


class GateVerdict(TypedDict):
    status: GateStatus
    missing: list[str]
    rerun_required: list[str]
    throughput: dict[str, ThroughputResult | None]
    move_quality: dict[str, MoveQualityResult | None]
    stop_rule: StopRuleResult | None
    calibration: CalibrationDecision | None
    calibration_branch: CalibrationBranch | None
    items: ItemDecisions | None


# ==============================================================================
# TSV input readers (T-225-03 — never crash silently, never pass on absent data)
# ==============================================================================


def read_single_tsv(
    directory: Path, pattern: str, required_columns: Sequence[str]
) -> list[dict[str, str]]:
    """Reads the ONE file matching `pattern` in `directory`. Raises ValueError
    (naming the directory and pattern) for zero or several matches, and
    ValueError (naming the directory, pattern, and column) for a missing
    required column."""
    matches = sorted(directory.glob(pattern)) if directory.is_dir() else []
    if len(matches) != 1:
        raise ValueError(
            f"read_single_tsv: expected exactly one file matching {pattern!r} in "
            f"{directory}, found {len(matches)}"
        )
    path = matches[0]
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        missing_columns = [c for c in required_columns if c not in fieldnames]
        if missing_columns:
            raise ValueError(
                f"read_single_tsv: {path} (pattern {pattern!r} in {directory}) is "
                f"missing required column(s): {missing_columns!r}"
            )
        return list(reader)


# ==============================================================================
# Throughput (T-50 / T-400)
# ==============================================================================


def _ladder_rows(rows: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    return [row for row in rows if row["depth"] == "ladder"]


def evaluate_throughput(
    a0_rows: Sequence[Mapping[str, str]], a2_rows: Sequence[Mapping[str, str]], budget: int
) -> ThroughputResult:
    a0_ladder = _ladder_rows(a0_rows)
    a2_ladder = _ladder_rows(a2_rows)
    for arm_label, ladder in (("a0", a0_ladder), ("a2", a2_ladder)):
        if len(ladder) != EXPECTED_THROUGHPUT_POSITIONS:
            raise ValueError(
                f"evaluate_throughput: expected {EXPECTED_THROUGHPUT_POSITIONS} ladder rows "
                f"for {arm_label} at budget {budget}, got {len(ladder)}"
            )
        for row in ladder:
            if row["maia_peak_inflight"] != "1" or row["maia_fifo"] != "true":
                raise ValueError(
                    f"evaluate_throughput: inadmissible ladder row for {arm_label} position "
                    f"{row['position']!r} at budget {budget} (maia_peak_inflight="
                    f"{row['maia_peak_inflight']!r}, maia_fifo={row['maia_fifo']!r}); "
                    "per the continuous-dispatch admissibility rule"
                )

    a0_by_pos = {row["position"]: row for row in a0_ladder}
    a2_by_pos = {row["position"]: row for row in a2_ladder}
    if set(a0_by_pos) != set(a2_by_pos):
        raise ValueError(
            f"evaluate_throughput: position-label mismatch at budget {budget}: "
            f"a0={sorted(a0_by_pos)} a2={sorted(a2_by_pos)}"
        )

    a0_wall_ms = sum(float(row["wall_ms"]) for row in a0_ladder)
    a2_wall_ms = sum(float(row["wall_ms"]) for row in a2_ladder)
    a0_grade_cpu_ms = sum(float(row["grade_cpu_ms"]) for row in a0_ladder)
    a2_grade_cpu_ms = sum(float(row["grade_cpu_ms"]) for row in a2_ladder)
    # Review fix (WR-01): a zero A0 wall sum raised ZeroDivisionError, which escaped
    # run_gates' ValueError net and crashed `gates` instead of recording a missing entry.
    if a0_wall_ms <= 0:
        raise ValueError(f"evaluate_throughput: A0 ladder wall_ms sums to zero at budget {budget}")
    ratio = a2_wall_ms / a0_wall_ms
    grade_cpu_ratio = a2_grade_cpu_ms / a0_grade_cpu_ms if a0_grade_cpu_ms > 0 else 0.0

    per_position_ratio: dict[str, float] = {}
    positions_above_one: list[str] = []
    nodes_evaluated_mismatches: list[str] = []
    for position in sorted(a0_by_pos):
        a0_row = a0_by_pos[position]
        a2_row = a2_by_pos[position]
        a0_pos_wall = float(a0_row["wall_ms"])
        pos_ratio = float(a2_row["wall_ms"]) / a0_pos_wall if a0_pos_wall > 0 else 0.0
        per_position_ratio[position] = pos_ratio
        if pos_ratio > 1.0:
            positions_above_one.append(position)
        if a0_row["nodes_evaluated"] != a2_row["nodes_evaluated"]:
            nodes_evaluated_mismatches.append(position)

    return {
        "budget": budget,
        "passed": ratio <= THROUGHPUT_MAX_WALL_RATIO,
        "ratio": ratio,
        "a0_wall_ms": a0_wall_ms,
        "a2_wall_ms": a2_wall_ms,
        "grade_cpu_ratio": grade_cpu_ratio,
        "per_position_ratio": per_position_ratio,
        "positions_above_one": sorted(positions_above_one),
        "nodes_evaluated_mismatches": sorted(nodes_evaluated_mismatches),
    }


# ==============================================================================
# Move quality (MQ-2 / MQ-1) — RESEARCH Pitfall 8 rerun-confirmation rule
# ==============================================================================


def _mq_regresses(row: Mapping[str, str], delta_col: str, verdict_col: str) -> bool:
    """A row regresses iff `float(delta_col) <= -MQ_REGRESSION_MARGIN`. Raises
    ValueError when that disagrees with `verdict_col` — a margin drift between
    the runner and this twin must never be silently trusted either way."""
    delta = float(row[delta_col])
    computed_regression = delta <= -MQ_REGRESSION_MARGIN
    stated_regression = row[verdict_col] == "regression"
    if computed_regression != stated_regression:
        raise ValueError(
            f"evaluate_move_quality: row {row.get('id')!r} {delta_col}={delta} disagrees "
            f"with {verdict_col}={row[verdict_col]!r} at margin {MQ_REGRESSION_MARGIN}"
        )
    return stated_regression


def _mq_rows_by_id(rows: Sequence[Mapping[str, str]], label: str) -> dict[str, Mapping[str, str]]:
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != EXPECTED_MQ_POSITIONS:
        raise ValueError(
            f"evaluate_move_quality: expected {EXPECTED_MQ_POSITIONS} rows for {label}, "
            f"got {len(by_id)}"
        )
    return by_id


def evaluate_move_quality(
    base_rows: Sequence[Mapping[str, str]],
    cand_rows: Sequence[Mapping[str, str]],
    cand_rerun_rows: Sequence[Mapping[str, str]] | None,
    criterion: str,
) -> MoveQualityResult:
    base_by_id = _mq_rows_by_id(base_rows, f"{criterion} base")
    cand_by_id = _mq_rows_by_id(cand_rows, f"{criterion} candidate")
    if set(base_by_id) != set(cand_by_id):
        raise ValueError(
            f"evaluate_move_quality: {criterion} id-set mismatch: "
            f"base={sorted(base_by_id)} candidate={sorted(cand_by_id)}"
        )

    base_regressed = {
        rid for rid, row in base_by_id.items() if _mq_regresses(row, "delta_bot", "verdict_bot")
    }
    cand_regressed = {
        rid for rid, row in cand_by_id.items() if _mq_regresses(row, "delta_bot", "verdict_bot")
    }
    flips = sorted(cand_regressed - base_regressed)

    analysis_base_regressions = sum(
        1 for row in base_by_id.values() if _mq_regresses(row, "delta_analysis", "verdict_analysis")
    )
    analysis_candidate_regressions = sum(
        1 for row in cand_by_id.values() if _mq_regresses(row, "delta_analysis", "verdict_analysis")
    )

    if flips and cand_rerun_rows is None:
        return {
            "criterion": criterion,
            "status": "rerun-required",
            "passed": None,
            "base_regressions": len(base_regressed),
            "candidate_regressions": len(cand_regressed),
            "confirmed_regressions": len(cand_regressed),
            "unconfirmed_flip_ids": [],
            "rerun_required_ids": flips,
            "analysis_base_regressions": analysis_base_regressions,
            "analysis_candidate_regressions": analysis_candidate_regressions,
        }

    unconfirmed: list[str] = []
    if flips and cand_rerun_rows is not None:
        rerun_by_id = {row["id"]: row for row in cand_rerun_rows}
        for rid in flips:
            rerun_row = rerun_by_id.get(rid)
            if rerun_row is None:
                raise ValueError(
                    f"evaluate_move_quality: {criterion} rerun is missing flipped id {rid!r}"
                )
            if not _mq_regresses(rerun_row, "delta_bot", "verdict_bot"):
                unconfirmed.append(rid)

    confirmed_count = len(cand_regressed) - len(unconfirmed)
    passed = confirmed_count <= len(base_regressed)

    return {
        "criterion": criterion,
        "status": "evaluated",
        "passed": passed,
        "base_regressions": len(base_regressed),
        "candidate_regressions": len(cand_regressed),
        "confirmed_regressions": confirmed_count,
        "unconfirmed_flip_ids": sorted(unconfirmed),
        "rerun_required_ids": [],
        "analysis_base_regressions": analysis_base_regressions,
        "analysis_candidate_regressions": analysis_candidate_regressions,
    }


def required_reruns(data_dir: Path) -> list[tuple[str, str]]:
    """The (arm, mode) pairs whose move-quality flips lack a rerun dir: MQ-2
    compares a0/mq-off with a2/mq-off; MQ-1 compares a2/mq-on with a21/mq-on.

    Bug fix (Phase 225 gate run): this used to pass `None` as the rerun rows, so
    a flip kept being listed as RERUN even after its mq-{mode}-rerun TSV existed,
    and the plan's "repeat until NO RERUNS REQUIRED" loop could never end. It now
    reads the optional rerun dir exactly as `gates` does. No threshold changed.
    """
    reruns: list[tuple[str, str]] = []

    def read_rerun(directory: Path) -> list[dict[str, str]] | None:
        if not directory.is_dir():
            return None
        return read_single_tsv(directory, _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)

    a0_off = read_single_tsv(data_dir / "a0" / "mq-off", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    a2_off = read_single_tsv(data_dir / "a2" / "mq-off", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq2 = evaluate_move_quality(
        a0_off, a2_off, read_rerun(data_dir / "a2" / "mq-off-rerun"), "MQ-2"
    )
    if mq2["status"] == "rerun-required":
        reruns.append(("a2", "off"))

    a2_on = read_single_tsv(data_dir / "a2" / "mq-on", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    a21_on = read_single_tsv(data_dir / "a21" / "mq-on", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq1 = evaluate_move_quality(a2_on, a21_on, read_rerun(data_dir / "a21" / "mq-on-rerun"), "MQ-1")
    if mq1["status"] == "rerun-required":
        reruns.append(("a21", "on"))

    return reruns


# ==============================================================================
# Stop rule (S1 / S2)
# ==============================================================================


def _percentile(values: Sequence[float], pct: int) -> float:
    if len(values) < 2:
        raise ValueError("_percentile: at least 2 values required")
    return statistics.quantiles(values, n=100, method="inclusive")[pct - 1]


def _require_stop_rows(rows: Sequence[Mapping[str, str]], label: str) -> None:
    if len(rows) != EXPECTED_STOP_POSITIONS:
        raise ValueError(
            f"evaluate_stop_rule: expected {EXPECTED_STOP_POSITIONS} rows for {label}, "
            f"got {len(rows)}"
        )
    for row in rows:
        if row["stop_rule"] != "on":
            raise ValueError(
                f"evaluate_stop_rule: {label} row for position {row['position']!r} has "
                f"stop_rule={row['stop_rule']!r}, expected 'on'"
            )


def evaluate_stop_rule(
    a2_rows: Sequence[Mapping[str, str]],
    a21_rows: Sequence[Mapping[str, str]],
    a0_rows: Sequence[Mapping[str, str]] | None,
) -> StopRuleResult:
    _require_stop_rows(a2_rows, "a2")
    _require_stop_rows(a21_rows, "a21")
    a2_positions = {row["position"] for row in a2_rows}
    a21_positions = {row["position"] for row in a21_rows}
    if a2_positions != a21_positions:
        raise ValueError(
            f"evaluate_stop_rule: position-label mismatch: a2={sorted(a2_positions)} "
            f"a21={sorted(a21_positions)}"
        )

    a21_max_wall_ms = max(float(row["wall_ms"]) for row in a21_rows)
    s1_passed = a21_max_wall_ms <= STOP_RULE_MAX_WALL_MS

    a2_early_stops = sum(1 for row in a2_rows if row["stop_reason"] == "early-stop")
    a21_early_stops = sum(1 for row in a21_rows if row["stop_reason"] == "early-stop")
    s2_trivial = a2_early_stops == 0
    s2_passed = (
        True
        if s2_trivial
        else a21_early_stops >= STOP_RULE_MIN_EARLY_STOP_RETENTION * a2_early_stops
    )

    labeled_rows: list[tuple[str, Sequence[Mapping[str, str]]]] = [
        ("a2", a2_rows),
        ("a21", a21_rows),
    ]
    if a0_rows is not None:
        labeled_rows.append(("a0", a0_rows))
    median_nodes_at_stop: dict[str, float] = {}
    p90_nodes_at_stop: dict[str, float] = {}
    for label, rows in labeled_rows:
        values = sorted(float(row["nodes_evaluated_at_stop"]) for row in rows)
        median_nodes_at_stop[label] = statistics.median(values)
        p90_nodes_at_stop[label] = _percentile(values, 90)

    deadline_exposure: dict[str, float] = {}
    for label, rows in (("a2", a2_rows), ("a21", a21_rows)):
        total_exposure = sum(float(row["exposure_snapshots"]) for row in rows)
        total_eligible = sum(float(row["eligible_snapshots"]) for row in rows)
        deadline_exposure[label] = (total_exposure / total_eligible) if total_eligible > 0 else 0.0

    return {
        "s1_passed": s1_passed,
        "a21_max_wall_ms": a21_max_wall_ms,
        "s2_passed": s2_passed,
        "s2_trivial": s2_trivial,
        "a2_early_stops": a2_early_stops,
        "a21_early_stops": a21_early_stops,
        "median_nodes_at_stop": median_nodes_at_stop,
        "p90_nodes_at_stop": p90_nodes_at_stop,
        "deadline_exposure": deadline_exposure,
    }


# ==============================================================================
# Calibration (D-13 amended / RESEARCH C-6): branch classification, the
# pre-registered decision table, and the A0-cells converter for the fail
# branch's attribution comparisons.
# ==============================================================================


def _load_calibration_verdict(path: Path) -> ParityVerdictResult:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or "verdict" not in payload:
        raise ValueError(
            f"_load_calibration_verdict: {path} is not a valid calibration verdict JSON"
        )
    return payload


def _load_calibration_verdict_optional(path: Path) -> ParityVerdictResult | None:
    if not path.is_file():
        return None
    return _load_calibration_verdict(path)


def calibration_branch(primary: ParityVerdictResult) -> CalibrationBranch:
    """fails/void -> decision; holds with |pooled shift| strictly above
    CALIBRATION_NEAR_MISS_FRACTION of its own threshold in either family ->
    report-only; otherwise -> none (D-13 amended, RESEARCH C-6)."""
    if primary["verdict"] in ("fails", "void"):
        return "decision"
    near_miss = False
    for family in ("maia", "sf"):
        pooled = primary[family]["pooled"]
        threshold = pooled["threshold"]
        if threshold > 0 and abs(pooled["shift"]) > CALIBRATION_NEAR_MISS_FRACTION * threshold:
            near_miss = True
    return "report-only" if near_miss else "none"


def _verdict_holds(verdict: ParityVerdictResult | None) -> bool:
    """A missing (None) or void secondary verdict counts as not holds."""
    return verdict is not None and verdict["verdict"] == "holds"


def calibration_item_decisions(
    primary: ParityVerdictResult,
    a0_vs_july: ParityVerdictResult | None,
    a2_vs_july: ParityVerdictResult | None,
    a2_vs_a0: ParityVerdictResult | None,
    a21_vs_a2: ParityVerdictResult | None,
) -> CalibrationDecision:
    """The pre-registered D-13 amended / RESEARCH C-6 decision table for
    whatever `calibration_branch(primary)` classifies:

    - "none": both items pass on the primary verdict alone.
    - "report-only": both items pass on the primary verdict; `a2_vs_a0` and
      `a21_vs_a2` (both REQUIRED — the branch was pre-registered to run) are
      recorded as attribution, and a follow-up seed is recommended when
      either is not holds.
    - "decision": `a0_vs_july` (REQUIRED) decides baseline_drift. With drift,
      item2 passes iff `a2_vs_a0` (REQUIRED) holds, item1 passes iff item2
      passes AND `a21_vs_a2` (REQUIRED) holds. Without drift, item2 passes
      iff `a2_vs_july` (REQUIRED) holds and item1 is always held (A21
      already failed against July).

    Raises ValueError naming the missing file whenever a branch's required
    secondary verdict is None — never silently treats an absent file as a
    pass or a fail.
    """
    branch = calibration_branch(primary)

    if branch == "none":
        return {
            "branch": "none",
            "item2_pass": True,
            "item1_pass": True,
            "baseline_drift": None,
            "attribution": {"a2_vs_a0": None, "a21_vs_a2": None},
            "follow_up_seed_recommended": False,
        }

    if branch == "report-only":
        if a2_vs_a0 is None or a21_vs_a2 is None:
            raise ValueError(
                "calibration_item_decisions: report-only branch requires "
                "calibration/verdict-a2-vs-a0.json and calibration/verdict-a21-vs-a2.json"
            )
        return {
            "branch": "report-only",
            "item2_pass": True,
            "item1_pass": True,
            "baseline_drift": None,
            "attribution": {"a2_vs_a0": a2_vs_a0["verdict"], "a21_vs_a2": a21_vs_a2["verdict"]},
            "follow_up_seed_recommended": not _verdict_holds(a2_vs_a0)
            or not _verdict_holds(a21_vs_a2),
        }

    # branch == "decision"
    if a0_vs_july is None:
        raise ValueError(
            "calibration_item_decisions: decision branch requires calibration/verdict-a0-vs-july.json"
        )
    baseline_drift = not _verdict_holds(a0_vs_july)
    attribution: CalibrationAttribution

    if baseline_drift:
        if a2_vs_a0 is None or a21_vs_a2 is None:
            raise ValueError(
                "calibration_item_decisions: decision branch with baseline drift requires "
                "calibration/verdict-a2-vs-a0.json and calibration/verdict-a21-vs-a2.json"
            )
        item2_pass = _verdict_holds(a2_vs_a0)
        item1_pass = item2_pass and _verdict_holds(a21_vs_a2)
        attribution = {"a2_vs_a0": a2_vs_a0["verdict"], "a21_vs_a2": a21_vs_a2["verdict"]}
    else:
        if a2_vs_july is None:
            raise ValueError(
                "calibration_item_decisions: decision branch without baseline drift requires "
                "calibration/verdict-a2-vs-july.json"
            )
        item2_pass = _verdict_holds(a2_vs_july)
        item1_pass = False  # A21 already failed against July — item1 is held regardless
        attribution = {"a2_vs_a0": None, "a21_vs_a2": None}

    return {
        "branch": "decision",
        "item2_pass": item2_pass,
        "item1_pass": item1_pass,
        "baseline_drift": baseline_drift,
        "attribution": attribution,
        "follow_up_seed_recommended": False,
    }


def cells_to_payload(cells: Mapping[CellKey, CellStats]) -> dict[str, list[dict[str, object]]]:
    """Serializes a `{(bot_elo, bot_blend): CellStats}` mapping into the
    `{"cells": [...]}` shape `calibration_parity_verdict.load_old_cells`
    reads back unchanged — the A0-cells converter for RESEARCH C-6's
    pre-registered fail-branch attribution comparisons."""
    rows: list[dict[str, object]] = []
    for key in sorted(cells):
        cell = cells[key]
        rows.append(
            {
                "bot_elo": cell["bot_elo"],
                "bot_blend": cell["bot_blend"],
                "rating_vs_maia": cell["rating_vs_maia"],
                "ci_vs_maia": list(cell["ci_vs_maia"]),
                "rating_vs_sf": cell["rating_vs_sf"],
                "ci_vs_sf": list(cell["ci_vs_sf"]),
            }
        )
    return {"cells": rows}


# ==============================================================================
# gates / reruns subcommands
# ==============================================================================


def run_gates(data_dir: Path) -> GateVerdict:
    missing: list[str] = []

    def read_required(
        directory: Path, pattern: str, columns: Sequence[str]
    ) -> list[dict[str, str]] | None:
        try:
            return read_single_tsv(directory, pattern, columns)
        except ValueError as exc:
            missing.append(str(exc))
            return None

    def read_optional(
        directory: Path, pattern: str, columns: Sequence[str]
    ) -> list[dict[str, str]] | None:
        if not directory.is_dir():
            return None
        return read_required(directory, pattern, columns)

    throughput: dict[str, ThroughputResult | None] = {}
    for budget in THROUGHPUT_BUDGETS:
        a0_rows = read_required(
            data_dir / "a0" / f"throughput-{budget}",
            _THROUGHPUT_TSV_PATTERN,
            _THROUGHPUT_REQUIRED_COLUMNS,
        )
        a2_rows = read_required(
            data_dir / "a2" / f"throughput-{budget}",
            _THROUGHPUT_TSV_PATTERN,
            _THROUGHPUT_REQUIRED_COLUMNS,
        )
        result: ThroughputResult | None = None
        if a0_rows is not None and a2_rows is not None:
            try:
                result = evaluate_throughput(a0_rows, a2_rows, budget)
            except ValueError as exc:
                missing.append(str(exc))
        throughput[str(budget)] = result

    mq_off_a0 = read_required(data_dir / "a0" / "mq-off", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq_off_a2 = read_required(data_dir / "a2" / "mq-off", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq_off_a2_rerun = read_optional(
        data_dir / "a2" / "mq-off-rerun", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
    )
    mq2: MoveQualityResult | None = None
    if mq_off_a0 is not None and mq_off_a2 is not None:
        try:
            mq2 = evaluate_move_quality(mq_off_a0, mq_off_a2, mq_off_a2_rerun, "MQ-2")
        except ValueError as exc:
            missing.append(str(exc))

    mq_on_a2 = read_required(data_dir / "a2" / "mq-on", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq_on_a21 = read_required(data_dir / "a21" / "mq-on", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS)
    mq_on_a21_rerun = read_optional(
        data_dir / "a21" / "mq-on-rerun", _MQ_TSV_PATTERN, _MQ_REQUIRED_COLUMNS
    )
    mq1: MoveQualityResult | None = None
    if mq_on_a2 is not None and mq_on_a21 is not None:
        try:
            mq1 = evaluate_move_quality(mq_on_a2, mq_on_a21, mq_on_a21_rerun, "MQ-1")
        except ValueError as exc:
            missing.append(str(exc))

    rerun_required: list[str] = []
    if mq2 is not None and mq2["status"] == "rerun-required":
        rerun_required.append("a2 off")
    if mq1 is not None and mq1["status"] == "rerun-required":
        rerun_required.append("a21 on")

    a2_stop = read_required(data_dir / "a2" / "stop", _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
    a21_stop = read_required(data_dir / "a21" / "stop", _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
    a0_stop = read_optional(data_dir / "a0" / "stop", _STOP_TSV_PATTERN, _STOP_REQUIRED_COLUMNS)
    stop_result: StopRuleResult | None = None
    if a2_stop is not None and a21_stop is not None:
        try:
            stop_result = evaluate_stop_rule(a2_stop, a21_stop, a0_stop)
        except ValueError as exc:
            missing.append(str(exc))

    primary_path = data_dir / "calibration" / "verdict-a21-vs-july.json"
    primary: ParityVerdictResult | None = None
    if not primary_path.is_file():
        missing.append(f"required calibration file missing: {primary_path}")
    else:
        try:
            primary = _load_calibration_verdict(primary_path)
        except ValueError as exc:
            missing.append(str(exc))

    branch: CalibrationBranch | None = None
    calibration: CalibrationDecision | None = None
    if primary is not None:
        branch = calibration_branch(primary)
        a0_vs_july = _load_calibration_verdict_optional(
            data_dir / "calibration" / "verdict-a0-vs-july.json"
        )
        a2_vs_july = _load_calibration_verdict_optional(
            data_dir / "calibration" / "verdict-a2-vs-july.json"
        )
        a2_vs_a0 = _load_calibration_verdict_optional(
            data_dir / "calibration" / "verdict-a2-vs-a0.json"
        )
        a21_vs_a2 = _load_calibration_verdict_optional(
            data_dir / "calibration" / "verdict-a21-vs-a2.json"
        )
        try:
            calibration = calibration_item_decisions(
                primary, a0_vs_july, a2_vs_july, a2_vs_a0, a21_vs_a2
            )
        except ValueError as exc:
            missing.append(str(exc))

    items: ItemDecisions | None = None
    t50 = throughput.get(str(THROUGHPUT_BUDGETS[0]))
    t400 = throughput.get(str(THROUGHPUT_BUDGETS[1]))
    if (
        t50 is not None
        and t400 is not None
        and mq2 is not None
        and mq2["passed"] is not None
        and mq1 is not None
        and mq1["passed"] is not None
        and stop_result is not None
        and calibration is not None
    ):
        items = decide_items(t50, t400, mq2, stop_result, mq1, calibration)

    status: GateStatus = (
        "complete" if (not missing and not rerun_required and items is not None) else "incomplete"
    )

    return {
        "status": status,
        "missing": missing,
        "rerun_required": rerun_required,
        "throughput": throughput,
        "move_quality": {"MQ-2": mq2, "MQ-1": mq1},
        "stop_rule": stop_result,
        "calibration": calibration,
        "calibration_branch": branch,
        "items": items,
    }


def decide_items(
    t50: ThroughputResult,
    t400: ThroughputResult,
    mq2: MoveQualityResult,
    stop_result: StopRuleResult,
    mq1: MoveQualityResult,
    calibration: CalibrationDecision,
) -> ItemDecisions:
    """D-14: item 2 ships iff T-50, T-400, MQ-2 and its calibration verdict
    pass; item 1 ships iff item 2 ships and S1, S2, MQ-1 and its calibration
    verdict pass; item 3 is independent of every bot gate."""
    item2_ok = (
        t50["passed"] and t400["passed"] and mq2["passed"] is True and calibration["item2_pass"]
    )
    item2: ItemOutcome = "ship" if item2_ok else "hold"
    item1_ok = (
        item2_ok
        and stop_result["s1_passed"]
        and stop_result["s2_passed"]
        and mq1["passed"] is True
        and calibration["item1_pass"]
    )
    item1: ItemOutcome = "ship" if item1_ok else "hold"
    return {"item2": item2, "item1": item1, "item3": "independent"}


def _print_gate_table(verdict: GateVerdict) -> None:
    print(f"STATUS {verdict['status']}")
    for budget_key, result in verdict["throughput"].items():
        if result is None:
            print(f"T-{budget_key}: MISSING")
        else:
            print(
                f"T-{budget_key}: {'PASS' if result['passed'] else 'FAIL'} ratio={result['ratio']:.4f}"
            )
    for criterion, mq_result in verdict["move_quality"].items():
        if mq_result is None:
            print(f"{criterion}: MISSING")
        elif mq_result["status"] == "rerun-required":
            print(f"{criterion}: RERUN-REQUIRED {mq_result['rerun_required_ids']}")
        else:
            print(f"{criterion}: {'PASS' if mq_result['passed'] else 'FAIL'}")
    stop_result = verdict["stop_rule"]
    if stop_result is None:
        print("S1/S2: MISSING")
    else:
        print(
            f"S1: {'PASS' if stop_result['s1_passed'] else 'FAIL'} max_wall_ms={stop_result['a21_max_wall_ms']:.0f}"
        )
        print(
            f"S2: {'PASS' if stop_result['s2_passed'] else 'FAIL'} "
            f"a2_early={stop_result['a2_early_stops']} a21_early={stop_result['a21_early_stops']}"
        )
    print(f"CALIBRATION_BRANCH: {verdict['calibration_branch']}")
    calibration = verdict["calibration"]
    if calibration is not None:
        print(
            f"CALIBRATION: item2_pass={calibration['item2_pass']} item1_pass={calibration['item1_pass']}"
        )
    items = verdict["items"]
    if items is not None:
        print(f"ITEM2: {items['item2']}")
        print(f"ITEM1: {items['item1']}")
        print(f"ITEM3: {items['item3']}")
    if verdict["missing"]:
        print("MISSING:")
        for entry in verdict["missing"]:
            print(f"  - {entry}")
    if verdict["rerun_required"]:
        print("RERUN REQUIRED:")
        for entry in verdict["rerun_required"]:
            print(f"  RERUN {entry}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gates_parser = subparsers.add_parser(
        "gates", help="Render every Phase 225 gate criterion from the pinned data layout"
    )
    gates_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    gates_parser.add_argument("--out-json", default=DEFAULT_VERDICT_JSON)

    reruns_parser = subparsers.add_parser(
        "reruns",
        help="Print the move-quality reruns required by unconfirmed pass->regression flips",
    )
    reruns_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    branch_parser = subparsers.add_parser(
        "branch",
        help="Print the calibration fail-branch classification (none/report-only/decision)",
    )
    branch_parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    cells_parser = subparsers.add_parser(
        "cells-to-json", help='Fit *-cells.tsv files into a {"cells": [...]} payload for --old-json'
    )
    cells_parser.add_argument("--cells-tsv", action="append", default=None, required=True)
    cells_parser.add_argument("--out-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "gates":
        data_dir = Path(args.data_dir)
        try:
            verdict = run_gates(data_dir)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _print_gate_table(verdict)
        return 0 if verdict["status"] == "complete" else EXIT_INCOMPLETE

    if args.command == "reruns":
        data_dir = Path(args.data_dir)
        try:
            reruns = required_reruns(data_dir)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        if not reruns:
            print("NO RERUNS REQUIRED")
        else:
            for arm, mode in reruns:
                print(f"RERUN {arm} {mode}")
        return 0

    if args.command == "branch":
        data_dir = Path(args.data_dir)
        primary_path = data_dir / "calibration" / "verdict-a21-vs-july.json"
        try:
            primary = _load_calibration_verdict(primary_path)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}")
            return 1
        branch = calibration_branch(primary)
        print(f"CALIBRATION_BRANCH {branch}")
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
