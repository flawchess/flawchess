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

from typing import Literal

from app.schemas.normalization import Platform, TimeControlBucket
from app.services.chesscom_to_lichess import normalize_to_lichess_blitz
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.flaws_service import INACCURACY_DROP, MATE_CP_EQUIVALENT, MISTAKE_DROP
from app.services.maia_encoding import clamp_to_ladder_bounds

# ─── Classification constants (GEMS-07) ────────────────────────────────────────

# Maia policy-probability ceilings, mirroring the frontend gemMove.ts semantics.
# A gem is "fewer than 1 in 5 rating-peers would play it" (GEM_MAIA_MAX_PROB); a
# great move is the (0.20, 0.50] band (ROADMAP SC5). Both are flat cutoffs (D-08
# defers any per-ELO iso-rarity curve). Named constants — no magic numbers.
GEM_MAIA_MAX_PROB: float = 0.20
GREAT_MAIA_MAX_PROB: float = 0.50

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
) -> BestMoveTier:
    """Classify a stored best-move candidate as gem / great / neither, PURELY from
    the stored maia_prob + cp margin and module constants (GEMS-07): no DB, no
    engine, no re-inference. A threshold retune reclassifies the corpus for free.

    C2 (only-good-move): the best move must beat the runner-up by >= MISTAKE_DROP
    in mover-POV expected score, else "neither". Given C2, C1 (hard-to-find):
    maia_prob <= GEM_MAIA_MAX_PROB -> "gem"; <= GREAT_MAIA_MAX_PROB -> "great";
    otherwise "neither".
    """
    best_es = _eval_to_expected_score(best_cp, best_mate, mover_color)
    second_es = _eval_to_expected_score(second_cp, second_mate, mover_color)
    if best_es is None or second_es is None:
        return "neither"
    if best_es - second_es < MISTAKE_DROP:
        return "neither"
    if maia_prob <= GEM_MAIA_MAX_PROB:
        return "gem"
    if maia_prob <= GREAT_MAIA_MAX_PROB:
        return "great"
    return "neither"
