"""Phase 70 (v1.13) opening insights service.

Single public entry point: compute_insights(session, user_id, request).
Pipeline: query_opening_transitions (per color) -> classify + severity ->
attribute (deepest Opening / lineage walk / drop on no match) ->
dedupe within color section -> rank (severity desc, n_games desc) ->
cap per section (5 weaknesses, 3 strengths). No precompute, no caching
(D-29) — partial-index-backed query keeps even Hikaru-class users <1 s.

See .planning/phases/70-backend-opening-insights-service/70-CONTEXT.md
for D-01..D-34 locked decisions.
"""

import ctypes
import datetime
from typing import Any, Literal

import chess
import chess.polyglot
import sentry_sdk
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opening import Opening
from app.repositories.openings_repository import (
    query_opening_transitions,
    query_openings_by_hashes,
)
from app.schemas.opening_insights import (
    OpeningInsightFinding,
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_LIGHT_THRESHOLD as LIGHT_THRESHOLD,
)
from app.services.openings_service import recency_cutoff

# ---------------------------------------------------------------------------
# Phase 70 thresholds. Mirror frontend/src/lib/arrowColor.ts so opening
# insights and board arrow colors stay in lock-step (CI-enforced via
# tests/services/test_opening_insights_arrow_consistency.py).
# Shared thresholds (also used by the SQL HAVING clause in the repository)
# are imported from app.services.opening_insights_constants above.
# ---------------------------------------------------------------------------

DARK_THRESHOLD: float = 0.60  # arrowColor.ts DARK_COLOR_THRESHOLD/100
WEAKNESS_CAP_PER_COLOR: int = 5
STRENGTH_CAP_PER_COLOR: int = 3
UNNAMED_LINE_NAME: str = "<unnamed line>"
UNNAMED_LINE_ECO: str = ""


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------


def _classify_row(
    row: Any,
) -> tuple[Literal["weakness", "strength"], Literal["minor", "major"]] | None:
    """Classify a transition row as weakness or strength, with severity.

    Uses strict > boundary at LIGHT_THRESHOLD (0.55) mirroring arrowColor.ts
    lines 49-57. Returns None for neutral positions (D-04).
    """
    loss_rate = row.l / row.n
    win_rate = row.w / row.n
    if loss_rate > LIGHT_THRESHOLD:
        severity: Literal["minor", "major"] = "major" if loss_rate >= DARK_THRESHOLD else "minor"
        return "weakness", severity
    if win_rate > LIGHT_THRESHOLD:
        severity = "major" if win_rate >= DARK_THRESHOLD else "minor"
        return "strength", severity
    return None


def _compute_score(row: Any) -> float:
    """Compute score = (W + D/2) / n. Informative only per D-06."""
    return (row.w + row.d / 2) / row.n


def _replay_san_sequence(san_sequence: list[str]) -> str:
    """Replay a space-separated SAN sequence from the start position.

    Implements D-25 entry-FEN reconstruction by replaying the exact moves
    the user played up to the entry position. Never falls back to the initial
    position (D-34).
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
    disagrees with the opening's parity, prefix with 'vs. ' per RESEARCH.md
    Pitfall 4 and stats_repository.py lines 250-260.
    """
    user_parity = 1 if finding_color == "white" else 0
    if opening_ply_count % 2 != user_parity:
        return f"vs. {name}"
    return name


def _compute_prefix_hashes(san_sequence: list[str]) -> list[int]:
    """Return the full_hash for every proper prefix (deepest first).

    BLOCKER-2: hashes MUST be converted via ctypes.c_int64(...).value to
    match the signed int64 stored on GamePosition.full_hash. Without this
    conversion, lookups against the openings table (whose Opening.full_hash
    is also signed via the same path) would silently miss every match.
    """
    board = chess.Board()
    hashes: list[int] = []
    for san in san_sequence:
        board.push_san(san)
        hashes.append(ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value)
    # Drop the LAST entry (full sequence == the entry position itself, which
    # was already covered by direct attribution). Deepest parent first.
    return list(reversed(hashes[:-1]))


def _attribute_finding(
    row: Any,
    openings_by_hash: dict[int, Opening],
    parents_by_hash: dict[int, Opening],
    finding_color: Literal["white", "black"],
) -> tuple[str, str, str] | None:
    """Attribute a finding to an opening name (BLOCKER-1 / D-22 / D-23 / D-34).

    Returns (opening_name, opening_eco, display_name) or None when no match
    is found at any lineage depth — None causes the finding to be DROPPED
    per D-34 (never surfaced with a sentinel name).

    Attribution path:
    1. Direct: look up entry_hash in openings_by_hash.
    2. Lineage walk: check parent prefix hashes in parents_by_hash (deepest first).
    3. No match → return None. Sentry tag set by calling pipeline on drop.
    """
    entry_hash_int = int(row.entry_hash)

    # Pass 1: direct attribution
    direct_opening = openings_by_hash.get(entry_hash_int)
    if direct_opening is not None:
        display_name = _apply_display_name_parity(
            direct_opening.name, direct_opening.ply_count, finding_color
        )
        return direct_opening.name, direct_opening.eco, display_name

    # Pass 2: lineage walk (deepest first)
    san_seq = list(row.entry_san_sequence or [])
    for prefix_hash in _compute_prefix_hashes(san_seq):
        parent_opening = parents_by_hash.get(prefix_hash)
        if parent_opening is not None:
            display_name = _apply_display_name_parity(
                parent_opening.name, parent_opening.ply_count, finding_color
            )
            return parent_opening.name, parent_opening.eco, display_name

    # No match at any depth — D-34: drop this finding
    return None


def _dedupe_within_section(
    items: list[tuple[OpeningInsightFinding, int]],
) -> list[OpeningInsightFinding]:
    """Deduplicate by resulting_full_hash within a section, keeping the deepest entry.

    D-24: when two findings share resulting_full_hash in the same color section,
    keep the one with the higher attribution ply_count (deeper opening wins).
    """
    best: dict[str, tuple[OpeningInsightFinding, int]] = {}
    for finding, ply_count in items:
        key = finding.resulting_full_hash
        existing = best.get(key)
        if existing is None or ply_count > existing[1]:
            best[key] = (finding, ply_count)
    return [finding for finding, _ in best.values()]


def _rank_section(findings: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    """Sort findings by (severity desc, n_games desc) per D-07.

    'major' comes before 'minor'; within each tier, higher n_games first.
    Ascending sort with negated n_games achieves descending n_games.
    """
    return sorted(
        findings,
        key=lambda f: (0 if f.severity == "major" else 1, -f.n_games),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def compute_insights(
    session: AsyncSession,
    user_id: int,
    request: OpeningInsightsRequest,
) -> OpeningInsightsResponse:
    """Compute four-section opening insights for one user under a filter set.

    Returns OpeningInsightsResponse with white_weaknesses, black_weaknesses,
    white_strengths, black_strengths — each capped per CONTEXT.md D-08.
    See module docstring for pipeline details.
    """
    cutoff: datetime.datetime | None = recency_cutoff(request.recency)

    # D-12 optimization: when the user narrows to a single color, skip the
    # off-color SQL query entirely (~50% latency saving).
    colors_to_query: list[Literal["white", "black"]]
    if request.color == "all":
        colors_to_query = ["white", "black"]
    else:
        colors_to_query = [request.color]

    # WARN-1: the full pipeline (queries + classify + attribute + dedupe +
    # rank + cap) is wrapped in a single try/except so any exception in
    # pure-Python stages also gets the Sentry context + tags.
    try:
        rows_by_color: dict[str, list[Row[Any]]] = {}
        # CLAUDE.md §Critical Constraints: AsyncSession not safe for asyncio.gather.
        for color in colors_to_query:
            rows_by_color[color] = await query_opening_transitions(
                session=session,
                user_id=user_id,
                color=color,
                time_control=request.time_control,
                platform=request.platform,
                rated=request.rated,
                opponent_type=request.opponent_type,
                recency_cutoff=cutoff,
                opponent_strength=request.opponent_strength,
                elo_threshold=request.elo_threshold,
            )

        # Pass 1: direct attribution for all entry hashes.
        direct_entry_hashes = list(
            {int(r.entry_hash) for rows in rows_by_color.values() for r in rows}
        )
        openings_by_hash = await query_openings_by_hashes(session, direct_entry_hashes)

        # Pass 2: parent-lineage attribution for unmatched (BLOCKER-1 / D-34).
        unmatched_parent_hashes: set[int] = set()
        for rows in rows_by_color.values():
            for r in rows:
                if int(r.entry_hash) not in openings_by_hash:
                    unmatched_parent_hashes.update(
                        _compute_prefix_hashes(list(r.entry_san_sequence or []))
                    )
        parents_by_hash = await query_openings_by_hashes(session, list(unmatched_parent_hashes))

        # ---- Build sections ----
        # Each section accumulates (OpeningInsightFinding, ply_count) tuples for D-24 dedupe.
        sections: dict[str, list[tuple[OpeningInsightFinding, int]]] = {
            "white_weaknesses": [],
            "black_weaknesses": [],
            "white_strengths": [],
            "black_strengths": [],
        }

        for color in colors_to_query:
            color_literal: Literal["white", "black"] = color
            for row in rows_by_color[color]:
                cls = _classify_row(row)
                if cls is None:
                    continue
                classification, severity = cls

                # BLOCKER-1: single attribution path. None => DROP per D-34.
                attribution = _attribute_finding(
                    row, openings_by_hash, parents_by_hash, color_literal
                )
                if attribution is None:
                    sentry_sdk.set_tag("openings.attribution.unmatched_dropped", True)
                    continue
                opening_name, opening_eco, display_name = attribution

                # BLOCKER-1 / D-25: entry_fen reconstructed by replaying the
                # actual SAN sequence the user played up to the entry. Never
                # fall back to chess.Board().fen() (initial position) — D-34.
                entry_fen = _replay_san_sequence(list(row.entry_san_sequence or []))

                # Carry the matched Opening.ply_count alongside for D-24
                # deeper-entry-wins dedupe; use 0 for parent-only matches
                # (parent-matched entries have lower specificity than direct matches).
                matched_opening = openings_by_hash.get(int(row.entry_hash))
                opening_ply_count = matched_opening.ply_count if matched_opening else 0

                win_rate = row.w / row.n
                loss_rate = row.l / row.n
                score = _compute_score(row)

                finding = OpeningInsightFinding(
                    color=color_literal,
                    classification=classification,
                    severity=severity,
                    opening_name=opening_name,
                    opening_eco=opening_eco,
                    display_name=display_name,
                    entry_fen=entry_fen,
                    entry_san_sequence=list(row.entry_san_sequence or []),  # Phase 71 (D-13): expose SAN sequence for FE deep-link replay
                    # BLOCKER-5 / Pitfall 1: stringify 64-bit ints at the API boundary.
                    entry_full_hash=str(int(row.entry_hash)),
                    candidate_move_san=row.move_san,
                    resulting_full_hash=str(int(row.resulting_full_hash)),
                    n_games=row.n,
                    wins=row.w,
                    draws=row.d,
                    losses=row.l,
                    win_rate=win_rate,
                    loss_rate=loss_rate,
                    score=score,
                )

                section_key = (
                    f"{color}_{'weaknesses' if classification == 'weakness' else 'strengths'}"
                )
                sections[section_key].append((finding, opening_ply_count))

        # Dedupe + rank + cap per section (D-02 caps: 5 weaknesses, 3 strengths).
        final_sections: dict[str, list[OpeningInsightFinding]] = {}
        for key, items in sections.items():
            deduped = _dedupe_within_section(items)
            ranked = _rank_section(deduped)
            cap = WEAKNESS_CAP_PER_COLOR if "weaknesses" in key else STRENGTH_CAP_PER_COLOR
            final_sections[key] = ranked[:cap]

        return OpeningInsightsResponse(
            white_weaknesses=final_sections["white_weaknesses"],
            black_weaknesses=final_sections["black_weaknesses"],
            white_strengths=final_sections["white_strengths"],
            black_strengths=final_sections["black_strengths"],
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
