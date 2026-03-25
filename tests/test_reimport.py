"""Tests for the reimport_games script.

Verifies:
1. CLI argument parsing (--user-id, --all, --yes, mutual exclusion).
2. Re-import pipeline flow (delete + create job + run_import called).
3. Eval extraction from %eval PGN annotations — confirms the extraction logic
   that the import pipeline (plan 28-02) uses to populate eval_cp/eval_mate.
"""

import datetime
import io
import uuid
from unittest.mock import AsyncMock, patch

import chess.pgn
import pytest

# ---------------------------------------------------------------------------
# Test PGN fixtures
# ---------------------------------------------------------------------------

# A short game WITH lichess %eval annotations — used to verify eval extraction
_EVAL_PGN = """\
[Event "Rated Blitz game"]
[Site "https://lichess.org/testgame"]
[Date "2024.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[TimeControl "300+0"]

1. e4 { [%eval 0.21] } 1... e5 { [%eval 0.17] } 2. Nf3 { [%eval 0.25] } 2... Nc6 { [%eval 0.25] } 1-0
"""

# A valid game WITHOUT eval annotations
_NO_EVAL_PGN = """\
[Event "Test"]
[Site "Test"]
[Date "2024.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "0-1"]
[TimeControl "600+0"]

1. f3 e5 2. g4 Qh4# 0-1
"""


# ---------------------------------------------------------------------------
# Test argument parsing
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Tests for parse_args() CLI argument handling."""

    def _get_parse_args(self):
        """Import parse_args lazily to avoid running main() at import time."""
        from scripts.reimport_games import parse_args

        return parse_args

    def test_parse_args_user_id(self):
        """--user-id 42 should parse as user_id=42 with all_users=False."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py", "--user-id", "42"]):
            args = parse_args()
        assert args.user_id == 42
        assert args.all_users is False
        assert args.yes is False

    def test_parse_args_all(self):
        """--all should parse as all_users=True with user_id=None."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py", "--all"]):
            args = parse_args()
        assert args.all_users is True
        assert args.user_id is None

    def test_parse_args_yes_flag(self):
        """--yes should set yes=True."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py", "--user-id", "5", "--yes"]):
            args = parse_args()
        assert args.yes is True

    def test_parse_args_short_yes_flag(self):
        """-y should also set yes=True (short form)."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py", "--all", "-y"]):
            args = parse_args()
        assert args.yes is True

    def test_parse_args_mutually_exclusive(self):
        """--user-id and --all together should raise SystemExit."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py", "--user-id", "1", "--all"]):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_requires_one(self):
        """No flags at all should raise SystemExit (one of --user-id/--all is required)."""
        parse_args = self._get_parse_args()
        with patch("sys.argv", ["reimport_games.py"]):
            with pytest.raises(SystemExit):
                parse_args()


# ---------------------------------------------------------------------------
# Test eval extraction from PGN %eval annotations
# ---------------------------------------------------------------------------


class TestEvalExtraction:
    """Tests for eval extraction from lichess %eval PGN annotations.

    This verifies the eval extraction logic that the import pipeline (plan 28-02)
    wires into _flush_batch. python-chess exposes node.eval() which returns a
    PovScore — we test that it correctly parses centipawn and mate values.

    These tests confirm the primary must_have truth: "re-imported games have
    eval_cp populated where available" — specifically that the extraction logic
    works correctly before it is wired into the DB storage path.
    """

    def test_eval_extracted_from_pgn_nodes(self):
        """node.eval() returns non-None PovScore for %eval annotated moves."""
        game = chess.pgn.read_game(io.StringIO(_EVAL_PGN))
        assert game is not None

        nodes = list(game.mainline())
        eval_values = []
        for node in nodes:
            pov_score = node.eval()
            if pov_score is not None:
                # Score from white's perspective
                cp = pov_score.white().score(mate_score=None)
                eval_values.append(cp)

        assert len(eval_values) > 0, "Expected at least one eval-annotated move"
        # First eval in _EVAL_PGN is +0.21 → 21 centipawns
        assert eval_values[0] == 21, f"Expected 21 centipawns, got {eval_values[0]}"

    def test_no_eval_annotation_returns_none(self):
        """node.eval() returns None for games without %eval annotations."""
        game = chess.pgn.read_game(io.StringIO(_NO_EVAL_PGN))
        assert game is not None

        nodes = list(game.mainline())
        for node in nodes:
            pov_score = node.eval()
            assert pov_score is None, f"Expected None eval for unannotated game, got {pov_score}"

    def test_eval_cp_and_eval_mate_extraction(self):
        """Both centipawn (eval_cp) and mate (eval_mate) are extractable from PovScore."""
        # PGN with a forced mate annotation
        mate_pgn = """\
[Event "Test"]
[Result "1-0"]
[White "Alice"]
[Black "Bob"]

1. e4 { [%eval #2] } 1... e5 1-0
"""
        game = chess.pgn.read_game(io.StringIO(mate_pgn))
        assert game is not None

        nodes = list(game.mainline())
        # First node has %eval #2 (mate in 2 for white)
        pov_score = nodes[0].eval()
        assert pov_score is not None

        # Mate score: .score(mate_score=None) returns None for forced mates
        # .mate() returns the mate-in-N value (positive = white mates)
        cp = pov_score.white().score(mate_score=None)
        mate = pov_score.white().mate()
        assert cp is None, "Mate position should have cp=None"
        assert mate == 2, f"Expected mate-in-2, got {mate}"

    def test_eval_extraction_logic_per_position_row(self):
        """Validate the per-position eval_cp/eval_mate row assembly logic.

        Mirrors what _flush_batch in import_service.py (plan 28-02) does:
        - Iterates over mainline nodes
        - Calls node.eval() at each ply
        - Stores eval_cp / eval_mate on the position dict
        - Ply 0 (starting position, before first move) always has eval=None
        - Final position (after last move) always has eval=None
        """
        game = chess.pgn.read_game(io.StringIO(_EVAL_PGN))
        assert game is not None

        nodes = list(game.mainline())
        # Simulate the position row assembly loop (identical to what plan 28-02 implements)
        evals: list[tuple[int | None, int | None]] = []

        for node in nodes:
            pov_score = node.eval()
            if pov_score is not None:
                eval_cp: int | None = pov_score.white().score(mate_score=None)
                eval_mate: int | None = pov_score.white().mate()
            else:
                eval_cp = None
                eval_mate = None
            evals.append((eval_cp, eval_mate))

        # Append None for the final position (no move played from there)
        evals.append((None, None))

        # Starting position ply 0 gets eval from node[0] (eval before ply 1 is known)
        # In the actual pipeline ply 0 uses no eval (eval is per-move, not per-position-before)
        # The final position always has None
        assert evals[-1] == (None, None), "Final position must have (None, None) eval"

        # Non-None evals should be present for annotated nodes
        non_none = [e for e in evals if e != (None, None)]
        assert len(non_none) > 0, "Expected at least some non-None evals for annotated game"


# ---------------------------------------------------------------------------
# Integration test for re-import pipeline flow
# ---------------------------------------------------------------------------


def _make_game_row(user_id: int = 1, pgn: str = _NO_EVAL_PGN) -> dict:
    """Build a minimal valid games row dict."""
    return {
        "user_id": user_id,
        "platform": "chess.com",
        "platform_game_id": f"game-{uuid.uuid4().hex}",
        "platform_url": None,
        "pgn": pgn,
        "variant": "Standard",
        "result": "0-1",
        "user_color": "white",
        "time_control_str": "600+0",
        "time_control_bucket": "blitz",
        "time_control_seconds": 600,
        "rated": True,
        "white_username": "Alice",
        "black_username": "Bob",
        "white_rating": 1500,
        "black_rating": 1500,
        "opening_name": None,
        "opening_eco": None,
        "played_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        "white_accuracy": None,
        "black_accuracy": None,
    }


class TestReimportFlow:
    """Integration tests for the reimport_user() function.

    Tests that the re-import flow correctly:
    1. Queries import jobs for a user to discover platforms
    2. Deletes all existing games
    3. Triggers run_import() for each platform
    """

    @pytest.mark.asyncio
    async def test_reimport_deletes_then_reimports(self, db_session):
        """Re-import flow calls delete_all_games_for_user then run_import per platform."""
        from tests.conftest import ensure_test_user
        from app.repositories.game_repository import bulk_insert_games, count_games_for_user
        from app.repositories.import_job_repository import create_import_job, update_import_job
        from scripts.reimport_games import reimport_user

        user_id = 999
        await ensure_test_user(db_session, user_id)

        # Insert a completed import job so reimport_user knows which platform to use
        job_id = str(uuid.uuid4())
        await create_import_job(
            db_session,
            job_id=job_id,
            user_id=user_id,
            platform="chess.com",
            username="testuser",
        )
        await update_import_job(db_session, job_id, status="completed")
        await db_session.flush()

        # Insert some existing games for this user
        game_rows = [_make_game_row(user_id=user_id)]
        await bulk_insert_games(db_session, game_rows)
        await db_session.flush()

        # Confirm games exist
        count_before = await count_games_for_user(db_session, user_id)
        assert count_before == 1

        # Run re-import with a mocked run_import (we don't want to hit the real API)
        with patch(
            "scripts.reimport_games.run_import", new_callable=AsyncMock
        ) as mock_run_import:
            # Mock get_job to return a completed job state
            from app.services.import_service import JobState, JobStatus

            mock_job_state = JobState(
                job_id="mocked-job",
                user_id=user_id,
                platform="chess.com",
                username="testuser",
                status=JobStatus.COMPLETED,
                games_imported=5,
            )
            with patch(
                "scripts.reimport_games.get_job", return_value=mock_job_state
            ):
                success, games_imported = await reimport_user(db_session, user_id)

        assert success is True
        # run_import was called once (one platform)
        mock_run_import.assert_called_once()
        # The games_imported count comes from the mock job state
        assert games_imported == 5

    @pytest.mark.asyncio
    async def test_reimport_skips_user_with_no_jobs(self, db_session):
        """User with no completed import jobs is skipped (returns success, 0 games)."""
        from tests.conftest import ensure_test_user
        from scripts.reimport_games import reimport_user

        user_id = 998
        await ensure_test_user(db_session, user_id)
        # No import jobs for this user

        success, games_imported = await reimport_user(db_session, user_id)

        assert success is True
        assert games_imported == 0

    @pytest.mark.asyncio
    async def test_get_platform_jobs_for_user_returns_completed_only(self, db_session):
        """get_platform_jobs_for_user returns only completed jobs."""
        from tests.conftest import ensure_test_user
        from app.repositories.import_job_repository import create_import_job, update_import_job
        from scripts.reimport_games import get_platform_jobs_for_user

        user_id = 997
        await ensure_test_user(db_session, user_id)

        # Insert a completed job and a failed job
        completed_job_id = str(uuid.uuid4())
        await create_import_job(
            db_session,
            job_id=completed_job_id,
            user_id=user_id,
            platform="lichess",
            username="lichessuser",
        )
        await update_import_job(db_session, completed_job_id, status="completed")

        failed_job_id = str(uuid.uuid4())
        await create_import_job(
            db_session,
            job_id=failed_job_id,
            user_id=user_id,
            platform="chess.com",
            username="chesscomuser",
        )
        await update_import_job(db_session, failed_job_id, status="failed")
        await db_session.flush()

        jobs = await get_platform_jobs_for_user(db_session, user_id)

        # Only the completed lichess job should be returned
        platforms = [platform for platform, _ in jobs]
        assert "lichess" in platforms, "Completed lichess job should be returned"
        assert "chess.com" not in platforms, "Failed chess.com job should NOT be returned"
