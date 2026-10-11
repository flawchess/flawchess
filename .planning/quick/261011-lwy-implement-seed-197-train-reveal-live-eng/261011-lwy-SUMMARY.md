---
phase: quick-261011-lwy
plan: 01
subsystem: frontend/train-reveal
tags: [train, reveal, stockfish, move-list, seed-197]
requires: []
provides:
  - first-move-only reveal chips with a dimmed live-engine preview at the end of the move list
  - commit-on-step navigation (forward button, ArrowRight, preview token tap)
  - Stockfish row rank offset (lines 2..N at a previewed leaf), preview-driven board pointer
affects:
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/analysis/VariationTree.tsx
tech-stack:
  added: []
  patterns:
    - pure preview model in lib + ephemeral state sub-hook (preview never stored in the tree or the Analyze snapshot)
key-files:
  created:
    - frontend/src/lib/trainRevealPreview.ts
    - frontend/src/lib/__tests__/trainRevealPreview.test.ts
    - frontend/src/hooks/useRevealPreview.ts
  modified:
    - frontend/src/lib/trainRevealLines.ts
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/board/HorizontalMoveList.tsx
    - frontend/src/components/train/TrainMoveTreeList.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainLineChips.tsx
    - frontend/src/lib/trainArrows.ts
    - CHANGELOG.md
decisions:
  - "Preview committed ids are recorded synchronously in commitPreview, so committed nodes are never graded even on the first render"
  - "The solid board pointer is the preview's next move whatever the Stockfish arrows setting says; only the live secondary arrows honor sfArrows 0"
metrics:
  tasks: 3
status: complete
actuals:
  tokens: 45000
  tasks: 3
  commits: 3
plan_head_before: 73433527990e3ac9480d578fa1b0f49dc8d9f668
plan_head_after: d2433c94e95e80ee3b92fbbba8d3235ccc963300
---

# Quick 261011-lwy: SEED-197 Train reveal live engine preview Summary

Each reveal chip now owns only its first move; the rest of its graded line is a dimmed, never-stored live-engine preview (at most 6 plies) at the end of the move list. The forward button, ArrowRight or a tap on a preview token commits it into the tree as real, ungraded nodes.

## Commits

| Task | Commit | Scope |
| ---- | ------ | ----- |
| 1 | `145243377` | Pure preview model (`trainRevealPreview.ts`) and first-move-only chip model (`trainRevealLines.ts`), with unit tests |
| 2 | `4aa5c0e4b` | `useRevealPreview` hook and commit-on-step navigation in `useTrainRevealTree`, with hook tests |
| 3 | `d2433c94e` | Preview render mode, Stockfish row rank offset, board pointer, "Graded eval" label, test updates, CHANGELOG |

## What changed in Task 3

- `HorizontalMoveList`: additive optional `onSelect` / `leading` / `after` item fields (Openings, bots and TacticLineExplorer untouched).
- `VariationTree`: opt-in `preview` prop (`VariationTreePreview`), honored by the wrap renderer only. Dimmed tokens `variation-preview-N` (index-based testids), a `variation-preview-eval` pill (text-sm, white on `BEST_MOVE_ARROW`), at a main-line leaf or inside a sideline's parentheses. The closing ")" and delete x move onto the last preview token's `after` slot via a shared `BlockClosing` helper.
- `EngineLines`: `allSecondary` replaced by `rankOffset` (badge color, aria-label and testids carry the true rank).
- `TrainMoveTreeList`: wires the preview (`token i` commits `i + 1` plies) and shows lines 2..N with `rankOffset=1` at a previewed leaf, all lines elsewhere.
- `TrainSolveScreen.resolveRevealBoardOverlay`: pointer = preview next move when anchored at the current node; a chip first-move node keeps the chip quality badge and highlight; a preview-committed node shows a plain last-move highlight.
- `TrainLineChips`: eval pill carries `title="Graded eval"` and `aria-label="Graded eval <score>"`.
- `trainArrows`: `dropLineMove` and its tests removed; doc comments reworded.
- CHANGELOG: new `[Unreleased]` Changed bullet; the superseded final sentence of the stepping bullet replaced.

## Deviations from Plan

### Task 1
None in behavior. The inherited-tail walk stops at the first (nearest) matching ancestor.

### Task 2
- **[Rule 1 - Bug avoidance] Synchronous committed-id recording.** Committed ids are recorded in `commitPreview` itself rather than via an effect on `[pending, nodes]`, so a freshly committed node is never graded on the first render.
- `source` ('live' | 'stored' | 'seed' | 'inherited') is not exposed on `RevealPreviewView` (not needed by any consumer).

### Task 3
- **[Rule 1 - Test fix] TrainSolveScreen tests rewritten, not weakened.** 7 tests failed and were rewritten for the replacement behavior: the "disagreeing engine move as secondary arrow" test now pins a depth-9 reveal engine (below `TRAIN_LIVE_ALT_MIN_DEPTH`) so the graded tail stays the pointer, with a new companion test for depth 10 where the live PV replaces the tail; `tapListMove(1)` in two tests became `tapPreview(0)`; the sideline/telemetry/badge tests use `engine-line-1-move-0` (rank 2) at a previewed leaf and assert the engine move becomes a real `variation-node-*`. Added: ArrowRight commit test and an Analyze-snapshot test (committed paths only, never the uncommitted preview).
- **Judgement call: pointer vs the Stockfish arrows setting.** Following the plan ("the solid pointer is always the preview's next move"), a previewed leaf draws the pointer even when the Stockfish arrows setting is 0. The `Stockfish arrows 0` test now asserts exactly one arrow (the preview pointer) instead of zero. Flag if the owner wants sfArrows 0 to suppress it.
- `aria-label` on the chip eval pill is on a plain span (as specified); no role added.

## Gate results (frontend)

- `npm run lint`: clean.
- `npm run build` (tsc -b + vite): passes.
- `npm test -- --run`: 5521-5522 of 5523 pass per run. The only failures were load flakes unrelated to this change (machine load average 40-48 from other sessions): `TrainStreakCard` "streak up" (3s waitFor on a real-timer animation) in two full runs, and `Train.solveLoop` (15s timeout) in one. Each passes when re-run alone (`TrainStreakCard` 24/24, `Train.solveLoop` + `TrainStreakCard` 31/31). Neither file imports anything touched here.
- `npm run knip`: clean (only the existing `.css` configuration hint).
- `TrainSolveScreen.test.tsx`: 174/174. `VariationTree`, `EngineLines`, `TrainMoveTreeList`, `TrainLineChips`, `trainArrows` suites pass.

## Manual browser UAT to do

- Open a reveal: faded preview after the chip move, with the blue live eval pill; chip eval tooltip reads "Graded eval".
- Press forward / ArrowRight repeatedly: instant commits; pause and watch the preview refine once the engine passes depth 10; committed nodes never change.
- Tap a faded token mid-preview (including from the puzzle position): commits that many plies.
- Sideline leaf: preview sits inside the parentheses, before ")" and the delete x; x still deletes.
- Stockfish row starts at "Line 2" at a leaf and at "Line 1" on a node with children; reserved height does not jump.
- Mobile (two-row list, 6-ply preview): list auto-scroll and wrap look right.
- Confirm preference on sfArrows 0 (pointer still draws).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Commits `145243377`, `4aa5c0e4b`, `d2433c94e` are ancestors of HEAD; created files exist (`trainRevealPreview.ts`, `trainRevealPreview.test.ts`, `useRevealPreview.ts`).

## Post-review fixes (orchestrator, 2026-10-11)

Code review (261011-lwy-REVIEW.md): 0 critical, 3 warnings, 5 info. Fixed with a mutation-checked test each:

| Finding | Commit | Fix |
|---|---|---|
| WR-02 | `3e4867134` | `committedPaths` in `RevealTreeSnapshot`; restore re-marks them never-graded |
| WR-03 | `efae4adc9` | `useRevealPreview` resets stored lines + committed ids eagerly on `resetKey` change |
| WR-01 | `65e9c1a39` | `pendingNextIdRef` guard: a second same-event `commitPreview` no longer marks the next hand-played move's id |
| IN-05 | `c03fb3b3c` | "Graded eval" as `sr-only` text (title tooltip kept) |
| IN-03 | `c7bd22191` | `EngineLines` rows keyed by `lineIndex + rankOffset` |

## Browser UAT (orchestrator, Chrome on dev :5174, 2026-10-11)

Verified live (tab visibility forced to `visible`, since the engine pauses in a hidden tab):
- Reveal opens with the chip's first move + a 6-ply dimmed preview (`text-muted-foreground`) led by the live eval pill; all three chip evals carry "Graded eval".
- ArrowRight: first press steps onto the chip move, later presses commit preview moves instantly; the inherited tail is replaced by the live PV once deep (Raxd8 -> Nxd8 Bf3 ...).
- Stepping back onto a node with children: no preview; Stockfish row shows lines 1..2; at a leaf only line 2; row height constant (50px).
- Token tap `variation-preview-2` committed exactly 3 plies.
- A board move at a6 created a sideline with the preview inside its parentheses before ")".
- **Fixed during UAT** (`6d15ebdc0`): on the 375x667 phone viewport, the `nearest` auto-scroll left the current move on the bottom row of the two-row list and the whole preview below the fold. The last preview token is now a scroll tail; the box scrolls so current + preview both fit. Re-verified: current node and all 6 preview plies visible. Full gate after the fix: lint, build, knip clean; 326 files / 5539 tests pass.

Pre-existing, NOT caused by this task: Analyze -> browser Back restores only the chip move (committed nodes and hand-played sidelines are lost) although sessionStorage holds the correct snapshot. Reproduced identically on the pre-change build (:5173, phase-238 branch, same reveal code as main before this task). Flagged for a follow-up.

Open for the owner: sfArrows = 0 still draws the solid preview pointer (executor's reading of "always the preview's next move"); one-line gate in `resolveRevealBoardOverlay` if 0 should hide it.
