---
phase: 139-tactic-mode-overlay-phase-135-subsume
plan: "03"
subsystem: frontend
status: complete
tags: [tactic-mode, deletion, cleanup, phase-135-retire, knip]
dependency_graph:
  requires:
    - "139-01: TacticModeOverlay + Analysis.tsx tactic wiring (regression tests = deletion gate)"
    - "139-02: FlawCard + LibraryGameCard Explore repointed (no remaining callers)"
  provides:
    - "TacticLineExplorer.tsx deleted (modal retired)"
    - "useTacticLine.ts deleted (PV stepper retired)"
    - "TacticLineExplorer.test.tsx + useTacticLine.test.tsx deleted"
    - "knip clean after deletion (useTacticLines survives via Analysis.tsx caller)"
  affects:
    - "TACTIC-03 requirement satisfied — modal retired, all entry points on /analysis"
tech_stack:
  added: []
  patterns:
    - "Deletion gated on parity verification (Pitfall 9 prevention: depends_on 139-01+02)"
    - "knip as dead-export sentinel post-deletion"
key_files:
  created: []
  modified: []
  deleted:
    - "frontend/src/components/library/TacticLineExplorer.tsx"
    - "frontend/src/hooks/useTacticLine.ts"
    - "frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx"
    - "frontend/src/hooks/__tests__/useTacticLine.test.tsx"
decisions:
  - "All 4 deletions committed in single atomic commit (628cf01e) — no partial removal"
  - "Comment-only references to TacticLineExplorer in surviving files are historical context, not active usage — left in place"
metrics:
  duration: "5min"
  completed: "2026-06-26"
  tasks: 1
  files: 4
---

# Phase 139 Plan 03: Deletion Gate — Retire TacticLineExplorer Summary

One-liner: TacticLineExplorer.tsx and useTacticLine.ts (plus their 26-test suites) deleted after entry-point repointing verified in Plan 02; knip, tsc -b, lint, and all 1196 remaining frontend tests pass.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Delete modal + retired hook and pass deletion gate | 628cf01e | -TacticLineExplorer.tsx, -useTacticLine.ts, -TacticLineExplorer.test.tsx, -useTacticLine.test.tsx |

## What Was Built

### Task 1 — Deletion + Gate

**Pre-deletion confirmation:** `grep -rn "^import.*TacticLineExplorer\|^import.*useTacticLine\b"` returned zero matches — no production file imports either name after Plans 01+02 repointed all callers.

**Deleted files:**
- `frontend/src/components/library/TacticLineExplorer.tsx` (576 lines — modal PV stepper, now subsumed by TacticModeOverlay on /analysis)
- `frontend/src/hooks/useTacticLine.ts` (197 lines — client-side PV stepper, now replaced by useAnalysisBoard.loadMainLine seeding)
- `frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx` (570+ lines, 16 tests)
- `frontend/src/hooks/__tests__/useTacticLine.test.tsx` (190+ lines, 10 tests)

Total: 1,635 lines deleted across 4 files.

**Deletion gate results:**

| Gate | Result |
|------|--------|
| `npx tsc -b --noEmit` | exit 0 |
| `npm run knip` | exit 0 (no unused files / dead exports) |
| `npm run lint` | exit 0 (3 warnings in auto-generated coverage/ only) |
| `npm test -- --run` | 1196/1196 passed (103 test files) |

Test count: 1222 → 1196 (26 tests from deleted suites retired); test files: 105 → 103.

**useTacticLines survives:** `useLibrary.ts:useTacticLines` is now called by `Analysis.tsx` (Plan 01 wiring); knip confirms it's live — no dead-export penalty.

## Deviations from Plan

None. The deletion was clean — no secondary dead exports from helpers used exclusively by the retired files. knip confirmed all surviving exports have callers.

## Test Results

```
Test Files  103 passed (103)
     Tests  1196 passed (1196)
```

## Known Stubs

None. This is a pure deletion plan — no new code introduced.

## Threat Flags

None. Deleting the modal removes a DOM surface (no new network or auth exposure). The /analysis route that replaces it is already auth-gated by ProtectedLayout (scoped in Phase 138).

## Self-Check: PASSED

- `frontend/src/components/library/TacticLineExplorer.tsx` does not exist: PASSED (gone)
- `frontend/src/hooks/useTacticLine.ts` does not exist: PASSED (gone)
- `frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx` does not exist: PASSED (gone)
- `frontend/src/hooks/__tests__/useTacticLine.test.tsx` does not exist: PASSED (gone)
- No import statements referencing TacticLineExplorer or useTacticLine in src/: PASSED
- Commit 628cf01e exists: FOUND
- `knip` exits 0: PASSED
- `tsc -b --noEmit` exits 0: PASSED
- `npm run lint` exits 0: PASSED
- All 1196 tests pass: PASSED
