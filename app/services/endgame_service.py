"""Endgame service: classification, aggregation, and orchestration for endgame analytics.

Exposes:
- classify_endgame_class: pure function mapping material_signature to category name
- EndgameClassInt: IntEnum encoding for endgame_class SmallInteger column
- _INT_TO_CLASS / _CLASS_TO_INT: bidirectional mappings for integer <-> string conversion
- _aggregate_endgame_stats: aggregates raw per-game rows into EndgameCategoryStats list
- get_endgame_stats: orchestrator for GET /api/endgames/stats
- get_endgame_games: orchestrator for GET /api/endgames/games
- build_endgame_elo_combos: per-combo weekly Endgame ELO + Actual ELO rolling series
- shared metric helpers (score-gap / clock-diff timelines, quintile bullets, span gaps,
  entry-clock extraction) consumed by endgame_ranked_service
"""

import bisect
import math
import statistics
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from datetime import date as _date
from enum import IntEnum
from typing import Any, Literal, NamedTuple, TypedDict, cast

import sentry_sdk
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    count_endgame_games,
    count_filtered_games,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
)
from app.schemas.openings import GameRecord
from app.schemas.endgames import (
    ClockDiffTimelinePoint,
    ClockDiffTimelineResponse,
    ConversionRecoveryStats,
    EndgameClass,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameGamesResponse,
    EndgameLabel,
    EndgameStatsResponse,
    EndgameWDLSummary,
    PressureQuintileBullet,
    ScoreGapTimelinePoint,
)
from app.services.endgame_zones import (
    # MIN_GAMES_* lifted to endgame_zones.py for codegen sharing.
    MIN_GAMES_PER_PRESSURE_BIN,
)
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.opening_insights_constants import EVAL_BASELINE_PAWNS_WHITE
from app.services.openings_service import (
    MIN_GAMES_FOR_TIMELINE,
    _build_wdl_stats,
    derive_user_result,
)
from app.repositories.stats_repository import EVAL_OUTLIER_TRIM_CP
from app.services.score_confidence import (
    VERDICT_CI_Z_99,
    ci_excludes,
    compute_paired_difference_test,
    compute_score_difference_test,
)


class EndgameClassInt(IntEnum):
    """Integer encoding for endgame_class column (SmallInteger, 2 bytes per row).
    Maps 1:1 to EndgameClass Literal strings."""

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

# Endgame classes excluded from the collapsible per-(class × TC) type
# cards. Mixed is the least-actionable catch-all (dropped) and pawnless is
# hidden in the UI; excluding them from aggregate_endgame_stats_by_tc keeps the
# per-TC card header count equal to the sum of the four rendered tiles. This does
# NOT affect the pooled `categories` (LLM path), which still includes Mixed.
_TYPE_CARD_EXCLUDED_CLASSES: frozenset[EndgameClass] = frozenset({"mixed", "pawnless"})


# Display labels for each endgame category.
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

    Categories:
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
# 4-ply persistence proxy. 100 cp == 1.0 pawn — surfaced to the user
# as "+1.0" / "-1.0" in tooltips and bucket labels.
EVAL_ADVANTAGE_THRESHOLD = 100

# Drop |eval_cp| >= 2000 from the entry_expected_score cohort.
# The Lichess winning-chances sigmoid saturates around +/-800 cp anyway (f(+800) ~
# 0.95, f(+1500) ~ 0.997), so very large evals add almost-1.0 contributions that
# overwhelm the mean. Matches the "analyzable endgame entry" cohort
# definition for consistency with the entry_eval bullet.
EVAL_CLIP_MAX_CP = 2000

# n-gate threshold below which any p-value is too unstable to surface to the
# wire (score-difference and paired-difference test gates).
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
        # White-perspective mate: eval_mate > 0 means White mates. Use a large
        # magnitude to guarantee threshold crossing.
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


# Minimum opponent sample size required to display the opponent
# baseline in the Conversion/Even/Recovery bullet chart. Matches the WDL-bar
# mute threshold used elsewhere (e.g. Opening Explorer moves list).
_MIN_OPPONENT_SAMPLE = 10


# Map game result + user_color to a chess score for
# terminal-span exit_score. Named constant per CLAUDE.md "no magic numbers";
# keyed on the outcome returned by derive_user_result (Literal["win","draw","loss"])
# so the dict is exhaustive against the type system.
_GAME_RESULT_TO_SCORE: dict[Literal["win", "draw", "loss"], float] = {
    "win": 1.0,
    "draw": 0.5,
    "loss": 0.0,
}


def _compute_span_scores(
    entry_eval_cp: int | None,
    entry_eval_mate: int | None,
    next_entry_eval_cp: int | None,
    next_entry_eval_mate: int | None,
    result: str,
    user_color: str,
) -> tuple[float, float] | None:
    """Return (es_entry, exit_score) for a span, or None if entry eval unavailable.

    Pure helper that exposes both components so callers can
    accumulate starts and ends separately (single source of truth for entry/exit
    logic). compute_span_gap delegates here and returns exit_score - es_entry.

    NULL-eval gate: returns None when both
    entry_eval_cp and entry_eval_mate are NULL — the span is excluded from the
    per-class cohort.

    Returns:
        (es_entry, exit_score) where:
          - es_entry  = lichess sigmoid over (eval_cp, eval_mate, user_color).
          - exit_score:
            * Transitory span (next_entry_eval_cp OR next_entry_eval_mate
              non-NULL): ES_sigmoid(next_entry_eval, user_color).
            * Terminal span (both next_entry_eval_* NULL): game-result score
              via _GAME_RESULT_TO_SCORE[derive_user_result(result, user_color)].
    """
    # Skip spans where the entry eval is unknown.
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

    return es_entry, exit_score


def compute_span_gap(
    entry_eval_cp: int | None,
    entry_eval_mate: int | None,
    next_entry_eval_cp: int | None,
    next_entry_eval_mate: int | None,
    result: str,
    user_color: str,
) -> float | None:
    """Return per-span gap `exit_score - ES_entry`, or None if entry eval unavailable.

    Delegates to _compute_span_scores (single
    source of truth for entry/exit/mate-precedence/terminal-vs-transitory logic).
    Sign convention: positive = user outperformed the Stockfish baseline
    (recovered eval, decisive conversions); negative = user gave back expected
    score. Matches the page-level Achievable Score Gap direction
    (`higher_is_better`) so the per-type ScoreGapRow reads identically to the
    page-level row on the same visual axis.

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
        gap_span = exit_score - ES_entry, or None when entry eval is unavailable.
    """
    scores = _compute_span_scores(
        entry_eval_cp, entry_eval_mate, next_entry_eval_cp, next_entry_eval_mate, result, user_color
    )
    if scores is None:
        return None
    return scores[1] - scores[0]


# Rolling window size for the score-difference timeline chart.
# Mirrors the 100-game window used by the clock-diff timeline.
SCORE_GAP_TIMELINE_WINDOW = 100


class _EndgameRow(NamedTuple):
    """Fields the `_aggregate_endgame_stats` per-row loop consumes, post row-shape dispatch.

    Produced by `_normalize_endgame_row` from a raw per-(game, endgame_class) span row
    (SA `Row` or 6/8/9-element tuple test fixture — see that function's docstring for the
    exact shapes). `game_id` is read by the dispatch but never consumed downstream in the
    per-row loop or the per-class builder, so it is intentionally omitted here.
    """

    endgame_class_int: int
    result: str
    user_color: str
    eval_cp: int | None
    eval_mate: int | None
    next_entry_eval_cp: int | None
    next_entry_eval_mate: int | None
    played_at: datetime | None


def _normalize_endgame_row(row: Row[Any] | tuple[Any, ...]) -> _EndgameRow:
    """Collapse the 6/8/9-tuple-vs-SA-`Row` shape dispatch into one typed row.

    Field ordering inside each branch matters: a reordered field here
    produces plausible-looking but wrong aggregates that no type checker catches.
    """
    row_played_at: datetime | None = None
    if isinstance(row, tuple):
        if len(row) == 6:
            _game_id, endgame_class_int, result, user_color, eval_cp, eval_mate = row
            next_entry_eval_cp: int | None = None
            next_entry_eval_mate: int | None = None
        elif len(row) == 8:
            # 8-tuple: full row shape (no played_at).
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
            # 9-tuple: full new row shape with played_at.
            (
                _game_id,
                endgame_class_int,
                result,
                user_color,
                eval_cp,
                eval_mate,
                next_entry_eval_cp,
                next_entry_eval_mate,
                row_played_at,
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
        row_played_at = getattr(row, "played_at", None)
    return _EndgameRow(
        endgame_class_int=endgame_class_int,
        result=result,
        user_color=user_color,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        next_entry_eval_cp=next_entry_eval_cp,
        next_entry_eval_mate=next_entry_eval_mate,
        played_at=row_played_at,
    )


class _EndgameAccumulators(TypedDict):
    """Per-endgame-class accumulator bundle built by one row-scan pass.

    Matches the `FilterParams` TypedDict convention in `app/services/stats_service.py`
    (TypedDicts for internal data structures). All 11 fields are outputs of the
    same row-scan pass in `_accumulate_endgame_rows`; `_build_category_stats` reads them
    to build one `EndgameCategoryStats` per class key.
    """

    wdl: dict[EndgameClass, dict[str, int]]
    conv: dict[EndgameClass, dict[str, int]]
    recov: dict[EndgameClass, dict[str, int]]
    gaps_by_class: dict[EndgameClass, list[float]]
    starts_by_class: dict[EndgameClass, list[float]]
    ends_by_class: dict[EndgameClass, list[float]]
    gaps_by_bucket: dict[str, list[float]]
    eval_sum_by_class: dict[EndgameClass, float]
    eval_sumsq_by_class: dict[EndgameClass, float]
    eval_n_by_class: dict[EndgameClass, int]
    last_played_at_by_class: dict[EndgameClass, datetime | None]


def _new_endgame_accumulators() -> _EndgameAccumulators:
    """Build the 11 empty per-class accumulator dicts `_accumulate_endgame_rows` fills."""
    return _EndgameAccumulators(
        # Conversion: games where user entered with eval advantage.
        # Recovery: games where user entered with eval deficit.
        wdl=defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0}),
        conv=defaultdict(lambda: {"games": 0, "wins": 0, "draws": 0}),
        recov=defaultdict(lambda: {"games": 0, "wins": 0, "draws": 0}),
        # Per-class per-span gap accumulator.
        # gap_span = exit_score - ES_entry; positive = outperformed Stockfish baseline.
        gaps_by_class=defaultdict(list),
        # Per-class start (es_entry) and end (exit_score) accumulators.
        # Appended under the exact same is-not-None gate as gaps_by_class, so the three
        # lists always have identical length (reconciliation invariant by construction).
        starts_by_class=defaultdict(list),
        ends_by_class=defaultdict(list),
        # Per-bucket ΔES accumulator. Per-span grain (not per-game):
        # a game spanning two bucket classes contributes a span-gap to each bucket.
        gaps_by_bucket=defaultdict(list),
        # Per-class eval cohort (user-perspective cp) for
        # MG-entry eval aggregation via compute_eval_confidence_bucket (same helper
        # as openings stats path). mate-excluded, NULL-excluded, |cp|>=2000 trimmed.
        eval_sum_by_class=defaultdict(float),
        eval_sumsq_by_class=defaultdict(float),
        eval_n_by_class=defaultdict(int),
        # MAX(played_at) per class for last_played_at.
        last_played_at_by_class=defaultdict(lambda: None),
    )


def _capture_invalid_endgame_class(class_int: int) -> None:
    """Surface an unexpected endgame_class integer from the DB to Sentry, then skip the row
    rather than 500 the endpoint.

    Per CLAUDE.md Sentry rules, variables go through set_context; the exception message is
    static so Sentry groups these together instead of per-class_int.
    """
    sentry_sdk.set_context("invalid_endgame_class", {"class_int": class_int})
    sentry_sdk.set_tag("source", "endgame_aggregate")
    sentry_sdk.capture_exception(ValueError("Unknown endgame_class integer from DB"))


def _accumulate_wdl_conv_recov(
    accumulators: _EndgameAccumulators,
    endgame_class: EndgameClass,
    outcome: Literal["win", "draw", "loss"],
    bucket: Literal["conversion", "parity", "recovery"],
) -> None:
    """Fold one row's W/D/L outcome into the pooled WDL and conversion/recovery accumulators."""
    wdl_key = "wins" if outcome == "win" else "draws" if outcome == "draw" else "losses"
    accumulators["wdl"][endgame_class][wdl_key] += 1

    # Conversion: user entered with significant eval advantage
    if bucket == "conversion":
        accumulators["conv"][endgame_class]["games"] += 1
        if outcome == "win":
            accumulators["conv"][endgame_class]["wins"] += 1
        elif outcome == "draw":
            accumulators["conv"][endgame_class]["draws"] += 1

    # Recovery: user entered with significant eval deficit
    if bucket == "recovery":
        accumulators["recov"][endgame_class]["games"] += 1
        if outcome == "win":
            accumulators["recov"][endgame_class]["wins"] += 1
        elif outcome == "draw":
            accumulators["recov"][endgame_class]["draws"] += 1


def _accumulate_score_gap(
    accumulators: _EndgameAccumulators,
    endgame_class: EndgameClass,
    bucket: Literal["conversion", "parity", "recovery"],
    endgame_row: _EndgameRow,
) -> None:
    """Fold one row's per-span Score Gap into the per-class and per-bucket accumulators.

    Accumulates the per-span gap for the paired
    one-sample z-test against H0: mean = 0 (compute_paired_difference_test, same helper
    the page-level Achievable Score Gap uses). Sign convention:
    gap = exit_score - ES_entry, positive = user outperformed Stockfish. NULL-eval spans
    return None from _compute_span_scores and are excluded from the cohort.
    """
    span_scores = _compute_span_scores(
        entry_eval_cp=endgame_row.eval_cp,
        entry_eval_mate=endgame_row.eval_mate,
        next_entry_eval_cp=endgame_row.next_entry_eval_cp,
        next_entry_eval_mate=endgame_row.next_entry_eval_mate,
        result=endgame_row.result,
        user_color=endgame_row.user_color,
    )
    if span_scores is None:
        return
    es_entry, exit_score = span_scores
    gap = exit_score - es_entry
    accumulators["gaps_by_class"][endgame_class].append(gap)
    accumulators["starts_by_class"][endgame_class].append(es_entry)
    accumulators["ends_by_class"][endgame_class].append(exit_score)
    # Bucket is already computed above; append the same gap into the
    # bucket cohort for the per-bucket paired-z test. Per-bucket path appends gap ONLY
    # (not start/end).
    accumulators["gaps_by_bucket"][bucket].append(gap)


def _accumulate_eval_and_played_at(
    accumulators: _EndgameAccumulators,
    endgame_class: EndgameClass,
    endgame_row: _EndgameRow,
) -> None:
    """Fold one row's eval-mean cohort and MAX(played_at) into the per-class accumulators.

    Accumulates user-perspective eval cp for the per-category eval
    mean / CI / confidence via compute_eval_confidence_bucket. Sign convention: user_cp =
    +eval_cp for white, -eval_cp for black (mirrors _classify_endgame_bucket). Excludes
    mate rows, NULL evals, and |cp| >= EVAL_OUTLIER_TRIM_CP (outlier trim, same as
    openings). Only called when the caller tracks eval/played_at (see
    `_accumulate_endgame_rows`'s `track_eval_and_played_at`).
    """
    if (
        endgame_row.eval_mate is None
        and endgame_row.eval_cp is not None
        and abs(endgame_row.eval_cp) < EVAL_OUTLIER_TRIM_CP
    ):
        sign = 1 if endgame_row.user_color == "white" else -1
        user_cp = sign * endgame_row.eval_cp
        accumulators["eval_sum_by_class"][endgame_class] += user_cp
        accumulators["eval_sumsq_by_class"][endgame_class] += user_cp * user_cp
        accumulators["eval_n_by_class"][endgame_class] += 1

    if endgame_row.played_at is not None:
        last_played_at_by_class = accumulators["last_played_at_by_class"]
        current_max = last_played_at_by_class[endgame_class]
        if current_max is None or endgame_row.played_at > current_max:
            last_played_at_by_class[endgame_class] = endgame_row.played_at


def _accumulate_endgame_rows(
    rows: Sequence[_EndgameRow],
    *,
    track_eval_and_played_at: bool = True,
) -> _EndgameAccumulators:
    """Single-pass per-row accumulation shared by `_aggregate_endgame_stats` (pooled) and
    `aggregate_endgame_stats_by_tc` (per-TC breakdown).

    `track_eval_and_played_at` gates the eval-mean and MAX(played_at) accumulation: the
    per-TC breakdown passes False, so its EndgameCategoryStats keep the schema defaults
    for those fields.
    """
    accumulators = _new_endgame_accumulators()

    for endgame_row in rows:
        endgame_class = _INT_TO_CLASS.get(endgame_row.endgame_class_int)
        if endgame_class is None:
            _capture_invalid_endgame_class(endgame_row.endgame_class_int)
            continue

        outcome = derive_user_result(endgame_row.result, endgame_row.user_color)
        bucket = _classify_endgame_bucket(
            endgame_row.eval_cp, endgame_row.eval_mate, endgame_row.user_color
        )
        _accumulate_wdl_conv_recov(accumulators, endgame_class, outcome, bucket)
        _accumulate_score_gap(accumulators, endgame_class, bucket, endgame_row)

        if track_eval_and_played_at:
            _accumulate_eval_and_played_at(accumulators, endgame_class, endgame_row)

    return accumulators


def _build_category_stats(
    endgame_class: EndgameClass,
    accumulators: _EndgameAccumulators,
) -> EndgameCategoryStats:
    """Build one `EndgameCategoryStats` from the per-class accumulator bundle.

    Shared per-class builder for `_aggregate_endgame_stats` (pooled) and
    `aggregate_endgame_stats_by_tc` (per-TC breakdown). When the accumulators came from
    `_accumulate_endgame_rows(..., track_eval_and_played_at=False)`, `eval_n_by_class` and
    `last_played_at_by_class` stay at their defaultdict defaults for every class, so the
    eval/`last_played_at` fields below come out as the schema defaults, which is what
    the per-TC breakdown reports.
    """
    wdl = accumulators["wdl"]
    conv = accumulators["conv"]
    recov = accumulators["recov"]
    gaps_by_class = accumulators["gaps_by_class"]
    starts_by_class = accumulators["starts_by_class"]
    ends_by_class = accumulators["ends_by_class"]
    eval_sum_by_class = accumulators["eval_sum_by_class"]
    eval_sumsq_by_class = accumulators["eval_sumsq_by_class"]
    eval_n_by_class = accumulators["eval_n_by_class"]
    last_played_at_by_class = accumulators["last_played_at_by_class"]

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
    recovery_pct = round(recovery_saves / recovery_games * 100, 1) if recovery_games > 0 else 0.0

    # Per-class opponent baseline via same-game mirror identity.
    # Conv is a win-rate, Recov is a save-rate, so the two mirror formulas
    # are asymmetric. Gated on the MIRROR bucket size (not the own bucket)
    # via _MIN_OPPONENT_SAMPLE.
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

    # Wilson score + last_played_at via _build_wdl_stats
    # (same helper as openings stats path — no reimplemented statistics).
    # score_p_value retains its existing gated semantics (None when total <
    # PVALUE_RELIABILITY_MIN_N) for backward compat (the field stays on the response; TypeTable does not render it).
    category_last_played_at = last_played_at_by_class[endgame_class]
    wdl_stats = _build_wdl_stats(wins, draws, losses, total, last_played_at=category_last_played_at)
    score_p_value: float | None = wdl_stats.p_value if total >= PVALUE_RELIABILITY_MIN_N else None

    # MG-entry eval aggregation via the verbatim
    # openings eval finalizer (same helper as openings_service.analyze).
    # Eval is per-span at endgame-entry (user-perspective cp); mate excluded,
    # NULL excluded, |cp| >= EVAL_OUTLIER_TRIM_CP trimmed.
    cat_eval_n = eval_n_by_class[endgame_class]
    cat_eval_sum = eval_sum_by_class[endgame_class]
    cat_eval_sumsq = eval_sumsq_by_class[endgame_class]
    cat_eval_pawns: float | None = None
    cat_eval_ci_low_pawns: float | None = None
    cat_eval_ci_high_pawns: float | None = None
    cat_eval_p_value: float | None = None
    cat_eval_confidence: Literal["low", "medium", "high"] = "low"
    if cat_eval_n > 0:
        conf_mg, p_value_mg, mean_cp_mg, ci_half_mg = compute_eval_confidence_bucket(
            cat_eval_sum, cat_eval_sumsq, cat_eval_n
        )  # H0: mean == 0 cp
        cat_eval_pawns = mean_cp_mg / 100.0
        if cat_eval_n >= 2:
            cat_eval_ci_low_pawns = (mean_cp_mg - ci_half_mg) / 100.0
            cat_eval_ci_high_pawns = (mean_cp_mg + ci_half_mg) / 100.0
        cat_eval_p_value = p_value_mg
        cat_eval_confidence = conf_mg

    # Per-class mean per-span gap with
    # paired one-sample z-test via compute_paired_difference_test. n-gates
    # are owned by the helper:
    #   n == 0 -> (0.0, None, None, None) — surface mean as None for wire.
    #   n == 1 -> (mean, None, None, None) — p/CI gated.
    #   n >= 2 -> ci_low/ci_high populated.
    #   n >= CONFIDENCE_MIN_N (=10) -> p_value populated.
    # The CI is 99% (displayed CIs match the verdict level), so the
    # ranked service's significance gate reads it as-is.
    # Sign: exit_score - ES_entry (positive = outperformed Stockfish baseline).
    type_gaps = gaps_by_class[endgame_class]
    type_gap_n = len(type_gaps)
    (
        type_gap_mean_raw,
        type_gap_p,
        type_gap_ci_low,
        type_gap_ci_high,
    ) = compute_paired_difference_test(type_gaps, z=VERDICT_CI_Z_99)
    # When n == 0 compute_paired_difference_test returns mean=0.0. Surface
    # None on the wire so the frontend hides the row (n==0 gate),
    # matching how the cohort-empty case reads.
    type_gap_mean: float | None = type_gap_mean_raw if type_gap_n > 0 else None

    # Start/end means over the identical cohort (same n,
    # same NULL-eval gate — lists have equal length by construction).
    # Use sum/len to avoid a statistics import; None when n == 0 (mirroring
    # type_gap_mean above so all three fields share the same None contract).
    type_starts = starts_by_class[endgame_class]
    type_ends = ends_by_class[endgame_class]
    type_start_mean: float | None = sum(type_starts) / type_gap_n if type_gap_n > 0 else None
    type_end_mean: float | None = sum(type_ends) / type_gap_n if type_gap_n > 0 else None

    return EndgameCategoryStats(
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
        # Per-class Score Gap fields. See
        # _compute_span_scores + compute_paired_difference_test above.
        type_achievable_score_gap_mean=type_gap_mean,
        type_achievable_score_gap_n=type_gap_n,
        type_achievable_score_gap_p_value=type_gap_p,
        type_achievable_score_gap_ci_low=type_gap_ci_low,
        type_achievable_score_gap_ci_high=type_gap_ci_high,
        # Descriptive start/end components.
        type_achievable_score_start_mean=type_start_mean,
        type_achievable_score_end_mean=type_end_mean,
        # WDLStats-aligned score/eval/last_played_at.
        score=wdl_stats.score,
        confidence=wdl_stats.confidence,
        p_value=wdl_stats.p_value,
        ci_low=wdl_stats.ci_low,
        ci_high=wdl_stats.ci_high,
        last_played_at=category_last_played_at,
        avg_eval_pawns=cat_eval_pawns,
        eval_ci_low_pawns=cat_eval_ci_low_pawns,
        eval_ci_high_pawns=cat_eval_ci_high_pawns,
        eval_n=cat_eval_n,
        eval_p_value=cat_eval_p_value,
        eval_confidence=cat_eval_confidence,
        eval_baseline_pawns=EVAL_BASELINE_PAWNS_WHITE,
    )


def _aggregate_endgame_stats(
    rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> tuple[list[EndgameCategoryStats], dict[str, list[float]]]:
    """Aggregate raw per-(game, class) endgame rows into EndgameCategoryStats list.

    Each row is one (game, endgame_class) span; see _normalize_endgame_row for the accepted
    SA Row / tuple shapes. endgame_class_int is 1-6 (see EndgameClassInt).
    A game_id may appear multiple times (once per endgame class it spent >= 6 plies in),
    so a game can count toward several classes.

    Computes per-category:
    - W/D/L counts and percentages
    - Conversion: win rate when user entered with eval advantage
    - Recovery: draw+win rate when user entered with eval deficit

    Also builds gaps_by_bucket — a per-bucket ΔES accumulator
    at per-span grain (not per-game). Returned alongside the categories list;
    current callers do not consume it.

    Returns (categories, gaps_by_bucket) where categories are sorted by total
    game count descending and gaps_by_bucket is a plain dict (not defaultdict).

    Pipeline: normalize each raw row (_normalize_endgame_row) -> accumulate per class
    (_accumulate_endgame_rows) -> build one EndgameCategoryStats per class
    (_build_category_stats) -> sort -> return.
    """
    if not rows:
        return [], {}

    normalized_rows = [_normalize_endgame_row(raw_row) for raw_row in rows]
    accumulators = _accumulate_endgame_rows(normalized_rows)

    categories: list[EndgameCategoryStats] = [
        _build_category_stats(endgame_class, accumulators) for endgame_class in accumulators["wdl"]
    ]

    # Sort by total descending — not a fixed category order
    categories.sort(key=lambda c: c.total, reverse=True)

    # Convert defaultdict to plain dict to avoid downstream defaultdict surprises.
    return categories, dict(accumulators["gaps_by_bucket"])


def aggregate_endgame_stats_by_tc(
    rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> dict[Literal["bullet", "blitz", "rapid", "classical"], list[EndgameCategoryStats]]:
    """Group endgame stats by (TC, class) for the collapsible type-breakdown cards.

    Single pass over the per-class `entry_rows` (already fetched) —
    one row per (game, endgame_class) span, the SAME source the pooled
    `categories` use — keyed on (TC, class). NOT `bucket_rows` (one row per
    game, class = first endgame position): that classified almost every game as
    "mixed", leaving the rook/minor/pawn/queen tiles empty. Returns
    dict[tc_str, list[EndgameCategoryStats]] in bullet/blitz/rapid/classical
    order. Mixed and pawnless are excluded (_TYPE_CARD_EXCLUDED_CLASSES) so the
    per-TC card header equals the sum of the four rendered tiles.

    Prod rows are SA Rows read by attribute (`row.time_control_bucket`,
    `row.next_entry_eval_cp`, ...). Test fixtures use plain tuples with the
    layout: game_id[0], endgame_class_int[1], result[2], user_color[3],
    eval_cp[4], eval_mate[5], time_control_bucket[6], next_entry_eval_cp[7],
    next_entry_eval_mate[8].

    Does NOT touch the pooled `categories` list. The LLM path reads
    `EndgameStatsResponse.categories` (pooled, Mixed included) and is unaffected by
    this function.
    """
    if not rows:
        return {}

    # Own row-shape dispatch (the tuple test-fixture layout embeds
    # time_control_bucket at index 6, shifting next_entry_eval_cp/mate to 7/8 -- a
    # different tuple shape than _normalize_endgame_row's, which has no TC column), then
    # group into per-TC _EndgameRow lists so the shared accumulate/build pipeline
    # (_accumulate_endgame_rows / _build_category_stats, see _aggregate_endgame_stats)
    # can run once per TC bucket instead of duplicating the per-row loop.
    rows_by_tc: dict[str, list[_EndgameRow]] = defaultdict(list)
    for row in rows:
        # entry_rows: SA Row or tuple. For tuples (test fixtures) col 6 is TC.
        if isinstance(row, tuple):
            if len(row) < 7:
                # Legacy 6-column fixture (no TC column) — skip; not per-TC data
                continue
            tc = row[6]
            endgame_row = _EndgameRow(
                endgame_class_int=row[1],
                result=row[2],
                user_color=row[3],
                eval_cp=row[4],
                eval_mate=row[5],
                next_entry_eval_cp=row[7] if len(row) > 7 else None,
                next_entry_eval_mate=row[8] if len(row) > 8 else None,
                played_at=None,
            )
        else:
            tc = row.time_control_bucket
            endgame_row = _EndgameRow(
                endgame_class_int=row.endgame_class,
                result=row.result,
                user_color=row.user_color,
                eval_cp=row.eval_cp,
                eval_mate=row.eval_mate,
                next_entry_eval_cp=row.next_entry_eval_cp,
                next_entry_eval_mate=row.next_entry_eval_mate,
                played_at=None,
            )

        if tc not in _TIME_CONTROL_ORDER:
            continue

        endgame_class = _INT_TO_CLASS.get(endgame_row.endgame_class_int)
        if endgame_class is None:
            continue  # Unknown class int; already captured by _aggregate_endgame_stats

        # The collapsible type cards render only rook/minor_piece/pawn/queen
        # tiles — Mixed is dropped (least-actionable catch-all) and pawnless is
        # hidden. Excluding them here (not just in the frontend) keeps the card header
        # "Games: X% (count)" equal to the sum of the four visible tiles. The pooled
        # `categories` / LLM path still see Mixed via _aggregate_endgame_stats.
        if endgame_class in _TYPE_CARD_EXCLUDED_CLASSES:
            continue

        rows_by_tc[tc].append(endgame_row)

    # Build per-TC lists in fixed order. track_eval_and_played_at=False: this breakdown
    # does not aggregate eval-mean or last_played_at (its EndgameCategoryStats keep the
    # schema defaults for those fields).
    result_by_tc: dict[
        Literal["bullet", "blitz", "rapid", "classical"], list[EndgameCategoryStats]
    ] = {}
    for tc in _TIME_CONTROL_ORDER:
        tc_rows = rows_by_tc.get(tc)
        if not tc_rows:
            continue
        tc_literal = cast(Literal["bullet", "blitz", "rapid", "classical"], tc)
        accumulators = _accumulate_endgame_rows(tc_rows, track_eval_and_played_at=False)
        result_by_tc[tc_literal] = [
            _build_category_stats(endgame_class, accumulators)
            for endgame_class in accumulators["wdl"]
        ]

    return result_by_tc


async def get_endgame_stats(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: _date | None = None,
    to_date: _date | None = None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameStatsResponse:
    """Orchestrate endgame stats query and return EndgameStatsResponse.

    Steps:
    1. Fetch one row per (game, endgame_class) span meeting the ply threshold.
    2. Aggregate into per-category stats with conversion/recovery.
    3. Return sorted categories (by total desc).
    """
    rows = await query_endgame_entry_rows(
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
    )
    # _aggregate_endgame_stats returns (categories, gaps_by_bucket);
    # get_endgame_stats does not use gaps_by_bucket.
    categories, _gaps_by_bucket = _aggregate_endgame_stats(rows)

    # Total games matching current filters (not just endgame games)
    total_games = await count_filtered_games(
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
    )
    # Count games that reached an endgame phase per the uniform ENDGAME_PLY_THRESHOLD rule:
    # a game qualifies if its total endgame plies meet the threshold.
    endgame_games = await count_endgame_games(
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
    from_date: _date | None = None,
    to_date: _date | None = None,
    offset: int = 0,
    limit: int = 20,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> EndgameGamesResponse:
    """Orchestrate endgame games query and return paginated EndgameGamesResponse.

    Steps:
    1. Fetch paginated Game objects for the requested endgame class.
    2. Build GameRecord objects matching the existing analysis schema.
    3. Return EndgameGamesResponse with pagination metadata.
    """
    games, matched_count = await _query_endgame_games(
        session,
        user_id=user_id,
        endgame_class=endgame_class,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
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
            ply_count=g.ply_count,
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


# --- Performance chart service functions ---


def build_wdl_summary(rows: list[Row[Any]]) -> EndgameWDLSummary:
    """Build EndgameWDLSummary from query_endgame_performance_rows rows.

    Row shape: ``(played_at, result, user_color, platform,
    time_control_bucket)`` — only indices 1 (result) and 2 (user_color) are
    consumed here; the trailing platform / TC columns enable per-combo
    partitioning in the Endgame ELO orchestrator and are ignored otherwise.
    """
    wins = draws = losses = 0
    for row in rows:
        result = row[1]
        user_color = row[2]
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


def compute_score_gap_timeline(
    endgame_rows: Sequence[Row[Any] | tuple[Any, ...]],
    non_endgame_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int,
    cutoff_str: str | None = None,
) -> list[ScoreGapTimelinePoint]:
    """Weekly rolling-window series of (endgame_score - non_endgame_score).

    Each side maintains its own trailing `window`-game window so weeks with
    sparse activity on one side still reflect the broader history of that
    side.
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
    but lets earlier games pre-fill the rolling windows, so the recency
    filter does not starve the window when the user picks a short window like
    "past 3 months".
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
    # Per-ISO-week count of all events (endgame + non-endgame); drives the
    # frontend volume bars on the Score % Difference timeline.
    per_week_total: dict[tuple[int, int], int] = {}
    # Per-ISO-week count of ENDGAME games only; drives the Endgame ELO
    # Timeline volume bars. Keep this a true per-week count, not the
    # trailing-window count: the bars stop reflecting weekly activity otherwise.
    per_week_endgame: dict[tuple[int, int], int] = {}
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
        if side == "endgame":
            per_week_endgame[(iso_year, iso_week)] = (
                per_week_endgame.get((iso_year, iso_week), 0) + 1
            )

        eg_count = len(endgame_window)
        non_endgame_count = len(non_endgame_window)
        if eg_count == 0 or non_endgame_count == 0:
            # Can't compute a difference until both sides have at least one
            # game; defer emission. The MIN_GAMES_FOR_TIMELINE filter below
            # also drops anything still too thin once both sides start.
            continue

        endgame_mean = statistics.mean(endgame_window)
        non_endgame_mean = statistics.mean(non_endgame_window)
        diff = endgame_mean - non_endgame_mean

        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        # sanity: score_difference == endgame_score - non_endgame_score within
        # rounding (1e-9 target; all three rounded to 4 decimals here). The
        # absolute per-side values are persisted so the frontend two-line chart
        # and the `score_timeline` insights subsection can read them directly
        # instead of reconstructing them from the signed difference.
        data_by_week[(iso_year, iso_week)] = {
            "date": monday.isoformat(),
            "score_difference": round(diff, 4),
            "endgame_game_count": eg_count,
            "non_endgame_game_count": non_endgame_count,
            "per_week_total_games": per_week_total[(iso_year, iso_week)],
            "per_week_endgame_games": per_week_endgame.get((iso_year, iso_week), 0),
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


# Quintile labels for the 5 pressure bins (0=max pressure, 4=min pressure).
_QUINTILE_LABELS: list[str] = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]

# Clamp: games where either clock at endgame entry exceeds this multiple of
# base_time_seconds are treated as bad data (bogus clock readings, e.g. from
# adjudicated or disconnected games). 2x handles legitimate banked increment
# (p99 in prod is 109%), but >200% is noise (saw max 2047% in prod).
MAX_CLOCK_PCT_OF_BASE = 2.0

# Rolling-window size for the Average Clock Difference over Time line chart.
CLOCK_PRESSURE_TIMELINE_WINDOW: int = 100


# Fixed display order for time control rows (fastest to slowest).
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]


# Rolling window size for the Endgame ELO timeline chart.
# Matches SCORE_GAP_TIMELINE_WINDOW.
ENDGAME_ELO_TIMELINE_WINDOW = 100

# Ordered combo list: chess.com first then lichess, per-platform follows
# _TIME_CONTROL_ORDER. Used for stable response ordering.
_ENDGAME_ELO_COMBO_ORDER: list[tuple[str, str]] = [
    (platform_name, tc) for platform_name in ("chess.com", "lichess") for tc in _TIME_CONTROL_ORDER
]

# Logistic stretch around Actual ELO.
# The `400` is fixed by Elo's logistic-skill assumption -- the same `400` the
# FIDE Performance Rating formula uses -- not a knob.
# See .planning/notes/endgame-elo-logistic-anchored.md for derivation.
_ELO_LOGISTIC_SCALE = 400.0

# Score-clamp epsilon for the logit transform — protects against log(0) when
# the trailing-window mean hits exactly 0.0 (all losses) or 1.0 (all wins).
# 1e-6 keeps the per-side ELO bounded inside roughly +-2400 (400 * log10(1e6))
# which is well past realistic territory at n=100.
_ENDGAME_ELO_SCORE_EPSILON = 1e-6


def _endgame_elo_logistic(
    actual_elo: int,
    endgame_score: float,
    non_endgame_score: float,
) -> tuple[int, int]:
    """Logistic stretch around Actual ELO.

    Returns (endgame_elo, non_endgame_elo) where the midpoint equals
    Actual ELO by construction:

        spread = 400 * log10( (s_E / (1 - s_E)) / (s_N / (1 - s_N)) )
        endgame_elo     = actual_elo + spread / 2
        non_endgame_elo = actual_elo - spread / 2

    Each side score is clamped to (epsilon, 1 - epsilon) so a streak of all
    wins or all losses on either side cannot blow up the logit. Same `400`
    that appears in the FIDE Performance Rating formula — no free constant.

    Don't derive the sides from a per-side FIDE Performance Rating: the 100-game
    trailing PR estimator lags the live Glicko snapshot used for Actual ELO, so
    Actual ELO stops sitting between the two lines (it failed in ~88% of weekly
    points). See `.planning/notes/endgame-elo-logistic-anchored.md`.
    """
    s_e = max(min(endgame_score, 1 - _ENDGAME_ELO_SCORE_EPSILON), _ENDGAME_ELO_SCORE_EPSILON)
    s_n = max(min(non_endgame_score, 1 - _ENDGAME_ELO_SCORE_EPSILON), _ENDGAME_ELO_SCORE_EPSILON)
    spread = _ELO_LOGISTIC_SCALE * math.log10((s_e / (1 - s_e)) / (s_n / (1 - s_n)))
    return (
        int(round(actual_elo + spread / 2)),
        int(round(actual_elo - spread / 2)),
    )


def _compute_endgame_elo_weekly_series(
    score_gap_timeline: Sequence[ScoreGapTimelinePoint],
    actual_elo_dates: Sequence[datetime],
    actual_elo_ratings: Sequence[int],
    cutoff_str: str | None = None,
) -> list[EndgameEloTimelinePoint]:
    """Build weekly Endgame ELO + Non-Endgame ELO + Actual ELO series for one combo.

    For each ``ScoreGapTimelinePoint`` (already filtered to weeks where both
    the endgame and non-endgame trailing windows hold ``>= MIN_GAMES_FOR_TIMELINE``
    games by the upstream producer), emit one ``EndgameEloTimelinePoint`` with:

    - ``endgame_elo`` / ``non_endgame_elo`` = ``_endgame_elo_logistic(actual_elo,
      pt.endgame_score, pt.non_endgame_score)``. A logistic stretch around the
      asof-joined Actual ELO; the midpoint equals Actual ELO by construction.
    - ``actual_elo`` = asof-join of (actual_elo_dates, actual_elo_ratings) at
      ``next_monday_dt``. Forward-fills from the latest prior game when the
      week itself has no games.
    - ``endgame_games_in_window`` = ``pt.endgame_game_count`` (carry-through
      from the score-gap producer; the trailing 100-game window count).
    - ``per_week_endgame_games`` = ``pt.per_week_endgame_games`` (true per-ISO
      week count).
    - ``per_week_total_games`` = ``pt.per_week_total_games`` (endgame +
      non-endgame games this ISO week; drives the volume bars because the
      chart plots both lines, so total weekly activity is what matters).

    ``cutoff_str`` filters output points to dates ``>= cutoff_str``; the
    score-gap producer already pre-fills the trailing windows from earlier
    games so no double-filtering is needed here.
    """
    out: list[EndgameEloTimelinePoint] = []
    for pt in score_gap_timeline:
        if cutoff_str is not None and pt.date < cutoff_str:
            continue

        # Plot on the ISO-week Monday to match the Score Gap timeline (which
        # also stores Monday). The asof bisect still runs against next-Monday
        # so the rating reflects the END of the ISO week -- i.e. the same
        # window state that drove the score-gap value plotted at this Monday.
        # Don't label the point with the Sunday of the week: that shifts the two
        # charts against each other by 6 days on the x-axis.
        try:
            monday = datetime.fromisoformat(pt.date).date()
        except ValueError:
            continue
        tzinfo = actual_elo_dates[0].tzinfo if actual_elo_dates else None
        monday_dt = datetime.combine(monday, time.min, tzinfo=tzinfo)
        next_monday_dt = monday_dt + timedelta(days=7)

        idx = bisect.bisect_right(actual_elo_dates, next_monday_dt)
        if idx == 0:
            # No prior actual-rating sample for this combo -- defensive skip.
            # In practice the score-gap producer already enforces both-window
            # MIN_GAMES_FOR_TIMELINE so an actual-rating row exists.
            continue
        actual_elo_at_date = actual_elo_ratings[idx - 1]

        endgame_elo, non_endgame_elo = _endgame_elo_logistic(
            int(actual_elo_at_date), pt.endgame_score, pt.non_endgame_score
        )

        out.append(
            EndgameEloTimelinePoint(
                date=monday.isoformat(),
                endgame_elo=endgame_elo,
                non_endgame_elo=non_endgame_elo,
                actual_elo=int(actual_elo_at_date),
                endgame_games_in_window=pt.endgame_game_count,
                per_week_endgame_games=pt.per_week_endgame_games,
                per_week_total_games=pt.per_week_total_games,
            )
        )

    return out


def extract_entry_clocks(
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
    for ply, clock in zip(plies, clocks, strict=True):
        if ply % 2 == user_parity and user_clock is None:
            user_clock = clock
        elif ply % 2 != user_parity and opp_clock is None:
            opp_clock = clock
        if user_clock is not None and opp_clock is not None:
            break
    return user_clock, opp_clock


def _bump_wdl_tuple(
    wdl: tuple[int, int, int],
    outcome: Literal["win", "draw", "loss"],
    *,
    invert: bool = False,
) -> tuple[int, int, int]:
    """Increment one (wins, draws, losses) tuple for one row's outcome.

    `invert=True` flips win<->loss (used for the opponent-side quintile WDL, where a
    user win is an opponent loss and vice versa; draws stay draws either way — see
    `iterate_clock_rows`'s docstring for why the two sides are tallied this way).
    """
    wins, draws, losses = wdl
    if outcome == "draw":
        return wins, draws + 1, losses
    is_win = outcome == "win"
    if invert:
        is_win = not is_win
    if is_win:
        return wins + 1, draws, losses
    return wins, draws, losses + 1


def iterate_clock_rows(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> tuple[
    dict[str, int],
    dict[tuple[str, int], tuple[int, int, int]],
    dict[tuple[str, int], tuple[int, int, int]],
    dict[tuple[str, int], int],
]:
    """Iterate clock_rows once, accumulating per-TC and per-(TC, quintile) data.

    Builds TWO parallel quintile splits from the SAME filtered
    games — one bucketed by USER's clock-pct, one by OPPONENT's clock-pct. The
    per-quintile delta is computed in build_quintile_bullets against these
    two splits, which are NOT independent (see below) — the covariance
    correction accounts for the overlap.

    Returns:
        tc_total: dict[tc -> total valid endgame games]
        tc_user_quintile_wdl: dict[(tc, quintile) -> (wins, draws, losses)] bucketed by USER's clock-pct
        tc_opp_quintile_wdl:  dict[(tc, quintile) -> (wins, draws, losses)] bucketed by OPP's clock-pct,
            with result inverted from the opponent's perspective (user-win = opp-loss).
        tc_shared_quintile_count: dict[(tc, quintile) -> count of games where
            user_quintile == opp_quintile == quintile].
            Feeds the covariance-correction `shared_n` parameter of
            `compute_score_difference_test` in `build_quintile_bullets`.

    Quintile index = min(4, int(clk_pct * 5)) so:
        0.0..0.2 -> 0 (max pressure), 0.2..0.4 -> 1, ..., 0.8..1.0 -> 4 (min pressure)

    User and opponent quintile assignments are computed independently per row
    (each side's own clock-pct decides its own bucket), but the two SPLITS are
    NOT statistically independent samples: whenever a game's user_quintile
    equals its opp_quintile (both players in the same time-pressure bucket),
    that single game contributes to BOTH cohorts for the SAME quintile index
    q — as `X` (user outcome) on the user side and as the exact linear inverse
    `1 - X` (opponent outcome) on the opp side. That shared-game overlap makes
    `compute_score_difference_test`'s naive independent-samples SE an
    underestimate; this function tracks the per-(tc, quintile)
    shared-game count `m` (below) and passes it through `build_quintile_bullets`
    as `shared_n` so the SE gets the `+2m*v/(n_u*n_o)` covariance-correction
    term instead of silently treating the cohorts as independent.

    Rows with base_clock <= 0 are skipped (defensive guard).
    Rows where either clock exceeds MAX_CLOCK_PCT_OF_BASE * base_clock are skipped
    (bogus readings; compute_clock_diff_timeline applies the same guard).
    """
    tc_total: dict[str, int] = defaultdict(int)
    tc_user_quintile_wdl: dict[tuple[str, int], tuple[int, int, int]] = defaultdict(
        lambda: (0, 0, 0)
    )
    tc_opp_quintile_wdl: dict[tuple[str, int], tuple[int, int, int]] = defaultdict(
        lambda: (0, 0, 0)
    )
    # Count of games per (tc, quintile) where the user
    # and opponent land in the SAME quintile — feeds the covariance correction.
    tc_shared_quintile_count: dict[tuple[str, int], int] = defaultdict(int)

    for row in clock_rows:
        time_control_bucket: str | None = row[1]
        base_time_seconds: int | None = row[2]
        result: str = row[4]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]

        if time_control_bucket is None:
            continue
        # Skip rows with invalid base clock.
        if base_time_seconds is None or base_time_seconds <= 0:
            continue

        tc = time_control_bucket
        tc_total[tc] += 1

        user_clock, opp_clock = extract_entry_clocks(ply_array, clock_array, user_color)
        if user_clock is None or opp_clock is None:
            continue
        if (
            user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
            or opp_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
        ):
            continue

        # Independent quintile assignments per side. 0 = 0-20% remaining (max
        # pressure), 4 = 80-100% remaining (min pressure).
        user_clk_pct = user_clock / base_time_seconds
        opp_clk_pct = opp_clock / base_time_seconds
        user_quintile = min(4, int(user_clk_pct * 5))
        opp_quintile = min(4, int(opp_clk_pct * 5))
        # This game overlaps both cohorts for the
        # same (tc, quintile) bucket when the two sides share a quintile.
        if user_quintile == opp_quintile:
            tc_shared_quintile_count[(tc, user_quintile)] += 1

        # Accumulate user-side WDL into user_quintile_wdl.
        outcome = derive_user_result(result, user_color)
        tc_user_quintile_wdl[(tc, user_quintile)] = _bump_wdl_tuple(
            tc_user_quintile_wdl[(tc, user_quintile)], outcome
        )

        # Accumulate opp-side WDL into opp_quintile_wdl with inverted outcome
        # (user-win = opp-loss; draws stay draws). Same game, different
        # quintile index (driven by opponent's clock-pct).
        tc_opp_quintile_wdl[(tc, opp_quintile)] = _bump_wdl_tuple(
            tc_opp_quintile_wdl[(tc, opp_quintile)], outcome, invert=True
        )

    return (
        dict(tc_total),
        dict(tc_user_quintile_wdl),
        dict(tc_opp_quintile_wdl),
        dict(tc_shared_quintile_count),
    )


def build_quintile_bullets(
    tc: str,
    user_quintile_wdl: dict[tuple[str, int], tuple[int, int, int]],
    opp_quintile_wdl: dict[tuple[str, int], tuple[int, int, int]],
    shared_quintile_count: dict[tuple[str, int], int],
) -> list[PressureQuintileBullet]:
    """Build exactly 5 PressureQuintileBullet entries for quintiles 0..4.

    Each bullet compares the user's score
    in quintile Q (bucketed by USER's clock-pct) against the opponent's score
    in the same quintile index Q (bucketed by OPPONENT's clock-pct). The two
    splits are NOT independent samples of the same filtered game-set — a game
    where the user's and opponent's quintile happen to coincide contributes to
    BOTH cohorts for the same quintile index (see `iterate_clock_rows`
    docstring). `shared_quintile_count[(tc, q)]` (the
    number of such overlapping games) is passed as `shared_n` to
    `compute_score_difference_test`, which adds a covariance-correction term to
    the SE instead of treating the two cohorts as independent.

    For each quintile q in 0..4:
    - n_user = sum of user_quintile_wdl[(tc, q)]; n_opp = sum of opp_quintile_wdl[(tc, q)].
    - Bullet n is the user-side count (drives the displayed sample-size chip).
    - n-gate: min(n_user, n_opp) >= MIN_GAMES_PER_PRESSURE_BIN. If unmet,
      delta is the raw difference (or 0.0 when either side has zero games) and
      all stats (p_value, ci_low, ci_high, opp_score) are None.
    - When the gate is met, delta = user_score - opp_score and significance comes
      from compute_score_difference_test(user_w, user_d, user_l, n_user, opp_w,
      opp_d, opp_l, n_opp, shared_n=m).
    """
    bullets: list[PressureQuintileBullet] = []
    for q in range(5):
        u_w, u_d, u_l = user_quintile_wdl.get((tc, q), (0, 0, 0))
        n_user = u_w + u_d + u_l
        o_w, o_d, o_l = opp_quintile_wdl.get((tc, q), (0, 0, 0))
        n_opp = o_w + o_d + o_l

        # n-gate: both sides must clear the bin floor before we trust
        # the delta enough to report stats. Zero games on either side also fails
        # the gate (no opp_score to subtract).
        gate_met = n_user >= MIN_GAMES_PER_PRESSURE_BIN and n_opp >= MIN_GAMES_PER_PRESSURE_BIN

        if not gate_met:
            # Raw delta only when both sides have at least one game; otherwise 0.0.
            if n_user > 0 and n_opp > 0:
                raw_user_score = (u_w + 0.5 * u_d) / n_user
                raw_opp_score = (o_w + 0.5 * o_d) / n_opp
                raw_delta = raw_user_score - raw_opp_score
            else:
                raw_delta = 0.0
            bullets.append(
                PressureQuintileBullet(
                    quintile_index=q,
                    quintile_label=_QUINTILE_LABELS[q],
                    n=n_user,
                    n_opp=n_opp,
                    delta=raw_delta,
                    p_value=None,
                    ci_low=None,
                    ci_high=None,
                    opp_score=None,
                )
            )
            continue

        user_score = (u_w + 0.5 * u_d) / n_user
        opp_score = (o_w + 0.5 * o_d) / n_opp
        delta = user_score - opp_score
        m = shared_quintile_count.get((tc, q), 0)
        # 99% CI, the level of the dot-colour verdict gate.
        p_value, ci_low, ci_high = compute_score_difference_test(
            u_w, u_d, u_l, n_user, o_w, o_d, o_l, n_opp, shared_n=m, z=VERDICT_CI_Z_99
        )
        bullets.append(
            PressureQuintileBullet(
                quintile_index=q,
                quintile_label=_QUINTILE_LABELS[q],
                n=n_user,
                n_opp=n_opp,
                delta=delta,
                p_value=p_value,
                ci_low=ci_low,
                ci_high=ci_high,
                opp_score=opp_score,
                significant=ci_excludes(0.0, ci_low, ci_high),
            )
        )
    return bullets


def compute_clock_diff_timeline(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int = CLOCK_PRESSURE_TIMELINE_WINDOW,
    cutoff: datetime | None = None,
) -> ClockDiffTimelineResponse:
    """Build the per-ISO-week rolling clock-diff timeline.

    Pooled across TCs (no time-control faceting — matches the pre-deletion
    line-chart convention). Filters out rows that lack clock data, have
    base_time_seconds <= 0, exceed MAX_CLOCK_PCT_OF_BASE, or are missing
    played_at. One point per ISO Monday using the rolling-window mean value of
    the LAST eligible game in that week. per_week_game_count counts only
    eligible games in THIS week; game_count reports the trailing window size.

    Runs as a separate single-pass aggregator (NOT inside iterate_clock_rows)
    to keep timeline semantics independent of the per-TC card aggregator —
    different filter semantics (pooled vs per-TC) and different output shape
    (chronological points vs TC buckets) make a shared pass awkward.

    Units: avg_clock_diff_pct is in PERCENT (not fraction). Multiplied by 100
    here so the field is directly chart-renderable on a [-30, 30] Y-axis.

    Args:
        clock_rows: rows from query_clock_stats_rows (shape: game_id,
            time_control_bucket, base_time_seconds, termination, result,
            user_color, ply_array, clock_array, played_at). Callers should pass
            the UNFILTERED-by-recency row stream so the rolling window can
            pre-fill from games before ``cutoff``; the function drops emitted
            points dated before the cutoff's ISO Monday.
        window: trailing rolling-window size. Defaults to
            CLOCK_PRESSURE_TIMELINE_WINDOW (100). Parameterised for tests that
            want to exercise window-truncation behaviour without 100 fixtures.
        cutoff: optional recency cutoff. Rows with ``played_at < cutoff`` still
            participate in the rolling window (so the first displayed week's
            "trailing 100" mean is fully populated), but ISO-week points whose
            Monday falls strictly before ``cutoff_monday`` are not emitted.
            ``None`` (no cutoff) keeps the legacy behaviour of emitting every
            week.

    Returns:
        ClockDiffTimelineResponse with chronologically-sorted points (empty
        when no row passes the eligibility predicate).
    """
    # Phase 1: collect eligible (played_at, clock_diff_pct) tuples + per-week
    # raw counts. Eligibility predicate mirrors iterate_clock_rows exactly —
    # if you change one, change the other.
    eligible: list[tuple[datetime, float]] = []
    per_week_counts: dict[_date, int] = defaultdict(int)
    for row in clock_rows:
        time_control_bucket: str | None = row[1]
        base_time_seconds: int | None = row[2]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]
        played_at = row[8] if len(row) > 8 else None
        if time_control_bucket is None:
            continue
        if base_time_seconds is None or base_time_seconds <= 0:
            continue
        if played_at is None:
            continue
        user_clock, opp_clock = extract_entry_clocks(ply_array, clock_array, user_color)
        if user_clock is None or opp_clock is None:
            continue
        if (
            user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
            or opp_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds
        ):
            continue
        clock_diff_pct = (user_clock - opp_clock) / base_time_seconds * 100
        eligible.append((played_at, clock_diff_pct))
        monday = played_at.date() - timedelta(days=played_at.date().weekday())
        # Only count games at-or-after the cutoff toward per_week_counts.
        # Pre-cutoff games pre-fill the rolling window (Phase 2) but never
        # produce an emitted point, so their per-week tallies are not surfaced.
        if cutoff is None or played_at >= cutoff:
            per_week_counts[monday] += 1

    # Phase 2: sort by played_at ASC, then trailing rolling-window walk.
    # week_to_rolling maps ISO Monday -> (rolling_mean, window_size_at_that_point).
    # Overwrite-on-week means the LAST game of the week wins (matches pre-88-07
    # convention and the iso_week_bucketing_emits_last_game test).
    eligible.sort(key=lambda t: t[0])
    rolling: list[float] = []
    week_to_rolling: dict[_date, tuple[float, int]] = {}
    for played_at, diff_pct in eligible:
        rolling.append(diff_pct)
        if len(rolling) > window:
            rolling = rolling[-window:]
        avg = sum(rolling) / len(rolling)
        monday = played_at.date() - timedelta(days=played_at.date().weekday())
        week_to_rolling[monday] = (round(avg, 4), len(rolling))

    # Phase 3: emit chronologically. With a cutoff, drop ISO-week points whose
    # Monday is strictly before the cutoff's ISO Monday — pre-cutoff weeks
    # already contributed to the rolling-window state (Phase 2) so the first
    # emitted post-cutoff point has a fully populated trailing window.
    cutoff_monday: _date | None = None
    if cutoff is not None:
        cutoff_date = cutoff.date()
        cutoff_monday = cutoff_date - timedelta(days=cutoff_date.weekday())
    points: list[ClockDiffTimelinePoint] = []
    for monday in sorted(week_to_rolling.keys()):
        if cutoff_monday is not None and monday < cutoff_monday:
            continue
        avg, n = week_to_rolling[monday]
        points.append(
            ClockDiffTimelinePoint(
                date=monday.isoformat(),
                avg_clock_diff_pct=avg,
                game_count=n,
                per_week_game_count=per_week_counts[monday],
            )
        )
    return ClockDiffTimelineResponse(points=points)


def build_endgame_elo_combos(
    endgame_rows_all: Sequence[Row[Any] | tuple[Any, ...]],
    non_endgame_rows_all: Sequence[Row[Any] | tuple[Any, ...]],
    asof_by_combo: dict[tuple[str, str], tuple[list[Any], list[int]]],
    cutoff_str: str | None,
) -> list[EndgameEloTimelineCombo]:
    """Pure per-(platform, TC) Endgame ELO combo builder.

    Used by the ranked path (``endgame_ranked_service``). ``endgame_rows_all`` /
    ``non_endgame_rows_all`` are cross-combo rows shaped ``(played_at, result,
    user_color, platform, time_control_bucket)``; ``asof_by_combo`` maps
    (platform, TC) to parallel ``(dates, ratings)`` arrays for the Actual ELO
    asof-join. Combos with zero qualifying points are dropped and
    the result follows ``_ENDGAME_ELO_COMBO_ORDER``.
    """
    # Partition the cross-combo endgame / non-endgame rows by (platform, TC).
    # These rows come from query_endgame_performance_rows with shape
    # (played_at, result, user_color, platform, time_control_bucket) — platform
    # is at index 3 and time_control_bucket at index 4.
    endgame_by_combo: dict[tuple[str, str], list[tuple[Any, ...]]] = {}
    for row in endgame_rows_all:
        key = (row[3], row[4])
        endgame_by_combo.setdefault(key, []).append(tuple(row))
    non_endgame_by_combo: dict[tuple[str, str], list[tuple[Any, ...]]] = {}
    for row in non_endgame_rows_all:
        key = (row[3], row[4])
        non_endgame_by_combo.setdefault(key, []).append(tuple(row))

    combos: list[EndgameEloTimelineCombo] = []
    for platform_name, tc in _ENDGAME_ELO_COMBO_ORDER:
        key = (platform_name, tc)
        asof_dates, asof_ratings = asof_by_combo.get(key, ([], []))

        # Per-combo score-gap series — built ONLY from this combo's rows so
        # the Endgame ELO line for combo X is not contaminated by games from
        # other combos.
        score_gap_for_combo = compute_score_gap_timeline(
            endgame_by_combo.get(key, []),
            non_endgame_by_combo.get(key, []),
            ENDGAME_ELO_TIMELINE_WINDOW,
            cutoff_str=cutoff_str,
        )

        points = _compute_endgame_elo_weekly_series(
            score_gap_for_combo,
            asof_dates,
            asof_ratings,
            cutoff_str=cutoff_str,
        )
        if not points:
            # Drop the combo entirely when no qualifying points.
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
    return combos
