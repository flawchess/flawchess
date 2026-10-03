# Phase 229: Umami User Identification & Feature Events - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Make UI behavior joinable to accounts. Every authenticated session (guests included) calls
`umami.identify(String(users.id))` so guest → registered → retention stitches into one
`distinct_id`; a per-page inventory of UI-only interactions ships as a small set of prop-carrying
events; the Privacy page stops claiming no personal data is collected. Frontend-only (self-hosted
Umami at analytics.flawchess.com, app site `0ca19960-…`).

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

</domain>

<decisions>
## Implementation Decisions

### Event taxonomy
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

### Identity edge cases
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

### Inventory scope
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

### Post-research decisions (2026-10-03, plan-phase)
- **D-16:** Identity source is the JWT `sub` claim of the stored `auth_token` (FastAPI-Users sets
  it to `str(user.id)`; guest tokens too), not a new profile field. Identify once at boot in
  `main.tsx` (before the tracker's first pageview, closes the D-09 gap on Umami 3.4+) and again in
  the `ProtectedLayout` effect on token/account-type change. Impersonation tokens
  (`is_impersonation: true`) never identify (D-11). The phase stays frontend-only for identity; no
  `id` added to `UserProfileResponse`.
- **D-17:** Pin the Umami image in `docker-compose.yml` to `ghcr.io/umami-software/umami:3.4.0`
  (deliberate upgrade from the running 3.3.1 at the next deploy; migrations 25/26 are additive).
  3.4.0 puts `distinct_id` in the session hash, so shared-device users get separate sessions and
  D-07 holds at the data level. Deploy note: the release must actually pull the new image.
- **D-18:** Account deletion: add a `docs/production-runbook.md` step with the SQL to delete
  Umami `session` / `website_event` (and related) rows by `distinct_id` on a deletion request.
  Manual, no code automation.

### Claude's Discretion
- Exact event-name list and prop keys within D-01/D-04.
- How `page` is derived (explicit literal at call site vs from the route).
- Plan split (identity wiring vs inventory waves) and test strategy (per-event unit tests vs a
  registry-level test). Existing `frontend/src/lib/__tests__/analytics.test.ts` is the anchor.
- The post-ship verification query shape against `flawchess-umami-db`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-183-umami-identify-and-feature-events.md` — full rationale, locked
  decisions, open research questions (a) persistence and (b) logout reset, breadcrumbs.
- `.planning/ROADMAP.md` § Phase 229 — goal and locked items.

### Analytics code and conventions
- `frontend/src/lib/analytics.ts` — `trackEvent`, `identifyAccountType`, `window.umami` typing,
  `scrubUmamiPayload` / `umamiBeforeSend` (payload scrub covers identify too).
- `frontend/src/lib/__tests__/analytics.test.ts` — existing analytics tests.
- `frontend/src/App.tsx` (~lines 661-709) — `umamiAccountTypeOf`, impersonation guard, current
  identify effect in `ProtectedLayout`.
- `frontend/index.html` — tracker tag (`data-domains`, `data-exclude-hash`, `data-before-send`,
  `crossorigin`).
- `frontend/CLAUDE.md` § "Outbound link tracking (Umami)" (lines ~30-43) — event conventions,
  the `<Link>` rule, the DB-known-actions rule to reword.
- `frontend/src/hooks/useAuth.ts` — `logout`, `logoutForPromotion`, `loginWithToken`,
  `impersonate` (D-07 reset hook points).
- `frontend/src/pages/Privacy.tsx` (~line 58) — analytics disclosure sentence to replace.

### Prior decisions
- `.planning/phases/228-settings-page/228-CONTEXT.md` D-10 — `settings-change` / `settings-reset`
  events (already shipped; fits this scheme).
- `.planning/notes/active-engagement-time-tracking.md` — SEED-069's earlier identify rejection;
  add the supersession pointer.
- `app/services/guest_service.py` (~lines 69, 136) — guest promotion keeps the `users` row.

### Research targets (unverified)
- Umami tracker source for the deployed version (`https://analytics.flawchess.com/script.js`):
  does `identify(id, data)` persist (localStorage/sessionStorage) or live in memory; is there a
  reset; does `distinct_id` attach at session level so earlier pageviews in the session are
  covered (D-08, D-09, D-07).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `trackEvent(name, data)` in `lib/analytics.ts`: no-ops without the tracker (dev, ad blockers,
  `data-domains`), so call sites need no guards. The typed wrapper (D-04) should build on it.
- `identifyAccountType()`: extend or replace with an id-carrying identify that keeps the
  `account` tag in `data`.
- `scrubUmamiPayload`: already runs on every outgoing payload including identify.

### Established Patterns
- Existing `trackEvent` call sites: `SettingsPanel.tsx` (`settings-change`), `EngineReadyGate.tsx`
  (engine-gate events as named constants), `useInstallPrompt.ts`, `ImportAskActions.tsx`.
- `data-umami-event` attributes are fine on `<button>` and outbound `target="_blank"` links only.
- Radix `Tabs` (`components/ui/tabs.tsx`) used in `AnalysisTabs.tsx`, `Openings.tsx`,
  `Endgames.tsx`, `LibraryPage.tsx`, `Auth.tsx`; check per page whether a tab changes the URL
  (D-02).

### Integration Points
- `ProtectedLayout` identify effect (`App.tsx`) for D-08/D-11.
- `useAuth.ts` logout paths for D-07.
- Component handlers across `components/analysis`, `components/filters`, `components/move-explorer`,
  `components/library`, `components/train`, `components/bots`, `components/popovers`,
  `components/layout` (mobile More drawer) for D-12/D-13.

</code_context>

<specifics>
## Specific Ideas

- Questions the data must answer: which features go unused; does touching feature X predict
  retention (join `session.distinct_id` to `users` / `user_activity`); per-user journeys for
  support/UX research. Acquisition context: Noël Studer newsletter → `/train` cohort vs Reddit
  traffic (`reports/growth/growth-recommendations-2026-10-03.md`).
- Filter-panel opens tracked alongside changes to separate "discovered" from "used" (D-13).

</specifics>

<deferred>
## Deferred Ideas

None, discussion stayed within phase scope.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — keyword match only, unrelated.
- `172-deferred-review-findings.md` — keyword match only, unrelated.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — unrelated (database).
- `2026-08-29-variation-tree-nested-button.md` — keyword match only, unrelated.

</deferred>

---

*Phase: 229-umami-identify-feature-events*
*Context gathered: 2026-10-03*
