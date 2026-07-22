---
phase: 183-persona-registry-bots-page
plan: 01
subsystem: ui
tags: [typescript, react, chess, bots, registry, localstorage]

# Dependency graph
requires:
  - phase: 182-style-levers
    provides: BOT_STYLE_BUNDLES (4 named style bundles), styleLinesFor per-style opening books, playStyle.ts preset constants (HUMAN_BLEND/LIGHT_BLEND/DEEP_BLEND)
provides:
  - PERSONA_REGISTRY (24-slot Record<PersonaId, Persona>, exhaustive at compile time)
  - RUNG_BLEND rung->preset table, STYLE_SECTION_ORDER, personasForSection, personaForId
  - personaAvatars.ts placeholder-avatar helpers (placeholderAvatarFor, resolveAvatarSrc)
  - botPersonaSetupSettings.ts last-used color/TC persistence (own key prefix)
  - 4 per-style theme accent constants (ATTACKER/TRICKSTER/GRINDER/WALL_ACCENT + _BG)
  - personaAvatarPrompts.md (24 persona prompt descriptors for the future real-art PR)
affects: [183-02, 183-03, 183-04, 183-05, 184-persona-calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Exhaustive Record<PersonaId, Persona> over a template-literal id union — mirrors botStyleBundles.ts's Record<Style, BotStyleParams> exhaustiveness convention"
    - "Persona.style resolved by BOT_STYLE_BUNDLES[style] by reference only, never spread/cloned (Pitfall 4)"
    - "localStorage settings persistence mirrored verbatim from botSetupSettings.ts under a new, distinct key prefix"

key-files:
  created:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/lib/personas/personaAvatars.ts
    - frontend/src/lib/personas/botPersonaSetupSettings.ts
    - frontend/src/data/personaAvatarPrompts.md
    - frontend/src/lib/personas/__tests__/personaRegistry.test.ts
    - frontend/src/lib/personas/__tests__/botPersonaSetupSettings.test.ts
  modified:
    - frontend/src/lib/theme.ts

key-decisions:
  - "botElo === rung for all 24 personas this phase (A1, pre-calibration placeholder) — Phase 184 replaces with measured values"
  - "RUNG_BLEND[1600] holds a canonical LIGHT_BLEND default for Record<Rung,number> completeness, but each of the 4 personas at rung 1600 picks Light or Deep explicitly per style identity (2 Light: Attacker/Wall, 2 Deep: Trickster/Grinder), justified inline"
  - "24 species/names/bios authored per D-09..D-14 (animal roster, size ascending with rung, 'Name the Species' convention, playful third-person 2-3 sentence bios) — pending user UAT review/swap per D-13"
  - "personaAvatars.ts ships D-18 placeholder-only (emoji+tint); zero Vite asset-import machinery built (RESEARCH.md Pitfall 6) — resolveAvatarSrc is the single forward-compat seam for the future real-art PR"
  - "botPersonaSetupSettings persists ONLY colorPreference+tcLabel — ELO/blend/style pinned by the persona itself, not persisted"

patterns-established:
  - "New localStorage settings modules mirror botSetupSettings.ts's control flow verbatim (SSR guard -> try/catch -> validate -> Sentry-once -> silent no-op) under their own key prefix"
  - "Per-style theme accent constants follow the MAIA_ACCENT/_BG naming + oklch convention, with explicit hue-collision-avoidance reasoning in the doc comment"

requirements-completed: [PERS-03, AVAT-02]

coverage:
  - id: D1
    description: "PERSONA_REGISTRY exhaustively defines 24 valid personas, 6 per style, each a complete valid BotGameSettings fragment (botElo in MAIA_ELO_LADDER, blend in {HUMAN,LIGHT,DEEP}, style resolved by reference to a BOT_STYLE_BUNDLES singleton)"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "RUNG_BLEND rung->preset table (800-1400 Human, 1800 Deep, 1600 defined) and STYLE_SECTION_ORDER/personasForSection ascending-by-rung ordering"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "personaForId is a plain guarded object index that never throws on an unrecognized id"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every persona has an authored non-empty name/bio, and 24 distinct species, carrying each style's per-tier arc (D-12)"
    requirement: "AVAT-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts"
        status: pass
      - kind: manual_procedural
        ref: "User reviews the full 24-persona roster in UAT and requests name/species/bio swaps (D-13)"
        status: unknown
    human_judgment: true
    rationale: "D-13 explicitly requires human review of the authored roster content (names/species/bios) even though the shape is unit-tested — content quality/tone is a subjective call, same process as Phase 182's curated opening lines."
  - id: D5
    description: "Placeholder avatars (species emoji + per-style tint) and 4 new theme accent constants; committed avatar-generation prompts for all 24 personas"
    verification:
      - kind: unit
        ref: "npx tsc -b (zero errors) + npm run lint (zero errors)"
        status: pass
      - kind: other
        ref: "grep checks: no .webp/.png import statements, no import.meta.glob, all 24 persona ids referenced in personaAvatarPrompts.md, no frontend/src/assets/personas directory"
        status: pass
    human_judgment: false
  - id: D6
    description: "botPersonaSetupSettings persists last-used color+TC under a new distinct key prefix with strict colorPreference validation, tolerant tcLabel, and Sentry-once corruption recovery"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/botPersonaSetupSettings.test.ts"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-22
status: complete
---

# Phase 183 Plan 01: Persona Registry & Bots Page Foundation Summary

**24-slot typed persona registry (4 styles x 6 ELO rungs) with authored animal names/bios, D-18 placeholder avatars, per-style theme accents, and a last-used color/TC persistence helper — the data foundation every downstream Bots-page plan consumes.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-22T08:58:14Z (per STATE.md session start)
- **Completed:** 2026-07-22T09:10:52Z
- **Tasks:** 3
- **Files modified:** 7 (6 created, 1 modified)

## Accomplishments

- `PERSONA_REGISTRY`: an exhaustive `Record<PersonaId, Persona>` (24 entries, compile-time-enforced completeness) mapping each of the 4 styles x 6 rungs to a complete pinned opponent config
- `RUNG_BLEND` rung->preset table (800-1400 Human, 1800 Deep, 1600 canonical default with per-persona Light/Deep discretion), `STYLE_SECTION_ORDER`, `personasForSection`, `personaForId`
- 24 authored animal personas (distinct species, ascending body size within each style, "Name the Species" naming, playful third-person bios carrying each tier's story) per D-09..D-14
- D-18 placeholder-avatar system (`personaAvatars.ts`): species emoji on a per-style background tint, plus a single forward-compat seam (`resolveAvatarSrc`) for the future real-art PR
- 4 new per-style theme accent constants (`ATTACKER_ACCENT`/`TRICKSTER_ACCENT`/`GRINDER_ACCENT`/`WALL_ACCENT` + `_BG` variants) in `theme.ts`
- `personaAvatarPrompts.md`: a master cel-shaded style prompt (matching the horse-logo look) + 24 per-persona prompt descriptors, committed for the future avatar-generation PR
- `botPersonaSetupSettings.ts`: last-used color/TC persistence under a brand-new, distinct localStorage key prefix, mirroring the hardened `botSetupSettings.ts` pattern verbatim

## Task Commits

Each task was committed atomically:

1. **Task 1: Persona registry, rung→preset table, and section order** - `10c16329` (feat)
2. **Task 2: Placeholder avatars, per-style accents, and committed avatar prompts** - `3b16af0d` (feat)
3. **Task 3: Last-used persona color/TC persistence (botPersonaSetupSettings)** - `d7d65605` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `frontend/src/lib/personas/personaRegistry.ts` - 24-slot exhaustive persona registry, RUNG_BLEND, STYLE_SECTION_ORDER, personasForSection, personaForId
- `frontend/src/lib/personas/__tests__/personaRegistry.test.ts` - 22 shape/identity/reference-discipline tests
- `frontend/src/lib/personas/personaAvatars.ts` - placeholder-avatar helpers (D-18) + forward-compat avatarSrc seam (D-17)
- `frontend/src/lib/theme.ts` - 4 new per-style accent + `_BG` constants
- `frontend/src/data/personaAvatarPrompts.md` - master style prompt + 24 per-persona descriptors
- `frontend/src/lib/personas/botPersonaSetupSettings.ts` - last-used color/TC persistence, new key prefix
- `frontend/src/lib/personas/__tests__/botPersonaSetupSettings.test.ts` - 16 round-trip/corruption/SSR/tolerance tests

## Decisions Made

- **1600-rung Light/Deep split (Claude's discretion, per plan):** Attacker and Wall use `LIGHT_BLEND` at 1600 (identity carried mainly by feature multipliers/book, not heavy search); Trickster and Grinder use `DEEP_BLEND` at 1600 (swindle-mode/calculating identities benefit from real search). `RUNG_BLEND[1600]` itself holds `LIGHT_BLEND` as the Record's canonical completeness value — individual 1600-rung personas set their own `blend` field explicitly rather than always reading `RUNG_BLEND[1600]`, matching the plan's literal "or the per-persona 1600 choice" instruction and the test's "RUNG_BLEND is defined for 1600 and equals LIGHT_BLEND or DEEP_BLEND" assertion (a single-value check on the table, not a per-persona equality check).
- **Roster content (D-13, pending UAT):** 24 species/names/bios authored per the D-09..D-14 conventions (animal roster matching the horse-logo brand, "Name the Species" naming e.g. "Riko the Raccoon"/"Bruno the Badger" reusing the exact examples from 183-CONTEXT.md, size ascending within each style, playful third-person 2-3-sentence bios carrying each tier's arc). This content is a first draft for the user to review and request swaps on, same process as Phase 182's curated opening lines — flagged as `human_judgment: true` in the coverage block (D4).
- **Theme accent hues:** picked 4 new oklch hues (15/320/165/235) with an explicit collision-avoidance rationale documented inline against every existing WDL/MAIA/severity/tactic hue in `theme.ts`, rather than reusing an existing accent.
- **The tilde-prefixed provisional-ELO label (D-04) is NOT implemented in this plan** — grep-confirmed it is realized in `183-04-PLAN.md`'s `PersonaCard.tsx` (`personasForSection`/`personaForId`/`rung` are the primitives this plan supplies; the tilde-text rendering is a UI concern for the grid plan). Noted here since the truth appears in this plan's frontmatter `must_haves` but its actual implementation is downstream.

## Deviations from Plan

None — plan executed exactly as written. All 3 tasks' acceptance criteria (test suites green, `tsc -b` zero errors, `npm run lint` zero errors, grep-verified absence of style-bundle cloning / eager-glob asset imports / real image files) were met without needing a Rule 1-4 deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PERSONA_REGISTRY`, `personasForSection`, `personaForId`, `RUNG_BLEND`, `STYLE_SECTION_ORDER`, `placeholderAvatarFor`, `resolveAvatarSrc`, `readPersonaSetupSettings`/`writePersonaSetupSettings`/`DEFAULT_PERSONA_SETUP_SETTINGS`, and the 4 theme accents are all ready for Plans 03/04 (PersonaGrid/PersonaCard/PersonaDetailSurface UI) to consume directly.
- `knip` currently flags `personaAvatars.ts` as an unused file and the 4 `*_ACCENT` (non-`_BG`) theme exports as unused — expected per this plan's own `<verification>` note ("knip may warn until Wave 2 wires them"); no action needed, will self-resolve once Plan 04 wires the grid UI.
- AVAT-01 stays intentionally partial/open (D-16): placeholder avatars ship now, curated real-art portraits land in a future PR using the committed `personaAvatarPrompts.md`. Not marked complete in REQUIREMENTS.md.
- No blockers for Plan 02 (draw-offer trigger logic) or Plan 03/04 (Bots page UI) — this plan's exports are additive-only and touch no existing runtime code paths (`Bots.tsx`, `useBotGame.ts`, `SetupScreen.tsx` are all untouched).

---
*Phase: 183-persona-registry-bots-page*
*Completed: 2026-07-22*

## Self-Check: PASSED

All 7 created/modified files verified present on disk; all 4 task/summary commit hashes (`10c16329`, `3b16af0d`, `d7d65605`, `56b29233`) verified present in git log.
