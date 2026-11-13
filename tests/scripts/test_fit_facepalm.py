"""Tests for the facepalm score fit (Phase 250 plan 02, D-01 / D-03)."""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from app.services.blunder_check_rules import PLAYED_PROB_OFFSET
from app.services.facepalm_score import FacepalmModel, loss_feature
from scripts.blunder_check import fit_facepalm
from scripts.blunder_check.facepalm_features import FEATURE_COLUMNS

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
    lines = ["\t".join(FEATURE_COLUMNS)]
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
    cells = {col: "" for col in FEATURE_COLUMNS}
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
    return "\t".join(cells[col] for col in FEATURE_COLUMNS)


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
    lines = ["\t".join(FEATURE_COLUMNS)]
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
                fit_facepalm.split_usable(fit_facepalm.load_features(features))[0],
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
