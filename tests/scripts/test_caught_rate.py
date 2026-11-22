"""Tests for the Phase 261 caught-rate calibration script (pure aggregation, no DB)."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.dialects import postgresql

from app.models.blunder_check import WindowOutcome
from app.services.score_confidence import wilson_bounds
from scripts.blunder_check.caught_rate import (
    SHARE_ACCEPT_HIGH,
    SHARE_ACCEPT_LOW,
    SHARE_MIN_WINDOWS,
    ArmLabel,
    BandRow,
    OutcomeLabel,
    WindowRow,
    aggregate_caught_rate,
    band_of,
    build_statement,
    count_unscored,
    exploration_share,
    render_report,
    window_row,
)

TODAY = datetime.date(2026, 11, 22)


def _rows(
    arm: ArmLabel, outcome: OutcomeLabel, count: int, score: float | None = 0.4, own: bool = True
) -> list[WindowRow]:
    return [WindowRow(arm, own, score, outcome) for _ in range(count)]


def _cell(rows: list[BandRow], arm: ArmLabel, origin: str, band: str) -> BandRow:
    (cell,) = [r for r in rows if (r.arm, r.origin, r.band) == (arm, origin, band)]
    return cell


def _share_rows(total: int, exploration: int) -> list[WindowRow]:
    return _rows("exploration", "caught", exploration) + _rows(
        "main", "caught", total - exploration
    )


def test_tracer_rows_to_report() -> None:
    rows = [
        WindowRow("exploration", True, 0.2, "caught"),
        WindowRow("exploration", False, 0.4, "missed"),
        WindowRow("main", True, 0.85, "caught"),
        WindowRow("main", False, 0.95, "false_alarm"),
        WindowRow("legacy", True, None, "missed"),
    ]
    report = render_report(rows, target="dev", since=None, today=TODAY)
    assert "## Exploration share" in report
    assert "## Caught rate by score band" in report
    for arm in ("exploration", "main", "legacy"):
        assert f"### Arm: {arm}" in report


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (0.0, "below 0.3"),
        (0.2999, "below 0.3"),
        (0.3, "0.3-0.5"),
        (0.4999, "0.3-0.5"),
        (0.5, "0.5-0.6"),
        (0.7, "0.7-0.8"),
        (0.9, "0.9-1.0"),
        (1.0, "0.9-1.0"),
        (None, None),
    ],
)
def test_band_of_bounds(score: float | None, band: str | None) -> None:
    assert band_of(score) == band


def test_reached_is_caught_plus_missed_and_false_alarms_sit_beside() -> None:
    rows = (
        _rows("main", "caught", 3, 0.55)
        + _rows("main", "missed", 1, 0.55)
        + _rows("main", "false_alarm", 2, 0.55)
    )
    cell = _cell(aggregate_caught_rate(rows), "main", "all", "0.5-0.6")
    assert (cell.reached, cell.caught, cell.rate, cell.false_alarms) == (4, 3, 0.75, 2)
    assert (cell.low, cell.high) == wilson_bounds(0.75, 4)


def test_origin_split_own_foreign_and_all() -> None:
    rows = _rows("main", "caught", 2, 0.8, own=True) + _rows("main", "missed", 3, 0.8, own=False)
    table = aggregate_caught_rate(rows)
    assert _cell(table, "main", "own", "0.8-0.9").reached == 2
    assert _cell(table, "main", "foreign", "0.8-0.9").reached == 3
    assert _cell(table, "main", "all", "0.8-0.9").reached == 5


def test_empty_cell_has_no_rate_or_interval() -> None:
    cell = _cell(aggregate_caught_rate([]), "exploration", "all", "below 0.3")
    assert (cell.reached, cell.rate, cell.low, cell.high) == (0, None, None, None)


def test_a_false_alarm_only_cell_has_no_rate() -> None:
    cell = _cell(
        aggregate_caught_rate(_rows("main", "false_alarm", 2, 0.65)), "main", "all", "0.6-0.7"
    )
    assert (cell.reached, cell.rate, cell.false_alarms) == (0, None, 2)


def test_legacy_window_falls_back_to_the_live_score() -> None:
    row = window_row(None, True, None, 0.42, WindowOutcome.CAUGHT)
    assert (row.arm, row.score, row.outcome) == ("legacy", 0.42, "caught")


def test_the_snapshot_wins_over_the_live_score() -> None:
    row = window_row(1, False, 0.3, 0.9, WindowOutcome.MISSED)
    assert (row.arm, row.score, row.outcome) == ("exploration", 0.3, "missed")


def test_main_arm_and_false_alarm_outcome_map() -> None:
    row = window_row(0, True, 0.8, None, WindowOutcome.FALSE_ALARM)
    assert (row.arm, row.outcome) == ("main", "false_alarm")


def test_legacy_window_without_any_score_is_unscored() -> None:
    row = window_row(None, True, None, None, WindowOutcome.MISSED)
    assert row.score is None
    rows = [row, *_rows("legacy", "caught", 1, 0.5)]
    assert count_unscored(rows) == {"exploration": 0, "main": 0, "legacy": 1}
    # An unscored window falls in no band.
    legacy_reached = sum(r.reached for r in aggregate_caught_rate(rows) if r.arm == "legacy")
    assert legacy_reached == 2 * 1  # only the scored window, once per origin row it lands in


def test_share_below_the_minimum_is_insufficient() -> None:
    assert exploration_share(_share_rows(SHARE_MIN_WINDOWS - 1, 100)).verdict == "insufficient"


def test_share_with_no_windows_is_insufficient() -> None:
    result = exploration_share([])
    assert (result.n, result.share, result.verdict) == (0, None, "insufficient")


def test_share_on_target_is_accepted() -> None:
    result = exploration_share(_share_rows(SHARE_MIN_WINDOWS, 100))
    assert (result.n, result.exploration, result.verdict) == (500, 100, "accept")


def test_share_entirely_below_the_band_fails() -> None:
    result = exploration_share(_share_rows(1000, 120))
    assert result.high is not None and result.high < SHARE_ACCEPT_LOW
    assert result.verdict == "fail"


def test_share_entirely_above_the_band_fails() -> None:
    result = exploration_share(_share_rows(1000, 320))
    assert result.low is not None and result.low > SHARE_ACCEPT_HIGH
    assert result.verdict == "fail"


def test_legacy_rows_are_excluded_from_the_share() -> None:
    rows = _share_rows(499, 100) + _rows("legacy", "caught", 50)
    result = exploration_share(rows)
    assert (result.n, result.verdict) == (499, "insufficient")


def test_statement_filters_herring_limits_the_live_score_and_has_no_join() -> None:
    compiled = str(build_statement(None).compile(dialect=postgresql.dialect()))
    assert "window_case !=" in compiled
    assert "LIMIT" in compiled
    assert "JOIN" not in compiled.upper()
    assert "ended_at" not in compiled


def test_statement_with_since_filters_on_ended_at() -> None:
    compiled = str(build_statement(TODAY).compile(dialect=postgresql.dialect()))
    assert "ended_at >=" in compiled


def test_report_never_holds_ids() -> None:
    rows = _rows("exploration", "caught", 3, 0.2) + _rows("main", "missed", 2, 0.9, own=False)
    report = render_report(rows, target="prod", since=TODAY, today=TODAY).lower()
    for forbidden in ("user_id", "game_id", "username", "window_id"):
        assert forbidden not in report
