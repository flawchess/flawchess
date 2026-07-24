# Phase 183: Persona Registry & Bots Page - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

24 named bot personas (4 styles × 6 rungs, 800–1800) in one typed registry, browsable as a grid on the Bots page with avatar/name/bio/style/provisional-ELO, one-action start with the persona's full pinned config, and the persona's presence carried through the game view and result surfaces. Includes the bot outgoing draw-offer UI explicitly deferred here from Phase 182 (the offer policy already fires in `useBotGame`; only the banner/buttons are missing). Custom mode (existing SetupScreen with raw ELO/preset knobs) stays fully intact per PERS-04. Covers PERS-01..04, AVAT-01 (partially — see D-16), AVAT-02. Calibrated ELO labels are Phase 184.

</domain>

<decisions>
## Implementation Decisions

### Bots page structure
- **D-01: Grid-first, Custom as escape hatch.** The persona grid becomes the default `/bots` view. Custom mode is one clearly-visible entry (e.g. a distinct "Custom" card or button) that opens the existing SetupScreen unchanged. Snapshot-resume precedence (Phase 170/171: `BotsGame` + `ResumeGate` when a snapshot exists) is unaffected.
- **D-02: Grid organized by style — 4 sections × 6 rungs.** Four style sections (Attacker, Trickster, Grinder, Wall), each showing its 6 characters ascending 800→1800. Tells each style's identity story and matches the bios' per-tier arc.
- **D-03: Compact cards + detail on tap.** Card shows avatar, name, ELO label (optionally a one-line tagline). Tapping opens a detail surface (dialog/panel) with the full bio, color/TC controls (D-05), and the Play button.
- **D-04: Provisional ELO labels use tilde format (`~1200`).** Signals approximate honestly; Phase 184 keeps the format and only swaps the number for the calibrated value.

### Persona start & in-game presence
- **D-05: Color and time control are chosen in the detail surface.** The persona pins preset/ELO/style/book/policy (PERS-02), but color + TC are session choices: compact chips in the detail dialog, defaulting to last-used (persisted like `botSetupSettings`). One surface, no separate strength step.
- **D-06: Full in-game persona presence.** Persona avatar + name render in the bot's clock strip (desktop AND mobile), and the result dialog/strip names the persona (e.g. "Riko the Raccoon wins on time").
- **D-07: Bot draw offer = non-blocking inline banner** near the board/clock area ("[Persona] offers a draw") with Accept and Decline buttons; expires per the Phase 182 policy's cooldown rules or on the user's next move. Play continues while it's up (lichess convention).
- **D-08: Post-game result surfaces offer "Rematch [persona]"** (same pinned config + same color/TC) alongside the existing analysis actions, plus a "New opponent" path back to the persona grid.

### Names, bios & tone
- **D-09: Animal-themed roster matching the FlawChess horse logo.** Small-to-medium animals for the current beginner-to-intermediate 800–1800 range; large animals are reserved for future >2000-ELO bots (SEED-114). Avatar look is influenced by playstyle (e.g. Trickster looks a bit crazy); animals may wear items (glasses, hats, ties, necklaces).
- **D-10: 24 distinct species, body size loosely increasing with rung** within each style; species picked to fit the style's vibe (e.g. Trickster: magpie/raccoon/fox; Wall: turtle/badger/beaver).
- **D-11: Naming = "Name the Species"** (e.g. "Riko the Raccoon", "Bruno the Badger"). Species doubles as the size/strength cue and reads naturally in text surfaces (result dialog, draw banner, rematch button).
- **D-12: Bios are playful third-person, 2–3 sentences:** who this animal is, how it plays, and what to watch out for at this tier — carrying the AVAT-02 per-tier story (e.g. Trickster: trap lines at 800–1200, swindle mode at 1600+).
- **D-13: Claude drafts all species/names/bios at execute time** following the conventions above; user reviews the full roster in UAT and requests swaps (same process as 182's curated opening lines).
- **D-14: Style display name is "Wall"** (not "Solid Wall" / "Great Wall" from earlier docs). Engine key `wall` already matches; UI copy and registry display names use simply "the Wall".

### Avatar pipeline
- **D-15: Claude writes prompts, user generates.** A master style prompt (matching the cel-shaded cartoon horse-logo look: friendly, outlined, cartoon) + 24 per-character prompt descriptors are committed in-repo alongside the registry. User runs them through their image tool of choice, curates, and drops the files in. Prompts stay in-repo so regeneration and the future >2000 extension are repeatable.
- **D-16: Phase ships with placeholders; real art lands later.** The phase merges with placeholder avatars; curated portraits arrive whenever (possibly after 183 ships). Consequence: AVAT-01 stays open/partial at phase close — track it rather than blocking the merge.
- **D-17: Portrait format — square face-and-shoulders, ~256×256 WebP.** Imported via Vite from `frontend/src/assets/personas/{persona-id}.webp` (hashed URLs, build-time existence check). Generate at high res, downscale before commit.
- **D-18: Placeholder look — species emoji on a per-style background tint.** Zero art dependency, instantly conveys species + style, intentional enough to ship publicly until portraits arrive.

### Claude's Discretion
- 1600-rung preset choice per persona (Light vs Deep, informed by `reports/data/bot-strength-lookup.json` measured ranges); 800–1400 Human and 1800 Deep are fixed by the requirements.
- Registry file shape and location (typed const registry; suggest colocating near `botStyleBundles.ts` conventions).
- Per-style accent colors for sections/placeholder tints (define in `theme.ts` per frontend rules).
- Snapshot/resume plumbing: persisting persona id in the game snapshot so a resumed game restores full persona identity (avatar, name, policy) and result surfaces.
- Exact detail-surface component (dialog vs drawer) and mobile grid column count.
- Exact species/name/bio roster content (D-13 — user reviews in UAT).
- Prompt file format/location for the avatar prompts.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` — locked explore decisions: persona-pins-everything, 24-slot grid, rung→preset table, honesty constraints, prior art (chess.com persona bots)
- `.planning/REQUIREMENTS.md` — PERS-01..04, AVAT-01/02 definitions + out-of-scope table (no persona × strength picker, no adaptive style)
- `.planning/phases/182-style-levers/182-CONTEXT.md` — Phase 182 decisions this phase builds on (D-02 style bundles, D-03 absent-style invariant, D-07 draw-offer UI deferral to this phase)

### Style layer (Phase 182 output this phase consumes)
- `frontend/src/lib/engine/botStyleBundles.ts` — the 4 named `BotStyleParams` bundles (`ATTACKER_STYLE`, `TRICKSTER_STYLE`, `GRINDER_STYLE`, `WALL_STYLE`, `BOT_STYLE_BUNDLES`) the registry references per persona
- `frontend/src/lib/engine/botStyle.ts` — `BotStyleParams` type and style semantics
- `frontend/src/lib/engine/styleOpeningLines.ts` — per-style curated opening books (already wired via `BookWeightingFn`)
- `frontend/src/lib/botDrawGate.ts` — draw accept/offer/resign policy the persona pins
- `frontend/src/lib/playStyle.ts` — Human/Light/Deep preset blends (`HUMAN_BLEND`/`LIGHT_BLEND`/`DEEP_BLEND`) the rung→preset mapping uses

### Bots page & game flow (the UI this phase extends)
- `frontend/src/pages/Bots.tsx` — outer `BotsPage` (setup/game phase switch, snapshot precedence, pending-store drain) + inner `BotsGame`; the persona grid slots in ahead of `SetupScreen`
- `frontend/src/components/bots/SetupScreen.tsx` — the Custom-mode form that must stay unchanged (PERS-04); its color/TC chip patterns are reusable in the persona detail surface
- `frontend/src/hooks/useBotGame.ts` — `BotGameSettings` (gains persona identity or is wrapped by it); draw-offer policy hook point for the D-07 banner
- `frontend/src/lib/botSetupSettings.ts` — persisted last-used settings pattern to mirror for persona color/TC defaults
- `frontend/src/lib/botGameSnapshot.ts` — snapshot schema that needs the persona id for resume
- `frontend/src/components/bots/ClockDisplay.tsx` — bot clock strip gaining avatar + name (D-06)
- `frontend/src/components/bots/GameResultDialog.tsx` / `GameResultStrip.tsx` — result surfaces gaining persona name + Rematch (D-08)

### Calibration inputs (label provenance)
- `reports/data/bot-strength-lookup.json` — measured Human/Light/Deep ranges dictating the rung→preset mapping and the provisional labels

### Brand reference
- `frontend/public/icons/logo-256.png` — the cel-shaded cartoon detective-horse logo the avatar style prompt must match

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SetupScreen.tsx` chip components (`chipStyles.ts` CHIP_* classes, TC preset grid, color chips): reuse directly in the persona detail surface for color/TC selection.
- `botSetupSettings.ts` owner-scoped localStorage pattern (`readSetupSettings`/`writeSetupSettings`): mirror for persona last-used color/TC (and possibly last-played persona).
- `BOT_STYLE_BUNDLES: Record<Style, BotStyleParams>`: the registry maps each persona slot to one of these + a rung ELO + a preset blend — no new engine params needed.
- `BotGameSettings.style?: BotStyleParams` (Phase 182 Plan 06): starting a persona game is just building a `BotGameSettings` with the pinned values; `undefined` style = Custom mode untouched by construction.
- `GameResultDialog`/`GameResultStrip` "New game" fallthrough (Phase 171 D-11/D-13): extend with Rematch rather than replacing the flow.

### Established Patterns
- Single entry point via `BotsPage` phase switch (setup vs game vs resume): the persona grid becomes part of the "setup" phase branch; do not add a second start path (Phase 171 invariant).
- Typed const registries with docstring-per-entry (`botStyleBundles.ts` style): the persona registry should follow this shape — one file, exhaustive `Record` or array typed against a `PersonaId` union.
- Theme colors in `theme.ts`, `data-testid` on every interactive element (`bots-persona-card-{id}`, `btn-persona-play`, etc.), `text-sm` floor, mobile-first: all frontend rules apply to the grid, detail surface, and banner.
- Vite asset imports with build-time existence checks (D-17) rather than `public/` path conventions.

### Integration Points
- `BotsPage` setup branch: renders persona grid (default) with Custom entry → existing `SetupScreen`.
- Persona detail Play → constructs `BotGameSettings` (botElo, blend from rung preset, style bundle, color, TC) → existing `onStart` path.
- `useBotGame` draw-offer state → new inline banner component near board/clocks (D-07); Accept wires to the existing draw-end path, Decline dismisses per policy cooldown.
- `botGameSnapshot` + `GameResultDialog`/`Strip`: carry persona id through snapshot/resume and post-game surfaces (registry lookup by id — never serialize the whole persona).
- Stored-game records (`useStoreBotGame`): bot name surfaces may want the persona name via `resolvePlayerName`-adjacent plumbing — keep minimal, registry-lookup-by-id.

</code_context>

<specifics>
## Specific Ideas

- Roster identity: animal characters in the horse-logo's cel-shaded cartoon style; playstyle shows in the animal's demeanor (crazy-eyed Trickster, sturdy Wall) and accessories (glasses, hats, ties, necklaces).
- Size ladder: small animals at 800 growing to medium at 1800 within each style; large animals (bear, moose, elephant…) explicitly saved for the >2000 extension.
- Portraits: square, face and shoulders only.
- Example name reads: "Riko the Raccoon offers a draw", "Bruno the Badger wins on time".
- Per-tier bio stories from SEED-098: Trickster = cheap trap lines at 800–1200, swindle mode + high variance at 1600+; Grinder's training value = drags games into endgames, exactly what FlawChess measures.

</specifics>

<deferred>
## Deferred Ideas

- Large-animal personas above 2000 ELO — gated on SEED-114 (ladder extension above ~1900 internal); the species-size convention (D-10) deliberately leaves room.
- Calibrated ELO labels + floor/ceiling honesty constraints — Phase 184 (CAL-04/05).
- "Suggest next rung up" nudge after a win — nice ladder feel, out of scope for the result surfaces this phase.
- Final curated avatar art — arrives asynchronously after merge (D-16); AVAT-01 completion tracked past phase close.

### Reviewed Todos (not folded)
- `172-deferred-review-findings` — analysis-page gem-sweep review findings; unrelated (keyword-noise match, same verdict as Phase 182).
- `2026-03-11-bitboard-storage-for-partial-position-queries` — DB storage idea; unrelated.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label` — chart label bug; unrelated to the Bots page.

</deferred>

---

*Phase: 183-Persona Registry & Bots Page*
*Context gathered: 2026-07-22*
