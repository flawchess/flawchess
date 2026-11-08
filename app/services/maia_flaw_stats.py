"""maia_flaw_stats.py — pure per-flaw Maia stats derivation (Phase 247, no I/O).

Given one position's full Maia policy (UCI -> probability over ALL legal moves) and
the played / best / second UCIs, derive the eight D-01 values stored on game_flaws:

- ``maia_played_prob`` / ``maia_played_rank``: the played move's probability and rank.
- ``maia_best_prob`` / ``maia_best_rank``: same for the engine-best move.
- ``maia_second_prob`` / ``maia_second_rank``: same for the engine's second-best move.
- ``maia_top_prob``: probability of Maia's own top move.
- ``maia_effective_moves``: 2**H with H the Shannon entropy in bits over all legal
  moves (a policy uniform over k moves gives exactly k).

Rank definition: ``RANK_BASE + count of legal moves with STRICTLY higher probability``.
Maia's top move has rank 1, equal-probability moves share a rank, and the move just
below a tied pair gets rank 3.

D-15: remote workers compute best_move and second_move in separate searches, so the
second move can collide with the best move. In that case (or when it is missing or
illegal) only the second pair goes None; played / top / effective stay set.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal, TypedDict

# Rank of the move with no strictly-higher-probability competitor.
RANK_BASE: int = 1

# Entropy is measured in bits, so effective moves = 2 ** H.
_ENTROPY_LOG_BASE: float = 2.0

# Policy size at which there is only one legal move (second move is meaningless).
_SINGLE_LEGAL_MOVE_COUNT: int = 1

MaiaReason = Literal[
    "played_not_legal",
    "no_rating",
    "pgn_unparseable",
    "invalid_root",
    "ply_beyond_mainline",
    "fen_mismatch",
    "best_missing",
    "best_not_legal",
    "second_missing",
    "second_not_legal",
    "second_equals_best",
    "single_legal_move",
]


class MaiaFlawStats(TypedDict):
    maia_played_prob: float | None
    maia_played_rank: int | None
    maia_best_prob: float | None
    maia_best_rank: int | None
    maia_second_prob: float | None
    maia_second_rank: int | None
    maia_top_prob: float | None
    maia_effective_moves: float | None


def null_maia_stats() -> MaiaFlawStats:
    """All eight D-01 values None (a row Maia could not score)."""
    return MaiaFlawStats(
        maia_played_prob=None,
        maia_played_rank=None,
        maia_best_prob=None,
        maia_best_rank=None,
        maia_second_prob=None,
        maia_second_rank=None,
        maia_top_prob=None,
        maia_effective_moves=None,
    )


def _rank(probs: Mapping[str, float], uci: str) -> int:
    """RANK_BASE + number of legal moves strictly more probable than `uci`."""
    own = probs[uci]
    return RANK_BASE + sum(1 for p in probs.values() if p > own)


def _effective_moves(probs: Mapping[str, float]) -> float:
    """2 ** (Shannon entropy in bits over all legal moves)."""
    entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)
    return float(_ENTROPY_LOG_BASE**entropy_bits)


def _best_reason(probs: Mapping[str, float], best_uci: str | None) -> MaiaReason | None:
    if best_uci is None:
        return "best_missing"
    if best_uci not in probs:
        return "best_not_legal"
    return None


def _second_reason(
    probs: Mapping[str, float], best_uci: str | None, second_uci: str | None
) -> MaiaReason | None:
    if len(probs) == _SINGLE_LEGAL_MOVE_COUNT:
        return "single_legal_move"
    if not second_uci:
        return "second_missing"
    if second_uci == best_uci:
        return "second_equals_best"
    if second_uci not in probs:
        return "second_not_legal"
    return None


def compute_maia_flaw_stats(
    probs: Mapping[str, float],
    *,
    played_uci: str,
    best_uci: str | None,
    second_uci: str | None,
) -> tuple[MaiaFlawStats | None, list[MaiaReason]]:
    """Derive the eight D-01 stats from one full policy (no I/O).

    Returns (None, ["played_not_legal"]) for an empty policy or a played move absent
    from it. Otherwise returns the stats with the best pair and/or second pair None
    (plus the matching reason) when those moves are missing, illegal, or (second
    only) equal to best or the only legal move.
    """
    if not probs or played_uci not in probs:
        return None, ["played_not_legal"]

    reasons: list[MaiaReason] = []
    stats = null_maia_stats()
    stats["maia_played_prob"] = float(probs[played_uci])
    stats["maia_played_rank"] = int(_rank(probs, played_uci))
    stats["maia_top_prob"] = float(max(probs.values()))
    stats["maia_effective_moves"] = _effective_moves(probs)

    best_reason = _best_reason(probs, best_uci)
    if best_reason is not None:
        reasons.append(best_reason)
    elif best_uci is not None:
        stats["maia_best_prob"] = float(probs[best_uci])
        stats["maia_best_rank"] = int(_rank(probs, best_uci))

    second_reason = _second_reason(probs, best_uci, second_uci)
    if second_reason is not None:
        reasons.append(second_reason)
    elif second_uci:
        stats["maia_second_prob"] = float(probs[second_uci])
        stats["maia_second_rank"] = int(_rank(probs, second_uci))

    return stats, reasons
