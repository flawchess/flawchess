"""Foreign-blunder filler: pure draw constants and the candidate pick (Phase 263).

When a Train session is short of the user's own material, the shortfall is filled with servable
blunders from other, non-guest users' games near the solver's rating (D-01, D-02). The SQL lives
in `app.services.train_pool` (`foreign_band_candidates_stmt` / `foreign_nearest_candidates_stmt`)
and the execution in `app.repositories.train_repository`; this module holds what needs no I/O:
the draw sizing constants, the escalation steps and `pick_foreign_candidates`.

Latency budget (the draw runs inside the compose request, prod `max_connections` is 50): the
band step at most 0.5 s cold on prod, both steps at most 1.5 s cold. The prod EXPLAIN at levels
1500 and 2600 runs before the squash-merge and again after the deploy (263-10 UAT list). Hard
cap: two statements per composition. The 20% nearest fallback blunder check uses measured 14.9 s
cold on prod and is deliberately not used here.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

from app.schemas.normalization import Platform, TimeControlBucket
from app.services.best_move_candidates import mover_color_for_ply, pinned_elo_for_mover
from app.services.blunder_check_rules import FOREIGN_RATING_BAND
from app.services.blunder_check_selection import FOREIGN_RAW_PREFILTER_MARGIN
from app.services.normalization import is_correspondence_time_control
from app.services.train_pool import MAX_ITEMS_PER_GAME_PER_SESSION, classify_puzzle_type

# TABLESAMPLE SYSTEM percentage of the band step. Prod 2026-11-23: 344 page reads, 91 ms cold,
# about 800 band games at level 1500.
FOREIGN_FILLER_SAMPLE_PERCENT: float = 0.1
# The larger percentage of the second (nearest-first) step only.
FOREIGN_FILLER_WIDE_SAMPLE_PERCENT: float = 0.4
# Sampled games kept per missing puzzle slot (not every game holds a servable blunder).
FOREIGN_FILLER_GAMES_PER_SLOT: int = 8
# Lower and upper bound of the sampled games one statement keeps.
FOREIGN_FILLER_MIN_GAMES: int = 40
FOREIGN_FILLER_MAX_GAMES: int = 200
# Extra candidates reconstructed beyond the shortfall, so a PGN that fails to replay does not
# leave the session short.
FOREIGN_FILLER_RECONSTRUCT_SLACK: int = 2


@dataclass(frozen=True)
class ForeignDrawStep:
    """One statement of the escalation: a sample percentage, band (False) or nearest-first (True)."""

    sample_percent: float
    nearest: bool


# Band step on the small sample, then a nearest-first step on a wider one (two statements max).
FOREIGN_FILLER_DRAW_STEPS: tuple[ForeignDrawStep, ...] = (
    ForeignDrawStep(sample_percent=FOREIGN_FILLER_SAMPLE_PERCENT, nearest=False),
    ForeignDrawStep(sample_percent=FOREIGN_FILLER_WIDE_SAMPLE_PERCENT, nearest=True),
)


@dataclass(frozen=True)
class ForeignCandidate:
    """One servable blunder of another user's game: only what the pick and the key need.

    No PGN, user id or username (D-21): the owner's identity never leaves the draw statement.
    `platform` and `time_control_bucket` are the project's Literal types, cast once where the row
    leaves SQL (`train_repository._draw_foreign_candidates`), never a bare `str`.
    """

    game_id: int
    ply: int
    missed_pv_lines: list[Any]
    platform: Platform
    time_control_bucket: TimeControlBucket | None
    time_control_str: str | None
    owner_rating: int | None


def foreign_game_limit(shortfall: int) -> int:
    """Sampled games one draw statement keeps for `shortfall` missing puzzles, clamped."""
    wanted = shortfall * FOREIGN_FILLER_GAMES_PER_SLOT
    return max(FOREIGN_FILLER_MIN_GAMES, min(FOREIGN_FILLER_MAX_GAMES, wanted))


def foreign_raw_bounds(level: float) -> tuple[int, int]:
    """Raw-rating prefilter range around `level`, wider than the band (platform scales differ).

    The exact band (`FOREIGN_RATING_BAND`) is checked on the pinned Elo in `pick_foreign_candidates`.
    """
    margin = FOREIGN_RATING_BAND + FOREIGN_RAW_PREFILTER_MARGIN
    return int(level - margin), int(level + margin)


def _pinned_elo(candidate: ForeignCandidate) -> float | None:
    """The owner's pinned Elo at game time, None when the game carries no rating."""
    if candidate.owner_rating is None:
        return None
    return pinned_elo_for_mover(
        raw_rating=candidate.owner_rating,
        platform=candidate.platform,
        time_control_bucket=candidate.time_control_bucket,
        is_correspondence=is_correspondence_time_control(candidate.time_control_str),
    )


def _is_sharp(candidate: ForeignCandidate) -> bool:
    return (
        classify_puzzle_type(candidate.missed_pv_lines, mover_color_for_ply(candidate.ply))
        == "sharp"
    )


def _rank_candidates(
    candidates: Sequence[ForeignCandidate],
    *,
    level: float,
    served: AbstractSet[tuple[int, int]],
    exclude_game_ids: AbstractSet[int],
    rng: random.Random,
) -> list[ForeignCandidate]:
    """In-band candidates shuffled first, then out-of-band ones nearest-first (no distance cap)."""
    in_band: list[ForeignCandidate] = []
    out_of_band: list[tuple[float, ForeignCandidate]] = []
    # Sorted first so the seeded shuffle depends on the candidate set, not the database row order.
    for candidate in sorted(candidates, key=lambda c: (c.game_id, c.ply)):
        if (candidate.game_id, candidate.ply) in served or candidate.game_id in exclude_game_ids:
            continue
        elo = _pinned_elo(candidate)
        if elo is None:
            continue
        distance = abs(elo - level)
        if distance <= FOREIGN_RATING_BAND:
            in_band.append(candidate)
        else:
            out_of_band.append((distance, candidate))
    rng.shuffle(in_band)
    out_of_band.sort(key=lambda pair: pair[0])
    return in_band + [candidate for _, candidate in out_of_band]


def pick_foreign_candidates(
    candidates: Sequence[ForeignCandidate],
    *,
    level: float,
    served: AbstractSet[tuple[int, int]],
    exclude_game_ids: AbstractSet[int],
    limit: int,
    want_sharp: bool,
    rng: random.Random,
) -> list[ForeignCandidate]:
    """Pick up to `limit` foreign blunders: a seeded random draw inside the rating band.

    Positions already served to the user (`served`, D-17) and excluded games are dropped, and so
    are rows without a pinned Elo. In-band rows (pinned Elo within `FOREIGN_RATING_BAND` of
    `level`) come first in seeded random order, out-of-band rows follow nearest-first with no
    distance cap (Phase 251 UAT). `want_sharp` moves the first sharp candidate to the front (D-16).
    At most `MAX_ITEMS_PER_GAME_PER_SESSION` puzzles per game (D-17). No time-control and no
    facepalm input (D-14, D-15).
    """
    ranked = _rank_candidates(
        candidates, level=level, served=served, exclude_game_ids=exclude_game_ids, rng=rng
    )
    if want_sharp:
        sharp_index = next((i for i, c in enumerate(ranked) if _is_sharp(c)), None)
        if sharp_index is not None:
            ranked.insert(0, ranked.pop(sharp_index))
    picked: list[ForeignCandidate] = []
    per_game: dict[int, int] = {}
    for candidate in ranked:
        if len(picked) >= limit:
            break
        if per_game.get(candidate.game_id, 0) >= MAX_ITEMS_PER_GAME_PER_SESSION:
            continue
        per_game[candidate.game_id] = per_game.get(candidate.game_id, 0) + 1
        picked.append(candidate)
    return picked
