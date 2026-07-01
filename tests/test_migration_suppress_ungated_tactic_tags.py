"""Data-correctness test for the Phase 147-02 old-corpus ungated-tactic-tag suppression
migration (SEED-074, D-03, D-04).

Seeds four `game_flaws` rows covering every carve-out plus a per-orientation
independence case, runs the migration's gated UPDATE, and asserts only the
cp-based candidate columns (per orientation) were suppressed:

  - Row 1 (both orientations candidate): NULL blobs on both orientations, joined
    `game_positions.eval_cp` non-NULL, motif set on both -> BOTH suppressed.
  - Row 2 (mate-adjacent): NULL blobs, joined `eval_cp IS NULL` (mate position),
    motif set on both -> KEPT (both orientations, D-06/Pitfall-2 carve-out).
  - Row 3 (D-06 sentinel): `pv_lines = '[]'::jsonb` on both orientations (NOT NULL),
    `eval_cp` non-NULL, motif set on both -> KEPT (both orientations).
  - Row 4 (per-orientation independence): `allowed_pv_lines` already populated
    (non-NULL real blob) -> allowed KEPT; `missed_pv_lines` NULL (candidate) ->
    missed SUPPRESSED. Proves suppression gates on each orientation's OWN blob
    column, not a combined check.

Re-runs the migration SQL a second time and asserts zero rows change (idempotency).

Mirrors the gated SQL in
`alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py::upgrade`;
keep in sync.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from tests.conftest import ensure_test_user

_TEST_USER_ID = 99479

# Mirror of the migration's gated UPDATE (per-orientation blob column + joined
# game_positions.eval_cp cp-based candidate check). Keep in sync with the
# migration file's upgrade() SQL.
_SUPPRESS_SQL = """
WITH batch AS (
    SELECT gf.user_id, gf.game_id, gf.ply,
           (gf.allowed_pv_lines IS NULL AND gp.eval_cp IS NOT NULL
                AND gf.allowed_tactic_motif IS NOT NULL) AS suppress_allowed,
           (gf.missed_pv_lines  IS NULL AND gp.eval_cp IS NOT NULL
                AND gf.missed_tactic_motif  IS NOT NULL) AS suppress_missed
    FROM game_flaws gf
    JOIN game_positions gp
      ON gp.user_id = gf.user_id AND gp.game_id = gf.game_id
         AND gp.ply = gf.ply - 1
    WHERE (gf.allowed_pv_lines IS NULL OR gf.missed_pv_lines IS NULL)
      AND gp.eval_cp IS NOT NULL
      AND (gf.allowed_tactic_motif IS NOT NULL OR gf.missed_tactic_motif IS NOT NULL)
)
UPDATE game_flaws gf
SET allowed_tactic_motif      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_motif END,
    allowed_tactic_piece      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_piece END,
    allowed_tactic_confidence = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_confidence END,
    allowed_tactic_depth      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_depth END,
    missed_tactic_motif       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_motif END,
    missed_tactic_piece       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_piece END,
    missed_tactic_confidence  = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_confidence END,
    missed_tactic_depth       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_depth END
FROM batch b
WHERE gf.user_id = b.user_id AND gf.game_id = b.game_id AND gf.ply = b.ply
  AND (b.suppress_allowed OR b.suppress_missed)
"""

_PGN = "1. e4 e5 2. Nf3 Nc6 *"


async def _seed_game(session: AsyncSession) -> int:
    game = Game(
        user_id=_TEST_USER_ID,
        platform="lichess",
        platform_game_id=f"suppress-ungated-{_TEST_USER_ID}",
        pgn=_PGN,
        result="1-0",
        user_color="white",
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game.id


def _add_position(
    session: AsyncSession,
    *,
    game_id: int,
    ply: int,
    eval_cp: int | None,
    eval_mate: int | None,
) -> None:
    session.add(
        GamePosition(
            user_id=_TEST_USER_ID,
            game_id=game_id,
            ply=ply,
            full_hash=0x9000 + ply,
            white_hash=0,
            black_hash=0,
            phase=1,
            endgame_class=None,
            eval_cp=eval_cp,
            eval_mate=eval_mate,
        )
    )


def _add_flaw(
    session: AsyncSession,
    *,
    game_id: int,
    ply: int,
    allowed_pv_lines: list | None = None,
    missed_pv_lines: list | None = None,
) -> None:
    # DO NOT pass allowed_pv_lines=None / missed_pv_lines=None explicitly — SQLAlchemy
    # serializes Python None to JSONB null (a JSON value), not SQL NULL, so the WHERE
    # allowed_pv_lines IS NULL predicate would never match. Only pass the kwarg when
    # a non-NULL value (populated blob or the D-06 [] sentinel) is needed; otherwise
    # omit it so the column defaults to true SQL NULL.
    kwargs = {}
    if allowed_pv_lines is not None:
        kwargs["allowed_pv_lines"] = allowed_pv_lines
    if missed_pv_lines is not None:
        kwargs["missed_pv_lines"] = missed_pv_lines
    session.add(
        GameFlaw(
            user_id=_TEST_USER_ID,
            game_id=game_id,
            ply=ply,
            severity=2,
            phase=1,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            allowed_tactic_motif=1,
            allowed_tactic_piece=2,
            allowed_tactic_confidence=80,
            allowed_tactic_depth=3,
            missed_tactic_motif=4,
            missed_tactic_piece=5,
            missed_tactic_confidence=70,
            missed_tactic_depth=2,
            **kwargs,
        )
    )


async def _fetch_flaw(session: AsyncSession, *, game_id: int, ply: int) -> GameFlaw:
    result = await session.execute(
        select(GameFlaw).where(
            GameFlaw.user_id == _TEST_USER_ID,
            GameFlaw.game_id == game_id,
            GameFlaw.ply == ply,
        )
    )
    flaw = result.unique().scalar_one()
    return flaw


async def test_suppress_carve_outs_and_idempotency(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _TEST_USER_ID)
    game_id = await _seed_game(db_session)

    # Row 1: cp-based candidate on BOTH orientations -> both suppressed.
    _add_position(db_session, game_id=game_id, ply=4, eval_cp=50, eval_mate=None)
    _add_flaw(db_session, game_id=game_id, ply=5)

    # Row 2: mate-adjacent (eval_cp IS NULL) -> KEPT on both orientations.
    _add_position(db_session, game_id=game_id, ply=6, eval_cp=None, eval_mate=5)
    _add_flaw(db_session, game_id=game_id, ply=7)

    # Row 3: D-06 [] sentinel on both orientations (NOT NULL, never matches IS NULL) -> KEPT.
    _add_position(db_session, game_id=game_id, ply=8, eval_cp=50, eval_mate=None)
    _add_flaw(db_session, game_id=game_id, ply=9, allowed_pv_lines=[], missed_pv_lines=[])

    # Row 4: per-orientation independence. allowed already populated (real blob) -> KEPT;
    # missed still NULL (candidate) -> SUPPRESSED. Proves the gate is per-orientation.
    _add_position(db_session, game_id=game_id, ply=10, eval_cp=50, eval_mate=None)
    _add_flaw(
        db_session,
        game_id=game_id,
        ply=11,
        allowed_pv_lines=[{"b": 10, "bm": None, "s": 5, "sm": None, "su": "e2e4"}],
    )

    await db_session.flush()

    result = await db_session.execute(text(_SUPPRESS_SQL))
    row_count = result.rowcount  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
    assert row_count == 2, "only row 1 (both orientations) and row 4 (missed only) touched"

    row1 = await _fetch_flaw(db_session, game_id=game_id, ply=5)
    assert row1.allowed_tactic_motif is None
    assert row1.allowed_tactic_piece is None
    assert row1.allowed_tactic_confidence is None
    assert row1.allowed_tactic_depth is None
    assert row1.missed_tactic_motif is None
    assert row1.missed_tactic_piece is None
    assert row1.missed_tactic_confidence is None
    assert row1.missed_tactic_depth is None

    row2 = await _fetch_flaw(db_session, game_id=game_id, ply=7)
    assert row2.allowed_tactic_motif == 1, "mate-adjacent allowed tag must be preserved"
    assert row2.missed_tactic_motif == 4, "mate-adjacent missed tag must be preserved"

    row3 = await _fetch_flaw(db_session, game_id=game_id, ply=9)
    assert row3.allowed_tactic_motif == 1, "D-06 sentinel allowed tag must be preserved"
    assert row3.missed_tactic_motif == 4, "D-06 sentinel missed tag must be preserved"

    row4 = await _fetch_flaw(db_session, game_id=game_id, ply=11)
    assert row4.allowed_tactic_motif == 1, "already-blobbed allowed tag must be preserved"
    assert row4.missed_tactic_motif is None, "candidate missed tag must be suppressed"

    # Idempotency: re-running the SQL a second time must update zero rows.
    rerun = await db_session.execute(text(_SUPPRESS_SQL))
    rerun_row_count = rerun.rowcount  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
    assert rerun_row_count == 0, "re-running the suppression SQL must be a no-op"
