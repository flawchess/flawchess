"""Session composition for the blunder-check drill (SEED-261108-dk0, Phases 249 and 250).

`compose_windows` draws one `SlotPlan` per session slot (250 D-12, D-16): a red herring, an own
blunder or a foreign blunder at one third each, with a herring's origin split own / foreign like
the blunders. It then fills the own slots from the user's unserved fully evaluated games, converts
every own slot own supply cannot fill into a foreign slot (D-15, same code path for a user with no
analysed games), and fills the foreign slots from other non-guest users' games whose mover's
pinned Elo sits within FOREIGN_RATING_BAND of the user's level (D-13). Every pick becomes a
`NewWindow` carrying a self-sufficient snapshot (start FEN + UCI moves) so a later delete of a
foreign game never breaks the session (249 D-15). At most one window per game per session.

Mechanics (Claude's discretion, recorded in the plan): on the fly per session start, game-first,
Python judgements on the classifier's own pass. Queries per start are bounded by MAX_OWN_BATCHES,
MAX_FOREIGN_BATCHES and MAX_SHAPE_REDRAWS (redraws reuse loaded batches).

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

# Own games loaded per batch (one random pick of fully evaluated games, then judged in Python).
OWN_BATCH_GAMES: int = 40
# Own batches per session start; the first batch already covers a typical session.
MAX_OWN_BATCHES: int = 3
# Foreign games loaded per batch.
FOREIGN_BATCH_GAMES: int = 40
# Foreign batches per session start (250 D-13: one rating band, no widening).
MAX_FOREIGN_BATCHES: int = 2
# TABLESAMPLE SYSTEM percentage for the foreign pick, so it never scans the whole games table.
FOREIGN_SAMPLE_PERCENT: float = 2.0
# The raw-rating prefilter is wider than the band because chess.com and lichess scales differ;
# the exact band (FOREIGN_RATING_BAND) is checked on the pinned Elo after loading.
FOREIGN_RAW_PREFILTER_MARGIN: int = 500
# Recent rated human games scanned to find the user's most-played time control (250 D-14).
USER_LEVEL_SCAN_GAMES: int = 200
# Newest games of that time control whose median pinned Elo is the user's level.
REFERENCE_ELO_GAMES: int = 50
# Level for a user with no rated games at all; mirrors the frontend FREE_PLAY_DEFAULT_ELO
# (frontend/src/hooks/useMaiaEloDefault.ts), the 250 CONTEXT default for such a user.
DEFAULT_USER_LEVEL_ELO: float = 1500.0
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


def user_level_elo(rows: Sequence[EloSourceRow]) -> float:
    """The user's level (250 D-14): median pinned Elo of the newest games in their most-played
    time control. `rows` are the user's rated human games, newest first.

    The bucket is the one with the most rows (a count tie goes to the bucket whose newest row comes
    first); correspondence rows and rows without a bucket never decide it. With no bucketed rows the
    level is the median over all rows, and with no rows DEFAULT_USER_LEVEL_ELO.
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
    return DEFAULT_USER_LEVEL_ELO if level is None else level


# ---------------------------------------------------------------------------
# PGN replay helpers (one python-chess parse each; failures are expected, not Sentry)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowSnapshot:
    """Self-sufficient window: start FEN plus the UCI moves from the lead-in start on."""

    start_fen: str
    move_ucis: str
    lead_in_plies: int


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


@dataclass
class _Pool:
    """Loaded batches of one origin (own or foreign) plus every id already picked."""

    batches: dict[int, _Batch] = field(default_factory=dict)
    seen_ids: list[int] = field(default_factory=list)

    def candidates(self) -> list[GameCandidates]:
        return [batch.candidates for batch in self.batches.values()]


@dataclass(frozen=True)
class _Filled:
    pick: WindowPick
    batch: _Batch


def _in_window(elo: float | None, elo_window: tuple[float, float] | None) -> bool:
    """Own games (no window) always pass; foreign games need a pinned Elo inside the band."""
    if elo_window is None:
        return True
    return elo is not None and elo_window[0] <= elo <= elo_window[1]


async def _load_batch(
    session: AsyncSession,
    *,
    user_id: int,
    game_ids: Sequence[int],
    is_own: bool,
    elo_window: tuple[float, float] | None,
) -> list[_Batch]:
    """Load and judge games (sequential awaits on the one session)."""
    games = await repo.load_candidate_games(session, game_ids)
    ids = [game.game_id for game in games]
    positions = await repo.load_positions(session, ids)
    flaws = await repo.load_blunder_flaws(session, ids)
    served = await repo.served_for_games(session, user_id=user_id, game_ids=ids)
    batches: list[_Batch] = []
    for game in games:
        elo = mover_pinned_elo(game)
        if not _in_window(elo, elo_window):
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
    elo_window: tuple[float, float] | None,
) -> None:
    pool.seen_ids.extend(game_ids)
    for batch in await _load_batch(
        session, user_id=user_id, game_ids=game_ids, is_own=is_own, elo_window=elo_window
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
) -> None:
    """Fill what the pool can for the still-empty slots; one window per game across the session."""
    used = {item.pick.game_id for item in filled.values()}
    for pick in assign_windows(empty, pool.candidates(), rng=rng, used_game_ids=used):
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


@dataclass(frozen=True)
class _Source:
    """Where the slots of one origin are filled from: the pick query and its limits."""

    origin: SlotOrigin
    max_rounds: int
    elo_window: tuple[float, float] | None
    pick: _PickFn


def _own_source(user_id: int) -> _Source:
    async def pick(
        session: AsyncSession, require_facepalm: bool, exclude_ids: Sequence[int]
    ) -> list[int]:
        return await repo.pick_own_game_ids(
            session,
            user_id=user_id,
            limit=OWN_BATCH_GAMES,
            exclude_ids=exclude_ids,
            require_facepalm=require_facepalm,
        )

    return _Source("own", MAX_OWN_BATCHES, None, pick)


async def _foreign_source(session: AsyncSession, user_id: int) -> _Source:
    """Foreign games whose mover's pinned Elo is within FOREIGN_RATING_BAND of the user's level.

    250 D-13: rating only (no time-control match), one band, no widening. The level is read once
    per session start (D-14).
    """
    level = user_level_elo(
        await repo.recent_rated_games(session, user_id=user_id, limit=USER_LEVEL_SCAN_GAMES)
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

    window = (level - FOREIGN_RATING_BAND, level + FOREIGN_RATING_BAND)
    return _Source("foreign", MAX_FOREIGN_BATCHES, window, pick)


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
            elo_window=source.elo_window,
        )
        _fill_from_pool(_empty_shapes(plans, filled, source.origin), pool, filled, rng=rng)


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
) -> None:
    """Redraw only the empty slots of one origin and retry its pool without new queries."""
    for _ in range(MAX_SHAPE_REDRAWS):
        empty = _empty_shapes(plans, filled, origin)
        if not empty:
            return
        for slot, shape in empty.items():
            plans[slot] = SlotPlan(origin, _redraw_shape(shape, rng))
        _fill_from_pool(_empty_shapes(plans, filled, origin), pool, filled, rng=rng)


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
        key_uci=None if blunder_ply is None else batch.positions[blunder_ply].best_move,
        refutation_uci=None
        if blunder_ply is None
        else _refutation_uci(batch.positions, blunder_ply),
        points_possible=points_possible(pick.shape),
    )


async def compose_windows(
    session: AsyncSession, *, user_id: int, rng: random.Random
) -> list[NewWindow]:
    """Compose up to BLUNDER_CHECK_SESSION_WINDOWS windows for the user (250 D-12..D-16)."""
    plans = {slot: draw_slot_plan(rng) for slot in range(BLUNDER_CHECK_SESSION_WINDOWS)}
    own, foreign = _Pool(), _Pool()
    filled: dict[int, _Filled] = {}
    await _fill_from_source(
        session,
        user_id=user_id,
        source=_own_source(user_id),
        plans=plans,
        pool=own,
        filled=filled,
        rng=rng,
    )
    _redraw_and_refill(plans, "own", own, filled, rng=rng)
    _convert_empty_own_to_foreign(plans, filled)
    if _empty_shapes(plans, filled, "foreign"):
        await _fill_from_source(
            session,
            user_id=user_id,
            source=await _foreign_source(session, user_id),
            plans=plans,
            pool=foreign,
            filled=filled,
            rng=rng,
        )
        _redraw_and_refill(plans, "foreign", foreign, filled, rng=rng)
    # Positions are renumbered contiguously so a short session keeps a gap-free sequence.
    windows: list[NewWindow] = []
    for _, item in sorted(filled.items()):
        window = _new_window(len(windows), item)
        if window is not None:
            windows.append(window)
    return windows
