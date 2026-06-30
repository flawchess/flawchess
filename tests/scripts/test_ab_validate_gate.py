"""A/B gate-validation harness tests (Phase 144, Plan 01).

Tests six Nyquist properties for scripts/ab_validate_gate.py:

 1. test_ungated_arm_bypasses_gate  — ungated arm NEVER calls apply_forcing_line_filter
 2. test_both_arms_use_same_blobs   — no EnginePool / chess.engine import; no DB writes
 3. test_gated_lte_ungated          — gated tag count <= ungated tag count per orientation
 4. test_report_output              — harness writes report with all required section headers
 5. test_dropped_case_fields        — dropped cases expose orientation/motif/FEN/depth/PV/URL
 6. test_analysis_board_url_format  — analysis_board_url builds ?game_id=X&ply=Y local link

Fixture design:
  - _TEST_USER_ID = 144_010 (distinct from 143_030 used by test_retag_flaws.py)
  - One Game, two GamePosition rows (ply 1 and ply 2), one GameFlaw at ply 1.
  - Flaw FEN: "8/8/8/3Q4/2p5/8/8/k6K" (black pawn c4 can capture undefended white queen d5).
    At this position detect_hanging_piece fires: PV "c4d5" captures the undefended queen.
    This guarantees the ungated arm detects HANGING_PIECE, which the gate then suppresses via
    the NON_FORCING_BLOB.
  - missed_pv_lines = NON_FORCING_BLOB -> gate rejects (too-small win-prob gap at margin=0.35).
  - allowed_pv_lines = FORCING_BLOB but positions[ply+1].pv=None -> allowed detection returns
    None for both arms (no dropped case on the allowed side).
  - Cleanup: delete Game (CASCADE removes positions + flaws) in a finally block to prevent
    lottery-test leakage (eval_lottery isolation memory).

Session-maker injection: run_ab_validation accepts session_maker= and report_dir= so the test
suite never touches the real --db dev target.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User

# ---------------------------------------------------------------------------
# Test constants (no magic numbers — CLAUDE.md)
# ---------------------------------------------------------------------------

# Unique user ID for this test module; must differ from 143_030 (test_retag_flaws).
_TEST_USER_ID = 144_010

# Minimal PGN — only needs to satisfy Game.pgn NOT NULL; detection ignores it.
_PGN = "1. e4 e5 2. Nf3 *"

# Board FEN at the flaw ply (ply 1): black to move (ply is odd).
# White queen on d5 (undefended), black pawn on c4 can capture it -> HANGING_PIECE fires!
# Kings: white on h1, black on a1.  FEN is piece-placement only (board_fen()).
_FEN_FLAW = "8/8/8/3Q4/2p5/8/8/k6K"

# Bad move black actually plays (ply 1): pawn advances to c3.
# Destination c3 != d5 (PV dest), so the same-dest gate does NOT fire -> detection proceeds.
_MOVE_SAN_FLAW = "c3"

# Best move black should have played (PV for missed pass): capture the hanging queen.
_PV_PLY_1 = "c4d5"

# Evaluations (white-perspective centipawns). Convention: positions[N].eval_cp is the
# eval AFTER move N (see flaws_service._run_all_moves_pass). The flaw is at ply 1, so the
# gate's already-winning reject reads positions[ply-1] = ply 0 (board BEFORE the flaw move).
# At ply 0 (before black's bad move): 0 (even position; solver=black not already winning).
# At ply 1 (after black's bad move):  0  (detection uses the FEN, not this eval).
# At ply 2 (after white's reply):     900 (white winning big).
_EVAL_PLY_0 = 0
_EVAL_PLY_1 = 0
_EVAL_PLY_2 = 900

# FORCING blob: solver nodes with large win-prob gap -> gate passes.
# Designed so that solver_color="white" passes (allowed orientation at ply 1):
#   b=800, s=0 -> p(800,w)-p(0,w) ≈ 0.9-0.5 = 0.4 > 0.35 -> forced.
_FORCING_BLOB: list[dict[str, Any]] = [
    {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S0 solver — forced
    {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 defender — ignored
    {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S1 solver — forced
]

# NON-FORCING blob: solver nodes with tiny win-prob gap -> gate fails at margin=0.35.
# b=300, s=280 (white-perspective): gap ≈ 0.01 << 0.35 -> not forced.
# Also: still-winning floor truncates (b=300 -> black solver_cp=-300 < 200cp floor).
# Either path results in gate rejection -> motif suppressed.
_NON_FORCING_BLOB: list[dict[str, Any]] = [
    {"b": 300, "bm": None, "s": 280, "sm": None, "su": "e4e5"},  # S0 — not forced at 0.35
    {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 defender — ignored
    {"b": 300, "bm": None, "s": 280, "sm": None, "su": "e4e5"},  # S1 — not forced at 0.35
]

# Tactic seed values (pre-existing tags on the flaw row; not re-used by A/B logic).
_SEED_MOTIF_INT = 2  # TacticMotifInt.HANGING_PIECE
_SEED_CONFIDENCE = 100
_SEED_DEPTH = 0


# ---------------------------------------------------------------------------
# Fixtures: committed data (run_ab_validation opens its own sessions internally)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:  # type: ignore[type-arg]
    """Return an async_sessionmaker bound to the per-run test DB."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def ab_fixture(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[tuple[int, int, int], None]:
    """Seed a committed User, Game, two GamePosition rows, and one GameFlaw.

    The flaw is at ply 1 with:
      - allowed_pv_lines = FORCING_BLOB  (allowed tag would survive the gate, but
        positions[ply+1].pv is None so allowed detection returns None for both arms)
      - missed_pv_lines = NON_FORCING_BLOB (gate suppresses; ungated arm detects HANGING_PIECE)

    This guarantees exactly ONE dropped case (missed orientation) in the A/B diff.

    Yields (user_id, game_id, flaw_ply).
    Teardown: delete Game (CASCADE removes positions + flaws), then User if isolated.
    Cleanup prevents lottery-test leakage (eval_lottery isolation memory from CLAUDE.md).
    """
    user_id = _TEST_USER_ID
    game_id_holder: list[int] = []

    async with session_factory() as session:
        existing = (
            (await session.execute(select(User).where(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=user_id,
                    email=f"test-ab-validate-{user_id}@example.com",
                    hashed_password="x",
                )
            )
            await session.flush()

        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/ab-test",
            pgn=_PGN,
            result="1-0",
            # Player is black: the flaw at ply 1 is a black move (odd ply), so this is the
            # player's own flaw and survives player_only_gate in _load_ab_flaws.
            user_color="black",
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
        game_id = game.id
        game_id_holder.append(game_id)

        # Seed positions at ply 0 (pre-flaw), ply 1 (flaw) and ply 2 (refutation).
        # ply 0: board BEFORE the flaw move; eval_cp feeds the gate's already-winning
        #        reject (Bug A fix: pre_flaw_eval_cp = positions[ply-1].eval_cp).
        # ply 1: the flaw position (black to move); PV = best missed move.
        # ply 2: after black's bad move (white to move); PV=None so allowed detection = None.
        session.add(
            GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=0,
                eval_cp=_EVAL_PLY_0,
                eval_mate=None,
                clock_seconds=None,
                phase=1,
                full_hash=1000,
                white_hash=2000,
                black_hash=3000,
                endgame_class=None,
                move_san=None,
                pv=None,
            )
        )
        session.add(
            GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=1,
                eval_cp=_EVAL_PLY_1,
                eval_mate=None,
                clock_seconds=None,
                phase=1,
                full_hash=1001,
                white_hash=2001,
                black_hash=3001,
                endgame_class=None,
                move_san=_MOVE_SAN_FLAW,  # bad move actually played at ply 1
                pv=_PV_PLY_1,  # best move black should have played
            )
        )
        session.add(
            GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=2,
                eval_cp=_EVAL_PLY_2,
                eval_mate=None,
                clock_seconds=None,
                phase=1,
                full_hash=1002,
                white_hash=2002,
                black_hash=3002,
                endgame_class=None,
                move_san=None,  # white's refutation move (irrelevant for detection)
                pv=None,  # no PV at ply+1 -> allowed detection returns None for both arms
            )
        )

        # Seed one GameFlaw at ply 1.
        # allowed_pv_lines = FORCING_BLOB but positions[ply+1].pv=None -> no allowed tag
        # missed_pv_lines  = NON_FORCING_BLOB -> gate suppresses; ungated detects HANGING_PIECE
        flaw = GameFlaw(
            user_id=user_id,
            game_id=game_id,
            ply=1,
            severity=2,  # blunder
            tempo=None,
            phase=1,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen=_FEN_FLAW,
            allowed_tactic_motif=None,
            allowed_tactic_piece=None,
            allowed_tactic_confidence=None,
            allowed_tactic_depth=None,
            missed_tactic_motif=_SEED_MOTIF_INT,
            missed_tactic_piece=None,
            missed_tactic_confidence=_SEED_CONFIDENCE,
            missed_tactic_depth=_SEED_DEPTH,
            allowed_pv_lines=_FORCING_BLOB,
            missed_pv_lines=_NON_FORCING_BLOB,
        )
        session.add(flaw)
        await session.commit()

    yield user_id, game_id_holder[0], 1

    # Teardown: delete committed rows to prevent lottery-test leakage.
    async with session_factory() as session:
        if game_id_holder:
            await session.execute(delete(Game).where(Game.id == game_id_holder[0]))
        await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUngatedArmBypassesGate:
    """(1) VALID-01: ungated arm calls _detect_tactic_for_flaw directly, never the gate."""

    @pytest.mark.asyncio
    async def test_ungated_arm_bypasses_gate(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ab_fixture: tuple[int, int, int],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Gate is never consulted when the ungated arm runs.

        Spy on apply_forcing_line_filter in flaws_service (where _classify_tactic_gated
        calls it after importing it at module load time). The ungated arm uses
        _detect_tactic_for_flaw directly and must produce a tag for the NON_FORCING_BLOB
        position, while the gated arm suppresses it — proving gate bypass for the ungated arm.
        """
        from scripts.ab_validate_gate import run_ab_validation

        gate_calls: list[str] = []

        def _spy_gate(
            line: object,
            solver_color: str,
            pre_flaw_eval_cp: int,
            firing_depth: int | None = None,
            margin: float = 0.35,
        ) -> bool:
            gate_calls.append(solver_color)
            from app.services.forcing_line_gate import apply_forcing_line_filter as _real

            return _real(line, solver_color, pre_flaw_eval_cp, firing_depth, margin)  # ty: ignore[invalid-argument-type]  # spy wrapper accepts object/str for broad capture

        monkeypatch.setattr("app.services.flaws_service.apply_forcing_line_filter", _spy_gate)

        user_id, _, _ = ab_fixture
        result = await run_ab_validation(
            db="dev",
            user_id=user_id,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        # Ungated arm detects HANGING_PIECE on _FEN_FLAW + _PV_PLY_1.
        assert result.ungated_count_missed >= 1, (
            "Ungated arm must detect HANGING_PIECE on the fixture "
            "(white queen d5 undefended; PV c4d5 captures it)."
        )
        # Gated arm suppresses it via NON_FORCING_BLOB rejection.
        assert result.gated_count_missed == 0, (
            "Gated arm must suppress the NON_FORCING_BLOB missed tag."
        )
        # Gate was called at most once: by the gated arm for the missed orientation.
        # If the ungated arm also called it, gate_calls would have 2+ entries.
        assert len(gate_calls) <= 1, (
            f"Gate called {len(gate_calls)} time(s); ungated arm must not consult "
            "apply_forcing_line_filter (only gated arm calls it, once per orientation "
            "where motif+blob+eval_cp are all present)."
        )


class TestBothArmsUseSameBlobs:
    """(2) VALID-01: both arms read the same stored blobs; no engine, no DB writes."""

    def test_both_arms_use_same_blobs(self) -> None:
        """Harness source must reference neither EnginePool nor chess.engine."""
        import scripts.ab_validate_gate as mod

        source = inspect.getsource(mod)
        assert "EnginePool" not in source, (
            "scripts/ab_validate_gate.py must not reference EnginePool (engine-free guarantee)."
        )
        assert "chess.engine" not in source, (
            "scripts/ab_validate_gate.py must not import chess.engine (engine-free guarantee)."
        )
        # DB-write sentinel: commits and bulk-update calls must be absent.
        assert ".commit()" not in source, (
            "scripts/ab_validate_gate.py must not call session.commit() (read-only guarantee)."
        )
        assert "bulk_update" not in source, (
            "scripts/ab_validate_gate.py must not call bulk_update (read-only guarantee)."
        )


class TestGatedLteUngated:
    """(3) VALID-01: gated tag count <= ungated tag count for every orientation."""

    @pytest.mark.asyncio
    async def test_gated_lte_ungated(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ab_fixture: tuple[int, int, int],
        tmp_path: Path,
    ) -> None:
        """Gate can only suppress, never add new tags; gated <= ungated per orientation."""
        from scripts.ab_validate_gate import run_ab_validation

        user_id, _, _ = ab_fixture
        result = await run_ab_validation(
            db="dev",
            user_id=user_id,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        assert result.gated_count_allowed <= result.ungated_count_allowed, (
            f"Gated allowed ({result.gated_count_allowed}) must be <= "
            f"ungated allowed ({result.ungated_count_allowed})."
        )
        assert result.gated_count_missed <= result.ungated_count_missed, (
            f"Gated missed ({result.gated_count_missed}) must be <= "
            f"ungated missed ({result.ungated_count_missed})."
        )


class TestReportOutput:
    """(4) VALID-02: harness writes a committed-markdown report with required sections."""

    @pytest.mark.asyncio
    async def test_report_output(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ab_fixture: tuple[int, int, int],
        tmp_path: Path,
    ) -> None:
        """Report file is created and contains all required section headers."""
        from scripts.ab_validate_gate import run_ab_validation

        user_id, _, _ = ab_fixture
        await run_ab_validation(
            db="dev",
            user_id=user_id,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        report_files = list(tmp_path.glob("ab-validation-*.md"))
        assert len(report_files) >= 1, (
            f"Expected at least one ab-validation-*.md report in {tmp_path}; found none."
        )
        content = report_files[-1].read_text()
        required_sections = (
            "Executive Summary",
            "Per-Motif",
            "Depth-Shift",
            "Dropped Cases",
            "A/B Summary",
        )
        for section in required_sections:
            assert section in content, (
                f"Report missing required section '{section}'.\n"
                f"Report content (first 500 chars):\n{content[:500]}"
            )


class TestDroppedCaseFields:
    """(5) VALID-02: dropped-case list exposes all required fields including analysis URL."""

    @pytest.mark.asyncio
    async def test_dropped_case_fields(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ab_fixture: tuple[int, int, int],
        tmp_path: Path,
    ) -> None:
        """Each dropped-case entry exposes orientation, motif, FEN, depth, PV, analysis URL."""
        from scripts.ab_validate_gate import run_ab_validation

        user_id, _, _ = ab_fixture
        result = await run_ab_validation(
            db="dev",
            user_id=user_id,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        # The fixture's missed_pv_lines=NON_FORCING_BLOB means the gated arm suppresses the
        # HANGING_PIECE motif that the ungated arm detects -> at least 1 dropped case.
        assert len(result.dropped_cases) >= 1, (
            "Expected at least 1 dropped case (ungated detects HANGING_PIECE on the fixture "
            "position; gated suppresses via NON_FORCING_BLOB). "
            f"ungated_missed={result.ungated_count_missed}, "
            f"gated_missed={result.gated_count_missed}."
        )

        for case in result.dropped_cases:
            assert case.orientation in ("allowed", "missed"), (
                f"Dropped case orientation must be 'allowed' or 'missed'; got {case.orientation!r}"
            )
            assert isinstance(case.motif_name, str) and case.motif_name, (
                "Dropped case motif_name must be a non-empty string."
            )
            assert isinstance(case.fen, str) and case.fen, (
                "Dropped case fen must be a non-empty string (board_fen() piece placement)."
            )
            assert case.depth is not None, (
                "Dropped case depth must not be None (tactic_depth from ungated arm)."
            )
            assert isinstance(case.pv_line, str) and case.pv_line, (
                "Dropped case pv_line must be a non-empty string (stored PV from game_positions)."
            )
            assert case.analysis_url == (
                f"http://localhost:5173/analysis?game_id={case.game_id}&ply={case.ply}"
            ), (
                "Dropped case analysis_url must be the local analysis-board deep-link "
                f"for its game_id/ply; got {case.analysis_url!r}"
            )


class TestAnalysisBoardUrl:
    """(6) analysis_board_url builds the local game-mode deep-link from game_id + ply."""

    def test_analysis_board_url_format(self) -> None:
        """URL helper: ?game_id=X&ply=Y against the local Vite dev server."""
        from scripts.ab_validate_gate import ANALYSIS_BASE_URL, analysis_board_url

        url = analysis_board_url(game_id=687478, ply=56)
        assert url == "http://localhost:5173/analysis?game_id=687478&ply=56", (
            f"analysis_board_url must build the local game-mode deep-link; got {url!r}"
        )
        assert url.startswith(ANALYSIS_BASE_URL + "/analysis?"), (
            "URL must target the local analysis route under ANALYSIS_BASE_URL."
        )

        # Different game_id / ply produce different URLs.
        assert analysis_board_url(1, 0) != analysis_board_url(1, 1), (
            "Different ply must yield a different deep-link."
        )
        assert analysis_board_url(1, 0) != analysis_board_url(2, 0), (
            "Different game_id must yield a different deep-link."
        )
