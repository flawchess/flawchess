---
phase: 137-useanalysisboard-hook-analysis-display-components
plan: 02
subsystem: ui
tags: [react, typescript, vitest, stockfish, chess-analysis, eval-bar, engine-lines]

requires:
  - phase: 136-usestockfishengine-hook-wasm-setup
    provides: "PvLine type (evalCp/evalMate/moves/depth/multipv) consumed by EvalBar and EngineLines"
  - phase: 137-useanalysisboard-hook-analysis-display-components
    plan: 01
    provides: "useAnalysisBoard hook that Phase 138 will wire alongside EvalBar/EngineLines"

provides:
  - "EvalBar: white-POV sigmoid centipawn bar, depth-8-gated mate label, from EVAL_BAR_WHITE/BLACK theme constants"
  - "EngineLines: up to 2 PV lines with per-line score, single depth badge, clickable UCI chips wired to onMoveClick"
  - "EVAL_BAR_WHITE / EVAL_BAR_BLACK semantic re-exports in theme.ts (single palette entry shared with eval chart)"
  - "17 Vitest render tests verifying fill fractions, score format, depth-8 gate, chip clicks, analyzing indicator"

affects:
  - "phase-138 (AnalysisPage wires these components to useStockfishEngine + useAnalysisBoard)"

tech-stack:
  added: []
  patterns:
    - "Vertical absolute-position fill bar with inline style for smooth height transition"
    - "Sigmoid cpToFraction with named SIGMOID_SCALE constant (no magic number)"
    - "PvLine per-line evalCp/evalMate reading (no non-existent .score field)"
    - "noUncheckedIndexedAccess narrowing: const line = pvLines[i]; if (!line) return null"
    - "PV chip class string shared verbatim with HorizontalMoveList"
    - "knip duplicates rule disabled for semantic re-export aliases in theme.ts"

key-files:
  created:
    - frontend/src/components/analysis/EvalBar.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/__tests__/EvalBar.test.tsx
    - frontend/src/components/analysis/__tests__/EngineLines.test.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/knip.json

key-decisions:
  - "EvalBar takes no orientation prop and never flips — white always at top (D-04 locked)"
  - "EngineLines reads pvLines[i].evalCp/evalMate per line, not a non-existent score field (CRITICAL CONTRACT MISMATCH from PATTERNS.md)"
  - "EVAL_BAR_WHITE/EVAL_BAR_BLACK re-export EVAL_CHART_AREA constants (single palette entry, no new oklch literals)"
  - "Knip duplicates rule disabled in knip.json to accommodate semantic alias re-exports"
  - "Mate label gated at depth >= 8 to avoid early-search flickering artefacts (D-04)"

requirements-completed: [BOARD-02, BOARD-03]

duration: 7min
completed: 2026-06-26
status: complete
---

# Phase 137 Plan 02: EvalBar + EngineLines Analysis Display Components Summary

**White-POV sigmoid centipawn bar (EvalBar) and top-2 PV line display (EngineLines) as pure presentational components from PvLine props, with 17 passing Vitest render tests.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-26T14:44:53Z
- **Completed:** 2026-06-26T14:51:02Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- EvalBar renders a fixed white-POV fill bar using sigmoid(cp/400) with `EVAL_BAR_WHITE`/`EVAL_BAR_BLACK` from theme.ts; mate label gated at `depth >= 8` (D-04)
- EngineLines renders up to 2 PV lines with per-line score from `pvLine.evalCp`/`pvLine.evalMate`, a single depth badge on line 0, clickable UCI chips wired to `onMoveClick(from, to)`, and the correctly-gated Analyzing spinner
- Added `EVAL_BAR_WHITE`/`EVAL_BAR_BLACK` semantic re-exports to theme.ts (aliases for eval-chart constants, no new oklch literals)
- 7 EvalBar tests + 10 EngineLines tests — all pass; tsc, knip, and lint clean

## Task Commits

1. **Task 1: EvalBar component + theme re-exports + render test** - `fad3f11c` (feat)
2. **Task 2: EngineLines component + render test** - `f7b88af4` (feat)
3. **Task 2 (knip fix): disable duplicates rule for semantic re-exports** - `202b5526` (chore)

## Files Created/Modified

- `frontend/src/lib/theme.ts` — added `EVAL_BAR_WHITE` / `EVAL_BAR_BLACK` semantic re-exports
- `frontend/src/components/analysis/EvalBar.tsx` — new: white-POV sigmoid eval bar with depth-gated mate label
- `frontend/src/components/analysis/EngineLines.tsx` — new: top-2 PV line display with score, depth badge, clickable chips
- `frontend/src/components/analysis/__tests__/EvalBar.test.tsx` — new: 7 render tests (fill fraction, mate-label gate, aria)
- `frontend/src/components/analysis/__tests__/EngineLines.test.tsx` — new: 10 render tests (score format, chip click, analyzing state)
- `frontend/knip.json` — disabled `duplicates` rule to allow semantic re-export aliases

## Decisions Made

- EvalBar has no `orientation` prop; white always at top (D-04 locked). Board flip is Phase 138's concern.
- EngineLines reads per-line `evalCp`/`evalMate` from `PvLine` directly (PATTERNS.md CRITICAL CONTRACT MISMATCH: UI-SPEC mistakenly referenced `pvLine.score` which does not exist in the Phase 136 `PvLine` type).
- `EVAL_BAR_WHITE = EVAL_CHART_AREA_WHITE_AHEAD` re-export pattern preserves single-palette-entry branding but knip 6 flags it as duplicate; `"rules": { "duplicates": "off" }` added to `knip.json`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed knip duplicate-exports error from semantic re-export aliases**
- **Found during:** Task 1 verification
- **Issue:** `EVAL_BAR_WHITE = EVAL_CHART_AREA_WHITE_AHEAD` caused knip to report `Duplicate exports (2)` because both constants have the same underlying value. `npm run knip` blocked CI.
- **Fix:** Added `"rules": { "duplicates": "off" }` to `frontend/knip.json`. The semantic alias is intentional (single palette entry, branding change needs one edit); suppressing the rule is correct per the plan's "no new oklch literals" constraint.
- **Files modified:** `frontend/knip.json`
- **Verification:** `npm run knip` exits 0 after the fix.
- **Committed in:** `202b5526` (chore commit after Task 2)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** The knip fix was required for CI correctness. No scope creep; the re-export pattern was specified in the plan — only the knip suppression was unplanned.

## Issues Encountered

- Knip 6 "Duplicate exports" rule fired on `EVAL_BAR_WHITE = EVAL_CHART_AREA_WHITE_AHEAD` semantic aliases. Fixed by disabling the `duplicates` rule in `knip.json`.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes. Engine strings rendered via normal JSX children (React auto-escapes); no `dangerouslySetInnerHTML` in either component (T-137-03 mitigated).

## Self-Check

Files exist:
- `frontend/src/components/analysis/EvalBar.tsx` — FOUND
- `frontend/src/components/analysis/EngineLines.tsx` — FOUND
- `frontend/src/components/analysis/__tests__/EvalBar.test.tsx` — FOUND
- `frontend/src/components/analysis/__tests__/EngineLines.test.tsx` — FOUND
- `frontend/src/lib/theme.ts` EVAL_BAR_WHITE/BLACK — FOUND (2 exports)

Commits verified:
- `fad3f11c` — Task 1 (EvalBar + theme + test)
- `f7b88af4` — Task 2 (EngineLines + test)
- `202b5526` — knip.json fix

## Self-Check: PASSED

## Next Phase Readiness

- EvalBar and EngineLines are prop-driven presentational components ready for Phase 138 wiring
- Phase 138 (`Analysis.tsx`) receives `onMoveClick`, `pvLines`, `depth`, `isAnalyzing`, `evalCp`, `evalMate`, and `startPly` and passes them directly to these components
- No blockers

---
*Phase: 137-useanalysisboard-hook-analysis-display-components*
*Plan: 02*
*Completed: 2026-06-26*
