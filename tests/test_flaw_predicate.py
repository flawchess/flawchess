"""Predicate unit tests for build_flaw_filter_clauses + flaw_exists_from_table (Plan 108-03).

Verifies the SEED-038 family-aware boolean logic and single-flaw EXISTS semantics:

- build_flaw_filter_clauses([], []) returns [] (no filter = match all)
- single-flaw EXISTS: a game whose one flaw is BOTH low-clock AND reversed
  matches the combined filter; a game with a low-clock flaw on ply X and a
  reversed flaw on a DIFFERENT ply Y does NOT match (AND across families is
  per-flaw, not per-game — the make-or-break SEED-038 test)
- OR within family: a flaw tagged "miss" OR "lucky" matches either
- severity set-membership: ["mistake"] matches mistakes only (not blunders)
- cross-user isolation: another user's game_flaws row does not satisfy the EXISTS
  for the requesting user (T-108-07)
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.repositories.game_flaws_repository import bulk_insert_game_flaws
from app.repositories.library_repository import (
    build_flaw_filter_clauses,
    flaw_exists_from_table,
)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

# Integer encoding — must match _SEVERITY_INT / _TEMPO_INT in game_flaws_repository
_SEV_MISTAKE = 1
_SEV_BLUNDER = 2
_TEMPO_LOW_CLOCK = 0
_TEMPO_HASTY = 1
_TEMPO_UNRUSHED = 2


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist (FK constraint on game_flaws.user_id)."""
    from tests.conftest import ensure_test_user

    for uid in [77001, 77002]:
        await ensure_test_user(db_session, uid)


async def _seed_game(session: AsyncSession, user_id: int = 77001) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/pred-test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game


def _flaw_row(
    *,
    user_id: int,
    game_id: int,
    ply: int,
    severity: int = _SEV_BLUNDER,
    tempo: int | None = None,
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
) -> dict:  # type: ignore[type-arg]
    """Return a game_flaws insert dict with sensible defaults."""
    return {
        "user_id": user_id,
        "game_id": game_id,
        "ply": ply,
        "severity": severity,
        "tempo": tempo,
        "phase": 1,  # middlegame
        "is_miss": is_miss,
        "is_lucky": is_lucky,
        "is_reversed": is_reversed,
        "is_squandered": is_squandered,
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
    }


async def _games_matching_exists(
    session: AsyncSession,
    *,
    user_id: int,
    severity: list[str],
    tags: list[str],
    candidate_game_ids: set[int],
) -> set[int]:
    """Return the subset of candidate_game_ids for which flaw_exists_from_table is True."""
    from app.services.flaws_service import FlawSeverity, FlawTag
    from typing import cast
    from collections.abc import Sequence

    pred = flaw_exists_from_table(
        user_id=user_id,
        severity=cast(Sequence[FlawSeverity], severity),
        tags=cast(Sequence[FlawTag], tags),
    )
    stmt = select(Game.id).where(
        Game.id.in_(candidate_game_ids),
        Game.user_id == user_id,
        pred,
    )
    rows = (await session.execute(stmt)).scalars().all()
    return set(rows)


# ---------------------------------------------------------------------------
# Unit tests (no DB) — build_flaw_filter_clauses
# ---------------------------------------------------------------------------


class TestBuildFlawFilterClausesUnit:
    """build_flaw_filter_clauses returns the correct clause list without DB."""

    def test_empty_severity_and_tags_returns_no_clauses(self) -> None:
        """Empty inputs → empty clause list (match all, no filter)."""
        clauses = build_flaw_filter_clauses([], [])
        assert clauses == [], "empty inputs must produce zero clauses"

    def test_severity_only_produces_one_clause(self) -> None:
        """Non-empty severity → exactly one severity clause."""
        clauses = build_flaw_filter_clauses(["blunder"], [])
        assert len(clauses) == 1, "severity only should produce exactly one clause"

    def test_single_tag_family_produces_one_clause(self) -> None:
        """One tag from one family → exactly one clause (OR within that family)."""
        clauses = build_flaw_filter_clauses([], ["miss"])
        assert len(clauses) == 1, "one opportunity tag should produce exactly one clause"

    def test_two_families_produce_two_clauses(self) -> None:
        """Tags from two different families → two clauses (AND across families)."""
        clauses = build_flaw_filter_clauses([], ["low-clock", "reversed"])
        assert len(clauses) == 2, "tags from two families should produce two clauses"

    def test_phase_tags_produce_no_clause(self) -> None:
        """Phase tags (opening, middlegame, endgame) must never produce a clause."""
        from app.services.flaws_service import FlawTag
        from typing import cast
        from collections.abc import Sequence as Seq

        for phase_tag in ("opening", "middlegame", "endgame"):
            # Cast the str literal to Sequence[FlawTag] for ty compliance.
            # Phase tags are valid FlawTag values but must produce no filter clause.
            tags = cast(Seq[FlawTag], [phase_tag])
            clauses = build_flaw_filter_clauses([], tags)
            assert clauses == [], f"phase tag '{phase_tag}' must produce zero clauses"

    def test_phase_tags_mixed_with_real_tags_ignored(self) -> None:
        """Phase tags are skipped even when mixed with real filter tags."""
        clauses = build_flaw_filter_clauses([], ["low-clock", "opening"])
        # Only the tempo family clause — opening is ignored
        assert len(clauses) == 1, "phase tags must not add extra clauses"

    def test_severity_plus_tags_produce_correct_count(self) -> None:
        """Severity + tags from two families → three clauses total."""
        clauses = build_flaw_filter_clauses(["blunder"], ["low-clock", "miss", "reversed"])
        # severity (1) + tempo family (1) + opportunity family (1) + impact family (1) = 4
        assert len(clauses) == 4

    def test_severity_uses_set_membership(self) -> None:
        """["mistake"] matches mistakes only — distinct from ["mistake", "blunder"]."""
        clauses_both = build_flaw_filter_clauses(["mistake", "blunder"], [])
        clauses_mistake = build_flaw_filter_clauses(["mistake"], [])
        assert len(clauses_both) == 1
        assert len(clauses_mistake) == 1
        # Set membership, not a shared MIN threshold: the two selections compile to
        # different predicates (IN (1) vs IN (1, 2)).
        sql_both = str(clauses_both[0].compile(compile_kwargs={"literal_binds": True}))
        sql_mistake = str(clauses_mistake[0].compile(compile_kwargs={"literal_binds": True}))
        assert sql_both != sql_mistake
        assert "2" not in sql_mistake, "mistakes-only must not include blunder (severity 2)"
        assert "2" in sql_both


# ---------------------------------------------------------------------------
# Integration tests — flaw_exists_from_table (real DB via db_session)
# ---------------------------------------------------------------------------


class TestFlawExistsFromTable:
    """flaw_exists_from_table produces the correct game-level EXISTS semantics."""

    @pytest.mark.asyncio
    async def test_empty_filter_returns_true_predicate(self, db_session: AsyncSession) -> None:
        """flaw_exists_from_table with empty severity + tags returns true().

        This means every game matches — the filter is effectively disabled.
        """
        game = await _seed_game(db_session)
        # No flaw row; no filter — should still match (true() = no restriction)
        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=[],
            tags=[],
            candidate_game_ids={game.id},
        )
        assert game.id in matched, "empty filter (true()) must match even a game with no flaws"

    @pytest.mark.asyncio
    async def test_severity_blunder_matches_blunder_row(self, db_session: AsyncSession) -> None:
        """severity=["blunder"] matches a game with a blunder row."""
        game = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game.id, ply=2, severity=_SEV_BLUNDER)],
        )
        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=["blunder"],
            tags=[],
            candidate_game_ids={game.id},
        )
        assert game.id in matched

    @pytest.mark.asyncio
    async def test_severity_mistake_only_excludes_blunder(self, db_session: AsyncSession) -> None:
        """severity=["mistake"] uses set-membership: matches mistakes only, not blunders.

        The UI exposes Blunders/Mistakes as independent toggles, so a mistakes-only
        selection must NOT match a game whose only flaw is a blunder (severity=2).
        """
        game_with_blunder = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_with_blunder.id, ply=2, severity=_SEV_BLUNDER)],
        )

        game_with_mistake = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_with_mistake.id, ply=4, severity=_SEV_MISTAKE)],
        )

        game_clean = await _seed_game(db_session)

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=["mistake"],
            tags=[],
            candidate_game_ids={game_with_blunder.id, game_with_mistake.id, game_clean.id},
        )
        assert game_with_blunder.id not in matched, "blunder-only game must NOT match mistakes-only"
        assert game_with_mistake.id in matched, "mistake game matches mistakes-only"
        assert game_clean.id not in matched, "clean game must not match"

    @pytest.mark.asyncio
    async def test_single_flaw_exists_both_families_match(self, db_session: AsyncSession) -> None:
        """SEED-038 make-or-break: a SINGLE flaw satisfying BOTH families matches.

        A game with ONE flaw row tagged low-clock AND reversed satisfies the
        combined filter (low-clock + reversed) because the same row satisfies
        both clauses simultaneously.
        """
        game = await _seed_game(db_session)
        # One flaw at ply 2: low-clock tempo AND reversed impact
        await bulk_insert_game_flaws(
            db_session,
            [
                _flaw_row(
                    user_id=77001,
                    game_id=game.id,
                    ply=2,
                    severity=_SEV_BLUNDER,
                    tempo=_TEMPO_LOW_CLOCK,
                    is_reversed=True,
                )
            ],
        )

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=[],
            tags=["low-clock", "reversed"],
            candidate_game_ids={game.id},
        )
        assert game.id in matched, (
            "a single flaw satisfying both families must match the combined filter"
        )

    @pytest.mark.asyncio
    async def test_split_flaws_across_plies_do_not_match_cross_family(
        self, db_session: AsyncSession
    ) -> None:
        """SEED-038 make-or-break: AND across families is per-flaw, NOT per-game.

        A game with:
        - Flaw at ply 2: low-clock (but NOT reversed)
        - Flaw at ply 6: reversed (but NOT low-clock)

        Must NOT match the filter "low-clock + reversed" because no SINGLE flaw
        satisfies both families simultaneously. This is the key test distinguishing
        single-flaw EXISTS from a game-level OR/AND.
        """
        game = await _seed_game(db_session)
        # Ply 2: low-clock flaw only
        await bulk_insert_game_flaws(
            db_session,
            [
                _flaw_row(
                    user_id=77001,
                    game_id=game.id,
                    ply=2,
                    severity=_SEV_BLUNDER,
                    tempo=_TEMPO_LOW_CLOCK,
                    is_reversed=False,  # explicit
                )
            ],
        )
        # Ply 6: reversed flaw only (no tempo tag)
        await bulk_insert_game_flaws(
            db_session,
            [
                _flaw_row(
                    user_id=77001,
                    game_id=game.id,
                    ply=6,
                    severity=_SEV_BLUNDER,
                    tempo=None,  # no tempo tag
                    is_reversed=True,
                )
            ],
        )

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=[],
            tags=["low-clock", "reversed"],
            candidate_game_ids={game.id},
        )
        assert game.id not in matched, (
            "split-flaw game must NOT match: no single flaw has both families "
            "(AND across families = single-flaw EXISTS, not per-game)"
        )

    @pytest.mark.asyncio
    async def test_or_within_family_opportunity(self, db_session: AsyncSession) -> None:
        """OR within the opportunity family: miss OR lucky matches either.

        A game with a "miss" flaw must match tags=["miss", "lucky"], and a
        game with a "lucky" flaw must also match — OR within family.
        """
        game_miss = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_miss.id, ply=2, is_miss=True)],
        )

        game_lucky = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_lucky.id, ply=4, is_lucky=True)],
        )

        game_neither = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [
                _flaw_row(
                    user_id=77001,
                    game_id=game_neither.id,
                    ply=6,
                    is_miss=False,
                    is_lucky=False,
                )
            ],
        )

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=[],
            tags=["miss", "lucky"],
            candidate_game_ids={game_miss.id, game_lucky.id, game_neither.id},
        )
        assert game_miss.id in matched, "game with a 'miss' flaw must match OR within opportunity"
        assert game_lucky.id in matched, "game with a 'lucky' flaw must match OR within opportunity"
        assert game_neither.id not in matched, "game with neither opportunity tag must not match"

    @pytest.mark.asyncio
    async def test_or_within_family_tempo(self, db_session: AsyncSession) -> None:
        """OR within the tempo family: low-clock OR hasty matches either."""
        game_low_clock = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_low_clock.id, ply=2, tempo=_TEMPO_LOW_CLOCK)],
        )

        game_hasty = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_hasty.id, ply=4, tempo=_TEMPO_HASTY)],
        )

        game_unrushed = await _seed_game(db_session)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game_unrushed.id, ply=6, tempo=_TEMPO_UNRUSHED)],
        )

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=[],
            tags=["low-clock", "hasty"],
            candidate_game_ids={game_low_clock.id, game_hasty.id, game_unrushed.id},
        )
        assert game_low_clock.id in matched
        assert game_hasty.id in matched
        assert game_unrushed.id not in matched, "unrushed is not in the selected tempo tags"

    @pytest.mark.asyncio
    async def test_cross_user_isolation(self, db_session: AsyncSession) -> None:
        """Another user's game_flaws rows do not satisfy the EXISTS for the requesting user.

        T-108-07: flaw_exists_from_table always includes GameFlaw.user_id == user_id.
        User 77001's flaw row must not satisfy the EXISTS when the query is for user 77002.
        """
        # Game owned by user 77001 with a blunder flaw.
        game = await _seed_game(db_session, user_id=77001)
        await bulk_insert_game_flaws(
            db_session,
            [_flaw_row(user_id=77001, game_id=game.id, ply=2, severity=_SEV_BLUNDER)],
        )

        # User 77002 owns no games and has no flaw rows — the EXISTS must not cross users.
        # We query as user 77002 but select from user 77001's game to directly test the
        # user_id scope inside the EXISTS subquery.
        from app.services.flaws_service import FlawSeverity
        from typing import cast
        from collections.abc import Sequence

        pred = flaw_exists_from_table(
            user_id=77002,  # different user
            severity=cast(Sequence[FlawSeverity], ["blunder"]),
            tags=[],
        )
        stmt = select(Game.id).where(Game.id == game.id, pred)
        rows = set((await db_session.execute(stmt)).scalars().all())
        assert game.id not in rows, (
            "EXISTS scoped to user 77002 must not find user 77001's flaw rows (T-108-07)"
        )

    @pytest.mark.asyncio
    async def test_game_with_no_flaw_rows_excluded_by_severity_filter(
        self, db_session: AsyncSession
    ) -> None:
        """A game with no game_flaws rows does not satisfy a non-trivial severity filter."""
        game = await _seed_game(db_session)
        # No flaw rows inserted.

        matched = await _games_matching_exists(
            db_session,
            user_id=77001,
            severity=["blunder"],
            tags=[],
            candidate_game_ids={game.id},
        )
        assert game.id not in matched, "a game with no flaw rows must not satisfy severity filter"
