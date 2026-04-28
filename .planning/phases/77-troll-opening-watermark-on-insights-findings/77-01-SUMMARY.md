---
phase: 77-troll-opening-watermark-on-insights-findings
plan: 01
subsystem: ui
tags: [frontend, react, vitest, fen, theme, asset-pipeline]

# Dependency graph
requires: []
provides:
  - frontend/src/assets/troll-face.svg at canonical kebab-case path (D-11)
  - TROLL_WATERMARK_OPACITY = 0.30 exported from theme.ts (D-02 lock)
  - deriveUserSideKey(fen, side) pure helper exported from frontend/src/lib/trollOpenings.ts (D-08)
  - isTrollPosition(fen, side) pure helper exported from frontend/src/lib/trollOpenings.ts (D-08)
  - frontend/src/data/trollOpenings.ts STUB (Plan 02 ships the curated data)
affects: [77-02-curate-troll-openings, 77-03-opening-finding-card-watermark, 77-04-move-explorer-row-tint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure helper module with vi.mock'd data dependency for test isolation"
    - "FEN piece-placement canonicalization (strip opponent pieces, recompute empty-square runs)"
    - "Theme constants for new visual treatments live in frontend/src/lib/theme.ts adjacent to peer constants"

key-files:
  created:
    - frontend/src/assets/troll-face.svg
    - frontend/src/lib/trollOpenings.ts
    - frontend/src/lib/trollOpenings.test.ts
    - frontend/src/data/trollOpenings.ts (stub, replaced by Plan 02)
  modified:
    - frontend/src/lib/theme.ts

key-decisions:
  - "Ship a stub frontend/src/data/trollOpenings.ts so the alias import resolves at vitest module-load time — vitest 4 resolves source-file imports before applying vi.mock factories, so the path must point to a real file. Plan 02 replaces the stub with the curated set."
  - "Bongcloud test FEN corrected to include the white e4 pawn on rank 4 (4P3) so deriveUserSideKey produces the key the mock places in WHITE_TROLL_KEYS."

patterns-established:
  - "deriveUserSideKey: split FEN at first space, validate exactly 8 ranks, strip opponent letter-class with regex, recanonicalize empty-square runs in a single linear pass per rank."

requirements-completed: []  # Plan frontmatter `requirements: []`; D-08/D-11 are decisions, not REQ-IDs.

# Metrics
duration: ~25min
completed: 2026-04-28
---

# Phase 77 Plan 01: Troll Opening Watermark Foundation Summary

**Pure-function FEN matcher (deriveUserSideKey + isTrollPosition) plus the locked 30% theme opacity and the kebab-case troll-face SVG asset, with 10 green golden-input vitest cases.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-28T~21:50Z
- **Completed:** 2026-04-28T22:14Z
- **Tasks:** 2
- **Files modified:** 5 (1 modified, 4 created)

## Accomplishments

- frontend/src/assets/troll-face.svg landed at canonical kebab-case path (D-11); temp/Troll-Face.svg removed from worktree.
- TROLL_WATERMARK_OPACITY = 0.30 exported from theme.ts adjacent to UNRELIABLE_OPACITY with Pitfall 4 multiplication note (D-02).
- deriveUserSideKey + isTrollPosition shipped as pure helpers, fully typed, behind explicit return types per CLAUDE.md (D-08).
- All 10 golden-input unit tests pass (`npm test -- --run src/lib/trollOpenings.test.ts`).
- tsc --noEmit and eslint clean.

## Task Commits

Each task was committed atomically; Task 2 followed the TDD cycle (RED → GREEN):

1. **Task 1: Move SVG asset and add theme constant** — `9e2f344` (feat)
2. **Task 2 RED: Failing tests for deriveUserSideKey and isTrollPosition** — `65bd86e` (test)
3. **Task 2 GREEN: Implement deriveUserSideKey and isTrollPosition** — `f8ed931` (feat)

## Files Created/Modified

- `frontend/src/assets/troll-face.svg` — decorative SVG, imported via Vite default URL pipeline.
- `frontend/src/lib/theme.ts` — added TROLL_WATERMARK_OPACITY = 0.30 with comment documenting CSS opacity multiplication on dimmed cards (Pitfall 4).
- `frontend/src/lib/trollOpenings.ts` — pure-function module with deriveUserSideKey + isTrollPosition.
- `frontend/src/lib/trollOpenings.test.ts` — vitest suite with vi.mock('@/data/trollOpenings', ...) and 10 cases.
- `frontend/src/data/trollOpenings.ts` — stub Sets so vitest can resolve the alias import at module-load time. Plan 02 replaces with the curated set.

## Decisions Made

- **Stub data file (Rule 3 fix):** vitest 4 resolves source-file imports before applying vi.mock factories. Without a real `frontend/src/data/trollOpenings.ts` the resolver throws "Cannot find package '@/data/trollOpenings'" before the mock has a chance to apply. Shipped a stub that exports empty `WHITE_TROLL_KEYS` / `BLACK_TROLL_KEYS` Sets so the alias resolves; Plan 02 overwrites the file with the curated set. Test isolation is preserved via the vi.mock factory (the stub's empty Sets are never read by the tests). Both Plan 01 and Plan 02 list this file in their working set, so Plan 02's executor will see it as already-existing and replace its content.
- **Bongcloud test FEN correction (Rule 1 fix):** the plan's specified Bongcloud FEN `rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPKPPP/RNBQ1BNR` is missing the white e4 pawn on rank 4. After 1.e4 e5 2.Ke2 the white pawn lives on e4, so rank 4 must be `4P3` not `8`. With rank 4 = `8` the derived white key is `8/8/8/8/8/8/PPPPKPPP/RNBQ1BNR` (no e4 pawn), which does NOT match the mocked `WHITE_TROLL_KEYS = ['8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR']`. Fixed to `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR` so the input FEN derives to exactly the key the plan author intended.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shipped stub data file so vitest can resolve the @/data/trollOpenings import**
- **Found during:** Task 2 GREEN (running vitest after creating trollOpenings.ts)
- **Issue:** Plan asserted that `vi.mock('@/data/trollOpenings', factory)` alone would let the test run without a real data file. In practice, vitest 4 throws `Cannot find package '@/data/trollOpenings'` because source-file import resolution happens before mock factories are applied to a registered module ID — the path must resolve to a file on disk for the alias to bind, and only then does vitest hand the resolved-id mock to the importer.
- **Fix:** Created `frontend/src/data/trollOpenings.ts` as a stub exporting empty `WHITE_TROLL_KEYS` and `BLACK_TROLL_KEYS` Sets with a comment explaining that Plan 02 replaces it. Test isolation is preserved because the test's `vi.mock` factory still overrides the stub at runtime.
- **Files modified:** frontend/src/data/trollOpenings.ts (new)
- **Verification:** `npm test -- --run src/lib/trollOpenings.test.ts` reports 10 passed.
- **Committed in:** f8ed931 (Task 2 GREEN commit)

**2. [Rule 1 - Bug] Corrected Bongcloud test FEN to include the white e4 pawn**
- **Found during:** Task 2 GREEN (Bongcloud test failed: expected true, received false)
- **Issue:** Plan's specified Bongcloud FEN had `8` on rank 4 instead of `4P3`. After 1.e4 e5 2.Ke2 the white pawn is on e4 (rank 4). Without that pawn the derived white key is `8/8/8/8/8/8/PPPPKPPP/RNBQ1BNR`, which does not match the mocked `WHITE_TROLL_KEYS` entry `8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR` that the plan also specified. The mocked key is the correct Bongcloud-position key, so the FEN was the broken half of the fixture.
- **Fix:** Changed test fixture FEN from `rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPKPPP/RNBQ1BNR` to `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR` (and the same for the wrong-side-routing test below it).
- **Files modified:** frontend/src/lib/trollOpenings.test.ts
- **Verification:** test now passes; comment in the test cites the Rule 1 fix.
- **Committed in:** f8ed931 (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking module-resolution, 1 fixture bug)
**Impact on plan:** Neither deviation alters scope or contract. The stub data file is replaced by Plan 02's content (same exports). The Bongcloud FEN fix preserves the plan's intended fixture key (`8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR`) — the planner just wrote a non-self-consistent FEN/key pair.

## Issues Encountered

- The plan's `git mv temp/Troll-Face.svg ...` step does not work because `/temp` is in `.gitignore` (so the source file is untracked and `git mv` rejects it). Used a plain filesystem move instead and `git add` on the destination. Result is identical from git's perspective: a single new file at the destination.
- Knip flags `frontend/src/data/trollOpenings.ts` as "unused" because nothing in the active source graph imports `frontend/src/lib/trollOpenings.ts` yet — Plan 03 (OpeningFindingCard) and Plan 04 (Move Explorer) will close this. This is expected during this wave; not a defect.

## Bongcloud Fixture Cross-Check For Plan 02

Per the plan's `<output>` section, this is the exact key the Bongcloud fixture derives to (for Plan 02 reviewer cross-check):

- Input FEN (corrected): `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR`
- Side: `'white'`
- Derived key: `8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR`

Plan 02's curation script must produce exactly this key for the Bongcloud `e4-e5-Ke2` line in WHITE_TROLL_KEYS for any future end-to-end test that joins both plans.

## tsc / lint Status

- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` exits 0 (the stub data file resolves the alias).
- `cd frontend && npm run lint` exits 0.
- `cd frontend && npm run knip` reports `frontend/src/data/trollOpenings.ts` as unused — expected this wave; resolved when Plan 03 imports `isTrollPosition`.

Per the plan's acceptance-criteria caveat: tsc was green this run, not red, because the stub data file was shipped as part of the Rule 3 fix.

## User Setup Required

None — no external service configuration.

## Next Plan Readiness

- Plan 02 (curate troll openings) can replace `frontend/src/data/trollOpenings.ts` with the curated WHITE/BLACK key sets — same export shape, no consumer changes needed.
- Plan 03 (OpeningFindingCard watermark) can import `isTrollPosition` and `TROLL_WATERMARK_OPACITY` directly.
- Plan 04 (Move Explorer row tint) can import `isTrollPosition` directly.

## Self-Check: PASSED

- frontend/src/assets/troll-face.svg — FOUND
- frontend/src/lib/theme.ts (TROLL_WATERMARK_OPACITY) — FOUND
- frontend/src/lib/trollOpenings.ts — FOUND
- frontend/src/lib/trollOpenings.test.ts — FOUND
- frontend/src/data/trollOpenings.ts — FOUND (stub)
- Commit 9e2f344 — FOUND
- Commit 65bd86e — FOUND
- Commit f8ed931 — FOUND

---
*Phase: 77-troll-opening-watermark-on-insights-findings*
*Completed: 2026-04-28*
