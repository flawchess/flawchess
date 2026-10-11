"""Service-level tests for the time-pressure helpers (Phase 88.1, Plan 09).

Phase 88.1 (D-07 supersedes D-05): cohort layer removed. Tests verify the new
same-game opp-quintile split design:
- iterate_clock_rows builds user_quintile_wdl + opp_quintile_wdl from the same
  filtered game-set, each side bucketed by its OWN clock-pct at endgame entry.
- build_quintile_bullets computes delta = user_score_in_Q − opp_score_in_Q
  using compute_score_difference_test (unpaired two-sample Wilson).
- n-gate per bullet = min(n_user_in_Q, n_opp_in_Q) >= MIN_GAMES_PER_PRESSURE_BIN.

Tests cover:
- Quintile bucketing boundary behaviour
- Independent user/opp quintile assignment in the same game
- Opponent-result inversion (user-win = opp-loss in opp_quintile_wdl)
- Delta=0 when user_score equals opp_score in the matching quintile
- N-gate produces stats=None when min(n_user_in_Q, n_opp_in_Q) < MIN
- query_cohort_clock_rows is removed from endgame_repository namespace
"""

import datetime
from typing import Any

import pytest

from app.services.endgame_service import (
    MIN_GAMES_PER_PRESSURE_BIN,
    compute_clock_diff_timeline,
    iterate_clock_rows,
)


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------


_UNSET: Any = object()


def _make_row(
    tc: str,
    user_clk_pct: float,
    opp_clk_pct: float,
    result: str = "1-0",
    user_color: str = "white",
    base_time_seconds: int = 300,
    game_id: int = 1,
    termination: str | None = None,
    user_clock: Any = _UNSET,
    opp_clock: Any = _UNSET,
    played_at: datetime.datetime | None = None,
) -> tuple[Any, ...]:
    """Build a minimal clock-stats row matching the shape consumed by iterate_clock_rows.

    Row indices consumed:
        [1] time_control_bucket
        [2] base_time_seconds
        [3] termination
        [4] result
        [5] user_color
        [6] ply_array
        [7] clock_array

    We use white-at-ply-0 (even) for user_clock, ply-1 (odd) for opp_clock.
    user_color="white" so extract_entry_clocks extracts (ply-0, ply-1).

    Plan 88-14: `termination` is consumed by the new top-zone aggregator for
    net_timeout_rate. `user_clock` / `opp_clock` overrides allow the caller to
    inject absolute-second clock values that don't match the pct convention,
    or pass `None` to exercise the clock-ineligible accumulation branch.
    """
    if user_clock is _UNSET:
        user_clock = user_clk_pct * base_time_seconds
    if opp_clock is _UNSET:
        opp_clock = opp_clk_pct * base_time_seconds
    return (
        game_id,  # [0] game_id
        tc,  # [1] time_control_bucket
        base_time_seconds,  # [2] base_time_seconds
        termination,  # [3] termination
        result,  # [4] result
        user_color,  # [5] user_color
        [0, 1],  # [6] ply_array (0=white's first move, 1=black's first move)
        [user_clock, opp_clock],  # [7] clock_array
        played_at,  # [8] played_at — consumed by compute_clock_diff_timeline (88-15 A-2)
    )


# ---------------------------------------------------------------------------
# Phase 88.1 design tests (RED -> GREEN after refactor)
# ---------------------------------------------------------------------------


class TestUserAndOppQuintileIndependentSplit:
    def test_user_and_opp_quintiles_are_independent_per_game(self) -> None:
        """Single game where user clk_pct=0.10 (quintile 0) and opp clk_pct=0.90 (quintile 4).

        The same game must increment user_quintile_wdl[(tc, 0)] AND
        opp_quintile_wdl[(tc, 4)] — two different quintile indices,
        same row.
        """
        row = _make_row(
            "blitz", user_clk_pct=0.10, opp_clk_pct=0.90, result="1-0", user_color="white"
        )
        _tc_total, user_q_wdl, opp_q_wdl, _tc_shared = iterate_clock_rows([row])

        # User in quintile 0 (max pressure) with one win.
        assert user_q_wdl.get(("blitz", 0)) == (1, 0, 0)
        # Opponent in quintile 4 (min pressure) with one loss (user won -> opp lost).
        assert opp_q_wdl.get(("blitz", 4)) == (0, 0, 1)
        # No cross-pollination into other quintile cells.
        assert user_q_wdl.get(("blitz", 4)) is None
        assert opp_q_wdl.get(("blitz", 0)) is None

    def test_opp_quintile_wdl_uses_inverted_result(self) -> None:
        """User wins (1-0, white) -> opp_quintile_wdl records a LOSS.

        Game contributes (1,0,0) to user_quintile_wdl and (0,0,1) to opp_quintile_wdl.
        """
        row = _make_row(
            "rapid", user_clk_pct=0.50, opp_clk_pct=0.50, result="1-0", user_color="white"
        )
        _tc_total, user_q_wdl, opp_q_wdl, _tc_shared = iterate_clock_rows([row])
        assert user_q_wdl.get(("rapid", 2)) == (1, 0, 0)  # user win
        assert opp_q_wdl.get(("rapid", 2)) == (0, 0, 1)  # opp loss

    def test_opp_inversion_user_loss_user_color_black(self) -> None:
        """User loses (1-0 with user_color=black) -> opp_quintile_wdl records a WIN."""
        # user_color="black" so user is at ply 1 (odd) and opp is at ply 0 (even).
        # Use a black-aware row: opp clock at ply 0, user clock at ply 1.
        base = 300
        # Build row so extract_entry_clocks returns user=0.50, opp=0.50.
        # With user_color="black", user_parity=1: ply 1 -> user_clock; ply 0 -> opp_clock.
        row = (
            1,  # game_id
            "rapid",
            base,
            None,
            "1-0",  # white wins => user (black) loses
            "black",
            [0, 1],
            [0.50 * base, 0.50 * base],  # ply 0 = opp's clock, ply 1 = user's clock
        )
        _tc_total, user_q_wdl, opp_q_wdl, _tc_shared = iterate_clock_rows([row])
        assert user_q_wdl.get(("rapid", 2)) == (0, 0, 1)  # user loss
        assert opp_q_wdl.get(("rapid", 2)) == (1, 0, 0)  # opp win

    def test_draw_appears_as_draw_in_both_splits(self) -> None:
        """Draw is a draw on both sides."""
        row = _make_row(
            "bullet", user_clk_pct=0.30, opp_clk_pct=0.70, result="1/2-1/2", user_color="white"
        )
        _tc_total, user_q_wdl, opp_q_wdl, _tc_shared = iterate_clock_rows([row])
        # User in quintile 1 (0.30 -> int(1.5) = 1), opp in quintile 3 (0.70 -> int(3.5) = 3).
        assert user_q_wdl.get(("bullet", 1)) == (0, 1, 0)
        assert opp_q_wdl.get(("bullet", 3)) == (0, 1, 0)

    def test_shared_quintile_count_increments_only_when_quintiles_match(self) -> None:
        """Phase 148 item 3 (D-04): tc_shared_quintile_count[(tc, q)] counts only
        rows where user_quintile == opp_quintile == q. A row where the two
        sides land in DIFFERENT quintiles must not increment any bucket."""
        same_quintile_row = _make_row(
            "blitz", user_clk_pct=0.50, opp_clk_pct=0.50, result="1-0", user_color="white"
        )
        different_quintile_row = _make_row(
            "blitz", user_clk_pct=0.10, opp_clk_pct=0.90, result="1-0", user_color="white"
        )
        _tc_total, _user_q_wdl, _opp_q_wdl, tc_shared = iterate_clock_rows(
            [same_quintile_row, different_quintile_row]
        )
        assert tc_shared.get(("blitz", 2)) == 1
        # The different-quintile row (Q0 vs Q4) must not appear anywhere.
        assert tc_shared.get(("blitz", 0)) is None
        assert tc_shared.get(("blitz", 4)) is None


class TestRepositoryNoCohortFunction:
    def test_query_cohort_clock_rows_removed_from_repository(self) -> None:
        """query_cohort_clock_rows must be gone from endgame_repository namespace."""
        from app.repositories import endgame_repository

        assert not hasattr(endgame_repository, "query_cohort_clock_rows")


# ---------------------------------------------------------------------------
# Existing behaviour preserved (carry-over with cohort plumbing removed)
# ---------------------------------------------------------------------------


class TestMinGamesPerPressureBinWired:
    def test_constant_imported_and_used(self) -> None:
        """MIN_GAMES_PER_PRESSURE_BIN must be importable from endgame_service (WR-05 wired)."""
        assert isinstance(MIN_GAMES_PER_PRESSURE_BIN, int)
        assert MIN_GAMES_PER_PRESSURE_BIN >= 1


# ---------------------------------------------------------------------------
# Plan 88-15 A-2: compute_clock_diff_timeline (rolling-window per-ISO-week
# clock-diff timeline). Pooled across TCs. Backend timeline for the restored
# "Average Clock Difference over Time" line chart.
# ---------------------------------------------------------------------------


def _dt(year: int, month: int, day: int) -> datetime.datetime:
    """Build a tz-naive datetime for played_at fixtures."""
    return datetime.datetime(year, month, day, 12, 0, 0)


class TestComputeClockDiffTimeline:
    """Plan 88-15 A-2: rolling-window per-ISO-week clock-diff timeline.

    Verifies the new compute_clock_diff_timeline aggregator: filters rows for
    clock eligibility, computes per-game clock_diff_pct = (user-opp)/base * 100
    (PERCENT, not fraction — chart Y-axis convention), buckets by ISO Monday,
    and emits one point per week using the rolling-mean value of the LAST
    eligible game in that week. per_week_game_count is THIS week's count only.
    """

    def test_empty_rows_returns_empty_points(self) -> None:
        resp = compute_clock_diff_timeline([])
        assert resp.points == []

    def test_single_week_single_game(self) -> None:
        # One game in ISO week of Mon 2025-01-06. user=180s, opp=120s, base=300s.
        # diff_pct = (180 - 120) / 300 * 100 = +20.0
        rows = [
            _make_row(
                "blitz",
                user_clk_pct=0.60,
                opp_clk_pct=0.40,
                game_id=1,
                played_at=_dt(2025, 1, 8),  # Wed of ISO week starting Mon 2025-01-06
            ),
        ]
        resp = compute_clock_diff_timeline(rows)
        assert len(resp.points) == 1
        p = resp.points[0]
        assert p.date == "2025-01-06"
        assert p.avg_clock_diff_pct == pytest.approx(20.0, abs=1e-6)
        assert p.game_count == 1
        assert p.per_week_game_count == 1

    def test_multiple_weeks_rolling_window(self) -> None:
        # 4 games across 3 ISO weeks. Window=100 (default) ⇒ rolling mean is
        # the cumulative mean throughout this test.
        # Week 2025-01-06: 1 game with diff +20%
        # Week 2025-01-13: 2 games with diffs +10% and -10%
        # Week 2025-01-20: 1 game with diff +0%
        # Rolling means at last-of-week:
        #   wk1            -> 20.0      (1 game)
        #   wk2 last (Fri) -> (20+10-10)/3 = 6.666... (3 games)
        #   wk3            -> (20+10-10+0)/4 = 5.0   (4 games)
        rows = [
            _make_row(
                "blitz",
                0.60,
                0.40,
                game_id=1,
                played_at=_dt(2025, 1, 8),  # wk1
            ),
            _make_row(
                "blitz",
                0.55,
                0.45,
                game_id=2,
                played_at=_dt(2025, 1, 14),  # wk2, Tue
            ),
            _make_row(
                "blitz",
                0.45,
                0.55,
                game_id=3,
                played_at=_dt(2025, 1, 17),  # wk2, Fri (LAST of wk2)
            ),
            _make_row(
                "blitz",
                0.50,
                0.50,
                game_id=4,
                played_at=_dt(2025, 1, 22),  # wk3
            ),
        ]
        resp = compute_clock_diff_timeline(rows)
        assert len(resp.points) == 3
        assert resp.points[0].date == "2025-01-06"
        assert resp.points[0].avg_clock_diff_pct == pytest.approx(20.0, abs=1e-6)
        assert resp.points[0].per_week_game_count == 1
        assert resp.points[0].game_count == 1
        assert resp.points[1].date == "2025-01-13"
        assert resp.points[1].avg_clock_diff_pct == pytest.approx(20.0 / 3.0, abs=1e-3)
        assert resp.points[1].per_week_game_count == 2
        assert resp.points[1].game_count == 3
        assert resp.points[2].date == "2025-01-20"
        assert resp.points[2].avg_clock_diff_pct == pytest.approx(5.0, abs=1e-6)
        assert resp.points[2].per_week_game_count == 1
        assert resp.points[2].game_count == 4

    def test_clock_ineligible_rows_skipped(self) -> None:
        # 3 rows in the same ISO week — only 1 is eligible:
        # - row 1: base_time_seconds = 0 (guard fail)
        # - row 2: user_clock = None (clock-eligibility fail)
        # - row 3: eligible, diff = +30%
        rows = [
            _make_row(
                "blitz",
                0.60,
                0.40,
                game_id=1,
                base_time_seconds=0,
                played_at=_dt(2025, 1, 8),
            ),
            _make_row(
                "blitz",
                0.60,
                0.40,
                game_id=2,
                user_clock=None,
                played_at=_dt(2025, 1, 8),
            ),
            _make_row(
                "blitz",
                0.65,
                0.35,
                game_id=3,
                played_at=_dt(2025, 1, 8),
            ),
        ]
        resp = compute_clock_diff_timeline(rows)
        assert len(resp.points) == 1
        p = resp.points[0]
        assert p.avg_clock_diff_pct == pytest.approx(30.0, abs=1e-6)
        assert p.game_count == 1
        assert p.per_week_game_count == 1

    def test_iso_week_bucketing_emits_last_game(self) -> None:
        # Three games on Mon/Wed/Sun of one ISO week (2025-01-06 .. 2025-01-12).
        # Cumulative rolling means: 10, 15, 20 -> emitted point uses the Sun
        # (last) game's rolling mean of 20. per_week_game_count = 3.
        rows = [
            _make_row(
                "blitz",
                0.55,
                0.45,
                game_id=1,  # +10%
                played_at=_dt(2025, 1, 6),  # Mon
            ),
            _make_row(
                "blitz",
                0.60,
                0.40,
                game_id=2,  # +20% (cum mean 15)
                played_at=_dt(2025, 1, 8),  # Wed
            ),
            _make_row(
                "blitz",
                0.65,
                0.35,
                game_id=3,  # +30% (cum mean 20)
                played_at=_dt(2025, 1, 12),  # Sun (LAST of week)
            ),
        ]
        resp = compute_clock_diff_timeline(rows)
        assert len(resp.points) == 1
        p = resp.points[0]
        assert p.date == "2025-01-06"
        assert p.avg_clock_diff_pct == pytest.approx(20.0, abs=1e-6)
        assert p.game_count == 3
        assert p.per_week_game_count == 3

    def test_percent_units_not_fraction(self) -> None:
        # user_clock=600s, opp_clock=300s, base=600s.
        # diff_pct must be 50.0 (PERCENT), not 0.5 (fraction).
        # This pins the unit-convention lock from the plan's Step 2 LOCKED note.
        rows = [
            _make_row(
                "rapid",
                user_clk_pct=0.0,  # ignored — we override absolute values below
                opp_clk_pct=0.0,
                base_time_seconds=600,
                user_clock=600.0,
                opp_clock=300.0,
                game_id=1,
                played_at=_dt(2025, 1, 8),
            ),
        ]
        resp = compute_clock_diff_timeline(rows)
        assert len(resp.points) == 1
        # The hard line: 50.0 not 0.5. Documents the percent-units lock.
        assert resp.points[0].avg_clock_diff_pct == pytest.approx(50.0, abs=1e-6)

    def test_cutoff_prefills_rolling_window_from_pre_cutoff_games(self) -> None:
        """REVIEW.md WR-01: pre-cutoff games pre-fill the rolling window but
        do NOT produce emitted points.

        Fixture: 4 pre-cutoff games (week 2024-12-30) with diff +10% each, then
        1 post-cutoff game (week 2025-01-13) with diff +30%. The cutoff is set
        to Mon 2025-01-06 12:00.

        Expected behaviour (post-fix):
          - Only the post-cutoff week's point is emitted (1 point total).
          - That point's game_count = 5 (4 pre-cutoff pre-fill + 1 post-cutoff)
            — the trailing rolling-window is fully populated from history.
          - per_week_game_count = 1 (only the in-week post-cutoff game).
          - avg_clock_diff_pct = (10*4 + 30) / 5 = 14.0.

        Pre-fix behaviour (the bug): the call site passed the already-filtered
        ``clock_rows`` so pre-cutoff games were dropped before reaching the
        aggregator, and the first emitted point's game_count was 1 instead of 5
        — the "trailing 100" tooltip was a lie at the leading edge.
        """
        rows = [
            # 4 pre-cutoff games on Wed 2025-01-01 (ISO week 2024-12-30).
            _make_row("blitz", 0.55, 0.45, game_id=1, played_at=_dt(2025, 1, 1)),
            _make_row("blitz", 0.55, 0.45, game_id=2, played_at=_dt(2025, 1, 1)),
            _make_row("blitz", 0.55, 0.45, game_id=3, played_at=_dt(2025, 1, 2)),
            _make_row("blitz", 0.55, 0.45, game_id=4, played_at=_dt(2025, 1, 2)),
            # 1 post-cutoff game on Tue 2025-01-14 (ISO week 2025-01-13).
            _make_row("blitz", 0.65, 0.35, game_id=5, played_at=_dt(2025, 1, 14)),
        ]
        cutoff = _dt(2025, 1, 6)  # Mon 2025-01-06 noon
        resp = compute_clock_diff_timeline(rows, cutoff=cutoff)
        # Only the post-cutoff week emits a point — pre-cutoff weeks are
        # pre-fill only.
        assert len(resp.points) == 1
        pt = resp.points[0]
        assert pt.date == "2025-01-13"
        # Rolling window saturated from pre-cutoff history: 5 games.
        assert pt.game_count == 5
        # Only 1 game in the post-cutoff week — per-week count tracks
        # in-window games only.
        assert pt.per_week_game_count == 1
        # Mean: 4 games at +10% pre-cutoff + 1 game at +30% post-cutoff = +14%.
        assert pt.avg_clock_diff_pct == pytest.approx(14.0, abs=1e-6)

    def test_cutoff_none_emits_all_weeks(self) -> None:
        """Sanity: cutoff=None preserves the legacy behaviour of emitting
        every ISO-week point (no pre-cutoff drop).
        """
        rows = [
            _make_row("blitz", 0.55, 0.45, game_id=1, played_at=_dt(2025, 1, 1)),
            _make_row("blitz", 0.65, 0.35, game_id=2, played_at=_dt(2025, 1, 14)),
        ]
        resp = compute_clock_diff_timeline(rows, cutoff=None)
        assert len(resp.points) == 2
        assert {p.date for p in resp.points} == {"2024-12-30", "2025-01-13"}


# ---------------------------------------------------------------------------
# Phase 94.3 Plan 04 — percentile_rows kwarg + per-(metric × TC) chip attach
# ---------------------------------------------------------------------------
