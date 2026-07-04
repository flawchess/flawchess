"""Shared scenario builders for the write-path golden-snapshot harness (Phase 150 WRITE-03).

Reused by BOTH ``scripts/gen_write_path_golden.py`` (the committed golden generator) and
``tests/services/test_flaw_upsert_equivalence.py`` (the drift-check equivalence test), so
the generator and the test literally run the same setup code and can never diverge on
scenario construction (150-01-PLAN.md D-01).

Every scenario drives the PRODUCTION submit entry point,
``app.routers.eval_remote._apply_atomic_submit`` — never a copy of the classify/write
logic — so this harness is the exact proof Plan 04's diff/upsert swap must stay green
against (WRITE-03). All 7 named scenarios (mirroring CONTEXT.md D-02's numbered list —
scenario 4, the flip-IN case, is the inverse ordering of scenario 3, not an 8th scenario;
see 150-01-SUMMARY.md deviations) end by dumping the game's ``game_flaws`` rows (every
content column, keyed by ``ply`` as a string) to a JSON-serializable dict. ``user_id`` /
``game_id`` are deliberately excluded from the dump — they vary run-to-run (autoincrement
PKs) and would break byte-identical regeneration.

Reuses DB/fixture helpers from ``tests/test_eval_worker_endpoints.py`` (session setup,
the blunder/flat eval fixtures, opening-cache helpers) rather than duplicating them —
mirrors the established cross-file reuse pattern in ``tests/test_worker_heartbeats.py``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable, Generator
from typing import Any, Final

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.test_eval_worker_endpoints import (
    _BLUNDER_SUBMIT_EVALS_142,
    _FLAT_SUBMIT_EVALS_142,
    _SIX_PLY_PGN_142,
    _WALKABLE_PV_PLY2,
    _WALKABLE_PV_PLY3,
    _atomic_request,
    _delete_games,
    _delete_opening_cache,
    _insert_game,
    _insert_game_positions,
    _insert_opening_cache_with_pv,
)

# ─── Named scenarios (order mirrors CONTEXT.md D-02) ──────────────────────────

SCENARIO_NAMES: Final[tuple[str, ...]] = (
    "scenario_1_fresh_full_submit",
    "scenario_2_residual_hole_retry",
    "scenario_3_flip_out",
    "scenario_4_flip_in",
    "scenario_5_entry_pass_replaced",
    "scenario_6_dedup_transplant_no_sentinel",
    "scenario_7_blobs_pending_suppression",
)

# game_flaws content columns dumped per row — excludes the (user_id, game_id, ply) PK.
# ply is the dump dict's key; user_id/game_id are run-specific autoincrement values.
DUMP_COLUMNS: Final[tuple[str, ...]] = (
    "severity",
    "tempo",
    "phase",
    "is_miss",
    "is_lucky",
    "is_reversed",
    "is_squandered",
    "fen",
    "allowed_tactic_motif",
    "allowed_tactic_piece",
    "allowed_tactic_confidence",
    "allowed_tactic_depth",
    "missed_tactic_motif",
    "missed_tactic_piece",
    "missed_tactic_confidence",
    "missed_tactic_depth",
    "allowed_pv_lines",
    "missed_pv_lines",
)

# A real, walkable forcing blob for ply 2 of _SIX_PLY_PGN_142 (mirrors
# test_atomic_submit_gates_tactic_tag_and_stamps_both_markers) — the REAL forcing-line
# gate genuinely runs and passes on this data, it is not a stubbed gate result.
_FORCING_ALLOWED_BLOB: list[dict[str, Any]] = [
    {"b": -800, "bm": None, "s": 0, "sm": None, "su": "b8c6"},
    {"b": 300, "bm": None, "s": 250, "sm": None, "su": "f1c4"},
    {"b": -800, "bm": None, "s": 0, "sm": None, "su": "f8c5"},
]


def _fake_detect_hanging_piece(
    n: int,
    fen_map: dict[int, str],
    positions: list[Any],
    pv_by_ply: Any = None,
    orientation: str = "allowed",
) -> tuple[int | None, int | None, int | None, int | None]:
    """Deterministic HANGING_PIECE/allowed tactic detection (independent of real PV
    pattern matching) — mirrors the fixed-motif monkeypatch used throughout
    tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint."""
    from app.services.tactic_detector import TACTIC_CONFIDENCE_HIGH, TacticMotifInt

    if orientation == "allowed":
        return (int(TacticMotifInt.HANGING_PIECE), 2, TACTIC_CONFIDENCE_HIGH, 0)
    return (None, None, None, None)


@contextlib.contextmanager
def _patch_tactic_detection(*, fake_assemble: bool) -> Generator[None, None, None]:
    """Monkeypatch tactic detection to a deterministic motif; optionally also fake
    blob assembly so a real forcing blob reaches the (real, unstubbed) gate.

    ``fake_assemble=True`` — used when a scenario needs a real, gated, non-NULL
    tactic tag + blob (scenario 1). ``fake_assemble=False`` — used when a scenario
    wants to prove the NULL-suppression path fires despite the server finding a
    real flaw (scenario 7: blob_nodes=[] means _assemble_flaw_blobs_from_submit
    returns {} for real, no stubbing needed there).
    """
    import app.routers.eval_remote as eval_remote_module
    import app.services.flaws_service as flaws_service_module

    mp = pytest.MonkeyPatch()
    mp.setattr(flaws_service_module, "_detect_tactic_for_flaw", _fake_detect_hanging_piece)
    if fake_assemble:
        mp.setattr(
            eval_remote_module,
            "_assemble_flaw_blobs_from_submit",
            lambda game_id_arg, submit_evals, sentinel_lines: {2: (_FORCING_ALLOWED_BLOB, [])},
        )
    try:
        yield
    finally:
        mp.undo()


async def _run_atomic_submit(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    evals: list[dict[str, object]],
) -> None:
    """Drive the production submit entry point directly (bypasses the HTTP/auth
    layer, mirroring every TestAtomicSubmitEndpoint test)."""
    from app.routers.eval_remote import _apply_atomic_submit

    await _apply_atomic_submit(
        game_id,
        _atomic_request(game_id, evals),
        worker_id="gen-write-path-golden",
        last_ip=None,
    )


# ─── Per-scenario setup (one fixed full_hash base per scenario avoids collision
# when scenarios run back-to-back against the same DB) ────────────────────────

_BASE_HASH: Final[dict[str, int]] = {
    "scenario_1_fresh_full_submit": 150_101_000,
    "scenario_2_residual_hole_retry": 150_102_000,
    "scenario_3_flip_out": 150_103_000,
    "scenario_4_flip_in": 150_104_000,
    "scenario_5_entry_pass_replaced": 150_105_000,
    "scenario_6_dedup_transplant_no_sentinel": 150_106_000,
    "scenario_7_blobs_pending_suppression": 150_107_000,
}

# Preserved blob/tag values simulating a prior atomic worker's real blob write
# (scenarios 2 and 3 manually UPDATE these onto the ply-2 flaw between submits).
_PRESERVED_ALLOWED: list[dict[str, Any]] = [{"b": 10, "bm": None, "s": 5, "sm": None, "su": "e2e4"}]
_PRESERVED_MISSED: list[dict[str, Any]] = [{"b": 20, "bm": None, "s": 8, "sm": None, "su": "d2d4"}]


async def _insert_six_ply_positions(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    base_hash: int,
) -> None:
    await _insert_game_positions(
        session_maker,
        user_id,
        game_id,
        [
            {"ply": p, "full_hash": base_hash + p, "eval_cp": None, "eval_mate": None}
            for p in range(6)
        ],
    )


async def _scenario_1(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Fresh full submit — all flaws new, all blobbed (real, gated, non-NULL tag)."""
    base = _BASE_HASH["scenario_1_fresh_full_submit"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)
    with _patch_tactic_detection(fake_assemble=True):
        await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    return game_id, []


async def _scenario_2(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Residual-hole retry — a sparse second submit (no fresh blob) must preserve
    the already-blobbed midgame flaw's blob + tactic tags (SEED-076)."""
    from app.models.game_flaw import GameFlaw

    base = _BASE_HASH["scenario_2_residual_hole_retry"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    # Attempt 1: full evals, no blobs -> flaw row created at ply 2 (blobs NULL).
    await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    # Simulate attempt 1 having blobbed + tagged the flaw (as a real atomic worker would).
    async with session_maker() as s:
        await s.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            .values(
                allowed_pv_lines=_PRESERVED_ALLOWED,
                missed_pv_lines=_PRESERVED_MISSED,
                allowed_tactic_motif=7,
                allowed_tactic_confidence=80,
            )
        )
        await s.commit()
    # Attempt 2: full evals again, NO blobs -> must preserve, not wipe.
    await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    return game_id, []


async def _scenario_3(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Borderline ply flips OUT of flaw status between submits (FLAWCHESS-8D) —
    the row must cleanly disappear, never a StaleDataError."""
    from app.models.game_flaw import GameFlaw

    base = _BASE_HASH["scenario_3_flip_out"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    # Attempt 1: blunder evals -> flaw row created + blobbed at ply 2 (snapshot source).
    await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    async with session_maker() as s:
        await s.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            .values(allowed_pv_lines=_PRESERVED_ALLOWED)
        )
        await s.commit()
    # Attempt 2: FLAT evals -> reclassify drops the ply-2 flaw entirely.
    await _run_atomic_submit(session_maker, game_id, list(_FLAT_SUBMIT_EVALS_142))
    return game_id, []


async def _scenario_4(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Borderline ply flips IN to flaw status — the INVERSE ordering of scenario 3
    (flat first, then blunder): a fresh flaw appears where none existed before."""
    base = _BASE_HASH["scenario_4_flip_in"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    # Attempt 1: FLAT evals -> no flaw exists.
    await _run_atomic_submit(session_maker, game_id, list(_FLAT_SUBMIT_EVALS_142))
    # Attempt 2: BLUNDER evals -> a fresh flaw row is inserted at ply 2 (no prior
    # blob to preserve — this is the "insert new" branch, not "update existing").
    await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    return game_id, []


async def _scenario_5(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Entry-pass rows (NULL tactic columns, wrong severity) must be REPLACED by
    the full/oracle pass, not left stale (ON CONFLICT DO NOTHING regression guard)."""
    from app.models.game_flaw import GameFlaw

    base = _BASE_HASH["scenario_5_entry_pass_replaced"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    # Pre-seed stale entry-pass rows BEFORE the atomic submit.
    async with session_maker() as seed:
        seed.add_all(
            [
                # Real flaw ply, but the WRONG severity + NULL tactics (mimics the
                # no-PV entry pass).
                GameFlaw(
                    user_id=user_id,
                    game_id=game_id,
                    ply=2,
                    severity=1,
                    phase=0,
                    is_miss=False,
                    is_lucky=False,
                    is_reversed=False,
                    is_squandered=False,
                    fen="stale",
                ),
                # Not a flaw per the full classify -- must be deleted, not survive.
                GameFlaw(
                    user_id=user_id,
                    game_id=game_id,
                    ply=0,
                    severity=2,
                    phase=0,
                    is_miss=False,
                    is_lucky=False,
                    is_reversed=False,
                    is_squandered=False,
                    fen="stale",
                ),
            ]
        )
        await seed.commit()

    await _run_atomic_submit(session_maker, game_id, list(_BLUNDER_SUBMIT_EVALS_142))
    return game_id, []


async def _scenario_6(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """Opening dedup-transplanted plies — a cache-omitted opening ply must merge its
    cached pv into engine_result_map, so the flaw's PV lines stay NULL / fillable
    (never a permanent []-sentinel taint, quick 260703-qgp)."""
    base = _BASE_HASH["scenario_6_dedup_transplant_no_sentinel"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    # Cache ply 2's position (the flaw's own board, "missed" line node 0) WITH a
    # real, walkable pv. The worker's partial submit omits ply 2 accordingly.
    cached_pv = "g1f3 b8c6"
    await _insert_opening_cache_with_pv(session_maker, [(base + 2, 30, None, "g1f3", cached_pv)])
    # Ply 3 ("allowed" line node 0) is submitted directly with a real, walkable pv
    # too, so only the missed line's cache-merged pv is under test.
    allowed_pv = "b8c6 f1c4"
    partial = [dict(e) for e in _BLUNDER_SUBMIT_EVALS_142 if e["ply"] != 2]
    for e in partial:
        if e["ply"] == 3:
            e["pv"] = allowed_pv

    await _run_atomic_submit(session_maker, game_id, partial)
    return game_id, [base + 2]


async def _scenario_7(
    session_maker: async_sessionmaker[AsyncSession], user_id: int
) -> tuple[int, list[int]]:
    """blobs_pending=True suppression — a server-found flaw the worker did not blob
    (both PV lines walkable but zero submitted blob_nodes) is suppressed to NULL,
    never persisted raw/ungated (Phase 147 D-01/D-03)."""
    base = _BASE_HASH["scenario_7_blobs_pending_suppression"]
    game_id = await _insert_game(session_maker, user_id, pgn=_SIX_PLY_PGN_142)
    await _insert_six_ply_positions(session_maker, user_id, game_id, base)

    walkable_evals: list[dict[str, object]] = [dict(e) for e in _BLUNDER_SUBMIT_EVALS_142]
    walkable_evals[2]["pv"] = _WALKABLE_PV_PLY2  # flaw's "missed" line (node0 = ply 2)
    walkable_evals[3]["pv"] = _WALKABLE_PV_PLY3  # flaw's "allowed" line (node0 = ply 3)

    with _patch_tactic_detection(fake_assemble=False):
        await _run_atomic_submit(session_maker, game_id, walkable_evals)
    return game_id, []


_ScenarioBuilder = Callable[
    [async_sessionmaker[AsyncSession], int], Awaitable[tuple[int, list[int]]]
]

_BUILDERS: Final[dict[str, _ScenarioBuilder]] = {
    "scenario_1_fresh_full_submit": _scenario_1,
    "scenario_2_residual_hole_retry": _scenario_2,
    "scenario_3_flip_out": _scenario_3,
    "scenario_4_flip_in": _scenario_4,
    "scenario_5_entry_pass_replaced": _scenario_5,
    "scenario_6_dedup_transplant_no_sentinel": _scenario_6,
    "scenario_7_blobs_pending_suppression": _scenario_7,
}


async def _dump_game_flaws(
    session_maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[str, dict[str, Any]]:
    """Dump every game_flaws row for ``game_id``, keyed by ply (as a string, for
    JSON-object compatibility), content columns only (DUMP_COLUMNS)."""
    from app.models.game_flaw import GameFlaw

    cols = [getattr(GameFlaw, name) for name in DUMP_COLUMNS]
    async with session_maker() as session:
        result = await session.execute(
            select(GameFlaw.ply, *cols).where(GameFlaw.game_id == game_id).order_by(GameFlaw.ply)
        )
        rows = result.all()
    return {str(row[0]): dict(zip(DUMP_COLUMNS, row[1:], strict=True)) for row in rows}


async def run_scenario(
    scenario_name: str,
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
) -> dict[str, dict[str, Any]]:
    """Run one named scenario end-to-end against ``session_maker`` and return its
    ply-keyed game_flaws dump (JSON-serializable). Cleans up its own game/opening-
    cache rows on the way out, whether it succeeded or raised.

    ``session_maker`` must be bound to an isolated test DB — this module never
    opens its own engine/connection (D-01: caller owns DB lifecycle, whether that's
    the generator script's ephemeral per-run DB or pytest's per-run test DB).
    """
    if scenario_name not in _BUILDERS:
        raise ValueError(f"Unknown scenario: {scenario_name!r}. Must be one of {SCENARIO_NAMES}")

    import app.routers.eval_remote as eval_remote_module
    import app.services.eval_apply as eval_apply_module
    import app.services.eval_drain as eval_drain_module

    mp = pytest.MonkeyPatch()
    mp.setattr(eval_remote_module, "async_session_maker", session_maker)
    mp.setattr(eval_drain_module, "async_session_maker", session_maker)
    # Phase 150 R7: _derive_atomic_sentinel_lines opens its own internal session in
    # eval_apply.py now (moved from eval_drain.py) — must redirect that binding too.
    mp.setattr(eval_apply_module, "async_session_maker", session_maker)

    game_id: int | None = None
    cache_hashes: list[int] = []
    try:
        game_id, cache_hashes = await _BUILDERS[scenario_name](session_maker, user_id)
        return await _dump_game_flaws(session_maker, game_id)
    finally:
        mp.undo()
        if game_id is not None:
            await _delete_games(session_maker, [game_id])
        if cache_hashes:
            await _delete_opening_cache(session_maker, cache_hashes)
