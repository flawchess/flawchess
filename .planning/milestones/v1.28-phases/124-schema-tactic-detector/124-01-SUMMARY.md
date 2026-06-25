---
phase: 124-schema-tactic-detector
plan: "01"
subsystem: tactic-detector
tags: [schema, migration, encoding, orm, repository]
status: complete
completed: "2026-06-17T22:15:00Z"
requires: []
provides:
  - game_flaws.tactic_motif (SmallInteger, nullable)
  - game_flaws.tactic_piece (SmallInteger, nullable)
  - game_flaws.tactic_confidence (SmallInteger, nullable)
  - TacticMotifInt IntEnum (24 members)
  - TacticMotif Literal type (24 strings)
  - FlawRecord.tactic_motif_int / tactic_piece / tactic_confidence fields
  - flaw_record_to_row tactic column emission
affects:
  - app/services/flaws_service.py (FlawRecord TypedDict + _build_flaw_record)
  - app/repositories/game_flaws_repository.py (flaw_record_to_row)
  - tests/services/test_flaws_service.py
  - tests/test_flaws_materialization.py
  - tests/test_flaws_repository.py
tech-stack:
  added: []
  patterns:
    - EndgameClassInt pattern applied: TacticMotifInt IntEnum + _INT_TO_MOTIF/_MOTIF_TO_INT dicts
    - nullable SmallInteger ORM column pattern (tempo precedent)
    - flaw_record_to_row .get() passthrough for optional fields
key-files:
  created:
    - alembic/versions/20260617_120000_phase_124_tactic_motifs.py
    - app/services/tactic_detector.py
  modified:
    - app/models/game_flaw.py
    - app/services/flaws_service.py
    - app/repositories/game_flaws_repository.py
    - tests/services/test_flaws_service.py
    - tests/test_flaws_materialization.py
    - tests/test_flaws_repository.py
decisions:
  - "D-01: Three nullable SmallInteger columns added (tactic_motif/piece/confidence) — all NULL on existing rows"
  - "D-02: TacticMotifInt IntEnum encoding follows EndgameClassInt precedent (no bitmask, no join table)"
  - "D-03: Named-mate subtypes stored fine-grained (9 mates) — MATE_MOTIFS frozenset enables free coarsening at query time"
  - "D-11: tactic_confidence always stored with motif, NULL only when no detector fired"
  - "D-12: tactic_piece semantics commented in ORM model"
metrics:
  duration: "~12 minutes"
  tasks_completed: 3
  files_changed: 7
---

# Phase 124 Plan 01: Schema + Tactic Detector Foundation Summary

Laid the schema and encoding foundation for tactic-motif detection. Three nullable SmallInteger columns (`tactic_motif`, `tactic_piece`, `tactic_confidence`) added to `game_flaws` via an Alembic migration, with `TacticMotifInt` IntEnum (24 members) and bidirectional dicts in a new `tactic_detector.py` encoding shell, and all three fields plumbed through `FlawRecord` and `flaw_record_to_row`.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Alembic migration + ORM columns | 5b156e60 | alembic/versions/20260617_120000_phase_124_tactic_motifs.py, app/models/game_flaw.py |
| 2 | tactic_detector.py encoding shell | 1e850046 | app/services/tactic_detector.py |
| 3 | FlawRecord + flaw_record_to_row | 4374bdcf | app/services/flaws_service.py, app/repositories/game_flaws_repository.py |

## Verification Results

- `uv run alembic upgrade head`: clean, migrated `20260617_130000 -> 20260617_120000_phase_124`
- `uv run alembic downgrade -1 && uv run alembic upgrade head`: round-trip clean
- Dev DB columns confirmed: `tactic_motif`, `tactic_piece`, `tactic_confidence` all `smallint`, nullable=YES
- `SELECT count(*) FROM game_flaws WHERE tactic_motif IS NOT NULL` = 0 (existing rows NULL)
- No `from app` imports in migration file
- `uv run ty check app/ tests/`: zero errors
- `uv run ruff check app/ tests/`: clean
- `uv run pytest -n auto tests/services/test_flaws_service.py`: 118 passed
- Encoding roundtrip: 24 members, 24 dict entries, `_MOTIF_TO_INT[_INT_TO_MOTIF[i]] == i` for all i, MATE_MOTIFS has 9 entries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ty check errors in test files constructing FlawRecord directly**
- **Found during:** Post-task-3 full `uv run ty check app/ tests/` run
- **Issue:** `FlawRecord` is a `TypedDict` without `total=False`, so adding the three new fields as required keys caused `missing-typed-dict-key` errors in 4 test sites across `test_flaws_service.py`, `test_flaws_materialization.py`, and `test_flaws_repository.py`.
- **Fix:** Added `tactic_motif_int=None`, `tactic_piece=None`, `tactic_confidence=None` to each of the 4 existing `FlawRecord` literal constructions in test files.
- **Files modified:** tests/services/test_flaws_service.py, tests/test_flaws_materialization.py, tests/test_flaws_repository.py
- **Commit:** e1d09540

## Known Stubs

- `detect_tactic_motif` function is not yet implemented (section-comment stub in `tactic_detector.py`). This is intentional — plan 02 owns detector implementation. The stub does not affect plan 01's goals.

## Threat Flags

None — no new external input, network, auth, or user-facing surface in this plan.

## Self-Check: PASSED

- [x] alembic/versions/20260617_120000_phase_124_tactic_motifs.py — created
- [x] app/services/tactic_detector.py — created
- [x] app/models/game_flaw.py — modified (3 new columns)
- [x] app/services/flaws_service.py — modified (FlawRecord + _build_flaw_record)
- [x] app/repositories/game_flaws_repository.py — modified (flaw_record_to_row)
- [x] Commits: 5b156e60, 1e850046, 4374bdcf, e1d09540 — all present in git log
- [x] ty check: zero errors across app/ and tests/
- [x] pytest: 148 tests across all affected test files passed
