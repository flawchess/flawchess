"""Fit the facepalm score by logistic regression on the owner's labels (Phase 250 D-01, D-03).

Reads a committed features table (``facepalm_features.py`` output) and nothing else: no
cache, no database, no Maia. Newton-Raphson (IRLS) logistic regression with an intercept on
the decided labels (1 = fair, 0 = unfair), seeded K-fold cross-validation, a passer table
(fair / unfair counts among rows scoring at or above a threshold, from out-of-fold
predictions), and a ready-to-paste constants block.

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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.blunder_check_rules import (  # noqa: E402
    FACEPALM_SCORE_MIN,
    LINE_DEPTH,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (  # noqa: E402
    FACEPALM_MODEL,
    FacepalmModel,
    facepalm_score,
    loss_feature,
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

# Form B's binary loss input is 1 when the depth-3 net loss is at least this (or a mate is in sight).
BINARY_LOSS_MIN: int = 2
# Form A clip candidates: no clip (the loss may be negative) or a lower clip at 0.
LOSS_FLOOR_CANDIDATES: tuple[int | None, ...] = (None, 0)
# CV AUCs closer than this are a tie; the out-of-fold fair share among passers then decides.
AUC_TIE_TOLERANCE: float = 0.005
# Sets used for the train / holdout split (sets 1-5 fit, set 6 is the blind validation set).
TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5")
TEST_SET: str = "6"

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

CONSTANT_NAMES: tuple[str, ...] = (
    "FACEPALM_INTERCEPT",
    "FACEPALM_PLAYED_COEF",
    "FACEPALM_SPREAD_COEF",
    "FACEPALM_LOSS_COEF",
    "FACEPALM_LOSS_FLOOR",
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


def load_features(path: Path) -> list[FitRow]:
    """Read the features TSV; raises FitError when the file is not a features table."""
    try:
        text = path.read_text()
    except OSError as exc:
        raise FitError("features file unreadable") from exc
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    if reader.fieldnames is None or any(col not in reader.fieldnames for col in REQUIRED_COLUMNS):
        raise FitError("features file lacks the required columns")
    rows: list[FitRow] = []
    for record in reader:
        rows.append(
            FitRow(
                n=record["n"],
                set_id=record["set"],
                label=_opt_float(record["label"]),
                played_prob=_opt_float(record["played_prob"]),
                reply_spread=_opt_float(record["reply_spread"]),
                line_loss_3=_opt_int(record["line_loss_3"]),
                line_mate_ply=_opt_int(record["line_mate_ply"]),
            )
        )
    if not rows:
        raise FitError("features file has no rows")
    return rows


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


def holdout_split(
    usable: Sequence[FitRow], loss_floor: int | None, threshold: float
) -> SplitResult:
    """Fit Form A on sets 1-5, report AUC and the passer table on set 6."""
    train = [row for row in usable if row.set_id in TRAIN_SETS]
    test = [row for row in usable if row.set_id == TEST_SET]
    thresholds = thresholds_for(threshold)
    if not train or not test:
        return SplitResult(len(train), len(test), None, [], "train or holdout set is empty")
    try:
        coef = fit_logistic(design_matrix(train, "a_log_played", loss_floor), labels_of(train))
        y_test = labels_of(test)
        scores = sigmoid(design_matrix(test, "a_log_played", loss_floor) @ coef)
        return SplitResult(
            len(train),
            len(test),
            auc(scores, y_test),
            passer_table(scores, y_test, thresholds),
            "",
        )
    except FitError as exc:
        return SplitResult(len(train), len(test), None, [], f"unavailable: {exc}")


def score_extras(rows: Sequence[FitRow], model: FacepalmModel) -> list[ExtraScore]:
    """Score the unlabelled rows with the shipped model (None when an input is NULL)."""
    return [
        ExtraScore(
            row=row,
            score=facepalm_score(
                played_prob=row.played_prob,
                reply_spread=row.reply_spread,
                loss_3=row.line_loss_3,
                mate_ply=row.line_mate_ply,
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


def _split_section(outcome: FitOutcome) -> list[str]:
    split = outcome.split
    lines = [
        "## Sets 1-5 vs set 6",
        "",
        f"Form A fitted on sets {TRAIN_SETS[0]}-{TRAIN_SETS[-1]} ({split.train_rows} usable rows), "
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


def _extra_section(outcome: FitOutcome, threshold: float) -> list[str]:
    lines = [
        "## Extra rows",
        "",
        f"Unlabelled rows scored with the Form A model below (threshold {threshold}).",
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
        *_split_section(outcome),
        *_extra_section(outcome, threshold),
        *_constants_section(outcome.model),
    ]
    return "\n".join(lines)


def constants_mismatches(shipped: FacepalmModel, refit: FacepalmModel) -> list[str]:
    """One table line per field where the refit differs from the shipped model (empty = match)."""
    fields: tuple[tuple[str, float, float], ...] = (
        ("FACEPALM_INTERCEPT", shipped.intercept, refit.intercept),
        ("FACEPALM_PLAYED_COEF", shipped.played_coef, refit.played_coef),
        ("FACEPALM_SPREAD_COEF", shipped.spread_coef, refit.spread_coef),
        ("FACEPALM_LOSS_COEF", shipped.loss_coef, refit.loss_coef),
    )
    lines = [
        f"| {name} | {old:.{COEF_DECIMALS}f} | {new:.{COEF_DECIMALS}f} |"
        for name, old, new in fields
        if abs(old - new) > CHECK_CONSTANTS_TOLERANCE
    ]
    if shipped.loss_floor != refit.loss_floor:
        lines.append(f"| FACEPALM_LOSS_FLOOR | {shipped.loss_floor} | {refit.loss_floor} |")
    return lines


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit the facepalm score on the features table.")
    parser.add_argument("--features", type=Path, required=True, help="features TSV")
    parser.add_argument("--out", type=Path, required=True, help="markdown report to write")
    parser.add_argument("--seed", type=int, default=FIT_SEED)
    parser.add_argument("--folds", type=int, default=CV_FOLDS)
    parser.add_argument("--threshold", type=float, default=FACEPALM_SCORE_MIN)
    parser.add_argument(
        "--loss-floor",
        choices=("auto", "none", "0"),
        default="auto",
        help="Form A clip: auto picks by CV AUC then fair share; none / 0 force it",
    )
    parser.add_argument(
        "--check-constants",
        action="store_true",
        help=(
            "after fitting, compare the chosen Form A model with the shipped FACEPALM_MODEL; "
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = load_features(args.features)
        outcome = run_fit(
            rows,
            threshold=args.threshold,
            folds=args.folds,
            seed=args.seed,
            loss_floor_mode=args.loss_floor,
        )
    except FitError as exc:
        print(f"fit failed: {exc}", file=sys.stderr)
        return EXIT_FIT_ERROR
    report = render_report(
        outcome,
        features_name=args.features.name,
        threshold=args.threshold,
        folds=args.folds,
        seed=args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    print(f"wrote {args.out}")
    if args.check_constants:
        return _check_constants(outcome.model)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
