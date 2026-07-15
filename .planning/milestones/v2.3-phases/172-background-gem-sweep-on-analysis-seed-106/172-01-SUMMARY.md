---
phase: 172-background-gem-sweep-on-analysis-seed-106
plan: 01
subsystem: api
tags: [opening-lookup, pydantic, fastapi, typescript, gem-sweep]

# Dependency graph
requires: []
provides:
  - "find_opening_ply_count(moves) — 1-based ply depth of the deepest opening-book match on the existing SAN trie"
  - "GameFlawCard.opening_ply_count — additive, computed-on-read field on the game-detail payload (0 = no match)"
  - "frontend/src/types/library.ts GameFlawCard.opening_ply_count TS mirror + EvalPoint.best_move UCI doc-comment"
affects: [172-03, 172-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parallel trie-walk function alongside an existing one (find_opening_ply_count next to find_opening) instead of modifying the original's signature/behavior"
    - "Derived value computed unconditionally in the single card-construction point (_build_card) rather than forking list-mode vs single-game contracts"

key-files:
  created: []
  modified:
    - app/services/opening_lookup.py
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/test_opening_lookup.py
    - tests/services/test_library_service.py
    - frontend/src/types/library.ts

key-decisions:
  - "Computed opening_ply_count unconditionally in _build_card (list mode included), per RESEARCH's Open Question 1 resolution documented in the plan — negligible cost against an already-loaded module-level trie."
  - "find_opening_ply_count does not call _normalize_pgn_to_san_sequence — it takes already-tokenized SAN (GameFlawCard.moves), leaving find_opening's PGN-taking signature and callers (normalization.py, position_bookmarks.py) untouched."
  - "Tested the walk-without-match edge case (behavior spec item 5) via a synthetic monkeypatched trie, since every root child in the real openings.tsv trie carries a result — that behavior is unreachable with real data at depth 1."

patterns-established:
  - "Add a new parallel function next to an existing trie-walker when the new function needs a different return contract (depth vs. discarded-depth result tuple), rather than overloading the original."

requirements-completed: []

coverage:
  - id: D1
    description: "find_opening_ply_count(moves) returns the 1-based ply depth of the deepest opening-book match, 0 when nothing matched, without touching find_opening's PGN-taking signature or callers"
    verification:
      - kind: unit
        ref: "tests/test_opening_lookup.py::TestFindOpeningPlyCount"
        status: pass
    human_judgment: false
  - id: D2
    description: "GameFlawCard.opening_ply_count is additive (default 0), computed in _build_card for both get_library_game and get_library_games, with zero migration"
    verification:
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_known_opening_game_has_nonzero_opening_ply_count"
        status: pass
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_unmatched_opening_game_has_zero_opening_ply_count"
        status: pass
      - kind: other
        ref: "git status --porcelain alembic/versions/ (empty)"
        status: pass
    human_judgment: false
  - id: D3
    description: "TypeScript GameFlawCard mirror carries opening_ply_count: number, and EvalPoint.best_move is documented as UCI (vs. SAN moves[i]) with a pointer to sanToUci()"
    verification:
      - kind: other
        ref: "npx tsc -b --noEmit (zero errors)"
        status: pass
      - kind: other
        ref: "grep -B 2 -A 2 'best_move' frontend/src/types/library.ts | grep -c sanToUci (>= 1)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 172 Plan 01: Opening Book Ply Count Summary

**Additive, computed-on-read `opening_ply_count` on `GameFlawCard`: a new `find_opening_ply_count` on the existing SAN trie, surfaced on the backend payload and mirrored into TypeScript — zero migration, zero backfill.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-14T22:34:01+02:00 (first commit)
- **Completed:** 2026-07-14T22:37:24+02:00 (last commit)
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- `find_opening_ply_count(moves: list[str]) -> int` on `app/services/opening_lookup.py` — walks the same module-level `_TRIE` singleton as `find_opening` but returns the 1-based depth of the deepest result-carrying node instead of discarding it.
- `GameFlawCard.opening_ply_count: int = 0` on `app/schemas/library.py`, computed unconditionally in `_build_card` (both list mode and single-game mode) from the already-tokenized `moves_data` — no re-parse of the stored PGN.
- `frontend/src/types/library.ts` mirrors the field as a non-optional `number`, and `EvalPoint.best_move`'s doc-comment now states explicitly that it's UCI (not SAN like `moves[i]`), pointing at `sanToUci()` as the required conversion — the durable guard against the SAN/UCI trap that would silently no-op the Plan 05 free prefilter.

## Task Commits

Each task was committed atomically:

1. **Task 1: `find_opening_ply_count` on the SAN trie** - `392ce46f` (feat)
2. **Task 2: Surface `opening_ply_count` on `GameFlawCard`** - `38ceed31` (feat)
3. **Task 3: Mirror the field into TypeScript types + document the UCI/SAN trap** - `2ee8614b` (feat)

_No TDD test→feat split commits — each task's tests were authored alongside the implementation in one commit per the plan's task boundaries._

## Files Created/Modified
- `app/services/opening_lookup.py` - new `find_opening_ply_count`, parallel to `find_opening`
- `app/schemas/library.py` - `GameFlawCard.opening_ply_count: int = 0`
- `app/services/library_service.py` - imports `find_opening_ply_count`, computes it in `_build_card`, passes it to the constructor
- `tests/test_opening_lookup.py` - new `TestFindOpeningPlyCount` class (6 test methods)
- `tests/services/test_library_service.py` - two new `TestGetLibraryGame` cases (known-opening non-zero, unmatched zero)
- `frontend/src/types/library.ts` - `GameFlawCard.opening_ply_count: number`, strengthened `EvalPoint.best_move` doc-comment

## Decisions Made
- Computed `opening_ply_count` unconditionally in `_build_card` (list-mode cards too), per the plan's explicit resolution of RESEARCH Open Question 1: the cost is tens of microseconds against an already-loaded trie, and gating it to the single-game path would fork `_build_card`'s contract for no measurable gain. Recorded in a code comment at the call site.
- `find_opening_ply_count` intentionally does not call `_normalize_pgn_to_san_sequence` — the caller (`_build_card`) already has tokenized SAN via `moves_data`, and `find_opening`'s PGN-taking signature/callers stay untouched.
- The "walks trie but never matches" behavior (spec item 5) is unreachable with the real `openings.tsv` trie at depth 1 (every legal first move maps to a named opening, e.g. King's Pawn Game for a lone `e4`). Tested it against a synthetic 2-node trie via `monkeypatch.setattr(opening_lookup, "_TRIE", ...)` instead of contorting a real-data fixture to fake the same property.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all three tasks passed verification on the first implementation attempt. One flaky, unrelated frontend test (`src/lib/__tests__/openings.test.ts`'s whole-corpus SAN-parity test) timed out at the default 5000ms under `npm test -- --run`'s parallel load; re-ran in isolation and it passed in ~2s. Confirmed unrelated to this plan (no `openings.tsv` corpus or `sanToSquares.ts` changes were made) and not touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 03 (background sweep) and Plan 05 (frontend prefilter) can now consume `opening_ply_count` from the game-detail payload to gate book plies out of the gem cascade (D-04) and mark theory plies (D-08).
- `EvalPoint.best_move`'s UCI doc-comment is in place ahead of Plan 05's free prefilter, which depends on correctly converting `moves[i]` (SAN) via `sanToUci()` before comparing against it.
- No blockers.

---
*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 7 created/modified files found on disk; all 3 task commit hashes (392ce46f, 38ceed31, 2ee8614b) found in git history.
