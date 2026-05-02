---
phase: 77-troll-opening-watermark-on-insights-findings
plan: 04
subsystem: frontend/move-explorer
tags: [frontend, ui, troll-watermark, react, tdd]
requires:
  - frontend/src/lib/trollOpenings.ts (Plan 01)
  - frontend/src/data/trollOpenings.ts (Plan 01)
  - frontend/src/assets/troll-face.svg (Plan 01)
provides:
  - Inline troll-face icon next to qualifying SAN rows in MoveExplorer
  - sideJustMoved derivation contract on MoveExplorer (full-FEN required)
affects:
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx
tech-stack:
  added: []
  patterns:
    - "Parent derives once, passes via prop (Pattern 2)"
    - "Defensive throw on input contract (Pitfall 7)"
key-files:
  created: []
  modified:
    - frontend/src/components/move-explorer/MoveExplorer.tsx
    - frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx
decisions:
  - "Place sideJustMoved useMemo BEFORE moveMap so its friendly error message wins over chess.js's generic FEN error"
  - "Update makeEntry test factory to default result_fen to a valid 8-rank board FEN (was empty string) since isTrollPosition now throws on malformed input"
metrics:
  duration: "5m"
  completed: 2026-04-28
  tasks_completed: 2
  files_modified: 2
  tests_added: 6
  tests_total: 19
---

# Phase 77 Plan 04: Move Explorer Inline Troll Icon Summary

Inline troll-face icon now renders next to SAN rows in `MoveExplorer` whose `result_fen` is in the curated troll set for the side that just moved (D-06), suppressed on mobile via `hidden sm:inline-block` (D-07), with side derivation owned by the parent `MoveExplorer` component (D-10) and a defensive throw guarding against board-only FEN inputs (Pitfall 7).

## Implementation

**Parent (`MoveExplorer`)**: A `useMemo` keyed on `[position]` parses the FEN's side-to-move token; throws `MoveExplorer: position must be a full FEN with side-to-move, got: <position>` if the token is missing or not `'w'`/`'b'`. Returns `Color` (`'white'` | `'black'`). Passed to every `MoveRow` instance via `sideJustMoved` prop.

**Child (`MoveRow`)**: Computes `showTroll = isTrollPosition(entry.result_fen, sideJustMoved)` inline (no `useMemo`, per RESEARCH.md anti-pattern note). When true, renders an `<img>` AFTER the SAN text inside an `inline-flex items-center gap-1` wrapper. Icon attributes:
- `src={trollFaceUrl}`
- `alt=""` and `aria-hidden="true"` (decorative)
- `data-testid="move-list-row-${entry.move_san}-troll-icon"`
- `className="hidden sm:inline-block h-3.5 w-3.5"` (desktop-only, fully opaque, small)

**Icon placement in SAN cell** (per output spec): the icon is placed AFTER the SAN text inside the `inline-flex items-center gap-1` wrapper:
```tsx
<td className="py-1 text-sm text-foreground font-normal truncate">
  <span className="inline-flex items-center gap-1">
    <span>{entry.move_san}</span>
    {showTroll && <img ... />}
  </span>
</td>
```

**`useMemo` dependency**: `[position]` (per output spec confirmation).

## Test Count Delta

`MoveExplorer.test.tsx` test count: **13 -> 19** (+6 Phase 77 tests). All 19 pass; lint and typecheck clean.

The 6 new tests in `describe('Phase 77 — Troll-opening inline icon', ...)`:
1. `renders troll icon when result_fen matches WHITE_TROLL_KEYS and parent is white-to-move` (D-06 positive)
2. `does not render troll icon when result_fen is not in the troll set` (D-06 negative)
3. `routes to BLACK_TROLL_KEYS when parent position is black-to-move (D-10)` (side derivation)
4. `icon has hidden + sm:inline-block class for mobile suppression (D-07)` (class-based, not visibility — jsdom is desktop-width)
5. `throws when position is a board-only FEN with no side-to-move token (Pitfall 7)` (defensive contract)
6. `icon is decorative (alt="" + aria-hidden)` (a11y)

## Existing Test Compatibility

The plan's output spec asks: "Whether the existing `position={START_FEN}` test fixtures continue to satisfy the throw-defensive check (they pass full FENs, so no regression)."

**Confirmed**: yes. `START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'` and `AFTER_E4_FEN = '... b KQkq - 0 1'` are both full FENs whose `split(' ')[1]` yields `'w'` / `'b'`, so the `sideJustMoved` derivation passes through them. No change needed to the 13 existing tests' `position` props.

However, the **`makeEntry` test factory needed an update**: its previous default `result_fen: ''` produced 0 ranks, which now triggers `deriveUserSideKey`'s `expected 8 ranks` throw on every render that doesn't override `result_fen`. Updated default to `'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'` (the starting-position board FEN, a non-troll key). This is an internal test-only change; it doesn't affect production code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reordered `sideJustMoved` useMemo BEFORE `moveMap` useMemo**
- **Found during:** Task 2 (Pitfall 7 test failed)
- **Issue:** The plan's step 2 in Task 1 instructed placing `sideJustMoved` "immediately after the existing `moveMap` `useMemo`". But `moveMap` calls `new Chess(position)` which throws `Invalid FEN: must contain six space-delimited fields` on board-only FENs *before* `sideJustMoved` ever runs. The Pitfall 7 test was asserting the friendly `must be a full FEN with side-to-move` error.
- **Fix:** Moved the `sideJustMoved` useMemo above `moveMap`. The defensive check now wins, producing the documented error message.
- **Files modified:** `frontend/src/components/move-explorer/MoveExplorer.tsx`
- **Commit:** `8dd77f7` (Task 2)

**2. [Rule 3 - Blocking] Updated `makeEntry` test factory default `result_fen`**
- **Found during:** Task 1 (existing tests broke after adding `isTrollPosition` call)
- **Issue:** Task 1's plan promised "existing tests use `position={START_FEN}` which is a full FEN — they should continue to pass." That holds for `position`, but every existing test relies on `makeEntry`'s default `result_fen: ''`, which trips `deriveUserSideKey`'s 8-rank validation throw added in Plan 01. All 13 existing tests failed with `Invalid FEN piece-placement: expected 8 ranks, got 1`.
- **Fix:** Changed `makeEntry`'s default `result_fen` to the valid starting-position board FEN `'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'` (a non-troll key, so it doesn't accidentally render the icon in non-Phase-77 tests). Tests that exercise the troll path override `result_fen` explicitly.
- **Files modified:** `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx`
- **Commit:** `e155497` (Task 1)

## Verification

- `cd frontend && npm test -- --run src/components/move-explorer/__tests__/MoveExplorer.test.tsx` -> 19 passed (0 failed)
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` -> exit 0 (no errors)
- `cd frontend && npm run lint` -> 0 errors (3 pre-existing coverage-dir warnings, unrelated)
- Manual mobile-suppression check at 375px deferred to phase-end per VALIDATION.md

## Commits

| Task | Commit  | Description                                                                  |
| ---- | ------- | ---------------------------------------------------------------------------- |
| 1    | e155497 | feat(77-04): add inline troll-face icon to MoveExplorer SAN cells            |
| 2    | 8dd77f7 | test(77-04): add Phase 77 troll-icon describe block + reorder useMemos       |

## Self-Check: PASSED

- File `frontend/src/components/move-explorer/MoveExplorer.tsx`: FOUND (modified)
- File `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx`: FOUND (modified)
- Commit `e155497`: FOUND in git log
- Commit `8dd77f7`: FOUND in git log
- All 19 tests pass; typecheck clean; lint clean (no new errors)
