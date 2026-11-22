"""Tests for the facepalm score fit (Phase 259 plan 07: fixed shape, six coefficients).

Trimmed to what ships (owner scope addition): one synthetic scalar table builder, no staged
selection, no forced-shape flags, no legacy or facts schemas.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from app.services.blunder_check_rules import FACEPALM_LAMBDA_MAX, PLAYED_PROB_OFFSET
from app.services.facepalm_score import FACEPALM_MODEL, FacepalmFacts, facepalm_score
from scripts.blunder_check import fit_facepalm
from scripts.blunder_check.fit_facepalm import ScalarCoefs, ScalarFitRow

REPO_ROOT = Path(__file__).resolve().parents[2]
# The Phase 259 plan 11 prod pull (D-15), the table the shipped constants were confirmed on. It is
# byte-identical to the plan 03 pull of 2026-11-21.
COMMITTED_FEATURES = REPO_ROOT / "reports/blunder-check/facepalm-features-2026-11-22.tsv"
COMMITTED_LABELS = REPO_ROOT / "reports/blunder-check/facepalm-labels.tsv"
# The pre-259 table (old-rule arrays, no loss / missed / reply_prob columns).
PRE_259_FEATURES = REPO_ROOT / "reports/blunder-check/facepalm-features-2026-11-16.tsv"

SYNTHETIC_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "game_id",
    "ply",
    "label",
    "played_prob",
    "reply_spread",
    "best_prob",
    "reply_prob",
    "loss",
    "missed",
    "loss_shipped",
    "missed_shipped",
)
SYNTHETIC_ROWS: int = 6000
SYNTHETIC_SEED: int = 9
SYNTHETIC_SETS: int = 8
LOSING_SHARE: float = 0.5
# Known generating coefficients, in fit_facepalm.CONSTANT_NAMES order.
TRUE_COEFS: tuple[float, ...] = (-1.0, -0.6, 0.9, 0.5, 2.0, 0.9)
# 6000 rows of the seeded draw recover each coefficient within this (the largest miss is about 0.07).
RECOVERY_TOLERANCE: float = 0.15
# SQL-free parity of the fit's score and the app twin (both are plain float arithmetic).
PARITY_TOLERANCE: float = 1e-9
SPREAD_RANGE: tuple[float, float] = (1.0, 10.0)
# A table whose labels depend strongly on the reply spread, so the spread alternative scores highest.
STRONG_SPREAD_COEF: float = -0.5


def _log(prob: np.ndarray) -> np.ndarray:
    return np.log(prob + PLAYED_PROB_OFFSET)


def synthetic_rows(
    rows: int = SYNTHETIC_ROWS, spread_coef: float = 0.0, seed: int = SYNTHETIC_SEED
) -> list[dict[str, str]]:
    """Rows of the scalar features table drawn from TRUE_COEFS (plus `spread_coef` on losing rows)."""
    rng = np.random.default_rng(seed)
    played = rng.uniform(0.02, 0.6, rows)
    spread = rng.uniform(*SPREAD_RANGE, rows)
    best = rng.uniform(0.05, 0.9, rows)
    reply = rng.uniform(0.05, 0.9, rows)
    losing = rng.uniform(0.0, 1.0, rows) < LOSING_SHARE
    loss = np.where(losing, rng.uniform(0.2, 4.0, rows), 0.0)
    missed = rng.uniform(0.0, 3.0, rows)
    intercept, played_c, loss_c, missed_c, best_c, reply_c = TRUE_COEFS
    z = (
        intercept
        + played_c * _log(played)
        + loss_c * loss
        + missed_c * missed
        + np.where(losing, reply_c * _log(reply) + spread_coef * spread, best_c * _log(best))
    )
    draws = rng.uniform(0.0, 1.0, rows)
    labels = (draws < 1.0 / (1.0 + np.exp(-z))).astype(int)
    return [
        {
            "n": str(i + 1),
            "set": str(i % SYNTHETIC_SETS + 1),
            "game_id": str(1000 + i),
            "ply": str(20 + i % 30),
            "label": str(labels[i]),
            "played_prob": f"{played[i]:.6f}",
            "reply_spread": f"{spread[i]:.6f}",
            "best_prob": f"{best[i]:.6f}",
            "reply_prob": f"{reply[i]:.6f}",
            "loss": f"{loss[i]:.6f}",
            "missed": f"{missed[i]:.6f}",
            "loss_shipped": f"{loss[i]:.6f}",
            "missed_shipped": f"{missed[i]:.6f}",
        }
        for i in range(rows)
    ]


def write_table(
    path: Path, rows: list[dict[str, str]], columns: tuple[str, ...] = SYNTHETIC_COLUMNS
) -> Path:
    lines = ["\t".join(columns), *("\t".join(row[col] for col in columns) for row in rows)]
    path.write_text("\n".join(lines) + "\n")
    return path


def constants_of(report: str) -> dict[str, float]:
    section = report.split("## Constants", 1)[1]
    values: dict[str, float] = {}
    for name in fit_facepalm.CONSTANT_NAMES:
        match = re.search(rf"^{name}: float = (\S+)$", section, flags=re.MULTILINE)
        assert match is not None, name
        values[name] = float(match.group(1))
    return values


@dataclass(frozen=True)
class ScalarRun:
    """One plain run of the script on the module's synthetic table."""

    features: Path
    report: str
    out: Path


@pytest.fixture(scope="module")
def scalar_run(tmp_path_factory: pytest.TempPathFactory) -> ScalarRun:
    directory = tmp_path_factory.mktemp("scalar-fit")
    features = write_table(directory / "features.tsv", synthetic_rows())
    out = directory / "report.md"
    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0
    return ScalarRun(features=features, report=out.read_text(), out=out)


def _row(**overrides: object) -> ScalarFitRow:
    base: dict[str, object] = {
        "n": "1",
        "set_id": "1",
        "label": 1.0,
        "played_prob": 0.1,
        "reply_spread": 3.0,
        "best_prob": 0.4,
        "reply_prob": 0.2,
        "loss": 0.0,
        "missed": 0.0,
    }
    return ScalarFitRow(**{**base, **overrides})  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Tracer and fit behaviour
# ---------------------------------------------------------------------------


def test_fit_runs_on_the_committed_259_features(tmp_path: Path) -> None:
    """Tracer: the fixed-shape fit runs end to end on the committed plan 03 table."""
    out = tmp_path / "report.md"

    code = fit_facepalm.main(
        [
            "--features",
            str(COMMITTED_FEATURES),
            "--labels",
            str(COMMITTED_LABELS),
            "--out",
            str(out),
        ]
    )

    assert code == fit_facepalm.EXIT_OK
    report = out.read_text()
    assert len(constants_of(report)) == len(fit_facepalm.CONSTANT_NAMES)
    assert "## Alternatives (information only)" in report
    assert "within range" in report or "outside range" in report
    assert "## Fair / unfair among passers at the D-15 cuts" in report


def test_synthetic_recovery_and_constants_block(scalar_run: ScalarRun) -> None:
    constants = constants_of(scalar_run.report)

    for name, truth in zip(fit_facepalm.CONSTANT_NAMES, TRUE_COEFS, strict=True):
        assert abs(constants[name] - truth) < RECOVERY_TOLERANCE, name


def test_same_seed_gives_byte_identical_reports(tmp_path: Path) -> None:
    features = write_table(tmp_path / "features.tsv", synthetic_rows(rows=400))
    first, second = tmp_path / "a.md", tmp_path / "b.md"

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


def test_separable_labels_exit_2_and_write_no_report(tmp_path: Path) -> None:
    rows = synthetic_rows(rows=60)
    for i, row in enumerate(rows):
        # The best-move probability alone separates the labels perfectly on non-losing rows.
        row.update(label=str(i % 2), loss="0.0", loss_shipped="0.0")
        row["best_prob"] = "0.8" if i % 2 else "0.1"
    features = write_table(tmp_path / "features.tsv", rows)
    out = tmp_path / "report.md"

    code = fit_facepalm.main(["--features", str(features), "--out", str(out)])

    assert code == fit_facepalm.EXIT_FIT_ERROR
    assert not out.exists()


# ---------------------------------------------------------------------------
# Design row, exclusions, scoring
# ---------------------------------------------------------------------------


def test_design_row_gates_reply_and_best_terms_by_loss() -> None:
    off = PLAYED_PROB_OFFSET
    losing = fit_facepalm.design_row(_row(loss=1.5, missed=0.5), "chosen")
    quiet = fit_facepalm.design_row(_row(loss=0.0, missed=0.5), "chosen")

    # [intercept, ln(played), loss, missed, best term, reply term]
    assert losing == pytest.approx([1.0, math.log(0.1 + off), 1.5, 0.5, 0.0, math.log(0.2 + off)])
    assert quiet == pytest.approx([1.0, math.log(0.1 + off), 0.0, 0.5, math.log(0.4 + off), 0.0])
    spread = fit_facepalm.design_row(_row(loss=1.5), "quiet_spread")
    assert spread[-1] == 3.0 and spread[4] == 0.0
    # The shipped baseline reads the old-rule pair, not the quiet one.
    shipped = _row(loss=0.0, loss_shipped=2.0, missed_shipped=1.0)
    assert fit_facepalm.design_row(shipped, "shipped_baseline")[2:4] == [2.0, 1.0]


def test_fit_scoring_equals_the_app_twin() -> None:
    """scalar_score is the app twin's facepalm_score (lam 1.0, the shipped model) on every row of the plan 03 table."""
    coefs = ScalarCoefs(
        intercept=FACEPALM_MODEL.intercept,
        played_coef=FACEPALM_MODEL.played_coef,
        loss_coef=FACEPALM_MODEL.loss_coef,
        missed_coef=FACEPALM_MODEL.missed_coef,
        best_prob_coef=FACEPALM_MODEL.best_prob_coef,
        reply_prob_coef=FACEPALM_MODEL.reply_prob_coef,
    )
    table = fit_facepalm.load_features(COMMITTED_FEATURES)
    scored = 0
    for row in table.rows:
        twin = facepalm_score(
            FacepalmFacts(
                played_prob=row.played_prob,
                loss=row.loss,
                missed=row.missed,
                best_prob=row.best_prob,
                reply_prob=row.reply_prob,
            ),
            lam=FACEPALM_LAMBDA_MAX,
            model=FACEPALM_MODEL,
        )
        fitted = fit_facepalm.scalar_score(row, coefs)
        if twin is None:
            assert fitted is None, (row.game_id, row.ply)
            continue
        assert fitted == pytest.approx(twin, abs=PARITY_TOLERANCE), (row.game_id, row.ply)
        scored += 1
    assert scored > 0


def test_scalar_score_is_the_logistic_of_the_chosen_shape() -> None:
    coefs = ScalarCoefs(-1.0, -0.5, 0.8, 0.4, 2.0, 0.9)
    row = _row(loss=2.0, missed=0.5)
    z = -1.0 - 0.5 * math.log(0.1 + PLAYED_PROB_OFFSET) + 0.8 * 2.0 + 0.4 * 0.5
    z += 0.9 * math.log(0.2 + PLAYED_PROB_OFFSET)

    assert fit_facepalm.scalar_score(row, coefs) == pytest.approx(1.0 / (1.0 + math.exp(-z)))
    # An input the row needs is NULL: unscored, never a made-up number.
    assert fit_facepalm.scalar_score(_row(loss=2.0, reply_prob=None), coefs) is None
    assert fit_facepalm.scalar_score(_row(loss=None), coefs) is None


def test_exclusions_are_counted_per_reason() -> None:
    rows = [
        _row(label=0.5),
        _row(label=None),
        _row(label=1.0),
        _row(played_prob=None),
        _row(loss=None),
        _row(loss=1.0, reply_prob=None),  # a losing row needs the reply probability
        _row(loss=1.0, best_prob=None),  # a losing row does not read the best-move probability
        _row(loss=0.0, best_prob=None),  # a non-losing row needs the best-move probability
    ]

    usable, excluded = fit_facepalm.split_usable(rows)

    assert len(usable) == 2
    assert excluded == {
        fit_facepalm.REASON_UNDECIDED: 1,
        fit_facepalm.REASON_NO_LABEL: 1,
        fit_facepalm.REASON_NO_PLAYED: 1,
        fit_facepalm.REASON_NO_LOSS: 1,
        fit_facepalm.REASON_NO_REPLY_PROB: 1,
        fit_facepalm.REASON_NO_BEST_PROB: 1,
    }


def test_load_features_rejects_foreign_and_pre_259_tables(tmp_path: Path) -> None:
    other = tmp_path / "other.tsv"
    other.write_text("a\tb\n1\t2\n")

    with pytest.raises(fit_facepalm.FitError):
        fit_facepalm.load_features(other)
    # An older table without the quiet-rule scalars cannot feed the scalar shape.
    with pytest.raises(fit_facepalm.FitError):
        fit_facepalm.load_features(PRE_259_FEATURES)


def test_help_lists_the_documented_flags() -> None:
    for script, flags in (
        (
            "scripts/blunder_check/fit_facepalm.py",
            ("--features", "--labels", "--threshold", "--check-constants"),
        ),
        ("scripts/blunder_check/facepalm_features.py", ("--pv-cache", "--extra", "--skip-missing")),
    ):
        done = subprocess.run(
            [sys.executable, "-I", str(REPO_ROOT / script), "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        for flag in flags:
            assert flag in done.stdout
    # The staged-selection flags are gone.
    done = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/blunder_check/fit_facepalm.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    for flag in ("--loss-floor", "--material-form", "--spread-form", "--material-input"):
        assert flag not in done.stdout


# ---------------------------------------------------------------------------
# --check-constants
# ---------------------------------------------------------------------------


def _patch_constants(monkeypatch: pytest.MonkeyPatch, values: dict[str, float]) -> None:
    for name, value in values.items():
        monkeypatch.setattr(fit_facepalm.blunder_check_rules, name, value, raising=False)


def _check_argv(scalar_run: ScalarRun, out: Path) -> list[str]:
    return ["--features", str(scalar_run.features), "--out", str(out), "--check-constants"]


def test_check_constants_exits_0_when_the_app_constants_are_the_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scalar_run: ScalarRun
) -> None:
    _patch_constants(monkeypatch, constants_of(scalar_run.report))

    assert fit_facepalm.main(_check_argv(scalar_run, tmp_path / "b.md")) == fit_facepalm.EXIT_OK


def test_shipped_constants_reproduce_from_the_committed_features(tmp_path: Path) -> None:
    """259 D-15 / 250 D-04: the app's FACEPALM_* constants are the refit on the committed plan 11 table."""
    code = fit_facepalm.main(
        [
            "--features",
            str(COMMITTED_FEATURES),
            "--labels",
            str(COMMITTED_LABELS),
            "--out",
            str(tmp_path / "check.md"),
            "--check-constants",
        ]
    )

    assert code == fit_facepalm.EXIT_OK


def test_check_constants_exits_6_and_prints_the_table_on_a_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scalar_run: ScalarRun,
) -> None:
    refit = constants_of(scalar_run.report)
    drifted = dict(refit)
    drifted["FACEPALM_INTERCEPT"] += 2 * fit_facepalm.CHECK_CONSTANTS_TOLERANCE
    # The new constant plan 09 adds is absent from the module: a mismatch row, not an error.
    del drifted["FACEPALM_REPLY_PROB_COEF"]
    _patch_constants(monkeypatch, drifted)
    monkeypatch.delattr(fit_facepalm.blunder_check_rules, "FACEPALM_REPLY_PROB_COEF", raising=False)

    code = fit_facepalm.main(_check_argv(scalar_run, tmp_path / "b.md"))

    assert code == fit_facepalm.EXIT_CONSTANTS_MISMATCH
    err = capsys.readouterr().err
    assert "FACEPALM_INTERCEPT" in err
    assert "FACEPALM_REPLY_PROB_COEF | missing" in err
    assert "FACEPALM_PLAYED_COEF" not in err


def test_check_constants_reports_every_constant_that_moved(monkeypatch: pytest.MonkeyPatch) -> None:
    coefs = ScalarCoefs(-1.0, -0.5, 0.8, 0.4, 2.0, 0.9)
    shipped = coefs.by_name()
    _patch_constants(monkeypatch, shipped)
    assert fit_facepalm.constants_mismatches(coefs) == []

    _patch_constants(monkeypatch, {name: value + 1.0 for name, value in shipped.items()})
    table = "\n".join(fit_facepalm.constants_mismatches(coefs))

    for name in fit_facepalm.CONSTANT_NAMES:
        assert name in table, name


# ---------------------------------------------------------------------------
# Hold-out, extras, owner section
# ---------------------------------------------------------------------------


def test_unlabelled_set_eight_rows_are_extras_not_fit_rows(tmp_path: Path) -> None:
    """Blind set-8 rows (empty label) are excluded as unlabelled and listed under Extra rows."""
    rows = synthetic_rows(rows=400)
    extras = [{**rows[i], "n": f"{900 + i}", "set": "8", "label": ""} for i in range(3)]
    features = write_table(tmp_path / "features.tsv", [*rows, *extras])
    out = tmp_path / "report.md"

    table = fit_facepalm.load_features(features)
    _, excluded = fit_facepalm.split_usable(table.rows)

    assert excluded[fit_facepalm.REASON_NO_LABEL] == len(extras)
    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0
    extra_section = out.read_text().split("## Extra rows", 1)[1].split("## Constants", 1)[0]
    for extra in extras:
        assert f"- row {extra['n']} (game {extra['game_id']} ply {extra['ply']}):" in extra_section


def test_a_table_without_set_eight_says_the_holdout_is_empty(
    tmp_path: Path, scalar_run: ScalarRun
) -> None:
    rows = [row for row in synthetic_rows(rows=400) if row["set"] != fit_facepalm.TEST_SET]
    features = write_table(tmp_path / "no8.tsv", rows)
    out = tmp_path / "no8.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    heading = f"## Sets {fit_facepalm.TRAIN_SETS_TEXT} vs set {fit_facepalm.TEST_SET}"
    section = out.read_text().split(heading, 1)[1].split("\n## ", 1)[0]
    assert fit_facepalm.HOLDOUT_EMPTY_NOTE in section
    # The hold-out is on the full table: set 8 has rows there and an AUC.
    assert "- AUC on set 8:" in scalar_run.report


LABEL_FILE_COLUMNS: tuple[str, ...] = ("n", "set", "link", "label", "comment")
OWNER_HEADING: str = "## Owner checks"


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


def test_owner_section_lists_commented_rows(tmp_path: Path, scalar_run: ScalarRun) -> None:
    """D-13: commented label rows verbatim with their score; the rest is skipped."""
    rows = fit_facepalm.load_features(scalar_run.features).rows
    scored = [row for row in rows if row.n in ("2", "3")]
    comment_a = "currently 6%, should be at least 90%"
    comment_b = "currently 88%, should be below 60% | with a pipe"
    labels = tmp_path / "labels.tsv"
    labels.write_text(
        "\n".join(
            [
                "\t".join(LABEL_FILE_COLUMNS),
                f"2\t2\thttps://example.test/a\t1\t{comment_a}",
                f"3\t3\thttps://example.test/b\t0\t{comment_b}",
                "4\t4\thttps://example.test/c\t1\t",  # an empty comment is skipped
                "5\t5\thttps://example.test/d\t1",  # no comment cell at all is skipped
                "99999\t8\thttps://example.test/f\t0\tnot in the table",
            ]
        )
        + "\n"
    )
    out = tmp_path / "report.md"

    code = _main_code(
        ["--features", str(scalar_run.features), "--out", str(out), "--labels", str(labels)]
    )

    assert code == 0
    report = out.read_text()
    section = _owner_text(report)
    coefs = ScalarCoefs(*(constants_of(report)[name] for name in fit_facepalm.CONSTANT_NAMES))
    for row, comment, link in ((scored[0], comment_a, "a"), (scored[1], comment_b, "b")):
        score = fit_facepalm._fmt(fit_facepalm.scalar_score(row, coefs))
        cell = comment.replace("|", "\\|")
        expected = f"| {row.n} | {row.n} | {row.label:g} | https://example.test/{link} | {cell} | {score} |"
        assert expected in section, expected
    assert (
        "| 99999 | 8 | n/a | https://example.test/f | not in the table | not in features |"
        in section
    )
    assert "example.test/c" not in section and "example.test/d" not in section


def test_owner_section_without_labels_says_so(scalar_run: ScalarRun) -> None:
    section = _owner_text(scalar_run.report)

    assert "--labels" in section
    # The sections that do not need the label file are there all the same.
    assert "Pure-miss pass rate" in section


def test_labels_file_without_comment_column_is_an_error(
    tmp_path: Path, scalar_run: ScalarRun, capsys: pytest.CaptureFixture[str]
) -> None:
    for dropped in ("comment", "n"):
        columns = [name for name in LABEL_FILE_COLUMNS if name != dropped]
        labels = tmp_path / f"no-{dropped}.tsv"
        labels.write_text("\t".join(columns) + "\n")
        out = tmp_path / f"no-{dropped}.md"

        code = _main_code(
            ["--features", str(scalar_run.features), "--out", str(out), "--labels", str(labels)]
        )

        assert code == fit_facepalm.EXIT_FIT_ERROR
        assert not out.exists()
        assert f"'{dropped}'" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# D-12 alternatives (information only) and the D-15 cut table
# ---------------------------------------------------------------------------


def _alternative_aucs(report: str) -> dict[str, float]:
    """The CV AUC mean of each shape row of the alternatives table."""
    section = report.split("## Alternatives (information only)", 1)[1].split("\n## ", 1)[0]
    aucs: dict[str, float] = {}
    for shape in fit_facepalm.SHAPES:
        match = re.search(
            rf"^\| {shape}: .*\| \d+ \| (\d\.\d{{3}}) \| \d\.\d{{3}} \|$", section, re.M
        )
        assert match is not None, shape
        aucs[shape] = float(match.group(1))
    return aucs


def test_alternatives_section_is_information_only(tmp_path: Path) -> None:
    """Four shapes and the |delta AUC| line; the constants stay the chosen fit when another scores higher."""
    features = write_table(
        tmp_path / "strong-spread.tsv", synthetic_rows(spread_coef=STRONG_SPREAD_COEF)
    )
    out = tmp_path / "report.md"

    assert fit_facepalm.main(["--features", str(features), "--out", str(out)]) == 0

    report = out.read_text()
    aucs = _alternative_aucs(report)
    assert max(aucs, key=lambda shape: aucs[shape]) == "quiet_spread_reply"
    assert re.search(
        r"\|AUC\(chosen\) - AUC\(shipped_baseline\)\| = \d\.\d{3} .*: (within|outside) range",
        report,
    )
    # The constants block is the chosen fit, not the best-scoring alternative: it equals the
    # coefficients printed in the "Chosen shape" section.
    chosen_section = report.split("## Chosen shape", 1)[1].split("\n## ", 1)[0]
    printed = {
        name: float(match.group(1))
        for name, label in zip(
            fit_facepalm.CONSTANT_NAMES,
            ("intercept", "played", "loss", "missed", "best_prob", "reply_prob"),
            strict=True,
        )
        if (match := re.search(rf"^- {label}: (\S+)$", chosen_section, flags=re.MULTILINE))
    }
    constants = constants_of(report)
    assert len(printed) == len(constants)
    for name, value in printed.items():
        assert constants[name] == pytest.approx(value, abs=1e-4)


def test_d15_cut_table_lists_every_cut(scalar_run: ScalarRun) -> None:
    section = scalar_run.report.split("## Fair / unfair among passers at the D-15 cuts", 1)[1]
    section = section.split("\n## ", 1)[0]

    for cut in fit_facepalm.D15_CUTS:
        assert f"score >= {cut:.2f}" in section
    assert "| all |" in section
    assert re.search(r"^\| loses \| \d+ \| \d+ \| \d+ \| \d+ / \d+ \|", section, flags=re.MULTILINE)
