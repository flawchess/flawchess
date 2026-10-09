---
phase: 228-settings-page
plan: 02
subsystem: ui
tags: [react, engine-lines, settings, theme, train, analysis]

requires:
  - phase: 228-settings-page
    provides: "useEngineDisplaySettings(), LineCount/ArrowCount, DEFAULT_LINES, SETTINGS_STORAGE_KEYS from @/lib/engineSettings (Plan 01)"
provides:
  - "maxLines prop on EngineLines and FlawChessEngineLines; rows-driven EngineLinesSkeleton; engineLinesMinHeightPx helper"
  - "fcLineCount / sfRankCount options on useAnalysisEngineLines (no store read inside the hook)"
  - "Per-engine theme tokens STOCKFISH_SECONDARY_LINE, FLAWCHESS_SECONDARY_LINE, FLAWCHESS_ENGINE_BADGE_PRIMARY"
  - "Train free-play card rows and skeleton follow the Stockfish lines setting"
affects: [228-03, useAnalysisBoardArrows, useStockfishEngine, useTrainFreePlay]

actuals:
  tokens: 21000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Counts enter presentational cards only as props; Analysis.tsx and TrainReveal read the store once"
    - "Per-count heights via inline style minHeight (engineLinesMinHeightPx), never interpolated Tailwind arbitrary classes"
    - "Solid primary + one translucent color per engine for every non-primary line"

key-files:
  created: []
  modified:
    - frontend/src/hooks/analysis/useAnalysisEngineLines.ts
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
    - frontend/src/components/analysis/AnalysisTabs.tsx
    - frontend/src/components/analysis/AnalysisDesktopCards.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/hooks/useGameOverlay.ts

key-decisions:
  - "Heights: ENGINE_LINE_ROW_PX = 30 desktop, 25 compact, so 2 rows still equal 60px / 50px; Stockfish card body adds STOCKFISH_CARD_BODY_CHROME_PX = 18, keeping today's 78px at the default"
  - "Badge alpha for non-primary lines starts at the plan's 0.45 for both engines (rgba of the primary's RGB); UAT tuning is Plan 03 Task 3 in the browser"
  - "FlawChess primary badge keeps today's rank-1 oklch(0.47 0.13 80) so white-text contrast is unchanged"

patterns-established:
  - "Non-primary engine lines: one translucent token per engine, white badge text, no eval-proportional alpha"

requirements-completed: [D-05, D-13, D-16]

coverage:
  - id: D1
    description: "FC reconciled lines, FC grading-union slice and SF reconciled ranking depth follow fcLineCount / sfRankCount; verdict lookup stays unsliced"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/analysis/__tests__/useAnalysisEngineLines.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cards render maxLines rows and maxLines-row skeletons; defaults keep 60/50/78px; FC card shows fewer rows when fewer candidates exist"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/EngineLines.test.tsx, FlawChessEngineLines.test.tsx, EngineUnsupportedNotice.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Train free play: Stockfish lines setting sets skeleton and rendered rows"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "Badge styling lock: solid primary, one translucent per engine for later lines, white text; retired tokens and dead second-best arrow gone"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/EngineLines.test.tsx, FlawChessEngineLines.test.tsx, frontend/src/hooks/__tests__/useGameOverlay.test.ts"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-03
status: complete
plan_head_before: 75dda6ccc9a39a534f8490c5c4b68a48c7fdc32c
plan_head_after: 8bfc4d09e4a988273d841a201f0d078f68815858
---

# Phase 228 Plan 02: Engine Cards Follow the Line Settings Summary

**Both engine cards on /analysis (desktop, mid, mobile Eval tab) and the Train free-play Stockfish card render the chosen 1-5 lines with matching N-row skeletons, with solid primary badges and one translucent color per engine for later lines.**

## Accomplishments

- `useAnalysisEngineLines` takes `fcLineCount` and `sfRankCount` options (pure transform, no store read). `flawChessRankedLinesForVerdict` stays unsliced. `Analysis.tsx` calls `useEngineDisplaySettings()` once, slices `flawChessDisplayedSans` to `fcLines` (so the FC contribution to the grading union follows the setting) and passes `sfLines` as `sfRankCount`. The `extraRootMoves` injection effect is untouched (still pvLines[0]/[1] only).
- `EngineLines` and `FlawChessEngineLines` take a required `maxLines`; both exported two-line caps (`MAX_LINES`) and the three min-height class constants are gone. `engineLinesMinHeightPx(rows, compact)` drives container heights as inline styles; `EngineLinesSkeleton` takes `rows: number`. `FlawChessCard` (`fcLines`), `MobileEngineLines` and `StockfishCard` (`sfLines`) thread the counts, and `TrainReveal` reads `sfLines` for rows and skeleton (D-13). No mobile cap (D-16). No settings shortcut in any card (D-05).
- Theme: added `STOCKFISH_SECONDARY_LINE`, `FLAWCHESS_SECONDARY_LINE` (alpha 0.45 of each primary RGB) and `FLAWCHESS_ENGINE_BADGE_PRIMARY`; deleted `FLAWCHESS_ENGINE_BADGE_SHADES`, `SECOND_BEST_ARROW`, `SECOND_BEST_BADGE_TEXT`. Badge text is white on every row (the dark-ink override is gone).
- `useGameOverlay`: removed the dead second-best arrow block and its token import.

## Task Commits

1. **Task 1: reconciled FC lines, SF ranking depth, grading-union slice follow settings** - `11d43a99a`
2. **Task 2: N-row cards and skeletons at every breakpoint, Train free play** - `5faaeac5b`
3. **Task 3: solid primary / translucent secondary badges, retire rank shades and second-best tokens** - `8bfc4d09e`

The measured `commits: 4` in the frontmatter includes `639aed1ae` (a `chore(reports)` commit by another session in the shared checkout, not part of this plan). This plan's own commits are the three above.

## Deviations from Plan

None to behavior. Notes:

- Reworded one comment in `AnalysisDesktopCards.tsx` so the plan's `min-h-[78px]` acceptance grep prints nothing.
- Updated one stale comment in `Analysis.test.tsx` (named the removed `FC_MAX_LINES`).
- Mutation check: forcing line-1 colors for every row made the new Stockfish and FlawChess badge tests fail; restored.

## Verification

From `frontend/`: `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm run knip` clean, `npm test -- --run` 4615 tests passed. Plan greps: no `MAX_LINES` / `FC_MAX_LINES` / `SF_MAX_LINES` outside tests, no `min-h-[78px]`/`min-h-[90px]` in `components/analysis`, no retired token names anywhere in `src`, no `SettingsSheetButton` or `/settings` link under `components/analysis`.

## UAT hand-off (Plan 03 / orchestrator, browser needed)

- Badge alpha 0.45 on both engines is the plan's starting value, untuned. Check white-text legibility on the translucent fills and that the badge still reads against the dark card (ChessBoard separately multiplies engine arrows by 0.75).
- Check card heights at the default (should be pixel-identical: 60px / 50px compact / 78px Stockfish card body) and at 5 lines (150px / 125px compact, no jump between skeleton and rows).
- Train free play still requests the old MultiPV, so more than 2 rows only appear once Plan 03 makes MultiPV a function of the setting.

## Known Stubs

None.

## Threat Flags

None. T-228-04 holds: counts reach the cards only as validated `LineCount` values and `slice()` bounds rendering.

## Follow-ups (not done, out of scope)

- `useGameOverlay`'s whole `boardArrows` field is unused by its only caller (Analysis.tsx never reads it); retiring the field is a separate cleanup.
- A shared checkout hazard surfaced: a foreign `chore(reports)` commit and an unrelated modified `../../seeds/closed/SEED-185-weekly-train-leaderboards.md` appeared during the run; neither was touched or staged.

## Self-Check: PASSED

Commits `11d43a99a`, `5faaeac5b`, `8bfc4d09e` are in `git log`; all key-files exist.
