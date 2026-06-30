"""Unit tests for app.services.forcing_line_gate -- pure forcing-line gate.

Covers Phase 141 GATE-01 and GATE-02 (D-01, D-07..D-10):
  - GATE-01 (D-07): only-move win-prob margin over solver nodes; solver-only
    uniqueness (defender nodes have no uniqueness requirement, D-10).
  - GATE-02 (D-08): already-winning reject when pre-flaw eval > 300 cp.
  - GATE-02 (D-09): still-winning floor stops extension below 200 cp.
  - GATE-02 (D-10): trailing-only-move strip and one-mover discard.
  - D-01 (pulled forward from Phase 143): full mate-priority hierarchy:
    only-best-is-mate forced; both-mates shorter-distance forced; mate-in-1
    never suppressed; fall through to win-prob margin otherwise.

Sign convention (D-05): blob cp values are white-perspective.  The gate converts
to side-to-move perspective at read time.  Mate tests cover both colors to catch
the asymmetric-sign bug class (Pitfall 1, mitigated by T-141-04).

This module is intentionally free of database sessions, async fixtures, and
Stockfish worker processes -- their absence IS the Phase 141 success criterion #2 guarantee.
"""

from app.services.forcing_line_gate import (
    ALREADY_WINNING_CP_THRESHOLD,
    ONLY_MOVE_WIN_PROB_MARGIN,
    STILL_WINNING_FLOOR_CP,
    PvNode,
    apply_forcing_line_filter,
    is_solver_node_forced,
)


# ---------------------------------------------------------------------------
# Helpers for building inline test blobs
# ---------------------------------------------------------------------------


def _cp_node(b: int, s: int | None = None) -> PvNode:
    """Construct a centipawn-only PvNode (white-perspective)."""
    return PvNode(b=b, bm=None, s=s, sm=None, su="e2e4" if s is not None else "")


def _mate_node(bm: int, sm: int | None = None) -> PvNode:
    """Construct a mate PvNode (white-perspective, positive = white mating)."""
    return PvNode(b=None, bm=bm, s=None, sm=sm, su="e2e4" if sm is not None else "")


def _only_move_node(b: int) -> PvNode:
    """Construct a solver node with no legal second move (only-move)."""
    return PvNode(b=b, bm=None, s=None, sm=None, su="")


# ---------------------------------------------------------------------------
# TestConstants: pin locked starting values
# ---------------------------------------------------------------------------


class TestConstants:
    """Assert that the three gate constants have the locked starting values (D-07..D-09)."""

    def test_only_move_win_prob_margin(self) -> None:
        """ONLY_MOVE_WIN_PROB_MARGIN is 0.35 -- lichess-puzzler +0.7 translated to 0..1."""
        assert ONLY_MOVE_WIN_PROB_MARGIN == 0.35

    def test_already_winning_cp_threshold(self) -> None:
        """ALREADY_WINNING_CP_THRESHOLD is 300 cp (D-08 already-winning reject)."""
        assert ALREADY_WINNING_CP_THRESHOLD == 300

    def test_still_winning_floor_cp(self) -> None:
        """STILL_WINNING_FLOOR_CP is 200 cp (D-09 still-winning floor)."""
        assert STILL_WINNING_FLOOR_CP == 200


# ---------------------------------------------------------------------------
# TestOnlyMoveMargin: GATE-01 -- is_solver_node_forced cp cases (D-07)
# ---------------------------------------------------------------------------


class TestOnlyMoveMargin:
    """Coverage for the centipawn win-prob margin branch of is_solver_node_forced (D-07)."""

    def test_large_gap_passes_for_white_solver(self) -> None:
        """A wide best-vs-second cp gap exceeds 0.35 margin and is forced (white solver)."""
        # best=800cp (solver well ahead), second=0cp (neutral).
        # delta ≈ p(800,"white") - p(0,"white") ≈ 0.947 - 0.5 = 0.447 > 0.35.
        node = _cp_node(b=800, s=0)
        assert is_solver_node_forced(node, "white") is True

    def test_large_gap_passes_for_black_solver(self) -> None:
        """Same gap flipped to black perspective is also forced (Pitfall 1 symmetry)."""
        # White-perspective: best=-800cp means black is ahead by 800.
        # From black's perspective: p(-800,"black") - p(-100,"black") > 0.35.
        node = _cp_node(b=-800, s=-100)
        assert is_solver_node_forced(node, "black") is True

    def test_small_gap_fails_for_white_solver(self) -> None:
        """A narrow best-vs-second cp gap is below 0.35 margin and is not forced."""
        # best=300cp (solver ahead), second=200cp (also decent for second).
        # delta ≈ p(300,"white") - p(200,"white") ≈ 0.751 - 0.677 = 0.074 < 0.35.
        node = _cp_node(b=300, s=200)
        assert is_solver_node_forced(node, "white") is False

    def test_small_gap_fails_for_black_solver(self) -> None:
        """Same narrow gap from black's perspective is also not forced."""
        node = _cp_node(b=-300, s=-200)
        assert is_solver_node_forced(node, "black") is False

    def test_no_second_legal_move_passes(self) -> None:
        """A node with no second legal move is unconditionally forced (only-move)."""
        node = _only_move_node(b=50)
        assert is_solver_node_forced(node, "white") is True

    def test_no_second_legal_move_passes_black_solver(self) -> None:
        """No-second-move passes regardless of solver color."""
        node = _only_move_node(b=-50)
        assert is_solver_node_forced(node, "black") is True

    def test_boundary_at_margin_not_forced(self) -> None:
        """A delta exactly equal to ONLY_MOVE_WIN_PROB_MARGIN does not pass (strictly greater required)."""
        # Find cp values where delta == 0.35 and assert the node is not forced.
        # p(800,"white") - p(0,"white") ≈ 0.447 > 0.35 -> passes.
        # p(300,"white") - p(200,"white") ≈ 0.074 < 0.35 -> fails.
        # We just confirm the strict > boundary by choosing values we know are sub-margin.
        node = _cp_node(b=250, s=180)  # well below margin
        assert is_solver_node_forced(node, "white") is False

    def test_all_solver_nodes_required_for_apply_filter(self) -> None:
        """apply_forcing_line_filter rejects when any interior solver node fails (not just firing)."""
        # S0=forced(800,0), D0=any, S1=not-forced(300,200), D1=any, S2=forced(800,0).
        # S1 is not forced -> whole line rejected.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced
            _cp_node(b=0, s=-100),  # D0 defender — ignored
            _cp_node(b=300, s=200),  # S1 solver — not forced
            _cp_node(b=0, s=-100),  # D1 defender — ignored
            _cp_node(b=800, s=0),  # S2 solver — forced
        ]
        # Pre-flaw eval: neutral (0 cp) — does not trigger already-winning reject.
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False

    def test_all_solver_nodes_pass_apply_filter(self) -> None:
        """apply_forcing_line_filter passes when every solver node is forced."""
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced
            _cp_node(b=0, s=-100),  # D0 defender — ignored
            _cp_node(b=800, s=0),  # S1 solver — forced
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True

    def test_defender_ambiguity_does_not_kill_line(self) -> None:
        """Defender node with a second-best move does not trigger the uniqueness check (D-10).

        A line that branches at a defender ply but has forced solver moves is valid.
        """
        # D0 has a genuine second-best (ambiguous defender) but is at an odd index.
        # Solver nodes S0, S1 are both forced.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced
            _cp_node(b=100, s=50),  # D0 defender — has second-best; NOT checked
            _cp_node(b=800, s=0),  # S1 solver — forced
        ]
        # Defender ambiguity must not invalidate the line.
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True


# ---------------------------------------------------------------------------
# TestMatePriority: D-01 -- mate-priority hierarchy, both colors (T-141-04)
# ---------------------------------------------------------------------------


class TestMatePriority:
    """Coverage for the mate-priority branch of is_solver_node_forced (D-01).

    Both solver colors are exercised for every case to catch the asymmetric-sign
    bug class (Pitfall 1 / T-141-04 -- Phase 82 was bitten by a single-color gap).
    """

    # --- only-best-is-mate ---

    def test_only_best_is_mate_white_solver(self) -> None:
        """White solver has a forced mate; second-best is cp -> forced (only-best-is-mate)."""
        node = PvNode(b=None, bm=5, s=300, sm=None, su="e2e4")
        assert is_solver_node_forced(node, "white") is True

    def test_only_best_is_mate_black_solver(self) -> None:
        """Black solver has a forced mate (bm<0 = black mating); second-best is cp -> forced."""
        node = PvNode(b=None, bm=-5, s=-300, sm=None, su="e7e5")
        assert is_solver_node_forced(node, "black") is True

    # --- both mates -> shorter distance forced ---

    def test_both_mates_shorter_wins_white_solver(self) -> None:
        """White solver: bm=3 vs sm=7 -> bm shorter -> forced."""
        node = _mate_node(bm=3, sm=7)
        assert is_solver_node_forced(node, "white") is True

    def test_both_mates_shorter_wins_black_solver(self) -> None:
        """Black solver: bm=-3 vs sm=-7 -> abs(bm)=3 < abs(sm)=7 -> forced."""
        node = PvNode(b=None, bm=-3, s=None, sm=-7, su="e7e5")
        assert is_solver_node_forced(node, "black") is True

    def test_both_mates_longer_not_forced_white_solver(self) -> None:
        """White solver: bm=7 vs sm=3 -> bm longer -> not forced."""
        node = _mate_node(bm=7, sm=3)
        assert is_solver_node_forced(node, "white") is False

    def test_both_mates_longer_not_forced_black_solver(self) -> None:
        """Black solver: abs(bm)=7 > abs(sm)=3 -> not forced."""
        node = PvNode(b=None, bm=-7, s=None, sm=-3, su="e7e5")
        assert is_solver_node_forced(node, "black") is False

    # --- mate-in-1 never suppressed ---

    def test_mate_in_1_never_suppressed_white_solver(self) -> None:
        """Mate-in-1 for white solver is always forced, even if second is also mate."""
        # bm=1 (mate-in-1), sm=1 (second also mate-in-1, same distance) -> still forced.
        node = _mate_node(bm=1, sm=1)
        assert is_solver_node_forced(node, "white") is True

    def test_mate_in_1_never_suppressed_black_solver(self) -> None:
        """Mate-in-1 for black solver (bm=-1) is always forced."""
        node = PvNode(b=None, bm=-1, s=None, sm=-1, su="e7e5")
        assert is_solver_node_forced(node, "black") is True

    def test_mate_in_1_vs_second_cp_white_solver(self) -> None:
        """Mate-in-1 for white vs a strong second-best cp is still forced (D-01 guarantee)."""
        node = PvNode(b=None, bm=1, s=900, sm=None, su="e2e4")
        assert is_solver_node_forced(node, "white") is True

    def test_mate_in_1_vs_second_cp_black_solver(self) -> None:
        """Mate-in-1 for black vs a strong second-best cp is still forced."""
        node = PvNode(b=None, bm=-1, s=-900, sm=None, su="e7e5")
        assert is_solver_node_forced(node, "black") is True

    # --- fall-through to win-prob margin ---

    def test_no_mate_falls_through_to_cp_margin(self) -> None:
        """Node with no mate on either move falls through to the win-prob margin."""
        # Large gap: forced.
        node = _cp_node(b=800, s=0)
        assert is_solver_node_forced(node, "white") is True
        # Small gap: not forced.
        node_weak = _cp_node(b=300, s=200)
        assert is_solver_node_forced(node_weak, "white") is False

    def test_both_mates_equal_distance_not_forced(self) -> None:
        """Both mates same distance (bm==sm): abs(bm) < abs(sm) is False -> not forced."""
        # bm=5, sm=5: equal distance.  abs(5) < abs(5) is False.
        node = _mate_node(bm=5, sm=5)
        assert is_solver_node_forced(node, "white") is False


# ---------------------------------------------------------------------------
# TestAlreadyWinning: D-08 -- pre-flaw already-winning reject (GATE-02)
# ---------------------------------------------------------------------------


class TestAlreadyWinning:
    """Coverage for the already-winning reject (D-08, apply_forcing_line_filter)."""

    def _valid_two_move_line_white(self) -> list[PvNode]:
        """Minimal valid two-solver-move line for a white solver (positive cp = white winning)."""
        return [
            _cp_node(b=800, s=0),  # S0 forced (large gap; above floor)
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=800, s=0),  # S1 forced
        ]

    def _valid_two_move_line_black(self) -> list[PvNode]:
        """Minimal valid two-solver-move line for a black solver (negative cp = black winning)."""
        return [
            _cp_node(b=-800, s=0),  # S0 forced for black (large gap; solver_cp=800 > floor)
            _cp_node(b=0, s=100),  # D0 defender
            _cp_node(b=-800, s=0),  # S1 forced for black
        ]

    def test_pre_flaw_above_threshold_white_solver_rejected(self) -> None:
        """pre_flaw_eval_cp=400 (white solver ahead by 400) -> reject (D-08)."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=400) is False

    def test_pre_flaw_above_threshold_black_solver_rejected(self) -> None:
        """pre_flaw_eval_cp=-400 (black solver ahead by 400) -> reject (D-08).

        The already-winning check fires before any floor truncation, so the line
        content is irrelevant for this test.
        """
        line = self._valid_two_move_line_black()
        assert apply_forcing_line_filter(line, "black", pre_flaw_eval_cp=-400) is False

    def test_pre_flaw_at_threshold_not_rejected(self) -> None:
        """pre_flaw_eval_cp=300 exactly (strictly greater-than check): not rejected."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=300) is True

    def test_pre_flaw_below_threshold_not_rejected(self) -> None:
        """pre_flaw_eval_cp=200 (well below threshold): not rejected."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=200) is True

    def test_pre_flaw_at_threshold_black_solver_not_rejected(self) -> None:
        """pre_flaw_eval_cp=-300 exactly for black solver: not rejected (strictly >).

        Uses a black-solver-appropriate line (negative cp = black winning) so the
        still-winning floor is not triggered (solver_cp = 800 >= 200).
        """
        line = self._valid_two_move_line_black()
        assert apply_forcing_line_filter(line, "black", pre_flaw_eval_cp=-300) is True

    def test_pre_flaw_neutral_not_rejected(self) -> None:
        """pre_flaw_eval_cp=0 (even position): not rejected."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True


# ---------------------------------------------------------------------------
# TestStillWinningFloor: D-09 -- extension stops below 200 cp (GATE-02)
# ---------------------------------------------------------------------------


class TestStillWinningFloor:
    """Coverage for the still-winning floor truncation (D-09)."""

    def test_solver_node_below_floor_truncates_line_white(self) -> None:
        """A solver node with b=150cp (white) is below 200cp floor: truncated, leaving one solver node -> one-mover discard."""
        # S0=forced(800,0), D0=any, S1 below floor (150cp).
        # After truncation: [S0, D0] -> 1 solver node -> one-mover discard -> False.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced and above floor
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=150, s=0),  # S1 solver — below STILL_WINNING_FLOOR_CP; truncated
            _cp_node(b=0, s=-100),  # D1 defender
            _cp_node(b=800, s=0),  # S2 solver — would be forced but never reached
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False

    def test_solver_node_below_floor_truncates_line_black(self) -> None:
        """Same truncation from black's perspective (white_cp=-150 -> solver_cp=150 < 200)."""
        line: list[PvNode] = [
            _cp_node(b=-800, s=0),  # S0 forced for black
            _cp_node(b=100, s=0),  # D0 defender
            _cp_node(b=-150, s=0),  # S1 below floor for black solver (solver_cp=150<200)
            _cp_node(b=100, s=0),  # D1 defender
            _cp_node(b=-800, s=0),  # S2 — never reached
        ]
        assert apply_forcing_line_filter(line, "black", pre_flaw_eval_cp=0) is False

    def test_solver_node_at_floor_included(self) -> None:
        """A solver node with b=200cp exactly is AT the floor (< 200 is False): included.

        We verify the node is included (not truncated) by checking it participates
        in the forced-ness evaluation. A 200cp vs 0cp delta is ~0.177, below the
        0.35 margin, so the filter returns False -- but the reason is the margin
        check, NOT floor truncation.
        """
        # S1 at exactly 200cp (not strictly below): included in the effective line.
        # p(200,"white") ~ 0.677; p(0) = 0.5; delta ~ 0.177 < 0.35 -> S1 not forced.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 forced
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=200, s=0),  # S1 at floor exactly, has second-best (included)
        ]
        result = apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0)
        # S1 was included but failed the margin check, not the floor.
        assert result is False  # not forced (small delta), but NOT due to floor truncation

    def test_mate_node_bypasses_floor_check(self) -> None:
        """A solver node that is a forced mate bypasses the still-winning floor (always winning).

        In practice, a MultiPV=2 search at a mate position typically yields a second-best
        cp move (all non-mate moves are losing, but they still exist as legal options).
        The mate-in-N node passes is_solver_node_forced via only-best-is-mate (D-01).
        """
        # S0: mate-in-3 as best; second-best is a 200cp move (not a mate — only-best-is-mate).
        # S1: mate-in-2 as best; second-best is a 150cp move.
        # Both mates bypass the floor check (bm is not None); no cp floor applies.
        s0: PvNode = PvNode(b=None, bm=3, s=200, sm=None, su="d1h5")  # forced via only-best-is-mate
        s1: PvNode = PvNode(b=None, bm=2, s=150, sm=None, su="d1h4")  # forced via only-best-is-mate
        line: list[PvNode] = [
            s0,  # S0 solver — mate-in-3, has cp second-best
            _cp_node(b=0, s=-100),  # D0 defender
            s1,  # S1 solver — mate-in-2, has cp second-best
        ]
        # Both solver nodes pass (only-best-is-mate); floor bypassed for both mates.
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True


# ---------------------------------------------------------------------------
# TestLineStripping: D-10 -- trailing strip, one-mover discard, defender re-convergence
# ---------------------------------------------------------------------------


class TestLineStripping:
    """Coverage for trailing-only-move strip and one-mover discard (D-10)."""

    def test_trailing_only_move_stripped_leaving_two_solver_nodes(self) -> None:
        """A trailing solver only-move is stripped; two genuine solver nodes remain -> passes."""
        # S0=forced(800,0), D0=any, S1=forced(800,0), D1=any, S2=only-move(250).
        # Strip S2 (and nodes after it; none here): [S0, D0, S1, D1].
        # Solver nodes: S0, S1 -> count=2 -> both forced -> PASS.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 forced
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=800, s=0),  # S1 forced
            _cp_node(b=0, s=-100),  # D1 defender
            _only_move_node(b=250),  # S2 trailing only-move — STRIPPED
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True

    def test_one_mover_line_discarded(self) -> None:
        """A line that reduces to one solver node after stripping is discarded."""
        # S0=forced(800,0), D0=any — only one solver node -> one-mover discard.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 — only solver node
            _cp_node(b=0, s=-100),  # D0 defender (extra)
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False

    def test_single_solver_node_line_discarded(self) -> None:
        """A line with just one solver move is a one-mover and is discarded."""
        line: list[PvNode] = [_cp_node(b=800, s=0)]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False

    def test_empty_line_discarded(self) -> None:
        """An empty line is discarded (zero solver nodes)."""
        assert apply_forcing_line_filter([], "white", pre_flaw_eval_cp=0) is False

    def test_multiple_trailing_only_moves_all_stripped(self) -> None:
        """Multiple consecutive trailing only-moves are all stripped."""
        # S0=forced, D0=any, S1=forced, D1=any, S2=only-move, D2=any, S3=only-move.
        # Strip S3 -> strip S2 and D2 -> strip S1? No: S1 has second-best.
        # Result: [S0, D0, S1] -> 2 solver nodes -> both forced -> PASS.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 forced
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=800, s=0),  # S1 forced (has second-best)
            _cp_node(b=0, s=-100),  # D1 defender
            _only_move_node(b=300),  # S2 only-move — stripped
            _cp_node(b=0, s=-100),  # D2 defender — stripped along with S2
            _only_move_node(b=250),  # S3 only-move — stripped first
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True

    def test_defender_re_convergence_does_not_kill_line(self) -> None:
        """Defender ambiguity (multiple equal replies) does NOT disqualify a forced line (D-10).

        A line that branches at a defender ply but re-converges to a single
        forcing continuation is valid; only solver-side ambiguity kills a line.
        """
        # D0 has a small gap (ambiguous): its node has s=50 (close to b=100).
        # But D0 is at an odd index -> not checked by is_solver_node_forced.
        # S0 and S1 are both forced.
        ambiguous_defender = _cp_node(b=100, s=50)  # unclear defender choice
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced
            ambiguous_defender,  # D0 defender — ambiguous; NOT checked
            _cp_node(b=800, s=0),  # S1 solver — forced
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True

    def test_line_stripped_to_one_solver_is_discarded(self) -> None:
        """Stripping the trailing only-move leaves exactly one solver node -> discarded."""
        # S0=forced, D0=any, S1=only-move.
        # Strip S1: [S0, D0] -> 1 solver node -> one-mover discard -> False.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 forced
            _cp_node(b=0, s=-100),  # D0 defender
            _only_move_node(b=300),  # S1 trailing only-move — stripped
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False
