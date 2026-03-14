"""Opening lookup service using a trie-based longest-prefix matching algorithm.

Loads openings.tsv at module init and provides find_opening(pgn) for fast lookups.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# TSV loading and trie construction
# ---------------------------------------------------------------------------

_OPENINGS_TSV = Path(__file__).resolve().parent.parent / "data" / "openings.tsv"

# Trie: nested dicts keyed by SAN move string.
# Terminal nodes have a '_result' key storing (eco, name).
_TRIE: dict = {}


def _normalize_pgn_to_san_sequence(pgn: str | None) -> list[str]:
    """Convert a PGN string into a list of individual SAN move tokens.

    Steps:
    1. Return [] for falsy input.
    2. Strip PGN header lines (lines that start with '[').
    3. Remove block comments in {...} and variations in (...).
    4. Remove result markers: 1-0, 0-1, 1/2-1/2, *.
    5. Remove move numbers (digits followed by dots, e.g. '1.' '12.' '2...').
    6. Split on whitespace and filter empty tokens.
    """
    if not pgn:
        return []

    # Remove header lines (lines starting with '[')
    lines = pgn.splitlines()
    lines = [line for line in lines if not line.startswith("[")]
    text = " ".join(lines)

    # Remove block comments {...} (non-greedy, don't cross braces)
    text = re.sub(r"\{[^}]*\}", " ", text)

    # Remove variations (...) — simple single-depth removal
    text = re.sub(r"\([^)]*\)", " ", text)

    # Remove result markers
    text = re.sub(r"1-0|0-1|1/2-1/2|\*", " ", text)

    # Remove move numbers: digits followed by one or more dots (e.g. '1.' '12.' '2...')
    text = re.sub(r"\d+\.+", " ", text)

    # Split and filter
    tokens = [t for t in text.split() if t]
    return tokens


def _build_trie() -> dict:
    """Load openings.tsv and build a move-keyed trie."""
    trie: dict = {}
    with open(_OPENINGS_TSV, encoding="utf-8") as f:
        next(f)  # skip header line
        for line in f:
            line = line.rstrip("\n")
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            eco, name, pgn = parts
            moves = _normalize_pgn_to_san_sequence(pgn)
            if not moves:
                continue
            node = trie
            for move in moves:
                if move not in node:
                    node[move] = {}
                node = node[move]
            # Store result at terminal node (last entry wins for same sequence)
            node["_result"] = (eco, name)
    return trie


# Build the trie once at module load time
_TRIE = _build_trie()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_opening(pgn: str | None) -> tuple[str | None, str | None]:
    """Return (eco_code, opening_name) for the longest known opening prefix in pgn.

    Returns (None, None) if no match is found.
    """
    moves = _normalize_pgn_to_san_sequence(pgn)
    if not moves:
        return None, None

    node = _TRIE
    last_result: tuple[str, str] | None = None

    for move in moves:
        if move not in node:
            break
        node = node[move]
        if "_result" in node:
            last_result = node["_result"]

    if last_result is None:
        return None, None
    return last_result
