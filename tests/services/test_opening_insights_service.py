"""Phase 70 service unit tests — INSIGHT-CORE-04, INSIGHT-CORE-05, INSIGHT-CORE-06, INSIGHT-CORE-07.

Tests cover the compute_insights() pipeline: classification boundaries,
severity tiers, deduplication, ranking, caps, attribution, display name
parity, color optimization, and bookmark isolation (D-18).
"""

from __future__ import annotations

import ctypes
from typing import Any, Literal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import chess
import chess.polyglot
import pytest

from app.models.opening import Opening
from app.schemas.opening_insights import (
    OpeningInsightFinding,
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE as MIN_GAMES_PER_CANDIDATE,
)
from app.services.opening_insights_service import (
    WEAKNESS_CAP_PER_COLOR,
    STRENGTH_CAP_PER_COLOR,
    _classify_row,
    _rank_section,
    compute_insights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    *,
    entry_hash: int = 100,
    move_san: str = "Nf3",
    resulting_full_hash: int = 200,
    entry_san_sequence: list[str] | None = None,
    n: int = 20,
    w: int = 4,
    d: int = 4,
    losses: int = 12,
) -> SimpleNamespace:
    """Construct a synthetic repository Row compatible with compute_insights."""
    if entry_san_sequence is None:
        entry_san_sequence = ["e4", "c5", "Nf3"]
    return SimpleNamespace(
        entry_hash=entry_hash,
        move_san=move_san,
        resulting_full_hash=resulting_full_hash,
        entry_san_sequence=entry_san_sequence,
        n=n,
        w=w,
        d=d,
        l=losses,
    )


def _make_opening(
    *,
    full_hash: int = 100,
    name: str = "Sicilian Defense",
    eco: str = "B20",
    ply_count: int = 4,
    pgn: str = "e4 c5",
) -> Opening:
    opening = MagicMock(spec=Opening)
    opening.full_hash = full_hash
    opening.name = name
    opening.eco = eco
    opening.ply_count = ply_count
    opening.pgn = pgn
    return opening


def _default_request(**kwargs: Any) -> OpeningInsightsRequest:
    defaults: dict[str, Any] = {"color": "white"}
    defaults.update(kwargs)
    return OpeningInsightsRequest(**defaults)


async def _run_compute(
    rows: list[SimpleNamespace],
    openings_by_hash: dict[int, Opening] | None = None,
    color: str = "white",
) -> OpeningInsightsResponse:
    """Helper: patch both repo functions and run compute_insights."""
    if openings_by_hash is None:
        openings_by_hash = {100: _make_opening()}

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        mock_transitions.return_value = rows
        mock_attribution.return_value = openings_by_hash

        return await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color=color),
        )


# ---------------------------------------------------------------------------
# Classification boundary tests (D-03, D-11; Phase 75)
# ---------------------------------------------------------------------------


def test_classify_row_neutral_score_046_returns_none() -> None:
    """D-03 strict <=/>= boundaries: score=0.46 → not a finding (neutral, |delta|<0.05)."""
    # n=100, w=40, d=12, l=48 → score = (40 + 6)/100 = 0.46
    row = _make_row(n=100, w=40, d=12, losses=48)
    assert _classify_row(row) is None


def test_classify_row_neutral_score_054_returns_none() -> None:
    """D-03 strict boundary: score=0.54 → not a finding (neutral, |delta|<0.05)."""
    # n=100, w=48, d=12, l=40 → score = (48 + 6)/100 = 0.54
    row = _make_row(n=100, w=48, d=12, losses=40)
    assert _classify_row(row) is None


def test_classify_row_minor_weakness_at_score_045_exact() -> None:
    """D-03/D-11: score=0.45 exactly → minor weakness (delta=-0.05, strict <=)."""
    # n=20, w=5, d=8, l=7 → score = (5 + 4)/20 = 0.45 exactly
    row = _make_row(n=20, w=5, d=8, losses=7)
    result = _classify_row(row)
    assert result is not None
    classification, severity = result
    assert classification == "weakness"
    assert severity == "minor"


def test_classify_row_major_weakness_at_score_040_exact() -> None:
    """D-03/D-11: score=0.40 → major weakness (delta=-0.10, strict <=)."""
    # n=20, w=4, d=8, l=8 → score = (4 + 4)/20 = 0.40 exactly
    row = _make_row(n=20, w=4, d=8, losses=8)
    result = _classify_row(row)
    assert result is not None
    classification, severity = result
    assert classification == "weakness"
    assert severity == "major"


def test_classify_row_minor_strength_at_score_055_exact() -> None:
    """D-03/D-11: score=0.55 → minor strength (delta=+0.05, strict >=)."""
    # n=20, w=8, d=6, l=6 → score = (8 + 3)/20 = 0.55 exactly
    row = _make_row(n=20, w=8, d=6, losses=6)
    result = _classify_row(row)
    assert result is not None
    classification, severity = result
    assert classification == "strength"
    assert severity == "minor"


def test_classify_row_major_strength_at_score_060_exact() -> None:
    """D-03/D-11: score=0.60 → major strength (delta=+0.10, strict >=)."""
    # n=20, w=10, d=4, l=6 → score = (10 + 2)/20 = 0.60 exactly
    row = _make_row(n=20, w=10, d=4, losses=6)
    result = _classify_row(row)
    assert result is not None
    classification, severity = result
    assert classification == "strength"
    assert severity == "major"


# ---------------------------------------------------------------------------
# Evidence floor (D-04 / Phase 75 INSIGHT-SCORE-05)
# ---------------------------------------------------------------------------


def test_min_games_floor_constant_is_10() -> None:
    """D-04 / Phase 75 INSIGHT-SCORE-05: discovery floor dropped from 20 to 10."""
    assert MIN_GAMES_PER_CANDIDATE == 10


def test_classify_row_does_not_filter_below_min_games() -> None:
    """The SQL HAVING clause owns the n>=10 floor; _classify_row only inspects score."""
    # n=8, w=2, d=2, l=4 → score = (2+1)/8 = 0.375 → major weakness regardless of n
    row = _make_row(n=8, w=2, d=2, losses=4)
    assert _classify_row(row) is not None


# ---------------------------------------------------------------------------
# Deduplication (D-21, D-24)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedupe_within_section_keeps_deepest_entry() -> None:
    """D-21, D-24: when two findings share resulting_full_hash in same section,
    keep the one with the deeper (higher ply_count) entry attribution."""
    # Two rows: same resulting_full_hash (999), same section (white weaknesses)
    # but different entry hashes (100 → ply_count=2, 200 → ply_count=6)
    row_shallow = _make_row(entry_hash=100, resulting_full_hash=999, n=20, w=2, d=2, losses=16)
    row_deep = _make_row(
        entry_hash=200,
        resulting_full_hash=999,
        entry_san_sequence=["e4", "c5", "Nf3", "d6"],
        n=30,
        w=3,
        d=3,
        losses=24,
    )

    opening_shallow = _make_opening(full_hash=100, name="Shallow Line", ply_count=2)
    opening_deep = _make_opening(full_hash=200, name="Deep Line", ply_count=6)

    response = await _run_compute(
        rows=[row_shallow, row_deep],
        openings_by_hash={100: opening_shallow, 200: opening_deep},
        color="white",
    )
    # Only one finding should survive dedupe (both are weaknesses, same resulting hash)
    assert len(response.white_weaknesses) == 1
    # The deeper entry (ply_count=6) wins
    assert response.white_weaknesses[0].opening_name == "Deep Line"


@pytest.mark.asyncio
async def test_cross_color_same_hash_kept_as_two_findings() -> None:
    """D-21: same resulting_full_hash in white and black sections → both kept."""
    # One row classified as weakness for white, one for black
    # same resulting_full_hash across colors
    row_white = _make_row(entry_hash=100, resulting_full_hash=999, n=20, w=2, d=2, losses=16)
    row_black = _make_row(entry_hash=100, resulting_full_hash=999, n=20, w=2, d=2, losses=16)
    opening = _make_opening(full_hash=100)

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        # First call (white) → row_white, second call (black) → row_black
        mock_transitions.side_effect = [
            [row_white],
            [row_black],
        ]
        mock_attribution.return_value = {100: opening}

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="all"),
        )

    # Both sections should have one finding (cross-color dedup does NOT happen)
    assert len(response.white_weaknesses) == 1
    assert len(response.black_weaknesses) == 1


@pytest.mark.asyncio
async def test_continuation_dedupe_collapses_chain_across_sections() -> None:
    """Phase 71 UAT fix: a chain of consecutive weak moves in the same line
    collapses to the shortest entry, even when the chain crosses color sections.

    Reproduces the Caro-Kann B10 case reported during UAT:
      - 1.e4 c6 2.Nc3 d5 3.exd5    (white weakness)
      - 1.e4 c6 2.Nc3 d5 3.exd5 cxd5    (black weakness)
      - 1.e4 c6 2.Nc3 d5 3.exd5 cxd5 4.d4    (white weakness)

    Only the shortest entry (3.exd5) should remain — its cover prefix
    [e4,c6,Nc3,d5,exd5] subsumes both deeper findings.
    """
    row_white_shallow = _make_row(
        entry_hash=100,
        move_san="exd5",
        resulting_full_hash=200,
        entry_san_sequence=["e4", "c6", "Nc3", "d5"],
        n=20,
        w=4,
        d=4,
        losses=12,
    )
    row_white_deep = _make_row(
        entry_hash=300,
        move_san="d4",
        resulting_full_hash=400,
        entry_san_sequence=["e4", "c6", "Nc3", "d5", "exd5", "cxd5"],
        n=20,
        w=3,
        d=4,
        losses=13,
    )
    row_black_mid = _make_row(
        entry_hash=200,
        move_san="cxd5",
        resulting_full_hash=300,
        entry_san_sequence=["e4", "c6", "Nc3", "d5", "exd5"],
        n=20,
        w=4,
        d=4,
        losses=12,
    )
    opening_a = _make_opening(full_hash=100, name="Caro-Kann Defense", eco="B10", ply_count=4)
    opening_b = _make_opening(full_hash=200, name="Caro-Kann Defense", eco="B10", ply_count=5)
    opening_c = _make_opening(full_hash=300, name="Caro-Kann Defense", eco="B10", ply_count=6)

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        # White call returns shallow + deep, black call returns mid.
        mock_transitions.side_effect = [
            [row_white_shallow, row_white_deep],
            [row_black_mid],
        ]
        mock_attribution.return_value = {100: opening_a, 200: opening_b, 300: opening_c}

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="all"),
        )

    # Only the shortest finding (3.exd5) should survive — both deeper continuations
    # are subsumed by the shallow finding's cover prefix.
    assert len(response.white_weaknesses) == 1
    assert response.white_weaknesses[0].candidate_move_san == "exd5"
    assert len(response.black_weaknesses) == 0


@pytest.mark.asyncio
async def test_continuation_dedupe_keeps_sibling_lines_at_same_depth() -> None:
    """Two findings sharing the same entry but with different candidate moves
    are siblings, not a chain — both must be kept (different cover prefixes)."""
    # Same entry position, two different candidate moves → both classified as weak.
    row_a = _make_row(
        entry_hash=100,
        move_san="exd5",
        resulting_full_hash=200,
        entry_san_sequence=["e4", "c6", "Nc3", "d5"],
        n=20,
        w=4,
        d=4,
        losses=12,
    )
    row_b = _make_row(
        entry_hash=100,
        move_san="d3",
        resulting_full_hash=201,
        entry_san_sequence=["e4", "c6", "Nc3", "d5"],
        n=20,
        w=4,
        d=4,
        losses=12,
    )
    opening = _make_opening(full_hash=100, name="Caro-Kann Defense", eco="B10", ply_count=4)
    response = await _run_compute(
        rows=[row_a, row_b],
        openings_by_hash={100: opening},
        color="white",
    )
    # Sibling candidates from the same entry are NOT a continuation chain.
    assert len(response.white_weaknesses) == 2
    candidates = {f.candidate_move_san for f in response.white_weaknesses}
    assert candidates == {"exd5", "d3"}


# ---------------------------------------------------------------------------
# Attribution (D-22, D-23, D-24)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attribution_picks_max_ply_count() -> None:
    """D-22: when multiple openings share entry_hash, the one with MAX(ply_count) wins.

    query_openings_by_hashes already handles this (Plan 70-03). Here we verify
    the service uses the returned opening name correctly.
    """
    # The mock already returns deepest opening by ply_count (as the repo does)
    opening = _make_opening(full_hash=100, name="Deep Sicilian", ply_count=8, eco="B70")
    response = await _run_compute(
        rows=[_make_row(n=20, w=4, d=4, losses=12)],
        openings_by_hash={100: opening},
        color="white",
    )
    assert len(response.white_weaknesses) == 1
    assert response.white_weaknesses[0].opening_name == "Deep Sicilian"
    assert response.white_weaknesses[0].opening_eco == "B70"


@pytest.mark.asyncio
async def test_finding_includes_entry_san_sequence() -> None:
    """Phase 71 (D-13): entry_san_sequence is exposed on the wire schema.

    Asserts:
      - field is a list of str
      - length >= MIN_ENTRY_PLY=3 (entry_ply >= 3 guaranteed by service)
      - replaying the sequence on a fresh chess.Board reproduces entry_fen exactly
    """
    opening = _make_opening(full_hash=100, name="Sicilian Defense", ply_count=4, eco="B20")
    # Default _make_row() uses entry_san_sequence=["e4", "c5", "Nf3"] (3 plys)
    row = _make_row(n=20, w=4, d=4, losses=12)
    response = await _run_compute(
        rows=[row],
        openings_by_hash={100: opening},
        color="white",
    )
    assert len(response.white_weaknesses) == 1
    finding = response.white_weaknesses[0]

    # Phase 71 (D-13): entry_san_sequence is the SAN sequence from the start
    # position to the entry position (candidate excluded). Must be a non-empty
    # list[str] with length >= MIN_ENTRY_PLY=3, and must replay to entry_fen.
    assert isinstance(finding.entry_san_sequence, list)
    assert all(isinstance(san, str) for san in finding.entry_san_sequence)
    assert len(finding.entry_san_sequence) >= 3, (
        f"entry_san_sequence must have at least MIN_ENTRY_PLY=3 plys, got {len(finding.entry_san_sequence)}"
    )
    # Replaying the SAN sequence must reproduce entry_fen exactly
    _board = chess.Board()
    for _san in finding.entry_san_sequence:
        _board.push_san(_san)
    assert _board.fen() == finding.entry_fen, (
        f"Replaying entry_san_sequence must reproduce entry_fen.\n"
        f"  expected: {finding.entry_fen}\n"
        f"  got:      {_board.fen()}"
    )


@pytest.mark.asyncio
async def test_attribution_lineage_walk_to_parent_hash() -> None:
    """D-23: when entry_hash has no direct openings match, walk parent lineage.

    Builds a real SAN sequence ["e4", "c5", "Nf3"], computes the full_hash at
    ply=2 (after "c5") as the 'Sicilian Defense' opening hash, and seeds an
    Opening row with that hash. The row's entry_hash is the hash at ply=3
    (post-Nf3), which has NO direct Opening row.

    The service must walk back to the ply=2 parent hash and return the
    'Sicilian Defense' name.
    """
    # Compute the Zobrist hash at ply=2 (after "c5") — the Sicilian Defense position
    board = chess.Board()
    board.push_san("e4")
    board.push_san("c5")
    parent_hash = ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value

    # The entry is at ply=3 (after Nf3) — this hash has no Opening row
    board.push_san("Nf3")
    entry_hash_at_ply3 = ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value

    parent_opening = _make_opening(
        full_hash=parent_hash,
        name="Sicilian Defense",
        eco="B20",
        ply_count=2,
    )

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        row = _make_row(
            entry_hash=entry_hash_at_ply3,
            entry_san_sequence=["e4", "c5", "Nf3"],
            n=20,
            w=2,
            d=2,
            losses=16,
        )
        mock_transitions.return_value = [row]

        # Pass 1: direct attribution → no match for entry_hash_at_ply3
        # Pass 2: parent attribution → returns parent_opening for parent_hash
        mock_attribution.side_effect = [
            {},  # direct pass: no opening at ply=3
            {parent_hash: parent_opening},  # parent pass: Sicilian at ply=2
        ]

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="white"),
        )

    assert len(response.white_weaknesses) == 1
    assert response.white_weaknesses[0].opening_name == "Sicilian Defense"


@pytest.mark.asyncio
async def test_attribution_drops_finding_when_no_lineage_match() -> None:
    """Per D-34, findings with no direct match AND no parent ancestor in the
    openings table are DROPPED from the response, not surfaced with a sentinel."""
    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        row = _make_row(n=20, w=2, d=2, losses=16, entry_hash=9999)
        mock_transitions.return_value = [row]
        # Both passes return empty dicts — no attribution possible
        mock_attribution.return_value = {}

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="white"),
        )

    # Finding is dropped — no sentinel '<unnamed line>' surfaced
    assert len(response.white_weaknesses) == 0


@pytest.mark.asyncio
async def test_unnamed_line_fallback_uses_empty_eco_and_sentinel_name() -> None:
    """D-23: this test verifies UNNAMED_LINE_* constants exist and are correct.

    Per D-34, unnamed-line findings are dropped in Phase 70 (not surfaced).
    The constants are defined for telemetry/future use but not emitted on
    responses. We verify the constants exist with correct values.
    """
    from app.services.opening_insights_service import UNNAMED_LINE_ECO, UNNAMED_LINE_NAME

    assert UNNAMED_LINE_NAME == "<unnamed line>"
    assert UNNAMED_LINE_ECO == ""


# ---------------------------------------------------------------------------
# Ranking and caps (D-07, D-02, D-08)
# ---------------------------------------------------------------------------


def _make_weakness_finding(
    score: float,
    candidate: str,
    confidence: Literal["low", "medium", "high"] = "high",
    n_games: int = 400,
) -> OpeningInsightFinding:
    """Build a minimal weakness OpeningInsightFinding for ranking-level tests.

    Quick task 260428-v9i: ranking now uses the Wilson 95% score interval, which
    is derived from `score` and `n_games` directly (no SE input). Tests therefore
    drive uncertainty via `n_games` rather than synthetic SE values; the SE
    component of the (finding, se) tuple is preserved upstream but ignored by
    `_rank_section`. wins/losses are derived from `score * n_games` so the
    finding is internally consistent for downstream display.
    """
    wins = int(round(score * n_games))
    return OpeningInsightFinding(
        color="white",
        classification="weakness",
        severity="major",
        opening_name="Test",
        opening_eco="A00",
        display_name="Test",
        entry_fen="",
        entry_san_sequence=[],
        entry_full_hash="0",
        candidate_move_san=candidate,
        resulting_full_hash="0",
        n_games=n_games,
        wins=wins,
        draws=0,
        losses=n_games - wins,
        score=score,
        confidence=confidence,
        p_value=0.5,
    )


def _make_strength_finding(
    score: float,
    candidate: str,
    confidence: Literal["low", "medium", "high"] = "high",
    n_games: int = 400,
) -> OpeningInsightFinding:
    wins = int(round(score * n_games))
    return OpeningInsightFinding(
        color="white",
        classification="strength",
        severity="major",
        opening_name="Test",
        opening_eco="A00",
        display_name="Test",
        entry_fen="",
        entry_san_sequence=[],
        entry_full_hash="0",
        candidate_move_san=candidate,
        resulting_full_hash="0",
        n_games=n_games,
        wins=wins,
        draws=0,
        losses=n_games - wins,
        score=score,
        confidence=confidence,
        p_value=0.5,
    )


def test_ranking_ignores_confidence_bucket_uses_ci_bound_only() -> None:
    """Quick task 260428-v9i: confidence bucket is no longer part of the sort
    key. A "medium" bucket row can outrank a "high" bucket row if its Wilson
    upper bound is more striking (and vice versa). Bucket is retained as a UI
    badge only.

      medium_tight: score=0.42, n_games=4000 -> Wilson upper ~ 0.4354.
      high_wide:    score=0.40, n_games=100  -> Wilson upper ~ 0.4980.

    Even though high_wide has the larger raw effect, medium_tight's tight CI
    sits much lower against the 0.5 pivot. medium_tight sorts first.
    """
    high_wide = _make_weakness_finding(
        score=0.40, candidate="high_wide", confidence="high", n_games=100
    )
    medium_tight = _make_weakness_finding(
        score=0.42, candidate="medium_tight", confidence="medium", n_games=4000
    )

    # SE values are arbitrary under Wilson — kept in the tuple for upstream
    # contract compatibility but ignored by _rank_section. Setting SE=0 here
    # would make the old Wald formula collapse to a pure score sort (giving
    # high_wide first), so this test also distinguishes Wilson from Wald.
    ranked = _rank_section(
        [(high_wide, 0.0), (medium_tight, 0.0)], direction="weakness"
    )
    assert [f.candidate_move_san for f in ranked] == ["medium_tight", "high_wide"], (
        "Tight medium-bucket row with stricter Wilson bound must outrank wide high-bucket row"
    )


def test_ranking_ci_upper_bound_tiebreak_within_same_confidence_for_weaknesses() -> None:
    """Quick task 260428-v9i: within a confidence bucket, weaknesses are ranked
    by Wilson 95% upper bound ASCENDING — the row whose score is most-confidently
    -below-0.5 sorts first. The fixture is chosen so that the new (Wilson upper)
    and old (|score - 0.5|) rules disagree:

      F1: score=0.40, n_games=10000 -> Wilson upper ~ 0.4096. |delta| = 0.10.
      F2: score=0.30, n_games=50    -> Wilson upper ~ 0.4375. |delta| = 0.20.

    Old rule (|score-0.5| desc): F2 first (|delta|=0.20 > 0.10).
    New rule (upper bound asc):  F1 first (0.4096 < 0.4375) — F1's CI is much
    tighter and stays well below 0.5, so F1 is the more-confidently-bad row.
    """
    f1 = _make_weakness_finding(score=0.40, candidate="f1", confidence="high", n_games=10000)
    f2 = _make_weakness_finding(score=0.30, candidate="f2", confidence="high", n_games=50)

    # SE arbitrary (ignored by Wilson). 0.0 also makes the old Wald formula
    # collapse to score-only, where f2 (0.30) < f1 (0.40) — opposite of Wilson.
    ranked = _rank_section([(f2, 0.0), (f1, 0.0)], direction="weakness")
    assert [f.candidate_move_san for f in ranked] == ["f1", "f2"], (
        "F1 (tight CI, upper=0.4096) must outrank F2 (wide CI, upper=0.4375) within the same bucket"
    )


def test_ranking_small_n_high_effect_does_not_outrank_large_n_moderate_effect_within_bucket() -> (
    None
):
    """Must-have: a small-N high-effect finding should NOT outrank a large-N
    moderate-effect finding within the same bucket — small N widens the Wilson
    interval and demotes the row.

      A (small N, high effect):     score=0.20, n_games=10  -> Wilson upper ~ 0.5098.
      B (large N, moderate effect): score=0.30, n_games=400 -> Wilson upper ~ 0.3466.

    New Wilson-bound rule: B.upper (0.347) < A.upper (0.510) -> B sorts FIRST.
    Old |score-0.5| rule would have ordered A.|delta|=0.30 > B.|delta|=0.20 -> A first.
    """
    a_small_n = _make_weakness_finding(score=0.20, candidate="a", confidence="high", n_games=10)
    b_large_n = _make_weakness_finding(score=0.30, candidate="b", confidence="high", n_games=400)

    # SE=0 makes the old Wald formula collapse to score-only, where A (0.20)
    # would sort first — but Wilson correctly demotes the small-N row.
    ranked = _rank_section([(a_small_n, 0.0), (b_large_n, 0.0)], direction="weakness")
    assert [f.candidate_move_san for f in ranked] == ["b", "a"], (
        "Large-N moderate finding must outrank small-N high-effect finding under Wilson"
    )


def test_ranking_strength_uses_lower_bound() -> None:
    """Quick task 260428-v9i: strengths sort by Wilson 95% LOWER bound DESCENDING
    (most-confidently-good first). Symmetric to the weakness case.

      F1: score=0.60, n_games=10000 -> Wilson lower ~ 0.5904.
      F2: score=0.70, n_games=50    -> Wilson lower ~ 0.5625.

    F1's lower bound (0.59) is well above 0.5; F2's (0.56) hugs the pivot.
    F1 sorts first under the new rule despite having a smaller raw effect.
    """
    f1 = _make_strength_finding(score=0.60, candidate="f1", confidence="high", n_games=10000)
    f2 = _make_strength_finding(score=0.70, candidate="f2", confidence="high", n_games=50)

    # SE=0 collapses old Wald to score-only, where f2 (0.70) > f1 (0.60) and
    # would sort first — opposite of Wilson, which correctly tightens f1's
    # bound and pushes it above f2's.
    ranked = _rank_section([(f2, 0.0), (f1, 0.0)], direction="strength")
    assert [f.candidate_move_san for f in ranked] == ["f1", "f2"], (
        "F1 (tight CI, lower=0.5904) must outrank F2 (wide CI, lower=0.5625) within the same bucket"
    )


def test_ranking_bound_handles_boundary_scores() -> None:
    """Quick task 260428-v9i: Wilson is well-defined at boundary scores (p=0,
    p=1) — no Wald-style SE=0 degeneracy. The defensive clamp to [0, 1] is kept
    in the implementation for safety, but ordering does not depend on it.

    Weakness side:
      f_extreme: score=0.95, n_games=10  -> Wilson upper ~ 0.9948 (NOT clamped).
      f_normal:  score=0.30, n_games=400 -> Wilson upper ~ 0.3466.
    Normal row sorts first (its bound is much further below 0.5).

    Strength side:
      s_extreme: score=0.05, n_games=10  -> Wilson lower ~ 0.0052.
      s_normal:  score=0.70, n_games=400 -> Wilson lower ~ 0.6534.
    Normal row sorts first (its bound is much further above 0.5).
    """
    f_extreme = _make_weakness_finding(
        score=0.95, candidate="extreme", confidence="high", n_games=10
    )
    f_normal = _make_weakness_finding(
        score=0.30, candidate="normal", confidence="high", n_games=400
    )

    # SE values arbitrary — Wilson uses only score and n_games.
    ranked = _rank_section([(f_extreme, 0.0), (f_normal, 0.0)], direction="weakness")
    # Normal row (upper ~0.347) sorts before extreme row (upper ~0.995).
    assert [f.candidate_move_san for f in ranked] == ["normal", "extreme"]

    s_extreme = _make_strength_finding(
        score=0.05, candidate="extreme", confidence="high", n_games=10
    )
    s_normal = _make_strength_finding(
        score=0.70, candidate="normal", confidence="high", n_games=400
    )

    ranked_s = _rank_section([(s_extreme, 0.0), (s_normal, 0.0)], direction="strength")
    # Normal row (lower ~0.653) sorts before extreme row (lower ~0.005).
    assert [f.candidate_move_san for f in ranked_s] == ["normal", "extreme"]


@pytest.mark.asyncio
async def test_caps_10_per_color_per_classification() -> None:
    """D-02, D-08 + Phase 71 UAT: per-section caps applied after sorting: top-10 weaknesses, top-10 strengths."""
    assert WEAKNESS_CAP_PER_COLOR == 10
    assert STRENGTH_CAP_PER_COLOR == 10

    # Create 12 weakness rows — only 10 should survive cap.
    # Use fixed n=20, w=4, d=4, l=12 (score=0.30, major) so all rows classify.
    # Distinct entry/resulting hashes prevent dedupe from removing them.
    weakness_rows = [
        _make_row(
            entry_hash=i,
            resulting_full_hash=100 + i,
            entry_san_sequence=["e4"],  # valid SAN for all rows
            n=20,
            w=4,
            d=4,
            losses=12,  # score=(4+2)/20=0.30 → major weakness for all
        )
        for i in range(1, 13)
    ]
    openings_map = {
        i: _make_opening(full_hash=i, name=f"Opening {i}", ply_count=2) for i in range(1, 13)
    }

    response = await _run_compute(
        rows=weakness_rows,
        openings_by_hash=openings_map,
        color="white",
    )
    assert len(response.white_weaknesses) == WEAKNESS_CAP_PER_COLOR  # 10
    assert len(response.white_strengths) == 0  # no strength rows

    # Now create 12 strength rows — only 10 should survive cap.
    strength_rows = [
        _make_row(
            entry_hash=20 + i,
            resulting_full_hash=200 + i,
            entry_san_sequence=["e4"],
            n=20,
            w=14,
            d=3,
            losses=3,  # score=(14+1.5)/20=0.775 → major strength
        )
        for i in range(1, 13)
    ]
    openings_strength = {
        20 + i: _make_opening(full_hash=20 + i, name=f"Strength {i}", ply_count=2)
        for i in range(1, 13)
    }
    response2 = await _run_compute(
        rows=strength_rows,
        openings_by_hash=openings_strength,
        color="white",
    )
    assert len(response2.white_strengths) == STRENGTH_CAP_PER_COLOR  # 10
    assert len(response2.white_weaknesses) == 0


# ---------------------------------------------------------------------------
# Phase 75 D-09: confidence + p_value end-to-end smoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_insights_populates_confidence_and_p_value() -> None:
    """Phase 75 D-09: every finding carries confidence + p_value fields."""
    # Major weakness, n=20: score = (2 + 0.5*2)/20 = 0.15 (delta=-0.35, major).
    # variance = (2 + 0.25*2)/20 - 0.0225 = 0.125 - 0.0225 = 0.1025
    # se = sqrt(0.1025/20) ≈ 0.0716
    # z ≈ -4.89; p ≈ 1e-6; n=20 >= 10 → high
    row = _make_row(n=20, w=2, d=2, losses=16)
    opening = _make_opening()
    response = await _run_compute(rows=[row], openings_by_hash={100: opening}, color="white")

    assert len(response.white_weaknesses) == 1
    finding = response.white_weaknesses[0]
    assert finding.severity == "major"
    assert finding.score == pytest.approx(0.15)
    assert finding.confidence == "high"
    assert 0.0 <= finding.p_value <= 1.0


# ---------------------------------------------------------------------------
# Color optimization (D-12)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_color_optimization_skips_unused_color_query() -> None:
    """D-12: when request.color='white', only one SQL call issued; black sections empty."""
    row = _make_row(n=20, w=12, d=4, losses=4)  # strength
    opening = _make_opening(full_hash=100)

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        mock_transitions.return_value = [row]
        mock_attribution.return_value = {100: opening}

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="white"),
        )

        # Only ONE query_opening_transitions call (for white)
        assert mock_transitions.call_count == 1

    # Black sections must be empty
    assert response.black_weaknesses == []
    assert response.black_strengths == []
    # White section has the strength finding
    assert len(response.white_strengths) == 1


# ---------------------------------------------------------------------------
# Display name parity (D-22 / RESEARCH.md Pitfall 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_display_name_vs_prefix_when_attribution_parity_disagrees() -> None:
    """D-22 / Pitfall 4: black-section finding attributed to white-defined opening
    (odd ply_count) gets display_name = 'vs. <name>'."""
    # A white-defined opening has odd ply_count (white's move, e.g., ply_count=3 = after white's 2nd move)
    # When it appears in the BLACK section, parity disagrees → prefix "vs. "
    white_defined_opening = _make_opening(
        full_hash=100,
        name="London System",
        ply_count=3,  # odd → defined for white
    )
    row = _make_row(n=20, w=2, d=2, losses=16)

    with (
        patch(
            "app.services.opening_insights_service.query_opening_transitions",
            new_callable=AsyncMock,
        ) as mock_transitions,
        patch(
            "app.services.opening_insights_service.query_openings_by_hashes",
            new_callable=AsyncMock,
        ) as mock_attribution,
    ):
        mock_transitions.side_effect = [
            [],  # white query: no rows
            [row],  # black query: one weakness
        ]
        mock_attribution.return_value = {100: white_defined_opening}

        response = await compute_insights(
            session=AsyncMock(),
            user_id=1,
            request=_default_request(color="all"),
        )

    assert len(response.black_weaknesses) == 1
    finding = response.black_weaknesses[0]
    assert finding.display_name.startswith("vs. ")
    assert "London System" in finding.display_name


# ---------------------------------------------------------------------------
# Bookmarks isolation (D-18)
# ---------------------------------------------------------------------------


def test_bookmarks_not_consumed_by_algorithm() -> None:
    """D-18: bookmarks are NOT an algorithmic input; OpeningInsightsRequest has
    no bookmark field and the service signature does not accept bookmarks."""
    # Verify at the schema level: no bookmark field on request model
    assert "bookmark" not in OpeningInsightsRequest.model_fields

    # Verify compute_insights signature does not have a bookmark parameter
    import inspect

    sig = inspect.signature(compute_insights)
    param_names = list(sig.parameters.keys())
    assert "bookmark" not in param_names
    assert "bookmarks" not in param_names
