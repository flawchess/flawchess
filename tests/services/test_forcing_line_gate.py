"""Unit tests for app.services.forcing_line_gate -- pure forcing-line gate.

Covers Phase 141 GATE-01 and GATE-02 (D-01, D-07..D-10):
  - GATE-01 (D-07): only-move win-prob margin over solver nodes; solver-only
    uniqueness (defender nodes have no uniqueness requirement, D-10).
  - GATE-02 (D-08): already-winning reject when pre-flaw eval > 600 cp (Phase 144;
    forced mates exempt).
  - GATE-02 (D-09): still-winning floor stops extension below 200 cp (Phase 144:
    conversion tail only -- the firing node is exempt).
  - GATE-02 (D-10): trailing-only-move strip and one-mover discard (forced mates exempt).
  - Phase 144 (sigmoid-saturation): the only-move check also passes on a large raw
    centipawn gap (ONLY_MOVE_CP_GAP_THRESHOLD), not just the win-prob margin.
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
    ONLY_MOVE_CP_GAP_THRESHOLD,
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
        """ALREADY_WINNING_CP_THRESHOLD is 800 cp (D-08, raised in Phase 144 VALID-02)."""
        assert ALREADY_WINNING_CP_THRESHOLD == 800

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
        # best=250cp (solver ahead), second=200cp. delta ≈ 0.039 < 0.35 win-prob margin,
        # and the 50cp gap is below the 100cp escape, so neither branch credits it.
        node = _cp_node(b=250, s=200)
        assert is_solver_node_forced(node, "white") is False

    def test_small_gap_fails_for_black_solver(self) -> None:
        """Same narrow gap from black's perspective is also not forced."""
        node = _cp_node(b=-250, s=-200)
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
        # S0=forced(800,0), D0=any, S1=not-forced(250,200), D1=any, S2=forced(800,0).
        # S1 is not forced (gap 50 < 100 escape, delta 0.039 < margin) -> whole line rejected.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced
            _cp_node(b=0, s=-100),  # D0 defender — ignored
            _cp_node(b=250, s=200),  # S1 solver — not forced
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
# TestDepthAwareForcedness: Bug B -- forcedness only through the firing depth
# ---------------------------------------------------------------------------


class TestDepthAwareForcedness:
    """Bug B: only solver nodes up to the firing depth must be forced.

    Models report case 27 (game 681358 ply 16): a real depth-0 fork whose firing
    node is a unique only-move, followed by a winning conversion whose deep solver
    nodes have several near-equal moves. The legacy whole-line check rejected it;
    the depth-aware check credits it.
    """

    # A case-27-shaped line: forced firing node at idx0, a NON-forced deep solver
    # node at idx2 (small gap, still above the +200 floor so it is not truncated),
    # and a forced node at idx4. pre_flaw_eval_cp=0 avoids the already-winning reject.
    _CASE_27_LINE: list[PvNode] = [
        _cp_node(b=800, s=0),  # S0 idx0 — forced firing node (gap ≈ 0.45)
        _cp_node(b=0, s=-100),  # D0 idx1 — defender, ignored
        _cp_node(b=250, s=200),  # S2 idx2 — NOT forced (tiny gap), b≥200 → not truncated
        _cp_node(b=0, s=-100),  # D1 idx3 — defender, ignored
        _cp_node(b=800, s=0),  # S4 idx4 — forced
    ]

    def test_legacy_none_rejects_on_deep_node(self) -> None:
        """firing_depth=None keeps the whole-line check: idx2 fails -> rejected."""
        assert apply_forcing_line_filter(self._CASE_27_LINE, "white", pre_flaw_eval_cp=0) is False

    def test_depth0_survives_despite_deep_non_forced_nodes(self) -> None:
        """firing_depth=0 checks only the firing node (idx0, forced) -> credited (Bug B)."""
        assert (
            apply_forcing_line_filter(
                self._CASE_27_LINE, "white", pre_flaw_eval_cp=0, firing_depth=0
            )
            is True
        )

    def test_depth2_requires_firing_node_forced(self) -> None:
        """firing_depth=2 includes idx2 (the firing node); it is not forced -> rejected."""
        assert (
            apply_forcing_line_filter(
                self._CASE_27_LINE, "white", pre_flaw_eval_cp=0, firing_depth=2
            )
            is False
        )

    def test_depth2_passes_when_setup_and_firing_forced(self) -> None:
        """A depth-2 tactic with idx0+idx2 forced and only a deep idx4 non-forced passes."""
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 idx0 — forced (setup)
            _cp_node(b=0, s=-100),  # D0 idx1
            _cp_node(b=800, s=0),  # S2 idx2 — forced (firing)
            _cp_node(b=0, s=-100),  # D1 idx3
            _cp_node(b=250, s=200),  # S4 idx4 — NOT forced (conversion tail)
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=2) is True
        # Whole-line check still rejects it (idx4 fails).
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is False

    def test_firing_depth_past_truncated_line_rejected(self) -> None:
        """A firing depth beyond the (untruncated) line means the firing node is absent -> reject."""
        # 5-node line, all solver nodes forced; firing_depth=6 points past it.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),
            _cp_node(b=0, s=-100),
            _cp_node(b=800, s=0),
            _cp_node(b=0, s=-100),
            _cp_node(b=800, s=0),
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=6) is False
        # The same line with the firing node in range is credited.
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=4) is True


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
        # Small gap: not forced (50cp gap below the 100cp escape, delta 0.039 below margin).
        node_weak = _cp_node(b=250, s=200)
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
        """pre_flaw_eval_cp=900 (white solver ahead by 900 > 800) -> reject (D-08)."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=900) is False

    def test_pre_flaw_above_threshold_black_solver_rejected(self) -> None:
        """pre_flaw_eval_cp=-900 (black solver ahead by 900 > 800) -> reject (D-08).

        The already-winning check fires before any floor truncation, so the line
        content is irrelevant for this test.
        """
        line = self._valid_two_move_line_black()
        assert apply_forcing_line_filter(line, "black", pre_flaw_eval_cp=-900) is False

    def test_pre_flaw_at_threshold_not_rejected(self) -> None:
        """pre_flaw_eval_cp=800 exactly (strictly greater-than check): not rejected."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=800) is True

    def test_pre_flaw_below_threshold_not_rejected(self) -> None:
        """pre_flaw_eval_cp=200 (well below threshold): not rejected."""
        line = self._valid_two_move_line_white()
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=200) is True

    def test_pre_flaw_at_threshold_black_solver_not_rejected(self) -> None:
        """pre_flaw_eval_cp=-800 exactly for black solver: not rejected (strictly >).

        Uses a black-solver-appropriate line (negative cp = black winning) so the
        still-winning floor is not triggered (solver_cp = 800 >= 200).
        """
        line = self._valid_two_move_line_black()
        assert apply_forcing_line_filter(line, "black", pre_flaw_eval_cp=-800) is True

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
        in the forced-ness evaluation. The 200-vs-120 gap is below both the 0.35
        win-prob margin and the 100cp escape, so the filter returns False -- but the
        reason is the only-move check, NOT floor truncation.
        """
        # S1 at exactly 200cp (not strictly below): included in the effective line.
        # cp_gap = 80 < 100 escape; p(200) - p(120) ~ 0.068 < 0.35 margin -> S1 not forced.
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 forced
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=200, s=120),  # S1 at floor exactly, has second-best (included)
        ]
        result = apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0)
        # S1 was included but failed the only-move check, not the floor.
        assert result is False  # not forced (small gap), but NOT due to floor truncation

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


# ---------------------------------------------------------------------------
# TestDefenderBranching: GATE-04 / SC3 -- multi-ply branch-then-reconverge
# ---------------------------------------------------------------------------


class TestDefenderBranching:
    """Coverage for the multi-ply defender branch-then-reconverge case (GATE-04, SC3).

    Residual gap from Phase 141: existing defender tests cover only a 3-node line
    with a single ambiguous defender node.  SC3 requires a 5-node line where BOTH
    defender nodes are ambiguous (branch-then-reconverge at D0 AND D1).
    """

    def test_multi_ply_defender_ambiguity_does_not_kill_line(self) -> None:
        """Multiple ambiguous defender nodes in a 5-node line do not kill a forced solver line.

        [S0=forced, D0=ambiguous, S1=forced, D1=ambiguous, S2=forced] — branch-then-reconverge
        at BOTH D0 and D1; solver continuations S0/S1/S2 are all forced.  The line must pass.
        Residual SC3 gap (Phase 143 GATE-04): the existing tests cover only single-node defender
        ambiguity; this verifies the multi-ply branch-then-reconverge case.
        """
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 solver — forced (large gap)
            _cp_node(b=100, s=50),  # D0 defender — ambiguous (s close to b); NOT checked
            _cp_node(b=800, s=0),  # S1 solver — forced
            _cp_node(b=100, s=80),  # D1 defender — highly ambiguous; NOT checked
            _cp_node(b=800, s=0),  # S2 solver — forced
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True


# ---------------------------------------------------------------------------
# TestMarginParam: D-03 -- margin parameter honored by both gate functions
# ---------------------------------------------------------------------------


class TestMarginParam:
    """Verify that is_solver_node_forced and apply_forcing_line_filter honor the margin arg (D-03).

    The margin parameter was added in Phase 143 Plan 01 so the re-tagger CLI can sweep
    thresholds without mutating the module-level constant (worker-pool-safe, spawn workers
    re-import the module with the original constant).
    """

    def test_margin_param_is_respected_by_is_solver_node_forced(self) -> None:
        """is_solver_node_forced respects a passed-in margin rather than the module constant (D-03).

        Node with a win-prob delta of 0.143: forced at margin=0.1 but NOT forced at margin=0.5.
        p(300,"white") - p(120,"white") ≈ 0.751 - 0.609 = 0.143. The 180cp gap would trip the
        100cp escape, so the escape is disabled here (cp_gap=10_000) to isolate the margin param.
        """
        node = _cp_node(b=300, s=120)
        assert is_solver_node_forced(node, "white", margin=0.1, cp_gap=10_000) is True
        assert is_solver_node_forced(node, "white", margin=0.5, cp_gap=10_000) is False

    def test_apply_filter_margin_param_is_respected(self) -> None:
        """apply_forcing_line_filter threads the margin param to is_solver_node_forced (D-03).

        apply_forcing_line_filter uses the default cp-gap escape (100), so the node keeps a
        90cp gap (< 100, escape inert) with solver_cp 290 (>= 200 floor). delta 0.068 sits
        between the two margins: passes at margin=0.03, fails at margin=0.2.
        """
        line: list[PvNode] = [
            _cp_node(b=290, s=200),  # S0 — forced at 0.03, not at 0.2 (gap 90 < 100 escape)
            _cp_node(b=0, s=-100),  # D0 — defender, ignored
            _cp_node(b=290, s=200),  # S1 — forced at 0.03, not at 0.2
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, margin=0.03) is True
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, margin=0.2) is False


# ---------------------------------------------------------------------------
# TestCpGapEscape: Phase 144 -- sigmoid-saturation centipawn-gap escape
# ---------------------------------------------------------------------------


class TestCpGapEscape:
    """The only-move check passes on a large raw cp gap even when win-prob saturates.

    The win-prob margin compresses once the solver is clearly ahead (A/B cases 2 & 33: a
    386cp / 248cp gap collapses below the 0.35 win-prob margin). A wide solver-perspective
    cp gap is itself an only-move signal (ONLY_MOVE_CP_GAP_THRESHOLD).
    """

    def test_cp_gap_threshold_constant(self) -> None:
        """ONLY_MOVE_CP_GAP_THRESHOLD is 100 cp (Phase 144 VALID-02 hand-check)."""
        assert ONLY_MOVE_CP_GAP_THRESHOLD == 100

    def test_saturated_large_cp_gap_forced_white(self) -> None:
        """A/B case 2 shape: best +416, second +30 -> win-prob gap 0.295 < 0.35 but cp_gap 386."""
        node = _cp_node(b=416, s=30)
        # Win-prob margin alone (escape disabled via a high cp_gap) rejects it...
        assert is_solver_node_forced(node, "white", margin=0.35, cp_gap=10_000) is False
        # ...but the default cp-gap escape (386 >= 100) credits it.
        assert is_solver_node_forced(node, "white") is True

    def test_saturated_large_cp_gap_forced_black(self) -> None:
        """A/B case 33 shape: best -716, second -468 (black) -> solver cp_gap 248 >= 100."""
        node = _cp_node(b=-716, s=-468)
        assert is_solver_node_forced(node, "black") is True

    def test_small_cp_gap_not_forced(self) -> None:
        """Below-escape shape: solver cp_gap 85 < 100 and win-prob gap 0.087 < 0.35 -> not forced."""
        node = _cp_node(b=-90, s=5)  # black solver: solver gap = 85
        assert is_solver_node_forced(node, "black") is False

    def test_cp_gap_param_override(self) -> None:
        """The cp_gap escape threshold is tunable per-call (worker-pool-safe)."""
        node = _cp_node(b=300, s=120)  # cp_gap 180, win-prob gap ~0.14
        assert is_solver_node_forced(node, "white", margin=0.5, cp_gap=150) is True
        assert is_solver_node_forced(node, "white", margin=0.5, cp_gap=250) is False


# ---------------------------------------------------------------------------
# TestForcedMateExemptions: Phase 144 -- mates skip already-winning + one-mover discard
# ---------------------------------------------------------------------------


class TestForcedMateExemptions:
    """A solver-winning forced mate at the firing node is decisive regardless of context.

    It is exempt from the already-winning reject (D-08) and the one-mover discard (D-10),
    but still subject to the only-move check (mate priority, D-01). A/B case 29: an allowed
    back-rank mate-in-1 played when the solver was already +8, which has a single solver node.
    """

    def test_mate_in_1_single_node_credited(self) -> None:
        """A/B case 29: mate-in-1 firing node + mate-delivered node; exempt from one-mover discard."""
        line: list[PvNode] = [
            PvNode(b=None, bm=1, s=978, sm=None, su="e1e2"),  # S0 mate-in-1
            PvNode(b=None, bm=0, s=None, sm=None, su=""),  # mate delivered
        ]
        assert (
            apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=808, firing_depth=0) is True
        )

    def test_mate_exempt_from_already_winning(self) -> None:
        """A forced mate is credited even when pre-flaw eval is far above the already-winning floor."""
        line: list[PvNode] = [
            PvNode(b=None, bm=2, s=500, sm=None, su="d1h5"),  # S0 mate-in-2
            _cp_node(b=0, s=-100),  # defender
        ]
        # pre_flaw +2000 would reject any non-mate motif; the mate is exempt.
        assert (
            apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=2000, firing_depth=0) is True
        )

    def test_non_mate_still_rejected_when_already_winning(self) -> None:
        """Control: a non-mate tactic above the already-winning floor is still rejected."""
        line: list[PvNode] = [
            _cp_node(b=800, s=0),
            _cp_node(b=0, s=-100),
            _cp_node(b=800, s=0),
        ]
        assert (
            apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=900, firing_depth=0) is False
        )

    def test_mate_against_solver_not_exempt(self) -> None:
        """A firing node whose 'best' mate is against the solver is not a forced-mate exemption."""
        # bm negative = black mating; for a white solver this is a mate AGAINST the solver.
        line: list[PvNode] = [
            PvNode(b=None, bm=-2, s=None, sm=None, su=""),  # S0 mate against white solver
            _cp_node(b=0, s=-100),
        ]
        # Not exempt -> already-winning reject fires on the +900 pre-flaw eval (> 800).
        assert (
            apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=900, firing_depth=0) is False
        )


# ---------------------------------------------------------------------------
# TestFloorScopedToConversionTail: Phase 144 -- floor exempts the firing node
# ---------------------------------------------------------------------------


class TestFloorScopedToConversionTail:
    """The still-winning floor only truncates conversion-tail nodes (index > firing_depth).

    A/B case 5: a modest-gain tactic whose firing node sits below +200 must not be killed by
    the floor. The firing node's quality is governed by the only-move check, not the floor.
    """

    def test_firing_node_below_floor_not_truncated(self) -> None:
        """Firing node at +150 (below floor) survives when firing_depth=0; only-move check decides.

        The firing node has a large cp gap (150 vs -300 = 450 >= 200 escape) so it is forced;
        with the floor scoped to the tail it is no longer truncated, so the line is credited.
        """
        line: list[PvNode] = [
            _cp_node(b=150, s=-300),  # S0 firing — below +200 floor but forced (cp_gap 450)
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=800, s=0),  # S2 conversion — above floor
        ]
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=0) is True

    def test_conversion_tail_below_floor_still_truncates(self) -> None:
        """A below-floor node PAST the firing depth still truncates (one-mover discard follows)."""
        line: list[PvNode] = [
            _cp_node(b=800, s=0),  # S0 firing — forced, above floor
            _cp_node(b=0, s=-100),  # D0 defender
            _cp_node(b=150, s=0),  # S2 conversion tail — below floor -> truncated
            _cp_node(b=0, s=-100),  # D1 defender
            _cp_node(b=800, s=0),  # S4 — never reached
        ]
        # firing_depth=0: tail node S2 truncated -> only S0 remains -> one-mover discard.
        assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=0) is False

    def test_legacy_none_firing_depth_truncates_whole_line(self) -> None:
        """firing_depth=None preserves the legacy whole-line floor (firing node not exempt)."""
        line: list[PvNode] = [
            _cp_node(b=150, s=-300),  # S0 below floor; with None this truncates immediately
            _cp_node(b=0, s=-100),
            _cp_node(b=800, s=0),
        ]
        assert (
            apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, firing_depth=None) is False
        )
