---
phase: 170-localstorage-resume
plan: 05
subsystem: frontend-ui
tags: [react, resume, bot-play, dialog, localstorage, tanstack-query]

# Dependency graph
requires:
  - phase: 170-01
    provides: botGameSnapshot.ts's BotGameSnapshot type + readSnapshot/clearSnapshot
  - phase: 170-02
    provides: useDrainPendingStore (the queue-drain hook mounted on /bots)
  - phase: 170-03
    provides: useBotGame's resume/ownerKey seam and the live/confirmLive gate
  - phase: 170-04
    provides: the wired persistence layer (snapshot-on-move, hide-time fold, enqueue-on-finish)
provides:
  - ResumeGate.tsx — the "Resume game?" overlay component (identity line, Resume/Discard, D-05 discard confirm)
  - Bots.tsx restructured into BotsPage (owner-scope resolution, boot-once snapshot read, silent queue drain) + BotsGame (the game body, generalized off BOT_GAME_SETTINGS)
  - The full RESUME-01 user-facing loop: snapshot detected → gate renders → Resume/Discard → live game or fresh game
affects: [171-bots-setup-screen]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-dismissible Dialog (open literal true, onOpenChange no-op, showCloseButton=false) for a gate that must not be bypassed by Escape/outside-click"
    - "Two sibling Dialogs (gate + nested discard-confirm) rather than physically nesting JSX, mirroring GameControls.tsx's flat resign-confirm shape"
    - "Lazy useState(() => Date.now()) to satisfy react-hooks/purity when a component needs one impure read at mount, not a live-ticking clock"
    - "Boot-state + key-changed remount (BotsPage's `{ resume, nonce }` state) to force a full BotsGame remount with a real resume: null on discard, instead of reusing the live hook instance's newGame()"

key-files:
  created:
    - frontend/src/components/bots/ResumeGate.tsx
    - frontend/src/components/bots/__tests__/ResumeGate.test.tsx
  modified:
    - frontend/src/pages/Bots.tsx

key-decisions:
  - "formatTcLabel/formatRelativeAge are module-private, pure, and take no toBackendTcStr dependency — a fresh human-label formatter per the plan's explicit instruction (the wire format must never leak into UI copy)."
  - "Date.now() moved into a lazy useState(() => Date.now()) initializer inside ResumeGate rather than called directly during render — react-hooks/purity (eslint-plugin-react-hooks, new rule this project already tripped in Plan 03) flags a bare Date.now() read at render as impure. A single mount-time snapshot is correct per D-06 (no live-ticking age display is required)."
  - "Test assertions use .toBeNull()/.not.toBeNull() instead of @testing-library/jest-dom's toBeInTheDocument() — this project has no jest-dom setup (grep confirmed zero prior usage across the whole frontend test suite); matched the codebase's existing convention instead of adding a new dependency."
  - "handleDiscard uses a functional setBoot((prev) => ({ resume: null, nonce: (prev?.nonce ?? 0) + 1 })) rather than closing over a bare boot.nonce, so the callback itself does not need boot as a dependency."

patterns-established:
  - "ResumeGate.tsx is the ONE resume-gate component — Phase 171 reuses it unchanged; only the no-snapshot branch (BOT_GAME_SETTINGS auto-start) is Phase 171's to replace."

requirements-completed: [RESUME-01]  # RESUME-02 was already closed by Plan 04.

coverage:
  - id: D1
    description: "ResumeGate renders the game identity line (TC label, bot ELO, move count, relative age), Resume calls onResume exactly once with no dialog, Discard opens a confirm dialog WITHOUT calling onDiscard, confirming the dialog calls onDiscard exactly once, and cancelling calls onDiscard zero times."
    requirement: "RESUME-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/ResumeGate.test.tsx (15 tests: identity line, resume, discard-opens-dialog, discard-confirm, discard-cancel, formatRelativeAge x7, formatTcLabel x3)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bots.tsx: owner-scope resolved from useUserProfile().data?.email before the snapshot is read (T-170-04 ordering trap); the pending-store drain fires exactly once via a ref guard, independently of the gate; discard clears only the in-progress snapshot (never the pending-store queue) and remounts BotsGame with resume: null via a changed key; ResumeGate renders only while resume !== null && !game.live, overlaying an already-mounted (engine-warming) board."
    requirement: "RESUME-01"
    verification:
      - kind: other
        ref: "source assertions (grep, see Issues Encountered) + npx tsc -b + npm run lint + npm run knip all clean + full frontend suite (npm test -- --run) 2016/2016 passed across 155 files"
        status: pass
    human_judgment: true
    rationale: "tsc/lint/knip/the full test suite prove the wiring compiles and does not regress any existing behavior, and grep-based source assertions confirm the structural invariants (no removePendingStore in Bots.tsx, no beforeunload, no text-xs, no variant=secondary). But no automated test exercises Bots.tsx's actual boot sequence in a real browser (position/clock restoration, the gate rendering over a live board, the mobile layout) — that requires the Task 3 human-verify checkpoint below, which has not yet been run by a human."
  - id: D3
    description: "The full end-to-end resume + store-once loop (SC1: resume restores position/clocks with no away-time billed; SC2: an abandoned game leaves no server trace; SC3: a finished game is stored exactly once across reloads) verified live in a browser per the plan's 7-step checkpoint."
    human_judgment: true
    verification: []
    rationale: "This is the plan's own blocking human-verify checkpoint (Task 3). Auto-approved to keep the --auto chain moving per this execution's checkpoint_policy, but NOT actually clicked through by a human yet — see 'Human Verification Checklist' below for the exact steps a human must still run."

# Metrics
duration: ~20min
completed: 2026-07-13
status: complete
---

# Phase 170 Plan 05: Resume Gate UI + Bots.tsx Wiring Summary

**The "Resume game?" gate (`ResumeGate.tsx`) and `Bots.tsx`'s restructuring into `BotsPage` (owner-scope resolution, boot-once snapshot read, silent pending-store drain) + `BotsGame` (the game body, generalized off the D-14 stub) — the user-facing half that makes SC1 observable inside Phase 170.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-13
- **Tasks:** 2 automated tasks + 1 blocking human-verify checkpoint (auto-approved, not yet human-run)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `ResumeGate.tsx`: a non-dismissible `Dialog` overlay (no close affordance, `onOpenChange` ignores close attempts) showing the resumable game's identity line — TC label, bot ELO, move count, relative age (e.g. "Blitz 5+3 vs FlawChess Bot (1500) · 14 moves · 2 days ago") — with Resume (`variant="default"`) and Discard (`variant="brand-outline"`) actions. Discard opens a `GameControls`-style confirm dialog first (D-05): "This game will be lost — unfinished games are never saved," with Cancel (`variant="outline"`) and a destructive-colored Discard confirm.
- `formatTcLabel`/`formatRelativeAge`: pure, module-private helpers with named threshold constants (`BULLET_MAX_SECONDS`, `BLITZ_MAX_SECONDS`, `RAPID_MAX_SECONDS`, `MOVES_PER_GAME_ESTIMATE`, `MS_PER_MINUTE`/`MS_PER_HOUR`/`MS_PER_DAY`) — no magic numbers, no `toBackendTcStr` dependency (the wire format never leaks into UI copy), no `Chess` instance construction (move count comes in as a prop, not a second PGN replay).
- `Bots.tsx` restructured: `BotsPage` (default export, unchanged for `React.lazy`) resolves the localStorage owner key from `useUserProfile().data?.email`, waits for the profile to settle before reading the snapshot (`readSnapshot`), renders a `bots-page-loading` placeholder while booting, drains the pending-store queue exactly once via a ref guard (`useDrainPendingStore`), and remounts `BotsGame` with a changed `key` on discard. `BotsGame` is today's game body generalized off the hardcoded `BOT_GAME_SETTINGS` constant to a per-instance `settings = resume?.settings ?? BOT_GAME_SETTINGS`, rendering `ResumeGate` whenever `resume !== null && !game.live`.
- Zero behavior change on the no-snapshot path: `BotsGame` mounts with `resume: null`, `settings` falls back to `BOT_GAME_SETTINGS`, and `useBotGame`'s own `live` default (`resume === undefined`) keeps the D-14 stub auto-start exactly as before.

## Task Commits

Each task was committed atomically:

1. **Task 1: ResumeGate component** - `a88d6891` (feat)
2. **Task 2: Bots.tsx — owner scope, snapshot detection, gate overlay, queue drain** - `3756148f` (feat)
3. **Task 3: Human verification (blocking checkpoint)** - not yet run by a human; see below.

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified

- `frontend/src/components/bots/ResumeGate.tsx` - new component: identity line, Resume/Discard, D-05 confirm dialog, `formatTcLabel`/`formatRelativeAge` helpers
- `frontend/src/components/bots/__tests__/ResumeGate.test.tsx` - new test file (15 tests)
- `frontend/src/pages/Bots.tsx` - restructured into `BotsPage` + `BotsGame`; `GamePanel` gained a `userColor` prop (no longer reads the module-level `BOT_GAME_SETTINGS` constant directly)

## Decisions Made

- `formatTcLabel`/`formatRelativeAge` are module-private pure functions inside `ResumeGate.tsx`, not extracted to a shared lib — the plan scoped them to this component only, and no other surface in the codebase currently needs a bucketed "Blitz 5+3"-style human label (the existing `formatTimeControl.ts` produces a different, bucket-less "5+3" shape for game cards).
- `Date.now()` moved into a lazy `useState(() => Date.now())` initializer — `react-hooks/purity` flags a bare `Date.now()` read at render as impure (the same class of lint rule Plan 03 already worked around for `gameUuid`/`initFromResume`). A single mount-time snapshot is correct per D-06 (age display does not need to live-tick).
- Test assertions use `.toBeNull()`/`.not.toBeNull()` rather than `@testing-library/jest-dom`'s `toBeInTheDocument()` — grep confirmed zero prior usage of that matcher anywhere in the frontend suite (no `jest-dom` setup exists), so the test file follows the codebase's actual established convention (`Analysis.test.tsx`, `Endgames.readinessGate.test.tsx`, etc.) instead of introducing a new dependency mid-plan.
- `handleDiscard` in `BotsPage` uses a functional `setBoot((prev) => ...)` update rather than closing over `boot.nonce` directly, so the callback's own dependency array only needs `ownerKey`.

## Deviations from Plan

None — plan executed exactly as written. Two lint-driven test-authoring corrections (not behavior deviations, see Decisions above): the `Date.now()` purity fix and the `jest-dom` matcher substitution, both caught by `npm run lint` / `npm test` on the first run and fixed before any commit.

## Issues Encountered

- Initial `npm run lint` run flagged `Cannot call impure function during render` on `ResumeGate.tsx`'s `Date.now()` call — fixed via a lazy `useState` initializer (see Decisions).
- Initial `npm test` run for `ResumeGate.test.tsx` failed 4/15 tests with `Invalid Chai property: toBeInTheDocument` — this project has no `jest-dom` matcher setup; fixed by switching to `.toBeNull()`/`.not.toBeNull()`, matching every other `queryByTestId`-based presence/absence assertion in the codebase.
- Source assertions performed via direct `grep` (not just prose claims):
  - `grep -n "removePendingStore" src/pages/Bots.tsx` → no matches (discard never touches the pending-store queue).
  - `grep -n "text-xs" src/pages/Bots.tsx src/components/bots/ResumeGate.tsx` → no matches.
  - `grep -n 'variant="secondary"' src/pages/Bots.tsx src/components/bots/ResumeGate.tsx` → no matches.
  - `grep -n "beforeunload" src/pages/Bots.tsx` → no matches.
  - `grep -n "toBackendTcStr\|new Chess" src/components/bots/ResumeGate.tsx` → only in doc comments explaining why they are NOT imported/constructed, not real usages.

## Verification Performed

- `cd frontend && npm test -- src/components/bots/__tests__/ResumeGate.test.tsx` → 15/15 passed.
- `cd frontend && npx tsc -b` → clean, zero errors.
- `cd frontend && npm run lint` → clean (0 errors; 3 pre-existing warnings in `coverage/` build artifacts, unrelated).
- `cd frontend && npm run knip` → clean, zero issues.
- `cd frontend && npm test -- --run` (full suite) → **155 files, 2016 tests, all passed** (up from 154 files / 2001 tests before this plan — the 14-test delta is `ResumeGate.test.tsx` minus one test consolidated during authoring... actual delta is 15 new tests across 1 new file).
- All acceptance-criteria source assertions (grep-based) confirmed above.

## Known Stubs

None — no data source is stubbed. Both `ResumeGate.tsx` and the `Bots.tsx` restructuring wire real, already-shipped persistence (Plans 01-04) end to end.

## Threat Flags

None beyond what the plan's own `<threat_model>` already registered (T-170-04, T-170-11, T-170-02, T-170-12) — no new security-relevant surface introduced. T-170-04 (cross-user snapshot leakage on a shared browser) is mitigated exactly as designed: `Bots.tsx` resolves `ownerKey` from `useUserProfile().data?.email` and waits for the profile to settle (`!isLoading`) before the first `readSnapshot` call — confirmed by direct inspection of the boot effect's guard.

## Human Verification Checklist (Task 3 — NOT YET run by a human)

This plan is `autonomous: false` and ends in a blocking `checkpoint:human-verify`. Per this execution's `--auto` chain policy, the checkpoint was **auto-approved to keep the chain moving** — it has **NOT** been clicked through by a human yet. The exact steps below must still be performed by the user in a real browser before this phase's SC1/SC2/SC3 are actually confirmed:

1. **Resume + no away-time billed (SC1).** Visit `/bots`, play 3-4 moves, note both clocks. Close the tab. Wait at least 60 seconds. Reopen `/bots`. Expect: a "Resume game?" gate showing the correct TC/bot ELO/move count/age, no game running behind it (neither clock ticking), and clicking Resume restores the exact position with both clocks at what they read when you closed the tab (minus at most your own already-spent think time, never the 60+ seconds away).
2. **Think time IS billed (D-01).** Start a fresh game (Discard → confirm). Play one move. On your next turn, sit ~30s, close the tab, reopen. Expect: on Resume, your clock is ~30s lower than at the start of that turn.
3. **The bot's think is REFUNDED (D-02).** Close the tab while the bot is thinking. Reopen and Resume. Expect: the bot's clock is unchanged from its last committed move.
4. **Discard confirms (D-05).** With a snapshot present, click Discard. Expect: a confirmation dialog first, not an immediate drop. Cancel → gate still there, game intact. Confirm → gate disappears, fresh game starts, reloading `/bots` shows no gate.
5. **An abandoned game leaves no server trace (SC2).** After step 4's discard, check the Library Games tab / dev DB `games` table for `platform = 'flawchess'`. Expect: the abandoned game is NOT there.
6. **A finished game is stored exactly once (SC3).** Play a game to a real finish (resign is fastest). Reload `/bots` twice. Expect: the game appears in the Library exactly once, the second reload makes no `POST /bots/games` (or gets `created: false`), and `localStorage` has no leftover `flawchess_bot_pending_store:` key.
7. **Mobile parity.** Repeat step 1 on a narrow viewport / real phone: the gate is legible, both buttons are tappable, nothing is clipped, and the Discard confirmation is reachable.

**Resume signal for a human running this checklist:** Type "approved", or describe which step failed and what you saw.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 171's setup screen replaces ONLY `BotsGame`'s no-snapshot branch (the `BOT_GAME_SETTINGS` fallback) — `ResumeGate.tsx`, the boot sequence, and the drain wiring are all reused unchanged.
- The full RESUME-01/RESUME-02 loop (snapshot → gate → resume/discard → store-once drain) is now structurally complete and wired end to end; only the live-browser human-verify checkpoint above remains to actually confirm SC1/SC2/SC3.
- No blockers. `tsc -b`, `eslint`, `knip`, and the full frontend suite (2016 tests / 155 files) are all green after this plan.

---
*Phase: 170-localstorage-resume*
*Completed: 2026-07-13*

## Self-Check: PASSED

`frontend/src/components/bots/ResumeGate.tsx`, `frontend/src/components/bots/__tests__/ResumeGate.test.tsx` verified present on disk; `frontend/src/pages/Bots.tsx` verified modified on disk; commit hashes `a88d6891` and `3756148f` verified present in git log.
