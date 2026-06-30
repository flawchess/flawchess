"""Pydantic v2 schemas for the eval remote API endpoints (Phase 120 SEED-048)."""

from datetime import datetime

from pydantic import BaseModel, Field

# Upper bound on the submitted evals list. A real game has at most a few hundred
# plies; this cap is generous insurance against a buggy/compromised worker posting
# an arbitrarily large body that the endpoint would materialize in memory at once.
MAX_SUBMIT_EVALS: int = 1024


class LeasePosition(BaseModel):
    ply: int = Field(ge=0)
    fen: str  # board.fen() — full FEN including turn, castling, en passant
    is_terminal: bool  # True for the terminal eval-donor


class LeaseResponse(BaseModel):
    game_id: int
    user_id: int  # informational: the game's authoritative owner (not trusted on submit)
    is_lichess_eval_game: bool
    positions: list[LeasePosition]
    leased_at: datetime
    # Opaque eval_jobs.id token; None for tier-3 derived picks (no eval_jobs row).
    # The worker echoes this back on submit so the server can stamp eval_jobs.
    job_id: int | None = None


class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None  # UCI string
    pv: str | None  # space-joined UCI, up to 12 plies
    # Phase 142 MPV-02: second-best per ply for JSONB blob assembly (D-03).
    # Default None = old worker omits field → server treats as no second-best (D-04).
    second_cp: int | None = None
    second_mate: int | None = None
    second_uci: str | None = None  # wire type str|None; None maps to su="" sentinel in blob


class SubmitRequest(BaseModel):
    game_id: int
    sf_version: str  # e.g. "Stockfish 18" — for D-5 version gate
    evals: list[SubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)
    # Opaque eval_jobs.id token echoed from the lease response; None for tier-3
    # or for an old worker that doesn't include the field. When present, the
    # submit handler stamps eval_jobs.status='completed' (guarded by WHERE status='leased').
    job_id: int | None = None


class SubmitResponse(BaseModel):
    game_id: int
    stamp_complete: bool
    failed_ply_count: int


# ─── Phase 123 SEED-051: entry-ply (import-time) batched schemas (D-07) ──────
# Entry-ply is a BATCH across games, so every position carries its game_id.
# Entry-ply uses depth-15 → returns only eval_cp/eval_mate (no best_move/pv).
# Reuses MAX_SUBMIT_EVALS cap (DoS guard — T-123-05): 50 games × ~3 plies ≈ 150 < 1024.


class EntryLeasePosition(BaseModel):
    game_id: int
    ply: int = Field(ge=0)
    fen: str  # board.fen() — full FEN including turn, castling, en passant


class EntryLeaseResponse(BaseModel):
    positions: list[EntryLeasePosition]
    leased_at: datetime


class EntrySubmitEval(BaseModel):
    game_id: int
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None


class EntrySubmitRequest(BaseModel):
    sf_version: str  # e.g. "Stockfish 18" — for SF-version gate (T-123-07)
    evals: list[EntrySubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)


class EntrySubmitResponse(BaseModel):
    game_ids: list[int]
    stamped_count: int


# ─── Phase 145 SHIP-01: flaw-blob-only lease/submit schemas (D-04) ────────────
#
# These are a DEDICATED, ISOLATED schema set for the flaw-blob backfill endpoint
# (POST /eval/remote/flaw-blob-lease + POST /eval/remote/flaw-blob-submit).
# Per D-04, they MUST NOT reuse or modify LeaseResponse/SubmitRequest — the live
# ply-keyed submit path (_apply_submit) is safety-critical and must remain unchanged.
#
# Token format (D-04a): "{flaw_ply}:{line}:{node_k}"
#   - flaw_ply: int  — the game_flaws.ply value for this flaw
#   - line: str      — "missed" (PV from flaw position) or "allowed" (PV from flaw+1)
#   - node_k: int    — PV walk index (0 = start board, 1 = after first PV move, ...)
# Example: "10:missed:2" → flaw at ply 10, missed line, third node in the PV walk.
# The worker treats the token as opaque (D-04a): it evaluates the leased FEN at
# MultiPV=2 and echoes the token unchanged on submit; no flaw-structure knowledge needed.


class FlawBlobLeasePosition(BaseModel):
    """One FEN position in a flaw-blob lease; token is the server's reassembly key."""

    token: str  # "{flaw_ply}:{line}:{node_k}" — opaque to worker (D-04a)
    fen: str  # board.fen() — full FEN with turn, castling, en passant


class FlawBlobLeaseResponse(BaseModel):
    """Lease response carrying one game's flaw-blob FENs for MultiPV=2 evaluation."""

    game_id: int
    # Bounded by MAX_SUBMIT_EVALS (DoS guard reused — T-145-05 / T-123-05).
    positions: list[FlawBlobLeasePosition] = Field(max_length=MAX_SUBMIT_EVALS)
    leased_at: datetime


class FlawBlobSubmitEval(BaseModel):
    """One worker result: echoed token + MultiPV=2 best and second-best evals."""

    token: str  # echoed from FlawBlobLeasePosition.token unchanged (D-04a)
    best_cp: int | None
    best_mate: int | None
    second_cp: int | None
    second_mate: int | None
    # Wire type is str|None: None = single-legal-move sentinel on the wire.
    # The server maps None → "" when assembling PvNode blobs (Pitfall 3).
    second_uci: str | None


class FlawBlobSubmitRequest(BaseModel):
    """Worker submit payload: game_id, engine version, and per-FEN evaluations."""

    game_id: int
    sf_version: str  # e.g. "Stockfish 18" — for D-5 version gate
    evals: list[FlawBlobSubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)


class FlawBlobSubmitResponse(BaseModel):
    """Submit acknowledgement: how many game_flaws rows had blobs written."""

    game_id: int
    blobs_written: int  # number of flaw rows updated (blobs + sentinels [] counts)
