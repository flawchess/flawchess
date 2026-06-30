"""Pure-math forcing-line gate for tactic crediting.

Implements the only-move gate (GATE-01, GATE-02) that determines whether a
stored PV-line blob represents a genuinely forced tactic sequence. Modeled on
the lichess-puzzler validity criteria (AGPL boundary: heuristics, constants,
and names only; no source copied).

Gate model:
  - Each solver node in the effective line must pass the only-move gate: the
    win-prob gap between the best and second-best move must exceed
    ONLY_MOVE_WIN_PROB_MARGIN. "Solver" is the tactic-delivering side; defender
    nodes have no uniqueness requirement (D-10).
  - Mate priority (D-01): only-best-is-mate forced; both-mates shorter
    distance forced; mate-in-1 is NEVER suppressed; else fall through to
    win-prob margin.
  - Already-winning reject (D-08): discard the motif if the pre-flaw position
    was already > ALREADY_WINNING_CP_THRESHOLD from the solver's perspective.
  - Still-winning floor (D-09): stop extending the line when the solver's
    best-move eval drops below STILL_WINNING_FLOOR_CP.
  - Trailing-only-move strip + one-mover discard (D-10): lines ending in
    trivial forced moves are stripped; single-solver-move lines are discarded.

Sign convention (D-05): cp values in the blob are white-perspective (matching
game_positions.eval_cp). The gate converts to side-to-move perspective at read
time via eval_utils helpers: eval_cp_to_expected_score(cp, solver_color).

Constant provenance:
  - ONLY_MOVE_WIN_PROB_MARGIN = 0.35 (D-07): lichess-puzzler's +0.7 margin in
    -1..+1 win-chance space equals +0.35 in our 0..1 win-prob space. Starting
    tunable value; final margin committed in Phase 144 (VALID-02).
  - ALREADY_WINNING_CP_THRESHOLD = 300 (D-08): lichess-puzzler already-winning
    reject (prev_score > Cp(300)).
  - STILL_WINNING_FLOOR_CP = 200 (D-09): lichess-puzzler cook_advantage floor
    (Cp(200)).

No I/O, no DB, stdlib + eval_utils only. The module is unit-testable in isolation
(zero engine, zero DB fixtures); see tests/services/test_forcing_line_gate.py.
This is the load-bearing property of Phase 141 success criterion #2.
"""

from typing import Literal, Sequence, TypedDict

from app.services.eval_utils import (
    LICHESS_K,  # noqa: F401 -- same sigmoid coefficient; imported to document dependency (D-07)
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)

# D-07: starting only-move margin (lichess-puzzler's +0.7 in -1..+1 win-chance space
# equals +0.35 in our 0..1 win-prob space). Treat as the provisional starting value;
# final margin committed in Phase 144 (VALID-02).
ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35

# D-08: reject the whole motif if the pre-flaw position was already > +300 cp
# from the solver's perspective (lichess-puzzler already-winning reject, prev_score > Cp(300)).
ALREADY_WINNING_CP_THRESHOLD: int = 300

# D-09: stop extending the line at the first solver node whose best-move eval drops
# below +200 cp from the solver's perspective (lichess-puzzler cook_advantage Cp(200)).
STILL_WINNING_FLOOR_CP: int = 200


class PvNode(TypedDict):
    """Per-node blob shape for allowed_pv_lines / missed_pv_lines (D-05).

    All cp values are white-perspective (matching game_positions.eval_cp).
    The gate converts to side-to-move perspective at read time.

    Keys:
        b:  best_cp -- centipawn eval of the best move, or None if the best
            move is a forced mate.
        bm: best_mate -- mate-in-N for the best move (positive = white is
            mating, negative = black is mating), or None if not a mate.
        s:  second_cp -- centipawn eval of the second-best move, or None if
            there is no legal second move or the second-best is a forced mate.
        sm: second_mate -- mate-in-N for the second-best move (same sign
            convention as bm), or None.
        su: second-best move in UCI notation (e.g. "e2e4"), or empty string
            if there is no legal second move.
    """

    b: int | None
    bm: int | None
    s: int | None
    sm: int | None
    su: str


# ---------------------------------------------------------------------------
# Private predicate helpers — each rule is its own small function (CLAUDE.md
# function-size discipline; nesting hard-cap 4).
# ---------------------------------------------------------------------------


def _is_already_winning(
    pre_flaw_eval_cp: int,
    solver_color: Literal["white", "black"],
) -> bool:
    """Return True if the pre-flaw position exceeded ALREADY_WINNING_CP_THRESHOLD (D-08).

    Args:
        pre_flaw_eval_cp: White-perspective centipawn eval at the flaw ply
            (game_positions.eval_cp at the position before the flaw move).
        solver_color: Color of the tactic-delivering side.

    Returns:
        True if the solver was already winning by more than
        ALREADY_WINNING_CP_THRESHOLD before the tactic (motif rejected).
    """
    solver_cp = pre_flaw_eval_cp if solver_color == "white" else -pre_flaw_eval_cp
    return solver_cp > ALREADY_WINNING_CP_THRESHOLD


def _resolve_mate_priority(
    node: PvNode,
    solver_color: Literal["white", "black"],
) -> bool | None:
    """Apply the mate-priority hierarchy (D-01) via eval_mate_to_expected_score.

    Returns:
        True  -- forced (best mate wins uniquely over second).
        False -- not forced (second mate has equal or shorter distance).
        None  -- no mate on the best move; fall through to win-prob margin.
    """
    bm = node["bm"]
    if bm is None:
        return None  # Best move is centipawn-scored; fall through.

    # Verify the best mate benefits the solver (should always be true in
    # well-formed tactic blobs, but guard against malformed data).
    if eval_mate_to_expected_score(bm, solver_color) != 1.0:
        return False  # Mate is against the solver; treat as not forced.

    # Mate-in-1 is never suppressed (D-01 guarantee), regardless of second.
    if abs(bm) == 1:
        return True

    sm = node["sm"]
    if sm is None:
        # Only the best move is a forced mate (second is cp or no second move).
        return True

    # Both moves are mates. Check if the second also benefits the solver.
    sm_wins_for_solver = eval_mate_to_expected_score(sm, solver_color) == 1.0
    if not sm_wins_for_solver:
        # Second mate is against solver; best wins unconditionally.
        return True

    # Both mates win for the solver: shorter distance (fewer moves) is forced.
    return abs(bm) < abs(sm)


def is_solver_node_forced(
    node: PvNode,
    solver_color: Literal["white", "black"],
) -> bool:
    """Return True if this solver node passes the only-move gate (D-07, GATE-01).

    First applies the mate-priority hierarchy (D-01) which covers all mate
    cases, then falls through to the centipawn win-prob margin. A node with
    no legal second move also passes (only-move by definition).

    Args:
        node: The PvNode blob entry. White-perspective cp values.
        solver_color: Color of the tactic-delivering side, used to flip
            white-perspective cp to side-to-move perspective.

    Returns:
        True if the solver had no practical alternative at this node.
    """
    # No second legal move: unconditionally forced (only-move).
    if node["s"] is None and node["sm"] is None:
        return True

    # Try mate-priority hierarchy (D-01); returns None if no mate on best move.
    mate_result = _resolve_mate_priority(node, solver_color)
    if mate_result is not None:
        return mate_result

    # Fall through: both moves are centipawn-scored. Apply win-prob margin.
    b = node["b"]
    s = node["s"]
    if b is None or s is None:
        # Malformed blob (mate/cp mismatch). Be conservative.
        return False

    p_best = eval_cp_to_expected_score(b, solver_color)
    p_second = eval_cp_to_expected_score(s, solver_color)
    return p_best - p_second > ONLY_MOVE_WIN_PROB_MARGIN


def _truncate_at_still_winning_floor(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
) -> list[PvNode]:
    """Stop extending the line at the first solver node below STILL_WINNING_FLOOR_CP (D-09).

    Solver nodes are at even indices (0-based); the line is assumed to start
    at a solver node. Defender nodes (odd indices) are always included up to
    the truncation point.

    Args:
        line: PvNode sequence starting at a solver ply.
        solver_color: Color of the tactic-delivering side.

    Returns:
        Nodes up to (but not including) the first out-of-floor solver node.
    """
    result: list[PvNode] = []
    for i, node in enumerate(line):
        if i % 2 == 0:  # Solver node.
            bm = node["bm"]
            b = node["b"]
            if bm is None and b is not None:
                # Non-mate: convert to solver-perspective and check floor.
                solver_cp = b if solver_color == "white" else -b
                if solver_cp < STILL_WINNING_FLOOR_CP:
                    break  # Tactic has fizzled; exclude this node and stop.
        result.append(node)
    return result


def _strip_trailing_only_moves(line: Sequence[PvNode]) -> list[PvNode]:
    """Strip trailing solver only-moves from the end of the line (D-10).

    A solver node is an "only-move" when it has no legal second move
    (s and sm both None). Trailing only-moves are stripped along with any
    subsequent nodes so the line ends on a solver node with a genuine second-best.

    Defender nodes (odd indices) are never evaluated for stripping; only
    ambiguity on the solver side matters (D-10).

    Args:
        line: PvNode sequence starting at a solver ply (solver nodes at even indices).

    Returns:
        Trimmed node list, possibly empty.
    """
    result = list(line)
    while result:
        # Find the last solver node (even index), scanning from the end.
        last_solver_idx = -1
        for i in range(len(result) - 1, -1, -1):
            if i % 2 == 0:
                last_solver_idx = i
                break
        if last_solver_idx < 0:
            break  # No solver nodes remain.

        last_solver = result[last_solver_idx]
        if last_solver["s"] is None and last_solver["sm"] is None:
            # Trailing only-move: strip this node and everything after it.
            result = result[:last_solver_idx]
        else:
            break  # Last solver has a genuine second-best; done stripping.

    return result


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
) -> bool:
    """Return True if the forcing-line gate passes for this PV blob (GATE-01, GATE-02).

    A motif is credited only when:
      1. The pre-flaw position was not already winning by a large margin (D-08).
      2. The effective line (after still-winning floor truncation and trailing
         only-move strip) has at least two solver nodes (one-mover discard, D-10).
      3. Every solver node in the effective line -- the firing node and all
         solver nodes leading to it -- passes the only-move gate (D-07).

    The line is assumed to start at a solver ply: index 0 = solver, 1 = defender,
    2 = solver, etc. Defender nodes have no uniqueness requirement (D-10).

    Args:
        line: Sequence of PvNode blobs for the PV line starting at a solver ply.
        solver_color: Color of the tactic-delivering side ("white" or "black").
        pre_flaw_eval_cp: White-perspective centipawn eval at the flaw position
            (game_positions.eval_cp at the flaw ply), used for the already-winning
            reject (D-08).

    Returns:
        True if the line passes all gate criteria and the motif should be credited.
        False if any criterion rejects the motif.
    """
    # D-08: already-winning reject.
    if _is_already_winning(pre_flaw_eval_cp, solver_color):
        return False

    # D-09: truncate at still-winning floor.
    truncated = _truncate_at_still_winning_floor(line, solver_color)

    # D-10: strip trailing solver only-moves.
    stripped = _strip_trailing_only_moves(truncated)

    # D-10: one-mover discard (need at least two solver nodes).
    solver_nodes = [node for i, node in enumerate(stripped) if i % 2 == 0]
    if len(solver_nodes) < 2:
        return False

    # D-07 / GATE-01: firing node AND every leading solver node must be forced.
    return all(is_solver_node_forced(node, solver_color) for node in solver_nodes)
