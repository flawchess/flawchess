---
phase: 157-flawchess-agreement-verdict-prose-hoverable-moves
plan: 02
subsystem: ui
tags: [react, typescript, vitest, chess-engine, flawchess-engine, stockfish, analysis-page]

requires:
  - phase: 157-01
    provides: computeFlawChessVerdict classifier + SHARP_DROP_THRESHOLD (frontend/src/lib/flawChessVerdict.ts)
  - phase: 155-156
    provides: FlawChessEngineLines.tsx (shared flawChessCard host), useStockfishEngine's engine.pvLines, useFlawChessEngine's rankedLines, board-arrow overlay plumbing (qualityHoverArrows/setHoveredQualityMoves)
provides:
  - "ProseSpan.tsx — content-agnostic hover-intent + click-to-play interactive move span shell, extracted from MaiaMoveQualityBar's private ProseMoveSpan"
  - "FlawChessAgreementVerdict.tsx — the prose agreement/divergence verdict component consuming Plan 01's classifier"
affects: []

tech-stack:
  added: []
  patterns:
    - "Content-parameterized interaction shell (ProseSpan) shared by two prose-verdict surfaces (Maia + FlawChess) instead of duplicating the hover-intent/click-to-play mechanics"
    - "Single shared JSX variable (flawChessCard) as the mechanism for automatic free-analysis/game-review parity"

key-files:
  created:
    - frontend/src/components/analysis/ProseSpan.tsx
    - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
    - frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx
  modified:
    - frontend/src/components/analysis/MaiaMoveQualityBar.tsx
    - frontend/src/pages/Analysis.tsx

key-decisions:
  - "Extracted ProseSpan (not duplicated) per PATTERNS.md's recommended default; MaiaMoveQualityBar's ProseMoveSpan is now a thin wrapper, all 9 of its pre-existing tests pass unchanged"
  - "Main prose sentence cites each pick's OBJECTIVE eval (verdict.flawChessMove.evalCp / verdict.stockfishMove.evalCp+evalMate) — the same numbers that drive the win%-drop tier split — rather than a practicalScore-derived number, keeping the sentence's cited evals mathematically consistent with the classification. The D-10 popover separately breaks out the FlawChess pick's converted practical-score number labeled '(practical)'"
  - "Aligned tier (D-04) renders exactly ONE ProseSpan (the shared move), built from the FlawChess pick's own span/popover (both engine lines always shown) rather than a separate combined-role span type"
  - "UCI->SAN conversion (uciToSan) is a small local helper using chess.js's Chess(baseFen).move({from,to,promotion}) wrapped in try/catch, mirroring Analysis.tsx's existing playProseMove pattern; an unresolvable SAN on either pick falls back to the same muted slot as D-02/D-03/D-06 rather than partially rendering with a raw UCI string (Pitfall 2)"
  - "D-02/D-03 (Stockfish off) and D-06 (partial/null verdict, or unresolvable SAN) all collapse into the identical fixed-height muted slot with the same testid (flawchess-verdict-prompt) and copy, since all three are 'nothing to narrate yet' states from the caller's perspective"
  - "Verdict inserted as a sibling directly below FlawChessEngineLines, inside the flawChessCard's `!flawChessLine ? ... : (...)` else-branch (only rendered when the FlawChess Engine toggle is on) — when FlawChess is off, rankedLines is empty so the classifier naturally returns null and the muted slot shows, giving the same behavior without a second explicit gate"

requirements-completed: [REVIEW-02]

coverage:
  - id: D1
    description: "Task 1 — ProseSpan extraction keeps all 9 pre-existing MaiaMoveQualityBar tests green (byte-identical testids/aria/behavior)"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx (all 9 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-02/D-03: verdict renders ONLY the fixed-height muted prompt when Stockfish is off; classifier not consulted"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx#shows the muted prompt (not the classifier) when Stockfish is off (D-02/D-03)"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-06: a partial/null verdict snapshot falls back to the same muted slot, never a bogus tier"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx#falls back to the same muted slot on a partial/null verdict (D-06)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-04/D-05/D-07: all three tiers (aligned/safe/sharp) render the correct prose template with named move spans, no bare 'best move' substring"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx (aligned/safe-divergence/sharp-divergence tests)"
        status: pass
      - kind: static
        ref: "grep -in 'best move' frontend/src/components/analysis/FlawChessAgreementVerdict.tsx — empty"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-09: hovering a verdict move span isolates that pick's board-arrow color (amber FlawChess / blue Stockfish), restoring null on leave"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx#isolates the hovered picks board arrow in its tier color, restoring on leave (D-09)"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-10: engine-labeled two-line popover, with the FlawChess line included/omitted correctly for the Stockfish pick based on a rootMove match in flawChessRankedLines"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx (3 D-10 tests: FC-pick both-lines, SF-pick omitted, SF-pick included)"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-11: clicking a span while its popover is open plays the move; the first press only reveals it"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx (2 D-11 tests)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Single insertion site in Analysis.tsx's shared flawChessCard gives free-analysis + game-review parity by construction (SC4/REVIEW-01); sourced from engine.pvLines[0] not engineTopLines"
    requirement: "REVIEW-02"
    verification:
      - kind: static
        ref: "grep -n 'FlawChessAgreementVerdict' frontend/src/pages/Analysis.tsx — exactly 1 import + 1 render call"
        status: pass
      - kind: static
        ref: "grep -n 'engineTopLines' frontend/src/pages/Analysis.tsx — new component not among its consumers"
        status: pass
    human_judgment: true

duration: 40min
completed: 2026-07-07
status: complete
---

# Phase 157 Plan 02: FlawChessAgreementVerdict Prose + Hoverable Moves Summary

**Prose agreement/divergence verdict below the FlawChess ranked lines, comparing FlawChess's practical #1 pick against Stockfish's objective #1 pick (aligned/safe/sharp tiers), with hoverable click-to-play move spans, board-arrow isolation, and an engine-labeled popover — wired once into the shared `flawChessCard` for automatic game-review parity**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-07
- **Tasks:** 3
- **Files modified:** 5 (2 created new components, 1 new test file, 2 modified: MaiaMoveQualityBar.tsx refactor, Analysis.tsx wiring)

## Accomplishments

- **`ProseSpan.tsx`** (new): extracted the content-agnostic hover-intent + click-to-play interactive span shell from `MaiaMoveQualityBar`'s private `ProseMoveSpan` — same button/Popover/PopoverAnchor/PopoverContent wiring, same synchronous `wasOpenAtPress` ref, same reveal-vs-play click branch and content-bridge hover, but with the popover body parameterized via `children` so a second consumer can supply its own content.
- **`MaiaMoveQualityBar.tsx`** (modified): its `ProseMoveSpan` is now a thin wrapper over `ProseSpan`. All 9 pre-existing tests pass unchanged — no testid, aria-label, or behavior change on the shipped Maia surface.
- **`FlawChessAgreementVerdict.tsx`** (new): renders the D-07 prose verdict for all three tiers —
  - **aligned**: "Both agree on `{move}` — objectively `{eval}`, and the practical pick too." (single named move)
  - **safe**: "Objectively `{sfMove}` (`{sfEval}`). But for a human here, FlawChess plays `{fcMove}` (`{fcEval}`) — barely any cost, far easier."
  - **sharp**: "`{sfMove}` is objectively best (`{sfEval}`) but it's a trap for humans. FlawChess plays the safer `{fcMove}` (`{fcEval}`) instead."
  - D-02/D-03: renders ONLY the fixed-height muted prompt `Turn on Stockfish to compare picks.` when `engineEnabled` is false — the classifier is never invoked.
  - D-06: the same muted slot covers a partial/null classifier result (mid-search snapshot) or an unresolvable UCI→SAN conversion — never a bogus tier, never a raw-UCI leak into the hover callback (Pitfall 2).
  - D-09: hovering/focusing a move span lifts a single `{san, color}` (amber `FLAWCHESS_ENGINE_ARROW` / blue `BEST_MOVE_ARROW`) via `onHoverMovesChange`, clearing to `null` on blur/unmount — feeds the existing `qualityHoverArrows` overlay with zero new plumbing.
  - D-10: the popover body is two engine-labeled lines. The FlawChess pick's popover always shows both (`FlawChess: X (practical)` / `Stockfish: Y (objective)`); the Stockfish pick's popover shows the FlawChess line ONLY when that UCI move is also present in `flawChessRankedLines` (rootMove match), otherwise omitting it entirely (no placeholder, no invented number).
  - D-11: clicking a span while its popover is open calls `onPlayMove(san)`; the first press only reveals it.
- **`FlawChessAgreementVerdict.test.tsx`** (new): 11 tests covering every `<behavior>` case (muted prompt, null-verdict fallback, all 3 tiers, hover-arrow isolation, both D-10 popover variants, both D-11 press states).
- **`Analysis.tsx`** (modified): `FlawChessAgreementVerdict` inserted exactly once as a sibling directly below `FlawChessEngineLines`, inside the same `flawChessCard` `CardBody`, wired to already-existing state/handlers (`setHoveredQualityMoves`, `playProseMove`) — no new plumbing declared. Sources `stockfishLine` from `engine.pvLines[0]` (D-01), never `engineTopLines`. Because `flawChessCard` is a single JSX variable rendered at both the mobile "Human" tab and the desktop human column, this one edit gives free-analysis/game-review parity by construction (SC4/REVIEW-01).

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract the content-agnostic ProseSpan shell** - `19560d10` (refactor)
2. **Task 2: Build FlawChessAgreementVerdict component + tests** - `60bf2e11` (feat)
3. **Task 3: Wire the verdict into the shared flawChessCard in Analysis.tsx** - `7dfd911d` (feat)

**Plan metadata:** commit to follow (docs: complete plan)

## Files Created/Modified

- `frontend/src/components/analysis/ProseSpan.tsx` - content-agnostic hover-intent + click-to-play span shell
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` - the prose agreement verdict component
- `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` - 11 co-located tests
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` - `ProseMoveSpan` refactored into a thin `ProseSpan` wrapper
- `frontend/src/pages/Analysis.tsx` - single insertion of `FlawChessAgreementVerdict` inside `flawChessCard`

## Decisions Made

- Chose extraction over duplication for the `ProseMoveSpan` shell, per `PATTERNS.md`'s recommended default — a single shared interaction primitive now backs both the Maia prose surface and the FlawChess verdict surface.
- The main prose sentence cites each pick's objective eval (the same numbers the win%-drop tier split is computed from) rather than a practical-score-derived number, so the cited evals stay mathematically consistent with the classification the reader sees narrated. The practical-score-converted number is reserved for the D-10 popover's explicit "(practical)"-labeled line.
- The aligned tier renders a single `ProseSpan` built from the FlawChess pick's own span/popover (both engine lines always shown), since the aligned move IS both picks simultaneously — no separate "combined" role type was introduced.
- `uciToSan` is a small local helper (not exported, not pushed into `flawChessVerdict.ts` — keeping that module chess.js-free per its own module contract) using the same `Chess(baseFen).move({from,to,promotion})` + try/catch pattern as `Analysis.tsx`'s existing `playProseMove`.
- D-02/D-03 and D-06 all collapse into the identical muted slot (same testid, same copy) since they're indistinguishable "nothing to narrate yet" states from the caller's point of view — this also means the muted-slot test coverage for "Stockfish off" transitively covers the null-verdict and unresolvable-SAN paths' rendering shape.
- The verdict is inserted inside the `flawChessCard`'s `!flawChessEnabled ? ... : (else)` branch (only rendered when the FlawChess Engine toggle itself is on) rather than unconditionally in the CardBody — when FlawChess is off, `rankedLines` is empty, so the classifier naturally returns `null` and the same muted slot renders; no second explicit gate was needed to achieve the same effect.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Doc-comment literally contained the forbidden "best move" substring**
- **Found during:** Task 2 verification (`grep -in 'best move' FlawChessAgreementVerdict.tsx` acceptance check)
- **Issue:** The module's own doc-comment explaining the D-08 constraint ("no UI string ... reads the bare phrase 'best move'") contained the literal substring it was documenting, tripping the acceptance criterion's grep check on the comment itself (not any user-facing string).
- **Fix:** Reworded the comment to describe the constraint without repeating the literal phrase.
- **Files modified:** `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx`
- **Verification:** `grep -in 'best move' frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — empty (exit 1).
- **Committed in:** `60bf2e11` (part of the Task 2 commit — caught before commit, not a follow-up fix)

---

**Total deviations:** 1 auto-fixed (Rule 1 — a doc-comment self-reference, not a user-facing bug)
**Impact on plan:** None — the component's actual behavior matched the plan exactly; only an internal comment needed rewording.

## Issues Encountered

None. All three tasks' `<verify>` commands passed on the first attempt after the one grep-comment fix above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both plans of Phase 157 are now complete; REVIEW-02 is fully delivered (classifier in 157-01, prose/UI consumer in 157-02).
- `FlawChessAgreementVerdict` is live on `/analysis` in both free analysis and game review (`?game_id&ply`) by construction (single shared `flawChessCard` insertion).
- Manual UAT (SC4, per the plan's `<verification>` section) — opening `/analysis?game_id=<id>&ply=<n>` with Stockfish on to visually confirm the verdict prose, hover arrow isolation, popover, and click-to-play — was not performed as part of this automated execution; recommended as a follow-up human check before considering the phase fully closed.
- No blockers. `npx tsc -b` zero errors, `npm run lint` clean (including `npx knip`), `npm test -- --run` fully green (1548/1548 tests across the whole frontend suite).

---
*Phase: 157-flawchess-agreement-verdict-prose-hoverable-moves*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: frontend/src/components/analysis/ProseSpan.tsx
- FOUND: frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
- FOUND: frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx
- FOUND: frontend/src/components/analysis/MaiaMoveQualityBar.tsx
- FOUND: frontend/src/pages/Analysis.tsx
- FOUND: 19560d10 (refactor commit)
- FOUND: 60bf2e11 (feat commit)
- FOUND: 7dfd911d (feat commit)
