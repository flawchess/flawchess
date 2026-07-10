---
phase: 155-react-hook-anytime-ui-free-analysis
plan: 04
subsystem: ui
tags: [react, typescript, vitest, mcts, stockfish, maia, analysis-page]

# Dependency graph
requires:
  - phase: 155-01
    provides: "Switch primitive, expectedScoreToWhitePovCp, FLAWCHESS_ENGINE_ACCENT/FLAWCHESS_ENGINE_HEADLINE_ACCENT theme tokens"
  - phase: 155-02
    provides: "useFlawChessEngine({ fen, enabled, elo }) — the anytime-emit hook mounted this plan"
  - phase: 155-03
    provides: "FlawChessEngineLines body component — the card content wired this plan"
provides:
  - "FlawChess Engine surfaced live on /analysis: card above Maia in both desktop column and mobile Human tab, on-by-default"
  - "Three independent header Switches (Stockfish/Maia/FlawChess) replacing the single icon-button toggle, all default ON"
  - "Left eval-bar FC>Maia precedence + right SF bar objective-eval handoff (POOL-04 mutual exclusion)"
affects: [156-board-arrows-toggles, 157-game-review-overlay]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared EngineToggleHeader helper (Switch + accent caption) factoring the near-identical header markup across all 3 engine cards, instead of tripling inline JSX (155-RESEARCH.md Pitfall 5)"
    - "Switch checked-track accent set via inline style={{backgroundColor}} override (wins over the primitive's default data-[state=checked]:bg-primary class) rather than a CSS custom property"
    - "Eval-bar source precedence (left slot FC>Maia, right slot SF-vs-FC-objective) extracted into a small derived-value block above the JSX, not inlined in conditionals"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/components/analysis/MaiaHumanPanel.tsx

key-decisions:
  - "Combined Task 1 (toggle refactor + gating) and Task 2 (card placement + eval-bar precedence) into a single commit: topLine/flawChessEngine's mount output is inert until Task 2's eval-bar wiring consumes it, so a Task-1-only commit would fail its own `tsc --noEmit` gate under noUnusedLocals (an unused local). Both were implemented and verified together instead."
  - "Expanded files_modified beyond the plan's stated Analysis.tsx-only scope to include MaiaHumanPanel.tsx — the Maia card's header is rendered inside that separate component, not inlined in Analysis.tsx, so 'retrofit the Maia card header' (Task 1's explicit instruction) required editing it. Added optional `enabled`/`onToggleEnabled` props; omitting both (as the pre-155 unit tests do) reproduces the exact prior header/no-header behavior byte-for-byte, keeping the locked 151.1 'compact drops the header' test green."
  - "Maia's header Switch renders even in `compact` (mobile) mode when the toggle props are supplied — a minimal switch-only row (no title/icon), not the full header — so the toggle stays reachable on mobile (D-03 mobile parity) without reintroducing the full title row's height that the 151.1 UAT deliberately removed."
  - "FlawChess Engine card's own root testid stays FlawChessEngineLines.tsx's pre-existing `analysis-flawchess-card` (Plan 03); the NEW wrapping Card in Analysis.tsx uses a distinct `analysis-flawchess-panel` testid to avoid a duplicate-testid collision (mirrors the existing analysis-engine-card/analysis-engine-lines outer/inner naming split)."
  - "engineLoading's guard gained `&& !flawChessEnabled` (Rule 1 bug fix): without it, the Stockfish card's loading skeleton spins forever once the FlawChess Engine suppresses the standalone search — both switches default ON, so this was an immediate, always-visible regression from the Task 1 gating change, not a latent edge case."
  - "No isError/'FlawChess Engine unavailable' state wired: the Plan 02 hook (frozen/out-of-scope this plan) exposes no error field — createWorkerPool/createMaiaQueue resolve failures to empty results rather than surfacing an error (per 154-02's own decision log). Fabricating a synthetic error signal from Analysis.tsx alone would be dishonest; documented as a known gap rather than a fake gate."
  - "EvalBar.tsx's generic aria-label ('Maia expected score: X%') is unchanged and technically reads as 'Maia' even when the FC source is active — EvalBar.tsx is not in this plan's file scope and fixing it isn't required by any task's acceptance criteria; left as a known minor cosmetic gap."

requirements-completed: [DISPLAY-01, DISPLAY-04]

coverage:
  - id: D1
    description: "FlawChess Engine card renders above the Maia panel by default in both the desktop human column and the mobile Human tab, on-by-default (D-01, DISPLAY-04)"
    requirement: "DISPLAY-04"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#FlawChess Engine eval-bar precedence (Phase 155) > renders the FlawChess card above the Maia panel by default (D-01)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Three independent header Switches (Stockfish/Maia/FlawChess), each accent-tinted, all default ON, each with data-testid + aria-label; Maia switch gates useMaiaEngine + useStockfishGradingEngine only, FlawChess hook independent of it"
    requirement: "DISPLAY-04"
    verification:
      - kind: unit
        ref: "npx tsc -b --noEmit (type-clean gating wiring) + frontend/src/pages/__tests__/Analysis.test.tsx (toggle click drives btn-analysis-flawchess-toggle in 3 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Left eval bar shows FC (brown, cap 'FC') with precedence over Maia (violet) when FlawChess Engine is enabled, falls back to Maia when only Maia is on (D-04)"
    requirement: "DISPLAY-04"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#FlawChess Engine eval-bar precedence (Phase 155) > shows the FlawChess eval bar ... / falls back to the Maia eval bar ..."
        status: pass
    human_judgment: false
  - id: D4
    description: "Right SF eval bar is fed the FlawChess Engine's top line objectiveEvalCp while it runs, honoring POOL-04 mutual exclusion (useStockfishEngine suppressed via engineEnabled && !flawChessEnabled)"
    requirement: "DISPLAY-01"
    verification:
      - kind: unit
        ref: "npx tsc -b --noEmit (rightEvalBarEvalCp/rightEvalBarEvalMate/rightEvalBarDepth derivation) + frontend/src/pages/__tests__/Analysis.test.tsx#shows engine-loading chrome while isReady=false ... (exercises the FC-off path where the standalone search resumes)"
        status: pass
    human_judgment: false
  - id: D5
    description: "SC4 real-device mobile-memory UAT (on-by-default gate, deferred from Phase 154) and the two research-decision confirmations (D-04 handoff reads correctly on-device; shared selectedElo acceptable) — perceptual/device behavior, not unit-testable"
    verification: []
    human_judgment: true
    rationale: "Real-device memory behavior and perceptual smoothness cannot be exercised in jsdom; this is the explicit HUMAN-UAT gate the plan's own verification section defers to /gsd-verify-work."

# Metrics
duration: 55min
completed: 2026-07-06
status: complete
---

# Phase 155 Plan 04: Analysis.tsx Integration (FlawChess Engine Live on /analysis) Summary

**Mounted `useFlawChessEngine` on `/analysis`, placed the `FlawChessEngineLines` card above Maia in both desktop and mobile layouts, replaced the single Stockfish toggle with three independent accent-tinted header Switches, and wired the D-04 eval-bar precedence (FC>Maia left, objective-eval handoff right) — the FlawChess Engine is now visible and live on the free-analysis board.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 (Tasks 1+2 committed together; see Deviations)
- **Files modified:** 3 (Analysis.tsx, Analysis.test.tsx, MaiaHumanPanel.tsx)

## Accomplishments

- `useFlawChessEngine({ fen, enabled: flawChessEnabled, elo: selectedElo })` mounted unconditionally; `topLine = rankedLines[0]` derived and narrowed (no `!` assertions) for the eval-bar precedence block
- `FlawChessEngineLines` wrapped in a `Card` + `CardHeader` (new switch) + `CardBody` (loading/off/lines states mirroring the Stockfish card's own pattern), stacked directly above `MaiaHumanPanel` in BOTH the desktop `analysis-human-column` and the mobile "Human" tab via one shared `flawChessCard` JSX const
- Three header `Switch`es via a new shared `EngineToggleHeader` helper: Stockfish (`btn-analysis-engine-toggle`, upgraded from an icon-`Button`), Maia (`btn-analysis-maia-toggle`, now inside `MaiaHumanPanel.tsx`), FlawChess (`btn-analysis-flawchess-toggle`) — all default ON, each accent-tinted (blue/violet/brown) via an inline `style={{backgroundColor}}` override on the checked track
- Gating wiring: `useStockfishEngine`'s effective `enabled` becomes `engineEnabled && !flawChessEnabled` (POOL-04 mutual exclusion, D-04/Open Question 1); `useMaiaEngine` + `useStockfishGradingEngine` gated on `maiaEnabled` (not `engineEnabled`); the FlawChess Engine's own hook is independent of both
- Left eval bar: conditional `whiteFraction`/`accentColor`/`testId` — FC (brown, `analysis-flawchess-eval-bar`) when enabled, else Maia (violet, `analysis-maia-eval-bar`) — `fcWhiteFraction` derived via the same root-STM→white-POV inversion as the existing Maia bar
- Right eval bar: `evalCp`/`evalMate`/`depth` swap to the FlawChess Engine's `topLine.objectiveEvalCp` (mate always `null`, depth `0`) while it runs, else the existing `gameOverlay` values — cap stays `'SF'`/`STOCKFISH_ACCENT`, only the data source changes
- `evalBarCap`'s type extended to `'Maia' | 'SF' | 'FC'`; `boardHeaderRow`'s left cap becomes `flawChessEnabled ? 'FC' : 'Maia'`, matching the existing `text-xs` precedent (no new `text-sm` cap introduced)
- Rule 1 bug fix: `engineLoading` gained a `&& !flawChessEnabled` guard — without it the Stockfish card's loading skeleton would spin forever once FlawChess suppresses the standalone search (both default ON)

## Task Commits

Tasks 1 and 2 were committed together (see Deviations for why); Task 3 separately:

1. **Tasks 1+2: Three-toggle Switch refactor + engine-gating, card placement + eval-bar precedence** - `adb80aa9` (feat)
2. **Task 3: Extend Analysis.test.tsx with FC-precedence cases + phase gate** - `1b6ce587` (test)

## Files Created/Modified

- `frontend/src/pages/Analysis.tsx` - Mounted `useFlawChessEngine`; added `EngineToggleHeader` shared helper; `maiaEnabled`/`flawChessEnabled` state; 3-switch header refactor; `flawChessCard` shared JSX const placed in both layouts; eval-bar precedence derivation + JSX wiring; `evalBarCap`/`boardHeaderRow` extended for `'FC'`; `engineLoading`/`flawChessLoading` derived values
- `frontend/src/pages/__tests__/Analysis.test.tsx` - New `useFlawChessEngine` mock; new `describe('FlawChess Engine eval-bar precedence (Phase 155)')` (3 tests); updated 4 pre-existing tests for the new FC-on-by-default precedence
- `frontend/src/components/analysis/MaiaHumanPanel.tsx` - New optional `enabled`/`onToggleEnabled` props rendering the Maia header Switch (full header on desktop, minimal switch-only row on mobile/compact when supplied); no-op when omitted (preserves the locked 151.1 test)

## Decisions Made

See `key-decisions` in frontmatter — summarized: (1) Tasks 1+2 committed together (type-checking dependency between them); (2) `MaiaHumanPanel.tsx` added to files_modified since the Maia header lives there, not in `Analysis.tsx`; (3) Maia's mobile switch renders as a minimal row, not the full header; (4) FlawChess card wrapper uses a distinct `analysis-flawchess-panel` testid to avoid colliding with `FlawChessEngineLines`' own pre-existing `analysis-flawchess-card` testid; (5) `engineLoading` Rule 1 fix; (6) no fabricated error state (hook exposes none); (7) `EvalBar.tsx`'s generic aria-label left unchanged (out of file scope).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stockfish card's loading skeleton would spin forever once FlawChess suppresses the standalone search**
- **Found during:** Task 1 (Stockfish-switch gating)
- **Issue:** `engineLoading = engineEnabled && !engine.isReady` never becomes false once `useStockfishEngine`'s effective `enabled` is suppressed by `flawChessEnabled` (both switches default ON) — `engine.isReady` never becomes `true` because the worker is never created, so the loading skeleton would render indefinitely instead of falling through to the (empty) engine-lines body.
- **Fix:** Added `&& !flawChessEnabled` to the guard: `engineLoading = engineEnabled && !flawChessEnabled && !engine.isReady`.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** New test "shows engine-loading chrome while isReady=false" toggles FlawChess off first and asserts the skeleton then appears; full suite green.
- **Committed in:** `adb80aa9`

**2. [Scope note, not a Rule violation] Expanded files_modified to include `MaiaHumanPanel.tsx`**
- **Found during:** Task 1 (retrofit the Maia card header)
- **Issue:** The plan's frontmatter `files_modified` lists only `Analysis.tsx` + its test file, but Task 1's action text explicitly instructs retrofitting "the Maia card header" with a Switch — that header is rendered inside `MaiaHumanPanel.tsx`, a separate component, not inlined in `Analysis.tsx`.
- **Fix:** Added optional `enabled`/`onToggleEnabled` props to `MaiaHumanPanelProps`, rendering the Switch only when both are supplied (Analysis.tsx always supplies them; the pre-155 unit tests do not, so their locked assertions — including "compact mode drops the header" — stay green unchanged).
- **Files modified:** `frontend/src/components/analysis/MaiaHumanPanel.tsx`
- **Verification:** `MaiaHumanPanel.test.tsx` (4/4 tests, unchanged) + full suite green.
- **Committed in:** `adb80aa9`

**3. [Combining rule, documented above] Tasks 1 and 2 committed together instead of separately**
- **Found during:** Planning the commit sequence after both tasks were implemented and verified
- **Issue:** Task 1's own acceptance criteria requires deriving `topLine = rankedLines[0]` from the newly-mounted hook, but nothing in Task 1's scope consumes `topLine` — only Task 2's eval-bar wiring does. A Task-1-only commit would leave `topLine` (and effectively `flawChessEngine`) unused, failing Task 1's own `npx tsc -b --noEmit` verify command under `noUnusedLocals: true`.
- **Fix:** Implemented and verified both tasks together, then committed as one unit; documented the reasoning in the commit message and here rather than fabricating dead-code placeholders to force an artificial intermediate commit.
- **Files modified:** `frontend/src/pages/Analysis.tsx`, `frontend/src/components/analysis/MaiaHumanPanel.tsx`
- **Verification:** `npx tsc -b --noEmit`, `npm run lint`, full suite, `npm run knip` — all clean after the combined commit.
- **Committed in:** `adb80aa9`

---

**Total deviations:** 3 (1 auto-fixed bug, 2 scope/sequencing notes)
**Impact on plan:** The bug fix was necessary for correct behavior of the plan's own gating change. The scope expansion (MaiaHumanPanel.tsx) was required to literally satisfy Task 1's explicit instruction and is minimal (additive, backward-compatible props). The commit-combining is a pragmatic sequencing choice with no functional impact — all acceptance criteria for both tasks are met and verified.

## Known Gaps (not fixed — out of scope)

- **No `isError`/"FlawChess Engine unavailable" state.** The Copywriting Contract prescribes this copy for a worker-init failure, but the Plan 02 `useFlawChessEngine` hook (frozen this plan) exposes no error field — `createWorkerPool`/`createMaiaQueue` resolve failures to empty results internally rather than surfacing them (154-02's own decision). Implementing this would require modifying Plan 02's hook, which is explicitly out of scope ("Any change to ... the hook ... owned by Plans 02/03"). Documented rather than fabricated.
- **`EvalBar.tsx`'s aria-label stays generic** ("Maia expected score: X%") even when the FC source drives the left bar's `whiteFraction` override — the label doesn't distinguish which source is active. `EvalBar.tsx` is not in this plan's file scope and no task's acceptance criteria requires touching it; a minor cosmetic/accessibility nit, not a functional bug.

## Issues Encountered

None beyond the items already covered under Deviations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full frontend suite green: 127 test files / 1522 tests; `npx tsc -b --noEmit`, `npm run lint`, `npm run knip` all clean
- DISPLAY-01 and DISPLAY-04 both close here: DISPLAY-01's Plan 02/04 split completes with the engine now actually mounted and visible; DISPLAY-04 (this plan's own requirement) is fully delivered — card placement, 3-toggle refactor, and eval-bar precedence are all live on `/analysis`
- **Phase 155 is now feature-complete** for the "React hook + anytime UI" milestone slice. Remaining verification is entirely human-in-the-loop, already flagged in the plan's own `<verification>` section:
  - **SC4 (deferred from Phase 154):** real-device mobile-memory UAT with all 3 engines on-by-default — the gate for whether the device-adaptive fallback (on desktop / off mobile) is needed
  - **Decision confirmation UAT:** the D-04 handoff (Stockfish suppression + SF-bar objective-eval swap) and the shared-`selectedElo` acceptance, both reading correctly on-device
  - **Perceptual UAT:** live-refine smoothness at the 150ms cadence, desktop + mobile
- Phase 156 (board arrows + toggles) and Phase 157 (game-review overlay) can build on this plan's `flawChessEnabled`/`maiaEnabled`/`engineEnabled` state and the `topLine`/`flawChessEngine.rankedLines` data already flowing through `Analysis.tsx`

---
*Phase: 155-react-hook-anytime-ui-free-analysis*
*Completed: 2026-07-06*

## Self-Check: PASSED

All 3 modified files verified present on disk; both commit hashes (adb80aa9, 1b6ce587) verified present in git log.
