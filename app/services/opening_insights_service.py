"""Opening insights service.

Single public entry point: compute_insights(session, user_id, request).
Pipeline: query_opening_transitions (per color) -> classify + severity ->
attribute (deepest Opening / lineage walk / drop on no match) ->
dedupe within color section and across continuations -> rank (Wilson 95%
bound, direction-aware) -> partition per section: up to 10 cards at p < 0.05
(medium or high confidence), current before older games; a section with none falls
back to its top 4 low-confidence "leaning" findings (D-38) -> MG-entry eval on the
card findings only.
No precompute, no caching — partial-index-backed query keeps even
Hikaru-class users <1 s.
"""

import ctypes
import datetime
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import SimpleNamespace  # Adapter for resulting-position W/D/L
from typing import Any, Literal

import chess
import chess.polyglot
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opening import Opening
from app.repositories.openings_repository import (
    query_opening_transitions,
    query_openings_by_hashes,
    query_resulting_position_wdl,  # Resulting-position WDL
    query_transition_prefixes,
)
from app.repositories.stats_repository import (
    OpeningPhaseEntryMetrics,
    query_opening_phase_entry_metrics_batch,
)
from app.schemas.opening_insights import (
    OpeningInsightFinding,
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.services.opening_eval import finalize_opening_eval
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
    OPENING_INSIGHTS_MAJOR_EFFECT as MAJOR_EFFECT,
    OPENING_INSIGHTS_MINOR_EFFECT as MINOR_EFFECT,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)
from app.services.repertoire_recency import (
    CurrentCutoffs,
    is_current,
    resolve_current_cutoffs,
)
from app.services.score_confidence import (
    compute_confidence_bucket,
    wilson_bounds,
)

# ---------------------------------------------------------------------------
# Thresholds. The score-based effect-size gate and Wilson score-test
# confidence buckets are imported from app.services.opening_insights_constants
# above. The CI consistency test
# (tests/services/test_opening_insights_arrow_consistency.py) keeps the
# backend constants and frontend/src/lib/arrowColor.ts in lock-step.
# ---------------------------------------------------------------------------

# Card findings per section (D-08, D-37): only 95%-gated ('medium' or 'high',
# p < 0.05, D-33) findings qualify. 10, not the original 5: with 5, a user with 5+ current
# findings never saw a significant older-games one (current sorts first). The phone
# 2-card view with "Show more" is a frontend concern.
FINDINGS_CARD_CAP: int = 10
# Leaning cards (D-38): a section with no 95% finding shows up to this many low-confidence
# findings instead of an empty state (prod 2026-10-18: "Moves that Cost You" was empty for
# about two thirds of user-colours with 20+ games). Fewer than the card cap: they are hints,
# not verdicts. The frontend tells them apart by confidence == 'low'.
FINDINGS_LEANING_CAP: int = 4
UNNAMED_LINE_NAME: str = "<unnamed line>"
UNNAMED_LINE_ECO: str = ""

# Surfaced when the resulting-position WDL lookup misses a
# resulting_full_hash that came back from query_opening_transitions. Should be
# zero under correct filter parity; non-zero indicates a divergence between the
# two query call sites that needs investigation.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------


def _classify_row(
    row: Any,
) -> tuple[Literal["weakness", "strength"], Literal["minor", "major"]] | None:
    """Classify a transition row by chess score against the 0.50 pivot.

    Score is (W + 0.5·D) / N. Effect-size thresholds are symmetric:
      - weakness: score <= 0.45 → minor; <= 0.40 → major
      - strength: score >= 0.55 → minor; >= 0.60 → major
    Strict <= / >= boundaries. Returns None for neutral positions.

    Compare score directly against precomputed pivot ± effect thresholds rather
    than against `delta = score - PIVOT`. The literal score values produced by
    integer-row factories (e.g. 0.45 = 9/20) are exactly equal to PIVOT ± EFFECT
    in IEEE-754 (0.50 - 0.05 == 0.45 exactly), but `0.45 - 0.50 == -0.04999…`,
    which would silently miss strict-<= boundary cases. Direct comparison keeps
    the strict <= / >= semantics on the boundary.
    """
    score = (row.w + 0.5 * row.d) / row.n
    weakness_minor_threshold = SCORE_PIVOT - MINOR_EFFECT  # 0.45
    weakness_major_threshold = SCORE_PIVOT - MAJOR_EFFECT  # 0.40
    strength_minor_threshold = SCORE_PIVOT + MINOR_EFFECT  # 0.55
    strength_major_threshold = SCORE_PIVOT + MAJOR_EFFECT  # 0.60
    if score <= weakness_minor_threshold:
        severity: Literal["minor", "major"] = (
            "major" if score <= weakness_major_threshold else "minor"
        )
        return "weakness", severity
    if score >= strength_minor_threshold:
        severity = "major" if score >= strength_major_threshold else "minor"
        return "strength", severity
    return None


def _compute_score(row: Any) -> float:
    """Compute score = (W + D/2) / n (the canonical classification metric)."""
    return (row.w + row.d / 2) / row.n


def _replay_san_sequence(san_sequence: list[str]) -> str:
    """Replay a SAN sequence from the start position.

    Reconstructs the entry FEN by replaying the exact moves
    the user played up to the entry position. With MIN_ENTRY_PLY=0 an empty
    sequence is valid and corresponds to the starting position itself
    (entry_ply=0, where the candidate is white's first move).
    """
    board = chess.Board()
    for san in san_sequence:
        board.push_san(san)
    return board.fen()


def _apply_display_name_parity(
    name: str,
    opening_ply_count: int,
    finding_color: Literal["white", "black"],
) -> str:
    """Apply 'vs. ' prefix when attribution parity disagrees with finding color.

    A white-defined opening has odd ply_count (white's move last);
    a black-defined opening has even ply_count. When the finding's color
    disagrees with the opening's parity, prefix with 'vs. '.
    """
    user_parity = 1 if finding_color == "white" else 0
    if opening_ply_count % 2 != user_parity:
        return f"vs. {name}"
    return name


def _signed_full_hash(board: chess.Board) -> int:
    """Return the signed int64 Zobrist hash for the current board position.

    Identical conversion to STARTING_POSITION_HASH in openings_repository and
    _compute_prefix_hashes: ctypes.c_int64 wraps the unsigned 64-bit polyglot
    hash to match the signed BIGINT stored on GamePosition.full_hash.
    """
    return ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value


def _compute_prefix_hashes(san_sequence: list[str]) -> list[int]:
    """Return the full_hash for every proper prefix (deepest first).

    Hashes MUST be converted via ctypes.c_int64(...).value to
    match the signed int64 stored on GamePosition.full_hash. Without this
    conversion, lookups against the openings table (whose Opening.full_hash
    is also signed via the same path) would silently miss every match.
    """
    board = chess.Board()
    hashes: list[int] = []
    for san in san_sequence:
        board.push_san(san)
        hashes.append(_signed_full_hash(board))
    # Drop the LAST entry (full sequence == the entry position itself, which
    # was already covered by direct attribution). Deepest parent first.
    return list(reversed(hashes[:-1]))


def _attribute_finding(
    row: Any,
    openings_by_hash: dict[int, Opening],
    parents_by_hash: dict[int, Opening],
    finding_color: Literal["white", "black"],
) -> tuple[str, str, str] | None:
    """Attribute a finding to an opening name.

    Returns (opening_name, opening_eco, display_name) or None when no match
    is found at any lineage depth — None causes the finding to be DROPPED
    (never surfaced with a sentinel name).

    Attribution path:
    1. Direct: look up entry_hash in openings_by_hash.
    2. Lineage walk: check parent prefix hashes in parents_by_hash (deepest first).
    3. ply=0 fallback: when san_seq is empty (entry IS the starting position),
       attribute by resulting_full_hash so e.g. "1.e4" surfaces as
       "King's Pawn Opening" via the position AFTER the candidate move. The
       openings table has min(ply_count)=1 so direct attribution always misses
       at ply=0; this fallback keeps the relaxed MIN_ENTRY_PLY=0 actually
       useful instead of silently dropping every first-move finding.
    4. No match → return None. Sentry tag set by calling pipeline on drop.
    """
    entry_hash_int = int(row.entry_hash)

    # Pass 1: direct attribution
    direct_opening = openings_by_hash.get(entry_hash_int)
    if direct_opening is not None:
        display_name = _apply_display_name_parity(
            direct_opening.name, direct_opening.ply_count, finding_color
        )
        return direct_opening.name, direct_opening.eco, display_name

    # Pass 2: lineage walk (deepest first). With MIN_ENTRY_PLY=0, ply=0
    # entries have a NULL entry_san_sequence (array_agg over empty window):
    # there is no parent lineage to walk in that case, so an empty list
    # short-circuits the loop and we fall through to the ply=0 fallback.
    san_seq = list(row.entry_san_sequence or [])
    for prefix_hash in _compute_prefix_hashes(san_seq):
        parent_opening = parents_by_hash.get(prefix_hash)
        if parent_opening is not None:
            display_name = _apply_display_name_parity(
                parent_opening.name, parent_opening.ply_count, finding_color
            )
            return parent_opening.name, parent_opening.eco, display_name

    # Pass 3: ply=0 fallback via resulting_full_hash (only when san_seq is
    # empty — i.e. entry IS the starting position).
    if not san_seq:
        result_hash_int = int(row.resulting_full_hash)
        result_opening = openings_by_hash.get(result_hash_int)
        if result_opening is not None:
            display_name = _apply_display_name_parity(
                result_opening.name, result_opening.ply_count, finding_color
            )
            return result_opening.name, result_opening.eco, display_name

    # No match at any depth — drop this finding
    return None


def _dedupe_within_section(
    items: list[tuple[OpeningInsightFinding, int, float]],
) -> list[tuple[OpeningInsightFinding, float]]:
    """Deduplicate by resulting_full_hash within a section, keeping the deepest entry.

    When two findings share resulting_full_hash in the same color section,
    keep the one with the higher attribution ply_count (deeper opening wins).

    Also threads `se` through. Returns (finding, se) tuples
    — opening_ply_count is consumed here and does not flow downstream to ranking.
    """
    best: dict[str, tuple[OpeningInsightFinding, int, float]] = {}
    for finding, ply_count, se in items:
        key = finding.resulting_full_hash
        existing = best.get(key)
        if existing is None or ply_count > existing[1]:
            best[key] = (finding, ply_count, se)
    return [(finding, se) for finding, _ply, se in best.values()]


def _robustness(finding: OpeningInsightFinding) -> float:
    """Directional Wilson-bound signal strength.

    Positive = the 95% CI puts the true score on the claimed side of 0.50;
    near-zero or negative = the CI straddles 0.50 and the finding is mostly
    noise. Combines effect size and sample-size uncertainty into a single
    continuous metric, replacing the old categorical confidence-bucket
    comparison in dedupe (which had nothing to do with line-collapse choice
    until MIN_ENTRY_PLY=0 surfaced low-signal shallow findings that began
    pre-empting more informative deeper ones).

    For weakness: 0.5 - wilson_upper(score, n)
        — how far below 0.50 the upper bound sits; large = robust weakness.
    For strength: wilson_lower(score, n) - 0.5
        — how far above 0.50 the lower bound sits; large = robust strength.
    """
    lower, upper = wilson_bounds(finding.score, finding.n_games)
    if finding.classification == "weakness":
        return SCORE_PIVOT - upper
    return lower - SCORE_PIVOT


def _dedupe_continuations(
    sections: dict[str, list[tuple[OpeningInsightFinding, float]]],
) -> dict[str, list[tuple[OpeningInsightFinding, float]]]:
    """Collapse each line to its single most-robust finding.

    When consecutive moves in the same line are all weak
    (or all strong), deeper findings crowd the block with the same opening
    line (e.g. Caro-Kann B10: 3.exd5, 3...cxd5, 4.d4 all surfacing as
    separate cards). Don't keep the shallowest entry per chain: with
    MIN_ENTRY_PLY=0 a low-signal shallow finding (CI straddling 0.50) would
    pre-empt a high-signal deeper one.

    Rule: iterate findings most-robust-first (Wilson-bound directional
    signal); a finding is dropped if its full_path = entry + [candidate] is
    prefix-related (either direction) to any already-kept finding's
    full_path. Two findings share a line iff one full_path is a prefix of
    the other. Tie-breaks (after `-robustness`): shallower depth, major
    severity, higher n_games.

    Applied globally across all four sections so chains crossing color
    boundaries (white candidate → black candidate → white candidate) still
    consolidate.

    Payload is `(finding, se)` so SE survives this
    stage and reaches _rank_section.
    """
    flat: list[tuple[str, OpeningInsightFinding, float]] = [
        (sk, f, se) for sk, items in sections.items() for f, se in items
    ]
    flat.sort(
        key=lambda kf: (
            -_robustness(kf[1]),
            len(kf[1].entry_san_sequence),
            0 if kf[1].severity == "major" else 1,
            -kf[1].n_games,
        )
    )

    kept_keys: set[tuple[str, str, str]] = set()
    kept_paths: list[tuple[str, tuple[str, ...]]] = []
    for section_key, finding, _se in flat:
        full_path = tuple(finding.entry_san_sequence) + (finding.candidate_move_san,)
        same_line = False
        for kept_section_key, kp in kept_paths:
            shares_line = (len(full_path) >= len(kp) and full_path[: len(kp)] == kp) or (
                len(kp) >= len(full_path) and kp[: len(full_path)] == full_path
            )
            if not shares_line:
                continue
            # Exception: same exact transition reached from different
            # color perspectives is two distinct findings (e.g. user plays
            # both colors → "as white, opponents respond with X" and "as
            # black, you play X" both clear the gates). Keep both.
            if full_path == kp and section_key != kept_section_key:
                continue
            same_line = True
            break
        if same_line:
            continue
        kept_keys.add((section_key, finding.entry_full_hash, finding.candidate_move_san))
        kept_paths.append((section_key, full_path))

    result: dict[str, list[tuple[OpeningInsightFinding, float]]] = {k: [] for k in sections}
    for section_key, items in sections.items():
        for finding, se in items:
            if (section_key, finding.entry_full_hash, finding.candidate_move_san) in kept_keys:
                result[section_key].append((finding, se))
    return result


def _rank_section(
    findings_with_se: list[tuple[OpeningInsightFinding, float]],
    direction: Literal["weakness", "strength"],
) -> list[OpeningInsightFinding]:
    """Sort findings by direction-aware Wilson 95% CI bound on the score, clamped to [0, 1].

    - weakness: ascending Wilson upper bound — the row whose score is
      most-confidently-below-0.5 (smallest plausible best case) sorts first.
    - strength: descending Wilson lower bound — the row whose score is
      most-confidently-above-0.5 (largest plausible worst case) sorts first.

    Wilson rather than a Wald `score +/- 1.96 * SE` formula: Wald degenerates
    at boundary scores (e.g. 0/11 -> SE=0, CI width=0, claiming 100% certainty);
    Wilson is well-defined for any p in [0, 1] and tighter for small n, so
    small-N extreme findings do not outrank large-N moderate findings purely on
    score.

    The `(finding, se)` tuple shape is preserved upstream because SE is still
    produced by compute_confidence_bucket for the UI confidence badge, but
    Wilson uses only `finding.score` and `finding.n_games` — the SE component
    of the tuple is intentionally ignored here.

    Confidence bucket is not part of the sort key:
    the CI bound already mixes effect size and sample size, so a high-N
    moderate-effect row that lives in the "medium" bucket can legitimately
    rank above a small-N extreme-effect row in the "high" bucket when its
    bound is more striking. Bucket is retained as a UI badge only.
    """

    def sort_key(item: tuple[OpeningInsightFinding, float]) -> float:
        finding, _se = item  # SE unused under Wilson; preserved for upstream compatibility
        lower, upper = wilson_bounds(finding.score, finding.n_games)
        if direction == "weakness":
            return upper
        # Negate so default ascending sort yields lower-bound descending.
        return -lower

    ranked = sorted(findings_with_se, key=sort_key)
    return [f for f, _se in ranked]


# ---------------------------------------------------------------------------
# MG-entry eval helpers (parity with OpeningWDL)
# ---------------------------------------------------------------------------


def _apply_eval_metrics_to_finding(
    finding: OpeningInsightFinding,
    pe: OpeningPhaseEntryMetrics,
) -> OpeningInsightFinding:
    """Populate the MG-entry eval fields on a finding from phase-entry metrics.

    Delegates to opening_eval.finalize_opening_eval, the single Openings eval
    finalizer shared with the Stats tab. The z-test runs against the finding colour's
    baseline (+25 cp White, -25 cp Black), not 0 cp (D-13), so "typical for the
    colour" reads as not significant. avg_eval_pawns stays the raw mean; the 95% CI
    bounds are returned alongside it.
    """
    fields = finalize_opening_eval(pe, finding.color)
    return finding.model_copy(update=dict(fields))


# ---------------------------------------------------------------------------
# compute_insights stage helpers
#
# compute_insights reads as a short pipeline:
#   1. _fetch_attribution_context  — pass-1 transitions + direct openings lookup
#   2. _fetch_position_wdl_per_color — pass-2 parent walk + per-color WDL fetch
#   3. _build_sections              — classify → attribute → dedupe → rank → partition → eval enrich (cards only)
# Each helper is module-private and called sequentially; no behavior changes.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _TransitionRow:
    """Typed wrapper for one transition, combining SQL-level and Python-derived attrs.

    SQL-level attrs (from query_opening_transitions):
        entry_hash, move_san, sample_pair=[ply, game_id], n, w, d, l, last_played_at

    Python-derived attrs (added by _wrap_transition_row):
        entry_san_sequence  — SAN prefix from start to entry position (plies 0..ply-1)
        resulting_full_hash — Zobrist hash after replaying entry_san_sequence + move_san

    sample_game_id / sample_ply are unpacked from sample_pair and stored on the
    wrapper for downstream prefix lookup + Sentry context.
    """

    entry_hash: int
    move_san: str
    sample_game_id: int
    sample_ply: int
    n: int
    w: int
    d: int
    l: int  # noqa: E741 — 'l' matches SQL label and fixture convention throughout
    last_played_at: datetime.datetime | None
    entry_san_sequence: list[str]
    resulting_full_hash: int


def _wrap_transition_row(
    raw_row: Any,
    prefixes: dict[tuple[int, int], list[str]],
) -> _TransitionRow | None:
    """Wrap a raw SQL row from query_opening_transitions into a typed _TransitionRow.

    Derives entry_san_sequence from the prefixes dict and resulting_full_hash by
    replaying the SAN sequence on a fresh chess.Board.

    Returns None on either of two distinct, deliberately separate drop reasons:

    1. No standard-start sample. The sample aggregate is filtered
       to `initial_fen IS NULL`, so a group in which EVERY game is custom-start
       yields a NULL `sample_pair`. There is no replayable SAN path to this
       position, so the group cannot be rendered.
    2. Replay failure. A defensive residual — with (1) filtered upstream the
       prefix should always be reachable, so this firing means something else is
       wrong (a corrupt PGN, an unmarked custom start).

    Both are expected, handled conditions rather than errors, so both report at
    warning level. Keeping them as separate messages matters: collapsing
    them would make the Sentry payload lie about which one fired.
    """
    # sample_pair is ARRAY[ply, game_id] from one real STANDARD-START row in the
    # group (paired aggregate — independent MIN(ply)/MIN(game_id) would
    # de-correlate under transposition). asyncpg returns it as a 2-element list,
    # and a NULL aggregate as None (NOT an empty list — the guard must be
    # `is None`, not a falsiness check on length).
    if raw_row.sample_pair is None:
        sentry_sdk.set_context(
            "opening_insights_drop",
            {
                "entry_hash": int(raw_row.entry_hash),
                "move_san": raw_row.move_san,
                "n": int(raw_row.n),
                "reason": "all_games_custom_start",
            },
        )
        sentry_sdk.set_tag("source", "opening_insights")
        sentry_sdk.capture_message(
            "Opening transition dropped: no standard-start sample game",
            level="warning",
        )
        return None

    sample_ply = int(raw_row.sample_pair[0])
    sample_game_id = int(raw_row.sample_pair[1])
    entry_san_sequence = prefixes.get((sample_game_id, sample_ply), [])

    try:
        board = chess.Board()
        for san in entry_san_sequence:
            board.push_san(san)
        board.push_san(raw_row.move_san)
        resulting_full_hash = _signed_full_hash(board)
    except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError, AssertionError) as exc:
        # SAN prefix is unreachable from chess.Board(). The systematic cause
        # (custom-start games being preferred as the sample representative) is
        # filtered out upstream, so this is a defensive residual rather than the
        # common path.
        #
        # Use a warning-level capture_message, not capture_exception: this
        # models a handled, expected drop, and as an exception it
        # escalated a non-bug into the issue list 74 times (FLAWCHESS-5E) while
        # the two genuinely actionable production issues sat below it. Rate
        # visibility is preserved; the escalation is not. Per CLAUDE.md the
        # message carries no variables — those stay in set_context so grouping
        # doesn't fragment.
        sentry_sdk.set_context(
            "opening_insights_drop",
            {
                "entry_hash": int(raw_row.entry_hash),
                "move_san": raw_row.move_san,
                "sample_game_id": sample_game_id,
                "sample_ply": sample_ply,
                "reason": "san_prefix_unreplayable",
                "error": str(exc),
            },
        )
        sentry_sdk.set_tag("source", "opening_insights")
        sentry_sdk.capture_message(
            "Opening transition dropped: SAN prefix unreplayable from the standard start",
            level="warning",
        )
        return None

    return _TransitionRow(
        entry_hash=int(raw_row.entry_hash),
        move_san=raw_row.move_san,
        sample_game_id=sample_game_id,
        sample_ply=sample_ply,
        n=int(raw_row.n),
        w=int(raw_row.w),
        d=int(raw_row.d),
        l=int(raw_row.l),
        last_played_at=raw_row.last_played_at,
        entry_san_sequence=entry_san_sequence,
        resulting_full_hash=resulting_full_hash,
    )


@dataclass(slots=True)
class _AttributionContext:
    """Pass-1 attribution context: per-color transition rows + direct openings lookup.

    Carried between _fetch_attribution_context and _fetch_position_wdl_per_color.
    """

    rows_by_color: dict[str, list[_TransitionRow]] = field(default_factory=dict)
    openings_by_hash: dict[int, Opening] = field(default_factory=dict)


@dataclass(slots=True)
class _PipelineContext:
    """Combined pass-1 + pass-2 context handed to _build_sections.

    Bundles transition rows, direct opening lookup, parent-lineage lookup,
    and per-color resulting-position WDL maps so the section-builder takes
    a single context parameter rather than 4+ positional arguments.
    """

    rows_by_color: dict[str, list[_TransitionRow]]
    openings_by_hash: dict[int, Opening]
    parents_by_hash: dict[int, Opening]
    pos_wdl_by_color: dict[
        Literal["white", "black"],
        dict[int, tuple[int, int, int, datetime.datetime | None]],
    ]
    # Per-colour current-repertoire cutoff (D-02); filled by compute_insights before
    # _build_sections so _row_to_finding can stamp is_current on each finding.
    cutoffs: CurrentCutoffs = field(default_factory=lambda: CurrentCutoffs(white=None, black=None))


async def _fetch_attribution_context(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    colors_to_query: Sequence[Literal["white", "black"]],
) -> _AttributionContext:
    """Stage 1: query transitions per color, derive Python attrs, resolve direct opening attribution.

    Runs query_opening_transitions sequentially per color (CLAUDE.md AsyncSession
    rule), then calls query_transition_prefixes once per color to batch-resolve
    SAN prefixes, wraps raw Rows into _TransitionRow (deriving entry_san_sequence
    and resulting_full_hash in Python), and looks up the union of entry hashes —
    plus resulting_full_hash for ply=0 entries so the ply=0 attribution fallback
    in `_attribute_finding` can name them by the resulting position
    (e.g. "1.e4" → "King's Pawn Opening").

    Rows where SAN replay fails (custom-FEN survivors) are dropped and Sentry-captured
    once per occurrence in _wrap_transition_row.
    """
    wrapped_by_color: dict[str, list[_TransitionRow]] = {}
    # CLAUDE.md §Critical Constraints: AsyncSession not safe for asyncio.gather.
    for color in colors_to_query:
        raw_rows = await query_opening_transitions(
            session=session,
            user_id=user_id,
            color=color,
            time_control=request.time_control,
            platform=request.platform,
            rated=request.rated,
            opponent_type=request.opponent_type,
            from_date=from_date,
            to_date=to_date,
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
        )
        # Unpack ARRAY[ply, game_id] into (game_id, ply) — sample_pair is paired
        # so each (game_id, ply) refers to a real row in the SQL group. Skip NULL
        # pairs (all-custom-start groups): this ran before _wrap_transition_row's
        # None guard, so such a group raised TypeError and failed compute_insights.
        samples = [
            (int(r.sample_pair[1]), int(r.sample_pair[0]))
            for r in raw_rows
            if r.sample_pair is not None
        ]
        prefixes = await query_transition_prefixes(session, user_id, samples)
        wrapped: list[_TransitionRow] = []
        for r in raw_rows:
            row = _wrap_transition_row(r, prefixes)
            if row is not None:
                wrapped.append(row)
        wrapped_by_color[color] = wrapped

    # Pass 1: direct attribution for all entry hashes. Also include
    # resulting_full_hash for ply=0 entries (empty SAN sequence) so the
    # ply=0 attribution fallback in `_attribute_finding` can name them
    # by the resulting position (e.g. "1.e4" → "King's Pawn Opening").
    direct_entry_hashes_set: set[int] = set()
    for rows in wrapped_by_color.values():
        for r in rows:
            direct_entry_hashes_set.add(r.entry_hash)
            if not r.entry_san_sequence:
                direct_entry_hashes_set.add(r.resulting_full_hash)
    openings_by_hash = await query_openings_by_hashes(session, list(direct_entry_hashes_set))

    return _AttributionContext(rows_by_color=wrapped_by_color, openings_by_hash=openings_by_hash)


async def _fetch_position_wdl_per_color(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    colors_to_query: Sequence[Literal["white", "black"]],
    ctx: _AttributionContext,
) -> _PipelineContext:
    """Stage 2: parent-lineage attribution + per-color resulting-position WDL.

    First walks parent prefix hashes for any entry hashes that missed direct
    attribution, then fetches per-color resulting-position
    W/D/L — aggregated across ALL move orders
    (transposition-inclusive). Sequential awaits per CLAUDE.md AsyncSession rule.

    Queries per color, scoped to that color's resulting_full_hash set,
    and passes color=color to query_resulting_position_wdl so the denominator
    matches query_opening_transitions' Game.user_color filter (avoids blending
    white-perspective and black-perspective games).
    """
    rows_by_color = ctx.rows_by_color
    openings_by_hash = ctx.openings_by_hash

    # Pass 2: parent-lineage attribution for unmatched entry hashes.
    unmatched_parent_hashes: set[int] = set()
    for rows in rows_by_color.values():
        for r in rows:
            if r.entry_hash not in openings_by_hash:
                # entry_san_sequence is already a list[str] on _TransitionRow
                # (ply=0 entries legitimately have an empty list).
                unmatched_parent_hashes.update(_compute_prefix_hashes(r.entry_san_sequence))
    parents_by_hash = await query_openings_by_hashes(session, list(unmatched_parent_hashes))

    # Aggregate W/D/L per resulting_full_hash across
    # ALL move orders (transposition-inclusive). Surfacing gate already ran
    # in query_opening_transitions HAVING n_games >= OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE
    # on move-played n. The values below feed _classify_row /
    # _compute_score / compute_confidence_bucket / wilson_bounds /
    # OpeningInsightFinding via a SimpleNamespace adapter so those helpers
    # don't change.
    pos_wdl_by_color: dict[
        Literal["white", "black"], dict[int, tuple[int, int, int, datetime.datetime | None]]
    ] = {}
    for color in colors_to_query:
        color_resulting_hashes: list[int] = list(
            {r.resulting_full_hash for r in rows_by_color[color]}
        )
        if not color_resulting_hashes:
            pos_wdl_by_color[color] = {}
            continue
        pos_wdl_by_color[color] = await query_resulting_position_wdl(
            session=session,
            user_id=user_id,
            hash_list=color_resulting_hashes,
            time_control=request.time_control,
            platform=request.platform,
            rated=request.rated,
            opponent_type=request.opponent_type,
            from_date=from_date,
            to_date=to_date,
            color=color,  # per-color: matches query_opening_transitions' Game.user_color filter
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
        )

    return _PipelineContext(
        rows_by_color=rows_by_color,
        openings_by_hash=openings_by_hash,
        parents_by_hash=parents_by_hash,
        pos_wdl_by_color=pos_wdl_by_color,
    )


def _row_to_finding(
    row: _TransitionRow,
    color_literal: Literal["white", "black"],
    pos_wdl_for_color: dict[int, tuple[int, int, int, datetime.datetime | None]],
    openings_by_hash: dict[int, Opening],
    parents_by_hash: dict[int, Opening],
    cutoff: datetime.datetime | None = None,
) -> tuple[OpeningInsightFinding, int, float] | None:
    """Convert one _TransitionRow into a (finding, ply_count, se) tuple, or None.

    ``cutoff`` is the finding colour's current-repertoire cutoff; the finding's
    ``is_current`` compares its last_played_at against it (D-04).

    Returns None when the row is neutral (classify miss) or when attribution
    fails at every depth (dropped). Mirrors the inner-loop body of the
    original compute_insights pipeline byte-for-byte.
    """
    # Feed _classify_row / _compute_score /
    # compute_confidence_bucket / wilson_bounds / OpeningInsightFinding
    # the resulting-position W/D/L via a SimpleNamespace adapter so
    # those helpers stay byte-identical. Non-WDL fields (move_san,
    # entry_*, resulting_full_hash) come from the typed _TransitionRow.
    pos = pos_wdl_for_color.get(row.resulting_full_hash)
    if pos is None:
        # Filter mismatch defensive fallback.
        # Should not fire when query_resulting_position_wdl filters
        # mirror query_opening_transitions; logged for diagnosis.
        logger.warning(
            "query_resulting_position_wdl missing resulting_full_hash=%s; "
            "falling back to move-played WDL",
            row.resulting_full_hash,
        )
        pos_row: Any = row
        # Fall back to the move-played MAX(played_at) from
        # query_opening_transitions (still the same user, same
        # filters) rather than dropping the line silently.
        finding_last_played_at: datetime.datetime | None = row.last_played_at
    else:
        pos_w, pos_d, pos_l, pos_last_played_at = pos
        pos_n = pos_w + pos_d + pos_l
        pos_row = SimpleNamespace(w=pos_w, d=pos_d, l=pos_l, n=pos_n)
        finding_last_played_at = pos_last_played_at

    cls = _classify_row(pos_row)
    if cls is None:
        return None
    classification, severity = cls

    # Single attribution path. None => DROP.
    attribution = _attribute_finding(row, openings_by_hash, parents_by_hash, color_literal)
    if attribution is None:
        sentry_sdk.set_tag("openings.attribution.unmatched_dropped", True)
        return None
    opening_name, opening_eco, display_name = attribution

    # entry_fen is reconstructed by replaying the SAN sequence.
    # entry_san_sequence is already a list[str] on _TransitionRow; no None coercion needed.
    # ply=0 entries have [] and legitimately replay zero moves → starting FEN.
    entry_fen = _replay_san_sequence(row.entry_san_sequence)

    # Carry the matched Opening.ply_count alongside for the
    # deeper-entry-wins dedupe; use 0 for parent-only matches
    # (parent-matched entries have lower specificity than direct matches).
    # ply=0 entries attribute via resulting_full_hash, so mirror
    # that lookup here to avoid under-counting their depth.
    matched_opening = openings_by_hash.get(row.entry_hash)
    if matched_opening is None and not row.entry_san_sequence:
        matched_opening = openings_by_hash.get(row.resulting_full_hash)
    opening_ply_count = matched_opening.ply_count if matched_opening else 0

    score = _compute_score(pos_row)
    confidence, p_value, se = compute_confidence_bucket(pos_row.w, pos_row.d, pos_row.l, pos_row.n)
    ci_low, ci_high = wilson_bounds(score, pos_row.n)

    finding = OpeningInsightFinding(
        color=color_literal,
        classification=classification,
        severity=severity,
        opening_name=opening_name,
        opening_eco=opening_eco,
        display_name=display_name,
        entry_fen=entry_fen,
        # SAN sequence start→entry; empty for entry_ply=0 (no preceding moves).
        entry_san_sequence=row.entry_san_sequence,
        # Stringify 64-bit ints at the API boundary.
        entry_full_hash=str(row.entry_hash),
        candidate_move_san=row.move_san,
        resulting_full_hash=str(row.resulting_full_hash),
        n_games=pos_row.n,
        wins=pos_row.w,
        draws=pos_row.d,
        losses=pos_row.l,
        score=score,
        confidence=confidence,
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
        # MAX(played_at) across all games
        # visiting the resulting position (transposition-inclusive,
        # color-filtered). Falls back to the move-played MAX from
        # query_opening_transitions when the resulting-position
        # lookup misses (matches the W/D/L fallback above).
        last_played_at=finding_last_played_at,
        is_current=is_current(finding_last_played_at, cutoff),
    )
    return finding, opening_ply_count, se


def _partition_section(ranked: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    """The card findings of a ranked section (D-33, D-38).

    Confidence 'medium' or 'high' (p < 0.05) qualifies, capped at FINDINGS_CARD_CAP. A
    section with no such finding falls back to its low-confidence "leaning" findings,
    capped at FINDINGS_LEANING_CAP, so the section is not empty; the two never mix, so a
    section is either all verdicts or all leaning. Both lists put current findings before
    older ones and keep the incoming Wilson order inside each group (stable sort, D-08).
    """
    confident = [f for f in ranked if f.confidence != "low"]
    cards, cap = (confident, FINDINGS_CARD_CAP) if confident else (ranked, FINDINGS_LEANING_CAP)
    # sorted() is stable, so Wilson order survives within the current / older groups.
    return sorted(cards, key=lambda f: not f.is_current)[:cap]


def _rank_sections(
    ctx: _PipelineContext, colors_to_query: Sequence[Literal["white", "black"]]
) -> dict[str, list[OpeningInsightFinding]]:
    """Classify, attribute, dedupe and rank every row into the four sections.

    Per-section transposition dedupe -> global continuation dedupe -> rank by the
    direction-aware Wilson 95% CI bound on (score, n_games). SE is ignored (Wald
    degenerates at small N) and the confidence bucket is not part of the sort key.
    """
    # Each section accumulates (OpeningInsightFinding, ply_count, se) tuples:
    # - ply_count drives the deeper-entry-wins dedupe in _dedupe_within_section
    #   (consumed there and not propagated downstream).
    # - se threads through dedupe stages but is ignored by _rank_section.
    sections: dict[str, list[tuple[OpeningInsightFinding, int, float]]] = {
        "white_weaknesses": [],
        "black_weaknesses": [],
        "white_strengths": [],
        "black_strengths": [],
    }

    for color in colors_to_query:
        color_literal: Literal["white", "black"] = color
        for row in ctx.rows_by_color[color]:
            built = _row_to_finding(
                row,
                color_literal,
                ctx.pos_wdl_by_color[color_literal],
                ctx.openings_by_hash,
                ctx.parents_by_hash,
                ctx.cutoffs[color_literal],
            )
            if built is None:
                continue
            finding, opening_ply_count, se = built
            section_key = (
                f"{color}_{'weaknesses' if finding.classification == 'weakness' else 'strengths'}"
            )
            sections[section_key].append((finding, opening_ply_count, se))

    deduped_sections: dict[str, list[tuple[OpeningInsightFinding, float]]] = {
        key: _dedupe_within_section(items) for key, items in sections.items()
    }
    deduped_sections = _dedupe_continuations(deduped_sections)
    ranked_sections: dict[str, list[OpeningInsightFinding]] = {}
    for key, findings_with_se in deduped_sections.items():
        direction: Literal["weakness", "strength"] = (
            "weakness" if "weaknesses" in key else "strength"
        )
        ranked_sections[key] = _rank_section(findings_with_se, direction=direction)
    return ranked_sections


async def _fetch_eval_metrics(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: Literal["white", "black"],
    findings: Sequence[OpeningInsightFinding],
) -> dict[int, OpeningPhaseEntryMetrics]:
    """MG-entry eval sums for the findings' resulting positions (empty when none).

    Key is resulting_full_hash (the position immediately after the candidate move),
    mirroring how Stats keys MG-entry eval.
    """
    hashes: list[int] = list({int(f.resulting_full_hash) for f in findings})
    if not hashes:
        return {}
    return await query_opening_phase_entry_metrics_batch(
        session=session,
        user_id=user_id,
        hashes=hashes,
        color=color,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )


async def _build_sections(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    colors_to_query: Sequence[Literal["white", "black"]],
    ctx: _PipelineContext,
) -> dict[str, list[OpeningInsightFinding]]:
    """Stage 3: classify -> attribute -> dedupe -> rank -> partition -> enrich cards.

    Builds the four sections (white/black x weaknesses/strengths), keeps the
    95%-gated cards of each (or its leaning fallback, D-38), then enriches ONLY the card
    findings with MG-entry eval metrics (at most FINDINGS_CARD_CAP per section). Enriching
    the uncapped ranked list measured 10.6 s for a heavy user (Pitfall 8). The eval batch
    awaits run sequentially per colour (AsyncSession is not safe for concurrent use).
    """
    ranked_sections = _rank_sections(ctx, colors_to_query)
    partitions = {key: _partition_section(ranked) for key, ranked in ranked_sections.items()}

    eval_by_color: dict[Literal["white", "black"], dict[int, OpeningPhaseEntryMetrics]] = {}
    for color in ("white", "black"):
        cards = partitions[f"{color}_weaknesses"] + partitions[f"{color}_strengths"]
        eval_by_color[color] = await _fetch_eval_metrics(
            session, user_id, request, from_date, to_date, color, cards
        )

    enriched: dict[str, list[OpeningInsightFinding]] = {}
    for key, cards in partitions.items():
        color_key: Literal["white", "black"] = "white" if key.startswith("white") else "black"
        enriched[key] = _enrich_findings(cards, eval_by_color[color_key])
    return enriched


def _enrich_findings(
    findings: Sequence[OpeningInsightFinding],
    metrics_map: dict[int, OpeningPhaseEntryMetrics],
) -> list[OpeningInsightFinding]:
    """Apply MG-entry eval metrics to each finding when present in metrics_map."""
    result: list[OpeningInsightFinding] = []
    for f in findings:
        pe = metrics_map.get(int(f.resulting_full_hash))
        if pe is not None:
            result.append(_apply_eval_metrics_to_finding(f, pe))
        else:
            result.append(f)
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def compute_insights(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
    *,
    now_utc: datetime.datetime,
) -> OpeningInsightsResponse:
    """Compute four-section opening insights for one user under a filter set.

    Returns OpeningInsightsResponse with white_weaknesses, black_weaknesses,
    white_strengths, black_strengths — each capped per section.
    ``now_utc`` (from the dev_now_utc dependency) anchors the current-repertoire
    cutoff behind every finding's ``is_current`` (D-02, D-03).
    See module docstring for pipeline details.
    """
    from_date: datetime.date | None = request.from_date
    to_date: datetime.date | None = request.to_date

    # Optimization: when the user narrows to a single color, skip the
    # off-color SQL query entirely (~50% latency saving).
    colors_to_query: list[Literal["white", "black"]]
    if request.color == "all":
        colors_to_query = ["white", "black"]
    else:
        colors_to_query = [request.color]

    # The full pipeline (queries + classify + attribute + dedupe +
    # rank + cap) is wrapped in a single try/except so any exception in
    # pure-Python stages also gets the Sentry context + tags.
    try:
        attribution_ctx = await _fetch_attribution_context(
            session, user_id, request, from_date, to_date, colors_to_query
        )
        pipeline_ctx = await _fetch_position_wdl_per_color(
            session, user_id, request, from_date, to_date, colors_to_query, attribution_ctx
        )
        # D-02: the cutoff is computed under the SAME filters as the findings.
        pipeline_ctx.cutoffs = await resolve_current_cutoffs(
            session,
            user_id,
            colors_to_query,
            now_utc=now_utc,
            time_control=request.time_control,
            platform=request.platform,
            rated=request.rated,
            opponent_type=request.opponent_type,
            from_date=from_date,
            to_date=to_date,
            opponent_gap_min=request.opponent_gap_min,
            opponent_gap_max=request.opponent_gap_max,
        )
        partitions = await _build_sections(
            session, user_id, request, from_date, to_date, colors_to_query, pipeline_ctx
        )
        return OpeningInsightsResponse(
            white_weaknesses=partitions["white_weaknesses"],
            black_weaknesses=partitions["black_weaknesses"],
            white_strengths=partitions["white_strengths"],
            black_strengths=partitions["black_strengths"],
            current_cutoff_white=pipeline_ctx.cutoffs["white"],
            current_cutoff_black=pipeline_ctx.cutoffs["black"],
            eval_baseline_pawns_white=EVAL_BASELINE_PAWNS_WHITE,
            eval_baseline_pawns_black=EVAL_BASELINE_PAWNS_BLACK,
        )
    except Exception as exc:
        # CLAUDE.md §Sentry: pass variable data via set_context; never embed
        # user_id or request values in the error message (preserves grouping).
        sentry_sdk.set_context(
            "opening_insights",
            {"user_id": user_id, "request": request.model_dump()},
        )
        sentry_sdk.capture_exception(exc)
        raise
