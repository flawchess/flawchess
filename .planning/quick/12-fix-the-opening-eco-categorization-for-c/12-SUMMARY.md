---
phase: quick-12
plan: 01
subsystem: backend
tags: [opening-lookup, normalization, trie, chess-openings, pgn-parsing]
dependency_graph:
  requires: []
  provides: [unified-opening-classification]
  affects: [normalization, import-pipeline]
tech_stack:
  added: []
  patterns: [trie-based-prefix-matching, module-level-init]
key_files:
  created:
    - app/data/openings.tsv
    - app/services/opening_lookup.py
    - tests/test_opening_lookup.py
  modified:
    - app/services/normalization.py
    - tests/test_normalization.py
decisions:
  - "Use dict-based trie (not prefix tree library) keyed by SAN moves for O(n) lookup where n=moves in game"
  - "Trie built once at module load — not per-game — so import cost is paid once at startup"
  - "Copy openings.tsv to app/data/ (backend-owned copy) instead of depending on frontend/public path"
  - "Last entry in TSV wins for duplicate move sequences — more specific names tend to come later in the file"
metrics:
  duration: 10min
  completed_date: "2026-03-14"
  tasks: 2
  files: 5
---

# Quick Task 12: Fix Opening ECO Categorization Summary

Unified opening classification using trie-based longest-prefix matching against openings.tsv for both chess.com and lichess games, replacing URL-based ECO extraction and lichess API opening field.

## What Was Built

**`app/services/opening_lookup.py`** — New service module:
- `_normalize_pgn_to_san_sequence(pgn)` strips PGN headers, annotations `{...}`, variations `(...)`, result markers, and move numbers to produce a clean list of SAN move tokens
- `_build_trie()` loads `app/data/openings.tsv` (3641 entries) into a nested dict trie at module init
- `find_opening(pgn)` walks the trie move-by-move, returning `(eco, name)` for the longest known prefix match

**`app/data/openings.tsv`** — Backend copy of the curated opening database (previously only in `frontend/public/`)

**`app/services/normalization.py`** — Updated normalization:
- Removed `_extract_chesscom_eco()` and `_extract_chesscom_opening_name()` functions
- `normalize_chesscom_game`: `pgn_str` defined unconditionally before use; `find_opening(pgn_str)` replaces URL-based extraction
- `normalize_lichess_game`: `find_opening(pgn)` replaces `opening.get("eco")` / `opening.get("name")` from lichess API field

**`tests/test_opening_lookup.py`** — 20 new tests covering normalization helpers and find_opening edge cases

**`tests/test_normalization.py`** — Removed 3 obsolete test classes (TestExtractEcoFromPgn, TestNormalizeChesscomGameEcoFallback, TestChesscomEcoExtraction); updated opening assertions in both platform test classes to reflect PGN-based matching

## Decisions Made

1. **Dict trie over external library**: Simple nested dicts are sufficient for 3641 entries, no dependency needed
2. **Module-level trie init**: One-time cost at startup; `find_opening` calls are O(moves) with no I/O
3. **Backend-owned TSV copy**: `app/data/openings.tsv` decouples backend from frontend directory structure
4. **Last-entry-wins for duplicates**: Consistent with the frontend's openings.ts behavior

## Test Results

- 79 tests pass total (59 normalization + 20 opening_lookup)
- No lint errors (`ruff check`)
- Both `normalize_chesscom_game` and `normalize_lichess_game` use `find_opening` for opening classification

## Deviations from Plan

**1. [Rule 1 - Bug] pgn_str defined unconditionally**
- **Found during:** Task 2 implementation
- **Issue:** The original code only defined `pgn_str` inside the `if not is_computer_game:` branch. After removing the `eco_url` extraction, `pgn_str` needed to be defined before the computer detection block to be available for `find_opening(pgn_str)`.
- **Fix:** Moved `pgn_str = game.get("pgn", "") or ""` before the computer detection block so it's always defined.
- **Files modified:** `app/services/normalization.py`
- **Commit:** fceef4f

## Self-Check: PASSED

All created files exist and all commits present.
