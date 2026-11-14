"""Arrow-oddness diagnostic for the blunder-check calibration report (D-17, Phase 248).

The blunder-check shows the user an arrow for the played move. If the arrow looks odd
(low Maia probability at the user's rating) exactly when the move is a blunder, the user can
win by flagging odd-looking arrows without reading the position. This module measures that:
Maia's probability of the played move for a deterministic sample of judged Good user moves,
against the stored probability of qualifying blunders. Probability only (Phase 250 D-10): the
played-move rank columns are dropped, so no rank is read or written here.

Good moves are scored on the exact pre-move board (the games.pgn replay, never game_flaws.fen)
at the game's pinned user Elo, through the same ``full_policy`` and ``compute_maia_flaw_stats``
the flaw scorer uses. Inference runs with no database session open.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.services import maia_engine
from app.services.maia_flaw_scoring import replay_flaw_boards
from app.services.maia_flaw_stats import compute_maia_flaw_stats
from scripts.blunder_check.metrics import ELO_BUCKETS, EloBucket, auc, quartiles
from scripts.blunder_check.sample import BlunderRecord, Collection, GoodMoveOddness

# Prod default; --oddness-sample overrides.
ODDNESS_GOOD_MOVES_PER_BUCKET: int = 1500
DEFAULT_SEED: int = 248_261_108
# Games whose PGNs are fetched per read-only SELECT.
PGN_BATCH_GAMES: int = 100

SessionMaker = async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class GoodMoveTarget:
    """One sampled judged Good user move, with its pre-move ES kept for the render-time band."""

    game_id: int
    ply: int
    bucket: EloBucket
    es_before: float | None


@dataclass
class ScoredGoodMoves:
    """Scored Good moves plus the targets the replay or the policy could not serve."""

    records: list[GoodMoveOddness]
    skipped: int


@dataclass(frozen=True)
class OddnessRow:
    """Per-bucket comparison of Maia's played-move probability: judged Good moves vs blunders."""

    n_good: int
    n_blunder: int
    good_quartiles: tuple[float, float, float] | None
    blunder_quartiles: tuple[float, float, float] | None
    auc: float | None


def select_good_moves(collection: Collection, per_bucket: int, seed: int) -> list[GoodMoveTarget]:
    """Sample up to per_bucket judged Good user moves per Elo bucket, reproducibly.

    Candidates are every Good user move of every rated, non-guest game of the bucket; no band
    filter is applied here (the pre-move ES is kept so render can filter at the chosen band).
    The candidate order is stable (game_id, ply) so one seeded Random yields the same sample.
    """
    by_bucket: dict[EloBucket, list[GoodMoveTarget]] = defaultdict(list)
    for game in sorted(collection.games, key=lambda g: g.game_id):
        if game.is_guest or game.bucket is None:
            continue
        by_bucket[game.bucket].extend(
            GoodMoveTarget(game.game_id, j.ply, game.bucket, j.es_before)
            for j in sorted(game.judgements, key=lambda j: j.ply)
            if j.good
        )
    rng = random.Random(seed)
    sampled: list[GoodMoveTarget] = []
    for bucket in ELO_BUCKETS:
        candidates = by_bucket.get(bucket, [])
        if len(candidates) > per_bucket:
            candidates = rng.sample(candidates, per_bucket)
        sampled.extend(sorted(candidates, key=lambda t: (t.game_id, t.ply)))
    return sampled


async def _fetch_pgns(session_maker: SessionMaker, game_ids: Sequence[int]) -> dict[int, str]:
    """One read-only SELECT for a batch of games; the session is closed before any inference."""
    async with session_maker() as session:
        rows = (await session.execute(select(Game.id, Game.pgn).where(Game.id.in_(game_ids)))).all()
    return {int(row[0]): str(row[1]) for row in rows}


def _score_game(
    pgn: str,
    targets: Sequence[GoodMoveTarget],
    elo: float,
) -> ScoredGoodMoves:
    """Score one game's targets on the exact replayed pre-move boards."""
    boards, reason = replay_flaw_boards(pgn, [t.ply for t in targets])
    records: list[GoodMoveOddness] = []
    skipped = 0
    for target in targets:
        replayed = boards.get(target.ply)
        if reason is not None or replayed is None:
            skipped += 1
            continue
        board, played_uci = replayed
        probs = maia_engine.full_policy(board.fen(), elo)
        if probs is None:
            # The CLI starts Maia before sampling; a None here means a broken session, not data.
            raise RuntimeError("Maia policy unavailable while scoring Good moves")
        stats, _ = compute_maia_flaw_stats(probs, played_uci=played_uci)
        played_prob = None if stats is None else stats["maia_played_prob"]
        if played_prob is None:
            skipped += 1
            continue
        records.append(
            GoodMoveOddness(
                game_id=target.game_id,
                ply=target.ply,
                bucket=target.bucket,
                es_before=target.es_before,
                played_prob=played_prob,
            )
        )
    return ScoredGoodMoves(records, skipped)


async def score_good_moves(
    session_maker: SessionMaker,
    targets: Sequence[GoodMoveTarget],
    pinned_elos: Mapping[int, float],
) -> ScoredGoodMoves:
    """Maia probability of each target move at the game's pinned user Elo (D-17)."""
    by_game: dict[int, list[GoodMoveTarget]] = defaultdict(list)
    for target in targets:
        by_game[target.game_id].append(target)
    game_ids = sorted(by_game)
    total = ScoredGoodMoves([], 0)
    for start in range(0, len(game_ids), PGN_BATCH_GAMES):
        batch = game_ids[start : start + PGN_BATCH_GAMES]
        pgns = await _fetch_pgns(session_maker, batch)
        for game_id in batch:
            pgn = pgns.get(game_id)
            elo = pinned_elos.get(game_id)
            if pgn is None or elo is None:
                total.skipped += len(by_game[game_id])
                continue
            scored = _score_game(pgn, by_game[game_id], elo)
            total.records.extend(scored.records)
            total.skipped += scored.skipped
    return total


def summarize_group(
    good: Sequence[GoodMoveOddness], blunders: Sequence[BlunderRecord]
) -> OddnessRow:
    """Compare the played-move probability of Good moves and blunders (blunders need a stored one)."""
    good_probs = [g.played_prob for g in good]
    blunder_probs = [b.maia_played_prob for b in blunders if b.maia_played_prob is not None]
    return OddnessRow(
        n_good=len(good_probs),
        n_blunder=len(blunder_probs),
        good_quartiles=quartiles(good_probs),
        blunder_quartiles=quartiles(blunder_probs),
        auc=auc(good_probs, blunder_probs),
    )


def summarize_oddness(
    good: Sequence[GoodMoveOddness], blunders: Sequence[BlunderRecord]
) -> dict[EloBucket, OddnessRow]:
    """Per-bucket OddnessRow; AUC = P(Good prob > blunder prob) + 0.5 P(tie)."""
    return {
        bucket: summarize_group(
            [g for g in good if g.bucket == bucket], [b for b in blunders if b.bucket == bucket]
        )
        for bucket in ELO_BUCKETS
    }
