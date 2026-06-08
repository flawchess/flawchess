"""Flaw-detection + classification service for Phase 105 (SEED-036).

Derives per-ply flaw severity and attribution tags from stored Stockfish evals.
No I/O, no DB — the module is a pure Python transform over already-loaded ORM objects.
See tests/services/test_flaws_service.py for unit tests.

Two output types:
  list[FlawRecord]   analyzed game — one entry per user mistake or blunder
  GameNotAnalyzed    chess.com / unanalyzed lichess game (< 90% eval coverage)

Note: inaccuracies are detected internally (for counts and the oracle test) but are
NOT emitted as FlawRecord items. Only mistakes and blunders appear in the returned
list. An inaccuracy-only analyzed game returns an empty list — distinct from
GameNotAnalyzed. See the 2026-06-05 amendment in 105-01-PLAN.md.
"""

from __future__ import annotations

import io
from typing import Literal, TypedDict

import chess
import chess.pgn
import sentry_sdk

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.normalization import parse_base_and_increment
from app.services.openings_service import derive_user_result

# ---------------------------------------------------------------------------
# Named constants — no magic numbers (CLAUDE.md)
# ---------------------------------------------------------------------------

# Lichess-aligned severity thresholds on the [0,1] ES scale.
# Lichess uses [−1, +1] winningChances with cutoffs 0.10/0.20/0.30; our scale
# is (winningChances + 1) / 2, so thresholds halve. See CONTEXT.md §Severity.
INACCURACY_DROP: float = 0.05
MISTAKE_DROP: float = 0.10
BLUNDER_DROP: float = 0.15

# Mate Option B: map mate eval to ±1000 cp before the sigmoid (CONTEXT.md §Mate).
# Do NOT use eval_mate_to_expected_score (hard 1.0/0.0) for drop math — that
# function is for endgame span averaging and would mis-size mate transitions.
MATE_CP_EQUIVALENT: int = 1000

# Eval coverage gate: fraction of plies with non-null eval required for "analyzed".
# The final ply always has null eval (zobrist.py: no move annotated), so a fully-
# analyzed 80-ply game scores 80/81 ≈ 98.8% — comfortably above this threshold.
EVAL_COVERAGE_MIN: float = 0.90

# Impact ladder thresholds (flaw-tag-definitions.md §Impact).
# Outcome-independent: computed from es_before/es_after only, never the game result.
FROM_WINNING_ES: float = 0.85  # squandered entry (>= 85%: overwhelming advantage)
WINNING_LINE_ES: float = 0.70  # reversed entry (>= 70%: clearly winning, ~+2.3 eval)
LOSING_LINE_ES: float = 0.30  # reversed exit (<= 30%: clearly losing, ~−2.3 eval)
SQUANDERED_EXIT_ES: float = 0.60  # squandered exit (<= 60%: erased back to roughly even)

# Tempo thresholds — relative to base_time_seconds (RESEARCH §Pattern 6).
# [ASSUMED] initial values; tunable once real data is available.
TIME_PRESSURE_CLOCK_FRACTION: float = 0.05  # < 5% of base = low clock
HASTY_MOVE_FRACTION: float = 0.01  # < 1% of base = fast move on comfortable clock
TIME_PRESSURE_CLOCK_ABS_SECONDS: float = 30.0  # fallback when base_time unknown
HASTY_MOVE_ABS_SECONDS: float = 5.0  # fallback when base_time unknown

# Oracle closeness tolerance for sanity test against Lichess game-level columns.
# [ASSUMED] — allows ≤2 off per color per severity (mate-handling divergence).
SANITY_TOLERANCE: int = 2

# ---------------------------------------------------------------------------
# Literal type aliases (CLAUDE.md §Type safety: Literal for fixed-value fields)
# ---------------------------------------------------------------------------

FlawSeverity = Literal["inaccuracy", "mistake", "blunder"]
FlawTag = Literal[
    "miss",
    "lucky",
    "reversed",
    "squandered",
    "low-clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame",
]
TempoTag = Literal["low-clock", "hasty", "unrushed"]

# ---------------------------------------------------------------------------
# TypedDict output contract (CONTEXT.md §Output contract; zobrist.py PlyData style)
# ---------------------------------------------------------------------------


class FlawRecord(TypedDict):
    ply: int  # half-move number (0-indexed)
    fen: str  # board_fen() of the position BEFORE the flawed move (piece placement
    # only) — so the Flaws-tab miniboard renders the decision point and move_san
    # resolves to its from/to arrow squares
    side: Literal["white", "black"]  # mover who made the flawed move
    severity: FlawSeverity
    tags: list[FlawTag]  # ordered, additive, orthogonal (populated in plan 02)
    es_before: float  # mover-POV ES before the flaw
    es_after: float  # mover-POV ES after the flaw
    move_san: str | None  # SAN from positions[N].move_san


class GameNotAnalyzed(TypedDict):
    reason: Literal["no_engine_analysis"]
    eval_coverage: float  # fraction 0.0–1.0


class SeverityCounts(TypedDict):
    """Per-game severity counts over the USER's moves (Phase 106, LIBG-08).

    Unlike the FlawRecord list (mistakes + blunders only), this carries all
    three tiers including the inaccuracy count — which is never exposed via
    classify_game_flaws (the kernel emits M+B only). See RESEARCH Pitfall 3:
    the I count must NOT be derived from the M+B FlawRecord set.
    """

    inaccuracy: int
    mistake: int
    blunder: int


GameFlawsResult = list[FlawRecord] | GameNotAnalyzed

# Internal type for the all-moves classification pass result per ply
_MoveEntry = tuple[Literal["white", "black"], FlawSeverity | None, float, float]

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ply_to_es(
    pos: GamePosition,
    mover_color: Literal["white", "black"],
) -> float | None:
    """Return mover-POV ES for this ply, or None if eval unavailable.

    Option B mate: maps mate to ±MATE_CP_EQUIVALENT cp before sigmoid.
    Do NOT call eval_mate_to_expected_score here — that returns hard 1.0/0.0
    and was built for endgame span averaging, not per-ply drop math (Pitfall 3
    in RESEARCH: mis-sizes mate transitions, would always flag mate-adjacent
    moves as blunders).
    """
    if pos.eval_mate is not None:
        cp_equiv = MATE_CP_EQUIVALENT if pos.eval_mate > 0 else -MATE_CP_EQUIVALENT
        return eval_cp_to_expected_score(cp_equiv, mover_color)
    if pos.eval_cp is not None:
        return eval_cp_to_expected_score(pos.eval_cp, mover_color)
    return None


def _classify_severity(drop: float) -> FlawSeverity | None:
    """Map a mover-POV ES drop to a severity label, or None if below threshold.

    Highest band wins (CONTEXT.md §Severity). All thresholds are boundary-inclusive.
    """
    if drop >= BLUNDER_DROP:
        return "blunder"
    if drop >= MISTAKE_DROP:
        return "mistake"
    if drop >= INACCURACY_DROP:
        return "inaccuracy"
    return None


def _compute_eval_coverage(positions: list[GamePosition]) -> float:
    """Fraction of positions with non-null eval_cp or eval_mate (0.0–1.0).

    The final position always has null eval (no move annotation), which is expected
    and counts against coverage — but for a fully-analyzed game the fraction is
    (N-1)/N which is well above the 0.90 threshold. No special case needed.
    """
    if not positions:
        return 0.0
    n_with_eval = sum(1 for p in positions if p.eval_cp is not None or p.eval_mate is not None)
    return n_with_eval / len(positions)


def _recompute_fen_map(pgn: str) -> dict[int, str]:
    """Return {ply: board_fen()} for every ply by replaying the PGN with python-chess.

    Uses board_fen() (piece placement only — CLAUDE.md §Chess logic: never board.fen()
    which includes castling/en passant metadata). Returns empty dict on parse failure,
    or a partial map if replay fails mid-game (callers fall back to fen="" per ply).
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return {}
    board = game.board()
    fens: dict[int, str] = {0: board.board_fen()}
    try:
        for ply, node in enumerate(game.mainline(), start=1):
            board.push(node.move)
            fens[ply] = board.board_fen()
    except (ValueError, AssertionError) as exc:
        # WR-03 fix: this PGN already parsed cleanly at import time (its positions
        # and evals are stored), so a replay failure here is a genuine data
        # inconsistency, not expected user-input noise. Capture it — otherwise
        # every later flaw silently falls back to fen="" via fen_map.get(n, "").
        sentry_sdk.set_context("flaws", {"stage": "fen_recompute", "failed_at_ply": len(fens)})
        sentry_sdk.capture_exception(exc)
    return fens


def _run_all_moves_pass(
    positions: list[GamePosition],
) -> dict[int, _MoveEntry]:
    """Classify every ply for both colors — required for miss/unpunished tag adjacency checks.

    Returns {ply_N: (mover_color, severity|None, es_before, es_after)} for
    N in range(1, len(positions)). Plies where either ES is None (interior null
    eval — Pitfall 4) are skipped and not included in the dict.

    ES semantics (eval-AFTER landmine, Pitfall 1):
        positions[N].eval_cp = eval AFTER move N was played.
        ES_before = _ply_to_es(positions[N-1], mover)  # board before mover plays move N
        ES_after  = _ply_to_es(positions[N],   mover)  # board after mover plays move N
    """
    all_moves: dict[int, _MoveEntry] = {}
    for n in range(1, len(positions)):
        mover: Literal["white", "black"] = "white" if n % 2 == 0 else "black"
        es_before = _ply_to_es(positions[n - 1], mover)
        es_after = _ply_to_es(positions[n], mover)
        if es_before is None or es_after is None:
            # Skip plies with missing eval (Pitfall 4: interior null)
            continue
        drop = es_before - es_after
        severity = _classify_severity(drop)
        all_moves[n] = (mover, severity, es_before, es_after)
    return all_moves


def _build_flaw_record(
    n: int,
    mover: Literal["white", "black"],
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    fen_map: dict[int, str],
    positions: list[GamePosition],
) -> FlawRecord:
    """Build a single FlawRecord for the mover's mistake/blunder at ply N."""
    # `n` is the 0-indexed half-move of the flawed move (positions[n].move_san is
    # the move played FROM ply n — see zobrist.py). fen_map[k] is the board AFTER
    # k half-moves (fen_map[0] = start), so the position BEFORE the flawed move is
    # fen_map[n] (n half-moves already played), NOT fen_map[n - 1]. Using n - 1
    # rendered the miniboard one ply too early (decision point off by one move).
    # This makes the miniboard show the decision point and lets the frontend
    # resolve move_san → arrow squares.
    return FlawRecord(
        ply=n,
        fen=fen_map.get(n, ""),
        side=mover,
        severity=severity,
        tags=[],
        es_before=es_before,
        es_after=es_after,
        move_san=positions[n].move_san,
    )


def _move_time(
    positions: list[GamePosition],
    n: int,
    increment: float,
) -> float | None:
    """Return move time in seconds for the mover at ply N, or None if unavailable.

    Same-side clock is two plies back (Pitfall 2 in RESEARCH — N-1 is the
    opponent's clock). Returns None for first moves (n < 2), when either
    clock is null, or when the computed time is negative (a clock anomaly).

    Formula: prev_same_side_clock - clock_after_move + increment
    (increment is added when the move is completed, so clock_after already
    reflects the pre-increment state before adding increment back).
    """
    if n < 2:
        return None
    prev_clock = positions[n - 2].clock_seconds
    curr_clock = positions[n].clock_seconds
    if prev_clock is None or curr_clock is None:
        return None
    move_time = prev_clock - curr_clock + increment
    # WR-05 fix: a negative move time is physically impossible (the player's own
    # clock cannot gain more than the increment between their moves) and signals
    # inconsistent/corrupt clock data. Treat it as unavailable rather than letting
    # it satisfy `move_time < fast_move_threshold` and mislabel the move as hasty.
    if move_time < 0:
        return None
    return move_time


def _classify_tempo(
    move_time: float | None,
    clock_after: float | None,
    base_time: int | None,
) -> TempoTag | None:
    """Return at most one tempo tag for a flaw, or None when clock data is unavailable.

    Returns one of {low-clock, hasty, unrushed}, or None when clock_after or
    move_time is unavailable (no misleading fallback — per the at-most-one rule in
    flaw-tag-naming.md §"Structural change").

    Priority: low-clock > hasty > unrushed.

    Relative thresholds are used when base_time is available (relative-to-base-clock
    is context-aware — a 5s move is hasty in classical but normal in bullet).
    Absolute fallback values are used when base_time is absent or zero.
    All threshold values are [ASSUMED] initial defaults; tunable on-the-fly.
    """
    if clock_after is None or move_time is None:
        return None

    # Pick thresholds — relative when base_time available (guard against div-by-zero)
    if base_time and base_time > 0:
        low_clock_threshold = base_time * TIME_PRESSURE_CLOCK_FRACTION
        fast_move_threshold = base_time * HASTY_MOVE_FRACTION
    else:
        low_clock_threshold = TIME_PRESSURE_CLOCK_ABS_SECONDS
        fast_move_threshold = HASTY_MOVE_ABS_SECONDS

    if clock_after < low_clock_threshold:
        return "low-clock"
    if move_time < fast_move_threshold:
        return "hasty"
    return "unrushed"


def _is_miss(n: int, all_moves: dict[int, _MoveEntry]) -> bool:
    """Return True if opponent's move at ply N-1 was a mistake or blunder.

    Requires the all-moves classification pass covering both colors (Pitfall 5).
    A miss means the user's error followed immediately after an opponent error,
    suggesting the user may have been rattled or exploiting what they thought
    was a free recovery.
    """
    opponent_n = n - 1
    if opponent_n < 1:
        return False
    entry = all_moves.get(opponent_n)
    if entry is None:
        return False
    opp_severity = entry[1]
    return opp_severity in ("mistake", "blunder")


def _is_unpunished(
    n: int,
    all_moves: dict[int, _MoveEntry],
    severity: FlawSeverity,
    user_result: Literal["win", "draw", "loss"],
) -> bool:
    """Return True when a user BLUNDER at ply N went UNPUNISHED by the opponent.

    lucky = user's blunder that the opponent did NOT capitalize on, so the
    user got away with it. Only applies to blunders (Pitfall 6 in RESEARCH —
    applying to inaccuracies and mistakes would produce a noise-heavy flood).

    A blunder is "unpunished" when the opponent's immediate reply at N+1 was itself
    a mistake or blunder: the user's expected score dropped on their blunder, then
    recovered because the opponent failed to find the punishing line. (ES is
    zero-sum across colors, so an opponent error == the user's eval bouncing back.)

    Bug fix (2026-06-07): this previously returned the INVERSE — it tagged a
    blunder whenever the opponent did NOT err, i.e. when the opponent played a fine
    move and *capitalized*. That fired on the common case (opponents usually reply
    sensibly), tagging ~42% of all blunders as "lucky escapes" and, worst of all,
    flagging fatal blunders where the opponent calmly played the winning/mating
    continuation (e.g. lichess 19BMxZnj: blunder into mate, opponent plays the
    mate move, user resigns). A lucky escape is the opposite: the opponent slipped.

    End-of-game (no opponent move at N+1) counts as a lucky escape only when the
    user did NOT lose — a blunder followed by the user resigning or flagging is a
    loss, not an escape (the opponent never had to punish because the user
    conceded). user_result != "loss" keeps the genuine end-of-game escapes (the
    blunder was actually mate, the game drew, or the opponent resigned anyway).
    """
    if severity != "blunder":
        return False
    opp_n = n + 1
    entry = all_moves.get(opp_n)
    if entry is None:
        # End of game — a lucky escape only if the user didn't lose (a loss here
        # means the user resigned/flagged right after blundering, not an escape).
        return user_result != "loss"
    opp_severity = entry[1]
    # Unpunished == the opponent erred in reply, letting the user's eval recover.
    return opp_severity in ("mistake", "blunder")


def _classify_impact(es_before: float, es_after: float) -> Literal["reversed", "squandered"] | None:
    """Most-severe-wins outcome-independent impact ladder (flaw-tag-definitions.md §Impact).

    At most one tag; most-severe is checked first so a 0.90→0.25 swing returns only
    "reversed" (not "squandered"). Replaces the prior outcome-dependent helper that
    keyed off the final game result — impact is now result-independent (computed
    entirely from es_before/es_after).

    Boundary convention: >= entry / <= exit (inclusive on both ends, per doc prose
    "or below"; differs from the prior strict < exit — Pitfall 4).

    Rungs:
      reversed   — es_before >= WINNING_LINE_ES (0.70) AND es_after <= LOSING_LINE_ES (0.30)
                   Full reversal: winning game turned into a losing one.
      squandered — es_before >= FROM_WINNING_ES (0.85) AND es_after <= SQUANDERED_EXIT_ES (0.60)
                   AND not reversed. Overwhelming advantage erased back to roughly even.
    """
    if es_before >= WINNING_LINE_ES and es_after <= LOSING_LINE_ES:
        return "reversed"
    if es_before >= FROM_WINNING_ES and es_after <= SQUANDERED_EXIT_ES:
        return "squandered"
    return None


def _phase_tag(phase: int | None) -> FlawTag:
    """Map the GamePosition.phase integer (0/1/2) to a phase FlawTag.

    Defaults to middlegame for unknown/null phase values (most positions
    are middlegame; this avoids spurious opening or endgame tags).
    """
    if phase == 0:
        return "opening"
    if phase == 2:
        return "endgame"
    return "middlegame"


def _build_tags(
    n: int,
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    positions: list[GamePosition],
    all_moves: dict[int, _MoveEntry],
    user_result: Literal["win", "draw", "loss"],
    increment: float,
    base_time: int | None,
) -> list[FlawTag]:
    """Assemble the ordered attribution tags list for one user flaw at ply N.

    Tag order: impact (reversed/squandered), miss, lucky, phase, tempo.
    Tags are additive and orthogonal. At most one impact tag and at most one tempo
    tag are present (tempo absent when clock data is unavailable).

    NOTE: user_result is still required here — _is_unpunished (lucky
    end-of-game rule) reads it. Only the impact branch no longer uses it.
    """
    tags: list[FlawTag] = []

    impact = _classify_impact(es_before, es_after)
    if impact is not None:
        tags.append(impact)

    if _is_miss(n, all_moves):
        tags.append("miss")

    if _is_unpunished(n, all_moves, severity, user_result):
        tags.append("lucky")

    tags.append(_phase_tag(positions[n].phase))

    clock_after = positions[n].clock_seconds
    move_time = _move_time(positions, n, increment)
    tempo = _classify_tempo(move_time, clock_after, base_time)
    if tempo is not None:
        tags.append(tempo)

    return tags


def _resolve_increment(game: Game) -> float:
    """Return the increment in seconds for this game.

    Single source of truth for increment resolution (Phase 109 — extracted
    from the inline block in classify_game_flaws to enable reuse by the
    eval chart builder in library_service.py).

    Priority:
    1. game.increment_seconds when explicitly stored (already parsed at import time).
    2. Parsed from game.time_control_str via parse_base_and_increment.
    3. 0.0 fallback (no increment info available).
    """
    if game.increment_seconds is not None:
        return game.increment_seconds
    if game.time_control_str:
        _, parsed_inc = parse_base_and_increment(game.time_control_str)
        if parsed_inc is not None:
            return parsed_inc
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_game_flaws(
    game: Game,
    positions: list[GamePosition],
) -> GameFlawsResult:
    """Derive all user flaws from stored per-ply evals.

    Args:
        game: Game row with result, user_color, base_time_seconds,
              increment_seconds, pgn.
        positions: All GamePosition rows for this game, ordered by ply ASC.
            Load via flaws_repository.fetch_game_positions_ordered.

    Returns:
        list[FlawRecord] for analyzed games — one entry per user mistake or
        blunder (inaccuracies are count-only, NOT emitted). An inaccuracy-only
        analyzed game returns an empty list, distinct from GameNotAnalyzed.

        GameNotAnalyzed when eval coverage < EVAL_COVERAGE_MIN (chess.com games,
        unanalyzed lichess games). Never returns a false zero-flaw game (LIBG-02).
    """
    # Coverage gate: return early for unanalyzed games (chess.com / no evals)
    coverage = _compute_eval_coverage(positions)
    if coverage < EVAL_COVERAGE_MIN:
        return GameNotAnalyzed(reason="no_engine_analysis", eval_coverage=coverage)

    # Build FEN map once and reuse for all flaw records
    fen_map = _recompute_fen_map(game.pgn)

    # All-moves pass: classify both colors (needed for miss/unpunished adjacency)
    all_moves = _run_all_moves_pass(positions)

    # Resolve increment once via shared helper (Phase 109: single source of truth).
    increment = _resolve_increment(game)

    user_result = derive_user_result(game.result, game.user_color)

    # Emit FlawRecords for user's mistakes and blunders only (inaccuracies are count-only)
    user_color = game.user_color
    flaws: list[FlawRecord] = []
    for n, (mover, severity, es_before, es_after) in all_moves.items():
        if mover != user_color:
            continue
        if severity not in ("mistake", "blunder"):
            # Inaccuracies are count-only per the 2026-06-05 amendment
            continue
        flaw = _build_flaw_record(n, mover, severity, es_before, es_after, fen_map, positions)
        flaw["tags"] = _build_tags(
            n,
            severity,
            es_before,
            es_after,
            positions,
            all_moves,
            user_result,
            increment,
            game.base_time_seconds,
        )
        flaws.append(flaw)

    return flaws


def count_game_severities(
    game: Game,
    positions: list[GamePosition],
) -> SeverityCounts | GameNotAnalyzed:
    """Count per-game inaccuracy/mistake/blunder over the USER's moves.

    The count-only sibling of classify_game_flaws. It exposes the inaccuracy
    count that the FlawRecord path deliberately omits (the kernel emits M+B only),
    so the Games-list card can show full B/M/I per game (LIBG-08). No tags, no
    FEN recompute — pure tally.

    Args:
        game: Game row (only user_color is read here).
        positions: All GamePosition rows for this game, ordered by ply ASC.

    Returns:
        SeverityCounts {inaccuracy, mistake, blunder} restricted to the user's
        moves (mover == game.user_color, parity per _run_all_moves_pass) for an
        analyzed game.

        GameNotAnalyzed when eval coverage < EVAL_COVERAGE_MIN — the IDENTICAL
        gate as classify_game_flaws, so analyzed/unanalyzed classification is
        consistent across the two entry points (chess.com / unanalyzed lichess
        games surface "no engine analysis" rather than a false 0/0/0).
    """
    # Coverage gate: identical to classify_game_flaws (same shape on miss).
    coverage = _compute_eval_coverage(positions)
    if coverage < EVAL_COVERAGE_MIN:
        return GameNotAnalyzed(reason="no_engine_analysis", eval_coverage=coverage)

    # Reuse the kernel's per-ply classification pass — no severity-math fork.
    all_moves = _run_all_moves_pass(positions)

    user_color = game.user_color
    counts = SeverityCounts(inaccuracy=0, mistake=0, blunder=0)
    for mover, severity, _es_before, _es_after in all_moves.values():
        if mover != user_color:
            continue
        if severity is None:
            continue
        counts[severity] += 1
    return counts
