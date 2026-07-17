"""best_move_candidates.py — pure candidate logic for Gem/Great detection (Phase 174).

Three pure, unit-testable pieces, each reusing an existing single-source
implementation so the backend can never drift from the live board:

  * pinned_elo_for_mover (GEMS-05, D-04) — the mover's lichess-blitz-equivalent
    rating, clamped to the Maia ELO ladder [600, 2600]. Reproduces the frontend's
    `deriveRawDefault` (`*_lichess_blitz ?? raw`, flawchess passthrough) via the
    shared normalize_to_lichess_blitz + clamp_to_ladder_bounds — no re-derivation.
  * passes_inaccuracy_gate (GEMS-02, D-05a) — the write-time candidate gate: keep
    a ply only when its best move beats the runner-up by >= INACCURACY_DROP in
    expected score, via the shared eval_cp_to_expected_score sigmoid with the
    flaws_service Option-B mate mapping (map mate to ±MATE_CP_EQUIVALENT BEFORE
    the sigmoid, NOT eval_mate_to_expected_score).
  * classify_best_move (GEMS-07) — the query-time gem/great/neither tier, a PURE
    function of stored (maia_prob, cp margin) and module constants only: no DB
    read, no engine call, no re-inference. A threshold retune therefore
    reclassifies the whole corpus with zero re-analysis.

Every function is pure (no I/O). The module reuses the canonical sigmoid,
ELO normalization, clamp, and drop thresholds verbatim; it never re-declares them.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import and_, case, func, literal
from sqlalchemy.sql.elements import ColumnElement

from app.schemas.normalization import Platform, TimeControlBucket
from app.services.chesscom_to_lichess import normalize_to_lichess_blitz
from app.services.eval_utils import LICHESS_K, eval_cp_to_expected_score
from app.services.flaws_service import INACCURACY_DROP, MATE_CP_EQUIVALENT, MISTAKE_DROP
from app.services.maia_encoding import clamp_to_ladder_bounds

# ─── Classification constants (GEMS-07) ────────────────────────────────────────

# Maia policy-probability ceilings, mirroring the frontend gemMove.ts semantics.
# A gem is "fewer than 1 in 5 rating-peers would play it" (GEM_MAIA_MAX_PROB); a
# great move is the (0.20, 0.50] band (ROADMAP SC5). Both are flat cutoffs (D-08
# defers any per-ELO iso-rarity curve). Named constants — no magic numbers.
GEM_MAIA_MAX_PROB: float = 0.20
GREAT_MAIA_MAX_PROB: float = 0.50

# Imported-eval divergence guard (Quick 260717-gmg). For a lichess-eval game the
# eval graph (game_positions.eval_cp) is lichess's imported %eval, while best_cp
# is OUR Stockfish (1M nodes) — two different engines. When our best-move eval is
# more OPTIMISTIC than lichess's authoritative post-move eval (mover POV) by more
# than this many points of expected score, our shallow search has overrated a
# sharp line and the "best move" pick is untrustworthy, so we suppress the badge
# rather than surface a spurious gem/great (e.g. game 640125, 55.Qc6+: our −0.82
# vs lichess −2.46 = 0.14 ES optimism). Directional (only optimistic divergence
# is a false positive) and query-time, so retuning reclassifies the corpus with
# zero re-analysis (GEMS-07). No-op for engine games (one engine feeds both).
BEST_MOVE_DIVERGENCE_MAX_ES: float = 0.10

MoverColor = Literal["white", "black"]
BestMoveTier = Literal["gem", "great", "neither"]


# ─── Mover-color helper (ply parity) ───────────────────────────────────────────


def mover_color_for_ply(ply: int) -> MoverColor:
    """The color to move at `ply`, by the established parity rule: white moves on
    even plies (0, 2, ...), black on odd plies. Matches flaws_service's convention."""
    return "white" if ply % 2 == 0 else "black"


# ─── Pinned ELO (GEMS-05, D-04) ────────────────────────────────────────────────


def pinned_elo_for_mover(
    *,
    raw_rating: int,
    platform: Platform,
    time_control_bucket: TimeControlBucket | None,
    is_correspondence: bool,
) -> float:
    """Derive the mover's Maia-facing ELO: the lichess-blitz-equivalent rating,
    clamped to the [600, 2600] ladder (D-04), matching the live board exactly.

    Reproduces the frontend `deriveRawDefault` fallback chain (`*_lichess_blitz ??
    raw`) with a flawchess passthrough, delegating to the shared
    normalize_to_lichess_blitz + clamp_to_ladder_bounds — never re-deriving either.
    A stored flawchess rating is already lichess-blitz-equivalent by construction
    (STORE-03), so it skips normalization. When normalization returns None
    (correspondence has no real-time analogue) or the TC bucket is missing, fall
    back to the raw rating, then clamp.
    """
    if platform == "flawchess":
        normalized: int | None = raw_rating
    elif time_control_bucket is None:
        normalized = None
    else:
        normalized = normalize_to_lichess_blitz(
            raw_rating, platform, time_control_bucket, is_correspondence=is_correspondence
        )
    rating = normalized if normalized is not None else raw_rating
    return clamp_to_ladder_bounds(rating)


# ─── Expected-score helper (shared sigmoid + Option-B mate) ────────────────────


def _eval_to_expected_score(
    eval_cp: int | None, eval_mate: int | None, mover_color: MoverColor
) -> float | None:
    """Mover-POV expected score for one (cp, mate) eval, or None when both are
    absent. Option B: map mate to ±MATE_CP_EQUIVALENT cp BEFORE the shared sigmoid
    (flaws_service convention) — NOT eval_mate_to_expected_score, whose hard 1.0/0.0
    mis-sizes per-ply drop math."""
    if eval_mate is not None:
        cp_equiv = MATE_CP_EQUIVALENT if eval_mate > 0 else -MATE_CP_EQUIVALENT
        return eval_cp_to_expected_score(cp_equiv, mover_color)
    if eval_cp is not None:
        return eval_cp_to_expected_score(eval_cp, mover_color)
    return None


# ─── Inaccuracy candidate gate (GEMS-02, D-05a) ────────────────────────────────


def passes_inaccuracy_gate(
    best_cp: int | None,
    best_mate: int | None,
    second_cp: int | None,
    second_mate: int | None,
    mover_color: MoverColor,
) -> bool:
    """True iff the best move beats the runner-up by at least INACCURACY_DROP in
    mover-POV expected score (D-05a). False when either eval is missing."""
    best_es = _eval_to_expected_score(best_cp, best_mate, mover_color)
    second_es = _eval_to_expected_score(second_cp, second_mate, mover_color)
    if best_es is None or second_es is None:
        return False
    return best_es - second_es >= INACCURACY_DROP


# ─── Gem/Great/neither classification (GEMS-07) ────────────────────────────────


def classify_best_move(
    maia_prob: float,
    best_cp: int | None,
    best_mate: int | None,
    second_cp: int | None,
    second_mate: int | None,
    mover_color: MoverColor,
    post_move_cp: int | None = None,
    post_move_mate: int | None = None,
    is_lichess_eval_game: bool = False,
) -> BestMoveTier:
    """Classify a stored best-move candidate as gem / great / neither, PURELY from
    the stored maia_prob + cp margin and module constants (GEMS-07): no DB, no
    engine, no re-inference. A threshold retune reclassifies the corpus for free.

    C2 (only-good-move): the best move must beat the runner-up by >= MISTAKE_DROP
    in mover-POV expected score, else "neither". Given C2, C1 (hard-to-find):
    maia_prob <= GEM_MAIA_MAX_PROB -> "gem"; <= GREAT_MAIA_MAX_PROB -> "great";
    otherwise "neither".

    Imported-eval divergence guard (Quick 260717-gmg): for lichess-eval games
    (is_lichess_eval_game=True) `post_move_cp`/`post_move_mate` carry lichess's
    authoritative post-move %eval for this ply. Because a candidate is stored only
    when played == our Stockfish best, that eval describes the same resulting
    position as best_cp — so when our best-move expected score exceeds it by more
    than BEST_MOVE_DIVERGENCE_MAX_ES (mover POV), our search overrated a sharp line
    and we suppress the badge. No-op for engine games (post-move eval is our own
    engine, so it never materially diverges) or when the post-move eval is missing.
    """
    best_es = _eval_to_expected_score(best_cp, best_mate, mover_color)
    second_es = _eval_to_expected_score(second_cp, second_mate, mover_color)
    if best_es is None or second_es is None:
        return "neither"
    if best_es - second_es < MISTAKE_DROP:
        return "neither"
    if is_lichess_eval_game:
        post_es = _eval_to_expected_score(post_move_cp, post_move_mate, mover_color)
        if post_es is not None and best_es - post_es > BEST_MOVE_DIVERGENCE_MAX_ES:
            return "neither"
    if maia_prob <= GEM_MAIA_MAX_PROB:
        return "gem"
    if maia_prob <= GREAT_MAIA_MAX_PROB:
        return "great"
    return "neither"


# ─── SQL twins of _eval_to_expected_score / classify_best_move (FILT-01) ───────
#
# The Library "has gem" / "has great" filter (FILT-01) must decide gem/great
# tiers inside a correlated EXISTS (app/repositories/library_repository.py::
# best_move_exists_from_table), so the classification needs a SQLAlchemy Core
# expression twin of the two Python functions above. Board (classify_best_move,
# called in Python) and filter (these SQL twins) agree by construction because
# both read the SAME module constants (GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB,
# MISTAKE_DROP, MATE_CP_EQUIVALENT) and the same LICHESS_K sigmoid coefficient —
# never re-declared here (GEMS-07/D-03b: one retune surface).
#
# Must stay consistent with _eval_to_expected_score / classify_best_move (the
# Python counterparts, same module). If either side changes, update the other —
# same sync discipline as decided_lost_sql / is_decided_lost
# (app/repositories/library_repository.py).


def _es_sql(cp_col: Any, mate_col: Any, user_color_col: Any) -> ColumnElement[float | None]:
    """SQL twin of _eval_to_expected_score.

    Option-B mate mapping: a mate eval maps to ±MATE_CP_EQUIVALENT centipawns
    BEFORE the shared Lichess-K sigmoid (mate takes priority over cp when both
    are present, matching the Python function's `if eval_mate is not None: ...
    elif eval_cp is not None: ...` branch order). NULL when both cols are NULL.
    """
    sign = case((user_color_col == "white", 1.0), else_=-1.0)
    mate_cp_equiv = case(
        (mate_col > 0, float(MATE_CP_EQUIVALENT)), else_=-float(MATE_CP_EQUIVALENT)
    )
    return case(
        (mate_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * mate_cp_equiv))),
        (cp_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * cp_col))),
        else_=literal(None),
    )


def best_move_tier_sql(
    maia_prob_col: Any,
    best_cp_col: Any,
    best_mate_col: Any,
    second_cp_col: Any,
    second_mate_col: Any,
    user_color_col: Any,
    post_move_cp_col: Any = None,
    post_move_mate_col: Any = None,
    is_lichess_eval_col: Any = None,
) -> ColumnElement[str | None]:
    """SQL twin of classify_best_move — returns 'gem' / 'great' / NULL.

    NULL is the SQL equivalent of the Python function's "neither" string (the
    EXISTS filter only ever tests membership in {'gem', 'great'}, so a bare
    NULL/'neither' distinction would be meaningless here).

    C2 (only-good-move) gate: NULL when either expected score is missing, or
    when the best-second margin is below MISTAKE_DROP. Then the imported-eval
    divergence guard (Quick 260717-gmg, mirrors classify_best_move): when
    is_lichess_eval_col is true and the post-move expected score is present and
    our best-move ES exceeds it by more than BEST_MOVE_DIVERGENCE_MAX_ES, NULL.
    Given both, C1 (hard-to-find): maia_prob_col <= GEM_MAIA_MAX_PROB -> 'gem';
    <= GREAT_MAIA_MAX_PROB -> 'great'; otherwise NULL. Both ceilings are inclusive
    (<=), matching classify_best_move exactly.

    The three post-move params default to None: when the caller omits them the
    guard is inert (no cols to read), so the classifier behaves exactly as before.
    """
    best_es = _es_sql(best_cp_col, best_mate_col, user_color_col)
    second_es = _es_sql(second_cp_col, second_mate_col, user_color_col)
    branches: list[Any] = [
        (best_es.is_(None), literal(None)),
        (second_es.is_(None), literal(None)),
        ((best_es - second_es) < MISTAKE_DROP, literal(None)),
    ]
    if is_lichess_eval_col is not None and post_move_cp_col is not None:
        post_es = _es_sql(post_move_cp_col, post_move_mate_col, user_color_col)
        branches.append(
            (
                and_(
                    is_lichess_eval_col,
                    post_es.isnot(None),
                    (best_es - post_es) > BEST_MOVE_DIVERGENCE_MAX_ES,
                ),
                literal(None),
            )
        )
    branches.append((maia_prob_col <= GEM_MAIA_MAX_PROB, literal("gem")))
    branches.append((maia_prob_col <= GREAT_MAIA_MAX_PROB, literal("great")))
    return case(*branches, else_=literal(None))
