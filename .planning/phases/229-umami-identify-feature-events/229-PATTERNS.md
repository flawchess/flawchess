# Phase 229: Umami User Identification & Feature Events - Pattern Map

**Mapped:** 2026-10-03
**Files analyzed:** ~40 (core identity/registry files + leaf instrumentation sites from RESEARCH inventory)
**Analogs found:** all core files have an in-repo analog; leaf handlers copy the SettingsPanel handler pattern

All analog paths below are git-tracked source (no mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/analytics.ts` (identifyUser, distinctIdFromToken, FEATURE_EVENTS / FeatureEventMap, trackFeature, currentPage, useTrackedOpen) | utility | event-driven | itself (`trackEvent`, `identifyAccountType`, `scrubUmamiPayload`) + `lib/push.ts:52-75` (base64url decode) | exact |
| `frontend/src/lib/__tests__/analytics.test.ts` | test | - | itself (`Umami globals` describe, lines 42-60) | exact |
| `frontend/src/main.tsx` | config/boot | event-driven | itself lines 21-28 (`captureFirstTouch`, `installUmamiBeforeSend`) | exact |
| `frontend/src/App.tsx` (ProtectedLayout effect, More drawer, settings open) | layout component | event-driven | itself lines 661-664, 706-709 | exact |
| `frontend/src/hooks/useAuth.ts` (load-bearing reload comments, optional fold of hard nav into `logoutForPromotion`) | hook | request-response | itself lines 158-182 | exact |
| `frontend/src/hooks/__tests__/useAuth.test.tsx` (new, D-07) | test | - | `frontend/src/api/__tests__/client.unauthorized.test.ts` (auth_token/localStorage handling) | role-match |
| `frontend/src/components/ui/info-popover.tsx` + 7 shells (`MetricStatPopover`, `AchievableScorePopover`, `FlawBulletPopover`, `BulletConfidencePopover`, `ScoreConfidencePopover`, `PercentileChip`, `PersonaEloDisclosurePopover`) | component | event-driven | `info-popover.tsx:22-33` (the useState to replace) | exact |
| `frontend/src/components/filters/{FilterPanel,FlawFilterControl,FilterActions,MobileFilterDrawer,OpponentStrengthFilter}.tsx`, `OpeningsFilterFields.tsx` | component | event-driven | `components/settings/SettingsPanel.tsx:31-41` | exact (handler + guard + track) |
| `frontend/src/components/layout/SidebarLayout.tsx` | component | event-driven | itself `handleStripClick` lines 91-93 | exact |
| `frontend/src/components/analysis/{AnalysisTabs,EloSelector,TemperatureSelector,AnalysisTagsPanel,EngineLines,FlawChessEngineLines,VariationTree,PasteModal}.tsx`, `components/board/BoardControls.tsx`, `pages/Analysis.tsx` | component | event-driven | SettingsPanel handler pattern | role-match |
| Train/Bots leaf files (`TrainSolveScreen`, `TrainReveal`, `TrainScheduleSettings`, `TrainReminderResurfaceBanner`, `SetupScreen`, `PersonaDetailSurface`, `PlayStyleControl`, `PersonaCard`, `PersonaGrid`, `ResumeGate`, `GameResultDialog`, `BotDrawOfferActions`, `MoveListPanel`) | component | event-driven | SettingsPanel handler pattern; `bots/EngineReadyGate.tsx:60-72` (named constants) | role-match |
| Component tracking tests (new: `FilterPanel.tracking.test.tsx`, `AnalysisTabs.tracking.test.tsx`, `SidebarLayout.test.tsx`, `info-popover.test.tsx`, EloSelector) | test | - | `components/settings/__tests__/SettingsPanel.test.tsx` | exact |
| Existing tests mocking analytics: `SettingsPanel.test.tsx:14`, `EngineReadyGate.test.tsx:31`, `ImportAskActions.test.tsx:14` | test | - | - | modify (see Shared: mocks) |
| `frontend/src/pages/Privacy.tsx:58` | static page | - | - | copy edit |
| `frontend/CLAUDE.md` Umami section | docs | - | itself | edit |
| `.planning/notes/active-engagement-time-tracking.md` | docs | - | - | pointer + correct localStorage claim (lines 65-66) |
| `docker-compose.yml:122` | config | - | `docker-compose.yml:3` (`postgres:18-alpine`, explicit tag) | exact |
| `docs/production-runbook.md` (D-18 deletion step) | docs | - | runbook `## Server` section (bash block + bullets) | role-match |

## Pattern Assignments

### `frontend/src/lib/analytics.ts` (utility, event-driven)

**Current global typing to retype** (lines 23-32):
```ts
declare global {
  interface Window {
    umami?: {
      track: (eventName: string, eventData?: Record<string, string>) => void;
      identify: (sessionData: Record<string, string>) => void;   // -> (distinctId: string, data?: Record<string, string>) => void
    };
    umamiBeforeSend?: (type: string, payload: UmamiPayload) => UmamiPayload;
  }
}
```

**Base no-op wrapper to build trackFeature on** (lines 34-36):
```ts
export function trackEvent(eventName: string, eventData?: Record<string, string>): void {
  window.umami?.track(eventName, eventData);
}
```

**Identify function to replace** (lines 97-107). Keep `UmamiAccountType`; delete `identifyAccountType` once unused (knip fails on dead exports):
```ts
export type UmamiAccountType = 'guest' | 'registered';
export function identifyAccountType(accountType: UmamiAccountType): void {
  window.umami?.identify({ account: accountType });
}
```
Replace with string-form `identifyUser(distinctId, accountType?)` per RESEARCH Pattern 1 (check `window.umami` BEFORE writing `lastIdentifyKey`, Pitfall 7).

**Named constant + doc-comment style** (lines 45-52): module-level `const` with a JSDoc explaining the why, e.g. `const SENSITIVE_QUERY_PARAMS: readonly string[] = ['token'];`. Use the same for `PAGE_IDS`, `PAGE_BY_SEGMENT`, `FEATURE_EVENT_NAMES`.

**try/catch fallback style** (lines 54-67, `stripSensitiveParams`): `try { ... } catch { return value; }` -> `distinctIdFromToken` returns `null` in catch.

**base64url decode precedent** (`frontend/src/lib/push.ts`, `BASE64_PAD_MODULUS` + `urlBase64ToUint8Array`):
```ts
const BASE64_PAD_MODULUS = 4;
const padding = '='.repeat(
  (BASE64_PAD_MODULUS - (base64String.length % BASE64_PAD_MODULUS)) % BASE64_PAD_MODULUS,
);
const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
const rawData = window.atob(base64);
```
Copy the padding logic (named constant, no magic 4). Do not add `jwt-decode`. Do not import from push.ts (different concern); a small local helper is fine.

---

### `frontend/src/lib/__tests__/analytics.test.ts` (test)

**Header/imports** (lines 1-3):
```ts
// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { identifyAccountType, installUmamiBeforeSend, scrubUmamiPayload } from '@/lib/analytics';
```
**Global stub + cleanup pattern** (lines 42-58) — replace the `identifies only the coarse account type` test:
```ts
describe('Umami globals', () => {
  afterEach(() => {
    delete window.umami;
    delete window.umamiBeforeSend;
  });
  it('identifies only the coarse account type', () => {
    const identify = vi.fn();
    window.umami = { track: vi.fn(), identify };
    identifyAccountType('guest');
    expect(identify).toHaveBeenCalledWith({ account: 'guest' });
  });
```
New assertions: `identify('123', { account: 'guest' })`, dedupe same key, retry after tracker absent, impersonation token -> null, scrub passes `id`/`data` through (copy the `leaves tokenless urls byte-identical` shape, lines 36-39). Dedupe state is module-level: expose a test reset or use `vi.resetModules()` + dynamic import in `beforeAll`/`beforeEach` (memory: hoist `await import` out of test bodies).

---

### `frontend/src/main.tsx` (boot)

**Analog** (lines 11, 21-28):
```ts
import { installUmamiBeforeSend } from "@/lib/analytics";
...
// Scrub credentials and the Google OAuth referrer from every Umami payload.
// The deferred tracker sends its first pageview only once the document is
// complete, so registering the hook here always precedes it.
installUmamiBeforeSend();
```
Add the boot identify call directly after line 28 with the same comment style (one exported helper from analytics.ts, e.g. `identifyFromStoredToken()`, reading `localStorage.getItem('auth_token')` only, never `guest_token`, in try/catch like `useAuth.ts:44`).

---

### `frontend/src/App.tsx` (ProtectedLayout)

**Analog** (lines 661-664 and 704-709):
```ts
function umamiAccountTypeOf(profile: UserProfile | undefined): UmamiAccountType | null {
  if (profile == null || profile.impersonation != null) return null;
  return profile.is_guest ? 'guest' : 'registered';
}
...
  const { token, refreshAuthToken } = useAuth();   // token already available
...
  // Split Umami reports by guest vs registered. Skipped while impersonating so
  // the admin's browser session is not relabelled with the target's type.
  const umamiAccountType = umamiAccountTypeOf(profile);
  useEffect(() => {
    if (umamiAccountType !== null) identifyAccountType(umamiAccountType);
  }, [umamiAccountType]);
```
Change: `const id = distinctIdFromToken(token); if (id !== null && umamiAccountType !== null) identifyUser(id, umamiAccountType);` deps `[token, umamiAccountType]`. Update the comment (no longer "no identifier"). More drawer: `setMoreOpen(true)` (~line 826), nav `<Link>` onClick (~line 600, keep locked-item `preventDefault` branch), `openSettings` (~line 578).

---

### `frontend/src/hooks/useAuth.ts` (D-07)

**Analog** (lines 158-182):
```ts
  const logout = (): void => {
    queryClient.clear();
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('promote_intent');
    setToken(null);
    setUser(null);
    window.location.href = '/';
  };

  const logoutForPromotion = useCallback((): void => {
    ...
    sessionStorage.setItem('promote_intent', '1');
    // No redirect — caller navigates to register page.
  }, []);
```
Add the load-bearing comment above `window.location.href = '/'` (text in RESEARCH "Load-bearing reload comment"). Optional: fold `window.location.href = '/login?tab=register'` into `logoutForPromotion` and drop it from the three callers (`SignupAskActions.tsx:61-62`, `Welcome.tsx:39-40`, `EvalCoverageBadge.tsx:114-115`).

---

### `frontend/src/components/ui/info-popover.tsx` + 7 shells (popover-open)

**Analog** (lines 22-33):
```tsx
function InfoPopover({ children, ariaLabel, testId, side = "top", icon: Icon = HelpCircle, triggerContent }: InfoPopoverProps) {
  const [open, setOpen] = React.useState(false)
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleMouseEnter = () => { hoverTimeout.current = setTimeout(() => setOpen(true), 100) }
  ...
  <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
```
Swap only line 23 for `const [open, setOpen] = useTrackedOpen(testId)`; both hover and tap paths route through `setOpen`, so no other change. Same one-line swap in each shell (lines listed in RESEARCH Pattern 3; `PersonaEloDisclosurePopover` passes the literal `"persona-elo-disclosure"`). Note: this file uses no-semicolon double-quote style (shadcn); keep it.

---

### Filter / board / train / bot handlers (filter-change, toggle, option-change, board-tool, action)

**Analog:** `frontend/src/components/settings/SettingsPanel.tsx:5, 31-41`
```ts
import { trackEvent } from '@/lib/analytics';
...
  const handleChange = (next: string): void => {
    // Radix single-select emits '' when the active item is re-tapped: keep the
    // current value and fire nothing (no write, no Umami event).
    if (next === '') return;
    const parsed = Number(next);
    if (parsed === value) return;
    setCountSetting(id, parsed);
    trackEvent('settings-change', { setting: id, value: String(parsed) });
  };
```
Rule to copy: guard empty/unchanged first, perform the state write, then one `trackFeature(...)` call in the handler. Never in a `useEffect` on the value (D-03). Sliders: track in Radix `onValueCommit` (passes through `components/ui/slider.tsx:22`), not `onValueChange`.

**Named-constant event style** for non-registry strings: `bots/EngineReadyGate.tsx:60-72` (`const ENGINE_GATE_SHOWN_EVENT = 'engine-gate-shown';`). With the typed registry the event names live in `analytics.ts`; call sites pass literals type-checked by `FeatureEventMap`.

### `frontend/src/components/layout/SidebarLayout.tsx` (panel-open)

**Analog** (lines 91-93):
```ts
  const handleStripClick = (panelId: string) => {
    onActivePanelChange(activePanel === panelId ? null : panelId);
  };
```
Fire `panel-open` only in the opening branch (`activePanel !== panelId`). `panelId` is `string`: narrow to the `'filters' | 'bookmarks' | 'tags'` union (type the `panels` prop ids) so the registry type holds.

`MobileFilterDrawer.tsx`: no current tracking; add typed `panel` prop and a ref-guarded false->true transition (the only allowed effect-style site, RESEARCH Anti-Patterns).

---

### Component tracking tests

**Analog:** `frontend/src/components/settings/__tests__/SettingsPanel.test.tsx:1-18, 58, 71-72`
```ts
// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const { trackEventMock } = vi.hoisted(() => ({ trackEventMock: vi.fn() }));
vi.mock('@/lib/analytics', () => ({ trackEvent: trackEventMock }));
beforeEach(() => { trackEventMock.mockClear(); });
...
expect(trackEventMock).toHaveBeenCalledTimes(1);
expect(trackEventMock).toHaveBeenCalledWith('settings-change', { setting: 'fcArrows', value: '3' });
```
For new tests prefer the partial-real mock (below) and assert on `trackEvent` with `{ page, target, value }`; also assert "render fires nothing" (D-03). Project registers no jest-dom matchers (see `EngineReadyGate.test.tsx:35`).

---

### `docker-compose.yml` (D-17)

**Analog** (line 3 vs line 122):
```yaml
    image: postgres:18-alpine                              # explicit version
...
  umami:
    image: ghcr.io/umami-software/umami:postgresql-latest  # -> ghcr.io/umami-software/umami:3.4.0
```
Add a short comment explaining the pin (floating tag changed session semantics; CI `docker compose up -d` never pulls, `.github/workflows/ci.yml:267-268`, so the deploy must pull the new image).

### `docs/production-runbook.md` (D-18)

**Analog style** (`## Server`, lines 7-30): an `##` heading, one-line intro, fenced ```bash``` block of commented `ssh flawchess "cd /opt/flawchess && docker compose ..."` commands, then bullets. New section e.g. `## Account deletion: Umami tail` with `ssh flawchess "cd /opt/flawchess && docker compose exec db psql -U ... umami"` and SQL deleting by `distinct_id` from `session_link`, `session_data`, `website_event`, `event_data` (via session_id), then `session`. Confirm table names against Umami prisma schema (RESEARCH: `session_link` PK `(website_id, distinct_id, session_id)`). Place near `## Infrastructure notes`.

## Shared Patterns

### Analytics mocks in existing tests (Pitfall 4)
**Apply to:** `SettingsPanel.test.tsx:14`, `EngineReadyGate.test.tsx:31`, `ImportAskActions.test.tsx:14-16`, and any test rendering a component that now calls `trackFeature`/`useTrackedOpen`.
Current factories export only `trackEvent`, so `trackFeature`/`useTrackedOpen` resolve `undefined`:
```ts
vi.mock('@/lib/analytics', () => ({ trackEvent: vi.fn() }));          // EngineReadyGate
vi.mock('@/lib/analytics', () => ({ trackEvent: trackEventMock }));   // SettingsPanel
```
Replace with:
```ts
vi.mock('@/lib/analytics', async (orig) => ({ ...(await orig<typeof import('@/lib/analytics')>()), trackEvent: trackEventMock }));
```
Keep `trackFeature` implemented via `trackEvent` so these spies see feature events. Grep all `vi.mock('@/lib/analytics'` before each wave.

### Impersonation guard (D-11)
**Source:** `App.tsx:661-664` (`profile.impersonation != null`) plus JWT `is_impersonation === true` in `distinctIdFromToken`. Both guards must apply; mutation-check each by reverting.

### Comment style for fixes / load-bearing code
**Source:** `main.tsx:25-28`, `analytics.ts:38-52`: short why-comment at the site, phase/decision ref (e.g. "Phase 229 D-07").

### Value unions
Import from existing sources (`types/api.ts` TimeControl/MatchSide, FilterPanel `FilterState`, bot TC preset const); never redeclare. `tsconfig.app.json` excludes tests, so call sites + `npm run build` are the type gate.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `useTrackedOpen` hook (in analytics.ts) | hook | event-driven | No existing tracking hook; build per RESEARCH Pattern 3 |
| `frontend/src/hooks/__tests__/useAuth.test.tsx` | test | - | No useAuth test exists; closest auth-token test is `api/__tests__/client.unauthorized.test.ts` |
| Runbook Umami SQL | docs | - | No SQL blocks in the runbook yet; use bash/psql block style |

## Metadata

**Analog search scope:** `frontend/src/lib`, `frontend/src/components/{settings,bots,train,ui,layout,filters}`, `frontend/src/hooks`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `docker-compose.yml`, `docs/production-runbook.md`
**Files scanned:** ~15
**Pattern extraction date:** 2026-10-03
