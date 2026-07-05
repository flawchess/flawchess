---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 06
subsystem: frontend / analysis-ui
tags: [maia, analysis-page, layout, react-hook, eval-bar, recharts, elo-selector]

requires:
  - phase: 151-04
    provides: "useMaiaEngine hook (perElo curve + expectedScoreAtSelectedElo + wdl) and MAIA_ELO_LADDER"
  - phase: 151-05
    provides: "EvalBar whiteFraction/testId override, MovesByRatingChart, EloSelector"
  - phase: 151-02
    provides: "MaiaAttribution notice (LIC-02)"
  - phase: 151-03
    provides: "UserProfile.current_rating (free-play ELO default source)"
provides:
  - "frontend/src/hooks/useMaiaEloDefault.ts — D-06/D-07 ELO default-derivation hook (selectedElo/setSelectedElo, FREE_PLAY_DEFAULT_ELO, user-override precedence)"
  - "frontend/src/components/analysis/MaiaHumanPanel.tsx — reusable ELO-selector + chart + attribution bundle"
  - "frontend/src/pages/Analysis.tsx — integrated 3-column desktop + mobile Human-tab layout wiring useMaiaEngine, both eval bars, chart, ELO selector, attribution"
  - ".planning/phases/151-.../151-MAIA-MEASUREMENTS.md — MAIA-06 size measurements + VALID-01 human sign-off"
affects:
  - "Phase 152 (flaw overlay Pillars A+B — builds the salience×trainability verdict on top of this always-on chart+bar surface)"

tech-stack:
  added: []
  patterns:
    - "ELO default-derivation extracted into a dedicated hook (useMaiaEloDefault) with a userOverrodeRef so a late data load seeds the default but a user pick wins permanently — keeps derivation out of the already-large Analysis.tsx render (CLAUDE.md 'refactor bloated code on sight')"
    - "MaiaHumanPanel component reused across THREE surfaces (desktop left column, mobile game-mode Human tab, mobile free-play Human tab) instead of tripling the JSX inline"
    - "Shared humanTab helper-const in Analysis.tsx so the mobile 4-tab strip and the free-play Moves|Human pair don't duplicate the tab-content JSX"

key-files:
  created:
    - frontend/src/hooks/useMaiaEloDefault.ts
    - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts
    - frontend/src/components/analysis/MaiaHumanPanel.tsx
    - frontend/src/components/analysis/__tests__/MaiaHumanPanel.test.tsx
    - .planning/phases/151-maia-in-the-browser-all-position-surfaces/151-MAIA-MEASUREMENTS.md
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "useMaiaEloDefault clamps the derived default to the ladder's [min,max] BOUNDS only (not step-snapping) — a rating like 1720 stays 1720; useMaiaEngine's own nearestByElo picks the closest rung for inference"
  - "useMaiaEngine mounted with enabled:true (not gated behind the Stockfish engine toggle) — MAIA-02 laziness is already satisfied by the route-level React.lazy covering the whole Analysis page; the Worker lives/dies with the component mount"
  - "Extracted the Maia surfaces into MaiaHumanPanel + a humanTab helper-const rather than inlining, because Analysis.tsx is ~1200 lines and the surfaces appear on three layouts"
  - "Free play (D-03 open detail) gets a minimal Moves|Human tab pair (previously move-list only) so the chart is reachable there too — planner decision, kept consistent with the tabbed game-mode surface"
  - "D-10: VALID-01 calibration + move-label sanity check passed -> NO model-size upgrade; the smallest maia3_simplified.onnx ships"

patterns-established:
  - "Analysis.tsx desktop is now a 3-column layout: left = human/Maia (chart + ELO selector + attribution), center = Maia bar + board + Stockfish bar, right = engine/tree/controls"

requirements-completed: [SURF-04, SURF-05, MAIA-04, MAIA-05, MAIA-06, LIC-02, VALID-01]

coverage:
  - id: D1
    description: "useMaiaEloDefault hook — game-mode rating-at-game-time / free-play current_rating default with user-override precedence, clamped to the ladder bounds (D-06/D-07)"
    requirement: "MAIA-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts (6 tests: white/black game mode, free-play current_rating, null fallback, user-override-then-late-load, single re-derive)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Desktop 3-column layout with the Maia bar mounted LEFT (analysis-maia-eval-bar) and Stockfish bar RIGHT (analysis-eval-bar); left human column (analysis-human-column) carries the ELO selector + chart"
    requirement: "SURF-04"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx (asserts analysis-maia-eval-bar + analysis-eval-bar render)"
        status: pass
      - kind: manual_procedural
        ref: "151-MAIA-MEASUREMENTS.md §3 — human confirmed both bars flank the board, correct direction"
        status: pass
    human_judgment: false
  - id: D3
    description: "MaiaHumanPanel (ELO selector + MovesByRatingChart + optional MaiaAttribution) reused across desktop column and mobile Human tabs"
    requirement: "LIC-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/MaiaHumanPanel.test.tsx (3 tests: renders selector+chart, attribution off by default, attribution on with showAttribution)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Mobile game-mode 4-tab strip (Moves|Eval|Human|Tags) + free-play Moves|Human pair, both eval bars persistent above the tab strip (D-03)"
    requirement: "SURF-04"
    verification:
      - kind: manual_procedural
        ref: "151-MAIA-MEASUREMENTS.md §3 — human live pass across game mode + free play"
        status: pass
    human_judgment: true
    rationale: "Mobile tab layout + persistent bars is a responsive-layout behavior best confirmed on a real viewport; the full Analysis page render is mocked at the Worker boundary in jsdom (no real Maia inference), so tab presence was human-verified live rather than asserted headless."
  - id: D5
    description: "Live per-position recompute with no server round-trip; chart + Maia bar update on every board navigation (SURF-05)"
    requirement: "SURF-05"
    verification:
      - kind: manual_procedural
        ref: "151-MAIA-MEASUREMENTS.md §2 qualitative + §3 — human confirmed responsive live recompute"
        status: pass
    human_judgment: true
    rationale: "Live per-move recompute against the real ONNX Worker cannot run in jsdom (no Worker); confirmed observationally in the human live pass."
  - id: D6
    description: "VALID-01 calibration eyeball + policy-vocab move-label sanity check + MAIA-06 size/latency measurement"
    requirement: "VALID-01"
    verification:
      - kind: manual_procedural
        ref: "151-MAIA-MEASUREMENTS.md §1 (sizes), §3 (calibration APPROVED + move-label sanity check confirmed)"
        status: pass
    human_judgment: true
    rationale: "Blocking-human quality gate (D-10 measure-and-judge): calibration plausibility, WDL sign, and correct move-label mapping of the best-effort 4352-vocab reconstruction require live human judgment, not automation."

duration: ~30min
completed: 2026-07-05
status: complete
---

# Phase 151 Plan 06: Analysis-Page Integration + VALID-01 Calibration Gate Summary

**Wired the full Maia surface into `/analysis` — 3-column desktop (Maia chart+selector left, Maia expected-score bar + board + Stockfish bar center, engine panel right), a mobile 4th "Human" tab plus a free-play Moves|Human pair, a `useMaiaEloDefault` hook for the D-07 ELO default, and visible attribution — then passed the VALID-01 human calibration + move-label sign-off with the smallest model retained (D-10).**

## Performance

- **Duration:** ~30 min active execution (excluding the blocking-human checkpoint wait)
- **Completed:** 2026-07-05
- **Tasks:** 4 (3 auto + 1 blocking-human quality gate)
- **Files modified:** 7 (2 new hooks/tests, 1 new component + test, Analysis.tsx + its test, 1 measurements doc)

## Accomplishments

- `useMaiaEloDefault.ts`: derives the "you are here" ELO from game-mode rating-at-game-time (`gameData.white_rating`/`black_rating` by `user_color`) or free-play `profile.current_rating ?? 1500`, clamped to the ladder bounds, with a `userOverrodeRef` so a late data load seeds the default but a user pick wins permanently. Six unit tests.
- Desktop `/analysis` reworked into the D-01 3-column layout: left `analysis-human-column` (ELO selector + Moves-by-Rating chart + attribution), center = Maia expected-score bar (`analysis-maia-eval-bar`, LEFT) + board + Stockfish bar (`analysis-eval-bar`, RIGHT), right = the unchanged engine/variation-tree/controls panel.
- Mobile game mode gained a 4th tab (`analysis-tab-human`) for order Moves | Eval | Human | Tags; free play gained a minimal Moves | Human tab pair so the chart is reachable there too — both eval bars stay above the tab strip in every mobile mode.
- `MaiaHumanPanel.tsx` extracted (ELO selector + chart + optional attribution) and reused across all three surfaces; `MaiaAttribution` now visibly mounted (LIC-02).
- VALID-01 human sign-off APPROVED (calibration + policy-vocab move-label sanity check) with MAIA-06 static sizes recorded; D-10 decision: no model-size upgrade.

## Task Commits

1. **Task 1: useMaiaEloDefault hook (TDD)** - `71f53956` (feat)
2. **Task 2: mount useMaiaEngine + Maia bar + desktop 3-column** - `e19d808d` (feat)
3. **Task 3: mobile Human tab + free-play tab pair + MaiaAttribution** - `8e942ece` (feat)
4. **Task 4: MAIA-06 measurements + VALID-01 human sign-off** - `e8787c84` (docs)

**Plan metadata:** this SUMMARY + STATE/ROADMAP/REQUIREMENTS update is the final commit.

## Files Created/Modified

- `frontend/src/hooks/useMaiaEloDefault.ts` - ELO default-derivation hook + FREE_PLAY_DEFAULT_ELO
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` - 6 unit tests
- `frontend/src/components/analysis/MaiaHumanPanel.tsx` - reusable ELO-selector + chart + attribution bundle
- `frontend/src/components/analysis/__tests__/MaiaHumanPanel.test.tsx` - 3 composition tests
- `frontend/src/pages/Analysis.tsx` - useMaiaEngine/useMaiaEloDefault/useUserProfile wiring, second (Maia) EvalBar, desktop 3-column, mobile Human tab + free-play tab pair, humanTab helper-const, playedSan/bestSan derivation, bestSanFromPv helper
- `frontend/src/pages/__tests__/Analysis.test.tsx` - mock useMaiaEngine/useUserProfile (no real Worker in jsdom), assert analysis-maia-eval-bar
- `.planning/phases/151-.../151-MAIA-MEASUREMENTS.md` - MAIA-06 sizes + VALID-01 sign-off

## Decisions Made

- ELO default clamps to the ladder's `[min, max]` bounds only (no step-snapping); `useMaiaEngine.nearestByElo` picks the inference rung.
- `useMaiaEngine` mounted with `enabled: true` (not behind the Stockfish toggle) — route-level `React.lazy` already provides MAIA-02 laziness; the Worker lives/dies with the mount.
- Extracted `MaiaHumanPanel` + a `humanTab` helper-const rather than inlining, honoring CLAUDE.md's nesting/LOC limits on the ~1200-line `Analysis.tsx`.
- Free play gets a Moves|Human tab pair (D-03 open detail resolved by the planner).
- D-10: calibration acceptable → smallest `maia3_simplified.onnx` retained, no 23M/79M upgrade.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Mocked useMaiaEngine + useUserProfile in the existing Analysis page test**
- **Found during:** Task 2/3 (after mounting the Maia hooks)
- **Issue:** `src/pages/__tests__/Analysis.test.tsx` renders the real `Analysis` page in jsdom, which has no `Worker` global for the classic Maia worker file — `new Worker(...)` in `useMaiaEngine` threw `ReferenceError: Worker is not defined`, failing all 5 pre-existing shell tests.
- **Fix:** Added `vi.mock('@/hooks/useMaiaEngine', ...)` returning a deterministic empty-curve stub and `vi.mock('@/hooks/useUserProfile', ...)` returning `{ data: undefined }` — mirroring the file's existing `useStockfishEngine` mock (jsdom has no real Worker for either engine). Also added an assertion that the new `analysis-maia-eval-bar` testid renders (SURF-04).
- **Files modified:** frontend/src/pages/__tests__/Analysis.test.tsx
- **Verification:** All 5 shell tests pass again; full suite 114 files / 1316 tests green.
- **Committed in:** `8e942ece` (Task 3 commit)

**2. [Rule 2 - Missing Critical] Added a bestSanFromPv helper for the chart's best-move emphasis**
- **Found during:** Task 2 (deriving MovesByRatingChart's `bestSan`)
- **Issue:** The chart's `bestSan` prop needs a SAN, but the engine exposes only the top-line first move as a UCI string (`engine.pvLines[0].moves[0]`). Passing UCI would silently never match the chart's SAN-keyed move set, so the engine-best line would never be emphasized.
- **Fix:** Added a module-scope `bestSanFromPv(baseFen, uci)` that replays the UCI move via chess.js at the current position and returns its SAN (null-safe, never throws). Consumed via a memo keyed on `[position, engine.pvLines]`.
- **Files modified:** frontend/src/pages/Analysis.tsx
- **Verification:** tsc/lint/knip/build green; chart renders with best-move emphasis.
- **Committed in:** `e19d808d` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking test-infra, 1 missing-critical helper)
**Impact on plan:** Both were necessary for the integration to function/verify; no scope creep beyond what the tasks' own action text implied (mounting the hook, feeding the chart's bestSan).

## Issues Encountered

- MAIA-06 per-device latency + cold-load numbers were not recorded numerically by the human during the live pass; the measurements doc records real on-disk artifact sizes and explicitly marks the per-device latency/cold-load rows as NOT YET MEASURED rather than fabricating values. Static sizes and the VALID-01 verdict are captured; a numeric latency budget can be filled later if introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The always-on Maia chart + expected-score bar surface is live and human-validated (calibration + correct move-label mapping), which is exactly the trust gate Phase 152 (flaw salience×trainability verdict) was waiting on.
- Open follow-up (non-blocking): numeric MAIA-06 per-device latency/cold-load timings remain unrecorded; capture on a real device if a latency budget is needed. The 151-04 policy-vocab index scheme is now human-validated against live inference for the positions checked (was the phase's main open risk).

---
*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Completed: 2026-07-05*

## Self-Check: PASSED
All 4 key created files exist on disk; all 4 task commits (71f53956, e19d808d, 8e942ece, e8787c84) present in git log.
