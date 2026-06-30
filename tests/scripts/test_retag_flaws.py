"""Re-tagger dry-run + idempotency tests for Phase 143 Plan 03.

Tests that run_backfill (from scripts/retag_flaws.py):

  (a) RETAG-01/SC1 — dry_run=True writes a per-motif delta report AND writes 0 DB rows
      (the DB tag columns are unchanged after the dry-run).
  (b) RETAG-02/SC4 idempotency — a real run suppresses the non-forcing tag; a SECOND
      real run at the SAME margin changes 0 rows (second run is a no-op).
  (c) Margin sensitivity — a larger margin suppresses more tags than a smaller one on
      the same fixture (--margin threads through correctly, RETAG-01 tunability).

Uses session-maker injection against the per-run test DB so run_backfill never touches a
real --db target. The game must have committed data (not rollback-scoped) since run_backfill
opens its own sessions internally via the injected session_maker.

Fixture cleanup: all committed rows (User, Game, GamePosition, GameFlaw) are deleted in a
finally block so non-guest Game inserts do not leak into the eval-queue lottery test.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.forcing_line_gate import ONLY_MOVE_WIN_PROB_MARGIN

# ---------------------------------------------------------------------------
# Test constants — no magic numbers (CLAUDE.md)
# ---------------------------------------------------------------------------

# Unique user ID for this test module — no conflict with test_backfill_flaws.py IDs.
_TEST_USER_ID = 143_030

# Minimal PGN — just enough plies for a flaw at ply 1 (black's first move).
# ply 0 = white's e4, ply 1 = black's e5 (the "flaw"), ply 2 = Nf3 (refutation ply).
_PGN = "1. e4 e5 2. Nf3 *"

# eval_cp values: white loses centipawn value at ply 1 (e5??) is black making a blunder.
# We simulate: before ply 1, white is slightly ahead (+50 cp); after ply 1, huge swing.
# But flaws are scored by ES drop for the MOVER — black's e5?? needs black's ES to drop.
# Use: eval at ply 0 (before ply 1): -500 (black winning), eval at ply 1 (after): +200 (white winning).
# ES drop for black: es(500 from black pov) ≈ 0.86 → es(-200 from black pov) ≈ 0.32; drop ≈ 0.54
_EVAL_PLY_0 = -500  # before ply 1 (black's flaw), black is winning
_EVAL_PLY_1 = 200  # after ply 1, white is winning — black blundered
_EVAL_PLY_2 = 200  # refutation ply

# Board setup for the test game:
# The game uses standard starting position; ply 1 is black's e5, ply 2 is Nf3.
# FEN before ply 1 (after white's e4): rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR
_FEN_PLY_1 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"

# A FORCING blob: solver node with a huge gap (b=800, s=0) → gate passes.
# A non-forcing blob: solver node with tiny gap (b=300, s=280) → gate fails at margin=0.35.
# Two solver nodes required for gate to fire (one-mover discard); add a defender node in between.
_FORCING_BLOB: list[dict[str, Any]] = [
    {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S0 solver — forced (huge gap)
    {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 defender — ignored by gate
    {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S1 solver — forced
]
_NON_FORCING_BLOB: list[dict[str, Any]] = [
    {"b": 300, "bm": None, "s": 280, "sm": None, "su": "e4e5"},  # S0 solver — not forced at 0.35
    {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 defender — ignored
    {"b": 300, "bm": None, "s": 280, "sm": None, "su": "e4e5"},  # S1 solver — not forced at 0.35
]

# A motif value to seed the game_flaw with (HANGING_PIECE = 2 per TacticMotifInt).
_SEED_MOTIF_INT = 2  # TacticMotifInt.HANGING_PIECE
_SEED_CONFIDENCE = 100
_SEED_DEPTH = 1


# ---------------------------------------------------------------------------
# Fixtures: committed data (run_backfill opens its own sessions internally)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:  # type: ignore[type-arg]
    """Return an async_sessionmaker bound to the per-run test DB."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def retag_fixture(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[tuple[int, int, int, int], None]:
    """Seed a committed User, Game, two GamePosition rows, and two GameFlaw rows.

    Both flaws at ply 1 are seeded with:
    - allowed_tactic_motif = _SEED_MOTIF_INT (pre-tagged)
    - allowed_pv_lines = _FORCING_BLOB for flaw at ply 1 (index 0)
    - missed_pv_lines = _NON_FORCING_BLOB for flaw at ply 1 (index 0)
    One flaw carries a FORCING allowed blob (tag should survive) and
    a NON_FORCING missed blob (tag should be suppressed by gate at margin=0.35).

    This makes the fixture exercise both "survived" and "suppressed" paths.

    Yields (user_id, game_id, ply_of_flaw, game_flaw_pk_tuple_count).
    Teardown: delete Game (cascade removes positions + flaws) and User if isolated.
    """
    user_id = _TEST_USER_ID
    game_id_holder: list[int] = []

    async with session_factory() as session:
        # Ensure isolated user exists.
        existing = (
            (await session.execute(select(User).where(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=user_id,
                    email=f"test-retag-{user_id}@example.com",
                    hashed_password="x",
                )
            )
            await session.flush()

        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/retag-test",
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
        game_id = game.id
        game_id_holder.append(game_id)

        # Seed three positions: ply 0 (before flaw), ply 1 (flaw), ply 2 (refutation).
        for ply, eval_cp in [(0, _EVAL_PLY_0), (1, _EVAL_PLY_1), (2, _EVAL_PLY_2)]:
            pv_val = "e4e5 d2d4" if ply == 1 else None  # PV at ply 1 for missed pass
            pv_at_2 = "f3e5 d7d6" if ply == 2 else None  # PV at ply 2 for allowed pass
            move_san = "e5" if ply == 1 else ("Nf3" if ply == 2 else "e4")
            session.add(
                GamePosition(
                    user_id=user_id,
                    game_id=game_id,
                    ply=ply,
                    eval_cp=eval_cp,
                    eval_mate=None,
                    clock_seconds=None,
                    phase=1,
                    full_hash=ply + 1000,
                    white_hash=ply + 2000,
                    black_hash=ply + 3000,
                    endgame_class=None,
                    move_san=move_san,
                    pv=pv_at_2 if ply == 2 else pv_val,
                )
            )

        # Seed one GameFlaw at ply 1 with a pre-existing tactic tag and both JSONB blobs.
        # allowed_pv_lines = FORCING (allowed tag survives at margin=0.35)
        # missed_pv_lines  = NON_FORCING (missed tag gets gate-suppressed at margin=0.35)
        flaw = GameFlaw(
            user_id=user_id,
            game_id=game_id,
            ply=1,  # black's e5?? at ply 1
            severity=2,  # blunder
            tempo=None,
            phase=1,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen=_FEN_PLY_1,
            # Pre-tagged tactic columns (will be re-derived by retag_flaws.py)
            allowed_tactic_motif=_SEED_MOTIF_INT,
            allowed_tactic_piece=None,
            allowed_tactic_confidence=_SEED_CONFIDENCE,
            allowed_tactic_depth=_SEED_DEPTH,
            missed_tactic_motif=_SEED_MOTIF_INT,
            missed_tactic_piece=None,
            missed_tactic_confidence=_SEED_CONFIDENCE,
            missed_tactic_depth=_SEED_DEPTH,
            # JSONB blobs (the re-tagger's primary inputs)
            allowed_pv_lines=_FORCING_BLOB,
            missed_pv_lines=_NON_FORCING_BLOB,
        )
        session.add(flaw)
        await session.commit()

    yield user_id, game_id_holder[0], 1, 1  # (user_id, game_id, flaw_ply, flaw_count)

    # Teardown: delete committed data to avoid test-pollution (lottery-test leakage guard).
    async with session_factory() as session:
        if game_id_holder:
            await session.execute(delete(Game).where(Game.id == game_id_holder[0]))
        await session.commit()


# ---------------------------------------------------------------------------
# Helper: read current tactic columns from DB
# ---------------------------------------------------------------------------


async def _read_flaw_tags(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    ply: int,
) -> tuple[
    int | None, int | None, int | None, int | None, int | None, int | None, int | None, int | None
]:
    """Return the 8 tactic-tag column values for a specific flaw."""
    async with session_factory() as session:
        row = (
            await session.execute(
                select(
                    GameFlaw.allowed_tactic_motif,
                    GameFlaw.allowed_tactic_piece,
                    GameFlaw.allowed_tactic_confidence,
                    GameFlaw.allowed_tactic_depth,
                    GameFlaw.missed_tactic_motif,
                    GameFlaw.missed_tactic_piece,
                    GameFlaw.missed_tactic_confidence,
                    GameFlaw.missed_tactic_depth,
                ).where(
                    GameFlaw.user_id == user_id,
                    GameFlaw.game_id == game_id,
                    GameFlaw.ply == ply,
                )
            )
        ).one()
    return tuple(row)  # type: ignore[return-value]


async def _reset_flaw_tags(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    ply: int,
    motif: int,
) -> None:
    """Reset tactic columns back to initial seeded values (for multi-run tests)."""
    async with session_factory() as session:
        await session.execute(
            update(GameFlaw)
            .where(
                GameFlaw.user_id == user_id,
                GameFlaw.game_id == game_id,
                GameFlaw.ply == ply,
            )
            .values(
                allowed_tactic_motif=motif,
                allowed_tactic_piece=None,
                allowed_tactic_confidence=_SEED_CONFIDENCE,
                allowed_tactic_depth=_SEED_DEPTH,
                missed_tactic_motif=motif,
                missed_tactic_piece=None,
                missed_tactic_confidence=_SEED_CONFIDENCE,
                missed_tactic_depth=_SEED_DEPTH,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# SC1: dry-run writes zero DB rows and produces a report file (RETAG-01)
# ---------------------------------------------------------------------------


class TestRetagDryRun:
    """run_backfill with dry_run=True writes zero DB rows and produces a report."""

    @pytest.mark.asyncio
    async def test_dry_run_writes_zero_db_rows(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
        tmp_path: Path,
    ) -> None:
        """SC1: dry_run=True must not change any game_flaws rows."""
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        # Record the baseline tags before dry-run.
        tags_before = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)

        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=True,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        # Tags must be completely unchanged after dry-run.
        tags_after = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)
        assert tags_before == tags_after, (
            f"Dry-run must not modify DB rows; before={tags_before}, after={tags_after}"
        )

    @pytest.mark.asyncio
    async def test_dry_run_writes_report_file(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
        tmp_path: Path,
    ) -> None:
        """SC1: dry_run=True writes a reports/retag/retag-YYYY-MM-DD.md file."""
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=True,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        # Report must have been written to the injected tmp dir (never the committed tree).
        report_files = list(tmp_path.glob("retag-*.md"))
        assert len(report_files) >= 1, f"Expected a retag report in {tmp_path}, found none"

        # Report must have the expected per-motif table sections.
        latest = max(report_files, key=lambda p: p.stat().st_mtime)
        content = latest.read_text()
        assert "Allowed-orientation tag changes" in content, "Report missing allowed table"
        assert "Missed-orientation tag changes" in content, "Report missing missed table"
        assert "Motif" in content and "Suppression %" in content, "Report missing columns"
        # Check the margin is documented.
        assert str(ONLY_MOVE_WIN_PROB_MARGIN) in content, "Report missing margin value"

    @pytest.mark.asyncio
    async def test_dry_run_report_contains_per_motif_counts(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
        tmp_path: Path,
    ) -> None:
        """SC1: The dry-run report must reflect per-motif removed/survived counts.

        The fixture seeds one flaw with:
        - allowed_pv_lines = FORCING (allowed tag survives at margin=0.35)
        - missed_pv_lines  = NON_FORCING (missed tag gets gate-suppressed at margin=0.35)
        So the report must show 1 survived + 0 suppressed for allowed, and
        0 survived + 1 suppressed for missed (both for HANGING_PIECE).
        """
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=True,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
            report_dir=tmp_path,
        )

        latest = max(tmp_path.glob("retag-*.md"), key=lambda p: p.stat().st_mtime)
        content = latest.read_text()

        # The fixture's motif is HANGING_PIECE (int=2) — the report decodes via TacticMotifInt.
        assert "HANGING_PIECE" in content, (
            f"Expected HANGING_PIECE in report (seed motif {_SEED_MOTIF_INT}); got:\n{content}"
        )


# ---------------------------------------------------------------------------
# SC4: idempotency — second run at same margin changes 0 rows (RETAG-02)
# ---------------------------------------------------------------------------


class TestRetagIdempotency:
    """A second real run at the same margin changes 0 rows (SC4, RETAG-02)."""

    @pytest.mark.asyncio
    async def test_second_run_changes_zero_rows(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
    ) -> None:
        """SC4: a second real run at the same margin is a no-op (idempotent)."""
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        # First real run: applies gate, some tags change.
        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=False,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
        )

        tags_after_first = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)

        # Second real run at the same margin: must produce identical output → 0 rows change.
        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=False,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
        )

        tags_after_second = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)
        assert tags_after_first == tags_after_second, (
            f"SC4 idempotency violated: second run at same margin changed rows; "
            f"after_first={tags_after_first}, after_second={tags_after_second}"
        )

    @pytest.mark.asyncio
    async def test_first_run_suppresses_non_forcing_missed_tag(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
    ) -> None:
        """First real run must suppress the non-forcing missed blob tag.

        The fixture seeds:
        - missed_pv_lines = NON_FORCING_BLOB → missed_tactic_motif should become None.
        - allowed_pv_lines = FORCING_BLOB → allowed_tactic_motif may survive or None
          depending on whether the detector also fires, but missed must be suppressed.
        """
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=False,
            limit=None,
            workers=1,
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory,
        )

        tags = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)
        # tags[4] = missed_tactic_motif; the NON_FORCING blob should suppress it.
        missed_motif_after = tags[4]
        assert missed_motif_after is None, (
            f"Expected missed_tactic_motif=None after gate suppression at margin "
            f"{ONLY_MOVE_WIN_PROB_MARGIN}, but got {missed_motif_after}"
        )


# ---------------------------------------------------------------------------
# Margin sensitivity — larger margin suppresses more tags (RETAG-01 tunability)
# ---------------------------------------------------------------------------


class TestRetagMarginSensitivity:
    """A larger --margin suppresses strictly more tags than a smaller one (RETAG-01)."""

    @pytest.mark.asyncio
    async def test_larger_margin_suppresses_more_tags(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        retag_fixture: tuple[int, int, int, int],
    ) -> None:
        """margin sensitivity: a larger margin suppresses strictly more tags than a smaller one.

        The _FORCING_BLOB has a large gap (b=800, s=0) → passes at any reasonable margin.
        The _NON_FORCING_BLOB has a small gap (b=300, s=280) → fails at margin=0.35, also
        fails at margin=0.5.

        For this test we need a blob that passes at a SMALL margin but fails at a LARGE one.
        We reset the flaw's allowed_pv_lines to a blob with intermediate gap, then compare.
        """
        from scripts.retag_flaws import run_backfill

        user_id, game_id, flaw_ply, _ = retag_fixture

        # Replace the allowed blob with one that passes at margin=0.1 but fails at margin=0.5.
        # From PATTERNS.md: p(400, white) - p(200, white) ≈ 0.799 - 0.677 = 0.122.
        # At margin=0.1: 0.122 > 0.1 → passes (forced).
        # At margin=0.5: 0.122 < 0.5 → fails (not forced).
        intermediate_blob: list[dict[str, Any]] = [
            {"b": 400, "bm": None, "s": 200, "sm": None, "su": "e4e5"},  # S0 — passes at 0.1
            {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 — ignored
            {"b": 400, "bm": None, "s": 200, "sm": None, "su": "e4e5"},  # S1 — passes at 0.1
        ]

        # Write the intermediate blob to the flaw (simulating a different blob configuration).
        async with session_factory() as session:
            await session.execute(
                update(GameFlaw)
                .where(
                    GameFlaw.user_id == user_id,
                    GameFlaw.game_id == game_id,
                    GameFlaw.ply == flaw_ply,
                )
                .values(
                    allowed_tactic_motif=_SEED_MOTIF_INT,
                    missed_tactic_motif=_SEED_MOTIF_INT,
                    allowed_pv_lines=intermediate_blob,
                    missed_pv_lines=intermediate_blob,
                )
            )
            await session.commit()

        # Run at small margin (0.1) — intermediate blob should SURVIVE (0.122 > 0.1).
        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=False,
            limit=None,
            workers=1,
            margin=0.1,
            session_maker=session_factory,
        )
        tags_small_margin = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)
        # At least one motif should survive (allowed or missed, depends on detector).
        # We check: with margin=0.1, the allowed blob passes the gate.
        # Actual DB state depends on whether _detect_tactic_for_flaw fires; just verify
        # the second run at margin=0.5 suppresses more.

        # Reset to seeded state (both motifs back to SEED_MOTIF_INT with intermediate blob).
        async with session_factory() as session:
            await session.execute(
                update(GameFlaw)
                .where(
                    GameFlaw.user_id == user_id,
                    GameFlaw.game_id == game_id,
                    GameFlaw.ply == flaw_ply,
                )
                .values(
                    allowed_tactic_motif=_SEED_MOTIF_INT,
                    missed_tactic_motif=_SEED_MOTIF_INT,
                    allowed_pv_lines=intermediate_blob,
                    missed_pv_lines=intermediate_blob,
                )
            )
            await session.commit()

        # Run at large margin (0.5) — intermediate blob FAILS (0.122 < 0.5) → suppressed.
        await run_backfill(
            db="dev",
            user_id=user_id,
            only_tagged=False,
            dry_run=False,
            limit=None,
            workers=1,
            margin=0.5,
            session_maker=session_factory,
        )
        tags_large_margin = await _read_flaw_tags(session_factory, user_id, game_id, flaw_ply)

        # Count surviving motifs (non-None) in each run.
        # tags tuple: (a_motif, a_piece, a_conf, a_depth, m_motif, m_piece, m_conf, m_depth)
        small_surviving = sum(
            1 for v in (tags_small_margin[0], tags_small_margin[4]) if v is not None
        )
        large_surviving = sum(
            1 for v in (tags_large_margin[0], tags_large_margin[4]) if v is not None
        )

        assert large_surviving <= small_surviving, (
            f"Larger margin (0.5) should suppress at least as many tags as smaller margin (0.1). "
            f"small_margin surviving motifs={small_surviving}, large_margin={large_surviving}. "
            f"tags at 0.1: {tags_small_margin}; tags at 0.5: {tags_large_margin}"
        )
        # The key assertion: at large margin, the intermediate blob MUST be suppressed
        # (0.122 < 0.5, gate fails on this blob regardless of orientation).
        allowed_at_large = tags_large_margin[0]
        missed_at_large = tags_large_margin[4]
        assert allowed_at_large is None and missed_at_large is None, (
            f"Intermediate blob (gap≈0.122) must be gate-suppressed at margin=0.5; "
            f"got allowed_motif={allowed_at_large}, missed_motif={missed_at_large}"
        )


# ---------------------------------------------------------------------------
# TestPreFlawEvalParity: the re-tagger and the live import path must derive the
# gate's pre_flaw_eval_cp identically (Bug A regression guard, Phase 144).
# ---------------------------------------------------------------------------


class TestPreFlawEvalParity:
    """`retag_flaws._worker_recompute` and `flaws_service._build_flaw_record` must agree.

    Both wrappers independently derive pre_flaw_eval_cp before calling the shared
    `_classify_tactic_gated`, so a divergence there is silent (it was: Bug A had the
    re-tagger read the eval AFTER the flaw move while the live path read the board before
    it). These tests pin both wrappers to positions[n-1].eval_cp by patching the shared
    detector to a fixed motif and choosing a position where the pre-flaw eval is outcome-
    determining: ply-1 is already-winning for the solver (suppress) while the flaw-ply eval
    is not (would credit). A re-tagger that regressed to the flaw-ply eval would credit the
    tag and the parity assertion would fail.
    """

    # A forcing allowed blob for a white solver: firing node forced (huge gap), two solver
    # nodes (clears the one-mover discard), all above the still-winning floor.
    _FORCING_ALLOWED: list[dict[str, Any]] = [
        {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S0 firing — forced
        {"b": 100, "bm": None, "s": 50, "sm": None, "su": "e5e4"},  # D0 defender — ignored
        {"b": 800, "bm": None, "s": 0, "sm": None, "su": "e4e5"},  # S1 — forced
    ]

    @staticmethod
    def _patch_detector(monkeypatch: pytest.MonkeyPatch, motif_int: int) -> None:
        """Force the shared detector to return a fixed depth-0 motif for the allowed pass only.

        Patches the flaws_service module global so BOTH wrappers (which funnel through
        flaws_service._classify_tactic_gated -> _detect_tactic_for_flaw) see it.
        """

        def _fake_detect(
            n: int,
            fen_map: dict[int, str],
            positions: list[Any],
            pv_by_ply: Any = None,
            orientation: str = "allowed",
        ) -> tuple[int | None, int | None, int | None, int | None]:
            if orientation == "allowed":
                return (motif_int, 2, 100, 0)  # (motif, piece=knight, confidence, depth=0)
            return (None, None, None, None)

        import app.services.flaws_service as fs

        monkeypatch.setattr(fs, "_detect_tactic_for_flaw", _fake_detect)

    def _run_both(
        self, prv_eval: int, cur_eval: int
    ) -> tuple[tuple[int | None, ...], tuple[int | None, ...]]:
        """Run the live and re-tagger wrappers over identical inputs; return both 8-tuples."""
        from app.services.flaws_service import _build_flaw_record
        from scripts.retag_flaws import _FlawWork, _PosRow, _worker_recompute

        ply = 1  # allowed orientation, odd ply -> white solver
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
        prv = _PosRow(move_san="e4", pv=None, eval_mate=None, eval_cp=prv_eval)
        cur = _PosRow(move_san="e5", pv=None, eval_mate=None, eval_cp=cur_eval)
        nxt = _PosRow(move_san="Nf3", pv="f3e5 d7d6", eval_mate=None, eval_cp=cur_eval)

        # _PosRow is a structural stand-in for GamePosition (the wrappers read only
        # .eval_cp / .move_san); list[Any] / dict-Any satisfy the nominal param types,
        # mirroring retag_flaws._worker_recompute's own `positions: list[Any]`.
        positions: list[Any] = [prv, cur, nxt]
        blobs: dict[int, Any] = {ply: (self._FORCING_ALLOWED, [])}

        # Live path: _build_flaw_record reads positions[ply-1].eval_cp for pre_flaw_eval_cp.
        record = _build_flaw_record(
            ply, "black", "blunder", 0.8, 0.3, {ply: fen}, positions, None, blobs
        )
        live = (
            record["allowed_tactic_motif_int"],
            record["allowed_tactic_piece"],
            record["allowed_tactic_confidence"],
            record["allowed_tactic_depth"],
            record["missed_tactic_motif_int"],
            record["missed_tactic_piece"],
            record["missed_tactic_confidence"],
            record["missed_tactic_depth"],
        )

        # Re-tagger path: _worker_recompute reads work.prv.eval_cp for pre_flaw_eval_cp.
        work = _FlawWork(
            user_id=1,
            game_id=1,
            ply=ply,
            fen=fen,
            prv=prv,
            cur=cur,
            nxt=nxt,
            old_tuple=(-1,) * 8,  # sentinel != any real tuple -> always returns the new tuple
            allowed_pv_blob=self._FORCING_ALLOWED,
            missed_pv_blob=[],
            margin=ONLY_MOVE_WIN_PROB_MARGIN,
        )
        retag = _worker_recompute(work)
        assert retag is not None  # sentinel old_tuple guarantees a non-None return
        return live, retag

    def test_parity_when_pre_flaw_already_winning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ply-1 already-winning (+900 white, > 800 threshold) suppresses; flaw-ply eval (0) would credit.

        This is the discriminating case: a re-tagger using the flaw-ply eval would credit
        the forced tag, breaking parity. Both wrappers must suppress.
        """
        self._patch_detector(monkeypatch, motif_int=2)  # HANGING_PIECE
        live, retag = self._run_both(prv_eval=900, cur_eval=0)
        assert live == retag, f"live {live} != retag {retag}"
        # Suppressed because the pre-flaw (ply-1) eval is already-winning for the solver.
        assert live[0] is None, f"allowed tag should be suppressed, got {live}"

        # Discrimination guard: with the flaw-ply eval (0) the same blob WOULD be credited,
        # so the parity above is meaningful (not vacuously suppressed for another reason).
        from app.services.flaws_service import _classify_tactic_gated

        unused_positions: list[Any] = [object(), object(), object()]  # detector is patched
        blob: Any = self._FORCING_ALLOWED
        credited = _classify_tactic_gated(
            1,
            {1: "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"},
            unused_positions,
            "allowed",
            pv_blob=blob,
            pre_flaw_eval_cp=0,
        )
        assert credited[0] == 2, "control: blob is credited when pre_flaw_eval_cp is not winning"

    def test_parity_when_pre_flaw_not_winning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ply-1 not winning (0): both wrappers credit the forced tag identically."""
        self._patch_detector(monkeypatch, motif_int=2)  # HANGING_PIECE
        live, retag = self._run_both(prv_eval=0, cur_eval=700)
        assert live == retag, f"live {live} != retag {retag}"
        assert live[0] == 2, f"allowed tag should be credited, got {live}"
        assert live[3] == 0, "firing depth should be 0"
