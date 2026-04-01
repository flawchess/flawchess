"""Analysis service: W/D/L derivation, stats computation, and orchestration."""

import datetime
import io
from typing import Literal

import sentry_sdk

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.analysis_repository import (
    HASH_COLUMN_MAP,
    query_all_results,
    query_matching_games,
    query_next_moves,
    query_time_series,
    query_transposition_counts,
)
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    BookmarkTimeSeries,
    GameRecord,
    NextMoveEntry,
    NextMovesRequest,
    NextMovesResponse,
    TimeSeriesPoint,
    TimeSeriesRequest,
    TimeSeriesResponse,
    WDLStats,
)

# Rolling window size for win-rate time series computation.
ROLLING_WINDOW_SIZE = 50

# Maps recency filter strings to timedelta offsets.
RECENCY_DELTAS: dict[str, datetime.timedelta] = {
    "week": datetime.timedelta(days=7),
    "month": datetime.timedelta(days=30),
    "3months": datetime.timedelta(days=90),
    "6months": datetime.timedelta(days=180),
    "year": datetime.timedelta(days=365),
}


def derive_user_result(
    result: str, user_color: str
) -> Literal["win", "draw", "loss"]:
    """Derive win/draw/loss from the raw PGN result and the user's color.

    Args:
        result: One of "1-0", "0-1", "1/2-1/2".
        user_color: One of "white", "black".

    Returns:
        "draw" for draws, "win" when the user's side won, "loss" otherwise.
    """
    if result == "1/2-1/2":
        return "draw"
    if (result == "1-0" and user_color == "white") or (
        result == "0-1" and user_color == "black"
    ):
        return "win"
    return "loss"


def recency_cutoff(recency: str | None) -> datetime.datetime | None:
    """Return a UTC datetime cutoff for the given recency filter, or None.

    Returns None for None or "all" (no recency restriction).
    """
    if recency is None or recency == "all":
        return None
    delta = RECENCY_DELTAS[recency]
    return datetime.datetime.now(tz=datetime.timezone.utc) - delta


async def analyze(
    session: AsyncSession,
    user_id: int,
    request: AnalysisRequest,
) -> AnalysisResponse:
    """Orchestrate a position analysis query and return W/D/L stats + games.

    Steps:
    1. Resolve hash column from match_side.
    2. Compute optional recency cutoff datetime.
    3. Fetch all (result, user_color) rows for aggregate stats.
    4. Compute W/D/L counts and percentages.
    5. Fetch paginated Game objects.
    6. Build GameRecord list and return AnalysisResponse.
    """
    # When target_hash is None, skip position filtering entirely
    hash_column = HASH_COLUMN_MAP[request.match_side] if request.target_hash is not None else None
    cutoff = recency_cutoff(request.recency)

    # --- Stats (full result set, no pagination) ---
    all_rows = await query_all_results(
        session=session,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=request.target_hash,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
    )

    wins = draws = losses = 0
    for result, user_color in all_rows:
        outcome = derive_user_result(result, user_color)
        if outcome == "win":
            wins += 1
        elif outcome == "draw":
            draws += 1
        else:
            losses += 1

    total = wins + draws + losses
    if total > 0:
        win_pct = round(wins / total * 100, 1)
        draw_pct = round(draws / total * 100, 1)
        loss_pct = round(losses / total * 100, 1)
    else:
        win_pct = draw_pct = loss_pct = 0.0

    stats = WDLStats(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
    )

    # --- Paginated game list ---
    games, matched_count = await query_matching_games(
        session=session,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=request.target_hash,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
        offset=request.offset,
        limit=request.limit,
    )

    game_records = [
        GameRecord(
            game_id=g.id,
            user_result=derive_user_result(g.result, g.user_color),
            played_at=g.played_at,
            time_control_bucket=g.time_control_bucket,
            platform=g.platform,
            platform_url=g.platform_url,
            white_username=g.white_username,
            black_username=g.black_username,
            white_rating=g.white_rating,
            black_rating=g.black_rating,
            opening_name=g.opening_name,
            opening_eco=g.opening_eco,
            user_color=g.user_color,
            move_count=g.move_count,
            termination=g.termination,
            time_control_str=g.time_control_str,
            result_fen=g.result_fen,
        )
        for g in games
    ]

    return AnalysisResponse(
        stats=stats,
        games=game_records,
        matched_count=matched_count,
        offset=request.offset,
        limit=request.limit,
    )


async def get_time_series(
    session: AsyncSession,
    user_id: int,
    request: TimeSeriesRequest,
) -> TimeSeriesResponse:
    """Return rolling-window win-rate time series for each bookmark in the request.

    Processes all bookmarks in a single service call — no N+1 HTTP calls.
    Each datapoint represents the win rate over the trailing ROLLING_WINDOW_SIZE
    games (or all games so far if fewer than ROLLING_WINDOW_SIZE have been played).
    Partial windows (games 1 to ROLLING_WINDOW_SIZE-1) are included from the start.
    """
    cutoff = recency_cutoff(request.recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    series: list[BookmarkTimeSeries] = []
    for bkm in request.bookmarks:
        hash_column = HASH_COLUMN_MAP[bkm.match_side]
        # Fetch all games (no recency filter) so rolling windows are pre-filled.
        # Other filters (time_control, platform, etc.) still applied.
        rows = await query_time_series(
            session,
            user_id,
            hash_column,
            bkm.target_hash,
            bkm.color,
            time_control=request.time_control,
            platform=request.platform,
            rated=request.rated,
            opponent_type=request.opponent_type,
            recency_cutoff=None,
        )

        # Build rolling-window datapoints from chronological per-game rows.
        # rows: (played_at, result, user_color) tuples ordered by played_at ASC.
        # Dict keyed by date keeps only the last game's rolling window per day.
        results_so_far: list[str] = []  # "win", "draw", or "loss" per game
        total_wins = total_draws = total_losses = 0
        data_by_date: dict[str, TimeSeriesPoint] = {}

        for played_at, result, user_color in rows:
            outcome = derive_user_result(result, user_color)
            results_so_far.append(outcome)

            # Accumulate overall totals (may be narrowed below by recency filter)
            if outcome == "win":
                total_wins += 1
            elif outcome == "draw":
                total_draws += 1
            else:
                total_losses += 1

            # Rolling window: trailing ROLLING_WINDOW_SIZE results
            window = results_so_far[-ROLLING_WINDOW_SIZE:]
            window_wins = window.count("win")
            window_total = len(window)
            win_rate = window_wins / window_total if window_total > 0 else 0.0

            data_by_date[played_at.strftime("%Y-%m-%d")] = TimeSeriesPoint(
                date=played_at.strftime("%Y-%m-%d"),
                win_rate=round(win_rate, 4),
                game_count=window_total,
                window_size=ROLLING_WINDOW_SIZE,
            )

        # Filter output to recency window (rolling window was computed over full history)
        data = list(data_by_date.values())
        if cutoff_str:
            data = [pt for pt in data if pt.date >= cutoff_str]
            # Recompute totals from filtered period only
            total_wins = total_draws = total_losses = 0
            for played_at, result, user_color in rows:
                if played_at.strftime("%Y-%m-%d") >= cutoff_str:
                    outcome = derive_user_result(result, user_color)
                    if outcome == "win":
                        total_wins += 1
                    elif outcome == "draw":
                        total_draws += 1
                    else:
                        total_losses += 1

        total_games = total_wins + total_draws + total_losses
        series.append(
            BookmarkTimeSeries(
                bookmark_id=bkm.bookmark_id,
                data=data,
                total_wins=total_wins,
                total_draws=total_draws,
                total_losses=total_losses,
                total_games=total_games,
            )
        )

    return TimeSeriesResponse(series=series)


async def _fetch_result_fens(
    session: AsyncSession,
    user_id: int,
    result_hashes: list[int],
) -> dict[int, str]:
    """Return {result_hash: board_fen} by replaying PGNs to the target ply.

    For each result_hash, fetches one sample game_id + ply from game_positions,
    then replays that game's PGN to the given ply and extracts board_fen
    (piece-placement-only FEN, not full FEN with castling/en passant).

    Uses DISTINCT ON full_hash so a single query fetches one sample per hash.
    Batches all PGN fetches in a second query to avoid N+1 queries.
    """
    if not result_hashes:
        return {}

    # One sample (full_hash, game_id, ply) per result_hash
    stmt = (
        select(GamePosition.full_hash, GamePosition.game_id, GamePosition.ply)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.full_hash.in_(result_hashes),
        )
        .distinct(GamePosition.full_hash)
        .order_by(GamePosition.full_hash, GamePosition.game_id)
    )
    samples_result = await session.execute(stmt)
    sample_rows = list(samples_result.all())

    if not sample_rows:
        return {}

    # Batch-fetch PGNs for all sampled game_ids
    game_ids = [row.game_id for row in sample_rows]
    pgn_stmt = select(Game.id, Game.pgn).where(Game.id.in_(game_ids))
    pgn_result = await session.execute(pgn_stmt)
    pgn_map = {row.id: row.pgn for row in pgn_result.all()}

    # Replay each PGN to the target ply and extract board_fen
    result_fens: dict[int, str] = {}
    for row in sample_rows:
        pgn_str = pgn_map.get(row.game_id)
        if not pgn_str:
            continue
        try:
            game = chess.pgn.read_game(io.StringIO(pgn_str))
        except Exception:
            sentry_sdk.capture_exception()
            continue
        if not game:
            continue
        board = game.board()
        for i, move in enumerate(game.mainline_moves()):
            board.push(move)
            if i + 1 == row.ply:
                # Pushed row.ply moves — now at the target ply position
                break
        result_fens[row.full_hash] = board.board_fen()

    return result_fens


async def get_next_moves(
    session: AsyncSession,
    user_id: int,
    request: NextMovesRequest,
) -> NextMovesResponse:
    """Orchestrate next-move aggregation and return NextMovesResponse.

    Steps:
    1. Compute optional recency cutoff datetime.
    2. Compute position_stats via query_all_results with full_hash.
    3. Query aggregated next moves (move_san, result_hash, W/D/L counts).
    4. Batch-query transposition counts for all result hashes.
    5. Compute result_fen for each result_hash via PGN replay.
    6. Build NextMoveEntry list and apply sort_by ordering.
    7. Return NextMovesResponse.
    """
    cutoff = recency_cutoff(request.recency)

    # --- Position stats using full_hash ---
    all_rows = await query_all_results(
        session=session,
        user_id=user_id,
        hash_column=GamePosition.full_hash,
        target_hash=request.target_hash,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
    )

    wins = draws = losses = 0
    for result, user_color in all_rows:
        outcome = derive_user_result(result, user_color)
        if outcome == "win":
            wins += 1
        elif outcome == "draw":
            draws += 1
        else:
            losses += 1

    total = wins + draws + losses
    win_pct = round(wins / total * 100, 1) if total > 0 else 0.0
    draw_pct = round(draws / total * 100, 1) if total > 0 else 0.0
    loss_pct = round(losses / total * 100, 1) if total > 0 else 0.0
    position_stats = WDLStats(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
    )

    # --- Next moves aggregation ---
    move_rows = await query_next_moves(
        session=session,
        user_id=user_id,
        target_hash=request.target_hash,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
    )

    if not move_rows:
        return NextMovesResponse(position_stats=position_stats, moves=[])

    # --- Transposition counts (batch) ---
    result_hashes = list({row.result_hash for row in move_rows})
    trans_counts = await query_transposition_counts(
        session=session,
        user_id=user_id,
        result_hash_list=result_hashes,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
    )

    # --- Result FENs via PGN replay ---
    result_fens = await _fetch_result_fens(session, user_id, result_hashes)

    # --- Build move entries ---
    moves: list[NextMoveEntry] = []
    for row in move_rows:
        gc = row.game_count
        w, d, lo = row.wins, row.draws, row.losses
        wp = round(w / gc * 100, 1) if gc > 0 else 0.0
        dp = round(d / gc * 100, 1) if gc > 0 else 0.0
        lp = round(lo / gc * 100, 1) if gc > 0 else 0.0
        moves.append(
            NextMoveEntry(
                move_san=row.move_san,
                game_count=gc,
                wins=w,
                draws=d,
                losses=lo,
                win_pct=wp,
                draw_pct=dp,
                loss_pct=lp,
                result_hash=str(row.result_hash),
                result_fen=result_fens.get(row.result_hash, ""),
                transposition_count=trans_counts.get(row.result_hash, gc),
            )
        )

    # --- Sort ---
    if request.sort_by == "win_rate":
        moves.sort(key=lambda m: m.win_pct, reverse=True)
    else:  # frequency (default)
        moves.sort(key=lambda m: m.game_count, reverse=True)

    return NextMovesResponse(position_stats=position_stats, moves=moves)
