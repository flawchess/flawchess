"""Session composition for the blunder-check drill (SEED-261108-dk0, Phases 249 and 250).

`compose_windows` draws one `SlotPlan` per session slot (250 D-12, D-16): a red herring, an own
blunder or a foreign blunder at one third each, with a herring's origin split own / foreign like
the blunders. It then fills the own slots from the user's unserved fully evaluated games, converts
every own slot own supply cannot fill into a foreign slot (D-15, same code path for a user with no
analysed games), and fills the foreign slots from other non-guest users' games whose mover's
pinned Elo sits within FOREIGN_RATING_BAND of the user's level (D-13). A foreign slot the band
cannot fill takes the games closest to the level instead, with no cap on the distance, and a slot
still empty after that goes back to the user's own games (Phase 251 UAT, replacing D-13's "no
widening"), so a session is short only when nothing is left to serve. Every pick becomes a
`NewWindow` carrying a self-sufficient snapshot (start FEN + UCI moves) so a later delete of a
foreign game never breaks the session (249 D-15). At most one window per game per session.

Mechanics (Claude's discretion, recorded in the plan): on the fly per session start, game-first,
Python judgements on the classifier's own pass. Queries per start are bounded by MAX_OWN_BATCHES,
MAX_FOREIGN_BATCHES, the two nearest-first picks and MAX_SHAPE_REDRAWS (redraws reuse loaded
batches).

All awaits on the one AsyncSession are sequential (CLAUDE.md: never gather on a session).
"""

from __future__ import annotations

import io
import random
import statistics
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import Final, cast

import chess
import chess.pgn
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blunder_check import WindowCase
from app.models.game_position import GamePosition
from app.repositories import blunder_check_repository as repo
from app.repositories.blunder_check_repository import (
    CandidateGame,
    EloSourceRow,
    NewWindow,
)
from app.schemas.normalization import Platform, TimeControlBucket
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.blunder_check_candidates import (
    GameCandidates,
    PickCase,
    WindowPick,
    assign_windows,
    judge_game,
    lead_in_start,
    points_possible,
)
from app.services.blunder_check_rules import (
    BLUNDER_CHECK_SESSION_WINDOWS,
    FOREIGN_RATING_BAND,
    SlotOrigin,
    SlotPlan,
    WindowShape,
    draw_blunder_shape,
    draw_herring_shape,
    draw_slot_plan,
)
from app.services.normalization import is_correspondence_time_control
from app.services.train_scheduler import BlunderCheckLevel

# Own games loaded per batch (one random pick of fully evaluated games, then judged in Python).
OWN_BATCH_GAMES: int = 40
# Own batches per session start; the first batch already covers a typical session.
MAX_OWN_BATCHES: int = 3
# Foreign games loaded per batch.
FOREIGN_BATCH_GAMES: int = 40
# Foreign batches per session start inside the rating band (250 D-13); slots they leave empty go
# to the nearest-first picks below.
MAX_FOREIGN_BATCHES: int = 2
# TABLESAMPLE SYSTEM percentage for the foreign pick, so it never scans the whole games table.
FOREIGN_SAMPLE_PERCENT: float = 2.0
# The raw-rating prefilter is wider than the band because chess.com and lichess scales differ;
# the exact band (FOREIGN_RATING_BAND) is checked on the pinned Elo after loading.
FOREIGN_RAW_PREFILTER_MARGIN: int = 500
# Nearest-first fallback (Phase 251 UAT): the sampled games closest to the user's level that one
# pick keeps before the blunder probe and the random draw of FOREIGN_BATCH_GAMES.
FOREIGN_NEAREST_POOL_GAMES: int = 400
# The larger TABLESAMPLE percentage tried when the nearest-first pick at FOREIGN_SAMPLE_PERCENT
# comes back with less than a full batch (a small table, or a thin tail of the rating scale).
FOREIGN_WIDE_SAMPLE_PERCENT: float = 20.0
# Recent rated human games scanned to find the user's most-played time control (250 D-14).
USER_LEVEL_SCAN_GAMES: int = 200
# Newest games of that time control whose median pinned Elo is the user's level.
REFERENCE_ELO_GAMES: int = 50
# Level for a user with no rated games at all; mirrors the frontend FREE_PLAY_DEFAULT_ELO
# (frontend/src/hooks/useMaiaEloDefault.ts), the 250 CONTEXT default for such a user.
DEFAULT_USER_LEVEL_ELO: float = 1500.0
# Phase 251 D-17: a user without rated games (every guest) composes at the Elo of their stored
# blunder-check level. The middle level equals DEFAULT_USER_LEVEL_ELO on purpose; tune here only.
LEVEL_ELO: Final[Mapping[BlunderCheckLevel, float]] = {
    "beginner": 1000.0,
    "intermediate": 1500.0,
    "advanced": 2000.0,
}
# Rounds that redraw only the still-empty slots (re-using already loaded batches).
MAX_SHAPE_REDRAWS: int = 5

_PV_SEPARATOR: Final = " "

_WINDOW_CASE: Final[Mapping[PickCase, WindowCase]] = {
    "herring": WindowCase.HERRING,
    "allowed": WindowCase.ALLOWED,
    "pure_miss": WindowCase.PURE_MISS,
    "mixed": WindowCase.MIXED,
}


def new_session_rng() -> random.Random:
    """The single RNG factory for composition; tests monkeypatch it to a seeded instance."""
    return random.Random()


# ---------------------------------------------------------------------------
# Elo
# ---------------------------------------------------------------------------


def _pinned(
    *,
    raw_rating: int | None,
    platform: str,
    time_control_bucket: str | None,
    time_control_str: str | None,
) -> float | None:
    """The mover's pinned (lichess-blitz-equivalent) Elo, None when unrated."""
    if raw_rating is None:
        return None
    return pinned_elo_for_mover(
        raw_rating=raw_rating,
        platform=cast(Platform, platform),
        time_control_bucket=cast(TimeControlBucket | None, time_control_bucket),
        is_correspondence=is_correspondence_time_control(time_control_str),
    )


def mover_pinned_elo(game: CandidateGame) -> float | None:
    """The owner's pinned Elo at game time (mirrors scripts/blunder_check/sample.py `_game_elo`)."""
    raw = game.white_rating if game.user_color == "white" else game.black_rating
    return _pinned(
        raw_rating=raw,
        platform=game.platform,
        time_control_bucket=game.time_control_bucket,
        time_control_str=game.time_control_str,
    )


def _median_pinned(rows: Sequence[EloSourceRow]) -> float | None:
    """Median pinned Elo of the rows; None when no row has a pinned Elo."""
    elos = [
        elo
        for row in rows
        if (
            elo := _pinned(
                raw_rating=row.rating,
                platform=row.platform,
                time_control_bucket=row.time_control_bucket,
                time_control_str=row.time_control_str,
            )
        )
        is not None
    ]
    return statistics.median(elos) if elos else None


def level_fallback_elo(level: BlunderCheckLevel | None) -> float:
    """The Elo a user without rated games composes at: their stored level, else the 1500 default."""
    return DEFAULT_USER_LEVEL_ELO if level is None else LEVEL_ELO[level]


def user_level_elo(
    rows: Sequence[EloSourceRow], *, fallback: float = DEFAULT_USER_LEVEL_ELO
) -> float:
    """The user's level (250 D-14): median pinned Elo of the newest games in their most-played
    time control. `rows` are the user's rated human games, newest first.

    The bucket is the one with the most rows (a count tie goes to the bucket whose newest row comes
    first); correspondence rows and rows without a bucket never decide it. With no bucketed rows the
    level is the median over all rows. Without a pinned Elo in the rows (a guest or a user with no
    rated games) the level is `fallback`, the stored level's Elo (D-17); rated games always win.
    """
    bucketed = [
        row
        for row in rows
        if row.time_control_bucket is not None
        and not is_correspondence_time_control(row.time_control_str)
    ]
    chosen: Sequence[EloSourceRow] = rows
    if bucketed:
        counts = Counter(row.time_control_bucket for row in bucketed)
        # max() keeps the first maximal key, and Counter preserves first-seen (newest) order.
        top_bucket = max(counts, key=lambda bucket: counts[bucket])
        chosen = [row for row in bucketed if row.time_control_bucket == top_bucket][
            :REFERENCE_ELO_GAMES
        ]
    level = _median_pinned(chosen)
    return fallback if level is None else level


# ---------------------------------------------------------------------------
# PGN replay helpers (one python-chess parse each; failures are expected, not Sentry)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowSnapshot:
    """Self-sufficient window: start FEN plus the UCI moves from the lead-in start on."""

    start_fen: str
    move_ucis: str
    lead_in_plies: int
    # The move played just before `start_fen`, None at the game's first position.
    prior_uci: str | None


def _mainline(pgn: str) -> tuple[chess.Board, list[chess.Move]] | None:
    """Start board and mainline moves, None for an unparseable PGN."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return None
        return game.board(), list(game.mainline_moves())
    except ValueError, IndexError, AttributeError, UnicodeDecodeError:
        return None


def build_snapshot(pgn: str, first_ply: int, last_ply: int) -> WindowSnapshot | None:
    """Snapshot from the lead-in start through the reply after `last_ply` (when it exists).

    None when the PGN is unparseable or the window runs past the end of the game.
    """
    parsed = _mainline(pgn)
    if parsed is None:
        return None
    board, moves = parsed
    if last_ply >= len(moves):
        return None
    lead_start = lead_in_start(first_ply)
    for move in moves[:lead_start]:
        board.push(move)
    end = min(last_ply + 1, len(moves) - 1)
    return WindowSnapshot(
        start_fen=board.fen(),
        move_ucis=" ".join(move.uci() for move in moves[lead_start : end + 1]),
        lead_in_plies=first_ply - lead_start,
        prior_uci=moves[lead_start - 1].uci() if lead_start > 0 else None,
    )


def legal_key_plies(
    pgn: str, positions: Sequence[GamePosition], flaw_plies: AbstractSet[int]
) -> set[int]:
    """Flaw plies whose stored best_move is set and legal on the board before that ply."""
    parsed = _mainline(pgn)
    if parsed is None:
        return set()
    board, moves = parsed
    best_by_ply = {p.ply: p.best_move for p in positions if p.best_move}
    legal: set[int] = set()
    for ply, move in enumerate(moves):
        uci = best_by_ply.get(ply)
        if ply in flaw_plies and uci is not None and _is_legal_uci(board, uci):
            legal.add(ply)
        board.push(move)
    return legal


def _is_legal_uci(board: chess.Board, uci: str) -> bool:
    try:
        return chess.Move.from_uci(uci) in board.legal_moves
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Batches and pools
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Batch:
    """One judged game with what is needed to build its window row."""

    game: CandidateGame
    positions: Sequence[GamePosition]
    candidates: GameCandidates
    is_own: bool
    mover_elo: float | None


@dataclass(frozen=True)
class _Reach:
    """How far from the user's level a foreign game's mover may be (pinned Elo)."""

    level: float
    max_distance: float

    def covers(self, elo: float | None) -> bool:
        return elo is not None and abs(elo - self.level) <= self.max_distance


@dataclass
class _Pool:
    """Loaded batches of one origin (own or foreign) plus every id already picked."""

    batches: dict[int, _Batch] = field(default_factory=dict)
    seen_ids: list[int] = field(default_factory=list)

    def candidates(self, reach: _Reach | None = None) -> list[GameCandidates]:
        """The judged games, limited to those within `reach` of a level when one is given."""
        return [
            batch.candidates
            for batch in self.batches.values()
            if reach is None or reach.covers(batch.mover_elo)
        ]


@dataclass(frozen=True)
class _Filled:
    pick: WindowPick
    batch: _Batch


async def _load_batch(
    session: AsyncSession,
    *,
    user_id: int,
    game_ids: Sequence[int],
    is_own: bool,
    cooled_pairs: Sequence[tuple[int, int]] = (),
) -> list[_Batch]:
    """Load and judge games (sequential awaits on the one session).

    A foreign game without a pinned Elo is dropped: its distance to the user's level is unknown.
    Every other foreign game is kept whatever its Elo; the band and the nearest-first fallback
    choose among the loaded games by `_Reach`.
    `cooled_pairs` (D-16) are the user's flaws served as puzzles inside the cooldown; they count
    as served for the Python judge, so such a blunder is never composed.
    """
    games = await repo.load_candidate_games(session, game_ids)
    ids = [game.game_id for game in games]
    positions = await repo.load_positions(session, ids)
    flaws = await repo.load_blunder_flaws(session, ids)
    served = await repo.served_for_games(
        session, user_id=user_id, game_ids=ids, cooled_pairs=cooled_pairs
    )
    batches: list[_Batch] = []
    for game in games:
        elo = mover_pinned_elo(game)
        if not is_own and elo is None:
            continue
        game_positions = positions.get(game.game_id, [])
        game_flaws = flaws.get(game.game_id, [])
        key_plies = legal_key_plies(game.pgn, game_positions, {f.ply for f in game_flaws})
        candidates = judge_game(
            game_id=game.game_id,
            user_is_white=game.user_color == "white",
            positions=game_positions,
            flaws=game_flaws,
            key_plies=key_plies,
            served_blunder_plies=served.served_blunder_plies.get(game.game_id, set()),
            served_ply_ranges=served.judged_ranges.get(game.game_id, []),
        )
        if candidates is not None:
            batches.append(_Batch(game, game_positions, candidates, is_own, elo))
    return batches


async def _load_into_pool(
    session: AsyncSession,
    pool: _Pool,
    *,
    user_id: int,
    game_ids: Sequence[int],
    is_own: bool,
    cooled_pairs: Sequence[tuple[int, int]] = (),
) -> None:
    pool.seen_ids.extend(game_ids)
    for batch in await _load_batch(
        session,
        user_id=user_id,
        game_ids=game_ids,
        is_own=is_own,
        cooled_pairs=cooled_pairs,
    ):
        pool.batches[batch.game.game_id] = batch


# ---------------------------------------------------------------------------
# Filling slots
# ---------------------------------------------------------------------------


def _fill_from_pool(
    empty: Mapping[int, WindowShape],
    pool: _Pool,
    filled: dict[int, _Filled],
    *,
    rng: random.Random,
    reach: _Reach | None = None,
) -> None:
    """Fill what the pool can for the still-empty slots; one window per game across the session.

    `reach` limits a foreign pool to the games close enough to the user's level.
    """
    used = {item.pick.game_id for item in filled.values()}
    for pick in assign_windows(empty, pool.candidates(reach), rng=rng, used_game_ids=used):
        filled[pick.slot] = _Filled(pick, pool.batches[pick.game_id])


def _empty_shapes(
    plans: Mapping[int, SlotPlan], filled: Mapping[int, _Filled], origin: SlotOrigin
) -> dict[int, WindowShape]:
    """Shapes of the still-empty slots of one origin."""
    return {
        slot: plan.shape
        for slot, plan in plans.items()
        if plan.origin == origin and slot not in filled
    }


def _wants_blunder(shape: WindowShape) -> bool:
    return shape.blunder_position is not None


# Picks one batch of candidate game ids: (session, require_facepalm, exclude_ids) -> ids.
_PickFn = Callable[[AsyncSession, bool, Sequence[int]], Awaitable[list[int]]]
# The nearest-first pick: (session, require_facepalm, exclude_ids, sample_percent) -> ids.
_NearestPickFn = Callable[[AsyncSession, bool, Sequence[int], float], Awaitable[list[int]]]


@dataclass(frozen=True)
class _Source:
    """Where the slots of one origin are filled from: the pick query and its limits."""

    origin: SlotOrigin
    max_rounds: int
    # Foreign only: the rating band around the user's level its slots are filled from first.
    band: _Reach | None
    pick: _PickFn
    # D-16: flaws served as puzzles inside the cross-mode cooldown (the user's own, never foreign).
    cooled_pairs: Sequence[tuple[int, int]] = ()
    # Foreign only: the games closest to the user's level, for slots the band cannot fill.
    pick_nearest: _NearestPickFn | None = None


def _own_source(user_id: int, cooled_pairs: Sequence[tuple[int, int]] = ()) -> _Source:
    async def pick(
        session: AsyncSession, require_facepalm: bool, exclude_ids: Sequence[int]
    ) -> list[int]:
        return await repo.pick_own_game_ids(
            session,
            user_id=user_id,
            limit=OWN_BATCH_GAMES,
            exclude_ids=exclude_ids,
            require_facepalm=require_facepalm,
            cooled_pairs=cooled_pairs,
        )

    return _Source("own", MAX_OWN_BATCHES, None, pick, cooled_pairs)


async def _foreign_source(
    session: AsyncSession, user_id: int, *, fallback_elo: float = DEFAULT_USER_LEVEL_ELO
) -> _Source:
    """Foreign games whose mover's pinned Elo is within FOREIGN_RATING_BAND of the user's level.

    250 D-13: rating only (no time-control match), one band. `pick_nearest` serves the slots the
    band leaves empty (Phase 251 UAT). The level is read once per session start (D-14). A user
    without rated games gets `fallback_elo` (D-17).
    """
    level = user_level_elo(
        await repo.recent_rated_games(session, user_id=user_id, limit=USER_LEVEL_SCAN_GAMES),
        fallback=fallback_elo,
    )
    raw_margin = FOREIGN_RATING_BAND + FOREIGN_RAW_PREFILTER_MARGIN

    async def pick(
        session: AsyncSession, require_facepalm: bool, exclude_ids: Sequence[int]
    ) -> list[int]:
        return await repo.pick_foreign_game_ids(
            session,
            user_id=user_id,
            raw_low=int(level - raw_margin),
            raw_high=int(level + raw_margin),
            limit=FOREIGN_BATCH_GAMES,
            exclude_ids=exclude_ids,
            sample_percent=FOREIGN_SAMPLE_PERCENT,
            require_facepalm=require_facepalm,
        )

    async def pick_nearest(
        session: AsyncSession,
        require_facepalm: bool,
        exclude_ids: Sequence[int],
        sample_percent: float,
    ) -> list[int]:
        return await repo.pick_nearest_foreign_game_ids(
            session,
            user_id=user_id,
            level=round(level),
            limit=FOREIGN_BATCH_GAMES,
            pool_size=FOREIGN_NEAREST_POOL_GAMES,
            exclude_ids=exclude_ids,
            sample_percent=sample_percent,
            require_facepalm=require_facepalm,
        )

    return _Source(
        "foreign",
        MAX_FOREIGN_BATCHES,
        _Reach(level, FOREIGN_RATING_BAND),
        pick,
        pick_nearest=pick_nearest,
    )


async def _fill_from_source(
    session: AsyncSession,
    *,
    user_id: int,
    source: _Source,
    plans: Mapping[int, SlotPlan],
    pool: _Pool,
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    """Load batches from one origin until its slots are full or the rounds run out.

    A round asks for games holding an unserved qualifying blunder while a blunder slot is still
    empty (`require_facepalm`); once such a pick comes back empty the origin has no blunder supply
    left and later rounds only serve the herring slots with plain picks.
    """
    blunders_exhausted = False
    for _ in range(source.max_rounds):
        empty = _empty_shapes(plans, filled, source.origin)
        want_blunder = any(_wants_blunder(shape) for shape in empty.values())
        want_herring = any(not _wants_blunder(shape) for shape in empty.values())
        require_facepalm = want_blunder and not blunders_exhausted
        if not (require_facepalm or want_herring):
            return
        ids = await source.pick(session, require_facepalm, pool.seen_ids)
        if not ids:
            if not require_facepalm:
                return
            blunders_exhausted = True
            continue
        await _load_into_pool(
            session,
            pool,
            user_id=user_id,
            game_ids=ids,
            is_own=source.origin == "own",
            cooled_pairs=source.cooled_pairs,
        )
        _fill_from_pool(
            _empty_shapes(plans, filled, source.origin), pool, filled, rng=rng, reach=source.band
        )


def _redraw_shape(shape: WindowShape, rng: random.Random) -> WindowShape:
    """A fresh shape of the same kind (blunder stays a blunder, herring stays a herring)."""
    return draw_blunder_shape(rng) if _wants_blunder(shape) else draw_herring_shape(rng)


def _redraw_and_refill(
    plans: dict[int, SlotPlan],
    origin: SlotOrigin,
    pool: _Pool,
    filled: dict[int, _Filled],
    *,
    rng: random.Random,
    reach: _Reach | None = None,
) -> None:
    """Redraw only the empty slots of one origin and retry its pool without new queries."""
    for _ in range(MAX_SHAPE_REDRAWS):
        empty = _empty_shapes(plans, filled, origin)
        if not empty:
            return
        for slot, shape in empty.items():
            plans[slot] = SlotPlan(origin, _redraw_shape(shape, rng))
        _fill_from_pool(_empty_shapes(plans, filled, origin), pool, filled, rng=rng, reach=reach)


async def _load_nearest_foreign(
    session: AsyncSession,
    *,
    user_id: int,
    source: _Source,
    plans: dict[int, SlotPlan],
    pool: _Pool,
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    """Load the games closest to the user's level for the foreign slots the band left empty.

    The first pick samples as much of the table as the band picks do; the wider sample is tried
    only when that pick came back short of a full batch (a small table or a thin tail of the
    rating scale), so the usual session start adds one query at most.
    """
    if source.pick_nearest is None:
        return
    for sample_percent in (FOREIGN_SAMPLE_PERCENT, FOREIGN_WIDE_SAMPLE_PERCENT):
        empty = _empty_shapes(plans, filled, "foreign")
        if not empty:
            return
        require_facepalm = any(_wants_blunder(shape) for shape in empty.values())
        ids = await source.pick_nearest(session, require_facepalm, pool.seen_ids, sample_percent)
        if ids:
            await _load_into_pool(session, pool, user_id=user_id, game_ids=ids, is_own=False)
            # In-band games the nearest pick happened to find still come first.
            _fill_from_pool(empty, pool, filled, rng=rng, reach=source.band)
            _redraw_and_refill(plans, "foreign", pool, filled, rng=rng, reach=source.band)
        if len(ids) >= FOREIGN_BATCH_GAMES:
            return


def _fill_nearest_first(
    plans: dict[int, SlotPlan],
    pool: _Pool,
    filled: dict[int, _Filled],
    *,
    band: _Reach,
    rng: random.Random,
) -> None:
    """Fill the empty foreign slots from the loaded games, the closest to the level first.

    The reach grows one band width at a time until the slots are full or the farthest loaded
    game is covered: there is no cap on the distance (Phase 251 UAT).
    """
    farthest = max(
        (
            abs(batch.mover_elo - band.level)
            for batch in pool.batches.values()
            if batch.mover_elo is not None
        ),
        default=0.0,
    )
    reach = band
    while reach.max_distance < farthest and _empty_shapes(plans, filled, "foreign"):
        reach = _Reach(band.level, reach.max_distance + band.max_distance)
        _fill_from_pool(_empty_shapes(plans, filled, "foreign"), pool, filled, rng=rng, reach=reach)
        _redraw_and_refill(plans, "foreign", pool, filled, rng=rng, reach=reach)


async def _fill_foreign_slots(
    session: AsyncSession,
    *,
    user_id: int,
    fallback_level_elo: float,
    plans: dict[int, SlotPlan],
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    """Fill the foreign slots: the rating band first, then the games closest to the level.

    Bug fix (Phase 251 UAT): the band was the only source, so a slot it could not fill was
    dropped and the session came up shorter than the size the user had set. The band picks take
    their batch from a raw-rating range several times wider than the band, so for a level at the
    edge of the rating scale, or on a small table, hardly any loaded game was in band.
    """
    source = await _foreign_source(session, user_id, fallback_elo=fallback_level_elo)
    pool = _Pool()
    await _fill_from_source(
        session, user_id=user_id, source=source, plans=plans, pool=pool, filled=filled, rng=rng
    )
    _redraw_and_refill(plans, "foreign", pool, filled, rng=rng, reach=source.band)
    if source.band is None or not _empty_shapes(plans, filled, "foreign"):
        return
    await _load_nearest_foreign(
        session, user_id=user_id, source=source, plans=plans, pool=pool, filled=filled, rng=rng
    )
    _fill_nearest_first(plans, pool, filled, band=source.band, rng=rng)


async def _refill_from_own(
    session: AsyncSession,
    *,
    user_id: int,
    source: _Source,
    plans: dict[int, SlotPlan],
    pool: _Pool,
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    """Last resort: foreign slots no foreign game could fill go to the user's own games."""
    for slot, shape in _empty_shapes(plans, filled, "foreign").items():
        plans[slot] = SlotPlan("own", shape)
    # The own games already loaded first: `_fill_from_source` only fills after a new batch.
    _fill_from_pool(_empty_shapes(plans, filled, "own"), pool, filled, rng=rng)
    await _fill_from_source(
        session, user_id=user_id, source=source, plans=plans, pool=pool, filled=filled, rng=rng
    )
    _redraw_and_refill(plans, "own", pool, filled, rng=rng)


def _convert_empty_own_to_foreign(
    plans: dict[int, SlotPlan], filled: Mapping[int, _Filled]
) -> None:
    """250 D-15 / D-16: own slots own supply could not fill become foreign slots, herrings included."""
    for slot in _empty_shapes(plans, filled, "own"):
        plans[slot] = SlotPlan("foreign", plans[slot].shape)


# ---------------------------------------------------------------------------
# Window rows
# ---------------------------------------------------------------------------


def _refutation_uci(positions: Sequence[GamePosition], blunder_ply: int) -> str | None:
    """The opponent's best reply after the blunder: best_move, else the first pv token (D-20)."""
    nxt = blunder_ply + 1
    if nxt >= len(positions):
        return None
    row = positions[nxt]
    if row.best_move:
        return row.best_move
    return row.pv.split(_PV_SEPARATOR)[0] if row.pv else None


def _new_window(position: int, item: _Filled) -> NewWindow | None:
    pick, batch = item.pick, item.batch
    snapshot = build_snapshot(batch.game.pgn, pick.first_ply, pick.judged_plies[-1])
    if snapshot is None:
        return None
    blunder_ply = pick.blunder_ply
    return NewWindow(
        position=position,
        game_id=batch.game.game_id,
        is_own=batch.is_own,
        window_length=pick.shape.length,
        blunder_position=pick.shape.blunder_position,
        first_ply=pick.first_ply,
        blunder_ply=blunder_ply,
        window_case=_WINDOW_CASE[pick.case],
        mover_elo=None if batch.mover_elo is None else round(batch.mover_elo),
        start_fen=snapshot.start_fen,
        move_ucis=snapshot.move_ucis,
        lead_in_plies=snapshot.lead_in_plies,
        prior_uci=snapshot.prior_uci,
        key_uci=None if blunder_ply is None else batch.positions[blunder_ply].best_move,
        refutation_uci=None
        if blunder_ply is None
        else _refutation_uci(batch.positions, blunder_ply),
        points_possible=points_possible(pick.shape),
    )


async def compose_windows(
    session: AsyncSession,
    *,
    user_id: int,
    rng: random.Random,
    count: int = BLUNDER_CHECK_SESSION_WINDOWS,
    fallback_level_elo: float = DEFAULT_USER_LEVEL_ELO,
    cooled_pairs: Sequence[tuple[int, int]] = (),
    start_position: int = 0,
) -> list[NewWindow]:
    """Compose up to `count` windows for the user (250 D-12..D-16).

    `count` is the user's `blunder_check_per_session` (Phase 251 D-04); the constant stays as
    the documented default for direct callers. `fallback_level_elo` is the stored level's Elo, used
    only when the user has no rated games (D-17). `cooled_pairs` are the user's own flaws
    served as puzzles inside the cross-mode cooldown (D-16): they are not composed as own blunders.
    `start_position` numbers the first returned window (the extension of an open session, D-06,
    continues after its existing windows); positions stay contiguous from there.
    """
    plans = {slot: draw_slot_plan(rng) for slot in range(count)}
    own = _Pool()
    own_source = _own_source(user_id, cooled_pairs)
    filled: dict[int, _Filled] = {}
    await _fill_from_source(
        session, user_id=user_id, source=own_source, plans=plans, pool=own, filled=filled, rng=rng
    )
    _redraw_and_refill(plans, "own", own, filled, rng=rng)
    _convert_empty_own_to_foreign(plans, filled)
    if _empty_shapes(plans, filled, "foreign"):
        await _fill_foreign_slots(
            session,
            user_id=user_id,
            fallback_level_elo=fallback_level_elo,
            plans=plans,
            filled=filled,
            rng=rng,
        )
    if _empty_shapes(plans, filled, "foreign"):
        await _refill_from_own(
            session,
            user_id=user_id,
            source=own_source,
            plans=plans,
            pool=own,
            filled=filled,
            rng=rng,
        )
    # Positions are renumbered contiguously from `start_position` so a short session keeps a
    # gap-free sequence.
    windows: list[NewWindow] = []
    for _, item in sorted(filled.items()):
        window = _new_window(start_position + len(windows), item)
        if window is not None:
            windows.append(window)
    return windows
