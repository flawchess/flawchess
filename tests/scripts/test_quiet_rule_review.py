"""Tests for the quiet-point rule review report (Phase 259 plan 02, D-09)."""

from __future__ import annotations

from pathlib import Path

import chess
import pytest

from scripts.blunder_check import facepalm_features, quiet_rule_review
from scripts.blunder_check.facepalm_features import LabelRow, build_feature_row, write_features_tsv
from scripts.blunder_check.quiet_rule_review import (
    CAUSES,
    D13_GAME_PLY,
    EXIT_BAD_TSV,
    EXIT_OK,
    FIXTURE_LABEL_NS,
    REVIEW_EXAMPLES,
    ReviewError,
    classify_change,
    main,
    render_review,
    review_rows,
)
from tests.services.line_material_fixtures import D13_FIXTURE, LINE_FIXTURES
from tests.services.maia_fakes import fake_full_policy

PINNED_ELO: float = 1500.0
PLAYED_PROB: float = 0.04


def _d13_row() -> facepalm_features.FeatureRow:
    return build_feature_row(
        LabelRow(
            n="extra", set_id="extra", game_id=D13_FIXTURE.game_id, ply=D13_FIXTURE.ply, label=""
        ),
        pre_board=chess.Board(D13_FIXTURE.pre_fen),
        played_uci=D13_FIXTURE.played_uci,
        pinned_elo=PINNED_ELO,
        played_prob=PLAYED_PROB,
        pv=D13_FIXTURE.refutation_line,
        pv_source="db",
        policy_fn=fake_full_policy,
        best_pv=D13_FIXTURE.best_line,
    )


def _fixture_rows() -> list[facepalm_features.FeatureRow]:
    """The committed label fixtures 153, 154, 156 and 170 as features rows (stored line = fixture)."""
    wanted = {int(n) for n in FIXTURE_LABEL_NS}
    rows: list[facepalm_features.FeatureRow] = []
    for fixture in LINE_FIXTURES:
        if fixture.label_n not in wanted:
            continue
        pre_board = chess.Board(fixture.pre_fen)
        rows.append(
            build_feature_row(
                LabelRow(
                    n=str(fixture.label_n),
                    set_id="6",
                    game_id=900000 + fixture.label_n,
                    ply=30,
                    label="1",
                ),
                pre_board=pre_board,
                played_uci=fixture.played_uci,
                pinned_elo=PINNED_ELO,
                played_prob=PLAYED_PROB,
                pv=fixture.line,
                pv_source="db",
                policy_fn=fake_full_policy,
                best_pv=None,  # the fixtures carry only the refutation line
            )
        )
    return rows


def _write(rows: list[facepalm_features.FeatureRow], path: Path) -> Path:
    write_features_tsv(rows, path)
    return path


def test_d13_row_end_to_end(tmp_path: Path) -> None:
    features = _write([_d13_row()], tmp_path / "features.tsv")
    out = tmp_path / "review.md"

    assert main(["--features", str(features), "--out", str(out)]) == EXIT_OK

    report = out.read_text()
    assert (
        f"https://flawchess.com/analysis?game_id={D13_FIXTURE.game_id}&ply={D13_FIXTURE.ply}"
        in report
    )
    # The best line's depth-1 value is a four-capture trade cut after two captures by the shipped rule.
    assert "d1 9 -> 0 [longer_exchange_settled]" in report
    assert "missed 2.581 -> 0.000" in report


def test_features_constant_matches_the_review_digits() -> None:
    assert quiet_rule_review.FEATURE_CELL_DIGITS == facepalm_features.FLOAT_SIGNIFICANT_DIGITS


def _steps(spec: list[tuple[bool, int, bool, bool]]) -> list[quiet_rule_review._Step]:
    return [quiet_rule_review._Step(opp, victim, 0, bm, om) for opp, victim, bm, om in spec]


@pytest.mark.parametrize(
    ("spec", "depth", "cause"),
    [
        # Line ends on a blunderer capture inside the walk: settled by the static exchange.
        ([(True, 3, False, False), (False, 3, False, False)], 3, "exchange_settled_at_end"),
        # Walk runs two plies past depth 1 and then stops on a quiet move.
        (
            [
                (True, 3, False, False),
                (False, 9, False, False),
                (True, 3, False, False),
                (False, 0, False, False),
            ],
            1,
            "longer_exchange_settled",
        ),
        # Exactly one ply past depth 3: the opponent's capture at ply 4 is pulled in.
        (
            [
                (True, 0, False, False),
                (False, 0, False, False),
                (True, 0, False, False),
                (True, 3, False, False),
                (False, 0, False, False),
            ],
            3,
            "later_capture_pulled_earlier",
        ),
        # Nothing explains it: a quiet line that ends without a capture.
        ([(True, 0, False, False), (False, 0, False, False)], 1, "other"),
        # An empty step list is "other", never an error.
        ([], 1, "other"),
    ],
)
def test_classify_change_causes(
    spec: list[tuple[bool, int, bool, bool]], depth: int, cause: str
) -> None:
    assert classify_change(_steps(spec), depth) == cause


def test_changed_fixtures_are_classified(tmp_path: Path) -> None:
    rows = _fixture_rows()
    assert {row.label_row.n for row in rows} == set(FIXTURE_LABEL_NS)
    features = _write(rows, tmp_path / "features.tsv")

    reviewed = review_rows(features)

    changed = [change for row in reviewed for change in row.changes]
    assert changed, "the fixtures were picked because the quiet rule changes them"
    assert all(change.cause in CAUSES for change in changed)
    report = render_review(reviewed)
    # The per-cause counts sum to the number of changed values (the 'all' row of the table).
    all_row = next(line for line in report.splitlines() if line.startswith("| all | all |"))
    assert int(all_row.rstrip(" |").rsplit("|", 1)[1]) == len(changed)
    # Every fixture row is an example, with its link.
    for row in reviewed:
        assert row.link in report


def test_report_is_deterministic(tmp_path: Path) -> None:
    features = _write([_d13_row(), *_fixture_rows()], tmp_path / "features.tsv")

    first = render_review(review_rows(features))
    second = render_review(review_rows(features))

    assert first == second
    assert first.count("### n=") <= max(REVIEW_EXAMPLES, len(FIXTURE_LABEL_NS) + 1)
    assert f"game_id={D13_GAME_PLY[0]}&ply={D13_GAME_PLY[1]}" in first


def test_missing_pre_fen_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    old_table = tmp_path / "old.tsv"
    old_table.write_text("n\tset\tgame_id\tply\tlabel\n1\t1\t7\t20\t1\n")

    code = main(["--features", str(old_table), "--out", str(tmp_path / "out.md")])

    assert code == EXIT_BAD_TSV
    assert "pre_fen" in capsys.readouterr().err
    assert not (tmp_path / "out.md").exists()
    with pytest.raises(ReviewError):
        review_rows(old_table)


def test_review_reports_zero_drift_on_its_own_tsv(tmp_path: Path) -> None:
    features = _write([_d13_row(), *_fixture_rows()], tmp_path / "features.tsv")

    reviewed = review_rows(features)

    assert not any(row.drift for row in reviewed)
    assert "(expected 0)" in render_review(reviewed)
    assert "drift from the recomputed quiet value: 0" in render_review(reviewed)


def test_review_imports_no_database_or_maia_code() -> None:
    source = Path(quiet_rule_review.__file__).read_text()

    for forbidden in ("db_url_for_target", "create_async_engine", "maia_engine"):
        assert forbidden not in source
