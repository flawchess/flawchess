"""Openings service: W/D/L derivation, stats computation, and orchestration."""

import datetime
import io
import logging
from typing import Literal

import sentry_sdk

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.openings_repository import (
    HASH_COLUMN_MAP,
    query_matching_games,
    query_next_moves,
    query_time_series,
    query_transposition_counts,
    query_transposition_wdl,  # Phase 80.1 D-02 — resulting-position WDL
    query_wdl_counts,
)
from app.repositories.stats_repository import query_opening_phase_entry_metrics_batch
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
)
from app.services.score_confidence import compute_confidence_bucket, wilson_bounds
from app.schemas.openings import (
    OpeningsRequest,
    OpeningsResponse,
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

logger = logging.getLogger(__name__)

# Rolling window size for win-rate time series computation.
ROLLING_WINDOW_SIZE = 50

# Minimum games in a rolling window before emitting a timeline data point.
# Prevents noisy 0%/100% points at the start of a series.
MIN_GAMES_FOR_TIMELINE = 10

# Maps recency filter strings to timedelta offsets.
RECENCY_DELTAS: dict[str, datetime.timedelta] = {
    "week": datetime.timedelta(days=7),
    "month": datetime.timedelta(days=30),
    "3months": datetime.timedelta(days=90),
    "6months": datetime.timedelta(days=180),
    "year": datetime.timedelta(days=365),
    "3years": datetime.timedelta(days=365 * 3),
    "5years": datetime.timedelta(days=365 * 5),
}


def _build_wdl_stats(wins: int, draws: int, losses: int, total: int) -> WDLStats:
    """Construct WDLStats with score, confidence, p_value, and Wilson 95% CI.

    Computes score = (W + 0.5·D) / total via compute_confidence_bucket. The CI
    uses Wilson bounds (shared `wilson_bounds`) — Wald was clamping to [0, 1] at
    the boundaries and degenerated to width 0 at p=0/1, so it was replaced with
    Wilson which is well-defined at the boundaries and always contains p.
    When total == 0, all stats are neutral defaults (score=0.5, CI=[0.5, 0.5]).
    """
    if total > 0:
        win_pct = round(wins / total * 100, 1)
        draw_pct = round(draws / total * 100, 1)
        loss_pct = round(losses / total * 100, 1)
    else:
        win_pct = draw_pct = loss_pct = 0.0

    confidence, p_value, _se = compute_confidence_bucket(wins, draws, losses, total)
    if total > 0:
        score = (wins + 0.5 * draws) / total
    else:
        score = 0.5
    if total > 0:
        ci_low, ci_high = wilson_bounds(score, total)
    else:
        ci_low = ci_high = 0.5

    return WDLStats(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
        score=score,
        confidence=confidence,
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
    )


def derive_user_result(result: str, user_color: str) -> Literal["win", "draw", "loss"]:
    """Derive win/draw/loss from the raw PGN result and the user's color.

    Args:
        result: One of "1-0", "0-1", "1/2-1/2".
        user_color: One of "white", "black".

    Returns:
        "draw" for draws, "win" when the user's side won, "loss" otherwise.
    """
    if result == "1/2-1/2":
        return "draw"
    if (result == "1-0" and user_color == "white") or (result == "0-1" and user_color == "black"):
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
    request: OpeningsRequest,
) -> OpeningsResponse:
    """Orchestrate a position openings query and return W/D/L stats + games.

    Steps:
    1. Resolve hash column from match_side.
    2. Compute optional recency cutoff datetime.
    3. Fetch all (result, user_color) rows for aggregate stats.
    4. Compute W/D/L counts and percentages.
    5. Fetch paginated Game objects.
    6. Build GameRecord list and return OpeningsResponse.
    """
    # When target_hash is None, skip position filtering entirely
    hash_column = HASH_COLUMN_MAP[request.match_side] if request.target_hash is not None else None
    cutoff = recency_cutoff(request.recency)

    # --- Stats via SQL aggregation (single round-trip, no Python loop) ---
    wdl_row = await query_wdl_counts(
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
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
    wins, draws, losses, total = wdl_row.wins, wdl_row.draws, wdl_row.losses, wdl_row.total

    stats = _build_wdl_stats(wins, draws, losses, total)

    # --- MG-entry eval pillar (quick task 260508-f9o) ---
    # Reuse the same helper + finalizer used by stats_service.get_most_played_openings
    # (lines 405-420) so the Moves-tab "Results played as" section gets the same
    # avg_eval_pawns / CI / confidence triple shown by the Stats and Insights cards.
    # AsyncSession is not safe for asyncio.gather (CLAUDE.md) — sequential await.
    if request.target_hash is not None:
        phase_entry_metrics = await query_opening_phase_entry_metrics_batch(
            session=session,
            user_id=user_id,
            hashes=[request.target_hash],
            color=request.color,
            time_control=request.time_control,
            platform=request.platform,
            rated=request.rated,
            opponent_type=request.opponent_type,
            recency_cutoff=cutoff,
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
            hash_column=request.match_side,
        )
        pe = phase_entry_metrics.get(request.target_hash)
        if pe is not None and pe.eval_n_mg > 0:
            # Mirrors stats_service.py:405-420 verbatim. H0: mean == 0 cp
            # (engine-balanced); the per-color baseline is a display tick on
            # the bullet chart, not the test reference (260504-rvh).
            confidence_mg, p_value_mg, mean_cp_mg, ci_half_mg = compute_eval_confidence_bucket(
                pe.eval_sum_mg,
                pe.eval_sumsq_mg,
                pe.eval_n_mg,
            )
            stats.avg_eval_pawns = mean_cp_mg / 100.0  # cp -> pawns
            if pe.eval_n_mg >= 2:
                stats.eval_ci_low_pawns = (mean_cp_mg - ci_half_mg) / 100.0
                stats.eval_ci_high_pawns = (mean_cp_mg + ci_half_mg) / 100.0
            stats.eval_n = pe.eval_n_mg
            stats.eval_p_value = p_value_mg
            stats.eval_confidence = confidence_mg

    # Per-color engine-asymmetry baseline (rendered as a tick on the bullet
    # chart). When request.color is None ("either color"), default to the
    # white baseline — matches the convention in stats_service / opening_insights.
    eval_baseline_pawns = (
        EVAL_BASELINE_PAWNS_BLACK if request.color == "black" else EVAL_BASELINE_PAWNS_WHITE
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
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
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

    return OpeningsResponse(
        stats=stats,
        games=game_records,
        matched_count=matched_count,
        offset=request.offset,
        limit=request.limit,
        eval_baseline_pawns=eval_baseline_pawns,
    )


async def get_time_series(
    session: AsyncSession,
    user_id: int,
    request: TimeSeriesRequest,
) -> TimeSeriesResponse:
    """Return rolling-window chess-score time series for each bookmark in the request.

    Processes all bookmarks in a single service call — no N+1 HTTP calls.
    Each datapoint represents the chess score (W + 0.5·D) / N over the trailing
    ROLLING_WINDOW_SIZE games (or all games so far if fewer than ROLLING_WINDOW_SIZE
    have been played). Partial windows (games 1 to ROLLING_WINDOW_SIZE-1) are
    included from the start.
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
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
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
            window_draws = window.count("draw")
            window_total = len(window)
            score = (window_wins + 0.5 * window_draws) / window_total if window_total > 0 else 0.0

            data_by_date[played_at.strftime("%Y-%m-%d")] = TimeSeriesPoint(
                date=played_at.strftime("%Y-%m-%d"),
                score=round(score, 4),
                game_count=window_total,
                window_size=ROLLING_WINDOW_SIZE,
            )

        # Drop early points with too few games in the rolling window
        # Filter output to recency window (rolling window was computed over full history)
        data = [pt for pt in data_by_date.values() if pt.game_count >= MIN_GAMES_FOR_TIMELINE]
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
    2. Compute position_stats via query_wdl_counts with full_hash.
    3. Query aggregated next moves (move_san, result_hash, W/D/L counts).
    4. Batch-query transposition counts for all result hashes.
    5. Compute result_fen for each result_hash via PGN replay.
    6. Build NextMoveEntry list and apply sort_by ordering.
    7. Return NextMovesResponse.
    """
    cutoff = recency_cutoff(request.recency)

    # --- Position stats via SQL aggregation (single round-trip, no Python loop) ---
    wdl_row = await query_wdl_counts(
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
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
    wins, draws, losses, total = wdl_row.wins, wdl_row.draws, wdl_row.losses, wdl_row.total
    position_stats = _build_wdl_stats(wins, draws, losses, total)

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
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
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
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )

    # --- Resulting-position WDL (batch) — Phase 80.1 D-02 ---
    # Sequential await (NOT asyncio.gather): AsyncSession is not concurrency-safe
    # per CLAUDE.md. Filter parameters mirror query_transposition_counts above
    # exactly to preserve filter parity (Pitfall 1 from RESEARCH.md).
    pos_wdl = await query_transposition_wdl(
        session=session,
        user_id=user_id,
        result_hash_list=result_hashes,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        recency_cutoff=cutoff,
        color=request.color,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )

    # --- Result FENs via PGN replay ---
    result_fens = await _fetch_result_fens(session, user_id, result_hashes)

    # --- Build move entries ---
    # Phase 80.1 D-01/D-02: game_count stays move-played; W/D/L flip to
    # resulting-position WDL (combined across all games visiting result_hash,
    # including transpositions). The two denominators (gc and pos_total)
    # legitimately diverge when transpositions exist — see TranspositionInfo
    # popover in MoveExplorer.tsx for the user-facing explanation.
    moves: list[NextMoveEntry] = []
    for row in move_rows:
        gc = row.game_count  # move-played, stays per D-01
        pos = pos_wdl.get(row.result_hash)
        if pos is None:
            # Filter mismatch defensive fallback (Pitfall 4 from RESEARCH.md).
            # Should not occur if query_transposition_wdl applies identical
            # filters to query_next_moves; logged so it surfaces in dev/prod.
            logger.warning(
                "query_transposition_wdl missing result_hash=%s; falling back to move-played WDL",
                row.result_hash,
            )
            w, d, lo = row.wins, row.draws, row.losses
            pos_total = gc
        else:
            w, d, lo = pos
            pos_total = w + d + lo

        wp = round(w / pos_total * 100, 1) if pos_total > 0 else 0.0
        dp = round(d / pos_total * 100, 1) if pos_total > 0 else 0.0
        lp = round(lo / pos_total * 100, 1) if pos_total > 0 else 0.0
        score = (w + 0.5 * d) / pos_total if pos_total > 0 else 0.5
        # Move Explorer rows are sorted by frequency or win_rate (not Wald CI bound),
        # so SE is not needed here — `_se` underscore signals "intentionally unused".
        confidence, p_value, _se = compute_confidence_bucket(w, d, lo, pos_total)
        moves.append(
            NextMoveEntry(
                move_san=row.move_san,
                game_count=gc,  # move-played per D-01
                wins=w,  # resulting-position per D-02
                draws=d,
                losses=lo,
                win_pct=wp,
                draw_pct=dp,
                loss_pct=lp,
                result_hash=str(row.result_hash),
                result_fen=result_fens.get(row.result_hash, ""),
                transposition_count=trans_counts.get(row.result_hash, gc),
                score=score,
                confidence=confidence,
                p_value=p_value,
            )
        )

    # --- Sort ---
    if request.sort_by == "win_rate":
        moves.sort(key=lambda m: m.win_pct, reverse=True)
    else:  # frequency (default)
        moves.sort(key=lambda m: m.game_count, reverse=True)

    return NextMovesResponse(position_stats=position_stats, moves=moves)
