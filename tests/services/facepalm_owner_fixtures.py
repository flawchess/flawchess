"""Committed score inputs of the two owner-labelled missed gains (Phase 254 plan 04).

Data only. The two positions of ``OWNER_MISS_FIXTURES`` (``line_material_fixtures``) with every
input of the facepalm score, so the post-refit check (plan 12) needs neither prod nor Maia. The
values are the two rows ``scripts/blunder_check/facepalm_features.py`` printed on the dev
database on 2026-11-14, copied exactly as printed (six significant digits):

    uv run --group maia-inference python scripts/blunder_check/facepalm_features.py \\
        --db dev --extra 817357:24 --extra 820181:65 --out temp/blunder-check/owner-fixtures-features.tsv

Depth-3 signed material is positive when the blunderer is up; neither line mates within
LINE_DEPTH, so both mate plies are None. Game ids and plies only, no usernames.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.facepalm_score import FacepalmFacts


@dataclass(frozen=True)
class OwnerFixtureFacts:
    """The score inputs of one owner miss fixture (the game id and ply identify it)."""

    game_id: int
    ply: int
    facts: FacepalmFacts


OWNER_FIXTURE_FACTS: tuple[OwnerFixtureFacts, ...] = (
    # Ba3 keeps material level at depth 3, the best line (Qxg7) wins 3: missed 3.
    OwnerFixtureFacts(
        game_id=817357,
        ply=24,
        facts=FacepalmFacts(
            played_prob=0.458327,
            reply_spread=8.78072,
            played_3=0,
            mate_ply=None,
            best_3=3,
            best_mate_ply=None,
            best_prob=0.206584,
            pre_spread=5.2426,
        ),
    ),
    # Rxf5 wins a rook, the best line wins 10: missed 5.
    OwnerFixtureFacts(
        game_id=820181,
        ply=65,
        facts=FacepalmFacts(
            played_prob=0.624289,
            reply_spread=8.38388,
            played_3=5,
            mate_ply=None,
            best_3=10,
            best_mate_ply=None,
            best_prob=0.209111,
            pre_spread=2.5917,
        ),
    ),
)
