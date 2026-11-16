"""Tests for the decaying-mean helper of the set-8 disagreement draw (SEED-261115-agg)."""

from __future__ import annotations

import pytest

from app.services.blunder_check_rules import (
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_MATE,
    LOSS_CAP,
    MATE_LOSS,
)
from app.services.facepalm_score import loss_feature, missed_feature
from scripts.blunder_check.decaying_mean import (
    DECAY_DEPTHS,
    DECAY_RATIO,
    DECAY_WEIGHTS,
    decaying_mean,
    gain_series,
    loss_series,
)


def array(*odd: int | None) -> list[int | None]:
    """A 9-slot material array from the five odd-depth values; even slots copy the previous odd."""
    slots: list[int | None] = []
    for index, value in enumerate(odd):
        slots.append(value)
        if index < len(odd) - 1:
            slots.append(value)
    return slots


def test_weights_derive_from_the_ratio() -> None:
    assert DECAY_DEPTHS == (1, 3, 5, 7, 9)
    assert DECAY_RATIO == 0.5
    assert DECAY_WEIGHTS == (1.0, 0.5, 0.25, 0.125, 0.0625)


def test_decaying_mean_normalises_over_known_depths() -> None:
    assert decaying_mean(dict.fromkeys(DECAY_DEPTHS, 4)) == pytest.approx(4.0)
    partial = {1: 2, 3: 4, 5: None, 7: None, 9: None}
    assert decaying_mean(partial) == pytest.approx((2 + 0.5 * 4) / 1.5)
    assert decaying_mean(dict.fromkeys(DECAY_DEPTHS)) is None
    assert decaying_mean({}) is None


def test_loss_series_reads_odd_slots_and_caps() -> None:
    assert loss_series(array(-3, 0, 0, 0, 0), None) == {1: 3, 3: 0, 5: 0, 7: 0, 9: 0}
    assert loss_series(array(-9, -9, -9, -9, -9), None) == dict.fromkeys(DECAY_DEPTHS, LOSS_CAP)
    assert loss_series(array(2, 2, 2, 2, 2), None) == dict.fromkeys(DECAY_DEPTHS, 0)
    assert loss_series(array(None, 0, 0, 0, 0), None)[1] is None


def test_loss_series_mate_counts_from_its_ply() -> None:
    series = loss_series(array(-1, -1, -1, -1, -1), 2)
    assert series == {1: 1, 3: MATE_LOSS, 5: MATE_LOSS, 7: MATE_LOSS, 9: MATE_LOSS}


def test_gain_series_best_minus_kept_capped() -> None:
    played = array(0, 0, 0, 0, 0)
    queen_trade = [1, 1, 1, 1, 10, 10, 1, 1, 1]
    assert gain_series(played, queen_trade, None) == {
        1: 1,
        3: 1,
        5: FACEPALM_MISSED_CAP,
        7: 1,
        9: 1,
    }


def test_gain_series_mate_counts_from_its_ply() -> None:
    series = gain_series(array(0, 0, 0, 0, 0), array(0, 0, 0, 0, 0), 4)
    assert series == {
        1: 0,
        3: 0,
        5: FACEPALM_MISSED_MATE,
        7: FACEPALM_MISSED_MATE,
        9: FACEPALM_MISSED_MATE,
    }


def test_gain_series_unknown_slot_and_floor() -> None:
    series = gain_series(array(None, 0, 0, 0, 0), array(2, 2, 2, 2, 2), None)
    assert series[1] is None and series[3] == 2
    # best - max(0, played): a played +2 against a best +5 keeps 2, so the gain is 3.
    assert gain_series(array(2, 2, 2, 2, 2), array(5, 5, 5, 5, 5), None)[3] == 3
    # A best line behind the played one is floored at 0 (the shipped missed term has no floor).
    assert gain_series(array(4, 4, 4, 4, 4), array(1, 1, 1, 1, 1), None)[3] == 0


@pytest.mark.parametrize(
    ("played_3", "best_3", "played_mate", "best_mate"),
    [
        (0, 9, None, None),
        (-3, 0, None, None),
        (-7, 4, None, None),
        (2, 5, None, None),
        (4, 1, None, None),
        (0, 0, 3, None),
        (0, 0, None, 2),
        (-1, 3, None, 6),
        (None, 3, None, None),
        (0, None, None, None),
    ],
)
def test_depth_three_parity_with_the_shipped_features(
    played_3: int | None, best_3: int | None, played_mate: int | None, best_mate: int | None
) -> None:
    played = array(None, played_3, 0, 0, 0)
    best = array(None, best_3, 0, 0, 0)
    loss = loss_series(played, played_mate)[3]
    shipped_loss = loss_feature(None if played_3 is None else -played_3, played_mate, loss_floor=0)
    assert (None if loss is None else float(loss)) == shipped_loss

    gain = gain_series(played, best, best_mate)[3]
    shipped_gain = missed_feature(
        played_3,
        best_3,
        best_mate,
        missed_floor=None,
        missed_cap=FACEPALM_MISSED_CAP,
        missed_mate=FACEPALM_MISSED_MATE,
    )
    # The shipped missed term is 0.0 for an unknown slot, the series says None there.
    assert (0.0 if gain is None else float(gain)) == max(0.0, shipped_gain)
