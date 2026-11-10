"""Human-readable spot-check sample for the blunder-check calibration (D-18, Phase 248).

Automated metrics can pass while the selection is wrong in a way only a person sees, so this
module exports a small, reproducible sample of windows drawn the way the feature would draw
them: window length L uniform over 3 to 5 user moves, a per-move blunder hazard of 0.265, so
about 30% of windows are herrings (every judged move Good, nothing to find).

Each window shows the public game link, a 3-ply lead-in, the judged user moves with the
opponent replies, the answer (the blunder, or "all safe") and the refutation or missed best move
with its Maia probability and rank. The file may be shown to GM Noel Studer, so it carries only
public game links, ratings and moves: no FlawChess user ids, usernames or emails (T-248-11).
"""

from __future__ import annotations

import io
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

import chess
import chess.pgn
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_position import GamePosition
from scripts.blunder_check.metrics import (
    ELO_BUCKETS,
    HAZARD,
    LEAD_IN_PLIES,
    WINDOW_LENGTHS,
    EloBucket,
    MoveJudgement,
    herring_flags,
)
from scripts.blunder_check.render import (
    ReportParams,
    analysis_blunders,
    analysis_games,
    blunder_fits,
    usable_blunders,
)
from scripts.blunder_check.sample import BlunderRecord, Collection

DEFAULT_SPOT_CHECK_PER_BUCKET: int = 20
# Draw attempts allowed per wanted window; an attempt is wasted when its pool is empty or used up.
MAX_DRAW_ATTEMPTS_PER_WINDOW: int = 50
NO_PUBLIC_LINK: str = "no public link"
# Separator of game_positions.pv (space-joined UCI line); its first token is the reply fallback.
PV_SEPARATOR: str = " "
HERRING_CASE: str = "herring"


@dataclass(frozen=True)
class WindowShape:
    """A drawn window: length in user moves and the blunder position (None for a herring)."""

    length: int
    blunder_position: int | None


@dataclass(frozen=True)
class SpotWindow:
    """One chosen window: `good_moves` are the Good judged moves shown before the answer."""

    bucket: EloBucket
    shape: WindowShape
    game_id: int
    elo: float | None
    good_moves: tuple[MoveJudgement, ...]
    blunder: BlunderRecord | None

    @property
    def case(self) -> str:
        return HERRING_CASE if self.blunder is None else self.blunder.case


@dataclass(frozen=True)
class SpotCheckParams:
    """What the spot-check draws against: the report thresholds and the per-bucket count."""

    report: ReportParams
    per_bucket: int = DEFAULT_SPOT_CHECK_PER_BUCKET


@dataclass(frozen=True)
class HerringCandidate:
    """A disjoint run of L consecutive Good, in-band user moves from one game."""

    game_id: int
    elo: float | None
    good_moves: tuple[MoveJudgement, ...]


@dataclass
class JudgedLine:
    """One judged Good user move with the opponent's reply."""

    move: str
    es_before: float | None
    reply: str | None


@dataclass
class SpotWindowDetail:
    """A window with everything the markdown needs, resolved from the game's PGN."""

    window: SpotWindow
    link: str
    user_rating: int | None
    start_fen: str
    lead_in: str
    judged: list[JudgedLine] = field(default_factory=list)
    answer_fen: str | None = None
    answer_move: str | None = None
    refutation: str | None = None
    missed_best: str | None = None


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def draw_window_shape(rng: random.Random) -> WindowShape:
    """L uniform over WINDOW_LENGTHS; the blunder sits at the first position whose hazard fires."""
    length = rng.choice(WINDOW_LENGTHS)
    for position in range(1, length + 1):
        if rng.random() < HAZARD:
            return WindowShape(length, position)
    return WindowShape(length, None)


def _herring_candidates(
    collection: Collection, bucket: EloBucket, length: int, params: ReportParams
) -> list[HerringCandidate]:
    """Disjoint L-windows over maximal runs of Good in-band moves, in (game_id, run) order."""
    candidates: list[HerringCandidate] = []
    games = sorted(
        (g for g in analysis_games(collection) if g.bucket == bucket), key=lambda g: g.game_id
    )
    for game in games:
        flags = herring_flags(game.judgements, params.band_low, params.band_high)
        index = 0
        while index < len(flags):
            if not flags[index]:
                index += 1
                continue
            end = index
            while end < len(flags) and flags[end]:
                end += 1
            for start in range(index, end - length + 1, length):
                candidates.append(
                    HerringCandidate(
                        game.game_id, game.elo, tuple(game.judgements[start : start + length])
                    )
                )
            index = end
    return candidates


class _BucketPools:
    """Lazily built candidate pools of one Elo bucket (blunders per position, herrings per length)."""

    def __init__(self, collection: Collection, bucket: EloBucket, params: ReportParams) -> None:
        self._collection = collection
        self._bucket = bucket
        self._params = params
        self._usable = sorted(
            (
                b
                for b in usable_blunders(analysis_blunders(collection), params)
                if b.bucket == bucket
            ),
            key=lambda b: (b.game_id, b.ply),
        )
        self._elo = {g.game_id: g.elo for g in collection.games if g.bucket == bucket}
        self._fit: dict[int, list[BlunderRecord]] = {}
        self._herring: dict[int, list[HerringCandidate]] = {}

    def blunders_fitting(self, position: int) -> list[BlunderRecord]:
        if position not in self._fit:
            self._fit[position] = [
                b for b in self._usable if blunder_fits(b, position, self._params)
            ]
        return self._fit[position]

    def herrings(self, length: int) -> list[HerringCandidate]:
        if length not in self._herring:
            self._herring[length] = _herring_candidates(
                self._collection, self._bucket, length, self._params
            )
        return self._herring[length]

    def elo_of(self, game_id: int) -> float | None:
        return self._elo.get(game_id)


def _blunder_window(
    pools: _BucketPools, shape: WindowShape, used: set[int], bucket: EloBucket, rng: random.Random
) -> SpotWindow | None:
    position = shape.blunder_position
    if position is None:
        return None
    available = [b for b in pools.blunders_fitting(position) if b.game_id not in used]
    if not available:
        return None
    blunder = rng.choice(available)
    preceding = tuple(blunder.preceding[len(blunder.preceding) - (position - 1) :])
    return SpotWindow(
        bucket, shape, blunder.game_id, pools.elo_of(blunder.game_id), preceding, blunder
    )


def _herring_window(
    pools: _BucketPools, shape: WindowShape, used: set[int], bucket: EloBucket, rng: random.Random
) -> SpotWindow | None:
    available = [c for c in pools.herrings(shape.length) if c.game_id not in used]
    if not available:
        return None
    chosen = rng.choice(available)
    return SpotWindow(bucket, shape, chosen.game_id, chosen.elo, chosen.good_moves, None)


def pick_windows(
    collection: Collection, params: SpotCheckParams, rng: random.Random
) -> list[SpotWindow]:
    """Per Elo bucket, hazard-model windows until per_bucket is reached or candidates run out.

    A blunder window at position k uses only a usable blunder that fits position k at the chosen
    band (D-16); a herring window uses L consecutive Good in-band moves of one game. A game
    appears at most once per bucket. Candidate order is stable, so the seed fixes the sample.
    """
    chosen: list[SpotWindow] = []
    for bucket in ELO_BUCKETS:
        # One child stream per bucket: a bucket's draws never shift the next bucket's.
        bucket_rng = random.Random(rng.getrandbits(64))
        pools = _BucketPools(collection, bucket, params.report)
        used: set[int] = set()
        picked = 0
        attempts = 0
        while (
            picked < params.per_bucket
            and attempts < params.per_bucket * MAX_DRAW_ATTEMPTS_PER_WINDOW
        ):
            attempts += 1
            shape = draw_window_shape(bucket_rng)
            build = _herring_window if shape.blunder_position is None else _blunder_window
            window = build(pools, shape, used, bucket, bucket_rng)
            if window is None:
                continue
            used.add(window.game_id)
            chosen.append(window)
            picked += 1
    return chosen


# ---------------------------------------------------------------------------
# Details from the database (read-only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GameInfo:
    pgn: str
    platform_url: str | None
    user_rating: int | None


def move_label(ply: int, san: str) -> str:
    """'14. Qd2' for White's move at ply 26, '14... O-O' for Black's."""
    number = ply // 2 + 1
    return f"{number}. {san}" if ply % 2 == 0 else f"{number}... {san}"


def format_line(plies: Sequence[tuple[int, str]]) -> str:
    """A move list: number before each White move and before a Black move that opens the line."""
    parts: list[str] = []
    for index, (ply, san) in enumerate(plies):
        if ply % 2 == 0 or index == 0:
            parts.append(move_label(ply, san))
        else:
            parts.append(san)
    return " ".join(parts)


class _Replay:
    """One pass over a game's mainline keeping SAN and pre-move boards for the wanted plies."""

    def __init__(self, pgn: str, wanted: set[int]) -> None:
        self.san: dict[int, str] = {}
        self.board: dict[int, chess.Board] = {}
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return
        board = game.board()
        for ply, node in enumerate(game.mainline()):
            if ply in wanted:
                self.board[ply] = board.copy(stack=False)
                self.san[ply] = board.san(node.move)
            board.push(node.move)

    def move_text(self, ply: int, uci: str | None) -> str | None:
        """SAN of `uci` on the board before `ply`, 'xxxx (illegal)' when not legal, None if unknown."""
        board = self.board.get(ply)
        if uci is None or board is None:
            return None
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return f"{uci} (illegal)"
        if move not in board.legal_moves:
            return f"{uci} (illegal)"
        return board.san(move)


def _shown_plies(window: SpotWindow) -> list[int]:
    """The judged user plies of the window, answer last (always at least one)."""
    plies = [m.ply for m in window.good_moves]
    if window.blunder is not None:
        plies.append(window.blunder.ply)
    return plies


def _wanted_plies(window: SpotWindow) -> set[int]:
    """Lead-in start through one ply past the last judged move (the opponent reply / refutation)."""
    shown = _shown_plies(window)
    return set(range(max(0, shown[0] - LEAD_IN_PLIES), shown[-1] + 2))


async def _load_game_info(
    session_maker: async_sessionmaker[AsyncSession], game_ids: Sequence[int]
) -> dict[int, _GameInfo]:
    stmt = select(
        Game.id,
        Game.pgn,
        Game.platform_url,
        Game.user_color,
        Game.white_rating,
        Game.black_rating,
    ).where(Game.id.in_(game_ids))
    async with session_maker() as session:
        rows = (await session.execute(stmt)).all()
    return {
        int(row[0]): _GameInfo(
            pgn=str(row[1]),
            platform_url=row[2],
            user_rating=row[4] if row[3] == "white" else row[5],
        )
        for row in rows
    }


async def _load_moves(
    session_maker: async_sessionmaker[AsyncSession], windows: Sequence[SpotWindow]
) -> tuple[dict[tuple[int, int], str | None], dict[tuple[int, int], str | None]]:
    """(best_move at the answer ply, refutation reply at answer ply + 1) keyed by (game_id, ply)."""
    pairs = {
        (w.game_id, ply)
        for w in windows
        if w.blunder is not None
        for ply in (w.blunder.ply, w.blunder.ply + 1)
    }
    if not pairs:
        return {}, {}
    stmt = select(
        GamePosition.game_id, GamePosition.ply, GamePosition.best_move, GamePosition.pv
    ).where(tuple_(GamePosition.game_id, GamePosition.ply).in_(sorted(pairs)))
    async with session_maker() as session:
        rows = (await session.execute(stmt)).all()
    best: dict[tuple[int, int], str | None] = {}
    reply: dict[tuple[int, int], str | None] = {}
    for game_id, ply, best_move, pv in rows:
        best[(game_id, ply)] = best_move
        # Refutation source (D-20): best_move, else the first pv token.
        reply[(game_id, ply)] = best_move or (pv.split(PV_SEPARATOR)[0] if pv else None)
    return best, reply


def _build_detail(
    window: SpotWindow,
    info: _GameInfo,
    best: dict[tuple[int, int], str | None],
    reply: dict[tuple[int, int], str | None],
) -> SpotWindowDetail:
    replay = _Replay(info.pgn, _wanted_plies(window))
    answer = window.blunder.ply if window.blunder is not None else None
    first = _shown_plies(window)[0]
    lead_start = max(0, first - LEAD_IN_PLIES)
    start_board = replay.board.get(lead_start)
    detail = SpotWindowDetail(
        window=window,
        link=info.platform_url or NO_PUBLIC_LINK,
        user_rating=info.user_rating,
        start_fen=start_board.fen() if start_board is not None else "unknown",
        lead_in=format_line(
            [(p, replay.san[p]) for p in range(lead_start, first) if p in replay.san]
        ),
    )
    for move in window.good_moves:
        opponent_reply = replay.san.get(move.ply + 1)
        detail.judged.append(
            JudgedLine(
                move=move_label(move.ply, replay.san.get(move.ply, "?")),
                es_before=move.es_before,
                reply=None if opponent_reply is None else move_label(move.ply + 1, opponent_reply),
            )
        )
    if answer is None:
        return detail
    answer_board = replay.board.get(answer)
    detail.answer_fen = answer_board.fen() if answer_board is not None else "unknown"
    detail.answer_move = move_label(answer, replay.san.get(answer, "?"))
    # The refutation row is keyed at answer + 1, the missed best move at the answer ply.
    detail.refutation = replay.move_text(answer + 1, reply.get((window.game_id, answer + 1)))
    detail.missed_best = replay.move_text(answer, best.get((window.game_id, answer)))
    return detail


async def fetch_window_details(
    session_maker: async_sessionmaker[AsyncSession], windows: Sequence[SpotWindow]
) -> list[SpotWindowDetail]:
    """Resolve windows against the database with two read-only SELECTs (games, positions)."""
    if not windows:
        return []
    infos = await _load_game_info(session_maker, sorted({w.game_id for w in windows}))
    best, reply = await _load_moves(session_maker, windows)
    return [_build_detail(w, infos[w.game_id], best, reply) for w in windows if w.game_id in infos]


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def _fmt_prob(prob: float | None, rank: int | None) -> str:
    if prob is None or rank is None:
        return "Maia pair not scored"
    return f"Maia probability {prob:.3f}, rank {rank}"


def _es_text(es: float | None) -> str:
    return "n/a" if es is None else f"{es:.2f}"


def _answer_lines(detail: SpotWindowDetail) -> list[str]:
    window = detail.window
    blunder = window.blunder
    if blunder is None:
        return ["- **Answer:** all safe (every judged move is Good)."]
    lines = [
        f"- **FEN before the answer move:** `{detail.answer_fen}`",
        f"- **Answer:** blunder {detail.answer_move} (pre-move ES {_es_text(blunder.es_before)}, "
        f"ES after {_es_text(blunder.es_played)}).",
    ]
    if blunder.case in ("allowed", "mixed"):
        lines.append(
            f"- **Refutation:** {detail.refutation or 'unknown'} "
            f"({_fmt_prob(blunder.maia_refutation_prob, blunder.maia_refutation_rank)})."
        )
    if blunder.case in ("pure_miss", "mixed"):
        lines.append(
            f"- **Missed best move:** {detail.missed_best or 'unknown'} "
            f"({_fmt_prob(blunder.maia_best_prob, blunder.maia_best_rank)})."
        )
    return lines


def _window_markdown(index: int, detail: SpotWindowDetail) -> str:
    window = detail.window
    shape = window.shape
    position = (
        "no blunder" if shape.blunder_position is None else f"blunder at {shape.blunder_position}"
    )
    pinned = "n/a" if window.elo is None else f"{window.elo:.0f}"
    rating = "n/a" if detail.user_rating is None else str(detail.user_rating)
    lines = [
        f"#### Window {index}: {window.case} (length {shape.length}, {position})",
        "",
        f"- **Game:** {detail.link}",
        f"- **User rating:** {rating} (pinned Maia Elo {pinned})",
        f"- **FEN before the lead-in:** `{detail.start_fen}`",
        f"- **Lead-in:** {detail.lead_in or '(game start)'}",
        "- **Judged user moves:**",
    ]
    for line in detail.judged:
        reply = f", reply {line.reply}" if line.reply else ""
        lines.append(f"  - {line.move} (Good, pre-move ES {_es_text(line.es_before)}){reply}")
    lines.extend(_answer_lines(detail))
    return "\n".join(lines)


def render_spot_check(details: Sequence[SpotWindowDetail], params: SpotCheckParams) -> str:
    """The spot-check markdown: header, then one subsection per Elo bucket."""
    report = params.report
    header = [
        "# Blunder-check spot-check",
        "",
        "Windows drawn the way the feature would draw them: length L uniform over "
        f"{WINDOW_LENGTHS[0]} to {WINDOW_LENGTHS[-1]} user moves, per-move blunder hazard "
        f"{HAZARD}, so roughly 30% are herrings (all judged moves safe). About "
        f"{params.per_bucket} windows per Elo bucket, at most one per game, drawn with a fixed "
        "seed.",
        "",
        f"Thresholds: refutation R = {report.refutation_threshold}, best-move X' = "
        f"{report.miss_threshold}, eval band [{report.band_low:.2f}, {report.band_high:.2f}] on "
        "the pre-move ES. A recommendation only; nothing here is wired into app code.",
        "",
        "How to read: for each window, play through the lead-in and the judged moves on the "
        "board (the game link opens the full game), decide whether the position is a fair "
        "question, then compare with the answer. A blunder window is fair when the refutation or "
        "the missed move is something a player of that rating could find. Moves are in SAN; a "
        "stored move that is not legal on the replayed board prints as its UCI with the word "
        "illegal.",
    ]
    by_bucket: dict[EloBucket, list[SpotWindowDetail]] = defaultdict(list)
    for detail in details:
        by_bucket[detail.window.bucket].append(detail)
    sections = ["\n".join(header)]
    for bucket in ELO_BUCKETS:
        bucket_details = by_bucket.get(bucket, [])
        if not bucket_details:
            continue
        body = [f"### {bucket}", ""]
        body.append("\n\n".join(_window_markdown(i, d) for i, d in enumerate(bucket_details, 1)))
        sections.append("\n".join(body))
    return "\n\n".join(sections) + "\n"
