"""Endgame service: classification, aggregation, and orchestration for endgame analytics.

Exposes:
- classify_endgame_class: pure function mapping material_signature to category name
- EndgameClassInt: IntEnum encoding for endgame_class SmallInteger column (Per D-06)
- _INT_TO_CLASS / _CLASS_TO_INT: bidirectional mappings for integer <-> string conversion
- _aggregate_endgame_stats: aggregates raw per-game rows into EndgameCategoryStats list
- get_endgame_stats: orchestrator for GET /api/endgames/stats
- get_endgame_games: orchestrator for GET /api/endgames/games
- get_endgame_performance: orchestrator for GET /api/endgames/performance
- get_endgame_timeline: orchestrator for GET /api/endgames/timeline
- get_endgame_elo_timeline: per-combo weekly Endgame ELO + Actual ELO rolling series (Phase 57 ELO-05)
"""

import bisect
import math
import statistics
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from enum import IntEnum
from typing import Any, Literal, cast

import sentry_sdk
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    count_endgame_games,
    count_filtered_games,
    query_clock_stats_rows,
    query_endgame_bucket_rows,
    query_endgame_elo_timeline_rows,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
    query_endgame_performance_rows,
    query_endgame_timeline_rows,
)
from app.schemas.openings import GameRecord
from app.schemas.endgames import (
    ClockPressureResponse,
    ClockPressureTimelinePoint,
    ClockStatsRow,
    ConversionRecoveryStats,
    EndgameClass,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameEloTimelineResponse,
    EndgameGamesResponse,
    EndgameLabel,
    EndgameOverallPoint,
    EndgameOverviewResponse,
    EndgamePerformanceResponse,
    EndgameStatsResponse,
    EndgameTimelinePoint,
    EndgameTimelineResponse,
    EndgameWDLSummary,
    MaterialBucket,
    MaterialRow,
    ScoreGapMaterialResponse,
    ScoreGapTimelinePoint,
    TimePressureBucketPoint,
    TimePressureChartResponse,
)
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.openings_service import MIN_GAMES_FOR_TIMELINE, derive_user_result, recency_cutoff
from app.services.score_confidence import (
    CI_Z_95,
    CONFIDENCE_MIN_N,
    compute_confidence_bucket,
    compute_paired_difference_test,
    compute_score_confidence_from_mean,
    compute_score_difference_test,
    wilson_bounds,
)


class EndgameClassInt(IntEnum):
    """Integer encoding for endgame_class column (SmallInteger, 2 bytes per row).
    Maps 1:1 to EndgameClass Literal strings. Per D-06."""

    ROOK = 1
    MINOR_PIECE = 2
    PAWN = 3
    QUEEN = 4
    MIXED = 5
    PAWNLESS = 6


_INT_TO_CLASS: dict[int, EndgameClass] = {
    1: "rook",
    2: "minor_piece",
    3: "pawn",
    4: "queen",
    5: "mixed",
    6: "pawnless",
}

_CLASS_TO_INT: dict[EndgameClass, int] = {v: k for k, v in _INT_TO_CLASS.items()}


# Display labels for each endgame category (D-07).
_ENDGAME_CATEGORY_LABELS: dict[EndgameClass, EndgameLabel] = {
    "rook": "Rook",
    "minor_piece": "Minor Piece",
    "pawn": "Pawn",
    "queen": "Queen",
    "mixed": "Mixed",
    "pawnless": "Pawnless",
}


def classify_endgame_class(material_signature: str) -> EndgameClass:
    """Classify a material_signature string into one of six endgame categories.

    Categories (D-07):
    - queen: queen(s), may have pawns, no rook or minor pieces
    - rook: rook(s), may have pawns, no queen or minor pieces
    - minor_piece: bishop/knight, may have pawns, no queen or rook
    - pawn: only pawns, no pieces
    - mixed: two or more piece families present WITH pawns
    - pawnless: no pawns at all — bare kings or multi-family without pawns (e.g. KRN_KR)

    Pawns alongside a single piece family do NOT trigger mixed — a rook+pawns endgame
    is a rook endgame, a bishop+pawns endgame is a minor piece endgame.

    Args:
        material_signature: Canonical string like "KRPP_KRP" (stronger side first).

    Returns:
        One of: "rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"
    """
    # Remove the underscore separator and kings — only look at non-king piece/pawn types
    sig = material_signature.replace("_", "").replace("K", "")

    has_queen = "Q" in sig
    has_rook = "R" in sig
    has_minor = "B" in sig or "N" in sig
    has_pawn = "P" in sig

    # Count piece families (queen, rook, minor) — pawns are NOT a piece family.
    # A rook endgame with pawns (KRP_KRP) is still a rook endgame.
    # Mixed = two or more piece families present WITH pawns (e.g. queen+rook+pawns).
    # Pawnless = no pawns at all (bare kings, or multi-family without pawns like KRB_KR).
    piece_families = sum([has_queen, has_rook, has_minor])

    # Pawnless: any endgame with no pawns and either no pieces (bare kings)
    # or multiple piece families (e.g. KRN_KR, KQR_KQ).
    if not has_pawn and (piece_families != 1):
        return "pawnless"

    if piece_families >= 2:
        return "mixed"

    # Single piece family (may have pawns alongside)
    if has_queen:
        return "queen"
    if has_rook:
        return "rook"
    if has_minor:
        return "minor_piece"
    if has_pawn:
        return "pawn"

    # Should not be reachable, but kept as safety net
    return "pawnless"


# Minimum Stockfish eval (in centipawns) to count as conversion or recovery.
# A single-point eval at the span-entry ply replaces the old material_imbalance +
# 4-ply persistence proxy (REFAC-02). 100 cp == 1.0 pawn — surfaced to the user
# as "+1.0" / "-1.0" in tooltips and bucket labels.
EVAL_ADVANTAGE_THRESHOLD = 100

# Phase 83 (D-07): drop |eval_cp| >= 2000 from the entry_expected_score cohort.
# The Lichess winning-chances sigmoid saturates around +/-800 cp anyway (f(+800) ~
# 0.95, f(+1500) ~ 0.997), so very large evals add almost-1.0 contributions that
# overwhelm the mean. Matches Phase 82's "analyzable endgame entry" cohort
# definition for consistency with the entry_eval bullet (see SEED-014 D-07).
EVAL_CLIP_MAX_CP = 2000

# Phase 85.1 (SEC1-08 / IN-01 carry-forward): n-gate threshold below which any
# p-value is too unstable to surface to the wire. Centralises the previous bare
# `10` occurrences inside `_get_endgame_performance_from_rows` (4 wire-format
# gates) and the new sites Phase 85.1 Plan 02 adds for the score-difference and
# paired-difference tests. CLAUDE.md "No magic numbers" rule — see Phase 85
# REVIEW IN-01 for the carry-forward.
PVALUE_RELIABILITY_MIN_N: int = 10


def _classify_endgame_bucket(
    eval_cp: int | None,
    eval_mate: int | None,
    user_color: str,
) -> Literal["conversion", "parity", "recovery"]:
    """Classify a single endgame span into conversion / parity / recovery.

    Args:
        eval_cp:   White-perspective centipawn eval at span-entry ply (NULL = unknown).
        eval_mate: White-perspective mate-in-N eval at span-entry ply (NULL = not a forced mate).
        user_color: "white" or "black" — determines sign flip.

    Returns:
        "conversion" if the user entered with eval >= +EVAL_ADVANTAGE_THRESHOLD,
        "recovery"   if the user entered with eval <= -EVAL_ADVANTAGE_THRESHOLD,
        "parity"     otherwise (including NULL eval).

    Sign convention:
        Raw SQL eval is always white-perspective. For black users the sign is
        flipped so positive user_eval = user is ahead. Mate scores override cp:
        eval_mate > 0 means the white side has a forced mate; < 0 means black has one.
    """
    # NULL eval routes to parity — engine error or not yet backfilled.
    if eval_mate is None and eval_cp is None:
        return "parity"

    # Determine the user-perspective eval score.
    sign = 1 if user_color == "white" else -1

    if eval_mate is not None:
        # Mate score: a positive value means the side that is to-move has mate,
        # but the raw white-perspective convention treats eval_mate > 0 as white winning.
        # We use large magnitude to guarantee threshold crossing.
        user_eval: int = sign * (1_000_000 if eval_mate > 0 else -1_000_000)
    elif eval_cp is not None:
        user_eval = sign * eval_cp
    else:
        # Both None — already handled by the early return above; unreachable.
        return "parity"

    if user_eval >= EVAL_ADVANTAGE_THRESHOLD:
        return "conversion"
    if user_eval <= -EVAL_ADVANTAGE_THRESHOLD:
        return "recovery"
    return "parity"


# Phase 60: minimum opponent sample size required to display the opponent
# baseline in the Conversion/Even/Recovery bullet chart. Matches the WDL-bar
# mute threshold used elsewhere (e.g. Opening Explorer moves list).
_MIN_OPPONENT_SAMPLE = 10


# Phase 87.1 (SEED-016 D-07): map game result + user_color to a chess score for
# terminal-span exit_score. Named constant per CLAUDE.md "no magic numbers";
# keyed on the outcome returned by derive_user_result (Literal["win","draw","loss"])
# so the dict is exhaustive against the type system.
_GAME_RESULT_TO_SCORE: dict[Literal["win", "draw", "loss"], float] = {
    "win": 1.0,
    "draw": 0.5,
    "loss": 0.0,
}


def _compute_span_gap(
    entry_eval_cp: int | None,
    entry_eval_mate: int | None,
    next_entry_eval_cp: int | None,
    next_entry_eval_mate: int | None,
    result: str,
    user_color: str,
) -> float | None:
    """Return per-span gap `exit_score - ES_entry`, or None if entry eval unavailable.

    Phase 87.1 (SEED-016 D-07). Sign convention: positive = user outperformed
    the Stockfish baseline (recovered eval, decisive conversions); negative =
    user gave back expected score. Matches the page-level Achievable Score Gap
    direction (`higher_is_better`) so the per-type ScoreGapRow reads identically
    to the page-level row on the same visual axis.

    Args:
        entry_eval_cp:       white-perspective cp at the span's first ply.
        entry_eval_mate:     white-perspective mate-in-N at the span's first ply.
        next_entry_eval_cp:  the NEXT span's first-ply cp (from LEAD()); NULL
                             marks a terminal span.
        next_entry_eval_mate: the NEXT span's first-ply mate-in-N; NULL for
                             terminal spans.
        result:              raw Game.result string ("1-0" / "0-1" / "1/2-1/2").
        user_color:          "white" | "black".

    Returns:
        gap_span = exit_score - ES_entry, computed as:
          - ES_entry  = lichess sigmoid over (eval_cp, eval_mate, user_color).
          - exit_score:
            * Transitory span (next_entry_eval_cp OR next_entry_eval_mate
              non-NULL): ES_sigmoid(next_entry_eval, user_color).
            * Terminal span (both next_entry_eval_* NULL): game-result score
              via _GAME_RESULT_TO_SCORE[derive_user_result(result, user_color)].
        Returns None when both entry_eval_cp and entry_eval_mate are NULL —
        the span is excluded from the per-class cohort (D-07: skip NULL-eval).

    Mate handling reuses eval_mate_to_expected_score (mate-in-N saturates to
    0.0 / 1.0 from the user's perspective). No new sigmoid math.
    """
    # D-07: skip spans where the entry eval is unknown. The eval-backfill
    # coverage on >=6-ply spans is effectively 100% in prod, so this is a
    # theoretical edge case — but the gate is total and safe.
    if entry_eval_cp is None and entry_eval_mate is None:
        return None

    # Entry expected score. Mate takes precedence over cp (a forced mate is a
    # terminal evaluation that the sigmoid would mis-compress to a finite value).
    if entry_eval_mate is not None:
        es_entry = eval_mate_to_expected_score(entry_eval_mate, user_color)  # ty: ignore[invalid-argument-type]
    else:
        # entry_eval_cp is non-None here (the early-return above guards the
        # both-NULL case).
        es_entry = eval_cp_to_expected_score(
            entry_eval_cp,  # ty: ignore[invalid-argument-type]
            user_color,  # ty: ignore[invalid-argument-type]
        )

    # Exit score: transitory if any next-span eval is populated, else terminal.
    is_transitory = next_entry_eval_cp is not None or next_entry_eval_mate is not None
    if is_transitory:
        if next_entry_eval_mate is not None:
            exit_score = eval_mate_to_expected_score(next_entry_eval_mate, user_color)  # ty: ignore[invalid-argument-type]
        else:
            exit_score = eval_cp_to_expected_score(
                next_entry_eval_cp,  # ty: ignore[invalid-argument-type]
                user_color,  # ty: ignore[invalid-argument-type]
            )
    else:
        # Terminal span: use the game-result score from the user's perspective.
        outcome = derive_user_result(result, user_color)
        exit_score = _GAME_RESULT_TO_SCORE[outcome]

    return exit_score - es_entry


# Rolling window size for the score-difference timeline chart (quick-260417-o2l).
# Mirrors the 100-game window used by the clock-diff timeline.
SCORE_GAP_TIMELINE_WINDOW = 100


def _aggregate_endgame_stats(
    rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> tuple[list[EndgameCategoryStats], dict[str, list[float]]]:
    """Aggregate raw per-(game, class) endgame rows into EndgameCategoryStats list.

    Each row is: (game_id, endgame_class_int, result, user_color, eval_cp, eval_mate)
    where endgame_class_int is 1-6 (see EndgameClassInt).
    A game_id may appear multiple times (once per endgame class it spent >= 6 plies in).
    Per D-02: multi-class per game.

    Computes per-category:
    - W/D/L counts and percentages
    - Conversion: win rate when user entered with eval advantage (REFAC-02) — D-08
    - Recovery: draw+win rate when user entered with eval deficit (REFAC-02) — D-09

    Phase 87.2 (D-01): also builds gaps_by_bucket — a per-bucket ΔES accumulator
    at per-span grain (not per-game). Returned alongside the categories list so
    the orchestrator can thread it to _compute_score_gap_material.

    Returns (categories, gaps_by_bucket) where categories are sorted by total
    game count descending (D-05) and gaps_by_bucket is a plain dict (not defaultdict).
    """
    if not rows:
        return [], {}

    # Accumulators per endgame class (per D-02: TypedDicts for internal data structures)
    wdl: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "draws": 0, "losses": 0}
    )
    # Conversion: games where user entered with eval advantage
    conv: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )
    # Recovery: games where user entered with eval deficit
    recov: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )
    # Phase 87.1 (SEED-016 D-07): per-class per-span gap accumulator.
    # gap_span = exit_score - ES_entry; positive = outperformed Stockfish baseline.
    # compute_paired_difference_test (from score_confidence.py, same helper as
    # Phase 85.1 SEC1-10 for the page-level Achievable Score Gap) is invoked
    # below in the per-class builder loop.
    gaps_by_class: dict[EndgameClass, list[float]] = defaultdict(list)
    # Phase 87.2 (D-01): per-bucket ΔES accumulator. Shares iteration with
    # gaps_by_class; bucket already computed at the _classify_endgame_bucket
    # call below for the rate-based counts. Per-span grain (not per-game):
    # a game spanning two bucket classes contributes a span-gap to each bucket.
    gaps_by_bucket: dict[str, list[float]] = defaultdict(list)

    for row in rows:
        # Phase 87.1: rows are 8-column SA Rows in prod (Phase 87.1 repo
        # extension) and 6-tuple test fixtures in legacy unit tests. Tuples
        # are padded with NULL next-eval; Rows expose the same columns by
        # attribute. Positional unpacking absorbs both shapes through the
        # branch below.
        if isinstance(row, tuple):
            if len(row) == 6:
                _game_id, endgame_class_int, result, user_color, eval_cp, eval_mate = row
                next_entry_eval_cp: int | None = None
                next_entry_eval_mate: int | None = None
            else:
                # 8-tuple: full new row shape, also valid via positional unpack.
                (
                    _game_id,
                    endgame_class_int,
                    result,
                    user_color,
                    eval_cp,
                    eval_mate,
                    next_entry_eval_cp,
                    next_entry_eval_mate,
                ) = row
        else:
            # SA Row object — attribute access. The repository labels the LEAD
            # columns next_entry_eval_cp / next_entry_eval_mate.
            _game_id = row.game_id
            endgame_class_int = row.endgame_class
            result = row.result
            user_color = row.user_color
            eval_cp = row.eval_cp
            eval_mate = row.eval_mate
            next_entry_eval_cp = row.next_entry_eval_cp
            next_entry_eval_mate = row.next_entry_eval_mate
        endgame_class = _INT_TO_CLASS.get(endgame_class_int)
        if endgame_class is None:
            # Unexpected class integer from DB — surface to Sentry and skip the
            # row rather than 500 the endpoint. Per CLAUDE.md Sentry rules,
            # variables go through set_context; exception message is static so
            # Sentry groups these together instead of per-class_int.
            sentry_sdk.set_context(
                "invalid_endgame_class",
                {"class_int": endgame_class_int},
            )
            sentry_sdk.set_tag("source", "endgame_aggregate")
            sentry_sdk.capture_exception(ValueError("Unknown endgame_class integer from DB"))
            continue
        outcome = derive_user_result(result, user_color)

        # W/D/L counts
        if outcome == "win":
            wdl[endgame_class]["wins"] += 1
        elif outcome == "draw":
            wdl[endgame_class]["draws"] += 1
        else:
            wdl[endgame_class]["losses"] += 1

        bucket = _classify_endgame_bucket(eval_cp, eval_mate, user_color)

        # Conversion: user entered with significant eval advantage (REFAC-02)
        if bucket == "conversion":
            conv[endgame_class]["games"] += 1
            if outcome == "win":
                conv[endgame_class]["wins"] += 1
            elif outcome == "draw":
                conv[endgame_class]["draws"] += 1

        # Recovery: user entered with significant eval deficit (REFAC-02)
        if bucket == "recovery":
            recov[endgame_class]["games"] += 1
            if outcome == "win":
                recov[endgame_class]["wins"] += 1
            elif outcome == "draw":
                recov[endgame_class]["draws"] += 1

        # Phase 87.1 (SEED-016 D-03/D-05/D-07): accumulate per-span gap for the
        # paired one-sample z-test against H0: mean = 0. compute_paired_difference_test
        # from app/services/score_confidence.py is the same helper Phase 85.1
        # SEC1-10 uses for the page-level Achievable Score Gap. Sign convention:
        # gap = exit_score - ES_entry, positive = user outperformed Stockfish.
        # NULL-eval spans return None and are excluded from the cohort (D-07).
        gap = _compute_span_gap(
            entry_eval_cp=eval_cp,
            entry_eval_mate=eval_mate,
            next_entry_eval_cp=next_entry_eval_cp,
            next_entry_eval_mate=next_entry_eval_mate,
            result=result,
            user_color=user_color,
        )
        if gap is not None:
            gaps_by_class[endgame_class].append(gap)
            # Phase 87.2 (D-01): bucket is already computed above; append the
            # same gap into the bucket cohort for the per-bucket paired-z test.
            # Excluded when gap is None (NULL-eval spans, same gate as per-class).
            gaps_by_bucket[bucket].append(gap)

    # Build EndgameCategoryStats objects
    categories: list[EndgameCategoryStats] = []
    for endgame_class in wdl:
        c = wdl[endgame_class]
        wins = c["wins"]
        draws = c["draws"]
        losses = c["losses"]
        total = wins + draws + losses

        if total > 0:
            win_pct = round(wins / total * 100, 1)
            draw_pct = round(draws / total * 100, 1)
            loss_pct = round(losses / total * 100, 1)
        else:
            win_pct = draw_pct = loss_pct = 0.0

        conv_data = conv[endgame_class]
        recov_data = recov[endgame_class]

        conversion_games = conv_data["games"]
        conversion_wins = conv_data["wins"]
        conversion_draws = conv_data["draws"]
        conversion_losses = conversion_games - conversion_wins - conversion_draws
        conversion_pct = (
            round(conversion_wins / conversion_games * 100, 1) if conversion_games > 0 else 0.0
        )

        recovery_games = recov_data["games"]
        recovery_wins = recov_data["wins"]
        recovery_draws = recov_data["draws"]
        recovery_saves = recovery_wins + recovery_draws  # derived, kept for backward compat
        recovery_pct = (
            round(recovery_saves / recovery_games * 100, 1) if recovery_games > 0 else 0.0
        )

        # Phase 84: per-class opponent baseline via same-game mirror identity.
        # Conv is a win-rate, Recov is a save-rate, so the two mirror formulas
        # are asymmetric. Reuses _MIN_OPPONENT_SAMPLE (line 233), gated on the
        # MIRROR bucket size (not the own bucket). Phase 60 introduced the
        # pattern for Section 2 at _compute_score_gap_material (~line 824).
        recovery_losses = recovery_games - recovery_wins - recovery_draws
        opponent_conversion_pct: float | None
        if recovery_games >= _MIN_OPPONENT_SAMPLE:
            opponent_conversion_pct = round(recovery_losses / recovery_games * 100, 1)
        else:
            opponent_conversion_pct = None
        opponent_conversion_games = recovery_games

        opponent_recovery_pct: float | None
        if conversion_games >= _MIN_OPPONENT_SAMPLE:
            opponent_recovery_pct = round(
                (conversion_losses + conversion_draws) / conversion_games * 100, 1
            )
        else:
            opponent_recovery_pct = None
        opponent_recovery_games = conversion_games

        conversion_stats = ConversionRecoveryStats(
            conversion_pct=conversion_pct,
            conversion_games=conversion_games,
            conversion_wins=conversion_wins,
            conversion_draws=conversion_draws,
            conversion_losses=conversion_losses,
            recovery_pct=recovery_pct,
            recovery_games=recovery_games,
            recovery_saves=recovery_saves,
            recovery_wins=recovery_wins,
            recovery_draws=recovery_draws,
            opponent_conversion_pct=opponent_conversion_pct,
            opponent_conversion_games=opponent_conversion_games,
            opponent_recovery_pct=opponent_recovery_pct,
            opponent_recovery_games=opponent_recovery_games,
        )

        # _ENDGAME_CATEGORY_LABELS is exhaustive for all EndgameClass values — direct lookup.
        # endgame_class is always a valid EndgameClass because _INT_TO_CLASS only contains them.
        label = _ENDGAME_CATEGORY_LABELS[endgame_class]

        # Phase 87 follow-up: per-class Wilson score-test p-value vs 50%.
        # Drives the per-card Score bullet sig-gating triple. Same wire-format
        # gate as endgame_score_p_value etc. (PVALUE_RELIABILITY_MIN_N=10).
        _conf_class, p_score_class_raw, _se_class = compute_confidence_bucket(
            wins, draws, losses, total
        )
        score_p_value: float | None = (
            p_score_class_raw if total >= PVALUE_RELIABILITY_MIN_N else None
        )

        # Phase 87.1 (SEED-016 D-03/D-05/D-07): per-class mean per-span gap with
        # paired one-sample z-test via compute_paired_difference_test. n-gates
        # are owned by the helper:
        #   n == 0 -> (0.0, None, None, None) — surface mean as None for wire.
        #   n == 1 -> (mean, None, None, None) — p/CI gated.
        #   n >= 2 -> ci_low/ci_high populated.
        #   n >= CONFIDENCE_MIN_N (=10) -> p_value populated.
        # Sign: exit_score - ES_entry (positive = outperformed Stockfish baseline).
        type_gaps = gaps_by_class[endgame_class]
        type_gap_n = len(type_gaps)
        (
            type_gap_mean_raw,
            type_gap_p,
            type_gap_ci_low,
            type_gap_ci_high,
        ) = compute_paired_difference_test(type_gaps)
        # When n == 0 compute_paired_difference_test returns mean=0.0. Surface
        # None on the wire so the frontend hides the row (D-08 n==0 gate),
        # matching how the cohort-empty case reads.
        type_gap_mean: float | None = type_gap_mean_raw if type_gap_n > 0 else None

        categories.append(
            EndgameCategoryStats(
                endgame_class=endgame_class,
                label=label,
                wins=wins,
                draws=draws,
                losses=losses,
                total=total,
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
                conversion=conversion_stats,
                score_p_value=score_p_value,
                # Phase 87.1 (SEED-016 D-05): per-class Score Gap fields. See
                # _compute_span_gap + compute_paired_difference_test above.
                type_achievable_score_gap_mean=type_gap_mean,
                type_achievable_score_gap_n=type_gap_n,
                type_achievable_score_gap_p_value=type_gap_p,
                type_achievable_score_gap_ci_low=type_gap_ci_low,
                type_achievable_score_gap_ci_high=type_gap_ci_high,
            )
        )

    # Sort by total descending (D-05) — not a fixed category order
    categories.sort(key=lambda c: c.total, reverse=True)

    # Convert defaultdict to plain dict to avoid downstream defaultdict surprises.
    return categories, dict(gaps_by_bucket)


async def get_endgame_stats(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameStatsResponse:
    """Orchestrate endgame stats query and return EndgameStatsResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch one row per (game, endgame_class) span meeting the ply threshold.
    3. Aggregate into per-category stats with conversion/recovery.
    4. Return sorted categories (by total desc, D-05).
    """
    cutoff = recency_cutoff(recency)
    rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # _aggregate_endgame_stats returns (categories, gaps_by_bucket) as of Phase 87.2.
    # get_endgame_stats does not use gaps_by_bucket — it's consumed by get_endgame_overview.
    categories, _gaps_by_bucket = _aggregate_endgame_stats(rows)

    # Total games matching current filters (not just endgame games)
    total_games = await count_filtered_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # Count games that reached an endgame phase per the uniform ENDGAME_PLY_THRESHOLD rule
    # (quick-260414-ae4): a game qualifies if its total endgame plies meet the threshold.
    endgame_games = await count_endgame_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    return EndgameStatsResponse(
        categories=categories,
        total_games=total_games,
        endgame_games=endgame_games,
    )


async def get_endgame_games(
    session: AsyncSession,
    user_id: int,
    endgame_class: EndgameClass,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    offset: int,
    limit: int,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameGamesResponse:
    """Orchestrate endgame games query and return paginated EndgameGamesResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch paginated Game objects for the requested endgame class.
    3. Build GameRecord objects matching the existing analysis schema.
    4. Return EndgameGamesResponse with pagination metadata.
    """
    cutoff = recency_cutoff(recency)
    games, matched_count = await _query_endgame_games(
        session,
        user_id=user_id,
        endgame_class=endgame_class,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        offset=offset,
        limit=limit,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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

    return EndgameGamesResponse(
        games=game_records,
        matched_count=matched_count,
        offset=offset,
        limit=limit,
    )


# --- Performance chart service functions (Phase 32) ---


def _build_wdl_summary(rows: list[Row[Any]]) -> EndgameWDLSummary:
    """Build EndgameWDLSummary from a list of (played_at, result, user_color) rows."""
    wins = draws = losses = 0
    for _played_at, result, user_color in rows:
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
    return EndgameWDLSummary(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
    )


def _wdl_to_score(wdl: EndgameWDLSummary) -> float:
    """Convert WDL summary to score in range 0.0-1.0.

    Score formula: (Win% + Draw%/2) / 100.
    Returns 0.0 for empty WDL (total == 0).
    """
    if wdl.total == 0:
        return 0.0
    return (wdl.win_pct + wdl.draw_pct / 2) / 100


# Display labels for the eval-stratified buckets (section 2 of
# endgame-analysis-v2.md). Threshold values reflect the Stockfish eval at the
# endgame-entry ply (REFAC-02), expressed in pawn units with one decimal place
# to match the rest of the page's eval rendering. Bucket name kept as
# MaterialBucket for wire-format compatibility.
# Unicode: \u2265 = >=, \u2264 = <=, \u2212 = minus sign
_MATERIAL_BUCKET_LABELS: dict[MaterialBucket, str] = {
    "conversion": "Conversion (\u2265 +1.0)",
    "parity": "Parity",
    "recovery": "Recovery (\u2264 \u22121.0)",
}

# Phase 85.1 WR-03: maps the Literal outcomes returned by derive_user_result
# to chess scores. Lifted to module scope so the dict isn't reallocated per
# request, and typed with Literal keys so a future caller indexing with an
# arbitrary string is caught by ty at edit time rather than KeyError at runtime.
_ACTUAL_SCORE_BY_OUTCOME: dict[Literal["win", "draw", "loss"], float] = {
    "win": 1.0,
    "draw": 0.5,
    "loss": 0.0,
}


def _compute_score_gap_timeline(
    endgame_rows: Sequence[Row[Any] | tuple[Any, ...]],
    non_endgame_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int,
    cutoff_str: str | None = None,
) -> list[ScoreGapTimelinePoint]:
    """Weekly rolling-window series of (endgame_score - non_endgame_score).

    Each side maintains its own trailing `window`-game window so weeks with
    sparse activity on one side still reflect the broader history of that
    side — analogous to the per-type series in `get_endgame_timeline`.
    Within the window, score = mean of per-game outcome scores
    (1.0 win / 0.5 draw / 0.0 loss).

    Both inputs carry rows shaped (played_at, result, user_color), already
    sorted ASC by played_at as produced by `query_endgame_performance_rows`.
    Rows missing `played_at` are skipped — they cannot be bucketed by ISO week.

    Output points sit on the Monday of an ISO week and reflect the window
    state after that week's last contributing game on either side. Weeks
    where either trailing window holds fewer than MIN_GAMES_FOR_TIMELINE
    games are dropped — matches the cold-start handling used elsewhere.

    `cutoff_str` (YYYY-MM-DD) drops emitted points dated before the cutoff
    but lets earlier games pre-fill the rolling windows — mirrors
    `get_endgame_timeline` so the recency filter does not starve the window
    when the user picks a short window like "past 3 months".
    """

    def _score_for(row: Row[Any] | tuple[Any, ...]) -> float | None:
        played_at = row[0]
        if played_at is None:
            return None
        outcome = derive_user_result(row[1], row[2])
        return {"win": 1.0, "draw": 0.5, "loss": 0.0}[outcome]

    # Tag each game with its side ("endgame"/"non_endgame") and merge into a
    # single chronological event stream. We can't just walk both lists in
    # lockstep — events must interleave by played_at to keep the rolling
    # windows in sync with real history.
    events: list[tuple[Any, Literal["endgame", "non_endgame"], float]] = []
    for row in endgame_rows:
        score = _score_for(row)
        if score is None:
            continue
        events.append((row[0], "endgame", score))
    for row in non_endgame_rows:
        score = _score_for(row)
        if score is None:
            continue
        events.append((row[0], "non_endgame", score))

    events.sort(key=lambda e: e[0])

    endgame_window: list[float] = []
    non_endgame_window: list[float] = []
    # Per-ISO-week count of all events (endgame + non-endgame) — drives the
    # frontend volume bars. Mirrors `per_week_count` in
    # `_compute_endgame_elo_weekly_series` (Phase 57.1 D-06).
    per_week_total: dict[tuple[int, int], int] = {}
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, side, score in events:
        if side == "endgame":
            endgame_window.append(score)
            endgame_window = endgame_window[-window:]
        else:
            non_endgame_window.append(score)
            non_endgame_window = non_endgame_window[-window:]

        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        per_week_total[(iso_year, iso_week)] = per_week_total.get((iso_year, iso_week), 0) + 1

        eg_count = len(endgame_window)
        neg_count = len(non_endgame_window)
        if eg_count == 0 or neg_count == 0:
            # Can't compute a difference until both sides have at least one
            # game; defer emission. The MIN_GAMES_FOR_TIMELINE filter below
            # also drops anything still too thin once both sides start.
            continue

        endgame_mean = statistics.mean(endgame_window)
        non_endgame_mean = statistics.mean(non_endgame_window)
        diff = endgame_mean - non_endgame_mean

        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        # sanity: score_difference == endgame_score - non_endgame_score within
        # rounding (1e-9 target; all three rounded to 4 decimals here). Phase 68
        # persists the absolute per-side values so the frontend two-line chart
        # and the `score_timeline` insights subsection can read them directly
        # instead of reconstructing them from the signed difference.
        data_by_week[(iso_year, iso_week)] = {
            "date": monday.isoformat(),
            "score_difference": round(diff, 4),
            "endgame_game_count": eg_count,
            "non_endgame_game_count": neg_count,
            "per_week_total_games": per_week_total[(iso_year, iso_week)],
            "endgame_score": round(endgame_mean, 4),
            "non_endgame_score": round(non_endgame_mean, 4),
        }

    return [
        ScoreGapTimelinePoint(**data_by_week[key])
        for key in sorted(data_by_week.keys())
        if data_by_week[key]["endgame_game_count"] >= MIN_GAMES_FOR_TIMELINE
        and data_by_week[key]["non_endgame_game_count"] >= MIN_GAMES_FOR_TIMELINE
        and (cutoff_str is None or data_by_week[key]["date"] >= cutoff_str)
    ]


def _aggregate_bucket_counts(
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> tuple[
    dict[MaterialBucket, int],
    dict[MaterialBucket, int],
    dict[MaterialBucket, int],
    dict[MaterialBucket, int],
]:
    """Group endgame entry rows by game and tally WDL per bucket.

    Per-game bucket selection priority (Phase 59 / REFAC-02):
      1) any row satisfying CONVERSION (eval >= +1.0, user perspective)
      2) else any row satisfying RECOVERY (eval <= -1.0)
      3) else fall back to the row with the LOWEST endgame_class_int (deterministic);
         bucket as "parity".

    Conversion-over-recovery tiebreak (1 > 2): when a game has BOTH, bucket as
    "conversion". Reaching a winning position is the earlier causal event in the
    game. Inverting would double-penalize conversion failures. Do NOT change
    without updating tests/test_endgame_service.py::TestScoreGapMaterialInvariant.

    NULL eval rows route to "parity" via _classify_endgame_bucket so they fall
    through to priority 3, preserving sum(material_rows.games) == endgame_wdl.total.

    Returns: (bucket_wins, bucket_draws, bucket_losses, bucket_games) — each a
    dict keyed by MaterialBucket.
    """
    bucket_wins: dict[MaterialBucket, int] = {"conversion": 0, "parity": 0, "recovery": 0}
    bucket_draws: dict[MaterialBucket, int] = {"conversion": 0, "parity": 0, "recovery": 0}
    bucket_losses: dict[MaterialBucket, int] = {"conversion": 0, "parity": 0, "recovery": 0}
    bucket_games: dict[MaterialBucket, int] = {"conversion": 0, "parity": 0, "recovery": 0}

    # rows carry labeled columns in prod (see query_endgame_bucket_rows /
    # query_endgame_entry_rows) and a matching NamedTuple stand-in in tests,
    # so attribute access is valid in both cases.
    rows_by_game: dict[int, list[Row[Any]]] = defaultdict(list)
    for row in entry_rows:
        rows_by_game[row.game_id].append(row)  # ty: ignore[unresolved-attribute, invalid-argument-type] — labeled Row / NamedTuple row

    for _, game_rows in rows_by_game.items():
        chosen_row: Row[Any] | None = None
        chosen_bucket: MaterialBucket = "parity"

        for r in game_rows:
            if _classify_endgame_bucket(r.eval_cp, r.eval_mate, r.user_color) == "conversion":
                chosen_row = r
                chosen_bucket = "conversion"
                break

        if chosen_row is None:
            for r in game_rows:
                if _classify_endgame_bucket(r.eval_cp, r.eval_mate, r.user_color) == "recovery":
                    chosen_row = r
                    chosen_bucket = "recovery"
                    break

        if chosen_row is None:
            chosen_row = min(game_rows, key=lambda r: r.endgame_class)
            chosen_bucket = "parity"

        outcome = derive_user_result(chosen_row.result, chosen_row.user_color)
        bucket_games[chosen_bucket] += 1
        if outcome == "win":
            bucket_wins[chosen_bucket] += 1
        elif outcome == "draw":
            bucket_draws[chosen_bucket] += 1
        else:
            bucket_losses[chosen_bucket] += 1

    return bucket_wins, bucket_draws, bucket_losses, bucket_games


def _bucket_pcts_and_scores(
    bucket_wins: dict[MaterialBucket, int],
    bucket_draws: dict[MaterialBucket, int],
    bucket_losses: dict[MaterialBucket, int],
    bucket_games: dict[MaterialBucket, int],
) -> tuple[dict[MaterialBucket, float], dict[MaterialBucket, tuple[float, float, float]]]:
    """First pass over the bucket counts -> per-bucket chess-score and (win_pct,
    draw_pct, loss_pct) needed for the MaterialRow construction loop."""
    bucket_score: dict[MaterialBucket, float] = {"conversion": 0.0, "parity": 0.0, "recovery": 0.0}
    bucket_pct: dict[MaterialBucket, tuple[float, float, float]] = {}
    for bucket_key in ("conversion", "parity", "recovery"):
        b: MaterialBucket = bucket_key
        games = bucket_games[b]
        if games > 0:
            win_pct = round(bucket_wins[b] / games * 100, 1)
            draw_pct = round(bucket_draws[b] / games * 100, 1)
            loss_pct = round(bucket_losses[b] / games * 100, 1)
            bucket_score[b] = (win_pct + draw_pct / 2) / 100
        else:
            win_pct = draw_pct = loss_pct = 0.0
            bucket_score[b] = 0.0
        bucket_pct[b] = (win_pct, draw_pct, loss_pct)
    return bucket_score, bucket_pct


# Phase 87.2 (D-05): _MIRROR_BUCKET and opponent_score / diff_* fields deleted.
# The peer-bullet WDL sig-test approach (Phase 60/86) is replaced by the
# per-bucket ΔES Score Gap metric (Phase 87.2).


def _build_material_rows(
    bucket_wins: dict[MaterialBucket, int],
    bucket_draws: dict[MaterialBucket, int],
    bucket_losses: dict[MaterialBucket, int],
    bucket_games: dict[MaterialBucket, int],
    bucket_score: dict[MaterialBucket, float],
    bucket_pct: dict[MaterialBucket, tuple[float, float, float]],
) -> list[MaterialRow]:
    """Build the 3 MaterialRow records (conversion/parity/recovery) with WDL
    percentages and chess score per bucket. Opponent-score mirror fields and
    per-bucket peer-bullet sig fields were deleted in Phase 87.2 (D-05)."""
    material_rows: list[MaterialRow] = []
    for bucket_key in ("conversion", "parity", "recovery"):
        b2: MaterialBucket = bucket_key
        win_pct, draw_pct, loss_pct = bucket_pct[b2]
        material_rows.append(
            MaterialRow(
                bucket=b2,
                label=_MATERIAL_BUCKET_LABELS[b2],
                games=bucket_games[b2],
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
                score=bucket_score[b2],
            )
        )
    return material_rows


def _compute_per_bucket_score_gap(
    gaps_by_bucket: dict[str, list[float]],
) -> dict[MaterialBucket, tuple[float | None, int, float | None, float | None, float | None]]:
    """Compute per-bucket ΔES Score Gap stats using compute_paired_difference_test.

    Returns a dict keyed by bucket with (mean, n, p_value, ci_low, ci_high).
    Mean is gated to None when n == 0 to prevent the helper's 0.0 default from
    polluting the wire (per RESEARCH §Pitfall 2).

    Sign convention: positive mean = user's exit_score exceeded Stockfish baseline
    (exit_score - ES_entry > 0 = outperformed). Matches Phase 87.1's per-class sign.
    """
    result: dict[
        MaterialBucket, tuple[float | None, int, float | None, float | None, float | None]
    ] = {}
    for bucket in ("conversion", "parity", "recovery"):
        b: MaterialBucket = bucket
        gaps = gaps_by_bucket.get(b, [])
        n = len(gaps)
        mean_raw, p_val, ci_lo, ci_hi = compute_paired_difference_test(gaps)
        # Gate mean to None when cohort is empty — avoids 0.0 polluting wire.
        mean_out: float | None = mean_raw if n > 0 else None
        result[b] = (mean_out, n, p_val, ci_lo, ci_hi)
    return result


def _compute_skill_score_gap(
    per_bucket: dict[
        MaterialBucket, tuple[float | None, int, float | None, float | None, float | None]
    ],
) -> tuple[float | None, int, float | None, float | None, float | None]:
    """Equal-weighted Skill aggregator over the three per-bucket ΔES results (D-01).

    Active buckets are those with n >= CONFIDENCE_MIN_N. The denominator drops
    sparse buckets (D-01): Skill = mean(mean_b for active b).

    CI propagation uses variance-of-sum / n_active² (Open Q §3 Option A):
      SE_b = (ci_high_b - ci_low_b) / (2 * CI_Z_95)
      SE_skill = sqrt(sum(SE_b²)) / n_active
      ci_low  = skill_mean - CI_Z_95 * SE_skill
      ci_high = skill_mean + CI_Z_95 * SE_skill

    Returns (skill_mean, skill_n, skill_p, skill_ci_low, skill_ci_high).
    skill_mean is None when n_active == 0. p_value is derived from two-sided
    normal z-test via erfc; None when SE_skill == 0 (degenerate constant signal).
    """
    active_buckets: list[MaterialBucket] = []
    for bucket in ("conversion", "parity", "recovery"):
        b: MaterialBucket = bucket
        _, n_b, _, _, _ = per_bucket[b]
        if n_b >= CONFIDENCE_MIN_N:
            active_buckets.append(b)

    n_active = len(active_buckets)

    if n_active == 0:
        return None, 0, None, None, None

    skill_n = sum(per_bucket[b][1] for b in active_buckets)
    skill_mean = sum(per_bucket[b][0] for b in active_buckets) / n_active  # type: ignore[misc]

    # Recover SE per active bucket from CI bounds (guaranteed populated: n >= 10 >= 2).
    se_sq_sum = 0.0
    for b in active_buckets:
        ci_lo_b = per_bucket[b][3]
        ci_hi_b = per_bucket[b][4]
        # ci_lo/ci_hi are None only when n < 2, but CONFIDENCE_MIN_N=10 >= 2,
        # so active buckets always have both CI bounds. Guard defensively.
        if ci_lo_b is not None and ci_hi_b is not None:
            se_b = (ci_hi_b - ci_lo_b) / (2.0 * CI_Z_95)
            se_sq_sum += se_b * se_b

    se_skill = math.sqrt(se_sq_sum) / n_active

    if se_skill == 0.0:
        # Degenerate: all active bucket means equal and zero SE. No informative CI.
        return skill_mean, skill_n, None, None, None

    # Two-sided z-test p-value: 2 * (1 - Phi(|z|)) = erfc(|z| / sqrt(2)).
    z_skill = abs(skill_mean / se_skill)
    skill_p: float = math.erfc(z_skill / math.sqrt(2.0))
    skill_ci_low = skill_mean - CI_Z_95 * se_skill
    skill_ci_high = skill_mean + CI_Z_95 * se_skill

    return skill_mean, skill_n, skill_p, skill_ci_low, skill_ci_high


def _compute_score_gap_material(
    endgame_wdl: EndgameWDLSummary,
    non_endgame_wdl: EndgameWDLSummary,
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
    *,
    gaps_by_bucket: dict[str, list[float]] | None = None,
    timeline: list[ScoreGapTimelinePoint] | None = None,
    timeline_window: int = SCORE_GAP_TIMELINE_WINDOW,
) -> ScoreGapMaterialResponse:
    """Compute endgame score gap and eval-stratified WDL table.

    Buckets are split by the Stockfish evaluation at the endgame-entry ply
    (REFAC-02 — the old material_imbalance + 4-ply persistence proxy is gone):
    conversion (eval >= +1.0), recovery (eval <= -1.0), parity (in between).
    Function and field names retain the `material` prefix for wire-format
    compatibility with the response schema (ScoreGapMaterialResponse).

    Args:
        endgame_wdl: WDL summary for games that reached an endgame.
        non_endgame_wdl: WDL summary for games that never reached an endgame.
        entry_rows: One row per endgame game from query_endgame_bucket_rows.
            Each row: (game_id, endgame_class_int, result, user_color,
                       eval_cp, eval_mate).
            Both endgame_wdl and entry_rows are produced with the uniform
            ENDGAME_PLY_THRESHOLD HAVING (quick-260414-ae4), so they count the
            same population of games — `sum(material_rows.games) ==
            endgame_wdl.total` holds by construction. The function still
            dedupes by game_id defensively. For any game where
            eval_cp/eval_mate is NULL (not yet backfilled), the game routes to
            the "parity" bucket via _classify_endgame_bucket.
        gaps_by_bucket: Phase 87.2 (D-01/D-06). Per-bucket ΔES span-gap
            accumulator produced by _aggregate_endgame_stats. Keys are
            "conversion", "parity", "recovery". None or missing keys treated
            as empty cohorts.
        timeline: Pre-computed score-gap timeline. The orchestrator builds
            this from the unfiltered-by-recency performance rows (so the
            rolling window is pre-filled with games before the cutoff) and
            then filters output points to the cutoff. None -> empty timeline.
        timeline_window: Window size carried on the response for the chart's
            tooltip/info copy.

    Returns:
        ScoreGapMaterialResponse with score gap and 3-row material breakdown.
    """
    # Phase 85.1 WR-01: use raw integer W/D/N counts (not the rounded
    # win_pct/draw_pct from _build_wdl_summary) so the response field shares a
    # single source of truth with the CI midpoint computed by
    # compute_score_difference_test below. _wdl_to_score rounds to 0.1% before
    # dividing, which could disagree with the CI center by up to ~0.001.
    endgame_score = (
        (endgame_wdl.wins + 0.5 * endgame_wdl.draws) / endgame_wdl.total
        if endgame_wdl.total > 0
        else 0.0
    )
    non_endgame_score = (
        (non_endgame_wdl.wins + 0.5 * non_endgame_wdl.draws) / non_endgame_wdl.total
        if non_endgame_wdl.total > 0
        else 0.0
    )
    score_difference = endgame_score - non_endgame_score

    # Phase 85.1 (SEC1-08 / SEC1-09): independent two-sample z-test on the
    # chess-score difference. Helper gates p_value at min(eg, ne) >=
    # PVALUE_RELIABILITY_MIN_N=10 and CI bounds at min(eg, ne) >= 2;
    # SE_diff=0 trap resolves the degenerate-both-sides case to {0.0, 1.0}.
    score_diff_p, score_diff_ci_low, score_diff_ci_high = compute_score_difference_test(
        endgame_wdl.wins,
        endgame_wdl.draws,
        endgame_wdl.losses,
        endgame_wdl.total,
        non_endgame_wdl.wins,
        non_endgame_wdl.draws,
        non_endgame_wdl.losses,
        non_endgame_wdl.total,
    )

    bucket_wins, bucket_draws, bucket_losses, bucket_games = _aggregate_bucket_counts(entry_rows)

    bucket_score, bucket_pct = _bucket_pcts_and_scores(
        bucket_wins, bucket_draws, bucket_losses, bucket_games
    )
    material_rows = _build_material_rows(
        bucket_wins, bucket_draws, bucket_losses, bucket_games, bucket_score, bucket_pct
    )

    # Phase 87.2 (D-01/D-05/D-06): per-bucket ΔES + equal-weighted Skill aggregator.
    # Replaces _compute_skill_wire composite Wald-z (D-05).
    # Sign: exit_score - ES_entry, positive = user outperformed Stockfish baseline.
    # Skill CI: variance-of-sum / n_active² propagation from 3 independent
    # paired-z outputs (Open Q §3 option A).
    resolved_gaps: dict[str, list[float]] = gaps_by_bucket if gaps_by_bucket is not None else {}
    per_bucket = _compute_per_bucket_score_gap(resolved_gaps)

    conv_mean, conv_n, conv_p, conv_ci_lo, conv_ci_hi = per_bucket["conversion"]
    parity_mean, parity_n, parity_p, parity_ci_lo, parity_ci_hi = per_bucket["parity"]
    recov_mean, recov_n, recov_p, recov_ci_lo, recov_ci_hi = per_bucket["recovery"]

    skill_mean, skill_n, skill_p, skill_ci_lo, skill_ci_hi = _compute_skill_score_gap(per_bucket)

    # quick-260515-wye: rate-based Endgame Skill composite for the gauge.
    # Equal-weighted mean of chess-scores over active buckets (n >= floor).
    # Restores the gauge driver dropped by Phase 87.2 D-05; the ΔES skill
    # mean above drives the bullet, not the gauge.
    active_rate_buckets: list[MaterialBucket] = [
        b for b in ("conversion", "parity", "recovery") if bucket_games[b] >= CONFIDENCE_MIN_N
    ]
    endgame_skill_rate_mean: float | None = (
        sum(bucket_score[b] for b in active_rate_buckets) / len(active_rate_buckets)
        if active_rate_buckets
        else None
    )

    return ScoreGapMaterialResponse(
        endgame_score=endgame_score,
        non_endgame_score=non_endgame_score,
        score_difference=score_difference,
        material_rows=material_rows,
        timeline=timeline if timeline is not None else [],
        timeline_window=timeline_window,
        score_difference_p_value=score_diff_p,
        score_difference_ci_low=score_diff_ci_low,
        score_difference_ci_high=score_diff_ci_high,
        # Phase 87.2 (D-06): per-bucket ΔES Score Gap fields.
        section2_score_gap_conv_mean=conv_mean,
        section2_score_gap_conv_n=conv_n,
        section2_score_gap_conv_p_value=conv_p,
        section2_score_gap_conv_ci_low=conv_ci_lo,
        section2_score_gap_conv_ci_high=conv_ci_hi,
        section2_score_gap_parity_mean=parity_mean,
        section2_score_gap_parity_n=parity_n,
        section2_score_gap_parity_p_value=parity_p,
        section2_score_gap_parity_ci_low=parity_ci_lo,
        section2_score_gap_parity_ci_high=parity_ci_hi,
        section2_score_gap_recov_mean=recov_mean,
        section2_score_gap_recov_n=recov_n,
        section2_score_gap_recov_p_value=recov_p,
        section2_score_gap_recov_ci_low=recov_ci_lo,
        section2_score_gap_recov_ci_high=recov_ci_hi,
        section2_score_gap_skill_mean=skill_mean,
        section2_score_gap_skill_n=skill_n,
        section2_score_gap_skill_p_value=skill_p,
        section2_score_gap_skill_ci_low=skill_ci_lo,
        section2_score_gap_skill_ci_high=skill_ci_hi,
        endgame_skill_rate_mean=endgame_skill_rate_mean,
    )


# Minimum endgame games per time control to include a row in the clock stats table.
# Rows below this threshold are too sparse for meaningful averages.
MIN_GAMES_FOR_CLOCK_STATS = 10

# Number of time-remaining buckets for the pressure-performance chart (Phase 55).
NUM_BUCKETS = 10
BUCKET_WIDTH_PCT = 10  # each bucket spans 10 percentage points

# Clamp: games where either clock at endgame entry exceeds this multiple of
# base_time_seconds are treated as bad data (bogus clock readings, e.g. from
# adjudicated or disconnected games). 2x handles legitimate banked increment
# (p99 in prod is 109%), but >200% is noise (saw max 2047% in prod).
MAX_CLOCK_PCT_OF_BASE = 2.0

# Display labels for time control buckets.
_TIME_CONTROL_LABELS: dict[str, str] = {
    "bullet": "Bullet",
    "blitz": "Blitz",
    "rapid": "Rapid",
    "classical": "Classical",
}

# Fixed display order for time control rows (fastest to slowest).
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]

# Rolling window size for the clock-diff timeline chart (quick-260416-w3q).
# Mirrors the 100-game window the frontend uses for the Win Rate by Endgame Type chart.
CLOCK_PRESSURE_TIMELINE_WINDOW = 100

# Rolling window size for the Endgame ELO timeline chart (Phase 57 ELO-05).
# Matches SCORE_GAP_TIMELINE_WINDOW and CLOCK_PRESSURE_TIMELINE_WINDOW per D-05.
ENDGAME_ELO_TIMELINE_WINDOW = 100

# Clamp bounds for the Endgame ELO formula (Phase 57 D-01). Skill outside this
# range would blow up log10(skill / (1 - skill)); clamping caps contribution at
# roughly +-510 Elo above/below opponent average, which is well beyond realistic
# performance-rating territory for any plausible sample size.
_ENDGAME_ELO_SKILL_CLAMP_LO = 0.05
_ENDGAME_ELO_SKILL_CLAMP_HI = 0.95

# Ordered combo list: chess.com first then lichess, per-platform follows
# _TIME_CONTROL_ORDER. Used for stable response ordering (Phase 57 D-09).
_ENDGAME_ELO_COMBO_ORDER: list[tuple[str, str]] = [
    (platform_name, tc) for platform_name in ("chess.com", "lichess") for tc in _TIME_CONTROL_ORDER
]


def _endgame_elo_from_skill(skill: float, actual_elo_at_date: float) -> int:
    """Skill-adjusted rating from skill composite + actual rating anchor (Phase 57.1 D-01).

    endgame_elo = round(actual_elo_at_date + 400 * log10(s / (1 - s))) where s is skill
    clamped to [_ENDGAME_ELO_SKILL_CLAMP_LO, _ENDGAME_ELO_SKILL_CLAMP_HI].

    When skill == 0.5 the log10 term is 0, so endgame_elo == actual_elo_at_date. Both
    timeline lines coincide at the neutral skill mark. 75 % skill puts endgame_elo
    roughly +190 Elo above; 25 % skill puts it roughly -190 Elo below. The anchor
    change (Phase 57.1) replaces the old opponent-average anchor; this is no longer a
    classical performance metric, it is a skill-adjusted rating.

    Pure function. Safe for skill=0.0 and skill=1.0 by construction (clamp is applied
    unconditionally before the log10 / division).
    """
    s = max(_ENDGAME_ELO_SKILL_CLAMP_LO, min(_ENDGAME_ELO_SKILL_CLAMP_HI, skill))
    return round(actual_elo_at_date + 400 * math.log10(s / (1 - s)))


def _endgame_skill_from_bucket_rows(
    rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> float | None:
    """Composite Endgame Skill rate from per-game bucket rows.

    Ports the frontend `endgameSkill()` helper in
    `frontend/src/components/charts/EndgameScoreGapSection.tsx` (lines 167-177).
    TODO (Phase 56): deduplicate with the backend endgame_skill() port introduced
    by Phase 56 when that phase lands.

    Row tuple shape (matches query_endgame_elo_timeline_rows bucket output):
        (played_at, platform, time_control_bucket, user_color,
         white_rating, black_rating, eval_cp, eval_mate, result).

    Bucketing (matches _compute_score_gap_material via _classify_endgame_bucket):
    - conversion: _classify_endgame_bucket returns "conversion" (eval >= +EVAL_ADVANTAGE_THRESHOLD)
        -> per-row rate = 1 if user won else 0 (Conv Win %)
    - recovery: _classify_endgame_bucket returns "recovery" (eval <= -EVAL_ADVANTAGE_THRESHOLD)
        -> per-row rate = 1 if user won or drew else 0 (Recov Save %)
    - parity: everything else (NULL eval routes here via _classify_endgame_bucket)
        -> per-row rate = user chess score (1 for win, 0.5 for draw, 0 for loss;
        Parity Score %)

    Returns mean-across-non-empty-buckets of per-bucket mean rates. Returns
    None when all three buckets are empty (<=0 games total).
    """
    conv_count = 0
    conv_wins = 0
    recov_count = 0
    recov_saves = 0  # wins + draws
    par_count = 0
    par_score_sum = 0.0

    for row in rows:
        # Tuple unpacking per Pitfall 5 (avoid ty row-attribute errors).
        (
            _played_at,
            _platform,
            _tc,
            user_color,
            _white_rating,
            _black_rating,
            eval_cp,
            eval_mate,
            result,
        ) = row

        outcome = derive_user_result(result, user_color)  # "win"/"draw"/"loss"
        bucket = _classify_endgame_bucket(eval_cp, eval_mate, user_color)

        if bucket == "conversion":
            conv_count += 1
            if outcome == "win":
                conv_wins += 1
        elif bucket == "recovery":
            recov_count += 1
            if outcome in ("win", "draw"):
                recov_saves += 1
        else:
            par_count += 1
            par_score_sum += {"win": 1.0, "draw": 0.5, "loss": 0.0}[outcome]

    rates: list[float] = []
    if conv_count > 0:
        rates.append(conv_wins / conv_count)
    if recov_count > 0:
        rates.append(recov_saves / recov_count)
    if par_count > 0:
        rates.append(par_score_sum / par_count)

    if not rates:
        return None
    return sum(rates) / len(rates)


def _compute_endgame_elo_weekly_series(
    bucket_rows: Sequence[Row[Any] | tuple[Any, ...]],
    all_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int,
    actual_elo_dates: Sequence[datetime],
    actual_elo_ratings: Sequence[int],
    cutoff_str: str | None = None,
) -> list[EndgameEloTimelinePoint]:
    """Co-compute weekly Endgame ELO + Actual ELO rolling series for one combo (Phase 57.1).

    Walks a merged chronological event stream of endgame bucket rows + all-games
    rows, maintaining one trailing window of bucket rows for the skill composite.
    At each ISO-week boundary, emits one point dated to the ISO-Sunday
    (end of week) with:
    - actual_elo = asof-join of (actual_elo_dates, actual_elo_ratings) at the
        ISO-week-end timestamp (Monday + 7 days, exclusive). Forward-fills from
        the latest prior game when the week itself has no games (D-02). The
        plotted date (Sunday) matches when this rating was measured — so a daily
        rating chart at the same date shows the same value (assuming matching
        filters).
    - endgame_elo = _endgame_elo_from_skill(skill, actual_elo) — both lines share
        the asof rating anchor (D-04).
    - endgame_games_in_window = len(endgame_window).
    - per_week_endgame_games = count of endgame events for this specific ISO week
        (NOT the trailing-window count). Drives the frontend volume bars (D-06).

    Per-point emission requires endgame_window_count >= MIN_GAMES_FOR_TIMELINE
    (D-06 carry-over from Phase 57). `cutoff_str` filters output points to
    >= cutoff while letting earlier games pre-fill the windows (Pitfall 2).

    bucket_rows tuple shape matches query_endgame_elo_timeline_rows bucket output:
      (played_at, platform, tc, user_color, white_rating, black_rating,
       eval_cp, eval_mate, result)
    all_rows tuple shape:
      (played_at, platform, tc, user_color, white_rating, black_rating)
    actual_elo_dates / actual_elo_ratings: parallel arrays sorted by date ASC,
        pre-computed by the orchestrator from this combo's all_rows. Derived from
        white_rating/black_rating by user_color. NULL-rating rows are excluded by
        the orchestrator before these arrays are built.
    """
    # Merge into single chronological stream. Tag each event with its side.
    events: list[tuple[Any, Literal["endgame", "all"], tuple[Any, ...]]] = []
    for row in bucket_rows:
        if row[0] is None:
            continue
        events.append((row[0], "endgame", tuple(row)))
    for row in all_rows:
        if row[0] is None:
            continue
        events.append((row[0], "all", tuple(row)))

    # Stable chronological sort. Ties broken by side tag so deterministic.
    events.sort(key=lambda e: (e[0], e[1]))

    endgame_window: list[tuple[Any, ...]] = []  # bucket rows for skill composite
    per_week_count: dict[tuple[int, int], int] = {}  # NEW (D-06): per-ISO-week endgame counts
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, side, row in events:
        # BUGFIX (Phase 57.1 WR-02): only emit on endgame events. Previously the
        # emission block ran for every merged event (endgame + "all"), so an
        # "all" event in a new ISO week with no endgame games yet would still
        # produce an emission with per_week_endgame_games=0. That contradicts
        # the docstring ("only emits on endgame events") and misleads the
        # frontend tooltip.
        if side != "endgame":
            continue

        endgame_window.append(row)
        endgame_window = endgame_window[-window:]
        iso_year_evt, iso_week_evt, _ = played_at.isocalendar()
        per_week_count[(iso_year_evt, iso_week_evt)] = (
            per_week_count.get((iso_year_evt, iso_week_evt), 0) + 1
        )

        # Require endgame window >= threshold for emission. NOTE (Phase 57.1):
        # the rolling user-rating mean from Phase 57 is gone — actual_elo now
        # comes from the per-combo asof arrays passed in by the orchestrator.
        if len(endgame_window) < MIN_GAMES_FOR_TIMELINE:
            continue

        skill = _endgame_skill_from_bucket_rows(endgame_window)
        if skill is None:
            continue

        # Compute the ISO-week emission key + monday + asof cutoff (Phase 57.1 D-01/D-02).
        # Cutoff = start of NEXT Monday (Pitfall 2): inclusive of any Sunday game.
        # BUGFIX (Phase 57.1 WR-01): pin monday_dt / next_monday_dt to midnight at the
        # ISO boundary. Previously these carried played_at's time-of-day, so the
        # bisect_right cutoff drifted up to 24h into the next ISO week — letting a
        # Monday-morning rating from week N+1 leak into week N's actual_elo.
        # Preserve tzinfo so the bisect comparison stays on the same tz axis
        # (played_at is tz-aware in production via DateTime(timezone=True)).
        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        monday_dt = datetime.combine(monday, time.min, tzinfo=played_at.tzinfo)
        next_monday_dt = monday_dt + timedelta(days=7)
        # Stored date is the ISO-Sunday (end of week). The asof rating reflects
        # end-of-Sunday, so the plotted date must match that moment — otherwise
        # a daily rating chart (e.g. Global Stats RatingChart) at the same date
        # shows a rating that lags the Endgame Timeline by 6 days (Phase 57.1
        # polish of D-02 framing).
        sunday = monday + timedelta(days=6)

        idx = bisect.bisect_right(actual_elo_dates, next_monday_dt)
        if idx == 0:
            # No prior game — unreachable in practice because the >=10-endgame-games
            # floor above prevents emission before the bucket window fills (which
            # itself requires games to have been played). Defensive skip.
            continue
        actual_elo_at_date = actual_elo_ratings[idx - 1]

        endgame_elo = _endgame_elo_from_skill(skill, float(actual_elo_at_date))

        data_by_week[(iso_year, iso_week)] = {
            "date": sunday.isoformat(),
            "endgame_elo": endgame_elo,
            "actual_elo": int(actual_elo_at_date),
            "endgame_games_in_window": len(endgame_window),
            "per_week_endgame_games": per_week_count.get((iso_year, iso_week), 0),
        }

    return [
        EndgameEloTimelinePoint(**data_by_week[key])
        for key in sorted(data_by_week.keys())
        if cutoff_str is None or data_by_week[key]["date"] >= cutoff_str
    ]


def _extract_entry_clocks(
    plies: list[int],
    clocks: list[float | None],
    user_color: str,
) -> tuple[float | None, float | None]:
    """Return (user_entry_clock, opp_entry_clock) at endgame entry.

    user_color determines ply parity: white=even plies (0,2,4,...), black=odd plies (1,3,...).
    Scans the ply/clock arrays and returns the first non-None clock for each parity.
    Returns (None, None) if the expected entry plies have no clock data.
    """
    user_parity = 0 if user_color == "white" else 1
    user_clock: float | None = None
    opp_clock: float | None = None
    for ply, clock in zip(plies, clocks):
        if ply % 2 == user_parity and user_clock is None:
            user_clock = clock
        elif ply % 2 != user_parity and opp_clock is None:
            opp_clock = clock
        if user_clock is not None and opp_clock is not None:
            break
    return user_clock, opp_clock


def _compute_clock_pressure(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
    *,
    timeline: list[ClockPressureTimelinePoint] | None = None,
    timeline_window: int = CLOCK_PRESSURE_TIMELINE_WINDOW,
) -> ClockPressureResponse:
    """Compute time pressure stats at endgame entry, grouped by time control.

    Each row from query_clock_stats_rows has the shape:
    (game_id, time_control_bucket, base_time_seconds, termination, result,
     user_color, ply_array, clock_array)

    query_clock_stats_rows returns one row per qualifying game (whole-game 6-ply
    rule via _any_endgame_ply_subquery, per quick-260414-pv4), so no Python-side
    deduplication is needed — rows can be iterated directly.

    Percentage is computed per-game as user_clock / base_time_seconds * 100,
    where base_time_seconds is the actual starting clock for that game (e.g. 600
    for a 600+0 game, 900 for a 900+10 game). This avoids the old bucket-first-seen
    bug where time_control_seconds (base + inc*40) mixed different starting clocks
    within a bucket (quick-260414-smt).

    Games where either clock exceeds MAX_CLOCK_PCT_OF_BASE * base_time_seconds are
    excluded entirely from clock accumulation as bad data.

    Returns ClockPressureResponse with:
    - rows: one ClockStatsRow per time control with >= MIN_GAMES_FOR_CLOCK_STATS games
    - total_clock_games: total endgame games with both entry clocks present
    - total_endgame_games: total distinct endgame games (all time controls, pre-filter)
    """
    # Previously collapsed multi-span rows to the earliest span per game; SQL now
    # delivers one row per game (whole-game rule, quick-260414-pv4), so we iterate directly.

    # Accumulators per time control bucket.
    # Using plain dicts to avoid ty complaints with mutable defaults in TypedDict.
    tc_game_ids: dict[str, set[int]] = defaultdict(set)
    tc_timeout_win_ids: dict[str, set[int]] = defaultdict(set)
    tc_timeout_loss_ids: dict[str, set[int]] = defaultdict(set)
    tc_user_clocks: dict[str, list[float]] = defaultdict(list)
    tc_opp_clocks: dict[str, list[float]] = defaultdict(list)
    tc_clock_diffs: dict[str, list[float]] = defaultdict(list)
    tc_user_pcts: dict[str, list[float]] = defaultdict(list)
    tc_opp_pcts: dict[str, list[float]] = defaultdict(list)

    for row in clock_rows:
        game_id: int = row[0]
        time_control_bucket: str | None = row[1]
        base_time_seconds: int | None = row[2]
        termination: str | None = row[3]
        result: str = row[4]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]

        # Skip rows without a time control bucket
        if time_control_bucket is None:
            continue

        tc = time_control_bucket
        # Set-based dedup retained as a defensive guard; under the post-pv4 SQL
        # contract, game_ids are already unique (one row per game).
        tc_game_ids[tc].add(game_id)

        # Extract entry clocks using ply parity
        user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)

        # Only accumulate clock stats when BOTH clocks are available AND
        # base_time_seconds is valid. Without a base clock we can't compute pct
        # or apply the 2x clamp, so the reading is unreliable — drop the whole
        # game from every accumulator (seconds, diff, pct) to keep the row
        # internally consistent.
        if (
            user_clock is not None
            and opp_clock is not None
            and base_time_seconds is not None
            and base_time_seconds > 0
        ):
            # Clamp: exclude games where either clock exceeds 2x base time — bogus
            # readings (e.g. adjudicated/disconnected games). Banked increment can
            # push clocks over 100% legitimately (p99 ~109%), but >200% is noise.
            if (
                user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
                or opp_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
            ):
                pass  # Skip entire game — bogus clock reading
            else:
                tc_user_clocks[tc].append(user_clock)
                tc_opp_clocks[tc].append(opp_clock)
                tc_clock_diffs[tc].append(user_clock - opp_clock)
                tc_user_pcts[tc].append(user_clock / base_time_seconds * 100)
                tc_opp_pcts[tc].append(opp_clock / base_time_seconds * 100)

        # Track timeouts — deduplicated by game_id per bucket
        if termination == "timeout":
            outcome = derive_user_result(result, user_color)
            if outcome == "win":
                tc_timeout_win_ids[tc].add(game_id)
            elif outcome == "loss":
                tc_timeout_loss_ids[tc].add(game_id)

    # Build response rows in fixed order; collect pre-filter totals
    grand_endgame_game_ids: set[int] = set()
    grand_clock_game_count = 0
    for game_ids in tc_game_ids.values():
        grand_endgame_game_ids.update(game_ids)
    for user_clocks in tc_user_clocks.values():
        grand_clock_game_count += len(user_clocks)

    rows: list[ClockStatsRow] = []
    for tc in _TIME_CONTROL_ORDER:
        game_ids = tc_game_ids.get(tc, set())
        total_endgame_games = len(game_ids)

        user_clocks = tc_user_clocks.get(tc, [])
        opp_clocks = tc_opp_clocks.get(tc, [])
        clock_diffs = tc_clock_diffs.get(tc, [])
        user_pcts = tc_user_pcts.get(tc, [])
        opp_pcts = tc_opp_pcts.get(tc, [])

        clock_games = len(user_clocks)

        # Two gates:
        # 1. total_endgame_games floor — not enough endgame games overall to bother.
        # 2. clock_games > 0 — no usable clock data at all (e.g. bucket is entirely
        #    daily/correspondence games with no base_time_seconds). Without this
        #    the table would show a row full of "—" under "Time Pressure at
        #    Endgame Entry".
        if total_endgame_games < MIN_GAMES_FOR_CLOCK_STATS or clock_games == 0:
            continue
        user_avg_seconds = statistics.mean(user_clocks) if user_clocks else None
        opp_avg_seconds = statistics.mean(opp_clocks) if opp_clocks else None
        avg_clock_diff_seconds = statistics.mean(clock_diffs) if clock_diffs else None
        user_avg_pct = statistics.mean(user_pcts) if user_pcts else None
        opp_avg_pct = statistics.mean(opp_pcts) if opp_pcts else None

        timeout_wins = len(tc_timeout_win_ids.get(tc, set()))
        timeout_losses = len(tc_timeout_loss_ids.get(tc, set()))
        net_timeout_rate = (timeout_wins - timeout_losses) / total_endgame_games * 100

        label = _TIME_CONTROL_LABELS.get(tc, tc.capitalize())

        rows.append(
            ClockStatsRow(
                time_control=cast(Literal["bullet", "blitz", "rapid", "classical"], tc),
                label=label,
                total_endgame_games=total_endgame_games,
                clock_games=clock_games,
                user_avg_pct=user_avg_pct,
                user_avg_seconds=user_avg_seconds,
                opp_avg_pct=opp_avg_pct,
                opp_avg_seconds=opp_avg_seconds,
                avg_clock_diff_seconds=avg_clock_diff_seconds,
                net_timeout_rate=net_timeout_rate,
            )
        )

    # Caller (the orchestrator) passes a pre-computed timeline built from
    # rows unfiltered by recency, so the rolling window can pre-fill from
    # games before the cutoff. Fall back to computing from `clock_rows` for
    # standalone use (tests, ad-hoc calls).
    if timeline is None:
        timeline = _compute_clock_pressure_timeline(clock_rows, timeline_window)

    return ClockPressureResponse(
        rows=rows,
        total_clock_games=grand_clock_game_count,
        total_endgame_games=len(grand_endgame_game_ids),
        timeline=timeline,
        timeline_window=timeline_window,
    )


def _compute_clock_pressure_timeline(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int,
    cutoff_str: str | None = None,
) -> list[ClockPressureTimelinePoint]:
    """Weekly rolling-window series of average clock-diff % at endgame entry.

    Single series collapsed across all time controls — users filter TCs via the
    sidebar. Each emitted point sits on the Monday of an ISO week and reflects
    the mean of (user_clock - opp_clock) / base_time_seconds * 100 over the
    trailing `window` games, using the window state after that week's last game
    (mirrors `_compute_weekly_rolling_series`).

    Filters applied per game (mirrors `_compute_clock_pressure` inclusion rules):
    - time_control_bucket must be present
    - base_time_seconds must be > 0
    - both entry clocks must be available
    - neither clock may exceed MAX_CLOCK_PCT_OF_BASE * base_time_seconds
    - played_at must be non-null (needed for ISO-week bucketing)

    Points with fewer than MIN_GAMES_FOR_TIMELINE games in the window are dropped,
    matching the same cold-start handling used by the Win Rate by Endgame Type chart.

    `cutoff_str` (YYYY-MM-DD) drops emitted points dated before the cutoff but
    lets earlier games pre-fill the rolling window — mirrors
    `get_endgame_timeline` so the recency filter does not starve the window
    when the user picks a short window like "past 3 months".
    """
    game_data: list[tuple[Any, float]] = []
    for row in clock_rows:
        time_control_bucket: str | None = row[1]
        base_time_seconds: int | None = row[2]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]
        played_at: Any = row[8]

        if time_control_bucket is None:
            continue
        if base_time_seconds is None or base_time_seconds <= 0:
            continue
        if played_at is None:
            continue

        user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)
        if user_clock is None or opp_clock is None:
            continue
        if (
            user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
            or opp_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
        ):
            continue

        diff_pct = (user_clock - opp_clock) / base_time_seconds * 100
        game_data.append((played_at, diff_pct))

    game_data.sort(key=lambda x: x[0])

    diffs_so_far: list[float] = []
    # Per-ISO-week count of clock-eligible endgame games — drives the frontend
    # volume bars (mirrors `per_week_count` in `_compute_endgame_elo_weekly_series`).
    per_week_count: dict[tuple[int, int], int] = {}
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, diff_pct in game_data:
        diffs_so_far.append(diff_pct)
        window_slice = diffs_so_far[-window:]
        avg = statistics.mean(window_slice)

        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        per_week_count[(iso_year, iso_week)] = per_week_count.get((iso_year, iso_week), 0) + 1
        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        data_by_week[(iso_year, iso_week)] = {
            "date": monday.isoformat(),
            "avg_clock_diff_pct": round(avg, 4),
            "game_count": len(window_slice),
            "per_week_game_count": per_week_count[(iso_year, iso_week)],
        }

    return [
        ClockPressureTimelinePoint(**data_by_week[key])
        for key in sorted(data_by_week.keys())
        if data_by_week[key]["game_count"] >= MIN_GAMES_FOR_TIMELINE
        and (cutoff_str is None or data_by_week[key]["date"] >= cutoff_str)
    ]


def _build_bucket_series(
    buckets: list[list[float]],
) -> list[TimePressureBucketPoint]:
    """Build 10-point series from accumulated [score_sum, game_count] pairs.

    Each element of buckets is [score_sum, game_count] for one bucket index.
    Returns a list of TimePressureBucketPoint with score=None when game_count==0.
    """
    points: list[TimePressureBucketPoint] = []
    for i, bucket in enumerate(buckets):
        score_sum = bucket[0]
        count = bucket[1]
        lo = i * BUCKET_WIDTH_PCT
        hi = (i + 1) * BUCKET_WIDTH_PCT
        label = f"{lo}-{hi}%"
        score = (score_sum / count) if count > 0 else None
        points.append(
            TimePressureBucketPoint(
                bucket_index=i,
                bucket_label=label,
                score=score,
                game_count=int(count),
            )
        )
    return points


def _compute_time_pressure_chart(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> TimePressureChartResponse:
    """Compute time-pressure performance chart data from clock_rows.

    Reuses the same clock_rows already fetched by query_clock_stats_rows in
    get_endgame_overview -- no additional DB query needed.

    query_clock_stats_rows returns one row per qualifying game (whole-game 6-ply
    rule via _any_endgame_ply_subquery, per quick-260414-pv4), so iterating rows
    directly produces one data point per game with no risk of double-counting
    games that cycle through multiple endgame classes.

    For each game with both clocks and valid time_control_seconds:
    - Bucket user's time% -> accumulate user_score into user_series
    - Bucket opp's time% -> accumulate (1 - user_score) into opp_series

    quick-260416-pkx: rows are now pooled across all time controls that pass
    MIN_GAMES_FOR_CLOCK_STATS into a single user_series + opp_series (10 buckets
    each). Per-time-control rows were dropped — the frontend previously
    re-aggregated them into a single weighted-average series, so the math now
    lives here (closer to the data). The per-TC threshold still applies: games
    belonging to a time control with fewer than MIN_GAMES_FOR_CLOCK_STATS
    endgame games are excluded from the pool.
    """
    # Per-time-control accumulators: [score_sum, game_count] per bucket per time control.
    # Kept at per-TC granularity so the MIN_GAMES_FOR_CLOCK_STATS threshold can drop
    # entire TCs before pooling — same behaviour the frontend had when it filtered
    # the backend's per-TC rows before aggregating.
    tc_user_buckets: dict[str, list[list[float]]] = defaultdict(
        lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
    )
    tc_opp_buckets: dict[str, list[list[float]]] = defaultdict(
        lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
    )
    # Count games with valid time_control_bucket (regardless of clock data) — used
    # for the MIN_GAMES_FOR_CLOCK_STATS gate and for the pooled total_endgame_games.
    tc_game_count: dict[str, int] = defaultdict(int)

    for row in clock_rows:
        # game_id (row[0]) and termination (row[3]) are unused in this consumer —
        # _compute_clock_pressure handles the timeout accounting.
        time_control_bucket: str | None = row[1]
        base_time_seconds: int | None = row[2]
        result: str = row[4]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]

        # Skip rows without a time control bucket
        if time_control_bucket is None:
            continue

        tc = time_control_bucket
        # One row per game after quick-260414-pv4 rewrite of query_clock_stats_rows, so
        # this increment cannot double-count games with multiple endgame-class spans.
        tc_game_count[tc] += 1

        # Extract entry clocks via ply parity — same as _compute_clock_pressure
        user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)

        # Skip if either clock is missing — can't bucket without both
        if user_clock is None or opp_clock is None:
            continue

        # Skip if base_time_seconds is absent or zero — can't compute per-game percentage
        # (quick-260414-smt: switched from bucket-first-seen time_control_seconds to
        # per-game base_time_seconds for apples-to-apples % within each bucket)
        if base_time_seconds is None or base_time_seconds <= 0:
            continue

        # Clamp: skip games where either clock exceeds 2x base time — bogus readings
        if (
            user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
            or opp_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
        ):
            continue

        user_pct = user_clock / base_time_seconds * 100
        opp_pct = opp_clock / base_time_seconds * 100

        # Clamp to [0, NUM_BUCKETS-1] — 100% maps to bucket 9, not 10
        user_bucket = min(int(user_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)
        opp_bucket = min(int(opp_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)

        user_score = {"win": 1.0, "draw": 0.5, "loss": 0.0}[derive_user_result(result, user_color)]

        # Accumulate: initialise defaultdict entry if needed, then update
        tc_user_buckets[tc][user_bucket][0] += user_score
        tc_user_buckets[tc][user_bucket][1] += 1
        tc_opp_buckets[tc][opp_bucket][0] += 1.0 - user_score
        tc_opp_buckets[tc][opp_bucket][1] += 1

    # Pool per-TC accumulators into a single series pair. TCs below the threshold
    # are dropped entirely — same behaviour as the previous per-TC filter that the
    # frontend then re-aggregated.
    pooled_user_buckets: list[list[float]] = [[0.0, 0] for _ in range(NUM_BUCKETS)]
    pooled_opp_buckets: list[list[float]] = [[0.0, 0] for _ in range(NUM_BUCKETS)]
    total_endgame_games = 0
    for tc in _TIME_CONTROL_ORDER:
        if tc_game_count.get(tc, 0) < MIN_GAMES_FOR_CLOCK_STATS:
            continue
        total_endgame_games += tc_game_count[tc]
        tc_user = tc_user_buckets[tc]
        tc_opp = tc_opp_buckets[tc]
        for i in range(NUM_BUCKETS):
            pooled_user_buckets[i][0] += tc_user[i][0]
            pooled_user_buckets[i][1] += tc_user[i][1]
            pooled_opp_buckets[i][0] += tc_opp[i][0]
            pooled_opp_buckets[i][1] += tc_opp[i][1]

    return TimePressureChartResponse(
        user_series=_build_bucket_series(pooled_user_buckets),
        opp_series=_build_bucket_series(pooled_opp_buckets),
        total_endgame_games=total_endgame_games,
    )


def _compute_rolling_series(rows: list[Row[Any]], window: int) -> list[dict]:
    """Compute a rolling-window win-rate series from chronological game rows.

    Mirrors the pattern in openings_service.get_time_series.

    Args:
        rows: List of (played_at, result, user_color) tuples ordered by played_at ASC.
        window: Rolling window size. Partial windows (< window games) are included.

    Returns:
        List of dicts with keys: date, win_rate, game_count, window_size.
        One entry per date (last game of the day), not per game.
    """
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    data_by_date: dict[str, dict] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)

        # Rolling window: trailing `window` results
        window_slice = results_so_far[-window:]
        win_count = window_slice.count("win")
        window_total = len(window_slice)
        win_rate = win_count / window_total if window_total > 0 else 0.0

        date_key = played_at.strftime("%Y-%m-%d")
        data_by_date[date_key] = {
            "date": date_key,
            "win_rate": round(win_rate, 4),
            "game_count": window_total,
            "window_size": window,
        }

    # Drop early points with too few games in the rolling window
    return [pt for pt in data_by_date.values() if pt["game_count"] >= MIN_GAMES_FOR_TIMELINE]


def _compute_weekly_rolling_series(
    rows: list[Row[Any]],
    window: int,
) -> list[dict]:
    """Compute a rolling-window win-rate series sampled once per ISO week.

    Walks chronological game rows maintaining a trailing `window`-game window,
    and emits one point per ISO week using the window state after the final
    game of that week. This gives weekly cadence (far fewer points than the
    per-game series) while preserving rolling-window smoothing across weeks,
    so weeks with few games still show the last `window` games of history
    rather than bouncing on a fresh sample.

    Args:
        rows: list of (played_at, result, user_color), ordered by played_at ASC.
        window: rolling window size (typically 50). Partial early windows
            (< window games) are allowed but dropped below MIN_GAMES_FOR_TIMELINE.

    Returns:
        list of dicts with keys: date (Monday of the ISO week, YYYY-MM-DD),
        win_rate, game_count. Sorted chronologically by date.
    """
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    # Per-ISO-week count of games — drives the frontend volume bars on the
    # Win Rate by Endgame Type chart (mirrors `per_week_count` in
    # `_compute_endgame_elo_weekly_series`).
    per_week_count: dict[tuple[int, int], int] = {}
    # Keyed by (iso_year, iso_week) so each week keeps only its final state.
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)

        window_slice = results_so_far[-window:]
        window_total = len(window_slice)
        win_rate = window_slice.count("win") / window_total if window_total > 0 else 0.0

        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        per_week_count[(iso_year, iso_week)] = per_week_count.get((iso_year, iso_week), 0) + 1
        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        # Overwrite so each week keeps the window state after its last game.
        data_by_week[(iso_year, iso_week)] = {
            "date": monday.isoformat(),
            "win_rate": round(win_rate, 4),
            "game_count": window_total,
            "per_week_game_count": per_week_count[(iso_year, iso_week)],
        }

    return [
        data_by_week[key]
        for key in sorted(data_by_week.keys())
        if data_by_week[key]["game_count"] >= MIN_GAMES_FOR_TIMELINE
    ]


def _get_endgame_performance_from_rows(
    endgame_rows: list[Row[Any]],
    non_endgame_rows: list[Row[Any]],
    bucket_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> EndgamePerformanceResponse:
    """Compute EndgamePerformanceResponse from pre-fetched rows.

    Phase 81 UAT amendment: entry-eval aggregation now consumes `bucket_rows`
    (one row per endgame game, eval at the chronologically first endgame
    position) instead of the per-class `entry_rows`. The bucket query applies
    the same game-level ENDGAME_PLY_THRESHOLD HAVING that drives the WDL
    denominator, so

        entry_eval_n + mate_excluded + null_eval_excluded == endgame_wdl.total

    by construction. NULL evals (engine errors / not-yet-backfilled positions)
    are dropped from the entry-eval mean even though they count toward
    `endgame_wdl.total` — including them would bias the mean toward 0. For a
    freshly imported user with incomplete eval backfill, `entry_eval_n` will
    lag `endgame_wdl.total` until backfill catches up.

    The previous per-class pipeline also excluded ~5 games per typical user
    (multi-class transitions where no single span reached the 6-ply threshold).
    Mate exclusion follows D-07. The user-perspective sign flip is unchanged.
    The Wilson score test of `endgame_wdl` against 50% still runs here.
    """
    endgame_wdl = _build_wdl_summary(endgame_rows)
    non_endgame_wdl = _build_wdl_summary(non_endgame_rows)

    # bucket_rows: one row per endgame game, eval at the first chronological
    # endgame position. No per-game dedupe needed — the SQL already returns
    # one row per game (GROUP BY game_id).
    eval_sum = 0.0
    eval_sumsq = 0.0
    eval_n = 0
    for row in bucket_rows:
        # Pitfall 3: explicit None checks. Never use `or` for numeric defaulting
        # on Optional columns — Python's truthiness would silently turn None -> 0.
        if row.eval_mate is not None:  # ty: ignore[unresolved-attribute]
            continue  # mate-excluded per D-07
        if row.eval_cp is None:  # ty: ignore[unresolved-attribute]
            continue  # NULL eval excluded
        # Pitfall 2: sign-flip per user color so positive = user is ahead.
        # Raw eval_cp is white-perspective; mirrors _classify_endgame_bucket.
        sign = 1 if row.user_color == "white" else -1  # ty: ignore[unresolved-attribute]
        signed_cp = float(sign * row.eval_cp)  # ty: ignore[unresolved-attribute]
        eval_sum += signed_cp
        eval_sumsq += signed_cp * signed_cp
        eval_n += 1

    # Wald-z one-sample test of mean vs 0 cp. Helper handles n<10 / n=1 / SE=0.
    _conf_e, p_eval_raw, mean_cp, ci_half_cp = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, eval_n
    )
    # Pitfall 5: gate the wire-format p-value to None when below the reliability
    # threshold (D-11). The helper returns 1.0 in that branch; surfacing 1.0 to
    # the API would conflate "no data" with "definitely consistent with H0".
    entry_eval_p_value: float | None = p_eval_raw if eval_n >= PVALUE_RELIABILITY_MIN_N else None
    entry_eval_mean_pawns = mean_cp / 100.0 if eval_n > 0 else 0.0
    entry_eval_ci_low_pawns: float | None
    entry_eval_ci_high_pawns: float | None
    if eval_n >= 2:
        entry_eval_ci_low_pawns = (mean_cp - ci_half_cp) / 100.0
        entry_eval_ci_high_pawns = (mean_cp + ci_half_cp) / 100.0
    else:
        # Variance undefined for n < 2; CI bounds are not meaningful.
        entry_eval_ci_low_pawns = None
        entry_eval_ci_high_pawns = None

    # Wilson score test of endgame_wdl against 50% (D-08).
    _conf_s, p_score_raw, _se = compute_confidence_bucket(
        endgame_wdl.wins, endgame_wdl.draws, endgame_wdl.losses, endgame_wdl.total
    )
    endgame_score_p_value: float | None = (
        p_score_raw if endgame_wdl.total >= PVALUE_RELIABILITY_MIN_N else None
    )

    # Mirror of endgame_score_p_value for the Section 1 "Games without Endgame" card (Phase 85 D-01).
    _conf_ns, p_non_score_raw, _se_ns = compute_confidence_bucket(
        non_endgame_wdl.wins,
        non_endgame_wdl.draws,
        non_endgame_wdl.losses,
        non_endgame_wdl.total,
    )
    non_endgame_score_p_value: float | None = (
        p_non_score_raw if non_endgame_wdl.total >= PVALUE_RELIABILITY_MIN_N else None
    )

    # Phase 83 Plan 2 (D-04..D-07, D-21): Stockfish-baseline expected score
    # sibling aggregator over the same bucket_rows cursor. Per-game expected
    # score via Lichess sigmoid for eval_cp / 0-or-1 for eval_mate. Mate is
    # INCLUDED here (D-06 — inverts the entry_eval cohort, which drops mate);
    # |eval_cp| >= EVAL_CLIP_MAX_CP rows are dropped (D-07).
    #
    # Phase 85.1 Plan 02 (SEC1-10): merge a paired-difference accumulator into
    # the SAME loop so the filter logic is shared by construction (mate INCLUDED,
    # |eval_cp| >= EVAL_CLIP_MAX_CP clipped, both-NULL skipped). For each surviving
    # row we capture the per-game expected score (avoiding a second sigmoid eval),
    # compute actual_score_i from derive_user_result, and append
    # d_i = actual_score_i - expected_score_i. d_n == ex_n by construction.
    # _ACTUAL_SCORE_BY_OUTCOME defined at module scope (WR-03).
    ex_sum = 0.0
    ex_n = 0
    diffs: list[float] = []
    for row in bucket_rows:
        if row.eval_mate is not None:  # ty: ignore[unresolved-attribute]
            # D-06: mate INCLUDED. Routed through the 0/1 helper, not the sigmoid.
            expected_score_i = eval_mate_to_expected_score(
                row.eval_mate,  # ty: ignore[unresolved-attribute]
                row.user_color,  # ty: ignore[unresolved-attribute]
            )
        elif row.eval_cp is not None:  # ty: ignore[unresolved-attribute]
            if abs(row.eval_cp) >= EVAL_CLIP_MAX_CP:  # ty: ignore[unresolved-attribute]
                continue  # D-07 clip — sigmoid saturates anyway
            expected_score_i = eval_cp_to_expected_score(
                row.eval_cp,  # ty: ignore[unresolved-attribute]
                row.user_color,  # ty: ignore[unresolved-attribute]
            )
        else:
            continue  # both NULL — skip per D-06 cohort filter
        ex_sum += expected_score_i
        ex_n += 1
        # Phase 85.1 paired-diff accumulator (SEC1-10).
        outcome = derive_user_result(
            row.result,  # ty: ignore[unresolved-attribute]
            row.user_color,  # ty: ignore[unresolved-attribute]
        )
        actual_score_i = _ACTUAL_SCORE_BY_OUTCOME[outcome]
        diffs.append(actual_score_i - expected_score_i)

    entry_expected_score = ex_sum / ex_n if ex_n > 0 else 0.0

    # Phase 85.1 (SEC1-10): paired one-sample z-test on per-game
    # (actual - expected) diffs. Helper gates p_value at n >=
    # PVALUE_RELIABILITY_MIN_N=10 and CI bounds at n >= 2; SE=0 trap resolves
    # the all-identical-diffs case to {0.0, 1.0}.
    # d_n == ex_n by construction (same filter applied to both accumulators).
    achievable_score_gap, achievable_p, achievable_ci_low, achievable_ci_high = (
        compute_paired_difference_test(diffs)
    )
    # Wilson sig test vs 50% via the (score, n) sibling helper. Single Wilson
    # code path with compute_confidence_bucket (memory feedback_wilson_chess_score.md).
    _conf_x, p_ex_raw, _se_ex = compute_score_confidence_from_mean(entry_expected_score, ex_n)
    # Same wire-format gate as entry_eval_p_value / endgame_score_p_value
    # (PVALUE_RELIABILITY_MIN_N, currently 10 — REVIEW IN-01 carry-forward).
    entry_expected_score_p_value: float | None = (
        p_ex_raw if ex_n >= PVALUE_RELIABILITY_MIN_N else None
    )
    entry_expected_score_ci_low: float | None
    entry_expected_score_ci_high: float | None
    if ex_n >= 2:
        ci_low, ci_high = wilson_bounds(entry_expected_score, ex_n)
        entry_expected_score_ci_low = ci_low
        entry_expected_score_ci_high = ci_high
    else:
        # n < 2 -> Wilson bounds defensive guard returns (0, 1) which is not
        # narratable. Gate to None to match the entry_eval CI convention.
        entry_expected_score_ci_low = None
        entry_expected_score_ci_high = None

    return EndgamePerformanceResponse(
        endgame_wdl=endgame_wdl,
        non_endgame_wdl=non_endgame_wdl,
        endgame_win_rate=endgame_wdl.win_pct,
        entry_eval_mean_pawns=entry_eval_mean_pawns,
        entry_eval_n=eval_n,
        entry_eval_p_value=entry_eval_p_value,
        endgame_score_p_value=endgame_score_p_value,
        non_endgame_score_p_value=non_endgame_score_p_value,
        entry_eval_ci_low_pawns=entry_eval_ci_low_pawns,
        entry_eval_ci_high_pawns=entry_eval_ci_high_pawns,
        entry_expected_score=entry_expected_score,
        entry_expected_score_n=ex_n,
        entry_expected_score_p_value=entry_expected_score_p_value,
        entry_expected_score_ci_low=entry_expected_score_ci_low,
        entry_expected_score_ci_high=entry_expected_score_ci_high,
        achievable_score_gap=achievable_score_gap,
        achievable_score_gap_p_value=achievable_p,
        achievable_score_gap_ci_low=achievable_ci_low,
        achievable_score_gap_ci_high=achievable_ci_high,
    )


async def get_endgame_performance(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgamePerformanceResponse:
    """Orchestrate endgame performance query and return EndgamePerformanceResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch WDL comparison rows and entry rows sequentially.
    3. Delegate aggregation to _get_endgame_performance_from_rows.
    4. Return EndgamePerformanceResponse.
    """
    cutoff = recency_cutoff(recency)

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and shares a single DB connection anyway.
    endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    bucket_rows = await query_endgame_bucket_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    return _get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, bucket_rows)


async def get_endgame_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
    window: int = 50,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameTimelineResponse:
    """Orchestrate endgame timeline query and return EndgameTimelineResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch ALL rows (no recency filter) so the rolling window is pre-filled
       with games before the cutoff — avoids cold-start when filtering recent games.
    3. Compute rolling-window series over full history.
    4. Filter output to only emit points on or after the recency cutoff.
    5. Merge overall series by date, build per-type series.
    6. Return EndgameTimelineResponse.
    """
    cutoff = recency_cutoff(recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    # Fetch all games (no recency filter) so rolling windows are pre-filled.
    # Other filters (time_control, platform, etc.) still applied.
    endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Compute rolling series over full history, then filter to recency window
    endgame_series = _compute_rolling_series(endgame_rows, window)
    non_endgame_series = _compute_rolling_series(non_endgame_rows, window)
    if cutoff_str:
        endgame_series = [pt for pt in endgame_series if pt["date"] >= cutoff_str]
        non_endgame_series = [pt for pt in non_endgame_series if pt["date"] >= cutoff_str]

    # Merge overall series by date. For each date that appears in either series,
    # find the latest point from each series up to that date.
    # We build cumulative dicts (date -> latest point) and collect all unique dates.
    endgame_by_date: dict[str, dict] = {}
    for pt in endgame_series:
        endgame_by_date[pt["date"]] = pt

    non_endgame_by_date: dict[str, dict] = {}
    for pt in non_endgame_series:
        non_endgame_by_date[pt["date"]] = pt

    all_dates = sorted(set(endgame_by_date.keys()) | set(non_endgame_by_date.keys()))

    # For each date, take the most recent known point from each series up to that date
    last_endgame_pt: dict | None = None
    last_non_endgame_pt: dict | None = None
    overall: list[EndgameOverallPoint] = []

    for date in all_dates:
        if date in endgame_by_date:
            last_endgame_pt = endgame_by_date[date]
        if date in non_endgame_by_date:
            last_non_endgame_pt = non_endgame_by_date[date]

        overall.append(
            EndgameOverallPoint(
                date=date,
                endgame_win_rate=last_endgame_pt["win_rate"] if last_endgame_pt else None,
                non_endgame_win_rate=last_non_endgame_pt["win_rate"]
                if last_non_endgame_pt
                else None,
                endgame_game_count=last_endgame_pt["game_count"] if last_endgame_pt else 0,
                non_endgame_game_count=last_non_endgame_pt["game_count"]
                if last_non_endgame_pt
                else 0,
                window_size=window,
            )
        )

    # Compute per-type rolling series sampled once per ISO week.
    # Weekly cadence keeps the point count low; sampling a trailing window of
    # `window` games (shared across weeks) prevents single-sparse-week noise.
    per_type: dict[str, list[EndgameTimelinePoint]] = {}
    for class_int, rows in per_type_rows.items():
        # Safe bracket access: class_int keys come from per_type_rows, which is
        # seeded from _ENDGAME_CLASS_INTS (the authoritative 1..6 set) in the
        # repository layer. No defensive .get() needed here.
        class_name = _INT_TO_CLASS[class_int]
        series = _compute_weekly_rolling_series(rows, window)
        per_type[class_name] = [
            EndgameTimelinePoint(
                date=pt["date"],
                win_rate=pt["win_rate"],
                game_count=pt["game_count"],
                per_week_game_count=pt["per_week_game_count"],
            )
            for pt in series
            if not cutoff_str or pt["date"] >= cutoff_str
        ]

    return EndgameTimelineResponse(overall=overall, per_type=per_type, window=window)


async def get_endgame_elo_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameEloTimelineResponse:
    """Orchestrate the Endgame ELO timeline query (Phase 57 ELO-05).

    Fetches rows WITHOUT the recency cutoff so the 100-game rolling windows
    pre-fill from games before the cutoff (Pitfall 2). Partitions both row
    streams in Python by (platform, time_control_bucket), invokes the weekly
    helper per combo, drops combos with zero qualifying points (D-10 tier 2),
    and returns combos ordered per _ENDGAME_ELO_COMBO_ORDER.
    """
    cutoff = recency_cutoff(recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    bucket_rows_all, all_rows_all = await query_endgame_elo_timeline_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,  # pre-fill windows; filter output via cutoff_str
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Partition by (platform, time_control_bucket).
    # Row positions: played_at=0, platform=1, time_control_bucket=2
    bucket_by_combo: dict[tuple[str, str], list[tuple[Any, ...]]] = {}
    for row in bucket_rows_all:
        key = (row[1], row[2])
        bucket_by_combo.setdefault(key, []).append(tuple(row))

    all_by_combo: dict[tuple[str, str], list[tuple[Any, ...]]] = {}
    for row in all_rows_all:
        key = (row[1], row[2])
        all_by_combo.setdefault(key, []).append(tuple(row))

    # Pre-compute per-combo (dates, ratings) parallel arrays for the asof-join
    # (Phase 57.1 D-01/D-02). Each combo's all_rows is already sorted by
    # played_at ASC by the repo query (ORDER BY played_at ASC); derive the
    # user_rating from white/black + user_color and skip NULL-rating rows.
    asof_by_combo: dict[tuple[str, str], tuple[list[Any], list[int]]] = {}
    for asof_key, rows in all_by_combo.items():
        dates: list[Any] = []
        ratings: list[int] = []
        for row in rows:
            played_at_val = row[0]
            user_color = row[3]
            white_rating = row[4]
            black_rating = row[5]
            if played_at_val is None or white_rating is None or black_rating is None:
                continue
            dates.append(played_at_val)
            ratings.append(white_rating if user_color == "white" else black_rating)
        asof_by_combo[asof_key] = (dates, ratings)

    combos: list[EndgameEloTimelineCombo] = []
    for platform_name, tc in _ENDGAME_ELO_COMBO_ORDER:
        key = (platform_name, tc)
        asof_dates, asof_ratings = asof_by_combo.get(key, ([], []))
        points = _compute_endgame_elo_weekly_series(
            bucket_by_combo.get(key, []),
            all_by_combo.get(key, []),
            ENDGAME_ELO_TIMELINE_WINDOW,
            asof_dates,
            asof_ratings,
            cutoff_str=cutoff_str,
        )
        if not points:
            # D-10 tier 2: drop combo entirely when no qualifying points.
            continue
        combo_key = f"{platform_name.replace('.', '_')}_{tc}"
        # Narrow platform/tc to the Literal types the schema expects. Both come
        # from Game.platform / Game.time_control_bucket which are constrained
        # upstream; a mismatch here would indicate a data anomaly.
        combos.append(
            EndgameEloTimelineCombo(
                combo_key=combo_key,
                platform=cast(Literal["chess.com", "lichess"], platform_name),
                time_control=cast(Literal["bullet", "blitz", "rapid", "classical"], tc),
                points=points,
            )
        )

    return EndgameEloTimelineResponse(
        combos=combos,
        timeline_window=ENDGAME_ELO_TIMELINE_WINDOW,
    )


async def get_endgame_overview(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    window: int = 50,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameOverviewResponse:
    """Compose all five endgame dashboard payloads into a single response.

    Fetches entry_rows and performance rows once, then threads them to both
    the stats/performance builders and _compute_score_gap_material — eliminating
    redundant DB queries that the previous implementation issued separately in
    get_endgame_stats and get_endgame_performance (Phase 53).

    All queries run sequentially on one AsyncSession — no asyncio.gather.
    See endgame_repository.py for AsyncSession concurrency notes.
    """
    cutoff = recency_cutoff(recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    # Fetch entry_rows once — shared by stats, performance, and score_gap_material.
    # Previously fetched redundantly by both get_endgame_stats and get_endgame_performance.
    entry_rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Stats: aggregate per-category W/D/L + conversion/recovery from entry_rows.
    # Phase 87.2: also produces gaps_by_bucket (per-span ΔES per eval bucket),
    # threaded to _compute_score_gap_material below for the Section 2 bullets.
    categories, gaps_by_bucket = _aggregate_endgame_stats(entry_rows)
    total_games = await count_filtered_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # Count games that reached an endgame phase per the uniform ENDGAME_PLY_THRESHOLD rule
    # (quick-260414-ae4): a game qualifies if its total endgame plies meet the threshold.
    endgame_games = await count_endgame_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    stats = EndgameStatsResponse(
        categories=categories,
        total_games=total_games,
        endgame_games=endgame_games,
    )

    # Performance: fetch WDL comparison rows WITHOUT recency cutoff so the
    # score-diff timeline rolling window can pre-fill from games before the
    # cutoff. Filter in Python for the table-side WDL math (cheap — these
    # rows are just (played_at, result, user_color)). Mirrors the pattern in
    # `get_endgame_timeline`.
    endgame_rows_all, non_endgame_rows_all = await query_endgame_performance_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    if cutoff is not None:
        endgame_rows = [r for r in endgame_rows_all if r[0] is not None and r[0] >= cutoff]
        non_endgame_rows = [r for r in non_endgame_rows_all if r[0] is not None and r[0] >= cutoff]
    else:
        endgame_rows = list(endgame_rows_all)
        non_endgame_rows = list(non_endgame_rows_all)

    # Score gap & material breakdown + Phase 81 entry-eval aggregation both need
    # game-level bucket_rows (one row per endgame game). Post quick-260414-ae4 the
    # bucket query applies the same ENDGAME_PLY_THRESHOLD HAVING as `_any_endgame_ply_subquery`,
    # so sum(material_rows.games) == endgame_wdl.total. Entry-eval n satisfies
    # `entry_eval_n + mate_excluded + null_eval_excluded == endgame_wdl.total`;
    # see _get_endgame_performance_from_rows for why NULL evals are dropped.
    bucket_rows = await query_endgame_bucket_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    performance = _get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, bucket_rows)
    # Build score-gap timeline from unfiltered rows so the rolling 100-game
    # window per side is pre-filled with games before the cutoff; then drop
    # output points dated before the cutoff via cutoff_str.
    score_gap_timeline = _compute_score_gap_timeline(
        endgame_rows_all,
        non_endgame_rows_all,
        SCORE_GAP_TIMELINE_WINDOW,
        cutoff_str=cutoff_str,
    )
    score_gap_material = _compute_score_gap_material(
        performance.endgame_wdl,
        performance.non_endgame_wdl,
        bucket_rows,
        gaps_by_bucket=gaps_by_bucket,
        timeline=score_gap_timeline,
        timeline_window=SCORE_GAP_TIMELINE_WINDOW,
    )

    timeline = await get_endgame_timeline(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        recency=recency,
        rated=rated,
        opponent_type=opponent_type,
        window=window,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # Clock pressure: fetch per-span arrays WITHOUT recency cutoff so the
    # clock-diff timeline can pre-fill from games before the cutoff. Filter in
    # Python (by played_at at row index 8) for the table + time-pressure chart
    # consumers, which only want games inside the recency window.
    clock_rows_all = await query_clock_stats_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    if cutoff is not None:
        clock_rows = [r for r in clock_rows_all if r[8] is not None and r[8] >= cutoff]
    else:
        clock_rows = list(clock_rows_all)
    clock_diff_timeline = _compute_clock_pressure_timeline(
        clock_rows_all,
        CLOCK_PRESSURE_TIMELINE_WINDOW,
        cutoff_str=cutoff_str,
    )
    clock_pressure = _compute_clock_pressure(
        clock_rows,
        timeline=clock_diff_timeline,
        timeline_window=CLOCK_PRESSURE_TIMELINE_WINDOW,
    )
    time_pressure_chart = _compute_time_pressure_chart(clock_rows)

    # Phase 57 ELO-05: paired Endgame ELO + Actual ELO timeline per (platform, TC) combo.
    # Uses its own repo query (query_endgame_elo_timeline_rows) because the row shape
    # differs from existing queries (adds white_rating/black_rating for Elo math and
    # requires the all-games stream for the Actual ELO line per D-04). The orchestrator
    # runs this sequentially — no asyncio.gather on AsyncSession per CLAUDE.md.
    endgame_elo_timeline = await get_endgame_elo_timeline(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    return EndgameOverviewResponse(
        stats=stats,
        performance=performance,
        timeline=timeline,
        score_gap_material=score_gap_material,
        clock_pressure=clock_pressure,
        time_pressure_chart=time_pressure_chart,
        endgame_elo_timeline=endgame_elo_timeline,
    )
