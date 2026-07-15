# Phase 171: Bots Page + Setup Screen + Nav - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 19
**Analogs found:** 17 / 19

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/components/bots/SetupScreen.tsx` (NEW) | component (page-level) | request-response (local state → Start) | `frontend/src/pages/Bots.tsx` (`BotsGame`/`BotsPage` composition) | role-match |
| `frontend/src/components/bots/PlayStyleControl.tsx` (NEW) | component (filter/control) | transform (value ↔ preset ↔ slider) | `frontend/src/components/filters/OpponentStrengthFilter.tsx` + `PresetRangeFilter.tsx` | role-match (sibling, not reuse) |
| `frontend/src/components/bots/ColorPicker.tsx` (NEW, or inline) | component (chip picker) | transform | `PresetRangeFilter.tsx`'s preset-chip block (lines 91-112) | partial-match (subset shape) |
| `frontend/src/components/bots/TimeControlPicker.tsx` (NEW, or inline) | component (chip picker) | transform | `PresetRangeFilter.tsx`'s preset-chip block (lines 91-112) | partial-match (subset shape, grouped) |
| `frontend/src/lib/botTimeControlPresets.ts` (NEW) | config (lookup table) | transform | `frontend/src/lib/opponentStrength.ts` (preset↔range derivation table) | role-match |
| `frontend/src/lib/botSetupSettings.ts` (NEW) | utility (localStorage module) | file-I/O (localStorage) | `frontend/src/lib/botGameSnapshot.ts` (single-object shape) | exact |
| `frontend/src/pages/Bots.tsx` (MODIFIED) | component (page) | request-response | itself (existing `BotsPage`/`BotsGame` split) | exact |
| `frontend/src/App.tsx` (MODIFIED — nav tables) | component (nav/routing config) | transform | itself (existing `NAV_ITEMS`/`BOTTOM_NAV_ITEMS`/`isActive`/lock rules) | exact |
| `frontend/src/components/bots/GameResultDialog.tsx` (MODIFIED) | component | request-response | itself + `frontend/src/components/library/EvalCoverageBadge.tsx` (guest-caveat copy pattern) | exact (self) / role-match (caveat) |
| `frontend/src/components/bots/GameResultStrip.tsx` (MODIFIED) | component | request-response | itself + `EvalCoverageBadge.tsx` | exact (self) / role-match (caveat) |
| `frontend/src/hooks/useMaiaEloDefault.ts` (MODIFIED) | hook | transform | itself (existing free-play branch) | exact |
| `frontend/src/hooks/useStoreBotGame.ts` (consumed, not modified — see D-21 note) | hook | event-driven (mutation) | itself (`useStoreBotGame` export already returns full `UseMutationResult`) | exact |
| `frontend/src/lib/chessClock.ts` (MODIFIED — comment only) | utility | — | itself | exact |
| `frontend/src/hooks/useBotGame.ts` (MODIFIED — doc comment only, D-21 finish effect) | hook | event-driven | itself | exact |
| `app/routers/users.py` (MODIFIED) | router | CRUD (read) | itself (`get_profile`/`update_profile` handlers) | exact |
| `app/schemas/users.py` (MODIFIED) | model (Pydantic schema) | transform | itself (`UserProfileResponse`, `current_rating` field precedent) | exact |
| `frontend/src/App.test.tsx` (NEW) | test | request-response (RTL render) | no direct analog — closest shape: `frontend/src/pages/Bots.test.tsx` / any RTL page test rendering `MemoryRouter` | role-match (none exists for App.tsx itself) |
| `frontend/src/components/bots/SetupScreen.test.tsx` (NEW) | test | request-response (RTL) | `frontend/src/components/filters/OpponentStrengthFilter.test.tsx` (if exists) or `GameResultDialog.test.tsx` | role-match |
| `frontend/src/lib/botSetupSettings.test.ts` (NEW) | test | file-I/O | `frontend/src/lib/botGameSnapshot.test.ts` | exact |
| `tests/test_users_router.py` (MODIFIED — new test class) | test | CRUD | itself (`TestProfileCurrentRating`, lines 297-368) | exact |

## Pattern Assignments

### `frontend/src/lib/botSetupSettings.ts` (utility, file-I/O)

**Analog:** `frontend/src/lib/botGameSnapshot.ts` (full file read — 190 lines)

Mirror this module **verbatim in shape**, single-object (not queue) variant. Key differences from the snapshot module: settings persist ELO/blend/TC/color only (no PGN/clock state), and the key prefix MUST be distinct from both `BOT_GAME_SNAPSHOT_KEY_PREFIX` and `BOT_PENDING_STORE_KEY_PREFIX`.

**Owner-scoped key convention** (copy exactly, `botGameSnapshot.ts:35-42`):
```typescript
export const BOT_GAME_SNAPSHOT_KEY_PREFIX = 'flawchess_bot_game:';

function snapshotKey(ownerKey: string | null | undefined): string {
  return `${BOT_GAME_SNAPSHOT_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}
```
For `botSetupSettings.ts`, use e.g. `BOT_SETUP_SETTINGS_KEY_PREFIX = 'flawchess_bot_setup_settings:'` (RESEARCH.md's suggested literal — distinct from `flawchess_bot_game:` and `flawchess_bot_pending_store:`).

**Read pattern with corruption recovery** (`botGameSnapshot.ts:116-152`, adapt: single object, no `version` field needed unless you want future migration safety — the snapshot module's version-mismatch silent-drop vs. shape-invalid Sentry-capture distinction is worth keeping):
```typescript
export function readSnapshot(ownerKey: string | null | undefined): BotGameSnapshot | null {
  if (typeof localStorage === 'undefined') return null;
  const key = snapshotKey(ownerKey);
  let raw: string | null;
  try {
    raw = localStorage.getItem(key);
  } catch {
    return null;
  }
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    clearCorruptSnapshot(key, err);
    return null;
  }
  // ... shape validation via isValidXShape, else clearCorruptSnapshot + null
}
```

**Write pattern** (`botGameSnapshot.ts:154-167` — silent no-op on SSR/quota):
```typescript
export function writeSnapshot(ownerKey, snapshot): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(snapshotKey(ownerKey), JSON.stringify(snapshot));
  } catch {
    // QuotaExceededError / Safari private mode — degrade to no-resume
  }
}
```

**Sentry-once-on-corruption helper** (`botGameSnapshot.ts:94-105`):
```typescript
function clearCorruptSnapshot(key: string, err: unknown): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // best-effort
  }
  Sentry.captureException(err, { tags: { source: 'bot-game' } });
}
```

**Type-guard shape** (`botGameSnapshot.ts:62-72`, `botPendingStore.ts:40-50` — same `isValidSettingsShape` duplicated in both files today; the new module needs its own for `{botElo, blend, baseSeconds, incrementSeconds, userColor}` plus whatever setup-only fields you add, e.g. `colorPreference: 'white'|'black'|'random'`).

**Anti-pattern warning (RESEARCH.md, explicit):** do NOT reuse `botGameSnapshot.ts`'s `isValidSnapshotShape` validator or key for settings — a settings-shaped object will fail that validator's `pgn`/`whiteClockMs` checks and get wrongly Sentry-flagged as corrupt.

---

### `frontend/src/components/bots/PlayStyleControl.tsx` (component, sibling of PresetRangeFilter)

**Analog:** `frontend/src/components/filters/PresetRangeFilter.tsx` (shell, full file, 129 lines) + `frontend/src/components/filters/OpponentStrengthFilter.tsx` (worked consumer example, full file, 96 lines) + `frontend/src/lib/opponentStrength.ts` (not read this session but cited by RESEARCH.md as the presets↔slider↔summary derivation-table pattern to mirror for `botTimeControlPresets.ts`-style pure functions).

**Do NOT widen `PresetRangeFilter`'s prop type** — `slider.value: [number, number]` and `minStepsBetweenThumbs` are hard range-only (`PresetRangeFilter.tsx:44-52`). Build a new component with the same visual shell but a single-thumb contract.

**Shell to copy (label + InfoPopover + summary row)** — `PresetRangeFilter.tsx:69-88`:
```tsx
<div data-testid={testIdPrefix}>
  <div className="mb-1 flex items-center justify-between gap-2">
    <p className="text-sm text-muted-foreground">
      <span className="inline-flex items-center gap-1">
        {label}
        <InfoPopover ariaLabel={infoAriaLabel} testId={`${testIdPrefix}-info`} side="bottom">
          {infoChildren}
        </InfoPopover>
      </span>
    </p>
    <span
      className={cn('text-sm tabular-nums', isSummaryActive ? 'font-medium text-toggle-active' : 'text-muted-foreground')}
      data-testid={`${testIdPrefix}-summary`}
    >
      {summary}
    </span>
  </div>
```

**Preset chip grid** (2-button grid for Human/Engine, `grid-cols-2`) — `PresetRangeFilter.tsx:91-112`:
```tsx
<div className={cn('mb-1 grid gap-1', gridClassName)} data-testid={`${testIdPrefix}-presets`}>
  {presets.map((preset) => {
    const isActive = activePreset === preset.key;
    return (
      <button
        key={preset.key}
        type="button"
        onClick={() => onPreset(preset.key)}
        data-testid={`${testIdPrefix}-preset-${preset.key}`}
        aria-pressed={isActive}
        className={cn(
          'rounded border h-11 sm:h-7 text-sm transition-colors',
          isActive
            ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
            : 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
        )}
      >
        {preset.label}
      </button>
    );
  })}
</div>
```

**Single-thumb slider wiring** (UI-SPEC.md's already-resolved contract, matches `EloSelector.tsx:99-107`'s confirmed single-thumb usage):
```tsx
<Slider
  min={0.05}
  max={1.00}
  step={0.05}
  value={[blend === 0 ? 0.05 : blend]}
  onValueChange={(values) => { const next = values[0]; if (next !== undefined) onChange(next); }}
  thumbLabels={['Play style']}
  className={blend === 0 ? 'opacity-50' : undefined}
  data-testid="setup-play-style-slider"
/>
```

**Consumer wiring pattern (presets ↔ value ↔ summary)** from `OpponentStrengthFilter.tsx:30-48`:
```tsx
const activePreset = derivePreset(value);       // 'human' | 'engine' | null, blend===0/1
const handleSliderChange = useCallback((values: number[]) => {
  const next = values[0];
  if (next !== undefined) onChange(next);
}, [onChange]);
const handlePreset = useCallback((preset: string) => {
  onChange(preset === 'human' ? 0 : 1);
}, [onChange]);
```

**Active-preset / summary derivation functions** — model on `opponentStrength.ts`'s `derivePreset`/`formatRangeSummary` pattern (not read verbatim this session, but its role is: pure functions colocated near the constants, imported by both the control and its tests). Put `deriveActivePreset(blend)` and `formatPlayStyleSummary(blend)` in a new `frontend/src/lib/playStyle.ts` (or inline in `PlayStyleControl.tsx` if small) so `PlayStyleControl.test.tsx` can unit-test them without RTL.

---

### `frontend/src/lib/botTimeControlPresets.ts` (config, lookup table)

**Analog:** RESEARCH.md's own Code Examples section already contains the exact recommended table (verified against `app/services/normalization.py` boundary rule and `frontend/src/lib/botGamePgn.ts:112-114`'s `toBackendTcStr`). Use verbatim:

```typescript
export interface TimeControlPreset {
  label: string;
  baseSeconds: number;
  incrementSeconds: number;
  bucket: 'blitz' | 'rapid' | 'classical'; // UI grouping label ONLY — see Pitfall 4
}

export const TIME_CONTROL_PRESETS: readonly TimeControlPreset[] = [
  { label: '3+0',  baseSeconds: 180,  incrementSeconds: 0,  bucket: 'blitz' },
  { label: '3+2',  baseSeconds: 180,  incrementSeconds: 2,  bucket: 'blitz' },
  { label: '5+0',  baseSeconds: 300,  incrementSeconds: 0,  bucket: 'blitz' },
  { label: '5+3',  baseSeconds: 300,  incrementSeconds: 3,  bucket: 'blitz' },
  { label: '10+0', baseSeconds: 600,  incrementSeconds: 0,  bucket: 'rapid' },
  { label: '10+5', baseSeconds: 600,  incrementSeconds: 5,  bucket: 'rapid' },
  { label: '15+10',baseSeconds: 900,  incrementSeconds: 10, bucket: 'rapid' },
  // NOTE: 30+0 computes to backend bucket 'rapid' (estimated=1800 -> rapid,
  // parse_time_control's frozen <=1800 boundary), not 'classical' — accepted,
  // documented quirk (RESEARCH.md Pitfall 4). This UI 'bucket' label is
  // display-grouping only, NOT what gets stored server-side.
  { label: '30+0', baseSeconds: 1800, incrementSeconds: 0,  bucket: 'classical' },
  { label: '30+20',baseSeconds: 1800, incrementSeconds: 20, bucket: 'classical' },
] as const;

export const DEFAULT_TC_PRESET_LABEL = '10+0';
```

**Conversion boundary to check when constructing `BotGameSettings`:** `frontend/src/types/bots.ts:22-37`'s in-repo doc comment explicitly warns against passing the display label (`"10+5"`) into the settings/store request — convert to `{baseSeconds, incrementSeconds}` first. `toBackendTcStr` (`frontend/src/lib/botGamePgn.ts:112-114`) is the existing function that does the reverse (seconds → wire string) at store time — do not duplicate its logic in the new preset table.

---

### `frontend/src/pages/Bots.tsx` (MODIFIED — setup screen wiring)

**Analog:** itself. Full file read (346 lines). Key excerpt — the stub to delete:

```typescript
// DELETE this (Bots.tsx:40-51):
const BOT_GAME_SETTINGS: BotGameSettings = {
  botElo: 1500,
  blend: 0.5,
  baseSeconds: 300,
  incrementSeconds: 3,
  userColor: 'white',
};
```

**Insertion point** — `BotsPage`'s render (Bots.tsx:334-345), currently:
```tsx
if (boot === null) {
  return <div data-testid="bots-page-loading" ...>Loading…</div>;
}
return (
  <BotsGame key={boot.nonce} resume={boot.resume} ownerKey={ownerKey} onDiscard={handleDiscard} />
);
```
D-09 requires branching here: `boot.resume === null` → render `<SetupScreen onStart={handleStart} ... />` instead of unconditionally mounting `BotsGame`. `boot.resume !== null` still mounts `BotsGame` immediately (ResumeGate overlay, unchanged per D-13).

**D-21 finish-store effect** — new code, no direct in-repo analog for "effect keyed on a value transitioning to non-null triggers a mutation." Closest existing shape is the boot effect pattern itself (`Bots.tsx:305-309`, `if (isLoading) return; if (boot !== null) return;` — a fire-once guard via ref/state) and `useDrainPendingStore`'s `hasDrainedRef` guard (`Bots.tsx:316-322`):
```typescript
const hasDrainedRef = useRef(false);
useEffect(() => {
  if (isLoading) return;
  if (hasDrainedRef.current) return;
  hasDrainedRef.current = true;
  void drain();
}, [isLoading, drain]);
```
Mirror this exact "fire once per relevant transition" shape for the D-21 finish-store effect, keyed on `game.outcome` becoming non-null (reset the ref when a new game starts, matching the existing `dialogDismissed` reset-on-new-game pattern at `Bots.tsx:200-202`: `useEffect(() => { if (game.outcome === null) setDialogDismissed(false); }, [game.outcome]);`).

---

### `frontend/src/App.tsx` (MODIFIED — nav entries D-16/17/18)

**Analog:** itself (full nav section read, lines 40-433).

**NAV_ITEMS / BOTTOM_NAV_ITEMS insertion** (`App.tsx:67-77`):
```typescript
const NAV_ITEMS = [
  { to: '/library', label: 'Library', Icon: FolderOpen },
  { to: '/bots', label: 'Bots', Icon: Bot },        // NEW, 2nd (D-16)
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/endgames', label: 'Endgames', Icon: TrophyIcon },
] as const;

const BOTTOM_NAV_ITEMS = [ /* same insertion */ ] as const;
```
Note: `Bot` icon import needed from `lucide-react` (not currently imported — check for a naming collision with the `BotGameSettings` type or `BotsPage` component; alias if needed, e.g. `import { Bot as BotIcon } from 'lucide-react'`).

**ROUTE_TITLES** (`App.tsx:85-91`): add `'/bots': 'Bots',`.

**isActive()** (`App.tsx:95-100`): add `if (to === '/bots') return pathname.startsWith('/bots');`.

**Three lock-rule exemption sites (NOT identical — each has its own exemption list, per RESEARCH.md Pattern 4):**
```typescript
// NavHeader (App.tsx:135) — 2-clause list, append /bots:
const locked = to !== '/library' && to !== '/admin' && to !== '/bots' && !navUnlocked;

// MobileBottomBar (App.tsx:300) — 1-clause list, append /bots:
const locked = to !== '/library' && to !== '/bots' && !navUnlocked;

// MobileMoreDrawer (App.tsx:386) — 2-clause list, append /bots (mirrors NavHeader):
const locked = to !== '/library' && to !== '/admin' && to !== '/bots' && !navUnlocked;
```

**Do NOT add a notification dot for `/bots`** (Pitfall 6, locked by UI-SPEC) — no `showBotsDot` analog to the `showOpeningsDot`/`showEndgamesDot` pattern at `App.tsx:118-121`/`290-291` should be created.

---

### `frontend/src/components/bots/GameResultDialog.tsx` / `GameResultStrip.tsx` (MODIFIED)

**Analog:** themselves (both full files read, 73 and 49 lines).

**Current "New game" wiring to rewire (D-11)** — `GameResultDialog.tsx:65-67`:
```tsx
<Button variant="default" onClick={onNewGame} data-testid="btn-new-game">
  New game
</Button>
```
`onNewGame` currently receives `game.newGame` from `Bots.tsx:282`/`113`. Per D-11, the prop should instead be a callback that returns to the setup screen (mirrors `BotsPage.handleDiscard`'s `key`-changed remount pattern, `Bots.tsx:329-332`) — NOT `game.newGame()` anymore.

**"Saved to your Library" + guest caveat insertion point** — add below `DialogFooter` in `GameResultDialog.tsx` (dialog) and below the button row in `GameResultStrip.tsx:33-45` (strip), gated as UI-SPEC.md specifies: only on `useStoreBotGame` mutation `status === 'success'`.

**Guest-caveat copy-pattern analog:** `frontend/src/components/library/analysisCoverageCopy.tsx` (`ANALYSIS_COVERAGE_INFO_COPY`, cited by RESEARCH.md at lines 13-15 — not re-read this session since UI-SPEC.md already locks the exact copy string: *"Guest games aren't analyzed automatically. Use 'Analyze this game' above, or sign up for automatic analysis of every game."*). Follow the same "problem stated, two paths forward, no jargon" tone; render as plain `text-sm` body copy, not a popover (CLAUDE.md text-sm floor — this is NOT the tooltip-exception surface).

**Accent link color convention** (theme.ts, per CLAUDE.md — do not hardcode): use the same `text-brand-brown-light` (or equivalent theme.ts token) that `EvalCoverageBadge.tsx`'s signup-CTA link already uses — check `frontend/src/lib/theme.ts` for the exact exported constant name at plan/implementation time rather than hardcoding a raw Tailwind class.

---

### `frontend/src/hooks/useMaiaEloDefault.ts` (MODIFIED — D-08 free-play branch)

**Analog:** itself (full file, 144 lines).

**Interface to widen** (`useMaiaEloDefault.ts:42-45`):
```typescript
export interface MaiaEloProfile {
  current_rating: number | null;
  lichess_blitz_equivalent_rating: number | null;  // NEW, D-08
}
```

**Free-play branch to repoint** (`useMaiaEloDefault.ts:102`, inside `deriveRawDefault`):
```typescript
// BEFORE:
return profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO;
// AFTER (D-08):
return profile?.lichess_blitz_equivalent_rating ?? FREE_PLAY_DEFAULT_ELO;
```
Game-mode branch (`useMaiaEloDefault.ts:94-101`, already normalized via Phase 164's `white_rating_lichess_blitz`) is untouched — same normalization pattern, just applied to the free-play input too.

---

### `app/schemas/users.py` (MODIFIED — D-07 new field)

**Analog:** itself — the existing `current_rating` field is the direct precedent for shape, placement, and doc-comment style (`app/schemas/users.py:29-32`):

```python
class UserProfileResponse(BaseModel):
    ...
    # MAIA-04 / D-07: rating from the user's most-recent game (across platforms),
    # read-only, index-backed. Feeds the free-play ELO-selector default. None
    # when the user has no games or their most recent game is unrated.
    current_rating: int | None = None

    # NEW — Phase 171 D-07: lichess-blitz-equivalent rating, derived from the
    # user's blitz-bucket user_rating_anchors row (already the blended
    # lichess-equivalent median Phase 167 trusts for bot-game rating
    # derivation). None for guests and users with no blitz-bucket anchor
    # (e.g. rapid/classical-only players) — the frontend falls back to 1500
    # (D-07). UI DEFAULT ONLY: never fed into bot move selection (BOT-03) —
    # see the setup-screen wiring comment in botSetupSettings.ts / SetupScreen.tsx.
    lichess_blitz_equivalent_rating: int | None = None
```

---

### `app/routers/users.py` (MODIFIED — D-07, both handlers)

**Analog:** itself — `get_profile` (lines 68-99) and `update_profile` (lines 102-128), both already call `game_repository.get_current_rating_by_platform` and construct `UserProfileResponse` field-by-field. Add one more repository call alongside it in BOTH handlers:

```python
from app.repositories import user_rating_anchors_repository  # add to existing import block (line 15)

# Inside get_profile (after the existing `ratings = await game_repository...` line, ~:83):
anchors = await user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=user.id)
blitz_anchor = anchors.get("blitz")
lichess_blitz_equivalent_rating = blitz_anchor.anchor_rating if blitz_anchor is not None else None
# ... then pass lichess_blitz_equivalent_rating=lichess_blitz_equivalent_rating
# into the UserProfileResponse(...) constructor call (both ~:84-99 and ~:113-128).
```

**Repository being called** — `app/repositories/user_rating_anchors_repository.py`: `fetch_anchors_for_user(session, *, user_id: int) -> dict[TimeControlBucket, RatingAnchorRow]` (keyword-only `user_id`, confirmed at line 129; `RatingAnchorRow` dataclass at line 41 has an `anchor_rating` field). Follow the SAME `user_id` keyword-only calling convention as `game_repository.get_current_rating_by_platform` already uses in this file (V4 access-control convention, per the repository's own docstring at `user_rating_anchors_repository.py:17-23`).

**Helper-function precedent** (optional, for readability) — the existing `_primary_current_rating` helper (`users.py:26-35`) is the model for extracting a small pure derivation function out of the handler body if the blitz-anchor lookup grows non-trivial; not required for a 3-line lookup.

---

## Shared Patterns

### Owner-scoped localStorage (D-10)
**Source:** `frontend/src/lib/botGameSnapshot.ts` (full pattern) + `frontend/src/lib/botPendingStore.ts` (sibling, queue variant — shows the "same shape, different key, different container type" precedent already established in this codebase)
**Apply to:** `botSetupSettings.ts`
```typescript
function key(ownerKey: string | null | undefined): string {
  return `${PREFIX}${ownerKey ?? 'anon'}`;
}
// SSR guard -> try/catch -> JSON.parse -> shape validator -> Sentry-once-on-corruption
```

### Preset + slider control shell (D-01)
**Source:** `frontend/src/components/filters/PresetRangeFilter.tsx` (shell), `OpponentStrengthFilter.tsx` (consumer wiring)
**Apply to:** `PlayStyleControl.tsx` (new sibling component — NOT a `PresetRangeFilter` prop variant, since that component's `slider.value` type is hard-typed `[number, number]`)

### Nav lock-rule exemption (D-17)
**Source:** `frontend/src/App.tsx` — three near-identical `locked = to !== ... && !navUnlocked` expressions in `NavHeader` (line 135), `MobileBottomBar` (line 300), `MobileMoreDrawer` (line 386)
**Apply to:** all three, each appending `&& to !== '/bots'` to its OWN existing exemption list (they are not identical today — do not copy one verbatim into the others).

### Backend derived-field-from-anchor read (D-07)
**Source:** `app/routers/users.py`'s existing `current_rating` derivation (`_primary_current_rating` + `game_repository.get_current_rating_by_platform`)
**Apply to:** the new `lichess_blitz_equivalent_rating` field, sourced from `user_rating_anchors_repository.fetch_anchors_for_user` instead — same "call repository, extract scalar, pass into response constructor in both GET and PUT handlers" shape.

### Guest not-auto-analyzed copy (D-20)
**Source:** `frontend/src/components/library/analysisCoverageCopy.tsx` / `EvalCoverageBadge.tsx` / `NoAnalysisState.tsx` (established guest-caveat tone; UI-SPEC.md already locks the exact copy string for this phase)
**Apply to:** `GameResultDialog.tsx` / `GameResultStrip.tsx`'s new post-store guest caveat row.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/App.test.tsx` | test | request-response (RTL) | RESEARCH.md confirms no `App.test.*` file exists today — this is the FIRST nav-level RTL test in the codebase. Build from RTL fundamentals (`render` + `MemoryRouter` + mock `useUserProfile`/`useReadiness`/`useAuth`), not from an existing App-level analog. Closest structural precedent for "render inside routing/query providers" is any existing page test that wraps in the app's provider stack (check `frontend/src/pages/*.test.tsx` at plan time for the provider-wrapping boilerplate to copy) — none read this session, flag for the planner to locate the actual wrapping helper (e.g. a `renderWithProviders` test util) before writing this file. |
| D-21's finish-time mutation-trigger effect (`Bots.tsx`) | hook logic (event-driven) | event-driven | No existing "effect fires a mutation exactly once on a value's null→non-null transition, with de-dupe against a second source (the pending-queue drain)" pattern exists in this codebase yet — closest partial analogs are the `hasDrainedRef`/`boot` fire-once effects in `Bots.tsx` (cited above) and `useMaiaEloDefault.ts`'s `userOverrodeRef` latch, but neither handles the double-POST dedupe RESEARCH.md's Assumption A2 / Pitfall 3 flags as needing an explicit test. Treat as new logic, verified by a dedicated "finish → store → remount → no second POST" test per D-21's explicit requirement. |

## Metadata

**Analog search scope:** `frontend/src/components/filters/`, `frontend/src/components/bots/`, `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/pages/Bots.tsx`, `frontend/src/App.tsx`, `app/routers/users.py`, `app/schemas/users.py`, `app/repositories/user_rating_anchors_repository.py`, `tests/test_users_router.py`, `tests/services/test_store_bot_game_service.py`
**Files scanned (full or targeted reads this session):** 15
**Pattern extraction date:** 2026-07-14
