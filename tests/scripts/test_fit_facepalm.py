"""Tests for the facepalm score fit (Phase 250 plan 02, D-01 / D-03)."""

from __future__ import annotations

import math
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from app.services.blunder_check_rules import (
    FACEPALM_DRILL_LAMBDA,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    MATERIAL_DECAY_RATIO,
    PLAYED_PROB_OFFSET,
    MaterialForm,
    MaterialInput,
    SpreadForm,
)
from app.services.facepalm_material import single_depth_material
from app.services.facepalm_score import (
    FacepalmFacts,
    FacepalmModel,
    facepalm_score,
    loss_feature,
    missed_feature,
)
from app.services.line_material import LINE_MATERIAL_SLOTS
from scripts.blunder_check import fit_facepalm
from scripts.blunder_check.facepalm_features import FEATURE_COLUMNS
from tests.facepalm_models import PHASE_250_MODEL, PHASE_254_MODEL

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

# The committed Phase 254 facts table (the one PHASE_254_MODEL was fitted on).
FEATURES_2026_11_15 = (
    Path(__file__).resolve().parents[2] / "reports/blunder-check/facepalm-features-2026-11-15.tsv"
)

# The committed Phase 256 facts table (the one the shipped FACEPALM_MODEL was refitted on, label
# sets 1-8, 256-07). REFIT_FIT_FLAGS are the flags of the recorded fit command that affect the
# constants: none forced (the owner took the cross-validated choice, 256 D-13). `--labels` is left
# out on purpose: it does not change the constants.
REFIT_FEATURES = (
    Path(__file__).resolve().parents[2] / "reports/blunder-check/facepalm-features-2026-11-16.tsv"
)
REFIT_FIT_FLAGS: tuple[str, ...] = ()

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


LEGACY_SPLIT_HEADING: str = (
    f"## Sets {fit_facepalm.LEGACY_TRAIN_SETS_TEXT} vs set {fit_facepalm.LEGACY_TEST_SET}"
)
FACTS_SPLIT_HEADING: str = f"## Sets {fit_facepalm.TRAIN_SETS_TEXT} vs set {fit_facepalm.TEST_SET}"


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
        LEGACY_SPLIT_HEADING,
        "## Extra rows",
        "## Constants",
    ):
        assert heading in report
    assert "A ranking, not a probability (D-01)" in report
    extra_section = report.split("## Extra rows", 1)[1].split("## Constants", 1)[0]
    assert "row extra" in extra_section
    assert ("AT OR ABOVE THRESHOLD" in extra_section) != ("below threshold" in extra_section)
    split_section = report.split(LEGACY_SPLIT_HEADING, 1)[1].split("## Extra rows", 1)[0]
    assert f"AUC on set {fit_facepalm.LEGACY_TEST_SET}" in split_section


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

    # The base filter no longer reads the reply spread (254 WR-03): the NULL-spread row stays,
    # and each candidate decides on it (`_spec_exclusion`).
    assert len(usable) == 3
    assert excluded == {
        fit_facepalm.REASON_UNDECIDED: 1,
        fit_facepalm.REASON_NO_LABEL: 1,
        fit_facepalm.REASON_NO_PLAYED: 1,
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
            (
                "--features",
                "--loss-floor",
                "--material-input",
                "--loss-gate",
                "--labels",
                "--check-constants",
            ),
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
FACTS_SETS: int = 8
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


# Deviation of the deeper odd slots from the depth-3 value in the synthetic arrays.
SLOT_DEVIATIONS: tuple[int, ...] = (-1, 0, 1)
DEEP_ODD_DEPTHS: tuple[int, ...] = (5, 7, 9)


def _line_cells(depth_3: int | None, fill_rng: np.random.Generator) -> list[str]:
    """The nine per-depth cells of one synthetic line (empty cells when depth 3 is NULL).

    Depth 1 is 0, depth 3 the row's own value, depths 5, 7, 9 deviate from it by -1, 0 or 1, and
    every even slot copies the odd slot before it. Drawn from `fill_rng`, never from the row's own
    generator, so the depth-3 columns and every label stay what they were before the arrays existed.
    """
    if depth_3 is None:
        return [""] * LINE_MATERIAL_SLOTS
    odd = {1: 0, 3: depth_3}
    for depth in DEEP_ODD_DEPTHS:
        odd[depth] = depth_3 + int(fill_rng.choice(SLOT_DEVIATIONS))
    slots = range(1, LINE_MATERIAL_SLOTS + 1)
    return [str(odd[depth if depth % 2 else depth - 1]) for depth in slots]


def _facts_cells(
    index: int,
    label: object,
    rng: np.random.Generator,
    noise: bool,
    fill_rng: np.random.Generator,
) -> str:
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
            "line_mate_ply": "" if mate_ply is None else str(mate_ply),
            "best_mate_ply": "" if best_mate_ply is None else str(best_mate_ply),
            "pv_source": "db",
        }
    )
    cells.update(zip(fit_facepalm.PLAYED_MAT_COLUMNS, _line_cells(played_3, fill_rng)))
    cells.update(zip(fit_facepalm.BEST_MAT_COLUMNS, _line_cells(best_3, fill_rng)))
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
    fill_rng = np.random.default_rng(FACTS_SEED + 1)
    lines = ["\t".join(FEATURE_COLUMNS)]
    for index in range(FACTS_ROWS):
        # Labels need the row's own values, so draw the row first and label it afterwards.
        cells = _facts_cells(index + 1, "", rng, noise, fill_rng)
        record = dict(zip(FEATURE_COLUMNS, cells.split("\t")))
        record["label"] = str(
            _true_label(
                record,
                rng.uniform(),
                best_prob_effect=best_prob_effect,
                pre_spread_effect=pre_spread_effect,
            )
        )
        if null_best_every and index % null_best_every == 0:
            record.update({**dict.fromkeys(fit_facepalm.BEST_MAT_COLUMNS, ""), "best_mate_ply": ""})
        lines.append("\t".join(record[col] for col in FEATURE_COLUMNS))
    # The last row is the unlabelled extra row (label cell empty, set "extra").
    extra = dict(zip(FEATURE_COLUMNS, _facts_cells(0, "", rng, noise, fill_rng).split("\t")))
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
    assert first.played_material == single_depth_material(-first.line_loss_3)
    assert first.best_3 is None and first.best_prob is None
    row = facts.rows[0]
    assert row.played_3 is None or row.line_loss_3 == -row.played_3
    # Phase 256 D-06: a facts row keeps all nine slots of both lines.
    assert row.played_material is not None and len(row.played_material) == LINE_MATERIAL_SLOTS
    assert row.best_material is not None and len(row.best_material) == LINE_MATERIAL_SLOTS
    assert any(r.best_3 is not None and r.best_prob is not None for r in facts.rows)


def test_check_constants_legacy_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The shipped model is the Phase 254 refit now; the legacy table reproduces the frozen
    # Phase 250 model it was fitted into.
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", PHASE_250_MODEL)
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
        material_input="decaying_mean",
        loss_gate=1.0,
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
        "FACEPALM_MATERIAL_INPUT",
        "FACEPALM_LOSS_GATE",
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


SET_EIGHT_ROWS: tuple[int, ...] = (241, 242, 243)


def test_unlabelled_set_eight_rows_are_extras_not_fit_rows(tmp_path: Path) -> None:
    """Blind set-8 rows (empty label) are excluded as unlabelled and listed under Extra rows."""
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    lines = features.read_text().splitlines()
    extra = dict(zip(FEATURE_COLUMNS, lines[-1].split("\t"), strict=True))
    for n in SET_EIGHT_ROWS:
        row = {**extra, "n": str(n), "set": "8", "label": ""}
        lines.append("\t".join(row[col] for col in FEATURE_COLUMNS))
    features.write_text("\n".join(lines) + "\n")

    table = fit_facepalm.load_features(features)
    _, excluded = fit_facepalm.split_usable(table.rows)
    out = tmp_path / "report.md"

    assert excluded[fit_facepalm.REASON_NO_LABEL] == 1 + len(SET_EIGHT_ROWS)
    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0
    extra_section = out.read_text().split("## Extra rows", 1)[1].split("## Constants", 1)[0]
    for n in SET_EIGHT_ROWS:
        assert f"- row {n}:" in extra_section


SPEC_SHAPES: tuple[fit_facepalm.CandidateSpec, ...] = (
    fit_facepalm.BASELINE_SPEC,
    fit_facepalm.CandidateSpec("combined", None, 9, "always"),
    fit_facepalm.CandidateSpec("split", 0, LOSS_CAP, "always", best_prob=True, pre_spread=True),
    fit_facepalm.CandidateSpec("combined", 0, LOSS_CAP, "loss_only", pre_spread=True),
    fit_facepalm.CandidateSpec("split", None, 9, "best_prob_for_misses"),
    fit_facepalm.CandidateSpec("combined", 0, 9, "best_prob_for_misses", pre_spread=True),
    # Phase 256: the aggregate inputs and both loss gates (parity per input and gate).
    fit_facepalm.CandidateSpec(
        "split", None, 9, "best_prob_for_misses", material_input="decaying_mean", loss_gate=1.0
    ),
    fit_facepalm.CandidateSpec("combined", 0, LOSS_CAP, "loss_only", material_input="first_stable"),
    fit_facepalm.CandidateSpec("split", 0, LOSS_CAP, "always", material_input="decaying_mean"),
    fit_facepalm.CandidateSpec(
        "split", 0, LOSS_CAP, "loss_only", material_input="first_stable", loss_gate=1.0
    ),
    fit_facepalm.CandidateSpec(
        "combined", None, LOSS_CAP, "best_prob_for_misses", material_input="decaying_mean"
    ),
)


@pytest.mark.parametrize("spec", SPEC_SHAPES, ids=fit_facepalm.spec_label)
def test_design_matrix_is_the_shipped_twin(
    spec: fit_facepalm.CandidateSpec, tmp_path: Path
) -> None:
    """sigmoid(x @ coef) equals facepalm_score of the candidate model on every usable row."""
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    base, _ = fit_facepalm.split_usable(fit_facepalm.load_features(features).rows)
    usable, _ = fit_facepalm.spec_usable(base, spec)
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
                played_material=row.played_material,
                mate_ply=row.line_mate_ply,
                best_material=row.best_material,
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
        self.outcome = fit_facepalm.run_facts_fit(self.usable, self.settings)


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

    def optional_float(text: str) -> float | None:
        return None if text == "None" else float(text)

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
        material_input=cast(MaterialInput, raw["FACEPALM_MATERIAL_INPUT"]),
        loss_gate=optional_float(raw["FACEPALM_LOSS_GATE"]),
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


def test_depth_3_fit_reproduces_the_2026_11_15_constants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refactored fit, forced to depth 3, still refits the Phase 254 constants (refactor pin)."""
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", PHASE_254_MODEL)
    argv = [
        "--features",
        str(FEATURES_2026_11_15),
        "--out",
        str(tmp_path / "r.md"),
        "--material-input",
        "depth_3",
        "--check-constants",
    ]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_OK


def test_shipped_constants_reproduce_from_the_refit_features(tmp_path: Path) -> None:
    """The shipped FACEPALM_* constants are the refit of the committed 2026-11-16 table (256 D-10).

    No monkeypatch: this runs against the real shipped FACEPALM_MODEL, so a hand-edited or stale
    constant exits EXIT_CONSTANTS_MISMATCH (T-256-19).
    """
    argv = [
        "--features",
        str(REFIT_FEATURES),
        "--out",
        str(tmp_path / "r.md"),
        *REFIT_FIT_FLAGS,
        "--check-constants",
    ]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_OK


def test_forced_decaying_mean_round_trips_through_check_constants(
    tmp_path: Path, facts_run: FactsRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    forced = ["--material-input", "decaying_mean"]
    base = ["--features", str(facts_run.features), "--out", str(tmp_path / "a.md"), *forced]
    assert fit_facepalm.main(base) == 0
    report = (tmp_path / "a.md").read_text()
    assert 'FACEPALM_MATERIAL_INPUT: MaterialInput = "decaying_mean"' in report
    assert "forced by --material-input decaying_mean" in report
    refit = _report_model(report)
    assert refit.material_input == "decaying_mean"
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", refit)

    forced_check = [*base[:3], str(tmp_path / "b.md"), *forced, "--check-constants"]
    assert fit_facepalm.main(forced_check) == fit_facepalm.EXIT_OK
    # Another forced input fits another model, so the decaying-mean model no longer reproduces.
    other = ["--features", str(facts_run.features), "--out", str(tmp_path / "c.md")]
    assert (
        fit_facepalm.main([*other, "--material-input", "depth_3", "--check-constants"])
        == fit_facepalm.EXIT_CONSTANTS_MISMATCH
    )


def test_material_input_flag_needs_a_facts_table(tmp_path: Path) -> None:
    argv = [
        "--features",
        str(LEGACY_FEATURES),
        "--out",
        str(tmp_path / "o.md"),
        "--material-input",
        "decaying_mean",
    ]

    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_FIT_ERROR


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
        FACTS_SPLIT_HEADING,
        "## Extra rows",
        "## Constants",
    ):
        assert heading in report, heading
    # Repeated-seed CV mean and spread sit next to the single-seed numbers, with each candidate's
    # own row count (candidates can fit different rows, Pitfall 1).
    assert "CV AUC mean" in report and "CV AUC spread" in report
    assert "| candidate | rows |" in report
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
        FACTS_SPLIT_HEADING, 1
    )[0]
    for set_id in range(1, FACTS_SETS + 1):
        assert re.search(rf"^\| {set_id} \|", set_section, flags=re.MULTILINE)
    # The constants block sets every FACEPALM_* model constant.
    constants = report.split("## Constants", 1)[1]
    for name in fit_facepalm.MODEL_CONSTANT_NAMES:
        assert re.search(rf"^{name}: ", constants, flags=re.MULTILINE), name


# ---------------------------------------------------------------------------
# Phase 256 plan 04 task 2: per-candidate rows (WR-03, D-05, D-12) and the stage-2 loss gate
# ---------------------------------------------------------------------------

# Nine-slot signed material lines (index = depth - 1): a pure miss (nothing lost, a pawn-and-more
# left on the table) and a line that loses a pawn only from depth 5 on.
LEVEL_LINE: tuple[int, ...] = (0,) * LINE_MATERIAL_SLOTS
GAIN_LINE: tuple[int, ...] = (0, 0, 3, 3, 3, 3, 3, 3, 3)
LATE_LOSS_LINE: tuple[int, ...] = (0, 0, 0, 0, -1, -1, -1, -1, -1)
DEFAULT_BEST_PROB: float = 0.3


def _line_row(
    played_line: tuple[int, ...],
    *,
    spread: float | None,
    best_prob: float | None = DEFAULT_BEST_PROB,
    best_line: tuple[int, ...] | None = GAIN_LINE,
    label: float | None = 1.0,
) -> fit_facepalm.FitRow:
    """A facts row built from full lines (the fit's own FitRow, no TSV)."""
    return fit_facepalm.FitRow(
        n="1",
        set_id="1",
        label=label,
        played_prob=0.1,
        reply_spread=spread,
        line_loss_3=-played_line[2],
        line_mate_ply=None,
        played_material=played_line,
        best_material=best_line,
        best_prob=best_prob,
    )


def _spec(
    spread_form: SpreadForm, material_input: MaterialInput = "depth_3", gate: float | None = None
) -> fit_facepalm.CandidateSpec:
    return fit_facepalm.CandidateSpec(
        "split", None, LOSS_CAP, spread_form, material_input=material_input, loss_gate=gate
    )


def test_spec_exclusion_keeps_null_spread_pure_miss_under_gated_form() -> None:
    """254 WR-03 / 256 D-12: a NULL reply spread only excludes a row the form would read it on."""
    row = _line_row(LEVEL_LINE, spread=None)

    # The base filter no longer reads the spread, so the row reaches every candidate.
    usable, excluded = fit_facepalm.split_usable([row])
    assert usable == [row]
    assert excluded[fit_facepalm.REASON_NO_LOSS] == 0
    # `always` reads the spread on every row; the gated forms never read it on a pure miss.
    assert fit_facepalm._spec_exclusion(row, _spec("always")) == fit_facepalm.REASON_NO_SPREAD
    assert fit_facepalm._spec_exclusion(row, _spec("loss_only")) is None
    assert fit_facepalm._spec_exclusion(row, _spec("best_prob_for_misses")) is None
    # Its design row is built without reading the spread (the read used to raise before the gate).
    values = fit_facepalm.spec_row_values(row, _spec("loss_only"))
    assert values[fit_facepalm.spec_columns(_spec("loss_only")).index("spread")] == 0.0
    # A row that loses material reads the spread under every form, so a NULL spread excludes it.
    losing = _line_row((0, 0, -2, -2, -2, -2, -2, -2, -2), spread=None)
    for form in ("always", "loss_only", "best_prob_for_misses"):
        assert fit_facepalm._spec_exclusion(losing, _spec(form)) == fit_facepalm.REASON_NO_SPREAD
    kept, counts = fit_facepalm.spec_usable([row, losing], _spec("loss_only"))
    assert kept == [row]
    assert counts[fit_facepalm.REASON_NO_SPREAD] == 1


def test_spec_exclusion_drops_pure_miss_without_best_prob() -> None:
    """256 D-05: the shipped twin leaves such a row unscored (D-04), so the fit does not fit it."""
    row = _line_row(LEVEL_LINE, spread=2.0, best_prob=None)

    assert (
        fit_facepalm._spec_exclusion(row, _spec("best_prob_for_misses"))
        == fit_facepalm.REASON_NO_BEST_PROB
    )
    # Additive or unused best probability reads NULL as 0, as the twin does (D-18).
    assert fit_facepalm._spec_exclusion(row, _spec("loss_only")) is None
    assert fit_facepalm._spec_exclusion(row, _spec("always")) is None
    additive = replace(_spec("loss_only"), best_prob=True)
    assert fit_facepalm._spec_exclusion(row, additive) is None
    # A losing row never needs the best probability.
    losing = _line_row((0, 0, -2, -2, -2, -2, -2, -2, -2), spread=2.0, best_prob=None)
    assert fit_facepalm._spec_exclusion(losing, _spec("best_prob_for_misses")) is None
    assert fit_facepalm.REASON_NO_BEST_PROB in fit_facepalm.EXCLUSION_REASONS


def test_spec_exclusion_uses_the_loss_gate_on_a_fractional_mean() -> None:
    """Under the decaying mean a late one-pawn loss is a fraction: losing at gate None, not at 1."""
    row = _line_row(LATE_LOSS_LINE, spread=None)
    mean_loss = fit_facepalm.material_loss(
        row.played_material, None, material_input="decaying_mean", loss_floor=0
    )
    assert mean_loss is not None and 0.0 < mean_loss < 1.0

    no_gate = _spec("loss_only", "decaying_mean", None)
    gate_one = _spec("loss_only", "decaying_mean", 1.0)
    assert fit_facepalm._spec_exclusion(row, no_gate) == fit_facepalm.REASON_NO_SPREAD
    assert fit_facepalm._spec_exclusion(row, gate_one) is None
    # Depth 3 sees no loss at all: the row is a pure miss under either gate.
    assert fit_facepalm._spec_exclusion(row, _spec("loss_only", "depth_3", None)) is None


def test_exclusion_counts_per_spread_form_in_data_section(tmp_path: Path) -> None:
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    lines = features.read_text().splitlines()
    header = lines[0].split("\t")
    spread_at = header.index("reply_spread")
    played_at = header.index("played_mat_3")
    label_at = header.index("label")
    blanked = 0
    for position, line in enumerate(lines[1:], start=1):
        cells = line.split("\t")
        # Blank the spread of a few labelled rows that lose nothing at depth 3 (pure misses).
        if cells[label_at] in ("0", "1") and cells[played_at] == "0" and blanked < 12:
            cells[spread_at] = ""
            lines[position] = "\t".join(cells)
            blanked += 1
    features.write_text("\n".join(lines) + "\n")
    out = tmp_path / "report.md"

    # The blanked rows are pure misses at depth 3, so the counts are read on that input.
    argv = ["--features", str(features), "--out", str(out), "--material-input", "depth_3"]
    assert fit_facepalm.main(argv) == 0

    data = out.read_text().split("## Data", 1)[1].split("## Stage 1", 1)[0]
    assert blanked == 12
    assert re.search(r"spread always.*excluded: NULL reply_spread 12,", data)
    for form in ("loss_only", "best_prob_for_misses"):
        for gate in ("none", "1"):
            assert re.search(
                rf"spread {form}, gate {gate}.*excluded: NULL reply_spread 0,", data
            ), (form, gate)
    assert "qualify only under a gated form" in data
    assert re.search(r"qualify only under a gated form[^:]*: 12\b", data)


def test_stage_two_lists_gate_candidates(facts_run: FactsRun) -> None:
    stage1 = fit_facepalm.select_material_form(facts_run.usable, facts_run.settings)

    stage2 = fit_facepalm.select_spread_form(facts_run.usable, stage1.chosen, facts_run.settings)

    assert fit_facepalm.LOSS_GATE_CANDIDATES == (None, 1.0)
    assert [(fit.spec.spread_form, fit.spec.loss_gate) for fit in stage2.candidates] == [
        ("always", None),
        ("loss_only", None),
        ("loss_only", 1.0),
        ("best_prob_for_misses", None),
        ("best_prob_for_misses", 1.0),
    ]
    only_one = fit_facepalm.select_spread_form(
        facts_run.usable, stage1.chosen, facts_run.settings, gate_mode="1"
    )
    assert [(fit.spec.spread_form, fit.spec.loss_gate) for fit in only_one.candidates] == [
        ("always", None),
        ("loss_only", 1.0),
        ("best_prob_for_misses", 1.0),
    ]
    assert "--loss-gate 1" in only_one.forced_by


def test_loss_gate_flag_forces_one_gate(tmp_path: Path, facts_run: FactsRun) -> None:
    for flag, shipped in (("none", "None"), ("1", "1.0")):
        out = tmp_path / f"gate-{flag}.md"
        argv = [
            "--features",
            str(facts_run.features),
            "--out",
            str(out),
            "--spread-form",
            "loss_only",
            "--loss-gate",
            flag,
        ]

        assert fit_facepalm.main(argv) == 0

        report = out.read_text()
        assert f"forced by --spread-form loss_only, --loss-gate {flag}" in report
        assert f"FACEPALM_LOSS_GATE: float | None = {shipped}" in report
    # The gate belongs to the facts schema.
    assert (
        fit_facepalm.main(
            [
                "--features",
                str(LEGACY_FEATURES),
                "--out",
                str(tmp_path / "x.md"),
                "--loss-gate",
                "1",
            ]
        )
        == fit_facepalm.EXIT_FIT_ERROR
    )


def test_d13_tables_align_with_the_chosen_rows_after_exclusion(tmp_path: Path) -> None:
    """Candidates fit different rows once a NULL spread is no longer a base exclusion (Pitfall 1)."""
    features = tmp_path / "facts.tsv"
    write_synthetic_facts(features)
    lines = features.read_text().splitlines()
    header = lines[0].split("\t")
    spread_at, played_at = header.index("reply_spread"), header.index("played_mat_3")
    for position in range(1, 40):
        cells = lines[position].split("\t")
        if cells[played_at] == "0":
            cells[spread_at] = ""
            lines[position] = "\t".join(cells)
    features.write_text("\n".join(lines) + "\n")
    rows = fit_facepalm.load_features(features).rows
    settings = fit_facepalm.FitSettings(0.7, fit_facepalm.CV_FOLDS, fit_facepalm.FIT_SEED)

    outcome = fit_facepalm.run_facts_fit(rows, settings, spread_mode="loss_only")

    always = outcome.stage1.chosen
    assert len(outcome.chosen.rows) == len(outcome.chosen.oof) > len(always.rows)
    assert len(always.rows) == len(always.oof)
    report = fit_facepalm.render_facts_report(
        outcome, features_name="f.tsv", threshold=0.7, folds=fit_facepalm.CV_FOLDS, seed=1
    )
    assert "| candidate | rows |" in report


# ---------------------------------------------------------------------------
# Phase 256 plan 05 task 1: the three-input comparison (D-06, D-07, D-09, D-14)
# ---------------------------------------------------------------------------


def test_choose_material_input_rules() -> None:
    tol = fit_facepalm.AUC_TIE_TOLERANCE
    share_tol = fit_facepalm.FAIR_SHARE_TIE_TOLERANCE
    inputs = fit_facepalm.MATERIAL_INPUTS
    assert inputs == ("decaying_mean", "first_stable", "depth_3")
    first = fit_facepalm.CandidateScore(6, 0.80, 0.70)

    # A higher CV AUC mean by more than the tolerance wins whatever the shares are and wherever
    # the input sits in the preference order.
    ahead = fit_facepalm.CandidateScore(4, 0.80 + 2 * tol, 0.10)
    index, reason = fit_facepalm.choose_material_input([first, first, ahead])
    assert index == 2 and "cross-validated AUC" in reason
    # Within the tolerance the fair share decides, but only beyond its own tolerance.
    better_share = fit_facepalm.CandidateScore(6, 0.80 + tol / 2, 0.70 + 2 * share_tol)
    index, reason = fit_facepalm.choose_material_input([first, better_share, first])
    assert index == 1 and "fair share" in reason
    # A fair share inside its tolerance is noise: the preference order decides (D-09).
    noise_share = fit_facepalm.CandidateScore(6, 0.80 + tol / 2, 0.70 + share_tol / 2)
    index, reason = fit_facepalm.choose_material_input([first, noise_share, noise_share])
    assert index == 0 and "D-09" in reason
    # Decaying mean against depth 3 on a full tie: the decaying mean (list order), even when depth 3
    # has fewer free coefficients (D-09 overrides "fewer coefficients" at this level).
    simpler = fit_facepalm.CandidateScore(4, 0.80, 0.70)
    assert fit_facepalm.choose_material_input([first, simpler])[0] == 0
    # First stable against depth 3: first stable.
    assert fit_facepalm.choose_material_input([simpler, first, simpler])[0] == 0
    assert fit_facepalm.choose_material_input([first, first])[0] == 0
    # No passers is the worst share.
    no_passers = fit_facepalm.CandidateScore(6, 0.80, None)
    assert fit_facepalm.choose_material_input([no_passers, first])[0] == 1


def _comparison_section(report: str) -> str:
    return report.split("## Material input", 1)[1].split("## Stage 1", 1)[0]


def test_material_input_auto_compares_three_inputs(tmp_path: Path, facts_run: FactsRun) -> None:
    section = _comparison_section(facts_run.report)

    names = re.findall(r"^\| (\w+) \| [^|]+ \| \d+ \|", section, flags=re.MULTILINE)
    assert tuple(names) == fit_facepalm.MATERIAL_INPUTS
    chosen = re.search(r"^Chosen input: (\w+)\. Reason: (.+)\.$", section, flags=re.MULTILINE)
    assert chosen is not None
    assert chosen.group(1) in fit_facepalm.MATERIAL_INPUTS
    # The rows column carries every input's row count (Pitfall 1) and nothing is forced.
    assert "forced by" not in section
    # The inputs that were not chosen keep their stage tables (D-14).
    others = [name for name in fit_facepalm.MATERIAL_INPUTS if name != chosen.group(1)]
    assert re.findall(r"^## Other input: (\w+)$", facts_run.report, flags=re.MULTILINE) == others

    # A forced input runs one pipeline: one comparison row, the flag named, no other-input block.
    out = tmp_path / "forced-input.md"
    argv = ["--features", str(facts_run.features), "--out", str(out)]
    assert fit_facepalm.main([*argv, "--material-input", "first_stable"]) == 0
    forced = out.read_text()
    forced_section = _comparison_section(forced)
    assert re.findall(r"^\| (\w+) \| [^|]+ \| \d+ \|", forced_section, flags=re.MULTILINE) == [
        "first_stable"
    ]
    assert "Chosen input: first_stable." in forced_section
    assert "--material-input first_stable" in forced_section
    assert "## Other input" not in forced


# ---------------------------------------------------------------------------
# Phase 256 plan 05 task 2: the chosen-model section (D-10, D-13)
# ---------------------------------------------------------------------------


def _chosen_model_section(report: str) -> str:
    return report.split("## Chosen model", 1)[1].split(
        "## Fair / unfair among passers by material type", 1
    )[0]


def test_constants_block_is_the_chosen_input_final(facts_run: FactsRun) -> None:
    """D-10 / T-256-24: the pasted constants are the chosen input's final, not another input's."""
    outcome = fit_facepalm.run_facts_fit(facts_run.usable, facts_run.settings)
    report = facts_run.report

    chosen_line = re.search(r"^Chosen input: (\w+)\.", report, flags=re.MULTILINE)
    assert chosen_line is not None
    block_input = re.search(
        r'^FACEPALM_MATERIAL_INPUT: MaterialInput = "(\w+)"$', report, flags=re.MULTILINE
    )
    assert block_input is not None
    assert block_input.group(1) == chosen_line.group(1) == outcome.chosen.spec.material_input
    # The block parsed back is the outcome's model, and that model is the chosen input's final.
    assert _report_model(report) == outcome.model
    finals = {entry.material_input: entry.chosen for entry in outcome.inputs}
    assert outcome.model == finals[outcome.chosen.spec.material_input].model
    # Every input was fitted on all the labelled sets: the final carries their rows (D-10).
    assert {row.set_id for row in outcome.chosen.rows} == {str(n) for n in range(1, FACTS_SETS + 1)}


def test_report_states_the_assumptions(facts_run: FactsRun) -> None:
    """D-13: the owner reads the assumptions the inputs rest on next to the chosen model."""
    section = _chosen_model_section(facts_run.report)

    assert "Assumptions" in section
    found = {
        tag: re.findall(rf"^- {tag}[ :].*$", section, flags=re.MULTILINE)
        for tag in ("A1", "A2", "A4")
    }
    assert all(len(matches) == 1 for matches in found.values()), found
    a1, a2, a4 = (found[tag][0] for tag in ("A1", "A2", "A4"))
    # The numbers come from the shipped constants, not from literals in the text.
    assert "first stable" in a1 and str(MATERIAL_DECAY_RATIO) in a1
    assert str(LINE_DEPTH) in a2 and str(MATE_LOSS) in a2
    assert "at least" in a4
    # The per-depth loss floor and the chosen missed floor and cap.
    chosen = fit_facepalm.run_facts_fit(facts_run.usable, facts_run.settings).chosen.spec
    floor = fit_facepalm._floor_text(chosen.missed_floor)
    assert re.search(
        rf"^- loss floor {fit_facepalm.FACTS_LOSS_FLOOR} per depth", section, flags=re.MULTILINE
    )
    assert f"missed floor {floor}, cap {chosen.missed_cap}, applied per depth" in section


# ---------------------------------------------------------------------------
# Phase 256 plan 06 task 1: the set-8 holdout per input (D-08)
# ---------------------------------------------------------------------------


def test_set_eight_holdout_runs_the_pipeline_on_sets_one_to_seven(
    facts_run: FactsRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-256-13: set 8 is only scored. Flipping its labels leaves the sets-1-7 pipeline unchanged."""
    modes = fit_facepalm.PipelineModes()
    seen: list[fit_facepalm.InputOutcome] = []
    real = fit_facepalm.run_input_pipeline

    def spy(*args: Any, **kwargs: Any) -> fit_facepalm.InputOutcome:
        outcome = real(*args, **kwargs)
        seen.append(outcome)
        return outcome

    monkeypatch.setattr(fit_facepalm, "run_input_pipeline", spy)
    flipped = [
        replace(row, label=1.0 - row.label)
        if row.set_id == fit_facepalm.TEST_SET and row.label is not None
        else row
        for row in facts_run.usable
    ]
    assert any(row.set_id == fit_facepalm.TEST_SET for row in flipped)

    original = fit_facepalm.input_holdout(
        facts_run.usable, facts_run.settings, "decaying_mean", modes
    )
    mirrored = fit_facepalm.input_holdout(flipped, facts_run.settings, "decaying_mean", modes)

    # The pipeline ran once per call, on rows of sets 1-7 only, and chose the same spec and
    # coefficients whatever set 8 says.
    assert len(seen) == 2
    for outcome in seen:
        assert {row.set_id for row in outcome.chosen.rows} <= set(fit_facepalm.TRAIN_SETS)
        assert fit_facepalm.TEST_SET not in {row.set_id for row in outcome.chosen.rows}
    first, second = seen
    assert first.chosen.spec == second.chosen.spec
    assert np.array_equal(first.chosen.coef, second.chosen.coef)
    # Same model, mirrored labels: the AUC mirrors and fair / unfair trade places at every cut.
    assert original.test_auc is not None and mirrored.test_auc is not None
    assert original.test_auc + mirrored.test_auc == pytest.approx(1.0)
    assert original.train_rows == mirrored.train_rows and original.test_rows == mirrored.test_rows
    assert [(e.fair, e.unfair) for e in original.table] == [
        (e.unfair, e.fair) for e in mirrored.table
    ]


def test_every_input_carries_its_own_set_eight_holdout(facts_run: FactsRun) -> None:
    outcome = facts_run.outcome
    report = facts_run.report

    assert [entry.material_input for entry in outcome.inputs] == list(fit_facepalm.MATERIAL_INPUTS)
    for entry in outcome.inputs:
        assert entry.holdout.note == "" and entry.holdout.test_auc is not None
        # The pipeline is refitted without set 8: it sees fewer rows than the all-sets final.
        assert entry.holdout.train_rows < len(entry.chosen.rows)
    assert outcome.split is next(
        entry.holdout for entry in outcome.inputs if entry.chosen is outcome.chosen
    )
    # The chosen input's holdout has its derived level-2 heading, the others sit under their own block.
    assert re.findall(rf"^{FACTS_SPLIT_HEADING}$", report, flags=re.MULTILINE) == [
        FACTS_SPLIT_HEADING
    ]
    other_heading = f"### Sets {fit_facepalm.TRAIN_SETS_TEXT} vs set {fit_facepalm.TEST_SET}"
    assert report.count(other_heading) == len(outcome.inputs) - 1
    section = report.split("## Material input", 1)[1].split("## Stage 1", 1)[0]
    for column in ("set-8 rows", "set-8 AUC", "set-8 fair / unfair at the cut"):
        assert column in section
    assert "about 55 decided rows" in section
    # One table row per input with the set-8 cells filled (rows, AUC, fair / unfair).
    for name in fit_facepalm.MATERIAL_INPUTS:
        pattern = rf"^\| {name} \| .* \| \d+ \| 0\.\d{{3}} \| \d+ / \d+ \|"
        assert re.search(pattern, section, flags=re.MULTILINE), name


def test_a_table_without_set_eight_says_the_holdout_is_empty(
    tmp_path: Path, facts_run: FactsRun
) -> None:
    no_set_eight = [
        line
        for line in facts_run.features.read_text().splitlines()
        if line.split("\t")[1] != fit_facepalm.TEST_SET
    ]
    features = tmp_path / "no8.tsv"
    features.write_text("\n".join(no_set_eight) + "\n")
    out = tmp_path / "no8.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    report = out.read_text()
    section = report.split(FACTS_SPLIT_HEADING, 1)[1].split("## Fair", 1)[0].split("## Other", 1)[0]
    assert fit_facepalm.HOLDOUT_EMPTY_NOTE in section
    # Without a set-8 AUC nothing can disagree.
    assert "Disagreement" not in report


def test_holdout_disagreement_is_flagged(facts_run: FactsRun) -> None:
    outcome = facts_run.outcome
    chosen = outcome.chosen.spec.material_input
    other = next(e.material_input for e in outcome.inputs if e.material_input != chosen)
    tol = fit_facepalm.AUC_TIE_TOLERANCE
    base = 0.70

    def with_aucs(aucs: dict[str, float | None]) -> list[fit_facepalm.InputOutcome]:
        return [
            replace(
                entry,
                holdout=fit_facepalm.SplitResult(
                    50, 55, aucs.get(entry.material_input, base), [], ""
                ),
            )
            for entry in outcome.inputs
        ]

    # Another input beats the chosen one by more than the tolerance: flagged, both named.
    ahead = with_aucs({other: base + 2 * tol})
    flag = fit_facepalm.holdout_disagreement(ahead, chosen)
    assert flag is not None and chosen in flag and other in flag and "D-13" in flag
    # Within the tolerance, the chosen input best, or no chosen-input AUC: not flagged.
    assert fit_facepalm.holdout_disagreement(with_aucs({other: base + tol / 2}), chosen) is None
    assert fit_facepalm.holdout_disagreement(with_aucs({chosen: base + 2 * tol}), chosen) is None
    assert fit_facepalm.holdout_disagreement(with_aucs({chosen: None}), chosen) is None
    # An input without a set-8 AUC never wins the comparison.
    assert fit_facepalm.holdout_disagreement(with_aucs({other: None}), chosen) is None

    # The report shows the line only when the outcome carries it.
    flagged = replace(outcome, inputs=ahead, holdout_disagreement=flag)
    flagged_report = fit_facepalm.render_facts_report(
        flagged, features_name="f.tsv", threshold=0.7, folds=fit_facepalm.CV_FOLDS, seed=1
    )
    assert "Disagreement:" in flagged_report
    calm = replace(outcome, inputs=with_aucs({}), holdout_disagreement=None)
    calm_report = fit_facepalm.render_facts_report(
        calm, features_name="f.tsv", threshold=0.7, folds=fit_facepalm.CV_FOLDS, seed=1
    )
    assert "Disagreement:" not in calm_report


# ---------------------------------------------------------------------------
# Phase 256 plan 06 task 2: the owner section for the D-13 checkpoint
# ---------------------------------------------------------------------------

LABEL_FILE_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "elo",
    "blitz_elo",
    "move",
    "link",
    "engine_drop",
    "expected_loss",
    "reply_loss",
    "practical_loss",
    "played_prob",
    "reply_spread",
    "line_loss3",
    "mate3",
    "label",
    "comment",
)
# Fields before the label cell in a labels row (n .. mate3), the rest of the line is label, comment.
LABEL_FILE_BEFORE_LABEL: int = 14
OWNER_HEADING: str = "## Owner checks"


def _label_line(n: str, set_id: str, link: str, label: str, comment: str | None) -> str:
    """One labels-file row; a row without a comment has no comment cell at all (15 fields)."""
    cells = [n, set_id, "1500", "1600", "Nf3", link, *[""] * (LABEL_FILE_BEFORE_LABEL - 6), label]
    if comment is not None:
        cells.append(comment)
    return "\t".join(cells)


def _facts_of(row: fit_facepalm.FitRow) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=row.played_prob,
        reply_spread=row.reply_spread,
        played_material=row.played_material,
        mate_ply=row.line_mate_ply,
        best_material=row.best_material,
        best_mate_ply=row.best_mate_ply,
        best_prob=row.best_prob,
        pre_spread=row.pre_spread,
    )


def _owner_text(report: str) -> str:
    """The owner section (up to the next level-2 heading)."""
    assert OWNER_HEADING in report, "the report has no owner section (D-13)"
    return report.split(OWNER_HEADING, 1)[1].split("\n## ", 1)[0]


def _main_code(argv: list[str]) -> int:
    """`fit_facepalm.main`'s exit code; an argparse rejection is its SystemExit code."""
    try:
        return fit_facepalm.main(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1


def test_owner_section_lists_commented_rows(tmp_path: Path, facts_run: FactsRun) -> None:
    """D-13: commented label rows verbatim with their old and new score; the rest is skipped."""
    scored = [row for row in facts_run.usable if row.n.isdigit()][:2]
    blank_played = "7"
    lines = facts_run.features.read_text().splitlines()
    header = lines[0].split("\t")
    played_at, n_at = header.index("played_prob"), header.index("n")
    for position, line in enumerate(lines[1:], start=1):
        cells = line.split("\t")
        if cells[n_at] == blank_played:
            cells[played_at] = ""
            lines[position] = "\t".join(cells)
    features = tmp_path / "facts.tsv"
    features.write_text("\n".join(lines) + "\n")
    comment_a = "currently 6%, should be at least 90%"
    comment_b = "currently 88%, should be below 60% | with a pipe"
    labels = tmp_path / "labels.tsv"
    labels.write_text(
        "\n".join(
            [
                "\t".join(LABEL_FILE_COLUMNS),
                _label_line(scored[0].n, "7", "https://example.test/a", "1", comment_a),
                _label_line(scored[1].n, "8", "https://example.test/b", "0", comment_b),
                # No comment cell at all (a set-8 style row, 15 fields) and an empty comment cell.
                _label_line("3", "8", "https://example.test/c", "1", None),
                _label_line("4", "8", "https://example.test/d", "0", ""),
                # A NULL input leaves the row unscored, an n missing from the features is unknown.
                _label_line(blank_played, "7", "https://example.test/e", "1", "no played prob"),
                _label_line("99999", "8", "https://example.test/f", "0", "not in the table"),
            ]
        )
        + "\n"
    )
    out = tmp_path / "report.md"

    assert (
        _main_code(["--features", str(features), "--out", str(out), "--labels", str(labels)]) == 0
    )

    report = out.read_text()
    section = _owner_text(report)
    model = _report_model(report)
    for row, comment in ((scored[0], comment_a), (scored[1], comment_b)):
        facts = _facts_of(row)
        old = fit_facepalm._fmt(
            facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA, model=fit_facepalm.FACEPALM_MODEL)
        )
        new = fit_facepalm._fmt(facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA, model=model))
        label = f"{row.label:g}"
        link = "https://example.test/a" if row is scored[0] else "https://example.test/b"
        set_id = "7" if row is scored[0] else "8"
        cell = comment.replace("|", "\\|")
        expected = f"| {row.n} | {set_id} | {label} | {link} | {cell} | {old} | {new} |"
        assert expected in section, expected
    assert "| 7 | 7 | 1 | https://example.test/e | no played prob | n/a | n/a |" in section
    assert (
        "| 99999 | 8 | n/a | https://example.test/f | not in the table "
        "| not in features | not in features |" in section
    )
    # Rows without a comment are not listed.
    assert "example.test/c" not in section and "example.test/d" not in section


def test_owner_section_without_labels_says_so(facts_run: FactsRun) -> None:
    section = _owner_text(facts_run.report)

    assert "--labels" in section
    # The sections that do not need the label file are there all the same.
    assert "Pure-miss pass rate" in section


def test_labels_file_without_comment_column_is_an_error(
    tmp_path: Path, facts_run: FactsRun, capsys: pytest.CaptureFixture[str]
) -> None:
    for dropped in ("comment", "n"):
        columns = [name for name in LABEL_FILE_COLUMNS if name != dropped]
        labels = tmp_path / f"no-{dropped}.tsv"
        labels.write_text("\t".join(columns) + "\n")
        out = tmp_path / f"no-{dropped}.md"

        code = _main_code(
            ["--features", str(facts_run.features), "--out", str(out), "--labels", str(labels)]
        )

        assert code == fit_facepalm.EXIT_FIT_ERROR
        assert not out.exists()
        assert f"'{dropped}'" in capsys.readouterr().err


def test_owner_section_pure_miss_pass_rates(facts_run: FactsRun) -> None:
    section = _owner_text(facts_run.report).split("### Pure-miss pass rate", 1)[1]
    chosen = facts_run.outcome.chosen
    misses = [
        position
        for position, row in enumerate(chosen.rows)
        if fit_facepalm._row_material_type(row) == "misses"
    ]
    assert misses, "the synthetic table must hold pure-miss rows"

    for cut in fit_facepalm.thresholds_for(0.7):
        passers = sum(1 for position in misses if chosen.oof[position] >= cut)
        share = fit_facepalm._fmt(passers / len(misses))
        assert f"| {cut:.2f} | {passers} | {len(misses)} | {share} |" in section, cut


def test_owner_section_scores_extra_rows_old_and_new(facts_run: FactsRun) -> None:
    section = _owner_text(facts_run.report).split("### Added rows", 1)[1].split("### ", 1)[0]
    # `facts_run.outcome` is fitted on the usable rows only, so read the unlabelled row from the table.
    extra = next(
        row for row in fit_facepalm.load_features(facts_run.features).rows if row.n == "extra"
    )
    facts = _facts_of(extra)
    old = facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA, model=fit_facepalm.FACEPALM_MODEL)
    new = facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA, model=_report_model(facts_run.report))
    assert old is not None and new is not None
    cuts = fit_facepalm.thresholds_for(0.7)
    below = " | ".join("yes" if new < cut else "no" for cut in cuts)

    assert f"| extra | {fit_facepalm._fmt(old)} | {fit_facepalm._fmt(new)} | {below} |" in section
    for cut in cuts:
        assert f"below {cut:.2f}" in section
