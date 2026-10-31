"""Shared seed helpers for the "out of the opening" worse/better tests (Phase 243).

Non-test module (no ``test_`` prefix) so the builder parity test (plan 01) and the
later Stage B / read-path tests can seed the same edge cases. Every spec carries the
classification the SQL builder must produce (``expected_side``), so the expected
per-colour counts are derived from the spec list, never retyped in a test.

Classification contract (CONTEXT D-01, D-02):
  * First middlegame ply = min(ply) with phase = 1.
  * User-POV eval minus the colour baseline (+25 cp White, -25 cp Black); at or below
    -100 cp is worse (-1), at or above +100 cp is better (+1), otherwise even (0).
    For White that is eval_cp <= -75 / >= +125; for Black eval_cp >= +125 / <= -75.
  * A mate score counts by its user-POV sign (eval_mate = 0 is even).
  * A middlegame entry with both evals NULL is non-qualifying (``None``).
  * No middlegame ply: only resignation / checkmate / timeout with a decisive result
    count (loss = worse, win = better); everything else is non-qualifying.

Every non-guest Game insert must be cleaned up in a ``finally`` (``delete_users``):
the global eval lottery flakes when a test leaks a non-guest needs-engine game.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, replace
from functools import partial
from typing import Literal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.opening_out_repository import OpeningOutCounts
from app.schemas.normalization import Color
from app.services.canonical_slice_sql import TimeControlBucket

# ── Constants (CLAUDE.md no-magic-numbers) ───────────────────────────────────

SEED_TC: TimeControlBucket = "blitz"
OTHER_TC: TimeControlBucket = "rapid"
USER_ELO: int = 1500
OPP_ELO_IN_BAND: int = 1550  # within +-100
OPP_ELO_OUT_OF_BAND: int = 1650  # +150 -> excluded by the equal-footing filter
SUB_800_USER_ELO: int = 750
SUB_800_OPP_ELO: int = 760
RECENT_DAYS_AGO: int = 30
STALE_DAYS_AGO: int = 37 * 31  # > 36 months -> outside the recency window
BASE_TIME_SECONDS: int = 180
OPENING_PLY_COUNT: int = 10  # plies 0..9 are phase 0 (opening)
MG_ENTRY_PLY: int = 10  # first middlegame ply (phase 1)
MG_LATER_PLY: int = 11  # a later middlegame ply that must never change the class
HASH_STRIDE: int = 100
FULL_HASH_BASE: int = 1_000_000
WHITE_HASH_BASE: int = 2_000_000
BLACK_HASH_BASE: int = 3_000_000
OPENING_PHASE: int = 0
MIDDLEGAME_PHASE: int = 1

# Edge-case evals (centred cut is +-100 cp around a +-25 cp baseline).
WHITE_WORSE_CP: int = -75
WHITE_EVEN_LOW_CP: int = -74
WHITE_BETTER_CP: int = 125
WHITE_EVEN_HIGH_CP: int = 124
BLACK_WORSE_CP: int = 125
BLACK_EVEN_HIGH_CP: int = 124
BLACK_BETTER_CP: int = -75
BLACK_EVEN_LOW_CP: int = -74
FIRST_MG_BAD_CP: int = 300  # magnitude of the first MG ply eval in the "later ply" spec
LATER_MG_REVERSAL_CP: int = 900  # later-ply eval of the opposite sign, must be ignored
MATE_FOR_WHITE: int = 3
MATE_AGAINST_WHITE: int = -2

# Expected-side vocabulary: -1 worse, 0 even, 1 better, None non-qualifying.
Side = Literal[-1, 0, 1]
Outcome = Literal["win", "draw", "loss"]


@dataclass(frozen=True)
class OpeningSpec:
    """One seeded game. ``outcome`` is user-perspective; ``expected_side`` is the oracle."""

    user_color: Color
    has_mg_entry: bool
    mg_eval_cp: int | None = None
    mg_eval_mate: int | None = None
    later_mg_eval_cp: int | None = None
    termination: str | None = "resignation"
    outcome: Outcome = "win"
    expected_side: Side | None = None
    in_slice: bool = True
    tc: TimeControlBucket = SEED_TC
    days_ago: int = RECENT_DAYS_AGO
    user_rating: int = USER_ELO
    opp_rating: int = OPP_ELO_IN_BAND
    rated: bool = True
    is_computer_game: bool = False
    lichess_evals_at: bool = False
    full_evals_completed_at: bool = False
    evals_completed_at: bool = False


def result_str(outcome: Outcome, user_color: Color) -> str:
    """PGN result string for a user-perspective outcome."""
    if outcome == "draw":
        return "1/2-1/2"
    return "1-0" if (user_color == "white") == (outcome == "win") else "0-1"


def _sign(user_color: Color) -> int:
    """+1 for White, -1 for Black: maps a user-POV eval to the White-POV eval stored in the DB."""
    return 1 if user_color == "white" else -1


def main_block_specs(color: Color) -> list[OpeningSpec]:
    """One cycle of every D-01 / D-02 edge case for ``color`` (11 qualifying, 4 excluded).

    Eval values are given in the colour's own POV via the per-colour edge constants,
    so the Black block is the mirror of the White block, not a copy.
    """
    white = color == "white"
    worse_cp = WHITE_WORSE_CP if white else BLACK_WORSE_CP
    even_a_cp = WHITE_EVEN_LOW_CP if white else BLACK_EVEN_HIGH_CP
    better_cp = WHITE_BETTER_CP if white else BLACK_BETTER_CP
    even_b_cp = WHITE_EVEN_HIGH_CP if white else BLACK_EVEN_LOW_CP
    sign = _sign(color)
    # Mate scores: a mate FOR the user is positive for White, negative for Black.
    mate_for_user = MATE_FOR_WHITE * sign
    mate_against_user = MATE_AGAINST_WHITE * sign

    mg = partial(OpeningSpec, user_color=color, has_mg_entry=True)
    early = partial(OpeningSpec, user_color=color, has_mg_entry=False)

    return [
        mg(mg_eval_cp=worse_cp, expected_side=-1),
        mg(mg_eval_cp=even_a_cp, expected_side=0),
        mg(mg_eval_cp=better_cp, expected_side=1),
        mg(mg_eval_cp=even_b_cp, expected_side=0),
        mg(mg_eval_mate=mate_for_user, expected_side=1),
        mg(mg_eval_mate=mate_against_user, expected_side=-1),
        mg(mg_eval_mate=0, expected_side=0),
        mg(expected_side=None),  # MG entry with both evals NULL
        # First MG ply bad for the user, a later MG ply hugely good: the first one wins.
        mg(
            mg_eval_cp=-FIRST_MG_BAD_CP * sign,
            later_mg_eval_cp=LATER_MG_REVERSAL_CP * sign,
            expected_side=-1,
        ),
        early(termination="resignation", outcome="loss", expected_side=-1),
        early(termination="checkmate", outcome="win", expected_side=1),
        early(termination="timeout", outcome="loss", expected_side=-1),
        early(termination="draw", outcome="draw", expected_side=None),
        early(termination="abandoned", outcome="loss", expected_side=None),
        early(termination="unknown", outcome="win", expected_side=None),
    ]


def simple_even_specs(color: Color, n: int) -> list[OpeningSpec]:
    """``n`` qualifying "even" games (eval 0) for ``color``; used for floor-boundary seeds."""
    return [
        OpeningSpec(user_color=color, has_mg_entry=True, mg_eval_cp=0, expected_side=0)
        for _ in range(n)
    ]


def out_of_slice_specs() -> list[OpeningSpec]:
    """Games that fail the canonical slice; each is a clear "worse" so a leak is visible."""
    worse = OpeningSpec(
        user_color="white", has_mg_entry=True, mg_eval_cp=WHITE_WORSE_CP, in_slice=False
    )
    return [
        replace(worse, days_ago=STALE_DAYS_AGO),  # 37 months old
        replace(worse, opp_rating=OPP_ELO_OUT_OF_BAND),  # opponent +150 Elo
        replace(worse, rated=False),
        replace(worse, is_computer_game=True),
        replace(worse, tc=OTHER_TC),  # a different time control
        replace(worse, user_rating=SUB_800_USER_ELO, opp_rating=SUB_800_OPP_ELO),  # sub-800
    ]


def with_eval_source(
    specs: list[OpeningSpec],
    *,
    lichess_evals_at: bool = False,
    full_evals_completed_at: bool = False,
    evals_completed_at: bool = False,
) -> list[OpeningSpec]:
    """Return ``specs`` with the three eval-source completion flags set on every spec."""
    return [
        replace(
            s,
            lichess_evals_at=lichess_evals_at,
            full_evals_completed_at=full_evals_completed_at,
            evals_completed_at=evals_completed_at,
        )
        for s in specs
    ]


def expected_counts(
    specs: list[OpeningSpec], *, tc: TimeControlBucket = SEED_TC
) -> dict[Color, OpeningOutCounts]:
    """Per-colour counts derived from the in-slice specs' ``expected_side``.

    A colour with in-slice games but no qualifying one appears with ``n_games = 0``,
    exactly like the builder's ``GROUP BY`` over ``count(side)``.
    """
    totals: dict[Color, list[int]] = {}
    for s in specs:
        if not s.in_slice or s.tc != tc:
            continue
        n, worse, better = totals.setdefault(s.user_color, [0, 0, 0])
        if s.expected_side is None:
            continue
        totals[s.user_color] = [
            n + 1,
            worse + (s.expected_side == -1),
            better + (s.expected_side == 1),
        ]
    return {
        c: OpeningOutCounts(n_games=v[0], worse_n=v[1], better_n=v[2]) for c, v in totals.items()
    }


def _make_game(
    user_id: int, tag: str, idx: int, spec: OpeningSpec, base: datetime.datetime
) -> Game:
    if spec.user_color == "white":
        white_rating, black_rating = spec.user_rating, spec.opp_rating
        white_username, black_username = "me", "opp"
    else:
        white_rating, black_rating = spec.opp_rating, spec.user_rating
        white_username, black_username = "opp", "me"
    now = datetime.datetime.now(datetime.timezone.utc)
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=f"openingout-{tag}-{user_id}-{idx}",
        pgn="1. e4 e5 *",
        result=result_str(spec.outcome, spec.user_color),
        user_color=spec.user_color,
        termination=spec.termination,
        time_control_str=f"{BASE_TIME_SECONDS}+0",
        time_control_bucket=spec.tc,
        time_control_seconds=BASE_TIME_SECONDS,
        base_time_seconds=BASE_TIME_SECONDS,
        rated=spec.rated,
        is_computer_game=spec.is_computer_game,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_rating,
        black_rating=black_rating,
        lichess_evals_at=now if spec.lichess_evals_at else None,
        full_evals_completed_at=now if spec.full_evals_completed_at else None,
        evals_completed_at=now if spec.evals_completed_at else None,
    )
    game.played_at = base - datetime.timedelta(days=spec.days_ago, minutes=idx)
    return game


def _position(
    user_id: int, game_id: int, ply: int, phase: int, **evals: int | None
) -> GamePosition:
    return GamePosition(
        game_id=game_id,
        user_id=user_id,
        ply=ply,
        full_hash=FULL_HASH_BASE + game_id * HASH_STRIDE + ply,
        white_hash=WHITE_HASH_BASE + game_id * HASH_STRIDE + ply,
        black_hash=BLACK_HASH_BASE + game_id * HASH_STRIDE + ply,
        phase=phase,
        **evals,
    )


def _positions_for(user_id: int, game_id: int, spec: OpeningSpec) -> list[GamePosition]:
    """Plies 0-9 are phase 0; a spec with an MG entry adds ply 10 (spec evals) and ply 11."""
    rows = [_position(user_id, game_id, ply, OPENING_PHASE) for ply in range(OPENING_PLY_COUNT)]
    if spec.has_mg_entry:
        rows.append(
            _position(
                user_id,
                game_id,
                MG_ENTRY_PLY,
                MIDDLEGAME_PHASE,
                eval_cp=spec.mg_eval_cp,
                eval_mate=spec.mg_eval_mate,
            )
        )
        rows.append(
            _position(
                user_id, game_id, MG_LATER_PLY, MIDDLEGAME_PHASE, eval_cp=spec.later_mg_eval_cp
            )
        )
    return rows


async def seed_opening_specs(
    session_maker: async_sessionmaker, user_id: int, specs: list[OpeningSpec], tag: str
) -> None:
    """Insert one Game (plus its positions) per spec for ``user_id``."""
    base = datetime.datetime.now(datetime.timezone.utc)
    async with session_maker() as session:
        for idx, spec in enumerate(specs):
            game = _make_game(user_id, tag, idx, spec, base)
            session.add(game)
            await session.flush()
            session.add_all(_positions_for(user_id, game.id, spec))
        await session.commit()


async def create_seed_user(session_maker: async_sessionmaker, *, tag: str) -> int:
    """Create a non-guest user with a unique email and lichess username; return its id."""
    unique = uuid.uuid4().hex
    async with session_maker() as session:
        user = User(
            email=f"opening-out-{tag}-{unique}@example.com",
            hashed_password="x",
            lichess_username=f"opening-out-{tag}-{unique}",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def delete_users(session_maker: async_sessionmaker, user_ids: list[int]) -> None:
    """Delete the users (CASCADE removes their games and positions)."""
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.commit()
