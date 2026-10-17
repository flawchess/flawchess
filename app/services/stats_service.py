"""Stats service: aggregation logic for rating history, global stats and most-played openings."""

import datetime
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import chess
import sentry_sdk
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position_bookmark import PositionBookmark
from app.repositories.position_bookmark_repository import get_bookmarks
from app.repositories.stats_repository import (
    OpeningPhaseEntryMetrics,
    PositionWDL,
    query_opening_phase_entry_metrics_batch,
    query_position_wdl_batch,
    query_rating_history,
    query_results_by_color,
    query_results_by_time_control,
    query_top_openings_sql_wdl,
)
from app.schemas.stats import (
    BookmarkPhaseEntryItem,
    BookmarkPhaseEntryQuery,
    BookmarkPhaseEntryResponse,
    GlobalStatsResponse,
    MostPlayedOpeningsResponse,
    OpeningWDL,
    RatingDataPoint,
    RatingHistoryResponse,
    WDLByCategory,
)
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
)
from app.services.opening_eval import finalize_opening_eval
from app.services.repertoire_recency import is_current, resolve_current_cutoffs
from app.services.score_confidence import score_verdict_fields
from app.services.zobrist import compute_hashes


# Minimum number of games required for an opening to appear in top openings.
MIN_GAMES_FOR_OPENING = 1

# Most-played pipeline sizing (D-05). The top query fetches MOST_PLAYED_FETCH_LIMIT
# candidates per colour BEFORE dedupe and the current/past split; the response keeps up to
# MOST_PLAYED_CURRENT_LIMIT current rows (main table) and MOST_PLAYED_PAST_LIMIT past rows
# (collapsed "Played before" group). Fetch 60, not the ~30 D-05 first guessed: dev
# evidence shows the owner's 10th current White row is rank 33 in the all-time ranking.
# Heavier repertoire shifts are covered by the cutoff-restricted second fetch.
MOST_PLAYED_FETCH_LIMIT = 60
MOST_PLAYED_CURRENT_LIMIT = 10
MOST_PLAYED_PAST_LIMIT = 10

# Minimum ply count for a named opening position to be considered: ply 3 keeps
# named gambits/systems like Blackmar-Diemer (1.d4 d5 2.e4) but cuts trivial
# trunks like "Queen's Pawn Game" (1.d4) and "King's Pawn Game" (1.e4) which
# would otherwise dominate position-based ranking — every d4/e4 game would
# count toward them.
MIN_PLY_WHITE = 3
MIN_PLY_BLACK = 3

# Ordered time control buckets for consistent output ordering.
_TIME_CONTROL_ORDER = ["bullet", "blitz", "rapid", "classical"]

# Color ordering for consistent output.
_COLOR_ORDER = ["white", "black"]


class FilterParams(TypedDict):
    """Typed filter parameters for position WDL batch queries.

    Internal data structure, so a TypedDict rather than a Pydantic model.
    Matches keyword parameters of query_position_wdl_batch in stats_repository.py.
    """

    time_control: list[str] | None
    platform: list[str] | None
    rated: bool | None
    opponent_type: str
    from_date: datetime.date | None
    to_date: datetime.date | None
    opponent_gap_min: int | None
    opponent_gap_max: int | None


async def get_rating_history(
    session: AsyncSession,
    user_id: int,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    platform: str | None = None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> RatingHistoryResponse:
    """Return per-platform per-game rating data points.

    Queries both platforms in sequence and maps rows to RatingDataPoint lists.

    When platform is "chess.com", only chess.com data is queried; lichess is empty.
    When platform is "lichess", only lichess data is queried; chess.com is empty.
    When platform is None, both platforms are queried.
    """
    if platform == "chess.com":
        chesscom_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="chess.com",
            from_date=from_date,
            to_date=to_date,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
        lichess_rows: list = []
    elif platform == "lichess":
        chesscom_rows = []
        lichess_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="lichess",
            from_date=from_date,
            to_date=to_date,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
    else:
        chesscom_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="chess.com",
            from_date=from_date,
            to_date=to_date,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
        lichess_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="lichess",
            from_date=from_date,
            to_date=to_date,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )

    def rows_to_points(rows: list) -> list[RatingDataPoint]:
        points = []
        for date_val, rating, tc_bucket, game_count in rows:
            # date_val is a date object from CAST(... AS DATE) — use isoformat directly
            date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
            points.append(
                RatingDataPoint(
                    date=date_str,
                    rating=rating,
                    time_control_bucket=tc_bucket or "unknown",
                    game_count=game_count,
                )
            )
        return points

    return RatingHistoryResponse(
        chess_com=rows_to_points(chesscom_rows),
        lichess=rows_to_points(lichess_rows),
    )


def _rows_to_wdl_categories(
    rows: list[Row[Any]],
    label_fn,
    label_order: list[str],
) -> list[WDLByCategory]:
    """Convert SQL-aggregated (label_key, total, wins, draws, losses) rows to WDLByCategory list.

    Rows are already aggregated by the database — no Python-side counting needed.
    """
    row_map = {row[0]: row for row in rows}

    categories = []
    for key in label_order:
        if key not in row_map:
            continue
        _, total, wins, draws, losses = row_map[key]
        if total > 0:
            win_pct = round(wins / total * 100, 1)
            draw_pct = round(draws / total * 100, 1)
            loss_pct = round(losses / total * 100, 1)
        else:
            win_pct = draw_pct = loss_pct = 0.0

        categories.append(
            WDLByCategory(
                label=label_fn(key),
                wins=wins,
                draws=draws,
                losses=losses,
                total=total,
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
            )
        )

    return categories


async def get_global_stats(
    session: AsyncSession,
    user_id: int,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    platform: str | None = None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Both queries return SQL-aggregated (label, total, wins, draws, losses) rows.
    When color is set ("white" or "black"), only games played as that color are included.
    """
    tc_rows = await query_results_by_time_control(
        session,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )
    color_rows = await query_results_by_color(
        session,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )

    by_time_control = _rows_to_wdl_categories(
        rows=tc_rows,
        label_fn=lambda key: key.title(),
        label_order=_TIME_CONTROL_ORDER,
    )

    by_color = _rows_to_wdl_categories(
        rows=color_rows,
        label_fn=lambda key: key.title(),
        label_order=_COLOR_ORDER,
    )

    return GlobalStatsResponse(
        by_time_control=by_time_control,
        by_color=by_color,
    )


@dataclass(slots=True)
class _MostPlayedCandidate:
    """One most-played row while it moves through dedupe, twin drop and the split."""

    eco: str
    name: str
    display_name: str
    pgn: str
    fen: str
    full_hash: int | None
    ply_count: int
    total: int
    wins: int
    draws: int
    losses: int
    last_played_at: datetime.datetime | None
    game_id_sum: int
    is_current: bool


def _build_candidates(
    rows: Sequence[Any],
    position_wdl: dict[int, PositionWDL],
    cutoff: datetime.datetime | None,
) -> list[_MostPlayedCandidate]:
    """Turn top-openings rows into candidates, preferring position-based WDL.

    Rows are read by attribute name (never by index): the top query grew a trailing
    ply_count column, and positional destructuring is what breaks when a column is
    added. Rows without a position bucket keep their opening-name WDL and read as
    current (last_played_at is None), exactly like the pre-242 behaviour.
    """
    candidates: list[_MostPlayedCandidate] = []
    for row in rows:
        full_hash: int | None = row.full_hash
        pos = position_wdl.get(full_hash) if full_hash is not None else None
        total, wins, draws, losses = row.total, row.wins, row.draws, row.losses
        if pos is not None:
            total, wins, draws, losses = pos.total, pos.wins, pos.draws, pos.losses
        last_played_at = pos.last_played_at if pos is not None else None
        candidates.append(
            _MostPlayedCandidate(
                eco=row.eco,
                name=row.name,
                display_name=row.display_name,
                pgn=row.pgn,
                fen=row.fen,
                full_hash=full_hash,
                ply_count=row.ply_count,
                total=total,
                wins=wins,
                draws=draws,
                losses=losses,
                last_played_at=last_played_at,
                game_id_sum=pos.game_id_sum if pos is not None else 0,
                is_current=is_current(last_played_at, cutoff),
            )
        )
    return candidates


def _game_set_fingerprint(c: _MostPlayedCandidate) -> tuple[Any, ...] | None:
    """Identity of a candidate's game set, or None when it cannot be fingerprinted.

    Needs a position bucket (full_hash, total > 0 and a real id sum; game ids are
    positive so 0 means "no bucket"). Equal fingerprints mean the same games: positions
    along one line are nested, so equal count plus equal id sum is effectively exact.
    """
    if c.full_hash is None or c.total <= 0 or c.game_id_sum == 0:
        return None
    return (c.total, c.wins, c.draws, c.losses, c.game_id_sum, c.last_played_at)


def _dedupe_identical_sets(candidates: list[_MostPlayedCandidate]) -> list[_MostPlayedCandidate]:
    """Collapse rows with an identical game set to the deepest line (D-06).

    Ties on depth keep the alphabetically first name. Candidates that cannot be
    fingerprinted are never collapsed. Input order is preserved.
    """
    best: dict[tuple[Any, ...], _MostPlayedCandidate] = {}
    for c in candidates:
        key = _game_set_fingerprint(c)
        if key is None:
            continue
        kept = best.get(key)
        if kept is None or (-c.ply_count, c.name) < (-kept.ply_count, kept.name):
            best[key] = c
    result: list[_MostPlayedCandidate] = []
    for c in candidates:
        key = _game_set_fingerprint(c)
        if key is None or best[key] is c:
            result.append(c)
    return result


def _drop_bookmark_twins(
    candidates: list[_MostPlayedCandidate], bookmark_hashes: set[int]
) -> list[_MostPlayedCandidate]:
    """Drop rows that duplicate a same-colour bookmark (bookmark wins, D-06).

    A row is a twin when its position equals a bookmark's position, or when it has the
    identical game set as such a row (a deeper line the bookmark's own position nests
    into). The second rule is what keeps a bookmark on a shallow position A from being
    shown next to a deeper "Most played" row B with the same games.
    """
    twin_prints = {
        fp
        for c in candidates
        if c.full_hash in bookmark_hashes and (fp := _game_set_fingerprint(c)) is not None
    }
    return [
        c
        for c in candidates
        if c.full_hash not in bookmark_hashes and _game_set_fingerprint(c) not in twin_prints
    ]


def _prepare_candidates(
    rows: Sequence[Any],
    position_wdl: dict[int, PositionWDL],
    cutoff: datetime.datetime | None,
    bookmark_hashes: set[int],
) -> list[_MostPlayedCandidate]:
    """Pure pipeline head: build -> drop bookmark twins -> dedupe identical sets.

    Twins are dropped BEFORE the identical-set dedupe. The dedupe keeps the deeper
    line and removes the shallower one, so with the order reversed a bookmark on the
    shallow position A had its candidate removed first, the twin drop then found no
    hash match for the surviving deeper row B, and A (pinned) and B (most played)
    were both shown with identical games (WR-01).
    """
    candidates = _build_candidates(rows, position_wdl, cutoff)
    candidates = _drop_bookmark_twins(candidates, bookmark_hashes)
    return _dedupe_identical_sets(candidates)


def _split_and_cap(candidates: list[_MostPlayedCandidate]) -> list[_MostPlayedCandidate]:
    """Current rows first, then past rows; each group by games desc, capped (D-05).

    Current-first ordering keeps consumers that slice the list (SuggestionsModal)
    sensible. The module limits are read at call time, never bound as defaults.
    """
    current = sorted((c for c in candidates if c.is_current), key=lambda c: -c.total)
    past = sorted((c for c in candidates if not c.is_current), key=lambda c: -c.total)
    return current[:MOST_PLAYED_CURRENT_LIMIT] + past[:MOST_PLAYED_PAST_LIMIT]


def _needs_recent_fallback(
    candidates: list[_MostPlayedCandidate], cutoff: datetime.datetime | None
) -> bool:
    """True when a cutoff exists and fewer current rows survived than the cap (D-05 clarified)."""
    if cutoff is None:
        return False
    return sum(1 for c in candidates if c.is_current) < MOST_PLAYED_CURRENT_LIMIT


def _recent_from_date(from_date: datetime.date | None, cutoff: datetime.datetime) -> datetime.date:
    """Later of the filter's from_date and the cutoff day.

    from_date is an inclusive date, so the restricted query also sees the cutoff day's
    earlier games; harmless because rows are classified by their real last_played_at.
    """
    cutoff_day = cutoff.date()
    if from_date is None:
        return cutoff_day
    return max(from_date, cutoff_day)


def _bookmark_full_hashes_by_color(
    bookmarks: Sequence[PositionBookmark],
) -> dict[Literal["white", "black"], set[int]]:
    """Replayed full hash of every coloured bookmark, grouped by bookmark colour.

    Replays the stored SAN list like position_bookmark_repository.update_match_side:
    legacy bookmarks may carry board-only FENs whose hashes would be wrong. Independent
    of match_side. Colour-less bookmarks are skipped, as are bookmarks whose moves do
    not replay (reported to Sentry with the bookmark id in context, never in the message).
    """
    hashes: dict[Literal["white", "black"], set[int]] = {"white": set(), "black": set()}
    for bookmark in bookmarks:
        color = bookmark.color
        if color != "white" and color != "black":
            continue
        board = chess.Board()
        try:
            for san in json.loads(bookmark.moves):
                board.push_san(san)
        except (ValueError, TypeError) as exc:
            sentry_sdk.set_tag("source", "stats")
            sentry_sdk.set_context("bookmark", {"bookmark_id": bookmark.id})
            sentry_sdk.capture_exception(exc)
            continue
        hashes[color].add(compute_hashes(board)[2])
    return hashes


async def _fetch_position_wdl(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    hashes: list[int],
    filter_params: FilterParams,
) -> dict[int, PositionWDL]:
    """Position-based WDL for the hashes under the unrestricted active filters."""
    return await query_position_wdl_batch(
        session,
        user_id,
        hashes,
        color=color,
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        from_date=filter_params["from_date"],
        to_date=filter_params["to_date"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )


async def _fetch_top_rows(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    min_ply: int,
    filter_params: FilterParams,
) -> list[Row[Any]]:
    """Top MOST_PLAYED_FETCH_LIMIT openings for the colour under the given filters."""
    return await query_top_openings_sql_wdl(
        session,
        user_id=user_id,
        color=color,
        min_games=MIN_GAMES_FOR_OPENING,
        limit=MOST_PLAYED_FETCH_LIMIT,
        min_ply=min_ply,
        from_date=filter_params["from_date"],
        to_date=filter_params["to_date"],
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )


async def _recent_nominee_rows(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    *,
    filter_params: FilterParams,
    min_ply: int,
    cutoff: datetime.datetime,
    known_hashes: set[int],
) -> list[Row[Any]]:
    """Top rows over games on or after the cutoff day, minus hashes already fetched.

    These rows only NOMINATE openings: their post-cutoff counts are never displayed.
    The caller re-counts the nominees under the unrestricted filters.
    """
    recent_params = FilterParams(
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        from_date=_recent_from_date(filter_params["from_date"], cutoff),
        to_date=filter_params["to_date"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )
    rows = await _fetch_top_rows(session, user_id, color, min_ply, recent_params)
    return [r for r in rows if r.full_hash is not None and r.full_hash not in known_hashes]


async def _merge_recent_nominees(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    *,
    filter_params: FilterParams,
    min_ply: int,
    cutoff: datetime.datetime,
    rows: list[Row[Any]],
    position_wdl: dict[int, PositionWDL],
) -> list[Row[Any]]:
    """Rows plus cutoff-restricted nominees; position_wdl gains the nominees' full counts.

    Returns ``rows`` itself (same object) when nothing was added: either the restricted
    query would repeat the first one (the filter's own from_date is already on or after
    the cutoff day) or it nominated no new opening.
    """
    if _recent_from_date(filter_params["from_date"], cutoff) == filter_params["from_date"]:
        return rows
    known_hashes = {r.full_hash for r in rows if r.full_hash is not None}
    nominees = await _recent_nominee_rows(
        session,
        user_id,
        color,
        filter_params=filter_params,
        min_ply=min_ply,
        cutoff=cutoff,
        known_hashes=known_hashes,
    )
    if not nominees:
        return rows
    nominee_wdl = await _fetch_position_wdl(
        session, user_id, color, [r.full_hash for r in nominees], filter_params
    )
    position_wdl.update(nominee_wdl)
    # Nominees whose games are a subset of the unrestricted ones always have a bucket;
    # dropping the rest guarantees post-cutoff counts never reach a displayed row.
    return rows + [r for r in nominees if r.full_hash in nominee_wdl]


def _candidate_to_opening_wdl(
    c: _MostPlayedCandidate,
    pe: OpeningPhaseEntryMetrics | None,
    color: Literal["white", "black"],
) -> OpeningWDL:
    """Build the response row for one surviving candidate."""
    if c.total > 0:
        win_pct = round(c.wins / c.total * 100, 1)
        draw_pct = round(c.draws / c.total * 100, 1)
        loss_pct = round(c.losses / c.total * 100, 1)
    else:
        win_pct = draw_pct = loss_pct = 0.0
    # The eval z-test runs against the colour baseline (+25 cp White / -25 cp Black,
    # D-13); avg_eval_pawns stays the raw mean.
    eval_fields = finalize_opening_eval(pe, color)
    score_fields = score_verdict_fields(c.wins, c.draws, c.losses)
    return OpeningWDL(
        opening_eco=c.eco,
        opening_name=c.name,
        display_name=c.display_name,
        label=f"{c.name} ({c.eco})",
        pgn=c.pgn,
        fen=c.fen,
        full_hash=str(c.full_hash) if c.full_hash is not None else "",
        wins=c.wins,
        draws=c.draws,
        losses=c.losses,
        total=c.total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
        score=score_fields["score"],
        score_confidence=score_fields["score_confidence"],
        score_p_value=score_fields["score_p_value"],
        score_ci99_low=score_fields["score_ci99_low"],
        score_ci99_high=score_fields["score_ci99_high"],
        avg_eval_pawns=eval_fields["avg_eval_pawns"],
        eval_ci_low_pawns=eval_fields["eval_ci_low_pawns"],
        eval_ci_high_pawns=eval_fields["eval_ci_high_pawns"],
        eval_ci99_low_pawns=eval_fields["eval_ci99_low_pawns"],
        eval_ci99_high_pawns=eval_fields["eval_ci99_high_pawns"],
        eval_n=eval_fields["eval_n"],
        eval_p_value=eval_fields["eval_p_value"],
        eval_confidence=eval_fields["eval_confidence"],
        # MAX(played_at); drives "Last played" and the current/past split.
        last_played_at=c.last_played_at,
        is_current=c.is_current,
    )


async def _most_played_for_color(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    *,
    filter_params: FilterParams,
    min_ply: int,
    cutoff: datetime.datetime | None,
    bookmark_hashes: set[int],
) -> list[OpeningWDL]:
    """Most-played rows for one colour: up to 10 current, then up to 10 past (D-04..D-06).

    Pipeline: top MOST_PLAYED_FETCH_LIMIT rows -> position WDL -> dedupe identical game
    sets -> drop bookmark twins -> (cutoff-restricted second fetch when current rows run
    short, D-05 clarified) -> split current/past and cap -> eval metrics for the
    survivors only (the expensive batch never sees the full candidate list).
    All awaits are sequential on the one AsyncSession.
    """
    rows = await _fetch_top_rows(session, user_id, color, min_ply, filter_params)
    # Batch-query position-based WDL: games passing through each position, which is
    # typically higher than the opening-name count. Matches "Results by Opening" counts.
    position_wdl = await _fetch_position_wdl(
        session,
        user_id,
        color,
        [r.full_hash for r in rows if r.full_hash is not None],
        filter_params,
    )
    candidates = _prepare_candidates(rows, position_wdl, cutoff, bookmark_hashes)

    if cutoff is not None and _needs_recent_fallback(candidates, cutoff):
        merged_rows = await _merge_recent_nominees(
            session,
            user_id,
            color,
            filter_params=filter_params,
            min_ply=min_ply,
            cutoff=cutoff,
            rows=rows,
            position_wdl=position_wdl,
        )
        if merged_rows is not rows:
            candidates = _prepare_candidates(merged_rows, position_wdl, cutoff, bookmark_hashes)

    survivors = _split_and_cap(candidates)
    survivor_hashes = [c.full_hash for c in survivors if c.full_hash is not None]
    phase_entry_metrics = await query_opening_phase_entry_metrics_batch(
        session,
        user_id,
        survivor_hashes,
        color=color,
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        from_date=filter_params["from_date"],
        to_date=filter_params["to_date"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )
    return [
        _candidate_to_opening_wdl(
            c, phase_entry_metrics.get(c.full_hash) if c.full_hash is not None else None, color
        )
        for c in survivors
    ]


async def get_most_played_openings(
    session: AsyncSession,
    user_id: int,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    *,
    now_utc: datetime.datetime,
) -> MostPlayedOpeningsResponse:
    """Return up to 10 current and 10 past most-played openings per colour.

    Opening selection uses the games table (by opening_eco/name), but the displayed
    game count comes from game_positions (games passing through the position). This
    matches the count shown in "Results by Opening".

    ``now_utc`` (from the dev_now_utc dependency, never the wall clock) anchors the
    60-day floor of the per-colour current-repertoire cutoff (D-03); each row carries
    ``is_current`` and the response returns both cutoffs. Rows are deduped (identical
    game sets keep the deeper line; a row duplicating a same-colour bookmark position is
    dropped, bookmark wins) before the split and the cap (D-05, D-06). See
    _most_played_for_color for the pipeline.

    Also populates the MG-entry eval fields via query_opening_phase_entry_metrics_batch.
    Sequential awaits within the same session (CLAUDE.md: AsyncSession not safe for
    concurrent use).
    """
    cutoffs = await resolve_current_cutoffs(
        session,
        user_id,
        ["white", "black"],
        now_utc=now_utc,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # FilterParams TypedDict. Passed explicitly (not via **) for ty compatibility.
    filter_params: FilterParams = FilterParams(
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # All of the user's coloured bookmarks, independent of the sidebar filters: the
    # bookmark section owns those positions, so the table never repeats them (D-06/D-16).
    bookmark_hashes = _bookmark_full_hashes_by_color(await get_bookmarks(session, user_id))

    white = await _most_played_for_color(
        session,
        user_id,
        "white",
        filter_params=filter_params,
        min_ply=MIN_PLY_WHITE,
        cutoff=cutoffs["white"],
        bookmark_hashes=bookmark_hashes["white"],
    )
    black = await _most_played_for_color(
        session,
        user_id,
        "black",
        filter_params=filter_params,
        min_ply=MIN_PLY_BLACK,
        cutoff=cutoffs["black"],
        bookmark_hashes=bookmark_hashes["black"],
    )
    return MostPlayedOpeningsResponse(
        white=white,
        black=black,
        # Per-color engine-asymmetry baselines (in pawns): the eval bar centre and the
        # H0 of the eval z-test on Openings surfaces (D-13), already applied above.
        eval_baseline_pawns_white=EVAL_BASELINE_PAWNS_WHITE,
        eval_baseline_pawns_black=EVAL_BASELINE_PAWNS_BLACK,
        current_cutoff_white=cutoffs["white"],
        current_cutoff_black=cutoffs["black"],
    )


def _bookmark_phase_entry_item(
    target_hash: str,
    pe: OpeningPhaseEntryMetrics | None,
    color: Literal["white", "black"] | None,
) -> BookmarkPhaseEntryItem:
    """Compute the MG-entry eval display fields for a single hash.

    Uses the same finalize_opening_eval as the most-played rows, so the bookmark
    endpoint reports identical numbers without depending on the OpeningWDL row shape.

    The eval z-test runs against the bookmark colour's baseline (+25 cp White, -25 cp
    Black; None counts as White), not 0 cp (D-13).
    """
    eval_fields = finalize_opening_eval(pe, color)
    return BookmarkPhaseEntryItem(
        target_hash=target_hash,
        avg_eval_pawns=eval_fields["avg_eval_pawns"],
        eval_ci_low_pawns=eval_fields["eval_ci_low_pawns"],
        eval_ci_high_pawns=eval_fields["eval_ci_high_pawns"],
        eval_ci99_low_pawns=eval_fields["eval_ci99_low_pawns"],
        eval_ci99_high_pawns=eval_fields["eval_ci99_high_pawns"],
        eval_n=eval_fields["eval_n"],
        eval_p_value=eval_fields["eval_p_value"],
        eval_confidence=eval_fields["eval_confidence"],
    )


async def get_bookmark_phase_entry_metrics(
    session: AsyncSession,
    user_id: int,
    bookmarks: list[BookmarkPhaseEntryQuery],
    *,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> BookmarkPhaseEntryResponse:
    """MG-entry eval fields for arbitrary bookmark target_hashes.

    Groups bookmarks by (match_side, color) — each group is one batched DB call to
    query_opening_phase_entry_metrics_batch with the matching hash_column. Sequential
    awaits within the same session (CLAUDE.md: AsyncSession not safe for concurrent use).
    """
    if not bookmarks:
        return BookmarkPhaseEntryResponse(items=[])

    # Group by (match_side, color). Bookmarks with the same group share one DB call.
    grouped: dict[
        tuple[Literal["white", "black", "full"], Literal["white", "black"] | None], list[int]
    ] = {}
    for b in bookmarks:
        key = (b.match_side, b.color)
        grouped.setdefault(key, []).append(int(b.target_hash))

    # Result map: target_hash (signed int) -> OpeningPhaseEntryMetrics
    metrics_by_hash: dict[int, OpeningPhaseEntryMetrics] = {}
    for (match_side, color), hashes in grouped.items():
        # Sequential await — same session.
        group_metrics = await query_opening_phase_entry_metrics_batch(
            session,
            user_id,
            hashes,
            color=color,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
            hash_column=match_side,
        )
        metrics_by_hash.update(group_metrics)

    items = [
        _bookmark_phase_entry_item(b.target_hash, metrics_by_hash.get(int(b.target_hash)), b.color)
        for b in bookmarks
    ]
    return BookmarkPhaseEntryResponse(items=items)
