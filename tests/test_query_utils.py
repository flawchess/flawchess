"""Unit tests for apply_game_filters date predicates (Phase 92 D-10).

Tests verify that the from_date / to_date parameters produce the correct
SQL WHERE clauses: from_date uses >= and to_date uses < with a +1-day shift
so that to_date is inclusive (covers the whole day).

These tests are INTENTIONALLY written before the signature change (TDD RED):
they call apply_game_filters with from_date= / to_date= keyword args that
do not yet exist, so they will fail with a TypeError until Task 2 lands.
"""

import datetime

import pytest
from sqlalchemy import select

from app.models.game import Game
from app.repositories.query_utils import apply_game_filters


def _compile_sql(stmt: object) -> str:
    """Compile stmt to a SQL string without literal binds (parameterised form)."""
    from sqlalchemy.dialects import postgresql

    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))  # type: ignore[union-attr]


def _get_params(stmt: object) -> dict:
    """Return the bind parameters dict from the compiled statement."""
    from sqlalchemy.dialects import postgresql

    compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False})  # type: ignore[union-attr]
    return dict(compiled.params)


def test_apply_game_filters_no_date_filter() -> None:
    """from_date=None, to_date=None — no played_at predicate in WHERE clause."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=None,
        to_date=None,
    )
    sql = _compile_sql(stmt)
    # No date predicates should appear.
    assert "played_at >= " not in sql, f"Unexpected from_date predicate: {sql}"
    assert "played_at < " not in sql, f"Unexpected to_date predicate: {sql}"


def test_apply_game_filters_from_only() -> None:
    """from_date set, to_date=None — only the >= predicate appears."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=datetime.date(2026, 3, 1),
        to_date=None,
    )
    sql = _compile_sql(stmt)
    params = _get_params(stmt)

    # Lower-bound predicate must appear.
    assert "played_at >=" in sql, f"Missing from_date predicate: {sql}"
    # Upper-bound predicate must NOT appear.
    assert "played_at <" not in sql, f"Unexpected to_date predicate: {sql}"
    # The bind value must match the supplied from_date.
    from_val = next((v for k, v in params.items() if "from_date" in k or "played_at" in k.lower()), None)
    assert from_val == datetime.date(2026, 3, 1) or any(
        v == datetime.date(2026, 3, 1) for v in params.values()
    ), f"Expected bind value 2026-03-01 in params: {params}"


def test_apply_game_filters_to_only() -> None:
    """to_date set, from_date=None — only the < predicate appears."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=None,
        to_date=datetime.date(2026, 4, 1),
    )
    sql = _compile_sql(stmt)

    # Upper-bound predicate must appear.
    assert "played_at <" in sql, f"Missing to_date predicate: {sql}"
    # Lower-bound predicate must NOT appear.
    assert "played_at >=" not in sql, f"Unexpected from_date predicate: {sql}"


def test_apply_game_filters_date_range() -> None:
    """Both bounds set — both predicates appear; upper bound is shifted +1 day.

    D-10: the upper bound uses ``<  to_date + 1 day`` so that to_date itself
    is inclusive (covers up to end-of-day in UTC without timezone math).
    """
    stmt = select(Game)
    to_date = datetime.date(2026, 4, 1)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=datetime.date(2026, 3, 1),
        to_date=to_date,
    )
    sql = _compile_sql(stmt)
    params = _get_params(stmt)

    # Both predicates must appear.
    assert "played_at >=" in sql, f"Missing from_date predicate: {sql}"
    assert "played_at <" in sql, f"Missing to_date predicate: {sql}"

    # The upper bound must be shifted by +1 day (2026-04-02, not 2026-04-01).
    expected_upper = datetime.date(2026, 4, 2)
    assert expected_upper in params.values(), (
        f"Expected upper bound {expected_upper} (to_date + 1 day) in params: {params}"
    )
