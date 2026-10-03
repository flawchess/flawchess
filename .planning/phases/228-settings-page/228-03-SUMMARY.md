---
phase: 228-settings-page
plan: 03
subsystem: ui
tags: [react, stockfish, multipv, arrows, analysis, train, settings]

requires:
  - phase: 228-settings-page
    provides: "useEngineDisplaySettings / SETTINGS_STORAGE_KEYS (Plan 01); fcLineCount / sfRankCount options and STOCKFISH_SECONDARY_LINE / FLAWCHESS_SECONDARY_LINE tokens (Plan 02)"
provides:
  - "useStockfishEngine takes a required multiPv option; setoption is resent only while idle; a change re-searches live with no worker restart"
  - "/analysis: free-run MultiPV = max(2, SF lines, SF arrows); every free-run root joins the grading union; sfRankCount = max(lines, arrows)"
  - "useAnalysisBoardArrows draws 0-3 arrows per engine from the same reconciled ranking as the cards (solid primary, one translucent color for ranks 2..N, engine width, primary painted last)"
  - "Train free play: MultiPV = max(SF lines, SF arrows); live arrows follow the SF arrows setting (0 draws none); reveal legend arrows untouched; eval-bar engine pinned to MultiPV 1"
  - "CHANGELOG [Unreleased] Added/Changed bullets for the phase"
affects: [phase-228 verification, useStockfishEngine callers, Train free play, Analysis board arrows]

actuals:
  tokens: 19600
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Idle-only UCI option change: setoption sent only from analyze()'s idle branch (appliedMultiPvRef vs multiPvRef); a change while thinking stops first and the stale-bestmove handler re-enters idle"
    - "multiPv never enters the worker-lifecycle effect deps (no WASM re-instantiation)"
    - "Per-engine arrow style table + pushEngineArrows helper: ranks pushed N-1..0 so the primary paints on top within its width tier"

key-files:
  created:
    - frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts
  modified:
    - frontend/src/hooks/useStockfishEngine.ts
    - frontend/src/hooks/__tests__/useStockfishEngine.test.ts
    - frontend/src/hooks/useTrainFreePlay.ts
    - frontend/src/hooks/__tests__/useTrainFreePlay.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/hooks/analysis/useAnalysisBoardArrows.ts
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - CHANGELOG.md

key-decisions:
  - "Free-run MultiPV floor ANALYSIS_FREE_RUN_MIN_MULTIPV = 2 keeps engine.pvLines[1] for the FlawChess second-move injection at every setting; extraRootMoves untouched"
  - "Train eval bar pinned at TRAIN_EVAL_BAR_MULTIPV = 1, independent of the settings (D-12)"
  - "Train free play searches at max(SF lines, SF arrows) at the fixed 1500 ms movetime, no movetime scaling (D-11)"
  - "reconciledBestUci dropped from Analysis.tsx's destructure (arrows now read reconciledPvLines); the hook result field stays, still covered by its own tests"

patterns-established:
  - "Arrow rank k reads ranking line k of the same list that feeds the card, so arrows and card rows can never disagree"

requirements-completed: [D-06, D-11, D-12, D-13, D-14, D-15]

coverage:
  - id: D1
    description: "useStockfishEngine multiPv: setoption at uciok before isready; idle change sends setoption then position then go; thinking change sends stop only, setoption after the stale bestmove; same value sends nothing; one Worker across changes; no early setoption before uciok"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStockfishEngine.test.ts#multiPv option changes (D-06, D-12)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Callers state their MultiPV: Train free play 2 / 4 / 3 / 1 per D-11; Analysis free run 2 / 2 / 4 / 3; eval bar pinned to 1"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainFreePlay.test.ts, frontend/src/pages/__tests__/Analysis.test.tsx#Settings drive search breadth"
        status: pass
    human_judgment: false
  - id: D3
    description: "/analysis arrows: N distinct moves in card order, solid primary + translucent ranks, engine widths, primary last, 0 hides arrows while the card stays, full free-run grading union, SF card reaches 5 rows with Maia and FlawChess off"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts, frontend/src/pages/__tests__/Analysis.test.tsx#Settings drive search breadth"
        status: pass
    human_judgment: false
  - id: D4
    description: "Train free-play live arrows follow the SF arrows setting; reveal legend arrows and stepper arrow unchanged (tested at SF arrows 0)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainArrows.test.ts, frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx"
        status: pass
    human_judgment: false
  - id: D5
    description: "Translucent badge/arrow alpha legibility, card heights, live re-search with real Stockfish WASM, mobile sheets, entry points"
    verification: []
    human_judgment: true
    rationale: "Browser UAT (VALIDATION.md Manual-Only): run by the orchestrator via Chrome automation, all 5 legs passed"

duration: 13min
completed: 2026-10-03
status: complete
plan_head_before: f10253cb9624ef9baff9860e2f4c632b73b08b41
plan_head_after: 84e12427d78f093929873f1bb3714f7231fd9130
---

# Phase 228 Plan 03: Per-Engine Search Breadth and Board Arrows Summary

**useStockfishEngine now takes a live, restart-free MultiPV option; /analysis draws 0-3 arrows per engine from the same reconciled ranking as the cards (solid primary, one translucent color for ranks 2..N), and Train free play searches at max(lines, arrows) with its live arrows following the setting while the reveal legend stays intact.**

## Performance

- **Duration:** about 13 min
- **Tasks:** 3 of 3 code tasks done; the browser UAT legs are deferred to the orchestrator (no browser tools in this executor)
- **Files:** 1 created, 12 modified

## Accomplishments

- **useStockfishEngine (D-06, D-12):** the module constant is gone; `multiPv` is a required option. `multiPvRef` (latest wanted) and `appliedMultiPvRef` (last sent to this worker, reset on teardown). `uciok` sends the current value before `isready` (155-UAT ordering kept); `analyze()` resends it only from the idle branch, never from thinking/stopping (FLAWCHESS-7V). A `[multiPv, analyze]` effect re-searches the current position on a change: from idle it searches at once, from thinking it stops and the stale-bestmove handler re-enters idle. The worker-lifecycle deps are still `[enabled, clearPendingPvCommit]`.
- **Callers:** Analysis free run `Math.max(ANALYSIS_FREE_RUN_MIN_MULTIPV, sfLines, sfArrows)` (floor 2 keeps `pvLines[1]` for the injection); Train free play `Math.max(sfLines, sfArrows)`; Train eval bar `TRAIN_EVAL_BAR_MULTIPV = 1`.
- **/analysis arrows (D-14, D-15):** `useAnalysisBoardArrows` replaced `enginePvLines` / `reconciledBestUci` with `stockfishArrowLines` (= `reconciledPvLines`, the card's list), `fcArrowCount`, `sfArrowCount`. A small `pushEngineArrows` helper plus two style records push ranks N-1..0, so rank k names its own move (the old shape repeated the argmax), the primary paints last, and widths stay per engine (FC 1.0, SF 0.5). `unionSans` now adds every free-run root SAN (still `Array.from(new Set(...)).sort()` for a stable key); `sfRankCount = Math.max(sfLines, sfArrows)`.
- **Train free play (D-11, D-13):** `buildTrainFreePlayArrows(pvLines, count)` mirrors the same shape (rank 0 `TRAIN_BEST_MOVE_ARROW`, others `STOCKFISH_SECONDARY_LINE`, layer keys `free-i`). `TrainSolveScreen` reads `sfArrows` and memoizes on `[freePlay.pvLines, sfArrows]`; `NO_PV_LINES` keeps the not-yet-current branch identity-stable. `buildTrainStepArrows` and the reveal/legend builders are untouched (diff hunks start after them).
- **CHANGELOG:** one Added bullet (settings page, sound, lines 1-5, arrows 0-3, in-place mobile sheets) and one Changed bullet (translucent non-primary lines).

## Task Commits

1. **Task 1 RED: multiPv option tests** - `b548673f6`
2. **Task 1 GREEN: multiPv option, live re-search, three callers** - `99779c3b4`
3. **Task 2: arrows 1..N from the reconciled ranking, grading union** - `6f8717f9b`
4. **Task 3: Train free-play arrows follow the setting, CHANGELOG** - `84e12427d`

## Mutation proof (Task 2, D-14)

With every Stockfish iteration forced to read `stockfishArrowLines[0]` (the old repeat-the-argmax shape), `useAnalysisBoardArrows.test.ts` failed exactly the three-arrow case ("sfArrowCount 3 draws three DISTINCT moves, rank k reading line k"); 1 failed, 8 passed. After restoring the file, all 9 passed again.

## Deviations from Plan

None to behavior. Notes:

- **TDD shape:** Task 1's hook cases and Task 2's arrows-hook cases were observed RED before implementation (hook RED committed separately as `b548673f6`). The Train D-11 caller cases (`useTrainFreePlay.test.ts`) and the Analysis page-level cases were written after the corresponding wiring, so they were not observed RED in isolation; the Analysis page cases did fail while the hook options were mid-rewrite, which is as close as that shape allows.
- **[Rule 3 - Blocking] `reconciledBestUci` unused in Analysis.tsx.** After the arrows hook stopped consuming it, eslint and tsc flagged the destructured value. Removed it from the destructure; `useAnalysisEngineLines` still returns it and its own tests still cover it.
- **Added a Train screen test** (`TrainSolveScreen.test.tsx`): at SF arrows 0, free play draws no live arrow while the pristine reveal still draws its legend arrows and restores them after Solution. This is the executable proof of the D-13 prohibition (the plan marked it `test`).
- Updated the stale comment near `Analysis.tsx` line 224 (it named the deleted arrow-count constant). The comment near `Analysis.test.tsx` ~2679 had already been reworded by Plan 02.

## Verification (from `frontend/`)

- `npm run lint` clean (including max-depth), `npm run build` (tsc -b + vite) clean, `npm test -- --run` 4646 tests passed, `npm run knip` exit 0.
- Acceptance greps: no `^const MULTIPV`; `multiPv: Math.max(ANALYSIS_FREE_RUN_MIN_MULTIPV, sfLines, sfArrows)` x1; `multiPv: TRAIN_EVAL_BAR_MULTIPV` x1; `Math.max(sfLines, sfArrows)` in `useTrainFreePlay.ts` x1; worker effect deps still `[enabled, clearPendingPvCommit]`; no `ARROW_COUNT` outside tests; no `enginePvLines|reconciledBestUci` in the arrows hook; `stockfishArrowLines: reconciledPvLines` x1; `sfRankCount: Math.max(sfLines, sfArrows)` x1; `buildTrainFreePlayArrows(pvLines` signature x1; `buildTrainFreePlayArrows(freePlay.pvLines, sfArrows)` x1; CHANGELOG `[Unreleased]` mentions settings.
- Backend half of the pre-merge gate is not part of this plan (frontend-only); it runs once before the squash-merge.

## Browser UAT legs (VALIDATION.md Manual-Only): run by the orchestrator 2026-10-03, all PASSED

Run via claude-in-chrome against the dev build (Vite :5173, desktop window 1594px; 375x667 same-origin iframe for mobile). Settings legs on the owner dev account (localhost); bot-game and Train legs on a guest session (127.0.0.1 origin) so the owner's saved bot game and Train state stayed untouched. Screenshots in `temp/228-uat/`.

1. **Desktop /analysis: PASSED.** At FC 5/3 and SF 5/3 on an Italian middlegame (FEN seed): FC card 5 rows, SF card 5 rows, both line blocks 150px. Arrow overlay: 3 gold (1 solid `rgb(213,152,0)` + 2 `rgba(213,152,0,0.45)`) and 3 blue (1 solid `rgba(37,99,235,0.8)` + 2 `rgba(37,99,235,0.45)`), primary drawn last in each set. SF arrows a4/b4/Re1 = SF card rows 1-3. White badge text legible on every translucent fill. FC arrows 0 / SF arrows 2: no gold arrows, FC card still 5 rows, exactly 2 blue arrows. Defaults: 2 rows each, 60px line blocks, SF card 116px from first skeleton paint through filled rows (no jump), 1 arrow per engine.
2. **Mobile 375px /analysis: PASSED.** `btn-analysis-settings` opens the bottom sheet over the board; SF lines 2 to 4, close; Eval tab shows 4 Stockfish rows, path stays `/analysis`, no asset gate. With the sheet open, SF lines 4 to 5 re-searched live to 5 rows (real WASM MultiPV, no reload).
3. **Mobile 375px bot game: PASSED.** Sound on: own move and bot reply each started one AudioBufferSourceNode. Sound off via `btn-bots-settings` sheet (`flawchess_bot_sound_muted` = 1): own move exf4 and the bot reply d4 started zero sources; game continued, path `/bots`, no resume gate.
4. **Train free play: PASSED.** SF 4/2: exploration card 4 rows, board 1 solid + 1 translucent blue arrow. Live changes while exploring (store setter): lines 5 gives 5 rows; arrows 0 removes all arrows while the card stays; arrows 3 gives 3. Back on the reveal with SF arrows 0: legend arrows unchanged (your-move red + best-move blue).
5. **Entries: PASSED.** Guest desktop header cogwheel opens `/settings` (panel rendered, active style applied); mobile More drawer lists `drawer-settings` directly above `drawer-logout`, tapping it opens `/settings`.

Alpha tuning status: 0.45 kept for both engines (legible, translucent ranks clearly distinct from the primary); no theme change needed.

## Known Stubs

None.

## Threat Flags

None. T-228-06/07/08 mitigated: `multiPv` is derived only from validated `LineCount` / `ArrowCount` integers via `Math.max` with fixed floors, setoption is sent only from the idle branch (tested: a thinking engine gets `stop` and no setoption until the stale bestmove), and the Worker constructor is called once across multiPv changes (tested).

## Notes

- The Analysis free run at high settings widens the grading union to a handful of extra moves at the fixed grading time cap (RESEARCH Open Question 2): accepted breadth/depth trade, no mitigation planned.
- A foreign unstaged change (`.planning/seeds/SEED-185-weekly-train-leaderboards.md`) from another session was present throughout and was never staged.

## Self-Check: PASSED

Created file `frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` exists; commits `b548673f6`, `99779c3b4`, `6f8717f9b`, `84e12427d` are in `git log`; full frontend gate green.
