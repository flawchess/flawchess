"""Endpoints for the remote eval worker protocol (Phase 120 SEED-048).

POST /eval/remote/lease  — claim one tier-3 game and return its (ply, FEN) positions.
POST /eval/remote/submit — apply a batch of engine evals server-side via the SEED-044
                           write path, enforcing D-5 SF-version gate and SEED-045
                           bounded-retry stamping.

Both endpoints require the X-Operator-Token header (T-120-01 operator auth gate).
403 when the token is not configured on the server (fail-closed); 401 when it does
not match. Token comparison is constant-time (hmac.compare_digest — no timing oracle).

Expected / non-exception status codes (do NOT Sentry-capture):
  403 — token not configured
  401 — wrong token
  204 — empty queue (lease) or lichess game deferred (lease)
  422 — SF version mismatch (submit)
  404 — game not found (submit)

The server owns ALL storage convention (D-2): workers are dumb FEN→eval functions.
The submit endpoint calls _apply_full_eval_results with the worker's ply-keyed evals;
the SEED-044 +1 post-move shift is applied there, not by the worker.
"""

import hmac
import io
from datetime import datetime, timezone
from typing import Annotated

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select, update
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.schemas.eval_remote import (
    LeasePosition,
    LeaseResponse,
    SubmitRequest,
    SubmitResponse,
)
from app.services.eval_drain import (
    MAX_EVAL_ATTEMPTS,
    _apply_full_eval_results,
    _classify_and_fill_oracle,
    _collect_full_ply_targets,
    _mark_full_evals_completed,
    _mark_full_pv_completed,
    _signal_flaw_completion,
)
from app.services.eval_queue_service import _claim_tier3_derived

router = APIRouter(prefix="/eval/remote", tags=["eval-remote"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def require_operator_token(
    x_operator_token: Annotated[str | None, Header(alias="X-Operator-Token")] = None,
) -> None:
    """Validate the operator token (T-120-01).

    Fail-closed: if no token is configured on the server, return 403 so the
    endpoint is unreachable even without an attacker knowing the token.
    Missing header also returns 403 (the server is not configured — do not
    leak whether the issue is missing configuration or missing client token).
    Uses hmac.compare_digest for constant-time comparison (no timing oracle).
    Token is never logged.
    """
    configured = settings.EVAL_OPERATOR_TOKEN
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator token not configured on server",
        )
    # Missing header OR wrong token → 401. We check for None after the
    # fail-closed config gate so a missing header with no server config
    # returns 403 (server not configured), not 401 (access denied).
    # Compare UTF-8 bytes, not str: hmac.compare_digest raises TypeError on
    # non-ASCII str operands, so a header with any non-ASCII byte would surface
    # as an uncaught 500 (and Sentry-spam) instead of the intended 401. Bytes
    # keep the comparison constant-time over the byte length with no ASCII limit.
    supplied = (x_operator_token or "").encode("utf-8")
    if x_operator_token is None or not hmac.compare_digest(configured.encode("utf-8"), supplied):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator token",
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_lease_positions(
    game_id: int,
    pgn_text: str,
    gp_rows: list[tuple[int, int, int | None, int | None]],
) -> list[LeasePosition] | None:
    """Collect per-ply FEN positions from a game's PGN for the lease response.

    Replays the PGN once to build a ply->board.fen() map, then merges with the
    target list from _collect_full_ply_targets (include_terminal=True so the last
    played ply's after-eval can be resolved at submit time — SEED-044 pitfall 3).

    Returns None on PGN parse failure (caller should return 204 — treat as no game).
    Returns a list of LeasePosition (may include an is_terminal=True entry).
    """
    targets = _collect_full_ply_targets(
        game_id=game_id,
        pgn_text=pgn_text,
        game_positions_rows=gp_rows,
        include_terminal=True,
    )
    if not targets:
        return None

    # Replay PGN to build ply -> FEN map (board.fen() = full FEN with turn/castling/ep).
    # Pre-push board at ply N is the position BEFORE the move at ply N — the correct
    # eval target position. The terminal position is the board AFTER the last push.
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None

    fen_by_ply: dict[int, str] = {}
    board = game.board()
    for ply, node in enumerate(game.mainline()):
        fen_by_ply[ply] = board.fen()  # pre-push board = position at ply
        board.push(node.move)
    # Terminal position: the board after the last push.
    terminal_ply = len(fen_by_ply)
    fen_by_ply[terminal_ply] = board.fen()

    positions: list[LeasePosition] = []
    for t in targets:
        fen = fen_by_ply.get(t.ply)
        if fen is None:
            continue
        positions.append(LeasePosition(ply=t.ply, fen=fen, is_terminal=t.is_terminal))

    return positions if positions else None


async def _apply_submit(
    game_id: int,
    body: SubmitRequest,
) -> SubmitResponse:
    """Apply a submit payload using the SEED-044 write path + SEED-045 decision tree.

    Read phase (short session, closed before write): load Game fields + GamePosition rows.
    Write phase (ONE late session): apply evals, classify flaws, stamp or retry.
    Mirrors _full_drain_tick Steps 2-4 (eval_drain.py lines ~1431-1519).

    Does NOT use asyncio.gather inside any open session (CLAUDE.md hard rule).
    """
    # ── Read phase — short session, close before write ────────────────────────
    async with async_session_maker() as read_session:
        game_result = await read_session.execute(select(Game).where(Game.id == game_id))
        game = game_result.unique().scalar_one_or_none()
        if game is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        pgn_text: str = game.pgn
        current_attempts: int = game.full_eval_attempts
        is_lichess_eval_game: bool = game.lichess_evals_at is not None
        # Authoritative owner for the post-commit cache signal — derived from the
        # game itself, NOT the worker payload. Trusting a client-supplied user_id
        # here (WR-04) would invalidate the wrong user's cache and leave the real
        # owner's analysis stale while signalling an unrelated user.
        owner_id: int = game.user_id

        gp_result = await read_session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(
                GamePosition.game_id == game_id,
                GamePosition.user_id == game.user_id,
            )
        )
        gp_rows: list[tuple[int, int, int | None, int | None]] = [
            (row.ply, row.full_hash, row.eval_cp, row.eval_mate) for row in gp_result.all()
        ]
    # read_session closed — no sessions open during CPU work below

    # Derive targets and build the engine_result_map from submitted evals.
    # Worker evals are position-keyed (no shift) — the server applies the +1 shift
    # inside _apply_full_eval_results via _post_move_eval (D-2 / pitfall 1).
    targets = _collect_full_ply_targets(
        game_id=game_id,
        pgn_text=pgn_text,
        game_positions_rows=gp_rows,
        include_terminal=not is_lichess_eval_game,
    )

    # Worker supplies (eval_cp, eval_mate, best_move, pv) keyed by position ply.
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {
        e.ply: (e.eval_cp, e.eval_mate, e.best_move, e.pv) for e in body.evals
    }

    # ── Write phase — ONE late session, all UPDATEs + commit atomic ──────────
    stamp_complete: bool
    failed_ply_count: int

    async with async_session_maker() as write_session:
        # dedup_map is empty {} — no cross-user dedup for remote submissions;
        # the worker already evaluated all positions (D-2: no dedup needed).
        failed_ply_count = await _apply_full_eval_results(
            write_session, targets, {}, engine_result_map, is_lichess_eval_game
        )

        # Classify game_flaws + fill oracle counts + write flaw PVs.
        # Runs AFTER _apply_full_eval_results so eval_cp is visible for classification.
        # Runs BEFORE completion markers so evals + flaws commit atomically (T-117-11).
        await _classify_and_fill_oracle(write_session, game_id, engine_result_map)

        new_attempts = current_attempts + 1
        games_table = Game.__table__

        if failed_ply_count == 0:
            # Path A: no holes — stamp both markers complete.
            await _mark_full_evals_completed(write_session, game_id)
            await _mark_full_pv_completed(write_session, game_id)
            stamp_complete = True

        elif new_attempts < MAX_EVAL_ATTEMPTS:
            # Path B: holes remain, under cap — increment attempts, leave pending.
            # Do NOT stamp full_evals_completed_at or full_pv_completed_at.
            await write_session.execute(
                update(games_table)  # ty: ignore[invalid-argument-type]
                .where(games_table.c.id == game_id)
                .values(full_eval_attempts=new_attempts)
            )
            stamp_complete = False

        else:
            # Path C: holes remain AND cap reached — stamp anyway (D-116-07 no-loop
            # invariant). One aggregated Sentry warning (never embed variable data in
            # the message string — use set_context for Sentry grouping, CLAUDE.md rule).
            await _mark_full_evals_completed(write_session, game_id)
            await _mark_full_pv_completed(write_session, game_id)
            sentry_sdk.set_context(
                "eval",
                {
                    "game_id": game_id,
                    "hole_count": failed_ply_count,
                    "attempts": new_attempts,
                },
            )
            sentry_sdk.set_tag("source", "remote_eval_worker")
            sentry_sdk.capture_message(
                "remote-worker: stamping complete after MAX_EVAL_ATTEMPTS with residual holes",
                level="warning",
            )
            stamp_complete = True

        await write_session.commit()

    # Signal after commit so the hook never fires for a partially-committed game.
    if stamp_complete:
        _signal_flaw_completion(owner_id)

    return SubmitResponse(
        game_id=game_id,
        stamp_complete=stamp_complete,
        failed_ply_count=failed_ply_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/lease", response_model=None)
async def lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
) -> Response | LeaseResponse:
    """Claim one tier-3 game and return its unanalyzed (ply, FEN) positions.

    Returns 204 when no eligible game is in the queue, or when the claimed game
    is a lichess-eval game (PV-backfill path deferred to v2 per D-4/v1 scope).

    Calls _claim_tier3_derived() directly — bypasses EVAL_AUTO_DRAIN_ENABLED gate
    (pitfall 2: that gate is for the background idle loop, not explicit requests).

    The terminal eval-donor (is_terminal=True) is always included (pitfall 3):
    without it, the last played ply's eval_cp stays NULL after submit.
    """
    async with async_session_maker() as read_session:
        claim = await _claim_tier3_derived(read_session)
    # read_session closed

    if claim is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    game_id, user_id, is_lichess_eval_game = claim

    # D-4 / v1 scope: lichess PV-backfill games (is_lichess_eval_game=True) deferred.
    if is_lichess_eval_game:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Load PGN + game_positions in a second short read session.
    async with async_session_maker() as read_session:
        game_result = await read_session.execute(
            sa.select(Game.pgn, Game.user_id).where(Game.id == game_id)
        )
        row = game_result.one_or_none()
        if row is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        pgn_text: str = row.pgn

        gp_result = await read_session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(
                GamePosition.game_id == game_id,
                GamePosition.user_id == row.user_id,
            )
        )
        gp_rows: list[tuple[int, int, int | None, int | None]] = [
            (r.ply, r.full_hash, r.eval_cp, r.eval_mate) for r in gp_result.all()
        ]
    # read_session closed

    positions = _build_lease_positions(game_id, pgn_text, gp_rows)
    if positions is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return LeaseResponse(
        game_id=game_id,
        user_id=user_id,
        is_lichess_eval_game=False,
        positions=positions,
        leased_at=datetime.now(timezone.utc),
    )


@router.post("/submit", response_model=SubmitResponse)
async def submit_eval(
    body: SubmitRequest,
    _auth: Annotated[None, Depends(require_operator_token)],
) -> SubmitResponse:
    """Apply a batch of engine evals to one game using the SEED-044 write path.

    D-5 SF-version gate is checked FIRST: if EXPECTED_SF_VERSION is configured
    and body.sf_version does not match, 422 is raised before any DB access.

    Server applies the SEED-044 +1 post-move shift via _apply_full_eval_results —
    the worker submits position-keyed evals as-is (D-2 storage responsibility).
    Duplicate submits for the same game are idempotent (ON CONFLICT DO NOTHING for
    flaws, idempotent oracle UPDATE, completion markers set to the same timestamp).
    """
    # D-5 gate FIRST — check before any DB access.
    if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION:
        # Static detail string for Sentry grouping — never embed version values
        # directly (fragments Sentry issues per CLAUDE.md rule).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stockfish version mismatch",
        )

    return await _apply_submit(
        game_id=body.game_id,
        body=body,
    )
