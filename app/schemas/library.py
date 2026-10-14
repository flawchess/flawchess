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
from typing import Final, Literal

from pydantic import BaseModel

from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import FlawDeltaMetric, FlawPhaseMetric, FlawTempoMetric
from app.services.tactic_delta_zones import TacticFamily, TacticSide
from app.services.flaws_service import FlawSeverity, FlawTag, SeverityCounts


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
    # Engine's best move FROM the position at this ply (UCI, e.g. "e2e4" / "e7e8q").
    # None for lichess-eval-only games (no PV captured) and the final position.
    best_move: str | None = None
    # Phase 175 (BOARD-01): pre-classified gem/great tier from the authoritative
    # classify_best_move (app.services.best_move_candidates), computed server-side
    # from the stored game_best_moves row. Null when no candidate row exists for
    # this ply OR the row classifies "neither" — the board never does its own
    # cp/margin math for the stored path (D-03).
    # Quick 260717-rbn: widened with two more tiers, both computed live in
    # _build_eval_series (no stored row involved). 'best' = the played move
    # identity-equals the stored game_positions.best_move (out of book, not
    # gem/great). 'good' = the mover-POV expected-score drop is below
    # INACCURACY_DROP (out of book, not best/gem/great) — the same "clean move"
    # convention _run_all_moves_pass already uses for the flaw markers.
    # Precedence (highest wins): gem > great > best > good > null. maia_prob
    # stays None for best/good — it is a gem/great-only rarity stat.
    best_move_tier: Literal["gem", "great", "best", "good"] | None = None
    # Maia policy probability for the popover "X% of rating-peers" stat. Populated
    # ONLY alongside a non-null gem/great best_move_tier — never set from a
    # "neither" row (Pitfall 5, D-03a) nor for best/good (they are not a Maia
    # rarity stat).
    maia_prob: float | None = None


class FlawMarker(BaseModel):
    """One flaw dot for the eval chart — both colors, B/M/I (Phase 109, LIBG-10).

    is_user=True → filled circle (player); is_user=False → hollow circle (opponent).
    tags is empty for inaccuracies (D-03).
    Phase 126 (TACUI-01): tactic chip fields surfaced; None when below
    MIN_TACTIC_CHIP_CONFIDENCE or when tactic column is NULL in DB.
    Phase 128 (D-07/D-10): both orientation column sets exposed orientation-labeled.
    The narration matrix (allowed×is_opponent, missed×is_opponent) is a Phase 129
    concern; 128 just keeps the schema labeled so 129 can apply it.
    """

    ply: int
    severity: FlawSeverity
    tags: list[FlawTag]  # empty for inaccuracies (D-03)
    is_user: bool  # True = filled dot (player), False = hollow dot (opponent)
    move_san: str | None  # SAN of the flawed move (positions[ply].move_san) — tooltip move label
    # allowed_* fields: tactic allowed to the flaw-maker's opponent (refutation PV)
    allowed_tactic_motif: str | None = None  # motif name string, or None when below confidence gate
    allowed_tactic_confidence: int | None = None  # raw confidence int (0-100), or None when gated
    # 0-based ply depth of the allowed tactic; None when its motif chip is hidden.
    allowed_tactic_depth: int | None = None
    # missed_* fields: tactic the flaw-maker missed (the "instead-of" PV, flaw_ply PV)
    missed_tactic_motif: str | None = None  # motif name string, or None when below confidence gate
    missed_tactic_confidence: int | None = None  # raw confidence int (0-100), or None when gated
    # 0-based ply depth of the missed tactic; None when its motif chip is hidden.
    missed_tactic_depth: int | None = None


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
    # Phase 164 additions (SEED-093): nullable Lichess-Blitz-normalized ratings,
    # a pure transform of (platform, time_control_bucket, rating) for Maia ELO
    # slider conditioning. None for correspondence games, chess.com classical,
    # NULL ratings, or NULL time_control_bucket. Raw white_rating/black_rating
    # above stay unchanged — the header keeps showing the real platform rating.
    white_rating_lichess_blitz: int | None = None
    black_rating_lichess_blitz: int | None = None
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
    # Phase 179 additions (SEED-112, D-01): canonical Phase 178 per-color
    # accuracy (0-100), sourced ONLY from Game.white_accuracy/black_accuracy —
    # never the *_accuracy_imported columns. None when not yet computed
    # (e.g. eval-coverage gate not satisfied).
    white_accuracy: float | None = None
    black_accuracy: float | None = None
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
    # Phase 210 (SEED-042): the position `moves` is replayed FROM. Null means the
    # standard start, which is the overwhelming majority. Non-null for chess.com
    # thematic/custom-position games and pasted [SetUp] PGNs — replaying their
    # SANs from the standard start is illegal and used to crash the analysis
    # board outright (Sentry FLAWCHESS-96).
    initial_fen: str | None = None
    # Active eval-job state for the on-demand analyze pill; null when no active job
    # (unanalyzed-and-unqueued, or already analyzed). The partial unique index
    # uq_eval_jobs_game_active guarantees at most one active row per game.
    active_eval_status: Literal["pending", "leased"] | None = None
    # Phase 172 (SEED-106 D-06): 1-based ply depth of the deepest opening-book
    # match, computed on-read from `moves` (no column, no migration/backfill).
    # 0 means no known opening prefix matched. Gates the gem sweep and marks
    # theory plies with the book badge on every surface gems already render.
    opening_ply_count: int = 0


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
    # Engine's best move FROM the pre-flaw decision position at ply=N (UCI, e.g.
    # "e2e4"). None for lichess-eval-only games (no PV captured). The Flaws-tab
    # miniboard draws it as a blue arrow next to the (red) flaw-move arrow.
    best_move: str | None = None
    # Tactic chip fields (Phase 126, TACUI-01; Phase 128 D-07 — both orientation column sets).
    # allowed_*: tactic allowed to flaw-maker's opponent (refutation PV, flaw_ply+1).
    # missed_*:  tactic the flaw-maker missed (the "instead-of" PV, flaw_ply).
    # Each pair is None when below _TACTIC_CHIP_CONFIDENCE_MIN or when the DB column is NULL.
    # Phase 129 applies the narration matrix (orientation × is_opponent_expr) to select
    # which fields to surface in the chip and comparison; 128 just exposes both labeled.
    allowed_tactic_motif: str | None = None
    allowed_tactic_confidence: int | None = None
    # 0-based ply depth of each tactic; None when the corresponding motif chip is
    # hidden (gated identically to *_tactic_motif). Frontend renders depth+1 (1..12)
    # as a badge on the matching miniboard arrow.
    allowed_tactic_depth: int | None = None
    missed_tactic_motif: str | None = None
    missed_tactic_confidence: int | None = None
    missed_tactic_depth: int | None = None


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


class FlawTrendPoint(BaseModel):
    """One ISO-week flaw-trend datapoint (oracle-sourced, per-100-moves macro).

    `date` is the Monday of the ISO week (a label for an ordinal axis, not a calendar
    bucket boundary). blunder/mistake/inaccuracy_rate are the MACRO mean over a trailing
    FLAW_TREND_WINDOW-game window of (oracle_count / user_moves * 100), from the
    games-table oracle columns (NOT game_flaws). games_in_window is the window size
    (<= FLAW_TREND_WINDOW); per_week_games is the games played that ISO week (volume bars).
    """

    date: str
    blunder_rate: float
    mistake_rate: float
    inaccuracy_rate: float
    games_in_window: int
    per_week_games: int


class FlawTrendTc(BaseModel):
    """One time control's Flaws Timeline series (Phase 239 D-00k)."""

    tc: TimeControlBucket
    points: list[FlawTrendPoint]


class FlawStatsResponse(BaseModel):
    """Response for GET /api/library/flaw-stats (LIBG-09, Phase 239 D-00k).

    trend_by_tc: one Flaws Timeline series per time control that has trend points,
        ordered bullet, blitz, rapid, classical; the client picks the selected TC's
        series. Games with a NULL time_control_bucket cannot be placed on the switch
        and are excluded. Empty when there is no analyzed game.
    analyzed_n: analyzed games in the filtered set (the Flaws tab's "no analyzed games"
        probe reads it). The per-TC coverage line reads FlawComparisonTc.analyzed_n /
        total_n instead. trend_window is the rolling window size (games) used for the
        trend chart.

    Phase 239 removed the severity counts, severity rates, tag distribution and pooled
    trend: nothing renders them any more (the tiles read the flaw-comparison bullets).
    """

    trend_by_tc: list[FlawTrendTc]
    trend_window: int
    analyzed_n: int


class FlawBullet(BaseModel):
    """Per-bullet data for one of the 12 flaw-delta metrics (Phase 115, FLAWCMP-01/03)."""

    tag: FlawDeltaMetric
    delta: (
        float | None
    )  # mean per-game delta (per 100 of user's moves); None = both sides zero events
    # 99% CI on delta (per 100 moves, D-14); None for zero-event bullets and below
    # two games (score_confidence.compute_paired_difference_test n-gates).
    ci_low: float | None
    ci_high: float | None
    # Per-player rates (Phase 115 UAT): mean per-game flaw rate per 100 of the
    # user's moves, for player and opponent separately. Both opponent and player
    # counts are normalized by the user's move count per game so that
    # player_rate - opp_rate == delta exactly (the comparison stays paired).
    # None for zero-event bullets.
    player_rate: float | None
    opp_rate: float | None
    # Two-sided p-value vs H0: delta == 0, from the same Wald-z that produces the
    # CI (z = mean / SE, p = erfc(|z| / sqrt(2))). None for zero-event bullets and
    # below CONFIDENCE_MIN_N (10) games (compute_paired_difference_test n-gate).
    p_value: float | None
    player_events: int  # total player-side tag events across analyzed games
    opp_events: int  # total opponent-side tag events across analyzed games
    # Typical-range bounds from the per-zone-TC FLAW_DELTA_ZONES registry: a band
    # symmetric around 0 (±IQR/2 of the measured quartiles, Phase 239 D-15).
    zone_lo: float
    zone_hi: float
    # Always True: every flaw metric has a band. Kept so FlawBullet and TacticBullet
    # share one shape (tactic family-sides without a viable band send False).
    has_zone: bool = True
    # Phase 239 D-14: True when the 99% CI on delta excludes 0. Only a significant cell
    # outside the band gets a red/green verdict; the backend owns the test.
    significant: bool


# FlawTempoMetric / FlawPhaseMetric live in app.services.flaw_delta_zones (the crossed-cell
# zone registry needs them and this module imports from there). Re-exported by import.
# Cell order of FlawComparisonTc.tempo_phase_cells: phase-major (game order), tempo order
# (Clock-card order) inside each phase.
TEMPO_PHASE_TEMPOS: Final[tuple[FlawTempoMetric, ...]] = ("low_clock", "hasty", "unrushed")
TEMPO_PHASE_PHASES: Final[tuple[FlawPhaseMetric, ...]] = (
    "opening",
    "middlegame",
    "endgame_phase",
)


class TempoPhaseCell(BaseModel):
    """One crossed tempo x game-phase cell of the flaw comparison (quick 261014-pb9).

    Counts only flaws carrying BOTH the tempo tag and the phase tag, on the same
    paired per-100-user-moves basis as FlawBullet (same CI, p-value, significance).
    Quick 261014-qj8: 8 of the 9 cells carry a pooled benchmark band from
    TEMPO_PHASE_ZONES (has_zone True, symmetric zone bounds). low_clock x opening is
    degenerate and has none (has_zone False, zone bounds 0). Flaws with NULL tempo (no
    clock data) are in no cell. Deliberately NOT part of FLAW_DELTA_METRICS, which drives
    the 12-bullet zone registry.
    """

    tempo: FlawTempoMetric
    phase: FlawPhaseMetric
    delta: float | None
    ci_low: float | None
    ci_high: float | None
    player_rate: float | None
    opp_rate: float | None
    p_value: float | None
    player_events: int
    opp_events: int
    zone_lo: float
    zone_hi: float
    has_zone: bool
    significant: bool


class FlawComparisonTc(BaseModel):
    """One time control's you-vs-opponent flaw comparison (Phase 239 D-02/D-03).

    tc: the time control bucket these bullets were computed over.
    analyzed_n: analyzed games of this TC after the current filter set.
    total_n: all games of this TC after the current filter set, analyzed or not; the
             coverage denominator of the Flaw Stats basis line (analyzed_n <= total_n).
    below_gate: True when analyzed_n < FLAW_COMPARISON_GATE; the bullets are still
                populated so tiles can show rates (D-03).
    bullets: always the 12 flaw-delta metrics in FLAW_DELTA_METRICS order.
    tempo_phase_cells: always 9 crossed tempo x phase cells, phase-major (opening,
                       middlegame, endgame_phase; low_clock, hasty, unrushed inside each).
                       Computed also below the gate, like bullets.
    """

    tc: TimeControlBucket
    analyzed_n: int
    total_n: int
    below_gate: bool
    bullets: list[FlawBullet]
    tempo_phase_cells: list[TempoPhaseCell]


class FlawComparisonResponse(BaseModel):
    """Response for GET /api/library/flaw-comparison (Phase 115, Phase 239 D-02).

    tcs: one entry per time control that the sidebar time-control filter allows and
         that has at least one analyzed game under the current filters, ordered
         bullet, blitz, rapid, classical. Zero-analyzed TCs are omitted (D-02), so an
         empty list means no analyzed games at all. Below-gate TCs keep their bullets
         (D-03). No request parameter selects a TC: the switch is client-side.
    analyzed_gate: minimum analyzed games per TC (library_service.FLAW_COMPARISON_GATE),
        exposed so the frontend can render "X of N" without hardcoding the gate.
    """

    tcs: list[FlawComparisonTc]
    analyzed_gate: int


# ---------------------------------------------------------------------------
# Phase 126 — Tactic comparison schemas (TACCMP-01/02/03)
# ---------------------------------------------------------------------------


class TacticBullet(BaseModel):
    """Per-family, per-side data for one tactic motif cell (Phase 126, 129, 239).

    Rates are mean tactic counts per 100 games (Phase 239 D-00h): a 1-vs-0 single-game
    difference reads 100.0. The p-value is scale-invariant and unchanged by the scaling.
    Sign convention: positive delta = you have MORE of these tactics than the opponent
    (mirrors FlawBullet; for both Missed and Allowed that is the bad direction).
    """

    family: TacticFamily
    orientation: TacticSide  # missed (you did not play it) or allowed (you let the opponent)
    you_rate: float | None  # mean count per 100 games (player side); None = zero events
    opp_rate: float | None  # mean count per 100 games (opponent side); None = zero events
    delta: float | None  # you_rate - opp_rate per 100 games; None = both sides zero events
    # 99% CI on delta (per 100 games, D-14) and the two-sided p vs H0: delta == 0.
    # None for zero events; the CI below two games and p below CONFIDENCE_MIN_N (10)
    # games (score_confidence.compute_paired_difference_test n-gates).
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    you_events: int  # raw event count (player side)
    opp_events: int  # raw event count (opponent side)
    # Typical-range bounds from the tactic zone registry (per 100 games), via the zone TC
    # (blitz/bullet read rapid, silently): symmetric ±IQR/2 around 0 (D-15).
    # 0.0 / 0.0 / False when the family-side has no viable band.
    zone_lo: float
    zone_hi: float
    has_zone: bool
    # Phase 239 D-14: True when the 99% CI on delta excludes 0. With a band, only a
    # significant cell outside the band gets a red/green verdict; without one
    # (has_zone False, D-16) the cell is judged on this flag alone. The backend owns
    # the test.
    significant: bool


class TacticComparisonTc(BaseModel):
    """One time control's tactic comparison (Phase 239 D-02/D-03).

    tc: the time control bucket these bullets were computed over.
    analyzed_n: analyzed games of this TC after the current filter set.
    below_gate: True when analyzed_n < TACTIC_COMPARISON_GATE; the bullets are still
                populated so the UI can decide what to show (D-03).
    bullets: always 38 entries: every family in FAMILY_TO_MOTIF_INTS order, missed
             before allowed.
    """

    tc: TimeControlBucket
    analyzed_n: int
    below_gate: bool
    bullets: list[TacticBullet]


class TacticComparisonResponse(BaseModel):
    """Response for GET /api/library/tactic-comparison (Phase 126, Phase 239 D-02/D-00h).

    tcs: one entry per time control that the sidebar time-control filter allows and
         that has at least one analyzed game under the current filters, ordered
         bullet, blitz, rapid, classical. Zero-analyzed TCs are omitted, so an empty
         list means no analyzed games at all. Below-gate TCs keep their bullets
         (D-03). No request parameter selects a TC: the switch is client-side.
    Each TC carries all 19 families x 2 sides in fixed FAMILY_TO_MOTIF_INTS order,
    missed before allowed. There is no ranking or top-N selection (D-00h).
    analyzed_gate: minimum analyzed games per TC (library_service.TACTIC_COMPARISON_GATE),
        exposed so the frontend can render "X of N" without hardcoding the gate.
    """

    tcs: list[TacticComparisonTc]
    analyzed_gate: int


# ---------------------------------------------------------------------------
# Phase 135 — Tactic Line Explorer schema
# ---------------------------------------------------------------------------


class TacticLinesResponse(BaseModel):
    """PV walk data for the TacticLineExplorer (Phase 135, Plan 01).

    Both orientations' SAN move lists, raw 0-based depths, motif strings, and
    the decision-position FEN for chess.js board initialization.

    missed_moves: SAN from the decision position (flaw_ply PV). None when
                  game_positions[ply].pv is NULL or unparseable.
    allowed_moves: SAN starting with the flaw move itself (prepended, index 0)
                   then the opponent's refutation PV from game_positions[ply+1].pv.
                   None when game_positions[ply+1].pv is NULL.
    position_fen: full FEN (piece placement + side-to-move from ply parity) for
                  chess.js root board initialization.
    missed_tactic_ply_index: same as missed_depth (no prepend); the SAN ladder
                  uses this to highlight the tactic punchline move.
    allowed_tactic_ply_index: allowed_depth + 1 — allowed_moves prepends the flaw
                  move at index 0, so the refutation punchline lands one index
                  deeper (at flaw_ply+1). The SAN ladder highlights that move.

    Never exposes internal Zobrist hashes (CLAUDE.md V5 / T-135-03).
    """

    # Missed line: SAN from the decision position (flaw_ply PV).
    missed_moves: list[str] | None = None
    missed_depth: int | None = None  # raw 0-based detector-loop index (DB value)
    missed_tactic_ply_index: int | None = None  # same as missed_depth; for SAN ladder highlight
    missed_motif: str | None = None  # TacticMotif name string or None
    # Engine eval of the missed-line root (decision position), white-POV. eval_cp is
    # post-move, so the decision position's eval lives on game_positions[ply-1].
    missed_eval_cp: int | None = None
    missed_eval_mate: int | None = None

    # Allowed line: SAN starting with the flaw move (prepended) then opponent PV.
    allowed_moves: list[str] | None = None
    allowed_depth: int | None = None  # raw 0-based detector-loop index (DB value)
    allowed_tactic_ply_index: int | None = None  # allowed_depth + 1 (flaw prepended)
    allowed_motif: str | None = None  # TacticMotif name string or None
    # Engine eval of the allowed-line root (position after the flaw move), white-POV.
    # That post-flaw position's eval is the post-move eval of the flaw move itself,
    # stored on game_positions[ply].
    allowed_eval_cp: int | None = None
    allowed_eval_mate: int | None = None

    # Decision-position metadata
    position_fen: str  # full FEN (with side-to-move) from game_flaws.fen + ply parity
    flaw_move_san: str | None = None  # move played (game_positions[n].move_san)
    best_move_uci: str | None = None  # engine best move (game_positions[n].best_move)
    flaw_ply: int  # real game ply of the flaw (for move-number labeling in SAN ladder)
    flaw_severity: FlawSeverity  # "mistake" | "blunder" — drives the SAN-ladder flaw-move glyph
