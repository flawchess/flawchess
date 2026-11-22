"""Committed score inputs of the two owner-labelled missed gains (Phase 254 plan 04, Phase 259 D-05).

Data only. The two positions of ``OWNER_MISS_FIXTURES`` (``line_material_fixtures``) with every
input of the scalar facepalm score (played probability, loss, missed gain, best-move probability and
best-reply probability), so the post-refit check needs neither prod nor Maia. The probabilities are
the values ``scripts/blunder_check/facepalm_features.py`` prints for these two positions, copied
exactly as printed (six significant digits):

    uv run --group maia-inference python scripts/blunder_check/facepalm_features.py \\
        --db dev --extra 817357:24 --extra 820181:65 --out temp/blunder-check/owner-fixtures-259.tsv

The dev database no longer holds these two games (the command prints "game or flaw row missing"), so
the same values were produced with the script's own pieces: the pinned Elo recovered from the
previously printed played probability (about 1543 and 1497), ``full_policy`` at the pre-blunder
board (played and best-move probability, equal to the 2026-11-14 print to six digits) and at the
post-blunder board (the reply probability, the first token of the committed refutation line), and
``facepalm_material_inputs`` on the committed line fixtures (loss and missed). Neither fixture
loses material under the quiet rule (loss 0), so the best-move term is the key-move term. Game ids
and plies only, no usernames.
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
    # Ba3 keeps material level, the best line (Qxg7) wins 3: loss 0, missed 3.
    OwnerFixtureFacts(
        game_id=817357,
        ply=24,
        facts=FacepalmFacts(
            played_prob=0.458327,
            loss=0.0,
            missed=3.0,
            best_prob=0.206584,
            reply_prob=0.244191,
        ),
    ),
    # Rxf5 wins a rook, the best line wins 10: loss 0, missed 5.
    OwnerFixtureFacts(
        game_id=820181,
        ply=65,
        facts=FacepalmFacts(
            played_prob=0.624289,
            loss=0.0,
            missed=5.0,
            best_prob=0.209111,
            reply_prob=0.523383,
        ),
    ),
)
