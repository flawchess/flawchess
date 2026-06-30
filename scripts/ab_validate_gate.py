"""Engine-free A/B gate-validation harness for Phase 144 (VALID-01, VALID-02).

Read-only: performs ZERO DB writes — no commits, no UPDATE statements.
Engine-free: zero Stockfish calls, no chess engine instantiation of any kind.
Scope: dev-28 only per D-01a. The 216 blob-bearing flaws are the entire A/B universe (D-01).

Purpose:
  Load user-28's stored MultiPV-2 JSONB blobs once and run tactic detection twice over the
  same stored inputs:
    - Ungated arm: _detect_tactic_for_flaw directly (pre-gate, the genuinely pre-143 path).
    - Gated arm:   _classify_tactic_gated at the test margin (the single SC4 classify path).
  Both arms read the SAME stored blobs, isolating the gate's contribution from eval_cp
  cross-machine non-determinism (VALID-01 core guarantee).

Output: reports/retag/ab-validation-YYYY-MM-DD.md with per-motif ungated/suppressed/survived
counts, per-arm depth distributions, a dropped-case list with local analysis-board
deep-links, and placeholder sections for the HUMAN-UAT hand-check result.

AGPL boundary: gate heuristics, constants, and names only — copy NO lichess-puzzler source.
See forcing_line_gate.py for the full boundary comment.

Usage:
    uv run python scripts/ab_validate_gate.py --db dev
    uv run python scripts/ab_validate_gate.py --db dev --user-id 28 --margin 0.35
    uv run python scripts/ab_validate_gate.py --db dev --user-id 28 --neighbourhood
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import chess
import sentry_sdk
from sqlalchemy import Row, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402

# Full model-registration import chain — GameFlaw/GamePosition carry FKs to games → users →
# oauth_accounts; importing only the queried models leaves parent tables unregistered and
# select() raises NoReferencedTableError at compile time. Game is also queried directly
# (player-only join), the others remain registration-only.
from app.models.game import Game  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.game_flaws_repository import TACTIC_TAG_COLUMNS  # noqa: E402
from app.repositories.query_utils import player_only_gate  # noqa: E402
from app.services.forcing_line_gate import ONLY_MOVE_WIN_PROB_MARGIN  # noqa: E402
from app.services.tactic_detector import TacticMotifInt  # noqa: E402

# The two arm functions: the ungated path (pre-143) and the gated path (SC4 classify path).
from app.services.flaws_service import (  # noqa: E402
    _classify_tactic_gated,
    _detect_tactic_for_flaw,
)

# ---------------------------------------------------------------------------
# Named constants (no magic numbers — CLAUDE.md)
# ---------------------------------------------------------------------------

# Default user-id for the A/B validation run (dev-28 only per D-01a).
DEFAULT_USER_ID: int = 28

# Small-N threshold: motifs with fewer than this many ungated detections get a caveat flag.
SMALL_N_THRESHOLD: int = 10

# Depth bucket labels for the distribution table.
DEPTH_BUCKETS: tuple[str, ...] = ("0", "1", "2", "3+")

# Cap the hand-check dropped-case listing (table + per-case PV blocks). The executive
# summary still reports the true total; only the enumerated detail is truncated to keep
# the report reviewable (the full set is in the thousands).
MAX_REPORTED_DROPPED_CASES: int = 1000

# Neighbourhood margins for the optional --neighbourhood sweep.
NEIGHBOURHOOD_MARGINS: tuple[float, ...] = (0.30, 0.40)


# ---------------------------------------------------------------------------
# Local position view (mirrors retag_flaws._PosRow — not imported to avoid coupling)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PosRow:
    """Minimal position view the tactic kernel reads (move_san / pv / eval_mate / eval_cp).

    eval_cp is white-perspective centipawn eval at this ply — used by the gate's
    already-winning reject (ALREADY_WINNING_CP_THRESHOLD check).
    """

    move_san: str | None
    pv: str | None
    eval_mate: int | None
    eval_cp: int | None


_EMPTY_POS = _PosRow(move_san=None, pv=None, eval_mate=None, eval_cp=None)

# Max (user_id, game_id, ply) tuples per position-load IN clause. A single IN over
# thousands of tuples overflows Postgres' max_stack_depth at parse time (#bug found
# when the dev-28 blob set grew past ~3k flaws via the Phase 144 MultiPV backfill).
_POSITION_KEY_CHUNK = 1000


# ---------------------------------------------------------------------------
# Public result types (imported by tests)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbCase:
    """A single dropped case: ungated detected a motif that the gated arm suppressed.

    Fields:
        orientation:  "allowed" or "missed".
        motif_name:   TacticMotifInt(motif_int).name, or str(int) on ValueError.
        game_id:      flaw game_id (drives the local analysis-board deep-link).
        fen:          board_fen() at the flaw ply (piece-placement only, no side-to-move).
        ply:          flaw ply index.
        depth:        tactic_depth returned by the ungated arm.
        pv_line:      stored PV string from game_positions.pv (raw UCI).
        analysis_url: http://localhost:5173/analysis?game_id={game_id}&ply={ply} (game mode).
        fen_url:      http://localhost:5173/analysis?fen=... free-play link seeded at the
                      board the PV line starts from (None when that board can't be built).
        line_fen:     full FEN (with side-to-move/move-number) the PV line starts from —
                      the flaw decision board for missed, the post-flaw board for allowed.
        san_line:     pv_line rendered in SAN with move numbers (None when unconvertible).
    """

    orientation: str
    motif_name: str
    game_id: int
    fen: str
    ply: int
    depth: int | None
    pv_line: str | None
    analysis_url: str
    fen_url: str | None
    line_fen: str | None
    san_line: str | None


@dataclass(frozen=True)
class AbResult:
    """Aggregated A/B comparison result returned by run_ab_validation.

    Counts (per orientation):
        ungated_count_*: flaws where the ungated arm detected a motif.
        gated_count_*:   flaws where the gated arm detected a motif (subset of ungated).

    dropped_cases: list of AbCase where ungated detected but gated suppressed.
    report_path:   path to the written report file (None if writing was skipped).
    """

    ungated_count_allowed: int
    gated_count_allowed: int
    ungated_count_missed: int
    gated_count_missed: int
    dropped_cases: list[AbCase]
    report_path: Path | None


# ---------------------------------------------------------------------------
# URL helper
# ---------------------------------------------------------------------------

# Local FlawChess frontend (Vite dev server) base for analysis-board deep-links.
ANALYSIS_BASE_URL = "http://localhost:5173"


def analysis_board_url(game_id: int, ply: int) -> str:
    """Build a local FlawChess analysis-board deep-link from game_id and ply.

    The dropped-case adjudication surface is the app's own analysis board (game
    mode: ?game_id=X&ply=Y loads the full game at that ply — see Analysis.tsx
    ROUTE-04). This is preferred over a reconstructed-FEN lichess link because the
    stored game_flaw.fen is piece-placement only (no castling / en passant), so an
    external FEN link can mis-render those positions; loading the real game at the
    ply renders the exact position with full state.

    Args:
        game_id: The flaw's game_id.
        ply: Flaw ply index.

    Returns:
        http://localhost:5173/analysis?game_id={game_id}&ply={ply}
    """
    return f"{ANALYSIS_BASE_URL}/analysis?game_id={game_id}&ply={ply}"


def fen_board_url(full_fen: str) -> str:
    """Build a local analysis free-play deep-link from a full FEN (Analysis.tsx ROUTE-02).

    The ?fen= mode seeds free play at the position, which (unlike ?game_id=&ply= game mode)
    lets the reviewer step through the dropped-case PV by hand — the suppressed line has no
    move-list tactic chip to expand, so game mode would land on the ply with nothing to
    inspect. The FEN's castling/en-passant fields are '-' (game_flaw.fen is piece-placement
    only), so a line hinging on castling rights or en passant may mis-render; the game-mode
    link remains available for those.
    """
    return f"{ANALYSIS_BASE_URL}/analysis?fen={quote(full_fen, safe='/')}"


def _side_to_move_char(ply: int) -> str:
    """White to move on even plies, black on odd (ply 0 = initial position, white to move)."""
    return "w" if ply % 2 == 0 else "b"


def _board_at_line_start(
    orientation: str,
    board_fen: str,
    ply: int,
    flaw_move_san: str | None,
) -> chess.Board | None:
    """Build the board the dropped-case PV line begins from.

    missed:  the decision board at the flaw ply (board_fen, side-to-move from ply parity);
             the missed best-move PV (positions[ply].pv) starts here.
    allowed: the board AFTER the flaw move (ply+1); the refutation PV (positions[ply+1].pv)
             starts here, so the actually-played flaw move (positions[ply].move_san) is
             pushed onto the decision board first. This is why the line FEN differs from the
             flaw FEN for allowed cases — the earlier "Full FEN" line used the flaw-ply board
             and side-to-move, which mismatched the allowed PV by one move.

    Castling/en-passant are '-' (board_fen carries no such state), so a flaw move that is a
    castle can't be replayed; returns None there and on any parse failure, and the caller
    degrades to the game-mode link / raw UCI.
    """
    fullmove = ply // 2 + 1
    try:
        board = chess.Board(f"{board_fen} {_side_to_move_char(ply)} - - 0 {fullmove}")
    except ValueError:
        return None
    if orientation == "allowed":
        if not flaw_move_san:
            return None
        try:
            board.push_san(flaw_move_san)  # advance to the post-flaw board (ply+1)
        except ValueError:
            return None
    return board


def _uci_line_to_san(board: chess.Board, pv_uci: str | None) -> str | None:
    """Render a space-joined UCI PV as SAN with move numbers, replaying on a copy of `board`.

    Stops at the first token that won't parse or is illegal from the running board (the
    stored line should be fully legal; this is a safety net). Returns None when nothing
    could be converted.
    """
    if not pv_uci:
        return None
    work = board.copy()
    parts: list[str] = []
    for token in pv_uci.split():
        try:
            move = chess.Move.from_uci(token)
        except ValueError:
            break
        if move not in work.legal_moves:
            break
        if work.turn == chess.WHITE:
            parts.append(f"{work.fullmove_number}.")
        elif not parts:
            parts.append(f"{work.fullmove_number}...")
        parts.append(work.san(move))
        work.push(move)
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# DB queries (read-only)
# ---------------------------------------------------------------------------


async def _load_ab_flaws(session: AsyncSession, user_id: int) -> list[Row[Any]]:
    """Load the player's blob-bearing flaws for the given user (single non-paginated query).

    Selects only flaws where at least one PV blob is present; pre-142 rows (NULL blobs)
    are excluded because both arms would produce identical (no-gate) results.

    Player-only: game_flaws stores BOTH movers' flaws (Phase 113, D-06). This harness
    only reports the player's own mistakes, so the rows are gated to plies where the
    mover color matches games.user_color via player_only_gate (the single source for the
    ply-parity × user_color math — never inline ``ply % 2`` here).

    allowed_pv_lines / missed_pv_lines are deferred=True on the ORM entity but safe to
    select explicitly — asyncpg auto-deserializes JSONB to list[dict].
    """
    stmt = (
        select(
            GameFlaw.user_id,
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.fen,
            *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
            GameFlaw.allowed_pv_lines,
            GameFlaw.missed_pv_lines,
        )
        .join(Game, (Game.id == GameFlaw.game_id) & (Game.user_id == GameFlaw.user_id))
        .where(
            GameFlaw.user_id == user_id,
            player_only_gate(GameFlaw.ply, Game.user_color),
            or_(
                GameFlaw.allowed_pv_lines.isnot(None),
                GameFlaw.missed_pv_lines.isnot(None),
            ),
        )
        .order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply)
    )
    result = await session.execute(stmt)
    return list(result.all())


async def _load_positions(
    session: AsyncSession,
    flaws: list[Row[Any]],
) -> dict[tuple[int, int, int], _PosRow]:
    """Load positions at (ply-1, ply, ply+1) for all flaws, chunking the tuple-IN.

    The missed arm reads positions[ply]; the allowed arm reads positions[ply+1].
    eval_cp at ply-1 (the board BEFORE the flaw move) feeds the gate's already-winning
    reject — see the Bug A fix in _process_flaws and flaws_service._build_flaw_record.

    The key set is chunked into _POSITION_KEY_CHUNK-sized tuple-IN batches: a single
    IN over thousands of (user_id, game_id, ply) tuples overflows Postgres'
    max_stack_depth during parse (surfaced once the dev-28 blob set grew past ~3k
    flaws via the Phase 144 MultiPV backfill). Chunking keeps each statement small.
    """
    keys: set[tuple[int, int, int]] = set()
    for flaw in flaws:
        if flaw.ply >= 1:
            keys.add((flaw.user_id, flaw.game_id, flaw.ply - 1))
        keys.add((flaw.user_id, flaw.game_id, flaw.ply))
        keys.add((flaw.user_id, flaw.game_id, flaw.ply + 1))

    key_list = list(keys)
    out: dict[tuple[int, int, int], _PosRow] = {}
    for start in range(0, len(key_list), _POSITION_KEY_CHUNK):
        chunk = key_list[start : start + _POSITION_KEY_CHUNK]
        stmt = select(
            GamePosition.user_id,
            GamePosition.game_id,
            GamePosition.ply,
            GamePosition.move_san,
            GamePosition.pv,
            GamePosition.eval_mate,
            GamePosition.eval_cp,
        ).where(tuple_(GamePosition.user_id, GamePosition.game_id, GamePosition.ply).in_(chunk))
        result = await session.execute(stmt)
        for uid, gid, pos_ply, move_san, pv, eval_mate, eval_cp in result.all():
            out[(uid, gid, pos_ply)] = _PosRow(
                move_san=move_san, pv=pv, eval_mate=eval_mate, eval_cp=eval_cp
            )
    return out


# ---------------------------------------------------------------------------
# Per-flaw A/B comparison kernel
# ---------------------------------------------------------------------------


def _decode_motif(motif_int: int | None) -> str | None:
    """Decode a TacticMotifInt value to its name; fall back to str(int) on ValueError."""
    if motif_int is None:
        return None
    try:
        return TacticMotifInt(motif_int).name
    except ValueError:
        return str(motif_int)


def _build_positions(ply: int, cur: _PosRow | None, nxt: _PosRow | None) -> list[Any]:
    """Build the sparse positions list the tactic kernels expect.

    Only ply and ply+1 carry real data; all other indices use _EMPTY_POS so that
    integer indexing and the `ply + 1 < len(positions)` guard behave correctly.
    Length ply+2 keeps positions[ply+1] valid.
    """
    positions: list[Any] = [_EMPTY_POS] * (ply + 2)
    if cur is not None:
        positions[ply] = cur
    if nxt is not None:
        positions[ply + 1] = nxt
    return positions


def _run_both_arms(
    ply: int,
    fen: str,
    positions: list[Any],
    allowed_pv_blob: list[Any] | None,
    missed_pv_blob: list[Any] | None,
    pre_flaw_eval_cp: int | None,
    margin: float,
) -> tuple[
    tuple[int | None, int | None, int | None, int | None],
    tuple[int | None, int | None, int | None, int | None],
    tuple[int | None, int | None, int | None, int | None],
    tuple[int | None, int | None, int | None, int | None],
]:
    """Run ungated and gated arms for both orientations.

    Returns (ungated_allowed, ungated_missed, gated_allowed, gated_missed).
    Each element is (motif, piece, confidence, depth) or all-None.

    UNGATED arm = _detect_tactic_for_flaw directly: the genuinely pre-143 detection
    path. apply_forcing_line_filter is NEVER called here (D-02a requirement).

    GATED arm = _classify_tactic_gated at the given margin: the SC4 single classify
    path identical to what retag_flaws.py uses.
    """
    fen_map = {ply: fen}

    # Ungated arm: call the detection kernel directly, bypassing the gate entirely.
    ungated_allowed = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="allowed")
    ungated_missed = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="missed")

    # Gated arm: the full classify path with apply_forcing_line_filter at the test margin.
    gated_allowed = _classify_tactic_gated(
        ply,
        fen_map,
        positions,
        orientation="allowed",
        pv_blob=allowed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=margin,
    )
    gated_missed = _classify_tactic_gated(
        ply,
        fen_map,
        positions,
        orientation="missed",
        pv_blob=missed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=margin,
    )

    return ungated_allowed, ungated_missed, gated_allowed, gated_missed


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _pv_for_orientation(
    orientation: str,
    ply: int,
    cur: _PosRow | None,
    nxt: _PosRow | None,
) -> str | None:
    """Return the stored PV line for the dropped-case surface.

    allowed: refutation PV from positions[ply+1].pv (board after flaw move).
    missed:  best-move PV from positions[ply].pv (board before flaw move).
    """
    if orientation == "allowed":
        return nxt.pv if nxt is not None else None
    return cur.pv if cur is not None else None


def _depth_bucket(depth: int | None) -> str:
    """Map a tactic depth int to one of the four report buckets."""
    if depth is None:
        return "3+"
    if depth <= 2:
        return str(depth)
    return "3+"


def _accumulate(
    flaw: Row[Any],
    ungated: tuple[int | None, ...],
    gated: tuple[int | None, ...],
    orientation: str,
    ungated_idx: int,
    cur: _PosRow | None,
    nxt: _PosRow | None,
    motif_ungated: Counter[str],
    motif_suppressed: Counter[str],
    motif_survived: Counter[str],
    depth_ungated: dict[str, Counter[str]],
    depth_gated: dict[str, Counter[str]],
    dropped_cases: list[AbCase],
) -> None:
    """Accumulate per-orientation stats for one flaw."""
    u_motif: int | None = ungated[ungated_idx]  # type: ignore[assignment]
    g_motif: int | None = gated[ungated_idx]  # type: ignore[assignment]
    u_depth: int | None = ungated[ungated_idx + 3]  # type: ignore[assignment]

    if u_motif is None:
        return  # ungated didn't detect — nothing to compare

    name = _decode_motif(u_motif) or str(u_motif)
    motif_ungated[name] += 1
    depth_ungated[name][_depth_bucket(u_depth)] += 1

    if g_motif is None:
        # Gate suppressed: dropped case.
        motif_suppressed[name] += 1
        pv = _pv_for_orientation(orientation, flaw.ply, cur, nxt)
        # Seed the FEN free-play link + SAN line from the board the PV starts on (the
        # post-flaw board for allowed needs the actually-played flaw move, cur.move_san).
        flaw_move_san = cur.move_san if cur is not None else None
        board = _board_at_line_start(orientation, flaw.fen, flaw.ply, flaw_move_san)
        line_fen = board.fen() if board is not None else None
        san_line = _uci_line_to_san(board, pv) if board is not None else None
        dropped_cases.append(
            AbCase(
                orientation=orientation,
                motif_name=name,
                game_id=flaw.game_id,
                fen=flaw.fen,
                ply=flaw.ply,
                depth=u_depth,
                pv_line=pv,
                analysis_url=analysis_board_url(flaw.game_id, flaw.ply),
                fen_url=fen_board_url(line_fen) if line_fen else None,
                line_fen=line_fen,
                san_line=san_line,
            )
        )
    else:
        # Survived: record gated depth (should match ungated depth).
        motif_survived[name] += 1
        g_depth: int | None = gated[ungated_idx + 3]  # type: ignore[assignment]
        depth_gated[name][_depth_bucket(g_depth)] += 1


def _process_flaws(
    flaws: list[Row[Any]],
    pos_by_key: dict[tuple[int, int, int], _PosRow],
    margin: float,
) -> tuple[
    Counter[str],
    Counter[str],
    Counter[str],
    Counter[str],
    Counter[str],
    Counter[str],
    dict[str, Counter[str]],
    dict[str, Counter[str]],
    dict[str, Counter[str]],
    dict[str, Counter[str]],
    list[AbCase],
    int,
    int,
]:
    """Run both arms over all flaws and return aggregated counters + dropped cases.

    Returns:
        (allowed_ungated, allowed_suppressed, allowed_survived,
         missed_ungated, missed_suppressed, missed_survived,
         depth_ungated_allowed, depth_gated_allowed,
         depth_ungated_missed, depth_gated_missed,
         dropped_cases, ungated_count_allowed, ungated_count_missed)
    """
    allowed_ungated: Counter[str] = Counter()
    allowed_suppressed: Counter[str] = Counter()
    allowed_survived: Counter[str] = Counter()
    missed_ungated: Counter[str] = Counter()
    missed_suppressed: Counter[str] = Counter()
    missed_survived: Counter[str] = Counter()

    # depth_* keyed by motif_name -> Counter of bucket -> count.
    depth_ua: dict[str, Counter[str]] = {}
    depth_ga: dict[str, Counter[str]] = {}
    depth_um: dict[str, Counter[str]] = {}
    depth_gm: dict[str, Counter[str]] = {}

    dropped_cases: list[AbCase] = []

    for flaw in flaws:
        ply = flaw.ply
        cur = pos_by_key.get((flaw.user_id, flaw.game_id, ply))
        nxt = pos_by_key.get((flaw.user_id, flaw.game_id, ply + 1))
        # Bug A fix: pre_flaw_eval_cp is the eval BEFORE the flaw move (positions[ply-1]),
        # not positions[ply] (which is the eval AFTER the flaw move). Mirrors the
        # flaws_service._build_flaw_record fix so this report reflects production behaviour.
        prv = pos_by_key.get((flaw.user_id, flaw.game_id, ply - 1))
        pre_flaw_eval_cp = prv.eval_cp if prv is not None else None
        positions = _build_positions(ply, cur, nxt)

        ua, um, ga, gm = _run_both_arms(
            ply,
            flaw.fen,
            positions,
            allowed_pv_blob=flaw.allowed_pv_lines,
            missed_pv_blob=flaw.missed_pv_lines,
            pre_flaw_eval_cp=pre_flaw_eval_cp,
            margin=margin,
        )

        # Ensure per-motif depth counters exist (initialised on first encounter).
        _init_depth_counters(ua, depth_ua)
        _init_depth_counters(gm, depth_gm)
        _init_depth_counters(ga, depth_ga)
        _init_depth_counters(um, depth_um)

        # TACTIC_TAG_COLUMNS layout:
        # [0] allowed_tactic_motif, [1] allowed_tactic_piece, [2] allowed_confidence,
        # [3] allowed_tactic_depth, [4] missed_tactic_motif, [5] missed_tactic_piece,
        # [6] missed_confidence, [7] missed_tactic_depth
        # ungated/gated tuples match this same 4-element layout per orientation:
        # (motif, piece, confidence, depth)

        _accumulate(
            flaw,
            ua,
            ga,
            "allowed",
            0,
            cur,
            nxt,
            allowed_ungated,
            allowed_suppressed,
            allowed_survived,
            depth_ua,
            depth_ga,
            dropped_cases,
        )
        _accumulate(
            flaw,
            um,
            gm,
            "missed",
            0,
            cur,
            nxt,
            missed_ungated,
            missed_suppressed,
            missed_survived,
            depth_um,
            depth_gm,
            dropped_cases,
        )

    return (
        allowed_ungated,
        allowed_suppressed,
        allowed_survived,
        missed_ungated,
        missed_suppressed,
        missed_survived,
        depth_ua,
        depth_ga,
        depth_um,
        depth_gm,
        dropped_cases,
        sum(allowed_ungated.values()),
        sum(missed_ungated.values()),
    )


def _init_depth_counters(
    arm_result: tuple[int | None, ...],
    depth_dict: dict[str, Counter[str]],
) -> None:
    """Ensure the depth_dict has a Counter for the motif detected in arm_result."""
    motif_int: int | None = arm_result[0]  # type: ignore[assignment]
    if motif_int is not None:
        name = _decode_motif(motif_int) or str(motif_int)
        if name not in depth_dict:
            depth_dict[name] = Counter()


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------


def _motif_table(
    ungated: Counter[str],
    suppressed: Counter[str],
    survived: Counter[str],
) -> str:
    """Build a per-motif pipe table with ungated/suppressed/survived/suppression%."""
    all_motifs = sorted(set(ungated) | set(suppressed) | set(survived))
    if not all_motifs:
        return "_No detections in this scope._\n"

    lines = [
        "| Motif | Ungated | Suppressed | Survived | Suppression % | Note |",
        "|-------|---------|------------|----------|---------------|------|",
    ]
    for motif in all_motifs:
        u = ungated[motif]
        sp = suppressed[motif]
        sv = survived[motif]
        pct = f"{100 * sp / u:.1f}%" if u > 0 else "n/a"
        note = f"small-N (N<{SMALL_N_THRESHOLD})" if u < SMALL_N_THRESHOLD else ""
        lines.append(f"| {motif} | {u} | {sp} | {sv} | {pct} | {note} |")
    return "\n".join(lines) + "\n"


def _depth_table(
    depth_ungated: dict[str, Counter[str]],
    depth_gated: dict[str, Counter[str]],
) -> str:
    """Build the depth-shift distribution table (Motif | Arm | D0 | D1 | D2 | D3+ | Mean)."""
    all_motifs = sorted(set(depth_ungated) | set(depth_gated))
    if not all_motifs:
        return "_No detections with depth data._\n"

    lines = [
        "| Motif | Arm | Depth 0 | Depth 1 | Depth 2 | Depth 3+ | Mean |",
        "|-------|-----|---------|---------|---------|----------|------|",
    ]
    for motif in all_motifs:
        for arm_label, depth_counter in (
            ("ungated", depth_ungated.get(motif, Counter())),
            ("gated", depth_gated.get(motif, Counter())),
        ):
            d0 = depth_counter.get("0", 0)
            d1 = depth_counter.get("1", 0)
            d2 = depth_counter.get("2", 0)
            d3 = depth_counter.get("3+", 0)
            total = d0 + d1 + d2 + d3
            # Mean: approximate using bucket midpoints (3+ -> 3).
            mean = (d0 * 0 + d1 * 1 + d2 * 2 + d3 * 3) / total if total > 0 else 0.0
            lines.append(f"| {motif} | {arm_label} | {d0} | {d1} | {d2} | {d3} | {mean:.1f} |")
    return "\n".join(lines) + "\n"


def _dropped_cases_section(dropped_cases: list[AbCase]) -> str:
    """Build the dropped-cases table + per-case PV detail block.

    Capped at MAX_REPORTED_DROPPED_CASES; a truncation note is emitted when the full
    set exceeds the cap so the report never silently hides dropped cases.
    """
    if not dropped_cases:
        return "_No dropped cases at this margin._\n"

    total = len(dropped_cases)
    shown = dropped_cases[:MAX_REPORTED_DROPPED_CASES]
    truncation_note = ""
    if total > MAX_REPORTED_DROPPED_CASES:
        truncation_note = (
            f"_Showing the first {MAX_REPORTED_DROPPED_CASES} of {total} dropped cases "
            f"(capped by MAX_REPORTED_DROPPED_CASES)._\n\n"
        )

    table_lines = [
        "| # | Orientation | Motif | Depth | Moves | Game | FEN |",
        "|---|-------------|-------|-------|-------|------|-----|",
    ]
    pv_blocks: list[str] = []

    for i, case in enumerate(shown, start=1):
        depth_str = str(case.depth) if case.depth is not None else "?"
        moves_cell = case.san_line or case.pv_line or "_n/a_"
        game_cell = f"[ply {case.ply}]({case.analysis_url})"
        fen_cell = f"[board]({case.fen_url})" if case.fen_url else "_n/a_"
        table_lines.append(
            f"| {i} | {case.orientation} | {case.motif_name} | {depth_str} "
            f"| `{moves_cell}` | {game_cell} | {fen_cell} |"
        )
        # SAN line preferred (CLAUDE.md: standard notation, not UCI); fall back to raw UCI
        # only when the line couldn't be replayed onto a board.
        if case.san_line:
            moves_block = f"Moves (SAN): `{case.san_line}`"
        else:
            moves_block = f"Moves (UCI — SAN unavailable): `{case.pv_line or 'n/a'}`"
        fen_display = case.line_fen or f"{case.fen} {_side_to_move_char(case.ply)} - - 0 1"
        fen_link = case.fen_url or "_n/a_"
        pv_blocks.append(
            f"#### Case {i} — {case.motif_name} ({case.orientation}, depth {depth_str})\n\n"
            f"{moves_block}\n\n"
            f"FEN (line start): `{fen_display}`\n\n"
            f"Game (full game at ply): {case.analysis_url}\n\n"
            f"FEN (free-play from line start): {fen_link}\n"
        )

    table = "\n".join(table_lines) + "\n"
    detail = "\n### Full PV Lines for Dropped Cases\n\n" + "\n".join(pv_blocks)
    return truncation_note + table + detail


def _pct(num: int, denom: int) -> str:
    return f"{100 * num / denom:.1f}%" if denom > 0 else "n/a"


def _write_ab_report(
    margin: float,
    user_id: int,
    total_flaws: int,
    allowed_ungated: Counter[str],
    allowed_suppressed: Counter[str],
    allowed_survived: Counter[str],
    missed_ungated: Counter[str],
    missed_suppressed: Counter[str],
    missed_survived: Counter[str],
    depth_ua: dict[str, Counter[str]],
    depth_ga: dict[str, Counter[str]],
    depth_um: dict[str, Counter[str]],
    depth_gm: dict[str, Counter[str]],
    dropped_cases: list[AbCase],
    neighbourhood_rows: list[str],
    report_dir: Path | None,
) -> Path:
    """Write the A/B validation report to reports/retag/ab-validation-YYYY-MM-DD.md.

    report_dir: injectable for tests (default: committed reports/retag/).
    Returns the path of the written report.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    if report_dir is None:
        report_dir = Path(__file__).resolve().parent.parent / "reports" / "retag"
    report_path = report_dir / f"ab-validation-{date_str}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    au = sum(allowed_ungated.values())
    as_ = sum(allowed_suppressed.values())
    av = sum(allowed_survived.values())
    mu = sum(missed_ungated.values())
    ms = sum(missed_suppressed.values())
    mv = sum(missed_survived.values())

    exec_rows = (
        f"| Ungated tags (allowed) | {au} |\n"
        f"| Gated survived (allowed) | {av} |\n"
        f"| Gate suppressed (allowed) | {as_} ({_pct(as_, au)}) |\n"
        f"| Ungated tags (missed) | {mu} |\n"
        f"| Gated survived (missed) | {mv} |\n"
        f"| Gate suppressed (missed) | {ms} ({_pct(ms, mu)}) |\n"
    )

    neighbourhood_section = ""
    if neighbourhood_rows:
        neighbourhood_section = (
            "\n## Neighbourhood Sweep (0.30 / 0.40)\n\n"
            + "| Margin | Suppressed Allowed | Suppressed Missed |\n"
            + "|--------|-------------------|------------------|\n"
            + "\n".join(neighbourhood_rows)
            + "\n"
        )

    dropped_count = len(dropped_cases)
    motif_allowed = _motif_table(allowed_ungated, allowed_suppressed, allowed_survived)
    motif_missed = _motif_table(missed_ungated, missed_suppressed, missed_survived)
    depth_section = (
        "### Allowed Orientation\n\n"
        + _depth_table(depth_ua, depth_ga)
        + "\n### Missed Orientation\n\n"
        + _depth_table(depth_um, depth_gm)
    )
    dropped_section = _dropped_cases_section(dropped_cases)

    content = f"""# FlawChess A/B Gate Validation Report

**Generated:** {ts_str}
**Script:** `scripts/ab_validate_gate.py`
**DB:** dev, user-id {user_id}
**Scope:** player's own flaws only (opponent flaws excluded via player_only_gate)
**Margin tested:** {margin} (ONLY_MOVE_WIN_PROB_MARGIN default: {ONLY_MOVE_WIN_PROB_MARGIN})
**Total blob-bearing flaws loaded:** {total_flaws}

## Executive Summary

| Metric | Count |
|--------|-------|
{exec_rows}
| Total dropped cases | {dropped_count} |
{neighbourhood_section}
## Per-Motif: Allowed Orientation

{motif_allowed}
## Per-Motif: Missed Orientation

{motif_missed}
## Depth-Shift Distribution

{depth_section}
## Dropped Cases — Hand-Check Required (HUMAN-UAT)

{dropped_section}
## False Negative Count (HUMAN-UAT — fill in after hand-check)

- **Total dropped:** {dropped_count}
- **False negatives (good tags killed):** _[fill in after reviewing each case above]_
- **Correct drops (noise):** _[fill in]_

## A/B Summary & Margin Justification

Margin {margin} — confirm or change based on hand-check results.
`ONLY_MOVE_WIN_PROB_MARGIN` in `forcing_line_gate.py` line 52 will be updated with a
pointer comment to this report after the hand-check is complete (Plan 02).

*Generated by `scripts/ab_validate_gate.py --db dev --user-id {user_id} --margin {margin}`.*
"""

    report_path.write_text(content)
    return report_path


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def run_ab_validation(
    *,
    db: str = "dev",
    user_id: int = DEFAULT_USER_ID,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
    neighbourhood: bool = False,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    report_dir: Path | None = None,
) -> AbResult:
    """Load blobs once, run both arms, diff, write report.

    Read-only: no commit, no UPDATE, no engine call.

    Args:
        db:            DB target ("dev", "benchmark", "prod").
        user_id:       Scope to this user (default: 28, dev-only per D-01a).
        margin:        Forcing-line gate win-prob margin (default: ONLY_MOVE_WIN_PROB_MARGIN).
        neighbourhood: When True, also report suppression counts at 0.30 and 0.40 for context.
        session_maker: Injectable session factory for testing.
        report_dir:    Injectable output dir; defaults to committed reports/retag/.

    Returns:
        AbResult with per-orientation ungated/gated counts, dropped cases, report path.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        try:
            flaws = await _load_ab_flaws(session, user_id)
        except Exception as exc:
            sentry_sdk.set_context("ab_validate_gate", {"user_id": user_id})
            sentry_sdk.capture_exception(exc)
            raise

        try:
            pos_by_key = await _load_positions(session, flaws)
        except Exception as exc:
            sentry_sdk.set_context("ab_validate_gate", {"user_id": user_id})
            sentry_sdk.capture_exception(exc)
            raise

    (
        au,
        as_,
        av,
        mu,
        ms,
        mv,
        depth_ua,
        depth_ga,
        depth_um,
        depth_gm,
        dropped_cases,
        ungated_allowed,
        ungated_missed,
    ) = _process_flaws(flaws, pos_by_key, margin)

    neighbourhood_rows: list[str] = []
    if neighbourhood:
        for nb_margin in NEIGHBOURHOOD_MARGINS:
            *_, nb_dropped, nb_ua, nb_um = _process_flaws(flaws, pos_by_key, nb_margin)
            nb_au = sum(_process_flaws(flaws, pos_by_key, nb_margin)[1].values())
            nb_mu = sum(_process_flaws(flaws, pos_by_key, nb_margin)[4].values())
            neighbourhood_rows.append(
                f"| {nb_margin} | {nb_au} ({_pct(nb_au, nb_ua)}) | {nb_mu} ({_pct(nb_mu, nb_um)}) |"
            )

    report_path = _write_ab_report(
        margin=margin,
        user_id=user_id,
        total_flaws=len(flaws),
        allowed_ungated=au,
        allowed_suppressed=as_,
        allowed_survived=av,
        missed_ungated=mu,
        missed_suppressed=ms,
        missed_survived=mv,
        depth_ua=depth_ua,
        depth_ga=depth_ga,
        depth_um=depth_um,
        depth_gm=depth_gm,
        dropped_cases=dropped_cases,
        neighbourhood_rows=neighbourhood_rows,
        report_dir=report_dir,
    )

    return AbResult(
        ungated_count_allowed=ungated_allowed,
        gated_count_allowed=sum(av.values()),
        ungated_count_missed=ungated_missed,
        gated_count_missed=sum(mv.values()),
        dropped_cases=dropped_cases,
        report_path=report_path,
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Engine-free A/B gate-validation harness: loads user-28 stored blobs once, "
            "runs tactic detection twice (ungated vs gated), emits per-motif counts + "
            "dropped-case list with local analysis-board links. Read-only, zero DB writes."
        )
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        default="dev",
        help="DB target (default: dev).",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=DEFAULT_USER_ID,
        dest="user_id",
        help=f"User ID to validate (default: {DEFAULT_USER_ID}; dev-28 only per D-01a).",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=ONLY_MOVE_WIN_PROB_MARGIN,
        help=(
            f"Forcing-line gate win-prob margin (default: {ONLY_MOVE_WIN_PROB_MARGIN}). "
            "Larger value suppresses more tags."
        ),
    )
    parser.add_argument(
        "--neighbourhood",
        action="store_true",
        help="Also report suppression at 0.30 and 0.40 for context (D-03).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    db_target: Literal["dev", "benchmark", "prod"] = args.db
    result = asyncio.run(
        run_ab_validation(
            db=db_target,
            user_id=args.user_id,
            margin=args.margin,
            neighbourhood=args.neighbourhood,
        )
    )
    print(f"Report written to: {result.report_path}")
    print(f"Ungated: allowed={result.ungated_count_allowed}, missed={result.ungated_count_missed}")
    print(f"Gated:   allowed={result.gated_count_allowed}, missed={result.gated_count_missed}")
    print(f"Dropped cases: {len(result.dropped_cases)}")
