---
phase: 182-style-levers
plan: "03"
subsystem: frontend-engine
tags: [flawchess-engine, opening-book, style-levers, eco-corpus]

# Dependency graph
requires: []
provides:
  - "styleLinesFor(style, side) -> per-style x color ReadonlySet<string> of curated ECO SAN-prefixes"
  - "Style type ('Attacker' | 'Trickster' | 'Grinder' | 'Wall')"
  - "8 curated ReadonlySet<string> constants (ATTACKER/TRICKSTER/GRINDER/WALL x WHITE/BLACK_LINES)"
affects: ["182-04-botStyle-transforms", "182-05-botStyleBundles", "182-07-wire-style-levers-into-useBotGame"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure exported data module (no chess.js, no I/O) mirroring trollOpenings.ts's curated-Set-literal + provenance-comment convention"
    - "Record<Style, {white, black}> lookup table guarantees TypeScript-exhaustive coverage of all 4 styles; defensive EMPTY_LINES fallback guarantees the accessor never returns undefined at runtime"

key-files:
  created:
    - frontend/src/lib/engine/styleOpeningLines.ts
    - frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts
  modified: []

key-decisions:
  - "styleLinesFor(style, side) was implemented in the Task 1 commit alongside the curated data rather than deferred to Task 2 — the lookup table and accessor are trivially small (~10 lines) and tightly coupled to the 8 Set constants they resolve; Task 2 added the accompanying test coverage rather than new production code. No plan-scope conflict: Task 2's stated files_modified already listed styleOpeningLines.ts."
  - "Curated 4 styles x 2 colors = 8 sets, 3-7 lines each, drawn from real named ECO lines (Attacker: King's/Danish/Evans/Smith-Morra Gambits white-side, Latvian/Englund/Budapest/Albin gambits black-side; Trickster: the exact troll openings named in trollOpenings.ts's comments -- Bongcloud/Hammerschlag/Halloween/Sodium/Napoleon/Grob/Barnes white-side, Borg/Drunken-Knight/Fried-Fox black-side; Grinder: Ruy-Lopez/Slav/QGD/French Exchange Variations white-side, Petrov/Berlin/Slav black-side; Wall: London/Colle white-side, Caro-Kann/Stonewall black-side)."
  - "All 8 curated sets kept non-empty by design (D-05 covers both colors per style for all 4 identities) -- the STYLE-01 'empty set, never undefined' edge is instead proven via a defensive-fallback unit test that casts an unrecognized style string into styleLinesFor, exercising the actual EMPTY_LINES fallback code path rather than relying on an incidentally-barren real pairing."

patterns-established:
  - "Curated SAN-prefix data module pattern for future opening-book-adjacent style data: pure Set<string> constants keyed by style x color, validated against the real prefixSet in a dedicated corpus-membership test"

requirements-completed: []  # STYLE-01 is shared across Plans 03/04/05/07 (frontmatter); this plan delivers only the curated-data + accessor half

coverage:
  - id: D1
    description: "Every curated prefix string (all 4 styles x 2 colors, 30 total lines) is a genuine member of the real openings.tsv prefix set — an unbookable curated string is a curation bug (D-05)"
    requirement: "STYLE-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts#curated prefixes are genuine ECO-corpus members (D-05)"
        status: pass
    human_judgment: false
  - id: D2
    description: "styleLinesFor(style, side) resolves the color-correct set for all 8 real style/side pairings and never returns undefined, including for an unrecognized style value via defensive fallback (STYLE-01 empty edge)"
    requirement: "STYLE-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts#styleLinesFor"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-21
status: complete
---

# Phase 182 Plan 03: Per-Style Opening Line Curation Summary

**Curated 8 ReadonlySet<string> SAN-prefix opening-line sets (4 styles x 2 colors) from the real `openings.tsv` ECO corpus, plus a `styleLinesFor(style, side)` accessor — the "menu" Plan 04's `styleBookWeighting` will boost within the existing `BookWeightingFn` seam.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- `frontend/src/lib/engine/styleOpeningLines.ts`: 8 curated `ReadonlySet<string>` constants (`ATTACKER_WHITE_LINES`/`ATTACKER_BLACK_LINES`, `TRICKSTER_WHITE_LINES`/`TRICKSTER_BLACK_LINES`, `GRINDER_WHITE_LINES`/`GRINDER_BLACK_LINES`, `WALL_WHITE_LINES`/`WALL_BLACK_LINES`), a `Style` type union, and `styleLinesFor(style, side): ReadonlySet<string>` which resolves the color-correct set via a `Record<Style, {white, black}>` lookup, defensively falling back to a shared `EMPTY_LINES` sentinel (never `undefined`).
- Every curated string is space-joined SAN with no move numbers, in the exact key shape `openings.ts`'s `buildLookup()`/`loadOpeningPrefixSet()` produces (e.g. `e4 e5 Ke2` for the Bongcloud Attack), sourced by grepping the real `frontend/public/openings.tsv` for each style's identity per D-05: Attacker = King's/Danish/Evans/Smith-Morra Gambits (white) + Latvian/Englund/Budapest/Albin Gambits (black); Trickster = the exact troll lines named in `trollOpenings.ts`'s provenance comments (Bongcloud, Hammerschlag, Halloween, Sodium, Napoleon, Grob, Barnes on white; Borg Defense, Drunken Knight Variation, Fried Fox Defense on black); Grinder = Ruy Lopez/Slav/QGD/French Exchange Variations (white) + Petrov's Defense/Berlin Defense/Slav Defense (black); Wall = London System/Colle System (white) + Caro-Kann Defense/Dutch Stonewall Variation (black).
- `frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts`: a real-corpus membership test (fetch-stub + `vi.resetModules()` pattern mirroring `openings.test.ts`, reading the actual shipped TSV) asserting all 30 curated lines are members of the real `loadOpeningPrefixSet()` output; a sanity test proving the membership check itself discriminates (a bogus `"e4 e5 Zz9"` string is correctly reported absent); a non-empty-set check per curated set; and 9 `styleLinesFor` tests covering all 8 real style/side pairings plus the defensive-fallback empty-set case.

## Task Commits

1. **Task 1: Curate per-style, per-color SAN-prefix line lists from openings.tsv** — `b0b826be` (feat) — also includes the `styleLinesFor` accessor (see Decisions Made).
2. **Task 2: Add styleLinesFor accessor + a test validating every prefix exists in openings.tsv** — `aa10ff7c` (test)

## Files Created

- `frontend/src/lib/engine/styleOpeningLines.ts` — 8 curated SAN-prefix `ReadonlySet<string>` constants, `Style` type, `styleLinesFor` accessor
- `frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts` — real-corpus membership test + `styleLinesFor` behavior tests

## Verification

- `cd frontend && npx tsc -b` — zero errors.
- `cd frontend && npx vitest run src/lib/engine/__tests__/styleOpeningLines.test.ts` — 12/12 passing.
- `cd frontend && npx vitest run src/lib/engine/` — 208/208 passing across all 15 engine test files (no regression in any existing module).
- `npm run lint` — 0 errors (3 pre-existing unrelated warnings in `coverage/` generated artifacts).
- `npm run knip` — clean.
- Mutation-proof: temporarily inserted a bogus `'e4 e5 Zz9'` string into `ATTACKER_WHITE_LINES` — the corpus-membership test correctly failed, naming the offending set and line (`{"label":"ATTACKER_WHITE_LINES","line":"e4 e5 Zz9"}`). Reverted immediately after (`git diff --stat` confirmed byte-identical to the committed version); tsc + tests re-confirmed green.

## Decisions Made

- `styleLinesFor` implemented in the Task 1 commit alongside the curated data (not deferred to Task 2) — the lookup table + accessor is ~10 lines tightly coupled to the 8 `Set` constants it resolves; splitting it into a separate commit would have added no isolation value. Task 2's `files_modified` already named `styleOpeningLines.ts`, so this stays within plan scope; Task 2's actual new contribution is the test file.
- All 8 curated sets kept non-empty (D-05's "both colors per style" requirement holds for all 4 identities with real, well-known ECO lines). The STYLE-01 "empty set, never undefined" edge case (a `must_haves.truths` backstop item) is instead proven via a defensive-fallback unit test that casts an unrecognized style string (`'NotAStyle' as Style`) into `styleLinesFor`, directly exercising the `EMPTY_LINES` fallback branch — this tests the actual defensive code path rather than relying on an incidentally-barren real style/color pairing.
- Grinder's black-side set includes bare `'d4 d5 c4 c6'` (Slav Defense) as a distinct "solid symmetric structure" entry alongside Wall's black-side Caro-Kann — both are legitimately drawish/simplifying black defenses but represent different structural identities (Slav's queenside-pawn solidity vs Caro-Kann's ...c6-...d5 setup), kept as separate style identities rather than merged.

## Deviations from Plan

None — plan executed as written (see Decisions Made for the Task 1/2 commit-boundary note, which stayed within the plan's stated `files_modified` scope).

## Issues Encountered

None.

## User Setup Required

None — pure static data, no external service configuration.

## Next Phase Readiness

- `styleLinesFor(style, side)` and all 8 curated sets are ready for Plan 04's `styleBookWeighting` factory to consume (per the plan's own key_links: `styleLinesFor(style, side) → per-style×color ReadonlySet<string> consumed by styleBookWeighting`).
- No blockers. `npx tsc -b` (zero errors) and `npx vitest run src/lib/engine/` (208/208) both green.

---
*Phase: 182-style-levers*
*Completed: 2026-07-21*

## Self-Check: PASSED

All claimed files and commits verified present on disk / in git history.
