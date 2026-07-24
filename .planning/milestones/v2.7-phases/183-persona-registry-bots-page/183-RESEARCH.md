# Phase 183: Persona Registry & Bots Page - Research

**Researched:** 2026-07-22
**Domain:** Frontend-only React/TypeScript feature (persona data registry + Bots-page UI), building on Phase 182's engine-level style levers
**Confidence:** HIGH (all findings verified directly against the current codebase; zero external libraries involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bots page structure**
- D-01: Grid-first, Custom as escape hatch. The persona grid becomes the default `/bots` view. Custom mode is one clearly-visible entry (e.g. a distinct "Custom" card or button) that opens the existing SetupScreen unchanged. Snapshot-resume precedence (Phase 170/171: `BotsGame` + `ResumeGate` when a snapshot exists) is unaffected.
- D-02: Grid organized by style: 4 sections × 6 rungs. Four style sections (Attacker, Trickster, Grinder, Wall), each showing its 6 characters ascending 800→1800.
- D-03: Compact cards + detail on tap. Card shows avatar, name, ELO label (optionally a one-line tagline). Tapping opens a detail surface (dialog/panel) with the full bio, color/TC controls (D-05), and the Play button.
- D-04: Provisional ELO labels use tilde format (`~1200`). Phase 184 keeps the format and only swaps the number for the calibrated value.

**Persona start & in-game presence**
- D-05: Color and time control are chosen in the detail surface. The persona pins preset/ELO/style/book/policy (PERS-02), but color + TC are session choices: compact chips in the detail dialog, defaulting to last-used (persisted like `botSetupSettings`). One surface, no separate strength step.
- D-06: Full in-game persona presence. Persona avatar + name render in the bot's clock strip (desktop AND mobile), and the result dialog/strip names the persona (e.g. "Riko the Raccoon wins on time").
- D-07: Bot draw offer = non-blocking inline banner near the board/clock area ("[Persona] offers a draw") with Accept and Decline buttons; expires per the Phase 182 policy's cooldown rules or on the user's next move. Play continues while it's up (lichess convention).
- D-08: Post-game result surfaces offer "Rematch [persona]" (same pinned config + same color/TC) alongside the existing analysis actions, plus a "New opponent" path back to the persona grid.

**Names, bios & tone**
- D-09: Animal-themed roster matching the FlawChess horse logo. Small-to-medium animals for 800–1800; large animals reserved for future >2000-ELO bots (SEED-114). Avatar look influenced by playstyle; animals may wear items.
- D-10: 24 distinct species, body size loosely increasing with rung within each style.
- D-11: Naming = "Name the Species" (e.g. "Riko the Raccoon").
- D-12: Bios are playful third-person, 2–3 sentences carrying the AVAT-02 per-tier story.
- D-13: Claude drafts all species/names/bios at execute time; user reviews the full roster in UAT and requests swaps.
- D-14: Style display name is "Wall" (not "Solid Wall"/"Great Wall"). UI copy and registry display names use simply "the Wall".

**Avatar pipeline**
- D-15: Claude writes prompts, user generates. A master style prompt + 24 per-character prompt descriptors are committed in-repo alongside the registry.
- D-16: Phase ships with placeholder avatars; real art lands later. AVAT-01 stays open/partial at phase close — track it rather than blocking the merge.
- D-17: Portrait format: square face-and-shoulders, ~256×256 WebP, imported via Vite from `frontend/src/assets/personas/{persona-id}.webp` (hashed URLs, build-time existence check). Generate at high res, downscale before commit.
- D-18: Placeholder look: species emoji on a per-style background tint.

### Claude's Discretion
- 1600-rung preset choice per persona (Light vs Deep, informed by `reports/data/bot-strength-lookup.json` measured ranges); 800–1400 Human and 1800 Deep are fixed by the requirements.
- Registry file shape and location (typed const registry; suggest colocating near `botStyleBundles.ts` conventions).
- Per-style accent colors for sections/placeholder tints (define in `theme.ts` per frontend rules).
- Snapshot/resume plumbing: persisting persona id in the game snapshot so a resumed game restores full persona identity (avatar, name, policy) and result surfaces.
- Exact detail-surface component (dialog vs drawer) and mobile grid column count.
- Exact species/name/bio roster content (D-13 — user reviews in UAT).
- Prompt file format/location for the avatar prompts.

### Deferred Ideas (OUT OF SCOPE)
- Large-animal personas above 2000 ELO — gated on SEED-114.
- Calibrated ELO labels + floor/ceiling honesty constraints — Phase 184 (CAL-04/05).
- "Suggest next rung up" nudge after a win — out of scope for the result surfaces this phase.
- Final curated avatar art — arrives asynchronously after merge (D-16); AVAT-01 completion tracked past phase close.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERS-01 | Browse 24 named bot personas (4 styles × 6 rungs) with name, avatar, bio, style, ELO label | Grid architecture pattern below; `Persona` registry shape; `theme.ts` per-style accent colors |
| PERS-02 | Start a game against any persona in one action, with the persona's full pinned config, no separate strength step | `BotGameSettings` construction pattern; detail-surface Play flow; `useBotGame`/`selectBotMove`/`styleBookWeighting`/`botDrawGate` already accept everything a persona needs (Phase 182 delivered the engine seams) |
| PERS-03 | Single typed registry mapping each of 24 slots to full config, rung→preset per measured ranges (800–1400 Human, 1600 Light/Deep, 1800 Deep) | `PERSONA_REGISTRY` shape; exact `bot-strength-lookup.json` derived ranges (Pitfall/Code Examples sections) |
| PERS-04 | Custom mode keeps raw (ELO, preset) knobs unchanged | `SetupScreen.tsx` is untouched by construction — the grid becomes a NEW default view, Custom is a routed escape hatch, D-03 (style params optional-everywhere) already guarantees Custom's `BotGameSettings.style` stays `undefined` |
| AVAT-01 | 24 AI-generated avatar portraits, curated, committed as static assets | Ships PARTIAL this phase (D-16): placeholder emoji+tint now (D-18), Vite `webp` import path documented for the future real-art PR (D-17) — no existing precedent for hashed image imports in this codebase, flagged as a new pattern |
| AVAT-02 | Name + short bio per persona conveying style identity and per-tier story | Bio/name authored at execute time (D-13); registry field shape documented below |
</phase_requirements>

## Summary

This phase is pure frontend wiring: a new data registry (24 personas) plus new/extended UI (grid, detail surface, in-game persona presence, outgoing draw-offer banner, rematch flow), consuming primitives Phase 182 already shipped and battle-tested (`BOT_STYLE_BUNDLES`, `styleLinesFor`/`styleBookWeighting`, `botDrawGate.ts`'s `wouldBotAcceptDraw`/`wouldBotResign`, `BotGameSettings.style?`). No new external packages, no backend changes, no new endpoints. The engineering risk is concentrated in three places: (1) correctly threading a new `personaId` identity through `BotGameSettings` → `BotGameSnapshot` → `useBotGame` state → the clock strip / result surfaces / rematch flow without breaking the existing style-bundle reverse-lookup pattern, (2) a **critical scope gap** — the bot's OUTGOING draw-offer trigger logic (D-07) does not exist anywhere in the codebase yet, despite 183-CONTEXT.md's framing that only the banner/buttons are missing (see Pitfall 1 below), and (3) picking a rung→(botElo, blend) mapping that is internally consistent with `MAIA_ELO_LADDER` and `bot-strength-lookup.json`'s measured floors/ceilings, since Phase 184's calibration work depends on this phase's `botElo`/`blend` choices being exactly the "raw preset" values the traceability note describes.

**Primary recommendation:** Build a new `frontend/src/lib/personas/` module holding a `PERSONA_REGISTRY: Record<PersonaId, Persona>` (24 entries, `PersonaId` a literal template type like `` `${StyleSlug}-${Rung}` ``) that composes Phase 182's `BOT_STYLE_BUNDLES` + `styleLinesFor` by reference (never re-implementing style data), sets `botElo` to the rung value itself and `blend` per the fixed rung→preset table, and add ONE new optional field `BotGameSettings.personaId?: string` (mirroring `style?`'s D-03 optionality contract) as the single source of truth threaded through snapshot, clock strip, draw banner, and result surfaces — do not try to reverse-derive persona identity from the style bundle alone, since multiple personas per style share the same `BotStyleParams` object.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Persona grid browsing (PERS-01) | Browser/Client | — | Pure static data render, `/bots` React route, no network |
| Persona registry (PERS-03) | Browser/Client | — | Plain TS module, bundled at build time; no backend/DB involvement (mirrors `botStyleBundles.ts`) |
| Persona game start (PERS-02) | Browser/Client | — | `useBotGame` already runs entirely client-side (WASM Stockfish + Maia ONNX in workers); no server round-trip to start a game |
| Custom mode (PERS-04) | Browser/Client | — | Existing `SetupScreen.tsx`, unchanged |
| In-game persona presence (clock strip, draw banner, result naming) | Browser/Client | — | Same `useBotGame` state machine, extended with a `personaId` field |
| Snapshot/resume persona identity | Browser/Client | — | `localStorage`, owner-scoped, mirrors `botGameSnapshot.ts` |
| Finished-game persistence (unrelated to persona identity itself) | API/Backend | Browser/Client | Existing `useStoreBotGame`/`toStoreRequest` pipeline (Phase 170/171) — out of scope to modify; a persona game's PGN/settings store exactly as a Custom game does today, no backend schema change needed for this phase |
| Avatar assets | CDN/Static | Browser/Client | Placeholder this phase (inline emoji+tint, zero asset weight); future real portraits become Vite-bundled hashed static assets served from the CDN edge, same as every other build asset |

## Standard Stack

No new libraries. This phase composes 100% existing, already-installed dependencies:

### Core (already in use, no version changes needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 + TypeScript | (repo-pinned) | Grid, detail dialog, banner components | Existing stack |
| `chess.js` | (repo-pinned) | Already consumed transitively via `useBotGame`/`selectBotMove` | No new usage surface for this phase |
| shadcn `Dialog`/`Drawer` (`components/ui/dialog.tsx`, `components/ui/drawer.tsx`) | n/a (local components) | Detail surface (D-03 Claude's-discretion: dialog vs drawer) | Both primitives already exist and are used elsewhere (`GameControls.tsx`'s resign confirm uses `Dialog`) — no new primitive needed |
| `lucide-react` | ^1.21.0 | Icons (e.g. a "swap opponent"/chevron icon on cards) | Already a dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| none | — | — | — |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain `Record<PersonaId, Persona>` const registry | A JSON data file + runtime validation (zod) | Rejected: `botStyleBundles.ts`/`styleOpeningLines.ts` both use plain typed TS const registries with zero runtime validation — the project convention for this exact kind of data, and it gets full TypeScript exhaustiveness checking (`Record<Style, ...>` pattern) for free, which a JSON file would not |
| Vite `import.meta.glob` for future avatar assets | Per-file named imports (24 explicit `import x from '@/assets/personas/riko.webp'`) | `import.meta.glob('./personas/*.webp', { eager: true })` silently omits files that don't exist yet (no build error for a missing persona), which conflicts with D-17's "build-time existence check" requirement; 24 explicit named imports DO fail the build if a referenced file is absent — but this phase ships placeholders (D-16/D-18) and does not need working image imports yet, so defer this decision to whenever real art lands |

**Installation:**
```bash
# No new dependencies — nothing to install.
```

**Version verification:** N/A — no new packages introduced this phase.

## Package Legitimacy Audit

**No new external packages are installed by this phase.** All functionality is built from existing project dependencies and hand-written TypeScript/React. This section is intentionally empty — the Package Legitimacy Gate protocol does not apply.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │   /bots route (BotsPage)     │
                         └──────────────┬───────────────┘
                                         │
                     snapshot exists?    │   no snapshot
                    ┌────────────────────┴────────────────────┐
                    ▼                                          ▼
           BotsGame (resume)                        NEW: setup-phase branch
                                                                │
                                          ┌─────────────────────┴─────────────────────┐
                                          ▼                                           ▼
                              PersonaGrid (NEW, default)                   "Custom" entry (D-01)
                              4 style sections × 6 cards                              │
                                          │                                           ▼
                                tap a card (D-03)                          SetupScreen (UNCHANGED,
                                          │                                  PERS-04)
                                          ▼
                        PersonaDetailSurface (NEW: dialog/drawer)
                        avatar + name + bio + style + ELO label
                        color chips + TC chips (reused chipStyles.ts
                        pattern from SetupScreen.tsx, D-05)
                                          │
                                    tap "Play"
                                          ▼
                     build BotGameSettings { botElo, blend, style:
                     BOT_STYLE_BUNDLES[persona.style], userColor,
                     baseSeconds, incrementSeconds, personaId: persona.id }
                                          │
                                          ▼
                              BotsPage.handleStart(settings)
                                          │
                                          ▼
                        BotsGame mounts → useBotGame(settings, …)
                        (UNCHANGED engine: selectBotMove / styleBookWeighting /
                         botDrawGate — all already accept `style`)
                                          │
                     ┌────────────────────┼─────────────────────────┐
                     ▼                    ▼                         ▼
          ClockDisplay (bot side)   NEW: BotDrawOfferBanner   GameResultDialog/Strip
          gains avatar+name via     (D-07 — REQUIRES a NEW    gains persona name (D-06)
          personaId → registry      trigger predicate in       + "Rematch [persona]" +
          lookup (D-06)             botDrawGate.ts, see        "New opponent" (D-08)
                                     Pitfall 1 — does NOT
                                     exist yet)
```

### Recommended Project Structure
```
frontend/src/
├── lib/
│   ├── engine/
│   │   ├── botStyleBundles.ts        # UNCHANGED (Phase 182 output, consumed by reference)
│   │   └── styleOpeningLines.ts      # UNCHANGED
│   ├── personas/                     # NEW directory — persona is product/UI data, not pure engine data
│   │   ├── personaRegistry.ts        # NEW: PersonaId type + PERSONA_REGISTRY const + rung→preset table
│   │   ├── personaAvatars.ts         # NEW: placeholder emoji/tint map (D-18) + avatar-prompt doc pointer
│   │   └── botPersonaSetupSettings.ts # NEW: last-used color/TC persistence (mirrors botSetupSettings.ts)
│   └── botDrawGate.ts                # EXTENDED: add wouldBotOfferDraw (Pitfall 1)
├── hooks/
│   └── useBotGame.ts                 # EXTENDED: BotGameSettings.personaId?; bot-outgoing-offer state
├── components/
│   └── bots/
│       ├── PersonaGrid.tsx           # NEW
│       ├── PersonaCard.tsx           # NEW
│       ├── PersonaDetailSurface.tsx  # NEW (dialog or drawer, Claude's discretion)
│       ├── BotDrawOfferBanner.tsx    # NEW (D-07)
│       ├── ClockDisplay.tsx          # EXTENDED: optional avatar+name
│       ├── GameResultDialog.tsx      # EXTENDED: persona name + Rematch/New opponent
│       └── GameResultStrip.tsx       # EXTENDED: mirrors dialog (mobile parity)
├── data/
│   └── personaAvatarPrompts.md       # NEW (or .ts) — the 24 prompt descriptors, D-15
└── pages/
    └── Bots.tsx                       # EXTENDED: setup-phase branch renders PersonaGrid by default
```

### Pattern 1: Registry composes Phase 182 primitives by reference, never by re-derivation

**What:** Each `Persona` entry stores a `style: Style` key (not a copy of `BotStyleParams`) and resolves `BOT_STYLE_BUNDLES[persona.style]` at game-start time, exactly like `useBotGame.ts`'s existing `styleNameFor` reverse-lookup does for the opposite direction.
**When to use:** Every persona-to-`BotGameSettings` construction site.
**Example:**
```typescript
// frontend/src/lib/personas/personaRegistry.ts (illustrative shape)
import type { Style } from '@/lib/engine/styleOpeningLines';
import { BOT_STYLE_BUNDLES } from '@/lib/engine/botStyleBundles';

export type Rung = 800 | 1000 | 1200 | 1400 | 1600 | 1800;
export type PersonaId = `${Lowercase<Style>}-${Rung}`;

export interface Persona {
  id: PersonaId;
  style: Style;               // reference key, NOT a copy of BotStyleParams
  rung: Rung;                 // the provisional ELO label's numeric value (D-04: displayed as `~${rung}`)
  botElo: number;              // engine-facing ELO (this phase: === rung, see Pitfall 2)
  blend: number;                // HUMAN_BLEND | LIGHT_BLEND | DEEP_BLEND, per the fixed rung table
  name: string;                 // e.g. "Riko the Raccoon" (D-11, authored at execute time)
  species: string;              // e.g. "Raccoon"
  bio: string;                  // 2-3 sentences (D-12)
  avatarEmoji: string;          // placeholder (D-18)
}

// Play-button construction (PersonaDetailSurface.tsx):
function buildPersonaSettings(persona: Persona, userColor: MoverColor, tc: TimeControlPreset): BotGameSettings {
  return {
    botElo: persona.botElo,
    blend: persona.blend,
    style: BOT_STYLE_BUNDLES[persona.style],   // reference, not a struct copy
    userColor,
    baseSeconds: tc.baseSeconds,
    incrementSeconds: tc.incrementSeconds,
    personaId: persona.id,                      // NEW field — see Pitfall 3
  };
}
```

### Pattern 2: `personaId` is a NEW, independent field on `BotGameSettings` — do not derive it from `style`

**What:** `useBotGame.ts` already has a `styleNameFor(style)` reverse-lookup by object identity against `BOT_STYLE_BUNDLES`, but that only recovers the STYLE (Attacker/Trickster/Grinder/Wall) — 6 personas per style share the exact same `BotStyleParams` object, so it cannot disambiguate which of the 6 rungs is in play. Persona-aware UI (clock strip name/avatar, draw banner, result naming, rematch) needs the full persona identity.
**When to use:** Everywhere the UI needs to know "which persona is this game" as opposed to "what style knobs are active."
**Example:**
```typescript
// useBotGame.ts's BotGameSettings interface, extended:
export interface BotGameSettings {
  botElo: number;
  blend: number;
  baseSeconds: number;
  incrementSeconds: number;
  userColor: MoverColor;
  style?: BotStyleParams;      // UNCHANGED (Phase 182 D-01/D-03)
  /** NEW (Phase 183): the persona this game was started against, or undefined
   * for a Custom-mode game (PERS-04 — Custom never sets this field, by
   * construction, mirroring style's D-03 optional-everywhere contract). A
   * game's persona identity is looked up ONCE via PERSONA_REGISTRY[personaId]
   * wherever a component needs avatar/name/bio — never re-serialize the
   * whole Persona object into settings/snapshot (mirrors botStyleBundles.ts's
   * own "reference by key membership, not by embedding" doc comment). */
  personaId?: PersonaId;
}
```

### Pattern 3: Snapshot/resume carries `personaId` for free — but the reverse lookup must degrade gracefully

**What:** `BotGameSnapshot.settings` is typed as `BotGameSettings` directly (`botGameSnapshot.ts`), so adding `personaId?` to `BotGameSettings` automatically flows through `writeSnapshot`/`readSnapshot` with **no `CURRENT_SNAPSHOT_VERSION` bump needed** — `isValidSnapshotShape`/`isValidSettingsShape` only assert the pre-existing required fields (`botElo`/`blend`/`baseSeconds`/`incrementSeconds`/`userColor`) and do not reject unknown/extra fields, so an old (pre-183) snapshot still validates with `personaId` simply absent (`undefined`).
**When to use:** Resume path — `PERSONA_REGISTRY[snapshot.settings.personaId]` may be `undefined` if a persona is ever removed/renamed from the registry after being played; every consumer (clock strip, banner, result surface) MUST treat a missing registry entry as "render the existing unstyled/Custom fallback" (e.g. "FlawChess Bot"), never crash.
**Example:**
```typescript
function personaFor(settings: BotGameSettings): Persona | undefined {
  return settings.personaId ? PERSONA_REGISTRY[settings.personaId] : undefined;
}
// ClockDisplay caller:
const persona = personaFor(settings);
<ClockDisplay sideLabel={persona?.name ?? 'FlawChess Bot'} avatarEmoji={persona?.avatarEmoji} ... />
```

### Pattern 4: Reuse `chipStyles.ts` + `SetupScreen.tsx`'s TC/color chip markup verbatim in the detail surface

**What:** `CHIP_BASE_CLASS`/`CHIP_ACTIVE_CLASS`/`CHIP_INACTIVE_CLASS` (`components/bots/chipStyles.ts`) and the `TcBucketGroup`-style 3-bucket TC grid are already the established, tested pattern (used identically by `SetupScreen.tsx` and `PlayStyleControl.tsx`). D-05 explicitly calls for reuse.
**When to use:** Persona detail surface's color + TC controls.

### Anti-Patterns to Avoid
- **Copying `BotStyleParams` into the persona registry:** breaks the "single source of truth" `botStyleBundles.ts` establishes and risks silent drift from Phase 182's hand-tuned values (D-12 provenance comments). Reference `BOT_STYLE_BUNDLES[style]` by key, always.
- **Embedding the whole `Persona` object in `BotGameSettings`/snapshot:** bloats localStorage and the snapshot payload with denormalized bio/name/avatar strings that can go stale if the registry content changes; store `personaId` only and look up fresh at render time (mirrors the project's existing "reference by key membership" convention).
- **A second start path:** the CONTEXT canonical refs explicitly flag `BotsPage`'s "setup vs game vs resume" phase switch as an established invariant (Phase 171) — the persona grid must slot INTO the existing "setup" branch (replacing/gating `SetupScreen` as the default view), not add a parallel entry point.
- **Deriving the bot's outgoing draw-offer purely from `wouldBotAcceptDraw`:** that function only answers "would the bot accept a USER-initiated offer" — it is not reusable as "should the bot itself offer" (see Pitfall 1).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Opening-book style steering | A new book-weighting mechanism | `styleBookWeighting` (`botStyle.ts`, Phase 182) via `useBotGame.ts`'s existing `resolveBookMove` wiring | Already composes `maiaPolicyWeighting`, already handles the SAN-prefix history seam correctly (Pitfall 2 in 182-RESEARCH.md) |
| Draw accept/resign policy | New score-threshold logic | `wouldBotAcceptDraw`/`wouldBotResign` (`botDrawGate.ts`) | Already unit-tested, already wired into `useBotGame.ts`'s post-move grade callback |
| Prior reweighting / score shaping | New per-move feature classifiers | `applyStylePriorReweighting`/`applyStyleScoreShaping` (`botStyle.ts`), invoked inside `selectBotMove.ts` (Plan 06 of Phase 182) | Already wired end-to-end, hand-tuned per D-12 |
| ELO-to-Maia-rung strength selection | A new mapping table | `MAIA_ELO_LADDER` (600–2600, step 100) — every rung (800..1800) is a valid entry | Consistency with `EloSelector`'s existing contract ("value must be present in ladder") |
| localStorage last-used persistence | A bespoke storage shim | Mirror `botSetupSettings.ts`'s SSR-guard → try/catch → JSON.parse → shape-validator → Sentry-once pattern verbatim, under a NEW key | This is the project's established, load-bearing pattern for exactly this kind of preference persistence — deviating risks reintroducing the WR-01/WR-02 bugs that pattern was hardened against |

**Key insight:** Every engine-level capability this phase needs (opening book steering, draw/resign policy, prior reweighting, score shaping) was already built, tuned, and tested in Phase 182. This phase's job is composition and UI, not new engine logic — with exactly ONE exception (Pitfall 1 below), which is new engine-adjacent logic disguised as "just the UI".

## Common Pitfalls

### Pitfall 1: The bot's OUTGOING draw-offer trigger logic does not exist yet — CONTEXT.md's framing is inaccurate
**What goes wrong:** 183-CONTEXT.md's `<domain>` section states this phase "Includes the bot outgoing draw-offer UI explicitly deferred here from Phase 182 (the offer policy already fires in `useBotGame`; only the banner/buttons are missing)." **This is verified false.** A full grep across `botDrawGate.ts`, `useBotGame.ts`, and their test files finds exactly three exported policy functions: `canOfferDraw` (the USER's cooldown throttle), `wouldBotAcceptDraw` (accepting a USER-initiated offer), and `wouldBotResign` (Phase 182, D-07/D-08). There is no `wouldBotOfferDraw` or equivalent anywhere — Phase 182's own D-07 decision literally says "the bot's outgoing draw-offer banner/buttons land with Phase 183's UI," but no accompanying trigger predicate shipped with it (only resignation did).
**Why it happens:** 182-CONTEXT.md's Claude's Discretion section DOES list "draw-offer trigger conditions and cooldowns" as an open item for that phase — it was apparently never actually implemented, only resignation was, and the deferral note in 183-CONTEXT.md was written assuming it had been.
**How to avoid:** Treat D-07 as needing BOTH new engine-adjacent logic AND new UI. Plan for a new pure predicate in `botDrawGate.ts`, e.g. `wouldBotOfferDraw(rootPracticalScore, chess, offerThreshold, contempt, movesSinceLastOwnOffer)`, mirroring `wouldBotResign`'s shape (same `null`-sentinel discipline, same `RESIGN_MIN_FULLMOVE`-style fullmove gate), wired into the SAME post-move `pool.grade(...).then(...)` callback in `useBotGame.ts` that already computes `wouldBotResign`. New `BotStyleParams` field(s) may be needed (an offer threshold/cooldown, since `contempt` alone answers "would I accept," not "would I initiate") — or the existing `contempt` + a fixed near-equal band (mirroring `DRAW_ACCEPT_SCORE_BAND`) may suffice; either way this needs explicit plan-time design, not just component wiring. Budget real engineering time for this, not "UI polish" time.
**Warning signs:** If the plan only lists "build BotDrawOfferBanner.tsx and wire it to an existing hook field," that is the exact trap this CONTEXT.md inaccuracy sets — there is no existing hook field to wire to.

### Pitfall 2: `botElo` vs the displayed rung label are conceptually different numbers — decide the mapping explicitly
**What goes wrong:** The phase requirement PERS-03 says "each rung's preset dictated by the measured ranges (800–1400 Human, 1600 Light/Deep, 1800 Deep)" — this fixes the `blend` (regime) per rung, but says nothing about what numeric `botElo` value each persona's underlying `selectBotMove`/Maia policy call should use. `MAIA_ELO_LADDER` (600–2600, step 100) makes every rung (800/1000/.../1800) a directly valid `botElo` value, so the simplest, most defensible choice for this PRE-calibration phase is `botElo === rung`. This is consistent with the ROADMAP traceability note: "shipped with provisional (raw preset) ELO labels" — i.e., the label IS the raw setting for now, and Phase 184 replaces the DISPLAY label with a calibrated one (it may also revisit the underlying `botElo`/`blend` choice at that point).
**Why it happens:** `bot-strength-lookup.json`'s `derived.*.lookup` tables (e.g. `human.lookup["1200"] = 1900`) are an INVERSE mapping — "what `bot_elo` do I need to feed the engine to make it PLAY LIKE a target blitz-equivalent strength of 1200" — not a forward "what should a persona labeled ~1200 use as botElo" answer. Using the lookup table's inverted values as `botElo` for the 183 registry would be a strength-calibration exercise, which REQUIREMENTS.md explicitly assigns to CAL-04/Phase 184, not this phase.
**How to avoid:** Confirm at plan time (flag to the user if ambiguous) that `botElo = rung` for all 24 personas in this phase, with `blend` per the fixed table (800/1000/1200/1400 → `HUMAN_BLEND`; 1600 → `LIGHT_BLEND` or `DEEP_BLEND` per Claude's discretion informed by the lookup ranges; 1800 → `DEEP_BLEND`). Document this explicitly in the registry file's header comment (mirroring `botStyleBundles.ts`'s provenance-comment convention) so Phase 184 has an unambiguous, auditable starting point to calibrate from.
**Warning signs:** A registry where `botElo` values don't match `MAIA_ELO_LADDER` rungs, or where they were pulled from `bot-strength-lookup.json`'s inverted lookup tables without an explicit justification comment.

### Pitfall 3: `EMPTY grid vs. one-action start` — PERS-02's "no separate strength selection step" excludes an ELO slider on the detail surface
**What goes wrong:** `SetupScreen.tsx`'s `EloSelector` is a natural component to reach for when building the detail surface, but PERS-02 and the phase goal explicitly forbid a persona×strength picker — SEED-098 calls this out as a locked decision and REQUIREMENTS.md's Out of Scope table repeats it ("Persona × strength picker | Persona-pins-everything is a locked decision").
**Why it happens:** `EloSelector`/`PlayStyleControl` are visible, reusable components sitting right next to the chip components this phase DOES want to reuse (color/TC), making it easy to over-reuse.
**How to avoid:** The detail surface reuses ONLY the color-preference chips and TC-preset chip grid pattern from `SetupScreen.tsx` (D-05) — never `EloSelector` or `PlayStyleControl`. ELO label and style are DISPLAY-ONLY on the card/detail surface (D-03/D-04).
**Warning signs:** A detail-surface component importing `EloSelector` or `PlayStyleControl`.

### Pitfall 4: `styleNameFor`'s reverse-identity lookup is fragile if a persona registry accidentally clones a bundle
**What goes wrong:** `styleNameFor` (`useBotGame.ts`) resolves a `BotStyleParams` value back to its `Style` key via `===` reference-equality against the 4 singleton `BOT_STYLE_BUNDLES` objects. If the persona registry (or any test fixture) spreads/clones a bundle (`{ ...ATTACKER_STYLE }`) instead of referencing it directly, `styleNameFor` silently returns `undefined` for that persona's games, and the book-weighting seam silently falls back to the default `maiaPolicyWeighting` (a SAFE but SILENT degrade per the existing doc comment) — the bug manifests as "this persona's opening book personality doesn't show up," which is hard to notice without close observation.
**Why it happens:** Object-spread is an easy, common JS idiom for "give me a similar object" and nothing in the type system prevents it — `BotStyleParams` is a plain data interface.
**How to avoid:** The persona registry must reference `BOT_STYLE_BUNDLES[style]` directly at construction time in every code path that builds a `BotGameSettings.style` value — never spread/clone it, even to "add a small per-persona override" (there is no such use case in this phase's decisions; if one arises, that is new-style-lever engineering out of this phase's scope).
**Warning signs:** Any `{ ...BOT_STYLE_BUNDLES[x] }` or `Object.assign({}, ...)` pattern touching style data.

### Pitfall 5: Bumping `CURRENT_SNAPSHOT_VERSION` is unnecessary and would silently drop every in-progress bot game
**What goes wrong:** Adding `personaId?` to `BotGameSettings` might look like a "schema change" that should bump `botGameSnapshot.ts`'s `CURRENT_SNAPSHOT_VERSION` (which the module's own doc comment says is "a silent hard drop, never a migration"). Bumping it would silently discard every user's in-progress Custom-mode game on their next `/bots` visit after this phase deploys — a real regression with no warning.
**Why it happens:** The instinct to version-bump on any interface change to a persisted type is reasonable in general, but this specific field is OPTIONAL and the shape validators (`isValidSettingsShape`/`isValidSnapshotShape`) only assert presence of pre-existing required fields — they don't reject extra/missing optional ones.
**How to avoid:** Do NOT bump `CURRENT_SNAPSHOT_VERSION` for this phase. Verify (with a unit test) that a snapshot object lacking `personaId` still round-trips through `readSnapshot`/`isValidSnapshotShape` cleanly, resolving to `settings.personaId === undefined`.
**Warning signs:** A diff touching `CURRENT_SNAPSHOT_VERSION` for this phase should trigger a second look.

### Pitfall 6: `import.meta.glob`/Vite asset imports have zero precedent in this codebase — don't invent the pattern speculatively
**What goes wrong:** D-17 describes a future Vite-imported hashed-WebP pattern (`frontend/src/assets/personas/{persona-id}.webp`), but a repo-wide search finds **no existing precedent** for `import.meta.glob` or any `@/assets/*` image import anywhere in `frontend/src` — every existing app image (screenshots, logo, icons) is referenced as a plain `/public/...` string path, never Vite-bundled. Building this import machinery now, before any real `.webp` files exist (D-16 ships placeholders only), risks either (a) dead code that bit-rots before it's ever exercised, or (b) a half-built pattern that doesn't actually satisfy D-17's "build-time existence check" requirement when real art eventually lands.
**Why it happens:** D-17 reads as an implementation instruction, but its own text frames it forward-looking ("regeneration and the future >2000 extension are repeatable") and D-16 explicitly defers the real assets.
**How to avoid:** This phase should design the `Persona` registry's avatar field to be FORWARD-COMPATIBLE with a future Vite import (e.g. a nullable `avatarSrc?: string` field alongside the always-present `avatarEmoji` placeholder) but should NOT build working `.webp` import plumbing against files that don't exist yet — that work belongs to whichever future change actually adds the art. Confirm this scoping explicitly with the user/planner rather than silently either over- or under-building it.
**Warning signs:** A `vite.config.ts` diff, or a `frontend/src/assets/personas/` directory with committed placeholder `.webp` stubs, in a phase whose own CONTEXT.md says avatars ship as emoji+tint.

### Pitfall 7: `RESIGN_MIN_FULLMOVE`/`DRAW_ACCEPT_MIN_FULLMOVE`-style early-game gates must be respected by any new offer-trigger logic
**What goes wrong:** If Pitfall 1's new `wouldBotOfferDraw` predicate is built without an early-game floor (mirroring `RESIGN_MIN_FULLMOVE = 20`/`DRAW_ACCEPT_MIN_FULLMOVE = 40`), a persona could offer a draw in a still-developing opening position — which reads as broken/unnatural bot behavior and undermines the "authentic opponent" framing this whole milestone is chasing.
**Why it happens:** The near-equal score band a naive implementation would reach for (mirroring `DRAW_ACCEPT_SCORE_BAND`) is satisfiable very early in a symmetric opening, well before any human would consider offering a draw.
**How to avoid:** New offer-trigger logic needs its own fullmove floor constant (can reuse `DRAW_ACCEPT_MIN_FULLMOVE` or define a sibling), analogous to how `wouldBotResign` reuses the `RESIGN_MIN_FULLMOVE` pattern.
**Warning signs:** A draw-offer banner appearing before move ~15-20 in manual testing.

## Code Examples

### Rung → preset mapping (fixed by PERS-03, verified against `bot-strength-lookup.json`)
```typescript
// Source: reports/data/bot-strength-lookup.json derived.{human,light,deep}.range
// human.range = { floor: 900, ceiling: 1400 } — the 800 rung sits BELOW the
// measured floor by design (SEED-098: "let the bottom rung be ~900 in
// practice... honest labeling matters least at the bottom").
// light.range = { floor: 1500, ceiling: 1600 }
// deep.range  = { floor: 1600, ceiling: 1800 }
// -> 1600 is the ONLY rung inside BOTH light's ceiling and deep's floor,
//    which is exactly why PERS-03 calls it out as Light-OR-Deep discretion.

import { HUMAN_BLEND, LIGHT_BLEND, DEEP_BLEND } from '@/lib/playStyle';

const RUNG_BLEND: Record<Rung, number> = {
  800: HUMAN_BLEND,
  1000: HUMAN_BLEND,
  1200: HUMAN_BLEND,
  1400: HUMAN_BLEND,
  1600: LIGHT_BLEND, // or DEEP_BLEND per-persona, Claude's discretion (informed by measured ranges above)
  1800: DEEP_BLEND,
};
```

### Grid section iteration typed off the existing `Style` union (no new union to maintain)
```typescript
// Source: frontend/src/lib/engine/styleOpeningLines.ts already exports Style
import type { Style } from '@/lib/engine/styleOpeningLines';

const STYLE_SECTION_ORDER: readonly Style[] = ['Attacker', 'Trickster', 'Grinder', 'Wall']; // D-02
```

### `wouldBotResign`'s shape as the direct template for the missing `wouldBotOfferDraw` (Pitfall 1)
```typescript
// Source: frontend/src/lib/botDrawGate.ts (existing, verbatim) — study this
// shape before designing wouldBotOfferDraw; it is the closest existing
// precedent for "a styled bot's own pure, hysteresis-free-or-gated decision."
export function wouldBotResign(
  rootPracticalScore: number | null,
  resignThreshold: number,
  consecutiveLowTurns: number,
  hysteresisFloor: number,
  chess: Chess,
): boolean {
  if (rootPracticalScore === null) return false;
  return (
    rootPracticalScore <= resignThreshold &&
    consecutiveLowTurns >= hysteresisFloor &&
    chess.moveNumber() >= RESIGN_MIN_FULLMOVE
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Bots page = single `SetupScreen` (raw ELO + preset knobs) | Bots page = persona grid (default) + Custom escape hatch | This phase (183) | `SetupScreen.tsx` itself is untouched (PERS-04); `Bots.tsx`'s setup-phase branch gains a new default view |
| Style personality carried only by engine-level params (Phase 182, no UI) | Style personality surfaces as named, bio'd, avatar'd characters | This phase (183) | The 4 `BOT_STYLE_BUNDLES` become end-user-visible for the first time |

**Deprecated/outdated:** None — this phase is additive, no prior pattern is being replaced or removed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `botElo === rung` for all 24 personas (Human rungs use `HUMAN_BLEND`, so `botElo` seeds the raw Maia policy call directly at that rating) | Pitfall 2 / Code Examples | If the intended mapping is instead the INVERTED `bot-strength-lookup.json` value, every persona's actual play strength would differ substantially from what the label implies, and Phase 184's calibration baseline would be built on the wrong starting assumption. Low risk in practice — `botElo = rung` is the only interpretation consistent with the "provisional (raw preset) ELO labels" language in STATE.md's roadmap rationale, but flag explicitly at plan time. |
| A2 | 1600-rung personas split arbitrarily between Light and Deep is acceptable, with no requirement that the split be even (e.g. 2-Light/2-Deep, or all 4 one way) | Standard Stack / Discretion | Low — CONTEXT.md leaves this fully to Claude's discretion per-persona, informed by measured ranges; no functional risk either way |
| A3 | The persona registry belongs in a new `frontend/src/lib/personas/` directory rather than `frontend/src/lib/engine/` | Architecture Patterns / Recommended Project Structure | Low — purely organizational; CONTEXT.md explicitly leaves file placement to Claude's discretion ("suggest colocating near `botStyleBundles.ts` conventions" is a suggestion, not a mandate) |
| A4 | A new `wouldBotOfferDraw` predicate (Pitfall 1) needs its own `BotStyleParams` field(s) (offer threshold/cooldown) rather than reusing `contempt`/`threshold` as-is | Pitfall 1 | Medium — this is genuinely open design work Phase 182 left undone; the planner should treat the exact mechanism as a plan-time decision, not something this research can fully resolve without spec input |

**If this table is empty:** N/A — see above.

## Open Questions (RESOLVED)

All three questions were resolved during planning — see inline markers.

1. **What triggers the bot's outgoing draw-offer, precisely?**
   - **RESOLVED (Plan 183-02):** `wouldBotOfferDraw` is a pure predicate mirroring `wouldBotResign`'s shape, reusing the existing `contempt` knob plus three module constants (near-equal band, fullmove floor, cooldown); no new `BotStyleParams` field, so the four shipped Phase-182 bundles stay byte-unchanged. Wired into the existing single `pool.grade().then()` callback (Plan 183-03 Task 2).
   - What we know: D-07 (183-CONTEXT.md) specifies the UI shape (non-blocking inline banner, Accept/Decline, expires on cooldown or the user's next move) and that it "fires per the Phase 182 policy's cooldown rules" — but per Pitfall 1, no such policy trigger exists in code yet.
   - What's unclear: The exact score condition (near-equal band? style-specific threshold?), the fullmove floor, and the cooldown symmetry with `DRAW_OFFER_COOLDOWN_MOVES` (5 user moves).
   - Recommendation: Plan should design `wouldBotOfferDraw` explicitly as a Task, using `wouldBotResign`'s shape as the template (pure predicate, `null`-sentinel discipline, fullmove floor), gated per-style via a new or reused `BotStyleParams` field, wired into the same `pool.grade(...).then(...)` callback as the existing resign check.

2. **Does "Rematch [persona]" reuse `newGame()`'s reset-in-place semantics, or go through the full `handleStart`/remount path?**
   - What we know: `Bots.tsx`'s `handleNewGame` currently unmounts `BotsGame` and returns to setup (D-11 from Phase 171: "New game" never calls the hook's own `newGame()`). D-08 wants "Rematch [persona]" to restart with the SAME pinned config + same color/TC.
   - What's unclear: Whether Rematch should call `BotsPage.handleStart(sameSettings)` (a fresh `BotsGame` remount, consistent with the existing "no second start path" invariant) or the hook's dormant `newGame()` API (which already exists, is tested, but has "no production caller" per its own doc comment).
   - Recommendation: Prefer `handleStart(sameSettings)` — it is the existing, single, tested start path (mirrors 171 D-11's rationale exactly) and avoids resurrecting `newGame()`'s untested-in-production code path for a new caller.
   - **RESOLVED (Plan 183-05 Task 3):** Rematch goes through `BotsPage.handleStart(sameSettings)` (fresh remount, single start path); the dormant `newGame()` API is not resurrected.

3. **Where does the "New opponent" action from the result surfaces route to — the grid, or all the way to `/bots` fresh?**
   - What we know: D-08 says "back to the persona grid."
   - What's unclear: Whether this is functionally identical to the existing `onNewGame` (already routes to the setup-phase branch, which under D-01 now defaults to the grid) or needs distinct wiring.
   - Recommendation: Likely identical to today's `onNewGame` once the setup-phase branch's default view is the grid (D-01) — verify at plan time whether a SEPARATE "New opponent" button is even needed alongside "Rematch," or whether the existing "New game"-equivalent action already satisfies it under the new default view.
   - **RESOLVED (Plan 183-05 Task 3):** "New opponent" reuses the existing `onNewGame` path, which lands on the setup branch whose default view is now the persona grid (D-01) — no distinct wiring.

## Environment Availability

Skipped — this phase has no external tool/service/runtime dependencies beyond the existing frontend dev stack (Node/npm/Vite), all of which are already verified present and working by every prior Bots-page phase (169-171, 182).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (frontend), `@testing-library/react` |
| Config file | `frontend/vite.config.ts` (test block) / `frontend/package.json` scripts |
| Quick run command | `npm test -- --run <path-to-file>.test.ts(x)` (from `frontend/`) |
| Full suite command | `npm test -- --run` (from `frontend/`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERS-01 | Grid renders 24 personas in 4 style sections × 6 rungs, each showing name/avatar/bio/style/ELO label | unit (RTL render) | `npm test -- --run src/components/bots/__tests__/PersonaGrid.test.tsx` | ❌ Wave 0 |
| PERS-02 | Tapping Play constructs a full `BotGameSettings` (all pinned fields) with exactly one action, no intermediate strength step | unit | `npm test -- --run src/components/bots/__tests__/PersonaDetailSurface.test.tsx` | ❌ Wave 0 |
| PERS-03 | `PERSONA_REGISTRY` has exactly 24 entries, 6 per style, `blend`/`botElo` match the fixed rung table, `style` references (not copies) `BOT_STYLE_BUNDLES` | unit (data-shape assertions, mirrors `botStyleBundles.test.ts`'s cross-style ordering assertions) | `npm test -- --run src/lib/personas/__tests__/personaRegistry.test.ts` | ❌ Wave 0 |
| PERS-04 | `SetupScreen.tsx` and its existing tests are byte-unchanged; Custom mode's `BotGameSettings.style`/`personaId` are `undefined` | unit (existing `SetupScreen.test.tsx` must still pass unmodified; add an explicit assertion that Custom-built settings have no `personaId`) | `npm test -- --run src/components/bots/__tests__/SetupScreen.test.tsx` | ✅ (extend) |
| AVAT-01 | Placeholder (emoji+tint) renders for every persona; missing/pending real art does not crash | unit | covered by `PersonaCard.test.tsx` | ❌ Wave 0 |
| AVAT-02 | Every persona has a non-empty `name`/`bio` string, bio conveys per-tier story (manual UAT review per D-13, not automatable) | unit (non-empty/shape only) + manual UAT | `npm test -- --run src/lib/personas/__tests__/personaRegistry.test.ts` | ❌ Wave 0 (shape only) |
| D-06 (in-game presence) | Clock strip shows persona avatar+name for a persona game, "FlawChess Bot" for Custom | unit | `npm test -- --run src/components/bots/__tests__/ClockDisplay.test.tsx` | ❌ Wave 0 (new test cases) |
| D-07 (draw offer) | `wouldBotOfferDraw` unit-tested per Pitfall 1's design (null-sentinel, near-equal band, fullmove floor); banner Accept/Decline wiring tested | unit | `npm test -- --run src/lib/__tests__/botDrawGate.test.ts` and a new `BotDrawOfferBanner.test.tsx` | ❌ Wave 0 (both new) |
| D-08 (rematch/new opponent) | Rematch reconstructs identical `BotGameSettings`; New opponent routes to grid | unit | `npm test -- --run src/pages/__tests__/Bots.test.tsx` (extend) | ✅ (extend) |

### Sampling Rate
- **Per task commit:** targeted `npm test -- --run <changed-file>.test.ts(x)`
- **Per wave merge:** `npm test -- --run` (full frontend suite) + `npm run lint` + `npx tsc -b` (per CLAUDE.md's "run tsc -b before integrating frontend" rule — this phase touches shared types on `BotGameSettings`)
- **Phase gate:** Full suite green + `npm run knip` (registry/component exports must all be genuinely consumed) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/lib/personas/__tests__/personaRegistry.test.ts` — 24-entry shape, rung→blend table, style-reference-not-copy assertions
- [ ] `src/components/bots/__tests__/PersonaGrid.test.tsx` — new
- [ ] `src/components/bots/__tests__/PersonaCard.test.tsx` — new
- [ ] `src/components/bots/__tests__/PersonaDetailSurface.test.tsx` — new
- [ ] `src/components/bots/__tests__/BotDrawOfferBanner.test.tsx` — new
- [ ] `wouldBotOfferDraw` test cases in `src/lib/__tests__/botDrawGate.test.ts` — new (Pitfall 1)
- [ ] `ClockDisplay.test.tsx` — does not exist yet; new persona-avatar test cases need a new file or extension of an existing render-based test elsewhere
- [ ] Framework install: none — Vitest/RTL already fully configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth surface — persona play uses the exact same guest/owner-scoped flow as today's Bots page |
| V3 Session Management | no | No change |
| V4 Access Control | no | No new authorization boundary — personas are public, client-side-only data |
| V5 Input Validation | yes | The new `personaId` field flowing through `localStorage` (snapshot + last-used settings) must be validated the same way every existing persisted field is: `readSnapshot`/`readSetupSettings`'s existing shape-validator pattern extended defensively — an unrecognized/tampered `personaId` string must resolve to "no persona found, fall back to unstyled display," never throw |
| V6 Cryptography | no | No new secrets, tokens, or crypto surface |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Corrupted/tampered `personaId` in localStorage (a user or extension editing `flawchess_bot_game:*`/`flawchess_bot_setup_settings:*` directly) | Tampering | Registry lookup by key returns `undefined` for any unrecognized id (plain object index, no `eval`/dynamic require); every consumer must null-coalesce to the existing unstyled fallback — no new attack surface beyond what `botGameSnapshot.ts`'s existing corruption-recovery path already handles for `style`/`botElo`/etc. |
| XSS via persona bio/name strings | Tampering/Info Disclosure | Bios/names are AUTHORED CONTENT (Claude-drafted at execute time, D-13), never user input — rendered via normal JSX text interpolation (React auto-escapes), never `dangerouslySetInnerHTML`. No new risk. |

## Sources

### Primary (HIGH confidence — verified directly against the repository)
- `frontend/src/lib/engine/botStyleBundles.ts` — the 4 style bundles, D-12 provenance comments, `BOT_STYLE_BUNDLES` shape
- `frontend/src/lib/engine/botStyle.ts` — `BotStyleParams`, `styleBookWeighting`, prior-reweighting/score-shaping transforms
- `frontend/src/lib/engine/styleOpeningLines.ts` — `Style` union, `styleLinesFor`
- `frontend/src/lib/botDrawGate.ts` — `canOfferDraw`, `wouldBotAcceptDraw`, `wouldBotResign` (confirmed: no offer-trigger function exists)
- `frontend/src/lib/__tests__/botDrawGate.test.ts` — confirms the exact 3 exported/tested functions (grep-verified, no fourth)
- `frontend/src/hooks/useBotGame.ts` — full 1446-line read; `BotGameSettings`, snapshot/persistence call sites, `runBotTurn`, `styleNameFor`
- `frontend/src/lib/botGameSnapshot.ts` — snapshot shape validators, `CURRENT_SNAPSHOT_VERSION` semantics
- `frontend/src/lib/botSetupSettings.ts` — the last-used-settings persistence pattern to mirror
- `frontend/src/lib/playStyle.ts` — `HUMAN_BLEND`/`LIGHT_BLEND`/`DEEP_BLEND`
- `frontend/src/pages/Bots.tsx` — `BotsPage`/`BotsGame` structure, setup/game/resume phase switch
- `frontend/src/components/bots/SetupScreen.tsx`, `chipStyles.ts`, `PlayStyleControl.tsx`, `GameControls.tsx` — reusable chip/dialog patterns
- `frontend/src/components/bots/ClockDisplay.tsx`, `GameResultDialog.tsx`, `GameResultStrip.tsx` — extension points for D-06/D-08
- `reports/data/bot-strength-lookup.json` — measured Human/Light/Deep floor/ceiling ranges (`derived.*.range`)
- `frontend/src/lib/maiaEncoding.ts` — `MAIA_ELO_LADDER` (600–2600, step 100)
- `frontend/vite.config.ts`, repo-wide grep for `import.meta.glob`/`@/assets` — confirmed no existing Vite-image-import precedent
- `frontend/src/lib/theme.ts` — existing color-constant conventions for per-style accent colors
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md`, `.planning/phases/182-style-levers/182-CONTEXT.md`, `.planning/REQUIREMENTS.md` — locked decisions and requirement text

### Secondary (MEDIUM confidence)
- None — no external documentation lookups were needed; this is a pure internal-codebase composition phase.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, everything verified against `package.json` and existing imports
- Architecture: HIGH — every pattern cited traces to a specific, read file in this session
- Pitfalls: HIGH for Pitfalls 2-7 (verified via direct code/data inspection); HIGH for Pitfall 1 specifically because it was verified by exhaustive grep across the exact files CONTEXT.md cites as already containing the policy, which do not

**Research date:** 2026-07-22
**Valid until:** 30 days (stable internal codebase, no external API/library drift risk) — but re-verify Pitfall 1's finding against the actual Phase 182 code at plan time in case a last-minute addendum landed after this research session
