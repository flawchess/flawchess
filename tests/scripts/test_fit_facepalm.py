"""Tests for the facepalm score fit (Phase 250 plan 02, D-01 / D-03)."""

from __future__ import annotations

import math
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from app.services.blunder_check_rules import (
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
    MaterialForm,
    SpreadForm,
)
from app.services.facepalm_score import (
    FacepalmFacts,
    FacepalmModel,
    facepalm_score,
    loss_feature,
    missed_feature,
)
from scripts.blunder_check import fit_facepalm
from scripts.blunder_check.facepalm_features import FEATURE_COLUMNS

# The committed 2026-11-13 table's header (the "legacy" schema the fit still reads).
LEGACY_FEATURE_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "game_id",
    "ply",
    "label",
    "pinned_elo",
    "played_prob",
    "reply_spread",
    "line_loss_1",
    "line_loss_3",
    "line_loss_5",
    "line_loss_7",
    "line_loss_9",
    "line_mate_ply",
    "pv_source",
    "pv_plies",
    "note",
)
LEGACY_FEATURES = (
    Path(__file__).resolve().parents[2] / "reports/blunder-check/facepalm-features-2026-11-13.tsv"
)

SYNTHETIC_ROWS: int = 4000
SYNTHETIC_SEED: int = 9
# Known generating model: intercept, played (on ln(p + offset)), spread, loss.
TRUE_COEFS: tuple[float, float, float, float] = (1.0, -0.7, -0.7, 0.3)
SYNTHETIC_MATE_SHARE: float = 0.03
SYNTHETIC_SETS: int = 6
# Smallest tolerance the seeded run passes with.
RECOVERY_TOLERANCE: float = 0.07
LOSS_RANGE: tuple[int, int] = (-3, 8)
MATE_LINE_LOSS: int = 9


def write_synthetic_features(path: Path) -> None:
    """A features TSV of SYNTHETIC_ROWS rows drawn from TRUE_COEFS, plus one extra row."""
    rng = np.random.default_rng(SYNTHETIC_SEED)
    played = rng.uniform(0.0, 0.6, SYNTHETIC_ROWS)
    spread = rng.uniform(1.0, 10.0, SYNTHETIC_ROWS)
    loss3 = rng.integers(LOSS_RANGE[0], LOSS_RANGE[1] + 1, SYNTHETIC_ROWS)
    is_mate = rng.uniform(0.0, 1.0, SYNTHETIC_ROWS) < SYNTHETIC_MATE_SHARE
    draws = rng.uniform(0.0, 1.0, SYNTHETIC_ROWS)
    lines = ["\t".join(LEGACY_FEATURE_COLUMNS)]
    for i in range(SYNTHETIC_ROWS):
        mate_ply = 1 if is_mate[i] else None
        loss_value = MATE_LINE_LOSS if is_mate[i] else int(loss3[i])
        feature = loss_feature(loss_value, mate_ply, loss_floor=None)
        assert feature is not None
        z = (
            TRUE_COEFS[0]
            + TRUE_COEFS[1] * np.log(played[i] + PLAYED_PROB_OFFSET)
            + TRUE_COEFS[2] * spread[i]
            + TRUE_COEFS[3] * feature
        )
        label = 1 if draws[i] < 1.0 / (1.0 + np.exp(-z)) else 0
        lines.append(
            _row(
                str(i + 1),
                str(i % SYNTHETIC_SETS + 1),
                label,
                played[i],
                spread[i],
                loss_value,
                mate_ply,
            )
        )
    lines.append(_row("extra", "extra", "", 0.02, 3.0, 0, None))
    path.write_text("\n".join(lines) + "\n")


def _row(
    n: str,
    set_id: str,
    label: int | str,
    played: float,
    spread: float,
    loss3: int,
    mate_ply: int | None,
) -> str:
    cells = {col: "" for col in LEGACY_FEATURE_COLUMNS}
    cells.update(
        {
            "n": n,
            "set": set_id,
            "game_id": "1",
            "ply": "1",
            "label": str(label),
            "played_prob": f"{played:.6g}",
            "reply_spread": f"{spread:.6g}",
            "line_loss_3": str(loss3),
            "line_mate_ply": "" if mate_ply is None else str(mate_ply),
            "pv_source": "db",
        }
    )
    return "\t".join(cells[col] for col in LEGACY_FEATURE_COLUMNS)


def _constants(report: str) -> dict[str, float | None]:
    section = report.split("## Constants", 1)[1]
    values: dict[str, float | None] = {}
    for name in fit_facepalm.CONSTANT_NAMES:
        match = re.search(rf"^{name}: [^=]+= (\S+)$", section, flags=re.MULTILINE)
        assert match is not None, name
        values[name] = None if match.group(1) == "None" else float(match.group(1))
    return values


def test_synthetic_recovery_and_constants_block(tmp_path: Path) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    out = tmp_path / "report.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    report = out.read_text()
    for heading in ("## Data", "## Form A", "## Constants"):
        assert heading in report
    constants = _constants(report)
    recovered = (
        constants["FACEPALM_INTERCEPT"],
        constants["FACEPALM_PLAYED_COEF"],
        constants["FACEPALM_SPREAD_COEF"],
        constants["FACEPALM_LOSS_COEF"],
    )
    for got, truth in zip(recovered, TRUE_COEFS):
        assert got is not None
        assert abs(got - truth) < RECOVERY_TOLERANCE


def _refit_model(features: Path, out: Path) -> FacepalmModel:
    """The model a plain run of the script ships for `features`, read from its constants block."""
    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0
    constants = _constants(out.read_text())
    values = [
        constants[name]
        for name in (
            "FACEPALM_INTERCEPT",
            "FACEPALM_PLAYED_COEF",
            "FACEPALM_SPREAD_COEF",
            "FACEPALM_LOSS_COEF",
        )
    ]
    assert all(value is not None for value in values)
    intercept, played, spread, loss = (float(v) for v in values if v is not None)
    floor = constants["FACEPALM_LOSS_FLOOR"]
    return FacepalmModel(
        intercept=intercept,
        played_coef=played,
        spread_coef=spread,
        loss_coef=loss,
        loss_floor=None if floor is None else int(floor),
    )


def test_check_constants_exits_0_when_the_shipped_model_is_the_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", _refit_model(features, tmp_path / "a.md"))

    argv = ["--features", str(features), "--out", str(tmp_path / "b.md"), "--check-constants"]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_OK


def test_check_constants_exits_6_and_prints_the_table_on_a_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    refit = _refit_model(features, tmp_path / "a.md")
    drifted = FacepalmModel(
        intercept=refit.intercept + 2 * fit_facepalm.CHECK_CONSTANTS_TOLERANCE,
        played_coef=refit.played_coef,
        spread_coef=refit.spread_coef,
        loss_coef=refit.loss_coef,
        loss_floor=None if refit.loss_floor is not None else 0,
    )
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", drifted)

    argv = ["--features", str(features), "--out", str(tmp_path / "b.md"), "--check-constants"]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_CONSTANTS_MISMATCH
    err = capsys.readouterr().err
    assert "FACEPALM_INTERCEPT" in err
    assert "FACEPALM_LOSS_FLOOR" in err
    assert "FACEPALM_PLAYED_COEF" not in err


def test_same_seed_gives_byte_identical_reports(tmp_path: Path) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(first)]) == 0
    assert fit_facepalm.main(["--features", str(features), "--out", str(second)]) == 0

    assert first.read_bytes() == second.read_bytes()


def test_auc_average_ranks_for_ties() -> None:
    scores = np.array([0.1, 0.4, 0.4, 0.9])
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    # pairs (pos, neg): 0.4 vs 0.1 win, 0.4 vs 0.4 tie, 0.9 vs both win -> (1 + 0.5 + 2) / 4
    assert fit_facepalm.auc(scores, labels) == 0.875


def test_cv_fold_ids_deterministic_and_balanced() -> None:
    first = fit_facepalm.cv_fold_ids(105, 10, 7)
    second = fit_facepalm.cv_fold_ids(105, 10, 7)
    assert np.array_equal(first, second)
    sizes = np.bincount(first)
    assert sizes.max() - sizes.min() <= 1
    assert not np.array_equal(first, fit_facepalm.cv_fold_ids(105, 10, 8))


# ---------------------------------------------------------------------------
# Task 2: Form B, clip choice, split, extra rows, failure exit
# ---------------------------------------------------------------------------


def _fit_row(
    played: float = 0.1,
    spread: float = 3.0,
    loss3: int | None = 0,
    mate_ply: int | None = None,
    label: float | None = 1.0,
    set_id: str = "1",
) -> fit_facepalm.FitRow:
    return fit_facepalm.FitRow(
        n="1",
        set_id=set_id,
        label=label,
        played_prob=played,
        reply_spread=spread,
        line_loss_3=loss3,
        line_mate_ply=mate_ply,
    )


def test_form_b_design_matrix_uses_raw_played_and_a_binary_loss() -> None:
    rows = [
        _fit_row(played=0.2, spread=4.0, loss3=1),  # below BINARY_LOSS_MIN
        _fit_row(played=0.3, spread=5.0, loss3=fit_facepalm.BINARY_LOSS_MIN),
        _fit_row(played=0.4, spread=6.0, loss3=-4, mate_ply=3),  # mate within LINE_DEPTH
        _fit_row(played=0.5, spread=7.0, loss3=0, mate_ply=5),  # mate beyond LINE_DEPTH
    ]

    x = fit_facepalm.design_matrix(rows, "b_raw_played_binary_loss", None)

    assert x.tolist() == [
        [1.0, 0.2, 4.0, 0.0],
        [1.0, 0.3, 5.0, 1.0],
        [1.0, 0.4, 6.0, 1.0],
        [1.0, 0.5, 7.0, 0.0],
    ]


def test_form_a_design_matrix_applies_the_loss_floor() -> None:
    rows = [_fit_row(loss3=-2)]

    unclipped = fit_facepalm.design_matrix(rows, "a_log_played", None)
    clipped = fit_facepalm.design_matrix(rows, "a_log_played", 0)

    assert unclipped[0, 3] == -2.0
    assert clipped[0, 3] == 0.0
    assert unclipped[0, 1] == pytest.approx(math.log(0.1 + PLAYED_PROB_OFFSET))


def test_choose_loss_floor_prefers_the_higher_auc() -> None:
    results = [
        fit_facepalm.ClipResult(loss_floor=None, cv_auc=0.80, fair_share=0.70),
        fit_facepalm.ClipResult(
            loss_floor=0, cv_auc=0.80 + 2 * fit_facepalm.AUC_TIE_TOLERANCE, fair_share=0.60
        ),
    ]

    floor, _reason = fit_facepalm.choose_loss_floor(results)

    assert floor == 0


def test_choose_loss_floor_falls_back_to_fair_share_within_the_tolerance() -> None:
    near = fit_facepalm.AUC_TIE_TOLERANCE / 2
    results = [
        fit_facepalm.ClipResult(loss_floor=None, cv_auc=0.80, fair_share=0.70),
        fit_facepalm.ClipResult(loss_floor=0, cv_auc=0.80 + near, fair_share=0.75),
    ]
    assert fit_facepalm.choose_loss_floor(results)[0] == 0

    swapped = [
        fit_facepalm.ClipResult(loss_floor=None, cv_auc=0.80, fair_share=0.75),
        fit_facepalm.ClipResult(loss_floor=0, cv_auc=0.80 + near, fair_share=0.70),
    ]
    assert fit_facepalm.choose_loss_floor(swapped)[0] is None


def test_choose_loss_floor_treats_no_passers_as_the_worst_share() -> None:
    results = [
        fit_facepalm.ClipResult(loss_floor=None, cv_auc=0.80, fair_share=None),
        fit_facepalm.ClipResult(loss_floor=0, cv_auc=0.80, fair_share=0.5),
    ]

    assert fit_facepalm.choose_loss_floor(results)[0] == 0


def test_choose_loss_floor_tie_picks_no_clip() -> None:
    results = [
        fit_facepalm.ClipResult(loss_floor=0, cv_auc=0.80, fair_share=0.70),
        fit_facepalm.ClipResult(loss_floor=None, cv_auc=0.80, fair_share=0.70),
    ]

    assert fit_facepalm.choose_loss_floor(results)[0] is None


def test_report_has_every_section_and_scores_the_extra_row(tmp_path: Path) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    out = tmp_path / "report.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    report = out.read_text()
    for heading in (
        "## Data",
        "## Form A",
        "## Form B",
        "## Clip choice",
        "## Sets 1-5 vs set 6",
        "## Extra rows",
        "## Constants",
    ):
        assert heading in report
    assert "A ranking, not a probability (D-01)" in report
    extra_section = report.split("## Extra rows", 1)[1].split("## Constants", 1)[0]
    assert "row extra" in extra_section
    assert ("AT OR ABOVE THRESHOLD" in extra_section) != ("below threshold" in extra_section)
    split_section = report.split("## Sets 1-5 vs set 6", 1)[1].split("## Extra rows", 1)[0]
    assert "AUC on set 6" in split_section


def test_forced_loss_floor_is_stated_and_used(tmp_path: Path) -> None:
    features = tmp_path / "features.tsv"
    write_synthetic_features(features)
    out = tmp_path / "report.md"

    code = fit_facepalm.main(["--features", str(features), "--out", str(out), "--loss-floor", "0"])

    assert code == 0
    report = out.read_text()
    assert "the clip was forced" in report
    assert "FACEPALM_LOSS_FLOOR: int | None = 0" in report


def test_separable_labels_exit_2_and_write_no_report(tmp_path: Path) -> None:
    lines = ["\t".join(LEGACY_FEATURE_COLUMNS)]
    for i in range(40):
        fair = i % 2 == 0
        # The reply spread alone separates the labels perfectly.
        lines.append(
            _row(str(i), "1", 1 if fair else 0, 0.1 + i * 0.001, 2.0 if fair else 9.0, i % 3, None)
        )
    features = tmp_path / "features.tsv"
    features.write_text("\n".join(lines) + "\n")
    out = tmp_path / "report.md"

    assert (
        fit_facepalm.main(["--features", str(features), "--out", str(out)])
        == fit_facepalm.EXIT_FIT_ERROR
    )
    assert not out.exists()
    with pytest.raises(fit_facepalm.FitError):
        fit_facepalm.fit_logistic(
            fit_facepalm.design_matrix(
                fit_facepalm.split_usable(fit_facepalm.load_features(features).rows)[0],
                "a_log_played",
                None,
            ),
            np.array([1.0 if i % 2 == 0 else 0.0 for i in range(40)]),
        )


def test_exclusions_are_counted_per_reason() -> None:
    rows = [
        _fit_row(label=0.5),
        _fit_row(label=None),
        _fit_row(label=1.0),
        fit_facepalm.FitRow("9", "1", 1.0, None, 3.0, 0, None),
        fit_facepalm.FitRow("9", "1", 1.0, 0.1, None, 0, None),
        fit_facepalm.FitRow("9", "1", 1.0, 0.1, 3.0, None, None),
        fit_facepalm.FitRow("9", "1", 0.0, 0.1, 3.0, None, 2),  # a mate settles a short line
    ]

    usable, excluded = fit_facepalm.split_usable(rows)

    assert len(usable) == 2
    assert excluded == {
        fit_facepalm.REASON_UNDECIDED: 1,
        fit_facepalm.REASON_NO_LABEL: 1,
        fit_facepalm.REASON_NO_PLAYED: 1,
        fit_facepalm.REASON_NO_SPREAD: 1,
        fit_facepalm.REASON_NO_LOSS: 1,
    }


def test_load_features_rejects_a_foreign_file(tmp_path: Path) -> None:
    other = tmp_path / "other.tsv"
    other.write_text("a\tb\n1\t2\n")

    with pytest.raises(fit_facepalm.FitError):
        fit_facepalm.load_features(other)


def test_help_lists_the_documented_flags() -> None:
    root = Path(fit_facepalm.__file__).resolve().parents[2]
    for script, flags in (
        (
            "scripts/blunder_check/fit_facepalm.py",
            ("--features", "--loss-floor", "--check-constants"),
        ),
        ("scripts/blunder_check/facepalm_features.py", ("--pv-cache", "--extra")),
    ):
        done = subprocess.run(
            [sys.executable, "-I", str(root / script), "--help"],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        for flag in flags:
            assert flag in done.stdout


# ---------------------------------------------------------------------------
# Phase 254 plan 04: the facts schema
# ---------------------------------------------------------------------------

FACTS_ROWS: int = 1200
FACTS_SEED: int = 17
FACTS_SETS: int = 7
# Known generating model of the synthetic facts table: the combined form (one coefficient on
# loss + missed, D-06), the spread on every row, no Maia best-move or pre-blunder terms.
FACTS_TRUE_INTERCEPT: float = 0.4
FACTS_TRUE_PLAYED: float = -0.7
FACTS_TRUE_SPREAD: float = -0.2
FACTS_TRUE_MATERIAL: float = 0.8
# Row mix: shares of pure misses, losses and rows that are neither (the rest).
FACTS_PURE_MISS_SHARE: float = 0.4
FACTS_LOSS_SHARE: float = 0.4
FACTS_MATE_SHARE: float = 0.03
FACTS_MAX_PLAYED_PROB: float = 0.6
FACTS_SPREAD_RANGE: tuple[float, float] = (1.0, 10.0)
FACTS_BEST_PROB_RANGE: tuple[float, float] = (0.05, 0.9)
FACTS_PRE_SPREAD_RANGE: tuple[float, float] = (1.0, 10.0)


def _facts_line_values(
    rng: np.random.Generator,
) -> tuple[int | None, int | None, int | None, int | None]:
    """(played_3, line_mate_ply, best_3, best_mate_ply) of one synthetic row."""
    kind = rng.uniform()
    if kind < FACTS_MATE_SHARE:
        return None, 2, 0, None  # the blunderer is mated; the best line holds the balance
    if kind < 2 * FACTS_MATE_SHARE:
        return 0, None, None, 1  # a missed mate
    kind = rng.uniform()
    if kind < FACTS_PURE_MISS_SHARE:
        played = int(rng.integers(0, 4))
        return played, None, played + int(rng.integers(1, 8)), None
    if kind < FACTS_PURE_MISS_SHARE + FACTS_LOSS_SHARE:
        return -int(rng.integers(1, 6)), None, int(rng.integers(-1, 3)), None
    played = int(rng.integers(0, 3))
    return played, None, played, None


def _facts_cells(index: int, label: object, rng: np.random.Generator, noise: bool) -> str:
    cells = {col: "" for col in FEATURE_COLUMNS}
    played_3, mate_ply, best_3, best_mate_ply = _facts_line_values(rng)
    played = rng.uniform(0.0, FACTS_MAX_PLAYED_PROB)
    spread = rng.uniform(*FACTS_SPREAD_RANGE)
    cells.update(
        {
            "n": str(index),
            "set": str(index % FACTS_SETS + 1),
            "game_id": "1",
            "ply": "1",
            "label": str(label),
            "played_prob": f"{played:.6g}",
            "reply_spread": f"{spread:.6g}",
            "best_prob": f"{rng.uniform(*FACTS_BEST_PROB_RANGE):.6g}" if noise else "",
            "pre_spread": f"{rng.uniform(*FACTS_PRE_SPREAD_RANGE):.6g}" if noise else "",
            "played_mat_3": "" if played_3 is None else str(played_3),
            "line_mate_ply": "" if mate_ply is None else str(mate_ply),
            "best_mat_3": "" if best_3 is None else str(best_3),
            "best_mate_ply": "" if best_mate_ply is None else str(best_mate_ply),
            "pv_source": "db",
        }
    )
    return "\t".join(cells[col] for col in FEATURE_COLUMNS)


def _true_label(
    row: dict[str, str], draw: float, *, best_prob_effect: float, pre_spread_effect: float
) -> int:
    """The label the generating model gives a synthetic row (the twins' own features).

    The two effects add `ln(best_prob + offset)` and `pre_spread` terms (0 = pure noise columns).
    """
    played_3 = None if row["played_mat_3"] == "" else int(row["played_mat_3"])
    best_3 = None if row["best_mat_3"] == "" else int(row["best_mat_3"])
    mate_ply = None if row["line_mate_ply"] == "" else int(row["line_mate_ply"])
    best_mate = None if row["best_mate_ply"] == "" else int(row["best_mate_ply"])
    loss = loss_feature(None if played_3 is None else -played_3, mate_ply, loss_floor=0)
    missed = missed_feature(
        played_3, best_3, best_mate, missed_floor=0, missed_cap=LOSS_CAP, missed_mate=MATE_LOSS
    )
    assert loss is not None
    z = (
        FACTS_TRUE_INTERCEPT
        + FACTS_TRUE_PLAYED * math.log(float(row["played_prob"]) + PLAYED_PROB_OFFSET)
        + FACTS_TRUE_SPREAD * float(row["reply_spread"])
        + FACTS_TRUE_MATERIAL * (loss + missed)
        + best_prob_effect * math.log(float(row["best_prob"] or "1") + PLAYED_PROB_OFFSET)
        + pre_spread_effect * float(row["pre_spread"] or "0")
    )
    return 1 if draw < 1.0 / (1.0 + math.exp(-z)) else 0


def write_synthetic_facts(
    path: Path,
    *,
    noise: bool = True,
    best_prob_effect: float = 0.0,
    pre_spread_effect: float = 0.0,
    null_best_every: int = 0,
) -> None:
    """A facts-schema table of FACTS_ROWS rows from the generating model, plus one extra row.

    `noise` fills best_prob and pre_spread with columns independent of the labels unless an
    effect makes the labels depend on them; `null_best_every` blanks the best line of every
    n-th row (the D-18 unknown best line).
    """
    rng = np.random.default_rng(FACTS_SEED)
    lines = ["\t".join(FEATURE_COLUMNS)]
    for index in range(FACTS_ROWS):
        # Labels need the row's own values, so draw the row first and label it afterwards.
        record = dict(zip(FEATURE_COLUMNS, _facts_cells(index + 1, "", rng, noise).split("\t")))
        record["label"] = str(
            _true_label(
                record,
                rng.uniform(),
                best_prob_effect=best_prob_effect,
                pre_spread_effect=pre_spread_effect,
            )
        )
        if null_best_every and index % null_best_every == 0:
            record.update({"best_mat_3": "", "best_mate_ply": ""})
        lines.append("\t".join(record[col] for col in FEATURE_COLUMNS))
    # The last row is the unlabelled extra row (label cell empty, set "extra").
    extra = dict(zip(FEATURE_COLUMNS, _facts_cells(0, "", rng, noise).split("\t")))
    extra.update({"n": "extra", "set": "extra", "label": ""})
    lines.append("\t".join(extra[col] for col in FEATURE_COLUMNS))
    path.write_text("\n".join(lines) + "\n")


def test_fit_loads_both_schemas(tmp_path: Path) -> None:
    legacy = fit_facepalm.load_features(LEGACY_FEATURES)
    facts_path = tmp_path / "facts.tsv"
    write_synthetic_facts(facts_path)
    facts = fit_facepalm.load_features(facts_path)

    assert legacy.schema == "legacy"
    assert facts.schema == "facts"
    # Legacy rows carry played_3 = -line_loss_3 and no best-line or pre-blunder facts.
    first = legacy.rows[1]
    assert first.line_loss_3 is not None and first.played_3 == -first.line_loss_3
    assert first.best_3 is None and first.best_prob is None
    row = facts.rows[0]
    assert row.played_3 is None or row.line_loss_3 == -row.played_3
    assert any(r.best_3 is not None and r.best_prob is not None for r in facts.rows)


def test_check_constants_legacy_still_passes(tmp_path: Path) -> None:
    argv = [
        "--features",
        str(LEGACY_FEATURES),
        "--out",
        str(tmp_path / "legacy.md"),
        "--check-constants",
    ]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_OK


def test_check_constants_reports_every_field_that_moved() -> None:
    shipped = FacepalmModel(
        intercept=1.0,
        played_coef=-0.5,
        spread_coef=-0.2,
        loss_coef=0.9,
        loss_floor=0,
        material_form="combined",
        missed_coef=0.3,
        missed_floor=None,
        missed_cap=9,
        missed_mate=7,
        spread_form="loss_only",
        best_prob_coef=0.2,
        pre_spread_coef=-0.1,
    )
    pre_refit = FacepalmModel(
        intercept=1.0, played_coef=-0.5, spread_coef=-0.2, loss_coef=0.9, loss_floor=0
    )

    table = "\n".join(fit_facepalm.constants_mismatches(shipped, pre_refit))

    # Everything but the five Phase 250 constants and the unchanged loss floor.
    for name in (
        "FACEPALM_MATERIAL_FORM",
        "FACEPALM_MISSED_COEF",
        "FACEPALM_MISSED_FLOOR",
        "FACEPALM_MISSED_CAP",
        "FACEPALM_MISSED_MATE",
        "FACEPALM_SPREAD_FORM",
        "FACEPALM_BEST_PROB_COEF",
        "FACEPALM_PRE_SPREAD_COEF",
    ):
        assert name in table, name
    for name in fit_facepalm.CONSTANT_NAMES:
        assert name not in table, name
    assert fit_facepalm.constants_mismatches(shipped, shipped) == []


def test_facts_schema_run_prints_every_model_constant(tmp_path: Path) -> None:
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    out = tmp_path / "report.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    section = out.read_text().split("## Constants", 1)[1]
    for name in fit_facepalm.MODEL_CONSTANT_NAMES:
        assert re.search(rf"^{name}: [^=]+= \S+$", section, flags=re.MULTILINE), name


SPEC_SHAPES: tuple[fit_facepalm.CandidateSpec, ...] = (
    fit_facepalm.BASELINE_SPEC,
    fit_facepalm.CandidateSpec("combined", None, 9, "always"),
    fit_facepalm.CandidateSpec("split", 0, LOSS_CAP, "always", best_prob=True, pre_spread=True),
    fit_facepalm.CandidateSpec("combined", 0, LOSS_CAP, "loss_only", pre_spread=True),
    fit_facepalm.CandidateSpec("split", None, 9, "best_prob_for_misses"),
    fit_facepalm.CandidateSpec("combined", 0, 9, "best_prob_for_misses", pre_spread=True),
)


@pytest.mark.parametrize("spec", SPEC_SHAPES, ids=fit_facepalm.spec_label)
def test_design_matrix_is_the_shipped_twin(
    spec: fit_facepalm.CandidateSpec, tmp_path: Path
) -> None:
    """sigmoid(x @ coef) equals facepalm_score of the candidate model on every usable row."""
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    usable, _ = fit_facepalm.split_usable(fit_facepalm.load_features(features).rows)
    names = fit_facepalm.spec_columns(spec)
    coef = np.round(
        np.random.default_rng(3).normal(0.0, 0.5, len(names)), fit_facepalm.COEF_DECIMALS
    )
    model = fit_facepalm.model_from_spec(spec, coef)
    scores = fit_facepalm.sigmoid(fit_facepalm.spec_design_matrix(usable, spec) @ coef)

    for row, score in zip(usable, scores):
        twin = facepalm_score(
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
            lam=1.0,
            model=model,
        )
        assert twin == pytest.approx(float(score), abs=1e-9)


# ---------------------------------------------------------------------------
# Phase 254 plan 04 task 2: staged selection (D-06, D-07, D-08) and the D-13 report
# ---------------------------------------------------------------------------

NULL_BEST_EVERY: int = 7
STRONG_EFFECT: float = 0.6


class FactsRun:
    """A synthetic facts table fitted once with the default (auto) stages."""

    def __init__(self, directory: Path) -> None:
        self.features = directory / "facts.tsv"
        write_synthetic_facts(self.features, null_best_every=NULL_BEST_EVERY)
        self.out = directory / "report.md"
        self.exit_code = fit_facepalm.main(
            ["--features", str(self.features), "--out", str(self.out)]
        )
        self.report = self.out.read_text()
        self.settings = fit_facepalm.FitSettings(
            threshold=0.7, folds=fit_facepalm.CV_FOLDS, seed=fit_facepalm.FIT_SEED
        )
        self.usable, _ = fit_facepalm.split_usable(fit_facepalm.load_features(self.features).rows)


@pytest.fixture(scope="module")
def facts_run(tmp_path_factory: pytest.TempPathFactory) -> FactsRun:
    return FactsRun(tmp_path_factory.mktemp("facts-run"))


def _report_model(report: str) -> FacepalmModel:
    """The model a report's constants block ships, parsed back from the printed constants."""
    section = report.split("## Constants", 1)[1]
    raw: dict[str, str] = {}
    for name in fit_facepalm.MODEL_CONSTANT_NAMES:
        match = re.search(rf"^{name}: [^=]+= (\S+)$", section, flags=re.MULTILINE)
        assert match is not None, name
        raw[name] = match.group(1).strip('"')

    def optional_int(text: str) -> int | None:
        return None if text == "None" else int(text)

    return FacepalmModel(
        intercept=float(raw["FACEPALM_INTERCEPT"]),
        played_coef=float(raw["FACEPALM_PLAYED_COEF"]),
        spread_coef=float(raw["FACEPALM_SPREAD_COEF"]),
        loss_coef=float(raw["FACEPALM_LOSS_COEF"]),
        loss_floor=optional_int(raw["FACEPALM_LOSS_FLOOR"]),
        material_form=cast(MaterialForm, raw["FACEPALM_MATERIAL_FORM"]),
        missed_coef=float(raw["FACEPALM_MISSED_COEF"]),
        missed_floor=optional_int(raw["FACEPALM_MISSED_FLOOR"]),
        missed_cap=int(raw["FACEPALM_MISSED_CAP"]),
        missed_mate=int(raw["FACEPALM_MISSED_MATE"]),
        spread_form=cast(SpreadForm, raw["FACEPALM_SPREAD_FORM"]),
        best_prob_coef=float(raw["FACEPALM_BEST_PROB_COEF"]),
        pre_spread_coef=float(raw["FACEPALM_PRE_SPREAD_COEF"]),
    )


def test_staged_selection_is_deterministic(facts_run: FactsRun) -> None:
    rows = facts_run.usable
    first = fit_facepalm.run_facts_fit(rows, facts_run.settings)
    second = fit_facepalm.run_facts_fit(rows, facts_run.settings)

    assert first.model == second.model
    assert first.chosen.spec == second.chosen.spec
    assert [s.chosen.spec for s in first.stage3] == [s.chosen.spec for s in second.stage3]
    # A strong pure-miss signal: stage 1 carries the missed term and beats the pre-refit baseline.
    stage1 = first.stage1
    assert stage1.chosen.spec.missed
    assert stage1.reference is not None
    assert stage1.chosen.auc_mean > stage1.reference.auc_mean + 0.05
    # Columns independent of the labels earn nothing: both coefficients stay 0.0.
    assert first.model.best_prob_coef == 0.0
    assert first.model.pre_spread_coef == 0.0
    assert not first.chosen.spec.best_prob and not first.chosen.spec.pre_spread


@pytest.mark.parametrize("effect", ["best_prob", "pre_spread"])
def test_an_informative_input_is_kept(effect: str, tmp_path: Path) -> None:
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(
        features,
        best_prob_effect=STRONG_EFFECT if effect == "best_prob" else 0.0,
        pre_spread_effect=STRONG_EFFECT if effect == "pre_spread" else 0.0,
    )
    usable, _ = fit_facepalm.split_usable(fit_facepalm.load_features(features).rows)
    settings = fit_facepalm.FitSettings(0.7, fit_facepalm.CV_FOLDS, fit_facepalm.FIT_SEED)

    outcome = fit_facepalm.run_facts_fit(usable, settings)

    kept = outcome.model.best_prob_coef if effect == "best_prob" else outcome.model.pre_spread_coef
    assert kept != 0.0


def test_tie_prefers_simpler_model() -> None:
    near = fit_facepalm.AUC_TIE_TOLERANCE / 2
    simple = fit_facepalm.CandidateScore(free_coefs=4, cv_auc=0.80, fair_share=0.70)
    bigger = fit_facepalm.CandidateScore(free_coefs=5, cv_auc=0.80 + near, fair_share=0.70)

    assert fit_facepalm.choose_candidate([bigger, simple])[0] == 1
    assert fit_facepalm.choose_candidate([simple, bigger])[0] == 0
    # A full tie of equal size keeps the first listed (the incumbent comes first).
    twin = fit_facepalm.CandidateScore(free_coefs=4, cv_auc=0.80, fair_share=0.70)
    assert fit_facepalm.choose_candidate([simple, twin])[0] == 0


def test_choose_candidate_rules() -> None:
    tol = fit_facepalm.AUC_TIE_TOLERANCE
    share_tol = fit_facepalm.FAIR_SHARE_TIE_TOLERANCE
    low = fit_facepalm.CandidateScore(4, 0.80, 0.90)
    # Higher AUC by more than the tolerance wins whatever the shares are.
    high = fit_facepalm.CandidateScore(6, 0.80 + 2 * tol, 0.50)
    assert fit_facepalm.choose_candidate([low, high])[0] == 1
    # Within the tolerance the fair share decides, but only beyond its own tolerance.
    better_share = fit_facepalm.CandidateScore(6, 0.80 + tol / 2, 0.90 + 2 * share_tol)
    assert fit_facepalm.choose_candidate([low, better_share])[0] == 1
    noise_share = fit_facepalm.CandidateScore(6, 0.80 + tol / 2, 0.90 + share_tol / 2)
    assert fit_facepalm.choose_candidate([low, noise_share])[0] == 0
    # No passers is the worst share.
    no_passers = fit_facepalm.CandidateScore(4, 0.80, None)
    assert fit_facepalm.choose_candidate([no_passers, low])[0] == 1


def test_candidate_spec_rejects_contradictory_shapes() -> None:
    with pytest.raises(ValueError):
        fit_facepalm.CandidateSpec("combined", 0, LOSS_CAP, "always", missed=False)
    with pytest.raises(ValueError):
        fit_facepalm.CandidateSpec("split", 0, LOSS_CAP, "best_prob_for_misses", best_prob=True)


def test_forced_form_flags(tmp_path: Path, facts_run: FactsRun) -> None:
    out = tmp_path / "forced.md"
    argv = [
        "--features",
        str(facts_run.features),
        "--out",
        str(out),
        "--material-form",
        "split",
        "--spread-form",
        "loss_only",
    ]

    assert fit_facepalm.main(argv) == 0

    report = out.read_text()
    assert "forced by --material-form split" in report
    assert "forced by --spread-form loss_only" in report
    assert "forced by" not in facts_run.report
    model = _report_model(report)
    assert (model.material_form, model.spread_form) == ("split", "loss_only")


def test_check_constants_compares_against_the_forced_fit(
    tmp_path: Path, facts_run: FactsRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    forced = ["--material-form", "split", "--spread-form", "loss_only"]
    base = ["--features", str(facts_run.features), "--out", str(tmp_path / "a.md"), *forced]
    assert fit_facepalm.main(base) == 0
    monkeypatch.setattr(
        fit_facepalm, "FACEPALM_MODEL", _report_model((tmp_path / "a.md").read_text())
    )

    forced_check = [*base[:3], str(tmp_path / "b.md"), *forced, "--check-constants"]
    assert fit_facepalm.main(forced_check) == fit_facepalm.EXIT_OK
    # The unforced fit picks another shape, so the forced model no longer reproduces from it.
    unforced = ["--features", str(facts_run.features), "--out", str(tmp_path / "c.md")]
    assert (
        fit_facepalm.main([*unforced, "--check-constants"]) == fit_facepalm.EXIT_CONSTANTS_MISMATCH
    )


def test_check_constants_facts_reports_the_selectors(
    tmp_path: Path,
    facts_run: FactsRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    refit = _report_model(facts_run.report)
    assert refit.spread_form == "always"
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", replace(refit, spread_form="loss_only"))

    argv = [
        "--features",
        str(facts_run.features),
        "--out",
        str(tmp_path / "o.md"),
        "--check-constants",
    ]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_CONSTANTS_MISMATCH
    assert "FACEPALM_SPREAD_FORM" in capsys.readouterr().err


def test_flags_of_the_other_schema_are_an_error(tmp_path: Path, facts_run: FactsRun) -> None:
    out = str(tmp_path / "o.md")

    assert (
        fit_facepalm.main(
            ["--features", str(LEGACY_FEATURES), "--out", out, "--spread-form", "always"]
        )
        == fit_facepalm.EXIT_FIT_ERROR
    )
    assert (
        fit_facepalm.main(
            ["--features", str(facts_run.features), "--out", out, "--loss-floor", "none"]
        )
        == fit_facepalm.EXIT_FIT_ERROR
    )


def test_same_seed_gives_byte_identical_facts_reports(tmp_path: Path, facts_run: FactsRun) -> None:
    again = tmp_path / "again.md"

    assert fit_facepalm.main(["--features", str(facts_run.features), "--out", str(again)]) == 0

    assert again.read_text() == facts_run.report


def test_report_has_d13_sections(facts_run: FactsRun) -> None:
    report = facts_run.report
    assert facts_run.exit_code == 0

    for heading in (
        "## Data",
        "## Stage 1: material form (D-06)",
        "## Stage 2: reply-spread form (D-07)",
        "## Stage 3a",
        "## Stage 3b",
        "## Chosen model",
        "## Fair / unfair among passers by material type",
        "## Fair / unfair among passers by label set",
        "## Sets 1-5 vs set 6",
        "## Extra rows",
        "## Constants",
    ):
        assert heading in report, heading
    # Repeated-seed CV mean and spread sit next to the single-seed numbers.
    assert "CV AUC mean" in report and "CV AUC spread" in report
    # D-18: label rows whose best line is NULL are counted (every NULL_BEST_EVERY-th row).
    labelled = [
        row for row in fit_facepalm.load_features(facts_run.features).rows if row.label is not None
    ]
    null_best = sum(1 for row in labelled if row.best_3 is None and row.best_mate_ply is None)
    assert null_best >= FACTS_ROWS // NULL_BEST_EVERY
    assert f"{null_best} of {len(labelled)}" in report
    # D-13: a row per material type, a column per cut, split by label set as well.
    type_section = report.split("## Fair / unfair among passers by material type", 1)[1].split(
        "## Fair / unfair among passers by label set", 1
    )[0]
    for kind in ("loses", "misses", "loses_and_misses", "neither", "all"):
        assert re.search(rf"^\| {kind} \|", type_section, flags=re.MULTILINE), kind
    for cut in fit_facepalm.FIT_THRESHOLDS:
        assert f"score >= {cut:.2f}" in type_section
    set_section = report.split("## Fair / unfair among passers by label set", 1)[1].split(
        "## Sets 1-5 vs set 6", 1
    )[0]
    for set_id in range(1, FACTS_SETS + 1):
        assert re.search(rf"^\| {set_id} \|", set_section, flags=re.MULTILINE)
    # The constants block sets every FACEPALM_* model constant.
    constants = report.split("## Constants", 1)[1]
    for name in fit_facepalm.MODEL_CONSTANT_NAMES:
        assert re.search(rf"^{name}: ", constants, flags=re.MULTILINE), name
