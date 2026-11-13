"""Tests for the blunder-check calibration sampler and report (SEED-261108-dk0, Phase 248, 250).

DB-backed tests commit games through a session maker bound to the per-run test DB and delete
them in teardown. The sampler's selector is global, so every assertion about its output is
scoped to this module's own game ids (other modules' games leak in under -n auto).
"""

from __future__ import annotations

import datetime
import json
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
from app.services.blunder_check_rules import FOREIGN_RATING_BAND, SlotPlan
from scripts.blunder_check.metrics import (
    HAZARD,
    EloBucket,
    MissCase,
    MoveJudgement,
    Provenance,
    blunder_fits_position,
    blunder_position_marginals,
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
    section_facepalm_score,
    section_herring_supply,
    section_provenance,
    section_recommended_constants,
    level_note,
    section_supply_by_origin,
    section_window_fit,
)
from scripts.blunder_check import spot_check
from scripts.blunder_check.spot_check import (
    JudgedLine,
    SpotCheckParams,
    SpotWindow,
    SpotWindowDetail,
    WindowShape,
    analysis_link,
    fetch_window_details,
    pick_windows,
    render_spot_check,
)
from scripts.blunder_check.sample import (
    CACHE_VERSION,
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
SEEDED_SCORE = 0.82
SEEDED_PLAYED_PROB = 0.04
SEEDED_SPREAD = 2.5
SEEDED_LOSS_3 = 3

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
        with_line: bool = True,
    ) -> int:
        evals = [HOLD_CP] * len(_SAN)
        evals[OPPONENT_BLUNDER_PLY] = GIFT_CP
        # The stored engine line after the user's blunder sits on the row at ply + 1.
        line_pv = {USER_BLUNDER_PLY + 1: "d7d5 e4d5 d8d5"} if with_line else {}
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
                        pv=line_pv.get(ply),
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
                        maia_played_prob=SEEDED_PLAYED_PROB if is_user_ply else None,
                        maia_reply_spread=SEEDED_SPREAD if is_user_ply else None,
                        line_loss_3=SEEDED_LOSS_3 if is_user_ply else None,
                        facepalm_score=SEEDED_SCORE if is_user_ply else None,
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
        assert blunder.maia_played_prob == pytest.approx(SEEDED_PLAYED_PROB)
        assert blunder.maia_reply_spread == pytest.approx(SEEDED_SPREAD)
        assert (blunder.line_loss_3, blunder.line_mate_ply) == (SEEDED_LOSS_3, None)
        assert blunder.facepalm_score == pytest.approx(SEEDED_SCORE)
        assert blunder.has_line

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
    async def test_blunder_without_a_stored_line_is_recorded_as_such(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # has_line separates "no line" from "line too short" in the Facepalm score section.
        with_line = await make_game(with_line=True)
        without_line = await make_game(with_line=False)
        async with session_factory() as session:
            batch = await collect_records(session, [with_line, without_line])
        by_game = {b.game_id: b for b in batch.blunders}
        assert by_game[with_line].has_line
        assert not by_game[without_line].has_line

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
PARAMS = ReportParams(facepalm_threshold=0.70, band_low=0.10, band_high=0.90)
QUALIFYING_SCORE = 0.9
BELOW_SCORE = 0.4


def _judgements(*es_values: float, good: bool = True, start_ply: int = 0) -> list[MoveJudgement]:
    """User moves on even plies (white user) with the given pre-move ES values."""
    return [MoveJudgement(start_ply + 2 * i, good, es) for i, es in enumerate(es_values)]


def _blunder(
    *,
    case: MissCase = "allowed",
    score: float | None = QUALIFYING_SCORE,
    played_prob: float | None = 0.05,
    spread: float | None = 2.0,
    loss_3: int | None = 3,
    mate_ply: int | None = None,
    has_line: bool = True,
    preceding: list[MoveJudgement] | None = None,
    es_before: float | None = MID_ES,
    bucket: EloBucket = BUCKET,
    provenance: Provenance = "engine",
    is_guest: bool = False,
) -> BlunderRecord:
    """A user blunder; the defaults give a scored one that qualifies at PARAMS."""
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
        maia_played_prob=played_prob,
        maia_reply_spread=spread,
        line_loss_3=loss_3,
        line_mate_ply=mate_ply,
        facepalm_score=score,
        has_line=has_line,
        preceding=preceding or [],
    )


def _unscored(reason: str) -> BlunderRecord:
    """An unscored blunder for each NULL reason of the Facepalm score section."""
    if reason == "no_spread":
        return _blunder(score=None, spread=None, loss_3=None, has_line=True)
    if reason == "no_line":
        return _blunder(score=None, loss_3=None, has_line=False)
    if reason == "line_too_short":
        return _blunder(score=None, loss_3=None, has_line=True)
    raise AssertionError(reason)


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
    lines: list[str] = []
    for line in section.splitlines():
        if line.startswith("|"):
            lines.append(line)
        elif lines:
            break
    return [[c.strip() for c in line.strip("|").split("|")] for line in lines[2:]]


def _row(section: str, label: str) -> list[str]:
    return next(r for r in _rows(section) if r[0] == label)


class TestFacepalmScoreSection:
    def test_counts_shares_null_reasons_and_pass_shares_per_bucket(self) -> None:
        scored = [_blunder(score=s) for s in (0.45, 0.55, 0.65, 0.75, 0.85, 0.95)]
        unscored = [_unscored("no_spread"), _unscored("no_line"), _unscored("line_too_short")]
        section = section_facepalm_score(Collection(blunders=[*scored, *unscored]), PARAMS)
        header = next(line for line in section.splitlines() if line.startswith("| Elo bucket"))
        columns = [c.strip() for c in header.strip("|").split("|")]
        row = dict(zip(columns, _row(section, BUCKET), strict=True))
        assert row["user blunders"] == "9"
        assert row["scored"] == "66.7% (n=9)"
        assert row["no spread"] == "11.1% (n=9)"
        assert row["no line"] == "11.1% (n=9)"
        assert row["line too short"] == "11.1% (n=9)"
        assert row["no played prob"] == "0.0% (n=9)"
        # Pass shares are of the 6 scored blunders: 5 / 4 / 3 / 2 are at or above 0.5 / 0.6 / 0.7 / 0.8.
        assert row["pass >= 0.50"] == "83.3% (n=6)"
        assert row["pass >= 0.60"] == "66.7% (n=6)"
        assert row["pass >= 0.70"] == "50.0% (n=6)"
        assert row["pass >= 0.80"] == "33.3% (n=6)"
        # Qualifying of all: 3 of the 9 user blunders reach 0.70, the unscored ones never do.
        assert row["qualifying of all (>= 0.70)"] == "33.3% (n=9)"
        assert row["score q1 / median / q3"] == "0.575 / 0.700 / 0.825"

    def test_chosen_threshold_outside_the_grid_gets_its_own_column(self) -> None:
        params = ReportParams(facepalm_threshold=0.65)
        section = section_facepalm_score(Collection(blunders=[_blunder(score=0.66)]), params)
        assert "pass >= 0.65" in section
        assert "qualifying of all (>= 0.65)" in section
        assert _row(section, BUCKET)[-2] == "100.0% (n=1)"

    def test_pooled_row_and_guest_exclusion(self) -> None:
        blunders = [
            _blunder(bucket="<800"),
            _blunder(bucket="2400+", score=None, spread=None),
            _blunder(is_guest=True),
        ]
        section = section_facepalm_score(Collection(blunders=blunders), PARAMS)
        assert _row(section, "all")[1] == "2"
        assert _row(section, "<800")[1] == "1"

    def test_missing_played_prob_is_its_own_reason(self) -> None:
        blunder = _blunder(score=None, played_prob=None)
        section = section_facepalm_score(Collection(blunders=[blunder]), PARAMS)
        header = next(line for line in section.splitlines() if line.startswith("| Elo bucket"))
        columns = [c.strip() for c in header.strip("|").split("|")]
        row = dict(zip(columns, _row(section, BUCKET), strict=True))
        assert row["no played prob"] == "100.0% (n=1)"
        assert row["line too short"] == "0.0% (n=1)"


class TestQualifyingPredicate:
    def test_null_never_qualifies_and_threshold_is_inclusive(self) -> None:
        from scripts.blunder_check.render import qualifying_blunders

        blunders = [_blunder(score=0.70), _blunder(score=0.6999), _blunder(score=None)]
        assert [b.facepalm_score for b in qualifying_blunders(blunders, PARAMS)] == [0.70]

    def test_report_has_the_facepalm_section_and_no_findability_grid(self) -> None:
        report = render_report(Collection(blunders=[_blunder()]), PARAMS)
        assert report.count("## Facepalm score") == 1
        assert "## Findability grid" not in report


class TestWindowFit:
    def test_three_good_in_band_moves_fit_positions_one_to_four_not_five(self) -> None:
        blunder = _blunder(preceding=_judgements(MID_ES, MID_ES, MID_ES))
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
        # Window-weighted average: 1 minus the blunder-window weight of position 5 (0.0328).
        assert row[7] == "96.7% (n=1)"

    def test_out_of_band_preceding_move_blocks_longer_positions(self) -> None:
        # Detects dropping the band check on the preceding judged moves.
        fits_all = _blunder(preceding=_judgements(MID_ES, MID_ES, MID_ES))
        fits_first_only = _blunder(preceding=_judgements(MID_ES, MID_ES, OUT_OF_BAND_ES))
        section = section_window_fit(Collection(blunders=[fits_all, fits_first_only]), PARAMS)
        row = _row(section, BUCKET)
        assert row[2] == "100.0% (n=2)"
        assert row[3] == "50.0% (n=2)"
        assert row[4] == "50.0% (n=2)"

    def test_not_good_preceding_move_blocks_longer_positions(self) -> None:
        preceding = [MoveJudgement(14, False, MID_ES), MoveJudgement(16, True, MID_ES)]
        blunder = _blunder(preceding=preceding)
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
            _blunder(es_before=0.5),
            _blunder(es_before=0.97),
        ]
        section = section_eval_band(Collection(blunders=blunders), PARAMS)
        rows = _rows(section)
        full_band = next(r for r in rows if r[0] == "[0.00, 1.00]")
        tight_band = next(r for r in rows if r[0] == "[0.10, 0.90]")
        assert full_band[-1] == "100.0% (n=2)"  # last column is the pooled "all" row
        assert tight_band[-1] == "50.0% (n=2)"


class TestSupplyByOrigin:
    def _collection(self) -> Collection:
        usable = [_blunder() for _ in range(10)]
        groups = [
            UserGroup(1, "engine", "lichess", "blitz", 1500, games=10, user_blunders=100),
            UserGroup(2, "engine", "lichess", "blitz", 1500, games=10, user_blunders=200),
        ]
        return Collection(blunders=usable, user_groups=groups)

    def test_percentiles_and_users_under_minimum(self) -> None:
        section = section_supply_by_origin(self._collection(), PARAMS)
        # Position 1 only fits (no preceding moves): fit share = blunder-window weight of position 1.
        assert "estimate" in section.lower()
        row = _row(section, "usable blunder windows")
        low, high = 100 * 0.3837, 200 * 0.3837
        assert float(row[3]) == pytest.approx((low + high) / 2, abs=0.2)  # p50 of two users
        assert "1 of 2" in section  # user 1 (about 38 windows) is under MIN_USER_WINDOWS = 50

    def test_pure_misses_are_capped(self) -> None:
        pure = [_blunder(case="pure_miss") for _ in range(10)]
        groups = [UserGroup(1, "engine", "lichess", "blitz", 1500, games=1, user_blunders=100)]
        section = section_supply_by_origin(Collection(blunders=pure, user_groups=groups), PARAMS)
        # No non-pure blunders at all: the cap on pure misses is 0 of the total.
        row = _row(section, "usable blunder windows")
        assert float(row[3]) == pytest.approx(0.0)


class TestForeignSupplyByLevel:
    """250 D-10, D-13: qualifying blunders of other users within +-FOREIGN_RATING_BAND of a level."""

    def _game_at(self, game_id: int, elo: float, *, guest: bool = False) -> GameRecord:
        game = _game(_judgements(MID_ES), user_id=game_id)
        game.elo = elo
        game.is_guest = guest
        return game

    def _at(self, game_id: int, **kwargs: Any) -> BlunderRecord:
        blunder = _blunder(**kwargs)
        blunder.game_id = game_id
        return blunder

    def _rows_by_level(self, collection: Collection) -> dict[str, list[str]]:
        section = section_supply_by_origin(collection, PARAMS)
        foreign = section.split("### Foreign supply per rating level")[1]
        return {r[0]: r for r in _rows(foreign)}

    def _collection(self, permille: int = 1000) -> Collection:
        games = [
            self._game_at(1, 700.0),
            self._game_at(2, 700.0),
            self._game_at(3, 1500.0),
            self._game_at(4, 2450.0),
            self._game_at(5, 1500.0, guest=True),
        ]
        blunders = [
            self._at(1),
            self._at(1),  # same game twice: one game, two blunders
            self._at(2, es_before=OUT_OF_BAND_ES),  # qualifying but not usable
            self._at(3),
            self._at(3, score=BELOW_SCORE),  # below the threshold: never counted
            self._at(3, score=None, spread=None),  # unscored: never counted
            self._at(4),
            self._at(5, is_guest=True),  # guest games never feed a foreign pool
        ]
        return Collection(meta=RunMeta(permille=permille), games=games, blunders=blunders)

    def test_counts_per_level_within_the_band_with_inclusive_edge(self) -> None:
        rows = self._rows_by_level(self._collection())
        assert list(rows) == [str(level) for level in range(600, 2601, 200)]
        # columns: level, band, qualifying, usable, games, sample n, note
        assert rows["600"][1] == f"{600 - FOREIGN_RATING_BAND} to {600 + FOREIGN_RATING_BAND}"
        assert rows["600"][2:6] == ["3", "2", "2", "3"]  # games 1 and 2: 3 blunders, 2 usable
        assert rows["800"][2:6] == ["3", "2", "2", "3"]
        assert rows["1000"][2:6] == ["0", "0", "0", "0"]
        assert rows["1400"][2:6] == ["1", "1", "1", "1"]
        assert rows["1600"][2:6] == ["1", "1", "1", "1"]
        # 2450 sits exactly FOREIGN_RATING_BAND from 2600 and 150 from 2400 (edge is inclusive).
        assert rows["2400"][2:6] == ["1", "1", "1", "1"]
        assert rows["2600"][2:6] == ["1", "1", "1", "1"]
        assert rows["2200"][2:6] == ["0", "0", "0", "0"]

    def test_extremes_are_called_out(self) -> None:
        rows = self._rows_by_level(self._collection())
        assert rows["600"][6] == "extreme: below 800"
        assert rows["2400"][6] == "extreme: 2400 and above"
        assert rows["2600"][6] == "extreme: 2400 and above"
        assert rows["800"][6] == "" and rows["2200"][6] == ""
        assert level_note(799) != "" and level_note(800) == "" and level_note(2399) == ""

    def test_counts_scale_from_the_sample_to_the_population(self) -> None:
        rows = self._rows_by_level(self._collection(permille=250))
        # 250 permille sampled: every sample count stands for four.
        assert rows["600"][2:6] == ["12", "8", "8", "3"]
        assert rows["2400"][2:6] == ["4", "4", "4", "1"]

    def test_own_supply_block_is_still_there(self) -> None:
        section = section_supply_by_origin(self._collection(), PARAMS)
        assert section.count("## Supply by origin") == 1
        assert "### Own supply per user" in section
        assert "usable blunder windows" in section


class TestWindowComposition:
    def test_window_fit_and_herring_text_use_the_d12_shares_not_the_hazard_herring_share(
        self,
    ) -> None:
        collection = Collection(
            blunders=[_blunder(preceding=_judgements(MID_ES, MID_ES))],
            games=[_game(_judgements(*[MID_ES] * 6))],
        )
        fit = section_window_fit(collection, PARAMS)
        herring = section_herring_supply(collection, PARAMS)
        assert "33.3%" in fit and "33.3%" in herring
        # The 249 hazard model's herring share (0.301) no longer describes the window mix.
        assert "0.301" not in fit and "30.1%" not in fit
        assert "raw P(blunder at k)" not in fit

    def test_position_weights_table_is_the_conditional_marginal_and_sums_to_one(self) -> None:
        fit = section_window_fit(Collection(blunders=[_blunder()]), PARAMS)
        rows = _rows(fit[fit.index("| position") :])
        weights = {int(r[0]): float(r[1]) for r in rows}
        marginals = blunder_position_marginals()
        assert sum(weights.values()) == pytest.approx(1.0, abs=1e-3)
        for position, weight in weights.items():
            assert weight == pytest.approx(marginals[position], abs=1e-4)

    def test_arrow_oddness_reports_the_probability_auc_only(self) -> None:
        collection = Collection(
            meta=RunMeta(date="2026-11-13"),
            blunders=[_scored_blunder(p) for p in BLUNDER_PROBS],
            oddness=[_good(p) for p in GOOD_PROBS],
        )
        section = render_report(collection, PARAMS).split("## Arrow oddness")[1]
        header = next(line for line in section.splitlines() if line.startswith("| Elo bucket"))
        assert "rank" not in header.lower()
        assert "AUC" in header


class TestProvenance:
    def test_provenance_rows_differ(self) -> None:
        engine = _blunder(preceding=_judgements(MID_ES, MID_ES, MID_ES), provenance="engine")
        lichess = _blunder(provenance="lichess")
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
                    score=0.123456789,
                    spread=2.718281828,
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
        assert restored.blunders[0].facepalm_score == 0.123456789
        assert restored.blunders[0].maia_reply_spread == 2.718281828
        assert restored.blunders[0].has_line

    def test_cache_written_with_the_new_version_round_trips(self, tmp_path: Path) -> None:
        collection = Collection(blunders=[_blunder(), _unscored("no_line")])
        path = tmp_path / "cache.json"
        write_cache(collection, path)
        assert json.loads(path.read_text())["version"] == CACHE_VERSION
        restored = read_cache(path)
        assert restored.blunders == collection.blunders

    def test_cache_with_the_previous_version_is_refused(self, tmp_path: Path) -> None:
        # T-250-25: a pre-250 cache holds the best / refutation pairs, not the facepalm fields.
        path = tmp_path / "cache.json"
        write_cache(Collection(blunders=[_blunder()]), path)
        raw = json.loads(path.read_text())
        raw["version"] = CACHE_VERSION - 1
        path.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="unsupported cache version"):
            read_cache(path)


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
    prob: float, *, bucket: EloBucket = BUCKET, es_before: float | None = MID_ES
) -> GoodMoveOddness:
    return GoodMoveOddness(game_id=1, ply=0, bucket=bucket, es_before=es_before, played_prob=prob)


def _scored_blunder(prob: float, *, bucket: EloBucket = BUCKET) -> BlunderRecord:
    """A qualifying blunder (default facepalm score) with the given played-move probability."""
    return _blunder(
        case="allowed", played_prob=prob, bucket=bucket, preceding=_judgements(0.5, 0.5, 0.5)
    )


class TestOddnessSummary:
    def test_known_auc_and_quartiles(self) -> None:
        good = [_good(p) for p in GOOD_PROBS]
        blunders = [_scored_blunder(p) for p in BLUNDER_PROBS]
        row = summarize_oddness(good, blunders)[BUCKET]
        assert (row.n_good, row.n_blunder) == (4, 4)
        assert row.auc == pytest.approx(EXPECTED_AUC)
        assert row.good_quartiles == pytest.approx((0.575, 0.65, 0.725))
        assert row.blunder_quartiles == pytest.approx((0.175, 0.4, 0.675))

    def test_empty_side_gives_no_auc(self) -> None:
        row = summarize_oddness([_good(0.5)], [])[BUCKET]
        assert row.auc is None
        assert row.blunder_quartiles is None

    def test_blunder_without_stored_probability_is_ignored(self) -> None:
        unscored = _blunder(case="allowed", played_prob=None)
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
        # Probability only (250 D-10): the record carries no rank.
        assert not hasattr(record, "played_rank")

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
            blunders=[_scored_blunder(p) for p in BLUNDER_PROBS],
            oddness=[*in_band_good, *out_of_band],
        )
        report = render_report(collection, PARAMS)
        assert report.count("## Arrow oddness") == 1
        assert report.count("## Recommended constants") == 1
        assert "recommendation only" in report
        row = _row(report.split("## Arrow oddness")[1], BUCKET)
        assert row[1] == "4"  # the out-of-band Good move is dropped
        assert row[-1] == f"{EXPECTED_AUC:.3f}"

    def test_baseline_table_separates_band_and_facepalm_selection(self) -> None:
        # Drill: the 4 usable blunders vs the 4 in-band Good moves (EXPECTED_AUC).
        usable = [_scored_blunder(p) for p in BLUNDER_PROBS]
        # Below the facepalm threshold but in band: counted by "band only" only.
        below_threshold = _blunder(case="allowed", score=BELOW_SCORE, played_prob=0.95)
        # Qualifying but out of band: counted by "unselected" only.
        out_of_band = _scored_blunder(0.95)
        out_of_band.es_before = OUT_OF_BAND_ES
        collection = Collection(
            meta=RunMeta(date="2026-11-10"),
            blunders=[*usable, below_threshold, out_of_band],
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


class TestCliFacepalmReport:
    def _cache(self, tmp_path: Path) -> Path:
        collection = Collection(
            meta=RunMeta(db_name="x", date="2026-11-13", games_sampled=1),
            games=[_game(_judgements(0.31, 0.5, 0.77))],
            blunders=[_blunder(), _unscored("no_line"), _unscored("line_too_short")],
        )
        path = tmp_path / "cache.json"
        write_cache(collection, path)
        return path

    def test_from_cache_renders_the_facepalm_section_and_no_findability_grid(
        self, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "out"
        code = cli_main(
            [
                "--from-cache",
                str(self._cache(tmp_path)),
                "--out-dir",
                str(out_dir),
                "--date",
                "2026-11-13",
                "--spot-check-per-bucket",
                "0",
                "--facepalm-threshold",
                "0.65",
            ]
        )
        assert code == 0
        report = (out_dir / "blunder-check-calibration-2026-11-13.md").read_text()
        assert report.count("## Facepalm score") == 1
        assert "## Findability grid" not in report
        assert "pass >= 0.65" in report

    def test_the_retired_threshold_flags_are_gone(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            cli_main(["--from-cache", "x.json", "--refutation-threshold", "0.2"])
        with pytest.raises(SystemExit):
            cli_main(["--from-cache", "x.json", "--miss-threshold", "0.2"])
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cli_main(["--help"])
        help_text = capsys.readouterr().out
        assert "--facepalm-threshold" in help_text
        assert "--refutation-threshold" not in help_text

    def test_a_threshold_outside_zero_to_one_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            cli_main(["--from-cache", "x.json", "--facepalm-threshold", "1.5"])


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

MIX_WINDOWS = 300
MIX_TOLERANCE = 0.06
ONE_THIRD = 1 / 3
SPOT_PER_BUCKET = 12
PUBLIC_LINK = "https://flawchess.com/analysis?game_id=1&ply=3"
MISSED_BEST_UCI = "d2d3"
REPLY_UCI = "b7b5"


def _fit_blunder(game_id: int, *, preceding_len: int, bucket: EloBucket = BUCKET) -> BlunderRecord:
    """A qualifying allowed blunder in band whose k-1 = preceding_len moves before it are Good."""
    blunder = _blunder(
        case="allowed",
        bucket=bucket,
        preceding=_judgements(*([MID_ES] * preceding_len)),
    )
    blunder.game_id = game_id
    return blunder


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


class TestSpotCheckMix:
    """250 D-12: windows are drawn with draw_slot_plan and kind-preserving redraws."""

    def _big_collection(self) -> Collection:
        blunders = [_fit_blunder(1000 + i, preceding_len=4) for i in range(MIX_WINDOWS + 100)]
        games = [_oddness_game(g, 12) for g in range(1, MIX_WINDOWS + 101)]
        return Collection(games=games, blunders=blunders)

    def test_about_one_third_of_the_windows_are_herrings(self) -> None:
        params = SpotCheckParams(PARAMS, MIX_WINDOWS)
        windows = pick_windows(self._big_collection(), params, random.Random(11))
        assert len(windows) == MIX_WINDOWS
        herrings = sum(1 for w in windows if w.blunder is None)
        assert herrings / len(windows) == pytest.approx(ONE_THIRD, abs=MIX_TOLERANCE)

    def test_slot_kind_comes_from_draw_slot_plan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        params = SpotCheckParams(PARAMS, SPOT_PER_BUCKET)
        collection = self._big_collection()
        monkeypatch.setattr(
            spot_check, "draw_slot_plan", lambda rng: SlotPlan("own", WindowShape(3, None))
        )
        assert all(w.blunder is None for w in pick_windows(collection, params, random.Random(5)))
        monkeypatch.setattr(
            spot_check, "draw_slot_plan", lambda rng: SlotPlan("foreign", WindowShape(3, 2))
        )
        windows = pick_windows(collection, params, random.Random(5))
        assert windows and all(w.blunder is not None for w in windows)

    def test_an_unfillable_blunder_shape_is_redrawn_as_a_blunder_not_swapped_for_a_herring(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Only position-1 blunders exist, but every plan asks for position 5: the redraw has to stay
        # a blunder window or the herring share would be inflated (and the mix skewed).
        bare = [_fit_blunder(2000 + i, preceding_len=0) for i in range(40)]
        collection = Collection(games=[_oddness_game(g, 12) for g in range(1, 41)], blunders=bare)
        monkeypatch.setattr(
            spot_check, "draw_slot_plan", lambda rng: SlotPlan("foreign", WindowShape(5, 5))
        )
        windows = pick_windows(collection, SpotCheckParams(PARAMS, 10), random.Random(3))
        assert windows
        assert all(w.blunder is not None and w.shape.blunder_position == 1 for w in windows)

    def test_rendered_spot_check_never_says_your_move_and_prints_score_inputs(self) -> None:
        collection = self._big_collection()
        windows = pick_windows(collection, SpotCheckParams(PARAMS, 40), random.Random(2))
        assert any(w.blunder is None for w in windows)
        assert any(w.blunder is not None for w in windows)
        details = [
            SpotWindowDetail(
                window=w,
                link=PUBLIC_LINK,
                user_rating=1480,
                start_fen="startfen",
                lead_in="1... e5",
                judged=[JudgedLine("3. Bb5", 0.52, "3... a6")],
                answer_fen=None if w.blunder is None else "answerfen",
                answer_move=None if w.blunder is None else "5. O-O",
                refutation=None if w.blunder is None else "b5",
            )
            for w in windows
        ]
        text_out = render_spot_check(details, SpotCheckParams(PARAMS, 40))
        assert "your move" not in text_out.lower()
        assert "all safe" in text_out
        assert text_out.count("**Score inputs:**") == sum(1 for w in windows if w.blunder)
        assert "own game" not in text_out.lower() and "foreign" not in text_out.lower()


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


class TestAnalysisLink:
    def test_points_at_the_board_before_the_first_judged_move(self) -> None:
        assert analysis_link(42, 10) == "https://flawchess.com/analysis?game_id=42&ply=9"

    def test_first_move_of_the_game_omits_ply(self) -> None:
        assert analysis_link(42, 0) == "https://flawchess.com/analysis?game_id=42"


class TestRenderSpotCheck:
    def test_allowed_window_prints_link_lead_in_judged_moves_answer_and_refutation(self) -> None:
        blunder = _blunder(
            case="allowed",
            score=0.83,
            played_prob=0.031,
            spread=2.46,
            loss_3=4,
            mate_ply=None,
        )
        text_out = render_spot_check([_detail(blunder)], SpotCheckParams(PARAMS, 20))
        for expected in (
            PUBLIC_LINK,
            "1... e5 2. Nf3 Nc6",
            "3. Bb5 (Good, pre-move ES 0.52), reply 3... a6",
            "4. Ba4 (Good, pre-move ES 0.49), reply 4... Nf6",
            "blunder 5. O-O",
            "`answerfen`",
            "**Refutation:** b5.",
            "**Score inputs:** facepalm score 0.830, played prob 0.031, reply spread 2.46, "
            "line loss 3 4, mate ply n/a.",
            "pinned Maia Elo 1500",
            "### 1200-1599",
        ):
            assert expected in text_out
        assert "Missed best move" not in text_out
        # Moves come in game order: lead-in, judged moves, answer.
        assert text_out.index("Nf3") < text_out.index("3. Bb5") < text_out.index("blunder 5. O-O")

    def test_pure_miss_prints_the_missed_best_move_with_its_maia_pair(self) -> None:
        blunder = _blunder(case="pure_miss", mate_ply=3, loss_3=None)
        text_out = render_spot_check([_detail(blunder)], SpotCheckParams(PARAMS, 20))
        assert "**Missed best move:** d3." in text_out
        assert "line loss 3 n/a, mate ply 3." in text_out
        assert "**Refutation:**" not in text_out

    def test_herring_says_all_safe(self) -> None:
        text_out = render_spot_check([_detail(None)], SpotCheckParams(PARAMS, 20))
        assert "all safe" in text_out
        assert "blunder 5." not in text_out


class TestFetchWindowDetails:
    @pytest.mark.asyncio
    async def test_san_sequence_link_and_stored_moves_come_from_the_game(
        self, make_game: MakeGame, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        game_id = await make_game()
        async with session_factory() as session:
            for ply, best, pv in ((8, MISSED_BEST_UCI, None), (9, None, f"{REPLY_UCI} a2a3")):
                await session.execute(
                    text(
                        "UPDATE game_positions SET best_move = :b, pv = :pv "
                        "WHERE game_id = :g AND ply = :p"
                    ),
                    {"b": best, "pv": pv, "g": game_id, "p": ply},
                )
            await session.commit()
        blunder = _blunder(case="pure_miss")
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

        # The link skips the lead-in: the board before the first judged move (ply 4) is ply=3.
        assert detail.link == f"https://flawchess.com/analysis?game_id={game_id}&ply=3"
        assert detail.user_rating == 1500
        # LEAD_IN_PLIES is 1: only the opponent's move before the first judged move is replayed.
        assert detail.lead_in == "2... Nc6"
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
        blunder = _blunder(case="pure_miss")
        blunder.game_id = game_id
        blunder.ply = USER_BLUNDER_PLY
        window = SpotWindow(BUCKET, WindowShape(1, 1), game_id, 1500.0, (), blunder)
        [detail] = await fetch_window_details(session_factory, [window])
        assert detail.missed_best == "e2e4 (illegal)"
        # No Good moves before the blunder: the link opens the board before the blunder itself.
        assert detail.link == (
            f"https://flawchess.com/analysis?game_id={game_id}&ply={USER_BLUNDER_PLY - 1}"
        )


class TestRecommendedConstants:
    def _blunders(self) -> list[BlunderRecord]:
        return [
            _blunder(score=0.55, played_prob=0.02, spread=1.5, loss_3=3),
            _blunder(score=0.65, played_prob=0.04, spread=2.5, loss_3=3),
            _blunder(score=0.75, played_prob=0.06, spread=3.5, loss_3=1),
            _blunder(score=0.85, played_prob=0.08, spread=4.5, loss_3=1),
            _unscored("no_line"),
        ]

    def test_states_chosen_values_and_recommendation_only(self) -> None:
        params = ReportParams(
            facepalm_threshold=0.65,
            band_low=0.10,
            band_high=0.90,
            spot_check_file="spot-check-2026-11-09.md",
        )
        section = section_recommended_constants(Collection(blunders=self._blunders()), params)
        assert "Facepalm threshold **0.65**" in section
        assert "[0.10, 0.90]" in section
        assert "recommendation only" in section
        assert "spot-check-2026-11-09.md" in section
        assert "R = " not in section and "X' = " not in section

    def test_fair_share_proxies_per_threshold(self) -> None:
        params = ReportParams(facepalm_threshold=0.65)
        section = section_recommended_constants(Collection(blunders=self._blunders()), params)
        rows = {r[0]: r for r in _rows(section)}
        # Columns: threshold, pass of scored, pass of all, median played prob, median spread,
        # mate or >= 2 points down, median usable windows per user.
        assert set(rows) == {"0.50", "0.60", "0.65", "0.70", "0.80"}
        assert rows["0.50"][1:6] == [
            "100.0% (n=4)",
            "80.0% (n=5)",
            "0.050",
            "3.00",
            "50.0% (n=4)",
        ]
        # Only the 0.85 blunder passes 0.80: it is a single, mildly punished (loss 1) one.
        assert rows["0.80"][1:6] == ["25.0% (n=4)", "20.0% (n=5)", "0.080", "4.50", "0.0% (n=1)"]
        assert "89%" in section  # the owner's label anchor at 0.7

    def test_threshold_with_no_passers_prints_na(self) -> None:
        params = ReportParams(facepalm_threshold=0.99)
        section = section_recommended_constants(Collection(blunders=self._blunders()), params)
        row = next(r for r in _rows(section) if r[0] == "0.99")
        assert row[1] == "0.0% (n=4)"
        assert row[3:6] == ["n/a", "n/a", "n/a (n=0)"]
