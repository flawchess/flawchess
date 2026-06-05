"""Library (Games-surface) schemas — Phase 106 (SEED-036, LIBG-08).

The card payload for the Games subtab: a paginated archive where each game
carries its per-game B/M/I severity counts plus a curated, deduped set of
tag-chips, and an explicit analysis-state so chess.com / unanalyzed-lichess
games surface "no engine analysis" rather than a false 0/0/0 (LIBG-02).

GameFlawCard mirrors GameRecord's fields (so the front-end reuses the same
game-card shape) and never includes any *_hash field (V5 information
disclosure — API responses expose FEN/usernames only, never internal hashes).
"""

import datetime
from typing import Literal

from pydantic import BaseModel

from app.services.flaws_service import FlawSeverity, FlawTag, SeverityCounts, TempoTag


class GameFlawCard(BaseModel):
    """A single game card for the Games subtab archive (LIBG-08).

    Mirrors GameRecord's display fields, extended with per-game severity counts,
    curated tag-chips, and an analysis state. Never exposes internal hashes.
    """

    game_id: int
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    white_rating: int | None
    black_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    user_color: str
    move_count: int | None
    termination: str | None = None
    time_control_str: str | None = None
    result_fen: str | None = None
    # Phase 106 additions:
    # severity_counts is None (never 0/0/0) for unanalyzed games — discriminated
    # by analysis_state.
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]


class LibraryGamesResponse(BaseModel):
    """Response for GET /api/library/games — paginated game archive (LIBG-08).

    Mirrors EndgameGamesResponse's pagination shape (games / matched_count /
    offset / limit); matched_count reflects all matching games before pagination.
    """

    games: list[GameFlawCard]
    matched_count: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Stats panel schemas (LIBG-09) — GET /api/library/flaw-stats
# ---------------------------------------------------------------------------


class SeverityRates(BaseModel):
    """Per-severity rates normalized two ways over the filtered analyzed-only set.

    per_game        = severity_count / analyzed_n (flaws per analyzed game).
    per_100_moves   = severity_count / total_user_moves * 100 (W2: the denominator
                      is the count of the USER's plies across the analyzed set, not
                      the count of severity events nor both colors' plies).

    Both dicts are keyed by FlawSeverity (inaccuracy/mistake/blunder). The
    inaccuracy figures come from count_game_severities (all three tiers), never
    from the M+B FlawRecord set.
    """

    per_game: dict[FlawSeverity, float]
    per_100_moves: dict[FlawSeverity, float]


class TagDistribution(BaseModel):
    """Tag distribution over the analyzed-set M+B FlawRecords (LIBG-09).

    tempo                 = count of each tempo tag (each flaw carries exactly one).
    result_changing_rate  = result-changing M+B flaws / total M+B flaws (W3); 0.0
                            when there are no M+B flaws.
    phase_histogram       = count of flaws in each game phase (each flaw carries
                            exactly one phase-* tag).
    """

    tempo: dict[TempoTag, int]
    result_changing_rate: float
    phase_histogram: dict[Literal["opening", "middlegame", "endgame"], int]


class FlawTrendPoint(BaseModel):
    """One rolling-GAME-window trend datapoint (D3, W5).

    `date` is a LABEL only: the played_at date of the LAST (most recent) game in
    the trailing window — NOT a calendar bucket boundary. `rate` is the mistakes+
    blunders per game over the window.
    """

    date: str
    rate: float
    game_count: int
    window_size: int


class FlawStatsResponse(BaseModel):
    """Response for GET /api/library/flaw-stats (LIBG-09).

    Stats over the filtered analyzed-only set. analyzed_pct / analyzed_n / total_n
    state the explicit >=90%-coverage denominator so the panel never implies clean
    games where evals are merely absent (criterion 4).
    """

    per_severity_counts: SeverityCounts
    rates: SeverityRates
    tag_distribution: TagDistribution
    trend: list[FlawTrendPoint]
    analyzed_pct: float
    analyzed_n: int
    total_n: int
