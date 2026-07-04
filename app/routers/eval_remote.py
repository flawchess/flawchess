"""Endpoints for the remote eval worker protocol (Phase 120 SEED-048).

Phase 149-03 PRUNE-01: the original Gen-1 POST /lease + POST /submit pair (and
_apply_submit) has been deleted — the fleet fully migrated to the atomic
(versioned) /atomic-lease + /atomic-submit pair below (Phase 147 SEED-074 Part
B), which closes the ungated-tag window the Gen-1 pair left open. See
149-RESEARCH.md for the deletion's Runtime State Inventory / zero-legacy-
traffic verification.

POST /eval/remote/entry-lease  — (Phase 123 SEED-051 D-07) claim a batch of pending
                                 entry-ply (import-time) games. D-5 backlog existence probe
                                 gates this endpoint; returns 204 when backlog < threshold.
POST /eval/remote/entry-submit — (Phase 123 SEED-051 D-07) apply depth-15 entry-ply evals
                                 via the no-shift SEED-044 write path (_apply_eval_results).
POST /eval/remote/atomic-lease — (Phase 147 SEED-074 Part B, D-02) versioned lease for the
                                 eval+blob worker pipeline. Claims via claim_eval_job
                                 (tier-1 > tier-2 > tier-3), returns the FEN-per-ply shape
                                 (_build_lease_positions, shared with the deleted Gen-1 /lease).
POST /eval/remote/atomic-submit — (Phase 147 SEED-074 Part B, D-01/D-02) paired with
                                 /atomic-lease. Applies full-ply evals + the worker's own
                                 MultiPV-2 continuation blobs together, in ONE write_session:
                                 evals -> server-authoritative classify_game_flaws (with the
                                 worker's blobs as gate input only, never trusted for flaw
                                 membership) -> blob write -> SEED-045 bounded-retry stamping
                                 (same Path A/B/C invariant _apply_submit used to use, CR-01)
                                 -> one commit. No ungated window is ever observable for a
                                 game processed here (see _apply_atomic_submit).

All endpoints require the X-Operator-Token header (T-120-01 operator auth gate).
403 when the token is not configured on the server (fail-closed); 401 when it does
not match. Token comparison is constant-time (hmac.compare_digest — no timing oracle).

Expected / non-exception status codes (do NOT Sentry-capture):
  403 — token not configured
  401 — wrong token
  204 — empty queue (atomic-lease) or lichess game deferred (atomic-lease) or shallow
        backlog (entry-lease) or over-cap fat game (atomic-lease)
  422 — SF version mismatch (entry-submit / atomic-submit) or foreign/out-of-range
        blob token (flaw-blob-submit / atomic-submit)
  404 — game not found (atomic-submit)

The server owns ALL storage convention (D-2): workers are dumb FEN→eval functions.
The atomic-submit endpoint calls _apply_full_eval_results with the worker's ply-keyed
evals; the SEED-044 +1 post-move shift is applied there, not by the worker.
The entry-submit endpoint calls _apply_eval_results (no shift) — entry-ply targets are
already position-keyed at the correct row; do NOT use _apply_full_eval_results.
"""

import hmac
import io
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select, update
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import DEDUP_MAX_PLY, GamePosition
from app.schemas.eval_remote import (
    MAX_SUBMIT_EVALS,
    AtomicLeaseResponse,
    AtomicSubmitRequest,
    AtomicSubmitResponse,
    EntryLeasePosition,
    EntryLeaseResponse,
    EntrySubmitRequest,
    EntrySubmitResponse,
    FlawBlobLeaseResponse,
    FlawBlobSubmitRequest,
    FlawBlobSubmitResponse,
    LeasePosition,
)
from app.services.eval_drain import (
    ENTRY_LEASE_BACKLOG_THRESHOLD,
    ENTRY_LEASE_BATCH_SIZE,
    ENTRY_LEASE_TTL_SECONDS,
    MAX_EVAL_ATTEMPTS,
    _EvalTarget,
    _FullPlyEvalTarget,
    _apply_eval_results,
    _apply_full_eval_results,
    _assemble_flaw_blobs_from_submit,
    _batch_update_flaw_pv_lines,
    _build_flaw_blob_lease_positions,
    _claim_entry_eval_games,
    _classify_and_fill_oracle,
    _classify_and_insert_flaws,
    _collect_eval_targets_from_db,
    _collect_full_ply_targets,
    _derive_atomic_sentinel_lines,
    _fetch_dedup_evals,
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
from app.repositories.worker_heartbeat_repository import upsert_worker_heartbeat
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


async def _fetch_cached_opening_hashes(
    session: AsyncSession,
    gp_rows: list[tuple[int, int, int | None, int | None]],
) -> frozenset[int]:
    """SEED-076 (+follow-up): the game's opening full_hashes (ply <= DEDUP_MAX_PLY) that
    are server-fillable — present in opening_position_eval WITH a cached pv.

    Reuses the same position-keyed cache lookup the local drain and submit dedup use
    (`_fetch_dedup_evals`) so the lease's cache-aware omission and the submit's dedup fill
    agree on exactly which openings are server-fillable. Gated on pv IS NOT NULL (SEED-076
    follow-up): a pv-less cache row can fill the eval at submit but NOT the pv, so the
    worker must still evaluate that opening fresh — omitting it here would leave a flaw at
    that ply permanently []-sentineled (no PV to walk). As `_upsert_opening_cache`'s
    DO UPDATE backfill fills pv onto existing rows over time, omission coverage ramps back
    up naturally. Returns an empty set for a game with no opening rows.
    """
    opening_hashes = [fh for (ply, fh, _cp, _mate) in gp_rows if ply <= DEDUP_MAX_PLY]
    if not opening_hashes:
        return frozenset()
    cached = await _fetch_dedup_evals(session, opening_hashes)
    return frozenset(fh for fh, (_cp, _mate, _bm, pv) in cached.items() if pv is not None)


def _lease_position_redundant(
    target: _FullPlyEvalTarget,
    target_by_ply: dict[int, _FullPlyEvalTarget],
    cached_hashes: frozenset[int],
) -> bool:
    """SEED-076: True when the worker need not evaluate this lease position.

    Two omission reasons, both making the position's eval available without a worker
    round-trip:

    - Cache-aware: an opening position (ply <= DEDUP_MAX_PLY) whose full_hash is already
      in `opening_position_eval` — the submit dedup_map fills it server-side. (Never
      applies to the terminal donor: its full_hash is 0 and is never cached.)
    - Incremental: position Q's eval is stored, post-move (SEED-044), at DB row Q-1. If
      that row already carries an eval, or is the legit game-over NULL (ends_game), the
      worker need not re-evaluate Q — the paired submit `preserve_existing_evals` guard
      keeps it out of the whole-game hole count.

    The terminal eval-donor is NEVER redundant (SEED-044 pitfall 3 / plan detail #2): it
    supplies the last played move's after-eval and must survive the filter.
    """
    if target.is_terminal:
        return False
    ply = target.ply
    if ply <= DEDUP_MAX_PLY and target.full_hash in cached_hashes:
        return True
    prev = target_by_ply.get(ply - 1)
    if prev is not None and (
        prev.eval_cp is not None or prev.eval_mate is not None or prev.ends_game
    ):
        return True
    return False


def _merge_dedup_pv_into_engine_map(
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> None:
    """SEED-076 follow-up: merge a cached opening position's pv into engine_result_map.

    The cache-aware lease omits opening positions already in opening_position_eval, so
    the worker never sends an eval/pv for them — the submit dedup_map fills the eval, but
    engine_result_map (and thus _classify_and_fill_oracle's pv write / sentinel derivation)
    never saw the cached pv. This is the crux fix: for each non-terminal target in the
    opening region whose full_hash is in dedup_map AND whose ply the worker did NOT
    evaluate fresh, insert the cached 4-tuple (cp, mate, best_move, pv) into
    engine_result_map. Never overrides a ply the worker resolved itself. Mutates
    engine_result_map in place; a no-op tuple for a dedup miss is never inserted.

    MUST run before `_classify_and_fill_oracle` (so classify writes the merged pv) and,
    on the atomic path, before `_derive_atomic_sentinel_lines` (so it walks the real pv
    instead of []-sentineling the flaw).
    """
    for target in targets:
        if target.is_terminal or target.ply > DEDUP_MAX_PLY:
            continue
        if target.ply in engine_result_map:
            continue
        cached = dedup_map.get(target.full_hash)
        if cached is not None:
            engine_result_map[target.ply] = cached


def _build_lease_positions(
    game_id: int,
    pgn_text: str,
    gp_rows: list[tuple[int, int, int | None, int | None]],
    cached_hashes: frozenset[int] = frozenset(),
) -> list[LeasePosition] | None:
    """Collect per-ply FEN positions from a game's PGN for the lease response.

    Replays the PGN once to build a ply->board.fen() map, then merges with the
    target list from _collect_full_ply_targets (include_terminal=True so the last
    played ply's after-eval can be resolved at submit time — SEED-044 pitfall 3).

    SEED-076 (cache-aware incremental lease): positions already fillable server-side —
    cached openings (in `opening_position_eval`) and plies whose DB row already has an
    eval — are omitted so a weak/slow worker never re-grinds them (the exact repeated
    opening timeout that permanently stamped user 218's games). See
    `_lease_position_redundant`. The terminal donor is always kept, and if the filter
    empties the lease (e.g. a board-over game with everything already resolved) we fall
    back to the full list so a claimed game is never starved of the submit that triggers
    the server-side dedup fill.

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

    # Index non-terminal targets by ply so the redundancy check can inspect the DB row
    # that each position's eval would fill (row Q-1, post-move shift — SEED-044).
    target_by_ply = {t.ply: t for t in targets if not t.is_terminal}

    all_positions: list[LeasePosition] = []
    filtered_positions: list[LeasePosition] = []
    for t in targets:
        fen = fen_by_ply.get(t.ply)
        if fen is None:
            continue
        pos = LeasePosition(ply=t.ply, fen=fen, is_terminal=t.is_terminal)
        all_positions.append(pos)
        if not _lease_position_redundant(t, target_by_ply, cached_hashes):
            filtered_positions.append(pos)

    # SEED-076 safety net: never return an empty lease for a claimed game — the submit
    # (which triggers the server-side dedup fill + the Path A/B/C completion decision)
    # only runs if the worker has something to evaluate. Fall back to the full list.
    positions = filtered_positions if filtered_positions else all_positions
    return positions if positions else None


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


@router.post("/atomic-lease", response_model=None)
async def atomic_lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
    scope: Annotated[Literal["explicit", "idle"] | None, Query()] = None,
) -> Response | AtomicLeaseResponse:
    """Claim the next eval game for the atomic (versioned) eval+blob worker pipeline.

    NEW endpoint pair (Phase 147 SEED-074 Part B, D-02) — does NOT modify /lease
    or /submit; both stay live and deprecated for a mixed-fleet deploy. Selects
    games with the IDENTICAL claim_eval_job priority (tier-1 > tier-2 > tier-3,
    SKIP LOCKED, stale-lease sweep) and returns the same FEN-per-ply lease shape
    _build_lease_positions already produces (Q4 narrower-hint design — no PGN,
    no Game metadata added to the payload).

    The upgraded worker classifies the leased positions locally purely as a HINT
    (which plies look like flaws), builds its own MultiPV-2 continuation blobs for
    those plies, and submits full-ply evals + blob nodes together via the paired
    /atomic-submit endpoint (147-05). The server re-runs classify_game_flaws
    authoritatively there — it never trusts the worker's local hint-classify.

    Returns 204 when no eligible game is in the queue, when the claimed game is a
    lichess-eval game (PV-backfill path deferred, mirrors /lease), or when the
    game's lease payload would exceed MAX_SUBMIT_EVALS positions (over-cap
    sentinel — reuses the 147-03/SEED-073 "never construct an oversized response,
    204 instead of 500" pattern). A real chess game essentially never reaches
    MAX_SUBMIT_EVALS (1024) plies, so this is defense-in-depth, not an expected
    path; the claimed job (if any) is released back to 'pending' rather than
    stuck 'leased' for the full TTL, mirroring the lichess-eval-game skip above.
    """
    # claim_eval_job owns its sessions — no caller session context needed.
    claim = await claim_eval_job(worker_id=worker_id, scope=scope)

    if claim is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    game_id = claim.game_id
    user_id = claim.user_id
    is_lichess_eval_game = claim.is_lichess_eval_game

    # D-4 / v1 scope: lichess PV-backfill games deferred (mirrors /lease).
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
        # SEED-076: opening full_hashes already in opening_position_eval — the
        # cache-aware lease omits these so a weak worker never re-grinds them.
        cached_hashes = await _fetch_cached_opening_hashes(read_session, gp_rows)
    # read_session closed

    positions = _build_lease_positions(game_id, pgn_text, gp_rows, cached_hashes)
    if positions is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # SEED-073/147-03 over-cap sentinel pattern: never construct an oversized
    # lease response. Release the job (if any) so it does not stay stuck
    # 'leased' for the full TTL instead of going back to 'pending' immediately.
    if len(positions) > MAX_SUBMIT_EVALS:
        if claim.job_id is not None:
            await release_job(claim.job_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return AtomicLeaseResponse(
        game_id=game_id,
        user_id=user_id,
        is_lichess_eval_game=False,
        positions=positions,
        leased_at=datetime.now(timezone.utc),
        job_id=claim.job_id,
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
    request: Request,
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
                        # D-05 (Phase 148 item 5): exclude a leased-but-expired game.
                        # Without this, a stale/re-leased game (e.g. re-leased under
                        # the same fixed --worker-id by a different worker instance,
                        # or a late resubmit after TTL reclaim) would still match on
                        # worker_id alone and get stamped complete with a late/wrong
                        # submission. sa.func.now() is server-side (avoids app/DB
                        # clock skew), matching the established pattern elsewhere
                        # (app/users.py, app/routers/auth.py).
                        Game.entry_eval_lease_expiry > sa.func.now(),
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

            # PRUNE-06: passive telemetry only (D-01/D-04) — no gate, submits only.
            await upsert_worker_heartbeat(
                write_session,
                worker_id=worker_id,
                last_ip=request.client.host if request.client else None,
                sf_version=body.sf_version,
                worker_schema_version=None,  # entry-submit never sends this (D-03)
                n_evals=len(body.evals),
            )
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

    # SEED-073: over-cap sentinel. Fat games (> MAX_SUBMIT_EVALS walkable flaw-blob
    # positions, e.g. games with many flaws and long PVs) used to raise a Pydantic
    # ValidationError when FlawBlobLeaseResponse.positions (max_length=MAX_SUBMIT_EVALS)
    # was constructed with an oversized list, surfacing as a 500. The tier-4 lottery then
    # re-picked the same game forever because it never wrote a blob and never cleared the
    # allowed_pv_lines IS NULL predicate. Fix: sentinel EVERY NULL-blob flaw ply of the
    # game (not just the un-walkable sentinel_lines) in one pass, mirroring the all-sentinel
    # branch above, and return 204 instead of ever building the oversized response. This
    # does not touch MAX_SUBMIT_EVALS (shared DoS guard T-145-05/T-123-05) or the submit
    # path — over-cap games never reach /flaw-blob-submit because no lease is returned.
    elif len(lease_positions) > MAX_SUBMIT_EVALS:
        async with async_session_maker() as null_plies_session:
            null_plies_result = await null_plies_session.execute(
                sa.select(GameFlaw.ply).where(
                    GameFlaw.game_id == game_id,
                    GameFlaw.allowed_pv_lines.is_(None),
                )
            )
            over_cap_plies: set[int] = set(null_plies_result.scalars().all())
        over_cap_blob_map = {ply: ([], []) for ply in over_cap_plies}
        async with async_session_maker() as write_session:
            await _batch_update_flaw_pv_lines(write_session, game_id, over_cap_blob_map)
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
    worker_id: str,
    last_ip: str | None,
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

        # PRUNE-06: passive telemetry only (D-01/D-04) — no gate, submits only.
        await upsert_worker_heartbeat(
            write_session,
            worker_id=worker_id,
            last_ip=last_ip,
            sf_version=body.sf_version,
            worker_schema_version=None,  # flaw-blob-submit never sends this (D-03)
            n_evals=len(body.evals),
        )
        await write_session.commit()

    return FlawBlobSubmitResponse(game_id=game_id, blobs_written=len(blob_map))


@router.post("/flaw-blob-submit", response_model=FlawBlobSubmitResponse)
async def flaw_blob_submit(
    body: FlawBlobSubmitRequest,
    request: Request,
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
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
    return await _apply_flaw_blob_submit(
        body.game_id,
        body,
        worker_id=worker_id,
        last_ip=request.client.host if request.client else None,
    )


# ─── Phase 147 SEED-074 Part B: atomic eval+blob submit helper + endpoint (D-01/D-02) ──


async def _snapshot_preserved_flaw_blobs(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> dict[int, dict[str, Any]]:
    """SEED-076: capture a game's flaw blob + tactic-tag columns before classify runs.

    `_classify_and_fill_oracle` does delete-then-insert, so an incremental atomic retry
    (the worker re-evaluates only the residual holes and does NOT re-blob already-done
    midgame flaws) would leave those flaws' `{allowed,missed}_pv_lines` + 8 tactic-tag
    columns NULL — dumping work already done back onto the tier-4 blob pass and transiently
    dropping tactic tags. We snapshot them here (keyed by ply) and restore them after the
    blob write for flaws not re-blobbed this submit.

    Only flaws that already carry a blob (allowed_pv_lines IS NOT NULL) are captured — a
    NULL-blob flaw has nothing to preserve (it is already awaiting the tier-4 pass).
    """
    result = await session.execute(
        select(
            GameFlaw.ply,
            GameFlaw.allowed_pv_lines,
            GameFlaw.missed_pv_lines,
            GameFlaw.allowed_tactic_motif,
            GameFlaw.allowed_tactic_piece,
            GameFlaw.allowed_tactic_confidence,
            GameFlaw.allowed_tactic_depth,
            GameFlaw.missed_tactic_motif,
            GameFlaw.missed_tactic_piece,
            GameFlaw.missed_tactic_confidence,
            GameFlaw.missed_tactic_depth,
        ).where(
            GameFlaw.game_id == game_id,
            GameFlaw.user_id == user_id,
            GameFlaw.allowed_pv_lines.isnot(None),
        )
    )
    snapshot: dict[int, dict[str, Any]] = {}
    for row in result.all():
        snapshot[row.ply] = {
            "allowed_pv_lines": row.allowed_pv_lines,
            "missed_pv_lines": row.missed_pv_lines,
            "allowed_tactic_motif": row.allowed_tactic_motif,
            "allowed_tactic_piece": row.allowed_tactic_piece,
            "allowed_tactic_confidence": row.allowed_tactic_confidence,
            "allowed_tactic_depth": row.allowed_tactic_depth,
            "missed_tactic_motif": row.missed_tactic_motif,
            "missed_tactic_piece": row.missed_tactic_piece,
            "missed_tactic_confidence": row.missed_tactic_confidence,
            "missed_tactic_depth": row.missed_tactic_depth,
        }
    return snapshot


async def _restore_preserved_flaw_blobs(
    session: AsyncSession,
    game_id: int,
    user_id: int,
    snapshot: dict[int, dict[str, Any]],
    freshly_blobbed: set[int],
) -> None:
    """SEED-076: re-apply snapshotted blob + tactic-tag columns for flaws the current
    submit did NOT re-blob, after classify's delete-then-insert reset them to NULL.

    - A ply the worker DID re-blob this submit (in `freshly_blobbed`) is skipped — its
      fresh values from `_run_multipv2_pass` + the fresh gate win.
    - A snapshotted ply no longer classified as a flaw after classify's delete-then-insert
      has NO surviving row and MUST be filtered out (see the `existing` guard below).

    Uses the ORM bulk-update-by-PK path (same as `bulk_update_tactic_tags`) so the JSONB
    blobs and tag columns update in one round-trip, inside the caller's write transaction.

    Bug fix (FLAWCHESS-8D): the ORM bulk-update-by-PK path asserts exactly 1 row matched
    per parameter set (GameFlaw PK = user_id/game_id/ply), so a snapshotted ply that
    classify no longer flags as a flaw raises StaleDataError ("0 were matched"), NOT the
    silent no-op the old docstring assumed. Incremental re-leasing (SEED-076) makes evals
    arrive across attempts and flip borderline plies in/out of flaw status between submits,
    so this is routine, not a race. Intersect the snapshot with the plies that actually
    survived classify before the bulk update.
    """
    existing_plies = set(
        (
            await session.scalars(
                select(GameFlaw.ply).where(
                    GameFlaw.game_id == game_id,
                    GameFlaw.user_id == user_id,
                )
            )
        ).all()
    )
    rows = [
        {"user_id": user_id, "game_id": game_id, "ply": ply, **cols}
        for ply, cols in snapshot.items()
        if ply not in freshly_blobbed and ply in existing_plies
    ]
    if not rows:
        return
    await session.execute(update(GameFlaw), rows)


async def _apply_atomic_submit(
    game_id: int,
    body: AtomicSubmitRequest,
    worker_id: str,
    last_ip: str | None,
) -> AtomicSubmitResponse:
    """Apply an atomic eval+blob submit: evals -> authoritative classify (with the
    worker's blobs) -> blob write -> both completion markers, ONE write_session
    (Phase 147 SEED-074 Part B, D-01/D-02 — the _full_drain_tick Step 4 template).

    Eliminates the ungated window the old /lease + /submit pair leaves open (D-01):
    the upgraded worker submits full-ply evals AND its own MultiPV-2 continuation
    blobs for the plies its LOCAL hint-classify flagged as flaws, together, in one
    request. The server NEVER trusts that hint (T-147-03 Spoofing/Tampering
    boundary) — it re-runs classify_game_flaws on its OWN game_positions and
    independently re-derives which (flaw_ply, line) pairs are structurally
    un-walkable (D-06 sentinel semantics) purely from the worker's submitted
    evals/PVs, via _derive_atomic_sentinel_lines — never from which tokens the
    worker happened to send.

    Read phase (short session, closed before CPU work): load Game + GamePosition
    rows, mirroring _apply_submit's read phase.

    Token tamper guard (T-147-02, mirrors _apply_flaw_blob_submit's T-145-09):
    every submitted blob_nodes token must parse and reference a flaw_ply within
    this game's actual ply range; anything else is rejected with 422 BEFORE any
    write happens. A token for an in-range ply the server does NOT classify as a
    flaw is intentionally NOT rejected here — the worker's local hint-classify is
    expected to sometimes diverge from the server's authoritative classify (that
    divergence is the whole reason the server re-classifies at all), so such a
    token is silently dropped later at the SQL join in _run_multipv2_pass (no
    game_flaws row exists at that ply to update).

    Write phase (ONE session, mirrors _full_drain_tick Step 4 / RESEARCH.md
    "_full_drain_tick's atomic-write ordering"): apply evals -> classify_game_flaws
    (with the worker-supplied blob_map) -> write blobs -> branch on failed_ply_count
    into the same Path A/B/C SEED-045 bounded-retry invariant _apply_submit uses
    (CR-01, 147-REVIEW.md) -> ONE commit (T-117-11: no partial/ungated state is
    ever observable). Path A (no holes) and Path C (holes, MAX_EVAL_ATTEMPTS
    reached) stamp both completion markers; Path B (holes, under cap) increments
    full_eval_attempts and leaves the game pending for retry instead.

    blobs_pending=True is passed to _classify_and_fill_oracle here (a deliberate,
    documented deviation from the plan's literal "blobs_pending stays False" — see
    147-05-SUMMARY.md Deviations): tracing _classify_tactic_gated shows blobs_pending
    ONLY affects the case where flaw_pv_blobs.get(flaw_ply) is None (the flaw_ply
    key is entirely absent — i.e. the server found a flaw the worker did not blob
    at all). It has ZERO effect on a flaw with a real submitted blob (gate runs via
    apply_forcing_line_filter unconditionally) and ZERO effect on the D-06
    []-sentinel / mate-adjacent FINAL cases (both gate on `pv_blob` being present,
    not on blobs_pending). blobs_pending=True is therefore required — and safe — to
    satisfy the must_have "a flaw the server found but the worker did not blob
    writes NULL (Part A net) and is left for tier-4 backfill", which is otherwise
    unreachable with blobs_pending=False (that must_have's own explicit Task 2 test
    requires it).
    """
    # ── Read phase — short session, close before CPU work ────────────────────
    async with async_session_maker() as read_session:
        game_result = await read_session.execute(select(Game).where(Game.id == game_id))
        game = game_result.unique().scalar_one_or_none()
        if game is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found",
            )

        pgn_text: str = game.pgn
        is_lichess_eval_game: bool = game.lichess_evals_at is not None
        owner_id: int = game.user_id
        # CR-01: read the current retry count so the write phase can branch on
        # the same Path A/B/C SEED-045 bounded-retry invariant _apply_submit uses.
        current_attempts: int = game.full_eval_attempts

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

    targets = _collect_full_ply_targets(
        game_id=game_id,
        pgn_text=pgn_text,
        game_positions_rows=gp_rows,
        include_terminal=not is_lichess_eval_game,
    )
    game_length = sum(1 for t in targets if not t.is_terminal)

    # Worker supplies (eval_cp, eval_mate, best_move, pv) keyed by position ply —
    # identical shape to /submit's engine_result_map (D-2: worker is a dumb
    # FEN->eval function; the server owns all storage convention).
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {
        e.ply: (e.eval_cp, e.eval_mate, e.best_move, e.pv) for e in body.evals
    }

    # SEED-076 follow-up: fetch the opening-cache dedup_map in its own short read
    # session and merge cached pv into engine_result_map BEFORE
    # _derive_atomic_sentinel_lines below — the sentinel derivation must see the
    # merged pv so a flaw at a cache-omitted opening ply gets a real PV walk
    # instead of a permanent [] sentinel. The cache is insert-only, so reading it
    # here (ahead of the write session) is staleness-safe. Reused as-is inside the
    # write session for _apply_full_eval_results below (not re-fetched).
    async with async_session_maker() as dedup_session:
        dedup_map = (
            {}
            if is_lichess_eval_game
            else await _fetch_dedup_evals(
                dedup_session,
                [t.full_hash for t in targets if t.ply <= DEDUP_MAX_PLY and not t.is_terminal],
            )
        )
    _merge_dedup_pv_into_engine_map(targets, dedup_map, engine_result_map)

    # ── Token tamper guard (T-147-02): structural in-game-range check ─────────
    # A token whose flaw_ply falls outside this game's actual ply range is
    # unconditionally foreign — reject before any write (mirrors the
    # _apply_flaw_blob_submit / T-145-09 precedent, whose own test uses an
    # out-of-range flaw_ply=99 for exactly this reason).
    for node in body.blob_nodes:
        try:
            node_flaw_ply, _line, _k = _parse_token(node.token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Malformed token: {node.token!r}",
            ) from exc
        if not (0 <= node_flaw_ply < game_length):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown or foreign token: {node.token!r}",
            )

    # ── Re-derive un-walkable (flaw_ply, line) pairs server-side (D-06) ────────
    # Entirely from the server's own authoritative classify + the worker's
    # submitted evals/PVs — independent of which tokens the worker submitted.
    sentinel_lines = await _derive_atomic_sentinel_lines(game_id, targets, engine_result_map)

    # Reassemble the worker's token-keyed blob_nodes into a {flaw_ply -> (allowed,
    # missed)} PvNode map. A flaw_ply with no submitted tokens and no sentinel entry
    # for either line is left out entirely — the classify call below (blobs_pending
    # =True) suppresses that flaw's tag to NULL rather than persisting it raw.
    flaw_pv_blobs = _assemble_flaw_blobs_from_submit(game_id, body.blob_nodes, sentinel_lines)

    # ── Write phase — ONE late session, all UPDATEs + commit atomic (T-117-11) ──
    stamp_complete: bool

    async with async_session_maker() as write_session:
        # SEED-076: dedup_map (fetched above, pre-write-session — SEED-076 follow-up
        # moved this earlier so the pv merge could run before sentinel derivation)
        # so cached opening plies the weak worker timed out on — and the cache-aware lease
        # omitted — are filled server-side BEFORE failed_ply_count is computed, and
        # preserve_existing_evals keeps already-eval'd plies dropped from the incremental
        # re-lease out of the hole count. Together they stop a fillable opening hole from
        # reaching the Path-C cap and permanently stamping the game incomplete (FLAWCHESS-8B).

        # SEED-076: snapshot existing flaw blobs + tactic tags BEFORE classify's
        # delete-then-insert, so a sparse incremental retry (worker did not re-blob an
        # already-done midgame flaw) does not wipe them (restored after the blob write).
        preserved_flaw_blobs = await _snapshot_preserved_flaw_blobs(
            write_session, game_id, owner_id
        )

        # CR-01 (147-REVIEW.md): capture failed_ply_count — previously discarded,
        # which unconditionally stamped completion markers even with NULL-hole
        # engine-game plies, reintroducing the pre-Phase-119 SEED-045 bug class
        # (see resweep_holed_games() docstring for the exact failure mode).
        failed_ply_count = await _apply_full_eval_results(
            write_session,
            targets,
            dedup_map,
            engine_result_map,
            is_lichess_eval_game,
            preserve_existing_evals=True,
        )

        # Server-authoritative classify: re-runs classify_game_flaws on the server's
        # OWN game_positions (T-147-03) using the worker's blobs purely as gate input,
        # never as a trusted flaw-ply hint. Runs BEFORE the blob write (Pitfall 4:
        # blobs are not yet in the DB here) and BEFORE the completion markers so
        # evals + flaws + blobs commit atomically with the markers.
        await _classify_and_fill_oracle(
            write_session,
            game_id,
            engine_result_map,
            flaw_pv_blobs if flaw_pv_blobs else None,
            blobs_pending=True,
        )

        flaws_written = await write_session.scalar(
            sa.select(sa.func.count()).select_from(GameFlaw).where(GameFlaw.game_id == game_id)
        )

        await _run_multipv2_pass(write_session, game_id, flaw_pv_blobs)

        # SEED-076: restore preserved blobs/tags for flaws this submit did NOT re-blob
        # with a REAL blob, undoing classify's delete-then-insert reset. "Freshly blobbed"
        # counts only non-empty lines: a sparse incremental retry that never re-evaluated
        # an already-done flaw yields a []-sentinel for it (no PV to walk), which
        # _run_multipv2_pass just wrote — restoring the prior real blob over that transient
        # sentinel is correct (the line's walkability was already proven on the first pass).
        freshly_blobbed = {
            ply for ply, (allowed, missed) in flaw_pv_blobs.items() if allowed or missed
        }
        await _restore_preserved_flaw_blobs(
            write_session, game_id, owner_id, preserved_flaw_blobs, freshly_blobbed
        )

        # CR-01: mirror _apply_submit's Path A/B/C SEED-045 bounded-retry branch
        # exactly, instead of unconditionally stamping both completion markers.
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
                "atomic-submit: stamping complete after MAX_EVAL_ATTEMPTS with residual holes",
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
                    jobs_table.c.status == "leased",
                )
                .values(status="completed", completed_at=now_ts)
            )

        # PRUNE-06: passive telemetry only (D-01/D-04) — no gate, submits only.
        await upsert_worker_heartbeat(
            write_session,
            worker_id=worker_id,
            last_ip=last_ip,
            sf_version=body.sf_version,
            worker_schema_version=body.worker_schema_version,
            n_evals=len(body.evals),
        )

        await write_session.commit()

    # Signal after commit so the hook never fires for a partially-committed game.
    # IN-01: gate on stamp_complete — a Path-B late submit must not prematurely
    # notify user-facing caches/UI that a game's analysis is complete.
    if stamp_complete:
        _signal_flaw_completion(owner_id)

    return AtomicSubmitResponse(
        game_id=game_id,
        flaws_written=flaws_written or 0,
        blobs_written=len(flaw_pv_blobs),
        failed_ply_count=failed_ply_count,
        stamp_complete=stamp_complete,
    )


@router.post("/atomic-submit", response_model=AtomicSubmitResponse)
async def atomic_submit_eval(
    body: AtomicSubmitRequest,
    request: Request,
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
) -> AtomicSubmitResponse:
    """Apply one game's full-ply evals + MultiPV-2 blobs atomically (Phase 147 D-01/D-02).

    NEW endpoint pair (paired with /atomic-lease, 147-04) — does NOT modify /submit
    or /flaw-blob-submit; both stay live for a mixed-fleet deploy. Unlike the old
    /submit (which always defers blobs to a separate tier-4 round-trip) and
    /flaw-blob-submit (which only ever retags existing NULL-blob flaw rows), this
    endpoint applies evals, classifies flaws, and writes gated tactic tags + PV-line
    blobs + both completion markers in ONE transaction — no ungated window is ever
    observable for a game processed here (see _apply_atomic_submit for the full
    write-ordering rationale).

    worker_schema_version is accepted but not gated on (Q5, RESEARCH.md): the server
    re-classifies authoritatively regardless of which schema version produced the
    worker's evals/blobs, so a stale worker cannot corrupt correctness — only
    (transiently) miss the gate for plies it didn't blob, which the NULL-suppression
    net + a future tier-4 pass resolves.

    Expected status codes (do NOT Sentry-capture):
      404 — game not found
      422 — SF version mismatch or foreign/out-of-range blob token (T-147-02)
    """
    # D-5 SF-version gate (same as /submit, /entry-submit, /flaw-blob-submit).
    if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stockfish version mismatch",
        )
    return await _apply_atomic_submit(
        game_id=body.game_id,
        body=body,
        worker_id=worker_id,
        last_ip=request.client.host if request.client else None,
    )
