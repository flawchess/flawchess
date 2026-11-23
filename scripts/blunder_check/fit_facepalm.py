"""Fit the facepalm score's six coefficients on the owner's labels (Phase 259 D-01, D-03, D-08, D-12 to D-15).

Reads a committed features table (``facepalm_features.py`` output) and nothing else: no
cache, no database, no Maia. The model shape is fixed by first principles, not chosen by AUC
(D-01)::

    z = intercept + played_coef * ln(played_prob + 0.01) + loss_coef * loss + missed_coef * missed
        + (loss > 0 and loss >= missed ? reply_prob_coef * ln(reply_prob + 0.01)
                                       : best_prob_coef * ln(best_prob + 0.01))

``loss`` and ``missed`` are the stored quiet-rule decaying means (D-03), the missed term is fitted at
lambda 1.0, and the best-reply probability replaces the reply spread on blunders that lose
material (D-08). The key-move term follows the type rule (262 D-04, ``--gate type``, the default):
the reply on an allowed loss, the best move on every other row. ``--gate loss`` is the Phase 259
gate (the reply on any loss above zero); it only reproduces the 2026-11-22 constants and gives the
D-05 reference line, it never chooses the model. Only the six coefficients are fitted: Newton-Raphson (IRLS) logistic regression
on the decided labels (1 = fair, 0 = unfair), seeded K-fold cross-validation, a fair / unfair table
among passers at the D-15 cuts from out-of-fold predictions, the label-set 8 hold-out, and a
ready-to-paste constants block.

An information-only section (D-12) fits the Phase 259 rule and shape (the reply probability when
``loss > 0``, read from the table's ``loss_shipped`` / ``missed_shipped`` columns), quiet + spread,
quiet + spread + reply probability, the chosen shape and the D-05 old-gate reference (the chosen
columns on the new inputs, read with the Phase 259 gate) on the same rows, and prints how far the
chosen shape's AUC is from the Phase 259 one against the 0.02 range. A second section prints the old
gate's CV AUC and out-of-fold fair / unfair at 0.70 next to the chosen model's (262 D-05), and a
third lists the rows whose (loss, missed) pair moved from the Phase 259 pair. None of them decides
the constants.

A ranking, not a probability (250 D-01): the labels are mostly rule passers, so the fitted values
are not calibrated to all blunders.

Usage::

    uv run python scripts/blunder_check/fit_facepalm.py \\
        --features reports/blunder-check/facepalm-features-<date>.tsv --out <report.md>
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

import numpy as np

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services import blunder_check_rules  # noqa: E402
from app.services.blunder_check_rules import PLAYED_PROB_OFFSET  # noqa: E402
from app.services.facepalm_score import is_allowed_loss  # noqa: E402
from scripts.blunder_check.metrics import MaterialType, material_type_of  # noqa: E402

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
# Cross-validation is repeated over FIT_SEED + 0..REPEAT_SEEDS-1 so the report shows stability
# (research Pitfall 10) and no number rides on one fold assignment.
REPEAT_SEEDS: int = 5
# Cut the set-8 hold-out table and the extra-row verdicts use by default. It is the labels' meaning
# (label 1 = "the score should be above 70%", CONTEXT D-23), NOT the shipped FACEPALM_SCORE_MIN.
FIT_SELECTION_THRESHOLD: float = 0.7
# D-15: the cuts the owner reads fair / unfair among passers at.
D15_CUTS: tuple[float, ...] = (0.50, 0.55, 0.60, 0.65, 0.70)
# D-12: the chosen shape's cross-validated AUC should sit within about this of the shipped rule's.
AUC_RANGE: float = 0.02
COEF_DECIMALS: int = 4

EXIT_OK: int = 0
EXIT_FIT_ERROR: int = 2
# --check-constants: the refit of the features table differs from the six shipped FACEPALM_* constants.
EXIT_CONSTANTS_MISMATCH: int = 6
# Coefficients are shipped rounded to COEF_DECIMALS (1e-4); a refit matches when every
# coefficient is within this of the shipped value.
CHECK_CONSTANTS_TOLERANCE: float = 1e-4

# Sigmoid input clip: exp(+-500) is representable, beyond that it overflows.
_LOGIT_CLIP: float = 500.0

LABEL_FAIR: float = 1.0
LABEL_UNFAIR: float = 0.0
LABEL_UNDECIDED: float = 0.5

# Sets of the hold-out split (256 D-08): the fit runs on sets 1-7 and is scored on set 8, the
# only fresh data. D-14: label sets 1 to 8 are used as they are.
TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7")
TEST_SET: str = "8"
TRAIN_SETS_TEXT: str = "1-7"
ALL_GROUP: str = "all"

REASON_UNDECIDED: str = "label 0.5 (undecided)"
REASON_NO_LABEL: str = "no label (extra row)"
REASON_NO_PLAYED: str = "NULL played_prob"
REASON_NO_LOSS: str = "NULL loss (no settled line)"
REASON_NO_REPLY_PROB: str = "NULL reply_prob on an allowed loss (262 D-04)"
REASON_NO_BEST_PROB: str = "NULL best_prob on a row that is not an allowed loss (262 D-04)"
EXCLUSION_REASONS: tuple[str, ...] = (
    REASON_UNDECIDED,
    REASON_NO_LABEL,
    REASON_NO_PLAYED,
    REASON_NO_LOSS,
    REASON_NO_REPLY_PROB,
    REASON_NO_BEST_PROB,
)
# Only the alternatives read the reply spread; a NULL one drops the row from that section alone.
REASON_NO_SPREAD: str = "NULL reply_spread on an allowed loss"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "label",
    "played_prob",
    "reply_spread",
    "best_prob",
    "reply_prob",
    "loss",
    "missed",
)
SHIPPED_COLUMNS: tuple[str, ...] = ("loss_shipped", "missed_shipped")

# The six fitted constants of the app twin, in design-matrix order.
CONSTANT_NAMES: tuple[str, ...] = (
    "FACEPALM_INTERCEPT",
    "FACEPALM_PLAYED_COEF",
    "FACEPALM_LOSS_COEF",
    "FACEPALM_MISSED_COEF",
    "FACEPALM_BEST_PROB_COEF",
    "FACEPALM_REPLY_PROB_COEF",
)

ShapeName = Literal["shipped_baseline", "quiet_spread", "quiet_spread_reply", "chosen", "old_gate"]
SHAPES: tuple[ShapeName, ...] = get_args(ShapeName)
SHAPE_WORDS: dict[ShapeName, str] = {
    "shipped_baseline": (
        "shipped rule and shape (Phase 259: loss_shipped / missed_shipped, reply probability "
        "when loss > 0)"
    ),
    "quiet_spread": "quiet rule, spread on losing rows",
    "quiet_spread_reply": "quiet rule, spread and reply probability on losing rows",
    "chosen": "new inputs, reply probability on allowed losses (the type rule, the shape that ships)",
    "old_gate": (
        "new inputs with the Phase 259 gate (reply probability when loss > 0), the D-05 reference"
    ),
}
# The design columns of each shape, intercept first (the chosen shape's order is CONSTANT_NAMES').
SHAPE_COLUMNS: dict[ShapeName, tuple[str, ...]] = {
    "chosen": ("intercept", "played", "loss", "missed", "best_prob", "reply_prob"),
    # The Phase 259 shape and the D-05 reference have the chosen columns; they differ in the inputs
    # they read (`_shape_material`) and the gate they apply (`SHAPE_GATES`).
    "shipped_baseline": ("intercept", "played", "loss", "missed", "best_prob", "reply_prob"),
    "old_gate": ("intercept", "played", "loss", "missed", "best_prob", "reply_prob"),
    "quiet_spread": ("intercept", "played", "loss", "missed", "best_prob", "spread"),
    "quiet_spread_reply": (
        "intercept",
        "played",
        "loss",
        "missed",
        "best_prob",
        "reply_prob",
        "spread",
    ),
}
MATERIAL_TYPES: tuple[MaterialType, ...] = get_args(MaterialType)

# The key-move gate (262 D-04): "type" is the 257 type rule, "loss" the Phase 259 loss-only gate.
GateName = Literal["type", "loss"]
GATES: tuple[GateName, ...] = get_args(GateName)
DEFAULT_GATE: GateName = "type"
# The shapes that pin their own gate (the Phase 259 loss gate); None = the run's gate.
SHAPE_GATES: dict[ShapeName, GateName | None] = {
    "shipped_baseline": "loss",
    "old_gate": "loss",
    "quiet_spread": None,
    "quiet_spread_reply": None,
    "chosen": None,
}
# Which key-move terms a shape reads: the reply probability (chosen columns and quiet_spread_reply)
# and the reply spread (the two spread shapes).
REPLY_PROB_SHAPES: tuple[ShapeName, ...] = (
    "chosen",
    "quiet_spread_reply",
    "shipped_baseline",
    "old_gate",
)
SPREAD_SHAPES: tuple[ShapeName, ...] = ("quiet_spread", "quiet_spread_reply")

REPORT_HEADER: str = (
    "A ranking, not a probability (250 D-01): the labels are mostly rule passers, so the fitted "
    "values are not calibrated to all blunders."
)


class FitError(RuntimeError):
    """The fit cannot be trusted (no data, separable labels, singular design, no convergence)."""


@dataclass(frozen=True, slots=True)
class ScalarFitRow:
    """One features-table row as the fit sees it."""

    n: str
    set_id: str
    label: float | None
    played_prob: float | None
    reply_spread: float | None
    best_prob: float | None
    reply_prob: float | None
    # Quiet-rule decaying means (D-03); `loss` is None when no settled line tells, `missed` is 0 for
    # an unknown best line (254 D-18).
    loss: float | None
    missed: float
    # The shipped (old-rule) inputs of the D-12 baseline; None when the table has no such columns.
    loss_shipped: float | None = None
    missed_shipped: float = 0.0
    # Where the row comes from (the extra rows are named by game and ply in the report).
    game_id: str = ""
    ply: str = ""


@dataclass(frozen=True, slots=True)
class FeatureTable:
    """The rows of a features file and whether it carries the shipped-rule columns."""

    rows: list[ScalarFitRow]
    has_shipped: bool


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


@dataclass(frozen=True, slots=True)
class ScalarCoefs:
    """The six fitted coefficients, rounded to COEF_DECIMALS (the values the app will hold)."""

    intercept: float
    played_coef: float
    loss_coef: float
    missed_coef: float
    best_prob_coef: float
    reply_prob_coef: float

    @classmethod
    def from_vector(cls, vector: Sequence[float]) -> ScalarCoefs:
        """The chosen shape's coefficient vector (SHAPE_COLUMNS["chosen"] order), rounded."""
        rounded = [round(float(c), COEF_DECIMALS) + 0.0 for c in vector]
        return cls(*rounded)

    def by_name(self) -> dict[str, float]:
        """The coefficients keyed by their FACEPALM_* constant names."""
        values = (
            self.intercept,
            self.played_coef,
            self.loss_coef,
            self.missed_coef,
            self.best_prob_coef,
            self.reply_prob_coef,
        )
        return dict(zip(CONSTANT_NAMES, values, strict=True))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _opt_float(cell: str) -> float | None:
    return float(cell) if cell != "" else None


def _scalar_row(record: dict[str, str], has_shipped: bool) -> ScalarFitRow:
    # 254 D-18: an unknown best line contributes missed = 0, so an empty `missed` is 0, not NULL.
    missed = _opt_float(record["missed"])
    shipped_loss = _opt_float(record["loss_shipped"]) if has_shipped else None
    shipped_missed = _opt_float(record["missed_shipped"]) if has_shipped else None
    return ScalarFitRow(
        n=record["n"],
        set_id=record["set"],
        label=_opt_float(record["label"]),
        played_prob=_opt_float(record["played_prob"]),
        reply_spread=_opt_float(record["reply_spread"]),
        best_prob=_opt_float(record["best_prob"]),
        reply_prob=_opt_float(record["reply_prob"]),
        loss=_opt_float(record["loss"]),
        missed=0.0 if missed is None else missed,
        loss_shipped=shipped_loss,
        missed_shipped=0.0 if shipped_missed is None else shipped_missed,
        game_id=record.get("game_id") or "",
        ply=record.get("ply") or "",
    )


def load_features(path: Path) -> FeatureTable:
    """Read the features TSV; raises FitError when the file is not a Phase 259 features table.

    A table written before Phase 259 (no `loss`, `missed`, `reply_prob` columns) is rejected: its
    inputs belong to the old rule and cannot feed the scalar shape.
    """
    try:
        text = path.read_text()
    except OSError as exc:
        raise FitError("features file unreadable") from exc
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    names = reader.fieldnames or ()
    if any(col not in names for col in REQUIRED_COLUMNS):
        raise FitError("features file lacks the required columns")
    has_shipped = all(col in names for col in SHIPPED_COLUMNS)
    rows = [_scalar_row(record, has_shipped) for record in reader]
    if not rows:
        raise FitError("features file has no rows")
    return FeatureTable(rows=rows, has_shipped=has_shipped)


@dataclass(frozen=True, slots=True)
class LabelNote:
    """One commented row of the owner's label file, for the owner section only (D-13)."""

    n: str
    set_id: str
    link: str
    comment: str


LABEL_NOTE_COLUMNS: tuple[str, ...] = ("n", "comment")


def load_label_notes(path: Path) -> dict[str, LabelNote]:
    """The label rows that carry a comment, by `n`, in file order.

    The fit never reads labels from this file (they stay in the features TSV): it is read for the
    comments and links the owner section prints. A row with no comment cell (csv.DictReader gives
    None, as on the set-8 rows) or an empty one is skipped; a file without the `n` or `comment`
    column is a FitError.
    """
    try:
        text = path.read_text()
    except OSError as exc:
        raise FitError("labels file unreadable") from exc
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    for column in LABEL_NOTE_COLUMNS:
        if column not in (reader.fieldnames or ()):
            raise FitError(f"labels file lacks the '{column}' column")
    notes: dict[str, LabelNote] = {}
    for record in reader:
        comment = (record["comment"] or "").strip()
        n = record["n"]
        if not comment or not n:
            continue
        notes[n] = LabelNote(
            n=n,
            set_id=record.get("set") or "",
            link=record.get("link") or "",
            comment=comment,
        )
    return notes


# ---------------------------------------------------------------------------
# Usable rows and the design row
# ---------------------------------------------------------------------------


def _shape_material(row: ScalarFitRow, shape: ShapeName) -> tuple[float | None, float]:
    """The (loss, missed) a shape reads: the shipped-rule pair for the baseline, else the quiet pair."""
    if shape == "shipped_baseline":
        return row.loss_shipped, row.missed_shipped
    return row.loss, row.missed


def _shape_gate(shape: ShapeName, gate: GateName) -> GateName:
    """The gate `shape` is read with: its own when it pins one (Phase 259 shapes), else the run's `gate`."""
    pinned = SHAPE_GATES[shape]
    return gate if pinned is None else pinned


def _reads_reply(loss: float, missed: float, gate: GateName) -> bool:
    """Whether the key-move term of a row is the reply (True) or the best move (False).

    "type": the 257 type rule, `is_allowed_loss` of the app twin (262 D-04). "loss": the Phase 259
    gate, any loss above zero. The loss gate exists only to reproduce the Phase 259 constants and
    for the D-05 reference line, never for the chosen model.
    """
    if gate == "type":
        return is_allowed_loss(loss, missed)
    return loss > 0


def missing_reason(
    row: ScalarFitRow, shape: ShapeName, gate: GateName = DEFAULT_GATE
) -> str | None:
    """Why `shape` cannot score `row` (a decided, played-prob row), or None when it can.

    Mirrors what the twin reads: the reply probability (or, for the spread shapes, the reply
    spread) on rows that read the reply under `gate`, the best-move probability on the others
    (256 D-04 mirrored, 262 D-04 gate).
    """
    loss, missed = _shape_material(row, shape)
    if loss is None:
        return REASON_NO_LOSS
    if _reads_reply(loss, missed, _shape_gate(shape, gate)):
        if shape in REPLY_PROB_SHAPES and row.reply_prob is None:
            return REASON_NO_REPLY_PROB
        if shape in SPREAD_SHAPES and row.reply_spread is None:
            return REASON_NO_SPREAD
        return None
    return REASON_NO_BEST_PROB if row.best_prob is None else None


def _exclusion_reason(row: ScalarFitRow, gate: GateName) -> str | None:
    """The first reason `row` cannot enter the chosen-shape fit, or None when it can."""
    if row.label is None:
        return REASON_NO_LABEL
    if row.label == LABEL_UNDECIDED:
        return REASON_UNDECIDED
    if row.played_prob is None:
        return REASON_NO_PLAYED
    return missing_reason(row, "chosen", gate)


def split_usable(
    rows: Sequence[ScalarFitRow], gate: GateName = DEFAULT_GATE
) -> tuple[list[ScalarFitRow], dict[str, int]]:
    """Rows the chosen shape can fit, and how many were excluded per reason."""
    counts = dict.fromkeys(EXCLUSION_REASONS, 0)
    usable: list[ScalarFitRow] = []
    for row in rows:
        reason = _exclusion_reason(row, gate)
        if reason is None:
            usable.append(row)
        else:
            counts[reason] += 1
    return usable, {reason: count for reason, count in counts.items() if reason != REASON_NO_SPREAD}


def labels_of(rows: Sequence[ScalarFitRow]) -> np.ndarray:
    """The 0 / 1 label vector of usable rows."""
    return np.array([row.label for row in rows], dtype=float)


def _require(value: float | None) -> float:
    if value is None:
        raise FitError("design matrix needs usable rows only")
    return value


def _log_term(prob: float | None) -> float:
    return math.log(_require(prob) + PLAYED_PROB_OFFSET)


def design_row(row: ScalarFitRow, shape: ShapeName, gate: GateName = DEFAULT_GATE) -> list[float]:
    """The design values of one usable row for `shape`, in SHAPE_COLUMNS order (intercept first).

    The best-move term is on rows that do not read the reply under `gate` only, and the reply term
    (reply probability, or the raw reply spread for the spread shapes) on rows that do, each 0
    elsewhere. The missed term is the raw `missed` (lambda 1.0).
    """
    loss_value, missed = _shape_material(row, shape)
    loss = _require(loss_value)
    reads_reply = _reads_reply(loss, missed, _shape_gate(shape, gate))
    values = [
        1.0,
        _log_term(row.played_prob),
        loss,
        missed,
        0.0 if reads_reply else _log_term(row.best_prob),
    ]
    reply = _log_term(row.reply_prob) if reads_reply and shape in REPLY_PROB_SHAPES else 0.0
    if shape not in SPREAD_SHAPES:
        return [*values, reply]
    spread = _require(row.reply_spread) if reads_reply else 0.0
    if shape == "quiet_spread_reply":
        return [*values, reply, spread]
    return [*values, spread]


def design_matrix(
    rows: Sequence[ScalarFitRow], shape: ShapeName, gate: GateName = DEFAULT_GATE
) -> np.ndarray:
    """Design matrix of usable rows for `shape`."""
    return np.array([design_row(row, shape, gate) for row in rows], dtype=float)


def scalar_score(
    row: ScalarFitRow, coefs: ScalarCoefs, gate: GateName = DEFAULT_GATE
) -> float | None:
    """The score of one features row under `coefs` (None when an input the row needs is NULL).

    The function plan 09 pins against the app twin: the logistic of the chosen shape's linear term.
    """
    if row.played_prob is None or row.loss is None:
        return None
    if missing_reason(row, "chosen", gate) is not None:
        return None
    vector = design_row(row, "chosen", gate)
    z = sum(c * v for c, v in zip(coefs.by_name().values(), vector, strict=True))
    return float(sigmoid(np.array(z)))


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


def cuts_for(threshold: float) -> list[float]:
    """The D-15 cuts plus the configured threshold, sorted."""
    return sorted({*D15_CUTS, threshold})


# ---------------------------------------------------------------------------
# Fit orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShapeFit:
    """One fitted shape: coefficients on all its rows plus cross-validated quality."""

    shape: ShapeName
    rows: Sequence[ScalarFitRow]
    coef: np.ndarray
    in_sample_auc: float
    cv_auc: float
    auc_mean: float
    auc_spread: float
    oof: np.ndarray


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
    """An unlabelled extra row scored with the fitted (rounded) coefficients."""

    row: ScalarFitRow
    score: float | None


@dataclass(frozen=True, slots=True)
class FitOutcome:
    rows: Sequence[ScalarFitRow]
    usable: Sequence[ScalarFitRow]
    excluded: dict[str, int]
    chosen: ShapeFit
    coefs: ScalarCoefs
    alternatives: list[ShapeFit]
    alternatives_note: str
    split: SplitResult
    extras: list[ExtraScore]
    # The key-move gate the run was fitted and scored with (262 D-04).
    gate: GateName
    # Whether the table carries loss_shipped / missed_shipped (the Phase 259 pair).
    has_shipped: bool


def fit_shape(
    rows: Sequence[ScalarFitRow],
    shape: ShapeName,
    folds: int,
    seed: int,
    gate: GateName = DEFAULT_GATE,
) -> ShapeFit:
    """Fit one shape on all rows and cross-validate it (repeated over REPEAT_SEEDS fold assignments)."""
    x = design_matrix(rows, shape, gate)
    y = labels_of(rows)
    coef = fit_logistic(x, y)
    oof = cv_predictions(x, y, folds, seed)
    repeats = [auc(oof, y)]
    repeats.extend(auc(cv_predictions(x, y, folds, seed + i), y) for i in range(1, REPEAT_SEEDS))
    return ShapeFit(
        shape=shape,
        rows=rows,
        coef=coef,
        in_sample_auc=auc(sigmoid(x @ coef), y),
        cv_auc=repeats[0],
        auc_mean=float(np.mean(repeats)),
        auc_spread=float(max(repeats) - min(repeats)),
        oof=oof,
    )


HOLDOUT_EMPTY_NOTE: str = "train or holdout set is empty"


def holdout_split(
    usable: Sequence[ScalarFitRow], threshold: float, gate: GateName = DEFAULT_GATE
) -> SplitResult:
    """Fit the chosen shape on sets 1-7, report AUC and the passer table on set 8."""
    train = [row for row in usable if row.set_id in TRAIN_SETS]
    test = [row for row in usable if row.set_id == TEST_SET]
    if not train or not test:
        return SplitResult(len(train), len(test), None, [], HOLDOUT_EMPTY_NOTE)
    try:
        coef = fit_logistic(design_matrix(train, "chosen", gate), labels_of(train))
        y_test = labels_of(test)
        scores = sigmoid(design_matrix(test, "chosen", gate) @ coef)
        table = passer_table(scores, y_test, cuts_for(threshold))
        return SplitResult(len(train), len(test), auc(scores, y_test), table, "")
    except FitError as exc:
        return SplitResult(len(train), len(test), None, [], f"unavailable: {exc}")


def _alternative_shapes(has_shipped: bool) -> tuple[ShapeName, ...]:
    return SHAPES if has_shipped else tuple(s for s in SHAPES if s != "shipped_baseline")


def fit_alternatives(
    usable: Sequence[ScalarFitRow],
    has_shipped: bool,
    folds: int,
    seed: int,
    gate: GateName = DEFAULT_GATE,
) -> tuple[list[ShapeFit], str]:
    """Every shape fitted on the rows usable for all of them (D-12); the second item is a note.

    The Phase 259 baseline and the D-05 old-gate reference read the loss gate (`SHAPE_GATES`), the
    other shapes the run's `gate`.
    """
    shapes = _alternative_shapes(has_shipped)
    rows = [
        row for row in usable if all(missing_reason(row, shape, gate) is None for shape in shapes)
    ]
    note = "" if has_shipped else "the features table has no loss_shipped / missed_shipped columns"
    if len(rows) < folds:
        return [], f"too few rows usable for every shape ({len(rows)})"
    try:
        return [fit_shape(rows, shape, folds, seed, gate) for shape in shapes], note
    except FitError as exc:
        return [], f"alternatives not fitted: {exc}"


def score_extras(
    rows: Sequence[ScalarFitRow], coefs: ScalarCoefs, gate: GateName = DEFAULT_GATE
) -> list[ExtraScore]:
    """Score the unlabelled rows with the fitted model (None when an input is NULL)."""
    return [
        ExtraScore(row=row, score=scalar_score(row, coefs, gate))
        for row in rows
        if row.label is None
    ]


def run_fit(
    table: FeatureTable,
    *,
    threshold: float,
    folds: int,
    seed: int,
    gate: GateName = DEFAULT_GATE,
) -> FitOutcome:
    """Run every comparison on the table's rows under the key-move `gate`."""
    usable, excluded = split_usable(table.rows, gate)
    if not usable:
        raise FitError("no usable rows")
    chosen = fit_shape(usable, "chosen", folds, seed, gate)
    coefs = ScalarCoefs.from_vector(chosen.coef.tolist())
    alternatives, note = fit_alternatives(usable, table.has_shipped, folds, seed, gate)
    return FitOutcome(
        rows=table.rows,
        usable=usable,
        excluded=excluded,
        chosen=chosen,
        coefs=coefs,
        alternatives=alternatives,
        alternatives_note=note,
        split=holdout_split(usable, threshold, gate),
        extras=score_extras(table.rows, coefs, gate),
        gate=gate,
        has_shipped=table.has_shipped,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


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


def _data_section(outcome: FitOutcome) -> list[str]:
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


def _chosen_section(outcome: FitOutcome, folds: int) -> list[str]:
    chosen = outcome.chosen
    return [
        "## Chosen shape",
        "",
        "Fixed by first principles (D-01, D-03, D-08), only the coefficients are fitted: "
        f"{SHAPE_WORDS['chosen']}. The missed term is fitted at lambda 1.0.",
        "",
        *(
            f"- {name}: {float(c):.{COEF_DECIMALS}f}"
            for name, c in zip(SHAPE_COLUMNS["chosen"], chosen.coef, strict=True)
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


def _row_material_type(row: ScalarFitRow) -> MaterialType:
    return material_type_of(row.loss, row.missed)


def _d15_section(outcome: FitOutcome, threshold: float) -> list[str]:
    """D-15: fair / unfair among passers at every cut, out of fold, by material type."""
    usable = outcome.chosen.rows
    y = labels_of(usable)
    types = np.array([_row_material_type(row) for row in usable])
    everything = np.ones(len(usable), dtype=bool)
    by_type = {kind: types == kind for kind in MATERIAL_TYPES if np.any(types == kind)}
    return [
        "## Fair / unfair among passers at the D-15 cuts",
        "",
        "Cells are fair / unfair among rows whose out-of-fold score of the chosen shape is at or "
        "above the cut, split by material type (loss > 0 loses, missed >= 1 misses).",
        "",
        *_group_lines(
            "material type",
            {**by_type, ALL_GROUP: everything},
            outcome.chosen.oof,
            y,
            cuts_for(threshold),
        ),
        "",
    ]


def _alternatives_section(outcome: FitOutcome, folds: int) -> list[str]:
    lines = [
        "## Alternatives (information only)",
        "",
        "D-01: the shape is fixed, these fits never choose it and the constants below are always the "
        f"chosen shape's. Every shape is fitted on the same rows; AUCs are {folds}-fold "
        f"cross-validated, mean over {REPEAT_SEEDS} seeds.",
        "",
    ]
    if outcome.alternatives_note:
        lines.extend([f"Note: {outcome.alternatives_note}.", ""])
    if not outcome.alternatives:
        return [*lines, "Not available.", ""]
    lines.extend(
        [
            "| shape | rows | CV AUC mean | CV AUC spread |",
            "|---|---|---|---|",
            *(
                f"| {fit.shape}: {SHAPE_WORDS[fit.shape]} | {len(fit.rows)} | {fit.auc_mean:.3f} "
                f"| {fit.auc_spread:.3f} |"
                for fit in outcome.alternatives
            ),
        ]
    )
    return [*lines, "", *_range_check_lines(outcome), ""]


def _range_check_lines(outcome: FitOutcome) -> list[str]:
    """D-12: |AUC(chosen) - AUC(shipped baseline)| against AUC_RANGE."""
    fits = {fit.shape: fit for fit in outcome.alternatives}
    baseline = fits.get("shipped_baseline")
    if baseline is None:
        return ["Range check: not available without the shipped-rule baseline."]
    delta = abs(fits["chosen"].auc_mean - baseline.auc_mean)
    verdict = "within range" if delta <= AUC_RANGE else "outside range"
    return [
        f"|AUC(chosen) - AUC(shipped_baseline)| = {delta:.3f} against the range {AUC_RANGE}: {verdict}."
    ]


def _fair_unfair_at_threshold(fit: ShapeFit) -> str:
    """Out-of-fold fair / unfair among rows scoring at or above FIT_SELECTION_THRESHOLD."""
    entry = passer_table(fit.oof, labels_of(fit.rows), [FIT_SELECTION_THRESHOLD])[0]
    return f"{entry.fair} / {entry.unfair}"


def _old_gate_section(outcome: FitOutcome) -> list[str]:
    """D-05: the chosen fit and the old-gate fit side by side on the same rows (information only)."""
    lines = [
        "## Old gate reference (D-05, information only)",
        "",
        "The model is fitted with the type-rule gate (262 D-04). This line fits the same shape on the "
        "same rows and inputs with the Phase 259 gate (the reply probability whenever loss > 0) and "
        "only informs (259 D-01): it never chooses the constants.",
        "",
    ]
    fits = {fit.shape: fit for fit in outcome.alternatives}
    chosen, old = fits.get("chosen"), fits.get("old_gate")
    if chosen is None or old is None:
        return [*lines, "Not available.", ""]
    cut = f"{FIT_SELECTION_THRESHOLD:.2f}"
    return [
        *lines,
        f"| gate | rows | CV AUC mean | fair / unfair at {cut} (out of fold) |",
        "|---|---|---|---|",
        f"| {outcome.gate} (chosen) | {len(chosen.rows)} | {chosen.auc_mean:.3f} "
        f"| {_fair_unfair_at_threshold(chosen)} |",
        f"| loss (old gate) | {len(old.rows)} | {old.auc_mean:.3f} | {_fair_unfair_at_threshold(old)} |",
        "",
    ]


def _pair(loss: float | None, missed: float | None) -> str:
    return f"{_fmt(loss)} / {_fmt(missed)}"


def _changed_inputs_section(outcome: FitOutcome) -> list[str]:
    """The rows whose (loss, missed) pair differs from the Phase 259 pair, both pairs shown."""
    if not outcome.has_shipped:
        return []
    lines = [
        "## Rows whose inputs changed",
        "",
        "Rows whose (loss, missed) pair under the current material rule differs from the Phase 259 "
        "pair (loss_shipped, missed_shipped).",
        "",
    ]
    moved = [
        row
        for row in outcome.rows
        if (row.loss, row.missed) != (row.loss_shipped, row.missed_shipped)
    ]
    if not moved:
        return [*lines, "None.", ""]
    lines.extend(
        [
            "| n | set | label | loss_shipped / missed_shipped | loss / missed |",
            "|---|---|---|---|---|",
        ]
    )
    for row in moved:
        label = "n/a" if row.label is None else f"{row.label:g}"
        lines.append(
            f"| {row.n} | {row.set_id} | {label} "
            f"| {_pair(row.loss_shipped, row.missed_shipped)} | {_pair(row.loss, row.missed)} |"
        )
    return [*lines, ""]


# The decided rows of set 8 (the blind set): its AUC moves by several hundredths between samples.
SET_EIGHT_SIZE_NOTE: str = (
    "Set 8 has about 55 decided rows, so its AUC moves by several hundredths between samples: "
    "read it as a check on the cross-validated numbers, not as a second ranking."
)


def _split_section(split: SplitResult) -> list[str]:
    """The holdout section; its heading names the split it was run on (never a literal)."""
    lines = [
        f"## Sets {TRAIN_SETS_TEXT} vs set {TEST_SET}",
        "",
        f"The chosen shape fitted on sets {TRAIN_SETS_TEXT} ({split.train_rows} usable rows), "
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
        SET_EIGHT_SIZE_NOTE,
        "",
    ]


OWNER_NO_SCORE: str = "n/a"
OWNER_NOT_IN_FEATURES: str = "not in features"
OWNER_FIXTURES_NOTE: str = (
    "The two owner fixtures (games 817357 ply 24 and 820181 ply 65) are dev-DB games that are not "
    "on prod and not in the features table: they are scored at the checkpoint from "
    "tests/services/facepalm_owner_fixtures.py."
)


def _cell(text: str) -> str:
    """A markdown table cell: a pipe in a comment must not split the row."""
    return text.replace("|", "\\|")


def _note_row(
    note: LabelNote, row: ScalarFitRow | None, coefs: ScalarCoefs, gate: GateName = DEFAULT_GATE
) -> str:
    """One commented label row: its label, comment and its score under the chosen coefficients."""
    if row is None:
        label, score = "n/a", OWNER_NOT_IN_FEATURES
    else:
        label = "n/a" if row.label is None else f"{row.label:g}"
        value = scalar_score(row, coefs, gate)
        score = OWNER_NO_SCORE if value is None else _fmt(value)
    return f"| {note.n} | {note.set_id} | {label} | {note.link} | {_cell(note.comment)} | {score} |"


def _commented_rows_lines(outcome: FitOutcome, notes: dict[str, LabelNote] | None) -> list[str]:
    """D-13: every commented label row (owner comment verbatim) with its score."""
    lines = ["### Commented label rows", ""]
    if notes is None:
        return [*lines, "Pass --labels <the owner label TSV> to list the commented rows here.", ""]
    by_n = {row.n: row for row in outcome.rows}
    lines.extend(
        [
            "The owner's comments and links, verbatim. The score is the chosen shape's (in sample).",
            "",
            "| n | set | label | link | comment | score |",
            "|---|---|---|---|---|---|",
        ]
    )
    lines.extend(
        _note_row(note, by_n.get(n), outcome.coefs, outcome.gate) for n, note in notes.items()
    )
    return [*lines, ""]


def _pure_miss_lines(outcome: FitOutcome, cuts: Sequence[float]) -> list[str]:
    """D-13: the share of pure-miss rows scoring at or above each cut (out of fold)."""
    chosen = outcome.chosen
    misses = [
        position for position, row in enumerate(chosen.rows) if _row_material_type(row) == "misses"
    ]
    lines = [
        "### Pure-miss pass rate",
        "",
        "Among the rows of material type 'misses' (nothing lost, material left on the table), the "
        "rows whose out-of-fold score is at or above each cut.",
        "",
    ]
    if not misses:
        return [*lines, "No pure-miss rows among the usable rows.", ""]
    lines.extend(["| cut | passers | rows | pass rate |", "|---|---|---|---|"])
    for cut in cuts:
        passers = sum(1 for position in misses if chosen.oof[position] >= cut)
        lines.append(f"| {cut:.2f} | {passers} | {len(misses)} | {_fmt(passers / len(misses))} |")
    return [*lines, ""]


def _owner_section(
    outcome: FitOutcome, notes: dict[str, LabelNote] | None, threshold: float
) -> list[str]:
    """D-13: what the owner reads at the checkpoint that the labels and features can show."""
    return [
        "## Owner checks (D-13, information only, not gates)",
        "",
        *_commented_rows_lines(outcome, notes),
        *_pure_miss_lines(outcome, cuts_for(threshold)),
        OWNER_FIXTURES_NOTE,
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
    where = f" (game {row.game_id} ply {row.ply})" if row.game_id else ""
    return [
        f"- row {row.n}{where}: played_prob {_fmt(row.played_prob)}, loss {_fmt(row.loss)}, "
        f"missed {_fmt(row.missed)}, reply_prob {_fmt(row.reply_prob)}: "
        f"score {_fmt(extra.score)}, {verdict}"
    ]


def _extra_section(outcome: FitOutcome, threshold: float) -> list[str]:
    lines = [
        "## Extra rows",
        "",
        f"Unlabelled rows scored with the constants below (threshold {threshold}).",
        "",
    ]
    if not outcome.extras:
        return [*lines, "None.", ""]
    for extra in outcome.extras:
        lines.extend(_extra_lines(extra, threshold))
    return [*lines, ""]


def constants_block(coefs: ScalarCoefs) -> str:
    """The six constants lines, values rounded to COEF_DECIMALS."""
    return "\n".join(
        f"{name}: float = {value:.{COEF_DECIMALS}f}" for name, value in coefs.by_name().items()
    )


def _constants_section(coefs: ScalarCoefs) -> list[str]:
    return ["## Constants", "", "```python", constants_block(coefs), "```", ""]


def render_report(
    outcome: FitOutcome,
    *,
    features_name: str,
    threshold: float,
    folds: int,
    seed: int,
    notes: dict[str, LabelNote] | None = None,
) -> str:
    """The markdown report (deterministic: no timestamps).

    `notes` are the commented rows of the owner's label file (`load_label_notes`); without them the
    owner section says to pass --labels.
    """
    lines = [
        "# Facepalm score fit",
        "",
        REPORT_HEADER,
        "",
        f"Features: {features_name}. Seed {seed} (repeats {seed}-{seed + REPEAT_SEEDS - 1}), "
        f"{folds} folds, threshold {threshold}. The model shape is fixed (D-01), label sets 1 to 8 "
        "are used as they are (D-14).",
        "",
        *_data_section(outcome),
        *_chosen_section(outcome, folds),
        *_d15_section(outcome, threshold),
        *_alternatives_section(outcome, folds),
        *_old_gate_section(outcome),
        *_changed_inputs_section(outcome),
        *_split_section(outcome.split),
        *_owner_section(outcome, notes, threshold),
        *_extra_section(outcome, threshold),
        *_constants_section(outcome.coefs),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# --check-constants and the CLI
# ---------------------------------------------------------------------------


def constants_mismatches(coefs: ScalarCoefs) -> list[str]:
    """One table line per FACEPALM_* constant where the app's value differs from the refit.

    The constants are read by attribute from the rules module; a missing name is a mismatch row
    (empty result = match).
    """
    lines: list[str] = []
    for name, refit in coefs.by_name().items():
        shipped = getattr(blunder_check_rules, name, None)
        if shipped is None:
            lines.append(f"| {name} | missing | {refit:.{COEF_DECIMALS}f} |")
        elif abs(shipped - refit) > CHECK_CONSTANTS_TOLERANCE:
            lines.append(f"| {name} | {shipped:.{COEF_DECIMALS}f} | {refit:.{COEF_DECIMALS}f} |")
    return lines


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit the facepalm score on the features table.")
    parser.add_argument("--features", type=Path, required=True, help="features TSV")
    parser.add_argument("--out", type=Path, required=True, help="markdown report to write")
    parser.add_argument("--seed", type=int, default=FIT_SEED)
    parser.add_argument("--folds", type=int, default=CV_FOLDS)
    parser.add_argument("--threshold", type=float, default=FIT_SELECTION_THRESHOLD)
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help=(
            "the owner label TSV, read only for the comments and links of the owner section "
            "(D-13); the fit itself takes its labels from --features"
        ),
    )
    parser.add_argument(
        "--check-constants",
        action="store_true",
        help=(
            "after fitting, compare the six FACEPALM_* constants of the app with the refit; "
            f"exit {EXIT_CONSTANTS_MISMATCH} with a shipped-vs-refit table when they differ"
        ),
    )
    parser.add_argument(
        "--gate",
        choices=GATES,
        default=DEFAULT_GATE,
        help=(
            "key-move gate of the chosen shape: type = the 257 type rule (262 D-04); "
            "loss = the Phase 259 gate, reproduces the 2026-11-22 constants"
        ),
    )
    return parser.parse_args(argv)


def _check_constants(coefs: ScalarCoefs) -> int:
    """Exit code of --check-constants: EXIT_OK on a match, else print the shipped-vs-refit table."""
    mismatches = constants_mismatches(coefs)
    if not mismatches:
        print("constants match: the app constants are the refit of this features table")
        return EXIT_OK
    print("constants differ from the refit:", file=sys.stderr)
    print("| constant | shipped | refit |\n|---|---|---|", file=sys.stderr)
    print("\n".join(mismatches), file=sys.stderr)
    return EXIT_CONSTANTS_MISMATCH


def _fit_and_render(table: FeatureTable, args: argparse.Namespace) -> tuple[str, ScalarCoefs]:
    """Run the fit; the markdown report and the refit coefficients."""
    # Read first: a bad labels file fails before the fit.
    notes = None if args.labels is None else load_label_notes(args.labels)
    outcome = run_fit(
        table, threshold=args.threshold, folds=args.folds, seed=args.seed, gate=args.gate
    )
    report = render_report(
        outcome,
        features_name=args.features.name,
        threshold=args.threshold,
        folds=args.folds,
        seed=args.seed,
        notes=notes,
    )
    return report, outcome.coefs


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report, coefs = _fit_and_render(load_features(args.features), args)
    except FitError as exc:
        print(f"fit failed: {exc}", file=sys.stderr)
        return EXIT_FIT_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    print(f"wrote {args.out}")
    if args.check_constants:
        return _check_constants(coefs)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
