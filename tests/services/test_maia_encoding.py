"""Unit tests for app.services.maia_encoding — the pure Python port of the client's
Maia-3 board->tensor encoding (frontend/src/lib/maiaEncoding.ts).

These tests are pure tensor/index/softmax math and MUST run in the default (no-group)
backend suite — the encoding module imports only stdlib + python-chess (NO numpy, NO
onnxruntime). The ONNX-session parity gate lives separately in
scripts/maia_parity_spike.py / tests/services/test_maia_parity.py (which importorskip
numpy + onnxruntime, both in the isolated maia-inference group).

Port target contract (151-MAIA-CONTRACT.md, re-verified by the 2026-07-10 headless
repro that matched the live UI to 0.01%):
  - 12-plane order: white P,N,B,R,Q,K (0-5), black p,n,b,r,q,k (6-11)
  - square index s = row*8 + file, row = rank-1 (a1=0, h8=63)
  - Black to move -> mirror piece placement (flip ranks, swap case) BEFORE encoding
  - tokens[squareIndex(sq)*12 + planeIdx] = 1.0 (square-major flat layout)
  - policy vocab 4352; legal-move-masked softmax excludes illegal moves entirely
  - ELO ladder [600, 2600] step 100; clamp_to_ladder_bounds = min(MAX, max(MIN, r))
"""

import math

from app.services.maia_encoding import (
    MAIA_ELO_LADDER_MAX,
    MAIA_ELO_LADDER_MIN,
    MAIA_ELO_LADDER_STEP,
    NUM_SQUARES,
    PIECE_PLANE_ORDER,
    PLANES_PER_SQUARE,
    POLICY_VOCAB_SIZE,
    clamp_to_ladder_bounds,
    elo_to_input,
    encode_board,
    mask_and_softmax,
    mirror_piece_placement,
    square_index,
)

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class TestConstants:
    def test_board_constants(self) -> None:
        assert NUM_SQUARES == 64
        assert PLANES_PER_SQUARE == 12
        assert POLICY_VOCAB_SIZE == 4352

    def test_elo_ladder_bounds(self) -> None:
        assert MAIA_ELO_LADDER_MIN == 600
        assert MAIA_ELO_LADDER_MAX == 2600
        assert MAIA_ELO_LADDER_STEP == 100

    def test_plane_order(self) -> None:
        """12-plane order: white P,N,B,R,Q,K (0-5), black p,n,b,r,q,k (6-11)."""
        assert list(PIECE_PLANE_ORDER) == [
            "P",
            "N",
            "B",
            "R",
            "Q",
            "K",
            "p",
            "n",
            "b",
            "r",
            "q",
            "k",
        ]
        assert PIECE_PLANE_ORDER.index("P") == 0
        assert PIECE_PLANE_ORDER.index("K") == 5
        assert PIECE_PLANE_ORDER.index("p") == 6
        assert PIECE_PLANE_ORDER.index("k") == 11


class TestSquareIndex:
    def test_corners(self) -> None:
        """a1 = 0, h8 = 63 (CONTRACT §a: s = row*8 + file, row = rank-1)."""
        assert square_index("a1") == 0
        assert square_index("h8") == 63

    def test_interior(self) -> None:
        assert square_index("e4") == 3 * 8 + 4  # rank4 -> row3, e -> file4 => 28
        assert square_index("h1") == 7
        assert square_index("a8") == 56


class TestMirror:
    def test_mirror_flips_ranks_and_swaps_case(self) -> None:
        """mirror_piece_placement reverses rank order AND swaps piece color case."""
        # A minimal asymmetric placement: white rook a1, black king e8.
        placement = "4k3/8/8/8/8/8/8/R7"
        mirrored = mirror_piece_placement(placement)
        # rank8 (4k3) becomes rank1 with case swapped -> "4K3"; rank1 (R7) becomes
        # rank8 with case swapped -> "r7".
        assert mirrored == "r7/8/8/8/8/8/8/4K3"

    def test_mirror_is_involution_on_symmetric_startpos(self) -> None:
        """The start position's piece placement is invariant under mirroring."""
        start_placement = START_FEN.split(" ")[0]
        assert mirror_piece_placement(mirror_piece_placement(start_placement)) == start_placement
        # startpos happens to be its own mirror image (rank-reverse + case-swap).
        assert mirror_piece_placement(start_placement) == start_placement


def _one_hot_planes_per_square(tokens: list[float]) -> list[float]:
    """Sum the 12 planes for each of the 64 squares (each occupied square -> 1.0)."""
    return [
        sum(tokens[s * PLANES_PER_SQUARE : (s + 1) * PLANES_PER_SQUARE]) for s in range(NUM_SQUARES)
    ]


class TestEncodeBoard:
    def test_length_and_floats(self) -> None:
        tokens = encode_board(START_FEN)
        assert len(tokens) == NUM_SQUARES * PLANES_PER_SQUARE
        assert all(isinstance(t, float) for t in tokens)

    def test_exactly_one_hot_per_occupied_square(self) -> None:
        """Start position has 32 pieces -> exactly 32 ones, all others 0."""
        tokens = encode_board(START_FEN)
        assert sum(tokens) == 32.0
        assert set(tokens) <= {0.0, 1.0}
        # Each occupied square carries exactly one plane set (never 2+).
        assert set(_one_hot_planes_per_square(tokens)) <= {0.0, 1.0}

    def test_known_piece_placement_index(self) -> None:
        """White rook on a1 -> tokens[squareIndex('a1')*12 + plane('R')] == 1.0."""
        tokens = encode_board(START_FEN)
        r_plane = PIECE_PLANE_ORDER.index("R")
        assert tokens[square_index("a1") * PLANES_PER_SQUARE + r_plane] == 1.0
        # Black king on e8.
        k_plane = PIECE_PLANE_ORDER.index("k")
        assert tokens[square_index("e8") * PLANES_PER_SQUARE + k_plane] == 1.0

    def test_black_to_move_mirrors_before_encoding(self) -> None:
        """A black-to-move FEN encodes the mirrored placement (mover's POV = 'White')."""
        placement = "4k3/8/8/8/8/8/8/R7"
        white_tokens = encode_board(f"{placement} w - - 0 1")
        black_tokens = encode_board(f"{placement} b - - 0 1")
        # They must differ (mirror applied only for black).
        assert white_tokens != black_tokens
        # black_tokens must equal encoding of the mirrored placement as white.
        assert black_tokens == encode_board(f"{mirror_piece_placement(placement)} w - - 0 1")


def _deterministic_policy() -> list[float]:
    """A varied, deterministic policy vector (stdlib-only, no numpy)."""
    return [math.sin(i * 0.5) for i in range(POLICY_VOCAB_SIZE)]


class TestMaskAndSoftmax:
    def test_sums_to_one_over_legal_moves(self) -> None:
        """Distribution normalizes to 1.0 across exactly the legal moves."""
        probs = mask_and_softmax(_deterministic_policy(), START_FEN)
        # Start position has 20 legal moves.
        assert len(probs) == 20
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        assert all(p >= 0.0 for p in probs.values())

    def test_illegal_moves_excluded(self) -> None:
        """Only legal moves appear as keys; an illegal UCI is never present."""
        policy = [0.0] * POLICY_VOCAB_SIZE
        probs = mask_and_softmax(policy, START_FEN)
        # e2e4 is legal from the start position; e2e5 is not.
        assert "e2e4" in probs
        assert "e2e5" not in probs
        # Uniform policy (all zeros) -> uniform distribution over 20 legal moves.
        for value in probs.values():
            assert abs(value - 1.0 / 20.0) < 1e-9

    def test_black_to_move_masking(self) -> None:
        """Legal-move masking works for a black-to-move position (mirror path)."""
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        policy = [0.0] * POLICY_VOCAB_SIZE
        probs = mask_and_softmax(policy, fen)
        assert len(probs) == 20
        assert "e7e5" in probs
        assert abs(sum(probs.values()) - 1.0) < 1e-9


class TestClampAndElo:
    def test_clamp_below_lower_bound(self) -> None:
        assert clamp_to_ladder_bounds(599) == 600
        assert clamp_to_ladder_bounds(0) == 600

    def test_clamp_above_upper_bound(self) -> None:
        assert clamp_to_ladder_bounds(2601) == 2600
        assert clamp_to_ladder_bounds(3000) == 2600

    def test_in_band_passthrough(self) -> None:
        assert clamp_to_ladder_bounds(600) == 600
        assert clamp_to_ladder_bounds(1500) == 1500
        assert clamp_to_ladder_bounds(2600) == 2600

    def test_elo_to_input_passthrough(self) -> None:
        assert elo_to_input(1500) == 1500.0
        assert elo_to_input(600) == 600.0
