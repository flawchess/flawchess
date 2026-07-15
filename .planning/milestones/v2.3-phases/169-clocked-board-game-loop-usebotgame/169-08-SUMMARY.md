---
phase: 169-clocked-board-game-loop-usebotgame
plan: 08
subsystem: frontend-lib
tags: [chess-clock, honest-clock, think-deadline, mcts-abort, gap-closure, vitest]

requires:
  - phase: 169-clocked-board-game-loop-usebotgame
    plan: "01"
    provides: "the original chessClock.ts module this plan rewrites (D-05 synthetic debit + never-flag clamp, now deleted)"
  - phase: 169-clocked-board-game-loop-usebotgame
    plan: "04"
    provides: "the original useBotGame.ts consumer of the deleted chessClock.ts helpers (temporarily broken by this plan; fixed by Plan 09)"
provides:
  - "chessClock.ts: honest bot clock (no synthetic debit, no never-flag clamp) + computeThinkDeadlineMs, the D-16 banded per-move think deadline"
  - "deadlineSearch.ts (net-new): createDeadlineSearch, a SearchRunner wrapper that cuts an in-flight search at a deadline, gated by the reused BOT_MIN_SEARCH_NODES floor, with immediate outer-cancel propagation"
affects: [169-09-usebotgame-clock-wiring]

tech-stack:
  added: []
  patterns:
    - "Two-signal abort separation: a wrapper's own inner AbortController isolates a 'soft' internal cut (deadline) from the caller's 'hard' outer signal (cancel), so the two can never be confused by a shared signal.aborted check"
    - "Deletion over deprecation for a reversed invariant (D-15) — the old synthetic-debit/never-flag machinery was removed outright, not guarded behind a flag or left commented out"

key-files:
  created:
    - frontend/src/lib/engine/deadlineSearch.ts
    - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts
  modified:
    - frontend/src/lib/chessClock.ts
    - frontend/src/lib/__tests__/chessClock.test.ts

key-decisions:
  - "D-16 deadline constants tuned by feel against the 168.5-04 measured search cost (median ~5.4s, worst-case ~12.7s): BOT_MOVES_TO_GO=30, BOT_THINK_INCREMENT_SHARE=0.7, BOT_THINK_DEADLINE_MIN_MS=800, BOT_THINK_DEADLINE_MAX_MS=15000, BOT_MOVE_OVERHEAD_MS=300 — a full 5+3 clock yields a ~12.1s deadline (comfortably above the median), while a near-empty clock decays toward the 800ms floor"
  - "Deleted-symbol doc references in chessClock.ts's new module docstring avoid literally naming the five deleted symbols (computeSyntheticDebitMs/reconcileBotDebitMs/NEVER_FLAG_FLOOR_MS/SYNTHETIC_DEBIT_DIVISOR/SYNTHETIC_INCREMENT_SHARE) so the plan's zero-hits grep check stays meaningful against the whole file, not just the deleted function bodies"
  - "deadlineSearch.ts's stub test fixture (createStubBaseSearch) mirrors mctsSearch's actual two abort-handling paths: an EventListener-based abort mid-run (graceful stop with best-so-far snapshot) AND a synchronous already-aborted-at-entry check (mirroring mctsSearch's while-loop-condition short-circuit) — the second path was added after the first test run surfaced a real timeout bug in the stub itself, not the module under test"

requirements-completed: []  # PLAY-04/PLAY-05 frontmatter-shared with Plan 09 (useBotGame clock wiring, which also owns the REQUIREMENTS.md/168.5-CONTEXT.md/botBudget.ts doc amendments per its own Task 3). This plan delivers only the honest-clock math + deadline-search wrapper; Plan 09 closes both requirements end-to-end and updates traceability.

coverage:
  - id: D1
    description: "The bot's clock is honest: no synthetic fraction-of-remaining debit, no never-flag clamp exist anywhere in chessClock.ts"
    requirement: "PLAY-05 (D-15)"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts (all 17 tests pass with zero references to the deleted symbols)"
        status: pass
      - kind: static
        ref: "grep -rn for the five deleted symbol names across frontend/src — zero hits outside useBotGame.ts's expected temporary breakage"
        status: pass
    human_judgment: false
  - id: D2
    description: "computeThinkDeadlineMs derives a banded, affordable per-move think deadline from remaining time + increment"
    requirement: "PLAY-05 (D-16)"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#computeThinkDeadlineMs (D-16 per-move think deadline) — 5 behaviors: full-clock exceeds median, shrinks monotonically, band clamp both directions, affordability cap, zero-increment usability"
        status: pass
    human_judgment: false
  - id: D3
    description: "createDeadlineSearch stops a search at the deadline and returns the best-so-far snapshot, not a throw or empty result"
    requirement: "PLAY-04/PLAY-05 (D-16/D-17)"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/deadlineSearch.test.ts (deadline-cut test)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The deadline never cuts below the D-18 minimum-node floor (reused BOT_MIN_SEARCH_NODES, not re-typed) — accepts a small overrun instead"
    requirement: "PLAY-05 (D-18)"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/deadlineSearch.test.ts (node-floor test)"
        status: pass
    human_judgment: false
  - id: D5
    description: "An outer cancel abort propagates immediately, never delayed by the node floor"
    requirement: "PLAY-04 (D-17)"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/deadlineSearch.test.ts (cancel-immediacy test)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-13
status: complete
---

# Phase 169 Plan 08: Honest Bot Clock + Think-Deadline Search Wrapper Summary

**Deleted the bot's synthetic-debit/never-flag clock math (D-15) and replaced the fixed search budget with a D-16 per-move think deadline enforced entirely outside the frozen engine core via a new `deadlineSearch.ts` `SearchRunner` wrapper, gated by the reused D-18 node floor and D-17 cancel-immediacy — a gap-closure response to the SC1/SC2 verification failure.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-13
- **Tasks:** 2
- **Files modified:** 4 (2 new, 2 rewritten)

## Accomplishments

- `chessClock.ts` no longer has any synthetic-debit or never-flag concept: `computeSyntheticDebitMs`, `reconcileBotDebitMs`, `NEVER_FLAG_FLOOR_MS`, `SYNTHETIC_DEBIT_DIVISOR`, `SYNTHETIC_INCREMENT_SHARE` are deleted outright (not guarded/deprecated), and the module docstring is rewritten with the D-15/D-16 model plus the D-19 calibration caveat (the bot's advertised ELO holds only at the full node budget — a deadline-cut bot in time trouble plays weaker, by design).
- `computeThinkDeadlineMs(remainingMs, incrementMs)` derives a banded per-move deadline (`remaining/BOT_MOVES_TO_GO + increment*BOT_THINK_INCREMENT_SHARE`, clamped to `[BOT_THINK_DEADLINE_MIN_MS, BOT_THINK_DEADLINE_MAX_MS]`, hard-capped at `remaining - BOT_MOVE_OVERHEAD_MS`, floored at 0) — 17 tests cover the full increment/pause/deadline behavior with zero DOM.
- `deadlineSearch.ts` (net-new) exports `createDeadlineSearch`, wrapping any `SearchRunner` (`mctsSearch` by default) with a deadline enforced through an INNER `AbortController` the caller never sees — `selectBotMove` argmaxes/samples the returned best-so-far snapshot exactly as if the search had finished on its own budget. `BOT_MIN_SEARCH_NODES` is derived from `FLAWCHESS_BOT_STOP_RULE.minNodes` (no re-typed literal). Six tests cover the deadline cut, the node-floor arm-then-fire behavior, immediate outer-cancel propagation (bypassing an unreachably-high floor), the fast path (with a timer-leak assertion via `vi.getTimerCount()`), full `onSnapshot` pass-through, and an already-aborted-at-entry edge case.
- The frozen engine core (`mctsSearch.ts`, `selectBotMove.ts`, `botBudget.ts`'s constants) is byte-identical — verified via `git diff --stat` showing no changes.

## Task Commits

1. **Task 1: chessClock.ts — delete the synthetic/never-flag math, add the D-16 per-move think deadline** — `2e2e2fff` (feat)
2. **Task 2: deadlineSearch.ts — SearchRunner wrapper that cuts at the deadline, gated by the D-18 node floor** — `2925a454` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/lib/chessClock.ts` — rewritten: synthetic-debit/never-flag machinery deleted; `computeThinkDeadlineMs` + 5 named D-16 constants added; module docstring rewritten with D-15/D-16/D-19
- `frontend/src/lib/__tests__/chessClock.test.ts` — rewritten: dropped the two deleted describe blocks and dead imports; added a `computeThinkDeadlineMs` describe with 5 behaviors
- `frontend/src/lib/engine/deadlineSearch.ts` — net-new: `createDeadlineSearch`, `DeadlineSearchOptions`, `BOT_MIN_SEARCH_NODES`
- `frontend/src/lib/engine/__tests__/deadlineSearch.test.ts` — net-new: 6 tests with a controllable stub `SearchRunner` fixture and fake timers

## Decisions Made

- D-16 deadline constants (`BOT_MOVES_TO_GO=30`, `BOT_THINK_INCREMENT_SHARE=0.7`, `BOT_THINK_DEADLINE_MIN_MS=800`, `BOT_THINK_DEADLINE_MAX_MS=15000`, `BOT_MOVE_OVERHEAD_MS=300`) tuned by feel per the plan's Claude's-Discretion note, checked against the 168.5-04 measured search cost — see `key-decisions` above and doc comments in `chessClock.ts` for the full reasoning.
- Kept the deleted symbol names out of the new module docstring's prose (referring to "the old machinery" instead of naming each symbol) so the plan's `grep -rn "<name>"` zero-hits acceptance check stays meaningful for the whole file, not just the removed function bodies.
- `deadlineSearch.test.ts`'s stub `SearchRunner` fixture needed a synchronous already-aborted-at-entry check (mirroring `mctsSearch`'s real `while (... && !signal.aborted ...)` loop-condition short-circuit) in addition to its event-listener-based abort handling — the first version only handled the event-listener path and hung on the already-aborted bonus test until this was added (see Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test-fixture (not module-under-test) bug: stub `SearchRunner` hung on an already-aborted outer signal**
- **Found during:** Task 2, writing the bonus "already aborted at entry" test for `deadlineSearch.test.ts`.
- **Issue:** The first version of `createStubBaseSearch` only resolved on an `'abort'` event listener. Since `chessClock.ts`'s wrapper aborts its inner controller synchronously (before ever registering a listener) when the outer signal is already aborted at call time, the inner signal is already-aborted before `baseSearch` runs — so an `'abort'` event never fires (the event already happened), and the listener-only stub never resolved, timing out the test.
- **Fix:** Added a synchronous `if (signal.aborted) { finish(latestSnapshot); return; }` check at the top of the stub's promise executor, mirroring `mctsSearch.ts`'s actual `while (nodesEvaluated < budget.maxNodes && !signal.aborted && !earlyStop)` loop-condition behavior (an already-aborted signal never enters the loop, and falls straight through to `return buildSnapshot(...)`).
- **Files modified:** `frontend/src/lib/engine/__tests__/deadlineSearch.test.ts` (test fixture only — `deadlineSearch.ts` itself required no change; its already-aborted-at-entry handling was correct from the start).
- **Commit:** `2925a454`

## Auth Gates Encountered

None.

## Known Stubs

None. Both `chessClock.ts` and `deadlineSearch.ts` are complete, fully-wired pure modules with no placeholder data paths — they are not yet consumed by `useBotGame.ts` (that wiring is explicitly Plan 09's scope), but nothing in this plan's own deliverables is a stub.

## Threat Flags

None beyond the plan's own pre-declared threat register (T-169-08-01/02/03), which this implementation satisfies:
- T-169-08-02 (timer/listener leak) — the fast-path test explicitly asserts `vi.getTimerCount() === 0` after resolution, and the `finally` block clears the timer and removes the outer abort listener on every exit path.
- T-169-08-03 (node-floor bypass) — the dedicated node-floor test proves a deadline firing at 0 nodes does not cut until `BOT_MIN_SEARCH_NODES` is reached.

## Expected Temporary Breakage (per plan, resolved by Plan 09)

As explicitly documented in the plan's task 1 acceptance criteria and top-level `<verification>` section, this plan intentionally leaves two things broken until Plan 09:
- `useBotGame.ts` still imports the now-deleted `computeSyntheticDebitMs`/`reconcileBotDebitMs` (lines 37-38, 522-523) — `cd frontend && npx tsc -b` reports 2 errors, both confined to `useBotGame.ts`. `deadlineSearch.ts` itself has zero `tsc` errors.
- `frontend/src/hooks/__tests__/useBotGame.test.ts` fails 6/11 tests at runtime with `TypeError: computeSyntheticDebitMs is not a function` (the same root cause, surfaced by Vitest's non-type-checking transform). This is out of this plan's scope (`useBotGame.ts` is not in `files_modified`); Plan 09 wires the honest clock + deadline search into the hook and restores a fully green frontend gate.

## Issues Encountered

None beyond the self-resolved test-fixture bug documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`computeThinkDeadlineMs` and `createDeadlineSearch` are both ready for Plan 09 to wire into `useBotGame.ts`: replace the deleted-helper call site (lines 522-523) with `computeThinkDeadlineMs`, construct a `createDeadlineSearch({ deadlineMs, baseSearch: mctsSearch })` per bot turn, pass it as `deps.search` to `selectBotMove`, and distinguish a deadline-cut resolution (commit the move) from a genuine outer cancel (discard the turn) per D-17 — the two-signal design means `useBotGame`'s existing `signal.aborted` check on its OWN outer controller continues to mean exactly "cancel" with no new branching required at that call site. No blockers for Plan 09.

## Self-Check: PASSED

- `[ -f frontend/src/lib/chessClock.ts ]` → FOUND
- `[ -f frontend/src/lib/engine/deadlineSearch.ts ]` → FOUND
- `[ -f frontend/src/lib/engine/__tests__/deadlineSearch.test.ts ]` → FOUND
- `git log --oneline --all | grep -E "2e2e2fff|2925a454"` → both commits FOUND
- `cd frontend && npx vitest run src/lib/__tests__/chessClock.test.ts src/lib/engine/__tests__/deadlineSearch.test.ts` → 23/23 passed
- `cd frontend && npx vitest run src/lib/engine/__tests__/` → 175/175 passed, no regression in the frozen engine suites
- `git diff --stat frontend/src/lib/engine/mctsSearch.ts frontend/src/lib/engine/selectBotMove.ts frontend/src/lib/engine/botBudget.ts` → empty (no changes)
- `npm run lint` on both new/changed files → clean (0 errors)
- `npx tsc -b` → 2 expected errors, both confined to `useBotGame.ts` (documented above, per-plan expected breakage); zero errors in `deadlineSearch.ts` or `chessClock.ts`

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-13*
