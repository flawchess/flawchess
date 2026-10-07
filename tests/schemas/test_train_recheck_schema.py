"""Pure Pydantic tests for the Phase 235 disagreement re-check boundary (SEED-192, D-18)."""

from __future__ import annotations

from typing import Any

import pytest

from app.schemas.train import RECHECK_DEPTH_CAP, SolveRecheck, SolveRequest

# Typed as dict[str, Any]: these tests intentionally pass malformed values.
_SOLVE_KWARGS: dict[str, Any] = {
    "position": 0,
    "guess": "several",
    "played_move": "e2e4",
    "move_quality": "good",
}

_VALID_RECHECK: dict[str, Any] = {
    "v": 1,
    "outcome": "confirmed",
    "key_es": 0.6,
    "played_es": 0.62,
    "key_es_recheck": 0.7,
    "played_es_recheck": 0.69,
    "key_depth": 15,
    "played_depth": 16,
    "key_depth_recheck": 18,
    "played_depth_recheck": 20,
}


def _with(**overrides: Any) -> dict[str, Any]:
    return {**_VALID_RECHECK, **overrides}


def _without(key: str) -> dict[str, Any]:
    return {k: v for k, v in _VALID_RECHECK.items() if k != key}


def test_valid_recheck_parses() -> None:
    request = SolveRequest.model_validate({**_SOLVE_KWARGS, "recheck": _VALID_RECHECK})
    assert request.recheck is not None
    assert request.recheck.model_dump() == _VALID_RECHECK


def test_integer_expected_scores_at_the_bounds_are_accepted() -> None:
    """JSON has no float/int distinction: a phone ES of exactly 0 or 1 is legitimate."""
    request = SolveRequest.model_validate(
        {**_SOLVE_KWARGS, "recheck": _with(key_es=1, played_es=0)}
    )
    assert request.recheck is not None
    assert request.recheck.key_es == 1.0
    assert request.recheck.played_es == 0.0


@pytest.mark.parametrize(
    "bad",
    [
        _with(bogus=1),
        _with(outcome="maybe"),
        _with(v=2),
        _with(key_es=1.5),
        _with(played_es=-0.1),
        _with(key_es_recheck=float("nan")),
        _with(played_es_recheck=True),
        _with(key_es="0.6"),
        _without("key_es"),
        _without("v"),
        _with(key_depth="15"),
        _with(played_depth=True),
        _with(key_depth_recheck=None),
        "confirmed",
        [],
    ],
)
def test_malformed_recheck_is_dropped_and_the_solve_still_validates(bad: Any) -> None:
    """D-18: a malformed re-check becomes None; the rest of the request is intact."""
    request = SolveRequest.model_validate({**_SOLVE_KWARGS, "recheck": bad})
    assert request.recheck is None
    assert request.position == 0
    assert request.played_move == "e2e4"


@pytest.mark.parametrize(
    "raw,expected",
    [(300, RECHECK_DEPTH_CAP), (-3, 0), (0, 0), (18, 18), (17.6, 18)],
)
def test_depths_are_clamped(raw: float, expected: int) -> None:
    model = SolveRecheck.model_validate(_with(key_depth=raw, played_depth_recheck=raw))
    assert model.key_depth == expected
    assert model.played_depth_recheck == expected


def test_absent_recheck_is_none() -> None:
    assert SolveRequest.model_validate(_SOLVE_KWARGS).recheck is None


def test_solve_request_ignores_unknown_keys() -> None:
    """A stale or newer bundle may send keys the server does not know: the solve
    still validates (SolveRequest must NOT forbid extras)."""
    request = SolveRequest.model_validate(
        {**_SOLVE_KWARGS, "recheck": _VALID_RECHECK, "future_field": {"x": 1}}
    )
    assert request.recheck is not None
    assert not hasattr(request, "future_field")
