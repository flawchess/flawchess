---
phase: 155-react-hook-anytime-ui-free-analysis
fixed_at: 2026-07-06T19:11:00Z
review_path: .planning/phases/155-react-hook-anytime-ui-free-analysis/155-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 155: Code Review Fix Report

**Fixed at:** 2026-07-06T19:11:00Z
**Source review:** .planning/phases/155-react-hook-anytime-ui-free-analysis/155-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, WR-03, WR-04 — IN-01/02/03/04 skipped per instruction, cosmetic/out of scope)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Stockfish engine card renders completely blank in the app's default state (both switches ON)

**Files modified:** `frontend/src/pages/Analysis.tsx`, `frontend/src/pages/__tests__/Analysis.test.tsx`
**Commit:** `9b416032`
**Applied fix:** Added a third branch (between `!engineEnabled` and the `<EngineLines>` fallback) in both the desktop `analysis-engine-card` body and the mobile `analysis-engine-lines-mobile` strip, showing "Merged into FlawChess Engine" when the Stockfish switch is ON but suppressed by the FlawChess Engine handoff. The mobile strip previously had no `!engineEnabled` branch at all either (only `engineLoading` / fallback), so the "Engine off" message was also added there for full desktop/mobile parity, matching the existing styling exactly (`flex h-full items-center px-2 text-sm text-muted-foreground`). Added `data-testid="analysis-engine-merged-message"` (desktop) / `"...-mobile"` (mobile) for testability. Added a regression test in `Analysis.test.tsx` asserting the merged message appears in the untouched default render (both switches ON, no clicks) and that the loading skeleton is absent.

### WR-01: `mctsSearch(...).then(...)` has no `.catch`

**Files modified:** `frontend/src/hooks/useFlawChessEngine.ts`
**Commit:** `d9156866` (combined with WR-02 — same effect, adjacent diff hunk, logically one change per the fix-agent's grouping allowance)
**Applied fix:** Restructured `.then(...)` into `.then(...).catch((err) => { if (aborted) return; Sentry.captureException(err, { tags: { source: 'flawchess-engine' } }); setIsSearching(false); })`. Added `import * as Sentry from '@sentry/react'`, matching the import style already used in `useMaiaEngine.ts` and `lib/engine/workerPool.ts`.

### WR-02: Search-trigger effect never aborts its own `AbortController` when `enabled` transitions to `false` without a FEN change

**Files modified:** `frontend/src/hooks/useFlawChessEngine.ts`
**Commit:** `d9156866`
**Applied fix:** Added a dedicated effect (`useEffect(() => { return () => abortControllerRef.current?.abort(); }, [debouncedFen, enabled]);`) whose only job is the cleanup — it runs on every `debouncedFen`/`enabled` change and on unmount, independent of whether the search-trigger effect's own guard passes. Verified the existing throttle and abort regression tests (`useFlawChessEngine.test.ts`) still pass unmodified — the new effect's abort is idempotent alongside the search-trigger effect's own explicit `abort()` call.

### WR-03: Right eval bar ("SF" cap) ignores the Stockfish toggle entirely while FlawChess Engine is enabled

**Files modified:** `frontend/src/pages/Analysis.tsx`
**Commit:** `18b5737d`
**Applied fix:** Gated `rightEvalBarEvalCp`/`rightEvalBarEvalMate`/`rightEvalBarDepth` on `!engineEnabled` first (forcing `null`/`null`/`0`, which `EvalBar`'s `computeWhiteFraction` reads as the neutral 0.5 midpoint), falling through to the existing `flawChessEnabled ? topLine... : gameOverlay...` logic only when the Stockfish switch is ON. Preserves both-on (FlawChess objective eval) and FlawChess-off (gameOverlay eval) behavior exactly.

### WR-04: `bestSan`/`engineTopLines` silently go empty in the default state

**Files modified:** `frontend/src/pages/Analysis.tsx`
**Commit:** `776fb5f4`
**Applied fix:** Both derivations now branch on `flawChessEnabled`: when true, `bestSan` reads `flawChessEngine.rankedLines[0]?.rootMove` (a UCI string, same shape `bestSanFromPv` already expects) and `engineTopLines` maps the top 2 `rankedLines` to `{ san, evalCp: objectiveEvalCp, evalMate: null }` (RankedLine has no mate field). When `flawChessEnabled` is false, both fall back to the original `engine.pvLines`-based logic unchanged.

## Skipped Issues

None — all 5 in-scope findings were fixed.

## Verification

- `npx tsc -b`: clean (zero errors), both incrementally after each commit and on final HEAD.
- `npm run lint`: clean.
- `npm test -- --run`: 127 test files / 1523 tests passed (includes the new CR-01 regression test and the pre-existing `useFlawChessEngine.test.ts` throttle/abort tests, unmodified and still green).
- `npm run knip`: clean, exit 0.

All four fixes were applied and verified inside an isolated git worktree (`/tmp/sv-155-reviewfix-*`, branch `gsd-reviewfix/155-*`), then fast-forwarded onto `gsd/phase-155-react-hook-anytime-ui-free-analysis` and the worktree/temp branch were cleaned up transactionally.

---

_Fixed: 2026-07-06T19:11:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
