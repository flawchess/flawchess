"""Library (Games-surface) service — Phase 106 (SEED-036, LIBG-08).

Phase 108 D-02 migration: GET /library/games and GET /library/flaw-stats now
read M+B flaws from `game_flaws` instead of re-calling the Phase 105 kernel
per query. The per-game N+1 `_load_analyzed_flaws` loop is retired.

Games card chips (curated/deduped M+B tags) and per-game M+B severity counts
come from a single batched `game_flaws` read for the whole page. Inaccuracy
counts come from the oracle columns (games.white_/black_inaccuracies) — never
from game_flaws (D-03). Analysis state ("no engine analysis") is determined by
the eval-coverage gate on game_positions (not by game_flaws row presence).

Flaw-stats severity counts, tag distribution, and trend come from a single
game_flaws JOIN games scan. The analyzed_n/total_n denominator stays on the
eval-coverage gate (game_positions) — a game analyzed with zero M+B flaws still
counts toward analyzed_n (Pitfall 6/RESEARCH §7).

Chip curation (SEED-036): aggregate tags to the game level across all game_flaws
rows, drop any phase tag (opening/middlegame/endgame), emit one chip per
remaining tag type (game-level dedupe), in a deterministic order.
"""

import datetime
from typing import Literal

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.repositories import library_repository
from app.repositories.library_repository import _TEMPO_INT_TO_TAG  # noqa: F401
from app.schemas.library import (
    FlawStatsResponse,
    FlawTrendPoint,
    GameFlawCard,
    LibraryFlawsResponse,
    LibraryGamesResponse,
    SeverityRates,
    TagDistribution,
)
from app.models.game_position import GamePosition
from app.schemas.library import EvalPoint, FlawMarker, PhaseTransitions
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.flaws_service import (
    FlawSeverity,
    FlawTag,
    SeverityCounts,
    TempoTag,
    _MoveEntry,
    _build_tags,
    _resolve_increment,
    _run_all_moves_pass,
)
from app.services.openings_service import (
    MIN_GAMES_FOR_TIMELINE,
    ROLLING_WINDOW_SIZE,
    derive_user_result,
)

# ---------------------------------------------------------------------------
# Phase 109 eval chart helpers (LIBG-10) — Task 1 stubs, Task 2 implements
# ---------------------------------------------------------------------------

# Tags that are user-framed and must be stripped from opponent flaw markers (D-03).
_USER_FRAMED_TAGS: frozenset[FlawTag] = frozenset({"miss", "lucky-escape"})


def _build_eval_series(
    game: Game,
    positions: list[GamePosition],
) -> tuple[list[EvalPoint], list[FlawMarker], PhaseTransitions]:
    """Compute white-perspective ES line, flaw markers, and phase transitions.

    Line perspective: white-perspective (eval_mate_to_expected_score/eval_cp_to_expected_score
    called with "white"). Flaw detection perspective: mover-POV drops via
    _run_all_moves_pass (D-01/D-04). No DB access — positions are pre-fetched
    by get_library_games (D-10: single batched query, no N+1).

    Args:
        game: Game row with user_color, result, base_time_seconds, increment_seconds.
        positions: All GamePosition rows for this game, ordered by ply ASC.

    Returns:
        (eval_series, flaw_markers, phase_transitions) tuple where:
        - eval_series: white-perspective ES per ply (es=None for missing eval, D-05)
        - flaw_markers: both-color B/M/I dots with is_user discriminator (D-01/D-07)
        - phase_transitions: first ply of middlegame (phase==1) and endgame (phase==2) (D-06)
    """
    all_moves = _run_all_moves_pass(positions)
    eval_series: list[EvalPoint] = []
    flaw_markers: list[FlawMarker] = []
    middlegame_ply: int | None = None
    endgame_ply: int | None = None

    # Increment for _build_tags tempo computation (Phase 109: shared helper).
    increment = _resolve_increment(game)

    # Per-color previous clock for move-time computation (Phase 109 feedback:
    # tooltip shows clock remaining + time spent on the move). clock_seconds is
    # the mover's remaining time AFTER the move; even ply = White, odd = Black.
    # Seed with the base time so move 0/1 (each side's first move) get a value.
    base_time: float | None = game.base_time_seconds
    prev_clock: dict[int, float | None] = {0: base_time, 1: base_time}  # 0 = White, 1 = Black

    for pos in positions:
        # White-perspective ES for the chart line (D-04).
        # Use eval_mate_to_expected_score (hard 1.0/0.0) for the line only —
        # NOT for drop math (Pitfall 1/2 in RESEARCH: _ply_to_es uses MATE_CP_EQUIVALENT).
        if pos.eval_mate is not None:
            es: float | None = eval_mate_to_expected_score(pos.eval_mate, "white")
        elif pos.eval_cp is not None:
            es = eval_cp_to_expected_score(pos.eval_cp, "white")
        else:
            es = None
        # Time spent on the move = prior same-color clock − current clock + increment
        # (increment is added back after each move). Clamp negatives from rounding.
        color = pos.ply % 2  # 0 = White, 1 = Black
        clock = pos.clock_seconds
        move_seconds: float | None = None
        if clock is not None:
            prior = prev_clock[color]
            if prior is not None:
                move_seconds = round(max(0.0, prior - clock + increment), 1)
            prev_clock[color] = clock

        eval_series.append(
            EvalPoint(
                ply=pos.ply,
                es=round(es, 3) if es is not None else None,
                eval_cp=pos.eval_cp,
                eval_mate=pos.eval_mate,
                clock_seconds=clock,
                move_seconds=move_seconds,
            )
        )

        # Phase transitions — first ply where phase==1 (middlegame) or phase==2 (endgame).
        # No ply-0 line (D-06): ply 0 is the initial position, not a transition.
        if pos.phase == 1 and middlegame_ply is None and pos.ply > 0:
            middlegame_ply = pos.ply
        elif pos.phase == 2 and endgame_ply is None and pos.ply > 0:
            endgame_ply = pos.ply

        # Flaw markers from the mover-POV kernel dict (both colors, D-01/D-02).
        # The kernel skips plies with missing eval — no entry → no marker.
        entry = all_moves.get(pos.ply)
        if entry is None:
            continue
        mover_color, severity, es_before, es_after = entry
        if severity is None:
            continue
        is_user = mover_color == game.user_color
        tags: list[FlawTag]
        if severity in ("mistake", "blunder"):
            if is_user:
                tags = _build_tags(
                    pos.ply,
                    severity,
                    es_before,
                    es_after,
                    positions,
                    all_moves,
                    derive_user_result(game.result, game.user_color),
                    increment,
                    game.base_time_seconds,
                )
            else:
                tags = _build_opponent_tags(
                    pos.ply,
                    severity,
                    es_before,
                    es_after,
                    positions,
                    all_moves,
                    game,
                    increment,
                )
        else:
            tags = []  # inaccuracy — no tags (D-03)
        flaw_markers.append(
            FlawMarker(
                ply=pos.ply,
                severity=severity,
                tags=tags,
                is_user=is_user,
                move_san=pos.move_san,
            )
        )

    return (
        eval_series,
        flaw_markers,
        PhaseTransitions(middlegame_ply=middlegame_ply, endgame_ply=endgame_ply),
    )


def _build_opponent_tags(
    n: int,
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    positions: list[GamePosition],
    all_moves: dict[int, _MoveEntry],
    game: Game,
    increment: float,
) -> list[FlawTag]:
    """Tags for an opponent flaw dot — mover-framed only (D-03 resolution).

    Flips user_result to opponent's perspective so while-ahead / result-changing
    are mover-relative. Strips 'miss' and 'lucky-escape' which are user-framed
    and meaningless/misleading from the opponent's perspective (RESEARCH D-03 Gray Area).
    """
    opponent_color: Literal["white", "black"] = "black" if game.user_color == "white" else "white"
    opponent_result = derive_user_result(game.result, opponent_color)
    raw_tags = _build_tags(
        n,
        severity,
        es_before,
        es_after,
        positions,
        all_moves,
        opponent_result,
        increment,
        game.base_time_seconds,
    )
    return [t for t in raw_tags if t not in _USER_FRAMED_TAGS]


# ---------------------------------------------------------------------------
# Canonical chip order — a subset of flaws_service.FlawTag with all phase
# tags removed. Defines the deterministic ordering of curated card chips.
# game_flaws rows are M+B-only (D-03), so inaccuracy tags never appear here.
_CHIP_ORDER: tuple[FlawTag, ...] = (
    "miss",
    "lucky-escape",
    "while-ahead",
    "result-changing",
    "low-clock",
    "impatient",
    "considered",
)


def _curate_chips_from_rows(flaw_rows: list[GameFlaw]) -> list[FlawTag]:
    """Collect a deduped, deterministically-ordered set of card chips from game_flaws rows.

    Aggregates non-phase tags across all of a game's game_flaws rows:
    - Boolean columns: is_miss, is_lucky_escape, is_while_ahead, is_result_changing
    - Tempo column: _TEMPO_INT_TO_TAG lookup (None → skip)
    Phase tags are excluded (opening/middlegame/endgame per _CHIP_ORDER curation).
    One chip per remaining tag type (game-level dedupe), in _CHIP_ORDER (SEED-036).
    """
    present: set[FlawTag] = set()
    for row in flaw_rows:
        if row.is_miss:
            present.add("miss")
        if row.is_lucky_escape:
            present.add("lucky-escape")
        if row.is_while_ahead:
            present.add("while-ahead")
        if row.is_result_changing:
            present.add("result-changing")
        if row.tempo is not None:
            tempo_tag = _TEMPO_INT_TO_TAG.get(row.tempo)
            if tempo_tag is not None:
                present.add(tempo_tag)
    return [tag for tag in _CHIP_ORDER if tag in present]


def _build_card(
    game: Game,
    flaw_rows: list[GameFlaw],
    is_analyzed: bool,
    positions: list[GamePosition],
) -> GameFlawCard:
    """Build one GameFlawCard from pre-fetched game_flaws rows (D-02 migration).

    No DB access — data is pre-fetched by get_library_games in three batch queries:
    fetch_page_game_flaws (chips + M+B counts), fetch_page_analyzed_set
    (analysis_state), and fetch_page_eval_positions (eval chart data). This
    eliminates the per-game classify_game_flaws kernel re-call.

    Inaccuracy count comes from the oracle columns (games.white_/black_inaccuracies)
    — never from game_flaws (D-03). NULL oracle values default to 0.

    "No engine analysis" state is gated on the eval-coverage check (is_analyzed),
    NOT on game_flaws row count — an analyzed game with zero M+B flaws still
    returns analysis_state="analyzed" (LIBG-02).

    Phase 109 (LIBG-10): when is_analyzed and positions are provided, the three
    new eval chart fields (eval_series, flaw_markers, phase_transitions) are
    populated via _build_eval_series. Unanalyzed games always get None for these.
    """
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]

    if not is_analyzed:
        severity_counts = None
        chips = []
        analysis_state = "no_engine_analysis"
        eval_series_data = None
        flaw_marker_data = None
        phase_transition_data = None
        moves_data = None
    else:
        # M+B counts from game_flaws rows (D-02); inaccuracy from oracle (D-03).
        mistake_count = sum(1 for r in flaw_rows if r.severity == 1)
        blunder_count = sum(1 for r in flaw_rows if r.severity == 2)
        # Oracle columns come from the chess.com/lichess API analysis (acceptable
        # approximation for the card display; D-03 keeps inaccuracy off game_flaws).
        if game.user_color == "white":
            inaccuracy_count = game.white_inaccuracies or 0
        else:
            inaccuracy_count = game.black_inaccuracies or 0
        severity_counts = SeverityCounts(
            inaccuracy=inaccuracy_count,
            mistake=mistake_count,
            blunder=blunder_count,
        )
        chips = _curate_chips_from_rows(flaw_rows)
        analysis_state = "analyzed"
        # Phase 109 (LIBG-10): populate eval chart fields for analyzed games.
        if positions:
            eval_series_val, flaw_marker_val, phase_transition_val = _build_eval_series(
                game, positions
            )
            eval_series_data = eval_series_val
            flaw_marker_data = flaw_marker_val
            phase_transition_data = phase_transition_val
            # SAN mainline for client-side per-ply board reconstruction on chart
            # hover. move_san is None on the terminal position only — filter it out
            # so moves[i] aligns with ply i (positions are ply-ordered).
            moves_data = [p.move_san for p in positions if p.move_san is not None]
        else:
            eval_series_data = None
            flaw_marker_data = None
            phase_transition_data = None
            moves_data = None

    return GameFlawCard(
        game_id=game.id,
        user_result=derive_user_result(game.result, game.user_color),
        played_at=game.played_at,
        time_control_bucket=game.time_control_bucket,
        platform=game.platform,
        platform_url=game.platform_url,
        white_username=game.white_username,
        black_username=game.black_username,
        white_rating=game.white_rating,
        black_rating=game.black_rating,
        opening_name=game.opening_name,
        opening_eco=game.opening_eco,
        user_color=game.user_color,
        move_count=game.move_count,
        termination=game.termination,
        time_control_str=game.time_control_str,
        result_fen=game.result_fen,
        severity_counts=severity_counts,
        chips=chips,
        analysis_state=analysis_state,
        eval_series=eval_series_data,
        flaw_markers=flaw_marker_data,
        phase_transitions=phase_transition_data,
        moves=moves_data,
    )


async def get_library_games(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: list[str] | None,
    flaw_tags: list[str] | None = None,
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> LibraryGamesResponse:
    """Return the flaw-filtered paginated games archive (LIBG-08).

    D-02 migration: no per-game kernel re-call. Two batch queries cover the page:
    1. fetch_page_game_flaws — one query for all game_flaws rows (chips + M+B counts)
    2. fetch_page_analyzed_set — one query for the eval-coverage-analyzed subset

    Inaccuracy count comes from oracle columns (games.white_/black_inaccuracies),
    never from game_flaws (D-03). Analysis state is gated on eval coverage, not
    on game_flaws row presence (LIBG-02 — never a false 0/0/0).
    """
    try:
        games, matched_count = await library_repository.query_filtered_games(
            session,
            user_id=user_id,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            flaw_severity=flaw_severity,
            flaw_tags=flaw_tags,
            offset=offset,
            limit=limit,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
            color=color,
        )

        if not games:
            return LibraryGamesResponse(
                games=[],
                matched_count=matched_count,
                offset=offset,
                limit=limit,
            )

        page_game_ids = [g.id for g in games]

        # Batch fetch game_flaws for the whole page (one query, grouped by game_id).
        page_flaws = await library_repository.fetch_page_game_flaws(session, user_id, page_game_ids)

        # Batch fetch the analyzed subset (eval-coverage gate — not game_flaws presence).
        analyzed_set = await library_repository.fetch_page_analyzed_set(
            session, user_id, page_game_ids
        )

        # Phase 109 (D-02/D-10): batch-load positions for analyzed games only (no N+1).
        # Scoped to analyzed_set so unanalyzed games incur zero position rows.
        analyzed_game_ids = [gid for gid in page_game_ids if gid in analyzed_set]
        page_positions = await library_repository.fetch_page_eval_positions(
            session, user_id, analyzed_game_ids
        )

        cards = [
            _build_card(
                game,
                page_flaws.get(game.id, []),
                game.id in analyzed_set,
                page_positions.get(game.id, []),
            )
            for game in games
        ]
    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("library_games", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    return LibraryGamesResponse(
        games=cards,
        matched_count=matched_count,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Stats panel (LIBG-09) — GET /api/library/flaw-stats
# ---------------------------------------------------------------------------

_SEVERITY_TIERS: tuple[FlawSeverity, ...] = ("inaccuracy", "mistake", "blunder")
_TEMPO_TAGS: tuple[TempoTag, ...] = ("low-clock", "impatient", "considered")
_PER_100 = 100.0


def _compute_rates(
    counts: SeverityCounts,
    analyzed_n: int,
    total_user_moves: int,
) -> SeverityRates:
    """Per-game and per-100-user-move rates per severity tier.

    per_game = count / analyzed_n; per_100_moves = count / total_user_moves * 100
    (W2 denominator). Both guard divide-by-zero -> 0.0.
    """
    per_game: dict[FlawSeverity, float] = {}
    per_100: dict[FlawSeverity, float] = {}
    for tier in _SEVERITY_TIERS:
        c = counts[tier]
        per_game[tier] = c / analyzed_n if analyzed_n > 0 else 0.0
        per_100[tier] = c / total_user_moves * _PER_100 if total_user_moves > 0 else 0.0
    return SeverityRates(per_game=per_game, per_100_moves=per_100)


def _build_tag_distribution(
    *,
    mistake_count: int,
    blunder_count: int,
    tempo_low_clock: int,
    tempo_impatient: int,
    tempo_considered: int,
    is_result_changing: int,
    is_miss: int,
    is_lucky_escape: int,
    is_while_ahead: int,
    phase_opening: int,
    phase_middlegame: int,
    phase_endgame: int,
) -> TagDistribution:
    """Build TagDistribution from pre-aggregated game_flaws scan counts (D-02).

    Replaces the per-game FlawRecord loop. Total M+B flaws = mistake + blunder
    (from game_flaws — inaccuracy never stored per D-03). Tempo counts sum to
    <= total M+B because rows with NULL tempo carry no tempo tag (clock-less games).
    The unmeasured remainder (total - sum(tempo)) is preserved by NOT normalizing
    to 100% (flaw-tag-naming.md §"Structural change").
    """
    total_flaws = mistake_count + blunder_count
    rate = is_result_changing / total_flaws if total_flaws > 0 else 0.0
    miss_rate = is_miss / total_flaws if total_flaws > 0 else 0.0
    lucky_escape_rate = is_lucky_escape / total_flaws if total_flaws > 0 else 0.0
    while_ahead_rate = is_while_ahead / total_flaws if total_flaws > 0 else 0.0
    return TagDistribution(
        tempo={
            "low-clock": tempo_low_clock,
            "impatient": tempo_impatient,
            "considered": tempo_considered,
        },
        result_changing_rate=rate,
        phase_histogram={
            "opening": phase_opening,
            "middlegame": phase_middlegame,
            "endgame": phase_endgame,
        },
        miss_rate=miss_rate,
        lucky_escape_rate=lucky_escape_rate,
        while_ahead_rate=while_ahead_rate,
    )


def _compute_trend(
    per_game: list[tuple[datetime.datetime | None, int]],
) -> list[FlawTrendPoint]:
    """Trailing rolling-GAME-window M+B-per-game trend (D3, W5).

    D-02 migration: per_game is now a list of (played_at, mb_count) tuples from
    a game_flaws GROUP BY aggregate (fetch_stats_trend), ordered chronologically.
    Includes analyzed games with zero M+B flaws (mb_count=0) — they anchor the
    rolling window but don't inflate the rate (zero numerator).

    Reuses the get_time_series windowing precedent: a trailing ROLLING_WINDOW_SIZE
    window over the chronological analyzed games, one datapoint per game (deduped
    to the last game per date), dropping early points with fewer than
    MIN_GAMES_FOR_TIMELINE games. Each point's `date` is the played_at date of the
    window's LAST game — a label, NOT a calendar bucket (W5).
    """
    flaws_so_far: list[int] = []  # M+B flaw count per chronological game
    data_by_date: dict[str, FlawTrendPoint] = {}
    for played_at, mb_count in per_game:
        flaws_so_far.append(mb_count)
        window = flaws_so_far[-ROLLING_WINDOW_SIZE:]
        window_total = len(window)
        rate = sum(window) / window_total if window_total > 0 else 0.0
        # Undated games (played_at None) cannot anchor a trend label; skip them.
        if played_at is None:
            continue
        date_label = played_at.strftime("%Y-%m-%d")
        data_by_date[date_label] = FlawTrendPoint(
            date=date_label,
            rate=round(rate, 4),
            game_count=window_total,
            window_size=ROLLING_WINDOW_SIZE,
        )
    return [pt for pt in data_by_date.values() if pt.game_count >= MIN_GAMES_FOR_TIMELINE]


def _empty_stats(total_n: int) -> FlawStatsResponse:
    """Zero-valued stats for an empty analyzed set (never raises)."""
    zero_counts = SeverityCounts(inaccuracy=0, mistake=0, blunder=0)
    return FlawStatsResponse(
        per_severity_counts=zero_counts,
        rates=_compute_rates(zero_counts, 0, 0),
        tag_distribution=_build_tag_distribution(
            mistake_count=0,
            blunder_count=0,
            tempo_low_clock=0,
            tempo_impatient=0,
            tempo_considered=0,
            is_result_changing=0,
            is_miss=0,
            is_lucky_escape=0,
            is_while_ahead=0,
            phase_opening=0,
            phase_middlegame=0,
            phase_endgame=0,
        ),
        trend=[],
        analyzed_pct=0.0,
        analyzed_n=0,
        total_n=total_n,
    )


async def get_flaw_stats(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: list[str] | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> FlawStatsResponse:
    """Stats-panel aggregate over the filtered analyzed-only set (LIBG-09).

    D-02 migration: the per-game kernel re-call loop (_load_analyzed_flaws) is
    retired. Pipeline:
    1. count_filtered_and_analyzed — total_n / analyzed_n (eval-coverage gate).
    2. fetch_stats_aggregates — single game_flaws scan: M+B counts + tag distribution
       aggregates (COUNT(*) FILTER). Inaccuracy stays the cheap aggregate (D-03).
    3. fetch_stats_trend — game_flaws GROUP BY game for the rolling trend.
    4. fetch_total_user_moves — game_positions aggregate for per-100 rate denominator.

    analyzed_n / total_n derive from the eval-coverage subquery — NOT from game_flaws
    row counts (Pitfall 6). An analyzed game with zero M+B flaws counts toward
    analyzed_n. An empty analyzed set returns zeros + empty trend, never raises.
    """
    try:
        total_n, analyzed_n = await library_repository.count_filtered_and_analyzed(
            session,
            user_id=user_id,
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
        if analyzed_n == 0:
            return _empty_stats(total_n)

        # The eval-coverage subquery is needed for all three game_flaws scans below.
        analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)

        _filter_kwargs: dict = dict(
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

        (
            mistake_count,
            blunder_count,
            tempo_low_clock,
            tempo_impatient,
            tempo_considered,
            is_result_changing,
            is_miss,
            is_lucky_escape,
            is_while_ahead,
            phase_opening,
            phase_middlegame,
            phase_endgame,
        ) = await library_repository.fetch_stats_aggregates(
            session, user_id, analyzed_subq, **_filter_kwargs
        )

        trend_data = await library_repository.fetch_stats_trend(
            session, user_id, analyzed_subq, **_filter_kwargs
        )

        total_user_moves = await library_repository.fetch_total_user_moves(
            session, user_id, analyzed_subq, **_filter_kwargs
        )

    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("flaw_stats", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    # Inaccuracy stays the cheap aggregate (D-03) — not from game_flaws.
    # Currently reported as 0 since the oracle columns (white_/black_inaccuracies)
    # use different thresholds (lichess) and the kernel aggregate would require
    # a full game_positions scan per game. D-03 accepted this; the stats panel
    # severity_counts inaccuracy field reflects M+B-only scope of game_flaws.
    counts = SeverityCounts(inaccuracy=0, mistake=mistake_count, blunder=blunder_count)

    return FlawStatsResponse(
        per_severity_counts=counts,
        rates=_compute_rates(counts, analyzed_n, total_user_moves),
        tag_distribution=_build_tag_distribution(
            mistake_count=mistake_count,
            blunder_count=blunder_count,
            tempo_low_clock=tempo_low_clock,
            tempo_impatient=tempo_impatient,
            tempo_considered=tempo_considered,
            is_result_changing=is_result_changing,
            is_miss=is_miss,
            is_lucky_escape=is_lucky_escape,
            is_while_ahead=is_while_ahead,
            phase_opening=phase_opening,
            phase_middlegame=phase_middlegame,
            phase_endgame=phase_endgame,
        ),
        trend=_compute_trend(trend_data),
        analyzed_pct=analyzed_n / total_n if total_n > 0 else 0.0,
        analyzed_n=analyzed_n,
        total_n=total_n,
    )


# ---------------------------------------------------------------------------
# Flaws subtab (Plan 108-05) — GET /api/library/flaws
# ---------------------------------------------------------------------------

# Default severity tiers when none are specified (D-08: M+B only)
_DEFAULT_SEVERITY: list[FlawSeverity] = ["mistake", "blunder"]


async def get_library_flaws(
    session: AsyncSession,
    user_id: int,
    *,
    severity: list[FlawSeverity],
    tags: list[FlawTag],
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None,
    offset: int,
    limit: int,
) -> LibraryFlawsResponse:
    """Paginated per-flaw list for the Flaws subtab (Plan 108-05, D-07/D-08).

    Each row is one flawed position from game_flaws, ordered recent-first
    (g.played_at DESC, f.ply ASC per D-07), with page size 20 per D-08.

    Severity defaults to M+B when unset (D-08). User-scoped (IDOR: user_id
    comes from the authenticated user only — the caller must never derive it
    from a request parameter). Predicate shared with the Games EXISTS filter
    (build_flaw_filter_clauses) to enforce cross-tab unification (SEED-038).

    Args:
        session: AsyncSession for DB access.
        user_id: Authenticated user's ID — always scopes the query (IDOR).
        severity: Severity tiers from the request. Caller defaults to M+B
                  when empty (router) or explicitly defaults here.
        tags: FlawTag values to filter on (phase tags excluded at HTTP layer).
        time_control / platform / rated / opponent_type / from_date / to_date /
          color: Game-metadata filters.
        offset: Pagination offset (>= 0).
        limit: Page size (1..100, default 20 per D-08).
    """
    effective_severity = severity if severity else _DEFAULT_SEVERITY
    try:
        flaws, matched_count = await library_repository.query_flaws(
            session,
            user_id=user_id,
            severity=effective_severity,
            tags=tags,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            color=color,
            offset=offset,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("library_flaws", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    return LibraryFlawsResponse(
        flaws=flaws,
        matched_count=matched_count,
        offset=offset,
        limit=limit,
    )
