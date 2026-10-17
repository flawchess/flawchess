"""Openings service: W/D/L derivation, stats computation, and orchestration."""

import datetime
import io
import logging
from collections.abc import Sequence
from typing import Any, Literal

import sentry_sdk

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import MAX_EXPLORER_PLY, GamePosition
from app.repositories.openings_repository import (
    HASH_COLUMN_MAP,
    query_matching_games,
    query_next_moves,
    query_resulting_position_wdl,  # Resulting-position WDL
    query_time_series,
    query_wdl_counts,
)
from app.repositories.stats_repository import query_opening_phase_entry_metrics_batch
from app.services.opening_eval import finalize_opening_eval, resolve_eval_baseline_pawns
from app.services.repertoire_recency import is_current, resolve_current_cutoffs
from app.services.score_confidence import (
    VERDICT_CI_Z_99,
    compute_confidence_bucket,
    score_verdict_fields,
    wilson_bounds,
)
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


def _build_wdl_stats(
    wins: int,
    draws: int,
    losses: int,
    total: int,
    last_played_at: datetime.datetime | None = None,
) -> WDLStats:
    """Construct WDLStats with score, confidence, p_value, and Wilson 95% and 99% CIs.

    Computes score = (W + 0.5·D) / total via compute_confidence_bucket. The CI
    uses Wilson bounds (shared `wilson_bounds`): well-defined at p=0/1 and always
    containing p.
    When total == 0, all stats are neutral defaults (score=0.5, CI=[0.5, 0.5]).

    `last_played_at` is the MAX(games.played_at) across the contributing games;
    the FE renders a "Last played: <relative>" line
    in the WDL confidence tooltip when it is non-None.
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
        ci99_low, ci99_high = wilson_bounds(score, total, z=VERDICT_CI_Z_99)
    else:
        ci_low = ci_high = 0.5
        ci99_low = ci99_high = 0.5

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
        ci99_low=ci99_low,
        ci99_high=ci99_high,
        last_played_at=last_played_at,
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


async def analyze(
    session: AsyncSession,
    user_id: int,
    request: OpeningsRequest,
) -> OpeningsResponse:
    """Orchestrate a position openings query and return W/D/L stats + games.

    Steps:
    1. Resolve hash column from match_side.
    2. Fetch all (result, user_color) rows for aggregate stats.
    3. Compute W/D/L counts and percentages.
    4. Fetch paginated Game objects.
    5. Build GameRecord list and return OpeningsResponse.
    """
    # When target_hash is None, skip position filtering entirely
    hash_column = HASH_COLUMN_MAP[request.match_side] if request.target_hash is not None else None

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
        from_date=request.from_date,
        to_date=request.to_date,
        color=request.color,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
    wins, draws, losses, total = wdl_row.wins, wdl_row.draws, wdl_row.losses, wdl_row.total

    stats = _build_wdl_stats(wins, draws, losses, total, last_played_at=wdl_row.last_played_at)

    # --- MG-entry eval pillar ---
    # Same helper + finalizer as stats_service.get_most_played_openings so the
    # Moves/Games position stats get the same avg_eval_pawns / CI / confidence
    # fields shown by the Stats tab rows.
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
            from_date=request.from_date,
            to_date=request.to_date,
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
            hash_column=request.match_side,
        )
        # Phase 242 (D-13): the z-test runs against the colour baseline (H0: mean ==
        # baseline), so the baseline is the verdict bar centre rather than a display
        # tick. avg_eval_pawns stays the raw mean. Shared with the Stats tab rows.
        eval_fields = finalize_opening_eval(
            phase_entry_metrics.get(request.target_hash), request.color
        )
        stats.avg_eval_pawns = eval_fields["avg_eval_pawns"]
        stats.eval_ci_low_pawns = eval_fields["eval_ci_low_pawns"]
        stats.eval_ci_high_pawns = eval_fields["eval_ci_high_pawns"]
        stats.eval_ci99_low_pawns = eval_fields["eval_ci99_low_pawns"]
        stats.eval_ci99_high_pawns = eval_fields["eval_ci99_high_pawns"]
        stats.eval_n = eval_fields["eval_n"]
        stats.eval_p_value = eval_fields["eval_p_value"]
        stats.eval_confidence = eval_fields["eval_confidence"]

    # Per-colour engine baseline (verdict bar centre and z-test H0). color=None
    # ("either colour") defaults to the white baseline, one resolver for the whole app.
    eval_baseline_pawns = resolve_eval_baseline_pawns(request.color)

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
        from_date=request.from_date,
        to_date=request.to_date,
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
            ply_count=g.ply_count,
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


def _in_window(
    played_at: datetime.datetime,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
) -> bool:
    """Return True when played_at falls within [from_date, to_date] (inclusive on both ends).

    When from_date or to_date is None, that bound is treated as open:
    None lower bound means "from the beginning of time", None upper bound
    means "to the end of time". Both None means always in-window (open range).
    Compares on date only — played_at.date() strips the time component so
    "end of day to_date" semantics match the repository convention.
    """
    game_date = played_at.date()
    if from_date is not None and game_date < from_date:
        return False
    if to_date is not None and game_date > to_date:
        return False
    return True


def _iso_week_monday(played_at: datetime.datetime) -> str:
    """ISO date string of the Monday of played_at's ISO week (the weekly bucket key).

    Same Monday-keyed bucketing as endgame_service's weekly score timeline
    (isocalendar weekday - 1 days back), so the two charts share a week axis.
    """
    _iso_year, _iso_week, iso_weekday = played_at.isocalendar()
    return (played_at - datetime.timedelta(days=iso_weekday - 1)).date().isoformat()


def _rolling_score(results_so_far: Sequence[str]) -> tuple[float, int]:
    """Chess score and size of the trailing ROLLING_WINDOW_SIZE window of outcomes."""
    window = results_so_far[-ROLLING_WINDOW_SIZE:]
    window_total = len(window)
    window_score = (
        (window.count("win") + 0.5 * window.count("draw")) / window_total
        if window_total > 0
        else 0.0
    )
    return window_score, window_total


def _build_bookmark_time_series(
    bookmark_id: int,
    rows: Sequence[Row[Any]],
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    cutoff: datetime.datetime | None,
) -> BookmarkTimeSeries:
    """Build one bookmark's weekly rolling-score time series from its chronological rows.

    `rows` are (played_at, result, user_color) tuples ordered by played_at ASC,
    spanning full history so pre-window games warm the rolling average even
    though only in-window points and WDL totals are emitted.

    Phase 242: points are bucketed by ISO week (keyed by that week's Monday). Each
    carries the rolling-50 score after the week's LAST in-window game and
    `per_week_games` (in-window games that week, the ScoreChart volume bars).
    The MIN_GAMES_FOR_TIMELINE floor still drops weeks whose rolling window is too
    thin. The series also carries the shared score verdict fields over its in-window
    totals (D-18) and `is_current` against the colour's repertoire cutoff (D-04).
    """
    results_so_far: list[str] = []  # "win", "draw", or "loss" per game
    outcome_counts = {"win": 0, "draw": 0, "loss": 0}
    last_played_at: datetime.datetime | None = None
    per_week_games: dict[str, int] = {}
    point_by_week: dict[str, TimeSeriesPoint] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        # Every game warms the rolling window, in-window or not.
        results_so_far.append(outcome)
        if not _in_window(played_at, from_date, to_date):
            continue

        outcome_counts[outcome] += 1
        last_played_at = played_at  # rows ordered ASC; final assignment wins
        week = _iso_week_monday(played_at)
        per_week_games[week] = per_week_games.get(week, 0) + 1
        window_score, window_total = _rolling_score(results_so_far)
        # Later games of the same week overwrite earlier ones: last game wins.
        point_by_week[week] = TimeSeriesPoint(
            date=week,
            score=round(window_score, 4),
            game_count=window_total,
            window_size=ROLLING_WINDOW_SIZE,
            per_week_games=per_week_games[week],
        )

    # Drop early points with too few games in the rolling window.
    data = [pt for pt in point_by_week.values() if pt.game_count >= MIN_GAMES_FOR_TIMELINE]

    total_wins = outcome_counts["win"]
    total_draws = outcome_counts["draw"]
    total_losses = outcome_counts["loss"]
    return BookmarkTimeSeries(
        bookmark_id=bookmark_id,
        data=data,
        total_wins=total_wins,
        total_draws=total_draws,
        total_losses=total_losses,
        total_games=total_wins + total_draws + total_losses,
        last_played_at=last_played_at,
        is_current=is_current(last_played_at, cutoff),
        **score_verdict_fields(total_wins, total_draws, total_losses),
    )


async def get_time_series(
    session: AsyncSession,
    user_id: int,
    request: TimeSeriesRequest,
    *,
    now_utc: datetime.datetime,
) -> TimeSeriesResponse:
    """Return weekly rolling-window chess-score time series for each bookmark in the request.

    Processes all bookmarks in a single service call — no N+1 HTTP calls.
    Each datapoint is one ISO week (keyed by its Monday) and carries the chess
    score (W + 0.5·D) / N over the trailing ROLLING_WINDOW_SIZE games (or all games
    so far if fewer than ROLLING_WINDOW_SIZE have been played) after that week's
    last game, plus the number of in-window games played that week. Partial
    windows (games 1 to ROLLING_WINDOW_SIZE-1) are included from the start,
    subject to the MIN_GAMES_FOR_TIMELINE floor.

    When from_date/to_date are set, emitted
    TimeSeriesPoints and WDL totals cover only in-window games; the rolling
    average is still warmed from pre-window games (full chronological history
    is loaded so trailing averages anchor correctly). When from_date/to_date
    are None, behavior is unchanged — the chart covers the full game history.

    `now_utc` (from the dev_now_utc dependency) anchors the per-colour
    current-repertoire cutoff behind each series' `is_current` flag (D-02..D-04).
    """
    # One cutoff query per distinct bookmark colour, under the request filters
    # (D-02). The cutoff uses the WINDOWED dates even though the series query below
    # loads full history for warm-up. Sequential awaits: AsyncSession is not
    # safe for asyncio.gather.
    colors = sorted({bkm.color for bkm in request.bookmarks if bkm.color is not None})
    cutoffs = await resolve_current_cutoffs(
        session,
        user_id,
        colors,
        now_utc=now_utc,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        from_date=request.from_date,
        to_date=request.to_date,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )

    series: list[BookmarkTimeSeries] = []
    for bkm in request.bookmarks:
        hash_column = HASH_COLUMN_MAP[bkm.match_side]
        # Do NOT pass from_date/to_date to the repo — keep loading the full
        # chronological history so pre-window games warm the rolling average.
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
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
        )
        # A colour-less bookmark has no cutoff, so it reads as current.
        cutoff = cutoffs[bkm.color] if bkm.color is not None else None
        series.append(
            _build_bookmark_time_series(
                bkm.bookmark_id, rows, request.from_date, request.to_date, cutoff
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

    # One sample (full_hash, game_id, ply) per result_hash.
    # ply <= MAX_EXPLORER_PLY ensures the partial hash index is used.
    stmt = (
        select(GamePosition.full_hash, GamePosition.game_id, GamePosition.ply)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.full_hash.in_(result_hashes),
            GamePosition.ply <= MAX_EXPLORER_PLY,
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
    1. Compute position_stats via query_wdl_counts with full_hash.
    2. Query aggregated next moves (move_san, result_hash, W/D/L counts).
    3. Batch-query resulting-position WDL for all result hashes; derive
       trans_counts inline from wins+draws+losses (one round trip).
    4. Compute result_fen for each result_hash via PGN replay.
    5. Build NextMoveEntry list and apply sort_by ordering.
    6. Return NextMovesResponse.
    """
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
        from_date=request.from_date,
        to_date=request.to_date,
        color=request.color,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
    wins, draws, losses, total = wdl_row.wins, wdl_row.draws, wdl_row.losses, wdl_row.total
    position_stats = _build_wdl_stats(
        wins, draws, losses, total, last_played_at=wdl_row.last_played_at
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
        from_date=request.from_date,
        to_date=request.to_date,
        color=request.color,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )

    if not move_rows:
        return NextMovesResponse(position_stats=position_stats, moves=[])

    # --- Resulting-position WDL (batch) ---
    # Single round trip returns {result_hash: (wins, draws, losses, last_played_at)}.
    # trans_counts (the move-tab "Transposition count" popover, position-total games
    # reaching result_hash via any move order) is derived inline from wins+draws+losses
    # since every game has exactly one result. Filter parameters mirror
    # query_next_moves exactly to preserve filter parity.
    result_hashes = list({row.result_hash for row in move_rows})
    pos_wdl = await query_resulting_position_wdl(
        session=session,
        user_id=user_id,
        hash_list=result_hashes,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        from_date=request.from_date,
        to_date=request.to_date,
        color=request.color,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
    trans_counts: dict[int, int] = {h: w + d + lo for h, (w, d, lo, _last) in pos_wdl.items()}

    # --- Result FENs via PGN replay ---
    result_fens = await _fetch_result_fens(session, user_id, result_hashes)

    # --- Build move entries ---
    # game_count stays move-played; W/D/L flip to
    # resulting-position WDL (combined across all games visiting result_hash,
    # including transpositions). The two denominators (move_game_count and pos_total)
    # legitimately diverge when transpositions exist — see TranspositionInfo
    # popover in MoveExplorer.tsx for the user-facing explanation.
    moves: list[NextMoveEntry] = []
    for row in move_rows:
        move_game_count = row.game_count  # move-played
        pos = pos_wdl.get(row.result_hash)
        if pos is None:
            # Filter mismatch defensive fallback.
            # Should not occur if query_resulting_position_wdl applies identical
            # filters to query_next_moves; logged so it surfaces in dev/prod.
            logger.warning(
                "query_resulting_position_wdl missing result_hash=%s; falling back to move-played WDL",
                row.result_hash,
            )
            w, d, lo = row.wins, row.draws, row.losses
            pos_total = move_game_count
        else:
            w, d, lo, _last = pos
            pos_total = w + d + lo

        wp = round(w / pos_total * 100, 1) if pos_total > 0 else 0.0
        dp = round(d / pos_total * 100, 1) if pos_total > 0 else 0.0
        lp = round(lo / pos_total * 100, 1) if pos_total > 0 else 0.0
        score = (w + 0.5 * d) / pos_total if pos_total > 0 else 0.5
        # Move Explorer rows are sorted by frequency or win_rate (not a CI bound),
        # so SE is not needed here — `_se` underscore signals "intentionally unused".
        confidence, p_value, _se = compute_confidence_bucket(w, d, lo, pos_total)
        moves.append(
            NextMoveEntry(
                move_san=row.move_san,
                game_count=move_game_count,  # move-played
                wins=w,  # resulting-position
                draws=d,
                losses=lo,
                win_pct=wp,
                draw_pct=dp,
                loss_pct=lp,
                result_hash=str(row.result_hash),
                result_fen=result_fens.get(row.result_hash, ""),
                transposition_count=trans_counts.get(row.result_hash, move_game_count),
                score=score,
                confidence=confidence,
                p_value=p_value,
                # MAX(played_at) across all games where the user played this
                # candidate move from the queried position (move-played
                # semantics). Drives the move-explorer Score popover's
                # "Last played: <relative>" line.
                last_played_at=row.last_played_at,
            )
        )

    # --- Sort ---
    if request.sort_by == "win_rate":
        moves.sort(key=lambda m: m.win_pct, reverse=True)
    else:  # frequency (default)
        moves.sort(key=lambda m: m.game_count, reverse=True)

    return NextMovesResponse(position_stats=position_stats, moves=moves)
