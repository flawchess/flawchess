"""Endpoints for the remote eval worker protocol (Phase 120 SEED-048).

POST /eval/remote/lease        — claim the next eval game (tier-1 > tier-2 > tier-3) and
                                 return its (ply, FEN) positions (Phase 121 SEED-048).
                                 Optional scope param (Phase 123 D-05): absent = bundled;
                                 scope=explicit = tier-1/2 only; scope=idle = tier-3 only.
POST /eval/remote/submit       — apply a batch of engine evals server-side via the SEED-044
                                 write path, enforcing D-5 SF-version gate and SEED-045
                                 bounded-retry stamping.
POST /eval/remote/entry-lease  — (Phase 123 SEED-051 D-07) claim a batch of pending
                                 entry-ply (import-time) games. D-5 backlog existence probe
                                 gates this endpoint; returns 204 when backlog < threshold.
POST /eval/remote/entry-submit — (Phase 123 SEED-051 D-07) apply depth-15 entry-ply evals
                                 via the no-shift SEED-044 write path (_apply_eval_results).

All endpoints require the X-Operator-Token header (T-120-01 operator auth gate).
403 when the token is not configured on the server (fail-closed); 401 when it does
not match. Token comparison is constant-time (hmac.compare_digest — no timing oracle).

Expected / non-exception status codes (do NOT Sentry-capture):
  403 — token not configured
  401 — wrong token
  204 — empty queue (lease) or lichess game deferred (lease) or shallow backlog (entry-lease)
  422 — SF version mismatch (submit / entry-submit)
  404 — game not found (submit)

The server owns ALL storage convention (D-2): workers are dumb FEN→eval functions.
The submit endpoint calls _apply_full_eval_results with the worker's ply-keyed evals;
the SEED-044 +1 post-move shift is applied there, not by the worker.
The entry-submit endpoint calls _apply_eval_results (no shift) — entry-ply targets are
already position-keyed at the correct row; do NOT use _apply_full_eval_results.
"""

import hmac
import io
from datetime import datetime, timezone
from typing import Annotated, Literal

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select, update
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.schemas.eval_remote import (
    EntryLeasePosition,
    EntryLeaseResponse,
    EntrySubmitRequest,
    EntrySubmitResponse,
    FlawBlobLeaseResponse,
    FlawBlobSubmitRequest,
    FlawBlobSubmitResponse,
    LeasePosition,
    LeaseResponse,
    SubmitRequest,
    SubmitResponse,
)
from app.services.eval_drain import (
    ENTRY_LEASE_BACKLOG_THRESHOLD,
    ENTRY_LEASE_BATCH_SIZE,
    ENTRY_LEASE_TTL_SECONDS,
    MAX_EVAL_ATTEMPTS,
    _EvalTarget,
    _apply_eval_results,
    _apply_full_eval_results,
    _assemble_flaw_blobs_from_submit,
    _batch_update_flaw_pv_lines,
    _build_flaw_blob_lease_positions,
    _build_flaw_multipv2_blobs,
    _claim_entry_eval_games,
    _classify_and_fill_oracle,
    _classify_and_insert_flaws,
    _collect_eval_targets_from_db,
    _collect_full_ply_targets,
    _load_pgns_for_games,
    _mark_evals_completed,
    _mark_full_evals_completed,
    _mark_full_pv_completed,
    _parse_token,
    _run_multipv2_pass,
    _signal_flaw_completion,
)
from app.models.eval_jobs import EvalJob
from app.models.game_flaw import GameFlaw
from app.repositories.game_flaws_repository import bulk_update_tactic_tags
from app.services.eval_queue_service import _claim_tier4_blob, claim_eval_job, release_job
from app.services.flaws_service import _classify_tactic_gated, _recompute_fen_map

# Worker identity for the remote eval worker — distinct from WORKER_ID_SERVER_POOL
# ("server-pool") so the eval_jobs.leased_by column is traceable per worker type.
_WORKER_ID_REMOTE: str = "remote-worker"

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
    # Phase 142 MPV-02: parallel second-best map (D-03 inline fields, not a parallel list).
    # Only includes rows where the worker provided second-best data; empty when old worker
    # omits fields (all three default None → condition is False → map stays empty → D-04).
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {
        e.ply: (e.second_cp, e.second_mate, e.second_uci)
        for e in body.evals
        if e.second_cp is not None or e.second_uci is not None
    }

    # Phase 142 MPV-02: build PvNode blobs from second-best data (CPU/engine region —
    # no session open here; CLAUDE.md hard rule). Passes dedup_map={} because the remote
    # path has no cross-user dedup (worker already evaluated all positions).
    # Guard: skip when second_best_map is empty (D-04 — old worker omits all second_*
    # fields → leave blobs NULL; Phase 145 backfills the gap). Only upgraded workers
    # providing at least one second-best ply trigger blob assembly.
    if second_best_map:
        blob_map = await _build_flaw_multipv2_blobs(
            game_id, targets, {}, engine_result_map, second_best_map
        )
    else:
        blob_map = {}

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
        # Bug fix (SHIP-02): pass blob_map so the forcing-line gate filters tactic tags.
        # Before this fix, blobs were written via _run_multipv2_pass but
        # _classify_and_fill_oracle was called without blob_map, leaving new-game tactic
        # tags unfiltered even when second-best data was available. blob_map if blob_map
        # degrades an empty dict (old worker, no second-best) to None → gate skipped →
        # old-worker backward-compat preserved.
        await _classify_and_fill_oracle(
            write_session, game_id, engine_result_map, blob_map if blob_map else None
        )

        # Phase 142 MPV-02: write allowed_pv_lines / missed_pv_lines JSONB blobs.
        # Runs AFTER _classify_and_fill_oracle so flaw rows exist for the UPDATE.
        # Same transaction = atomic with flaw rows (Pitfall 5 / T-142-03-04).
        # No-op when blob_map is empty (old worker omitted second-best — D-04).
        await _run_multipv2_pass(write_session, game_id, blob_map)

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

        # Stamp eval_jobs for tier-1/tier-2 claims when all plies resolved (Path A/C).
        # The WHERE status='leased' guard makes a late submit (lease expired + re-claimed,
        # or job already completed) a safe no-op — never corrupts an unrelated job.
        # Path B (holes remain, stamp_complete=False) is deliberately NOT stamped:
        # the eval_jobs row stays 'leased' until the sweep requeues it after the TTL.
        if body.job_id is not None and stamp_complete:
            jobs_table = EvalJob.__table__
            now_ts = datetime.now(timezone.utc)
            await write_session.execute(
                update(jobs_table)  # ty: ignore[invalid-argument-type]
                .where(
                    jobs_table.c.id == body.job_id,
                    jobs_table.c.status == "leased",  # idempotency / late-submit guard
                )
                .values(status="completed", completed_at=now_ts)
            )

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
# Worker-id advisory dependency (D-10)
# ---------------------------------------------------------------------------


async def worker_id_label(
    x_worker_id: Annotated[str | None, Header(alias="X-Worker-Id")] = None,
) -> str:
    """Extract the advisory worker identity from X-Worker-Id header (D-10).

    Used for both eval_jobs.leased_by (full-ply) and games.entry_eval_leased_by.
    Advisory ONLY — never used for authz or ownership (T-123-03).
    Absent header (old workers) → fall back to _WORKER_ID_REMOTE ("remote-worker").
    """
    label = x_worker_id or _WORKER_ID_REMOTE
    # WR-01 (Phase 123): games.entry_eval_leased_by is VARCHAR(16). An X-Worker-Id
    # header longer than 16 chars would overflow the column on entry-lease, raising a
    # PostgreSQL StringDataRightTruncation → unhandled 500 (the worker's own < 10-char
    # validation is not authoritative server-side). Truncate here so a long header can
    # never surface as a 500. The full-ply path's eval_jobs.leased_by is VARCHAR(100),
    # so truncating to 16 is safe for both write sites.
    return label[:16]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/lease", response_model=None)
async def lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
    scope: Annotated[Literal["explicit", "idle"] | None, Query()] = None,
) -> Response | LeaseResponse:
    """Claim the next eval game (tier-1 > tier-2 > tier-3) and return its FEN positions.

    Returns 204 when no eligible game is in the queue, or when the claimed game
    is a lichess-eval game (PV-backfill path deferred to v2 per D-4/v1 scope).

    Delegates to claim_eval_job which implements tier-1 > tier-2 > tier-3 priority
    with SKIP LOCKED and stale-lease sweep. claim_eval_job opens its own sessions
    internally — do NOT wrap this call in a session context (Pitfall 1).

    D-05 scope param (Phase 123):
      absent   → today's bundled tier-1>2>3 (backward-compat for un-updated workers).
      explicit → tier-1/2 only.
      idle     → tier-3 only.

    The EVAL_AUTO_DRAIN_ENABLED gate inside claim_eval_job applies only to tier-3
    (idle backlog). Tier-1/tier-2 picks are never gated — a freshly-enqueued
    explicit request must always be claimable by the remote worker.

    The lease response carries job_id = eval_jobs.id for tier-1/tier-2 claims,
    and job_id=None for tier-3 derived picks (no eval_jobs row exists).

    The terminal eval-donor (is_terminal=True) is always included (pitfall 3):
    without it, the last played ply's eval_cp stays NULL after submit.
    """
    # claim_eval_job owns its sessions — no caller session context needed.
    claim = await claim_eval_job(worker_id=worker_id, scope=scope)

    if claim is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    game_id = claim.game_id
    user_id = claim.user_id
    is_lichess_eval_game = claim.is_lichess_eval_game

    # D-4 / v1 scope: lichess PV-backfill games (is_lichess_eval_game=True) deferred.
    # WR-01 (Phase 121): claim_eval_job leased the eval_jobs row before we discovered
    # it's a lichess game we don't process. Release it back to 'pending' so the server
    # pool (which DOES do the flaw-PV backfill) can claim it immediately, instead of
    # leaving it stranded 'leased' for the full lease TTL. Tier-3 derived picks have
    # job_id=None and own no eval_jobs row, so the guard skips them.
    if is_lichess_eval_game:
        if claim.job_id is not None:
            await release_job(claim.job_id)
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
        job_id=claim.job_id,
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


@router.post("/entry-lease", response_model=None)
async def entry_lease_eval_games(
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
) -> Response | EntryLeaseResponse:
    """Claim a batch of pending entry-ply (import-time) games and return their FENs.

    D-5 backlog existence probe runs FIRST (D-02: remote-lease-only; server pool
    always drains regardless of backlog depth). If backlog < ENTRY_LEASE_BACKLOG_THRESHOLD
    → 204 (worker falls to scope=idle). OFFSET = THRESHOLD-1 (0-indexed; Pitfall 6).

    The server derives {game_id, ply, fen}[] via _collect_eval_targets_from_db +
    target.board.fen() so the worker stays a dumb depth-15 FEN→eval node (D-2).

    Claim commits before returning — the lease is durable before the worker begins
    evaluation. Entry-submit stamps evals_completed_at (permanent lease release).
    """
    # ── D-5 backlog existence probe FIRST ────────────────────────────────────
    # OFFSET = THRESHOLD - 1 (Pitfall 6: 300th row is at offset 299, 0-indexed).
    # Bind as :param — never f-string (project Security rule / T-123-02).
    async with async_session_maker() as probe_session:
        # WR-03 (Phase 123): the probe predicate MUST match _claim_entry_eval_games'
        # claim predicate (NULL or expired lease). Counting leased rows here would let
        # the probe pass while the claim returns [] (all available rows leased by other
        # workers), wasting a claim transaction per cycle near the tail. Keeping the two
        # predicates in lock-step prevents that drift.
        probe = await probe_session.execute(
            sa.text("""
                SELECT 1 FROM games
                WHERE evals_completed_at IS NULL
                  AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
                ORDER BY id DESC
                LIMIT 1 OFFSET :offset
            """),
            {"offset": ENTRY_LEASE_BACKLOG_THRESHOLD - 1},
        )
        backlog_deep_enough = probe.scalar_one_or_none() is not None
    # probe_session closed

    if not backlog_deep_enough:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # ── Claim a batch of pending games ────────────────────────────────────────
    async with async_session_maker() as claim_session:
        game_ids = await _claim_entry_eval_games(
            claim_session, worker_id, ENTRY_LEASE_BATCH_SIZE, ENTRY_LEASE_TTL_SECONDS
        )
        await claim_session.commit()
    # claim_session committed — lease is durable before FEN derivation

    if not game_ids:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # ── Derive {game_id, ply, fen}[] server-side (D-2) ───────────────────────
    # Worker never parses PGN; server ships FENs from the canonical derivation path.
    game_pgn_rows = await _load_pgns_for_games(game_ids)
    pgn_map = {gid: pgn for gid, pgn in game_pgn_rows}

    async with async_session_maker() as read_session:
        eval_targets = await _collect_eval_targets_from_db(read_session, game_ids, pgn_map)
    # read_session closed

    positions: list[EntryLeasePosition] = [
        EntryLeasePosition(
            game_id=t.game_id,
            ply=t.ply,
            fen=t.board.fen(),  # pre-push board snapshot at the target ply
        )
        for t in eval_targets
    ]

    return EntryLeaseResponse(
        positions=positions,
        leased_at=datetime.now(timezone.utc),
    )


@router.post("/entry-submit", response_model=EntrySubmitResponse)
async def entry_submit_eval(
    body: EntrySubmitRequest,
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
) -> EntrySubmitResponse:
    """Apply depth-15 entry-ply evals via the no-shift SEED-044 write path.

    CRITICAL: uses _apply_eval_results (no +1 shift), NOT _apply_full_eval_results.
    Entry-ply targets are already position-keyed at the correct row; applying the
    full-ply +1 shift would corrupt the midgame/endgame-span-entry evals (Pitfall 1).

    The server re-derives _EvalTarget objects from each game_id so ply/endgame_class
    stay server-controlled (T-123-04). The worker payload can only set eval_cp/eval_mate
    for the plies the server originally chose. Idempotent (ON CONFLICT DO NOTHING for
    flaws, re-stamp is harmless).
    """
    # D-5 SF-version gate FIRST (T-123-07) — copy from /submit, check before DB access.
    if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stockfish version mismatch",
        )

    # Group submitted evals by game_id for per-game re-derivation.
    evals_by_game: dict[int, dict[int, tuple[int | None, int | None]]] = {}
    for e in body.evals:
        evals_by_game.setdefault(e.game_id, {})[e.ply] = (e.eval_cp, e.eval_mate)

    # CR-01 (Phase 123): stamp the FULL set of games leased to THIS worker that are
    # still pending — NOT just the games that came back with evals. A leased game can
    # yield zero eval targets at drain time (e.g. an unreachable target ply silently
    # dropped by _snapshot_boards), so it never appears in body.evals. If we only
    # stamped submitted games, those zero-target games would stay pending, get
    # re-leased every TTL cycle, and livelock forever. The in-process server pool
    # avoids this by stamping every claimed game regardless of target count (D-09 /
    # R-02); this mirrors that invariant. Lease ownership (entry_eval_leased_by ==
    # worker_id) is the same advisory worker identity the worker sent on /entry-lease.
    async with async_session_maker() as guard_session:
        leased_game_ids: list[int] = list(
            (
                await guard_session.execute(
                    select(Game.id).where(
                        Game.entry_eval_leased_by == worker_id,
                        Game.evals_completed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
    # guard_session closed
    leased_set = set(leased_game_ids)

    # WR-02 (Phase 123): only classify/apply evals for games this worker actually
    # holds a live lease on. A buggy or out-of-sync worker could submit a stale or
    # wrong game_id; without this filter the server would re-derive, classify, and
    # stamp an unrelated game. The operator is trusted (not an authz hole), but the
    # submit body does not prove a game was ever leased, so we ignore non-leased ids.
    game_ids_submitted = [gid for gid in evals_by_game if gid in leased_set]

    if not leased_game_ids:
        return EntrySubmitResponse(game_ids=[], stamped_count=0)

    # ── Re-derive _EvalTargets server-side (server controls ply/endgame_class) ──
    # Only for the games whose evals we will actually apply (lease-owned + submitted).
    eval_targets: list[_EvalTarget] = []
    eval_results: list[tuple[int | None, int | None]] = []
    if game_ids_submitted:
        game_pgn_rows = await _load_pgns_for_games(game_ids_submitted)
        pgn_map = {gid: pgn for gid, pgn in game_pgn_rows}

        async with async_session_maker() as read_session:
            eval_targets = await _collect_eval_targets_from_db(
                read_session, game_ids_submitted, pgn_map
            )
        # read_session closed

        # Zip the worker's submitted evals onto the re-derived targets by (game_id, ply).
        # Targets without a matching submitted eval get (None, None) → skipped in
        # _apply_eval_results.
        for t in eval_targets:
            game_evals = evals_by_game.get(t.game_id, {})
            eval_results.append(game_evals.get(t.ply, (None, None)))

    # ── Write phase (ONE session): apply → classify → stamp ──────────────────
    stamped_count = 0
    try:
        async with async_session_maker() as write_session:
            # _apply_eval_results: NO +1 shift — entry-ply positions are already at the
            # correct row (Pitfall 1: do NOT use _apply_full_eval_results here).
            if eval_targets:
                await _apply_eval_results(write_session, eval_targets, eval_results)

            # Classify game_flaws AFTER _apply_eval_results (eval_cp must be visible)
            # and BEFORE _mark_evals_completed (atomicity guard). Only games we applied
            # evals for need (re-)classification.
            if game_ids_submitted:
                await _classify_and_insert_flaws(write_session, game_ids_submitted)

            # CR-01: stamp evals_completed_at = now() for the FULL leased set (permanent
            # lease release per D-01) — including zero-target games that never appeared
            # in body.evals. The queue predicate (evals_completed_at IS NULL) stops
            # matching immediately, breaking the re-lease livelock.
            await _mark_evals_completed(write_session, leased_game_ids)
            stamped_count = len(leased_game_ids)
            await write_session.commit()
    except Exception as exc:
        # Capture non-trivial exceptions (Sentry rule: never embed variables in message).
        # IN-01: report the actual lease owner, not a static "entry-submit" literal.
        sentry_sdk.set_context(
            "entry_submit",
            {"game_ids": leased_game_ids, "worker_id": worker_id},
        )
        sentry_sdk.set_tag("source", "remote_eval_worker")
        sentry_sdk.capture_exception(exc)
        # WR-04 (Phase 123): best-effort release the leases so the games are reclaimable
        # immediately, rather than stalling for the full TTL. The full-ply path releases
        # explicitly via release_job for the same reason; mirror that "release now, don't
        # wait for TTL" design here. Done in its own session so the failed write_session
        # rollback does not swallow the release.
        try:
            async with async_session_maker() as rel_session:
                await rel_session.execute(
                    update(Game.__table__)  # ty: ignore[invalid-argument-type]
                    .where(Game.__table__.c.id.in_(leased_game_ids))
                    .values(entry_eval_lease_expiry=None, entry_eval_leased_by=None)
                )
                await rel_session.commit()
        except Exception as rel_exc:
            sentry_sdk.capture_exception(rel_exc)
        raise

    return EntrySubmitResponse(
        game_ids=leased_game_ids,
        stamped_count=stamped_count,
    )


# ─── Phase 145 SHIP-01: flaw-blob-only lease endpoint (D-04) ─────────────────


@router.post("/flaw-blob-lease", response_model=None)
async def flaw_blob_lease(
    _auth: Annotated[None, Depends(require_operator_token)],
) -> Response | FlawBlobLeaseResponse:
    """Claim one tier-4-selected game's flaw-blob FENs for MultiPV=2 evaluation.

    Dedicated, isolated flaw-blob backfill endpoint (D-04). Does NOT reuse or touch
    the live _apply_submit path — see D-04 isolation boundary in the threat model.

    Flow:
    1. Call _claim_tier4_blob — random pick of one analyzed non-guest game with
       at least one NULL-blob flaw (allowed_pv_lines IS NULL). Returns 204 when the
       backfill queue is empty.
    2. Build lease via _build_flaw_blob_lease_positions — walks each flaw's two PV
       lines from stored game_positions.pv. Walkable lines (>= 2 PV nodes) become
       FlawBlobLeasePosition entries with token="{flaw_ply}:{line}:{node_k}". Lines
       with NULL pv or < 2-node walks are sentinels.
    3. All-sentinel games (zero walkable lines): write [] sentinel for all flaw plies
       via _batch_update_flaw_pv_lines and return 204. Sentinels clear the
       allowed_pv_lines IS NULL predicate so the game is never re-picked (T-145-07
       forward-progress guarantee — the lottery cannot loop on un-fillable games).
    4. Mixed or fully-walkable games: return FlawBlobLeaseResponse. The worker will
       evaluate the leased FENs at MultiPV=2 and submit via /flaw-blob-submit (Plan 04).
       Sentinel lines in mixed games are written at submit time (Plan 04 handler).

    Token format (D-04a): "{flaw_ply}:{line}:{node_k}" — opaque to worker. The worker
    echoes the token unchanged on submit; the server parses it to reassemble PvNode blobs.
    """
    # ── Tier-4 pick: open own session, close after pick ───────────────────────
    async with async_session_maker() as session:
        blob_pick = await _claim_tier4_blob(session)
    # session closed

    if blob_pick is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    game_id, _user_id = blob_pick

    # ── Build lease positions from stored PVs (no engine calls, no gather) ────
    lease_positions, sentinel_lines = await _build_flaw_blob_lease_positions(game_id)

    # All-sentinel: no walkable lines → write [] sentinels and return 204 (T-145-07).
    # This clears the allowed_pv_lines IS NULL predicate so the game is never re-picked.
    if not lease_positions:
        if sentinel_lines:
            # Build blob_map: {flaw_ply: ([], [])} for every sentinel flaw.
            # Both allowed and missed get [] because the worker won't fill them.
            sentinel_plies = {flaw_ply for flaw_ply, _line in sentinel_lines}
            sentinel_blob_map = {ply: ([], []) for ply in sentinel_plies}
            async with async_session_maker() as write_session:
                await _batch_update_flaw_pv_lines(write_session, game_id, sentinel_blob_map)
                await write_session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return FlawBlobLeaseResponse(
        game_id=game_id,
        positions=lease_positions,
        leased_at=datetime.now(timezone.utc),
    )


# ─── Phase 145 SHIP-01: flaw-blob submit helper + endpoint (D-04, D-07) ──────


async def _apply_flaw_blob_submit(
    game_id: int,
    body: FlawBlobSubmitRequest,
) -> FlawBlobSubmitResponse:
    """Apply a flaw-blob submit: reassemble PvNode blobs and run per-game gated retag (D-07).

    Isolated from _apply_submit (D-04): does not branch that handler, does not call
    _classify_and_fill_oracle, does not stamp full_evals_completed_at. Only the 8 tactic
    columns are updated (bulk_update_tactic_tags). No engine calls, no asyncio.gather.

    Flow:
    1. Read phase: load Game + all GamePosition rows + NULL-blob flaw plies.
    2. Idempotency gate: if no NULL-blob flaws remain → return blobs_written=0 (D-03).
    3. Re-derive lease (opens its own sessions inside _build_flaw_blob_lease_positions).
    4. Security: reject any submitted token not in the current lease (T-145-09).
    5. CPU phase: assemble blob_map, build fen_map, run _classify_tactic_gated per flaw.
    6. Write phase: _batch_update_flaw_pv_lines + bulk_update_tactic_tags + commit.
    """
    # ── Read phase ────────────────────────────────────────────────────────────
    async with async_session_maker() as read_session:
        game = await read_session.scalar(select(Game).where(Game.id == game_id))
        if game is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        positions_result = await read_session.execute(
            select(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.user_id == game.user_id)
            .order_by(GamePosition.ply)
        )
        positions = list(positions_result.scalars().all())

        null_plies_result = await read_session.execute(
            sa.select(GameFlaw.ply).where(
                GameFlaw.game_id == game_id,
                GameFlaw.allowed_pv_lines.is_(None),
            )
        )
        null_flaw_plies: set[int] = set(null_plies_result.scalars().all())
    # read_session closed

    # ── Idempotency gate: all blobs already written → no-op double-submit (D-03) ──
    if not null_flaw_plies:
        return FlawBlobSubmitResponse(game_id=game_id, blobs_written=0)

    # ── Re-derive lease for token validation and sentinel detection ───────────
    # _build_flaw_blob_lease_positions opens its own sessions (after our read_session
    # was closed) so the CLAUDE.md no-concurrent-session rule is satisfied.
    lease_positions, sentinel_lines = await _build_flaw_blob_lease_positions(game_id)
    valid_tokens: set[str] = {pos.token for pos in lease_positions}

    # Security T-145-09: reject tokens not issued in the current lease.
    # Workers only receive tokens for walkable PV nodes; sentinel-line tokens
    # were never emitted and must never be accepted as valid submissions.
    for e in body.evals:
        if e.token not in valid_tokens:
            try:
                flaw_ply, _line, _k = _parse_token(e.token)
                in_null_plies = flaw_ply in null_flaw_plies
            except ValueError:
                in_null_plies = False
            # A token for a flaw_ply that doesn't belong to this game's NULL-blob set
            # is definitively foreign — reject unconditionally.
            if not in_null_plies:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown or foreign token: {e.token!r}",
                )
            # Token is for a NULL-blob flaw but not in the lease — it's a sentinel-line
            # token that was never leased to the worker. Reject it: workers must not
            # submit tokens the server never issued (T-145-09 tampering guard).
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown or foreign token: {e.token!r}",
            )

    # ── CPU phase: assemble blobs + classify ─────────────────────────────────
    blob_map = _assemble_flaw_blobs_from_submit(game_id, body.evals, sentinel_lines)
    fen_map = _recompute_fen_map(game.pgn)

    # D-07: per-game gated retag — only the 8 tactic columns; no severity/phase reclassification.
    updates: list[dict[str, object]] = []
    for flaw_ply in null_flaw_plies:
        blob_pair = blob_map.get(flaw_ply)
        allowed_blob = blob_pair[0] if blob_pair is not None else None
        missed_blob = blob_pair[1] if blob_pair is not None else None
        pre_flaw_eval_cp: int | None = (
            positions[flaw_ply - 1].eval_cp
            if flaw_ply >= 1 and flaw_ply - 1 < len(positions)
            else None
        )
        allowed_motif, allowed_piece, allowed_conf, allowed_depth = _classify_tactic_gated(
            flaw_ply, fen_map, positions, "allowed", allowed_blob, pre_flaw_eval_cp
        )
        missed_motif, missed_piece, missed_conf, missed_depth = _classify_tactic_gated(
            flaw_ply, fen_map, positions, "missed", missed_blob, pre_flaw_eval_cp
        )
        updates.append(
            {
                "user_id": game.user_id,
                "game_id": game_id,
                "ply": flaw_ply,
                "allowed_tactic_motif": allowed_motif,
                "allowed_tactic_piece": allowed_piece,
                "allowed_tactic_confidence": allowed_conf,
                "allowed_tactic_depth": allowed_depth,
                "missed_tactic_motif": missed_motif,
                "missed_tactic_piece": missed_piece,
                "missed_tactic_confidence": missed_conf,
                "missed_tactic_depth": missed_depth,
            }
        )

    # ── Write phase: blobs + tactic tags in one transaction ──────────────────
    async with async_session_maker() as write_session:
        await _batch_update_flaw_pv_lines(write_session, game_id, blob_map)
        await bulk_update_tactic_tags(write_session, updates)
        await write_session.commit()

    return FlawBlobSubmitResponse(game_id=game_id, blobs_written=len(blob_map))


@router.post("/flaw-blob-submit", response_model=FlawBlobSubmitResponse)
async def flaw_blob_submit(
    body: FlawBlobSubmitRequest,
    _auth: Annotated[None, Depends(require_operator_token)],
) -> FlawBlobSubmitResponse:
    """Apply worker MultiPV=2 results: write PvNode blobs and run per-game gated retag (D-07).

    Dedicated, isolated submit endpoint for the flaw-blob backfill (D-04). Does NOT
    call _apply_submit or _classify_and_fill_oracle — isolation from the live eval
    ingest path is enforced by the dedicated schema and separate handler logic.

    Flow (see _apply_flaw_blob_submit for details):
    1. Validates every token against the server-issued lease (T-145-09 foreign-token guard).
    2. Assembles PvNode blobs from worker results; writes sentinel [] for NULL-PV lines (D-06).
    3. Runs _classify_tactic_gated per flaw using the in-memory blob_map (no extra DB round-trip).
    4. Updates only the 8 tactic columns via bulk_update_tactic_tags (D-07 rolling rollout).
    5. Returns FlawBlobSubmitResponse(game_id, blobs_written) where blobs_written counts flaw
       rows updated (real blobs + sentinels []).

    A re-submit after all blobs are written is write-idempotent: returns blobs_written=0 (D-03).

    Expected status codes (do NOT Sentry-capture):
      404 — game not found
      422 — SF version mismatch or foreign/unknown token (T-145-09)
    """
    # D-5 SF-version gate (same as /submit and /entry-submit — T-145-05b).
    if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stockfish version mismatch",
        )
    return await _apply_flaw_blob_submit(body.game_id, body)
