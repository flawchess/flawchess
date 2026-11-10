"""Tests for the blunder-check calibration sampler and report (SEED-261108-dk0, Phase 248, plan 04).

DB-backed tests commit games through a session maker bound to the per-run test DB and delete
them in teardown. The sampler's selector is global, so every assertion about its output is
scoped to this module's own game ids (other modules' games leak in under -n auto).
"""

from __future__ import annotations

import datetime
import random
import uuid
from pathlib import Path
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

import chess
import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services import maia_engine
from scripts.blunder_check.metrics import (
    HAZARD,
    WINDOW_LENGTHS,
    EloBucket,
    MissCase,
    MoveJudgement,
    Provenance,
    blunder_fits_position,
    hazard_position_weights,
    in_band,
)
from scripts.blunder_check.oddness import (
    GoodMoveTarget,
    score_good_moves,
    select_good_moves,
    summarize_oddness,
)
from scripts.blunder_check.render import (
    ReportParams,
    render_report,
    section_eval_band,
    section_findability_grid,
    section_herring_supply,
    section_provenance,
    section_recommended_constants,
    section_supply_per_user,
    section_window_fit,
)
from scripts.blunder_check.spot_check import (
    JudgedLine,
    SpotCheckParams,
    SpotWindow,
    SpotWindowDetail,
    WindowShape,
    draw_window_shape,
    fetch_window_details,
    pick_windows,
    render_spot_check,
)
from scripts.blunder_check.sample import (
    PERMILLE_BASE,
    BlunderRecord,
    Collection,
    GameRecord,
    GoodMoveOddness,
    RunMeta,
    UserGroup,
    collect_records,
    fetch_user_groups,
    make_readonly_engine,
    read_cache,
    select_sample_game_ids,
    write_cache,
)

from scripts.blunder_check_calibration import EXIT_MAIA_UNAVAILABLE
from scripts.blunder_check_calibration import main as cli_main
from tests.services.maia_fakes import fake_full_policy

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 248_001

_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 *"
_SAN = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]
HOLD_CP = 100
GIFT_CP = 500
OPPONENT_BLUNDER_PLY = 7
USER_BLUNDER_PLY = 8
BEST_PROB = 0.5
REFUTATION_PROB = 0.1

MakeGame = Callable[..., Awaitable[int]]


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def make_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[MakeGame, None]:
    """Factory for committed, fully evaluated games with stored flaws; cleans up in teardown."""
    created: list[int] = []
    async with session_factory() as session:
        existing = (
            (await session.execute(select(User).where(User.id == _TEST_USER_ID)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"blunder-check-cal-{_TEST_USER_ID}@example.com",
                    hashed_password="x",
                )
            )
            await session.commit()

    async def _make(
        *,
        white_rating: int | None = 1500,
        lichess_evals: bool = False,
        user_id: int = _TEST_USER_ID,
    ) -> int:
        evals = [HOLD_CP] * len(_SAN)
        evals[OPPONENT_BLUNDER_PLY] = GIFT_CP
        async with session_factory() as session:
            game = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=f"blunder-check-cal-{uuid.uuid4().hex}",
                pgn=_PGN,
                result="1-0",
                user_color="white",
                white_rating=white_rating,
                black_rating=1600,
                time_control_str="300+0",
                time_control_bucket="blitz",
                time_control_seconds=300,
                base_time_seconds=300,
                increment_seconds=0.0,
                rated=True,
                is_computer_game=False,
                full_evals_completed_at=datetime.datetime.now(datetime.timezone.utc),
                lichess_evals_at=datetime.datetime.now(datetime.timezone.utc)
                if lichess_evals
                else None,
            )
            session.add(game)
            await session.flush()
            game_id = game.id
            for ply, cp in enumerate(evals):
                session.add(
                    GamePosition(
                        user_id=user_id,
                        game_id=game_id,
                        ply=ply,
                        eval_cp=cp,
                        eval_mate=None,
                        clock_seconds=None,
                        phase=1,
                        full_hash=ply,
                        white_hash=ply,
                        black_hash=ply,
                        endgame_class=None,
                        move_san=_SAN[ply],
                    )
                )
            await session.flush()
            for ply, is_miss in ((OPPONENT_BLUNDER_PLY, False), (USER_BLUNDER_PLY, True)):
                is_user_ply = ply == USER_BLUNDER_PLY
                session.add(
                    GameFlaw(
                        user_id=user_id,
                        game_id=game_id,
                        ply=ply,
                        severity=2,
                        tempo=None,
                        phase=1,
                        is_miss=is_miss,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen="",
                        maia_best_prob=BEST_PROB if is_user_ply else None,
                        maia_best_rank=1 if is_user_ply else None,
                        maia_refutation_prob=REFUTATION_PROB if is_user_ply else None,
                        maia_refutation_rank=3 if is_user_ply else None,
                    )
                )
            await session.commit()
        created.append(game_id)
        return game_id

    yield _make

    async with session_factory() as session:
        if created:
            await session.execute(delete(Game).where(Game.id.in_(created)))
        await session.execute(delete(User).where(User.id == _TEST_USER_ID))
        await session.commit()


class TestReadOnlyEngine:
    @pytest.mark.asyncio
    async def test_session_is_read_only_and_writes_raise(self, test_engine: Any) -> None:
        engine = make_readonly_engine(test_engine.url.render_as_string(hide_password=False))
        try:
            async with engine.connect() as conn:
                shown = (
                    await conn.execute(text("SHOW default_transaction_read_only"))
                ).scalar_one()
                assert shown == "on"
                with pytest.raises(DBAPIError):
                    await conn.execute(text("UPDATE games SET pgn = pgn WHERE false"))
        finally:
            await engine.dispose()


class TestTracer:
    @pytest.mark.asyncio
    async def test_sample_to_records_to_report(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game()
        async with session_factory() as session:
            sampled = await select_sample_game_ids(session, permille=PERMILLE_BASE, limit=None)
            assert game_id in sampled
            none_sampled = await select_sample_game_ids(session, permille=0, limit=None)
            assert game_id not in none_sampled
            batch = await collect_records(session, [game_id])

        assert batch.games_gap_skipped == 0
        [record] = batch.games
        assert record.provenance == "engine"
        assert record.bucket == "1200-1599"
        # Both stored blunders match the recomputed severities.
        assert (record.control_agree, record.control_total) == (2, 2)

        [blunder] = batch.blunders
        assert blunder.ply == USER_BLUNDER_PLY
        assert blunder.case == "pure_miss"
        assert blunder.is_miss
        assert blunder.maia_best_prob == pytest.approx(BEST_PROB)
        assert blunder.maia_refutation_rank == 3

        collection = Collection(
            meta=RunMeta(db_name="test", date="2026-11-09", games_sampled=1),
            games=batch.games,
            blunders=batch.blunders,
        )
        report = render_report(collection, ReportParams())
        for heading in (
            "## How to read this report",
            "## Sample",
            "## Control",
            "## Cases by Elo bucket",
        ):
            assert report.count(heading) == 1

    @pytest.mark.asyncio
    async def test_unrated_game_keeps_record_but_has_no_blunder_record(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game(white_rating=None)
        async with session_factory() as session:
            batch = await collect_records(session, [game_id])
        assert batch.games_unrated == 1
        assert batch.blunders_unrated == 1
        assert batch.blunders == []
        assert batch.games[0].bucket is None

    @pytest.mark.asyncio
    async def test_game_with_ply_gap_is_skipped_and_counted(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game()
        async with session_factory() as session:
            await session.execute(
                delete(GamePosition).where(GamePosition.game_id == game_id, GamePosition.ply == 4)
            )
            await session.commit()
            batch = await collect_records(session, [game_id])
        assert batch.games_gap_skipped == 1
        assert batch.games == []


# ---------------------------------------------------------------------------
# Hand-built collections (no DB): the report sections
# ---------------------------------------------------------------------------

MID_ES = 0.5
OUT_OF_BAND_ES = 0.97
BUCKET: EloBucket = "1200-1599"
PARAMS = ReportParams(refutation_threshold=0.20, miss_threshold=0.20, band_low=0.10, band_high=0.90)


def _judgements(*es_values: float, good: bool = True, start_ply: int = 0) -> list[MoveJudgement]:
    """User moves on even plies (white user) with the given pre-move ES values."""
    return [MoveJudgement(start_ply + 2 * i, good, es) for i, es in enumerate(es_values)]


def _blunder(
    *,
    case: MissCase = "allowed",
    refutation: tuple[float | None, int | None] = (None, None),
    best: tuple[float | None, int | None] = (None, None),
    preceding: list[MoveJudgement] | None = None,
    es_before: float | None = MID_ES,
    bucket: EloBucket = BUCKET,
    provenance: Provenance = "engine",
    is_guest: bool = False,
) -> BlunderRecord:
    return BlunderRecord(
        game_id=1,
        ply=20,
        bucket=bucket,
        provenance=provenance,
        is_guest=is_guest,
        case=case,
        is_miss=case != "allowed",
        es_before=es_before,
        es_played=0.2,
        es_ref=0.5,
        maia_played_prob=None,
        maia_played_rank=None,
        maia_best_prob=best[0],
        maia_best_rank=best[1],
        maia_refutation_prob=refutation[0],
        maia_refutation_rank=refutation[1],
        preceding=preceding or [],
    )


def _game(
    judgements: list[MoveJudgement],
    *,
    provenance: Provenance = "engine",
    bucket: EloBucket = BUCKET,
    user_id: int = 1,
) -> GameRecord:
    return GameRecord(
        game_id=user_id,
        user_id=user_id,
        is_guest=False,
        provenance=provenance,
        elo=1500.0,
        bucket=bucket,
        judgements=judgements,
        control_agree=0,
        control_total=0,
    )


def _rows(section: str) -> list[list[str]]:
    """Parsed markdown table rows (header and separator dropped) of the first table."""
    lines = [line for line in section.splitlines() if line.startswith("|")]
    return [[c.strip() for c in line.strip("|").split("|")] for line in lines[2:]]


def _row(section: str, label: str) -> list[str]:
    return next(r for r in _rows(section) if r[0] == label)


class TestFindabilityGrid:
    def test_two_of_four_allowed_pass_at_r_020(self) -> None:
        blunders = [
            _blunder(refutation=(0.05, 4)),
            _blunder(refutation=(0.10, 3)),
            _blunder(refutation=(0.25, 2)),
            _blunder(refutation=(0.50, 1)),
        ]
        section = section_findability_grid(Collection(blunders=blunders), PARAMS)
        row = _row(section, BUCKET)
        # columns: bucket, n scored, unscored, rank-1 only, then the grid 0.05 ... 0.50
        assert row[1:4] == ["4", "0", "25.0% (n=4)"]
        assert row[4 + 3] == "50.0% (n=4)"  # grid index 3 is 0.20

    def test_unscored_pairs_are_counted_and_excluded_from_denominators(self) -> None:
        blunders = [_blunder(refutation=(0.5, 1)), _blunder(), _blunder()]
        section = section_findability_grid(Collection(blunders=blunders), PARAMS)
        row = _row(section, BUCKET)
        assert row[1:3] == ["1", "2"]
        assert row[4 + 3] == "100.0% (n=1)"

    def test_mixed_passes_if_either_pair_passes(self) -> None:
        blunders = [
            _blunder(case="mixed", refutation=(0.01, 9), best=(0.6, 2)),
            _blunder(case="mixed", refutation=(0.01, 9), best=(0.01, 9)),
        ]
        section = section_findability_grid(Collection(blunders=blunders), PARAMS)
        mixed_row = [r for r in _rows(section) if r[0] == BUCKET][-1]
        assert mixed_row[4 + 3] == "50.0% (n=2)"


class TestWindowFit:
    def test_three_good_in_band_moves_fit_positions_one_to_four_not_five(self) -> None:
        blunder = _blunder(refutation=(0.5, 1), preceding=_judgements(MID_ES, MID_ES, MID_ES))
        section = section_window_fit(Collection(blunders=[blunder]), PARAMS)
        row = _row(section, BUCKET)
        assert row[1] == "1"
        assert row[2:7] == [
            "100.0% (n=1)",
            "100.0% (n=1)",
            "100.0% (n=1)",
            "100.0% (n=1)",
            "0.0% (n=1)",
        ]
        # Hazard-weighted average with the D-16 normalized weights: 1 - 0.037 for position 5.
        assert row[7] == "96.3% (n=1)"

    def test_out_of_band_preceding_move_blocks_longer_positions(self) -> None:
        # Detects dropping the band check on the preceding judged moves.
        fits_all = _blunder(refutation=(0.5, 1), preceding=_judgements(MID_ES, MID_ES, MID_ES))
        fits_first_only = _blunder(
            refutation=(0.5, 1), preceding=_judgements(MID_ES, MID_ES, OUT_OF_BAND_ES)
        )
        section = section_window_fit(Collection(blunders=[fits_all, fits_first_only]), PARAMS)
        row = _row(section, BUCKET)
        assert row[2] == "100.0% (n=2)"
        assert row[3] == "50.0% (n=2)"
        assert row[4] == "50.0% (n=2)"

    def test_not_good_preceding_move_blocks_longer_positions(self) -> None:
        preceding = [MoveJudgement(14, False, MID_ES), MoveJudgement(16, True, MID_ES)]
        blunder = _blunder(refutation=(0.5, 1), preceding=preceding)
        row = _row(section_window_fit(Collection(blunders=[blunder]), PARAMS), BUCKET)
        assert row[3] == "100.0% (n=1)"
        assert row[4] == "0.0% (n=1)"


class TestHerringSupply:
    def test_disjoint_windows_per_length(self) -> None:
        seven_good = _judgements(*[MID_ES] * 7)
        broken = [*seven_good, MoveJudgement(14, False, MID_ES)]
        section = section_herring_supply(Collection(games=[_game(broken)]), PARAMS)
        row = _row(section, BUCKET)
        # L=3: 2 windows, L=4: 1, L=5: 1; uniform mean over lengths = 4/3.
        assert row[1:5] == ["1", "2.000", "1.000", "1.000"]
        assert row[5] == "1.333"

    def test_band_applies_to_every_judged_move(self) -> None:
        judgements = _judgements(MID_ES, MID_ES, OUT_OF_BAND_ES, MID_ES, MID_ES, MID_ES)
        row = _row(section_herring_supply(Collection(games=[_game(judgements)]), PARAMS), BUCKET)
        assert row[1:5] == ["1", "1.000", "0.000", "0.000"]


class TestEvalBand:
    def test_share_in_band_per_candidate(self) -> None:
        blunders = [
            _blunder(refutation=(0.5, 1), es_before=0.5),
            _blunder(refutation=(0.5, 1), es_before=0.97),
        ]
        section = section_eval_band(Collection(blunders=blunders), PARAMS)
        rows = _rows(section)
        full_band = next(r for r in rows if r[0] == "[0.00, 1.00]")
        tight_band = next(r for r in rows if r[0] == "[0.10, 0.90]")
        assert full_band[-1] == "100.0% (n=2)"  # last column is the pooled "all" row
        assert tight_band[-1] == "50.0% (n=2)"


class TestSupplyPerUser:
    def _collection(self) -> Collection:
        usable = [_blunder(refutation=(0.5, 1)) for _ in range(10)]
        groups = [
            UserGroup(1, "engine", "lichess", "blitz", 1500, games=10, user_blunders=100),
            UserGroup(2, "engine", "lichess", "blitz", 1500, games=10, user_blunders=200),
        ]
        return Collection(blunders=usable, user_groups=groups)

    def test_percentiles_and_users_under_minimum(self) -> None:
        section = section_supply_per_user(self._collection(), PARAMS)
        # Position 1 only fits (no preceding moves): fit share = normalized weight of position 1.
        assert "estimate" in section.lower()
        row = _row(section, "usable blunder windows")
        low, high = 100 * 0.3790, 200 * 0.3790
        assert float(row[3]) == pytest.approx((low + high) / 2, abs=0.2)  # p50 of two users
        assert "1 of 2" in section  # user 1 (about 38 windows) is under MIN_USER_WINDOWS = 50

    def test_pure_misses_are_capped(self) -> None:
        pure = [_blunder(case="pure_miss", best=(0.5, 1)) for _ in range(10)]
        groups = [UserGroup(1, "engine", "lichess", "blitz", 1500, games=1, user_blunders=100)]
        section = section_supply_per_user(Collection(blunders=pure, user_groups=groups), PARAMS)
        # No non-pure blunders at all: the cap on pure misses is 0 of the total.
        row = _row(section, "usable blunder windows")
        assert float(row[3]) == pytest.approx(0.0)


class TestProvenance:
    def test_provenance_rows_differ(self) -> None:
        engine = _blunder(
            refutation=(0.5, 1), preceding=_judgements(MID_ES, MID_ES, MID_ES), provenance="engine"
        )
        lichess = _blunder(refutation=(0.5, 1), provenance="lichess")
        collection = Collection(
            blunders=[engine, lichess],
            games=[
                _game(_judgements(*[MID_ES] * 3), provenance="engine"),
                _game(_judgements(*[MID_ES] * 3), provenance="lichess", user_id=2),
            ],
        )
        section = section_provenance(collection, PARAMS)
        engine_row = _row(section, "engine")
        lichess_row = _row(section, "lichess")
        assert engine_row[1] == "1" and lichess_row[1] == "1"
        assert engine_row[4] != lichess_row[4]  # hazard-weighted fit share


class TestCacheRoundTrip:
    def test_cache_renders_byte_identical_markdown(self, tmp_path: Path) -> None:
        collection = Collection(
            meta=RunMeta(db_name="x", date="2026-11-09", games_sampled=2),
            games=[_game(_judgements(0.31, 0.5, 0.77))],
            blunders=[
                _blunder(
                    refutation=(0.123456789, 2),
                    preceding=_judgements(MID_ES, 0.4),
                )
            ],
            user_groups=[
                UserGroup(1, "engine", "lichess", "blitz", 1500, games=3, user_blunders=4)
            ],
        )
        path = tmp_path / "cache.json"
        write_cache(collection, path)
        restored = read_cache(path)
        assert render_report(restored, PARAMS) == render_report(collection, PARAMS)
        assert restored.blunders[0].maia_refutation_prob == 0.123456789


class TestUserGroupAggregates:
    @pytest.mark.asyncio
    async def test_exact_counts_for_non_guest_users_only(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        await make_game()
        guest_id = _TEST_USER_ID + 1
        async with session_factory() as session:
            session.add(
                User(
                    id=guest_id,
                    email=f"blunder-check-cal-{guest_id}@example.com",
                    hashed_password="x",
                    is_guest=True,
                )
            )
            await session.commit()
        try:
            guest_game = await make_game(user_id=guest_id)
            async with session_factory() as session:
                groups = await fetch_user_groups(session)
            mine = [g for g in groups if g.user_id == _TEST_USER_ID]
            assert [
                (g.provenance, g.platform, g.rating_floor, g.games, g.user_blunders) for g in mine
            ] == [("engine", "lichess", 1500, 1, 1)]
            assert all(g.user_id != guest_id for g in groups)
            assert guest_game
        finally:
            async with session_factory() as session:
                await session.execute(delete(Game).where(Game.user_id == guest_id))
                await session.execute(delete(User).where(User.id == guest_id))
                await session.commit()


def test_hazard_constant_is_the_seed_value() -> None:
    assert HAZARD == pytest.approx(0.265)


# ---------------------------------------------------------------------------
# Plan 05: arrow oddness (D-17)
# ---------------------------------------------------------------------------

GOOD_PROBS = (0.5, 0.6, 0.7, 0.8)
BLUNDER_PROBS = (0.1, 0.2, 0.6, 0.9)
# Hand count over the 16 (good, blunder) pairs: 2 + 2.5 + 3 + 3 = 10.5 wins.
EXPECTED_AUC = 10.5 / 16
ODDNESS_ELO = 1500.0


def _good(
    prob: float, rank: int = 2, *, bucket: EloBucket = BUCKET, es_before: float | None = MID_ES
) -> GoodMoveOddness:
    return GoodMoveOddness(
        game_id=1, ply=0, bucket=bucket, es_before=es_before, played_prob=prob, played_rank=rank
    )


def _scored_blunder(prob: float, rank: int, *, bucket: EloBucket = BUCKET) -> BlunderRecord:
    blunder = _blunder(
        case="allowed", refutation=(0.5, 1), bucket=bucket, preceding=_judgements(0.5, 0.5, 0.5)
    )
    blunder.maia_played_prob = prob
    blunder.maia_played_rank = rank
    return blunder


class TestOddnessSummary:
    def test_known_auc_quartiles_and_rank_one_shares(self) -> None:
        good = [_good(p, rank=1 if p >= 0.7 else 2) for p in GOOD_PROBS]
        blunders = [_scored_blunder(p, rank=1 if p == 0.9 else 3) for p in BLUNDER_PROBS]
        row = summarize_oddness(good, blunders)[BUCKET]
        assert (row.n_good, row.n_blunder) == (4, 4)
        assert row.auc == pytest.approx(EXPECTED_AUC)
        assert row.good_quartiles == pytest.approx((0.575, 0.65, 0.725))
        assert row.blunder_quartiles == pytest.approx((0.175, 0.4, 0.675))
        assert row.good_rank1_share == pytest.approx(0.5)
        assert row.blunder_rank1_share == pytest.approx(0.25)

    def test_empty_side_gives_no_auc(self) -> None:
        row = summarize_oddness([_good(0.5)], [])[BUCKET]
        assert row.auc is None
        assert row.blunder_quartiles is None

    def test_blunder_without_stored_pair_is_ignored(self) -> None:
        unscored = _blunder(case="allowed")
        row = summarize_oddness([_good(0.5)], [unscored])[BUCKET]
        assert row.n_blunder == 0


def _oddness_game(game_id: int, n_moves: int, *, bucket: EloBucket = BUCKET) -> GameRecord:
    judgements = [MoveJudgement(2 * i, True, MID_ES) for i in range(n_moves)]
    judgements.append(MoveJudgement(2 * n_moves, False, MID_ES))
    return GameRecord(
        game_id=game_id,
        user_id=game_id,
        is_guest=False,
        provenance="engine",
        elo=ODDNESS_ELO,
        bucket=bucket,
        judgements=judgements,
        control_agree=0,
        control_total=0,
    )


class TestOddnessSelectGoodMoves:
    def test_deterministic_for_a_fixed_seed_and_capped_per_bucket(self) -> None:
        collection = Collection(games=[_oddness_game(g, 10) for g in range(1, 6)])
        first = select_good_moves(collection, 7, seed=3)
        assert first == select_good_moves(collection, 7, seed=3)
        assert len(first) == 7
        assert first != select_good_moves(collection, 7, seed=4)

    def test_only_good_non_guest_rated_moves_are_candidates(self) -> None:
        guest = _oddness_game(1, 5)
        guest.is_guest = True
        unrated = _oddness_game(2, 5)
        unrated.bucket = None
        rated = _oddness_game(3, 5)
        picked = select_good_moves(Collection(games=[guest, unrated, rated]), 100, seed=1)
        assert {t.game_id for t in picked} == {3}
        # 5 Good moves; the trailing not-Good move is never a candidate.
        assert len(picked) == 5
        assert all(t.ply != 10 for t in picked)

    def test_small_bucket_is_taken_whole(self) -> None:
        collection = Collection(games=[_oddness_game(1, 3)])
        assert len(select_good_moves(collection, 1500, seed=1)) == 3


class TestOddnessScoreGoodMoves:
    @pytest.mark.asyncio
    async def test_probability_comes_from_full_policy_on_the_exact_replayed_board(
        self,
        make_game: MakeGame,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        game_id = await make_game()
        monkeypatch.setattr(maia_engine, "full_policy", fake_full_policy)
        ply = 8
        targets = [
            GoodMoveTarget(game_id, ply, BUCKET, MID_ES),
            GoodMoveTarget(game_id, 99, BUCKET, MID_ES),
        ]
        scored = await score_good_moves(session_factory, targets, {game_id: ODDNESS_ELO})

        assert scored.skipped == 1  # ply 99 is beyond the mainline
        [record] = scored.records
        board = chess.Board()
        for san in _SAN[:ply]:
            board.push_san(san)
        expected = fake_full_policy(board.fen(), ODDNESS_ELO)
        assert record.played_prob == pytest.approx(expected["e1g1"])
        ranked = sorted(expected.values(), reverse=True)
        assert record.played_rank == 1 + ranked.index(expected["e1g1"])

    @pytest.mark.asyncio
    async def test_missing_policy_raises(
        self,
        make_game: MakeGame,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        game_id = await make_game()
        monkeypatch.setattr(maia_engine, "full_policy", lambda fen, elo: None)
        with pytest.raises(RuntimeError):
            await score_good_moves(
                session_factory, [GoodMoveTarget(game_id, 4, BUCKET, MID_ES)], {game_id: 1500.0}
            )


class TestArrowOddnessSection:
    def test_section_filters_good_moves_by_band_and_prints_auc(self) -> None:
        in_band_good = [_good(p) for p in GOOD_PROBS]
        out_of_band = [_good(0.01, es_before=OUT_OF_BAND_ES)]
        collection = Collection(
            meta=RunMeta(date="2026-11-09"),
            blunders=[_scored_blunder(p, 3) for p in BLUNDER_PROBS],
            oddness=[*in_band_good, *out_of_band],
        )
        report = render_report(collection, PARAMS)
        assert report.count("## Arrow oddness") == 1
        assert report.count("## Recommended constants") == 1
        assert "recommendation only" in report
        row = _row(report.split("## Arrow oddness")[1], BUCKET)
        assert row[1] == "4"  # the out-of-band Good move is dropped
        assert row[-1] == f"{EXPECTED_AUC:.3f}"

    def test_baseline_table_separates_band_and_findability_selection(self) -> None:
        # Drill: the 4 usable blunders vs the 4 in-band Good moves (EXPECTED_AUC).
        usable = [_scored_blunder(p, 3) for p in BLUNDER_PROBS]
        # Not findable (refutation far below R) but in band: counted by "band only" only.
        unfindable = _blunder(case="allowed", refutation=(0.01, 9))
        unfindable.maia_played_prob, unfindable.maia_played_rank = 0.95, 1
        # Findable but out of band: counted by "unselected" only.
        out_of_band = _scored_blunder(0.95, 1)
        out_of_band.es_before = OUT_OF_BAND_ES
        collection = Collection(
            meta=RunMeta(date="2026-11-10"),
            blunders=[*usable, unfindable, out_of_band],
            oddness=[*(_good(p) for p in GOOD_PROBS), _good(0.01, es_before=OUT_OF_BAND_ES)],
        )
        section = render_report(collection, PARAMS).split("### Drill against the unselected")[1]
        row = _row(section, BUCKET)
        # Unselected: 5 Good x 6 blunders, 10.5 wins (the 0.01 Good and the 0.95s add none).
        unselected_auc = 10.5 / 30
        # Band only: 4 Good x 5 blunders, 10.5 wins.
        band_auc = 10.5 / 20
        assert row[1:3] == ["5", "6"]
        assert row[3] == f"{unselected_auc:.3f}"
        assert row[4] == f"{band_auc:.3f}"
        assert row[5] == f"{EXPECTED_AUC:.3f}"
        assert row[6] == f"{EXPECTED_AUC - unselected_auc:+.3f}"
        assert _row(section, "all")[5] == f"{EXPECTED_AUC:.3f}"

    def test_oddness_records_survive_the_cache(self, tmp_path: Path) -> None:
        collection = Collection(
            meta=RunMeta(date="2026-11-09", db_target="dev", seed=7, oddness_sample=4),
            games=[_game(_judgements(0.5, 0.5, 0.5))],
            oddness=[_good(p) for p in GOOD_PROBS],
        )
        path = tmp_path / "cache.json"
        write_cache(collection, path)
        restored = read_cache(path)
        assert restored.oddness == collection.oddness
        assert restored.meta.db_target == "dev"
        assert render_report(restored, PARAMS) == render_report(collection, PARAMS)


class TestCliMaiaLifecycle:
    def test_exits_3_when_maia_is_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _noop_start(*, intra_op_num_threads: int | None = None) -> None:
            return None

        monkeypatch.setattr(maia_engine, "start_maia", _noop_start)
        monkeypatch.setattr(maia_engine, "_session", None)
        code = cli_main(["--db", "dev", "--out-dir", str(tmp_path), "--oddness-sample", "5"])
        assert code == EXIT_MAIA_UNAVAILABLE == 3
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Plan 05: spot-check export (D-18) and Recommended constants
# ---------------------------------------------------------------------------

SHAPE_DRAWS = 20_000
SHARE_TOLERANCE = 0.01
SPOT_PER_BUCKET = 12
PUBLIC_LINK = "https://lichess.org/abc12345"
MISSED_BEST_UCI = "d2d3"
REPLY_UCI = "b7b5"
BEST_RANK = 1


def _fit_blunder(game_id: int, *, preceding_len: int, bucket: EloBucket = BUCKET) -> BlunderRecord:
    """An allowed, findable blunder in band whose k-1 = preceding_len moves before it are Good."""
    blunder = _blunder(
        case="allowed",
        refutation=(0.6, 1),
        bucket=bucket,
        preceding=_judgements(*([MID_ES] * preceding_len)),
    )
    blunder.game_id = game_id
    return blunder


class TestDrawWindowShape:
    def test_herring_share_and_position_shares_follow_the_hazard_model(self) -> None:
        rng = random.Random(1)
        shapes = [draw_window_shape(rng) for _ in range(SHAPE_DRAWS)]
        weights = hazard_position_weights()
        herring = sum(1 for s in shapes if s.blunder_position is None) / SHAPE_DRAWS
        assert herring == pytest.approx(weights["herring_share"], abs=SHARE_TOLERANCE)
        for position, raw in weights["raw"].items():
            share = sum(1 for s in shapes if s.blunder_position == position) / SHAPE_DRAWS
            assert share == pytest.approx(raw, abs=SHARE_TOLERANCE)
        assert {s.length for s in shapes} == set(WINDOW_LENGTHS)
        assert all(s.blunder_position is None or s.blunder_position <= s.length for s in shapes)


class TestPickWindows:
    def _collection(self) -> Collection:
        # 30 blunders that fit every position, 30 that fit position 1 only (nothing precedes them).
        full = [_fit_blunder(100 + i, preceding_len=4) for i in range(30)]
        bare = [_fit_blunder(200 + i, preceding_len=0) for i in range(30)]
        games = [
            _oddness_game(g, 12) for g in range(1, 31)
        ]  # herring supply: 12 Good in-band moves each
        return Collection(games=games, blunders=[*full, *bare])

    def test_blunder_windows_only_use_blunders_that_fit_their_position(self) -> None:
        params = SpotCheckParams(PARAMS, SPOT_PER_BUCKET)
        windows = pick_windows(self._collection(), params, random.Random(5))
        blunder_windows = [w for w in windows if w.blunder is not None]
        assert blunder_windows
        for w in blunder_windows:
            assert w.blunder is not None and w.shape.blunder_position is not None
            assert blunder_fits_position(
                w.blunder.preceding,
                w.blunder.es_before,
                w.shape.blunder_position,
                PARAMS.band_low,
                PARAMS.band_high,
            )
            assert len(w.good_moves) == w.shape.blunder_position - 1

    def test_herring_windows_are_consecutive_good_in_band_moves(self) -> None:
        params = SpotCheckParams(PARAMS, SPOT_PER_BUCKET)
        windows = pick_windows(self._collection(), params, random.Random(5))
        herrings = [w for w in windows if w.blunder is None]
        assert herrings
        for w in herrings:
            assert len(w.good_moves) == w.shape.length
            assert all(m.good and in_band(m.es_before, 0.10, 0.90) for m in w.good_moves)
            plies = [m.ply for m in w.good_moves]
            assert plies == list(range(plies[0], plies[0] + 2 * len(plies), 2))

    def test_no_game_twice_per_bucket_and_count_is_capped(self) -> None:
        params = SpotCheckParams(PARAMS, SPOT_PER_BUCKET)
        windows = pick_windows(self._collection(), params, random.Random(5))
        assert len(windows) == SPOT_PER_BUCKET
        assert len({w.game_id for w in windows}) == len(windows)

    def test_same_seed_same_windows_and_exhausted_candidates_stop_early(self) -> None:
        params = SpotCheckParams(PARAMS, SPOT_PER_BUCKET)
        collection = self._collection()
        assert pick_windows(collection, params, random.Random(5)) == pick_windows(
            collection, params, random.Random(5)
        )
        assert pick_windows(collection, params, random.Random(5)) != pick_windows(
            collection, params, random.Random(6)
        )
        tiny = Collection(games=[_oddness_game(1, 3)], blunders=[])
        assert len(pick_windows(tiny, SpotCheckParams(PARAMS, 50), random.Random(1))) == 1


def _detail(
    window_blunder: BlunderRecord | None,
    *,
    link: str = PUBLIC_LINK,
    shape: WindowShape | None = None,
) -> SpotWindowDetail:
    shape = shape or WindowShape(3, None if window_blunder is None else 3)
    window = SpotWindow(
        BUCKET,
        shape,
        7,
        1500.0,
        (MoveJudgement(4, True, 0.52), MoveJudgement(6, True, 0.49)),
        window_blunder,
    )
    detail = SpotWindowDetail(
        window=window,
        link=link,
        user_rating=1480,
        start_fen="startfen",
        lead_in="1... e5 2. Nf3 Nc6",
        judged=[
            JudgedLine("3. Bb5", 0.52, "3... a6"),
            JudgedLine("4. Ba4", 0.49, "4... Nf6"),
        ],
    )
    if window_blunder is not None:
        detail.answer_fen = "answerfen"
        detail.answer_move = "5. O-O"
        detail.refutation = "b5"
        detail.missed_best = "d3"
    return detail


class TestRenderSpotCheck:
    def test_allowed_window_prints_link_lead_in_judged_moves_answer_and_refutation(self) -> None:
        blunder = _blunder(case="allowed", refutation=(0.31, 2))
        text_out = render_spot_check([_detail(blunder)], SpotCheckParams(PARAMS, 20))
        for expected in (
            PUBLIC_LINK,
            "1... e5 2. Nf3 Nc6",
            "3. Bb5 (Good, pre-move ES 0.52), reply 3... a6",
            "4. Ba4 (Good, pre-move ES 0.49), reply 4... Nf6",
            "blunder 5. O-O",
            "`answerfen`",
            "**Refutation:** b5 (Maia probability 0.310, rank 2)",
            "pinned Maia Elo 1500",
            "### 1200-1599",
        ):
            assert expected in text_out
        assert "Missed best move" not in text_out
        # Moves come in game order: lead-in, judged moves, answer.
        assert text_out.index("Nf3") < text_out.index("3. Bb5") < text_out.index("blunder 5. O-O")

    def test_pure_miss_prints_the_missed_best_move_with_its_maia_pair(self) -> None:
        blunder = _blunder(case="pure_miss", best=(0.5, BEST_RANK))
        text_out = render_spot_check([_detail(blunder)], SpotCheckParams(PARAMS, 20))
        assert "**Missed best move:** d3 (Maia probability 0.500, rank 1)" in text_out
        assert "**Refutation:**" not in text_out

    def test_herring_says_all_safe_and_missing_link_is_stated(self) -> None:
        text_out = render_spot_check(
            [_detail(None, link="no public link")], SpotCheckParams(PARAMS, 20)
        )
        assert "all safe" in text_out
        assert "no public link" in text_out
        assert "blunder 5." not in text_out


class TestFetchWindowDetails:
    @pytest.mark.asyncio
    async def test_san_sequence_link_and_stored_moves_come_from_the_game(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game()
        async with session_factory() as session:
            await session.execute(
                text("UPDATE games SET platform_url = :url WHERE id = :id"),
                {"url": PUBLIC_LINK, "id": game_id},
            )
            for ply, best, pv in ((8, MISSED_BEST_UCI, None), (9, None, f"{REPLY_UCI} a2a3")):
                await session.execute(
                    text(
                        "UPDATE game_positions SET best_move = :b, pv = :pv "
                        "WHERE game_id = :g AND ply = :p"
                    ),
                    {"b": best, "pv": pv, "g": game_id, "p": ply},
                )
            await session.commit()
        blunder = _blunder(case="pure_miss", best=(0.5, BEST_RANK), refutation=(0.3, 2))
        blunder.game_id = game_id
        blunder.ply = USER_BLUNDER_PLY
        window = SpotWindow(
            BUCKET,
            WindowShape(3, 3),
            game_id,
            1500.0,
            (MoveJudgement(4, True, 0.5), MoveJudgement(6, True, 0.5)),
            blunder,
        )
        [detail] = await fetch_window_details(session_factory, [window])

        assert detail.link == PUBLIC_LINK
        assert detail.user_rating == 1500
        assert detail.lead_in == "1... e5 2. Nf3 Nc6"
        assert [(j.move, j.reply) for j in detail.judged] == [
            ("3. Bb5", "3... a6"),
            ("4. Ba4", "4... Nf6"),
        ]
        assert detail.answer_move == "5. O-O"
        board = chess.Board()
        for san in _SAN[:USER_BLUNDER_PLY]:
            board.push_san(san)
        assert detail.answer_fen == board.fen()
        assert detail.missed_best == "d3"
        # best_move is NULL at ply + 1, so the first pv token stands in as the refutation.
        assert detail.refutation == "b5"

        rendered = render_spot_check([detail], SpotCheckParams(PARAMS, 20))
        assert str(_TEST_USER_ID) not in rendered
        assert "example.com" not in rendered

    @pytest.mark.asyncio
    async def test_stored_move_that_is_illegal_on_the_board_prints_uci_and_illegal(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game()
        async with session_factory() as session:
            await session.execute(
                text("UPDATE game_positions SET best_move = 'e2e4' WHERE game_id = :g AND ply = 8"),
                {"g": game_id},
            )
            await session.commit()
        blunder = _blunder(case="pure_miss", best=(0.5, BEST_RANK))
        blunder.game_id = game_id
        blunder.ply = USER_BLUNDER_PLY
        window = SpotWindow(BUCKET, WindowShape(1, 1), game_id, 1500.0, (), blunder)
        [detail] = await fetch_window_details(session_factory, [window])
        assert detail.missed_best == "e2e4 (illegal)"
        assert detail.link == "no public link"


class TestRecommendedConstants:
    def test_section_states_chosen_values_pass_shares_and_recommendation_only(self) -> None:
        blunders = [
            _scored_blunder(0.3, 2),
            _blunder(refutation=(0.05, 4)),
            _blunder(refutation=(0.25, 2)),
            _blunder(refutation=(0.10, 3)),
            _blunder(),
        ]
        params = ReportParams(
            refutation_threshold=0.20,
            miss_threshold=0.30,
            band_low=0.10,
            band_high=0.90,
            spot_check_file="spot-check-2026-11-09.md",
        )
        section = section_recommended_constants(Collection(blunders=blunders), params)
        assert "R = 0.2" in section and "X' = 0.3" in section
        assert "[0.10, 0.90]" in section
        assert "recommendation only" in section
        assert "spot-check-2026-11-09.md" in section
        # The last blunder has no stored pair (unscored, left out of the denominator): of the 4
        # scored allowed blunders the rank-1 one and the 0.25 one pass at R = 0.2.
        assert _row(section, BUCKET)[1] == "50.0% (n=4)"
