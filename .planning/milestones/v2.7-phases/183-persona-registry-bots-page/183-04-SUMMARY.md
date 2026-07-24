---
phase: 183-persona-registry-bots-page
plan: 04
subsystem: ui
tags: [react, typescript, chess, bots, personas, radix-dialog]

# Dependency graph
requires:
  - phase: 183-01
    provides: "PERSONA_REGISTRY (24-slot registry), STYLE_SECTION_ORDER/personasForSection/personaForId, placeholderAvatarFor/resolveAvatarSrc, botPersonaSetupSettings (last-used color/TC), per-style theme accents"
  - phase: 183-03
    provides: "BotGameSettings.personaId?"
provides:
  - "PersonaGrid — the Bots page's default setup view: 4 style sections x 6 personas ascending by rung, plus a Custom entry"
  - "PersonaCard — a single tappable persona tile (avatar, name, tilde ELO label)"
  - "PersonaDetailSurface — a controlled Dialog showing bio + reused color/TC chips + one Play button, building a fully-pinned BotGameSettings and calling onStart exactly once"
  - "Bots.tsx wiring: PersonaGrid is the default setup view; selecting Custom routes to the unchanged SetupScreen; both Play and Start call the single existing handleStart"
affects: [183-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PersonaDetailSurface mirrors GameResultDialog's Dialog shell + mobile-anchor pattern (top-[30%] sm:top-1/2) and mirrors SetupScreen's TcBucketGroup markup + CHIP_* classes verbatim under its own persona-tc-*/persona-color-* testid convention"
    - "A Custom-mode escape hatch renders as a sibling above the untouched child component (a small back-button div before <SetupScreen/>), never as a wrapper around it — keeps the child's own root/props byte-identical"
    - "Avatar rendering checks resolveAvatarSrc(persona) first (future real-art image), falling back to the placeholderAvatarFor emoji — a backstop that also keeps the D-17 forward-compat seam consumed (non-dead) per npm run knip"

key-files:
  created:
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/PersonaCard.tsx
    - frontend/src/components/bots/PersonaDetailSurface.tsx
    - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
    - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
    - frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx
  modified:
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "PersonaCard/PersonaDetailSurface consume resolveAvatarSrc (not just placeholderAvatarFor) — required by this plan's own backstop truth and to keep knip green; every persona still omits avatarSrc today so this is currently a no-op fallback path"
  - "The Custom-mode 'back to grid' affordance is a sibling <div> rendered BEFORE <SetupScreen/>, not a wrapper around it — SetupScreen.tsx stays completely unmodified (PERS-04 prohibition)"
  - "Bots.tsx's handleStart/handleNewGame/handleDiscard additionally reset the new local detailPersona/showCustomSetup state to the grid default — additive resets only, the existing boot/snapshot plumbing in each callback is untouched"
  - "startFromSetup() in Bots.test.tsx now routes through the bots-persona-custom entry first, so every pre-existing SetupScreen-driven test in that file kept working with a one-line helper change rather than per-test rewrites"

patterns-established:
  - "A routed 'escape hatch' to an unchanged legacy component is wired via local page-level UI state (open/closed), never a prop change to the legacy component"

requirements-completed: [PERS-01]

coverage:
  - id: D1
    description: "PersonaGrid renders all 24 personas grouped into the 4 STYLE_SECTION_ORDER sections, each ascending by rung 800->1800, plus a Custom entry"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaGrid.test.tsx > renders exactly 24 persona cards, grouped into 4 sections in STYLE_SECTION_ORDER (DOM order)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaGrid.test.tsx > renders a Custom entry that invokes onSelectCustom on click"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each PersonaCard shows the placeholder avatar (emoji on per-style tint, with a real-art fallback path), name, and a tilde-prefixed provisional ELO label; tapping fires onSelect"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaCard.test.tsx (6 tests: name/label/avatar, aria-label, onSelect call, text-sm floor, avatarSrc backstop x2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "PersonaDetailSurface shows the full bio, reused color/TC chips (CHIP_* classes), and defaults to the persisted last-used color/TC values; no EloSelector/PlayStyleControl import (Pitfall 3)"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx (rendering + defaulting describe blocks, 5 tests)"
        status: pass
      - kind: other
        ref: "grep -n 'EloSelector|PlayStyleControl' frontend/src/components/bots/PersonaDetailSurface.tsx — only a doc-comment mention, no import"
        status: pass
    human_judgment: false
  - id: D4
    description: "Play builds a complete BotGameSettings (botElo=persona.botElo, blend=persona.blend, style=BOT_STYLE_BUNDLES[persona.style] by reference, resolved userColor, baseSeconds/incrementSeconds from the chosen TC, personaId=persona.id), persists the color/TC preference, and calls onStart exactly once"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx > Play builds the pinned BotGameSettings (PERS-02) (3 tests: settings shape + reference identity, Random resolution, persistence)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Bots.tsx's setup-phase branch renders PersonaGrid by default; selecting a persona opens the detail surface whose Play routes through the single existing handleStart; selecting Custom shows the unchanged SetupScreen; both Play and Start call the SAME handleStart (no parallel start path); snapshot/resume precedence unaffected"
    requirement: "PERS-01, PERS-02, PERS-04"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx > Bots — setup/resume/new-game convergence (V-11) (grid-by-default, Custom routing, persona->detail->Play->handleStart, snapshot-beats-both, discard/new-game fall through to grid — full describe block + the rest of the 24-test suite unaffected)"
        status: pass
      - kind: other
        ref: "git diff --stat frontend/src/components/bots/SetupScreen.tsx — empty (byte-unchanged this plan)"
        status: pass
    human_judgment: false
---

# Phase 183 Plan 04: Persona Browsing + One-Action-Start UI Summary

**PersonaGrid/PersonaCard/PersonaDetailSurface (24-persona browse grid + Dialog-based detail surface with reused color/TC chips) slotted into Bots.tsx as the new default setup view, with the unchanged SetupScreen reachable via a routed Custom entry — both paths converge on the single existing `handleStart`.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-22T09:36:00Z (approx, per session start)
- **Completed:** 2026-07-22T09:49:00Z
- **Tasks:** 3
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments

- `PersonaCard.tsx`: a compact tappable `<button>` (`data-testid="bots-persona-card-{id}"`) showing the avatar (real-art `resolveAvatarSrc` image when present, D-18 emoji-on-tint placeholder otherwise — never crashes on an absent/pending avatarSrc), the persona's name, and a tilde-prefixed provisional ELO label (`~800`, never a raw unqualified number).
- `PersonaGrid.tsx`: iterates `STYLE_SECTION_ORDER`, rendering the 4 style sections (Attacker/Trickster/Grinder/Wall — D-14, never "Solid Wall") each with its 6 personas ascending by rung via `personasForSection`, plus one clearly-visible `bots-persona-custom` entry routing to `SetupScreen`.
- `PersonaDetailSurface.tsx`: a controlled `Dialog` (mirrors `GameResultDialog`'s shell + `top-[30%] sm:top-1/2` mobile anchor) showing the avatar/name, DISPLAY-ONLY style + tilde-ELO text, full bio, and the exact `SetupScreen` color/TC chip markup (`CHIP_BASE_CLASS`/`CHIP_ACTIVE_CLASS`/`CHIP_INACTIVE_CLASS`) under its own `persona-color-*`/`persona-tc-*` testids, defaulting to `readPersonaSetupSettings(ownerKey) ?? DEFAULT_PERSONA_SETUP_SETTINGS` every time it opens. Play resolves an unresolved Random preference to a concrete color (D-12), builds the fully-pinned `BotGameSettings` (`botElo`/`blend`/`personaId` pinned by the persona, `style` resolved **by reference** via `BOT_STYLE_BUNDLES[persona.style]`, never cloned), persists the chosen preference, and calls `onStart` exactly once. Imports neither `EloSelector` nor `PlayStyleControl` (Pitfall 3).
- `Bots.tsx`: the `startedSettings === null` branch now defaults to `PersonaGrid`; selecting a persona opens `PersonaDetailSurface` (`onStart={handleStart}`); selecting Custom shows the byte-unchanged `SetupScreen` (`onStart={handleStart}`) with a small back-button sibling above it (never a wrapper around it). New local state (`detailPersona`, `showCustomSetup`) is additive only — the snapshot/resume precedence and boot plumbing above it are untouched — and resets to the grid default whenever `handleStart`/`handleNewGame`/`handleDiscard` fire.
- `Bots.test.tsx`: `startFromSetup()` now routes through the Custom entry first (one-line helper change kept every pre-existing SetupScreen-driven test working); added 3 new tests pinning the grid-by-default view, Custom routing, and the persona → detail → Play → `handleStart` path (asserting the resulting settings carry `personaId`).

## Task Commits

Each task was committed atomically:

1. **Task 1: PersonaGrid + PersonaCard (browse, 4 sections x 6 rungs)** - `6d7ed94e` (feat)
2. **Task 2: PersonaDetailSurface (bio + color/TC chips + one-action Play)** - `429b1371` (feat)
3. **Task 3: Bots.tsx setup branch renders PersonaGrid by default (Custom routed)** - `85796def` (feat, includes the resolveAvatarSrc backstop fix + PersonaCard test update)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `frontend/src/components/bots/PersonaGrid.tsx` - the Bots page's default setup view: 4 style sections + Custom entry
- `frontend/src/components/bots/PersonaCard.tsx` - a single tappable persona tile
- `frontend/src/components/bots/PersonaDetailSurface.tsx` - bio + reused color/TC chips + one-action Play dialog
- `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx` - 5 tests: 24-card DOM order, per-card content, Custom entry, onSelectPersona, text-sm floor
- `frontend/src/components/bots/__tests__/PersonaCard.test.tsx` - 6 tests: content/aria-label/onSelect/text-sm floor + the avatarSrc backstop (image vs emoji fallback)
- `frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx` - 8 tests: rendering, no-strength-picker, null-persona no-op, default seeding (persisted vs fallback), Play settings shape (incl. style reference identity), Random resolution, persistence
- `frontend/src/pages/Bots.tsx` - setup-phase branch swapped to PersonaGrid-by-default with Custom routing
- `frontend/src/pages/__tests__/Bots.test.tsx` - `startFromSetup()` routes through Custom; 3 new tests for the grid/Custom/persona-Play paths; existing assertions updated from `setup-screen` to `bots-persona-grid` where they pinned the default entry point

## Decisions Made

- **Consumed `resolveAvatarSrc` in both new avatar-rendering call sites** (not just `placeholderAvatarFor`): the plan's own backstop truth ("a persona whose real-art avatarSrc is absent/pending never crashes the card") describes real conditional behavior, not just a passive fallback value — and leaving `resolveAvatarSrc` uncalled left it as a genuinely unused export, failing the plan's own `<verification>` block (`npm run knip` exited 1). Wiring it as `avatarSrc ? <img .../> : emoji` in both `PersonaCard` and `PersonaDetailSurface` satisfies both. See Deviations below.
- **Custom-mode back affordance is a sibling, not a wrapper**: rendered as a small `<Button variant="ghost" size="icon">` in its own `<div>` immediately before `<SetupScreen/>` (a `<>...</>` fragment), so `SetupScreen`'s own root `className`/props are untouched — satisfies the plan's explicit "SetupScreen.tsx stays byte-unchanged" prohibition (confirmed via `git diff --stat`, empty).
- **State resets are additive-only in `handleStart`/`handleNewGame`/`handleDiscard`**: each callback gained exactly two new `setShowCustomSetup(false)`/`setDetailPersona(null)` lines: the existing snapshot/boot logic in each callback is unchanged line-for-line.
- **`startFromSetup()` test helper routes through Custom first** rather than rewriting the ~20 downstream tests that call it: since the helper is the single choke point every pre-existing SetupScreen-driven test uses, a one-line prepend (click `bots-persona-custom`, wait for `setup-screen`) kept the entire suite green without touching test bodies that don't care about the entry point.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] `resolveAvatarSrc` left unused, failing the plan's own `npm run knip` verification gate**
- **Found during:** Task 3 verification (running the plan's full `<verification>` block)
- **Issue:** Task 1/2's initial implementation used only `placeholderAvatarFor` for avatar rendering. `resolveAvatarSrc` (Plan 01's D-17 forward-compat seam for the future real-art PR) was imported by no runtime code, so `npm run knip` reported it as an unused export and exited 1 — a genuine gate failure, and also an incomplete reading of this plan's own backstop truth ("a persona whose real-art avatarSrc is absent/pending never crashes the card"), which implies the card actually checks `avatarSrc` and falls back, not merely renders the emoji unconditionally.
- **Fix:** `PersonaCard.tsx` and `PersonaDetailSurface.tsx` both now call `resolveAvatarSrc(persona)` and render `<img src={avatarSrc} .../>` when present, falling back to the `placeholderAvatarFor` emoji otherwise. Every persona in `PERSONA_REGISTRY` still omits `avatarSrc` today, so this is currently a no-op fallback path in production — the real branch activates automatically once the future real-art PR populates `avatarSrc` on any persona.
- **Files modified:** `frontend/src/components/bots/PersonaCard.tsx`, `frontend/src/components/bots/PersonaDetailSurface.tsx`, `frontend/src/components/bots/__tests__/PersonaCard.test.tsx`
- **Verification:** `npm run knip` now exits 0 (no unused exports); 2 new `PersonaCard.test.tsx` tests prove both branches (emoji fallback for a real registry persona; `<img>` render for a locally-constructed persona fixture carrying `avatarSrc`).
- **Committed in:** `85796def` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality)
**Impact on plan:** Necessary to satisfy the plan's own backstop must-have and keep its `<verification>` block green. No scope creep — both files touched were already in this plan's `files_modified` list.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PersonaGrid`, `PersonaCard`, and `PersonaDetailSurface` are fully wired into `Bots.tsx` as the default setup view; `SetupScreen` remains reachable, untouched, via the Custom entry.
- Plan 05 (draw-offer banner UI, per the phase's Wave structure) can now rely on `BotGameSettings.personaId` being populated end-to-end for any game started via the persona path — `personaForId(settings.personaId)` resolves the full `Persona` (name/avatar/bio) for that banner.
- The plan's `<objective>` note on D-08 "New opponent" is now satisfied structurally: since `PersonaGrid` is the default setup view, the existing `onNewGame` path (unmodified `handleNewGame`) already returns to it — Plan 05 can wire a result-surface "New opponent"/"Rematch" action against that same path with no further Bots.tsx changes needed for the return-to-grid behavior itself.
- `frontend/src/lib/personas/personaAvatars.ts`'s `resolveAvatarSrc` and `PERSONA_STYLE_TINT` (via `placeholderAvatarFor`) are now both live-consumed; the 183-01-SUMMARY.md note about `personaAvatars.ts` "self-resolving once Plan 04 wires the grid UI" per `npm run knip` is now fully resolved (confirmed 0 unused exports).
- Full frontend suite (180 files / 2464 tests) passes; `npx tsc -b` and `npm run lint` are clean; no known gaps or deferred items for this plan.

---
*Phase: 183-persona-registry-bots-page*
*Completed: 2026-07-22*

## Self-Check: PASSED

All 8 created/modified source+test files verified present on disk; all 3 task commit hashes (`6d7ed94e`, `429b1371`, `85796def`) verified present in git log.
