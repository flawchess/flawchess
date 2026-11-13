"""Pure composition core for the blunder-check drill (SEED-261108-dk0, Phase 249).

Two stages, both pure (no DB, no I/O):

1. ``judge_game`` turns one analyzed game into candidates: user blunders (with their case,
   findability and the latest window position they can occupy) and herring runs (L consecutive
   safe user moves per window length). Severity and expected score come only from the stored-flaw
   classifier's own ``_run_all_moves_pass``; they are never re-derived (T-249-01).
2. ``assign_windows`` fills the session's drawn slots from the candidates of many games. Shapes
   are drawn first (D-03): a blunder is only ever picked among candidates that fit the drawn
   position, never the position derived from a blunder. There is no case cap (D-07) and no forced
   blunder/herring mix (D-11).

The quality gates on a blunder are findability (D-06, D-08), the early-ply floor and the
undecided-position rule: no played-probability cap and no capture/check/mate rule.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Literal, Protocol

from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: PLC2701
from app.repositories.query_utils import mover_is_white_at_ply
from app.services.blunder_check_rules import (
    BEST_PROB_MIN,
    BETTER_MOVE_POINTS,
    BLUNDER_POINTS,
    ES_BAND_HIGH,
    ES_BAND_LOW,
    LEAD_IN_PLIES,
    MAX_BLUNDER_POSITION,
    REFUTATION_PROB_MIN,
    SAFE_POINTS,
    WINDOW_LENGTHS,
    FindabilityInputs,
    MoveJudgement,
    WindowShape,
    blunder_es,
    blunder_position_undecided,
    findable,
    herring_flags,
    max_fit_position,
    miss_case,
    past_early_ply_floor,
    user_move_judgements,
)

# Private import by design: ES and severity must be the classifier's own pass, never re-derived
# (precedent: scripts/remote_eval_worker.py imports _run_all_moves_pass).
from app.services.flaws_service import _MoveEntry, _run_all_moves_pass  # noqa: PLC2701

PickCase = Literal["herring", "allowed", "pure_miss", "mixed"]
BlunderCase = Literal["allowed", "pure_miss", "mixed"]

_BLUNDER_SEVERITY_INT: int = _SEVERITY_INT["blunder"]
_BLUNDER_LABEL: Literal["blunder"] = "blunder"
# User plies kept before a blunder: enough for the deepest window position (position k needs k-1).
_PRECEDING_KEPT: int = MAX_BLUNDER_POSITION - 1
_FIRST_POSITION: int = 1


class FlawLike(Protocol):
    """The read-only flaw fields judging needs (a repository row satisfies it structurally)."""

    @property
    def ply(self) -> int: ...

    @property
    def severity(self) -> int: ...

    @property
    def is_miss(self) -> bool: ...

    @property
    def maia_refutation_prob(self) -> float | None: ...

    @property
    def maia_refutation_rank(self) -> int | None: ...

    @property
    def maia_best_prob(self) -> float | None: ...

    @property
    def maia_best_rank(self) -> int | None: ...


@dataclass(frozen=True)
class BlunderCandidate:
    """A user blunder that can anchor a window at any position 1..max_position."""

    game_id: int
    ply: int
    case: BlunderCase
    max_position: int
    # The up to MAX_BLUNDER_POSITION - 1 user plies immediately before the blunder, in game order.
    preceding_plies: tuple[int, ...]


@dataclass(frozen=True)
class HerringRun:
    """L consecutive Good, in-band user moves (the plies of the user's moves) with nothing to find."""

    game_id: int
    plies: tuple[int, ...]


@dataclass(frozen=True)
class GameCandidates:
    """Everything one game can supply: blunders and, per window length, herring runs."""

    game_id: int
    blunders: tuple[BlunderCandidate, ...]
    herrings: Mapping[int, tuple[HerringRun, ...]]


@dataclass(frozen=True)
class WindowPick:
    """One filled slot: the judged user plies (blunder last for a blunder window)."""

    slot: int
    game_id: int
    shape: WindowShape
    judged_plies: tuple[int, ...]
    blunder_ply: int | None
    case: PickCase

    @property
    def first_ply(self) -> int:
        return self.judged_plies[0]


@dataclass(frozen=True)
class _JudgedGame:
    """Classifier output for one game, shared by the blunder and herring scans."""

    game_id: int
    user_is_white: bool
    all_moves: Mapping[int, _MoveEntry]
    judgements: Sequence[MoveJudgement]
    # GamePosition.phase per ply (the position the move at that ply is played from).
    phases: Sequence[int | None]


# ---------------------------------------------------------------------------
# Judging one game
# ---------------------------------------------------------------------------


def _is_contiguous(positions: Sequence[GamePosition]) -> bool:
    """The classifier indexes positions by list index, so plies must run 0..n-1 without gaps."""
    return bool(positions) and all(p.ply == i for i, p in enumerate(positions))


def _past_floor(game: _JudgedGame, ply: int) -> bool:
    """Whether the move at `ply` clears the early-ply floor for its position's phase."""
    return ply < len(game.phases) and past_early_ply_floor(ply, game.phases[ply])


def _floor_position_cap(game: _JudgedGame, preceding: Sequence[MoveJudgement]) -> int:
    """Largest window position whose judged moves before the blunder all clear the early-ply floor.

    Bug fix (Phase 249 review): the floor was checked on the blunder ply only, so a blunder just
    past the floor drawn at a late position made the user judge opening-theory moves. Herring
    windows already check every judged ply.
    """
    cleared = 0
    for judgement in reversed(preceding):
        if not _past_floor(game, judgement.ply):
            break
        cleared += 1
    return _FIRST_POSITION + cleared


def _blunder_candidate(
    game: _JudgedGame,
    flaw: FlawLike,
    key_plies: AbstractSet[int],
    prompted_blunder_plies: AbstractSet[int],
) -> BlunderCandidate | None:
    """A stored blunder becomes a candidate only if it is the user's, still a blunder when
    recomputed (consistency guard, T-249-01), from an undecided position (`blunder_position_undecided`),
    findable (D-06) and fits window position 1+ (D-04, D-05).
    """
    if flaw.severity != _BLUNDER_SEVERITY_INT:
        return None
    if mover_is_white_at_ply(flaw.ply) != game.user_is_white:
        return None
    if flaw.ply not in key_plies or flaw.ply in prompted_blunder_plies:
        return None
    # Phase 249 UAT: no blunders from the early plies (same floors as personalized puzzles).
    if not _past_floor(game, flaw.ply):
        return None
    entry = game.all_moves.get(flaw.ply)
    if entry is None or entry[1] != _BLUNDER_LABEL:
        return None
    es_before, es_played, es_ref = blunder_es(game.all_moves, flaw.ply)
    # Phase 249 UAT: only blunders from a position that was not decided yet.
    if not blunder_position_undecided(es_before):
        return None
    case = miss_case(flaw.is_miss, es_ref, es_played)
    if case == "unclassified":
        return None
    maia = FindabilityInputs(
        refutation_prob=flaw.maia_refutation_prob,
        refutation_rank=flaw.maia_refutation_rank,
        best_prob=flaw.maia_best_prob,
        best_rank=flaw.maia_best_rank,
    )
    if not findable(case, maia, REFUTATION_PROB_MIN, BEST_PROB_MIN):
        return None
    preceding = [j for j in game.judgements if j.ply < flaw.ply][-_PRECEDING_KEPT:]
    max_position = min(max_fit_position(preceding, es_before), _floor_position_cap(game, preceding))
    if max_position < _FIRST_POSITION:
        return None
    return BlunderCandidate(
        game_id=game.game_id,
        ply=flaw.ply,
        case=case,
        max_position=max_position,
        preceding_plies=tuple(j.ply for j in preceding),
    )


def _in_served_range(ply: int, served_ply_ranges: Sequence[tuple[int, int]]) -> bool:
    """Inclusive bounds."""
    return any(low <= ply <= high for low, high in served_ply_ranges)


def _herring_runs(
    game: _JudgedGame, served_ply_ranges: Sequence[tuple[int, int]]
) -> dict[int, tuple[HerringRun, ...]]:
    """Sliding runs (not only disjoint, for variety) of L consecutive herring-flagged user moves
    that clear the early-ply floor and do not touch a ply range the user was already served."""
    flags = herring_flags(game.judgements, ES_BAND_LOW, ES_BAND_HIGH)
    runs: dict[int, tuple[HerringRun, ...]] = {}
    for length in WINDOW_LENGTHS:
        found: list[HerringRun] = []
        for start in range(len(game.judgements) - length + 1):
            if not all(flags[start : start + length]):
                continue
            plies = tuple(j.ply for j in game.judgements[start : start + length])
            if any(_in_served_range(ply, served_ply_ranges) for ply in plies):
                continue
            # Phase 249 UAT: an all-safe window never judges an early-ply move either.
            if not all(_past_floor(game, ply) for ply in plies):
                continue
            found.append(HerringRun(game.game_id, plies))
        runs[length] = tuple(found)
    return runs


def judge_game(
    *,
    game_id: int,
    user_is_white: bool,
    positions: Sequence[GamePosition],
    flaws: Sequence[FlawLike],
    key_plies: AbstractSet[int],
    prompted_blunder_plies: AbstractSet[int],
    served_ply_ranges: Sequence[tuple[int, int]],
) -> GameCandidates | None:
    """Judge one game into blunder candidates and herring runs; None for gapped positions."""
    if not _is_contiguous(positions):
        return None
    all_moves = _run_all_moves_pass(list(positions))
    move_plies = [p.ply for p in positions if p.move_san]
    game = _JudgedGame(
        game_id=game_id,
        user_is_white=user_is_white,
        all_moves=all_moves,
        judgements=user_move_judgements(all_moves, move_plies, user_is_white),
        phases=[p.phase for p in positions],
    )
    candidates = (
        _blunder_candidate(game, flaw, key_plies, prompted_blunder_plies)
        for flaw in sorted(flaws, key=lambda f: f.ply)
    )
    return GameCandidates(
        game_id=game_id,
        blunders=tuple(c for c in candidates if c is not None),
        herrings=_herring_runs(game, served_ply_ranges),
    )


# ---------------------------------------------------------------------------
# Filling the drawn slots
# ---------------------------------------------------------------------------


def judged_plies_for(candidate: BlunderCandidate, position: int) -> tuple[int, ...]:
    """The last position - 1 preceding user plies, then the blunder ply."""
    needed = position - 1
    lead = candidate.preceding_plies[-needed:] if needed > 0 else ()
    return (*lead, candidate.ply)


def _ordered_slots(slots: Mapping[int, WindowShape]) -> list[tuple[int, WindowShape]]:
    """Rarest first: blunder positions descending, then herring lengths descending."""
    blunder_slots = [(s, shape) for s, shape in slots.items() if shape.blunder_position is not None]
    herring_slots = [(s, shape) for s, shape in slots.items() if shape.blunder_position is None]
    blunder_slots.sort(key=lambda item: (-(item[1].blunder_position or 0), item[0]))
    herring_slots.sort(key=lambda item: (-item[1].length, item[0]))
    return blunder_slots + herring_slots


def _blunder_options(
    slot: int, shape: WindowShape, games: Sequence[GameCandidates]
) -> list[WindowPick]:
    """Candidates whose maximum position reaches the drawn one (D-03)."""
    position = shape.blunder_position or _FIRST_POSITION
    return [
        WindowPick(
            slot=slot,
            game_id=game.game_id,
            shape=shape,
            judged_plies=judged_plies_for(candidate, position),
            blunder_ply=candidate.ply,
            case=candidate.case,
        )
        for game in games
        for candidate in game.blunders
        if candidate.max_position >= position
    ]


def _herring_options(
    slot: int, shape: WindowShape, games: Sequence[GameCandidates]
) -> list[WindowPick]:
    return [
        WindowPick(
            slot=slot,
            game_id=game.game_id,
            shape=shape,
            judged_plies=run.plies,
            blunder_ply=None,
            case="herring",
        )
        for game in games
        for run in game.herrings.get(shape.length, ())
    ]


def _pick_sort_key(pick: WindowPick) -> tuple[int, int, int]:
    return (pick.game_id, pick.first_ply, pick.blunder_ply or 0)


def assign_windows(
    slots: Mapping[int, WindowShape],
    games: Sequence[GameCandidates],
    *,
    rng: random.Random,
    used_game_ids: AbstractSet[int],
) -> list[WindowPick]:
    """Fill the drawn slots rarest first, at most one window per game; unfillable slots are absent.

    Options are sorted before the choice so a seeded rng reproduces the result.
    """
    taken = set(used_game_ids)
    picks: list[WindowPick] = []
    for slot, shape in _ordered_slots(slots):
        eligible = [game for game in games if game.game_id not in taken]
        if shape.blunder_position is not None:
            options = _blunder_options(slot, shape, eligible)
        else:
            options = _herring_options(slot, shape, eligible)
        if not options:
            continue
        options.sort(key=_pick_sort_key)
        pick = rng.choice(options)
        taken.add(pick.game_id)
        picks.append(pick)
    return picks


def points_possible(shape: WindowShape) -> int:
    """D-14: 1 per judged safe move, plus 3 for flagging the blunder and 2 for the better move."""
    if shape.blunder_position is None:
        return shape.length * SAFE_POINTS
    return (shape.blunder_position - 1) * SAFE_POINTS + BLUNDER_POINTS + BETTER_MOVE_POINTS


def lead_in_start(first_ply: int) -> int:
    """First ply of the lead-in shown before a window (D-12), clamped at the game start."""
    return max(0, first_ply - LEAD_IN_PLIES)
