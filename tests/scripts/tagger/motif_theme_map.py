"""Motif -> lichess-theme map for the tagger validation harness (D-10).

Maps each FlawChess tactic motif string to the set of lichess puzzle theme names
that correspond to it. Lichess themes are camelCase (e.g. 'discoveredAttack'),
multi-label (a single puzzle can carry many themes), and space-separated in the
CSV 'Themes' column.

A precision hit is credited when the detector's motif is in the puzzle's theme
set via this map (D-10 multi-label matching): any intersection between our motif's
theme set and the puzzle's Themes counts as a true positive.

Sources:
  - lichess puzzleTheme.xml (https://github.com/lichess-org/lila/blob/master/
    translation/source/puzzleTheme.xml)
  - HuggingFace Lichess/chess-puzzles README (confirmed capturingDefender,
    xRayAttack, smotheredMate, anastasiaMate, hookMate, arabianMate, bodenMate)

Open Questions (resolved at selector-run time):
  OQ-1: exact spelling of 'hangingPiece' vs 'hanging' in actual CSV rows.
        The selector script prints the 50 most common themes so the mapping can
        be verified on first run. If the theme name differs, update this map and
        re-run the selector.
  OQ-2: 'double-bishop-mate' may not appear as a labeled theme in the CSV.
        Marked as UNVALIDATED_MOTIFS pending confirmation. If found (e.g. as
        'doubleBishopMate'), add it here and remove from UNVALIDATED_MOTIFS.

MOTIF_TO_THEMES: dict[str, tuple[str, ...]]
  Keys are FlawChess motif strings (matching TacticMotif Literal values).
  Values are tuples of lichess theme names that count as a match.
  Multi-value tuples (e.g. mate -> mate + mateIn1..mateIn5) credit any match.

UNVALIDATED_MOTIFS: frozenset[str]
  Motifs with no confirmed lichess theme equivalent. These are tracked separately
  so the harness can report them as "unvalidated" rather than "failing" — their
  precision cannot be measured against the CC0 puzzle set.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Motif -> lichess theme map (D-10 multi-label)
# ---------------------------------------------------------------------------

MOTIF_TO_THEMES: dict[str, tuple[str, ...]] = {
    # --- Core geometric motifs ---
    "fork": ("fork",),
    # OQ-1: 'hangingPiece' spelling confirmed from HuggingFace README; verify in actual data.
    "hanging-piece": ("hangingPiece",),
    "pin": ("pin",),
    "skewer": ("skewer",),
    "double-check": ("doubleCheck",),
    "discovered-check": ("discoveredCheck",),
    "discovered-attack": ("discoveredAttack",),
    "trapped-piece": ("trappedPiece",),
    # --- Mate motifs ---
    # 'mate' is the catch-all; mateInN provide finer-grained coverage.
    "back-rank-mate": ("backRankMate",),
    "mate": ("mate", "mateIn1", "mateIn2", "mateIn3", "mateIn4", "mateIn5"),
    "smothered-mate": ("smotheredMate",),
    "anastasia-mate": ("anastasiaMate",),
    "hook-mate": ("hookMate",),
    "arabian-mate": ("arabianMate",),
    "boden-mate": ("bodenMate",),
    "dovetail-mate": ("dovetailMate",),
    # --- Tier-3 motifs ---
    "deflection": ("deflection",),
    "attraction": ("attraction",),
    "intermezzo": ("intermezzo",),
    # xRayAttack confirmed in HuggingFace README.
    "x-ray": ("xRayAttack",),
    "interference": ("interference",),
    "clearance": ("clearance",),
    # capturingDefender confirmed in HuggingFace README.
    "capturing-defender": ("capturingDefender",),
    "sacrifice": ("sacrifice",),
    # --- Move-type family (Phase 128.1-02, D-02) ---
    # Detected + stored for lichess parity; chip-surfacing is Phase 129 (D-09).
    "en-passant": ("enPassant",),
    "promotion": ("promotion",),
    "under-promotion": ("underPromotion",),
}

# ---------------------------------------------------------------------------
# Unvalidated motifs — no confirmed lichess theme equivalent (D-10)
# ---------------------------------------------------------------------------

UNVALIDATED_MOTIFS: frozenset[str] = frozenset(
    {
        # 'self-interference' is not in the lichess puzzle theme vocabulary.
        "self-interference",
        # 'double-bishop-mate' is not confirmed as a lichess theme.
        # OQ-2: verify on first selector run; add to MOTIF_TO_THEMES if found.
        "double-bishop-mate",
    }
)
