"""Fit the facepalm score by logistic regression on the owner's labels (Phase 250 D-01, D-03; Phase 254).

Reads a committed features table (``facepalm_features.py`` output) and nothing else: no
cache, no database, no Maia. Newton-Raphson (IRLS) logistic regression with an intercept on
the decided labels (1 = fair, 0 = unfair), seeded K-fold cross-validation, a passer table
(fair / unfair counts among rows scoring at or above a threshold, from out-of-fold
predictions), and a ready-to-paste constants block.

Two feature schemas (detected from the header):

- ``legacy``: the committed 2026-11-13 table (``line_loss_N`` columns). The Phase 250 Form A /
  Form B / loss-floor comparison runs unchanged and ``--check-constants`` keeps reproducing
  the pre-refit constants from it.
- ``facts``: the Phase 254 table (both signed 9-slot material arrays, both mate plies, the
  best move's probability and the pre-blunder spread). The fit picks the model shape in three
  deterministic stages (D-06 material form, D-07 spread form, D-08 optional Maia inputs) by
  cross-validated AUC, then the fair share at the cut, then the simpler model, and reports the
  D-13 fair / unfair tables. Candidates are real ``FacepalmModel`` instances scored with the
  shipped twins, so what is fitted is what the app computes.

A ranking, not a probability (D-01): the labels are mostly rule passers, so the fitted values
are not calibrated to all blunders.

Usage::

    uv run python scripts/blunder_check/fit_facepalm.py \
        --features reports/blunder-check/facepalm-features-<date>.tsv --out <report.md>
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, get_args

import numpy as np

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.blunder_check_rules import (  # noqa: E402
    FACEPALM_DRILL_LAMBDA,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
    MaterialForm,
    SpreadForm,
)
from scripts.blunder_check.metrics import MaterialType, material_type  # noqa: E402
from app.services.facepalm_score import (  # noqa: E402
    FACEPALM_MODEL,
    FacepalmFacts,
    FacepalmModel,
    facepalm_score,
    loss_feature,
    missed_feature,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

IRLS_MAX_ITER: int = 50
IRLS_TOL: float = 1e-8
# A coefficient this large means the labels are (nearly) separable by the inputs: the fit is
# not identified and must not be shipped.
SEPARATION_COEF_LIMIT: float = 50.0
CV_FOLDS: int = 10
FIT_SEED: int = 250
# Cut the fit's model selection and fair-share tables use by default. It is the labels' meaning
# (label 1 = "the score should be above 70%", CONTEXT D-23), NOT the shipped FACEPALM_SCORE_MIN:
# the drill cut may sit below it on purpose, and a refit must not depend on where the cut is
# set (--check-constants would otherwise stop reproducing the shipped model once the cut moves).
FIT_SELECTION_THRESHOLD: float = 0.7
FIT_THRESHOLDS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9)
COEF_DECIMALS: int = 4

EXIT_OK: int = 0
EXIT_FIT_ERROR: int = 2
# --check-constants: the refit of the features table differs from the shipped FACEPALM_MODEL.
EXIT_CONSTANTS_MISMATCH: int = 6
# Coefficients are shipped rounded to COEF_DECIMALS (1e-4); a refit matches when every
# coefficient is within this of the shipped value.
CHECK_CONSTANTS_TOLERANCE: float = 1e-4

# Sigmoid input clip: exp(+-500) is representable, beyond that it overflows.
_LOGIT_CLIP: float = 500.0

LABEL_FAIR: float = 1.0
LABEL_UNFAIR: float = 0.0
LABEL_UNDECIDED: float = 0.5

FitForm = Literal["a_log_played", "b_raw_played_binary_loss"]
LossFloorMode = Literal["auto", "none", "0"]
FeatureSchema = Literal["legacy", "facts"]
MATERIAL_TYPES: tuple[MaterialType, ...] = get_args(MaterialType)

# The loss floor of every facts-schema candidate: D-05 fixes loss = max(0, -played_3), and an
# active missed term requires it (FacepalmModel.__post_init__).
FACTS_LOSS_FLOOR: int = 0
# Candidate material forms, simplest first (the first of a full tie wins).
MATERIAL_FORMS: tuple[MaterialForm, ...] = ("combined", "split")
SPREAD_FORMS: tuple[SpreadForm, ...] = ("always", "loss_only", "best_prob_for_misses")
# Missed-term clip candidates (stage 1): no floor or floor 0; the cap shared with the loss or a wider one.
MISSED_FLOOR_CANDIDATES: tuple[int | None, ...] = (None, 0)
MISSED_CAP_WIDE: int = 9
MISSED_CAP_CANDIDATES: tuple[int, ...] = (LOSS_CAP, MISSED_CAP_WIDE)
# Cross-validation is repeated over FIT_SEED + 0..REPEAT_SEEDS-1 so the report shows stability
# (research Pitfall 10) and the stage choices do not ride on one fold assignment.
REPEAT_SEEDS: int = 5
# Out-of-fold fair shares closer than this are a tie (selection noise, Pitfall 10).
FAIR_SHARE_TIE_TOLERANCE: float = 0.01

# Form B's binary loss input is 1 when the depth-3 net loss is at least this (or a mate is in sight).
BINARY_LOSS_MIN: int = 2
# Form A clip candidates: no clip (the loss may be negative) or a lower clip at 0.
LOSS_FLOOR_CANDIDATES: tuple[int | None, ...] = (None, 0)
# CV AUCs closer than this are a tie; the out-of-fold fair share among passers then decides.
AUC_TIE_TOLERANCE: float = 0.005
# Sets used for the train / holdout split (sets 1-5 and the Phase 254 miss set 7 fit, set 6 is the blind validation set).
TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "7")
TEST_SET: str = "6"
TRAIN_SETS_TEXT: str = "1-5 and 7"
ALL_GROUP: str = "all"

REASON_UNDECIDED: str = "label 0.5 (undecided)"
REASON_NO_LABEL: str = "no label (extra row)"
REASON_NO_PLAYED: str = "NULL played_prob"
REASON_NO_SPREAD: str = "NULL reply_spread"
REASON_NO_LOSS: str = "NULL loss feature (line too short to tell)"
EXCLUSION_REASONS: tuple[str, ...] = (
    REASON_UNDECIDED,
    REASON_NO_LABEL,
    REASON_NO_PLAYED,
    REASON_NO_SPREAD,
    REASON_NO_LOSS,
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "label",
    "played_prob",
    "reply_spread",
    "line_loss_3",
    "line_mate_ply",
)

FACTS_REQUIRED_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "label",
    "played_prob",
    "reply_spread",
    "best_prob",
    "pre_spread",
    "played_mat_3",
    "line_mate_ply",
    "best_mat_3",
    "best_mate_ply",
)

# The legacy constants block (Phase 250 shape) and the full model block (Phase 254).
CONSTANT_NAMES: tuple[str, ...] = (
    "FACEPALM_INTERCEPT",
    "FACEPALM_PLAYED_COEF",
    "FACEPALM_SPREAD_COEF",
    "FACEPALM_LOSS_COEF",
    "FACEPALM_LOSS_FLOOR",
)
MODEL_CONSTANT_NAMES: tuple[str, ...] = (
    *CONSTANT_NAMES,
    "FACEPALM_MATERIAL_FORM",
    "FACEPALM_MISSED_COEF",
    "FACEPALM_MISSED_FLOOR",
    "FACEPALM_MISSED_CAP",
    "FACEPALM_MISSED_MATE",
    "FACEPALM_SPREAD_FORM",
    "FACEPALM_BEST_PROB_COEF",
    "FACEPALM_PRE_SPREAD_COEF",
)

REPORT_HEADER: str = (
    "A ranking, not a probability (D-01): the labels are mostly rule passers, so the fitted "
    "values are not calibrated to all blunders."
)


class FitError(RuntimeError):
    """The fit cannot be trusted (no data, separable labels, singular design, no convergence)."""


@dataclass(frozen=True, slots=True)
class FitRow:
    """One features-table row as the fit sees it."""

    n: str
    set_id: str
    label: float | None
    played_prob: float | None
    reply_spread: float | None
    line_loss_3: int | None
    line_mate_ply: int | None
    # Signed material at LINE_DEPTH (positive = the blunderer is up) of the played / best line;
    # legacy rows carry played_3 = -line_loss_3 and no best-line or pre-blunder facts.
    played_3: int | None = None
    best_3: int | None = None
    best_mate_ply: int | None = None
    best_prob: float | None = None
    pre_spread: float | None = None


@dataclass(frozen=True, slots=True)
class FeatureTable:
    """The rows of a features file and the schema its header declared."""

    rows: list[FitRow]
    schema: FeatureSchema


@dataclass(frozen=True, slots=True)
class PasserRow:
    """Fair and unfair rows scoring at or above `threshold`."""

    threshold: float
    fair: int
    unfair: int

    @property
    def passers(self) -> int:
        return self.fair + self.unfair

    @property
    def fair_share(self) -> float | None:
        return self.fair / self.passers if self.passers else None


# ---------------------------------------------------------------------------
# Loading and design matrix
# ---------------------------------------------------------------------------


def _opt_float(cell: str) -> float | None:
    return float(cell) if cell != "" else None


def _opt_int(cell: str) -> int | None:
    return int(cell) if cell != "" else None


def _legacy_row(record: dict[str, str]) -> FitRow:
    loss_3 = _opt_int(record["line_loss_3"])
    return FitRow(
        n=record["n"],
        set_id=record["set"],
        label=_opt_float(record["label"]),
        played_prob=_opt_float(record["played_prob"]),
        reply_spread=_opt_float(record["reply_spread"]),
        line_loss_3=loss_3,
        line_mate_ply=_opt_int(record["line_mate_ply"]),
        played_3=None if loss_3 is None else -loss_3,
    )


def _facts_row(record: dict[str, str]) -> FitRow:
    played_3 = _opt_int(record["played_mat_3"])
    return FitRow(
        n=record["n"],
        set_id=record["set"],
        label=_opt_float(record["label"]),
        played_prob=_opt_float(record["played_prob"]),
        reply_spread=_opt_float(record["reply_spread"]),
        # The loss is the negated signed material (the legacy column's meaning).
        line_loss_3=None if played_3 is None else -played_3,
        line_mate_ply=_opt_int(record["line_mate_ply"]),
        played_3=played_3,
        best_3=_opt_int(record["best_mat_3"]),
        best_mate_ply=_opt_int(record["best_mate_ply"]),
        best_prob=_opt_float(record["best_prob"]),
        pre_spread=_opt_float(record["pre_spread"]),
    )


def _schema_of(fieldnames: Sequence[str] | None) -> tuple[FeatureSchema, tuple[str, ...]]:
    """The schema a header declares and its required columns; FitError for a foreign file."""
    names = set(fieldnames or ())
    if "played_mat_3" in names:
        return "facts", FACTS_REQUIRED_COLUMNS
    if "line_loss_3" in names:
        return "legacy", REQUIRED_COLUMNS
    raise FitError("features file lacks the required columns")


def load_features(path: Path) -> FeatureTable:
    """Read the features TSV; raises FitError when the file is not a features table."""
    try:
        text = path.read_text()
    except OSError as exc:
        raise FitError("features file unreadable") from exc
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    schema, required = _schema_of(reader.fieldnames)
    if any(col not in (reader.fieldnames or ()) for col in required):
        raise FitError("features file lacks the required columns")
    build = _facts_row if schema == "facts" else _legacy_row
    rows = [build(record) for record in reader]
    if not rows:
        raise FitError("features file has no rows")
    return FeatureTable(rows=rows, schema=schema)


def _exclusion_reason(row: FitRow) -> str | None:
    """The first reason `row` cannot enter the fit, or None when it can."""
    if row.label is None:
        return REASON_NO_LABEL
    if row.label == LABEL_UNDECIDED:
        return REASON_UNDECIDED
    if row.played_prob is None:
        return REASON_NO_PLAYED
    if row.reply_spread is None:
        return REASON_NO_SPREAD
    if loss_feature(row.line_loss_3, row.line_mate_ply, loss_floor=None) is None:
        return REASON_NO_LOSS
    return None


def split_usable(rows: Sequence[FitRow]) -> tuple[list[FitRow], dict[str, int]]:
    """Rows that can enter the fit, and how many were excluded per reason."""
    counts = dict.fromkeys(EXCLUSION_REASONS, 0)
    usable: list[FitRow] = []
    for row in rows:
        reason = _exclusion_reason(row)
        if reason is None:
            usable.append(row)
        else:
            counts[reason] += 1
    return usable, counts


def labels_of(rows: Sequence[FitRow]) -> np.ndarray:
    """The 0 / 1 label vector of usable rows."""
    return np.array([row.label for row in rows], dtype=float)


def _require(value: float | None) -> float:
    if value is None:
        raise FitError("design matrix needs usable rows only")
    return value


def binary_loss(row: FitRow) -> float:
    """Form B's loss input: 1 when a mate is within LINE_DEPTH or the depth-3 loss is >= BINARY_LOSS_MIN."""
    mated = row.line_mate_ply is not None and row.line_mate_ply <= LINE_DEPTH
    lost = row.line_loss_3 is not None and row.line_loss_3 >= BINARY_LOSS_MIN
    return 1.0 if mated or lost else 0.0


def design_matrix(rows: Sequence[FitRow], form: FitForm, loss_floor: int | None) -> np.ndarray:
    """Design matrix of usable rows: ones, then the form's three inputs.

    Form A: ln(played_prob + PLAYED_PROB_OFFSET), reply spread, the clipped loss feature.
    Form B: raw played_prob, reply spread, the binary loss. `loss_floor` applies to Form A only.
    """
    columns: list[list[float]] = []
    for row in rows:
        played = _require(row.played_prob)
        spread = _require(row.reply_spread)
        if form == "a_log_played":
            loss = loss_feature(row.line_loss_3, row.line_mate_ply, loss_floor=loss_floor)
            columns.append([1.0, math.log(played + PLAYED_PROB_OFFSET), spread, _require(loss)])
        else:
            columns.append([1.0, played, spread, binary_loss(row)])
    return np.array(columns, dtype=float)


# ---------------------------------------------------------------------------
# Logistic regression
# ---------------------------------------------------------------------------


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically safe logistic function."""
    return 1.0 / (1.0 + np.exp(-np.clip(z, -_LOGIT_CLIP, _LOGIT_CLIP)))


def fit_logistic(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Maximum-likelihood logistic coefficients by IRLS from zeros (x carries the intercept column).

    Raises FitError on a singular design, on non-convergence within IRLS_MAX_ITER, and when a
    coefficient exceeds SEPARATION_COEF_LIMIT (separable labels); never returns unconverged
    coefficients.
    """
    coef = np.zeros(x.shape[1])
    for _ in range(IRLS_MAX_ITER):
        p = sigmoid(x @ coef)
        weights = p * (1.0 - p)
        hessian = x.T @ (x * weights[:, None])
        try:
            step = np.linalg.solve(hessian, x.T @ (y - p))
        except np.linalg.LinAlgError as exc:
            raise FitError("singular design matrix") from exc
        coef = coef + step
        if not np.all(np.isfinite(coef)) or np.max(np.abs(coef)) > SEPARATION_COEF_LIMIT:
            raise FitError("coefficients diverge (separable labels?)")
        if np.max(np.abs(step)) < IRLS_TOL:
            return coef
    raise FitError("no convergence within the iteration limit")


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """1-based ranks of `values`, ties get the average rank."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        stop = start
        while stop + 1 < len(values) and sorted_values[stop + 1] == sorted_values[start]:
            stop += 1
        ranks[order[start : stop + 1]] = (start + stop) / 2.0 + 1.0
        start = stop + 1
    return ranks


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Area under the ROC curve (Mann-Whitney U with average ranks for ties)."""
    positive = labels == LABEL_FAIR
    n_pos = int(positive.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        raise FitError("AUC needs both label classes")
    ranks = _average_ranks(scores)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def cv_fold_ids(n: int, folds: int, seed: int) -> np.ndarray:
    """Deterministic fold id (0..folds-1) per row: a seeded permutation, fold = position % folds."""
    permutation = np.random.default_rng(seed).permutation(n)
    ids = np.empty(n, dtype=int)
    ids[permutation] = np.arange(n) % folds
    return ids


def cv_predictions(x: np.ndarray, y: np.ndarray, folds: int, seed: int) -> np.ndarray:
    """Out-of-fold probabilities: each row is scored by a fit that never saw it."""
    if folds < 2 or folds > len(y):
        raise FitError("fold count must be between 2 and the row count")
    ids = cv_fold_ids(len(y), folds, seed)
    predictions = np.empty(len(y), dtype=float)
    for fold in range(folds):
        held_out = ids == fold
        coef = fit_logistic(x[~held_out], y[~held_out])
        predictions[held_out] = sigmoid(x[held_out] @ coef)
    return predictions


def passer_table(
    scores: np.ndarray, labels: np.ndarray, thresholds: Sequence[float]
) -> list[PasserRow]:
    """Fair and unfair row counts among passers (score >= threshold) per threshold."""
    table: list[PasserRow] = []
    for threshold in thresholds:
        passing = scores >= threshold
        fair = int(np.sum(passing & (labels == LABEL_FAIR)))
        unfair = int(np.sum(passing & (labels == LABEL_UNFAIR)))
        table.append(PasserRow(threshold=threshold, fair=fair, unfair=unfair))
    return table


def model_from_coefs(coef: np.ndarray, loss_floor: int | None) -> FacepalmModel:
    """The shipped model: coefficients rounded to COEF_DECIMALS (the values the app will hold)."""
    rounded = [round(float(c), COEF_DECIMALS) + 0.0 for c in coef]
    return FacepalmModel(
        intercept=rounded[0],
        played_coef=rounded[1],
        spread_coef=rounded[2],
        loss_coef=rounded[3],
        loss_floor=loss_floor,
    )


def constants_block(model: FacepalmModel) -> str:
    """The five constants lines, values rounded to COEF_DECIMALS."""

    def num(value: float) -> str:
        return f"{round(value, COEF_DECIMALS) + 0.0:.{COEF_DECIMALS}f}"

    floor = "None" if model.loss_floor is None else str(model.loss_floor)
    return "\n".join(
        [
            f"FACEPALM_INTERCEPT: float = {num(model.intercept)}",
            f"FACEPALM_PLAYED_COEF: float = {num(model.played_coef)}",
            f"FACEPALM_SPREAD_COEF: float = {num(model.spread_coef)}",
            f"FACEPALM_LOSS_COEF: float = {num(model.loss_coef)}",
            f"FACEPALM_LOSS_FLOOR: int | None = {floor}",
        ]
    )


# ---------------------------------------------------------------------------
# Facts schema: candidate model shapes (D-06, D-07, D-08)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    """One model shape of the facts-schema fit; `missed=False` is the pre-refit baseline.

    The design matrix of a spec follows the score twins term by term (lambda 1 = "as fitted"):
    ``combined`` has one column ``loss + missed`` (one coefficient), ``split`` separate ``loss``
    and ``missed`` columns, gated spread forms zero the spread column on rows that do not lose
    material, ``best_prob_for_misses`` adds ``ln(best_prob + offset)`` on those rows only, and
    the optional inputs are additive columns that read 0 when their fact is NULL.
    """

    material_form: MaterialForm
    missed_floor: int | None
    missed_cap: int
    spread_form: SpreadForm
    best_prob: bool = False
    pre_spread: bool = False
    missed: bool = True

    def __post_init__(self) -> None:
        if not self.missed and self.material_form == "combined":
            raise ValueError("the combined form always carries the missed term")
        if self.best_prob and self.spread_form == "best_prob_for_misses":
            raise ValueError("best_prob_for_misses already carries the best-move term")


# The pre-refit shape (D-12): split material, no missed term, spread on every row, no Maia inputs.
BASELINE_SPEC: CandidateSpec = CandidateSpec(
    material_form="split",
    missed_floor=FACTS_LOSS_FLOOR,
    missed_cap=LOSS_CAP,
    spread_form="always",
    missed=False,
)


def spec_columns(spec: CandidateSpec) -> tuple[str, ...]:
    """The names of the design columns of `spec`, in design-matrix order (intercept first)."""
    names = ["intercept", "played", "spread"]
    if spec.material_form == "combined":
        names.append("loss_plus_missed")
    else:
        names.append("loss")
        if spec.missed:
            names.append("missed")
    if spec.best_prob or spec.spread_form == "best_prob_for_misses":
        names.append("best_prob")
    if spec.pre_spread:
        names.append("pre_spread")
    return tuple(names)


def _best_prob_value(row: FitRow, spec: CandidateSpec, loss: float) -> float:
    """ln(best_prob + offset), 0 when unknown; on pure misses only for best_prob_for_misses."""
    if row.best_prob is None or (spec.spread_form == "best_prob_for_misses" and loss > 0):
        return 0.0
    return math.log(row.best_prob + PLAYED_PROB_OFFSET)


def spec_row_values(row: FitRow, spec: CandidateSpec) -> list[float]:
    """The design values of one usable row for `spec` (same order as `spec_columns`)."""
    loss = _require(loss_feature(row.line_loss_3, row.line_mate_ply, loss_floor=FACTS_LOSS_FLOOR))
    missed = missed_feature(
        row.played_3,
        row.best_3,
        row.best_mate_ply,
        missed_floor=spec.missed_floor,
        missed_cap=spec.missed_cap,
        missed_mate=MATE_LOSS,
    )
    spread = _require(row.reply_spread)
    gated_off = spec.spread_form != "always" and loss <= 0
    values = [
        1.0,
        math.log(_require(row.played_prob) + PLAYED_PROB_OFFSET),
        0.0 if gated_off else spread,
    ]
    if spec.material_form == "combined":
        values.append(loss + missed)
    else:
        values.append(loss)
        if spec.missed:
            values.append(missed)
    if spec.best_prob or spec.spread_form == "best_prob_for_misses":
        values.append(_best_prob_value(row, spec, loss))
    if spec.pre_spread:
        values.append(row.pre_spread if row.pre_spread is not None else 0.0)
    return values


def spec_design_matrix(rows: Sequence[FitRow], spec: CandidateSpec) -> np.ndarray:
    """Design matrix of usable rows for `spec`."""
    return np.array([spec_row_values(row, spec) for row in rows], dtype=float)


def model_from_spec(spec: CandidateSpec, coef: np.ndarray) -> FacepalmModel:
    """The shipped model of `spec`: coefficients rounded to COEF_DECIMALS, absent terms 0.0."""
    values = {
        name: round(float(c), COEF_DECIMALS) + 0.0 for name, c in zip(spec_columns(spec), coef)
    }
    return FacepalmModel(
        intercept=values["intercept"],
        played_coef=values["played"],
        spread_coef=values["spread"],
        loss_coef=values["loss_plus_missed"]
        if spec.material_form == "combined"
        else values["loss"],
        loss_floor=FACTS_LOSS_FLOOR,
        material_form=spec.material_form,
        missed_coef=values.get("missed", 0.0),
        missed_floor=spec.missed_floor,
        missed_cap=spec.missed_cap,
        missed_mate=MATE_LOSS,
        spread_form=spec.spread_form,
        best_prob_coef=values.get("best_prob", 0.0),
        pre_spread_coef=values.get("pre_spread", 0.0),
    )


def _floor_text(floor: int | None) -> str:
    return "none" if floor is None else str(floor)


def _none_or(value: int | None) -> str:
    """A Python literal of an optional int for the constants block."""
    return "None" if value is None else str(value)


def spec_label(spec: CandidateSpec) -> str:
    """A short human label of `spec` for the stage tables."""
    if not spec.missed:
        return "baseline: split, no missed term (pre-refit shape)"
    parts = [
        spec.material_form,
        f"missed floor {_floor_text(spec.missed_floor)}",
        f"cap {spec.missed_cap}",
        f"spread {spec.spread_form}",
    ]
    if spec.best_prob:
        parts.append("+ best_prob")
    if spec.pre_spread:
        parts.append("+ pre_spread")
    return ", ".join(parts)


def model_constants_block(model: FacepalmModel) -> str:
    """Every FACEPALM_* model constant, ready to paste (coefficients rounded to COEF_DECIMALS)."""

    def num(value: float) -> str:
        return f"{round(value, COEF_DECIMALS) + 0.0:.{COEF_DECIMALS}f}"

    return "\n".join(
        [
            f"FACEPALM_INTERCEPT: float = {num(model.intercept)}",
            f"FACEPALM_PLAYED_COEF: float = {num(model.played_coef)}",
            f"FACEPALM_SPREAD_COEF: float = {num(model.spread_coef)}",
            f"FACEPALM_LOSS_COEF: float = {num(model.loss_coef)}",
            f"FACEPALM_LOSS_FLOOR: int | None = {_none_or(model.loss_floor)}",
            f'FACEPALM_MATERIAL_FORM: MaterialForm = "{model.material_form}"',
            f"FACEPALM_MISSED_COEF: float = {num(model.missed_coef)}",
            f"FACEPALM_MISSED_FLOOR: int | None = {_none_or(model.missed_floor)}",
            f"FACEPALM_MISSED_CAP: int = {model.missed_cap}",
            f"FACEPALM_MISSED_MATE: int = {model.missed_mate}",
            f'FACEPALM_SPREAD_FORM: SpreadForm = "{model.spread_form}"',
            f"FACEPALM_BEST_PROB_COEF: float = {num(model.best_prob_coef)}",
            f"FACEPALM_PRE_SPREAD_COEF: float = {num(model.pre_spread_coef)}",
        ]
    )


# ---------------------------------------------------------------------------
# Fit orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FormFit:
    """One fitted variant: coefficients on all usable rows plus cross-validated quality."""

    form: FitForm
    loss_floor: int | None
    coef: np.ndarray
    in_sample_auc: float
    cv_auc: float
    oof: np.ndarray


@dataclass(frozen=True, slots=True)
class ClipResult:
    """A Form A clip candidate as the choice rule sees it."""

    loss_floor: int | None
    cv_auc: float
    fair_share: float | None


@dataclass(frozen=True, slots=True)
class SplitResult:
    """Fit on the training sets, scored on the holdout set; `note` says why it is unavailable."""

    train_rows: int
    test_rows: int
    test_auc: float | None
    table: list[PasserRow]
    note: str


@dataclass(frozen=True, slots=True)
class ExtraScore:
    """An unlabelled extra row scored with the shipped (rounded) model."""

    row: FitRow
    score: float | None


@dataclass(frozen=True, slots=True)
class FitOutcome:
    rows: Sequence[FitRow]
    usable: Sequence[FitRow]
    excluded: dict[str, int]
    clip_fits: list[FormFit]
    chosen: FormFit
    clip_reason: str
    clip_forced: bool
    form_b: FormFit
    split: SplitResult
    model: FacepalmModel
    extras: list[ExtraScore]


def fit_form(
    rows: Sequence[FitRow], form: FitForm, loss_floor: int | None, folds: int, seed: int
) -> FormFit:
    """Fit one variant on all rows and cross-validate it."""
    x = design_matrix(rows, form, loss_floor)
    y = labels_of(rows)
    coef = fit_logistic(x, y)
    oof = cv_predictions(x, y, folds, seed)
    return FormFit(
        form=form,
        loss_floor=loss_floor,
        coef=coef,
        in_sample_auc=auc(sigmoid(x @ coef), y),
        cv_auc=auc(oof, y),
        oof=oof,
    )


def fair_share_at(fit: FormFit, labels: np.ndarray, threshold: float) -> float | None:
    """Out-of-fold fair share among passers at `threshold`; None without passers."""
    return passer_table(fit.oof, labels, [threshold])[0].fair_share


def choose_loss_floor(results: Sequence[ClipResult]) -> tuple[int | None, str]:
    """The Form A clip: highest CV AUC; AUCs within AUC_TIE_TOLERANCE fall back to the fair share
    among passers; a remaining tie picks no clip (None). Returns the floor and the reason."""
    best_auc = max(result.cv_auc for result in results)
    contenders = [r for r in results if best_auc - r.cv_auc < AUC_TIE_TOLERANCE]
    if len(contenders) == 1:
        return contenders[0].loss_floor, "higher cross-validated AUC"

    def share(result: ClipResult) -> float:
        return -1.0 if result.fair_share is None else result.fair_share

    best_share = max(share(r) for r in contenders)
    finalists = [r for r in contenders if share(r) == best_share]
    if len(finalists) == 1:
        return (
            finalists[0].loss_floor,
            f"AUCs within {AUC_TIE_TOLERANCE}, higher out-of-fold fair share among passers",
        )
    if any(r.loss_floor is None for r in finalists):
        return None, "AUC and fair share tie, no clip chosen"
    return finalists[0].loss_floor, "AUC and fair share tie"


def _floor_from_mode(mode: LossFloorMode) -> int | None:
    return 0 if mode == "0" else None


def pick_clip(
    usable: Sequence[FitRow], mode: LossFloorMode, threshold: float, folds: int, seed: int
) -> tuple[list[FormFit], FormFit, str]:
    """Fit every clip candidate and choose one (or honour a forced clip)."""
    y = labels_of(usable)
    fits = [fit_form(usable, "a_log_played", floor, folds, seed) for floor in LOSS_FLOOR_CANDIDATES]
    if mode != "auto":
        forced = _floor_from_mode(mode)
        chosen = next(fit for fit in fits if fit.loss_floor == forced)
        return fits, chosen, "forced by --loss-floor"
    results = [ClipResult(f.loss_floor, f.cv_auc, fair_share_at(f, y, threshold)) for f in fits]
    floor, reason = choose_loss_floor(results)
    return fits, next(fit for fit in fits if fit.loss_floor == floor), reason


DesignFn = Callable[[Sequence[FitRow]], np.ndarray]


def _holdout(usable: Sequence[FitRow], design: DesignFn, threshold: float) -> SplitResult:
    """Fit on the training sets, report AUC and the passer table on the holdout set."""
    train = [row for row in usable if row.set_id in TRAIN_SETS]
    test = [row for row in usable if row.set_id == TEST_SET]
    thresholds = thresholds_for(threshold)
    if not train or not test:
        return SplitResult(len(train), len(test), None, [], "train or holdout set is empty")
    try:
        coef = fit_logistic(design(train), labels_of(train))
        y_test = labels_of(test)
        scores = sigmoid(design(test) @ coef)
        return SplitResult(
            len(train),
            len(test),
            auc(scores, y_test),
            passer_table(scores, y_test, thresholds),
            "",
        )
    except FitError as exc:
        return SplitResult(len(train), len(test), None, [], f"unavailable: {exc}")


def holdout_split(
    usable: Sequence[FitRow], loss_floor: int | None, threshold: float
) -> SplitResult:
    """Fit Form A on the training sets, report AUC and the passer table on set 6."""
    return _holdout(usable, lambda rows: design_matrix(rows, "a_log_played", loss_floor), threshold)


def score_extras(rows: Sequence[FitRow], model: FacepalmModel) -> list[ExtraScore]:
    """Score the unlabelled rows with the shipped model (None when an input is NULL)."""
    return [
        ExtraScore(
            row=row,
            score=facepalm_score(
                # Legacy rows carry played_3 = -line_loss_3 and no best-line or pre-blunder facts.
                FacepalmFacts(
                    played_prob=row.played_prob,
                    reply_spread=row.reply_spread,
                    played_3=row.played_3,
                    mate_ply=row.line_mate_ply,
                    best_3=row.best_3,
                    best_mate_ply=row.best_mate_ply,
                    best_prob=row.best_prob,
                    pre_spread=row.pre_spread,
                ),
                lam=FACEPALM_DRILL_LAMBDA,
                model=model,
            ),
        )
        for row in rows
        if row.label is None
    ]


def thresholds_for(threshold: float) -> list[float]:
    """FIT_THRESHOLDS plus the configured threshold, sorted."""
    return sorted({*FIT_THRESHOLDS, threshold})


def run_fit(
    rows: Sequence[FitRow],
    *,
    threshold: float,
    folds: int,
    seed: int,
    loss_floor_mode: LossFloorMode = "auto",
) -> FitOutcome:
    """Run every comparison on `rows`."""
    usable, excluded = split_usable(rows)
    if not usable:
        raise FitError("no usable rows")
    clip_fits, chosen, reason = pick_clip(usable, loss_floor_mode, threshold, folds, seed)
    model = model_from_coefs(chosen.coef, chosen.loss_floor)
    return FitOutcome(
        rows=rows,
        usable=usable,
        excluded=excluded,
        clip_fits=clip_fits,
        chosen=chosen,
        clip_reason=reason,
        clip_forced=loss_floor_mode != "auto",
        form_b=fit_form(usable, "b_raw_played_binary_loss", None, folds, seed),
        split=holdout_split(usable, chosen.loss_floor, threshold),
        model=model,
        extras=score_extras(rows, model),
    )


# ---------------------------------------------------------------------------
# Facts schema: fitting a candidate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FitSettings:
    """The run's cross-validation settings: the cut, the fold count and the base seed."""

    threshold: float
    folds: int
    seed: int


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """A candidate as the choice rule sees it (seed-averaged cross-validated quality)."""

    free_coefs: int
    cv_auc: float
    fair_share: float | None


@dataclass(frozen=True, slots=True)
class CandidateFit:
    """One fitted candidate: coefficients on all usable rows plus cross-validated quality.

    `cv_auc` / `oof` / `fair_share` are the base seed's (the numbers a single run reports);
    `seed_aucs` / `seed_shares` hold REPEAT_SEEDS repeats, base seed first.
    """

    spec: CandidateSpec
    coef: np.ndarray
    in_sample_auc: float
    cv_auc: float
    fair_share: float | None
    passers: PasserRow
    oof: np.ndarray
    seed_aucs: tuple[float, ...]
    seed_shares: tuple[float | None, ...]

    @property
    def free_coefs(self) -> int:
        return len(spec_columns(self.spec))

    @property
    def auc_mean(self) -> float:
        return float(np.mean(self.seed_aucs))

    @property
    def auc_spread(self) -> float:
        return float(max(self.seed_aucs) - min(self.seed_aucs))

    @property
    def share_mean(self) -> float | None:
        defined = [share for share in self.seed_shares if share is not None]
        return float(np.mean(defined)) if defined else None

    @property
    def score(self) -> CandidateScore:
        """The seed-averaged numbers every stage decision is made on."""
        return CandidateScore(self.free_coefs, self.auc_mean, self.share_mean)

    @property
    def model(self) -> FacepalmModel:
        return model_from_spec(self.spec, self.coef)


def fit_candidate(
    rows: Sequence[FitRow], spec: CandidateSpec, settings: FitSettings
) -> CandidateFit:
    """Fit `spec` on all usable rows and cross-validate it over REPEAT_SEEDS seeds."""
    x = spec_design_matrix(rows, spec)
    y = labels_of(rows)
    coef = fit_logistic(x, y)
    oofs = [
        cv_predictions(x, y, settings.folds, settings.seed + repeat)
        for repeat in range(REPEAT_SEEDS)
    ]
    tables = [passer_table(oof, y, [settings.threshold])[0] for oof in oofs]
    return CandidateFit(
        spec=spec,
        coef=coef,
        in_sample_auc=auc(sigmoid(x @ coef), y),
        cv_auc=auc(oofs[0], y),
        fair_share=tables[0].fair_share,
        passers=tables[0],
        oof=oofs[0],
        seed_aucs=tuple(auc(oof, y) for oof in oofs),
        seed_shares=tuple(table.fair_share for table in tables),
    )


# ---------------------------------------------------------------------------
# Facts schema: staged model selection (D-06, D-07, D-08)
# ---------------------------------------------------------------------------

MaterialFormMode = Literal["auto", "combined", "split"]
SpreadFormMode = Literal["auto", "always", "loss_only", "best_prob_for_misses"]


def choose_candidate(scores: Sequence[CandidateScore]) -> tuple[int, str]:
    """The index of the winning candidate and why, by the Phase 250 rule.

    Higher cross-validated AUC wins by more than AUC_TIE_TOLERANCE; AUCs within it fall back to
    the out-of-fold fair share among passers (shares within FAIR_SHARE_TIE_TOLERANCE are a tie);
    a remaining tie picks the model with fewer free coefficients, the first listed on a full tie.
    Candidates are listed simplest first, and an incumbent before the model that adds to it, so
    an input only enters a model by beating it.
    """
    best_auc = max(score.cv_auc for score in scores)
    contenders = [
        i for i, score in enumerate(scores) if best_auc - score.cv_auc <= AUC_TIE_TOLERANCE
    ]
    if len(contenders) == 1:
        return contenders[0], "higher cross-validated AUC"

    def share(index: int) -> float:
        value = scores[index].fair_share
        return -1.0 if value is None else value

    best_share = max(share(i) for i in contenders)
    finalists = [i for i in contenders if best_share - share(i) <= FAIR_SHARE_TIE_TOLERANCE]
    if len(finalists) == 1:
        return (
            finalists[0],
            f"AUCs within {AUC_TIE_TOLERANCE}, higher out-of-fold fair share among passers",
        )
    fewest = min(scores[i].free_coefs for i in finalists)
    winner = next(i for i in finalists if scores[i].free_coefs == fewest)
    return winner, "AUC and fair share tie, fewer free coefficients"


@dataclass(frozen=True, slots=True)
class StageResult:
    """One selection stage: every fitted candidate, the winner, and what was left out or forced."""

    title: str
    candidates: list[CandidateFit]
    chosen: CandidateFit
    reason: str
    forced_by: str
    failed: list[str]
    reference: CandidateFit | None = None


def _fit_all(
    rows: Sequence[FitRow], specs: Sequence[CandidateSpec], settings: FitSettings
) -> tuple[list[CandidateFit], list[str]]:
    """Fit every spec; one that cannot be fitted (singular, separable) is listed, not fatal."""
    fits: list[CandidateFit] = []
    failed: list[str] = []
    for spec in specs:
        try:
            fits.append(fit_candidate(rows, spec, settings))
        except FitError as exc:
            failed.append(f"{spec_label(spec)}: {exc}")
    return fits, failed


def _stage_from_fits(
    title: str,
    fits: list[CandidateFit],
    failed: list[str],
    *,
    forced_by: str = "",
    reference: CandidateFit | None = None,
) -> StageResult:
    if not fits:
        raise FitError("no candidate model could be fitted")
    index, reason = choose_candidate([fit.score for fit in fits])
    return StageResult(title, fits, fits[index], reason, forced_by, failed, reference)


def material_candidates(mode: MaterialFormMode) -> list[CandidateSpec]:
    """Stage 1 candidates: material form x missed floor x missed cap (spread always, no Maia inputs)."""
    forms = MATERIAL_FORMS if mode == "auto" else (mode,)
    return [
        CandidateSpec(form, floor, cap, "always")
        for form in forms
        for floor in MISSED_FLOOR_CANDIDATES
        for cap in MISSED_CAP_CANDIDATES
    ]


def select_material_form(
    rows: Sequence[FitRow], settings: FitSettings, mode: MaterialFormMode = "auto"
) -> StageResult:
    """Stage 1 (D-06): combined (one coefficient on loss + missed) vs split, with the missed clip.

    The pre-refit baseline (split, no missed term) is fitted for reference and never chosen: the
    question of this stage is which way to carry the missed term, not whether to.
    """
    fits, failed = _fit_all(rows, material_candidates(mode), settings)
    baseline, baseline_failed = _fit_all(rows, [BASELINE_SPEC], settings)
    return _stage_from_fits(
        "Stage 1: material form (D-06)",
        fits,
        [*failed, *baseline_failed],
        forced_by="" if mode == "auto" else f"--material-form {mode}",
        reference=baseline[0] if baseline else None,
    )


def select_spread_form(
    rows: Sequence[FitRow],
    incumbent: CandidateFit,
    settings: FitSettings,
    mode: SpreadFormMode = "auto",
) -> StageResult:
    """Stage 2 (D-07): the reply-spread form (always / loss_only / best_prob_for_misses).

    Given the stage-1 winner, which has spread form `always`; it is the incumbent and is not
    refitted. A forced form other than `always` leaves only that form in the stage.
    """
    forms = SPREAD_FORMS if mode == "auto" else (mode,)
    specs = [
        replace(incumbent.spec, spread_form=form, best_prob=False, pre_spread=False)
        for form in forms
        if form != incumbent.spec.spread_form
    ]
    fits, failed = _fit_all(rows, specs, settings)
    keeps_incumbent = mode in ("auto", incumbent.spec.spread_form)
    return _stage_from_fits(
        "Stage 2: reply-spread form (D-07)",
        [incumbent, *fits] if keeps_incumbent else fits,
        failed,
        forced_by="" if mode == "auto" else f"--spread-form {mode}",
    )


def _add_input(
    rows: Sequence[FitRow],
    incumbent: CandidateFit,
    extra: CandidateSpec,
    settings: FitSettings,
    title: str,
) -> StageResult:
    """One D-08 step: the incumbent against the same model plus one input; ties keep the incumbent."""
    fits, failed = _fit_all(rows, [extra], settings)
    return _stage_from_fits(title, [incumbent, *fits], failed)


def select_pre_inputs(
    rows: Sequence[FitRow], incumbent: CandidateFit, settings: FitSettings
) -> list[StageResult]:
    """Stage 3 (D-08): best_prob (unless stage 2 already uses it), then pre_spread.

    Each input is kept only if it beats the model so far; an input that earns nothing keeps its
    0.0 coefficient.
    """
    steps: list[StageResult] = []
    current = incumbent
    if current.spec.spread_form != "best_prob_for_misses":
        step = _add_input(
            rows,
            current,
            replace(current.spec, best_prob=True),
            settings,
            "Stage 3a: best-move probability (D-08)",
        )
        steps.append(step)
        current = step.chosen
    steps.append(
        _add_input(
            rows,
            current,
            replace(current.spec, pre_spread=True),
            settings,
            "Stage 3b: pre-blunder spread (D-08)",
        )
    )
    return steps


# ---------------------------------------------------------------------------
# Facts schema: run
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FactsOutcome:
    rows: Sequence[FitRow]
    usable: Sequence[FitRow]
    excluded: dict[str, int]
    stage1: StageResult
    stage2: StageResult
    stage3: list[StageResult]
    chosen: CandidateFit
    model: FacepalmModel
    split: SplitResult
    extras: list[ExtraScore]


def run_facts_fit(
    rows: Sequence[FitRow],
    settings: FitSettings,
    *,
    material_mode: MaterialFormMode = "auto",
    spread_mode: SpreadFormMode = "auto",
) -> FactsOutcome:
    """Run the three selection stages on the facts-schema `rows`."""
    usable, excluded = split_usable(rows)
    if not usable:
        raise FitError("no usable rows")
    stage1 = select_material_form(usable, settings, material_mode)
    stage2 = select_spread_form(usable, stage1.chosen, settings, spread_mode)
    stage3 = select_pre_inputs(usable, stage2.chosen, settings)
    chosen = stage3[-1].chosen
    return FactsOutcome(
        rows=rows,
        usable=usable,
        excluded=excluded,
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        chosen=chosen,
        model=chosen.model,
        split=_holdout(
            usable, lambda part: spec_design_matrix(part, chosen.spec), settings.threshold
        ),
        extras=score_extras(rows, chosen.model),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

FORM_A_NAMES: tuple[str, ...] = (
    "intercept",
    "ln(played_prob + offset)",
    "reply_spread",
    "loss feature",
)
FORM_B_NAMES: tuple[str, ...] = ("intercept", "played_prob", "reply_spread", "binary loss")


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _passer_lines(table: Sequence[PasserRow]) -> list[str]:
    lines = ["| threshold | passers | fair | unfair | fair share |", "|---|---|---|---|---|"]
    for entry in table:
        lines.append(
            f"| {entry.threshold:.2f} | {entry.passers} | {entry.fair} | {entry.unfair} "
            f"| {_fmt(entry.fair_share)} |"
        )
    return lines


def _data_section(outcome: FitOutcome | FactsOutcome) -> list[str]:
    y = labels_of(outcome.usable)
    fair = int(np.sum(y == LABEL_FAIR))
    lines = [
        "## Data",
        "",
        f"- rows in the features file: {len(outcome.rows)}",
        f"- usable for the fit: {len(outcome.usable)} ({fair} fair, {len(outcome.usable) - fair} unfair)",
    ]
    lines.extend(f"- excluded, {reason}: {count}" for reason, count in outcome.excluded.items())
    return [*lines, ""]


def _fit_section(
    title: str,
    description: str,
    fit: FormFit,
    names: Sequence[str],
    y: np.ndarray,
    folds: int,
    threshold: float,
) -> list[str]:
    table = passer_table(fit.oof, y, thresholds_for(threshold))
    return [
        title,
        "",
        description,
        "",
        *(f"- {name}: {float(c):.{COEF_DECIMALS}f}" for name, c in zip(names, fit.coef)),
        f"- AUC in sample: {fit.in_sample_auc:.3f}",
        f"- AUC {folds}-fold cross-validated: {fit.cv_auc:.3f}",
        "",
        "Fair / unfair among passers, out-of-fold predictions:",
        "",
        *_passer_lines(table),
        "",
    ]


def _form_a_section(outcome: FitOutcome, folds: int, threshold: float) -> list[str]:
    floor = outcome.chosen.loss_floor
    return _fit_section(
        "## Form A",
        "ln(played_prob + PLAYED_PROB_OFFSET), reply spread, loss feature at LINE_DEPTH "
        f"(loss floor: {'none' if floor is None else floor}). This form ships (D-01).",
        outcome.chosen,
        FORM_A_NAMES,
        labels_of(outcome.usable),
        folds,
        threshold,
    )


def _form_b_section(outcome: FitOutcome, folds: int, threshold: float) -> list[str]:
    return _fit_section(
        "## Form B",
        f"Raw played probability, reply spread, binary loss (line_loss_3 >= {BINARY_LOSS_MIN} or a "
        f"mate within {LINE_DEPTH} plies). Reported for the owner's comparison only.",
        outcome.form_b,
        FORM_B_NAMES,
        labels_of(outcome.usable),
        folds,
        threshold,
    )


def _clip_section(outcome: FitOutcome, threshold: float) -> list[str]:
    y = labels_of(outcome.usable)
    lines = [
        "## Clip choice",
        "",
        f"Form A with the loss unclipped against a lower clip at 0 (fair share at threshold {threshold}).",
        "",
        "| loss floor | AUC cross-validated | passers | fair | unfair | fair share |",
        "|---|---|---|---|---|---|",
    ]
    for fit in outcome.clip_fits:
        row = passer_table(fit.oof, y, [threshold])[0]
        floor = "none" if fit.loss_floor is None else str(fit.loss_floor)
        lines.append(
            f"| {floor} | {fit.cv_auc:.3f} | {row.passers} | {row.fair} | {row.unfair} "
            f"| {_fmt(row.fair_share)} |"
        )
    chosen = "none" if outcome.chosen.loss_floor is None else str(outcome.chosen.loss_floor)
    suffix = (
        " (the clip was forced, the script's own rule is overruled)" if outcome.clip_forced else ""
    )
    return [*lines, "", f"Chosen loss floor: {chosen}. Reason: {outcome.clip_reason}{suffix}.", ""]


def _split_section(split: SplitResult, subject: str) -> list[str]:
    lines = [
        "## Sets 1-5 vs set 6",
        "",
        f"{subject} fitted on sets {TRAIN_SETS_TEXT} ({split.train_rows} usable rows), "
        f"scored on set {TEST_SET} ({split.test_rows} usable rows).",
        "",
    ]
    if split.note:
        return [*lines, f"Not available: {split.note}", ""]
    return [
        *lines,
        f"- AUC on set {TEST_SET}: {_fmt(split.test_auc)}",
        "",
        *_passer_lines(split.table),
        "",
    ]


def _extra_lines(extra: ExtraScore, threshold: float) -> list[str]:
    row = extra.row
    if extra.score is None:
        verdict = "not scored (a NULL input)"
    elif extra.score >= threshold:
        verdict = "AT OR ABOVE THRESHOLD"
    else:
        verdict = "below threshold"
    return [
        f"- row {row.n}: played_prob {_fmt(row.played_prob)}, reply_spread {_fmt(row.reply_spread)}, "
        f"line_loss_3 {row.line_loss_3}, line_mate_ply {row.line_mate_ply}: "
        f"score {_fmt(extra.score)}, {verdict}"
    ]


def _extra_section(outcome: FitOutcome | FactsOutcome, threshold: float) -> list[str]:
    lines = [
        "## Extra rows",
        "",
        f"Unlabelled rows scored with the model below (threshold {threshold}).",
        "",
    ]
    if not outcome.extras:
        return [*lines, "None.", ""]
    for extra in outcome.extras:
        lines.extend(_extra_lines(extra, threshold))
    return [*lines, ""]


def _constants_section(model: FacepalmModel) -> list[str]:
    return ["## Constants", "", "```python", constants_block(model), "```", ""]


def render_report(
    outcome: FitOutcome, *, features_name: str, threshold: float, folds: int, seed: int
) -> str:
    """The markdown report (deterministic: no timestamps)."""
    lines = [
        "# Facepalm score fit",
        "",
        REPORT_HEADER,
        "",
        f"Features: {features_name}. Seed {seed}, {folds} folds, threshold {threshold}.",
        "",
        *_data_section(outcome),
        *_form_a_section(outcome, folds, threshold),
        *_form_b_section(outcome, folds, threshold),
        *_clip_section(outcome, threshold),
        *_split_section(outcome.split, "Form A"),
        *_extra_section(outcome, threshold),
        *_constants_section(outcome.model),
    ]
    return "\n".join(lines)


def _facts_constants_section(model: FacepalmModel) -> list[str]:
    return ["## Constants", "", "```python", model_constants_block(model), "```", ""]


def _row_material_type(row: FitRow) -> MaterialType:
    return material_type(row.played_3, row.line_mate_ply, row.best_3, row.best_mate_ply)


def _best_line_null(row: FitRow) -> bool:
    """No settled best-line fact: the missed term contributes 0 for the row (D-18)."""
    return row.best_3 is None and row.best_mate_ply is None


def _material_count_lines(usable: Sequence[FitRow]) -> list[str]:
    """Usable rows per label set and material type."""
    sets = sorted({row.set_id for row in usable})
    types = [_row_material_type(row) for row in usable]
    lines = [
        f"| set | {' | '.join(MATERIAL_TYPES)} | all |",
        f"|---|{'---|' * (len(MATERIAL_TYPES) + 1)}",
    ]
    for set_id in [*sets, ALL_GROUP]:
        members = [t for row, t in zip(usable, types) if set_id in (ALL_GROUP, row.set_id)]
        counts = [str(sum(1 for t in members if t == kind)) for kind in MATERIAL_TYPES]
        lines.append(f"| {set_id} | {' | '.join(counts)} | {len(members)} |")
    return lines


def _facts_data_section(outcome: FactsOutcome) -> list[str]:
    labelled = [row for row in outcome.rows if row.label is not None]
    null_best = [row for row in labelled if _best_line_null(row)]
    usable_null = sum(1 for row in outcome.usable if _best_line_null(row))
    best_mates = sum(
        1 for row in labelled if row.best_mate_ply is not None and row.best_mate_ply <= LINE_DEPTH
    )
    return [
        *_data_section(outcome)[:-1],
        f"- label rows with a NULL best line (the missed term contributes 0, D-18): "
        f"{len(null_best)} of {len(labelled)} ({usable_null} usable for the fit)",
        f"- label rows with a best-line mate within {LINE_DEPTH} plies (the missed-mate value "
        f"stays MATE_LOSS = {MATE_LOSS}): {best_mates}",
        "",
        "Usable rows per label set and material type (D-13):",
        "",
        *_material_count_lines(outcome.usable),
        "",
    ]


def _stage_row(fit: CandidateFit, mark: str) -> str:
    passers = fit.passers
    return (
        f"| {spec_label(fit.spec)} | {fit.free_coefs} | {fit.cv_auc:.3f} | {fit.auc_mean:.3f} "
        f"| {fit.auc_spread:.3f} | {passers.passers} | {passers.fair} | {passers.unfair} "
        f"| {_fmt(fit.fair_share)} | {_fmt(fit.share_mean)} | {mark} |"
    )


def _stage_section(stage: StageResult, threshold: float) -> list[str]:
    lines = [
        f"## {stage.title}",
        "",
        f"At the cut {threshold}. CV AUC and fair share are the base seed's; the mean and the spread "
        f"(max - min) of CV AUC, and the mean fair share, are over {REPEAT_SEEDS} seeds. "
        "Choices are made on the seed means.",
        "",
        "| candidate | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair "
        "| fair share | fair share mean | |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    if stage.reference is not None:
        lines.append(_stage_row(stage.reference, "reference only, not a candidate"))
    lines.extend(
        _stage_row(fit, "chosen" if fit is stage.chosen else "") for fit in stage.candidates
    )
    forced = (
        f" (forced by {stage.forced_by}: the script's own rule is overruled)"
        if stage.forced_by
        else ""
    )
    lines.extend(["", f"Chosen: {spec_label(stage.chosen.spec)}. Reason: {stage.reason}{forced}."])
    lines.extend(f"- not fitted, {note}" for note in stage.failed)
    return [*lines, ""]


def _input_words(name: str, coef: float, used: bool) -> str:
    if used and coef != 0.0:
        return f"{name} enters the model (coefficient {coef:.{COEF_DECIMALS}f})"
    return f"{name} earns nothing and keeps a 0.0 coefficient"


def _chosen_section(outcome: FactsOutcome, folds: int) -> list[str]:
    chosen = outcome.chosen
    spec, model = chosen.spec, outcome.model
    material = (
        "one coefficient on loss + missed (combined)"
        if spec.material_form == "combined"
        else "separate loss and missed coefficients (split)"
    )
    spread = {
        "always": "the reply spread enters on every row",
        "loss_only": "the reply spread enters only on rows that lose material",
        "best_prob_for_misses": (
            "the reply spread enters on rows that lose material, the best-move probability "
            "stands in for pure misses"
        ),
    }[spec.spread_form]
    best_used = spec.best_prob or spec.spread_form == "best_prob_for_misses"
    return [
        "## Chosen model",
        "",
        f"- material: {material}; missed floor {_floor_text(spec.missed_floor)}, cap "
        f"{spec.missed_cap}, missed-mate value {MATE_LOSS}",
        f"- spread: {spread}",
        f"- {_input_words('best-move probability', model.best_prob_coef, best_used)}",
        f"- {_input_words('pre-blunder spread', model.pre_spread_coef, spec.pre_spread)}",
        "",
        *(
            f"- {name}: {float(c):.{COEF_DECIMALS}f}"
            for name, c in zip(spec_columns(spec), chosen.coef)
        ),
        f"- AUC in sample: {chosen.in_sample_auc:.3f}",
        f"- AUC {folds}-fold cross-validated: {chosen.cv_auc:.3f}; over {REPEAT_SEEDS} seeds "
        f"mean {chosen.auc_mean:.3f}, spread {chosen.auc_spread:.3f}",
        "",
    ]


def _group_lines(
    column: str,
    groups: dict[str, np.ndarray],
    oof: np.ndarray,
    y: np.ndarray,
    cuts: Sequence[float],
) -> list[str]:
    """One row per group: its size, fair and unfair counts, and fair / unfair among passers per cut."""
    lines = [
        f"| {column} | rows | fair | unfair | "
        + " | ".join(f"score >= {cut:.2f}" for cut in cuts)
        + " |",
        f"|---|---|---|---|{'---|' * len(cuts)}",
    ]
    for name, mask in groups.items():
        fair = int(np.sum(mask & (y == LABEL_FAIR)))
        unfair = int(np.sum(mask & (y == LABEL_UNFAIR)))
        cells = []
        for cut in cuts:
            passing = mask & (oof >= cut)
            cells.append(
                f"{int(np.sum(passing & (y == LABEL_FAIR)))} / "
                f"{int(np.sum(passing & (y == LABEL_UNFAIR)))}"
            )
        lines.append(f"| {name} | {int(mask.sum())} | {fair} | {unfair} | {' | '.join(cells)} |")
    return lines


def _d13_sections(outcome: FactsOutcome, threshold: float) -> list[str]:
    """D-13: fair / unfair among passers at every cut, by material type and by label set."""
    usable = outcome.usable
    y = labels_of(usable)
    oof = outcome.chosen.oof
    cuts = thresholds_for(threshold)
    types = np.array([_row_material_type(row) for row in usable])
    set_ids = np.array([row.set_id for row in usable])
    everything = np.ones(len(usable), dtype=bool)
    by_type = {kind: types == kind for kind in MATERIAL_TYPES if np.any(types == kind)}
    by_set = {set_id: set_ids == set_id for set_id in sorted(set(set_ids.tolist()))}
    note = (
        "Cells are fair / unfair among rows whose out-of-fold score of the chosen model is at or "
        "above the cut."
    )
    return [
        "## Fair / unfair among passers by material type",
        "",
        note,
        "",
        *_group_lines("material type", {**by_type, ALL_GROUP: everything}, oof, y, cuts),
        "",
        "## Fair / unfair among passers by label set",
        "",
        note,
        "",
        *_group_lines("label set", {**by_set, ALL_GROUP: everything}, oof, y, cuts),
        "",
    ]


def render_facts_report(
    outcome: FactsOutcome, *, features_name: str, threshold: float, folds: int, seed: int
) -> str:
    """The markdown report of a facts-schema fit (deterministic: no timestamps)."""
    lines = [
        "# Facepalm score fit",
        "",
        REPORT_HEADER,
        "",
        f"Features: {features_name} (facts schema). Seed {seed} (repeats {seed}-{seed + REPEAT_SEEDS - 1}), "
        f"{folds} folds, threshold {threshold}. The loss floor is fixed at {FACTS_LOSS_FLOOR} (D-05), "
        "there is no forcing-flag input (D-10).",
        "",
        *_facts_data_section(outcome),
        *_stage_section(outcome.stage1, threshold),
        *_stage_section(outcome.stage2, threshold),
        *(line for stage in outcome.stage3 for line in _stage_section(stage, threshold)),
        *_chosen_section(outcome, folds),
        *_d13_sections(outcome, threshold),
        *_split_section(outcome.split, "The chosen model"),
        *_extra_section(outcome, threshold),
        *_facts_constants_section(outcome.model),
    ]
    return "\n".join(lines)


# (constant name, FacepalmModel field) pairs; coefficients compare within CHECK_CONSTANTS_TOLERANCE,
# the rest exactly (floors, cap, mate value, both Literal selectors).
_COEFFICIENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("FACEPALM_INTERCEPT", "intercept"),
    ("FACEPALM_PLAYED_COEF", "played_coef"),
    ("FACEPALM_SPREAD_COEF", "spread_coef"),
    ("FACEPALM_LOSS_COEF", "loss_coef"),
    ("FACEPALM_MISSED_COEF", "missed_coef"),
    ("FACEPALM_BEST_PROB_COEF", "best_prob_coef"),
    ("FACEPALM_PRE_SPREAD_COEF", "pre_spread_coef"),
)
_EXACT_FIELDS: tuple[tuple[str, str], ...] = (
    ("FACEPALM_LOSS_FLOOR", "loss_floor"),
    ("FACEPALM_MATERIAL_FORM", "material_form"),
    ("FACEPALM_MISSED_FLOOR", "missed_floor"),
    ("FACEPALM_MISSED_CAP", "missed_cap"),
    ("FACEPALM_MISSED_MATE", "missed_mate"),
    ("FACEPALM_SPREAD_FORM", "spread_form"),
)


def constants_mismatches(shipped: FacepalmModel, refit: FacepalmModel) -> list[str]:
    """One table line per FacepalmModel field where the refit differs from the shipped model.

    Every field is compared (empty result = match). A legacy-schema refit carries the pre-refit
    defaults of the Phase 254 fields, so a shipped model that has moved on reports them too.
    """
    lines: list[str] = []
    for name, field in _COEFFICIENT_FIELDS:
        old: float = getattr(shipped, field)
        new: float = getattr(refit, field)
        if abs(old - new) > CHECK_CONSTANTS_TOLERANCE:
            lines.append(f"| {name} | {old:.{COEF_DECIMALS}f} | {new:.{COEF_DECIMALS}f} |")
    for name, field in _EXACT_FIELDS:
        old_value = getattr(shipped, field)
        new_value = getattr(refit, field)
        if old_value != new_value:
            lines.append(f"| {name} | {old_value} | {new_value} |")
    return lines


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit the facepalm score on the features table.")
    parser.add_argument("--features", type=Path, required=True, help="features TSV")
    parser.add_argument("--out", type=Path, required=True, help="markdown report to write")
    parser.add_argument("--seed", type=int, default=FIT_SEED)
    parser.add_argument("--folds", type=int, default=CV_FOLDS)
    parser.add_argument("--threshold", type=float, default=FIT_SELECTION_THRESHOLD)
    parser.add_argument(
        "--loss-floor",
        choices=("auto", "none", "0"),
        default="auto",
        help="legacy schema only, Form A clip: auto picks by CV AUC then fair share; none / 0 force it",
    )
    parser.add_argument(
        "--material-form",
        choices=("auto", "combined", "split"),
        default="auto",
        help=(
            "facts schema only, stage 1 (D-06): auto picks by CV AUC then fair share; "
            "combined / split force the form and the report says so"
        ),
    )
    parser.add_argument(
        "--spread-form",
        choices=("auto", "always", "loss_only", "best_prob_for_misses"),
        default="auto",
        help=(
            "facts schema only, stage 2 (D-07): auto picks by CV AUC then fair share; "
            "the other values force the form and the report says so"
        ),
    )
    parser.add_argument(
        "--check-constants",
        action="store_true",
        help=(
            "after fitting, compare the chosen model (every FacepalmModel field) with the shipped FACEPALM_MODEL; "
            f"exit {EXIT_CONSTANTS_MISMATCH} with a shipped-vs-refit table when they differ"
        ),
    )
    return parser.parse_args(argv)


def _check_constants(refit: FacepalmModel) -> int:
    """Exit code of --check-constants: EXIT_OK on a match, else print the shipped-vs-refit table."""
    mismatches = constants_mismatches(FACEPALM_MODEL, refit)
    if not mismatches:
        print("constants match: the shipped FACEPALM_MODEL is the refit of this features table")
        return EXIT_OK
    print("constants differ from the refit:", file=sys.stderr)
    print("| constant | shipped | refit |\n|---|---|---|", file=sys.stderr)
    print("\n".join(mismatches), file=sys.stderr)
    return EXIT_CONSTANTS_MISMATCH


def _check_flags(schema: FeatureSchema, args: argparse.Namespace) -> None:
    """The form flags belong to one schema each; a flag the table cannot honour is an error."""
    if schema == "facts" and args.loss_floor != "auto":
        raise FitError("--loss-floor applies to the legacy schema only (the facts loss floor is 0)")
    if schema == "legacy" and (args.material_form != "auto" or args.spread_form != "auto"):
        raise FitError("--material-form and --spread-form need a facts-schema features table")


def _fit_and_render(table: FeatureTable, args: argparse.Namespace) -> tuple[str, FacepalmModel]:
    """Run the fit of the table's schema; the markdown report and the refit model."""
    _check_flags(table.schema, args)
    if table.schema == "facts":
        settings = FitSettings(threshold=args.threshold, folds=args.folds, seed=args.seed)
        facts_outcome = run_facts_fit(
            table.rows,
            settings,
            material_mode=args.material_form,
            spread_mode=args.spread_form,
        )
        report = render_facts_report(
            facts_outcome,
            features_name=args.features.name,
            threshold=args.threshold,
            folds=args.folds,
            seed=args.seed,
        )
        return report, facts_outcome.model
    outcome = run_fit(
        table.rows,
        threshold=args.threshold,
        folds=args.folds,
        seed=args.seed,
        loss_floor_mode=args.loss_floor,
    )
    report = render_report(
        outcome,
        features_name=args.features.name,
        threshold=args.threshold,
        folds=args.folds,
        seed=args.seed,
    )
    return report, outcome.model


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report, model = _fit_and_render(load_features(args.features), args)
    except FitError as exc:
        print(f"fit failed: {exc}", file=sys.stderr)
        return EXIT_FIT_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    print(f"wrote {args.out}")
    if args.check_constants:
        return _check_constants(model)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
