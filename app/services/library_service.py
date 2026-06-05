"""Library (Games-surface) service — Phase 106 (SEED-036, LIBG-08).

Orchestrates GET /api/library/games: the flaw-filtered paginated game archive
where each card carries per-game B/M/I severity counts plus a curated, deduped
set of tag-chips.

Per D1 (locked): counts + chips come from RE-CALLING the Phase 105 kernel per
game on the returned page only (`count_game_severities` for B/M/I incl.
inaccuracy; `classify_game_flaws` for the chip tag set). The kernel re-call
loop runs SEQUENTIALLY on the one AsyncSession — never asyncio.gather (a single
session is not safe for concurrent coroutine use; CLAUDE.md §Critical
Constraints).

Chip curation (SEED-036): aggregate tags to the game level across all
FlawRecords, drop any `phase-*` tag, emit one chip per remaining tag type
(game-level dedupe), in a deterministic order. FlawRecords are already M+B-only,
so inaccuracy-level tags never appear.

chess.com / unanalyzed-lichess games surface the explicit "no engine analysis"
card state (analysis_state="no_engine_analysis", severity_counts=None), never a
false 0/0/0 (LIBG-02).
"""

import datetime
from typing import Literal

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories import library_repository
from app.repositories.flaws_repository import fetch_game_positions_ordered
from app.schemas.library import (
    GameFlawCard,
    LibraryGamesResponse,
    FlawStatsResponse,
    FlawTrendPoint,
    SeverityRates,
    TagDistribution,
)
from app.services.flaws_service import (
    FlawRecord,
    FlawSeverity,
    FlawTag,
    SeverityCounts,
    TempoTag,
    classify_game_flaws,
    count_game_severities,
)
from app.services.openings_service import (
    MIN_GAMES_FOR_TIMELINE,
    ROLLING_WINDOW_SIZE,
    derive_user_result,
)

# Canonical chip order — a subset of flaws_service.FlawTag with all phase-*
# tags removed. Defines the deterministic ordering of curated card chips.
# FlawRecords are M+B-only, so inaccuracy-level tags never reach this list.
_CHIP_ORDER: tuple[FlawTag, ...] = (
    "miss",
    "unpunished",
    "from-winning",
    "result-changing",
    "time-pressure",
    "hasty",
    "knowledge-gap",
)
_PHASE_TAG_PREFIX = "phase-"


def _curate_chips(flaws: list[FlawRecord]) -> list[FlawTag]:
    """Collect a deduped, deterministically-ordered set of card chips.

    Aggregates tags across all of a game's FlawRecords, drops any `phase-*` tag,
    and emits one chip per remaining tag type in _CHIP_ORDER (SEED-036 curation).
    """
    present: set[str] = set()
    for flaw in flaws:
        for tag in flaw["tags"]:
            if not tag.startswith(_PHASE_TAG_PREFIX):
                present.add(tag)
    return [tag for tag in _CHIP_ORDER if tag in present]


async def _build_card(
    session: AsyncSession,
    game: Game,
    user_id: int,
) -> GameFlawCard:
    """Build one GameFlawCard by re-calling the kernel for this game.

    Loads the game's plies once, then derives the B/M/I counts and chip set.
    GameNotAnalyzed (chess.com / unanalyzed lichess) -> no_engine_analysis card
    state with severity_counts=None and chips=[] (never a false 0/0/0).
    """
    positions = await fetch_game_positions_ordered(session, game.id, user_id)
    counts_result = count_game_severities(game, positions)

    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]
    # Both kernel return shapes are TypedDicts (plain dicts at runtime);
    # discriminate on the "reason" key (the GameNotAnalyzed discriminant).
    if "reason" in counts_result:
        severity_counts = None
        chips = []
        analysis_state = "no_engine_analysis"
    else:
        severity_counts = counts_result
        flaws_result = classify_game_flaws(game, positions)
        # classify_game_flaws shares the identical coverage gate, so an
        # analyzed game here always returns a list[FlawRecord].
        flaws = flaws_result if isinstance(flaws_result, list) else []
        chips = _curate_chips(flaws)
        analysis_state = "analyzed"

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
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> LibraryGamesResponse:
    """Return the flaw-filtered paginated games archive (LIBG-08).

    Loads the filtered page via query_filtered_games, then re-calls the Phase 105
    kernel per game (sequentially on the same AsyncSession — NEVER asyncio.gather)
    to attach per-game B/M/I counts and curated chips. The page size is already
    bounded by `limit` (le 100 at the route) so the per-game N+1 re-call loop is
    capped (RESEARCH Pitfall 4).
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
            offset=offset,
            limit=limit,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )

        cards = [await _build_card(session, game, user_id) for game in games]
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
_TEMPO_TAGS: tuple[TempoTag, ...] = ("time-pressure", "hasty", "knowledge-gap")
# game_position.phase ints -> human phase label (Lichess Divider: 0/1/2).
_PHASE_TAG_TO_KEY: dict[FlawTag, Literal["opening", "middlegame", "endgame"]] = {
    "phase-opening": "opening",
    "phase-middlegame": "middlegame",
    "phase-endgame": "endgame",
}
_RESULT_CHANGING_TAG: FlawTag = "result-changing"
_PER_100 = 100.0


class _GameFlaws:
    """Per-analyzed-game aggregation collected by _load_analyzed_flaws.

    Carries the chronological inputs the rate / tag / trend stages need:
    the SeverityCounts (all three tiers, for the I count), the M+B FlawRecords
    (for tags), the user-mover ply count (per-100-moves denominator, W2), and
    the window's most-recent game date (trend label, W5).
    """

    __slots__ = ("counts", "flaws", "user_moves", "played_at")

    def __init__(
        self,
        counts: SeverityCounts,
        flaws: list[FlawRecord],
        user_moves: int,
        played_at: datetime.datetime | None,
    ) -> None:
        self.counts = counts
        self.flaws = flaws
        self.user_moves = user_moves
        self.played_at = played_at


def _count_user_moves(game: Game, positions: list[GamePosition]) -> int:
    """Count the USER's plies among loaded positions (per-100-moves denominator, W2).

    A ply N is the user's when its mover parity matches game.user_color
    (mover = white if N even else black, per the kernel _run_all_moves_pass at
    line 210). ply 0 is the initial position (no move) and is excluded.
    """
    user_color = game.user_color
    total = 0
    for pos in positions:
        if pos.ply < 1:
            continue
        mover = "white" if pos.ply % 2 == 0 else "black"
        if mover == user_color:
            total += 1
    return total


async def _load_analyzed_flaws(
    session: AsyncSession,
    user_id: int,
    game_ids: list[int],
) -> list[_GameFlaws]:
    """Re-call the Phase 105 kernel per analyzed game (SEQUENTIAL on one session).

    For each chronological game id: load its plies once, then derive the
    SeverityCounts (count_game_severities, all three tiers) + M+B FlawRecords
    (classify_game_flaws) + the user-mover ply count. Never asyncio.gather —
    a single AsyncSession is not safe for concurrent coroutine use (CLAUDE.md
    §Critical Constraints). The cost is O(analyzed games) (A4, accepted for v1).

    game_ids are already restricted to the analyzed (>=90% coverage) filtered set,
    so the kernel returns SeverityCounts / list[FlawRecord], never GameNotAnalyzed.
    """
    per_game: list[_GameFlaws] = []
    for game_id in game_ids:
        game = await session.get(Game, game_id)
        # Ownership guard: game_ids already come from the user-scoped analyzed set,
        # but re-assert user_id before reading any game state (T-106-03AC).
        if game is None or game.user_id != user_id:
            continue
        positions = await fetch_game_positions_ordered(session, game_id, user_id)
        counts_result = count_game_severities(game, positions)
        if "reason" in counts_result:
            # Defensive: analyzed_game_ids already excludes unanalyzed games.
            continue
        flaws_result = classify_game_flaws(game, positions)
        flaws = flaws_result if isinstance(flaws_result, list) else []
        per_game.append(
            _GameFlaws(
                counts=counts_result,
                flaws=flaws,
                user_moves=_count_user_moves(game, positions),
                played_at=game.played_at,
            )
        )
    return per_game


def _aggregate_counts(per_game: list[_GameFlaws]) -> SeverityCounts:
    """Sum per-game SeverityCounts (all three tiers) over the analyzed set."""
    total = SeverityCounts(inaccuracy=0, mistake=0, blunder=0)
    for gf in per_game:
        for tier in _SEVERITY_TIERS:
            total[tier] += gf.counts[tier]
    return total


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


def _compute_tag_distribution(per_game: list[_GameFlaws]) -> TagDistribution:
    """Tempo split, result-changing rate, and phase histogram over M+B flaws (W3).

    Each FlawRecord carries exactly one tempo tag and exactly one phase-* tag.
    result_changing_rate = flaws tagged result-changing / total M+B flaws (0.0 when
    there are none). The numerator/denominator are both M+B FlawRecords — the
    inaccuracy count never enters this distribution.
    """
    tempo: dict[TempoTag, int] = {tag: 0 for tag in _TEMPO_TAGS}
    phase_histogram: dict[Literal["opening", "middlegame", "endgame"], int] = {
        "opening": 0,
        "middlegame": 0,
        "endgame": 0,
    }
    total_flaws = 0
    result_changing = 0
    for gf in per_game:
        for flaw in gf.flaws:
            total_flaws += 1
            for tag in flaw["tags"]:
                if tag in _TEMPO_TAGS:
                    tempo[tag] += 1
                elif tag in _PHASE_TAG_TO_KEY:
                    phase_histogram[_PHASE_TAG_TO_KEY[tag]] += 1
                elif tag == _RESULT_CHANGING_TAG:
                    result_changing += 1
    rate = result_changing / total_flaws if total_flaws > 0 else 0.0
    return TagDistribution(
        tempo=tempo,
        result_changing_rate=rate,
        phase_histogram=phase_histogram,
    )


def _compute_trend(per_game: list[_GameFlaws]) -> list[FlawTrendPoint]:
    """Trailing rolling-GAME-window M+B-per-game trend (D3, W5).

    Reuses the get_time_series windowing precedent: a trailing ROLLING_WINDOW_SIZE
    window over the chronological analyzed games, one datapoint per game (deduped
    to the last game per date), dropping early points with fewer than
    MIN_GAMES_FOR_TIMELINE games. Each point's `date` is the played_at date of the
    window's LAST game — a label, NOT a calendar bucket (W5).
    """
    flaws_so_far: list[int] = []  # M+B flaw count per chronological game
    data_by_date: dict[str, FlawTrendPoint] = {}
    for gf in per_game:
        flaws_so_far.append(len(gf.flaws))
        window = flaws_so_far[-ROLLING_WINDOW_SIZE:]
        window_total = len(window)
        rate = sum(window) / window_total if window_total > 0 else 0.0
        # Undated games (played_at None) cannot anchor a trend label; skip them.
        if gf.played_at is None:
            continue
        date_label = gf.played_at.strftime("%Y-%m-%d")
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
        tag_distribution=_compute_tag_distribution([]),
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
) -> FlawStatsResponse:
    """Stats-panel aggregate over the filtered analyzed-only set (LIBG-09).

    Pipeline (split into stage helpers to stay shallow): compute the >=90%-coverage
    denominator + chronological analyzed-game ids (SQL), re-call the kernel per
    analyzed game (D1 pragmatic path), then derive per-severity counts/rates (per
    game + per 100 user-moves, W2), the tag distribution (tempo split, result-
    changing rate W3, phase histogram), and the rolling-GAME-window trend (D3/W5).
    An empty analyzed set returns zeros + empty trend, never raises.
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
        )
        if analyzed_n == 0:
            return _empty_stats(total_n)

        game_ids = await library_repository.analyzed_game_ids(
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
        )
        per_game = await _load_analyzed_flaws(session, user_id, game_ids)
    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("flaw_stats", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    counts = _aggregate_counts(per_game)
    total_user_moves = sum(gf.user_moves for gf in per_game)
    return FlawStatsResponse(
        per_severity_counts=counts,
        rates=_compute_rates(counts, analyzed_n, total_user_moves),
        tag_distribution=_compute_tag_distribution(per_game),
        trend=_compute_trend(per_game),
        analyzed_pct=analyzed_n / total_n if total_n > 0 else 0.0,
        analyzed_n=analyzed_n,
        total_n=total_n,
    )
