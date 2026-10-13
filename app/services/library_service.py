"""Library (Games-surface) service — Phase 106 (SEED-036, LIBG-08).

Phase 108 D-02 migration: GET /library/games and GET /library/flaw-stats now
read M+B flaws from `game_flaws` instead of re-calling the Phase 105 kernel
per query. The per-game N+1 `_load_analyzed_flaws` loop is retired.

Games card chips (curated/deduped M+B tags) and per-game M+B severity counts
come from a single batched `game_flaws` read for the whole page. Inaccuracy
counts come from the oracle columns (games.white_/black_inaccuracies) — never
from game_flaws (D-03). Analysis state ("no engine analysis") is determined by
the eval-coverage gate on game_positions (not by game_flaws row presence).

Flaw-stats (Phase 239) returns the coverage counts plus a per-time-control Flaws
Timeline. The analyzed_n/total_n denominator stays on the eval-coverage gate — a
game analyzed with zero M+B flaws still counts toward analyzed_n (Pitfall 6/RESEARCH §7).

Chip curation (SEED-036): aggregate tags to the game level across all game_flaws
rows, drop any phase tag (opening/middlegame/endgame), emit one chip per
remaining tag type (game-level dedupe), in a deterministic order.
"""

import datetime
import math
from collections.abc import Sequence
from typing import Any, Final, Literal, cast

import chess
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_best_move import GameBestMove
from app.models.game_flaw import GameFlaw
from app.repositories import library_repository
from app.repositories.library_repository import (
    TacticOrientation,
    _TACTIC_CHIP_CONFIDENCE_MIN,
    _TEMPO_INT_TO_TAG,
    is_decided_lost,
    tactic_slot_visible,
)
from app.repositories.query_utils import ANALYTICS_INCLUDED_PLATFORMS, mover_is_white_at_ply
from app.services.tactic_detector import _INT_TO_MOTIF as _TACTIC_INT_TO_MOTIF
from app.schemas.library import (
    FlawBullet,
    FlawComparisonResponse,
    FlawComparisonTc,
    FlawStatsResponse,
    FlawTrendPoint,
    FlawTrendTc,
    GameFlawCard,
    LibraryFlawsResponse,
    LibraryGamesResponse,
    TacticBullet,
    TacticComparisonResponse,
    TacticComparisonTc,
)
from app.services.best_move_candidates import classify_best_move, mover_color_for_ply
from app.services.flaw_delta_zones import FLAW_DELTA_METRICS, FlawDeltaMetric, flaw_delta_zone
from app.services.score_confidence import VERDICT_CI_Z_99, ci_excludes
from app.services.tactic_delta_zones import (
    TACTIC_FAMILIES,
    TacticFamily,
    TacticSide,
    tactic_delta_zone,
)
from app.models.game_position import GamePosition
from app.schemas.library import EvalPoint, FlawMarker, PhaseTransitions
from app.services.eval_utils import (
    derive_is_lichess_eval_game,
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.flaws_service import (
    FlawSeverity,
    FlawTag,
    SeverityCounts,
    _MoveEntry,
    _build_tags,
    _resolve_increment,
    _run_all_moves_pass,
)
from app.schemas.normalization import Platform, TimeControlBucket
from app.services.chesscom_to_lichess import normalize_to_lichess_blitz
from app.services.normalization import is_correspondence_time_control
from app.services.opening_lookup import find_opening_ply_count
from app.services.openings_service import (
    MIN_GAMES_FOR_TIMELINE,
    derive_user_result,
)

# ---------------------------------------------------------------------------
# Phase 109 eval chart helpers (LIBG-10) — Task 1 stubs, Task 2 implements
# ---------------------------------------------------------------------------

# Tags that are user-framed and must be stripped from opponent flaw markers (D-03).
_USER_FRAMED_TAGS: frozenset[FlawTag] = frozenset({"miss", "lucky"})


# Per-ply tactic chip + depth payload for FlawMarkers (gated, both orientations):
# (allowed_motif, allowed_conf, allowed_depth, missed_motif, missed_conf, missed_depth).
_TacticByPlyEntry = tuple[str | None, int | None, int | None, str | None, int | None, int | None]


def _derive_phase_transitions(positions: list[GamePosition]) -> PhaseTransitions:
    """First ply of middlegame (phase==1) and endgame (phase==2), first occurrence wins.

    Quick 260714-rj5: extracted from _build_eval_series's main loop so there is
    ONE derivation, not two — an unanalyzed card (no eval_series) still needs
    phase_transitions to render the board's phase markers. No ply-0 transition
    (D-06): ply 0 is the initial position, not a transition.
    """
    middlegame_ply: int | None = None
    endgame_ply: int | None = None
    for pos in positions:
        if pos.phase == 1 and middlegame_ply is None and pos.ply > 0:
            middlegame_ply = pos.ply
        elif pos.phase == 2 and endgame_ply is None and pos.ply > 0:
            endgame_ply = pos.ply
    return PhaseTransitions(middlegame_ply=middlegame_ply, endgame_ply=endgame_ply)


def _best_move_identity_plies(positions: list[GamePosition]) -> set[int]:
    """Plies where the played move identity-equals the stored engine best_move.

    Quick 260717-rbn (Task 1): replays ONE chess.Board() over `positions` in ply
    order. For each position with a move played, parses it via
    board.parse_san(pos.move_san) on the PRE-move board and compares it by
    Move-object equality to chess.Move.from_uci(pos.best_move) — never a raw
    SAN==UCI string compare (they use different notations). Wrapped in
    try/except mirroring _same_dest_as_best_line's guard posture: a malformed
    SAN/UCI stops the replay early and returns the plies collected so far,
    since the board state can no longer be trusted past that point.
    """
    identity_plies: set[int] = set()
    board = chess.Board()
    try:
        for pos in positions:
            if pos.move_san is None:
                continue
            played_move = board.parse_san(pos.move_san)
            if pos.best_move is not None and played_move == chess.Move.from_uci(pos.best_move):
                identity_plies.add(pos.ply)
            board.push(played_move)
    except ValueError, chess.IllegalMoveError:
        return identity_plies
    return identity_plies


def _build_eval_series(
    game: Game,
    positions: list[GamePosition],
    tactic_by_ply: dict[int, _TacticByPlyEntry] | None = None,
    best_moves_by_ply: dict[int, GameBestMove] | None = None,
    opening_ply_count: int = 0,
) -> tuple[list[EvalPoint], list[FlawMarker], PhaseTransitions]:
    """Compute white-perspective ES line, flaw markers, and phase transitions.

    Line perspective: white-perspective (eval_mate_to_expected_score/eval_cp_to_expected_score
    called with "white"). Flaw detection perspective: mover-POV drops via
    _run_all_moves_pass (D-01/D-04). No DB access — positions are pre-fetched
    by get_library_games (D-10: single batched query, no N+1).

    Args:
        game: Game row with user_color, result, base_time_seconds, increment_seconds.
        positions: All GamePosition rows for this game, ordered by ply ASC.
        tactic_by_ply: Optional dict mapping ply → (allowed_motif, allowed_conf,
                       allowed_depth, missed_motif, missed_conf, missed_depth) for
                       tactic chip + depth data on FlawMarkers.
                       Sourced from game_flaws rows (Phase 126, TACUI-01 single-game
                       card; Phase 128 D-07 extends to both orientation column sets).
                       None = no tactic chip data (default, preserves backward compat).
                       Each motif/conf pair is None when below _TACTIC_CHIP_CONFIDENCE_MIN
                       or when the DB column is NULL.
        best_moves_by_ply: Optional dict mapping ply -> GameBestMove candidate row
                       (Phase 175, BOARD-01). None/missing entry -> EvalPoint.
                       best_move_tier/maia_prob stay null (a stored row is not
                       automatically a marker — Pitfall 3 — classify_best_move is
                       always called on the raw floats). maia_prob is populated
                       ONLY when the tier is not "neither" (Pitfall 5).
        opening_ply_count: 1-based ply depth of the deepest opening-book match
                       (Quick 260717-rbn), computed by the caller via
                       find_opening_ply_count BEFORE calling this function.
                       Gates the new best/good tiers to out-of-book plies
                       (pos.ply >= opening_ply_count) — book/theory plies never
                       get a best/good label. Defaults to 0 (no book gate).

    Returns:
        (eval_series, flaw_markers, phase_transitions) tuple where:
        - eval_series: white-perspective ES per ply (es=None for missing eval, D-05)
        - flaw_markers: both-color B/M/I dots with is_user discriminator (D-01/D-07)
        - phase_transitions: first ply of middlegame (phase==1) and endgame (phase==2) (D-06)
    """
    all_moves = _run_all_moves_pass(positions)
    # Quick 260717-rbn (Task 1): plies where the played move identity-equals the
    # stored engine best_move — the noise-immune basis for the 'best' tier.
    identity_plies = _best_move_identity_plies(positions)
    eval_series: list[EvalPoint] = []
    flaw_markers: list[FlawMarker] = []

    # Increment for _build_tags tempo computation (Phase 109: shared helper).
    increment = _resolve_increment(game)

    # Bug fix: daily (chess.com) and correspondence (lichess) games emit %clk
    # annotations but the values are meaningless — witnessed e.g. for game id 687474
    # (user 28) where clocks jump 0.7s → 21.3s → 1008s → 90s across consecutive
    # moves. Suppress clock_seconds and move_seconds at the display layer so the
    # frontend's != null guards hide the nonsensical numbers. Storage is untouched
    # (game_positions.clock_seconds feeds time-management stats, out of scope).
    is_correspondence = is_correspondence_time_control(game.time_control_str)

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
        # Correspondence/daily: force clock to None so both clock_seconds and the
        # derived move_seconds are None — per-move %clk values are meaningless for
        # these games (see is_correspondence comment above).
        clock = None if is_correspondence else pos.clock_seconds
        move_seconds: float | None = None
        if clock is not None:
            prior = prev_clock[color]
            if prior is not None:
                move_seconds = round(max(0.0, prior - clock + increment), 1)
            prev_clock[color] = clock

        # Phase 175 (BOARD-01): pre-classified gem/great tier from the stored
        # game_best_moves row, via the SAME authoritative classify_best_move the
        # FILT-01 filter's SQL twin agrees with (D-03b). Row presence alone is
        # NEVER the marker (Pitfall 3) — classify_best_move is always called on
        # the raw floats; a [0.05, 0.10) margin row classifies "neither" here.
        best_move_tier: Literal["gem", "great", "best", "good"] | None = None
        best_move_maia_prob: float | None = None
        best_row = best_moves_by_ply.get(pos.ply) if best_moves_by_ply else None
        if best_row is not None:
            tier = classify_best_move(
                best_row.maia_prob,
                best_row.best_cp,
                best_row.best_mate,
                best_row.second_cp,
                best_row.second_mate,
                mover_color_for_ply(pos.ply),
                # Imported-eval divergence guard (Quick 260717-gmg): pos.eval_cp is
                # lichess's authoritative post-move %eval for a lichess-eval game;
                # suppress the badge when our best_cp overrates it. Since played ==
                # best for every candidate, pos.eval_cp describes the same resulting
                # position as best_cp (both post-best-move). Phase 212 D-03: routed
                # through the single derivation point -- under
                # BENCHMARK_HOMOGENIZE_EVAL_SOURCE, pos.eval_cp holds OUR engine's
                # value while lichess_evals_at deliberately stays set (D-04), so
                # the guard's "pos.eval_cp is lichess's %eval" premise no longer
                # holds and this read must follow the homogenized boolean, not the
                # raw timestamp.
                post_move_cp=pos.eval_cp,
                post_move_mate=pos.eval_mate,
                is_lichess_eval_game=derive_is_lichess_eval_game(game.lichess_evals_at),
            )
            if tier != "neither":
                best_move_tier = tier
                # Pitfall 5: maia_prob populated ONLY alongside a non-null tier.
                best_move_maia_prob = best_row.maia_prob

        # Quick 260717-rbn (Task 1): 'best'/'good' tiers, computed live (no
        # stored row involved). Precedence gem > great > best > good > null —
        # only applied when gem/great left best_move_tier unset. Gated to
        # out-of-book plies (pos.ply >= opening_ply_count) with a move played.
        # 'best': the played move identity-equals the stored engine best_move
        # (noise-immune — the identity_plies replay). 'good': the mover-POV ES
        # drop is below INACCURACY_DROP — read from the SAME all_moves dict the
        # flaw markers below use (all_moves[pos.ply] describes the quality of
        # pos.move_san per the post-move eval convention documented on
        # _run_all_moves_pass), not recomputed.
        if best_move_tier is None and pos.move_san is not None and pos.ply >= opening_ply_count:
            if pos.ply in identity_plies:
                best_move_tier = "best"
            else:
                entry_for_tier = all_moves.get(pos.ply)
                if entry_for_tier is not None and entry_for_tier[1] is None:
                    best_move_tier = "good"

        eval_series.append(
            EvalPoint(
                ply=pos.ply,
                es=round(es, 3) if es is not None else None,
                eval_cp=pos.eval_cp,
                eval_mate=pos.eval_mate,
                clock_seconds=clock,
                move_seconds=move_seconds,
                # Engine best move FROM this position (NULL for lichess-eval-only games).
                best_move=pos.best_move,
                best_move_tier=best_move_tier,
                maia_prob=best_move_maia_prob,
            )
        )

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
        # Phase 126 (TACUI-01): tactic chip fields from pre-fetched game_flaws data.
        # Phase 128 D-07: both orientation column sets on FlawMarker (orientation-labeled).
        tac_allowed_motif: str | None = None
        tac_allowed_conf: int | None = None
        tac_allowed_depth: int | None = None
        tac_missed_motif: str | None = None
        tac_missed_conf: int | None = None
        tac_missed_depth: int | None = None
        if tactic_by_ply is not None:
            tac_entry = tactic_by_ply.get(pos.ply)
            if tac_entry is not None:
                (
                    tac_allowed_motif,
                    tac_allowed_conf,
                    tac_allowed_depth,
                    tac_missed_motif,
                    tac_missed_conf,
                    tac_missed_depth,
                ) = tac_entry
        flaw_markers.append(
            FlawMarker(
                ply=pos.ply,
                severity=severity,
                tags=tags,
                is_user=is_user,
                move_san=pos.move_san,
                allowed_tactic_motif=tac_allowed_motif,
                allowed_tactic_confidence=tac_allowed_conf,
                allowed_tactic_depth=tac_allowed_depth,
                missed_tactic_motif=tac_missed_motif,
                missed_tactic_confidence=tac_missed_conf,
                missed_tactic_depth=tac_missed_depth,
            )
        )

    # Checkmate: lichess emits no %eval once the game is over, so the mating move's
    # resulting position has es=None, which breaks the chart line at the mate. The
    # mate is decisive on the board, so set the mating ply's es to 1.0/0.0
    # (white-perspective) from the mating side's color (ply parity: even=White) and
    # make the chart END on the mate by nulling every ply after it: the trailing
    # terminal position (move_san=None) is not a real move and would otherwise show
    # as a stray "Ply N · Eval: —" point (or carry a bogus `eval_mate=0` annotation
    # that maps to 0.0 regardless of winner). Frontend trims the nulled tail. Only
    # the final move can be mate, so there is at most one '#'. Non-checkmate
    # terminations (resignation, timeout) have no '#' and are left untouched.
    mate_idx = next(
        (i for i, pos in enumerate(positions) if (pos.move_san or "").endswith("#")),
        None,
    )
    if mate_idx is not None:
        eval_series[mate_idx].es = 1.0 if positions[mate_idx].ply % 2 == 0 else 0.0
        for point in eval_series[mate_idx + 1 :]:
            point.es = None

    return (
        eval_series,
        flaw_markers,
        _derive_phase_transitions(positions),
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

    Impact tags (reversed/squandered) are outcome-independent (mover-relative by
    definition). Flips user_result to opponent's perspective for lucky
    (_is_unpunished). Strips 'miss' and 'lucky' which are user-framed
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
    "lucky",
    "reversed",
    "squandered",
    "low-clock",
    "hasty",
    "unrushed",
)


def _curate_chips_from_rows(flaw_rows: list[GameFlaw]) -> list[FlawTag]:
    """Collect a deduped, deterministically-ordered set of card chips from game_flaws rows.

    Aggregates non-phase tags across all of a game's game_flaws rows:
    - Boolean columns: is_miss, is_lucky, is_reversed, is_squandered
    - Tempo column: _TEMPO_INT_TO_TAG lookup (None → skip)
    Phase tags are excluded (opening/middlegame/endgame per _CHIP_ORDER curation).
    One chip per remaining tag type (game-level dedupe), in _CHIP_ORDER (SEED-036).
    """
    present: set[FlawTag] = set()
    for row in flaw_rows:
        if row.is_miss:
            present.add("miss")
        if row.is_lucky:
            present.add("lucky")
        if row.is_reversed:
            present.add("reversed")
        if row.is_squandered:
            present.add("squandered")
        if row.tempo is not None:
            tempo_tag = _TEMPO_INT_TO_TAG.get(row.tempo)
            if tempo_tag is not None:
                present.add(tempo_tag)
    return [tag for tag in _CHIP_ORDER if tag in present]


def _build_tactic_by_ply_entry(
    fr: GameFlaw, pos_by_ply: dict[int, GamePosition]
) -> tuple[int, _TacticByPlyEntry] | None:
    """Compute one row's tactic-by-ply entry, or `None` if neither slot is visible.

    Extracted from `_build_card`'s per-row tactic-slot loop (216-06, zero
    behavior change): the decided-lost lookup, both `tactic_slot_visible`
    gates, and the motif/confidence/depth resolution for the allowed and
    missed slots are exactly as the inline code it replaces. Visibility
    gating is preserved exactly -- a slot becoming visible when it previously
    was not would be a user-visible change.
    """
    prev_pos = pos_by_ply.get(fr.ply - 1)
    fr_decided_lost = is_decided_lost(
        prev_pos.eval_cp if prev_pos else None,
        prev_pos.eval_mate if prev_pos else None,
        mover_is_white=mover_is_white_at_ply(fr.ply),
    )
    allowed_visible = tactic_slot_visible(
        fr.allowed_tactic_motif,
        fr.allowed_tactic_confidence,
        fr.allowed_tactic_depth,
        orientation_kind="allowed",
        tactic_families=(),
        tactic_orientation="either",
        min_tactic_depth=None,
        max_tactic_depth=None,
        decided_lost=fr_decided_lost,
    )
    allowed_motif_str: str | None = None
    allowed_conf_val: int | None = None
    allowed_depth_val: int | None = None
    if allowed_visible and fr.allowed_tactic_motif is not None:
        allowed_motif_str = _TACTIC_INT_TO_MOTIF.get(fr.allowed_tactic_motif)
        if allowed_motif_str is not None:
            allowed_conf_val = fr.allowed_tactic_confidence
            allowed_depth_val = fr.allowed_tactic_depth

    missed_visible = tactic_slot_visible(
        fr.missed_tactic_motif,
        fr.missed_tactic_confidence,
        fr.missed_tactic_depth,
        orientation_kind="missed",
        tactic_families=(),
        tactic_orientation="either",
        min_tactic_depth=None,
        max_tactic_depth=None,
        decided_lost=fr_decided_lost,
    )
    missed_motif_str: str | None = None
    missed_conf_val: int | None = None
    missed_depth_val: int | None = None
    if missed_visible and fr.missed_tactic_motif is not None:
        missed_motif_str = _TACTIC_INT_TO_MOTIF.get(fr.missed_tactic_motif)
        if missed_motif_str is not None:
            missed_conf_val = fr.missed_tactic_confidence
            missed_depth_val = fr.missed_tactic_depth

    if allowed_motif_str is None and missed_motif_str is None:
        return None

    return (
        fr.ply,
        (
            allowed_motif_str,
            allowed_conf_val,
            allowed_depth_val,
            missed_motif_str,
            missed_conf_val,
            missed_depth_val,
        ),
    )


def _build_card(
    game: Game,
    flaw_rows: list[GameFlaw],
    is_analyzed: bool,
    positions: list[GamePosition],
    active_eval_status: Literal["pending", "leased"] | None = None,
    *,
    tactic_flaw_rows: list[GameFlaw] | None = None,
    best_moves_by_ply: dict[int, GameBestMove] | None = None,
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
    populated via _build_eval_series. Unanalyzed games always get None for
    eval_series/flaw_markers (no evals exist to synthesize). Quick 260714-rj5:
    when positions are provided for an unanalyzed game (single-game path only),
    moves and phase_transitions ARE populated — they derive from move_san/phase
    on game_positions, not from evals, so an unanalyzed game can still render a
    navigable board.

    Quick 260702-mnd: the card now surfaces every valid tactic slot regardless of
    the active tactic/severity filter — a selected card is a complete picture of
    that game's flaws, consistent with the context chips (which already ignore
    every filter, see _curate_chips_from_rows). Game SELECTION (which games
    appear at all) is still enforced upstream by query_filtered_games; this
    function only decides which tags render on an already-selected card. The two
    validity gates that remain are: (1) decided_lost — the pre-move position was
    not already decisively lost for the mover, and (2) the confidence floor
    (_TACTIC_CHIP_CONFIDENCE_MIN, inside tactic_slot_visible). Both gate
    correctness/noise, not filter membership.

    Quick 260628-u7d: tactic_flaw_rows is a both-color (ungated) row list used
    ONLY to populate the per-ply tactic map for eval-chart tooltips — it may
    include opponent rows. When None, falls back to flaw_rows so any other caller
    keeps exact existing behavior. severity_counts, chips, and all stats still
    iterate flaw_rows (player-gated) and are byte-for-byte unchanged.
    """
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]

    if not is_analyzed:
        severity_counts = None
        chips = []
        analysis_state = "no_engine_analysis"
        # Quick 260714-rj5: unanalyzed games have no evals — do NOT synthesize an
        # all-None eval series — but moves come from game_positions.move_san and
        # do NOT depend on evals, so an unanalyzed game can still render a
        # navigable board (fixes the empty-board dead end for unanalyzed/pending
        # games). get_library_game now always fetches positions; get_library_games
        # keeps its analyzed-only positions gate, so positions is [] there.
        eval_series_data = None
        flaw_marker_data = None
        phase_transition_data = _derive_phase_transitions(positions) if positions else None
        moves_data = (
            [p.move_san for p in positions if p.move_san is not None] if positions else None
        )
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
            # Quick 260702-mnd: build tactic_by_ply via the shared per-slot predicate
            # (tactic_slot_visible), called with filter-neutral arguments so it only
            # applies the two validity gates (decided_lost + confidence floor) — no
            # filter/severity pruning. Game SELECTION is enforced upstream by
            # query_filtered_games (D-1: the severity gate that used to live here is
            # removed too, matching the context chips which never pruned by severity).
            # Build a ply → GamePosition index once for decided-lost lookups (per-row ply N-1).
            # Quick 260628-u7d: tactic_flaw_rows may include opponent rows (both movers),
            # so mover_is_white is derived per-ply instead of assuming mover == user.
            pos_by_ply: dict[int, GamePosition] = {p.ply: p for p in positions}
            tactic_by_ply: dict[int, _TacticByPlyEntry] = {}
            rows_for_tactic = tactic_flaw_rows if tactic_flaw_rows is not None else flaw_rows
            for fr in rows_for_tactic:
                # Decided-lost: look up the pre-move position (ply N-1) and check.
                # mover_is_white derived from ply parity (single-source convention) so the
                # gate is correct for both player rows and opponent rows.
                entry = _build_tactic_by_ply_entry(fr, pos_by_ply)
                if entry is not None:
                    ply, tactic_entry = entry
                    tactic_by_ply[ply] = tactic_entry
            # SAN mainline for client-side per-ply board reconstruction on chart
            # hover. move_san is None on the terminal position only — filter it out
            # so moves[i] aligns with ply i (positions are ply-ordered). Quick
            # 260717-rbn: computed BEFORE _build_eval_series (not after, as
            # previously) so opening_ply_count is available to gate the new
            # best/good tiers to out-of-book plies.
            moves_data = [p.move_san for p in positions if p.move_san is not None]
            eval_series_val, flaw_marker_val, phase_transition_val = _build_eval_series(
                game,
                positions,
                tactic_by_ply=tactic_by_ply if tactic_by_ply else None,
                best_moves_by_ply=best_moves_by_ply,
                opening_ply_count=find_opening_ply_count(moves_data) if moves_data else 0,
            )
            eval_series_data = eval_series_val
            flaw_marker_data = flaw_marker_val
            phase_transition_data = phase_transition_val
        else:
            eval_series_data = None
            flaw_marker_data = None
            phase_transition_data = None
            moves_data = None

    # Phase 164 (SEED-093): Lichess-Blitz-normalized ratings for Maia ELO slider
    # conditioning. Correspondence check runs FIRST (chess.com Daily / lichess
    # correspondence lack a real-time-play equivalent in either ChessGoals
    # table) before dispatching by (platform, time_control_bucket).
    is_correspondence = is_correspondence_time_control(game.time_control_str)
    # BUG FIX (Phase 167, RESEARCH Pitfall 3): normalize_to_lichess_blitz has only
    # chess.com/lichess branches (if platform == "chess.com": ... else: # lichess).
    # Once Platform gained "flawchess" (Plan 01, D-17), a flawchess game's rating
    # would silently fall into the lichess else-branch and get re-run through the
    # Table-2 inversion for non-blitz buckets — but a stored flawchess rating is
    # ALREADY lichess-blitz-equivalent by construction of anchor_rating (STORE-03).
    # Guard both call sites so a flawchess rating passes through unchanged instead
    # of being double-converted.
    is_flawchess = game.platform == "flawchess"
    white_rating_lichess_blitz = (
        game.white_rating
        if is_flawchess
        else (
            normalize_to_lichess_blitz(
                game.white_rating,
                cast(Platform, game.platform),
                cast(TimeControlBucket, game.time_control_bucket),
                is_correspondence=is_correspondence,
            )
            if game.white_rating is not None and game.time_control_bucket is not None
            else None
        )
    )
    black_rating_lichess_blitz = (
        game.black_rating
        if is_flawchess
        else (
            normalize_to_lichess_blitz(
                game.black_rating,
                cast(Platform, game.platform),
                cast(TimeControlBucket, game.time_control_bucket),
                is_correspondence=is_correspondence,
            )
            if game.black_rating is not None and game.time_control_bucket is not None
            else None
        )
    )

    # Phase 172 (SEED-106 D-06): computed unconditionally for every card (list
    # mode included), not just the single-game path. This is a few dozen dict
    # lookups against an already-loaded module-level trie (tens of
    # microseconds) — gating it to get_library_game alone would fork
    # _build_card's contract for no measurable gain (RESEARCH Open Question 1).
    opening_ply_count = find_opening_ply_count(moves_data) if moves_data else 0

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
        white_rating_lichess_blitz=white_rating_lichess_blitz,
        black_rating_lichess_blitz=black_rating_lichess_blitz,
        opening_name=game.opening_name,
        opening_eco=game.opening_eco,
        user_color=game.user_color,
        ply_count=game.ply_count,
        termination=game.termination,
        time_control_str=game.time_control_str,
        result_fen=game.result_fen,
        severity_counts=severity_counts,
        # Phase 179 (SEED-112, D-01): canonical Phase 178 accuracy columns only —
        # deliberately never game.white_accuracy_imported / black_accuracy_imported.
        white_accuracy=game.white_accuracy,
        black_accuracy=game.black_accuracy,
        chips=chips,
        analysis_state=analysis_state,
        eval_series=eval_series_data,
        flaw_markers=flaw_marker_data,
        phase_transitions=phase_transition_data,
        moves=moves_data,
        initial_fen=game.initial_fen,
        active_eval_status=active_eval_status,
        opening_ply_count=opening_ply_count,
    )


async def get_library_game(
    session: AsyncSession,
    game_id: int,
) -> GameFlawCard | None:
    """Return a single GameFlawCard for any game, by id.

    Quick 260717-agv: this is the analysis-page game-view path
    (GET /library/games/{game_id}, used only by the Analysis board). It is
    intentionally NOT owner-scoped — any authenticated user may inspect any
    game by url (e.g. /analysis?game_id=640125) for opponent scouting and game
    sharing. The requester's identity is irrelevant to WHAT is returned; the
    only gate is "logged in", enforced by the router's current_active_user
    dependency. Returns None only when the game does not exist (router → 404).

    Data is scoped to the game's OWNER (game.user_id), not the requester: the
    flaws, positions and evals for a game live under the owner's user_id, so
    every downstream batch query is passed owner_id (a different requester would
    otherwise get empty rows).

    Reuses _build_card with the same three batch queries as get_library_games
    (fetch_page_analyzed_set, fetch_page_game_flaws, fetch_page_eval_positions),
    called with [game_id]. Queries run sequentially on the one AsyncSession
    (no asyncio.gather — CLAUDE.md §"Never use asyncio.gather on the same AsyncSession").

    Quick 260702-mnd (D-3): the tactic/severity filter params this endpoint used
    to accept existed ONLY to drive per-slot pruning in _build_card, which is now
    removed. The single-game path does no game selection, so those params had no
    other purpose — dropped end-to-end (router, service, frontend client/hook).
    """
    game = await session.get(Game, game_id)
    if game is None:
        return None

    owner_id = game.user_id  # scope data to the owner; any logged-in user may view
    game_ids = [game_id]

    is_analyzed = game_id in await library_repository.fetch_page_analyzed_set(
        session, owner_id, game_ids
    )
    flaw_rows = (await library_repository.fetch_page_game_flaws(session, owner_id, game_ids)).get(
        game_id, []
    )
    # Both-color rows for tactic tooltip population (opponent plies included).
    # WARNING: must not replace flaw_rows — counts/chips stay player-gated.
    tactic_flaw_rows = (
        await library_repository.fetch_page_game_flaws_both_colors(session, owner_id, game_ids)
    ).get(game_id, [])

    # Fetch active eval-job status for the pending→leased pill transition.
    # Sequential call on the same AsyncSession (no asyncio.gather per CLAUDE.md).
    active_map = await library_repository.fetch_page_active_eval_status(session, owner_id, game_ids)

    # Quick 260714-rj5: always fetch positions on the single-game path (not
    # gated on is_analyzed) — moves come from game_positions.move_san, which
    # does not depend on evals, so an unanalyzed game can still render a
    # navigable board. fetch_page_eval_positions has no analyzed-ness predicate
    # of its own; positions are scoped to owner_id (the game's owner).
    positions: list[GamePosition] = (
        await library_repository.fetch_page_eval_positions(session, owner_id, game_ids)
    ).get(game_id, [])

    # Phase 175 (BOARD-01): batch-fetch stored best-move candidate rows for this
    # game, same already-user-scoped game_ids list as fetch_page_eval_positions
    # (fetch_page_best_moves has no user_id column of its own — IDOR safety comes
    # from this caller-side scoping).
    best_moves_by_ply = (await library_repository.fetch_page_best_moves(session, game_ids)).get(
        game_id, {}
    )

    return _build_card(
        game,
        flaw_rows,
        is_analyzed,
        positions,
        active_map.get(game_id),
        tactic_flaw_rows=tactic_flaw_rows,
        best_moves_by_ply=best_moves_by_ply,
    )


# ---------------------------------------------------------------------------
# Phase 208 (D-11/D-12, PASTE-05/09) — Library-scoped "Pasted" opt-in
# ---------------------------------------------------------------------------

# The Games tab's default platform population (LIBG-08 substitution below).
# `flawchess` is in this list because Phase 167 D-03 opted bot games back INTO
# the Library (the opposite of the default-exclusion the rest of the app
# applies to them). `"pgn"` is deliberately NOT in it: D-11 makes pasted games
# opt-in, the OPPOSITE of how bot games were handled — a user pastes games
# that are frequently NOT their own, so they must stay hidden until the
# Library's explicit "Pasted" chip asks for them. This list must NEVER gain
# "pgn".
LIBRARY_GAMES_BASE_PLATFORMS: tuple[str, ...] = ("chess.com", "lichess", "flawchess")


def resolve_library_platforms(
    platform: Sequence[str] | None,
    *,
    include_pasted: bool,
    surface: Literal["games", "analytics"],
) -> list[str]:
    """Resolve the platform list a Library surface should query (D-11/D-12).

    Each Library surface has its own correct default population, so a single
    shared base would silently change one of them:
    - surface="games" (GET /library/games): the Games tab shows flawchess
      bot-practice games by Phase 167 D-03, so its base is
      LIBRARY_GAMES_BASE_PLATFORMS (chess.com/lichess/flawchess).
    - surface="analytics" (flaw-stats/flaws/flaw-comparison/tactic-comparison):
      these surfaces do NOT show bot games — their base is
      ANALYTICS_INCLUDED_PLATFORMS (chess.com/lichess), the explicit-list
      equivalent of the `platform=None` default through apply_game_filters
      (Plan 02's test_analytics_included_platforms_list_equals_default keeps
      the two readings equal).

    When `platform` is already explicit (caller passed a list), that list is
    the starting point instead of either base — an explicit caller selection
    is preserved, only extended.

    `include_pasted` is purely additive: when True and "pgn" is not already
    present, it is appended. It never removes or replaces anything, and it
    never mutates the input list.
    """
    if platform is not None:
        base = list(platform)
    elif surface == "games":
        base = list(LIBRARY_GAMES_BASE_PLATFORMS)
    else:
        base = list(ANALYTICS_INCLUDED_PLATFORMS)
    if include_pasted and "pgn" not in base:
        base.append("pgn")
    return base


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
    tactic_families: list[str] | None = None,
    tactic_orientation: Literal["either", "missed", "allowed"] = "either",
    min_tactic_depth: int | None = None,
    max_tactic_depth: int | None = None,
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
    has_gem: bool | None = None,
    has_great: bool | None = None,
    include_pasted: bool = False,
) -> LibraryGamesResponse:
    """Return the flaw-filtered paginated games archive (LIBG-08).

    D-02 migration: no per-game kernel re-call. Two batch queries cover the page:
    1. fetch_page_game_flaws — one query for all game_flaws rows (chips + M+B counts)
    2. fetch_page_analyzed_set — one query for the eval-coverage-analyzed subset

    Inaccuracy count comes from oracle columns (games.white_/black_inaccuracies),
    never from game_flaws (D-03). Analysis state is gated on eval coverage, not
    on game_flaws row presence (LIBG-02 — never a false 0/0/0).

    Phase 167 D-03: apply_game_filters now excludes platform='flawchess' by
    default (D-02, STORE-07). The Library Games tab is the one surface that
    SHOULD show flawchess bot-practice games, so when the caller passes no
    explicit platform filter, substitute an explicit list covering all three
    platforms to opt back in. NOTE: this alone is not sufficient for a bot
    game to actually surface here — the router's `opponent_type` query param
    still defaults to "human" (RESEARCH Pitfall 5), which independently
    excludes is_computer_game=True rows; wiring that default/filter-chip is
    Phase 171's job, out of scope here.

    Phase 208 (D-11/D-12, PASTE-05/09): `include_pasted` is the Library-only
    opt-in that reveals `platform='pgn'` games, off by default, additive to
    whatever population this tab already shows — resolved through
    resolve_library_platforms (surface="games") so pasted games join the
    existing chess.com/lichess/flawchess default rather than replacing it.

    has_gem / has_great (FILT-01, D-04/D-05): threaded straight through to
    query_filtered_games -> apply_game_filters -> best_move_exists_from_table,
    no transformation at this layer.
    """
    library_platform = resolve_library_platforms(
        platform, include_pasted=include_pasted, surface="games"
    )
    try:
        games, matched_count = await library_repository.query_filtered_games(
            session,
            user_id=user_id,
            time_control=time_control,
            platform=library_platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            flaw_severity=flaw_severity,
            flaw_tags=flaw_tags,
            tactic_families=tactic_families,
            tactic_orientation=tactic_orientation,
            min_tactic_depth=min_tactic_depth,
            max_tactic_depth=max_tactic_depth,
            offset=offset,
            limit=limit,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
            color=color,
            has_gem=has_gem,
            has_great=has_great,
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

        # Both-color rows for tactic tooltip population (opponent plies included).
        # WARNING: must not replace page_flaws — counts/chips stay player-gated.
        page_tactic_flaws = await library_repository.fetch_page_game_flaws_both_colors(
            session, user_id, page_game_ids
        )

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

        # Batch-fetch active eval-job status (pending|leased) for the page.
        # Sequential call on the same AsyncSession (no asyncio.gather per CLAUDE.md).
        active_status_map = await library_repository.fetch_page_active_eval_status(
            session, user_id, page_game_ids
        )

        # Phase 175 (BOARD-01): batch-fetch stored best-move candidate rows,
        # scoped to the same analyzed_game_ids as page_positions (unanalyzed
        # games have no eval_series to attach tiers to). No user_id scoping of
        # its own — IDOR safety comes from this already-user-scoped id list.
        page_best_moves = await library_repository.fetch_page_best_moves(session, analyzed_game_ids)

        cards = [
            _build_card(
                game,
                page_flaws.get(game.id, []),
                game.id in analyzed_set,
                page_positions.get(game.id, []),
                active_status_map.get(game.id),
                tactic_flaw_rows=page_tactic_flaws.get(game.id, []),
                best_moves_by_ply=page_best_moves.get(game.id, {}),
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

_PER_100 = 100.0
# Trailing rolling window (games) for the flaw trend chart. Matches the Endgame ELO
# Timeline window (endgame_service.ENDGAME_ELO_TIMELINE_WINDOW = 100) so the two
# time-series charts read consistently.
FLAW_TREND_WINDOW = 100


def _user_moves_from_ply_count(user_color: str, ply_count: int) -> int:
    """User move count from total half-moves (ply_count). White moves first.

    ply_count is the total number of half-moves (== max game_positions.ply). White
    plays the odd-indexed half-moves -> ceil(ply_count/2); black the even ones ->
    floor(ply_count/2). (game_flaws.ply is a 0-indexed from-position 0..ply_count-1,
    a separate numbering — irrelevant here since the trend reads oracle counts.)
    """
    if user_color == "white":
        return (ply_count + 1) // 2  # ceil
    return ply_count // 2  # floor


def _compute_flaw_trend(rows: list[Any]) -> list[FlawTrendPoint]:
    """ISO-week per-100-move MACRO flaw trend over a trailing FLAW_TREND_WINDOW window.

    Mirrors the Endgame ELO Timeline windowing (endgame_service.compute_score_gap_timeline):
    walk games chronologically, keep a trailing FLAW_TREND_WINDOW-game window of per-game
    rates, and emit ONE point per ISO week — the window state at that week's last game.
    Each rate is the macro mean over the window of (oracle_count / user_moves * 100), the
    same per-game-then-mean aggregation the KPI cards use. per_week_games is the games
    that ISO week (drives the volume bars). Weeks whose window has fewer than
    MIN_GAMES_FOR_TIMELINE games are dropped (partial-window floor).

    rows come from fetch_flaw_trend_rows: (played_at, user_color, ply_count, blunders,
    mistakes, inaccuracies), oracle move-quality counts picked by color, played_at ASC.
    """
    b_rates: list[float] = []
    m_rates: list[float] = []
    i_rates: list[float] = []
    per_week_games: dict[tuple[int, int], int] = {}
    point_by_week: dict[tuple[int, int], FlawTrendPoint] = {}

    for row in rows:
        moves = _user_moves_from_ply_count(row.user_color, int(row.ply_count))
        if moves <= 0:
            continue
        b_rates.append(int(row.blunders or 0) / moves * _PER_100)
        m_rates.append(int(row.mistakes or 0) / moves * _PER_100)
        i_rates.append(int(row.inaccuracies or 0) / moves * _PER_100)

        iso = row.played_at.isocalendar()
        week_key = (iso.year, iso.week)
        per_week_games[week_key] = per_week_games.get(week_key, 0) + 1

        window_b = b_rates[-FLAW_TREND_WINDOW:]
        n = len(window_b)
        if n < MIN_GAMES_FOR_TIMELINE:
            continue
        window_m = m_rates[-FLAW_TREND_WINDOW:]
        window_i = i_rates[-FLAW_TREND_WINDOW:]
        # Last-write-wins per ISO week -> the point reflects the week's final game,
        # so per_week_games (accumulated above) is the full week count at emit time.
        monday = datetime.date.fromisocalendar(iso.year, iso.week, 1)
        point_by_week[week_key] = FlawTrendPoint(
            date=monday.isoformat(),
            blunder_rate=round(sum(window_b) / n, 4),
            mistake_rate=round(sum(window_m) / n, 4),
            inaccuracy_rate=round(sum(window_i) / n, 4),
            games_in_window=n,
            per_week_games=per_week_games[week_key],
        )
    return [point_by_week[key] for key in sorted(point_by_week)]


def _compute_flaw_trend_by_tc(rows: Sequence[Any]) -> list[FlawTrendTc]:
    """One Flaws Timeline series per time control (Phase 239 D-00k).

    Buckets the trend rows by their tc column and runs the unchanged
    _compute_flaw_trend per TC in LIBRARY_TC_ORDER. A TC is emitted only when it has
    at least one trend point (the partial-window floor can leave a TC with none).
    """
    rows_by_tc = _bucket_rows_by_tc(rows)
    series: list[FlawTrendTc] = []
    for tc in LIBRARY_TC_ORDER:
        points = _compute_flaw_trend(rows_by_tc.get(tc, []))
        if points:
            series.append(FlawTrendTc(tc=tc, points=points))
    return series


def _empty_stats(total_n: int) -> FlawStatsResponse:
    """Zero-valued stats for an empty analyzed set (never raises)."""
    return FlawStatsResponse(
        trend_by_tc=[],
        trend_window=FLAW_TREND_WINDOW,
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
    include_pasted: bool = False,
) -> FlawStatsResponse:
    """Coverage counts + per-TC Flaws Timeline over the filtered set (LIBG-09, Phase 239).

    Pipeline:
    1. count_filtered_and_analyzed — total_n / analyzed_n (eval-coverage gate). An empty
       analyzed set returns zeros + empty trend_by_tc, never raises.
    2. fetch_flaw_trend_rows — oracle per-game rows (with their tc), bucketed per time
       control by _compute_flaw_trend_by_tc.

    analyzed_n / total_n derive from the eval-coverage subquery — NOT from game_flaws
    row counts (Pitfall 6). An analyzed game with zero M+B flaws counts toward
    analyzed_n. The severity counts, rates and tag distribution this endpoint used to
    return are gone (Phase 239 D-00e/D-00k): the tiles read the flaw-comparison bullets.

    Phase 208 (D-11/D-12, PASTE-05/09): `include_pasted` opts pasted games into
    this analytics surface's own default population (resolve_library_platforms,
    surface="analytics" — chess.com/lichess, NOT flawchess), off by default.
    """
    platform = resolve_library_platforms(
        platform, include_pasted=include_pasted, surface="analytics"
    )
    try:
        # Coverage badge: omit flaw_severity so total_n spans the WHOLE filtered
        # game set and analyzed_n <= total_n (a flaw EXISTS would collapse them).
        total_n, analyzed_n = await library_repository.count_filtered_and_analyzed(
            session,
            user_id=user_id,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
            color=color,
        )
        if analyzed_n == 0:
            return _empty_stats(total_n)

        # Trend reads the games-table oracle columns directly (no analyzed_subq /
        # game_flaws) — its own oracle-present gate defines "analyzed" for the chart.
        trend_rows = await library_repository.fetch_flaw_trend_rows(
            session,
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
    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("flaw_stats", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    return FlawStatsResponse(
        trend_by_tc=_compute_flaw_trend_by_tc(trend_rows),
        trend_window=FLAW_TREND_WINDOW,
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
    tactic_families: list[str] | None = None,
    tactic_orientation: TacticOrientation = "either",
    min_tactic_depth: int | None = None,
    max_tactic_depth: int | None = None,
    offset: int,
    limit: int,
    include_pasted: bool = False,
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
        include_pasted: Phase 208 (D-11/D-12, PASTE-05/09) — the Library-only
          opt-in that reveals `platform='pgn'` games on the Flaws tab, off by
          default, resolved through resolve_library_platforms(surface="analytics")
          so it never admits flawchess bot games (this surface's own default
          population excludes them, unlike the Games tab).
    """
    effective_severity = severity if severity else _DEFAULT_SEVERITY
    platform = resolve_library_platforms(
        platform, include_pasted=include_pasted, surface="analytics"
    )
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
            tactic_families=tactic_families,
            orientation=tactic_orientation,
            min_tactic_depth=min_tactic_depth,
            max_tactic_depth=max_tactic_depth,
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


# ---------------------------------------------------------------------------
# Phase 115 — You-vs-Opponent flaw comparison (FLAWCMP-01/03/04/05)
# ---------------------------------------------------------------------------

# Named constant — no magic number (CLAUDE.md no-magic-numbers rule).
# Matches §5 cohort inclusion basis: only users with >= 20 analyzed games
# were included in the benchmark pool, so the user's delta and the zone
# rest on comparable sample sizes (D-09).
FLAW_COMPARISON_GATE: int = 20

# Phase 239 D-14 (replaces the D-12 40-flaw low-sample fade): a cell gets a red/green
# verdict only when its 99% CI on the gap excludes 0. The bands are symmetric around 0
# (D-15), so a gap outside the band is significant on its own side.
MIN_DELTAS_FOR_SIGNIFICANCE: int = 2  # one game has no variance, so no CI


def _is_significant(deltas: list[float], ci_low: float, ci_high: float) -> bool:
    """D-14 gate: the 99% CI on the mean per-game gap excludes 0."""
    return len(deltas) >= MIN_DELTAS_FOR_SIGNIFICANCE and ci_excludes(0.0, ci_low, ci_high)


# Phase 239 D-02: TC order of the per-TC payloads (fast to slow, same as the TC switch).
LIBRARY_TC_ORDER: Final[tuple[TimeControlBucket, ...]] = ("bullet", "blitz", "rapid", "classical")


def _compute_mean_ci(
    values: list[float],
    z: float = VERDICT_CI_Z_99,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) for a list of per-game deltas (99% by default, D-14).

    Returns (0.0, 0.0, 0.0) when values is empty.
    Returns (mean, mean, mean) when n == 1 (undefined variance).
    Normal/t Wald-z approximation — adequate at N >= 20 per RESEARCH §CI Method.
    No scipy dependency: sample variance computed from stdlib math.
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(values) / n
    if n == 1:
        return mean, mean, mean
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    se = math.sqrt(variance / n)
    half = z * se
    return mean, mean - half, mean + half


def _two_sided_p(values: list[float]) -> float | None:
    """Two-sided p-value for H0: mean == 0 over per-game deltas.

    Uses the same Wald-z as _compute_mean_ci (z = mean / SE) and the normal
    survival function p = erfc(|z| / sqrt(2)) — stdlib only, no scipy. Returns
    None when n < 2 (SE undefined). Degenerate SE == 0: p = 0.0 when the mean is
    nonzero (a perfectly tight nonzero estimate), 1.0 when the mean is exactly 0.
    """
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    se = math.sqrt(variance / n)
    if se == 0.0:
        return 0.0 if mean != 0.0 else 1.0
    z = mean / se
    return math.erfc(abs(z) / math.sqrt(2.0))


def _bucket_rows_by_tc(rows: Sequence[Any]) -> dict[str, list[Any]]:
    """Group per-game rows by their tc column (Phase 239 D-02).

    One fetched row set serves every TC, so the switch never costs an extra query.
    """
    by_tc: dict[str, list[Any]] = {}
    for row in rows:
        by_tc.setdefault(str(row.tc), []).append(row)
    return by_tc


def _build_flaw_bullet(
    metric: FlawDeltaMetric,
    tc: TimeControlBucket,
    deltas: list[float],
    player_rates: list[float],
    opp_rates: list[float],
    p_total: int,
    o_total: int,
) -> FlawBullet:
    """Build one FlawBullet from the per-game accumulators of one metric in one TC."""
    band = flaw_delta_zone(metric, tc)
    if p_total == 0 and o_total == 0:
        # Zero-event: no events on either side, render muted placeholder (D-11)
        return FlawBullet(
            tag=metric,
            delta=None,
            ci_low=None,
            ci_high=None,
            player_rate=None,
            opp_rate=None,
            p_value=None,
            player_events=0,
            opp_events=0,
            zone_lo=band.zone_lo,
            zone_hi=band.zone_hi,
            has_zone=True,
            significant=False,
        )
    mean, ci_low, ci_high = _compute_mean_ci(deltas)
    return FlawBullet(
        tag=metric,
        delta=mean,
        ci_low=ci_low,
        ci_high=ci_high,
        player_rate=sum(player_rates) / len(player_rates) if player_rates else 0.0,
        opp_rate=sum(opp_rates) / len(opp_rates) if opp_rates else 0.0,
        p_value=_two_sided_p(deltas),
        player_events=p_total,
        opp_events=o_total,
        zone_lo=band.zone_lo,
        zone_hi=band.zone_hi,
        has_zone=True,
        significant=_is_significant(deltas, ci_low, ci_high),
    )


def _compute_bullets(rows: Sequence[Any], tc: TimeControlBucket) -> list[FlawBullet]:
    """Aggregate one TC's per-game rows into the 12 FlawBullet objects (FLAW_DELTA_METRICS order).

    Each row has: game_id, tc, user_moves, player_<tag>, opp_<tag> for all 12 tags.
    For each metric: collect per-game deltas (player - opp) / user_moves * 100,
    plus the per-game player and opponent rates (each / user_moves * 100, so the
    comparison stays paired and player_rate - opp_rate == delta exactly), and
    accumulate total event counts. Zero-event bullet: both sides = 0 across all
    games → delta=None (not 0.0, D-11). Zone bounds come from the per-zone-TC
    registry via flaw_delta_zone(metric, tc) (D-07, D-08).
    """
    tags = FLAW_DELTA_METRICS
    deltas_by_tag: dict[str, list[float]] = {t: [] for t in tags}
    player_rates_by_tag: dict[str, list[float]] = {t: [] for t in tags}
    opp_rates_by_tag: dict[str, list[float]] = {t: [] for t in tags}
    player_totals: dict[str, int] = {t: 0 for t in tags}
    opp_totals: dict[str, int] = {t: 0 for t in tags}

    for row in rows:
        user_moves = int(row.user_moves) if row.user_moves else 0
        if user_moves <= 0:
            # Guard: skip rows with degenerate denominator (should be excluded by anchor)
            continue
        for tag in tags:
            player_count = int(getattr(row, f"player_{tag}", 0) or 0)
            opp_count = int(getattr(row, f"opp_{tag}", 0) or 0)
            player_totals[tag] += player_count
            opp_totals[tag] += opp_count
            player_rate = player_count / user_moves * 100.0
            opp_rate = opp_count / user_moves * 100.0
            player_rates_by_tag[tag].append(player_rate)
            opp_rates_by_tag[tag].append(opp_rate)
            deltas_by_tag[tag].append(player_rate - opp_rate)

    return [
        _build_flaw_bullet(
            tag,
            tc,
            deltas_by_tag[tag],
            player_rates_by_tag[tag],
            opp_rates_by_tag[tag],
            player_totals[tag],
            opp_totals[tag],
        )
        for tag in tags
    ]


async def get_flaw_comparison(
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
    include_pasted: bool = False,
) -> FlawComparisonResponse:
    """Per-TC you-vs-opponent flaw comparison over the filtered analyzed set (Phase 115, 239).

    Pipeline:
    1. count_analyzed_by_tc: analyzed games per time control within the current
       filters (the sidebar TC filter narrows the list, D-02). No analyzed games at
       all → tcs=[].
    2. fetch_flaw_comparison: ONE per-game LEFT JOIN aggregation (24 COUNT FILTER
       columns plus the tc column); sequential awaits only, never gather on the session.
    3. _bucket_rows_by_tc + _compute_bullets: mean + Wald-z CI per metric per TC,
       zone bounds from the per-zone-TC registry. Bullets are ALWAYS computed, also
       for below-gate TCs, so tiles can show rates (D-03); below_gate is flagged.

    IDOR guard (T-115-01): user_id is from current_active_user, never a request param.

    Phase 208 (D-11/D-12, PASTE-05/09): `include_pasted` opts pasted games into
    this analytics surface's own default population (resolve_library_platforms,
    surface="analytics"), off by default.
    """
    platform = resolve_library_platforms(
        platform, include_pasted=include_pasted, surface="analytics"
    )
    try:
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

        # Analyzed-game counts per TC for the SEVERITY-FILTERED set (passes
        # flaw_severity), so analyzed_n matches the set the bullets aggregate over.
        counts = await library_repository.count_analyzed_by_tc(
            session,
            user_id=user_id,
            **_filter_kwargs,
        )
        if not counts:
            return FlawComparisonResponse(tcs=[], analyzed_gate=FLAW_COMPARISON_GATE)

        analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)
        rows = await library_repository.fetch_flaw_comparison(
            session,
            user_id,
            analyzed_subq,
            **_filter_kwargs,
        )
        rows_by_tc = _bucket_rows_by_tc(rows)
        tcs = [
            FlawComparisonTc(
                tc=tc,
                analyzed_n=counts[tc],
                below_gate=counts[tc] < FLAW_COMPARISON_GATE,
                bullets=_compute_bullets(rows_by_tc.get(tc, []), tc),
            )
            for tc in LIBRARY_TC_ORDER
            if counts.get(tc)
        ]
        return FlawComparisonResponse(tcs=tcs, analyzed_gate=FLAW_COMPARISON_GATE)

    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("flaw_comparison", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise


# ---------------------------------------------------------------------------
# Phase 126 — Tactic comparison (TACCMP-01/02/03)
# ---------------------------------------------------------------------------

# Named constant — no magic number (CLAUDE.md no-magic-numbers rule).
# Mirrors FLAW_COMPARISON_GATE: same minimum analyzed-game floor so the section
# gate is consistent with the flaw comparison section (D-03).
TACTIC_COMPARISON_GATE: int = 20

# Confidence threshold for chip display (D-09). Re-exported from library_repository
# where it gates the query_flaws row build; named here so callers import from the
# service layer (MIN_TACTIC_CHIP_CONFIDENCE is the public constant name per PATTERNS).
MIN_TACTIC_CHIP_CONFIDENCE: int = _TACTIC_CHIP_CONFIDENCE_MIN


# Phase 239 D-00h: tactic gaps read per 100 games. The per-game counts are multiplied once,
# in _compute_tactic_bullets; the mean and CI scale linearly and the p-value is
# scale-invariant, so nothing downstream rescales.
PER_100_GAMES: float = 100.0


def _build_tactic_bullet(
    family: TacticFamily,
    orientation: TacticSide,
    tc: TimeControlBucket,
    you_rates: list[float],
    opp_rates: list[float],
    you_total: int,
    opp_total: int,
) -> TacticBullet:
    """Build one TacticBullet from the per-game accumulators of one family-side in one TC."""
    band = tactic_delta_zone(family, orientation, tc)
    zone_lo = band.zone_lo if band is not None else 0.0
    zone_hi = band.zone_hi if band is not None else 0.0
    if you_total == 0 and opp_total == 0:
        # Zero-event family-side: delta=None (mirrors the FlawBullet zero-event pattern, D-11).
        return TacticBullet(
            family=family,
            orientation=orientation,
            you_rate=None,
            opp_rate=None,
            delta=None,
            ci_low=None,
            ci_high=None,
            p_value=None,
            you_events=0,
            opp_events=0,
            zone_lo=zone_lo,
            zone_hi=zone_hi,
            has_zone=band is not None,
            significant=False,
        )
    deltas = [y - o for y, o in zip(you_rates, opp_rates, strict=True)]
    mean, ci_low, ci_high = _compute_mean_ci(deltas)
    return TacticBullet(
        family=family,
        orientation=orientation,
        you_rate=sum(you_rates) / len(you_rates) if you_rates else 0.0,
        opp_rate=sum(opp_rates) / len(opp_rates) if opp_rates else 0.0,
        delta=mean,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=_two_sided_p(deltas),
        you_events=you_total,
        opp_events=opp_total,
        zone_lo=zone_lo,
        zone_hi=zone_hi,
        has_zone=band is not None,
        significant=_is_significant(deltas, ci_low, ci_high),
    )


def _compute_tactic_bullets(
    rows: Sequence[Any],
    orientation: TacticSide,
    tc: TimeControlBucket,
) -> list[TacticBullet]:
    """Aggregate one TC's per-game rows into the 19 TacticBullets of one orientation.

    Each row has: game_id, tc, player_{family}, opp_{family} for every family in
    TACTIC_FAMILIES. Per game, the rate is the count times PER_100_GAMES (Phase 239
    D-00h), so a single game with one missed fork reads 100.0. Bullets come back in
    TACTIC_FAMILIES order with no ranking or selection; get_tactic_comparison interleaves
    the two orientations. Zone bounds come from the tactic registry via
    tactic_delta_zone(family, orientation, tc) (D-11); zero-event family: delta=None.
    """
    bullets: list[TacticBullet] = []
    for family in TACTIC_FAMILIES:
        you_counts = [int(getattr(row, f"player_{family}", 0) or 0) for row in rows]
        opp_counts = [int(getattr(row, f"opp_{family}", 0) or 0) for row in rows]
        bullets.append(
            _build_tactic_bullet(
                family,
                orientation,
                tc,
                [c * PER_100_GAMES for c in you_counts],
                [c * PER_100_GAMES for c in opp_counts],
                sum(you_counts),
                sum(opp_counts),
            )
        )
    return bullets


def _interleave_tactic_bullets(
    missed: Sequence[TacticBullet], allowed: Sequence[TacticBullet]
) -> list[TacticBullet]:
    """Fixed payload order: per family, missed bullet then allowed bullet (D-00h)."""
    return [bullet for pair in zip(missed, allowed, strict=True) for bullet in pair]


async def get_tactic_comparison(
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
    tactic_families: Sequence[str] | None = None,
    include_pasted: bool = False,
) -> TacticComparisonResponse:
    """Per-TC tactic motif you-vs-opponent comparison, per 100 games (Phase 126/129/239).

    Returns one TacticComparisonTc per time control that the filters allow and that has
    at least one analyzed game (D-02), ordered bullet..classical. Each carries all 19
    families x missed/allowed in fixed FAMILY_TO_MOTIF_INTS order (missed before allowed),
    also when the TC is below the 20-game gate (D-03). No ranking, no top-N (D-00h).

    Pipeline:
    1. count_analyzed_by_tc: analyzed games per TC under the current filters
       (tactic_filter_orientation="either", so the denominator matches both fetches).
       No analyzed games at all → tcs=[].
    2. fetch_tactic_comparison called TWICE (once per orientation), sequential awaits
       only, never gather on the session.
    3. _bucket_rows_by_tc + _compute_tactic_bullets: mean + Wald-z CI per family per
       orientation per TC, zone bounds from the tactic registry (D-11).

    IDOR guard (T-126-01, T-239-08): user_id is from current_active_user, never a request param.

    Phase 208 (D-11/D-12, PASTE-05/09): `include_pasted` opts pasted games into
    this analytics surface's own default population (resolve_library_platforms,
    surface="analytics"), off by default.
    """
    platform = resolve_library_platforms(
        platform, include_pasted=include_pasted, surface="analytics"
    )
    try:
        _filter_kwargs: dict[str, Any] = dict(
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
            # Thread the tactic-family filter into BOTH the count and the per-game
            # fetches so analyzed_n matches the set the bullets aggregate over (WR-02).
            tactic_families=tactic_families,
            # SEED-062: the grid shows BOTH orientations, so narrow the game
            # population on "either" (not the apply_game_filters "allowed" default).
            tactic_filter_orientation="either",
        )

        counts = await library_repository.count_analyzed_by_tc(
            session,
            user_id=user_id,
            # WR-01: the tactic population is blob-done games only (the section 5
            # calibration basis); the flaw comparison does not pass this.
            require_tactic_blobs=True,
            **_filter_kwargs,
        )
        if not counts:
            return TacticComparisonResponse(tcs=[], analyzed_gate=TACTIC_COMPARISON_GATE)

        analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)
        # Two fetches (one per orientation), each bucketed per TC in Python.
        missed_rows = await library_repository.fetch_tactic_comparison(
            session,
            user_id,
            analyzed_subq,
            tactic_confidence_min=MIN_TACTIC_CHIP_CONFIDENCE,
            orientation="missed",
            **_filter_kwargs,
        )
        allowed_rows = await library_repository.fetch_tactic_comparison(
            session,
            user_id,
            analyzed_subq,
            tactic_confidence_min=MIN_TACTIC_CHIP_CONFIDENCE,
            orientation="allowed",
            **_filter_kwargs,
        )
        missed_by_tc = _bucket_rows_by_tc(missed_rows)
        allowed_by_tc = _bucket_rows_by_tc(allowed_rows)

        tcs = [
            TacticComparisonTc(
                tc=tc,
                analyzed_n=counts[tc],
                below_gate=counts[tc] < TACTIC_COMPARISON_GATE,
                bullets=_interleave_tactic_bullets(
                    _compute_tactic_bullets(missed_by_tc.get(tc, []), "missed", tc),
                    _compute_tactic_bullets(allowed_by_tc.get(tc, []), "allowed", tc),
                ),
            )
            for tc in LIBRARY_TC_ORDER
            if counts.get(tc)
        ]
        return TacticComparisonResponse(tcs=tcs, analyzed_gate=TACTIC_COMPARISON_GATE)

    except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
        sentry_sdk.set_context("tactic_comparison", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise
