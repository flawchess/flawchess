---
phase: 170-localstorage-resume
plan: 03
subsystem: frontend-hooks
tags: [react-hooks, resume, bot-play, useBotGame, live-gate]

# Dependency graph
requires:
  - phase: 170-01
    provides: botGameSnapshot.ts's BotGameSnapshot type + restoreChess() (the PGN-based produce/consume path), foldClockBasesForSnapshot
provides:
  - "useBotGame(settings, resume?, ownerKey?): UseBotGameState — the resume seam every 11 ref/state values seed from"
  - "gameUuid on UseBotGameState — stable per-game id, minted once, re-minted only by newGame()"
  - "live/confirmLive on UseBotGameState — the D-03 prewarm gate"
affects: [170-04, 170-05, resume-gate-ui, store-once-drain]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy useState(() => computeOnce()) for a one-time expensive render-phase computation, NOT a manually-cached ref — react-hooks/refs (react-hooks 7.1.1) forbids reading .current during render, and any ref-derived value later exposed in the return object trips this rule"
    - "gameUuid modeled as useState (not useRef) for the same react-hooks/refs reason — anything surfaced in UseBotGameState's return object during render cannot be sourced from a ref"
    - "live gate: exactly 3 effects (turn-anchor, clock-tick, bot-turn-trigger) gated by `if (!live) return;` + `live` in deps; the provider bring-up effect stays unconditional `[]` deps — this is the whole D-03 mechanism"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts

key-decisions:
  - "gameUuid modeled as React state, not a useRef as the plan's action text literally specified — react-hooks/refs (a lint rule new in react-hooks 7.1.1, already flagged as project-relevant in eslint.config.js's own comment for a sibling rule) forbids reading ref.current during render, and exposing gameUuid on the hook's return object IS a render-phase read. useState gives byte-identical external behavior (mint once, re-mint only in newGame()) with zero lint violation. Documented here per CLAUDE.md's 'lint clean' hard gate taking precedence over the plan's literal wording (Rule 3 auto-fix)."
  - "The resume->Chess/history one-time computation (initFromResume) is cached via a lazy useState(() => ...) initializer, not a manually-cached ref-with-undefined-sentinel as the plan's action text suggested — same react-hooks/refs reason; every downstream seed (viewedPlyRef, liveGamePlyRef, moveHistory state, activeColor state) reads the cached STATE value during render, which is unrestricted."
  - "Task 1 and Task 2 committed together in a single commit — the refs/state block, the newGame() callback, and the return statement are physically interleaved by both tasks (e.g. `live` and `gameUuid` state declared adjacently), so a clean hunk-level split into two atomic commits would risk a broken intermediate compile state. Matches this project's own precedent for tightly-coupled task pairs (STATE.md: '[Phase 155-04]: Combined Task 1+2 into one commit')."

patterns-established:
  - "A resumed hook mounts with live=false; confirmLive() is the caller's explicit 'go' signal — Plan 05's resume gate UI wires its Resume button to this."
  - "movesSinceLastDeclineRef mirrors movesSinceLastDecline state via the same sync-effect pattern liveGamePlyRef already used — Plan 04's snapshot-write effects read this ref, not the state, to avoid depending on (and re-running per) the state itself."

requirements-completed: []  # RESUME-01/RESUME-02 are multi-plan (170-01/03/04/05); left pending here, closed at the phase's final plan per this project's established partial-delivery convention.

coverage:
  - id: D1
    description: "useBotGame(settings, resume?, ownerKey?) restores a game from a snapshot: position, move stack, clocks, and every latch — through ONE hook and ONE game loop (initFromResume is the single snapshot->board replay call site)."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resume-seed"
        status: pass
    human_judgment: false
  - id: D2
    description: "hasLeftBook, hasFiredLowTime, and movesSinceLastDecline each individually survive a resume — proven by an actual revert -> named-red-test -> restore cycle for each, not a grep or symbol-presence check."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resume-seed > hasLeftBook seed survives a resume"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resume-seed > movesSinceLastDecline seed survives a resume"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resume-seed > hasFiredLowTime seed survives a resume"
        status: pass
    human_judgment: false
  - id: D3
    description: "Clock bases after restore equal the snapshot's bases exactly regardless of wall-clock time elapsed since savedAt — no away-time is billed."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#no-away-time"
        status: pass
    human_judgment: false
  - id: D4
    description: "gameUuid is minted once at game start, stable across a resume, and re-minted ONLY by newGame() — keeps the server's uq_games_user_platform_game_id idempotency reachable across a resume (T-170-07, the phase's one high-severity threat, fully mitigated)."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#stable-uuid"
        status: pass
    human_judgment: false
  - id: D5
    description: "A resumed game restored on the bot's turn runs zero engine searches and zero clock ticks until confirmLive() — but the provider bring-up effect (pool.warm/queue.warm/ECO fetch) starts immediately on mount, proven in BOTH directions (over-gating and under-gating) via two dedicated revert proofs against the bot-turn-trigger effect and the provider bring-up effect respectively."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#prewarm-gate"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-07-13
status: complete
---

# Phase 170 Plan 03: Resume Seam + Live Gate in useBotGame Summary

**`useBotGame(settings, resume?, ownerKey?)` now restores an in-progress bot game through one hook and one game loop, with all 11 ref/state values individually revert-proven, and a `live`/`confirmLive` gate that warms the engines instantly on a resumed mount while holding the clock and the bot's search until the caller confirms.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-13
- **Tasks:** 2 (committed together — see Deviations)
- **Files modified:** 2

## Accomplishments

- **Resume seam (D-10):** `useBotGame` accepts an optional `resume?: BotGameSnapshot` and `ownerKey?: string | null` (the latter unused by this plan, reserved for Plan 04). Every one of the 11 documented ref/state values seeds from the snapshot via `initFromResume` — a single PGN replay cached once per mount, not once per re-render (this hook re-renders on every 100ms clock tick, so re-replaying the PGN on every tick would have been a real perf bug).
- **`gameUuid` (D-11):** minted once via `crypto.randomUUID()` at game start, carried unchanged through a resume, re-minted ONLY by `newGame()`. This is the mechanism that keeps the server's `uq_games_user_platform_game_id` idempotency reachable across a resume — the phase's one high-severity threat (T-170-07), fully mitigated and proven by the `stable-uuid` test group.
- **`live`/`confirmLive` gate (D-03):** a resumed game mounts with `live: false`. The turn-anchor, clock-tick, and bot-turn-trigger effects each gained an `if (!live) return;` guard plus `live` in their dependency array. The provider bring-up effect (`pool.warm()`/`queue.warm()`/ECO prefix fetch) stays deliberately UNCONDITIONAL with `[]` deps and unguarded — a large comment block explains why a future reader must not "tidy" this into the gate (it would defeat D-03 entirely, since `WorkerPool`/`MaiaQueue` have no life outside this hook's own effect).
- **Zero behavior change on the fresh-game path:** `live` defaults to `resume === undefined`, so a fresh game is live from mount exactly as before. The entire pre-existing 42-test suite (turn-gate, pacing, end-conditions, resign-draw, pgn-export, bot-clock, cancel, hidden-tab, book, finalize-idempotency) passed unmodified throughout.

## Task Commits

Task 1 (resume seam) and Task 2 (live gate) were committed together — see Deviations for why.

1. **Task 1 + Task 2: Resume seam + live gate** - `34d3ec91` (feat)

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified

- `frontend/src/hooks/useBotGame.ts` - resume/ownerKey params, `initFromResume` module helper, 11 seeded refs/state, `gameUuidRef`→state, `movesSinceLastDeclineRef` mirror, `live`/`confirmLive`, 3 gated effects, `newGame()` re-mints uuid + sets live true, `gameUuid`/`live`/`confirmLive` on `UseBotGameState`
- `frontend/src/hooks/__tests__/useBotGame.test.ts` - `resume-seed` (7 tests), `no-away-time` (2 tests), `stable-uuid` (1 test), `prewarm-gate` (5 tests) groups; `buildResumeSnapshot` fixture builder (drives real chess.js + production `annotateClock`, never a hand-typed PGN string, per the plan's explicit instruction)

## Decisions Made

- **`gameUuid` modeled as `useState`, not `useRef`** as the plan's action text literally specified. `eslint-plugin-react-hooks`'s `react-hooks/refs` rule (new in 7.1.1 — the project's `eslint.config.js` already has a dated comment acknowledging a sibling rule from the same release) forbids reading `ref.current` during render, and exposing `gameUuid` on the hook's return object is unavoidably a render-phase read. `useState` gives byte-identical external behavior (mint once at mount, re-mint only in `newGame()`) with zero lint violation — verified via `npm run lint` clean. This is a Rule 3 auto-fix (CLAUDE.md's `npm run lint` clean gate is a hard verification requirement that takes precedence over the plan's literal implementation detail; the plan's *behavior* contract — "expose `gameUuid: string`, mint once, re-mint only in `newGame()`" — is preserved exactly).
- **`initFromResume`'s one-time PGN replay cached via a lazy `useState(() => ...)` initializer**, not the plan's suggested manually-cached-ref-with-undefined-sentinel pattern — same `react-hooks/refs` reason: `viewedPlyRef`, `liveGamePlyRef`, and the `moveHistory`/`activeColor` state initializers all need to read the cached restored-board data during render, which is disallowed from a ref but is the exact intended use of a lazy `useState` initializer.
- **Task 1 and Task 2 committed together**, not as two atomic per-task commits. The refs/state block, `newGame()`, and the return statement are physically interleaved by both tasks (e.g. the `live` and `gameUuid` state declarations sit adjacent to each other, both touched while fixing the lint violation above). A clean hunk-level split risked a broken intermediate compile state. This project has an established precedent for this exact situation (STATE.md: "[Phase 155-04]: Combined Task 1+2 into one commit — ... a Task-1-only commit would fail its own tsc --noEmit gate").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `gameUuidRef`/`restoredRef` (manual ref-cache pattern) violated `react-hooks/refs`**

- **Found during:** Task 1/2 implementation, first `npm run lint` run.
- **Issue:** The plan's literal action text specifies `gameUuidRef = useRef<string>(...)` exposed directly in the return statement (`gameUuid: gameUuidRef.current`), and a manually-cached ref (`restoredRef.current === undefined ? ... : ...`) for the one-time snapshot->board replay. Both trip `eslint-plugin-react-hooks`'s `react-hooks/refs` rule ("Cannot access refs during render") — 8 errors on the first `npm run lint` run, all tracing back to these two ref reads (directly, or via every derived value like `restoredLivePly`).
- **Fix:** Converted both to `useState`: `gameUuid` is now `useState<string>(() => resume?.gameUuid ?? crypto.randomUUID())` with `setGameUuid` called in `newGame()`; the restored-board cache is `useState(() => initFromResume(resume))`, a standard React lazy-initializer pattern that computes exactly once (React's documented guarantee) without ever reading `.current` during render.
- **Files modified:** `frontend/src/hooks/useBotGame.ts`
- **Commit:** `34d3ec91`

Other than this necessary lint-driven substitution, plan executed as written — every seed table row, both effect gates, and the return-surface additions match the plan's `<action>` spec exactly.

## Revert Proofs

Per the plan's mandatory mutation-test discipline (Phase 169's "half-invariant" lesson — a rule enforced in one place but bypassed in another is invisible to tsc/eslint/knip/a passing suite), each of the five required mechanisms below was ACTUALLY reverted in the source, the named test observed going RED, and the mechanism restored + reconfirmed green. No revert used a grep or symbol-presence check.

1. **REVERT PROOF #1 — `hasLeftBookRef` resume seed** (`useBotGame.ts`)
   - **Mechanism reverted:** `const hasLeftBookRef = useRef(resume?.hasLeftBook ?? false);` → `const hasLeftBookRef = useRef(false);`
   - **Test that went red:** `resume-seed > hasLeftBook seed survives a resume — the bot searches instead of consulting the book on its next turn` — failed with `expected "vi.fn()" to not be called at all, but actually been called 1 times` (`mockPolicy`, i.e. the book's `queue.policy` call, fired — proving the book was consulted instead of skipped).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useBotGame.test.ts -t "hasLeftBook seed"` → 1 passed).

2. **REVERT PROOF #2 — `movesSinceLastDecline` resume seed** (`useBotGame.ts`)
   - **Mechanism reverted:** `useState(resume?.movesSinceLastDecline ?? DRAW_OFFER_COOLDOWN_MOVES)` → `useState(DRAW_OFFER_COOLDOWN_MOVES)`.
   - **Test that went red:** `resume-seed > movesSinceLastDecline seed survives a resume — canOfferDraw is false immediately, no confirmLive() needed` — failed with `expected true to be false` (the resumed cooldown was silently reset, making an immediate draw offer possible again).
   - **Restored and reconfirmed green:** yes (1 passed).

3. **REVERT PROOF #3 — `hasFiredLowTimeRef` resume seed** (`useBotGame.ts`)
   - **Mechanism reverted:** `const hasFiredLowTimeRef = useRef(resume?.hasFiredLowTime ?? false);` → `const hasFiredLowTimeRef = useRef(false);`
   - **Test that went red:** `resume-seed > hasFiredLowTime seed survives a resume — the low-time sound does not re-fire when the threshold is crossed again` — failed with `expected "vi.fn()" to not be called with arguments: [ 'low-time' ]` (the sound fired again on a resumed game that had already played it once this game).
   - **Restored and reconfirmed green:** yes (1 passed).

4. **REVERT PROOF #4 — bot-turn-trigger effect's `live` guard (under-gating direction)** (`useBotGame.ts`)
   - **Mechanism reverted:** commented out `if (!live) return;` inside the bot-turn-trigger effect (deps array left with `live` still present, so this genuinely isolates only the guard).
   - **Test that went red:** `prewarm-gate > a bot-to-move resume runs zero searches and freezes the bot clock before confirmLive()...` — failed with `expected "vi.fn()" to not be called at all, but actually been called 1 times` (`mockSelectBotMove` fired the instant the resumed-on-the-bot's-turn hook mounted, before `confirmLive()` was ever called — exactly the sharp bug D-03 exists to close).
   - **Restored and reconfirmed green:** yes (1 passed).

5. **REVERT PROOF #5 — provider bring-up effect gated (over-gating direction, "the mistake a future reader is most likely to make")** (`useBotGame.ts`)
   - **Mechanism reverted:** ADDED `if (!live) return;` to the top of the provider bring-up effect (still `[]` deps, unchanged).
   - **Test that went red:** `prewarm-gate > the providers warm BEFORE confirmLive() on a resumed mount — D-03 mechanism 1 is deliberately NOT gated` — failed with `expected "vi.fn()" to be called 1 times, but got 0 times` (`pool.warm`/`queue.warm` never fired on a resumed mount — and because the effect's deps stay `[]`, this failure mode is unrecoverable even after a later `confirmLive()`, an even sharper demonstration of why this effect must never be gated).
   - **Restored and reconfirmed green:** yes (1 passed).

Both directions of the `live` gate (under-gating via #4, over-gating via #5) are proven, and all three seed-survival latches (#1, #2, #3) are proven individually — matching the plan's explicit acceptance criteria and the phase's mutation-test discipline in full.

## Verification Performed

- `cd frontend && npm test -- src/hooks/__tests__/useBotGame.test.ts` → 47 passed (7 resume-seed + 2 no-away-time + 1 stable-uuid + 5 prewarm-gate = 15 new; 32 pre-existing, all unmodified and green).
- `cd frontend && npm test` (full suite) → 154 files, 1987 tests, all passed.
- `cd frontend && npx tsc -b` → clean, zero errors.
- `cd frontend && npm run lint` → clean (0 errors; 3 pre-existing warnings in `coverage/` build artifacts, unrelated).
- `cd frontend && npm run knip` → clean, zero issues.
- Source assertion (per plan `<verification>`): the provider bring-up effect's dependency array is still `[]` and carries no `live` guard — confirmed by direct inspection (`sed -n '892,924p' useBotGame.ts`) after the revert-proof restoration.

## Known Stubs

None — this plan touches only `useBotGame.ts`'s internal seam/gate; no UI, no data source stubs.

## Threat Flags

None beyond what the plan's own `<threat_model>` already registered (T-170-02, T-170-08, T-170-07) — no new security-relevant surface was introduced. T-170-07 (the phase's one high-severity threat, `gameUuid` re-minting on resume) is fully mitigated as designed, proven by the `stable-uuid` test group.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `useBotGame(settings, resume?, ownerKey?)`'s public signature is now settled — Plan 04 (snapshot-write effects) can add `ownerKey`-driven `writeSnapshot()` calls without touching the signature again. `movesSinceLastDeclineRef` was added specifically so Plan 04's write-on-hide handler has a fresh, non-reactive read of the draw-cooldown counter.
- `live`/`confirmLive` are ready for Plan 05's resume-gate UI component to wire directly (`onClick={() => game.confirmLive()}` on the Resume button).
- `gameUuid` is ready for Plan 04's pending-store enqueue (`finalizeGame` → `enqueuePendingStore({ gameUuid, ... })`) and the eventual `POST /bots/games` call.
- No blockers. Full frontend suite (1987 tests across 154 files), `tsc -b`, `eslint`, and `knip` all green after this plan.

---
*Phase: 170-localstorage-resume*
*Completed: 2026-07-13*

## Self-Check: PASSED

`frontend/src/hooks/useBotGame.ts` and `frontend/src/hooks/__tests__/useBotGame.test.ts` verified present and modified on disk; commit `34d3ec91` verified present in git log.
