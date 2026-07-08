---
phase: 155-react-hook-anytime-ui-free-analysis
plan: 03
subsystem: ui
tags: [react, typescript, vitest, mcts, engine-ui]

# Dependency graph
requires:
  - phase: 155-01
    provides: "FLAWCHESS_ENGINE_ACCENT/FLAWCHESS_ENGINE_HEADLINE_ACCENT theme tokens, expectedScoreToWhitePovCp(es, rootMover), Wave 0 test scaffold for FlawChessEngineLines.test.tsx"
provides:
  - "FlawChessEngineLines component (body-only): rankedLines: RankedLine[] -> top-3 rows with score-pair badge + modal-path SAN chips"
  - "EngineLines.tsx additive exports: replayPvLine, formatScore, EngineLinesSkeleton rows prop, LINES_MIN_HEIGHT_3"
affects: [155-04-Analysis-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FlawChessEngineLines is a structural sibling of EngineLines.tsx, reusing its replayPvLine/formatScore/EngineLinesSkeleton verbatim via export rather than duplicating them"
    - "Score-pair badge: two independently-colored inline spans (STOCKFISH_ACCENT / FLAWCHESS_ENGINE_HEADLINE_ACCENT) inside one aria-labeled shell, instead of EngineLines' single-color filled pill"

key-files:
  created:
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
  modified:
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx

key-decisions:
  - "Exported replayPvLine and formatScore from EngineLines.tsx (additive `export` keyword only, no behavior change) rather than duplicating their bodies into the new file, avoiding a Knip-flagged unused duplicate per the plan's stated preference"
  - "Extended EngineLinesSkeleton with a rows?: 2 | 3 prop (default 2) plus a new exported LINES_MIN_HEIGHT_3 constant, instead of writing a second skeleton component — rows=3 both sizes the container height and drives the placeholder row count via Array.from"
  - "FlawChessEngineLines has no compact prop (unlike EngineLines) — card placement/mobile-tab wiring is explicitly Plan 04's job per this plan's Out-of-Scope section, so the body component only needs its single (desktop-shaped) layout for now"
  - "moveLabel(startPly, moveIndex) called directly (no ternary) — EngineLines' `lineIndex === 0 ? moveIndex : moveIndex` ternary was a no-op (both branches identical), not worth reproducing"

patterns-established:
  - "New engine-source display components extend EngineLines.tsx's exported helpers (replayPvLine/formatScore/EngineLinesSkeleton) rather than re-implementing PV-replay or score-formatting logic"

requirements-completed: [DISPLAY-02, DISPLAY-03]

coverage:
  - id: D1
    description: "FlawChessEngineLines renders exactly 3 rows from a 4-line rankedLines fixture (MAX_LINES=3, D-08)"
    requirement: "DISPLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx#renders exactly 3 rows from a 4-line fixture (MAX_LINES=3, D-08)"
        status: pass
    human_judgment: false
  - id: D2
    description: "modalPath renders as clickable SAN chips, first MAX_PLIES=5 visible with an expand chevron revealing the rest of a >5-ply path"
    requirement: "DISPLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx#renders modalPath as SAN chips, first MAX_PLIES=5 plies + expand chevron (DISPLAY-02)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Each row's score-pair badge shows both the objective (white-POV Stockfish cp) and practical (expectedScoreToWhitePovCp-derived) numbers, correctly formatted and aria-labeled without the bare phrase 'best move'"
    requirement: "DISPLAY-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx#renders the objective/practical score pair per line (DISPLAY-03)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Clicking a modal-path chip calls onMoveClick with the full UCI prefix up to and including the clicked move (D-10 graft semantics)"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx#clicking a modal-path chip calls onMoveClick with the expected UCI prefix (D-10)"
        status: pass
    human_judgment: false
  - id: D5
    description: "EngineLines.tsx changes are additive only (existing behavior unchanged); full frontend suite, tsc, lint, and knip all pass/clean per plan expectations"
    verification:
      - kind: unit
        ref: "npx vitest run src/components/analysis/__tests__/EngineLines.test.tsx (13/13 pass, unchanged) + npm test -- --run (127 files / 1519 tests pass) + npx tsc -b --noEmit + npm run lint (clean)"
        status: pass
    human_judgment: false

# Metrics
duration: 13min
completed: 2026-07-06
status: complete
---

# Phase 155 Plan 03: FlawChessEngineLines (Score-Pair Badge + Modal-Path Chips) Summary

**`FlawChessEngineLines.tsx` renders the top 3 FlawChess Engine ranked practical lines as a structural sibling of `EngineLines.tsx`, with a two-number objective/practical score-pair badge and clickable modal-path SAN chips — the visible surface of DISPLAY-02 and DISPLAY-03.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-07-06T19:58:00+02:00 (approx.)
- **Completed:** 2026-07-06T20:11:00+02:00 (approx.)
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `FlawChessEngineLines.tsx` created: body-only component (no Card/CardHeader wrapper — that's Plan 04's job) accepting `rankedLines: RankedLine[]`, `isSearching`, `startPly`, `baseFen`, optional `rootMover` (derived via `sideToMoveFromFen(baseFen)` when omitted), `flipped`, `onMoveClick`
- Score-pair badge (D-06, DISPLAY-03): a two-segment aria-labeled span — objective (`formatScore(objectiveEvalCp, null)`, `STOCKFISH_ACCENT`) and practical (`formatScore(expectedScoreToWhitePovCp(practicalScore, rootMover), null)`, `FLAWCHESS_ENGINE_HEADLINE_ACCENT`) — aria-label reads `"Line {n}: objectively {X}, practically {Y} for you"`, never the bare phrase "best move" (ARROW-04 principle)
- Modal-path chips (D-07, DISPLAY-02): `RankedLine.modalPath` walked via the (now-exported) `replayPvLine()`, first `MAX_PLIES=5` chips + `ChevronDown` expand for the rest, identical hover `Tooltip`+`MiniBoard` preview and `onMoveClick(moves.slice(0, moveIndex+1))` graft semantics as `EngineLines.tsx` (D-10)
- Top 3 lines (D-08): local `MAX_LINES=3` constant, distinct from `EngineLines.tsx`'s own `MAX_LINES=2` — the shared constant was left untouched
- First-paint skeleton (D-09): `EngineLinesSkeleton` extended with a `rows?: 2 | 3` prop (default 2) and a new exported `LINES_MIN_HEIGHT_3` constant, so the 3-row FlawChess card gets a correctly-sized fixed-height placeholder without a second skeleton component
- `EngineLines.tsx` edits are additive only: `replayPvLine` and `formatScore` gained an `export` keyword (bodies unchanged); `EngineLinesSkeleton`'s new `rows` prop defaults to 2, preserving every existing caller's behavior exactly (verified: `EngineLines.test.tsx` 13/13 unchanged)
- `FlawChessEngineLines.test.tsx`'s two Wave 0 `it.todo` placeholders replaced with 10 real render tests covering the 3-row cap, chip/expand rendering, score-pair numbers + aria-label, null-`objectiveEvalCp` placeholder, `onMoveClick` graft, semantic-button chips, skeleton gating both directions, and a no-"best move"-unqualified guard

## Task Commits

Each task was committed atomically:

1. **Task 1: Build FlawChessEngineLines (score-pair badge + modal-path SAN chips + graft)** - `7e8e3cae` (feat)
2. **Task 2: Fill in FlawChessEngineLines test (chips + score pair) — DISPLAY-02/03** - `f7bab366` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/components/analysis/FlawChessEngineLines.tsx` - New body-only component (top-3 ranked lines, score-pair badge, modal-path chips)
- `frontend/src/components/analysis/EngineLines.tsx` - Additive: exported `replayPvLine`/`formatScore`, `EngineLinesSkeleton` gained a `rows` prop, new exported `LINES_MIN_HEIGHT_3` constant
- `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` - Filled in with 10 real tests (was 2 `it.todo` placeholders)

## Decisions Made

- Exported `replayPvLine`/`formatScore` from `EngineLines.tsx` rather than duplicating their bodies, per the plan's stated preference (avoids a Knip-flagged unused duplicate; both functions are byte-identical to the originals, just reused)
- `EngineLinesSkeleton` extended with a `rows?: 2 | 3` prop (default `2`) plus a new exported `LINES_MIN_HEIGHT_3` constant, rather than writing a second skeleton component for the 3-row card
- `FlawChessEngineLines` intentionally has no `compact` prop — per the plan's explicit Out-of-Scope note, card placement and any mobile-tab-specific layout are Plan 04's job; this body component only needs its single desktop-shaped layout for now
- `moveLabel(startPly, moveIndex)` is called directly without the `lineIndex === 0 ? moveIndex : moveIndex` ternary present in `EngineLines.tsx`'s `PvLineRow` — that ternary was a no-op in the original (both branches identical) and wasn't worth reproducing in the new component

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `FlawChessEngineLines` is ready for Plan 04's `Analysis.tsx` integration: accepts `rankedLines`/`isSearching`/`startPly`/`baseFen`/`rootMover`/`flipped`/`onMoveClick`, no JSX wrapper baked in
- `npm run knip` flags `FlawChessEngineLines.tsx` (and the Plan 01 `switch.tsx` + 2 theme tokens) as currently unused — expected, matching the Plan 01 SUMMARY's precedent: nothing this phase produces is wired into `Analysis.tsx` until Plan 04
- Full frontend suite green: 127 passed test files, 1519 passed tests; `npx tsc -b --noEmit` and `npm run lint` both clean
- DISPLAY-02 and DISPLAY-03 marked complete in `REQUIREMENTS.md` — DISPLAY-02 was never shared with another plan's frontmatter, and DISPLAY-03's Plan 01/03 split closes here per the requirement's own "closes when Plan 03 lands" note

---
*Phase: 155-react-hook-anytime-ui-free-analysis*
*Completed: 2026-07-06*

## Self-Check: PASSED

All 3 created/modified source files plus the SUMMARY.md itself verified present on disk; both commit hashes (7e8e3cae, f7bab366) verified present in git log.
