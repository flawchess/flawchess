"""Session composition for the blunder-check drill (SEED-261108-dk0, Phase 249).

`compose_windows` draws the session's window shapes first (D-03/D-11), then fills them from
games in bounded batches: the user's own unserved fully evaluated games first, and only for the
slots own supply cannot fit, other non-guest users' games whose mover's pinned Elo sits in a band
around the user's reference Elo (D-09). Every pick becomes a `NewWindow` carrying a
self-sufficient snapshot (start FEN + UCI moves) so a later delete of a foreign game never breaks
the session (D-15).

Mechanics (Claude's discretion, recorded in the plan): on the fly per session start, game-first,
Python judgements on the classifier's own pass. Queries per start are bounded by
MAX_OWN_BATCHES, len(FOREIGN_ELO_BANDS) and MAX_SHAPE_REDRAWS (redraws reuse loaded batches).

All awaits on the one AsyncSession are sequential (CLAUDE.md: never gather on a session).
"""

from __future__ import annotations

import io
import random
import statistics
from collections.abc import Mapping, Sequence
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
    WindowShape,
    draw_window_shape,
)
from app.services.normalization import is_correspondence_time_control

# Own games loaded per batch (one random pick of fully evaluated games, then judged in Python).
OWN_BATCH_GAMES: int = 40
# Own batches per session start; the first batch already covers a typical session.
MAX_OWN_BATCHES: int = 3
# Foreign games loaded per Elo band.
FOREIGN_BATCH_GAMES: int = 40
# TABLESAMPLE SYSTEM percentage for the foreign pick, so it never scans the whole games table.
FOREIGN_SAMPLE_PERCENT: float = 2.0
# Pinned-Elo half-widths around the user's reference Elo; one batch per band (widened once).
FOREIGN_ELO_BANDS: tuple[int, ...] = (100, 200)
# The raw-rating prefilter is wider than the band because chess.com and lichess scales differ;
# the exact band is checked on the pinned Elo after loading.
FOREIGN_RAW_PREFILTER_MARGIN: int = 500
# Recent games whose median pinned Elo is the user's reference Elo.
REFERENCE_ELO_GAMES: int = 50
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


def reference_elo(rows: Sequence[EloSourceRow]) -> float | None:
    """Median pinned Elo of the user's recent rated games; None for no rows."""
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
            prompted_blunder_plies=served.prompted.get(game.game_id, set()),
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


def _empty_slots(
    slots: Mapping[int, WindowShape], filled: Mapping[int, _Filled]
) -> dict[int, WindowShape]:
    return {slot: shape for slot, shape in slots.items() if slot not in filled}


async def _fill_from_own(
    session: AsyncSession,
    *,
    user_id: int,
    slots: Mapping[int, WindowShape],
    own: _Pool,
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    for _ in range(MAX_OWN_BATCHES):
        if not _empty_slots(slots, filled):
            return
        ids = await repo.pick_own_game_ids(
            session, user_id=user_id, limit=OWN_BATCH_GAMES, exclude_ids=own.seen_ids
        )
        if not ids:
            return
        await _load_into_pool(
            session, own, user_id=user_id, game_ids=ids, is_own=True, elo_window=None
        )
        _fill_from_pool(_empty_slots(slots, filled), own, filled, rng=rng)


async def _fill_from_foreign(
    session: AsyncSession,
    *,
    user_id: int,
    slots: Mapping[int, WindowShape],
    foreign: _Pool,
    filled: dict[int, _Filled],
    rng: random.Random,
) -> None:
    reference = reference_elo(
        await repo.recent_rated_games(session, user_id=user_id, limit=REFERENCE_ELO_GAMES)
    )
    if reference is None:
        return
    for band in FOREIGN_ELO_BANDS:
        if not _empty_slots(slots, filled):
            return
        raw_margin = band + FOREIGN_RAW_PREFILTER_MARGIN
        ids = await repo.pick_foreign_game_ids(
            session,
            user_id=user_id,
            raw_low=int(reference - raw_margin),
            raw_high=int(reference + raw_margin),
            limit=FOREIGN_BATCH_GAMES,
            exclude_ids=foreign.seen_ids,
            sample_percent=FOREIGN_SAMPLE_PERCENT,
        )
        await _load_into_pool(
            session,
            foreign,
            user_id=user_id,
            game_ids=ids,
            is_own=False,
            elo_window=(reference - band, reference + band),
        )
        _fill_from_pool(_empty_slots(slots, filled), foreign, filled, rng=rng)


def _redraw_and_refill(
    slots: dict[int, WindowShape],
    pools: Sequence[_Pool],
    filled: dict[int, _Filled],
    *,
    rng: random.Random,
) -> None:
    """Redraw only the empty slots and retry own then foreign pools without new queries."""
    for _ in range(MAX_SHAPE_REDRAWS):
        empty = _empty_slots(slots, filled)
        if not empty:
            return
        for slot in empty:
            slots[slot] = draw_window_shape(rng)
        for pool in pools:
            _fill_from_pool(_empty_slots(slots, filled), pool, filled, rng=rng)


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
    """Compose up to BLUNDER_CHECK_SESSION_WINDOWS windows for the user (D-02, D-09)."""
    slots = {slot: draw_window_shape(rng) for slot in range(BLUNDER_CHECK_SESSION_WINDOWS)}
    own, foreign = _Pool(), _Pool()
    filled: dict[int, _Filled] = {}
    await _fill_from_own(session, user_id=user_id, slots=slots, own=own, filled=filled, rng=rng)
    if _empty_slots(slots, filled):
        await _fill_from_foreign(
            session, user_id=user_id, slots=slots, foreign=foreign, filled=filled, rng=rng
        )
    _redraw_and_refill(slots, (own, foreign), filled, rng=rng)
    # Positions are renumbered contiguously so a short session keeps a gap-free sequence.
    windows: list[NewWindow] = []
    for _, item in sorted(filled.items()):
        window = _new_window(len(windows), item)
        if window is not None:
            windows.append(window)
    return windows
