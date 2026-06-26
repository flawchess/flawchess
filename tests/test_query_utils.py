"""Unit tests for apply_game_filters date predicates (Phase 92 D-10).

Tests verify that the from_date / to_date parameters produce the correct
SQL WHERE clauses: from_date uses >= and to_date uses < with a +1-day shift
so that to_date is inclusive (covers the whole day).

These tests are INTENTIONALLY written before the signature change (TDD RED):
they call apply_game_filters with from_date= / to_date= keyword args that
do not yet exist, so they will fail with a TypeError until Task 2 lands.

Phase 128 Plan 03 (Task 2 TDD RED): orientation dimension tests for apply_game_filters.
Tests assert that orientation="missed" produces EXISTS referencing missed_tactic_motif
and orientation="allowed" (default) references allowed_tactic_motif.
"""

import datetime

from sqlalchemy import select

from app.models.game import Game
from app.repositories.query_utils import apply_game_filters


def _compile_sql(stmt: object) -> str:
    """Compile stmt to a SQL string without literal binds (parameterised form)."""
    from sqlalchemy.dialects import postgresql

    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))  # ty: ignore[unresolved-attribute]


def _get_params(stmt: object) -> dict:
    """Return the bind parameters dict from the compiled statement."""
    from sqlalchemy.dialects import postgresql

    compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False})  # ty: ignore[unresolved-attribute]
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
    from_val = next(
        (v for k, v in params.items() if "from_date" in k or "played_at" in k.lower()), None
    )
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


# ---------------------------------------------------------------------------
# Phase 128 Plan 03 (Task 2 TDD) — orientation dimension tests (D-09)
# ---------------------------------------------------------------------------


class TestTacticOrientationFilter:
    """orientation param in apply_game_filters selects the correct column set.

    Phase 128 D-09: orientation selects the matching column pair at both filter
    sites. Unknown-family keys still yield no ints (no-op). Orientation is a
    closed Literal enum — never raw column-name interpolation (T-128-05).
    """

    _BASE_FAMILIES = ["fork"]  # single known family to get a non-empty motif int set

    def _stmt_sql(self, orientation: str | None = None) -> str:
        """Return compiled SQL for apply_game_filters with tactic_families=[fork]."""
        stmt = select(Game.id).where(Game.user_id == 1)
        kwargs: dict = dict(
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            user_id=1,
            tactic_families=self._BASE_FAMILIES,
        )
        if orientation is not None:
            kwargs["orientation"] = orientation
        stmt = apply_game_filters(stmt, **kwargs)
        from sqlalchemy.dialects import postgresql

        return str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )

    def test_default_orientation_references_both_columns(self) -> None:
        """orientation unspecified (default) → EXISTS uses BOTH column sets.

        Quick 260621-sm8 follow-up: the neutral default is now "either" (was
        "allowed"), matching build_flaw_filter_clauses. An "allowed" default would
        make non-tactic callers (which omit orientation) wrongly filter once the
        tactic EXISTS is gated on _tactic_controls_active.
        """
        sql = self._stmt_sql()
        assert "allowed_tactic_motif" in sql, (
            f"Default orientation must reference allowed_tactic_motif; got: {sql}"
        )
        assert "missed_tactic_motif" in sql, (
            f"Default orientation (either) must reference missed_tactic_motif; got: {sql}"
        )

    def test_allowed_orientation_references_allowed_column(self) -> None:
        """orientation='allowed' → EXISTS uses allowed_tactic_motif."""
        sql = self._stmt_sql(orientation="allowed")
        assert "allowed_tactic_motif" in sql, (
            f"orientation='allowed' must reference allowed_tactic_motif; got: {sql}"
        )
        assert "missed_tactic_motif" not in sql, (
            f"orientation='allowed' must NOT reference missed_tactic_motif; got: {sql}"
        )

    def test_missed_orientation_references_missed_column(self) -> None:
        """orientation='missed' → EXISTS uses missed_tactic_motif.

        The same FAMILY_TO_MOTIF_INTS expansion and EXISTS structure is used;
        only the column name changes (D-09).
        """
        sql = self._stmt_sql(orientation="missed")
        assert "missed_tactic_motif" in sql, (
            f"orientation='missed' must reference missed_tactic_motif; got: {sql}"
        )
        assert "allowed_tactic_motif" not in sql, (
            f"orientation='missed' must NOT reference allowed_tactic_motif; got: {sql}"
        )

    def test_unknown_family_is_noop_for_both_orientations(self) -> None:
        """Unknown family keys → no EXISTS clause added (no-op, T-126-02 preserved)."""
        for orientation in ("allowed", "missed"):
            stmt = select(Game.id).where(Game.user_id == 1)
            stmt = apply_game_filters(
                stmt,
                time_control=None,
                platform=None,
                rated=None,
                opponent_type="all",
                from_date=None,
                to_date=None,
                user_id=1,
                tactic_families=["not_a_real_family"],
                orientation=orientation,  # type: ignore[arg-type]
            )
            from sqlalchemy.dialects import postgresql

            sql = str(
                stmt.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": False},
                )
            )
            assert "tactic_motif" not in sql, (
                f"Unknown family with orientation={orientation!r} must produce no tactic EXISTS clause; got: {sql}"
            )


# ---------------------------------------------------------------------------
# Phase 129 Plan 01 (Task 1 TDD RED) — depth + either tests for apply_game_filters
# ---------------------------------------------------------------------------


class TestTacticDepthAndEitherFilter:
    """max_tactic_depth + orientation='either' in apply_game_filters.

    Phase 129 D-05/D-08: depth bound on the active orientation's depth column;
    'either' = OR across both missed_* and allowed_* column sets.
    These tests target apply_game_filters (Games-EXISTS site). The site now gates
    on confidence too (SEED-061); these depth/either tests are confidence-agnostic
    because the compiled fixture uses high-confidence rows.
    """

    def _stmt_sql(
        self,
        orientation: str = "allowed",
        min_tactic_depth: int | None = None,
        max_tactic_depth: int | None = None,
    ) -> str:
        """Compile apply_game_filters with tactic_families=['fork'] to SQL text."""
        stmt = select(Game.id).where(Game.user_id == 1)
        kwargs: dict = dict(
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            user_id=1,
            tactic_families=["fork"],
            orientation=orientation,
        )
        if min_tactic_depth is not None:
            kwargs["min_tactic_depth"] = min_tactic_depth
        if max_tactic_depth is not None:
            kwargs["max_tactic_depth"] = max_tactic_depth
        stmt = apply_game_filters(stmt, **kwargs)
        from sqlalchemy.dialects import postgresql

        return str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )

    def test_either_references_both_columns(self) -> None:
        """orientation='either' → EXISTS clause references BOTH missed and allowed motif columns."""
        sql = self._stmt_sql(orientation="either")
        assert "missed_tactic_motif" in sql, (
            f"either orientation must reference missed_tactic_motif; got: {sql}"
        )
        assert "allowed_tactic_motif" in sql, (
            f"either orientation must reference allowed_tactic_motif; got: {sql}"
        )

    def test_depth_none_omits_depth_column(self) -> None:
        """max_tactic_depth=None → no depth column in the clause."""
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=None)
        # No depth predicate when no bound is set
        assert "allowed_tactic_depth" not in sql, (
            f"max_tactic_depth=None must NOT add allowed_tactic_depth predicate; got: {sql}"
        )

    def test_depth_bound_references_depth_column(self) -> None:
        """max_tactic_depth=3 → clause includes the orientation's depth column."""
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=3)
        assert "allowed_tactic_depth" in sql, (
            f"max_tactic_depth=3 must add allowed_tactic_depth predicate; got: {sql}"
        )
        assert "missed_tactic_depth" not in sql, (
            f"allowed orientation must NOT reference missed_tactic_depth; got: {sql}"
        )

    def test_missed_depth_bound_references_missed_depth_column(self) -> None:
        """orientation='missed' + max_tactic_depth=3 → missed_tactic_depth predicate."""
        sql = self._stmt_sql(orientation="missed", max_tactic_depth=3)
        assert "missed_tactic_depth" in sql, (
            f"missed orientation + depth bound must add missed_tactic_depth predicate; got: {sql}"
        )
        assert "allowed_tactic_depth" not in sql, (
            f"missed orientation must NOT reference allowed_tactic_depth; got: {sql}"
        )

    def test_mate_exemption_removed_when_depth_set(self) -> None:
        """Quick 260620-l5k: mates obey the depth range — no exemption OR at the Games site.

        The Phase 129 D-04 exemption was removed, so a bounded depth filter references
        the motif column ONCE (primary family filter), with a plain range predicate.
        Quick 260626-bdt: the decided-lost NOT(…) clause adds OR inside its own scope;
        those are unrelated to the depth predicate and are expected.
        """
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=3)
        # Quick 260621-qz9: allowed column is decision-anchored (+1), so the depth
        # predicate compiles as "allowed_tactic_depth + <param> <=".
        assert "allowed_tactic_depth +" in sql and "<=" in sql  # depth predicate is present
        # The old mate exemption was an OR that let mates bypass the depth bound:
        # "(allowed_tactic_depth <= N OR eval_mate IS NOT NULL)". Verify that pattern
        # is gone by checking the depth predicate's local AND-term contains no OR.
        # Quick 260626-bdt: the NOT(decided_lost) clause appended after the depth term
        # contains its own OR — those are inside a NOT(...) wrapper and do NOT appear
        # between "allowed_tactic_depth" and the next " AND " separator.
        depth_ctx = sql[sql.find("allowed_tactic_depth") :]
        depth_term = depth_ctx.split(" AND ")[0]  # just the depth's own AND-term
        assert " OR " not in depth_term, (
            f"No OR exemption on the depth predicate itself; depth term: {depth_term}"
        )

    def test_min_depth_bound_references_depth_column(self) -> None:
        """Quick 260620-l5k: min_tactic_depth adds a >= lower-bound predicate.

        Quick 260621-qz9: the allowed column carries the decision-anchored +1 offset,
        so both bounds compile as "allowed_tactic_depth + <param>" comparisons.
        """
        sql = self._stmt_sql(orientation="allowed", min_tactic_depth=2, max_tactic_depth=5)
        assert "allowed_tactic_depth +" in sql and ">=" in sql, (
            f"min_tactic_depth=2 must add an offset 'allowed_tactic_depth + ... >='; got: {sql}"
        )
        assert "allowed_tactic_depth +" in sql and "<=" in sql, (
            f"max_tactic_depth=5 must add an offset 'allowed_tactic_depth + ... <='; got: {sql}"
        )

    def test_allowed_depth_decision_anchored_missed_not(self) -> None:
        """Quick 260621-qz9: the Games-EXISTS site offsets allowed depth by +1; missed bare."""
        allowed_sql = self._stmt_sql(orientation="allowed", min_tactic_depth=2, max_tactic_depth=5)
        assert "allowed_tactic_depth +" in allowed_sql, (
            f"allowed orientation must offset the depth column (+1); got: {allowed_sql}"
        )
        missed_sql = self._stmt_sql(orientation="missed", min_tactic_depth=2, max_tactic_depth=5)
        assert "missed_tactic_depth >=" in missed_sql, (
            f"missed orientation must compare the bare column; got: {missed_sql}"
        )
        assert "missed_tactic_depth +" not in missed_sql, (
            f"missed orientation must NOT offset the depth column; got: {missed_sql}"
        )

    def test_either_depth_references_both_depth_columns(self) -> None:
        """orientation='either' + max_tactic_depth → both missed and allowed depth columns."""
        sql = self._stmt_sql(orientation="either", max_tactic_depth=3)
        assert "missed_tactic_depth" in sql, (
            f"either + depth must reference missed_tactic_depth; got: {sql}"
        )
        assert "allowed_tactic_depth" in sql, (
            f"either + depth must reference allowed_tactic_depth; got: {sql}"
        )

    def test_confidence_gate_present_in_exists_site(self) -> None:
        """Games-EXISTS site (apply_game_filters) MUST gate on confidence (SEED-061).

        Reverses the Phase 129 "Pitfall 3" asymmetry: confidence is now gated at
        both the Games-EXISTS and the Flaws list (build_flaw_filter_clauses), so a
        game cannot match a tactic-family filter on a below-threshold tactic that
        would never render a chip.
        """
        for orientation in ("allowed", "missed", "either"):
            sql = self._stmt_sql(orientation=orientation)
            assert "tactic_confidence" in sql, (
                f"apply_game_filters orientation={orientation!r} must gate on confidence; got: {sql}"
            )
