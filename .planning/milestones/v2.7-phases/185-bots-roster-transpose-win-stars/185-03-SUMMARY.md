---
phase: 185-bots-roster-transpose-win-stars
plan: 03
subsystem: ui
tags: [react, typescript, vitest, bots, tanstack-query, theme]

# Dependency graph
requires:
  - phase: 185-bots-roster-transpose-win-stars
    plan: "01"
    provides: "GET /bots/persona-wins aggregation endpoint + StoreBotGameRequest.persona_id (backend contracts consumed here)"
  - phase: 185-bots-roster-transpose-win-stars
    plan: "02"
    provides: "Transposed grid-cols-4 PersonaGrid (this plan edits the same file, adding a prop rather than restructuring layout)"
provides:
  - "STAR_FILLED/STAR_EMPTY named theme constants"
  - "useBotPersonaWins hook + botsApi.getPersonaWins + PersonaWinsResponse type"
  - "PersonaCard PersonaStars sub-component + MAX_DISPLAY_STARS constant + winsForPersona prop"
  - "PersonaGrid winsByPersona prop, threaded from Bots.tsx's single useBotPersonaWins() call"
  - "frontend StoreBotGameRequest.persona_id (sent on every finished bot game)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-fetch-then-prop-drill (Pattern 3): ONE useBotPersonaWins() call in Bots.tsx, prop-drilled through PersonaGrid -> PersonaCard; no useQuery inside either component"
    - "Loading/error/zero-state merge: winsForPersona undefined renders identically to 0 (all-outline stars) — a transient fetch failure never shows a false negative"

key-files:
  created:
    - frontend/src/hooks/useBotPersonaWins.ts
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/types/bots.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useStoreBotGame.ts
    - frontend/src/hooks/__tests__/useStoreBotGame.test.ts
    - frontend/src/components/bots/PersonaCard.tsx
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
    - frontend/src/pages/Bots.tsx

key-decisions:
  - "STAR_FILLED/STAR_EMPTY declared as independent named constants in theme.ts, NOT an alias of FLAWCHESS_ENGINE_ACCENT despite the matching gold hue — per UI-SPEC, so the two can diverge independently later"
  - "PersonaStars renders via a filled/empty count split (Array.from({length: filledCount}) + Array.from({length: emptyCount})) rather than a single MAX_DISPLAY_STARS-length loop with an i<filledCount check — the split makes the Math.min cap load-bearing (removing it would render MORE than 3 stars for wins>=4), whereas the single-loop form would silently truncate at exactly 3 regardless of the cap and make the required mutation check a no-op"
  - "Star color/fill set directly to STAR_FILLED/STAR_EMPTY literals (not lucide's implicit currentColor CSS-inheritance chain) — functionally equivalent to the UI-SPEC's fill='currentColor' shorthand but avoids depending on an ambient CSS `color` value that isn't otherwise set on the wrapping span"
  - "winsByPersona kept OPTIONAL (Record<string, number> | undefined) on PersonaGridProps per the plan's literal action text, even though Bots.tsx always passes it — preserves existing PersonaGrid.test.tsx call sites that omit the prop"
  - "toStoreRequest's existing test updated (not just extended) to include persona_id: null in its full-object equality assertion, since the mapper's own field set changed; added two new focused tests for the personaId->persona_id mapping and the Custom-mode/old-entry null fallback"

requirements-completed: []  # No formal REQ-IDs for this post-milestone phase (see plan frontmatter)

coverage:
  - id: T1
    description: "STAR_FILLED/STAR_EMPTY theme constants, useBotPersonaWins hook, botsApi.getPersonaWins, PersonaWinsResponse type, and persona_id on the store-game request all exist and type-check; stale localStorage queue entries still round-trip"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts (toStoreRequest field-mapping tests, incl. new personaId->persona_id and null-fallback cases)"
        status: pass
      - kind: other
        ref: "npx tsc -b (zero errors)"
        status: pass
    human_judgment: false
  - id: T2
    description: "PersonaCard renders min(wins,3) gold-filled + remainder grey-outline stars; undefined/0 render identically (all-outline, no visible '0 wins' text); overflow caps at 3; stars-row aria-label is separate from the card's persona-identity aria-label; winsByPersona is prop-drilled Bots.tsx -> PersonaGrid -> PersonaCard with no useQuery in either component"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaCard.test.tsx#PersonaCard win-stars row (Phase 185) — 8 new tests: overflow cap, 1-filled/2-outline, zero-state no-text, undefined-identical-to-zero + stays clickable, separate aria-labels, singular '1 win', mutation-check"
        status: pass
      - kind: other
        ref: "grep -c useQuery PersonaCard.tsx -> 0; grep -c useQuery PersonaGrid.tsx -> 1 (a doc-comment mention only, no actual call — verified by reading the matched line)"
        status: pass
      - kind: other
        ref: "npx tsc -b (zero errors); npm test -- --run (2518/2518 passed); npm run lint (0 errors); npm run knip (clean)"
        status: pass
    human_judgment: false

duration: 28min
completed: 2026-07-22
status: complete
---

# Phase 185 Plan 03: Persona Win-Stars Frontend Summary

**Wired the per-persona win-stars UI end-to-end: `STAR_FILLED`/`STAR_EMPTY` theme constants, a `useBotPersonaWins` hook against Plan 01's endpoint, `persona_id` sent on every finished bot game, and a `PersonaStars` row (min(wins,3) gold + remainder grey) prop-drilled from a single `Bots.tsx` fetch through `PersonaGrid` into every `PersonaCard`.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-07-22T18:17:00Z
- **Completed:** 2026-07-22T18:25:00Z
- **Tasks:** 2 (1 auto, 1 TDD auto)
- **Files modified:** 9 (1 new hook, 8 modified)

## Accomplishments
- `theme.ts` gained `STAR_FILLED`/`STAR_EMPTY` as independent named constants (not an alias of `FLAWCHESS_ENGINE_ACCENT`)
- `useBotPersonaWins` hook mirrors `useUserProfile`'s exact shape against `GET /bots/persona-wins`; `botsApi.getPersonaWins` + `PersonaWinsResponse` type added alongside
- `toStoreRequest` now sends `persona_id: entry.settings.personaId ?? null` on every finished bot game — `isValidPendingEntry` left untightened so old queued localStorage entries (predating the field) still round-trip
- `PersonaCard` renders a new `PersonaStars` row: exactly `MAX_DISPLAY_STARS` (3) star glyphs, `Math.min(wins, 3)` gold-filled left-to-right + remainder grey-outline; `undefined`/`0` render identically (all-outline, no visible "0 wins" text); the stars-row `<span>` carries its own `aria-label` ("N win"/"N wins"), kept separate from the card button's persona-identity `aria-label`
- `Bots.tsx` calls `useBotPersonaWins()` exactly once and threads `winsByPersona` through `PersonaGrid` → `PersonaCard` as `winsForPersona` — neither intermediate component calls `useQuery`, preserving their existing no-`QueryClientProvider` render tests
- Mutation-verified: the `PersonaStars` render logic was restructured (filled-count/empty-count split, rather than a single fixed-length loop) specifically so the `Math.min` cap is load-bearing — reverting it was confirmed to break the overflow test (more than 3 stars render), then reverted back

## Task Commits

1. **Task 1: Win-count fetch plumbing — theme constants, type, api client, hook, store-request field** - `4c7a8c20` (feat)
2. **Task 2: PersonaStars row + prop-drill winsByPersona through Bots.tsx → PersonaGrid → PersonaCard** - `704244db` (feat)

## Files Created/Modified
- `frontend/src/hooks/useBotPersonaWins.ts` (new) - `useQuery<PersonaWinsResponse>` against `/bots/persona-wins`, `queryKey: ['botPersonaWins']`, `staleTime: 300_000`
- `frontend/src/lib/theme.ts` - `STAR_FILLED`/`STAR_EMPTY` named exports
- `frontend/src/types/bots.ts` - `StoreBotGameRequest.persona_id`, `PersonaWinsResponse` type alias
- `frontend/src/api/client.ts` - `botsApi.getPersonaWins`
- `frontend/src/hooks/useStoreBotGame.ts` - `toStoreRequest` adds `persona_id: entry.settings.personaId ?? null`
- `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` - updated full-object mapping test + 2 new personaId-mapping tests
- `frontend/src/components/bots/PersonaCard.tsx` - `PersonaStars` sub-component, `MAX_DISPLAY_STARS` constant, `winsForPersona?: number` prop
- `frontend/src/components/bots/PersonaGrid.tsx` - `winsByPersona?: Record<string, number>` prop, passed to each `PersonaCard`
- `frontend/src/components/bots/__tests__/PersonaCard.test.tsx` - 8 new win-stars-row tests
- `frontend/src/pages/Bots.tsx` - single `useBotPersonaWins()` call, threaded into `PersonaGrid`

## Decisions Made
- `STAR_FILLED`/`STAR_EMPTY` are independently-declared constants, not an import of `FLAWCHESS_ENGINE_ACCENT`, even though `STAR_FILLED`'s value matches it numerically (per UI-SPEC's explicit instruction)
- Restructured `PersonaStars`' render loop as a filled-count/empty-count split rather than a single `MAX_DISPLAY_STARS`-length loop with an `i < filledCount` check — the single-loop form would render exactly 3 stars regardless of whether `Math.min` was applied (since the array length itself was already capped at 3), making the plan's required "mutation check: reverting the cap fails the test" impossible to satisfy honestly. The split form (`Array.from({length: filledCount})` + `Array.from({length: emptyCount})`) makes a raw win count above 3 genuinely overflow the row when the cap is removed, so the mutation check is real
- Passed `STAR_FILLED`/`STAR_EMPTY` directly as the `fill`/`color` prop values on each `Star` glyph rather than relying on lucide's `fill="currentColor"` + ambient CSS `color` inheritance — functionally identical result, no dependency on an ambient `color` style that isn't otherwise set
- `winsByPersona` kept optional on `PersonaGridProps` (matches the plan's literal action text) even though `Bots.tsx` always supplies it — preserves existing `PersonaGrid.test.tsx` call sites that omit the prop

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated the pre-existing `toStoreRequest` full-object-equality test to include the new `persona_id` field**
- **Found during:** Task 1 verification (`npx vitest run src/hooks`)
- **Issue:** `useStoreBotGame.test.ts`'s "maps every PendingStoreEntry field to its StoreBotGameRequest counterpart" test asserted `toEqual` against a literal object that predated the new `persona_id` field, so it failed once the field was added
- **Fix:** Added `persona_id: null` to the expected object, plus two new focused tests (`personaId` maps through; absent `personaId` falls back to `null`)
- **Files modified:** `frontend/src/hooks/__tests__/useStoreBotGame.test.ts`
- **Commit:** `4c7a8c20`

## Issues Encountered

None blocking. The `PersonaStars` render-structure choice (filled/empty split vs. single capped loop) was discovered mid-Task-2 while performing the plan's required mutation check: the first implementation attempt (single `MAX_DISPLAY_STARS`-length loop) passed all functional tests but the mutation check itself was a no-op (removing `Math.min` didn't change rendered output, since the loop's own length was already capped). Restructured to the filled/empty split so the cap is genuinely load-bearing, then re-ran and confirmed the mutation check fails as required before reverting.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 185 is now feature-complete across all 3 plans: backend win tracking (01), grid transpose (02), and frontend win-stars (03)
- Full wave merge gate green: `npx tsc -b` clean, `npm test -- --run` 2518/2518 passed, `npm run lint` 0 errors (3 pre-existing unrelated `coverage/` warnings), `npm run knip` clean
- Manual verification per 185-VALIDATION.md (play/finish a persona game, confirm a gold star appears; confirm zero-win cards show 3 grey-outline stars) remains a human-in-the-loop step, not run by this executor

---
*Phase: 185-bots-roster-transpose-win-stars*
*Completed: 2026-07-22*

## Self-Check: PASSED

All 10 created/modified files found on disk; both task commit hashes (`4c7a8c20`, `704244db`) found in `git log`.
