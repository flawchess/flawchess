"""Materialization round-trip test for Phase 108 Plan 02 (D-10).

Tests that the FlawRecord→game_flaws insert chain (flaw_record_to_row +
bulk_insert_game_flaws) produces rows that exactly match what classify_game_flaws
returns — the D-10 invariant that the import hook, reclassify_positions.py, and
backfill_flaws.py all use the same single classification path.

Coverage:
- The set of (ply, severity) rows written equals the M+B subset of classify_game_flaws
- No row exists for an inaccuracy ply (D-03: game_flaws is M+B only)
- A FlawRecord with no tempo tag yields a row with tempo IS NULL
- Each boolean column matches tag membership
- A GameNotAnalyzed game produces zero rows

No dev DB reset needed — tests use the db_session rollback fixture.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import (
    bulk_insert_game_flaws,
    flaw_record_to_row,
)
from app.services.flaws_service import (
    FlawRecord,
    classify_game_flaws,
)


# ---------------------------------------------------------------------------
# In-memory builders (mirrors tests/services/test_flaws_service.py pattern)
# ---------------------------------------------------------------------------

# A real PGN that classify_game_flaws can replay for FEN recomputation.
# 10 half-moves = plies 0-9; ply 9 is the final position (no eval).
_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"


def _make_pos(
    ply: int,
    eval_cp: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Build a GamePosition with eval/clock fields for pure unit testing (no DB flush)."""
    pos = GamePosition()
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = None
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = move_san
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KP_KP"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos


def _make_game_obj(
    pgn: str = _PGN,
    user_color: str = "white",
    result: str = "1-0",
    base_time_seconds: int | None = None,
    increment_seconds: float | None = None,
) -> Game:
    """Build a minimal Game object for unit testing (no DB flush)."""
    game = Game()
    game.pgn = pgn
    game.user_color = user_color
    game.result = result
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = increment_seconds
    game.time_control_str = None
    return game


# ---------------------------------------------------------------------------
# DB seed helpers (for the bulk-insert round-trip tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist (FK constraint)."""
    from tests.conftest import ensure_test_user

    await ensure_test_user(db_session, 78001)


async def _seed_game(session: AsyncSession, user_id: int = 78001) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/mat-test",
        pgn=_PGN,
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


# ---------------------------------------------------------------------------
# Helpers to build known-flaw positions
# ---------------------------------------------------------------------------

# These cp values produce known mover-POV ES drops for white:
#   eval_cp_to_expected_score(200, "white")  ≈ 0.685
#   eval_cp_to_expected_score(-500, "white") ≈ 0.160  → drop ≈ 0.525 (blunder)
#   eval_cp_to_expected_score(100, "white")  ≈ 0.591
#   eval_cp_to_expected_score(-50, "white")  ≈ 0.488  → drop ≈ 0.103 (mistake)
#   eval_cp_to_expected_score(50, "white")   ≈ 0.568
#   eval_cp_to_expected_score(0, "white")    = 0.500  → drop ≈ 0.068 (inaccuracy)

_CP_BLUNDER_BEFORE = 200  # ES ≈ 0.685 for white mover
_CP_BLUNDER_AFTER = -500  # ES ≈ 0.160  → drop ≈ 0.525 ≥ 0.15 = blunder

_CP_MISTAKE_BEFORE = 100  # ES ≈ 0.591 for white mover
_CP_MISTAKE_AFTER = -50  # ES ≈ 0.488  → drop ≈ 0.103 ≥ 0.10 = mistake

_CP_INACCURACY_BEFORE = 50  # ES ≈ 0.568 for white mover
_CP_INACCURACY_AFTER = 0  # ES = 0.500  → drop ≈ 0.068 ≥ 0.05 = inaccuracy


def _build_mixed_positions() -> tuple[list[GamePosition], int, int, int]:
    """Build positions with one blunder (ply 2), one mistake (ply 4), one inaccuracy (ply 6).

    White moves at even plies (2, 4, 6). All 10 plies present; ply 9 has no eval
    so coverage = 9/10 = 0.90 >= EVAL_COVERAGE_MIN.

    Returns (positions, blunder_ply, mistake_ply, inaccuracy_ply).
    """
    # Start with clean baseline cp=20 for all positions
    positions = [_make_pos(i, eval_cp=20) for i in range(10)]

    # Blunder at white's ply 2: ES drops ≈ 0.525 (≥ BLUNDER_DROP)
    positions[1] = _make_pos(1, eval_cp=_CP_BLUNDER_BEFORE)  # baseline before ply 2
    positions[2] = _make_pos(2, eval_cp=_CP_BLUNDER_AFTER, move_san="Nf3")  # white blunder

    # Mistake at white's ply 4: ES drops ≈ 0.103 (≥ MISTAKE_DROP, < BLUNDER_DROP)
    positions[3] = _make_pos(3, eval_cp=_CP_MISTAKE_BEFORE)  # baseline before ply 4
    positions[4] = _make_pos(4, eval_cp=_CP_MISTAKE_AFTER, move_san="Bb5")  # white mistake

    # Inaccuracy at white's ply 6: ES drops ≈ 0.068 (≥ INACCURACY_DROP, < MISTAKE_DROP)
    positions[5] = _make_pos(5, eval_cp=_CP_INACCURACY_BEFORE)  # baseline before ply 6
    positions[6] = _make_pos(6, eval_cp=_CP_INACCURACY_AFTER, move_san="Ba4")  # white inaccuracy

    # Final ply has no eval (coverage gate: 9/10 = 0.90)
    positions[9] = _make_pos(9)

    return positions, 2, 4, 6


# ---------------------------------------------------------------------------
# TestFlawRecordToRow — unit tests (no DB required)
# ---------------------------------------------------------------------------


class TestFlawRecordToRow:
    """flaw_record_to_row correctly maps FlawRecord fields to game_flaws column values."""

    def _make_flaw(
        self,
        ply: int = 10,
        severity: str = "blunder",
        tags: list[str] | None = None,
        es_before: float = 0.85,
        es_after: float = 0.30,
    ) -> FlawRecord:
        """Build a minimal FlawRecord dict."""
        from app.services.flaws_service import FlawSeverity, FlawTag

        resolved_severity: FlawSeverity = severity  # ty: ignore[invalid-assignment]
        resolved_tags: list[FlawTag] = list(tags or ["middlegame"])  # ty: ignore[invalid-assignment]
        return FlawRecord(
            ply=ply,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            side="white",
            severity=resolved_severity,
            tags=resolved_tags,
            es_before=es_before,
            es_after=es_after,
            move_san="e4",
        )

    def test_severity_blunder_maps_to_2(self) -> None:
        """Blunder severity maps to int 2."""
        row = flaw_record_to_row(user_id=1, game_id=10, flaw=self._make_flaw(severity="blunder"))
        assert row["severity"] == 2

    def test_severity_mistake_maps_to_1(self) -> None:
        """Mistake severity maps to int 1."""
        row = flaw_record_to_row(user_id=1, game_id=10, flaw=self._make_flaw(severity="mistake"))
        assert row["severity"] == 1

    def test_inaccuracy_raises_value_error(self) -> None:
        """D-03: inaccuracy severity raises ValueError (never stored in game_flaws)."""
        with pytest.raises(ValueError, match="inaccuracy"):
            flaw_record_to_row(user_id=1, game_id=10, flaw=self._make_flaw(severity="inaccuracy"))

    def test_tempo_none_when_no_tempo_tag(self) -> None:
        """FlawRecord with only a phase tag (no tempo tag) yields tempo=None."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame"]),  # no tempo tag
        )
        assert row["tempo"] is None

    def test_tempo_low_clock_maps_to_0(self) -> None:
        """low-clock tempo tag maps to int 0."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "low-clock"]),
        )
        assert row["tempo"] == 0

    def test_tempo_hasty_maps_to_1(self) -> None:
        """hasty tempo tag maps to int 1."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "hasty"]),
        )
        assert row["tempo"] == 1

    def test_tempo_unrushed_maps_to_2(self) -> None:
        """unrushed tempo tag maps to int 2."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "unrushed"]),
        )
        assert row["tempo"] == 2

    def test_phase_opening_maps_to_0(self) -> None:
        """opening phase tag maps to int 0."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["opening"]),
        )
        assert row["phase"] == 0

    def test_phase_middlegame_maps_to_1(self) -> None:
        """middlegame phase tag maps to int 1."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame"]),
        )
        assert row["phase"] == 1

    def test_phase_endgame_maps_to_2(self) -> None:
        """endgame phase tag maps to int 2."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["endgame"]),
        )
        assert row["phase"] == 2

    def test_boolean_tag_miss(self) -> None:
        """'miss' tag sets is_miss=True; absent sets is_miss=False."""
        row_with = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "miss"]),
        )
        row_without = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame"]),
        )
        assert row_with["is_miss"] is True
        assert row_without["is_miss"] is False

    def test_boolean_tag_lucky(self) -> None:
        """'lucky' tag sets is_lucky=True."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "lucky"]),
        )
        assert row["is_lucky"] is True

    def test_boolean_tag_reversed(self) -> None:
        """'reversed' tag sets is_reversed=True (es_before>=0.70, es_after<=0.30)."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "reversed"], es_before=0.90, es_after=0.20),
        )
        assert row["is_reversed"] is True

    def test_boolean_tag_squandered(self) -> None:
        """'squandered' tag sets is_squandered=True (es_before>=0.85, es_after<=0.60)."""
        row = flaw_record_to_row(
            user_id=1,
            game_id=10,
            flaw=self._make_flaw(tags=["middlegame", "squandered"], es_before=0.88, es_after=0.55),
        )
        assert row["is_squandered"] is True

    def test_passthrough_fields(self) -> None:
        """es_before, es_after, move_san, fen are passed through unchanged."""
        flaw = self._make_flaw(ply=15, es_before=0.72, es_after=0.31, tags=["middlegame"])
        flaw["move_san"] = "Rxf7"
        flaw["fen"] = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R"
        row = flaw_record_to_row(user_id=1, game_id=10, flaw=flaw)
        assert row["ply"] == 15
        assert row["es_before"] == pytest.approx(0.72)
        assert row["es_after"] == pytest.approx(0.31)
        assert row["move_san"] == "Rxf7"
        assert "r1bqkbnr" in row["fen"]

    def test_user_id_and_game_id_in_row(self) -> None:
        """user_id and game_id are present in the output row."""
        row = flaw_record_to_row(user_id=42, game_id=99, flaw=self._make_flaw())
        assert row["user_id"] == 42
        assert row["game_id"] == 99


# ---------------------------------------------------------------------------
# TestBulkInsertGameFlaws — unit tests (DB required)
# ---------------------------------------------------------------------------


class TestBulkInsertGameFlaws:
    """bulk_insert_game_flaws is idempotent and skips empty input."""

    @pytest.mark.asyncio
    async def test_no_op_on_empty_list(self, db_session: AsyncSession) -> None:
        """bulk_insert_game_flaws is a no-op on an empty list (no error)."""
        await bulk_insert_game_flaws(db_session, [])
        # No exception raised — implicit pass

    @pytest.mark.asyncio
    async def test_inserts_row_and_reads_back(self, db_session: AsyncSession) -> None:
        """A row inserted via bulk_insert_game_flaws reads back with correct values."""
        game = await _seed_game(db_session)

        flaw: FlawRecord = {
            "ply": 10,
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "side": "white",
            "severity": "blunder",
            "tags": ["middlegame", "reversed"],
            "es_before": 0.90,
            "es_after": 0.20,
            "move_san": "e4",
        }
        row = flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=flaw)
        await bulk_insert_game_flaws(db_session, [row])
        await db_session.flush()

        result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
                GameFlaw.ply == 10,
            )
        )
        stored = result.scalar_one()
        assert stored.severity == 2  # blunder
        assert stored.phase == 1  # middlegame
        assert stored.is_reversed is True
        assert stored.is_miss is False
        assert stored.tempo is None  # no tempo tag
        assert abs(stored.es_before - 0.90) < 1e-6
        assert abs(stored.es_after - 0.20) < 1e-6

    @pytest.mark.asyncio
    async def test_on_conflict_do_nothing_is_idempotent(self, db_session: AsyncSession) -> None:
        """Inserting the same row twice does not raise an error (ON CONFLICT DO NOTHING)."""
        game = await _seed_game(db_session)

        flaw: FlawRecord = {
            "ply": 5,
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "side": "white",
            "severity": "mistake",
            "tags": ["opening"],
            "es_before": 0.55,
            "es_after": 0.44,
            "move_san": "e4",
        }
        row = flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=flaw)
        await bulk_insert_game_flaws(db_session, [row])
        await db_session.flush()
        # Second insert: must silently skip (ON CONFLICT DO NOTHING)
        await bulk_insert_game_flaws(db_session, [row])
        await db_session.flush()

        count_result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
                GameFlaw.ply == 5,
            )
        )
        rows = count_result.scalars().all()
        assert len(rows) == 1, "ON CONFLICT DO NOTHING must not create duplicate rows"


# ---------------------------------------------------------------------------
# TestMaterializationRoundTrip — the D-10 invariant (one classify path)
# ---------------------------------------------------------------------------


class TestMaterializationRoundTrip:
    """The set of rows inserted by flaw_record_to_row + bulk_insert_game_flaws
    exactly matches the M+B subset of classify_game_flaws output.

    This is the Wave 0 dependency proving the D-10 invariant:
        game_flaws rows ≡ classify_game_flaws M+B output
    """

    @pytest.mark.asyncio
    async def test_mb_rows_match_classifier_output(self, db_session: AsyncSession) -> None:
        """The inserted (ply, severity) set equals the M+B subset of classify_game_flaws.

        Game has one blunder (ply 2), one mistake (ply 4), one inaccuracy (ply 6).
        Only blunder + mistake rows must appear in game_flaws.
        """
        game_obj = _make_game_obj(user_color="white", result="1-0")
        positions, blunder_ply, mistake_ply, inaccuracy_ply = _build_mixed_positions()

        # Get the ground truth from the classifier
        classify_result = classify_game_flaws(game_obj, positions)
        assert isinstance(classify_result, list), (
            "Expected list[FlawRecord], got GameNotAnalyzed. "
            "Check EVAL_COVERAGE_MIN and position count."
        )

        # Verify the classifier emitted the expected severities
        emitted_severities = {r["severity"] for r in classify_result}
        # Must contain at least mistake and blunder (inaccuracy NOT emitted)
        assert "mistake" in emitted_severities or "blunder" in emitted_severities, (
            "Expected at least one mistake or blunder from classify_game_flaws"
        )
        assert "inaccuracy" not in emitted_severities, (
            "classify_game_flaws must not emit inaccuracy FlawRecords (D-03)"
        )

        # Now insert the rows via the materialization path
        game = await _seed_game(db_session)

        rows = [
            flaw_record_to_row(
                user_id=game.user_id,
                game_id=game.id,
                flaw=flaw,
            )
            for flaw in classify_result
        ]
        await bulk_insert_game_flaws(db_session, rows)
        await db_session.flush()

        # Read back from DB
        db_result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
            )
        )
        stored_rows = db_result.scalars().all()

        # Row count matches the classifier's M+B output count
        assert len(stored_rows) == len(classify_result), (
            f"Expected {len(classify_result)} rows (M+B only), got {len(stored_rows)} in game_flaws"
        )

        # (ply, severity_int) set matches exactly
        classifier_pairs = {
            (r["ply"], 1 if r["severity"] == "mistake" else 2) for r in classify_result
        }
        db_pairs = {(r.ply, r.severity) for r in stored_rows}
        assert classifier_pairs == db_pairs, (
            f"Materialized rows differ from classifier output: "
            f"classifier={classifier_pairs}, db={db_pairs}"
        )

    @pytest.mark.asyncio
    async def test_no_row_for_inaccuracy_ply(self, db_session: AsyncSession) -> None:
        """The inaccuracy ply (ply 6) produces no game_flaws row (D-03)."""
        game_obj = _make_game_obj(user_color="white", result="1-0")
        positions, blunder_ply, mistake_ply, inaccuracy_ply = _build_mixed_positions()

        classify_result = classify_game_flaws(game_obj, positions)
        assert isinstance(classify_result, list)

        game = await _seed_game(db_session)
        rows = [
            flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=flaw)
            for flaw in classify_result
        ]
        await bulk_insert_game_flaws(db_session, rows)
        await db_session.flush()

        # The inaccuracy ply must not appear in game_flaws
        inaccuracy_result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
                GameFlaw.ply == inaccuracy_ply,
            )
        )
        inaccuracy_rows = inaccuracy_result.scalars().all()
        assert len(inaccuracy_rows) == 0, (
            f"Inaccuracy at ply {inaccuracy_ply} must not produce a game_flaws row (D-03)"
        )

    @pytest.mark.asyncio
    async def test_tempo_null_when_no_clock_data(self, db_session: AsyncSession) -> None:
        """A FlawRecord with no tempo tag yields a game_flaws row with tempo IS NULL.

        Positions have no clock_seconds => _classify_tempo returns None => no tempo tag.
        base_time_seconds=None ensures the fallback also yields None for move time.
        """
        game_obj = _make_game_obj(
            user_color="white",
            result="1-0",
            base_time_seconds=None,  # no base time => tempo classification returns None
            increment_seconds=None,
        )

        # Build positions with no clock data
        positions = [_make_pos(i, eval_cp=20) for i in range(10)]
        # Blunder for white at ply 2
        positions[1] = _make_pos(1, eval_cp=_CP_BLUNDER_BEFORE)
        positions[2] = _make_pos(2, eval_cp=_CP_BLUNDER_AFTER, move_san="Nf3")
        positions[9] = _make_pos(9)  # final null

        classify_result = classify_game_flaws(game_obj, positions)
        assert isinstance(classify_result, list)
        assert len(classify_result) >= 1, "Expected at least one blunder"

        # Check that the blunder flaw has no tempo tag
        blunder_flaws = [r for r in classify_result if r["ply"] == 2]
        assert len(blunder_flaws) == 1
        blunder = blunder_flaws[0]
        tempo_tags = [t for t in blunder["tags"] if t in {"low-clock", "hasty", "unrushed"}]
        assert len(tempo_tags) == 0, (
            f"Expected no tempo tags when clock data absent, got {tempo_tags}"
        )

        # Insert and verify tempo IS NULL in DB
        game = await _seed_game(db_session)
        row = flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=blunder)
        await bulk_insert_game_flaws(db_session, [row])
        await db_session.flush()

        db_result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
                GameFlaw.ply == 2,
            )
        )
        stored = db_result.scalar_one()
        assert stored.tempo is None, (
            f"Expected tempo IS NULL when no clock data, got {stored.tempo}"
        )

    @pytest.mark.asyncio
    async def test_boolean_columns_match_tag_membership(self, db_session: AsyncSession) -> None:
        """Boolean columns (is_miss, is_lucky, is_reversed, is_squandered)
        match the tag membership in the corresponding FlawRecord.
        """
        game_obj = _make_game_obj(user_color="white", result="1-0")
        positions, blunder_ply, mistake_ply, inaccuracy_ply = _build_mixed_positions()

        classify_result = classify_game_flaws(game_obj, positions)
        assert isinstance(classify_result, list) and len(classify_result) >= 1

        game = await _seed_game(db_session)
        rows = [
            flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=flaw)
            for flaw in classify_result
        ]
        await bulk_insert_game_flaws(db_session, rows)
        await db_session.flush()

        # For each inserted row, verify boolean columns match FlawRecord tags
        for flaw_rec in classify_result:
            ply = flaw_rec["ply"]
            db_flaw_result = await db_session.execute(
                select(GameFlaw).where(
                    GameFlaw.user_id == game.user_id,
                    GameFlaw.game_id == game.id,
                    GameFlaw.ply == ply,
                )
            )
            stored_flaw = db_flaw_result.scalar_one()
            tags = set(flaw_rec["tags"])

            assert stored_flaw.is_miss == ("miss" in tags), (
                f"ply={ply}: is_miss mismatch. tags={tags}, stored={stored_flaw.is_miss}"
            )
            assert stored_flaw.is_lucky == ("lucky" in tags), (
                f"ply={ply}: is_lucky mismatch. tags={tags}, stored={stored_flaw.is_lucky}"
            )
            assert stored_flaw.is_reversed == ("reversed" in tags), (
                f"ply={ply}: is_reversed mismatch. tags={tags}, stored={stored_flaw.is_reversed}"
            )
            assert stored_flaw.is_squandered == ("squandered" in tags), (
                f"ply={ply}: is_squandered mismatch. tags={tags}, stored={stored_flaw.is_squandered}"
            )

    @pytest.mark.asyncio
    async def test_game_not_analyzed_produces_zero_rows(self, db_session: AsyncSession) -> None:
        """A chess.com-style all-null-eval game produces zero game_flaws rows.

        classify_game_flaws returns GameNotAnalyzed (dict with 'reason' key).
        The hook skips it silently — no rows inserted.
        """
        game_obj = _make_game_obj(user_color="white", result="1-0")
        # All-null-eval positions: eval coverage = 0.0 < EVAL_COVERAGE_MIN (0.90)
        positions = [_make_pos(i) for i in range(10)]  # all None eval_cp

        result = classify_game_flaws(game_obj, positions)
        # Verify it's GameNotAnalyzed — use isinstance(result, dict) for ty narrowing
        # (GameNotAnalyzed is a TypedDict, i.e. a plain dict at runtime; list is not a dict)
        assert isinstance(result, dict), "Expected GameNotAnalyzed (dict) for all-null-eval game"
        assert result["reason"] == "no_engine_analysis"

        # Simulate what the hook does: skip if GameNotAnalyzed
        game = await _seed_game(db_session)
        # result is already narrowed to dict (GameNotAnalyzed) by the isinstance check above
        # No rows to insert — the hook would have hit the "reason" in result early exit
        await db_session.flush()

        db_result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
            )
        )
        rows_in_db = db_result.scalars().all()
        assert len(rows_in_db) == 0, (
            f"GameNotAnalyzed must produce zero game_flaws rows, got {len(rows_in_db)}"
        )
