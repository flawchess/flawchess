# Phase 183: Persona Registry & Bots Page - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 13 (7 new, 6 modified)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/personas/personaRegistry.ts` | config (typed data registry) | CRUD (static lookup) | `frontend/src/lib/engine/botStyleBundles.ts` | exact |
| `frontend/src/lib/personas/personaAvatars.ts` | config (placeholder data) | CRUD (static lookup) | `frontend/src/lib/engine/botStyleBundles.ts` | role-match |
| `frontend/src/lib/personas/botPersonaSetupSettings.ts` | utility (localStorage persistence) | CRUD (read/write) | `frontend/src/lib/botSetupSettings.ts` | exact |
| `frontend/src/lib/botDrawGate.ts` (extend: `wouldBotOfferDraw`) | utility (pure predicate) | transform | `wouldBotResign` in same file | exact |
| `frontend/src/hooks/useBotGame.ts` (extend: `personaId`, offer-state) | hook (state machine) | event-driven | existing `wouldBotResign` wiring block (same file, lines ~1344-1371) | exact |
| `frontend/src/components/bots/PersonaGrid.tsx` | component | request-response (render) | `frontend/src/components/bots/SetupScreen.tsx` (screen-level composition) | role-match |
| `frontend/src/components/bots/PersonaCard.tsx` | component | request-response (render) | `frontend/src/components/bots/SetupScreen.tsx`'s `TcBucketGroup`/chip button pattern | role-match |
| `frontend/src/components/bots/PersonaDetailSurface.tsx` | component (dialog) | request-response (render + form submit) | `frontend/src/components/bots/SetupScreen.tsx` + `GameResultDialog.tsx` (Dialog shell) | exact (composite) |
| `frontend/src/components/bots/BotDrawOfferBanner.tsx` | component | event-driven (accept/decline) | `frontend/src/components/bots/ClockDisplay.tsx` (bot-side status UI near clock) | role-match |
| `frontend/src/components/bots/ClockDisplay.tsx` (extend: avatar+name) | component | request-response (render) | itself (extend in place) | exact |
| `frontend/src/components/bots/GameResultDialog.tsx` (extend: persona name + Rematch) | component | request-response (render + actions) | itself (extend in place) | exact |
| `frontend/src/components/bots/GameResultStrip.tsx` (extend: mirrors dialog) | component | request-response (render + actions) | `GameResultDialog.tsx` (must mirror) | exact |
| `frontend/src/pages/Bots.tsx` (extend: setup branch renders `PersonaGrid` by default) | controller (page/phase switch) | request-response | itself (extend `startedSettings === null` branch, lines 571-579) | exact |
| `frontend/src/lib/botGameSnapshot.ts` (no code change expected; verify pass-through) | model (snapshot shape validator) | CRUD (persist/restore) | itself | exact (verify-only) |

## Pattern Assignments

### `frontend/src/lib/personas/personaRegistry.ts` (config, CRUD/static lookup)

**Analog:** `frontend/src/lib/engine/botStyleBundles.ts` (full file read, 201 lines)

**Header/provenance-comment pattern** (lines 1-45): every registry file in this codebase opens with a doc comment explaining (a) what composes what by REFERENCE not copy, (b) what downstream consumer wires it in, (c) provenance/tuning notes per field. Mirror this exactly — cite Phase 182's `BOT_STYLE_BUNDLES`/`styleLinesFor` as the composed-by-reference dependencies, and cite Pitfall 2's `botElo === rung` decision explicitly in the header so Phase 184 has an auditable starting point.

**Core pattern — typed const collection keyed by an exhaustive union** (lines 195-200):
```typescript
export const BOT_STYLE_BUNDLES: Record<Style, BotStyleParams> = {
  Attacker: ATTACKER_STYLE,
  Trickster: TRICKSTER_STYLE,
  Grinder: GRINDER_STYLE,
  Wall: WALL_STYLE,
};
```
Apply the identical shape for `PERSONA_REGISTRY: Record<PersonaId, Persona>` — a `Record` over a literal-template `PersonaId` union (` `${Lowercase<Style>}-${Rung}` `) gives free TS exhaustiveness (missing a persona is a compile error), exactly like the 4-style record does today.

**Reference-not-copy discipline** (lines 39-44, 195-200 combined): each `Persona.style: Style` field must be a plain key, resolved via `BOT_STYLE_BUNDLES[persona.style]` at construction time — never `{ ...BOT_STYLE_BUNDLES[x] }`. This is Pitfall 4 in RESEARCH.md; the botStyleBundles.ts doc comment on line 39-44 is the canonical statement of the "reference by key membership, not by embedding" convention this registry must also follow for its own `style` field and (per Pattern 2/3 in RESEARCH.md) for `personaId` on `BotGameSettings`.

---

### `frontend/src/lib/personas/botPersonaSetupSettings.ts` (utility, CRUD read/write)

**Analog:** `frontend/src/lib/botSetupSettings.ts` (full file read, 203 lines) — mirror **verbatim**, per RESEARCH.md's "Don't Hand-Roll" table and CONTEXT.md D-05.

**Imports pattern** (lines 19-22):
```typescript
import * as Sentry from '@sentry/react';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';
import { HUMAN_BLEND, BLEND_MAX, PLAY_STYLE_DEFAULT_BLEND } from '@/lib/playStyle';
import { DEFAULT_TC_PRESET_LABEL, findPresetByLabel } from '@/lib/botTimeControlPresets';
```
(swap the ELO/blend imports for whatever the persona-settings shape needs — likely just color preference + TC, since ELO/blend/style are pinned by the persona itself, not persisted here).

**Key-prefix + owner-scoping pattern** (lines 24, 37-39):
```typescript
export const BOT_SETUP_SETTINGS_KEY_PREFIX = 'flawchess_bot_setup_settings:';
function setupSettingsKey(ownerKey: string | null | undefined): string {
  return `${BOT_SETUP_SETTINGS_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}
```
Use a NEW, distinct key prefix (e.g. `flawchess_bot_persona_settings:`) — never reuse `botSetupSettings.ts`'s key (its own header comment at lines 1-17 explicitly forbids cross-key reuse: "a settings-shaped object written under that key would fail its validator").

**Shape-validator + range-check pattern** (lines 56-87): `isNumberInRange` + a shape-predicate function returning a type guard (`value is BotSetupSettings`) that range-checks every numeric field and enum-checks every string field. Out-of-range values must be treated as corruption (WR-01 bug fix documented at lines 63-76 — do not repeat the "type-check but not range-check" mistake).

**Read/write/corruption-recovery pattern** (lines 89-150): SSR-guard → try/catch → JSON.parse → shape-validator → Sentry-once-on-corruption (`clearCorruptSetupSettings`) → silent-no-op write. Copy this control flow exactly; this is the project's hardened, load-bearing localStorage pattern (per MEMORY `project_frontend_no_prettier`-adjacent conventions and CLAUDE.md's Sentry rules — every corruption path calls `Sentry.captureException` with a `source` tag, e.g. `'bot-persona-setup-settings'`).

---

### `frontend/src/lib/botDrawGate.ts` — extend with `wouldBotOfferDraw` (utility, pure predicate)

**Analog:** `wouldBotResign` in the same file (lines 165-180, already fully read above).

**Core pattern — pure predicate, sentinel discipline, fullmove floor**:
```typescript
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
`wouldBotOfferDraw` must follow this EXACT shape (per RESEARCH.md Pitfall 1 + Code Examples section, which flags this as the direct template): a pure function, `null`-sentinel refused FIRST and unconditionally (mirrors line 172-173), a near-equal-band check (mirroring `wouldBotAcceptDraw`'s `DRAW_ACCEPT_SCORE_BAND`/`drawValue = 0.5 + contempt` pattern at lines 112-133 of the same file), and its OWN fullmove floor constant analogous to `RESIGN_MIN_FULLMOVE`/`DRAW_ACCEPT_MIN_FULLMOVE` (RESEARCH.md Pitfall 7 — do not reuse `RESIGN_MIN_FULLMOVE` blindly without confirming the intended offer-vs-resign timing separately). No hysteresis-state is owned by this module — the caller (`useBotGame.ts`) owns any counter ref, exactly as `consecutiveLowScoreTurnsRef` is owned there for resignation (see next section).

**Constant-declaration pattern** (lines 26-58): every tunable constant gets an exported `const` with a doc comment citing its decision ID (D-01/D-04/D-08) and an `[ASSUMED]`/hand-tuned disclosure where applicable. A new `wouldBotOfferDraw`-specific constant (offer score band, offer fullmove floor, offer cooldown-in-own-moves) should follow this exact documentation convention.

---

### `frontend/src/hooks/useBotGame.ts` — extend `BotGameSettings.personaId?` + wire offer-trigger (hook, event-driven)

**Analog:** the existing `wouldBotResign` wiring block, same file, lines 1344-1371 (already fully read above).

**Field-addition pattern on `BotGameSettings`** (lines 162-193, esp. 180-192 for the precedent optional-field doc comment style):
```typescript
export interface BotGameSettings {
  botElo: number;
  blend: number;
  baseSeconds: number;
  incrementSeconds: number;
  userColor: MoverColor;
  style?: BotStyleParams;
  // NEW: personaId?: PersonaId; — mirror the `style?` doc-comment convention:
  // explain what `undefined` means (Custom mode, PERS-04, by construction),
  // and that nothing here re-serializes the whole Persona object.
}
```

**Post-move grade callback wiring pattern** (lines 1324-1376, esp. 1344-1371):
```typescript
pool
  .grade(fen, [uci])
  .then((gradeMap) => {
    if (controller.signal.aborted) return;
    const grade = gradeMap.get(uci);
    if (grade) {
      const score = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
      lastRootPracticalScoreRef.current = score;
      if (settings.style) {
        // existing resign-hysteresis counter + wouldBotResign check
        if (resigns) {
          finalizeGame({ reason: 'resignation', winner: settings.userColor });
        }
      }
      // NEW: a sibling `if (settings.style)` block here computes
      // wouldBotOfferDraw the SAME way (fresh score this callback just
      // computed, its own counter ref reset only in newGame(), mirrors the
      // ref-latch pattern documented at lines 1348-1351) and sets new
      // outgoing-offer state for BotDrawOfferBanner to render, instead of
      // calling finalizeGame.
    }
  })
  .catch(() => { /* best-effort only */ });
```
Reuse the SAME callback, the SAME staleness guard (`controller.signal.aborted`), and the SAME `settings.style` gate — do not add a second `pool.grade()` call site (CR-02 fix at lines 1327-1337 explains exactly why a second/parallel grade call is dangerous: it can resolve after `newGame()`/`resign()` and corrupt state).

**`styleNameFor` reverse-lookup caution** (lines 299-320, fully read above): `personaId` must be threaded as an INDEPENDENT field, never derived from `styleNameFor(settings.style)` — 6 personas share one style bundle, so the existing reverse-lookup cannot disambiguate rung. This is RESEARCH.md Pattern 2, directly grounded in this exact function.

---

### `frontend/src/components/bots/PersonaDetailSurface.tsx` (component, composite)

**Analog A (chip reuse):** `frontend/src/components/bots/SetupScreen.tsx`, `TcBucketGroup` + color-chip block (lines 153-205, 258-277, fully read above).

**TC chip grid pattern** (lines 159-205):
```tsx
<div className="grid flex-1 gap-1" style={{ gridTemplateColumns: `repeat(${presets.length}, minmax(0, 1fr))` }}>
  {presets.map((preset) => {
    const isActive = activeLabel === preset.label;
    return (
      <button
        key={preset.label}
        type="button"
        data-testid={tcPresetTestId(bucket, preset.label)}
        aria-pressed={isActive}
        onClick={() => onSelect(preset.label)}
        className={cn(CHIP_BASE_CLASS, isActive ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS)}
      >
        {preset.label}
      </button>
    );
  })}
</div>
```

**Color chip pattern** (lines 258-277) — identical shape with `COLOR_OPTIONS`. Copy both blocks into the detail surface unchanged (import `CHIP_BASE_CLASS`/`CHIP_ACTIVE_CLASS`/`CHIP_INACTIVE_CLASS` from `chipStyles.ts`, and reuse `TIME_CONTROL_PRESETS`/`TC_BUCKET_ORDER`/`TC_BUCKET_LABELS` from `botTimeControlPresets.ts` + `SetupScreen.tsx`'s own local constants where not already exported).

**Explicit exclusion (Pitfall 3):** do NOT import `EloSelector` or `PlayStyleControl` (`SetupScreen.tsx` lines 19, 21) — ELO/style are DISPLAY-ONLY on the persona surface, never editable controls.

**Analog B (dialog shell):** `frontend/src/components/bots/GameResultDialog.tsx` (full file read, 135 lines) — `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogFooter` composition (lines 4-10, 76-134) is the established shadcn Dialog usage pattern for this page; mirror its `open`/`onOpenChange` controlled-dialog contract (lines 77-82) and its mobile-anchor override (`top-[30%] sm:top-1/2`, line 86) for a comfortable-thumb-reach position on mobile.

---

### `frontend/src/components/bots/ClockDisplay.tsx` (extend: avatar+name, D-06)

**Analog:** itself — extend in place (full file read, 70 lines).

**Current props/render shape** (lines 6-18, 39-69): `sideLabel: string` already exists as the label slot. Add an optional `avatarEmoji?: string` (or richer avatar prop) rendered alongside `sideLabel` inside the existing `<span className="flex items-center gap-2 text-sm font-medium">` (line 48) — same slot the "thinking" pulse dot already occupies (lines 50-60), so the avatar+name+thinking-dot three-way layout composes naturally without restructuring the card.

**Caller-side lookup pattern to build:** per RESEARCH.md Pattern 3, `personaFor(settings)` degrades gracefully:
```typescript
function personaFor(settings: BotGameSettings): Persona | undefined {
  return settings.personaId ? PERSONA_REGISTRY[settings.personaId] : undefined;
}
const persona = personaFor(settings);
<ClockDisplay sideLabel={persona?.name ?? 'FlawChess Bot'} avatarEmoji={persona?.avatarEmoji} ... />
```
This lookup helper belongs in `personaRegistry.ts` (or a small `personaLookup.ts` sibling) — every consumer (clock strip, draw banner, result dialog/strip) calls the SAME helper, never re-implements the `settings.personaId ? PERSONA_REGISTRY[...] : undefined` ternary inline (avoids drift across 4+ call sites).

---

### `frontend/src/components/bots/GameResultDialog.tsx` / `GameResultStrip.tsx` (extend: persona name + Rematch, D-08)

**Analog:** `GameResultDialog.tsx` itself (full file read) is also the analog `GameResultStrip.tsx` must mirror (its own header comment, lines 16-19, already states this contract: "`GameResultStrip` renders the EXACT same strings rather than re-typing them").

**Existing action-button pattern** (lines 111-131):
```tsx
<DialogFooter>
  <Button variant="brand-outline" onClick={onAnalyze} disabled={analyzeBusy} data-testid="btn-analyze-game">
    {analyzeBusy && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
    Analyze this game
  </Button>
  <Button variant="default" onClick={onNewGame} data-testid="btn-new-game">
    New game
  </Button>
</DialogFooter>
```
Add a `Rematch [persona]` button here using `variant="brand-outline"` (secondary — per CLAUDE.md's Primary vs secondary rule, "New game"/"New opponent" stays `variant="default"` as the primary CTA since it's the more common path back to browsing) or vice versa per UAT — either way, never hand-roll button colors (`className`/`bg-*`), only use the two sanctioned variants. Route "New opponent" through the SAME `onNewGame` callback Bots.tsx already wires (RESEARCH.md Open Question 3 — likely identical to today's `onNewGame` once D-01 makes the grid the default setup view).

**Title-copy pattern** (lines 46-51, 73-74): `resultCopy(outcome, userColor)` is the single source of the result string; extend `resultCopy`'s call site (or a persona-aware wrapper) so "Bruno the Badger wins on time" substitutes for the generic copy — do not fork a second copy-generation path.

---

### `frontend/src/pages/Bots.tsx` (extend: setup branch renders `PersonaGrid` by default, D-01)

**Analog:** itself — extend in place at the existing setup-phase branch.

**Current phase-switch pattern** (lines 546-592, esp. 571-579):
```tsx
if (startedSettings === null) {
  return (
    <SetupScreen
      ownerKey={ownerKey}
      normalizedRating={profile?.lichess_blitz_equivalent_rating ?? null}
      onStart={handleStart}
    />
  );
}
```
Replace this branch's default render with `PersonaGrid` (passing the same `ownerKey`/`onStart` plumbing plus a "Custom" escape-hatch callback that renders `SetupScreen` unchanged) — do NOT add a second `if` branch/second start path; `handleStart` (lines 513-516) is the SINGLE existing entry point both the persona detail surface's Play button and `SetupScreen`'s Start button must call, per the Phase 171 "no second start path" invariant (RESEARCH.md Anti-Pattern, System Architecture Diagram).

**`handleNewGame`/`handleStart` reuse for Rematch** (lines 510-524): `handleStart(sameSettings)` is RESEARCH.md's recommended mechanism for "Rematch [persona]" (Open Question 2) — remounts a fresh `BotsGame` via the existing tested path, rather than resurrecting the hook's dormant `newGame()` API.

---

### `frontend/src/lib/botGameSnapshot.ts` (verify-only, no code change expected)

**Analog:** itself. RESEARCH.md Pitfall 5/Pattern 3 (already verified during research): `BotGameSnapshot.settings: BotGameSettings` flows `personaId?` through `writeSnapshot`/`readSnapshot` automatically once added to `BotGameSettings` — `isValidSnapshotShape`/`isValidSettingsShape` only assert PRE-EXISTING required fields and do not reject unknown/extra optional fields. **Do not bump `CURRENT_SNAPSHOT_VERSION`** for this phase (verify with a unit test that a snapshot lacking `personaId` still round-trips cleanly to `personaId === undefined`).

## Shared Patterns

### localStorage persistence (SSR-guard → try/catch → validate → Sentry-once)
**Source:** `frontend/src/lib/botSetupSettings.ts` (full pattern, lines 89-150)
**Apply to:** `botPersonaSetupSettings.ts` (new key, D-05's last-used color/TC persistence)
```typescript
export function readSetupSettings(ownerKey: string | null | undefined): BotSetupSettings | null {
  if (typeof localStorage === 'undefined') return null;
  const key = setupSettingsKey(ownerKey);
  let raw: string | null;
  try { raw = localStorage.getItem(key); } catch { return null; }
  if (raw === null) return null;
  let parsed: unknown;
  try { parsed = JSON.parse(raw); } catch (err) { clearCorruptSetupSettings(key, err); return null; }
  if (!isValidSetupSettingsShape(parsed)) {
    clearCorruptSetupSettings(key, new Error('bot setup settings has an invalid shape'));
    return null;
  }
  return parsed;
}
```

### Pure predicate + sentinel discipline for engine-adjacent bot decisions
**Source:** `frontend/src/lib/botDrawGate.ts`, `wouldBotResign`/`wouldBotAcceptDraw`
**Apply to:** the new `wouldBotOfferDraw` predicate (D-07/Pitfall 1)
```typescript
if (rootPracticalScore === null) return false; // never decide off an unevaluated position
```

### Toggle-chip visuals
**Source:** `frontend/src/components/bots/chipStyles.ts` (full file, 33 lines)
**Apply to:** `PersonaDetailSurface.tsx`'s color/TC chips
```typescript
export const CHIP_BASE_CLASS = 'rounded border h-10 sm:h-7 text-sm transition-colors';
export const CHIP_ACTIVE_CLASS = 'border-toggle-active bg-toggle-active text-toggle-active-foreground';
export const CHIP_INACTIVE_CLASS = 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground';
```

### Sentry error capture with `source` tag
**Source:** `frontend/src/lib/botSetupSettings.ts` lines 92-99 (`clearCorruptSetupSettings`)
**Apply to:** every new corruption/error path (persona settings storage, avatar-lookup fallback if it ever throws)
```typescript
Sentry.captureException(err, { tags: { source: 'bot-persona-setup-settings' } });
```

### Single entry point / no second start path
**Source:** `frontend/src/pages/Bots.tsx`, `handleStart` (lines 513-516) + the phase-switch structure (lines 546-592)
**Apply to:** `PersonaGrid`'s Play button, `PersonaDetailSurface`'s Play button, Rematch — ALL must call the same `handleStart`/`BotGameSettings`-in callback, never a parallel path.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Vite `.webp` asset import machinery (D-17, deferred per RESEARCH.md Pitfall 6) | config/build | file-I/O | No precedent anywhere in `frontend/src` for `import.meta.glob`/`@/assets/*` image imports (repo-wide grep confirmed zero hits) — this phase ships D-18 emoji+tint placeholders only; do not build the import plumbing speculatively. `personaAvatars.ts` should expose a nullable `avatarSrc?: string` field for forward-compatibility only. |
| `data/personaAvatarPrompts.md` (D-15, the 24 prompt descriptors) | content/doc | n/a | Pure authored content, no code pattern to copy from — follow `botStyleBundles.ts`'s per-entry-doc-comment convention loosely for structure/consistency, not a functional analog. |

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/lib/engine/`, `frontend/src/hooks/`, `frontend/src/components/bots/`, `frontend/src/pages/`
**Files scanned:** botStyleBundles.ts, botStyle.ts, styleOpeningLines.ts, botDrawGate.ts, botDrawGate.test.ts (referenced), useBotGame.ts, botGameSnapshot.ts, botSetupSettings.ts, Bots.tsx, SetupScreen.tsx, chipStyles.ts, ClockDisplay.tsx, GameResultDialog.tsx, GameResultStrip.tsx, theme.ts (referenced)
**Pattern extraction date:** 2026-07-22
