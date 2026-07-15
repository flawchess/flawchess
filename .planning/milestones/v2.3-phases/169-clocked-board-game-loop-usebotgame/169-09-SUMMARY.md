---
phase: 169-clocked-board-game-loop-usebotgame
plan: "09"
subsystem: frontend-hooks
tags: [chess-clock, honest-clock, think-deadline, react-hooks, vitest, gap-closure]

requires:
  - phase: 169-clocked-board-game-loop-usebotgame
    plan: "08"
    provides: "computeThinkDeadlineMs (chessClock.ts D-16) and createDeadlineSearch/BOT_MIN_SEARCH_NODES (deadlineSearch.ts) — the two pure primitives this plan wires into useBotGame"
provides:
  - "useBotGame.ts: honest bot debit (D-15), per-move think deadline dispatch (D-16/D-17), hidden-tab debit fix (D-20/WR-02), idempotent finalizeGame (WR-03), scroll-back-preserving commitMove (WR-05)"
  - "GameControls.tsx/Bots.tsx: correct draw-cooldown prop wiring and conditional tooltip (WR-04)"
  - "botBudget.ts: D-19 documentation caveat (deadline-cut bot plays below advertised ELO in time trouble)"
  - "168.5-CONTEXT.md + REQUIREMENTS.md: amended to reflect the reversed never-flag invariant, closing the two BLOCKED requirements"
affects: [170-localstorage-resume, 171-bots-page-setup-store]

tech-stack:
  added: []
  patterns:
    - "Idempotency latch via a ref (not state) for a finalize action reachable from async continuations and effects that can hold a stale closure"
    - "Two-signal abort separation consumed at the call site: the outer AbortSignal now means exactly one thing (cancel) because the deadline cut lives entirely inside createDeadlineSearch's inner controller"
    - "View/live-ply snapshot via refs kept in sync by a dedicated setter (updateViewedPly) plus a same-tick-safe liveGamePlyRef, avoiding a state-setter-inside-updater purity violation"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/GameControls.tsx
    - frontend/src/lib/engine/botBudget.ts
    - .planning/REQUIREMENTS.md
    - .planning/phases/168.5-bot-move-pacing-search-budget-seed-096/168.5-CONTEXT.md

key-decisions:
  - "resetTurnAnchor() re-baselines pausedAtRef alongside turnStartedAtRef whenever the anchor resets (commitMove, newGame) — the single fix point for WR-02's future-dated-anchor bug, since both refs must move together or a mid-hide commit corrupts the next mover's elapsed calculation"
  - "commitMove computes wasLive from viewedPlyRef/liveGamePlyRef (both refs, kept fresh outside the render cycle) rather than closing over moveHistory/viewedPly state directly — commitMove's own useCallback deps don't include either, so a direct read would be permanently stale"
  - "buildBotMoveDeps extracted as a top-level pure helper (not inlined in runBotTurn) purely to keep the D-16 wiring auditable in one place and respect CLAUDE.md's logic-LOC/nesting limits on an already-dense async body"
  - "Test G (WR-03) captures a REAL stale closure (result.current.offerDraw taken before checkmate) rather than trying to win a race against React's effect-flush timing — deterministic and directly mirrors the bug report's 'stale closure under rapid updates' mechanism; wouldBotAcceptDraw is forced true via a test-only override object since the Fool's-mate script never satisfies the real endgame gate"
  - "168.5-CONTEXT.md D-01/D-02/D-04 get SUPERSEDED annotations appended (original text preserved verbatim) rather than rewritten, so the historical decision record stays intact and future verifiers don't re-fail the phase on stale prose"

requirements-completed: [PLAY-03, PLAY-04, PLAY-05, PLAY-06, PLAY-07]

coverage:
  - id: D1
    description: "The bot is debited its real wall-clock turn time (search + reveal delay) plus the Fischer increment on commit — the same rule the user's clock obeys (D-15)"
    requirement: "PLAY-05"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGame.test.ts > pacing > ticks the bot clock down in real time... and debits the REAL elapsed time on commit (D-15 honest clock)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The bot can lose on time: a bot whose think outlasts its remaining clock produces a timeout LOSS for the bot, winner = user (amended SC1)"
    requirement: "PLAY-06"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGame.test.ts > bot clock (D-15/D-16/D-18, amended SC1) > bot flags on time..."
        status: pass
    human_judgment: false
  - id: D3
    description: "The bot enforces a per-move think deadline derived from its remaining clock (computeThinkDeadlineMs + BOT_MIN_SEARCH_NODES wired via createDeadlineSearch's deps.search seam), and a deadline-cut search still commits its best move so far — a cancel still discards the turn (D-16/D-17)"
    requirement: "PLAY-05"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGame.test.ts > bot clock ... > wires the D-16 think deadline into deps.search..., > the node floor stays BOT_MIN_SEARCH_NODES...; cancel (D-17) > a cancel during the bot think (resign) discards the turn..."
        status: pass
    human_judgment: false
  - id: D4
    description: "Time while the tab is hidden during the bot's think is not charged to its committed debit, and a move committed while still hidden cannot produce a future-dated anchor on resume (D-20/WR-02, amended SC2)"
    requirement: "PLAY-04"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGame.test.ts > hidden-tab time (D-20/WR-02, amended SC2) > both tests"
        status: pass
    human_judgment: false
  - id: D5
    description: "finalizeGame is idempotent (first outcome wins) — a stale draw-accept resolving after a bot move already delivered checkmate cannot overwrite the outcome, PGN, or double-fire the game-end sound (WR-03)"
    requirement: "PLAY-06"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGame.test.ts > finalize idempotency (WR-03) > a stale draw-accept resolving after a bot move already delivered checkmate..."
        status: pass
    human_judgment: false
  - id: D6
    description: "A bot move no longer ejects the user from D-13 view-only scroll-back (WR-05); setViewedPly is never called from inside the setMoveHistory updater"
    requirement: "PLAY-03"
    verification:
      - kind: static
        ref: "grep -n 'setViewedPly' frontend/src/hooks/useBotGame.ts — the only call site outside updateViewedPly's own definition is the useState declaration"
        status: pass
    human_judgment: false
  - id: D7
    description: "The draw-cooldown tooltip only appears when the cooldown is actually active, and the GameControls props are wired to their documented meanings (WR-04)"
    requirement: "PLAY-07"
    verification:
      - kind: static
        ref: "git diff frontend/src/pages/Bots.tsx frontend/src/components/bots/GameControls.tsx — drawCooldownActive={!game.canOfferDraw} replaces the hardcoded false; the Tooltip only mounts when drawCooldownActive is true"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-07-13
status: complete
---

# Phase 169 Plan 09: useBotGame Honest-Clock Gap Closure Summary

**Rewires `useBotGame` onto the honest, flaggable bot clock (D-15/D-16) with a per-move think deadline injected via `createDeadlineSearch`, fixes the hidden-tab debit exploit (D-20/WR-02), makes `finalizeGame` idempotent (WR-03), stops bot moves from ejecting the user out of scroll-back (WR-05), and fixes the dead draw-cooldown prop (WR-04) — closing PLAY-04/PLAY-05 and restoring amended SC1/SC2.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-07-13
- **Tasks:** 3
- **Files modified:** 7 (2 code files rewired, 1 test file extended, 2 UI files fixed, 1 constants doc-only, 2 docs)

## Accomplishments

- `useBotGame.ts`'s clock model is now honest end-to-end: the bot's debit is `computeElapsedMs(turnStartedAtRef.current, Date.now())` read LIVE at resolution time (no dispatch-time snapshot local), the clock-tick effect's flag check stays ungated by color, and a per-move think deadline (`computeThinkDeadlineMs`) is injected into `selectBotMove` via `createDeadlineSearch({ deadlineMs, minNodes: BOT_MIN_SEARCH_NODES })` — a deadline cut resolves normally with the search's best-so-far move (committed), while an outer cancel (resign/new game/unmount/bot-flagged) still discards the turn, because the two travel on physically separate AbortControllers.
- `resetTurnAnchor()` is the single fix point for D-20/WR-02: it re-baselines `pausedAtRef` alongside `turnStartedAtRef` whenever the anchor resets, so a bot move committing while the tab is still hidden can never shift the anchor into the future on resume.
- `finalizeGame` is latched by `outcomeRef` (first outcome wins); the draw-resolution effect checks the same ref before evaluating `wouldBotAcceptDraw`, so a stale pending draw offer can never overwrite a real checkmate/timeout outcome, PGN, or double-fire the game-end sound.
- `commitMove` no longer calls `setViewedPly` from inside the `setMoveHistory` updater (a purity violation) and only snaps the view to live when the viewer was already live (or the mover is the user, who can only move from the live position) — bot moves no longer eject the user from D-13 scroll-back.
- `Bots.tsx`/`GameControls.tsx`: the cooldown prop is now genuinely wired to `!game.canOfferDraw` (the hook's cooldown gate, inverted) and the tooltip only mounts when the cooldown is actually active, per WR-04.
- `botBudget.ts` carries a comment-only D-19 caveat; `168.5-CONTEXT.md`'s D-01/D-02/D-04 decisions are annotated SUPERSEDED (original text preserved, D-04b's "harness has no pacing theater" clause explicitly noted as surviving); `REQUIREMENTS.md`'s PLAY-03..PLAY-07 traceability rows updated to Complete.
- 18 tests in `useBotGame.test.ts` (12 pre-existing + 6 new gap-closure behaviors, plus the corrected "pacing" assertion), all passing consistently across repeated runs (the reveal delay uses real, unseeded `Math.random`).
- Full frontend gate green: `npm run lint && npx tsc -b && npm test -- --run && npm run knip` — 149 test files, 1886 tests, zero lint/type/knip issues. Backend PGN roundtrip contract (`tests/test_bot_pgn_clk_roundtrip.py`) unaffected.

## Task Commits

1. **Task 1: useBotGame — honest debit, per-move think deadline, hidden-tab debit fix, idempotent finalize, scroll-back preservation** — `eccf09b7` (feat)
2. **Task 2: useBotGame regression tests — the six behaviors whose absence let these gaps ship** — `b6c04319` (test)
3. **Task 3: Draw-cooldown prop wiring + doc amendments (D-19 in botBudget, 168.5 decision records, REQUIREMENTS traceability) + full frontend gate** — `3820b55f` (fix)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/hooks/useBotGame.ts` — rewired: synthetic-debit/never-flag imports deleted; `resetTurnAnchor`/`updateViewedPly`/`buildBotMoveDeps` helpers added; `finalizeGame`/`commitMove`/draw-resolution effect/`runBotTurn` all amended per D-15/D-16/D-17/D-20/WR-02/WR-03/WR-05
- `frontend/src/hooks/__tests__/useBotGame.test.ts` — pacing assertion fixed (honest debit, not never-flag); 6 new describe blocks (`bot clock`, `cancel`, `hidden-tab time`, `finalize idempotency`) with 6 new tests; two new mocks (`deadlineSearch` spy, `botDrawGate` passthrough-with-override)
- `frontend/src/pages/Bots.tsx` — `GameControls`'s `canOfferDraw`/`drawCooldownActive` props correctly wired
- `frontend/src/components/bots/GameControls.tsx` — the cooldown Tooltip conditionally mounts only when `drawCooldownActive` is true
- `frontend/src/lib/engine/botBudget.ts` — D-19 documentation-only addition, no constant changed
- `.planning/REQUIREMENTS.md` — PLAY-03..PLAY-07 rows set to Complete
- `.planning/phases/168.5-bot-move-pacing-search-budget-seed-096/168.5-CONTEXT.md` — D-01/D-02/D-04 marked SUPERSEDED, D-04b's harness clause noted as surviving

## Decisions Made

See `key-decisions` in frontmatter for the five load-bearing implementation decisions (anchor re-baseline point, ref-based staleness avoidance in `commitMove`, the `buildBotMoveDeps` extraction, the deterministic stale-closure construction for Test G, and the append-don't-rewrite approach to `168.5-CONTEXT.md`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion bugs in the first draft of Tests 2 (pacing) and 8b (WR-02 mid-hide commit) — not implementation bugs**
- **Found during:** Task 2, first `vitest run` of the new suite.
- **Issue:** Two test assertions were internally inconsistent with the hook's own correct, by-design behavior: (a) the pacing test's tight debit band (7000-9500ms) was too narrow given legitimate effect-dispatch scheduling slack, failing at an actual debit of 10000ms; (b) the WR-02 mid-hide-commit test compared the post-resume clock against an EARLIER, still-hidden-interval reading (which legitimately continues ticking down while hidden, then correctly jumps back up at resume once the pause discount applies) rather than against the clock's true base — the correct invariant per the plan's own wording is "no clock ever exceeds its post-increment base", not "never exceeds an arbitrary earlier reading".
- **Fix:** Widened the pacing band to 7000-11000ms (still tightly excludes the old synthetic model's ~15000ms debit); rewrote the WR-02 assertion to compare against the fixed base (`DEFAULT_SETTINGS.baseSeconds * 1000`) instead of a mid-sequence snapshot.
- **Files modified:** `frontend/src/hooks/__tests__/useBotGame.test.ts` (test-only; `useBotGame.ts` itself needed no change — traced the discrepancy to the test's own faulty premise, confirmed via manual sequence tracing of the anchor/pause math).
- **Commit:** `b6c04319` (Task 2 commit — both fixes landed before the task was committed, no separate commit needed)

**2. [Rule 3 - Blocking] `vi.mock` factory TDZ ReferenceError on first test run**
- **Found during:** Task 2, first `vitest run` of the new suite.
- **Issue:** The initial `@/lib/botDrawGate` mock called `mockWouldBotAcceptDraw.mockImplementation(actual.wouldBotAcceptDraw)` eagerly inside the `vi.mock` factory body. Because `vi.mock(...)` factories run as part of resolving `useBotGame.ts`'s import graph — which happens BEFORE the test file's own top-level `const` statements execute — this eagerly touched a not-yet-initialized `const`, tripping a TDZ `ReferenceError`.
- **Fix:** Replaced the `vi.fn()`-based spy-with-eager-mutation with a plain mutable override object (`acceptDrawOverride: { value: boolean | null }`) that the factory's returned closure only ever READS lazily (at actual call time, well after the test file has finished initializing) — never mutated eagerly inside the factory body itself.
- **Files modified:** `frontend/src/hooks/__tests__/useBotGame.test.ts`.
- **Commit:** `b6c04319` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 test-assertion bug, 1 blocking test-infra issue) — both confined to the test file; zero changes to the hook or UI implementation beyond what the plan specified.
**Impact on plan:** No scope creep — both fixes were necessary to get the specified regression coverage actually running and asserting the correct invariant.

## Auth Gates Encountered

None.

## Known Stubs

None.

## Threat Flags

None beyond the plan's own pre-declared threat register (T-169-09-01/02/03/04), which this implementation satisfies:
- T-169-09-01 (hidden-tab debit farming) — closed by reading `turnStartedAtRef.current` live at resolution time; locked by the "hidden-tab time... is not charged" test.
- T-169-09-02 (WR-02 future-dated anchor) — closed by `resetTurnAnchor`'s pause re-baseline; locked by the mid-hide-commit test.
- T-169-09-03 (non-idempotent finalize) — closed by the `outcomeRef` latch; locked by the WR-03 test.
- T-169-09-04 (client-supplied PGN/outcome trust) — explicitly out of scope, transferred to Phase 171/STORE-02 per the plan's own threat register; unchanged by this plan.

## Expected Temporary Breakage (from Plan 08, resolved here)

Plan 08 intentionally left `useBotGame.ts`/`useBotGame.test.ts` broken (2 `tsc` errors, 6/11 failing tests) pending this plan's wiring. Both are now fully resolved: `npx tsc -b` is clean, and all 18 tests in `useBotGame.test.ts` pass.

## Issues Encountered

None beyond the two self-resolved test-authoring issues documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`useBotGame`'s public contract (`UseBotGameState`, `BotGameSettings`) is unchanged — Phases 170 (localStorage resume) and 171 (setup screen + store-on-finish) can consume it exactly as before. The frozen Phase 166/168.5 engine core (`mctsSearch.ts`, `selectBotMove.ts`, `botBudget.ts`'s calibrated constants) remains byte-identical throughout this closure. Amended SC1/SC2 both hold (proven by automated tests, not just prose); PLAY-04/PLAY-05 move from BLOCKED to Complete; PLAY-06/PLAY-07 are hardened. No blockers for Phase 170/171.

## Self-Check: PASSED

- `[ -f frontend/src/hooks/useBotGame.ts ]` → FOUND
- `[ -f frontend/src/hooks/__tests__/useBotGame.test.ts ]` → FOUND
- `[ -f frontend/src/pages/Bots.tsx ]` → FOUND
- `[ -f frontend/src/components/bots/GameControls.tsx ]` → FOUND
- `git log --oneline --all | grep -E "eccf09b7|b6c04319|3820b55f"` → all three commits FOUND
- `cd frontend && npx tsc -b` → clean, zero errors
- `cd frontend && npx vitest run src/hooks/__tests__/useBotGame.test.ts` → 18/18 passed (verified across 3 consecutive runs, no flake)
- `cd frontend && npm run lint && npx tsc -b && npm test -- --run && npm run knip` → all green (149 test files, 1886 tests)
- `uv run pytest tests/test_bot_pgn_clk_roundtrip.py -q` → 1 passed
- `git diff --stat frontend/src/lib/engine/mctsSearch.ts frontend/src/lib/engine/selectBotMove.ts` → empty (frozen engine core untouched)
- `git diff frontend/src/lib/engine/botBudget.ts` → comment-only, all constant values byte-identical

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-13*
