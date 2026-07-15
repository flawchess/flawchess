---
phase: 170-localstorage-resume
plan: 01
subsystem: frontend-lib
tags: [localstorage, chess.js, resume, bot-play, react-free]

# Dependency graph
requires:
  - phase: 169-clocked-board-game-loop-usebotgame
    provides: chessClock.ts's pause-aware chargeableElapsedMs family, useBotGame's honest-clock model
  - phase: 169.5-bot-opening-book
    provides: the one-way hasLeftBook latch (openingBook.ts) that this plan's snapshot payload persists
provides:
  - foldClockBasesForSnapshot — the single exported function expressing the D-01/D-02 leave/resume clock-fold asymmetry
  - botGameSnapshot.ts — versioned, owner-scoped, PGN-based in-progress snapshot module (readSnapshot/writeSnapshot/clearSnapshot/restoreChess)
  - botPendingStore.ts — bounded, owner-scoped, uuid-idempotent finished-game queue (enqueuePendingStore/listPendingStore/removePendingStore)
affects: [170-02, 170-03, 170-04, 170-05, resume-seam, store-once-drain]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "chess.pgn() as the single move+clock serialization format (D-08 RESOLVED — verified lossless [%clk] round-trip via chess.js 1.4.0's loadPgn)"
    - "Owner-scoped localStorage keys (`${prefix}${ownerKey ?? 'anon'}`) copied verbatim from useUserFlag.ts's storageKey"
    - "Capture-once-then-clear Sentry discipline for corrupted localStorage values (clear the bad key at first detection, never re-capture on subsequent reads)"

key-files:
  created:
    - frontend/src/lib/botGameSnapshot.ts
    - frontend/src/lib/botPendingStore.ts
    - frontend/src/lib/__tests__/botGameSnapshot.test.ts
    - frontend/src/lib/__tests__/botPendingStore.test.ts
  modified:
    - frontend/src/lib/chessClock.ts
    - frontend/src/lib/__tests__/chessClock.test.ts

key-decisions:
  - "D-08 RESOLVED: snapshot persists chess.pgn() (not SAN+clk-array) — chess.js 1.4.0 round-trips [%clk] comments losslessly, per 170-RESEARCH.md's empirical verification."
  - "BotGameSnapshot.version typed as `number` (not the literal `1`) per the plan task's explicit field list, even though RESEARCH.md/PATTERNS.md showed a `1` literal — the runtime hard-drop-on-mismatch behavior is identical either way."
  - "A clean version mismatch is a silent hard drop (no key removal, no Sentry capture) — distinct from a corruption failure (parse error / shape-validation failure), which DOES remove the key and capture once. This distinction was explicit in the plan's acceptance criteria and is asserted by a dedicated 'version' test group."
  - "botPendingStore.ts does NOT call Sentry.captureException on corruption — the plan's behavior/action spec for this module never mentions Sentry (unlike botGameSnapshot.ts's T-170-02 threat entry), so this was left out to avoid unspecified scope creep."

patterns-established:
  - "Fold rule lives in exactly one exported function (chessClock.ts's foldClockBasesForSnapshot) — later plans (Plan 04's useBotGame resume seam) must call it, never re-implement the D-01/D-02 branch."
  - "botGameSnapshot.restoreChess is the only snapshot->Chess replay path in the codebase — no parallel SAN-replay helper."

requirements-completed: [RESUME-01, RESUME-02]

coverage:
  - id: D1
    description: "foldClockBasesForSnapshot expresses the D-01/D-02 clock-fold asymmetry as a single pure function: folds the user's in-turn elapsed think time into their clock base, leaves the bot's base untouched on its own turn, clamps at zero, never mutates input."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/chessClock.test.ts#fold (Phase 170 D-01/D-02 leave/resume clock-fold asymmetry)"
        status: pass
    human_judgment: false
  - id: D2
    description: "botGameSnapshot.ts round-trips a mid-game chess.pgn() (with [%clk] comments for both colors) byte-identically through readSnapshot/writeSnapshot/restoreChess, and degrades corrupt/wrong-version/foreign-owner/storage-throw inputs to null without ever throwing."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#round-trip (D-08 acceptance gate)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#version"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#corrupt"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#owner"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#write/clear behavior"
        status: pass
    human_judgment: false
  - id: D3
    description: "botPendingStore.ts is a bounded (MAX_PENDING_STORE_ENTRIES=10, FIFO drop-oldest), owner-scoped, uuid-idempotent queue on a key physically separate from the in-progress snapshot — an unfinished game has no path into the queue."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botPendingStore.test.ts#store-once (SC2 structural invariant, D-12 separate key)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botPendingStore.test.ts#cap (T-170-03 bounded FIFO queue)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/botPendingStore.test.ts#basic queue operations"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-13
status: complete
---

# Phase 170 Plan 01: Snapshot + Pending-Store + Clock-Fold Primitives Summary

**Three pure, React-free primitives — foldClockBasesForSnapshot, botGameSnapshot.ts, botPendingStore.ts — that make RESUME-01's lossless resume and RESUME-02's store-once-and-only-once behavior structurally true, each proven by an actual revert -> red-test -> restore cycle.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-13
- **Tasks:** 3
- **Files modified:** 6 (2 modified, 4 created)

## Accomplishments
- `foldClockBasesForSnapshot` in `chessClock.ts`: the single exported function expressing the D-01/D-02 leave/resume clock-fold asymmetry (bill the user's in-turn think time, refund the bot's interrupted search).
- `botGameSnapshot.ts`: versioned, owner-scoped, PGN-based in-progress snapshot with `readSnapshot`/`writeSnapshot`/`clearSnapshot`/`restoreChess` — round-trips a mid-game position with every `[%clk]` comment byte-identical, and degrades corrupt/wrong-version/foreign-owner/storage-failure inputs to `null` without ever throwing.
- `botPendingStore.ts`: bounded (cap 10, FIFO drop-oldest), owner-scoped, uuid-idempotent finished-game queue on a key physically separate from the in-progress snapshot.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the D-01/D-02 clock-fold rule to chessClock.ts** - `182799e0` (feat)
2. **Task 2: botGameSnapshot.ts — versioned, owner-scoped, PGN-based in-progress snapshot** - `0f97dc53` (feat)
3. **Task 3: botPendingStore.ts — the bounded, owner-scoped finished-game queue** - `c2f8663c` (feat)

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified
- `frontend/src/lib/chessClock.ts` - added `foldClockBasesForSnapshot` (exported) and `foldElapsedIntoClockBase` (module-private helper)
- `frontend/src/lib/__tests__/chessClock.test.ts` - added the `fold` describe block (6 assertions)
- `frontend/src/lib/botGameSnapshot.ts` - new module: `CURRENT_SNAPSHOT_VERSION`, `BOT_GAME_SNAPSHOT_KEY_PREFIX`, `BotGameSnapshot` interface, `readSnapshot`/`writeSnapshot`/`clearSnapshot`/`restoreChess`
- `frontend/src/lib/__tests__/botGameSnapshot.test.ts` - new test file (10 tests: round-trip, version, corrupt, owner, write/clear)
- `frontend/src/lib/botPendingStore.ts` - new module: `BOT_PENDING_STORE_KEY_PREFIX`, `MAX_PENDING_STORE_ENTRIES`, `PendingStoreEntry` interface, `enqueuePendingStore`/`listPendingStore`/`removePendingStore`
- `frontend/src/lib/__tests__/botPendingStore.test.ts` - new test file (12 tests: basic ops, cap, store-once, owner, corruption)

## Decisions Made
- `BotGameSnapshot.version` typed as `number` (plan task's explicit field list), not the literal `1` shown in RESEARCH.md/PATTERNS.md — behaviorally identical (hard-drop-on-mismatch either way), just a looser type.
- A clean version mismatch is a silent hard drop (no removal, no Sentry) while a genuine corruption (parse failure, shape-validation failure) removes the bad key and captures to Sentry exactly once — this distinction was explicit in the plan's acceptance criteria (D-06 vs T-170-02) and is asserted by separate test groups (`version` vs `corrupt`).
- `botPendingStore.ts` intentionally has no Sentry capture on corruption — the plan's task 3 behavior/action spec never mentions it (unlike task 2's explicit T-170-02 requirement for `botGameSnapshot.ts`), so it was left out rather than added unprompted.

## Deviations from Plan

None - plan executed exactly as written. One test-authoring correction made during development (not a deviation from the plan's specified module behavior): the initial "store-once" revert-detector test for botPendingStore's separate-key invariant did not actually exercise a shared-key collision (it never enqueued anything before writing/clearing the snapshot), so the REVERT PROOF's first run passed even with the sabotaged shared prefix. A second, stronger test (`D-12 rationale, made concrete: a pending entry survives starting a brand-new in-progress game for the same owner`) was added, confirmed red under the sabotage, then confirmed green after restoring the real prefix. This is a test-quality fix within Task 3's own scope, not a change to module behavior.

## Revert Proofs

Per the plan's mutation-test discipline (Phase 169's "half-invariant" lesson), each invariant below was ACTUALLY reverted, the named test observed going red, and the mechanism restored + reconfirmed green.

1. **D-01/D-02 clock-fold asymmetry** (`foldClockBasesForSnapshot`, `chessClock.ts`)
   - **Mechanism reverted:** deleted the `if (activeColor !== userColor) { return { ...bases }; }` early-return branch, so the function always folds regardless of who is on move.
   - **Test that went red:** `frontend/src/lib/__tests__/chessClock.test.ts` > `fold (Phase 170 D-01/D-02 leave/resume clock-fold asymmetry)` > `` D-02: does NOT fold on the bot's turn — the bot's interrupted think is refunded, base written as of its last commit `` — failed with `{white: 300000, black: 260000}` vs expected `{white: 300000, black: 300000}`.
   - **Restored and reconfirmed green:** yes (`npm test -- src/lib/__tests__/chessClock.test.ts -t "fold"` → 6 passed).

2. **D-08 PGN round-trip** (`restoreChess`, `botGameSnapshot.ts`)
   - **Mechanism reverted:** changed `restoreChess` to `new Chess(new Chess().loadPgn(pgn).fen())` — a FEN-based restore (exactly the D-08 trap named in the plan).
   - **Test that went red:** `frontend/src/lib/__tests__/botGameSnapshot.test.ts` > `round-trip (D-08 acceptance gate)` > `restores a byte-identical pgn for a both-colors game with a [%clk] comment on every ply` — threw `TypeError: Cannot read properties of undefined (reading 'fen')` (chess.js 1.4.0's `loadPgn` returns `void`, so the FEN-based swap fails outright rather than just losing fidelity — an even sharper detector than anticipated).
   - **Restored and reconfirmed green:** yes (`npm test -- src/lib/__tests__/botGameSnapshot.test.ts` → 10 passed).

3. **D-12 separate-key invariant** (`BOT_PENDING_STORE_KEY_PREFIX`, `botPendingStore.ts`)
   - **Mechanism reverted:** set `BOT_PENDING_STORE_KEY_PREFIX` equal to `BOT_GAME_SNAPSHOT_KEY_PREFIX` (`'flawchess_bot_game:'`).
   - **Test that went red:** `frontend/src/lib/__tests__/botPendingStore.test.ts` > `store-once (SC2 structural invariant, D-12 separate key)` > `D-12 rationale, made concrete: a pending entry survives starting a brand-new in-progress game for the same owner` — failed with `[]` vs expected `['finished-game']` (the new in-progress snapshot write silently overwrote the enqueued pending entry, exactly the D-12 failure mode).
   - **Restored and reconfirmed green:** yes (`npm test -- src/lib/__tests__/botPendingStore.test.ts` → 12 passed).

## Issues Encountered
- The plan-suggested "store-once" test (write+clear a snapshot with an empty pending queue, assert the pending queue stays empty) does not actually detect a shared-key bug, since nothing was ever enqueued to be destroyed. Fixed by adding a second test that enqueues a pending entry first, then writes a new in-progress snapshot for the same owner, and asserts the pending entry survives — this is the test that genuinely proves D-12's stated rationale ("a failed store followed by a new game silently destroys the finished game forever").

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `foldClockBasesForSnapshot`, `botGameSnapshot.ts`, and `botPendingStore.ts` are ready for Plan 04's `useBotGame` resume seam (D-10) to consume directly — no further changes needed to these three modules for that integration.
- `BotGameSnapshot`/`PendingStoreEntry` both type-import `BotGameSettings` from `@/hooks/useBotGame` (type-only, zero runtime cycle) — Plan 04 can freely import from `botGameSnapshot.ts`/`botPendingStore.ts` without circularity concerns.
- No blockers. Full frontend suite (1957 tests across 153 files), `tsc -b`, `eslint`, and `knip` all green after this plan.

---
*Phase: 170-localstorage-resume*
*Completed: 2026-07-13*

## Self-Check: PASSED

All 5 created files verified present on disk; all 3 task commit hashes (`182799e0`, `0f97dc53`, `c2f8663c`) verified present in git log.
