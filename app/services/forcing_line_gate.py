"""Pure-math forcing-line gate for tactic crediting.

Implements the only-move gate (GATE-01, GATE-02) that determines whether a
stored PV-line blob represents a genuinely forced tactic sequence. Modeled on
the lichess-puzzler validity criteria (AGPL boundary: heuristics, constants,
and names only; no source copied).

Gate model:
  - Each solver node up to and including the tactic's firing depth must pass the
    only-move gate: the win-prob gap between the best and second-best move must
    exceed ONLY_MOVE_WIN_PROB_MARGIN, OR the raw solver-perspective centipawn gap
    must reach ONLY_MOVE_CP_GAP_THRESHOLD (Phase 144 sigmoid-saturation escape — a
    large cp gap collapses to a tiny win-prob gap once the solver is clearly ahead).
    "Solver" is the tactic-delivering side; defender nodes have no uniqueness
    requirement (D-10). The conversion AFTER the tactic fires is exempt (Bug B): a
    winning position usually has several near-equal follow-up moves, which must not
    retroactively reject a tactic that already landed. firing_depth=None preserves
    the legacy whole-line check.
  - Mate priority (D-01): only-best-is-mate forced; both-mates shorter
    distance forced; mate-in-1 is NEVER suppressed; else fall through to
    win-prob margin. Phase 144: a solver-winning forced mate at the firing node is
    additionally exempt from the already-winning reject and the one-mover discard.
  - Already-winning reject (D-08): discard the motif if the pre-flaw position
    was already > ALREADY_WINNING_CP_THRESHOLD from the solver's perspective
    (forced mates exempt).
  - Still-winning floor (D-09): stop extending the line when a CONVERSION-TAIL
    solver node (index > firing_depth) drops below STILL_WINNING_FLOOR_CP; the
    firing node and the path to it are exempt (Phase 144).
  - Trailing-only-move strip + one-mover discard (D-10): lines ending in
    trivial forced moves are stripped; single-solver-move lines are discarded
    (forced mates exempt from the discard).

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

# Phase 144 (sigmoid-saturation fix): centipawn-gap escape for the only-move test.
# The win-prob margin compresses when the solver is already clearly ahead — a 3-4 pawn
# "only winning move" reads as a tiny win-prob gap once both moves sit on the flat top
# of the sigmoid (A/B case 2: a 386 cp gap collapses to 0.295 win-prob; case 33: 248 cp
# -> 0.085). A large raw best-vs-second centipawn gap is itself an only-move signal, so a
# node also passes when the solver-perspective cp gap reaches this threshold, regardless of
# the win-prob margin. 100 cp (lowered from the initial 200 in the VALID-02 A/B sweep): the
# user-28 hand-check found the ~1-pawn-only tactics dropped at 200 — clear forks/pins/skewers
# where the best move is a pawn better than the alternative (A/B cases 28/41/47/72) — to be
# genuine. A spot-check of ~20 newly-credited tags in the 100–150 cp-gap band surfaced no
# false alarms (a 1-pawn best-vs-second edge is a strong only-move signal in practice).
# Re-credits ~170 tags across the dev-28 population vs the 200 baseline. See
# reports/retag/ab-validation-2026-06-30.md.
ONLY_MOVE_CP_GAP_THRESHOLD: int = 100

# D-08: reject the whole motif if the pre-flaw position was already winning by a large
# margin from the solver's perspective (lichess-puzzler already-winning reject). Phase 144
# raised this from 300 to 600 cp, then to 800 cp in the VALID-02 A/B sweep: FlawChess tags
# real-game tactics (not puzzles), and a conversion tactic the player got to play while
# already winning (a hanging queen at +6.1, a clean skewer at +6.3 — A/B cases 14/98) is
# worth crediting. Every tag re-credited by the 600->800 raise is "missed" orientation (a
# tactic the player had available while ahead), i.e. exactly the conversion tactics we don't
# want to lose; the count plateaus near +10 (~20 tags on dev-28). 800 cp still filters truly
# crushing (+8+) mop-up. Forced mates are exempt entirely (see apply_forcing_line_filter).
ALREADY_WINNING_CP_THRESHOLD: int = 800

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
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
    cp_gap: int = ONLY_MOVE_CP_GAP_THRESHOLD,
) -> bool:
    """Return True if this solver node passes the only-move gate (D-07, GATE-01).

    First applies the mate-priority hierarchy (D-01) which covers all mate
    cases, then falls through to the centipawn win-prob margin OR the raw
    centipawn-gap escape. A node with no legal second move also passes
    (only-move by definition).

    Args:
        node: The PvNode blob entry. White-perspective cp values.
        solver_color: Color of the tactic-delivering side, used to flip
            white-perspective cp to side-to-move perspective.
        margin: Win-probability gap threshold (default: ONLY_MOVE_WIN_PROB_MARGIN).
            Passed through to the cp comparison so callers can tune the threshold
            without mutating the module constant (D-03, worker-pool-safe).
        cp_gap: Centipawn-gap escape threshold (default: ONLY_MOVE_CP_GAP_THRESHOLD).
            The win-prob margin saturates when the solver is already clearly ahead, so a
            large solver-perspective best-vs-second cp gap also counts as forced.

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
    if p_best - p_second > margin:
        return True

    # Sigmoid-saturation escape (Phase 144): when the solver is already clearly ahead the
    # win-prob gap collapses even for a large centipawn gap, so a wide raw cp gap between
    # best and second-best is itself an only-move signal (A/B cases 2 & 33).
    solver_b = b if solver_color == "white" else -b
    solver_s = s if solver_color == "white" else -s
    return solver_b - solver_s >= cp_gap


def _truncate_at_still_winning_floor(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    firing_depth: int | None = None,
) -> list[PvNode]:
    """Stop extending the line at the first conversion-tail solver node below the floor (D-09).

    Solver nodes are at even indices (0-based); the line is assumed to start
    at a solver node. Defender nodes (odd indices) are always included up to
    the truncation point.

    Phase 144: the floor only truncates the CONVERSION TAIL (solver nodes at index >
    firing_depth). The firing node and the path leading to it (index <= firing_depth) are
    always kept — their quality is governed by the only-move margin, not the floor. The
    floor exists to drop fizzled conversion moves, not to reject a tactic whose firing eval
    is modest (A/B case 5: a ~1-pawn attraction was killed because the firing node itself
    sat below +200). firing_depth=None preserves the legacy whole-line floor check.

    Args:
        line: PvNode sequence starting at a solver ply.
        solver_color: Color of the tactic-delivering side.
        firing_depth: Detector tactic depth (node index of the firing move); nodes at
            index <= firing_depth are exempt from the floor. None checks every solver node.

    Returns:
        Nodes up to (but not including) the first out-of-floor conversion-tail solver node.
    """
    result: list[PvNode] = []
    for i, node in enumerate(line):
        past_firing = firing_depth is None or i > firing_depth
        if i % 2 == 0 and past_firing:  # Conversion-tail solver node.
            bm = node["bm"]
            b = node["b"]
            if bm is None and b is not None:
                # Non-mate: convert to solver-perspective and check floor.
                solver_cp = b if solver_color == "white" else -b
                if solver_cp < STILL_WINNING_FLOOR_CP:
                    break  # Conversion has fizzled; exclude this node and stop.
        result.append(node)
    return result


def _is_forced_mate_firing(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    firing_depth: int | None,
) -> bool:
    """Return True if the firing node delivers a forced mate for the solver (Phase 144).

    A solver-winning forced mate is decisive regardless of the prior eval or the number of
    solver moves, so it is exempt from the already-winning reject (D-08) and the one-mover
    discard (D-10) — both of which would otherwise kill a legitimate allowed/missed mate
    (A/B case 29: a back-rank mate-in-1 played when already +8, which has only one solver
    node). The only-move check still applies to the firing node (mate priority, D-01).

    The firing node is at index firing_depth (the detector's tactic depth); None defaults
    to index 0 (mate motifs fire at depth 0 in practice).
    """
    idx = firing_depth if firing_depth is not None else 0
    if idx < 0 or idx >= len(line):
        return False
    bm = line[idx]["bm"]
    return bm is not None and eval_mate_to_expected_score(bm, solver_color) == 1.0


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


def _solver_nodes_through_firing_depth(
    line: Sequence[PvNode],
    firing_depth: int | None,
) -> list[PvNode]:
    """Return the solver nodes whose forcedness must be verified (Bug B, D-07).

    Solver nodes are at even indices (0-based). node index i corresponds to the
    detector's tactic depth i (half-moves from the firing position).

    firing_depth=None preserves the legacy whole-line behavior (every solver node).
    When set, only solver nodes at index <= firing_depth are returned: the firing
    node and the solver moves leading to it. The follow-up conversion (deeper solver
    nodes) is excluded so a tactic that has already fired and won material is not
    rejected just because the technical conversion has multiple winning paths.
    """
    if firing_depth is None:
        return [node for i, node in enumerate(line) if i % 2 == 0]
    return [node for i, node in enumerate(line) if i % 2 == 0 and i <= firing_depth]


def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
    firing_depth: int | None = None,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> bool:
    """Return True if the forcing-line gate passes for this PV blob (GATE-01, GATE-02).

    A motif is credited only when:
      1. The pre-flaw position was not already winning by a large margin (D-08).
      2. The effective line (after still-winning floor truncation and trailing
         only-move strip) has at least two solver nodes (one-mover discard, D-10).
      3. Every solver node up to and including the firing depth -- the firing node
         and all solver nodes leading to it -- passes the only-move gate (D-07).
         The conversion AFTER the tactic fires is NOT required to be forced (Bug B):
         once material is won, the technical follow-up commonly has several
         near-equal winning moves, which must not retroactively reject the tactic.

    The line is assumed to start at a solver ply: index 0 = solver, 1 = defender,
    2 = solver, etc. Defender nodes have no uniqueness requirement (D-10).

    Args:
        line: Sequence of PvNode blobs for the PV line starting at a solver ply.
        solver_color: Color of the tactic-delivering side ("white" or "black").
        pre_flaw_eval_cp: White-perspective centipawn eval at the flaw position
            (game_positions.eval_cp at the flaw ply), used for the already-winning
            reject (D-08).
        firing_depth: The detector's tactic depth (half-moves from the firing
            position; node index i == depth i). Only solver nodes at index
            <= firing_depth must be forced. None (default) preserves the legacy
            whole-line check; production passes the detected depth so the conversion
            tail is exempt from the only-move requirement.
        margin: Win-probability gap threshold forwarded to every is_solver_node_forced
            call (default: ONLY_MOVE_WIN_PROB_MARGIN). Lets the re-tagger CLI sweep
            different thresholds without mutating the module constant (D-03,
            worker-pool-safe).

    Returns:
        True if the line passes all gate criteria and the motif should be credited.
        False if any criterion rejects the motif.
    """
    # Phase 144: a solver-winning forced mate is decisive — exempt it from the
    # already-winning reject (D-08) and the one-mover discard (D-10). A forced mate stays
    # subject to the only-move check on its firing node (mate priority, D-01).
    forced_mate = _is_forced_mate_firing(line, solver_color, firing_depth)

    # D-08: already-winning reject (forced mates exempt).
    if not forced_mate and _is_already_winning(pre_flaw_eval_cp, solver_color):
        return False

    # D-09: truncate at still-winning floor (conversion tail only — firing node exempt).
    truncated = _truncate_at_still_winning_floor(line, solver_color, firing_depth)

    # D-10: strip trailing solver only-moves.
    stripped = _strip_trailing_only_moves(truncated)

    # D-10: one-mover discard (need at least two solver nodes; forced mates exempt — a
    # mate-in-1 legitimately has a single solver move).
    solver_nodes = [node for i, node in enumerate(stripped) if i % 2 == 0]
    if not forced_mate and len(solver_nodes) < 2:
        return False

    # Bug B: the firing node must survive the still-winning-floor truncation. If the
    # detector fired at a depth past the floor-truncated line, the tactic fizzled
    # before it landed -> reject. Compared against `truncated` (not `stripped`) so a
    # firing node removed only by the trailing only-move strip -- which is a forced
    # move and would have passed anyway -- does not cause a false reject. A None
    # firing_depth skips this (legacy whole-line check).
    if firing_depth is not None and firing_depth >= len(truncated):
        return False

    # D-07 / GATE-01: every solver node through the firing depth must be forced.
    relevant = _solver_nodes_through_firing_depth(stripped, firing_depth)
    if not relevant:
        return False
    return all(is_solver_node_forced(node, solver_color, margin) for node in relevant)
