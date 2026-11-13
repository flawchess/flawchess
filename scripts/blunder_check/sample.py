"""Read-only sampler for the blunder-check calibration report (SEED-261108-dk0, Phase 248, 250).

Turns per-ply evals into per-blunder and per-game records using the flaw classifier's own
expected-score convention (``_run_all_moves_pass``), so every number in the report is computed
the way the app computes it (D-13). Everything here only reads: the engine opens each
connection with ``default_transaction_read_only = on`` and a named statement timeout, so an
accidental write raises instead of landing (T-248-08).

The records and the exact per-user aggregates are plain dataclasses with to_dict/from_dict, so
a whole collection can be written to a JSON cache and re-rendered without a database.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import aliased, load_only

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: PLC2701
from app.repositories.query_utils import (
    ANALYTICS_INCLUDED_PLATFORMS,
    is_opponent_expr,
    mover_is_white_at_ply,
)
from app.schemas.normalization import Platform, TimeControlBucket
from app.services.best_move_candidates import pinned_elo_for_mover

# Private import by design: the report must use the classifier's own per-ply pass (precedent:
# scripts/remote_eval_worker.py imports it the same way).
from app.services.flaws_service import _run_all_moves_pass  # noqa: PLC2701
from app.services.normalization import is_correspondence_time_control
from scripts.backfill_maia_flaws import SHARD_RESIDUE_SQL
from scripts.blunder_check.metrics import (
    MAX_BLUNDER_POSITION,
    EloBucket,
    MissCase,
    MoveJudgement,
    Provenance,
    blunder_es,
    elo_bucket,
    flaw_control,
    miss_case,
    user_move_judgements,
)

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# Statement timeout on the report connection: long enough for the aggregate scans on prod,
# short enough that a runaway query cannot hold the server for hours.
REPORT_STATEMENT_TIMEOUT_MS: int = 30 * 60 * 1000
# Sampling resolution: permille of games, selected by md5 residue of the game id.
PERMILLE_BASE: int = 1000
# chess.com and lichess only; pasted and bot-platform games are out of the population.
CALIBRATION_PLATFORMS: tuple[str, ...] = ANALYTICS_INCLUDED_PLATFORMS
DEFAULT_BATCH_GAMES: int = 500
# Rating groups for the per-user aggregates (approximation of the exact per-game Elo, D-23).
RATING_GROUP_WIDTH: int = 50
BLUNDER_SEVERITY: int = _SEVERITY_INT["blunder"]
# Version 2 (Phase 250): blunder records carry the facepalm fields instead of the Maia best /
# refutation pairs and ranks; a cache written before that no longer loads.
CACHE_VERSION: int = 2
# Number of user moves kept before each blunder (positions 2..MAX_BLUNDER_POSITION need k-1).
PRECEDING_MOVES_KEPT: int = MAX_BLUNDER_POSITION - 1


# ---------------------------------------------------------------------------
# Read-only engine
# ---------------------------------------------------------------------------


def readonly_connect_args(
    statement_timeout_ms: int = REPORT_STATEMENT_TIMEOUT_MS,
) -> dict[str, Any]:
    """asyncpg connect args that make every session of the engine read-only with a timeout."""
    return {
        "server_settings": {
            "default_transaction_read_only": "on",
            "statement_timeout": str(statement_timeout_ms),
        }
    }


def make_readonly_engine(url: str) -> AsyncEngine:
    """One-connection read-only engine; the URL is never logged."""
    return create_async_engine(
        url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args=readonly_connect_args(),
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def _judgement_to_list(j: MoveJudgement) -> list[Any]:
    return [j.ply, j.good, j.es_before]


def _judgement_from_list(raw: Sequence[Any]) -> MoveJudgement:
    return MoveJudgement(int(raw[0]), bool(raw[1]), None if raw[2] is None else float(raw[2]))


@dataclass
class GameRecord:
    """One sampled game: provenance, the user's Elo/bucket, judged user moves, control tally."""

    game_id: int
    user_id: int
    is_guest: bool
    provenance: Provenance
    elo: float | None
    bucket: EloBucket | None
    judgements: list[MoveJudgement]
    control_agree: int
    control_total: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "user_id": self.user_id,
            "is_guest": self.is_guest,
            "provenance": self.provenance,
            "elo": self.elo,
            "bucket": self.bucket,
            "judgements": [_judgement_to_list(j) for j in self.judgements],
            "control_agree": self.control_agree,
            "control_total": self.control_total,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> GameRecord:
        return cls(
            game_id=int(raw["game_id"]),
            user_id=int(raw["user_id"]),
            is_guest=bool(raw["is_guest"]),
            provenance=raw["provenance"],
            elo=raw["elo"],
            bucket=raw["bucket"],
            judgements=[_judgement_from_list(j) for j in raw["judgements"]],
            control_agree=int(raw["control_agree"]),
            control_total=int(raw["control_total"]),
        )


@dataclass
class BlunderRecord:
    """One user-side blunder of a sampled, rated game, with its ES and the stored facepalm inputs.

    `has_line` records whether the game holds a stored engine line after the blunder (the
    game_positions.pv of ply + 1), so a NULL score with a spread can be told apart as "no line"
    or "line too short".
    """

    game_id: int
    ply: int
    bucket: EloBucket
    provenance: Provenance
    is_guest: bool
    case: MissCase
    is_miss: bool
    es_before: float | None
    es_played: float | None
    es_ref: float | None
    maia_played_prob: float | None
    maia_reply_spread: float | None
    line_loss_3: int | None
    line_mate_ply: int | None
    facepalm_score: float | None
    has_line: bool
    preceding: list[MoveJudgement]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "ply": self.ply,
            "bucket": self.bucket,
            "provenance": self.provenance,
            "is_guest": self.is_guest,
            "case": self.case,
            "is_miss": self.is_miss,
            "es_before": self.es_before,
            "es_played": self.es_played,
            "es_ref": self.es_ref,
            "maia_played_prob": self.maia_played_prob,
            "maia_reply_spread": self.maia_reply_spread,
            "line_loss_3": self.line_loss_3,
            "line_mate_ply": self.line_mate_ply,
            "facepalm_score": self.facepalm_score,
            "has_line": self.has_line,
            "preceding": [_judgement_to_list(j) for j in self.preceding],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> BlunderRecord:
        return cls(
            game_id=int(raw["game_id"]),
            ply=int(raw["ply"]),
            bucket=raw["bucket"],
            provenance=raw["provenance"],
            is_guest=bool(raw["is_guest"]),
            case=raw["case"],
            is_miss=bool(raw["is_miss"]),
            es_before=raw["es_before"],
            es_played=raw["es_played"],
            es_ref=raw["es_ref"],
            maia_played_prob=raw["maia_played_prob"],
            maia_reply_spread=raw["maia_reply_spread"],
            line_loss_3=raw["line_loss_3"],
            line_mate_ply=raw["line_mate_ply"],
            facepalm_score=raw["facepalm_score"],
            has_line=bool(raw["has_line"]),
            preceding=[_judgement_from_list(j) for j in raw["preceding"]],
        )


@dataclass
class UserGroup:
    """Exact per-user counts for one (provenance, platform, TC bucket, rating group) cell (D-23).

    rating_floor is the lower edge of a RATING_GROUP_WIDTH-wide group of the user's rating at
    game time. Only fully evaluated games of non-guest users are counted.
    """

    user_id: int
    provenance: Provenance
    platform: str
    time_control_bucket: str | None
    rating_floor: int
    games: int = 0
    user_blunders: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "provenance": self.provenance,
            "platform": self.platform,
            "time_control_bucket": self.time_control_bucket,
            "rating_floor": self.rating_floor,
            "games": self.games,
            "user_blunders": self.user_blunders,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> UserGroup:
        return cls(
            user_id=int(raw["user_id"]),
            provenance=raw["provenance"],
            platform=raw["platform"],
            time_control_bucket=raw["time_control_bucket"],
            rating_floor=int(raw["rating_floor"]),
            games=int(raw["games"]),
            user_blunders=int(raw["user_blunders"]),
        )


@dataclass
class GoodMoveOddness:
    """Maia's probability of one judged Good user move at the user's pinned Elo (D-17).

    Lives here (not in oddness.py) so the cached Collection can hold it without an import cycle.
    """

    game_id: int
    ply: int
    bucket: EloBucket
    es_before: float | None
    played_prob: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "ply": self.ply,
            "bucket": self.bucket,
            "es_before": self.es_before,
            "played_prob": self.played_prob,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> GoodMoveOddness:
        return cls(
            game_id=int(raw["game_id"]),
            ply=int(raw["ply"]),
            bucket=raw["bucket"],
            es_before=raw["es_before"],
            played_prob=float(raw["played_prob"]),
        )


@dataclass
class RunMeta:
    """Run metadata printed in the report header and stored in the cache."""

    db_name: str = ""
    # "dev" or "prod": lets --from-cache reopen the same target for the spot-check lookups.
    db_target: str = ""
    seed: int = 0
    oddness_sample: int = 0
    oddness_skipped: int = 0
    date: str = ""
    permille: int = PERMILLE_BASE
    limit_games: int | None = None
    games_sampled: int = 0
    games_gap_skipped: int = 0
    games_unrated: int = 0
    blunders_unrated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> RunMeta:
        return cls(**{k: raw[k] for k in cls().__dict__ if k in raw})


@dataclass
class Collection:
    """Everything the report needs, independent of the database."""

    meta: RunMeta = field(default_factory=RunMeta)
    games: list[GameRecord] = field(default_factory=list)
    blunders: list[BlunderRecord] = field(default_factory=list)
    user_groups: list[UserGroup] = field(default_factory=list)
    oddness: list[GoodMoveOddness] = field(default_factory=list)


@dataclass(frozen=True)
class GameRow:
    """The game columns the builder needs."""

    game_id: int
    user_id: int
    user_color: str
    white_rating: int | None
    black_rating: int | None
    platform: str
    time_control_bucket: str | None
    time_control_str: str | None
    has_lichess_evals: bool
    is_guest: bool


@dataclass(frozen=True)
class FlawRow:
    """The stored game_flaws columns the builder needs."""

    ply: int
    severity: int
    is_miss: bool
    maia_played_prob: float | None
    maia_reply_spread: float | None
    line_loss_3: int | None
    line_mate_ply: int | None
    facepalm_score: float | None
    has_line: bool


@dataclass
class BatchResult:
    """Records built from one batch plus the skip counters."""

    games: list[GameRecord] = field(default_factory=list)
    blunders: list[BlunderRecord] = field(default_factory=list)
    games_gap_skipped: int = 0
    games_unrated: int = 0
    blunders_unrated: int = 0


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

_SELECT_SAMPLE_SQL: str = f"""
SELECT g.id
FROM games g
WHERE g.full_evals_completed_at IS NOT NULL
  AND g.platform = ANY(CAST(:platforms AS text[]))
  AND {SHARD_RESIDUE_SQL} % CAST(:permille_base AS bigint) < CAST(:permille AS bigint)
ORDER BY g.id
{{limit_clause}}
"""


async def select_sample_game_ids(
    session: AsyncSession,
    *,
    permille: int,
    limit: int | None,
) -> list[int]:
    """Deterministic sample: fully evaluated games below the md5 residue cut, ordered by id."""
    params: dict[str, Any] = {
        "platforms": list(CALIBRATION_PLATFORMS),
        "permille_base": PERMILLE_BASE,
        "permille": permille,
    }
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit
    sql = _SELECT_SAMPLE_SQL.format(limit_clause=limit_clause)
    result = await session.execute(text(sql), params)
    return [int(row[0]) for row in result.all()]


# ---------------------------------------------------------------------------
# Batch load
# ---------------------------------------------------------------------------


async def _load_game_rows(session: AsyncSession, game_ids: Sequence[int]) -> list[GameRow]:
    stmt = (
        select(
            Game.id,
            Game.user_id,
            Game.user_color,
            Game.white_rating,
            Game.black_rating,
            Game.platform,
            Game.time_control_bucket,
            Game.time_control_str,
            Game.lichess_evals_at.isnot(None),
            User.is_guest,
        )
        .join(User, User.id == Game.user_id)
        .where(Game.id.in_(game_ids))
        .order_by(Game.id)
    )
    return [
        GameRow(
            game_id=row[0],
            user_id=row[1],
            user_color=row[2],
            white_rating=row[3],
            black_rating=row[4],
            platform=row[5],
            time_control_bucket=row[6],
            time_control_str=row[7],
            has_lichess_evals=bool(row[8]),
            is_guest=bool(row[9]),
        )
        for row in (await session.execute(stmt)).all()
    ]


async def _load_positions(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, list[GamePosition]]:
    stmt = (
        select(GamePosition)
        .options(
            load_only(
                GamePosition.game_id,
                GamePosition.ply,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
                GamePosition.move_san,
            )
        )
        .where(GamePosition.game_id.in_(game_ids))
        .order_by(GamePosition.game_id, GamePosition.ply)
    )
    by_game: dict[int, list[GamePosition]] = defaultdict(list)
    for position in (await session.execute(stmt)).scalars().all():
        by_game[position.game_id].append(position)
    return by_game


async def _load_flaws(session: AsyncSession, game_ids: Sequence[int]) -> dict[int, list[FlawRow]]:
    # The stored engine line after a flaw sits on the game_positions row at ply + 1 (the same
    # join the Maia hook uses); only its presence is read, never the line itself.
    next_position = aliased(GamePosition)
    has_line = func.coalesce(func.length(next_position.pv), 0) > 0
    stmt = (
        select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.severity,
            GameFlaw.is_miss,
            GameFlaw.maia_played_prob,
            GameFlaw.maia_reply_spread,
            GameFlaw.line_loss_3,
            GameFlaw.line_mate_ply,
            GameFlaw.facepalm_score,
            has_line,
        )
        .select_from(GameFlaw)
        .outerjoin(
            next_position,
            sa.and_(
                next_position.game_id == GameFlaw.game_id,
                next_position.user_id == GameFlaw.user_id,
                next_position.ply == GameFlaw.ply + 1,
            ),
        )
        .where(GameFlaw.game_id.in_(game_ids))
    )
    by_game: dict[int, list[FlawRow]] = defaultdict(list)
    for row in (await session.execute(stmt)).all():
        by_game[row[0]].append(FlawRow(*row[1:]))
    return by_game


# ---------------------------------------------------------------------------
# Record building
# ---------------------------------------------------------------------------


def _is_contiguous(positions: Sequence[GamePosition]) -> bool:
    """The classifier indexes positions by list index, so plies must run 0..n-1 without gaps."""
    return bool(positions) and all(p.ply == i for i, p in enumerate(positions))


def _user_rating(row: GameRow) -> int | None:
    return row.white_rating if row.user_color == "white" else row.black_rating


def _game_elo(row: GameRow) -> float | None:
    """The user's pinned Elo at game time (the classifier-side Maia convention), None if unrated."""
    rating = _user_rating(row)
    if rating is None:
        return None
    return pinned_elo_for_mover(
        raw_rating=rating,
        platform=cast(Platform, row.platform),
        time_control_bucket=cast(TimeControlBucket | None, row.time_control_bucket),
        is_correspondence=is_correspondence_time_control(row.time_control_str),
    )


def _blunder_record(
    row: GameRow,
    flaw: FlawRow,
    bucket: EloBucket,
    provenance: Provenance,
    all_moves: Mapping[int, Any],
    judgements: Sequence[MoveJudgement],
) -> BlunderRecord:
    es_before, es_played, es_ref = blunder_es(all_moves, flaw.ply)
    return BlunderRecord(
        game_id=row.game_id,
        ply=flaw.ply,
        bucket=bucket,
        provenance=provenance,
        is_guest=row.is_guest,
        case=miss_case(flaw.is_miss, es_ref, es_played),
        is_miss=flaw.is_miss,
        es_before=es_before,
        es_played=es_played,
        es_ref=es_ref,
        maia_played_prob=flaw.maia_played_prob,
        maia_reply_spread=flaw.maia_reply_spread,
        line_loss_3=flaw.line_loss_3,
        line_mate_ply=flaw.line_mate_ply,
        facepalm_score=flaw.facepalm_score,
        has_line=flaw.has_line,
        preceding=[j for j in judgements if j.ply < flaw.ply][-PRECEDING_MOVES_KEPT:],
    )


def build_game_records(
    rows: Sequence[GameRow],
    positions_by_game: Mapping[int, Sequence[GamePosition]],
    flaws_by_game: Mapping[int, Sequence[FlawRow]],
) -> BatchResult:
    """Build per-game and per-blunder records from loaded rows (D-13).

    Severities and ES come from the classifier's own ``_run_all_moves_pass``; a game whose
    positions have a ply gap is skipped and counted, an unrated game keeps its GameRecord
    (bucket None) but contributes no blunder records.
    """
    result = BatchResult()
    for row in rows:
        positions = list(positions_by_game.get(row.game_id, ()))
        if not _is_contiguous(positions):
            result.games_gap_skipped += 1
            continue
        all_moves = _run_all_moves_pass(positions)
        move_plies = [p.ply for p in positions if p.move_san]
        user_is_white = row.user_color == "white"
        judgements = user_move_judgements(all_moves, move_plies, user_is_white)
        elo = _game_elo(row)
        bucket = elo_bucket(elo) if elo is not None else None
        provenance: Provenance = "lichess" if row.has_lichess_evals else "engine"
        flaws = flaws_by_game.get(row.game_id, ())
        agree, total = flaw_control(all_moves, {f.ply: f.severity for f in flaws})
        result.games.append(
            GameRecord(
                game_id=row.game_id,
                user_id=row.user_id,
                is_guest=row.is_guest,
                provenance=provenance,
                elo=elo,
                bucket=bucket,
                judgements=judgements,
                control_agree=agree,
                control_total=total,
            )
        )
        user_blunders = [
            f
            for f in flaws
            if f.severity == BLUNDER_SEVERITY and mover_is_white_at_ply(f.ply) == user_is_white
        ]
        if bucket is None:
            result.games_unrated += 1
            result.blunders_unrated += len(user_blunders)
            continue
        result.blunders.extend(
            _blunder_record(row, f, bucket, provenance, all_moves, judgements)
            for f in sorted(user_blunders, key=lambda f: f.ply)
        )
    return result


async def collect_records(session: AsyncSession, game_ids: Sequence[int]) -> BatchResult:
    """Load one batch with three short SELECTs and build its records."""
    rows = await _load_game_rows(session, game_ids)
    positions = await _load_positions(session, game_ids)
    flaws = await _load_flaws(session, game_ids)
    return build_game_records(rows, positions, flaws)


async def collect_sample(
    session: AsyncSession,
    game_ids: Sequence[int],
    batch_games: int,
    meta: RunMeta,
) -> Collection:
    """Collect every batch of the sample into one Collection (meta counters are updated)."""
    collection = Collection(meta=meta)
    for start in range(0, len(game_ids), batch_games):
        batch = await collect_records(session, game_ids[start : start + batch_games])
        collection.games.extend(batch.games)
        collection.blunders.extend(batch.blunders)
        meta.games_gap_skipped += batch.games_gap_skipped
        meta.games_unrated += batch.games_unrated
        meta.blunders_unrated += batch.blunders_unrated
    meta.games_sampled = len(collection.games)
    return collection


# ---------------------------------------------------------------------------
# Exact per-user aggregates (D-23): SELECT only, one statement each
# ---------------------------------------------------------------------------


def _user_rating_expr() -> sa.ColumnElement[int]:
    return case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)


def _group_columns() -> list[Any]:
    rating = _user_rating_expr()
    rating_floor = (rating - rating % RATING_GROUP_WIDTH).label("rating_floor")
    lichess = Game.lichess_evals_at.isnot(None).label("has_lichess_evals")
    return [
        Game.user_id.label("user_id"),
        lichess,
        Game.platform.label("platform"),
        Game.time_control_bucket.label("time_control_bucket"),
        rating_floor,
    ]


def _eligible_game_predicates() -> list[Any]:
    """Fully evaluated, rated games of non-guest users on the calibration platforms."""
    return [
        User.is_guest.is_(False),
        Game.full_evals_completed_at.isnot(None),
        Game.platform.in_(CALIBRATION_PLATFORMS),
        _user_rating_expr().isnot(None),
    ]


async def fetch_user_groups(session: AsyncSession) -> list[UserGroup]:
    """Exact per-user game and user-side blunder counts grouped by (provenance, platform, TC, rating)."""
    columns = _group_columns()
    group_by = [c for c in columns]
    games_stmt = (
        select(*columns, func.count().label("n"))
        .select_from(Game)
        .join(User, User.id == Game.user_id)
        .where(*_eligible_game_predicates())
        .group_by(*group_by)
    )
    # User parity via the single-source expression (negated), never inline ply math.
    blunders_stmt = (
        select(*columns, func.count().label("n"))
        .select_from(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .join(User, User.id == Game.user_id)
        .where(
            *_eligible_game_predicates(),
            GameFlaw.severity == BLUNDER_SEVERITY,
            ~is_opponent_expr(GameFlaw.ply, Game.user_color),
        )
        .group_by(*group_by)
    )
    groups: dict[tuple[Any, ...], UserGroup] = {}

    def _group(row: Any) -> UserGroup:
        key = tuple(row[:5])
        if key not in groups:
            groups[key] = UserGroup(
                user_id=int(row[0]),
                provenance="lichess" if row[1] else "engine",
                platform=row[2],
                time_control_bucket=row[3],
                rating_floor=int(row[4]),
            )
        return groups[key]

    for row in (await session.execute(games_stmt)).all():
        _group(row).games = int(row[5])
    for row in (await session.execute(blunders_stmt)).all():
        _group(row).user_blunders = int(row[5])
    return sorted(
        groups.values(),
        key=lambda g: (
            g.user_id,
            g.provenance,
            g.platform,
            str(g.time_control_bucket),
            g.rating_floor,
        ),
    )


def group_elo_bucket(group: UserGroup) -> EloBucket:
    """Bucket of a rating group, using the group midpoint as the raw rating (an approximation)."""
    elo = pinned_elo_for_mover(
        raw_rating=group.rating_floor + RATING_GROUP_WIDTH // 2,
        platform=cast(Platform, group.platform),
        time_control_bucket=cast(TimeControlBucket | None, group.time_control_bucket),
        is_correspondence=False,
    )
    return elo_bucket(elo)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def collection_to_dict(collection: Collection) -> dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "meta": collection.meta.to_dict(),
        "games": [g.to_dict() for g in collection.games],
        "blunders": [b.to_dict() for b in collection.blunders],
        "user_groups": [u.to_dict() for u in collection.user_groups],
        "oddness": [o.to_dict() for o in collection.oddness],
    }


def collection_from_dict(raw: Mapping[str, Any]) -> Collection:
    if raw.get("version") != CACHE_VERSION:
        raise ValueError("unsupported cache version")
    return Collection(
        meta=RunMeta.from_dict(raw["meta"]),
        games=[GameRecord.from_dict(g) for g in raw["games"]],
        blunders=[BlunderRecord.from_dict(b) for b in raw["blunders"]],
        user_groups=[UserGroup.from_dict(u) for u in raw["user_groups"]],
        # Caches written before the oddness sample existed have no such key.
        oddness=[GoodMoveOddness.from_dict(o) for o in raw.get("oddness", [])],
    )


def write_cache(collection: Collection, path: Path) -> None:
    """Write the collection as JSON (floats round-trip exactly)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection_to_dict(collection)))


def read_cache(path: Path) -> Collection:
    return collection_from_dict(json.loads(path.read_text()))
