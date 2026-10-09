# Phase 229: Umami User Identification & Feature Events - Research

**Researched:** 2026-10-03
**Domain:** Self-hosted Umami v3 tracker/server semantics, React instrumentation, typed analytics registry
**Confidence:** HIGH for tracker/server behavior (read the deployed script and the matching tagged source), HIGH for the inventory (read the handlers), MEDIUM for the legal/privacy reading

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Locked upstream in SEED-183 / ROADMAP and not re-decided here:

- Raw `users.id` as `distinct_id` (no opaque `analytics_id`, no HMAC). Pre-guest landing pageviews
  stay anonymous. Guest promotion keeps the same `users` row, so the id is stable across promotion.
- Keep the `account: guest|registered` session tag (`identifyAccountType`). Retype
  `window.umami.identify` to the `(distinctId, data)` signature.
- Few event names with props, not auto-capture. DB-known actions (signups, imports, analysis runs)
  stay un-evented. Internal links use `trackEvent()` in `onClick`, never `data-umami-event` on a
  `<Link>`.
- Privacy copy: replace "No personal data is collected or shared" in `Privacy.tsx` with one
  sentence: usage analytics are linked to your account ID (logged-in and guest), stay on our
  servers, and are never shared.
- `frontend/CLAUDE.md`: add a rule that new features ship with their event; touch up the existing
  "don't duplicate DB-known actions" wording (it frames Umami as anonymous).
- Add a "superseded for usage analytics by SEED-183" pointer in
  `.planning/notes/active-engagement-time-tracking.md`.
- Post-ship verification: `session.distinct_id` populated in the `flawchess-umami-db` MCP (baseline:
  0 of 1,941 app sessions in the 30 days to 2026-10-03).

#### Event taxonomy
- **D-01:** Verb-level event names (roughly 6-10) with props, e.g. `tab-switch`, `toggle`,
  `filter-change`, `board-tool`, `popover-open`, `panel-open`, plus the existing `settings-change`.
  Props: `page`, `target`, and `value` where a value applies. One dashboard row per interaction
  type, broken down by props. Exact name list is the planner's call within this shape.
  — **Reversibility:** costly — renaming an event later splits its history in Umami into two series.
- **D-02:** No events for URL-routed tab switches (Openings/Endgames/Library sub-tabs such as
  `/openings/*`, `/library/stats`); their pageviews already answer "is this tab used".
  `tab-switch` only fires for tabs that don't change the URL (e.g. `AnalysisTabs.tsx`
  moves/eval/human/flawchess/stats) and in-page view toggles.
- **D-03:** Toggles, filters, and selectors fire on **user-initiated change only**, from the
  onClick/onChange handler, with the new value. No events on mount, URL/state restore, or
  programmatic changes.
- **D-04:** Prop values are enumerated only: typed `Literal`-style unions (tab ids, setting ids,
  on/off, bucket names, page ids). Never FENs, usernames, opponent names, opening names, game ids,
  or free text. Enforce through a typed wrapper in `lib/analytics.ts` (e.g. `trackFeature()`), so
  the event/prop vocabulary lives in one typed registry instead of loose strings at call sites.
- **D-05:** Existing events stay as-is, no renames: `signup-cta`, `import-cta`, `guest-start`, PWA
  funnel (`pwa-installed`, `pwa-install-outcome`, `pwa-install-offer-shown`), `settings-change`,
  `settings-reset`, engine-gate events, all `outbound-*`. New scheme applies to new events only.
- **D-06:** Skip high-frequency interactions: move stepping (arrow keys/buttons), piece drag, eval
  chart scrubbing. Track the discrete feature toggles instead (engine on/off, arrows, flip board,
  Maia panel, etc.).

#### Identity edge cases
- **D-07:** Logout / account switch is a **clean break, whatever it takes**: traffic after logout
  must never carry the previous user's id. If the tracker has no reset API and keeps the id in
  memory or storage, logout does a full page reload and/or clears the tracker's storage. Research
  picks the mechanism; the requirement is non-negotiable. Covers `logout` and
  `logoutForPromotion` in `frontend/src/hooks/useAuth.ts` and any login-as-another-user path.
- **D-08:** Prefer **no browser storage**: keep the id in memory and re-identify on every app load
  (the `ProtectedLayout` effect in `App.tsx` already runs per load). This keeps the "cookie-free"
  claim honest and makes D-07 trivial. Only if research shows the tracker persists the id
  unavoidably: accept it and add a storage clause to the Privacy sentence.
- **D-09:** The first pageview of a load fires before the profile query resolves and may lack the
  id. Acceptable **if** Umami stitches `distinct_id` at session level (a later identify in the same
  session covers earlier pageviews). Research verifies; only if it does not stitch, fix it (e.g.
  re-send or manual pageview), preferring the least invasive option.
- **D-10:** Superuser/admin sessions are identified normally; analysis queries exclude known admin
  ids. No `account: admin` tag.
- **D-11:** Impersonation keeps skipping identify entirely (current `umamiAccountTypeOf` behavior),
  so the admin's browser is never attributed to the impersonated user's id. Extend the same guard
  to the new id-carrying identify call.

#### Inventory scope
- **D-12:** Inventory covers four surface groups:
  1. **Analysis board:** `AnalysisTabs` tab switches, Maia ELO + temperature selectors, engine
     toggles, arrows, flip board, position bookmarks, other board tools.
  2. **Openings / Endgames / Library:** filter changes (TC, color, rated, recency, platform,
     opponent type), move-explorer toggles, chart/table view toggles, flaw-card actions.
  3. **Train + Bots:** Train start-screen options, hint/reveal/skip-style actions, bot setup
     choices (TC presets, color, strength).
  4. **Info popovers + nav:** explanation/info-icon popover opens, mobile "More" drawer items.
  The Phase 228 settings overlay is already instrumented (`settings-change`, `settings-reset`).
- **D-13:** Panel/popover opens: track **both** explanation popover opens **and** filter-panel
  opens (owner wants discovery vs actual use visible). This is the one exception to D-03's
  "change only" rule: opening a filter panel fires its own open event; changing a filter inside it
  fires `filter-change`.
- **D-14:** Exclude `/admin`, `/activity`, and auth flows (login, register, password reset,
  OAuth callback). Auth outcomes are DB-known; `signup-cta` already covers attribution.
- **D-15:** No inventory review gate. The planner builds the inventory and wires it directly; the
  owner reviews in the diff / UAT. The inventory should still be written down (a table in the plan
  or the typed registry from D-04) so the CLAUDE.md rule has a reference.

### Claude's Discretion
- Exact event-name list and prop keys within D-01/D-04.
- How `page` is derived (explicit literal at call site vs from the route).
- Plan split (identity wiring vs inventory waves) and test strategy (per-event unit tests vs a
  registry-level test). Existing `frontend/src/lib/__tests__/analytics.test.ts` is the anchor.
- The post-ship verification query shape against `flawchess-umami-db`.

### Deferred Ideas (OUT OF SCOPE)
None, discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (Requirements: TBD). The CONTEXT decisions are the requirement set.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01/D-04/D-05 | Few verb-level events, typed registry, no renames | §Typed registry design; 9-name vocabulary below |
| D-02/D-03/D-06 | Non-URL tabs only, user-initiated only, skip high-frequency | Inventory "Excluded" list; slider `onValueCommit` pitfall |
| D-07 | Clean break on logout | Tracker keeps the id in a closure variable only; every logout path already does a full navigation (§Identity) |
| D-08 | No browser storage | Deployed tracker never writes storage (§Identity, verified) |
| D-09 | First-pageview gap | Version-dependent: stitched on 3.3.1 (running), NOT stitched on 3.4.0 (what the floating tag now points to). Boot-time identify closes it on both |
| D-10/D-11 | Admins identified, impersonation skipped | Impersonation JWT carries `is_impersonation: true`; guard on that and on `profile.impersonation` |
| D-12/D-13/D-14 | Inventory, panel+popover opens, exclusions | ~48-row inventory with file:line; 4 shared choke points cover ~70 call sites |
| D-15 | Inventory written down | The `FEATURE_EVENTS` const registry doubles as the inventory reference |
</phase_requirements>

## Summary

The deployed tracker is **Umami v3.3.1**. The `Last-Modified` header on `analytics.flawchess.com/script.js` is 2026-08-20 18:27:52, a minute after the v3.3.1 GitHub release (18:26:22). The minified script matches `src/tracker/index.ts@v3.3.1`, which is byte-identical to v3.3.0. `identify(id, data)` stores the id in an **in-memory closure variable** (`identity`) and attaches it as `payload.id` to every later pageview, event and identify in that page load. It survives SPA route changes (pushState is patched, no reload) and is lost on any full reload. The tracker never writes localStorage, sessionStorage or cookies; its only storage access is `getItem("umami.disabled")`. There is no reset API. **D-08 holds with no storage clause needed**, and **D-07 is already met because every logout path does a hard navigation** (`logout` sets `window.location.href = '/'`, and all three `logoutForPromotion` callers set `window.location.href = '/login?tab=register'`).

D-09 depends on the server version. On v3.3.1 the session id is `uuid(websiteId, ip, userAgent, monthlySalt)`. `distinct_id` is **not** part of it, and identify runs `UPDATE session SET distinct_id = …`. So earlier pageviews in the same session are covered: stitching works. **But prod runs `ghcr.io/umami-software/umami:postgresql-latest`, and that tag now resolves to v3.4.0** (same digest as `3.4.0`). v3.4.0 adds `distinctId` to the session hash ("Identified visitors sharing an IP address and user agent now receive separate sessions by distinct ID"). Prod is still on 3.3.1 only because `docker compose up -d` never pulls. After the next manual pull, a pageview sent before identify lands in a separate anonymous session and is never stitched. The design should therefore identify **before the tracker's first pageview**. That is possible on both versions: `main.tsx` already relies on running before the deferred tracker's first pageview (`main.tsx:25-28`), and the user id is the `sub` claim of the stored `auth_token` JWT.

**Blocking fact for the planner:** `UserProfile` (frontend) and `UserProfileResponse` (backend) carry **no `id` field** (`frontend/src/types/users.ts:24-38`, `app/schemas/users.py:51-79`). A "frontend-only" phase cannot read `users.id` from the profile. The only frontend-only source is the JWT `sub` claim: FastAPI-Users writes `{"sub": str(user.id), ...}` for regular and guest tokens, and impersonation tokens carry `sub = target.id` plus `is_impersonation: True`.

**Primary recommendation:** Identify from the JWT `sub` (frontend-only). Do it once at boot in `main.tsx` from `localStorage.auth_token`, right after `installUmamiBeforeSend()`, so the first pageview carries the id on any Umami version. Do it again in the `ProtectedLayout` effect keyed on `[token, accountType]` to cover in-place guest creation and promotion and to attach `{account}`. Skip both when the token's `is_impersonation` claim is true. Keep logout's full reload as the D-07 mechanism, and add a load-bearing comment plus a test. For events, instrument four shared choke points first: `InfoPopover` plus 7 sibling popover shells through one hook, `FilterPanel`/`FlawFilterControl` handlers, `SidebarLayout.handleStripClick` plus `MobileFilterDrawer`, and `EloSelector`/`BoardControls`. They cover about 70 call sites. Wire the remaining ~25 leaf handlers individually through a typed `trackFeature()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Distinct-id derivation (JWT `sub`) | Browser / Client | — | Token already in the client; no backend change needed |
| Identify call + dedupe | Browser / Client (`lib/analytics.ts`) | — | Tracker is client-side; identity lives in tracker memory |
| Session stitching / distinct_id storage | Umami server (`/api/send`) + Umami Postgres | — | Server decides the session id; we can only influence it via payload `id` timing |
| Feature-event vocabulary | Browser / Client (typed registry) | — | D-04: one typed registry in `lib/analytics.ts` |
| Payload scrubbing | Browser / Client (`umamiBeforeSend`) | — | Already runs on identify payloads too |
| Privacy disclosure | Frontend static page | — | One sentence in `Privacy.tsx` |
| Post-ship verification | Umami Postgres (read-only MCP) | App Postgres (separate DB) | Cross-DB join is impossible in SQL (separate databases), so join in Python/pandas |
| Umami version pinning (optional) | Deploy config (`docker-compose.yml`) | — | Outside "frontend-only"; owner decision |

## Identity: verified tracker and server behavior

### Deployed version (evidence)

- `curl -sI https://analytics.flawchess.com/script.js` returns `last-modified: Thu, 20 Aug 2026 18:27:52 GMT`, and `gh api repos/umami-software/umami/releases` lists `v3.3.1 2026-08-20T18:26:22Z`. [VERIFIED: HTTP header + GitHub releases API]
- The deployed script has no `distinct-id` attribute (`grep -c "distinct-id" script.js` returns 0). That attribute is new in v3.4.0. [VERIFIED: deployed script]
- `src/tracker/index.ts` is identical at v3.3.0 and v3.3.1 (`diff` printed nothing). [VERIFIED: gh api]
- `docker-compose.yml:122`: `image: ghcr.io/umami-software/umami:postgresql-latest`. [VERIFIED: docker-compose.yml:122]
- GHCR digests: `postgresql-latest` = `latest` = `3.4.0` = `sha256:85909afc…`, while `3.3.1` = `sha256:fa32d116…`. [VERIFIED: ghcr.io registry API]
- The CI deploy runs `docker compose build --no-cache backend caddy` then `docker compose up -d`, with no `pull` (`.github/workflows/ci.yml:267-268`). The cached 3.3.1 image therefore persists until someone pulls manually. [VERIFIED: ci.yml:267-268]

### (a) Persistence: in memory only, re-sent on every payload, survives SPA routing

From `src/tracker/index.ts@v3.3.1` (matches the deployed minified `G=(t,e)=>{const a="string"==typeof t?t:t.id;return void 0!==a&&(V=a),Q="",q({...C(),data:"object"==typeof t?t:e},"identify")}`):

```ts
// index.ts:282-292
const getPayload = () => ({
  website, screen, language, title: document.title, hostname,
  url: currentUrl, referrer: stripOrigin(currentRef), tag,
  id: identity ? identity : undefined,
});
// index.ts:441-460
const identify = (id: string | (EventData & { id?: string }), data?: EventData): Promise<void> => {
  const nextIdentity = typeof id === 'string' ? id : id.id;
  if (nextIdentity !== undefined) { identity = nextIdentity; }
  cache = '';
  return send({ ...getPayload(), data: typeof id === 'object' ? id : data }, 'identify');
};
// index.ts:643-644
let cache: string | undefined;
let identity: string | undefined;
```
[VERIFIED: github.com/umami-software/umami/blob/v3.3.1/src/tracker/index.ts]

- `identity` is a closure `let`, assigned synchronously before the async send. Every later `getPayload()` (pageviews from patched `pushState`/`replaceState`, `track()` events, identify) carries `id`. The only storage access in the deployed script is `getItem("umami.disabled")`; there is no `setItem`, `sessionStorage` or `document.cookie` (verified by grep of the deployed `script.js`). **D-08: no storage clause required.** [VERIFIED: deployed script.js]
- The `cache` (`x-umami-cache` JWT) is also in memory and is reset to `''` by every identify, which forces the server to recompute the session on that request.
- `window.umami` is only installed when absent: `if (!window.umami) { window.umami = { track, identify, getSession } }` (index.ts:628-635). [VERIFIED]
- This refutes the June note's claim (`.planning/notes/active-engagement-time-tracking.md:65-66`, "persistence is **localStorage-based**"). The supersession pointer should say so.

### (b) Reset: none, and none is needed

- The tracker object exposes only `track`, `identify`, `getSession` (index.ts:631-635). There is no reset. `identify('')` would set `identity = ''`, which `getPayload` treats as falsy and omits, but that relies on an implementation detail and sends a no-op identify request. **Do not use it.**
- Every path that ends a user's in-memory identity already does a full navigation, which wipes the closure:
  - `useAuth.ts:158-168` `logout`: `queryClient.clear(); localStorage.removeItem('auth_token'); … window.location.href = '/';` [VERIFIED: useAuth.ts:158-168]
  - `logoutForPromotion` (`useAuth.ts:170-182`) has "No redirect — caller navigates to register page", and all three callers hard-navigate on the next line: `SignupAskActions.tsx:61-62`, `Welcome.tsx:39-40`, `EvalCoverageBadge.tsx:114-115` each run `logoutForPromotion(); window.location.href = '/login?tab=register';` [VERIFIED: the three files]
  - Ending impersonation goes through `ImpersonationPill.tsx:45` `onClick={logout}`, which reloads. [VERIFIED]
- **Recommendation for D-07:** keep the reloads as the mechanism. Add a comment at `logout`/`logoutForPromotion` saying the hard navigation is load-bearing for analytics identity (Umami v3 has no reset API). Add a unit test that guards the invariant (logout assigns `window.location.href`). Optionally fold the `window.location.href = '/login?tab=register'` into `logoutForPromotion` itself so a future caller can't forget it (all three callers use the identical URL). Planner's call; it is a small, safe refactor.
- Logins without a reload (`login`, `loginWithToken`, `loginAsGuest`, `impersonate`) always start from an empty in-memory identity, because the prior logout reloaded, or they overwrite it with the new id via the effect. With the impersonation guard, the admin's in-memory id stays during impersonation, so events carry the **admin** id, never the target's. D-11 and D-10 are satisfied: admin ids are excluded at analysis time.
- **Do not decode `guest_token` at boot.** `logout` deliberately keeps it (`useAuth.ts:160`, "Keep guest_token so the same guest account is reused"). Only `auth_token` identifies the active session.

### (c) Server: session-level vs per-event, and the version split

`src/app/api/send/route.ts@v3.3.1`:
```ts
// :154-158
const saltRotation = process.env.SALT_ROTATION || 'month';
const sessionSalt = getSalt(saltRotation, createdAt);
const visitSalt = hash(startOfHour(createdAt).toUTCString());
const sessionId = uuid(sourceId, ip, userAgent, sessionSalt);
// :163-177  createSession({... distinctId: id ...})  (insert … on conflict (session_id) do nothing)
// :308-334  identify branch
} else if (type === COLLECTION_TYPE.identify) {
  if (websiteId && id) {
    const newLinkId = hash(sessionId, id);
    if (sessionLinkId !== newLinkId) {
      await Promise.all([
        saveSessionLink({ websiteId, sessionId, distinctId: id, createdAt }),
        updateSession({ websiteId, sessionId, distinctId: id }),
      ]);
```
`updateSession.ts:25-31` runs `update session set distinct_id = {{distinctId}} where website_id = … and session_id = … and coalesce(distinct_id, '') != {{distinctId}}`. [VERIFIED: v3.3.1 source]

`src/app/api/send/route.ts@v3.4.0` diff:
```ts
>     const distinctId = truncateString(id, FIELD_LENGTH.distinctId);
>     // Identified users need a separate deterministic session from anonymous users
>     // who happen to share the same IP address and user agent.
>     const sessionId = uuid(sourceId, ip, userAgent, sessionSalt, distinctId ?? '');
```
[VERIFIED: v3.4.0 source; release notes: "Identified visitors sharing an IP address and user agent now receive separate sessions by distinct ID"]

| | v3.3.1 (running now) | v3.4.0 (`postgresql-latest` today) |
|---|---|---|
| Session key | site + IP + UA + calendar month (no `SALT_ROTATION` set in compose → `'month'`) | same + `distinct_id` |
| Identify mid-load | Updates the **same** session row → earlier pageviews stitched | Payload now carries id → **new** session; earlier pageviews stay in the anonymous session |
| D-09 with profile-timed identify | OK | First pageview of every full load unattributed |
| Shared device / post-logout | Same device-month session; `session.distinct_id` is last-write-wins, so post-logout anonymous traffic is attributed to the previous user | Cleanly separated per user |
| Per-event distinct id in Postgres | None: `website_event` has no `distinct_id` column; relational `saveEvent` ignores it (only the ClickHouse path writes it) | Same |

Consequences:
1. **Identify before the first pageview.** Then D-09 holds on both versions and no re-send or manual pageview is needed. The boot-time identify in `main.tsx` does this. The tracker's first auto-pageview runs in `init()`, which waits for `document.readyState === 'complete'` (index.ts:646-652). `main.tsx` module code runs earlier: the tracker is a classic `defer` script in `<head>` and `main.tsx` is a module script in `<body>`, both executed in document order before DOMContentLoaded. The project already relies on this ordering (`main.tsx:25-27`: "The deferred tracker sends its first pageview only once the document is complete, so registering the hook here always precedes it."). [VERIFIED: index.ts init + main.tsx:25-28; HTML defer/module ordering ASSUMED from spec knowledge]
2. **Pin the Umami image (owner decision, outside frontend-only).** The floating tag changes session semantics silently on the next `docker compose pull`. Recommend pinning to an explicit tag (`ghcr.io/umami-software/umami:3.4.0` after a deliberate upgrade, or `:3.3.1` to freeze what runs). The design above works on both. 3.4.0 enforces D-07 at the data level (shared device and post-logout traffic separated), and acquisition attribution does not depend on stitching anonymous landings because it already lives in the app DB (`users.first_touch_*` via `lib/firstTouch.ts`). Its two new migrations (`25_add_annotation`, `26_add_api_key`) are additive.
3. **For analysis, `session_link` is the authoritative join table.** `session_link(website_id, session_id, distinct_id, created_at)` has PK `(website_id, distinct_id, session_id)` and records every (session, id) pair. `session.distinct_id` is a last-write-wins convenience. On 3.3.1, sessions with more than one linked id are shared-device sessions; flag or exclude them. [VERIFIED: prisma/schema.prisma@v3.3.1:71-80]

### (d) Signatures, payload, scrub hook

- Supported: `identify(id: string, data?)` and `identify(data & { id? })` (index.ts:158-176). **Use the string form.** The object form copies the whole object, including `id`, into session data (`data: typeof id === 'object' ? id : data`). [VERIFIED]
- Wire payload: `POST /api/send` with `{ type: 'identify', payload: { website, screen, language, title, hostname, url, referrer, tag, id, data } }`. The server's zod schema accepts `id: z.string().optional()`, and `distinct_id` is truncated to 50 chars (`FIELD_LENGTH.distinctId: 50`). Stringified int ids fit easily. [VERIFIED: route.ts:32-72, constants.ts:271-285]
- `data-before-send` is called for **every** send type including identify: `send()` resolves `window[beforeSend](type, payload)` before fetch (index.ts:383-395). `scrubUmamiPayload` spreads the payload, so `id` and `data` pass through untouched. Add a test asserting that `id` survives the scrub. [VERIFIED]
- Dev and localhost: `trackingDisabled()` returns true when `domains` excludes the hostname, so identify becomes a no-op in dev (index.ts:376-381, tag `data-domains="flawchess.com"` at `index.html:45`). [VERIFIED]

### Current code to change (verbatim)

`frontend/src/lib/analytics.ts:25-28` [VERIFIED]:
```ts
    umami?: {
      track: (eventName: string, eventData?: Record<string, string>) => void;
      identify: (sessionData: Record<string, string>) => void;
    };
```
`frontend/src/lib/analytics.ts:97,105-107` [VERIFIED]:
```ts
export type UmamiAccountType = 'guest' | 'registered';
export function identifyAccountType(accountType: UmamiAccountType): void {
  window.umami?.identify({ account: accountType });
}
```
`frontend/src/App.tsx:661-664,706-709` [VERIFIED]:
```ts
function umamiAccountTypeOf(profile: UserProfile | undefined): UmamiAccountType | null {
  if (profile == null || profile.impersonation != null) return null;
  return profile.is_guest ? 'guest' : 'registered';
}
  const umamiAccountType = umamiAccountTypeOf(profile);
  useEffect(() => {
    if (umamiAccountType !== null) identifyAccountType(umamiAccountType);
  }, [umamiAccountType]);
```
JWT claims. FastAPI-Users `jwt.py:66`: `data = {"sub": str(user.id), "aud": self.token_audience}`. Impersonation, `app/users.py:236-242`: `"sub": str(target.id), "aud": self.token_audience, "act_as": target.id, "admin_id": admin.id, "is_impersonation": True,`. Guest tokens use the plain `JWTStrategy` (`app/users.py:209`). [VERIFIED]

## Standard Stack

No new packages. Everything is in-repo or the already-deployed tracker.

| Component | Version | Purpose | Note |
|-----------|---------|---------|------|
| Umami tracker (self-hosted) | 3.3.1 deployed; 3.4.0 on next pull | pageviews, `track`, `identify` | [VERIFIED] |
| radix-ui | ^1.4.3 (package.json:39) | Tabs/Popover/Slider/ToggleGroup handlers | Slider exposes `onValueCommit` [CITED: radix-ui.com/primitives/docs/components/slider] |
| vitest | ^5.0.0 (package.json:79) | unit tests | config `vite.config.ts:90-94`, setup `src/vitest.setup.ts` |
| JWT payload decode | none (hand-written, ~10 lines) | read `sub` / `is_impersonation` | base64url-decode the middle segment; non-verifying, analytics only. Pattern precedent: `lib/push.ts:52-69` uses `window.atob` |

**Don't add `jwt-decode`.** A 10-line base64url decode with try/catch is enough for reading two claims, and no new dependency means no legitimacy audit. This is not "hand-rolling crypto": nothing is verified, the value is only used as an analytics label.

## Package Legitimacy Audit

No external packages are installed by this phase.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 page load
    │
    ├─► <head> defer script.js (Umami 3.3.1/3.4.0) ── installs window.umami {track, identify}
    │                                                   identity=undefined (memory)
    ├─► main.tsx (module, runs before readyState=complete)
    │     installUmamiBeforeSend()          ── window.umamiBeforeSend = scrubUmamiPayload
    │     bootIdentify(): token = localStorage.auth_token
    │        └─ distinctIdFromToken(token) ─┬─ null (no token / impersonation / malformed) → skip
    │                                       └─ "123" → identifyUser("123")  → identity="123"
    │
    ├─► readyState=complete → tracker init → first pageview {.., id:"123"}
    │
    ├─► React: ProtectedLayout effect [token, accountType]
    │     profile resolves → identifyUser(id, account)   (dedupe: same id+account → no-op)
    │     in-place transitions (guest create, promotion, impersonate) re-run the effect
    │
    ├─► user interaction ─► component handler ─► trackFeature(name, {target, value})
    │                                              └─ adds page=currentPage() ─► trackEvent
    │                                                    └─► umami.track(name, data)
    │
    └─► every send ─► umamiBeforeSend(type, payload) ─► POST analytics.flawchess.com/api/send
                                                          ├─ 3.3.1: session=uuid(site,ip,ua,month); identify → UPDATE session.distinct_id + session_link
                                                          └─ 3.4.0: session=uuid(site,ip,ua,month,distinct_id)
 logout / logoutForPromotion ─► hard navigation ─► tracker closure wiped (D-07)
```

### Recommended file touch map

```
frontend/src/lib/analytics.ts            # identifyUser, distinctIdFromToken, FEATURE_EVENTS registry, trackFeature, currentPage, useTrackedOpen
frontend/src/main.tsx                    # boot identify after installUmamiBeforeSend()
frontend/src/App.tsx                     # ProtectedLayout effect; More drawer + bottom-bar More; settings open
frontend/src/hooks/useAuth.ts            # load-bearing-reload comments (+ optional fold of the hard nav)
frontend/src/components/ui/info-popover.tsx + 7 popover shells   # useTrackedOpen
frontend/src/components/filters/{FilterPanel,FlawFilterControl,FilterActions,MobileFilterDrawer,OpponentStrengthFilter}.tsx
frontend/src/components/layout/SidebarLayout.tsx
frontend/src/components/analysis/{AnalysisTabs,EloSelector,TemperatureSelector,AnalysisTagsPanel,EngineLines,FlawChessEngineLines,VariationTree,PasteModal}.tsx
frontend/src/components/board/BoardControls.tsx
frontend/src/pages/Analysis.tsx          # engine-toggle wrappers
… leaf handlers per inventory
frontend/src/pages/Privacy.tsx:58
frontend/CLAUDE.md                       # Umami section rule + DB-known reword
.planning/notes/active-engagement-time-tracking.md   # supersession pointer (+ correct the localStorage claim)
```

### Pattern 1: Identity helpers (recommended shape)

```ts
// lib/analytics.ts — sketch, names are the planner's call
declare global {
  interface Window {
    umami?: {
      track: (eventName: string, eventData?: Record<string, string>) => void;
      identify: (distinctId: string, data?: Record<string, string>) => void;
    };
    umamiBeforeSend?: (type: string, payload: UmamiPayload) => UmamiPayload;
  }
}

let lastIdentifyKey: string | null = null; // per page load; reload resets it with the tracker

/** JWT `sub` = users.id (FastAPI-Users). Null for impersonation tokens (D-11) or anything malformed. */
export function distinctIdFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const json = JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '=')));
    if (json.is_impersonation === true) return null;
    return typeof json.sub === 'string' && /^\d+$/.test(json.sub) ? json.sub : null;
  } catch { return null; }
}

export function identifyUser(distinctId: string, accountType?: UmamiAccountType): void {
  const key = `${distinctId}|${accountType ?? ''}`;
  if (key === lastIdentifyKey || !window.umami) return;
  lastIdentifyKey = key;
  window.umami.identify(distinctId, accountType ? { account: accountType } : undefined);
}
```
- Keep the tracker-absent guard *before* recording the dedupe key, so a late-loading tracker is not deduped away. Also keep `identifyAccountType` removable: knip fails CI on dead exports.
- ProtectedLayout effect: `const id = distinctIdFromToken(token); if (id !== null && umamiAccountType !== null) identifyUser(id, umamiAccountType);` deps `[token, umamiAccountType]`. `umamiAccountTypeOf` already returns null under impersonation, so both guards apply.
- Boot (`main.tsx`, after `installUmamiBeforeSend()`): `const id = distinctIdFromToken(localStorage.getItem('auth_token')); if (id) identifyUser(id);`. Wrap in try/catch for the `localStorage` access, matching `useAuth.ts:44`.

### Pattern 2: Typed registry plus `trackFeature`

Runtime-inspectable const arrays give an inventory reference (D-15) and let tests iterate the vocabulary. Types are derived from them (D-04).

```ts
export const PAGE_IDS = ['home', 'library', 'openings', 'endgames', 'analysis', 'train', 'bots', 'welcome', 'other'] as const;
export type PageId = (typeof PAGE_IDS)[number];
const PAGE_BY_SEGMENT: Readonly<Record<string, PageId>> = {
  '': 'home', library: 'library', openings: 'openings', endgames: 'endgames',
  analysis: 'analysis', train: 'train', bots: 'bots', welcome: 'welcome',
};
export function currentPage(pathname: string = window.location.pathname): PageId {
  return PAGE_BY_SEGMENT[pathname.split('/')[1] ?? ''] ?? 'other';
}

type OnOff = 'on' | 'off';
// One entry per event name; each is a discriminated union over `target`.
export interface FeatureEventMap {
  'tab-switch':    { target: 'moves' | 'eval' | 'human' | 'flawchess' | 'stats' };
  'toggle':        { target: 'engine-stockfish' | 'engine-maia' | 'engine-flawchess' | 'bookmark-chart'; value: OnOff }
                 | { target: 'played-as'; value: 'white' | 'black' }
                 | { target: 'chart-legend'; value: 'elo-timeline' | 'flaw-trend' };
  'option-change': { target: 'engine-elo' | 'bot-elo'; value: `${number}` }   // ladder rung (enumerated constant ladder)
                 | { target: 'play-style'; value: 'human' | 'light' | 'deep' | 'custom' }
                 | { target: 'bot-tc'; value: string /* TIME_CONTROL_PRESETS label union, type it from the const */ }
                 | { target: 'bot-color'; value: 'white' | 'black' | 'random' };
  'filter-change': { target: 'time-control'; value: TimeControl }
                 | { target: 'platform'; value: Platform | 'pasted' }
                 | { target: 'played-as'; value: FilterState['playedAs'] }
                 | { target: 'piece-filter'; value: MatchSide }
                 | { target: 'rated'; value: 'all' | 'rated' | 'casual' }
                 | { target: 'opponent-type'; value: OpponentType }
                 | { target: 'opponent-strength'; value: OpponentStrengthPreset | 'custom' }
                 | { target: 'recency'; value: RecencyPreset | 'all' | 'custom' }
                 | { target: 'endgame-type'; value: EndgameClass }
                 | { target: 'severity'; value: 'blunder' | 'mistake' }
                 | { target: 'flaw-tag'; value: FlawTag }
                 | { target: 'tactic-family'; value: TacticFamily }
                 | { target: 'tactic-orientation'; value: 'either' | 'missed' | 'allowed' }
                 | { target: 'tactic-depth' | 'has-gem' | 'has-great' }
                 | { target: 'reset' | 'apply' };
  'board-tool':    { target: 'flip' | 'paste-open' | 'paste-load' | 'line-expand' | 'line-delete' | 'elo-reset' };
  'popover-open':  { target: string };  // component testId, developer constant; see pitfall 5
  'panel-open':    { target: 'filters' | 'tags' | 'bookmarks' | 'bookmark-suggestions' | 'settings' | 'more-drawer'
                       | 'train-schedule' | 'tc-section' | 'show-more' };
  'action':        { target: 'chip-cycle' | 'bookmark-load' | 'train-solution' | 'train-explore-exit'
                       | 'reminder-banner-dismiss' | 'persona-open' | 'custom-setup-open' | 'bot-resume'
                       | 'bot-discard' | 'bot-rematch' | 'bot-new-game' | 'bot-analyze' | 'bot-draw-decline'
                       | 'bot-return-live' };
  'nav-click':     { target: 'library' | 'train' | 'bots' | 'openings' | 'endgames' | 'analysis'; source: 'more-drawer' };
}
export type FeatureEventName = keyof FeatureEventMap;

export function trackFeature<E extends FeatureEventName>(name: E, props: FeatureEventMap[E]): void {
  trackEvent(name, { page: currentPage(), ...props } as Record<string, string>);
}
```
- Import the value unions from their existing sources: `TimeControl`/`MatchSide` from `types/api.ts:33,35`; `FilterState['playedAs']`, `PastedFilter`, `OpponentType`, `RecencyPreset` from `FilterPanel.tsx`/types; `FlawTag`, `TacticFamily`, `EndgameClass`; the bot TC label union from `lib/botTimeControlPresets.ts`. Do not re-declare them, so a new enum member flows through automatically. The exact unions above are a sketch: confirm each name against its source file before coding. Only `FilterState` (`FilterPanel.tsx:41-84`), `PastedFilter` (`:85`), and the ToggleGroupItem values `either/white/black` (`:400-402`), `human/bot/both` (`:599-601`) and `all/rated/casual` (`:622-624`) were read this session.
- 9 new names, within D-01's 6-10. `settings-change`/`settings-reset` stay as-is (D-05). `action` is broader than the D-01 examples; it collects discrete one-shot buttons so the event list doesn't sprawl.
- `page` is derived from the route inside `trackFeature`. Recommend this over call-site literals: shared components (InfoPopover, FilterPanel, EloSelector, BoardControls) render on several pages and could not pass a correct literal without threading props. `website_event.url_path` holds the full path anyway; `page` exists for the Umami UI property breakdown.

### Pattern 3: one hook for all hover/tap popovers (D-13)

Eight popover shells duplicate the same `const [open, setOpen] = React.useState(false)` plus a 100 ms hover timer: `info-popover.tsx:23` (49 call sites), `MetricStatPopover.tsx:45` (11 users), `AchievableScorePopover.tsx:72`, `FlawBulletPopover.tsx:165`, `BulletConfidencePopover.tsx:43`, `ScoreConfidencePopover.tsx:40`, `PercentileChip.tsx:338`, `PersonaEloDisclosurePopover.tsx:47`. Replace each `useState(false)` with `useTrackedOpen(testId)`. It returns `[open, setOpen]` and fires `trackFeature('popover-open', { target })` on the first false→true transition per mounted instance (a ref guard). That caps hover-flicker noise and still answers "was it discovered". It covers both open paths (hover timer and Radix `onOpenChange` tap) because both go through `setOpen`. `PersonaEloDisclosurePopover` has a hard-coded testid `"persona-elo-disclosure"` (line 67); pass that.

### Anti-Patterns to Avoid
- **Tracking from `useEffect` on a value** (e.g. `useEffect(() => track(tab), [tab])`) fires on mount and restore, which violates D-03. Track in the handler. The one allowed effect-style site is `MobileFilterDrawer` open, and only on a ref-guarded false→true transition, because parents open it by setting state directly from their trigger buttons.
- **`data-umami-event` on `<Link>`** (existing rule, `frontend/CLAUDE.md` Outbound section): use `trackFeature` in `onClick`.
- **Diffing `FilterPanel.update(partial)`** to infer what changed: instrument each of the ~9 handlers explicitly with typed values instead.
- **Object-form identify** (`identify({ id, account })`): it leaks `id` into `session_data` as a data key. Use the string form.

## Feature-Event Inventory (draft, ~48 rows)

Legend: "Shared" = one instrumentation point covers the listed call sites. All handlers are user-initiated. URL? = does the interaction change the URL (D-02).

### Group 1: Analysis board (page auto: `analysis`, shared components also `bots`/`openings`/`train`)

| # | Interaction | Handler (file:line) | URL? | Event / props |
|---|---|---|---|---|
| 1 | Mobile/mid tab switch | `AnalysisTabs.tsx:797` uncontrolled `<Tabs defaultValue="moves">`: add `onValueChange`. Values `moves`,`eval`,`human`,`flawchess`,`stats` (`:799-826`) | no | `tab-switch {target}` |
| 2 | Stockfish on/off | `AnalysisDesktopCards.tsx:66` `onCheckedChange={setEngineEnabled}`; raw setter `Analysis.tsx:420`, also passed at `:2412` | no | `toggle {target:'engine-stockfish', value}` |
| 3 | Maia on/off | `MaiaHumanPanel.tsx:164` `onCheckedChange={onToggleEnabled}`; from `Analysis.tsx:2370,2457` | no | `toggle {engine-maia}` |
| 4 | FlawChess Engine on/off | `AnalysisTabs.tsx:428`; setter `Analysis.tsx:425`, passed `:2224` | no | `toggle {engine-flawchess}` |
| 5 | Engine ELO slider (Shared: Analysis + Bots setup `SetupScreen.tsx:249`) | `EloSelector.tsx:105` `onValueChange`: add `onValueCommit` | no | `option-change {target: page==='bots'?'bot-elo':'engine-elo', value: rung}` |
| 6 | ELO reset | `EloSelector.tsx:118` `onClick={onReset}` | no | `board-tool {elo-reset}` |
| 7 | Play-style (temperature) slider | `TemperatureSelector.tsx:103`: use `onValueCommit` | no | `option-change {play-style}` |
| 8 | Flip board (Shared: Analysis `:2166,:2643`, Openings `:666`, Bots `:443`, TrainReveal `:509`, OpeningsMobileBoardPanel `:111`, AnalysisBoardStage `:168`) | `BoardControls.tsx:215` `onClick={onFlip}` | no | `board-tool {flip}` |
| 8b | Flip in bot mobile bar | `BotGameMobileBar.tsx:130` | no | `board-tool {flip}` |
| 9 | Open PGN/FEN paste (Shared desktop+mobile) | `AnalysisTabs.tsx:520` `onClick={onOpenPasteModal}` | no | `board-tool {paste-open}` |
| 10 | Paste "load" (non-saving) | `PasteModal.tsx:250` `btn-paste-load` | no | `board-tool {paste-load}`. Skip `btn-paste-analyze` (`:240`), which saves a game (DB-known) |
| 11 | Expand engine line | `EngineLines.tsx:369`, `FlawChessEngineLines.tsx:420` `setExpanded` | no | `board-tool {line-expand}` (fire on expand only) |
| 12 | Delete variation line | `VariationTree.tsx:684,1025` | no | `board-tool {line-delete}` |
| 13 | Tag chip cycle | `AnalysisTagsPanel.tsx:274` `handleActivate` | no | `action {chip-cycle}` |
| 14 | Settings sheet open (Shared: `btn-analysis-settings` `App.tsx:452`, `btn-bots-settings` `BotGameMobileLayout.tsx:112`) | `SettingsSheetButton.tsx:87` (DrawerTrigger: track in its `onOpenChange(true)`) | no | `panel-open {settings}` |

### Group 2: Openings / Endgames / Library / Stats

| # | Interaction | Handler (file:line) | URL? | Event / props |
|---|---|---|---|---|
| 15 | Desktop sidebar panel open (Shared: Openings `OpeningsDesktopSidebar.tsx:167`, Endgames `:917`, GlobalStats `:259`, Library Games `:441`, Flaws `:463`). Ids `filters`/`bookmarks`/`tags` | `SidebarLayout.tsx:91-93` `handleStripClick`: fire when `activePanel !== panelId` | no | `panel-open {target: panelId}` |
| 16 | Mobile drawer open (Shared: 8 call sites, `Endgames.tsx:1010`, `FlawsTab.tsx:500,524`, `GlobalStats.tsx:317`, `OpeningsMobileDrawers.tsx:60,85`, `GamesTab.tsx:478,501`) | `MobileFilterDrawer.tsx`: add typed `panel: 'filters'\|'tags'\|'bookmarks'` prop; ref-guarded open transition | no | `panel-open {target: panel}` |
| 17 | Played-as (Library) | `FilterPanel.tsx:391` | no | `filter-change {played-as, value}` |
| 18 | Recency preset / custom | `FilterPanel.tsx:423`, custom commit `:510` | no | `filter-change {recency}` |
| 19 | Time-control chip | `FilterPanel.tsx:526` `toggleTimeControl(tc)` | no | `filter-change {time-control, value: tc}` |
| 20 | Platform chip | `FilterPanel.tsx:551` `togglePlatform(p)` | no | `filter-change {platform}` |
| 21 | Pasted chip | `FilterPanel.tsx:562` `togglePasted` | no | `filter-change {platform, value:'pasted'}` |
| 22 | Opponent strength | `OpponentStrengthFilter.tsx:45` preset path (value=preset); `:38` slider path: commit only, value `custom` | no | `filter-change {opponent-strength}` |
| 23 | Opponent type | `FilterPanel.tsx:590` | no | `filter-change {opponent-type}` |
| 24 | Rated | `FilterPanel.tsx:613` | no | `filter-change {rated}` |
| 25 | Reset / Apply (Shared footer) | `FilterActions.tsx:43` (reset), `:53` (apply); `FilterPanel.tsx:653` lone reset; `LibraryFilterPanel.tsx:80` | no | `filter-change {reset}` / `{apply}` |
| 26 | Piece filter (Openings) | `OpeningsFilterFields.tsx:67` | no | `filter-change {piece-filter, value: matchSide}` |
| 27 | Openings color toggle | `Openings.tsx:645` (desktop), `:797` (mobile) | no | `toggle {played-as, value}` |
| 28 | Endgame type select | `Endgames.tsx:798` | no | `filter-change {endgame-type}` |
| 29 | Severity / flaw-tag / tactic-family chips | `FlawFilterControl.tsx` `handleSeverityToggle`/`handleTagToggle`/`handleTacticFamilyToggle` (~`:498-520`) | no | `filter-change {severity\|flaw-tag\|tactic-family, value: toggled item}` |
| 30 | Tactic orientation | `FlawFilterControl.tsx:596` | no | `filter-change {tactic-orientation}` |
| 31 | Tactic depth / gem / great | `FlawFilterControl` props `onTacticDepthChange`, `onHasGemToggle`, `onHasGreatToggle` | no | `filter-change {tactic-depth\|has-gem\|has-great}` |
| 32 | Bookmark suggestions open | `Openings.tsx:520,637,832` `setSuggestionsOpen(true)` | no | `panel-open {bookmark-suggestions}` |
| 33 | Bookmark load | `PositionBookmarkCard.tsx:198` | no | `action {bookmark-load}` |
| 34 | Bookmark chart toggle (localStorage only, `Openings.tsx:7-8`) | `PositionBookmarkCard.tsx:186` | no (navigates to stats only if not already there, `Openings.tsx:258`) | `toggle {bookmark-chart}` |
| 35 | Per-TC accordion expand | `EndgameTypeBreakdownSection.tsx:116`, `EndgameMetricsByTcSection.tsx:100`, `EndgameTimePressureSection.tsx:91` `onValueChange={setExpandedTcs}`: fire when an item is added | no | `panel-open {tc-section}` |
| 36 | Chart legend toggle | `EndgameEloTimelineSection.tsx:425`, `FlawTrendChart.tsx:177` | no | `toggle {chart-legend, value}` |
| 37 | "Show more" expanders | `OpeningInsightsBlock.tsx:268`, `OpeningStatsSection.tsx:63`, `TacticMotifGroup.tsx:93`, `MoveStats.tsx:340` | no | `panel-open {show-more}` (on expand only) |
| 38 | Game-card chip cycle | `LibraryGameCard.tsx:599` `handleActivate(ref)` | no | `action {chip-cycle}` |

### Group 3: Train + Bots

| # | Interaction | Handler (file:line) | URL? | Event / props |
|---|---|---|---|---|
| 39 | Show solution | `TrainSolveScreen.tsx:523` | no | `action {train-solution}` |
| 40 | Exit exploration | `TrainReveal.tsx:457` | no | `action {train-explore-exit}` |
| 41 | Train schedule card expand | `TrainScheduleSettings.tsx:275` (expand only) | no | `panel-open {train-schedule}` |
| 42 | Reminder resurface dismiss | `TrainReminderResurfaceBanner.tsx:108` | no | `action {reminder-banner-dismiss}` |
| 43 | Bot TC preset | `SetupScreen.tsx:195`, `PersonaDetailSurface.tsx:108` | no | `option-change {bot-tc}` |
| 44 | Bot color | `SetupScreen.tsx:269`, `PersonaDetailSurface.tsx:252` | no | `option-change {bot-color}` |
| 45 | Bot play style preset | `PlayStyleControl.tsx:86` | no | `option-change {play-style}` |
| 46 | Persona open / custom setup | `PersonaCard.tsx:116`, `PersonaGrid.tsx:168` | no | `action {persona-open\|custom-setup-open}` |
| 47 | Resume / discard / rematch / new game / analyze / draw-decline / return-live | `ResumeGate.tsx:136,165`; `GameResultDialog.tsx:194,185,169`; `BotDrawOfferActions.tsx:42`; `MoveListPanel.tsx:96` | no (analyze navigates, but the source button is UI-only) | `action {bot-…}` |

Bot setup note: finished bot games already store `nominal_elo`, `play_style_blend`, `tc_preset` (`app/models/bot_game_settings.py:31-35`) and the persona. Setup events overlap the DB for finished games. D-12 keeps them because abandoned setups are invisible to the DB. Analysis should not double-count them as "games".

### Group 4: Info popovers + nav

| # | Interaction | Handler (file:line) | URL? | Event / props |
|---|---|---|---|---|
| 48 | All explanation popovers (Shared: 49 `InfoPopover` sites + 7 shells, ~70 instances) | `useTrackedOpen` in the 8 shells (Pattern 3) | no | `popover-open {target: testId}` |
| 49 | Mobile More drawer open | `App.tsx:553` button → `App.tsx:826` `setMoreOpen(true)` | no | `panel-open {more-drawer}` |
| 50 | More-drawer nav items | `App.tsx:600` `<Link>` inside `DrawerClose`: add `onClick` (keep the locked-item `preventDefault` branch; fire only when not locked) | yes, but the *source* is UI-only | `nav-click {target, source:'more-drawer'}` |
| 51 | More-drawer Settings | `App.tsx:578` `openSettings` | no | `panel-open {settings}` |

Exclude `drawer-nav-admin`/`activity` (D-14): the target union has no admin/activity members, so the call is guarded by type.

### Excluded (with reason)
- URL-routed tabs: `Openings.tsx:575,708`, `Endgames.tsx:889,963`, `LibraryPage.tsx:58,100` (D-02).
- Move stepping / FF / line stepper (`BoardControls` back/forward/reset, `TrainLineStepper.tsx:259-307`), explorer row click (`MoveExplorer.tsx:329`), eval chart click/scrub (`EvalChart.tsx:1001`), Maia quality-bar hover/play (D-06).
- DB-known: bookmark save/delete (`Openings.tsx:865`, `PositionBookmarkCard.tsx:209`), suggestions save (`SuggestionsModal.tsx:216`), insights generate/retry (`EndgameInsightsBubble.tsx:90,123`, `llm_log`), train guess (`drill_solves.guess`), train session start (`TrainStartScreen.tsx:389`), schedule/reminder settings (`train_settings`, push_subscriptions), import, paste-analyze (stores game), bot result/resign/draw-accept.
- Auth/admin/activity flows (D-14). Pagination (`Pagination.tsx`) is optional and low value; skip unless the owner wants it.
- "Analyze" deep links (Openings `onAnalyzePosition`, FlawCard `btn-flaw-analyze`, Train `btn-train-analyze`): the `/analysis` pageview's `referrer_path` already records the source. Optional.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session stitching / re-sending pageviews | Manual `umami.track()` pageview replays after identify | Identify at boot before the first auto-pageview | Replays double-count pageviews; boot identify is version-proof |
| Tracker reset | `identify('')` hack, deleting `window.umami`, re-injecting the script | Existing hard navigation on logout | No public reset API; reload is already there |
| Debounced slider tracking | setTimeout debouncers | Radix `onValueCommit` | Fires once at interaction end |
| Per-popover tracking code | 8 copies of tracking logic | `useTrackedOpen(testId)` | One tested hook |
| Event vocabulary docs | Separate markdown inventory | The `FeatureEventMap` / const arrays in `lib/analytics.ts` | The CLAUDE.md rule points to one source of truth (D-15) |

## Runtime State Inventory

Not a rename phase, but runtime state matters here:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Umami DB `session.distinct_id` 0/1,941 (baseline); `session_link`, `session_data(account)` | None to migrate. Verify after ship |
| Live service config | Umami container on cached 3.3.1 while `postgresql-latest` = 3.4.0 | Owner decision: pin tag (see Open Q1) |
| OS-registered state | None, verified: no cron/systemd touches Umami | none |
| Secrets/env vars | None. `SALT_ROTATION` unset → `'month'` (route.ts:154) | none |
| Build artifacts | Cloudflare caches `script.js` (`cache-control: public, max-age=86400`, `cf-cache-status: HIT`) | After any Umami upgrade, the tracker changes within ≤1 day; no action for this phase |

## Common Pitfalls

### Pitfall 1: Umami upgrade silently changes session semantics
**What goes wrong:** the next `docker compose pull` moves prod 3.3.1 → 3.4.0. Profile-timed identify then leaves the first pageview of each load in an anonymous session.
**How to avoid:** boot-time identify (Pattern 1), and pin the image tag.
**Warning signs:** after an upgrade, sessions with `distinct_id IS NULL` that hold exactly one pageview on a protected route.

### Pitfall 2: Slider `onValueChange` spams events
**What goes wrong:** Radix Slider `onValueChange` fires on every step while dragging (EloSelector, TemperatureSelector, PresetRangeFilter, OpponentStrengthFilter slider). That would emit dozens of events per drag.
**How to avoid:** track only in `onValueCommit`, which the repo's `Slider` passes through via `...props` (`components/ui/slider.tsx:22`). Nothing uses it yet.

### Pitfall 3: Radix single ToggleGroup emits `''` on re-tap
**What goes wrong:** re-tapping the active item yields `''`. SettingsPanel already guards this (`SettingsPanel.tsx:35-37`: "Radix single-select emits '' when the active item is re-tapped: keep the current value and fire nothing"). Without the guard you get bogus `value:''` events.
**How to avoid:** fire after the existing `if (!v) return` / `if (v)` guards (FilterPanel `:391-393`, OpeningsFilterFields `:68`), and only when the value actually changed.

### Pitfall 4: Partial `vi.mock('@/lib/analytics')` factories
**What goes wrong:** `SettingsPanel.test.tsx:14`, `EngineReadyGate.test.tsx:31` and `ImportAskActions.test.tsx:14` mock the module with only `trackEvent`. If a component under those tests starts calling `trackFeature`, or renders an instrumented `InfoPopover`, the import resolves to `undefined` and the test throws.
**How to avoid:** switch those mocks to `vi.mock('@/lib/analytics', async (orig) => ({ ...(await orig()), trackEvent: mock }))`, or keep `trackFeature` calling `trackEvent` so asserting on the `trackEvent` mock still works.

### Pitfall 5: `popover-open` target is a testId string, not a typed literal
**What goes wrong:** D-04 wants enumerated values. The 49 InfoPopover testIds are developer constants, some composed from enums (`time-pressure-card-${card.tc}-…`, `opening-insights-section-${section.key}-info`, `-mobile` suffixes), not user data. Typing all 49 as a literal union is churn.
**How to avoid:** accept `target: string` for `popover-open` only. Add a registry test that asserts the shape `/^[a-z0-9-]+$/`, and a short review rule ("testId must never interpolate user data"). Optionally strip `-mobile`/`-sidebar` suffixes in `useTrackedOpen` so desktop and mobile aggregate into one row.

### Pitfall 6: Tests are excluded from `tsc -b`
**What goes wrong:** `tsconfig.app.json:43` has `"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx"]`, so `@ts-expect-error` registry assertions in tests are not gated (see the precedent note in `selectBotMove.test.ts:304-306`). The type gate is the call sites in `src`, checked by `npm run build`.
**How to avoid:** run `npm run build` in the gate. Runtime registry tests iterate the const arrays.

### Pitfall 7: Identify before the tracker exists
**What goes wrong:** if `window.umami` is missing (ad blocker, failed fetch), identify no-ops. Recording the dedupe key anyway would suppress a later retry.
**How to avoid:** check `window.umami` before setting `lastIdentifyKey` (Pattern 1).

### Pitfall 8: Cross-database join in verification
**What goes wrong:** the Umami DB (`DATABASE_URL …/umami`, `docker-compose.yml:124`) and the app DB are separate Postgres databases. `JOIN users` is impossible without dblink or fdw.
**How to avoid:** pull distinct ids from `flawchess-umami-db` and users from `flawchess-prod-db` separately, and join in Python. Subagents cannot call the MCPs; the orchestrator runs them.

### Pitfall 9: Account deletion now has an Umami tail
**What goes wrong:** `Privacy.tsx` "Your rights" promises deleting "any associated data". Umami sessions keyed by `distinct_id` are now associated data.
**How to avoid:** out of scope to automate. Flag for a runbook note: Umami has `sessionDeletionEnabled: true` (`/api/config`), so per-session delete is possible in the UI. See Open Question 3.

## Code Examples

### Boot identify (main.tsx, after line 28)
```ts
// Identify before the deferred tracker's first pageview (it waits for readyState
// 'complete'), so the landing pageview carries the id on Umami 3.4+ too, where the
// distinct id is part of the session hash. Memory-only: reload or logout wipes it.
installUmamiBeforeSend();
identifyFromStoredToken(); // reads localStorage 'auth_token' only, never 'guest_token'
```

### Load-bearing reload comment (useAuth.ts logout)
```ts
// The hard navigation is ALSO the analytics identity reset: Umami v3 keeps the
// identify() id in tracker memory with no reset API, so a reload is what stops
// post-logout traffic carrying this user's id (Phase 229 D-07). Keep it.
window.location.href = '/';
```

### Privacy sentence (Privacy.tsx:58)
Current, verbatim [VERIFIED: Privacy.tsx:58]: "We use self-hosted, privacy-friendly, cookie-free analytics (Umami) to understand which pages are visited, and whether by a guest or a registered account. No personal data is collected or shared."
Proposed: "We use self-hosted, cookie-free analytics (Umami) to understand which pages and features are used. For logged-in and guest accounts this usage data is linked to your account ID, stays on our own servers, and is never shared with third parties."
"Cookie-free" stays true: the tracker writes no cookies or storage, and `credentials` defaults to `omit` (`data-fetch-credentials`, script default `"omit"`). No storage clause is needed (D-08).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Umami ≤3.3.x: session = site+IP+UA+month, identify updates that row | 3.4.0: distinct id is part of the session hash | v3.4.0, 2026-09-17 | Identify must precede the first pageview to cover it |
| `identify` only via JS | v3.4.0 also accepts a `data-distinct-id` script attribute | v3.4.0 | Not usable here: the id is dynamic and the tag is static HTML |
| June note: "localStorage-based persistence" | v3 tracker: memory-only | — | Correct the note when adding the pointer |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Classic `defer` script in `<head>` executes before the `type="module"` `main.tsx`, both before `readyState==='complete'` | Identity (c), Pattern 1 | Boot identify could run before `window.umami` exists → no-op; the effect still identifies later (degrades to the D-09 gap on 3.4.0 only). Verify in UAT via devtools: the first `/api/send` pageview payload carries `id` |
| A2 | Radix `onValueCommit` fires once at drag end | Pitfall 2 | Event volume; check in UAT |
| A3 | Reading `auth_token` from localStorage to derive an analytics id raises no ePrivacy Art. 5(3) issue beyond the existing auth use (no new storage is written) | Primary recommendation | Legal nuance. If the owner disagrees, use Alternative A below (backend `id` on the profile) |
| A4 | Exact value-union type names (`OpponentStrengthPreset`, `RecencyPreset`, `EndgameClass`, `FlawTag`, `TacticFamily`, bot TC label type) | Pattern 2 | Compile errors at the call site; resolve by reading each source file |
| A5 | Owner is fine with `popover-open` carrying a testId string | Pitfall 5 | Rework to a literal union |

**Alternative A (if JWT parsing is rejected):** add `id: int` to `UserProfileResponse` (`app/schemas/users.py:51`, both constructors `app/routers/users.py:98,131`) and `id: number` to `UserProfile` (`types/users.ts:24`), then identify from the profile in the effect only. Cost: a small backend change plus backend test updates (`tests/test_users_router.py` and others reference the profile). It reintroduces the first-pageview gap on Umami ≥3.4.0 (fine on 3.3.1).

## Open Questions

1. **Pin the Umami image?** Prod runs 3.3.1 from a floating tag that now means 3.4.0.
   - Recommendation: pin explicitly in `docker-compose.yml`, preferably `3.4.0` after a deliberate pull, because per-user sessions enforce D-07 at the data level. This is outside "frontend-only", so the owner decides. The phase design works either way.
2. **JWT `sub` vs a backend profile `id`.** Recommendation: JWT `sub` (frontend-only, version-proof first pageview). Alternative A if the owner prefers not to parse tokens.
3. **Account-deletion promise.** Should the runbook gain "delete Umami sessions for `distinct_id = <id>`"? It is flagged only, not in the locked scope.
4. **Fold the hard navigation into `logoutForPromotion`?** It is optional hardening of D-07; all three callers already use the same URL.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | frontend build/tests | ✓ | v24.19.0 | — |
| npm | frontend | ✓ | 11.17.0 | — |
| Deployed Umami | identify/events | ✓ | 3.3.1 (heartbeat `{"ok":true}`) | — |
| `flawchess-umami-db` MCP | post-ship verification | orchestrator only | — | Subagents cannot call it |
| Local Umami | dev testing | ✗ (dev tracking disabled by `data-domains`) | — | Unit tests mock `window.umami`; real verification is post-deploy |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest ^5.0.0 (+ @testing-library/react, jsdom per-file `// @vitest-environment jsdom`) |
| Config file | `frontend/vite.config.ts:90-94` (`setupFiles: ['src/vitest.setup.ts']`) |
| Quick run command | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Decision → Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-08/D-11 | `distinctIdFromToken`: sub for normal/guest tokens; null for `is_impersonation`, malformed, non-numeric, null | unit | `npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ extend |
| D-08 | `identifyUser` calls `identify('123', {account:'guest'})` (string form), dedupes the same key, retries when the tracker was absent | unit | same | ✅ extend (replace `identifies only the coarse account type` test at `:53-58`) |
| D-09 | Boot identify reads `auth_token` only (not `guest_token`) | unit | same | ✅ extend |
| D-04 | `trackFeature` adds `page` from pathname (`history.pushState('/analysis')` → `page:'analysis'`); `currentPage` table incl. `'/'`→home, unknown→other | unit | same | ✅ extend |
| D-04 | Registry: every event name kebab-case and ≤50 chars (`FIELD_LENGTH.eventName`), every literal target `/^[a-z0-9-]+$/` | unit | same | ✅ extend |
| Scrub | `scrubUmamiPayload('identify', {id:'5', data:{account:'guest'}})` passes id/data through | unit | same | ✅ extend |
| D-13 | `useTrackedOpen`: one event on first open, none on mount, none on re-open in the same mount | unit | `npx vitest run src/components/ui/__tests__/info-popover.test.tsx` | ❌ Wave 0 |
| D-13 | SidebarLayout fires `panel-open` on open, not on close | unit | `npx vitest run src/components/layout/__tests__/SidebarLayout.test.tsx` | ❌ Wave 0 |
| D-03 | FilterPanel: clicking a TC chip fires one `filter-change {time-control}`; rendering fires nothing; ToggleGroup re-tap fires nothing | unit | `npx vitest run src/components/filters/__tests__/FilterPanel.tracking.test.tsx` | ❌ Wave 0 |
| D-02 | AnalysisTabs click fires `tab-switch`; initial render does not | unit | `npx vitest run src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` | ❌ Wave 0 |
| D-07 | `logout` assigns `window.location.href`; the three `logoutForPromotion` callers hard-navigate | unit | `npx vitest run src/hooks/__tests__/useAuth.test.tsx` | ❌ Wave 0 |
| D-06 | Slider tracking only on commit | unit | EloSelector test | ❌ Wave 0 |
| Privacy | `Privacy.tsx` no longer contains "No personal data is collected" | unit/grep | `grep -c "No personal data is collected" frontend/src/pages/Privacy.tsx` → 0 | n/a |
| Post-ship | `session.distinct_id` populated | manual (orchestrator MCP) | SQL below | n/a |

Mutation check (project memory: prove a gap fix by reverting it): for the impersonation guard and the dedupe-before-tracker-check ordering, the plan should revert each fix once and confirm the corresponding test fails.

### Post-ship verification SQL (run by the orchestrator via `flawchess-umami-db`; website `0ca19960-2398-4caf-b321-8039708fa7ef`)
```sql
-- 1. Coverage: sessions with activity since ship that carry a distinct id
WITH active AS (
  SELECT DISTINCT session_id FROM website_event
  WHERE website_id = '0ca19960-2398-4caf-b321-8039708fa7ef'
    AND created_at >= :ship_ts
)
SELECT count(*) AS active_sessions,
       count(s.distinct_id) AS identified_sessions
FROM active a JOIN session s USING (session_id);

-- 2. Identity links written by identify (authoritative, multi-id aware)
SELECT count(*) AS links, count(DISTINCT distinct_id) AS users, count(DISTINCT session_id) AS sessions
FROM session_link
WHERE website_id = '0ca19960-2398-4caf-b321-8039708fa7ef' AND created_at >= :ship_ts;

-- 3. Shared-device sessions (more than one id linked; on 3.3.1 these need care)
SELECT session_id, array_agg(distinct_id) FROM session_link
WHERE website_id = '0ca19960-2398-4caf-b321-8039708fa7ef'
GROUP BY session_id HAVING count(*) > 1;

-- 4. First-pageview gap check (should be ~0 with boot identify): anonymous
--    sessions whose pageviews are on protected routes
SELECT count(*) FROM session s
WHERE s.website_id = '0ca19960-2398-4caf-b321-8039708fa7ef' AND s.distinct_id IS NULL
  AND s.created_at >= :ship_ts
  AND EXISTS (SELECT 1 FROM website_event e WHERE e.session_id = s.session_id
              AND e.event_type = 1 AND e.url_path ~ '^/(library|openings|endgames|train|bots|analysis)');

-- 5. Feature events with props (event_type 2 = customEvent)
SELECT e.event_name, d.data_key, d.string_value, count(*)
FROM website_event e JOIN event_data d ON d.website_event_id = e.event_id
WHERE e.website_id = '0ca19960-2398-4caf-b321-8039708fa7ef'
  AND e.event_type = 2 AND e.created_at >= :ship_ts
GROUP BY 1, 2, 3 ORDER BY 4 DESC;
```
Schema facts: `session.distinct_id varchar(50)`; `session_link(website_id, session_id, distinct_id, created_at)` PK `(website_id, distinct_id, session_id)`; `event_data(website_event_id, data_key, string_value, …)`; `EVENT_TYPE = { pageView: 1, customEvent: 2, linkEvent: 3, pixelEvent: 4, performance: 5 }`. [VERIFIED: prisma/schema.prisma@v3.3.1:39-80,116-185; constants.ts:118-123]. Join to app users happens in Python (Pitfall 8). Exclude admin ids (D-10).

### Sampling Rate
- **Per task commit:** the touched component's test file plus `analytics.test.ts`
- **Per wave merge:** `npm test -- --run` + `npm run build`
- **Phase gate:** full pre-merge gate from root CLAUDE.md (frontend half: lint, build, test, knip). Backend untouched unless Alternative A is chosen.

### Wave 0 Gaps
- [ ] `src/components/ui/__tests__/info-popover.test.tsx` (useTrackedOpen)
- [ ] `src/components/layout/__tests__/SidebarLayout.test.tsx`
- [ ] `src/components/filters/__tests__/FilterPanel.tracking.test.tsx`
- [ ] `src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx`
- [ ] `src/hooks/__tests__/useAuth.test.tsx` (logout hard-nav invariant)
- [ ] Update the partial analytics mocks in the 3 existing tests (Pitfall 4)

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no auth change) | — |
| V3 Session Management | yes (indirectly) | Logout reload remains; analytics id never used for authorization |
| V4 Access Control | yes | Impersonation guard (D-11): never identify as the target |
| V5 Input Validation | yes | Typed registry: enumerated props only, no free text (D-04) |
| V6 Cryptography | no | JWT is *read* without verification for an analytics label only, never trusted for authz |
| V8 Data Protection / Privacy | yes | Pseudonymous id on first-party infra; Privacy sentence updated; no new storage |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII in event props (FEN, usernames, opening names, game ids) | Information disclosure | `FeatureEventMap` literal unions; registry test; popover target shape test |
| Token leak to analytics | Information disclosure | Only `sub` is sent, never the token; existing `?token=`/hash scrubbing unchanged |
| Admin browsing attributed to impersonated user | Repudiation / integrity | `is_impersonation` claim + `profile.impersonation` guard |
| Previous user's id on a shared browser | Information disclosure | Hard navigation on every logout path; 3.4.0 separates sessions server-side |
| Forged `sub` by a user editing localStorage | Tampering | Only affects their own analytics label; no authz impact. Accept |

## Project Constraints (from CLAUDE.md)

- No magic numbers: named constants (e.g. the 50-char event-name limit, dedupe and page tables).
- Never bare `str` for a fixed set: literal unions throughout (D-04 aligns).
- Nesting depth ≤4 (eslint `max-depth`); keep tracking one line in each handler.
- `data-testid` on every interactive element (existing testids are reused as popover targets).
- `data-umami-event` only on `<button>` and outbound `_blank` links; `trackEvent`/`trackFeature` in `onClick` for internal links.
- Knip: remove `identifyAccountType` if unused after the refactor; every new export must have an importer.
- `npm run build` before integrating shared-type changes (lint and test do not type-check).
- Em-dashes sparingly in UI copy (Privacy sentence above uses none).
- Frontend has no Prettier: ESLint only.
- Phase scope: Umami pinning and account-deletion runbook are flagged, not implemented, unless the owner approves.

## Sources

### Primary (HIGH confidence)
- `https://analytics.flawchess.com/script.js` (deployed minified tracker), response headers, `/api/heartbeat`, `/api/config`
- github.com/umami-software/umami @ v3.3.1: `src/tracker/index.ts`, `src/app/api/send/route.ts`, `src/queries/sql/sessions/{createSession,updateSession,saveSessionLink}.ts`, `src/queries/sql/events/saveEvent.ts`, `src/lib/{crypto,detect,constants}.ts`, `prisma/schema.prisma`
- github.com/umami-software/umami @ v3.4.0: `route.ts` diff, tracker diff, release notes, migrations list
- ghcr.io registry manifests for `postgresql-latest`, `latest`, `3.3.1`, `3.4.0`
- In-repo files read this session (paths and lines cited inline)
- `.venv/.../fastapi_users/authentication/strategy/jwt.py:66`

### Secondary (MEDIUM confidence)
- radix-ui.com Slider docs (`onValueCommit` exists; semantics assumed)

### Tertiary (LOW confidence)
- HTML defer/module execution ordering (training knowledge; consistent with the project's own `main.tsx` comment)
- ePrivacy reading of reading `auth_token` for analytics (A3)

## Metadata

**Confidence breakdown:**
- Tracker/server semantics: HIGH, from reading the deployed script and the version-matched source, with the version proven by header timestamp and digest comparison
- Inventory: HIGH for handler locations (grep plus reads); MEDIUM for completeness (a ~280-file sweep focused on the four D-12 groups)
- Registry type names: MEDIUM (A4)
- Privacy/legal: MEDIUM-LOW

**Research date:** 2026-10-03
**Valid until:** until the Umami container is re-pulled (semantics change at 3.4.0); otherwise 30 days
