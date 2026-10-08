"""Pure Pydantic tests for the Phase 236 phone grade boundary (SEED-193, D-01/D-07)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.train import RECHECK_DEPTH_CAP, PhoneGrade, ReviewRequest, SolveRequest

# Typed as dict[str, Any]: these tests intentionally pass malformed values.
_SOLVE_KWARGS: dict[str, Any] = {
    "position": 0,
    "guess": "several",
    "played_move": "e2e4",
    "move_quality": "good",
}
_REVIEW_KWARGS: dict[str, Any] = {"v": 1, "exit": "next", "review_ms": 5000}

_VALID_PHONE_GRADE: dict[str, Any] = {
    "v": 1,
    "tier": "inaccuracy",
    "key_es": 0.62,
    "played_es": 0.55,
    "key_depth": 14,
    "played_depth": 13,
}


def _solve(phone_grade: Any) -> SolveRequest:
    return SolveRequest.model_validate({**_SOLVE_KWARGS, "phone_grade": phone_grade})


def _review(phone_grade: Any) -> ReviewRequest:
    return ReviewRequest.model_validate({**_REVIEW_KWARGS, "phone_grade": phone_grade})


# Both request bodies carry the record with the same drop-to-None contract.
_BUILDERS = pytest.mark.parametrize("build", [_solve, _review], ids=["solve", "review"])

Builder = Callable[[Any], SolveRequest | ReviewRequest]


def _with(**overrides: Any) -> dict[str, Any]:
    return {**_VALID_PHONE_GRADE, **overrides}


def _without(key: str) -> dict[str, Any]:
    return {k: v for k, v in _VALID_PHONE_GRADE.items() if k != key}


def test_field_set_is_exactly_the_six_keys() -> None:
    """D-07: no device or engine hint, the record has exactly these keys."""
    assert set(PhoneGrade.model_fields) == {
        "v",
        "tier",
        "key_es",
        "played_es",
        "key_depth",
        "played_depth",
    }


@_BUILDERS
def test_valid_phone_grade_parses_and_round_trips(build: Builder) -> None:
    request = build(_VALID_PHONE_GRADE)
    assert request.phone_grade is not None
    assert request.phone_grade.model_dump() == _VALID_PHONE_GRADE


@_BUILDERS
def test_integer_expected_scores_at_the_bounds_are_accepted(build: Builder) -> None:
    """JSON has no float/int distinction: a phone ES of exactly 0 or 1 is legitimate."""
    request = build(_with(key_es=1, played_es=0))
    assert request.phone_grade is not None
    assert request.phone_grade.key_es == 1.0
    assert request.phone_grade.played_es == 0.0


@_BUILDERS
@pytest.mark.parametrize(
    "bad",
    [
        _with(threads=4),
        _with(wasm="simd"),
        _with(tier="best"),
        _with(v=2),
        _with(key_es=1.5),
        _with(played_es=-0.1),
        _with(key_es=float("nan")),
        _with(played_es=True),
        _with(key_es="0.6"),
        _without("key_es"),
        _without("v"),
        _without("tier"),
        _with(key_depth="15"),
        _with(played_depth=True),
        _with(played_depth=None),
        "inaccuracy",
        [],
    ],
)
def test_malformed_phone_grade_is_dropped_and_the_body_still_validates(
    build: Builder, bad: Any
) -> None:
    """D-01: a malformed record becomes None; the rest of the body is intact."""
    request = build(bad)
    assert request.phone_grade is None


def test_dropped_phone_grade_keeps_the_solve_fields() -> None:
    request = _solve(_with(threads=4))
    assert request.phone_grade is None
    assert request.position == 0
    assert request.played_move == "e2e4"


def test_dropped_phone_grade_keeps_every_review_telemetry_key() -> None:
    request = _review(_with(threads=4))
    assert request.phone_grade is None
    assert request.exit == "next"
    assert request.review_ms == 5000


@pytest.mark.parametrize(
    "raw,expected",
    [(300, RECHECK_DEPTH_CAP), (-3, 0), (0, 0), (18, 18), (17.6, 18)],
)
def test_depths_are_clamped(raw: float, expected: int) -> None:
    model = PhoneGrade.model_validate(_with(key_depth=raw, played_depth=raw))
    assert model.key_depth == expected
    assert model.played_depth == expected


def test_phone_grade_model_itself_rejects_an_extra_key() -> None:
    """extra="forbid" on the record: only the request wrappers swallow the error."""
    with pytest.raises(ValidationError):
        PhoneGrade.model_validate(_with(threads=4))


def test_absent_phone_grade_is_none_on_both_bodies() -> None:
    assert SolveRequest.model_validate(_SOLVE_KWARGS).phone_grade is None
    assert ReviewRequest.model_validate(_REVIEW_KWARGS).phone_grade is None


def test_review_request_without_phone_grade_validates_like_a_stale_bundle() -> None:
    request = ReviewRequest.model_validate(_REVIEW_KWARGS)
    assert request.model_dump(exclude_none=True) == {"v": 1, "exit": "next", "review_ms": 5000}


def test_review_request_unknown_top_level_key_still_raises() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest.model_validate({**_REVIEW_KWARGS, "future_field": 1})


def test_solve_request_ignores_unknown_keys() -> None:
    """A stale or newer bundle may send keys the server does not know (no extra=forbid)."""
    request = SolveRequest.model_validate(
        {**_SOLVE_KWARGS, "phone_grade": _VALID_PHONE_GRADE, "future_field": {"x": 1}}
    )
    assert request.phone_grade is not None
    assert not hasattr(request, "future_field")


def test_review_patch_excludes_the_phone_grade() -> None:
    """The router's telemetry patch must not carry the record (D-12)."""
    request: BaseModel = _review(_VALID_PHONE_GRADE)
    patch = request.model_dump(exclude_none=True, exclude={"phone_grade"})
    assert "phone_grade" not in patch
