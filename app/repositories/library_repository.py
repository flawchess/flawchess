"""Library (Games-surface) repository — Phase 106 (SEED-036, LIBG-08/09).

Single SQL transcription of the Phase 105 ES-drop severity math, used for:
  - the user-color-scoped EXISTS flaw-severity filter (LIBG-08), and
  - per-ply flagged-row observation for the cross-check seam guard.

This is the ONE place where the severity-drop math is duplicated (SQL vs the
Python kernel in flaws_service.py). To prevent drift it imports the kernel
constants (LICHESS_K, MISTAKE_DROP, BLUNDER_DROP, INACCURACY_DROP,
MATE_CP_EQUIVALENT) — no literal thresholds in SQL — and the seam is guarded by
the SQL<->kernel cross-check fixture test (tests/test_library_repository.py,
criterion 5 / B2).

Correctness pins replicated from the kernel (flaws_service._run_all_moves_pass
+ _ply_to_es):
  - mover = white if ply even else black; the `sign` flip lives inside the ES sigmoid.
  - eval-AFTER semantics: positions[N].eval_cp is the eval AFTER move N, so
    ES_before = ES(ply N-1) via LAG, ES_after = ES(ply N).
  - mate Option B: a non-null eval_mate maps to ±MATE_CP_EQUIVALENT cp BEFORE the
    sigmoid (never the hard 1.0/0.0 converter).
  - interior null evals (current OR previous) are non-flaggable (excluded).
  - USER-COLOR scope (B1): only plies whose mover-parity equals the game's
    user_color can satisfy the filter — opponent-only blunders never match.

All user input crosses into SQL via bound parameters (user_id, drop threshold);
no f-string interpolation of user input (T-106-01).
"""

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Float, Select, Subquery, and_, case, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import apply_game_filters
from app.services.eval_utils import LICHESS_K
from app.services.flaws_service import (
    BLUNDER_DROP,
    EVAL_COVERAGE_MIN,
    INACCURACY_DROP,
    MATE_CP_EQUIVALENT,
    MISTAKE_DROP,
    FlawSeverity,
)

# Severity -> minimum mover-POV ES drop. Imported constants, one source of truth
# with the Python kernel (_classify_severity). The Games filter offers only
# mistake/blunder per scope, but inaccuracy is mapped for completeness/cross-check.
_DROP_THRESHOLD: dict[FlawSeverity, float] = {
    "inaccuracy": INACCURACY_DROP,
    "mistake": MISTAKE_DROP,
    "blunder": BLUNDER_DROP,
}


def _drop_threshold(severity: FlawSeverity) -> float:
    """Return the minimum ES drop for a severity tier (imported kernel constant)."""
    return _DROP_THRESHOLD[severity]


def _cp_equiv(eval_cp: Any, eval_mate: Any) -> ColumnElement[Any]:
    """Mate Option-B cp-equivalent: ±MATE_CP_EQUIVALENT when mate, else raw cp.

    Accepts either a mapped column attribute (GamePosition.eval_cp) or a window
    expression (func.lag(...).over(...)); both are SQL column expressions.

    Mirrors flaws_service._ply_to_es: a non-null eval_mate substitutes
    +MATE_CP_EQUIVALENT when eval_mate > 0 else -MATE_CP_EQUIVALENT, BEFORE the
    sigmoid (never the hard 1.0/0.0 converter). NOTE: this matches the kernel's
    `> 0 / else` mapping, NOT sign(): the kernel maps eval_mate == 0 (producible
    from python-chess Mate(0)) to -MATE_CP_EQUIVALENT, whereas sign(0) == 0 would
    map it to ES 0.5 and diverge from the Python kernel (WR-01 cross-check drift).
    """
    return case(
        (
            eval_mate.isnot(None),
            case((eval_mate > 0, MATE_CP_EQUIVALENT), else_=-MATE_CP_EQUIVALENT),
        ),
        else_=eval_cp,
    )


def _es_expr(cp_equiv: ColumnElement[Any], mover_sign: ColumnElement[Any]) -> ColumnElement[Any]:
    """Mover-POV expected score: 1/(1+exp(-K * sign * cp_equiv)).

    Transcribes eval_utils.eval_cp_to_expected_score exactly, with LICHESS_K
    imported (no literal K in SQL).
    """
    # Cast to Float so the division is floating-point, matching the Python sigmoid.
    return 1.0 / (1.0 + func.exp(-LICHESS_K * mover_sign * func.cast(cp_equiv, Float)))


def _per_ply_drop_subquery(user_id: int) -> Subquery:
    """Build the per-ply ES-drop subquery for one user.

    Returns a subquery with columns: game_id, ply, eval_cp, eval_mate, prev_cp,
    prev_mate, drop (mover-POV ES drop). Non-flaggable rows (current OR previous
    eval null) are filtered by the caller via _drop_filter, and the mover-parity
    user-color restriction (against the correlated Game.user_color) by
    _user_ply_filter — so the same subquery serves both the EXISTS and the
    per-ply observation helper.

    mover = white if ply even else black -> sign = +1 if ply even else -1.
    """
    mover_sign = case((GamePosition.ply % 2 == 0, 1), else_=-1)

    prev_cp = func.lag(GamePosition.eval_cp).over(
        partition_by=GamePosition.game_id,
        order_by=GamePosition.ply.asc(),
    )
    prev_mate = func.lag(GamePosition.eval_mate).over(
        partition_by=GamePosition.game_id,
        order_by=GamePosition.ply.asc(),
    )

    es_after = _es_expr(_cp_equiv(GamePosition.eval_cp, GamePosition.eval_mate), mover_sign)
    es_before = _es_expr(_cp_equiv(prev_cp, prev_mate), mover_sign)

    inner = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.ply.label("ply"),
            GamePosition.eval_cp.label("eval_cp"),
            GamePosition.eval_mate.label("eval_mate"),
            prev_cp.label("prev_cp"),
            prev_mate.label("prev_mate"),
            (es_before - es_after).label("drop"),
        )
        .where(GamePosition.user_id == user_id)
        .subquery("per_ply")
    )
    return inner


def _drop_filter(inner: Subquery) -> ColumnElement[bool]:
    """Non-flaggable rows excluded: both current and previous eval must be present.

    Mirrors the kernel's "skip if either ES is None" (interior null, Pitfall 5).
    A null previous eval (the first ply of each game window) is also excluded —
    consistent with the kernel iterating from ply N=1 with a real N-1 neighbour.
    """
    has_curr = or_(inner.c.eval_cp.isnot(None), inner.c.eval_mate.isnot(None))
    has_prev = or_(inner.c.prev_cp.isnot(None), inner.c.prev_mate.isnot(None))
    return and_(has_curr, has_prev)


def _user_ply_filter(inner: Subquery) -> ColumnElement[bool]:
    """Restrict to the USER's plies (B1): mover-parity == the game's user_color.

    Correlates the outer Game row so the parity is matched against THAT game's
    user_color. A ply is the user's when:
      (ply even AND user_color = 'white') OR (ply odd AND user_color = 'black').
    """
    return or_(
        and_(inner.c.ply % 2 == 0, Game.user_color == "white"),
        and_(inner.c.ply % 2 == 1, Game.user_color == "black"),
    )


def flaw_exists_subquery(
    user_id: int,
    severities: Sequence[FlawSeverity],
) -> ColumnElement[bool]:
    """Correlated EXISTS: True iff the game has >=1 USER ply of a requested severity.

    The drop threshold is MIN over the requested severities (so ["mistake"]
    matches mistakes-or-worse; ["blunder"] matches blunders only). All thresholds
    and LICHESS_K are imported constants; user_id is a bound parameter.

    USER-COLOR scope (B1): only plies whose mover-parity equals the outer game's
    user_color satisfy the EXISTS, so a game where only the opponent blundered is
    NOT selected. The EXISTS correlates GamePosition.game_id to the outer Game.id
    and binds user_id, scoping the read to the authenticated user (T-106-AC).
    """
    if not severities:
        # No severities -> trivially-false predicate (matches no game).
        return false()

    threshold = min(_drop_threshold(s) for s in severities)
    inner = _per_ply_drop_subquery(user_id)

    return exists(
        select(inner.c.ply).where(
            inner.c.game_id == Game.id,
            _drop_filter(inner),
            _user_ply_filter(inner),
            inner.c.drop >= threshold,
        )
    )


async def flagged_plies_for_severity(
    session: AsyncSession,
    *,
    game_id: int,
    user_id: int,
    severity: FlawSeverity,
) -> list[int]:
    """Return the USER plies of a single game whose ES drop >= the severity threshold.

    Test/seam helper backing the SQL<->kernel cross-check (B2). Applies the same
    user-color scope and non-flaggable-row exclusion as the EXISTS filter, but
    observes the per-ply flag directly rather than collapsing to a boolean.
    """
    threshold = _drop_threshold(severity)
    inner = _per_ply_drop_subquery(user_id)

    stmt = (
        select(inner.c.ply)
        .select_from(inner)
        .join(Game, Game.id == inner.c.game_id)
        .where(
            inner.c.game_id == game_id,
            Game.user_id == user_id,
            _drop_filter(inner),
            _user_ply_filter(inner),
            inner.c.drop >= threshold,
        )
        .order_by(inner.c.ply.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


def _filtered_games_base(
    user_id: int,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    opponent_gap_min: int | None,
    opponent_gap_max: int | None,
    color: str | None = None,
) -> Select[tuple[int]]:
    """Build the filtered `SELECT Game.id` base shared by the archive + stats paths.

    The single place the Games-surface filter set (incl. the boolean
    flaw-severity EXISTS) is composed, so query_filtered_games,
    count_filtered_and_analyzed, and analyzed_game_ids stay in lockstep on what
    "the filtered set" means. user_id is threaded into both the base WHERE and
    the EXISTS scope (T-106-02AC / T-106-03AC).
    """
    base_stmt: Select[tuple[int]] = select(Game.id).where(Game.user_id == user_id)
    return apply_game_filters(
        base_stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        color=color,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        flaw_severity=flaw_severity,
        user_id=user_id,
    )


async def query_filtered_games(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> tuple[list[Game], int]:
    """Return paginated user Game objects, optionally flaw-severity filtered.

    Mirrors endgame_repository.query_endgame_games' paginated-archive shape, but
    drops the endgame-span subquery — the base select is simply the user's games,
    with the boolean flaw-severity EXISTS applied via apply_game_filters when
    severities are supplied (LIBG-08). When flaw_severity is None/empty the
    query is a plain filtered archive (no EXISTS).

    Returns (page_games, matched_count) where matched_count reflects ALL matching
    games before offset/limit. Ordered played_at DESC nulls last. The user_id is
    threaded into both the base WHERE and the EXISTS scope (T-106-02AC).
    """
    base_stmt = select(Game).where(Game.user_id == user_id)
    base_stmt = apply_game_filters(
        base_stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        color=color,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        flaw_severity=flaw_severity,
        user_id=user_id,
    )

    # Count total matching games (before pagination).
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    matched_count = (await session.execute(count_stmt)).scalar_one()

    if matched_count == 0:
        return [], 0

    games_stmt = base_stmt.order_by(Game.played_at.desc().nulls_last()).offset(offset).limit(limit)
    games = list((await session.execute(games_stmt)).scalars().all())
    return games, matched_count


def _analyzed_game_ids_subquery(user_id: int) -> Subquery:
    """Per-game coverage aggregate -> game_ids whose >=90% of plies carry an eval.

    Replicates flaws_service._compute_eval_coverage in SQL:
        SUM(CASE WHEN eval_cp OR eval_mate non-null THEN 1 ELSE 0 END)::float
        / COUNT(*)  >=  EVAL_COVERAGE_MIN
    grouped by game_id. EVAL_COVERAGE_MIN is the imported kernel constant (no 0.90
    literal). User-scoped via the game_positions.user_id == :user_id predicate.
    """
    has_eval = case(
        (or_(GamePosition.eval_cp.isnot(None), GamePosition.eval_mate.isnot(None)), 1),
        else_=0,
    )
    coverage = func.cast(func.sum(has_eval), Float) / func.count()
    return (
        select(GamePosition.game_id.label("game_id"))
        .where(GamePosition.user_id == user_id)
        .group_by(GamePosition.game_id)
        .having(coverage >= EVAL_COVERAGE_MIN)
        .subquery("analyzed")
    )


async def count_filtered_and_analyzed(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> tuple[int, int]:
    """Return (total_n, analyzed_n) over the filtered Games-surface set (LIBG-09).

    total_n   = count of games matching the filter set.
    analyzed_n = subset whose per-game eval coverage (plies with eval_cp OR
                 eval_mate non-null / total plies) >= EVAL_COVERAGE_MIN — the
                  identical gate the kernel applies per game, so analyzed_n here
                 equals the number of games the kernel would NOT report as
                 GameNotAnalyzed. A fully-analyzed game (only its final ply null)
                 scores (N-1)/N >= 0.90; an all-null chess.com game scores 0.0.

    Both are user-scoped. The panel uses analyzed_n / total_n as the explicit
    "% analyzed" denominator so it never implies clean games where evals are
    merely absent (criterion 4).
    """
    base = _filtered_games_base(
        user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=flaw_severity,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )
    base_subq = base.subquery("filtered")
    total_n = (await session.execute(select(func.count()).select_from(base_subq))).scalar_one()
    if total_n == 0:
        return 0, 0

    analyzed_subq = _analyzed_game_ids_subquery(user_id)
    analyzed_stmt = select(func.count()).select_from(
        select(base_subq.c.id).where(base_subq.c.id.in_(select(analyzed_subq.c.game_id))).subquery()
    )
    analyzed_n = (await session.execute(analyzed_stmt)).scalar_one()
    return total_n, analyzed_n


async def analyzed_game_ids(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> list[int]:
    """Return the analyzed (>=90% coverage) filtered game_ids, played_at ASC.

    The chronological game-id list the stats service iterates for its per-game
    kernel re-call (D1 pragmatic path) and rolling-GAME-window trend (D3). Same
    filter set + analyzed gate as count_filtered_and_analyzed; ordered oldest
    first so the trend windows accumulate in play order. User-scoped.
    """
    base = _filtered_games_base(
        user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=flaw_severity,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )
    base_subq = base.subquery("filtered")
    analyzed_subq = _analyzed_game_ids_subquery(user_id)
    stmt = (
        select(Game.id)
        .where(
            Game.id.in_(select(base_subq.c.id)),
            Game.id.in_(select(analyzed_subq.c.game_id)),
        )
        .order_by(Game.played_at.asc().nulls_last())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)
