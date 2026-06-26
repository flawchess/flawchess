---
phase: 127-detector-hardening-validation
plan: "02"
subsystem: validation-harness
tags: [tactic-detector, validation, pytest, ci, fixtures, lichess, cc0]
dependency_graph:
  requires: []
  provides:
    - tests/scripts/tagger/ (excluded harness package)
    - tests/scripts/tagger/motif_theme_map.py (MOTIF_TO_THEMES, UNVALIDATED_MOTIFS)
    - tests/scripts/tagger/conftest.py (offline fixture loader)
    - fixtures/tagger/detector_fixture.csv (4368-row stratified CC0 puzzle fixture)
    - scripts/select_tagger_fixtures.py (re-runnable selector)
  affects:
    - pyproject.toml (addopts: tagger ignore added)
    - .github/workflows/ci.yml (tagger precision gate step added)
tech_stack:
  added: []
  patterns:
    - stratified CC0 puzzle fixture (D-07)
    - excluded test directory (D-14) parallel to tests/scripts/benchmarks/
    - offline harness conftest (no DB, no asyncio)
    - zstd streaming CSV selector (mirrors select_benchmark_users.py pattern)
key_files:
  created:
    - tests/scripts/tagger/__init__.py
    - tests/scripts/tagger/conftest.py
    - tests/scripts/tagger/motif_theme_map.py
    - fixtures/tagger/detector_fixture.csv
    - scripts/select_tagger_fixtures.py
  modified:
    - pyproject.toml (addopts extended)
    - .github/workflows/ci.yml (tagger precision gate step)
decisions:
  - D-10: MOTIF_TO_THEMES is multi-label (22 motifs mapped to 1+ lichess themes each)
  - D-11: CC0/AGPL boundary recorded in selector docstring and conftest docstring; cook.py neither vendored nor ported
  - D-14: tagger dir + pyproject ignore land together in Task 1; CI uses explicit path in Task 2
  - OQ-1 resolved: hangingPiece confirmed (219,869 occurrences in 6M puzzle scan)
  - OQ-2 confirmed: double-bishop-mate not in top-50 themes; UNVALIDATED_MOTIFS correctly includes it
  - OQ-4 resolved: N=50 per stratum, MIN_STRATUM_SIZE=10, RATING_BAND_THRESHOLDS=(1200,1600,2000)
metrics:
  duration: "~10 minutes"
  completed: "2026-06-19T14:03:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 2
status: complete
---

# Phase 127 Plan 02: Validation Harness Infrastructure Summary

One-liner: Offline tagger validation harness scaffold with 4368-row stratified CC0 fixture, 22-motif theme map, and dedicated CI precision gate step.

## What Was Built

### Task 1: motif->theme map + excluded tagger package + pyproject ignore

- `tests/scripts/tagger/__init__.py`: empty package marker
- `tests/scripts/tagger/conftest.py`: session-scoped `detector_fixture` fixture that loads `fixtures/tagger/detector_fixture.csv` offline (no DB, no asyncio) and returns typed `PuzzleRow` dicts
- `tests/scripts/tagger/motif_theme_map.py`: `MOTIF_TO_THEMES` (22 motifs, multi-label per D-10) and `UNVALIDATED_MOTIFS` (`self-interference`, `double-bishop-mate`) with module docstring recording OQ-1/OQ-2 caveats
- `pyproject.toml`: `addopts` extended with `--ignore=tests/scripts/tagger` alongside the existing benchmark ignore; comment updated to mention tagger; directory + ignore land together (D-14)

### Task 2: stratified puzzle selector + committed fixture + CI step

- `scripts/select_tagger_fixtures.py`: streams the full lichess CC0 puzzle `.csv.zst` via `zstandard`, applies `Moves[0]` to the published FEN to produce board-after-flaw (critical RESEARCH Pitfall 1 convention), filters by MOTIF_TO_THEMES, stratified-samples N=50 per (motif, rating_band) with MIN_STRATUM_SIZE=10 collapse; prints top-50 themes for map validation; CC0/AGPL boundary recorded in docstring (SC#4, D-11)
- `fixtures/tagger/detector_fixture.csv`: 4368 rows, columns `PuzzleId,FEN,FirstMove,PV,Themes,Rating`; FEN is board-after-flaw; generated from 6,014,381 puzzle scan
- `.github/workflows/ci.yml`: "Tagger precision gate" step added immediately after "Run pytest"; runs `uv run pytest tests/scripts/tagger -v` with no DB env (offline harness)

## Open Questions Resolved at Selector Run

| Question | Resolution |
|----------|------------|
| OQ-1: hangingPiece spelling | Confirmed: `hangingPiece` (219,869 occurrences) |
| OQ-2: double-bishop-mate theme | Not found in top-50; UNVALIDATED_MOTIFS correctly includes it |
| OQ-4: fixture size N | N=50 per stratum chosen; boden-mate/gt2000 had 37 puzzles, smothered-mate/gt2000 had 34 - both accepted as is (above MIN_STRATUM_SIZE=10) |

## Verification Results

| Check | Result |
|-------|--------|
| `MOTIF_TO_THEMES['fork'] == ('fork',)` | PASS |
| `'self-interference' in UNVALIDATED_MOTIFS` | PASS |
| `len(MOTIF_TO_THEMES) == 22` | PASS |
| `--ignore=tests/scripts/tagger` in pyproject.toml addopts | PASS |
| `uv run pytest tests/scripts/tagger --collect-only` | PASS (no tests yet — Plan 03) |
| fixture header correct | PASS |
| fixture row count >= 100 (actual: 4368) | PASS |
| fixture FEN parses as chess.Board | PASS |
| CI yaml contains pytest tests/scripts/tagger | PASS |
| `uv run pytest -n auto -x` (default suite) excludes tagger | PASS (2797 tests, none from tagger) |

## Deviations from Plan

None - plan executed exactly as written.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes.

The committed fixture CSV is CC0 public-domain puzzle data (database.lichess.org). No PII or secrets.

## Self-Check: PASSED

Files exist:
- tests/scripts/tagger/__init__.py: FOUND
- tests/scripts/tagger/conftest.py: FOUND
- tests/scripts/tagger/motif_theme_map.py: FOUND
- fixtures/tagger/detector_fixture.csv: FOUND
- scripts/select_tagger_fixtures.py: FOUND

Commits:
- 4653b69b: contains Task 1 files (tagger package + motif_theme_map + pyproject ignore; incorporated by pre-push hook into doc commit)
- 90ccc7a9: feat(127-02): stratified puzzle selector + committed fixture + CI step
