"""Library (Games-surface) repository — Phase 106 (SEED-036, LIBG-08/09).

Phase 108 D-02 migration: the window-scan EXISTS flaw filter is replaced by a
direct `game_flaws` table lookup. The shared predicate builder
`build_flaw_filter_clauses` produces the family-aware WHERE clauses (OR within
family, AND across families per SEED-038); `flaw_exists_from_table` wraps them
in a correlated EXISTS for the Games tab. The same predicate builder is reused
by the Flaws SELECT path (Plan 108-05) so cross-tab filter unification is
enforced in code, not convention.

All user input crosses into SQL via bound parameters (user_id, severity, tag
values from `_SEVERITY_INT` / `_TEMPO_INT` dict lookups); no f-string
interpolation of user input (T-108-06).
"""

import datetime
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import Float, Select, Subquery, case, exists, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import (
    _PHASE_INT,
    _SEVERITY_INT,
    _TEMPO_INT,
)
from app.repositories.query_utils import apply_game_filters, player_only_gate
from app.schemas.library import FlawListItem
from app.services.flaws_service import (
    EVAL_COVERAGE_MIN,
    FlawSeverity,
    FlawTag,
)
from app.services.openings_service import derive_user_result

# ---------------------------------------------------------------------------
# Inverse encoding maps — reconstruct tags from game_flaws integer columns
# (D-02 migration: chips built from stored rows, not kernel re-call)
# ---------------------------------------------------------------------------

# int → FlawTag string (reverse of _SEVERITY_INT / _TEMPO_INT / _PHASE_INT).
# Dict comprehensions produce int→str; the ty: ignore[invalid-assignment] on
# each line suppresses the Literal narrowing mismatch (correct at runtime).
_SEVERITY_INT_TO_TAG: dict[int, FlawSeverity] = {  # ty: ignore[invalid-assignment]
    v: k for k, v in _SEVERITY_INT.items()
}
_TEMPO_INT_TO_TAG: dict[int, FlawTag] = {  # ty: ignore[invalid-assignment]
    v: k for k, v in _TEMPO_INT.items()
}
_PHASE_INT_TO_TAG: dict[int, Literal["opening", "middlegame", "endgame"]] = {  # ty: ignore[invalid-assignment]
    v: k for k, v in _PHASE_INT.items()
}


def build_flaw_filter_clauses(
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> list[ColumnElement[bool]]:
    """Return WHERE clauses filtering game_flaws rows (SEED-038 family-aware logic).

    OR within family, AND across families: each returned clause covers one family;
    the caller ANDs all clauses together. Phase tags (opening/middlegame/endgame)
    are NOT filter predicates per UI-SPEC §Tag-family sections — they produce no
    clause here.

    Encoding maps (_SEVERITY_INT / _TEMPO_INT) are imported from
    game_flaws_repository — single source of truth, no duplication (SEED-038 /
    CLAUDE.md §Shared Query Filters).

    Args:
        severity: Subset of ["mistake", "blunder"]. Set-membership: ["mistake"]
                  matches mistakes only, ["blunder"] matches blunders only, both
                  matches either. Empty = no severity filter (match all severities
                  present in game_flaws).
        tags: Selected FlawTag values from FlawFilterControl. Empty = no tag
              filter. Phase tags are ignored (never produce a clause).

    Returns:
        A list of SQLAlchemy column expressions. Empty list = no flaw filter
        (match all rows). The caller is responsible for ANDing the clauses.
    """
    clauses: list[ColumnElement[bool]] = []

    # Severity filter — set membership. The UI exposes Blunders/Mistakes as
    # independent toggles, so ["mistake"] must match mistakes ONLY (not "mistakes or
    # worse"). A prior MIN-threshold (severity >= min) leaked blunders into a
    # mistakes-only selection. game_flaws stores only mistake(1)/blunder(2) (D-03).
    if severity:
        clauses.append(GameFlaw.severity.in_([_SEVERITY_INT[s] for s in severity]))

    # Tempo family: OR within {low-clock, hasty, unrushed}
    tempo_tags = [t for t in tags if t in {"low-clock", "hasty", "unrushed"}]
    if tempo_tags:
        clauses.append(GameFlaw.tempo.in_([_TEMPO_INT[t] for t in tempo_tags]))

    # Opportunity family: OR within {miss, lucky}
    opp_tags = [t for t in tags if t in {"miss", "lucky"}]
    if opp_tags:
        opp_clauses: list[ColumnElement[bool]] = []
        if "miss" in opp_tags:
            opp_clauses.append(GameFlaw.is_miss.is_(True))
        if "lucky" in opp_tags:
            opp_clauses.append(GameFlaw.is_lucky.is_(True))
        clauses.append(or_(*opp_clauses))

    # Impact family: OR within {reversed, squandered}
    imp_tags = [t for t in tags if t in {"reversed", "squandered"}]
    if imp_tags:
        imp_clauses: list[ColumnElement[bool]] = []
        if "reversed" in imp_tags:
            imp_clauses.append(GameFlaw.is_reversed.is_(True))
        if "squandered" in imp_tags:
            imp_clauses.append(GameFlaw.is_squandered.is_(True))
        clauses.append(or_(*imp_clauses))

    # Phase tags (opening/middlegame/endgame) are intentionally NOT handled —
    # they are display-only tags in the UI, not filter predicates (RESEARCH Pitfall 5).

    return clauses


def flaw_exists_from_table(
    user_id: int,
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> ColumnElement[bool]:
    """Correlated EXISTS: True iff the game has >=1 flaw row satisfying the filter.

    game_flaws-backed EXISTS (replaces the Phase 106 window-scan EXISTS after
    D-02 migration). Scopes to the authenticated user and the outer Game.id so
    cross-user leaks are impossible (T-108-07).

    Returns true() when both severity and tags are empty — no filter = match all
    games. This mirrors the Phase 106 None sentinel: callers that pass no filter
    see no restriction added to the statement.

    Args:
        user_id: The authenticated user's ID — always included in the EXISTS
                 WHERE clause to prevent cross-user information disclosure.
        severity: Subset of ["mistake", "blunder"]. Empty = no severity filter.
        tags: Selected FlawTag values. Empty = no tag filter.
    """
    clauses = build_flaw_filter_clauses(severity, tags)
    if not clauses:
        # No filter — match all games (caller decides whether to add to statement)
        return true()
    # D-04: player-only gate — after Phase 113 game_flaws contains both sides;
    # the EXISTS filter for the Games tab must only match player flaws so an
    # opponent-only flaw does not falsely flag a game into the Flaw filter (R1/R6).
    # Game.id is the outer correlating column (correlated EXISTS pattern).
    return exists(
        select(GameFlaw.ply).where(
            GameFlaw.game_id == Game.id,
            GameFlaw.user_id == user_id,
            player_only_gate(GameFlaw.ply, Game.user_color),  # D-04 player gate
            *clauses,
        )
    )


def _reconstruct_tags(flaw: GameFlaw) -> list[FlawTag]:
    """Reconstruct FlawTag list from game_flaws typed columns in deterministic order.

    Order: opportunity (miss, lucky) → impact (reversed, squandered)
    → tempo. Phase tags (opening/middlegame/endgame) are intentionally EXCLUDED from
    the per-flaw tag list returned by the endpoint (they are display-only per UI-SPEC).

    The deterministic order mirrors _CHIP_ORDER in library_service.

    Args:
        flaw: A GameFlaw ORM row with typed boolean + int columns.

    Returns:
        A list of FlawTag strings in canonical order, with no phase tags.
    """
    tags: list[FlawTag] = []
    if flaw.is_miss:
        tags.append("miss")
    if flaw.is_lucky:
        tags.append("lucky")
    if flaw.is_reversed:
        tags.append("reversed")
    if flaw.is_squandered:
        tags.append("squandered")
    if flaw.tempo is not None:
        tempo_tag = _TEMPO_INT_TO_TAG.get(flaw.tempo)
        if tempo_tag is not None:
            tags.append(tempo_tag)
    return tags


async def query_flaws(
    session: AsyncSession,
    *,
    user_id: int,
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None,
    offset: int,
    limit: int,
) -> tuple[list[FlawListItem], int]:
    """Paginated SELECT f.* FROM game_flaws JOIN games for the Flaws subtab (Plan 108-05).

    Phase 112 (D-05/D-08): extended with two aliased game_positions outer-joins to
    source move_san, eval_cp/eval_mate before and after the flaw:
      - PositionAt  (alias for ply=N): move_san + eval-after fields
      - PositionBefore (alias for ply=N-1): eval-before fields
    LEFT JOIN ensures no crash when ply=0/1 has no prior position.

    Reuses build_flaw_filter_clauses (shared with the Games EXISTS filter) so
    cross-tab filter unification is enforced in code (SEED-038).

    Ordered recent-first: g.played_at DESC NULLS LAST, f.ply ASC (D-07).
    User-scoped via GameFlaw.user_id == user_id (T-108-10 IDOR mitigation).
    Never exposes *_hash columns (CLAUDE.md V5).

    Args:
        session: AsyncSession for DB access.
        user_id: The authenticated user's ID — always scopes the query (IDOR).
        severity: Severity tiers to include. Empty = no severity filter.
        tags: FlawTag values to filter on (phase tags produce no clause).
        time_control / platform / rated / opponent_type / from_date / to_date /
          color: Game-metadata filters (threaded through apply_game_filters).
        offset: Pagination offset (>= 0).
        limit: Page size (1..100, default 20 per D-08).

    Returns:
        (flaws, matched_count) where matched_count is the total before pagination.
    """
    flaw_clauses = build_flaw_filter_clauses(severity, tags)

    # Two aliases for game_positions (Phase 112, D-08):
    # PositionAt:     ply=N  → move_san + eval-after (same row as the flawed move)
    # PositionBefore: ply=N-1 → eval-before (position BEFORE the flawed move)
    # User-scoped on both joins (T-112-02: no cross-user position rows can attach).
    PositionAt = aliased(GamePosition, name="pos_at")  # noqa: N806
    PositionBefore = aliased(GamePosition, name="pos_before")  # noqa: N806

    # Base: game_flaws JOIN games + two LEFT JOINs on game_positions scoped to user
    base_stmt = (
        select(GameFlaw, Game, PositionAt, PositionBefore)
        .join(Game, Game.id == GameFlaw.game_id)
        .outerjoin(
            PositionAt,
            (PositionAt.game_id == GameFlaw.game_id)
            & (PositionAt.user_id == GameFlaw.user_id)
            & (PositionAt.ply == GameFlaw.ply),
        )
        .outerjoin(
            PositionBefore,
            (PositionBefore.game_id == GameFlaw.game_id)
            & (PositionBefore.user_id == GameFlaw.user_id)
            & (PositionBefore.ply == GameFlaw.ply - 1),
        )
        .where(
            GameFlaw.user_id == user_id,
            # D-04: player-only gate — after Phase 113 game_flaws contains both sides;
            # the Flaws-subtab list must only show player flaws so opponent blunders do
            # not appear as flaw cards. Game is already joined above (R2 gate).
            player_only_gate(GameFlaw.ply, Game.user_color),
            *flaw_clauses,
        )
    )

    # Apply game-metadata filters (time_control, platform, etc.) via shared util.
    # apply_game_filters adds conditions to a Select[T]; we feed it a select on Game
    # then apply its conditions to base_stmt via a subquery approach.
    # apply_game_filters filters only Game columns — no conflict with GamePosition aliases.
    game_filter_stmt: Select[tuple[int]] = select(Game.id).where(Game.user_id == user_id)
    game_filter_stmt = apply_game_filters(
        game_filter_stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        color=color,
        user_id=user_id,
    )
    base_stmt = base_stmt.where(GameFlaw.game_id.in_(game_filter_stmt))

    # Count total matching rows (before pagination).
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    matched_count = (await session.execute(count_stmt)).scalar_one()

    if matched_count == 0:
        return [], 0

    # Paginate, ordered recent-first (D-07).
    paged_stmt = (
        base_stmt.order_by(Game.played_at.desc().nulls_last(), GameFlaw.ply.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(paged_stmt)).all()

    items: list[FlawListItem] = [
        FlawListItem(
            game_id=flaw.game_id,
            ply=flaw.ply,
            fen=flaw.fen,
            move_san=pos_at.move_san if pos_at else None,
            severity=_SEVERITY_INT_TO_TAG[flaw.severity],
            tags=_reconstruct_tags(flaw),
            eval_cp_before=pos_before.eval_cp if pos_before else None,
            eval_mate_before=pos_before.eval_mate if pos_before else None,
            eval_cp_after=pos_at.eval_cp if pos_at else None,
            eval_mate_after=pos_at.eval_mate if pos_at else None,
            white_rating=game.white_rating,
            black_rating=game.black_rating,
            user_result=derive_user_result(game.result, game.user_color),
            played_at=game.played_at,
            time_control_bucket=game.time_control_bucket,
            time_control_str=game.time_control_str,
            move_count=game.move_count,
            termination=game.termination,
            platform=game.platform,
            platform_url=game.platform_url,
            white_username=game.white_username,
            black_username=game.black_username,
            user_color=game.user_color,
        )
        for flaw, game, pos_at, pos_before in rows
    ]
    return items, matched_count


async def fetch_page_game_flaws(
    session: AsyncSession,
    user_id: int,
    game_ids: Sequence[int],
) -> dict[int, list[GameFlaw]]:
    """Batch-load all game_flaws rows for a page of games, grouped by game_id.

    Returns a dict mapping game_id -> list[GameFlaw] (may be empty for an
    analyzed-but-flawless game or a game with no game_flaws rows yet).
    User-scoped via GameFlaw.user_id == user_id (T-108-08 mitigation).

    Single query for the whole page (no N+1 per-game call). The caller groups
    by game_id in Python, reconstructing chips and M+B counts from the rows.
    """
    if not game_ids:
        return {}
    # D-04: player-only gate — after Phase 113 game_flaws contains both sides;
    # fetch_page_game_flaws feeds chip/M+B building on Games-tab cards so it must
    # return only player rows. Game JOIN is added here to bring user_color into
    # scope for player_only_gate (R3 gate).
    stmt = (
        select(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.user_id == user_id,
            GameFlaw.game_id.in_(game_ids),
            player_only_gate(GameFlaw.ply, Game.user_color),  # D-04 player gate
        )
    )
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, list[GameFlaw]] = {gid: [] for gid in game_ids}
    for row in rows:
        result[row.game_id].append(row)
    return result


async def fetch_page_eval_positions(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids: Sequence[int],
) -> dict[int, list[GamePosition]]:
    """Batch-load GamePosition rows for analyzed games on a page, grouped by game_id.

    Only called for games in analyzed_set (unanalyzed games get no positions).
    Selects full ORM objects so _run_all_moves_pass and _build_tags can consume
    them unchanged. Ordered by game_id, ply ASC for sequential grouping.
    User-scoped via GamePosition.user_id (IDOR mitigation — T-109-01, same
    pattern as fetch_page_game_flaws / T-108-08).
    """
    if not analyzed_game_ids:
        return {}
    stmt = (
        select(GamePosition)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.game_id.in_(analyzed_game_ids),
        )
        .order_by(GamePosition.game_id, GamePosition.ply)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, list[GamePosition]] = {gid: [] for gid in analyzed_game_ids}
    for row in rows:
        result[row.game_id].append(row)
    return result


async def fetch_page_analyzed_set(
    session: AsyncSession,
    user_id: int,
    game_ids: Sequence[int],
) -> frozenset[int]:
    """Return the subset of game_ids that pass the >=90% eval-coverage gate.

    Used in _build_card to determine analysis_state for each page game without
    a per-game position load. Replaces the per-game count_game_severities
    analysis_state check after D-02 migration.
    """
    if not game_ids:
        return frozenset()
    analyzed_subq = _analyzed_game_ids_subquery(user_id)
    stmt = select(analyzed_subq.c.game_id).where(analyzed_subq.c.game_id.in_(game_ids))
    rows = (await session.execute(stmt)).scalars().all()
    return frozenset(rows)


async def fetch_stats_aggregates(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids_subq: Subquery,
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
    color: str | None,
) -> tuple[int, int, int, int, int, int, int, int, int, int, int, int]:
    """Single game_flaws JOIN games scan producing M+B stats panel aggregates.

    Returns a 12-tuple:
      (mistake_count, blunder_count,
       tempo_low_clock, tempo_hasty, tempo_unrushed,
       is_reversed, is_miss, is_lucky, is_squandered,
       phase_opening, phase_middlegame, phase_endgame)

    All counts are over the analyzed+filtered game set.
    User-scoped (T-108-08). The analyzed_game_ids_subq is the eval-coverage
    gate (Pitfall 6 — D-03: analyzed_n stays on the coverage subquery).
    """
    base_filtered_subq = _filtered_games_base(
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
    ).subquery("filtered")
    filtered_analyzed_subq = (
        select(base_filtered_subq.c.id)
        .where(base_filtered_subq.c.id.in_(select(analyzed_game_ids_subq.c.game_id)))
        .subquery("filtered_analyzed")
    )

    # D-04: Game JOIN required so Game.user_color is in scope for player_only_gate.
    # After Phase 113 game_flaws contains both sides; this gate ensures the stats
    # panel aggregates count only player flaws (no opponent inflation — R4).
    stmt = (
        select(
            func.count().filter(GameFlaw.severity == _SEVERITY_INT["mistake"]),
            func.count().filter(GameFlaw.severity == _SEVERITY_INT["blunder"]),
            func.count().filter(GameFlaw.tempo == _TEMPO_INT["low-clock"]),
            func.count().filter(GameFlaw.tempo == _TEMPO_INT["hasty"]),
            func.count().filter(GameFlaw.tempo == _TEMPO_INT["unrushed"]),
            func.count().filter(GameFlaw.is_reversed.is_(True)),
            func.count().filter(GameFlaw.is_miss.is_(True)),
            func.count().filter(GameFlaw.is_lucky.is_(True)),
            func.count().filter(GameFlaw.is_squandered.is_(True)),
            func.count().filter(GameFlaw.phase == _PHASE_INT["opening"]),
            func.count().filter(GameFlaw.phase == _PHASE_INT["middlegame"]),
            func.count().filter(GameFlaw.phase == _PHASE_INT["endgame"]),
        )
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.user_id == user_id,
            GameFlaw.game_id.in_(select(filtered_analyzed_subq.c.id)),
            player_only_gate(GameFlaw.ply, Game.user_color),  # D-04 player gate (R4)
        )
    )
    row = (await session.execute(stmt)).one()
    return (
        row[0],  # mistake_count
        row[1],  # blunder_count
        row[2],  # tempo_low_clock
        row[3],  # tempo_hasty
        row[4],  # tempo_unrushed
        row[5],  # is_reversed
        row[6],  # is_miss
        row[7],  # is_lucky
        row[8],  # is_squandered
        row[9],  # phase_opening
        row[10],  # phase_middlegame
        row[11],  # phase_endgame
    )


async def fetch_stats_trend(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids_subq: Subquery,
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
    color: str | None,
) -> list[tuple[datetime.datetime | None, int]]:
    """Per-game M+B flaw count for trend computation, ordered by played_at ASC.

    Returns list of (played_at, mb_count) tuples — one entry per analyzed+filtered
    game, including games with zero M+B flaws (LEFT JOIN semantics via subquery).
    Ordered oldest-first for rolling-window accumulation in _compute_trend.

    The trend is computed over the same analyzed+filtered set as fetch_stats_aggregates.
    """
    base_filtered_subq = _filtered_games_base(
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
    ).subquery("filtered_t")
    filtered_analyzed_game_ids = (
        select(base_filtered_subq.c.id)
        .where(base_filtered_subq.c.id.in_(select(analyzed_game_ids_subq.c.game_id)))
        .subquery("fa_ids")
    )

    # Games in the analyzed+filtered set (may have 0 game_flaws rows)
    games_subq = (
        select(Game.id, Game.played_at)
        .where(
            Game.user_id == user_id,
            Game.id.in_(select(filtered_analyzed_game_ids.c.id)),
        )
        .subquery("analyzed_games")
    )

    # Flaw counts per game (0 for games with no flaws in game_flaws)
    # D-04: Game JOIN required so Game.user_color is in scope for player_only_gate.
    # After Phase 113 game_flaws contains both sides; this gate ensures the per-game
    # M+B trend counts only player flaws (no opponent inflation — R5).
    flaw_counts_subq = (
        select(
            GameFlaw.game_id,
            func.count().label("mb_count"),
        )
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.user_id == user_id,
            GameFlaw.game_id.in_(select(filtered_analyzed_game_ids.c.id)),
            player_only_gate(GameFlaw.ply, Game.user_color),  # D-04 player gate (R5)
        )
        .group_by(GameFlaw.game_id)
        .subquery("flaw_counts")
    )

    stmt = (
        select(
            games_subq.c.played_at,
            func.coalesce(flaw_counts_subq.c.mb_count, 0).label("mb_count"),
        )
        .outerjoin(flaw_counts_subq, flaw_counts_subq.c.game_id == games_subq.c.id)
        .order_by(games_subq.c.played_at.asc().nulls_last())
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]


async def fetch_total_user_moves(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids_subq: Subquery,
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
    color: str | None,
) -> int:
    """Count the user's plies across all analyzed+filtered games (per-100 rate denominator).

    A ply N is the user's when mover parity matches game.user_color:
    - White moves at even plies (N % 2 == 0)
    - Black moves at odd plies  (N % 2 != 0)
    Ply 0 (initial position, no move) is excluded.

    This mirrors _count_user_moves() semantics from library_service.py, computed
    in one SQL aggregate over game_positions JOIN games (no per-game kernel loop).
    """
    base_filtered_subq = _filtered_games_base(
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
    ).subquery("filtered_u")
    filtered_analyzed_ids = (
        select(base_filtered_subq.c.id)
        .where(base_filtered_subq.c.id.in_(select(analyzed_game_ids_subq.c.game_id)))
        .subquery("fa_ids2")
    )

    # Count positions where ply >= 1 AND mover matches game.user_color.
    # Even ply → white mover; odd ply → black mover (matches kernel _run_all_moves_pass).
    # SQLAlchemy 2.x case(): positional *whens as individual (condition, value) tuples.
    user_ply = case(
        ((GamePosition.ply % 2 == 0) & (Game.user_color == "white"), 1),
        ((GamePosition.ply % 2 != 0) & (Game.user_color == "black"), 1),
        else_=0,
    )

    stmt = (
        select(func.sum(user_ply))
        .select_from(GamePosition)
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.game_id.in_(select(filtered_analyzed_ids.c.id)),
            GamePosition.ply >= 1,
        )
    )
    result = (await session.execute(stmt)).scalar_one_or_none()
    return int(result) if result is not None else 0


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
    flaw_tags: Sequence[str] | None = None,
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> tuple[list[Game], int]:
    """Return paginated user Game objects, optionally flaw-severity/tag filtered.

    Mirrors endgame_repository.query_endgame_games' paginated-archive shape, but
    drops the endgame-span subquery — the base select is simply the user's games,
    with the flaw EXISTS applied via apply_game_filters when severities and/or
    tags are supplied (LIBG-08, SEED-038). flaw_tags restricts to games with a
    single flaw satisfying ALL selected tag families (OR within family, AND
    across families). When both flaw_severity and flaw_tags are None/empty the
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
        flaw_tags=flaw_tags,
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
