"""Tests for the Phase 262 refit_shift report (pure functions, no DB).

The DB path (`fetch_rows`) is exercised by the dev run of the tracer and by the prod run at the
owner checkpoint.
"""

from __future__ import annotations

import math

import pytest

from app.services.blunder_check_rules import PLAYED_PROB_OFFSET
from app.services.facepalm_score import FacepalmType
from scripts.backfill_promotion_material import as_real
from scripts.blunder_check.fit_facepalm import D15_CUTS, FIT_SELECTION_THRESHOLD, ScalarCoefs
from scripts.blunder_check.refit_shift import (
    PHASE_259_COEFS,
    SampledBlunder,
    ShiftRow,
    candidate_coefs,
    pick_newly_passing,
    render_report,
    score_versions,
    summarize,
)

MOD = 10


def _blunder(
    *,
    loss: float | None,
    missed: float | None,
    best: float | None = 0.5,
    reply: float | None = 0.2,
    game_id: int = 1,
    ply: int = 10,
    is_own: bool = True,
) -> SampledBlunder:
    return SampledBlunder(
        game_id=game_id,
        ply=ply,
        is_own=is_own,
        played_prob=0.1,
        best_prob=best,
        reply_prob=reply,
        stored_loss=loss,
        stored_missed=missed,
    )


def _expected(
    coefs: ScalarCoefs, loss: float, missed: float, key_coef: float, key_prob: float
) -> float:
    z = (
        coefs.intercept
        + coefs.played_coef * math.log(0.1 + PLAYED_PROB_OFFSET)
        + coefs.loss_coef * loss
        + coefs.missed_coef * missed
        + key_coef * math.log(key_prob + PLAYED_PROB_OFFSET)
    )
    return 1.0 / (1.0 + math.exp(-z))


def _row(
    game_id: int,
    ply: int = 10,
    *,
    old: float | None,
    new: float | None,
    old_type: FacepalmType | None = "missed_win",
    new_type: FacepalmType | None = "missed_win",
    is_own: bool = False,
    inputs_changed: bool = False,
) -> ShiftRow:
    return ShiftRow(
        game_id=game_id,
        ply=ply,
        is_own=is_own,
        old_loss=1.0,
        old_missed=2.0,
        new_loss=1.0,
        new_missed=2.0,
        old_score=old,
        new_score=new,
        old_type=old_type,
        new_type=new_type,
        inputs_changed=inputs_changed,
    )


def test_mixed_row_reads_the_reply_when_shipped_and_the_best_move_when_candidate() -> None:
    row = score_versions(_blunder(loss=1.0, missed=2.0), None)
    candidate = candidate_coefs()
    assert row.old_score == pytest.approx(
        _expected(PHASE_259_COEFS, 1.0, 2.0, PHASE_259_COEFS.reply_prob_coef, 0.2)
    )
    assert row.new_score == pytest.approx(
        _expected(candidate, 1.0, 2.0, candidate.best_prob_coef, 0.5)
    )
    assert row.old_type == row.new_type == "missed_win"
    assert not row.inputs_changed


def test_mixed_row_without_a_best_move_probability_loses_its_score() -> None:
    row = score_versions(_blunder(loss=1.0, missed=2.0, best=None), None)
    assert row.old_score is not None
    assert row.new_score is None
    summary = summarize([row], mod=MOD)
    assert summary.lose_score == 1
    assert summary.gate_unscored == 1
    assert summary.gain_score == 0


def test_a_recomputed_pair_equal_in_four_byte_floats_is_not_a_change() -> None:
    stored = as_real(1.4516129032258065)
    assert stored != 1.4516129032258065  # the float64 replay is not representable in 4 bytes
    row = score_versions(_blunder(loss=stored, missed=0.0, reply=0.3), (1.4516129032258065, 0.0))
    assert not row.inputs_changed
    assert (row.new_loss, row.new_missed) == (stored, 0.0)


def test_a_recomputed_pair_that_differs_replaces_the_stored_pair() -> None:
    row = score_versions(_blunder(loss=1.0, missed=0.0), (3.0, 0.0))
    assert row.inputs_changed
    assert (row.old_loss, row.new_loss) == (1.0, 3.0)
    assert row.old_score is not None and row.new_score is not None
    assert row.new_score > row.old_score


def test_a_stored_null_row_that_settles_gains_a_score() -> None:
    row = score_versions(_blunder(loss=None, missed=None), (2.0, 0.0))
    assert row.old_score is None and row.old_type is None
    assert row.new_score is not None and row.new_type == "allowed_loss"
    assert summarize([row], mod=MOD).gain_score == 1


def test_summarize_counts_passers_enter_and_leave_and_scales_by_mod() -> None:
    rows = [
        _row(1, old=0.55, new=0.75),  # enters at 0.70 (and passes 0.50/0.55/0.60/0.65 both)
        _row(2, old=0.80, new=0.40, old_type="allowed_loss"),  # leaves
        _row(3, old=0.90, new=0.95, is_own=True),  # stays
        _row(4, old=None, new=0.72, is_own=True),  # enters, gains a score
        _row(5, old=0.60, new=None),  # loses a score
    ]
    summary = summarize(rows, mod=MOD)
    assert summary.sampled == 5
    assert summary.mod == MOD
    cut = FIT_SELECTION_THRESHOLD
    assert summary.passers_old[cut] == 2
    assert summary.passers_new[cut] == 3
    assert summary.passers_old[0.50] == 4
    assert set(D15_CUTS) <= set(summary.passers_old)
    assert summary.enter_by_new_type["missed_win"] == 2
    assert summary.leave_by_new_type["missed_win"] == 1
    assert summary.leave_by_old_type["allowed_loss"] == 1
    assert summary.own_passers_old == 1
    assert summary.own_passers_new == 2
    assert (summary.lose_score, summary.gain_score) == (1, 1)
    report = render_report(summary, [], target="dev", seed=1, spot_check=20)
    assert f"{summary.passers_new[cut]} (x{MOD} = {summary.passers_new[cut] * MOD})" in report
    assert f"{summary.leave_by_new_type['missed_win']} (x{MOD} = {MOD})" in report


def test_pick_newly_passing_is_deterministic_bounded_and_only_upward() -> None:
    rows = [_row(g, old=0.3, new=0.8) for g in range(1, 31)]
    rows += [
        _row(100, old=0.8, new=0.3),
        _row(101, old=0.9, new=0.9),
        _row(102, old=None, new=None),
    ]
    rows.append(_row(103, old=None, new=0.71))  # an unscored shipped row that now passes counts
    first = pick_newly_passing(rows, 20, seed=262)
    assert first == pick_newly_passing(rows, 20, seed=262)
    assert len(first) == 20
    assert all(r.new_score is not None and r.new_score >= FIT_SELECTION_THRESHOLD for r in first)
    assert all(r.old_score is None or r.old_score < FIT_SELECTION_THRESHOLD for r in first)
    assert {r.game_id for r in first}.isdisjoint({100, 101, 102})
    assert pick_newly_passing(rows, 20, seed=1) != first
    assert len(pick_newly_passing(rows[:3], 20, seed=262)) == 3
    assert pick_newly_passing([_row(1, old=0.9, new=0.9)], 20, seed=262) == []


def test_report_lists_links_and_holds_no_user_identity() -> None:
    rows = [_row(7, 33, old=0.4, new=0.9, inputs_changed=True)]
    report = render_report(
        summarize(rows, mod=MOD),
        pick_newly_passing(rows, 20, seed=262),
        target="prod",
        seed=262,
        spot_check=20,
    )
    assert "https://flawchess.com/analysis?game_id=7&ply=33" in report
    assert "promotion (inputs changed)" in report
    assert "user_id" not in report
    assert "username" not in report
