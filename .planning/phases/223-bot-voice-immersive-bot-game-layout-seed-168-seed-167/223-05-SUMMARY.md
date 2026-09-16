---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
plan: 05
subsystem: ui
tags: [react, mobile-layout, bot-game, testing-library, eslint-complexity]

requires:
  - phase: 223-01
    provides: "BotGameBubble.tsx (base persona bubble), game.botLine wiring"
  - phase: 223-03
    provides: "BOTVOICE-07 BoardSoundsSwitch, so the in-game mute toggle removed here has a replacement home already shipped"
provides:
  - "BotGameMobileBar.tsx: Resign/Back/Forward/Flip four-action bottom bar, published through mobileBoardControls in place of the main nav"
  - "BotClockStrip.tsx: mobile white-left/black-right clock+material row, no name/style/ELO"
  - "BotDrawOfferActions.tsx: Accept/Decline pair, moved out of the retired banner into BotGameBubble's actions slot"
  - "BotGameMobileLayout.tsx: back arrow + bubble + board + clock strip, replacing the old renderMobileLayout helper"
  - "BotsPage.handleBackToRoster + BotsGameProps.onBackToRoster: mobile back-arrow navigation that preserves the in-progress snapshot"
  - "GameControls.tsx reduced to the resign trigger only (offer-draw + cooldown tooltip + mute removed)"
  - "BotDrawOfferBanner.tsx and its test deleted outright"
affects: [223-06]

actuals:
  tokens: 16070
  tasks: 3
  commits: 3
  plan_head_before: 1f4405efb9008a94a20bbe77e36d3a7d37f3d55c

tech-stack:
  added: []
  patterns:
    - "usePublishMobileBoardControls scoped inside the mobile layout component's own mount, not the page — keeps a whole branch (and its cleanup-on-unmount) out of BotsGame's pinned complexity budget."
    - "drawOfferActionsOrUndefined / personaOrNull: pre-built-element helper functions returning `ReactElement | undefined`, called once per render and stored in a const, so BotsGame's own body never branches on the underlying booleans."

key-files:
  created:
    - frontend/src/components/bots/BotGameMobileBar.tsx
    - frontend/src/components/bots/__tests__/BotGameMobileBar.test.tsx
    - frontend/src/components/bots/BotClockStrip.tsx
    - frontend/src/components/bots/__tests__/BotClockStrip.test.tsx
    - frontend/src/components/bots/BotDrawOfferActions.tsx
    - frontend/src/components/bots/BotGameMobileLayout.tsx
  modified:
    - frontend/src/lib/mobileBoardControls.ts
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/components/bots/BotGameBubble.tsx
    - frontend/src/components/bots/GameControls.tsx
    - frontend/src/lib/botGameCopy.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx
  deleted:
    - frontend/src/components/bots/BotDrawOfferBanner.tsx
    - frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx

key-decisions:
  - "handleBackToRoster in BotsPage is mechanically identical to the existing handleNewGame (same three state resets + boot bump), but kept as its own named callback with its own doc comment: the two share code by coincidence, not by contract — 'New game' is a post-result action, 'back to roster' is a mid-game exit, and a future change to either's semantics (e.g. New game clearing the snapshot) must not silently change the other."
  - "Reworded three doc comments (BotGameBubble.tsx, BotDrawOfferActions.tsx, botGameCopy.ts) that named the retired `BotDrawOfferBanner` component verbatim, to 'the retired draw-offer banner component' — the literal identifier, left by the interrupted prior task-2 run, failed this plan's own acceptance criterion (`grep -rl \"BotDrawOfferBanner\" frontend/src` must return nothing). No behavior change, doc-only."
  - "Bots.test.tsx's draw-offer describe block now drives the offer through `fakeGame.setBotDrawOffer(true)` and asserts the Accept/Decline buttons render inside `bot-game-bubble` via `within()`, rather than asserting persona-specific copy text — the fake `useBotGame` mock hardcodes `botLine: null` (unaffected by this plan), and the real `botDrawOffer -> botLine` coupling that would surface the persona-specific `botGameCopy.ts` 'draw-offer' table text is not yet wired in production code either (confirmed by reading `useBotGameVoice.ts`'s `drawOfferLive` field, which is never set to `true` from any call site). Testing what the code actually does, not what a later requirement will make it do."

patterns-established:
  - "Mechanically-identical-but-semantically-distinct callbacks stay as separate named functions with separate doc comments (handleNewGame vs handleBackToRoster) rather than deduplicated into one, because their contracts are allowed to diverge independently."

requirements-completed: [BOTVOICE-04]

coverage:
  - id: D1
    description: "Mobile game screen: back arrow, avatar+bubble row, board, clock strip (white left/black right, material beside each clock), fixed four-action bar (Resign/Back/Forward/Flip) replacing the main nav"
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/BotGameMobileBar.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/BotClockStrip.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#bot bar takeover describe blocks"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bots — mobile clock strip (Phase 223, BOTVOICE-05, D-11)"
        status: pass
    human_judgment: true
    rationale: "Automated tests prove DOM structure, testid presence and callback wiring, not actual pixel layout/visual ordering on a real phone viewport. The plan's own <output> instructions defer visual/board-width confirmation to plan 06's UAT (223-06 declares the same BOTVOICE-05 requirement)."
  - id: D2
    description: "Mobile screen shows no bot name, style, estimated ELO or player name (D-11)"
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#renders both clocks on mobile with no bot name, style or ELO text (persona game)"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#renders both clocks on mobile with no name text for a Custom game (no persona)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Reset (view-nav) and the four-action bar carry no Reset action on mobile; the user-side Offer draw button (with its cooldown tooltip) and the in-game mute toggle are removed from both mobile and desktop — BOTVOICE-07's settings switch is now the only way to change board sounds. Desktop's BoardControls Reset (return-to-live-position) is UNCHANGED — deferred to 223-06, the desktop half of BOTVOICE-05."
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bots — mobile chrome removed, back arrow wired (Phase 223, BOTVOICE-05, D-10/D-12/SC7)"
        status: pass
      - kind: other
        ref: "grep -rlE 'board-btn-mute|board-btn-offer-draw|bot-draw-offer-banner' src --include='*.ts' --include='*.tsx' | grep -cv '__tests__' == 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "The bot's draw offer is accepted or declined from inside the bubble, both original testids preserved, and a Custom game with no persona still gets the offer and its two buttons"
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bots — bot draw-offer actions render inside the bubble (Phase 223, BOTVOICE-05, D-12)"
        status: pass
    human_judgment: false
  - id: D5
    description: "BotDrawOfferBanner and its test are deleted, and no export is left dangling for the dead-export gate to find"
    requirement: BOTVOICE-04
    verification:
      - kind: other
        ref: "test ! -e BotDrawOfferBanner.tsx && test ! -e BotDrawOfferBanner.test.tsx"
        status: pass
      - kind: other
        ref: "npm run knip"
        status: pass
    human_judgment: false
  - id: D6
    description: "The page root keeps a bottom clearance (pb-20 sm:pb-4), because the replacement bar is still fixed-positioned and outside the page's flow"
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#BotsGame — bottom-nav clearance (171 UAT gap 3, Task 1)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Resign keeps its two-step confirmation with its existing dialog and button testids, on both the mobile bar and the desktop control row"
    requirement: BOTVOICE-04
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/BotGameMobileBar.test.tsx"
        status: pass
    human_judgment: false
  - id: D8
    description: "BotsGame's measured cyclomatic complexity is at or below the 25 pinned in frontend/eslint.config.js, with that file unedited; BoardControls stays at its own pinned 16"
    requirement: BOTVOICE-04
    verification:
      - kind: other
        ref: "npx eslint --no-inline-config --rule 'complexity: [\"error\", 25]' src/pages/Bots.tsx"
        status: pass
      - kind: other
        ref: "npx eslint --no-inline-config --rule 'complexity: [\"error\", 16]' src/components/board/BoardControls.tsx"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-15
status: complete
---

# Phase 223 Plan 05: Bot Voice & Immersive Bot Game Layout — Mobile Layout Rework Summary

**Mobile bot-game screen rebuilt to back arrow / avatar+bubble / board / clock strip / fixed four-action bar, with `BotsGame` measuring complexity 21 against its pinned ceiling of 25, deleting the draw-offer banner and both the offer-draw and mute controls in the process.**

## Performance

- **Duration:** 45 min (this continuation session only — a prior executor completed Tasks 1-2 across an earlier session before being interrupted by a provider rate limit mid-Task-3)
- **Completed:** 2026-09-15T21:11:27Z
- **Tasks:** 3 (Tasks 1-2 completed by the interrupted prior executor; Task 3 completed and committed in this session)
- **Files modified:** 16 (6 created, 2 deleted, 8 modified)

## Accomplishments

- `BotGameMobileBar` (four-action Resign/Back/Forward/Flip bar) publishes through the existing `mobileBoardControls` seam and swaps in for the shared `BoardControls` row in `App.tsx`'s `MobileBottomBar`, with `MobileBoardControls.onReset`/`canReset` made optional and `onResign` added.
- `BotClockStrip` (white left / black right, material beside each clock, no name/style/ELO) and `BotGameMobileLayout` (back arrow → bubble → board → clock strip, publishing the four-action payload from its own mount) replace the old `renderMobileLayout` page helper.
- `BotDrawOfferActions` (Accept/Decline, both testids preserved) now renders inside `BotGameBubble`'s actions slot on both breakpoints; `BotGameBubble` gained a persona-less rendering form (`BOT_DRAW_OFFER_FALLBACK_COPY`) for a Custom game with no persona to key copy off.
- `GameControls` reduced to the resign trigger + its two-step confirm dialog; the user-side Offer draw button (with its cooldown tooltip) and the in-game mute toggle are gone.
- `BotDrawOfferBanner.tsx` and its test deleted outright; `BotsPage` gained `handleBackToRoster` (wired to a new `onBackToRoster` prop on `BotsGame`) so the mobile back arrow returns to the roster without clearing the in-progress snapshot.
- `BotsGame` measures cyclomatic complexity **21** against its pinned ceiling of **25** (down from the baseline 25 — the rework moved every new branch into new components); `BoardControls` stays untouched at its own pinned **16**; `frontend/eslint.config.js` was not edited.

## Task Commits

Each task was committed atomically:

1. **T-223-05-01: The four-action bar — payload extension, new bar component, App takeover branch** — `10eab5fe2` (feat)
2. **T-223-05-02: The clock strip, the draw-offer actions and the mobile layout component** — `e30c2d9e4` (feat)
3. **T-223-05-03: Swap the mobile layout in, strip the control row to resign, retire the banner** — `73e86359c` (feat)

**Plan metadata:** committed separately after this SUMMARY.

## Files Created/Modified

- `frontend/src/components/bots/BotGameMobileBar.tsx` — new four-action fixed bottom bar (Resign/Back/Forward/Flip)
- `frontend/src/components/bots/BotClockStrip.tsx` — new mobile clock+material row, no bot identity
- `frontend/src/components/bots/BotDrawOfferActions.tsx` — new Accept/Decline pair, lifted from the retired banner
- `frontend/src/components/bots/BotGameMobileLayout.tsx` — new mobile layout, replaces the deleted `renderMobileLayout` helper
- `frontend/src/lib/mobileBoardControls.ts` — `onResign?` added, `onReset`/`canReset` made optional
- `frontend/src/App.tsx` — `MobileBottomBar` branches on a resign action to render `BotGameMobileBar`
- `frontend/src/components/bots/BotGameBubble.tsx` — renders in a persona-less form when `actions` is supplied with no persona
- `frontend/src/components/bots/GameControls.tsx` — reduced to the resign trigger only
- `frontend/src/lib/botGameCopy.ts` — doc-comment wording fix (see Deviations)
- `frontend/src/pages/Bots.tsx` — mobile layout swapped in, `handleBackToRoster`/`onBackToRoster` added, mute state/handlers/imports removed, draw-offer actions wired into the bubble
- `frontend/src/pages/__tests__/Bots.test.tsx` — clock-strip/bubble-actions/back-arrow/chrome-removed test rewrites
- `frontend/src/components/bots/BotDrawOfferBanner.tsx` — **deleted**
- `frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx` — **deleted**

## Decisions Made

See `key-decisions` in frontmatter. Summary: `handleBackToRoster` is a deliberate near-duplicate of `handleNewGame` (kept separate for independent-evolution safety); three doc comments were reworded to stop naming the retired `BotDrawOfferBanner` component literally (see Deviations); the draw-offer test rewrite drives the boolean flag directly rather than asserting persona-specific copy text that production code doesn't yet produce.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded three doc comments naming the retired `BotDrawOfferBanner` component verbatim**
- **Found during:** Task 3, acceptance-criteria verification gate
- **Issue:** The prior (interrupted) executor's Task 2 commit left three doc comments — in `BotGameBubble.tsx`, `BotDrawOfferActions.tsx`, and `botGameCopy.ts` — that named the retired component `BotDrawOfferBanner` verbatim for historical context. This plan's own acceptance criterion (`grep -rl "BotDrawOfferBanner" frontend/src` must return nothing) failed against these three files.
- **Fix:** Reworded each to "the retired draw-offer banner component" (no literal identifier), preserving the explanatory intent.
- **Files modified:** `frontend/src/components/bots/BotGameBubble.tsx`, `frontend/src/components/bots/BotDrawOfferActions.tsx`, `frontend/src/lib/botGameCopy.ts`
- **Verification:** `grep -rl "BotDrawOfferBanner" frontend/src` now exits 1 (no matches)
- **Committed in:** `73e86359c` (Task 3 commit)

### Accepted Literal-Text Deviation (not auto-fixed — documented instead)

**2. `frontend/src/pages/Bots.tsx`'s `@/lib/sounds` import keeps `playSound` alongside `unlockAudio`**
- **Found during:** Task 3, acceptance-criteria verification gate
- **Issue:** Task 3's acceptance criteria state "`frontend/src/pages/Bots.tsx` contains no import from `@/lib/sounds` other than the audio-unlock helper" — read literally, this would also forbid `playSound`. `playSound('game-start')` is pre-existing, unrelated functionality (plays a sound on game start, called from `handleStart`) that has nothing to do with the mute/offer-draw removal this task performs.
- **Why not fixed:** The task's own `<read_first>`/`<action>` text is more precise than the acceptance-criteria bullet: "remove the mute state, the toggle handler and the **two** sound-module imports that become unused" — i.e. `setMuted` and `useMuted` only. Removing `playSound` would delete the shipped game-start-sound feature, a Rule-1-relevant regression, to satisfy an overly literal reading of one bullet.
- **Resolution:** Kept `playSound` imported and wired exactly as before; removed only `setMuted`/`useMuted` (done). Documenting here per the HARD GATE's "log it as a deviation with reason" instruction rather than silently skipping either the criterion or the feature.
- **Verification:** `grep -n "playSound" frontend/src/pages/Bots.tsx` shows the pre-existing `handleStart` call site, unchanged; full frontend gate (lint/build/knip/test) passes.
- **Committed in:** `73e86359c` (Task 3 commit) — no separate fix, this is the as-shipped state.

---

**Total deviations:** 1 auto-fixed (Rule 1 — doc-comment wording), 1 accepted literal-text deviation (documented, not auto-fixed).
**Impact on plan:** Both are cosmetic/textual, not functional. No scope creep; no regression introduced.

## Issues Encountered

The plan's Task 3 was interrupted mid-execution by a provider rate limit in a prior session, leaving `BotDrawOfferBanner.tsx` and its test staged as deleted, `GameControls.tsx` partially reduced, and `Bots.tsx` mid-edit (the mobile layout swap and `handleBackToRoster` not yet applied, `Bots.test.tsx` not yet updated). This session read the full diff of both modified files, reconciled the remaining Task 3 action-list items against what was already applied, and completed: `handleBackToRoster` + `onBackToRoster` wiring at both `BotsGame` call sites, the three doc-comment rewordings needed to pass the plan's own acceptance criterion, and the full `Bots.test.tsx` rewrite (clock-strip assertions, bubble-actions assertions, mobile-chrome-removed assertions, back-arrow assertion). No other issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 223's mobile-side BOTVOICE-04/05(partial)/07(partial) work is complete for this plan. `BOTVOICE-05` is shared with plan `223-06` (the desktop-half rework, not yet summarized) and `BOTVOICE-07` is shared with plan `223-03` (already summarized) — both requirement IDs are subject to the shared-ID gate (#2388) and will be marked complete only when every plan declaring them has a `SUMMARY.md`.
- The removed vertical chrome on mobile: the old `BoardControls size="xl"` row (~48px) + the `GameControls` resign/offer-draw/mute row (~48px) + the draw-offer banner slot (~40-50px), roughly 110-130px per RESEARCH's own measurement, are gone — replaced by one avatar+bubble row (avatar `size-12`/48px, bubble `min-h-10` 40px + `py-2` padding + 2px border ≈ 60-64px total row height, whichever of avatar/bubble is taller since they sit `items-start` in a flex row). Net estimate: roughly **50-70px freed** on mobile, available to `useFitBoardToViewport` for the board itself — plan 06's UAT should confirm the actual before/after board-width numbers at 375×667, since this is an arithmetic estimate from source, not a browser measurement.
- `BotsGame`'s measured complexity after this plan: **21** (ceiling 25, `frontend/eslint.config.js` unedited).
- No blockers. Ready for `223-06` (the desktop-side BOTVOICE-05 rework) and phase-level UAT.

## Self-Check: PASSED

- All 15 key files (created/modified) confirmed present on disk via `[ -f ]`; both deleted files (`BotDrawOfferBanner.tsx` and its test) confirmed absent.
- All 3 task commit hashes (`10eab5fe2`, `e30c2d9e4`, `73e86359c`) confirmed present via `git log --oneline --all`.
- Re-ran every plan-level `<verification>` command: `npm run lint`, `npm run build`, `npm run knip`, `npm test -- --run` (270 files / 4258 tests) all pass; `eslint --rule 'complexity:["error",25]'` on `Bots.tsx` and `'complexity:["error",16]'` on `BoardControls.tsx` both exit 0; the eslint.config.js/BoardControls.tsx/package-lock/uv.lock baseline-diff gate exits 0.
- Re-ran every Task 3 `<acceptance_criteria>` bullet individually (grep/file-check/CLI) — all pass, including the `BotDrawOfferBanner` literal-name grep after the doc-comment fix.
- `commits: 3` / `plan_head_before: 1f4405efb9008a94a20bbe77e36d3a7d37f3d55c` in the frontmatter is measured via `git rev-list --count ${PLAN_HEAD_BEFORE}..HEAD`, not narrated.

---
*Phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167*
*Completed: 2026-09-15*
