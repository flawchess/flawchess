"""maia_flaw_stats.py — pure per-flaw Maia stats derivation (Phase 247, no I/O).

Given one position's full Maia policy (UCI -> probability over ALL legal moves) and the
played UCI, derive the one base value stored on game_flaws that the facepalm score still
reads: ``maia_played_prob``, the played move's probability. (Phase 250 D-11 dropped the
rank, best, second, top and effective-moves values and the Phase 248 refutation pair.)

``reply_spread`` is the Phase 250 effective number of replies one ply after a blunder.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal, TypedDict

# Entropy is measured in bits, so effective moves = 2 ** H.
_ENTROPY_LOG_BASE: float = 2.0

MaiaReason = Literal[
    "played_not_legal",
    "no_rating",
    "pgn_unparseable",
    "invalid_root",
    "ply_beyond_mainline",
    "fen_mismatch",
    "no_legal_reply",
]


class MaiaFlawStats(TypedDict):
    maia_played_prob: float | None


def null_maia_stats() -> MaiaFlawStats:
    """The base value None (a row Maia could not score)."""
    return MaiaFlawStats(maia_played_prob=None)


class FacepalmStats(TypedDict):
    """The eight Phase 250 facepalm columns of one game_flaws row (D-05)."""

    maia_reply_spread: float | None
    line_loss_1: int | None
    line_loss_3: int | None
    line_loss_5: int | None
    line_loss_7: int | None
    line_loss_9: int | None
    line_mate_ply: int | None
    facepalm_score: float | None


def null_facepalm_stats() -> FacepalmStats:
    """All eight Phase 250 values None (out of scope or not scorable).

    Written for every flaw that is not a scorable user blunder, so a full re-score also
    clears a stale value on a row since downgraded from blunder (D-06, D-08 precedent).
    """
    return FacepalmStats(
        maia_reply_spread=None,
        line_loss_1=None,
        line_loss_3=None,
        line_loss_5=None,
        line_loss_7=None,
        line_loss_9=None,
        line_mate_ply=None,
        facepalm_score=None,
    )


def _effective_moves(probs: Mapping[str, float]) -> float:
    """2 ** (Shannon entropy in bits over all legal moves)."""
    entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)
    return float(_ENTROPY_LOG_BASE**entropy_bits)


def reply_spread(probs: Mapping[str, float]) -> float:
    """Effective number of replies in `probs` (250 D-01): 2 ** Shannon entropy in bits.

    `probs` is Maia's full policy over ALL legal moves one ply after the blunder (the
    opponent to move) at the blunderer's pinned Elo, with no truncation. This is the
    Phase 247 effective-moves formula applied one ply later; the go-forward hook, the
    backfill and the score fit all call this one implementation. A policy uniform over k
    moves gives exactly k.
    """
    return _effective_moves(probs)


def compute_maia_flaw_stats(
    probs: Mapping[str, float],
    *,
    played_uci: str,
) -> tuple[MaiaFlawStats | None, list[MaiaReason]]:
    """Derive the base stat (the played move's probability) from one full policy (no I/O).

    Returns (None, ["played_not_legal"]) for an empty policy or a played move absent
    from it.
    """
    if not probs or played_uci not in probs:
        return None, ["played_not_legal"]
    return MaiaFlawStats(maia_played_prob=float(probs[played_uci])), []
