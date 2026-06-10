"""Library (Games-surface) schemas — Phase 106 (SEED-036, LIBG-08).

The card payload for the Games subtab: a paginated archive where each game
carries its per-game B/M/I severity counts plus a curated, deduped set of
tag-chips, and an explicit analysis-state so chess.com / unanalyzed-lichess
games surface "no engine analysis" rather than a false 0/0/0 (LIBG-02).

GameFlawCard mirrors GameRecord's fields (so the front-end reuses the same
game-card shape) and never includes any *_hash field (V5 information
disclosure — API responses expose FEN/usernames only, never internal hashes).

Phase 108 Plan 05: FlawListItem + LibraryFlawsResponse for GET /library/flaws.
Per-flaw flat list (one row per flawed position), ordered recent-first
(g.played_at DESC, f.ply), paginated (page size 20 per D-08). Never exposes
internal *_hash columns (CLAUDE.md V5).
"""

import datetime
from typing import Literal

from pydantic import BaseModel

from app.services.flaws_service import FlawSeverity, FlawTag, SeverityCounts, TempoTag


# ---------------------------------------------------------------------------
# Phase 109 eval chart models (LIBG-10) — defined before GameFlawCard so
# the three new fields below resolve without forward references.
# ---------------------------------------------------------------------------


class EvalPoint(BaseModel):
    """One ply's white-perspective ES datapoint for the eval chart line (Phase 109, LIBG-10)."""

    ply: int
    es: float | None  # white-perspective ES in (0,1); null = missing eval
    eval_cp: int | None  # raw cp for tooltip display
    eval_mate: int | None  # signed, white-perspective (positive = White has mate)
    clock_seconds: (
        float | None
    )  # mover's remaining clock AFTER this move; null = no %clk (chess.com)
    move_seconds: float | None  # time spent on this move (1dp); null when prior clock unknown


class FlawMarker(BaseModel):
    """One flaw dot for the eval chart — both colors, B/M/I (Phase 109, LIBG-10).

    is_user=True → filled circle (player); is_user=False → hollow circle (opponent).
    tags is empty for inaccuracies (D-03).
    """

    ply: int
    severity: FlawSeverity
    tags: list[FlawTag]  # empty for inaccuracies (D-03)
    is_user: bool  # True = filled dot (player), False = hollow dot (opponent)
    move_san: str | None  # SAN of the flawed move (positions[ply].move_san) — tooltip move label


class PhaseTransitions(BaseModel):
    """First ply of middlegame and endgame phases — at most two phase lines (Phase 109, D-06)."""

    middlegame_ply: int | None  # None = middlegame never reached
    endgame_ply: int | None  # None = endgame never reached


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
    ply_count: int | None
    termination: str | None = None
    time_control_str: str | None = None
    result_fen: str | None = None
    # Phase 106 additions:
    # severity_counts is None (never 0/0/0) for unanalyzed games — discriminated
    # by analysis_state.
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]
    # Phase 109 additions — null for unanalyzed games (analysis_state === 'no_engine_analysis'):
    eval_series: list[EvalPoint] | None = None
    flaw_markers: list[FlawMarker] | None = None
    phase_transitions: PhaseTransitions | None = None
    # SAN mainline (one entry per ply, ordered) for client-side per-ply board
    # reconstruction on eval-chart hover. moves[i] is the move played at ply i, so
    # replaying moves[0..i] yields the position whose eval is eval_series[i].es.
    # Null for unanalyzed games / games without positions.
    moves: list[str] | None = None


class FlawListItem(BaseModel):
    """One row in the Flaws subtab — one flawed position (Plan 108-05, D-07/D-08).

    Carries the full display payload for the miniboard list: board position,
    marked move, severity, reconstructed tags (from typed game_flaws columns),
    before/after raw eval (from game_positions join), and the game metadata
    needed for the row header (opponent, ratings, date, result).

    Phase 112 (SC-2 + SC-4): adds white_rating/black_rating and before/after
    eval fields (eval_cp/eval_mate); drops es_before/es_after (now dead — D-07).
    move_san is now join-sourced from game_positions (D-08).
    Never exposes *_hash fields (CLAUDE.md V5).
    """

    game_id: int
    ply: int
    fen: str
    move_san: str | None  # from game_positions join at ply=N (D-08, Phase 112)
    severity: FlawSeverity  # "mistake" | "blunder" (M+B only, D-03)
    tags: list[FlawTag]  # reconstructed from typed columns in deterministic order
    # Before/after eval from game_positions join (D-05, Phase 112).
    # eval_cp_before / eval_mate_before: game_positions at ply=N-1 (white-POV).
    # eval_cp_after  / eval_mate_after:  game_positions at ply=N   (white-POV).
    # All nullable: LEFT JOIN; ply=0 has no ply-1 row; chess.com has no eval.
    eval_cp_before: int | None
    eval_mate_before: int | None
    eval_cp_after: int | None
    eval_mate_after: int | None
    # Player ratings from the games join (D-03, Phase 112).
    white_rating: int | None
    black_rating: int | None
    # Game metadata for the row header
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    # Game-info line parity with the Games card (raw TC string, ply count,
    # termination reason). All from the games join; nullable like the source rows.
    time_control_str: str | None
    ply_count: int | None
    termination: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    user_color: str
    # Clock context for the flaw card (plan 260610-vru).
    # clock_seconds: mover's remaining clock AFTER the flawed move; null = no %clk (chess.com).
    # move_seconds: time spent on the flawed move (1dp); null when prior clock unknown.
    clock_seconds: float | None
    move_seconds: float | None


class LibraryFlawsResponse(BaseModel):
    """Response for GET /api/library/flaws — paginated per-flaw list (Plan 108-05).

    Mirrors LibraryGamesResponse's pagination shape (flaws / matched_count /
    offset / limit). matched_count reflects all matching flaw rows before
    pagination (not a game count — one game may contribute multiple rows).
    """

    flaws: list[FlawListItem]
    matched_count: int
    offset: int
    limit: int


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

    tempo                 = count of each tempo tag (at most one per flaw). Tempo
                            counts sum to <= M+B flaws because flaws with unavailable
                            clock data carry no tempo tag. The Flaw-Stats panel must
                            show the unmeasured remainder (total M+B - sum(tempo))
                            rather than normalizing the three measured segments to 100%
                            (per flaw-tag-naming.md §"Structural change").
    phase_histogram       = count of flaws in each game phase (each flaw carries
                            exactly one phase tag).
    miss_rate             = miss M+B flaws / total M+B flaws; 0.0 when there are
                            no M+B flaws. (D-01, Phase 107)
    lucky_rate     = lucky M+B flaws / total M+B flaws; 0.0 when
                            there are no M+B flaws. (D-01, Phase 107)
    reversed_rate         = reversed M+B flaws / total M+B flaws; 0.0 when there
                            are no M+B flaws. (Phase 110, D-03)
    squandered_rate       = squandered M+B flaws / total M+B flaws; 0.0 when there
                            are no M+B flaws. (Phase 110, D-03)
    """

    tempo: dict[TempoTag, int]
    phase_histogram: dict[Literal["opening", "middlegame", "endgame"], int]
    # D-01: Opportunity and Impact rates.
    # Each = count / total M+B flaws; 0.0 when there are no M+B flaws.
    # Flat floats (no nested dicts).
    miss_rate: float
    lucky_rate: float
    reversed_rate: float
    squandered_rate: float


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
