"""maia_encoding.py — pure Python port of the client's Maia-3 board->tensor encoding.

Port target: frontend/src/lib/maiaEncoding.ts (and its worker mirror
frontend/public/maia/maia-worker.js). This module reproduces the CONFIRMED tensor
contract (151-MAIA-CONTRACT.md), re-verified by the 2026-07-10 headless repro that
matched the live UI root distribution to 0.01%
(.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md):

  - 12 one-hot piece-occupancy planes per square, order white P,N,B,R,Q,K (0-5),
    black p,n,b,r,q,k (6-11); no history planes (n=0, "simplified" export).
  - square index s = row*8 + file, row = rank-1 (a1 = 0, h8 = 63).
  - When Black is to move, the piece placement is mirrored (ranks flipped + case
    swapped) BEFORE encoding, so the side to move is always presented as "White".
  - Flat, square-major token layout: tokens[squareIndex(sq)*12 + planeIdx] = 1.0.
  - Policy vocab size 4352 = 4096 base (from,to) pairs + 256 underpromotion lanes
    (64 destination squares x 4 piece lanes). Queen promotions collapse into the
    base lane. Legal-move-masked softmax over the vocab, keyed here by UCI (the
    backend's move currency) rather than the client's SAN — the probability VALUE
    is identical, only the dict key differs.
  - ELO ladder [600, 2600] step 100 (21 rungs); clamp_to_ladder_bounds mirrors the
    frontend clampToLadderBounds so a gem shown live and a gem stored in the DB
    never disagree for the same position/rating (D-04).

This module is PURE (stdlib + python-chess only, NO numpy) and imports cleanly
WITHOUT onnxruntime — so the encoding unit tests run in the default (no-group)
backend suite. numpy lives only in the isolated `maia-inference` uv group alongside
onnxruntime (GEMS-06); the ONNX session, the numpy tensor plumbing, and the parity
gate all live in scripts/maia_parity_spike.py / tests/services/test_maia_parity.py,
which sync that group. encode_board returns a plain list[float]; the ONNX callers
wrap it in a numpy float32 tensor at feed time.

Attribution: the algorithm mirrors FlawChess's own MIT maiaEncoding.ts, which was
written from scratch against the confirmed ONNX I/O contract — no CSSLab AGPL
encoding source is copied.
"""

import math
from collections.abc import Sequence

import chess

# ─── Board encoding constants (CONTRACT §a) ────────────────────────────────────

NUM_SQUARES: int = 64
PLANES_PER_SQUARE: int = 12
NUM_SQUARES_PER_SIDE: int = 8

# 12-plane order: white P,N,B,R,Q,K (0-5), black p,n,b,r,q,k (6-11).
PIECE_PLANE_ORDER: tuple[str, ...] = ("P", "N", "B", "R", "Q", "K", "p", "n", "b", "r", "q", "k")

# ─── Policy vocabulary (CONTRACT §d) ───────────────────────────────────────────

POLICY_VOCAB_SIZE: int = 4352
# Base (non-underpromotion) move-index space: every (from, to) square pair.
BASE_VOCAB_SIZE: int = NUM_SQUARES * NUM_SQUARES  # 4096
# Underpromotion piece lanes reserved per destination square (q shares the base
# lane; only r/b/n index the reserved 256 slots). 4352 - 4096 = 256 = 64 x 4.
UNDERPROMOTION_PIECE_LANES: tuple[str, ...] = ("q", "r", "b", "n")

# ─── ELO ladder (CONTRACT §c; D-04) ────────────────────────────────────────────

MAIA_ELO_LADDER_MIN: int = 600
MAIA_ELO_LADDER_MAX: int = 2600
MAIA_ELO_LADDER_STEP: int = 100


# ─── Square indexing (CONTRACT §a) ─────────────────────────────────────────────


def square_index(square: str) -> int:
    """Map an algebraic square (e.g. "e4") to its token index: s = row*8 + file,
    row = rank - 1 (a1 = 0, h8 = 63)."""
    file = ord(square[0]) - ord("a")
    rank = int(square[1])
    row = rank - 1
    return row * NUM_SQUARES_PER_SIDE + file


def mirror_square(square: str) -> str:
    """Mirror a square vertically (rank r -> rank 9-r), keeping the file unchanged.
    Used to translate a real-board move into the mover's-POV frame the model expects
    when Black is to move."""
    file = square[0]
    rank = NUM_SQUARES_PER_SIDE + 1 - int(square[1])
    return f"{file}{rank}"


def mirror_piece_placement(piece_placement: str) -> str:
    """Mirror a FEN piece-placement field: flip ranks top-to-bottom and swap piece
    colors (uppercase<->lowercase), so the side to move is always presented as
    "White" moving up the board (CONTRACT §a)."""
    ranks = piece_placement.split("/")
    return "/".join(row.swapcase() for row in reversed(ranks))


# ─── Board -> tensor encoding (CONTRACT §a) ────────────────────────────────────


def _encode_piece_placement(piece_placement: str) -> list[float]:
    """Encode a piece-placement field into a flat (64 * 12) token list, square-major:
    tokens[squareIndex(sq)*12 + planeIdx]. Plain list[float] so the module stays
    numpy-free; ONNX callers wrap it in a float32 tensor at feed time."""
    tokens = [0.0] * (NUM_SQUARES * PLANES_PER_SQUARE)
    rows = piece_placement.split("/")  # rows[0] = rank8 ... rows[7] = rank1
    for row_from_top in range(NUM_SQUARES_PER_SIDE):
        row = NUM_SQUARES_PER_SIDE - 1 - row_from_top  # rank8 -> row7, rank1 -> row0
        file = 0
        for char in rows[row_from_top]:
            if char.isdigit():
                file += int(char)
                continue
            if char in PIECE_PLANE_ORDER:
                plane_idx = PIECE_PLANE_ORDER.index(char)
                tokens[(row * NUM_SQUARES_PER_SIDE + file) * PLANES_PER_SQUARE + plane_idx] = 1.0
            file += 1
    return tokens


def encode_board(fen: str) -> list[float]:
    """Encode a FEN into the Maia-3 flat (64*12) token list. Mirrors the board to the
    mover's POV when Black is to move (CONTRACT §a). No history planes (n=0 simplified
    export)."""
    parts = fen.split(" ")
    piece_placement = parts[0]
    if not piece_placement:
        raise ValueError(f"maia_encoding: invalid FEN (no piece-placement field): {fen}")
    is_black_to_move = len(parts) > 1 and parts[1] == "b"
    framed = mirror_piece_placement(piece_placement) if is_black_to_move else piece_placement
    return _encode_piece_placement(framed)


# ─── ELO input (CONTRACT §b) ───────────────────────────────────────────────────


def elo_to_input(elo: float) -> float:
    """Map a ladder ELO value to the confirmed ELO input form: a raw continuous
    float scalar fed directly as elo_self/elo_oppo (CONTRACT §b — no embedding).
    Kept as a named function so the single confirmed mechanism has one place to
    change if the model's ELO input contract is ever revised."""
    return float(elo)


def clamp_to_ladder_bounds(rating: float) -> float:
    """Clamp a rating to the [600, 2600] ELO ladder, mirroring the frontend
    clampToLadderBounds exactly (D-04): min(MAX, max(MIN, rating))."""
    return float(min(MAIA_ELO_LADDER_MAX, max(MAIA_ELO_LADDER_MIN, rating)))


# ─── Policy vocabulary index (CONTRACT §d) ─────────────────────────────────────


def move_vocab_index(from_square: str, to_square: str, promotion: str | None) -> int:
    """Flat policy-vocab index for a move, keyed by from + to + promotion.
    Queen promotions (and non-promoting moves) share the base from*64+to lane —
    a pawn reaching the back rank always promotes, so `to` alone disambiguates it.
    Underpromotions (r/b/n) use a reserved lane keyed by destination + piece."""
    from_idx = square_index(from_square)
    to_idx = square_index(to_square)
    if promotion is None or promotion == "q":
        return from_idx * NUM_SQUARES + to_idx
    lane_idx = UNDERPROMOTION_PIECE_LANES.index(promotion)
    return BASE_VOCAB_SIZE + to_idx * len(UNDERPROMOTION_PIECE_LANES) + lane_idx


# ─── Legal-move masking + softmax (MAIA-03) ────────────────────────────────────


def mask_and_softmax(policy: Sequence[float], fen: str) -> dict[str, float]:
    """Mask the model's flat policy logits to the current FEN's legal moves (via
    python-chess) and apply a numerically-stable softmax, returning a normalized
    per-legal-move probability distribution keyed by UCI. Illegal moves are never
    present in the output. Mirrors from/to squares into the model's frame when
    Black is to move (CONTRACT §d "mirror caveat") before indexing into `policy`.

    `policy` is any indexable sequence of floats (the ONNX callers pass the model's
    logits_move output via `.tolist()`), keeping this function numpy-free."""
    board = chess.Board(fen)
    is_black_to_move = not board.turn  # chess.WHITE is True; Black to move -> False

    n = len(policy)
    ucis: list[str] = []
    scores: list[float] = []
    for move in board.legal_moves:
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        if is_black_to_move:
            from_sq = mirror_square(from_sq)
            to_sq = mirror_square(to_sq)
        promotion = chess.piece_symbol(move.promotion) if move.promotion is not None else None
        idx = move_vocab_index(from_sq, to_sq, promotion)
        score = float(policy[idx]) if 0 <= idx < n else float("-inf")
        ucis.append(move.uci())
        scores.append(score)

    if not scores:
        return {}

    max_score = max(scores)
    exps = [math.exp(s - max_score) for s in scores]
    total = sum(exps)
    if total <= 0.0:
        return {uci: 0.0 for uci in ucis}
    return {uci: exp / total for uci, exp in zip(ucis, exps)}
