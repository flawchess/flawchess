---
phase: 170-localstorage-resume
plan: 04
subsystem: frontend-hooks
tags: [react-hooks, localstorage, resume, bot-play, useBotGame, store-once]

# Dependency graph
requires:
  - phase: 170-01
    provides: botGameSnapshot.ts's readSnapshot/writeSnapshot/clearSnapshot/restoreChess, botPendingStore.ts's enqueuePendingStore/listPendingStore, chessClock.ts's foldClockBasesForSnapshot
  - phase: 170-03
    provides: the resume seam (resume?, ownerKey? params), the live/confirmLive gate, gameUuid as React state
provides:
  - "The wired persistence layer: useBotGame now writes/clears/enqueues at exactly four call sites"
  - "SC2 made STRUCTURAL: enqueuePendingStore has exactly one call site (finalizeGame), so an unfinished game has no reachable path to the server"
  - "The D-01/D-02 clock-fold asymmetry wired into a real tab-hide/pagehide effect (not just the pure chessClock.ts helper from Plan 01)"
affects: [170-05, resume-gate-ui, store-once-drain]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "buildSnapshot: a single useCallback assembling the BotGameSnapshot payload, called by both write sites (commitMove, the hide-time effect) with only the clock bases argument differing"
    - "The hide-time snapshot write lives in its OWN useEffect, declared immediately after the pre-existing []-deps pause-bookkeeping visibilitychange effect, with a real dependency array — never bolted onto the []-deps handler"
    - "Every-move and hide-time writes are both guarded by `if (live && !outcomeRef.current)` — a dormant resumed game and a terminal move never trigger a stray write"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts

key-decisions:
  - "Task 1 and Task 2 were split into two separate atomic commits (matching the plan's own two-task structure), unlike Plan 03's precedent of combining tightly-coupled tasks. This was verified safe up front: Task 1 (commitMove write + hide-time effect + buildSnapshot) and Task 2 (finalizeGame enqueue+clear + newGame clear) touch orthogonal call sites with no shared intermediate-compile-state risk — only the shared import block and file-header docblock needed a temporary Task-1-only wording, both cleanly restored to their final form in the Task 2 commit. Verified byte-for-byte: `git diff` of the two-commit split against the single-shot combined diff is empty."
  - "commitMove's explicit `if (live && !outcomeRef.current)` guard is kept even though the terminal-move `return` a few lines above already makes `outcomeRef.current` being set unreachable at that call site in the current code — per the plan's explicit instruction to keep the guard, not rely on that ordering alone as an invariant."
  - "The hide-time write always passes `chargeableElapsedMs()` to `foldClockBasesForSnapshot` (not a manually-branched `userIsActive ? chargeableElapsedMs() : 0` as RESEARCH.md's illustrative example did) — `foldClockBasesForSnapshot` (Plan 01) already owns the `activeColor !== userColor` branch internally, so duplicating that decision at the call site would be a second copy of the D-01/D-02 invariant."
  - "Reverted requirements.mark-complete's RESUME-01 checkbox flip: RESUME-01 is shared across Plans 04/05 (frontmatter) — 170-04 alone delivers the persistence half (snapshot on every move, fold on tab-hide); the SC1 'Resume game?' prompt is Plan 05's job. Left `[ ]` Pending in REQUIREMENTS.md with a partial-delivery note; Plan 05 actually closes it. RESUME-02 was already `[x]` Complete before this plan ran (a no-op `already_complete` on this run's `requirements.mark-complete` call) — not altered."

patterns-established:
  - "buildSnapshot is the ONE place a BotGameSnapshot payload is assembled from the hook's live refs/state — any future write site must call it, not re-derive the payload shape."

requirements-completed: [RESUME-02]  # RESUME-01's SC1 ("Resume game?" prompt) is Plan 05's job — left Pending, partial-delivery note recorded in STATE.md.

coverage:
  - id: D1
    description: "commitMove writes an in-progress snapshot after every committed move (no fold — the clock base is already settled), guarded off for a dormant resumed game and a terminal move."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#snapshot-write"
        status: pass
    human_judgment: false
  - id: D2
    description: "A dedicated visibilitychange(hidden)/pagehide effect writes a snapshot with the D-01/D-02 clock-fold asymmetry applied: the user's in-turn think time is billed, the bot's interrupted think is refunded (its base written unmodified). The live ref itself is never mutated by the fold."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#hide-fold"
        status: pass
    human_judgment: false
  - id: D3
    description: "finalizeGame enqueues the finished game to the pending-store queue and clears the in-progress snapshot; this is the ONLY enqueuePendingStore call site in the codebase, making SC2 (an abandoned game leaves no server trace) structural."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#finalize-enqueue"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#store-once"
        status: pass
    human_judgment: false
  - id: D4
    description: "newGame() clears the in-progress snapshot but deliberately does NOT touch the pending-store queue — a finished-but-not-yet-stored game survives starting a new one."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#newgame-pending-store"
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-07-13
status: complete
---

# Phase 170 Plan 04: Wire Persistence Writes into useBotGame Summary

**`useBotGame` now snapshots on every move, folds the D-01/D-02 clock asymmetry into a dedicated tab-hide/pagehide write, and enqueues-and-clears exactly once on game end — making RESUME-01's "persists on every move" and RESUME-02's "an abandoned game leaves no server trace" both structurally true, with all five revert proofs performed and confirmed.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-13
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- **Every-move snapshot write (D-01 primary path):** `commitMove` writes an in-progress snapshot as its last statement, using the already-settled post-increment clock base — no fold needed there. Guarded by `live && !outcomeRef.current` so a dormant resumed game or a terminal move never triggers a stray write.
- **Hide-time fold write (D-01/D-02):** a NEW `useEffect`, declared immediately after the pre-existing `[]`-deps pause-bookkeeping `visibilitychange` effect (so DOM listener registration order guarantees `pausedAtRef` is already set before this handler reads `chargeableElapsedMs()`). Registers BOTH `visibilitychange` (hidden) and `pagehide` — never `beforeunload`/`unload`. Computes `foldClockBasesForSnapshot(clockBaseRef.current, activeColor, settings.userColor, chargeableElapsedMs())` and writes the folded copy, never mutating the live ref.
- **`buildSnapshot`:** the single `useCallback` that assembles a `BotGameSnapshot` payload from `chessRef`, `gameUuid`, `settings`, `hasLeftBookRef`, `hasFiredLowTimeRef`, `movesSinceLastDeclineRef`, and `Date.now()` — both write sites differ only in which clock bases they pass.
- **Enqueue-and-clear on finish (SC2, structural):** `finalizeGame` now enqueues `{ gameUuid, pgn: finalPgn, settings, enqueuedAt }` to the pending-store queue and clears the in-progress snapshot, behind the existing `outcomeRef` first-outcome-wins latch. This is the ONLY `enqueuePendingStore` call site in the codebase (verified via `grep`) — the mechanism that makes "an abandoned game has no reachable path to the server" a structural property, not a convention.
- **`newGame()` clears the snapshot only** — explicitly does NOT call `removePendingStore`, so a finished-but-not-yet-stored game survives starting a new one.

## Task Commits

Each task was committed atomically:

1. **Task 1: Snapshot on every move, and on tab-hide with the D-01/D-02 fold** - `99299a92` (feat)
2. **Task 2: Enqueue-and-clear on game end; clear on new game** - `153868c1` (feat)

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified

- `frontend/src/hooks/useBotGame.ts` - `buildSnapshot` helper; `commitMove`'s every-move write; the new hide-time `visibilitychange`/`pagehide` effect; `finalizeGame`'s enqueue+clear; `newGame`'s clear-only; updated file-header docblock naming all four persistence call sites and the SC2 invariant.
- `frontend/src/hooks/__tests__/useBotGame.test.ts` - `snapshot-write` (3 tests), `hide-fold` (5 tests), `finalize-enqueue` (4 tests), `store-once` (1 test), `newgame-pending-store` (1 test) — 14 new tests, `localStorage.clear()` added to `beforeEach`.

## Decisions Made

- Task 1 and Task 2 were split into two separate atomic commits — verified byte-identical to a single combined diff via `git diff` comparison, since the two tasks touch orthogonal call sites (only the shared import block and file-header docblock needed temporary Task-1-scoped wording, restored to final form in the Task 2 commit).
- `commitMove`'s `if (live && !outcomeRef.current)` guard was kept explicit per the plan's instruction, even though the code's existing early `return` on a terminal move already makes `outcomeRef.current` unreachable-true at that call site today — the guard documents the invariant rather than relying on that ordering alone.
- The hide-time write always passes the real `chargeableElapsedMs()` to `foldClockBasesForSnapshot` rather than pre-branching on `userIsActive` at the call site — `foldClockBasesForSnapshot` (Plan 01) already owns that branch internally, so re-deriving it here would duplicate the D-01/D-02 invariant in a second place.

## Deviations from Plan

None — plan executed exactly as written. The only structural choice beyond the plan's literal text was splitting Task 1/Task 2 into two commits (a process decision, not a behavior deviation) — the resulting code is identical to what a single combined commit would have produced (verified via diff).

## Revert Proofs

Per the plan's mandatory mutation-test discipline (Phase 169's "half-invariant" lesson), each mechanism below was ACTUALLY reverted in the source, the named test observed going RED, and the mechanism restored + reconfirmed green.

1. **REVERT PROOF #1 — hide-time write passes unfolded bases** (`useBotGame.ts`, hide-time effect)
   - **Mechanism reverted:** replaced `writeSnapshot(ownerKey, buildSnapshot(folded))` (computed via `foldClockBasesForSnapshot`) with `writeSnapshot(ownerKey, buildSnapshot(clockBaseRef.current))` — the unfolded live bases.
   - **Tests that went red:** `hide-fold > D-01: bills the user's 40s...` (expected `whiteClockMs: 260_000`, got `300_000`) and `hide-fold > a pagehide event produces the same fold write...` (expected `260_000`, got `300_000`).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "hide-fold"` → 5 passed).

2. **REVERT PROOF #2 — hide-time write mutates the live clock base** (`useBotGame.ts`, hide-time effect)
   - **Mechanism reverted:** added `clockBaseRef.current = folded;` right after computing the fold, before `writeSnapshot`.
   - **Tests that went red:** `hide-fold > a duplicate hidden event...` (expected the second write's bases to equal the first's; `220_000` vs `260_000` — the live ref had already been folded once, so the second fold double-subtracted) and `hide-fold > does not mutate the live clock base...` (expected debit `< 45_000`, got `80_000` — the doubled debit).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "hide-fold"` → 5 passed).

3. **REVERT PROOF #3 — `writeSnapshot` removed from `commitMove`** (`useBotGame.ts`)
   - **Mechanism reverted:** deleted the `if (live && !outcomeRef.current) { writeSnapshot(...) }` block from `commitMove`.
   - **Tests that went red:** `snapshot-write > writes a snapshot after a user move...` (`readSnapshot(OWNER_KEY)` was `null`, expected non-null) and `snapshot-write > fires on EVERY committed move, including a bot reply...` (`TypeError: Cannot read properties of null`).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "snapshot-write"` → 3 passed).

4. **REVERT PROOF #4 — `enqueuePendingStore` moved from `finalizeGame` into `commitMove`** (`useBotGame.ts`)
   - **Mechanism reverted:** removed the enqueue call from `finalizeGame` and added an unconditional `enqueuePendingStore(ownerKey, { gameUuid, pgn: chessRef.current.pgn(), settings, enqueuedAt: Date.now() })` call inside `commitMove`, firing on every committed move regardless of outcome.
   - **Test that went red:** `store-once > an unfinished game leaves the pending-store queue EMPTY...` — failed with `[ { gameUuid: "...", pgn: "...", settings: {...}, enqueuedAt: 0 } ]` vs expected `[]` (a single unfinished move was queued).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "store-once"` → 1 passed).

5. **REVERT PROOF #5 — `clearSnapshot` removed from `finalizeGame`** (`useBotGame.ts`)
   - **Mechanism reverted:** deleted the `clearSnapshot(ownerKey);` call from `finalizeGame`.
   - **Tests that went red:** `finalize-enqueue > checkmate enqueues exactly one entry...` and `finalize-enqueue > resign enqueues exactly one entry...` — both failed on `expect(readSnapshot(OWNER_KEY)).toBeNull()`, receiving the full leftover snapshot object instead of `null`.
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "finalize-enqueue"` → 4 passed).

## Verification Performed

- `cd frontend && npm test -- src/hooks/__tests__/useBotGame.test.ts` → 61 passed (14 new: 3 snapshot-write + 5 hide-fold + 4 finalize-enqueue + 1 store-once + 1 newgame-pending-store; 47 pre-existing from Plans 03/169/169.5, all unmodified and green).
- `cd frontend && npm test` (full suite) → 154 files, 2001 tests, all passed.
- `cd frontend && npx tsc -b` → clean, zero errors.
- `cd frontend && npm run lint` → clean (0 errors; 3 pre-existing warnings in `coverage/` build artifacts, unrelated).
- `cd frontend && npm run knip` → clean, zero issues.
- Source assertions (per plan `<verification>`):
  - No `beforeunload`/`unload` listener anywhere in `useBotGame.ts` (only mentioned in an explanatory comment).
  - `enqueuePendingStore` appears at exactly ONE call site in `frontend/src/` outside its own module and its tests (`grep -rn "enqueuePendingStore(" src/ | grep -v __tests__ | grep -v botPendingStore.ts` → 1 hit, `useBotGame.ts:610`).
  - `newGame` does not call `removePendingStore` (only referenced in an explanatory comment).
  - The new hide-time effect's dependency array is `[live, activeColor, settings.userColor, ownerKey, chargeableElapsedMs, buildSnapshot]` (non-empty, includes `activeColor`).
  - The pre-existing pause-bookkeeping `visibilitychange` effect (line ~980) still has `[]` deps, unmodified.
- All FIVE revert proofs performed and recorded above with the exact test name that went red for each.

## Known Stubs

None — this plan wires real persistence into a real game loop; no data source is stubbed.

## Threat Flags

None beyond what the plan's own `<threat_model>` already registered (T-170-09, T-170-02, T-170-10, T-170-01) — no new security-relevant surface introduced. T-170-09 (the plan's one high-severity threat: a second `enqueuePendingStore` call site) is fully mitigated, proven by the `store-once` test and the source-assertion grep above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `useBotGame`'s persistence layer is complete: a game survives a snapshot round-trip on every move and on tab-hide with correct clock fairness, and a finished game reaches the pending-store queue exactly once, with an unfinished game structurally unable to reach it at all.
- Plan 05 (the resume-gate UI component on `/bots`) can now wire `confirmLive()` and the snapshot-detection mount effect against a fully-functional persistence backend — no further changes to `useBotGame.ts`'s persistence call sites are expected for that plan.
- No blockers. Full frontend suite (2001 tests across 154 files), `tsc -b`, `eslint`, and `knip` all green after this plan.

---
*Phase: 170-localstorage-resume*
*Completed: 2026-07-13*

## Self-Check: PASSED

`frontend/src/hooks/useBotGame.ts` and `frontend/src/hooks/__tests__/useBotGame.test.ts` verified present and modified on disk; commit hashes `99299a92` and `153868c1` verified present in git log.
