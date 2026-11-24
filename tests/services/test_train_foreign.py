"""Pure tests of the Phase 263 foreign-blunder pick and draw sizing (no database).

`pick_foreign_candidates` is the only decision-maker between the draw statement's rows and the
session: band membership (D-05), the seeded random order (D-14), the absence of any time-control
or facepalm input (D-15), the served-position and one-per-game rules (D-17) and the first-session
sharp preference (D-16). Every test builds `ForeignCandidate` rows by hand and passes a seeded
`random.Random`, so the outcomes are deterministic.

The statement-level rules (guests, the solver's own games, the six pool predicates) are in
`tests/repositories/test_train_foreign.py`.
"""

from __future__ import annotations

import random

from app.schemas.normalization import Platform, TimeControlBucket
from app.services.train_foreign import (
    FOREIGN_FILLER_MAX_GAMES,
    FOREIGN_FILLER_MIN_GAMES,
    ForeignCandidate,
    foreign_game_limit,
    foreign_raw_bounds,
    pick_foreign_candidates,
)
from tests.train_foreign_seed import FOREIGN_SHARP_PV_LINES, FOREIGN_SOFT_PV_LINES

# The owner's rating band around the solver's level, in pinned Elo (FOREIGN_RATING_BAND).
_LEVEL = 1500.0
_PICK_SEEDS = tuple(range(10))


def _candidate(
    game_id: int,
    *,
    ply: int = 2,
    rating: int | None = 1500,
    missed_pv_lines: list[object] | None = None,
    platform: Platform = "lichess",
    time_control_bucket: TimeControlBucket | None = "blitz",
    time_control_str: str | None = "300+0",
) -> ForeignCandidate:
    return ForeignCandidate(
        game_id=game_id,
        ply=ply,
        missed_pv_lines=list(missed_pv_lines or FOREIGN_SOFT_PV_LINES),
        platform=platform,
        time_control_bucket=time_control_bucket,
        time_control_str=time_control_str,
        owner_rating=rating,
    )


def _pick(
    candidates: list[ForeignCandidate],
    *,
    level: float = _LEVEL,
    served: set[tuple[int, int]] | None = None,
    exclude: set[int] | None = None,
    limit: int = 10,
    want_sharp: bool = False,
    seed: int = 0,
) -> list[ForeignCandidate]:
    return pick_foreign_candidates(
        candidates,
        level=level,
        served=served or set(),
        exclude_game_ids=exclude or set(),
        limit=limit,
        want_sharp=want_sharp,
        rng=random.Random(seed),
    )


def test_pick_prefers_in_band_then_nearest() -> None:
    # Pinned Elo of a lichess blitz rating is the rating itself; the band is +-150.
    candidates = [
        _candidate(1, rating=1900),
        _candidate(2, rating=1500),
        _candidate(3, rating=1700),
        _candidate(4, rating=1450),
        _candidate(5, rating=None),
    ]

    picked = _pick(candidates)

    assert {c.game_id for c in picked[:2]} == {2, 4}
    # Out of band, nearest first, no distance cap; a row without a rating is never drawn.
    assert [c.game_id for c in picked[2:]] == [3, 1]


def test_pick_skips_served_positions_and_excluded_games() -> None:
    candidates = [_candidate(1), _candidate(2), _candidate(3), _candidate(4, ply=6)]

    picked = _pick(candidates, served={(1, 2), (4, 4)}, exclude={2})

    # (1, 2) was served to this user before, game 2 holds a herring of the session, and
    # (4, 4) is not (4, 6): the position, not the game, is the served identity.
    assert sorted((c.game_id, c.ply) for c in picked) == [(3, 2), (4, 6)]


def test_pick_takes_one_puzzle_per_game() -> None:
    candidates = [_candidate(1, ply=2), _candidate(1, ply=4), _candidate(2, ply=2)]

    picked = _pick(candidates)

    assert sorted(c.game_id for c in picked) == [1, 2]


def test_pick_prefers_sharp_only_when_wanted() -> None:
    candidates = [_candidate(game_id) for game_id in range(1, 8)]
    # Out of band on purpose: the sharp preference outranks the band.
    candidates.append(_candidate(99, rating=1900, missed_pv_lines=list(FOREIGN_SHARP_PV_LINES)))

    wanted = [_pick(candidates, want_sharp=True, limit=1, seed=seed) for seed in _PICK_SEEDS]
    unwanted = [_pick(candidates, want_sharp=False, limit=1, seed=seed) for seed in _PICK_SEEDS]

    assert all([c.game_id for c in picked] == [99] for picked in wanted)
    # Without the flag the out-of-band sharp row is last, never first.
    assert all([c.game_id for c in picked] != [99] for picked in unwanted)


def test_pick_ignores_time_control() -> None:
    # A flawchess rating is already lichess-blitz-equivalent, so the time control is the only thing
    # that differs between the two variants (the rating-scale normalisation of the other platforms
    # is a comparability step, not a preference).
    def variant(bucket: TimeControlBucket, time_control_str: str) -> list[ForeignCandidate]:
        return [
            _candidate(
                game_id,
                platform="flawchess",
                time_control_bucket=bucket,
                time_control_str=time_control_str,
            )
            for game_id in range(1, 30)
        ]

    blitz = _pick(variant("blitz", "300+0"), limit=5, seed=3)
    daily = _pick(variant("classical", "1/86400"), limit=5, seed=3)
    bullet = _pick(variant("bullet", "60+0"), limit=5, seed=3)

    assert [c.game_id for c in blitz] == [c.game_id for c in daily] == [c.game_id for c in bullet]


def test_pick_is_seeded() -> None:
    candidates = [_candidate(game_id) for game_id in range(1, 30)]

    first = [c.game_id for c in _pick(candidates, limit=5, seed=7)]
    again = [c.game_id for c in _pick(list(reversed(candidates)), limit=5, seed=7)]
    others = {tuple(c.game_id for c in _pick(candidates, limit=5, seed=seed)) for seed in range(10)}

    assert first == again
    assert len(others) > 1


def test_foreign_game_limit_clamps() -> None:
    assert foreign_game_limit(1) == FOREIGN_FILLER_MIN_GAMES
    assert foreign_game_limit(100) == FOREIGN_FILLER_MAX_GAMES
    assert FOREIGN_FILLER_MIN_GAMES <= foreign_game_limit(10) <= FOREIGN_FILLER_MAX_GAMES


def test_foreign_raw_bounds() -> None:
    assert foreign_raw_bounds(1500.0) == (850, 2150)
