"""Pure Pydantic tests for the Phase 233 telemetry boundary models (SEED-190)."""

from __future__ import annotations

from typing import Any

import pydantic
import pytest

from app.schemas.train import (
    TELEMETRY_CARDS_CAP,
    TELEMETRY_DURATION_CAP_MS,
    TELEMETRY_EXPLORE_MOVES_CAP,
    TELEMETRY_LINE_STEPS_CAP,
    ReviewTelemetry,
    SolveRequest,
    SolveTelemetry,
)

# Typed as dict[str, Any]: these tests intentionally pass malformed values.
_SOLVE_KWARGS: dict[str, Any] = {
    "position": 0,
    "guess": "several",
    "played_move": "e2e4",
    "move_quality": "good",
}


@pytest.mark.parametrize(
    "raw,expected",
    [(1234.6, 1235), (99_999_999, TELEMETRY_DURATION_CAP_MS), (-5, 0), (0, 0), (1500, 1500)],
)
def test_duration_is_rounded_and_clamped(raw: float, expected: int) -> None:
    assert ReviewTelemetry.model_validate({"v": 1, "exit": "next", "review_ms": raw}).review_ms == (
        expected
    )
    assert SolveTelemetry.model_validate({"v": 1, "guess_ms": raw}).guess_ms == expected


def test_counters_clamp_to_their_caps() -> None:
    model = ReviewTelemetry.model_validate(
        {
            "v": 1,
            "exit": "next",
            "review_line_steps": 500,
            "review_cards_opened": 99,
            "review_board_moves": 999,
        }
    )
    assert model.review_line_steps == TELEMETRY_LINE_STEPS_CAP
    assert model.review_cards_opened == TELEMETRY_CARDS_CAP
    assert model.review_board_moves == TELEMETRY_EXPLORE_MOVES_CAP


@pytest.mark.parametrize(
    "payload",
    [
        {"v": 1, "exit": "next", "review_ms": True},
        {"v": 1, "exit": "next", "review_ms": "12"},
        {"v": 1, "exit": "next", "review_explored": 1},
        {"v": 1, "exit": "next", "review_board_moves": True},
        {"v": 1, "exit": "next", "bogus": 1},
        {"v": 1},
        {"v": 2, "exit": "next"},
        {"v": 1, "exit": "close"},
    ],
)
def test_review_telemetry_rejects_malformed(payload: dict[str, Any]) -> None:
    with pytest.raises(pydantic.ValidationError):
        ReviewTelemetry.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"v": 1, "client": "tablet"},
        {"v": 1, "guess_ms": True},
        {"v": 1, "resumed": 1},
        {"v": 1, "bogus": 1},
        {"v": 2},
    ],
)
def test_solve_telemetry_rejects_malformed(payload: dict[str, Any]) -> None:
    with pytest.raises(pydantic.ValidationError):
        SolveTelemetry.model_validate(payload)


@pytest.mark.parametrize(
    "bad",
    [{"v": 1, "bogus": 1}, {"v": 1, "client": "tablet"}, {"v": 1, "guess_ms": "12"}, {"v": 2}],
)
def test_solve_request_drops_invalid_telemetry_but_keeps_the_solve(bad: dict[str, Any]) -> None:
    req = SolveRequest.model_validate({**_SOLVE_KWARGS, "telemetry": bad})
    assert req.telemetry is None
    assert (req.position, req.guess, req.played_move, req.move_quality) == (
        0,
        "several",
        "e2e4",
        "good",
    )


def test_solve_request_keeps_valid_telemetry() -> None:
    req = SolveRequest.model_validate(
        {**_SOLVE_KWARGS, "telemetry": {"v": 1, "client": "desktop", "guess_ms": 900}}
    )
    assert req.telemetry is not None
    assert req.telemetry.client == "desktop"
    assert req.telemetry.guess_ms == 900


def test_dump_exclude_none_omits_unset_keys() -> None:
    assert ReviewTelemetry(v=1, exit="next").model_dump(exclude_none=True) == {
        "v": 1,
        "exit": "next",
    }
