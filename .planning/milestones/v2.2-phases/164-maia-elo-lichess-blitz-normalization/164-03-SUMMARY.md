---
phase: 164-maia-elo-lichess-blitz-normalization
plan: 03
subsystem: frontend
tags: [typescript, react-hook, maia, rating-normalization]

# Dependency graph
requires:
  - "GameFlawCard.white_rating_lichess_blitz / .black_rating_lichess_blitz (164-02 backend fields, mirrored here)"
provides:
  - "useMaiaEloDefault's deriveRawDefault reads the mover-color's Lichess-blitz-normalized rating with a raw-rating fallback"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive optional-field mirroring of a backend DTO extension — GameFlawCard (types/library.ts) and MaiaEloGameData (useMaiaEloDefault.ts) both gain the same two `?: number | null` fields, keeping the frontend/backend field-name contract locked"
    - "`??` read-with-fallback inside deriveRawDefault — normalized field first, raw rating second — with everything downstream (clampToLadderBounds, userOverrodeRef, free-play path) untouched"

key-files:
  created: []
  modified:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useMaiaEloDefault.ts
    - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts

key-decisions:
  - "Both new fields are optional (`?: number | null`) on both TS types, mirroring the plan's Pitfall 5 requirement, so existing fixtures/call sites keep compiling and a missing/older-cached value falls through to the raw rating via `??`"
  - "Doc comment at the top of useMaiaEloDefault.ts updated to state the normalized-rating-first D-07 rule, keeping the hook's own documentation in sync with the behavior change"

patterns-established: []

requirements-completed: []

coverage:
  - id: T1
    description: "Game mode, mover-color's *_lichess_blitz present → deriveRawDefault returns the normalized value, not the raw rating"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts::'game mode: normalized field present for the mover color is used instead of the raw rating'"
        status: pass
    human_judgment: false
  - id: T2
    description: "Game mode, mover-color's *_lichess_blitz null → deriveRawDefault falls back to that color's raw rating"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts::'game mode: normalized field null/absent for the mover color falls back to the raw rating'"
        status: pass
    human_judgment: false
  - id: T3
    description: "Mixed — normalized present for one color, null for the other — correct per-color choice driven by sideToMove"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts::'game mode: mixed — normalized present for one color, null for the other — picks per-color by sideToMove'"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-11
status: complete
---

# Phase 164 Plan 03: Maia ELO Slider Reads Lichess-Blitz-Normalized Rating Summary

**The Maia ELO slider's game-mode default now reads the mover-color's Lichess-blitz-normalized rating (falling back to the raw rating when null/absent), via two mirrored optional TS fields and a one-line `??` change in `deriveRawDefault`.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `GameFlawCard` (`frontend/src/types/library.ts`) gains `white_rating_lichess_blitz?: number | null` and `black_rating_lichess_blitz?: number | null` directly beneath the existing raw rating fields, mirroring the backend fields added in Plan 02, with a Phase 164 provenance comment matching the file's existing convention.
- `MaiaEloGameData` (`frontend/src/hooks/useMaiaEloDefault.ts`) gains the identical two optional fields.
- `deriveRawDefault`'s game-mode branch now returns `gameData.white_rating_lichess_blitz ?? gameData.white_rating` for white and the black analog, resolved off `moverColor = sideToMove ?? gameData.user_color` exactly as before — the `??` supplies the raw-rating fallback whenever the normalized value is `null`/`undefined`. The free-play branch (`profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO`), `clampToLadderBounds`, `userOverrodeRef`, and the re-derivation `useEffect` guard are all byte-for-byte unchanged — `git diff` confirms only the field additions and the two return expressions.
- The hook's top-of-file doc comment updated to describe the normalized-rating-first D-07 rule so the documentation stays in sync with the new behavior.
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts`'s `gameData()` fixture extended with the two optional fields (defaulting to `undefined`), and 3 new test cases added: normalized-used, null-fallback, and mixed-by-color (verified against both `sideToMove: 'white'` and `sideToMove: 'black'` on the same fixture object).
- `cd frontend && npx tsc -b --noEmit` clean. Targeted hook test file: 11/11 passed (8 pre-existing + 3 new). Full frontend gate (`npm run lint && npm test -- --run`): lint 0 errors (3 pre-existing warnings confined to the generated `coverage/` artifact directory, unrelated to this change), full suite 1752/1752 tests passed across 139 files.

## Task Commits

1. **Task 1: Add the two optional TS fields + deriveRawDefault read-with-fallback**
   - `48ba82fd` feat(164-03): read Lichess-blitz-normalized rating in Maia ELO default
2. **Task 2: Hook tests — normalized-used / null-fallback / mixed-by-color**
   - `01ef20fd` test(164-03): cover normalized-used / null-fallback / mixed-by-color cases

## Files Created/Modified

- `frontend/src/types/library.ts` — Added `white_rating_lichess_blitz?: number | null` / `black_rating_lichess_blitz?: number | null` to `GameFlawCard`, immediately after the existing raw rating fields, with a Phase 164 comment.
- `frontend/src/hooks/useMaiaEloDefault.ts` — Added the identical two optional fields to `MaiaEloGameData`; `deriveRawDefault`'s game-mode branch now reads the normalized field per mover-color with a raw-rating `??` fallback; updated the top-of-file doc comment to describe the new D-07 rule.
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` — Extended the `gameData()` fixture with the two optional fields (default `undefined`); added 3 new test cases covering present-used, null-fallback, and mixed-by-color behavior.

## Decisions Made

- Both new fields kept optional (`?: number | null`) on both TS types (Pitfall 5) — this is what lets every pre-existing `gameData()` call site and any other `GameFlawCard`-shaped test fixture keep compiling untouched, and it's what makes the `??` fallback in `deriveRawDefault` meaningful (a missing/older-cached-bundle value degrades to the raw rating rather than `undefined` propagating through `clampToLadderBounds`).
- Updated the hook's doc comment as part of Task 1 (not deferred) since the D-07 rule it describes materially changed — leaving stale documentation in a hook this heavily cross-referenced (five distinct historical decision entries in STATE.md alone) was judged a correctness risk for future readers, not scope creep.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This is a client-only read of a field already returned by the existing `GET /api/library/games/{game_id}` response (live since Plan 02); no new network call, no new deploy step beyond the next normal frontend build/deploy.

## Next Phase Readiness

- Phase 164 (all 3 plans) is now functionally complete: the backend computes and serves `white_rating_lichess_blitz`/`black_rating_lichess_blitz` on `GameFlawCard` (Plans 01–02), and the frontend's Maia ELO slider default now consumes them with a safe raw-rating fallback (Plan 03).
- No blockers or concerns. No further plans are queued under this phase per the 164-PATTERNS.md / 164-RESEARCH.md scope (7/7 files, no analog gaps).
- Manual/live verification (opening `/analysis` in game mode for a chess.com bullet/rapid/classical game and confirming the ELO selector seats at the normalized value instead of the raw rating) is optional polish — not required by this plan's automated verification, which is complete and green.

---
*Phase: 164-maia-elo-lichess-blitz-normalization*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: `.planning/phases/164-maia-elo-lichess-blitz-normalization/164-03-SUMMARY.md`
- FOUND: `frontend/src/types/library.ts`
- FOUND: `frontend/src/hooks/useMaiaEloDefault.ts`
- FOUND: `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts`
- FOUND: commits `48ba82fd`, `01ef20fd`
