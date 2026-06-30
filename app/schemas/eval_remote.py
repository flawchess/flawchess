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
