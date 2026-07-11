---
phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l
plan: 02
subsystem: ui
tags: [react, typescript, analysis-page, deep-link, chess-js]

# Dependency graph
requires:
  - phase: 165 (plan 01)
    provides: gem-ELO calibration harness producing brilliant-dataset TSVs with arbitrary mid-game FENs
provides:
  - "buildAnalysisFenUrl / parseAnalysisFenParam pure helpers in analysisUrl.ts"
  - "Additive ?fen= deep-link seeding a free-play root on /analysis, alongside existing ?line="
  - "Deterministic precedence: game_id > fen > line"
affects: [analysis-page, gem-move-harness, seed-094]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "URL-param seeding effects share hasLoadedMainLine ref; precedence enforced via explicit `=== null` guards rather than effect ordering"

key-files:
  created: []
  modified:
    - frontend/src/lib/analysisUrl.ts
    - frontend/src/lib/analysisUrl.test.ts
    - frontend/src/pages/Analysis.tsx

key-decisions:
  - "?fen= restored additively (not a revert) alongside ?line=, per SEED-094 / D-06 — brilliant-dataset positions are arbitrary mid-game snapshots with no move-list-to-start"
  - "parseAnalysisFenParam validates via chess.js in try/catch, degrading garbage/null/empty to null so a hand-typed bad URL cannot crash the board (T-165-03)"
  - "Precedence game_id > fen > line enforced by adding `rootFenSeed === null` to the existing ?line= effect guard (T-165-04), since both seeding effects share the hasLoadedMainLine ref"

patterns-established:
  - "Additive URL-param restoration: when re-adding a previously-removed param, extend module doc comments to describe it as complementary rather than a replacement"

requirements-completed: [SEED-094]

coverage:
  - id: D1
    description: "buildAnalysisFenUrl / parseAnalysisFenParam pure helpers with round-trip, encoding-safety, null/empty/garbage unit tests"
    requirement: "SEED-094"
    verification:
      - kind: unit
        ref: "frontend/src/lib/analysisUrl.test.ts#buildAnalysisFenUrl / parseAnalysisFenParam"
        status: pass
    human_judgment: false
  - id: D2
    description: "?fen= seeds a free-play root on /analysis; ?line= still works unchanged; precedence game_id > fen > line; garbage FEN degrades gracefully without crashing"
    requirement: "SEED-094"
    verification:
      - kind: manual_procedural
        ref: "Human browser verification per Task 3 how-to-verify steps (mid-game FEN load + playability, ?line= regression check, garbage-FEN crash check)"
        status: pass
    human_judgment: true
    rationale: "Requires visually confirming board rendering, move numbering, and playability in a real browser — not mechanically derivable from unit tests alone."

# Metrics
duration: ~35min
completed: 2026-07-11
status: complete
---

# Phase 165 Plan 02: Restore ?fen= Analysis Deep-Link Summary

**Additive `?fen=<fen>` deep-link on `/analysis` seeds an arbitrary mid-game FEN as a free-play root, making gem-ELO harness TSV positions clickable, with deterministic game_id > fen > line precedence.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-11T15:05:00Z (approx, prior executor)
- **Completed:** 2026-07-11T15:45:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 3

## Accomplishments
- Added `buildAnalysisFenUrl` and `parseAnalysisFenParam` pure helpers to `analysisUrl.ts`, unit-tested for round-trip, encoding-safety (`%20`/`%2F`), and null/empty/garbage degradation to `null`.
- Wired `?fen=` seeding into `Analysis.tsx`: a new free-play effect calls the existing `loadMainLine([], rootFenSeed)` to root the board at an arbitrary mid-game FEN, reusing `hasLoadedMainLine` and `fenToRootPly` without any new hook method.
- Enforced deterministic precedence `game_id > fen > line` by adding a `rootFenSeed === null` guard to the existing `?line=` seeding effect, closing the effect-ordering landmine (RESEARCH Landmine 8 / T-165-04).
- Human browser verification confirmed: a mid-game FEN loads a playable free-play root, `?line=` continues to work unchanged, and a garbage `?fen=` value falls back gracefully without crashing the page.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): failing tests for buildAnalysisFenUrl/parseAnalysisFenParam** - `4bda5adb` (test)
2. **Task 1 (GREEN): implement buildAnalysisFenUrl / parseAnalysisFenParam** - `03fcb933` (feat)
3. **Task 2: wire ?fen= seeding + precedence into Analysis.tsx** - `a9c275a3` (feat)
4. **Task 3: Human-verify ?fen= deep-link in the browser** - human-verified pass, "approved" (no code changes; checkpoint gate, no separate commit)

**Plan metadata:** this commit (docs: complete plan)

_Note: Task 1 followed TDD RED→GREEN as specified by `tdd="true"`._

## Files Created/Modified
- `frontend/src/lib/analysisUrl.ts` - Added `FEN_PARAM` constant, `buildAnalysisFenUrl`, `parseAnalysisFenParam`; updated module doc comment to describe `?fen=` as additively restored
- `frontend/src/lib/analysisUrl.test.ts` - New `describe` blocks for `buildAnalysisFenUrl` / `parseAnalysisFenParam` covering build format, round-trip, encoding-safety, and null/empty/garbage cases
- `frontend/src/pages/Analysis.tsx` - Imports `parseAnalysisFenParam`, reads `?fen=` into `rootFenSeed`, adds a free-play seeding effect calling `loadMainLine([], rootFenSeed)`, and guards the existing `?line=` effect with `rootFenSeed === null` for deterministic precedence

## Decisions Made
- `?fen=` is documented as additive to `?line=`, not a revert of its prior removal — module doc comments in both `analysisUrl.ts` and `Analysis.tsx` were updated accordingly so future readers don't mistake this for undoing a deliberate removal.
- Precedence conflict (both effects sharing `hasLoadedMainLine`) resolved via an explicit `rootFenSeed === null` guard on the `?line=` effect rather than reordering effects, keeping the winner deterministic regardless of React effect scheduling.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `?fen=` deep-link is live and additive; gem-ELO harness TSV `analysis_url` column values are now clickable into a playable free-play analysis root.
- No blockers. Phase 165 (both plans 01 and 02) is now complete.

---
*Phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: frontend/src/lib/analysisUrl.ts
- FOUND: frontend/src/pages/Analysis.tsx
- FOUND: .planning/phases/165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l/165-02-SUMMARY.md
- FOUND commit: 4bda5adb
- FOUND commit: 03fcb933
- FOUND commit: a9c275a3
