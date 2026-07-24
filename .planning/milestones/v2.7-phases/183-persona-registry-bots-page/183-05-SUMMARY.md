---
phase: 183-persona-registry-bots-page
plan: 05
subsystem: ui
tags: [react, typescript, chess, bots, personas, copywriting]

# Dependency graph
requires:
  - phase: 183-01
    provides: "PERSONA_REGISTRY/personaForId, placeholderAvatarFor, PersonaId type"
  - phase: 183-03
    provides: "BotGameSettings.personaId?, useBotGame's botDrawOffer/acceptBotDraw/declineBotDraw"
  - phase: 183-04
    provides: "PersonaGrid as the default setup view (the 'New opponent' return target)"
provides:
  - "personaFor(settings) — the ONE shared settings.personaId -> Persona lookup, consumed by the clock strip, draw banner, and both result surfaces"
  - "ClockDisplay avatarEmoji prop — persona avatar rendered beside sideLabel"
  - "BotDrawOfferBanner — non-blocking inline bot draw-offer UI (D-07)"
  - "resultCopy(outcome, userColor, personaName?) — persona-named bot-actor result copy, byte-identical fallback when personaName is omitted"
  - "GameResultDialog/GameResultStrip Rematch <Persona> + relabeled New opponent actions"
affects: [184-persona-calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A single shared lookup helper (personaFor) resolved ONCE per render in the caller (Bots.tsx) and threaded down as plain props — every consumer null-coalesces to its own generic fallback rather than re-deriving the settings.personaId -> Persona relationship"
    - "Additive optional resultCopy parameter substitutes only into the branches where the substituted actor is grammatically correct (bot-actor branches), leaving every other branch (user-actor, draw, and the personaName-omitted path) byte-identical to the pre-existing strings"
    - "Primary/secondary button swap driven by data, not two separate JSX trees: Rematch (when present) takes variant=default and New opponent steps down to brand-outline, matching CLAUDE.md's single-high-emphasis-CTA rule for both the persona and Custom-game cases"

key-files:
  created:
    - frontend/src/components/bots/BotDrawOfferBanner.tsx
    - frontend/src/components/bots/__tests__/ClockDisplay.test.tsx
    - frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx
  modified:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/components/bots/ClockDisplay.tsx
    - frontend/src/lib/botGameEnd.ts
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/GameResultStrip.tsx
    - frontend/src/pages/Bots.tsx
    - frontend/src/lib/__tests__/botGameEnd.test.ts
    - frontend/src/components/bots/__tests__/GameResultDialog.test.tsx
    - frontend/src/components/bots/__tests__/GameResultStrip.test.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "personaFor(settings: BotGameSettings) imports BotGameSettings via `import type` from useBotGame.ts — verbatimModuleSyntax erases the import at compile time, so it introduces no runtime circular dependency despite useBotGame.ts also importing PersonaId from personaRegistry.ts"
  - "resultCopy substitution scope: ONLY the branches where the bot is the grammatical actor (checkmate/timeout loss, the D-03-unreachable 'the bot resigned' win) get the persona name; user-win and user-resigned branches, and every draw branch, stay unchanged regardless of personaName — matches the acceptance criteria's 'bot-actor copy' framing exactly"
  - "Rematch reuses the EXACT SAME settings object reference passed to handleStart (not a rebuilt/cloned settings object) — 'same pinned config' is satisfied by object identity, the simplest and most literal reading of D-08"
  - "Primary/secondary swap: with a persona (Rematch present), Rematch is variant=default and New opponent steps down to variant=brand-outline; for a Custom game (no Rematch), New opponent stays variant=default — keeps exactly one variant=default CTA visible at all times per CLAUDE.md's primary-button rule"
  - "AVAT-01 (real-art avatar portraits) is NOT marked complete despite appearing in this plan's frontmatter requirements list — it stays intentionally open per 183-01-SUMMARY.md's D-16 note (placeholder emoji avatars only this milestone); this plan only threads the EXISTING placeholder avatar through the clock strip, it does not add real art"

patterns-established:
  - "Non-blocking inline game-state banners (BotDrawOfferBanner) render as a plain conditional div sibling near the board — never a Dialog — so play continues underneath; width-capped via the same BOT_BOARD_MAX_WIDTH_PX/DESKTOP_SIDE_COLUMN_PX constants the board layout already uses, so it never sprawls to the page's max-w-5xl container"

requirements-completed: [PERS-02]

coverage:
  - id: D1
    description: "The bot clock strip shows the persona avatar + name for a persona game and falls back to 'FlawChess Bot' for a Custom game, identically on desktop and mobile, via the shared personaFor helper"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/ClockDisplay.test.tsx (3 tests: avatar+label render, label-only when avatarEmoji omitted, text-sm floor)"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx > Bots — bot clock persona presence (D-06) (2 tests: persona game shows name+emoji, Custom game shows 'FlawChess Bot')"
        status: pass
      - kind: other
        ref: "grep -rn 'personaId ? PERSONA_REGISTRY|personaId ? personaForId' src/ (excluding personaRegistry.ts) — zero hits, no inline re-implementation"
        status: pass
    human_judgment: false
  - id: D2
    description: "The bot's outgoing draw offer surfaces as a non-blocking inline banner reading '<Persona name> offers a draw' (generic fallback for Custom) with working Accept/Decline; play continues; auto-expires on the user's next move via the existing hook"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx (6 tests: renders-nothing when not live, persona-named prompt, generic fallback, Accept/Decline call through, text-sm floor)"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx > Bots — bot draw-offer banner wiring (D-07) (2 tests: persona-named banner + Accept/Decline call the hook's acceptBotDraw/declineBotDraw, Custom-game generic fallback)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The result dialog and result strip name the persona in the outcome copy for a persona game (bot-actor branches: checkmate/timeout loss, bot-resigned win), keeping the byte-identical generic copy for a Custom game; the strip renders the SAME string as the dialog (mobile parity)"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameEnd.test.ts > resultCopy — persona-named bot-actor copy (Phase 183, D-06) (6 tests: checkmate/timeout/resigned substitution, user-actor unchanged, draw unchanged, exact pre-183 strings when personaName omitted/null/undefined)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx and GameResultStrip.test.tsx > persona-named copy + Rematch/New opponent describe blocks (4 tests total, case-for-case parity)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The result surfaces offer 'Rematch <Persona>' (same pinned settings object, via the existing handleStart) alongside Analyze, and a relabeled 'New opponent' path (existing onNewGame, no new route); Custom games show no Rematch button"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx > Bots — Rematch/New opponent (Phase 183, D-06/D-08) (3 tests: dialog Rematch starts a fresh game with the SAME settings object and calls the single handleStart path (newGame() never called), the strip mirrors the same copy/Rematch, a Custom game shows no Rematch + relabeled New opponent)"
        status: pass
      - kind: other
        ref: "grep -n 'onNewGame={' frontend/src/pages/Bots.tsx — both result surfaces still wired to the same handleNewGame; no new route/navigate call added for New opponent"
        status: pass
    human_judgment: false
  - id: D5
    description: "Backstop: a resumed game whose personaId is no longer present in PERSONA_REGISTRY renders the unstyled 'FlawChess Bot' fallback everywhere (clock, banner, result copy) and never crashes"
    verification:
      - kind: other
        ref: "Source review: personaFor/personaForId is a guarded object-index lookup that returns undefined (never throws) for an unrecognized id (personaRegistry.ts, unchanged this plan); every consumer (Bots.tsx's persona = personaFor(settings)) null-coalesces via persona?.name ?? 'FlawChess Bot' / persona?.name ?? null, so an undefined persona degrades to the exact same generic paths a Custom game already exercises (covered by the Custom-game test cases in D1/D2/D3/D4 above, which exercise personaName === null through the identical code path)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-22
status: complete
---

# Phase 183 Plan 05: Persona Presence in the Live Game + Result Surfaces Summary

**Persona avatar+name in the bot clock strip, a non-blocking BotDrawOfferBanner for the bot's outgoing draw offer, persona-named `resultCopy` for bot-actor outcomes, and a "Rematch \<Persona\>"/relabeled "New opponent" pair on both result surfaces — all resolving identity through one shared `personaFor(settings)` lookup.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-22T11:53:00Z (approx, per session start)
- **Completed:** 2026-07-22T12:08:40Z
- **Tasks:** 3
- **Files modified:** 13 (3 created, 10 modified)

## Accomplishments

- `personaFor(settings)` added to `personaRegistry.ts` — the ONE shared `settings.personaId -> Persona` lookup every consumer in this plan (clock strip, draw banner, both result surfaces) calls, instead of re-implementing the ternary inline. Type-only imports `BotGameSettings` from `useBotGame.ts` (erased at compile time by `verbatimModuleSyntax`, so no runtime circular import despite the reverse `PersonaId` import).
- `ClockDisplay` gains an optional `avatarEmoji` prop rendered beside `sideLabel`; `Bots.tsx` resolves `persona = personaFor(settings)` once and feeds the bot clock the persona's name/avatar, falling back to `'FlawChess Bot'` for a Custom game — one `botClock` element feeds both desktop and mobile layouts, so parity is structural (D-06).
- `BotDrawOfferBanner`: a new non-blocking inline banner (`aria-live="polite"`) reading `"<Persona> offers a draw"` (or the generic fallback) with Accept/Decline, rendered as a plain sibling near the board (never a Dialog) and width-capped to match the board/side-column group. Fed by `game.botDrawOffer`/`acceptBotDraw`/`declineBotDraw` (Plan 03) — the hook already auto-expires the offer on the user's next move, no extra page logic needed (D-07).
- `resultCopy(outcome, userColor, personaName?)` — the persona name substitutes ONLY into the bot-actor branches (checkmate/timeout loss, the D-03-unreachable "the bot resigned" win copy); user-actor branches and every draw branch stay unchanged, and omitting `personaName` returns the exact pre-183 generic strings byte-for-byte (verified against the pre-existing test suite unchanged).
- `GameResultDialog`/`GameResultStrip` both render the identical persona-aware title, relabel "New game" to "New opponent" (reusing the existing `onNewGame` path, no new route), and add "Rematch \<Persona\>" (persona games only) as the primary CTA — New opponent steps down to `brand-outline` whenever Rematch is present, keeping exactly one `variant=default` button visible at a time per CLAUDE.md's primary/secondary rule.
- `Bots.tsx` threads a new `onRematch: (settings) => void` prop through `BotsGame`, wired to `BotsPage.handleStart` at both mount sites (fresh-start and resumed-snapshot). `handleRematch` calls `onRematch(settings)` with the SAME settings object reference the current game is playing with — "same pinned config" via object identity, the most literal reading of D-08.

## Task Commits

Each task was committed atomically:

1. **Task 1: Persona presence in the bot clock strip (D-06, desktop + mobile)** - `e2075ae5` (feat)
2. **Task 2: BotDrawOfferBanner + wiring (D-07)** - `cdf7a0b3` (feat)
3. **Task 3: Persona-named result copy + Rematch / New opponent (D-06/D-08)** - `29c79e37` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `frontend/src/components/bots/BotDrawOfferBanner.tsx` - non-blocking inline bot draw-offer banner
- `frontend/src/components/bots/__tests__/ClockDisplay.test.tsx` - 3 tests: avatar rendering, no-avatar fallback, text-sm floor
- `frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx` - 6 tests: gating, persona/generic copy, Accept/Decline, text-sm floor
- `frontend/src/lib/personas/personaRegistry.ts` - added `personaFor(settings)`
- `frontend/src/components/bots/ClockDisplay.tsx` - added optional `avatarEmoji` prop
- `frontend/src/lib/botGameEnd.ts` - `resultCopy` gains optional `personaName` param
- `frontend/src/components/bots/GameResultDialog.tsx` - persona-named title, Rematch, relabeled New opponent
- `frontend/src/components/bots/GameResultStrip.tsx` - mirrors GameResultDialog case-for-case (mobile parity)
- `frontend/src/pages/Bots.tsx` - `persona = personaFor(settings)` resolved once; wires the clock strip, banner, both result surfaces, and `onRematch={handleStart}`
- `frontend/src/lib/__tests__/botGameEnd.test.ts` - 6 new tests for persona-named/unchanged branches
- `frontend/src/components/bots/__tests__/GameResultDialog.test.tsx` - 2 new tests (persona title + Rematch, Custom no-Rematch)
- `frontend/src/components/bots/__tests__/GameResultStrip.test.tsx` - 2 new tests (mirrors dialog case-for-case)
- `frontend/src/pages/__tests__/Bots.test.tsx` - useBotGame mock extended with `botDrawOffer`/`acceptBotDraw`/`declineBotDraw`; 6 new tests across 3 new describe blocks (clock presence, draw-offer wiring, Rematch/New opponent)

## Decisions Made

- **`personaFor` type-only imports `BotGameSettings`:** `verbatimModuleSyntax` (tsconfig.app.json) erases `import type` statements at compile time, so `personaRegistry.ts` importing a type from `useBotGame.ts` (which itself imports `PersonaId` from `personaRegistry.ts`) introduces zero runtime circular dependency — confirmed via a clean `npx tsc -b` and the full test suite passing.
- **resultCopy substitution scope is precisely "bot-actor" branches:** checkmate-loss, timeout-loss, and the (D-03-unreachable) bot-resigned-win branch get the persona name; the user-win and user-resigned branches, plus every draw branch, are left completely unchanged by `personaName` — matching the plan's own acceptance criterion wording ("substitutes it into the bot-actor copy") rather than naming the persona everywhere the copy mentions an outcome.
- **Rematch reuses the exact same settings object reference**, not a rebuilt clone — `handleRematch` in `BotsGame` calls `onRematch(settings)` with its own `settings` prop verbatim. This is the simplest, most literal satisfaction of "same pinned config + same color/TC" and is pinned by a `toBe` (reference-identity) test assertion, not just a value-equality one.
- **Primary/secondary button swap is data-driven, not two JSX trees:** `variant={personaName ? 'brand-outline' : 'default'}` on the New opponent button in both result surfaces — Rematch (when rendered) takes `variant="default"`, so exactly one high-emphasis CTA is visible whether or not the game was a persona game.
- **AVAT-01 stays unmarked in REQUIREMENTS.md** despite appearing in this plan's frontmatter `requirements` list — 183-01-SUMMARY.md's D-16 decision already established this milestone ships placeholder-emoji avatars only (real-art portraits are a future PR); this plan only threads the EXISTING `placeholderAvatarFor` emoji through the clock strip, adding no new avatar capability, so AVAT-01 remains intentionally open.

## Deviations from Plan

**1. [Rule 1 - Bug] `resultCopy`'s intermediate implementation accidentally changed the no-persona default strings**

- **Found during:** Task 3, before running any verification
- **Issue:** A first-pass implementation introduced a shared `botActor = personaName ?? 'the bot'` variable and interpolated it into every bot-actor branch. This silently changed the DEFAULT (no-persona) strings from the exact pre-183 `'You lost — checkmate'` / `'You lost on time'` to `'the bot wins — checkmate'` / `'the bot wins on time'` — a direct violation of the plan's "keeping the generic copy for a Custom game" truth and would have broken the pre-existing `botGameEnd.test.ts` suite.
- **Fix:** Rewrote each branch to explicitly return the exact original literal string when `personaName` is falsy, and only interpolate `personaName` when it is truthy — verified byte-identical against the pre-existing (unmodified) test assertions before adding any new persona-specific tests.
- **Files modified:** `frontend/src/lib/botGameEnd.ts` (caught and fixed before any commit — not present in the committed history).
- **Verification:** `npm test -- --run src/lib/__tests__/botGameEnd.test.ts` — all 12 pre-existing tests plus 6 new persona-copy tests pass; the "exact pre-183 generic strings when personaName is omitted/null/undefined" test explicitly pins this.

---

**Total deviations:** 1 auto-fixed (1 self-caught bug, corrected before commit — no scope creep, no impact on shipped behavior)
**Impact on plan:** None on the shipped code — the bug was caught and fixed during Task 3's own implementation, before verification or commit.

## Issues Encountered

None beyond the self-caught deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- This closes the in-game half of Phase 183 (D-06/D-07/D-08): every persona-facing UI surface (browse grid, detail surface, live clock strip, outgoing draw-offer banner, result copy, rematch/new-opponent) is now wired end to end through the single `personaFor`/`personaForId` lookup chain.
- Phase 184 (persona calibration) can proceed against this UI without further wiring changes — `botElo === rung` (the A1 placeholder from 183-01) is the only remaining "provisional, not measured" surface, and it is entirely outside this plan's scope (calibration only changes the persona registry's data, not any of the UI consuming it).
- `AVAT-01` (real-art avatar portraits) remains open by design — `resolveAvatarSrc`'s forward-compat seam is unchanged and ready for a future real-art PR to populate `avatarSrc` on any persona, which will flow through to the clock strip's `avatarEmoji` rendering automatically once that PR also threads an image-vs-emoji check through `ClockDisplay` (not built this plan — `ClockDisplay` currently only accepts an `avatarEmoji` string, mirroring the plan's literal scope).
- No blockers. Full frontend suite (182 files / 2490 tests), `npx tsc -b`, `npm run lint`, and `npm run knip` are all green.

---
*Phase: 183-persona-registry-bots-page*
*Completed: 2026-07-22*

## Self-Check: PASSED

All 13 created/modified files verified present on disk; all 3 task commit hashes (`e2075ae5`, `cdf7a0b3`, `29c79e37`) verified present in git log.
