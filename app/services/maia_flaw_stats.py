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
    # Phase 254 D-08: the best move is unknown (no pv and no best_move at the flaw ply) or is not
    # in Maia's policy, so maia_best_prob stays NULL; the row is still scored on the loss alone.
    "best_move_missing",
]


class MaiaFlawStats(TypedDict):
    maia_played_prob: float | None


def null_maia_stats() -> MaiaFlawStats:
    """The base value None (a row Maia could not score)."""
    return MaiaFlawStats(maia_played_prob=None)


class FacepalmStats(TypedDict):
    """The facepalm FACT columns of one game_flaws row (no stored score, 254 D-02): the reply
    spread, the played line's mate ply, the signed material arrays and the best line's mate ply
    (D-09). The score is computed at query time from these facts and the pre-blunder inputs."""

    maia_reply_spread: float | None
    line_mate_ply: int | None
    # Phase 254 D-09: signed 9-slot material of the played / best line (None when every slot is
    # None) and the ply after which the best line mates the opponent (0 = the best move mates).
    played_line_material: list[int | None] | None
    best_line_material: list[int | None] | None
    best_line_mate_ply: int | None


def null_facepalm_stats() -> FacepalmStats:
    """All facepalm values None (out of scope or not scorable).

    Written for every flaw that is not a scorable user blunder, so a full re-score also
    clears a stale value on a row since downgraded from blunder (D-06, D-08 precedent).
    """
    return FacepalmStats(
        maia_reply_spread=None,
        line_mate_ply=None,
        played_line_material=None,
        best_line_material=None,
        best_line_mate_ply=None,
    )


class MaiaPreStats(TypedDict):
    """The two Phase 254 pre-blunder Maia inputs of one game_flaws row (D-08)."""

    maia_best_prob: float | None
    maia_pre_spread: float | None


def null_maia_pre_stats() -> MaiaPreStats:
    """Both pre-blunder inputs None (out of scope, not scorable, or not computed in this mode)."""
    return MaiaPreStats(maia_best_prob=None, maia_pre_spread=None)


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


def pre_blunder_spread(probs: Mapping[str, float]) -> float:
    """Effective number of moves in `probs` at the PRE-blunder position (254 D-08).

    `probs` is Maia's full policy at the decision position (the blunderer to move) at the
    blunderer's pinned Elo, the same call that yields ``maia_played_prob``. Same formula as
    `reply_spread` (the Phase 247 effective-moves formula), applied to the position the blunder
    was played from: a policy uniform over k moves gives exactly k.
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
