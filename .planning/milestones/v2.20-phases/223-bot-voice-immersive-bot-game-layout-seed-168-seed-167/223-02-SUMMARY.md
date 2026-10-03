---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
plan: 02
subsystem: ui
tags: [react, bots, chess, voice-copy, persona-rotation, date-fns]

requires:
  - phase: 223-01
    provides: "botGameCopy.ts's BotLineKey union / BOT_LINE_TABLES shape, botLineCopy, BOT_LINE_MAX_CHARS"
provides:
  - "botGameCopy.ts: all ten in-game BOT_LINE_TABLES keys (game-start, first-capture, earned-tease, punished-mistake, nice-move, player-threat, draw-offer, bot-won, bot-lost, game-drawn), each an exhaustive Record<PersonaId, string> over all 24 personas"
  - "botGameCopy.ts: ROSTER_GREETINGS (24 welcome lines), RosterHostInput, RosterHost, rosterHost() — the /bots roster's daily persona-rotation host picker"
  - "trainBotCopy.ts: LANDING_ROTATION_EPOCH and LANDING_HOST_IDS exported so rosterHost shares the exact epoch/id order landingHost uses"
  - "PersonaGrid.tsx: BotWelcomeCard (renamed from HumanLikeOpponentsCard) rendering the bots-welcome-bubble, replacing the prose intro paragraph"
  - "lib/__tests__/botGameCopy.test.ts: the exhaustive per-table/per-persona invariant test (budget, em-dash, forbidden-claim, insult, numeric-disclosure, no cross-surface duplication) plus the rosterHost/landingHost rotation-agreement test"
affects: [223-04, 223-05, 223-06]

actuals:
  tokens: 12811
  tasks: 3
  commits: 3
  plan_head_before: 96435bfe9f6e064d8c7195835456d34209e126fa

tech-stack:
  added: []
  patterns:
    - "Exhaustive Record<BotLineKey, Record<PersonaId, string>> tables guarded by one regex-over-every-entry invariant test, mirroring trainBotCopy.ts/trainBotCopy.test.ts's own convention"
    - "Shared rotation primitives (epoch + id order) exported from one module and imported by a sibling module's own rotation function, rather than two independently-declared copies that could silently drift apart"

key-files:
  created:
    - frontend/src/lib/__tests__/botGameCopy.test.ts
  modified:
    - frontend/src/lib/botGameCopy.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
    - frontend/src/lib/__tests__/trainBotCopy.test.ts

key-decisions:
  - "Authored the invariant-test regexes (forbidden-claim, insult, numeric-disclosure) myself as named module-level constants, since the plan states the RULES in prose (223-CONTEXT D-08, PersonaGrid's copy-accuracy comment) but not an exact pattern — each regex comment cites the rule it enforces and where that rule is stated, per the task's own acceptance criteria."
  - "Task 2 (tdd=\"true\") followed the task's own explicit action ordering — author the four tables first, then write the invariant test — rather than a strict test-first RED/GREEN split. The test passed immediately (no RED failure) because the tables were already correct production copy. Same documented exception as 223-01 Task 2's TDD Gate Compliance note (Fail-Fast Rule 1: 'the feature demonstrably already exists')."
  - "rosterHost copies landingHost's day-index formula verbatim, importing the newly-exported LANDING_ROTATION_EPOCH/LANDING_HOST_IDS rather than declaring a second epoch or id list — the rotation-agreement test (a full 24-day cycle) proves the two pages agree structurally, not by luck."
  - "Reworded a RosterHostInput doc comment from the literal token 'introSeenAt' to 'gating on whether the intro stepper has been seen' — the acceptance-criteria grep for that literal cannot distinguish an explanatory comment from a real reference, the same false-positive-comment class documented in 223-01-SUMMARY.md Deviation #2 and 223-03-SUMMARY.md Deviation #1. No behavior change; rosterHost's body never referenced the field either way."
  - "PersonaGrid computes the roster rotation's ISO day via date-fns's format(devClockNow(readDevClockOffsetMinutes()), 'yyyy-MM-dd') rather than Date.prototype.toISOString().slice(0, 10) — matching the existing format/parseISO convention already used by TrainStartScreen.tsx and TrainScheduleSettings.tsx, rather than introducing a second date-formatting idiom."

patterns-established: []

requirements-completed: [BOTVOICE-01, BOTVOICE-06]

coverage:
  - id: D1
    description: "The five move-triggered line tables (first-capture, earned-tease, punished-mistake, nice-move, player-threat) — 120 authored strings across 24 personas, board-truth safe, no claim of calculation/foresight"
    requirement: "BOTVOICE-01"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botGameCopy.test.ts#ALL_SURFACES (BOT_LINE_TABLES + ROSTER_GREETINGS) — shared invariants (all 6 cases)"
        status: pass
      - kind: other
        ref: "npm run build (TypeScript exhaustiveness proof: a missing persona in any table is a compile error)"
        status: pass
    human_judgment: true
    rationale: "Structural correctness (exhaustiveness, character budget, forbidden-claim/insult/numeric-disclosure regexes) is fully machine-verified above, but whether each line genuinely reads in that persona's distinct voice — and whether the tease register lands as playful rather than mean to an 800-rung beginner — is a tone judgment regex checks cannot fully capture. Plan 06's UAT is the plan's own designated re-calibration point for exactly this."
  - id: D2
    description: "The four state-triggered tables (draw-offer, bot-won, bot-lost, game-drawn) — 96 authored strings — plus the invariant test that guards all ten in-game tables at once"
    requirement: "BOTVOICE-01"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botGameCopy.test.ts#BOT_LINE_TABLES — exhaustiveness (3 cases) + ALL_SURFACES shared invariants (6 cases) + draw-offer-reads-as-offer + terminal-table tonal checks (3 cases)"
        status: pass
      - kind: other
        ref: "npm run build (exhaustiveness proof for the four new tables)"
        status: pass
    human_judgment: true
    rationale: "Same tone-judgment gap as D1 for the authored copy itself. The invariant test's MECHANICAL guarantees (budget/em-dash/forbidden-claim/insult/numeric/no-duplication/tonal deny-lists) are fully proven and pass; a human still owns whether 'gracious, never gloating' (bot-won) and 'congratulating without being saccharine' (bot-lost) land correctly in each of the 24 voices."
  - id: D3
    description: "The roster page opens with a per-persona welcome bubble (BotWelcomeCard) replacing the prose paragraph; the engine InfoPopover stays reachable inline and the estimated-rating row stays beneath it with its non-null gate; a guest sees the bubble without the rating row"
    requirement: "BOTVOICE-06"
    verification:
      - kind: unit
        ref: "src/components/bots/__tests__/PersonaGrid.test.tsx#renders the welcome bubble with rosterHost's own copy for the mocked date, plus the engine popover trigger"
        status: pass
      - kind: unit
        ref: "src/components/bots/__tests__/PersonaGrid.test.tsx#renders the welcome bubble AND the rating row for a non-null strength"
        status: pass
      - kind: unit
        ref: "src/components/bots/__tests__/PersonaGrid.test.tsx#a guest (null strength) still sees the welcome bubble, with no rating row (D-13, SC6)"
        status: pass
    human_judgment: true
    rationale: "Functional behavior (bubble renders with the correct persona/copy, popover and rating row present/gated correctly) is fully proven by the passing tests above. Visual adequacy of the new bubble layout inside the existing card (does it read well at 375px, does the avatar/bubble proportion look right) is deferred to plan 06's phase-level UAT, per this phase's own convention (223-01-SUMMARY.md's Next Phase Readiness note makes the same deferral for the in-game bubble)."
  - id: D4
    description: "The roster host and the /train landing host resolve to the SAME persona for the same calendar date, structurally — both read the exported LANDING_ROTATION_EPOCH and LANDING_HOST_IDS, never two independently-declared copies"
    requirement: "BOTVOICE-06"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botGameCopy.test.ts#rosterHost / landingHost — shared daily rotation (223-02) — all 3 cases (24-day full-cycle agreement, greeting-pairing, Tank fallback)"
        status: pass
      - kind: other
        ref: "grep -c 'LANDING_ROTATION_EPOCH\\|LANDING_HOST_IDS' frontend/src/lib/botGameCopy.ts -> 5 (import + two live reads), grep -c 'new Date(' frontend/src/lib/botGameCopy.ts -> 0"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-09-15
status: complete
---

# Phase 223 Plan 02: Bot Voice Copy & Roster Rotation Summary

**All ten in-game trigger tables (240 lines) plus ROSTER_GREETINGS (24 lines) are authored across 24 personas with a shared invariant test, and the /bots roster now opens with a rotating welcome bubble that structurally agrees with /train's daily host via exported LANDING_ROTATION_EPOCH/LANDING_HOST_IDS.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-15T19:47:00Z (approx.)
- **Completed:** 2026-09-15T20:08:00Z
- **Tasks:** 3 completed
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- Authored 120 board-truth-safe lines across the five move-triggered tables (`first-capture`, `earned-tease`, `punished-mistake`, `nice-move`, `player-threat`), each an exhaustive `Record<PersonaId, string>`, max measured length 50 chars against the 64-char budget.
- Authored 96 lines across the four state-triggered tables (`draw-offer`, `bot-won`, `bot-lost`, `game-drawn`), recording the accepted `useWinCelebrationHold` loss/draw trade-off in the module header, and wrote `botGameCopy.test.ts`: a 21-case invariant suite iterating `Object.keys(BOT_LINE_TABLES)` (never a hand-written key list) that enforces the budget, em-dash ban, forbidden-claim regex, insult regex, numeric-disclosure regex, no cross-table/landing-greeting duplication, the draw-offer-reads-as-offer contract and terminal-table tone.
- Authored `ROSTER_GREETINGS` (24 welcome lines) and `rosterHost()`, importing the newly-exported `LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS` from `trainBotCopy.ts` so the roster and /train landing rotations agree on the day's host structurally — proven by a 24-day full-cycle agreement test.
- Renamed `HumanLikeOpponentsCard` to `BotWelcomeCard` in `PersonaGrid.tsx`: the prose paragraph is now a `bots-welcome-bubble` wrapping `TrainBotBubble` (`avatarSize="large"`) with the rotating persona's greeting, the engine `InfoPopover` kept inline at the end of the copy, and the estimated-rating row kept verbatim beneath it with its non-null gate — a guest sees the bubble with no rating row.
- Total authored-line count for this plan: 264 (240 in `BOT_LINE_TABLES` + 24 in `ROSTER_GREETINGS`); measured longest line is 50 characters against the 64-character `BOT_LINE_MAX_CHARS` budget.

## Task Commits

1. **Task 1: The five move-triggered line tables — 120 authored strings in 24 voices** - `5ad8171ac` (feat)
2. **Task 2: The four state-triggered tables and the copy invariant test that guards all ten** - `b9e2f857b` (feat)
3. **Task 3: The roster welcome bubble, its greeting table and the shared daily rotation** - `22127cacb` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/lib/botGameCopy.ts` - widened `BotLineKey` to all ten keys with their tables, `ROSTER_GREETINGS`, `RosterHostInput`/`RosterHost`/`rosterHost()`
- `frontend/src/lib/__tests__/botGameCopy.test.ts` - the exhaustive invariant test (new file)
- `frontend/src/lib/trainBotCopy.ts` - exported `LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS`, updated the header's scoped-exception sentence
- `frontend/src/lib/__tests__/trainBotCopy.test.ts` - import-side assertion for the two newly-exported primitives
- `frontend/src/components/bots/PersonaGrid.tsx` - `BotWelcomeCard` (renamed), the `bots-welcome-bubble` wrapper, rotation-day computation via `devClockNow(readDevClockOffsetMinutes())`
- `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx` - bubble/rating-row/guest test cases replacing the prose assertion

## Decisions Made

See `key-decisions` in the frontmatter. The most consequential: `rosterHost` imports the SAME `LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS` `landingHost` uses rather than declaring a second copy of either, so "the same bot greets you on /train and /bots today" is a structural guarantee (proven by a 24-day full-cycle test) rather than something that could silently drift if either list were edited independently.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in an acceptance-criteria command] The `introSeenAt` literal-token grep cannot distinguish an explanatory comment from a real reference**
- **Found during:** Task 3's own acceptance criteria — `grep -c "introSeenAt" frontend/src/lib/botGameCopy.ts` (implied by "rosterHost's body contains no introSeenAt reference").
- **Issue:** `RosterHostInput`'s doc comment explained the design ("there is no `introSeenAt` field") using the literal token the check would grep for, so an accurate comment describing the absence tripped a check meant to catch a real usage. Same false-positive-comment class as 223-01-SUMMARY.md Deviation #2 (`.grade(` in a doc comment) and 223-03-SUMMARY.md Deviation #1 (`localStorage` in a doc comment).
- **Fix:** Reworded the comment to "gating on whether the intro stepper has been seen" — same meaning, no behavior change; `rosterHost`'s function body never referenced the field under either wording.
- **Files modified:** `frontend/src/lib/botGameCopy.ts`
- **Verification:** `grep -c "introSeenAt" frontend/src/lib/botGameCopy.ts` returns 0; `rosterHost`'s body (re-read after the edit) still has no such field, no such gate.
- **Committed in:** `22127cacb` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (bug in an acceptance-criteria command).
**Impact on plan:** No scope creep. The underlying invariant (no intro-stepper gate on the roster rotation) held both before and after the wording fix — the fix only corrected which grep confirms it.

## Issues Encountered

None beyond the documented deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All ten in-game `BOT_LINE_TABLES` keys plus `ROSTER_GREETINGS` are final for this phase (264 authored strings, all under budget, all clean against the forbidden-claim/insult/numeric-disclosure regexes) — plans 04/05 wire triggers and layout against tables that already exist and are already tested; no further table shape changes are expected before plan 06's UAT.
- `rosterHost` and `landingHost` are proven to agree structurally for any date; a future edit to either `LANDING_GREETINGS`/`ROSTER_GREETINGS`'s id ordering (unlikely, since both derive from `Object.keys`) would be caught immediately by the rotation-agreement test.
- Per this plan's own D1/D2/D3 coverage rationale: the AUTHORED WORDING (voice/tone quality) and the roster bubble's real rendered appearance at 375px are the two things plan 06's UAT should still re-check — everything structurally provable (exhaustiveness, budget, forbidden patterns, rotation agreement, gating) already passes.
- No blockers for plans 04/05/06.

---
*Phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167*
*Plan: 02*
*Completed: 2026-09-15*

## Self-Check: PASSED

- Created file `frontend/src/lib/__tests__/botGameCopy.test.ts` verified present on disk.
- `git log --oneline --all` contains all three task commits (`5ad8171ac`, `b9e2f857b`, `22127cacb`).
- All plan-level `<verification>` commands re-run and pass: `npm run lint`, `npm run build`, `npm test -- --run` (269 files / 4249 tests), and the supply-chain diff gate (`eslint.config.js`/package/lockfile/pyproject/uv.lock unchanged).
- All task-level `<acceptance_criteria>` re-checked and pass, including the 144-entry and 240-entry grep counts, the `trainBotCopy.ts` scoped-diff check, and the `LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS`/`new Date(`/`introSeenAt` greps in `botGameCopy.ts`.
